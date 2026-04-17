"""Silence Detector — what is the user NOT saying?

Analyzes conversation patterns to detect avoided topics,
unasked questions, and tension signals hidden in silence.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def detect_silence_signals(
    *,
    recent_topics: list[str],
    expected_topics: list[str],
    conversation_length: int = 0,
    user_corrections: int = 0,
) -> list[dict[str, object]]:
    """Detect what's missing from the conversation."""
    signals = []
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Topics expected but not mentioned
    recent_lower = {t.lower() for t in recent_topics}
    for expected in expected_topics:
        if expected.lower() not in recent_lower:
            signals.append({
                "type": "topic_avoidance",
                "topic": expected,
                "confidence": 0.4,
                "evidence": f"Expected topic '{expected}' not mentioned in recent conversation",
                "ts": now,
            })

    # Short conversations after corrections might signal frustration
    if user_corrections >= 2 and conversation_length <= 3:
        signals.append({
            "type": "truncated_after_correction",
            "topic": None,
            "confidence": 0.6,
            "evidence": f"{user_corrections} corrections in {conversation_length} turns — possible frustration",
            "ts": now,
        })

    # Long silence after active period
    # (This would need idle_hours tracking, handled by heartbeat)

    for signal in signals:
        event_bus.publish(
            "cognitive_silence.signal_detected",
            {"type": signal["type"], "confidence": signal["confidence"]},
        )

    return signals


def build_silence_surface() -> dict[str, object]:
    return {
        "active": True,
        "description": "Silence detection runs during conversation analysis",
        "summary": "Monitoring for unspoken signals",
    }
