"""Artifact and template helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> Path:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, data: Any) -> Path:
    return write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_template(
    source: Path, destination: Path, substitutions: dict[str, str]
) -> None:
    """Copy a text-only template tree, replacing placeholders in every file."""

    for item in sorted(source.rglob("*")):
        if "__pycache__" in item.parts or "node_modules" in item.parts:
            continue
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            ensure_dir(target)
            continue
        text = item.read_text(encoding="utf-8")
        for key, value in substitutions.items():
            text = text.replace(key, value)
        write_text(target, text)
