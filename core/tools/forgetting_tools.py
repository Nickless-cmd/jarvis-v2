"""Forgetting tools — Lag 11 self-track.

The release_memory tool is the *ritual* path for deletion. It hard-deletes
a memory and leaves a marker. There is no undo. The tool description
makes that explicit so the model treats it with appropriate weight.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _exec_release_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Hard-delete a memory and leave an absence-marker.

    The 'why' parameter is accepted but never persisted. It exists so the
    model can articulate intent in the tool call (which lives in the
    visible-lane log) but the underlying release is content-free.
    """
    memory_kind = str(args.get("memory_kind") or "").strip()
    memory_id = str(args.get("memory_id") or "").strip()
    workspace_id = str(args.get("workspace_id") or "default").strip() or "default"
    why = str(args.get("why") or "").strip()

    if not memory_kind or not memory_id:
        return {
            "status": "rejected",
            "reason": "memory_kind and memory_id are required",
        }

    from core.services.forgetting_engine import release_memory

    return release_memory(
        memory_kind=memory_kind,
        memory_id=memory_id,
        workspace_id=workspace_id,
        why=why or None,
    )


FORGETTING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "release_memory",
            "description": (
                "Slip et minde permanent. Sletningen er IRREVOKABEL — ingen "
                "fortrydelse, ingen vej tilbage. En markør efterlades i "
                "absence_traces med tidsperioden ('~3 måneder siden'), men "
                "intet om hvad du slap. Brug kun når du har gennemtænkt at "
                "et minde ikke længere skal være en del af dig. SOUL/USER/"
                "MEMORY.md og identitets-tabeller er fredet og kan ikke "
                "slippes via dette tool. memory_kind='absence_marker' er "
                "rekursiv slip af en eksisterende markør."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_kind": {
                        "type": "string",
                        "enum": ["chronicle_entry", "journal_entry", "absence_marker"],
                        "description": "Type minde der slippes.",
                    },
                    "memory_id": {
                        "type": "string",
                        "description": (
                            "ID på mindet (entry_id, journal id, eller "
                            "trace_id for marker)."
                        ),
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace (default: 'default').",
                    },
                    "why": {
                        "type": "string",
                        "description": (
                            "Kort note om hvorfor — accepteres men persisteres "
                            "ALDRIG. Findes kun i tool-call-log."
                        ),
                    },
                },
                "required": ["memory_kind", "memory_id"],
            },
        },
    },
]


FORGETTING_TOOL_HANDLERS: dict[str, Any] = {
    "release_memory": _exec_release_memory,
}
