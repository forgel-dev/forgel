"""GitHub publish flow: branch, push, pull request, checks, merge.

The flow is deliberately conservative: it never pushes to the base branch,
never force-pushes, and auto-merges only when checks are green (or when the
project explicitly disables the CI requirement). Every publish writes a report
in the control repository and a ledger event.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import git_ops
from .artifacts import write_text
from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger
from .i18n import t as _t
from .program_manifest import entries as manifest_entries
from .project_config import GitConfig, load_project_config
from .providers.github import GithubProvider
from .providers.github_api import (
    GithubAPI,
    GithubAPIError,
    wait_for_checks,
)
from .providers.github_auth import DEFAULT_API_BASE, AuthToken, GithubAuth


class GithubFlowError(RuntimeError):
    """The publish or merge flow cannot continue safely."""


@dataclass(frozen=True)
class PublishResult:
    project_id: str
    repo_id: str
    full_name: str
    branch: str
    base: str
    pr_number: int
    pr_url: str
    checks: str
    merged: bool
    merge_sha: str
    status: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _slug(value: str) -> str:
    return (
        re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:40]
        or "change"
    )


def _git_config(layout: ProjectLayout) -> GitConfig:
    try:
        config = load_project_config(layout.control)
    except Exception:  # noqa: BLE001 - defaults are safe for the flow
        config = None
    return config.git if config is not None else GitConfig()


def _select_entry(
    layout: ProjectLayout,
    repo_id: str,
    full_name_override: str,
) -> dict[str, Any]:
    repos = manifest_entries(layout)
    if repo_id:
        entry = next((item for item in repos if item["id"] == repo_id), None)
        if entry is None:
            known = ", ".join(item["id"] for item in repos) or "none"
            raise GithubFlowError(
                f"unknown repository {repo_id!r}; known: {known}"
            )
        if (
            not full_name_override
            and entry.get("provider") != "github"
            and "github.com" not in entry.get("url", "")
        ):
            raise GithubFlowError(
                f"repository {repo_id} is not a GitHub repository"
            )
        return entry
    github = [
        item
        for item in repos
        if full_name_override
        or item.get("provider") == "github"
        or "github.com" in item["url"]
    ]
    if not github:
        raise GithubFlowError("the project has no GitHub repositories")
    if len(github) > 1:
        ids = ", ".join(item["id"] for item in github)
        raise GithubFlowError(
            f"several GitHub repositories; choose one: {ids}"
        )
    return github[0]


def _full_name(entry: dict[str, Any], override: str) -> str:
    if override:
        provider = GithubProvider()
        remote = provider.parse(override)
        return remote.slug
    try:
        remote = GithubProvider().parse(entry["url"])
    except Exception as exc:  # noqa: BLE001 - convert to a flow error
        raise GithubFlowError(str(exc)) from exc
    return remote.slug


def _client(
    settings: Settings,
    git_config: GitConfig,
    auth: AuthToken | None,
    api: Any | None,
) -> tuple[Any, AuthToken, str, str]:
    auth_client: GithubAuth | None = None
    if auth is None:
        auth_client = GithubAuth(settings.home)
        auth = auth_client.resolve(git_config.auth)
    api_base = (
        auth_client.api_base
        if auth_client is not None
        else DEFAULT_API_BASE
    )
    client = api or GithubAPI(auth.token, api_base=api_base)
    return client, auth, api_base, auth.token


def _control_commit(layout: ProjectLayout, message: str) -> None:
    control = layout.control
    if not (control / ".git").exists():
        return
    subprocess.run(
        ["git", "add", "-A"], cwd=control, capture_output=True, check=False
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Forgel",
            "-c",
            "user.email=forgel@localhost",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=control,
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "tag", "-f", "forgel-baseline"],
        cwd=control,
        capture_output=True,
        check=False,
    )


def _record(
    layout: ProjectLayout,
    ledger: Ledger,
    project_id: str,
    entry: dict[str, Any],
    result: PublishResult,
) -> None:
    report = layout.artifact("docs/program/git/report.md")
    header = """# Git Report

Pull requests published by Forgel. The ledger is the runtime source.

"""
    text = report.read_text(encoding="utf-8") if report.exists() else header
    if not text.endswith("\n"):
        text += "\n"
    block = f"""## {_now()}

- Project: `{project_id}`
- Repository: `{entry['id']}` ({result.full_name})
- Branch: `{result.branch}` → `{result.base}`
- Pull request: #{result.pr_number} {result.pr_url}
- Checks: `{result.checks}`
- Merged: `{str(result.merged).lower()}` ({result.merge_sha or '—'})
- Status: `{result.status}`

"""
    write_text(report, text + block)
    _control_commit(layout, f"Record GitHub publish for {entry['id']}")
    generation = ledger.current_generation(project_id)
    ref = str(report.relative_to(layout.root))
    ledger.append_event(
        project_id,
        "github",
        status=result.status,
        idempotency_key=(
            f"{project_id}:github:{entry['id']}:{result.pr_number}:"
            f"{result.status}:{result.checks}"
        ),
        artifact_refs=[ref],
        payload={
            "repo": entry["id"],
            "full_name": result.full_name,
            "branch": result.branch,
            "base": result.base,
            "pr_number": result.pr_number,
            "pr_url": result.pr_url,
            "checks": result.checks,
            "merged": result.merged,
            "merge_sha": result.merge_sha,
            "status": result.status,
        },
        generation=generation,
    )


def _prepare_branch(
    local: Path,
    base: str,
    branch: str,
    title: str,
    commit_message: str,
    token: str | None,
    git_config: GitConfig,
) -> tuple[str, bool]:
    """Return the working branch and whether a local commit was created."""

    fetch(local, token)
    if not git_ops.ref_exists(local, f"origin/{base}"):
        raise GithubFlowError(
            f"base branch origin/{base} was not found after fetch; check "
            "git.base_branch"
        )
    current = git_ops.current_branch(local)
    dirty = git_ops.is_dirty(local)
    if branch and current != base and branch != current:
        if git_ops.branch_exists(local, branch):
            git_ops.checkout(local, branch)
            current = branch
            dirty = git_ops.is_dirty(local)
        else:
            raise GithubFlowError(
                f"current branch is {current!r}; switch to {branch!r} "
                "manually or publish from the base branch"
            )

    if current == base:
        if dirty and not commit_message:
            raise GithubFlowError(
                "the working tree has uncommitted changes; commit them or "
                "pass a commit message"
            )
        ahead = git_ops.commits_since(local, f"origin/{base}")
        if not dirty and ahead == 0:
            raise GithubFlowError(
                "nothing to publish: the branch has no commits ahead of "
                f"origin/{base}"
            )
        working = branch or (
            f"{git_config.branch_prefix}{_stamp()}-"
            f"{_slug(title or git_ops.last_commit_subject(local))}"
        )
        if git_ops.branch_exists(local, working):
            working += f"-{int(time.time()) % 10000}"
        git_ops.create_branch(local, working)
    else:
        working = current
        if dirty and not commit_message:
            raise GithubFlowError(
                "the working tree has uncommitted changes; commit them or "
                "pass a commit message"
            )

    committed = False
    if git_ops.is_dirty(local) and commit_message:
        git_ops.commit_all(local, commit_message)
        committed = True

    if git_ops.commits_since(local, f"origin/{base}") == 0:
        raise GithubFlowError(
            "nothing to publish: the branch has no commits ahead of "
            f"origin/{base}"
        )

    if not git_ops.is_ancestor(local, f"origin/{base}", "HEAD"):
        git_ops.rebase(local, f"origin/{base}", token)
    return working, committed


def fetch(local: Path, token: str | None) -> None:
    git_ops.fetch(local, token)


def publish(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str = "",
    title: str = "",
    body: str = "",
    base_branch: str = "",
    branch: str = "",
    commit_message: str = "",
    wait: bool = True,
    merge: str = "",
    check_timeout: float = 300.0,
    api: Any | None = None,
    auth: AuthToken | None = None,
    full_name_override: str = "",
    log: Callable[[str], None] = print,
) -> PublishResult:
    layout = ProjectLayout.detect(project["workspace"])
    git_config = _git_config(layout)
    entry = _select_entry(layout, repo_id, full_name_override)
    full_name = _full_name(entry, full_name_override)
    owner = full_name.split("/", 1)[0]
    local = layout.repo_path(entry["id"])
    if not (local / ".git").exists():
        raise GithubFlowError(
            f"repository {entry['id']} has no git history at {local}"
        )
    remote_url = entry.get("url") or git_ops.origin_url(local)
    if not remote_url:
        raise GithubFlowError("the repository has no remote URL")
    git_ops.ensure_remote(local, remote_url)

    client, auth_token, _api_base, git_token = _client(
        settings, git_config, auth, api
    )
    git_token = git_token if git_ops.is_https(remote_url) else None
    base = base_branch or git_config.base_branch
    working, _committed = _prepare_branch(
        local,
        base,
        branch,
        title,
        commit_message,
        git_token,
        git_config,
    )
    git_ops.push(local, working, git_token)
    sha = git_ops.head_sha(local)

    pr = client.find_open_pull(
        full_name, head=f"{owner}:{working}", base=base
    )
    if pr is None:
        title = title or git_ops.last_commit_subject(local) or (
            f"Forgel: {working}"
        )
        body = body or "Published by Forgel."
        try:
            pr = client.create_pull(
                full_name,
                head=f"{owner}:{working}",
                base=base,
                title=title,
                body=body,
                draft=git_config.draft_pr,
            )
        except GithubAPIError as exc:
            raise GithubFlowError(str(exc)) from exc
    number = int(pr.get("number", 0))
    pr_url = str(pr.get("html_url", ""))

    checks = (
        wait_for_checks(
            client,
            full_name,
            sha,
            timeout=check_timeout,
            log=log,
        )
        if wait
        else client.check_state(full_name, sha)
    )
    merge_mode = merge or git_config.merge
    if merge_mode not in {"auto", "human"}:
        raise GithubFlowError(f"unknown merge mode {merge_mode!r}")

    merged = bool(pr.get("merged", False))
    merge_sha = ""
    status = "pr_open"
    if merge_mode == "auto" and not merged:
        if checks.state == "failed":
            status = "checks_failed"
        elif checks.state == "pending":
            status = "checks_pending"
        elif checks.state == "none" and git_config.require_ci:
            status = "no_ci"
        else:
            try:
                if pr.get("draft"):
                    client.mark_ready(full_name, number)
                result = client.merge_pull(full_name, number)
                merged = bool(result.get("merged", False))
                merge_sha = str(result.get("sha", ""))
                status = "merged" if merged else "merge_failed"
            except GithubAPIError as exc:
                status = "merge_failed"
                log(f"[github] merge failed: {exc}")

    outcome = PublishResult(
        project_id=str(project["id"]),
        repo_id=str(entry["id"]),
        full_name=full_name,
        branch=working,
        base=base,
        pr_number=number,
        pr_url=pr_url,
        checks=checks.state,
        merged=merged,
        merge_sha=merge_sha,
        status=status,
    )
    _record(layout, ledger, str(project["id"]), entry, outcome)
    return outcome


def merge_pr(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str = "",
    number: int | None = None,
    base_branch: str = "",
    branch: str = "",
    wait: bool = True,
    check_timeout: float = 300.0,
    require_ci: bool | None = None,
    api: Any | None = None,
    auth: AuthToken | None = None,
    full_name_override: str = "",
    log: Callable[[str], None] = print,
) -> PublishResult:
    layout = ProjectLayout.detect(project["workspace"])
    git_config = _git_config(layout)
    entry = _select_entry(layout, repo_id, full_name_override)
    full_name = _full_name(entry, full_name_override)
    local = layout.repo_path(entry["id"])
    client, _auth_token, _api_base, _git_token = _client(
        settings, git_config, auth, api
    )
    base = base_branch or git_config.base_branch
    if number is None:
        working = branch or git_ops.current_branch(local)
        owner = full_name.split("/", 1)[0]
        pr = client.find_open_pull(
            full_name, head=f"{owner}:{working}", base=base
        )
        if pr is None:
            raise GithubFlowError(
                f"no open pull request for {working!r} into {base!r}"
            )
    else:
        pr = client.get_pull(full_name, number)
    pr_number = int(pr.get("number", number or 0))
    pr_url = str(pr.get("html_url", ""))
    head_sha = str(pr.get("head", {}).get("sha", ""))
    if not head_sha:
        raise GithubFlowError("cannot determine the pull request head SHA")
    checks = (
        wait_for_checks(
            client, full_name, head_sha, timeout=check_timeout, log=log
        )
        if wait
        else client.check_state(full_name, head_sha)
    )
    required = (
        git_config.require_ci if require_ci is None else require_ci
    )
    result: dict[str, Any] = {}
    if checks.state == "failed":
        status = "checks_failed"
        merged = False
    elif checks.state == "pending":
        status = "checks_pending"
        merged = False
    elif checks.state == "none" and required:
        status = "no_ci"
        merged = False
    else:
        if pr.get("draft"):
            client.mark_ready(full_name, pr_number)
        result = client.merge_pull(full_name, pr_number)
        merged = bool(result.get("merged", False))
        status = "merged" if merged else "merge_failed"
    merge_sha = str(result.get("sha", "")) if merged else ""
    outcome = PublishResult(
        project_id=str(project["id"]),
        repo_id=str(entry["id"]),
        full_name=full_name,
        branch=str(pr.get("head", {}).get("ref", branch)),
        base=base,
        pr_number=pr_number,
        pr_url=pr_url,
        checks=checks.state,
        merged=merged,
        merge_sha=merge_sha,
        status=status,
    )
    _record(layout, ledger, str(project["id"]), entry, outcome)
    return outcome


def status_text(
    settings: Settings,
    project: dict[str, Any],
    lang: str = "en",
) -> str:
    layout = ProjectLayout.detect(project["workspace"])
    git_config = _git_config(layout)
    auth = GithubAuth(settings.home)
    lines = [
        _t(lang, "github_status_project", project=project["id"]),
        _t(lang, "github_status_auth", auth=auth.status()),
        _t(lang, "github_status_merge", policy=git_config.merge),
        _t(
            lang,
            "github_status_base",
            branch=git_config.base_branch,
        ),
        _t(
            lang,
            "github_status_ci",
            value=str(git_config.require_ci).lower(),
        ),
        _t(lang, "github_status_repositories"),
    ]
    repos = manifest_entries(layout)
    if not repos:
        lines.append(_t(lang, "github_status_none"))
        return "\n".join(lines)
    for entry in repos:
        local = layout.repo_path(entry["id"])
        branch = "?"
        dirty = "?"
        if (local / ".git").exists():
            try:
                branch = git_ops.current_branch(local)
                dirty = _t(
                    lang,
                    "github_status_dirty"
                    if git_ops.is_dirty(local)
                    else "github_status_clean",
                )
            except Exception:  # noqa: BLE001 - status must not crash
                branch = _t(lang, "github_status_detached")
        depends = ", ".join(entry["depends_on"]) or _t(
            lang, "github_status_depends_none"
        )
        lines.append(
            _t(
                lang,
                "github_status_entry",
                id=entry["id"],
                provider=entry["provider"],
                url=entry["url"] or "—",
                branch=branch,
                worktree=dirty,
                depends=depends,
            )
        )
    return "\n".join(lines)
