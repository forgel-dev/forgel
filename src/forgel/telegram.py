"""Telegram chat gateway.

A dependency-free long-polling adapter over the Bot API. The gateway is a thin
edge: every command calls the same core functions as the CLI, and the
deterministic orchestrator stays the only thing that changes a project.

Access is closed by default. The bot refuses to start without
``TELEGRAM_ALLOWED_CHAT_IDS`` and ignores updates from every other chat.

The gateway is also the daemon host: between polls it runs pending work, so a
single ``forgel telegram`` process is a complete self-hosted control plane.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from . import daemon_config
from .agent import ProjectAgent
from .artifacts import read_json
from .chat import HELP, CommandRouter, Reply  # noqa: F401 - HELP is re-exported
from .config import Settings
from .control import is_paused
from .daemon import project_state, run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .secrets import get_secret
from .tasks import latest_task

MESSAGE_LIMIT = 4000


class TelegramError(RuntimeError):
    """The Bot API call failed."""


class TelegramConfigError(RuntimeError):
    """The gateway is not configured."""


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    allowed_chat_ids: frozenset[int]
    api_base: str = "https://api.telegram.org"
    poll_timeout: int = 25

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
    ) -> TelegramConfig:
        env = environ if environ is not None else os.environ
        token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token and home is not None:
            token = get_secret(home, "telegram.bot_token", env)
        if not token:
            raise TelegramConfigError(
                "TELEGRAM_BOT_TOKEN is required (env or /secret)"
            )
        raw_ids = env.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
        if not raw_ids:
            raise TelegramConfigError(
                "TELEGRAM_ALLOWED_CHAT_IDS is required; the gateway is closed "
                "by default"
            )
        chat_ids: set[int] = set()
        for item in raw_ids.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                chat_ids.add(int(item))
            except ValueError as exc:
                raise TelegramConfigError(
                    f"TELEGRAM_ALLOWED_CHAT_IDS contains a non-numeric id: {item!r}"
                ) from exc
        if not chat_ids:
            raise TelegramConfigError("TELEGRAM_ALLOWED_CHAT_IDS is empty")

        api_base = env.get(
            "TELEGRAM_API_BASE", "https://api.telegram.org"
        ).strip().rstrip("/")
        raw_timeout = env.get("TELEGRAM_POLL_TIMEOUT", "").strip()
        if raw_timeout:
            try:
                poll_timeout = int(raw_timeout)
            except ValueError as exc:
                raise TelegramConfigError(
                    "TELEGRAM_POLL_TIMEOUT must be an integer"
                ) from exc
        elif home is not None:
            try:
                poll_timeout = int(
                    daemon_config.get_value(home, "telegram.poll_timeout")
                )
            except daemon_config.DaemonConfigError as exc:
                raise TelegramConfigError(
                    f"invalid daemon configuration: {exc}"
                ) from exc
        else:
            poll_timeout = 25
        poll_timeout = max(0, min(poll_timeout, 50))
        return cls(
            token=token,
            allowed_chat_ids=frozenset(chat_ids),
            api_base=api_base,
            poll_timeout=poll_timeout,
        )


class TelegramAPI:
    """Minimal Bot API client built on ``urllib``."""

    def __init__(
        self,
        config: TelegramConfig,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def call(
        self,
        method: str,
        payload: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = f"{self.config.api_base}/bot{self.config.token}/{method}"
        data = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self._opener(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise TelegramError(self._redact(f"{method}: {exc}")) from exc
        except json.JSONDecodeError as exc:
            raise TelegramError(f"{method}: invalid JSON response") from exc
        if not isinstance(body, dict):
            raise TelegramError(f"{method}: unexpected response")
        if not body.get("ok"):
            raise TelegramError(
                self._redact(
                    f"{method}: {body.get('description', 'unknown error')}"
                )
            )
        return body.get("result")

    def _redact(self, message: str) -> str:
        if self.config.token:
            return message.replace(self.config.token, "***")
        return message

    def get_updates(
        self, offset: int | None, timeout: int
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self.call(method="getUpdates", payload=payload, timeout=timeout + 15)
        return list(result or [])

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        chunks = split_message(text)
        sent: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if reply_markup is not None and index == len(chunks) - 1:
                payload["reply_markup"] = reply_markup
            sent.append(self.call(method="sendMessage", payload=payload))
        return sent

    def edit_message_text(self, chat_id: int, message_id: int, text: str) -> Any:
        return self.call(
            method="editMessageText",
            payload={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text[:MESSAGE_LIMIT],
                "disable_web_page_preview": True,
            },
        )

    def answer_callback_query(self, callback_id: str, text: str = "") -> Any:
        payload: dict[str, Any] = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text[:200]
        return self.call(method="answerCallbackQuery", payload=payload)

    def delete_message(self, chat_id: int, message_id: int) -> Any:
        return self.call(
            method="deleteMessage",
            payload={"chat_id": chat_id, "message_id": message_id},
        )

    def send_chat_action(self, chat_id: int, action: str = "typing") -> Any:
        return self.call(
            method="sendChatAction",
            payload={"chat_id": chat_id, "action": action},
        )


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Split text into Bot API sized chunks without cutting lines if possible."""

    if len(text) <= limit:
        return [text] if text else [""]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


class TelegramGateway:
    """Long-polling loop that also hosts the daemon."""

    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        config: TelegramConfig,
        api: TelegramAPI | None = None,
        poll_timeout: int | None = None,
        daemon_enabled: bool = True,
        agent: ProjectAgent | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.config = config
        self.api = api or TelegramAPI(config)
        self.poll_timeout = (
            poll_timeout if poll_timeout is not None else config.poll_timeout
        )
        self.daemon_enabled = daemon_enabled
        self.log = log
        self.router = CommandRouter(
            settings,
            ledger,
            daemon_enabled=daemon_enabled,
            agent=agent,
        )
        self.offset: int | None = None
        self._states: dict[str, str] = {
            project["id"]: project_state(ledger, project)
            for project in ledger.list_projects()
        }

    # -------------------------------------------------------------- updates

    def process(self, update: dict[str, Any]) -> bool:
        message = update.get("message")
        if message is not None:
            return self._process_message(message)
        callback = update.get("callback_query")
        if callback is not None:
            return self._process_callback(callback)
        return False

    def _process_message(self, message: dict[str, Any]) -> bool:
        chat_id = (message.get("chat") or {}).get("id")
        if not isinstance(chat_id, int):
            return False
        if chat_id not in self.config.allowed_chat_ids:
            self.log(f"[telegram] ignored message from chat {chat_id}")
            return False
        text = message.get("text")
        if not isinstance(text, str):
            return False
        actor = actor_label(message.get("from") or {})
        if (
            not text.startswith("/")
            or text.startswith("/adopt")
            or text.startswith("/repo add")
            or text.startswith("/github publish")
            or text.startswith("/github merge")
        ):
            try:
                self.api.send_chat_action(chat_id, "typing")
            except TelegramError:
                pass
        reply = self.router.handle(chat_id, text, actor)
        message_id = message.get("message_id")
        if reply.delete_source and isinstance(message_id, int):
            try:
                self.api.delete_message(chat_id, message_id)
            except TelegramError as exc:
                self.log(f"[telegram] deleteMessage failed: {exc}")
                reply = Reply(
                    reply.text
                    + "\n\nWarning: the source message could not be deleted; "
                    "delete it manually."
                )
        self._send(chat_id, reply)
        return True

    def _process_callback(self, callback: dict[str, Any]) -> bool:
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        callback_id = str(callback.get("id", ""))
        if not isinstance(chat_id, int):
            return False
        if chat_id not in self.config.allowed_chat_ids:
            self.log(f"[telegram] ignored callback from chat {chat_id}")
            return False
        actor = actor_label(callback.get("from") or {})
        reply = self.router.handle_callback(
            chat_id, str(callback.get("data", "")), actor
        )
        try:
            self.api.answer_callback_query(callback_id, reply.callback_text)
        except TelegramError as exc:
            self.log(f"[telegram] answerCallbackQuery failed: {exc}")
        message_id = message.get("message_id")
        if isinstance(message_id, int):
            try:
                self.api.edit_message_text(chat_id, message_id, reply.text)
            except TelegramError:
                self._send(chat_id, Reply(reply.text))
        else:
            self._send(chat_id, Reply(reply.text))
        return True

    # ----------------------------------------------------------------- loop

    def run(
        self,
        interval: float = 2.0,
        max_cycles: int | None = None,
    ) -> None:
        self._announce_online()
        if self.daemon_enabled:
            self._daemon_cycle()
        next_cycle = time.monotonic() + interval
        cycles = 0
        while True:
            try:
                updates = self.api.get_updates(self.offset, self.poll_timeout)
            except TelegramError as exc:
                self.log(f"[telegram] polling failed: {exc}")
                time.sleep(min(max(interval, 1.0), 5.0))
                cycles += 1
                if max_cycles is not None and cycles >= max_cycles:
                    return
                continue
            handled = False
            for update in updates:
                self.offset = int(update.get("update_id", 0)) + 1
                try:
                    handled = self.process(update) or handled
                except Exception as exc:  # noqa: BLE001 - keep polling
                    self.log(f"[telegram] update failed: {exc}")
            if self.daemon_enabled and (
                handled or time.monotonic() >= next_cycle
            ):
                self._daemon_cycle()
                next_cycle = time.monotonic() + interval
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                return

    def _daemon_cycle(self) -> None:
        if is_paused(self.settings.home):
            self.log("[telegram] daemon paused")
        else:
            try:
                run_once(self.settings, self.ledger, self.log)
            except Exception as exc:  # noqa: BLE001 - the gateway must stay up
                self.log(f"[telegram] daemon cycle failed: {exc}")
        self._notify_transitions()

    # --------------------------------------------------------- notifications

    def _announce_online(self) -> None:
        if not self.daemon_enabled:
            mode = "commands only"
        elif is_paused(self.settings.home):
            mode = "paused"
        else:
            mode = "running"
        agent = "configured" if self.router.agent is not None else "disabled"
        text = (
            f"Forgel gateway is online. Daemon: {mode}. "
            f"Agent: {agent}. /help"
        )
        for chat_id in sorted(self.config.allowed_chat_ids):
            self._send(chat_id, Reply(text))

    def _notify_transitions(self) -> None:
        current = {
            project["id"]: project_state(self.ledger, project)
            for project in self.ledger.list_projects()
        }
        for project_id, state in current.items():
            if self._states.get(project_id) == state:
                continue
            project = self.ledger.get_project(project_id)
            if project is None:
                continue
            message = self._transition_message(project, state)
            if message:
                for chat_id in sorted(self.config.allowed_chat_ids):
                    self._send(chat_id, Reply(message))
        self._states = current

    def _transition_message(
        self, project: dict[str, Any], state: str
    ) -> str | None:
        project_id = project["id"]
        if state == "awaiting staging approval":
            return (
                f"{project['name']} ({project_id}) is ready for staging review.\n"
                f"Approve: /approve {project_id} staging\n"
                f"Details: /status {project_id}"
            )
        if state == "staging rejected":
            return (
                f"Staging was rejected for {project_id}.\n"
                "Change the scope with /sync, then approve the next generation."
            )
        if state == "reconciliation pending":
            return (
                f"External changes detected in {project_id}.\n"
                f"Review: /sync {project_id}\n"
                f"Decide: /reconcile {project_id} accept|fix|rollback|ignore"
            )
        if state.startswith("failed at "):
            stage = state[len("failed at ") :]
            return (
                f"{project_id} stopped at stage {stage}.\n"
                f"Check /status {project_id} and the daemon log."
            )
        if state == "task pending":
            return (
                f"A task is queued for {project['name']} ({project_id}). "
                "The daemon will start it in this cycle."
            )
        if state == "task done":
            task = latest_task(ProjectLayout.detect(project["workspace"]))
            title = task["title"] if task else "task"
            return (
                f"Agent finished {title} for {project_id}.\n"
                f"Details: /status {project_id}"
            )
        if state == "task failed":
            task = latest_task(ProjectLayout.detect(project["workspace"]))
            reason = ""
            if task:
                reason = str(task.get("result", {}).get("summary", ""))
            return (
                f"Agent task failed for {project_id}."
                + (f"\n{reason}" if reason else "")
                + f"\nDetails: /status {project_id}"
            )
        if state == "done":
            return self._done_message(project)
        return None

    def _done_message(self, project: dict[str, Any]) -> str:
        project_id = project["id"]
        layout = ProjectLayout.detect(project["workspace"])
        staging_path = layout.artifact("staging.json")
        url = ""
        if staging_path.exists():
            try:
                url = str(read_json(staging_path).get("url", ""))
            except (OSError, json.JSONDecodeError):
                url = ""
        lines = [f"{project['name']} ({project_id}) is done."]
        if url:
            lines.append(f"Staging: {url}")
        lines.append(f"Status: /status {project_id}")
        return "\n".join(lines)

    def _send(self, chat_id: int, reply: Reply) -> None:
        try:
            self.api.send_message(chat_id, reply.text, reply.reply_markup)
        except TelegramError as exc:
            self.log(f"[telegram] sendMessage failed: {exc}")


def actor_label(user: Mapping[str, Any]) -> str:
    username = user.get("username")
    if username:
        return f"@{username}"
    name = user.get("first_name") or "user"
    user_id = user.get("id", "?")
    return f"{name} ({user_id})"


def run_bot(
    settings: Settings,
    ledger: Ledger,
    config: TelegramConfig,
    api: TelegramAPI | None = None,
    daemon: bool = True,
    interval: float | None = None,
    poll_timeout: int | None = None,
    max_cycles: int | None = None,
    agent: ProjectAgent | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """Run the gateway until interrupted."""

    if agent is None:
        client = build_model_client(settings.home, log=log)
        if client is None:
            log("[telegram] model not configured; free text is disabled")
        else:
            agent = ProjectAgent(settings, ledger, client)
    if interval is None:
        interval = float(daemon_config.get_value(settings.home, "daemon.interval"))
    gateway = TelegramGateway(
        settings,
        ledger,
        config,
        api=api,
        poll_timeout=poll_timeout,
        daemon_enabled=daemon,
        agent=agent,
        log=log,
    )
    gateway.run(interval=interval, max_cycles=max_cycles)
