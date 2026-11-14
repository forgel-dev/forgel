"""Independent QA for a coding task.

The coding agent runs its own final test; this pass runs the project's
environment contract again, from a clean process, after the agent has committed.
It is the difference between "the agent says it works" and "the project's own
gate passes".

The QA verdict is authoritative: a green agent run with a red QA becomes a
failed task, with the QA report attached. A project without an environment
contract falls back to the task's test command; when there is nothing to run,
the verdict is ``skipped`` rather than a false pass.
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
    status: str  # pass | fail | skipped
    runtime: str
    report: str = ""
    commands: list[dict[str, Any]] = field(default_factory=list)
    output: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cap(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


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


def _environment_commands(
    environment: Environment | None, task: dict[str, Any]
) -> tuple[list[str], bool]:
    """The project gate plus the task's own test command.

    The environment contract is the project gate; a task-specific test command
    is an additional check on this change and runs too, unless it is already
    one of the gate commands. The boolean says whether the environment
    contributed a command (used in the runtime label).
    """

    commands = (
        list(environment.test) + list(environment.e2e)
        if environment is not None
        else []
    )
    from_environment = bool(commands)
    test_command = [str(item) for item in task.get("test_command", [])]
    if test_command:
        rendered = shlex.join(test_command)
        if rendered not in commands:
            commands.append(rendered)
    return commands, from_environment


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


def _run_local(
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
    commands: Sequence[str],
) -> tuple[int, str]:
    workdir = _workdir(layout, environment, repo_id)
    env = {
        **os.environ,
        **(environment.env_map if environment is not None else {}),
    }
    output = ""
    for command in commands:
        try:
            argv = command_argv(command)
        except Exception as exc:  # noqa: BLE001 - reported as a failure
            output += f"$ {command}\ninvalid command: {exc}\n"
            return 2, output
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
            output += f"timed out after 600s\n{partial}"
            return 124, output
        except (OSError, subprocess.SubprocessError) as exc:
            output += f"cannot run command: {exc}\n"
            return 127, output
        output += completed.stdout + completed.stderr
        if completed.returncode != 0:
            return completed.returncode, output
    return 0, output


def _run_sandbox(
    settings: Settings,
    project: dict[str, Any],
    layout: ProjectLayout,
    environment: Environment | None,
    repo_id: str,
    commands: Sequence[str],
) -> tuple[int, str, str]:
    sandbox = DockerSandbox(settings)
    available, detail = sandbox.available()
    if not available:
        raise SandboxError(f"sandbox unavailable: {detail}")
    session = sandbox.session(
        layout, environment, str(project["id"]), repo_id
    )
    label = f"docker sandbox ({session.image})"
    output = ""
    with session:
        for command in commands:
            argv = shlex.split(command)
            if not argv:
                output += f"$ {command}\nempty command\n"
                return 2, output, label
            output += f"$ {command}\n"
            code, text = session.run(argv, timeout=600)
            output += text
            if code != 0:
                return code, output, label
    return 0, output, label


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
    path = layout.artifact(
        f"docs/program/agent/{task_id}.qa.md"
    )
    report_ref = str(path.relative_to(layout.root))
    command_lines = (
        "\n".join(
            f"- `{item['command']}` -> exit {item['exit_code']}"
            for item in result.commands
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

## Commands

{command_lines}

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
    }
    status = str(stored.get("status") or task.get("status") or "done")
    if result.status == "fail":
        status = "failed"
        summary = str(data.get("summary") or "").strip()
        data["summary"] = (
            (summary + "; " if summary else "")
            + f"task QA failed (exit {exit_code})"
        )
    update_task(layout, task_id, status=status, result=data)
    ledger.append_event(
        str(project["id"]),
        "task_qa",
        status={
            "pass": "completed",
            "fail": "failed",
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
    )


def run_task_qa(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    task: dict[str, Any],
    log: Callable[[str], None] = print,
) -> TaskQAResult:
    """Run the project's gate for a completed task and record the verdict."""

    layout = ProjectLayout.detect(project["workspace"])
    task = get_task(layout, str(task["id"])) or task
    repo_id = _task_repo_id(layout, task)
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
    commands, from_environment = _environment_commands(environment, task)
    if not commands:
        return _record(
            ledger,
            layout,
            project,
            task,
            TaskQAResult(
                status="skipped",
                runtime="none",
                output="No environment command and no task test command.",
            ),
            0,
            log,
        )
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
            code, output, runtime = _run_sandbox(
                settings,
                project,
                layout,
                environment,
                repo_id,
                commands,
            )
        except SandboxError as exc:
            code, output, runtime = 1, f"sandbox error: {exc}", "sandbox"
    else:
        code, output = _run_local(
            layout, environment, repo_id, commands
        )
        runtime = "local"
        if from_environment:
            runtime += " + environment.yaml"
    return _record(
        ledger,
        layout,
        project,
        task,
        TaskQAResult(
            status="pass" if code == 0 else "fail",
            runtime=runtime,
            commands=[
                {"command": command, "exit_code": code}
                for command in commands
            ],
            output=_cap(output),
        ),
        code,
        log,
    )
