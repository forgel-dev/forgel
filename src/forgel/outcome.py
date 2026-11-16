"""Structured outcomes from the shared command router.

``forgel say`` must answer with the same decision the console and Telegram
get: an answer, a queued task, a plan or a control action. The router stays the
only dispatcher; this module observes one routed call and reports what it
became, so the client never grows a second dispatch table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .chat import CommandRouter
from .layout import ProjectLayout
from .tasks import get_task

ANSWER_COMMANDS = {"/start", "/help"}


@dataclass(frozen=True)
class Outcome:
    """One routed message: its kind, the reply text and its payload."""

    kind: str
    text: str
    payload: dict[str, Any] = field(default_factory=dict)


class _Recorder:
    """Remember the agent result that the router used for this message."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent
        self.result: Any = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)

    def handle(self, *args: Any, **kwargs: Any) -> Any:
        result = self._agent.handle(*args, **kwargs)
        self.result = result
        return result


def _task_payload(
    router: CommandRouter, chat_id: int, task_id: object
) -> dict[str, Any] | None:
    if not task_id:
        return None
    project_id = router.ledger.get_session(chat_id)
    project = router.ledger.get_project(project_id) if project_id else None
    if project is None:
        return {"id": str(task_id)}
    layout = ProjectLayout.detect(project["workspace"])
    task = get_task(layout, str(task_id))
    return task or {"id": str(task_id)}


def _message_outcome(
    router: CommandRouter, chat_id: int, text: str, actor: str
) -> Outcome:
    agent = router.agent
    recorder = _Recorder(agent) if agent is not None else None
    if recorder is not None:
        router.agent = recorder
    try:
        reply = router.handle(chat_id, text, actor)
    finally:
        router.agent = agent
    result = recorder.result if recorder is not None else None
    if result is None:
        return Outcome("answer", reply.text, {})
    if result.kind in {"action", "actions"}:
        return Outcome(
            "action", reply.text, {"actions": list(result.actions or [])}
        )
    if result.kind == "change_request":
        return Outcome(
            "change_request",
            reply.text,
            {
                "task": _task_payload(router, chat_id, result.task_id),
                "request": result.request,
            },
        )
    return Outcome("answer", reply.text, {})


def handle_outcome(
    router: CommandRouter, chat_id: int, text: str, actor: str
) -> Outcome:
    """Route one message exactly like the console and report its kind."""

    raw = str(text or "").strip()
    if not raw:
        return Outcome("answer", "Send a command or a message. /help", {})
    if not raw.startswith("/"):
        return _message_outcome(router, chat_id, raw, actor)
    command = raw.partition(" ")[0].split("@", 1)[0].lower()
    reply = router.handle(chat_id, raw, actor)
    if command == "/plan":
        return Outcome("plan", reply.text, {"command": command})
    if command in ANSWER_COMMANDS:
        return Outcome("answer", reply.text, {"command": command})
    return Outcome("action", reply.text, {"command": command})
