"""Append-only project ledger backed by SQLite.

The ledger is the source of resumability: projects, events and checkpoints
survive a process crash. Events are scoped by a generation; a reconcile starts a
new generation without deleting the old history.
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
        self._conn = sqlite3.connect(str(self.path), timeout=30)
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
                generation  INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                seq               INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id        TEXT NOT NULL REFERENCES projects(id),
                generation        INTEGER NOT NULL DEFAULT 1,
                stage             TEXT NOT NULL,
                status            TEXT NOT NULL,
                attempt           INTEGER NOT NULL DEFAULT 1,
                idempotency_key   TEXT NOT NULL UNIQUE,
                artifact_refs     TEXT NOT NULL DEFAULT '[]',
                cost              REAL NOT NULL DEFAULT 0,
                payload           TEXT NOT NULL DEFAULT '{}',
                created_at        TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS events_project_generation
                ON events (project_id, generation, stage);

            CREATE TABLE IF NOT EXISTS checkpoints (
                project_id  TEXT PRIMARY KEY REFERENCES projects(id),
                stage       TEXT NOT NULL,
                generation  INTEGER NOT NULL DEFAULT 1,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS approvals (
                seq            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id     TEXT NOT NULL REFERENCES projects(id),
                generation     INTEGER NOT NULL,
                scope          TEXT NOT NULL,
                decision       TEXT NOT NULL,
                actor          TEXT NOT NULL,
                compliance_ack INTEGER NOT NULL DEFAULT 0,
                notes          TEXT NOT NULL DEFAULT '',
                release_sha    TEXT NOT NULL DEFAULT '',
                created_at     TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS approvals_project_scope
                ON approvals (project_id, scope, generation);

            CREATE TABLE IF NOT EXISTS sessions (
                chat_id     INTEGER PRIMARY KEY,
                project_id  TEXT NOT NULL REFERENCES projects(id),
                updated_at  TEXT NOT NULL
            );
            """
        )
        self._ensure_column("projects", "generation", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column("events", "generation", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column("checkpoints", "generation", "INTEGER NOT NULL DEFAULT 1")
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        columns = {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def create_project(
        self, project_id: str, name: str, brief: str, workspace: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO projects (id, name, brief, workspace, generation, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
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

    def current_generation(self, project_id: str) -> int:
        row = self._conn.execute(
            "SELECT generation FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return int(row["generation"]) if row is not None else 1

    def start_generation(self, project_id: str, stage: str) -> int:
        """Increment the project generation and set its checkpoint to ``stage``."""

        generation = self.current_generation(project_id) + 1
        self._conn.execute(
            "UPDATE projects SET generation = ? WHERE id = ?",
            (generation, project_id),
        )
        self._conn.commit()
        self.set_checkpoint(project_id, stage, generation)
        return generation

    def append_event(
        self,
        project_id: str,
        stage: str,
        status: str = "completed",
        idempotency_key: str | None = None,
        artifact_refs: list[str] | None = None,
        cost: float = 0.0,
        payload: dict[str, Any] | None = None,
        generation: int | None = None,
    ) -> dict[str, Any]:
        """Append an event. Re-appending the same key returns the original row."""

        if generation is None:
            generation = self.current_generation(project_id)
        key = idempotency_key or f"{project_id}:g{generation}:{stage}:{status}"
        existing = self._conn.execute(
            "SELECT * FROM events WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if existing is not None:
            return dict(existing)

        attempt = (
            self._conn.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE project_id = ? AND generation = ? AND stage = ?
                """,
                (project_id, generation, stage),
            ).fetchone()[0]
            + 1
        )
        self._conn.execute(
            """
            INSERT INTO events (
                project_id, generation, stage, status, attempt, idempotency_key,
                artifact_refs, cost, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                generation,
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

    def has_completed(
        self, project_id: str, stage: str, generation: int | None = None
    ) -> bool:
        if generation is None:
            generation = self.current_generation(project_id)
        row = self._conn.execute(
            """
            SELECT 1 FROM events
            WHERE project_id = ? AND generation = ? AND stage = ? AND status = 'completed'
            LIMIT 1
            """,
            (project_id, generation, stage),
        ).fetchone()
        return row is not None

    def events(
        self, project_id: str, generation: int | None = None
    ) -> list[dict[str, Any]]:
        if generation is None:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE project_id = ? ORDER BY seq", (project_id,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM events
                WHERE project_id = ? AND generation = ?
                ORDER BY seq
                """,
                (project_id, generation),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_checkpoint(
        self, project_id: str, stage: str, generation: int | None = None
    ) -> None:
        if generation is None:
            generation = self.current_generation(project_id)
        self._conn.execute(
            """
            INSERT INTO checkpoints (project_id, stage, generation, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id)
            DO UPDATE SET
                stage = excluded.stage,
                generation = excluded.generation,
                updated_at = excluded.updated_at
            """,
            (project_id, stage, generation, utcnow()),
        )
        self._conn.commit()

    def checkpoint_state(self, project_id: str) -> tuple[str, int] | None:
        row = self._conn.execute(
            "SELECT stage, generation FROM checkpoints WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row["stage"]), int(row["generation"])

    def checkpoint(self, project_id: str) -> str | None:
        state = self.checkpoint_state(project_id)
        return state[0] if state is not None else None

    def add_approval(
        self,
        project_id: str,
        generation: int,
        scope: str,
        decision: str,
        actor: str,
        compliance_ack: bool = False,
        notes: str = "",
        release_sha: str = "",
    ) -> dict[str, Any]:
        self._conn.execute(
            """
            INSERT INTO approvals (
                project_id, generation, scope, decision, actor,
                compliance_ack, notes, release_sha, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                generation,
                scope,
                decision,
                actor,
                int(compliance_ack),
                notes,
                release_sha,
                utcnow(),
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM approvals WHERE seq = last_insert_rowid()"
        ).fetchone()
        assert row is not None
        return dict(row)

    def approvals(
        self,
        project_id: str,
        scope: str | None = None,
        generation: int | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM approvals WHERE project_id = ?"
        params: list[Any] = [project_id]
        if scope is not None:
            query += " AND scope = ?"
            params.append(scope)
        if generation is not None:
            query += " AND generation = ?"
            params.append(generation)
        query += " ORDER BY seq"
        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def latest_approval(
        self,
        project_id: str,
        scope: str,
        generation: int | None = None,
    ) -> dict[str, Any] | None:
        rows = self.approvals(project_id, scope, generation)
        return rows[-1] if rows else None

    def set_session(self, chat_id: int, project_id: str) -> None:
        self._conn.execute(
            """
            INSERT INTO sessions (chat_id, project_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id)
            DO UPDATE SET
                project_id = excluded.project_id,
                updated_at = excluded.updated_at
            """,
            (chat_id, project_id, utcnow()),
        )
        self._conn.commit()

    def get_session(self, chat_id: int) -> str | None:
        row = self._conn.execute(
            "SELECT project_id FROM sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return str(row["project_id"]) if row is not None else None

    def clear_session(self, chat_id: int) -> None:
        self._conn.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
