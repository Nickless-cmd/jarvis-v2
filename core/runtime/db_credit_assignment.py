"""Credit assignment — schema migration, choice recording, and outcome querying.

Lag 1: links beslutninger (cognitive_decisions) til self-review outcomes,
så Jarvis kan lære af sine valg over tid.

Conventions (Claude review 2026-05-17):
- credit_score: 1-5 scale (self-judgement), not weighted composite
- Drift-delta stored in evidence_summary JSON as raw context
- Eventbus: credit_assignment.choice_recorded + .outcome_linked
- Pending index for O(log N) pre-check every tick
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Schema migration ──────────────────────────────────────────────────────

def ensure_credit_assignment_tables(conn: sqlite3.Connection | None = None) -> None:
    """Add credit-assignment columns to existing tables + pending index.

    Idempotent: columns are added once only. Index is IF NOT EXISTS.
    No-op if they already exist.
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
        # Only create index if table exists (may not be created yet)
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cognitive_decisions'"
        ).fetchone()
        if table_exists:
            conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_cognitive_decisions_pending
                   ON cognitive_decisions(kind, outcome_aggregate)
                   WHERE outcome_aggregate IS NULL
                     AND kind != 'conversational'"""
            )
        conn.commit()
    finally:
        if _close:
            conn.close()


def _migrate_table(
    conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    """Add columns to *table* if they don't already exist.

    Gracefully no-ops if the table itself doesn't exist yet — the
    main init_db() may call ensure_credit_assignment_tables() before
    the table's _ensure_* function has run.
    """
    # Check table existence first — PRAGMA table_info fails on missing table
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not exists:
        return  # table not created yet; columns will be in the CREATE TABLE

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

    Fires credit_assignment.choice_recorded on the eventbus.
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

    # Eventbus: choice_recorded
    try:
        event_bus.publish(
            "credit_assignment.choice_recorded",
            {
                "decision_id": decision_id,
                "kind": kind,
                "created_at": now,
                "score": None,
                "rationale": why or None,
            },
        )
    except Exception:
        pass

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
    evidence_summary: str = "{}",
    run_id: str = "",
) -> dict[str, Any] | None:
    """Link a self-review outcome to a decision and update outcome_aggregate.

    credit_score: 1-5 scale (self-judgement). 5 = excellent, 1 = poor.
    evidence_summary: JSON blob with raw context (drift-delta, signals, etc.).

    Fires credit_assignment.outcome_linked on the eventbus.
    Creates an outcome record in runtime_self_review_outcomes, then updates
    cognitive_decisions.outcome_aggregate with a simple average (1-5 scale).
    """
    now = _now_iso()
    outcome_id = f"ca-{uuid4().hex[:12]}"

    # Guard: clamp credit_score to 1-5
    credit_score_clamped = max(1.0, min(5.0, credit_score))
    credit_score_display = f"{credit_score_clamped}/5"

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
                f"Credit score: {credit_score_display}",
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
                credit_score_clamped,
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
        aggregate = sum(scores) / len(scores) if scores else credit_score_clamped

        conn.execute(
            "UPDATE cognitive_decisions SET outcome_aggregate = ? WHERE decision_id = ?",
            (aggregate, decision_id),
        )

        conn.commit()

    # Eventbus: outcome_linked
    try:
        event_bus.publish(
            "credit_assignment.outcome_linked",
            {
                "decision_id": decision_id,
                "kind": None,  # caller should enrich from decision record
                "created_at": now,
                "score": credit_score_clamped,
                "rationale": rationale or None,
            },
        )
    except Exception:
        pass

    return {
        "decision_id": decision_id,
        "outcome_id": outcome_id,
        "credit_score": credit_score_clamped,
        "aggregate": aggregate,
        "scale": "1-5",
    }


# ── Query surface ─────────────────────────────────────────────────────────

# ── Outcome scorers (Lag 1 Phase 1) ────────────────────────────────────

def score_provider_outcome(decision_id: str, result: dict) -> dict[str, Any] | None:
    """Score a provider_routing decision based on actual call result.

    Uses the primary + booster model from the design doc:
      - call_ok + latency<2s  → 5.0
      - call_ok + latency 2-5s → 4.0
      - call_ok + latency>5s   → 3.0
      - error + fallback worked → 2.5
      - error + no fallback    → 1.0
      - booster: cost < median +0.5

    Returns: link_outcome_to_decision result, or None on error.
    """
    status = result.get("status", "error")
    latency_ms = result.get("latency_ms", 99999)
    fallback_used = result.get("fallback_used", False)

    if status == "ok":
        if latency_ms < 2000:
            primary = 5.0
        elif latency_ms < 5000:
            primary = 4.0
        else:
            primary = 3.0
    else:
        primary = 2.5 if fallback_used else 1.0

    booster = 0.0
    cost = result.get("cost_per_token", 0.0)
    if cost and cost > 0:
        try:
            median_cost = _get_median_provider_cost()
            if cost < median_cost:
                booster = 0.5
        except Exception:
            pass

    score = min(5.0, primary + booster)
    latency_label = f"{latency_ms}ms" if latency_ms < 99999 else "timeout"
    rationale = f"provider: {status}, latency={latency_label}, cost_booster={booster}"

    import json
    evidence = json.dumps({
        "latency_ms": latency_ms,
        "cost_per_token": cost,
        "status": status,
        "fallback_used": fallback_used,
        "primary_score": primary,
        "booster": booster,
    }, ensure_ascii=False)

    return link_outcome_to_decision(
        decision_id=decision_id,
        credit_score=score,
        rationale=rationale,
        evidence_summary=evidence,
        run_id=f"provider-score-{uuid4().hex[:12]}",
    )


def score_tier_outcome(
    decision_id: str,
    tier_used: str,
    next_turns: list[dict],
) -> dict[str, Any] | None:
    """Score a model_tier decision after observing subsequent turns.

    Looks at next_turns for signals of correctness:
      - No correction + task progress → 4.0
      - Over-engineering detected → 2.0
      - Under-tier (missed nuance) → 1.5
      - Auto-escalation happened → 3.5
      - Booster: task completion detected → +1.0
    """
    primary = 3.0  # neutral fallback

    # Collect signals from next_turns
    user_corrected = False
    user_dismissed = False
    task_advanced = False
    over_engineered = False

    for turn in next_turns:
        text = (turn.get("content") or turn.get("text") or "").lower()
        if any(w in text for w in ("nej", "stop", "forkert", "ikke det", "giv kortere", "bare gør")):
            user_corrected = True
            if any(w in text for w in ("bare gør", "bare", "hurtigt")):
                over_engineered = True
        if any(w in text for w in ("tak", "ja", "godt", "👍", "🙏", "perfekt")):
            task_advanced = True
        if any(w in text for w in ("du bestemmer", "det er din opgave", "gør det")):
            task_advanced = True
        if any(w in text for w in ("for lang", "kortere", "for detaljeret")):
            over_engineered = True

    if over_engineered and user_corrected:
        primary = 2.0
    elif user_corrected and not over_engineered:
        # Correction without over-engineering signal → under-tier
        primary = 1.5
    elif task_advanced and not user_corrected:
        primary = 4.0

    # Check for auto-escalation marker
    for turn in next_turns:
        meta = turn.get("_meta", {})
        if isinstance(meta, dict):
            if meta.get("escalated") or meta.get("tier_changed"):
                primary = 3.5
                break

    booster = 1.0 if task_advanced and not user_corrected else 0.0
    score = min(5.0, primary + booster)

    import json
    evidence = json.dumps({
        "tier_used": tier_used,
        "user_corrected": user_corrected,
        "task_advanced": task_advanced,
        "over_engineered": over_engineered,
        "primary_score": primary,
        "booster": booster,
    }, ensure_ascii=False)

    return link_outcome_to_decision(
        decision_id=decision_id,
        credit_score=score,
        rationale=f"tier: {tier_used}, corrected={user_corrected}, advanced={task_advanced}, booster={booster}",
        evidence_summary=evidence,
        run_id=f"tier-score-{uuid4().hex[:12]}",
    )


def score_response_outcome(
    decision_id: str,
    style_used: str,
    user_reply: str,
) -> dict[str, Any] | None:
    """Score a response_style decision based on user engagement.

    Looks for engagement signals in the user's next message:
      - Engagement (tak, smiles, follow-up) → 4.5
      - Neutral continuation → 3.5
      - Correction / ignore → 1.5
      - Explicit style request → 2.0
      - Booster: style matches user's own style → +0.5
    """
    text = (user_reply or "").lower()

    # Engagement signals
    engagement_signals = (
        "tak", "🙏", "👍", "🙂", "😊", "🖤", "smiler",
        "godt", "fedt", "perfekt", "præcis",
        "ja det", "det giver mening", "forstået",
    )
    correction_signals = (
        "nej", "stop", "forkert", "ikke det", "ikke hvad",
        "det var ikke", "du misforstår", "genlæs",
        "prøv igen", "det er ikke",
    )
    style_request_signals = (
        "kortere", "længere", "mere detaljeret", "mindre",
        "kortfattet", "uddyb", "opsummer",
    )

    is_engaged = any(s in text for s in engagement_signals)
    is_correction = any(s in text for s in correction_signals)
    is_style_request = any(s in text for s in style_request_signals)

    if is_engaged and not is_correction:
        primary = 4.5
    elif is_style_request:
        # User is reacting to style (not necessarily negatively)
        primary = 2.0
    elif is_correction:
        primary = 1.5
    else:
        # Neutral — user continued without reacting to style
        primary = 3.5

    # Booster: if style matches user's brevity
    booster = 0.0
    reply_len = len(user_reply or "")
    user_is_brief = reply_len < 80
    if user_is_brief and style_used == "short_direct":
        booster = 0.5
    elif not user_is_brief and style_used == "elaborate":
        booster = 0.5

    score = min(5.0, primary + booster)

    import json
    evidence = json.dumps({
        "style_used": style_used,
        "user_engaged": is_engaged,
        "user_correction": is_correction,
        "user_style_request": is_style_request,
        "reply_length": reply_len,
        "primary_score": primary,
        "booster": booster,
    }, ensure_ascii=False)

    return link_outcome_to_decision(
        decision_id=decision_id,
        credit_score=score,
        rationale=f"style: {style_used}, engaged={is_engaged}, correction={is_correction}, booster={booster}",
        evidence_summary=evidence,
        run_id=f"style-score-{uuid4().hex[:12]}",
    )


def _get_median_provider_cost() -> float:
    """Approximate median cost-per-token across recent cheap-lane calls.

    Returns a conservative estimate (0.001 USD/token) if no data yet.
    This is a fast non-blocking call — reads from cheap_balancer_state.
    """
    try:
        from core.services.cheap_lane_balancer import balancer_snapshot
        snap = balancer_snapshot()
        recent = snap.get("recent_calls", [])
        costs = []
        for call in recent:
            cp = call.get("cost_per_token")
            if cp and isinstance(cp, (int, float)) and cp > 0:
                costs.append(cp)
        if costs:
            costs.sort()
            return costs[len(costs) // 2]
    except Exception:
        pass
    return 0.001  # fallback: 0.1 cent per token


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
