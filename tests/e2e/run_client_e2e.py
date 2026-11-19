#!/usr/bin/env python3
"""Cross-repository end-to-end gate: the Forgel engine and Forgel Code.

``environment.yaml`` runs this after the self-hosting smoke. The engine is the
real CLI from this repository; the client is the real CLI from the sibling
``code`` repository, located through ``FORGEL_REPO_CODE`` (set from the
environment contract's ``mounts``; ``/code`` inside the sandbox).

The scenario proves the machine-readable contract between the two processes:
``projects`` sees the project, ``use`` selects it, ``status`` and ``session``
receive ``--project``, and ``say`` carries the phrase in ``--text`` and reaches
the engine. A scripted model answers; no network, Docker or provider model is
used.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from forgel.artifacts import write_text  # noqa: E402
from forgel.config import Settings  # noqa: E402
from forgel.layout import ProjectLayout  # noqa: E402
from forgel.ledger import Ledger  # noqa: E402
from forgel.program_manifest import set_entries  # noqa: E402
from forgel.project_config import render_project_config  # noqa: E402
from forgel.projects import create_project  # noqa: E402

BRIEF = "A tiny local fixture used to test the engine and the client together."
ANSWER = "Integration answer."
MAIN_ENTRY = {
    "id": "main",
    "role": "application",
    "provider": "local",
    "url": "",
    "depends_on": [],
}


class GateError(RuntimeError):
    """The client-engine scenario could not be driven."""


def _client_root() -> Path:
    raw = os.environ.get("FORGEL_REPO_CODE", "").strip()
    root = Path(raw).expanduser() if raw else ROOT.parent / "code"
    root = root.resolve()
    if not (root / "forgel_code").is_dir():
        raise GateError(
            "the Forgel Code repository is not available; set "
            f"FORGEL_REPO_CODE or place it at {ROOT.parent / 'code'}"
        )
    return root


def _engine_wrapper(path: Path, home: Path) -> None:
    """A ``forgel`` executable with the test home fixed."""

    path.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$FORGEL_TEST_ARGV"\n'
        f'exec {shlex.quote(sys.executable)} -m forgel '
        f'"$@" --home {shlex.quote(str(home))}\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_client(
    client_root: Path,
    wrapper: Path,
    env: dict[str, str],
    *args: str,
) -> tuple[int, dict[str, object] | None, str]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "forgel_code",
            "--engine",
            str(wrapper),
            *args,
            "--json",
        ],
        cwd=str(client_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    payload: dict[str, object] | None = None
    if completed.stdout.strip():
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError:
            value = None
        if isinstance(value, dict):
            payload = value
    return completed.returncode, payload, (
        completed.stdout + completed.stderr
    )[-4000:]


def _add(
    checks: list[tuple[str, bool, str]],
    name: str,
    ok: bool,
    detail: str = "",
) -> None:
    checks.append((name, bool(ok), detail))


def run_gate(checks: list[tuple[str, bool, str]]) -> None:
    client_root = _client_root()
    home = Path(tempfile.mkdtemp(prefix="forgel-client-e2e-"))
    try:
        settings = Settings(
            home=home,
            registry_path=ROOT / "registry" / "recipes.json",
            templates_path=ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=ROOT / "jurisdiction",
            qa_runtime="local",
            sandbox="local",
            peak_policy="always",
        )
        ledger = Ledger(settings.db_path)
        try:
            project_id = create_project(
                settings,
                ledger,
                "client e2e",
                BRIEF,
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            if project is None:
                raise GateError("the project is missing from the ledger")
            layout = ProjectLayout.detect(project["workspace"])
            set_entries(layout, [MAIN_ENTRY])
            repo = layout.repo_path("main")
            repo.mkdir(parents=True, exist_ok=True)
            (repo / "README.md").write_text("fixture\n", encoding="utf-8")
            write_text(
                layout.control / "forgel.toml",
                render_project_config(
                    "client e2e", model_peak_policy="always"
                ),
            )
        finally:
            ledger.close()

        (home / "model-script.json").write_text(
            json.dumps(
                {
                    "responses": [
                        json.dumps(
                            {"kind": "answer", "reply": ANSWER}
                        )
                    ]
                }
            ),
            encoding="utf-8",
        )
        wrapper = home / "forgel-engine"
        argv_log = home / "argv.log"
        _engine_wrapper(wrapper, home)
        client_home = home / "client-home"
        env = dict(os.environ)
        env.update(
            {
                "FORGEL_MODEL_MODE": "script",
                "FORGEL_CODE_HOME": str(client_home),
                "FORGEL_TEST_ARGV": str(argv_log),
                "PYTHONPATH": os.pathsep.join(
                    [str(ROOT / "src"), str(client_root)]
                ),
            }
        )

        code, payload, output = _run_client(
            client_root, wrapper, env, "projects"
        )
        projects = (
            (payload or {}).get("result", {}).get("projects", [])
            if isinstance((payload or {}).get("result"), dict)
            else []
        )
        _add(
            checks,
            "the client reads the project list",
            code == 0
            and isinstance(payload, dict)
            and any(
                item.get("id") == project_id
                for item in projects
                if isinstance(item, dict)
            ),
            output,
        )

        code, payload, output = _run_client(
            client_root, wrapper, env, "use", project_id
        )
        _add(
            checks,
            "the client selects the project",
            code == 0
            and isinstance(payload, dict)
            and payload.get("project") == project_id,
            output,
        )

        code, payload, output = _run_client(
            client_root, wrapper, env, "status"
        )
        result = (payload or {}).get("result")
        project_view = (
            result.get("project") if isinstance(result, dict) else None
        )
        _add(
            checks,
            "status carries the selected project",
            code == 0
            and isinstance(payload, dict)
            and payload.get("project") == project_id
            and isinstance(project_view, dict)
            and project_view.get("id") == project_id,
            output,
        )

        code, payload, output = _run_client(
            client_root, wrapper, env, "session"
        )
        result = (payload or {}).get("result")
        selected = (
            result.get("project") if isinstance(result, dict) else None
        )
        _add(
            checks,
            "the engine session points to the project",
            code == 0
            and isinstance(selected, dict)
            and selected.get("id") == project_id,
            output,
        )

        code, payload, output = _run_client(
            client_root, wrapper, env, "say", "hello", "integration"
        )
        result = (payload or {}).get("result")
        text = str(result.get("text") or "") if isinstance(result, dict) else ""
        _add(
            checks,
            "say reaches the engine through --text",
            code == 0
            and isinstance(payload, dict)
            and payload.get("project") == project_id
            and ANSWER in text,
            output,
        )

        lines = argv_log.read_text(encoding="utf-8").splitlines()
        status_line = next(
            (line for line in lines if line.startswith("status ")), ""
        )
        say_line = next(
            (line for line in lines if line.startswith("say ")), ""
        )
        _add(
            checks,
            "the engine receives --project on status",
            f"--project {project_id}" in status_line,
            status_line,
        )
        _add(
            checks,
            "say sends --text and --project",
            "--text" in say_line
            and f"--project {project_id}" in say_line,
            say_line,
        )
    finally:
        shutil.rmtree(home, ignore_errors=True)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    failure = ""
    try:
        run_gate(checks)
    except Exception as exc:  # noqa: BLE001 - report the failure, never crash
        failure = f"{type(exc).__name__}: {exc}"
    print("=== CLIENT E2E ===")
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
        print("FAIL client e2e is red: " + ", ".join(failed))
        return 1
    print("PASS client e2e is green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
