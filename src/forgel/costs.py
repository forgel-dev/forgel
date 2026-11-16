"""Cost and acceptance reporting read straight from the ledger.

The report is a pure function of recorded events and approvals, so running it
never writes, migrates or deletes ledger data. The CLI (``forgel cost``) and the
local console (``/cost``) print the same text.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Sequence

from . import language
from .config import Settings
from .i18n import t as _t
from .ledger import Ledger
from .projects import ProjectError, resolve_project


def money(value: float) -> str:
    return f"${float(value):.2f}"


def acceptance_counts(acceptances: list[dict[str, Any]]) -> tuple[int, int]:
    accepted = sum(1 for item in acceptances if item["decision"] == "accepted")
    rejected = sum(1 for item in acceptances if item["decision"] == "rejected")
    return accepted, rejected


def cost_report(
    ledger: Ledger, project_id: str, lang: str = "en"
) -> str:
    """Return the cost report for one project in ``lang``."""

    summary = ledger.cost_summary(project_id)
    acceptances = ledger.acceptances(project_id)
    accepted, rejected = acceptance_counts(acceptances)

    lines = [_t(lang, "cost_title", project=project_id), ""]
    lines.append(_t(lang, "cost_total", money=money(summary["total"])))
    lines.append(_t(lang, "cost_per_stage"))
    if summary["by_stage"]:
        for stage in sorted(summary["by_stage"]):
            lines.append(
                f"  {stage:<16} {money(summary['by_stage'][stage])}"
            )
    else:
        lines.append(_t(lang, "cost_none"))
    lines.append(_t(lang, "cost_per_generation"))
    if summary["by_generation"]:
        for generation in sorted(summary["by_generation"]):
            lines.append(
                f"  g{generation:<15} {money(summary['by_generation'][generation])}"
            )
    else:
        lines.append(_t(lang, "cost_none"))
    lines.append(
        _t(
            lang,
            "cost_acceptance",
            count=len(acceptances),
            accepted=accepted,
            rejected=rejected,
        )
    )
    for item in acceptances:
        reason = (
            _t(lang, "cost_reason", reason=item["reason"])
            if item["reason"]
            else ""
        )
        lines.append(
            _t(
                lang,
                "cost_acceptance_line",
                decision=item["decision"],
                task=item["task_id"],
                actor=item["actor"],
                reason=reason,
            )
        )
    return "\n".join(lines)


def cost_command(argv: Sequence[str]) -> int:
    """``forgel cost <project> [--home DIR]``; reads the ledger, never writes."""

    parser = argparse.ArgumentParser(
        prog="forgel cost",
        description="Report project cost and task acceptance from the ledger.",
    )
    parser.add_argument("project_id")
    parser.add_argument("--home", default=None)
    args = parser.parse_args(list(argv))
    lang = language.detect(" ".join(argv), "en")
    settings = Settings.from_env(args.home)
    try:
        ledger = Ledger(settings.db_path, read_only=True)
    except Exception as exc:  # noqa: BLE001 - report, do not migrate
        print(
            _t(lang, "cost_ledger_error", error=exc),
            file=sys.stderr,
        )
        return 1
    try:
        try:
            project = resolve_project(ledger, args.project_id)
        except ProjectError as exc:
            print(
                _t(lang, "cli_error", error=exc),
                file=sys.stderr,
            )
            return 1
        print(cost_report(ledger, str(project["id"]), lang))
        return 0
    finally:
        ledger.close()
