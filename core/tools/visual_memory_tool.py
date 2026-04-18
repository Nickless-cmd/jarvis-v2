"""Visual memory tool — Jarvis kan læse sine egne visuelle minder.

Native tool der giver Jarvis adgang til de seneste webcam-beskrivelser.
Bruges til at bringe ikke-sproglig rumfornemmelse ind i samtalen.

Tools:
  read_visual_memory — returner de N seneste visuelle minder
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def _exec_read_visual_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Read recent visual memories (webcam room descriptions).

    Args:
        limit: Number of recent memories to return (default: 5, max: 20).
    """
    limit = min(int(args.get("limit", 5)), 20)

    try:
        from core.services.visual_memory import get_visual_memories, build_visual_memory_surface

        surface = build_visual_memory_surface()
        if not surface.get("enabled"):
            return {
                "status": "disabled",
                "message": "Visual memory er deaktiveret (layer_visual_memory_enabled=false).",
            }

        memories = get_visual_memories(limit=limit)
        if not memories:
            return {
                "status": "empty",
                "message": "Ingen visuelle minder endnu — dæmonen har ikke kørt endnu.",
                "configured_model": surface.get("configured_model"),
            }

        return {
            "status": "ok",
            "count": len(memories),
            "total_records": surface.get("record_count", 0),
            "memories": [
                {
                    "captured_at": m.get("captured_at", ""),
                    "description": m.get("description", ""),
                    "model": m.get("model", ""),
                }
                for m in memories
            ],
        }

    except Exception as exc:
        logger.warning("read_visual_memory failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

VISUAL_MEMORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_visual_memory",
            "description": (
                "Læs dine seneste visuelle minder — beskrivelser af rummet genereret fra "
                "webcam-snapshots. Brug dette når du vil vide hvordan rummet ser ud lige nu "
                "eller ønsker at bringe en sansemæssig fornemmelse ind i samtalen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Antal seneste minder at returnere (default: 5, max: 20).",
                    },
                },
            },
        },
    },
]
