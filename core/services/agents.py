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


def note_agent_result(agent_id: str, status: str, *, tokens_in: int = 0,
                      tokens_out: int = 0, cost_usd: float = 0.0,
                      duration_ms: int = 0, tool_calls: int = 0,
                      role: str = "", **data: Any) -> None:
    """En agent-dispatch afsluttede (succes ELLER fejl) → observe robusthedskonvolut
    (status + tokens/cost/duration/tool_calls) + registrér to numeriske tidsserier
    (agent_duration_ms + agent_tokens=in+out) så trend/drift bliver læsbar via `jc series`.
    Metadata-only. Self-safe — kaster ALDRIG ind i dispatch-stien."""
    try:
        tin = int(tokens_in or 0)
        tout = int(tokens_out or 0)
        dur = int(duration_ms or 0)
        cost = float(cost_usd or 0.0)
        calls = int(tool_calls or 0)
    except Exception:
        tin = tout = dur = calls = 0
        cost = 0.0
    _observe("agent_result", {
        "agent_id": str(agent_id or ""), "status": str(status or ""),
        "role": str(role or ""), "tokens_in": tin, "tokens_out": tout,
        "cost_usd": cost, "duration_ms": dur, "tool_calls": calls, **data,
    })
    try:
        from core.services import central_timeseries
        meta = {"agent_id": str(agent_id or ""), "status": str(status or ""),
                "role": str(role or "")}
        central_timeseries.record("agents", "agent_duration_ms", dur, meta=meta)
        central_timeseries.record("agents", "agent_tokens", tin + tout,
                                  meta={"cost_usd": cost, "status": str(status or ""),
                                        "agent_id": str(agent_id or ""),
                                        "tokens_in": tin, "tokens_out": tout})
    except Exception:
        pass


def note_agent_blocked(agent_id: str, status: str = "blocked", *, reason: str = "",
                       role: str = "", **data: Any) -> None:
    """En agent blev BLOKERET / mangler kontekst (typet ikke-fejl) → distinkt observe.
    VIGTIGT: dette er IKKE en fejl — det er en anmodning-om-hjælp. Vi router den ALDRIG
    gennem note_agent_error, fordi det ville falsk inflatere fejl-raten som Centralens
    drift-detektion vogter. Self-safe."""
    _observe("agent_blocked", {
        "agent_id": str(agent_id or ""), "status": str(status or "blocked"),
        "kind": "blocked", "reason": str(reason or "")[:160], "role": str(role or ""),
        **data,
    })


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
