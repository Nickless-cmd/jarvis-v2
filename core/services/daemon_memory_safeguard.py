"""Daemon memory safeguard — post-hoc check that Jarvis saved what mattered.

This is the "daemon half" of the double-nudge system. After each heartbeat
tick, it checks whether the most recent assistant turn contained learning
markers (corrections, new facts, user preferences) WITHOUT a corresponding
save-tool call (memory_upsert_section, remember_this, write to USER.md, etc.).

If a gap is detected, it fires a `memory_safeguard.missed_save` event and
appends a nudge to the next prompt via the initiative queue.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that suggest something learnable happened
_LEARNING_MARKERS = re.compile(
    r"(jeg (har |skal |bør |må |vil )?lært|jeg (har |skal )?gemt|"
    r"husk dette|ny fakt(a|um)|bruger.{0,10}præference|"
    r"korrekt(ion|ere)|rettelse|vigtigt at|skal gemmes|"
    r"standing order|beslutning:|decision:|fra nu af|"
    r"jeg (noterer|noterer mig|bemærker)|skriv ned|note:)",
    re.IGNORECASE,
)

# Tool calls that count as "saving"
_SAVE_TOOLS = {
    "memory_upsert_section",
    "remember_this",
    "write_file",  # writing to MEMORY.md / USER.md counts
    "edit_file",   # editing those files counts too
}


def run(**kwargs: Any) -> dict[str, Any]:
    """Check last assistant turn for missed saves. Called by heartbeat."""
    try:
        from core.services.chat_sessions import recent_chat_session_messages
        from core.eventbus.bus import event_bus
    except Exception:
        return {"status": "skip", "reason": "imports failed"}

    # Get the most recent assistant message
    try:
        messages = recent_chat_session_messages(limit=4)
    except Exception:
        return {"status": "skip", "reason": "no messages"}

    last_assistant = None
    for msg in reversed(messages):
        role = str(msg.get("role", "")).lower()
        if role == "assistant":
            last_assistant = msg.get("content", "")
            break

    if not last_assistant:
        return {"status": "skip", "reason": "no assistant message"}

    # Check for learning markers
    has_marker = bool(_LEARNING_MARKERS.search(last_assistant))

    if not has_marker:
        return {"status": "ok", "reason": "no learning markers detected"}

    # Check if a save tool was called recently
    try:
        events = event_bus.recent(limit=30)
        save_called = any(
            str(e.get("kind", "")) == "tool.invoked"
            and str(e.get("data", {}).get("tool_name", "")) in _SAVE_TOOLS
            for e in events
        )
    except Exception:
        save_called = False

    if save_called:
        return {"status": "ok", "reason": "learning marker + save tool called"}

    # Gap detected — fire nudge
    try:
        event_bus.publish(
            "memory_safeguard.missed_save",
            {
                "hint": "Læringsmarkør fundet uden save-tool. Kald memory_upsert_section eller remember_this nu!",
                "message_preview": last_assistant[:200],
            },
        )
    except Exception:
        pass

    logger.info("memory_safeguard: learning marker without save detected")

    return {
        "status": "nudge_fired",
        "reason": "learning marker found but no save tool called",
    }