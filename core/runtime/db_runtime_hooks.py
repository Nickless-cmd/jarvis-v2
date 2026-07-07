"""Persistence for the `runtime_hook_dispatches` table.

Split out of core/runtime/db.py per the boy-scout rule. Owns its schema
(ensure_runtime_hooks_tables) plus the record/get/list CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_runtime_hooks_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_hook_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL UNIQUE,
            event_kind TEXT NOT NULL,
            status TEXT NOT NULL,
            task_id TEXT NOT NULL DEFAULT '',
            flow_id TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_hook_dispatches_status
        ON runtime_hook_dispatches(status, id DESC)
        """
    )


def record_runtime_hook_dispatch(
    *,
    event_id: int,
    event_kind: str,
    status: str,
    task_id: str = "",
    flow_id: str = "",
    summary: str = "",
    created_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_hook_dispatches (
                event_id,
                event_kind,
                status,
                task_id,
                flow_id,
                summary,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                event_kind = excluded.event_kind,
                status = excluded.status,
                task_id = excluded.task_id,
                flow_id = excluded.flow_id,
                summary = excluded.summary,
                created_at = excluded.created_at
            """,
            (
                int(event_id),
                event_kind,
                status,
                task_id,
                flow_id,
                summary,
                created_at,
            ),
        )
        conn.commit()
    dispatch = get_runtime_hook_dispatch(event_id)
    if dispatch is None:
        raise RuntimeError("runtime hook dispatch was not persisted")
    return dispatch


def get_runtime_hook_dispatch(event_id: int) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                event_id,
                event_kind,
                status,
                task_id,
                flow_id,
                summary,
                created_at
            FROM runtime_hook_dispatches
            WHERE event_id = ?
            LIMIT 1
            """,
            (int(event_id),),
        ).fetchone()
    if row is None:
        return None
    return {
        "event_id": int(row["event_id"]),
        "event_kind": row["event_kind"],
        "status": row["status"],
        "task_id": row["task_id"],
        "flow_id": row["flow_id"],
        "summary": row["summary"],
        "created_at": row["created_at"],
    }


def list_runtime_hook_dispatches(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                event_id,
                event_kind,
                status,
                task_id,
                flow_id,
                summary,
                created_at
            FROM runtime_hook_dispatches
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [
        {
            "event_id": int(row["event_id"]),
            "event_kind": row["event_kind"],
            "status": row["status"],
            "task_id": row["task_id"],
            "flow_id": row["flow_id"],
            "summary": row["summary"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
