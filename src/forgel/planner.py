"""Turn a milestone goal into an ordered backlog of task intents.

The planner is one model call with clean context: the project brief, the
repository graph, the environment contract, recent tasks and the goal. It
returns a small, ordered list of task intents: a title, the outcome, the
repository and dependencies. A separate requirements writer expands each
intent into a formal specification, and a plan review judges the whole set
against the original problem before any task is queued.

The plan is a project artifact: `docs/program/plans/<plan_id>.md`; each task
specification is `docs/program/specs/<task_id>.md`. `--dry-run` previews the
specifications without creating tasks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import dependencies, language, peak, specs, tasks
from .adopt import AdoptError, add_repository, create_repository
from .agent import build_context
from .artifacts import write_text
from .config import Settings
from .environment import load_environment
from .integration import integration_problem, integration_warning
from .layout import ProjectLayout
from .ledger import Ledger
from .model_output import json_objects
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    build_model_client,
    project_model_name,
)
from .program_manifest import entries as manifest_entries
from .program_manifest import slugify_repo_id
from .providers import ProviderError
from .providers.github_api import GithubAPIError
from .providers.github_auth import GithubAuthError
from .release_train import new_release_id, plan_release
from .repo_tools import (
    MAX_READ_CHARS,
    RESEARCH_ACTIONS,
    RepoActionError,
    execute_repo_action,
)

MAX_TASKS = 20
DEFAULT_TASKS = 8
MAX_RESEARCH_STEPS = 50


class PlanningError(RuntimeError):
    """The goal cannot be turned into a usable plan."""


@dataclass(frozen=True)
class PlanResult:
    plan_id: str
    goal: str
    notes: str
    tasks: list[dict[str, Any]] = field(default_factory=list)
    repositories: list[dict[str, Any]] = field(default_factory=list)
    artifact: str = ""
    release_id: str = ""
    dry_run: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def plan_tasks(
    layout: ProjectLayout, plan_id: str = ""
) -> tuple[str, list[dict[str, Any]]]:
    """Tasks of a plan, and the plan id (the latest when not given)."""

    items = [
        task for task in tasks.list_tasks(layout) if task.get("plan_id")
    ]
    if not plan_id and items:
        plan_id = max(str(task["plan_id"]) for task in items)
    return plan_id, [
        task for task in items if str(task.get("plan_id")) == plan_id
    ]


def plan_status(
    layout: ProjectLayout, plan_id: str = ""
) -> dict[str, Any]:
    """Derive the milestone state from its tasks.

    done     all tasks are done or cancelled;
    review   nothing runnable, at least one task awaits acceptance;
    stalled  a failure/blocked task and nothing runnable;
    running  there is still runnable work (or acceptance is pending).
    """

    plan_id, items = plan_tasks(layout, plan_id)
    if not items:
        return {
            "plan_id": "",
            "goal": "",
            "status": "none",
            "counts": {},
            "tasks": [],
        }
    statuses = {
        str(task["id"]): str(task.get("status")) for task in items
    }
    counts: dict[str, int] = {}
    for status in statuses.values():
        counts[status] = counts.get(status, 0) + 1
    runnable = any(
        task.get("status") == "pending"
        and all(
            statuses.get(dep) == "done"
            for dep in (task.get("depends_on") or [])
        )
        for task in items
    )
    failed = any(status == "failed" for status in statuses.values())
    blocked = any(status == "blocked" for status in statuses.values())
    reviewing = any(
        status == "review" for status in statuses.values()
    )
    if all(
        status in {"done", "cancelled"} for status in statuses.values()
    ):
        state = "done"
    elif failed and not runnable:
        state = "stalled"
    elif blocked and not runnable and not reviewing:
        state = "stalled"
    elif reviewing and not runnable:
        state = "review"
    else:
        state = "running"
    goal = next(
        (str(task.get("plan_goal") or "") for task in items), ""
    )
    return {
        "plan_id": plan_id,
        "goal": goal,
        "status": state,
        "counts": counts,
        "tasks": [
            {
                "id": task["id"],
                "title": task.get("title", ""),
                "status": task.get("status", ""),
                "blocked_by": (task.get("result") or {}).get(
                    "blocked_by", ""
                ),
            }
            for task in items
        ],
    }


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

You may inspect the repositories yourself before planning. Reply with exactly
one JSON action per turn:
{{"action": "list_files", "path": ".", "repo_id": "main"}}
{{"action": "read_file", "path": "PLAN.md", "repo_id": "main"}}
Paths are relative to the repository and may not leave it. Read the project's
own documents and code instead of guessing; do not ask a human. The context
below already includes the project documents and a file tree; read only what
is missing and stop reading once you can plan. When you have enough context,
reply with the plan object below. Never mix an action and the plan in one
reply. Return JSON only; do not use tool-call markup, XML or
provider-specific function calls.

Return exactly one JSON object:
{{
  "notes": "assumptions and ordering rationale in a few sentences",
  "repositories": [
    {{
      "id": "api",
      "role": "backend",
      "path": "optional local path",
      "create": true,
      "private": true,
      "org": "optional GitHub owner",
      "depends_on": ["existing-or-earlier-repo-id"]
    }}
  ],
  "tasks": [
    {{
      "title": "short imperative title",
      "summary": "the outcome this task delivers and why it is needed",
      "repo_id": "one of the project repositories, or empty for the sole one",
      "depends_on": [0]
    }}
  ]
}}

Rules:
- Produce 1 to {max_tasks} tasks, in execution order.
- If the goal needs repositories that are not in the project graph, list them
  in "repositories" and use their ids in tasks. Do not silently narrow the
  goal to the existing repositories.
- create=true creates a new GitHub repository (path optional); create=false
  adds an existing local git repository at path. Repositories are created or
  added before the tasks run; depends_on may reference an existing repository
  or an earlier planned one.
- depends_on uses 0-based indexes of earlier tasks only; no cycles.
- One repository per task; do not mix repositories in one task.
- A separate requirements writer turns each task intent into a formal
  specification. Your job is the decomposition: a clear outcome, the right
  repository and the right order. Do not write the detailed specification
  here; put uncertainty and ordering rationale in "notes".
- Every task must be a single repository change that a coding agent can
  implement, test and commit on its own.
- Do not create tasks for production deploys, payments, secrets, data
  destruction or legal decisions.
- If the project has interacting repositories (a dependency edge), a
  frontend/acceptance or mobile repository, or sibling mounts, the environment
  contract must declare e2e. A mobile repository needs a simulator/emulator;
  a frontend repository needs a real browser. A missing simulator defers the
  mobile e2e but must not stop planning. A database or cache covered by
  the unit-test framework does not by itself require a program e2e; a browser
  or an external tool without a standard test harness belongs in the
  specification's real-interface check. The plan gate rejects a missing
  program e2e for the hard cases; never plan around it or invent a substitute.
- Follow the project and repository instructions in the context. Repository
  rules are more specific and take precedence on conflict. Write task titles,
  summaries and notes in the artifact language they require.
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


def _parse_repositories(
    data: Mapping[str, Any], known: Sequence[str]
) -> list[dict[str, Any]]:
    raw = data.get("repositories", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PlanningError("repositories must be a list")
    seen = set(known)
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise PlanningError(
                f"repository {index} must be an object"
            )
        repo_id = slugify_repo_id(str(item.get("id", "")))
        if not repo_id:
            raise PlanningError(f"repository {index} has no id")
        if repo_id in seen:
            raise PlanningError(
                f"repository {index} duplicates or already exists: {repo_id}"
            )
        create = item.get("create", True)
        if not isinstance(create, bool):
            raise PlanningError(
                f"repository {repo_id}: create must be true or false"
            )
        path = str(item.get("path") or "").strip()
        if not create and not path:
            raise PlanningError(
                f"repository {repo_id}: an existing repository needs a path"
            )
        depends = item.get("depends_on", [])
        if not isinstance(depends, list) or not all(
            isinstance(value, str) and value.strip() for value in depends
        ):
            raise PlanningError(
                f"repository {repo_id}: depends_on must be a list of ids"
            )
        dependencies = list(dict.fromkeys(value.strip() for value in depends))
        for dependency in dependencies:
            if dependency not in seen:
                raise PlanningError(
                    f"repository {repo_id}: unknown dependency "
                    f"{dependency!r}; define it earlier or use an existing id"
                )
        specs.append(
            {
                "id": repo_id,
                "role": str(item.get("role") or "application").strip(),
                "create": create,
                "private": bool(item.get("private", True)),
                "org": str(item.get("org") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "path": path,
                "depends_on": dependencies,
            }
        )
        seen.add(repo_id)
    return specs


def _parse_plan(
    raw: str,
    known_repos: Sequence[str],
    default_repo: str,
    max_tasks: int,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
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
    repositories = _parse_repositories(data, known_repos)
    allowed_repos = list(known_repos) + [
        str(item["id"]) for item in repositories
    ]
    if len(allowed_repos) != 1:
        default_repo = ""
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
        summary = str(item.get("summary", "")).strip()
        if not title:
            raise PlanningError(f"task {index} has no title")
        if title.lower() in titles:
            raise PlanningError(f"duplicate task title: {title!r}")
        titles.add(title.lower())
        repo_id = str(item.get("repo_id", "")).strip() or default_repo
        if allowed_repos and repo_id not in allowed_repos:
            raise PlanningError(
                f"task {index} targets unknown repository {repo_id!r}"
            )
        depends_on = item.get("depends_on") or []
        if not isinstance(depends_on, list) or any(
            not isinstance(value, int) or value < 0 or value >= index
            for value in depends_on
        ):
            raise PlanningError(
                f"task {index}: depends_on must use earlier task indexes"
            )
        items.append(
            {
                "title": title,
                "summary": summary,
                "repo_id": repo_id,
                "depends_on": [int(value) for value in depends_on],
            }
        )
    return notes, items, repositories


def _cap(text: str, limit: int = MAX_READ_CHARS) -> str:
    if len(text) <= limit:
        return text
    return (
        text[:limit]
        + "\n... [truncated; use read_file with offset to read the rest]"
    )


def _apply_repositories(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    repositories: Sequence[Mapping[str, Any]],
) -> None:
    """Create or add repositories before the plan's coding tasks run."""

    for spec in repositories:
        repo_id = str(spec["id"])
        try:
            if bool(spec.get("create", True)):
                create_repository(
                    settings,
                    ledger,
                    dict(project),
                    repo_id,
                    org=str(spec.get("org") or ""),
                    private=bool(spec.get("private", True)),
                    depends_on=list(spec.get("depends_on") or []),
                    role=str(spec.get("role") or "application"),
                    description=str(spec.get("description") or ""),
                    path=str(spec.get("path") or ""),
                )
            else:
                add_repository(
                    settings,
                    ledger,
                    dict(project),
                    str(spec.get("path") or ""),
                    repo_id=repo_id,
                    depends_on=list(spec.get("depends_on") or []),
                    role=str(spec.get("role") or "application"),
                )
        except (
            AdoptError,
            ProviderError,
            GithubAPIError,
            GithubAuthError,
            OSError,
            ValueError,
        ) as exc:
            raise PlanningError(
                f"repository setup failed for {repo_id}: {exc}"
            ) from exc


def _spec_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except specs.SpecError as exc:
        raise PlanningError(str(exc)) from exc


def _task_error(
    item: Mapping[str, Any], index: int, exc: PlanningError
) -> PlanningError:
    detail = str(exc)
    title = str(item.get("title") or index)
    if f"task: {title}" not in detail and f"task {title}" not in detail:
        detail = f"task {title}: {detail}"
    return PlanningError(detail)


def _dependency_call(
    layout: ProjectLayout,
    intent: Mapping[str, Any],
    spec: dict[str, Any],
    client: ModelClient,
    log: Callable[[str], None],
) -> dict[str, Any]:
    if not spec.get("external_dependencies"):
        return spec
    try:
        spec["external_dependencies"] = dependencies.investigate(
            layout, intent, spec, client, log
        )
    except dependencies.DependencyError as exc:
        raise PlanningError(str(exc)) from exc
    return spec


def plan_project(
    settings: Settings,
    ledger: Ledger,
    project: Mapping[str, Any],
    goal: str,
    max_tasks: int = DEFAULT_TASKS,
    dry_run: bool = False,
    client: ModelClient | None = None,
    log: Callable[[str], None] = print,
    release_id: str = "",
    release_class: str = "minor",
) -> PlanResult:
    """Ask the model for an ordered backlog and queue it as tasks."""

    goal = goal.strip()
    if not goal:
        raise PlanningError("a milestone goal is required")
    release_class = str(release_class or "minor").strip().lower()
    if release_class not in {"patch", "minor", "major"}:
        release_class = "minor"
    release_id = release_id.strip() or new_release_id(goal)
    max_tasks = max(1, min(int(max_tasks), MAX_TASKS))
    layout = ProjectLayout.detect(str(project["workspace"]))
    try:
        environment = load_environment(layout)
    except Exception as exc:  # noqa: BLE001 - the contract is project data
        raise PlanningError(f"environment contract: {exc}") from exc
    problem = integration_problem(layout, environment)
    if problem:
        raise PlanningError(problem)
    deferred = integration_warning(layout, environment)
    if deferred:
        log(f"[plan] {project['id']}: {deferred}")
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
    raw = ""
    parsed: (
        tuple[str, list[dict[str, Any]], list[dict[str, Any]]] | None
    ) = None
    plan_retries = 0
    budget_notice = False
    research_steps = 0
    for _ in range(MAX_RESEARCH_STEPS + 4):
        try:
            raw = model_client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError as exc:
            raise PlanningError(
                f"planner model call failed: {exc}"
            ) from exc
        objects = json_objects(raw)
        actions = [
            item
            for item in objects
            if str(item.get("action", "")) in RESEARCH_ACTIONS
        ]
        finals = [
            item
            for item in objects
            if str(item.get("action", "")) not in RESEARCH_ACTIONS
        ]
        observations: list[str] = []
        for action_data in actions:
            if research_steps >= MAX_RESEARCH_STEPS:
                break
            try:
                observation = execute_repo_action(
                    layout, repos, action_data
                )
            except RepoActionError as exc:
                observation = f"error: {exc}"
            observations.append(observation)
            research_steps += 1
        if observations:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observations:\n"
                    + "\n\n".join(_cap(item) for item in observations)
                    + "\n\nReply with another action or the final plan "
                    "JSON object.",
                )
            )
        if finals:
            final = finals[-1]
            try:
                parsed = _parse_plan(
                    json.dumps(final), known, default_repo, max_tasks
                )
                break
            except PlanningError as exc:
                if plan_retries < 2:
                    if not observations:
                        messages.append(
                            ModelMessage("assistant", raw.strip())
                        )
                    messages.append(
                        ModelMessage(
                            "user",
                            f"The plan is invalid: {exc}. Return a "
                            "corrected, complete JSON plan object with notes "
                            "and tasks. Existing repositories are context: do "
                            "not list one in repositories; use its id in a "
                            "task. Do not use tool-call markup, XML, "
                            "provider-specific function calls or prose.",
                        )
                    )
                    plan_retries += 1
                    continue
                raise PlanningError(str(exc)) from exc
        if not actions:
            if plan_retries < 2:
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        "Return exactly one JSON plan object with notes and "
                        "tasks. Do not use tool-call markup, XML, "
                        "provider-specific function calls or prose.",
                    )
                )
                plan_retries += 1
                continue
            raise PlanningError("the planner did not return a plan")
        if research_steps >= MAX_RESEARCH_STEPS and not observations:
            if budget_notice:
                raise PlanningError(
                    "the planner exceeded the research step limit"
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Research budget exhausted. Return the final plan JSON "
                    "object now; do not read or list more files.",
                )
            )
            budget_notice = True
            continue
    if parsed is None:
        raise PlanningError("the planner did not return a plan")
    notes, items, repositories = parsed
    problem = integration_problem(layout, environment, repositories)
    if problem:
        raise PlanningError(problem)
    deferred = integration_warning(layout, environment, repositories)
    if deferred:
        notes = notes + "\n\n## Integration deferred\n\n" + deferred
        log(f"[plan] {project['id']}: {deferred}")
    plan_id = _plan_id(goal)
    task_language = language.detect(goal)
    used: set[str] = set()
    ids: list[str] = []
    for item in items:
        candidate = tasks.new_task_id(str(item["title"]))
        suffix = 2
        while candidate in used or tasks.task_path(
            layout, candidate
        ).exists():
            candidate = (
                f"{tasks.new_task_id(str(item['title']))}-{suffix}"
            )
            suffix += 1
        used.add(candidate)
        ids.append(candidate)

    if dry_run:
        preview: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            try:
                spec = _spec_call(specs.write_task_spec,
                    settings, layout, goal, notes, item, model_client, log
                )
            except PlanningError as exc:
                raise _task_error(item, index + 1, exc) from exc
            spec = _dependency_call(
                layout, item, spec, model_client, log
            )
            preview.append(dict(spec))
        review = _spec_call(specs.review_plan, 
            layout, goal, notes, preview, model_client, log
        )
        notes = notes + "\n\n## Plan review\n\n" + review.to_markdown()
        return PlanResult(
            plan_id=plan_id,
            goal=goal,
            notes=notes,
            tasks=preview,
            repositories=repositories,
            release_id=release_id,
            dry_run=True,
        )

    _apply_repositories(settings, ledger, project, repositories)
    task_specs: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        log(f"[spec] task {index + 1}/{len(items)}: writing")
        try:
            spec = _spec_call(specs.write_task_spec,
                settings, layout, goal, notes, item, model_client, log
            )
        except PlanningError as exc:
            raise PlanningError(
                f"task {item.get('title') or index + 1}: {exc}"
            ) from exc
        task_specs.append(
            _dependency_call(
                layout, item, spec, model_client, log
            )
        )
    review = _spec_call(specs.review_plan, 
        layout, goal, notes, task_specs, model_client, log
    )
    if not review.sufficient:
        log("[plan] review found gaps; revising the specifications")
        for finding in review.findings:
            position = int(finding.get("task", -1))
            if 0 <= position < len(items):
                try:
                    revised = _spec_call(specs.write_task_spec,
                        settings,
                        layout,
                        goal,
                        notes,
                        items[position],
                        model_client,
                        log,
                        review_issue=str(finding.get("issue") or ""),
                    )
                except PlanningError as exc:
                    raise _task_error(
                        items[position], position + 1, exc
                    ) from exc
                task_specs[position] = _dependency_call(
                    layout,
                    items[position],
                    revised,
                    model_client,
                    log,
                )
        review = _spec_call(specs.review_plan, 
            layout, goal, notes, task_specs, model_client, log
        )
    if not review.sufficient:
        details = "; ".join(
            f"task {item.get('task')}: {item.get('issue')}"
            for item in review.findings
        ) or "no findings"
        raise PlanningError(
            "the plan does not solve the stated problem: " + details
        )
    notes = notes + "\n\n## Plan review\n\n" + review.to_markdown()

    created: list[dict[str, Any]] = []
    task_records: list[dict[str, Any]] = []
    for index, (item, spec) in enumerate(zip(items, task_specs)):
        dependencies = [ids[position] for position in item["depends_on"]]
        spec_ref = specs.spec_path(ids[index])
        task = tasks.create_task(
            layout,
            str(item["title"]),
            [],
            [],
            repo_id=str(item["repo_id"]),
            test_command=list(spec["test_command"]),
            plan_id=plan_id,
            plan_goal=goal,
            order=index + 1,
            depends_on=dependencies,
            checks=list(spec["checks"]),
            language=task_language,
            spec=spec_ref,
            external_dependencies=list(
                spec.get("external_dependencies") or []
            ),
            task_id=ids[index],
            release_id=release_id,
            release_class=release_class,
            summary=str(item.get("summary") or ""),
        )
        write_text(
            layout.artifact(spec_ref),
            specs.render_spec(
                spec,
                ids[index],
                plan_id,
                str(item["repo_id"]),
                dependencies,
            ),
        )
        created.append(
            {
                **item,
                **spec,
                "task_id": ids[index],
                "spec": spec_ref,
                "depends_on": dependencies,
            }
        )
        task_records.append(task)
    path = layout.artifact(f"docs/program/plans/{plan_id}.md")
    task_lines = "\n".join(
        f"{index}. `{item['task_id']}` {item['title']}\n"
        f"   - repo: {item['repo_id'] or '(sole)'}\n"
        f"   - depends on: {', '.join(item['depends_on']) or 'none'}\n"
        f"   - spec: `{item['spec']}`\n"
        f"   - summary: {item.get('summary') or '—'}\n"
        f"   - checks: "
        + (
            "; ".join(
                check["criterion"]
                + (
                    ""
                    if check["verification"] == "review"
                    else f" ({json.dumps(check['command'])})"
                )
                for check in item["checks"]
            )
        )
        for index, item in enumerate(created, 1)
    )
    repo_lines = (
        "\n".join(
            f"- `{item['id']}` — "
            f"{'create' if item.get('create') else 'add'}, "
            f"{item.get('role', 'application')}, "
            f"depends on: {', '.join(item.get('depends_on') or []) or 'none'}"
            for item in repositories
        )
        or "- none"
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

## Repositories

{repo_lines}

## Backlog

{task_lines}
""",
    )
    tasks.commit_task(layout, ids[-1], f"Plan {plan_id}")
    plan_release(
        layout,
        project,
        release_id,
        title=goal,
        request=goal,
        release_class=release_class,
        task_items=task_records,
        plan_id=plan_id,
        ledger=ledger,
    )
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
        repositories=repositories,
        artifact=str(path.relative_to(layout.root)),
        release_id=release_id,
    )
