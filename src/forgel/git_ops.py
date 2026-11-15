"""Git operations for the pull-request flow.

No force-push, no direct push to the base branch. Authentication is passed to
git through environment-scoped configuration, so a token never appears in the
URL, argv or ``.git/config``.
"""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
SECRET_NAMES = {".env", "secrets.toml", "id_rsa", "id_ed25519"}


class GitOperationError(RuntimeError):
    """A git command failed or the operation is unsafe."""


def _run(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if env:
        merged.update(env)
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=merged,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitOperationError(f"git {' '.join(args)} failed: {exc}") from exc


def _ok(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = _run(repo, *args, env=env)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitOperationError(f"git {' '.join(args)} failed: {detail}")
    return result


def auth_env(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    encoded = base64.b64encode(
        f"x-access-token:{token}".encode("utf-8")
    ).decode("ascii")
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {encoded}",
    }


def is_https(url: str) -> bool:
    return url.startswith(("https://", "http://"))


def current_branch(repo: Path) -> str:
    result = _ok(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branch = result.stdout.strip()
    if not branch or branch == "HEAD":
        raise GitOperationError("HEAD is detached; check out a branch first")
    return branch


def is_dirty(repo: Path) -> bool:
    return bool(_ok(repo, "status", "--porcelain").stdout.strip())


def head_sha(repo: Path) -> str:
    return _ok(repo, "rev-parse", "HEAD").stdout.strip()


def status_paths(repo: Path) -> list[str]:
    result = _run(repo, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) <= 3:
            continue
        value = line[3:].strip().strip('"')
        if " -> " in value:
            value = value.split(" -> ", 1)[1].strip('"')
        paths.append(value)
    return paths


def tag_baseline(repo: Path) -> None:
    _ok(repo, "tag", "-f", "forgel-baseline")


def origin_url(repo: Path) -> str:
    result = _run(repo, "remote", "get-url", "origin")
    return result.stdout.strip() if result.returncode == 0 else ""


def _normalize_remote(url: str) -> str:
    return url.rstrip("/").removesuffix(".git")


def ensure_remote(repo: Path, url: str) -> None:
    existing = origin_url(repo)
    if not existing:
        _ok(repo, "remote", "add", "origin", url)
        return
    if _normalize_remote(existing) != _normalize_remote(url):
        raise GitOperationError(
            f"origin is {existing!r}, expected {url!r}; refusing to push to "
            "a different repository"
        )


def fetch(repo: Path, token: str | None = None) -> None:
    env = auth_env(token) if is_https(origin_url(repo)) else None
    _ok(repo, "fetch", "--prune", "origin", env=env)


def branch_exists(repo: Path, name: str) -> bool:
    result = _run(repo, "show-ref", "--verify", f"refs/heads/{name}")
    return result.returncode == 0


def ref_exists(repo: Path, ref: str) -> bool:
    result = _run(repo, "rev-parse", "--verify", "--quiet", ref)
    return result.returncode == 0


def create_branch(repo: Path, name: str) -> None:
    if branch_exists(repo, name):
        raise GitOperationError(
            f"branch {name!r} already exists; check it out instead"
        )
    _ok(repo, "checkout", "-b", name)


def checkout(repo: Path, name: str) -> None:
    if not branch_exists(repo, name):
        raise GitOperationError(f"branch {name!r} does not exist")
    _ok(repo, "checkout", name)


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = _run(repo, "merge-base", "--is-ancestor", ancestor, descendant)
    if result.returncode not in {0, 1}:
        raise GitOperationError(
            f"cannot compare {ancestor} and {descendant}: "
            f"{result.stderr.strip()}"
        )
    return result.returncode == 0


def rebase(repo: Path, upstream: str, token: str | None = None) -> None:
    env = auth_env(token) if is_https(origin_url(repo)) else None
    result = _run(repo, "rebase", upstream, env=env)
    if result.returncode != 0:
        _run(repo, "rebase", "--abort")
        detail = (result.stderr or result.stdout).strip()
        raise GitOperationError(
            "upstream moved and the rebase has conflicts; resolve it "
            f"manually and publish again. {detail}"
        )


def staged_files(repo: Path) -> list[str]:
    result = _run(repo, "diff", "--cached", "--name-only")
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def secret_like(paths: list[str]) -> list[str]:
    suspicious: list[str] = []
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if name == ".env.example":
            continue
        if (
            name in SECRET_NAMES
            or name.startswith((".env.", "id_rsa", "id_ed25519"))
            or name.endswith(SECRET_SUFFIXES)
        ):
            suspicious.append(path)
    return suspicious


def commit_all(repo: Path, message: str) -> str:
    _ok(repo, "add", "-A")
    staged = staged_files(repo)
    if not staged:
        return head_sha(repo)
    suspicious = secret_like(staged)
    if suspicious:
        raise GitOperationError(
            "refusing to commit files that look like secrets: "
            + ", ".join(suspicious)
        )
    _ok(
        repo,
        "-c",
        "user.name=Forgel",
        "-c",
        "user.email=forgel@localhost",
        "commit",
        "-s",
        "-q",
        "-m",
        message,
    )
    return head_sha(repo)


def commit_paths(repo: Path, paths: list[str], message: str) -> str:
    """Commit only the given paths, leaving other worktree changes alone."""

    existing = [item for item in paths if item]
    if not existing:
        return head_sha(repo)
    suspicious = secret_like(existing)
    if suspicious:
        raise GitOperationError(
            "refusing to commit files that look like secrets: "
            + ", ".join(suspicious)
        )
    _ok(repo, "add", "--", *existing)
    result = _run(
        repo,
        "-c",
        "user.name=Forgel",
        "-c",
        "user.email=forgel@localhost",
        "commit",
        "-s",
        "-q",
        "-m",
        message,
        "--",
        *existing,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).lower()
        if "nothing to commit" not in detail and "no changes added" not in detail:
            raise GitOperationError(
                "commit failed: " + (result.stderr or result.stdout).strip()
            )
    return head_sha(repo)


def push(repo: Path, branch: str, token: str | None = None) -> None:
    env = auth_env(token) if is_https(origin_url(repo)) else None
    result = _run(
        repo, "push", "--set-upstream", "origin", branch, env=env
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitOperationError(
            f"push failed (no force-push is attempted): {detail}"
        )


def last_commit_subject(repo: Path) -> str:
    result = _run(repo, "log", "-1", "--format=%s")
    return result.stdout.strip() if result.returncode == 0 else ""


def commits_since(repo: Path, ref: str) -> int:
    result = _run(repo, "rev-list", "--count", f"{ref}..HEAD")
    try:
        return int(result.stdout.strip()) if result.returncode == 0 else 0
    except ValueError:
        return 0
