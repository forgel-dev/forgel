"""Runtime control switches shared by the daemon, the CLI and the chat gateway.

``pause`` is a file-backed switch so it survives a restart and is visible to
every process that shares ``FORGEL_HOME``. A paused daemon starts no new
iterations; commands and status reads keep working.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import write_json


def control_path(home: Path) -> Path:
    return home / "control.json"


def read_control(home: Path) -> dict[str, Any]:
    path = control_path(home)
    if not path.exists():
        return {"paused": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paused": False}
    if not isinstance(data, dict):
        return {"paused": False}
    return {"paused": bool(data.get("paused", False))}


def is_paused(home: Path) -> bool:
    return bool(read_control(home)["paused"])


def set_paused(home: Path, paused: bool) -> Path:
    """Write the switch atomically so a reader never sees a partial file."""

    data = read_control(home)
    data["paused"] = bool(paused)
    path = control_path(home)
    temporary = path.with_suffix(".json.tmp")
    write_json(temporary, data)
    temporary.replace(path)
    return path
