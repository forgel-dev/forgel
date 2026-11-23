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

from . import __version__, git_ops, language, peak, tasks
from .adopt import (
    AdoptError,
    add_repository,
    adopt_repository,
    create_repository,
    extract_control,
    publish_repository,
    set_dependencies,
)
from .approvals import ApprovalError, latest_approval, record_approval
from .artifacts import read_json
from . import limits
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
from .local_env import LocalEnvError, init_local_env, load_local_env
from .model import build_model_client
from . import scenario
from .planner import PlanningError, plan_project, plan_status
from .release import ReleaseError, release_project
from .project_config import (
    ConfigError,
    SimplicityConfig,
    load_project_config,
)
from .program_manifest import entries as manifest_entries
from .program_manifest import repo_location
from .projects import ProjectError, create_project, resolve_project
from .proposals import ProposalError, propose_project, summarize_proposals
from .sandbox import DockerSandbox
from .task_review import accept_task, reject_task
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
from .i18n import has as _has
from .i18n import t as _t

_UI_LANG = "en"


def _say(key: str, **values: object) -> str:
    return _t(_UI_LANG, key, **values)


def _status_name(status: object) -> str:
    key = str(status or "")
    return _t(_UI_LANG, key) if _has(_UI_LANG, key) else key


def _plan_status_name(status: object) -> str:
    key = f"plan_{status or 'none'}"
    return (
        _t(_UI_LANG, key)
        if _has(_UI_LANG, key)
        else str(status or "")
    )


_DOCTOR_LABELS = {
    "home writable": "cli_doctor_home_writable",
    "registry": "cli_doctor_registry",
    "jurisdictions": "cli_doctor_jurisdictions",
    "templates": "cli_doctor_templates",
    "ledger": "cli_doctor_ledger",
    "control": "cli_doctor_control",
    "context window": "cli_doctor_context_window",
    "tokenizer": "cli_doctor_tokenizer",
    "task pipeline": "cli_doctor_task_pipeline",
    "model schedule": "cli_doctor_model_schedule",
    "sandbox": "cli_doctor_sandbox",
    "sandbox images": "cli_doctor_sandbox_images",
    "sandbox limits": "cli_doctor_sandbox_limits",
    "telegram": "cli_doctor_telegram",
    "model": "cli_doctor_model",
    "github auth": "cli_doctor_github_auth",
    "git version": "cli_doctor_git_version",
}


def _set_ui_language(argv: Sequence[str]) -> None:
    global _UI_LANG
    _UI_LANG = (
        "ru"
        if any(
            language.detect(str(item), "en") == "ru"
            for item in argv
        )
        else "en"
    )


def _settings(args: argparse.Namespace) -> Settings:
    """Build settings after loading local .env files.

    The process environment wins; ``.env.local``/``.env`` in the working
    directory and in the Forgel home fill the gaps.
    """

    try:
        load_local_env(Path.cwd(), None)
        home = (
            Path(args.home)
            if args.home
            else Path(
                os.environ.get("FORGEL_HOME", Path.home() / ".forgel")
            )
        )
        load_local_env(None, home.expanduser())
    except LocalEnvError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        raise SystemExit(2) from exc
    return Settings.from_env(args.home)


def cmd_setup(args: argparse.Namespace) -> int:
    try:
        path = init_local_env(Path.cwd(), force=args.force)
    except LocalEnvError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1
    print(_say("cli_created", item=path))
    print(_say("cli_setup_hint"))
    print(_say("cli_doctor_hint"))
    return 0


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
            _say(
                "cli_awaiting",
                project=project_id,
                scope=_say(f"cli_scope_{scope}"),
                decision=decision,
                generation=approval.get("generation"),
            )
        )
        if staging:
            print(
                _say(
                    "cli_staging",
                    url=staging.get("url", _say("cli_unknown")),
                )
            )
        print(
            _say(
                "cli_approve",
                project=project_id,
                scope=scope,
            )
        )
        print(_say("cli_then_run", project=project_id))
        return
    print(_say("cli_done", project=project_id))
    if staging:
        print(
            _say(
                "cli_staging",
                url=staging.get("url", _say("cli_unknown")),
            )
        )
        print(
            _say(
                "cli_command",
                command=staging.get("command", _say("cli_unknown")),
            )
        )
    print(_say("cli_serve_hint", project=project_id))


def cmd_init(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project_id = create_project(settings, ledger, args.name, args.brief)
        print(project_id)
        return 0
    except ProjectError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 2
    finally:
        ledger.close()


def cmd_run(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        result = Orchestrator(settings, ledger).run(args.project_id)
        _print_result(ledger, args.project_id, result)
        return 0
    except StageError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1
    finally:
        ledger.close()


def cmd_limit(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        if args.name and args.seconds is not None:
            try:
                value = limits.set_value(layout, args.name, args.seconds)
            except ValueError as exc:
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 2
            print(f"{args.name} = {value:g}s")
            return 0
        effective = {**limits.LIMITS, **limits.load(layout)}
        for name in sorted(effective):
            print(f"{name}: {effective[name]:g}s")
        return 0
    finally:
        ledger.close()


def cmd_status(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        state = ledger.checkpoint_state(args.project_id)
        checkpoint = (
            state[0] if state is not None else _say("cli_none")
        )
        generation = (
            state[1] if state is not None else ledger.current_generation(args.project_id)
        )
        print(_say("cli_status_project", project=project["id"]))
        print(_say("cli_status_name", name=project["name"]))
        print(
            _say(
                "cli_status_recipe",
                recipe=project.get("recipe_id")
                or _say("cli_none"),
            )
        )
        print(
            _say(
                "cli_status_workspace",
                workspace=project["workspace"],
            )
        )
        print(
            _say("cli_status_generation", generation=generation)
        )
        print(
            _say("cli_status_checkpoint", checkpoint=checkpoint)
        )
        print(
            _say(
                "cli_status_state",
                state=project_state(ledger, project),
            )
        )
        for scope in ("staging", "production"):
            approval = latest_approval(ledger, project["id"], scope, generation)
            if approval is None:
                value = _say("cli_none")
            else:
                value = _say(
                    "cli_status_approval_value",
                    decision=approval["decision"],
                    actor=approval["actor"],
                    at=approval["created_at"],
                )
            print(
                _say(
                    "cli_status_approval",
                    scope=_say(f"cli_scope_{scope}") + ":",
                    value=value,
                )
            )
        print(
            _say(
                "cli_status_proposals",
                count=len(
                    summarize_proposals(
                        ProjectLayout.detect(
                            project["workspace"]
                        ).control
                    )
                ),
            )
        )
        print()
        print(_say("cli_events_header"))
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
            print(_say("cli_no_projects"))
            return 0
        print(_say("cli_list_header"))
        for project in projects:
            state = ledger.checkpoint_state(project["id"])
            checkpoint = (
                state[0] if state is not None else _say("cli_none")
            )
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


def cmd_sync(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        if result.get("brownfield"):
            print(
                _say(
                    "cli_sync_brownfield",
                    decision=result["decision"],
                    status=result["status"],
                )
            )
        elif result.get("started"):
            decision = result.get("decision") or "forced"
            print(
                _say(
                    "cli_sync_applied",
                    decision=decision,
                    generation=result["generation"],
                    stage=result["from_stage"],
                )
            )
            print(_say("cli_run_hint", project=args.project_id))
        elif result.get("pending"):
            analysis = result.get("analysis", {})
            print(
                _say(
                    "cli_sync_pending",
                    count=result["count"],
                )
            )
            labels = (
                "violations",
                "requirements",
                "documented",
                "undocumented",
                "deletions",
            )
            for key in labels:
                items = analysis.get(key, [])
                if items:
                    print(
                        "  "
                        + _say(
                            f"chat_sync_{key}",
                            count=len(items),
                        )
                    )
            print(
                _say(
                    "cli_sync_see",
                    path=result.get("reconciliation"),
                )
            )
            print(
                _say(
                    "cli_reconcile_hint",
                    project=args.project_id,
                )
            )
        else:
            print(_say("cli_no_changes"))
        return 0
    finally:
        ledger.close()


def cmd_reconcile(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        if result.get("brownfield"):
            print(
                _say(
                    "cli_sync_brownfield",
                    decision=result["decision"],
                    status=result["status"],
                )
            )
        else:
            print(
                _say(
                    "cli_sync_started",
                    decision=result["decision"],
                    status=result["status"],
                    generation=result["generation"],
                    stage=result["from_stage"],
                )
            )
            print(_say("cli_run_hint", project=args.project_id))
        return 0
    finally:
        ledger.close()


def cmd_config(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = ledger.get_project(args.project_id)
        if project is None:
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        control = ProjectLayout.detect(project["workspace"]).control
        try:
            config = load_project_config(control)
        except ConfigError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        if config is None:
            print(_say("cli_no_config"))
            return 0
        print(
            _say(
                "cli_config_path",
                path=control / "forgel.toml",
            )
        )
        print(
            _say(
                "cli_config_project",
                name=config.name or "—",
            )
        )
        print(
            _say(
                "cli_config_recipe",
                recipe=config.recipe or "—",
            )
        )
        print(_say("cli_config_qa", runtime=config.qa.runtime))
        print(
            _say(
                "cli_config_jurisdiction",
                pack=config.jurisdiction.pack,
            )
        )
        print(
            _say(
                "cli_config_models",
                model=config.models.default,
                architecture=config.models.architecture,
            )
        )
        print(
            _say(
                "cli_config_budget",
                feature=f"${config.budget.per_feature_usd:g}",
                project=f"${config.budget.per_project_usd:g}",
            )
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
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        control = ProjectLayout.detect(project["workspace"]).control
        files = resolve_context(control)
        if not files:
            print(_say("cli_no_context"))
            return 0
        print(_say("cli_context_header"))
        for item in files:
            if item.native:
                kind = _say("cli_context_native")
            elif item.name == "CLAUDE.md":
                kind = _say("cli_context_shim")
            else:
                kind = _say("cli_context_canon")
            print(
                _say(
                    "cli_context_entry",
                    name=item.name,
                    kind=kind,
                    size=len(item.text),
                )
            )
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
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        try:
            config = load_project_config(layout.control)
        except ConfigError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        simplicity = config.simplicity if config is not None else SimplicityConfig()
        metrics = measure_patch(layout.root)
        violations = evaluate(metrics, simplicity)
        path = write_report(layout.control, metrics, violations)
        print(
            _say(
                "cli_report",
                path=path.relative_to(layout.root),
            )
        )
        print(
            _say(
                "cli_complexity_metrics",
                added=metrics.added_lines,
                removed=metrics.removed_lines,
                files=metrics.files_changed,
            )
        )
        print(
            _say(
                "cli_complexity_extra",
                keys=metrics.new_config_keys,
                markers=metrics.compat_markers,
                branches=metrics.branches_added,
                append_only=metrics.append_only_files,
            )
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
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
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
            print(_say("cli_error", error=exc), file=sys.stderr)
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
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        control = ProjectLayout.detect(project["workspace"]).control
        proposals = summarize_proposals(control)
        if not proposals:
            print(_say("cli_no_proposals"))
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
            print(_say("cli_unknown_project", project=args.project_id), file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        script = layout.repo_path("api") / "app.py"
        if not script.exists():
            print(
                _say("cli_serve_missing", path=script),
                file=sys.stderr,
            )
            return 1
        staging_path = layout.artifact("staging.json")
        if not staging_path.exists():
            print(
                _say("cli_serve_missing", path=staging_path),
                file=sys.stderr,
            )
            return 1
        print(
            _say(
                "cli_serving",
                name=project["name"],
                port=args.port,
            )
        )
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
            print(_say("cli_error", error=exc), file=sys.stderr)
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        print(
            _say(
                "cli_decision_recorded",
                scope=_say(f"cli_scope_{record['scope']}"),
                decision=record["decision"],
                project=record["project_id"],
                generation=record["generation"],
                actor=record["actor"],
            )
        )
        if record["decision"] != "approved":
            print(_say("cli_decision_gate"))
        elif record["scope"] == "production":
            print(_say("cli_decision_production"))
        else:
            print(
                _say(
                    "cli_decision_run",
                    project=record["project_id"],
                )
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
    print(_say("cli_daemon_paused"))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    settings = _settings(args)
    set_paused(settings.home, False)
    print(_say("cli_daemon_resumed"))
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        if args.action == "review":
            if not args.task_id:
                print(
                    _say("cli_task_review_requires"),
                    file=sys.stderr,
                )
                return 2
            from .model import build_model_client
            from .task_review import rerun_review

            model = build_model_client(
                settings.home,
                log=lambda message: print(message, file=sys.stderr),
            )
            if model is None:
                print(_say("cli_review_no_model"), file=sys.stderr)
                return 1
            try:
                updated = rerun_review(
                    settings,
                    ledger,
                    project,
                    args.task_id,
                    model,
                )
            except ValueError as exc:
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 1
            tasks.commit_task(
                layout,
                updated["id"],
                f"Review task {updated['id']}",
            )
            print(
                _say(
                    "cli_task_reviewed",
                    task=updated["id"],
                    status=_status_name(updated["status"]),
                )
            )
            return 0
        if args.action == "retry":
            if not args.task_id:
                print(
                    _say("cli_task_retry_requires"),
                    file=sys.stderr,
                )
                return 2
            try:
                task = tasks.retry_task(layout, args.task_id)
            except ValueError as exc:
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 1
            tasks.commit_task(
                layout, task["id"], f"Retry task {task['id']}"
            )
            print(
                _say(
                    "cli_task_requeued",
                    task=task["id"],
                    count=task["result"].get("manual_retries", 0),
                )
            )
            return 0
        if args.action in {"accept", "reject"}:
            if not args.task_id:
                print(
                    _say(
                        "cli_task_action_requires",
                        action=args.action,
                    ),
                    file=sys.stderr,
                )
                return 2
            task = tasks.get_task(layout, args.task_id)
            if task is None:
                print(
                    _say(
                        "cli_unknown_task",
                        task=args.task_id,
                    ),
                    file=sys.stderr,
                )
                return 1
            if args.action == "accept":
                updated = accept_task(
                    settings,
                    ledger,
                    project,
                    task,
                    actor=args.actor,
                    notes=args.notes,
                )
            else:
                updated = reject_task(
                    settings,
                    ledger,
                    project,
                    task,
                    actor=args.actor,
                    notes=args.notes,
                )
            tasks.commit_task(
                layout,
                updated["id"],
                f"{args.action.capitalize()} task {updated['id']}",
            )
            print(
                _say(
                    f"cli_task_{args.action}ed",
                    task=updated["id"],
                    status=_status_name(updated["status"]),
                )
            )
            return 0
        if args.action == "cancel":
            if not args.task_id:
                print(
                    _say("cli_task_cancel_requires"),
                    file=sys.stderr,
                )
                return 2
            try:
                task = tasks.cancel_task(layout, args.task_id)
            except ValueError as exc:
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 1
            tasks.commit_task(
                layout, task["id"], f"Cancel task {task['id']}"
            )
            print(_say("cli_task_cancelled", task=task["id"]))
            return 0
        if args.action == "list":
            entries = tasks.list_tasks(layout)
            if not entries:
                print(_say("cli_no_tasks"))
                return 0
            for task in entries:
                result = task.get("result", {})
                summary = result.get("summary", "") if result else ""
                print(
                    f"{task['id']:<40} "
                    f"{_status_name(task['status']):<8} "
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
                language=language.detect(
                    " ".join(
                        [args.title, *args.require, *args.accept]
                    )
                ),
            )
        except ValueError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
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


def cmd_release(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        try:
            result = release_project(
                settings,
                ledger,
                project,
                version=args.version,
                notes=args.notes,
                repo_id=args.repo,
                draft=args.draft,
                prerelease=args.prerelease,
                generate_notes=args.generate_notes,
                log=lambda message: print(message, file=sys.stderr),
            )
        except ReleaseError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        print(
            _say(
                "cli_release_header",
                version=result.tag,
                status=result.status,
                manifest=result.manifest,
            )
        )
        for item in result.repos:
            print(
                _say(
                    "cli_release_repo",
                    repo=item.repo_id,
                    tag=item.tag,
                    sha=item.sha,
                    detail=item.release_url or item.detail,
                )
            )
        return 0 if result.status != "failed" else 1
    finally:
        ledger.close()


def cmd_github(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        if args.action == "status":
            print(status_text(settings, project, lang=_UI_LANG))
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        print(
            _say(
                "cli_github_repository",
                repo=result.repo_id,
                full=result.full_name,
            )
        )
        print(
            _say(
                "cli_github_branch",
                branch=result.branch,
                base=result.base,
            )
        )
        print(
            _say(
                "cli_github_pull",
                number=result.pr_number,
                url=result.pr_url,
            )
            if result.pr_number
            else _say("cli_github_pushed")
        )
        print(_say("cli_github_checks", checks=result.checks))
        print(
            _say(
                "cli_github_merged",
                merged=_say(
                    "chat_yes" if result.merged else "chat_no"
                ),
            )
            + (f" ({result.merge_sha})" if result.merge_sha else "")
        )
        print(_say("cli_github_status", status=result.status))
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        project = ledger.get_project(result.project_id)
        layout = (
            ProjectLayout.detect(project["workspace"])
            if project is not None
            else None
        )
        print(_say("cli_adopt_project", project=result.project_id))
        print(
            _say(
                "cli_adopt_repo",
                repo=result.repo_id,
                provider=result.provider,
            )
        )
        print(_say("cli_adopt_url", url=result.url))
        if layout is not None and layout.is_linked:
            print(_say("cli_adopt_mode_linked"))
            print(
                _say(
                    "cli_adopt_control",
                    path=layout.control.relative_to(
                        layout.root
                    ).as_posix(),
                )
            )
        else:
            print(_say("cli_adopt_mode_cloned"))
        print(_say("cli_adopt_auth", detail=result.auth.detail))
        if result.provider == "local":
            print(_say("cli_adopt_note"))
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        layout = ProjectLayout.detect(project["workspace"])
        if args.action == "list":
            repos = manifest_entries(layout)
            if not repos:
                print(_say("cli_no_repositories"))
                return 0
            for entry in repos:
                depends = (
                    ", ".join(entry["depends_on"])
                    or _say("cli_none")
                )
                print(
                    _say(
                        "cli_repo_line",
                        id=entry["id"],
                        role=entry["role"],
                        provider=entry["provider"],
                        url=repo_location(layout, entry) or "—",
                        depends=depends,
                    )
                )
            return 0
        depends = [item for item in args.depends_on.split(",") if item]
        if args.action == "create":
            if not args.id:
                print(
                    _say("cli_repo_create_requires"),
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
                    path=args.path,
                )
            except (AdoptError, ProviderError, GithubAuthError) as exc:
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 1
            print(
                _say(
                    "cli_repo_created",
                    repo=created.entry["id"],
                    url=created.url,
                    project=project["id"],
                )
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
                print(_say("cli_repo_nothing_to_publish"))
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
                        _say(
                            "cli_repo_publish_error",
                            repo=repo_id,
                            error=exc,
                        ),
                        file=sys.stderr,
                    )
                    return 1
                print(
                    _say(
                        "cli_repo_published",
                        repo=repo_id,
                        url=published.url,
                    )
                )
            return 0
        if args.action == "link":
            if not args.url:
                print(
                    _say("cli_repo_link_requires"),
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
                print(_say("cli_error", error=exc), file=sys.stderr)
                return 1
            edges = (
                ", ".join(entry["depends_on"])
                or _say("cli_none")
            )
            print(
                _say(
                    "cli_repo_updated",
                    repo=entry["id"],
                    edges=edges,
                )
            )
            return 0
        if not args.url:
            print(_say("cli_repo_add_requires"), file=sys.stderr)
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
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        print(
            _say(
                "cli_repo_added",
                repo=result.entry["id"],
                provider=result.entry["provider"],
                project=project["id"],
            )
        )
        if result.entry["depends_on"]:
            print(
                _say(
                    "cli_repo_depends_on",
                    edges=", ".join(result.entry["depends_on"]),
                )
            )
        else:
            print(_say("cli_repo_standalone"))
        return 0
    finally:
        ledger.close()


def cmd_deploy(args: argparse.Namespace) -> int:
    target = Path(args.file)
    try:
        if args.action == "init":
            path = deploy_init(target)
            print(_say("cli_deploy_created", path=path))
            return 0
        config = DeployConfig.from_file(target)
        try:
            mode = target.stat().st_mode & 0o777
            if mode & 0o077:
                print(
                    _say(
                        "cli_chmod_warning",
                        path=target,
                        mode=f"{mode:o}",
                    ),
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
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    settings = _settings(args)
    issues: list[str] = []

    def report(label: str, value: str, ok: bool = True) -> None:
        key = _DOCTOR_LABELS.get(label)
        name = _say(key) if key else label
        print(f"{'OK  ' if ok else 'WARN'} {name:<22} {value}")
        if not ok:
            issues.append(name)

    print(_say("cli_doctor_home", path=settings.home))
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
        report(
            "ledger",
            _say(
                "cli_doctor_projects",
                path=settings.db_path,
                count=count,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - doctor reports, never crashes
        report("ledger", str(exc), False)

    report(
        "control",
        _say(
            "cli_doctor_paused"
            if is_paused(settings.home)
            else "cli_doctor_running"
        ),
    )
    report(
        "context window",
        str(settings.context_window),
    )
    report("tokenizer", tokenizer_name())
    report(
        "task pipeline",
        _say(
            "cli_doctor_pipeline",
            qa=_say("cli_on" if settings.task_qa else "cli_off"),
            review=_say(
                "cli_on" if settings.task_review else "cli_off"
            ),
            accept=settings.task_accept,
        ),
    )
    if peak.should_defer(
        settings.peak_policy, hours=settings.peak_hours
    ):
        boundary = peak.next_off_peak(hours=settings.peak_hours)
        report(
            "model schedule",
            _say(
                "cli_doctor_peak",
                policy=settings.peak_policy,
                moment=boundary.strftime("%H:%M UTC"),
            ),
        )
    else:
        report(
            "model schedule",
            _say(
                "cli_doctor_off_peak",
                policy=settings.peak_policy,
            ),
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
            ", ".join(settings.sandbox_images)
            or _say("cli_doctor_any_image"),
        )
        report(
            "sandbox limits",
            _say(
                "cli_doctor_limits",
                cpus=settings.sandbox_cpus,
                memory=settings.sandbox_memory,
                pids=settings.sandbox_pids,
                network=settings.sandbox_network,
                digest=(
                    _say("cli_doctor_digest")
                    if settings.sandbox_require_digest
                    else ""
                ),
            ),
        )
    else:
        report("sandbox", _say("cli_doctor_local"))

    try:
        telegram = TelegramConfig.from_env(home=settings.home)
        report(
            "telegram",
            _say(
                "cli_doctor_telegram_value",
                count=len(telegram.allowed_chat_ids),
                timeout=telegram.poll_timeout,
            ),
        )
    except TelegramConfigError as exc:
        report("telegram", str(exc), False)

    model = build_model_client(settings.home, log=lambda _m: None)
    if model is None:
        report(
            "model",
            _say("cli_doctor_model_missing"),
            False,
        )
    else:
        report("model", type(model).__name__)

    github = GithubAuth(settings.home)
    status = github.status(_UI_LANG)
    report(
        "github auth",
        status,
        status != _say("github_auth_none"),
    )

    for tool in ("git", "docker", "node", "npm"):
        path = shutil.which(tool)
        report(
            tool,
            path or _say("cli_doctor_not_found"),
            path is not None,
        )
    if shutil.which("git"):
        version = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=False
        ).stdout.strip()
        report("git version", version)

    if issues:
        print(_say("cli_doctor_result_issues", items=", ".join(issues)))
        return 1
    print(_say("cli_doctor_result_ok"))
    return 0


def cmd_secret(args: argparse.Namespace) -> int:
    settings = _settings(args)
    if args.action == "list":
        for key, state in secret_status(settings.home).items():
            print(f"{key:<26} {state}")
        return 0
    if not args.key:
        print(_say("cli_secret_key_required"), file=sys.stderr)
        return 2
    try:
        if args.action == "set":
            if sys.stdin.isatty():
                value = getpass.getpass(f"{args.key}: ")
            else:
                value = sys.stdin.readline().strip()
            if not value:
                print(
                    _say("cli_secret_empty"),
                    file=sys.stderr,
                )
                return 2
            path = set_secret(settings.home, args.key, value)
            print(
                _say(
                    "cli_secret_saved",
                    key=args.key,
                    file=path,
                )
            )
        else:
            removed = delete_secret(settings.home, args.key)
            if removed:
                print(_say("cli_secret_deleted", key=args.key))
            else:
                print(_say("cli_secret_missing", key=args.key))
        return 0
    except (SecretError, OSError) as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1


def cmd_plan(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            return 1
        if args.status:
            layout = ProjectLayout.detect(project["workspace"])
            summary = plan_status(layout)
            if summary["status"] == "none":
                print(_say("cli_no_plans"))
                return 0
            print(
                _say(
                    "chat_plan_status_header",
                    plan=summary["plan_id"],
                    status=_plan_status_name(summary["status"]),
                    count=len(summary["tasks"]),
                )
            )
            if summary["goal"]:
                print(
                    _say(
                        "chat_plan_goal",
                        goal=summary["goal"],
                    )
                )
            for item in summary["tasks"]:
                suffix = (
                    _say(
                        "cli_plan_blocked",
                        blocked=item["blocked_by"],
                    )
                    if item["blocked_by"]
                    else ""
                )
                print(
                    _say(
                        "cli_plan_status_task",
                        status=_status_name(item["status"]),
                        title=item["title"],
                        suffix=suffix,
                    )
                )
            return 0
        if not args.goal:
            print(_say("cli_plan_requires"), file=sys.stderr)
            return 2
        try:
            result = plan_project(
                settings,
                ledger,
                project,
                args.goal,
                max_tasks=args.max_tasks,
                dry_run=args.dry_run,
                release_class=args.release_class,
            )
        except PlanningError as exc:
            print(_say("cli_error", error=exc), file=sys.stderr)
            print(_say("cli_plan_not_created"), file=sys.stderr)
            return 1
        print(
            _say(
                "cli_plan_header",
                plan=result.plan_id,
                count=len(result.tasks),
                dry_run=(
                    _say("cli_plan_dry_run_suffix")
                    if result.dry_run
                    else ""
                ),
            )
        )
        if result.notes:
            print(result.notes)
        for index, item in enumerate(result.tasks, 1):
            depends = (
                ", ".join(
                    str(value) for value in item["depends_on"]
                )
                or _say("cli_none")
            )
            identifier = item.get("task_id") or "-"
            print(
                _say(
                    "cli_plan_entry",
                    index=index,
                    title=item["title"],
                    repo=item.get("repo_id") or _say("cli_sole"),
                    deps=depends,
                    task=identifier,
                )
            )
            checks = item.get("checks") or []
            if checks:
                print(
                    _say(
                        "cli_plan_checks",
                        checks="; ".join(
                            check["criterion"] for check in checks
                        ),
                    )
                )
        if result.artifact:
            print(
                _say(
                    "cli_plan_artifact",
                    path=result.artifact,
                )
            )
        return 0
    finally:
        ledger.close()




def cmd_control(args: argparse.Namespace) -> int:
    settings = _settings(args)
    ledger = _ledger(settings)
    try:
        project = resolve_project(ledger, args.project_id)
        if args.action != "extract":
            print(_say("cli_control_usage"), file=sys.stderr)
            return 2
        result = extract_control(settings, ledger, project, args.path)
        print(_say("cli_control", path=result.control))
        print(
            _say(
                "cli_control_moved",
                items=", ".join(result.moved)
                or _say("cli_control_nothing"),
            )
        )
        print(_say("cli_control_note"))
        return 0
    except (ProjectError, AdoptError) as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1
    finally:
        ledger.close()

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


def cmd_scenario(args: argparse.Namespace) -> int:
    _settings(args)  # load the local env; the sandbox has its own home
    data = (
        scenario.load_scenario(Path(args.scenario))
        if str(args.scenario or "").strip()
        else {}
    )
    messages = list(args.message or data.get("messages") or [])
    if not messages:
        print(
            _say("cli_error", error="a scenario needs at least one message"),
            file=sys.stderr,
        )
        return 2
    fixture = Path(
        str(args.fixture or data.get("fixture") or ".")
    ).expanduser()
    snapshot = str(args.snapshot or data.get("snapshot") or "")
    try:
        sandbox = scenario.create_sandbox(
            fixture,
            snapshot,
            root=Path(args.root).expanduser() if args.root else None,
            keep=bool(args.keep),
        )
    except scenario.ScenarioError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1
    try:
        scenario.apply_seed(sandbox, data.get("seed"))
        client = build_model_client(sandbox.settings.home)
        if client is None:
            print(
                _say(
                    "cli_error",
                    error="no model is configured for the scenario",
                ),
                file=sys.stderr,
            )
            return 1
        print("Sandbox: %s" % sandbox.root)
        sandbox.run(
            messages,
            client=client,
            execute=bool(args.execute),
            log=print,
        )
        return 0
    finally:
        sandbox.close()


def cmd_telegram(args: argparse.Namespace) -> int:
    settings = _settings(args)
    try:
        config = TelegramConfig.from_env(home=settings.home)
    except TelegramConfigError as exc:
        print(_say("cli_error", error=exc), file=sys.stderr)
        return 1
    ledger = _ledger(settings)
    try:
        print(
            _say(
                "cli_telegram_started",
                count=len(config.allowed_chat_ids),
            ),
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

    limit = subparsers.add_parser(
        "limit", help="Show or raise a runtime limit"
    )
    limit.add_argument("project_id")
    limit.add_argument("name", nargs="?")
    limit.add_argument("seconds", nargs="?", type=float)
    limit.add_argument("--home", default=None)
    limit.set_defaults(func=cmd_limit)

    status = subparsers.add_parser("status", help="Show a project and its events")
    status.add_argument("project_id")
    status.add_argument("--home", default=None)
    status.set_defaults(func=cmd_status)

    listing = subparsers.add_parser("list", help="List projects")
    listing.add_argument("--home", default=None)
    listing.set_defaults(func=cmd_list)

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

    plan = subparsers.add_parser(
        "plan", help="Turn a milestone goal into queued tasks"
    )
    plan.add_argument("project_id")
    plan.add_argument("--goal", default="")
    plan.add_argument("--status", action="store_true")
    plan.add_argument("--max-tasks", type=int, default=8)
    plan.add_argument(
        "--release-class",
        choices=["patch", "minor", "major"],
        default="minor",
    )
    plan.add_argument("--dry-run", action="store_true")
    plan.add_argument("--home", default=None)
    plan.set_defaults(func=cmd_plan)

    control = subparsers.add_parser(
        "control", help="Move a linked project's state into a separate repository"
    )
    control.add_argument("action", choices=["extract"])
    control.add_argument("project_id")
    control.add_argument("--path", default="")
    control.add_argument("--home", default=None)
    control.set_defaults(func=cmd_control)

    setup = subparsers.add_parser(
        "setup", help="Create a local .env.local setup file"
    )
    setup.add_argument("--force", action="store_true")
    setup.set_defaults(func=cmd_setup)

    chat = subparsers.add_parser(
        "chat", help="Local console: the same commands without Telegram"
    )
    chat.add_argument("--project", default="")
    chat.add_argument("--no-daemon", action="store_true")
    chat.add_argument("--actor", default="local")
    chat.add_argument("--home", default=None)
    chat.set_defaults(func=cmd_chat)

    sandbox = subparsers.add_parser(
        "scenario",
        help=(
            "Run a real scenario in an isolated sandbox: no provider, no "
            "push, no release on a real remote"
        ),
    )
    sandbox.add_argument("--fixture", default="")
    sandbox.add_argument("--snapshot", default="")
    sandbox.add_argument("--scenario", default="")
    sandbox.add_argument("--message", action="append", default=[])
    sandbox.add_argument("--execute", action="store_true")
    sandbox.add_argument("--keep", action="store_true")
    sandbox.add_argument("--root", default="")
    sandbox.add_argument("--home", default=None)
    sandbox.set_defaults(func=cmd_scenario)

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
    task.add_argument(
        "action",
        choices=[
            "add",
            "list",
            "cancel",
            "retry",
            "accept",
            "reject",
            "review",
        ],
    )
    task.add_argument("project_id")
    task.add_argument("--task", dest="task_id", default="")
    task.add_argument("--actor", default="owner")
    task.add_argument("--notes", default="")
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

    release = subparsers.add_parser(
        "release", help="Tag and publish a project release"
    )
    release.add_argument("project_id")
    release.add_argument("--version", default="")
    release.add_argument("--notes", default="")
    release.add_argument("--repo", default="")
    release.add_argument("--draft", action="store_true")
    release.add_argument("--prerelease", action="store_true")
    release.add_argument(
        "--generate-notes",
        dest="generate_notes",
        action="store_true",
        help="Ask GitHub to generate release notes from commits",
    )
    release.add_argument("--home", default=None)
    release.set_defaults(func=cmd_release)

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
    repo.add_argument("--path", default="")
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
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        # `forgel` alone is the local client, like opening a chat.
        arguments = ["chat"]
    _set_ui_language(arguments)
    args = parser.parse_args(arguments)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001 - never abort without an answer
        print(_say("cli_error", error=exc), file=sys.stderr)
        print(_say("cli_operation_stopped"), file=sys.stderr)
        return 1
