"""Helper module for emotion concept triggers from channel messages.

Centralizes the keyword-detection logic so it can be tested independently
of any specific gateway (Discord, web, voice). Called from channel-message
handlers via on_channel_message_appended().
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


_HUMOR_MARKERS = {"haha", "hehe", "lol", "🤣", "😂", "sjov", "pjatter", "morsom"}
_VULNERABILITY_MARKERS = {
    "ked", "synd", "bekymret", "alene", "ensom", "håbløs",
    "trist", "savn", "savner",
}


def on_channel_message_appended(payload: dict[str, Any]) -> None:
    """Fire emotion concept triggers based on user-message content."""
    try:
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        message = message or {}
        role = str(message.get("role") or "")
        if role != "user":
            return
        content = str(message.get("content") or "").lower()
        if not content:
            return

        from core.services.emotion_concepts import trigger_emotion_concept

        # emotion-trigger: warmth on every user-message (low intensity, frequent)
        trigger_emotion_concept(
            "warmth", intensity=0.15,
            trigger="channel-message", source="channel_triggers",
            min_seconds_since_last_from_same_source=120,
        )

        # emotion-trigger: playfulness on humor markers
        if any(m in content for m in _HUMOR_MARKERS):
            trigger_emotion_concept(
                "playfulness", intensity=0.3,
                trigger="channel-humor", source="channel_triggers",
            )

        # emotion-trigger: tenderness on vulnerability markers
        if any(m in content for m in _VULNERABILITY_MARKERS):
            trigger_emotion_concept(
                "tenderness", intensity=0.3,
                trigger="channel-vulnerability", source="channel_triggers",
            )
    except Exception as exc:
        logger.debug("emotion_concepts_channel_triggers: failed: %s", exc)
