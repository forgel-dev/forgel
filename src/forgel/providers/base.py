"""Repository provider contract.

Hosting is pluggable: the core asks a provider to parse a URL, report its
authentication state and clone a repository. The first provider is GitHub; a
generic git provider covers SSH, public HTTPS and local paths.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

CLONE_TIMEOUT = 3600


class ProviderError(RuntimeError):
    """A repository cannot be parsed or cloned."""


@dataclass(frozen=True)
class Remote:
    url: str
    provider: str
    slug: str


@dataclass(frozen=True)
class AuthReport:
    configured: bool
    detail: str


def _credentialed(url: str) -> bool:
    """True when a URL embeds a password or an HTTPS token."""

    scheme, separator, rest = url.partition("://")
    if not separator:
        return False
    authority = rest.split("/", 1)[0]
    if "@" not in authority:
        return False
    userinfo = authority.split("@", 1)[0]
    if ":" in userinfo:
        return True
    return scheme in {"http", "https"}


def _slug_from_url(url: str) -> str:
    value = url.rstrip("/")
    if value.startswith("file://"):
        value = value[len("file://") :]
    value = value.split(":", 1)[-1] if value.startswith("git@") else value
    value = value.split("/")[-1]
    if value.endswith(".git"):
        value = value[:-4]
    return value or "repo"


def clone_repository(
    url: str,
    destination: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: int = CLONE_TIMEOUT,
) -> None:
    """Clone with prompts disabled, so a missing credential fails fast."""

    if (destination / ".git").exists():
        raise ProviderError(f"destination already contains a repository: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    merged = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if env:
        merged.update(env)
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--", url, str(destination)],
            capture_output=True,
            text=True,
            env=merged,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProviderError(f"git clone failed: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ProviderError(f"git clone failed: {detail}")
    if not (destination / ".git").exists():
        raise ProviderError(f"git clone produced no repository at {destination}")


class GitProvider:
    """SSH, public HTTPS and local paths; credentials are the host's job."""

    name = "git"

    def parse(self, url: str) -> Remote:
        url = url.strip()
        if not url:
            raise ProviderError("a repository URL is required")
        if _credentialed(url):
            raise ProviderError(
                "remove credentials from the URL and use the secret store"
            )
        local = url.startswith(("/", "./", "../", "file://"))
        return Remote(
            url=url,
            provider="local" if local else self.name,
            slug=_slug_from_url(url),
        )

    def auth(self, home: Path) -> AuthReport:
        return AuthReport(
            configured=False,
            detail=(
                "uses the host git configuration; public HTTPS needs no "
                "credentials and SSH uses the host key"
            ),
        )

    def clone(self, remote: Remote, destination: Path, home: Path) -> None:
        clone_repository(remote.url, destination)


def validate_url(url: str) -> None:
    """Reject obviously unsafe URL forms before a provider sees them."""

    if _credentialed(url):
        raise ProviderError(
            "remove credentials from the URL and use the secret store"
        )
    if re.search(r"\s", url):
        raise ProviderError("a repository URL must not contain whitespace")
