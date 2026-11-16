"""Read-only repository inspection for model-driven research."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .layout import ProjectLayout

MAX_READ_CHARS = 200_000
MAX_LIST_ENTRIES = 200
READ_DEFAULT_LINES = 2_000
READ_MAX_LINES = 5_000
RESEARCH_ACTIONS = {"list_files", "read_file"}
SKIP_PARTS = {
    ".git",
    ".forgel",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
}


class RepoActionError(ValueError):
    """A research action is invalid or leaves the repository."""


def _repo_id(
    repos: Sequence[Mapping[str, Any]], action: Mapping[str, Any]
) -> str:
    known = [str(entry["id"]) for entry in repos]
    requested = str(action.get("repo_id") or "").strip()
    if not requested:
        requested = "main" if "main" in known else (known[0] if known else "")
    if requested not in known:
        raise RepoActionError(f"unknown repository: {requested or '(none)'}")
    return requested


def _repo(
    layout: ProjectLayout,
    repos: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> Path:
    return layout.repo_path(_repo_id(repos, action)).resolve()


def _path(repo: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RepoActionError("a path is required")
    relative = Path(value)
    if relative.is_absolute():
        raise RepoActionError("absolute paths are not allowed")
    candidate = (repo / relative).resolve()
    try:
        candidate.relative_to(repo.resolve())
    except ValueError as exc:
        raise RepoActionError("path escapes the repository") from exc
    if any(part in {".git", ".forgel"} for part in relative.parts):
        raise RepoActionError(
            "the .git and .forgel directories are off-limits"
        )
    if relative.parts[:2] == ("docs", "program"):
        raise RepoActionError(
            "process artifacts under docs/program are not readable"
        )
    return candidate


def read_text_page(
    path: Path,
    offset: Any = 1,
    limit: Any = READ_DEFAULT_LINES,
    display: str = "",
) -> str:
    """Read a line range with numbering and an explicit continuation hint."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"cannot read {display or path.name}: {exc}"
    all_lines = text.splitlines()
    total = len(all_lines)
    try:
        start = max(1, int(offset))
    except (TypeError, ValueError):
        start = 1
    try:
        count = max(1, min(int(limit), READ_MAX_LINES))
    except (TypeError, ValueError):
        count = READ_DEFAULT_LINES
    if total == 0:
        return f"{display or path.name}: empty file"
    if start > total:
        return (
            f"{display or path.name}: {total} lines; "
            f"offset {start} is past the end"
        )
    end = min(total, start + count - 1)
    numbered: list[str] = []
    used = 0
    for number in range(start, end + 1):
        line = all_lines[number - 1]
        rendered = f"{number:04d}| {line}"
        if used + len(rendered) + 1 > MAX_READ_CHARS:
            if not numbered:
                numbered.append(
                    f"{number:04d}| "
                    + line[:MAX_READ_CHARS]
                    + " ... [line truncated]"
                )
            break
        numbered.append(rendered)
        used += len(rendered) + 1
    actual_end = start + len(numbered) - 1
    header = (
        f"{display or path.name}: lines {start}-{actual_end} of {total}"
    )
    footer = ""
    if actual_end < total:
        footer = (
            f"\n... use read_file with offset={actual_end + 1} "
            f"to continue"
        )
    return header + "\n" + "\n".join(numbered) + footer


def execute_repo_action(
    layout: ProjectLayout,
    repos: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> str:
    """Run one read-only research action and return an observation."""

    repo = _repo(layout, repos, action)
    kind = str(action.get("action"))
    if kind == "list_files":
        path = _path(repo, action.get("path") or ".")
        if not path.exists():
            return f"not found: {action.get('path')}"
        if not path.is_dir():
            return f"not a directory: {action.get('path')}"
        lines: list[str] = []
        for item in sorted(path.rglob("*")):
            relative = item.relative_to(repo)
            if any(part in SKIP_PARTS for part in relative.parts):
                continue
            if relative.parts[:2] == ("docs", "program"):
                continue
            if item.name.endswith((".pyc", ".sqlite3", ".sqlite")):
                continue
            lines.append(
                relative.as_posix() + ("/" if item.is_dir() else "")
            )
            if len(lines) >= MAX_LIST_ENTRIES:
                lines.append("... [list truncated]")
                break
        return "\n".join(lines) or "(empty)"
    if kind == "read_file":
        path = _path(repo, action.get("path"))
        if (
            path.name.startswith(".env")
            or path.name in {"id_rsa", "id_ed25519", "ledger.sqlite3"}
            or path.suffix in {".pem", ".key"}
        ):
            return "secret-like files are not readable"
        if not path.exists() or not path.is_file():
            return f"file not found: {action.get('path')}"
        data = path.read_bytes()
        if b"\x00" in data:
            return "binary file; not displayed"
        return read_text_page(
            path,
            action.get("offset", 1),
            action.get("limit", READ_DEFAULT_LINES),
            display=str(action.get("path") or ""),
        )
    raise RepoActionError(f"unknown action: {kind}")
