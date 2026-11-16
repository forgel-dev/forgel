"""Durable client sessions.

The client stays stateless between calls: the engine remembers which project a
session key points at. The default key is ``local`` and it maps to the same
ledger row the local console uses (chat id 0), so a project selected in one
channel is visible in the others.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .layout import ProjectLayout
from .ledger import Ledger

DEFAULT_SESSION = "local"


def session_key(value: int | str | None = None) -> str:
    """Normalize a session key; the empty key and chat id 0 are ``local``."""

    text = str(value).strip() if value is not None else ""
    if not text or text == "0":
        return DEFAULT_SESSION
    return text


def ledger_key(value: int | str | None = None) -> int:
    """The integer session row used by the ledger.

    ``local`` is chat id 0 so the console selection is shared with the client.
    A numeric key is used as is; any other key becomes a stable 63-bit hash.
    """

    name = session_key(value)
    if name == DEFAULT_SESSION:
        return 0
    if name.lstrip("-").isdigit():
        return int(name)
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


def get_session_project(
    ledger: Ledger, key: int | str | None = None
) -> str | None:
    return ledger.get_session(ledger_key(key))


def set_session_project(
    ledger: Ledger, key: int | str | None, project_id: str
) -> str:
    name = session_key(key)
    ledger.set_session(ledger_key(name), str(project_id))
    return name


def clear_session_project(ledger: Ledger, key: int | str | None = None) -> str:
    name = session_key(key)
    ledger.clear_session(ledger_key(name))
    return name


def session_view(
    ledger: Ledger, key: int | str | None = None
) -> dict[str, Any]:
    """The session key, its selected project id and the project record."""

    name = session_key(key)
    project_id = ledger.get_session(ledger_key(name))
    project = ledger.get_project(project_id) if project_id else None
    if project_id and project is None:
        ledger.clear_session(ledger_key(name))
        project_id = None
    return {
        "session": name,
        "project": project_id,
        "name": project["name"] if project is not None else None,
    }


def conversation(
    ledger: Ledger,
    session: int | str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Recent turns of the session, read through the engine."""

    from .agent import load_history

    project_id = get_session_project(ledger, session)
    if not project_id:
        return []
    project = ledger.get_project(project_id)
    if project is None:
        return []
    layout = ProjectLayout.detect(project["workspace"])
    rows = load_history(
        layout, limit=max(1, int(limit)), session=str(ledger_key(session))
    )
    return [
        {
            "role": str(row.get("role")),
            "text": str(row.get("text") or ""),
            "at": str(row.get("at") or ""),
        }
        for row in rows
        if row.get("role") in {"user", "assistant"}
        and str(row.get("text") or "").strip()
    ]
