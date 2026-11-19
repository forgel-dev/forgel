from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.environment import Environment
from forgel.integration import (
    integration_problem,
    integration_required,
    integration_warning,
)
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]

MAIN = {
    "id": "main",
    "role": "application",
    "provider": "local",
    "url": "",
    "depends_on": [],
}


class IntegrationRequirementTest(unittest.TestCase):
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
            "Integration demo",
            "A demo project.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        self.layout = ProjectLayout.detect(project["workspace"])

    def _repos(self, *repos: dict) -> None:
        set_entries(self.layout, list(repos))

    def test_a_single_repository_needs_no_program_e2e(self) -> None:
        self._repos(MAIN)
        required, _reason = integration_required(self.layout, None)
        self.assertFalse(required)
        self.assertEqual(
            integration_problem(self.layout, None), ""
        )

    def test_an_interacting_repository_requires_e2e(self) -> None:
        self._repos(
            MAIN,
            {
                **MAIN,
                "id": "code",
                "depends_on": ["main"],
            },
        )
        required, reason = integration_required(self.layout, None)
        self.assertTrue(required)
        self.assertIn("code->main", reason)
        problem = integration_problem(self.layout, None)
        self.assertIn("needs a program e2e", problem)
        self.assertIn("code->main", problem)

    def test_a_frontend_repository_requires_e2e(self) -> None:
        self._repos({**MAIN, "role": "frontend"})
        required, reason = integration_required(self.layout, None)
        self.assertTrue(required)
        self.assertIn("frontend", reason)

    def test_a_mobile_repository_requires_e2e(self) -> None:
        self._repos({**MAIN, "role": "mobile"})
        required, reason = integration_required(self.layout, None)
        self.assertTrue(required)
        self.assertIn("simulator", reason)
        self.assertEqual(
            integration_problem(self.layout, None), ""
        )
        self.assertIn(
            "deferred", integration_warning(self.layout, None)
        )

    def test_sibling_mounts_require_e2e(self) -> None:
        self._repos(MAIN, {**MAIN, "id": "code"})
        environment = Environment(mounts=("code",))
        required, reason = integration_required(
            self.layout, environment
        )
        self.assertTrue(required)
        self.assertIn("mounts", reason)

    def test_database_services_do_not_require_e2e(self) -> None:
        self._repos(MAIN)
        environment = Environment(
            services=("compose.yaml",),
            ports=(5432,),
            health="/health",
        )
        required, _reason = integration_required(
            self.layout, environment
        )
        self.assertFalse(required)
        self.assertEqual(
            integration_problem(self.layout, environment), ""
        )

    def test_a_declared_e2e_satisfies_the_requirement(self) -> None:
        self._repos(
            MAIN,
            {**MAIN, "id": "code", "depends_on": ["main"]},
        )
        environment = Environment(
            image="python:3.12-slim",
            e2e=("python -c \"print('e2e')\"",),
        )
        self.assertTrue(
            integration_required(self.layout, environment)[0]
        )
        self.assertEqual(
            integration_problem(self.layout, environment), ""
        )


if __name__ == "__main__":
    unittest.main()
