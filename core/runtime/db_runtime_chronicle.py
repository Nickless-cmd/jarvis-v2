"""Persistence for Jarvis' runtime chronicle-consolidation signal cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for the
four tables runtime_consolidation_target_signals,
runtime_chronicle_consolidation_signals, runtime_chronicle_consolidation_briefs
and runtime_chronicle_consolidation_proposals via the `_ensure_*_table` helpers,
plus all CRUD and the private row-mapper helpers for the cluster. The
ensure-functions are called both lazily by the CRUD functions themselves and by
init_db (which imports them back from db.py), matching the original wiring.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import (
    connect,
    _upsert_signal,
    _CONFIDENCE_RANKS,
    _SOURCE_KIND_RANKS,
)


def _ensure_runtime_consolidation_target_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_consolidation_target_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_consolidation_target_signals_status
        ON runtime_consolidation_target_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_consolidation_target_signals_canonical_key
        ON runtime_consolidation_target_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_signals_status
        ON runtime_chronicle_consolidation_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_signals_canonical_key
        ON runtime_chronicle_consolidation_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_brief_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL UNIQUE,
            brief_type TEXT NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_briefs_status
        ON runtime_chronicle_consolidation_briefs(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_briefs_canonical_key
        ON runtime_chronicle_consolidation_briefs(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_proposal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_proposals_status
        ON runtime_chronicle_consolidation_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_proposals_canonical_key
        ON runtime_chronicle_consolidation_proposals(canonical_key, id DESC)
        """
    )


def _runtime_consolidation_target_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
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


def _runtime_chronicle_consolidation_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
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


def _runtime_chronicle_consolidation_brief_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "brief_id": row["brief_id"],
        "brief_type": row["brief_type"],
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


def _runtime_chronicle_consolidation_proposal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
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


def upsert_runtime_consolidation_target_signal(
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
    """Insert or merge a consolidation-target signal keyed on ``signal_id``.

    Ensures the table, then upserts via ``_upsert_signal`` (overwriting core
    text/status, rank-picking source_kind/confidence, merging the summary
    columns and accumulating the counts). Returns the persisted row dict
    updated with the upsert meta; raises RuntimeError if the row cannot be
    read back.
    """
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_consolidation_target_signals",
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

    signal = get_runtime_consolidation_target_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime consolidation-target signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_consolidation_target_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return consolidation-target signals newest-first as row dicts.

    Optionally filters by ``status`` and caps the result at ``limit`` (min 1).
    Returns an empty list when no rows match.
    """
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
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
            FROM runtime_consolidation_target_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_consolidation_target_signal_from_row(row) for row in rows]


def get_runtime_consolidation_target_signal(signal_id: str) -> dict[str, object] | None:
    """Return the consolidation-target signal row dict for ``signal_id``, or None if absent."""
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
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
            FROM runtime_consolidation_target_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_consolidation_target_signal_from_row(row)


def update_runtime_consolidation_target_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Set status/status_reason/updated_at on a consolidation-target signal.

    Returns the refreshed row dict, or None if no signal matches ``signal_id``.
    """
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_consolidation_target_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_consolidation_target_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_consolidation_target_signal(signal_id)


def supersede_runtime_consolidation_target_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all live consolidation-target signals in a domain as 'superseded'.

    Updates rows whose ``canonical_key`` matches ``consolidation-target:%:{domain_key}``
    and status is active/softening/stale, excluding ``exclude_signal_id``.
    Returns the number of rows superseded.
    """
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_consolidation_target_signals
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
                f"consolidation-target:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_signal(
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
    """Insert or merge a chronicle-consolidation signal keyed on ``signal_id``.

    Ensures the table, then upserts via ``_upsert_signal`` (overwriting core
    text/status, rank-picking source_kind/confidence, merging summaries and
    accumulating counts). Returns the persisted row dict updated with the
    upsert meta; raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_chronicle_consolidation_signals",
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

    signal = get_runtime_chronicle_consolidation_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime chronicle consolidation signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_chronicle_consolidation_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return chronicle-consolidation signals newest-first as row dicts.

    Optionally filters by ``status`` and caps at ``limit`` (min 1). Returns an
    empty list when no rows match.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
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
            FROM runtime_chronicle_consolidation_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_signal_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_signal(
    signal_id: str,
) -> dict[str, object] | None:
    """Return the chronicle-consolidation signal row dict for ``signal_id``, or None if absent."""
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
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
            FROM runtime_chronicle_consolidation_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_signal_from_row(row)


def update_runtime_chronicle_consolidation_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Set status/status_reason/updated_at on a chronicle-consolidation signal.

    Returns the refreshed row dict, or None if no signal matches ``signal_id``.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_chronicle_consolidation_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_signal(signal_id)


def supersede_runtime_chronicle_consolidation_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all live chronicle-consolidation signals in a domain as 'superseded'.

    Updates rows whose ``canonical_key`` matches ``chronicle-consolidation:%:{domain_key}``
    and status is active/softening/stale, excluding ``exclude_signal_id``.
    Returns the number of rows superseded.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_signals
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
                f"chronicle-consolidation:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_brief(
    *,
    brief_id: str,
    brief_type: str,
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
    """Insert or merge a chronicle-consolidation brief keyed on ``brief_id``.

    Ensures the table, then upserts via ``_upsert_signal`` (overwriting core
    text/status, rank-picking source_kind/confidence, merging summaries and
    accumulating counts). Returns the persisted row dict updated with the
    upsert meta; raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_chronicle_consolidation_briefs",
            id_col="brief_id",
            type_col="brief_type",
            id_val=brief_id,
            type_val=brief_type,
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

    brief = get_runtime_chronicle_consolidation_brief(resolved_id)
    if brief is None:
        raise RuntimeError("runtime chronicle consolidation brief was not persisted")
    brief.update(meta)
    return brief


def list_runtime_chronicle_consolidation_briefs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return chronicle-consolidation briefs newest-first as row dicts.

    Optionally filters by ``status`` and caps at ``limit`` (min 1). Returns an
    empty list when no rows match.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                brief_id,
                brief_type,
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
            FROM runtime_chronicle_consolidation_briefs
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_brief_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_brief(
    brief_id: str,
) -> dict[str, object] | None:
    """Return the chronicle-consolidation brief row dict for ``brief_id``, or None if absent."""
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        row = conn.execute(
            """
            SELECT
                brief_id,
                brief_type,
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
            FROM runtime_chronicle_consolidation_briefs
            WHERE brief_id = ?
            LIMIT 1
            """,
            (brief_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_brief_from_row(row)


def update_runtime_chronicle_consolidation_brief_status(
    brief_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Set status/status_reason/updated_at on a chronicle-consolidation brief.

    Returns the refreshed row dict, or None if no brief matches ``brief_id``.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        row = conn.execute(
            """
            SELECT brief_id
            FROM runtime_chronicle_consolidation_briefs
            WHERE brief_id = ?
            LIMIT 1
            """,
            (brief_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_briefs
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE brief_id = ?
            """,
            (status, status_reason, updated_at, brief_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_brief(brief_id)


def supersede_runtime_chronicle_consolidation_briefs_for_domain(
    *,
    domain_key: str,
    exclude_brief_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all live chronicle-consolidation briefs in a domain as 'superseded'.

    Updates rows whose ``canonical_key`` matches ``chronicle-consolidation-brief:%:{domain_key}``
    and status is active/softening/stale, excluding ``exclude_brief_id``.
    Returns the number of rows superseded.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_briefs
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND brief_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"chronicle-consolidation-brief:%:{domain_key}",
                exclude_brief_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
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
    """Insert or merge a chronicle-consolidation proposal keyed on ``proposal_id``.

    Ensures the table, then upserts via ``_upsert_signal`` (overwriting core
    text/status, rank-picking source_kind/confidence, merging summaries and
    accumulating counts). Returns the persisted row dict updated with the
    upsert meta; raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_chronicle_consolidation_proposals",
            id_col="proposal_id",
            type_col="proposal_type",
            id_val=proposal_id,
            type_val=proposal_type,
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

    proposal = get_runtime_chronicle_consolidation_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime chronicle consolidation proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_chronicle_consolidation_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return chronicle-consolidation proposals newest-first as row dicts.

    Optionally filters by ``status`` and caps at ``limit`` (min 1). Returns an
    empty list when no rows match.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
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
            FROM runtime_chronicle_consolidation_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_proposal_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_proposal(
    proposal_id: str,
) -> dict[str, object] | None:
    """Return the chronicle-consolidation proposal row dict for ``proposal_id``, or None if absent."""
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
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
            FROM runtime_chronicle_consolidation_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_proposal_from_row(row)


def update_runtime_chronicle_consolidation_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Set status/status_reason/updated_at on a chronicle-consolidation proposal.

    Returns the refreshed row dict, or None if no proposal matches ``proposal_id``.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_chronicle_consolidation_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_proposal(proposal_id)


def supersede_runtime_chronicle_consolidation_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all live chronicle-consolidation proposals in a domain as 'superseded'.

    Updates rows whose ``canonical_key`` matches ``chronicle-consolidation-proposal:%:{domain_key}``
    and status is active/softening/stale, excluding ``exclude_proposal_id``.
    Returns the number of rows superseded.
    """
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"chronicle-consolidation-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)
