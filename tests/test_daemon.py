from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.daemon import project_is_done, run_daemon
from forgel.ledger import Ledger, new_project_id

REPO_ROOT = Path(__file__).resolve().parents[1]


class DaemonTest(unittest.TestCase):
    def _settings(self, tmp: str) -> Settings:
        return Settings(
            home=Path(tmp),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )

    def test_once_processes_a_pending_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id, "hello-web", "A minimal web app.", str(workspace)
            )

            cycles = run_daemon(
                settings, ledger, once=True, log=lambda message: None
            )

            self.assertEqual(cycles, 1)
            self.assertTrue(project_is_done(ledger, project_id))
            self.assertTrue(
                (workspace / "docs/program/iterations/1/close.md").exists()
            )

    def test_done_project_is_not_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id, "hello-web", "A minimal web app.", str(workspace)
            )

            run_daemon(settings, ledger, once=True, log=lambda message: None)
            events = len(ledger.events(project_id))
            run_daemon(settings, ledger, once=True, log=lambda message: None)

            self.assertEqual(len(ledger.events(project_id)), events)


if __name__ == "__main__":
    unittest.main()
