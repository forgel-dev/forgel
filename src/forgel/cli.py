"""Command-line interface for the M0 skeleton."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import __version__, git_ops, peak, tasks
from .adopt import (
    AdoptError,
    add_repository,
    adopt_repository,
    create_repository,
    publish_repository,
    set_dependencies,
)
from .approvals import ApprovalError, latest_approval, record_approval
from .artifacts import read_json
from .complexity import evaluate, measure_patch, write_report
from .config import Settings
from .console import run_console
from .context import effective_context, resolve_context
from .control import is_paused, set_paused
from .daemon import project_state, run_daemon
from .deploy import (
    DeployConfig,
    DeployError,
    deploy_backup,
    deploy_init,
    deploy_logs,
    deploy_restart,
    deploy_status,
    deploy_up,
)
from .github_flow import (
    GithubFlowError,
    merge_pr,
    publish,
    status_text,
)
from .git_ops import GitOperationError
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .project_config import (
    ConfigError,
    SimplicityConfig,
    load_project_config,
)
from .program_manifest import entries as manifest_entries
from .projects import ProjectError, create_project, resolve_project
from .proposals import ProposalError, propose_project, summarize_proposals
from .sandbox import DockerSandbox
from .tokens import tokenizer_name
from .providers import ProviderError
from .providers.github_api import GithubAPIError
from .providers.github_auth import GithubAuth, GithubAuthError
from .orchestrator import Orchestrator, StageError
from .secrets import (
    SecretError,
    delete_secret,
    secret_status,
    set_secret,
)
from .sync import SyncError, reconcile_project, sync_project
from .telegram import TelegramConfig, TelegramConfigError, run_bot


def _settings(args: argparse.Namespace) -> Settings:
    return Settings.from_env(args.home)


def _ledger(settings: Settings) -> Ledger:
    return Ledger(settings.db_path)


def _print_result(
    ledger: Ledger,
    project_id: str,
    result: dict[str, object] | None = None,
) -> None:
    project = ledger.get_project(project_id)
    assert project is not None
    layout = ProjectLayout.detect(project["workspace"])
    staging_path = layout.artifact("staging.json")
    staging = read_json(staging_path) if staging_path.exists() else {}
    approval = None
    if result is not None:
        approval = result.get("approval_required")
    if isinstance(approval, dict):
        scope = approval.get("scope", "staging")
        decision = approval.get("decision", "pending")
        print(
            f"Project {project_id} is awaiting {scope} approval "
            f"({decision}, generation {approval.get('generation')})."
        )
        if staging:
            print(f"Staging: {staging.get('url', 'unknown')}")
        print(f"Approve: forgel approve {project_id} --scope {scope}")
        print(f"Then run: forgel run {project_id}")
        return
    print(f"Project {project_id} is done.")
    if staging:
        print(f"Staging: {staging.get('url', 'unknown')}")
        print(f"Command: {staging.get('command', 'unknown')}")
    print(f"Serve it with: forgel serve {project_id}")


def cmd_init(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project_id = create_project(settings, ledger, args.name, args.brief)
        print(project_id)
        return 0
    except ProjectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
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
        result = Orchestrator(settings, ledger).run(args.project_id)
        _print_result(ledger, args.project_id, result)
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
        print(f"state:      {project_state(ledger, project)}")
        for scope in ("staging", "production"):
            approval = latest_approval(ledger, project["id"], scope, generation)
            if approval is None:
                value = "none"
            else:
                value = (
                    f"{approval['decision']} by {approval['actor']} "
                    f"at {approval['created_at']}"
                )
            print(f"{scope + ':':<12}{value}")
        print(
            "proposals:  "
            f"{len(summarize_proposals(ProjectLayout.detect(project['workspace']).control))}"
        )
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
        project_id = create_project(settings, ledger, args.name, args.brief)
        print(f"Created {project_id}")
        result = Orchestrator(settings, ledger).run(project_id)
        _print_result(ledger, project_id, result)
        return 0
    except (ProjectError, StageError) as exc:
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
        if result.get("brownfield"):
            print(
                f"Reconciliation: {result['decision']} "
                f"({result['status']}). No generation started "
                "(brownfield project)."
            )
        elif result.get("started"):
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
        if result.get("brownfield"):
            print(
                f"Reconciliation: {result['decision']} "
                f"({result['status']}). No generation started "
                "(brownfield project)."
            )
        else:
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
        control = ProjectLayout.detect(project["workspace"]).control
        try:
            config = load_project_config(control)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if config is None:
            print("no forgel.toml; defaults apply")
            return 0
        print(f"config:       {control / 'forgel.toml'}")
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
        control = ProjectLayout.detect(project["workspace"]).control
        files = resolve_context(control)
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
            print(effective_context(control))
        return 0
    finally:
        ledger.close()


def cmd_complexity(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(f"error: unknown project {args.project_id}", file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        try:
            config = load_project_config(layout.control)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        simplicity = config.simplicity if config is not None else SimplicityConfig()
        metrics = measure_patch(layout.root)
        violations = evaluate(metrics, simplicity)
        path = write_report(layout.control, metrics, violations)
        print(f"report: {path.relative_to(layout.root)}")
        print(
            f"added: {metrics.added_lines}, removed: {metrics.removed_lines}, "
            f"files: {metrics.files_changed}"
        )
        print(
            f"new config keys: {metrics.new_config_keys}, "
            f"compat markers: {metrics.compat_markers}, "
            f"branches: {metrics.branches_added}, "
            f"append-only files: {metrics.append_only_files}"
        )
        if violations:
            print("NEEDS_SIMPLIFICATION")
            for item in violations:
                print(f"- {item}")
            return 1
        print("PASS")
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
        control = ProjectLayout.detect(project["workspace"]).control
        try:
            config = load_project_config(control)
            path = propose_project(
                control,
                config,
                kind=args.kind,
                title=args.title,
                evidence=args.evidence,
                risk=args.risk,
            )
        except (ConfigError, ProposalError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(path.relative_to(control))
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
        control = ProjectLayout.detect(project["workspace"]).control
        proposals = summarize_proposals(control)
        if not proposals:
            print("no proposals")
            return 0
        for proposal in proposals:
            print(
                f"{proposal['kind']:<6} {proposal['status']:<8} "
                f"{proposal['title']} ({proposal['file']})"
            )
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
        layout = ProjectLayout.detect(project["workspace"])
        script = layout.repo_path("api") / "app.py"
        if not script.exists():
            print(f"error: {script} does not exist; run the project first", file=sys.stderr)
            return 1
        staging_path = layout.artifact("staging.json")
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
                cwd=str(layout.root),
                env=env,
                check=False,
            )
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        ledger.close()


def _record_decision(args: argparse.Namespace, decision: str) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        actor = args.actor or os.environ.get("USER") or "cli"
        compliance = bool(
            getattr(args, "accept_compliance_responsibility", False)
        )
        try:
            record = record_approval(
                ledger,
                project["id"],
                scope=args.scope,
                actor=actor,
                decision=decision,
                compliance_ack=compliance,
                notes=args.notes,
            )
        except ApprovalError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(
            f"Decision recorded: {record['scope']} {record['decision']} "
            f"for {record['project_id']} (generation {record['generation']}) "
            f"by {record['actor']}."
        )
        if record["decision"] != "approved":
            print(
                "The project stays at the approval gate. Start a new "
                "generation with sync/reconcile before deciding again."
            )
        elif record["scope"] == "production":
            print(
                "No deploy provider is configured; the release stays manual "
                "and the approval is recorded for the audit trail."
            )
        else:
            print(
                f"Run: forgel run {record['project_id']} "
                "(or let the daemon continue)."
            )
        return 0
    finally:
        ledger.close()


def cmd_approve(args: argparse.Namespace) -> int:
    return _record_decision(args, "approved")


def cmd_reject(args: argparse.Namespace) -> int:
    return _record_decision(args, "rejected")


def cmd_pause(args: argparse.Namespace) -> int:
    settings = _settings(args)
    set_paused(settings.home, True)
    print("Daemon paused.")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    settings = _settings(args)
    set_paused(settings.home, False)
    print("Daemon resumed.")
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        if args.action == "cancel":
            if not args.task_id:
                print("error: task cancel requires --task", file=sys.stderr)
                return 2
            try:
                task = tasks.cancel_task(layout, args.task_id)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            tasks.commit_task(
                layout, task["id"], f"Cancel task {task['id']}"
            )
            print(f"Cancelled {task['id']}.")
            return 0
        if args.action == "list":
            entries = tasks.list_tasks(layout)
            if not entries:
                print("no tasks")
                return 0
            for task in entries:
                result = task.get("result", {})
                summary = result.get("summary", "") if result else ""
                print(
                    f"{task['id']:<40} {task['status']:<8} "
                    f"{task['title']}"
                )
                if summary:
                    print(f"  {summary}")
            return 0
        try:
            task = tasks.create_task(
                layout,
                title=args.title,
                requirements=args.require,
                acceptance=args.accept,
                constraints=args.constraint,
                repo_id=args.repo,
                test_command=(
                    shlex.split(args.test_command)
                    if args.test_command
                    else []
                ),
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        try:
            if (layout.control / ".git").exists():
                git_ops.commit_all(
                    layout.control, f"Add task {task['id']}"
                )
                git_ops.tag_baseline(layout.control)
        except GitOperationError:
            pass
        print(task["id"])
        return 0
    finally:
        ledger.close()


def cmd_github(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.action == "status":
            print(status_text(settings, project))
            return 0
        try:
            if args.action == "publish":
                result = publish(
                    settings,
                    ledger,
                    project,
                    repo_id=args.repo,
                    title=args.title,
                    body=args.body,
                    base_branch=args.base_branch,
                    branch=args.branch,
                    commit_message=args.commit_message,
                    wait=not args.no_wait,
                    merge=args.merge,
                )
            else:
                result = merge_pr(
                    settings,
                    ledger,
                    project,
                    repo_id=args.repo,
                    number=args.pr,
                    base_branch=args.base_branch,
                    branch=args.branch,
                    wait=not args.no_wait,
                    require_ci=False if args.no_require_ci else None,
                )
        except (
            GithubFlowError,
            GithubAPIError,
            GithubAuthError,
            GitOperationError,
        ) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"repository: {result.repo_id} ({result.full_name})")
        print(f"branch:     {result.branch} -> {result.base}")
        print(f"pull:       #{result.pr_number} {result.pr_url}")
        print(f"checks:     {result.checks}")
        print(
            f"merged:     {str(result.merged).lower()}"
            + (f" ({result.merge_sha})" if result.merge_sha else "")
        )
        print(f"status:     {result.status}")
        return 0 if result.status not in {"checks_failed", "merge_failed"} else 1
    finally:
        ledger.close()


def cmd_adopt(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            result = adopt_repository(
                settings,
                ledger,
                args.url,
                brief=args.brief,
                name=args.name,
            )
        except (AdoptError, ProviderError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"project:  {result.project_id}")
        print(f"repo:     {result.repo_id} ({result.provider})")
        print(f"url:      {result.url}")
        print("mode:     brownfield")
        print(f"auth:     {result.auth.detail}")
        return 0
    finally:
        ledger.close()


def cmd_repo(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        if args.action == "list":
            repos = manifest_entries(layout)
            if not repos:
                print("no repositories")
                return 0
            for entry in repos:
                depends = ", ".join(entry["depends_on"]) or "none"
                print(
                    f"{entry['id']:<12} {entry['role']:<16} "
                    f"{entry['provider']:<8} {entry['url'] or '—'}"
                    f"  depends_on={depends}"
                )
            return 0
        depends = [item for item in args.depends_on.split(",") if item]
        if args.action == "create":
            if not args.id:
                print(
                    "error: repo create requires --id <repository-id>",
                    file=sys.stderr,
                )
                return 2
            try:
                created = create_repository(
                    settings,
                    ledger,
                    project,
                    args.id,
                    org=args.org,
                    private=not args.public,
                    depends_on=depends,
                    role=args.role,
                    description=args.description,
                )
            except (AdoptError, ProviderError, GithubAuthError) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(
                f"Created {created.entry['id']} at {created.url} "
                f"and added it to {project['id']}."
            )
            return 0
        if args.action == "publish":
            targets = (
                [args.id]
                if args.id
                else [
                    entry["id"]
                    for entry in manifest_entries(layout)
                    if "github.com" not in (entry.get("url") or "")
                ]
            )
            if not targets:
                print("nothing to publish")
                return 0
            for repo_id in targets:
                try:
                    published = publish_repository(
                        settings,
                        ledger,
                        project,
                        repo_id,
                        org=args.org,
                        private=not args.public,
                        description=args.description,
                    )
                except (
                    AdoptError,
                    ProviderError,
                    GithubAuthError,
                ) as exc:
                    print(
                        f"error: {repo_id}: {exc}", file=sys.stderr
                    )
                    return 1
                print(f"Published {repo_id} to {published.url}")
            return 0
        if args.action == "link":
            if not args.url:
                print(
                    "error: repo link requires a repository id",
                    file=sys.stderr,
                )
                return 2
            try:
                entry = set_dependencies(
                    settings,
                    ledger,
                    project,
                    args.url,
                    depends,
                )
            except (AdoptError, ValueError) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            edges = ", ".join(entry["depends_on"]) or "none"
            print(f"Updated dependencies for {entry['id']}: {edges}.")
            return 0
        if not args.url:
            print("error: repo add requires a URL", file=sys.stderr)
            return 2
        try:
            result = add_repository(
                settings,
                ledger,
                project,
                args.url,
                repo_id=args.id,
                depends_on=depends,
                role=args.role,
            )
        except (AdoptError, ProviderError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(
            f"Added {result.entry['id']} ({result.entry['provider']}) "
            f"to {project['id']}."
        )
        if result.entry["depends_on"]:
            print(
                "depends_on: " + ", ".join(result.entry["depends_on"])
            )
        else:
            print("no dependency edges; maintained separately in the project")
        return 0
    finally:
        ledger.close()


def cmd_deploy(args: argparse.Namespace) -> int:
    target = Path(args.file)
    try:
        if args.action == "init":
            path = deploy_init(target)
            print(f"Created {path} (mode 0600); edit it and run forgel deploy up.")
            return 0
        config = DeployConfig.from_file(target)
        try:
            mode = target.stat().st_mode & 0o777
            if mode & 0o077:
                print(
                    f"warning: {target} is mode {mode:o}; use chmod 600",
                    file=sys.stderr,
                )
        except OSError:
            pass
        if args.action == "up":
            deploy_up(
                config,
                assume_yes=args.yes,
                allow_install=not args.no_install,
                interactive=sys.stdin.isatty(),
            )
        elif args.action == "status":
            deploy_status(config)
        elif args.action == "logs":
            deploy_logs(config, follow=args.follow)
        elif args.action == "restart":
            deploy_restart(config)
        else:
            output = (
                Path(args.output)
                if args.output
                else Path(
                    "forgel-backup-"
                    + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                    + ".tgz"
                )
            )
            deploy_backup(config, output)
        return 0
    except DeployError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    settings = _settings(args)
    issues: list[str] = []

    def report(label: str, value: str, ok: bool = True) -> None:
        print(f"{'OK  ' if ok else 'WARN'} {label:<22} {value}")
        if not ok:
            issues.append(label)

    print(f"home: {settings.home}")
    try:
        settings.home.mkdir(parents=True, exist_ok=True)
        probe = settings.home / ".forgel-doctor"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report("home writable", str(settings.home))
    except OSError as exc:
        report("home writable", str(exc), False)

    report(
        "registry",
        str(settings.registry_path),
        settings.registry_path.exists(),
    )
    report(
        "jurisdictions",
        str(settings.jurisdiction_path),
        settings.jurisdiction_path.exists(),
    )
    report(
        "templates",
        str(settings.templates_path),
        settings.templates_path.exists(),
    )

    try:
        ledger = Ledger(settings.db_path)
        try:
            count = len(ledger.list_projects())
        finally:
            ledger.close()
        report("ledger", f"{settings.db_path} ({count} projects)")
    except Exception as exc:  # noqa: BLE001 - doctor reports, never crashes
        report("ledger", str(exc), False)

    paused = "paused" if is_paused(settings.home) else "running"
    report("control", paused)
    report(
        "context window",
        str(settings.context_window),
    )
    report("tokenizer", tokenizer_name())
    if peak.should_defer(
        settings.peak_policy, hours=settings.peak_hours
    ):
        boundary = peak.next_off_peak(hours=settings.peak_hours)
        report(
            "model schedule",
            f"{settings.peak_policy}; peak until "
            f"{boundary.strftime('%H:%M UTC')}",
        )
    else:
        report(
            "model schedule",
            f"{settings.peak_policy}; off-peak now",
        )
    if settings.sandbox == "docker":
        sandbox = DockerSandbox(settings)
        available, detail = sandbox.available()
        report(
            "sandbox",
            f"docker {detail}" if available else detail,
            available,
        )
        report(
            "sandbox images",
            ", ".join(settings.sandbox_images) or "any image",
        )
        report(
            "sandbox limits",
            f"{settings.sandbox_cpus} cpu, {settings.sandbox_memory}, "
            f"{settings.sandbox_pids} pids, network {settings.sandbox_network}"
            + (", digest required" if settings.sandbox_require_digest else ""),
        )
    else:
        report("sandbox", "local (single-tenant)")

    try:
        telegram = TelegramConfig.from_env(home=settings.home)
        report(
            "telegram",
            f"{len(telegram.allowed_chat_ids)} allowed chat(s), "
            f"poll {telegram.poll_timeout}s",
        )
    except TelegramConfigError as exc:
        report("telegram", str(exc), False)

    model = build_model_client(settings.home, log=lambda _m: None)
    if model is None:
        report("model", "not configured; free text disabled", False)
    else:
        report("model", type(model).__name__)

    github = GithubAuth(settings.home)
    status = github.status()
    report(
        "github auth",
        status,
        status != "no GitHub credentials",
    )

    for tool in ("git", "docker", "node", "npm"):
        path = shutil.which(tool)
        report(tool, path or "not found", path is not None)
    if shutil.which("git"):
        version = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=False
        ).stdout.strip()
        report("git version", version)

    if issues:
        print("RESULT: ISSUES (" + ", ".join(issues) + ")")
        return 1
    print("RESULT: OK")
    return 0


def cmd_secret(args: argparse.Namespace) -> int:
    settings = _settings(args)
    if args.action == "list":
        for key, state in secret_status(settings.home).items():
            print(f"{key:<26} {state}")
        return 0
    if not args.key:
        print("error: a secret key is required", file=sys.stderr)
        return 2
    try:
        if args.action == "set":
            if sys.stdin.isatty():
                value = getpass.getpass(f"{args.key}: ")
            else:
                value = sys.stdin.readline().strip()
            if not value:
                print("error: the value must not be empty", file=sys.stderr)
                return 2
            path = set_secret(settings.home, args.key, value)
            print(f"Saved {args.key} to {path} (mode 0600).")
        else:
            removed = delete_secret(settings.home, args.key)
            if removed:
                print(f"Deleted {args.key}.")
            else:
                print(f"{args.key} is not set in the file.")
        return 0
    except (SecretError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_chat(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        run_console(
            settings,
            ledger,
            project_id=args.project,
            daemon=not args.no_daemon,
            actor=args.actor,
        )
        return 0
    finally:
        ledger.close()


def cmd_telegram(args: argparse.Namespace) -> int:
    settings = _settings(args)
    try:
        config = TelegramConfig.from_env(home=settings.home)
    except TelegramConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    ledger = _ledger(settings)
    try:
        print(
            f"Telegram gateway started; allowed chats: "
            f"{len(config.allowed_chat_ids)}.",
            file=sys.stderr,
        )
        run_bot(
            settings,
            ledger,
            config,
            daemon=not args.no_daemon,
            interval=args.interval,
            poll_timeout=args.poll_timeout,
        )
        return 0
    except KeyboardInterrupt:
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

    run = subparsers.add_parser("run", help="Run the project to the next gate")
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

    demo = subparsers.add_parser(
        "demo", help="Create and run a demo project to the approval gate"
    )
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

    complexity = subparsers.add_parser(
        "complexity", help="Measure the patch against the simplicity budget"
    )
    complexity.add_argument("project_id")
    complexity.add_argument("--home", default=None)
    complexity.set_defaults(func=cmd_complexity)

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

    approve = subparsers.add_parser(
        "approve", help="Record a staging or production approval"
    )
    approve.add_argument("project_id")
    approve.add_argument(
        "--scope", choices=["staging", "production"], default="staging"
    )
    approve.add_argument(
        "--accept-compliance-responsibility", action="store_true"
    )
    approve.add_argument("--notes", default="")
    approve.add_argument("--actor", default="")
    approve.add_argument("--home", default=None)
    approve.set_defaults(func=cmd_approve)

    reject = subparsers.add_parser(
        "reject", help="Reject a staging or production release"
    )
    reject.add_argument("project_id")
    reject.add_argument(
        "--scope", choices=["staging", "production"], default="staging"
    )
    reject.add_argument("--notes", default="")
    reject.add_argument("--actor", default="")
    reject.add_argument("--home", default=None)
    reject.set_defaults(func=cmd_reject)

    pause = subparsers.add_parser("pause", help="Pause new daemon iterations")
    pause.add_argument("--home", default=None)
    pause.set_defaults(func=cmd_pause)

    resume = subparsers.add_parser("resume", help="Resume daemon iterations")
    resume.add_argument("--home", default=None)
    resume.set_defaults(func=cmd_resume)

    chat = subparsers.add_parser(
        "chat", help="Local console: the same commands without Telegram"
    )
    chat.add_argument("--project", default="")
    chat.add_argument("--no-daemon", action="store_true")
    chat.add_argument("--actor", default="local")
    chat.add_argument("--home", default=None)
    chat.set_defaults(func=cmd_chat)

    telegram = subparsers.add_parser(
        "telegram", help="Run the Telegram gateway and the daemon"
    )
    telegram.add_argument("--home", default=None)
    telegram.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Daemon cycle interval (default: daemon.interval in config.toml)",
    )
    telegram.add_argument(
        "--poll-timeout",
        type=int,
        default=None,
        help="Long-polling timeout in seconds (default: daemon config or env)",
    )
    telegram.add_argument(
        "--no-daemon",
        action="store_true",
        help="Serve commands only; do not run iterations",
    )
    telegram.set_defaults(func=cmd_telegram)

    task = subparsers.add_parser(
        "task", help="Queue or list coding-agent tasks"
    )
    task.add_argument("action", choices=["add", "list", "cancel"])
    task.add_argument("project_id")
    task.add_argument("--task", dest="task_id", default="")
    task.add_argument("--title", default="")
    task.add_argument("--require", action="append", default=[])
    task.add_argument("--accept", action="append", default=[])
    task.add_argument("--constraint", action="append", default=[])
    task.add_argument("--repo", default="")
    task.add_argument(
        "--test-command",
        dest="test_command",
        default="",
        help="Command the agent must pass, e.g. 'python -m unittest discover -s tests'",
    )
    task.add_argument("--home", default=None)
    task.set_defaults(func=cmd_task)

    github = subparsers.add_parser(
        "github", help="Publish a branch and manage pull requests"
    )
    github.add_argument("action", choices=["status", "publish", "merge"])
    github.add_argument("project_id")
    github.add_argument("--repo", default="")
    github.add_argument("--title", default="")
    github.add_argument("--body", default="")
    github.add_argument("--base", dest="base_branch", default="")
    github.add_argument("--branch", default="")
    github.add_argument(
        "--commit",
        dest="commit_message",
        default="",
        help="Commit all changes with this message before publishing",
    )
    github.add_argument(
        "--merge", choices=["auto", "human"], default=""
    )
    github.add_argument("--pr", type=int, default=None)
    github.add_argument("--no-wait", action="store_true")
    github.add_argument("--no-require-ci", action="store_true")
    github.add_argument("--home", default=None)
    github.set_defaults(func=cmd_github)

    adopt = subparsers.add_parser(
        "adopt", help="Adopt an existing repository as a project"
    )
    adopt.add_argument("url")
    adopt.add_argument("--brief", default="")
    adopt.add_argument("--name", default="")
    adopt.add_argument("--home", default=None)
    adopt.set_defaults(func=cmd_adopt)

    repo = subparsers.add_parser(
        "repo", help="List, add, create or publish project repositories"
    )
    repo.add_argument(
        "action", choices=["list", "add", "link", "create", "publish"]
    )
    repo.add_argument("project_id")
    repo.add_argument("url", nargs="?", default="")
    repo.add_argument("--id", default="")
    repo.add_argument("--depends-on", dest="depends_on", default="")
    repo.add_argument("--role", default="application")
    repo.add_argument("--org", default="")
    repo.add_argument("--public", action="store_true")
    repo.add_argument("--description", default="")
    repo.add_argument("--home", default=None)
    repo.set_defaults(func=cmd_repo)

    deploy = subparsers.add_parser(
        "deploy", help="Deploy the daemon to a remote host over SSH"
    )
    deploy.add_argument(
        "action", choices=["init", "up", "status", "logs", "restart", "backup"]
    )
    deploy.add_argument("--file", default=".env.deploy")
    deploy.add_argument("--follow", action="store_true")
    deploy.add_argument("--output", default="")
    deploy.add_argument(
        "--yes",
        action="store_true",
        help="Allow installing Docker/Compose without prompting",
    )
    deploy.add_argument(
        "--no-install",
        action="store_true",
        help="Never install remotely; report missing Docker/Compose",
    )
    deploy.set_defaults(func=cmd_deploy)

    doctor = subparsers.add_parser(
        "doctor", help="Check the local installation and deployment prerequisites"
    )
    doctor.add_argument("--home", default=None)
    doctor.set_defaults(func=cmd_doctor)

    secret = subparsers.add_parser(
        "secret", help="Manage secrets in the local 0600 store"
    )
    secret.add_argument(
        "action", choices=["list", "set", "delete"], nargs="?", default="list"
    )
    secret.add_argument("key", nargs="?", default="")
    secret.add_argument("--home", default=None)
    secret.set_defaults(func=cmd_secret)

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
