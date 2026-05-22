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


def _user_active_recently(*, window_minutes: int = 10) -> bool:
    """Cheap check: has any user-role chat message landed in the last N minutes?

    Defensive copy of heartbeat_runtime._user_recently_active that doesn't
    require an import from the heavy module. Returns False on any error
    (fail-open — we'd rather burn the dispatch than skip a needed tick).
    """
    try:
        from core.runtime.db import connect
        cutoff = (datetime.now(UTC) - timedelta(minutes=max(1, int(window_minutes)))).isoformat()
        with connect() as c:
            row = c.execute(
                """SELECT 1 FROM chat_messages
                   WHERE role = 'user' AND created_at >= ?
                   LIMIT 1""",
                (cutoff,),
            ).fetchone()
        return row is not None
    except Exception:
        return False


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

    # Learning pipeline loop closure — route outputs between learning systems
    try:
        from core.services.learning_pipeline_orchestrator import run_reflect_cycle
        pipeline_result = run_reflect_cycle()
        if pipeline_result.get("status") == "completed" and pipeline_result.get("actions_taken", 0) > 0:
            reflection["learning_pipeline"] = {
                "actions_taken": pipeline_result["actions_taken"],
                "generalizations_created": pipeline_result.get("generalizations_created", 0),
                "reasoning_captured": pipeline_result.get("reasoning_captured", 0),
                "policies_routed": pipeline_result.get("policies_routed", 0),
            }
    except Exception as exc:
        logger.debug("reflect_phase: learning pipeline failed: %s", exc)
    # Recall-before-act: pull warm-tier + (optional cold) memories tied to
    # current priorities. Cheap when priorities empty; meaningful otherwise.
    try:
        from core.services.memory_hierarchy import recall_before_act
        # Build a query from active goals + priorities for targeted recall
        query_parts: list[str] = []
        for g in (signals.get("active_goals") or [])[:2]:
            if g.get("title"):
                query_parts.append(str(g.get("title")))
        query_parts.extend(priorities[:2])
        query = " ".join(query_parts)[:200]
        if query.strip():
            reflection["memory_recall"] = recall_before_act(
                query=query,
                include_cold=bool(priorities),  # only spend on cold if action warranted
                cold_max=4,
            )
    except Exception:
        pass
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

    # 5. Memory consolidation — Phase 2: idle-tick is good time to merge dupes
    if _budget_left():
        try:
            from core.services.memory_search import invalidate_index
            # Cheap: invalidate stale embedding cache so next search rebuilds fresh
            invalidate_index()
            actions.append("memory_index_invalidated")
        except Exception:
            pass

    # 6. Idle recovery — fatigue drains faster during real idle than passive decay alone.
    # Models physical "rest is restorative" — sitting still with the system actively
    # signaling rest mode IS recovery, not just absence of work.
    if _budget_left():
        try:
            from core.runtime.db import (
                get_latest_cognitive_personality_vector,
                upsert_cognitive_personality_vector,
            )
            import json as _json
            pv = get_latest_cognitive_personality_vector() or {}
            eb_raw = pv.get("emotional_baseline") or "{}"
            eb = _json.loads(str(eb_raw)) if isinstance(eb_raw, str) else eb_raw
            cur_fatigue = float(eb.get("fatigue", 0.0))
            if cur_fatigue > 0.3:
                # Stronger decay: 8% per idle tick (vs 3% from passive decay)
                eb["fatigue"] = max(0.0, cur_fatigue * 0.92)
                upsert_cognitive_personality_vector(
                    confidence_by_domain=str(pv.get("confidence_by_domain", "{}")),
                    communication_style=str(pv.get("communication_style", "{}")),
                    learned_preferences=str(pv.get("learned_preferences", "[]")),
                    recurring_mistakes=str(pv.get("recurring_mistakes", "[]")),
                    strengths_discovered=str(pv.get("strengths_discovered", "[]")),
                    current_bearing=str(pv.get("current_bearing", "")),
                    emotional_baseline=_json.dumps(eb, ensure_ascii=False),
                )
                actions.append(f"idle_recovery:fatigue {cur_fatigue:.2f}→{eb['fatigue']:.2f}")
        except Exception:
            pass

    # 7. Baseline rhythms (2026-05-22 fix): jobs that previously lived in
    # run_heartbeat_tick but were orphaned when scheduler started routing
    # through tick_with_phases (commit a3bfb0f6). These are LLM-free, very
    # cheap, and are critical for cross-session baseline data (most notably
    # the interlanguage practice cohort used in Phase 2 validation).
    #
    # Each job is self-gating (debounce / time-window inside its own logic)
    # so calling it on every idle tick is safe — it no-ops when not due.

    # 7a. Interlanguage practice — 30-min DB-gated (mirrors
    # heartbeat_runtime.py:1443 logic exactly).
    if _budget_left():
        try:
            import sqlite3 as _sql
            from pathlib import Path as _Path
            _practice_db = str(_Path.home() / ".jarvis-v2" / "state" / "jarvis.db")
            with _sql.connect(_practice_db) as _conn:
                _row = _conn.execute(
                    "SELECT MAX(created_at) FROM interlanguage_practice "
                    "WHERE peer_id = 'jarvis'"
                ).fetchone()
            _last_iso = _row[0] if _row else None
            _should_fire = False
            if _last_iso is None:
                _should_fire = True
            else:
                _last_dt = datetime.fromisoformat(_last_iso)
                if (datetime.now(UTC) - _last_dt).total_seconds() >= 1800:
                    _should_fire = True
            if _should_fire:
                from core.services.interlanguage_practice import practice_tick
                practice_tick(tick_id="productive_idle")
                actions.append("interlanguage_practice")
        except Exception:
            pass

    # 7b. Personality drift tick — has its own internal 30-min debounce.
    if _budget_left():
        try:
            from core.services.personality_vector import tick_personality_drift
            tick_personality_drift()
            actions.append("personality_drift_tick")
        except Exception:
            pass

    # 7c. Life services — dreams, wants, boredom, tick-elapsed. Each
    # one accepts a duration kwarg and decays/accumulates accordingly.
    # Use idle elapsed (capped at 60s for sanity) rather than fixed 30s
    # so the system reflects actual idle time, not assumed cadence.
    if _budget_left():
        _idle_dur = min(time.time() - started, 60.0)
        for _fn_path, _label in (
            ("core.services.continuity_kernel.record_tick_elapsed", "tick_elapsed"),
            ("core.services.dream_continuum.evolve_dreams", "dreams"),
            ("core.services.initiative_accumulator.accumulate_wants", "wants"),
            ("core.services.boredom_curiosity_bridge.add_boredom", "boredom"),
        ):
            try:
                _mod_path, _fn_name = _fn_path.rsplit(".", 1)
                _mod = __import__(_mod_path, fromlist=[_fn_name])
                _fn = getattr(_mod, _fn_name)
                # record_tick_elapsed uses seconds=, others use duration=timedelta
                if _label == "tick_elapsed":
                    _fn(seconds=_idle_dur)
                else:
                    _fn(duration=timedelta(seconds=_idle_dur))
                actions.append(_label)
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

    if priorities:
        # 2026-05-22 (Claude): early active-chat gate check.
        # The dispatched run_heartbeat_tick runs 30+ inline daemons with
        # per-daemon deadlines totalling 90-150s wall time. If we already
        # know Bjørn is chatting (active in last ~10 min), the gate
        # WILL block the outbound action anyway — but we'd have burned
        # 140s of CPU first. Short-circuit: skip the heavy dispatch,
        # go straight to productive_idle (0.13s) so baseline rhythms
        # still fire without wasted work.
        if _user_active_recently(window_minutes=10):
            logger.info(
                "act_phase: skipping dispatch — user active in last 10min "
                "(would be blocked by active-chat-gate anyway)"
            )
            idle_result = productive_idle()
            return {
                "kind": "skipped_for_active_chat",
                "trigger": trigger,
                "had_priorities": bool(priorities),
                "idle_result": idle_result,
            }

        # Action warranted — dispatch to existing tick
        try:
            from core.services.heartbeat_runtime import run_heartbeat_tick
            tick_result = run_heartbeat_tick(name=name, trigger=trigger)
            tick_status = (
                getattr(tick_result, "status", "unknown") if tick_result else "none"
            )
            # If the dispatched tick was blocked (e.g. the active-chat-gate
            # fired because user became active mid-dispatch), still run
            # productive_idle so baseline rhythms keep firing.
            if tick_status == "blocked":
                idle_result = productive_idle()
                return {
                    "kind": "tick_blocked_then_idle",
                    "trigger": trigger,
                    "had_priorities": bool(priorities),
                    "tick_status": tick_status,
                    "idle_result": idle_result,
                }
            return {
                "kind": "tick_dispatched",
                "trigger": trigger,
                "had_priorities": bool(priorities),
                "tick_status": tick_status,
            }
        except Exception as exc:
            logger.warning("act_phase: tick dispatch failed: %s", exc)
            return {"kind": "tick_failed", "error": str(exc)}

    # No clear priorities — productive idle.
    # IMPORTANT: Even when activity == "high" (e.g. during a chat session),
    # we do NOT dispatch to run_heartbeat_tick here. That call would
    # try to acquire _HEARTBEAT_TICK_LOCK and almost certainly fail,
    # producing a <100ms "tick_dispatched" with score=20.
    # Without priorities there's nothing urgent to act on — productive
    # idle is strictly more useful.
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
    # Phase 5: self-evaluate this tick's quality (observation only, no mutation)
    try:
        from core.services.agent_self_evaluation import evaluate_tick_quality
        evaluation = evaluate_tick_quality(tick_result=result)
        result["evaluation"] = evaluation
    except Exception:
        pass
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "heartbeat.phased_tick",
            {
                "activity_level": reflection.get("activity_level"),
                "priorities": reflection.get("priorities"),
                "act_kind": action.get("kind"),
                "elapsed_ms": elapsed_ms,
                "quality_score": (result.get("evaluation") or {}).get("score"),
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
