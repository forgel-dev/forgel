from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.approvals import record_approval
from forgel.complexity import measure_patch
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.orchestrator import Orchestrator
from forgel.projects import create_project
from forgel.sync import reconcile_project, sync_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class ContainerProjectTest(unittest.TestCase):
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

    def _create(self) -> tuple[str, Path, ProjectLayout]:
        project_id = create_project(
            self.settings,
            self.ledger,
            "container-demo",
            "A minimal web app with an index page and a health check.",
        )
        root = self.settings.projects_dir / project_id
        return project_id, root, ProjectLayout.detect(root)

    def _finish(self, orchestrator: Orchestrator, project_id: str) -> None:
        orchestrator.run(project_id)
        record_approval(
            self.ledger, project_id, scope="staging", actor="test"
        )
        orchestrator.run(project_id)

    def test_pipeline_runs_in_a_container(self) -> None:
        project_id, root, layout = self._create()
        self.assertTrue(layout.is_container)
        self.assertTrue((root / "project.json").exists())
        self.assertTrue(layout.control.is_dir())
        self.assertTrue(layout.repos_root.is_dir())

        orchestrator = Orchestrator(self.settings, self.ledger)
        result = orchestrator.run(project_id)
        self.assertEqual(result["approval_required"]["scope"], "staging")

        record_approval(
            self.ledger, project_id, scope="staging", actor="test"
        )
        orchestrator.run(project_id)
        self.assertEqual(self.ledger.checkpoint(project_id), "done")

        self.assertTrue((layout.control / "docs/program/state.md").exists())
        self.assertTrue((layout.control / "staging.json").exists())
        self.assertTrue((layout.control / "forgel.toml").exists())
        self.assertTrue((layout.control / "program.yaml").exists())
        self.assertTrue((layout.repo_path("api") / "app.py").exists())
        self.assertTrue((layout.repo_path("web") / "index.html").exists())
        self.assertTrue(
            (layout.repo_path("infra") / "Dockerfile").exists()
        )
        self.assertTrue(
            (layout.repo_path("e2e") / "qa/runner.mjs").exists()
        )

        git_roots = layout.git_roots()
        names = {path.name for path in git_roots}
        self.assertEqual(names, {"program", "api", "web", "infra", "e2e"})
        for target in git_roots:
            self.assertTrue((target / ".git").is_dir())

        intake = self.ledger.events(project_id)[0]
        refs = json.loads(intake["artifact_refs"])
        self.assertIn("program/forgel.toml", refs)
        self.assertIn("program/docs/program/requirements.json", refs)

        manifest = layout.artifact("docs/program/releases/g1.json")
        self.assertTrue(manifest.exists())
        release = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(
            set(release["repos"]),
            {"program", "repos/api", "repos/web", "repos/infra", "repos/e2e"},
        )
        self.assertEqual(len(release["digest"]), 12)

        staging = json.loads(
            (layout.control / "staging.json").read_text(encoding="utf-8")
        )
        self.assertTrue(staging["command"].endswith("repos/api/app.py"))

    def test_sync_and_rollback_across_repositories(self) -> None:
        project_id, root, layout = self._create()
        orchestrator = Orchestrator(self.settings, self.ledger)
        self._finish(orchestrator, project_id)

        index = layout.repo_path("web") / "index.html"
        original = index.read_text(encoding="utf-8")
        index.write_text(original + "\n<!-- external edit -->\n", encoding="utf-8")

        result = sync_project(root, self.ledger, project_id)
        self.assertFalse(result["started"])
        self.assertTrue(result["pending"])
        self.assertIn("repos/web/index.html", result["files"])
        self.assertTrue(
            layout.artifact("docs/program/reconciliation.md").exists()
        )

        result = reconcile_project(
            root,
            self.ledger,
            project_id,
            decision="rollback",
            notes="revert the external edit",
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(index.read_text(encoding="utf-8"), original)
        self.assertEqual(
            self.ledger.checkpoint_state(project_id), ("review", 2)
        )

        orchestrator.run(project_id)
        record_approval(
            self.ledger, project_id, scope="staging", actor="test"
        )
        orchestrator.run(project_id)
        self.assertEqual(
            self.ledger.checkpoint_state(project_id), ("done", 2)
        )

    def test_complexity_aggregates_repository_patches(self) -> None:
        project_id, root, layout = self._create()
        orchestrator = Orchestrator(self.settings, self.ledger)
        self._finish(orchestrator, project_id)

        app = layout.repo_path("api") / "app.py"
        app.write_text(
            app.read_text(encoding="utf-8") + "\n# external change\n",
            encoding="utf-8",
        )
        metrics = measure_patch(root)
        self.assertGreaterEqual(metrics.added_lines, 1)
        self.assertGreaterEqual(metrics.files_changed, 1)


if __name__ == "__main__":
    unittest.main()
