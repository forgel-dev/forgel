"""Long-running control-plane loop.

Forgel is a daemon, not a one-shot CLI: it picks projects with pending work,
runs one finite iteration, and then waits. A completed project is never looped
on again; new work starts a new iteration.
"""

from __future__ import annotations

import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from . import dependencies, peak, specs, tasks
from .artifacts import write_text
from .approvals import awaits_approval, latest_approval
from .coding_agent import CodingAgent
from .task_review import accept_parked_green_tasks, process_task_result
from .config import Settings
from .control import is_paused
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient, build_model_client
from .orchestrator import Orchestrator
from .state import STAGES


def project_is_done(ledger: Ledger, project_id: str) -> bool:
    state = ledger.checkpoint_state(project_id)
    if state is None:
        return False
    stage, generation = state
    return stage == "done" and ledger.has_completed(project_id, "done", generation)


def has_blocking_reconciliation(workspace: Path) -> bool:
    path = ProjectLayout.detect(workspace).artifact(
        "docs/program/reconciliation.md"
    )
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "- Status: pending" in text or "- Status: fix_required" in text


def project_state(ledger: Ledger, project: dict[str, Any]) -> str:
    """Return a short human-readable state used by status and notifications."""

    project_id = project["id"]
    layout = ProjectLayout.detect(project["workspace"])
    if has_blocking_reconciliation(Path(project["workspace"])):
        return "reconciliation pending"
    task = tasks.latest_task(layout)
    if task is not None and task.get("status") == "pending":
        moment = tasks.retry_moment(task)
        if moment is not None and moment > datetime.now(timezone.utc):
            return f"task retry at {moment.strftime('%H:%M UTC')}"
    if task is not None and task.get("status") in {
        "pending",
        "running",
        "review",
        "blocked",
        "failed",
    }:
        return f"task {task['status']}"
    if (
        tasks.next_pending_task(layout) is None
        and tasks.blocked_pending(layout)
    ):
        return "task blocked"
    state = ledger.checkpoint_state(project_id)
    if state is None:
        if task is not None and task.get("status") == "done":
            return "task done"
        if task is not None and task.get("status") == "cancelled":
            return "task cancelled"
        return "adopted" if layout.metadata().get("mode") == "brownfield" else "queued"
    stage, generation = state
    if stage == "approval":
        approval = latest_approval(ledger, project_id, "staging", generation)
        if approval is None:
            return "awaiting staging approval"
        if approval["decision"] != "approved":
            return f"staging {approval['decision']}"
    stage_events = [
        event
        for event in ledger.events(project_id, generation)
        if event["stage"] in STAGES
    ]
    if stage_events and stage_events[-1]["status"] == "failed":
        return f"failed at {stage_events[-1]['stage']}"
    return stage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failure(
    kind: str, message: str, retryable: bool | None = None
) -> dict[str, Any]:
    return {
        "kind": kind,
        "message": message,
        "retryable": (
            kind == "infrastructure" if retryable is None else retryable
        ),
    }


def _classify_crash(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    lowered = message.lower()
    if "sandbox" in lowered or "docker" in lowered:
        return _failure("infrastructure", message)
    return _failure("external", message, retryable=False)


def _tail(text: Any, limit: int = 3_000) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return "… [truncated]\n" + value[-limit:]


def _feedback_from(data: dict[str, Any]) -> list[str]:
    feedback: list[str] = []
    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    for item in review.get("blocking") or []:
        feedback.append(f"review: {item}")
    if review.get("summary"):
        feedback.append(f"review summary: {review['summary']}")
    qa = data.get("qa") if isinstance(data.get("qa"), dict) else {}
    failure_kind = str(qa.get("failure_kind") or "").strip()
    if failure_kind in {"spec", "environment", "infrastructure"}:
        feedback.append(
            f"QA failure kind: {failure_kind}. This is not a code defect; "
            "the runtime routes it away from the coding agent."
        )
    for item in qa.get("checks") or []:
        if item.get("verdict") != "fail":
            continue
        lines = [
            f"QA check failed: {item.get('criterion')}",
            f"  repository: {item.get('repo') or 'project root'}",
            f"  cwd: {item.get('workdir') or '-'}",
            f"  command: {item.get('command') or '-'}",
            f"  exit: {item.get('exit_code')}",
        ]
        output = _tail(item.get("output"))
        if output:
            lines.append("  output:\n" + output)
        if item.get("scope") == "e2e":
            lines.append(
                "  note: program e2e failure; fix the integration, not only "
                "the unit test"
            )
        feedback.append("\n".join(lines))
    if not feedback:
        feedback.append(
            str(data.get("summary") or "the previous attempt failed")
        )
    return feedback


def _review_findings(data: dict[str, Any]) -> list[str]:
    """The review's concrete findings, without the prose summary."""

    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    findings: list[str] = []
    for item in review.get("blocking") or []:
        text = str(item).strip()
        if text:
            findings.append(text)
    for item in review.get("requirements") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("verdict") or "") in {"pass", ""}:
            continue
        requirement = str(item.get("requirement") or "").strip()
        note = str(item.get("note") or "").strip()
        if requirement:
            findings.append(
                f"{requirement}: {note}" if note else requirement
            )
    seen: set[str] = set()
    unique: list[str] = []
    for finding in findings:
        if finding not in seen:
            seen.add(finding)
            unique.append(finding)
    return unique


def _handle_spec_issues(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task: dict[str, Any],
    issues: list[dict[str, Any]],
    client: ModelClient,
    log: Callable[[str], None],
) -> None:
    """Route a coder's specification deviation through the planner gate."""

    from . import protocol

    task_id = str(task["id"])
    try:
        decisions = protocol.assess_spec_issues(
            ledger, project, layout, task, issues, client, log
        )
    except Exception as exc:  # noqa: BLE001 - the gate must not crash the daemon
        data = dict(task.get("result") or {})
        data["failure"] = _failure(
            "infrastructure",
            f"the planner could not assess the specification issue: {exc}",
        )
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result=data,
        )
        log(
            f"[planner] {project['id']}: task {task_id}: "
            f"specification gate failed: {exc}"
        )
        return
    accepted = [item for item in decisions if item.rewrite]
    rejected = [item for item in decisions if not item.rewrite]
    reasons = "; ".join(item.reason for item in rejected)
    if accepted:
        issue_text = "\n".join(
            f"- {issues[item.index].get('problem') or 'specification issue'}: "
            f"{item.reason}"
            + (
                f" (proposal: {issues[item.index].get('proposal')})"
                if issues[item.index].get("proposal")
                else ""
            )
            for item in accepted
        )
        try:
            protocol.rewrite_task_spec(
                settings,
                ledger,
                project,
                layout,
                task,
                client,
                issue_text,
                log,
            )
        except Exception as exc:  # noqa: BLE001
            data = dict(task.get("result") or {})
            data["failure"] = _failure(
                "infrastructure",
                "the planner accepted a specification issue but the "
                f"rewrite failed: {exc}",
            )
            tasks.update_task(
                layout,
                task_id,
                status="failed",
                finished_at=_now(),
                result=data,
            )
            log(
                f"[planner] {project['id']}: task {task_id}: "
                f"specification rewrite failed: {exc}"
            )
            return
        message = (
            "the planner accepted the specification issue and rewrote the "
            "specification; implement the new version"
        )
        if reasons:
            message += f". Rejected deviations: {reasons}"
    else:
        message = (
            "the planner rejected the deviation; follow the accepted "
            "specification"
            + (f": {reasons}" if reasons else "")
        )
    data = dict(task.get("result") or {})
    data["failure"] = _failure("spec", message, retryable=False)
    data["spec_feedback"] = [message]
    data.pop("spec_issues", None)
    tasks.update_task(
        layout,
        task_id,
        status="failed",
        finished_at=_now(),
        result=data,
    )
    log(f"[planner] {project['id']}: task {task_id}: {message}")


def _dismiss_review(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task_id: str,
    data: dict[str, Any],
    log: Callable[[str], None],
) -> None:
    """The planner rejected every finding; the review counts as passed."""

    from .task_review import accept_task, await_acceptance

    data["review_filter"]["dismissed"] = True
    task = tasks.update_task(layout, task_id, result=data)
    attempt = tasks.attempt_number(task)
    ledger.append_event(
        str(project["id"]),
        "review_dismissed",
        status="completed",
        idempotency_key=(
            f"{project['id']}:review_dismissed:{task_id}:r{attempt}"
        ),
        artifact_refs=[],
        payload={
            "dismissed": [
                item["finding"]
                for item in data["review_filter"]["decisions"]
                if not item["valid"]
            ]
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    if settings.task_accept == "auto":
        accept_task(
            settings,
            ledger,
            project,
            task,
            actor="planner",
            notes="the planner rejected every review finding",
        )
    else:
        await_acceptance(
            layout,
            task,
            "the planner rejected every review finding; acceptance required",
        )
    log(
        f"[planner] {project['id']}: task {task_id}: "
        "all review findings rejected; the review passes"
    )


def _quarantine(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task_id: str,
    failure: dict[str, Any],
    attempts: int,
    log: Callable[[str], None],
) -> None:
    if settings.plan_on_failure == "stop":
        tasks.block_dependents(layout, task_id, stop=True)
    elif settings.plan_on_failure == "quarantine":
        tasks.block_dependents(layout, task_id, stop=False)
    stored = tasks.get_task(layout, task_id) or {}
    attempt = tasks.attempt_number(stored)
    ledger.append_event(
        str(project["id"]),
        "task_failure",
        status="failed",
        idempotency_key=(
            f"{project['id']}:task_failure:{task_id}:"
            f"{failure.get('kind')}:{attempts}:r{attempt}"
        ),
        artifact_refs=[],
        payload={
            "task": task_id,
            "kind": failure.get("kind"),
            "attempts": attempts,
            "rework": attempt,
            "policy": settings.plan_on_failure,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[task] {project['id']}: {task_id} failed "
        f"({failure.get('kind')}); policy {settings.plan_on_failure}"
    )


def _rewrite_spec_from_failure(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task: dict[str, Any],
    client: ModelClient,
    failure: dict[str, Any],
    log: Callable[[str], None],
) -> bool:
    """Repair an invalid check or criterion without sending the coder back.

    A specification defect is the planner's problem, not the code's. Rewriting
    the spec keeps ``rework_count`` for code failures only and prevents a
    coder from being asked to fix a check that cannot pass.
    """

    task_id = str(task["id"])
    data = dict(task.get("result") or {})
    reworks = int(data.get("spec_rework_count", 0))
    limit = max(1, settings.task_reworks)
    if reworks >= limit:
        log(
            f"[spec] {project['id']}: task {task_id}: "
            "specification rework limit reached"
        )
        return False
    issue = str(failure.get("message") or "").strip() or (
        "the specification has an invalid acceptance check"
    )
    from . import protocol

    try:
        protocol.rewrite_task_spec(
            settings, ledger, project, layout, task, client, issue, log
        )
    except Exception as exc:  # noqa: BLE001 - the failure path must not crash
        log(
            f"[spec] {project['id']}: task {task_id}: "
            f"specification rewrite failed: {exc}"
        )
        return False
    data["spec_rework_count"] = reworks + 1
    data["feedback"] = [
        "The specification was rewritten after an invalid check: "
        + _tail(issue, 800),
        "Implement the new specification. Do not change code only to "
        "satisfy the old check.",
    ]
    data["last_failure"] = failure
    data.pop("failure", None)
    tasks.update_task(
        layout,
        task_id,
        status="pending",
        started_at="",
        finished_at="",
        result=data,
    )
    log(
        f"[spec] {project['id']}: task {task_id}: invalid check; "
        f"specification rewritten; spec rework "
        f"{reworks + 1}/{limit}"
    )
    return True


def handle_failure(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task_id: str,
    client: ModelClient | None,
    log: Callable[[str], None],
    now: datetime | None = None,
) -> None:
    """React to a failure by kind: retry, rework, arbitrate, quarantine."""

    task = tasks.get_task(layout, task_id)
    if task is None or task.get("status") != "failed":
        return
    moment = now or datetime.now(timezone.utc)
    data = dict(task.get("result") or {})
    failure = dict(
        data.get("failure")
        or _failure("external", "unknown failure", retryable=False)
    )
    kind = str(failure.get("kind") or "external")
    attempts = int(data.get("attempts", 0))
    if kind == "infrastructure" and attempts < settings.task_retries:
        backoff = settings.retry_backoff or (1,)
        delay = backoff[min(attempts, len(backoff) - 1)]
        retry_at = (moment + timedelta(minutes=delay)).isoformat(
            timespec="seconds"
        )
        data["attempts"] = attempts + 1
        data["retry_after"] = retry_at
        data["last_failure"] = failure
        data.pop("failure", None)
        tasks.update_task(
            layout,
            task_id,
            status="pending",
            started_at="",
            finished_at="",
            result=data,
        )
        log(
            f"[retry] {project['id']}: task {task_id} infrastructure "
            f"failure; retry {attempts + 1}/{settings.task_retries} "
            f"in {delay}m (at {retry_at})"
        )
        return
    spec_feedback = [
        str(item) for item in (data.get("spec_feedback") or [])
    ]
    if kind == "spec" and not spec_feedback:
        # An invalid check or criterion is the planner's defect. Rewrite the
        # spec; never spend a coder rework on a check that cannot pass.
        if client is not None and _rewrite_spec_from_failure(
            settings, ledger, project, layout, task, client, failure, log
        ):
            return
        _quarantine(
            settings, ledger, project, layout, task_id, failure, attempts, log
        )
        return
    if kind == "environment":
        # A project-level environment gate or a broken contract is not the
        # code under test. Keep the coder out of it and show the evidence.
        _quarantine(
            settings, ledger, project, layout, task_id, failure, attempts, log
        )
        return
    filtered_feedback: list[str] | None = None
    if kind == "review" and client is not None:
        findings = _review_findings(data)
        if findings:
            from . import protocol

            try:
                decisions = protocol.filter_review_findings(
                    ledger, project, layout, task, findings, client, log
                )
            except Exception as exc:  # noqa: BLE001
                log(
                    f"[planner] {project['id']}: task {task_id}: "
                    f"review filter failed: {exc}"
                )
                decisions = None
            if decisions is not None:
                valid = [item for item in decisions if item.valid]
                data["review_filter"] = {
                    "decisions": [
                        {
                            "finding": item.finding,
                            "valid": item.valid,
                            "scope": item.scope,
                            "reason": item.reason,
                        }
                        for item in decisions
                    ],
                }
                if not valid:
                    _dismiss_review(
                        settings,
                        ledger,
                        project,
                        layout,
                        task_id,
                        data,
                        log,
                    )
                    return
                spec_findings = [
                    item for item in valid if item.scope == "spec"
                ]
                if spec_findings:
                    issue = "\n".join(
                        f"- {item.finding}: {item.reason}"
                        for item in spec_findings
                    )
                    try:
                        protocol.rewrite_task_spec(
                            settings,
                            ledger,
                            project,
                            layout,
                            tasks.get_task(layout, task_id) or task,
                            client,
                            issue,
                            log,
                        )
                    except Exception as exc:  # noqa: BLE001
                        log(
                            f"[planner] {project['id']}: task {task_id}: "
                            f"specification rewrite failed: {exc}"
                        )
                        data.pop("review_filter", None)
                    else:
                        filtered_feedback = [
                            f"{item.finding} — {item.reason}"
                            for item in valid
                        ] + [
                            "The planner rewrote the specification; "
                            "implement the new version."
                        ]
                if filtered_feedback is None:
                    filtered_feedback = [
                        f"{item.finding} — {item.reason}"
                        for item in valid
                    ]
    if kind in {"qa", "review"} or (kind == "spec" and spec_feedback):
        reworks = int(data.get("rework_count", 0))
        if reworks < settings.task_reworks:
            data["rework_count"] = reworks + 1
            if kind == "spec":
                data["feedback"] = list(
                    data.get("spec_feedback") or []
                ) or _feedback_from(data)
                data.pop("spec_feedback", None)
            else:
                data["feedback"] = filtered_feedback or _feedback_from(data)
            data["last_failure"] = failure
            data.pop("failure", None)
            tasks.update_task(
                layout,
                task_id,
                status="pending",
                started_at="",
                finished_at="",
                result=data,
            )
            log(
                f"[rework] {project['id']}: task {task_id} sent back "
                f"({kind}); rework {reworks + 1}/{settings.task_reworks}"
            )
            return
        if settings.task_arbiter and client is not None:
            from .arbiter import run_task_arbiter
            from .task_review import accept_task, await_acceptance

            arbitration = run_task_arbiter(
                settings, ledger, project, task, client, log
            )
            if arbitration.verdict == "accept":
                if settings.task_accept == "auto":
                    accept_task(
                        settings,
                        ledger,
                        project,
                        task,
                        actor="arbiter",
                        notes=arbitration.summary,
                    )
                else:
                    await_acceptance(
                        layout,
                        task,
                        "arbiter accepted; human acceptance required",
                    )
                return
            if arbitration.verdict == "criteria":
                data = dict(
                    (tasks.get_task(layout, task_id) or task).get("result")
                    or data
                )
                data["summary"] = (
                    str(data.get("summary") or "").strip()
                    + "; acceptance criteria need revision"
                ).strip("; ")
                data["failure"] = {
                    "kind": "criteria",
                    "message": arbitration.summary,
                    "retryable": False,
                }
                tasks.update_task(
                    layout, task_id, status="failed", result=data
                )
                _quarantine(
                    settings,
                    ledger,
                    project,
                    layout,
                    task_id,
                    data["failure"],
                    attempts,
                    log,
                )
                return
            if arbitration.verdict == "fix":
                data = dict(
                    (tasks.get_task(layout, task_id) or task).get("result")
                    or data
                )
                data["failure"] = {
                    "kind": "review",
                    "message": arbitration.summary
                    or "the arbiter confirmed the review rejection",
                    "retryable": False,
                }
                tasks.update_task(
                    layout, task_id, status="failed", result=data
                )
                failure = data["failure"]
    _quarantine(
        settings, ledger, project, layout, task_id, failure, attempts, log
    )


def _ensure_formal_spec(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task: dict[str, Any],
    client: ModelClient,
    log: Callable[[str], None],
) -> dict[str, Any]:
    """Give a free-text task a formal specification and dependency report."""

    current = str(task.get("spec") or "")
    if current.startswith("docs/program/specs/"):
        return task
    task_id = str(task["id"])
    requirements = [str(item) for item in task.get("requirements") or []]
    acceptance = [str(item) for item in task.get("acceptance") or []]
    intent = {
        "title": task.get("title") or task_id,
        "summary": (
            "; ".join(requirements + acceptance)
            or task.get("title")
            or task_id
        ),
        "repo_id": task.get("repo_id") or "",
        "depends_on": [
            str(item) for item in (task.get("depends_on") or [])
        ],
        "requirements": requirements,
        "acceptance": acceptance,
    }
    goal = str(task.get("plan_goal") or task.get("title") or task_id)
    spec = specs.write_task_spec(
        settings, layout, goal, "", intent, client, log=log
    )
    if spec.get("external_dependencies"):
        spec["external_dependencies"] = dependencies.investigate(
            layout, intent, spec, client, log
        )
    ref = specs.spec_path(task_id)
    write_text(
        layout.artifact(ref),
        specs.render_spec(
            spec,
            task_id,
            str(task.get("plan_id") or ""),
            intent["repo_id"],
            intent["depends_on"],
        ),
    )
    updated = tasks.update_task(
        layout,
        task_id,
        spec=ref,
        request=current,
        checks=list(spec.get("checks") or []),
        test_command=list(spec.get("test_command") or []),
        requirements=list(spec.get("requirements") or []),
        acceptance=list(spec.get("acceptance") or []),
        external_dependencies=list(
            spec.get("external_dependencies") or []
        ),
    )
    tasks.commit_control(layout, f"Spec {task_id}")
    ledger.append_event(
        str(project["id"]),
        "spec",
        status="completed",
        idempotency_key=(
            f"{project['id']}:spec:{task_id}:"
            f"r{tasks.attempt_number(task)}"
        ),
        artifact_refs=[ref],
        payload={
            "request": current,
            "requirements": list(spec.get("requirements") or []),
            "dependencies": [
                {
                    "name": item.get("name"),
                    "mode": item.get("mode"),
                }
                for item in (spec.get("external_dependencies") or [])
            ],
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[spec] {project['id']}: task {task_id}: formal specification "
        f"written ({ref})"
    )
    return updated


def _run_task(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    task: dict[str, Any],
    client: ModelClient | None,
    log: Callable[[str], None],
) -> bool:
    task_id = str(task["id"])
    policy = peak.project_policy(settings, layout.control)
    if peak.should_defer(policy, hours=settings.peak_hours):
        log(
            f"[daemon] {project['id']}: {peak.defer_message(hours=settings.peak_hours, tz_name=settings.timezone)}"
        )
        return False
    stored = dict(task.get("result") or {})
    stored.pop("retry_after", None)
    tasks.update_task(
        layout,
        task_id,
        status="running",
        started_at=_now(),
        result=stored,
    )
    log(f"[daemon] {project['id']}: starting task {task_id}")
    model = client or build_model_client(settings.home, log=log)
    if model is None:
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={
                "summary": "no model configured for the coding agent",
                "failure": _failure(
                    "external",
                    "no model configured",
                    retryable=False,
                ),
            },
        )
        log(f"[daemon] {project['id']}: task {task_id} has no model client")
        handle_failure(
            settings, ledger, project, layout, task_id, None, log
        )
        return True
    try:
        if settings.free_text_spec:
            task = _ensure_formal_spec(
                settings,
                ledger,
                project,
                layout,
                task,
                model,
                log,
            )
    except (specs.SpecError, dependencies.DependencyError) as exc:
        data = dict(task.get("result") or {})
        data["summary"] = f"specification blocked: {exc}"
        data["failure"] = _failure(
            "external", str(exc), retryable=False
        )
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result=data,
        )
        log(
            f"[spec] {project['id']}: task {task_id} blocked: {exc}"
        )
        handle_failure(
            settings, ledger, project, layout, task_id, model, log
        )
        try:
            tasks.commit_control(layout, f"Task {task_id}: result")
        except Exception:  # noqa: BLE001 - a commit must not stop the daemon
            pass
        return True
    try:
        result = CodingAgent(settings, ledger, model).run(
            project, task, log
        )
        spec_blocked = False
        if result.status == "done":
            stored = tasks.get_task(layout, task_id) or task
            issues = [
                item
                for item in (
                    (stored.get("result") or {}).get("spec_issues") or []
                )
                if isinstance(item, dict)
            ]
            if issues:
                spec_blocked = True
                _handle_spec_issues(
                    settings,
                    ledger,
                    project,
                    layout,
                    stored,
                    issues,
                    model,
                    log,
                )
        if (
            result.status == "done"
            and not spec_blocked
            and (settings.task_qa or settings.task_review)
        ):
            # The agent's own "done" is not the final state: QA and review
            # still have to run. Keep the task running so an interrupted
            # process is recovered instead of being accepted unchecked.
            tasks.update_task(layout, task_id, status="running")
            try:
                process_task_result(
                    settings, ledger, project, task, model, log
                )
            except Exception as exc:  # noqa: BLE001 - the pipeline must not crash
                stored = tasks.get_task(layout, task_id) or task
                tasks.update_task(
                    layout,
                    task_id,
                    status="failed",
                    result={
                        **dict(stored.get("result") or {}),
                        "summary": f"post-agent pipeline failed: {exc}",
                        "failure": _failure(
                            "external",
                            f"post-agent pipeline failed: {exc}",
                            retryable=False,
                        ),
                    },
                )
                log(
                    f"[task] {project['id']}: {task_id} "
                    f"post-agent pipeline crashed: {exc}"
                )
    except Exception as exc:  # noqa: BLE001 - one task must not kill the daemon
        trace = traceback.format_exc(limit=12)
        failure = _classify_crash(exc)
        failure["traceback"] = trace[-4000:]
        tasks.update_task(
            layout,
            task_id,
            status="failed",
            finished_at=_now(),
            result={
                "summary": f"agent crashed: {exc}",
                "failure": failure,
            },
        )
        log(
            f"[daemon] {project['id']}: task {task_id} "
            f"crashed: {exc}\n{trace}"
        )
    handle_failure(
        settings, ledger, project, layout, task_id, model, log
    )
    try:
        tasks.commit_control(layout, f"Task {task_id}: result")
    except Exception:  # noqa: BLE001 - a commit must not stop the daemon
        pass
    return True


def run_once(
    settings: Settings,
    ledger: Ledger,
    log: Callable[[str], None] = print,
    client: ModelClient | None = None,
) -> list[str]:
    """Run every project that has pending work. Returns processed project ids."""

    processed: list[str] = []
    seen: dict[str, str] = {}
    for project in ledger.list_projects():
        project_id = project["id"]
        workspace = str(Path(project["workspace"]).resolve())
        owner = seen.get(workspace)
        if owner is not None:
            log(
                f"[daemon] {project_id}: duplicate workspace of "
                f"{owner}; skipped"
            )
            continue
        seen[workspace] = project_id
        if project_is_done(ledger, project_id):
            continue
        layout = ProjectLayout.detect(project["workspace"])
        for task_id in accept_parked_green_tasks(
            settings, ledger, project, layout
        ):
            log(
                f"[daemon] {project_id}: auto-accepted {task_id} "
                "(green review)"
            )
        recovered = tasks.recover_running(layout)
        for task in recovered:
            log(
                f"[daemon] {project_id}: recovered interrupted task "
                f"{task['id']} ({task['status']})"
            )
        task = tasks.next_pending_task(layout)
        if task is None and tasks.waiting_pending(layout):
            continue
        if task is not None:
            if _run_task(
                settings, ledger, project, layout, task, client, log
            ):
                processed.append(project_id)
            continue
        if layout.metadata().get("mode") == "brownfield":
            # No pending task: idle. A blocked/retrying task is visible in
            # the project state instead of a log line on every cycle.
            continue
        if awaits_approval(ledger, project_id):
            log(f"[daemon] {project_id}: waiting for staging approval")
            continue
        workspace = Path(project["workspace"])
        if has_blocking_reconciliation(workspace):
            log(f"[daemon] {project_id}: waiting for a reconciliation decision")
            continue
        try:
            log(f"[daemon] {project_id}: running iteration")
            Orchestrator(settings, ledger).run(project_id)
            processed.append(project_id)
        except Exception as exc:  # noqa: BLE001 - one project must not kill the daemon
            log(f"[daemon] {project_id}: stopped: {exc}")
    return processed


def next_retry_wait(ledger: Ledger) -> float | None:
    """Seconds until the earliest pending retry, if any."""

    now = datetime.now(timezone.utc)
    moments: list[datetime] = []
    for project in ledger.list_projects():
        layout = ProjectLayout.detect(project["workspace"])
        moments.extend(tasks.retry_times(layout))
    future = [moment for moment in moments if moment > now]
    if not future:
        return None
    return max(1.0, min((min(future) - now).total_seconds(), 3600.0))


def run_daemon(
    settings: Settings,
    ledger: Ledger,
    interval: float = 5.0,
    once: bool = False,
    max_cycles: int | None = None,
    log: Callable[[str], None] = print,
    client: ModelClient | None = None,
) -> int:
    """Run the control-plane loop. Returns the number of cycles executed."""

    cycles = 0
    while True:
        if is_paused(settings.home):
            processed = []
            log("[daemon] paused")
        else:
            processed = run_once(settings, ledger, log, client)
        cycles += 1
        if once or (max_cycles is not None and cycles >= max_cycles):
            return cycles
        wait = interval
        if not processed:
            retry_wait = next_retry_wait(ledger)
            if retry_wait is not None:
                wait = retry_wait
            log(f"[daemon] idle; next poll in {wait:g}s")
        time.sleep(wait)
