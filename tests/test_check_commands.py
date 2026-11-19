from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.check_commands import check_problems, command_problem
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class CheckCommandsTest(unittest.TestCase):
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
            "Check demo",
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
        self.main = self.layout.repo_path("main")
        self.code = self.layout.repo_path("code")
        self.main.mkdir(parents=True, exist_ok=True)
        self.code.mkdir(parents=True, exist_ok=True)

    def _test_module(self, root: Path, name: str) -> None:
        tests = root / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / f"{name}.py").write_text("", encoding="utf-8")

    def test_a_check_in_a_sibling_repository_is_rejected(self) -> None:
        self._test_module(self.main, "test_cli")
        problem = command_problem(
            self.layout,
            "code",
            ["python", "-m", "unittest", "tests.test_cli"],
        )
        self.assertIn("main", problem)
        self.assertIn("code", problem)
        self.assertIn("tests.test_cli", problem)

    def test_a_check_in_the_task_repository_is_accepted(self) -> None:
        self._test_module(self.code, "test_cli")
        self.assertEqual(
            command_problem(
                self.layout,
                "code",
                ["python", "-m", "unittest", "tests.test_cli"],
            ),
            "",
        )

    def test_a_check_for_a_new_file_is_accepted(self) -> None:
        self.assertEqual(
            command_problem(
                self.layout,
                "code",
                ["python", "-m", "unittest", "tests.test_new"],
            ),
            "",
        )

    def test_discover_in_a_sibling_repository_is_rejected(self) -> None:
        (self.main / "tests").mkdir()
        problem = command_problem(
            self.layout,
            "code",
            ["python", "-m", "unittest", "discover", "-s", "tests"],
        )
        self.assertIn("tests", problem)
        self.assertIn("main", problem)

    def test_a_script_in_a_sibling_repository_is_rejected(self) -> None:
        scripts = self.main / "scripts"
        scripts.mkdir()
        (scripts / "check.py").write_text("print('ok')\n", encoding="utf-8")
        problem = command_problem(
            self.layout, "code", ["python", "scripts/check.py"]
        )
        self.assertIn("scripts/check.py", problem)
        self.assertIn("main", problem)

    def test_a_non_python_command_is_not_guessed(self) -> None:
        self.assertEqual(
            command_problem(self.layout, "code", ["make", "test"]), ""
        )

    def test_check_problems_names_the_criterion(self) -> None:
        self._test_module(self.main, "test_cli")
        problems = check_problems(
            self.layout,
            "code",
            [
                {
                    "criterion": "The client tests pass",
                    "command": ["python", "-m", "unittest", "tests.test_cli"],
                }
            ],
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("The client tests pass", problems[0])


if __name__ == "__main__":
    unittest.main()
