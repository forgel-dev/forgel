"""Local console channel.

One client, no separate utilities: start `forgel` in a repository, `/adopt`
it, describe the milestone, and watch the daemon work. The console and the
Telegram gateway share one command router, so every command behaves the same.

After a command the console drains runnable work until it reaches a real stop:
a task awaiting acceptance, a plan that is stalled or done, or a retry that is
scheduled for later. A scheduled retry is waited out (Ctrl-C returns to the
prompt); an idle home returns immediately.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Callable

try:  # line editing and history for the prompt; no dependency
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - platform without readline
    readline = None  # type: ignore[assignment]

from .agent import ProjectAgent, append_history, load_history
from .chat import CommandRouter
from .config import Settings
from .control import is_paused
from .daemon import next_retry_wait, run_once
from .language import detect as detect_language
from .layout import ProjectLayout
from .ledger import Ledger
from .model import build_model_client
from .planner import plan_status
from .projects import ProjectError, resolve_project
from .tasks import latest_task, list_tasks, retry_moment

PROMPT = "forgel> "
QUIT = {"/quit", "/exit", "quit", "exit", "bye"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "done": "done",
        "failed": "failed",
        "review": "needs your decision",
        "pending": "queued",
        "running": "running",
        "blocked": "blocked",
        "cancelled": "cancelled",
        "plan_done": "done",
        "plan_review": "awaiting a decision",
        "plan_stalled": "stalled",
        "plan_running": "running",
        "plan_none": "none",
        "milestone": "Milestone {plan}: {status} ({counts}).",
        "count_done": "done",
        "count_failed": "failed",
        "count_blocked": "blocked",
        "count_review": "in review",
        "count_pending": "queued",
        "explain_question": "The user's last message: {text}\n\nExplain the result in plain language, in the language of that message. Start with the concrete thing that did not work and why, not with the task status or plan counts. Synthesize the whole context: what happened and why, what is now blocked or waiting, what the runtime will do next on its own, and what — if anything — the user must decide. If the task is not complete, name the real cause from the evidence, not a generic \"process error\". Do not restate the status dump, do not list raw fields, and do not invent facts. If nothing is needed from the user, say so directly.",
        "explain_state_question": "Explain the current state in plain language, in the language of the user's message. Synthesize the plan and the latest result: what happened, what is blocked or waiting, what the runtime will do next on its own, and what — if anything — the user must decide. Do not restate the status dump or invent facts.",
        "explain_missing_model": "No model is configured, so this result cannot be explained in plain language. Task {task}: {status}. Reports: {reports}.",
        "explain_failed": "I couldn't explain the result just now. The task is {status}. Reports: {reports}.",
        "waiting": "Waiting for a scheduled retry at {moment} (about {minutes} min). Ctrl-C returns to the prompt.",
        "stopped": "Stopped waiting; the retry stays scheduled.",
        "daemon_error": "daemon error: {error}",
    },
    "ru": {
        "done": "готово",
        "failed": "провал",
        "review": "нужно решение",
        "pending": "в очереди",
        "running": "в работе",
        "blocked": "заблокировано",
        "cancelled": "отменено",
        "plan_done": "завершён",
        "plan_review": "ждёт решения",
        "plan_stalled": "застрял",
        "plan_running": "в работе",
        "plan_none": "нет",
        "milestone": "План {plan}: {status} ({counts}).",
        "count_done": "готово",
        "count_failed": "провал",
        "count_blocked": "заблокировано",
        "count_review": "на проверке",
        "count_pending": "в очереди",
        "explain_question": "Пользователь только что написал: «{text}».\n\nОбъясни результат на языке этого сообщения. Начни с конкретного места, которое не сработало, и почему, а не со статуса задачи или счётчиков плана. Собери весь контекст: что произошло и почему, что сейчас заблокировано или ждёт, что система сделает дальше сама и что, если вообще что-то, должен решить пользователь. Если задача не выполнена, назови реальную причину по фактам, а не общее «процесс завершился ошибкой». Не пересказывай статус и не перечисляй поля; не выдумывай факты. Если от пользователя ничего не требуется, скажи это прямо.",
        "explain_state_question": "Объясни текущее состояние на языке сообщения пользователя. Собери картину из плана и последнего результата: что произошло, что заблокировано или ждёт, что система сделает дальше сама и что, если что-то, должен решить пользователь. Не пересказывай статус и не выдумывай факты.",
        "explain_missing_model": "Модель не настроена, поэтому объяснить результат человеческим языком нельзя. Задача {task}: {status}. Отчёты: {reports}.",
        "explain_failed": "Не удалось объяснить результат. Статус задачи: {status}. Отчёты: {reports}.",
        "waiting": "Ждём запланированный повтор в {moment} (около {minutes} мин). Ctrl-C вернёт к приглашению.",
        "stopped": "Ожидание остановлено; повтор остаётся запланированным.",
        "daemon_error": "ошибка демона: {error}",
    },
}


def _t(lang: str, key: str, **values: object) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    return template.format(**values)


def _status_name(lang: str, status: str) -> str:
    key = str(status or "")
    if key in STRINGS["en"]:
        return _t(lang, key)
    return key


def _plan_line(summary: dict, lang: str) -> str:
    counts = summary.get("counts") or {}
    parts = [
        _t(lang, f"count_{key}") + f" {counts[key]}"
        for key in ("done", "failed", "blocked", "review", "pending")
        if counts.get(key)
    ]
    return _t(
        lang,
        "milestone",
        plan=summary.get("plan_id") or "",
        status=_t(lang, f"plan_{summary.get('status') or 'none'}"),
        counts=", ".join(parts) or _t(lang, "plan_none"),
    )


def _attention_task(layout: ProjectLayout) -> dict | None:
    tasks = list_tasks(layout)
    for status in ("review", "failed", "pending", "blocked", "running"):
        items = [
            task for task in tasks if task.get("status") == status
        ]
        if items:
            return items[-1]
    return None


def _cap_text(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _tail_text(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return "…" + text[-limit:].lstrip()


def _recent_conversation(
    layout: ProjectLayout, session: str = "", limit: int = 6
) -> list[dict]:
    rows = load_history(layout, limit=limit * 2, session=session)
    items = [
        {
            "role": row.get("role"),
            "text": _cap_text(row.get("text"), 500),
        }
        for row in rows
        if row.get("role") in {"user", "assistant"}
        and str(row.get("text") or "").strip()
    ]
    return items[-limit:]


def _report_text(
    layout: ProjectLayout,
    ref: object,
    limit: int = 5000,
    tail: bool = False,
) -> str:
    text_ref = str(ref or "").strip()
    if not text_ref:
        return ""
    try:
        text = layout.artifact(text_ref).read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return ("…" + text[-limit:]) if tail else (text[:limit] + "…")


def _report_actions(
    layout: ProjectLayout, ref: object, limit: int = 30
) -> list[str]:
    text = _report_text(layout, ref, limit=200_000)
    marker = "## Actions"
    if marker not in text:
        return []
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    actions = [
        _cap_text(line.strip()[2:], 300)
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]
    return actions[-limit:]


def _task_observation(task: dict, layout: ProjectLayout) -> dict:
    result = dict(task.get("result") or {})
    qa = dict(result.get("qa") or {})
    review = dict(result.get("review") or {})
    failed_requirements = [
        {
            "requirement": item.get("requirement"),
            "verdict": item.get("verdict"),
            "note": _cap_text(item.get("note"), 900),
        }
        for item in (review.get("requirements") or [])
        if str(item.get("verdict") or "") not in {"pass", ""}
    ]
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "plan_goal": task.get("plan_goal"),
        "status": task.get("status"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "requirements": list(task.get("requirements") or []),
        "acceptance": list(task.get("acceptance") or []),
        "constraints": list(task.get("constraints") or []),
        "checks": list(task.get("checks") or []),
        "summary": _cap_text(result.get("summary"), 2600),
        "failure": result.get("failure") or {},
        "last_failure": result.get("last_failure") or {},
        "last_actions": _report_actions(layout, result.get("report")),
        "last_commands": [
            {
                "command": item.get("command"),
                "exit_code": item.get("exit_code"),
                "final_test": bool(item.get("final_test")),
            }
            for item in (result.get("commands") or [])
        ][-12:],
        "final_test_output": _tail_text(
            result.get("test_output"), 3000
        ),
        "qa": {
            "status": qa.get("status"),
            "review_required": qa.get("review_required"),
            "commands": [
                {
                    "command": item.get("command"),
                    "exit_code": item.get("exit_code"),
                }
                for item in (qa.get("commands") or [])
            ][:12],
            "checks": [
                {
                    "criterion": item.get("criterion"),
                    "exit_code": item.get("exit_code"),
                    "verdict": item.get("verdict"),
                }
                for item in (qa.get("checks") or [])
            ][:12],
            "report": _report_text(
                layout, qa.get("report"), limit=8000, tail=True
            ),
        },
        "review": {
            "status": review.get("status"),
            "summary": _cap_text(review.get("summary"), 4000),
            "blocking": [
                _cap_text(item, 900)
                for item in (review.get("blocking") or [])
            ][:10],
            "failed_requirements": failed_requirements[:10],
        },
        "acceptance": result.get("acceptance") or {},
        "files_changed": list(result.get("files_changed") or [])[:40],
        "context": result.get("context") or {},
        "reports": [
            str(ref)
            for ref in (
                result.get("report"),
                qa.get("report"),
                review.get("report"),
            )
            if str(ref or "").strip()
        ],
    }


def _plan_observation(layout: ProjectLayout) -> dict:
    summary = plan_status(layout)
    return {
        "id": summary.get("plan_id"),
        "goal": summary.get("goal"),
        "status": summary.get("status"),
        "counts": summary.get("counts"),
        "tasks": [
            {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "blocked_by": task.get("blocked_by"),
            }
            for task in (summary.get("tasks") or [])
        ],
    }


def _changed_tasks(
    layout: ProjectLayout, before: dict[str, str]
) -> list[dict]:
    changed: list[dict] = []
    for item in list_tasks(layout):
        task_id = str(item["id"])
        status = str(item.get("status", ""))
        if before.get(task_id) == status:
            continue
        result = dict(item.get("result") or {})
        if status == "pending" and not (
            result.get("last_failure") or result.get("retry_after")
        ):
            continue
        if status not in {
            "done",
            "failed",
            "review",
            "pending",
            "blocked",
            "cancelled",
            "running",
        }:
            continue
        changed.append(item)
    return changed


def _conversation_observation(
    layout: ProjectLayout, session: str = ""
) -> list[dict]:
    return _recent_conversation(layout, session=session)


def _explain_outcomes(
    agent: ProjectAgent | None,
    project: dict | None,
    layout: ProjectLayout,
    before: dict[str, str],
    lang: str,
    user_text: str,
    session: str = "",
) -> str:
    """Ask the model for a plain-language account of what just happened."""

    changed = _changed_tasks(layout, before)
    if not changed:
        return ""
    last = changed[-1]
    reports = _task_observation(last, layout)["reports"]
    if agent is None or project is None:
        return _t(
            lang,
            "explain_missing_model",
            task=last.get("id") or "",
            status=_status_name(lang, str(last.get("status") or "")),
            reports=", ".join(reports) or "—",
        )
    observation = json.dumps(
        {
            "project": {
                "name": project.get("name"),
                "brief": _cap_text(project.get("brief"), 800),
            },
            "plan": _plan_observation(layout),
            "changed_tasks": [
                _task_observation(task, layout) for task in changed
            ],
            "recent_conversation": _conversation_observation(
                layout, session
            ),
        },
        ensure_ascii=False,
        indent=2,
    )
    question = _t(
        lang, "explain_question", text=user_text or "(no message)"
    )
    fallback = _t(
        lang,
        "explain_failed",
        status=_status_name(lang, str(last.get("status") or "")),
        reports=", ".join(reports) or "—",
    )
    try:
        answer = agent.explain(
            project, question, observation, fallback=fallback
        )
    except Exception:  # noqa: BLE001 - the console must stay up
        answer = fallback
    answer = str(answer or "").strip()
    if answer:
        return answer
    return fallback


def _report_state(
    ledger: Ledger,
    output: Callable[[str], None],
    agent: ProjectAgent | None = None,
    lang: str = "en",
    session: str = "",
) -> None:
    project_id = ledger.get_session(0)
    if not project_id:
        return
    project = ledger.get_project(project_id)
    if project is None:
        return
    layout = ProjectLayout.detect(project["workspace"])
    summary = plan_status(layout)
    task = _attention_task(layout)
    if agent is not None and task is not None:
        observation = json.dumps(
            {
                "project": {
                    "name": project.get("name"),
                    "brief": _cap_text(project.get("brief"), 800),
                },
                "plan": _plan_observation(layout),
                "latest_task": _task_observation(task, layout),
                "recent_conversation": _conversation_observation(
                    layout, session
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            answer = agent.explain(
                project,
                _t(lang, "explain_state_question"),
                observation,
                fallback=_t(
                    lang,
                    "explain_failed",
                    status=_status_name(
                        lang, str(task.get("status") or "")
                    ),
                    reports=", ".join(
                        _task_observation(task, layout)["reports"]
                    )
                    or "—",
                ),
            ).strip()
        except Exception:  # noqa: BLE001 - the console must stay up
            answer = ""
        if answer:
            output(answer)
            return
    if summary["status"] not in {"none", "running"}:
        output(_plan_line(summary, lang))
    if task is None:
        return
    reports = _task_observation(task, layout)["reports"]
    output(
        _t(
            lang,
            "explain_missing_model",
            task=task.get("id") or "",
            status=_status_name(lang, str(task.get("status") or "")),
            reports=", ".join(reports) or "—",
        )
    )


def _drain(
    settings: Settings,
    ledger: Ledger,
    output: Callable[[str], None],
    sleep_fn: Callable[[float], None] = time.sleep,
    lang: str = "en",
    agent: ProjectAgent | None = None,
    project: dict | None = None,
    session: str = "",
) -> None:
    """Run until no immediately runnable work remains.

    A scheduled retry is waited out; Ctrl-C stops the wait and returns to the
    prompt without losing the task.
    """

    while True:
        try:
            processed = run_once(settings, ledger, log=output)
        except Exception as exc:  # noqa: BLE001 - the console must stay up
            output(_t(lang, "daemon_error", error=exc))
            return
        if processed:
            continue
        wait = next_retry_wait(ledger)
        if wait is None:
            # The caller prints the outcome of tasks whose status changed.
            return
        moment = None
        for project in ledger.list_projects():
            layout = ProjectLayout.detect(project["workspace"])
            task = latest_task(layout)
            if task is not None:
                moment = retry_moment(task) or moment
        when = (
            moment.strftime("%H:%M UTC") if moment else ""
        )
        output(
            _t(
                lang,
                "waiting",
                moment=when,
                minutes=f"{wait / 60:.0f}",
            )
        )
        try:
            sleep_fn(wait)
        except KeyboardInterrupt:
            output(_t(lang, "stopped"))
            _report_state(
                ledger, output, agent, lang, session
            )
            return


def _flush_pending_input() -> None:
    """Drop keys typed while the daemon was working, before the prompt."""

    try:
        import termios
    except ImportError:  # pragma: no cover - non-POSIX
        return
    try:
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (OSError, ValueError):
        return


COMMANDS = (
    "/help",
    "/adopt",
    "/new",
    "/use",
    "/projects",
    "/status",
    "/plan",
    "/tasks",
    "/task",
    "/repo",
    "/secret",
    "/config",
    "/peak",
    "/pause",
    "/resume",
    "/github",
    "/deploy",
    "/quit",
    "/exit",
)


def _completion_options(buffer: str, ledger: Ledger) -> list[str]:
    stripped = buffer.lstrip()
    if stripped.startswith("/use "):
        return [str(item["id"]) for item in ledger.list_projects()]
    if stripped.startswith("/"):
        return list(COMMANDS)
    return []


def _setup_readline(settings: Settings, ledger: Ledger) -> None:
    if readline is None:
        return
    history = settings.home / "console_history"
    try:
        settings.home.mkdir(parents=True, exist_ok=True)
        readline.read_history_file(history)
    except OSError:
        pass
    readline.set_history_length(500)

    def completer(text: str, state: int) -> str | None:
        options = _completion_options(
            readline.get_line_buffer(), ledger
        )
        matches = [item for item in options if item.startswith(text)]
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")


def _save_history(settings: Settings) -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(settings.home / "console_history")
    except OSError:
        return


def _prompt_text(ledger: Ledger, chat_id: int) -> str:
    project_id = ledger.get_session(chat_id)
    if project_id:
        project = ledger.get_project(project_id)
        if project is not None:
            return f"forgel[{project['name']}]> "
    return PROMPT


def _read_input(
    input_fn: Callable[[str], str], prompt: str, interactive: bool
) -> str:
    line = input_fn(prompt)
    if not interactive:
        return line
    parts: list[str] = []
    while line.rstrip().endswith("\\"):
        parts.append(line.rstrip()[:-1])
        line = input_fn("... ")
    parts.append(line)
    return "\n".join(parts)


class _Spinner:
    """A one-line activity indicator while the model is working."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "_Spinner":
        if not self.enabled:
            return self
        self._thread = threading.Thread(
            target=self._spin, daemon=True
        )
        self._thread.start()
        return self

    def _spin(self) -> None:
        frames = "|/-\\"
        index = 0
        while not self._stop.wait(0.15):
            sys.stdout.write(
                "\r\033[2m" + frames[index % len(frames)] + " working…\033[0m"
            )
            sys.stdout.flush()
            index += 1

    def __exit__(self, *exc_info: object) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


def _task_snapshot(layout: ProjectLayout) -> dict[str, str]:
    return {
        str(item["id"]): str(item.get("status", ""))
        for item in list_tasks(layout)
    }


def run_console(
    settings: Settings,
    ledger: Ledger,
    project_id: str = "",
    daemon: bool = True,
    actor: str = "local",
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    agent: ProjectAgent | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Run the local console until EOF or ``/quit``."""

    chat_id = 0
    if project_id:
        try:
            project = resolve_project(ledger, project_id)
        except ProjectError as exc:
            output(f"error: {exc}")
            return
        ledger.set_session(chat_id, str(project["id"]))
        output(f"Selected {project['id']}.")

    if agent is None:
        client = build_model_client(settings.home, log=output)
        if client is None:
            candidates = [
                Path.cwd() / ".env.local",
                settings.home / ".env.local",
            ]
            existing = [path for path in candidates if path.exists()]
            output("Forgel is not fully configured:")
            if existing:
                targets = " or ".join(str(path) for path in existing)
                output(
                    f"  model: set FORGEL_MODEL_API_KEY in {targets}"
                )
                output(
                    "         (`forgel setup` creates ./.env.local; "
                    "it is never committed)"
                )
            else:
                output(
                    "  model: set FORGEL_MODEL_API_KEY in the environment, "
                    "./.env.local, or "
                    f"{settings.home / '.env.local'} "
                    "(`forgel setup` creates ./.env.local)"
                )
            output(
                "  github: optional locally; needed to publish branches "
                "or create repositories"
            )
            output(
                "Commands and /adopt work; planning and code changes need "
                "the model. `forgel doctor` checks the rest."
            )
        else:
            agent = ProjectAgent(settings, ledger, client)
    router = CommandRouter(
        settings, ledger, daemon_enabled=daemon, agent=agent
    )
    output(
        "Forgel console. Describe the work or use /help; "
        "/quit exits."
    )
    output(
        "Mode: "
        + (
            "after each command the daemon runs until it needs you"
            if daemon
            else "commands only"
        )
        + "."
    )
    interactive = (
        input_fn is input
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )
    if interactive:
        _setup_readline(settings, ledger)
        selected = ledger.get_session(chat_id)
        project = ledger.get_project(selected) if selected else None
        output(
            f"Project: {project['name'] if project else 'none'}  ·  "
            f"cwd: {Path.cwd()}"
        )
        output(
            "Tab completes commands; ↑/↓ history; \\ continues a line; "
            "Ctrl-C stops input; Ctrl-D exits."
        )
    lang = "en"
    try:
        while True:
            if interactive:
                _flush_pending_input()
            prompt = (
                _prompt_text(ledger, chat_id) if interactive else PROMPT
            )
            try:
                line = _read_input(input_fn, prompt, interactive)
            except EOFError:
                break
            except KeyboardInterrupt:
                if interactive:
                    output("")
                    continue
                break
            text = line.strip()
            if not text:
                continue
            if text in QUIT:
                break
            if not text.startswith("/"):
                lang = detect_language(text, lang)
            if router.agent is None:
                client = build_model_client(settings.home, log=output)
                if client is not None:
                    router.agent = ProjectAgent(settings, ledger, client)
            try:
                with _Spinner(interactive):
                    reply = router.handle(chat_id, text, actor)
            except KeyboardInterrupt:
                if interactive:
                    output("Stopped.")
                    continue
                raise
            except Exception as exc:  # noqa: BLE001 - keep the console up
                output(f"error: {exc}")
                continue
            if reply.text:
                output(reply.text)
                if interactive:
                    output("")
            if daemon and not is_paused(settings.home):
                selected = ledger.get_session(chat_id)
                project = (
                    ledger.get_project(selected) if selected else None
                )
                layout = (
                    ProjectLayout.detect(project["workspace"])
                    if project is not None
                    else None
                )
                before = (
                    _task_snapshot(layout) if layout is not None else {}
                )
                try:
                    _drain(
                        settings,
                        ledger,
                        output,
                        sleep_fn=sleep_fn,
                        lang=lang,
                        agent=router.agent,
                        project=project,
                        session=str(chat_id),
                    )
                except KeyboardInterrupt:
                    if interactive:
                        output("Stopped; back to the prompt.")
                        continue
                    raise
                if layout is not None:
                    explanation = _explain_outcomes(
                        router.agent,
                        project,
                        layout,
                        before,
                        lang,
                        text,
                        session=str(chat_id),
                    )
                    if explanation:
                        output(explanation)
                        append_history(
                            layout,
                            "assistant",
                            explanation,
                            actor,
                            session=str(chat_id),
                        )
    finally:
        if interactive:
            _save_history(settings)
    output("Bye.")
