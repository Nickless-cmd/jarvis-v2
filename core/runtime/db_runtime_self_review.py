"""Persistence for Jarvis' runtime self-review signal cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for the
five runtime_self_review_* tables (signal, record, run, outcome, cadence_signal)
via lazily-invoked `_ensure_runtime_self_review_*_table` helpers, plus all CRUD
and the private row-mapper helpers for the cluster. The ensure-functions are
called lazily by the CRUD functions themselves (never by init_db), so the
cluster is self-contained.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import (
    connect,
    _merge_text_fragments,
    _stronger_ranked_value,
    _CONFIDENCE_RANKS,
    _SOURCE_KIND_RANKS,
)


def _ensure_runtime_self_review_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_signals_status
        ON runtime_self_review_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_signals_canonical_key
        ON runtime_self_review_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_record_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
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
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_records_status
        ON runtime_self_review_records(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_records_canonical_key
        ON runtime_self_review_records(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_run_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            run_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            record_run_id TEXT NOT NULL DEFAULT '',
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
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_runs_status
        ON runtime_self_review_runs(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_runs_canonical_key
        ON runtime_self_review_runs(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_outcome_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outcome_id TEXT NOT NULL UNIQUE,
            outcome_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            review_run_id TEXT NOT NULL DEFAULT '',
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
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_outcomes_status
        ON runtime_self_review_outcomes(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_outcomes_canonical_key
        ON runtime_self_review_outcomes(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_cadence_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_cadence_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_cadence_signals_status
        ON runtime_self_review_cadence_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_cadence_signals_canonical_key
        ON runtime_self_review_cadence_signals(canonical_key, id DESC)
        """
    )


def _runtime_self_review_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
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
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_record_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "record_id": row["record_id"],
        "record_type": row["record_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
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
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_run_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "run_id": row["run_id"],
        "run_type": row["run_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "record_run_id": row["record_run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_outcome_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "outcome_id": row["outcome_id"],
        "outcome_type": row["outcome_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "review_run_id": row["review_run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_cadence_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
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
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert_runtime_self_review_signal(
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
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
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
                FROM runtime_self_review_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_signals (
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
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_signals
                    SET
                        status = ?,
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
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_review_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self-review signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_review_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
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
            FROM runtime_self_review_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_signal_from_row(row) for row in rows]


def get_runtime_self_review_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
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
            FROM runtime_self_review_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_signal_from_row(row)


def update_runtime_self_review_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_review_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_review_signal(signal_id)


def supersede_runtime_self_review_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_record(
    *,
    record_id: str,
    record_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    record_id,
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
                FROM runtime_self_review_records
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_records (
                    record_id,
                    record_type,
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
                    record_id,
                    record_type,
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
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = record_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["record_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_records
                    SET
                        status = ?,
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
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE record_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    record = get_runtime_self_review_record(resolved_id)
    if record is None:
        raise RuntimeError("runtime self-review record was not persisted")
    record.update(meta)
    return record


def list_runtime_self_review_records(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                record_id,
                record_type,
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
            FROM runtime_self_review_records
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_record_from_row(row) for row in rows]


def get_runtime_self_review_record(record_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        row = conn.execute(
            """
            SELECT
                record_id,
                record_type,
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
            FROM runtime_self_review_records
            WHERE record_id = ?
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_record_from_row(row)


def update_runtime_self_review_record_status(
    record_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        row = conn.execute(
            """
            SELECT record_id
            FROM runtime_self_review_records
            WHERE record_id = ?
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_records
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE record_id = ?
            """,
            (status, status_reason, updated_at, record_id),
        )
        conn.commit()
    return get_runtime_self_review_record(record_id)


def supersede_runtime_self_review_records_for_domain(
    *,
    domain_key: str,
    exclude_record_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_records
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND record_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-record:%:{domain_key}",
                exclude_record_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_run(
    *,
    run_id: str,
    run_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    record_run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    run_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    record_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_runs
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_runs (
                    run_id,
                    run_type,
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
                    record_run_id,
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
                    run_id,
                    run_type,
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
                    record_run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = run_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["run_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and record_run_id == str(existing["record_run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_runs
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        record_run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE run_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        record_run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    run = get_runtime_self_review_run(resolved_id)
    if run is None:
        raise RuntimeError("runtime self-review run was not persisted")
    run.update(meta)
    return run


def list_runtime_self_review_runs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                run_id,
                run_type,
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
                record_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_runs
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_run_from_row(row) for row in rows]


def get_runtime_self_review_run(run_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        row = conn.execute(
            """
            SELECT
                run_id,
                run_type,
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
                record_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_runs
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_run_from_row(row)


def update_runtime_self_review_run_status(
    run_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        row = conn.execute(
            """
            SELECT run_id
            FROM runtime_self_review_runs
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_runs
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (status, status_reason, updated_at, run_id),
        )
        conn.commit()
    return get_runtime_self_review_run(run_id)


def supersede_runtime_self_review_runs_for_domain(
    *,
    domain_key: str,
    exclude_run_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_runs
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND run_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-run:%:{domain_key}",
                exclude_run_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_outcome(
    *,
    outcome_id: str,
    outcome_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    review_run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    outcome_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    review_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_outcomes
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_outcomes (
                    outcome_id,
                    outcome_type,
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
                    review_run_id,
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
                    outcome_id,
                    outcome_type,
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
                    review_run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = outcome_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["outcome_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and review_run_id == str(existing["review_run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_outcomes
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        review_run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE outcome_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        review_run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    outcome = get_runtime_self_review_outcome(resolved_id)
    if outcome is None:
        raise RuntimeError("runtime self-review outcome was not persisted")
    outcome.update(meta)
    return outcome


def list_runtime_self_review_outcomes(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                outcome_id,
                outcome_type,
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
                review_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_outcomes
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_outcome_from_row(row) for row in rows]


def get_runtime_self_review_outcome(outcome_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        row = conn.execute(
            """
            SELECT
                outcome_id,
                outcome_type,
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
                review_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_outcomes
            WHERE outcome_id = ?
            LIMIT 1
            """,
            (outcome_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_outcome_from_row(row)


def update_runtime_self_review_outcome_status(
    outcome_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        row = conn.execute(
            """
            SELECT outcome_id
            FROM runtime_self_review_outcomes
            WHERE outcome_id = ?
            LIMIT 1
            """,
            (outcome_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_outcomes
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE outcome_id = ?
            """,
            (status, status_reason, updated_at, outcome_id),
        )
        conn.commit()
    return get_runtime_self_review_outcome(outcome_id)


def supersede_runtime_self_review_outcomes_for_domain(
    *,
    domain_key: str,
    exclude_outcome_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_outcomes
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND outcome_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-outcome:%:{domain_key}",
                exclude_outcome_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_cadence_signal(
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
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
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
                FROM runtime_self_review_cadence_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_cadence_signals (
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
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_cadence_signals
                    SET
                        status = ?,
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
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_review_cadence_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self-review cadence signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_review_cadence_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
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
            FROM runtime_self_review_cadence_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_cadence_signal_from_row(row) for row in rows]


def get_runtime_self_review_cadence_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
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
            FROM runtime_self_review_cadence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_cadence_signal_from_row(row)


def update_runtime_self_review_cadence_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_review_cadence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_cadence_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_review_cadence_signal(signal_id)


def supersede_runtime_self_review_cadence_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_cadence_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-cadence:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)
