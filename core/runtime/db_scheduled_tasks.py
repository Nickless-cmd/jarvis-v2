"""Scheduled tasks — engangs-planlagte opgaver Jarvis skal udføre på et tidspunkt
(modsat recurring_tasks som er gentagne).

Udskilt fra db.py (Boy Scout-reglen, 2026-06-15) — én naturlig sammenhængende
enhed: tabel-DDL + create/get/get_due/mark_fired/mark_cancelled/update/list +
row→dict-helper. Re-eksporteres fra db.py for bagudkompat (veto_gate,
scheduled_tasks, prompt_contract, visible_runs, jarvisx-route m.fl. importerer
via core.runtime.db).

Multi-user (#76/#80/#153): list_scheduled_tasks scopes til brugerens egne tasks
(+ NULL/'' = generel/owner); RUNNEREN get_due_scheduled_tasks er bevidst uscopet
(skal fyre ALLE forfaldne tasks).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.runtime.db_core import connect


def _ensure_scheduled_tasks_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            focus TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'jarvis-tool',
            status TEXT NOT NULL DEFAULT 'pending',
            run_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            fired_at TEXT NOT NULL DEFAULT '',
            cancelled_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            scheduled_for_user_id TEXT,
            initiated_by TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status_run_at "
        "ON scheduled_tasks(status, run_at, id DESC)"
    )


def _row_get(row: sqlite3.Row, key: str, default=None):
    """Safe column access — returns default if column missing from row."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def _scheduled_task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "task_id": row["task_id"],
        "focus": row["focus"],
        "source": row["source"],
        "status": row["status"],
        "run_at": row["run_at"],
        "created_at": row["created_at"],
        "fired_at": row["fired_at"],
        "cancelled_at": row["cancelled_at"],
        "updated_at": row["updated_at"],
        "scheduled_for_user_id": _row_get(row, "scheduled_for_user_id"),
    }


def create_scheduled_task(
    *,
    task_id: str,
    focus: str,
    source: str = "jarvis-tool",
    run_at: str,
    created_at: str,
    updated_at: str,
) -> dict[str, Any]:
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        conn.execute(
            """
            INSERT INTO scheduled_tasks (task_id, focus, source, status, run_at, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?)
            """,
            (task_id, focus, source, run_at, created_at, updated_at),
        )
        conn.commit()
    return get_scheduled_task(task_id)


def get_scheduled_task(task_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        row = conn.execute(
            "SELECT * FROM scheduled_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
    return _scheduled_task_from_row(row) if row else None


def get_due_scheduled_tasks(now_iso: str) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM scheduled_tasks
            WHERE status = 'pending' AND run_at <= ?
            ORDER BY run_at ASC
            """,
            (now_iso,),
        ).fetchall()
    return [_scheduled_task_from_row(r) for r in rows]


def mark_scheduled_task_fired(task_id: str, fired_at: str, updated_at: str) -> None:
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        conn.execute(
            """
            UPDATE scheduled_tasks
            SET status = 'fired', fired_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (fired_at, updated_at, task_id),
        )
        conn.commit()


def mark_scheduled_task_cancelled(task_id: str, cancelled_at: str, updated_at: str) -> None:
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        conn.execute(
            """
            UPDATE scheduled_tasks
            SET status = 'cancelled', cancelled_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (cancelled_at, updated_at, task_id),
        )
        conn.commit()


def update_scheduled_task(task_id: str, *, focus: str | None = None, run_at: str | None = None, updated_at: str) -> dict[str, Any] | None:
    """Opdater focus og/eller run_at på en pending task. Returnerer den opdaterede
    task eller None hvis ikke fundet/ikke pending."""
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        fields: list[str] = []
        params: list[object] = []
        if focus is not None:
            fields.append("focus = ?")
            params.append(focus)
        if run_at is not None:
            fields.append("run_at = ?")
            params.append(run_at)
        if not fields:
            return get_scheduled_task(task_id)
        fields.append("updated_at = ?")
        params.append(updated_at)
        params.append(task_id)
        conn.execute(
            f"UPDATE scheduled_tasks SET {', '.join(fields)} WHERE task_id = ? AND status = 'pending'",
            params,
        )
        conn.commit()
    return get_scheduled_task(task_id)


def list_scheduled_tasks(limit: int = 20) -> list[dict[str, Any]]:
    # PRIVATLIVS-GUARD: scope til brugerens egne tasks (+ NULL/'' = generel/owner),
    # så list-tool'et ikke afslører en anden brugers schedulede opgaver. RUNNEREN
    # (get_due_scheduled_tasks) er bevidst U-scopet — den skal fyre ALLE forfaldne.
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    with connect() as conn:
        _ensure_scheduled_tasks_table(conn)
        if _current_uid:
            rows = conn.execute(
                """
                SELECT * FROM scheduled_tasks
                WHERE scheduled_for_user_id = ?
                   OR scheduled_for_user_id IS NULL OR scheduled_for_user_id = ''
                ORDER BY run_at ASC
                LIMIT ?
                """,
                (_current_uid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks ORDER BY run_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_scheduled_task_from_row(r) for r in rows]
