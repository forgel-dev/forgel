"""The universal requirements/specification document template.

Every free-text change request and every planned task specification is
rendered through the same template, so the process cannot drift into a short
or ad-hoc document. The template is a package file; the renderer fills its
placeholders and keeps every section present.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

TEMPLATE_PATH = Path(__file__).with_name("spec_template.md")
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


def template_text() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def render(values: Mapping[str, Any]) -> str:
    text = template_text()

    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        if value is None:
            return "—"
        rendered = str(value).strip()
        return rendered or "—"

    return PLACEHOLDER.sub(replace, text)


def bullets(values: Sequence[Any], empty: str = "None stated.") -> str:
    lines = [f"- {str(item).strip()}" for item in values if str(item).strip()]
    return "\n".join(lines) or f"- {empty}"


def numbered(prefix: str, values: Sequence[Any]) -> str:
    lines = [
        f"- **{prefix}-{index}**: {str(item).strip()}"
        for index, item in enumerate(values, 1)
        if str(item).strip()
    ]
    return "\n".join(lines) or "- None stated."


def decisions_table(decisions: Sequence[Any]) -> str:
    rows: list[str] = []
    for item in decisions:
        if isinstance(item, dict):
            decision_id = str(item.get("id") or "").strip()
            decision = str(item.get("decision") or "").strip()
            source = str(item.get("source") or "").strip()
        elif isinstance(item, (tuple, list)) and len(item) >= 3:
            decision_id = str(item[0]).strip()
            decision = str(item[1]).strip()
            source = str(item[2]).strip()
        else:
            continue
        if decision:
            rows.append(
                f"| {decision_id or '—'} | {decision} | {source or '—'} |"
            )
    if not rows:
        return (
            "| — | No explicit user decisions were recorded in this "
            "conversation. | — |"
        )
    return (
        "| ID | Decision | Source |\n"
        "|----|----------|--------|\n"
        + "\n".join(rows)
    )
