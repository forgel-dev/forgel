"""The engine's own version, taken from the release declaration.

A release declares exactly one version: ``[project] version`` in
``pyproject.toml``. That file is the authority; the engine keeps no second,
independently editable statement of it, so nothing can drift from the release.
An installed distribution does not ship the declaration, so it falls back to
the package metadata, which is written from that same file when the
distribution is built.

The version is reported as ``major.minor.patch``, so two of them compare
component by component. Reading it needs no project, no stored configuration,
no ledger, no model credential and no network, and writes nothing.
"""

from __future__ import annotations

import importlib.metadata
import re
import sys
import tomllib
from pathlib import Path
from typing import Sequence

DISTRIBUTION = "forgel"
COMPARABLE = re.compile(r"^\d+\.\d+\.\d+$")


class EngineVersionError(RuntimeError):
    """The declared version cannot be read or is not comparable."""


def declared_version() -> str:
    """The version ``pyproject.toml`` declares, or an empty string."""

    path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return ""
    project = data.get("project")
    version = project.get("version") if isinstance(project, dict) else None
    return version if isinstance(version, str) else ""


def installed_version() -> str:
    """The version the installed metadata carries, or an empty string."""

    try:
        return importlib.metadata.version(DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return ""


def resolved_version() -> str:
    """The version the release declares, or an empty string.

    The declaration wins; the installed metadata is only the same value as
    seen by an engine that ships without the declaration.
    """

    for source in (declared_version, installed_version):
        version = source().strip()
        if COMPARABLE.match(version):
            return version
    return ""


def engine_version() -> str:
    """The engine's own version, comparable component by component."""

    version = resolved_version()
    if not version:
        raise EngineVersionError(
            "cannot read the declared engine version from pyproject.toml "
            "or the installed package metadata"
        )
    return version


def version_command(argv: Sequence[str]) -> int:
    """``forgel version [--json] [--home PATH]``: one JSON object, no state.

    The report is invoked the way the engine's other program-facing commands
    are, so ``--json`` and ``--home`` are accepted. Reading the version needs
    no stored configuration, so the home path is simply not used.
    """

    unexpected: list[str] = []
    items = list(argv)
    index = 0
    while index < len(items):
        item = items[index]
        if item == "--home":
            index += 2
            continue
        if item == "--json" or item.startswith("--home="):
            index += 1
            continue
        unexpected.append(item)
        index += 1
    if unexpected:
        return report(False, f"unknown arguments: {' '.join(unexpected)}")
    try:
        version = engine_version()
    except EngineVersionError as exc:
        return report(False, str(exc))
    return report(True, version=version)


def report(ok: bool, reason: str = "", version: str = "") -> int:
    """Write the engine's usual envelope; a failure keeps its reason."""

    from .client_cli import envelope, write

    if not ok:
        print(f"error: {reason}", file=sys.stderr)
    write(envelope(ok, "version", version, reason, version=version))
    return 0 if ok else 1
