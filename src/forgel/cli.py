"""Command-line interface for the M0 skeleton."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .artifacts import ensure_dir, read_json
from .config import Settings
from .ledger import Ledger, new_project_id
from .orchestrator import Orchestrator, StageError

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")


def _settings(args: argparse.Namespace) -> Settings:
    return Settings.from_env(args.home)


def _ledger(settings: Settings) -> Ledger:
    return Ledger(settings.db_path)


def _create_project(
    settings: Settings, ledger: Ledger, name: str, brief: str
) -> str:
    project_id = new_project_id(name)
    workspace = settings.projects_dir / project_id
    ensure_dir(workspace)
    ledger.create_project(project_id, name, brief, str(workspace))
    return project_id


def _print_result(ledger: Ledger, project_id: str) -> None:
    project = ledger.get_project(project_id)
    assert project is not None
    staging_path = Path(project["workspace"]) / "staging.json"
    staging = read_json(staging_path) if staging_path.exists() else {}
    print(f"Project {project_id} is done.")
    if staging:
        print(f"Staging: {staging.get('url', 'unknown')}")
        print(f"Command: {staging.get('command', 'unknown')}")
    print(f"Serve it with: forgel serve {project_id}")


def cmd_init(args: argparse.Namespace) -> int:
    if not _NAME_RE.fullmatch(args.name):
        print(
            "error: name must be 1-64 characters of letters, digits, spaces, "
            "hyphens or underscores",
            file=sys.stderr,
        )
        return 2
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project_id = _create_project(settings, ledger, args.name, args.brief)
        print(project_id)
        return 0
    finally:
        ledger.close()


def cmd_run(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        Orchestrator(settings, ledger).run(args.project_id)
        _print_result(ledger, args.project_id)
        return 0
    except StageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        ledger.close()


def cmd_status(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        checkpoint = ledger.checkpoint(args.project_id) or "none"
        print(f"project:    {project['id']}")
        print(f"name:       {project['name']}")
        print(f"recipe:     {project.get('recipe_id') or 'none'}")
        print(f"workspace:  {project['workspace']}")
        print(f"checkpoint: {checkpoint}")
        print()
        print(f"{'seq':>4}  {'stage':<14} {'status':<10} artifacts")
        for event in ledger.events(args.project_id):
            try:
                refs = json.loads(event["artifact_refs"])
            except json.JSONDecodeError:
                refs = []
            suffix = ", ".join(refs) if refs else "-"
            print(
                f"{event['seq']:>4}  {event['stage']:<14} "
                f"{event['status']:<10} {suffix}"
            )
        return 0
    finally:
        ledger.close()


def cmd_list(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        projects = ledger.list_projects()
        if not projects:
            print("no projects")
            return 0
        print(f"{'id':<36} {'name':<24} {'checkpoint':<14} created")
        for project in projects:
            checkpoint = ledger.checkpoint(project["id"]) or "none"
            print(
                f"{project['id']:<36} {project['name']:<24} "
                f"{checkpoint:<14} {project['created_at']}"
            )
        return 0
    finally:
        ledger.close()


def cmd_demo(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project_id = _create_project(settings, ledger, args.name, args.brief)
        print(f"Created {project_id}")
        Orchestrator(settings, ledger).run(project_id)
        _print_result(ledger, project_id)
        return 0
    except StageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        ledger.close()


def cmd_serve(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        workspace = Path(project["workspace"])
        script = workspace / "api" / "app.py"
        if not script.exists():
            print(f"error: {script} does not exist; run the project first", file=sys.stderr)
            return 1
        staging_path = workspace / "staging.json"
        if not staging_path.exists():
            print(
                f"error: {staging_path} does not exist; run the project first",
                file=sys.stderr,
            )
            return 1
        print(f"Serving {project['name']} at http://127.0.0.1:{args.port}")
        env = {**os.environ, "PORT": str(args.port)}
        try:
            subprocess.run(
                [sys.executable, str(script), "--port", str(args.port)],
                cwd=str(workspace),
                env=env,
                check=False,
            )
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        ledger.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgel",
        description="Open-source autonomous software studio (M0 skeleton).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a project")
    init.add_argument("name")
    init.add_argument("--brief", required=True)
    init.add_argument("--home", default=None)
    init.set_defaults(func=cmd_init)

    run = subparsers.add_parser("run", help="Run the project to completion")
    run.add_argument("project_id")
    run.add_argument("--home", default=None)
    run.set_defaults(func=cmd_run)

    status = subparsers.add_parser("status", help="Show a project and its events")
    status.add_argument("project_id")
    status.add_argument("--home", default=None)
    status.set_defaults(func=cmd_status)

    listing = subparsers.add_parser("list", help="List projects")
    listing.add_argument("--home", default=None)
    listing.set_defaults(func=cmd_list)

    demo = subparsers.add_parser("demo", help="Create and run a demo project")
    demo.add_argument("--name", default="hello-web")
    demo.add_argument(
        "--brief",
        default="A minimal web app with an index page and a health check.",
    )
    demo.add_argument("--home", default=None)
    demo.set_defaults(func=cmd_demo)

    serve = subparsers.add_parser("serve", help="Serve the generated staging app")
    serve.add_argument("project_id")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--home", default=None)
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
