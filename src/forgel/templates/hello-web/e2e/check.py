#!/usr/bin/env python3
"""Acceptance check for the hello-web M0 template.

The check starts the generated API on an ephemeral port, fetches ``/health`` and
``/``, asserts the expected content, and exits non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app import PROJECT_NAME, create_server  # noqa: E402

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    checks.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f" [{detail}]" if detail else ""))
    return bool(condition)


def fetch(url: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.read()


def main() -> int:
    server = create_server("127.0.0.1", 0)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{host}:{port}"

    try:
        try:
            status, body = fetch(base + "/health")
            payload = json.loads(body)
            check("health status 200", status == 200, str(status))
            check("health body ok", payload.get("status") == "ok", str(payload))
        except Exception as exc:  # noqa: BLE001 - the report must show the failure
            check("health status 200", False, repr(exc))
            check("health body ok", False, repr(exc))

        try:
            status, body = fetch(base + "/")
            html = body.decode("utf-8", errors="replace")
            check("index status 200", status == 200, str(status))
            check("index mentions project", PROJECT_NAME in html, PROJECT_NAME)
        except Exception as exc:  # noqa: BLE001
            check("index status 200", False, repr(exc))
            check("index mentions project", False, repr(exc))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    failed = [item for item in checks if not item[1]]
    print(f"SUMMARY: {len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
