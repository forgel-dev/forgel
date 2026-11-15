"""Usage: `env NAME=value python ...` must run when PATH has no `python`.

QA runs acceptance checks from a stripped environment (a handful of safe
variables plus the contract's `env`), so a check written as
``env PYTHONPATH=src python -m unittest ...`` failed with
``env: python: No such file or directory`` (exit 127). ``command_argv`` pins
the interpreter to the running one, which this test reproduces with a PATH
that only carries ``env`` and ``python3``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forgel.environment import command_argv

POSIX = os.name == "posix"

SCRIPT = (
    'import os, sys; '
    'sys.exit(0 if os.environ.get("PYTHONPATH") == "src" else 1)'
)


@unittest.skipUnless(POSIX, "needs symlinks and a POSIX env(1)")
class EnvPrefixedPythonExecutionTest(unittest.TestCase):
    def test_env_prefixed_python_runs_with_a_path_without_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "python3").symlink_to(sys.executable)
            env_program = "/usr/bin/env"
            if not Path(env_program).exists():
                self.skipTest("no /usr/bin/env on this host")
            (path / "env").symlink_to(env_program)
            command = f"env PYTHONPATH=src python -c {ascii(SCRIPT)}"
            completed = subprocess.run(
                command_argv(command),
                cwd=tmp,
                env={"PATH": str(path)},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )


if __name__ == "__main__":
    unittest.main()
