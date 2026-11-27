"""Control ownership and operation vocabulary for model-driven workflows.

The chat agent, planner and controller have different prompt contracts. This
module does not merge them: it gives the runtime one code-owned description of
who leads the current state and which operation names each role understands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from . import tasks
from .layout import ProjectLayout
from .release_train import TERMINAL_RELEASE_STATUSES, list_releases

CHAT = "chat"
PLANNER = "planner"
CONTROLLER = "controller"
RUNTIME = "runtime"

RUNTIME_OPERATIONS: tuple[str, ...] = (
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

CONTROLLER_OPERATIONS: tuple[str, ...] = (
    "retry",
    "task_retry",
    "task_restart",
    "rework",
    "respec",
    "accept",
    "reject",
    "cancel",
    "block",
    "run_task",
    "task_process",
    "task_qa",
    "task_review",
    "release_resume",
    "release_audit",
    "release_finalize",
    "release_fix",
    "set_limit",
    "ask_user",
    "stop",
)

ROLE_OPERATIONS: Mapping[str, tuple[str, ...]] = {
    CHAT: RUNTIME_OPERATIONS,
    CONTROLLER: CONTROLLER_OPERATIONS,
}


@dataclass(frozen=True)
class ControlState:
    """The single leading role and the visible continuation boundaries."""

    leader: str
    detail: str
    handoff: str
    branches: tuple[str, ...]


def _stopped_release(layout: ProjectLayout) -> dict[str, Any] | None:
    for release in reversed(list_releases(layout)):
        if str(release.get("status") or "") in {"blocked", "failed"}:
            return release
    return None


def _active_release(layout: ProjectLayout) -> dict[str, Any] | None:
    for release in reversed(list_releases(layout)):
        if str(release.get("status") or "") not in TERMINAL_RELEASE_STATUSES:
            return release
    return None


def control_state(layout: ProjectLayout) -> ControlState:
    """Resolve one leading role from the current task and release state."""

    current = tasks.current_task(layout)
    status = str(current.get("status") or "") if current is not None else ""
    if current is not None and status in {"failed", "blocked"}:
        task_id = str(current.get("id") or "current task")
        return ControlState(
            leader=CONTROLLER,
            detail=f"controller owns recovery of {task_id} ({status})",
            handoff=(
                "chat preserves the user's intent and reports the outcome; "
                "it does not improvise a separate recovery path"
            ),
            branches=(
                "controller chooses a valid recovery operation",
                "runtime executes that operation and returns the resulting state",
            ),
        )
    if current is not None and status in {"pending", "running", "review"}:
        task_id = str(current.get("id") or "current task")
        return ControlState(
            leader=RUNTIME,
            detail=f"runtime owns {task_id} ({status})",
            handoff="controller takes over if the runtime reports a stop",
            branches=(
                "runtime advances execution, verification or acceptance",
                "chat answers and records new user intent without duplicating execution",
            ),
        )
    stopped = _stopped_release(layout)
    if stopped is not None:
        release_id = str(stopped.get("id") or "current release")
        return ControlState(
            leader=CONTROLLER,
            detail=f"controller owns recovery of release {release_id}",
            handoff=(
                "chat preserves the release goal and reports the outcome; "
                "planner is consulted only for a requirements decision"
            ),
            branches=(
                "controller chooses a valid release or task recovery operation",
                "runtime resumes the release train after the operation",
            ),
        )
    active = _active_release(layout)
    if active is not None:
        release_id = str(active.get("id") or "current release")
        return ControlState(
            leader=RUNTIME,
            detail=f"runtime release train owns {release_id}",
            handoff="controller takes over if the release train stops",
            branches=(
                "runtime audits and advances the release",
                "chat reports release state and records new user intent",
            ),
        )
    return ControlState(
        leader=CHAT,
        detail="chat owns user intent while no work is active",
        handoff="planner may decompose a new goal; runtime owns accepted work",
        branches=(
            "chat answers or records a change request",
            "planner decomposes a milestone when planning is requested",
            "controller receives a stopped process when one occurs",
        ),
    )


def render_control_state(layout: ProjectLayout) -> str:
    """Render structured ownership for the main chat agent's context."""

    state = control_state(layout)
    lines = [
        f"Current control owner: {state.leader} — {state.detail}",
        f"Handoff: {state.handoff}",
        "Available branches:",
    ]
    lines.extend(f"- {branch}" for branch in state.branches)
    return "\n".join(lines)
