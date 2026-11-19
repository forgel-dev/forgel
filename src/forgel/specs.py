"""Formal task specifications and plan review.

The planner decomposes a milestone into task intents. A separate requirements
writer turns each intent into a formal specification document; a plan review
then judges the whole set against the original problem, not against the specs
themselves. The specification is the artifact the coding agent, QA and the
independent reviewer work from; the task record is an index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from . import requirements as requirements_doc
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
SPEC_DIR = "docs/program/specs"


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
  "open_questions": ["only a question that cannot be decided reversibly"],
  "affected_files": ["path or area"],
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
  result is judged. Do not add features beyond the intent.
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
        "depends_on": list(intent.get("depends_on") or []),
        "problem": str(data.get("problem") or "").strip(),
        "outcome": str(data.get("outcome") or "").strip(),
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
        "affected_files": _strings(data.get("affected_files")),
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
            "<function_call",
            "<system_warning",
        )
    )


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
    for _ in range(MAX_SPEC_STEPS + 4):
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
        if finals:
            try:
                parsed = _normalize_spec(finals[-1], intent)
                problems = check_problems(
                    layout,
                    str(intent.get("repo_id") or ""),
                    parsed.get("checks") or [],
                )
                if problems:
                    raise SpecError("; ".join(problems))
                break
            except SpecError as exc:
                if retries >= 1:
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
                        f"The specification is invalid: {exc}. Return a "
                        "complete JSON specification. Every command check "
                        "must run in the task repository "
                        f"'{intent.get('repo_id') or 'project root'}' and "
                        "must not point at files that exist only in another "
                        "repository.",
                    )
                )
                retries += 1
                continue
        if _looks_like_tool_markup(raw) and markup_retries < 2:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return exactly one JSON specification object, not "
                    "tool-call markup or XML. Do not emit "
                    "<｜｜DSML｜｜>, <tool_call> or provider-specific calls.",
                )
            )
            markup_retries += 1
            continue
        if not actions:
            if retries >= 1:
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
    depends_on: Sequence[str],
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
        "depends_on": ", ".join(f"`{item}`" for item in depends_on)
        or "none",
        "status": "Specification",
        "version": "1.0.0",
        "created": created,
        "source": f"Plan `{plan_id}`",
        "author": "Forgel requirements writer",
        "overview": overview or "—",
        "goals": requirements_doc.bullets(spec.get("goals") or []),
        "non_goals": requirements_doc.bullets(spec.get("non_goals") or []),
        "user_decisions": requirements_doc.decisions_table(
            spec.get("user_decisions") or []
        ),
        "functional_requirements": requirements_doc.numbered(
            "FR", spec.get("requirements") or []
        ),
        "technical_requirements": requirements_doc.bullets(
            spec.get("constraints") or []
        ),
        "user_stories": requirements_doc.bullets(
            spec.get("user_stories") or []
        ),
        "tests": requirements_doc.checks_text(
            spec.get("checks") or [], spec.get("test_command") or []
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
        "affected_files": requirements_doc.bullets(
            spec.get("affected_files") or [], "Not identified yet."
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
    return requirements_doc.render(values) + _external_section(spec)


def _external_section(spec: Mapping[str, Any]) -> str:
    dependencies = [
        item
        for item in (spec.get("external_dependencies") or [])
        if isinstance(item, dict)
    ]
    if not dependencies:
        return ""
    lines = ["", "## External Dependencies", ""]
    for item in dependencies:
        lines.append(
            f"- **{item.get('name') or '—'}** — mode `"
            f"{item.get('mode') or 'unknown'}`; interface: "
            f"{item.get('interface') or '—'}; docs: "
            f"{item.get('docs') or '—'}; evidence: "
            f"{item.get('evidence') or '—'}"
        )
        stub = str(item.get("stub") or "").strip()
        if stub:
            lines.append("  ```")
            lines.extend("  " + line for line in stub.splitlines())
            lines.append("  ```")
    return "\n".join(lines) + "\n"


def spec_path(task_id: str) -> str:
    return f"{SPEC_DIR}/{task_id}.md"
