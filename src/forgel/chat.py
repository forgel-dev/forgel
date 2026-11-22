"""Chat command router and user-facing UX.

The router is transport-free: it turns text from one chat into core calls and a
reply. It never touches the network, so it is fully testable. Every command is
scoped to one project, chosen explicitly or from the chat's session; the agent
receives only that project's context.
"""

from __future__ import annotations

import re
import secrets
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from . import config_store, daemon_config, peak
from .i18n import has as _has
from .i18n import t as _t
from .language import detect as detect_language
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
from .release import ReleaseError, release_project
from .task_review import accept_task, reject_task, rerun_review
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

HELP = _t("en", "help")


@dataclass(frozen=True)
class Reply:
    text: str
    reply_markup: dict[str, Any] | None = None
    callback_text: str = ""
    delete_source: bool = False
    failed: bool = False


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
        self._languages: dict[int, str] = {}

    # ------------------------------------------------------------- language

    def _language(self, chat_id: int) -> str:
        return self._languages.get(chat_id, "en")

    def language(self, chat_id: int) -> str:
        """The last language seen in this chat (used by channel notices)."""

        return self._language(chat_id)

    def _text(self, chat_id: int, text_key: str, **values: Any) -> str:
        return _t(self._language(chat_id), text_key, **values)

    def _error(self, chat_id: int, key: str, **values: Any) -> Reply:
        return Reply(
            self._text(chat_id, key, **values),
            failed=True,
        )

    def _review_client(self) -> Any:
        if self.agent is not None:
            return self.agent.client
        from .model import build_model_client

        return build_model_client(self.settings.home)

    def _status_name(self, chat_id: int, status: object) -> str:
        key = str(status or "")
        lang = self._language(chat_id)
        return _t(lang, key) if _has(lang, key) else key

    def _plan_status_name(self, chat_id: int, status: object) -> str:
        key = f"plan_{status or 'none'}"
        lang = self._language(chat_id)
        return (
            _t(lang, key)
            if _has(lang, key)
            else str(status or "")
        )

    # ------------------------------------------------------------- dispatch

    def handle(self, chat_id: int, text: str, actor: str) -> Reply:
        probe = (
            text
            if not text.strip().startswith("/")
            else text.partition(" ")[2]
        )
        self._languages[chat_id] = detect_language(
            probe, self._language(chat_id)
        )
        try:
            reply = self._dispatch(chat_id, text, actor)
        except Exception as exc:  # noqa: BLE001 - the router must stay up
            reply = self._error(
                chat_id, "chat_error", error=exc
            )
        if self.agent is not None and reply.failed:
            selected = self._selected(chat_id)
            if not isinstance(selected, Reply):
                try:
                    explanation = self.agent.explain_failure(
                        selected, text, reply.text
                    )
                except Exception:  # noqa: BLE001 - keep the original error
                    explanation = ""
                if explanation:
                    reply = Reply(explanation)
        return reply

    def _dispatch(self, chat_id: int, text: str, actor: str) -> Reply:
        text = text.strip()
        if not text:
            return Reply(self._text(chat_id, "chat_empty"))
        if not text.startswith("/"):
            return self._message(chat_id, text, actor)
        command_token, _, rest = text.partition(" ")
        command = command_token.split("@", 1)[0].lower()
        rest = rest.strip()

        handlers: dict[str, Callable[[int, str, str], Reply]] = {
            "/start": lambda chat, _rest, _actor: Reply(
                self._text(chat, "help")
            ),
            "/help": lambda chat, _rest, _actor: Reply(
                self._text(chat, "help")
            ),
            "/new": self._new,
            "/adopt": self._adopt,
            "/repo": self._repo,
            "/control": self._control,
            "/github": self._github,
            "/release": self._release,
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
            return self._error(
                chat_id,
                "chat_unknown_command",
                command=command,
            )
        return handler(chat_id, rest, actor)

    def handle_callback(self, chat_id: int, data: str, actor: str) -> Reply:
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "ap":
            return Reply(
                self._text(chat_id, "chat_unknown_action"),
                callback_text=self._text(
                    chat_id, "chat_callback_unknown"
                ),
            )
        _, token, action = parts
        entry = self._production_tokens.pop(token, None)
        if entry is None or time.time() - entry[1] > self._token_ttl:
            return Reply(
                self._text(chat_id, "chat_approval_expired"),
                callback_text=self._text(
                    chat_id, "chat_callback_expired"
                ),
            )
        project_id = entry[0]
        if action == "no":
            return Reply(
                self._text(
                    chat_id,
                    "chat_production_cancelled",
                    project=project_id,
                ),
                callback_text=self._text(
                    chat_id, "chat_callback_cancelled"
                ),
            )
        if action != "ok":
            return Reply(
                self._text(chat_id, "chat_unknown_action"),
                callback_text=self._text(
                    chat_id, "chat_callback_unknown"
                ),
            )
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
            return Reply(
                self._text(chat_id, "chat_error", error=exc),
                callback_text=self._text(
                    chat_id, "chat_callback_not_approved"
                ),
                failed=True,
            )
        return Reply(
            self._approval_text(
                chat_id, record, production=True
            ),
            callback_text=self._text(
                chat_id, "chat_callback_approved"
            ),
        )

    # ------------------------------------------------------------- projects

    def _new(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return self._error(chat_id, "chat_new_usage")
        if "|" in rest:
            name, brief = rest.split("|", 1)
        else:
            name, brief = derive_name(rest), rest
        try:
            project_id = create_project(
                self.settings, self.ledger, name, brief
            )
        except ProjectError as exc:
            return self._error(chat_id, "chat_error", error=exc)
        self.ledger.set_session(chat_id, project_id)
        return Reply(
            self._text(
                chat_id, "chat_new_created", project=project_id
            )
        )

    def _adopt(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return self._error(chat_id, "chat_adopt_usage")
        url, _, brief = rest.partition("|")
        try:
            result = adopt_repository(
                self.settings, self.ledger, url.strip(), brief.strip()
            )
        except (AdoptError, ProviderError) as exc:
            return self._error(
                chat_id,
                "chat_error_with_hint",
                error=exc,
                hint=self._github_hint(url, str(exc)),
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
                self._text(
                    chat_id,
                    "chat_adopted_linked",
                    project=result.project_id,
                ),
                self._text(
                    chat_id,
                    "chat_repository",
                    repo=result.repo_id,
                    provider=result.provider,
                ),
                self._text(chat_id, "chat_brownfield_in_place"),
                self._text(
                    chat_id, "chat_control_artifacts", path=control
                ),
            ]
        else:
            lines = [
                self._text(
                    chat_id,
                    "chat_adopted",
                    url=result.url,
                    project=result.project_id,
                ),
                self._text(
                    chat_id,
                    "chat_repository",
                    repo=result.repo_id,
                    provider=result.provider,
                ),
                self._text(chat_id, "chat_brownfield_no_regen"),
                self._text(chat_id, "chat_config_initialized"),
            ]
        if result.provider == "local":
            lines.append(self._text(chat_id, "chat_no_origin"))
        if result.provider == "github":
            if result.auth.configured:
                lines.append(
                    self._text(
                        chat_id,
                        "chat_github_detail",
                        detail=result.auth.detail,
                    )
                )
            else:
                lines.append(
                    self._text(
                        chat_id,
                        "chat_github_private",
                        detail=result.auth.detail,
                    )
                )
        lines.append(self._text(chat_id, "chat_link_hint"))
        lines.append(self._text(chat_id, "chat_link_when"))
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
                return Reply(self._text(chat_id, "chat_repo_none"))
            lines = [
                self._text(
                    chat_id, "chat_repo_list", count=len(repos)
                )
            ]
            for entry in repos:
                depends = (
                    ", ".join(entry["depends_on"])
                    or self._text(chat_id, "chat_none")
                )
                lines.append(
                    self._text(
                        chat_id,
                        "chat_repo_entry",
                        id=entry["id"],
                        role=entry["role"],
                        provider=entry["provider"],
                        url=repo_location(layout, entry) or "—",
                        depends=depends,
                    )
                )
            return Reply("\n".join(lines))
        if action == "link":
            if len(tokens) < 2:
                return self._error(chat_id, "chat_repo_link_usage")
            parts = tokens[1].split()
            if not parts:
                return self._error(chat_id, "chat_repo_link_usage")
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
                return self._error(chat_id, "chat_repo_link_usage")
            try:
                entry = set_dependencies(
                    self.settings,
                    self.ledger,
                    project,
                    repo_id,
                    depends_on,
                )
            except (AdoptError, ValueError) as exc:
                return self._error(chat_id, "chat_error", error=exc)
            edges = (
                ", ".join(entry["depends_on"])
                or self._text(chat_id, "chat_none")
            )
            return Reply(
                self._text(
                    chat_id,
                    "chat_repo_updated",
                    repo=entry["id"],
                    edges=edges,
                )
            )
        if action in {"create", "publish"}:
            if len(tokens) < 2 and action == "create":
                return self._error(
                    chat_id, "chat_repo_create_usage"
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
                    return self._error(
                        chat_id,
                        "chat_unexpected_argument",
                        token=token,
                    )
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
                        self._text(
                            chat_id,
                            "chat_repo_created",
                            repo=created.entry["id"],
                            url=created.url,
                            project=project["id"],
                        )
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
                    return Reply(
                        self._text(
                            chat_id, "chat_repo_nothing_to_publish"
                        )
                    )
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
                    self._text(
                        chat_id,
                        "chat_repo_published",
                        items="\n".join(lines),
                    )
                )
            except (
                AdoptError,
                ProviderError,
                GithubAuthError,
                GithubAPIError,
            ) as exc:
                hint = self._github_hint(
                    chat_id, "github.com", str(exc)
                )
                return self._error(
                    chat_id,
                    "chat_error_with_hint",
                    error=exc,
                    hint=hint,
                )
        if action != "add":
            return self._error(chat_id, "chat_repo_usage")
        if len(tokens) < 2:
            return self._error(chat_id, "chat_repo_add_usage")
        parts = tokens[1].split()
        if not parts:
            return self._error(chat_id, "chat_repo_add_usage")
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
                return self._error(
                    chat_id,
                    "chat_unexpected_argument",
                    token=token,
                )
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
            return self._error(
                chat_id,
                "chat_error_with_hint",
                error=exc,
                hint=self._github_hint(chat_id, url, str(exc)),
            )
        entry = result.entry
        lines = [
            self._text(
                chat_id,
                "chat_repo_added",
                repo=entry["id"],
                project=project["id"],
            ),
            self._text(
                chat_id,
                "chat_repo_provider",
                provider=entry["provider"],
                url=entry.get("path") or entry["url"] or "—",
            ),
        ]
        if entry["depends_on"]:
            lines.append(
                self._text(
                    chat_id,
                    "chat_repo_dependency_edges",
                    edges=", ".join(entry["depends_on"]),
                )
            )
        else:
            lines.append(
                self._text(chat_id, "chat_repo_separate")
            )
        return Reply("\n".join(lines))

    def _tasks(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        entries = list_tasks(layout)
        if not entries:
            return Reply(self._text(chat_id, "chat_tasks_none"))
        lines = [
            self._text(
                chat_id, "chat_tasks_header", count=len(entries)
            )
        ]
        for task in entries:
            summary = str(task.get("result", {}).get("summary", ""))
            lines.append(
                f"{task['id']}  "
                f"{self._status_name(chat_id, task['status'])}  "
                f"{task['title']}"
            )
            if summary:
                lines.append(f"  {summary}")
        return Reply("\n".join(lines))

    def _task(self, chat_id: int, rest: str, _actor: str) -> Reply:
        usage = self._text(chat_id, "chat_task_usage")
        tokens = rest.split(maxsplit=2)
        action = tokens[0].lower() if tokens else ""
        if action not in {"cancel", "retry", "accept", "reject", "review"}:
            return Reply(usage, failed=True)
        if len(tokens) < 2:
            return Reply(usage, failed=True)
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        task_id = tokens[1]
        notes = tokens[2].strip() if len(tokens) > 2 else ""
        if action == "review":
            client = self._review_client()
            if client is None:
                return self._error(chat_id, "chat_review_no_model")
            try:
                updated = rerun_review(
                    self.settings,
                    self.ledger,
                    project,
                    task_id,
                    client,
                )
            except ValueError as exc:
                return self._error(chat_id, "chat_error", error=exc)
            commit_task(
                layout,
                updated["id"],
                f"Review task {updated['id']}",
            )
            return Reply(
                self._text(
                    chat_id,
                    "chat_task_reviewed",
                    task=updated["id"],
                    status=self._status_name(
                        chat_id, updated["status"]
                    ),
                )
            )
        if action in {"cancel", "retry"}:
            try:
                task = (
                    cancel_task(layout, task_id)
                    if action == "cancel"
                    else retry_task(layout, task_id)
                )
            except ValueError as exc:
                return self._error(chat_id, "chat_error", error=exc)
            commit_task(
                layout,
                task["id"],
                f"{action.capitalize()} task {task['id']}",
            )
            return Reply(
                self._text(
                    chat_id,
                    "chat_task_cancelled"
                    if action == "cancel"
                    else "chat_task_requeued",
                    task=task["id"],
                )
            )
        task = get_task(layout, task_id)
        if task is None:
            return self._error(
                chat_id, "chat_unknown_task", task=task_id
            )
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
            self._text(
                chat_id,
                "chat_task_accepted"
                if action == "accept"
                else "chat_task_rejected",
                task=updated["id"],
                status=self._status_name(
                    chat_id, updated["status"]
                ),
            )
        )

    def _control(self, chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=1)
        action = tokens[0].lower() if tokens else ""
        if action != "extract":
            return self._error(chat_id, "chat_control_usage")
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        path = tokens[1].strip() if len(tokens) > 1 else ""
        try:
            result = extract_control(
                self.settings, self.ledger, project, path
            )
        except AdoptError as exc:
            return self._error(chat_id, "chat_error", error=exc)
        return Reply(
            self._text(
                chat_id, "chat_control_moved", path=result.control
            )
        )

    def _github(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        tokens = rest.split(maxsplit=1)
        action = tokens[0].lower() if tokens else "status"
        if action == "status":
            return Reply(
                status_text(
                    self.settings,
                    project,
                    lang=self._language(chat_id),
                )
            )
        if action not in {"publish", "merge"}:
            return self._error(chat_id, "chat_github_usage")
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
                        return self._error(
                            chat_id,
                            "chat_github_merge_arg",
                            token=part,
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
            return self._error(chat_id, "chat_error", error=exc)
        merged = self._text(
            chat_id, "chat_yes" if result.merged else "chat_no"
        )
        lines = [
            self._text(
                chat_id,
                "chat_github_result_repository",
                repo=result.repo_id,
                full=result.full_name,
            ),
            self._text(
                chat_id,
                "chat_github_result_branch",
                branch=result.branch,
                base=result.base,
            ),
            self._text(
                chat_id,
                "chat_github_result_pr",
                number=result.pr_number,
                url=result.pr_url,
            )
            if result.pr_number
            else self._text(chat_id, "chat_github_result_pushed"),
            self._text(
                chat_id,
                "chat_github_result_checks",
                checks=result.checks,
            ),
            self._text(
                chat_id,
                "chat_github_result_merged",
                merged=merged,
            )
            + (f" ({result.merge_sha})" if result.merge_sha else ""),
            self._text(
                chat_id,
                "chat_github_result_status",
                status=result.status,
            ),
        ]
        return Reply("\n".join(lines))

    def _release(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project = self._selected(chat_id)
        if isinstance(project, Reply):
            return project
        try:
            tokens = shlex.split(rest)
        except ValueError as exc:
            return self._error(chat_id, "chat_error", error=exc)
        version = ""
        notes = ""
        repo_id = ""
        draft = False
        generate_notes = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token in {"--version", "--notes", "--repo"}:
                if index + 1 >= len(tokens):
                    return self._error(chat_id, "chat_release_usage")
                value = tokens[index + 1]
                if token == "--version":
                    version = value
                elif token == "--notes":
                    notes = value
                else:
                    repo_id = value
                index += 2
                continue
            if token == "--draft":
                draft = True
            elif token == "--generate-notes":
                generate_notes = True
            else:
                return self._error(chat_id, "chat_release_usage")
            index += 1
        try:
            result = release_project(
                self.settings,
                self.ledger,
                project,
                version=version,
                notes=notes,
                repo_id=repo_id,
                draft=draft,
                generate_notes=generate_notes,
                log=lambda _message: None,
            )
        except ReleaseError as exc:
            return self._error(chat_id, "chat_error", error=exc)
        lines = [
            self._text(
                chat_id,
                "chat_release_header",
                version=result.tag,
                status=result.status,
                manifest=result.manifest,
            )
        ]
        for item in result.repos:
            lines.append(
                self._text(
                    chat_id,
                    "chat_release_repo",
                    repo=item.repo_id,
                    tag=item.tag,
                    sha=item.sha,
                    detail=item.release_url or item.detail,
                )
            )
        return Reply("\n".join(lines))

    def _projects(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        projects = self.ledger.list_projects()
        if not projects:
            return Reply(self._text(chat_id, "chat_projects_none"))
        selected = self.ledger.get_session(chat_id)
        lines = [
            self._text(
                chat_id, "chat_projects_header", count=len(projects)
            )
        ]
        for project in projects[:30]:
            state = project_state(self.ledger, project)
            generation = self.ledger.current_generation(project["id"])
            marker = "*" if project["id"] == selected else " "
            lines.append(
                self._text(
                    chat_id,
                    "chat_project_entry",
                    marker=marker,
                    project=project["id"],
                    generation=generation,
                    state=state,
                )
            )
        if len(projects) > 30:
            lines.append(
                self._text(
                    chat_id,
                    "chat_projects_more",
                    count=len(projects) - 30,
                )
            )
        lines.append(self._text(chat_id, "chat_projects_select"))
        return Reply("\n".join(lines))

    def _use(self, chat_id: int, rest: str, _actor: str) -> Reply:
        if not rest:
            return self._error(chat_id, "chat_use_usage")
        project = self._resolve(chat_id, rest.split()[0])
        if isinstance(project, Reply):
            return project
        self.ledger.set_session(chat_id, project["id"])
        state = project_state(self.ledger, project)
        return Reply(
            self._text(
                chat_id,
                "chat_use_selected",
                name=project["name"],
                project=project["id"],
                state=state,
            )
        )

    def _status(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        project_id = project["id"]
        generation = self.ledger.current_generation(project_id)
        checkpoint = self.ledger.checkpoint(project_id) or self._text(
            chat_id, "chat_none"
        )
        layout = ProjectLayout.detect(project["workspace"])
        task = latest_task(layout)
        lines = [
            self._text(
                chat_id, "chat_status_project", project=project_id
            ),
            self._text(
                chat_id, "chat_status_name", name=project["name"]
            ),
            self._text(
                chat_id, "chat_status_layout", layout=layout.kind
            ),
            self._text(
                chat_id,
                "chat_status_recipe",
                recipe=project.get("recipe_id")
                or self._text(chat_id, "chat_none"),
            ),
            self._text(
                chat_id,
                "chat_status_generation",
                generation=generation,
            ),
            self._text(
                chat_id, "chat_status_checkpoint", checkpoint=checkpoint
            ),
            self._text(
                chat_id,
                "chat_status_state",
                state=project_state(self.ledger, project),
            ),
        ]
        if task is not None:
            lines.append(
                self._text(
                    chat_id,
                    "chat_status_task",
                    title=task["title"],
                    status=self._status_name(chat_id, task["status"]),
                )
            )
        staging_path = layout.artifact("staging.json")
        if staging_path.exists():
            try:
                staging = read_json(staging_path)
            except (OSError, json.JSONDecodeError):
                staging = {}
            lines.append(
                self._text(
                    chat_id,
                    "chat_status_staging",
                    status=self._status_name(
                        chat_id, staging.get("status", "unknown")
                    ),
                    url=staging.get("url", ""),
                ).rstrip()
            )
        for scope in ("staging", "production"):
            approval = latest_approval(self.ledger, project_id, scope, generation)
            scope_name = self._text(chat_id, f"chat_scope_{scope}")
            if approval is None:
                lines.append(
                    self._text(
                        chat_id,
                        "chat_status_approval_none",
                        scope=scope_name,
                    )
                )
            else:
                lines.append(
                    self._text(
                        chat_id,
                        "chat_status_approval",
                        scope=scope_name,
                        decision=approval["decision"],
                        actor=approval["actor"],
                    )
                )
        lines.append(
            self._text(
                chat_id,
                "chat_status_reconciliation",
                status=reconciliation_status_path(
                    layout.artifact("docs/program/reconciliation.md")
                ),
            )
        )
        proposals = summarize_proposals(layout.control)
        lines.append(
            self._text(
                chat_id,
                "chat_status_proposals",
                count=len(proposals),
            )
        )
        events = self.ledger.events(project_id, generation)[-8:]
        if events:
            lines.append(self._text(chat_id, "chat_status_recent"))
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
            return Reply(
                self._text(
                    chat_id, "chat_run_done", project=project_id
                )
            )
        if not self.daemon_enabled:
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_gateway",
                    project=project_id,
                )
            )
        if is_paused(self.settings.home):
            return Reply(self._text(chat_id, "chat_daemon_paused"))
        state = project_state(self.ledger, project)
        if state == "task cancelled":
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_cancelled",
                    project=project_id,
                )
            )
        if state.startswith("task "):
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_state",
                    project=project_id,
                    state=state,
                )
            )
        if state == "adopted":
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_brownfield",
                    project=project_id,
                )
            )
        if state.startswith("awaiting staging approval") or state.startswith(
            "staging "
        ):
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_approval",
                    project=project_id,
                    state=state,
                )
            )
        layout = ProjectLayout.detect(project["workspace"])
        if reconciliation_status_path(
            layout.artifact("docs/program/reconciliation.md")
        ) in {"pending", "fix_required"}:
            return Reply(
                self._text(
                    chat_id,
                    "chat_run_reconcile",
                    project=project_id,
                )
            )
        return Reply(
            self._text(
                chat_id, "chat_run_queued", project=project_id
            )
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
            return self._error(chat_id, "chat_error", error=exc)
        if result.get("started"):
            return Reply(
                self._text(
                    chat_id,
                    "chat_sync_started",
                    decision=result.get("decision", "forced"),
                    generation=result["generation"],
                    stage=result["from_stage"],
                )
            )
        if result.get("pending"):
            analysis = result.get("analysis", {})
            lines = [
                self._text(
                    chat_id,
                    "chat_sync_pending",
                    count=result["count"],
                )
            ]
            for key in (
                "violations",
                "requirements",
                "documented",
                "undocumented",
                "deletions",
            ):
                items = analysis.get(key, [])
                if items:
                    lines.append(
                        self._text(
                            chat_id,
                            f"chat_sync_{key}",
                            count=len(items),
                        )
                    )
            lines.append(
                self._text(
                    chat_id,
                    "chat_sync_see",
                    path=result.get("reconciliation"),
                )
            )
            lines.append(
                self._text(
                    chat_id,
                    "chat_sync_decide",
                    project=project["id"],
                )
            )
            return Reply("\n".join(lines))
        return Reply(self._text(chat_id, "chat_sync_none"))

    def _reconcile(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, remainder = self._target_args(chat_id, rest, DECISIONS)
        if isinstance(project, Reply):
            return project
        tokens = remainder.split(maxsplit=1)
        if not tokens or tokens[0].lower() not in DECISIONS:
            return self._error(chat_id, "chat_reconcile_usage")
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
            return self._error(chat_id, "chat_error", error=exc)
        if result.get("brownfield"):
            tail = self._text(chat_id, "chat_reconcile_brownfield")
        else:
            tail = self._text(
                chat_id,
                "chat_reconcile_rerun",
                generation=result["generation"],
                stage=result["from_stage"],
            )
        return Reply(
            self._text(
                chat_id,
                "chat_reconcile_result",
                decision=result["decision"],
                status=result["status"],
                tail=tail,
            )
        )

    def _proposals(self, chat_id: int, rest: str, _actor: str) -> Reply:
        project, _remainder = self._target(chat_id, rest)
        if isinstance(project, Reply):
            return project
        layout = ProjectLayout.detect(project["workspace"])
        proposals = summarize_proposals(layout.control)
        if not proposals:
            return Reply(self._text(chat_id, "chat_proposals_none"))
        lines = [
            self._text(
                chat_id, "chat_proposals_header", count=len(proposals)
            )
        ]
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
                    self._text(
                        chat_id,
                        "chat_production_needs_release",
                        checkpoint=(
                            state[0]
                            if state
                            else self._text(chat_id, "chat_none")
                        ),
                    )
                )
            generation = self.ledger.current_generation(project_id)
            if not is_approved(
                self.ledger, project_id, "staging", generation
            ):
                return Reply(
                    self._text(
                        chat_id,
                        "chat_production_after_staging",
                        project=project_id,
                    )
                )
            token = secrets.token_hex(4)
            self._production_tokens[token] = (project_id, time.time())
            markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": self._text(
                                chat_id, "chat_button_accept"
                            ),
                            "callback_data": f"ap:{token}:ok",
                        }
                    ],
                    [
                        {
                            "text": self._text(
                                chat_id, "chat_button_cancel"
                            ),
                            "callback_data": f"ap:{token}:no",
                        }
                    ],
                ]
            }
            return Reply(
                self._production_prompt(chat_id, project),
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
            return self._error(chat_id, "chat_error", error=exc)
        return Reply(
            self._approval_text(
                chat_id,
                record,
                production=scope == "production",
            )
        )

    # ------------------------------------------------------------ config

    def _plan(
        self,
        chat_id: int,
        rest: str,
        _actor: str,
        release_class: str = "minor",
        product_intent: str = "",
        user_experience: str = "",
    ) -> Reply:
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
                return Reply(self._text(chat_id, "chat_plan_none"))
            lines = [
                self._text(
                    chat_id,
                    "chat_plan_status_header",
                    plan=summary["plan_id"],
                    status=self._plan_status_name(
                        chat_id, summary["status"]
                    ),
                    count=len(summary["tasks"]),
                )
            ]
            if summary["goal"]:
                lines.append(
                    self._text(
                        chat_id,
                        "chat_plan_goal",
                        goal=summary["goal"],
                    )
                )
            for item in summary["tasks"]:
                suffix = (
                    self._text(
                        chat_id,
                        "chat_plan_blocked",
                        blocked=item["blocked_by"],
                    )
                    if item["blocked_by"]
                    else ""
                )
                lines.append(
                    self._text(
                        chat_id,
                        "chat_plan_task",
                        status=self._status_name(
                            chat_id, item["status"]
                        ),
                        title=item["title"],
                        suffix=suffix,
                    )
                )
            return Reply("\n".join(lines))
        if not goal:
            return self._error(chat_id, "chat_plan_usage")
        try:
            result = plan_project(
                self.settings,
                self.ledger,
                project,
                goal,
                dry_run=dry_run,
                release_class=release_class,
                product_intent=product_intent,
                user_experience=user_experience,
            )
        except PlanningError as exc:
            return self._error(chat_id, "chat_error", error=exc)
        lines = [
            self._text(
                chat_id,
                "chat_plan_header",
                plan=result.plan_id,
                count=len(result.tasks),
            )
        ]
        if result.notes:
            lines.append(result.notes)
        for index, item in enumerate(result.tasks, 1):
            checks = item.get("checks") or []
            suffix = (
                self._text(
                    chat_id, "chat_plan_checks", count=len(checks)
                )
                if checks
                else ""
            )
            lines.append(
                self._text(
                    chat_id,
                    "chat_plan_entry",
                    index=index,
                    title=item["title"],
                    repo=item.get("repo_id")
                    or self._text(chat_id, "chat_sole"),
                    task=item.get("task_id") or "-",
                    suffix=suffix,
                )
            )
        if dry_run:
            lines.append(self._text(chat_id, "chat_plan_dry_run"))
        else:
            lines.append(self._text(chat_id, "chat_plan_queued"))
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
                return self._error(chat_id, "chat_error", error=exc)
            policy = argument
        elif argument in {"", "status"}:
            policy = peak.project_policy(self.settings, layout.control)
        else:
            return self._error(chat_id, "chat_peak_usage")
        return Reply(
            peak.status_text(
                policy,
                hours=self.settings.peak_hours,
                tz_name=self.settings.timezone,
                lang=self._language(chat_id),
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
                return self._error(chat_id, "chat_error", error=exc)
            lines = [
                view,
                "",
                self._text(chat_id, "chat_config_secrets_header"),
            ]
            for key, state in secret_status(self.settings.home).items():
                lines.append(f"  {key}: {state}")
            return Reply("\n".join(lines))
        if tokens[0] != "set" or len(tokens) < 3:
            return self._error(chat_id, "chat_config_usage")
        key, value = tokens[1], tokens[2]

        if key in daemon_config.SCHEMA:
            try:
                daemon_config.set_value(self.settings.home, key, value)
            except daemon_config.DaemonConfigError as exc:
                return self._error(chat_id, "chat_error", error=exc)
            current = daemon_config.get_value(self.settings.home, key)
            note = ""
            if key in {"daemon.interval", "telegram.poll_timeout"}:
                note = self._text(chat_id, "chat_config_restart")
            return Reply(
                self._text(
                    chat_id,
                    "chat_config_set_daemon",
                    key=key,
                    value=config_store.format_value(current),
                    note=note,
                )
            )
        if key in SECRET_KEYS:
            return Reply(
                self._text(chat_id, "chat_config_secret", key=key)
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
                return self._error(chat_id, "chat_error", error=exc)
            return Reply(
                self._text(
                    chat_id,
                    "chat_config_set_project",
                    key=key,
                    value=config_store.format_value(typed),
                    project=project["id"],
                )
            )
        return Reply(
            self._text(
                chat_id,
                "chat_config_unknown",
                project_keys=", ".join(
                    sorted(config_store.PROJECT_KINDS)
                ),
                daemon_keys=", ".join(sorted(daemon_config.SCHEMA)),
            )
        )

    def _secret(self, chat_id: int, rest: str, _actor: str) -> Reply:
        tokens = rest.split(maxsplit=1)
        note = self._text(chat_id, "chat_secret_note")
        if not tokens:
            lines = [
                self._text(chat_id, "chat_secret_header"),
            ]
            for key, state in secret_status(self.settings.home).items():
                lines.append(f"  {key}: {state}")
            lines.append(self._text(chat_id, "chat_secret_hint"))
            return Reply("\n".join(lines))

        action = tokens[0].lower()
        if action == "set":
            if len(tokens) < 2:
                return self._error(chat_id, "chat_secret_set_usage")
            parts = tokens[1].split(maxsplit=1)
            if len(parts) < 2:
                return self._error(chat_id, "chat_secret_set_usage")
            key, value = parts
            try:
                path = set_secret(self.settings.home, key, value)
            except (SecretError, OSError) as exc:
                return self._error(chat_id, "chat_error", error=exc)
            restart = (
                self._text(chat_id, "chat_secret_restart")
                if key == "telegram.bot_token"
                else ""
            )
            return Reply(
                self._text(
                    chat_id,
                    "chat_secret_saved",
                    key=key,
                    file=path.name,
                    restart=restart,
                    note=note,
                ),
                delete_source=True,
            )
        if action == "delete":
            if len(tokens) < 2:
                return self._error(chat_id, "chat_secret_delete_usage")
            key = tokens[1].strip()
            try:
                removed = delete_secret(self.settings.home, key)
            except (SecretError, OSError) as exc:
                return self._error(chat_id, "chat_error", error=exc)
            if removed:
                return Reply(
                    self._text(
                        chat_id,
                        "chat_secret_deleted",
                        key=key,
                        file=SECRETS_FILENAME,
                    )
                )
            return Reply(
                self._text(chat_id, "chat_secret_missing", key=key)
            )
        return self._error(chat_id, "chat_secret_usage")

    # ----------------------------------------------------------- daemon

    def _pause(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        set_paused(self.settings.home, True)
        return Reply(self._text(chat_id, "chat_pause"))

    def _resume(self, chat_id: int, _rest: str, _actor: str) -> Reply:
        set_paused(self.settings.home, False)
        return Reply(self._text(chat_id, "chat_resume"))

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
                    failed=reply.failed,
                )
            return reply

        action = result.action
        args = dict(result.args or {})
        if action == "plan":
            goal = str(args.get("goal") or "").strip()
            if not goal:
                return self._error(chat_id, "chat_action_no_goal")
            release_class = str(
                args.get("release_class") or "minor"
            ).strip().lower()
            if release_class not in {"patch", "minor", "major"}:
                release_class = "minor"
            return combine(
                self._plan(
                    chat_id,
                    goal,
                    actor,
                    release_class=release_class,
                    product_intent=str(
                        args.get("product_intent") or ""
                    ).strip(),
                    user_experience=str(
                        args.get("user_experience") or ""
                    ).strip(),
                )
            )
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
                    return self._error(
                        chat_id, "chat_action_no_decision"
                    )
                task_id = str(task["id"])
            notes = str(args.get("notes") or "").strip()
            rest = f"{action} {task_id} {notes}".strip()
            return combine(self._task(chat_id, rest, actor))
        if action == "review":
            project = self._selected(chat_id)
            if isinstance(project, Reply):
                return project
            layout = ProjectLayout.detect(project["workspace"])
            task_id = str(args.get("task_id") or "").strip()
            if not task_id:
                task = next(
                    (
                        item
                        for item in reversed(list_tasks(layout))
                        if item.get("status") == "review"
                    ),
                    None,
                )
                if task is None:
                    return self._error(
                        chat_id, "chat_action_no_review_task"
                    )
                task_id = str(task["id"])
            return combine(
                self._task(chat_id, f"review {task_id}", actor)
            )
        if action == "adopt":
            url = str(args.get("url") or "").strip()
            brief = str(args.get("brief") or "").strip()
            if not url:
                return self._error(chat_id, "chat_action_no_url")
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
                return self._error(chat_id, "chat_action_no_repo_url")
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
                return self._error(chat_id, "chat_action_no_repo_id")
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
        if action == "release":
            version = str(args.get("version") or "").strip()
            if not version:
                return self._error(chat_id, "chat_release_usage")
            parts = [f"--version {shlex.quote(version)}"]
            repo_id = str(
                args.get("repo") or args.get("repo_id") or ""
            ).strip()
            if repo_id:
                parts.append(f"--repo {shlex.quote(repo_id)}")
            notes = str(args.get("notes") or "").strip()
            if notes:
                parts.append(f"--notes {shlex.quote(notes)}")
            return combine(
                self._release(chat_id, " ".join(parts), actor)
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
        return self._error(chat_id, "chat_action_not_allowed")

    # ------------------------------------------------------------- agent

    def _message(self, chat_id: int, text: str, actor: str) -> Reply:
        if looks_like_secret(text):
            return Reply(
                self._text(chat_id, "chat_secret_looks"),
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
                    lang=self._language(chat_id),
                )
            )
        if self.agent is None:
            return Reply(
                self._text(chat_id, "chat_agent_missing")
            )
        try:
            result = self.agent.handle(
                project, text, actor, session=str(chat_id)
            )
        except Exception as exc:  # noqa: BLE001 - answer instead of crashing
            return self._error(
                chat_id, "chat_agent_error", error=exc
            )
        if result.kind in {"action", "actions"} and result.actions:
            replies: list[Reply] = []
            narration = False
            error_reply: Reply | None = None
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
                if action in {"status", "tasks"}:
                    narration = True
                if reply.failed:
                    error_reply = reply
                    break
                replies.append(reply)
            if error_reply is not None:
                done = "\n\n".join(
                    reply.text for reply in replies if reply.text
                )
                error_text = error_reply.text.strip()
                error_word = self._text(chat_id, "chat_error_word")
                if not error_text.lower().startswith(error_word):
                    error_text = self._text(
                        chat_id,
                        "chat_error_prefix",
                        text=error_text,
                    )
                if done:
                    error_text += self._text(
                        chat_id, "chat_earlier", results=done
                    )
                return Reply(error_text, failed=True)
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

    def _github_hint(self, chat_id: int, url: str, message: str) -> str:
        if "github.com" not in url:
            return ""
        lowered = message.lower()
        if any(
            marker in lowered
            for marker in (
                "nodename nor servname",
                "name or service not known",
                "errno 8",
                "not reachable by dns",
                "temporary failure in name resolution",
            )
        ):
            return "\n\n" + self._text(chat_id, "chat_github_dns")
        if "resource not accessible by integration" in lowered:
            return "\n\n" + self._text(
                chat_id, "chat_github_app_permission"
            )
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
        return "\n\n" + self._text(chat_id, "chat_github_auth")

    def _selected(self, chat_id: int) -> dict[str, Any] | Reply:
        project_id = self.ledger.get_session(chat_id)
        if project_id is None:
            return self._error(chat_id, "chat_no_project_selected")
        project = self.ledger.get_project(project_id)
        if project is None:
            self.ledger.clear_session(chat_id)
            return self._error(chat_id, "chat_project_gone")
        return project

    def _resolve(self, chat_id: int, token: str) -> dict[str, Any] | Reply:
        try:
            return resolve_project(self.ledger, token)
        except ProjectError as exc:
            return self._error(chat_id, "chat_error", error=exc)

    def _target(
        self, chat_id: int, rest: str
    ) -> tuple[dict[str, Any] | Reply, str]:
        """Resolve an explicit leading project id, or the selected project."""

        rest = rest.strip()
        if not rest:
            return self._selected(chat_id), ""
        token, _, remainder = rest.partition(" ")
        project = self._resolve(chat_id, token)
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
        project = self._resolve(chat_id, token)
        return project, remainder.strip()

    def _approval_text(
        self,
        chat_id: int,
        record: dict[str, Any],
        production: bool,
    ) -> str:
        scope = "production" if production else "staging"
        decision = (
            "recorded"
            if record["decision"] == "approved"
            else "rejected"
        )
        release = (
            self._text(
                chat_id,
                "chat_approval_release",
                sha=record["release_sha"],
            )
            if record.get("release_sha")
            else ""
        )
        text = self._text(
            chat_id, f"chat_approval_{scope}_{decision}"
        )
        text += self._text(
            chat_id,
            "chat_approval_details",
            project=record["project_id"],
            generation=record["generation"],
            release=release,
            actor=record["actor"],
        )
        if record["decision"] != "approved":
            text += self._text(chat_id, "chat_approval_gate")
        elif production:
            text += self._text(
                chat_id, "chat_approval_production_manual"
            )
        else:
            text += self._text(chat_id, "chat_approval_next_cycle")
        return text

    def _production_prompt(
        self, chat_id: int, project: dict[str, Any]
    ) -> str:
        generation = self.ledger.current_generation(project["id"])
        return self._text(
            chat_id,
            "chat_production_prompt",
            name=project["name"],
            project=project["id"],
            generation=generation,
        )
