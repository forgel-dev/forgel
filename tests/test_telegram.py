from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.agent import ProjectAgent
from forgel.approvals import record_approval
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.control import is_paused
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.project_config import render_project_config
from forgel.projects import create_project
from forgel.secrets import get_secret, set_secret
from forgel.telegram import (
    HELP,
    CommandRouter,
    TelegramConfig,
    TelegramConfigError,
    TelegramGateway,
    split_message,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeAPI:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, dict | None]] = []
        self.answers: list[tuple[str, str]] = []
        self.edits: list[tuple[int, int, str]] = []
        self.deleted: list[tuple[int, int]] = []
        self.actions: list[tuple[int, str]] = []

    def send_message(
        self, chat_id: int, text: str, reply_markup: dict | None = None
    ) -> list[dict]:
        self.sent.append((chat_id, text, reply_markup))
        return [{}]

    def answer_callback_query(self, callback_id: str, text: str = "") -> dict:
        self.answers.append((callback_id, text))
        return {}

    def edit_message_text(self, chat_id: int, message_id: int, text: str) -> dict:
        self.edits.append((chat_id, message_id, text))
        return {}

    def delete_message(self, chat_id: int, message_id: int) -> dict:
        self.deleted.append((chat_id, message_id))
        return {}

    def send_chat_action(self, chat_id: int, action: str = "typing") -> dict:
        self.actions.append((chat_id, action))
        return {}

    def get_updates(self, offset: int | None, timeout: int) -> list[dict]:
        return []


class ConfigTest(unittest.TestCase):
    def test_requires_token_and_allowlist(self) -> None:
        with self.assertRaises(TelegramConfigError):
            TelegramConfig.from_env({})
        with self.assertRaises(TelegramConfigError):
            TelegramConfig.from_env({"TELEGRAM_BOT_TOKEN": "t"})
        with self.assertRaises(TelegramConfigError):
            TelegramConfig.from_env(
                {
                    "TELEGRAM_BOT_TOKEN": "t",
                    "TELEGRAM_ALLOWED_CHAT_IDS": "abc",
                }
            )

    def test_token_can_come_from_the_secret_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            set_secret(home, "telegram.bot_token", "file-token")
            config = TelegramConfig.from_env(
                {"TELEGRAM_ALLOWED_CHAT_IDS": "7"}, home=home
            )
            self.assertEqual(config.token, "file-token")

    def test_parses_chat_ids(self) -> None:
        config = TelegramConfig.from_env(
            {
                "TELEGRAM_BOT_TOKEN": "t",
                "TELEGRAM_ALLOWED_CHAT_IDS": "1, 2,3",
                "TELEGRAM_POLL_TIMEOUT": "5",
            }
        )
        self.assertEqual(config.allowed_chat_ids, frozenset({1, 2, 3}))
        self.assertEqual(config.poll_timeout, 5)

    def test_split_message_respects_the_limit(self) -> None:
        text = "\n".join(f"line {index}" for index in range(1000))
        chunks = split_message(text, limit=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))
        self.assertEqual("\n".join(chunks), text)


class RouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.router = CommandRouter(self.settings, self.ledger)

    def _project(self, name: str = "demo", brief: str = "A demo brief.") -> str:
        return create_project(self.settings, self.ledger, name, brief)

    def send(self, text: str, actor: str = "@tester"):
        return self.router.handle(7, text, actor)

    def test_help(self) -> None:
        self.assertEqual(self.send("/help").text, HELP)
        self.assertEqual(self.send("/start").text, HELP)

    def test_new_creates_a_project(self) -> None:
        reply = self.send("/new Demo App | A small web app.")
        self.assertIn("created", reply.text)
        projects = self.ledger.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Demo App")
        self.assertEqual(projects[0]["brief"], "A small web app.")

    def test_new_without_name_derives_one(self) -> None:
        self.send("/new A tiny notes app")
        project = self.ledger.list_projects()[0]
        self.assertEqual(project["name"], "A tiny notes app")

    def test_list_and_status(self) -> None:
        project_id = self._project()
        listing = self.send("/list")
        self.assertIn(project_id, listing.text)
        status = self.send(f"/status {project_id[:10]}")
        self.assertIn(f"project: {project_id}", status.text)
        self.assertIn("staging approval: none", status.text)

    def test_unknown_project_is_reported(self) -> None:
        reply = self.send("/status missing")
        self.assertIn("error", reply.text)

    def test_run_reports_a_disabled_daemon(self) -> None:
        project_id = self._project()
        router = CommandRouter(
            self.settings, self.ledger, daemon_enabled=False
        )
        reply = router.handle(7, f"/run {project_id}", "@tester")
        self.assertIn("does not run iterations", reply.text)

    def test_pause_and_resume(self) -> None:
        self.send("/pause")
        self.assertTrue(is_paused(self.settings.home))
        self.send("/resume")
        self.assertFalse(is_paused(self.settings.home))

    def test_staging_approval_through_chat(self) -> None:
        project_id = self._project()
        self.ledger.set_checkpoint(project_id, "approval")
        reply = self.send(f"/approve {project_id} staging looks good")
        self.assertIn("Staging approval recorded", reply.text)
        rows = self.ledger.approvals(project_id, "staging")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor"], "@tester")
        self.assertEqual(rows[0]["notes"], "looks good")

    def test_reject_stays_at_the_gate(self) -> None:
        project_id = self._project()
        self.ledger.set_checkpoint(project_id, "approval")
        reply = self.send(f"/reject {project_id} staging not ready")
        self.assertIn("Staging rejected", reply.text)
        rows = self.ledger.approvals(project_id, "staging")
        self.assertEqual(rows[0]["decision"], "rejected")

    def test_production_requires_a_callback_with_the_disclaimer(self) -> None:
        project_id = self._project()
        self.ledger.set_checkpoint(project_id, "approval")
        record_approval(
            self.ledger, project_id, scope="staging", actor="@tester"
        )
        self.ledger.set_checkpoint(project_id, "done")

        prompt = self.send(f"/approve {project_id} production")
        self.assertIn("not a law firm", prompt.text)
        self.assertIsNotNone(prompt.reply_markup)
        assert prompt.reply_markup is not None
        callback = prompt.reply_markup["inline_keyboard"][0][0]["callback_data"]
        self.assertTrue(callback.startswith("ap:"))

        reply = self.router.handle_callback(7, callback, "@tester")
        self.assertIn("Production approval recorded", reply.text)
        rows = self.ledger.approvals(project_id, "production")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["compliance_ack"], 1)

        repeated = self.router.handle_callback(7, callback, "@tester")
        self.assertIn("expired", repeated.text)

    def test_production_is_blocked_before_the_release_closes(self) -> None:
        project_id = self._project()
        self.ledger.set_checkpoint(project_id, "approval")
        record_approval(
            self.ledger, project_id, scope="staging", actor="@tester"
        )
        reply = self.send(f"/approve {project_id} production")
        self.assertIn("requires a completed release", reply.text)

    def test_sync_and_proposals_on_a_fresh_workspace(self) -> None:
        project_id = self._project()
        sync = self.send(f"/sync {project_id}")
        self.assertIn("No external changes", sync.text)
        proposals = self.send(f"/proposals {project_id}")
        self.assertIn("No proposals", proposals.text)


class SelectionAndAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)

    def _router(self, responses: list[str] | None = None) -> CommandRouter:
        if responses is None:
            return CommandRouter(self.settings, self.ledger)
        client = ScriptedModelClient(responses)
        agent = ProjectAgent(self.settings, self.ledger, client)
        return CommandRouter(self.settings, self.ledger, agent=agent)

    def _project(self, name: str, brief: str) -> str:
        return create_project(self.settings, self.ledger, name, brief)

    def test_new_selects_the_created_project(self) -> None:
        router = self._router()
        reply = router.handle(7, "/new Demo | A demo brief.", "@tester")
        project = self.ledger.list_projects()[0]
        self.assertEqual(self.ledger.get_session(7), project["id"])
        self.assertIn("selected", reply.text)
        status = router.handle(7, "/status", "@tester")
        self.assertIn(project["id"], status.text)

    def test_use_switches_the_selected_project(self) -> None:
        router = self._router()
        first = self._project("First", "First brief.")
        second = self._project("Second", "Second brief.")
        self.ledger.set_session(7, first)
        reply = router.handle(7, f"/use {second}", "@tester")
        self.assertIn("Selected", reply.text)
        self.assertEqual(self.ledger.get_session(7), second)
        projects = router.handle(7, "/projects", "@tester")
        self.assertIn(f"* {second}", projects.text)
        self.assertIn(f"  {first}", projects.text)

    def test_missing_selection_is_reported(self) -> None:
        router = self._router()
        self.assertIn(
            "No project selected", router.handle(7, "/status", "@tester").text
        )
        self.assertIn(
            "No project selected", router.handle(7, "hello", "@tester").text
        )

    def test_plain_message_goes_to_the_selected_agent(self) -> None:
        router = self._router(
            [json.dumps({"kind": "answer", "reply": "project answer"})]
        )
        project = self._project("Alpha", "Alpha brief marker.")
        self.ledger.set_session(7, project)
        reply = router.handle(7, "What is this project?", "@tester")
        self.assertEqual(reply.text, "project answer")

    def test_agent_prompts_are_isolated_between_projects(self) -> None:
        client = ScriptedModelClient(
            [
                json.dumps({"kind": "answer", "reply": "alpha"}),
                json.dumps({"kind": "answer", "reply": "beta"}),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        router = CommandRouter(self.settings, self.ledger, agent=agent)
        alpha = self._project("Alpha One", "Alpha brief marker.")
        beta = self._project("Beta Two", "Beta brief marker.")

        self.ledger.set_session(7, alpha)
        router.handle(7, "first", "@tester")
        self.ledger.set_session(7, beta)
        router.handle(7, "second", "@tester")

        alpha_prompt = client.requests[0][1].content
        beta_prompt = client.requests[1][1].content
        self.assertIn("Alpha brief marker.", alpha_prompt)
        self.assertNotIn("Beta brief marker.", alpha_prompt)
        self.assertIn("Beta brief marker.", beta_prompt)
        self.assertNotIn("Alpha brief marker.", beta_prompt)

    def test_secret_like_message_is_not_sent_to_the_agent(self) -> None:
        client = ScriptedModelClient([])
        agent = ProjectAgent(self.settings, self.ledger, client)
        router = CommandRouter(self.settings, self.ledger, agent=agent)
        project = self._project("Alpha", "Alpha brief.")
        self.ledger.set_session(7, project)

        reply = router.handle(7, "sk-" + "b" * 24, "@tester")

        self.assertTrue(reply.delete_source)
        self.assertIn("looks like a secret", reply.text)
        self.assertEqual(client.requests, [])

    def test_secret_set_never_echoes_the_value(self) -> None:
        router = self._router()
        value = "sk-" + "c" * 24
        reply = router.handle(
            7, f"/secret set model.api_key {value}", "@tester"
        )
        self.assertTrue(reply.delete_source)
        self.assertNotIn(value, reply.text)
        self.assertEqual(
            get_secret(self.settings.home, "model.api_key", {}), value
        )
        listing = router.handle(7, "/secret", "@tester")
        self.assertNotIn(value, listing.text)
        self.assertIn("model.api_key: file", listing.text)

    def test_config_supports_daemon_keys_and_secret_hints(self) -> None:
        router = self._router()
        reply = router.handle(7, "/config set daemon.interval 3", "@tester")
        self.assertIn("daemon.interval = 3", reply.text)
        hint = router.handle(
            7, "/config set model.api_key sk-value", "@tester"
        )
        self.assertIn("is a secret", hint.text)

    def test_config_view_and_set(self) -> None:
        router = self._router()
        project = self._project("Demo", "A demo brief.")
        self.ledger.set_session(7, project)
        root = Path(self.ledger.get_project(project)["workspace"])
        write_text(
            ProjectLayout.detect(root).control / "forgel.toml",
            render_project_config("Demo"),
        )
        view = router.handle(7, "/config", "@tester")
        self.assertIn("qa.runtime = auto (project)", view.text)
        set_reply = router.handle(
            7, "/config set qa.runtime docker", "@tester"
        )
        self.assertIn("qa.runtime = docker", set_reply.text)
        after = router.handle(7, "/config", "@tester")
        self.assertIn("qa.runtime = docker (project)", after.text)


class AdoptCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.router = CommandRouter(self.settings, self.ledger)

    def _repo(self, name: str) -> Path:
        path = self.settings.home / "sources" / name
        path.mkdir(parents=True)
        (path / "README.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(["git", "add", "-A"], cwd=path, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "initial",
            ],
            cwd=path,
            check=True,
        )
        return path

    def test_adopt_selects_and_adds_related_repositories(self) -> None:
        backend = self._repo("backend")
        adopted = self.router.handle(
            7, f"/adopt {backend} | Backend service", "@tester"
        )
        self.assertIn("Adopted", adopted.text)
        project = self.ledger.list_projects()[0]
        self.assertEqual(self.ledger.get_session(7), project["id"])
        listing = self.router.handle(7, "/repo list", "@tester")
        self.assertIn("main", listing.text)
        self.assertIn(str(backend), listing.text)

        frontend = self._repo("frontend")
        added = self.router.handle(
            7,
            f"/repo add {frontend} web depends_on=main",
            "@tester",
        )
        self.assertIn("Added repository web", added.text)
        self.assertIn("Dependency edges: main", added.text)
        layout = ProjectLayout.detect(project["workspace"])
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: web", program)
        self.assertIn("depends_on: [main]", program)

        infra = self._repo("infra")
        independent = self.router.handle(
            7, f"/repo add {infra} infra", "@tester"
        )
        self.assertIn("No dependency edges", independent.text)

        linked = self.router.handle(
            7, "/repo link infra depends_on=main", "@tester"
        )
        self.assertIn("Updated dependencies for infra: main", linked.text)
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("depends_on: [main]", program)

    def test_repo_add_requires_a_selected_project(self) -> None:
        reply = self.router.handle(
            7, f"/repo add {self._repo('x')}", "@tester"
        )
        self.assertIn("No project selected", reply.text)

    def test_github_status_reports_the_project_repositories(self) -> None:
        backend = self._repo("backend")
        self.router.handle(7, f"/adopt {backend}", "@tester")
        status = self.router.handle(7, "/github", "@tester")
        self.assertIn("merge policy: auto", status.text)
        self.assertIn("main: local", status.text)
        usage = self.router.handle(7, "/github nope", "@tester")
        self.assertIn("Usage:", usage.text)


class GatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.api = FakeAPI()
        self.config = TelegramConfig(
            token="t", allowed_chat_ids=frozenset({7})
        )
        self.gateway = TelegramGateway(
            self.settings,
            self.ledger,
            self.config,
            api=self.api,  # type: ignore[arg-type]
            log=lambda message: None,
        )

    def _message(
        self, chat_id: int, text: str, message_id: int = 1
    ) -> dict:
        return {
            "update_id": 1,
            "message": {
                "message_id": message_id,
                "chat": {"id": chat_id},
                "from": {"id": chat_id, "username": "tester"},
                "text": text,
            },
        }

    def test_ignores_unauthorized_chats(self) -> None:
        handled = self.gateway.process(self._message(99, "/help"))
        self.assertFalse(handled)
        self.assertEqual(self.api.sent, [])

    def test_answers_an_allowed_chat(self) -> None:
        handled = self.gateway.process(self._message(7, "/help"))
        self.assertTrue(handled)
        self.assertEqual(len(self.api.sent), 1)
        chat_id, text, _markup = self.api.sent[0]
        self.assertEqual(chat_id, 7)
        self.assertEqual(text, HELP)

    def test_callback_edits_the_prompt(self) -> None:
        update = {
            "update_id": 2,
            "callback_query": {
                "id": "cb",
                "from": {"id": 7, "username": "tester"},
                "message": {"message_id": 42, "chat": {"id": 7}},
                "data": "ap:missing:ok",
            },
        }
        handled = self.gateway.process(update)
        self.assertTrue(handled)
        self.assertEqual(len(self.api.answers), 1)
        self.assertEqual(self.api.edits[0][1], 42)
        self.assertIn("expired", self.api.edits[0][2].lower())

    def test_notifications_are_skipped_for_unchanged_state(self) -> None:
        before = len(self.api.sent)
        self.gateway._notify_transitions()
        self.assertEqual(len(self.api.sent), before)

    def test_secret_message_is_deleted_and_not_echoed(self) -> None:
        value = "sk-" + "d" * 24
        handled = self.gateway.process(
            self._message(7, f"/secret set model.api_key {value}", message_id=5)
        )
        self.assertTrue(handled)
        self.assertEqual(self.api.deleted, [(7, 5)])
        self.assertTrue(self.api.sent)
        self.assertNotIn(value, self.api.sent[-1][1])

    def test_plain_text_triggers_typing_and_the_agent_hint(self) -> None:
        project_id = create_project(
            self.settings, self.ledger, "Demo", "A demo brief."
        )
        self.ledger.set_session(7, project_id)
        handled = self.gateway.process(self._message(7, "hello"))
        self.assertTrue(handled)
        self.assertEqual(self.api.actions, [(7, "typing")])
        self.assertIn("agent is not configured", self.api.sent[-1][1])


class TelegramAPITest(unittest.TestCase):
    def test_send_message_splits_and_calls_the_api(self) -> None:
        calls: list[dict] = []

        class Response:
            def __init__(self, payload: dict) -> None:
                self._body = json.dumps(payload).encode()

            def read(self) -> bytes:
                return self._body

            def __enter__(self) -> Response:
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def opener(request: object, timeout: float = 0) -> Response:
            body = json.loads(request.data.decode())  # type: ignore[attr-defined]
            calls.append(body)
            return Response({"ok": True, "result": {"message_id": len(calls)}})

        from forgel.telegram import TelegramAPI

        api = TelegramAPI(
            TelegramConfig(token="t", allowed_chat_ids=frozenset({1})),
            opener=opener,
        )
        api.send_message(1, "x" * 5000)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call["chat_id"] == 1 for call in calls))


if __name__ == "__main__":
    unittest.main()
