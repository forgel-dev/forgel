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

import base64
import re
from pathlib import Path

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
        token = get_secret(home, "github.token")
        if token:
            return AuthReport(
                configured=True,
                detail="GitHub token from the environment or secret store",
            )
        return AuthReport(
            configured=False,
            detail=(
                "no GitHub token; public HTTPS clone works, SSH uses the "
                "host key, private repositories and push need a token"
            ),
        )

    def clone(self, remote: Remote, destination: Path, home: Path) -> None:
        token = get_secret(home, "github.token")
        if not token or not remote.url.startswith(("https://", "http://")):
            clone_repository(remote.url, destination)
            return
        encoded = base64.b64encode(
            f"x-access-token:{token}".encode("utf-8")
        ).decode("ascii")
        # Environment-scoped git config keeps the token out of the URL, argv
        # and .git/config.
        clone_repository(
            remote.url,
            destination,
            env={
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {encoded}",
            },
        )
