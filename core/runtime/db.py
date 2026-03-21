from __future__ import annotations

import sqlite3
from pathlib import Path

from core.runtime.config import STATE_DIR

DB_PATH = Path(STATE_DIR) / "jarvis.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT NOT NULL,
                text_preview TEXT,
                error TEXT,
                capability_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_work_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT NOT NULL,
                user_message_preview TEXT,
                capability_id TEXT,
                work_preview TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_work_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                user_message_preview TEXT,
                capability_id TEXT,
                work_preview TEXT,
                projection_source TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_inner_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                status TEXT NOT NULL,
                note_kind TEXT NOT NULL DEFAULT '',
                focus TEXT NOT NULL DEFAULT '',
                uncertainty TEXT NOT NULL DEFAULT '',
                identity_alignment TEXT NOT NULL DEFAULT '',
                work_signal TEXT NOT NULL DEFAULT '',
                private_summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_growth_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                learning_kind TEXT NOT NULL,
                lesson TEXT NOT NULL,
                mistake_signal TEXT NOT NULL DEFAULT '',
                helpful_signal TEXT NOT NULL DEFAULT '',
                identity_signal TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_self_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                identity_focus TEXT NOT NULL,
                preferred_work_mode TEXT NOT NULL,
                recurring_tension TEXT NOT NULL,
                growth_direction TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                capability_id TEXT NOT NULL,
                capability_name TEXT,
                capability_kind TEXT,
                execution_mode TEXT NOT NULL,
                approval_policy TEXT,
                run_id TEXT,
                requested_at TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_at TEXT,
                executed INTEGER NOT NULL DEFAULT 0,
                executed_at TEXT,
                invocation_status TEXT,
                invocation_execution_mode TEXT
            )
            """
        )
        _ensure_private_inner_note_columns(conn)
        _ensure_capability_invocation_approval_columns(conn)
        _ensure_capability_approval_request_columns(conn)
        conn.commit()


def recent_visible_runs(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                lane,
                provider,
                model,
                status,
                started_at,
                finished_at,
                text_preview,
                error,
                capability_id
            FROM visible_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "text_preview": row["text_preview"],
            "error": row["error"],
            "capability_id": row["capability_id"],
        }
        for row in rows
    ]


def recent_visible_work_units(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                started_at,
                finished_at,
                user_message_preview,
                capability_id,
                work_preview
            FROM visible_work_units
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
        }
        for row in rows
    ]


def recent_visible_work_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            FROM visible_work_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
            "projection_source": row["projection_source"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }
        for row in rows
    ]


def record_private_inner_note(
    *,
    note_id: str,
    source: str,
    run_id: str,
    work_id: str,
    status: str,
    note_kind: str,
    focus: str,
    uncertainty: str,
    identity_alignment: str,
    work_signal: str,
    private_summary: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_inner_notes (
                note_id, source, run_id, work_id, status, note_kind, focus,
                uncertainty, identity_alignment, work_signal, private_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                source=excluded.source,
                work_id=excluded.work_id,
                status=excluded.status,
                note_kind=excluded.note_kind,
                focus=excluded.focus,
                uncertainty=excluded.uncertainty,
                identity_alignment=excluded.identity_alignment,
                work_signal=excluded.work_signal,
                private_summary=excluded.private_summary,
                created_at=excluded.created_at
            """,
            (
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at,
            ),
        )
        conn.commit()


def recent_private_inner_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at
            FROM private_inner_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "status": row["status"],
            "note_kind": row["note_kind"],
            "focus": row["focus"],
            "uncertainty": row["uncertainty"],
            "identity_alignment": row["identity_alignment"],
            "work_signal": row["work_signal"],
            "private_summary": row["private_summary"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_growth_note(
    *,
    record_id: str,
    source: str,
    run_id: str,
    work_id: str,
    learning_kind: str,
    lesson: str,
    mistake_signal: str,
    helpful_signal: str,
    identity_signal: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_growth_notes (
                record_id, source, run_id, work_id, learning_kind, lesson,
                mistake_signal, helpful_signal, identity_signal, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                record_id=excluded.record_id,
                source=excluded.source,
                work_id=excluded.work_id,
                learning_kind=excluded.learning_kind,
                lesson=excluded.lesson,
                mistake_signal=excluded.mistake_signal,
                helpful_signal=excluded.helpful_signal,
                identity_signal=excluded.identity_signal,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def recent_private_growth_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at
            FROM private_growth_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "record_id": row["record_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "learning_kind": row["learning_kind"],
            "lesson": row["lesson"],
            "mistake_signal": row["mistake_signal"],
            "helpful_signal": row["helpful_signal"],
            "identity_signal": row["identity_signal"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_self_model(
    *,
    model_id: str,
    source: str,
    identity_focus: str,
    preferred_work_mode: str,
    recurring_tension: str,
    growth_direction: str,
    confidence: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_self_models (
                model_id, source, identity_focus, preferred_work_mode,
                recurring_tension, growth_direction, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_id) DO UPDATE SET
                source=excluded.source,
                identity_focus=excluded.identity_focus,
                preferred_work_mode=excluded.preferred_work_mode,
                recurring_tension=excluded.recurring_tension,
                growth_direction=excluded.growth_direction,
                confidence=excluded.confidence,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_self_model() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at
            FROM private_self_models
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "model_id": row["model_id"],
        "source": row["source"],
        "identity_focus": row["identity_focus"],
        "preferred_work_mode": row["preferred_work_mode"],
        "recurring_tension": row["recurring_tension"],
        "growth_direction": row["growth_direction"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


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


def _ensure_private_inner_note_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(private_inner_notes)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "note_kind": "TEXT NOT NULL DEFAULT ''",
        "focus": "TEXT NOT NULL DEFAULT ''",
        "uncertainty": "TEXT NOT NULL DEFAULT ''",
        "identity_alignment": "TEXT NOT NULL DEFAULT ''",
        "work_signal": "TEXT NOT NULL DEFAULT ''",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE private_inner_notes ADD COLUMN {name} {spec}")


def visible_session_continuity() -> dict[str, object]:
    recent_runs = recent_visible_runs(limit=1)
    recent_invocations = recent_capability_invocations(limit=2)
    latest_run = recent_runs[0] if recent_runs else {}
    recent_capability_ids = [
        capability_id
        for item in recent_invocations
        if (capability_id := str(item.get("capability_id") or "").strip())
    ]
    return {
        "active": bool(latest_run or recent_invocations),
        "source": "persisted-visible-runs+capability-invocations",
        "latest_run_id": latest_run.get("run_id"),
        "latest_status": latest_run.get("status"),
        "latest_finished_at": latest_run.get("finished_at"),
        "latest_text_preview": latest_run.get("text_preview"),
        "latest_capability_id": latest_run.get("capability_id"),
        "recent_capability_ids": recent_capability_ids,
        "included_run_rows": len(recent_runs),
        "included_capability_rows": len(recent_invocations),
    }


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
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(
            f"ALTER TABLE capability_approval_requests ADD COLUMN {name} {spec}"
        )
