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
    _upsert_signal,
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
    """Insert or merge a runtime self-review signal into runtime_self_review_signals.

    Delegates to `_upsert_signal` with canonical-key dedup over the active/softening/stale
    statuses (overwriting text/status, rank-merging source_kind/confidence, accumulating
    support/session counts). Returns the persisted signal row dict (with merge meta merged
    in); raises RuntimeError if the row could not be read back.
    """
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_self_review_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=("active", "softening", "stale"),
            overwrite_cols=[
                ("status", status),
                ("title", title),
                ("summary", summary),
                ("rationale", rationale),
                ("run_id", run_id),
                ("session_id", session_id),
            ],
            rank_cols=[
                ("source_kind", source_kind, _SOURCE_KIND_RANKS),
                ("confidence", confidence, _CONFIDENCE_RANKS),
            ],
            merge_text_cols=[
                ("evidence_summary", evidence_summary, 4),
                ("support_summary", support_summary, 4),
                ("status_reason", status_reason, 4),
            ],
            accumulate_cols=[
                ("support_count", support_count),
                ("session_count", session_count),
            ],
            created_at=created_at,
            updated_at=updated_at,
        )

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
    """Return up to `limit` runtime self-review signals, newest first (ORDER BY id DESC).

    Filters on `status` when given; returns a list of signal row dicts (empty if none).
    """
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
    """Return the runtime self-review signal row dict for `signal_id`, or None if absent."""
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
    """Set status/status_reason/updated_at on the signal `signal_id`.

    No-op returning None if the signal does not exist; otherwise commits and returns the
    refreshed signal row dict.
    """
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
    """Mark all still-live signals in `domain_key` as 'superseded' except `exclude_signal_id`.

    Matches canonical_key LIKE 'self-review:%:{domain_key}' with status in
    active/softening/stale. Commits and returns the number of rows updated.
    """
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
    """Insert or merge a runtime self-review record into runtime_self_review_records.

    Delegates to `_upsert_signal` with canonical-key dedup over the fresh/active/fading/stale
    statuses. Returns the persisted record row dict (with merge meta merged in); raises
    RuntimeError if the row could not be read back.
    """
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_self_review_records",
            id_col="record_id",
            type_col="record_type",
            id_val=record_id,
            type_val=record_type,
            canonical_key=canonical_key,
            lookup_statuses=("fresh", "active", "fading", "stale"),
            overwrite_cols=[
                ("status", status),
                ("title", title),
                ("summary", summary),
                ("rationale", rationale),
                ("run_id", run_id),
                ("session_id", session_id),
            ],
            rank_cols=[
                ("source_kind", source_kind, _SOURCE_KIND_RANKS),
                ("confidence", confidence, _CONFIDENCE_RANKS),
            ],
            merge_text_cols=[
                ("evidence_summary", evidence_summary, 4),
                ("support_summary", support_summary, 4),
                ("status_reason", status_reason, 4),
            ],
            accumulate_cols=[
                ("support_count", support_count),
                ("session_count", session_count),
            ],
            created_at=created_at,
            updated_at=updated_at,
        )

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
    """Return up to `limit` runtime self-review records, newest first (ORDER BY id DESC).

    Filters on `status` when given; returns a list of record row dicts (empty if none).
    """
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
    """Return the runtime self-review record row dict for `record_id`, or None if absent."""
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
    """Set status/status_reason/updated_at on the record `record_id`.

    No-op returning None if the record does not exist; otherwise commits and returns the
    refreshed record row dict.
    """
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
    """Mark all still-live records in `domain_key` as 'superseded' except `exclude_record_id`.

    Matches canonical_key LIKE 'self-review-record:%:{domain_key}' with status in
    fresh/active/fading/stale. Commits and returns the number of rows updated.
    """
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
    """Insert or merge a runtime self-review run into runtime_self_review_runs.

    Delegates to `_upsert_signal` with canonical-key dedup over the fresh/active/fading/stale
    statuses. Returns the persisted run row dict (with merge meta merged in); raises
    RuntimeError if the row could not be read back.
    """
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_self_review_runs",
            id_col="run_id",
            type_col="run_type",
            id_val=run_id,
            type_val=run_type,
            canonical_key=canonical_key,
            lookup_statuses=("fresh", "active", "fading", "stale"),
            overwrite_cols=[
                ("status", status),
                ("title", title),
                ("summary", summary),
                ("rationale", rationale),
                ("record_run_id", record_run_id),
                ("session_id", session_id),
            ],
            rank_cols=[
                ("source_kind", source_kind, _SOURCE_KIND_RANKS),
                ("confidence", confidence, _CONFIDENCE_RANKS),
            ],
            merge_text_cols=[
                ("evidence_summary", evidence_summary, 4),
                ("support_summary", support_summary, 4),
                ("status_reason", status_reason, 4),
            ],
            accumulate_cols=[
                ("support_count", support_count),
                ("session_count", session_count),
            ],
            created_at=created_at,
            updated_at=updated_at,
        )

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
    """Return up to `limit` runtime self-review runs, newest first (ORDER BY id DESC).

    Filters on `status` when given; returns a list of run row dicts (empty if none).
    """
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
    """Return the runtime self-review run row dict for `run_id`, or None if absent."""
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
    """Set status/status_reason/updated_at on the run `run_id`.

    No-op returning None if the run does not exist; otherwise commits and returns the
    refreshed run row dict.
    """
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
    """Mark all still-live runs in `domain_key` as 'superseded' except `exclude_run_id`.

    Matches canonical_key LIKE 'self-review-run:%:{domain_key}' with status in
    fresh/active/fading/stale. Commits and returns the number of rows updated.
    """
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
    """Insert or merge a runtime self-review outcome into runtime_self_review_outcomes.

    Delegates to `_upsert_signal` with canonical-key dedup over the fresh/active/fading/stale
    statuses. Returns the persisted outcome row dict (with merge meta merged in); raises
    RuntimeError if the row could not be read back.
    """
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_self_review_outcomes",
            id_col="outcome_id",
            type_col="outcome_type",
            id_val=outcome_id,
            type_val=outcome_type,
            canonical_key=canonical_key,
            lookup_statuses=("fresh", "active", "fading", "stale"),
            overwrite_cols=[
                ("status", status),
                ("title", title),
                ("summary", summary),
                ("rationale", rationale),
                ("review_run_id", review_run_id),
                ("session_id", session_id),
            ],
            rank_cols=[
                ("source_kind", source_kind, _SOURCE_KIND_RANKS),
                ("confidence", confidence, _CONFIDENCE_RANKS),
            ],
            merge_text_cols=[
                ("evidence_summary", evidence_summary, 4),
                ("support_summary", support_summary, 4),
                ("status_reason", status_reason, 4),
            ],
            accumulate_cols=[
                ("support_count", support_count),
                ("session_count", session_count),
            ],
            created_at=created_at,
            updated_at=updated_at,
        )

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
    """Return up to `limit` runtime self-review outcomes, newest first (ORDER BY id DESC).

    Filters on `status` when given; returns a list of outcome row dicts (empty if none).
    """
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
    """Return the runtime self-review outcome row dict for `outcome_id`, or None if absent."""
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
    """Set status/status_reason/updated_at on the outcome `outcome_id`.

    No-op returning None if the outcome does not exist; otherwise commits and returns the
    refreshed outcome row dict.
    """
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
    """Mark all still-live outcomes in `domain_key` as 'superseded' except `exclude_outcome_id`.

    Matches canonical_key LIKE 'self-review-outcome:%:{domain_key}' with status in
    fresh/active/fading/stale. Commits and returns the number of rows updated.
    """
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
    """Insert or merge a cadence signal into runtime_self_review_cadence_signals.

    Delegates to `_upsert_signal` with canonical-key dedup over the active/softening/stale
    statuses. Returns the persisted cadence-signal row dict (with merge meta merged in);
    raises RuntimeError if the row could not be read back.
    """
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_self_review_cadence_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=("active", "softening", "stale"),
            overwrite_cols=[
                ("status", status),
                ("title", title),
                ("summary", summary),
                ("rationale", rationale),
                ("run_id", run_id),
                ("session_id", session_id),
            ],
            rank_cols=[
                ("source_kind", source_kind, _SOURCE_KIND_RANKS),
                ("confidence", confidence, _CONFIDENCE_RANKS),
            ],
            merge_text_cols=[
                ("evidence_summary", evidence_summary, 4),
                ("support_summary", support_summary, 4),
                ("status_reason", status_reason, 4),
            ],
            accumulate_cols=[
                ("support_count", support_count),
                ("session_count", session_count),
            ],
            created_at=created_at,
            updated_at=updated_at,
        )

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
    """Return up to `limit` cadence signals, newest first (ORDER BY id DESC).

    Filters on `status` when given; returns a list of cadence-signal row dicts (empty if none).
    """
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
    """Return the cadence-signal row dict for `signal_id`, or None if absent."""
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
    """Set status/status_reason/updated_at on the cadence signal `signal_id`.

    No-op returning None if the cadence signal does not exist; otherwise commits and returns
    the refreshed cadence-signal row dict.
    """
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
    """Mark all still-live cadence signals in `domain_key` as 'superseded' except `exclude_signal_id`.

    Matches canonical_key LIKE 'self-review-cadence:%:{domain_key}' with status in
    active/softening/stale. Commits and returns the number of rows updated.
    """
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
