"""Project workspace layout.

A project is a container. The target layout keeps control artifacts in
``program/`` and every repository in ``repos/<id>/`` as a real git repository.
Existing M0 projects keep the flat layout; detection keeps both readable while
the template migrates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CONTROL_DIR = "program"
REPOS_DIR = "repos"
LAYOUT_MARKER = "project.json"


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

    @property
    def is_container(self) -> bool:
        return self.kind == "container"

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
