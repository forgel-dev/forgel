"""Long-running control-plane loop.

Forgel is a daemon, not a one-shot CLI: it picks projects with pending work,
runs one finite iteration, and then waits. A completed project is never looped
on again; new work starts a new iteration.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from .config import Settings
from .ledger import Ledger
from .orchestrator import Orchestrator


def project_is_done(ledger: Ledger, project_id: str) -> bool:
    state = ledger.checkpoint_state(project_id)
    if state is None:
        return False
    stage, generation = state
    return stage == "done" and ledger.has_completed(project_id, "done", generation)


def has_blocking_reconciliation(workspace: Path) -> bool:
    path = workspace / "docs" / "program" / "reconciliation.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "- Status: pending" in text or "- Status: fix_required" in text


def run_once(
    settings: Settings,
    ledger: Ledger,
    log: Callable[[str], None] = print,
) -> list[str]:
    """Run every project that has pending work. Returns processed project ids."""

    processed: list[str] = []
    for project in ledger.list_projects():
        project_id = project["id"]
        if project_is_done(ledger, project_id):
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
) -> int:
    """Run the control-plane loop. Returns the number of cycles executed."""

    cycles = 0
    while True:
        processed = run_once(settings, ledger, log)
        cycles += 1
        if once or (max_cycles is not None and cycles >= max_cycles):
            return cycles
        if not processed:
            log(f"[daemon] idle; next poll in {interval:g}s")
        time.sleep(interval)
