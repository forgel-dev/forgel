"""Brief intake for the M0 skeleton.

The real intake will ask the user clarifying questions. For M0 it produces a
small, honest structured record: the brief plus the capabilities the stub recipe
needs. It does not pretend to infer features from free text.
"""

from __future__ import annotations

from typing import Any


def build_requirements(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": project["name"],
        "brief": project["brief"],
        "requires": ["web"],
        "excludes": [],
        "region": "ru",
        "jurisdiction": "ru",
        "entity": "unspecified",
        "payments": False,
        "constraints": [],
    }
