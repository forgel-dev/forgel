from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.github_flow import (
    GithubFlowError,
    merge_pr,
    publish,
    status_text,
)
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries, write_program
from forgel.project_config import render_project_config
from forgel.projects import create_project
from forgel.providers.github_api import CheckReport
from forgel.providers.github_auth import AuthToken

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class FakeAPI:
    def __init__(self, checks: str = "green") -> None:
        self.checks = checks
        self.created: dict | None = None
        self.ready = False
        self.merged_call: dict | None = None
        self.pull: dict | None = None

    def find_open_pull(self, full_name: str, head: str, base: str) -> None:
        return None

    def create_pull(
        self,
        full_name: str,
        head: str,
        base: str,
        title: str,
        body: str,
        draft: bool,
    ) -> dict:
        self.created = {
            "full_name": full_name,
            "head": head,
            "base": base,
            "title": title,
            "body": body,
            "draft": draft,
        }
        return {
            "number": 7,
            "html_url": "https://github.com/owner/repo/pull/7",
            "draft": draft,
            "merged": False,
        }

    def check_state(self, full_name: str, ref: str) -> CheckReport:
        return CheckReport(self.checks)

    def mark_ready(self, full_name: str, number: int) -> None:
        self.ready = True

    def merge_pull(self, full_name: str, number: int) -> dict:
        self.merged_call = {"full_name": full_name, "number": number}
        return {"merged": True, "sha": "abc123"}

    def get_pull(self, full_name: str, number: int) -> dict:
        return self.pull or {
            "number": number,
            "html_url": f"https://github.com/{full_name}/pull/{number}",
            "head": {"sha": "deadbeef", "ref": "feature"},
            "draft": False,
            "merged": False,
        }


class GithubFlowTest(unittest.TestCase):
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
        self.remote = self.home / "remote.git"
        _run(self.home, "init", "--bare", "-q", str(self.remote))
        _run(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")

    def _setup(self, checks: str = "green", require_ci: bool = True):
        project_id = create_project(
            self.settings,
            self.ledger,
            "demo",
            "A demo repository.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        repo = layout.repo_path("app")
        _run(self.home, "clone", "-q", str(self.remote), str(repo))
        set_entries(
            layout,
            [
                {
                    "id": "app",
                    "role": "application",
                    "provider": "local",
                    "url": str(self.remote),
                    "depends_on": [],
                }
            ],
        )
        write_program(layout, "demo", "")
        write_text(
            layout.control / "forgel.toml",
            render_project_config("demo", git_require_ci=require_ci),
        )
        _run(layout.control, "init", "-q")
        _run(layout.control, "add", "-A")
        _run(
            layout.control,
            "-c",
            "user.name=Forgel",
            "-c",
            "user.email=forgel@localhost",
            "commit",
            "-q",
            "-m",
            "control",
        )
        (repo / "README.md").write_text("hello\n", encoding="utf-8")
        _run(repo, "add", "-A")
        _run(
            repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "initial",
        )
        _run(repo, "push", "origin", "main")
        (repo / "change.txt").write_text("change\n", encoding="utf-8")
        _run(repo, "add", "-A")
        _run(
            repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "change",
        )
        return project, repo, FakeAPI(checks)

    def _publish(self, project, api, **kwargs):
        return publish(
            self.settings,
            self.ledger,
            project,
            api=api,
            auth=AuthToken("token", "pat"),
            full_name_override="owner/repo",
            **kwargs,
        )

    def test_publish_creates_branch_pr_and_merges(self) -> None:
        project, repo, api = self._setup()
        result = self._publish(project, api)
        self.assertEqual(result.status, "merged")
        self.assertTrue(result.merged)
        self.assertEqual(result.checks, "green")
        self.assertEqual(result.pr_number, 7)
        assert api.created is not None
        self.assertEqual(api.created["base"], "main")
        self.assertTrue(api.created["head"].startswith("owner:forgel/"))
        self.assertTrue(api.created["draft"])
        self.assertTrue(api.ready)
        assert api.merged_call is not None
        self.assertEqual(api.merged_call["number"], 7)
        self.assertEqual(result.merge_sha, "abc123")

        branches = _run(
            self.remote, "branch", "--list", result.branch
        ).stdout
        self.assertIn(result.branch, branches)

        layout = ProjectLayout.detect(project["workspace"])
        report = layout.artifact("docs/program/git/report.md")
        self.assertTrue(report.exists())
        self.assertIn("pull/7", report.read_text(encoding="utf-8"))
        events = self.ledger.events(project["id"])
        github_events = [
            event for event in events if event["stage"] == "github"
        ]
        self.assertEqual(len(github_events), 1)
        self.assertEqual(github_events[0]["status"], "merged")

    def test_human_merge_leaves_the_pr_open(self) -> None:
        project, _repo, api = self._setup()
        result = self._publish(project, api, merge="human")
        self.assertEqual(result.status, "pr_open")
        self.assertFalse(result.merged)
        self.assertIsNone(api.merged_call)
        self.assertFalse(api.ready)

    def test_failed_checks_do_not_merge(self) -> None:
        project, _repo, api = self._setup(checks="failed")
        result = self._publish(project, api)
        self.assertEqual(result.status, "checks_failed")
        self.assertFalse(result.merged)
        self.assertIsNone(api.merged_call)

    def test_missing_ci_blocks_auto_merge_by_default(self) -> None:
        project, _repo, api = self._setup(checks="none")
        result = self._publish(project, api)
        self.assertEqual(result.status, "no_ci")
        self.assertFalse(result.merged)

    def test_missing_ci_can_be_allowed_by_config(self) -> None:
        project, _repo, api = self._setup(
            checks="none", require_ci=False
        )
        result = self._publish(project, api)
        self.assertEqual(result.status, "merged")

    def test_dirty_tree_requires_a_commit_message(self) -> None:
        project, repo, api = self._setup()
        (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
        with self.assertRaises(GithubFlowError):
            self._publish(project, api)
        result = self._publish(
            project, api, commit_message="commit dirty work"
        )
        self.assertEqual(result.status, "merged")

    def test_explicit_merge_of_an_existing_pr(self) -> None:
        project, _repo, api = self._setup()
        api.pull = {
            "number": 9,
            "html_url": "https://github.com/owner/repo/pull/9",
            "head": {"sha": "deadbeef", "ref": "feature"},
            "draft": False,
            "merged": False,
        }
        result = merge_pr(
            self.settings,
            self.ledger,
            project,
            number=9,
            api=api,
            auth=AuthToken("token", "pat"),
            full_name_override="owner/repo",
        )
        self.assertEqual(result.status, "merged")
        self.assertEqual(result.pr_number, 9)

    def test_status_text_is_local_only(self) -> None:
        project, _repo, _api = self._setup()
        text = status_text(self.settings, project)
        self.assertIn("merge policy: auto", text)
        self.assertIn("app: local", text)


if __name__ == "__main__":
    unittest.main()
