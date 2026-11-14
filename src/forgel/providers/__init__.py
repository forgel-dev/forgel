"""Repository provider registry."""

from __future__ import annotations

from .base import AuthReport, GitProvider, ProviderError, Remote, validate_url
from .github import GithubProvider


def get_provider(url: str) -> GitProvider | GithubProvider:
    value = url.strip().lower()
    if value.startswith(("git@github.com", "ssh://git@github.com")):
        return GithubProvider()
    if "github.com/" in value:
        return GithubProvider()
    if "/" in value and not value.startswith(("/", "./", "../", "file://")):
        parts = value.split("/")
        if (
            len(parts) == 2
            and parts[0]
            and parts[1]
            and ":" not in parts[0]
        ):
            # owner/repo shorthand resolves to GitHub.
            return GithubProvider()
    return GitProvider()


__all__ = [
    "AuthReport",
    "GitProvider",
    "GithubProvider",
    "ProviderError",
    "Remote",
    "get_provider",
    "validate_url",
]
