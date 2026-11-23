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
from . import limits, specs, tasks
from .artifacts import write_text
from .daemon import handle_failure, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient
from .release_train import (
    audit_release,
    finalize_release,
    list_releases,
    load_release,
    release_tasks,
    resume_release,
)
from .task_qa import run_task_qa
from .task_review import process_task_result, rerun_review
from .tasks import current_task, get_task

Log = Callable[[str], None]

OPERATIONS = (
    "drive",
    "task_retry",
    "task_restart",
    "task_process",
    "task_qa",
    "task_review",
    "release_resume",
    "release_audit",
    "release_finalize",
    "set_limit",
)


def _task(layout: ProjectLayout, task_id: str) -> dict[str, Any]:
    task_id = str(task_id or "").strip()
    task = get_task(layout, task_id) if task_id else current_task(layout)
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


def _restart_from_requirements(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    task: Mapping[str, Any],
    client: ModelClient,
    log: Log,
) -> str:
    """Rewrite the specification from the task's own request and start over."""

    task_id = str(task["id"])
    repo_id = str(task.get("repo_id") or "").strip()
    depends_on = [str(item) for item in (task.get("depends_on") or [])]
    intent = {
        "title": task.get("title") or task_id,
        "summary": task.get("summary") or task.get("title") or task_id,
        "repo_id": repo_id,
        "depends_on": depends_on,
    }
    goal = str(task.get("plan_goal") or task.get("title") or "—")
    notes = ""
    request = str(task.get("request") or "").strip()
    if request:
        try:
            notes = layout.artifact(request).read_text(encoding="utf-8")
        except OSError:
            notes = ""
    log(f"[restart] {project['id']}: task {task_id}: rewriting spec")
    spec = specs.write_task_spec(
        settings, layout, goal, notes, intent, client, log=log
    )
    ref = specs.spec_path(task_id)
    write_text(
        layout.artifact(ref),
        specs.render_spec(
            spec,
            task_id,
            str(task.get("plan_id") or ""),
            repo_id,
            depends_on,
        ),
    )
    tasks.restart_task(layout, task_id)
    tasks.update_task(
        layout,
        task_id,
        spec=ref,
        requirements=list(spec.get("requirements") or []),
        acceptance=list(spec.get("acceptance") or []),
        constraints=list(spec.get("constraints") or []),
        checks=list(spec.get("checks") or []),
        test_command=list(spec.get("test_command") or []),
        external_dependencies=list(
            spec.get("external_dependencies") or []
        ),
    )
    tasks.commit_task(layout, task_id, f"Restart spec {task_id}")
    ledger.append_event(
        str(project["id"]),
        "task_restart",
        status="completed",
        payload={
            "task": task_id,
            "requirements": list(spec.get("requirements") or []),
        },
        artifact_refs=[ref],
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[restart] {project['id']}: task {task_id}: specification "
        f"rewritten; task is pending"
    )
    return f"Task {task_id} restarted from its requirements."


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

    if name == "set_limit":
        limit_name = str(
            args.get("name") or "command_timeout"
        ).strip()
        value = limits.set_value(
            layout, limit_name, args.get("seconds")
        )
        return f"Limit {limit_name} is now {value:g}s."

    if name == "drive":
        processed = run_once(settings, ledger, log=log)
        if not processed:
            return "The runtime had nothing runnable."
        return "The runtime advanced: " + ", ".join(processed) + "."

    if name == "task_retry":
        task = _task(layout, str(args.get("task_id") or ""))
        task_id = str(task["id"])
        tasks.retry_task(layout, task_id)
        return f"Task {task_id} is queued again."

    if name == "task_restart":
        task = _task(layout, str(args.get("task_id") or ""))
        if client is None:
            raise ValueError(
                "no model is configured to rewrite the specification"
            )
        return _restart_from_requirements(
            settings, ledger, project, layout, task, client, log
        )

    if name == "release_resume":
        release = _release(layout, str(args.get("release_id") or ""))
        resume_release(layout, str(release["id"]))
        return f"Release {release['id']} is running again."

    if name in {"task_process", "task_qa", "task_review"}:
        task = _task(layout, str(args.get("task_id") or ""))
        task_id = str(task["id"])
        if name == "task_qa":
            qa = run_task_qa(settings, ledger, dict(project), task, log)
            return f"Task {task_id}: QA {qa.status}."
        if name == "task_review":
            if client is None:
                raise ValueError("no model is configured for the reviewer")
            if str(task.get("status") or "") == "review":
                updated = rerun_review(
                    settings, ledger, dict(project), task_id, client, log
                )
                return (
                    f"Task {task_id}: QA and review re-ran; "
                    f"status {updated.get('status') or 'unknown'}."
                )
            # A failed or blocked task can be reviewed too: run the same
            # post-agent pipeline and let the controller see the outcome.
            process_task_result(
                settings, ledger, dict(project), task, client, log
            )
            stored = get_task(layout, task_id) or task
            return (
                f"Task {task_id}: QA and review ran; "
                f"status {stored.get('status') or 'unknown'}."
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
