"""Visible-chat self-state summary — let Jarvis answer questions about
himself from data instead of confabulating.

Background: when Bjørn asked "what's missing in your backend?", Jarvis
replied with claims like "20 commitments at 0% adherence" and "stale
goals collecting dust". The actual DB state was 5 active decisions with
adherence 0.43–0.75 (avg ~0.6) and 4 goals all updated within 48h with
0 stale. He wasn't lying — he just had no access to his own numbers.

The heartbeat prompt already includes this context for autonomous ticks.
Visible chat doesn't. This service produces a small block that gets
injected into visible chat prompts so introspective questions are
answered against real state, not narrative.

Output is intentionally short — under 600 chars typically — and has no
jargon. The model sees concrete numbers and can phrase them naturally.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _decision_summary() -> dict[str, Any]:
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT directive, adherence_score, last_reviewed_at "
                "FROM behavioral_decisions WHERE status = 'active'"
            ).fetchall()
    except Exception as exc:
        logger.debug("self_state_summary: decisions query failed: %s", exc)
        return {}
    if not rows:
        return {"count": 0}
    scores = [
        float(r["adherence_score"])
        for r in rows
        if r["adherence_score"] is not None
    ]
    avg = sum(scores) / len(scores) if scores else None
    never_reviewed = sum(1 for r in rows if not r["last_reviewed_at"])
    return {
        "count": len(rows),
        "avg_adherence": round(avg, 2) if avg is not None else None,
        "scored": len(scores),
        "never_reviewed": never_reviewed,
    }


def _goals_summary() -> dict[str, Any]:
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT title, progress_pct, updated_at "
                "FROM long_horizon_goals WHERE status IN ('active','open')"
            ).fetchall()
    except Exception as exc:
        logger.debug("self_state_summary: goals query failed: %s", exc)
        return {}
    if not rows:
        return {"count": 0}
    progress_values = [int(r["progress_pct"] or 0) for r in rows]
    avg = sum(progress_values) / len(progress_values)
    cutoff = datetime.now(UTC) - timedelta(days=14)
    stale = 0
    for r in rows:
        upd = r["updated_at"] or ""
        try:
            ts = datetime.fromisoformat(upd.replace("Z", "+00:00"))
            if ts < cutoff:
                stale += 1
        except Exception:
            stale += 1  # missing/unparseable counts as stale
    return {
        "count": len(rows),
        "avg_progress_pct": round(avg, 1),
        "stale_count": stale,
    }


def _recent_tick_quality() -> dict[str, Any]:
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='tick_quality_summary_signals'"
            ).fetchone()
            if row is None:
                return {}
            r = conn.execute(
                "SELECT score, summary, created_at FROM tick_quality_summary_signals "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
    except Exception as exc:
        logger.debug("self_state_summary: tick_quality query failed: %s", exc)
        return {}
    if not r:
        return {}
    return {
        "score": int(r["score"] or 0),
        "summary": (str(r["summary"] or "")[:120]),
        "at": str(r["created_at"] or "")[:10],
    }


def build_self_state_block() -> str:
    """Return a short prompt section. Empty string when nothing useful to add."""
    parts: list[str] = []

    decisions = _decision_summary()
    if decisions.get("count"):
        c = decisions["count"]
        avg = decisions.get("avg_adherence")
        scored = decisions.get("scored", 0)
        never = decisions.get("never_reviewed", 0)
        if avg is not None:
            adherence_pct = int(avg * 100)
            parts.append(
                f"behavioral_decisions: {c} active, avg adherence {adherence_pct}% "
                f"(scored {scored}/{c}, never-reviewed {never})"
            )
        else:
            parts.append(f"behavioral_decisions: {c} active, no scores yet")

    goals = _goals_summary()
    if goals.get("count"):
        c = goals["count"]
        avg = goals.get("avg_progress_pct", 0)
        stale = goals.get("stale_count", 0)
        parts.append(
            f"long_horizon_goals: {c} active, avg progress {avg}%, stale {stale}/{c}"
        )

    tick = _recent_tick_quality()
    if tick:
        parts.append(
            f"latest_tick_quality: {tick.get('score')}/100 ({tick.get('at')})"
        )

    if not parts:
        return ""

    return (
        "## Your real-time self-state (use these numbers, don't guess)\n"
        + "\n".join(f"- {p}" for p in parts)
        + "\n\nWhen asked introspective questions about your decisions, goals, "
        "or tick quality: cite these actual numbers, do not confabulate "
        "pessimistic ones. If a metric isn't here, say you can check it."
    )
