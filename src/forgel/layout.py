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
LINKED_DIR = ".forgel"
LINKED_MARKER = Path(LINKED_DIR) / LAYOUT_MARKER
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
        if (root / LINKED_MARKER).exists():
            return cls(root=root, kind="linked")
        return cls(root=root, kind="legacy")

    @classmethod
    def from_project(cls, project: dict[str, Any]) -> ProjectLayout:
        return cls.detect(project["workspace"])

    @property
    def is_container(self) -> bool:
        return self.kind == "container"

    @property
    def is_linked(self) -> bool:
        """A project whose repositories are the folders themselves, in place."""

        return self.kind == "linked"

    @property
    def is_project(self) -> bool:
        return self.kind in {"container", "linked"}

    def metadata(self) -> dict[str, Any]:
        path = (
            self.root / LINKED_MARKER
            if self.is_linked
            else self.root / LAYOUT_MARKER
        )
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def repo_ids(self) -> list[str]:
        """Repository ids for a project."""

        if self.is_linked:
            repos = self.metadata().get("repos")
            if isinstance(repos, list):
                return [
                    str(item["id"])
                    for item in repos
                    if isinstance(item, dict) and item.get("id")
                ]
            return ["main"]
        if not self.is_container or not self.repos_root.exists():
            return []
        return sorted(
            item.name
            for item in self.repos_root.iterdir()
            if item.is_dir() and not item.name.startswith(".")
        )

    def git_targets(self) -> list[Path]:
        """Roots that carry their own git history, with or without ``.git``."""

        if not self.is_project:
            return [self.root]
        targets = [self.control] + [
            self.repo_path(repo_id) for repo_id in self.repo_ids()
        ]
        unique: list[Path] = []
        seen: set[Path] = set()
        for target in targets:
            resolved = target.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            unique.append(target)
        return unique

    def git_roots(self) -> list[Path]:
        return [target for target in self.git_targets() if (target / ".git").exists()]

    def repo_ref(self, repo_id: str, relative: str = "") -> str:
        """Return a project-root-relative path for a repository file."""

        if self.is_linked:
            path = self.repo_path(repo_id)
            try:
                base = path.relative_to(self.root).as_posix()
            except ValueError:
                base = str(path)
            if base == ".":
                return relative or "."
            return f"{base}/{relative}".rstrip("/") if relative else base
        base = f"{REPOS_DIR}/{repo_id}" if self.is_container else repo_id
        return f"{base}/{relative}".rstrip("/") if relative else base

    @property
    def control(self) -> Path:
        """Where program artifacts, config and docs live."""

        if self.is_container:
            return self.root / CONTROL_DIR
        if self.is_linked:
            return self.root
        return self.root

    @property
    def repos_root(self) -> Path:
        if self.is_container:
            return self.root / REPOS_DIR
        return self.root

    def repo_path(self, repo_id: str) -> Path:
        if self.is_linked:
            repos = self.metadata().get("repos")
            if isinstance(repos, list):
                for item in repos:
                    if (
                        isinstance(item, dict)
                        and item.get("id") == repo_id
                    ):
                        stored = str(item.get("path") or "")
                        if stored:
                            path = Path(stored)
                            return (
                                path
                                if path.is_absolute()
                                else self.root / path
                            ).resolve()
                        if repo_id == "main":
                            return self.root
            return self.root / repo_id
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
