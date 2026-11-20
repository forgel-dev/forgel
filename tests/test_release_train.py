from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.daemon import run_once
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries, write_program
from forgel.projects import create_project
from forgel.providers.github import GithubProvider
from forgel.release_train import (
    INITIAL_VERSION,
    attach_blocked_release,
    discover_base,
    eligible_pending_task,
    list_releases,
    next_version,
    plan_release,
    process_releases,
    release_tasks,
    save_release,
)
from forgel.tasks import create_task, get_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]

PASS_AUDIT = json.dumps(
    {
        "verdict": "pass",
        "summary": "The change set is coherent and tested.",
        "findings": [],
    }
)
FAIL_AUDIT = json.dumps(
    {
        "verdict": "fail",
        "summary": "The widget has no test.",
        "findings": [
            {
                "severity": "critical",
                "repo_id": "web",
                "issue": "The widget has no test",
                "suggestion": "Add a test that renders the widget",
            }
        ],
    }
)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


class FakeGithub(GithubProvider):
    def parse(self, url: str):  # noqa: ANN201 - test double
        return SimpleNamespace(slug="owner/repo")

    def release(self, *args, **kwargs):  # noqa: ANN002, ANN003
        tag = args[2]
        return {
            "html_url": f"https://github.com/owner/repo/releases/tag/{tag}"
        }


class FakeAuth:
    def __init__(self, home: Path) -> None:
        self.home = home

    def resolve(self, mode: str = "auto"):  # noqa: ANN201
        return SimpleNamespace(token="ghp_test")


class ReleaseTrainTest(unittest.TestCase):
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
        project_id = create_project(
            self.settings,
            self.ledger,
            "release-train",
            "A two-repository project.",
            mode="brownfield",
        )
        self.project = self.ledger.get_project(project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])
        self.remotes: dict[str, Path] = {}
        for repo_id in ("api", "web"):
            bare = self.home / f"{repo_id}.git"
            _run(self.home, "init", "--bare", "-q", str(bare))
            _run(bare, "symbolic-ref", "HEAD", "refs/heads/main")
            self.remotes[repo_id] = bare
        set_entries(
            self.layout,
            [
                {
                    "id": "api",
                    "role": "application",
                    "provider": "local",
                    "url": str(self.remotes["api"]),
                    "depends_on": [],
                },
                {
                    "id": "web",
                    "role": "frontend",
                    "provider": "local",
                    "url": str(self.remotes["web"]),
                    "depends_on": ["api"],
                },
            ],
        )
        write_program(self.layout, "release-train", "")
        for repo_id in ("api", "web"):
            repo = self.layout.repo_path(repo_id)
            _run(self.home, "clone", "-q", str(self.remotes[repo_id]), str(repo))
            write_text(repo / "README.md", f"{repo_id}\n")
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
        web = self.layout.repo_path("web")
        write_text(
            web / "CHANGELOG.md",
            "# Changelog\n\n## [1.8.5] - 2026-11-01\n\n### Fixed\n\n- one\n",
        )
        _run(web, "add", "CHANGELOG.md")
        _run(
            web,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "changelog",
        )
        _run(web, "tag", "-a", "v1.8.5", "-m", "v1.8.5")
        _run(web, "push", "origin", "main", "--tags")

    def _release(
        self,
        repo_id: str = "web",
        release_class: str = "minor",
        release_id: str = "20261120120000_widget",
        title: str = "Add a widget",
    ) -> tuple[dict, dict]:
        task = create_task(
            self.layout,
            title,
            ["Add a widget"],
            ["The widget is rendered"],
            repo_id=repo_id,
            release_id=release_id,
            release_class=release_class,
            summary="Adds a widget to the page",
        )
        repo = self.layout.repo_path(repo_id)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        update_task(
            self.layout,
            str(task["id"]),
            status="done",
            result={
                "acceptance": {
                    "status": "accepted",
                    "actor": "auto",
                    "at": "2026-11-20T00:00:00+00:00",
                    "notes": "",
                },
                "files_changed": [],
                "git": {"base": sha, "head": sha},
                "qa": {"status": "pass"},
                "review": {"status": "pass"},
            },
        )
        stored = get_task(self.layout, str(task["id"]))
        assert stored is not None
        release = plan_release(
            self.layout,
            self.project,
            release_id,
            title=title,
            request=title,
            release_class=release_class,
            task_items=[stored],
            ledger=self.ledger,
        )
        return release, stored

    def test_version_rules(self) -> None:
        self.assertEqual(next_version(None, "minor"), INITIAL_VERSION)
        self.assertEqual(next_version(None, "patch"), INITIAL_VERSION)
        self.assertEqual(next_version("0.1.0", "patch"), "0.1.1")
        self.assertEqual(next_version("0.1.0", "minor"), "0.2.0")
        self.assertEqual(next_version("1.8.5", "minor"), "1.9.0")
        self.assertEqual(next_version("1.8.5", "patch"), "1.8.6")
        self.assertEqual(next_version("0.5.0", "major"), "1.0.0")
        self.assertEqual(next_version("1.8.5", "major"), "2.0.0")

    def test_base_version_comes_from_tags_or_changelog(self) -> None:
        api_base, _ = discover_base(self.layout.repo_path("api"))
        web_base, source = discover_base(self.layout.repo_path("web"))
        self.assertIsNone(api_base)
        self.assertEqual(web_base, "1.8.5")
        self.assertIn("1.8.5", source)

    def test_a_passing_audit_publishes_one_version_per_repository(self) -> None:
        release, _task = self._release()

        actions = process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )

        self.assertIn(f"released:{release['id']}", actions)
        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["status"], "tagged")
        self.assertEqual(stored["repos"]["web"]["version"], "1.9.0")
        tags = _run(self.remotes["web"], "tag", "--list").stdout
        self.assertIn("v1.9.0", tags)
        changelog = (
            self.layout.repo_path("web") / "CHANGELOG.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## [1.9.0]", changelog)
        self.assertIn("Add a widget", changelog)
        self.assertIn("## [1.8.5]", changelog)
        plan = (
            self.layout.repo_path("web")
            / "releases"
            / "1.9.0"
            / "plan.md"
        )
        self.assertTrue(plan.exists())
        audit = (
            self.layout.artifact(
                f"docs/program/releases/{release['id']}/audit.md"
            )
        )
        self.assertTrue(audit.exists())
        self.assertIn("pass", audit.read_text(encoding="utf-8"))

    def test_a_request_across_two_repositories_releases_both(self) -> None:
        api_task = create_task(
            self.layout,
            "Expose the widget API",
            ["Add the endpoint"],
            ["The endpoint answers"],
            repo_id="api",
            release_id="20261120120000_widget",
            release_class="minor",
            summary="Adds the endpoint",
        )
        web_task = create_task(
            self.layout,
            "Render the widget",
            ["Render the widget"],
            ["The widget is rendered"],
            repo_id="web",
            release_id="20261120120000_widget",
            release_class="minor",
            summary="Renders the widget",
        )
        for task in (api_task, web_task):
            repo = self.layout.repo_path(str(task["repo_id"]))
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            update_task(
                self.layout,
                str(task["id"]),
                status="done",
                result={
                    "acceptance": {
                        "status": "accepted",
                        "actor": "auto",
                        "at": "2026-11-20T00:00:00+00:00",
                        "notes": "",
                    },
                    "files_changed": [],
                    "git": {"base": sha, "head": sha},
                },
            )
        items = [
            get_task(self.layout, str(task["id"])) for task in (api_task, web_task)
        ]
        release = plan_release(
            self.layout,
            self.project,
            "20261120120000_widget",
            title="Widget across the stack",
            request="Widget across the stack",
            release_class="minor",
            task_items=[item for item in items if item],
            ledger=self.ledger,
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )

        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["repos"]["api"]["version"], "0.1.0")
        self.assertEqual(stored["repos"]["web"]["version"], "1.9.0")
        self.assertEqual(stored["repos"]["api"]["status"], "tagged")
        self.assertEqual(stored["repos"]["web"]["status"], "tagged")
        self.assertIn(
            "v0.1.0",
            _run(self.remotes["api"], "tag", "--list").stdout,
        )
        self.assertIn(
            "v1.9.0",
            _run(self.remotes["web"], "tag", "--list").stdout,
        )

    def test_a_github_release_is_created_when_a_provider_is_available(self) -> None:
        release, _task = self._release()

        with patch(
            "forgel.release_train.get_provider",
            return_value=FakeGithub(),
        ), patch("forgel.release_train.GithubAuth", FakeAuth):
            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                ScriptedModelClient([PASS_AUDIT]),
                log=lambda _m: None,
            )

        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["status"], "released")
        self.assertEqual(
            stored["repos"]["web"]["release"],
            "https://github.com/owner/repo/releases/tag/v1.9.0",
        )

    def test_the_daemon_publishes_a_ready_release(self) -> None:
        release, _task = self._release()

        processed = run_once(
            self.settings,
            self.ledger,
            client=ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )

        self.assertIn(self.project["id"], processed)
        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["id"], release["id"])
        self.assertEqual(stored["status"], "tagged")
        self.assertIn(
            "v1.9.0",
            _run(self.remotes["web"], "tag", "--list").stdout,
        )

    def test_an_unreleased_changelog_version_is_used(self) -> None:
        web = self.layout.repo_path("web")
        text = (web / "CHANGELOG.md").read_text(encoding="utf-8")
        write_text(
            web / "CHANGELOG.md",
            text.replace(
                "## [1.8.5]",
                "## [2.4.0] - Unreleased\n\n### Added\n\n- next\n\n## [1.8.5]",
            ),
        )
        _run(web, "add", "CHANGELOG.md")
        _run(
            web,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "next version",
        )
        release, _task = self._release(release_class="patch")

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )

        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["repos"]["web"]["version"], "2.4.0")
        self.assertEqual(stored["repos"]["web"]["base_version"], "1.8.5")
        text = (web / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [2.4.0] - ", text)
        self.assertNotIn("Unreleased", text)
        self.assertIn("- next", text)
        self.assertIn("Add a widget", text)

    def test_a_blocked_release_blocks_only_its_repository(self) -> None:
        blocked_release, blocked_task = self._release(
            repo_id="web",
            release_id="20261120120000_web",
            title="Blocked web change",
        )
        blocked_release["status"] = "blocked"
        save_release(self.layout, blocked_release)
        api_task = create_task(
            self.layout,
            "API change",
            ["Change the API"],
            ["The API changed"],
            repo_id="api",
            release_id="20261120130000_api",
            release_class="minor",
        )
        plan_release(
            self.layout,
            self.project,
            "20261120130000_api",
            title="API change",
            request="API change",
            release_class="minor",
            task_items=[api_task],
            ledger=self.ledger,
        )

        eligible = eligible_pending_task(self.layout)

        assert eligible is not None
        self.assertEqual(eligible["repo_id"], "api")
        self.assertNotEqual(eligible["id"], blocked_task["id"])

    def test_a_new_task_joins_a_blocked_release_for_the_same_repository(
        self,
    ) -> None:
        release, _task = self._release(
            repo_id="web",
            release_id="20261120120000_web",
            title="Blocked web change",
        )
        release["status"] = "blocked"
        save_release(self.layout, release)
        follow_up = create_task(
            self.layout,
            "Fix the audit finding",
            ["Fix it"],
            ["It is fixed"],
            repo_id="web",
            release_id="20261120130000_follow",
            release_class="patch",
        )

        attached = attach_blocked_release(
            self.layout, self.project, follow_up
        )

        self.assertEqual(attached, release["id"])
        stored = get_task(self.layout, str(follow_up["id"]))
        assert stored is not None
        self.assertEqual(stored["release_id"], release["id"])
        reopened = list_releases(self.layout)[0]
        self.assertEqual(reopened["status"], "running")
        self.assertIn(
            str(follow_up["id"]),
            [str(task["id"]) for task in release_tasks(self.layout, release["id"])],
        )

    def test_a_disjoint_release_publishes_while_another_waits(self) -> None:
        web_task = create_task(
            self.layout,
            "Pending web work",
            ["Do web work"],
            ["Web work is done"],
            repo_id="web",
            release_id="20261120120000_web",
            release_class="minor",
        )
        plan_release(
            self.layout,
            self.project,
            "20261120120000_web",
            title="Web work",
            request="Web work",
            release_class="minor",
            task_items=[web_task],
            ledger=self.ledger,
        )
        api_release, _api_task = self._release(
            repo_id="api",
            release_id="20261120130000_api",
            title="API work",
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )

        releases = {
            release["id"]: release for release in list_releases(self.layout)
        }
        self.assertEqual(releases["20261120120000_web"]["status"], "planned")
        self.assertIn(
            releases[api_release["id"]]["status"], {"tagged", "released"}
        )

    def test_a_failing_audit_queues_a_fix_task(self) -> None:
        release, _task = self._release()

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([FAIL_AUDIT]),
            log=lambda _m: None,
        )

        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["status"], "running")
        fix_tasks = [
            task
            for task in release_tasks(self.layout, str(release["id"]))
            if task.get("status") == "pending"
            and str(task.get("title") or "").startswith("Release audit:")
        ]
        self.assertEqual(len(fix_tasks), 1)
        self.assertEqual(fix_tasks[0]["repo_id"], "web")
        self.assertIn(
            "widget has no test",
            " ".join(fix_tasks[0]["requirements"]),
        )

    def test_a_release_waits_for_its_own_tasks(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="pending",
            result={},
        )
        actions = process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([PASS_AUDIT]),
            log=lambda _m: None,
        )
        self.assertEqual(actions, [])
        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["status"], "planned")


if __name__ == "__main__":
    unittest.main()
