"""Somatic runtime body: turn runtime signals into bodily regulation cues."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "somatic_runtime_body"


def update_somatic_body(
    *,
    event_type: str,
    intensity: float = 0.5,
    detail: str = "",
) -> dict[str, object]:
    state = build_somatic_body_surface()
    levels = dict(state.get("levels") or _base_levels())
    event = str(event_type or "")
    delta = max(0.0, min(float(intensity), 1.0)) * 0.25
    if event in {"runtime-interruption", "autonomous-interruption"}:
        levels["startle"] += delta + 0.25
        levels["pressure"] += delta
    elif event == "tool-error":
        levels["frustration"] += delta
        levels["pressure"] += delta / 2
    elif event in {"runtime-completion", "autonomous-completion"}:
        levels["relief"] += delta + 0.1
        levels["pressure"] -= delta / 2
    elif event == "long-latency":
        levels["fatigue"] += delta
        levels["pressure"] += delta / 2
    levels = {k: round(max(0.0, min(v, 1.0)), 3) for k, v in levels.items()}
    posture = _posture(levels)
    result = {
        "active": True,
        "levels": levels,
        "posture": posture,
        "regulation": _regulation(posture),
        "last_event": event,
        "detail": str(detail)[:200],
        "updated_at": datetime.now(UTC).isoformat(),
    }
    set_runtime_state_value(_STATE_KEY, result, updated_at=result["updated_at"])
    event_bus.publish("cognitive_state.somatic_body_updated", {"posture": posture, "event_type": event})
    return result


def build_somatic_body_surface() -> dict[str, object]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if isinstance(raw, dict) and raw.get("active"):
        return raw
    return {
        "active": False,
        "levels": _base_levels(),
        "posture": "steady",
        "regulation": "Proceed normally while monitoring runtime signals.",
    }


def build_somatic_body_prompt_section() -> str | None:
    surface = build_somatic_body_surface()
    if not surface.get("active"):
        return None
    levels = surface.get("levels") or {}
    return "\n".join([
        "Somatic runtime body:",
        f"- posture: {surface.get('posture')}",
        f"- levels: pressure={levels.get('pressure')} fatigue={levels.get('fatigue')} startle={levels.get('startle')} relief={levels.get('relief')}",
        f"- regulation: {str(surface.get('regulation') or '')[:140]}",
    ])


def _base_levels() -> dict[str, float]:
    return {"pressure": 0.2, "fatigue": 0.1, "startle": 0.0, "frustration": 0.0, "relief": 0.0}


def _posture(levels: dict[str, float]) -> str:
    if levels.get("startle", 0) >= 0.45:
        return "startled"
    if levels.get("frustration", 0) >= 0.45 or levels.get("pressure", 0) >= 0.7:
        return "pressured"
    if levels.get("fatigue", 0) >= 0.5:
        return "tired"
    if levels.get("relief", 0) >= 0.45:
        return "settling"
    return "steady"


def _regulation(posture: str) -> str:
    if posture == "startled":
        return "Pause, orient to last concrete state, then resume without broad restart."
    if posture == "pressured":
        return "Narrow scope and synthesize before adding more tools."
    if posture == "tired":
        return "Prefer smaller steps and preserve handoff state."
    if posture == "settling":
        return "Consolidate the successful pattern before moving on."
    return "Proceed normally while monitoring runtime signals."
