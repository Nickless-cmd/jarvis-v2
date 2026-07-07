"""Persistence for the `capability_invocations` table.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema
(ensure_capability_tables) plus the recent-read helper and the
approval-column migration used by init_db.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_capability_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capability_invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capability_id TEXT NOT NULL,
            capability_name TEXT,
            capability_kind TEXT,
            status TEXT NOT NULL,
            execution_mode TEXT NOT NULL,
            invoked_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            result_preview TEXT,
            detail TEXT,
            approval_policy TEXT,
            approval_required INTEGER NOT NULL DEFAULT 0,
            approved INTEGER NOT NULL DEFAULT 0,
            granted INTEGER NOT NULL DEFAULT 0,
            run_id TEXT
        )
        """
    )


def recent_capability_invocations(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                capability_id,
                capability_name,
                capability_kind,
                status,
                execution_mode,
                invoked_at,
                finished_at,
                result_preview,
                detail,
                approval_policy,
                approval_required,
                approved,
                granted,
                run_id
            FROM capability_invocations
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "capability_id": row["capability_id"],
            "capability_name": row["capability_name"],
            "capability_kind": row["capability_kind"],
            "status": row["status"],
            "execution_mode": row["execution_mode"],
            "invoked_at": row["invoked_at"],
            "finished_at": row["finished_at"],
            "result_preview": row["result_preview"],
            "detail": row["detail"],
            "approval": {
                "policy": row["approval_policy"],
                "required": bool(row["approval_required"]),
                "approved": bool(row["approved"]),
                "granted": bool(row["granted"]),
            },
            "run_id": row["run_id"],
        }
        for row in rows
    ]


def _ensure_capability_invocation_approval_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(capability_invocations)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "approval_policy": "TEXT",
        "approval_required": "INTEGER NOT NULL DEFAULT 0",
        "approved": "INTEGER NOT NULL DEFAULT 0",
        "granted": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE capability_invocations ADD COLUMN {name} {spec}")
