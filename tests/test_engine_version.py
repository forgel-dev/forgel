import io
import json
import os
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from forgel import engine_version
from forgel.entry import main

REPO_ROOT = Path(__file__).resolve().parents[1]


def _declared() -> str:
    data = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    return data["project"]["version"]


class EngineVersionTest(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, dict, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = engine_version.version_command(argv)
        return code, json.loads(out.getvalue()), err.getvalue()

    def test_reports_the_declared_version(self) -> None:
        code, payload, _ = self._run(["--json"])
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], _declared())
        self.assertEqual(payload["kind"], "version")

    def test_version_is_comparable_component_by_component(self) -> None:
        _, payload, _ = self._run(["--json"])
        parts = payload["version"].split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertGreaterEqual(int(part), 0)

    def test_reads_with_nothing_set_up_and_leaves_nothing_behind(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp)
            where = str(empty)
            with mock.patch.dict(
                os.environ, {"HOME": where, "FORGEL_HOME": where}
            ):
                previous = os.getcwd()
                os.chdir(empty)
                try:
                    code, payload, _ = self._run(
                        ["--json", "--home", where]
                    )
                finally:
                    os.chdir(previous)
            self.assertEqual(code, 0)
            self.assertEqual(payload["version"], _declared())
            self.assertEqual(list(empty.iterdir()), [])

    def test_version_comes_from_the_release_declaration(self) -> None:
        self.assertEqual(engine_version.declared_version(), _declared())
        with mock.patch.object(
            engine_version, "declared_version", return_value="9.8.7"
        ):
            code, payload, _ = self._run(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["version"], "9.8.7")

    def test_failure_is_a_failure_with_its_reason(self) -> None:
        with mock.patch.object(
            engine_version, "declared_version", return_value=""
        ), mock.patch.object(
            engine_version, "installed_version", return_value=""
        ):
            code, payload, err = self._run(["--json"])
        self.assertNotEqual(code, 0)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["error"])
        self.assertIn(payload["error"], err)

    def test_only_comparable_versions_are_stated(self) -> None:
        with mock.patch.object(
            engine_version, "declared_version", return_value="1.0"
        ), mock.patch.object(
            engine_version, "installed_version", return_value="0.1.0"
        ):
            code, payload, _ = self._run(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["version"], "0.1.0")

    def test_unknown_arguments_are_refused(self) -> None:
        code, payload, _ = self._run(["--nonsense"])
        self.assertNotEqual(code, 0)
        self.assertFalse(payload["ok"])


class EntryDispatchTest(unittest.TestCase):
    def test_the_entry_point_reports_the_version(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["version", "--json"])
        payload = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["version"], _declared())

    def test_the_package_version_is_the_declared_one(self) -> None:
        import forgel

        self.assertEqual(forgel.__version__, _declared())


if __name__ == "__main__":
    unittest.main()
