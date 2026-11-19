"""Deterministic validation of acceptance-check commands.

The specification is written by a model; QA is the process gate. This module
is the oracle between them. It does not require a referenced test to exist
yet — the task may be the change that creates it. It refuses a command that
points at a file or package which exists only in a sibling repository: such a
check would run in the task repository and fail for a reason unrelated to the
code, sending the coding agent to fix the wrong thing.

The environment contract's own commands are authoritative and are not
validated here; they run in the environment's working directory.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .layout import ProjectLayout
from .program_manifest import entries

Target = tuple[str, str, bool]  # kind, value, require __main__


def _tokens(command: Sequence[str] | str) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return [str(item) for item in command]


def _strip_prefix(tokens: list[str]) -> list[str]:
    """Drop ``env`` and ``NAME=value`` prefixes before the executable."""

    while tokens and (
        tokens[0] == "env"
        or ("=" in tokens[0] and not tokens[0].startswith("-"))
    ):
        tokens = tokens[1:]
    return tokens


def _python_targets(tokens: list[str]) -> list[Target]:
    """Files or modules a Python command will import or execute."""

    tokens = _strip_prefix(tokens)
    if not tokens:
        return []
    executable = Path(tokens[0]).name
    if not executable.startswith("python"):
        return []
    args = tokens[1:]
    if "-c" in args:
        return []
    targets: list[Target] = []
    if "-m" in args:
        index = args.index("-m")
        if index + 1 >= len(args):
            return []
        module = args[index + 1]
        rest = args[index + 2:]
        if module == "unittest":
            if "discover" in rest:
                start = "."
                for position, item in enumerate(rest):
                    if item in {"-s", "--start-directory"}:
                        if position + 1 < len(rest):
                            start = rest[position + 1]
                    elif item.startswith("--start-directory="):
                        start = item.split("=", 1)[1]
                targets.append(("dir", start, False))
            else:
                for item in rest:
                    if item.startswith("-"):
                        continue
                    if "." in item:
                        targets.append(("module", item, False))
        else:
            targets.append(("module", module, True))
        return targets
    for item in args:
        if item.startswith("-"):
            continue
        targets.append(("script", item, False))
        break
    return targets


def _module_file(workdir: Path, dotted: str) -> Path | None:
    """The file or package directory for a dotted name, or ``None``.

    ``unittest`` names may carry a class or method after the module; the
    longest prefix that resolves wins.
    """

    parts = dotted.split(".")
    for cut in range(len(parts), 0, -1):
        base = workdir.joinpath(*parts[:cut])
        if base.with_suffix(".py").is_file():
            return base.with_suffix(".py")
        if (base / "__init__.py").is_file():
            return base / "__init__.py"
    return None


def _exists(workdir: Path, target: Target) -> bool:
    kind, value, require_main = target
    if kind == "dir":
        return (workdir / value).is_dir()
    if kind == "script":
        return (workdir / value).is_file()
    path = _module_file(workdir, value)
    if path is None:
        return False
    if require_main and path.name == "__init__.py":
        return (path.parent / "__main__.py").is_file()
    return True


def command_problem(
    layout: ProjectLayout,
    repo_id: str,
    command: Sequence[str] | str,
) -> str:
    """Why a check cannot run in the task repository, or ``""``.

    Only proven cross-repository references are rejected. A missing target is
    allowed: the task may create it. A target that exists only in a sibling
    repository is a specification defect, not a code defect.
    """

    tokens = _tokens(command)
    targets = _python_targets(tokens)
    if not targets:
        return ""
    task_workdir = layout.repo_path(repo_id) if repo_id else layout.root
    siblings: list[tuple[str, Path]] = [
        (str(entry["id"]), layout.repo_path(str(entry["id"])))
        for entry in entries(layout)
        if str(entry["id"]) != repo_id
    ]
    for target in targets:
        if _exists(task_workdir, target):
            continue
        for sibling_id, sibling_root in siblings:
            if _exists(sibling_root, target):
                return (
                    f"check command {shlex.join(tokens)} references "
                    f"'{target[1]}', which exists in repository "
                    f"'{sibling_id}' but not in the task repository "
                    f"'{repo_id or 'project root'}' (cwd {task_workdir}); "
                    "the check would fail for a reason unrelated to the task"
                )
    return ""


def check_problems(
    layout: ProjectLayout,
    repo_id: str,
    checks: Iterable[Mapping[str, Any]],
) -> list[str]:
    """Problems of every command check in a normalized specification."""

    problems: list[str] = []
    for check in checks:
        command = check.get("command") or []
        problem = command_problem(layout, repo_id, command)
        if problem:
            criterion = str(check.get("criterion") or "check").strip()
            problems.append(f"{criterion}: {problem}")
    return problems
