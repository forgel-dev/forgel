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

MAX_SPEC_STEPS = 8
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
- Return JSON only; no tool-call markup, XML or prose.
"""


PLAN_REVIEW_PROMPT = """You review a milestone plan against the original
problem. You are not checking whether the specs are internally consistent or
whether their requirements are met. You are answering one question:

If every task is completed exactly as written, will the user's original
problem be solved?

Read the goal, the plan notes and the specifications. Name:
- what the plan assumes but does not deliver;
- which part of the goal no task covers;
- any task that can be green while the problem remains unsolved.

Recorded user decisions in the specifications are binding. A plan that
contradicts a recorded decision is insufficient even if every task passes.

Return exactly one JSON object:
{"sufficient": true | false,
 "findings": [{"task": 0, "issue": "concrete gap"}]}

Use sufficient=true only when the plan as written solves the problem. Do not
rewrite the specifications; report the gaps. Return JSON only.
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
    messages = [
        ModelMessage("system", SPEC_SYSTEM_PROMPT),
        ModelMessage(
            "user",
            "Milestone goal:\n"
            f"{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
            f"Task intent:\n{json.dumps(dict(intent), ensure_ascii=False)}\n\n"
            f"User decision log:\n{decisions_text}\n\n"
            f"Repository file tree:\n{_context(layout, repo_id)}\n\n"
            + (
                "The plan review rejected the previous version for this "
                f"task:\n{review_issue}\n\n"
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
    for _ in range(MAX_SPEC_STEPS + 4):
        try:
            raw = client.complete(messages, model=model)
        except ModelError as exc:
            raise SpecError(f"the requirements writer failed: {exc}") from exc
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
        if observations:
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
                break
            except SpecError as exc:
                if retries >= 1:
                    keys = sorted(finals[-1].keys())
                    raise SpecError(
                        f"{exc}; model keys: {keys}; output: {raw[:600]}"
                    ) from exc
                if not observations:
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
        if not actions:
            if retries >= 1:
                raise SpecError(
                    "the requirements writer did not return a specification"
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
                    "the requirements writer exceeded the research step limit"
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
        raise SpecError("the requirements writer did not return a spec")
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

    rendered = "\n\n".join(
        f"--- Task {index}: {spec.get('title')} ---\n"
        f"Problem: {spec.get('problem')}\n"
        f"Outcome: {spec.get('outcome')}\n"
        f"Scope: {'; '.join(spec.get('scope') or [])}\n"
        f"Non-goals: {'; '.join(spec.get('non_goals') or [])}\n"
        f"Requirements: {'; '.join(spec.get('requirements') or [])}\n"
        f"Acceptance: {'; '.join(spec.get('acceptance') or [])}\n"
        f"Assumptions: {'; '.join(spec.get('assumptions') or [])}\n"
        f"Risks: {'; '.join(spec.get('risks') or [])}\n"
        for index, spec in enumerate(specs)
    )
    messages = [
        ModelMessage("system", PLAN_REVIEW_PROMPT),
        ModelMessage(
            "user",
            f"Milestone goal:\n{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
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
    return requirements_doc.render(values)


def spec_path(task_id: str) -> str:
    return f"{SPEC_DIR}/{task_id}.md"
