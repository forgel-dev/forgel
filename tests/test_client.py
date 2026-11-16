from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from forgel import entry
from forgel.agent import append_history
from forgel.client import maybe_dispatch
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import create_task, get_task, list_tasks, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = {"ok", "kind", "text", "error"}


class ClientCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.project_id = create_project(
            self.settings, self.ledger, "Client", "A brief.", mode="brownfield"
        )
        project = self.ledger.get_project(self.project_id)
        assert project is not None
        self.layout = ProjectLayout.detect(project["workspace"])
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                }
            ],
        )
        self.env = {
            "FORGEL_MODEL_MODE": "script",
            "FORGEL_MODEL_API_KEY": "",
            "FORGEL_PEAK_POLICY": "always",
        }

    def _call(self, *argv: str) -> tuple[int, dict, str]:
        out = io.StringIO()
        with patch.dict(os.environ, self.env, clear=False):
            with redirect_stdout(out):
                code = entry.main([*argv, "--home", str(self.home)])
        text = out.getvalue()
        lines = [line for line in text.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, text)
        data = json.loads(lines[0])
        self.assertIsInstance(data, dict)
        return code, data, text

    def _assert_envelope(self, data: dict) -> None:
        self.assertTrue(ENVELOPE.issubset(data.keys()), data)
        self.assertIsInstance(data["ok"], bool)
        self.assertIsInstance(data["kind"], str)
        self.assertIsInstance(data["text"], str)
        self.assertIsInstance(data["error"], str)

    def _review_task(self) -> str:
        task = create_task(
            self.layout,
            "Add a health endpoint",
            ["Expose /health"],
            ["GET /health returns 200"],
            repo_id="main",
        )
        update_task(
            self.layout,
            str(task["id"]),
            status="review",
            result={"summary": "implemented"},
        )
        return str(task["id"])

    def _failed_task(self) -> str:
        task = create_task(
            self.layout,
            "Broken change",
            ["Change it"],
            ["It works"],
            repo_id="main",
        )
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={"summary": "failed", "failure": {"kind": "agent"}},
        )
        return str(task["id"])

    def test_status_json_returns_a_project_payload(self) -> None:
        code, data, _ = self._call("status", self.project_id, "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertTrue(data["ok"])
        self.assertEqual(data["kind"], "status")
        self.assertEqual(data["project"]["id"], self.project_id)
        self.assertEqual(data["project"]["name"], "Client")

    def test_tasks_json_lists_the_queue(self) -> None:
        task_id = self._review_task()
        code, data, _ = self._call("tasks", self.project_id, "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "tasks")
        self.assertEqual([item["id"] for item in data["tasks"]], [task_id])

    def test_task_accept_json_records_the_decision(self) -> None:
        task_id = self._review_task()
        code, data, _ = self._call(
            "task",
            "accept",
            "--task",
            task_id,
            "--project",
            self.project_id,
            "--json",
        )
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "task")
        self.assertEqual(data["task"]["id"], task_id)
        self.assertEqual(data["task"]["status"], "done")

    def test_task_reject_json_sends_the_work_back(self) -> None:
        task_id = self._review_task()
        code, data, _ = self._call(
            "task",
            "reject",
            "--task",
            task_id,
            "--project",
            self.project_id,
            "--notes",
            "wrong header",
            "--json",
        )
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["task"]["id"], task_id)
        self.assertEqual(data["task"]["status"], "failed")

    def test_task_retry_json_requeues_a_failed_task(self) -> None:
        task_id = self._failed_task()
        code, data, _ = self._call(
            "task",
            "retry",
            "--task",
            task_id,
            "--project",
            self.project_id,
            "--json",
        )
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["task"]["id"], task_id)
        self.assertEqual(data["task"]["status"], "pending")

    def test_plan_status_json_returns_the_milestone(self) -> None:
        task = create_task(
            self.layout,
            "Milestone step",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            plan_id="plan-1",
            plan_goal="Ship M1",
        )
        update_task(self.layout, str(task["id"]), status="done")
        code, data, _ = self._call(
            "plan", self.project_id, "--status", "--json"
        )
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "plan")
        self.assertEqual(data["plan"]["plan_id"], "plan-1")
        self.assertEqual(data["plan"]["status"], "done")

    def test_projects_json_lists_every_project(self) -> None:
        code, data, _ = self._call("projects", "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "projects")
        ids = [item["id"] for item in data["projects"]]
        self.assertIn(self.project_id, ids)

    def test_session_commands_set_and_read_the_default_session(self) -> None:
        code, data, _ = self._call("session", self.project_id, "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["session"], "local")
        self.assertEqual(data["project"]["id"], self.project_id)

        code, data, _ = self._call("session", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(data["session"], "local")
        self.assertEqual(data["project"]["id"], self.project_id)
        self.assertEqual(self.ledger.get_session(0), self.project_id)

        code, data, _ = self._call(
            "session", self.project_id, "--session", "other", "--json"
        )
        self.assertEqual(code, 0)
        self.assertEqual(data["session"], "other")

    def test_history_json_returns_the_recent_conversation(self) -> None:
        self.ledger.set_session(0, self.project_id)
        append_history(self.layout, "user", "hello", "local", session="0")
        append_history(self.layout, "assistant", "hi", "local", session="0")
        code, data, _ = self._call("history", "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "history")
        self.assertEqual(
            [item["text"] for item in data["history"]], ["hello", "hi"]
        )

    def test_pause_resume_and_daemon_json(self) -> None:
        code, data, _ = self._call("pause", "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertTrue(data["paused"])

        code, data, _ = self._call("resume", "--json")
        self.assertEqual(code, 0)
        self.assertFalse(data["paused"])

        code, data, _ = self._call("daemon", "--json")
        self.assertEqual(code, 0)
        self._assert_envelope(data)
        self.assertEqual(data["kind"], "daemon")
        self.assertGreaterEqual(data["cycles"], 1)

    def test_a_failing_call_returns_one_error_object_and_non_zero(self) -> None:
        code, data, _ = self._call("status", "missing-project", "--json")
        self.assertNotEqual(code, 0)
        self._assert_envelope(data)
        self.assertFalse(data["ok"])
        self.assertEqual(data["kind"], "status")
        self.assertIn("unknown project", data["error"])

    def test_say_without_text_is_an_error_envelope(self) -> None:
        code, data, _ = self._call("say", "--json")
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])
        self.assertEqual(data["kind"], "say")
        self.assertTrue(data["error"])

    def test_say_routes_a_change_request_to_a_queued_task(self) -> None:
        response = {
            "kind": "change_request",
            "reply": "Recorded.",
            "title": "Add a health endpoint",
            "requirements": ["Expose GET /health"],
            "acceptance": ["GET /health returns 200"],
            "repo_id": "main",
            "assumptions": ["The endpoint lives in the main app"],
        }
        (self.home / "model-script.json").write_text(
            json.dumps({"responses": [json.dumps(response)]}),
            encoding="utf-8",
        )
        code, data, _ = self._call(
            "say",
            "--project",
            self.project_id,
            "--text",
            "add a health endpoint",
            "--json",
        )
        self.assertEqual(code, 0, data)
        self._assert_envelope(data)
        self.assertTrue(data["ok"])
        self.assertEqual(data["kind"], "change_request")
        self.assertIn("Recorded.", data["text"])
        queued = list_tasks(self.layout)
        self.assertEqual(len(queued), 1)
        self.assertEqual(data["task"]["id"], queued[0]["id"])
        self.assertEqual(data.get("task_id"), queued[0]["id"])
        self.assertIsNotNone(get_task(self.layout, str(queued[0]["id"])))

    def test_say_answers_a_question(self) -> None:
        response = {"kind": "answer", "reply": "It is an app."}
        (self.home / "model-script.json").write_text(
            json.dumps({"responses": [json.dumps(response)]}),
            encoding="utf-8",
        )
        code, data, _ = self._call(
            "say",
            "--project",
            self.project_id,
            "--text",
            "what is this?",
            "--json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(data["kind"], "answer")
        self.assertEqual(data["text"], "It is an app.")
        self.assertEqual(list_tasks(self.layout), [])

    def test_existing_commands_are_not_taken_over(self) -> None:
        self.assertIsNone(maybe_dispatch(["status", self.project_id]))
        self.assertIsNone(maybe_dispatch(["task", "list", self.project_id]))
        self.assertIsNone(maybe_dispatch(["chat"]))
        self.assertIsNone(maybe_dispatch([]))
        self.assertIsNone(maybe_dispatch(["telegram"]))


if __name__ == "__main__":
    unittest.main()
