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
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import limits, tasks
from .config import Settings
from .context_window import CONTEXT_ACTION, ContextWindow, Item
from .environment import load_environment, render_environment
from .instructions import instruction_context
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    cache_tokens,
    project_model_name,
)
from .model_output import json_objects, looks_like_tool_markup

MAX_CONTEXT_PAGES = 40
MAX_MARKUP_RETRIES = 3

OPERATIONS = (
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
- task_retry: queue the task again unchanged;
- task_restart: rewrite the specification from the task request and run it
  again from the beginning;
- rework: send the work back with concrete feedback;
- respec: the specification is the defect; rewrite it for the given issue;
- accept: the work meets the requirements; accept it;
- reject: the work does not meet the requirements; send it back;
- cancel: the work is no longer wanted;
- block: stop the work and keep the reason;
- run_task, task_process, task_qa, task_review: run a task operation now;
- release_resume, release_audit, release_finalize, release_fix: run a
  release operation now;
- set_limit {name, seconds}: raise a runtime limit when the work
  legitimately needs more room (the limits block lists the known limits);
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

Return JSON only. Never emit tool-call markup such as <｜｜DSML｜｜> or XML;
the runtime understands only the JSON forms above.

Use only the facts in the context. Do not repeat what is already proven to
work. Do not ask the owner to choose between internal process options.
Every inactive task carries its full record and specification in the context.
The "stopped" list names the tasks a release operation acts on; the other
inactive tasks are context. Read the tasks before choosing.

The context is paged, not truncated. The manifest lists every item and its
page count; the first pages that fit are shown. To read any page, answer only
with {"action": "context_page", "key": "<item key>", "page": <n>}; the
runtime returns that page and asks again. Use it before deciding when a fact
you need is not shown.
"""


TASK_ACTIONS = {
    "retry",
    "task_retry",
    "task_restart",
    "set_limit",
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
RELEASE_ACTIONS = {
    "audit",
    "fix",
    "block",
    "ask_user",
    "set_limit",
    "task_retry",
    "task_restart",
    "respec",
}
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
    if name in {"task_retry", "task_restart"}:
        return name
    if name == "set_limit":
        return "set_limit"
    if name in {"retry", "run_task"}:
        return "retry"
    if name in TASK_ACTIONS:
        return name
    return _TASK_ALIASES.get(name, "rework")


def release_action(operation: str) -> str:
    name = str(operation or "").strip().lower()
    if name in {"task_retry", "task_restart"}:
        return name
    if name == "set_limit":
        return "set_limit"
    if name == "respec":
        return "respec"
    if name in {"release_resume", "release_audit"}:
        return "audit"
    if name == "ask_user":
        return "ask_user"
    if name in {"block", "stop", "cancel"}:
        return "block"
    # Every other operation means the change set goes back for a fix.
    return "fix"


PERMISSIONS = """You decide the next step; you do not edit files, run commands or change a check.
- retry: requeue the same work unchanged. The agent runs again with the same task and the same repository tests.
- rework: send the work back with feedback. The same repository tests run again; feedback cannot change a test command, a limit or a missing tool.
- respec: rewrite the specification text from "issue"; the repository test commands and the environment gate stay as they are. The issue states the behavior defect in plain product terms: never a command, file path, code, tool name or runtime mechanic.
- set_limit {name, seconds}: raise a runtime limit (the limits item lists them).
- accept/reject: decide on work that already meets or misses the requirements.
- cancel/block/stop: end the work and report the state.
The coding agent edits files and runs repository commands; its git is read-only. The runtime commits the selected change set. Never send work back to make the agent run a git write command or perform a commit.
Before retry or rework, compare the failure with the checks, the environment and the limits: if the same command would produce the same result, a repeat cannot help. Use set_limit when a limit cut the work; stop when the task cannot succeed as written.
When the stop is a review rejection, verify every blocking finding against the net diff and the commit series. A finding about a change that a later commit reverted is invalid; a correct change that is merely unrelated to the task is not a defect in the work. Do not send work back for an invalid finding: accept the task when its requirements are met; reject it when the work itself is wrong."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _conversation(layout: ProjectLayout) -> str:
    path = layout.root / ".forgel" / "conversations" / "0.jsonl"
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
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
        turns.append(f"{producer}: {text}")
    return "\n".join(turns)


def _history(
    ledger: Ledger, project_id: str, data: Mapping[str, Any]
) -> str:
    decisions: list[dict[str, Any]] = []
    try:
        events = ledger.events(project_id)
    except Exception:  # noqa: BLE001 - history is optional context
        events = []
    for event in events[-40:]:
        if str(event.get("stage")) != "controller":
            continue
        payload = event.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        decisions.append(
            {
                "at": event.get("created_at"),
                "stage": (payload or {}).get("stage"),
                "operation": (payload or {}).get("operation"),
            }
        )
    return json.dumps(
        {
            "attempts": data.get("attempts"),
            "rework_count": data.get("rework_count"),
            "resume_count": data.get("resume_count"),
            "feedback": data.get("feedback"),
            "last_failure": data.get("last_failure"),
            "previous_controller_decisions": decisions[-10:],
        },
        ensure_ascii=False,
        indent=1,
    )


def _task_id(context: Mapping[str, Any]) -> str:
    task = context.get("task")
    if not isinstance(task, Mapping):
        return ""
    return str(task.get("id") or "").strip()


def _task_items(
    layout: ProjectLayout,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    key_suffix: str = "",
    details: bool = False,
) -> list[Item]:
    """The record, specification and optional evidence for one task."""

    task_id = str(task.get("id") or "")
    label = str(task.get("title") or task_id)
    suffix = f":{key_suffix}" if key_suffix else ""
    items = [
        Item(
            f"task{suffix}",
            f"the full task record: {label}",
            json.dumps(task, ensure_ascii=False, indent=1),
        )
    ]
    result = task.get("result") or {}
    items.append(
        Item(
            f"history{suffix}",
            f"attempts and previous decisions: {label}",
            _history(ledger, str(project.get("id")), result),
        )
    )
    spec_ref = str(task.get("spec") or "").strip()
    spec = _read(
        layout.artifact(spec_ref)
        if spec_ref
        else layout.artifact(f"docs/program/specs/{task_id}.md")
    )
    if spec:
        items.append(
            Item(
                f"specification{suffix}",
                f"the task specification: {label}",
                spec,
            )
        )
    if details:
        for report_suffix, key, title in (
            ("", "agent_report", "the agent's report"),
            (".qa.md", "qa_report", "the QA report"),
            (".review.md", "review_report", "the review report"),
        ):
            text = _read(
                layout.artifact(
                    f"docs/program/agent/{task_id}{report_suffix}.md"
                )
            )
            if text:
                items.append(Item(f"{key}{suffix}", f"{title}: {label}", text))
        try:
            from .task_review import task_diff, _commit_series

            diff = task_diff(layout, task)
            series = _commit_series(layout, task)
        except Exception:  # noqa: BLE001 - the diff is optional context
            diff = ""
            series = ""
        if diff:
            items.append(
                Item(
                    f"diff{suffix}",
                    f"the task's net change: {label}",
                    diff,
                )
            )
        if series:
            items.append(
                Item(
                    f"commit_series{suffix}",
                    f"the task's commits in order: {label}",
                    series,
                )
            )
    return items


def _window(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    ledger: Ledger,
    stage: str,
    context: Mapping[str, Any],
) -> ContextWindow:
    items: list[Item] = [
        Item(
            "failure",
            "the failure that stopped the work",
            json.dumps(
                context.get("failure") or {},
                ensure_ascii=False,
                indent=1,
            ),
        ),
        Item(
            "situation",
            "the stage context",
            json.dumps(dict(context), ensure_ascii=False, indent=1),
        ),
    ]
    seen_tasks: set[str] = set()
    task_id = _task_id(context)
    if task_id:
        task = tasks.get_task(layout, task_id)
        if task is not None:
            seen_tasks.add(task_id)
            items.extend(
                _task_items(
                    layout, ledger, project, task, details=True
                )
            )
    stopped_tasks = context.get("tasks")
    if isinstance(stopped_tasks, list):
        for entry in stopped_tasks:
            if not isinstance(entry, Mapping):
                continue
            stopped_id = str(entry.get("id") or "").strip()
            if not stopped_id or stopped_id in seen_tasks:
                continue
            task = tasks.get_task(layout, stopped_id)
            if task is None:
                continue
            seen_tasks.add(stopped_id)
            items.extend(
                _task_items(
                    layout,
                    ledger,
                    project,
                    task,
                    key_suffix=stopped_id,
                    details=str(task.get("status") or "")
                    in {"failed", "blocked"},
                )
            )
    try:
        environment = load_environment(layout)
    except Exception:  # noqa: BLE001 - a broken contract is context too
        environment = None
    if environment is not None:
        items.append(
            Item(
                "environment",
                "the environment contract",
                render_environment(environment),
            )
        )
    instructions = instruction_context(layout)
    if instructions:
        items.append(
            Item(
                "instructions",
                "project and repository instructions",
                instructions,
            )
        )
    values = {**limits.LIMITS, **limits.load(layout)}
    items.append(
        Item(
            "limits",
            "runtime limits and how to raise them",
            json.dumps(
                {
                    "values": values,
                    "reasons": limits.REASONS,
                    "set_with": (
                        'set_limit {"name": "<limit>", "seconds": <n>}'
                    ),
                },
                ensure_ascii=False,
                indent=1,
            ),
        )
    )
    items.append(
        Item(
            "permissions",
            "what you can and cannot change",
            PERMISSIONS,
        )
    )
    release = context.get("release")
    if isinstance(release, Mapping):
        items.append(
            Item(
                "release",
                "the stopped release",
                json.dumps(dict(release), ensure_ascii=False, indent=1),
            )
        )
    release_tasks = context.get("tasks")
    if isinstance(release_tasks, list):
        items.append(
            Item(
                "release_tasks",
                "the release's inactive tasks",
                json.dumps(
                    release_tasks, ensure_ascii=False, indent=1
                ),
            )
        )
    escalations = layout.artifact("docs/program/escalations")
    if escalations.is_dir():
        blocks = []
        for path in sorted(escalations.glob("*.md"))[-5:]:
            text = _read(path)
            if text.strip():
                blocks.append(f"--- {path.name} ---\n{text[:4_000]}")
        if blocks:
            items.append(
                Item(
                    "escalations",
                    "changes escalated to the planner",
                    "\n\n".join(blocks),
                )
            )
    conversation = _conversation(layout)
    if conversation:
        items.append(
            Item("conversation", "the project conversation", conversation)
        )
    return ContextWindow(items)


def _prompt(
    project: Mapping[str, Any], stage: str, window: ContextWindow
) -> str:
    return (
        f"Project: {project.get('name')} ({project.get('id')})\n"
        f"Stage: {stage}\n\n"
        + window.render()
        + "\n\nReturn the next-step JSON now, or request a context page "
        "with " + CONTEXT_ACTION + "."
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

    window = _window(layout, project, ledger, stage, context)
    messages = [
        ModelMessage("system", SYSTEM_PROMPT),
        ModelMessage("user", _prompt(project, stage, window)),
    ]
    input_tokens = 0
    output_tokens = 0
    cache_hit = 0
    cache_miss = 0
    calls = 0
    data: Any = None
    page_index: int | None = None
    markup_retries = 0
    for _ in range(MAX_CONTEXT_PAGES):
        try:
            raw = client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError as exc:
            raise ControllerError(
                f"the controller call failed: {exc}"
            ) from exc
        calls += 1
        usage = getattr(client, "last_usage", None)
        if isinstance(usage, dict):
            input_tokens += int(usage.get("prompt_tokens") or 0)
            output_tokens += int(usage.get("completion_tokens") or 0)
            hit, miss = cache_tokens(usage)
            cache_hit += hit
            cache_miss += miss
        objects = json_objects(raw)
        parsed = objects[-1] if objects else None
        if not isinstance(parsed, dict) and looks_like_tool_markup(raw):
            markup_retries += 1
            if markup_retries > MAX_MARKUP_RETRIES:
                raise ControllerError(
                    "the controller kept returning tool-call markup"
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return exactly one JSON object, not tool-call markup. "
                    "To read a context page use " + CONTEXT_ACTION
                    + "; then decide.",
                )
            )
            continue
        if (
            isinstance(parsed, dict)
            and str(parsed.get("action") or "") == "context_page"
        ):
            key = str(parsed.get("key") or "").strip()
            try:
                page = int(parsed.get("page") or 1)
            except (TypeError, ValueError):
                page = 0
            try:
                text = window.read(key, page)
            except (KeyError, ValueError) as exc:
                text = f"cannot read that context: {exc}"
            messages.append(ModelMessage("assistant", raw))
            if page_index is not None:
                # Keep the working set to one page: the manifest lists every
                # page, so a released page can be requested again.
                messages[page_index] = ModelMessage(
                    "user",
                    "[the previous context page was released; request it "
                    "again if you still need it]",
                )
            messages.append(
                ModelMessage(
                    "user",
                    text + "\n\nReturn the next-step JSON now.",
                )
            )
            page_index = len(messages) - 1
            log(
                f"[controller] {stage}: context {key} page {page}"
            )
            continue
        data = parsed
        break
    else:
        raise ControllerError(
            "the controller kept requesting context without deciding"
        )
    if not isinstance(data, dict):
        preview = " ".join(str(raw).split())[:300]
        raise ControllerError(
            "the controller returned no decision"
            + (f": {preview}" if preview else "")
        )
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
            "model_calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_hit_tokens": cache_hit,
            "cache_miss_tokens": cache_miss,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[controller] {stage}: {decision.operation}"
        + (f" — {decision.reason}" if decision.reason else "")
    )
    return decision
