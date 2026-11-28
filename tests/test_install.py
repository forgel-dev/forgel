"""The engine's one-command installer, driven end to end.

Every test runs the real ``install.sh`` with an isolated home directory and a
target source tree, so no network, no other user and no shared location is
touched. The engine the installer reports about is then asked for its own
version, which is the value the contract promises.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "install.sh"
DECLARED = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]
SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class InstallerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="forgel-install-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.root = self.home / ".local/share/forgel"
        self.bin = self.home / ".local/bin"

    def _env(self, **extra: str) -> dict[str, str]:
        env = {
            "HOME": str(self.home),
            "PATH": SYSTEM_PATH,
            "SHELL": "/bin/sh",
            "LC_ALL": "C",
            "FORGEL_SOURCE": str(REPO),
            "FORGEL_REF": "latest",
            "FORGEL_PYTHON": sys.executable,
            "FORGEL_INSTALL_ROOT": str(self.root),
            "FORGEL_BIN_DIR": str(self.bin),
        }
        env.update(extra)
        return env

    def _run(self, *arguments: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["sh", str(SCRIPT), *arguments],
            env=self._env(**env),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=600,
        )

    def _terminal(self) -> str:
        """What a newly started terminal session reaches by name."""

        completed = subprocess.run(
            ["sh", "-i", "-l", "-c", "command -v forgel 2>/dev/null || true"],
            env={
                "HOME": str(self.home),
                "SHELL": "/bin/sh",
                "PATH": "/usr/bin:/bin",
                "TERM": "dumb",
                "LC_ALL": "C",
            },
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return completed.stdout.strip()

    def _engine_version(self) -> str:
        completed = subprocess.run(
            [str(self.bin / "forgel"), "version", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)["version"]

    def _source_tree(self, version: str) -> Path:
        tree = self.tmp / f"engine-{version}"
        shutil.copytree(
            REPO / "src",
            tree / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copytree(REPO / "registry", tree / "registry")
        shutil.copytree(REPO / "jurisdiction", tree / "jurisdiction")
        declaration = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        (tree / "pyproject.toml").write_text(
            declaration.replace(
                f'version = "{DECLARED}"', f'version = "{version}"', 1
            ),
            encoding="utf-8",
        )
        return tree

    def _installed_versions(self) -> list[str]:
        return sorted(path.name for path in (self.root / "versions").iterdir())

    def test_resolve_reports_the_declared_version_and_changes_nothing(
        self,
    ) -> None:
        completed = self._run("--resolve")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"{DECLARED}\n")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_resolve_failure_names_cause_and_reports_no_version(self) -> None:
        completed = self._run(
            "--resolve", FORGEL_SOURCE="http://127.0.0.1:9/forgel.json"
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn("error:", completed.stderr)
        self.assertIn("next:", completed.stderr)

    def test_install_reports_the_version_the_engine_reports(self) -> None:
        completed = self._run()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"{DECLARED}\n")
        self.assertTrue((self.bin / "forgel").exists())
        self.assertEqual(self._engine_version(), DECLARED)
        self.assertEqual(len(self._installed_versions()), 1)

    def test_new_terminal_session_runs_the_engine_by_name(self) -> None:
        self.assertEqual(self._run().returncode, 0)

        self.assertEqual(self._terminal(), str(self.bin / "forgel"))

    def test_install_preserves_other_settings_and_does_not_duplicate(
        self,
    ) -> None:
        profile = self.home / ".profile"
        profile.write_text("export EDITOR=vi\n", encoding="utf-8")

        first = self._run()
        second = self._run()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, f"{DECLARED}\n")
        text = profile.read_text(encoding="utf-8")
        self.assertEqual(text.count("# >>> forgel installer >>>"), 1)
        self.assertIn("export EDITOR=vi\n", text)
        self.assertEqual(len(self._installed_versions()), 1)
        self.assertEqual(self._engine_version(), DECLARED)

    def test_newer_target_replaces_the_older_engine(self) -> None:
        newer = "0.1.1"
        tree = self._source_tree(newer)

        self.assertEqual(self._run().returncode, 0)
        upgraded = self._run(FORGEL_SOURCE=str(tree))

        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertEqual(upgraded.stdout, f"{newer}\n")
        self.assertEqual(self._engine_version(), newer)
        self.assertEqual(len(self._installed_versions()), 1)

    def test_uninstall_takes_back_what_was_added_and_keeps_data(self) -> None:
        profile = self.home / ".profile"
        profile.write_text("export EDITOR=vi\n", encoding="utf-8")
        self.assertEqual(self._run().returncode, 0)
        data = self.home / ".forgel" / "program" / "notes.txt"
        data.parent.mkdir(parents=True)
        data.write_text("keep me\n", encoding="utf-8")

        removed = self._run("--uninstall")

        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertIn("removed", removed.stdout)
        self.assertFalse((self.bin / "forgel").exists())
        self.assertEqual(
            profile.read_text(encoding="utf-8"), "export EDITOR=vi\n"
        )
        self.assertEqual(data.read_text(encoding="utf-8"), "keep me\n")
        self.assertEqual(self._terminal(), "")

    def test_uninstall_without_an_installation_succeeds(self) -> None:
        completed = self._run("--uninstall")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Nothing was installed", completed.stdout)

    def test_missing_interpreter_stops_before_any_change(self) -> None:
        completed = self._run(FORGEL_PYTHON=str(self.tmp / "missing-python"))

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("3.11", completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_resolve_after_install_keeps_the_installed_engine(self) -> None:
        self.assertEqual(self._run().returncode, 0)

        resolved = self._run("--resolve")

        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(resolved.stdout, f"{DECLARED}\n")
        self.assertEqual(self._engine_version(), DECLARED)
        self.assertEqual(len(self._installed_versions()), 1)

    def test_a_known_reference_is_honoured_and_an_unknown_one_fails(
        self,
    ) -> None:
        known = self._run("--resolve", FORGEL_REF=DECLARED)
        unknown = self._run("--resolve", FORGEL_REF="9.9.9")

        self.assertEqual(known.returncode, 0, known.stderr)
        self.assertEqual(known.stdout, f"{DECLARED}\n")
        self.assertNotEqual(unknown.returncode, 0)
        self.assertEqual(unknown.stdout, "")
        self.assertIn("9.9.9", unknown.stderr)

    def test_a_shadowing_engine_fails_and_restores_the_settings(
        self,
    ) -> None:
        profile = self.home / ".profile"
        profile.write_text("forgel() { return 0; }\n", encoding="utf-8")

        completed = self._run()

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn("error:", completed.stderr)
        self.assertIn("next:", completed.stderr)
        self.assertEqual(
            profile.read_text(encoding="utf-8"), "forgel() { return 0; }\n"
        )
        self.assertFalse((self.bin / "forgel").exists())

    def test_failed_upgrade_keeps_the_previous_engine_working(self) -> None:
        self.assertEqual(self._run().returncode, 0)
        broken = self._source_tree("0.1.2")
        (broken / "src/forgel/entry.py").unlink()

        failed = self._run(FORGEL_SOURCE=str(broken))

        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(failed.stdout, "")
        self.assertIn("error:", failed.stderr)
        self.assertEqual(self._engine_version(), DECLARED)
        self.assertEqual(len(self._installed_versions()), 1)


if __name__ == "__main__":
    unittest.main()
