from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel import git_ops
from forgel.adopt import AdoptError, create_repository, publish_repository
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import entries, set_entries
from forgel.projects import create_project
from forgel.providers.github_api import GithubAPIError
from forgel.providers.github_auth import AuthToken

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeAPI:
    def __init__(self, existing: bool = False) -> None:
        self.existing = existing
        self.created: list[dict] = []
        self.user_calls = 0

    def user(self) -> dict:
        self.user_calls += 1
        return {"login": "octocat"}

    def create_repo(
        self,
        owner: str,
        name: str,
        private: bool = True,
        description: str = "",
    ) -> dict:
        if self.existing:
            raise GithubAPIError(422, "name already exists")
        self.created.append(
            {
                "owner": owner,
                "name": name,
                "private": private,
                "description": description,
            }
        )
        return {
            "full_name": f"{owner}/{name}",
            "clone_url": f"https://github.com/{owner}/{name}.git",
        }


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class RepoCreateTest(unittest.TestCase):
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
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "Git demo",
            "A demo project for repository creation.",
        )
        self.project = self.ledger.get_project(self.project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])
        self.auth = AuthToken(token="tok", kind="pat")

    def test_create_repository_creates_remote_local_repo_and_entry(self) -> None:
        api = FakeAPI()
        with patch("forgel.adopt.git_ops.push") as pushed:
            result = create_repository(
                self.settings,
                self.ledger,
                self.project,
                "billing",
                org="acme",
                description="Billing service",
                api=api,
                auth=self.auth,
            )
        self.assertEqual(
            api.created,
            [
                {
                    "owner": "acme",
                    "name": "billing",
                    "private": True,
                    "description": "Billing service",
                }
            ],
        )
        self.assertEqual(result.url, "https://github.com/acme/billing.git")
        local = self.layout.repo_path("billing")
        self.assertTrue((local / ".git").is_dir())
        self.assertTrue((local / "README.md").exists())
        self.assertTrue((local / "FORGEL.md").exists())
        self.assertTrue((local / "AGENTS.md").exists())
        self.assertEqual(
            _git(local, "log", "-1", "--format=%s").stdout.strip(),
            "Initialize billing",
        )
        self.assertEqual(
            git_ops.origin_url(local),
            "https://github.com/acme/billing.git",
        )
        entry = next(
            item for item in entries(self.layout) if item["id"] == "billing"
        )
        self.assertEqual(entry["provider"], "github")
        self.assertEqual(entry["url"], "https://github.com/acme/billing.git")
        self.assertIn(
            "billing",
            (self.layout.control / "program.yaml").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            self.layout.artifact("docs/program/repos/billing.md").exists()
        )
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("repo_create", stages)
        pushed.assert_called_once()
        self.assertEqual(pushed.call_args[0][1], "main")

    def test_create_uses_the_user_login_without_an_org(self) -> None:
        api = FakeAPI()
        with patch("forgel.adopt.git_ops.push"):
            result = create_repository(
                self.settings,
                self.ledger,
                self.project,
                "notes",
                api=api,
                auth=self.auth,
            )
        self.assertEqual(api.user_calls, 1)
        self.assertEqual(api.created[0]["owner"], "octocat")
        self.assertEqual(result.entry["provider"], "github")

    def test_an_existing_remote_name_is_reported(self) -> None:
        api = FakeAPI(existing=True)
        with self.assertRaises(AdoptError) as ctx:
            create_repository(
                self.settings,
                self.ledger,
                self.project,
                "billing",
                org="acme",
                api=api,
                auth=self.auth,
            )
        self.assertIn("already exists", str(ctx.exception))
        self.assertFalse(self.layout.repo_path("billing").exists())

    def test_app_credentials_require_an_org(self) -> None:
        with self.assertRaises(AdoptError):
            create_repository(
                self.settings,
                self.ledger,
                self.project,
                "billing",
                api=FakeAPI(),
                auth=AuthToken(token="tok", kind="app"),
            )

    def test_duplicate_repository_id_is_rejected(self) -> None:
        with self.assertRaises(AdoptError):
            create_repository(
                self.settings,
                self.ledger,
                self.project,
                "api",
                org="acme",
                api=FakeAPI(),
                auth=self.auth,
            )

    def test_publish_repository_creates_the_remote_and_updates_the_entry(
        self,
    ) -> None:
        local = self.layout.repo_path("api")
        local.mkdir(parents=True)
        write_text(local / "README.md", "api\n")
        _git(local, "init", "-q", "-b", "main")
        _git(local, "add", "-A")
        _git(
            local,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "initial",
        )
        api = FakeAPI()
        with patch("forgel.adopt.git_ops.push") as pushed:
            result = publish_repository(
                self.settings,
                self.ledger,
                self.project,
                "api",
                org="acme",
                api=api,
                auth=self.auth,
            )
        self.assertEqual(result.entry["url"], "https://github.com/acme/api.git")
        entry = next(
            item for item in entries(self.layout) if item["id"] == "api"
        )
        self.assertEqual(entry["provider"], "github")
        self.assertEqual(
            git_ops.origin_url(local), "https://github.com/acme/api.git"
        )
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("repo_publish", stages)
        pushed.assert_called_once()

    def test_publishing_an_already_published_repo_is_rejected(self) -> None:
        current = entries(self.layout)
        updated = [
            dict(item, url="https://github.com/acme/api.git", provider="github")
            if item["id"] == "api"
            else item
            for item in current
        ]
        set_entries(self.layout, updated)
        with self.assertRaises(AdoptError):
            publish_repository(
                self.settings,
                self.ledger,
                self.project,
                "api",
                api=FakeAPI(),
                auth=self.auth,
            )


if __name__ == "__main__":
    unittest.main()
