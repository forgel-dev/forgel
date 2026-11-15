"""Local console channel.

One client, no separate utilities: start `forgel` in a repository, `/adopt`
it, describe the milestone, and watch the daemon work. The console and the
Telegram gateway share one command router, so every command behaves the same.

After a command the console drains runnable work until it reaches a real stop:
a task awaiting acceptance, a plan that is stalled or done, or a retry that is
scheduled for later. A scheduled retry is waited out (Ctrl-C returns to the
prompt); an idle home returns immediately.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Callable

try:  # line editing and history for the prompt; no dependency
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform without readline
    readline = None  # type: ignore[assignment]

from .agent import ProjectAgent, append_history
from .chat import CommandRouter
from .config import Settings
from .control import is_paused
from .daemon import next_retry_wait, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .planner import plan_status
from .projects import ProjectError, resolve_project
from .tasks import latest_task, list_tasks, retry_moment

PROMPT = "forgel> "
QUIT = {"/quit", "/exit", "quit", "exit", "bye"}


def _report_state(
    ledger: Ledger, output: Callable[[str], None]
) -> None:
    project_id = ledger.get_session(0)
    if not project_id:
        return
    project = ledger.get_project(project_id)
    if project is None:
        return
    layout = ProjectLayout.detect(project["workspace"])
    summary = plan_status(layout)
    if summary["status"] not in {"none", "running"}:
        output(
            f"Milestone {summary['plan_id']}: {summary['status']}."
        )
    task = latest_task(layout)
    if task is None:
        return
    status = task.get("status")
    if status == "review":
        output(
            f"Task {task['id']} awaits your decision: say \"accept\" "
            "or tell me what to change."
        )
    elif status == "pending":
        moment = retry_moment(task)
        if moment is not None:
            output(
                f"Task {task['id']} retries at "
                f"{moment.strftime('%H:%M UTC')}."
            )
    elif status == "failed":
        output(
            f"Task {task['id']} failed: "
            + str((task.get("result") or {}).get("summary", ""))[:200]
        )


def _drain(
    settings: Settings,
    ledger: Ledger,
    output: Callable[[str], None],
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Run until no immediately runnable work remains.

    A scheduled retry is waited out; Ctrl-C stops the wait and returns to the
    prompt without losing the task.
    """

    while True:
        try:
            processed = run_once(settings, ledger, log=output)
        except Exception as exc:  # noqa: BLE001 - the console must stay up
            output(f"daemon error: {exc}")
            return
        if processed:
            continue
        wait = next_retry_wait(ledger)
        if wait is None:
            _report_state(ledger, output)
            return
        moment = None
        for project in ledger.list_projects():
            layout = ProjectLayout.detect(project["workspace"])
            task = latest_task(layout)
            if task is not None:
                moment = retry_moment(task) or moment
        when = (
            f" at {moment.strftime('%H:%M UTC')}" if moment else ""
        )
        output(
            f"Waiting for a scheduled retry{when} "
            f"(about {wait / 60:.0f} min). Ctrl-C returns to the prompt."
        )
        try:
            sleep_fn(wait)
        except KeyboardInterrupt:
            output("Stopped waiting; the retry stays scheduled.")
            _report_state(ledger, output)
            return


def _flush_pending_input() -> None:
    """Drop keys typed while the daemon was working, before the prompt."""

    try:
        import termios
    except ImportError:  # pragma: no cover - non-POSIX
        return
    try:
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (OSError, ValueError):
        return


COMMANDS = (
    "/help",
    "/adopt",
    "/new",
    "/use",
    "/projects",
    "/status",
    "/plan",
    "/tasks",
    "/task",
    "/repo",
    "/secret",
    "/config",
    "/peak",
    "/pause",
    "/resume",
    "/github",
    "/deploy",
    "/quit",
    "/exit",
)


def _completion_options(buffer: str, ledger: Ledger) -> list[str]:
    stripped = buffer.lstrip()
    if stripped.startswith("/use "):
        return [str(item["id"]) for item in ledger.list_projects()]
    if stripped.startswith("/"):
        return list(COMMANDS)
    return []


def _setup_readline(settings: Settings, ledger: Ledger) -> None:
    if readline is None:
        return
    history = settings.home / "console_history"
    try:
        settings.home.mkdir(parents=True, exist_ok=True)
        readline.read_history_file(history)
    except OSError:
        pass
    readline.set_history_length(500)

    def completer(text: str, state: int) -> str | None:
        options = _completion_options(
            readline.get_line_buffer(), ledger
        )
        matches = [item for item in options if item.startswith(text)]
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")


def _save_history(settings: Settings) -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(settings.home / "console_history")
    except OSError:
        return


def _prompt_text(ledger: Ledger, chat_id: int) -> str:
    project_id = ledger.get_session(chat_id)
    if project_id:
        project = ledger.get_project(project_id)
        if project is not None:
            return f"forgel[{project['name']}]> "
    return PROMPT


def _read_input(
    input_fn: Callable[[str], str], prompt: str, interactive: bool
) -> str:
    line = input_fn(prompt)
    if not interactive:
        return line
    parts: list[str] = []
    while line.rstrip().endswith("\\"):
        parts.append(line.rstrip()[:-1])
        line = input_fn("... ")
    parts.append(line)
    return "\n".join(parts)


class _Spinner:
    """A one-line activity indicator while the model is working."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "_Spinner":
        if not self.enabled:
            return self
        self._thread = threading.Thread(
            target=self._spin, daemon=True
        )
        self._thread.start()
        return self

    def _spin(self) -> None:
        frames = "|/-\\"
        index = 0
        while not self._stop.wait(0.15):
            sys.stdout.write(
                "\r\033[2m" + frames[index % len(frames)] + " working…\033[0m"
            )
            sys.stdout.flush()
            index += 1

    def __exit__(self, *exc_info: object) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


def _task_snapshot(layout: ProjectLayout) -> dict[str, str]:
    return {
        str(item["id"]): str(item.get("status", ""))
        for item in list_tasks(layout)
    }


def _task_update_text(
    layout: ProjectLayout, before: dict[str, str]
) -> str:
    """Summarize tasks whose status changed during this drain."""

    items = list_tasks(layout)
    lines: list[str] = []
    for item in items:
        task_id = str(item["id"])
        status = str(item.get("status", ""))
        if before.get(task_id) == status:
            continue
        result = item.get("result") or {}
        summary = str(result.get("summary") or "").strip()
        files = [str(value) for value in result.get("files_changed") or []]
        report = str(result.get("report") or "").strip()
        line = f"Task `{task_id}`: **{status}**"
        if summary:
            line += f" — {summary}"
        if files:
            line += "\nFiles: " + ", ".join(f"`{value}`" for value in files)
        if report:
            line += f"\nReport: `{report}`"
        lines.append(line)
    return "\n\n".join(lines)


def run_console(
    settings: Settings,
    ledger: Ledger,
    project_id: str = "",
    daemon: bool = True,
    actor: str = "local",
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    agent: ProjectAgent | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Run the local console until EOF or ``/quit``."""

    chat_id = 0
    if project_id:
        try:
            project = resolve_project(ledger, project_id)
        except ProjectError as exc:
            output(f"error: {exc}")
            return
        ledger.set_session(chat_id, str(project["id"]))
        output(f"Selected {project['id']}.")

    if agent is None:
        client = build_model_client(settings.home, log=output)
        if client is None:
            candidates = [
                Path.cwd() / ".env.local",
                settings.home / ".env.local",
            ]
            existing = [path for path in candidates if path.exists()]
            output("Forgel is not fully configured:")
            if existing:
                targets = " or ".join(str(path) for path in existing)
                output(
                    f"  model: set FORGEL_MODEL_API_KEY in {targets}"
                )
                output(
                    "         (`forgel setup` creates ./.env.local; "
                    "it is never committed)"
                )
            else:
                output(
                    "  model: set FORGEL_MODEL_API_KEY in the environment, "
                    "./.env.local, or "
                    f"{settings.home / '.env.local'} "
                    "(`forgel setup` creates ./.env.local)"
                )
            output(
                "  github: optional locally; needed to publish branches "
                "or create repositories"
            )
            output(
                "Commands and /adopt work; planning and code changes need "
                "the model. `forgel doctor` checks the rest."
            )
        else:
            agent = ProjectAgent(settings, ledger, client)
    router = CommandRouter(
        settings, ledger, daemon_enabled=daemon, agent=agent
    )
    output(
        "Forgel console. Describe the work or use /help; "
        "/quit exits."
    )
    output(
        "Mode: "
        + (
            "after each command the daemon runs until it needs you"
            if daemon
            else "commands only"
        )
        + "."
    )
    interactive = (
        input_fn is input
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )
    if interactive:
        _setup_readline(settings, ledger)
        selected = ledger.get_session(chat_id)
        project = ledger.get_project(selected) if selected else None
        output(
            f"Project: {project['name'] if project else 'none'}  ·  "
            f"cwd: {Path.cwd()}"
        )
        output(
            "Tab completes commands; ↑/↓ history; \\ continues a line; "
            "Ctrl-C stops input; Ctrl-D exits."
        )
    try:
        while True:
            if interactive:
                _flush_pending_input()
            prompt = (
                _prompt_text(ledger, chat_id) if interactive else PROMPT
            )
            try:
                line = _read_input(input_fn, prompt, interactive)
            except EOFError:
                break
            except KeyboardInterrupt:
                if interactive:
                    output("")
                    continue
                break
            text = line.strip()
            if not text:
                continue
            if text in QUIT:
                break
            if router.agent is None:
                client = build_model_client(settings.home, log=output)
                if client is not None:
                    router.agent = ProjectAgent(settings, ledger, client)
            try:
                with _Spinner(interactive):
                    reply = router.handle(chat_id, text, actor)
            except KeyboardInterrupt:
                if interactive:
                    output("Stopped.")
                    continue
                raise
            except Exception as exc:  # noqa: BLE001 - keep the console up
                output(f"error: {exc}")
                continue
            if reply.text:
                output(reply.text)
                if interactive:
                    output("")
            if daemon and not is_paused(settings.home):
                selected = ledger.get_session(chat_id)
                project = (
                    ledger.get_project(selected) if selected else None
                )
                layout = (
                    ProjectLayout.detect(project["workspace"])
                    if project is not None
                    else None
                )
                before = (
                    _task_snapshot(layout) if layout is not None else {}
                )
                try:
                    _drain(settings, ledger, output, sleep_fn=sleep_fn)
                except KeyboardInterrupt:
                    if interactive:
                        output("Stopped; back to the prompt.")
                        continue
                    raise
                if layout is not None:
                    update = _task_update_text(layout, before)
                    if update:
                        output(update)
                        append_history(
                            layout,
                            "assistant",
                            update,
                            actor,
                            session=str(chat_id),
                        )
    finally:
        if interactive:
            _save_history(settings)
    output("Bye.")
