"""Project workspace layout.

A project is a container. The target layout keeps control artifacts in
``program/`` and every repository in ``repos/<id>/`` as a real git repository.
Existing M0 projects keep the flat layout; detection keeps both readable while
the template migrates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTROL_DIR = "program"
REPOS_DIR = "repos"
LAYOUT_MARKER = "project.json"
TEMPLATE_REPOS = ("api", "web", "infra", "e2e")


@dataclass(frozen=True)
class ProjectLayout:
    root: Path
    kind: str

    @classmethod
    def detect(cls, workspace: str | Path) -> ProjectLayout:
        root = Path(workspace)
        if (root / LAYOUT_MARKER).exists():
            return cls(root=root, kind="container")
        return cls(root=root, kind="legacy")

    @classmethod
    def from_project(cls, project: dict[str, Any]) -> ProjectLayout:
        return cls.detect(project["workspace"])

    @property
    def is_container(self) -> bool:
        return self.kind == "container"

    def metadata(self) -> dict[str, Any]:
        path = self.root / LAYOUT_MARKER
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def repo_ids(self) -> list[str]:
        """Repository ids for a container, discovered from ``repos/``."""

        if not self.is_container or not self.repos_root.exists():
            return []
        return sorted(
            item.name
            for item in self.repos_root.iterdir()
            if item.is_dir() and not item.name.startswith(".")
        )

    def git_targets(self) -> list[Path]:
        """Roots that carry their own git history, with or without ``.git``."""

        if not self.is_container:
            return [self.root]
        return [self.control] + [
            self.repo_path(repo_id) for repo_id in self.repo_ids()
        ]

    def git_roots(self) -> list[Path]:
        return [target for target in self.git_targets() if (target / ".git").exists()]

    def repo_ref(self, repo_id: str, relative: str = "") -> str:
        """Return a project-root-relative path for a repository file."""

        base = f"{REPOS_DIR}/{repo_id}" if self.is_container else repo_id
        return f"{base}/{relative}".rstrip("/") if relative else base

    @property
    def control(self) -> Path:
        """Where program artifacts, config and docs live."""

        return self.root / CONTROL_DIR if self.is_container else self.root

    @property
    def repos_root(self) -> Path:
        return self.root / REPOS_DIR if self.is_container else self.root

    def repo_path(self, repo_id: str) -> Path:
        return self.repos_root / repo_id

    def artifact(self, relative: str) -> Path:
        return self.control / relative

    def contains(self, path: Path) -> bool:
        """True when ``path`` resolves inside the project root."""

        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return True
