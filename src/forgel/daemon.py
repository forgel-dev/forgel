"""Long-running control-plane loop.

Forgel is a daemon, not a one-shot CLI: it picks projects with pending work,
runs one finite iteration, and then waits. A completed project is never looped
on again; new work starts a new iteration.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from . import peak, tasks
from .approvals import awaits_approval, latest_approval
from .coding_agent import CodingAgent
from .task_review import process_task_result
from .config import Settings
from .control import is_paused
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient, build_model_client
from .orchestrator import Orchestrator
from .state import STAGES


def project_is_done(ledger: Ledger, project_id: str) -> bool:
    state = ledger.checkpoint_state(project_id)
    if state is None:
        return False
    stage, generation = state
    return stage == "done" and ledger.has_completed(project_id, "done", generation)


def has_blocking_reconciliation(workspace: Path) -> bool:
    path = ProjectLayout.detect(workspace).artifact(
        "docs/program/reconciliation.md"
    )
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "- Status: pending" in text or "- Status: fix_required" in text


def project_state(ledger: Ledger, project: dict[str, Any]) -> str:
    """Return a short human-readable state used by status and notifications."""

    project_id = project["id"]
    layout = ProjectLayout.detect(project["workspace"])
    if has_blocking_reconciliation(Path(project["workspace"])):
        return "reconciliation pending"
    task = tasks.latest_task(layout)
    if task is not None and task.get("status") == "pending":
        moment = tasks.retry_moment(task)
        if moment is not None and moment > datetime.now(timezone.utc):
            return f"task retry at {moment.strftime('%H:%M UTC')}"
    if task is not None and task.get("status") in {
        "pending",
        "running",
        "review",
        "blocked",
        "failed",
    }:
        return f"task {task['status']}"
    if (
        tasks.next_pending_task(layout) is None
        and tasks.blocked_pending(layout)
    ):
        return "task blocked"
    state = ledger.checkpoint_state(project_id)
    if state is None:
        if task is not None and task.get("status") == "done":
            return "task done"
        if task is not None and task.get("status") == "cancelled":
            return "task cancelled"
        return "adopted" if layout.metadata().get("mode") == "brownfield" else "queued"
    stage, generation = state
    if stage == "approval":
        approval = latest_approval(ledger, project_id, "staging", generation)
        if approval is None:
            return "awaiting staging approval"
        if approval["decision"] != "approved":
            return f"staging {approval['decision']}"
    stage_events = [
        event
        for event in ledger.events(project_id, generation)
        if event["stage"] in STAGES
    ]
    if stage_events and stage_events[-1]["status"] == "failed":
        return f"failed at {stage_events[-1]['stage']}"
    return stage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failure(
    kind: str, message: str, retryable: bool | None = None
) -> dict[str, Any]:
    return {
        "kind": kind,
        "message": message,
        "retryable": (
            kind == "infrastructure" if retryable is None else retryable
        ),
    }


def _classify_crash(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    lowered = message.lower()
    if "sandbox" in lowered or "docker" in lowered:
        return _failure("infrastructure", message)
    return _failure("external", message, retryable=False)


def _feedback_from(data: dict[str, Any]) -> list[str]:
    feedback: list[str] = []
    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    for item in review.get("blocking") or []:
        feedback.append(f"review: {item}")
    if review.get("summary"):
        feedback.append(f"review summary: {review['summary']}")
    qa = data.get("qa") if isinstance(data.get("qa"), dict) else {}
    for item in qa.get("checks") or []:
        if item.get("verdict") == "fail":
            feedback.append(
                f"QA check failed: {item.get('criterion')} "
                f"(exit {item.get('exit_code')})"
            )
    if not feedback:
        feedback.append(
            str(data.get("summary") or "the previous attempt failed")
        )
    return feedback


def _quarantine(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task_id: str,
    failure: dict[str, Any],
    attempts: int,
    log: Callable[[str], None],
) -> None:
    if settings.plan_on_failure == "stop":
        tasks.block_dependents(layout, task_id, stop=True)
    elif settings.plan_on_failure == "quarantine":
        tasks.block_dependents(layout, task_id, stop=False)
    ledger.append_event(
        str(project["id"]),
        "task_failure",
        status="failed",
        idempotency_key=(
            f"{project['id']}:task_failure:{task_id}:"
            f"{failure.get('kind')}:{attempts}"
        ),
        artifact_refs=[],
        payload={
            "task": task_id,
            "kind": failure.get("kind"),
            "attempts": attempts,
            "policy": settings.plan_on_failure,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[task] {project['id']}: {task_id} failed "
        f"({failure.get('kind')}); policy {settings.plan_on_failure}"
    )


def handle_failure(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task_id: str,
    client: ModelClient | None,
    log: Callable[[str], None],
    now: datetime | None = None,
) -> None:
    """React to a failure by kind: retry, rework, arbitrate, quarantine."""

    task = tasks.get_task(layout, task_id)
    if task is None or task.get("status") != "failed":
        return
    moment = now or datetime.now(timezone.utc)
    data = dict(task.get("result") or {})
    failure = dict(
        data.get("failure")
        or _failure("external", "unknown failure", retryable=False)
    )
    kind = str(failure.get("kind") or "external")
    attempts = int(data.get("attempts", 0))
    if kind == "infrastructure" and attempts < settings.task_retries:
        backoff = settings.retry_backoff or (1,)
        delay = backoff[min(attempts, len(backoff) - 1)]
        retry_at = (moment + timedelta(minutes=delay)).isoformat(
            timespec="seconds"
        )
        data["attempts"] = attempts + 1
        data["retry_after"] = retry_at
        data["last_failure"] = failure
        data.pop("failure", None)
        tasks.update_task(
            layout,
            task_id,
            status="pending",
            started_at="",
            finished_at="",
            result=data,
        )
        log(
            f"[retry] {project['id']}: task {task_id} infrastructure "
            f"failure; retry {attempts + 1}/{settings.task_retries} "
            f"in {delay}m (at {retry_at})"
        )
        return
    if kind in {"qa", "review"}:
        reworks = int(data.get("rework_count", 0))
        if reworks < settings.task_reworks:
            data["rework_count"] = reworks + 1
            data["feedback"] = _feedback_from(data)
            data["last_failure"] = failure
            data.pop("failure", None)
            tasks.update_task(
                layout,
                task_id,
                status="pending",
                started_at="",
                finished_at="",
                result=data,
            )
            log(
                f"[rework] {project['id']}: task {task_id} sent back "
                f"({kind}); rework {reworks + 1}/{settings.task_reworks}"
            )
            return
        if settings.task_arbiter and client is not None:
            from .arbiter import run_task_arbiter
            from .task_review import accept_task, await_acceptance

            arbitration = run_task_arbiter(
                settings, ledger, project, task, client, log
            )
            if arbitration.verdict == "accept":
                if settings.task_accept == "auto":
                    accept_task(
                        settings,
                        ledger,
                        project,
                        task,
                        actor="arbiter",
                        notes=arbitration.summary,
                    )
                else:
                    await_acceptance(
                        layout,
                        task,
                        "arbiter accepted; human acceptance required",
                    )
                return
            if arbitration.verdict == "criteria":
                data = dict(
                    (tasks.get_task(layout, task_id) or task).get("result")
                    or data
                )
                data["summary"] = (
                    str(data.get("summary") or "").strip()
                    + "; acceptance criteria need revision"
                ).strip("; ")
                data["failure"] = {
                    "kind": "criteria",
                    "message": arbitration.summary,
                    "retryable": False,
                }
                tasks.update_task(
                    layout, task_id, status="failed", result=data
                )
                _quarantine(
                    settings,
                    ledger,
                    project,
                    layout,
                    task_id,
                    data["failure"],
                    attempts,
                    log,
                )
                return
            if arbitration.verdict == "fix":
                data = dict(
                    (tasks.get_task(layout, task_id) or task).get("result")
                    or data
                )
                data["failure"] = {
                    "kind": "review",
                    "message": arbitration.summary
                    or "the arbiter confirmed the review rejection",
                    "retryable": False,
                }
                tasks.update_task(
                    layout, task_id, status="failed", result=data
                )
                failure = data["failure"]
    _quarantine(
        settings, ledger, project, layout, task_id, failure, attempts, log
    )


def _run_task(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task: dict[str, Any],
    client: ModelClient | None,
    log: Callable[[str], None],
) -> bool:
    task_id = str(task["id"])
    policy = peak.project_policy(settings, layout.control)
    if peak.should_defer(policy, hours=settings.peak_hours):
        log(
            f"[daemon] {project['id']}: {peak.defer_message(hours=settings.peak_hours, tz_name=settings.timezone)}"
        )
        return False
    stored = dict(task.get("result") or {})
    stored.pop("retry_after", None)
    tasks.update_task(
        layout,
        task_id,
        status="running",
        started_at=_now(),
        result=stored,
    )
    log(f"[daemon] {project['id']}: starting task {task_id}")
    model = client or build_model_client(settings.home, log=log)
    if model is None:
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={
                "summary": "no model configured for the coding agent",
                "failure": _failure(
                    "external",
                    "no model configured",
                    retryable=False,
                ),
            },
        )
        log(f"[daemon] {project['id']}: task {task_id} has no model client")
        handle_failure(
            settings, ledger, project, layout, task_id, None, log
        )
        return True
    try:
        result = CodingAgent(settings, ledger, model).run(
            project, task, log
        )
        if result.status == "done" and (
            settings.task_qa or settings.task_review
        ):
            try:
                process_task_result(
                    settings, ledger, project, task, model, log
                )
            except Exception as exc:  # noqa: BLE001 - the pipeline must not crash
                stored = tasks.get_task(layout, task_id) or task
                tasks.update_task(
                    layout,
                    task_id,
                    status="failed",
                    result={
                        **dict(stored.get("result") or {}),
                        "summary": f"post-agent pipeline failed: {exc}",
                        "failure": _failure(
                            "external",
                            f"post-agent pipeline failed: {exc}",
                            retryable=False,
                        ),
                    },
                )
                log(
                    f"[task] {project['id']}: {task_id} "
                    f"post-agent pipeline crashed: {exc}"
                )
    except Exception as exc:  # noqa: BLE001 - one task must not kill the daemon
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={
                "summary": f"agent crashed: {exc}",
                "failure": _classify_crash(exc),
            },
        )
        log(f"[daemon] {project['id']}: task {task_id} crashed: {exc}")
    handle_failure(
        settings, ledger, project, layout, task_id, model, log
    )
    try:
        tasks.commit_control(layout, f"Task {task_id}: result")
    except Exception:  # noqa: BLE001 - a commit must not stop the daemon
        pass
    return True


def run_once(
    settings: Settings,
    ledger: Ledger,
    log: Callable[[str], None] = print,
    client: ModelClient | None = None,
) -> list[str]:
    """Run every project that has pending work. Returns processed project ids."""

    processed: list[str] = []
    for project in ledger.list_projects():
        project_id = project["id"]
        if project_is_done(ledger, project_id):
            continue
        layout = ProjectLayout.detect(project["workspace"])
        recovered = tasks.recover_running(layout)
        for task in recovered:
            log(
                f"[daemon] {project_id}: recovered interrupted task "
                f"{task['id']} ({task['status']})"
            )
        task = tasks.next_pending_task(layout)
        if task is None and tasks.waiting_pending(layout):
            continue
        if task is not None:
            if _run_task(
                settings, ledger, project, layout, task, client, log
            ):
                processed.append(project_id)
            continue
        if layout.metadata().get("mode") == "brownfield":
            # No pending task: idle. A blocked/retrying task is visible in
            # the project state instead of a log line on every cycle.
            continue
        if awaits_approval(ledger, project_id):
            log(f"[daemon] {project_id}: waiting for staging approval")
            continue
        workspace = Path(project["workspace"])
        if has_blocking_reconciliation(workspace):
            log(f"[daemon] {project_id}: waiting for a reconciliation decision")
            continue
        try:
            log(f"[daemon] {project_id}: running iteration")
            Orchestrator(settings, ledger).run(project_id)
            processed.append(project_id)
        except Exception as exc:  # noqa: BLE001 - one project must not kill the daemon
            log(f"[daemon] {project_id}: stopped: {exc}")
    return processed


def next_retry_wait(ledger: Ledger) -> float | None:
    """Seconds until the earliest pending retry, if any."""

    now = datetime.now(timezone.utc)
    moments: list[datetime] = []
    for project in ledger.list_projects():
        layout = ProjectLayout.detect(project["workspace"])
        moments.extend(tasks.retry_times(layout))
    future = [moment for moment in moments if moment > now]
    if not future:
        return None
    return max(1.0, min((min(future) - now).total_seconds(), 3600.0))


def run_daemon(
    settings: Settings,
    ledger: Ledger,
    interval: float = 5.0,
    once: bool = False,
    max_cycles: int | None = None,
    log: Callable[[str], None] = print,
    client: ModelClient | None = None,
) -> int:
    """Run the control-plane loop. Returns the number of cycles executed."""

    cycles = 0
    while True:
        if is_paused(settings.home):
            processed = []
            log("[daemon] paused")
        else:
            processed = run_once(settings, ledger, log, client)
        cycles += 1
        if once or (max_cycles is not None and cycles >= max_cycles):
            return cycles
        wait = interval
        if not processed:
            retry_wait = next_retry_wait(ledger)
            if retry_wait is not None:
                wait = retry_wait
            log(f"[daemon] idle; next poll in {wait:g}s")
        time.sleep(wait)
