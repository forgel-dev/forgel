"""Runtime configuration for the core."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import peak
from .model_profiles import default_profile

SANDBOX_MODES = {"local", "docker"}
SANDBOX_NETWORKS = {"none", "bridge"}
MEMORY_LIMIT = re.compile(r"\d+(\.\d+)?[bkmgBKMG]?")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _env_list(name: str) -> tuple[str, ...]:
    value = os.environ.get(name, "")
    return tuple(item.strip() for item in value.split(",") if item.strip())


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
    sandbox: str = "local"
    sandbox_host: str = ""
    sandbox_image: str = ""
    sandbox_projects_root: str = ""
    sandbox_network: str = "none"
    sandbox_cpus: str = "2"
    sandbox_memory: str = "2g"
    sandbox_pids: int = 512
    sandbox_images: tuple[str, ...] = ()
    sandbox_require_digest: bool = False
    sandbox_read_only: bool = True
    context_window: int = default_profile().context_window
    # The runtime reads the policy from the environment (off-peak by default).
    # Direct construction defaults to "always" so library and test code does
    # not become time-dependent.
    peak_policy: str = "always"
    peak_hours: str = default_profile().peak_windows
    timezone: str = ""

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
        sandbox = (
            os.environ.get("FORGEL_SANDBOX", "local").strip().lower()
            or "local"
        )
        if sandbox not in SANDBOX_MODES:
            raise ValueError(
                "FORGEL_SANDBOX must be one of: local, docker"
            )
        sandbox_network = (
            os.environ.get("FORGEL_SANDBOX_NETWORK", "none").strip().lower()
            or "none"
        )
        if sandbox_network not in SANDBOX_NETWORKS:
            raise ValueError(
                "FORGEL_SANDBOX_NETWORK must be one of: none, bridge"
            )
        sandbox_cpus = (
            os.environ.get("FORGEL_SANDBOX_CPUS", "2").strip() or "2"
        )
        try:
            cpus_value = float(sandbox_cpus)
        except ValueError as exc:
            raise ValueError("FORGEL_SANDBOX_CPUS must be a number") from exc
        if cpus_value <= 0:
            raise ValueError("FORGEL_SANDBOX_CPUS must be positive")
        sandbox_memory = (
            os.environ.get("FORGEL_SANDBOX_MEMORY", "2g").strip() or "2g"
        )
        if not MEMORY_LIMIT.fullmatch(sandbox_memory):
            raise ValueError(
                "FORGEL_SANDBOX_MEMORY must look like 512m or 2g"
            )
        pids_raw = (
            os.environ.get("FORGEL_SANDBOX_PIDS", "512").strip() or "512"
        )
        if not pids_raw.isdigit() or int(pids_raw) <= 0:
            raise ValueError("FORGEL_SANDBOX_PIDS must be a positive integer")
        profile = default_profile()
        context_raw = (
            os.environ.get(
                "FORGEL_CONTEXT_WINDOW", str(profile.context_window)
            ).strip()
            or str(profile.context_window)
        )
        if not context_raw.isdigit() or int(context_raw) < 4096:
            raise ValueError(
                "FORGEL_CONTEXT_WINDOW must be an integer of at least 4096"
            )
        peak_policy = peak.policy_from_env()
        if peak_policy not in peak.POLICIES:
            raise ValueError(
                "FORGEL_PEAK_POLICY must be one of: off_peak, always"
            )
        peak_hours = peak.hours_from_env()
        peak.parse_hours(peak_hours)
        return cls(
            home=home_path.expanduser().resolve(),
            registry_path=registry_path.expanduser().resolve(),
            templates_path=templates_path,
            jurisdiction_path=jurisdiction_path.expanduser().resolve(),
            qa_runtime=qa_runtime,
            sandbox=sandbox,
            sandbox_host=os.environ.get("FORGEL_SANDBOX_HOST", "").strip(),
            sandbox_image=os.environ.get("FORGEL_SANDBOX_IMAGE", "").strip(),
            sandbox_projects_root=os.environ.get(
                "FORGEL_SANDBOX_PROJECTS_ROOT", ""
            ).strip(),
            sandbox_network=sandbox_network,
            sandbox_cpus=sandbox_cpus,
            sandbox_memory=sandbox_memory,
            sandbox_pids=int(pids_raw),
            sandbox_images=_env_list("FORGEL_SANDBOX_IMAGES"),
            sandbox_require_digest=_env_bool(
                "FORGEL_SANDBOX_REQUIRE_DIGEST", False
            ),
            sandbox_read_only=_env_bool("FORGEL_SANDBOX_READ_ONLY", True),
            context_window=int(context_raw),
            peak_policy=peak_policy,
            peak_hours=peak_hours,
            timezone=os.environ.get("FORGEL_TIMEZONE", "").strip(),
        )

    @property
    def db_path(self) -> Path:
        return self.home / "ledger.sqlite3"

    @property
    def projects_dir(self) -> Path:
        return self.home / "projects"
