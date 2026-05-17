"""Credit assignment — schema migration, choice recording, and outcome querying.

Lag 1: links beslutninger (cognitive_decisions) til self-review outcomes,
så Jarvis kan lære af sine valg over tid.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db import connect


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Schema migration ──────────────────────────────────────────────────────

def ensure_credit_assignment_tables(conn: sqlite3.Connection | None = None) -> None:
    """Add credit-assignment columns to existing tables.

    Idempotent: columns are added once only. No-op if they already exist.
    """
    _close = False
    if conn is None:
        conn = connect()
        _close = True
    try:
        _migrate_table(
            conn,
            "cognitive_decisions",
            [
                ("kind", "TEXT NOT NULL DEFAULT 'conversational'"),
                ("outcome_aggregate", "REAL"),
            ],
        )
        _migrate_table(
            conn,
            "runtime_self_review_outcomes",
            [
                ("decision_id", "TEXT"),
                ("credit_score", "REAL"),
            ],
        )
    finally:
        if _close:
            conn.close()


def _migrate_table(
    conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    """Add columns to *table* if they don't already exist."""
    existing = {
        row[1].lower()
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    for col_name, col_type in columns:
        if col_name.lower() not in existing:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
            )
    conn.commit()


# ── Choice recording ──────────────────────────────────────────────────────

def record_choice(
    *,
    kind: str = "conversational",
    title: str,
    options: list[str],
    decision: str,
    why: str = "",
    context: str = "",
) -> str:
    """Record a choice in cognitive_decisions with a kind tag.

    Returns the decision_id so outcome hooks can reference it later.
    """
    decision_id = f"dec-{uuid4().hex[:12]}"
    now = _now_iso()

    with connect() as conn:
        ensure_credit_assignment_tables(conn)
        conn.execute(
            """INSERT INTO cognitive_decisions
               (decision_id, title, context, options, decision, why, regrets, refs,
                created_at, kind, outcome_aggregate)
               VALUES (?, ?, ?, ?, ?, ?, '[]', '[]', ?, ?, NULL)""",
            (
                decision_id,
                title,
                context,
                json.dumps(options),
                decision,
                why,
                now,
                kind,
            ),
        )
        conn.commit()

    return decision_id


def list_unreviewed_decisions(
    *, kind: str | None = "prompt_variant", limit: int = 10
) -> list[dict[str, Any]]:
    """Find decisions of a given *kind* that have no linked outcome yet.

    A decision is "unreviewed" when cognitive_decisions.outcome_aggregate IS NULL.
    """
    with connect() as conn:
        ensure_credit_assignment_tables(conn)
        if kind:
            rows = conn.execute(
                """SELECT * FROM cognitive_decisions
                   WHERE kind = ? AND outcome_aggregate IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (kind, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM cognitive_decisions
                   WHERE outcome_aggregate IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Outcome linking ───────────────────────────────────────────────────────

def link_outcome_to_decision(
    *,
    decision_id: str,
    credit_score: float,
    rationale: str,
    evidence_summary: str,
    run_id: str = "",
) -> dict[str, Any] | None:
    """Link a self-review outcome to a decision and update outcome_aggregate.

    Creates an outcome record in runtime_self_review_outcomes, then updates
    cognitive_decisions.outcome_aggregate with a simple average.
    """
    now = _now_iso()
    outcome_id = f"ca-{uuid4().hex[:12]}"

    with connect() as conn:
        ensure_credit_assignment_tables(conn)

        # 1. Insert outcome with decision_id link
        conn.execute(
            """INSERT INTO runtime_self_review_outcomes
               (outcome_id, outcome_type, canonical_key, status,
                title, summary, rationale,
                source_kind, confidence, evidence_summary, support_summary,
                status_reason, review_run_id, session_id,
                support_count, session_count, merge_count,
                created_at, updated_at,
                decision_id, credit_score)
               VALUES (?, ?, ?, ?,
                       ?, ?, ?,
                       ?, ?, ?, ?,
                       ?, ?, ?,
                       ?, ?, ?,
                       ?, ?,
                       ?, ?)""",
            (
                outcome_id,
                "credit_assignment",
                decision_id,
                "active",
                f"Lag 1 outcome: {decision_id}",
                f"Credit score: {credit_score}/100",
                rationale,
                "meta_reflection",
                "medium",
                evidence_summary,
                "",
                "",
                run_id,
                "",
                1,
                1,
                0,
                now,
                now,
                decision_id,
                credit_score,
            ),
        )

        # 2. Compute rolling average outcome_aggregate for this decision
        all_outcomes = conn.execute(
            """SELECT credit_score FROM runtime_self_review_outcomes
               WHERE decision_id = ? AND credit_score IS NOT NULL
               ORDER BY created_at DESC LIMIT 20""",
            (decision_id,),
        ).fetchall()

        scores = [r["credit_score"] for r in all_outcomes if r["credit_score"] is not None]
        aggregate = sum(scores) / len(scores) if scores else credit_score

        conn.execute(
            "UPDATE cognitive_decisions SET outcome_aggregate = ? WHERE decision_id = ?",
            (aggregate, decision_id),
        )

        conn.commit()

    return {"decision_id": decision_id, "outcome_id": outcome_id, "credit_score": credit_score, "aggregate": aggregate}


# ── Query surface ─────────────────────────────────────────────────────────

def get_credit_trend(
    *, kind: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Show decisions with their outcomes for oversight."""
    with connect() as conn:
        ensure_credit_assignment_tables(conn)
        where_clause = "cd.kind != 'conversational'"
        params: list[Any] = []
        if kind:
            where_clause = "cd.kind = ?"
            params.append(kind)
        rows = conn.execute(
            f"""SELECT cd.kind, cd.title, cd.decision,
                       cd.outcome_aggregate, cd.created_at AS decision_at,
                       rsro.credit_score, rsro.created_at AS reviewed_at,
                       rsro.rationale, rsro.evidence_summary
                FROM cognitive_decisions cd
                LEFT JOIN runtime_self_review_outcomes rsro
                  ON rsro.decision_id = cd.decision_id
                WHERE {where_clause}
                ORDER BY cd.created_at DESC
                LIMIT ?""",
            params + [limit],
        ).fetchall()
    return [dict(r) for r in rows]
