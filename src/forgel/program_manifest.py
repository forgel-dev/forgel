"""Canonical repository list for a project.

``project.json`` is the machine-readable source; ``program.yaml`` is the
human-readable manifest in the control repository. Both are rendered from the
same entries, so adding a repository cannot leave them out of sync.

Dependency edges are the reason to group repositories in one project: if the
frontend consumes the backend contract, the project knows the change set. A
project may also contain independent repositories; the process still works,
but the grouping adds no coupling, and the UI says so.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .artifacts import write_json, write_text
from .layout import ProjectLayout

DEFAULT_TEMPLATE_REPOS: tuple[dict[str, Any], ...] = (
    {
        "id": "api",
        "role": "backend",
        "provider": "local",
        "url": "",
        "depends_on": [],
        "contracts": {"publishes": ["openapi.yaml"]},
    },
    {
        "id": "web",
        "role": "frontend",
        "provider": "local",
        "url": "",
        "depends_on": ["api"],
        "contracts": {"consumes": ["api/openapi.yaml"]},
    },
    {
        "id": "infra",
        "role": "infrastructure",
        "provider": "local",
        "url": "",
        "depends_on": [],
        "contracts": {},
    },
    {
        "id": "e2e",
        "role": "acceptance",
        "provider": "local",
        "url": "",
        "depends_on": ["api", "web"],
        "contracts": {},
    },
)

ROLE_BY_ID = {
    "api": "backend",
    "web": "frontend",
    "infra": "infrastructure",
    "e2e": "acceptance",
}


def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
    repo_id = str(entry.get("id", "")).strip()
    if not repo_id:
        raise ValueError("a repository entry needs an id")
    depends_on = entry.get("depends_on") or []
    if not isinstance(depends_on, list):
        depends_on = []
    contracts = entry.get("contracts") or {}
    if not isinstance(contracts, dict):
        contracts = {}
    normalized_contracts = {
        key: [str(item) for item in values if str(item).strip()]
        for key, values in contracts.items()
        if isinstance(values, list) and values
    }
    normalized: dict[str, Any] = {
        "id": repo_id,
        "role": str(
            entry.get("role") or ROLE_BY_ID.get(repo_id, "application")
        ),
        "provider": str(
            entry.get("provider") or ("git" if entry.get("url") else "local")
        ),
        "url": str(entry.get("url") or ""),
        "depends_on": [str(item) for item in depends_on if str(item).strip()],
        "contracts": normalized_contracts,
    }
    if entry.get("path"):
        normalized["path"] = str(entry["path"])
    return normalized


def _default_entry(repo_id: str) -> dict[str, Any]:
    for entry in DEFAULT_TEMPLATE_REPOS:
        if entry["id"] == repo_id:
            return _normalize(dict(entry))
    return _normalize({"id": repo_id})


def entries(layout: ProjectLayout) -> list[dict[str, Any]]:
    metadata = layout.metadata()
    if isinstance(metadata.get("repos"), list):
        normalized: list[dict[str, Any]] = []
        for item in metadata["repos"]:
            if isinstance(item, dict) and item.get("id"):
                normalized.append(_normalize(item))
            elif isinstance(item, str) and item.strip():
                normalized.append(_default_entry(item.strip()))
        # An explicitly empty list is meaningful for a brownfield project
        # before its first repository is recorded.
        if normalized or metadata.get("mode") == "brownfield":
            return normalized
    return [dict(entry) for entry in DEFAULT_TEMPLATE_REPOS]


def entry_map(layout: ProjectLayout) -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in entries(layout)}


def repo_control_path(layout: ProjectLayout, repo_id: str) -> str:
    """Path as written in program.yaml, relative to the control repo."""

    if layout.is_container:
        return f"../repos/{repo_id}"
    if layout.is_linked:
        target = layout.repo_path(repo_id)
        try:
            return os.path.relpath(target, layout.root)
        except ValueError:
            return str(target)
    return f"./{repo_id}"


def repo_project_path(layout: ProjectLayout, repo_id: str) -> str:
    return layout.repo_ref(repo_id)


def render_program(
    layout: ProjectLayout,
    name: str,
    recipe: str,
    repos: list[dict[str, Any]],
) -> str:
    recipe_literal = json.dumps(recipe) if recipe else '""'
    lines = [
        "# program.yaml",
        f"project: {name}",
        f"recipe: {recipe_literal}",
        "repos:",
    ]
    for entry in repos:
        lines.extend(
            [
                f"  - id: {entry['id']}",
                f"    role: {entry['role']}",
                f"    path: {repo_control_path(layout, entry['id'])}",
            ]
        )
        if entry.get("provider"):
            lines.append(f"    provider: {entry['provider']}")
        if entry.get("url"):
            lines.append(f"    url: {json.dumps(entry['url'])}")
        depends_on = entry.get("depends_on") or []
        rendered = ", ".join(depends_on) if depends_on else ""
        lines.append(f"    depends_on: [{rendered}]")
        contracts = entry.get("contracts") or {}
        if contracts:
            lines.append("    contracts:")
            for key in ("publishes", "consumes"):
                values = contracts.get(key)
                if values:
                    lines.append(f"      {key}: [{', '.join(values)}]")
    return "\n".join(lines) + "\n"


def write_program(layout: ProjectLayout, name: str, recipe: str) -> Path:
    return write_text(
        layout.control / "program.yaml",
        render_program(layout, name, recipe, entries(layout)),
    )


def update_metadata(layout: ProjectLayout, values: dict[str, Any]) -> Path:
    if layout.is_container:
        path = layout.root / "project.json"
    elif layout.is_linked:
        path = layout.root / ".forgel" / "project.json"
    else:
        raise ValueError("project metadata is only available in a project")
    metadata = layout.metadata()
    metadata.update(values)
    return write_json(path, metadata)


def set_entries(
    layout: ProjectLayout, repos: list[dict[str, Any]]
) -> Path:
    return update_metadata(
        layout, {"repos": [_normalize(entry) for entry in repos]}
    )


def add_entry(
    layout: ProjectLayout, entry: dict[str, Any]
) -> dict[str, Any]:
    normalized = _normalize(entry)
    current = entries(layout)
    if any(item["id"] == normalized["id"] for item in current):
        raise ValueError(f"repository id already exists: {normalized['id']}")
    set_entries(layout, current + [normalized])
    return normalized


def slugify_repo_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-")
    return slug[:40] or "repo"


def unique_repo_id(layout: ProjectLayout, value: str) -> str:
    base = slugify_repo_id(value)
    existing = {entry["id"] for entry in entries(layout)}
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def validate_dependencies(
    known_ids: set[str], depends_on: list[str]
) -> None:
    unknown = sorted(set(depends_on) - known_ids)
    if unknown:
        raise ValueError(
            "unknown dependency id(s): " + ", ".join(unknown)
        )
