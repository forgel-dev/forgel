"""Secret storage for the daemon.

Environment variables win over the local file. The file exists for the MVP
convenience of setting a key from the chat gateway; it is written with mode
``0600`` and is never read into an artifact or a log.

Telegram bots have no end-to-end encryption: a secret sent to a bot still
passes through Telegram's cloud. The gateway deletes the message immediately,
but the operator must treat this as a convenience, not a cryptographic
guarantee. Use ``forgel secret set`` over SSH or environment variables in
production.
"""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Mapping

SECRET_KEYS: dict[str, tuple[str, ...]] = {
    "telegram.bot_token": ("TELEGRAM_BOT_TOKEN",),
    "model.api_key": ("FORGEL_MODEL_API_KEY",),
    "github.token": ("FORGEL_GITHUB_TOKEN", "GITHUB_TOKEN"),
    "github.app_id": ("FORGEL_GITHUB_APP_ID", "GITHUB_APP_ID"),
    "github.app_private_key": ("FORGEL_GITHUB_APP_PRIVATE_KEY",),
}

SECRETS_FILENAME = "secrets.toml"


class SecretError(RuntimeError):
    """A secret cannot be stored or is not in the known set."""


def secrets_path(home: Path) -> Path:
    return home / SECRETS_FILENAME


def _read_file(home: Path) -> dict[str, str]:
    path = secrets_path(home)
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    values: dict[str, str] = {}
    for section, entries in data.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            if isinstance(value, str):
                values[f"{section}.{key}"] = value
    return values


def get_secret(
    home: Path,
    key: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return a secret from the environment first, then the file."""

    env = environ if environ is not None else os.environ
    for name in SECRET_KEYS.get(key, ()):
        value = env.get(name, "").strip()
        if value:
            return value
    return _read_file(home).get(key, "")


def secret_status(
    home: Path, environ: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Return ``env``, ``file`` or ``missing`` for every known secret."""

    env = environ if environ is not None else os.environ
    stored = _read_file(home)
    status: dict[str, str] = {}
    for key, env_names in SECRET_KEYS.items():
        if any(env.get(name, "").strip() for name in env_names):
            status[key] = "env"
        elif stored.get(key):
            status[key] = "file"
        else:
            status[key] = "missing"
    return status


def _render(values: dict[str, str]) -> str:
    lines = [
        "# Forgel secrets. Never commit this file.",
        "# Values in the environment override this file.",
    ]
    sections: dict[str, list[tuple[str, str]]] = {}
    for key, value in values.items():
        section, _, name = key.partition(".")
        sections.setdefault(section, []).append((name, value))
    for section in sorted(sections):
        lines.append("")
        lines.append(f"[{section}]")
        for name, value in sorted(sections[section]):
            lines.append(f"{name} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def _write(home: Path, values: dict[str, str]) -> Path:
    path = secrets_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".toml.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(_render(values))
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return path


def set_secret(home: Path, key: str, value: str) -> Path:
    if key not in SECRET_KEYS:
        raise SecretError(f"unknown secret {key!r}")
    value = value.strip()
    if not value:
        raise SecretError("the value must not be empty")
    if any(char in value for char in "\r\n"):
        raise SecretError("the value must be a single line")
    values = _read_file(home)
    values[key] = value
    return _write(home, values)


def delete_secret(home: Path, key: str) -> bool:
    if key not in SECRET_KEYS:
        raise SecretError(f"unknown secret {key!r}")
    values = _read_file(home)
    if key not in values:
        return False
    del values[key]
    _write(home, values)
    return True
