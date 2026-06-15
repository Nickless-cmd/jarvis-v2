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
        # Productive idle is a *valid success state* (no priorities to act on,
        # so the tick used time on observation/maintenance). It deserves to
        # cap near the same ceiling as dispatched, not act as a consolation.
        # Was: +25 for ≥2 actions / +10 for 1. Bumped 2026-05-07 because
        # productive_idle previously couldn't score above 55 even when
        # everything went well — that read as "stable but low" tick quality.
        actions = (act.get("result") or {}).get("actions") or []
        if len(actions) >= 2:
            score += 40
            notes.append(f"productive idle: {len(actions)} actions")
        elif actions:
            score += 20
            notes.append(f"productive idle: {len(actions)} action")

    # Healthy elapsed time. Threshold was 30s — set when heartbeat used
    # faster providers (groq llama-3.1-8b). Now the visible/heartbeat lane
    # uses glm-5.1:cloud via Ollama which routinely takes 2-3 minutes per
    # tick. Bumped to 180s (2026-05-07) so legitimate ticks get credit;
    # >180s still indicates a real stall (provider hung, infinite loop).
    elapsed_ms = int(tick_result.get("elapsed_ms") or 0)
    if elapsed_ms > 0 and elapsed_ms < 180_000:
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
    """Compute adherence over ACTIVE behavioral decisions (the curated kind).

    Reads from `behavioral_decisions` (the deliberate action-commitments
    table created via decision-API), NOT from `cognitive_decisions` (which
    is auto-populated by marker-detection on conversation chatter and has
    no status field — using it gave us 0% adherence on phantom decisions).

    A decision's adherence is its rolling adherence_score field. Aggregate
    score = mean across active decisions. Flag = mean < 60%.
    """
    try:
        from core.runtime.db_decisions import list_decisions
        decisions = list_decisions(status="active", limit=50) or []
    except Exception:
        return {"status": "ok", "score": None, "note": "no behavioral_decisions table or list API"}
    if not decisions:
        return {"status": "ok", "score": None, "note": "no active behavioral decisions"}

    scores: list[float] = []
    unreviewed = 0
    duplicate_groups = _duplicate_decision_groups(decisions)
    low_decisions: list[dict[str, Any]] = []
    for d in decisions:
        s = d.get("adherence_score")
        if s is None:
            unreviewed += 1
            continue
        try:
            score_f = float(s)
            scores.append(score_f)
            if score_f < 0.6:
                low_decisions.append({
                    "decision_id": str(d.get("decision_id") or ""),
                    "directive": str(d.get("directive") or "")[:180],
                    "adherence_score": round(score_f, 3),
                    "last_reviewed_at": str(d.get("last_reviewed_at") or ""),
                })
        except (TypeError, ValueError):
            unreviewed += 1
    total = len(decisions)

    if not scores:
        return {
            "status": "ok",
            "score": None,
            "total": total,
            "unreviewed": unreviewed,
            "duplicate_groups": duplicate_groups,
            "note": "no decisions have been reviewed yet — no adherence data",
        }

    mean = sum(scores) / len(scores)
    score = round(mean * 100, 1)
    flag = "under 60% — review and either revoke or strengthen" if score < 60 else None
    recovery = _adherence_recovery_plan(
        score=score,
        low_decisions=low_decisions,
        duplicate_groups=duplicate_groups,
        unreviewed=unreviewed,
    )
    return {
        "status": "ok",
        "score": score,
        "adherence_rate": f"{score}%",
        "total": total,
        "reviewed": len(scores),
        "unreviewed": unreviewed,
        "duplicate_groups": duplicate_groups,
        "low_decisions": low_decisions,
        "recovery": recovery,
        "flag": flag,
    }


def _normalize_decision_directive(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _duplicate_decision_groups(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_directive: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        key = _normalize_decision_directive(decision.get("directive"))
        if not key:
            continue
        by_directive.setdefault(key, []).append(decision)
    groups: list[dict[str, Any]] = []
    for items in by_directive.values():
        if len(items) < 2:
            continue
        items_sorted = sorted(
            items,
            key=lambda item: (
                item.get("adherence_score") is None,
                -int(item.get("priority") or 0),
                str(item.get("created_at") or ""),
            ),
        )
        keeper = items_sorted[0]
        duplicates = items_sorted[1:]
        groups.append({
            "directive": str(keeper.get("directive") or "")[:180],
            "keeper_id": str(keeper.get("decision_id") or ""),
            "duplicate_ids": [str(item.get("decision_id") or "") for item in duplicates],
            "count": len(items),
        })
    return groups


def _adherence_recovery_plan(
    *,
    score: float,
    low_decisions: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
    unreviewed: int,
) -> dict[str, Any]:
    actions: list[str] = []
    if duplicate_groups:
        duplicate_count = sum(len(group.get("duplicate_ids") or []) for group in duplicate_groups)
        actions.append(f"Revoke or merge {duplicate_count} duplicate active decision(s); keep the reviewed/highest-priority one.")
    if low_decisions:
        actions.append("For each low-adherence decision, do one visible recovery action next turn before adding new commitments.")
    if unreviewed:
        actions.append(f"Review {unreviewed} unreviewed active decision(s) before creating replacements.")
    if score < 60:
        actions.append("During tool work, surface a short status before the 5th tool call or explain the blocker.")
    return {
        "needed": bool(actions),
        "actions": actions,
        "focus_decision_ids": [item["decision_id"] for item in low_decisions[:3]],
        "duplicate_groups": duplicate_groups,
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
        line = f"{emoji} Tick-kvalitet (sidste 7d): {avg}/100 ({trend})"
        # Escalation: when the score has been stuck low for a while, surface
        # a sharper line so any active decisions about quality have something
        # concrete to fire against. Without this, quality data is descriptive
        # but never actionable.
        try:
            avg_f = float(avg)
            if avg_f < 50.0:
                line = (
                    f"Tick-kvalitet under tærskel: {avg}/100 over "
                    f"{summary.get('count')} ticks ({trend})."
                )
                # Fire eventbus alarm so other subscribers (council activator,
                # etc.) can react too.
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("tick_quality.alarm", {
                        "avg": avg, "trend": trend,
                        "count": summary.get("count"),
                    })
                except Exception:
                    pass
        except (TypeError, ValueError):
            pass
        parts.append(line)
        # Generalized-learning capture (#159, plan A): tick-kvalitets-vurderingen er
        # en selv-evaluerings-konklusion → fodr den ind i reasoning_store. dedup på dag.
        try:
            from datetime import datetime, timezone
            from core.services.reasoning_store import capture_conclusion
            _day = datetime.now(timezone.utc).date().isoformat()
            capture_conclusion(
                source="self_evaluation",
                conclusion_text=line[:600],
                context="heartbeat tick-kvalitets-evaluering",
                confidence=0.5,
                dedup_key=f"self_evaluation:{_day}:{avg}:{trend}",
            )
        except Exception:
            pass

    # Decision adherence
    adherence = decision_adherence_summary()
    if adherence.get("score") is not None:
        score = adherence["score"]
        if adherence.get("flag"):
            parts.append(f"Decision adherence {score}% (under 60% tærskel)")
            recovery = adherence.get("recovery") if isinstance(adherence.get("recovery"), dict) else {}
            actions = recovery.get("actions") if isinstance(recovery.get("actions"), list) else []
            if actions:
                parts.append(f"Adherence recovery kandidat: {actions[0]}")
        elif score < 80:
            parts.append(f"Decision adherence: {score}% (advisory band)")

    # Stale goals
    stale = detect_stale_goals()
    if stale:
        parts.append(f"Stagnerende mål: {len(stale)} (≥3 dage uden progress)")

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
