"""Independent review and acceptance for coding tasks.

The reviewer gets a clean context: the task's explicit requirements, the diff
the agent committed, the QA verdict and the assumptions. It does not see the
agent's self-justification and it cannot modify the repository. A failed review
fails the task; a passing review is accepted automatically unless the project
opts into human acceptance.

Acceptance is a record, not a second implementation: it writes who accepted,
when and with what note into the task and the ledger.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .artifacts import write_text
from . import contract, git_ops
from .config import Settings
from .instructions import instruction_context
from .layout import ProjectLayout
from .ledger import Ledger
from .model_output import json_objects
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .program_manifest import entries as manifest_entries
from .project_config import ConfigError, load_project_config
from .repo_tools import (
    RESEARCH_ACTIONS,
    RepoActionError,
    execute_repo_action,
)
from .session_context import budget_for
from .task_qa import TaskQAResult, run_task_qa
from .tasks import (
    attempt_number,
    commit_control,
    get_task,
    list_tasks,
    update_task,
)

MAX_DIFF_CHARS = 16_000
MAX_FILE_CHARS = 12_000
MAX_QA_CHARS = 2_000
MAX_REVIEW_RETRIES = 10
REMOVAL_REASONS = {"removed", "replaced", "wrong"}
PUSH_RETRY_SECONDS = 60
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
    return (
        text[:limit]
        + f"\n... [truncated, {len(text)} chars; read the full file "
        "with read_file]"
    )


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
    return _cap(text, MAX_FILE_CHARS)


def _current_files_text(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> str:
    _repo_id, repo = _repo(layout, task)
    files, _commits = _attributed(task)
    if not files:
        files = [
            name for name in ("README.md",) if (repo / name).is_file()
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
        for relative in files or ["README.md"]:
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


def _git_ok(repo: Path, args: list[str]) -> bool:
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
        return False
    return completed.returncode == 0


def _test_still_exists(repo: Path, label: str) -> bool:
    """True when the removed test is present at HEAD (for example restored)."""

    kind, _, value = label.partition(":")
    if kind == "file":
        path = value.strip()
        return bool(path) and (
            (repo / path).exists()
            or _git_ok(repo, ["cat-file", "-e", f"HEAD:{path}"])
        )
    line = value.strip()
    match = re.search(r"def\s+(test_\w+)", line)
    if match:
        pattern = f"def {match.group(1)}"
    else:
        match = re.search(
            r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]", line
        )
        if not match:
            return False
        pattern = match.group(1)
    return _git_ok(
        repo, ["grep", "-q", "-F", "-e", pattern, "HEAD", "--", "."]
    )


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
    return [
        label
        for label in dict.fromkeys(labels)
        if not _test_still_exists(repo, label)
    ]


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
    spec_ref = str(task.get("spec") or "").strip()
    spec_text = ""
    if spec_ref:
        try:
            spec_text = layout.artifact(spec_ref).read_text(
                encoding="utf-8"
            )
        except OSError:
            spec_text = ""
    if spec_text:
        requirements = "- see the task specification below"
        acceptance = "- see the task specification below"
        constraints = "- see the task specification below"
        assumptions = "- see the task specification below"
    spec_section = (
        f"\nTask specification (`{spec_ref}`):\n{spec_text}\n"
        if spec_text
        else ""
    )
    result = dict(task.get("result") or {})
    qa = result.get("qa") if isinstance(result.get("qa"), dict) else {}
    attributed_files, attributed_commits = _attributed(task)
    files = ", ".join(attributed_files) or "none"
    commits = ", ".join(
        f"`{item}`" for item in attributed_commits
    ) or "none"
    _repo_id, repo = _repo(layout, task)
    instructions = instruction_context(
        layout, [_repo_id] if _repo_id else None
    )
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
    return f"""Project and repository instructions:
{instructions or "- none"}

TASK: {task.get('title', task.get('id'))}
{contract.digest(layout, task)}
{spec_section}
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

Scope of responsibility:
- Follow the project and repository instructions in the prompt. Repository
  rules are more specific and take precedence on conflict. Write the review
  summary and requirement notes in the artifact language they require.
- The task specification fixes the implementation contract: which external
  interfaces the code uses, which libraries it depends on, and the interfaces
  it must expose. Do not re-derive, replace or second-guess that contract; a
  mismatch is reported only against the written requirement.
- Deterministic checks (the environment gate, acceptance commands, contract
  tests) are QA's responsibility. Treat their verdict as authoritative; do not
  reproduce them with your own model of the interface.
- Judge the attributed diff on requirement compliance and code quality:
  logical errors, architectural problems, security issues, and weakened or
  deleted tests without an allowed justification. Report a requirement that
  is not met and a feature that was not requested.
- A finding that asks for a different implementation, a simpler path or a
  style change is not a requirement. A change to the specification needs a
  concrete, verifiable defect; the specification is valid by default because
  it was written and independently accepted.
- For every external dependency recorded in the specification, check the
  diff: a `direct` dependency must use the real local or test interface; a
  `stub` must match the recorded evidence and documentation. A stub that
  contradicts the evidence is blocking.
- You do not define the process: the stages, gates, rework policy and
  acceptance rules are fixed by the runtime; follow them.
- Do not add product requirements and do not report pure stylistic
  preferences.

Report:
- a requirement that is not met,
- a feature that was not requested,
- a logical error, an architectural problem, or another quality defect in
  the diff,
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
    parsed_requirements = [
        {
            "requirement": str(item.get("requirement", "")).strip(),
            "verdict": str(item.get("verdict", "")).strip().lower(),
            "note": str(item.get("note", "")).strip(),
        }
        for item in requirements
        if isinstance(item, dict)
        and str(item.get("requirement", "")).strip()
    ]
    return {
        "verdict": verdict,
        "summary": str(data.get("summary", "")).strip(),
        "requirements": parsed_requirements,
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
    attempt = attempt_number(task)
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
            f"{project['id']}:task_review:{task_id}:"
            f"{result.status}:r{attempt}"
        ),
        artifact_refs=[report_ref],
        payload={
            "task": task_id,
            "status": result.status,
            "rework": attempt,
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


def _review_window(
    settings: Settings, layout: ProjectLayout
) -> int:
    try:
        config = load_project_config(layout.control)
    except ConfigError:
        return settings.context_window
    if config is None:
        return settings.context_window
    return config.models.context_window


def _expected_acceptance(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> int:
    spec_ref = str(task.get("spec") or "").strip()
    if spec_ref:
        try:
            text = layout.artifact(spec_ref).read_text(encoding="utf-8")
        except OSError:
            text = ""
        if "## Acceptance" in text:
            section = text.split("## Acceptance", 1)[1].split(
                "\n## ", 1
            )[0]
            return sum(
                1
                for line in section.splitlines()
                if line.strip().startswith("- ")
            )
    return len(task.get("acceptance") or [])


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
    coverage_retries = 0
    model = project_model_name(layout.control)
    budget = budget_for(_review_window(settings, layout))
    while True:
        if budget.usage(messages, model) >= budget.usable:
            return _record_review(
                ledger,
                layout,
                project,
                task,
                ReviewResult(
                    status="error",
                    summary=(
                        "the reviewer context window is exhausted"
                    ),
                ),
                log,
            )
        try:
            raw = client.complete(messages, model=model)
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
        if observations:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observations:\n"
                    + "\n\n".join(
                        _cap(item, 6_000) for item in observations
                    )
                    + "\n\nReturn another action or the final verdict "
                    "JSON.",
                )
            )
        if finals:
            try:
                parsed = _parse_review(json.dumps(finals[-1]))
            except (ValueError, json.JSONDecodeError) as exc:
                if answer_retries < MAX_REVIEW_RETRIES:
                    if not observations:
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
            expected = _expected_acceptance(layout, task)
            if (
                expected
                and len(parsed["requirements"]) < expected
                and coverage_retries < MAX_REVIEW_RETRIES
            ):
                coverage_retries += 1
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "The verdict must cover every acceptance criterion: "
                        f"{expected} criteria, "
                        f"{len(parsed['requirements'])} covered. Return one "
                        "requirement entry per criterion, using the criterion "
                        "text as the requirement, and keep the verdict.",
                    )
                )
                continue
            break
        if not actions:
            if answer_retries < MAX_REVIEW_RETRIES:
                messages.append(ModelMessage("assistant", raw.strip()))
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
                    summary="the reviewer returned no usable JSON",
                ),
                log,
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
    expected = _expected_acceptance(layout, task)
    if expected and len(parsed["requirements"]) < expected:
        return _record_review(
            ledger,
            layout,
            project,
            task,
            ReviewResult(
                status="error",
                summary=(
                    "the review did not cover every acceptance "
                    f"criterion ({len(parsed['requirements'])}/{expected}); "
                    f"reviewer verdict: {parsed['verdict']}"
                ),
                output=_cap(raw, MAX_QA_CHARS),
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
    attempt = attempt_number(task)
    ledger.append_event(
        str(project["id"]),
        "task_accept" if status == "accepted" else "task_reject",
        status="completed",
        idempotency_key=(
            f"{project['id']}:accept:{task['id']}:{status}:{actor}:"
            f"r{attempt}"
        ),
        artifact_refs=[],
        payload={
            "task": task["id"],
            "status": status,
            "actor": actor,
            "notes": notes.strip(),
            "rework": attempt,
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
    updated = _set_acceptance(
        settings, ledger, project, task, "accepted", actor, notes
    )
    _push_accepted(settings, ledger, project, updated)
    return updated


def _push_accepted(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task: Mapping[str, Any],
) -> None:
    """Push the accepted task's branch and the control repository."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    task_id = str(task["id"])
    repo_id, repo = _repo(layout, task)
    previous = dict((task.get("result") or {}).get("push") or {})
    try:
        push_attempt = int(previous.get("attempts") or 0) + 1
    except (TypeError, ValueError):
        push_attempt = 1

    def push_one(path: Path) -> dict[str, str]:
        if not (path / ".git").exists():
            return {"status": "skipped", "detail": "no git history"}
        remote = git_ops.origin_url(path)
        if not remote:
            return {"status": "skipped", "detail": "no remote"}
        try:
            branch = git_ops.current_branch(path)
        except git_ops.GitOperationError as exc:
            return {
                "status": "failed",
                "detail": f"cannot determine the branch: {exc}",
            }
        token: str | None = None
        if git_ops.is_https(remote):
            try:
                from .providers.github_auth import (
                    GithubAuth,
                    GithubAuthError,
                )

                token = GithubAuth(settings.home).resolve("auto").token
            except GithubAuthError:
                token = None
        try:
            git_ops.push(path, branch, token)
        except git_ops.GitOperationError as exc:
            return {"status": "failed", "detail": str(exc)}
        return {"status": "pushed", "detail": "", "branch": branch}

    own_dirty: list[str] = []
    if (repo / ".git").exists():
        task_files = [
            str(item)
            for item in ((task.get("result") or {}).get("files_changed") or [])
        ]

        def _owned(path: str) -> bool:
            for item in task_files:
                if item.endswith("/") and path.startswith(item):
                    return True
                if path == item:
                    return True
            return False

        own_dirty = [
            item for item in git_ops.status_paths(repo) if _owned(item)
        ]
    if own_dirty:
        pushed = {
            "status": "failed",
            "detail": (
                "the task's own files are uncommitted: "
                + ", ".join(own_dirty)
            ),
            "branch": "",
        }
    else:
        pushed = push_one(repo)
    control = layout.root if layout.is_linked else layout.control
    control_result: dict[str, str] | None = None
    if control.resolve() != repo.resolve():
        try:
            commit_control(layout, f"Accept task {task_id}")
        except Exception:  # noqa: BLE001 - a commit must not undo acceptance
            pass
        control_result = push_one(control)
    data = dict(task.get("result") or {})
    status = pushed.get("status", "failed")
    next_at = ""
    if status == "failed":
        next_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=PUSH_RETRY_SECONDS)
        ).isoformat(timespec="seconds")
    data["push"] = {
        "status": status,
        "repo": repo_id,
        "branch": pushed.get("branch", ""),
        "detail": pushed.get("detail", ""),
        "control": control_result,
        "attempts": push_attempt,
        "next_at": next_at,
    }
    update_task(layout, task_id, result=data)
    ledger.append_event(
        str(project["id"]),
        "task_push",
        status=status,
        idempotency_key=(
            f"{project['id']}:task_push:{task_id}:"
            f"r{attempt_number(task)}:p{push_attempt}"
        ),
        artifact_refs=[],
        payload={
            "task": task_id,
            "repo": repo_id,
            "branch": pushed.get("branch", ""),
            "detail": pushed.get("detail", ""),
            "control": control_result,
        },
        generation=ledger.current_generation(str(project["id"])),
    )


def retry_failed_pushes(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
) -> list[str]:
    """Retry publication of accepted tasks whose push failed and is due."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pushed: list[str] = []
    for task in list_tasks(layout):
        if str(task.get("status") or "") != "done":
            continue
        result = task.get("result") or {}
        acceptance = result.get("acceptance") or {}
        if str(acceptance.get("status") or "") != "accepted":
            continue
        push = result.get("push") or {}
        if str(push.get("status") or "") != "failed":
            continue
        next_at = str(push.get("next_at") or "")
        if next_at and next_at > now:
            continue
        task_id = str(task["id"])
        fresh = get_task(layout, task_id) or task
        _push_accepted(settings, ledger, project, fresh)
        updated = get_task(layout, task_id) or fresh
        current = (updated.get("result") or {}).get("push") or {}
        if str(current.get("status") or "") == "pushed":
            pushed.append(task_id)
    return pushed


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
    if settings.task_accept == "auto" and review_status == "pass":
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


def rerun_review(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    task_id: str,
    client: ModelClient | None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Re-run QA and review for a task awaiting a decision."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    task = get_task(layout, str(task_id))
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if task.get("status") != "review":
        raise ValueError(
            "only tasks awaiting a review decision can be re-reviewed "
            f"(status: {task.get('status')})"
        )
    if client is None:
        raise ValueError("no model configured for the reviewer")
    log(
        f"[review] {project['id']}: task {task_id}: re-running QA and review"
    )
    process_task_result(
        settings, ledger, project, task, client, log
    )
    stored = get_task(layout, str(task_id)) or task
    if stored.get("status") == "failed":
        from .daemon import handle_failure

        handle_failure(
            settings,
            ledger,
            dict(project),
            layout,
            str(task_id),
            client,
            log,
        )
        stored = get_task(layout, str(task_id)) or stored
    return stored


def accept_parked_green_tasks(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    layout: ProjectLayout,
) -> list[str]:
    """Accept tasks that were parked for a human while the policy was human.

    Switching ``FORGEL_TASK_ACCEPT`` to ``auto`` must take effect without a
    manual accept for every task already waiting. A task stays parked only
    when the reviewer errored: without a verdict there is nothing to accept.
    """

    if settings.task_accept != "auto":
        return []
    accepted: list[str] = []
    for task in list_tasks(layout):
        if task.get("status") != "review":
            continue
        result = dict(task.get("result") or {})
        acceptance = dict(result.get("acceptance") or {})
        if acceptance.get("status") != "pending":
            continue
        review = dict(result.get("review") or {})
        if str(review.get("status") or "") != "pass":
            continue
        accept_task(
            settings,
            ledger,
            project,
            task,
            actor="auto",
            notes="acceptance policy is auto",
        )
        accepted.append(str(task["id"]))
    return accepted
