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
import subprocess
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
from .repo_tools import (
    MAX_READ_CHARS,
    RESEARCH_ACTIONS,
    RepoActionError,
    execute_repo_action,
)
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)

CONVERSATION_DIR = ".forgel"
CONVERSATIONS_DIR = "conversations"
HISTORY_RECENT_CHARS = 12_000
HISTORY_COMPACT_CHARS = 24_000
HISTORY_KEEP_TURNS = 4
HISTORY_SUMMARY_CHARS = 6_000
MAX_CONTEXT_CHARS = 24_000
OVERVIEW_DOC_CHARS = 4_000
OVERVIEW_TOTAL_CHARS = 14_000
MAX_RESEARCH_STEPS = 6
GENERIC_SKIP_DIRS = {
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

Before answering questions about the project, its documents or its code,
inspect the repository yourself. Reply with exactly one JSON action:
{"kind": "action", "action": "list_files", "action_args": {"path": ".", "repo_id": "main"}}
{"kind": "action", "action": "read_file", "action_args": {"path": "PLAN.md", "repo_id": "main"}}
Paths are relative and may not leave the repository. Read PLAN.md, README.md,
FORGEL.md, docs and code instead of guessing. Do not read files under
docs/program: that is Forgel's process state, not project documentation. After
the observation, return the final answer JSON.

Return JSON only. Never emit tool-call markup such as <｜｜DSML｜｜> or XML;
the runtime understands only the JSON forms above.

Read only what the question needs: list a directory to discover names, then
read specific files. Do not read the whole repository. Files already read are
provided in the context; use them instead of re-reading unchanged files, and
re-read only when you need a different part or the file changed.

The user is the product owner, not a Forgel developer. Answer from the
project documents and code, not from Forgel's process metadata. For any
question about status, plans or what to do next, use README, PLAN and the
project's docs (the context already includes them). Do not invent process
steps such as setting a recipe or a checkpoint.

The runtime is already configured. Never tell the user to set
FORGEL_MODEL_API_KEY, run `forgel setup`, or configure GitHub unless the
runtime output explicitly says it is missing.

Never use these words with the user unless they ask for them: adopted,
linked, generation, checkpoint, staging, production approval, proposal,
recipe, ledger, program.yaml, forgel.toml, agent run, provider. Describe the
work in ordinary product language: what is done, what is pending, what needs
a decision, and the concrete next step from the project's roadmap. Earlier
turns may contain these terms; keep their facts but restate them plainly.

Reply in the language of the user's message. Return exactly one JSON object:
{
  "kind": "answer" | "change_request" | "action" | "actions",
  "reply": "text for the user",
  "action": "one of the actions below, action only",
  "action_args": {"...": "action parameters"},
  "actions": [
    {"action": "one of the actions below", "action_args": {"...": "..."}}
  ],
  "title": "short title, change_request only",
  "summary": "one paragraph, change_request only",
  "requirements": ["explicit requirement", "..."],
  "acceptance": ["criterion", "..."],
  "constraints": ["constraint", "..."],
  "repo_id": "one of the repositories in program.yaml, or empty",
  "test_command": ["command", "arg"] or [],
  "assumptions": ["what you decided where the request was silent"]
}

kind="answer" must include a non-empty plain-text "reply". Never answer a
question with a plan or task object; the plan action is separate and needs a
milestone goal.

If the request contains several executable steps ("accept and move on",
"do X then Y"), return kind="actions" with every step in order. Execute the
whole request now; never defer a step to the next message. When the user says
"move on" or "continue", choose the next executable step from the project
plan and include it; do not ask which step. Stop only for a missing required
argument, a material fork, an irreversible action or a human gate.

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


SUMMARY_PROMPT = """You compact the conversation of a project assistant.

Preserve decisions, facts, file names, user preferences, open questions and
what was already done. Write in the same language as the conversation. Be
concise and concrete. Return plain text, not JSON, and no process field
names or identifiers unless they are essential.
"""


@dataclass(frozen=True)
class AgentResult:
    text: str
    kind: str
    request: str | None = None
    task_id: str | None = None
    action: str = ""
    args: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None


def _session_key(session: str) -> str:
    key = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(session).strip())[:64]
    return key or "default"


def conversations_dir(layout: ProjectLayout) -> Path:
    return layout.root / CONVERSATION_DIR / CONVERSATIONS_DIR


def conversation_path(layout: ProjectLayout, session: str = "") -> Path:
    path = conversations_dir(layout) / f"{_session_key(session)}.jsonl"
    legacy = layout.root / CONVERSATION_DIR / "conversation.jsonl"
    if not path.exists() and legacy.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        legacy.replace(path)
    return path


def session_state_path(layout: ProjectLayout, session: str = "") -> Path:
    return conversations_dir(layout) / f"{_session_key(session)}.session.json"


def load_session_state(
    layout: ProjectLayout, session: str = ""
) -> dict[str, Any]:
    path = session_state_path(layout, session)
    if not path.exists():
        return {"summary": "", "compacted": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"summary": "", "compacted": 0}
    if not isinstance(data, dict):
        return {"summary": "", "compacted": 0}
    try:
        compacted = max(0, int(data.get("compacted", 0)))
    except (TypeError, ValueError):
        compacted = 0
    return {"summary": str(data.get("summary", "")), "compacted": compacted}


def save_session_state(
    layout: ProjectLayout,
    state: Mapping[str, Any],
    session: str = "",
) -> None:
    path = session_state_path(layout, session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "summary": str(state.get("summary", "")),
                "compacted": int(state.get("compacted", 0)),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_history(
    layout: ProjectLayout,
    limit: int | None = None,
    session: str = "",
) -> list[dict[str, Any]]:
    path = conversation_path(layout, session)
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
                "tool",
            }:
                turns.append(item)
    except OSError:
        return []
    if limit is None:
        return turns
    return turns[-limit:]


def append_history(
    layout: ProjectLayout,
    role: str,
    text: str,
    actor: str = "",
    session: str = "",
    tool: str = "",
    path: str = "",
) -> None:
    path_obj = conversation_path(layout, session)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "role": role,
        "text": text,
        "actor": actor,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if tool:
        entry["tool"] = tool
    if path:
        entry["path"] = path
    with path_obj.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _tracked_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [item for item in result.stdout.split("\0") if item]


def _repo_files(root: Path) -> list[str]:
    tracked = _tracked_files(root)
    if tracked:
        return tracked
    files: list[str] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in GENERIC_SKIP_DIRS
        )
        for name in sorted(filenames):
            files.append(
                (Path(directory) / name).relative_to(root).as_posix()
            )
    return files


def _unsafe_name(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    if name == ".env.example":
        return False
    return (
        name.startswith(".env")
        or name.endswith((".pem", ".key"))
        or name.startswith(("id_rsa", "id_ed25519"))
    )


def _workspace_tree(root: Path, limit: int = 80) -> str:
    files = [
        item for item in _repo_files(root) if not _unsafe_name(item)
    ]
    lines = files[:limit]
    if len(files) > limit:
        lines.append("...")
    return "\n".join(lines)


def _doc_excerpt(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    headings = [
        line for line in text.splitlines() if re.match(r"^#{1,3} ", line)
    ]
    return (
        text[:limit]
        + "\n... [truncated; document headings] ...\n"
        + "\n".join(headings[:80])
    )


def _repository_overview(
    layout: ProjectLayout, repos: list[dict[str, Any]]
) -> str:
    """Read the project's own documentation from tracked files."""

    if not repos:
        return ""
    main_id = next(
        (str(entry["id"]) for entry in repos if entry["id"] == "main"),
        str(repos[0]["id"]),
    )
    root = layout.repo_path(main_id)
    documents = []
    for relative in sorted(_repo_files(root)):
        if not relative.endswith(".md"):
            continue
        if "/" in relative and not (
            relative.startswith("docs/")
            and not relative.startswith("docs/program/")
        ):
            continue
        path = root / relative
        if path.is_file():
            documents.append(path)
    parts: list[str] = []
    budget = OVERVIEW_TOTAL_CHARS
    for path in documents:
        if budget <= 0:
            break
        relative = path.relative_to(root).as_posix()
        excerpt = _doc_excerpt(path, min(OVERVIEW_DOC_CHARS, budget))
        if not excerpt:
            continue
        budget -= len(excerpt)
        parts.append(f"--- {relative} ---\n{excerpt}")
    return "\n\n".join(parts)


def _plain_brief(text: str) -> str:
    brief = str(text or "").strip()
    lowered = brief.lower()
    if lowered.startswith("adopted in place"):
        return "Existing project, taken over in place."
    if lowered.startswith("adopted from "):
        return "Existing project from " + brief[len("Adopted from "):]
    return brief


def build_context(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    ledger: Ledger,
) -> str:
    """Build a human-facing context from project documents and current work."""

    parts = [
        f"Project: {project['name']} ({project['id']})",
        f"Brief: {_plain_brief(project.get('brief', ''))}",
    ]
    repos = manifest_entries(layout)
    repo_lines = "\n".join(
        f"- {entry['id']} ({entry.get('role', 'application')})"
        for entry in repos
    ) or "- none"
    parts.append("Repositories:\n" + repo_lines)

    task_items = tasks.list_tasks(layout)
    if task_items:
        counts: dict[str, int] = {}
        for item in task_items:
            status = str(item.get("status", ""))
            counts[status] = counts.get(status, 0) + 1
        summary = ", ".join(
            f"{count} {status}" for status, count in sorted(counts.items())
        )
        recent = "\n".join(
            f"- {item.get('title', '')} ({item.get('status', '')})"
            for item in task_items[-5:]
        )
        parts.append(
            f"Current work: {len(task_items)} task(s) — {summary}\n{recent}"
        )
    else:
        parts.append("Current work: no tasks planned yet.")

    plans_dir = layout.artifact("docs/program/plans")
    plans = sorted(plans_dir.glob("*.md")) if plans_dir.is_dir() else []
    if plans:
        first = plans[-1].read_text(encoding="utf-8").splitlines()
        goal = first[0][len("# Plan: ") :] if first else ""
        parts.append(f"Current plan: {goal or plans[-1].stem}")

    overview = _repository_overview(layout, repos)
    if overview:
        parts.append("Project documents:\n" + overview)

    main_id = next(
        (str(entry["id"]) for entry in repos if entry["id"] == "main"),
        str(repos[0]["id"]) if repos else "",
    )
    if main_id:
        tree = _workspace_tree(layout.repo_path(main_id))
        if tree:
            parts.append("Files:\n" + tree)

    context = "\n\n".join(parts)
    return context[:MAX_CONTEXT_CHARS]


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "request"


def _cap(text: str, limit: int = MAX_READ_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


def _json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _looks_like_tool_markup(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "<｜｜dsml｜｜",
            "<|",
            "<tool_call",
            "<function_call",
            "<system_warning",
        )
    )


def _looks_structured(text: str) -> bool:
    """True when a model reply is a raw structure, not prose."""

    if _looks_like_tool_markup(text):
        return True
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    return stripped.startswith(("{", "["))


UNFORMATTED_REPLY = (
    "The model returned no readable answer. Please try again."
)


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
        return {
            "kind": "answer",
            "reply": (
                UNFORMATTED_REPLY
                if _looks_structured(raw)
                else raw.strip()
            ),
        }
    if not isinstance(data, dict):
        return {
            "kind": "answer",
            "reply": (
                UNFORMATTED_REPLY
                if _looks_structured(raw)
                else raw.strip()
            ),
        }
    kind = data.get("kind")
    if kind not in {"answer", "change_request", "action", "actions"}:
        kind = "answer"
    action = str(data.get("action", "")).strip()
    action_args = data.get("action_args")
    if not isinstance(action_args, dict):
        action_args = {}
    if kind == "action" and action not in AGENT_ACTIONS:
        kind = "answer"
        action = ""
        action_args = {}
    actions: list[dict[str, Any]] = []
    raw_actions = data.get("actions")
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            name = str(item.get("action", "")).strip()
            if name not in AGENT_ACTIONS:
                continue
            args = item.get("action_args")
            actions.append(
                {
                    "action": name,
                    "action_args": args if isinstance(args, dict) else {},
                }
            )
    if kind == "action" and action and not actions:
        actions.append(
            {"action": action, "action_args": action_args}
        )
    if kind == "actions" and not actions:
        kind = "answer"
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        if kind in {"action", "actions"}:
            reply = ""
        else:
            reply = (
                UNFORMATTED_REPLY
                if _looks_structured(raw)
                else raw.strip()
            )
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
        "actions": actions,
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


def _turn_chars(turns: list[dict[str, Any]]) -> int:
    return sum(len(str(turn.get("text", ""))) for turn in turns)


def _recent_turns(
    turns: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used = 0
    for turn in reversed(turns):
        size = len(str(turn.get("text", "")))
        if selected and used + size > limit:
            break
        selected.append(turn)
        used += size
    return list(reversed(selected))


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

    def narrate(
        self,
        project: Mapping[str, Any],
        question: str,
        observation: str,
    ) -> str:
        """Turn a runtime status dump into a natural-language answer."""

        layout = ProjectLayout.detect(project["workspace"])
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "You are Forgel's project agent. The runtime executed "
                    "the action the user asked for. Turn the observation "
                    "into a short natural-language answer in the user's "
                    "language. Use only facts from the observation; never "
                    "invent state. Do not dump raw key:value fields or "
                    "process identifiers unless they help. Return plain "
                    "text, not JSON."
                ),
            ),
            ModelMessage(
                role="user",
                content=(
                    f"Project: {project['name']} ({project['id']})\n\n"
                    f"User question:\n{question}\n\n"
                    f"Runtime observation:\n{observation}\n\n"
                    "Answer the user naturally and briefly."
                ),
            ),
        ]
        try:
            raw = self.client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError:
            return (
                "I couldn't summarize the project state just now. "
                "Please retry."
            )
        answer = parse_answer(raw)
        reply = str(answer.get("reply", "")).strip()
        if not reply or _looks_structured(reply):
            return (
                "I couldn't summarize the project state just now. "
                "Please retry."
            )
        return reply

    def _session_history(
        self, layout: ProjectLayout, session: str
    ) -> str:
        history = load_history(layout, session=session)
        state = load_session_state(layout, session)
        compacted = min(int(state.get("compacted", 0)), len(history))
        pending = history[compacted:]
        if (
            len(pending) > HISTORY_KEEP_TURNS
            and _turn_chars(pending) > HISTORY_COMPACT_CHARS
        ):
            state = self._compact_session(
                layout, session, history, state
            )
            compacted = min(
                int(state.get("compacted", 0)), len(history)
            )
            pending = history[compacted:]
        recent = _recent_turns(pending, HISTORY_RECENT_CHARS)
        parts: list[str] = []
        summary = str(state.get("summary", "")).strip()
        if summary:
            parts.append("Session summary:\n" + summary)
        if recent:
            lines: list[str] = []
            for turn in recent:
                role = str(turn.get("role", ""))
                if role == "assistant" and (
                    str(turn.get("text", "")) == UNFORMATTED_REPLY
                ):
                    continue
                if role == "tool":
                    path = str(turn.get("path", ""))
                    if path.startswith("docs/program/"):
                        continue
                    label = "Tool result"
                    tool = str(turn.get("tool", "")).strip()
                    path = str(turn.get("path", "")).strip()
                    if tool or path:
                        label += f" ({tool} {path})".rstrip()
                else:
                    label = role.capitalize()
                lines.append(f"{label}: {turn.get('text', '')}")
            parts.append("Recent conversation:\n" + "\n".join(lines))
        return "\n\n".join(parts)

    def _compact_session(
        self,
        layout: ProjectLayout,
        session: str,
        history: list[dict[str, Any]],
        state: Mapping[str, Any],
    ) -> dict[str, Any]:
        compacted = min(
            int(state.get("compacted", 0)), len(history)
        )
        end = max(compacted, len(history) - HISTORY_KEEP_TURNS)
        chunk = history[compacted:end]
        if not chunk:
            return dict(state)
        transcript = "\n".join(
            f"{turn.get('role')}: {turn.get('text', '')}"
            for turn in chunk
        )
        messages = [
            ModelMessage("system", SUMMARY_PROMPT),
            ModelMessage(
                "user",
                f"Existing summary:\n"
                f"{state.get('summary') or '(none)'}\n\n"
                f"Conversation to compact:\n{transcript}",
            ),
        ]
        try:
            raw = self.client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError:
            return dict(state)
        answer = parse_answer(raw)
        summary = str(answer.get("reply", "")).strip()
        if not summary or _looks_structured(summary):
            return dict(state)
        combined = (
            str(state.get("summary", "")) + "\n" + summary
        ).strip()
        if len(combined) > HISTORY_SUMMARY_CHARS:
            combined = combined[-HISTORY_SUMMARY_CHARS:]
        new_state = {"summary": combined, "compacted": end}
        save_session_state(layout, new_state, session)
        return new_state

    def handle(
        self,
        project: Mapping[str, Any],
        text: str,
        actor: str,
        session: str = "",
    ) -> AgentResult:
        layout = ProjectLayout.detect(project["workspace"])
        context = build_context(layout, project, self.ledger)
        history_text = self._session_history(layout, session)
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
                    f"Session so far:\n{history_text or '(new session)'}\n\n"
                    f"New message:\n{text}"
                ),
            ),
        ]
        append_history(layout, "user", text, actor, session=session)
        model = project_model_name(layout.control)
        repos = manifest_entries(layout)
        raw = ""
        markup_retries = 0
        answer_retries = 0
        for step in range(MAX_RESEARCH_STEPS + 1):
            try:
                raw = self.client.complete(messages, model=model)
            except ModelError as exc:
                return AgentResult(
                    text=f"Model call failed: {exc}",
                    kind="error",
                )
            data = _json_object(raw)
            action = str(data.get("action", "")) if data else ""
            if action not in RESEARCH_ACTIONS:
                if _looks_like_tool_markup(raw) and markup_retries < 2:
                    messages.append(
                        ModelMessage("assistant", raw.strip())
                    )
                    messages.append(
                        ModelMessage(
                            "user",
                            "Return exactly one JSON object, not tool-call "
                            "markup. Read files with "
                            '{"kind": "action", "action": "read_file", '
                            '"action_args": {"path": "..."}} and answer with '
                            '{"kind": "answer", "reply": "..."}.',
                        )
                    )
                    markup_retries += 1
                    continue
                candidate = parse_answer(raw)
                unreadable = candidate["kind"] == "answer" and (
                    not str(candidate["reply"]).strip()
                    or candidate["reply"] == UNFORMATTED_REPLY
                )
                if unreadable and answer_retries < 2:
                    messages.append(
                        ModelMessage("assistant", raw.strip())
                    )
                    messages.append(
                        ModelMessage(
                            "user",
                            "That reply cannot be shown to the user. Return "
                            "exactly one JSON object with kind=answer and a "
                            "non-empty plain-text reply. Do not return a "
                            "plan, a task list, tool-call markup or an "
                            "empty reply. Use a read_file action if you "
                            "still need a file.",
                        )
                    )
                    answer_retries += 1
                    continue
                break
            if step == MAX_RESEARCH_STEPS:
                return AgentResult(
                    text=(
                        "I need more file reads than allowed for one answer. "
                        "Please narrow the question."
                    ),
                    kind="error",
                )
            args = dict(data.get("action_args") or {})
            for key in ("path", "repo_id"):
                if key in data and key not in args:
                    args[key] = data[key]
            research = {"action": action, **args}
            try:
                observation = execute_repo_action(layout, repos, research)
            except RepoActionError as exc:
                observation = f"error: {exc}"
            append_history(
                layout,
                "tool",
                _cap(observation),
                actor,
                session=session,
                tool=action,
                path=str(args.get("path") or ""),
            )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observation:\n"
                    + _cap(observation)
                    + "\n\nContinue with another action or the final "
                    "JSON answer.",
                )
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

        append_history(
            layout, "assistant", result_text, actor, session=session
        )
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
            actions=answer.get("actions") or [],
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
