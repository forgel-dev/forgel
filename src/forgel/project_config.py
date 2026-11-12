"""Project configuration from ``forgel.toml``.

TOML is used because it is explicit, readable, and parsed by the standard
library. The project file is the most specific configuration layer; explicit
runtime settings still win where they must.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

VALID_QA_RUNTIMES = {"auto", "docker", "local"}


class ConfigError(RuntimeError):
    """Raised when ``forgel.toml`` is malformed or has invalid values."""


@dataclass(frozen=True)
class QAConfig:
    runtime: str = "auto"


@dataclass(frozen=True)
class JurisdictionConfig:
    pack: str = "ru"


@dataclass(frozen=True)
class ModelsConfig:
    default: str = "deepseek-flash"
    architecture: str = "deepseek-v4-pro"


@dataclass(frozen=True)
class BudgetConfig:
    per_feature_usd: float = 10.0
    per_project_usd: float = 300.0


@dataclass(frozen=True)
class ReleaseConfig:
    auto_patch: bool = False
    propose_minor: bool = False


@dataclass(frozen=True)
class ProjectConfig:
    name: str | None
    recipe: str | None
    qa: QAConfig
    jurisdiction: JurisdictionConfig
    models: ModelsConfig
    budget: BudgetConfig
    release: ReleaseConfig


def render_project_config(
    name: str,
    recipe: str = "",
    qa_runtime: str = "auto",
    jurisdiction_pack: str = "ru",
    model_default: str = "deepseek-flash",
    model_architecture: str = "deepseek-v4-pro",
    per_feature_usd: float = 10.0,
    per_project_usd: float = 300.0,
    auto_patch: bool = False,
    propose_minor: bool = False,
) -> str:
    return f"""[project]
name = "{name}"
recipe = "{recipe}"

[qa]
runtime = "{qa_runtime}"

[jurisdiction]
pack = "{jurisdiction_pack}"

[models]
default = "{model_default}"
architecture = "{model_architecture}"

[budget]
per_feature_usd = {per_feature_usd:g}
per_project_usd = {per_project_usd:g}

[release]
auto_patch = {str(auto_patch).lower()}
propose_minor = {str(propose_minor).lower()}
"""


def _section(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"forgel.toml: [{name}] must be a table")
    return value


def load_project_config(workspace: Path) -> ProjectConfig | None:
    path = workspace / "forgel.toml"
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid forgel.toml: {exc}") from exc

    project = _section(data, "project")
    qa = _section(data, "qa")
    jurisdiction = _section(data, "jurisdiction")
    models = _section(data, "models")
    budget = _section(data, "budget")
    release = _section(data, "release")

    runtime = str(qa.get("runtime", "auto"))
    if runtime not in VALID_QA_RUNTIMES:
        raise ConfigError(
            f"forgel.toml: qa.runtime must be one of {sorted(VALID_QA_RUNTIMES)}"
        )

    per_feature = float(budget.get("per_feature_usd", 10.0))
    per_project = float(budget.get("per_project_usd", 300.0))
    if per_feature < 0 or per_project < 0:
        raise ConfigError("forgel.toml: budget values must be non-negative")

    auto_patch = release.get("auto_patch", False)
    propose_minor = release.get("propose_minor", False)
    if not isinstance(auto_patch, bool) or not isinstance(propose_minor, bool):
        raise ConfigError("forgel.toml: [release] values must be booleans")

    return ProjectConfig(
        name=str(project["name"]) if "name" in project else None,
        recipe=str(project["recipe"]) if "recipe" in project else None,
        qa=QAConfig(runtime=runtime),
        jurisdiction=JurisdictionConfig(pack=str(jurisdiction.get("pack", "ru"))),
        models=ModelsConfig(
            default=str(models.get("default", "deepseek-flash")),
            architecture=str(models.get("architecture", "deepseek-v4-pro")),
        ),
        budget=BudgetConfig(
            per_feature_usd=per_feature,
            per_project_usd=per_project,
        ),
        release=ReleaseConfig(
            auto_patch=auto_patch,
            propose_minor=propose_minor,
        ),
    )
