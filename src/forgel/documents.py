"""Which documents the process takes into work.

A repository may already hold documents when Forgel takes it over: a README,
a plan, its own rule files. They stay readable, but they are not instructions
for Forgel's process. The boundary is the project's initialization time,
recorded when Forgel created or adopted the project.

A document's time is its first commit (``git log --diff-filter=A``), or the
file's own creation time while it is not committed yet.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .layout import ProjectLayout


def parse_time(value: Any) -> datetime | None:
    """Parse an ISO timestamp; ``None`` when it is missing or malformed."""

    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def initialized_at(
    layout: ProjectLayout, project: Mapping[str, Any] | None = None
) -> datetime | None:
    """When Forgel initialized the project, or ``None`` for legacy layouts."""

    metadata = layout.metadata()
    parsed = parse_time(metadata.get("created_at"))
    if parsed is not None:
        return parsed
    if project is not None:
        return parse_time(project.get("created_at"))
    return None


def document_created_at(path: Path) -> datetime | None:
    """When the document first appeared: its first commit or creation time."""

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(path.parent),
                "log",
                "--diff-filter=A",
                "--follow",
                "--format=%aI",
                "--",
                path.name,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0:
        stamps = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        if stamps:
            # ``git log`` is newest first; the earliest add is the last line.
            return parse_time(stamps[-1])
    try:
        stat = path.stat()
    except OSError:
        return None
    created = getattr(stat, "st_birthtime", None)
    return datetime.fromtimestamp(
        created if created else stat.st_mtime, timezone.utc
    )


def is_current(
    path: Path, initialized: datetime | None
) -> bool:
    """True when the document appeared at or after initialization."""

    if initialized is None:
        return True
    created = document_created_at(path)
    if created is None:
        return True
    return created >= initialized


def created_after(value: Any, initialized: datetime | None) -> bool:
    """True when a recorded creation time is at or after initialization."""

    if initialized is None:
        return True
    created = parse_time(value)
    return created is None or created >= initialized


def current_documents(
    paths: Iterable[Path], initialized: datetime | None
) -> list[Path]:
    return [path for path in paths if is_current(path, initialized)]
