"""Independent QA for a coding task.

The coding agent runs its own final test; this pass runs the project's
environment contract again, plus the task's explicit acceptance checks and its
test command, from a clean process after the agent has committed.

Acceptance checks are ordinary commands stored in the task record, outside the
agent's write scope: the agent cannot weaken them from the repository. A check
whose criterion cannot be automated is marked ``verification: review`` and is
verified by the independent reviewer from the evidence in the task report; it
is not a separate human evidence gate.

The verdict is authoritative: a green agent run with a red QA becomes a failed
task, with the QA report attached. When there is nothing to run, the verdict is
``skipped`` rather than a false pass.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from . import capabilities
from .artifacts import write_text
from .check_commands import check_problems
from .config import Settings
from .environment import (
    Environment,
    command_argv,
    load_environment,
    mount_env_name,
)
from .git_ops import status_paths
from .integration import integration_problem, integration_warning
from .layout import ProjectLayout
from .ledger import Ledger
from .proc import merge_output
from .program_manifest import entries
from .sandbox import DockerSandbox, SandboxError, docker_runner
from .tasks import attempt_number, get_task, update_task

MAX_OUTPUT = 20_000
MAX_CHECK_OUTPUT = 4_000


@dataclass(frozen=True)
class TaskQAResult:
    status: str  # pass | fail | review | skipped
    runtime: str
    report: str = ""
    commands: list[dict[str, Any]] = field(default_factory=list)
    output: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)
    review_required: bool = False
    failure_kind: str = ""  # code | spec | environment | infrastructure


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cap(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


def _tail(text: str, limit: int = MAX_CHECK_OUTPUT) -> str:
    """The end of a command output, where the traceback and the error are."""

    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return "… [truncated]\n" + value[-limit:]


def _skipped_e2e(
    check: dict[str, Any], message: str
) -> dict[str, Any]:
    return {
        "criterion": check.get("criterion") or "environment e2e",
        "command": check.get("command") or "",
        "exit_code": None,
        "verdict": "skipped",
        "scope": "e2e",
        "repo": check.get("repo") or "",
        "workdir": check.get("workdir") or "",
        "output": message,
        "failure": "",
    }


DOC_SUFFIXES = {".md", ".rst", ".txt"}


def _documentation_only(task: dict[str, Any]) -> bool:
    files = [
        str(item)
        for item in ((task.get("result") or {}).get("files_changed") or [])
    ]
    if not files:
        return False
    return all(
        item.endswith(tuple(DOC_SUFFIXES)) or item.startswith("docs/")
        for item in files
    )


def _task_repo_id(
    layout: ProjectLayout, task: dict[str, Any]
) -> str:
    repo_id = str(task.get("repo_id") or "")
    if repo_id:
        return repo_id
    from .program_manifest import entries

    repos = entries(layout)
    if len(repos) == 1:
        return str(repos[0]["id"])
    return ""


def _qa_checks(
    layout: ProjectLayout,
    environment: Environment | None,
    task: dict[str, Any],
    repo_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Executable checks with an explicit scope and working directory.

    Environment commands run where the environment contract lives. Task
    checks and the task test command always run in the task repository; that
    is the invariant the QA gate depends on.
    """

    executable: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    task_root = layout.repo_path(repo_id) if repo_id else layout.root
    env_root = environment.workdir(layout) if environment is not None else None
    env_repo = (
        environment.repository(layout) if environment is not None else ""
    )

    def add(
        label: str,
        command: str,
        scope: str,
        workdir: Path,
        repo: str,
    ) -> None:
        key = (command, str(workdir))
        if key in seen:
            return
        seen.add(key)
        executable.append(
            {
                "criterion": label,
                "command": command,
                "verification": "command",
                "scope": scope,
                "repo": repo,
                "workdir": str(workdir),
            }
        )

    if environment is not None:
        root = env_root or layout.root
        for command in environment.test:
            add("environment test", command, "environment", root, env_repo)
        for command in environment.e2e:
            add("environment e2e", command, "e2e", root, env_repo)
    for check in task.get("checks", []):
        criterion = str(check.get("criterion", "")).strip() or "check"
        if check.get("verification") == "review":
            review.append(
                {"criterion": criterion, "verification": "review"}
            )
            continue
        add(
            criterion,
            shlex.join(check.get("command", [])),
            "task",
            task_root,
            repo_id,
        )
    test_command = [str(item) for item in task.get("test_command", [])]
    if test_command:
        add(
            "task test command",
            shlex.join(test_command),
            "task",
            task_root,
            repo_id,
        )
    return executable, review


def _workdir(
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
) -> Path:
    """Fallback directory for a check that carries no explicit workdir."""

    if repo_id:
        return layout.repo_path(repo_id)
    if environment is not None:
        return environment.workdir(layout)
    return layout.root


SAFE_ENV_KEYS = {
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TERM",
    "SHELL",
    "SYSTEMROOT",
    "COMSPEC",
}


def _run_local(
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
    checks: Sequence[dict[str, Any]],
    timeout: float = 900.0,
) -> list[tuple[dict[str, Any], int, str]]:
    fallback = _workdir(layout, environment, repo_id)
    env = {
        key: os.environ[key]
        for key in SAFE_ENV_KEYS
        if key in os.environ
    }
    env.update(environment.env_map if environment is not None else {})
    if environment is not None:
        for mount in environment.mounts:
            env[mount_env_name(mount)] = str(layout.repo_path(mount))
    results: list[tuple[dict[str, Any], int, str]] = []
    for check in checks:
        command = check["command"]
        workdir = Path(str(check.get("workdir") or fallback))
        output = ""
        try:
            argv = command_argv(command)
        except Exception as exc:  # noqa: BLE001 - reported as a failure
            results.append((check, 2, f"invalid command: {exc}"))
            continue
        output += f"$ {command}\n# cwd: {workdir}\n"
        try:
            completed = subprocess.run(
                argv,
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=max(60.0, float(timeout)),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            partial = merge_output(exc.stdout, exc.stderr)
            results.append(
                (check, 124, output + f"timed out after 600s\n{partial}")
            )
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            results.append(
                (check, 127, output + f"cannot run command: {exc}")
            )
            continue
        results.append(
            (
                check,
                completed.returncode,
                output + completed.stdout + completed.stderr,
            )
        )
    return results


def _repo_for_workdir(layout: ProjectLayout, workdir: Path) -> str:
    """The repository a working directory belongs to, or ``""``."""

    target = workdir.resolve()
    for entry in entries(layout):
        repo_id = str(entry["id"])
        if layout.repo_path(repo_id).resolve() == target:
            return repo_id
    return ""


def _run_sandbox(
    settings: Settings,
    project: dict[str, Any],
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
    checks: Sequence[dict[str, Any]],
) -> tuple[list[tuple[dict[str, Any], int, str]], str]:
    sandbox = DockerSandbox(settings)
    available, detail = sandbox.available()
    if not available:
        raise SandboxError(f"sandbox unavailable: {detail}")
    fallback = _workdir(layout, environment, repo_id)
    groups: dict[Path, list[dict[str, Any]]] = {}
    for check in checks:
        workdir = Path(str(check.get("workdir") or fallback))
        groups.setdefault(workdir, []).append(check)
    results: list[tuple[dict[str, Any], int, str]] = []
    labels: list[str] = []
    for workdir, group in groups.items():
        group_repo = _repo_for_workdir(layout, workdir)
        if not group_repo:
            # The sandbox mounts one repository. Do not run a project-level
            # check in the task repository: that would produce a false result.
            for check in group:
                scope = str(check.get("scope") or "task")
                results.append(
                    (
                        {
                            **check,
                            "failure": (
                                "spec" if scope == "task" else "environment"
                            ),
                        },
                        2,
                        f"$ {check['command']}\n# cwd: {workdir}\n"
                        "project-level check cannot run in the sandbox; "
                        "set environment.repo or run local QA\n",
                    )
                )
            continue
        session = sandbox.session(
            layout, environment, str(project["id"]), group_repo
        )
        labels.append(session.image)
        with session:
            for check in group:
                argv = shlex.split(check["command"])
                output = f"$ {check['command']}\n# cwd: {workdir}\n"
                if not argv:
                    results.append((check, 2, output + "empty command\n"))
                    continue
                try:
                    code, text = session.run(
                        argv,
                        timeout=max(
                            60.0,
                            float(settings.command_timeout or 900),
                        ),
                    )
                except SandboxError as exc:
                    results.append(
                        (check, 1, output + f"sandbox error: {exc}")
                    )
                    continue
                results.append((check, code, output + text))
    label = (
        "docker sandbox ("
        + (", ".join(sorted(set(labels))) or "none")
        + ")"
    )
    return results, label


def _record(
    ledger: Ledger,
    layout: ProjectLayout,
    project: dict[str, Any],
    task: dict[str, Any],
    result: TaskQAResult,
    exit_code: int,
    log: Callable[[str], None],
) -> TaskQAResult:
    task_id = str(task["id"])
    path = layout.artifact(f"docs/program/agent/{task_id}.qa.md")
    report_ref = str(path.relative_to(layout.root))
    check_lines = (
        "\n".join(
            f"- {item['criterion']}: {item.get('verdict', item.get('verification', 'command'))}"
            + (
                f" (exit {item['exit_code']})"
                if item.get("exit_code") is not None
                else ""
            )
            + (
                f" [{item.get('scope') or 'task'} "
                f"{item.get('repo') or 'project'} @ {item.get('workdir') or '-'}]"
                if item.get("verdict") != "review"
                else ""
            )
            for item in result.checks
        )
        or "- none"
    )
    failure_line = (
        f"- Failure kind: `{result.failure_kind}`\n"
        if result.failure_kind
        else ""
    )
    write_text(
        path,
        f"""# Task QA: {task.get('title', task_id)}

- Task: `{task_id}`
- Project: `{project['id']}`
- Runtime: {result.runtime}
- Verdict: **{result.status.upper()}**
{failure_line}- Exit code: {exit_code}
- Finished: {_now()}

## Checks

{check_lines}

## Output

```
{result.output or 'not run'}
```
""",
    )
    stored = get_task(layout, task_id) or task
    data = dict(stored.get("result") or {})
    data["qa"] = {
        "status": result.status,
        "runtime": result.runtime,
        "report": report_ref,
        "commands": result.commands,
        "checks": result.checks,
        "review_required": result.review_required,
        "failure_kind": result.failure_kind,
    }
    status = str(stored.get("status") or task.get("status") or "done")
    if result.status == "fail":
        status = "failed"
        failing = next(
            (
                item
                for item in result.checks
                if item.get("verdict") == "fail"
                and (
                    not result.failure_kind
                    or item.get("failure") == result.failure_kind
                )
            ),
            None,
        )
        if failing is None:
            failing = next(
                (
                    item
                    for item in result.checks
                    if item.get("verdict") == "fail"
                ),
                None,
            )
        if failing is not None:
            detail = (
                f"{failing.get('criterion')} "
                f"[{failing.get('scope') or 'task'} "
                f"{failing.get('repo') or 'project'} @ "
                f"{failing.get('workdir') or '-'}]"
            )
            if result.failure_kind in {
                "spec",
                "environment",
                "infrastructure",
            }:
                evidence = " ".join(
                    str(failing.get("output") or "").split()
                )
                if evidence:
                    detail += ": " + evidence[:1200]
        else:
            detail = f"exit {exit_code}"
        summary = str(data.get("summary") or "").strip()
        data["summary"] = (
            (summary + "; " if summary else "")
            + f"task QA failed: {detail}"
        )
        kind = {
            "spec": "spec",
            "environment": "environment",
            "infrastructure": "infrastructure",
        }.get(result.failure_kind, "qa")
        data["failure"] = {
            "kind": kind,
            "message": f"task QA failed: {detail}",
            "retryable": kind == "infrastructure",
        }
    else:
        skipped = [
            item
            for item in result.checks
            if item.get("verdict") == "skipped"
        ]
        if skipped:
            note = str(skipped[0].get("output") or "").strip()
            note = note.splitlines()[0] if note else "e2e skipped"
            summary = str(data.get("summary") or "").strip()
            data["summary"] = (
                (summary + "; " if summary else "") + note
            )
    update_task(layout, task_id, status=status, result=data)
    attempt = attempt_number(task)
    ledger.append_event(
        str(project["id"]),
        "task_qa",
        status={
            "pass": "completed",
            "fail": "failed",
            "review": "review",
            "skipped": "skipped",
        }[result.status],
        idempotency_key=(
            f"{project['id']}:task_qa:{task_id}:{result.status}:"
            f"r{attempt}"
        ),
        artifact_refs=[report_ref],
        payload={
            "task": task_id,
            "status": result.status,
            "runtime": result.runtime,
            "review_required": result.review_required,
            "failure_kind": result.failure_kind,
            "rework": attempt,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[qa] {project['id']}: task {task_id}: {result.status} "
        f"({result.runtime})"
        + (
            f" [{result.failure_kind}]"
            if result.failure_kind
            else ""
        )
    )
    return TaskQAResult(
        status=result.status,
        runtime=result.runtime,
        report=report_ref,
        commands=result.commands,
        output=result.output,
        checks=result.checks,
        review_required=result.review_required,
        failure_kind=result.failure_kind,
    )


def run_task_qa(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    task: dict[str, Any],
    log: Callable[[str], None] = print,
) -> TaskQAResult:
    """Run the project gate and the task's acceptance checks."""

    layout = ProjectLayout.detect(project["workspace"])
    task = get_task(layout, str(task["id"])) or task
    log(f"[qa] {project['id']}: task {task['id']}: running")
    repo_id = _task_repo_id(layout, task)
    result_data = dict(task.get("result") or {})
    task_files = [
        str(item) for item in (result_data.get("files_changed") or [])
    ]
    if repo_id:
        repo_path = layout.repo_path(repo_id)
        if (repo_path / ".git").exists():
            dirty = status_paths(repo_path)

            def _owned(path: str) -> bool:
                for item in task_files:
                    if item.endswith("/") and path.startswith(item):
                        return True
                    if path == item:
                        return True
                return False

            own = [item for item in dirty if _owned(item)]
            if own:
                detail = (
                    "the task repository still has the task's uncommitted "
                    "files: " + ", ".join(own)
                )
                checks = [
                    {
                        "criterion": "the task repository is committed",
                        "command": "",
                        "exit_code": 1,
                        "verdict": "fail",
                        "scope": "task",
                        "repo": repo_id,
                        "workdir": str(repo_path),
                        "output": detail,
                        "failure": "code",
                    }
                ]
                return _record(
                    ledger,
                    layout,
                    project,
                    task,
                    TaskQAResult(
                        status="fail",
                        runtime="uncommitted",
                        output=detail,
                        checks=checks,
                        failure_kind="code",
                    ),
                    1,
                    log,
                )
    if _documentation_only(task):
        return _record(
            ledger,
            layout,
            project,
            task,
            TaskQAResult(
                status="skipped",
                runtime="documentation-only",
                output=(
                    "Documentation-only change; executable checks are "
                    "skipped and the result is verified by review."
                ),
                review_required=True,
            ),
            0,
            log,
        )
    try:
        environment = load_environment(layout)
    except Exception as exc:  # noqa: BLE001 - environment is project data
        return _record(
            ledger,
            layout,
            project,
            task,
            TaskQAResult(
                status="fail",
                runtime="environment",
                output=f"environment contract: {exc}",
                failure_kind="environment",
            ),
            2,
            log,
        )
    problem = integration_problem(layout, environment)
    integration_skips: list[dict[str, Any]] = []
    if problem:
        # The plan carries a task that declares the e2e. Until that task
        # lands, the program e2e is recorded as skipped: the other checks
        # still decide the task instead of every task failing on the contract.
        integration_skips.append(
            _skipped_e2e(
                {
                    "criterion": "program e2e",
                    "command": "",
                    "repo": (
                        environment.repository(layout)
                        if environment is not None
                        else ""
                    ),
                },
                problem,
            )
        )
    executable, review = _qa_checks(
        layout, environment, task, repo_id
    )
    e2e_checks = [
        item for item in executable if item.get("scope") == "e2e"
    ]
    other_checks = [
        item for item in executable if item.get("scope") != "e2e"
    ]
    deferred = integration_warning(layout, environment)
    missing = capabilities.unavailable(environment, layout)
    skipped_e2e: list[dict[str, Any]] = []
    run_checks = list(executable)
    skip_message = ""
    if e2e_checks and missing:
        skip_message = capabilities.message(missing)
        skipped_e2e = [
            _skipped_e2e(item, skip_message) for item in e2e_checks
        ]
        run_checks = other_checks
    elif not e2e_checks and (deferred or missing):
        parts = []
        if missing:
            parts.append(capabilities.message(missing))
        if deferred:
            parts.append(deferred)
        skip_message = "\n".join(parts)
        workdir = str(
            environment.workdir(layout)
            if environment is not None
            else layout.root
        )
        skipped_e2e = [
            _skipped_e2e(
                {
                    "criterion": "environment e2e (deferred)",
                    "command": "",
                    "repo": (
                        environment.repository(layout)
                        if environment is not None
                        else ""
                    ),
                    "workdir": workdir,
                },
                skip_message,
            )
        ]
        run_checks = other_checks
    elif e2e_checks:
        run_checks = executable
    else:
        run_checks = other_checks
    if integration_skips:
        skipped_e2e = skipped_e2e + integration_skips
        if not skip_message:
            skip_message = problem
    if not run_checks and not review and not skipped_e2e:
        return _record(
            ledger,
            layout,
            project,
            task,
            TaskQAResult(
                status="skipped",
                runtime="none",
                output="No environment command, check or task test command.",
            ),
            0,
            log,
        )
    if skipped_e2e:
        first = skip_message.splitlines()[0] if skip_message else "e2e skipped"
        log(
            f"[qa] {project['id']}: task {task['id']}: {first}"
        )
    task_checks = [
        item for item in executable if item.get("scope") == "task"
    ]
    problems = check_problems(layout, repo_id, task_checks)
    if problems:
        detail = "\n".join(f"- {problem}" for problem in problems)
        workdir = str(
            layout.repo_path(repo_id) if repo_id else layout.root
        )
        checks = [
            {
                "criterion": "check command runs in the task repository",
                "command": "",
                "exit_code": 2,
                "verdict": "fail",
                "scope": "task",
                "repo": repo_id,
                "workdir": workdir,
                "output": detail,
                "failure": "spec",
            }
        ]
        return _record(
            ledger,
            layout,
            project,
            task,
            TaskQAResult(
                status="fail",
                runtime="preflight",
                output=detail,
                checks=checks,
                failure_kind="spec",
            ),
            2,
            log,
        )
    results: list[tuple[dict[str, Any], int, str]]
    if docker_runner(settings) is not None:
        if not repo_id:
            return _record(
                ledger,
                layout,
                project,
                task,
                TaskQAResult(
                    status="fail",
                    runtime="sandbox",
                    output="The task has no repository for the sandbox.",
                    failure_kind="spec",
                ),
                2,
                log,
            )
        try:
            results, runtime = _run_sandbox(
                settings, project, layout, environment, repo_id, run_checks
            )
        except SandboxError as exc:
            results = [
                (
                    {
                        "criterion": "sandbox",
                        "command": "",
                        "scope": "environment",
                        "repo": "",
                        "workdir": "",
                        "failure": "infrastructure",
                    },
                    1,
                    str(exc),
                )
            ]
            runtime = "sandbox"
    else:
        results = _run_local(
            layout,
            environment,
            repo_id,
            run_checks,
            max(60.0, float(settings.command_timeout or 900)),
        )
        runtime = "local"
        if environment is not None and (environment.test or environment.e2e):
            runtime += " + environment.yaml"
    if skipped_e2e:
        runtime += " + e2e skipped"
    checks: list[dict[str, Any]] = []
    output = ""
    exit_code = 0
    failure_kinds: set[str] = set()
    for check, code, text in results:
        output += text
        failure = str(check.get("failure") or "")
        if code != 0 and not failure:
            if (
                code in {124, 126, 127}
                or "cannot run command" in text
                or "timed out" in text
            ):
                failure = "infrastructure"
            elif check.get("scope") == "e2e":
                failure = "code"
            elif check.get("scope") == "environment":
                failure = "environment"
            else:
                failure = "code"
        if code != 0:
            failure_kinds.add(failure)
        checks.append(
            {
                "criterion": check["criterion"],
                "command": check["command"],
                "exit_code": code,
                "verdict": "pass" if code == 0 else "fail",
                "scope": check.get("scope") or "task",
                "repo": check.get("repo", repo_id),
                "workdir": check.get("workdir", ""),
                "output": _tail(text) if code != 0 else "",
                "failure": failure if code != 0 else "",
            }
        )
        if code != 0 and exit_code == 0:
            exit_code = code
    for item in skipped_e2e:
        checks.append(item)
        output += (
            f"$ {item['command']}\n# cwd: {item['workdir']}\n"
            f"[skipped] {item['output']}\n"
        )
    for check in review:
        checks.append(
            {
                "criterion": check["criterion"],
                "command": "",
                "exit_code": None,
                "verdict": "review",
                "scope": "review",
                "repo": "",
                "workdir": "",
                "output": "",
                "failure": "",
            }
        )
    if exit_code != 0:
        status = "fail"
    elif run_checks:
        status = "pass"
    elif review:
        status = "review"
    elif skipped_e2e:
        status = "pass"
    else:
        status = "review"
    if exit_code != 0:
        exit_code = exit_code or 1
    failure_kind = ""
    if exit_code != 0:
        for candidate in ("code", "spec", "infrastructure", "environment"):
            if candidate in failure_kinds:
                failure_kind = candidate
                break
    return _record(
        ledger,
        layout,
        project,
        task,
        TaskQAResult(
            status=status,
            runtime=runtime,
            commands=[
                {
                    "command": item["command"],
                    "exit_code": item["exit_code"],
                    "scope": item["scope"],
                    "repo": item["repo"],
                    "workdir": item["workdir"],
                }
                for item in checks
                if item["exit_code"] is not None
            ],
            output=_cap(output),
            checks=checks,
            review_required=bool(review),
            failure_kind=failure_kind,
        ),
        exit_code,
        log,
    )
