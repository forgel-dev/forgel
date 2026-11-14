"""Project configuration from ``forgel.toml``.

TOML is used because it is explicit, readable, and parsed by the standard
library. The project file is the most specific configuration layer; explicit
runtime settings still win where they must.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VALID_QA_RUNTIMES = {"auto", "docker", "local"}
VALID_GIT_AUTH = {"auto", "github_app", "pat", "deploy_key"}
VALID_GIT_MERGE = {"auto", "human"}


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
    architecture: str = "deepseek-flash"
    context_window: int = 1_000_000
    peak_policy: str = "off_peak"


@dataclass(frozen=True)
class BudgetConfig:
    per_feature_usd: float = 10.0
    per_project_usd: float = 300.0


@dataclass(frozen=True)
class ReleaseConfig:
    auto_patch: bool = False
    propose_minor: bool = False


@dataclass(frozen=True)
class SimplicityConfig:
    enabled: bool = True
    max_added_lines: int = 400
    max_new_config_keys: int = 2
    max_compat_markers: int = 0


@dataclass(frozen=True)
class RefactoringConfig:
    enabled: bool = True
    budget_percent: int = 10
    allow_auto_targeted: bool = True


@dataclass(frozen=True)
class GitConfig:
    provider: str = "github"
    auth: str = "auto"
    org: str = ""
    base_branch: str = "main"
    branch_prefix: str = "forgel/"
    draft_pr: bool = True
    require_ci: bool = True
    merge: str = "auto"
    auto_revert_on_failure: bool = True


@dataclass(frozen=True)
class ProjectConfig:
    name: str | None
    recipe: str | None
    qa: QAConfig
    jurisdiction: JurisdictionConfig
    models: ModelsConfig
    budget: BudgetConfig
    release: ReleaseConfig
    simplicity: SimplicityConfig
    refactoring: RefactoringConfig
    git: GitConfig = field(default_factory=GitConfig)


def render_project_config(
    name: str,
    recipe: str = "",
    qa_runtime: str = "auto",
    jurisdiction_pack: str = "ru",
    model_default: str = "deepseek-flash",
    model_architecture: str = "deepseek-flash",
    model_context_window: int = 1_000_000,
    model_peak_policy: str = "off_peak",
    per_feature_usd: float = 10.0,
    per_project_usd: float = 300.0,
    auto_patch: bool = False,
    propose_minor: bool = False,
    simplicity_enabled: bool = True,
    max_added_lines: int = 400,
    max_new_config_keys: int = 2,
    max_compat_markers: int = 0,
    refactoring_enabled: bool = True,
    refactor_budget_percent: int = 10,
    allow_auto_targeted: bool = True,
    git_provider: str = "github",
    git_auth: str = "auto",
    git_org: str = "",
    git_base_branch: str = "main",
    git_branch_prefix: str = "forgel/",
    git_draft_pr: bool = True,
    git_require_ci: bool = True,
    git_merge: str = "auto",
    git_auto_revert_on_failure: bool = True,
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
context_window = {model_context_window}
peak_policy = "{model_peak_policy}"

[budget]
per_feature_usd = {per_feature_usd:g}
per_project_usd = {per_project_usd:g}

[release]
auto_patch = {str(auto_patch).lower()}
propose_minor = {str(propose_minor).lower()}

[simplicity]
enabled = {str(simplicity_enabled).lower()}
max_added_lines = {max_added_lines}
max_new_config_keys = {max_new_config_keys}
max_compat_markers = {max_compat_markers}

[refactoring]
enabled = {str(refactoring_enabled).lower()}
budget_percent = {refactor_budget_percent}
allow_auto_targeted = {str(allow_auto_targeted).lower()}

[git]
provider = "{git_provider}"
auth = "{git_auth}"
org = "{git_org}"
base_branch = "{git_base_branch}"
branch_prefix = "{git_branch_prefix}"
draft_pr = {str(git_draft_pr).lower()}
require_ci = {str(git_require_ci).lower()}
merge = "{git_merge}"
auto_revert_on_failure = {str(git_auto_revert_on_failure).lower()}
"""


def _section(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"forgel.toml: [{name}] must be a table")
    return value


def _context_window(models: dict[str, object]) -> int:
    value = models.get("context_window", 1000000)
    if isinstance(value, bool):
        raise ConfigError("forgel.toml: models.context_window must be an integer")
    try:
        window = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            "forgel.toml: models.context_window must be an integer"
        ) from exc
    if window < 4096:
        raise ConfigError(
            "forgel.toml: models.context_window must be at least 4096"
        )
    return window


def _peak_policy(models: dict[str, object]) -> str:
    value = str(models.get("peak_policy", "off_peak")).strip().lower()
    if value not in {"off_peak", "always"}:
        raise ConfigError(
            "forgel.toml: models.peak_policy must be off_peak or always"
        )
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
    simplicity = _section(data, "simplicity")
    refactoring = _section(data, "refactoring")
    git = _section(data, "git")

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

    simplicity_enabled = simplicity.get("enabled", True)
    if not isinstance(simplicity_enabled, bool):
        raise ConfigError("forgel.toml: simplicity.enabled must be a boolean")
    max_added_lines = int(simplicity.get("max_added_lines", 400))
    max_new_config_keys = int(simplicity.get("max_new_config_keys", 2))
    max_compat_markers = int(simplicity.get("max_compat_markers", 0))
    if min(max_added_lines, max_new_config_keys, max_compat_markers) < 0:
        raise ConfigError("forgel.toml: simplicity limits must be non-negative")

    refactoring_enabled = refactoring.get("enabled", True)
    allow_auto_targeted = refactoring.get("allow_auto_targeted", True)
    if not isinstance(refactoring_enabled, bool) or not isinstance(
        allow_auto_targeted, bool
    ):
        raise ConfigError("forgel.toml: [refactoring] flags must be booleans")
    refactor_budget_percent = int(refactoring.get("budget_percent", 10))
    if refactor_budget_percent < 0:
        raise ConfigError("forgel.toml: refactoring.budget_percent must be non-negative")

    git_auth = str(git.get("auth", "auto"))
    if git_auth not in VALID_GIT_AUTH:
        raise ConfigError(
            f"forgel.toml: git.auth must be one of {sorted(VALID_GIT_AUTH)}"
        )
    git_merge = str(git.get("merge", "auto"))
    if git_merge not in VALID_GIT_MERGE:
        raise ConfigError(
            f"forgel.toml: git.merge must be one of {sorted(VALID_GIT_MERGE)}"
        )
    git_base = str(git.get("base_branch", "main")).strip()
    if not git_base or any(char.isspace() for char in git_base):
        raise ConfigError("forgel.toml: git.base_branch must be a branch name")
    git_prefix = str(git.get("branch_prefix", "forgel/"))
    if " " in git_prefix:
        raise ConfigError("forgel.toml: git.branch_prefix must not contain spaces")
    git_org = str(git.get("org", "")).strip()
    if git_org and not re.fullmatch(r"[A-Za-z0-9_.-]+", git_org):
        raise ConfigError("forgel.toml: git.org must be a GitHub owner name")
    git_draft = git.get("draft_pr", True)
    git_require_ci = git.get("require_ci", True)
    git_revert = git.get("auto_revert_on_failure", True)
    if not all(
        isinstance(value, bool)
        for value in (git_draft, git_require_ci, git_revert)
    ):
        raise ConfigError("forgel.toml: [git] flags must be booleans")

    return ProjectConfig(
        name=str(project["name"]) if "name" in project else None,
        recipe=str(project["recipe"]) if "recipe" in project else None,
        qa=QAConfig(runtime=runtime),
        jurisdiction=JurisdictionConfig(pack=str(jurisdiction.get("pack", "ru"))),
        models=ModelsConfig(
            default=str(models.get("default", "deepseek-flash")),
            architecture=str(models.get("architecture", "deepseek-flash")),
            context_window=_context_window(models),
            peak_policy=_peak_policy(models),
        ),
        budget=BudgetConfig(
            per_feature_usd=per_feature,
            per_project_usd=per_project,
        ),
        release=ReleaseConfig(
            auto_patch=auto_patch,
            propose_minor=propose_minor,
        ),
        simplicity=SimplicityConfig(
            enabled=simplicity_enabled,
            max_added_lines=max_added_lines,
            max_new_config_keys=max_new_config_keys,
            max_compat_markers=max_compat_markers,
        ),
        refactoring=RefactoringConfig(
            enabled=refactoring_enabled,
            budget_percent=refactor_budget_percent,
            allow_auto_targeted=allow_auto_targeted,
        ),
        git=GitConfig(
            provider=str(git.get("provider", "github")),
            auth=git_auth,
            org=git_org,
            base_branch=git_base,
            branch_prefix=git_prefix,
            draft_pr=git_draft,
            require_ci=git_require_ci,
            merge=git_merge,
            auto_revert_on_failure=git_revert,
        ),
    )
