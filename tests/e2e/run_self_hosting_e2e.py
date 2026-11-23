#!/usr/bin/env python3
"""Offline self-hosting end-to-end smoke of Forgel on itself.

This is the gate declared by ``environment.yaml``'s ``e2e`` entry. It runs
with ``FORGEL_MODEL_MODE=script`` and the scripted model, adopts a local
fixture repository, plans a milestone, runs one task through the coding agent,
task QA and task review, and stops at the staging approval gate: the task is
parked in ``review`` status with a pending acceptance decision, and the project
never reaches ``done`` on its own.

For a brownfield linked project there is no orchestrator staging descriptor;
the human sign-off that keeps the pipeline from reaching ``done`` is the task
acceptance gate. The product default is ``FORGEL_TASK_ACCEPT=auto``; the driver
opts into ``human`` to prove that the gate is a hard stop when a project asks
for it.

No network, Docker daemon, cloud resources or provider model are touched. The
temporary home and fixture repository are removed on exit, and the exit code
is non-zero when any gate is red.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from forgel.adopt import adopt_repository  # noqa: E402
from forgel.config import Settings  # noqa: E402
from forgel.daemon import run_once  # noqa: E402
from forgel.layout import ProjectLayout  # noqa: E402
from forgel.ledger import Ledger  # noqa: E402
from forgel.model import ScriptedModelClient  # noqa: E402
from forgel.planner import plan_project  # noqa: E402
from forgel.tasks import get_task  # noqa: E402

BRIEF = "A tiny local fixture used to smoke-test Forgel on itself."
GOAL = "Add a greeting module to the fixture repository."

PLAN = {
    "notes": "One small task; the approval gate must still need a human.",
    "repositories": [],
    "tasks": [
        {
            "title": "Add a greeting module",
            "summary": "Add a small greeting module to the fixture.",
            "repo_id": "main",
            "depends_on": [],
        }
    ],
}

SPEC = {
    "problem": "The fixture has no greeting module.",
    "outcome": "greeting.py exists and the fixture test command stays green.",
    "scope": ["Add greeting.py with a short greeting message."],
    "non_goals": [],
    "requirements": [
        "Create greeting.py with a short greeting message.",
    ],
    "acceptance": [
        "greeting.py exists and the fixture test command stays green.",
    ],
    "constraints": ["Python standard library only."],
    "assumptions": [],
    "risks": [],
    "checks": [
        {
            "criterion": "The gate command exits 0",
            "verification": "command",
            "command": ["python", "-c", "print('ok')"],
        }
    ],
    "test_command": ["python", "--version"],
}

CRITIC = {"sufficient": True, "findings": []}

AGENT_WRITE = {
    "action": "write_file",
    "path": "greeting.py",
    "content": 'print("hello from the fixture")\n',
}
AGENT_DONE = {
    "action": "done",
    "summary": "added the greeting module and confirmed the fixture test",
}
REVIEW = {
    "verdict": "pass",
    "summary": "The tiny change meets every explicit requirement.",
    "requirements": [
        {
            "requirement": "greeting.py exists",
            "verdict": "pass",
            "note": "The agent wrote it and committed the change.",
        }
    ],
    "blocking": [],
}


class GateError(RuntimeError):
    """The self-hosting pipeline could not be driven to the gate."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def _make_fixture(root: Path) -> None:
    """A small local git repository the smoke test can adopt."""

    root.mkdir(parents=True)
    (root / "README.md").write_text(
        "# Fixture\n\nA local fixture repository for the self-hosting smoke.\n",
        encoding="utf-8",
    )
    (root / "environment.yaml").write_text(
        "image: python:3.12-slim\n"
        "test:\n"
        "  - python --version\n",
        encoding="utf-8",
    )
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-q",
        "-m",
        "initial",
    )
    origin = root.parent / "fixture-origin.git"
    _git(
        root.parent,
        "init",
        "--bare",
        "-q",
        "-b",
        "main",
        str(origin),
    )
    _git(root, "remote", "add", "origin", str(origin))
    if (root / ".git" / "HEAD").exists():
        return
    raise GateError(f"the fixture is not a git repository: {root}")


def _force_always_peak(layout: ProjectLayout) -> None:
    """Keep the smoke deterministic: never defer for DeepSeek peak pricing."""

    path = layout.control / "forgel.toml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if 'peak_policy = "off_peak"' in text:
        path.write_text(
            text.replace('peak_policy = "off_peak"', 'peak_policy = "always"'),
            encoding="utf-8",
        )


def _responses() -> list[str]:
    return [
        json.dumps(PLAN),
        json.dumps(SPEC),
        json.dumps(CRITIC),
        json.dumps(AGENT_WRITE),
        json.dumps(AGENT_DONE),
        json.dumps({"commit": ["greeting.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
        json.dumps(REVIEW),
    ]


def run_gate(home: Path, checks: list[tuple[str, bool, str]]) -> None:
    """Drive the pipeline once; append each gate result to ``checks``."""

    _make_fixture(home / "fixture")
    settings = Settings(
        home=home,
        registry_path=ROOT / "registry" / "recipes.json",
        templates_path=ROOT / "src" / "forgel" / "templates",
        jurisdiction_path=ROOT / "jurisdiction",
        qa_runtime="local",
        sandbox="local",
        peak_policy="always",
        task_qa=True,
        task_review=True,
        task_accept="human",
    )
    ledger = Ledger(settings.db_path)
    try:
        adopted = adopt_repository(
            settings,
            ledger,
            str(home / "fixture"),
            brief=BRIEF,
            name="selfhost",
        )
        project = ledger.get_project(adopted.project_id)
        if project is None:
            raise GateError("the adopted project is missing from the ledger")
        layout = ProjectLayout.detect(project["workspace"])
        _force_always_peak(layout)

        client = ScriptedModelClient(_responses())
        plan = plan_project(
            settings,
            ledger,
            project,
            GOAL,
            client=client,
            log=lambda _m: None,
        )
        checks.append(("a milestone was planned", bool(plan.tasks), str(len(plan.tasks))))
        if not plan.tasks:
            return

        processed = run_once(
            settings, ledger, log=lambda _m: None, client=client
        )
        checks.append(
            ("the daemon ran the task", bool(processed), str(processed))
        )

        task_id = str(plan.tasks[0]["task_id"])
        stored = get_task(layout, task_id) or {}
        result = dict(stored.get("result") or {})
        status = str(stored.get("status") or "")
        qa = dict(result.get("qa") or {})
        review = dict(result.get("review") or {})
        acceptance = dict(result.get("acceptance") or {})
        checkpoint = ledger.checkpoint(str(project["id"]))

        mode = os.environ.get("FORGEL_MODEL_MODE", "").strip().lower()
        checks.extend(
            [
                ("FORGEL_MODEL_MODE=script", mode == "script", mode),
                (
                    "the task stopped at the staging approval gate",
                    status == "review",
                    status,
                ),
                ("task QA passed", qa.get("status") == "pass", str(qa.get("status"))),
                (
                    "task review passed",
                    review.get("status") == "pass",
                    str(review.get("status")),
                ),
                (
                    "acceptance is pending a human decision",
                    acceptance.get("status") == "pending",
                    str(acceptance.get("status")),
                ),
                (
                    "the project never reached done",
                    checkpoint != "done",
                    str(checkpoint),
                ),
            ]
        )
    finally:
        ledger.close()


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="forgel-selfhost-e2e-"))
    checks: list[tuple[str, bool, str]] = []
    failure = ""
    try:
        run_gate(home, checks)
    except Exception as exc:  # noqa: BLE001 - report the failure, never crash
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(home, ignore_errors=True)

    print("=== SELF-HOSTING E2E ===")
    for name, ok, detail in checks:
        suffix = f" [{detail}]" if detail else ""
        print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}")
    if failure:
        print(f"FAIL driver crashed: {failure}")
        return 1

    failed = [name for name, ok, _detail in checks if not ok]
    if not checks:
        print("FAIL no gate was evaluated")
        return 1
    if failed:
        print("FAIL self-hosting gate is red: " + ", ".join(failed))
        return 1
    print("PASS self-hosting gate is green and parked for human approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
