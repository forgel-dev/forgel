"""Read-only repository inspection for model-driven research."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .layout import ProjectLayout

MAX_READ_CHARS = 12_000
MAX_LIST_ENTRIES = 200
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
    return layout.repo_path(_repo_id(repos, action))


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
    return candidate


def _cap(text: str) -> str:
    if len(text) <= MAX_READ_CHARS:
        return text
    return text[:MAX_READ_CHARS] + "\n... [truncated]"


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
        return _cap(data.decode("utf-8", errors="replace"))
    raise RepoActionError(f"unknown action: {kind}")
