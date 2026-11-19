from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.specs import SpecError, write_task_spec

REPO_ROOT = Path(__file__).resolve().parents[1]

VALID = {
    "problem": "The client needs the change.",
    "outcome": "The change is in the client.",
    "scope": ["the client"],
    "non_goals": [],
    "requirements": ["Make the change"],
    "acceptance": ["The change is present"],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The change is present"],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "affected_files": ["forgel_code/cli.py"],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
    "checks": [
        {"criterion": "The change is present", "verification": "review"}
    ],
    "test_command": [],
    "external_dependencies": [],
}


class SpecCheckValidationTest(unittest.TestCase):
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
        project_id = create_project(
            self.settings,
            self.ledger,
            "Spec demo",
            "A demo project.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
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
                },
                {
                    "id": "code",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                },
            ],
        )
        main = self.layout.repo_path("main")
        code = self.layout.repo_path("code")
        (main / "tests").mkdir(parents=True, exist_ok=True)
        (main / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (main / "tests" / "test_cli.py").write_text(
            "", encoding="utf-8"
        )
        code.mkdir(parents=True, exist_ok=True)

    def _intent(self) -> dict:
        return {
            "title": "Client change",
            "summary": "Change the client.",
            "repo_id": "code",
            "depends_on": [],
        }

    def test_a_sibling_repository_check_is_retried_in_the_spec(self) -> None:
        invalid = dict(VALID)
        invalid["checks"] = [
            {
                "criterion": "The client tests pass",
                "command": ["python", "-m", "unittest", "tests.test_cli"],
            }
        ]
        client = ScriptedModelClient(
            [json.dumps(invalid), json.dumps(VALID)]
        )
        spec = write_task_spec(
            self.settings,
            self.layout,
            "Goal",
            "",
            self._intent(),
            client,
            log=lambda _m: None,
        )
        self.assertEqual(spec["checks"][0]["verification"], "review")
        retry = client.requests[1][-1].content
        self.assertIn("exists in repository 'main'", retry)
        self.assertIn("task repository 'code'", retry)

    def test_an_external_dependency_needs_a_command_check(self) -> None:
        review_only = dict(VALID)
        review_only["external_dependencies"] = [
            {"name": "weather", "interface": "HTTP forecast"}
        ]
        valid = dict(review_only)
        valid["checks"] = [
            {
                "criterion": "The forecast interface answers",
                "verification": "command",
                "command": ["python", "-c", "print('ok')"],
            }
        ]
        client = ScriptedModelClient(
            [json.dumps(review_only), json.dumps(valid)]
        )
        spec = write_task_spec(
            self.settings,
            self.layout,
            "Goal",
            "",
            self._intent(),
            client,
            log=lambda _m: None,
        )
        self.assertEqual(spec["checks"][0]["verification"], "command")
        retry = client.requests[1][-1].content
        self.assertIn("command check", retry)

    def test_a_persistent_sibling_check_fails_the_spec(self) -> None:
        invalid = dict(VALID)
        invalid["checks"] = [
            {
                "criterion": "The client tests pass",
                "command": ["python", "-m", "unittest", "tests.test_cli"],
            }
        ]
        client = ScriptedModelClient(
            [json.dumps(invalid), json.dumps(invalid)]
        )
        with self.assertRaises(SpecError) as caught:
            write_task_spec(
                self.settings,
                self.layout,
                "Goal",
                "",
                self._intent(),
                client,
                log=lambda _m: None,
            )
        self.assertIn("exists in repository 'main'", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
