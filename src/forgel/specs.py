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
from typing import Any, Callable, Mapping, Sequence

from .layout import ProjectLayout
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

Return exactly one JSON object:
{"sufficient": true | false,
 "findings": [{"task": 0, "issue": "concrete gap"}]}

Use sufficient=true only when the plan as written solves the problem. Do not
rewrite the specifications; report the gaps. Return JSON only.
"""


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
    messages = [
        ModelMessage("system", SPEC_SYSTEM_PROMPT),
        ModelMessage(
            "user",
            "Milestone goal:\n"
            f"{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
            f"Task intent:\n{json.dumps(dict(intent), ensure_ascii=False)}\n\n"
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
    for step in range(MAX_SPEC_STEPS + 2):
        try:
            raw = client.complete(messages, model=model)
        except ModelError as exc:
            raise SpecError(f"the requirements writer failed: {exc}") from exc
        data = _json_object(raw)
        action = str(data.get("action", "")) if data else ""
        if action in RESEARCH_ACTIONS and step < MAX_SPEC_STEPS:
            args = dict(data.get("action_args") or {})
            for key in ("path", "repo_id"):
                if key in data and key not in args:
                    args[key] = data[key]
            try:
                observation = execute_repo_action(
                    layout,
                    manifest_entries(layout),
                    {"action": action, **args},
                )
            except RepoActionError as exc:
                observation = f"error: {exc}"
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observation:\n"
                    + observation[:MAX_SPEC_CHARS]
                    + "\n\nReturn another action or the final spec JSON.",
                )
            )
            continue
        try:
            parsed = _normalize_spec(data or {}, intent)
            break
        except SpecError:
            if retries >= 1:
                raise
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return a complete JSON specification with explicit "
                    "requirements, acceptance criteria and checks.",
                )
            )
            retries += 1
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
    data = _json_object(raw)
    if data is None or not isinstance(data.get("sufficient"), bool):
        raise SpecError("the plan review did not return a verdict")
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
    def bullets(values: Sequence[Any], empty: str = "none") -> str:
        return "\n".join(f"- {value}" for value in values) or f"- {empty}"

    checks = "\n".join(
        f"- {item['criterion']}: "
        + (
            "review"
            if item["verification"] == "review"
            else "`" + " ".join(item["command"]) + "`"
        )
        for item in spec.get("checks") or []
    ) or "- none"
    return f"""# Task Spec: {spec.get('title')}

- Task: `{task_id}`
- Plan: `{plan_id}`
- Repository: `{repo_id or '(sole)'}`
- Depends on: {', '.join(f'`{item}`' for item in depends_on) or 'none'}

## Problem

{spec.get('problem') or '—'}

## Outcome

{spec.get('outcome') or '—'}

## Scope

{bullets(spec.get('scope') or [])}

## Non-goals

{bullets(spec.get('non_goals') or [])}

## Requirements

{bullets(spec.get('requirements') or [])}

## Acceptance

{bullets(spec.get('acceptance') or [])}

## Checks

{checks}

## Constraints

{bullets(spec.get('constraints') or [])}

## Assumptions

{bullets(spec.get('assumptions') or [])}

## Risks

{bullets(spec.get('risks') or [])}
"""


def spec_path(task_id: str) -> str:
    return f"{SPEC_DIR}/{task_id}.md"
