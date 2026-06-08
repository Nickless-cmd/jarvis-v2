"""Tools for Persistent Identity Sketch — read and update.

Two tools:
  - ``read_identity_sketch`` — read current sketch
  - ``update_identity_sketch`` — manually trigger an update
"""
from __future__ import annotations

from typing import Any


def _exec_read_identity_sketch(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.services.identity_sketch import get_identity_sketch
        sketch = get_identity_sketch()
        if sketch:
            content = sketch.get("content", "")
            updated = sketch.get("updated_at", "unknown")
            version = sketch.get("version", 0)
            trigger = sketch.get("updated_by", "unknown")
            return {
                "status": "ok",
                "content": content,
                "updated_at": updated,
                "version": version,
                "updated_by": trigger,
            }
        return {"status": "ok", "content": None, "note": "No sketch exists yet."}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_update_identity_sketch(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.services.identity_sketch import update_identity_sketch
        trigger = str(args.get("trigger", "manual"))
        result = update_identity_sketch(trigger=trigger)
        return {
            "status": "ok",
            "version": result["version"],
            "updated_at": result["updated_at"],
            "content": result["content"],
            "trigger": result["trigger"],
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


IDENTITY_SKETCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_identity_sketch",
            "description": (
                "Read Jarvis' current identity sketch — a 150-250 word "
                "dynamic document describing who he is right now: mood, "
                "active goals, recent events, and current focus. Survives "
                "compaction and model swaps."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_identity_sketch",
            "description": (
                "Manually trigger an identity sketch update. The sketch is "
                "generated from live signals (mood, goals, events, sensory "
                "context) and persisted. Also updates automatically before "
                "compaction and periodically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger": {
                        "type": "string",
                        "enum": ["manual", "post_conversation", "model_swap"],
                        "description": "What triggered the update (default: 'manual')",
                    },
                },
                "required": [],
            },
        },
    },
]
