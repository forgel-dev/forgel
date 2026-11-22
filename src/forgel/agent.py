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
from typing import Any, Mapping, Sequence

from . import i18n, language, requirements as requirements_doc, tasks
from .artifacts import write_text
from .config import Settings
from .instructions import instruction_context
from .layout import ProjectLayout
from .ledger import Ledger
from .program_manifest import entries as manifest_entries
from .providers.github_auth import GithubAuth, GithubAuthError
from .release_train import (
    attach_blocked_release,
    discover_base,
    list_releases,
    load_release,
    new_release_id,
    plan_release,
)
from .runtime_model import process_model
from .repo_tools import (
    MAX_READ_CHARS,
    RESEARCH_ACTIONS,
    RepoActionError,
    execute_repo_action,
)
from .model_output import json_objects
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
HISTORY_VISIBLE_TURNS = 6
HISTORY_TURN_CHARS = 4_000
HISTORY_SUMMARY_CHARS = 6_000
MAX_CONTEXT_CHARS = 24_000
OVERVIEW_DOC_CHARS = 4_000
OVERVIEW_TOTAL_CHARS = 14_000
MAX_RESEARCH_STEPS = 20
MAX_MARKUP_RETRIES = 3
MAX_ANSWER_RETRIES = 3
MAX_REQUEST_RETRIES = 3
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
    "review",
    "run",
    "repo_add",
    "repo_create",
    "repo_publish",
    "release",
    "release_resume",
    "runtime",
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
repo_id is any id from the repository map (for example "code"). Use
list_files and read_file with that id to inspect any repository; the map
itself only names the repositories.
Paths are relative and may not leave the repository. Read the project
documents, manifests and source code instead of guessing; use whichever files
exist in the repository. Do not read files under
docs/program: that is Forgel's process state, not project documentation. After
the observation, return the final answer JSON.

Return JSON only. Never emit tool-call markup such as <｜｜DSML｜｜> or XML;
the runtime understands only the JSON forms above.

Read only what the question needs: list a directory to discover names, then
read specific files. Do not read the whole repository. Files already read are
provided in the conversation; use them instead of re-reading unchanged files,
and re-read only when you need a different part or the file changed.

Each repository in the context has an id, a role and a location. The map does
not describe what a repository contains. Determine the target repository
yourself: inspect the candidates with list_files and read_file using their
ids, then choose from what you actually read. The user's message and the
whole conversation are part of the request; a follow-up belongs to the
repository the conversation has been about, even when the message itself does
not name it. Set repo_id to an existing id and never leave it empty while the
conversation and the contents identify a repository.

The user is the product owner, not a Forgel developer. Answer from the
project documents and code, not from Forgel's process metadata. For any
question about status, plans or what to do next, use README, PLAN and the
project's docs (the context already includes them). Do not invent process
steps such as setting a recipe or a checkpoint.

The Runtime section states this agent's capabilities. Use it as the source of
truth for actions: do not ask the owner to configure a capability that the
Runtime section reports as available. Do not infer capabilities from the
conversation or from project artifacts; a run recorded in an artifact belongs
to the agent and environment that produced it. The conversation distinguishes
this agent's turns from reports produced by other runs; a report describes its
producer's run, not this agent's state.

The Runtime process block is the runtime map: the pipeline, the owner of each
stage, the gates and the release policy. Use it for questions about how work
moves and to stay in your role; never invent a stage, an owner or a process.

Never use these words with the user unless they ask for them: adopted,
linked, generation, checkpoint, staging, production approval, proposal,
recipe, ledger, program.yaml, forgel.toml, agent run, provider. Describe the
work in ordinary product language: what is done, what is pending, what needs
a decision, and the concrete next step from the project's roadmap. Earlier
turns may contain these terms; keep their facts but restate them plainly.

Reply in the language of the user's message.

Follow the project and repository instructions in the context. Repository
rules are more specific and take precedence on conflict. Use them for task
titles, summaries, change-request documents, plans, specifications, reports
and commit messages; chat replies follow the user's language unless the
instructions say otherwise. Return exactly one JSON object:
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
  "product_intent": "what the owner wants the product to become, in their terms; preserve a named reference product",
  "user_experience": "how the owner will use it: the main flow, the surfaces, and what the change replaces",
  "roadmap": ["ordered deliverable steps of the whole request, when it has more than one"],
  "requirements": ["explicit requirement", "..."],
  "acceptance": ["criterion", "..."],
  "constraints": ["constraint", "..."],
  "user_decisions": [
    {"decision": "product decision the user stated", "source": "where they said it"}
  ],
  "goals": ["outcome the request must achieve"],
  "non_goals": ["explicitly out of scope"],
  "user_stories": ["as a ... I want ... so that ..."],
  "tests": ["what must be tested"],
  "risks": ["what can make this fail or miss the goal"],
  "open_questions": ["only a question that cannot be decided reversibly"],
  "affected_files": ["path or area"],
  "repo_id": "an existing repository id; required for a change_request",
  "release_class": "patch for a bug fix, minor for new functionality or changed behaviour; major only for the first product release or a breaking change after 1.0.0",
  "test_command": ["command", "arg"] or [],
  "assumptions": ["what you decided where the request was silent"]
}

kind="answer" must include a non-empty plain-text "reply". Never answer a
question with a plan or task object; the plan action is separate and needs a
milestone goal.

A request to act, change something or continue is an instruction to execute
the next executable step now. Answer only for questions, status, or when a
required argument, a material fork or a human gate blocks execution. If the
request does not name the step, choose the next step from the project
documents. Never reply with what you intend to do later.

A request that spans several repositories or describes a milestone-sized
change is a plan, not one task: return kind="action", action="plan" with the
goal instead of a change_request, so the planner decomposes it.

A user request may contain several executable steps. Return every step that
can be executed now as kind="actions", in order. Do not defer an executable
step to a later user message. Stop only when a required argument is missing,
a material fork remains, the action is irreversible, or a human gate is
required.

Actions (ask for the missing required argument instead of guessing only when
the action cannot run without it):
- adopt {url, brief?}: adopt a repository as a new project and select it;
  "this repository" means the working directory shown in the message.
- plan {goal, product_intent?, user_experience?, roadmap?, release_class?,
  max_tasks?}: turn a milestone goal into an ordered backlog and one release;
  release_class follows the same rule as a change request. Pass the product
  intent, the experience and the roadmap exactly as the owner stated them.
- status {}: project, milestone and task state.
- tasks {}: list the task queue.
- accept {task_id?}: accept the task awaiting review (the runtime picks the
  latest when omitted).
- reject {task_id?, notes?}: reject it and send the work back.
- retry {task_id?}: requeue a failed or blocked task.
- review {task_id?}: re-run QA and review for a task awaiting a decision,
  for example after the reviewer could not produce a verdict.
- run {}: let the daemon work now.
- repo_add {url, id?, depends_on?}: add an existing repository.
- repo_create {id, org?, public?, depends_on?, description?}.
- repo_publish {id?, org?, public?}.
- release {version, repo?}: publish the project's repositories now as a manual
  release; version is the tag the user asked for without the leading `v`
  (for example "0.1.0").
- release_resume {release_id?}: put a stopped release back into the release
  train so it is audited and published again.
- runtime {operation, task_id?, release_id?}: run or restart one runtime
  operation now, in the order the state needs. Operations: drive (advance one
  daemon iteration), orchestrate (run the project pipeline to the next gate),
  task_process (QA, review and acceptance for a task), task_qa, task_review,
  release_audit, release_finalize.
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
- Reconcile the request with the current state first. If an open task or a
  stopped release already carries this work, act on that state (run, retry,
  review or release_resume) instead of queueing another task. Queue a new
  task only for work that no open task and no stopped release covers.
- Treat the user's explicit product decisions as binding requirements. Scan
  the whole conversation — earlier messages, answers to clarifying questions,
  implementation remarks and later follow-ups — not only the last message.
  Put every decision in "user_decisions"; never omit one and never ask the
  user to confirm a decision already made. A later decision overrides an
  earlier one.
- Record the owner's product intent and the experience they described under
  "product_intent" and "user_experience". Preserve a named reference product
  and what the change replaces. If the intent is materially ambiguous between
  different products, ask one consolidated question before queueing.
- Record the ordered roadmap of the whole request under "roadmap" when it has
  more than one deliverable step. A change_request is one deliverable; a
  multi-step request returns the plan action with its goal and roadmap.
- Write the change-request document in the artifact language required by the
  project and repository instructions even when the chat reply is in the
  the user's language. State the request as requirements and decisions; do
  not paste the user's raw message into the document.
- Fill goals, non-goals, user stories, tests, risks, open questions and
  affected files for the document. Leave a list empty only when the
  conversation truly has nothing to add.
- list the explicit functional requirements and acceptance criteria; do not
  guess unstated features;
- when the request depends on an external interface (a tool, a service, a
  data format, a protocol), record the relevant contract in the requirements
  or assumptions from its authoritative source; never leave the coder to
  guess it;
- determine repo_id by reading the candidate repositories with list_files
  and read_file, then set the id whose contents match the request and the
  whole conversation. A follow-up belongs to the repository the conversation
  is about. If the work needs a repository that does not exist, use the
  repo_create action instead of inventing an id. Record an inferred choice in
  "assumptions";
- every change request is a release. Set release_class to "patch" for a bug
  fix and "minor" for new functionality or a change in existing behaviour.
  Before 1.0.0 a breaking change is still a minor release. Use "major" only
  when the user explicitly asks for the first product release or, after
  1.0.0, for a change that breaks a published contract;
- set test_command only when the project's test command is evident from the
  context, otherwise leave it empty;
- the runtime release train owns release versions, tags and publication. Do
  not state, promise or choose a version or tag yourself; report the queued
  change and let the release report carry the version;
- the daemon will run the task with a separate coding agent; you cannot edit
  code yourself.
"""


class AgentError(RuntimeError):
    """The agent could not produce a usable answer."""


EXPLAIN_PROMPT = """You are Forgel's project agent. Your job is diagnosis, not
a status report. The project owner wants to know what exactly did not work and
why, in the language of their latest message.

Rules:
- Open with the concrete malfunction: which step, command, file or criterion
  broke. The task status is the outcome, never the explanation; do not lead
  with it and do not restate it.
- Give the mechanism from the evidence in the context. Connect cause to
  effect: why that made the task impossible to finish. Distinguish the root
  cause from the symptom.
- Use the task requirements, acceptance criteria, checks, actions, command
  exits, QA report, review defects and plan state together. Do not explain one
  field in isolation.
- Then state the consequence for the milestone and the concrete unblock: what
  the runtime does automatically, what needs a retry or a criteria change, and
  what the owner must decide. If nothing is required, say so plainly.
- If the evidence is insufficient to name a cause, say which evidence is
  missing; never guess and never substitute "a process error", "an internal
  error" or "something went wrong".
- Recorded user decisions are binding. Never ask the owner to confirm a
  decision already in the conversation or in the user-decision log; ask only
  for a detail that is genuinely missing.
- Use only facts present in the context. Never invent files, results, state or
  decisions.
- Return plain prose in the user's language. No JSON, no key:value dump, no
  boilerplate template, no internal terms such as ledger, generation or
  checkpoint unless they are the cause.
"""

OUTCOME_PROMPT = """You are Forgel's project agent. The runtime has finished a
task the user asked for. Report only the outcome, in the language of the
user's message.

Rules:
- Say what was done and where: the repository, the main changes and whether
  the task is accepted.
- If the push status is "failed", say that the work is accepted locally but
  could not be published yet, and that the runtime will retry automatically.
  If it is "pushed" or "skipped", no publication detail is needed.
- If the task is not accepted, state the blocker and what happens next.
  Never ask the user to choose between internal process options: the runtime
  owns that choice. Ask only for what only the owner can decide: a production
  approval, missing access or a product change.
- Do not describe intermediate failed checks, rewrites, retries, QA or review
  steps, attempts, commits, ledger events or any other internal process. The
  user sees their request and the result; everything between them is not
  theirs to follow.
- Use only facts present in the context. Return plain prose, no JSON, no field
  names, no task ids unless the user needs one to act.
"""

RELEASE_OUTCOME_PROMPT = """You are Forgel's project agent. A release the user
asked for has been audited and published. Report only the result, in the
language of the user's message.

Rules:
- Name the request, the repositories and the released version of each one.
- Say whether the release is published: the tag exists and a provider release
  exists, or the tag exists without a provider release.
- If a repository failed to publish, say which one and that the runtime will
  retry automatically. If the release is blocked, state what stopped it and
  what happens next. Never ask the user to choose between internal process
  options: the runtime owns that choice. Ask only for what only the owner can
  decide: a production approval, missing access or a product change.
- Do not describe tasks, audits, intermediate checks, retries, commits, ledger
  events or any other internal process. The user sees the request and the
  released result.
- Use only facts present in the context. Return plain prose, no JSON, no field
  names, no internal identifiers unless the user needs one to act.
"""


SUMMARY_PROMPT = """You compact the conversation of a project assistant.

Preserve decisions, facts, file names, user preferences, open questions and
what was already done. Attribute each fact to its producer: a report in the
conversation describes the run that produced it. Write in the same language as
the conversation. Be concise and concrete. Return plain text, not JSON, and no
process field names or identifiers unless they are essential.
"""


@dataclass(frozen=True)
class AgentResult:
    text: str
    kind: str
    request: str | None = None
    task_id: str | None = None
    release_id: str = ""
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
                "report",
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
    repo: str = "",
    agent: str = "",
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
    if repo:
        entry["repo"] = repo
    if agent:
        entry["agent"] = agent
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
        if relative in {"FORGEL.md", "AGENTS.md"}:
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


def _release_plan_line(release: Mapping[str, Any]) -> str:
    repos = ", ".join(
        f"{repo_id} "
        f"{data.get('planned_version') or data.get('version') or '—'}"
        for repo_id, data in (release.get("repos") or {}).items()
    )
    return (
        f"Release plan `{release.get('id')}`: {repos or '—'}. "
        "The release train will audit and publish it."
    )


def _plain_brief(text: str) -> str:
    brief = str(text or "").strip()
    lowered = brief.lower()
    if lowered.startswith("adopted in place"):
        return "Existing project, taken over in place."
    if lowered.startswith("adopted from "):
        return "Existing project from " + brief[len("Adopted from "):]
    return brief


def runtime_capabilities(
    settings: Settings, layout: ProjectLayout
) -> str:
    """Structured state: what the agent in this process may actually use."""

    lines = [
        f"- model: {project_model_name(layout.control)}",
        f"- sandbox: {settings.sandbox}",
    ]
    try:
        github = GithubAuth(settings.home).status("en")
    except (GithubAuthError, OSError):
        github = "unknown"
    lines.append(f"- github: {github}")
    return "\n".join(lines)


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
    parts.append("Repositories:\n" + _repo_map(layout, repos))
    instructions = instruction_context(layout)
    if instructions:
        parts.append(instructions)

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

    releases = list_releases(layout)
    if releases:
        lines: list[str] = []
        for release in releases[-3:]:
            repos_text = ", ".join(
                f"{repo_id} "
                f"{data.get('version') or data.get('planned_version') or '—'}"
                for repo_id, data in (
                    release.get("repos") or {}
                ).items()
            )
            detail = str(release.get("detail") or "").strip()
            if not detail:
                audit = release.get("audit") or {}
                if str(audit.get("verdict") or "") in {"error", "fail"}:
                    detail = str(audit.get("summary") or "").strip()
            lines.append(
                f"- `{release['id']}` {release.get('title') or ''}: "
                f"{release.get('status') or 'unknown'}"
                + (f" ({repos_text})" if repos_text else "")
                + (f" — {_cap(detail, 400)}" if detail else "")
            )
        parts.append("Releases:\n" + "\n".join(lines))

    plans_dir = layout.artifact("docs/program/plans")
    plans = sorted(plans_dir.glob("*.md")) if plans_dir.is_dir() else []
    if plans:
        first = plans[-1].read_text(encoding="utf-8").splitlines()
        goal = first[0][len("# Plan: ") :] if first else ""
        parts.append(f"Current plan: {goal or plans[-1].stem}")

    overview = _repository_overview(layout, repos)
    if overview:
        parts.append("Project documents:\n" + overview)

    decisions_path = layout.artifact("docs/program/decisions.md")
    if decisions_path.is_file():
        decisions = decisions_path.read_text(encoding="utf-8")
        parts.append("User decisions (binding):\n" + _cap(decisions, 6000))

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


def _repo_map(
    layout: ProjectLayout, repos: Sequence[Mapping[str, Any]]
) -> str:
    """Ids, roles, locations and the released version the model can rely on."""

    lines: list[str] = []
    for entry in repos:
        location = str(
            entry.get("url") or entry.get("path") or ""
        ).strip()
        line = (
            f"- {entry['id']} ({entry.get('role') or 'application'})"
        )
        if location:
            line += f" — {location}"
        base, _source = discover_base(
            layout.repo_path(str(entry["id"]))
        )
        line += (
            f"\n  released: v{base}" if base else "\n  no release yet"
        )
        lines.append(line)
    return "\n".join(lines) or "- none"


def _cap(text: str, limit: int = MAX_READ_CHARS) -> str:
    if len(text) <= limit:
        return text
    return (
        text[:limit]
        + "\n... [truncated; use read_file with offset to read the rest]"
    )


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

    objects = json_objects(raw)
    data = objects[-1] if objects else None
    if data is None:
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
        reply = ""
        for key in ("message", "text", "content", "explanation", "answer"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                reply = value
                break
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
        "product_intent": str(data.get("product_intent", "")).strip(),
        "user_experience": str(data.get("user_experience", "")).strip(),
        "roadmap": [
            str(item) for item in (data.get("roadmap") or [])
            if str(item).strip()
        ],
        "requirements": [
            str(item) for item in requirements if str(item).strip()
        ],
        "acceptance": [str(item) for item in acceptance if str(item).strip()],
        "constraints": [
            str(item) for item in constraints if str(item).strip()
        ],
        "repo_id": str(data.get("repo_id", "")).strip(),
        "release_class": str(data.get("release_class", "")).strip().lower(),
        "test_command": [
            str(item) for item in test_command if str(item).strip()
        ],
        "assumptions": [
            str(item) for item in assumptions if str(item).strip()
        ],
    }


def _change_request_gaps(
    answer: Mapping[str, Any], repos: Sequence[Mapping[str, Any]]
) -> list[str]:
    """The fields a change request needs before it can become a task."""

    gaps: list[str] = []
    known = {str(entry["id"]) for entry in repos}
    repo_id = str(answer.get("repo_id") or "").strip()
    if not repo_id:
        gaps.append("repo_id")
    elif repo_id not in known:
        gaps.append(
            f"a known repo_id ({repo_id!r} is not a repository of this project)"
        )
    if not str(answer.get("title") or "").strip():
        gaps.append("title")
    if not (answer.get("requirements") or answer.get("acceptance")):
        gaps.append("requirements or acceptance criteria")
    return gaps


def _turn_chars(turns: list[dict[str, Any]]) -> int:
    return sum(len(str(turn.get("text", ""))) for turn in turns)


def _trim_turn(turn: dict[str, Any], limit: int) -> dict[str, Any]:
    text = str(turn.get("text", ""))
    if len(text) <= limit:
        return turn
    trimmed = dict(turn)
    trimmed["text"] = (
        text[:limit]
        + "\n... [turn truncated; the full text is in the history file]"
    )
    return trimmed


def _recent_turns(
    turns: list[dict[str, Any]],
    limit: int,
    min_turns: int = HISTORY_VISIBLE_TURNS,
    turn_limit: int = HISTORY_TURN_CHARS,
) -> list[dict[str, Any]]:
    """Recent turns for the prompt, newest kept and long turns trimmed.

    The newest ``min_turns`` turns are always present, so one long answer
    cannot push the message before it out of the prompt and break the
    continuity between two consecutive messages.
    """

    selected: list[dict[str, Any]] = []
    used = 0
    for index, turn in enumerate(reversed(turns)):
        size = min(len(str(turn.get("text", ""))), turn_limit)
        forced = index < min_turns
        if selected and not forced and used + size > limit:
            break
        selected.append(_trim_turn(turn, turn_limit))
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
        self._capabilities = ""

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
        if (
            not reply
            or reply == UNFORMATTED_REPLY
            or _looks_structured(reply)
        ):
            return (
                "I couldn't summarize the project state just now. "
                "Please retry."
            )
        return reply

    def explain(
        self,
        project: Mapping[str, Any],
        question: str,
        observation: str,
        fallback: str = "",
        prompt: str = "",
    ) -> str:
        """Explain a finished task from the whole context, not a status dump."""

        layout = ProjectLayout.detect(project["workspace"])
        messages = [
            ModelMessage(
                role="system",
                content=prompt or EXPLAIN_PROMPT,
            ),
            ModelMessage(
                role="user",
                content=(
                    f"Project: {project['name']} ({project['id']})\n\n"
                    f"User message:\n{question}\n\n"
                    f"Runtime context:\n{observation}\n\n"
                    "Write the explanation now."
                ),
            ),
        ]
        try:
            raw = self.client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError:
            return fallback or (
                "I couldn't explain the result just now. Please retry."
            )
        answer = parse_answer(raw)
        reply = str(answer.get("reply", "")).strip()
        if (
            not reply
            or reply == UNFORMATTED_REPLY
            or _looks_structured(reply)
        ):
            return fallback or (
                "I couldn't explain the result just now. Please retry."
            )
        return reply

    def explain_failure(
        self,
        project: Mapping[str, Any],
        operation: str,
        error: str,
        fallback: str = "",
    ) -> str:
        """Explain a failed operation and the next step, in the user's language."""

        lang = language.detect(operation)
        question = i18n.t(lang, "failure_question")
        default = i18n.t(lang, "failure_default", error=error)
        observation = json.dumps(
            {
                "operation": operation,
                "error": error,
                "project": {
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "brief": project.get("brief"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            return self.explain(
                project, question, observation, fallback=fallback or default
            )
        except Exception:  # noqa: BLE001 - the fallback is the answer
            return fallback or default

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
                    repo = str(turn.get("repo", "")).strip()
                    path = str(turn.get("path", "")).strip()
                    target = ":".join(
                        part for part in (repo, path) if part
                    )
                    if tool or target:
                        label += f" ({tool} {target})".rstrip()
                elif role == "report":
                    produced_by = str(
                        turn.get("agent") or "subagent"
                    ).strip()
                    label = f"Report from {produced_by}"
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
            (
                f"report from {turn.get('agent') or 'subagent'}: "
                if str(turn.get("role")) == "report"
                else f"{turn.get('role')}: "
            )
            + str(turn.get("text", ""))
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
        if not self._capabilities:
            self._capabilities = runtime_capabilities(
                self.settings, layout
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
                    f"Runtime capabilities (this agent):\n"
                    f"{self._capabilities}\n\n"
                    f"Runtime process:\n"
                    f"{process_model(layout, project)}\n\n"
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
        answer: dict[str, Any] | None = None
        markup_retries = 0
        answer_retries = 0
        request_retries = 0
        research_steps = 0
        for step in range(
            MAX_RESEARCH_STEPS
            + 1
            + MAX_MARKUP_RETRIES
            + MAX_ANSWER_RETRIES
            + MAX_REQUEST_RETRIES
        ):
            try:
                raw = self.client.complete(messages, model=model)
            except ModelError as exc:
                return AgentResult(
                    text=f"Model call failed: {exc}",
                    kind="error",
                )
            objects = json_objects(raw)
            actions = [
                item
                for item in objects
                if str(item.get("action", "")) in RESEARCH_ACTIONS
            ]
            finals = [
                item
                for item in objects
                if str(item.get("action", "")) not in RESEARCH_ACTIONS
            ]
            if actions and research_steps >= MAX_RESEARCH_STEPS:
                if not finals:
                    return AgentResult(
                        text=(
                            "I need more file reads than allowed for one "
                            "answer. Please narrow the question."
                        ),
                        kind="error",
                    )
                actions = []
            if actions:
                observations: list[str] = []
                for data in actions:
                    if research_steps >= MAX_RESEARCH_STEPS:
                        break
                    args = dict(data.get("action_args") or {})
                    for key in ("path", "repo_id"):
                        if key in data and key not in args:
                            args[key] = data[key]
                    try:
                        observation = execute_repo_action(
                            layout,
                            repos,
                            {"action": str(data["action"]), **args},
                        )
                    except RepoActionError as exc:
                        observation = f"error: {exc}"
                    observations.append(observation)
                    research_steps += 1
                    repo = str(args.get("repo_id") or "").strip()
                    if not repo:
                        repo = next(
                            (
                                str(entry["id"])
                                for entry in repos
                                if str(entry["id"]) == "main"
                            ),
                            str(repos[0]["id"]) if repos else "",
                        )
                    append_history(
                        layout,
                        "tool",
                        _cap(observation),
                        actor,
                        session=session,
                        tool=str(data["action"]),
                        path=str(args.get("path") or ""),
                        repo=repo,
                    )
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "Observations:\n"
                        + "\n\n".join(
                            _cap(item) for item in observations
                        )
                        + "\n\nContinue with another action or the final "
                        "JSON answer.",
                    )
                )
                if not finals:
                    continue
            if _looks_like_tool_markup(raw) and markup_retries < MAX_MARKUP_RETRIES:
                messages.append(ModelMessage("assistant", raw.strip()))
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
            candidate = parse_answer(
                json.dumps(finals[-1]) if finals else raw
            )
            unreadable = candidate["kind"] in {
                "answer",
                "change_request",
            } and (
                not str(candidate["reply"]).strip()
                or candidate["reply"] == UNFORMATTED_REPLY
            )
            if unreadable and answer_retries < MAX_ANSWER_RETRIES:
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "That reply cannot be shown to the user. Answer the "
                        f"user's question ({_cap(text, 600)}) with exactly "
                        "one JSON object and a non-empty plain-text reply. "
                        "Do not return a plan, a task list, tool-call "
                        "markup or an empty reply. Use a read_file action "
                        "if you still need a file.",
                    )
                )
                answer_retries += 1
                continue
            gaps = (
                _change_request_gaps(candidate, repos)
                if candidate["kind"] == "change_request"
                else []
            )
            if gaps and request_retries < MAX_REQUEST_RETRIES:
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "That change request cannot be queued: it is missing "
                        + ", ".join(gaps)
                        + ". Fill those fields from the project context. If a "
                        "task or a stopped release already carries this work, "
                        "use its action instead of a new change request.",
                    )
                )
                request_retries += 1
                continue
            if gaps:
                return AgentResult(
                    text=(
                        "The change was not queued: the request is missing "
                        + ", ".join(gaps)
                        + "."
                    ),
                    kind="error",
                )
            answer = candidate
            break
        if answer is None:
            answer = parse_answer(raw)
        result_text = answer["reply"]
        if (
            answer["kind"] == "change_request"
            and result_text == UNFORMATTED_REPLY
        ):
            result_text = ""
        request = None
        task_id = None
        release_id = ""
        if answer["kind"] == "change_request":
            request = self._record_request(
                layout, project, text, actor, answer
            )
            release_class = (
                str(answer.get("release_class") or "minor").strip().lower()
            )
            release_id = new_release_id(
                str(answer.get("title") or text or "release")
            )
            task = self._queue_task(
                layout,
                text,
                answer,
                spec=request,
                release_id=release_id,
                release_class=release_class,
            )
            if task is not None:
                task_id = str(task["id"])
                attached = attach_blocked_release(
                    layout, project, task
                )
                if attached:
                    release_id = attached
                    release_plan = load_release(layout, attached)
                else:
                    release_plan = plan_release(
                        layout,
                        project,
                        release_id,
                        title=str(answer.get("title") or text or "change"),
                        request=str(answer.get("summary") or text),
                        release_class=release_class,
                        task_items=[task],
                        ledger=self.ledger,
                        settings=self.settings,
                    )
                result_text += (
                    f"\n\nRecorded as `{request}`. Queued task "
                    f"`{task_id}` for repository `{task['repo_id']}`; the "
                    "daemon will start it and report back."
                )
                if release_plan is not None:
                    result_text += (
                        "\n\n" + _release_plan_line(release_plan)
                    )
            else:
                release_id = ""
                result_text += (
                    f"\n\nRecorded as `{request}`. No task was queued: the "
                    "request does not name a repository."
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
            release_id=release_id,
            action=answer.get("action", "") if answer["kind"] == "action" else "",
            args=(
                answer.get("action_args") or {}
                if answer["kind"] == "action"
                else None
            ),
            actions=answer.get("actions") or [],
        )

    def _record_decisions(
        self,
        layout: ProjectLayout,
        decisions: Any,
        actor: str,
        title: str,
    ) -> list[tuple[str, str, str]]:
        """Append explicit user decisions to the project decision log."""

        entries = [
            item for item in (decisions or []) if isinstance(item, dict)
        ]
        path = layout.artifact("docs/program/decisions.md")
        header = (
            "# User Decisions\n\n"
            "Product decisions explicitly stated by the user. Requirements "
            "documents must carry the relevant decisions and must not "
            "re-open them.\n\n"
            "| ID | Decision | Source |\n"
            "|----|----------|--------|\n"
        )
        existing = path.read_text(encoding="utf-8") if path.exists() else header
        known: dict[str, tuple[str, str, str]] = {}
        for line in existing.splitlines():
            if not line.strip().startswith("| D-"):
                continue
            parts = [item.strip() for item in line.split("|")]
            if len(parts) >= 4 and parts[1]:
                known[parts[2].lower()] = (
                    parts[1],
                    parts[2],
                    parts[3],
                )
        numbers = [
            int(match.group(1))
            for match in re.finditer(r"\| D-(\d+) \|", existing)
        ]
        next_number = (max(numbers) if numbers else 0) + 1
        rows: list[tuple[str, str, str]] = []
        added: list[tuple[str, str, str]] = []
        for item in entries:
            decision = str(item.get("decision") or "").strip()
            if not decision:
                continue
            if decision.lower() in known:
                rows.append(known[decision.lower()])
                continue
            source = str(
                item.get("source") or f"request: {title} ({actor})"
            ).strip()
            decision_id = f"D-{next_number:03d}"
            next_number += 1
            row = (decision_id, decision, source)
            known[decision.lower()] = row
            rows.append(row)
            added.append(row)
        if added:
            addition = "\n".join(
                f"| {item[0]} | {item[1]} | {item[2]} |"
                for item in added
            )
            write_text(
                path,
                existing.rstrip() + "\n" + addition + "\n",
            )
        return rows

    def _record_request(
        self,
        layout: ProjectLayout,
        project: Mapping[str, Any],
        text: str,
        actor: str,
        answer: Mapping[str, Any],
    ) -> str:
        title = str(answer.get("title") or "Change request").strip()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        relative = f"docs/program/requests/{timestamp}_{_slug(title)}.md"

        def items(key: str) -> list[str]:
            value = answer.get(key)
            if isinstance(value, str):
                value = [value]
            if not isinstance(value, list):
                return []
            return [
                str(item).strip() for item in value if str(item).strip()
            ]

        requirements = items("requirements")
        acceptance = items("acceptance")
        constraints = items("constraints")
        assumptions = items("assumptions")
        goals = items("goals") or requirements
        non_goals = items("non_goals")
        user_stories = items("user_stories")
        tests = items("tests")
        risks = items("risks")
        open_questions = items("open_questions")
        affected = items("affected_files")
        decisions = self._record_decisions(
            layout, answer.get("user_decisions"), actor, title
        )
        test_command = [str(item) for item in (answer.get("test_command") or [])]

        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        test_text = requirements_doc.bullets(tests)
        if test_command:
            test_text += (
                "\n- Command: `" + " ".join(test_command) + "`"
            )
        values = {
            "kind": "Feature",
            "title": title,
            "project": f"`{project['id']}`",
            "task": "—",
            "plan": "—",
            "repository": "—",
            "depends_on": "—",
            "status": "New",
            "version": "1.0.0",
            "created": created,
            "source": f"Local console request ({actor})",
            "author": "Forgel project agent",
            "overview": answer.get("summary") or "—",
            "product_intent": answer.get("product_intent") or "None stated.",
            "user_experience": (
                answer.get("user_experience") or "None stated."
            ),
            "roadmap": requirements_doc.bullets(
                answer.get("roadmap") or [], "None stated."
            ),
            "goals": requirements_doc.bullets(goals),
            "non_goals": requirements_doc.bullets(
                non_goals, "None stated."
            ),
            "user_decisions": requirements_doc.decisions_table(decisions),
            "functional_requirements": requirements_doc.numbered(
                "FR", requirements
            ),
            "technical_requirements": requirements_doc.bullets(
                constraints, "None stated."
            ),
            "user_stories": requirements_doc.bullets(
                user_stories, "None stated."
            ),
            "tests": test_text,
            "acceptance": requirements_doc.numbered("AC", acceptance),
            "scope": requirements_doc.bullets(
                list(non_goals) + list(constraints), "None stated."
            ),
            "risks": requirements_doc.bullets(risks, "None stated."),
            "open_questions": requirements_doc.bullets(
                open_questions, "None."
            ),
            "affected_files": requirements_doc.bullets(
                affected, "Not identified yet."
            ),
            "assumptions": requirements_doc.bullets(
                assumptions, "None; the request was explicit enough."
            ),
            "related_documents": requirements_doc.bullets(
                [
                    "`docs/program/decisions.md`",
                    "`docs/program/state.md`",
                ]
            ),
            "revision_history": requirements_doc.bullets(
                [f"1.0.0 — {created[:10]} — Initial request recorded."]
            ),
        }
        write_text(
            layout.artifact(relative),
            requirements_doc.render(values),
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
        spec: str = "",
        release_id: str = "",
        release_class: str = "",
    ) -> dict[str, Any] | None:
        repos = manifest_entries(layout)
        if not repos:
            return None
        known = {str(entry["id"]) for entry in repos}
        repo_id = str(answer.get("repo_id") or "").strip()
        if repo_id not in known:
            return None
        title = (
            str(answer.get("title") or "").strip() or "Change request"
        )
        requirements = answer.get("requirements") or [
            answer.get("summary") or "The requested change is implemented"
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
            language=language.detect(text),
            spec=spec,
            release_id=release_id,
            release_class=release_class,
            summary=str(answer.get("summary") or ""),
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
