from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel import git_ops
from forgel.git_ops import GitOperationError


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class GitOpsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.remote = self.root / "remote.git"
        _run(self.root, "init", "--bare", "-q", str(self.remote))
        _run(
            self.remote,
            "symbolic-ref",
            "HEAD",
            "refs/heads/main",
        )
        self.repo = self.root / "work"
        _run(self.root, "clone", "-q", str(self.remote), str(self.repo))
        _run(
            self.repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "initial",
        )
        git_ops.push(self.repo, "main")

    def test_branch_commit_push_and_basics(self) -> None:
        self.assertEqual(git_ops.current_branch(self.repo), "main")
        self.assertFalse(git_ops.is_dirty(self.repo))
        self.assertEqual(
            git_ops.origin_url(self.repo), str(self.remote)
        )
        git_ops.fetch(self.repo)
        git_ops.create_branch(self.repo, "feature")
        (self.repo / "file.txt").write_text("hello\n", encoding="utf-8")
        git_ops.commit_all(self.repo, "add file")
        self.assertTrue(git_ops.is_dirty(self.repo) is False)
        self.assertIn("add file", git_ops.last_commit_subject(self.repo))
        self.assertTrue(
            git_ops.is_ancestor(self.repo, "origin/main", "HEAD")
        )
        git_ops.push(self.repo, "feature")
        branches = _run(
            self.remote, "branch", "--list", "feature"
        ).stdout
        self.assertIn("feature", branches)

    def test_existing_branch_is_not_recreated(self) -> None:
        with self.assertRaises(GitOperationError):
            git_ops.create_branch(self.repo, "main")

    def test_remote_mismatch_is_rejected(self) -> None:
        with self.assertRaises(GitOperationError):
            git_ops.ensure_remote(
                self.repo, "https://example.com/other.git"
            )

    def test_secret_files_are_not_committed(self) -> None:
        (self.repo / ".env").write_text("TOKEN=x\n", encoding="utf-8")
        with self.assertRaises(GitOperationError):
            git_ops.commit_all(self.repo, "leak")
        self.assertTrue(git_ops.is_dirty(self.repo))

    def test_commit_paths_ignores_a_deleted_untracked_file(self) -> None:
        (self.repo / "keep.txt").write_text("keep\n", encoding="utf-8")
        (self.repo / "temp.yaml").write_text("temp\n", encoding="utf-8")
        (self.repo / "temp.yaml").unlink()
        git_ops.commit_paths(
            self.repo, ["keep.txt", "temp.yaml"], "keep only"
        )
        files = _run(
            self.repo, "show", "--name-only", "--format=", "HEAD"
        ).stdout
        self.assertIn("keep.txt", files)
        self.assertNotIn("temp.yaml", files)

    def test_commit_paths_stages_a_tracked_deletion(self) -> None:
        (self.repo / "gone.txt").write_text("x\n", encoding="utf-8")
        git_ops.commit_paths(self.repo, ["gone.txt"], "add")
        (self.repo / "gone.txt").unlink()
        git_ops.commit_paths(self.repo, ["gone.txt"], "remove")
        files = _run(
            self.repo, "show", "--name-only", "--format=", "HEAD"
        ).stdout
        self.assertIn("gone.txt", files)

    def test_committing_unchanged_paths_is_not_an_error(self) -> None:
        (self.repo / "same.txt").write_text("same\n", encoding="utf-8")
        first = git_ops.commit_paths(
            self.repo, ["same.txt"], "add"
        )
        second = git_ops.commit_paths(
            self.repo, ["same.txt"], "again"
        )
        self.assertEqual(second, first)
        self.assertEqual(second, git_ops.head_sha(self.repo))

    def test_auth_env_does_not_contain_the_raw_token(self) -> None:
        env = git_ops.auth_env("super-secret-token")
        assert env is not None
        self.assertNotIn(
            "super-secret-token", env["GIT_CONFIG_VALUE_0"]
        )

    def test_a_failed_token_falls_back_to_host_credentials(self) -> None:
        _run(
            self.repo,
            "remote",
            "set-url",
            "origin",
            "https://github.com/o/r.git",
        )
        calls: list[dict[str, str] | None] = []

        def fake(repo, *args, env=None, timeout=180.0):
            if tuple(args[:2]) == ("remote", "get-url"):
                return subprocess.CompletedProcess(
                    ["git", *args],
                    0,
                    "https://github.com/o/r.git\n",
                    "",
                )
            calls.append(env)
            return subprocess.CompletedProcess(
                ["git", *args],
                1 if env else 0,
                "",
                "denied" if env else "",
            )

        with patch("forgel.git_ops._run", side_effect=fake):
            git_ops.push(self.repo, "main", "ghp_token")
        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(calls[0])
        self.assertIsNone(calls[1])

    def test_a_failed_https_push_falls_back_to_ssh(self) -> None:
        _run(
            self.repo,
            "remote",
            "set-url",
            "origin",
            "https://github.com/o/r.git",
        )
        calls: list[tuple[str, ...]] = []

        def fake(repo, *args, env=None, timeout=180.0):
            if tuple(args[:2]) == ("remote", "get-url"):
                return subprocess.CompletedProcess(
                    ["git", *args],
                    0,
                    "https://github.com/o/r.git\n",
                    "",
                )
            calls.append(tuple(args))
            code = 0 if args and str(args[1]).startswith("git@") else 1
            return subprocess.CompletedProcess(
                ["git", *args], code, "", "denied" if code else ""
            )

        with patch("forgel.git_ops._run", side_effect=fake):
            git_ops.push(self.repo, "main")
        self.assertTrue(
            any(
                args[1] == "git@github.com:o/r.git"
                for args in calls
                if len(args) > 1
            )
        )
        self.assertEqual(
            git_ops.ssh_url("https://github.com/o/r.git"),
            "git@github.com:o/r.git",
        )


if __name__ == "__main__":
    unittest.main()
