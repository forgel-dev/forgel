"""Scripted model actions for the harness e2e.

This is a deterministic stand-in for a model. It exercises the daemon, the
coding agent tool loop, git commits, the task ledger and the external
validator without spending provider budget. A real run uses the bridge or the
API mode instead.
"""

from __future__ import annotations

import json

APP_SOURCE = r'''#!/usr/bin/env python3
"""Mini Blog: a minimal standard-library blog platform."""

import argparse
import html
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DB_PATH = os.environ.get("BLOG_DB", "blog.sqlite3")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def page(title, content):
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title></head>"
        f"<body><h1>Mini Blog</h1>{content}</body></html>"
    )


def render_index(posts):
    items = "".join(
        f'<li><a href="/posts/{row["id"]}">{html.escape(row["title"])}</a></li>'
        for row in posts
    )
    form = (
        '<form method="post" action="/posts">'
        '<input name="title" placeholder="Title" required>'
        '<textarea name="body" placeholder="Body" required></textarea>'
        '<button type="submit">Create</button></form>'
    )
    return page("Mini Blog", f"{form}<ul>{items}</ul>")


def render_post(post):
    return page(
        post["title"],
        f'<article><h2>{html.escape(post["title"])}</h2>'
        f'<p>{html.escape(post["body"])}</p></article>'
        '<p><a href="/">Back</a></p>',
    )


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, json.dumps({"status": "ok"}), "application/json")
            return
        connection = connect()
        try:
            if path == "/":
                posts = connection.execute(
                    "SELECT id, title FROM posts ORDER BY id"
                ).fetchall()
                self._send(200, render_index(posts))
                return
            if path.startswith("/posts/"):
                try:
                    post_id = int(path.rsplit("/", 1)[1])
                except ValueError:
                    self._send(404, page("Not found", "<p>Not found</p>"))
                    return
                post = connection.execute(
                    "SELECT id, title, body FROM posts WHERE id = ?",
                    (post_id,),
                ).fetchone()
                if post is None:
                    self._send(404, page("Not found", "<p>Not found</p>"))
                    return
                self._send(200, render_post(post))
                return
            self._send(404, page("Not found", "<p>Not found</p>"))
        finally:
            connection.close()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/posts":
            self._send(404, "not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        title = (form.get("title") or [""])[0].strip()
        body = (form.get("body") or [""])[0].strip()
        if not title or not body:
            self._send(400, page("Error", "<p>Title and body are required</p>"))
            return
        connection = connect()
        try:
            cursor = connection.execute(
                "INSERT INTO posts (title, body, created_at) VALUES (?, ?, ?)",
                (title, body, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            connection.commit()
            post_id = cursor.lastrowid
        finally:
            connection.close()
        self.send_response(303)
        self.send_header("Location", f"/posts/{post_id}")
        self.end_headers()

    def log_message(self, *args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8000"))
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
'''

TEST_SOURCE = r'''from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_TMP = tempfile.TemporaryDirectory()
os.environ["BLOG_DB"] = str(Path(_TMP.name) / "test.sqlite3")

import app  # noqa: E402


class BlogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        host, port = cls.server.server_address
        cls.base = f"http://{host}:{port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_health(self):
        with urllib.request.urlopen(self.base + "/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["status"], "ok")

    def test_index_has_form(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as response:
            text = response.read().decode("utf-8")
            self.assertIn("Mini Blog", text)
            self.assertIn("<form", text)

    def test_create_and_view_post(self):
        data = urllib.parse.urlencode(
            {"title": "Hello", "body": "World"}
        ).encode("utf-8")
        with urllib.request.urlopen(self.base + "/posts", data=data, timeout=5) as response:
            text = response.read().decode("utf-8")
        self.assertIn("Hello", text)
        self.assertIn("World", text)

    def test_unknown_post_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(self.base + "/posts/9999", timeout=5)
        self.assertEqual(raised.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
'''

README_SOURCE = """# Mini Blog

A minimal blog platform built by Forgel.

## Run

```bash
python app.py --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Posts are stored in `blog.sqlite3`; set `BLOG_DB`
to use another path.

## Test

```bash
python -m unittest discover -s tests
```
"""


def responses() -> list[str]:
    return [
        json.dumps(
            {
                "action": "write_file",
                "path": "app.py",
                "content": APP_SOURCE,
            }
        ),
        json.dumps(
            {
                "action": "write_file",
                "path": "tests/test_blog.py",
                "content": TEST_SOURCE,
            }
        ),
        json.dumps(
            {
                "action": "write_file",
                "path": "README.md",
                "content": README_SOURCE,
            }
        ),
        json.dumps(
            {
                "action": "run",
                "command": [
                    "python",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                ],
            }
        ),
        json.dumps(
            {
                "action": "done",
                "summary": "implemented Mini Blog with SQLite and tests",
            }
        ),
    ]
