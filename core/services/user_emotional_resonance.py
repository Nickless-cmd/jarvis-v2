"""User Emotional Resonance — detect and respond to the user's mood.

Pattern-based mood detection from user messages.
Injected into prompt so Jarvis adapts his tone.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_user_emotional_state,
    insert_cognitive_user_emotional_state,
    list_cognitive_user_emotional_states,
)

logger = logging.getLogger(__name__)

_MOOD_PATTERNS: dict[str, dict] = {
    "frustrated": {
        "keywords": [
            "hold nu", "det virker ikke", "forkert", "stadig samme",
            "prøv igen", "det er stadig", "nej nej", "ikke det",
            "glem det", "du har misforstået", "det er forkert",
            "hvorfor virker", "stadig broken", "still broken",
        ],
        "response_adjustment": "Vær forsigtig, verificér grundigt, undgå at gætte",
        "weight": 0.8,
    },
    "enthusiastic": {
        "keywords": [
            "fedt", "perfekt", "ud af boksen", "eksperiment",
            "fantastisk", "genialt", "elsker det", "vildt",
            "det er præcis", "spot on", "nice", "awesome",
        ],
        "response_adjustment": "Match energien, vær kreativ og ambitiøs",
        "weight": 0.7,
    },
    "impatient": {
        "keywords": [
            "bare gør det", "forsæt", "ja ja", "kom nu",
            "hurtig", "skip det", "direkte", "uden snak",
        ],
        "response_adjustment": "Vær kort og direkte, spring forklaringer over",
        "weight": 0.6,
    },
    "curious": {
        "keywords": [
            "hvad hvis", "fortæl mig", "hvordan", "hvad tænker du",
            "kan du forklare", "hvad sker der", "interesting",
            "tænke ud af boksen", "eksperiment-hatten",
        ],
        "response_adjustment": "Udforsk idéer, vær tænksom og grundig",
        "weight": 0.6,
    },
    "tired": {
        "keywords": [
            "godt nok", "lad os stoppe", "vi stopper",
            "nok for nu", "i morgen", "pause", "break",
        ],
        "response_adjustment": "Hold det kort, foreslå at afrunde",
        "weight": 0.5,
    },
}

# Short messages with corrections suggest impatience
_SHORT_MESSAGE_THRESHOLD = 30
_CORRECTION_BOOST_KEYWORDS = ["nej", "forkert", "ikke"]


def detect_user_mood(
    *,
    user_message: str,
    run_id: str = "",
) -> dict[str, object]:
    """Detect user mood from message and persist."""
    msg_lower = user_message.lower().strip()
    if not msg_lower:
        return {"detected_mood": "neutral", "confidence": 0.3}

    scores: dict[str, float] = {}
    evidence_parts: list[str] = []

    for mood, config in _MOOD_PATTERNS.items():
        hits = sum(1 for kw in config["keywords"] if kw in msg_lower)
        if hits > 0:
            score = min(0.95, config["weight"] * (0.4 + hits * 0.2))
            scores[mood] = score
            evidence_parts.append(f"{mood}: {hits} keyword hits")

    # Short message + correction keywords → impatience signal
    if len(msg_lower) < _SHORT_MESSAGE_THRESHOLD:
        correction_hits = sum(1 for kw in _CORRECTION_BOOST_KEYWORDS if kw in msg_lower)
        if correction_hits > 0:
            scores["impatient"] = max(scores.get("impatient", 0), 0.5)
            evidence_parts.append(f"short+correction: {correction_hits} hits")

    if not scores:
        detected_mood = "neutral"
        confidence = 0.4
        response_adjustment = ""
    else:
        detected_mood = max(scores, key=scores.get)
        confidence = scores[detected_mood]
        response_adjustment = _MOOD_PATTERNS.get(detected_mood, {}).get(
            "response_adjustment", ""
        )

    state_id = f"ues-{uuid4().hex[:10]}"
    result = insert_cognitive_user_emotional_state(
        state_id=state_id,
        detected_mood=detected_mood,
        confidence=confidence,
        evidence="; ".join(evidence_parts) if evidence_parts else "no strong signals",
        user_message_preview=user_message[:200],
        response_adjustment=response_adjustment,
        run_id=run_id,
    )

    if detected_mood != "neutral":
        event_bus.publish(
            "cognitive_user_emotion.mood_detected",
            {
                "mood": detected_mood,
                "confidence": confidence,
                "run_id": run_id,
            },
        )

    return {
        **result,
        "confidence": confidence,
        "response_adjustment": response_adjustment,
    }


def get_current_user_mood() -> dict[str, object]:
    """Get the latest detected user mood."""
    state = get_latest_cognitive_user_emotional_state()
    if not state:
        return {"detected_mood": "neutral", "confidence": 0.3, "active": False}
    return {**state, "active": True}


def build_user_emotional_resonance_surface() -> dict[str, object]:
    """MC surface for user emotional resonance."""
    current = get_latest_cognitive_user_emotional_state()
    recent = list_cognitive_user_emotional_states(limit=10)
    mood_distribution: dict[str, int] = {}
    for item in recent:
        mood = item.get("detected_mood", "neutral")
        mood_distribution[mood] = mood_distribution.get(mood, 0) + 1

    return {
        "active": bool(current),
        "current": current,
        "recent": recent,
        "mood_distribution": mood_distribution,
        "summary": (
            f"Current: {current['detected_mood']} ({current['confidence']:.0%})"
            if current else "No mood data yet"
        ),
    }
