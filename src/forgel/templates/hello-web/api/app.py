#!/usr/bin/env python3
"""Minimal HTTP server for the hello-web M0 template.

No third-party dependencies. Serves the static frontend from ``../web`` and a
JSON health endpoint at ``/health``.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
from pathlib import Path

PROJECT_NAME = "__PROJECT_NAME__"
ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT / "web"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)  # type: ignore[arg-type]

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/health":
            body = json.dumps({"status": "ok", "project": PROJECT_NAME}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        return


def create_server(
    host: str = "127.0.0.1", port: int = 0
) -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Serve {PROJECT_NAME}")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    host, port = server.server_address
    print(f"http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
