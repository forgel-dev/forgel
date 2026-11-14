"""Coding agent: execute a task inside one repository.

The model returns one JSON action per turn. The runtime executes it, returns a
bounded observation and loops. This protocol works with any chat model (no
provider-specific function calling), which also makes a subagent bridge and a
scripted local run possible.

Safety is deliberately conservative: paths stay inside the repository, a small
command allowlist is used, a step limit bounds cost, secrets are removed from
the child environment, and secret-looking files are never committed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import git_ops, tasks
from .artifacts import write_text
from .config import Settings
from .environment import Environment, EnvironmentError, load_environment
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .sandbox import CommandRunner, SandboxError, docker_runner

MAX_STEPS = 24
MAX_FILE_BYTES = 200_000
MAX_READ_CHARS = 12_000
MAX_OBSERVATION = 4_000
MAX_LIST_ENTRIES = 200
MAX_HISTORY_MESSAGES = 12
ALLOWED_ACTIONS = {
    "list_files",
    "read_file",
    "write_file",
    "delete_file",
    "run",
    "done",
    "fail",
}
ALLOWED_EXECUTABLES = {
    "python",
    "python3",
    "pytest",
    "node",
    "npm",
    "make",
    "git",
}
GIT_READ_ONLY = {"status", "diff", "log", "show", "rev-parse"}
NPM_ALLOWED = {"test", "run", "--version", "-v"}
SKIP_PARTS = {
    ".git",
    ".forgel",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
}
SECRET_PATH_NAMES = {".env", "secrets.toml"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
SAFE_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TERM",
    "SHELL",
    "VIRTUAL_ENV",
}
DEFAULT_GITIGNORE = """__pycache__/
*.py[cod]
node_modules/
.env
.env.*
!.env.example
*.sqlite3
.forgel/
"""

SYSTEM_PROMPT = """You are Forgel's coding agent for exactly one repository.

Work only inside the repository. Never touch `.git`, never read or write files
outside it, and never add secrets.

Reply with exactly one JSON object per turn. Available actions:
{"action": "list_files", "path": "."}
{"action": "read_file", "path": "relative/path"}
{"action": "write_file", "path": "relative/path", "content": "..."}
{"action": "delete_file", "path": "relative/path"}
{"action": "run", "command": ["python", "-m", "unittest"], "timeout": 60}
{"action": "done", "summary": "what was implemented and how it was tested"}
{"action": "fail", "reason": "why the task cannot be completed"}

Rules:
- Implement exactly the explicit requirements. Do not add unrelated features.
- Prefer the Python standard library unless the task says otherwise. Do not
  install packages.
- No external APIs, no network calls, no deployment changes, no Telegram.
- Write tests for the requirements and run them. Call done only after the
  tests pass and the requirements are implemented.
- Keep the change small and readable.
"""


class AgentError(RuntimeError):
    """The coding agent cannot run a task."""


@dataclass(frozen=True)
class AgentResult:
    status: str
    summary: str
    steps: int
    files_changed: list[str] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    test_output: str = ""
    report: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ref(layout: ProjectLayout, path: Path) -> str:
    return str(path.relative_to(layout.root))


def _safe_env(layout: ProjectLayout) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key in SAFE_ENV_KEYS
    }
    agent_home = layout.root / ".forgel" / "agent-home"
    agent_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(agent_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _cap(text: str, limit: int = MAX_OBSERVATION) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


def parse_action(raw: str) -> dict[str, Any] | None:
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
    if not isinstance(data, dict):
        return None
    action = data.get("action")
    if action not in ALLOWED_ACTIONS:
        return None
    return data


class CodingAgent:
    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        client: ModelClient,
        max_steps: int | None = None,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.client = client
        env_steps = os.environ.get("FORGEL_AGENT_MAX_STEPS", "").strip()
        steps = max_steps or (int(env_steps) if env_steps.isdigit() else MAX_STEPS)
        self.max_steps = max(4, min(steps, 60))

    # ------------------------------------------------------------------ run

    def run(
        self,
        project: Mapping[str, Any],
        task: Mapping[str, Any],
        log: Callable[[str], None] = print,
    ) -> AgentResult:
        layout = ProjectLayout.detect(project["workspace"])
        repo_id, repo = self._repository(layout, task)
        if not (repo / ".git").exists():
            raise AgentError(f"repository {repo_id} has no git history")
        gitignore = repo / ".gitignore"
        if not gitignore.exists():
            write_text(gitignore, DEFAULT_GITIGNORE)

        try:
            environment = load_environment(layout)
        except EnvironmentError as exc:
            raise AgentError(f"environment contract: {exc}") from exc
        model = project_model_name(layout.control)
        stack = ExitStack()
        try:
            runner = self._open_runner(
                stack, layout, project, repo_id, environment
            )
            (
                status,
                summary,
                steps,
                actions,
                commands,
                touched,
                test_output,
            ) = self._converse(
                layout, repo, repo_id, task, model, runner, environment
            )
        finally:
            stack.close()
        if status == "done":
            try:
                changed = sorted(
                    set(touched) | set(git_ops.status_paths(repo))
                )
                if changed:
                    git_ops.commit_all(
                        repo, f"Agent: {task['title']}"
                    )
            except git_ops.GitOperationError as exc:
                status = "failed"
                summary += f"; commit failed: {exc}"

        files_changed = sorted(
            set(touched) | set(git_ops.status_paths(repo))
        )
        report = self._write_report(
            layout,
            task,
            repo_id,
            status,
            summary,
            steps,
            files_changed,
            actions,
            commands,
            test_output,
        )
        tasks.update_task(
            layout,
            str(task["id"]),
            status="done" if status == "done" else "failed",
            finished_at=_now(),
            result={
                "summary": summary,
                "files_changed": files_changed,
                "commands": commands,
                "test_output": _cap(test_output, 6000),
                "report": _ref(layout, report),
            },
        )
        try:
            if (layout.control / ".git").exists():
                git_ops.commit_all(
                    layout.control, f"Agent report: {task['title']}"
                )
                git_ops.tag_baseline(layout.control)
        except git_ops.GitOperationError:
            pass
        self._record_event(
            layout,
            project,
            task,
            status,
            report,
            summary,
            files_changed,
        )
        log(f"[agent] {project['id']}: {status}: {summary}")
        return AgentResult(
            status=status,
            summary=summary,
            steps=steps,
            files_changed=files_changed,
            commands=commands,
            test_output=test_output,
            report=_ref(layout, report),
        )

    # ------------------------------------------------------------- sandbox

    def _open_runner(
        self,
        stack: ExitStack,
        layout: ProjectLayout,
        project: Mapping[str, Any],
        repo_id: str,
        environment: Environment | None,
    ) -> CommandRunner | None:
        """Enter the project sandbox when configured, or return ``None``.

        The repository is bind-mounted into the container, so file actions stay
        on the host and only command execution moves into the sandbox.
        """

        sandbox = docker_runner(self.settings)
        if sandbox is None:
            return None
        if environment is None and not self.settings.sandbox_image:
            raise AgentError(
                "FORGEL_SANDBOX=docker requires environment.yaml or "
                "FORGEL_SANDBOX_IMAGE"
            )
        available, detail = sandbox.available()
        if not available:
            raise AgentError(f"sandbox unavailable: {detail}")
        try:
            return stack.enter_context(
                sandbox.session(
                    layout,
                    environment,
                    str(project["id"]),
                    repo_id,
                )
            )
        except SandboxError as exc:
            raise AgentError(f"sandbox: {exc}") from exc

    def _converse(
        self,
        layout: ProjectLayout,
        repo: Path,
        repo_id: str,
        task: Mapping[str, Any],
        model: str,
        runner: CommandRunner | None,
        environment: Environment | None,
    ) -> tuple[
        str,
        str,
        int,
        list[str],
        list[dict[str, Any]],
        set[str],
        str,
    ]:
        """Run the model loop and the final test, returning the run state."""

        messages: list[ModelMessage] = [
            ModelMessage("system", SYSTEM_PROMPT),
            ModelMessage(
                "user",
                self._task_prompt(layout, task, repo_id, repo),
            ),
        ]
        actions: list[str] = []
        commands: list[dict[str, Any]] = []
        touched: set[str] = set()
        status = "failed"
        summary = "step limit reached"
        invalid = 0
        steps = 0

        for step in range(1, self.max_steps + 1):
            steps = step
            try:
                raw = self.client.complete(messages, model=model)
            except ModelError as exc:
                status = "failed"
                summary = f"model call failed: {exc}"
                break
            action = parse_action(raw)
            if action is None:
                invalid += 1
                messages.append(ModelMessage("assistant", raw))
                messages.append(
                    ModelMessage(
                        "user",
                        "Invalid reply. Return exactly one JSON action object.",
                    )
                )
                if invalid >= 3:
                    status = "failed"
                    summary = "the model did not return a valid action"
                    break
                continue
            invalid = 0
            kind = str(action["action"])
            messages.append(
                ModelMessage("assistant", json.dumps(action, ensure_ascii=False))
            )
            if kind == "done":
                status = "done"
                summary = str(action.get("summary", "")).strip() or (
                    "agent reported done"
                )
                break
            if kind == "fail":
                status = "failed"
                summary = str(action.get("reason", "")).strip() or (
                    "agent reported failure"
                )
                break
            observation, command = self._execute(
                layout,
                repo,
                action,
                touched,
                runner,
                environment.env_map if environment else None,
            )
            actions.append(self._action_summary(action))
            if command is not None:
                commands.append(command)
            messages.append(
                ModelMessage("user", f"OBSERVATION:\n{_cap(observation)}")
            )
            messages = self._trim(messages)
        else:
            status = "failed"
            summary = f"step limit reached ({self.max_steps})"

        test_output = ""
        if status == "done":
            test_command = [
                str(item) for item in task.get("test_command", [])
            ]
            if test_command:
                code, output = self._run_command(
                    layout,
                    repo,
                    test_command,
                    timeout=120,
                    runner=runner,
                    extra_env=environment.env_map if environment else None,
                )
                test_output = output
                commands.append(
                    {
                        "command": test_command,
                        "exit_code": code,
                        "final_test": True,
                    }
                )
                if code != 0:
                    status = "failed"
                    summary += f"; final test command exited {code}"
        return (
            status,
            summary,
            steps,
            actions,
            commands,
            touched,
            test_output,
        )

    # ------------------------------------------------------------- setup

    @staticmethod
    def _repository(
        layout: ProjectLayout, task: Mapping[str, Any]
    ) -> tuple[str, Path]:
        from .program_manifest import entries

        repos = entries(layout)
        if not repos:
            raise AgentError("the project has no repositories")
        wanted = str(task.get("repo_id") or "")
        if wanted:
            entry = next(
                (item for item in repos if item["id"] == wanted), None
            )
            if entry is None:
                raise AgentError(f"unknown repository {wanted!r}")
        elif len(repos) == 1:
            entry = repos[0]
        else:
            ids = ", ".join(item["id"] for item in repos)
            raise AgentError(
                f"the project has several repositories; set repo_id ({ids})"
            )
        return entry["id"], layout.repo_path(entry["id"])

    def _task_prompt(
        self,
        layout: ProjectLayout,
        task: Mapping[str, Any],
        repo_id: str,
        repo: Path,
    ) -> str:
        requirements = "\n".join(
            f"- {item}" for item in task.get("requirements", [])
        )
        acceptance = "\n".join(
            f"- {item}" for item in task.get("acceptance", [])
        )
        constraints = "\n".join(
            f"- {item}" for item in task.get("constraints", [])
        ) or "- none"
        test_command = task.get("test_command") or []
        tree = self._list(repo)
        branch = git_ops.current_branch(repo)
        return f"""TASK: {task['title']}

Requirements:
{requirements}

Acceptance criteria:
{acceptance}

Constraints:
{constraints}

Final test command: {json.dumps(test_command)}
Repository: {repo_id} at {repo} (branch {branch})

Files:
{tree}
"""

    # ------------------------------------------------------------ execution

    def _execute(
        self,
        layout: ProjectLayout,
        repo: Path,
        action: Mapping[str, Any],
        touched: set[str],
        runner: CommandRunner | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        kind = str(action.get("action"))
        try:
            if kind == "list_files":
                return self._list(repo), None
            if kind == "read_file":
                path = self._path(repo, action.get("path"))
                if path.name in SECRET_PATH_NAMES or path.name.endswith(
                    SECRET_SUFFIXES
                ):
                    return "secret-like files are not readable", None
                if not path.exists() or not path.is_file():
                    return f"file not found: {action.get('path')}", None
                data = path.read_bytes()
                if b"\x00" in data:
                    return "binary file; not displayed", None
                text = data.decode("utf-8", errors="replace")
                return _cap(text, MAX_READ_CHARS), None
            if kind == "write_file":
                path = self._path(repo, action.get("path"))
                self._check_write_path(path)
                content = action.get("content")
                if not isinstance(content, str):
                    return "write_file needs a string content", None
                raw = content.encode("utf-8")
                if len(raw) > MAX_FILE_BYTES:
                    return f"file too large ({len(raw)} bytes)", None
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                relative = path.relative_to(repo.resolve()).as_posix()
                touched.add(relative)
                return f"wrote {len(raw)} bytes to {relative}", None
            if kind == "delete_file":
                path = self._path(repo, action.get("path"))
                self._check_write_path(path)
                if not path.exists():
                    return f"file not found: {action.get('path')}", None
                path.unlink()
                relative = path.relative_to(repo.resolve()).as_posix()
                touched.add(relative)
                return f"deleted {relative}", None
            if kind == "run":
                command = self._command(action.get("command"))
                timeout = action.get("timeout", 60)
                try:
                    timeout_value = max(5, min(int(timeout), 120))
                except (TypeError, ValueError):
                    timeout_value = 60
                code, output = self._run_command(
                    layout,
                    repo,
                    command,
                    timeout=timeout_value,
                    runner=runner,
                    extra_env=extra_env,
                )
                return (
                    f"exit code {code}\n{_cap(output)}",
                    {
                        "command": command,
                        "exit_code": code,
                    },
                )
        except AgentError as exc:
            return f"error: {exc}", None
        except OSError as exc:
            return f"error: {exc}", None
        return f"unknown action: {kind}", None

    def _path(self, repo: Path, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise AgentError("a path is required")
        relative = Path(value)
        if relative.is_absolute():
            raise AgentError("absolute paths are not allowed")
        candidate = (repo / relative).resolve()
        try:
            candidate.relative_to(repo.resolve())
        except ValueError as exc:
            raise AgentError("path escapes the repository") from exc
        if any(part in {".git", ".forgel"} for part in relative.parts):
            raise AgentError("the .git and .forgel directories are off-limits")
        return candidate

    def _check_write_path(self, path: Path) -> None:
        name = path.name
        if name in SECRET_PATH_NAMES or name.endswith(SECRET_SUFFIXES):
            raise AgentError(f"refusing to write secret-like file {name}")

    def _command(self, value: Any) -> list[str]:
        if isinstance(value, str):
            command = shlex.split(value)
        elif isinstance(value, list) and all(
            isinstance(item, str) for item in value
        ):
            command = [str(item) for item in value]
        else:
            raise AgentError("run needs a command list")
        if not command:
            raise AgentError("the command is empty")
        executable = Path(command[0]).name
        if (
            executable not in ALLOWED_EXECUTABLES
            and not executable.startswith("python")
        ):
            raise AgentError(f"command {executable!r} is not allowed")
        if executable == "git":
            if len(command) < 2 or command[1] not in GIT_READ_ONLY:
                raise AgentError(
                    "only read-only git commands are allowed"
                )
        if executable == "npm":
            if len(command) < 2 or command[1] not in NPM_ALLOWED:
                raise AgentError("only npm test/run are allowed")
        if any(
            item in {"|", ">", ">>", "<", "&&", "||", ";"} for item in command
        ):
            raise AgentError("shell operators are not allowed")
        return command

    def _run_command(
        self,
        layout: ProjectLayout,
        repo: Path,
        command: Sequence[str],
        timeout: float,
        runner: CommandRunner | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> tuple[int, str]:
        if runner is not None:
            try:
                return runner.run(list(command), timeout=timeout)
            except SandboxError as exc:
                return 125, _cap(f"sandbox error: {exc}")
        argv = list(command)
        if argv and Path(argv[0]).name in {"python", "python3"}:
            argv[0] = sys.executable
        env = _safe_env(layout)
        if extra_env:
            env.update(extra_env)
        try:
            completed = subprocess.run(
                argv,
                cwd=str(repo),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            return 124, _cap(f"timed out after {timeout:g}s\n{output}")
        except (OSError, subprocess.SubprocessError) as exc:
            return 127, f"cannot run command: {exc}"
        output = (completed.stdout or "") + (completed.stderr or "")
        return completed.returncode, _cap(output)

    @staticmethod
    def _list(repo: Path) -> str:
        lines: list[str] = []
        for path in sorted(repo.rglob("*")):
            relative = path.relative_to(repo)
            if any(part in SKIP_PARTS for part in relative.parts):
                continue
            if path.name.endswith((".pyc", ".sqlite3", ".sqlite")):
                continue
            suffix = "/" if path.is_dir() else ""
            lines.append(relative.as_posix() + suffix)
            if len(lines) >= MAX_LIST_ENTRIES:
                lines.append("... [list truncated]")
                break
        return "\n".join(lines) or "(empty repository)"

    @staticmethod
    def _action_summary(action: Mapping[str, Any]) -> str:
        kind = action.get("action")
        if kind in {"read_file", "write_file", "delete_file"}:
            return f"{kind}: {action.get('path')}"
        if kind == "run":
            return f"run: {action.get('command')}"
        return str(kind)

    @staticmethod
    def _trim(messages: list[ModelMessage]) -> list[ModelMessage]:
        if len(messages) <= MAX_HISTORY_MESSAGES:
            return messages
        return [
            messages[0],
            messages[1],
            ModelMessage(
                "user",
                "Earlier observations were omitted to stay within context.",
            ),
        ] + messages[-8:]

    # --------------------------------------------------------------- output

    def _write_report(
        self,
        layout: ProjectLayout,
        task: Mapping[str, Any],
        repo_id: str,
        status: str,
        summary: str,
        steps: int,
        files_changed: list[str],
        actions: list[str],
        commands: list[dict[str, Any]],
        test_output: str,
    ) -> Path:
        path = layout.artifact(
            f"docs/program/agent/{task['id']}.md"
        )
        requirements = "\n".join(
            f"- {item}" for item in task.get("requirements", [])
        ) or "- none"
        acceptance = "\n".join(
            f"- {item}" for item in task.get("acceptance", [])
        ) or "- none"
        constraints = "\n".join(
            f"- {item}" for item in task.get("constraints", [])
        ) or "- none"
        action_lines = "\n".join(f"- {item}" for item in actions) or "- none"
        command_lines = (
            "\n".join(
                f"- `{json.dumps(item['command'])}` → exit "
                f"{item['exit_code']}"
                for item in commands
            )
            or "- none"
        )
        write_text(
            path,
            f"""# Agent Run: {task['title']}

- Task: `{task['id']}`
- Status: `{status}`
- Repository: `{repo_id}`
- Steps: {steps}
- Finished: {_now()}

## Requirements

{requirements}

## Acceptance Criteria

{acceptance}

## Constraints

{constraints}

## Summary

{summary or '—'}

## Files Changed

{chr(10).join(f'- `{item}`' for item in files_changed) or '- none'}

## Commands

{command_lines}

## Final Test Output

```
{test_output or 'not run'}
```

## Actions

{action_lines}
""",
        )
        return path

    def _record_event(
        self,
        layout: ProjectLayout,
        project: Mapping[str, Any],
        task: Mapping[str, Any],
        status: str,
        report: Path,
        summary: str,
        files_changed: list[str],
    ) -> None:
        generation = self.ledger.current_generation(str(project["id"]))
        self.ledger.append_event(
            str(project["id"]),
            "agent_run",
            status=status,
            idempotency_key=(
                f"{project['id']}:agent_run:{task['id']}:{status}"
            ),
            artifact_refs=[_ref(layout, report)],
            payload={
                "task": task["id"],
                "title": task["title"],
                "summary": summary,
                "files_changed": files_changed,
            },
            generation=generation,
        )
