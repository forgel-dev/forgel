"""Project-scoped conversation agent.

The agent receives context from exactly one project. There is no shared cache,
no cross-project prompt and no global conversation: isolation is enforced by
construction in :func:`build_context` and by the per-project history file.

In the current milestone the agent is the intake stage: it answers questions
from the project context and records change requests. It does not edit code and
must not claim that it did.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import tasks
from .artifacts import write_text
from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger
from .program_manifest import entries as manifest_entries
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)

CONVERSATION_DIR = ".forgel"
HISTORY_TURNS = 8
MAX_CONTEXT_CHARS = 6000
SKIP_DIRS = {
    ".git",
    ".forgel",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
}

AGENT_ACTIONS = {
    "adopt",
    "plan",
    "status",
    "tasks",
    "accept",
    "reject",
    "retry",
    "run",
    "repo_add",
    "repo_create",
    "repo_publish",
    "control_extract",
    "peak",
    "pause",
    "resume",
    "approve_staging",
}

SYSTEM_PROMPT = """You are Forgel's project agent for exactly one project.
You must use only the context and conversation of the current project. Never
mention, infer or request information about any other project.

You are the control plane. The user speaks naturally; you decide whether to
answer, to turn the request into a coding task, or to perform a process
action. Perform the action yourself — never tell the user to type a slash
command. You cannot edit code, run tests, commit or deploy, and you must
never claim that you did.

Reply in the language of the user's message. Return exactly one JSON object:
{
  "kind": "answer" | "change_request" | "action",
  "reply": "text for the user",
  "action": "one of the actions below, action only",
  "action_args": {"...": "action parameters"},
  "title": "short title, change_request only",
  "summary": "one paragraph, change_request only",
  "requirements": ["explicit requirement", "..."],
  "acceptance": ["criterion", "..."],
  "constraints": ["constraint", "..."],
  "repo_id": "one of the repositories in program.yaml, or empty",
  "test_command": ["command", "arg"] or [],
  "assumptions": ["what you decided where the request was silent"]
}

Actions (ask for the missing required argument instead of guessing only when
the action cannot run without it):
- adopt {url, brief?}: adopt a repository as a new project and select it;
  "this repository" means the working directory shown in the message.
- plan {goal, max_tasks?}: turn a milestone goal into an ordered backlog.
- status {}: project, milestone and task state.
- tasks {}: list the task queue.
- accept {task_id?}: accept the task awaiting review (the runtime picks the
  latest when omitted).
- reject {task_id?, notes?}: reject it and send the work back.
- retry {task_id?}: requeue a failed or blocked task.
- run {}: let the daemon work now.
- repo_add {url, id?, depends_on?}: add an existing repository.
- repo_create {id, org?, public?, depends_on?, description?}.
- repo_publish {id?, org?, public?}.
- control_extract {path?}: move the project state into a separate repository,
  for a project that started with one folder and grew.
- peak {policy?}: show or set the model peak policy ("always" or "off_peak").
- pause {}, resume {}.
- approve_staging {}: approve staging only.

Never change configuration or secrets, grant production approval, or perform
a destructive action; for those, answer that the user must do it explicitly.
Use kind=change_request when the user asks for a product or code change.
Use kind=answer for questions and conversation.

Autonomy (D-075):
- Work autonomously. Do not interrogate the user and never ask for permission
  to start or continue. The goal is a finished result the user can review.
- If a detail is unspecified but reversible, decide, put it in "assumptions",
  and continue. A wrong assumption is corrected in the next request.
- Return kind=answer with a question only when two interpretations would
  produce materially different products and a wrong choice wastes a full
  cycle, when the request needs an irreversible or production action
  (deleting data, production deploy, payments, secrets, legal), or when
  required access is missing. Ask one consolidated question, not a dialogue.

For a change request:
- list the explicit requirements and acceptance criteria; do not guess
  unstated features;
- set repo_id from program.yaml. With several repositories, choose the one the
  request most likely targets from the roles, dependency edges and recent
  tasks, and record why in "assumptions"; do not ask which repository. Leave
  repo_id empty only when nothing in the context points to one;
- set test_command only when the project's test command is evident from the
  context, otherwise leave it empty;
- the daemon will run the task with a separate coding agent; you cannot edit
  code yourself.
"""


class AgentError(RuntimeError):
    """The agent could not produce a usable answer."""


@dataclass(frozen=True)
class AgentResult:
    text: str
    kind: str
    request: str | None = None
    task_id: str | None = None
    action: str = ""
    args: dict[str, Any] | None = None


def conversation_path(layout: ProjectLayout) -> Path:
    return layout.root / CONVERSATION_DIR / "conversation.jsonl"


def load_history(
    layout: ProjectLayout, limit: int = HISTORY_TURNS
) -> list[dict[str, Any]]:
    path = conversation_path(layout)
    if not path.exists():
        return []
    turns: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("role") in {
                "user",
                "assistant",
            }:
                turns.append(item)
    except OSError:
        return []
    return turns[-limit:]


def append_history(
    layout: ProjectLayout, role: str, text: str, actor: str = ""
) -> None:
    path = conversation_path(layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "role": role,
        "text": text,
        "actor": actor,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_capped(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


def _workspace_tree(root: Path, limit: int = 80) -> str:
    lines: list[str] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in SKIP_DIRS
        )
        relative = Path(directory).relative_to(root)
        depth = len(relative.parts)
        if depth >= 2:
            dirnames[:] = []
        if relative != Path("."):
            lines.append(f"{relative.as_posix()}/")
        for name in sorted(filenames):
            if name in SKIP_DIRS:
                continue
            lines.append((relative / name).as_posix())
            if len(lines) >= limit:
                return "\n".join(lines)
    return "\n".join(lines)


def build_context(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    ledger: Ledger,
) -> str:
    """Build context from this project's files and ledger only."""

    parts = [
        f"Project id: {project['id']}",
        f"Project name: {project['name']}",
        f"Workspace layout: {layout.kind}",
        f"Brief: {project['brief']}",
    ]
    for relative in (
        "forgel.toml",
        "program.yaml",
        "docs/program/state.md",
        "docs/program/requirements.json",
        "docs/program/reconciliation.md",
    ):
        path = layout.artifact(relative)
        if not path.exists() or not layout.contains(path):
            continue
        text = _read_capped(path, 1500)
        if text:
            parts.append(f"--- {relative} ---\n{text}")

    events = ledger.events(project["id"])[-10:]
    if events:
        lines = [
            f"- {event['stage']} {event['status']} (gen {event['generation']})"
            for event in events
        ]
        parts.append("Recent ledger events:\n" + "\n".join(lines))

    tree = _workspace_tree(layout.root)
    if tree:
        parts.append("Workspace files:\n" + tree)

    context = "\n\n".join(parts)
    return context[:MAX_CONTEXT_CHARS]


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "request"


def parse_answer(raw: str) -> dict[str, Any]:
    """Parse a model answer, falling back to plain text for non-JSON output."""

    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"kind": "answer", "reply": raw.strip()}
    if not isinstance(data, dict):
        return {"kind": "answer", "reply": raw.strip()}
    kind = data.get("kind")
    if kind not in {"answer", "change_request", "action"}:
        kind = "answer"
    action = str(data.get("action", "")).strip()
    action_args = data.get("action_args")
    if not isinstance(action_args, dict):
        action_args = {}
    if kind == "action" and action not in AGENT_ACTIONS:
        kind = "answer"
        action = ""
        action_args = {}
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        reply = raw.strip()
    acceptance = data.get("acceptance")
    if not isinstance(acceptance, list):
        acceptance = []
    requirements = data.get("requirements")
    if not isinstance(requirements, list):
        requirements = []
    constraints = data.get("constraints")
    if not isinstance(constraints, list):
        constraints = []
    test_command = data.get("test_command")
    if not isinstance(test_command, list):
        test_command = []
    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list):
        assumptions = []
    return {
        "kind": kind,
        "reply": reply.strip(),
        "action": action,
        "action_args": action_args,
        "title": str(data.get("title", "")).strip(),
        "summary": str(data.get("summary", "")).strip(),
        "requirements": [
            str(item) for item in requirements if str(item).strip()
        ],
        "acceptance": [str(item) for item in acceptance if str(item).strip()],
        "constraints": [
            str(item) for item in constraints if str(item).strip()
        ],
        "repo_id": str(data.get("repo_id", "")).strip(),
        "test_command": [
            str(item) for item in test_command if str(item).strip()
        ],
        "assumptions": [
            str(item) for item in assumptions if str(item).strip()
        ],
    }


class ProjectAgent:
    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        client: ModelClient,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.client = client

    def handle(
        self, project: Mapping[str, Any], text: str, actor: str
    ) -> AgentResult:
        layout = ProjectLayout.detect(project["workspace"])
        context = build_context(layout, project, self.ledger)
        history = load_history(layout)
        history_text = "\n".join(
            f"{turn['role']}: {turn.get('text', '')}" for turn in history
        )
        messages = [
            ModelMessage(
                role="system",
                content=(
                    f"{SYSTEM_PROMPT}\nCurrent project: "
                    f"{project['name']} ({project['id']})."
                ),
            ),
            ModelMessage(
                role="user",
                content=(
                    f"Working directory: {os.getcwd()}\n\n"
                    f"Context:\n{context}\n\n"
                    f"Conversation:\n{history_text or '(none)'}\n\n"
                    f"New message:\n{text}"
                ),
            ),
        ]
        model = project_model_name(layout.control)
        try:
            raw = self.client.complete(messages, model=model)
        except ModelError as exc:
            return AgentResult(
                text=f"Model call failed: {exc}",
                kind="error",
            )
        answer = parse_answer(raw)
        result_text = answer["reply"]
        request = None
        task_id = None
        if answer["kind"] == "change_request":
            request = self._record_request(
                layout, project, text, actor, answer
            )
            task = self._queue_task(layout, text, answer)
            if task is not None:
                task_id = str(task["id"])
                result_text += (
                    f"\n\nRecorded as `{request}`. Queued task "
                    f"`{task_id}` for repository `{task['repo_id']}`; the "
                    "daemon will start it and report back."
                )
            else:
                result_text += (
                    f"\n\nRecorded as `{request}`. I did not queue a task: "
                    "the project has several repositories and I could not "
                    "choose one. Tell me which repository to use."
                )

        append_history(layout, "user", text, actor)
        append_history(layout, "assistant", result_text)
        self._record_call(project, model, answer["kind"])
        return AgentResult(
            text=result_text,
            kind=answer["kind"],
            request=request,
            task_id=task_id,
            action=answer.get("action", "") if answer["kind"] == "action" else "",
            args=(
                answer.get("action_args") or {}
                if answer["kind"] == "action"
                else None
            ),
        )

    def _record_request(
        self,
        layout: ProjectLayout,
        project: Mapping[str, Any],
        text: str,
        actor: str,
        answer: Mapping[str, Any],
    ) -> str:
        title = answer.get("title") or text.strip().splitlines()[0][:80]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        relative = f"docs/program/requests/{timestamp}_{_slug(title)}.md"
        acceptance = answer.get("acceptance") or []
        criteria = "\n".join(f"- {item}" for item in acceptance) or "- Not stated."
        requirements = "\n".join(
            f"- {item}" for item in (answer.get("requirements") or [])
        ) or "- See the request."
        constraints = "\n".join(
            f"- {item}" for item in (answer.get("constraints") or [])
        ) or "- None stated."
        assumptions = "\n".join(
            f"- {item}" for item in (answer.get("assumptions") or [])
        ) or "- None; the request was explicit enough."
        write_text(
            layout.artifact(relative),
            f"""# Change Request: {title}

- Status: `new`
- Project: `{project['id']}`
- Created: {datetime.now(timezone.utc).isoformat(timespec="seconds")}
- Source: Telegram ({actor})

## Request

{text}

## Summary

{answer.get('summary') or '—'}

## Requirements

{requirements}

## Acceptance Criteria

{criteria}

## Constraints

{constraints}

## Assumptions

{assumptions}
""",
        )
        generation = self.ledger.current_generation(project["id"])
        self.ledger.append_event(
            project["id"],
            "request",
            status="recorded",
            idempotency_key=(
                f"{project['id']}:g{generation}:request:"
                f"{Path(relative).stem}"
            ),
            artifact_refs=[relative],
            payload={"title": title, "actor": actor},
            generation=generation,
        )
        return relative

    def _queue_task(
        self,
        layout: ProjectLayout,
        text: str,
        answer: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        repos = manifest_entries(layout)
        if not repos:
            return None
        known = {entry["id"] for entry in repos}
        repo_id = str(answer.get("repo_id") or "").strip()
        if repo_id and repo_id not in known:
            repo_id = ""
        if not repo_id and len(repos) == 1:
            repo_id = repos[0]["id"]
        if not repo_id:
            return None
        title = (
            str(answer.get("title") or "").strip()
            or text.strip().splitlines()[0][:80]
            or "Change request"
        )
        requirements = answer.get("requirements") or [
            answer.get("summary") or text.strip()
        ]
        acceptance = answer.get("acceptance") or [
            "The explicit requirements are implemented",
            "The project tests pass",
        ]
        constraints = answer.get("constraints") or [
            "Keep the change inside the selected repository",
            "Do not add unrequested features",
        ]
        test_command = answer.get("test_command") or []
        task = tasks.create_task(
            layout,
            title,
            [str(item) for item in requirements],
            [str(item) for item in acceptance],
            [str(item) for item in constraints],
            repo_id=repo_id,
            test_command=[str(item) for item in test_command],
            assumptions=[
                str(item) for item in (answer.get("assumptions") or [])
            ],
        )
        tasks.commit_task(
            layout, str(task["id"]), f"Queue task {task['id']}"
        )
        return task

    def _record_call(
        self, project: Mapping[str, Any], model: str, kind: str
    ) -> None:
        generation = self.ledger.current_generation(project["id"])
        self.ledger.append_event(
            project["id"],
            "agent",
            status="completed",
            idempotency_key=(
                f"{project['id']}:g{generation}:agent:{os.urandom(6).hex()}"
            ),
            payload={"model": model, "kind": kind},
            generation=generation,
        )
