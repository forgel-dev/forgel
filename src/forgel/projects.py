"""Project creation and lookup shared by the CLI and the chat gateway."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .artifacts import ensure_dir, write_json
from .config import Settings
from .layout import TEMPLATE_REPOS
from .ledger import Ledger, new_project_id

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")


class ProjectError(RuntimeError):
    """Raised when a project cannot be created or resolved."""


def derive_name(brief: str) -> str:
    """Derive a short ASCII project name from the first words of a brief."""

    words = re.findall(r"[A-Za-z0-9_-]+", brief)
    name = " ".join(words[:5])[:48].strip()
    return name or "project"


def create_project(
    settings: Settings,
    ledger: Ledger,
    name: str,
    brief: str,
    mode: str = "template",
) -> str:
    name = " ".join(name.split())
    if not NAME_RE.fullmatch(name):
        raise ProjectError(
            "name must be 1-64 characters of letters, digits, spaces, "
            "hyphens or underscores"
        )
    brief = brief.strip()
    if not brief:
        raise ProjectError("the brief must not be empty")
    if mode not in {"template", "brownfield"}:
        raise ProjectError(f"unknown project mode {mode!r}")
    project_id = new_project_id(name)
    workspace = settings.projects_dir / project_id
    ensure_dir(workspace / "program")
    ensure_dir(workspace / "repos")
    write_json(
        workspace / "project.json",
        {
            "id": project_id,
            "name": name,
            "layout": "container",
            "mode": mode,
            "repos": list(TEMPLATE_REPOS) if mode == "template" else [],
            "created_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
        },
    )
    ledger.create_project(project_id, name, brief, str(workspace))
    return project_id


def resolve_project(ledger: Ledger, token: str) -> dict[str, Any]:
    """Resolve a full id, a unique id prefix, or a unique project name."""

    token = token.strip()
    if not token:
        raise ProjectError("provide a project id or a unique prefix")
    projects = ledger.list_projects()
    exact = [project for project in projects if project["id"] == token]
    if exact:
        return exact[0]
    prefixed = [project for project in projects if project["id"].startswith(token)]
    if len(prefixed) == 1:
        return prefixed[0]
    if len(prefixed) > 1:
        ids = ", ".join(project["id"] for project in prefixed)
        raise ProjectError(f"ambiguous prefix {token!r}: {ids}")
    named = [project for project in projects if project["name"].lower() == token.lower()]
    if len(named) == 1:
        return named[0]
    if len(named) > 1:
        raise ProjectError(f"multiple projects are named {token!r}; use an id")
    raise ProjectError(f"unknown project {token!r}")
