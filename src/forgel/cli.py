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
from .context import effective_context, resolve_context
from .daemon import run_daemon
from .ledger import Ledger, new_project_id
from .project_config import ConfigError, load_project_config
from .proposals import ProposalError, list_proposals, propose_project
from .orchestrator import Orchestrator, StageError
from .sync import SyncError, reconcile_project, sync_project

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
        state = ledger.checkpoint_state(args.project_id)
        checkpoint = state[0] if state is not None else "none"
        generation = (
            state[1] if state is not None else ledger.current_generation(args.project_id)
        )
        print(f"project:    {project['id']}")
        print(f"name:       {project['name']}")
        print(f"recipe:     {project.get('recipe_id') or 'none'}")
        print(f"workspace:  {project['workspace']}")
        print(f"generation: {generation}")
        print(f"checkpoint: {checkpoint}")
        print()
        print(f"{'seq':>4}  {'gen':>3}  {'stage':<14} {'status':<10} artifacts")
        for event in ledger.events(args.project_id):
            try:
                refs = json.loads(event["artifact_refs"])
            except json.JSONDecodeError:
                refs = []
            suffix = ", ".join(refs) if refs else "-"
            print(
                f"{event['seq']:>4}  {event['generation']:>3}  "
                f"{event['stage']:<14} {event['status']:<10} {suffix}"
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
        print(f"{'id':<36} {'name':<24} {'gen':>3} {'checkpoint':<14} created")
        for project in projects:
            state = ledger.checkpoint_state(project["id"])
            checkpoint = state[0] if state is not None else "none"
            generation = (
                state[1]
                if state is not None
                else ledger.current_generation(project["id"])
            )
            print(
                f"{project['id']:<36} {project['name']:<24} "
                f"{generation:>3} {checkpoint:<14} {project['created_at']}"
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


def cmd_sync(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        try:
            result = sync_project(
                Path(project["workspace"]),
                ledger,
                args.project_id,
                from_stage=args.from_stage,
                force=args.force,
                decision=args.decision,
                notes=args.notes,
            )
        except (SyncError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if result.get("started"):
            decision = result.get("decision") or "forced"
            print(
                f"Reconciliation applied: {decision}. "
                f"Generation {result['generation']} started; "
                f"re-run from {result['from_stage']}."
            )
            print(f"Run: forgel run {args.project_id}")
        elif result.get("pending"):
            analysis = result.get("analysis", {})
            print(
                f"External changes: {result['count']} file(s). "
                "Decision required."
            )
            labels = (
                ("Violations", "violations"),
                ("Requirements changed", "requirements"),
                ("Documented modifications", "documented"),
                ("Undocumented changes", "undocumented"),
                ("Deletions", "deletions"),
            )
            for label, key in labels:
                items = analysis.get(key, [])
                if items:
                    print(f"  {label}: {len(items)}")
            print(f"See {result.get('reconciliation')}.")
            print(
                f"Run: forgel reconcile {args.project_id} "
                "--decision accept|fix|rollback|ignore [--notes ...]"
            )
        else:
            print("No external changes detected.")
        return 0
    finally:
        ledger.close()


def cmd_reconcile(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        try:
            result = reconcile_project(
                Path(project["workspace"]),
                ledger,
                args.project_id,
                decision=args.decision,
                notes=args.notes,
                from_stage=args.from_stage,
            )
        except (SyncError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(
            f"Reconciliation: {result['decision']} ({result['status']}). "
            f"Generation {result['generation']} started; "
            f"re-run from {result['from_stage']}."
        )
        print(f"Run: forgel run {args.project_id}")
        return 0
    finally:
        ledger.close()


def cmd_config(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        workspace = Path(project["workspace"])
        try:
            config = load_project_config(workspace)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if config is None:
            print("no forgel.toml; defaults apply")
            return 0
        print(f"config:       {workspace / 'forgel.toml'}")
        print(f"project:      {config.name or '—'}")
        print(f"recipe:       {config.recipe or '—'}")
        print(f"qa.runtime:   {config.qa.runtime}")
        print(f"jurisdiction: {config.jurisdiction.pack}")
        print(f"models:       {config.models.default} / {config.models.architecture}")
        print(
            "budget:       "
            f"${config.budget.per_feature_usd:g}/feature, "
            f"${config.budget.per_project_usd:g}/project"
        )
        return 0
    finally:
        ledger.close()


def cmd_context(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        workspace = Path(project["workspace"])
        files = resolve_context(workspace)
        if not files:
            print("no context files")
            return 0
        print("context files (priority order):")
        for item in files:
            if item.native:
                kind = "native"
            elif item.name == "CLAUDE.md":
                kind = "local shim"
            else:
                kind = "canon"
            print(f"  {item.name:<12} {kind:<10} {len(item.text)} bytes")
        if args.raw:
            print()
            print(effective_context(workspace))
        return 0
    finally:
        ledger.close()


def cmd_propose(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        workspace = Path(project["workspace"])
        try:
            config = load_project_config(workspace)
            path = propose_project(
                workspace,
                config,
                kind=args.kind,
                title=args.title,
                evidence=args.evidence,
                risk=args.risk,
            )
        except (ConfigError, ProposalError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(path.relative_to(workspace))
        return 0
    finally:
        ledger.close()


def cmd_proposals(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        workspace = Path(project["workspace"])
        paths = list_proposals(workspace)
        if not paths:
            print("no proposals")
            return 0
        for path in paths:
            text = path.read_text(encoding="utf-8")
            kind = ""
            status = ""
            title = path.stem
            for line in text.splitlines():
                if line.startswith("# Proposal: "):
                    title = line[len("# Proposal: ") :]
                elif line.startswith("- Class: "):
                    kind = line.split(":", 1)[1].strip().strip("`")
                elif line.startswith("- Status: "):
                    status = line.split(":", 1)[1].strip().strip("`")
            print(f"{kind:<6} {status:<8} {title} ({path.name})")
        return 0
    finally:
        ledger.close()


def cmd_daemon(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        run_daemon(
            settings,
            ledger,
            interval=args.interval,
            once=args.once,
            max_cycles=args.max_cycles,
        )
        return 0
    except KeyboardInterrupt:
        return 0
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

    sync = subparsers.add_parser(
        "sync", help="Reconcile external changes and start a new generation"
    )
    sync.add_argument("project_id")
    sync.add_argument(
        "--from",
        dest="from_stage",
        default="review",
        help="Stage to re-run from (default: review)",
    )
    sync.add_argument("--force", action="store_true")
    sync.add_argument(
        "--decision",
        choices=["accept", "fix", "rollback", "ignore"],
        default=None,
    )
    sync.add_argument("--notes", default="")
    sync.add_argument("--home", default=None)
    sync.set_defaults(func=cmd_sync)

    reconcile = subparsers.add_parser(
        "reconcile", help="Apply a decision to a pending reconciliation"
    )
    reconcile.add_argument("project_id")
    reconcile.add_argument(
        "--decision",
        choices=["accept", "fix", "rollback", "ignore"],
        required=True,
    )
    reconcile.add_argument("--notes", default="")
    reconcile.add_argument(
        "--from",
        dest="from_stage",
        default="review",
        help="Stage to re-run from (default: review)",
    )
    reconcile.add_argument("--home", default=None)
    reconcile.set_defaults(func=cmd_reconcile)

    config = subparsers.add_parser("config", help="Show the project forgel.toml")
    config.add_argument("project_id")
    config.add_argument("--home", default=None)
    config.set_defaults(func=cmd_config)

    context = subparsers.add_parser(
        "context", help="Show resolved context files and their priority"
    )
    context.add_argument("project_id")
    context.add_argument("--raw", action="store_true")
    context.add_argument("--home", default=None)
    context.set_defaults(func=cmd_context)

    propose = subparsers.add_parser(
        "propose", help="Create a post-release change proposal"
    )
    propose.add_argument("project_id")
    propose.add_argument(
        "--kind", choices=["patch", "minor", "major"], required=True
    )
    propose.add_argument("--title", required=True)
    propose.add_argument("--evidence", default="")
    propose.add_argument("--risk", default="")
    propose.add_argument("--home", default=None)
    propose.set_defaults(func=cmd_propose)

    proposals = subparsers.add_parser(
        "proposals", help="List change proposals"
    )
    proposals.add_argument("project_id")
    proposals.add_argument("--home", default=None)
    proposals.set_defaults(func=cmd_proposals)

    daemon = subparsers.add_parser(
        "daemon", help="Run the long-lived orchestrator loop"
    )
    daemon.add_argument("--home", default=None)
    daemon.add_argument("--interval", type=float, default=5.0)
    daemon.add_argument("--once", action="store_true")
    daemon.add_argument("--max-cycles", type=int, default=None)
    daemon.set_defaults(func=cmd_daemon)

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
