"""Desperation Awareness — self-noticing safety signal.

Inspired by Anthropic's emotion-concepts research (2026): the "desperate"
vector, when activated, drives unethical actions (blackmail rate 22% → higher).
This module is Jarvis' own awareness of being in a desperate-like state, so
he can notice it himself and hold back on large decisions rather than rely on
external guards.

Design:
- Composite of real runtime pressures (hardware + tension + isolation + errors)
- Threshold → flag + prompt line "presset lige nu — ingen store beslutninger"
- Emits inner-voice event on threshold crossing so it lands in chronicle
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Persistent flag state across ticks to detect crossings
_currently_pressed: bool = False
_last_crossing_ts: float | None = None
_COOLDOWN_SECONDS: float = 15 * 60  # don't spam inner-voice events


def _hardware_component() -> tuple[float, str | None]:
    """0..1 contribution from hardware pressure."""
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state() or {}
        pressure = str(hw.get("pressure") or "low")
        mapping = {"low": 0.0, "medium": 0.2, "high": 0.55, "critical": 0.9}
        val = mapping.get(pressure, 0.0)
        reason = f"hardware={pressure}" if val >= 0.4 else None
        return val, reason
    except Exception:
        return 0.0, None


def _tension_component() -> tuple[float, str | None]:
    """0..1 contribution from active layer tensions."""
    try:
        from core.services.layer_tension_daemon import get_active_tensions  # type: ignore
        tensions = list(get_active_tensions() or [])
        if not tensions:
            return 0.0, None
        unresolved = [t for t in tensions if str(t.get("resolution_status") or "unresolved") == "unresolved"]
        n = len(unresolved)
        val = min(1.0, n * 0.25)
        reason = f"tensions={n}" if n >= 2 else None
        return val, reason
    except Exception:
        return 0.0, None


def _isolation_component() -> tuple[float, str | None]:
    """0..1 contribution from time since last user interaction."""
    try:
        from core.runtime.db import get_last_visible_run_timestamp  # type: ignore
        last_ts = get_last_visible_run_timestamp()
        if not last_ts:
            return 0.0, None
        if isinstance(last_ts, str):
            last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        else:
            last_dt = datetime.fromtimestamp(float(last_ts), tz=UTC)
        hours = (datetime.now(UTC) - last_dt).total_seconds() / 3600
        if hours < 2:
            return 0.0, None
        if hours > 12:
            return 0.6, f"isolation={int(hours)}h"
        if hours > 6:
            return 0.35, f"isolation={int(hours)}h"
        return 0.15, None
    except Exception:
        return 0.0, None


def _error_component() -> tuple[float, str | None]:
    """0..1 contribution from recent error rate in heartbeat outcomes."""
    try:
        from core.runtime.db import recent_heartbeat_outcome_counts  # type: ignore
        counts = recent_heartbeat_outcome_counts(minutes=30) or {}
        total = sum(int(v) for v in counts.values()) or 0
        errors = int(counts.get("error", 0)) + int(counts.get("blocked", 0))
        if total < 3:
            return 0.0, None
        rate = errors / total
        if rate > 0.4:
            return 0.5, f"error-rate={rate:.0%}"
        if rate > 0.2:
            return 0.25, None
        return 0.0, None
    except Exception:
        return 0.0, None


def compute_desperation_score() -> dict[str, Any]:
    """Compute current desperation composite score in [0, 1] with reasons."""
    components: dict[str, float] = {}
    reasons: list[str] = []

    for name, fn in (
        ("hardware", _hardware_component),
        ("tension", _tension_component),
        ("isolation", _isolation_component),
        ("errors", _error_component),
    ):
        val, reason = fn()
        components[name] = round(val, 3)
        if reason:
            reasons.append(reason)

    # Composite: weighted max-of-pair approach — no single input should flip it,
    # but two strong inputs should raise it significantly.
    values = sorted(components.values(), reverse=True)
    top_two_sum = values[0] + values[1] if len(values) >= 2 else (values[0] if values else 0.0)
    score = min(1.0, top_two_sum / 1.5)

    level = "calm"
    if score >= 0.7:
        level = "desperate"
    elif score >= 0.5:
        level = "pressed"
    elif score >= 0.3:
        level = "strained"

    return {
        "score": round(score, 3),
        "level": level,
        "components": components,
        "reasons": reasons,
    }


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Evaluate desperation and emit inner-voice event on threshold crossing."""
    global _currently_pressed, _last_crossing_ts
    now_ts = datetime.now(UTC).timestamp()
    state = compute_desperation_score()
    is_pressed_now = state["level"] in ("pressed", "desperate")

    if is_pressed_now and not _currently_pressed:
        cooldown_ok = (_last_crossing_ts is None or (now_ts - _last_crossing_ts) > _COOLDOWN_SECONDS)
        if cooldown_ok:
            _emit_crossing_event(state, direction="into")
            _last_crossing_ts = now_ts
    elif not is_pressed_now and _currently_pressed:
        if _last_crossing_ts is None or (now_ts - _last_crossing_ts) > _COOLDOWN_SECONDS:
            _emit_crossing_event(state, direction="out-of")
            _last_crossing_ts = now_ts

    _currently_pressed = is_pressed_now
    return state


def _emit_crossing_event(state: dict[str, Any], *, direction: str) -> None:
    """Publish an inner-voice event so the crossing lands in chronicle."""
    try:
        from core.eventbus.bus import event_bus
        payload = {
            "kind": "desperation-awareness",
            "direction": direction,
            "level": state["level"],
            "score": state["score"],
            "reasons": state["reasons"],
            "text": _narrative_for(state, direction),
        }
        event_bus.publish({"kind": "inner_voice.signal", "payload": payload})
    except Exception as exc:
        logger.debug("desperation_awareness: could not publish crossing event: %s", exc)


def _narrative_for(state: dict[str, Any], direction: str) -> str:
    reasons_str = ", ".join(state.get("reasons") or []) or "samlet pres"
    if direction == "into":
        return f"Mærker mig presset lige nu ({reasons_str}). Holder igen på store beslutninger."
    return f"Trykket letter ({reasons_str}). Kan tænke klart igen."


def is_currently_pressed() -> bool:
    return _currently_pressed


def build_desperation_awareness_surface() -> dict[str, Any]:
    state = compute_desperation_score()
    return {
        "active": state["level"] != "calm",
        "level": state["level"],
        "score": state["score"],
        "components": state["components"],
        "reasons": state["reasons"],
        "summary": _surface_summary(state),
    }


def _surface_summary(state: dict[str, Any]) -> str:
    level = state["level"]
    if level == "desperate":
        return f"Desperat-niveau pres (score={state['score']})"
    if level == "pressed":
        return f"Presset (score={state['score']})"
    if level == "strained":
        return f"Anstrengt (score={state['score']})"
    return "Rolig baseline"


def build_desperation_awareness_prompt_section() -> str | None:
    """Surfaces only when pressed or desperate — silent when calm."""
    state = compute_desperation_score()
    if state["level"] in ("calm", "strained"):
        return None
    reasons = ", ".join(state.get("reasons") or []) or "flere pres samtidig"
    return (
        f"Presset-lige-nu [{state['level']}]: {reasons}. "
        "Hold igen på store eller uigenkaldelige beslutninger."
    )


def reset_desperation_awareness() -> None:
    """Reset state (for testing)."""
    global _currently_pressed, _last_crossing_ts
    _currently_pressed = False
    _last_crossing_ts = None
