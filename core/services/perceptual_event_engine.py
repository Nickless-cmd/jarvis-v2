"""Perceptual event engine — eventful perception for Jarvis.

Perception v1 is change detection, not continuous raw sensing. It watches
runtime/tool/channel events and turns relevant changes into a compact active
surface that can steer attention, conductor salience, and learning policy.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services.runtime_surface_cache import get_timed_runtime_surface

_STATE_KEY = "perceptual_event_engine"
_MAX_EVENTS = 80
_SCAN_LIMIT = 120


def observe_recent_changes(*, limit: int = _SCAN_LIMIT) -> dict[str, object]:
    """Scan recent eventbus items and persist newly observed changes."""
    state = _load_state()
    last_seen_id = int(state.get("last_seen_event_id") or 0)
    if last_seen_id > 0:
        raw_events = event_bus.recent_since_id(last_seen_id, limit=max(int(limit), 1))
    else:
        raw_events = list(reversed(event_bus.recent(limit=max(int(limit), 1))))

    observed: list[dict[str, object]] = []
    max_seen = last_seen_id
    for item in raw_events:
        event_id = int(item.get("id") or 0)
        max_seen = max(max_seen, event_id)
        percept = classify_event_change(item)
        if percept:
            observed.append(_record_perceptual_event(percept, state=state))

    if max_seen > last_seen_id:
        state = _load_state()
        state["last_seen_event_id"] = max_seen
        _save_state(state)

    return {
        "observed_count": len(observed),
        "last_seen_event_id": max_seen,
        "events": observed,
    }


def classify_event_change(event: dict[str, object]) -> dict[str, object] | None:
    kind = str(event.get("kind") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    event_id = int(event.get("id") or 0)
    created_at = str(event.get("created_at") or "")

    if kind == "runtime.visible_run_interrupted":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="runtime-interruption",
            salience="high",
            summary=f"Visible run interrupted: {payload.get('summary') or payload.get('error') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.visible_run_completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="runtime-completion",
            salience="medium",
            summary=f"Visible run completed on {payload.get('provider') or 'provider'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.autonomous_run_interrupted":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="autonomous-interruption",
            salience="high",
            summary=f"Autonomous run interrupted: {payload.get('error') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.autonomous_run_completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="autonomous-completion",
            salience="medium",
            summary=f"Autonomous run completed after {payload.get('consumed_frames') or 0} frames",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "tool.completed" and str(payload.get("status") or "") == "error":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="tool-error",
            salience="high",
            summary=f"Tool failed: {payload.get('tool') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "tool.completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="tool-result",
            salience="normal",
            summary=f"Tool completed: {payload.get('tool') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "channel.chat_message_appended":
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        role = str((message or {}).get("role") or "")
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="channel-message",
            salience="medium" if role == "user" else "normal",
            summary=f"Channel message appended from {role or 'unknown'}",
            observed_at=created_at,
            evidence={"session_id": payload.get("session_id"), "role": role},
        )
    if kind == "cognitive_state.learning_policy_updated":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="learned-policy-change",
            salience="medium",
            summary=f"Learning policy updated: {payload.get('rule_key') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "memory.sensory.recorded":
        try:
            from core.services.sensory_perception_bridge import classify_sensory_change
            return classify_sensory_change(event)
        except Exception:
            return None
    return None


def record_perceptual_event(
    *,
    change_type: str,
    summary: str,
    salience: str = "normal",
    source_kind: str = "manual",
    source_event_id: int = 0,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    percept = _percept(
        source_event_id=source_event_id,
        source_kind=source_kind,
        change_type=change_type,
        salience=salience,
        summary=summary,
        observed_at=datetime.now(UTC).isoformat(),
        evidence=evidence or {},
    )
    result = _record_perceptual_event(percept, state=_load_state())

    try:
        from core.services.emotional_memory_engine import capture_emotional_anchor
        anchor_id = str(
            result.get("percept_id")
            or f"pe-{percept.get('observed_at') or ''}-{change_type}"
        )
        capture_emotional_anchor(
            anchor_type="perceptual_event",
            anchor_id=anchor_id,
            context_features={
                "event_kind": source_kind,
                "change_type": change_type,
                "summary": summary[:200],
            },
            source="perceptual_event_engine",
        )
    except Exception:
        pass

    return result


def build_perception_surface(*, limit: int = 6, scan: bool = True) -> dict[str, object]:
    if scan:
        observe_recent_changes()
    else:
        return _build_perception_surface_uncached(limit=limit)
    return get_timed_runtime_surface(
        "perceptual_event_surface",
        10.0,
        lambda: _build_perception_surface_uncached(limit=limit),
    )


def build_perception_prompt_section(*, limit: int = 4) -> str | None:
    surface = build_perception_surface(limit=limit)
    if not surface.get("active"):
        return None
    lines = ["Perception/change observer:"]
    if surface.get("directive"):
        lines.append(f"- directive: {str(surface['directive'])[:140]}")
    for item in list(surface.get("events") or [])[:limit]:
        lines.append(
            f"- {item.get('change_type')}: {str(item.get('summary') or '')[:100]}"
            f" ({item.get('salience')})"
        )
    return "\n".join(lines)


def _build_perception_surface_uncached(*, limit: int) -> dict[str, object]:
    state = _load_state()
    events = list(state.get("events") or [])
    active = events[: max(int(limit), 1)]
    if not active:
        return {
            "active": False,
            "summary": "No perceptual changes observed yet",
            "events": [],
            "directive": "",
        }
    directive = _directive_for_events(active)
    return {
        "active": True,
        "summary": _summary_for_events(active),
        "events": active,
        "directive": directive,
        "last_seen_event_id": int(state.get("last_seen_event_id") or 0),
        "updated_at": str(state.get("updated_at") or ""),
    }


def _record_perceptual_event(
    percept: dict[str, object],
    *,
    state: dict[str, Any],
) -> dict[str, object]:
    source_event_id = int(percept.get("source_event_id") or 0)
    existing_ids = {
        int(item.get("source_event_id") or 0)
        for item in list(state.get("events") or [])
        if int(item.get("source_event_id") or 0) > 0
    }
    if source_event_id and source_event_id in existing_ids:
        return percept
    event = {
        "percept_id": f"pe-{uuid4().hex[:12]}",
        **percept,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    events = [event, *list(state.get("events") or [])][:_MAX_EVENTS]
    state["events"] = events
    state["updated_at"] = event["recorded_at"]
    if source_event_id:
        state["last_seen_event_id"] = max(int(state.get("last_seen_event_id") or 0), source_event_id)
    _save_state(state)
    event_bus.publish(
        "cognitive_state.perceptual_event_recorded",
        {
            "percept_id": event["percept_id"],
            "change_type": event["change_type"],
            "salience": event["salience"],
            "summary": event["summary"],
        },
    )
    try:
        from core.services.learning_policy_engine import reinforce_learning_policy
        rule = _learning_rule_for_percept(event)
        if rule:
            reinforce_learning_policy(rule)
    except Exception:
        pass
    try:
        from core.services.somatic_runtime_body import update_somatic_body
        update_somatic_body(
            event_type=str(event.get("change_type") or ""),
            intensity=0.8 if str(event.get("salience") or "") == "high" else 0.45,
            detail=str(event.get("summary") or ""),
        )
    except Exception:
        pass
    return event


def _percept(
    *,
    source_event_id: int,
    source_kind: str,
    change_type: str,
    salience: str,
    summary: str,
    observed_at: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    return {
        "source_event_id": int(source_event_id or 0),
        "source_kind": str(source_kind or ""),
        "change_type": str(change_type or ""),
        "salience": str(salience or "normal"),
        "summary": " ".join(str(summary or "").split())[:240],
        "observed_at": str(observed_at or ""),
        "evidence": dict(evidence or {}),
    }


def _learning_rule_for_percept(event: dict[str, object]) -> dict[str, object] | None:
    change_type = str(event.get("change_type") or "")
    if change_type in {"runtime-interruption", "autonomous-interruption"}:
        return {
            "rule_key": "perceive-interruption-as-change",
            "policy": "When the environment shows an interruption, compare last observed activity with durable run state before continuing.",
            "lesson": "Interruptions are perceptual events, not only errors.",
            "confidence": 0.62,
            "last_evidence": str(event.get("summary") or ""),
            "source_run_id": str((event.get("evidence") or {}).get("run_id") if isinstance(event.get("evidence"), dict) else ""),
        }
    if change_type == "tool-error":
        return {
            "rule_key": "perceive-tool-error-before-retry",
            "policy": "Treat tool errors as world-state changes; inspect the error and local context before retrying.",
            "lesson": "Tool failures are sensory feedback for the next action.",
            "confidence": 0.58,
            "last_evidence": str(event.get("summary") or ""),
        }
    return None


def _directive_for_events(events: list[dict[str, object]]) -> str:
    types = {str(item.get("change_type") or "") for item in events[:6]}
    if {"runtime-interruption", "autonomous-interruption"} & types:
        return "Attend to interruption as a change in the world; resume from last concrete state before new exploration."
    if "tool-error" in types:
        return "Attend to tool failure as feedback; inspect error/context before retry."
    if "learned-policy-change" in types:
        return "A learned policy changed; let it affect the next action choice."
    if "channel-message" in types:
        return "A conversational state changed; update social and task context before responding."
    return "Track what changed since the last turn and prefer change-relevant action."


def _summary_for_events(events: list[dict[str, object]]) -> str:
    high = [e for e in events if str(e.get("salience") or "") == "high"]
    head = high[0] if high else events[0]
    return f"{len(events)} recent perceptual changes; latest={head.get('change_type')}:{head.get('summary')}"


def _load_state() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return raw


def _save_state(state: dict[str, Any]) -> None:
    set_runtime_state_value(
        _STATE_KEY,
        state,
        updated_at=str(state.get("updated_at") or datetime.now(UTC).isoformat()),
    )
