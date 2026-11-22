"""Plain-text project and repository instructions.

Conventions such as the artifact language belong in ``FORGEL.md`` and
``AGENTS.md``, not in engine settings. Project-level files (in the control
repository) apply to every repository. A repository may add its own files;
they are more specific and take precedence on conflict. Every model role
receives both layers.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from .documents import initialized_at, is_current
from .layout import ProjectLayout
from .program_manifest import entries

INSTRUCTION_FILES = ("FORGEL.md", "AGENTS.md")
MAX_FILE_CHARS = 6_000
MAX_TOTAL_CHARS = 16_000


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _files(
    root: Path,
    label: str,
    seen: set[Path],
    initialized: datetime | None = None,
) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for name in INSTRUCTION_FILES:
        path = root / name
        if not path.is_file():
            continue
        if not is_current(path, initialized):
            # A rule file that existed before Forgel initialized the project
            # is readable context, not an instruction for the process.
            continue
        try:
            key = path.resolve()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        text = _read(path)
        if text:
            items.append(
                (f"{label}: {name}", text[:MAX_FILE_CHARS])
            )
    return items


def instruction_context(
    layout: ProjectLayout,
    repo_ids: Sequence[str] | None = None,
) -> str:
    """The project and repository instruction layers, labeled and bounded."""

    seen: set[Path] = set()
    initialized = initialized_at(layout)
    items = _files(layout.control, "Project", seen, initialized)
    ids: Iterable[str] = (
        list(repo_ids)
        if repo_ids is not None
        else [str(entry["id"]) for entry in entries(layout)]
    )
    for repo_id in ids:
        items += _files(
            layout.repo_path(repo_id),
            f"Repository {repo_id}",
            seen,
            initialized,
        )
    if not items:
        return ""
    header = (
        "Project and repository instructions. Project rules apply to every "
        "repository; repository rules are more specific and take precedence "
        "on conflict."
    )
    parts = [header]
    used = len(header)
    for label, text in items:
        if used >= MAX_TOTAL_CHARS:
            break
        block = f"### {label}\n{text}"
        remaining = MAX_TOTAL_CHARS - used
        if len(block) > remaining:
            block = block[:remaining] + "\n... [truncated]"
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)
