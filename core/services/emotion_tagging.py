"""Emotion tagging — capture affective context at memory-creation time.

Existing memory creation (private_brain, sensory, council) does not
record the mood/affective state in which the memory was formed. That's
a missed signal — emotion-tagged memories let later recall surface
"what was I feeling when I learned this?" and helps mood-weighted recall
(in memory_recall_engine) score more accurately.

This module is a thin wrapper that captures current_mood + dominant
affect at call-time and returns a tag dict. Callers attach it to their
memory records (in metadata field).

Does NOT modify existing record-creation paths — opt-in. New code paths
can call ``current_emotion_tag()`` and stash the result.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def current_emotion_tag() -> dict[str, Any]:
    """Snapshot current affective state for tagging a new memory."""
    tag: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "mood": {},
        "dominant_affect": "",
        "temperature_field": "",
    }
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        mood_name = str(get_current_mood() or "")
        intensity = float(get_mood_intensity() or 0.0)
        if mood_name:
            tag["mood"] = {mood_name: round(intensity, 3)}
            if intensity >= 0.5:
                tag["dominant_affect"] = mood_name
    except Exception as exc:
        logger.debug("emotion_tag: mood read failed: %s", exc)
    try:
        from core.services.affective_meta_state import current_temperature_field
        tf = current_temperature_field()
        if tf:
            tag["temperature_field"] = str(tf)
    except Exception:
        pass
    return tag


def format_emotion_tag(tag: dict[str, Any]) -> str:
    """Render a tag as a compact string for inclusion in memory text."""
    if not tag or not tag.get("mood"):
        return ""
    parts = []
    if tag.get("dominant_affect"):
        parts.append(f"feeling={tag['dominant_affect']}")
    if tag.get("temperature_field"):
        parts.append(f"field={tag['temperature_field']}")
    mood = tag.get("mood") or {}
    top3 = sorted(mood.items(), key=lambda kv: kv[1], reverse=True)[:3]
    if top3:
        parts.append("mood:" + ",".join(f"{k}={v:.2f}" for k, v in top3))
    return f"[{' | '.join(parts)}]" if parts else ""


def _exec_capture_emotion_tag(args: dict[str, Any]) -> dict[str, Any]:
    tag = current_emotion_tag()
    return {"status": "ok", "tag": tag, "compact": format_emotion_tag(tag)}


EMOTION_TAGGING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "capture_emotion_tag",
            "description": (
                "Snapshot current affective state (mood vector + dominant "
                "affect + temperature field) — for attaching to a new memory "
                "record so later recall can answer 'what was I feeling when "
                "I learned this?'."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
