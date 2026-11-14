"""Local ``.env.local`` setup for the CLI client.

The local client does not need the deployment file (``.env.deploy``) and all
its SSH settings. ``forgel init`` writes ``.env.local`` in the current
repository; the client loads it automatically, together with a plain ``.env``
in the same directory and in the Forgel home.

Precedence, highest first:

1. the process environment;
2. ``./.env.local``;
3. ``./.env``;
4. ``$FORGEL_HOME/.env.local``;
5. ``$FORGEL_HOME/.env``.

Only ``FORGEL_*`` and ``TELEGRAM_*`` keys are loaded: a local file cannot
rewrite ``PATH`` or inject unrelated variables.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

FILES = (".env.local", ".env")
ALLOWED_PREFIXES = ("FORGEL_", "TELEGRAM_")
KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "env.local.example"


class LocalEnvError(RuntimeError):
    """A local environment file is malformed."""


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LocalEnvError(f"cannot read {path}: {exc}") from exc
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not KEY_PATTERN.fullmatch(key):
            raise LocalEnvError(
                f"{path}:{number}: expected KEY=VALUE, got {raw!r}"
            )
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_local_env(
    cwd: Path | None = None, home: Path | None = None
) -> list[Path]:
    """Load local files into ``os.environ`` without overriding the process."""

    directories: list[Path] = []
    if cwd is not None:
        directories.append(Path(cwd))
    if home is not None:
        directories.append(Path(home).expanduser())
    loaded: list[Path] = []
    for directory in directories:
        for name in FILES:
            path = directory / name
            if not path.is_file():
                continue
            values = parse_env_file(path)
            for key, value in values.items():
                if not key.startswith(ALLOWED_PREFIXES):
                    continue
                os.environ.setdefault(key, value)
            loaded.append(path)
    return loaded


def _gitignore_has(path: Path, entry: str) -> bool:
    if not path.exists():
        return False
    return any(
        line.strip() == entry
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def init_local_env(cwd: Path, force: bool = False) -> Path:
    """Write ``.env.local`` from the bundled template and ignore it in git."""

    cwd = Path(cwd)
    target = cwd / ".env.local"
    if target.exists() and not force:
        raise LocalEnvError(
            f"{target} already exists; edit it or run `forgel init --force`"
        )
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise LocalEnvError(f"cannot read the template: {exc}") from exc
    target.write_text(template, encoding="utf-8")
    gitignore = cwd / ".gitignore"
    if not _gitignore_has(gitignore, ".env.local"):
        prefix = ""
        if gitignore.exists():
            existing = gitignore.read_text(encoding="utf-8")
            prefix = "" if existing.endswith("\n") or not existing else "\n"
        with gitignore.open("a", encoding="utf-8") as handle:
            handle.write(f"{prefix}.env.local\n")
    return target
