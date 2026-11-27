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
from forgel.controller import OPERATIONS
from forgel.daemon import run_once
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries, write_program
from forgel.projects import create_project
from forgel.providers.github import GithubProvider
from forgel.release_train import (
    AUDIT_TOTAL_TIMEOUT,
    INITIAL_VERSION,
    UNRESOLVED_RELEASE_DETAIL,
    MAX_AUDIT_ERRORS,
    _audit_client,
    attach_blocked_release,
    discover_base,
    eligible_pending_task,
    list_releases,
    load_release,
    next_version,
    plan_release,
    process_releases,
    release_tasks,
    resume_release,
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
RESPEC_SPEC = {
    "problem": "The work is missing.",
    "outcome": "The work is done.",
    "scope": ["the work"],
    "non_goals": [],
    "requirements": ["The work is done."],
    "acceptance": ["The work works."],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The work exists."],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
    "external_dependencies": [],
}
MINOR_AUDIT = json.dumps(
    {
        "verdict": "fail",
        "summary": "Only style issues remain.",
        "findings": [
            {
                "severity": "minor",
                "repo_id": "web",
                "issue": "The widget import is unused",
                "suggestion": "Remove the unused import",
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
            settings=self.settings,
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

    def test_a_failed_audit_without_blocking_findings_publishes(self) -> None:
        release, _task = self._release()

        actions = process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([MINOR_AUDIT]),
            log=lambda _m: None,
        )

        self.assertIn(f"released:{release['id']}", actions)
        stored = list_releases(self.layout)[0]
        self.assertEqual(stored["status"], "tagged")
        audit = stored.get("audit") or {}
        self.assertEqual(audit.get("verdict"), "fail")
        self.assertEqual(len(audit.get("findings") or []), 1)

    def test_a_cancelled_task_does_not_block_the_release(self) -> None:
        release, _task = self._release()
        cancelled = create_task(
            self.layout,
            "Drop the banner",
            ["Drop the banner"],
            ["The banner is gone"],
            repo_id="web",
            release_id=str(release["id"]),
        )
        update_task(
            self.layout,
            cancelled["id"],
            status="cancelled",
            result={"summary": "cancelled by the user"},
        )

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

    def test_a_release_with_only_cancelled_tasks_is_cancelled(self) -> None:
        release, task = self._release()
        update_task(self.layout, task["id"], status="cancelled")

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([]),
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "cancelled")

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

    def test_a_release_updates_the_runtime_preset_manifest(self) -> None:
        api = self.layout.repo_path("api")
        write_text(
            api / "package.json",
            json.dumps({"name": "api", "version": "1.2.3"}) + "\n",
        )
        write_text(
            api / "README.md",
            "curl https://example/v1.2.3/install.sh | sh\n",
        )
        _run(api, "add", "package.json", "README.md")
        _run(
            api,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "package manifest",
        )
        _run(api, "push", "origin", "main")
        _run(api, "tag", "-a", "v1.2.3", "-m", "v1.2.3")
        _run(api, "push", "origin", "--tags")
        old_tag = _run(api, "rev-parse", "v1.2.3").stdout.strip()
        release, _task = self._release(
            repo_id="api",
            release_id="20261120140000_api",
            title="API change",
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
        self.assertEqual(stored["repos"]["api"]["preset"], "node")
        self.assertEqual(stored["repos"]["api"]["version"], "1.3.0")
        self.assertIn(
            '"version": "1.3.0"',
            (api / "package.json").read_text(encoding="utf-8"),
        )
        remote = _run(
            self.remotes["api"],
            "show",
            "main:package.json",
        ).stdout
        self.assertIn('"version": "1.3.0"', remote)
        self.assertEqual(
            _run(api, "rev-parse", "v1.2.3").stdout.strip(), old_tag
        )
        self.assertIn(
            "v1.3.0", (api / "README.md").read_text(encoding="utf-8")
        )
        self.assertEqual(release["id"], stored["id"])

    def _controller_settings(self) -> Settings:
        return Settings(
            home=self.settings.home,
            registry_path=self.settings.registry_path,
            templates_path=self.settings.templates_path,
            jurisdiction_path=self.settings.jurisdiction_path,
            qa_runtime="local",
        )

    def test_the_controller_queues_a_fix_task_for_audit_findings(
        self,
    ) -> None:
        release, _task = self._release()
        client = ScriptedModelClient(
            [
                FAIL_AUDIT,
                json.dumps(
                    {
                        "operation": "release_fix",
                        "reason": "the widget has no test",
                    }
                ),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
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

    def test_a_rework_decision_queues_fix_tasks(self) -> None:
        release, _task = self._release()
        client = ScriptedModelClient(
            [
                FAIL_AUDIT,
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "the widget has no test",
                        "feedback": ["Add the test"],
                    }
                ),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
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

    def test_an_audit_decision_keeps_the_release_running(self) -> None:
        release, _task = self._release()
        client = ScriptedModelClient(
            [
                FAIL_AUDIT,
                json.dumps(
                    {"operation": "release_audit", "reason": "re-check"}
                ),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")

    def test_an_audit_controller_failure_stops_without_retry(self) -> None:
        release, _task = self._release()
        client = ScriptedModelClient([FAIL_AUDIT])

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertFalse(stored.get("next_at"))
        self.assertEqual(
            stored["last_error"]["stage"], "audit_controller"
        )

    def test_a_stop_decision_blocks_the_release(self) -> None:
        release, _task = self._release()
        client = ScriptedModelClient(
            [
                FAIL_AUDIT,
                json.dumps(
                    {"operation": "stop", "reason": "no viable fix"}
                ),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["detail"], "no viable fix")

    def test_the_controller_asks_the_owner_for_a_blocked_release(
        self,
    ) -> None:
        release, _task = self._release()
        question = "Which widget behavior is wanted?"
        client = ScriptedModelClient(
            [
                FAIL_AUDIT,
                json.dumps(
                    {
                        "operation": "ask_user",
                        "question": question,
                    }
                ),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["detail"], question)

    def test_the_release_state_tree(self) -> None:
        defined = {
            "planned",
            "running",
            "failed",
            "partial",
            "ready",
            "finalizing",
            "tagged",
            "released",
            "blocked",
            "cancelled",
        }
        for release_status in (
            "planned",
            "running",
            "failed",
            "blocked",
            "released",
            "tagged",
        ):
            for task_state in ("pending", "review", "failed", "done"):
                self.setUp()
                release, task = self._release()
                release["status"] = release_status
                save_release(self.layout, release)
                if task_state != "done":
                    update_task(
                        self.layout,
                        str(task["id"]),
                        status=task_state,
                    )
                client = ScriptedModelClient(
                    [
                        PASS_AUDIT,
                        json.dumps(
                            {"operation": "rework", "reason": "again"}
                        ),
                    ]
                )

                process_releases(
                    self.settings,
                    self.ledger,
                    self.project,
                    self.layout,
                    client,
                    log=lambda _m: None,
                )

                stored = load_release(
                    self.layout, str(release["id"])
                )
                assert stored is not None
                self.assertIn(
                    stored["status"],
                    defined,
                    f"{release_status}/{task_state}",
                )

    def test_every_operation_leaves_a_valid_release_on_audit_findings(
        self,
    ) -> None:
        for operation in OPERATIONS:
            self.setUp()
            release, _task = self._release()
            client = ScriptedModelClient(
                [
                    FAIL_AUDIT,
                    json.dumps(
                        {
                            "operation": operation,
                            "reason": "a reason",
                            "question": "a question",
                            "args": {
                                "name": "command_timeout",
                                "seconds": 7200,
                            },
                        }
                    ),
                ]
            )

            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                client,
                log=lambda _m: None,
            )

            stored = load_release(self.layout, str(release["id"]))
            assert stored is not None
            self.assertIn(
                stored["status"],
                {"running", "blocked"},
                operation,
            )

    def test_every_operation_leaves_a_valid_release_on_a_failed_task(
        self,
    ) -> None:
        for operation in OPERATIONS:
            self.setUp()
            release, task = self._release()
            update_task(
                self.layout,
                str(task["id"]),
                status="failed",
                result={
                    "summary": "broken",
                    "failure": {
                        "kind": "qa",
                        "message": "the test failed",
                    },
                },
            )
            client = ScriptedModelClient(
                [
                    json.dumps(
                        {
                            "operation": operation,
                            "reason": "a reason",
                            "question": "a question",
                            "args": {
                                "name": "command_timeout",
                                "seconds": 7200,
                            },
                        }
                    )
                ]
            )

            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                client,
                log=lambda _m: None,
            )

            stored = load_release(self.layout, str(release["id"]))
            assert stored is not None
            self.assertIn(
                stored["status"],
                {"running", "blocked", "failed"},
                operation,
            )
            again = get_task(self.layout, str(task["id"]))
            assert again is not None
            self.assertIn(
                again["status"],
                {"pending", "failed", "blocked"},
                operation,
            )

    def test_the_release_controller_receives_inactive_task_specs(
        self,
    ) -> None:
        done = create_task(
            self.layout,
            "Finished work",
            ["Ship the finished work"],
            ["The finished work runs"],
            repo_id="web",
            spec="docs/program/specs/done.md",
            release_id="20261125120000_blocked-spec",
            release_class="minor",
        )
        write_text(
            self.layout.artifact("docs/program/specs/done.md"),
            "DONE-SPEC-MARKER",
        )
        update_task(
            self.layout,
            str(done["id"]),
            status="done",
            result={
                "acceptance": {
                    "status": "accepted",
                    "actor": "auto",
                    "at": "2026-11-25T00:00:00+00:00",
                    "notes": "",
                }
            },
        )
        done_stored = get_task(self.layout, str(done["id"]))
        assert done_stored is not None
        task = create_task(
            self.layout,
            "Blocked installer",
            ["Ship the installer"],
            ["The installer runs"],
            repo_id="web",
            spec="docs/program/specs/blocked.md",
            release_id="20261125120000_blocked-spec",
            release_class="minor",
        )
        write_text(
            self.layout.artifact("docs/program/specs/blocked.md"),
            "RELEASE-SPEC-MARKER",
        )
        update_task(
            self.layout,
            str(task["id"]),
            status="blocked",
            result={
                "summary": (
                    "blocked: the dependency scout exceeded its step limit"
                ),
                "blocked_by": "decision",
            },
        )
        stored = get_task(self.layout, str(task["id"]))
        assert stored is not None
        release = plan_release(
            self.layout,
            self.project,
            "20261125120000_blocked-spec",
            title="Blocked installer",
            request="Blocked installer",
            release_class="minor",
            task_items=[done_stored, stored],
            ledger=self.ledger,
            settings=self.settings,
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"operation": "stop", "reason": "seen the spec"}
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        prompt = client.requests[0][1].content
        self.assertIn("DONE-SPEC-MARKER", prompt)
        self.assertIn("RELEASE-SPEC-MARKER", prompt)
        stored_release = load_release(
            self.layout, str(release["id"])
        )
        assert stored_release is not None
        self.assertEqual(stored_release["status"], "blocked")

    def test_a_respec_decision_rewrites_and_requeues_the_task(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {
                    "kind": "qa",
                    "message": "the specification is incomplete",
                },
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "respec",
                        "issue": (
                            "The specification must describe the widget "
                            "behavior."
                        ),
                        "reason": "the current specification is incomplete",
                    }
                ),
                json.dumps(RESPEC_SPEC),
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = get_task(self.layout, str(task["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(
            stored["requirements"], RESPEC_SPEC["requirements"]
        )
        spec_path = self.layout.artifact(
            f"docs/program/specs/{task['id']}.md"
        )
        self.assertIn(
            "The work is done.", spec_path.read_text(encoding="utf-8")
        )
        stored_release = load_release(
            self.layout, str(release["id"])
        )
        assert stored_release is not None
        self.assertEqual(stored_release["status"], "running")
        self.assertIn(
            "The current specification is",
            client.requests[1][-1].content,
        )
        self.assertIn(
            "The specification must describe the widget behavior.",
            client.requests[1][-1].content,
        )

    def test_process_releases_builds_a_client_for_the_controller(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "retry the task",
                    }
                )
            ]
        )
        with patch(
            "forgel.release_train.build_model_client",
            return_value=client,
        ) as build:
            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                None,
                log=lambda _m: None,
            )
        build.assert_called_once()
        stored_release = load_release(
            self.layout, str(release["id"])
        )
        assert stored_release is not None
        self.assertEqual(stored_release["status"], "running")
        stored = get_task(self.layout, str(task["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "pending")

    def test_a_controller_handoff_keeps_the_runtime_active(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="blocked",
            result={
                "summary": "blocked: the dependency scout stopped",
                "blocked_by": "decision",
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "respec",
                        "issue": "rewrite the task scope",
                    }
                )
            ]
        )
        with patch(
            "forgel.runtime_ops.run_operation",
            side_effect=RuntimeError("RESPEC-ERROR-MARKER"),
        ):
            processed = run_once(
                self.settings,
                self.ledger,
                client=client,
                log=lambda _m: None,
            )

        self.assertIn(self.project["id"], processed)
        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")
        self.assertEqual(stored["last_error"]["stage"], "respec")

    def test_a_controller_failure_stops_without_retry(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        actions = process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([]),
            log=lambda _m: None,
        )
        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertFalse(stored.get("next_at"))
        self.assertEqual(stored["last_error"]["stage"], "controller")
        self.assertIn(f"failed:{release['id']}", actions)

    def test_an_unresolved_release_block_is_retried(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        release["status"] = "blocked"
        release["detail"] = UNRESOLVED_RELEASE_DETAIL
        save_release(self.layout, release)
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "retry the task",
                    }
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")
        stored_task = get_task(self.layout, str(task["id"]))
        assert stored_task is not None
        self.assertEqual(stored_task["status"], "pending")

    def test_a_release_without_a_model_blocks_with_a_clear_reason(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        with patch(
            "forgel.release_train.build_model_client",
            return_value=None,
        ):
            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                None,
                log=lambda _m: None,
            )
        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertIn(
            "no model is configured", str(stored.get("detail"))
        )

    def test_a_failed_respec_is_handed_to_the_controller(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="blocked",
            result={
                "summary": "blocked: the dependency scout stopped",
                "blocked_by": "decision",
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "respec",
                        "issue": "rewrite the task scope",
                    }
                )
            ]
        )
        with patch(
            "forgel.runtime_ops.run_operation",
            side_effect=RuntimeError("RESPEC-ERROR-MARKER"),
        ):
            actions = process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                client,
                log=lambda _m: None,
            )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")
        self.assertFalse(stored.get("next_at"))
        self.assertEqual(stored["last_error"]["stage"], "respec")
        self.assertIn(
            "RESPEC-ERROR-MARKER", stored["last_error"]["message"]
        )
        self.assertIn(f"controller:{release['id']}", actions)
        again = get_task(self.layout, str(task["id"]))
        assert again is not None
        self.assertEqual(again["status"], "blocked")
        second = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "try another step",
                    }
                )
            ]
        )
        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            second,
            log=lambda _m: None,
        )
        self.assertIn(
            "RESPEC-ERROR-MARKER", second.requests[0][-1].content
        )

    def test_the_controller_can_stop_after_an_internal_error(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="blocked",
            result={
                "summary": "blocked: the dependency scout stopped",
                "blocked_by": "decision",
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "respec",
                        "issue": "rewrite the task scope",
                    }
                )
            ]
        )
        with patch(
            "forgel.runtime_ops.run_operation",
            side_effect=RuntimeError("RESPEC-ERROR-MARKER"),
        ):
            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                client,
                log=lambda _m: None,
            )
        reason = "the same writer failure is unavoidable"
        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient(
                [
                    json.dumps(
                        {"operation": "block", "reason": reason}
                    )
                ]
            ),
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["detail"], reason)
        self.assertFalse(stored.get("next_at"))
        self.assertNotIn("last_error", stored)

    def test_a_bad_set_limit_is_handed_to_the_controller(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "agent", "message": "bad limit"},
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "set_limit",
                        "reason": "raise the limit",
                        "args": {
                            "name": "command_timeout",
                            "seconds": "not-a-number",
                        },
                    }
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")
        self.assertFalse(stored.get("next_at"))
        self.assertEqual(stored["last_error"]["stage"], "set_limit")
        self.assertIn("positive number", stored["last_error"]["message"])

    def test_the_controller_receives_the_last_internal_error(
        self,
    ) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "agent", "message": "failed"},
            },
        )
        release["last_error"] = {
            "stage": "respec",
            "task": str(task["id"]),
            "message": "LAST-ERROR-MARKER",
            "retries": 1,
            "at": "2026-11-25T17:02:26+00:00",
        }
        save_release(self.layout, release)
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "try another step",
                    }
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        self.assertIn(
            "LAST-ERROR-MARKER", client.requests[0][-1].content
        )

    def test_a_failed_release_task_goes_back_to_work(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "rework",
                        "reason": "redo the work",
                        "feedback": ["Fix the failing test"],
                    }
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")
        again = get_task(self.layout, str(task["id"]))
        assert again is not None
        self.assertEqual(again["status"], "pending")
        self.assertEqual(
            again["result"]["feedback"], ["Fix the failing test"]
        )

    def test_a_failed_release_task_can_be_stopped(self) -> None:
        release, task = self._release()
        update_task(
            self.layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "broken",
                "failure": {"kind": "qa", "message": "the test failed"},
            },
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "operation": "stop",
                        "reason": "the work cannot be fixed",
                    }
                )
            ]
        )

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            client,
            log=lambda _m: None,
        )

        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["detail"], "the work cannot be fixed")

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

    def test_a_stopped_release_returns_to_the_train(self) -> None:
        release, _task = self._release()
        release["status"] = "blocked"
        release["detail"] = "the audit could not run"
        release["audit"] = {
            "rounds": 2,
            "verdict": "error",
            "summary": "the audit could not run",
        }
        save_release(self.layout, release)

        resumed = resume_release(
            self.layout, str(release["id"])
        )

        self.assertEqual(resumed["status"], "running")
        self.assertEqual(resumed["detail"], "")
        self.assertEqual(resumed["audit"]["rounds"], 0)
        self.assertEqual(resumed["audit"]["verdict"], "")
        stored = load_release(self.layout, str(release["id"]))
        assert stored is not None
        self.assertEqual(stored["status"], "running")

    def test_a_published_release_is_not_resumed(self) -> None:
        release, _task = self._release()
        release["status"] = "blocked"
        for data in (release.get("repos") or {}).values():
            data["status"] = "released"
        save_release(self.layout, release)

        with self.assertRaises(ValueError):
            resume_release(self.layout, str(release["id"]))

    def test_the_audit_gets_a_longer_deadline(self) -> None:
        scripted = ScriptedModelClient([])
        self.assertIs(_audit_client(scripted), scripted)

        from forgel.model import ModelConfig, OpenAICompatibleClient

        client = OpenAICompatibleClient(
            ModelConfig(
                base_url="http://example.test",
                api_key="k",
                total_timeout=300.0,
            )
        )
        audited = _audit_client(client)
        self.assertEqual(
            audited.config.total_timeout, AUDIT_TOTAL_TIMEOUT
        )
        self.assertEqual(
            audited.config.timeout, AUDIT_TOTAL_TIMEOUT
        )

    def test_an_audit_error_does_not_consume_a_round(self) -> None:
        release, _task = self._release()
        release_id = str(release["id"])

        process_releases(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            ScriptedModelClient([]),
            log=lambda _m: None,
        )

        stored = load_release(self.layout, release_id)
        assert stored is not None
        audit = stored.get("audit") or {}
        self.assertEqual(audit.get("verdict"), "error")
        self.assertEqual(audit.get("rounds"), 0)
        self.assertEqual(audit.get("errors"), 1)
        self.assertNotEqual(stored.get("status"), "blocked")

    def test_repeated_audit_errors_block_the_release(self) -> None:
        release, _task = self._release()
        release_id = str(release["id"])

        for _ in range(MAX_AUDIT_ERRORS):
            process_releases(
                self.settings,
                self.ledger,
                self.project,
                self.layout,
                ScriptedModelClient([]),
                log=lambda _m: None,
            )

        stored = load_release(self.layout, release_id)
        assert stored is not None
        self.assertEqual(stored.get("status"), "blocked")


if __name__ == "__main__":
    unittest.main()
