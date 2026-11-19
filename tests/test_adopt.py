from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.adopt import (
    AdoptError,
    _assert_no_local_environment,
    add_repository,
    adopt_repository,
    extract_control,
    set_dependencies,
)
from forgel.config import Settings
from forgel.daemon import project_state, run_daemon
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import entries
from forgel.projects import create_project
from forgel.providers.github_auth import GithubAuthError
from forgel.sync import reconcile_project, sync_project

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_repo(path: Path, filename: str = "README.md") -> Path:
    path.mkdir(parents=True)
    (path / filename).write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "initial",
        ],
        cwd=path,
        check=True,
    )
    return path


class AdoptTest(unittest.TestCase):
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
        # A test fixture without an origin must never create a real GitHub
        # repository, even when the host has GitHub App credentials.
        self._auth_patch = patch(
            "forgel.adopt.GithubAuth",
            side_effect=GithubAuthError(
                "remote creation disabled in tests"
            ),
        )
        self._auth_patch.start()
        self.addCleanup(self._auth_patch.stop)

    def _source(self, name: str, filename: str = "README.md") -> Path:
        return _make_repo(self.home / "sources" / name, filename)

    def test_adopt_links_the_source_folder_in_place(self) -> None:
        source = self._source("backend")
        result = adopt_repository(
            self.settings,
            self.ledger,
            str(source),
            brief="Backend service",
            name="backend",
        )
        project = self.ledger.get_project(result.project_id)
        assert project is not None
        self.assertEqual(result.repo_id, "main")
        self.assertEqual(result.provider, "local")
        layout = ProjectLayout.detect(project["workspace"])
        self.assertTrue(layout.is_linked)
        self.assertEqual(
            Path(project["workspace"]).resolve(), source.resolve()
        )
        self.assertFalse((source / "repos").exists())
        self.assertTrue((source / ".forgel" / "project.json").exists())
        self.assertEqual(layout.metadata()["mode"], "brownfield")
        self.assertEqual(
            layout.repo_path("main").resolve(), source.resolve()
        )
        self.assertTrue((layout.repo_path("main") / ".git").exists())
        self.assertTrue((layout.control / ".git").exists())
        self.assertTrue((layout.control / "forgel.toml").exists())
        self.assertTrue((layout.control / "FORGEL.md").exists())
        forgel_text = (layout.control / "FORGEL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Repository Summary", forgel_text)
        self.assertIn("hello", forgel_text)
        self.assertIn("README.md", forgel_text)
        self.assertTrue(
            layout.artifact("docs/program/adoption.md").exists()
        )
        self.assertTrue(layout.artifact("docs/program/state.md").exists())

        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: main", program)
        self.assertIn("provider: local", program)
        self.assertIn('recipe: ""', program)
        self.assertIn("depends_on: []", program)

        repo_tags = subprocess.run(
            ["git", "tag"],
            cwd=layout.repo_path("main"),
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        self.assertIn("forgel-baseline", repo_tags)

        events = self.ledger.events(result.project_id)
        self.assertIn("adopt", {event["stage"] for event in events})
        self.assertEqual(
            project_state(self.ledger, project), "adopted"
        )

        run_daemon(
            self.settings, self.ledger, once=True, log=lambda _m: None
        )
        self.assertIsNone(self.ledger.checkpoint(result.project_id))
        self.assertNotIn(
            "intake",
            {event["stage"] for event in self.ledger.events(result.project_id)},
        )

    def test_project_name_comes_from_the_remote_not_the_folder(self) -> None:
        source = self._source("local-folder")
        subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                "git@github.com:forgel-dev/forgel.git",
            ],
            cwd=source,
            check=True,
        )
        adopted = adopt_repository(
            self.settings, self.ledger, str(source)
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        self.assertEqual(project["name"], "forgel")
        toml = (source / "forgel.toml").read_text(encoding="utf-8")
        self.assertIn('name = "forgel"', toml)
        program = (source / "program.yaml").read_text(encoding="utf-8")
        self.assertIn("project: forgel", program)
        diff = subprocess.run(
            ["git", "show", "--format=", "HEAD"],
            cwd=source,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertNotIn("local-folder", diff)
        self.assertNotIn(str(source), diff)

    def test_local_folder_name_is_the_default_without_origin(self) -> None:
        source = self._source("local-folder")
        adopted = adopt_repository(
            self.settings, self.ledger, str(source)
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        self.assertEqual(project["name"], "local-folder")

    def test_adopt_artifacts_do_not_contain_local_paths(self) -> None:
        source = self._source("backend")
        adopt_repository(
            self.settings, self.ledger, str(source), brief="Backend service",
            name="backend",
        )
        diff = subprocess.run(
            ["git", "show", "--format=", "HEAD"],
            cwd=source,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertNotIn(str(source), diff)
        self.assertNotIn(str(Path.home()), diff)

    def test_local_environment_content_is_refused(self) -> None:
        source = self._source("backend")
        leak = source / "leak.md"
        leak.write_text(f"home: {Path.home()}\n", encoding="utf-8")
        with self.assertRaises(AdoptError):
            _assert_no_local_environment(source, ["leak.md"])

    def test_add_repository_records_dependencies(self) -> None:
        backend = adopt_repository(
            self.settings, self.ledger, str(self._source("backend")),
            name="backend",
        )
        project = self.ledger.get_project(backend.project_id)
        assert project is not None
        frontend = add_repository(
            self.settings,
            self.ledger,
            project,
            str(self._source("frontend", "index.html")),
            repo_id="web",
            depends_on=["main"],
        )
        self.assertEqual(frontend.entry["id"], "web")
        self.assertEqual(frontend.entry["depends_on"], ["main"])

        layout = ProjectLayout.detect(project["workspace"])
        self.assertTrue((layout.repo_path("web") / ".git").exists())
        self.assertTrue(
            layout.artifact("docs/program/repos/web.md").exists()
        )
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: web", program)
        self.assertIn("depends_on: [main]", program)
        self.assertEqual(len(entries(layout)), 2)

        infra = add_repository(
            self.settings,
            self.ledger,
            project,
            str(self._source("infra-repo")),
            repo_id="infra",
        )
        self.assertEqual(infra.entry["depends_on"], [])
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: infra", program)
        self.assertEqual(len(entries(layout)), 3)

        # Independent repositories are allowed and the process stays healthy.
        result = sync_project(
            Path(project["workspace"]), self.ledger, project["id"]
        )
        self.assertEqual(result["count"], 0)
        self.assertFalse(result["pending"])

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=layout.control,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        self.assertGreaterEqual(len(log.splitlines()), 3)

    def test_dependency_edges_can_be_changed_and_cleared(self) -> None:
        backend = adopt_repository(
            self.settings, self.ledger, str(self._source("backend")),
            name="backend",
        )
        project = self.ledger.get_project(backend.project_id)
        assert project is not None
        add_repository(
            self.settings,
            self.ledger,
            project,
            str(self._source("frontend")),
            repo_id="web",
        )
        layout = ProjectLayout.detect(project["workspace"])
        updated = set_dependencies(
            self.settings, self.ledger, project, "web", ["main"]
        )
        self.assertEqual(updated["depends_on"], ["main"])
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("depends_on: [main]", program)

        cleared = set_dependencies(
            self.settings, self.ledger, project, "web", []
        )
        self.assertEqual(cleared["depends_on"], [])
        program = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("depends_on: [main]", program)
        self.assertIn("depends_on: []", program)

    def test_duplicate_or_self_dependency_is_rejected(self) -> None:
        backend = adopt_repository(
            self.settings, self.ledger, str(self._source("backend")),
            name="backend",
        )
        project = self.ledger.get_project(backend.project_id)
        assert project is not None
        with self.assertRaises(AdoptError):
            add_repository(
                self.settings,
                self.ledger,
                project,
                str(self._source("frontend")),
                repo_id="main",
            )
        with self.assertRaises(AdoptError):
            add_repository(
                self.settings,
                self.ledger,
                project,
                str(self._source("other")),
                repo_id="api",
                depends_on=["api"],
            )

    def test_template_projects_reject_added_repositories(self) -> None:
        project_id = create_project(
            self.settings, self.ledger, "template", "A template project."
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        with self.assertRaises(AdoptError):
            add_repository(
                self.settings,
                self.ledger,
                project,
                str(self._source("extra")),
            )

    def test_credentials_are_rejected_before_a_project_is_created(self) -> None:
        with self.assertRaises(AdoptError):
            adopt_repository(
                self.settings,
                self.ledger,
                "https://token@github.com/owner/repo",
            )
        self.assertEqual(self.ledger.list_projects(), [])

    def test_state_can_move_to_a_separate_repository(self) -> None:
        source = self._source("backend")
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), name="backend"
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        self.assertEqual(layout.control.resolve(), source.resolve())
        target = self.home / "program-state"
        result = extract_control(
            self.settings, self.ledger, project, str(target)
        )
        self.assertEqual(result.control, str(target.resolve()))
        self.assertIn("forgel.toml", result.moved)
        self.assertTrue((target / "forgel.toml").exists())
        self.assertTrue((target / "docs" / "program").is_dir())
        self.assertTrue((target / ".git").exists())
        self.assertFalse((source / "forgel.toml").exists())
        self.assertFalse((source / "docs" / "program").exists())
        layout = ProjectLayout.detect(project["workspace"])
        self.assertEqual(layout.control.resolve(), target.resolve())
        metadata = json.loads(
            (source / ".forgel" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(metadata["control"], str(target.resolve()))
        program = (target / "program.yaml").read_text(encoding="utf-8")
        self.assertIn("path: ../sources/backend", program)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=source,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        self.assertEqual(status, "")

    def test_brownfield_sync_accept_and_rollback(self) -> None:
        source = self._source("backend")
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), name="backend"
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        readme = layout.repo_path("main") / "README.md"
        readme.write_text("changed\n", encoding="utf-8")

        result = sync_project(
            Path(project["workspace"]), self.ledger, project["id"]
        )
        self.assertTrue(result["pending"])
        self.assertIn("README.md", result["files"])
        self.assertEqual(result["analysis"]["violations"], [])

        decision = reconcile_project(
            Path(project["workspace"]),
            self.ledger,
            project["id"],
            decision="accept",
            notes="accepted",
        )
        self.assertTrue(decision["brownfield"])
        self.assertFalse(decision["started"])
        self.assertEqual(decision["status"], "accepted")
        clean = sync_project(
            Path(project["workspace"]), self.ledger, project["id"]
        )
        self.assertEqual(clean["count"], 0)
        self.assertEqual(
            project_state(self.ledger, project), "adopted"
        )

        readme.write_text("revert me\n", encoding="utf-8")
        sync_project(Path(project["workspace"]), self.ledger, project["id"])
        rolled_back = reconcile_project(
            Path(project["workspace"]),
            self.ledger,
            project["id"],
            decision="rollback",
        )
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertEqual(readme.read_text(encoding="utf-8"), "changed\n")
        self.assertEqual(
            project_state(self.ledger, project), "adopted"
        )

    def test_linked_siblings_are_synced_and_rolled_back(self) -> None:
        backend = adopt_repository(
            self.settings, self.ledger, str(self._source("backend")),
            name="backend",
        )
        project = self.ledger.get_project(backend.project_id)
        assert project is not None
        frontend = self._source("frontend")
        add_repository(
            self.settings,
            self.ledger,
            project,
            str(frontend),
            repo_id="web",
            depends_on=["main"],
        )
        layout = ProjectLayout.detect(project["workspace"])
        readme = frontend / "README.md"
        readme.write_text("changed\n", encoding="utf-8")
        result = sync_project(
            Path(project["workspace"]), self.ledger, project["id"]
        )
        self.assertIn("repos/web/README.md", result["files"])
        self.assertEqual(result["analysis"]["violations"], [])
        rolled_back = reconcile_project(
            Path(project["workspace"]),
            self.ledger,
            project["id"],
            decision="rollback",
        )
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertEqual(readme.read_text(encoding="utf-8"), "hello\n")

    def test_project_metadata_lists_both_repos(self) -> None:
        backend = adopt_repository(
            self.settings, self.ledger, str(self._source("backend")),
            name="backend",
        )
        project = self.ledger.get_project(backend.project_id)
        assert project is not None
        add_repository(
            self.settings,
            self.ledger,
            project,
            str(self._source("frontend")),
            repo_id="web",
            depends_on=["main"],
        )
        metadata = json.loads(
            (
                Path(project["workspace"])
                / ".forgel"
                / "project.json"
            ).read_text(encoding="utf-8")
        )
        ids = [entry["id"] for entry in metadata["repos"]]
        self.assertEqual(ids, ["main", "web"])


if __name__ == "__main__":
    unittest.main()
