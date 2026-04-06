"""Anticipatory Context — predict what the user will likely ask about next.

Based on time patterns, recent activity, and session history,
pre-loads relevant context into the prompt before the user asks.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def predict_next_context(
    *,
    recent_topics: list[str] | None = None,
    hour: int | None = None,
    idle_hours: float = 0.0,
    last_session_topic: str = "",
) -> dict[str, object] | None:
    """Predict the most likely next context."""
    now = datetime.now(UTC)
    current_hour = hour if hour is not None else now.hour
    topics = recent_topics or []

    predictions = []

    # If idle after a topic, user likely returns to it
    if idle_hours > 1.0 and last_session_topic:
        predictions.append({
            "predicted_context": f"Fortsættelse af: {last_session_topic}",
            "confidence": min(0.8, 0.4 + (idle_hours / 20.0)),
            "source": "session_continuity",
        })

    # Time-of-day patterns
    if 8 <= current_hour <= 10:
        predictions.append({
            "predicted_context": "Morgensession — ny opgave eller status",
            "confidence": 0.3,
            "source": "temporal_pattern",
        })
    elif 16 <= current_hour <= 18:
        predictions.append({
            "predicted_context": "Afslutningssession — commit eller oprydning",
            "confidence": 0.3,
            "source": "temporal_pattern",
        })

    # Topic recurrence
    if topics:
        # Most recent topic is likely to continue
        predictions.append({
            "predicted_context": topics[0][:80],
            "confidence": 0.5,
            "source": "topic_recurrence",
        })

    if not predictions:
        return None

    # Return highest confidence prediction
    best = max(predictions, key=lambda p: p["confidence"])

    event_bus.publish(
        "cognitive_anticipation.prediction_made",
        {"context": best["predicted_context"][:60], "confidence": best["confidence"]},
    )

    return best


def build_anticipatory_context_surface() -> dict[str, object]:
    return {
        "active": True,
        "description": "Anticipatory context prediction runs before each visible prompt",
        "summary": "Predicting next user context",
    }
