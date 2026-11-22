"""The controlling agent: one operator for every stopped process.

The runtime has a one-way pipeline from the task statement to the release.
While nothing goes wrong it walks that pipeline directly. When any step
reports a finding, an execution or environment error, or a lack of
information, the deterministic ladders stop and this agent takes over: it
receives the whole situation and the runtime's operations, decides the next
step and keeps going until the work reaches its result.

Asking the owner is one of its operations, not a separate process. It is the
last resort, used only when the decision needs a product choice the owner
must make.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    cache_tokens,
    project_model_name,
)
from .model_output import json_objects

MAX_CONTEXT_CHARS = 24_000
MAX_MESSAGE_CHARS = 2_000
MAX_MESSAGES = 12

OPERATIONS = (
    "retry",
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
    "ask_user",
    "stop",
)


class ControllerError(RuntimeError):
    """The controlling agent could not produce a usable decision."""


@dataclass(frozen=True)
class Decision:
    operation: str
    reason: str = ""
    summary: str = ""
    feedback: list[str] = field(default_factory=list)
    issue: str = ""
    question: str = ""
    release_id: str = ""
    args: dict[str, Any] = field(default_factory=dict)


SYSTEM_PROMPT = """You are Forgel's controlling agent. The one-way process
from the task statement to the release stopped because of a problem. You see
the whole situation and every runtime operation. Decide the next step that
gets the work to its result; do not follow a fixed retry ladder.

Operations:
- retry: run the same work again unchanged;
- rework: send the work back with concrete feedback;
- respec: the specification is the defect; rewrite it for the given issue;
- accept: the work meets the requirements; accept it;
- reject: the work does not meet the requirements; send it back;
- cancel: the work is no longer wanted;
- block: stop the work and keep the reason;
- run_task, task_process, task_qa, task_review: run a task operation now;
- release_resume, release_audit, release_finalize, release_fix: run a
  release operation now;
- ask_user: stop and ask the owner; only when the decision needs a product
  choice, access or an irreversible action that only the owner can make;
- stop: stop and report the current state.

Return exactly one JSON object:
{
  "operation": "one of the operations above",
  "reason": "why this step follows from the state",
  "summary": "the outcome in one paragraph",
  "feedback": ["concrete instruction for rework or reject"],
  "issue": "the specification defect for respec",
  "question": "the one question for ask_user",
  "release_id": "the release for a release operation, when not the current one"
}

Use only the facts in the context. Do not repeat what is already proven to
work. Do not ask the owner to choose between internal process options.
"""


TASK_ACTIONS = {
    "retry",
    "rework",
    "respec",
    "accept",
    "cancel",
    "task_process",
    "task_qa",
    "task_review",
    "block",
    "ask_user",
}
RELEASE_ACTIONS = {"audit", "fix", "block", "ask_user"}
# Any operation the model may choose is mapped to a stage action. Nothing
# falls through: a tool that does not exist for the stage is its equivalent,
# not a dead end.
_TASK_ALIASES = {
    "reject": "rework",
    "release_fix": "rework",
    "release_resume": "rework",
    "release_audit": "rework",
    "release_finalize": "rework",
    "stop": "block",
}


def task_action(operation: str) -> str:
    name = str(operation or "").strip().lower()
    if name in {"retry", "run_task"}:
        return "retry"
    if name in TASK_ACTIONS:
        return name
    return _TASK_ALIASES.get(name, "rework")


def release_action(operation: str) -> str:
    name = str(operation or "").strip().lower()
    if name in {"release_resume", "release_audit"}:
        return "audit"
    if name == "ask_user":
        return "ask_user"
    if name in {"block", "stop", "cancel"}:
        return "block"
    # Every other operation means the change set goes back for a fix.
    return "fix"


def _cap(text: Any, limit: int) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return value[:limit] + "\n... [truncated]"


def _conversation(layout: ProjectLayout) -> str:
    path = layout.root / ".forgel" / "conversations" / "0.jsonl"
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-MAX_MESSAGES:]
    except OSError:
        return ""
    turns: list[str] = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        producer = str(
            item.get("agent") or item.get("role") or ""
        ).strip()
        turns.append(f"{producer}: {_cap(text, MAX_MESSAGE_CHARS)}")
    return "\n".join(turns)


def _prompt(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    stage: str,
    context: Mapping[str, Any],
) -> str:
    conversation = _conversation(layout)
    return (
        f"Project: {project.get('name')} ({project.get('id')})\n"
        f"Stage: {stage}\n\n"
        f"Situation:\n"
        + _cap(
            json.dumps(dict(context), ensure_ascii=False, indent=1),
            MAX_CONTEXT_CHARS,
        )
        + (f"\n\nRecent conversation:\n{conversation}" if conversation else "")
        + "\n\nReturn the next-step JSON now."
    )


def decide(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    stage: str,
    context: Mapping[str, Any],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> Decision:
    """Ask the controlling agent for the next step."""

    messages = [
        ModelMessage("system", SYSTEM_PROMPT),
        ModelMessage(
            "user", _prompt(layout, project, stage, context)
        ),
    ]
    try:
        raw = client.complete(
            messages, model=project_model_name(layout.control)
        )
    except ModelError as exc:
        raise ControllerError(f"the controller call failed: {exc}") from exc
    objects = json_objects(raw)
    data = objects[-1] if objects else None
    if not isinstance(data, dict):
        raise ControllerError("the controller returned no decision")
    operation = str(data.get("operation") or "").strip().lower()
    if operation not in OPERATIONS:
        raise ControllerError(
            f"the controller chose an unknown operation: {operation!r}"
        )
    feedback = data.get("feedback")
    if isinstance(feedback, str):
        feedback = [feedback]
    if not isinstance(feedback, list):
        feedback = []
    args = data.get("args")
    if not isinstance(args, dict):
        args = {}
    decision = Decision(
        operation=operation,
        reason=str(data.get("reason") or "").strip(),
        summary=str(data.get("summary") or "").strip(),
        feedback=[
            str(item).strip() for item in feedback if str(item).strip()
        ],
        issue=str(data.get("issue") or "").strip(),
        question=str(data.get("question") or "").strip(),
        release_id=str(data.get("release_id") or "").strip(),
        args=args,
    )
    usage = getattr(client, "last_usage", None)
    if not isinstance(usage, dict):
        usage = {}
    hit, miss = cache_tokens(usage)
    ledger.append_event(
        str(project["id"]),
        "controller",
        status=decision.operation,
        idempotency_key=(
            f"{project['id']}:controller:{stage}:{uuid.uuid4().hex}"
        ),
        payload={
            "stage": stage,
            "operation": decision.operation,
            "model_calls": 1,
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(
                usage.get("completion_tokens") or 0
            ),
            "cache_hit_tokens": hit,
            "cache_miss_tokens": miss,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[controller] {stage}: {decision.operation}"
        + (f" — {decision.reason}" if decision.reason else "")
    )
    return decision
