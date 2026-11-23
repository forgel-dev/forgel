"""Formal task specifications and plan review.

The planner decomposes a milestone into task intents. A separate requirements
writer turns each intent into a formal specification document; a plan review
then judges the whole set against the original problem, not against the specs
themselves. The specification is the artifact the coding agent, QA and the
independent reviewer work from; the task record is an index.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from . import requirements as requirements_doc
from .artifacts import write_text
from .check_commands import check_problems
from .instructions import instruction_context
from .layout import ProjectLayout
from .model_output import json_objects
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .program_manifest import entries as manifest_entries
from .repo_tools import RESEARCH_ACTIONS, RepoActionError, execute_repo_action

MAX_SPEC_STEPS = 50
MAX_SPEC_CHARS = 12_000
MAX_SPEC_RETRIES = 5
SPEC_KEYS = {
    "problem",
    "outcome",
    "scope",
    "non_goals",
    "requirements",
    "acceptance",
    "constraints",
    "checks",
    "external_dependencies",
}
SPEC_DIR = "docs/program/specs"
CANCEL_MARKER = "<!-- forgel:cancelled -->"
CANCEL_NOTE = (
    f"{CANCEL_MARKER}\n"
    "\n"
    "> **Cancelled.** This task was cancelled. The runtime does not accept "
    "this requirements document for work.\n"
)


class SpecError(RuntimeError):
    """The requirements writer could not produce a usable specification."""


class PlanReviewError(SpecError):
    """The plan does not solve the stated problem."""


@dataclass
class PlanReview:
    sufficient: bool
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_markdown(self) -> str:
        if self.sufficient:
            return "The plan review found the plan sufficient for the goal."
        lines = ["The plan review found the plan insufficient for the goal:"]
        lines.extend(
            f"- task {item.get('task')}: {item.get('issue')}"
            for item in self.findings
        )
        return "\n".join(lines)


SPEC_SYSTEM_PROMPT = """You are Forgel's requirements writer for exactly one
task. The planner has split a milestone into tasks; your job is the formal
specification for one of them.

You may inspect the repository before writing:
{"action": "list_files", "path": ".", "repo_id": "main"}
{"action": "read_file", "path": "relative/path", "repo_id": "main"}
Paths are relative to the repository and may not leave it. Read the code you
depend on instead of assuming it exists; stop once you know enough.

Return exactly one JSON object:
{
  "problem": "what problem this task solves",
  "outcome": "what is true when the task is done",
  "product_intent": "the product intent this task serves, when stated",
  "user_experience": "how the user experiences this task's result, when stated",
  "scope": ["in scope"],
  "non_goals": ["explicitly out of scope"],
  "requirements": ["explicit, testable requirement"],
  "acceptance": ["observable acceptance criterion"],
  "constraints": ["constraint"],
  "assumptions": ["what you assumed where the intent was silent"],
  "external_dependencies": [
    {"name": "service, tool or format",
     "interface": "how the task uses it",
     "docs": "path, URL or excerpt source, or empty"}
  ],
  "risks": ["what could make this task fail or miss the goal"],
  "goals": ["outcome this task must achieve"],
  "user_decisions": [
    {"decision": "binding product decision", "source": "where it was recorded"}
  ],
  "user_stories": ["as a ... I want ... so that ..."],
  "open_questions": ["only a truly undecidable choice, never a way to avoid deciding"],
  "related_documents": ["path"],
  "revision_history": ["version and what changed"],
  "checks": [
    {"criterion": "which acceptance criterion",
     "verification": "command" | "review",
     "command": ["command", "arg"]}
  ],
  "test_command": ["command", "arg"] or []
}

Rules:
- Requirements must be explicit and testable; acceptance must say how the
  result is judged. Do not add features beyond the intent, and do not
  prescribe an implementation file list: state the required behavior, the
  developer chooses the files.
- Requirements, acceptance, constraints, goals, user stories, risks and open
  questions describe observable product behavior and outcomes only. Never put
  a command (shell, git, package manager), a file path, code, an identifier, a
  tool or provider name, an environment variable, an interface, a contract, an
  endpoint, a request or response format, a schema, a commit/PR/worktree step
  or any other implementation detail into them. A verification command
  belongs only in the "checks" field, and the test command in
  "test_command". Runtime mechanics (git, commit, worktree, done report) are
  never requirements. This is a requirements document: the permission to
  document a stable interface in user documentation does not apply. If the
  intent or the respec issue names a command, a file or a runtime step,
  restate the behavior it must produce.
- Documentation is text and is verified by review. Never require or add a
  test, guard, assertion or automated check that reads a documentation file;
  a documentation task has review-only checks and no test command.
- A respec issue is a binding decision: the rewritten requirements and
  acceptance must remove the option the issue rejected and must not leave a
  product choice open when the acceptance depends on it. Requirements and
  acceptance must be mutually consistent; a requirement that permits an
  option the acceptance forbids is invalid. Decide the remaining details from
  the issue, the task intent and the recorded decisions and write the
  requirement; never use an open question to avoid the decision, and never
  leave the specification waiting for an answer.
- Do not default to open questions. Decide every reversible detail yourself,
  record it as an assumption, and write the requirement. An open question is
  reserved for a truly undecidable choice and never stops the work.
- Give every acceptance criterion a check. Use a command when the criterion
  can be verified by one; use review only for a subjective criterion. Never
  use a vacuous check.
- The task is one repository change that a coding agent can finish, test and
  commit on its own.
- Product decisions recorded in the project's user-decision log are binding.
  Include the decisions relevant to this task under "user_decisions" with
  their IDs and sources; do not re-open them. If the task contradicts a
  recorded decision, say so in risks and open_questions.
- If the intent is ambiguous or cannot achieve the milestone problem, record
  the gap in risks and keep the scope honest; do not invent a solution.
- If the task depends on an external interface (a tool, a service, a data
  format, a protocol), record the contract the implementation needs, derived
  from its authoritative source, and add a command check that exercises the
  real interface when it is available; a hand-written stub is not proof of
  the contract. A task that needs a browser, a mobile simulator or emulator,
  a live third-party service, a message broker, object storage or another
  tool without a standard test harness must include at least one command
  check that exercises that real interface; a fake engine, a mock or a stub
  is not proof. A database or cache that the project's unit-test framework
  already handles needs the normal test command, not a separate integration
  environment.
- A specification is rewritten only for the concrete defect the planner
  reported; keep unrelated scope stable and never treat a preference, a
  simpler path or a wording change as a defect.
- List every external dependency the task touches — a service, tool, binary,
  API, schema or data format from outside this project and its repositories.
  A sibling project repository, the standard library or a package already
  provided by the project environment is not external; use it directly. Give
  the documentation source; leave it empty when none is known. Do not invent
  the interface; the dependency scout investigates it.
- Follow the project and repository instructions in the prompt. Repository
  rules are more specific and take precedence on conflict. Write the
  specification in the artifact language they require.
- Return JSON only; no tool-call markup, XML or prose.
"""


PLAN_REVIEW_PROMPT = """You review a milestone plan and its specifications
against the original problem. This is the planner's acceptance gate: after a
specification is accepted it is binding and the coder follows it.

Follow the project and repository instructions in the prompt. Repository rules
are more specific and take precedence on conflict. Write findings in the
artifact language they require.

Answer two questions:
1. If every task is completed exactly as specified, will the original problem
   be solved?
2. Does a specification have an explicit defect that makes it unsound to
   implement — a logical contradiction, an unachievable requirement, a
   security or architectural problem?

Read the goal, the plan notes and the specifications. Name:
- what the plan assumes but does not deliver;
- which part of the goal no task covers;
- any task that can be green while the problem remains unsolved;
- any specification with one of the explicit defects above.

Recorded user decisions in the specifications are binding. A plan that
contradicts a recorded decision is insufficient even if every task passes.
Do not reject for wording, style or preference, and do not rewrite the
specifications; report concrete gaps and defects.

Return exactly one JSON object:
{"sufficient": true | false,
 "findings": [{"task": 0, "issue": "concrete gap or defect"}]}

Use sufficient=true only when the plan as written solves the problem and no
specification has an explicit defect. Return JSON only.
"""


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _check(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    criterion = str(raw.get("criterion", "")).strip()
    if not criterion:
        return None
    verification = str(raw.get("verification", "command")).strip().lower()
    if verification not in {"command", "review"}:
        verification = "command"
    command = raw.get("command", [])
    if isinstance(command, str):
        command = [command]
    if not isinstance(command, list):
        command = []
    command = [str(item) for item in command if str(item).strip()]
    if verification == "command" and not command:
        return None
    return {
        "criterion": criterion,
        "verification": verification,
        "command": command,
    }


def _normalize_spec(
    data: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> dict[str, Any]:
    requirements = _strings(data.get("requirements"))
    acceptance = _strings(data.get("acceptance"))
    checks = [
        item
        for item in (_check(raw) for raw in data.get("checks") or [])
        if item is not None
    ]
    if not requirements:
        raise SpecError("the specification has no requirements")
    if not acceptance:
        raise SpecError("the specification has no acceptance criteria")
    if not checks:
        raise SpecError("the specification has no checks")
    external_dependencies = [
        {
            "name": str(item.get("name") or "").strip(),
            "interface": str(item.get("interface") or "").strip(),
            "docs": str(item.get("docs") or "").strip(),
            "mode": str(item.get("mode") or "").strip(),
            "evidence": str(item.get("evidence") or "").strip(),
            "stub": str(item.get("stub") or "").strip(),
        }
        for item in (data.get("external_dependencies") or [])
        if isinstance(item, dict)
        and str(item.get("name") or "").strip()
    ]
    if external_dependencies and not any(
        item["verification"] == "command" and item["command"]
        for item in checks
    ):
        raise SpecError(
            "an external dependency needs at least one command check that "
            "exercises the real interface"
        )
    return {
        "title": str(intent.get("title") or "").strip(),
        "summary": str(intent.get("summary") or "").strip(),
        "repo_id": str(intent.get("repo_id") or "").strip(),
        "problem": str(data.get("problem") or "").strip(),
        "outcome": str(data.get("outcome") or "").strip(),
        "product_intent": str(
            data.get("product_intent") or ""
        ).strip(),
        "user_experience": str(
            data.get("user_experience") or ""
        ).strip(),
        "scope": _strings(data.get("scope")),
        "non_goals": _strings(data.get("non_goals")),
        "requirements": requirements,
        "acceptance": acceptance,
        "constraints": _strings(data.get("constraints")),
        "assumptions": _strings(data.get("assumptions")),
        "external_dependencies": external_dependencies,
        "risks": _strings(data.get("risks")),
        "goals": _strings(data.get("goals"))
        or ([str(data.get("outcome") or "").strip()]
            if str(data.get("outcome") or "").strip()
            else []),
        "user_decisions": [
            {
                "decision": str(item.get("decision") or "").strip(),
                "source": str(item.get("source") or "").strip(),
            }
            for item in (data.get("user_decisions") or [])
            if isinstance(item, dict)
            and str(item.get("decision") or "").strip()
        ],
        "user_stories": _strings(data.get("user_stories")),
        "open_questions": _strings(data.get("open_questions")),
        "related_documents": _strings(data.get("related_documents")),
        "revision_history": _strings(data.get("revision_history")),
        "checks": checks,
        "test_command": _strings(data.get("test_command")),
    }


def _context(
    layout: ProjectLayout, repo_id: str
) -> str:
    try:
        tree = execute_repo_action(
            layout,
            manifest_entries(layout),
            {"action": "list_files", "path": ".", "repo_id": repo_id},
        )
    except RepoActionError as exc:
        tree = f"(file tree unavailable: {exc})"
    return tree[:MAX_SPEC_CHARS]


def _looks_like_tool_markup(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "<｜｜dsml｜｜",
            "<|",
            "<tool_call",
            "<tool_result",
            "<function_call",
            "<parameter",
            "</invoke>",
            "<system_warning",
        )
    )


IMPLEMENTATION_PATTERNS = (
    re.compile(r"\bgit\b", re.IGNORECASE),
    re.compile(r"\b(?:curl|wget)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:pip|npm|yarn|pnpm|docker|ssh|scp|rsync)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bpython\s+-m\b", re.IGNORECASE),
    re.compile(r"\b(?:sh|bash|zsh)\s+-c\b", re.IGNORECASE),
    re.compile(r"```"),
    re.compile(r"(?:https?://|git@)\S+", re.IGNORECASE),
    re.compile(
        r"\b[\w.-]+(?:/[\w.-]+)+\.(?:md|py|sh|json|ya?ml|toml|txt|mjs|js|ts|cfg|ini)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b[\w-]+\.(?:md|py|sh|json|ya?ml|toml|txt|mjs|js|ts|cfg|ini)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:commit|commits|committed|worktree|done report)\b",
        re.IGNORECASE,
    ),
)

IMPLEMENTATION_FIELDS = (
    "problem",
    "outcome",
    "requirements",
    "acceptance",
    "constraints",
    "goals",
    "user_stories",
    "scope",
    "non_goals",
    "risks",
    "open_questions",
    "assumptions",
)


def implementation_problems(spec: Mapping[str, Any]) -> list[str]:
    """Functional text must not carry commands, files, code or runtime steps."""

    problems: list[str] = []
    for field in IMPLEMENTATION_FIELDS:
        value = spec.get(field)
        values = [value] if isinstance(value, str) else value or []
        for item in values:
            text = str(item).strip()
            if not text:
                continue
            for pattern in IMPLEMENTATION_PATTERNS:
                match = pattern.search(text)
                if match:
                    problems.append(
                        f"{field}: implementation detail "
                        f"{match.group(0)!r} in {text[:160]!r}"
                    )
                    break
    return problems


DOCUMENTATION_WORDS = re.compile(
    r"\b(?:readme|documentation|documents?|docs?|manual|guide|changelog)\b",
    re.IGNORECASE,
)
TEST_WORDS = re.compile(
    r"\b(?:tests?|guard|assertions?|assert)\b", re.IGNORECASE
)


def documentation_task(
    intent: Mapping[str, Any], spec: Mapping[str, Any]
) -> bool:
    """True when the task is a documentation change."""

    text = " ".join(
        str(item or "")
        for item in (
            intent.get("title"),
            intent.get("summary"),
            spec.get("problem"),
            spec.get("outcome"),
        )
    )
    return bool(DOCUMENTATION_WORDS.search(text))


def documentation_problems(
    intent: Mapping[str, Any], spec: Mapping[str, Any]
) -> list[str]:
    """Documentation is text: it is reviewed, never tested."""

    if not documentation_task(intent, spec):
        return []
    problems: list[str] = []
    if spec.get("test_command"):
        problems.append("a documentation task has no test_command")
    for check in spec.get("checks") or []:
        criterion = str(check.get("criterion") or "")
        command = " ".join(
            str(item) for item in (check.get("command") or [])
        )
        if str(check.get("verification") or "") != "review":
            problems.append(
                "a documentation check must be review-only: "
                f"{criterion[:120]}"
            )
        if DOCUMENTATION_WORDS.search(
            criterion + " " + command
        ) and TEST_WORDS.search(criterion + " " + command):
            problems.append(
                "documentation is verified by review, not by a test: "
                f"{criterion[:120]}"
            )
    for field in (
        "requirements",
        "acceptance",
        "constraints",
        "goals",
        "user_stories",
    ):
        value = spec.get(field)
        values = [value] if isinstance(value, str) else value or []
        for item in values:
            text = str(item).strip()
            if (
                text
                and DOCUMENTATION_WORDS.search(text)
                and TEST_WORDS.search(text)
            ):
                problems.append(
                    f"{field}: documentation is verified by review, not "
                    f"by a test: {text[:120]}"
                )
    return problems


def _looks_like_spec(data: Mapping[str, Any]) -> bool:
    """A candidate final answer must carry spec fields, not tool results."""

    if str(data.get("kind") or "").strip().lower() == "spec":
        return True
    return bool(SPEC_KEYS & set(data))


def _diagnostics(
    intent: Mapping[str, Any],
    attempts: int,
    research_paths: Sequence[str],
    retries: int,
    markup_retries: int,
    raw: str,
    last_observation: str,
    reason: str,
) -> str:
    title = str(intent.get("title") or "the task")
    research = ", ".join(research_paths[-8:]) or "none"
    observation = " ".join(
        (last_observation or "").strip().split()
    )[:400]
    return (
        f"{reason}; task: {title}; model calls: {attempts}; "
        f"research: {research}; answer retries: {retries}; "
        f"markup retries: {markup_retries}; "
        f"last observation: {observation or '—'}; "
        f"last model output: {raw[:1200] or '(empty)'}"
    )


def write_task_spec(
    settings: Any,
    layout: ProjectLayout,
    goal: str,
    notes: str,
    intent: Mapping[str, Any],
    client: ModelClient,
    log: Callable[[str], None] = print,
    review_issue: str = "",
) -> dict[str, Any]:
    """Turn one planner intent into a formal, structured specification."""

    repo_id = str(intent.get("repo_id") or "").strip()
    decisions_path = layout.artifact("docs/program/decisions.md")
    try:
        decisions_text = decisions_path.read_text(encoding="utf-8")
    except OSError:
        decisions_text = "(no user-decision log yet)"
    repo_lines = "\n".join(
        f"- {item['id']}: {item.get('role') or 'application'}"
        for item in manifest_entries(layout)
    ) or "- (sole)"
    instructions = instruction_context(
        layout, [repo_id] if repo_id else None
    )
    messages = [
        ModelMessage("system", SPEC_SYSTEM_PROMPT),
        ModelMessage(
            "user",
            "Milestone goal:\n"
            f"{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
            f"Task intent:\n{json.dumps(dict(intent), ensure_ascii=False)}\n\n"
            f"User decision log:\n{decisions_text}\n\n"
            f"Project repositories:\n{repo_lines}\n\n"
            + (
                f"Project and repository instructions:\n{instructions}\n\n"
                if instructions
                else ""
            )
            + f"Repository file tree:\n{_context(layout, repo_id)}\n\n"
            + (
                "The previous version was rejected for this concrete "
                f"defect:\n{review_issue}\n\n"
                if review_issue
                else ""
            )
            + "Write the formal specification now.",
        ),
    ]
    model = project_model_name(layout.control)
    parsed: dict[str, Any] | None = None
    retries = 0
    research_steps = 0
    budget_notice = False
    attempts = 0
    markup_retries = 0
    research_paths: list[str] = []
    last_observation = ""
    for _ in range(MAX_SPEC_STEPS + MAX_SPEC_RETRIES + 6):
        attempts += 1
        try:
            raw = client.complete(messages, model=model)
        except ModelError as exc:
            raise SpecError(
                f"the requirements writer failed on model call {attempts}: "
                f"{exc}; research: "
                f"{', '.join(research_paths[-8:]) or 'none'}"
            ) from exc
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
            and _looks_like_spec(item)
        ]
        observations: list[str] = []
        for data in actions:
            if research_steps >= MAX_SPEC_STEPS:
                break
            args = dict(data.get("action_args") or {})
            for key in ("path", "repo_id"):
                if key in data and key not in args:
                    args[key] = data[key]
            try:
                observation = execute_repo_action(
                    layout,
                    manifest_entries(layout),
                    {"action": str(data["action"]), **args},
                )
            except RepoActionError as exc:
                observation = f"error: {exc}"
            observations.append(observation)
            research_steps += 1
            research_paths.append(
                f"{data['action']}:{args.get('path') or ''}"
            )
        if observations:
            last_observation = observations[-1]
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observations:\n"
                    + "\n\n".join(
                        item[:MAX_SPEC_CHARS] for item in observations
                    )
                    + "\n\nReturn another action or the final spec JSON.",
                )
            )
        unknown = [
            item
            for item in objects
            if str(item.get("action") or "").strip()
            and str(item.get("action")) not in RESEARCH_ACTIONS
            and not _looks_like_spec(item)
        ]
        if unknown and not finals:
            if markup_retries < MAX_SPEC_RETRIES:
                names = ", ".join(
                    sorted(
                        {
                            str(item.get("action") or "")
                            for item in unknown
                        }
                    )
                )
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        f"Unknown action(s): {names}. The only research "
                        "actions are list_files and read_file. Return one "
                        "of them or the final specification JSON.",
                    )
                )
                markup_retries += 1
                continue
        if finals:
            try:
                parsed = _normalize_spec(finals[-1], intent)
                implementation = implementation_problems(parsed)
                if implementation:
                    raise SpecError("; ".join(implementation[:5]))
                documentation = documentation_problems(intent, parsed)
                if documentation:
                    raise SpecError("; ".join(documentation[:5]))
                problems = check_problems(
                    layout,
                    str(intent.get("repo_id") or ""),
                    parsed.get("checks") or [],
                )
                if problems:
                    raise SpecError("; ".join(problems))
                break
            except SpecError as exc:
                if retries >= MAX_SPEC_RETRIES:
                    keys = sorted(finals[-1].keys())
                    raise SpecError(
                        _diagnostics(
                            intent,
                            attempts,
                            research_paths,
                            retries,
                            markup_retries,
                            raw,
                            last_observation,
                            f"{exc}; model keys: {keys}",
                        )
                    ) from exc
                if not observations:
                    messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        f"The specification is invalid: {exc}. The document "
                        "describes functional requirements only: remove every "
                        "command, file path, code, tool or provider name, "
                        "environment variable, commit/git/worktree/done-report "
                        "step and other implementation detail from "
                        "requirements, acceptance, constraints, goals, user "
                        "stories, risks, open questions and assumptions; a "
                        "verification command belongs only in checks. A "
                        "documentation task is text: it has review-only "
                        "checks, no test command and no test or guard that "
                        "reads a documentation file. A respec issue is "
                        "binding: remove the option it rejected and keep "
                        "requirements and acceptance consistent. Return "
                        "a complete JSON specification. Every command check "
                        "must run in the task repository "
                        f"'{intent.get('repo_id') or 'project root'}' and "
                        "must not point at files that exist only in another "
                        "repository.",
                    )
                )
                retries += 1
                continue
        if _looks_like_tool_markup(raw) and markup_retries < MAX_SPEC_RETRIES:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return exactly one JSON specification object, not "
                    "tool-call markup, tool results or XML. Do not emit "
                    "<｜｜DSML｜｜>, <tool_call>, <tool_result>, "
                    "<invoke>/<parameter> or provider-specific calls.",
                )
            )
            markup_retries += 1
            continue
        if not actions:
            if retries >= MAX_SPEC_RETRIES:
                raise SpecError(
                    _diagnostics(
                        intent,
                        attempts,
                        research_paths,
                        retries,
                        markup_retries,
                        raw,
                        last_observation,
                        "the requirements writer did not return a "
                        "specification",
                    )
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return a complete JSON specification with explicit "
                    "requirements, acceptance criteria and checks.",
                )
            )
            retries += 1
            continue
        if research_steps >= MAX_SPEC_STEPS and not observations:
            if budget_notice:
                raise SpecError(
                    _diagnostics(
                        intent,
                        attempts,
                        research_paths,
                        retries,
                        markup_retries,
                        raw,
                        last_observation,
                        "the requirements writer exceeded the research "
                        "step limit",
                    )
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Research budget exhausted. Return the final spec JSON "
                    "now; do not read or list more files.",
                )
            )
            budget_notice = True
            continue
    if parsed is None:
        raise SpecError(
            _diagnostics(
                intent,
                attempts,
                research_paths,
                retries,
                markup_retries,
                raw,
                last_observation,
                "the requirements writer did not return a spec",
            )
        )
    return parsed


def review_plan(
    layout: ProjectLayout,
    goal: str,
    notes: str,
    specs: Sequence[Mapping[str, Any]],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> PlanReview:
    """Judge the specs against the original problem."""

    def render_one(index: int, spec: Mapping[str, Any]) -> str:
        dependencies = "; ".join(
            f"{item.get('name')} ({item.get('mode') or 'unknown'})"
            for item in (spec.get("external_dependencies") or [])
            if isinstance(item, dict)
        ) or "none"
        return (
            f"--- Task {index}: {spec.get('title')} ---\n"
            f"Problem: {spec.get('problem')}\n"
            f"Outcome: {spec.get('outcome')}\n"
            f"Scope: {'; '.join(spec.get('scope') or [])}\n"
            f"Non-goals: {'; '.join(spec.get('non_goals') or [])}\n"
            f"Requirements: {'; '.join(spec.get('requirements') or [])}\n"
            f"Acceptance: {'; '.join(spec.get('acceptance') or [])}\n"
            f"External dependencies: {dependencies}\n"
            f"Assumptions: {'; '.join(spec.get('assumptions') or [])}\n"
            f"Risks: {'; '.join(spec.get('risks') or [])}\n"
        )

    rendered = "\n\n".join(
        render_one(index, spec) for index, spec in enumerate(specs)
    )
    instructions = instruction_context(layout)
    messages = [
        ModelMessage("system", PLAN_REVIEW_PROMPT),
        ModelMessage(
            "user",
            "Project and repository instructions:\n"
            + (instructions or "- none")
            + f"\n\nMilestone goal:\n{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
            f"Specifications:\n{rendered[:MAX_SPEC_CHARS * 2]}",
        ),
    ]
    try:
        raw = client.complete(
            messages, model=project_model_name(layout.control)
        )
    except ModelError as exc:
        raise SpecError(f"the plan review failed: {exc}") from exc
    objects = json_objects(raw)
    data = next(
        (
            item
            for item in objects
            if isinstance(item.get("sufficient"), bool)
        ),
        None,
    )
    if data is None:
        keys = [sorted(item.keys()) for item in objects]
        raise SpecError(
            "the plan review did not return a verdict; "
            f"model objects: {keys}; output: {raw[:600]}"
        )
    findings = [
        {
            "task": int(item.get("task", 0)),
            "issue": str(item.get("issue") or "").strip(),
        }
        for item in (data.get("findings") or [])
        if isinstance(item, dict)
    ]
    return PlanReview(bool(data["sufficient"]), findings)


def render_spec(
    spec: Mapping[str, Any],
    task_id: str,
    plan_id: str,
    repo_id: str,
) -> str:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    problem = str(spec.get("problem") or "").strip()
    outcome = str(spec.get("outcome") or "").strip()
    overview = problem
    if outcome:
        overview += ("\n\n" if overview else "") + f"**Outcome:** {outcome}"
    values = {
        "kind": "Task Spec",
        "title": spec.get("title") or "",
        "project": "—",
        "task": f"`{task_id}`",
        "plan": f"`{plan_id}`",
        "repository": f"`{repo_id or '(sole)'}`",
        "status": "Specification",
        "version": "1.0.0",
        "created": created,
        "source": f"Plan `{plan_id}`",
        "author": "Forgel requirements writer",
        "overview": overview or "—",
        "product_intent": spec.get("product_intent") or "—",
        "user_experience": spec.get("user_experience") or "—",
        "goals": requirements_doc.bullets(spec.get("goals") or []),
        "non_goals": requirements_doc.bullets(spec.get("non_goals") or []),
        "user_decisions": requirements_doc.decisions_table(
            spec.get("user_decisions") or []
        ),
        "functional_requirements": requirements_doc.numbered(
            "FR", spec.get("requirements") or []
        ),
        "user_stories": requirements_doc.bullets(
            spec.get("user_stories") or []
        ),
        "acceptance": requirements_doc.numbered(
            "AC", spec.get("acceptance") or []
        ),
        "scope": requirements_doc.bullets(
            list(spec.get("scope") or [])
            + list(spec.get("non_goals") or [])
        ),
        "risks": requirements_doc.bullets(spec.get("risks") or []),
        "open_questions": requirements_doc.bullets(
            spec.get("open_questions") or [], "None."
        ),
        "assumptions": requirements_doc.bullets(
            spec.get("assumptions") or []
        ),
        "related_documents": requirements_doc.bullets(
            spec.get("related_documents")
            or ["`docs/program/decisions.md`"]
        ),
        "revision_history": requirements_doc.bullets(
            spec.get("revision_history")
            or ["1.0.0 — Initial specification."]
        ),
    }
    return requirements_doc.render(values)


def spec_path(task_id: str) -> str:
    return f"{SPEC_DIR}/{task_id}.md"


def document_path(task: Mapping[str, Any]) -> str:
    """The requirements document of a task: its own spec, or the default."""

    return str(task.get("spec") or spec_path(str(task["id"])))


def cancelled(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> bool:
    """True when the requirements document is marked cancelled."""

    try:
        text = layout.artifact(document_path(task)).read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
    return text.lstrip().startswith(CANCEL_MARKER)


def mark_cancelled(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> bool:
    """Put the cancellation note at the top of the requirements document.

    Returns False when the task has no requirements document yet.
    """

    path = layout.artifact(document_path(task))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if text.lstrip().startswith(CANCEL_MARKER):
        return True
    write_text(path, CANCEL_NOTE + "\n" + text)
    return True
