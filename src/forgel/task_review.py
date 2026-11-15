"""Independent review and acceptance for coding tasks.

The reviewer gets a clean context: the task's explicit requirements, the diff
the agent committed, the QA verdict and the assumptions. It does not see the
agent's self-justification and it cannot modify the repository. A failed review
fails the task; a passing review leaves the task in ``review`` until a human
accepts it, unless the project explicitly opts into automatic acceptance.

Acceptance is a record, not a second implementation: it writes who accepted,
when and with what note into the task and the ledger.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
from .program_manifest import entries as manifest_entries
from .repo_tools import (
    RESEARCH_ACTIONS,
    RepoActionError,
    execute_repo_action,
)
from .task_qa import TaskQAResult, run_task_qa
from .tasks import get_task, update_task

MAX_DIFF_CHARS = 16_000
MAX_FILE_CHARS = 12_000
MAX_REVIEW_STEPS = 8
MAX_QA_CHARS = 2_000
REMOVAL_REASONS = {"removed", "replaced", "wrong"}
TEST_PATH = re.compile(
    r"(^|/)(tests?|spec|__tests__)/"
    r"|(^|/)test_[^/]+\.(py|js|ts|tsx|jsx|mjs)$"
    r"|_test\.(py|js|ts|tsx|jsx|mjs)$"
    r"|\.(test|spec)\.(js|ts|tsx|jsx|mjs)$"
)
TEST_FUNCTION = re.compile(
    r"^-\s*(async\s+)?def\s+test_\w+"
    r"|^-\s*(it|test)\s*\("
)


@dataclass(frozen=True)
class ReviewResult:
    status: str  # pass | fail | skipped | error
    summary: str
    report: str = ""
    requirements: list[dict[str, Any]] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)
    output: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


def _repo(layout: ProjectLayout, task: Mapping[str, Any]) -> tuple[str, Path]:
    repo_id = str(task.get("repo_id") or "")
    if not repo_id:
        from .program_manifest import entries

        repos = entries(layout)
        if len(repos) == 1:
            repo_id = str(repos[0]["id"])
    if not repo_id:
        return "", layout.root
    return repo_id, layout.repo_path(repo_id)


def _attributed(task: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Files and commits attributed to this task across attempts."""

    result = dict(task.get("result") or {})
    files = [
        str(item) for item in (result.get("files_changed") or [])
    ]
    git = result.get("git") if isinstance(result.get("git"), dict) else {}
    commits = [str(item) for item in (git.get("commits") or [])]
    legacy = str(git.get("commit") or "")
    if legacy and legacy not in commits:
        commits.append(legacy)
    return files, commits


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


def _attributed_diff(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    _repo_id, repo = _repo(layout, task)
    files, commits = _attributed(task)
    if not (repo / ".git").exists():
        return "The repository has no git history."
    if not commits:
        return (
            "No product commits were attributed to this task. The change may "
            "already exist in the repository; inspect the current files."
        )
    parts: list[str] = []
    for commit in commits:
        command = ["show", "--format=", commit]
        if files:
            command += ["--", *files]
        text = _git_output(repo, command).strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip() or "No product changes in those commits."


def _reference_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if path.name == "PLAN.md" and "### 7.15" in text:
        start = text.index("### 7.15")
        end = text.find("\n### 7.16", start)
        section = text[start : end if end >= 0 else start + 6_000]
        return _cap(section, MAX_FILE_CHARS)
    return _cap(text, MAX_FILE_CHARS)


def _current_files_text(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    _repo_id, repo = _repo(layout, task)
    files, _commits = _attributed(task)
    if not files:
        files = [
            name
            for name in ("README.md", "PLAN.md")
            if (repo / name).is_file()
        ]
    parts: list[str] = []
    for relative in files:
        path = (repo / relative).resolve()
        try:
            path.relative_to(repo.resolve())
        except ValueError:
            continue
        text = _reference_text(path)
        if text:
            parts.append(f"--- {relative} ---\n{text}")
    return "\n\n".join(parts) or "(no relevant files)"


def _commit_evidence(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    _repo_id, repo = _repo(layout, task)
    files, commits = _attributed(task)
    lines: list[str] = []
    for commit in commits:
        text = _git_output(
            repo, ["show", "-s", "--format=fuller", commit]
        ).strip()
        if text:
            lines.append(text)
    if not commits:
        for relative in files or ["README.md", "PLAN.md"]:
            text = _git_output(
                repo,
                ["log", "-1", "--format=fuller", "--", relative],
            ).strip()
            if text:
                lines.append(f"--- {relative} ---\n{text}")
    return "\n\n".join(lines) or "(no commit evidence)"


def task_diff(layout: ProjectLayout, task: Mapping[str, Any]) -> str:
    return _attributed_diff(layout, task)


def _git_output(
    repo: Path, args: list[str]
) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout if completed.returncode == 0 else ""


def detected_test_removals(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> list[str]:
    """Deleted test files and removed test functions in the committed diff."""

    _repo_id, repo = _repo(layout, task)
    if not (repo / ".git").exists():
        return []
    files, commits = _attributed(task)
    names = ""
    patch = ""
    if commits:
        for commit in commits:
            command = ["show", "--format=", "--name-status", commit]
            if files:
                command += ["--", *files]
            names += _git_output(repo, command)
            command = ["show", "--format=", commit]
            if files:
                command += ["--", *files]
            patch += _git_output(repo, command)
    else:
        # Tasks created before attribution existed.
        result = dict(task.get("result") or {})
        git = result.get("git") if isinstance(result.get("git"), dict) else {}
        base = str(git.get("base") or "")
        head = str(git.get("head") or "")
        if base and head and base != head:
            names = _git_output(
                repo, ["diff", "--name-status", f"{base}..{head}"]
            )
            patch = _git_output(repo, ["diff", f"{base}..{head}"])
        elif head:
            names = _git_output(
                repo, ["show", "--format=", "--name-status", head]
            )
            patch = _git_output(repo, ["show", "--format=", head])
        else:
            return []
    labels: list[str] = []
    for line in names.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("D"):
            path = parts[-1].strip()
            if TEST_PATH.search(path):
                labels.append(f"file:{path}")
    for line in patch.splitlines():
        if line.startswith("---"):
            continue
        if TEST_FUNCTION.match(line):
            labels.append(f"line:{line[1:].strip()[:100]}")
    return list(dict.fromkeys(labels))


def test_removals(task: Mapping[str, Any]) -> list[dict[str, str]]:
    result = dict(task.get("result") or {})
    removals: list[dict[str, str]] = []
    for item in result.get("test_removals") or []:
        if not isinstance(item, dict):
            continue
        test = str(item.get("test", "")).strip()
        reason = str(item.get("reason", "")).strip().lower()
        replacement = str(item.get("replacement", "")).strip()
        if test and reason in REMOVAL_REASONS:
            removals.append(
                {
                    "test": test,
                    "reason": reason,
                    "replacement": replacement,
                }
            )
    return removals


def _review_prompt(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    requirements = "\n".join(
        f"- {item}" for item in task.get("requirements", [])
    ) or "- none"
    acceptance = "\n".join(
        f"- {item}" for item in task.get("acceptance", [])
    ) or "- none"
    constraints = "\n".join(
        f"- {item}" for item in task.get("constraints", [])
    ) or "- none"
    assumptions = "\n".join(
        f"- {item}" for item in task.get("assumptions", [])
    ) or "- none"
    result = dict(task.get("result") or {})
    qa = result.get("qa") if isinstance(result.get("qa"), dict) else {}
    attributed_files, attributed_commits = _attributed(task)
    files = ", ".join(attributed_files) or "none"
    commits = ", ".join(
        f"`{item}`" for item in attributed_commits
    ) or "none"
    _repo_id, repo = _repo(layout, task)
    worktree = (
        _git_output(repo, ["status", "--porcelain"]).strip()
        or "clean"
    )
    check_lines = (
        "\n".join(
            f"- {item.get('criterion')}: {item.get('verdict')}"
            + (
                f" (exit {item.get('exit_code')})"
                if item.get("exit_code") is not None
                else " (review-only)"
            )
            for item in (qa.get("checks") or [])
        )
        or "- none"
    )
    detected = "\n".join(
        f"- {item}"
        for item in detected_test_removals(layout, task)
    ) or "- none"
    justifications = "\n".join(
        f"- {item['test']}: {item['reason']}"
        + (f" -> {item['replacement']}" if item["replacement"] else "")
        for item in test_removals(task)
    ) or "- none"
    return f"""TASK: {task.get('title', task.get('id'))}

Requirements:
{requirements}

Acceptance criteria:
{acceptance}

Constraints:
{constraints}

Assumptions recorded:
{assumptions}

Files attributed to this task: {files}
Commits attributed to this task: {commits}
Worktree: {worktree}
QA verdict: {qa.get('status', 'not run')} ({qa.get('runtime', 'n/a')})

Acceptance checks:
{check_lines}

Test removals detected in the attributed commits:
{detected}
Developer justifications:
{justifications}
Allowed reasons: "removed" (the scenario is gone), "replaced" (behavior
changed; the replacement must exist in the attributed change), "wrong"
(incorrect or duplicate test). An unjustified removal is a blocking defect.

Attributed change (only this task's commits):
{_cap(task_diff(layout, task), MAX_DIFF_CHARS)}

Current relevant files:
{_cap(_current_files_text(layout, task), MAX_FILE_CHARS * 2)}

Commit evidence:
{_cap(_commit_evidence(layout, task), MAX_FILE_CHARS)}
"""


SYSTEM_PROMPT = """You are an independent reviewer. You did not implement this
change and you must not modify the repository.

The repository is the source of truth. Judge the current state against the
requirements and acceptance criteria. The attributed files and commits are
this task's contribution; commits outside that list belong to other work and
are not part of this review. Do not fail a task because of extra commits or
pipeline bookkeeping.

If no product changes are attributed to the task, check whether the current
repository already satisfies the requirements. A previous signed commit is
valid; no new commit is required for an already-satisfied task.

You may inspect the repository before deciding. Reply with exactly one
action per turn:
{"action": "list_files", "path": ".", "repo_id": "main"}
{"action": "read_file", "path": "README.md", "repo_id": "main"}
When you have enough context, return the verdict object.

Report:
- a requirement that is not met,
- a feature that was not requested,
- a security problem, a committed secret, or a weakened test,
- a failing acceptance check or an unverified review-only criterion,
- a deleted test without one of the allowed justifications; "replaced"
  requires the named replacement to be present in the attributed change.

Every review-only criterion must appear in "requirements" with a verdict.

Do not rewrite the code and do not report stylistic preferences. Return
JSON only; do not emit tool-call markup, XML or provider-specific function
calls. Return exactly one JSON object:
{
  "verdict": "pass" | "fail",
  "summary": "one paragraph",
  "requirements": [
    {"requirement": "...", "verdict": "pass" | "fail", "note": "..."}
  ],
  "blocking": ["blocking defect, if any"]
}

A pass with a non-empty "blocking" list is a fail.
"""


def _parse_review(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("the reviewer did not return JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("the review must be a JSON object")
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in {"pass", "fail"}:
        raise ValueError("the review verdict must be pass or fail")
    blocking = [
        str(item).strip()
        for item in data.get("blocking", [])
        if str(item).strip()
    ]
    if verdict == "pass" and blocking:
        verdict = "fail"
    requirements = data.get("requirements", [])
    if not isinstance(requirements, list):
        requirements = []
    return {
        "verdict": verdict,
        "summary": str(data.get("summary", "")).strip(),
        "requirements": [
            {
                "requirement": str(item.get("requirement", "")).strip(),
                "verdict": str(item.get("verdict", "")).strip().lower(),
                "note": str(item.get("note", "")).strip(),
            }
            for item in requirements
            if isinstance(item, dict)
        ],
        "blocking": blocking,
    }


def _record_review(
    ledger: Ledger,
    layout: ProjectLayout,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    result: ReviewResult,
    log: Callable[[str], None],
) -> ReviewResult:
    task_id = str(task["id"])
    path = layout.artifact(
        f"docs/program/agent/{task_id}.review.md"
    )
    report_ref = str(path.relative_to(layout.root))
    requirement_lines = (
        "\n".join(
            f"- {item['requirement']}: {item['verdict']}"
            + (f" — {item['note']}" if item["note"] else "")
            for item in result.requirements
        )
        or "- none"
    )
    write_text(
        path,
        f"""# Task Review: {task.get('title', task_id)}

- Task: `{task_id}`
- Project: `{project['id']}`
- Verdict: **{result.status.upper()}**
- Finished: {_now()}

## Summary

{result.summary or '—'}

## Requirements

{requirement_lines}

## Blocking

{chr(10).join(f'- {item}' for item in result.blocking) or '- none'}

## Test Removals

{chr(10).join(f'- {item}' for item in detected_test_removals(layout, task)) or '- none'}

{chr(10).join(f'- {item["test"]}: {item["reason"]}' + (f" -> {item["replacement"]}" if item["replacement"] else "") for item in test_removals(task)) or ''}
""",
    )
    stored = get_task(layout, task_id) or task
    data = dict(stored.get("result") or {})
    data["review"] = {
        "status": result.status,
        "summary": result.summary,
        "requirements": result.requirements,
        "blocking": result.blocking,
        "report": report_ref,
    }
    status = str(stored.get("status") or "done")
    if result.status == "fail":
        status = "failed"
        summary = str(data.get("summary") or "").strip()
        data["summary"] = (
            (summary + "; " if summary else "")
            + "task review failed"
        )
        data["failure"] = {
            "kind": "review",
            "message": result.summary or "task review failed",
            "retryable": False,
        }
    elif result.status == "error":
        data["failure"] = {
            "kind": "external",
            "message": result.summary,
            "retryable": False,
        }
    update_task(layout, task_id, status=status, result=data)
    ledger.append_event(
        str(project["id"]),
        "task_review",
        status={
            "pass": "completed",
            "fail": "failed",
            "skipped": "skipped",
            "error": "error",
        }[result.status],
        idempotency_key=(
            f"{project['id']}:task_review:{task_id}:{result.status}"
        ),
        artifact_refs=[report_ref],
        payload={
            "task": task_id,
            "status": result.status,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(f"[review] {project['id']}: task {task_id}: {result.status}")
    return ReviewResult(
        status=result.status,
        summary=result.summary,
        report=report_ref,
        requirements=result.requirements,
        blocking=result.blocking,
        output=result.output,
    )


def run_task_review(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> ReviewResult:
    """Review a committed task from a clean context."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    task = get_task(layout, str(task["id"])) or task
    log(f"[review] {project['id']}: task {task['id']}: running")
    removals = detected_test_removals(layout, task)
    if removals and not test_removals(task):
        return _record_review(
            ledger,
            layout,
            project,
            task,
            ReviewResult(
                status="fail",
                summary=(
                    "Tests were deleted without a justification."
                ),
                blocking=[
                    f"Unjustified test removal: {item}"
                    for item in removals
                ],
            ),
            log,
        )
    if client is None:
        return _record_review(
            ledger,
            layout,
            project,
            task,
            ReviewResult(
                status="error",
                summary="No model client is configured for the reviewer.",
            ),
            log,
        )
    messages = [
        ModelMessage("system", SYSTEM_PROMPT),
        ModelMessage("user", _review_prompt(layout, task)),
    ]
    raw = ""
    parsed: dict[str, Any] | None = None
    answer_retries = 0
    for step in range(MAX_REVIEW_STEPS + 3):
        try:
            raw = client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError as exc:
            return _record_review(
                ledger,
                layout,
                project,
                task,
                ReviewResult(
                    status="error",
                    summary=f"Reviewer model call failed: {exc}",
                ),
                log,
            )
        data = _json_object(raw)
        action = str(data.get("action", "")) if data else ""
        if action not in RESEARCH_ACTIONS:
            try:
                parsed = _parse_review(raw)
                break
            except (ValueError, json.JSONDecodeError) as exc:
                if answer_retries < 2:
                    messages.append(
                        ModelMessage("assistant", raw.strip())
                    )
                    messages.append(
                        ModelMessage(
                            "user",
                            "Return exactly one JSON verdict object with "
                            "verdict, summary, requirements and blocking. "
                            "Do not use tool-call markup, XML, "
                            "provider-specific function calls or prose.",
                        )
                    )
                    answer_retries += 1
                    continue
                return _record_review(
                    ledger,
                    layout,
                    project,
                    task,
                    ReviewResult(
                        status="error",
                        summary=(
                            "Reviewer returned an unusable answer: "
                            f"{exc}"
                        ),
                        output=_cap(raw, MAX_QA_CHARS),
                    ),
                    log,
                )
        if step == MAX_REVIEW_STEPS:
            return _record_review(
                ledger,
                layout,
                project,
                task,
                ReviewResult(
                    status="error",
                    summary="the reviewer exceeded the inspection limit",
                ),
                log,
            )
        args = dict(data.get("action_args") or {})
        for key in ("path", "repo_id"):
            if key in data and key not in args:
                args[key] = data[key]
        research = {"action": action, **args}
        try:
            observation = execute_repo_action(
                layout, manifest_entries(layout), research
            )
        except RepoActionError as exc:
            observation = f"error: {exc}"
        messages.append(ModelMessage("assistant", raw.strip()))
        messages.append(
            ModelMessage(
                "user",
                "Observation:\n"
                + _cap(observation, 6_000)
                + "\n\nReturn another action or the final verdict JSON.",
            )
        )
    if parsed is None:
        return _record_review(
            ledger,
            layout,
            project,
            task,
            ReviewResult(
                status="error",
                summary="the reviewer did not return a verdict",
            ),
            log,
        )
    return _record_review(
        ledger,
        layout,
        project,
        task,
        ReviewResult(
            status=parsed["verdict"],
            summary=parsed["summary"],
            requirements=parsed["requirements"],
            blocking=parsed["blocking"],
        ),
        log,
    )


def _set_acceptance(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    status: str,
    actor: str,
    notes: str,
) -> dict[str, Any]:
    layout = ProjectLayout.detect(str(project["workspace"]))
    task = get_task(layout, str(task["id"])) or task
    data = dict(task.get("result") or {})
    data["acceptance"] = {
        "status": status,
        "actor": actor,
        "at": _now(),
        "notes": notes.strip(),
    }
    if status == "rejected":
        summary = str(data.get("summary") or "").strip()
        data["summary"] = (
            (summary + "; " if summary else "")
            + "rejected"
            + (f": {notes.strip()}" if notes.strip() else "")
        )
    updated = update_task(
        layout,
        str(task["id"]),
        status="done" if status == "accepted" else "failed",
        result=data,
    )
    ledger.append_event(
        str(project["id"]),
        "task_accept" if status == "accepted" else "task_reject",
        status="completed",
        idempotency_key=(
            f"{project['id']}:accept:{task['id']}:{status}:{actor}"
        ),
        artifact_refs=[],
        payload={
            "task": task["id"],
            "status": status,
            "actor": actor,
            "notes": notes.strip(),
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    return updated


def accept_task(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    actor: str = "owner",
    notes: str = "",
) -> dict[str, Any]:
    return _set_acceptance(
        settings, ledger, project, task, "accepted", actor, notes
    )


def reject_task(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    actor: str = "owner",
    notes: str = "",
) -> dict[str, Any]:
    return _set_acceptance(
        settings, ledger, project, task, "rejected", actor, notes
    )


def await_acceptance(
    layout: ProjectLayout,
    task: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    data = dict(task.get("result") or {})
    data["acceptance"] = {
        "status": "pending",
        "reason": reason,
        "at": _now(),
    }
    return update_task(
        layout, str(task["id"]), status="review", result=data
    )


def process_task_result(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> None:
    """Run the post-agent pipeline: QA, review, acceptance."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    task = get_task(layout, str(task["id"])) or task
    if not (settings.task_qa or settings.task_review):
        return
    qa: TaskQAResult | None = None
    if settings.task_qa:
        qa = run_task_qa(
            settings, ledger, project, task, log
        )
        task = get_task(layout, str(task["id"])) or task
        if qa.status == "fail":
            return
    if settings.task_review:
        review = run_task_review(
            settings, ledger, project, task, client, log
        )
        task = get_task(layout, str(task["id"])) or task
        if review.status == "fail":
            return
    else:
        review = ReviewResult(status="skipped", summary="review disabled")
    result = dict(task.get("result") or {})
    review_status = str(
        (result.get("review") or {}).get("status", review.status)
    )
    review_required = bool(qa.review_required) if qa is not None else False
    if (
        settings.task_accept == "auto"
        and review_status not in {"error", "fail"}
        and not review_required
    ):
        accept_task(
            settings, ledger, project, task, actor="auto", notes=""
        )
        return
    reason = "review passed; acceptance required"
    if review_required:
        reason = "acceptance checks require review"
    elif review_status == "error":
        reason = "the reviewer could not produce a verdict"
    elif review_status == "skipped":
        reason = "review is disabled; acceptance required"
    await_acceptance(layout, task, reason)
