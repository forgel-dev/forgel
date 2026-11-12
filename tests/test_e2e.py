from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.ledger import Ledger, new_project_id
from forgel.orchestrator import Orchestrator, StageError
from forgel.sync import reconcile_project, sync_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class EndToEndTest(unittest.TestCase):
    def test_pipeline_reaches_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
                qa_runtime="local",
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
                (workspace / "docs/program/iterations/1/close.md").exists()
            )
            self.assertTrue(
                (workspace / "docs/program/complexity/report.md").exists()
            )
            self.assertTrue(
                (workspace / "docs/program/acceptance/0001_hello-web.md").exists()
            )
            self.assertTrue((workspace / "api/app.py").exists())
            self.assertTrue((workspace / "web/index.html").exists())
            self.assertTrue((workspace / "e2e/check.py").exists())
            self.assertTrue((workspace / "Dockerfile").exists())
            self.assertTrue((workspace / "docker/docker-compose.qa.yml").exists())
            self.assertTrue((workspace / "qa/runner.mjs").exists())
            self.assertTrue((workspace / "qa/scenarios/hello_web.mjs").exists())
            self.assertTrue((workspace / "FORGEL.md").exists())
            self.assertTrue((workspace / "AGENTS.md").exists())
            self.assertTrue((workspace / "forgel.toml").exists())
            config = (workspace / "forgel.toml").read_text(encoding="utf-8")
            self.assertIn('name = "hello-web"', config)
            self.assertIn('recipe = "hello-web@0.1.0"', config)
            self.assertIn("[release]", config)
            self.assertIn("auto_patch = false", config)
            self.assertIn("propose_minor = false", config)
            self.assertIn("[refactoring]", config)
            self.assertIn("budget_percent = 10", config)
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
            self.assertIn("**Runtime:** local", qa)
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
                qa_runtime="local",
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

    def test_sync_starts_new_generation_after_external_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
                qa_runtime="local",
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

            orchestrator = Orchestrator(settings, ledger)
            orchestrator.run(project_id)
            self.assertEqual(ledger.checkpoint_state(project_id), ("done", 1))
            self.assertTrue((workspace / ".git").exists())

            index = workspace / "web" / "index.html"
            index.write_text(
                index.read_text(encoding="utf-8") + "\n<!-- external edit -->\n",
                encoding="utf-8",
            )

            result = sync_project(
                workspace, ledger, project_id, from_stage="review"
            )
            self.assertFalse(result["started"])
            self.assertTrue(result["pending"])
            self.assertTrue(
                (workspace / "docs" / "program" / "reconciliation.md").exists()
            )
            with self.assertRaises(StageError):
                orchestrator.run(project_id)

            changes = workspace / "docs" / "program" / "external-changes.md"
            self.assertTrue(changes.exists())
            self.assertIn("web/index.html", changes.read_text(encoding="utf-8"))

            result = reconcile_project(
                workspace,
                ledger,
                project_id,
                decision="accept",
                notes="accepted external edit",
            )
            self.assertTrue(result["started"])
            self.assertEqual(result["generation"], 2)
            self.assertEqual(ledger.checkpoint_state(project_id), ("review", 2))

            spec = (
                workspace
                / "docs"
                / "program"
                / "features"
                / "20261113000000_hello_web.md"
            ).read_text(encoding="utf-8")
            self.assertIn("External Change", spec)

            orchestrator.run(project_id)
            self.assertEqual(ledger.checkpoint_state(project_id), ("done", 2))
            for stage in ("review", "qa", "acceptance", "audit", "done"):
                self.assertTrue(
                    ledger.has_completed(project_id, stage, 2),
                    f"stage {stage} did not run in generation 2",
                )
            self.assertTrue(ledger.has_completed(project_id, "review", 1))

    def test_rollback_restores_the_external_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
                qa_runtime="local",
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id, "hello-web", "A minimal web app.", str(workspace)
            )

            orchestrator = Orchestrator(settings, ledger)
            orchestrator.run(project_id)

            index = workspace / "web" / "index.html"
            original = index.read_text(encoding="utf-8")
            index.write_text(
                original + "\n<!-- external edit -->\n", encoding="utf-8"
            )

            sync_project(workspace, ledger, project_id, from_stage="review")
            result = reconcile_project(
                workspace,
                ledger,
                project_id,
                decision="rollback",
                notes="revert the external edit",
            )
            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(index.read_text(encoding="utf-8"), original)

            orchestrator.run(project_id)
            self.assertEqual(ledger.checkpoint_state(project_id), ("done", 2))


if __name__ == "__main__":
    unittest.main()
