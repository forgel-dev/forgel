"""The project environment contract (``environment.yaml``).

An environment is a declarative project artifact (D-071, PLAN §7.13): a
container image or a build context, plus the commands Forgel runs. The core
never knows a language's test or e2e command; it reads this file and runs what
it says inside the project sandbox.

The file lives in the control repository (``program/environment.yaml`` for a
container project, the project root for a legacy one), or in the sole
repository of a brownfield project, where it is committed next to the code.
``build`` and ``services`` paths are relative to the file's own directory.
Commands run in the repository named by ``repo``; when it is omitted, the sole
repository is used, otherwise the project root. ``mounts`` lists sibling
repositories the commands need; the sandbox mounts them read-only, so a
repository's e2e can inspect the product without exposing the rest of the
project. ``env`` adds variables to every command, both in the sandbox and in
the local fallback.

Only a strict YAML subset is accepted: top-level ``key: value`` pairs, scalar
values, flow lists (``[a, b]``), block lists and one level of nested mapping
(for ``env``). That is the whole contract, so a richer document is a mistake
worth reporting, not silently ignoring.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layout import ProjectLayout
from .program_manifest import entries

FILENAME = "environment.yaml"
FIELDS = {
    "image",
    "build",
    "repo",
    "mounts",
    "services",
    "setup",
    "test",
    "e2e",
    "env",
    "ports",
    "health",
}
COMMAND_FIELDS = ("setup", "test", "e2e")
REPO_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
RESERVED_ENV = {"HOME", "TMPDIR"}


class EnvironmentError(ValueError):
    """The environment contract is malformed or inconsistent with the project."""


@dataclass(frozen=True)
class Environment:
    """A parsed environment contract."""

    image: str = ""
    build: str = ""
    repo: str = ""
    mounts: tuple[str, ...] = ()
    services: tuple[str, ...] = ()
    setup: tuple[str, ...] = ()
    test: tuple[str, ...] = ()
    e2e: tuple[str, ...] = ()
    env: tuple[tuple[str, str], ...] = ()
    ports: tuple[int, ...] = ()
    health: str = ""
    # The directory the contract was loaded from; build and services resolve
    # against it. Not part of the contract's value or identity.
    base: Path | None = field(default=None, compare=False, repr=False)

    @property
    def env_map(self) -> dict[str, str]:
        return dict(self.env)

    def commands(self, name: str) -> tuple[str, ...]:
        if name not in COMMAND_FIELDS:
            raise ValueError(f"unknown command field: {name}")
        return tuple(getattr(self, name))

    @property
    def has_commands(self) -> bool:
        return any(self.commands(name) for name in COMMAND_FIELDS)

    def repository(self, layout: ProjectLayout) -> str:
        """The repository the commands run in, or ``""`` for the project root."""

        if self.repo:
            return self.repo
        known = [entry["id"] for entry in entries(layout)]
        return known[0] if len(known) == 1 else ""

    def workdir(self, layout: ProjectLayout) -> Path:
        repo_id = self.repository(layout)
        return layout.repo_path(repo_id) if repo_id else layout.root

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.image:
            data["image"] = self.image
        if self.build:
            data["build"] = self.build
        if self.repo:
            data["repo"] = self.repo
        for key in ("mounts", "services", "setup", "test", "e2e"):
            values = getattr(self, key)
            if values:
                data[key] = list(values)
        if self.env:
            data["env"] = self.env_map
        if self.ports:
            data["ports"] = list(self.ports)
        if self.health:
            data["health"] = self.health
        return data


# --------------------------------------------------------------------- YAML


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment, respecting quoted strings."""

    out: list[str] = []
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            out.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(line):
                out.append(line[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            out.append(char)
        elif char == "#" and (not out or out[-1].isspace()):
            break
        else:
            out.append(char)
        index += 1
    return "".join(out).rstrip()


def _unquote(value: str, number: int) -> str:
    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            raise EnvironmentError(
                f"line {number}: unterminated double-quoted string"
            )
        try:
            return str(json.loads(value))
        except json.JSONDecodeError as exc:
            raise EnvironmentError(
                f"line {number}: invalid double-quoted string: {exc}"
            ) from exc
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise EnvironmentError(
                f"line {number}: unterminated single-quoted string"
            )
        return value[1:-1].replace("''", "'")
    if value[:1] in "[{":
        raise EnvironmentError(
            f"line {number}: only scalar values and [a, b] lists are supported"
        )
    return value


def _flow_list(body: str, number: int) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(body):
        char = body[index]
        if quote:
            current.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(body):
                current.append(body[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            current.append(char)
        elif char == ",":
            items.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    if quote:
        raise EnvironmentError(f"line {number}: unterminated quoted list item")
    items.append("".join(current))
    if items == [""]:
        return []
    return [_unquote(item.strip(), number) for item in items]


def _scalar(value: str, number: int) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("["):
        if not value.endswith("]"):
            raise EnvironmentError(f"line {number}: unterminated list")
        return _flow_list(value[1:-1], number)
    return _unquote(value, number)


def _split_key(line: str, number: int) -> tuple[str, str]:
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == ":" and (
            index + 1 == len(line) or line[index + 1] in " \t"
        ):
            key = line[:index].strip()
            if not key or not all(part.isalnum() or part in "_-" for part in key):
                raise EnvironmentError(f"line {number}: invalid key {key!r}")
            return key, line[index + 1 :].strip()
        index += 1
    raise EnvironmentError(f"line {number}: expected 'key: value'")


def parse_yaml(text: str) -> dict[str, Any]:
    """Parse the strict YAML subset used by the environment contract."""

    lines = text.splitlines()
    data: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        number = index + 1
        line = _strip_comment(lines[index])
        index += 1
        if not line.strip():
            continue
        if "\t" in line:
            raise EnvironmentError(f"line {number}: tabs are not allowed")
        if line[:1].isspace():
            raise EnvironmentError(f"line {number}: unexpected indentation")
        key, value = _split_key(line, number)
        if key in data:
            raise EnvironmentError(f"line {number}: duplicate key {key!r}")
        if value:
            data[key] = _scalar(value, number)
            continue
        items: list[Any] = []
        mapping: dict[str, Any] = {}
        indent: int | None = None
        is_map = False
        while index < len(lines):
            nested_number = index + 1
            nested = _strip_comment(lines[index])
            if not nested.strip():
                index += 1
                continue
            if not nested[:1].isspace():
                break
            if "\t" in nested:
                raise EnvironmentError(
                    f"line {nested_number}: tabs are not allowed"
                )
            stripped = nested.strip()
            current = len(nested) - len(nested.lstrip())
            if indent is None:
                indent = current
                is_map = not stripped.startswith("-")
            elif current != indent:
                raise EnvironmentError(
                    f"line {nested_number}: inconsistent indentation"
                )
            if is_map:
                nested_key, nested_value = _split_key(stripped, nested_number)
                if nested_key in mapping:
                    raise EnvironmentError(
                        f"line {nested_number}: duplicate key {nested_key!r}"
                    )
                if not nested_value:
                    raise EnvironmentError(
                        f"line {nested_number}: nested values must be scalar"
                    )
                mapping[nested_key] = _scalar(
                    nested_value, nested_number
                )
            else:
                if not stripped.startswith("-"):
                    raise EnvironmentError(
                        f"line {nested_number}: expected a '- item' list entry"
                    )
                item = stripped[1:].strip()
                if not item:
                    raise EnvironmentError(
                        f"line {nested_number}: empty list entry"
                    )
                items.append(_scalar(item, nested_number))
            index += 1
        data[key] = mapping if is_map else items
    return data


# ----------------------------------------------------------------- contract


def _string(data: dict[str, Any], key: str, source: str) -> str:
    value = data.get(key, "")
    if not isinstance(value, str):
        raise EnvironmentError(f"{source}: '{key}' must be a string")
    return value.strip()


def _strings(data: dict[str, Any], key: str, source: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list):
        raise EnvironmentError(
            f"{source}: '{key}' must be a string or a list of strings"
        )
    items = [str(item).strip() for item in value]
    if any(not item for item in items):
        raise EnvironmentError(f"{source}: '{key}' contains an empty entry")
    return tuple(items)


def _commands(data: dict[str, Any], key: str, source: str) -> tuple[str, ...]:
    commands = _strings(data, key, source)
    for command in commands:
        if "\x00" in command:
            raise EnvironmentError(f"{source}: '{key}' contains a NUL byte")
    return commands


def _project_path(value: str, key: str, source: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        raise EnvironmentError(
            f"{source}: '{key}' must be relative to the contract directory"
        )
    if ".." in path.parts:
        raise EnvironmentError(
            f"{source}: '{key}' must not leave the contract directory"
        )
    return path.as_posix()


def _env_map(data: dict[str, Any], source: str) -> tuple[tuple[str, str], ...]:
    value = data.get("env", {})
    if value in ({}, []):
        return ()
    if not isinstance(value, dict):
        raise EnvironmentError(
            f"{source}: 'env' must be a mapping of NAME: value"
        )
    items: list[tuple[str, str]] = []
    for key, item in value.items():
        if not ENV_NAME.fullmatch(str(key)):
            raise EnvironmentError(f"{source}: invalid env name {key!r}")
        if key in RESERVED_ENV:
            raise EnvironmentError(
                f"{source}: env cannot override {key}; the sandbox sets it"
            )
        if not isinstance(item, str):
            raise EnvironmentError(
                f"{source}: env value for {key} must be a string"
            )
        if "\x00" in item:
            raise EnvironmentError(
                f"{source}: env value for {key} contains a NUL byte"
            )
        items.append((str(key), item))
    return tuple(items)


def _ports(data: dict[str, Any], source: str) -> tuple[int, ...]:
    value = data.get("ports", [])
    if isinstance(value, (int, str)):
        value = [value]
    if not isinstance(value, list):
        raise EnvironmentError(f"{source}: 'ports' must be an integer or a list")
    ports: list[int] = []
    for item in value:
        if isinstance(item, bool):
            raise EnvironmentError(f"{source}: 'ports' must contain integers")
        try:
            port = int(str(item).strip())
        except ValueError as exc:
            raise EnvironmentError(
                f"{source}: 'ports' must contain integers"
            ) from exc
        if not 1 <= port <= 65535:
            raise EnvironmentError(
                f"{source}: port {port} is outside 1..65535"
            )
        ports.append(port)
    return tuple(dict.fromkeys(ports))


def parse_environment(
    text: str, source: str = FILENAME, base: Path | None = None
) -> Environment:
    """Parse and validate an environment contract."""

    data = parse_yaml(text)
    unknown = sorted(set(data) - FIELDS)
    if unknown:
        raise EnvironmentError(
            f"{source}: unknown field(s): {', '.join(unknown)}"
        )
    image = _string(data, "image", source)
    build = _project_path(_string(data, "build", source), "build", source)
    if not image and not build:
        raise EnvironmentError(f"{source}: 'image' or 'build' is required")
    if image and build:
        raise EnvironmentError(
            f"{source}: set either 'image' or 'build', not both"
        )
    repo = _string(data, "repo", source)
    if repo and not REPO_NAME.fullmatch(repo):
        raise EnvironmentError(f"{source}: invalid 'repo' name {repo!r}")
    mounts = tuple(dict.fromkeys(_strings(data, "mounts", source)))
    for item in mounts:
        if not REPO_NAME.fullmatch(item):
            raise EnvironmentError(
                f"{source}: invalid repository id in 'mounts': {item!r}"
            )
        if item == repo:
            raise EnvironmentError(
                f"{source}: 'mounts' repeats the working repository {item!r}"
            )
    services = tuple(
        _project_path(path, "services", source)
        for path in _strings(data, "services", source)
    )
    ports = _ports(data, source)
    health = _string(data, "health", source)
    if health and not (
        health.startswith("/")
        or health.startswith("http://")
        or health.startswith("https://")
    ):
        raise EnvironmentError(
            f"{source}: 'health' must be a path or an http(s) URL"
        )
    return Environment(
        image=image,
        build=build,
        repo=repo,
        mounts=mounts,
        services=services,
        setup=_commands(data, "setup", source),
        test=_commands(data, "test", source),
        e2e=_commands(data, "e2e", source),
        env=_env_map(data, source),
        ports=ports,
        health=health,
        base=base,
    )


def command_argv(command: str) -> list[str]:
    """Split a contract command for execution.

    A bare ``python`` or ``python3`` is resolved to the interpreter running
    Forgel, so a committed contract stays portable across hosts where only one
    of those names exists.
    """

    argv = shlex.split(command)
    if not argv:
        raise EnvironmentError("an empty command cannot be run")
    if Path(argv[0]).name in {"python", "python3"}:
        argv[0] = sys.executable
    return argv


def environment_path(layout: ProjectLayout) -> Path:
    """Where the contract lives: the control repository, else the sole repo.

    A brownfield project commits its environment next to the code, so a
    project with one repository may keep ``environment.yaml`` there. The
    control repository still wins when both exist.
    """

    control = layout.control / FILENAME
    if control.is_file():
        return control
    known = entries(layout)
    if len(known) == 1:
        candidate = layout.repo_path(known[0]["id"]) / FILENAME
        if candidate.is_file():
            return candidate
    return control


def load_environment(layout: ProjectLayout) -> Environment | None:
    """Read the project's environment contract, or ``None`` when absent.

    A malformed contract raises :class:`EnvironmentError`; it never falls back
    silently, because a broken environment must be visible in QA. The fallback
    is only for projects that do not define one yet.
    """

    path = environment_path(layout)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EnvironmentError(f"{path}: cannot read: {exc}") from exc
    environment = parse_environment(
        text, source=str(path), base=path.parent
    )
    known = {entry["id"] for entry in entries(layout)}
    repo_id = environment.repository(layout)
    if environment.repo and repo_id not in known:
        raise EnvironmentError(
            f"{path}: unknown repository {repo_id!r}; known: "
            + ", ".join(sorted(known))
        )
    unknown_mounts = sorted(set(environment.mounts) - known)
    if unknown_mounts:
        raise EnvironmentError(
            f"{path}: unknown repository id(s) in 'mounts': "
            + ", ".join(unknown_mounts)
        )
    base = path.parent
    if environment.build:
        target = base / environment.build
        if not target.exists():
            raise EnvironmentError(
                f"{path}: build path does not exist: {environment.build}"
            )
    for service in environment.services:
        if not (base / service).is_file():
            raise EnvironmentError(
                f"{path}: service file does not exist: {service}"
            )
    return environment


def render_environment(environment: Environment) -> str:
    """Render the contract in the canonical shape used by the templates."""

    data = environment.to_dict()
    lines = [
        "# environment.yaml — the project environment contract.",
        "# The core reads this file; it contains no language-specific logic.",
    ]
    for key in ("image", "build", "repo"):
        if key in data:
            lines.append(f"{key}: {data[key]}")
    for key in ("mounts", "services", "setup", "test", "e2e"):
        if key not in data:
            continue
        values = data[key]
        if len(values) == 1:
            lines.append(f"{key}: [{json.dumps(values[0])}]")
            continue
        lines.append(f"{key}:")
        lines.extend(f"  - {json.dumps(value)}" for value in values)
    if "env" in data:
        lines.append("env:")
        lines.extend(
            f"  {key}: {json.dumps(value)}"
            for key, value in data["env"].items()
        )
    if "ports" in data:
        lines.append("ports: [" + ", ".join(str(port) for port in data["ports"]) + "]")
    if "health" in data:
        lines.append(f"health: {json.dumps(data['health'])}")
    return "\n".join(lines) + "\n"
