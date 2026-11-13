"""Minimal, comment-preserving edits of known keys in a TOML file.

The standard library reads TOML but does not write it. Rewriting the whole
project file would drop comments and unknown sections, so this module replaces
one ``key = value`` line inside a known section.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value))


def _find_section(lines: list[str], section: str) -> tuple[int, int] | None:
    """Return the header index and the index where the section ends."""

    header = f"[{section}]"
    start = None
    for index, line in enumerate(lines):
        if line.strip() == header:
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    return start, end


def set_value(path: Path, section: str, key: str, literal: str) -> None:
    """Set ``section.key`` to a pre-rendered TOML literal."""

    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    span = _find_section(lines, section)
    new_line = f"{key} = {literal}"
    if span is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([f"[{section}]", new_line])
    else:
        start, end = span
        replaced = False
        for index in range(start + 1, end):
            stripped = lines[index].strip()
            if not stripped or stripped.startswith("#"):
                continue
            name = stripped.split("=", 1)[0].strip()
            if name == key:
                lines[index] = new_line
                replaced = True
                break
        if not replaced:
            insert_at = end
            while insert_at > start + 1 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines.insert(insert_at, new_line)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, path)
