"""Persistence for the `runtime_flows` table — multi-step flow state per task.

Split out of core/runtime/db.py per the boy-scout rule. Owns its schema
(ensure_runtime_flows_tables) plus the create/get/list/update CRUD.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def ensure_runtime_flows_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id TEXT NOT NULL UNIQUE,
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            current_step TEXT NOT NULL DEFAULT '',
            step_state TEXT NOT NULL DEFAULT '',
            plan_json TEXT NOT NULL DEFAULT '[]',
            next_action TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_flows_task_status
        ON runtime_flows(task_id, status, id DESC)
        """
    )


def _runtime_flow_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "flow_id": row["flow_id"],
        "task_id": row["task_id"],
        "status": row["status"],
        "current_step": row["current_step"],
        "step_state": row["step_state"],
        "plan_json": row["plan_json"],
        "next_action": row["next_action"],
        "last_error": row["last_error"],
        "attempt_count": int(row["attempt_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_runtime_flow(
    *,
    flow_id: str,
    task_id: str,
    status: str,
    current_step: str = "",
    step_state: str = "",
    plan_json: str = "[]",
    next_action: str = "",
    last_error: str = "",
    attempt_count: int = 0,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_flows (
                flow_id,
                task_id,
                status,
                current_step,
                step_state,
                plan_json,
                next_action,
                last_error,
                attempt_count,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                flow_id,
                task_id,
                status,
                current_step,
                step_state,
                plan_json,
                next_action,
                last_error,
                int(attempt_count),
                created_at,
                updated_at,
            ),
        )
        conn.commit()
    flow = get_runtime_flow(flow_id)
    if flow is None:
        raise RuntimeError("runtime flow was not persisted")
    return flow


def get_runtime_flow(flow_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                flow_id,
                task_id,
                status,
                current_step,
                step_state,
                plan_json,
                next_action,
                last_error,
                attempt_count,
                created_at,
                updated_at
            FROM runtime_flows
            WHERE flow_id = ?
            LIMIT 1
            """,
            (flow_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_flow_from_row(row)


def list_runtime_flows(
    *,
    status: str | None = None,
    task_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                flow_id,
                task_id,
                status,
                current_step,
                step_state,
                plan_json,
                next_action,
                last_error,
                attempt_count,
                created_at,
                updated_at
            FROM runtime_flows
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_flow_from_row(row) for row in rows]


def update_runtime_flow(
    flow_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    step_state: str | None = None,
    plan_json: str | None = None,
    next_action: str | None = None,
    last_error: str | None = None,
    attempt_count: int | None = None,
    updated_at: str,
) -> dict[str, object] | None:
    updates: list[str] = ["updated_at = ?"]
    params: list[object] = [updated_at]
    field_map: dict[str, object | None] = {
        "status": status,
        "current_step": current_step,
        "step_state": step_state,
        "plan_json": plan_json,
        "next_action": next_action,
        "last_error": last_error,
        "attempt_count": attempt_count,
    }
    for column, value in field_map.items():
        if value is None:
            continue
        updates.append(f"{column} = ?")
        params.append(value)
    params.append(flow_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT flow_id FROM runtime_flows WHERE flow_id = ? LIMIT 1",
            (flow_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            f"""
            UPDATE runtime_flows
            SET {', '.join(updates)}
            WHERE flow_id = ?
            """,
            tuple(params),
        )
        conn.commit()
    return get_runtime_flow(flow_id)
