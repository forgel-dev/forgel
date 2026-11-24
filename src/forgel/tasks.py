"""Task records for the coding agent.

A task is a small JSON file in the control repository. The daemon picks the
first pending task, the coding agent implements it, and the task records the
result. Files, not a second database, keep the work reviewable in git.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import git_ops
from .artifacts import read_json, write_json
from .layout import ProjectLayout

TASKS_DIR = "docs/program/tasks"
CONTROL_PATHS = (
    "forgel.toml",
    "program.yaml",
    "FORGEL.md",
    "AGENTS.md",
    ".gitignore",
    "docs/program",
)
VALID_STATUSES = {
    "pending",
    "running",
    "review",
    "blocked",
    "done",
    "failed",
    "cancelled",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "task"


def tasks_dir(layout: ProjectLayout) -> Path:
    return layout.artifact(TASKS_DIR)


def task_path(layout: ProjectLayout, task_id: str) -> Path:
    return tasks_dir(layout) / f"{task_id}.json"


def _normalize_check(item: dict[str, Any]) -> dict[str, Any]:
    """One acceptance check: a command, or an explicit review criterion."""

    if not isinstance(item, dict):
        raise ValueError("a check must be an object")
    criterion = str(item.get("criterion", "")).strip()
    if not criterion:
        raise ValueError("a check needs a criterion")
    verification = str(item.get("verification", "command")).strip().lower()
    if verification not in {"command", "review"}:
        raise ValueError(
            f"check {criterion!r}: verification must be command or review"
        )
    command = item.get("command", [])
    if isinstance(command, str):
        command = [command]
    if not isinstance(command, list):
        raise ValueError(f"check {criterion!r}: command must be a list")
    command = [str(value) for value in command if str(value).strip()]
    if verification == "command" and not command:
        raise ValueError(
            f"check {criterion!r}: a command check needs a command"
        )
    return {
        "criterion": criterion,
        "verification": verification,
        "command": command,
    }


def new_task_id(title: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{timestamp}_{_slug(title)}"


def create_task(
    layout: ProjectLayout,
    title: str,
    requirements: list[str],
    acceptance: list[str],
    constraints: list[str] | None = None,
    repo_id: str = "",
    test_command: list[str] | None = None,
    assumptions: list[str] | None = None,
    plan_id: str = "",
    plan_goal: str = "",
    order: int = 0,
    checks: list[dict[str, Any]] | None = None,
    language: str = "",
    spec: str = "",
    external_dependencies: list[dict[str, Any]] | None = None,
    task_id: str = "",
    release_id: str = "",
    release_class: str = "",
    summary: str = "",
) -> dict[str, Any]:
    title = title.strip()
    requirements = [item.strip() for item in requirements if item.strip()]
    acceptance = [item.strip() for item in acceptance if item.strip()]
    if not title:
        raise ValueError("a task needs a title")
    if not spec and not requirements:
        raise ValueError("a task needs at least one requirement")
    if not spec and not acceptance:
        raise ValueError("a task needs at least one acceptance criterion")
    task_id = task_id.strip() or new_task_id(title)
    data = {
        "id": task_id,
        "title": title,
        "spec": spec.strip(),
        "summary": summary.strip(),
        "requirements": requirements,
        "acceptance": acceptance,
        "constraints": [
            item.strip() for item in (constraints or []) if item.strip()
        ],
        "repo_id": repo_id,
        "test_command": list(test_command or []),
        "assumptions": [
            item.strip() for item in (assumptions or []) if item.strip()
        ],
        "plan_id": plan_id,
        "plan_goal": plan_goal,
        "release_id": release_id.strip(),
        "release_class": release_class.strip().lower(),
        "order": order,
        "checks": [_normalize_check(item) for item in (checks or [])],
        "external_dependencies": [
            dict(item) for item in (external_dependencies or [])
            if isinstance(item, dict)
        ],
        "language": language.strip().lower(),
        "status": "pending",
        "created_at": _now(),
        "started_at": "",
        "finished_at": "",
        "result": {},
    }
    write_json(task_path(layout, task_id), data)
    return data


def list_tasks(layout: ProjectLayout) -> list[dict[str, Any]]:
    directory = tasks_dir(layout)
    if not directory.exists():
        return []
    tasks: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = read_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id"):
            tasks.append(data)
    return tasks


def get_task(
    layout: ProjectLayout, task_id: str
) -> dict[str, Any] | None:
    path = task_path(layout, task_id)
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def update_task(
    layout: ProjectLayout, task_id: str, **updates: Any
) -> dict[str, Any]:
    task = get_task(layout, task_id)
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"unknown task status {updates['status']!r}")
    task.update(updates)
    write_json(task_path(layout, task_id), task)
    return task


def recover_running(
    layout: ProjectLayout, max_resumes: int = 3
) -> list[dict[str, Any]]:
    """Requeue tasks left running by an interrupted process.

    A single daemon is assumed. The durable agent state file, when present, is
    read by the next coding-agent session; the task record keeps the resume
    count so a crash loop stops after ``max_resumes`` attempts.
    """

    recovered: list[dict[str, Any]] = []
    for task in list_tasks(layout):
        if task.get("status") != "running":
            continue
        result = dict(task.get("result") or {})
        count = int(result.get("resume_count", 0)) + 1
        if count > max_resumes:
            result["summary"] = (
                f"interrupted {count - 1} times; not retried again"
            )
            recovered.append(
                update_task(
                    layout,
                    str(task["id"]),
                    status="failed",
                    finished_at=_now(),
                    result=result,
                )
            )
            continue
        result["resume_count"] = count
        result["resumed_at"] = _now()
        if result.get("summary"):
            result["last_summary"] = result["summary"]
        recovered.append(
            update_task(
                layout,
                str(task["id"]),
                status="pending",
                started_at="",
                finished_at="",
                result=result,
            )
        )
    return recovered


def blocked_pending(layout: ProjectLayout) -> list[dict[str, Any]]:
    """Tasks explicitly blocked and waiting for a decision."""

    return [
        task
        for task in list_tasks(layout)
        if task.get("status") == "blocked"
    ]


def stop_plan(
    layout: ProjectLayout, failed_id: str
) -> list[dict[str, Any]]:
    """Halt the failed task's plan: its pending and blocked tasks stop."""

    tasks = list_tasks(layout)
    failed = next(
        (task for task in tasks if task["id"] == failed_id), None
    )
    if failed is None:
        return []
    plan_id = str(failed.get("plan_id") or "")
    if not plan_id:
        return []
    changed: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task["id"])
        if task_id == failed_id or task.get("plan_id") != plan_id:
            continue
        if task.get("status") not in {"pending", "blocked"}:
            continue
        data = dict(task.get("result") or {})
        data["blocked_by"] = failed_id
        changed.append(
            update_task(
                layout,
                task_id,
                status="blocked",
                result=data,
            )
        )
    return changed


def unblock_for_retry(
    layout: ProjectLayout, task_id: str
) -> list[dict[str, Any]]:
    """Return the tasks stopped by ``task_id`` to pending."""

    changed: list[dict[str, Any]] = []
    for task in list_tasks(layout):
        if task.get("status") != "blocked":
            continue
        data = dict(task.get("result") or {})
        if data.get("blocked_by") != task_id:
            continue
        data.pop("blocked_by", None)
        changed.append(
            update_task(
                layout, str(task["id"]), status="pending", result=data
            )
        )
    return changed


def retry_task(
    layout: ProjectLayout, task_id: str
) -> dict[str, Any]:
    """Manually requeue a task and release what its failure stopped.

    Any status can be requeued: a running task that a human or controller
    wants to run again, a task in review, or a finished one. The task keeps
    its specification and its result; only the execution counters reset.
    """

    task = get_task(layout, task_id)
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if task.get("status") == "cancelled":
        raise ValueError(f"task {task_id} is cancelled")
    data = dict(task.get("result") or {})
    if data.get("failure"):
        data["last_failure"] = data["failure"]
    data.pop("failure", None)
    data.pop("retry_after", None)
    data["attempts"] = 0
    data["rework_count"] = 0
    data["manual_retries"] = int(data.get("manual_retries", 0)) + 1
    updated = update_task(
        layout,
        task_id,
        status="pending",
        started_at="",
        finished_at="",
        result=data,
    )
    unblock_for_retry(layout, task_id)
    return updated


def restart_task(
    layout: ProjectLayout, task_id: str
) -> dict[str, Any]:
    """Clear a task's result and put it back to pending, from the beginning.

    The caller rewrites the specification first; this only resets the task
    state. Any status is accepted, including a running or finished task.
    """

    task = get_task(layout, task_id)
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if task.get("status") == "cancelled":
        raise ValueError(f"task {task_id} is cancelled")
    previous = dict(task.get("result") or {})
    updated = update_task(
        layout,
        task_id,
        status="pending",
        started_at="",
        finished_at="",
        result={
            "manual_restarts": int(
                previous.get("manual_restarts", 0)
            )
            + 1,
            "restarted_at": _now(),
        },
    )
    unblock_for_retry(layout, task_id)
    return updated


def retry_moment(task: dict[str, Any]) -> datetime | None:
    """When a delayed retry becomes runnable, or ``None``."""

    value = (task.get("result") or {}).get("retry_after")
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def waiting_pending(
    layout: ProjectLayout, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Pending tasks whose backoff has not elapsed yet."""

    moment = now or datetime.now(timezone.utc)
    return [
        task
        for task in list_tasks(layout)
        if task.get("status") == "pending"
        and (retry_moment(task) or moment) > moment
    ]


def retry_times(layout: ProjectLayout) -> list[datetime]:
    return [
        moment
        for task in list_tasks(layout)
        if task.get("status") == "pending"
        for moment in [retry_moment(task)]
        if moment is not None
    ]


def attempt_number(task: Mapping[str, Any]) -> int:
    """The rework attempt of a task: 0 for the first run."""

    result = task.get("result") or {}
    try:
        return max(0, int(result.get("rework_count") or 0))
    except (TypeError, ValueError):
        return 0


def _retry_ready(
    task: dict[str, Any], now: datetime | None = None
) -> bool:
    moment = retry_moment(task)
    if moment is None:
        return True
    return (now or datetime.now(timezone.utc)) >= moment


def next_pending_task(
    layout: ProjectLayout,
    now: datetime | None = None,
    release_id: str = "",
) -> dict[str, Any] | None:
    tasks = list_tasks(layout)
    for task in tasks:
        if task.get("status") != "pending":
            continue
        if release_id and str(task.get("release_id") or "") != release_id:
            continue
        if not _retry_ready(task, now):
            continue
        return task
    return None


def listed_tasks(layout: ProjectLayout) -> list[dict[str, Any]]:
    """The task list shown to the user: cancelled work is removed from it."""

    return [
        task
        for task in list_tasks(layout)
        if task.get("status") != "cancelled"
    ]


def latest_task(layout: ProjectLayout) -> dict[str, Any] | None:
    """The task launched most recently, or the latest created when none was."""

    tasks = listed_tasks(layout)
    if not tasks:
        return None
    return max(
        tasks,
        key=lambda task: (
            _launch_moment(task),
            _task_touch(layout, task),
        ),
    )


def current_task(layout: ProjectLayout) -> dict[str, Any] | None:
    """The task the runtime is working on now: a running task, else the last
    launched one.

    An implicit operation ("restart the current task") targets the running
    task first, then the task launched most recently. File-name order is never
    used to decide which task is current.
    """

    tasks = listed_tasks(layout)
    running = [
        task for task in tasks if task.get("status") == "running"
    ]
    if running:
        return max(
            running,
            key=lambda task: (
                _launch_moment(task),
                _task_touch(layout, task),
            ),
        )
    return latest_task(layout)


def _moment(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _launch_moment(task: Mapping[str, Any]) -> datetime:
    result = task.get("result") or {}
    launched = [
        _moment(task.get("started_at")),
        _moment(result.get("restarted_at")),
    ]
    latest = max(
        (moment for moment in launched if moment is not None),
        default=None,
    )
    if latest is not None:
        return latest
    return (
        _moment(task.get("created_at"))
        or datetime.min.replace(tzinfo=timezone.utc)
    )


def _task_touch(layout: ProjectLayout, task: Mapping[str, Any]) -> float:
    try:
        return task_path(
            layout, str(task.get("id") or "")
        ).stat().st_mtime
    except OSError:
        return 0.0


def cancel_task(
    layout: ProjectLayout, task_id: str, notes: str = ""
) -> dict[str, Any]:
    """Cancel a task in any status.

    The record and its result stay: the task's commits are kept for the
    release audit, which decides whether to keep or revert them.
    """

    task = get_task(layout, task_id)
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if task.get("status") == "cancelled":
        return task
    summary = "cancelled by the user"
    if notes:
        summary += f": {notes}"
    data = dict(task.get("result") or {})
    data["summary"] = summary
    data["cancelled_at"] = _now()
    return update_task(
        layout,
        task_id,
        status="cancelled",
        finished_at=_now(),
        result=data,
    )


def commit_control(layout: ProjectLayout, message: str) -> None:
    """Commit project artifacts, best effort, without touching product work."""

    if layout.is_linked:
        if layout.control.resolve() != layout.root.resolve():
            if (layout.control / ".git").exists():
                try:
                    git_ops.commit_all(layout.control, message)
                except git_ops.GitOperationError:
                    return
            return
        paths = [
            item for item in CONTROL_PATHS if (layout.root / item).exists()
        ]
        if not paths:
            return
        try:
            git_ops.commit_paths(layout.root, paths, message)
        except git_ops.GitOperationError:
            return
        return
    if not (layout.control / ".git").exists():
        return
    try:
        git_ops.commit_all(layout.control, message)
    except git_ops.GitOperationError:
        return


def commit_task(
    layout: ProjectLayout, task_id: str, message: str
) -> None:
    """Commit a task file to the control repository, best effort."""

    if layout.is_linked:
        commit_control(layout, message)
        return
    if not (layout.control / ".git").exists():
        return
    try:
        git_ops.commit_all(layout.control, message)
        git_ops.tag_baseline(layout.control)
    except git_ops.GitOperationError:
        return
