"""Long-running control-plane loop.

Forgel is a daemon, not a one-shot CLI: it picks projects with pending work,
runs one finite iteration, and then waits. A completed project is never looped
on again; new work starts a new iteration.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import peak, tasks
from .approvals import awaits_approval, latest_approval
from .coding_agent import CodingAgent
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
    if task is not None and task.get("status") in {
        "pending",
        "running",
        "failed",
    }:
        return f"task {task['status']}"
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
    tasks.update_task(
        layout, task_id, status="running", started_at=_now()
    )
    log(f"[daemon] {project['id']}: starting task {task_id}")
    model = client or build_model_client(settings.home, log=log)
    if model is None:
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={"summary": "no model configured for the coding agent"},
        )
        log(f"[daemon] {project['id']}: task {task_id} has no model client")
        return True
    try:
        CodingAgent(settings, ledger, model).run(project, task, log)
    except Exception as exc:  # noqa: BLE001 - one task must not kill the daemon
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={"summary": f"agent crashed: {exc}"},
        )
        log(f"[daemon] {project['id']}: task {task_id} crashed: {exc}")
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
        if task is not None:
            if _run_task(
                settings, ledger, project, layout, task, client, log
            ):
                processed.append(project_id)
            continue
        if layout.metadata().get("mode") == "brownfield":
            log(f"[daemon] {project_id}: brownfield project has no executor yet")
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
        if not processed:
            log(f"[daemon] idle; next poll in {interval:g}s")
        time.sleep(interval)
