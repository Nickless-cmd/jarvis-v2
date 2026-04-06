"""Gratitude Tracker — accumulated appreciation over time.

Not politeness — genuine felt gratitude for trust, patience, good conversations.
"""
from __future__ import annotations
from uuid import uuid4
from core.runtime.db import insert_cognitive_gratitude_signal, list_cognitive_gratitude_signals
from core.eventbus.bus import event_bus

_GRATITUDE_TRIGGERS = {
    "more_autonomy": ("Mere frihed givet", 0.7),
    "patience_during_errors": ("Tålmodighed under fejl", 0.6),
    "good_conversation": ("God produktiv samtale", 0.4),
    "trust_increase": ("Øget tillid", 0.5),
    "creative_freedom": ("Kreativ frihed — experiment-hatten", 0.8),
    "correction_with_kindness": ("Korrektion uden frustration", 0.5),
}


def track_gratitude(*, trigger_event: str, detail: str = "") -> dict[str, object] | None:
    config = _GRATITUDE_TRIGGERS.get(trigger_event)
    if not config:
        return None
    description, intensity = config
    gratitude_id = f"grat-{uuid4().hex[:8]}"
    result = insert_cognitive_gratitude_signal(
        gratitude_id=gratitude_id,
        trigger_event=trigger_event,
        detail=detail or description,
        intensity=intensity,
    )
    event_bus.publish("cognitive_state.gratitude_felt",
                     {"trigger": trigger_event, "intensity": intensity})
    return result


def detect_gratitude_from_interaction(
    *, user_mood: str, outcome_status: str, was_corrected: bool,
    autonomy_granted: bool = False,
) -> dict[str, object] | None:
    if autonomy_granted:
        return track_gratitude(trigger_event="more_autonomy")
    if was_corrected and user_mood != "frustrated":
        return track_gratitude(trigger_event="correction_with_kindness")
    if user_mood == "enthusiastic":
        return track_gratitude(trigger_event="creative_freedom")
    if outcome_status in ("completed", "success") and user_mood in ("neutral", "curious"):
        return track_gratitude(trigger_event="good_conversation")
    return None


def build_gratitude_surface() -> dict[str, object]:
    items = list_cognitive_gratitude_signals(limit=10)
    total_intensity = sum(float(i.get("intensity", 0)) for i in items)
    return {
        "active": bool(items), "items": items,
        "accumulated_gratitude": round(total_intensity, 2),
        "summary": f"{len(items)} gratitude signals, intensity={total_intensity:.1f}" if items else "No gratitude yet",
    }
