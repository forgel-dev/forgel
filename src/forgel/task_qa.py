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

from .artifacts import write_text
from .config import Settings
from .environment import Environment, command_argv, load_environment
from .layout import ProjectLayout
from .ledger import Ledger
from .sandbox import DockerSandbox, SandboxError, docker_runner
from .tasks import get_task, update_task

MAX_OUTPUT = 20_000


@dataclass(frozen=True)
class TaskQAResult:
    status: str  # pass | fail | review | skipped
    runtime: str
    report: str = ""
    commands: list[dict[str, Any]] = field(default_factory=list)
    output: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)
    review_required: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cap(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


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
    environment: Environment | None, task: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Executable checks and review-only criteria, deduplicated by command."""

    executable: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, command: str) -> None:
        if command in seen:
            return
        seen.add(command)
        executable.append(
            {"criterion": label, "command": command, "verification": "command"}
        )

    if environment is not None:
        for command in environment.test:
            add("environment test", command)
        for command in environment.e2e:
            add("environment e2e", command)
    for check in task.get("checks", []):
        criterion = str(check.get("criterion", "")).strip() or "check"
        if check.get("verification") == "review":
            review.append(
                {"criterion": criterion, "verification": "review"}
            )
            continue
        add(criterion, shlex.join(check.get("command", [])))
    test_command = [str(item) for item in task.get("test_command", [])]
    if test_command:
        add("task test command", shlex.join(test_command))
    return executable, review


def _workdir(
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
) -> Path:
    if environment is not None:
        return environment.workdir(layout)
    if repo_id:
        return layout.repo_path(repo_id)
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
) -> list[tuple[dict[str, Any], int, str]]:
    workdir = _workdir(layout, environment, repo_id)
    env = {
        key: os.environ[key]
        for key in SAFE_ENV_KEYS
        if key in os.environ
    }
    env.update(environment.env_map if environment is not None else {})
    results: list[tuple[dict[str, Any], int, str]] = []
    for check in checks:
        command = check["command"]
        output = ""
        try:
            argv = command_argv(command)
        except Exception as exc:  # noqa: BLE001 - reported as a failure
            results.append((check, 2, f"invalid command: {exc}"))
            continue
        output += f"$ {command}\n"
        try:
            completed = subprocess.run(
                argv,
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            partial = (exc.stdout or "") + (exc.stderr or "")
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
    session = sandbox.session(
        layout, environment, str(project["id"]), repo_id
    )
    label = f"docker sandbox ({session.image})"
    results: list[tuple[dict[str, Any], int, str]] = []
    with session:
        for check in checks:
            argv = shlex.split(check["command"])
            output = f"$ {check['command']}\n"
            if not argv:
                results.append((check, 2, output + "empty command\n"))
                continue
            try:
                code, text = session.run(argv, timeout=600)
            except SandboxError as exc:
                results.append((check, 1, output + f"sandbox error: {exc}"))
                break
            results.append((check, code, output + text))
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
            for item in result.checks
        )
        or "- none"
    )
    write_text(
        path,
        f"""# Task QA: {task.get('title', task_id)}

- Task: `{task_id}`
- Project: `{project['id']}`
- Runtime: {result.runtime}
- Verdict: **{result.status.upper()}**
- Exit code: {exit_code}
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
    }
    status = str(stored.get("status") or task.get("status") or "done")
    if result.status == "fail":
        status = "failed"
        summary = str(data.get("summary") or "").strip()
        data["summary"] = (
            (summary + "; " if summary else "")
            + f"task QA failed (exit {exit_code})"
        )
        data["failure"] = {
            "kind": "qa",
            "message": f"task QA failed (exit {exit_code})",
            "retryable": False,
        }
    update_task(layout, task_id, status=status, result=data)
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
            f"{project['id']}:task_qa:{task_id}:{result.status}"
        ),
        artifact_refs=[report_ref],
        payload={
            "task": task_id,
            "status": result.status,
            "runtime": result.runtime,
            "review_required": result.review_required,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(
        f"[qa] {project['id']}: task {task_id}: {result.status} "
        f"({result.runtime})"
    )
    return TaskQAResult(
        status=result.status,
        runtime=result.runtime,
        report=report_ref,
        commands=result.commands,
        output=result.output,
        checks=result.checks,
        review_required=result.review_required,
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
            ),
            2,
            log,
        )
    executable, review = _qa_checks(environment, task)
    if not executable and not review:
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
                ),
                2,
                log,
            )
        try:
            results, runtime = _run_sandbox(
                settings, project, layout, environment, repo_id, executable
            )
        except SandboxError as exc:
            results = [
                ({"criterion": "sandbox", "command": ""}, 1, str(exc))
            ]
            runtime = "sandbox"
    else:
        results = _run_local(layout, environment, repo_id, executable)
        runtime = "local"
        if environment is not None and (environment.test or environment.e2e):
            runtime += " + environment.yaml"
    checks: list[dict[str, Any]] = []
    output = ""
    exit_code = 0
    for check, code, text in results:
        output += text
        checks.append(
            {
                "criterion": check["criterion"],
                "command": check["command"],
                "exit_code": code,
                "verdict": "pass" if code == 0 else "fail",
            }
        )
        if code != 0 and exit_code == 0:
            exit_code = code
    for check in review:
        checks.append(
            {
                "criterion": check["criterion"],
                "command": "",
                "exit_code": None,
                "verdict": "review",
            }
        )
    if exit_code != 0:
        status = "fail"
    elif executable:
        status = "pass"
    else:
        status = "review"
    if exit_code != 0:
        exit_code = exit_code or 1
    return _record(
        ledger,
        layout,
        project,
        task,
        TaskQAResult(
            status=status,
            runtime=runtime,
            commands=[
                {"command": item["command"], "exit_code": item["exit_code"]}
                for item in checks
                if item["exit_code"] is not None
            ],
            output=_cap(output),
            checks=checks,
            review_required=bool(review),
        ),
        exit_code,
        log,
    )
