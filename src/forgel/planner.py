"""Turn a milestone goal into an ordered backlog of coding tasks.

The planner is one model call with clean context: the project brief, the
repository graph, the environment contract, recent tasks and the goal. It
returns a small, ordered list of independently verifiable tasks with explicit
requirements, acceptance criteria and dependencies. The daemon then runs them
in order; a task whose dependency is not done is not picked up.

The plan is a project artifact: `docs/program/plans/<plan_id>.md`. `--dry-run`
shows the backlog without creating tasks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import peak, tasks
from .agent import build_context
from .artifacts import write_text
from .config import Settings
from .environment import load_environment
from .layout import ProjectLayout
from .ledger import Ledger
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    build_model_client,
    project_model_name,
)
from .program_manifest import entries as manifest_entries

MAX_TASKS = 20
DEFAULT_TASKS = 8


class PlanningError(RuntimeError):
    """The goal cannot be turned into a usable plan."""


@dataclass(frozen=True)
class PlanResult:
    plan_id: str
    goal: str
    notes: str
    tasks: list[dict[str, Any]] = field(default_factory=list)
    artifact: str = ""
    dry_run: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "goal"


def _plan_id(goal: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}_{_slug(goal)}"


def _system_prompt(max_tasks: int) -> str:
    return f"""You are Forgel's planner for exactly one project.

Turn the milestone goal into an ordered backlog of small coding tasks. The
daemon runs one task at a time; each task is one repository change that a
coding agent can implement, test and commit on its own.

Return exactly one JSON object:
{{
  "notes": "assumptions and ordering rationale in a few sentences",
  "tasks": [
    {{
      "title": "short imperative title",
      "requirements": ["explicit requirement", "..."],
      "acceptance": ["observable acceptance criterion", "..."],
      "constraints": ["constraint", "..."],
      "repo_id": "one of the project repositories, or empty for the sole one",
      "test_command": ["command", "arg"] or [],
      "depends_on": [0]
    }}
  ]
}}

Rules:
- Produce 1 to {max_tasks} tasks, in execution order.
- depends_on uses 0-based indexes of earlier tasks only; no cycles.
- One repository per task; do not mix repositories in one task.
- Give every task explicit requirements and acceptance criteria; the agent
  must not invent unstated features.
- Set test_command when the project's test command is evident from the
  environment contract or the repository; otherwise leave it empty.
- Do not create tasks for production deploys, payments, secrets, data
  destruction or legal decisions.
- Work autonomously: do not ask questions; put assumptions in "notes".
"""


def _context(layout: ProjectLayout, project: Mapping[str, Any], ledger: Ledger) -> str:
    repos = manifest_entries(layout)
    repo_lines = "\n".join(
        f"- {entry['id']} ({entry.get('role', 'application')}), "
        f"depends on: {', '.join(entry.get('depends_on') or []) or 'none'}"
        for entry in repos
    ) or "- none"
    try:
        environment = load_environment(layout)
    except Exception as exc:  # noqa: BLE001 - context is best effort
        environment_lines = f"- invalid environment: {exc}"
    else:
        if environment is None:
            environment_lines = "- no environment contract"
        else:
            environment_lines = (
                f"- image: {environment.image or environment.build}\n"
                f"- test: {list(environment.test) or 'none'}\n"
                f"- e2e: {list(environment.e2e) or 'none'}"
            )
    recent = tasks.list_tasks(layout)[-5:]
    recent_lines = "\n".join(
        f"- {item['title']} ({item.get('status')})" for item in recent
    ) or "- none"
    project_context = build_context(layout, project, ledger)
    return f"""Project: {project['name']} ({project['id']})
Brief: {project.get('brief', '')}

Repositories:
{repo_lines}

Environment:
{environment_lines}

Recent tasks:
{recent_lines}

Project context:
{project_context}
"""


def _parse_plan(
    raw: str,
    known_repos: Sequence[str],
    default_repo: str,
    max_tasks: int,
) -> tuple[str, list[dict[str, Any]]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise PlanningError("the planner did not return a JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise PlanningError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanningError("the plan must be a JSON object")
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise PlanningError("the plan has no tasks")
    if len(raw_tasks) > max_tasks:
        raise PlanningError(
            f"the plan has {len(raw_tasks)} tasks; the limit is {max_tasks}"
        )
    notes = str(data.get("notes", "")).strip()
    items: list[dict[str, Any]] = []
    titles: set[str] = set()
    for index, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            raise PlanningError(f"task {index} must be an object")
        title = str(item.get("title", "")).strip()
        requirements = [
            str(value).strip()
            for value in item.get("requirements", [])
            if str(value).strip()
        ]
        acceptance = [
            str(value).strip()
            for value in item.get("acceptance", [])
            if str(value).strip()
        ]
        constraints = [
            str(value).strip()
            for value in item.get("constraints", [])
            if str(value).strip()
        ]
        if not title:
            raise PlanningError(f"task {index} has no title")
        if title.lower() in titles:
            raise PlanningError(f"duplicate task title: {title!r}")
        titles.add(title.lower())
        if not requirements:
            raise PlanningError(f"task {index} has no requirements")
        if not acceptance:
            raise PlanningError(f"task {index} has no acceptance criteria")
        repo_id = str(item.get("repo_id", "")).strip() or default_repo
        if known_repos and repo_id not in known_repos:
            raise PlanningError(
                f"task {index} targets unknown repository {repo_id!r}"
            )
        command = item.get("test_command", [])
        if isinstance(command, str):
            command = [command]
        if not isinstance(command, list):
            raise PlanningError(f"task {index} test_command must be a list")
        depends = item.get("depends_on", [])
        if not isinstance(depends, list) or not all(
            isinstance(value, int) and 0 <= value < index
            for value in depends
        ):
            raise PlanningError(
                f"task {index} depends_on must reference earlier indexes"
            )
        items.append(
            {
                "title": title,
                "requirements": requirements,
                "acceptance": acceptance,
                "constraints": constraints,
                "repo_id": repo_id,
                "test_command": [str(value) for value in command],
                "depends_on": list(dict.fromkeys(depends)),
                "assumptions": [
                    str(value).strip()
                    for value in item.get("assumptions", [])
                    if str(value).strip()
                ],
            }
        )
    return notes, items


def plan_project(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    goal: str,
    max_tasks: int = DEFAULT_TASKS,
    dry_run: bool = False,
    client: ModelClient | None = None,
    log: Callable[[str], None] = print,
) -> PlanResult:
    """Ask the model for an ordered backlog and queue it as tasks."""

    goal = goal.strip()
    if not goal:
        raise PlanningError("a milestone goal is required")
    max_tasks = max(1, min(int(max_tasks), MAX_TASKS))
    layout = ProjectLayout.detect(str(project["workspace"]))
    if not layout.is_container:
        raise PlanningError(
            "planning requires a container project"
        )
    policy = peak.project_policy(settings, layout.control)
    if peak.should_defer(policy, hours=settings.peak_hours):
        raise PlanningError(
            peak.defer_message(
                hours=settings.peak_hours, tz_name=settings.timezone
            )
        )
    model_client = client or build_model_client(settings.home, log=log)
    if model_client is None:
        raise PlanningError(
            "no model configured; set FORGEL_MODEL_API_KEY or a secret"
        )
    repos = manifest_entries(layout)
    known = [str(entry["id"]) for entry in repos]
    default_repo = known[0] if len(known) == 1 else ""
    messages = [
        ModelMessage("system", _system_prompt(max_tasks)),
        ModelMessage(
            "user",
            f"Milestone goal:\n{goal}\n\n" + _context(layout, project, ledger),
        ),
    ]
    try:
        raw = model_client.complete(
            messages, model=project_model_name(layout.control)
        )
    except ModelError as exc:
        raise PlanningError(f"planner model call failed: {exc}") from exc
    notes, items = _parse_plan(raw, known, default_repo, max_tasks)
    plan_id = _plan_id(goal)
    if dry_run:
        return PlanResult(
            plan_id=plan_id,
            goal=goal,
            notes=notes,
            tasks=items,
            dry_run=True,
        )
    created: list[dict[str, Any]] = []
    ids: list[str] = []
    for index, item in enumerate(items):
        dependencies = [ids[position] for position in item["depends_on"]]
        task = tasks.create_task(
            layout,
            item["title"],
            item["requirements"],
            item["acceptance"],
            item["constraints"],
            repo_id=item["repo_id"],
            test_command=item["test_command"],
            assumptions=item["assumptions"],
            plan_id=plan_id,
            plan_goal=goal,
            order=index + 1,
            depends_on=dependencies,
        )
        ids.append(str(task["id"]))
        created.append(
            {
                **item,
                "task_id": task["id"],
                "depends_on": dependencies,
            }
        )
    path = layout.artifact(f"docs/program/plans/{plan_id}.md")
    task_lines = "\n".join(
        f"{index}. `{item['task_id']}` {item['title']}\n"
        f"   - repo: {item['repo_id'] or '(sole)'}\n"
        f"   - depends on: {', '.join(item['depends_on']) or 'none'}\n"
        f"   - requirements: {'; '.join(item['requirements'])}\n"
        f"   - acceptance: {'; '.join(item['acceptance'])}"
        for index, item in enumerate(created, 1)
    )
    write_text(
        path,
        f"""# Plan: {goal}

- Plan: `{plan_id}`
- Project: `{project['id']}`
- Created: {_now()}
- Tasks: {len(created)}

## Notes

{notes or '—'}

## Backlog

{task_lines}
""",
    )
    tasks.commit_task(layout, ids[-1], f"Plan {plan_id}")
    ledger.append_event(
        str(project["id"]),
        "plan",
        status="completed",
        idempotency_key=f"{project['id']}:plan:{plan_id}",
        artifact_refs=[str(path.relative_to(layout.root))],
        payload={
            "goal": goal,
            "tasks": ids,
            "plan": plan_id,
        },
        generation=ledger.current_generation(str(project["id"])),
    )
    log(f"[plan] {project['id']}: {len(created)} task(s) queued")
    return PlanResult(
        plan_id=plan_id,
        goal=goal,
        notes=notes,
        tasks=created,
        artifact=str(path.relative_to(layout.root)),
    )
