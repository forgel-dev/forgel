"""Release trains: one user request becomes a versioned release per repository.

A release is the unit the user cares about: they asked for a change, the
planner split it into tasks, and when every task is accepted the runtime audits
the change set as a whole and publishes one version in each repository the
request touched. Repositories release independently: a request that only
touches one repository creates one version, a request across several
repositories creates one release train with a version per repository.

The version comes from the repository itself. Tags or a ``CHANGELOG.md`` set
the base; without history the first release is ``0.1.0``. A patch increments
the patch number, a minor release the minor number, and a major release is
only meaningful from ``1.0.0`` onward (the first product release); before that
a breaking change is still a minor release.

Everything the runtime writes is an artifact in git: the release plan and the
audit live in the project control repository, the changelog and the release
record live in the released repository.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import git_ops, tasks
from .artifacts import write_json, write_text
from .config import Settings
from .instructions import instruction_context
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    build_model_client,
    project_model_name,
)
from .model_output import json_objects
from .program_manifest import entries as manifest_entries
from .presets import (
    PresetError,
    find_preset,
    load_presets,
    write_paths,
    write_version,
)
from .providers import ProviderError, get_provider
from .providers.github import GithubProvider
from .providers.github_api import GithubAPIError
from .providers.github_auth import GithubAuth, GithubAuthError

RELEASES_DIR = "docs/program/releases"
REPO_RELEASES_DIR = "releases"
CHANGELOG = "CHANGELOG.md"
INITIAL_VERSION = "0.1.0"
MAX_AUDIT_ROUNDS = 2
MAX_FIX_FINDINGS = 3
RELEASE_RETRY_SECONDS = 60
MAX_DIFF_CHARS = 60_000
MAX_STAT_CHARS = 8_000
RELEASE_CLASSES = {"patch", "minor", "major"}
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
CHANGELOG_SECTION = re.compile(
    r"^##\s+\[?v?(\d+\.\d+\.\d+(?:[-+][^\]]*)?)\]?", re.MULTILINE
)

CHANGELOG_HEADER = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""

AUDIT_PROMPT = """You audit a completed release before it is published.
Judge the change set as a whole, not task by task.

Check:
- the requirements of the user's request against what the tasks changed;
- regressions in existing behaviour and cross-repository contracts;
- security defects, leaked secrets, unsafe input and authorization;
- data migrations, destructive operations and rollback;
- tests and evidence: a criterion is passed only when its command or review
  evidence is present.

A finding is blocking only when shipping it would break the product, lose or
leak data, break a contract or leave a required check unverified. Style and
optional improvements are non-blocking. Use only the evidence in the context;
never invent a file, a result or a decision.

Return exactly one JSON object:
{"verdict": "pass" | "fail",
 "summary": "what the audit concluded",
 "findings": [
   {"severity": "critical" | "major" | "minor",
    "repo_id": "one repository from the change set",
    "issue": "the concrete defect",
    "suggestion": "how to fix it"}
 ]}
"""


class ReleaseError(RuntimeError):
    """The release cannot be planned or published."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _retry_at() -> str:
    return (
        datetime.now(timezone.utc)
        + timedelta(seconds=RELEASE_RETRY_SECONDS)
    ).isoformat(timespec="seconds")


def _due(moment: str) -> bool:
    return not moment or moment <= _now()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "release"


def new_release_id(title: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{stamp}_{_slug(title)}"


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = SEMVER.match(str(value or "").strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _format(version: tuple[int, int, int]) -> str:
    return "%d.%d.%d" % version


def discover_base(repo: Path) -> tuple[str | None, str]:
    """The last released version of a repository and where it came from."""

    versions: list[tuple[int, int, int]] = []
    sources: list[str] = []
    if (repo / ".git").exists():
        for tag in git_ops.tags(repo):
            parsed = parse_version(tag)
            if parsed is not None:
                versions.append(parsed)
                sources.append(f"tag {tag}")
    changelog = repo / CHANGELOG
    if changelog.is_file():
        try:
            text = changelog.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for match in CHANGELOG_SECTION.finditer(text):
            line_end = text.find("\n", match.start())
            line = text[
                match.start() : line_end if line_end >= 0 else len(text)
            ]
            if "unreleased" in line.lower():
                continue
            parsed = parse_version(match.group(1))
            if parsed is not None:
                versions.append(parsed)
                sources.append(f"changelog {match.group(1)}")
    if not versions:
        return None, "no release history"
    latest = max(versions)
    return _format(latest), sources[-1] if sources else "release history"


def discover_planned(repo: Path) -> str:
    """A version the repository already marks as ``Unreleased``."""

    changelog = repo / CHANGELOG
    if not changelog.is_file():
        return ""
    try:
        text = changelog.read_text(encoding="utf-8")
    except OSError:
        return ""
    planned: list[tuple[int, int, int]] = []
    for match in CHANGELOG_SECTION.finditer(text):
        line_end = text.find("\n", match.start())
        line = text[
            match.start() : line_end if line_end >= 0 else len(text)
        ]
        if "unreleased" not in line.lower():
            continue
        parsed = parse_version(match.group(1))
        if parsed is not None:
            planned.append(parsed)
    return _format(max(planned)) if planned else ""


def _preset_id(
    settings: Settings | None,
    repo: Path,
    entry: Mapping[str, Any],
) -> str:
    if settings is None:
        return ""
    try:
        preset = find_preset(
            load_presets(settings.registry_path), repo, entry
        )
    except PresetError:
        return ""
    return preset.id if preset is not None else ""


def _version_after(base: str | None, planned: str, release_class: str) -> str:
    kind = str(release_class or "").strip().lower()
    if kind == "major":
        current = parse_version(base or "")
        if current is None or current < (1, 0, 0):
            return "1.0.0"
    if planned:
        current = parse_version(base or "")
        target = parse_version(planned)
        if target is not None and (current is None or target > current):
            return planned
    return next_version(base, release_class)


def next_version(base: str | None, release_class: str) -> str:
    """The next version for a release class.

    No history: the first release is 0.1.0. Before 1.0.0 a major release is the
    first product release and becomes 1.0.0; after that a major release opens a
    new major line.
    """

    kind = str(release_class or "").strip().lower()
    if kind not in RELEASE_CLASSES:
        kind = "minor"
    parsed = parse_version(base or "")
    if parsed is None:
        return INITIAL_VERSION
    major, minor, patch = parsed
    if kind == "major":
        if (major, minor, patch) < (1, 0, 0):
            return "1.0.0"
        return "%d.0.0" % (major + 1)
    if kind == "minor":
        return "%d.%d.0" % (major, minor + 1)
    return "%d.%d.%d" % (major, minor, patch + 1)


def release_dir(layout: ProjectLayout, release_id: str) -> Path:
    return layout.artifact(f"{RELEASES_DIR}/{release_id}")


def release_path(
    layout: ProjectLayout, release_id: str, name: str
) -> Path:
    return release_dir(layout, release_id) / name


def release_tasks(
    layout: ProjectLayout, release_id: str
) -> list[dict[str, Any]]:
    return [
        task
        for task in tasks.list_tasks(layout)
        if str(task.get("release_id") or "") == release_id
    ]


def load_release(
    layout: ProjectLayout, release_id: str
) -> dict[str, Any] | None:
    path = release_path(layout, release_id, "release.json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_releases(layout: ProjectLayout) -> list[dict[str, Any]]:
    root = layout.artifact(RELEASES_DIR)
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/release.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("id"):
            items.append(data)
    return items


def save_release(
    layout: ProjectLayout,
    release: dict[str, Any],
) -> None:
    write_json(
        release_path(layout, str(release["id"]), "release.json"),
        release,
    )
    write_text(
        release_path(layout, str(release["id"]), "plan.md"),
        render_plan(release, release_tasks(layout, str(release["id"]))),
    )


def _repo_tasks(
    release: Mapping[str, Any], tasks_list: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in tasks_list:
        repo_id = str(task.get("repo_id") or "")
        if not repo_id:
            continue
        grouped.setdefault(repo_id, []).append(task)
    return grouped


def render_plan(
    release: Mapping[str, Any],
    tasks_list: list[dict[str, Any]],
) -> str:
    grouped = _repo_tasks(release, tasks_list)
    repo_lines: list[str] = []
    for repo_id, items in grouped.items():
        repo = dict((release.get("repos") or {}).get(repo_id) or {})
        base = str(repo.get("base_version") or "")
        version = str(repo.get("version") or "")
        status = str(repo.get("status") or "pending")
        line = f"- `{repo_id}` — {status}"
        if repo.get("preset"):
            line += f", preset {repo['preset']}"
        if base:
            line += f", base {base}"
        if version:
            line += f", releases {version}"
        elif repo.get("planned_version"):
            line += f", planned {repo['planned_version']}"
        repo_lines.append(line)
    task_lines = "\n".join(
        f"- `{task.get('id')}` — {task.get('title')} "
        f"({task.get('repo_id') or '—'}, {task.get('status')})"
        for task in tasks_list
    )
    audit = dict(release.get("audit") or {})
    return f"""# Release plan {release.get('id')}

- Project: `{release.get('project')}`
- Request: {release.get('title')}
- Class: {release.get('release_class')}
- Status: {release.get('status')}
- Created: {release.get('created_at')}
{'- Plan: `' + str(release.get('plan_id')) + '`' if release.get('plan_id') else ''}

## Request

{release.get('request') or '—'}

## Repositories

{chr(10).join(repo_lines) or '- none'}

## Tasks

{task_lines or '- none'}

## Audit

- Rounds: {audit.get('rounds', 0)}
- Verdict: {audit.get('verdict') or 'not run'}
- Report: `{audit.get('report') or '—'}`
"""


def plan_release(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release_id: str,
    title: str,
    request: str,
    release_class: str,
    task_items: list[dict[str, Any]],
    plan_id: str = "",
    ledger: Ledger | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Create the release plan for a user request and its tasks."""

    kind = str(release_class or "").strip().lower()
    if kind not in RELEASE_CLASSES:
        kind = "minor"
    grouped = _repo_tasks({}, task_items)
    entries = {
        str(entry["id"]): entry for entry in manifest_entries(layout)
    }
    repos: dict[str, dict[str, Any]] = {}
    for repo_id in grouped:
        repo = layout.repo_path(repo_id)
        base_sha = ""
        if (repo / ".git").exists():
            try:
                base_sha = git_ops.head_sha(repo)
            except git_ops.GitOperationError:
                base_sha = ""
        base_version, source = discover_base(repo)
        repos[repo_id] = {
            "base_sha": base_sha,
            "base_version": base_version or "",
            "base_source": source,
            "preset": _preset_id(
                settings, repo, entries.get(repo_id, {})
            ),
            "planned_version": next_version(base_version, kind),
            "version": "",
            "status": "pending",
            "tag": "",
            "sha": "",
            "release": "",
            "detail": "",
        }
    release = {
        "id": release_id,
        "project": project["id"],
        "title": title.strip() or request.strip()[:80],
        "request": request.strip(),
        "release_class": kind,
        "plan_id": plan_id,
        "created_at": _now(),
        "status": "planned",
        "tasks": [str(task["id"]) for task in task_items],
        "repos": repos,
        "audit": {
            "rounds": 0,
            "verdict": "",
            "summary": "",
            "report": "",
            "task_ids": [],
        },
        "control_push": {},
        "finalized_at": "",
        "detail": "",
    }
    save_release(layout, release)
    try:
        tasks.commit_control(layout, f"Release plan {release_id}")
    except Exception:  # noqa: BLE001 - a commit must not undo the plan
        pass
    if ledger is not None:
        ledger.append_event(
            str(project["id"]),
            "release_plan",
            status="completed",
            idempotency_key=f"{project['id']}:release:{release_id}:plan",
            artifact_refs=[
                f"{RELEASES_DIR}/{release_id}/plan.md"
            ],
            payload={
                "release": release_id,
                "class": kind,
                "tasks": release["tasks"],
                "repos": list(repos),
            },
            generation=ledger.current_generation(str(project["id"])),
        )
    return release


def _accepted(task: Mapping[str, Any]) -> bool:
    result = task.get("result") or {}
    acceptance = result.get("acceptance") or {}
    return str(acceptance.get("status") or "") == "accepted"


TERMINAL_RELEASE_STATUSES = {
    "released",
    "tagged",
    "cancelled",
}


def release_repo_ids(
    layout: ProjectLayout, release: Mapping[str, Any]
) -> set[str]:
    repos = {str(key) for key in (release.get("repos") or {})}
    for task in release_tasks(layout, str(release["id"])):
        repo_id = str(task.get("repo_id") or "")
        if repo_id:
            repos.add(repo_id)
    return repos


def blocking_release(
    layout: ProjectLayout,
    repo_id: str,
    release_id: str = "",
) -> dict[str, Any] | None:
    """An earlier unfinished release that owns the same repository."""

    for release in list_releases(layout):
        current = str(release["id"])
        if release_id and current >= release_id:
            break
        status = str(release.get("status") or "")
        if status in TERMINAL_RELEASE_STATUSES:
            continue
        if repo_id in release_repo_ids(layout, release):
            return release
    return None


def eligible_pending_task(
    layout: ProjectLayout, now: Any = None
) -> dict[str, Any] | None:
    """The first pending task whose repository has no earlier open release."""

    tasks_list = tasks.list_tasks(layout)
    statuses = {
        str(task["id"]): str(task.get("status") or "")
        for task in tasks_list
    }
    for task in tasks_list:
        if task.get("status") != "pending":
            continue
        if tasks._dependency_blockers(task, statuses):
            continue
        if not tasks._retry_ready(task, now):
            continue
        release_id = str(task.get("release_id") or "")
        repo_id = str(task.get("repo_id") or "")
        if release_id and repo_id:
            if blocking_release(layout, repo_id, release_id):
                continue
        return task
    return None


def attach_blocked_release(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    task: dict[str, Any],
) -> str:
    """Reopen a blocked release for the task's repository instead of a new one."""

    repo_id = str(task.get("repo_id") or "")
    if not repo_id:
        return ""
    for release in list_releases(layout):
        if str(release.get("status") or "") != "blocked":
            continue
        if repo_id not in release_repo_ids(layout, release):
            continue
        if blocking_release(layout, repo_id, str(release["id"])):
            continue
        task_id = str(task["id"])
        release.setdefault("repos", {}).setdefault(
            repo_id,
            {
                "base_sha": "",
                "base_version": "",
                "base_source": "",
                "version": "",
                "status": "pending",
                "tag": "",
                "sha": "",
                "release": "",
                "detail": "",
            },
        )
        task_ids = list(release.get("tasks") or [])
        if task_id not in task_ids:
            task_ids.append(task_id)
        release["tasks"] = task_ids
        release["status"] = "running"
        release["detail"] = ""
        release["next_at"] = ""
        audit = dict(release.get("audit") or {})
        audit["rounds"] = 0
        audit["verdict"] = ""
        release["audit"] = audit
        save_release(layout, release)
        tasks.update_task(
            layout,
            task_id,
            release_id=str(release["id"]),
            release_class=str(release.get("release_class") or "patch"),
        )
        try:
            tasks.commit_control(
                layout, f"Attach task {task_id} to release {release['id']}"
            )
        except Exception:  # noqa: BLE001 - a commit must not undo the attach
            pass
        return str(release["id"])
    return ""


def _primary_repo(
    grouped: Mapping[str, list[dict[str, Any]]],
) -> str:
    if not grouped:
        return ""
    return max(grouped, key=lambda key: len(grouped[key]))


def _repo_diff(
    layout: ProjectLayout,
    release: Mapping[str, Any],
    repo_id: str,
) -> str:
    repo = layout.repo_path(repo_id)
    if not (repo / ".git").exists():
        return "(no git history)"
    recorded = dict((release.get("repos") or {}).get(repo_id) or {})
    items = [
        task
        for task in release_tasks(layout, str(release["id"]))
        if str(task.get("repo_id") or "") == repo_id
    ]
    base = ""
    for task in items:
        git = (task.get("result") or {}).get("git") or {}
        base = str(git.get("base") or "")
        if base:
            commits = [
                str(item) for item in (git.get("commits") or [])
            ]
            if not commits and git.get("commit"):
                commits = [str(git["commit"])]
            # A rework records the previous attempt's head as its base; when
            # that base is the task's own first commit, the release must
            # start from that commit's parent to include the whole change.
            if commits and base == commits[0]:
                base = f"{commits[0]}^"
            break
    if not base:
        base = str(recorded.get("base_sha") or "")
    if not base:
        return "(no base revision recorded)"
    try:
        head = git_ops.head_sha(repo)
    except git_ops.GitOperationError as exc:
        return f"(cannot read HEAD: {exc})"
    stat = git_ops.diff(repo, base, head, stat=True)
    diff = git_ops.diff(repo, base, head)
    stat = stat[:MAX_STAT_CHARS]
    if len(diff) > MAX_DIFF_CHARS:
        diff = (
            diff[:MAX_DIFF_CHARS]
            + "\n... [diff truncated; inspect the repository]"
        )
    return f"base {base}..{head}\n\nStat:\n{stat or '(empty)'}\n\nDiff:\n{diff or '(empty)'}"


def _audit_observation(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release: Mapping[str, Any],
    items: list[dict[str, Any]],
) -> str:
    grouped = _repo_tasks(release, items)
    task_rows = []
    for task in items:
        result = task.get("result") or {}
        qa = result.get("qa") or {}
        review = result.get("review") or {}
        task_rows.append(
            {
                "id": task.get("id"),
                "title": task.get("title"),
                "repo_id": task.get("repo_id"),
                "spec": task.get("spec"),
                "summary": task.get("summary"),
                "requirements": list(task.get("requirements") or []),
                "acceptance": list(task.get("acceptance") or []),
                "files_changed": list(result.get("files_changed") or []),
                "qa": {"status": qa.get("status")},
                "review": {
                    "status": review.get("status"),
                    "summary": review.get("summary"),
                },
                "test_output": result.get("test_output"),
            }
        )
    return json.dumps(
        {
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "brief": project.get("brief"),
            },
            "release": {
                "id": release.get("id"),
                "title": release.get("title"),
                "request": release.get("request"),
                "class": release.get("release_class"),
            },
            "tasks": task_rows,
            "repositories": {
                repo_id: _repo_diff(layout, release, repo_id)
                for repo_id in grouped
            },
            "instructions": instruction_context(layout),
        },
        ensure_ascii=False,
        indent=2,
    )


def _parse_audit(raw: str) -> dict[str, Any]:
    for item in reversed(json_objects(raw)):
        if "verdict" in item:
            verdict = str(item.get("verdict") or "").lower()
            if verdict in {"pass", "fail"}:
                findings = item.get("findings")
                return {
                    "verdict": verdict,
                    "summary": str(item.get("summary") or "").strip(),
                    "findings": [
                        dict(finding)
                        for finding in (findings or [])
                        if isinstance(finding, dict)
                    ],
                }
    raise ValueError("the auditor returned no verdict")


def _render_audit(
    release: Mapping[str, Any], audit: Mapping[str, Any]
) -> str:
    findings = audit.get("findings") or []
    lines = "\n".join(
        "- [{severity}] {repo}: {issue}{suggestion}".format(
            severity=item.get("severity") or "minor",
            repo=item.get("repo_id") or "—",
            issue=item.get("issue") or "—",
            suggestion=(
                " — " + str(item.get("suggestion"))
                if item.get("suggestion")
                else ""
            ),
        )
        for item in findings
    )
    return f"""# Release audit {release.get('id')}

- Round: {audit.get('rounds')}
- Verdict: {audit.get('verdict')}
- At: {audit.get('at')}

## Summary

{audit.get('summary') or '—'}

## Findings

{lines or '- none'}
"""


def audit_release(
    settings: Settings,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release: dict[str, Any],
    items: list[dict[str, Any]],
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> bool:
    """Run the whole-change-set audit. Returns True when the release passes."""

    audit = dict(release.get("audit") or {})
    audit["rounds"] = int(audit.get("rounds") or 0) + 1
    audit["task_ids"] = [str(task["id"]) for task in items]
    audit["at"] = _now()
    if client is None:
        audit["verdict"] = "skipped"
        audit["summary"] = (
            "no model is configured for the release audit; "
            "the release is not published without an audit"
        )
        release["audit"] = audit
        release["status"] = "blocked"
        release["detail"] = audit["summary"]
        save_release(layout, release)
        log(f"[release] {release['id']}: audit requires a model")
        return False
    messages = [
        ModelMessage("system", AUDIT_PROMPT),
        ModelMessage(
            "user",
            _audit_observation(layout, project, release, items)
            + "\n\nReturn the audit JSON now.",
        ),
    ]
    try:
        raw = client.complete(
            messages,
            model=project_model_name(layout.control),
        )
        parsed = _parse_audit(raw)
    except (ModelError, ValueError) as exc:
        audit["verdict"] = "error"
        audit["summary"] = f"the audit could not run: {exc}"
        release["audit"] = audit
        if int(audit["rounds"]) >= MAX_AUDIT_ROUNDS:
            release["status"] = "blocked"
            release["detail"] = audit["summary"]
        save_release(layout, release)
        log(f"[release] {release['id']}: audit error: {exc}")
        return False
    audit.update(parsed)
    audit["at"] = _now()
    report = f"{RELEASES_DIR}/{release['id']}/audit.md"
    write_text(
        release_path(layout, str(release["id"]), "audit.md"),
        _render_audit(release, audit),
    )
    audit["report"] = report
    release["audit"] = audit
    blocking = [
        finding
        for finding in audit.get("findings") or []
        if str(finding.get("severity") or "").lower()
        in {"critical", "major"}
    ]
    if audit["verdict"] == "pass":
        release["status"] = "ready"
        save_release(layout, release)
        log(f"[release] {release['id']}: audit passed")
        return True
    if (
        audit["rounds"] < MAX_AUDIT_ROUNDS
        and blocking
        and _queue_fix_tasks(layout, release, items, blocking, log)
    ):
        release["status"] = "running"
        save_release(layout, release)
        return False
    release["status"] = "blocked"
    release["detail"] = audit.get("summary") or "the audit failed"
    save_release(layout, release)
    log(f"[release] {release['id']}: audit blocked the release")
    return False


def _queue_fix_tasks(
    layout: ProjectLayout,
    release: dict[str, Any],
    items: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    log: Callable[[str], None],
) -> bool:
    grouped = _repo_tasks(release, items)
    known = {str(entry["id"]) for entry in manifest_entries(layout)}
    existing = {
        str(task.get("title") or "")
        for task in release_tasks(layout, str(release["id"]))
    }
    created = 0
    for finding in findings[:MAX_FIX_FINDINGS]:
        issue = str(finding.get("issue") or "").strip()
        if not issue:
            continue
        repo_id = str(finding.get("repo_id") or "").strip()
        if repo_id not in grouped or repo_id not in known:
            repo_id = _primary_repo(grouped)
        if not repo_id:
            continue
        title = "Release audit: " + issue[:80]
        if title in existing:
            continue
        suggestion = str(finding.get("suggestion") or "").strip()
        task = tasks.create_task(
            layout,
            title,
            [issue],
            [
                f"The release audit finding is resolved: {issue}",
                "Existing tests pass",
            ],
            repo_id=repo_id,
            summary=suggestion or issue,
            release_id=str(release["id"]),
            release_class=str(release.get("release_class") or "patch"),
            plan_goal=str(release.get("title") or ""),
        )
        existing.add(title)
        task_ids = list(release.get("tasks") or [])
        if str(task["id"]) not in task_ids:
            task_ids.append(str(task["id"]))
        release["tasks"] = task_ids
        created += 1
        log(
            f"[release] {release['id']}: queued fix task "
            f"{task['id']} for {repo_id}"
        )
    return bool(created)


def _prepend_changelog(
    repo: Path,
    version: str,
    section: str,
    entries: list[str] | None = None,
    subsection: str = "",
) -> None:
    path = repo / CHANGELOG
    if not path.exists():
        write_text(path, CHANGELOG_HEADER + "\n" + section)
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = CHANGELOG_HEADER + "\n"
    heading = re.compile(
        rf"^##\s+\[{re.escape(version)}\]", re.MULTILINE
    ).search(text)
    if heading is not None:
        start = heading.start()
        end = text.find("\n## [", start + len(heading.group(0)))
        if end < 0:
            end = len(text)
        existing = text[start:end]
        first_break = existing.find("\n")
        if first_break < 0:
            first_break = len(existing)
        heading_line = existing[:first_break]
        if "unreleased" in heading_line.lower():
            heading_line = f"## [{version}] - {_today()}"
        body = existing[first_break + 1 :]
        missing = [
            line
            for line in (entries or [])
            if line.strip() and line.strip() not in body
        ]
        if missing:
            marker = f"### {subsection}" if subsection else ""
            if marker and marker in body:
                position = body.index(marker) + len(marker)
                next_section = body.find("\n### ", position)
                if next_section < 0:
                    next_section = len(body)
                before = body[:next_section].rstrip()
                body = (
                    before
                    + "\n"
                    + "\n".join(missing)
                    + "\n"
                    + body[next_section:]
                )
            else:
                extra = (
                    f"### {subsection}\n\n" if subsection else ""
                )
                body = (
                    body.rstrip()
                    + "\n\n"
                    + extra
                    + "\n".join(missing)
                    + "\n"
                )
        updated = heading_line + "\n" + body
        text = text[:start] + updated + text[end:]
        write_text(path, text)
        return
    match = CHANGELOG_SECTION.search(text)
    if match:
        text = text[: match.start()] + section + "\n\n" + text[match.start() :]
    else:
        text = text.rstrip() + "\n\n" + section
    write_text(path, text)


def _changelog_parts(
    release: Mapping[str, Any], version: str, items: list[dict[str, Any]]
) -> tuple[str, list[str], str]:
    title = "Added"
    if str(release.get("release_class") or "") == "patch":
        title = "Fixed"
    elif str(release.get("release_class") or "") == "major":
        title = "Changed"
    lines: list[str] = []
    for task in items:
        summary = str(task.get("summary") or "").strip()
        line = f"- {task.get('title')}"
        if summary:
            line += f" — {summary}"
        else:
            requirements = list(task.get("requirements") or [])
            if requirements:
                line += " (" + "; ".join(requirements[:3]) + ")"
        lines.append(line)
    section = (
        f"## [{version}] - {_today()}\n\n"
        f"### {title}\n\n"
        + "\n".join(lines or ["- Release."])
        + "\n"
    )
    return section, lines, title


def _changelog_section(
    release: Mapping[str, Any], version: str, items: list[dict[str, Any]]
) -> str:
    return _changelog_parts(release, version, items)[0]


def _repo_plan(
    release: Mapping[str, Any],
    repo_id: str,
    version: str,
    items: list[dict[str, Any]],
    preset_id: str = "",
    version_files: list[str] | None = None,
) -> str:
    staged = "\n".join(
        f"- {task.get('title')} (`{task.get('id')}`, "
        f"{task.get('status')})"
        for task in items
    )
    files = ", ".join(f"`{path}`" for path in (version_files or []))
    return f"""# Release plan {version}

- Repository: `{repo_id}`
- Project: `{release.get('project')}`
- Release train: `{release.get('id')}`
- Request: {release.get('title')}
- Class: {release.get('release_class')}
- Preset: {preset_id or 'none'}
- Version files: {files or 'none'}
- Created: {release.get('created_at')}

## What is included

{staged or '- none'}

## Artifacts

- Changelog: `CHANGELOG.md`
- Release record: `releases/{version}/release.md`
"""


def _repo_record(
    release: Mapping[str, Any],
    version: str,
    items: list[dict[str, Any]],
    release_url: str,
    preset_id: str = "",
    version_files: list[str] | None = None,
) -> str:
    staged = "\n".join(
        f"- {task.get('title')} (`{task.get('id')}`)"
        for task in items
    )
    files = ", ".join(f"`{path}`" for path in (version_files or []))
    return f"""# Release {version}

- Tag: `v{version}`
- Date: {_today()}
- Project: `{release.get('project')}`
- Release train: `{release.get('id')}`
- Preset: {preset_id or 'none'}
- Version files: {files or 'none'}
- GitHub release: {release_url or 'pending'}

## Tasks

{staged or '- none'}
"""


def _push_repo(settings: Settings, path: Path) -> dict[str, str]:
    if not (path / ".git").exists():
        return {"status": "skipped", "detail": "no git history"}
    remote = git_ops.origin_url(path)
    if not remote:
        return {"status": "skipped", "detail": "no remote"}
    try:
        branch = git_ops.current_branch(path)
    except git_ops.GitOperationError as exc:
        return {
            "status": "failed",
            "detail": f"cannot determine the branch: {exc}",
        }
    token: str | None = None
    if git_ops.is_https(remote):
        try:
            token = GithubAuth(settings.home).resolve("auto").token
        except GithubAuthError:
            token = None
    try:
        git_ops.push(path, branch, token)
    except git_ops.GitOperationError as exc:
        return {"status": "failed", "detail": str(exc)}
    return {"status": "pushed", "branch": branch, "detail": ""}


def _provider_release(
    settings: Settings,
    release: Mapping[str, Any],
    project: Mapping[str, Any],
    entry: Mapping[str, Any],
    repo: Path,
    tag: str,
    sha: str,
    body: str,
) -> tuple[str, str]:
    remote = str(entry.get("url") or "").strip()
    if not remote:
        remote = git_ops.origin_url(repo)
    if not remote:
        return "", "no remote for a provider release"
    try:
        provider = get_provider(remote)
    except ProviderError as exc:
        return "", str(exc)
    if not isinstance(provider, GithubProvider):
        return "", "the provider has no release API"
    try:
        full_name = provider.parse(remote).slug
    except ProviderError as exc:
        return "", str(exc)
    try:
        auth = GithubAuth(settings.home).resolve("auto")
    except GithubAuthError as exc:
        return "", f"no API token for a GitHub release: {exc}"
    try:
        data = provider.release(
            settings.home,
            full_name,
            tag,
            sha,
            name=f"{project.get('name') or project['id']} {tag}",
            body=body,
            token=auth.token,
        )
    except (GithubAuthError, GithubAPIError, ProviderError) as exc:
        return "", f"GitHub release not created: {exc}"
    return str(data.get("html_url") or ""), ""


def _finalize_repo(
    settings: Settings,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release: dict[str, Any],
    repo_id: str,
    entry: Mapping[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    repo = layout.repo_path(repo_id)
    result = dict((release.get("repos") or {}).get(repo_id) or {})
    if str(result.get("status") or "") == "released":
        return result
    if not (repo / ".git").exists():
        result.update(
            {"status": "failed", "detail": "repository has no git history"}
        )
        return result
    base_version, source = discover_base(repo)
    try:
        preset_list = load_presets(settings.registry_path)
    except PresetError as exc:
        result.update(
            {"status": "failed", "detail": f"preset: {exc}"}
        )
        return result
    version = str(result.get("version") or "")
    if not version:
        planned = discover_planned(repo)
        version = _version_after(
            base_version,
            planned,
            str(release.get("release_class") or "minor"),
        )
        result["version"] = version
        result["base_version"] = base_version or ""
        result["base_source"] = source
        if planned:
            result["planned_version"] = planned
    try:
        preset_paths = write_paths(
            preset_list, repo, entry, version
        )
    except PresetError as exc:
        result.update(
            {"status": "failed", "detail": f"preset: {exc}"}
        )
        return result
    tag = f"v{version}"
    allowed = {
        CHANGELOG,
        f"{REPO_RELEASES_DIR}/{version}/plan.md",
        f"{REPO_RELEASES_DIR}/{version}/release.md",
        *preset_paths,
    }
    dirty = [
        path
        for path in git_ops.status_paths(repo)
        if path not in allowed
    ]
    if dirty:
        result.update(
            {
                "status": "failed",
                "detail": "uncommitted changes: " + ", ".join(dirty[:10]),
            }
        )
        return result
    try:
        preset_id, version_files = write_version(
            preset_list, repo, entry, version
        )
    except PresetError as exc:
        result.update(
            {"status": "failed", "detail": f"preset: {exc}"}
        )
        return result
    result["preset"] = preset_id
    result["version_files"] = version_files
    section, entries, subsection = _changelog_parts(
        release, version, items
    )
    _prepend_changelog(
        repo, version, section, entries, subsection
    )
    write_text(
        repo / REPO_RELEASES_DIR / version / "plan.md",
        _repo_plan(
            release,
            repo_id,
            version,
            items,
            preset_id,
            version_files,
        ),
    )
    write_text(
        repo / REPO_RELEASES_DIR / version / "release.md",
        _repo_record(
            release,
            version,
            items,
            "",
            preset_id,
            version_files,
        ),
    )
    sha = git_ops.commit_all(repo, f"Release v{version}")
    result["sha"] = sha
    result["tag"] = tag
    existing = git_ops.tag_sha(repo, tag)
    if existing and existing != sha:
        result.update(
            {
                "status": "failed",
                "detail": f"tag {tag} already exists at {existing}, not {sha}",
            }
        )
        return result
    if not existing:
        try:
            git_ops.create_tag(
                repo,
                tag,
                f"Release {tag} of {project.get('name') or project['id']}",
            )
        except git_ops.GitOperationError as exc:
            result.update(
                {"status": "failed", "detail": f"tag not created: {exc}"}
            )
            return result
    remote = git_ops.origin_url(repo)
    if not remote:
        result.update(
            {
                "status": "tagged",
                "release": "",
                "detail": "tag created; the repository has no remote",
            }
        )
        return result
    pushed = _push_repo(settings, repo)
    try:
        git_ops.push_tag(
            repo,
            tag,
            GithubAuth(settings.home).resolve("auto").token
            if git_ops.is_https(remote)
            else None,
        )
    except (git_ops.GitOperationError, GithubAuthError) as exc:
        result.update(
            {
                "status": "failed",
                "detail": f"tag created; push failed: {exc}",
            }
        )
        return result
    if pushed.get("status") != "pushed":
        result.update(
            {
                "status": "failed",
                "detail": f"branch push failed: {pushed.get('detail')}",
            }
        )
        return result
    url, detail = _provider_release(
        settings, release, project, entry, repo, tag, sha, section
    )
    if url:
        write_text(
            repo / REPO_RELEASES_DIR / version / "release.md",
            _repo_record(
                release,
                version,
                items,
                url,
                str(result.get("preset") or ""),
                list(result.get("version_files") or []),
            ),
        )
        try:
            git_ops.commit_all(repo, f"Record release v{version}")
            git_ops.push(repo, pushed.get("branch", ""))
        except git_ops.GitOperationError as exc:
            detail = f"release record commit failed: {exc}"
    result.update(
        {
            "status": "released" if url else "tagged",
            "release": url,
            "detail": detail,
        }
    )
    return result


def finalize_release(
    settings: Settings,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release: dict[str, Any],
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Publish the release in every repository it touched."""

    release["status"] = "finalizing"
    save_release(layout, release)
    items = release_tasks(layout, str(release["id"]))
    grouped = _repo_tasks(release, items)
    entries = {str(entry["id"]): entry for entry in manifest_entries(layout)}
    results: dict[str, dict[str, Any]] = {}
    for repo_id, repo_items in grouped.items():
        entry = entries.get(repo_id)
        if entry is None:
            results[repo_id] = {
                "status": "failed",
                "detail": "unknown repository",
            }
            continue
        results[repo_id] = _finalize_repo(
            settings, layout, project, release, repo_id, entry, repo_items
        )
        save_release(layout, release)
        log(
            f"[release] {release['id']}: {repo_id} "
            f"{results[repo_id].get('status')}"
        )
    release["repos"] = {
        **dict(release.get("repos") or {}),
        **results,
    }
    statuses = {str(item.get("status") or "") for item in results.values()}
    if statuses and statuses <= {"released"}:
        status = "released"
    elif statuses and statuses <= {"released", "tagged"}:
        status = "tagged"
    elif statuses & {"released", "tagged"}:
        status = "partial"
    else:
        status = "failed"
    release["status"] = status
    release["finalized_at"] = _now()
    release["next_at"] = (
        _retry_at() if status in {"partial", "failed"} else ""
    )
    report = f"{RELEASES_DIR}/{release['id']}/release.md"
    write_text(
        release_path(layout, str(release["id"]), "release.md"),
        _render_release_record(release),
    )
    save_release(layout, release)
    tasks.commit_control(layout, f"Release {release['id']}")
    control = layout.root if layout.is_linked else layout.control
    control_push = _push_repo(settings, control)
    if control_push.get("status") == "failed":
        control_push["next_at"] = _retry_at()
    release["control_push"] = control_push
    save_release(layout, release)
    summary = ", ".join(
        "%s %s" % (key, value.get("version"))
        for key, value in results.items()
    )
    log(
        f"[release] {release['id']}: {status} ({summary})"
    )
    return release


def _render_release_record(release: Mapping[str, Any]) -> str:
    rows = "\n".join(
        f"| `{repo_id}` | {data.get('preset') or '—'} | "
        f"{data.get('base_version') or '—'} | "
        f"{data.get('version') or '—'} | {data.get('tag') or '—'} | "
        f"{data.get('sha') or '—'} | {data.get('release') or '—'} | "
        f"{data.get('detail') or '—'} |"
        for repo_id, data in (release.get("repos") or {}).items()
    )
    return f"""# Release {release.get('id')}

- Project: `{release.get('project')}`
- Request: {release.get('title')}
- Class: {release.get('release_class')}
- Status: {release.get('status')}
- Finalized: {release.get('finalized_at') or '—'}

## Repositories

| Repository | Preset | Base | Version | Tag | Commit | GitHub release | Detail |
|---|---|---|---|---|---|---|---|
{rows or '| — | — | — | — | — | — | — | — |'}
"""


def _retry_tagged_release(
    settings: Settings,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    release: dict[str, Any],
    log: Callable[[str], None],
) -> bool:
    """Try the provider release again for repositories that are already tagged."""

    changed = False
    items = release_tasks(layout, str(release["id"]))
    entries = {str(entry["id"]): entry for entry in manifest_entries(layout)}
    grouped = _repo_tasks(release, items)
    for repo_id, data in (release.get("repos") or {}).items():
        if str(data.get("status") or "") != "tagged":
            continue
        if data.get("release"):
            continue
        entry = entries.get(repo_id)
        repo_items = grouped.get(repo_id) or []
        if entry is None or not repo_items:
            continue
        repo = layout.repo_path(repo_id)
        version = str(data.get("version") or "")
        tag = str(data.get("tag") or f"v{version}")
        sha = str(data.get("sha") or git_ops.head_sha(repo))
        body = _changelog_section(release, version, repo_items)
        url, detail = _provider_release(
            settings, release, project, entry, repo, tag, sha, body
        )
        if url:
            data["release"] = url
            data["status"] = "released"
            data["detail"] = ""
            try:
                write_text(
                    repo
                    / REPO_RELEASES_DIR
                    / version
                    / "release.md",
                    _repo_record(
                        release,
                        version,
                        repo_items,
                        url,
                        str(data.get("preset") or ""),
                        list(data.get("version_files") or []),
                    ),
                )
                git_ops.commit_all(
                    repo, f"Record release v{version}"
                )
                pushed = _push_repo(settings, repo)
                if pushed.get("status") != "pushed":
                    data["detail"] = (
                        "release record push failed: "
                        f"{pushed.get('detail')}"
                    )
            except git_ops.GitOperationError as exc:
                data["detail"] = f"release record failed: {exc}"
            changed = True
        elif detail:
            data["detail"] = detail
    if changed:
        statuses = {
            str(item.get("status") or "")
            for item in (release.get("repos") or {}).values()
        }
        if statuses and statuses <= {"released"}:
            release["status"] = "released"
        elif statuses and statuses <= {"released", "tagged"}:
            release["status"] = "tagged"
        write_text(
            release_path(layout, str(release["id"]), "release.md"),
            _render_release_record(release),
        )
        tasks.commit_control(layout, f"Record release {release['id']}")
        control = layout.root if layout.is_linked else layout.control
        control_push = _push_repo(settings, control)
        if control_push.get("status") == "failed":
            control_push["next_at"] = _retry_at()
        release["control_push"] = control_push
        save_release(layout, release)
        log(f"[release] {release['id']}: provider release retried")
    return changed


def process_releases(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> list[str]:
    """Advance release trains: audit ready ones and publish passing ones."""

    actions: list[str] = []
    auditor = client
    waiting: list[set[str]] = []
    for release in list_releases(layout):
        release_id = str(release["id"])
        status = str(release.get("status") or "")
        if status == "released":
            push = dict(release.get("control_push") or {})
            if push.get("status") == "failed" and _due(
                str(push.get("next_at") or "")
            ):
                control = layout.root if layout.is_linked else layout.control
                refreshed = _push_repo(settings, control)
                if refreshed.get("status") == "failed":
                    refreshed["next_at"] = _retry_at()
                release["control_push"] = refreshed
                save_release(layout, release)
            continue
        if status == "tagged":
            push = dict(release.get("control_push") or {})
            if push.get("status") == "failed" and _due(
                str(push.get("next_at") or "")
            ):
                control = layout.root if layout.is_linked else layout.control
                refreshed = _push_repo(settings, control)
                if refreshed.get("status") == "failed":
                    refreshed["next_at"] = _retry_at()
                release["control_push"] = refreshed
                save_release(layout, release)
            if _due(str(release.get("provider_retry_at") or "")):
                if _retry_tagged_release(
                    settings, layout, project, release, log
                ):
                    release["provider_retry_at"] = ""
                else:
                    release["provider_retry_at"] = _retry_at()
                save_release(layout, release)
            continue
        if status in {"blocked", "cancelled"}:
            continue
        repos = release_repo_ids(layout, release)
        if any(repos & blocked for blocked in waiting):
            continue
        if status in {"partial", "failed"} and not _due(
            str(release.get("next_at") or "")
        ):
            waiting.append(repos)
            continue
        items = release_tasks(layout, release_id)
        if not items:
            waiting.append(repos)
            continue
        statuses = {str(task.get("status") or "") for task in items}
        if (
            not statuses & {"pending", "running", "review"}
            and not all(
                task.get("status") == "done" and _accepted(task)
                for task in items
            )
        ):
            release["status"] = "blocked"
            release["detail"] = (
                "the release has a failed or cancelled task"
            )
            save_release(layout, release)
            actions.append(f"blocked:{release_id}")
            continue
        if not all(task.get("status") == "done" and _accepted(task) for task in items):
            waiting.append(repos)
            continue
        audit = dict(release.get("audit") or {})
        audited = list(audit.get("task_ids") or [])
        current = [str(task["id"]) for task in items]
        passed = (
            audit.get("verdict") == "pass" and audited == current
        )
        if status != "finalizing" and not passed:
            auditor = auditor or build_model_client(
                settings.home, log=log
            )
            if audit_release(
                settings, layout, project, release, items, auditor, log
            ):
                release["status"] = "ready"
                save_release(layout, release)
            else:
                if str(release.get("status")) == "blocked":
                    actions.append(f"blocked:{release_id}")
                    continue
                actions.append(f"audit:{release_id}")
                waiting.append(repos)
                continue
        try:
            finalize_release(settings, layout, project, release, log)
        except Exception as exc:  # noqa: BLE001 - one release must not stop the daemon
            release["status"] = "failed"
            release["detail"] = f"release failed: {exc}"
            release["next_at"] = _retry_at()
            save_release(layout, release)
            log(f"[release] {release_id}: failed: {exc}")
            actions.append(f"failed:{release_id}")
            waiting.append(repos)
            continue
        final = str(release.get("status") or "failed")
        actions.append(
            f"released:{release_id}"
            if final in {"released", "tagged"}
            else f"failed:{release_id}"
        )
        ledger.append_event(
            str(project["id"]),
            "release",
            status=str(release.get("status") or "failed"),
            idempotency_key=(
                f"{project['id']}:release:{release_id}:final"
            ),
            artifact_refs=[
                f"{RELEASES_DIR}/{release_id}/release.md"
            ],
            payload={
                "release": release_id,
                "class": release.get("release_class"),
                "repos": {
                    repo_id: {
                        "version": data.get("version"),
                        "tag": data.get("tag"),
                        "status": data.get("status"),
                        "release": data.get("release"),
                    }
                    for repo_id, data in (release.get("repos") or {}).items()
                },
            },
            generation=ledger.current_generation(str(project["id"])),
        )
        break
    return actions
