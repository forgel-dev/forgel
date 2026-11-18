"""GitHub provider.

Self-host installations can clone public repositories without credentials. A
personal access token (or a deploy key over SSH) enables private repositories
and later push/pull-request operations. The token is read from the secret
store or the environment and is passed to git through environment-scoped
configuration, never through the URL or ``.git/config``.

A GitHub App installation token is the target production auth (D-049); the
PAT/deploy-key path is the M0.5 bootstrap.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import git_ops
from ..secrets import get_secret
from .base import (
    AuthReport,
    ProviderError,
    Remote,
    clone_repository,
    validate_url,
)

_GITHUB_RE = re.compile(
    r"github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


class GithubProvider:
    name = "github"

    def parse(self, url: str) -> Remote:
        value = url.strip()
        if not value:
            raise ProviderError("a repository URL is required")
        validate_url(value)
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            value = f"https://github.com/{value}.git"
        match = _GITHUB_RE.search(value)
        if match is None:
            raise ProviderError(f"not a GitHub repository URL: {url}")
        owner = match.group("owner")
        repo = match.group("repo")
        if value.startswith("git@"):
            canonical = f"git@github.com:{owner}/{repo}.git"
        elif value.startswith("ssh://"):
            canonical = f"ssh://git@github.com/{owner}/{repo}.git"
        else:
            canonical = f"https://github.com/{owner}/{repo}.git"
        validate_url(canonical)
        return Remote(
            url=canonical,
            provider=self.name,
            slug=f"{owner}/{repo}",
        )

    def auth(self, home: Path) -> AuthReport:
        from .github_auth import GithubAuth, GithubAuthError

        auth = GithubAuth(home)
        modes: list[str] = []
        try:
            if auth.app_ready():
                modes.append("GitHub App configured")
        except GithubAuthError as exc:
            modes.append(f"GitHub App misconfigured: {exc}")
        if auth.pat():
            modes.append("PAT configured")
        if auth.session_token():
            modes.append("GitHub CLI session available")
        detail = (
            ", ".join(modes)
            or "no API token (App, PAT or GitHub CLI session)"
        )
        detail += (
            "; git transport uses the host SSH key or HTTPS credential "
            "helper when no token is needed"
        )
        return AuthReport(configured=bool(modes), detail=detail)

    def clone(self, remote: Remote, destination: Path, home: Path) -> None:
        token = get_secret(home, "github.token")
        env = None
        if token and remote.url.startswith(("https://", "http://")):
            # Environment-scoped git config keeps the token out of the URL,
            # argv and .git/config.
            env = git_ops.auth_env(token)
        clone_repository(remote.url, destination, env=env)
