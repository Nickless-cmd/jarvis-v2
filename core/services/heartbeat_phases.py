"""Heartbeat phases — explicit Sense / Reflect / Act structure on top of existing tick.

Existing run_heartbeat_tick is monolithic (~600 lines of merged
behaviour). Rather than rewriting that, this module adds an EXPLICIT
3-phase structure as a wrapper/companion:

  Sense:    Gather all relevant signals (mood, goals, events, sensory)
  Reflect:  Generate inner reflection on state + priorities (cheap LLM)
  Act:      Either dispatch to existing tick OR run productive idle work

Productive idle is the key insight — when there's no obvious action,
don't just wait. Use the time for consolidation, dream generation,
self-review, sensory recording. Idle ticks are NOT wasted ticks.

Adaptive cadence: track recent activity level, suggest next interval.
- High activity → 5 min
- Normal → 15 min
- Idle → 30 min (with productive work)

Design choice: this module DOES NOT replace run_heartbeat_tick. It
calls it as part of act_phase when action is warranted. Existing
behaviour preserved; new phase-explicit observability layered on top.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_HIGH_ACTIVITY_TICK_THRESHOLD = 8     # tools/min in last hour
_LOW_ACTIVITY_TICK_THRESHOLD = 1
_PRODUCTIVE_IDLE_BUDGET_SECONDS = 30   # cap for idle work


# ── Phase 1: Sense ─────────────────────────────────────────────────────


def sense_phase(*, name: str = "default") -> dict[str, Any]:
    """Gather signals for this tick. Pure-read — no side effects."""
    signals: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "name": name,
    }

    # Mood + temperature
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        signals["mood_name"] = str(get_current_mood() or "")
        signals["mood_intensity"] = float(get_mood_intensity() or 0.0)
    except Exception:
        pass
    try:
        from core.services.affective_meta_state import current_temperature_field
        signals["temperature_field"] = str(current_temperature_field() or "")
    except Exception:
        pass

    # Active goals
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=5)
        signals["active_goals"] = [
            {"goal_id": g.get("goal_id"), "title": g.get("title"), "priority": g.get("priority")}
            for g in active
        ]
    except Exception:
        signals["active_goals"] = []

    # Recent eventbus activity (last hour)
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=300)
        cutoff = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        recent = [e for e in events if str(e.get("created_at", "")) >= cutoff]
        signals["events_last_hour"] = len(recent)
        signals["tool_invocations_last_hour"] = sum(
            1 for e in recent if str(e.get("kind", "")) == "tool.invoked"
        )
        signals["errors_last_hour"] = sum(
            1 for e in recent
            if str(e.get("kind", "")) == "tool.completed"
            and str((e.get("payload") or {}).get("status", "")) == "error"
        )
    except Exception:
        signals.update({
            "events_last_hour": 0,
            "tool_invocations_last_hour": 0,
            "errors_last_hour": 0,
        })

    # Open questions / curiosity
    try:
        from core.services.curiosity_daemon import _open_questions
        signals["open_questions_count"] = len(list(_open_questions or []))
    except Exception:
        signals["open_questions_count"] = 0

    # Verification gate state (from earlier work)
    try:
        from core.services.verification_gate import evaluate_verification_gate
        gate = evaluate_verification_gate(minutes=15)
        signals["unverified_mutations"] = int(gate.get("unverified_count") or 0)
        signals["failed_verifies"] = int(gate.get("failed_verify_count") or 0)
    except Exception:
        signals["unverified_mutations"] = 0
        signals["failed_verifies"] = 0

    # Context pressure
    try:
        from core.services.context_window_manager import estimate_pressure
        pressure = estimate_pressure()
        signals["context_pressure_level"] = str(pressure.get("level") or "")
        signals["context_tokens"] = int(pressure.get("estimated_tokens") or 0)
    except Exception:
        pass

    return signals


# ── Phase 2: Reflect ───────────────────────────────────────────────────


def _classify_activity(signals: dict[str, Any]) -> str:
    """Classify current activity level from signals."""
    tool_count = int(signals.get("tool_invocations_last_hour") or 0)
    if tool_count >= _HIGH_ACTIVITY_TICK_THRESHOLD * 60:  # tools/hour scaled
        return "high"
    if tool_count <= _LOW_ACTIVITY_TICK_THRESHOLD * 60:
        return "idle"
    return "normal"


def _identify_priorities(signals: dict[str, Any]) -> list[str]:
    """Heuristic — what should this tick attend to?"""
    priorities: list[str] = []
    if int(signals.get("failed_verifies") or 0) >= 1:
        priorities.append("address_failed_verifications")
    if int(signals.get("unverified_mutations") or 0) >= 3:
        priorities.append("verify_recent_mutations")
    if str(signals.get("context_pressure_level", "")) in ("high", "critical"):
        priorities.append("compact_context")
    if signals.get("active_goals"):
        priorities.append("advance_goals")
    if int(signals.get("errors_last_hour") or 0) >= 5:
        priorities.append("investigate_errors")
    return priorities


def reflect_phase(signals: dict[str, Any]) -> dict[str, Any]:
    """Synthesize reflection. Heuristic-only by default; LLM optional."""
    activity = _classify_activity(signals)
    priorities = _identify_priorities(signals)
    reflection: dict[str, Any] = {
        "activity_level": activity,
        "priorities": priorities,
        "reflection_kind": "heuristic",
    }
    # Recommend next-tick interval based on activity
    if activity == "high":
        reflection["suggested_next_interval_seconds"] = 300   # 5 min
    elif activity == "idle":
        reflection["suggested_next_interval_seconds"] = 1800  # 30 min
    else:
        reflection["suggested_next_interval_seconds"] = 900   # 15 min
    return reflection


# ── Phase 3: Act (or productive idle) ──────────────────────────────────


def productive_idle(*, budget_seconds: float = _PRODUCTIVE_IDLE_BUDGET_SECONDS) -> dict[str, Any]:
    """Run light maintenance work when there's no clear action. Time-bounded."""
    started = time.time()
    actions: list[str] = []

    def _budget_left() -> bool:
        return (time.time() - started) < budget_seconds

    # 1. Memory consolidation if any pending
    if _budget_left():
        try:
            from core.services.memory_consolidator import consolidate_pending_memories  # type: ignore
            res = consolidate_pending_memories(limit=3)
            if res:
                actions.append(f"memory_consolidate:{res.get('merged', 0)}")
        except Exception:
            pass

    # 2. Personality drift snapshot (safe, frequent)
    if _budget_left():
        try:
            from core.services.personality_drift import take_snapshot
            snap = take_snapshot()
            if snap.get("status") == "ok":
                actions.append("personality_snapshot")
        except Exception:
            pass

    # 3. Surprise detection (anomaly scan)
    if _budget_left():
        try:
            from core.services.surprise_detector import scan_for_surprises  # type: ignore
            res = scan_for_surprises()
            if res and res.get("surprises_detected"):
                actions.append(f"surprises:{res.get('count', 0)}")
        except Exception:
            pass

    # 4. Composite candidate mining (cheap, observational)
    if _budget_left():
        try:
            from core.services.tool_pattern_miner import find_candidate_composites
            res = find_candidate_composites(max_results=3)
            if res.get("candidates"):
                actions.append(f"composite_candidates:{len(res['candidates'])}")
        except Exception:
            pass

    elapsed = time.time() - started
    return {
        "kind": "productive_idle",
        "actions": actions,
        "elapsed_seconds": round(elapsed, 2),
        "budget_seconds": budget_seconds,
    }


def act_phase(
    *,
    signals: dict[str, Any],
    reflection: dict[str, Any],
    name: str = "default",
    trigger: str = "phased",
) -> dict[str, Any]:
    """Either run normal heartbeat tick OR productive idle, based on reflection."""
    activity = str(reflection.get("activity_level") or "normal")
    priorities = reflection.get("priorities") or []

    if priorities or activity == "high":
        # Action warranted — dispatch to existing tick
        try:
            from core.services.heartbeat_runtime import run_heartbeat_tick
            tick_result = run_heartbeat_tick(name=name, trigger=trigger)
            return {
                "kind": "tick_dispatched",
                "trigger": trigger,
                "had_priorities": bool(priorities),
                "tick_status": getattr(tick_result, "status", "unknown") if tick_result else "none",
            }
        except Exception as exc:
            logger.warning("act_phase: tick dispatch failed: %s", exc)
            return {"kind": "tick_failed", "error": str(exc)}

    # No clear action — productive idle
    idle_result = productive_idle()
    return {"kind": "productive_idle", "result": idle_result}


# ── Orchestrator ───────────────────────────────────────────────────────


def tick_with_phases(*, name: str = "default", trigger: str = "phased") -> dict[str, Any]:
    """Run all 3 phases in sequence, return structured result."""
    started = datetime.now(UTC)
    signals = sense_phase(name=name)
    reflection = reflect_phase(signals)
    action = act_phase(signals=signals, reflection=reflection, name=name, trigger=trigger)
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    result = {
        "status": "ok",
        "name": name,
        "trigger": trigger,
        "phases": {
            "sense": signals,
            "reflect": reflection,
            "act": action,
        },
        "elapsed_ms": elapsed_ms,
    }
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "heartbeat.phased_tick",
            {
                "activity_level": reflection.get("activity_level"),
                "priorities": reflection.get("priorities"),
                "act_kind": action.get("kind"),
                "elapsed_ms": elapsed_ms,
            },
        )
    except Exception:
        pass
    return result


# ── Tool exposure ──────────────────────────────────────────────────────


def _exec_phased_tick(args: dict[str, Any]) -> dict[str, Any]:
    return tick_with_phases(
        name=str(args.get("name") or "default"),
        trigger=str(args.get("trigger") or "manual-phased"),
    )


def _exec_sense_only(args: dict[str, Any]) -> dict[str, Any]:
    """Read-only: gather current signals without running reflection or action."""
    return {"status": "ok", "signals": sense_phase(name=str(args.get("name") or "default"))}


HEARTBEAT_PHASES_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "phased_heartbeat_tick",
            "description": (
                "Run a 3-phase heartbeat tick (Sense → Reflect → Act). "
                "Dispatches to existing tick when action warranted, runs "
                "productive idle work otherwise (consolidation, snapshots, "
                "surprise detection, pattern mining)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "trigger": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "heartbeat_sense",
            "description": "Read-only: gather current heartbeat signals without acting. Cheap.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": [],
            },
        },
    },
]
