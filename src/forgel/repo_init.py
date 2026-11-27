"""Repository initialization: establish and verify the repository test gate.

The model inspects one repository, determines the command or commands that
run its tests, and runs them before reporting. A new repository may need a
minimal test setup first; an existing repository is only read and run, never
modified. A command counts only when the process starts and returns; test
failures and an empty suite are acceptable, a missing executable or a timeout
is not.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .coding_agent import ALLOWED_EXECUTABLES, NPM_ALLOWED
from .model import ModelClient, ModelError, ModelMessage
from .model_output import json_objects

MAX_OUTPUT = 6_000
MAX_FILE_BYTES = 200_000
READ_BYTES = 100_000
SKIP_DIRS = {
    ".git",
    ".forgel",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
}
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
INVALID_EXIT_CODES = {124, 125, 126, 127}

SYSTEM_PROMPT = """You initialize one repository for a project.

Your job is to establish the command or commands that run this repository's
test suite, and to prove that they run. You may inspect files, run commands,
and, only for a new repository, write files. You never write to an existing
repository and never touch git.

Rules:
- Determine the stack from the repository and the project. For a new
  repository without a test setup, create the minimal configuration and an
  empty test set, then run the test command with that empty set. For an
  existing repository, use the command it already has; do not create a new
  test framework or rewrite its setup.
- Run every command you intend to report. A command is valid when the process
  starts and returns, whatever its exit code: tests may be absent or failing.
  A missing executable or a timeout is not valid.
- Prefer one command that runs the whole suite. If several commands are
  needed, return them in execution order.
- If no command can be established, report an empty list.

Reply with exactly one JSON object per turn:
{"action": "list_files", "path": "."}
{"action": "read_file", "path": "relative/path"}
{"action": "write_file", "path": "relative/path", "content": "..."}
{"action": "run", "command": ["command", "arg"], "timeout": 600}
{"action": "done", "test": ["command string", "another command"]}

On done, list only commands you actually ran and that were valid. Return JSON
only; do not emit tool-call markup or prose.
"""


class RepoInitError(RuntimeError):
    """The repository test gate could not be established."""


class RepoInitAgent:
    def __init__(
        self,
        client: ModelClient | None,
        model: str = "",
        log: Callable[[str], None] = print,
    ) -> None:
        self.client = client
        self.model = model
        self.log = log
        self._valid: set[str] = set()

    def commands(
        self,
        repo: Path,
        repo_id: str,
        *,
        allow_write: bool,
        preset: str = "",
    ) -> list[str]:
        if self.client is None:
            return []
        self._valid = set()
        repo = repo.resolve()
        if not repo.is_dir():
            return []
        messages = [
            ModelMessage("system", SYSTEM_PROMPT),
            ModelMessage(
                "user",
                self._task_prompt(
                    repo, repo_id, allow_write, preset
                ),
            ),
        ]
        while True:
            try:
                raw = self.client.complete(
                    messages, model=self.model or None
                )
            except ModelError as exc:
                self.log(f"[init] {repo_id}: model failed: {exc}")
                return []
            objects = json_objects(raw)
            action = objects[0] if objects else None
            if not isinstance(action, dict):
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "Return exactly one JSON action object with an "
                        "action from the list. No prose, no tool markup.",
                    )
                )
                continue
            kind = str(action.get("action") or "").strip()
            messages.append(
                ModelMessage(
                    "assistant",
                    json.dumps(action, ensure_ascii=False),
                )
            )
            if kind == "done":
                reported = action.get("test")
                if not isinstance(reported, list):
                    return []
                return self._accepted(reported)
            if kind == "fail":
                return []
            observation = self._execute(
                repo, action, allow_write=allow_write
            )
            messages.append(ModelMessage("user", observation))
        self.log(f"[init] {repo_id}: step limit reached")
        return []

    def _accepted(self, reported: list[Any]) -> list[str]:
        accepted: list[str] = []
        for item in reported:
            text = str(item).strip()
            if not text:
                continue
            try:
                argv = shlex.split(text)
            except ValueError:
                continue
            key = shlex.join(argv)
            if key in self._valid and key not in accepted:
                accepted.append(key)
        return accepted

    def _task_prompt(
        self,
        repo: Path,
        repo_id: str,
        allow_write: bool,
        preset: str,
    ) -> str:
        return (
            f"Repository: {repo_id} at {repo}\n"
            f"New repository: {'yes' if allow_write else 'no'}\n"
            f"Preset: {preset or 'none'}\n"
            f"Writable: {'yes' if allow_write else 'no'}\n\n"
            "Files:\n"
            f"{self._tree(repo)}\n\n"
            "Establish and run the test command or commands now."
        )

    def _tree(self, repo: Path) -> str:
        paths: list[str] = []
        for root, dirs, files in os.walk(repo):
            dirs[:] = sorted(
                name for name in dirs if name not in SKIP_DIRS
            )
            for name in sorted(files):
                path = Path(root) / name
                try:
                    relative = path.relative_to(repo).as_posix()
                except ValueError:
                    continue
                paths.append(relative)
                if len(paths) >= 300:
                    return "\n".join(paths) + "\n..."
        return "\n".join(paths) or "(empty)"

    def _execute(
        self,
        repo: Path,
        action: Mapping[str, Any],
        *,
        allow_write: bool,
    ) -> str:
        kind = str(action.get("action") or "").strip()
        try:
            if kind == "list_files":
                return self._tree(repo)
            if kind == "read_file":
                path = self._path(repo, action.get("path"))
                if not path.is_file():
                    return f"file not found: {action.get('path')}"
                data = path.read_bytes()
                if len(data) > READ_BYTES:
                    data = data[:READ_BYTES]
                if b"\x00" in data:
                    return "binary file; not displayed"
                return data.decode("utf-8", "replace")
            if kind == "write_file":
                if not allow_write:
                    return "writing is not allowed for this repository"
                path = self._path(repo, action.get("path"))
                content = action.get("content")
                if not isinstance(content, str):
                    return "write_file needs a string content"
                raw = content.encode("utf-8")
                if len(raw) > MAX_FILE_BYTES:
                    return f"file too large ({len(raw)} bytes)"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return (
                    "wrote "
                    + str(len(raw))
                    + " bytes to "
                    + path.relative_to(repo).as_posix()
                )
            if kind == "run":
                return self._run(repo, action)
            return f"unknown action: {kind}"
        except (OSError, ValueError) as exc:
            return f"error: {exc}"

    def _path(self, repo: Path, value: Any) -> Path:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("a path is required")
        path = (repo / raw).resolve()
        if path != repo and repo not in path.parents:
            raise ValueError("the path escapes the repository")
        if ".git" in path.relative_to(repo).parts:
            raise ValueError("the .git directory is not accessible")
        return path

    def _run(self, repo: Path, action: Mapping[str, Any]) -> str:
        command = action.get("command")
        if isinstance(command, str):
            command = shlex.split(command)
        if not isinstance(command, list) or not all(
            isinstance(item, str) for item in command
        ):
            return "run needs a command list"
        command = [str(item) for item in command if str(item).strip()]
        if not command:
            return "the command is empty"
        executable = Path(command[0]).name
        if (
            executable not in ALLOWED_EXECUTABLES
            and not executable.startswith("python")
        ):
            return f"command {executable!r} is not allowed"
        if executable in {"git", "docker"}:
            return f"command {executable!r} is not allowed during setup"
        if executable == "npm" and (
            len(command) < 2 or command[1] not in NPM_ALLOWED
        ):
            return "only npm test/run/install are allowed"
        if any(
            item in {"|", ">", ">>", "<", "&&", "||", ";"}
            for item in command
        ):
            return "shell operators are not allowed"
        timeout = action.get("timeout", 600)
        try:
            seconds = max(30.0, min(float(timeout), 900.0))
        except (TypeError, ValueError):
            seconds = 600.0
        env = {
            key: os.environ[key]
            for key in SAFE_ENV_KEYS
            if key in os.environ
        }
        try:
            completed = subprocess.run(
                command,
                cwd=str(repo),
                env=env,
                capture_output=True,
                text=True,
                timeout=seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return f"$ {shlex.join(command)}\ntimed out after {seconds:g}s"
        except (OSError, subprocess.SubprocessError) as exc:
            return f"$ {shlex.join(command)}\ncannot run: {exc}"
        output = (completed.stdout + completed.stderr)[-MAX_OUTPUT:]
        if completed.returncode not in INVALID_EXIT_CODES:
            self._valid.add(shlex.join(command))
        return (
            f"$ {shlex.join(command)}\n"
            f"exit code {completed.returncode}\n{output}"
        )
