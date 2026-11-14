from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.agent import ProjectAgent
from forgel.config import Settings
from forgel.console import run_console
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


def _feed(lines: list[str]):
    remaining = list(lines)

    def read(_prompt: str) -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return read


class ConsoleTest(unittest.TestCase):
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

    def _run(self, lines: list[str], agent=None):
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            daemon=False,
            input_fn=_feed(lines),
            output=output.append,
            agent=agent,
        )
        return "\n".join(output)

    def test_new_project_and_selection_work_without_telegram(self) -> None:
        text = self._run(["/new Demo | A demo brief.", "/projects", "/quit"])
        self.assertIn("Forgel console", text)
        projects = self.ledger.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Demo")
        self.assertEqual(self.ledger.get_session(0), projects[0]["id"])
        self.assertIn(projects[0]["id"], text)

    def test_starts_with_a_selected_project(self) -> None:
        project_id = create_project(
            self.settings, self.ledger, "Selected", "A brief."
        )
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            project_id=project_id,
            daemon=False,
            input_fn=_feed(["/status", "/quit"]),
            output=output.append,
        )
        self.assertIn(f"Selected {project_id}", "\n".join(output))
        self.assertEqual(self.ledger.get_session(0), project_id)

    def test_free_text_records_a_change_request(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Console agent",
            "A brief.",
            mode="brownfield",
        )
        layout = ProjectLayout.detect(
            self.ledger.get_project(project_id)["workspace"]
        )
        from forgel.program_manifest import set_entries

        set_entries(
            layout,
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
        self.ledger.set_session(0, project_id)
        response = {
            "kind": "change_request",
            "reply": "Recorded.",
            "title": "Add a page",
            "requirements": ["Add a page"],
            "acceptance": ["The page exists"],
            "repo_id": "main",
            "assumptions": ["The page goes in the main app"],
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        text = self._run(
            ["Add a page to the app", "/tasks", "/quit"], agent=agent
        )
        self.assertIn("Recorded.", text)
        self.assertIn("Add a page", text)

    def test_quit_and_eof_end_the_console(self) -> None:
        text = self._run(["/quit"])
        self.assertIn("Bye.", text)
        text = self._run([])
        self.assertIn("Bye.", text)

    def test_a_missing_model_is_reported_with_the_setup_command(
        self,
    ) -> None:
        output: list[str] = []
        with patch(
            "forgel.console.build_model_client", return_value=None
        ):
            run_console(
                self.settings,
                self.ledger,
                daemon=False,
                input_fn=_feed(["/quit"]),
                output=output.append,
            )
        text = "\n".join(output)
        self.assertIn("not fully configured", text)
        self.assertIn("forgel setup", text)
        self.assertIn("FORGEL_MODEL_API_KEY", text)

    def test_daemon_mode_returns_when_there_is_nothing_to_do(self) -> None:
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            daemon=True,
            input_fn=_feed(["/projects", "/quit"]),
            output=output.append,
        )
        self.assertIn("Bye.", "\n".join(output))

    def test_a_model_configured_after_start_enables_free_text(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Late model",
            "A brief.",
            mode="brownfield",
        )
        from forgel.program_manifest import set_entries

        layout = ProjectLayout.detect(
            self.ledger.get_project(project_id)["workspace"]
        )
        set_entries(
            layout,
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
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "late answer"})]
        )
        output: list[str] = []
        with patch(
            "forgel.console.build_model_client",
            side_effect=[None, client],
        ):
            run_console(
                self.settings,
                self.ledger,
                project_id=project_id,
                daemon=False,
                input_fn=_feed(["hello", "/quit"]),
                output=output.append,
            )
        self.assertIn("late answer", "\n".join(output))
        self.assertEqual(len(client.requests), 1)

    def test_help_puts_plain_language_first(self) -> None:
        text = self._run(["/help", "/quit"])
        self.assertIn("Talk in plain language", text)
        self.assertIn("/adopt", text)
        self.assertIn("accept the latest task", text)


if __name__ == "__main__":
    unittest.main()
