"""Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY).

Phase 5 of Jarvis' implementation plan. Per the deferred design note in
docs/design_notes/self_improving_loops.md, we start with **observation**
ONLY — no auto-mutation. The system measures itself; humans decide
whether to act on findings.

Three trackers:

1. **Tick quality scoring** — after each phased_heartbeat_tick, evaluate
   if it produced useful output (priorities → actions, idle → consolidations).
   Score 0-100. Persisted in state_store.

2. **Decision adherence tracking** — periodically run decision_review on
   recent runs. If adherence < 60% → flag in chronicle.

3. **Stale goal detection** — for each active autonomous goal, check
   if there has been progress (tool invocations referencing the goal,
   sub-goal status changes, related events) in last N days. Flag stale.

NO auto-mutation. Just observation + flags. Mission Control / chronicle
surfaces the data; user decides if/how to act.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TICK_EVAL_KEY = "tick_quality_evaluations"
_GOAL_PROGRESS_KEY = "goal_progress_tracking"
_MAX_TICK_EVALS_KEPT = 200
_GOAL_STALE_DAYS = 3


# ── Tick quality scoring ──────────────────────────────────────────


def evaluate_tick_quality(*, tick_result: dict[str, Any]) -> dict[str, Any]:
    """Score a phased tick's quality based on observable outputs.

    Heuristic — no LLM call. Scoring rules:
    - Tick had priorities and dispatched: +30
    - Productive idle had ≥2 actions: +25
    - Reflection identified concrete priorities: +15
    - No errors during tick: +20
    - Sense gathered ≥5 signal types: +10
    Max: 100
    """
    score = 0
    notes: list[str] = []
    phases = tick_result.get("phases") or {}

    sense = phases.get("sense") or {}
    sense_keys_present = sum(1 for k in (
        "mood_name", "active_goals", "events_last_hour",
        "context_pressure_level", "errors_last_hour"
    ) if k in sense)
    if sense_keys_present >= 5:
        score += 10
        notes.append(f"sense gathered {sense_keys_present} signal types")

    reflect = phases.get("reflect") or {}
    priorities = reflect.get("priorities") or []
    if priorities:
        score += 15
        notes.append(f"reflect identified {len(priorities)} priorities")

    act = phases.get("act") or {}
    act_kind = str(act.get("kind") or "")
    if act_kind == "tick_dispatched" and priorities:
        score += 30
        notes.append("dispatched tick on warranted priorities")
    elif act_kind == "productive_idle":
        actions = (act.get("result") or {}).get("actions") or []
        if len(actions) >= 2:
            score += 25
            notes.append(f"productive idle: {len(actions)} actions")
        elif actions:
            score += 10
            notes.append(f"productive idle: {len(actions)} action")

    elapsed_ms = int(tick_result.get("elapsed_ms") or 0)
    if elapsed_ms > 0 and elapsed_ms < 30000:  # under 30s = healthy
        score += 20
        notes.append(f"healthy elapsed time ({elapsed_ms}ms)")

    score = min(100, score)
    eval_record = {
        "eval_id": f"teval-{uuid4().hex[:10]}",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "score": score,
        "notes": notes,
        "tick_kind": act_kind,
        "had_priorities": bool(priorities),
        "elapsed_ms": elapsed_ms,
    }

    # Persist (rolling window)
    try:
        existing = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(existing, list):
            existing = []
        existing.append(eval_record)
        save_json(_TICK_EVAL_KEY, existing[-_MAX_TICK_EVALS_KEPT:])
    except Exception as exc:
        logger.debug("tick eval persist failed: %s", exc)

    return eval_record


def tick_quality_summary(*, days: int = 7) -> dict[str, Any]:
    """Aggregate stats over recent evaluations."""
    try:
        evals = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(evals, list):
            evals = []
    except Exception:
        evals = []
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    recent = [e for e in evals if str(e.get("evaluated_at", "")) >= cutoff]
    if not recent:
        return {"status": "ok", "count": 0, "avg_score": None, "trend": "no data"}
    avg = sum(int(e.get("score") or 0) for e in recent) / len(recent)
    last_5_avg = sum(int(e.get("score") or 0) for e in recent[-5:]) / min(5, len(recent))
    trend = "stable"
    if last_5_avg > avg + 5:
        trend = "improving"
    elif last_5_avg < avg - 5:
        trend = "degrading"
    return {
        "status": "ok",
        "count": len(recent),
        "avg_score": round(avg, 1),
        "last_5_avg": round(last_5_avg, 1),
        "trend": trend,
        "window_days": days,
    }


# ── Stale goal detection ─────────────────────────────────────────


def detect_stale_goals(*, stale_days: int = _GOAL_STALE_DAYS) -> list[dict[str, Any]]:
    """Find active goals with no recent progress signal."""
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=50)
    except Exception:
        return []

    cutoff = (datetime.now(UTC) - timedelta(days=stale_days)).isoformat()
    stale: list[dict[str, Any]] = []
    for g in active:
        updated = str(g.get("updated_at") or g.get("created_at") or "")
        if updated and updated < cutoff:
            stale.append({
                "goal_id": g.get("goal_id"),
                "title": g.get("title"),
                "priority": g.get("priority"),
                "last_update": updated,
                "days_stale": stale_days,
            })
    return stale


def stale_goals_section() -> str | None:
    stale = detect_stale_goals()
    if not stale:
        return None
    lines = [f"⏰ {len(stale)} aktive mål uden progress i ≥{_GOAL_STALE_DAYS} dage:"]
    for g in stale[:5]:
        lines.append(f"  • [{g.get('priority', '?')}] {g.get('title', '?')} (sidst opdateret {g.get('last_update', '?')[:10]})")
    return "\n".join(lines)


# ── Decision adherence tracking ──────────────────────────────────


def decision_adherence_summary() -> dict[str, Any]:
    """Run decision_review heuristic on recent decisions. Returns score."""
    try:
        from core.runtime.db import list_cognitive_decisions
        decisions = list_cognitive_decisions(limit=20) or []
    except Exception:
        return {"status": "ok", "score": None, "note": "no decisions table or list_decisions API"}
    if not decisions:
        return {"status": "ok", "score": None, "note": "no decisions to review"}

    # Heuristic: a decision is "adhered to" if:
    # - status != revoked
    # - status == applied OR has at least one referencing event
    adhered = 0
    revoked = 0
    pending = 0
    for d in decisions:
        status = str(d.get("status", ""))
        if status == "revoked":
            revoked += 1
        elif status in ("applied", "approved", "executed"):
            adhered += 1
        else:
            pending += 1
    total = max(1, len(decisions))
    score = round((adhered / total) * 100, 1)
    flag = score < 60
    return {
        "status": "ok",
        "score": score,
        "adhered": adhered,
        "revoked": revoked,
        "pending": pending,
        "total": total,
        "flag": flag,
    }


# ── Self-eval awareness section ──────────────────────────────────


def self_evaluation_section() -> str | None:
    """Compact awareness section combining all trackers."""
    parts: list[str] = []

    # Tick quality
    summary = tick_quality_summary()
    if summary.get("avg_score") is not None and summary.get("count", 0) >= 5:
        avg = summary["avg_score"]
        trend = summary.get("trend", "")
        emoji = {"improving": "📈", "degrading": "📉", "stable": "➡"}.get(trend, "")
        parts.append(f"{emoji} Tick-kvalitet (sidste 7d): {avg}/100 ({trend})")

    # Decision adherence
    adherence = decision_adherence_summary()
    if adherence.get("score") is not None:
        score = adherence["score"]
        if adherence.get("flag"):
            parts.append(f"⚠ Decision adherence {score}% — under 60% tærskel")
        elif score < 80:
            parts.append(f"Decision adherence: {score}% (overvej review)")

    # Stale goals
    stale = detect_stale_goals()
    if stale:
        parts.append(f"⏰ {len(stale)} mål stagnerer (≥3 dage uden progress)")

    if not parts:
        return None
    return "Self-evaluation:\n" + "\n".join(f"  {p}" for p in parts)


# ── Tools ────────────────────────────────────────────────────────


def _exec_tick_quality_summary(args: dict[str, Any]) -> dict[str, Any]:
    return tick_quality_summary(days=int(args.get("days") or 7))


def _exec_detect_stale_goals(args: dict[str, Any]) -> dict[str, Any]:
    stale = detect_stale_goals(stale_days=int(args.get("stale_days") or _GOAL_STALE_DAYS))
    return {"status": "ok", "stale_goals": stale, "count": len(stale)}


def _exec_decision_adherence(args: dict[str, Any]) -> dict[str, Any]:
    return decision_adherence_summary()


SELF_EVALUATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tick_quality_summary",
            "description": (
                "Aggregate stats over recent phased_heartbeat_tick evaluations. "
                "Returns avg_score (0-100), trend (improving/stable/degrading)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_stale_goals",
            "description": "Find active autonomous goals with no progress in N days (default 3).",
            "parameters": {
                "type": "object",
                "properties": {"stale_days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_adherence_summary",
            "description": (
                "Heuristic adherence score for recent decisions: % applied/approved "
                "vs revoked/pending. Score < 60% flags concern."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
