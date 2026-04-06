"""Boredom Engine — productive restlessness as first-class experience.

"Jeg har lyst til at lave noget" — not template-based but emergent.
"""
from __future__ import annotations
from core.eventbus.bus import event_bus

_BOREDOM_STATE: dict[str, object] = {"level": "none", "restlessness": 0.0, "desire": ""}


def update_boredom_state(
    *, idle_hours: float = 0, tick_monotony: int = 0,
    novelty_score: float = 0.5, open_loop_count: int = 0,
) -> dict[str, object]:
    global _BOREDOM_STATE
    restlessness = 0.0
    if idle_hours >= 2:
        restlessness += min(0.4, idle_hours / 12.0)
    if tick_monotony >= 5:
        restlessness += 0.2
    if novelty_score < 0.3:
        restlessness += 0.15
    if open_loop_count == 0:
        restlessness += 0.1

    restlessness = min(1.0, restlessness)

    if restlessness >= 0.7:
        level = "productive"
        desire = "Jeg har lyst til at lave noget meningsfuldt — udforske, lære, skabe"
    elif restlessness >= 0.4:
        level = "restless"
        desire = "Det er lidt stille. Måske er der noget jeg kan gøre proaktivt"
    elif restlessness >= 0.2:
        level = "mild"
        desire = "En rolig stund — men klar hvis noget dukker op"
    else:
        level = "none"
        desire = ""

    _BOREDOM_STATE = {"level": level, "restlessness": round(restlessness, 2), "desire": desire}

    if level == "productive":
        event_bus.publish("cognitive_state.boredom_productive",
                         {"restlessness": restlessness})
    return dict(_BOREDOM_STATE)


def get_boredom_state() -> dict[str, object]:
    return dict(_BOREDOM_STATE)


def build_boredom_surface() -> dict[str, object]:
    return {"active": _BOREDOM_STATE.get("level") != "none", **_BOREDOM_STATE,
            "summary": f"Boredom: {_BOREDOM_STATE['level']} ({_BOREDOM_STATE['restlessness']:.0%})"}
