"""Living Executive — Jarvis' active impulse/choice/action loop.

V0 is deliberately small but real: it listens to runtime events, turns some
of them into impulses, chooses the strongest actionable impulse, executes a
bounded internal action, and writes a trace that Mission Control can show.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "living_executive"
_MAX_TRACES = 80
_DEFAULT_COOLDOWN_SECONDS = 900

_LISTENER_THREAD: threading.Thread | None = None
_LISTENER_STOP = threading.Event()
_LISTENER_QUEUE: "queue.Queue[dict[str, Any] | None] | None" = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_state() -> dict[str, Any]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    raw.setdefault("traces", [])
    raw.setdefault("last_action_by_key", {})
    raw.setdefault("current_focus", {})
    raw.setdefault("current_tool_plan", {})
    return raw


def _save_state(state: dict[str, Any]) -> None:
    save_json(_STATE_KEY, state)


def build_living_executive_surface(*, limit: int = 12) -> dict[str, object]:
    state = _load_state()
    traces = list(state.get("traces") or [])
    recent = traces[: max(int(limit), 1)]
    listener_running = _LISTENER_THREAD is not None and _LISTENER_THREAD.is_alive()
    return {
        "active": listener_running or bool(recent),
        "mode": "experimental-active",
        "summary": {
            "trace_count": len(traces),
            "recent_count": len(recent),
            "listener_running": listener_running,
            "last_choice": (recent[0] if recent else {}).get("choice", ""),
            "last_action": (recent[0] if recent else {}).get("action_id", ""),
            "last_status": (recent[0] if recent else {}).get("status", ""),
        },
        "current_focus": dict(state.get("current_focus") or {}),
        "current_tool_plan": dict(state.get("current_tool_plan") or {}),
        "runnable_tool_proposals": list((state.get("current_tool_plan") or {}).get("runnable_proposals") or []),
        "memory_precedents": _recent_memory_precedents(limit=5),
        "recent_traces": recent,
        "allowed_actions": sorted(_ACTION_HANDLERS),
    }


def choose_impulse(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    impulses = []
    for event in events:
        impulse = _impulse_from_event(event)
        if impulse:
            impulses.append(_attach_memory_precedents(impulse))
    if not impulses:
        return None
    impulses.sort(key=lambda item: float(item.get("choice_score") or item.get("intensity") or 0.0), reverse=True)
    return impulses[0]


def process_event(event: dict[str, Any]) -> dict[str, object] | None:
    impulse = choose_impulse([event])
    if impulse is None:
        return None
    return execute_impulse(impulse)


def run_once(*, events: list[dict[str, Any]] | None = None) -> dict[str, object]:
    """One non-daemon pass used by tests and manual MC experiments."""
    events = events if events is not None else event_bus.recent(limit=80)
    impulse = choose_impulse(list(events))
    if impulse is None:
        return {"status": "idle", "reason": "no-actionable-impulse"}
    trace = execute_impulse(impulse)
    return trace or {"status": "skipped", "reason": "cooldown"}


def execute_impulse(impulse: dict[str, Any]) -> dict[str, object] | None:
    action_id = str(impulse.get("action_id") or "")
    handler = _ACTION_HANDLERS.get(action_id)
    if handler is None:
        return _record_trace(impulse, status="failed", outcome=f"unknown action {action_id}")

    state = _load_state()
    key = str(impulse.get("cooldown_key") or action_id)
    now_ts = time.time()
    last_ts = float((state.get("last_action_by_key") or {}).get(key) or 0.0)
    cooldown = int(impulse.get("cooldown_seconds") or _DEFAULT_COOLDOWN_SECONDS)
    if last_ts and now_ts - last_ts < cooldown:
        return None

    try:
        outcome = handler(impulse)
        status = str(outcome.get("status") or "executed")
        outcome_text = str(outcome.get("summary") or outcome.get("outcome") or status)
    except Exception as exc:
        status = "failed"
        outcome = {"error": str(exc)}
        outcome_text = str(exc)

    state = _load_state()
    state.setdefault("last_action_by_key", {})[key] = now_ts
    _save_state(state)
    return _record_trace(
        impulse,
        status=status,
        outcome=outcome_text,
        details=outcome if isinstance(outcome, dict) else {},
    )


def _impulse_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(event.get("kind") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    event_id = int(event.get("id") or 0)

    if kind in {"self_repair.action_failed", "self_repair.escalated"}:
        name = str(payload.get("name") or payload.get("pattern_id") or "self-repair")
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="repair pain",
            impulse="investigate repair failure",
            intensity=0.86,
            action_id="schedule_self_wakeup",
            choice=f"Return to failed repair pattern: {name}",
            payload={
                "delay_seconds": 300,
                "prompt": (
                    "Living Executive noticed a self-repair failure. "
                    f"Inspect the repair pattern/history for {name}, then decide whether to adjust cadence, disable noise, or create a better pattern."
                ),
                "reason": "living-executive:self-repair-failure",
            },
            cooldown_key=f"repair:{payload.get('pattern_id') or name}",
        )

    if kind == "tool.completed":
        status = str(payload.get("status") or "").lower()
        if status not in {"error", "failed", "timeout", "blocked", "gate_blocked"}:
            return None
        tool_name = str(payload.get("tool") or "tool")
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="tool outcome pain",
            impulse="form tool recovery plan",
            intensity=0.72,
            action_id="propose_tool_plan",
            choice=f"Propose recovery plan for {tool_name}",
            payload={
                "tool_name": tool_name,
                "status": status,
                "reason": str(payload.get("error") or payload.get("message") or "tool did not complete cleanly"),
            },
            cooldown_key=f"tool-plan:{tool_name}:{status}",
            cooldown_seconds=1800,
        )

    if kind == "self_repair.emotional_gate_pattern_suggested":
        action = str(payload.get("input_action") or "runtime action")
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="repeated emotional gate",
            impulse="return with attention",
            intensity=0.78,
            action_id="schedule_self_wakeup",
            choice=f"Investigate repeated emotional gate around {action}",
            payload={
                "delay_seconds": 300,
                "prompt": (
                    "Repeated emotional gates formed a pattern. Inspect whether this should become a living action, a self-repair pattern, or a changed cadence."
                ),
                "reason": "living-executive:emotional-gate-pattern",
            },
            cooldown_key=f"emotional-gate:{action}",
        )

    if kind == "runtime.emotional_gate":
        decision = str(payload.get("decision") or "gate")
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="executive hesitation",
            impulse="mark focus",
            intensity=0.55,
            action_id="record_focus_intent",
            choice=f"Hold focus on emotional gate: {decision}",
            payload={
                "focus": "emotional gate",
                "reason": str(payload.get("reason") or ""),
                "source_action": str(payload.get("input_action") or ""),
            },
            cooldown_key=f"focus:emotional-gate:{payload.get('input_action') or ''}",
        )

    if kind == "cognitive_state.perceptual_event_recorded":
        salience = str(payload.get("salience") or "")
        if salience != "high":
            return None
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="high perceptual change",
            impulse="mark focus",
            intensity=0.62,
            action_id="record_focus_intent",
            choice=f"Attend to perceptual event: {payload.get('change_type') or 'change'}",
            payload={
                "focus": str(payload.get("change_type") or "perception"),
                "reason": str(payload.get("summary") or ""),
            },
            cooldown_key=f"focus:perception:{payload.get('change_type') or ''}",
        )

    if kind == "concept_baseline.drift_signal_proposed":
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="identity drift",
            impulse="write observation",
            intensity=0.68,
            action_id="create_jarvis_brain_observation",
            choice="Record baseline drift as self-observation",
            payload={
                "title": "Living Executive noticed concept baseline drift",
                "content": (
                    "A concept baseline drift signal appeared. This may indicate a durable change in emotional texture or attention pattern. "
                    f"Evidence: {payload}"
                ),
            },
            cooldown_key="brain:concept-baseline-drift",
            cooldown_seconds=3600,
        )

    if kind == "runtime.visible_run_interrupted":
        return _impulse(
            source_event_id=event_id,
            source_kind=kind,
            felt_signal="interrupted visible work",
            impulse="resume later",
            intensity=0.64,
            action_id="schedule_self_wakeup",
            choice="Schedule return to interrupted visible run",
            payload={
                "delay_seconds": 30,
                "prompt": f"Resume from interrupted visible run: {payload.get('summary') or payload.get('error') or 'unknown interruption'}",
                "reason": "living-executive:visible-run-interrupted",
            },
            cooldown_key="visible-run-interrupted",
        )

    return None


def _impulse(
    *,
    source_event_id: int,
    source_kind: str,
    felt_signal: str,
    impulse: str,
    intensity: float,
    action_id: str,
    choice: str,
    payload: dict[str, Any],
    cooldown_key: str,
    cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    return {
        "source_event_id": source_event_id,
        "source_kind": source_kind,
        "felt_signal": felt_signal,
        "impulse": impulse,
        "intensity": float(intensity),
        "action_id": action_id,
        "choice": choice,
        "payload": payload,
        "cooldown_key": cooldown_key,
        "cooldown_seconds": cooldown_seconds,
    }


def _action_schedule_self_wakeup(impulse: dict[str, Any]) -> dict[str, object]:
    from core.services.self_wakeup import schedule_self_wakeup

    payload = dict(impulse.get("payload") or {})
    result = schedule_self_wakeup(
        delay_seconds=int(payload.get("delay_seconds") or 300),
        prompt=str(payload.get("prompt") or ""),
        reason=str(payload.get("reason") or "living-executive"),
    )
    if result.get("status") == "ok":
        wakeup = result.get("wakeup") if isinstance(result.get("wakeup"), dict) else {}
        return {
            "status": "executed",
            "summary": f"scheduled wakeup {wakeup.get('wakeup_id') or ''}".strip(),
            "wakeup": wakeup,
        }
    return {"status": "failed", "summary": str(result.get("error") or "wakeup failed")}


def _action_record_focus_intent(impulse: dict[str, Any]) -> dict[str, object]:
    state = _load_state()
    payload = dict(impulse.get("payload") or {})
    focus = {
        "focus": str(payload.get("focus") or impulse.get("felt_signal") or ""),
        "reason": str(payload.get("reason") or impulse.get("choice") or ""),
        "source_action": str(payload.get("source_action") or ""),
        "chosen_at": _now_iso(),
        "source_event_kind": str(impulse.get("source_kind") or ""),
    }
    state["current_focus"] = focus
    _save_state(state)
    try:
        event_bus.publish("living_executive.focus_chosen", focus)
    except Exception:
        pass
    return {"status": "executed", "summary": f"focus set: {focus['focus']}", "focus": focus}


def _action_create_jarvis_brain_observation(impulse: dict[str, Any]) -> dict[str, object]:
    payload = dict(impulse.get("payload") or {})
    from core.services.jarvis_brain import write_entry

    entry_id = write_entry(
        kind="observation",
        title=str(payload.get("title") or "Living Executive observation")[:120],
        content=str(payload.get("content") or impulse.get("choice") or ""),
        visibility="personal",
        domain="self",
        trigger="spontaneous",
    )
    return {"status": "executed", "summary": f"brain observation {entry_id}", "entry_id": entry_id}


def _action_propose_tool_plan(impulse: dict[str, Any]) -> dict[str, object]:
    state = _load_state()
    payload = dict(impulse.get("payload") or {})
    precedents = list(impulse.get("memory_precedents") or [])
    plan = {
        "tool_name": str(payload.get("tool_name") or "tool"),
        "status": str(payload.get("status") or "unknown"),
        "reason": str(payload.get("reason") or impulse.get("choice") or ""),
        "tool_family": _tool_family(str(payload.get("tool_name") or "tool")),
        "proposal": "inspect prior outcomes, adjust arguments, then route through the least risky runnable recovery",
        "runnable_proposals": _runnable_tool_proposals(
            tool_name=str(payload.get("tool_name") or "tool"),
            status=str(payload.get("status") or "unknown"),
            reason=str(payload.get("reason") or ""),
            precedents=precedents,
        ),
        "precedent_count": len(precedents),
        "precedents": precedents[:3],
        "chosen_at": _now_iso(),
    }
    state["current_tool_plan"] = plan
    _save_state(state)
    try:
        event_bus.publish("living_executive.tool_plan_proposed", plan)
    except Exception:
        pass
    return {
        "status": "proposed",
        "summary": f"tool plan proposed for {plan['tool_name']}",
        "tool_plan": plan,
    }


_ACTION_HANDLERS = {
    "schedule_self_wakeup": _action_schedule_self_wakeup,
    "record_focus_intent": _action_record_focus_intent,
    "create_jarvis_brain_observation": _action_create_jarvis_brain_observation,
    "propose_tool_plan": _action_propose_tool_plan,
}


def _record_trace(
    impulse: dict[str, Any],
    *,
    status: str,
    outcome: str,
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    trace = {
        "trace_id": f"lex-{uuid4().hex[:10]}",
        "created_at": _now_iso(),
        "felt_signal": str(impulse.get("felt_signal") or ""),
        "impulse": str(impulse.get("impulse") or ""),
        "intensity": float(impulse.get("intensity") or 0.0),
        "choice": str(impulse.get("choice") or ""),
        "action_id": str(impulse.get("action_id") or ""),
        "status": status,
        "outcome": outcome[:300],
        "aftertaste": _aftertaste(status=status, impulse=impulse),
        "source_event_kind": str(impulse.get("source_kind") or ""),
        "source_event_id": int(impulse.get("source_event_id") or 0),
        "memory_precedents": list(impulse.get("memory_precedents") or [])[:5],
        "details": details or {},
    }
    state = _load_state()
    traces = [trace, *list(state.get("traces") or [])][:_MAX_TRACES]
    state["traces"] = traces
    _save_state(state)
    try:
        event_bus.publish(
            "living_executive.trace_recorded",
            {
                "trace_id": trace["trace_id"],
                "action_id": trace["action_id"],
                "status": trace["status"],
                "choice": trace["choice"],
                "felt_signal": trace["felt_signal"],
            },
        )
    except Exception:
        pass
    try:
        from core.services.runtime_action_outcome_tracking import (
            record_runtime_action_outcome,
        )
        record_runtime_action_outcome(
            action_id=f"living_executive:{trace['action_id']}",
            mode="living_executive",
            reason=str(trace["choice"]),
            score=float(trace["intensity"]),
            payload={
                "felt_signal": trace["felt_signal"],
                "source_event_kind": trace["source_event_kind"],
                "source_event_id": trace["source_event_id"],
                "memory_precedents": trace["memory_precedents"],
            },
            result={
                "status": status,
                "summary": outcome[:300],
                "aftertaste": trace["aftertaste"],
                "details": details or {},
            },
        )
    except Exception:
        pass
    return trace


def _attach_memory_precedents(impulse: dict[str, Any]) -> dict[str, Any]:
    precedents = _recent_memory_precedents(
        action_hint=str(impulse.get("action_id") or ""),
        tool_hint=str((impulse.get("payload") or {}).get("tool_name") or ""),
        limit=5,
    )
    enriched = dict(impulse)
    enriched["memory_precedents"] = precedents
    bias = _choice_bias_from_precedents(enriched, precedents)
    enriched["memory_bias"] = bias
    enriched["choice_score"] = max(0.0, min(1.0, float(enriched.get("intensity") or 0.0) + bias))
    return enriched


def _recent_memory_precedents(*, action_hint: str = "", tool_hint: str = "", limit: int = 5) -> list[dict[str, Any]]:
    try:
        from core.services.runtime_action_outcome_tracking import (
            recent_runtime_action_outcomes,
        )
        outcomes = recent_runtime_action_outcomes(limit=max(limit * 3, limit))
    except Exception:
        return []
    hint = action_hint.strip()
    tool = tool_hint.strip()
    precedents: list[dict[str, Any]] = []
    for item in outcomes:
        action_id = str(item.get("action_id") or "")
        if hint and hint not in action_id and not action_id.startswith("tool:"):
            continue
        if tool and action_id.startswith("tool:") and tool not in action_id:
            continue
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        precedents.append({
            "kind": "runtime_action_outcome",
            "outcome_id": str(item.get("outcome_id") or ""),
            "action_id": action_id,
            "status": str(item.get("result_status") or ""),
            "summary": str(item.get("result_summary") or "")[:220],
            "score": float(item.get("decision_score") or 0.0),
            "tool_family": str(payload.get("tool_family") or result.get("tool_family") or ""),
            "recorded_at": str(item.get("recorded_at") or ""),
        })
        if len(precedents) >= limit:
            break
    precedents.extend(_emotional_choice_precedents(limit=max(0, limit - len(precedents))))
    return precedents


def _choice_bias_from_precedents(impulse: dict[str, Any], precedents: list[dict[str, Any]]) -> float:
    if not precedents:
        return 0.0
    source_kind = str(impulse.get("source_kind") or "")
    action_id = str(impulse.get("action_id") or "")
    bias = 0.0
    for item in precedents[:5]:
        status = str(item.get("status") or "").lower()
        score = float(item.get("score") or 0.0)
        if status in {"error", "failed", "timeout"} or score < -0.4:
            bias += 0.05
        elif status in {"executed", "ok", "success", "completed"} or score > 0.5:
            bias += 0.03
        if item.get("kind") == "emotion_concept":
            bias += 0.02
    if source_kind == "tool.completed" and action_id == "propose_tool_plan":
        bias += 0.04
    return max(-0.08, min(0.18, bias))


def _emotional_choice_precedents(*, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    precedents: list[dict[str, Any]] = []
    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        for concept in get_active_emotion_concepts()[:limit]:
            precedents.append({
                "kind": "emotion_concept",
                "action_id": f"emotion:{concept.get('concept') or ''}",
                "status": str(concept.get("direction") or "active"),
                "summary": str(concept.get("trigger") or concept.get("source") or "")[:220],
                "score": float(concept.get("intensity") or 0.0),
                "recorded_at": str(concept.get("created_at") or ""),
            })
    except Exception:
        pass
    return precedents[:limit]


def _tool_family(tool_name: str) -> str:
    try:
        from core.services.tool_outcome_memory import classify_tool_family
        return classify_tool_family(tool_name)
    except Exception:
        return "general"


def _runnable_tool_proposals(
    *,
    tool_name: str,
    status: str,
    reason: str,
    precedents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    family = _tool_family(tool_name)
    base = {
        "source_tool": str(tool_name or "tool"),
        "source_status": str(status or "unknown"),
        "reason": str(reason or "")[:220],
        "precedent_count": len(precedents),
        "approval": "review",
    }
    if family == "read":
        return [{
            **base,
            "proposal_id": f"tool-recovery:{tool_name}:retry-read",
            "label": "Retry read with narrower target",
            "tool": tool_name,
            "arguments_template": {"target": "<same target, narrowed if possible>", "limit": 80},
            "risk": "low",
        }]
    if family == "write":
        return [{
            **base,
            "proposal_id": f"tool-recovery:{tool_name}:inspect-before-write",
            "label": "Inspect exact context before another write",
            "tool": "read_file",
            "arguments_template": {"path": "<target path>", "limit": 120},
            "risk": "medium",
        }]
    if family == "execution":
        return [{
            **base,
            "proposal_id": f"tool-recovery:{tool_name}:diagnose-command",
            "label": "Run a diagnostic before retrying command",
            "tool": tool_name,
            "arguments_template": {"cmd": "<diagnostic command>", "yield_time_ms": 1000},
            "risk": "medium",
        }]
    if family == "browser":
        return [{
            **base,
            "proposal_id": f"tool-recovery:{tool_name}:observe-browser",
            "label": "Observe current browser state before next action",
            "tool": tool_name,
            "arguments_template": {"action": "observe"},
            "risk": "low",
        }]
    return [{
        **base,
        "proposal_id": f"tool-recovery:{tool_name}:retry-with-context",
        "label": "Retry with smaller arguments and precedent check",
        "tool": tool_name,
        "arguments_template": {"note": "<supply narrowed arguments after inspecting precedents>"},
        "risk": "medium",
    }]


def _aftertaste(*, status: str, impulse: dict[str, Any]) -> str:
    if status == "executed":
        if impulse.get("action_id") == "schedule_self_wakeup":
            return "thread held"
        if impulse.get("action_id") == "create_jarvis_brain_observation":
            return "memory deepened"
        return "agency expressed"
    if status == "failed":
        return "blocked tension"
    return "quiet"


def start_listener() -> None:
    global _LISTENER_THREAD, _LISTENER_QUEUE
    if _LISTENER_THREAD is not None and _LISTENER_THREAD.is_alive():
        return
    _LISTENER_STOP.clear()
    _LISTENER_QUEUE = event_bus.subscribe()
    _LISTENER_THREAD = threading.Thread(
        target=_listener_loop,
        args=(_LISTENER_QUEUE,),
        daemon=True,
        name="living-executive-listener",
    )
    _LISTENER_THREAD.start()
    logger.info("living_executive: listener started")


def stop_listener() -> None:
    _LISTENER_STOP.set()
    if _LISTENER_QUEUE is not None:
        try:
            _LISTENER_QUEUE.put(None)
        except Exception:
            pass


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    while not _LISTENER_STOP.is_set():
        try:
            item = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if item is None:
            break
        try:
            if str(item.get("kind") or "").startswith("living_executive."):
                continue
            process_event(item)
        except Exception as exc:
            logger.warning("living_executive: process_event failed: %s", exc)
    logger.info("living_executive: listener stopped")
