"""The task contract, shared by the developer and the reviewer.

Both roles receive the same short block: requirements, acceptance, constraints
and non-goals. A specification states behavior, not an implementation file
list: the developer and the reviewer judge the change as a whole against the
requirements — whether a needed file is missing and whether an unrelated,
temporary or generated file is present.
"""

from __future__ import annotations

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
- Make one coherent change that implements the requirements.
- Include every file the task needs to work; exclude unrelated, temporary,
  debug or generated files.
- Stage and commit only the changed files. Never `git add -A` and never commit
  the whole working tree; an unrelated change is never attributed to this task.
- Do not refactor unrelated code or the test harness, and do not add
  interfaces the requirements do not name.
- Documentation is text: do not add or require tests for it; the reviewer
  reads it.
- Documentation states behavior and stable interfaces, never volatile
  implementation details such as timings, runtime bounds, internal structure
  or local environment; remove a stale detail instead of changing code to
  match it.
- The reviewer judges the change as a whole against the requirements, not
  against a file list."""


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


def without_affected_files(text: str) -> str:
    """Drop an implementation file list left in an older specification.

    The specification states behavior. A file list from an earlier version is
    context at most; neither the developer nor the reviewer compares against
    it.
    """

    return re.sub(
        r"^##\s+Affected Files\s*$\n.*?(?=^##\s|\Z)",
        "",
        text,
        flags=re.MULTILINE | re.DOTALL,
    ).strip() + "\n"


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

    def block(title: str, values: list[str]) -> str:
        body = "\n".join(f"- {item}" for item in values) or "- see the spec"
        return f"{title}:\n{body}"

    parts = [
        "## Task contract",
        block("Requirements", requirements),
        block("Acceptance criteria", acceptance),
        block("Constraints", constraints),
        block("Non-goals", goals),
        RULES,
    ]
    return "\n\n".join(parts)
