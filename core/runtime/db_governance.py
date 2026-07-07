"""Persistence for governance-adjacent CRUD domains.

Split out of core/runtime/db.py per the boy-scout rule. Owns three
self-contained CRUD domains and their private row-mappers:

- tool-intent approval requests (`create/get/resolve/expire_tool_intent_approval_request`
  + `_tool_intent_approval_request_from_row`). The schema helper
  `_ensure_tool_intent_approval_request_columns` STAYS in db.py because init_db
  calls it directly; this domain's CRUD does not need it (init_db seeds the
  columns at startup).
- runtime contract-file writes (`record/get/recent/…_counts` + row-mapper +
  the lazy `_ensure_runtime_contract_file_write_table`, which init_db does NOT
  call — it moves here with the domain).
- runtime webchat execution pilots (`record/list/get_runtime_webchat_execution_pilot`
  + row-mapper). Its schema helper `_ensure_runtime_webchat_execution_pilot_table`
  STAYS in db.py (init_db calls it) and is lazily imported back here.
"""
from __future__ import annotations

import sqlite3
from uuid import uuid4

from core.runtime.db_core import connect


# ---------------------------------------------------------------------------
# Tool-intent approval requests
# ---------------------------------------------------------------------------


def create_tool_intent_approval_request(
    *,
    intent_key: str,
    intent_type: str,
    intent_target: str,
    approval_scope: str,
    approval_required: bool,
    approval_reason: str,
    requested_at: str,
    expires_at: str,
    execution_state: str = "not-executed",
) -> dict[str, object]:
    approval_id = f"tool-intent-approval-{uuid4().hex}"
    # Stamp from workspace_context so approval rows carry the requesting user.
    scheduled_for_user_id: str | None = None
    initiated_by: str | None = None
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or None
        scheduled_for_user_id = uid
        initiated_by = f"user:{uid}" if uid else "jarvis-self"
    except Exception:
        pass
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tool_intent_approval_requests (
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                approval_required,
                approval_state,
                approval_source,
                approval_reason,
                requested_at,
                expires_at,
                execution_state,
                scheduled_for_user_id,
                initiated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                1 if approval_required else 0,
                "pending",
                "none",
                approval_reason,
                requested_at,
                expires_at,
                execution_state,
                scheduled_for_user_id,
                initiated_by,
            ),
        )
        conn.commit()
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        raise RuntimeError("tool intent approval request was not persisted")
    return request


def get_tool_intent_approval_request(intent_key: str) -> dict[str, object] | None:
    normalized = str(intent_key or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                approval_required,
                approval_state,
                approval_source,
                approval_reason,
                requested_at,
                expires_at,
                resolved_at,
                resolution_reason,
                resolution_message,
                session_id,
                execution_state
            FROM tool_intent_approval_requests
            WHERE intent_key = ?
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    if row is None:
        return None
    return _tool_intent_approval_request_from_row(row)


def resolve_tool_intent_approval_request(
    intent_key: str,
    *,
    approval_state: str,
    approval_source: str,
    resolved_at: str,
    resolution_reason: str,
    resolution_message: str = "",
    session_id: str = "",
) -> dict[str, object] | None:
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        return None
    with connect() as conn:
        conn.execute(
            """
            UPDATE tool_intent_approval_requests
            SET
                approval_state = ?,
                approval_source = ?,
                resolved_at = ?,
                resolution_reason = ?,
                resolution_message = ?,
                session_id = ?
            WHERE intent_key = ?
            """,
            (
                approval_state,
                approval_source,
                resolved_at,
                resolution_reason,
                resolution_message,
                session_id,
                intent_key,
            ),
        )
        conn.commit()
    return get_tool_intent_approval_request(intent_key)


def expire_tool_intent_approval_request(
    intent_key: str,
    *,
    expired_at: str,
    resolution_reason: str,
) -> dict[str, object] | None:
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        return None
    with connect() as conn:
        conn.execute(
            """
            UPDATE tool_intent_approval_requests
            SET
                approval_state = ?,
                approval_source = ?,
                resolved_at = ?,
                resolution_reason = ?
            WHERE intent_key = ?
            """,
            (
                "expired",
                "none",
                expired_at,
                resolution_reason,
                intent_key,
            ),
        )
        conn.commit()
    return get_tool_intent_approval_request(intent_key)


def _tool_intent_approval_request_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "approval_id": str(row["approval_id"]),
        "intent_key": str(row["intent_key"]),
        "intent_type": str(row["intent_type"]),
        "intent_target": str(row["intent_target"]),
        "approval_scope": str(row["approval_scope"]),
        "approval_required": bool(row["approval_required"]),
        "approval_state": str(row["approval_state"]),
        "approval_source": str(row["approval_source"]),
        "approval_reason": str(row["approval_reason"]),
        "requested_at": str(row["requested_at"]),
        "expires_at": str(row["expires_at"]),
        "resolved_at": str(row["resolved_at"] or ""),
        "resolution_reason": str(row["resolution_reason"] or ""),
        "resolution_message": str(row["resolution_message"] or ""),
        "session_id": str(row["session_id"] or ""),
        "execution_state": str(row["execution_state"] or "not-executed"),
    }


# ---------------------------------------------------------------------------
# Runtime contract-file writes
# ---------------------------------------------------------------------------


def record_runtime_contract_file_write(
    *,
    write_id: str,
    candidate_id: str,
    target_file: str,
    canonical_key: str,
    write_status: str,
    actor: str,
    summary: str,
    content_line: str,
    created_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_contract_file_writes (
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at,
            ),
        )
        conn.commit()
    write = get_runtime_contract_file_write(write_id)
    if write is None:
        raise RuntimeError("runtime contract file write was not persisted")
    return write


def get_runtime_contract_file_write(write_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        row = conn.execute(
            """
            SELECT
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            FROM runtime_contract_file_writes
            WHERE write_id = ?
            LIMIT 1
            """,
            (write_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_contract_file_write_from_row(row)


def recent_runtime_contract_file_writes(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        rows = conn.execute(
            """
            SELECT
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            FROM runtime_contract_file_writes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_contract_file_write_from_row(row) for row in rows]


def runtime_contract_file_write_counts() -> dict[str, int]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        rows = conn.execute(
            """
            SELECT target_file, write_status, COUNT(*) AS n
            FROM runtime_contract_file_writes
            GROUP BY target_file, write_status
            """
        ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        key = f"{row['target_file']}:{row['write_status']}"
        counts[key] = int(row["n"] or 0)
    return counts


def _ensure_runtime_contract_file_write_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_contract_file_writes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            write_id TEXT NOT NULL UNIQUE,
            candidate_id TEXT NOT NULL,
            target_file TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            write_status TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            content_line TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_contract_file_writes_target
        ON runtime_contract_file_writes(target_file, id DESC)
        """
    )


def _runtime_contract_file_write_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "write_id": row["write_id"],
        "candidate_id": row["candidate_id"],
        "target_file": row["target_file"],
        "canonical_key": row["canonical_key"],
        "write_status": row["write_status"],
        "actor": row["actor"],
        "summary": row["summary"],
        "content_line": row["content_line"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Runtime webchat execution pilots
# ---------------------------------------------------------------------------
#
# NB: `_ensure_runtime_webchat_execution_pilot_table` stays in db.py because
# init_db calls it at startup. It is lazily imported inside each CRUD function
# below to avoid a top-level dependency on the db facade.


def record_runtime_webchat_execution_pilot(
    *,
    pilot_id: str,
    canonical_key: str,
    status: str,
    execution_type: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 0,
    delivery_channel: str = "webchat",
    delivery_state: str = "blocked",
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    from core.runtime.db import _ensure_runtime_webchat_execution_pilot_table
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_webchat_execution_pilots (
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                max(int(support_count or 0), 1),
                max(int(session_count or 0), 0),
                delivery_channel,
                delivery_state,
                created_at,
                updated_at,
            ),
        )
        conn.commit()
    pilot = get_runtime_webchat_execution_pilot(pilot_id)
    if pilot is None:
        raise RuntimeError("runtime webchat execution pilot was not persisted")
    return pilot


def list_runtime_webchat_execution_pilots(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    from core.runtime.db import _ensure_runtime_webchat_execution_pilot_table
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        params: list[object] = []
        where = ""
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(max(int(limit or 0), 1))
        rows = conn.execute(
            f"""
            SELECT
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            FROM runtime_webchat_execution_pilots
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_runtime_webchat_execution_pilot_from_row(row) for row in rows]


def get_runtime_webchat_execution_pilot(pilot_id: str) -> dict[str, object] | None:
    from core.runtime.db import _ensure_runtime_webchat_execution_pilot_table
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        row = conn.execute(
            """
            SELECT
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            FROM runtime_webchat_execution_pilots
            WHERE pilot_id = ?
            LIMIT 1
            """,
            (pilot_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_webchat_execution_pilot_from_row(row)


def _runtime_webchat_execution_pilot_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "pilot_id": row["pilot_id"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "execution_type": row["execution_type"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "delivery_channel": row["delivery_channel"],
        "delivery_state": row["delivery_state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
