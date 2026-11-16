"""Machine-readable client commands.

Every operation the local client shows is a parameterized ``forgel`` subcommand.
With ``--json`` a command writes exactly one JSON object to stdout and nothing
else; without the flag it keeps the human-readable text.

The envelope is flat: ``ok``, ``kind``, ``text``, ``error`` plus one
operation-specific field (``task``, ``tasks``, ``plan``, ``project``,
``projects``, ``history``, ``paused`` or ``cycles``). Free text goes through
:func:`forgel.outcome.handle_outcome`, which delegates to the same
``CommandRouter`` the console and Telegram use; the CLI never reimplements a
command.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from . import session as session_store
from . import tasks as task_store
from .agent import ProjectAgent
from .approvals import latest_approval
from .artifacts import read_json
from .chat import CommandRouter
from .config import Settings
from .control import is_paused, set_paused
from .daemon import project_state, run_daemon
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .outcome import handle_outcome
from .planner import PlanningError, plan_project, plan_status
from .projects import ProjectError, resolve_project
from .proposals import summarize_proposals
from .sync import reconciliation_status_path
from .task_review import accept_task, reject_task


def envelope(
    ok: bool, kind: str, text: str = "", error: str = "", **payload: Any
) -> dict[str, Any]:
    """Build the stable envelope: flags, kind, reply text, payload."""

    data: dict[str, Any] = {
        "ok": bool(ok),
        "kind": kind,
        "text": text,
        "error": error,
    }
    data.update(payload)
    return data


def write(data: dict[str, Any]) -> None:
    """Write exactly one JSON object."""

    print(json.dumps(data, ensure_ascii=False))


def emit(args: Any, data: dict[str, Any]) -> None:
    """JSON with ``--json``; the human-readable text otherwise."""

    if getattr(args, "json", False):
        write(data)
    else:
        print(data.get("text") or "")


def fail(args: Any, kind: str, message: str) -> int:
    """Report an error; a JSON client still gets exactly one object."""

    print(f"error: {message}", file=sys.stderr)
    if getattr(args, "json", False):
        write(envelope(False, kind, "", message))
    return 1


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def project_ref(project: dict[str, Any]) -> dict[str, Any]:
    return {"id": project["id"], "name": project["name"]}


def target(ledger: Ledger, args: Any) -> dict[str, Any]:
    """Resolve an explicit project id or the project selected for the session."""

    token = str(getattr(args, "project_id", "") or "").strip()
    if not token:
        token = (
            session_store.get_session_project(
                ledger, getattr(args, "session", None)
            )
            or ""
        )
    if not token:
        raise ProjectError(
            "no project selected; pass a project id or run "
            "`forgel session <project>`"
        )
    return resolve_project(ledger, token)


def task_view(task: dict[str, Any]) -> dict[str, Any]:
    result = dict(task.get("result") or {})
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "repo_id": task.get("repo_id") or "",
        "plan_id": task.get("plan_id") or "",
        "summary": str(result.get("summary") or ""),
        "created_at": task.get("created_at") or "",
    }


def say(settings: Settings, ledger: Ledger, args: Any) -> int:
    """Route one free-text message through the shared command router."""

    text = str(getattr(args, "text", "") or "").strip()
    if not text:
        text = " ".join(getattr(args, "words", None) or []).strip()
    if not text:
        return fail(
            args,
            "say",
            'say needs text: --text "..." or a trailing argument',
        )
    try:
        project = target(ledger, args)
    except ProjectError as exc:
        return fail(args, "say", str(exc))
    key = session_store.set_session_project(
        ledger, getattr(args, "session", None), project["id"]
    )
    agent = None
    client = build_model_client(settings.home, log=_log)
    if client is not None:
        agent = ProjectAgent(settings, ledger, client)
    router = CommandRouter(settings, ledger, daemon_enabled=True, agent=agent)
    actor = str(getattr(args, "actor", "") or "local")
    try:
        outcome = handle_outcome(
            router, session_store.ledger_key(key), text, actor
        )
    except Exception as exc:  # noqa: BLE001 - one bad turn must not crash
        return fail(args, "say", str(exc))
    payload = dict(outcome.payload)
    if payload.get("task") is not None:
        payload["task"] = task_view(payload["task"])
        payload["task_id"] = payload["task"].get("id")
    emit(args, envelope(True, outcome.kind, outcome.text, **payload))
    return 0


def projects_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return "no projects"
    lines = ["Projects: " + str(len(items))]
    for item in items:
        marker = "*" if item["selected"] else " "
        lines.append(
            f"{marker} {item['id']}  {item['name']}\n"
            f"    gen {item['generation']}  {item['state']}"
        )
    return "\n".join(lines)


def projects(settings: Settings, ledger: Ledger, args: Any) -> int:
    key = session_store.session_key(getattr(args, "session", None))
    selected = session_store.get_session_project(ledger, key)
    items = [
        {
            "id": project["id"],
            "name": project["name"],
            "generation": ledger.current_generation(project["id"]),
            "state": project_state(ledger, project),
            "selected": project["id"] == selected,
        }
        for project in ledger.list_projects()
    ]
    emit(
        args,
        envelope(
            True, "projects", projects_text(items), session=key, projects=items
        ),
    )
    return 0


def use(settings: Settings, ledger: Ledger, args: Any) -> int:
    try:
        project = resolve_project(ledger, str(args.project_id or ""))
    except ProjectError as exc:
        return fail(args, "use", str(exc))
    key = session_store.set_session_project(
        ledger, getattr(args, "session", None), project["id"]
    )
    emit(
        args,
        envelope(
            True,
            "use",
            f"Selected {project['name']} ({project['id']}) for session {key}.",
            session=key,
            project=project_ref(project),
        ),
    )
    return 0


def session(settings: Settings, ledger: Ledger, args: Any) -> int:
    """Read the session, or set its active project when one is given."""

    token = str(getattr(args, "project_id", "") or "").strip()
    if token:
        try:
            project = resolve_project(ledger, token)
        except ProjectError as exc:
            return fail(args, "session", str(exc))
        key = session_store.set_session_project(
            ledger, getattr(args, "session", None), project["id"]
        )
    else:
        key = session_store.session_key(getattr(args, "session", None))
    view = session_store.session_view(ledger, key)
    record = (
        {"id": view["project"], "name": view["name"]}
        if view["project"]
        else None
    )
    if record is not None:
        text = f"Session {key} selects {record['name']} ({record['id']})."
    else:
        text = f"Session {key} has no project selected."
    emit(args, envelope(True, "session", text, session=key, project=record))
    return 0


def history(settings: Settings, ledger: Ledger, args: Any) -> int:
    key = session_store.session_key(getattr(args, "session", None))
    view = session_store.session_view(ledger, key)
    limit = max(1, int(getattr(args, "limit", 20) or 20))
    items = session_store.conversation(ledger, key, limit=limit)
    record = (
        {"id": view["project"], "name": view["name"]}
        if view["project"]
        else None
    )
    project = record["id"] if record else "no project"
    emit(
        args,
        envelope(
            True,
            "history",
            f"History of session {key}: {len(items)} turn(s) in {project}.",
            session=key,
            project=record,
            history=items,
        ),
    )
    return 0


def tasks(settings: Settings, ledger: Ledger, args: Any) -> int:
    """List the task queue of one project."""

    try:
        project = target(ledger, args)
    except ProjectError as exc:
        return fail(args, "tasks", str(exc))
    layout = ProjectLayout.detect(project["workspace"])
    items = [task_view(task) for task in task_store.list_tasks(layout)]
    if items:
        lines = [f"Tasks: {len(items)}"]
        for item in items:
            lines.append(f"{item['id']}  {item['status']}  {item['title']}")
            if item["summary"]:
                lines.append(f"  {item['summary']}")
        text = "\n".join(lines)
    else:
        text = "No tasks. A change request sent as a plain message queues one."
    emit(
        args,
        envelope(
            True, "tasks", text, project=project_ref(project), tasks=items
        ),
    )
    return 0


def _finish_task(
    args: Any, project: dict[str, Any], updated: dict[str, Any], text: str
) -> int:
    emit(
        args,
        envelope(
            True,
            "task",
            text,
            project=project_ref(project),
            task=task_view(updated),
        ),
    )
    return 0


def task(settings: Settings, ledger: Ledger, args: Any) -> int:
    """Accept, reject, retry, cancel or queue a task."""

    try:
        project = target(ledger, args)
    except ProjectError as exc:
        return fail(args, "task", str(exc))
    layout = ProjectLayout.detect(project["workspace"])
    action = str(args.action)
    if action == "add":
        try:
            created = task_store.create_task(
                layout,
                title=args.title,
                requirements=args.require,
                acceptance=args.accept,
                constraints=args.constraint,
                repo_id=args.repo,
                test_command=(
                    args.test_command.split() if args.test_command else []
                ),
            )
        except ValueError as exc:
            return fail(args, "task", str(exc))
        task_store.commit_task(
            layout, created["id"], f"Add task {created['id']}"
        )
        return _finish_task(args, project, created, f"Queued {created['id']}.")
    task_id = str(getattr(args, "task_id", "") or "").strip()
    if not task_id:
        return fail(args, "task", f"task {action} requires --task")
    if action in {"retry", "cancel"}:
        try:
            updated = (
                task_store.retry_task(layout, task_id)
                if action == "retry"
                else task_store.cancel_task(layout, task_id)
            )
        except ValueError as exc:
            return fail(args, "task", str(exc))
        task_store.commit_task(
            layout,
            updated["id"],
            f"{action.capitalize()} task {updated['id']}",
        )
        verb = "Requeued" if action == "retry" else "Cancelled"
        return _finish_task(args, project, updated, f"{verb} {updated['id']}.")
    stored = task_store.get_task(layout, task_id)
    if stored is None:
        return fail(args, "task", f"unknown task {task_id!r}")
    actor = str(getattr(args, "actor", "") or "owner")
    notes = str(getattr(args, "notes", "") or "")
    decide = accept_task if action == "accept" else reject_task
    updated = decide(
        settings, ledger, project, stored, actor=actor, notes=notes
    )
    task_store.commit_task(
        layout, updated["id"], f"{action.capitalize()} task {updated['id']}"
    )
    return _finish_task(
        args,
        project,
        updated,
        f"{action.capitalize()}ed {updated['id']} ({updated['status']}).",
    )


def project_view(ledger: Ledger, project: dict[str, Any]) -> dict[str, Any]:
    project_id = project["id"]
    layout = ProjectLayout.detect(project["workspace"])
    state = ledger.checkpoint_state(project_id)
    checkpoint = state[0] if state is not None else "none"
    generation = (
        state[1] if state is not None else ledger.current_generation(project_id)
    )
    latest = task_store.latest_task(layout)
    staging: dict[str, Any] | None = None
    staging_path = layout.artifact("staging.json")
    if staging_path.exists():
        try:
            data = read_json(staging_path)
        except (OSError, json.JSONDecodeError):
            data = {}
        if data:
            staging = {
                "status": data.get("status"),
                "url": data.get("url"),
            }
    approvals: dict[str, Any] = {}
    for scope in ("staging", "production"):
        approval = latest_approval(ledger, project_id, scope, generation)
        approvals[scope] = (
            {
                "decision": approval["decision"],
                "actor": approval["actor"],
                "at": approval["created_at"],
            }
            if approval is not None
            else None
        )
    return {
        "id": project_id,
        "name": project["name"],
        "layout": layout.kind,
        "recipe": project.get("recipe_id") or None,
        "generation": generation,
        "checkpoint": checkpoint,
        "state": project_state(ledger, project),
        "task": task_view(latest) if latest is not None else None,
        "staging": staging,
        "approvals": approvals,
        "reconciliation": reconciliation_status_path(
            layout.artifact("docs/program/reconciliation.md")
        ),
        "proposals": len(summarize_proposals(layout.control)),
        "events": [
            {"stage": event["stage"], "status": event["status"]}
            for event in ledger.events(project_id, generation)[-8:]
        ],
    }


def status(settings: Settings, ledger: Ledger, args: Any) -> int:
    try:
        project = target(ledger, args)
    except ProjectError as exc:
        return fail(args, "status", str(exc))
    view = project_view(ledger, project)
    emit(
        args,
        envelope(
            True,
            "status",
            f"{project['id']}: {view['state']} "
            f"(generation {view['generation']}, "
            f"checkpoint {view['checkpoint']})",
            project=view,
        ),
    )
    return 0


def plan(settings: Settings, ledger: Ledger, args: Any) -> int:
    try:
        project = target(ledger, args)
    except ProjectError as exc:
        return fail(args, "plan", str(exc))
    layout = ProjectLayout.detect(project["workspace"])
    if getattr(args, "status", False):
        summary = plan_status(layout)
        if summary["status"] == "none":
            text = "no plans"
        else:
            text = (
                f"Plan {summary['plan_id']}: {summary['status']} "
                f"({len(summary['tasks'])} tasks)"
            )
        emit(
            args,
            envelope(
                True,
                "plan",
                text,
                project=project_ref(project),
                plan=summary,
            ),
        )
        return 0
    goal = str(getattr(args, "goal", "") or "").strip()
    if not goal:
        return fail(args, "plan", 'provide --goal "..." or --status')
    try:
        result = plan_project(
            settings,
            ledger,
            project,
            goal,
            max_tasks=args.max_tasks,
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    except PlanningError as exc:
        return fail(args, "plan", str(exc))
    emit(
        args,
        envelope(
            True,
            "plan",
            f"Plan {result.plan_id}: {len(result.tasks)} task(s)"
            + (" (dry run)" if result.dry_run else ""),
            project=project_ref(project),
            plan={
                "id": result.plan_id,
                "goal": result.goal,
                "notes": result.notes,
                "dry_run": result.dry_run,
                "artifact": result.artifact,
                "tasks": [
                    {
                        "title": item.get("title"),
                        "repo_id": item.get("repo_id") or "",
                        "task_id": item.get("task_id") or "",
                        "depends_on": list(item.get("depends_on") or []),
                    }
                    for item in result.tasks
                ],
            },
        ),
    )
    return 0


def pause(settings: Settings, ledger: Ledger, args: Any) -> int:
    set_paused(settings.home, True)
    emit(args, envelope(True, "control", "Daemon paused.", paused=True))
    return 0


def resume(settings: Settings, ledger: Ledger, args: Any) -> int:
    set_paused(settings.home, False)
    emit(args, envelope(True, "control", "Daemon resumed.", paused=False))
    return 0


def daemon(settings: Settings, ledger: Ledger, args: Any) -> int:
    cycles = run_daemon(
        settings,
        ledger,
        interval=args.interval,
        once=args.once,
        max_cycles=args.max_cycles,
        log=_log,
    )
    emit(
        args,
        envelope(
            True,
            "daemon",
            f"Daemon ran {cycles} cycle(s).",
            cycles=cycles,
            paused=is_paused(settings.home),
        ),
    )
    return 0
