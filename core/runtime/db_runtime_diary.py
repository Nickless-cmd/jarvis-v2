"""Persistence for the runtime diary-synthesis signal cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
the runtime_diary_synthesis_signals table via the lazily-invoked
`_ensure_runtime_diary_synthesis_signal_table` (called by the CRUD functions
themselves, never by init_db), plus all CRUD, the supersede/status helpers and
the private `_runtime_diary_synthesis_signal_from_row` row-mapper.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect


def list_runtime_diary_synthesis_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
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
                merge_count,
                created_at,
                updated_at
            FROM runtime_diary_synthesis_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_diary_synthesis_signal_from_row(row) for row in rows]


def get_diary_synthesis_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
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
                merge_count,
                created_at,
                updated_at
            FROM runtime_diary_synthesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_diary_synthesis_signal_from_row(row)


def update_diary_synthesis_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_diary_synthesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = ?,
                updated_at = ?,
                status_reason = ?
            WHERE signal_id = ?
            """,
            (status, updated_at, status_reason, signal_id),
        )
        conn.commit()
        return get_diary_synthesis_signal(signal_id)


def supersede_diary_synthesis_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"diary-synthesis:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_diary_synthesis_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
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
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
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
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_diary_synthesis_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_diary_synthesis_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
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
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
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
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            return {
                "was_created": True,
                "was_updated": False,
                **get_diary_synthesis_signal(signal_id),
            }

        was_created = False
        # Sikker int-cast (2026-06-22): merge_count kunne komme tilbage som str fra DB →
        # `old_merge_count + 1` kastede TypeError (str+int) og dræbte diary-synthesis-trackeren.
        try:
            old_merge_count = int(existing[15] or 0) if len(existing) > 15 else 0
        except (TypeError, ValueError):
            old_merge_count = 0
        conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = ?,
                title = ?,
                summary = ?,
                rationale = ?,
                source_kind = ?,
                confidence = ?,
                evidence_summary = ?,
                support_summary = ?,
                status_reason = ?,
                run_id = ?,
                session_id = ?,
                support_count = ?,
                session_count = ?,
                merge_count = ?,
                updated_at = ?
            WHERE signal_id = ?
            """,
            (
                status,
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
                old_merge_count + 1,
                updated_at,
                existing[0],
            ),
        )
        conn.commit()
        return {
            "was_created": was_created,
            "was_updated": True,
            **get_diary_synthesis_signal(existing[0]),
        }


def _runtime_diary_synthesis_signal_from_row(
    row: tuple[object, ...],
) -> dict[str, object]:
    return {
        "signal_id": str(row[0]),
        "signal_type": str(row[1]),
        "canonical_key": str(row[2]),
        "status": str(row[3]),
        "title": str(row[4]),
        "summary": str(row[5]),
        "rationale": str(row[6]),
        "source_kind": str(row[7]),
        "confidence": str(row[8]),
        "evidence_summary": str(row[9]),
        "support_summary": str(row[10]),
        "status_reason": str(row[11]),
        "run_id": str(row[12]),
        "session_id": str(row[13]),
        "support_count": int(row[14]) if row[14] else 1,
        "session_count": int(row[15]) if row[15] else 1,
        "merge_count": int(row[16]) if row[16] else 0,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
    }


def _ensure_runtime_diary_synthesis_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_diary_synthesis_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_diary_synthesis_signals_status
        ON runtime_diary_synthesis_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_diary_synthesis_signals_canonical_key
        ON runtime_diary_synthesis_signals(canonical_key, id DESC)
        """
    )

