"""Persistence for Jarvis' runtime dream signal cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for the
three runtime_dream_* tables (dream_hypothesis_signal, dream_adoption_candidate,
dream_influence_proposal) via lazily-invoked `_ensure_*_table` helpers, plus all
CRUD and the private row-mapper helpers for the cluster. The ensure-functions are
called lazily by the CRUD functions themselves (never by init_db), so the cluster
is self-contained.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import (
    connect,
    _upsert_signal,
    _CONFIDENCE_RANKS,
    _SOURCE_KIND_RANKS,
)


def _ensure_runtime_dream_hypothesis_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_hypothesis_signals (
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
            updated_at TEXT NOT NULL,
            relevant_to_users TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_hypothesis_signals_status
        ON runtime_dream_hypothesis_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_hypothesis_signals_canonical_key
        ON runtime_dream_hypothesis_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_dream_adoption_candidate_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_adoption_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL UNIQUE,
            candidate_type TEXT NOT NULL,
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
            updated_at TEXT NOT NULL,
            relevant_to_users TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_adoption_candidates_status
        ON runtime_dream_adoption_candidates(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_adoption_candidates_canonical_key
        ON runtime_dream_adoption_candidates(canonical_key, id DESC)
        """
    )


def _ensure_runtime_dream_influence_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_influence_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
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
            updated_at TEXT NOT NULL,
            relevant_to_users TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_influence_proposals_status
        ON runtime_dream_influence_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_influence_proposals_canonical_key
        ON runtime_dream_influence_proposals(canonical_key, id DESC)
        """
    )


def _runtime_dream_hypothesis_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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


def _runtime_dream_adoption_candidate_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "candidate_id": row["candidate_id"],
        "candidate_type": row["candidate_type"],
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


def _runtime_dream_influence_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
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


def upsert_runtime_dream_hypothesis_signal(
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
    """Insert or merge a dream hypothesis signal into runtime_dream_hypothesis_signals.

    Ensures the table exists, then upserts via the shared `_upsert_signal` helper
    (keyed on signal_id / canonical_key, merging into an existing active/integrating/
    fading/stale row when present). Re-reads and returns the persisted row dict with
    the upsert metadata merged in. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_dream_hypothesis_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=("active", "integrating", "fading", "stale"),
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

    signal = get_runtime_dream_hypothesis_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime dream hypothesis signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_dream_hypothesis_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return dream hypothesis signals as row dicts, newest first.

    Optionally filters by status and always scopes to the current user
    (rows with NULL relevant_to_users or matching the current user id). Bounded
    by `limit`. Returns an empty list when nothing matches.
    """
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if _current_uid:
            clauses.append(
                "(relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%')"
            )
            params.append(_current_uid)
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
            FROM runtime_dream_hypothesis_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_hypothesis_signal_from_row(row) for row in rows]


def get_runtime_dream_hypothesis_signal(signal_id: str) -> dict[str, object] | None:
    """Return the dream hypothesis signal with this signal_id as a row dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
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
            FROM runtime_dream_hypothesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_hypothesis_signal_from_row(row)


def update_runtime_dream_hypothesis_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at of one dream hypothesis signal.

    No-op returning None if no row has this signal_id; otherwise writes the new
    status and returns the refreshed row dict.
    """
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_dream_hypothesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_hypothesis_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_dream_hypothesis_signal(signal_id)


def supersede_runtime_dream_hypothesis_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all still-live dream hypothesis signals for a domain as 'superseded'.

    Sets status='superseded' (with the given status_reason/updated_at) on every
    active/integrating/fading/stale row whose canonical_key matches the domain,
    except the excluded signal_id. Returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_hypothesis_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'integrating', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-hypothesis:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_dream_adoption_candidate(
    *,
    candidate_id: str,
    candidate_type: str,
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
    """Insert or merge a dream adoption candidate into runtime_dream_adoption_candidates.

    Ensures the table exists, then upserts via the shared `_upsert_signal` helper
    (keyed on candidate_id / canonical_key, merging into an existing fresh/active/
    fading/stale row when present). Re-reads and returns the persisted row dict with
    the upsert metadata merged in. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_dream_adoption_candidates",
            id_col="candidate_id",
            type_col="candidate_type",
            id_val=candidate_id,
            type_val=candidate_type,
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

    candidate = get_runtime_dream_adoption_candidate(resolved_id)
    if candidate is None:
        raise RuntimeError("runtime dream adoption candidate was not persisted")
    candidate.update(meta)
    return candidate


def list_runtime_dream_adoption_candidates(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return dream adoption candidates as row dicts, newest first.

    Optionally filters by status and always scopes to the current user
    (rows with NULL relevant_to_users or matching the current user id). Bounded
    by `limit`. Returns an empty list when nothing matches.
    """
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if _current_uid:
            clauses.append(
                "(relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%')"
            )
            params.append(_current_uid)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                candidate_id,
                candidate_type,
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
            FROM runtime_dream_adoption_candidates
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_adoption_candidate_from_row(row) for row in rows]


def get_runtime_dream_adoption_candidate(candidate_id: str) -> dict[str, object] | None:
    """Return the dream adoption candidate with this candidate_id as a row dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        row = conn.execute(
            """
            SELECT
                candidate_id,
                candidate_type,
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
            FROM runtime_dream_adoption_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_adoption_candidate_from_row(row)


def update_runtime_dream_adoption_candidate_status(
    candidate_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at of one dream adoption candidate.

    No-op returning None if no row has this candidate_id; otherwise writes the new
    status and returns the refreshed row dict.
    """
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        row = conn.execute(
            """
            SELECT candidate_id
            FROM runtime_dream_adoption_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_adoption_candidates
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (status, status_reason, updated_at, candidate_id),
        )
        conn.commit()
    return get_runtime_dream_adoption_candidate(candidate_id)


def supersede_runtime_dream_adoption_candidates_for_domain(
    *,
    domain_key: str,
    exclude_candidate_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all still-live dream adoption candidates for a domain as 'superseded'.

    Sets status='superseded' (with the given status_reason/updated_at) on every
    fresh/active/fading/stale row whose canonical_key matches the domain, except the
    excluded candidate_id. Returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_adoption_candidates
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND candidate_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-adoption-candidate:%:{domain_key}",
                exclude_candidate_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_dream_influence_proposal(
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
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    """Insert or merge a dream influence proposal into runtime_dream_influence_proposals.

    Ensures the table exists, then upserts via the shared `_upsert_signal` helper
    (keyed on proposal_id / canonical_key, merging into an existing fresh/active/
    fading/stale row when present). Re-reads and returns the persisted row dict with
    the upsert metadata merged in. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_dream_influence_proposals",
            id_col="proposal_id",
            type_col="proposal_type",
            id_val=proposal_id,
            type_val=proposal_type,
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

    proposal = get_runtime_dream_influence_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime dream influence proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_dream_influence_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return dream influence proposals as row dicts, newest first.

    Optionally filters by status and always scopes to the current user
    (rows with NULL relevant_to_users or matching the current user id). Bounded
    by `limit`. Returns an empty list when nothing matches.
    """
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if _current_uid:
            clauses.append(
                "(relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%')"
            )
            params.append(_current_uid)
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
            FROM runtime_dream_influence_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_influence_proposal_from_row(row) for row in rows]


def get_runtime_dream_influence_proposal(proposal_id: str) -> dict[str, object] | None:
    """Return the dream influence proposal with this proposal_id as a row dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
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
            FROM runtime_dream_influence_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_influence_proposal_from_row(row)


def update_runtime_dream_influence_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at of one dream influence proposal.

    No-op returning None if no row has this proposal_id; otherwise writes the new
    status and returns the refreshed row dict.
    """
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_dream_influence_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_influence_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_dream_influence_proposal(proposal_id)


def supersede_runtime_dream_influence_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all still-live dream influence proposals for a domain as 'superseded'.

    Sets status='superseded' (with the given status_reason/updated_at) on every
    fresh/active/fading/stale row whose canonical_key matches the domain, except the
    excluded proposal_id. Returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_influence_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-influence-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)
