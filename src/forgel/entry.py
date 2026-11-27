"""Console-script entry point.

``forgel`` dispatches four kinds of work: the reporting commands that read
only from the ledger (``forgel cost``), the engine's own identity report
(``forgel version``), the machine-readable client commands (``forgel say``,
``forgel status --json``, ...) and everything else, which stays in
``forgel.cli``. Keeping the split here means a reporting path never has to
start a model session or load settings, and the client parser never changes the
legacy commands.
"""

from __future__ import annotations

import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "cost":
        from .costs import cost_command

        return cost_command(arguments[1:])
    if arguments and arguments[0] == "version":
        from .engine_version import version_command

        return version_command(arguments[1:])
    from .client import maybe_dispatch

    handled = maybe_dispatch(arguments)
    if handled is not None:
        return handled
    from .cli import main as cli_main

    return cli_main(arguments)
