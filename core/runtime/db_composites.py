"""Composite tools store — Jarvis proposals of new tool sequences.

A composite is a named sequence of existing tool calls, with
templated arguments that can reference input params or earlier-step
results. No arbitrary Python — only composition.

Lifecycle: proposed → approved → active | revoked.
Only 'approved' composites can be invoked.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


VALID_STATUSES = {"proposed", "approved", "revoked"}


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS composite_tools (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            input_schema TEXT NOT NULL,
            steps TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            approved_by TEXT,
            created_by TEXT,
            invocation_count INTEGER NOT NULL DEFAULT 0,
            last_invoked_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_composites_status "
        "ON composite_tools (status, created_at DESC)"
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def propose_composite(
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
    steps: list[dict[str, Any]],
    created_by: str | None = None,
) -> dict[str, Any]:
    """Insert a new proposal. Name must be unique."""
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO composite_tools (
                name, description, input_schema, steps, status,
                created_at, created_by
            ) VALUES (?, ?, ?, ?, 'proposed', ?, ?)
            """,
            (
                name,
                description.strip(),
                json.dumps(input_schema),
                json.dumps(steps),
                now,
                created_by,
            ),
        )
        conn.commit()
    result = get_composite(name)
    assert result is not None
    return result


def approve_composite(
    name: str, *, approved_by: str | None = None
) -> dict[str, Any] | None:
    if not get_composite(name):
        return None
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE composite_tools SET status='approved', "
            "approved_at=?, approved_by=? WHERE name=?",
            (now, approved_by, name),
        )
        conn.commit()
    return get_composite(name)


def revoke_composite(name: str) -> dict[str, Any] | None:
    if not get_composite(name):
        return None
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE composite_tools SET status='revoked' WHERE name=?",
            (name,),
        )
        conn.commit()
    return get_composite(name)


def get_composite(name: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM composite_tools WHERE name=?", (name,)
        ).fetchone()
    if row is None:
        return None
    return _decode(dict(row))


def list_composites(
    *, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    where = ""
    params: list[Any] = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    query = (
        f"SELECT * FROM composite_tools {where} "
        "ORDER BY created_at DESC LIMIT ?"
    )
    params.append(int(limit))
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(query, params).fetchall()
    return [_decode(dict(r)) for r in rows]


def record_invocation(name: str) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE composite_tools SET invocation_count = invocation_count + 1, "
            "last_invoked_at = ? WHERE name = ?",
            (now, name),
        )
        conn.commit()


def delete_composite(name: str) -> bool:
    with connect() as conn:
        _ensure_tables(conn)
        cur = conn.execute(
            "DELETE FROM composite_tools WHERE name=?", (name,)
        )
        conn.commit()
    return (cur.rowcount or 0) > 0


def count_composites(*, status: str | None = None) -> int:
    where = ""
    params: list[Any] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM composite_tools {where}",
            params,
        ).fetchone()
    return int(row["c"] if row else 0)


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    try:
        row["input_schema"] = json.loads(row.get("input_schema") or "{}")
    except Exception:
        row["input_schema"] = {}
    try:
        row["steps"] = json.loads(row.get("steps") or "[]")
    except Exception:
        row["steps"] = []
    return row
