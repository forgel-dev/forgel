from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from forgel.approvals import awaits_approval, record_approval
from forgel.config import Settings
from forgel.daemon import project_is_done, run_daemon, run_once
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger, new_project_id
from forgel.projects import create_project
from forgel.tasks import create_task, get_task

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
            self.assertFalse(project_is_done(ledger, project_id))
            self.assertTrue(awaits_approval(ledger, project_id))

            record_approval(
                ledger, project_id, scope="staging", actor="test"
            )
            run_daemon(settings, ledger, once=True, log=lambda message: None)

            self.assertTrue(project_is_done(ledger, project_id))
            self.assertTrue(
                (workspace / "docs/program/iterations/1/close.md").exists()
            )

    def test_peak_hours_defer_model_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project_id = create_project(
                settings,
                ledger,
                "Peak demo",
                "A demo brief.",
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            assert project is not None
            layout = ProjectLayout.detect(project["workspace"])
            task = create_task(
                layout,
                "Do the work",
                ["Do it"],
                ["It is done"],
                repo_id="main",
            )
            logs: list[str] = []
            with patch(
                "forgel.daemon.peak.should_defer", return_value=True
            ):
                processed = run_once(
                    settings, ledger, log=logs.append
                )
            self.assertEqual(processed, [])
            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "pending")
            self.assertTrue(any("paused" in line for line in logs))

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
            record_approval(
                ledger, project_id, scope="staging", actor="test"
            )
            run_daemon(settings, ledger, once=True, log=lambda message: None)
            events = len(ledger.events(project_id))
            run_daemon(settings, ledger, once=True, log=lambda message: None)

            self.assertEqual(len(ledger.events(project_id)), events)


if __name__ == "__main__":
    unittest.main()
