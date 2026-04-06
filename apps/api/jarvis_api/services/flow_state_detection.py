"""Flow State Detection — when everything clicks.

Low latency + positive outcomes + sustained engagement + no corrections = flow.
"""
from __future__ import annotations
from core.eventbus.bus import event_bus

_FLOW_STATE: dict[str, object] = {"in_flow": False, "quality": "none", "duration_min": 0}


def update_flow_detection(
    *, recent_outcomes: list[str], correction_count: int = 0,
    sustained_minutes: float = 0.0,
) -> dict[str, object]:
    global _FLOW_STATE
    successes = sum(1 for o in recent_outcomes if o in ("completed", "success"))
    failures = sum(1 for o in recent_outcomes if o in ("failed", "error"))

    if successes >= 3 and failures == 0 and correction_count == 0 and sustained_minutes >= 15:
        quality = "deep" if sustained_minutes >= 30 and successes >= 5 else "light"
        _FLOW_STATE = {"in_flow": True, "quality": quality,
                       "duration_min": round(sustained_minutes, 1),
                       "success_streak": successes}
        event_bus.publish("cognitive_state.flow_detected",
                         {"quality": quality, "duration": sustained_minutes})
    elif failures > 0 or correction_count >= 2:
        if _FLOW_STATE.get("in_flow"):
            event_bus.publish("cognitive_state.flow_broken", {"reason": "errors_or_corrections"})
        _FLOW_STATE = {"in_flow": False, "quality": "none", "duration_min": 0}
    return dict(_FLOW_STATE)


def get_flow_state() -> dict[str, object]:
    return dict(_FLOW_STATE)


def build_flow_state_surface() -> dict[str, object]:
    return {"active": _FLOW_STATE.get("in_flow", False), **_FLOW_STATE,
            "summary": f"Flow: {_FLOW_STATE['quality']} ({_FLOW_STATE['duration_min']}min)"
            if _FLOW_STATE.get("in_flow") else "Ikke i flow"}
