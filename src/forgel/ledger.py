"""Append-only project ledger backed by SQLite.

The ledger is the source of resumability: projects, events and checkpoints
survive a process crash. Every stage transition is recorded before the next
stage starts.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in name)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "project"


def new_project_id(name: str) -> str:
    return f"{slugify(name)}-{uuid.uuid4().hex[:8]}"


class Ledger:
    """SQLite-backed project, event and checkpoint storage."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                brief       TEXT NOT NULL,
                recipe_id   TEXT,
                workspace   TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                seq               INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id        TEXT NOT NULL REFERENCES projects(id),
                stage             TEXT NOT NULL,
                status            TEXT NOT NULL,
                attempt           INTEGER NOT NULL DEFAULT 1,
                idempotency_key   TEXT NOT NULL UNIQUE,
                artifact_refs     TEXT NOT NULL DEFAULT '[]',
                cost              REAL NOT NULL DEFAULT 0,
                payload           TEXT NOT NULL DEFAULT '{}',
                created_at        TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS events_project_stage
                ON events (project_id, stage);

            CREATE TABLE IF NOT EXISTS checkpoints (
                project_id  TEXT PRIMARY KEY REFERENCES projects(id),
                stage       TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def create_project(
        self, project_id: str, name: str, brief: str, workspace: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO projects (id, name, brief, workspace, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, name, brief, workspace, utcnow()),
        )
        self._conn.commit()

    def set_recipe(self, project_id: str, recipe_id: str) -> None:
        self._conn.execute(
            "UPDATE projects SET recipe_id = ? WHERE id = ?", (recipe_id, project_id)
        )
        self._conn.commit()

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def list_projects(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def append_event(
        self,
        project_id: str,
        stage: str,
        status: str = "completed",
        idempotency_key: str | None = None,
        artifact_refs: list[str] | None = None,
        cost: float = 0.0,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append an event. Re-appending the same key returns the original row."""

        key = idempotency_key or f"{project_id}:{stage}:{status}"
        existing = self._conn.execute(
            "SELECT * FROM events WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if existing is not None:
            return dict(existing)

        attempt = (
            self._conn.execute(
                "SELECT COUNT(*) FROM events WHERE project_id = ? AND stage = ?",
                (project_id, stage),
            ).fetchone()[0]
            + 1
        )
        self._conn.execute(
            """
            INSERT INTO events (
                project_id, stage, status, attempt, idempotency_key,
                artifact_refs, cost, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                stage,
                status,
                attempt,
                key,
                json.dumps(artifact_refs or []),
                cost,
                json.dumps(payload or {}),
                utcnow(),
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM events WHERE idempotency_key = ?", (key,)
        ).fetchone()
        assert row is not None
        return dict(row)

    def has_completed(self, project_id: str, stage: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM events
            WHERE project_id = ? AND stage = ? AND status = 'completed'
            LIMIT 1
            """,
            (project_id, stage),
        ).fetchone()
        return row is not None

    def events(self, project_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE project_id = ? ORDER BY seq", (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def set_checkpoint(self, project_id: str, stage: str) -> None:
        self._conn.execute(
            """
            INSERT INTO checkpoints (project_id, stage, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(project_id)
            DO UPDATE SET stage = excluded.stage, updated_at = excluded.updated_at
            """,
            (project_id, stage, utcnow()),
        )
        self._conn.commit()

    def checkpoint(self, project_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT stage FROM checkpoints WHERE project_id = ?", (project_id,)
        ).fetchone()
        return str(row["stage"]) if row is not None else None

    def close(self) -> None:
        self._conn.close()
