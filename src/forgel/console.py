"""Local console channel.

The Telegram gateway and the console are two channels over one command
router. A local user needs no bot token, no VPS and no network round-trip:
the same `/new`, `/adopt`, `/repo`, `/tasks`, `/status`, `/approve` commands
work against the local daemon.

The console is deliberately thin: it reads a line, passes it to
:class:`forgel.chat.CommandRouter`, prints the reply, and runs one daemon
cycle so a queued project or task starts immediately.
"""

from __future__ import annotations

from typing import Callable

from .agent import ProjectAgent
from .chat import CommandRouter
from .config import Settings
from .control import is_paused
from .daemon import run_once
from .ledger import Ledger
from .model import build_model_client
from .projects import ProjectError, resolve_project

PROMPT = "forgel> "
QUIT = {"/quit", "/exit"}


def run_console(
    settings: Settings,
    ledger: Ledger,
    project_id: str = "",
    daemon: bool = True,
    actor: str = "local",
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    agent: ProjectAgent | None = None,
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
                "Model not configured: commands work, free text is disabled. "
                "Set FORGEL_MODEL_API_KEY or /secret set model.api_key."
            )
        else:
            agent = ProjectAgent(settings, ledger, client)
    router = CommandRouter(
        settings, ledger, daemon_enabled=daemon, agent=agent
    )
    output("Forgel console. /help for commands, /quit to exit.")

    daemon_note = (
        "the daemon runs after each command"
        if daemon
        else "commands only"
    )
    output(f"Mode: {daemon_note}.")
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
        try:
            reply = router.handle(chat_id, text, actor)
        except Exception as exc:  # noqa: BLE001 - the console must stay up
            output(f"error: {exc}")
            continue
        if reply.text:
            output(reply.text)
        if daemon and not is_paused(settings.home):
            try:
                processed = run_once(settings, ledger, log=output)
            except Exception as exc:  # noqa: BLE001 - report, then continue
                output(f"daemon error: {exc}")
                continue
            if processed:
                output(
                    "Processed: " + ", ".join(processed)
                    + ". /status for details."
                )
    output("Bye.")
