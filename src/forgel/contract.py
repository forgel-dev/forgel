"""The task contract, shared by the developer and the reviewer.

Both roles receive the same short block: requirements, acceptance, constraints,
non-goals and the files the specification allows. The runtime also uses the
file list to keep commits inside the contract.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any, Mapping

from .layout import ProjectLayout

CONTROL_PREFIXES = ("docs/program/", ".forgel/")
CONTROL_FILES = {"program.yaml", "forgel.toml"}


def is_control_path(value: str) -> bool:
    """True for process state that the engine commits, not a product file."""

    path = str(value or "").strip()
    return path in CONTROL_FILES or path.startswith(CONTROL_PREFIXES)

RULES = """Rules:
- Change only the files the specification lists; make one logical change.
- Stage and commit only those files. Never `git add -A` and never commit the
  whole working tree; an unrelated change is never attributed to this task.
- Do not refactor unrelated code or the test harness, and do not add
  interfaces the specification does not name.
- Never commit temporary, probe, debug or generated scratch files.
- The reviewer judges the committed change against this contract."""


def _spec_text(layout: ProjectLayout, task: Mapping[str, Any]) -> str:
    ref = str(task.get("spec") or "").strip()
    if not ref:
        return ""
    try:
        return layout.artifact(ref).read_text(encoding="utf-8")
    except OSError:
        return ""


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


PLACEHOLDERS = {
    "none",
    "none stated",
    "not identified yet",
    "not stated",
    "unknown",
    "—",
}


def _bullets(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            value = line[2:].strip().strip("`").strip()
            if (
                value
                and value.lower().rstrip(".") not in PLACEHOLDERS
            ):
                items.append(value)
    return items


def affected_files(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> list[str]:
    return _bullets(_section(_spec_text(layout, task), "Affected Files"))


def non_goals(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> list[str]:
    return _bullets(_section(_spec_text(layout, task), "Non-Goals"))


def digest(layout: ProjectLayout, task: Mapping[str, Any]) -> str:
    requirements = [
        str(item) for item in task.get("requirements") or []
    ]
    acceptance = [str(item) for item in task.get("acceptance") or []]
    constraints = [str(item) for item in task.get("constraints") or []]
    goals = non_goals(layout, task)
    files = affected_files(layout, task)

    def block(title: str, values: list[str]) -> str:
        body = "\n".join(f"- {item}" for item in values) or "- see the spec"
        return f"{title}:\n{body}"

    parts = [
        "## Task contract",
        block("Requirements", requirements),
        block("Acceptance criteria", acceptance),
        block("Constraints", constraints),
        block("Non-goals", goals),
        block("Affected files", files),
        RULES,
    ]
    return "\n\n".join(parts)


def in_scope(path: str, affected: list[str]) -> bool:
    value = str(path or "").strip().lstrip("./")
    for entry in affected:
        item = entry.strip().lstrip("./")
        if not item:
            continue
        if value == item or value.startswith(item.rstrip("/") + "/"):
            return True
        if fnmatch.fnmatch(value, item):
            return True
    return False
