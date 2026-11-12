from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.ledger import Ledger, new_project_id
from forgel.orchestrator import Orchestrator

REPO_ROOT = Path(__file__).resolve().parents[1]


class EndToEndTest(unittest.TestCase):
    def test_pipeline_reaches_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id,
                "hello-web",
                "A minimal web app with an index page and a health check.",
                str(workspace),
            )

            Orchestrator(settings, ledger).run(project_id)

            self.assertEqual(ledger.checkpoint(project_id), "done")
            self.assertTrue((workspace / "program.yaml").exists())
            self.assertTrue((workspace / "lock.json").exists())
            self.assertTrue((workspace / "staging.json").exists())
            self.assertTrue(
                (workspace / "docs/program/acceptance/0001_hello-web.md").exists()
            )
            self.assertTrue((workspace / "api/app.py").exists())
            self.assertTrue((workspace / "web/index.html").exists())
            self.assertTrue((workspace / "e2e/check.py").exists())
            self.assertTrue(
                (workspace / "docs/program/jurisdiction/profile.json").exists()
            )
            self.assertTrue(
                (workspace / "docs/program/jurisdiction/requirements.md").exists()
            )
            self.assertTrue(
                (workspace / "docs/program/jurisdiction/compliance.md").exists()
            )
            self.assertTrue(
                (workspace / "docs/program/jurisdiction/disclaimer.md").exists()
            )

            profile = json.loads(
                (workspace / "docs/program/jurisdiction/profile.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(profile["id"], "ru")
            self.assertEqual(profile["status"], "draft")
            self.assertEqual(profile["legal_review_status"], "draft")
            self.assertTrue(profile["production_allowed"])
            self.assertTrue(profile["acknowledgement_required"])

            lock = json.loads((workspace / "lock.json").read_text(encoding="utf-8"))
            self.assertEqual(lock["jurisdiction"]["status"], "draft")
            self.assertTrue(lock["jurisdiction"]["production_allowed"])
            self.assertTrue(lock["jurisdiction"]["acknowledgement_required"])

            qa = (workspace / "docs/program/qa-report.md").read_text(encoding="utf-8")
            self.assertIn("**Verdict:** PASS", qa)
            self.assertIn("SUMMARY: 4/4 checks passed", qa)

            acceptance = (
                workspace / "docs/program/acceptance/0001_hello-web.md"
            ).read_text(encoding="utf-8")
            self.assertIn("**Verdict:** PASS", acceptance)

    def test_resume_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(project_id, "hello-web", "A minimal web app.", str(workspace))

            orchestrator = Orchestrator(settings, ledger)
            orchestrator.run(project_id)
            first_events = len(ledger.events(project_id))
            orchestrator.run(project_id)
            self.assertEqual(len(ledger.events(project_id)), first_events)
            self.assertEqual(ledger.checkpoint(project_id), "done")


if __name__ == "__main__":
    unittest.main()
