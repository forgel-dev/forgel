#!/usr/bin/env python3
"""Manual end-to-end test: a local daemon builds a minimal blog platform.

This is not part of ``make test``. It is the foundation for the migration
process: the same scenario can be moved to a separate repository and run
before releases. It spends provider budget in ``api`` mode; the default
``script`` mode uses a deterministic stand-in model and is free.

Modes
-----
script  deterministic harness validation; no model calls.
bridge  the daemon waits for an external subagent driver (no provider budget).
api     a real OpenAI-compatible model; requires FORGEL_MODEL_API_KEY and
        --yes because it spends budget.

Exit codes
----------
0  harness passed, and the product passed (or --strict was not set)
1  harness failed
2  harness passed but the product failed in --strict mode
3  configuration/usage error
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from forgel.adopt import adopt_repository  # noqa: E402
from forgel.artifacts import write_text  # noqa: E402
from forgel.config import Settings  # noqa: E402
from forgel.environment import (  # noqa: E402
    Environment,
    EnvironmentError,
    command_argv,
    environment_path,
    load_environment,
    render_environment,
)
from forgel.layout import ProjectLayout  # noqa: E402
from forgel.ledger import Ledger  # noqa: E402
from forgel.tasks import create_task, get_task  # noqa: E402
from tests.e2e.blog_actions import responses  # noqa: E402

TASK_TITLE = "Minimal blog platform"
TASK_BRIEF = "Build a minimal blog platform from scratch."
REQUIREMENTS = [
    "Build a minimal blog web application in Python using only the standard "
    "library.",
    "Running `python app.py --host 127.0.0.1 --port <port>` starts an HTTP "
    "server. The SQLite path comes from the BLOG_DB environment variable and "
    "defaults to blog.sqlite3.",
    'GET /health returns HTTP 200 with JSON {"status":"ok"}.',
    "GET / returns HTML containing the text Mini Blog, a form to create a "
    "post, and the list of existing posts.",
    "POST /posts accepts form fields title and body, stores the post and "
    "redirects to the new post.",
    "GET /posts/<id> returns HTML with the post title and body; unknown ids "
    "return 404.",
    "Posts persist in SQLite across server restarts.",
    "Tests under tests/ run with `python -m unittest discover -s tests` and "
    "cover health, index, create/view and 404.",
    "README.md documents how to run and test the app.",
]
ACCEPTANCE = [
    "The external validator tests/e2e/validate_blog.py exits 0.",
    "The app starts with the documented command and passes health, index, "
    "create, view, persistence and 404 checks.",
    "The unit test command exits 0.",
    "The repository contains no third-party imports, external URLs or "
    "secret-like files.",
]
CONSTRAINTS = [
    "Python standard library only; do not add dependencies or a requirements file.",
    "No external API calls, no network access, no deployment configuration, no Telegram.",
    "No authentication, payments, search, comments, editing or other unrequested features.",
    "Keep the implementation small: one app module and one test module are enough.",
    "Do not write .env, secrets, keys or database files into the repository.",
]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _make_source(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "README.md").write_text(
        "The blog platform will be implemented by Forgel.\n",
        encoding="utf-8",
    )
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(
        path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-q",
        "-m",
        "initial",
    )


def _checks(project: dict, layout: ProjectLayout, task: dict) -> list[tuple[str, bool, str]]:
    repo = layout.repo_path("main")
    report_ref = task.get("result", {}).get("report", "")
    report = layout.root / report_ref if report_ref else None
    state = str(task.get("status"))
    try:
        environment = load_environment(layout)
        environment_detail = "" if environment else "not found"
    except EnvironmentError as exc:
        environment = None
        environment_detail = str(exc)
    checks = [
        ("task record exists", bool(task.get("id")), ""),
        (
            "environment contract valid",
            environment is not None and bool(environment.test),
            environment_detail,
        ),
        (
            "task reached a terminal state",
            state in {"done", "failed"},
            state,
        ),
        (
            "report written",
            bool(report_ref) and report is not None and report.exists(),
            str(report),
        ),
        (
            "task result has a summary",
            bool(task.get("result", {}).get("summary")),
            "",
        ),
    ]
    if state == "done":
        commit = _git(repo, "log", "-1", "--format=%s").stdout.strip()
        worktree = _git(repo, "status", "--porcelain").stdout.strip()
        checks.extend(
            [
                ("agent commit present", "Agent:" in commit, commit),
                ("code worktree clean after commit", worktree == "", worktree[:300]),
            ]
        )
    return checks


def _review_prompt(project: dict, layout: ProjectLayout, task: dict) -> str:
    repo = layout.repo_path("main")
    return f"""You are an independent reviewer. You did not take part in the
implementation. Do not modify the repository.

Project: {project['id']}
Task:
{json.dumps(task, indent=2, ensure_ascii=False)}

Repository: {repo}
Validator: {ROOT / 'tests/e2e/validate_blog.py'}

Review the repository against the explicit requirements above. Check that no
unrequested feature was added, that there are no external calls or secrets,
and that the implementation and tests are coherent. Return a short verdict:
PASS or FAIL per explicit requirement, plus any blocking defect. Do not
rewrite the code.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["script", "bridge", "api"], default="script"
    )
    parser.add_argument(
        "--driver-command",
        default="",
        help="Bridge mode: command that reads a prompt on stdin and prints the answer",
    )
    parser.add_argument(
        "--review-command",
        default="",
        help="Optional external reviewer: command that reads the prompt on stdin",
    )
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--home",
        type=Path,
        default=None,
        help="Use an explicit empty FORGEL_HOME (useful for manual bridge runs)",
    )
    args = parser.parse_args()

    if args.mode == "api":
        if not os.environ.get("FORGEL_MODEL_API_KEY"):
            print(
                "error: api mode needs FORGEL_MODEL_API_KEY", file=sys.stderr
            )
            return 3
        if not args.yes:
            print(
                "error: api mode spends provider budget; re-run with --yes",
                file=sys.stderr,
            )
            return 3

    if args.home is not None:
        home = args.home.expanduser().resolve()
        if home.exists() and any(home.iterdir()):
            print(f"error: --home is not empty: {home}", file=sys.stderr)
            return 3
        home.mkdir(parents=True, exist_ok=True)
    else:
        home = Path(tempfile.mkdtemp(prefix="forgel-e2e-blog-"))
    print(f"home:      {home}", flush=True)
    settings = Settings(
        home=home,
        registry_path=ROOT / "registry" / "recipes.json",
        templates_path=ROOT / "src" / "forgel" / "templates",
        jurisdiction_path=ROOT / "jurisdiction",
        qa_runtime="local",
    )
    ledger = Ledger(settings.db_path)
    try:
        source = home / "source"
        _make_source(source)
        adopted = adopt_repository(
            settings, ledger, str(source), brief=TASK_BRIEF
        )
        project = ledger.get_project(adopted.project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        environment = Environment(
            image="python:3.12-slim",
            test=("python -m unittest discover -s tests",),
        )
        write_text(
            environment_path(layout),
            render_environment(environment),
        )
        test_command = command_argv(environment.test[0])
        task = create_task(
            layout,
            TASK_TITLE,
            REQUIREMENTS,
            ACCEPTANCE,
            CONSTRAINTS,
            repo_id="main",
            test_command=test_command,
        )
    finally:
        ledger.close()

    mode = {
        "script": "script",
        "bridge": "bridge",
        "api": "auto",
    }[args.mode]
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "FORGEL_HOME": str(home),
        "FORGEL_MODEL_MODE": mode,
    }
    if args.mode == "script":
        (home / "model-script.json").write_text(
            json.dumps({"responses": responses()}, ensure_ascii=False),
            encoding="utf-8",
        )
    if args.mode == "bridge":
        env["FORGEL_MODEL_BRIDGE_DIR"] = str(home / "model-bridge")
        Path(env["FORGEL_MODEL_BRIDGE_DIR"]).mkdir(
            parents=True, exist_ok=True
        )
        print(
            f"bridge:    {env['FORGEL_MODEL_BRIDGE_DIR']}", flush=True
        )

    driver: subprocess.Popen[str] | None = None
    if args.mode == "bridge" and args.driver_command:
        driver = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/e2e/subagent_driver.py"),
                "--bridge-dir",
                env["FORGEL_MODEL_BRIDGE_DIR"],
                "--command",
                args.driver_command,
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    elif args.mode == "bridge":
        print(
            "bridge mode: start a driver against "
            f"{env['FORGEL_MODEL_BRIDGE_DIR']} in another terminal",
            file=sys.stderr,
        )

    daemon_env = env
    daemon = subprocess.run(
        [
            sys.executable,
            "-m",
            "forgel",
            "daemon",
            "--home",
            str(home),
            "--once",
        ],
        env=daemon_env,
        capture_output=True,
        text=True,
        timeout=args.timeout,
        check=False,
    )
    if driver is not None:
        driver.terminate()
        try:
            driver.wait(timeout=5)
        except subprocess.TimeoutExpired:
            driver.kill()

    print(f"mode:      {args.mode}")
    print(f"home:      {home}")
    print(f"project:   {project['id']}")
    print(f"task:      {task['id']}")
    print(f"daemon:    exit {daemon.returncode}")
    if daemon.returncode != 0:
        print(daemon.stdout[-4000:])
        print(daemon.stderr[-4000:])

    ledger = Ledger(settings.db_path)
    try:
        stored = get_task(layout, task["id"]) or task
    finally:
        ledger.close()
    print(f"status:    {stored.get('status')}")
    print(f"summary:   {stored.get('result', {}).get('summary', '')}")

    harness_checks = [
        ("daemon exited cleanly", daemon.returncode == 0, str(daemon.returncode)),
    ]
    harness_checks.extend(_checks(project, layout, stored))
    harness_failed = [name for name, ok, _detail in harness_checks if not ok]
    print("\n=== HARNESS ===")
    for name, ok, detail in harness_checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" [{detail}]" if detail else ""))

    product_ok = False
    if stored.get("status") == "done":
        validator = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tests/e2e/validate_blog.py"),
                str(layout.repo_path("main")),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        print(validator.stdout)
        if validator.returncode != 0:
            print(validator.stderr[-2000:])
        product_ok = validator.returncode == 0
    print("=== PRODUCT ===")
    print(f"{'PASS' if product_ok else 'FAIL'} blog acceptance")

    if args.review_command:
        prompt = _review_prompt(project, layout, stored)
        review = subprocess.run(
            shlex.split(args.review_command),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
        print("\n=== EXTERNAL REVIEW ===")
        print(review.stdout.strip() or review.stderr.strip())

    if args.clean:
        shutil.rmtree(home, ignore_errors=True)
    else:
        print(f"artifacts kept in {home}")

    if harness_failed:
        return 1
    if args.strict and not product_ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
