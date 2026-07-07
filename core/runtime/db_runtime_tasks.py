"""Persistence for the `runtime_tasks` table — Jarvis' durable task queue.

Split out of core/runtime/db.py per the boy-scout rule. Owns its schema
(ensure_runtime_tasks_tables) plus the create/get/list/update CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_runtime_tasks_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            origin TEXT NOT NULL,
            status TEXT NOT NULL,
            goal TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'medium',
            flow_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            retry_at TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            result_summary TEXT NOT NULL DEFAULT '',
            artifact_ref TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_tasks_status_priority
        ON runtime_tasks(status, priority, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_tasks_kind_origin
        ON runtime_tasks(kind, origin, id DESC)
        """
    )


def _runtime_task_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "task_id": row["task_id"],
        "kind": row["kind"],
        "origin": row["origin"],
        "status": row["status"],
        "goal": row["goal"],
        "scope": row["scope"],
        "priority": row["priority"],
        "flow_id": row["flow_id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "owner": row["owner"],
        "retry_at": row["retry_at"],
        "blocked_reason": row["blocked_reason"],
        "result_summary": row["result_summary"],
        "artifact_ref": row["artifact_ref"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_runtime_task(
    *,
    task_id: str,
    kind: str,
    origin: str,
    status: str,
    goal: str,
    scope: str = "",
    priority: str = "medium",
    flow_id: str = "",
    session_id: str = "",
    run_id: str = "",
    owner: str = "",
    retry_at: str = "",
    blocked_reason: str = "",
    result_summary: str = "",
    artifact_ref: str = "",
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_tasks (
                task_id,
                kind,
                origin,
                status,
                goal,
                scope,
                priority,
                flow_id,
                session_id,
                run_id,
                owner,
                retry_at,
                blocked_reason,
                result_summary,
                artifact_ref,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                kind,
                origin,
                status,
                goal,
                scope,
                priority,
                flow_id,
                session_id,
                run_id,
                owner,
                retry_at,
                blocked_reason,
                result_summary,
                artifact_ref,
                created_at,
                updated_at,
            ),
        )
        conn.commit()
    task = get_runtime_task(task_id)
    if task is None:
        raise RuntimeError("runtime task was not persisted")
    return task


def get_runtime_task(task_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                task_id,
                kind,
                origin,
                status,
                goal,
                scope,
                priority,
                flow_id,
                session_id,
                run_id,
                owner,
                retry_at,
                blocked_reason,
                result_summary,
                artifact_ref,
                created_at,
                updated_at
            FROM runtime_tasks
            WHERE task_id = ?
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_task_from_row(row)


def list_runtime_tasks(
    *,
    status: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                task_id,
                kind,
                origin,
                status,
                goal,
                scope,
                priority,
                flow_id,
                session_id,
                run_id,
                owner,
                retry_at,
                blocked_reason,
                result_summary,
                artifact_ref,
                created_at,
                updated_at
            FROM runtime_tasks
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_task_from_row(row) for row in rows]


def update_runtime_task(
    task_id: str,
    *,
    status: str | None = None,
    flow_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    owner: str | None = None,
    retry_at: str | None = None,
    blocked_reason: str | None = None,
    result_summary: str | None = None,
    artifact_ref: str | None = None,
    updated_at: str,
) -> dict[str, object] | None:
    updates: list[str] = ["updated_at = ?"]
    params: list[object] = [updated_at]
    field_map = {
        "status": status,
        "flow_id": flow_id,
        "session_id": session_id,
        "run_id": run_id,
        "owner": owner,
        "retry_at": retry_at,
        "blocked_reason": blocked_reason,
        "result_summary": result_summary,
        "artifact_ref": artifact_ref,
    }
    for column, value in field_map.items():
        if value is None:
            continue
        updates.append(f"{column} = ?")
        params.append(value)
    params.append(task_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT task_id FROM runtime_tasks WHERE task_id = ? LIMIT 1",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            f"""
            UPDATE runtime_tasks
            SET {', '.join(updates)}
            WHERE task_id = ?
            """,
            tuple(params),
        )
        conn.commit()
    return get_runtime_task(task_id)
