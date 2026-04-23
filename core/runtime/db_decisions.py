"""Behavioral decisions store — commitments Jarvis makes to himself.

A decision is a concrete directive Jarvis has chosen to follow in the
future, often born from a reflection ("I noticed I cut people off —
from now on I'll pause before replying"). Unlike a passive reflection,
a decision surfaces in the heartbeat every cycle and can be reviewed
for adherence.

Schema:
- behavioral_decisions: one row per commitment (directive, rationale,
  status, trigger_cue, adherence metadata)
- behavioral_decision_reviews: append-only reviews of how well the
  decision is being kept (so Jarvis can notice drift or success)
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


VALID_STATUSES = {"active", "paused", "revoked", "fulfilled"}


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS behavioral_decisions (
            decision_id TEXT PRIMARY KEY,
            directive TEXT NOT NULL,
            rationale TEXT,
            trigger_cue TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 50,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_reviewed_at TEXT,
            adherence_score REAL,
            source_record_id TEXT,
            source_type TEXT,
            created_by TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_status "
        "ON behavioral_decisions (status, priority DESC, updated_at DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS behavioral_decision_reviews (
            review_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verdict TEXT NOT NULL,
            note TEXT,
            evidence TEXT,
            FOREIGN KEY (decision_id) REFERENCES behavioral_decisions(decision_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decision_reviews_decision "
        "ON behavioral_decision_reviews (decision_id, created_at DESC)"
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_decision(
    *,
    directive: str,
    rationale: str | None = None,
    trigger_cue: str | None = None,
    priority: int = 50,
    source_record_id: str | None = None,
    source_type: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    decision_id = _new_id("dec")
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO behavioral_decisions (
                decision_id, directive, rationale, trigger_cue, status,
                priority, created_at, updated_at, source_record_id,
                source_type, created_by
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                directive.strip(),
                (rationale or "").strip() or None,
                (trigger_cue or "").strip() or None,
                max(0, min(100, int(priority))),
                now,
                now,
                source_record_id,
                source_type,
                created_by,
            ),
        )
        conn.commit()
    return get_decision(decision_id) or {}


def append_review(
    *,
    decision_id: str,
    verdict: str,
    note: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any] | None:
    """Record a self-assessment: how am I doing on this?

    verdict: 'kept', 'broken', 'partial', 'irrelevant'
    Updates adherence_score as rolling average of (kept=1.0, partial=0.5,
    broken=0.0, irrelevant=ignored) over the last 20 reviews.
    """
    decision = get_decision(decision_id)
    if not decision:
        return None
    review_id = _new_id("rev")
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO behavioral_decision_reviews (
                review_id, decision_id, created_at, verdict, note, evidence
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                decision_id,
                now,
                verdict.strip(),
                (note or "").strip() or None,
                (evidence or "").strip() or None,
            ),
        )
        # compute rolling adherence over last 20 reviews (ignoring 'irrelevant')
        rows = conn.execute(
            """
            SELECT verdict FROM behavioral_decision_reviews
             WHERE decision_id = ?
             ORDER BY created_at DESC LIMIT 20
            """,
            (decision_id,),
        ).fetchall()
        scored = []
        for r in rows:
            v = str(r["verdict"]).lower().strip()
            if v == "kept":
                scored.append(1.0)
            elif v == "partial":
                scored.append(0.5)
            elif v == "broken":
                scored.append(0.0)
        adherence = sum(scored) / len(scored) if scored else None
        conn.execute(
            """
            UPDATE behavioral_decisions
               SET last_reviewed_at = ?,
                   adherence_score = ?,
                   updated_at = ?
             WHERE decision_id = ?
            """,
            (now, adherence, now, decision_id),
        )
        conn.commit()
    return get_decision(decision_id)


def set_status(decision_id: str, new_status: str) -> dict[str, Any] | None:
    if new_status not in VALID_STATUSES:
        return None
    if not get_decision(decision_id):
        return None
    now = _now_iso()
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE behavioral_decisions SET status = ?, updated_at = ? "
            "WHERE decision_id = ?",
            (new_status, now, decision_id),
        )
        conn.commit()
    return get_decision(decision_id)


def get_decision(decision_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM behavioral_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_decisions(
    *,
    status: str | None = "active",
    limit: int = 50,
) -> list[dict[str, Any]]:
    where = ""
    params: list[Any] = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    query = (
        f"SELECT * FROM behavioral_decisions {where} "
        "ORDER BY priority DESC, updated_at DESC LIMIT ?"
    )
    params.append(int(limit))
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def list_reviews(decision_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT * FROM behavioral_decision_reviews "
            "WHERE decision_id = ? ORDER BY created_at DESC LIMIT ?",
            (decision_id, int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_decision(decision_id: str) -> bool:
    with connect() as conn:
        _ensure_tables(conn)
        cur = conn.execute(
            "DELETE FROM behavioral_decisions WHERE decision_id = ?",
            (decision_id,),
        )
        conn.execute(
            "DELETE FROM behavioral_decision_reviews WHERE decision_id = ?",
            (decision_id,),
        )
        conn.commit()
    return (cur.rowcount or 0) > 0


def count_decisions(*, status: str | None = None) -> int:
    where = ""
    params: list[Any] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    with connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM behavioral_decisions {where}",
            params,
        ).fetchone()
    return int(row["c"] if row else 0)
