"""DB helpers for emotional_memory_anchors table.

Split out from db.py per CLAUDE.md boy scout rule (db.py is 33k lines).
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any

from core.runtime.db import connect, _now_iso


def _ensure_emotional_memory_anchors_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS emotional_memory_anchors (
            anchor_type        TEXT NOT NULL,
            anchor_id          TEXT NOT NULL,
            captured_at        TEXT NOT NULL,
            mood               TEXT NOT NULL,
            intensity          REAL NOT NULL,
            confidence         REAL,
            curiosity          REAL,
            frustration        REAL,
            fatigue            REAL,
            trust              REAL,
            outcome_score      REAL,
            outcome_source     TEXT,
            outcome_updated_at TEXT,
            context_features_json TEXT NOT NULL DEFAULT '{}',
            source             TEXT,
            notes              TEXT,
            PRIMARY KEY (anchor_type, anchor_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emo_mem_type_time
            ON emotional_memory_anchors (anchor_type, captured_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emo_mem_outcome
            ON emotional_memory_anchors (outcome_score)
            WHERE outcome_score IS NOT NULL
        """
    )


def insert_emotional_memory_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    captured_at: str,
    mood: str,
    intensity: float,
    confidence: float | None = None,
    curiosity: float | None = None,
    frustration: float | None = None,
    fatigue: float | None = None,
    trust: float | None = None,
    outcome_score: float | None = None,
    outcome_source: str | None = None,
    context_features_json: str = "{}",
    source: str | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    """UPSERT an emotional memory anchor. Idempotent on (anchor_type, anchor_id)."""
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            with connect() as conn:
                _ensure_emotional_memory_anchors_table(conn)
                conn.execute(
                    """
                    INSERT INTO emotional_memory_anchors
                        (anchor_type, anchor_id, captured_at, mood, intensity,
                         confidence, curiosity, frustration, fatigue, trust,
                         outcome_score, outcome_source, outcome_updated_at,
                         context_features_json, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(anchor_type, anchor_id) DO UPDATE SET
                        captured_at=excluded.captured_at,
                        mood=excluded.mood,
                        intensity=excluded.intensity,
                        confidence=excluded.confidence,
                        curiosity=excluded.curiosity,
                        frustration=excluded.frustration,
                        fatigue=excluded.fatigue,
                        trust=excluded.trust,
                        outcome_score=excluded.outcome_score,
                        outcome_source=excluded.outcome_source,
                        outcome_updated_at=excluded.outcome_updated_at,
                        context_features_json=excluded.context_features_json,
                        source=excluded.source,
                        notes=excluded.notes
                    """,
                    (
                        str(anchor_type)[:60],
                        str(anchor_id)[:240],
                        str(captured_at),
                        str(mood)[:60],
                        float(intensity),
                        confidence,
                        curiosity,
                        frustration,
                        fatigue,
                        trust,
                        outcome_score,
                        outcome_source,
                        _now_iso() if outcome_score is not None else None,
                        str(context_features_json or "{}"),
                        source,
                        notes,
                    ),
                )
            return {
                "anchor_type": anchor_type,
                "anchor_id": anchor_id,
                "captured_at": captured_at,
            }
        except sqlite3.OperationalError as exc:
            last_err = exc
            if attempt == 0:
                time.sleep(0.05)
                continue
            raise
    if last_err:
        raise last_err
    return {
        "anchor_type": anchor_type,
        "anchor_id": anchor_id,
        "captured_at": captured_at,
    }


def get_emotional_memory_anchor(
    anchor_type: str, anchor_id: str
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        row = conn.execute(
            "SELECT * FROM emotional_memory_anchors WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_emotional_memory_anchors(
    *,
    anchor_type: str | None = None,
    since: str | None = None,
    min_intensity: float | None = None,
    outcome: str | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Return anchors filtered and ordered by captured_at DESC."""
    where: list[str] = []
    params: list[Any] = []
    if anchor_type:
        where.append("anchor_type = ?")
        params.append(str(anchor_type))
    if since:
        where.append("captured_at >= ?")
        params.append(str(since))
    if min_intensity is not None:
        where.append("intensity >= ?")
        params.append(float(min_intensity))
    if outcome == "bad":
        where.append("outcome_score IS NOT NULL AND outcome_score < -0.2")
    elif outcome == "good":
        where.append("outcome_score IS NOT NULL AND outcome_score > 0.2")

    sql = "SELECT * FROM emotional_memory_anchors"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY captured_at DESC LIMIT ?"
    params.append(max(int(limit), 1))

    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_emotional_memory_outcome(
    *,
    anchor_type: str,
    anchor_id: str,
    score: float,
    source: str,
    force: bool = False,
) -> bool:
    """Update outcome score. Returns True if updated, False if blocked.

    An explicit override (source starting with 'override:') can be replaced by
    another explicit override only if force=True. Auto-derived outcomes can
    always be overridden without force.
    """
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        existing = conn.execute(
            "SELECT outcome_source FROM emotional_memory_anchors "
            "WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        ).fetchone()
        if existing is None:
            return False
        existing_source = str(existing["outcome_source"] or "")
        is_existing_override = existing_source.startswith("override:")
        if is_existing_override and not force:
            return False
        conn.execute(
            """
            UPDATE emotional_memory_anchors
            SET outcome_score = ?, outcome_source = ?, outcome_updated_at = ?
            WHERE anchor_type = ? AND anchor_id = ?
            """,
            (
                float(score),
                str(source)[:60],
                _now_iso(),
                str(anchor_type),
                str(anchor_id),
            ),
        )
    return True


def delete_emotional_memory_anchor(anchor_type: str, anchor_id: str) -> bool:
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        cur = conn.execute(
            "DELETE FROM emotional_memory_anchors WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        )
        return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "anchor_type": row["anchor_type"],
        "anchor_id": row["anchor_id"],
        "captured_at": row["captured_at"],
        "mood": row["mood"],
        "intensity": row["intensity"],
        "confidence": row["confidence"],
        "curiosity": row["curiosity"],
        "frustration": row["frustration"],
        "fatigue": row["fatigue"],
        "trust": row["trust"],
        "outcome_score": row["outcome_score"],
        "outcome_source": row["outcome_source"],
        "outcome_updated_at": row["outcome_updated_at"],
        "context_features_json": row["context_features_json"],
        "source": row["source"],
        "notes": row["notes"],
    }
