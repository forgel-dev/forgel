"""Context-file resolution.

Forgel reads ``FORGEL.md`` first, then ``AGENTS.md``, then ``CLAUDE.md`` if a
local compatibility shim exists. The first file is native; the second is the
cross-harness canon; the third is local only and is never generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CONTEXT_FILES = ("FORGEL.md", "AGENTS.md", "CLAUDE.md")


@dataclass(frozen=True)
class ContextFile:
    name: str
    path: Path
    text: str
    native: bool


def resolve_context(workspace: Path) -> list[ContextFile]:
    found: list[ContextFile] = []
    for name in CONTEXT_FILES:
        path = workspace / name
        if not path.exists():
            continue
        found.append(
            ContextFile(
                name=name,
                path=path,
                text=path.read_text(encoding="utf-8"),
                native=name == "FORGEL.md",
            )
        )
    return found


def effective_context(workspace: Path) -> str:
    parts = []
    for item in resolve_context(workspace):
        parts.append(f"# Source: {item.name}\n\n{item.text.strip()}")
    return "\n\n---\n\n".join(parts)
