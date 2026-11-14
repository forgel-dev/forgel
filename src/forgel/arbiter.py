"""External arbiter between the developer and the reviewer.

A repeated rejection can mean the change is wrong, or that the acceptance
criteria are wrong. The developer and the reviewer cannot settle that between
themselves: the arbiter sees both sides with a clean context and decides.

    accept    the change meets the requirements; the reviewer is wrong;
    fix       the change does not meet the requirements; send it back;
    criteria  the criteria are inconsistent or unverifiable; re-specify.

The verdict is recorded and visible. It never modifies the acceptance criteria
itself: a "criteria" verdict fails the task with the proposed revision for a
human or the planner to act on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .artifacts import write_text
from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .task_review import MAX_DIFF_CHARS, task_diff
from .tasks import get_task, update_task

MAX_TEXT = 4_000


@dataclass(frozen=True)
class ArbiterResult:
    verdict: str  # accept | fix | criteria | error
    summary: str
    rationale: str = ""
    proposed_criteria: list[str] = field(default_factory=list)
    report: str = ""
    output: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cap(text: str, limit: int = MAX_TEXT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


SYSTEM_PROMPT = """You are an external arbiter between a developer and an
independent reviewer. You did not implement the change and you must not modify
the repository.

Decide the disagreement:
- "accept": the change meets the explicit requirements; the reviewer is wrong;
- "fix": the change does not meet the requirements; send it back to the
  developer;
- "criteria": the acceptance criteria are inconsistent, unverifiable or
  contradict the requirements; the task must be re-specified, not reworked.

Return exactly one JSON object:
{
  "verdict": "accept" | "fix" | "criteria",
  "summary": "the decision in one paragraph",
  "rationale": "why, referring to the requirements and the evidence",
  "proposed_criteria": ["a revised acceptance criterion, criteria verdict only"]
}

Be concrete. Do not accept a change that fails an executable check. Do not
blame the developer for a criterion that cannot be verified.
"""


def _prompt(layout: ProjectLayout, task: Mapping[str, Any]) -> str:
    result = dict(task.get("result") or {})
    requirements = "\n".join(
        f"- {item}" for item in task.get("requirements", [])
    ) or "- none"
    acceptance = "\n".join(
        f"- {item}" for item in task.get("acceptance", [])
    ) or "- none"
    constraints = "\n".join(
        f"- {item}" for item in task.get("constraints", [])
    ) or "- none"
    review = result.get("review") if isinstance(result.get("review"), dict) else {}
    qa = result.get("qa") if isinstance(result.get("qa"), dict) else {}
    blocking = "\n".join(
        f"- {item}" for item in (review.get("blocking") or [])
    ) or "- none"
    review_requirements = "\n".join(
        f"- {item.get('requirement')}: {item.get('verdict')} "
        f"{item.get('note', '')}"
        for item in (review.get("requirements") or [])
        if isinstance(item, dict)
    ) or "- none"
    checks = "\n".join(
        f"- {item.get('criterion')}: {item.get('verdict')}"
        for item in (qa.get("checks") or [])
    ) or "- none"
    feedback = "\n".join(
        f"- {item}" for item in (result.get("feedback") or [])
    ) or "- none"
    return f"""TASK: {task.get('title', task.get('id'))}

Requirements:
{requirements}

Acceptance criteria:
{acceptance}

Constraints:
{constraints}

Reviewer verdict: {review.get('status', 'none')}
Reviewer summary: {review.get('summary', '')}
Blocking defects:
{blocking}
Reviewer per-requirement verdicts:
{review_requirements}

QA: {qa.get('status', 'not run')} ({qa.get('runtime', 'n/a')})
Checks:
{checks}

Developer summary: {result.get('summary', '')}
Developer assumptions:
{chr(10).join(f'- {item}' for item in (task.get('assumptions') or [])) or '- none'}
Feedback already given on the previous attempt:
{feedback}

Diff:
{_cap(task_diff(layout, task), MAX_DIFF_CHARS)}
"""


def _parse(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("the arbiter did not return JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("the arbitration must be a JSON object")
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in {"accept", "fix", "criteria"}:
        raise ValueError("the arbiter verdict must be accept, fix or criteria")
    proposed = [
        str(item).strip()
        for item in data.get("proposed_criteria", [])
        if str(item).strip()
    ]
    return {
        "verdict": verdict,
        "summary": str(data.get("summary", "")).strip(),
        "rationale": str(data.get("rationale", "")).strip(),
        "proposed_criteria": proposed,
    }


def _record(
    ledger: Ledger,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    result: ArbiterResult,
    log: Callable[[str], None],
) -> ArbiterResult:
    task_id = str(task["id"])
    path = layout.artifact(f"docs/program/agent/{task_id}.arbiter.md")
    report_ref = str(path.relative_to(layout.root))
    proposed = (
        "\n".join(f"- {item}" for item in result.proposed_criteria)
        or "- none"
    )
    write_text(
        path,
        f"""# Task Arbitration: {task.get('title', task_id)}

- Task: `{task_id}`
- Project: `{project['id']}`
- Verdict: **{result.verdict.upper()}**
- Finished: {_now()}

## Summary

{result.summary or '—'}

## Rationale

{result.rationale or '—'}

## Proposed Criteria

{proposed}
""",
    )
    stored = get_task(layout, task_id) or task
    data = dict(stored.get("result") or {})
    data["arbiter"] = {
        "verdict": result.verdict,
        "summary": result.summary,
        "rationale": result.rationale,
        "proposed_criteria": result.proposed_criteria,
        "report": report_ref,
    }
    update_task(layout, task_id, result=data)
    ledger.append_event(
        str(project["id"]),
        "task_arbiter",
        status={
            "accept": "completed",
            "fix": "completed",
            "criteria": "completed",
            "error": "error",
        }[result.verdict],
        idempotency_key=(
            f"{project['id']}:task_arbiter:{task_id}:{result.verdict}"
        ),
        artifact_refs=[report_ref],
        payload={
            "task": task_id,
            "verdict": result.verdict,
            "proposed_criteria": result.proposed_criteria,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[arbiter] {project['id']}: task {task_id}: {result.verdict}"
    )
    return ArbiterResult(
        verdict=result.verdict,
        summary=result.summary,
        rationale=result.rationale,
        proposed_criteria=result.proposed_criteria,
        report=report_ref,
        output=result.output,
    )


def run_task_arbiter(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> ArbiterResult:
    layout = ProjectLayout.detect(str(project["workspace"]))
    task = get_task(layout, str(task["id"])) or task
    if client is None:
        return _record(
            ledger,
            layout,
            project,
            task,
            ArbiterResult(
                verdict="error",
                summary="No model client is configured for the arbiter.",
            ),
            log,
        )
    messages = [
        ModelMessage("system", SYSTEM_PROMPT),
        ModelMessage("user", _prompt(layout, task)),
    ]
    try:
        raw = client.complete(
            messages, model=project_model_name(layout.control)
        )
    except ModelError as exc:
        return _record(
            ledger,
            layout,
            project,
            task,
            ArbiterResult(
                verdict="error",
                summary=f"Arbiter model call failed: {exc}",
            ),
            log,
        )
    try:
        parsed = _parse(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        return _record(
            ledger,
            layout,
            project,
            task,
            ArbiterResult(
                verdict="error",
                summary=f"Arbiter returned an unusable answer: {exc}",
                output=_cap(raw),
            ),
            log,
        )
    return _record(
        ledger,
        layout,
        project,
        task,
        ArbiterResult(
            verdict=parsed["verdict"],
            summary=parsed["summary"],
            rationale=parsed["rationale"],
            proposed_criteria=parsed["proposed_criteria"],
        ),
        log,
    )
