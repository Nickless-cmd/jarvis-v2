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
            trigger_name TEXT,
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
        # Legacy per-turn LLM suspicions were written as broken reviews.
        # Only independently assessed reviews belong in the adherence score.
        adherence, _ = _verified_adherence(conn, decision_id)
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


#: Hvor mange TAELLENDE domme der kraeves, foer en adherence-score maa dannes.
#: Under graensen er svaret «ikke maalt» (None) — ikke «brudt».
_MIN_VERDICTS: int = 3


def _verified_adherence(
    conn: sqlite3.Connection, decision_id: str,
) -> tuple[float | None, str | None]:
    rows = conn.execute(
        """
        SELECT verdict, created_at FROM behavioral_decision_reviews
         WHERE decision_id = ?
           AND (note IS NULL OR note NOT LIKE 'Auto-detected breach:%')
         ORDER BY created_at DESC LIMIT 20
        """,
        (decision_id,),
    ).fetchall()
    values = {"kept": 1.0, "partial": 0.5, "broken": 0.0}
    scored = [values[str(row["verdict"]).lower().strip()]
              for row in rows if str(row["verdict"]).lower().strip() in values]
    # Et maal kraever mere end et par domme (5/10-2026).
    #
    # Maalt samme dag: 72 af 80 aktive beslutninger havde <=2 taellende domme,
    # og ALLE 19 der stod paa 0.0 havde <=2 — ingen af dem havde >=5. Scoren er
    # et gennemsnit over de sidste 20 domme, men de fleste beslutninger naar
    # aldrig 20, og to domme i traek giver 0.0 i ugevis. En ung beslutning kan
    # derfor ikke passere taersklen paa 0.6, og muren af «brudte» beslutninger
    # voksede monotont — praecis den fejlform gatens egen begrundelse advarer
    # mod: «et baand der kan revoke, sletter systematisk de svaere og beholder
    # de lette.»
    #
    # Under graensen returneres None, som betyder IKKE MAALT: gaten laeser None
    # som «aldrig reviewet» og springer beslutningen over, og indbakken
    # registrerer den ikke. Dommene slettes ikke — de ligger append-only, saa
    # grundlaget vokser videre og en score danner sig selv naar der er nok.
    score = (sum(scored) / len(scored)
             if len(scored) >= _MIN_VERDICTS else None)
    return score, str(rows[0]["created_at"]) if rows else None


def repair_legacy_auto_adherence() -> int:
    """Rebuild stored scores after legacy automatic suspicions polluted them.

    The append-only reviews remain intact for audit. Safe to run repeatedly.
    """
    with connect() as conn:
        _ensure_tables(conn)
        ids = [str(row["decision_id"]) for row in conn.execute(
            "SELECT decision_id FROM behavioral_decisions"
        ).fetchall()]
        for decision_id in ids:
            score, reviewed_at = _verified_adherence(conn, decision_id)
            conn.execute(
                "UPDATE behavioral_decisions SET adherence_score = ?, "
                "last_reviewed_at = ? WHERE decision_id = ?",
                (score, reviewed_at, decision_id),
            )
        conn.commit()
    return len(ids)


def update_decision(
    decision_id: str,
    *,
    directive: str | None = None,
    rationale: str | None = None,
    trigger_cue: str | None = None,
    trigger_name: str | None = None,
    priority: int | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    """Update mutable fields on a decision.

    Semantics:
    - ``None``  → field is left unchanged
    - ``""``    → field is cleared to NULL (rationale/trigger_cue/trigger_name)
    - otherwise → field is set to the given value

    ``status`` must be one of VALID_STATUSES; ``priority`` is clamped 0-100.
    Returns the updated row (or None if decision_id is unknown).
    """
    if status is not None and status not in VALID_STATUSES:
        return None
    if not get_decision(decision_id):
        return None

    sets: list[str] = []
    params: list[Any] = []
    if directive is not None:
        sets.append("directive = ?")
        params.append(str(directive).strip())
    if rationale is not None:
        sets.append("rationale = ?")
        params.append(str(rationale).strip() or None)
    if trigger_cue is not None:
        sets.append("trigger_cue = ?")
        params.append(str(trigger_cue).strip() or None)
    if trigger_name is not None:
        sets.append("trigger_name = ?")
        params.append(str(trigger_name).strip() or None)
    if priority is not None:
        sets.append("priority = ?")
        params.append(max(0, min(100, int(priority))))
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if not sets:
        return get_decision(decision_id)  # nothing to change — return as-is

    sets.append("updated_at = ?")
    params.append(_now_iso())
    params.append(decision_id)
    with connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            f"UPDATE behavioral_decisions SET {', '.join(sets)} "
            "WHERE decision_id = ?",
            params,
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
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    """List decisions, newest priority first.

    ``limit=None`` means *no cap*. Dedup'en i
    ``behavioral_decisions.create_decision`` bruger det: loftet på 100 var
    aldrig en semantisk grænse, men den slap igennem som default og lod
    samme direktiv blive oprettet i dublet så snart tabellen voksede forbi
    loftet (26/9-2026).
    """
    where = ""
    params: list[Any] = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    query = (
        f"SELECT * FROM behavioral_decisions {where} "
        "ORDER BY priority DESC, updated_at DESC"
    )
    if limit is not None:
        query += " LIMIT ?"
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
