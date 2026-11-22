"""Runtime operations the project agent may start or restart directly.

The runtime owns a pipeline: a coding agent, QA, review, acceptance, the
release audit and publication. The project agent is the control plane, so it
gets the same operations and decides their order from the conversation and the
project state. Each operation validates its own preconditions and reports what
it did; none of them asks the user a question.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .config import Settings
from .daemon import handle_failure, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient
from .orchestrator import Orchestrator
from .release_train import (
    audit_release,
    finalize_release,
    list_releases,
    load_release,
    release_tasks,
)
from .task_qa import run_task_qa
from .task_review import process_task_result, rerun_review
from .tasks import get_task, latest_task

Log = Callable[[str], None]

OPERATIONS = (
    "drive",
    "task_process",
    "task_qa",
    "task_review",
    "release_audit",
    "release_finalize",
    "orchestrate",
)


def _task(layout: ProjectLayout, task_id: str) -> dict[str, Any]:
    task_id = str(task_id or "").strip()
    task = get_task(layout, task_id) if task_id else latest_task(layout)
    if task is None:
        raise ValueError(
            f"unknown task {task_id!r}" if task_id else "there is no task"
        )
    return task


def _release(
    layout: ProjectLayout, release_id: str
) -> dict[str, Any]:
    release_id = str(release_id or "").strip()
    if release_id:
        release = load_release(layout, release_id)
        if release is None:
            raise ValueError(f"unknown release {release_id!r}")
        return release
    releases = list_releases(layout)
    if not releases:
        raise ValueError("there is no release")
    return releases[-1]


def run_operation(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    operation: str,
    args: Mapping[str, Any] | None = None,
    client: ModelClient | None = None,
    log: Log = lambda _message: None,
) -> str:
    """Run one runtime operation by name and return what it did."""

    args = dict(args or {})
    layout = ProjectLayout.detect(str(project["workspace"]))
    name = str(operation or "").strip()
    if name not in OPERATIONS:
        raise ValueError(
            f"unknown runtime operation {name!r}; "
            f"expected one of {', '.join(OPERATIONS)}"
        )

    if name == "drive":
        processed = run_once(settings, ledger, log=log)
        if not processed:
            return "The runtime had nothing runnable."
        return "The runtime advanced: " + ", ".join(processed) + "."

    if name == "orchestrate":
        Orchestrator(settings, ledger).run(str(project["id"]))
        return "The project pipeline ran to the next gate."

    if name in {"task_process", "task_qa", "task_review"}:
        task = _task(layout, str(args.get("task_id") or ""))
        task_id = str(task["id"])
        if name == "task_qa":
            qa = run_task_qa(settings, ledger, dict(project), task, log)
            return f"Task {task_id}: QA {qa.status}."
        if name == "task_review":
            if str(task.get("status") or "") != "review":
                raise ValueError(
                    "only a task awaiting a review decision can be reviewed "
                    f"(status: {task.get('status') or 'unknown'})"
                )
            if client is None:
                raise ValueError("no model is configured for the reviewer")
            updated = rerun_review(
                settings, ledger, dict(project), task_id, client, log
            )
            return (
                f"Task {task_id}: QA and review re-ran; "
                f"status {updated.get('status') or 'unknown'}."
            )
        process_task_result(
            settings, ledger, dict(project), task, client, log
        )
        stored = get_task(layout, task_id) or task
        if stored.get("status") == "failed":
            handle_failure(
                settings,
                ledger,
                dict(project),
                layout,
                task_id,
                client,
                log,
            )
            stored = get_task(layout, task_id) or stored
        return (
            f"Task {task_id}: the post-agent pipeline ran; "
            f"status {stored.get('status') or 'unknown'}."
        )

    release = _release(layout, str(args.get("release_id") or ""))
    release_id = str(release["id"])
    if name == "release_audit":
        if client is None:
            raise ValueError("no model is configured for the release audit")
        items = release_tasks(layout, release_id)
        passed = audit_release(
            settings,
            layout,
            dict(project),
            release,
            items,
            client,
            log,
            ledger=ledger,
        )
        updated = load_release(layout, release_id) or release
        audit = dict(updated.get("audit") or {})
        verdict = str(audit.get("verdict") or "unknown")
        round_number = audit.get("rounds") or 0
        if passed:
            return (
                f"Release {release_id}: audit passed; "
                f"round {round_number}."
            )
        return (
            f"Release {release_id}: audit {verdict}; "
            f"round {round_number}."
        )
    updated = finalize_release(
        settings, layout, dict(project), release, log
    )
    return (
        f"Release {release_id}: {updated.get('status') or 'unknown'}."
    )
