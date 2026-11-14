"""Effective configuration and validated edits.

Two layers, one view:

* project: ``forgel.toml`` in the project's control directory;
* daemon: ``$FORGEL_HOME/config.toml``.

Only whitelisted keys can be changed from the chat gateway. Every write is
validated by parsing the file again; an invalid value restores the previous
file content.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from . import daemon_config, peak
from .project_config import (
    VALID_GIT_AUTH,
    VALID_GIT_MERGE,
    BudgetConfig,
    ConfigError,
    GitConfig,
    JurisdictionConfig,
    ModelsConfig,
    ProjectConfig,
    QAConfig,
    RefactoringConfig,
    ReleaseConfig,
    SimplicityConfig,
    load_project_config,
)
from .toml_edit import set_value, toml_literal

PROJECT_KINDS: dict[str, str] = {
    "qa.runtime": "runtime",
    "jurisdiction.pack": "str",
    "models.default": "str",
    "models.architecture": "str",
    "models.peak_policy": "peak",
    "budget.per_feature_usd": "float",
    "budget.per_project_usd": "float",
    "release.auto_patch": "bool",
    "release.propose_minor": "bool",
    "simplicity.enabled": "bool",
    "simplicity.max_added_lines": "int",
    "simplicity.max_new_config_keys": "int",
    "simplicity.max_compat_markers": "int",
    "refactoring.enabled": "bool",
    "refactoring.budget_percent": "int",
    "refactoring.allow_auto_targeted": "bool",
    "git.base_branch": "str",
    "git.branch_prefix": "str",
    "git.auth": "auth",
    "git.merge": "merge",
    "git.require_ci": "bool",
    "git.draft_pr": "bool",
    "git.auto_revert_on_failure": "bool",
}


def _default_config() -> ProjectConfig:
    return ProjectConfig(
        name=None,
        recipe=None,
        qa=QAConfig(),
        jurisdiction=JurisdictionConfig(),
        models=ModelsConfig(),
        budget=BudgetConfig(),
        release=ReleaseConfig(),
        simplicity=SimplicityConfig(),
        refactoring=RefactoringConfig(),
        git=GitConfig(),
    )


def project_values(control: Path) -> dict[str, Any]:
    config = load_project_config(control) or _default_config()
    return {
        "qa.runtime": config.qa.runtime,
        "jurisdiction.pack": config.jurisdiction.pack,
        "models.default": config.models.default,
        "models.architecture": config.models.architecture,
        "models.peak_policy": config.models.peak_policy,
        "budget.per_feature_usd": config.budget.per_feature_usd,
        "budget.per_project_usd": config.budget.per_project_usd,
        "release.auto_patch": config.release.auto_patch,
        "release.propose_minor": config.release.propose_minor,
        "simplicity.enabled": config.simplicity.enabled,
        "simplicity.max_added_lines": config.simplicity.max_added_lines,
        "simplicity.max_new_config_keys": config.simplicity.max_new_config_keys,
        "simplicity.max_compat_markers": config.simplicity.max_compat_markers,
        "refactoring.enabled": config.refactoring.enabled,
        "refactoring.budget_percent": config.refactoring.budget_percent,
        "refactoring.allow_auto_targeted": (
            config.refactoring.allow_auto_targeted
        ),
        "git.base_branch": config.git.base_branch,
        "git.branch_prefix": config.git.branch_prefix,
        "git.auth": config.git.auth,
        "git.merge": config.git.merge,
        "git.require_ci": config.git.require_ci,
        "git.draft_pr": config.git.draft_pr,
        "git.auto_revert_on_failure": config.git.auto_revert_on_failure,
    }


def _raw_project(control: Path) -> dict[str, Any]:
    path = control / "forgel.toml"
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def project_source(control: Path, key: str) -> str:
    section, _, name = key.partition(".")
    raw = _raw_project(control)
    if isinstance(raw.get(section), dict) and name in raw[section]:
        return "project"
    return "default"


def _parse_float(key: str, raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number") from exc
    if value < 0:
        raise ConfigError(f"{key} must be non-negative")
    return value


def _parse_int(key: str, raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer") from exc
    if value < 0:
        raise ConfigError(f"{key} must be non-negative")
    return value


def parse_project_value(key: str, raw: str) -> Any:
    kind = PROJECT_KINDS.get(key)
    if kind is None:
        raise ConfigError(f"unknown project setting {key!r}")
    raw = raw.strip()
    if kind == "runtime":
        if raw not in {"auto", "docker", "local"}:
            raise ConfigError("qa.runtime must be auto, docker or local")
        return raw
    if kind == "auth":
        if raw not in VALID_GIT_AUTH:
            raise ConfigError(
                f"{key} must be one of {sorted(VALID_GIT_AUTH)}"
            )
        return raw
    if kind == "merge":
        if raw not in VALID_GIT_MERGE:
            raise ConfigError(
                f"{key} must be one of {sorted(VALID_GIT_MERGE)}"
            )
        return raw
    if kind == "peak":
        lowered = raw.lower()
        if lowered not in peak.POLICIES:
            raise ConfigError(
                f"{key} must be one of {sorted(peak.POLICIES)}"
            )
        return lowered
    if kind == "bool":
        lowered = raw.lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        raise ConfigError(f"{key} must be true or false")
    if kind == "int":
        return _parse_int(key, raw)
    if kind == "float":
        return _parse_float(key, raw)
    if not raw:
        raise ConfigError(f"{key} must not be empty")
    return raw


def set_project_value(control: Path, key: str, raw: str) -> Any:
    path = control / "forgel.toml"
    if not path.exists():
        raise ConfigError("this project has no forgel.toml yet")
    value = parse_project_value(key, raw)
    section, _, name = key.partition(".")
    previous = path.read_text(encoding="utf-8")
    set_value(path, section, name, toml_literal(value))
    try:
        load_project_config(control)
    except ConfigError:
        path.write_text(previous, encoding="utf-8")
        raise
    return value


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def effective_view(home: Path, control: Path | None) -> str:
    lines = ["Project settings:"]
    if control is None:
        lines.append("  no project selected (use /use <id>)")
    else:
        values = project_values(control)
        for key in PROJECT_KINDS:
            source = project_source(control, key)
            lines.append(
                f"  {key} = {format_value(values[key])} ({source})"
            )
    lines.append("")
    lines.append("Daemon settings:")
    for key in daemon_config.SCHEMA:
        value = daemon_config.get_value(home, key)
        source = daemon_config.value_source(home, key)
        lines.append(f"  {key} = {format_value(value)} ({source})")
    return "\n".join(lines)
