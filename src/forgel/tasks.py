"""Task records for the coding agent.

A task is a small JSON file in the control repository. The daemon picks the
first pending task, the coding agent implements it, and the task records the
result. Files, not a second database, keep the work reviewable in git.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import git_ops
from .artifacts import read_json, write_json
from .layout import ProjectLayout

TASKS_DIR = "docs/program/tasks"
VALID_STATUSES = {
    "pending",
    "running",
    "review",
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
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    title = title.strip()
    requirements = [item.strip() for item in requirements if item.strip()]
    acceptance = [item.strip() for item in acceptance if item.strip()]
    if not title:
        raise ValueError("a task needs a title")
    if not requirements:
        raise ValueError("a task needs at least one requirement")
    if not acceptance:
        raise ValueError("a task needs at least one acceptance criterion")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    task_id = f"{timestamp}_{_slug(title)}"
    data = {
        "id": task_id,
        "title": title,
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
        "order": order,
        "depends_on": [
            item for item in (depends_on or []) if item
        ],
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


def _dependency_blockers(
    task: dict[str, Any], statuses: dict[str, str]
) -> list[str]:
    return [
        dep
        for dep in (task.get("depends_on") or [])
        if statuses.get(dep) != "done"
    ]


def blocked_pending(layout: ProjectLayout) -> list[dict[str, Any]]:
    """Pending tasks whose dependencies are not done yet (or have failed)."""

    tasks = list_tasks(layout)
    statuses = {str(task["id"]): str(task.get("status")) for task in tasks}
    return [
        task
        for task in tasks
        if task.get("status") == "pending"
        and _dependency_blockers(task, statuses)
    ]


def next_pending_task(layout: ProjectLayout) -> dict[str, Any] | None:
    tasks = list_tasks(layout)
    statuses = {str(task["id"]): str(task.get("status")) for task in tasks}
    for task in tasks:
        if task.get("status") != "pending":
            continue
        if not _dependency_blockers(task, statuses):
            return task
    return None


def latest_task(layout: ProjectLayout) -> dict[str, Any] | None:
    tasks = list_tasks(layout)
    return tasks[-1] if tasks else None


def cancel_task(layout: ProjectLayout, task_id: str) -> dict[str, Any]:
    task = get_task(layout, task_id)
    if task is None:
        raise ValueError(f"unknown task {task_id!r}")
    if task.get("status") != "pending":
        raise ValueError(
            f"only pending tasks can be cancelled (status: {task.get('status')})"
        )
    return update_task(
        layout,
        task_id,
        status="cancelled",
        finished_at=_now(),
        result={"summary": "cancelled by the user"},
    )


def commit_task(
    layout: ProjectLayout, task_id: str, message: str
) -> None:
    """Commit a task file to the control repository, best effort."""

    if not (layout.control / ".git").exists():
        return
    try:
        git_ops.commit_all(layout.control, message)
        git_ops.tag_baseline(layout.control)
    except git_ops.GitOperationError:
        return
