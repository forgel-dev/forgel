#!/usr/bin/env python3
"""External acceptance validator for the blog e2e.

It knows nothing about Forgel internals. It runs the generated application,
checks the explicit product requirements and prints a deterministic verdict.
The external review prompt covers judgement that a script cannot make.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

THIRD_PARTY = (
    "flask",
    "django",
    "fastapi",
    "requests",
    "sqlalchemy",
    "aiohttp",
    "starlette",
    "uvicorn",
    "bottle",
    "tornado",
)
URL_RE = re.compile(r"https?://[^\s'\"<>]+")
IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE
)

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    checks.append((name, bool(condition), detail))
    print(
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f" [{detail}]" if detail else "")
    )
    return bool(condition)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(url: str, process: subprocess.Popen[str], timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:  # noqa: BLE001 - retry until the deadline
            pass
        time.sleep(0.2)
    return False


def start_app(repo: Path, db: Path, port: int) -> subprocess.Popen[str]:
    env = {**os.environ, "BLOG_DB": str(db)}
    return subprocess.Popen(
        [
            sys.executable,
            "app.py",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_app(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def fetch(url: str, data: bytes | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def post_form(url: str, values: dict[str, str]) -> tuple[int, str]:
    import urllib.parse

    data = urllib.parse.urlencode(values).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, ""
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location", "")
        return exc.code, location


def static_checks(repo: Path) -> None:
    python_files = [
        path
        for path in repo.rglob("*.py")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    bad_imports: list[str] = []
    for path in python_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in IMPORT_RE.finditer(text):
            root = match.group(1)
            if root in THIRD_PARTY:
                bad_imports.append(f"{path.relative_to(repo)}: {root}")
    check("stdlib only (no third-party imports)", not bad_imports, "; ".join(bad_imports))

    external: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix not in {".py", ".html", ".md", ".js", ".mjs"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for url in URL_RE.findall(text):
            if "{" in url:
                # A template or f-string, not a concrete external endpoint.
                continue
            host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
            if host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
                external.append(f"{path.relative_to(repo)}: {url}")
    check("no external URLs", not external, "; ".join(external[:5]))

    secrets = [
        str(path.relative_to(repo))
        for path in repo.rglob("*")
        if path.is_file()
        and (
            path.name in {".env", "secrets.toml"}
            or path.name.endswith((".pem", ".key", ".p12", ".pfx"))
        )
    ]
    check("no secret files", not secrets, ", ".join(secrets))


def validate(repo: Path) -> int:
    app = repo / "app.py"
    check("app.py exists", app.exists())
    check("README.md exists", (repo / "README.md").exists())
    check("tests directory exists", (repo / "tests").is_dir())
    if not app.exists():
        return 1

    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = (tests.stdout + tests.stderr).strip()
    check("unit tests pass", tests.returncode == 0, output.splitlines()[-1] if output else "")
    if tests.returncode != 0:
        print(output[-3000:])

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "blog.sqlite3"
        port = free_port()
        process = start_app(repo, db, port)
        base = f"http://127.0.0.1:{port}"
        try:
            if not wait_health(base + "/health", process):
                stderr = ""
                if process.poll() is not None:
                    _, stderr = process.communicate(timeout=5)
                check("app starts", False, stderr[-1000:])
                return 1
            check("app starts", True)

            status, body = fetch(base + "/health")
            try:
                health = json.loads(body)
            except json.JSONDecodeError:
                health = {}
            check(
                "GET /health returns status ok",
                status == 200 and health.get("status") == "ok",
                body[:200],
            )

            status, index = fetch(base + "/")
            check(
                "GET / has Mini Blog and a form",
                status == 200 and "Mini Blog" in index and "<form" in index,
                str(status),
            )

            post_status, location = post_form(
                base + "/posts", {"title": "Hello", "body": "World"}
            )
            check(
                "POST /posts redirects to the post",
                post_status in {200, 201, 302, 303}
                and (not location or location.startswith("/posts/")),
                f"{post_status} {location}",
            )
            post_path = location or "/posts/1"
            status, post = fetch(base + post_path)
            check(
                "GET the post shows title and body",
                status == 200 and "Hello" in post and "World" in post,
                str(status),
            )
            status, index = fetch(base + "/")
            check(
                "the post is listed on the index",
                status == 200 and "Hello" in index,
                str(status),
            )
        finally:
            stop_app(process)

        port = free_port()
        process = start_app(repo, db, port)
        base = f"http://127.0.0.1:{port}"
        try:
            if wait_health(base + "/health", process):
                status, post = fetch(base + post_path)
                check(
                    "posts persist across a restart",
                    status == 200 and "Hello" in post and "World" in post,
                    str(status),
                )
            else:
                check("posts persist across a restart", False, "app did not restart")
        finally:
            stop_app(process)

    static_checks(repo)
    failed = [item for item in checks if not item[1]]
    print(f"SUMMARY: {len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    return validate(args.repo.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
