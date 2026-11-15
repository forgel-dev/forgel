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

import hashlib
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

from . import git_ops, language, tasks
from .artifacts import write_text
from .config import Settings
from .session_context import (
    ContextBudget,
    SessionState,
    budget_for,
    handoff_prompt,
)
from .environment import Environment, EnvironmentError, load_environment
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .project_config import ConfigError, load_project_config
from .repo_tools import READ_DEFAULT_LINES, read_text_page
from .sandbox import CommandRunner, SandboxError, docker_runner

MAX_SESSIONS = 6
MAX_FILE_BYTES = 200_000
MAX_OBSERVATION = 200_000
MAX_INVALID_REPLIES = 8
MAX_LIST_ENTRIES = 200
MAX_REPEATED_ACTIONS = 5
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
    "docker",
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
    # Docker client settings. The agent HOME is redirected below, which hides
    # ~/.docker and makes the client fall back to /var/run/docker.sock even
    # when Docker Desktop keeps its socket and context elsewhere.
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "DOCKER_CERT_PATH",
    "DOCKER_TLS_VERIFY",
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

Reply with exactly one JSON object per turn. Do not emit tool-call markup,
XML or provider-specific function calls; the runtime understands only the
JSON actions below.
{"action": "list_files", "path": "."}
{"action": "read_file", "path": "relative/path", "offset": 1, "limit": 2000}
{"action": "write_file", "path": "relative/path", "content": "..."}
{"action": "delete_file", "path": "relative/path"}
{"action": "run", "command": ["python", "-m", "unittest"], "timeout": 60}
{"action": "done", "summary": "what was implemented and how it was tested", "assumptions": ["what you decided where the task was silent"], "test_removals": [{"test": "tests/test_x.py::test_y", "reason": "removed|replaced|wrong", "replacement": "tests/test_x.py::test_z"}]}
{"action": "fail", "reason": "why the task cannot be completed"}

Context:
- The runtime owns the context window. It may end this session and hand your
  state to a new session. Do not estimate tokens, warn about context limits or
  ask to continue; just keep working from the task, the repository and any
  SESSION HANDOFF you receive.

Autonomy (D-075):
- Work autonomously. The task is the source of truth. You cannot ask the user
  questions and must not stop for permission to start, continue or finish.
- When a detail is unspecified but reversible, choose the simplest option
  consistent with the requirements and record it in done.assumptions.
- Use fail only when two interpretations would produce materially different
  products and the wrong one wastes a full cycle, when the action is
  irreversible or destructive (deleting data, rewriting history, force-push,
  production deploy, payments, secrets, legal), or when required access is
  missing. State the exact decision needed.
- Before release, err on the side of doing and showing a finished result; in
  production, treat product data conservatively.

Rules:
- Implement exactly the explicit requirements. Do not add unrelated features.
- Use read_file for file contents. run is only for tests and build commands;
  never use python, grep, cat or similar to print a file. read_file returns a
  numbered line range with a continuation hint; read the next range with
  offset instead of writing helper scripts.
- A file you have read is in the conversation. Do not read it again before
  editing; when you know the exact change, call write_file immediately.
- Do not repeat an action. If you see the same observation twice, change the
  approach or make the edit.
- If the task changes documentation only, edit the document and call done; do
  not add tests.
- Prefer the Python standard library unless the task says otherwise. Do not
  install packages.
- No external APIs, no network calls, no deployment changes, no Telegram.
- Write tests for the requirements and run them. Call done only after the
  tests pass and the requirements are implemented.
- Tests are normally only added. Deleting a test requires a justification in
  done.test_removals, with one of: "removed" (the scenario is genuinely
  removed), "replaced" (the behavior changed and a new test replaces it; name
  the replacement), or "wrong" (the test was incorrect or duplicated). Never
  delete or weaken a test just to make the run pass.
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
    parent_home = os.environ.get("HOME", "")
    if "DOCKER_CONFIG" not in env and parent_home:
        docker_config = Path(parent_home) / ".docker"
        if docker_config.exists():
            env["DOCKER_CONFIG"] = str(docker_config)
    agent_home = layout.root / ".forgel" / "agent-home"
    agent_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(agent_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _observation_summary(
    action: Mapping[str, Any],
    observation: str,
    command: Mapping[str, Any] | None,
) -> str:
    """A short progress line for the handoff state, never file contents."""

    kind = str(action.get("action"))
    path = str(action.get("path") or "")
    if kind in {"read_file", "write_file", "delete_file"}:
        if kind == "read_file":
            first = observation.splitlines()[0] if observation else ""
            return f"read_file {path}: {first[:160]}"
        return f"{kind} {path}"
    if kind == "run":
        argv = []
        if command is not None:
            argv = [str(item) for item in (command.get("command") or [])]
        if not argv:
            argv = [str(item) for item in (action.get("command") or [])]
        exit_code = command.get("exit_code") if command else "?"
        return f"run {shlex.join(argv)} -> exit {exit_code}"
    first = observation.splitlines()[0] if observation else ""
    return f"{kind}: {first[:200]}"


def _cap(text: str, limit: int = MAX_OBSERVATION) -> str:
    if len(text) <= limit:
        return text
    return (
        text[:limit]
        + f"\n... [output truncated, {len(text)} chars; rerun with a "
        "narrower command or read the file with read_file]"
    )


def _looks_like_tool_markup(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "<｜｜dsml｜｜",
            "<|",
            "<tool_call",
            "<function_call",
            "<system_warning",
        )
    )


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
        if max_steps is not None:
            steps = max(1, int(max_steps))
        elif env_steps.isdigit() and int(env_steps) > 0:
            steps = int(env_steps)
        else:
            steps = 0  # no step limit; context drives sessions
        self.max_steps = min(steps, 5_000)
        env_sessions = os.environ.get(
            "FORGEL_AGENT_MAX_SESSIONS", ""
        ).strip()
        sessions = (
            int(env_sessions) if env_sessions.isdigit() else MAX_SESSIONS
        )
        self.max_sessions = max(1, min(sessions, 20))

    def _context_window(self, layout: ProjectLayout) -> int:
        try:
            config = load_project_config(layout.control)
        except ConfigError:
            config = None
        if config is not None:
            return config.models.context_window
        return self.settings.context_window

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
        # Each attempt starts from the current HEAD. The review is state-based
        # and uses the attributed files, not a commit range, so unrelated
        # commits between attempts never enter the review.
        base_sha = git_ops.head_sha(repo)
        preexisting = set(git_ops.status_paths(repo))
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
                assumptions,
                context_stats,
                failure_kind,
                test_removals,
            ) = self._converse(
                layout, repo, repo_id, task, model, runner, environment
            )
        finally:
            stack.close()
        previous_result = dict(task.get("result") or {})
        previous_files = [
            str(item)
            for item in (previous_result.get("files_changed") or [])
        ]
        dirty = set(git_ops.status_paths(repo))
        carried: set[str] = set()
        for item in previous_files:
            if item.endswith("/"):
                carried |= {
                    path for path in dirty if path.startswith(item)
                }
            elif item in dirty:
                carried.add(item)
        changed = sorted(
            (dirty - preexisting) | set(touched) | carried
        )
        commit_sha = ""
        if status == "done":
            try:
                if changed:
                    commit_sha = git_ops.commit_paths(
                        repo, changed, f"Agent: {task['title']}"
                    )
            except git_ops.GitOperationError as exc:
                status = "failed"
                failure_kind = "infrastructure"
                summary += f"; commit failed: {exc}"
        if not changed:
            changed = sorted(set(touched))

        files_changed = changed
        attributed_files = sorted(
            set(previous_files) | set(files_changed)
        )
        previous_git = (
            previous_result.get("git")
            if isinstance(previous_result.get("git"), dict)
            else {}
        )
        attributed_commits = [
            str(item)
            for item in (previous_git.get("commits") or [])
        ]
        previous_commit = str(previous_git.get("commit") or "")
        if previous_commit and previous_commit not in attributed_commits:
            attributed_commits.append(previous_commit)
        if commit_sha and commit_sha not in attributed_commits:
            attributed_commits.append(commit_sha)
        previous_removals = [
            item
            for item in (previous_result.get("test_removals") or [])
            if isinstance(item, dict)
        ]
        merged_removals = {
            str(item.get("test", "")): item
            for item in previous_removals + test_removals
            if item.get("test")
        }
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
            assumptions,
            context_stats,
            test_removals,
        )
        tasks.update_task(
            layout,
            str(task["id"]),
            status="done" if status == "done" else "failed",
            finished_at=_now(),
            result={
                **previous_result,
                "summary": summary,
                "files_changed": attributed_files,
                "commands": commands,
                "test_output": _cap(test_output, 6000),
                "assumptions": assumptions,
                "context": context_stats,
                "test_removals": list(merged_removals.values()),
                "git": {
                    "base": base_sha,
                    "head": git_ops.head_sha(repo),
                    "commit": commit_sha,
                    "commits": attributed_commits,
                },
                "failure": (
                    {"kind": failure_kind, "message": summary}
                    if status == "failed"
                    else {}
                ),
                "report": _ref(layout, report),
            },
        )
        try:
            if (layout.control / ".git").exists():
                if layout.is_linked:
                    task_path = tasks.task_path(
                        layout, str(task["id"])
                    )
                    refs = [_ref(layout, report)]
                    try:
                        refs.append(
                            str(task_path.relative_to(layout.root))
                        )
                    except ValueError:
                        pass
                    git_ops.commit_paths(
                        layout.root,
                        refs,
                        f"Agent report: {task['title']}",
                    )
                else:
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
        if status == "failed":
            log(
                f"[agent] {project['id']}: task {task['id']}: failed — "
                f"{summary[:200]}"
            )
        else:
            log(f"[agent] {project['id']}: task {task['id']}: {status}")
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
        list[str],
        dict[str, Any],
        list[dict[str, str]],
    ]:
        """Run the model loop and the final test, returning the run state.

        The loop is session-based: when the estimated prompt size approaches
        the context budget, the run writes a durable state file and starts a
        new session from it. The step cap is a hard loop guard, not a normal
        session boundary. The model never manages token counts or asks a human
        to continue.
        """

        window = self._context_window(layout)
        budget: ContextBudget = budget_for(window)
        model_calls = 0
        estimated_input_tokens = 0
        provider_input_tokens = 0
        provider_output_tokens = 0
        state_path = layout.artifact(
            f"docs/program/agent/{task['id']}.state.md"
        )
        state_ref = _ref(layout, state_path) if state_path.exists() else ""
        task_prompt = self._task_prompt(layout, task, repo_id, repo)
        if state_path.exists():
            previous = state_path.read_text(encoding="utf-8")
            task_prompt += (
                "\n\n## Previous session state\n\n" + previous
            )
        messages: list[ModelMessage] = [
            ModelMessage("system", SYSTEM_PROMPT),
            ModelMessage("user", task_prompt),
        ]
        actions: list[str] = []
        commands: list[dict[str, Any]] = []
        touched: set[str] = set()
        recent: list[str] = []
        assumptions = [
            str(item).strip()
            for item in task.get("assumptions", [])
            if str(item).strip()
        ]
        test_removals: list[dict[str, str]] = []
        status = "failed"
        summary = "agent did not finish within the session limit"
        failure_kind = "agent"
        invalid = 0
        markup_retries = 0
        steps = 0
        sessions = 0
        compactions = 0
        signatures: dict[str, int] = {}

        def handoff(session: int) -> tuple[list[ModelMessage], str]:
            changed = sorted(
                set(touched) | set(git_ops.status_paths(repo))
            )
            state = SessionState(
                task_id=str(task["id"]),
                title=str(task["title"]),
                session=session,
                requirements=[
                    str(item) for item in task.get("requirements", [])
                ],
                acceptance=[
                    str(item) for item in task.get("acceptance", [])
                ],
                constraints=[
                    str(item) for item in task.get("constraints", [])
                ],
                assumptions=list(assumptions),
                files_changed=changed,
                actions=list(actions),
                commands=list(commands),
                observations=list(recent),
            )
            max_state_tokens = max(512, int(window * 0.05))
            write_text(
                state_path,
                state.to_markdown(
                    max_tokens=max_state_tokens, model=model
                ),
            )
            return (
                [
                    ModelMessage("system", SYSTEM_PROMPT),
                    ModelMessage("user", self._task_prompt(
                        layout, task, repo_id, repo
                    ) + "\n\n" + handoff_prompt(
                        state,
                        max_tokens=max_state_tokens,
                        model=model,
                    )),
                ],
                _ref(layout, state_path),
            )

        terminal = False
        for session in range(1, self.max_sessions + 1):
            sessions = session
            handed_off = False
            session_steps = 0
            while True:
                if self.max_steps and session_steps >= self.max_steps:
                    status = "failed"
                    failure_kind = "agent"
                    summary = (
                        "operator step limit reached "
                        f"({self.max_steps})"
                    )
                    terminal = True
                    break
                session_steps += 1
                steps += 1
                estimated_input_tokens += budget.usage(messages, model)
                try:
                    raw = self.client.complete(messages, model=model)
                except ModelError as exc:
                    status = "failed"
                    summary = f"model call failed: {exc}"
                    failure_kind = "infrastructure"
                    terminal = True
                    break
                model_calls += 1
                usage = getattr(self.client, "last_usage", None)
                if isinstance(usage, dict):
                    try:
                        provider_input_tokens += int(
                            usage.get("prompt_tokens", 0)
                        )
                        provider_output_tokens += int(
                            usage.get("completion_tokens", 0)
                        )
                    except (TypeError, ValueError):
                        pass
                action = parse_action(raw)
                if action is None:
                    if (
                        _looks_like_tool_markup(raw)
                        and markup_retries < 2
                    ):
                        messages.append(
                            ModelMessage("assistant", raw)
                        )
                        messages.append(
                            ModelMessage(
                                "user",
                                "Return exactly one JSON action object. "
                                "Do not use tool-call markup, XML or "
                                "provider-specific function calls.",
                            )
                        )
                        markup_retries += 1
                        continue
                    invalid += 1
                    messages.append(ModelMessage("assistant", raw))
                    messages.append(
                        ModelMessage(
                            "user",
                            "Invalid reply. Return exactly one JSON action "
                            "object using one of: list_files, read_file, "
                            "write_file, delete_file, run, done, fail. "
                            "Do not return prose, a plan, tool-call markup "
                            "or any other shape.",
                        )
                    )
                    if invalid >= MAX_INVALID_REPLIES:
                        status = "failed"
                        summary = (
                            "the model did not return a valid action "
                            f"after {invalid} attempts"
                        )
                        terminal = True
                        break
                    continue
                invalid = 0
                markup_retries = 0
                kind = str(action["action"])
                messages.append(
                    ModelMessage(
                        "assistant",
                        json.dumps(action, ensure_ascii=False),
                    )
                )
                if kind == "done":
                    status = "done"
                    summary = str(action.get("summary", "")).strip() or (
                        "agent reported done"
                    )
                    for item in action.get("assumptions", []):
                        value = str(item).strip()
                        if value and value not in assumptions:
                            assumptions.append(value)
                    for item in action.get("test_removals", []):
                        if not isinstance(item, dict):
                            continue
                        test = str(item.get("test", "")).strip()
                        reason = str(item.get("reason", "")).strip().lower()
                        replacement = str(
                            item.get("replacement", "")
                        ).strip()
                        if (
                            test
                            and reason in {"removed", "replaced", "wrong"}
                        ):
                            test_removals.append(
                                {
                                    "test": test,
                                    "reason": reason,
                                    "replacement": replacement,
                                }
                            )
                    terminal = True
                    break
                if kind == "fail":
                    status = "failed"
                    summary = str(action.get("reason", "")).strip() or (
                        "agent reported failure"
                    )
                    terminal = True
                    break
                signature = self._signature(action)
                repeats = 0
                if kind in {"read_file", "write_file", "run"}:
                    repeats = signatures.get(signature, 0) + 1
                    signatures[signature] = repeats
                    if repeats >= MAX_REPEATED_ACTIONS:
                        status = "failed"
                        failure_kind = "agent"
                        summary = (
                            f"repeated action loop: {signature}"
                        )
                        terminal = True
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
                recent.append(
                    _observation_summary(action, observation, command)
                )
                recent = recent[-6:]
                messages.append(
                    ModelMessage(
                        "user", f"OBSERVATION:\n{_cap(observation)}"
                    )
                )
                if repeats >= 3:
                    warning = (
                        "You have repeated this action several times. Its "
                        "result is already above. Do not repeat it; make the "
                        "edit or call done."
                    )
                    messages.append(ModelMessage("user", warning))
                    recent.append(warning)
                if kind in {"write_file", "delete_file"} and (
                    observation.startswith(("wrote ", "deleted "))
                ):
                    signatures.clear()
                if budget.should_compact(messages, model):
                    if session < self.max_sessions:
                        used = budget.usage(messages, model)
                        messages, state_ref = handoff(session)
                        invalid = 0
                        compactions += 1
                        handed_off = True
                        print(
                            f"[agent] {task['id']}: context handoff to "
                            f"session {session + 1} "
                            f"(~{used}/{budget.usable} tokens)"
                        )
                        break
                    status = "failed"
                    failure_kind = "agent"
                    summary = "context session limit reached"
                    terminal = True
                    break
            if terminal:
                break
            if not handed_off:
                status = "failed"
                failure_kind = "agent"
                summary = "agent stopped without a terminal action"
                break

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
                    failure_kind = "qa"
                    summary += f"; final test command exited {code}"
        context_stats = {
            "window": window,
            "usable": budget.usable,
            "sessions": sessions,
            "compactions": compactions,
            "model_calls": model_calls,
            "estimated_input_tokens": estimated_input_tokens,
            "provider_input_tokens": provider_input_tokens,
            "provider_output_tokens": provider_output_tokens,
            "estimated_tokens": budget.usage(messages, model),
            "state": state_ref if compactions else "",
        }
        return (
            status,
            summary,
            steps,
            actions,
            commands,
            touched,
            test_output,
            assumptions,
            context_stats,
            failure_kind,
            test_removals,
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
        assumptions = "\n".join(
            f"- {item}" for item in task.get("assumptions", [])
        ) or "- none"
        feedback = "\n".join(
            f"- {item}"
            for item in (
                (task.get("result") or {}).get("feedback") or []
            )
        )
        feedback_section = (
            f"\nPrevious attempt feedback (address it):\n{feedback}\n"
            if feedback
            else ""
        )
        test_command = task.get("test_command") or []
        tree = self._list(repo)
        branch = git_ops.current_branch(repo)
        answer_language = language.name(str(task.get("language") or ""))
        return f"""TASK: {task['title']}

Requirements:
{requirements}

Acceptance criteria:
{acceptance}

Constraints:
{constraints}

Assumptions already recorded at intake (do not re-ask):
{assumptions}
{feedback_section}
Final test command: {json.dumps(test_command)}
Repository: {repo_id} at {repo} (branch {branch})

Write done.summary, done.assumptions and fail.reason in {answer_language}.
The user asked for this task in that language; keep the report readable to them.

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
                return read_text_page(
                    path,
                    action.get("offset", 1),
                    action.get("limit", READ_DEFAULT_LINES),
                    display=str(action.get("path") or ""),
                ), None
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
                if self._looks_like_file_inspection(command):
                    return (
                        "File contents must be read with read_file. "
                        "run is only for tests and build commands; "
                        "this command was not executed.",
                        None,
                    )
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

    @staticmethod
    def _looks_like_file_inspection(command: Sequence[str]) -> bool:
        executable = Path(command[0]).name
        if executable.startswith("python") and "-c" in command:
            index = command.index("-c")
            code = " ".join(command[index + 1:])
            return any(
                marker in code
                for marker in (
                    "open(",
                    "read_text",
                    "readlines",
                    ".read(",
                    "write_text",
                    "Path(",
                )
            )
        return False

    @staticmethod
    def _signature(action: Mapping[str, Any]) -> str:
        kind = str(action.get("action"))
        path = str(action.get("path") or "")
        if kind in {"read_file", "list_files", "delete_file"}:
            return f"{kind}:{path}"
        if kind == "write_file":
            content = str(action.get("content") or "")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
            return f"write_file:{path}:{digest}"
        if kind == "run":
            return "run:" + json.dumps(
                action.get("command"), sort_keys=True, ensure_ascii=False
            )
        return kind

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
        if executable == "docker":
            if len(command) < 2 or command[1] != "compose":
                raise AgentError("only docker compose is allowed")
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
        assumptions: list[str],
        context_stats: dict[str, Any],
        test_removals: list[dict[str, str]],
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
        assumption_lines = (
            "\n".join(f"- {item}" for item in assumptions) or "- none"
        )
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

## Assumptions

{assumption_lines}

## Test Removals

{chr(10).join(f"- {item['test']}: {item['reason']}" + (f" -> {item['replacement']}" if item.get('replacement') else "") for item in test_removals) or "- none"}

## Context

- Window limit: {context_stats.get('window', 0)} tokens (usable {context_stats.get('usable', 0)})
- Sessions: {context_stats.get('sessions', 1)}
- Handoffs: {context_stats.get('compactions', 0)}
- Model calls: {context_stats.get('model_calls', 0)}
- Estimated input tokens (all calls): {context_stats.get('estimated_input_tokens', 0)}
- Provider input/output tokens: {context_stats.get('provider_input_tokens', 0)} / {context_stats.get('provider_output_tokens', 0)}
- Estimated prompt at the end: {context_stats.get('estimated_tokens', 0)} tokens
{('- State: `' + str(context_stats.get('state')) + '`') if context_stats.get('state') else '- State: not needed'}

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
