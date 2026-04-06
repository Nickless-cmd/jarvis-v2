"""Procedure Bank — reusable procedures learned from experience.

When Jarvis successfully completes a task type multiple times,
the approach can be extracted as a reusable procedure.
"""

from __future__ import annotations

import logging

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# In-memory procedure store (will be DB-backed when patterns emerge)
_PROCEDURES: list[dict[str, object]] = []


def record_procedure(
    *,
    name: str,
    trigger_pattern: str,
    procedure_text: str,
    success_count: int = 1,
) -> dict[str, object]:
    """Record or update a learned procedure."""
    for proc in _PROCEDURES:
        if proc.get("name") == name:
            proc["success_count"] = int(proc.get("success_count", 0)) + 1
            proc["procedure_text"] = procedure_text
            event_bus.publish("cognitive_procedure.updated", {"name": name})
            return proc

    entry = {
        "name": name,
        "trigger_pattern": trigger_pattern,
        "procedure_text": procedure_text,
        "success_count": success_count,
    }
    _PROCEDURES.append(entry)
    event_bus.publish("cognitive_procedure.created", {"name": name})
    return entry


def build_procedure_surface() -> dict[str, object]:
    return {
        "active": bool(_PROCEDURES),
        "procedures": _PROCEDURES[:20],
        "summary": f"{len(_PROCEDURES)} procedures learned" if _PROCEDURES else "No procedures yet",
    }
