"""Persistence for Jarvis' runtime cognition-* signal cluster.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for the
eight runtime cognition-oriented signal tables (reflection_signal,
reflective_critic, internal_opposition_signal, meaning_significance_signal,
witness_signal, awareness_signal, executive_contradiction_signal,
metabolism_state_signal) via `_ensure_runtime_*_table` helpers, plus all CRUD
and the private row-mapper helpers for the cluster.

The meaning_significance / metabolism_state / executive_contradiction
ensure-functions are called by init_db (re-imported back into db.py so init_db
resolves them at call-time); the reflection / reflective_critic / awareness /
witness / internal_opposition ensures are called lazily by their own CRUD. All
ensures are also invoked lazily inside their CRUD, so the cluster is
self-contained.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import (
    connect,
    _merge_text_fragments,
    _stronger_ranked_value,
    _upsert_signal,
    _CONFIDENCE_RANKS,
    _SOURCE_KIND_RANKS,
)


def upsert_runtime_reflective_critic(
    *,
    critic_id: str,
    critic_type: str,
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
    """Insert or merge a runtime reflective-critic row keyed by ``canonical_key``.

    If an active/stale row with the same canonical_key exists, its ranked
    fields (source_kind/confidence) and text fields are merged and support/
    session counts accumulated; otherwise a new row is inserted. Commits and
    returns the resulting critic dict augmented with was_created/was_updated/
    merge_state metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    critic_id,
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
                FROM runtime_reflective_critics
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
                INSERT INTO runtime_reflective_critics (
                    critic_id,
                    critic_type,
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
                    critic_id,
                    critic_type,
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
            resolved_id = critic_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["critic_id"])
            merged_status = (
                "active"
                if status == "active"
                else str(status or existing["status"] or "active")
            )
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
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
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
                    UPDATE runtime_reflective_critics
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
                    WHERE critic_id = ?
                    """,
                    (
                        merged_status,
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

    critic = get_runtime_reflective_critic(resolved_id)
    if critic is None:
        raise RuntimeError("runtime reflective critic was not persisted")
    critic.update(meta)
    return critic



def list_runtime_reflective_critics(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return reflective-critic rows (dicts), newest first, optionally filtered by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                critic_id,
                critic_type,
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
            FROM runtime_reflective_critics
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_reflective_critic_from_row(row) for row in rows]



def get_runtime_reflective_critic(critic_id: str) -> dict[str, object] | None:
    """Return the reflective-critic row for ``critic_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        row = conn.execute(
            """
            SELECT
                critic_id,
                critic_type,
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
            FROM runtime_reflective_critics
            WHERE critic_id = ?
            LIMIT 1
            """,
            (critic_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_reflective_critic_from_row(row)



def update_runtime_reflective_critic_status(
    critic_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one reflective critic.

    Commits and returns the refreshed critic dict, or None if ``critic_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        row = conn.execute(
            """
            SELECT critic_id
            FROM runtime_reflective_critics
            WHERE critic_id = ?
            LIMIT 1
            """,
            (critic_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_reflective_critics
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE critic_id = ?
            """,
            (status, status_reason, updated_at, critic_id),
        )
        conn.commit()
    return get_runtime_reflective_critic(critic_id)



def supersede_runtime_reflective_critics(
    *,
    critic_type: str,
    exclude_critic_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all active/stale critics of ``critic_type`` (except ``exclude_critic_id``) superseded.

    Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_reflective_critics
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE critic_type = ?
              AND critic_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                critic_type,
                exclude_critic_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_awareness_signal(
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
    """Insert or merge a runtime awareness-signal row keyed by ``canonical_key``.

    If a row with the same canonical_key exists it is merged (ranked
    source_kind/confidence, merged text fields, accumulated support/session
    counts); otherwise a new row is inserted. Commits and returns the signal
    dict with was_created/was_updated/merge_state metadata. Raises RuntimeError
    if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
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
                FROM runtime_awareness_signals
                WHERE canonical_key = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_awareness_signals (
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
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
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
                    UPDATE runtime_awareness_signals
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

    signal = get_runtime_awareness_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime awareness signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_awareness_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return awareness-signal rows (dicts), newest first, optionally filtered by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
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
            FROM runtime_awareness_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_awareness_signal_from_row(row) for row in rows]



def get_runtime_awareness_signal(signal_id: str) -> dict[str, object] | None:
    """Return the awareness-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
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
            FROM runtime_awareness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_awareness_signal_from_row(row)



def update_runtime_awareness_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one awareness signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_awareness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_awareness_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_awareness_signal(signal_id)



def supersede_runtime_awareness_signals(
    *,
    signal_type: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark all live awareness signals of ``signal_type`` (except ``exclude_signal_id``) superseded.

    Live statuses are active/constrained/recovered/stale. Commits and returns
    the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_awareness_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE signal_type = ?
              AND signal_id != ?
              AND status IN ('active', 'constrained', 'recovered', 'stale')
            """,
            (
                status_reason,
                updated_at,
                signal_type,
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_reflection_signal(
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
    """Insert or merge a runtime reflection-signal row via the shared _upsert_signal helper.

    Rows sharing ``canonical_key`` in an active/integrating/settled/stale state
    are merged (ranked source_kind/confidence, merged text fields, accumulated
    counts); otherwise a new row is inserted. Commits and returns the signal
    dict with merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_reflection_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=("active", "integrating", "settled", "stale"),
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

    signal = get_runtime_reflection_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime reflection signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_reflection_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return reflection-signal rows (dicts), newest first, optionally filtered by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
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
            FROM runtime_reflection_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_reflection_signal_from_row(row) for row in rows]



def get_runtime_reflection_signal(signal_id: str) -> dict[str, object] | None:
    """Return the reflection-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
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
            FROM runtime_reflection_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_reflection_signal_from_row(row)



def update_runtime_reflection_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one reflection signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_reflection_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_reflection_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_reflection_signal(signal_id)



def supersede_runtime_reflection_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark active reflection signals for a domain (except one) superseded.

    Matches canonical_key ``reflection-signal:%:{domain_key}`` in an active/
    integrating/settled/stale state, excluding ``exclude_signal_id``. Commits
    and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_reflection_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'integrating', 'settled', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"reflection-signal:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_witness_signal(
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
    """Insert or merge a runtime witness-signal row via the shared _upsert_signal helper.

    Rows sharing ``canonical_key`` in a fresh/carried/fading state are merged;
    otherwise a new row is inserted. Commits and returns the signal dict with
    merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_witness_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=('fresh', 'carried', 'fading'),
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

    signal = get_runtime_witness_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime witness signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_witness_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return witness-signal rows (dicts), newest first, optionally filtered by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
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
            FROM runtime_witness_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_witness_signal_from_row(row) for row in rows]



def get_runtime_witness_signal(signal_id: str) -> dict[str, object] | None:
    """Return the witness-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
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
            FROM runtime_witness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_witness_signal_from_row(row)



def update_runtime_witness_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one witness signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_witness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_witness_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_witness_signal(signal_id)



def supersede_runtime_witness_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark fresh/carried/fading witness signals for a domain (except one) superseded.

    Matches canonical_key ``witness-signal:%:{domain_key}``, excluding
    ``exclude_signal_id``. Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_witness_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('fresh', 'carried', 'fading')
            """,
            (
                status_reason,
                updated_at,
                f"witness-signal:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_internal_opposition_signal(
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
    """Insert or merge a runtime internal-opposition-signal row via _upsert_signal.

    Rows sharing ``canonical_key`` in an active/softening/stale state are
    merged; otherwise a new row is inserted. Commits and returns the signal
    dict with merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_internal_opposition_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=('active', 'softening', 'stale'),
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

    signal = get_runtime_internal_opposition_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime internal opposition signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_internal_opposition_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return internal-opposition-signal rows (dicts), newest first, optionally by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
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
            FROM runtime_internal_opposition_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_internal_opposition_signal_from_row(row) for row in rows]



def get_runtime_internal_opposition_signal(signal_id: str) -> dict[str, object] | None:
    """Return the internal-opposition-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
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
            FROM runtime_internal_opposition_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_internal_opposition_signal_from_row(row)



def update_runtime_internal_opposition_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one internal-opposition signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_internal_opposition_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_internal_opposition_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_internal_opposition_signal(signal_id)



def supersede_runtime_internal_opposition_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark active/softening/stale internal-opposition signals for a domain (except one) superseded.

    Matches canonical_key ``internal-opposition:%:{domain_key}``, excluding
    ``exclude_signal_id``. Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_internal_opposition_signals
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
                f"internal-opposition:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_meaning_significance_signal(
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
    """Insert or merge a runtime meaning-significance-signal row via _upsert_signal.

    Rows sharing ``canonical_key`` in an active/softening/stale state are
    merged; otherwise a new row is inserted. Commits and returns the signal
    dict with merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_meaning_significance_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=('active', 'softening', 'stale'),
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

    signal = get_runtime_meaning_significance_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime meaning significance signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_meaning_significance_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return meaning-significance-signal rows (dicts), newest first, optionally by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
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
            FROM runtime_meaning_significance_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_meaning_significance_signal_from_row(row) for row in rows]



def get_runtime_meaning_significance_signal(signal_id: str) -> dict[str, object] | None:
    """Return the meaning-significance-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
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
            FROM runtime_meaning_significance_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_meaning_significance_signal_from_row(row)



def update_runtime_meaning_significance_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one meaning-significance signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_meaning_significance_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_meaning_significance_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_meaning_significance_signal(signal_id)



def supersede_runtime_meaning_significance_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark active/softening/stale meaning-significance signals for a focus (except one) superseded.

    Matches canonical_key ``meaning-significance:%:{focus_key}``, excluding
    ``exclude_signal_id``. Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_meaning_significance_signals
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
                f"meaning-significance:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_metabolism_state_signal(
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
    """Insert or merge a runtime metabolism-state-signal row via _upsert_signal.

    Rows sharing ``canonical_key`` in an active/softening/stale state are
    merged; otherwise a new row is inserted. Commits and returns the signal
    dict with merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_metabolism_state_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=('active', 'softening', 'stale'),
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

    signal = get_runtime_metabolism_state_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime metabolism-state signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_metabolism_state_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return metabolism-state-signal rows (dicts), newest first, optionally by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
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
            FROM runtime_metabolism_state_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_metabolism_state_signal_from_row(row) for row in rows]



def get_runtime_metabolism_state_signal(signal_id: str) -> dict[str, object] | None:
    """Return the metabolism-state-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
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
            FROM runtime_metabolism_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_metabolism_state_signal_from_row(row)



def update_runtime_metabolism_state_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one metabolism-state signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_metabolism_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_metabolism_state_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_metabolism_state_signal(signal_id)



def supersede_runtime_metabolism_state_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark active/softening/stale metabolism-state signals for a domain (except one) superseded.

    Matches canonical_key ``metabolism-state:%:{domain_key}``, excluding
    ``exclude_signal_id``. Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_metabolism_state_signals
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
                f"metabolism-state:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def upsert_runtime_executive_contradiction_signal(
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
    """Insert or merge a runtime executive-contradiction-signal row via _upsert_signal.

    Rows sharing ``canonical_key`` in an active/softening/stale state are
    merged; otherwise a new row is inserted. Commits and returns the signal
    dict with merge metadata. Raises RuntimeError if the row cannot be read back.
    """
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        resolved_id, meta = _upsert_signal(
            conn=conn,
            table="runtime_executive_contradiction_signals",
            id_col="signal_id",
            type_col="signal_type",
            id_val=signal_id,
            type_val=signal_type,
            canonical_key=canonical_key,
            lookup_statuses=('active', 'softening', 'stale'),
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

    signal = get_runtime_executive_contradiction_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime executive contradiction signal was not persisted")
    signal.update(meta)
    return signal



def list_runtime_executive_contradiction_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return executive-contradiction-signal rows (dicts), newest first, optionally by status.

    Returns an empty list when no rows match. ``limit`` is clamped to >= 1.
    """
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
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
            FROM runtime_executive_contradiction_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_executive_contradiction_signal_from_row(row) for row in rows]



def get_runtime_executive_contradiction_signal(
    signal_id: str,
) -> dict[str, object] | None:
    """Return the executive-contradiction-signal row for ``signal_id`` as a dict, or None if absent."""
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
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
            FROM runtime_executive_contradiction_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_executive_contradiction_signal_from_row(row)



def update_runtime_executive_contradiction_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    """Update status/status_reason/updated_at for one executive-contradiction signal.

    Commits and returns the refreshed signal dict, or None if ``signal_id``
    does not exist.
    """
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_executive_contradiction_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_executive_contradiction_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_executive_contradiction_signal(signal_id)



def supersede_runtime_executive_contradiction_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    """Mark active/softening/stale executive-contradiction signals for a domain (except one) superseded.

    Matches canonical_key ``executive-contradiction:%:{domain_key}``, excluding
    ``exclude_signal_id``. Commits and returns the number of rows updated.
    """
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_executive_contradiction_signals
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
                f"executive-contradiction:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)



def _ensure_runtime_reflective_critic_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_reflective_critics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            critic_id TEXT NOT NULL UNIQUE,
            critic_type TEXT NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_status
        ON runtime_reflective_critics(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_canonical_key
        ON runtime_reflective_critics(canonical_key, id DESC)
        """
    )



def _ensure_runtime_awareness_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_awareness_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 0,
            session_count INTEGER NOT NULL DEFAULT 0,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_awareness_signals_status
        ON runtime_awareness_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_awareness_signals_canonical_key
        ON runtime_awareness_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_reflection_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_reflection_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_reflection_signals_status
        ON runtime_reflection_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflection_signals_canonical_key
        ON runtime_reflection_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_witness_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_witness_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_runtime_witness_signals_status
        ON runtime_witness_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_witness_signals_canonical_key
        ON runtime_witness_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_internal_opposition_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_internal_opposition_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_internal_opposition_signals_status
        ON runtime_internal_opposition_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_internal_opposition_signals_canonical_key
        ON runtime_internal_opposition_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_meaning_significance_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_meaning_significance_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_meaning_significance_signals_status
        ON runtime_meaning_significance_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_meaning_significance_signals_canonical_key
        ON runtime_meaning_significance_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_metabolism_state_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_metabolism_state_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_metabolism_state_signals_status
        ON runtime_metabolism_state_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_metabolism_state_signals_canonical_key
        ON runtime_metabolism_state_signals(canonical_key, id DESC)
        """
    )



def _ensure_runtime_executive_contradiction_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_executive_contradiction_signals (
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
        CREATE INDEX IF NOT EXISTS idx_runtime_executive_contradiction_signals_status
        ON runtime_executive_contradiction_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_executive_contradiction_signals_canonical_key
        ON runtime_executive_contradiction_signals(canonical_key, id DESC)
        """
    )



def _runtime_meaning_significance_signal_from_row(
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



def _runtime_metabolism_state_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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



def _runtime_executive_contradiction_signal_from_row(
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



def _runtime_reflective_critic_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "critic_id": row["critic_id"],
        "critic_type": row["critic_type"],
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



def _runtime_awareness_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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



def _runtime_reflection_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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



def _runtime_witness_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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



def _runtime_internal_opposition_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
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
