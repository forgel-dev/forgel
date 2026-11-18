from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries, write_program
from forgel.projects import create_project
from forgel.release import ReleaseError, release_project
from forgel.secrets import set_secret

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class FakeReleaseAPI:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None

    def release_for_tag(self, full_name: str, tag: str) -> None:
        return None

    def create_release(
        self,
        full_name: str,
        tag: str,
        target: str,
        name: str = "",
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        generate_notes: bool = False,
    ) -> dict[str, object]:
        self.created = {
            "full_name": full_name,
            "tag": tag,
            "target": target,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
            "generate_notes": generate_notes,
        }
        return {
            "html_url": f"https://github.com/{full_name}/releases/tag/{tag}"
        }


def _no_api_credentials():
    return (
        patch.dict(
            os.environ,
            {
                "FORGEL_GITHUB_TOKEN": "",
                "GITHUB_TOKEN": "",
                "GH_TOKEN": "",
            },
        ),
        patch(
            "forgel.providers.github_auth.GithubAuth.session_token",
            return_value="",
        ),
    )


class ReleaseTest(unittest.TestCase):
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

    def _project(self, url: str = "") -> tuple[dict, ProjectLayout, Path]:
        project_id = create_project(
            self.settings,
            self.ledger,
            "release-demo",
            "A demo project.",
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
                    "provider": "github" if url else "local",
                    "url": url or str(self.remote),
                    "depends_on": [],
                }
            ],
        )
        write_program(layout, "release-demo", "")
        repo.joinpath("README.md").write_text("hello\n", encoding="utf-8")
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
        return project, layout, repo

    def test_a_release_tags_and_pushes_without_an_api_token(self) -> None:
        project, layout, _repo = self._project()
        env_patch, session_patch = _no_api_credentials()
        with env_patch, session_patch:
            result = release_project(
                self.settings,
                self.ledger,
                project,
                version="1.2.3",
                log=lambda _m: None,
            )
        self.assertEqual(result.tag, "v1.2.3")
        self.assertEqual(result.status, "tagged")
        tags = _run(self.remote, "tag", "--list").stdout
        self.assertIn("v1.2.3", tags)
        manifest = layout.artifact("docs/program/releases/v1.2.3.json")
        self.assertTrue(manifest.exists())
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], "v1.2.3")
        self.assertIn("app", data["repos"])

    def test_an_api_release_is_created_when_a_token_exists(self) -> None:
        project, layout, _repo = self._project(
            url="https://github.com/owner/repo.git"
        )
        set_secret(self.home, "github.token", "ghp_test")
        api = FakeReleaseAPI()
        result = release_project(
            self.settings,
            self.ledger,
            project,
            version="2.0.0",
            notes="A release",
            api=api,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "released")
        self.assertEqual(result.repos[0].release_url,
                         "https://github.com/owner/repo/releases/tag/v2.0.0")
        assert api.created is not None
        self.assertEqual(api.created["tag"], "v2.0.0")
        self.assertIn("A release", str(api.created["body"]))
        manifest = layout.artifact("docs/program/releases/v2.0.0.json")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertIn("releases/tag", json.dumps(data))

    def test_a_dirty_repository_cannot_be_released(self) -> None:
        project, _layout, repo = self._project()
        repo.joinpath("README.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(ReleaseError):
            release_project(
                self.settings,
                self.ledger,
                project,
                version="3.0.0",
                log=lambda _m: None,
            )


if __name__ == "__main__":
    unittest.main()
