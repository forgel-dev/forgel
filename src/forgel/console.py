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

import time
from typing import Callable

from .agent import ProjectAgent
from .chat import CommandRouter
from .config import Settings
from .control import is_paused
from .daemon import next_retry_wait, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .planner import plan_status
from .projects import ProjectError, resolve_project
from .tasks import latest_task, retry_moment

PROMPT = "forgel> "
QUIT = {"/quit", "/exit"}


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
            f"Task {task['id']} awaits acceptance: "
            f"/task accept {task['id']}"
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
            output(
                "Model not configured: commands work, free text and planning "
                "are disabled. Set FORGEL_MODEL_API_KEY or "
                "/secret set model.api_key."
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
    while True:
        try:
            line = input_fn(PROMPT)
        except (EOFError, KeyboardInterrupt):
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
            reply = router.handle(chat_id, text, actor)
        except Exception as exc:  # noqa: BLE001 - the console must stay up
            output(f"error: {exc}")
            continue
        if reply.text:
            output(reply.text)
        if daemon and not is_paused(settings.home):
            _drain(settings, ledger, output, sleep_fn=sleep_fn)
    output("Bye.")
