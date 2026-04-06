"""Conversation Rhythm — tracks conversation signature patterns.

Detects: rapid_fire, deep_dive, correction_loop, flow_state, exploratory.
Over time, Jarvis learns which patterns lead to success or friction.
"""

from __future__ import annotations

import logging

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_cognitive_conversation_signatures,
    upsert_cognitive_conversation_signature,
)

logger = logging.getLogger(__name__)


def classify_conversation(
    *,
    turn_count: int,
    correction_count: int,
    avg_message_length: int,
    duration_minutes: float,
    outcome_status: str,
) -> str:
    """Classify the conversation rhythm pattern."""
    if correction_count >= 3:
        return "correction_loop"
    if turn_count >= 15 and duration_minutes >= 30:
        return "deep_dive"
    if turn_count >= 10 and avg_message_length < 50:
        return "rapid_fire"
    if duration_minutes >= 20 and correction_count == 0:
        return "flow_state"
    return "exploratory"


def track_conversation_rhythm(
    *,
    run_id: str,
    session_id: str = "",
    turn_count: int = 1,
    correction_count: int = 0,
    avg_message_length: int = 100,
    duration_minutes: float = 5.0,
    outcome_status: str = "completed",
) -> dict[str, object]:
    """Track and classify the conversation rhythm."""
    sig_type = classify_conversation(
        turn_count=turn_count,
        correction_count=correction_count,
        avg_message_length=avg_message_length,
        duration_minutes=duration_minutes,
        outcome_status=outcome_status,
    )

    success = outcome_status in ("completed", "success")
    result = upsert_cognitive_conversation_signature(
        signature_type=sig_type,
        success=success,
        context=outcome_status,
        duration_min=duration_minutes,
    )

    event_bus.publish(
        "cognitive_state.conversation_rhythm_tracked",
        {"signature": sig_type, "success": success, "turns": turn_count},
    )
    return {"signature_type": sig_type, **result}


def build_conversation_rhythm_surface() -> dict[str, object]:
    signatures = list_cognitive_conversation_signatures(limit=10)
    return {
        "active": bool(signatures),
        "signatures": signatures,
        "summary": (
            f"{len(signatures)} conversation patterns tracked"
            if signatures else "No conversation patterns yet"
        ),
    }
