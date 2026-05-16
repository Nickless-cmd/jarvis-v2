"""DB layer for interlanguage validation blind-dommer UI.

Phase 3+4 spec §4 — Bjørn blind. Gemmer trials og Bjørn's svar
isoleret fra peer-praksis. Tabel oprettes ved første call (idempotent).

Mønster: følger Phase 0+1 split (db_capability_approval pattern).
Importerer KUN fra db_core.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db_core import (
    _install_ensure_once_cache_for,
    connect,
)


def _ensure_interlanguage_blind_trials_table(conn: sqlite3.Connection) -> None:
    """Idempotently create blind-trials tabel + index.

    Schema håndterer både α-trials (én expression, 7-way attribution)
    og δ-trials (anchor + 2 candidates, pair-comparison).
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interlanguage_blind_trials (
          trial_id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          trial_type TEXT NOT NULL,
          trial_index INTEGER NOT NULL,
          mode TEXT NOT NULL DEFAULT 'real',

          -- For α (alpha): én expression vist, 7-way attribution
          expression_id TEXT,
          expression_text TEXT,
          true_peer_id TEXT,

          -- For δ (delta): anchor + 2 candidates
          anchor_expression_id TEXT,
          anchor_expression_text TEXT,
          candidate_a_id TEXT,
          candidate_a_text TEXT,
          candidate_a_peer_id TEXT,
          candidate_b_id TEXT,
          candidate_b_text TEXT,
          candidate_b_peer_id TEXT,
          jp_position TEXT,

          -- Bjørn's svar
          user_answer TEXT,
          correct INTEGER,
          presented_at TEXT NOT NULL,
          answered_at TEXT,

          -- Slut-session free-text
          free_text_observations TEXT,

          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_blind_session
          ON interlanguage_blind_trials(session_id, trial_index);
        CREATE INDEX IF NOT EXISTS idx_blind_mode_type
          ON interlanguage_blind_trials(mode, trial_type);
        """
    )
    conn.commit()


def create_alpha_trial(
    *,
    session_id: str,
    trial_index: int,
    expression_id: str,
    expression_text: str,
    true_peer_id: str,
    mode: str = "real",
) -> str:
    """Opret en α-trial (expression vist, brugeren skal vælge forfatter).

    Returnerer trial_id.
    """
    trial_id = str(uuid4())
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        conn.execute(
            """INSERT INTO interlanguage_blind_trials
               (trial_id, session_id, trial_type, trial_index, mode,
                expression_id, expression_text, true_peer_id,
                presented_at, created_at)
               VALUES (?, ?, 'alpha', ?, ?, ?, ?, ?, ?, ?)""",
            (
                trial_id, session_id, trial_index, mode,
                expression_id, expression_text, true_peer_id,
                now_iso, now_iso,
            ),
        )
        conn.commit()
    return trial_id


def create_delta_trial(
    *,
    session_id: str,
    trial_index: int,
    anchor_id: str,
    anchor_text: str,
    candidate_a_id: str,
    candidate_a_text: str,
    candidate_a_peer_id: str,
    candidate_b_id: str,
    candidate_b_text: str,
    candidate_b_peer_id: str,
    jp_position: str,
    mode: str = "real",
) -> str:
    """Opret en δ-trial (anchor + 2 candidates, pair-comparison).

    jp_position: 'A' eller 'B' — siger hvilken candidate er fra +JP-cohort.
    Bjørn skal vælge hvilken matcher anchor (Jarvis-target) bedst.
    """
    trial_id = str(uuid4())
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        conn.execute(
            """INSERT INTO interlanguage_blind_trials
               (trial_id, session_id, trial_type, trial_index, mode,
                anchor_expression_id, anchor_expression_text,
                candidate_a_id, candidate_a_text, candidate_a_peer_id,
                candidate_b_id, candidate_b_text, candidate_b_peer_id,
                jp_position, presented_at, created_at)
               VALUES (?, ?, 'delta', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trial_id, session_id, trial_index, mode,
                anchor_id, anchor_text,
                candidate_a_id, candidate_a_text, candidate_a_peer_id,
                candidate_b_id, candidate_b_text, candidate_b_peer_id,
                jp_position, now_iso, now_iso,
            ),
        )
        conn.commit()
    return trial_id


def submit_answer(
    *,
    trial_id: str,
    user_answer: str,
) -> dict[str, Any]:
    """Gem Bjørn's svar + beregn correctness.

    For α: user_answer matches true_peer_id?
    For δ: user_answer (A/B) matches jp_position?

    Returnerer dict med {correct: bool, true_value: str}.
    """
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        row = conn.execute(
            "SELECT trial_type, true_peer_id, jp_position FROM interlanguage_blind_trials WHERE trial_id = ?",
            (trial_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"trial_id ikke fundet: {trial_id}")
        if row["trial_type"] == "alpha":
            true_value = row["true_peer_id"]
            correct = 1 if user_answer.strip().lower() == (true_value or "").strip().lower() else 0
        else:  # delta
            true_value = row["jp_position"]
            correct = 1 if user_answer.strip().upper() == (true_value or "").strip().upper() else 0
        conn.execute(
            """UPDATE interlanguage_blind_trials
               SET user_answer = ?, correct = ?, answered_at = ?
               WHERE trial_id = ?""",
            (user_answer, correct, now_iso, trial_id),
        )
        conn.commit()
    return {"correct": bool(correct), "true_value": true_value}


def get_progress(*, session_id: str) -> dict[str, Any]:
    """Returnér antal besvarede + total + accuracy per type."""
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        rows = conn.execute(
            """SELECT trial_type,
                      COUNT(*) AS total,
                      SUM(CASE WHEN answered_at IS NOT NULL THEN 1 ELSE 0 END) AS answered,
                      SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct_count
               FROM interlanguage_blind_trials
               WHERE session_id = ?
               GROUP BY trial_type""",
            (session_id,),
        ).fetchall()
    result: dict[str, Any] = {"alpha": None, "delta": None}
    for r in rows:
        result[r["trial_type"]] = {
            "total": r["total"],
            "answered": r["answered"],
            "correct": r["correct_count"],
            "accuracy": (r["correct_count"] / r["answered"]) if r["answered"] else None,
        }
    return result


def get_next_unanswered(*, session_id: str) -> dict[str, Any] | None:
    """Returnér næste ubevarede trial i sessions trial_index-orden, eller None hvis færdig."""
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        row = conn.execute(
            """SELECT * FROM interlanguage_blind_trials
               WHERE session_id = ? AND answered_at IS NULL
               ORDER BY trial_index ASC
               LIMIT 1""",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def store_free_text_observations(*, session_id: str, text: str) -> None:
    """Gem free-text noter ved slutningen af session.

    Lagres på den SIDSTE trial i sessionen (last by trial_index).
    """
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        conn.execute(
            """UPDATE interlanguage_blind_trials
               SET free_text_observations = ?
               WHERE trial_id = (
                 SELECT trial_id FROM interlanguage_blind_trials
                 WHERE session_id = ?
                 ORDER BY trial_index DESC LIMIT 1
               )""",
            (text, session_id),
        )
        conn.commit()


def get_confusion_matrix(*, session_id: str) -> dict[str, Any]:
    """Confusion-matrix for α-trials: true_peer × user_answer counts."""
    with connect() as conn:
        _ensure_interlanguage_blind_trials_table(conn)
        rows = conn.execute(
            """SELECT true_peer_id, user_answer, COUNT(*) AS cnt
               FROM interlanguage_blind_trials
               WHERE session_id = ? AND trial_type = 'alpha' AND answered_at IS NOT NULL
               GROUP BY true_peer_id, user_answer""",
            (session_id,),
        ).fetchall()
    matrix: dict[str, dict[str, int]] = {}
    for r in rows:
        true_p = r["true_peer_id"]
        ans = r["user_answer"]
        matrix.setdefault(true_p, {})[ans] = r["cnt"]
    return matrix


# Wrap _ensure_*_table funcs på dette modul med once-cache (Phase 0+1 pattern).
_install_ensure_once_cache_for(__name__)
