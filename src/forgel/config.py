"""Runtime configuration for the core."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Paths used by the core.

    ``home`` holds the ledger and generated projects. ``registry_path`` points at
    the recipe catalog. ``templates_path`` points at the bundled project templates.
    """

    home: Path
    registry_path: Path
    templates_path: Path
    jurisdiction_path: Path
    qa_runtime: str = "auto"

    @classmethod
    def from_env(cls, home: str | Path | None = None) -> Settings:
        """Build settings from an optional explicit home and environment variables."""

        home_path = Path(home) if home is not None else Path(
            os.environ.get("FORGEL_HOME", Path.home() / ".forgel")
        )
        repo_root = Path(__file__).resolve().parents[2]
        registry_path = Path(
            os.environ.get("FORGEL_REGISTRY", repo_root / "registry" / "recipes.json")
        )
        templates_path = Path(__file__).resolve().parent / "templates"
        jurisdiction_path = Path(
            os.environ.get("FORGEL_JURISDICTIONS", repo_root / "jurisdiction")
        )
        qa_runtime = os.environ.get("FORGEL_QA_RUNTIME", "auto").lower()
        if qa_runtime not in {"auto", "docker", "local"}:
            raise ValueError(
                "FORGEL_QA_RUNTIME must be one of: auto, docker, local"
            )
        return cls(
            home=home_path.expanduser().resolve(),
            registry_path=registry_path.expanduser().resolve(),
            templates_path=templates_path,
            jurisdiction_path=jurisdiction_path.expanduser().resolve(),
            qa_runtime=qa_runtime,
        )

    @property
    def db_path(self) -> Path:
        return self.home / "ledger.sqlite3"

    @property
    def projects_dir(self) -> Path:
        return self.home / "projects"
