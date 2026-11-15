"""Commands prefixed with ``env NAME=value`` still resolve ``python``.

Acceptance checks are stored as ``env PYTHONPATH=src python -m unittest ...``
so the interpreter must still be pinned to the running one.
"""

from __future__ import annotations

import sys
import unittest

from forgel.environment import EnvironmentError, command_argv


class EnvPrefixedCommandTest(unittest.TestCase):
    def test_python_after_assignments_is_resolved(self) -> None:
        self.assertEqual(
            command_argv("env PYTHONPATH=src python -m unittest discover"),
            [
                "env",
                "PYTHONPATH=src",
                sys.executable,
                "-m",
                "unittest",
                "discover",
            ],
        )

    def test_several_assignments_are_kept(self) -> None:
        self.assertEqual(
            command_argv("env A=1 B=two python3 -V"),
            ["env", "A=1", "B=two", sys.executable, "-V"],
        )

    def test_env_without_a_program_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            command_argv("env PYTHONPATH=src")

    def test_env_with_other_programs_is_kept(self) -> None:
        self.assertEqual(
            command_argv("env A=1 node check.mjs"),
            ["env", "A=1", "node", "check.mjs"],
        )


if __name__ == "__main__":
    unittest.main()
