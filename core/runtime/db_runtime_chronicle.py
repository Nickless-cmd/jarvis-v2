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
    _merge_text_fragments,
    _stronger_ranked_value,
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
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
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
                FROM runtime_consolidation_target_signals
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
                INSERT INTO runtime_consolidation_target_signals (
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
                    UPDATE runtime_consolidation_target_signals
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
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
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
                FROM runtime_chronicle_consolidation_signals
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
                INSERT INTO runtime_chronicle_consolidation_signals (
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
                    UPDATE runtime_chronicle_consolidation_signals
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
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    brief_id,
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
                INSERT INTO runtime_chronicle_consolidation_briefs (
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
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = brief_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["brief_id"])
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
                    UPDATE runtime_chronicle_consolidation_briefs
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
                    WHERE brief_id = ?
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
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
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
                INSERT INTO runtime_chronicle_consolidation_proposals (
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
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
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
                    UPDATE runtime_chronicle_consolidation_proposals
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
                    WHERE proposal_id = ?
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
