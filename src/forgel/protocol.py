"""Planner gates for the fixed coder, QA and reviewer protocol.

The planner is the only role that accepts a specification, that judges a
coder's deviation from it, and that filters a reviewer's findings before they
reach the coder. The gates here are runtime stages, not agent choices: the
coder and the reviewer follow the process; they do not define it.

Every decision is recorded in the ledger so the task history shows what was
accepted, rejected or rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from . import specs, tasks
from .artifacts import write_text
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient, ModelError, ModelMessage, project_model_name
from .model_output import json_objects
from .tasks import attempt_number


class ProtocolError(RuntimeError):
    """The planner gate could not produce a usable decision."""


@dataclass(frozen=True)
class FindingDecision:
    finding: str
    valid: bool
    scope: str  # "code" | "spec"
    reason: str


@dataclass(frozen=True)
class IssueDecision:
    index: int
    rewrite: bool
    reason: str


FINDINGS_PROMPT = """You are Forgel's planner. A code review failed; before
anything reaches the coder you decide which findings are valid.

The accepted specification is the contract. Findings are requests to change
the work, not instructions. The specification was written and independently
reviewed, so assume it is valid by default: a request to change it needs a
concrete defect, not a preference.

For each finding decide:
- valid=true when it identifies a real unmet requirement, a logical or
  architectural defect in the diff, a security problem, an unjustified test
  deletion, or another verifiable failure, consistent with the accepted
  specification;
- valid=false when it contradicts the accepted specification, adds a product
  requirement nobody asked for, asks to change the specification for a
  preference or a simpler path rather than a concrete defect, is a
  stylistic opinion, is outside the task's scope, or is factually wrong.
For every valid finding set scope:
- "code" when the coder can fix it without changing the specification;
- "spec" when the specification itself is wrong, contradictory, unachievable
  or unsound and must be rewritten before the code.
Reject a finding only with a concrete reason grounded in the specification or
the evidence. Do not invent findings and do not change the process.

Return exactly one JSON object:
{"decisions": [{"index": 0, "valid": true | false,
                "scope": "code" | "spec", "reason": "..."}]}
"""


ISSUES_PROMPT = """You are Forgel's planner. The coder reported a deviation
from the accepted specification and gave reasons. Decide whether the
specification must be rewritten or the coder must comply.

The specification was written by one role and accepted by another, so assume
it is valid. A rewrite is an exception, not a routine choice: accept it only
for a concrete, verifiable defect — a logical contradiction, an unachievable
or unsound requirement, a security or architectural problem — never for a
preference, a simpler implementation or a wording change.

- rewrite=true when such a defect exists and the coder's justification is
  sound;
- rewrite=false when the deviation is not justified; the specification stands.
A deviation is not justified only because the code already exists. Give a
concrete reason grounded in the specification or the evidence.

Return exactly one JSON object:
{"decisions": [{"index": 0, "rewrite": true | false, "reason": "..."}]}
"""


def _task_context(layout: ProjectLayout, task: Mapping[str, Any]) -> str:
    parts = [f"Task: {task.get('title') or task.get('id')}"]
    for name in ("requirements", "acceptance", "constraints", "assumptions"):
        items = [str(item) for item in (task.get(name) or [])]
        if items:
            parts.append(
                name.title()
                + ":\n"
                + "\n".join(f"- {item}" for item in items)
            )
    spec_ref = str(task.get("spec") or "").strip()
    if spec_ref:
        try:
            spec_text = layout.artifact(spec_ref).read_text(
                encoding="utf-8"
            )
        except OSError:
            spec_text = ""
        if spec_text:
            parts.append(
                f"Accepted specification ({spec_ref}):\n{spec_text}"
            )
    return "\n\n".join(parts)


def _review_evidence(task: Mapping[str, Any]) -> str:
    result = dict(task.get("result") or {})
    review = result.get("review") if isinstance(
        result.get("review"), dict
    ) else {}
    qa = result.get("qa") if isinstance(result.get("qa"), dict) else {}
    lines = [
        f"Review verdict: {review.get('status') or 'fail'}",
        f"Review summary: {review.get('summary') or '—'}",
    ]
    qa_checks = [
        item
        for item in (qa.get("checks") or [])
        if item.get("verdict") == "fail"
    ]
    if qa_checks:
        lines.append(
            "Failed QA checks: "
            + "; ".join(
                f"{item.get('criterion')} (exit {item.get('exit_code')})"
                for item in qa_checks
            )
        )
    return "\n".join(lines)


def _complete(
    layout: ProjectLayout,
    messages: Sequence[ModelMessage],
    client: ModelClient,
) -> str:
    try:
        return client.complete(
            messages, model=project_model_name(layout.control)
        )
    except ModelError as exc:
        raise ProtocolError(
            f"the planner gate failed: {exc}"
        ) from exc


def _decisions(raw: str) -> list[dict[str, Any]]:
    for obj in json_objects(raw):
        items = obj.get("decisions")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    raise ProtocolError(
        "the planner gate did not return decisions"
    )


def filter_review_findings(
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    task: Mapping[str, Any],
    findings: Sequence[str],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> list[FindingDecision]:
    """Let the planner accept or reject each review finding."""

    if not findings:
        return []
    evidence = _review_evidence(task)
    listing = "\n".join(
        f"{index}. {finding}" for index, finding in enumerate(findings)
    )
    messages = [
        ModelMessage("system", FINDINGS_PROMPT),
        ModelMessage(
            "user",
            _task_context(layout, task)
            + "\n\n"
            + evidence
            + "\n\nFindings:\n"
            + listing,
        ),
    ]
    raw = _complete(layout, messages, client)
    decisions: dict[int, dict[str, Any]] = {}
    for item in _decisions(raw):
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            raise ProtocolError(
                "the planner gate returned a decision without an index"
            ) from None
        if 0 <= index < len(findings):
            decisions[index] = item
    if len(decisions) != len(findings):
        raise ProtocolError(
            "the planner gate did not decide every finding"
        )
    result: list[FindingDecision] = []
    for index, finding in enumerate(findings):
        item = decisions[index]
        valid = item.get("valid")
        if not isinstance(valid, bool):
            raise ProtocolError(
                f"the planner gate gave no verdict for finding {index}"
            )
        scope = str(item.get("scope") or "code").strip().lower()
        if valid and scope not in {"code", "spec"}:
            raise ProtocolError(
                f"the planner gate gave an unknown scope for finding {index}"
            )
        reason = str(item.get("reason") or "").strip()
        if not reason:
            raise ProtocolError(
                f"the planner gate gave no reason for finding {index}"
            )
        result.append(
            FindingDecision(
                finding=finding,
                valid=valid,
                scope=scope if valid else "code",
                reason=reason,
            )
        )
    _record(
        ledger,
        project,
        task,
        "review_filter",
        {
            "decisions": [
                {
                    "finding": item.finding,
                    "valid": item.valid,
                    "scope": item.scope,
                    "reason": item.reason,
                }
                for item in result
            ],
            "valid": sum(1 for item in result if item.valid),
        },
    )
    log(
        f"[planner] {project['id']}: task {task['id']}: "
        f"{sum(1 for item in result if item.valid)}/{len(result)} "
        "review finding(s) accepted"
    )
    return result


def assess_spec_issues(
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    task: Mapping[str, Any],
    issues: Sequence[Mapping[str, Any]],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> list[IssueDecision]:
    """Let the planner decide whether a coder deviation rewrites the spec."""

    if not issues:
        return []
    listing = "\n".join(
        f"{index}. requirement: {item.get('requirement') or '—'}\n"
        f"   problem: {item.get('problem') or '—'}\n"
        f"   proposal: {item.get('proposal') or '—'}"
        for index, item in enumerate(issues)
    )
    messages = [
        ModelMessage("system", ISSUES_PROMPT),
        ModelMessage(
            "user",
            _task_context(layout, task)
            + "\n\nReported deviations:\n"
            + listing,
        ),
    ]
    raw = _complete(layout, messages, client)
    decisions: dict[int, dict[str, Any]] = {}
    for item in _decisions(raw):
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            raise ProtocolError(
                "the planner gate returned a decision without an index"
            ) from None
        if 0 <= index < len(issues):
            decisions[index] = item
    if len(decisions) != len(issues):
        raise ProtocolError(
            "the planner gate did not decide every reported deviation"
        )
    result: list[IssueDecision] = []
    for index in range(len(issues)):
        item = decisions[index]
        rewrite = item.get("rewrite")
        if not isinstance(rewrite, bool):
            raise ProtocolError(
                f"the planner gate gave no verdict for deviation {index}"
            )
        reason = str(item.get("reason") or "").strip()
        if not reason:
            raise ProtocolError(
                f"the planner gate gave no reason for deviation {index}"
            )
        result.append(
            IssueDecision(index=index, rewrite=rewrite, reason=reason)
        )
    _record(
        ledger,
        project,
        task,
        "spec_issue",
        {
            "decisions": [
                {
                    "index": item.index,
                    "rewrite": item.rewrite,
                    "reason": item.reason,
                }
                for item in result
            ],
        },
    )
    log(
        f"[planner] {project['id']}: task {task['id']}: "
        f"{sum(1 for item in result if item.rewrite)}/{len(result)} "
        "specification deviation(s) accepted"
    )
    return result


def rewrite_task_spec(
    settings: Any,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
    task: Mapping[str, Any],
    client: ModelClient,
    issue: str,
    log: Callable[[str], None] = print,
) -> str:
    """Rewrite the accepted specification from the planner's finding."""

    task_id = str(task["id"])
    repo_id = str(task.get("repo_id") or "").strip()
    intent = {
        "title": task.get("title") or task_id,
        "summary": task.get("summary") or task.get("title") or task_id,
        "repo_id": repo_id,
    }
    goal = str(task.get("plan_goal") or task.get("title") or "—")
    spec = specs.write_task_spec(
        settings,
        layout,
        goal,
        "",
        intent,
        client,
        log=log,
        review_issue=issue,
    )
    ref = specs.spec_path(task_id)
    write_text(
        layout.artifact(ref),
        specs.render_spec(
            spec,
            task_id,
            str(task.get("plan_id") or ""),
            repo_id,
        ),
    )
    tasks.update_task(layout, task_id, spec=ref)
    updates: dict[str, Any] = {}
    if not task.get("requirements"):
        updates["requirements"] = list(spec.get("requirements") or [])
    if not task.get("acceptance"):
        updates["acceptance"] = list(spec.get("acceptance") or [])
    if spec.get("external_dependencies"):
        updates["external_dependencies"] = list(
            spec["external_dependencies"]
        )
    if updates:
        tasks.update_task(layout, task_id, **updates)
    tasks.commit_task(layout, task_id, f"Rewrite spec {task_id}")
    _record(
        ledger,
        project,
        task,
        "spec_rewrite",
        {
            "issue": issue,
            "requirements": list(spec.get("requirements") or []),
        },
        artifact_refs=[ref],
    )
    log(
        f"[planner] {project['id']}: task {task_id}: "
        f"specification rewritten ({ref})"
    )
    return ref


def _record(
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    stage: str,
    payload: dict[str, Any],
    artifact_refs: Sequence[str] = (),
) -> None:
    attempt = attempt_number(task)
    ledger.append_event(
        str(project["id"]),
        stage,
        status="completed",
        idempotency_key=(
            f"{project['id']}:{stage}:{task['id']}:r{attempt}"
        ),
        artifact_refs=list(artifact_refs),
        payload=payload,
        generation=ledger.current_generation(str(project["id"])),
    )
