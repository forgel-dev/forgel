"""The runtime process, as structured state for the main chat agent.

An agent can only stay inside its role if it knows the whole map: who owns
each stage, where the human gates are, what the release train does and what
the agent itself must not do. This module is the single source for that model.
The project agent receives the rendered block on every prompt; the block is
code-owned and tested, not prompt prose.
"""

from __future__ import annotations

from typing import Any, Mapping

from .layout import ProjectLayout
from .release_train import list_releases

PROCESS: tuple[tuple[str, str, str], ...] = (
    (
        "intake and control",
        "this agent",
        "answers, records change requests, queues tasks and plans, and runs "
        "control actions. It does not edit code, run tests, commit or deploy. "
        "A normal release is performed by the release train; an explicit "
        "manual release request is executed through the runtime release "
        "action.",
    ),
    (
        "project setup",
        "this agent and the runtime",
        "adopt or create a project, record the program manifest and the "
        "repository instructions; artifacts in git are the source of truth.",
    ),
    (
        "planning",
        "planner and requirements writer",
        "turn a goal into an ordered backlog, write a formal specification "
        "for every task, record dependencies, and review the whole plan "
        "before anything is queued.",
    ),
    (
        "execution",
        "daemon and coding agent",
        "run one task at a time in the task repository and sandbox; commit "
        "only the files attributed to the task.",
    ),
    (
        "verification",
        "QA, reviewer and acceptor",
        "run deterministic checks and environment e2e, then an independent "
        "review, then acceptance (automatic or human). A failure reworks the "
        "task or schedules a retry with backoff.",
    ),
    (
        "release",
        "runtime release train",
        "after every task is accepted: audit the whole change set, assign one "
        "version per repository from its tags and CHANGELOG, write the "
        "changelog and release records, create an annotated tag, push it and "
        "publish the provider release. A release without its audit is not "
        "published.",
    ),
    (
        "deploy",
        "human gate",
        "staging and production approvals, with the compliance "
        "acknowledgement; the runtime never deploys on its own.",
    ),
    (
        "external changes",
        "sync and reconcile",
        "edits made outside Forgel are recorded and reconciled against the "
        "artifacts; they are never overwritten silently.",
    ),
)

CONTROL: tuple[str, ...] = (
    "pause and resume, the peak-hour policy, retries with backoff, and a "
    "durable ledger plus git artifacts as the state of record.",
    "human gates: staging approval, production approval, jurisdiction and "
    "compliance decisions.",
)

RELEASE_POLICY: tuple[str, ...] = (
    "a published tag is immutable; a change after it is a new version "
    "(patch or minor; major from 1.0.0)",
    "release versions are assigned by the runtime, never by an agent",
    "a release without its audit is not published",
    "only a critical or major audit finding holds a release; a failed "
    "audit with no blocking finding publishes, and its findings stay in "
    "the audit report",
)


def process_model(
    layout: ProjectLayout, project: Mapping[str, Any]
) -> str:
    """The runtime map, ownership, gates and current releases."""

    lines = ["Pipeline:"]
    for stage, owner, detail in PROCESS:
        lines.append(f"- {stage}: {owner} — {detail}")
    lines.append("Control and gates:")
    for item in CONTROL:
        lines.append(f"- {item}")
    lines.append("Release policy:")
    for item in RELEASE_POLICY:
        lines.append(f"- {item}")
    releases = list_releases(layout)
    if releases:
        lines.append("Current releases:")
        for release in releases[-3:]:
            repos = ", ".join(
                f"{repo_id} "
                f"{data.get('version') or data.get('planned_version') or '—'}"
                for repo_id, data in (
                    release.get("repos") or {}
                ).items()
            )
            lines.append(
                f"- {release.get('title') or release['id']}: "
                f"{release.get('status') or 'unknown'}"
                + (f" ({repos})" if repos else "")
            )
    return "\n".join(lines)
