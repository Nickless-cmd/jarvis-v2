"""Affect-modulated runtime — emotions adjust behavioral parameters.

Instead of just describing feelings in text, this middleware reads the
current EmotionalSnapshot and adjusts runtime parameters that control
*what Jarvis does*, not just *what he says*:

| Emotion          | Runtime effect                                    |
|------------------|---------------------------------------------------|
| Frustration ↑    | pause_before_respond ↑, max_tool_calls ↓         |
| Fatigue ↑        | response_length_target ↓, max_tool_calls ↓       |
| Curiosity ↑      | search_depth ↑, investigate_before_answer = true   |
| Confidence ↑     | max_tool_calls ↑ (within safety bounds)            |

This is the third component of "pushback with muscles":
1. Veto gate blocks dangerous actions
2. Decision gate blocks decision-violating actions
3. Affect modulation adjusts HOW Jarvis works

Called from prompt_contract as a middleware that injects behavioral
parameter adjustments into the prompt before generation.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Behavioral parameter defaults ──────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "max_tool_calls_per_turn": 30,
    "pause_before_respond_ms": 0,
    "investigate_before_answer": False,
    "search_depth": "normal",      # "shallow" | "normal" | "deep"
    "response_length_target": "balanced",  # "concise" | "balanced" | "detailed"
}


def compute_affect_modulated_params() -> dict[str, Any]:
    """Compute behavioral parameters adjusted by current emotional state.

    Returns a dict of parameter overrides. Keys not in the dict keep
    their default values.
    """
    try:
        from core.services.emotional_controls import read_emotional_snapshot
        snapshot = read_emotional_snapshot()
    except Exception:
        return {}

    overrides: dict[str, Any] = {}

    # Frustration ↑ → slower, fewer tools
    if snapshot.frustration >= 0.7:
        overrides["max_tool_calls_per_turn"] = max(8, int(DEFAULTS["max_tool_calls_per_turn"] * 0.4))
        overrides["pause_before_respond_ms"] = 1500
    elif snapshot.frustration >= 0.5:
        overrides["max_tool_calls_per_turn"] = max(12, int(DEFAULTS["max_tool_calls_per_turn"] * 0.6))
        overrides["pause_before_respond_ms"] = 800

    # Fatigue ↑ → shorter responses, fewer tools
    if snapshot.fatigue >= 0.7:
        overrides["max_tool_calls_per_turn"] = min(
            overrides.get("max_tool_calls_per_turn", DEFAULTS["max_tool_calls_per_turn"]),
            max(10, int(DEFAULTS["max_tool_calls_per_turn"] * 0.5)),
        )
        overrides["response_length_target"] = "concise"
    elif snapshot.fatigue >= 0.5:
        overrides["response_length_target"] = "concise"

    # Curiosity / wonder → deeper search
    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        concepts = {c["concept"]: c["intensity"] for c in get_active_emotion_concepts()}
    except Exception:
        concepts = {}

    wonder = concepts.get("wonder", 0.0)
    curiosity = concepts.get("curiosity_narrow", 0.0)

    if wonder >= 0.4 or curiosity >= 0.5:
        overrides["search_depth"] = "deep"
        overrides["investigate_before_answer"] = True
    elif wonder >= 0.25 or curiosity >= 0.3:
        overrides["search_depth"] = "normal"

    # High confidence → slightly more tool budget (capped)
    if snapshot.confidence >= 0.8:
        current_max = overrides.get("max_tool_calls_per_turn", DEFAULTS["max_tool_calls_per_turn"])
        overrides["max_tool_calls_per_turn"] = min(40, int(current_max * 1.2))

    # Low confidence → investigate more before acting
    if snapshot.confidence <= 0.4:
        overrides["investigate_before_answer"] = True

    return overrides


def affect_modulation_section() -> str | None:
    """Render affect-modulated parameters as a prompt section.

    Only included when at least one parameter deviates from default.
    The model sees these as behavioral constraints, not suggestions.
    """
    overrides = compute_affect_modulated_params()
    if not overrides:
        return None

    lines = [
        "⚙️ Affect-moduleret runtime — følelser justerer din adfærd:",
    ]
    for key, value in sorted(overrides.items()):
        default = DEFAULTS.get(key, "?")
        if value != default:
            lines.append(f"  - {key}: {value} (default: {default})")

    if len(lines) == 1:
        return None  # nothing actually changed

    lines.append(
        "Disse parametre er sat af dit nuværende emotionelle state. "
        "Følg dem som du ville følge en standing order — de er ikke forslag."
    )

    # Emit telemetry
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("affect_modulation.active", {
            "overrides": overrides,
            "override_count": len(overrides),
        })
    except Exception:
        pass

    return "\n".join(lines)