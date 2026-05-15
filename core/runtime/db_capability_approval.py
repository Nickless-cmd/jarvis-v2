"""Capability approval + approval feedback CRUD.

Domæne: brugerens explicit approval/decline af capability-anmodninger
plus efterfølgende feedback. Tabeller: capability_approval_requests,
approval_feedback_log (begge oprettet i init_db; column-extensions
nedenfor).

Importerer KUN fra core.runtime.db_core (ingen cirkulære imports).
Re-eksporteres via core.runtime.db (facaden).

Split-spec: docs/superpowers/specs/2026-05-15-db-split-design.md
"""
from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db_core import (
    _install_ensure_once_cache_for,
    connect,
)


# === capability_approval_request CRUD (verbatim from db.py L4341-4689) ===
def recent_capability_approval_requests(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_capability_approval_request_from_row(row) for row in rows]


def get_capability_approval_request(request_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    return _capability_approval_request_from_row(row)


def approve_capability_approval_request(
    request_id: str, *, approved_at: str
) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None

        status = str(row["status"] or "")
        final_approved_at = row["approved_at"]
        if status == "pending":
            conn.execute(
                """
                UPDATE capability_approval_requests
                SET status = ?, approved_at = ?
                WHERE request_id = ?
                """,
                ("approved", approved_at, request_id),
            )
            conn.commit()
            status = "approved"
            final_approved_at = approved_at

    return _capability_approval_request_from_row(
        row,
        status=status,
        approved_at=final_approved_at,
    )


def record_capability_approval_request_execution(
    request_id: str,
    *,
    executed_at: str,
    invocation_status: str,
    invocation_execution_mode: str,
) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE capability_approval_requests
            SET
                executed = ?,
                executed_at = ?,
                invocation_status = ?,
                invocation_execution_mode = ?
            WHERE request_id = ?
            """,
            (1, executed_at, invocation_status, invocation_execution_mode, request_id),
        )
        conn.commit()
    return _capability_approval_request_from_row(
        row,
        executed=True,
        executed_at=executed_at,
        invocation_status=invocation_status,
        invocation_execution_mode=invocation_execution_mode,
    )


def _capability_approval_request_from_row(
    row: sqlite3.Row,
    *,
    status: str | None = None,
    approved_at: str | None = None,
    executed: bool | None = None,
    executed_at: str | None = None,
    invocation_status: str | None = None,
    invocation_execution_mode: str | None = None,
) -> dict[str, object]:
    return {
        "request_id": row["request_id"],
        "capability_id": row["capability_id"],
        "capability_name": row["capability_name"],
        "capability_kind": row["capability_kind"],
        "execution_mode": row["execution_mode"],
        "approval_policy": row["approval_policy"],
        "run_id": row["run_id"],
        "proposal_target_path": row["proposal_target_path"],
        "proposal_content": row["proposal_content"],
        "proposal_content_summary": row["proposal_content_summary"],
        "proposal_content_fingerprint": row["proposal_content_fingerprint"],
        "proposal_content_source": row["proposal_content_source"],
        "proposal_reason": row["proposal_reason"],
        "requested_at": row["requested_at"],
        "status": status if status is not None else row["status"],
        "approved_at": approved_at if approved_at is not None else row["approved_at"],
        "executed": executed if executed is not None else bool(row["executed"]),
        "executed_at": executed_at if executed_at is not None else row["executed_at"],
        "invocation_status": (
            invocation_status
            if invocation_status is not None
            else row["invocation_status"]
        ),
        "invocation_execution_mode": (
            invocation_execution_mode
            if invocation_execution_mode is not None
            else row["invocation_execution_mode"]
        ),
    }


def _ensure_capability_approval_request_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(capability_approval_requests)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "approved_at": "TEXT",
        "executed": "INTEGER NOT NULL DEFAULT 0",
        "executed_at": "TEXT",
        "invocation_status": "TEXT",
        "invocation_execution_mode": "TEXT",
        "proposal_target_path": "TEXT",
        "proposal_content": "TEXT",
        "proposal_content_summary": "TEXT",
        "proposal_content_fingerprint": "TEXT",
        "proposal_content_source": "TEXT",
        "proposal_reason": "TEXT",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(
            f"ALTER TABLE capability_approval_requests ADD COLUMN {name} {spec}"
        )


def latest_capability_approval_request(
    *,
    execution_mode: str | None = None,
    include_executed: bool = True,
) -> dict[str, object] | None:
    clauses: list[str] = []
    params: list[object] = []
    if execution_mode:
        clauses.append("execution_mode = ?")
        params.append(execution_mode)
    if not include_executed:
        clauses.append("executed = 0")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            {where}
            ORDER BY id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    if row is None:
        return None
    return _capability_approval_request_from_row(row)


def latest_approved_capability_approval_request(
    *,
    execution_mode: str | None = None,
    capability_id: str | None = None,
) -> dict[str, object] | None:
    clauses = ["status = 'approved'", "approved_at IS NOT NULL"]
    params: list[object] = []
    if execution_mode:
        clauses.append("execution_mode = ?")
        params.append(execution_mode)
    if capability_id:
        clauses.append("capability_id = ?")
        params.append(capability_id)
    where = f"WHERE {' AND '.join(clauses)}"
    with connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            {where}
            ORDER BY approved_at DESC, id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    if row is None:
        return None
    return _capability_approval_request_from_row(row)

# === approval_feedback CRUD (verbatim from db.py L4876-5018) ===
def insert_approval_feedback(
    *,
    recorded_at: str,
    intent_key: str,
    approval_state: str,
    approval_source: str,
    tool_name: str = "",
    resolution_reason: str = "",
    resolution_message: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id, recorded_at, intent_key, approval_state, approval_source,
                   tool_name, resolution_reason, resolution_message, session_id
            FROM approval_feedback_log
            WHERE recorded_at = ?
              AND intent_key = ?
              AND approval_state = ?
              AND approval_source = ?
              AND resolution_reason = ?
              AND resolution_message = ?
              AND session_id = ?
            LIMIT 1
            """,
            (
                recorded_at,
                intent_key,
                approval_state,
                approval_source,
                resolution_reason,
                resolution_message,
                session_id,
            ),
        ).fetchone()
        if existing is not None:
            return _approval_feedback_from_row(existing)
        cursor = conn.execute(
            """
            INSERT INTO approval_feedback_log (
                recorded_at,
                intent_key,
                approval_state,
                approval_source,
                tool_name,
                resolution_reason,
                resolution_message,
                session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recorded_at,
                intent_key,
                approval_state,
                approval_source,
                tool_name,
                resolution_reason,
                resolution_message,
                session_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, recorded_at, intent_key, approval_state, approval_source,
                   tool_name, resolution_reason, resolution_message, session_id
            FROM approval_feedback_log
            WHERE id = ?
            """,
            (int(cursor.lastrowid),),
        ).fetchone()
    if row is None:
        raise RuntimeError("approval feedback was not persisted")
    return _approval_feedback_from_row(row)


def list_approval_feedback(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, recorded_at, intent_key, approval_state, approval_source,
                   tool_name, resolution_reason, resolution_message, session_id
            FROM approval_feedback_log
            ORDER BY recorded_at DESC, id DESC
            LIMIT ?
            """,
            (max(int(limit), 1),),
        ).fetchall()
    return [_approval_feedback_from_row(row) for row in rows]


def approval_feedback_stats_by_tool(days: int = 7) -> list[dict[str, object]]:
    cutoff = (datetime.now(UTC) - timedelta(days=max(int(days), 1))).isoformat()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                tool_name,
                SUM(CASE WHEN approval_state = 'approved' THEN 1 ELSE 0 END) AS approved_count,
                SUM(CASE WHEN approval_state = 'denied' THEN 1 ELSE 0 END) AS denied_count,
                SUM(CASE WHEN approval_state = 'expired' THEN 1 ELSE 0 END) AS expired_count,
                COUNT(*) AS total_count
            FROM approval_feedback_log
            WHERE recorded_at >= ?
            GROUP BY tool_name
            ORDER BY total_count DESC, tool_name ASC
            """,
            (cutoff,),
        ).fetchall()
    return [
        {
            "tool_name": str(row["tool_name"] or ""),
            "approved_count": int(row["approved_count"] or 0),
            "denied_count": int(row["denied_count"] or 0),
            "expired_count": int(row["expired_count"] or 0),
            "total_count": int(row["total_count"] or 0),
        }
        for row in rows
    ]


def count_approval_feedback() -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM approval_feedback_log"
        ).fetchone()
    return int((row or {})["count"] or 0)


def _approval_feedback_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": int(row["id"]),
        "recorded_at": str(row["recorded_at"] or ""),
        "intent_key": str(row["intent_key"] or ""),
        "approval_state": str(row["approval_state"] or ""),
        "approval_source": str(row["approval_source"] or ""),
        "tool_name": str(row["tool_name"] or ""),
        "resolution_reason": str(row["resolution_reason"] or ""),
        "resolution_message": str(row["resolution_message"] or ""),
        "session_id": str(row["session_id"] or ""),
    }


# Wrap _ensure_*_table funcs på dette modul med once-cache.
_install_ensure_once_cache_for(__name__)
