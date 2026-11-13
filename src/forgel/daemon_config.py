"""Daemon-level configuration.

Daemon settings live in ``$FORGEL_HOME/config.toml`` and are deliberately
separate from project configuration in ``forgel.toml``:

* daemon: polling cadence, worker concurrency, model endpoint;
* project: QA runtime, jurisdiction, model names, budget, release policy.

Secrets never live here; see :mod:`forgel.secrets`.
"""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any, Mapping

CONFIG_FILENAME = "config.toml"

DEFAULTS: dict[str, dict[str, Any]] = {
    "daemon": {"interval": 2.0},
    "telegram": {"poll_timeout": 25},
    "models": {"base_url": "https://api.deepseek.com/v1"},
}

# dotted key -> (kind, minimum, maximum)
SCHEMA: dict[str, tuple[str, float | None, float | None]] = {
    "daemon.interval": ("float", 0.1, 3600.0),
    "telegram.poll_timeout": ("int", 0, 50),
    "models.base_url": ("str", None, None),
}


class DaemonConfigError(RuntimeError):
    """A daemon setting is unknown or invalid."""


def config_path(home: Path) -> Path:
    return home / CONFIG_FILENAME


def _read_raw(home: Path) -> dict[str, Any]:
    path = config_path(home)
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DaemonConfigError(f"invalid {path.name}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def raw_config(home: Path) -> dict[str, Any]:
    return _read_raw(home)


def load_config(home: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {
        section: dict(values) for section, values in DEFAULTS.items()
    }
    for section, values in _read_raw(home).items():
        if not isinstance(values, dict):
            continue
        merged.setdefault(section, {}).update(values)
    return merged


def get_value(home: Path, key: str) -> Any:
    section, _, name = key.partition(".")
    return load_config(home).get(section, {}).get(name)


def value_source(home: Path, key: str) -> str:
    section, _, name = key.partition(".")
    raw = _read_raw(home)
    if isinstance(raw.get(section), dict) and name in raw[section]:
        return "daemon"
    return "default"


def parse_value(key: str, raw: str) -> Any:
    if key not in SCHEMA:
        raise DaemonConfigError(f"unknown daemon setting {key!r}")
    kind, minimum, maximum = SCHEMA[key]
    raw = raw.strip()
    if kind == "str":
        if not raw:
            raise DaemonConfigError("the value must not be empty")
        if key == "models.base_url" and not raw.startswith(
            ("http://", "https://")
        ):
            raise DaemonConfigError("models.base_url must start with http:// or https://")
        return raw
    try:
        value = float(raw) if kind == "float" else int(raw)
    except ValueError as exc:
        raise DaemonConfigError(f"{key} must be a {kind}") from exc
    if minimum is not None and value < minimum:
        raise DaemonConfigError(f"{key} must be at least {minimum:g}")
    if maximum is not None and value > maximum:
        raise DaemonConfigError(f"{key} must be at most {maximum:g}")
    return value


def _render(data: Mapping[str, Mapping[str, Any]]) -> str:
    sections: dict[str, list[str]] = {
        "daemon": [],
        "telegram": [],
        "models": [],
    }
    for section, name in (
        ("daemon", "interval"),
        ("telegram", "poll_timeout"),
        ("models", "base_url"),
    ):
        if name not in data.get(section, {}):
            continue
        value = data[section][name]
        if isinstance(value, str):
            literal = json.dumps(value)
        else:
            literal = repr(value)
        sections[section].append(f"{name} = {literal}")
    lines = [
        "# Forgel daemon configuration. Secrets live in secrets.toml.",
    ]
    for section in ("daemon", "telegram", "models"):
        if not sections[section]:
            continue
        lines.append("")
        lines.append(f"[{section}]")
        lines.extend(sections[section])
    return "\n".join(lines) + "\n"


def save_config(home: Path, data: Mapping[str, Mapping[str, Any]]) -> Path:
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".toml.tmp")
    temporary.write_text(_render(data), encoding="utf-8")
    os.replace(temporary, path)
    return path


def set_value(home: Path, key: str, raw: str) -> Path:
    value = parse_value(key, raw)
    section, _, name = key.partition(".")
    data: dict[str, Any] = {
        section_name: dict(values)
        for section_name, values in _read_raw(home).items()
        if isinstance(values, dict)
    }
    data.setdefault(section, {})[name] = value
    return save_config(home, data)
