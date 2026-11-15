"""Chat command router and user-facing UX.

The router is transport-free: it turns text from one chat into core calls and a
reply. It never touches the network, so it is fully testable. Every command is
scoped to one project, chosen explicitly or from the chat's session; the agent
receives only that project's context.
"""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from . import config_store, daemon_config, peak
from .adopt import (
    AdoptError,
    add_repository,
    adopt_repository,
    create_repository,
    extract_control,
    publish_repository,
    set_dependencies,
)
from .agent import ProjectAgent, append_history, build_context
from .approvals import ApprovalError, is_approved, latest_approval, record_approval
from .artifacts import read_json
from .config import Settings
from .control import is_paused, set_paused
from .daemon import project_is_done, project_state
from .git_ops import GitOperationError
from .github_flow import (
    GithubFlowError,
    merge_pr,
    publish,
    status_text,
)
from .layout import ProjectLayout
from .ledger import Ledger
from .artifacts import write_text
from .planner import PlanningError, plan_project, plan_status
from .project_config import ConfigError, render_project_config
from .task_review import accept_task, reject_task
from .program_manifest import entries as manifest_entries
from .program_manifest import repo_location
from .projects import ProjectError, create_project, derive_name, resolve_project
from .proposals import summarize_proposals
from .providers import ProviderError
from .providers.github_api import GithubAPIError
from .providers.github_auth import GithubAuthError
from .secrets import (
    SECRETS_FILENAME,
    SECRET_KEYS,
    SecretError,
    delete_secret,
    secret_status,
    set_secret,
)
from .sync import (
    SyncError,
    reconcile_project,
    reconciliation_status_path,
    sync_project,
)
from .tasks import (
    cancel_task,
    commit_task,
    get_task,
    latest_task,
    list_tasks,
    retry_task,
)

DECISIONS = {"accept", "fix", "rollback", "ignore"}
SCOPES = {"staging", "production"}

SECRET_PATTERNS = (
    re.compile(r"(^|[^A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(^|[^A-Za-z0-9])ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"(^|[^A-Za-z0-9])github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"(^|[^A-Za-z0-9])AKIA[0-9A-Z]{16}([^A-Za-z0-9]|$)"),
)

HELP = """Forgel

Talk in plain language. I decide what to do: answer, queue a code change,
plan a milestone, show the state, accept or send work back, retry, pause, or
adopt a repository. You do not need to remember commands.

Examples
  adopt this repository
  plan the milestone: bring the project to M1
  what is happening?
  accept the latest task
  send it back: the header is wrong
  retry the failed task
  work in peak hours / only off-peak
  pause / resume

Entry points and sensitive operations stay explicit
/adopt <url> [| brief]   adopt a repository and select it
/new <name> | <brief>    create a template project
/secret ...              secret names, set, delete
/config [set ...]        effective settings
/help
/quit                    exit the console

Project ids can be shortened to any unique prefix. Secrets sent to a bot pass
through Telegram, which has no end-to-end encryption for bots; prefer
environment variables or `forgel secret set` over SSH in production."""


@dataclass(frozen=True)
class Reply:
    text: str
    reply_markup: dict[str, Any] | None = None
    callback_text: str = ""
    delete_source: bool = False


def looks_like_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


class CommandRouter:
    """Turn chat text into core calls. No network, no threads."""

    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        daemon_enabled: bool = True,
        agent: ProjectAgent | None = None,
        github_api: Any | None = None,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.daemon_enabled = daemon_enabled
        self.agent = agent
        self.github_api = github_api
        self._production_tokens: dict[str, tuple[str, float]] = {}
        self._token_ttl = 900.0

    # ------------------------------------------------------------- dispatch

    def handle(self, chat_id: int, text: str, actor: str) -> Reply:
        text = text.strip()
        if not text:
            return Reply("Send a command or a message. /help")
        if not text.startswith("/"):
            return self._message(chat_id, text, actor)
        command_token, _, rest = text.partition(" ")
        command = command_token.split("@", 1)[0].lower()
        rest = rest.strip()

        handlers: dict[str, Callable[[int, str, str], Reply]] = {
            "/start": lambda _chat, _rest, _actor: Reply(HELP),
            "/help": lambda _chat, _rest, _actor: Reply(HELP),
            "/new": self._new,
            "/adopt": self._adopt,
            "/repo": self._repo,
            "/control": self._control,
            "/github": self._github,
            "/plan": self._plan,
            "/tasks": self._tasks,
            "/task": self._task,
            "/projects": self._projects,
            "/list": self._projects,
            "/use": self._use,
            "/status": self._status,
            "/run": self._run,
            "/sync": self._sync,
            "/reconcile": self._reconcile,
            "/proposals": self._proposals,
            "/approve": self._approve,
            "/reject": self._reject,
            "/config": self._config,
            "/peak": self._peak,
            "/secret": self._secret,
            "/pause": self._pause,
            "/resume": self._resume,
        }
        handler = handlers.get(command)
        if handler is None:
            return Reply(f"Unknown command {command}. /help lists them.")
        return handler(chat_id, rest, actor)

    def handle_callback(self, chat_id: int, data: str, actor: str) -> Reply:
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "ap":
            return Reply("Unknown action.", callback_text="Unknown action")
        _, token, action = parts
        entry = self._production_tokens.pop(token, None)
        if entry is None or time.time() - entry[1] > self._token_ttl:
            return Reply(
                "This approval request expired. Run /approve again.",
                callback_text="Expired",
            )
        project_id = entry[0]
        if action == "no":
            return Reply(
                f"Production approval cancelled for {project_id}.",
                callback_text="Cancelled",
            )
        if action != "ok":
            return Reply("Unknown action.", callback_text="Unknown action")
        try:
            record = record_approval(
                self.ledger,
                project_id,
                scope="production",
                actor=actor,
                decision="approved",
                compliance_ack=True,
                notes="confirmed in Telegram",
            )
        except ApprovalError as exc:
            return Reply(f"error: {exc}", callback_text="Not approved")
        return Reply(
            self._approval_text(record, production=True),
            callback_text="Approved",
        )

    # ------------------------------------------------------------- projects

    def _new(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return Reply(
                "Usage: /new <name> | <brief>\n"
                "or: /new <brief> to derive the name."
            )
        if "|" in rest:
            name, brief = rest.split("|", 1)
        else:
            name, brief = derive_name(rest), rest
        try:
            project_id = create_project(
                self.settings, self.ledger, name, brief
            )
        except ProjectError as exc:
            return Reply(f"error: {exc}")
        self.ledger.set_session(chat_id, project_id)
        return Reply(
            f"Project {project_id} created and selected.\n"
            "The daemon will run it and report back."
        )

    def _adopt(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return Reply(
                "Usage: /adopt <repository-url> [| brief]\n"
                "Supports GitHub URLs, SSH remotes, owner/repo and local paths."
            )
        url, _, brief = rest.partition("|")
        try:
            result = adopt_repository(
                self.settings, self.ledger, url.strip(), brief.strip()
            )
        except (AdoptError, ProviderError) as exc:
            return Reply(
                f"error: {exc}" + self._github_hint(url, str(exc))
            )
        self.ledger.set_session(chat_id, result.project_id)
        project = self.ledger.get_project(result.project_id)
        layout = (
            ProjectLayout.detect(project["workspace"])
            if project is not None
            else None
        )
        if layout is not None and layout.is_linked:
            control = layout.control.relative_to(layout.root).as_posix()
            lines = [
                f"Adopted the folder in place as {result.project_id} and "
                "selected it.",
                f"Repository: {result.repo_id} ({result.provider}).",
                "Mode: brownfield — the source folder is the repository; "
                "there is no second copy.",
                f"Control artifacts live in {control}/.",
            ]
        else:
            lines = [
                f"Adopted {result.url} as {result.project_id} and selected "
                "it.",
                f"Repository: {result.repo_id} ({result.provider}).",
                "Mode: brownfield — Forgel will not regenerate this "
                "repository.",
                "Config initialized in program/forgel.toml and program.yaml.",
            ]
        if result.provider == "local":
            lines.append(
                "No origin remote was found. The folder stays local; "
                "configure GitHub and ask me to publish it, or add a remote "
                "yourself."
            )
        if result.provider == "github":
            if result.auth.configured:
                lines.append("GitHub: " + result.auth.detail + ".")
            else:
                lines.append(
                    "GitHub: " + result.auth.detail + ". For private "
                    "repositories and later push/PR set FORGEL_GITHUB_TOKEN "
                    "on the host or /secret set github.token <token>; a "
                    "fine-grained token needs Contents read/write."
                )
        lines.append(
            "If a related repository belongs here, tell me to add it and "
            "which repository it depends on."
        )
        lines.append(
            "Link repositories only when their code depends on each other "
            "(for example a frontend consumes a backend contract). "
            "Independent repositories can be linked, but Forgel will simply "
            "maintain them separately."
        )
        return Reply("\n".join(lines))

    def _repo(self, chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=1)
        action = tokens[0].lower() if tokens else "list"
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        if action == "list":
            layout = ProjectLayout.detect(project["workspace"])
            repos = manifest_entries(layout)
            if not repos:
                return Reply("This project has no repositories recorded.")
            lines = [f"Repositories: {len(repos)}"]
            for entry in repos:
                depends = ", ".join(entry["depends_on"]) or "none"
                lines.append(
                    f"{entry['id']}  {entry['role']}  {entry['provider']}\n"
                    f"  url: {repo_location(layout, entry) or '—'}\n"
                    f"  depends on: {depends}"
                )
            return Reply("\n".join(lines))
        if action == "link":
            if len(tokens) < 2:
                return Reply("Usage: /repo link <id> depends_on=<id,id>")
            parts = tokens[1].split()
            if not parts:
                return Reply("Usage: /repo link <id> depends_on=<id,id>")
            repo_id = parts[0]
            depends_on: list[str] = []
            found = False
            for token in parts[1:]:
                if token.startswith("depends_on="):
                    found = True
                    depends_on = [
                        item
                        for item in token.split("=", 1)[1].split(",")
                        if item
                    ]
            if not found:
                return Reply("Usage: /repo link <id> depends_on=<id,id>")
            try:
                entry = set_dependencies(
                    self.settings,
                    self.ledger,
                    project,
                    repo_id,
                    depends_on,
                )
            except (AdoptError, ValueError) as exc:
                return Reply(f"error: {exc}")
            edges = ", ".join(entry["depends_on"]) or "none"
            return Reply(
                f"Updated dependencies for {entry['id']}: {edges}."
            )
        if action in {"create", "publish"}:
            if len(tokens) < 2 and action == "create":
                return Reply(
                    "Usage: /repo create <id> [org=<name>] [public] "
                    "[depends_on=<id,id>] [| description]"
                )
            payload, _, description = (
                tokens[1] if len(tokens) > 1 else ""
            ).partition("|")
            parts = payload.split()
            repo_id = ""
            options = parts
            is_option = (
                lambda token: token.startswith(
                    ("org=", "depends_on=", "path=")
                )
                or token == "public"
            )
            if action == "create":
                repo_id = parts[0]
                options = parts[1:]
            elif parts and not is_option(parts[0]):
                repo_id = parts[0]
                options = parts[1:]
            org = ""
            path = ""
            public = False
            depends_on: list[str] = []
            for token in options:
                if token.startswith("org="):
                    org = token.split("=", 1)[1]
                elif token.startswith("path="):
                    path = token.split("=", 1)[1]
                elif token == "public":
                    public = True
                elif token.startswith("depends_on="):
                    depends_on = [
                        item
                        for item in token.split("=", 1)[1].split(",")
                        if item
                    ]
                else:
                    return Reply(f"unexpected argument: {token}")
            description = description.strip()
            try:
                if action == "create":
                    created = create_repository(
                        self.settings,
                        self.ledger,
                        project,
                        repo_id,
                        org=org,
                        private=not public,
                        depends_on=depends_on,
                        description=description,
                        path=path,
                    )
                    return Reply(
                        f"Created {created.entry['id']} at {created.url} "
                        f"and added it to {project['id']}."
                    )
                if repo_id:
                    targets = [repo_id]
                else:
                    layout = ProjectLayout.detect(project["workspace"])
                    targets = [
                        entry["id"]
                        for entry in manifest_entries(layout)
                        if "github.com" not in (entry.get("url") or "")
                    ]
                if not targets:
                    return Reply("Nothing to publish.")
                lines: list[str] = []
                for target in targets:
                    published = publish_repository(
                        self.settings,
                        self.ledger,
                        project,
                        target,
                        org=org,
                        private=not public,
                        description=description,
                    )
                    lines.append(
                        f"{target}: {published.url}"
                    )
                return Reply(
                    "Published repositories:\n" + "\n".join(lines)
                )
            except (
                AdoptError,
                ProviderError,
                GithubAuthError,
                GithubAPIError,
            ) as exc:
                hint = self._github_hint("github.com", str(exc))
                return Reply(f"error: {exc}{hint}")
        if action != "add":
            return Reply(
                "Usage: /repo list, /repo add <url> [id] "
                "[depends_on=<id,id>], /repo create <id>, "
                "/repo publish [id] or /repo link <id> "
                "depends_on=<id,id>"
            )
        if len(tokens) < 2:
            return Reply(
                "Usage: /repo add <url> [id] [depends_on=<id,id>]"
            )
        parts = tokens[1].split()
        if not parts:
            return Reply(
                "Usage: /repo add <url> [id] [depends_on=<id,id>]"
            )
        url = parts[0]
        repo_id = ""
        depends_on: list[str] = []
        for token in parts[1:]:
            if token.startswith("depends_on="):
                depends_on = [
                    item
                    for item in token.split("=", 1)[1].split(",")
                    if item
                ]
            elif not repo_id:
                repo_id = token
            else:
                return Reply(f"unexpected argument: {token}")
        try:
            result = add_repository(
                self.settings,
                self.ledger,
                project,
                url,
                repo_id=repo_id,
                depends_on=depends_on,
            )
        except (AdoptError, ProviderError) as exc:
            return Reply(
                f"error: {exc}" + self._github_hint(url, str(exc))
            )
        entry = result.entry
        lines = [
            f"Added repository {entry['id']} to {project['id']}.",
            f"Provider: {entry['provider']}; "
            f"url: {entry.get('path') or entry['url'] or '—'}.",
        ]
        if entry["depends_on"]:
            lines.append(
                "Dependency edges: "
                + ", ".join(entry["depends_on"])
                + "."
            )
        else:
            lines.append(
                "No dependency edges recorded: this repository is maintained "
                "separately inside the project."
            )
        return Reply("\n".join(lines))

    def _tasks(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        entries = list_tasks(layout)
        if not entries:
            return Reply(
                "No tasks. A change request sent as a plain message queues one."
            )
        lines = [f"Tasks: {len(entries)}"]
        for task in entries:
            summary = str(task.get("result", {}).get("summary", ""))
            lines.append(
                f"{task['id']}  {task['status']}  {task['title']}"
            )
            if summary:
                lines.append(f"  {summary}")
        return Reply("\n".join(lines))

    def _task(self, chat_id: int, rest: str, _actor: str) -> Reply:
        usage = (
            "Usage: /task cancel|retry <task-id>, "
            "/task accept <task-id> [note] or "
            "/task reject <task-id> [note]"
        )
        tokens = rest.split(maxsplit=2)
        action = tokens[0].lower() if tokens else ""
        if action not in {"cancel", "retry", "accept", "reject"}:
            return Reply(usage)
        if len(tokens) < 2:
            return Reply(usage)
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        task_id = tokens[1]
        notes = tokens[2].strip() if len(tokens) > 2 else ""
        if action in {"cancel", "retry"}:
            try:
                task = (
                    cancel_task(layout, task_id)
                    if action == "cancel"
                    else retry_task(layout, task_id)
                )
            except ValueError as exc:
                return Reply(f"error: {exc}")
            commit_task(
                layout,
                task["id"],
                f"{action.capitalize()} task {task['id']}",
            )
            return Reply(
                f"{'Cancelled' if action == 'cancel' else 'Requeued'} "
                f"task {task['id']}."
            )
        task = get_task(layout, task_id)
        if task is None:
            return Reply(f"error: unknown task {task_id!r}")
        if action == "accept":
            updated = accept_task(
                self.settings,
                self.ledger,
                project,
                task,
                actor="telegram",
                notes=notes,
            )
        else:
            updated = reject_task(
                self.settings,
                self.ledger,
                project,
                task,
                actor="telegram",
                notes=notes,
            )
        commit_task(
            layout,
            updated["id"],
            f"{action.capitalize()} task {updated['id']}",
        )
        return Reply(
            f"{action.capitalize()}ed task {updated['id']} "
            f"({updated['status']})."
        )

    def _control(self, chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=1)
        action = tokens[0].lower() if tokens else ""
        if action != "extract":
            return Reply("Usage: /control extract [path]")
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        path = tokens[1].strip() if len(tokens) > 1 else ""
        try:
            result = extract_control(
                self.settings, self.ledger, project, path
            )
        except AdoptError as exc:
            return Reply(f"error: {exc}")
        return Reply(
            f"Project state moved to {result.control}. "
            "The product repository no longer tracks it."
        )

    def _github(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        tokens = rest.split(maxsplit=1)
        action = tokens[0].lower() if tokens else "status"
        if action == "status":
            return Reply(status_text(self.settings, project))
        if action not in {"publish", "merge"}:
            return Reply(
                "Usage: /github, /github publish [repo] <title>, "
                "/github merge [repo] [pr]"
            )
        payload = tokens[1].strip() if len(tokens) > 1 else ""
        known = {entry["id"] for entry in manifest_entries(
            ProjectLayout.detect(project["workspace"])
        )}
        repo_id = ""
        parts = payload.split()
        if parts and parts[0] in known:
            repo_id = parts.pop(0)
        try:
            if action == "publish":
                title = " ".join(parts)
                result = publish(
                    self.settings,
                    self.ledger,
                    project,
                    repo_id=repo_id,
                    title=title,
                    wait=True,
                    api=self.github_api,
                )
            else:
                number = None
                for part in parts:
                    if part.isdigit():
                        number = int(part)
                    else:
                        return Reply(
                            f"unexpected argument: {part}; usage: "
                            "/github merge [repo] [pr]"
                        )
                result = merge_pr(
                    self.settings,
                    self.ledger,
                    project,
                    repo_id=repo_id,
                    number=number,
                    wait=True,
                    api=self.github_api,
                )
        except (
            GithubFlowError,
            GithubAPIError,
            GithubAuthError,
            GitOperationError,
        ) as exc:
            return Reply(f"error: {exc}")
        lines = [
            f"repository: {result.repo_id} ({result.full_name})",
            f"branch: {result.branch} -> {result.base}",
            f"pull request: #{result.pr_number} {result.pr_url}",
            f"checks: {result.checks}",
            f"merged: {'yes' if result.merged else 'no'}"
            + (f" ({result.merge_sha})" if result.merge_sha else ""),
            f"status: {result.status}",
        ]
        return Reply("\n".join(lines))

    def _projects(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        projects = self.ledger.list_projects()
        if not projects:
            return Reply("No projects. Create one with /new <name> | <brief>.")
        selected = self.ledger.get_session(chat_id)
        lines = [f"Projects: {len(projects)}"]
        for project in projects[:30]:
            state = project_state(self.ledger, project)
            generation = self.ledger.current_generation(project["id"])
            marker = "*" if project["id"] == selected else " "
            lines.append(
                f"{marker} {project['id']}\n    gen {generation}  {state}"
            )
        if len(projects) > 30:
            lines.append(f"... and {len(projects) - 30} more")
        lines.append("Select with /use <id>.")
        return Reply("\n".join(lines))

    def _use(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return Reply("Usage: /use <id or unique prefix>")
        project = self._resolve(rest.split()[0])
        if isinstance(project, Reply):
            return project
        self.ledger.set_session(chat_id, project["id"])
        state = project_state(self.ledger, project)
        return Reply(
            f"Selected {project['name']} ({project['id']}).\n"
            f"State: {state}.\n"
            "Messages without a command now go to this project's agent."
        )

    def _status(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        project_id = project["id"]
        generation = self.ledger.current_generation(project_id)
        checkpoint = self.ledger.checkpoint(project_id) or "none"
        layout = ProjectLayout.detect(project["workspace"])
        task = latest_task(layout)
        lines = [
            f"project: {project_id}",
            f"name: {project['name']}",
            f"layout: {layout.kind}",
            f"recipe: {project.get('recipe_id') or 'none'}",
            f"generation: {generation}",
            f"checkpoint: {checkpoint}",
            f"state: {project_state(self.ledger, project)}",
        ]
        if task is not None:
            lines.append(
                f"task: {task['title']} ({task['status']})"
            )
        staging_path = layout.artifact("staging.json")
        if staging_path.exists():
            try:
                staging = read_json(staging_path)
            except (OSError, json.JSONDecodeError):
                staging = {}
            lines.append(
                f"staging: {staging.get('status', 'unknown')} "
                f"{staging.get('url', '')}".rstrip()
            )
        for scope in ("staging", "production"):
            approval = latest_approval(self.ledger, project_id, scope, generation)
            if approval is None:
                lines.append(f"{scope} approval: none")
            else:
                lines.append(
                    f"{scope} approval: {approval['decision']} "
                    f"by {approval['actor']}"
                )
        lines.append(
            "reconciliation: "
            + reconciliation_status_path(
                layout.artifact("docs/program/reconciliation.md")
            )
        )
        proposals = summarize_proposals(layout.control)
        lines.append(f"proposals: {len(proposals)}")
        events = self.ledger.events(project_id, generation)[-8:]
        if events:
            lines.append("recent stages:")
            for event in events:
                lines.append(f"  {event['stage']} {event['status']}")
        return Reply("\n".join(lines))

    # ------------------------------------------------------------ work verbs

    def _run(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        project_id = project["id"]
        if project_is_done(self.ledger, project_id):
            return Reply(f"{project_id} is already done.")
        if not self.daemon_enabled:
            return Reply(
                "This gateway does not run iterations. "
                f"Run `forgel run {project_id}` on the host."
            )
        if is_paused(self.settings.home):
            return Reply("The daemon is paused. Send /resume first.")
        state = project_state(self.ledger, project)
        if state == "task cancelled":
            return Reply(f"{project_id}: the task was cancelled.")
        if state.startswith("task "):
            return Reply(
                f"{project_id}: {state}. The daemon will process queued tasks."
            )
        if state == "adopted":
            return Reply(
                f"{project_id} is a brownfield project: the template pipeline "
                "does not run. Send a change request as a plain message or "
                "inspect it with /status."
            )
        if state.startswith("awaiting staging approval") or state.startswith(
            "staging "
        ):
            return Reply(
                f"{project_id}: {state}.\n"
                f"Approve: /approve {project_id} staging"
            )
        layout = ProjectLayout.detect(project["workspace"])
        if reconciliation_status_path(
            layout.artifact("docs/program/reconciliation.md")
        ) in {"pending", "fix_required"}:
            return Reply(
                f"{project_id} needs a reconciliation decision.\n"
                f"Review: /sync {project_id}"
            )
        return Reply(
            f"{project_id} is queued; the daemon will run it in this cycle."
        )

    def _sync(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        try:
            result = sync_project(
                Path(project["workspace"]), self.ledger, project["id"]
            )
        except (SyncError, ValueError) as exc:
            return Reply(f"error: {exc}")
        if result.get("started"):
            return Reply(
                f"Reconciliation: {result.get('decision', 'forced')}. "
                f"Generation {result['generation']} started from "
                f"{result['from_stage']}."
            )
        if result.get("pending"):
            analysis = result.get("analysis", {})
            lines = [
                f"External changes: {result['count']} file(s). "
                "A decision is required."
            ]
            for label, key in (
                ("Violations", "violations"),
                ("Requirements changed", "requirements"),
                ("Documented modifications", "documented"),
                ("Undocumented changes", "undocumented"),
                ("Deletions", "deletions"),
            ):
                items = analysis.get(key, [])
                if items:
                    lines.append(f"{label}: {len(items)}")
            lines.append(f"See {result.get('reconciliation')}.")
            lines.append(
                f"Decide: /reconcile {project['id']} "
                "accept|fix|rollback|ignore [notes]"
            )
            return Reply("\n".join(lines))
        return Reply("No external changes detected.")

    def _reconcile(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, remainder = self._target_args(chat_id, rest, DECISIONS)
        if isinstance(project, Reply):
            return project
        tokens = remainder.split(maxsplit=1)
        if not tokens or tokens[0].lower() not in DECISIONS:
            return Reply(
                "Usage: /reconcile [id] accept|fix|rollback|ignore [notes]"
            )
        decision = tokens[0].lower()
        notes = tokens[1] if len(tokens) > 1 else ""
        try:
            result = reconcile_project(
                Path(project["workspace"]),
                self.ledger,
                project["id"],
                decision=decision,
                notes=notes,
            )
        except (SyncError, ValueError) as exc:
            return Reply(f"error: {exc}")
        if result.get("brownfield"):
            tail = "No generation started (brownfield project)."
        else:
            tail = (
                f"Generation {result['generation']} will re-run from "
                f"{result['from_stage']}."
            )
        return Reply(
            f"Reconciliation: {result['decision']} "
            f"({result['status']}). {tail}"
        )

    def _proposals(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        proposals = summarize_proposals(layout.control)
        if not proposals:
            return Reply("No proposals.")
        lines = [f"Proposals: {len(proposals)}"]
        for proposal in proposals:
            lines.append(
                f"{proposal['kind'] or '?'}  {proposal['status'] or '?'}  "
                f"{proposal['title']}\n  {proposal['file']}"
            )
        return Reply("\n".join(lines))

    # ------------------------------------------------------------- approvals

    def _approve(self, chat_id: int, rest: str, actor: str) -> Reply:
        return self._decide(chat_id, rest, actor, approved=True)

    def _reject(self, chat_id: int, rest: str, actor: str) -> Reply:
        return self._decide(chat_id, rest, actor, approved=False)

    def _decide(
        self, chat_id: int, rest: str, actor: str, approved: bool
    ) -> Reply:
        argument_tokens = SCOPES | {"--accept-compliance-responsibility"}
        project, remainder = self._target_args(chat_id, rest, argument_tokens)
        if isinstance(project, Reply):
            return project
        command = "/approve" if approved else "/reject"
        project_id = project["id"]
        tokens = remainder.split()
        scope = "staging"
        if tokens and tokens[0] in SCOPES:
            scope = tokens.pop(0)
        ack = "--accept-compliance-responsibility" in tokens
        notes = " ".join(
            token for token in tokens
            if token != "--accept-compliance-responsibility"
        )

        if approved and scope == "production" and not ack:
            state = self.ledger.checkpoint_state(project_id)
            if state is None or state[0] != "done":
                return Reply(
                    "Production approval requires a completed release.\n"
                    f"Current checkpoint: {state[0] if state else 'none'}. "
                    "Approve staging and let the daemon finish it first."
                )
            generation = self.ledger.current_generation(project_id)
            if not is_approved(
                self.ledger, project_id, "staging", generation
            ):
                return Reply(
                    "Approve staging before production:\n"
                    f"/approve {project_id} staging"
                )
            token = secrets.token_hex(4)
            self._production_tokens[token] = (project_id, time.time())
            markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "I accept responsibility",
                            "callback_data": f"ap:{token}:ok",
                        }
                    ],
                    [{"text": "Cancel", "callback_data": f"ap:{token}:no"}],
                ]
            }
            return Reply(
                self._production_prompt(project),
                reply_markup=markup,
            )

        try:
            record = record_approval(
                self.ledger,
                project_id,
                scope=scope,
                actor=actor,
                decision="approved" if approved else "rejected",
                compliance_ack=ack,
                notes=notes,
            )
        except ApprovalError as exc:
            return Reply(f"error: {exc}")
        return Reply(
            self._approval_text(record, production=scope == "production")
        )

    # ------------------------------------------------------------ config

    def _plan(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        goal = rest.strip()
        dry_run = False
        if goal.startswith("--dry-run"):
            dry_run = True
            goal = goal[len("--dry-run") :].strip()
        if goal.lower() in {"status", "list"}:
            layout = ProjectLayout.detect(project["workspace"])
            summary = plan_status(layout)
            if summary["status"] == "none":
                return Reply("No plans for this project.")
            lines = [
                f"Plan {summary['plan_id']}: {summary['status']} "
                f"({len(summary['tasks'])} tasks)"
            ]
            if summary["goal"]:
                lines.append(f"Goal: {summary['goal']}")
            for item in summary["tasks"]:
                suffix = (
                    f" (blocked by {item['blocked_by']})"
                    if item["blocked_by"]
                    else ""
                )
                lines.append(
                    f"- {item['status']}: {item['title']}{suffix}"
                )
            return Reply("\n".join(lines))
        if not goal:
            return Reply(
                "Usage: /plan [--dry-run] <milestone goal> or /plan status"
            )
        try:
            result = plan_project(
                self.settings,
                self.ledger,
                project,
                goal,
                dry_run=dry_run,
            )
        except PlanningError as exc:
            return Reply(f"error: {exc}")
        lines = [
            f"Plan {result.plan_id}: {len(result.tasks)} task(s)."
        ]
        if result.notes:
            lines.append(result.notes)
        for index, item in enumerate(result.tasks, 1):
            checks = item.get("checks") or []
            suffix = f" ({len(checks)} checks)" if checks else ""
            lines.append(
                f"{index}. {item['title']} "
                f"[{item.get('repo_id') or 'sole'}] -> "
                f"{item.get('task_id') or '-'}{suffix}"
            )
        if dry_run:
            lines.append("(dry run; no tasks created)")
        else:
            lines.append(
                "The daemon runs them in order; a task waits for its "
                "dependencies."
            )
        return Reply("\n".join(lines))

    def _peak(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        argument = rest.strip().lower()
        if argument in {"always", "off_peak"}:
            try:
                config_store.set_project_value(
                    layout.control, "models.peak_policy", argument
                )
            except ConfigError as exc:
                return Reply(f"error: {exc}")
            policy = argument
        elif argument in {"", "status"}:
            policy = peak.project_policy(self.settings, layout.control)
        else:
            return Reply("Usage: /peak [always|off_peak]")
        return Reply(
            peak.status_text(
                policy,
                hours=self.settings.peak_hours,
                tz_name=self.settings.timezone,
            )
        )

    def _config(self, chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=2)
        if not tokens:
            project = self._selected(chat_id)
            control = (
                None
                if isinstance(project, Reply)
                else ProjectLayout.detect(project["workspace"]).control
            )
            try:
                view = config_store.effective_view(
                    self.settings.home, control
                )
            except (ConfigError, daemon_config.DaemonConfigError) as exc:
                return Reply(f"error: {exc}")
            lines = [view, "", "Secrets:"]
            for key, state in secret_status(self.settings.home).items():
                lines.append(f"  {key}: {state}")
            return Reply("\n".join(lines))
        if tokens[0] != "set" or len(tokens) < 3:
            return Reply("Usage: /config or /config set <key> <value>")
        key, value = tokens[1], tokens[2]

        if key in daemon_config.SCHEMA:
            try:
                daemon_config.set_value(self.settings.home, key, value)
            except daemon_config.DaemonConfigError as exc:
                return Reply(f"error: {exc}")
            current = daemon_config.get_value(self.settings.home, key)
            note = ""
            if key in {"daemon.interval", "telegram.poll_timeout"}:
                note = "\nRestart the gateway to apply it."
            return Reply(
                f"Set {key} = {config_store.format_value(current)} "
                f"(daemon).{note}"
            )
        if key in SECRET_KEYS:
            return Reply(
                f"{key} is a secret. Use: /secret set {key} <value>"
            )
        if key in config_store.PROJECT_KINDS:
            project = self._selected(chat_id)
            if isinstance(project, Reply):
                return project
            control = ProjectLayout.detect(project["workspace"]).control
            config_path = control / "forgel.toml"
            if not config_path.exists():
                write_text(
                    config_path,
                    render_project_config(project["name"]),
                )
            try:
                typed = config_store.set_project_value(control, key, value)
            except (ConfigError, OSError) as exc:
                return Reply(f"error: {exc}")
            return Reply(
                f"Set {key} = {config_store.format_value(typed)} "
                f"(project {project['id']})."
            )
        return Reply(
            "Unknown setting.\n"
            "Project keys: "
            + ", ".join(sorted(config_store.PROJECT_KINDS))
            + "\nDaemon keys: "
            + ", ".join(sorted(daemon_config.SCHEMA))
        )

    def _secret(self, _chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=1)
        note = (
            "\nTelegram bots have no end-to-end encryption. This message is "
            "deleted after the command, but prefer environment variables or "
            "`forgel secret set` over SSH in production."
        )
        if not tokens:
            lines = ["Secrets (env overrides the file):"]
            for key, state in secret_status(self.settings.home).items():
                lines.append(f"  {key}: {state}")
            lines.append(
                "Set with /secret set <key> <value>; the message is deleted."
            )
            return Reply("\n".join(lines))

        action = tokens[0].lower()
        if action == "set":
            if len(tokens) < 2:
                return Reply("Usage: /secret set <key> <value>")
            parts = tokens[1].split(maxsplit=1)
            if len(parts) < 2:
                return Reply("Usage: /secret set <key> <value>")
            key, value = parts
            try:
                path = set_secret(self.settings.home, key, value)
            except (SecretError, OSError) as exc:
                return Reply(f"error: {exc}")
            restart = (
                "\nRestart the gateway to use a new telegram.bot_token."
                if key == "telegram.bot_token"
                else ""
            )
            return Reply(
                f"Saved {key} to {path.name} (mode 0600). "
                "The value was not echoed and the source message is being "
                "deleted." + restart + note,
                delete_source=True,
            )
        if action == "delete":
            if len(tokens) < 2:
                return Reply("Usage: /secret delete <key>")
            key = tokens[1].strip()
            try:
                removed = delete_secret(self.settings.home, key)
            except (SecretError, OSError) as exc:
                return Reply(f"error: {exc}")
            if removed:
                return Reply(f"Deleted {key} from {SECRETS_FILENAME}.")
            return Reply(f"{key} is not set in the file.")
        return Reply(
            "Usage: /secret, /secret set <key> <value>, "
            "/secret delete <key>"
        )

    # ----------------------------------------------------------- daemon

    def _pause(self, _chat_id: int, _rest: str, _actor: str) -> Reply:
        set_paused(self.settings.home, True)
        return Reply(
            "The daemon is paused. Tell me to resume when you want it "
            "running again."
        )

    def _resume(self, _chat_id: int, _rest: str, _actor: str) -> Reply:
        set_paused(self.settings.home, False)
        return Reply("The daemon is running again.")

    # --------------------------------------------------------------- actions

    def _execute_action(
        self, chat_id: int, actor: str, result: Any
    ) -> Reply:
        """Run a control action chosen by the model from the whitelist."""

        def combine(reply: Reply) -> Reply:
            text = str(getattr(result, "text", "") or "").strip()
            if text and text not in reply.text:
                return Reply(
                    f"{text}\n\n{reply.text}",
                    reply.reply_markup,
                    reply.callback_text,
                )
            return reply

        action = result.action
        args = dict(result.args or {})
        if action == "plan":
            goal = str(args.get("goal") or "").strip()
            if not goal:
                return Reply("Tell me the milestone goal.")
            return combine(self._plan(chat_id, goal, actor))
        if action == "status":
            return combine(self._status(chat_id, "", actor))
        if action == "tasks":
            return combine(self._tasks(chat_id, "", actor))
        if action == "run":
            return combine(self._run(chat_id, "", actor))
        if action in {"accept", "reject", "retry"}:
            project = self._selected(chat_id)
            if isinstance(project, Reply):
                return project
            layout = ProjectLayout.detect(project["workspace"])
            task_id = str(args.get("task_id") or "").strip()
            if not task_id:
                wanted = {
                    "accept": "review",
                    "reject": "review",
                    "retry": "failed",
                }[action]
                task = next(
                    (
                        item
                        for item in reversed(list_tasks(layout))
                        if item.get("status") == wanted
                    ),
                    None,
                )
                if task is None:
                    return Reply(
                        "There is no task waiting for that decision."
                    )
                task_id = str(task["id"])
            notes = str(args.get("notes") or "").strip()
            rest = f"{action} {task_id} {notes}".strip()
            return combine(self._task(chat_id, rest, actor))
        if action == "adopt":
            url = str(args.get("url") or "").strip()
            brief = str(args.get("brief") or "").strip()
            if not url:
                return Reply("Tell me the repository URL or path.")
            payload = f"{url} | {brief}" if brief else url
            return combine(self._adopt(chat_id, payload, actor))
        if action == "control_extract":
            path = str(args.get("path") or "").strip()
            return combine(
                self._control(
                    chat_id, f"extract {path}".strip(), actor
                )
            )
        if action == "repo_add":
            url = str(args.get("url") or "").strip()
            if not url:
                return Reply("Tell me the repository URL.")
            parts = [url]
            repo_id = str(args.get("id") or "").strip()
            if repo_id:
                parts.append(repo_id)
            deps = args.get("depends_on") or []
            if isinstance(deps, str):
                deps = [item for item in deps.split(",") if item]
            if deps:
                parts.append("depends_on=" + ",".join(str(d) for d in deps))
            return combine(
                self._repo(chat_id, "add " + " ".join(parts), actor)
            )
        if action == "repo_create":
            repo_id = str(args.get("id") or "").strip()
            if not repo_id:
                return Reply("Tell me the new repository id.")
            parts = [repo_id]
            org = str(args.get("org") or "").strip()
            if org:
                parts.append(f"org={org}")
            if args.get("public"):
                parts.append("public")
            deps = args.get("depends_on") or []
            if isinstance(deps, str):
                deps = [item for item in deps.split(",") if item]
            if deps:
                parts.append("depends_on=" + ",".join(str(d) for d in deps))
            path = str(args.get("path") or "").strip()
            if path:
                parts.append(f"path={path}")
            rest = "create " + " ".join(parts)
            description = str(args.get("description") or "").strip()
            if description:
                rest += " | " + description
            return combine(self._repo(chat_id, rest, actor))
        if action == "repo_publish":
            parts = []
            repo_id = str(args.get("id") or "").strip()
            if repo_id:
                parts.append(repo_id)
            org = str(args.get("org") or "").strip()
            if org:
                parts.append(f"org={org}")
            if args.get("public"):
                parts.append("public")
            return combine(
                self._repo(
                    chat_id, "publish " + " ".join(parts), actor
                )
            )
        if action == "peak":
            policy = str(args.get("policy") or "").strip()
            return combine(self._peak(chat_id, policy, actor))
        if action == "pause":
            return combine(self._pause(chat_id, "", actor))
        if action == "resume":
            return combine(self._resume(chat_id, "", actor))
        if action == "approve_staging":
            return combine(self._approve(chat_id, "staging", actor))
        return Reply(
            "I can't perform that action. Configuration, secrets and "
            "production approval stay explicit."
        )

    # ------------------------------------------------------------- agent

    def _message(self, chat_id: int, text: str, actor: str) -> Reply:
        if looks_like_secret(text):
            return Reply(
                "This looks like a secret and was not processed. Use "
                "/secret set <key> <value>; the message is being deleted.",
                delete_source=True,
            )
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        policy = peak.project_policy(self.settings, layout.control)
        if peak.should_defer(policy, hours=self.settings.peak_hours):
            return Reply(
                peak.defer_message(
                    hours=self.settings.peak_hours,
                    tz_name=self.settings.timezone,
                )
            )
        if self.agent is None:
            return Reply(
                "The project agent is not configured. Set "
                "FORGEL_MODEL_API_KEY on the host or use "
                "/secret set model.api_key <value>, then restart the gateway."
            )
        try:
            result = self.agent.handle(
                project, text, actor, session=str(chat_id)
            )
        except Exception as exc:  # noqa: BLE001 - answer instead of crashing
            return Reply(f"Agent error: {exc}")
        if result.kind in {"action", "actions"} and result.actions:
            replies = []
            narration = False
            actions = result.actions[:4]
            for index, item in enumerate(actions):
                action = str(item.get("action") or "")
                args = item.get("action_args") or {}
                proxy = SimpleNamespace(
                    action=action,
                    args=args,
                    text=result.text if index == 0 else "",
                )
                reply = self._execute_action(chat_id, actor, proxy)
                replies.append(reply)
                if action in {"status", "tasks"}:
                    narration = True
                lowered = reply.text.strip().lower()
                if lowered.startswith(
                    ("error", "tell me", "usage", "i can't")
                ):
                    break
            combined = "\n\n".join(
                reply.text for reply in replies if reply.text
            )
            if (
                narration
                and len(actions) == 1
                and self.agent is not None
            ):
                observation = build_context(
                    layout, project, self.ledger
                )
                narrated = self.agent.narrate(
                    project, text, observation
                ).strip()
                if narrated:
                    append_history(
                        layout,
                        "assistant",
                        narrated,
                        actor,
                        session=str(chat_id),
                    )
                    return Reply(narrated)
            return Reply(combined)
        return Reply(result.text)

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _github_hint(url: str, message: str) -> str:
        if "github.com" not in url:
            return ""
        lowered = message.lower()
        if not any(
            marker in lowered
            for marker in (
                "could not read username",
                "authentication failed",
                "terminal prompts disabled",
                "repository not found",
            )
        ):
            return ""
        return (
            "\n\nGitHub authentication failed. Set FORGEL_GITHUB_TOKEN on "
            "the host or /secret set github.token <token>; a fine-grained "
            "token needs Contents read/write."
        )

    def _selected(self, chat_id: int) -> dict[str, Any] | Reply:
        project_id = self.ledger.get_session(chat_id)
        if project_id is None:
            return Reply(
                "No project selected. Use /projects, then /use <id>."
            )
        project = self.ledger.get_project(project_id)
        if project is None:
            self.ledger.clear_session(chat_id)
            return Reply(
                "The selected project no longer exists. Use /projects."
            )
        return project

    def _resolve(self, token: str) -> dict[str, Any] | Reply:
        try:
            return resolve_project(self.ledger, token)
        except ProjectError as exc:
            return Reply(f"error: {exc}")

    def _target(
        self, chat_id: int, rest: str
    ) -> tuple[dict[str, Any] | Reply, str]:
        """Resolve an explicit leading project id, or the selected project."""

        rest = rest.strip()
        if not rest:
            return self._selected(chat_id), ""
        token, _, remainder = rest.partition(" ")
        project = self._resolve(token)
        return project, remainder.strip()

    def _target_args(
        self, chat_id: int, rest: str, argument_tokens: set[str]
    ) -> tuple[dict[str, Any] | Reply, str]:
        """Like :meth:`_target`, but a leading argument keeps the selection."""

        rest = rest.strip()
        if not rest:
            return self._selected(chat_id), ""
        token, _, remainder = rest.partition(" ")
        if token in argument_tokens:
            return self._selected(chat_id), rest
        project = self._resolve(token)
        return project, remainder.strip()

    def _approval_text(self, record: dict[str, Any], production: bool) -> str:
        scope = "Production" if production else "Staging"
        if record["decision"] == "approved":
            text = f"{scope} approval recorded"
        else:
            text = f"{scope} rejected"
        text += (
            f" for {record['project_id']} (generation {record['generation']}"
        )
        if record.get("release_sha"):
            text += f", release {record['release_sha']}"
        text += f") by {record['actor']}."
        if record["decision"] != "approved":
            text += (
                "\nThe project stays at the approval gate. Use /sync to start "
                "a new generation, then decide again."
            )
        elif production:
            text += (
                "\nNo deploy provider is configured, so this release stays "
                "manual; the approval is recorded in the ledger and "
                "docs/program/approvals.md."
            )
        else:
            text += "\nThe daemon will continue on its next cycle."
        return text

    def _production_prompt(self, project: dict[str, Any]) -> str:
        generation = self.ledger.current_generation(project["id"])
        return (
            f"Production approval for {project['name']} "
            f"({project['id']}), generation {generation}.\n\n"
            "Forgel is a software development tool, not a law firm. "
            "Jurisdiction packs are advisory and do not establish legal "
            "compliance. By accepting, you confirm that you are responsible "
            "for the product's regulatory compliance in its target markets. "
            "See docs/program/jurisdiction/disclaimer.md.\n\n"
            "Approve production?"
        )
