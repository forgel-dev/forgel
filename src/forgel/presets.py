"""Runtime presets: how a repository reads and writes its version manifests.

A release version is carried by the tag and the changelog, but a repository
also declares its version in runtime-specific files: ``package.json`` for
Node, ``pyproject.toml`` or ``__init__.py`` for Python, a version initializer
for Rails. Those files are a property of the runtime, not of the release
train, so the release train asks a preset to read the current version and to
write the new one.

Presets are data in the registry (``registry/recipes.json``) and a repository
selects one explicitly with ``preset:`` in ``program.yaml`` or by the files it
contains. An unknown explicit preset is an error; a repository with no preset
keeps the tag and changelog as its only release record.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

KINDS = {"text", "toml", "ini", "json", "ruby", "regex"}
WILDCARD_CHARS = "*?["


class PresetError(RuntimeError):
    """The preset registry or a version target is invalid."""


@dataclass(frozen=True)
class VersionTarget:
    path: str
    kind: str
    section: str = ""
    key: str = ""
    pattern: str = ""
    replacement: str = ""


@dataclass(frozen=True)
class Preset:
    id: str
    description: str
    detect: tuple[str, ...]
    read: tuple[VersionTarget, ...]
    write: tuple[VersionTarget, ...]


def _target(item: Any, preset_id: str) -> VersionTarget:
    if not isinstance(item, dict):
        raise PresetError(f"preset {preset_id}: a version target must be an object")
    path = str(item.get("path") or "").strip()
    kind = str(item.get("kind") or "").strip().lower()
    if not path:
        raise PresetError(f"preset {preset_id}: a target needs a path")
    if kind not in KINDS:
        raise PresetError(
            f"preset {preset_id}: unknown version kind {kind!r}; "
            f"expected one of {sorted(KINDS)}"
        )
    section = str(item.get("section") or "").strip()
    key = str(item.get("key") or "").strip()
    pattern = str(item.get("pattern") or "")
    replacement = str(item.get("replacement") or "")
    if kind in {"toml", "ini"} and (not section or not key):
        raise PresetError(
            f"preset {preset_id}: {kind} target {path!r} needs section and key"
        )
    if kind in {"json", "ruby"} and not key:
        raise PresetError(
            f"preset {preset_id}: {kind} target {path!r} needs a key"
        )
    if kind == "regex":
        if not pattern:
            raise PresetError(
                f"preset {preset_id}: regex target {path!r} needs a pattern"
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise PresetError(
                f"preset {preset_id}: invalid regex for {path!r}: {exc}"
            ) from exc
    return VersionTarget(
        path=path,
        kind=kind,
        section=section,
        key=key,
        pattern=pattern,
        replacement=replacement,
    )


def load_presets(path: Path) -> list[Preset]:
    """Load runtime presets from the registry file; no presets is valid."""

    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PresetError(f"cannot read presets from {path}: {exc}") from exc
    raw = data.get("presets", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        raise PresetError(f"{path}: presets must be a list")
    presets: list[Preset] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise PresetError(f"{path}: a preset must be an object")
        preset_id = str(item.get("id") or "").strip()
        if not preset_id:
            raise PresetError(f"{path}: a preset needs an id")
        if preset_id in seen:
            raise PresetError(f"{path}: duplicate preset {preset_id!r}")
        seen.add(preset_id)
        detect = item.get("detect") or []
        if not isinstance(detect, list):
            raise PresetError(
                f"preset {preset_id}: detect must be a list"
            )
        read = item.get("read") or []
        write = item.get("write") or []
        if not isinstance(read, list) or not isinstance(write, list):
            raise PresetError(
                f"preset {preset_id}: read and write must be lists"
            )
        presets.append(
            Preset(
                id=preset_id,
                description=str(item.get("description") or "").strip(),
                detect=tuple(
                    str(value).strip()
                    for value in detect
                    if str(value).strip()
                ),
                read=tuple(_target(value, preset_id) for value in read),
                write=tuple(_target(value, preset_id) for value in write),
            )
        )
    return presets


def _matches(repo: Path, pattern: str) -> bool:
    if any(char in pattern for char in WILDCARD_CHARS):
        return any(item.is_file() for item in repo.glob(pattern))
    return (repo / pattern).is_file()


def find_preset(
    presets: list[Preset],
    repo: Path,
    entry: Mapping[str, Any],
) -> Preset | None:
    """The preset named by the entry, or the first one whose files match."""

    wanted = str(entry.get("preset") or "").strip()
    if wanted:
        for preset in presets:
            if preset.id == wanted:
                return preset
        raise PresetError(f"unknown preset {wanted!r}")
    for preset in presets:
        if any(_matches(repo, pattern) for pattern in preset.detect):
            return preset
    return None


def _paths(repo: Path, target: VersionTarget) -> list[Path]:
    if any(char in target.path for char in WILDCARD_CHARS):
        return sorted(
            item for item in repo.glob(target.path) if item.is_file()
        )
    path = repo / target.path
    return [path] if path.is_file() else []


def write_paths(
    presets: list[Preset],
    repo: Path,
    entry: Mapping[str, Any],
    version: str = "",
) -> list[str]:
    """Repository-relative files that carry a version or would be rewritten.

    A file with a recognised version is included even when it already has the
    target value, so a retry after a crash before the release commit can still
    accept the file as part of the release. A file merely matched by a glob
    without a version is not included, so an unrelated edit cannot slip into
    the release commit.
    """

    preset = find_preset(presets, repo, entry)
    if preset is None:
        return []
    paths: list[str] = []
    for target in preset.write:
        for path in _paths(repo, target):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            known = bool(_read(path, target))
            changed = bool(
                version and _write(text, target, version) != text
            )
            if not known and not changed:
                continue
            try:
                relative = path.relative_to(repo).as_posix()
            except ValueError:
                continue
            paths.append(relative)
    return sorted(set(paths))


def _section_bounds(
    text: str, section: str, comment: str
) -> tuple[int, int] | None:
    header = re.search(
        rf"^\[{re.escape(section)}\]\s*(?:{comment})?$", text, re.MULTILINE
    )
    if header is None:
        return None
    start = header.end()
    following = re.search(r"^\[", text[start:], re.MULTILINE)
    end = start + following.start() if following else len(text)
    return start, end


def _read_toml(text: str, target: VersionTarget) -> str:
    bounds = _section_bounds(text, target.section, r"#.*")
    if bounds is None:
        return ""
    body = text[bounds[0] : bounds[1]]
    if re.search(
        r"^dynamic\s*=\s*\[[^\]]*[\"']version[\"']",
        body,
        re.MULTILINE,
    ):
        return ""
    match = re.search(
        rf"^{re.escape(target.key)}\s*=\s*[\"']([^\"']+)[\"']",
        body,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def _write_toml(text: str, target: VersionTarget, version: str) -> str:
    bounds = _section_bounds(text, target.section, r"#.*")
    if bounds is None:
        return text
    body = text[bounds[0] : bounds[1]]
    if re.search(
        r"^dynamic\s*=\s*\[[^\]]*[\"']version[\"']",
        body,
        re.MULTILINE,
    ):
        return text
    match = re.search(
        rf"^({re.escape(target.key)}\s*=\s*[\"'])([^\"']+)([\"'])",
        body,
        re.MULTILINE,
    )
    if match is None:
        return text
    body = (
        body[: match.start()]
        + match.group(1)
        + version
        + match.group(3)
        + body[match.end() :]
    )
    return text[: bounds[0]] + body + text[bounds[1] :]


def _read_ini(text: str, target: VersionTarget) -> str:
    bounds = _section_bounds(text, target.section, r"[;#].*")
    if bounds is None:
        return ""
    body = text[bounds[0] : bounds[1]]
    match = re.search(
        rf"^{re.escape(target.key)}\s*=\s*(\S+)",
        body,
        re.MULTILINE,
    )
    if match is None:
        return ""
    return match.group(1).strip().strip("\"'[]()")


def _write_ini(text: str, target: VersionTarget, version: str) -> str:
    bounds = _section_bounds(text, target.section, r"[;#].*")
    if bounds is None:
        return text
    body = text[bounds[0] : bounds[1]]
    match = re.search(
        rf"^({re.escape(target.key)}\s*=\s*)\S+",
        body,
        re.MULTILINE,
    )
    if match is None:
        return text
    body = body[: match.start()] + match.group(1) + version + body[match.end() :]
    return text[: bounds[0]] + body + text[bounds[1] :]


def _read_json(text: str, target: VersionTarget) -> str:
    match = re.search(
        rf'"{re.escape(target.key)}"\s*:\s*"([^"]*)"', text
    )
    return match.group(1) if match else ""


def _write_json(text: str, target: VersionTarget, version: str) -> str:
    pattern = re.compile(
        rf'("{re.escape(target.key)}"\s*:\s*")([^"]*)(")'
    )
    match = pattern.search(text)
    if match is None:
        return text
    return (
        text[: match.start()]
        + match.group(1)
        + version
        + match.group(3)
        + text[match.end() :]
    )


def _ruby_pattern(target: VersionTarget) -> re.Pattern[str]:
    return re.compile(
        rf"^(\s*{re.escape(target.key)}\s*=\s*[\"'])([^\"']+)([\"'])",
        re.MULTILINE,
    )


def _read_ruby(text: str, target: VersionTarget) -> str:
    match = _ruby_pattern(target).search(text)
    return match.group(2) if match else ""


def _write_ruby(text: str, target: VersionTarget, version: str) -> str:
    match = _ruby_pattern(target).search(text)
    if match is None:
        return text
    return (
        text[: match.start()]
        + match.group(1)
        + version
        + match.group(3)
        + text[match.end() :]
    )


def _read(path: Path, target: VersionTarget) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    if target.kind == "text":
        return text.strip()
    if target.kind == "toml":
        return _read_toml(text, target)
    if target.kind == "ini":
        return _read_ini(text, target)
    if target.kind == "json":
        return _read_json(text, target)
    if target.kind == "ruby":
        return _read_ruby(text, target)
    if target.kind == "regex":
        match = re.search(target.pattern, text)
        return match.group(1) if match else ""
    return ""


def _write(text: str, target: VersionTarget, version: str) -> str:
    if target.kind == "text":
        return version + "\n"
    if target.kind == "toml":
        return _write_toml(text, target, version)
    if target.kind == "ini":
        return _write_ini(text, target, version)
    if target.kind == "json":
        return _write_json(text, target, version)
    if target.kind == "ruby":
        return _write_ruby(text, target, version)
    if target.kind == "regex":
        if not target.replacement:
            return text
        return re.sub(
            target.pattern,
            target.replacement.replace("{version}", version),
            text,
            count=1,
        )
    return text


def read_versions(
    presets: list[Preset],
    repo: Path,
    entry: Mapping[str, Any],
) -> list[tuple[str, str]]:
    """Version strings declared by the repository's preset."""

    preset = find_preset(presets, repo, entry)
    if preset is None:
        return []
    found: list[tuple[str, str]] = []
    for target in preset.read:
        for path in _paths(repo, target):
            value = _read(path, target)
            if not value:
                continue
            try:
                relative = path.relative_to(repo).as_posix()
            except ValueError:
                relative = str(path)
            found.append((value, f"preset {preset.id} {relative}"))
    return found


def write_version(
    presets: list[Preset],
    repo: Path,
    entry: Mapping[str, Any],
    version: str,
) -> tuple[str, list[str]]:
    """Write the release version into the preset's manifests."""

    preset = find_preset(presets, repo, entry)
    if preset is None:
        return "", []
    changed: list[str] = []
    for target in preset.write:
        for path in _paths(repo, target):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            updated = _write(text, target, version)
            if updated == text:
                continue
            try:
                path.write_text(updated, encoding="utf-8")
            except OSError:
                continue
            try:
                relative = path.relative_to(repo).as_posix()
            except ValueError:
                relative = str(path)
            changed.append(relative)
    return preset.id, sorted(set(changed))
