"""Release a completed project: tags, provider releases and a manifest.

A release is the human-approved state of every repository. The core creates
and pushes the tag, then asks the provider for its release object when the
provider and an API token are available. Without an API token the tag is still
created and pushed; the result says that no provider release was made.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import git_ops, tasks
from .approvals import latest_approval, release_state
from .artifacts import write_json
from .layout import ProjectLayout
from .ledger import Ledger
from .program_manifest import entries as manifest_entries
from .providers import ProviderError, get_provider
from .providers.github import GithubProvider
from .providers.github_api import GithubAPIError
from .providers.github_auth import GithubAuth, GithubAuthError


class ReleaseError(RuntimeError):
    """The project cannot be released."""


@dataclass(frozen=True)
class RepoRelease:
    repo_id: str
    sha: str
    tag: str
    pushed: bool
    release_url: str
    detail: str


@dataclass(frozen=True)
class ReleaseResult:
    project_id: str
    version: str
    tag: str
    digest: str
    repos: list[RepoRelease] = field(default_factory=list)
    status: str = "tagged"
    manifest: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tag_name(version: str, generation: int) -> str:
    value = version.strip()
    if not value:
        return f"g{generation}"
    if re.fullmatch(r"\d+\.\d+\.\d+(?:[-+].*)?", value):
        return f"v{value}"
    return value


def _release_notes(
    project: Mapping[str, Any],
    version: str,
    generation: int,
    repos: Mapping[str, str],
    notes: str,
) -> str:
    body = notes.strip()
    lines = [
        f"Release {version} of {project.get('name') or project['id']} "
        f"({project['id']}), generation {generation}.",
        "",
        "Repositories:",
    ]
    lines.extend(f"- {repo_id}: {sha}" for repo_id, sha in repos.items())
    block = "\n".join(lines)
    return body + ("\n\n" + block if body else block)


def release_project(
    settings: Any,
    ledger: Ledger,
    project: Mapping[str, Any],
    version: str = "",
    notes: str = "",
    repo_id: str = "",
    draft: bool = False,
    prerelease: bool = False,
    generate_notes: bool = False,
    api: Any | None = None,
    log: Callable[[str], None] = print,
) -> ReleaseResult:
    """Create or push the release tag and the provider release objects."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    project_id = str(project["id"])
    generation = ledger.current_generation(project_id)
    tag = _tag_name(version, generation)
    selected = manifest_entries(layout)
    if repo_id:
        selected = [item for item in selected if item["id"] == repo_id]
        if not selected:
            raise ReleaseError(f"unknown repository {repo_id!r}")
    if not selected:
        raise ReleaseError("the project has no repositories to release")

    shas: dict[str, str] = {}
    repos: list[tuple[dict[str, Any], Path, str]] = []
    for entry in selected:
        repo = layout.repo_path(entry["id"])
        if not (repo / ".git").exists():
            raise ReleaseError(
                f"repository {entry['id']} has no git history at {repo}"
            )
        if git_ops.is_dirty(repo):
            raise ReleaseError(
                f"repository {entry['id']} has uncommitted changes; "
                "commit or stash them before releasing"
            )
        sha = git_ops.head_sha(repo)
        if not sha:
            raise ReleaseError(
                f"repository {entry['id']} has no commits to release"
            )
        shas[entry["id"]] = sha
        repos.append((dict(entry), repo, sha))

    auth: Any | None = None
    auth_detail = ""
    try:
        auth = GithubAuth(settings.home).resolve("auto")
    except GithubAuthError as exc:
        auth_detail = str(exc)
    body = _release_notes(
        project, tag, generation, shas, notes
    )
    results: list[RepoRelease] = []
    for entry, repo, sha in repos:
        entry_id = str(entry["id"])
        detail = ""
        pushed = False
        release_url = ""
        existing = git_ops.tag_sha(repo, tag)
        if existing and existing != sha:
            detail = (
                f"tag {tag} already exists at {existing}, not {sha}"
            )
            results.append(
                RepoRelease(
                    repo_id=entry_id,
                    sha=sha,
                    tag=tag,
                    pushed=False,
                    release_url="",
                    detail=detail,
                )
            )
            continue
        if not existing:
            try:
                git_ops.create_tag(
                    repo,
                    tag,
                    f"Release {tag} of {project.get('name') or project_id}",
                )
            except git_ops.GitOperationError as exc:
                detail = f"tag not created: {exc}"
                results.append(
                    RepoRelease(
                        repo_id=entry_id,
                        sha=sha,
                        tag=tag,
                        pushed=False,
                        release_url="",
                        detail=detail,
                    )
                )
                continue
        remote_url = entry.get("url") or git_ops.origin_url(repo)
        if remote_url:
            try:
                git_ops.push_tag(
                    repo,
                    tag,
                    auth.token if auth is not None else None,
                )
                pushed = True
            except git_ops.GitOperationError as exc:
                detail = f"tag created; push failed: {exc}"
        else:
            detail = "tag created; the repository has no remote"
        provider = get_provider(remote_url or "")
        if isinstance(provider, GithubProvider) and remote_url:
            full_name = provider.parse(remote_url).slug
            if auth is None:
                detail = (
                    detail
                    + ("; " if detail else "")
                    + f"no API token for a GitHub release: {auth_detail}"
                )
            else:
                try:
                    data = provider.release(
                        settings.home,
                        full_name,
                        tag,
                        sha,
                        name=f"{project.get('name') or project_id} {tag}",
                        body=body,
                        draft=draft,
                        prerelease=prerelease,
                        generate_notes=generate_notes,
                        api=api,
                        token=auth.token,
                    )
                    release_url = str(data.get("html_url", ""))
                    detail = "tag pushed; GitHub release created"
                except (
                    GithubAuthError,
                    GithubAPIError,
                    ProviderError,
                ) as exc:
                    detail = (
                        "tag pushed; GitHub release not created: "
                        f"{exc}"
                    )
        elif remote_url:
            detail = (
                detail + ("; " if detail else "")
                + "the provider has no release API"
            )
        results.append(
            RepoRelease(
                repo_id=entry_id,
                sha=sha,
                tag=tag,
                pushed=pushed,
                release_url=release_url,
                detail=detail or "tag created and pushed",
            )
        )

    released = sum(1 for item in results if item.release_url)
    pushed_count = sum(1 for item in results if item.pushed)
    if released == len(results):
        status = "released"
    elif released:
        status = "partial"
    elif pushed_count:
        status = "tagged"
    else:
        status = "failed"

    digest, _state = release_state(str(project["workspace"]))
    manifest_ref = f"docs/program/releases/{tag.replace('/', '-')}.json"
    staging = latest_approval(ledger, project_id, "staging", generation)
    production = latest_approval(
        ledger, project_id, "production", generation
    )
    write_json(
        layout.artifact(manifest_ref),
        {
            "version": tag,
            "project": project_id,
            "generation": generation,
            "digest": digest,
            "repos": {
                item.repo_id: {
                    "sha": item.sha,
                    "tag": item.tag,
                    "pushed": item.pushed,
                    "release": item.release_url,
                    "detail": item.detail,
                }
                for item in results
            },
            "notes": body,
            "staging_approval": staging,
            "production_approval": production,
            "created_at": _now(),
        },
    )
    tasks.commit_control(layout, f"Release {tag}")
    ledger.append_event(
        project_id,
        "release",
        status=status,
        idempotency_key=f"{project_id}:release:{tag}",
        artifact_refs=[manifest_ref],
        payload={
            "version": tag,
            "digest": digest,
            "repos": {
                item.repo_id: item.release_url or item.detail
                for item in results
            },
            "status": status,
        },
        generation=generation,
    )
    log(
        f"[release] {project_id}: {tag} {status} "
        f"({released}/{len(results)} provider release(s))"
    )
    return ReleaseResult(
        project_id=project_id,
        version=tag,
        tag=tag,
        digest=digest,
        repos=results,
        status=status,
        manifest=manifest_ref,
    )
