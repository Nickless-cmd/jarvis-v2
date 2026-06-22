"""Agents-cluster — gør multi-agent-systemerne synlige i Den Intelligente Central: agent-pool
(spawn_agent_task), swarm (dispatch af flere agenter), og council (deliberation). Før var de
HELT usynlige — en spawnet agent der fejlede/loopede/brændte tokens, eller en council der gik
i deadlock, blev aldrig fanget af nogen cluster.

Observe pr. lifecycle-punkt: agent spawn/error, council-deliberation-udfald (rounds/deadlock/
escalation/recruitment). Metadata-only. Grundlag for adaptiv læring (er swarm/council stabilt?).
Self-safe; kaster aldrig ind i agent-/council-stien.
"""
from __future__ import annotations

from typing import Any


def _observe(nerve: str, data: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "agents", "nerve": nerve, **data})
    except Exception:
        pass


def note_agent_spawn(agent_id: str, role: str, *, parent: str = "",
                     council_id: str = "", mode: str = "") -> None:
    """En agent blev spawnet (pool/swarm). Metadata-only."""
    _observe("agent_spawn", {
        "agent_id": str(agent_id or ""), "role": str(role or ""),
        "parent": str(parent or ""), "council_id": str(council_id or ""),
        "mode": str(mode or ""),
    })


def note_agent_error(agent_id: str, error: Any, **data: Any) -> None:
    """En agent fejlede → observe (synlig)."""
    _observe("agent_error", {"agent_id": str(agent_id or ""),
                             "error": f"{type(error).__name__}: {error}"[:160], **data})


def note_council(topic: str, *, rounds: int = 0, deadlocked: bool = False,
                 escalated: bool = False, recruited: str = "") -> None:
    """En council-deliberation kørte → observe udfald (rounds/deadlock/witness-escalation/
    recruitment). Deadlock + escalation er de interessante mønstre."""
    _observe("council_session", {
        "topic": str(topic or "")[:80], "rounds": int(rounds or 0),
        "deadlocked": bool(deadlocked), "escalated": bool(escalated),
        "recruited": str(recruited or ""),
    })


def agents_summary(*, window: int = 500) -> dict[str, Any]:
    """Read-only: nylig agent/council-aktivitet (til MC). Self-safe."""
    spawns = 0
    errors = 0
    councils = 0
    deadlocks = 0
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent(limit=window):
            if r.cluster != "agents":
                continue
            if r.nerve == "agent_spawn":
                spawns += 1
            elif r.nerve == "agent_error":
                errors += 1
            elif r.nerve == "council_session":
                councils += 1
                if (r.payload or {}).get("deadlocked"):
                    deadlocks += 1
    except Exception:
        pass
    return {"agent_spawns": spawns, "agent_errors": errors,
            "council_sessions": councils, "council_deadlocks": deadlocks}
