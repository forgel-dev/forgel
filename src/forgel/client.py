"""Parser and dispatch for the machine-readable client commands.

``forgel.entry`` calls :func:`maybe_dispatch` before the legacy CLI parser.
The new subcommands always belong to the client; ``status``, ``task``,
``plan``, ``pause``, ``resume`` and ``daemon`` are taken over only when
``--json`` is given, so their human-readable behaviour and output are
unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Sequence

from . import client_cli
from .config import Settings
from .ledger import Ledger
from .local_env import LocalEnvError, load_local_env

# Only in the machine-readable client.
CLIENT_COMMANDS = {"say", "projects", "session", "use", "history", "tasks"}
# Existing commands that gain a ``--json`` form.
JSON_COMMANDS = {"status", "task", "plan", "pause", "resume", "daemon"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgel", description="Machine-readable client commands."
    )
    sub = parser.add_subparsers(dest="client_command", required=True)

    def common(name: str, help_text: str, project: bool = True):
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--json", action="store_true")
        item.add_argument("--home", default=None)
        item.add_argument("--session", default=None)
        if project:
            item.add_argument("--project", dest="project_flag", default="")
            item.add_argument("project_id", nargs="?", default="")
        return item

    say = common("say", "Send free text through the command router")
    say.add_argument("--text", default="")
    say.add_argument("words", nargs="*")
    say.add_argument("--actor", default="local")
    say.set_defaults(func=client_cli.say)

    projects = common("projects", "List projects", project=False)
    projects.set_defaults(func=client_cli.projects)

    use = common("use", "Select the active project for a session")
    use.set_defaults(func=client_cli.use)

    session = common("session", "Read or set the session project")
    session.set_defaults(func=client_cli.session)

    history = common(
        "history", "Recent conversation of a session", project=False
    )
    history.add_argument("--limit", type=int, default=20)
    history.set_defaults(func=client_cli.history)

    tasks = common("tasks", "List the task queue of a project")
    tasks.set_defaults(func=client_cli.tasks)

    status = common("status", "Project status")
    status.set_defaults(func=client_cli.status)

    task = common("task", "Decide or queue a task")
    task.add_argument(
        "action", choices=["accept", "reject", "retry", "cancel", "add", "review"]
    )
    task.add_argument("--task", dest="task_id", default="")
    task.add_argument("--actor", default="owner")
    task.add_argument("--notes", default="")
    task.add_argument("--title", default="")
    task.add_argument("--require", action="append", default=[])
    task.add_argument("--accept", action="append", default=[])
    task.add_argument("--constraint", action="append", default=[])
    task.add_argument("--repo", default="")
    task.add_argument("--test-command", dest="test_command", default="")
    task.set_defaults(func=client_cli.task)

    plan = common("plan", "Plan a milestone or show the milestone")
    plan.add_argument("--goal", default="")
    plan.add_argument("--status", action="store_true")
    plan.add_argument("--max-tasks", type=int, default=8)
    plan.add_argument(
        "--release-class",
        choices=["patch", "minor", "major"],
        default="minor",
    )
    plan.add_argument("--dry-run", action="store_true")
    plan.set_defaults(func=client_cli.plan)

    pause = common("pause", "Pause the daemon", project=False)
    pause.set_defaults(func=client_cli.pause)

    resume = common("resume", "Resume the daemon", project=False)
    resume.set_defaults(func=client_cli.resume)

    daemon = common("daemon", "Run the daemon now", project=False)
    daemon.add_argument("--interval", type=float, default=5.0)
    daemon.add_argument("--once", action="store_true", default=True)
    daemon.add_argument("--loop", dest="once", action="store_false")
    daemon.add_argument("--max-cycles", type=int, default=None)
    daemon.set_defaults(func=client_cli.daemon)

    return parser


def _settings(args: argparse.Namespace) -> Settings:
    try:
        load_local_env(Path.cwd(), None)
        home = (
            Path(args.home)
            if getattr(args, "home", None)
            else Path.home() / ".forgel"
        )
        load_local_env(None, home.expanduser())
    except LocalEnvError as exc:
        raise SystemExit(f"error: {exc}") from exc
    return Settings.from_env(getattr(args, "home", None))


def _resolve_project_arg(args: argparse.Namespace) -> None:
    """A ``--project`` value fills the optional positional project id."""

    flag = str(getattr(args, "project_flag", "") or "").strip()
    positional = str(getattr(args, "project_id", "") or "").strip()
    if flag and not positional:
        args.project_id = flag


def run(
    argv: Sequence[str],
    parser_factory: Callable[[], argparse.ArgumentParser] = build_parser,
) -> int:
    """Parse and run one client command."""

    as_json = "--json" in argv
    try:
        args = parser_factory().parse_args(list(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        if code == 0:
            return 0
        if as_json:
            client_cli.write(
                client_cli.envelope(False, "usage", "", "invalid arguments")
            )
        return code or 2
    _resolve_project_arg(args)
    settings = _settings(args)
    ledger = Ledger(settings.db_path)
    try:
        return int(args.func(settings, ledger, args))
    finally:
        ledger.close()


def maybe_dispatch(argv: Sequence[str] | None) -> int | None:
    """Handle the client commands before the legacy CLI parser."""

    arguments = list(argv or [])
    if not arguments:
        return None
    name = arguments[0]
    if name in CLIENT_COMMANDS:
        return run(arguments)
    if name in JSON_COMMANDS and "--json" in arguments:
        return run(arguments)
    return None
