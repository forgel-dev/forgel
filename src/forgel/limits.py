"""Runtime limits: defaults, a project override and the set_limit operation.

A limit here is a crash guard, never a work budget. Every limit has a reason,
is configurable, and the controlling agent can raise it at runtime with the
``set_limit`` operation when the work legitimately needs more room.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .layout import ProjectLayout

FILE = "docs/program/limits.json"

LIMITS: dict[str, float] = {
    "command_timeout": 3_600.0,
    "check_timeout": 3_600.0,
    "audit_timeout": 3_600.0,
    "github_check_timeout": 3_600.0,
    "sandbox_timeout": 3_600.0,
    "git_timeout": 3_600.0,
    "clone_timeout": 3_600.0,
}

REASONS: dict[str, str] = {
    "command_timeout": (
        "A repository command (build, test suite, probe) may run this long "
        "before it is treated as hung. One hour covers a deliberately slow "
        "suite; raise it with set_limit for a longer one."
    ),
    "check_timeout": (
        "One acceptance check may run this long. A check that runs a whole "
        "suite or an e2e is not a work budget."
    ),
    "audit_timeout": (
        "The release audit may spend this long on model calls before it is "
        "treated as hung."
    ),
    "github_check_timeout": (
        "A commit's CI checks may take this long before Forgel stops "
        "waiting."
    ),
    "sandbox_timeout": (
        "One command inside the sandbox may run this long."
    ),
    "git_timeout": (
        "A git operation (clone, fetch, push, diff) may run this long."
    ),
    "clone_timeout": (
        "Cloning an adopted repository may take this long."
    ),
}


def path(layout: ProjectLayout) -> Path:
    return layout.artifact(FILE)


def load(layout: ProjectLayout) -> dict[str, float]:
    file = path(layout)
    if not file.is_file():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    values: dict[str, float] = {}
    for name, value in data.items():
        if name not in LIMITS:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            values[name] = number
    return values


def get(
    layout: ProjectLayout,
    name: str,
    default: float | None = None,
) -> float:
    override = load(layout).get(name)
    if override is not None:
        return override
    if default is not None:
        return float(default)
    return float(LIMITS.get(name, 0.0))


def set_value(
    layout: ProjectLayout, name: str, seconds: Any
) -> float:
    if name not in LIMITS:
        raise ValueError(
            f"unknown limit {name!r}; known: "
            + ", ".join(sorted(LIMITS))
        )
    try:
        value = float(seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"limit {name} must be a number of seconds") from exc
    if value <= 0:
        raise ValueError(f"limit {name} must be positive")
    values = load(layout)
    values[name] = value
    file = path(layout)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps(values, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value


def describe() -> str:
    lines = []
    for name in sorted(LIMITS):
        lines.append(
            f"- {name}: {LIMITS[name]:g}s — {REASONS.get(name, '')}"
        )
    return "\n".join(lines)
