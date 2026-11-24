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
from .daemon import _run_task, handle_failure, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient
from .release_train import (
    audit_release,
    cancel_empty_release,
    finalize_release,
    list_releases,
    load_release,
    release_tasks,
    resume_release,
)
from .task_qa import run_task_qa
from .task_review import process_task_result, rerun_review
from .tasks import get_task

Log = Callable[[str], None]

OPERATIONS = (
    "drive",
    "task_retry",
    "task_restart",
    "task_respec",
    "task_cancel",
    "task_process",
    "task_qa",
    "task_review",
    "release_resume",
    "release_audit",
    "release_finalize",
    "set_limit",
)


def _task(
    layout: ProjectLayout, task_id: str
) -> dict[str, Any]:
    """Resolve a task reference through the shared task selector."""

    value = str(task_id or "").strip()
    task = tasks.resolve_task(layout, value)
    if task is None:
        raise ValueError(
            f"unknown task {value!r}" if value else "there is no task"
        )
    return task


def _workable(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> None:
    """Refuse work on a cancelled task: the document is not accepted."""

    if str(task.get("status") or "") == "cancelled" or specs.cancelled(
        layout, task
    ):
        raise ValueError(
            f"task {task['id']} is cancelled; its requirements document "
            "is not accepted for work"
        )


def _requested_changes(args: Mapping[str, Any]) -> str:
    return str(
        args.get("changes")
        or args.get("clarification")
        or args.get("issue")
        or args.get("notes")
        or ""
    ).strip()


def _current_spec(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    ref = str(task.get("spec") or "").strip() or specs.spec_path(
        str(task.get("id") or "")
    )
    try:
        text = layout.artifact(ref).read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    if text:
        return text
    parts: list[str] = []
    for title, key in (
        ("Requirements", "requirements"),
        ("Acceptance", "acceptance"),
    ):
        values = [
            str(item).strip()
            for item in task.get(key) or []
            if str(item).strip()
        ]
        if values:
            parts.append(
                title + ":\n" + "\n".join(f"- {item}" for item in values)
            )
    return "\n\n".join(parts)


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
    requested_changes: str = "",
) -> str:
    """Rewrite the specification from the task's own request and start over."""

    task_id = str(task["id"])
    repo_id = str(task.get("repo_id") or "").strip()
    intent = {
        "title": task.get("title") or task_id,
        "summary": task.get("summary") or task.get("title") or task_id,
        "repo_id": repo_id,
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
        settings,
        layout,
        goal,
        notes,
        intent,
        client,
        log=log,
        requested_changes=requested_changes,
        current_spec=_current_spec(layout, task),
    )
    ref = specs.spec_path(task_id)
    write_text(
        layout.artifact(ref),
        specs.render_spec(
            spec,
            task_id,
            str(task.get("plan_id") or ""),
            repo_id,
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
        f"rewritten; task restarted"
    )
    stored = tasks.get_task(layout, task_id)
    if stored is not None:
        _run_task(
            settings,
            ledger,
            dict(project),
            layout,
            stored,
            client,
            log,
        )
    return f"Task {task_id} restarted from its requirements."


def _rewrite_task_requirements(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    task: Mapping[str, Any],
    client: ModelClient,
    log: Log,
    requested_changes: str,
) -> str:
    """Rewrite the task's requirements without changing its status or work."""

    task_id = str(task["id"])
    repo_id = str(task.get("repo_id") or "").strip()
    intent = {
        "title": task.get("title") or task_id,
        "summary": task.get("summary") or task.get("title") or task_id,
        "repo_id": repo_id,
    }
    goal = str(task.get("plan_goal") or task.get("title") or "—")
    notes = ""
    request = str(task.get("request") or "").strip()
    if request:
        try:
            notes = layout.artifact(request).read_text(encoding="utf-8")
        except OSError:
            notes = ""
    log(f"[respec] {project['id']}: task {task_id}: rewriting requirements")
    spec = specs.write_task_spec(
        settings,
        layout,
        goal,
        notes,
        intent,
        client,
        log=log,
        requested_changes=requested_changes,
        current_spec=_current_spec(layout, task),
    )
    ref = specs.spec_path(task_id)
    write_text(
        layout.artifact(ref),
        specs.render_spec(
            spec,
            task_id,
            str(task.get("plan_id") or ""),
            repo_id,
        ),
    )
    tasks.update_task(
        layout,
        task_id,
        spec=ref,
        requirements=list(spec.get("requirements") or []),
        acceptance=list(spec.get("acceptance") or []),
        constraints=list(spec.get("constraints") or []),
        external_dependencies=list(
            spec.get("external_dependencies") or []
        ),
    )
    tasks.commit_task(layout, task_id, f"Rewrite requirements {task_id}")
    ledger.append_event(
        str(project["id"]),
        "task_respec",
        status="completed",
        payload={
            "task": task_id,
            "changes": requested_changes,
            "requirements": list(spec.get("requirements") or []),
        },
        artifact_refs=[ref],
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[respec] {project['id']}: task {task_id}: requirements "
        "rewritten; status unchanged"
    )
    return (
        f"Task {task_id}: requirements rewritten; "
        "the task status is unchanged."
    )


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

    if name == "task_cancel":
        task = _task(layout, str(args.get("task_id") or ""))
        task_id = str(task["id"])
        notes = str(
            args.get("notes") or args.get("reason") or ""
        ).strip()
        cancelled = tasks.cancel_task(layout, task_id, notes=notes)
        marked = specs.mark_cancelled(layout, cancelled)
        answer = (
            f"Task {task_id} is cancelled and is not accepted for work "
            "again."
        )
        if marked:
            answer += " Its requirements document is marked at the top."
        release_id = cancel_empty_release(layout, task_id)
        if release_id:
            answer += (
                f" Release {release_id} had no tasks left and is cancelled."
            )
        answer += (
            " Commits it already made stay in the tree for the release "
            "audit."
        )
        return answer

    if name == "task_retry":
        task = _task(layout, str(args.get("task_id") or ""))
        _workable(layout, task)
        task_id = str(task["id"])
        tasks.retry_task(layout, task_id)
        return f"Task {task_id} is queued again."

    if name == "task_restart":
        task = _task(layout, str(args.get("task_id") or ""))
        _workable(layout, task)
        if client is None:
            raise ValueError(
                "no model is configured to rewrite the specification"
            )
        return _restart_from_requirements(
            settings,
            ledger,
            project,
            layout,
            task,
            client,
            log,
            requested_changes=_requested_changes(args),
        )

    if name == "task_respec":
        task = _task(layout, str(args.get("task_id") or ""))
        _workable(layout, task)
        if client is None:
            raise ValueError(
                "no model is configured to rewrite the specification"
            )
        changes = _requested_changes(args)
        if not changes:
            raise ValueError(
                "task_respec needs the requested requirement changes"
            )
        return _rewrite_task_requirements(
            settings,
            ledger,
            project,
            layout,
            task,
            client,
            log,
            changes,
        )

    if name == "release_resume":
        release = _release(layout, str(args.get("release_id") or ""))
        resume_release(layout, str(release["id"]))
        return f"Release {release['id']} is running again."

    if name in {"task_process", "task_qa", "task_review"}:
        task = _task(layout, str(args.get("task_id") or ""))
        _workable(layout, task)
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
