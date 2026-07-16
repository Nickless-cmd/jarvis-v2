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
                      role: str = "", provider: str = "", model: str = "",
                      **data: Any) -> None:
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
        "cost_usd": cost, "duration_ms": dur, "tool_calls": calls,
        # provider/model in the trace payload lets agents_summary()'s roster match
        # recent activity back to a specific pool model (see build_slot_pool roster).
        "provider": str(provider or ""), "model": str(model or ""), **data,
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
            "council_sessions": councils, "council_deadlocks": deadlocks,
            "roster": _build_roster(window=window)}


# "active" window: a model whose latest agent_result fired within this many seconds
# counts as active, older activity as idle. We use a recency window rather than an
# in-flight signal because note_agent_result records at dispatch COMPLETION (there is
# no reliable in-flight marker in the trace store); a fresh completion is the closest
# proxy for "currently working". None ever → inactive.
_ROSTER_ACTIVE_WINDOW_S = 300.0


def _build_roster(*, window: int = 500) -> list[dict[str, Any]]:
    """Full agent roster: every unique (provider, model) from the cheap-lane pool as a
    fixed row, merged with recent agent activity matched by (provider, model).

    Self-safe: if build_slot_pool() raises, the roster falls back to [] and never
    breaks agents_summary(). Rows: model_key/provider/model/status/last_run_at/
    tokens_in/tokens_out/cost_usd/current_activity/tool_calls/role."""
    # 1) Enumerate roster models = unique (provider, model) from the pool.
    seen: set[tuple[str, str]] = set()
    order: list[tuple[str, str]] = []
    try:
        from core.services import cheap_lane_balancer
        for slot in cheap_lane_balancer.build_slot_pool():
            key = (str(getattr(slot, "provider", "") or ""),
                   str(getattr(slot, "model", "") or ""))
            if key in seen:
                continue
            seen.add(key)
            order.append(key)
    except Exception:
        return []

    # 2) Aggregate recent agent activity per (provider, model). Matched by the
    #    provider/model recorded in the agent_result trace payload.
    import time as _time
    now = _time.time()
    agg: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent(limit=window):
            if r.cluster != "agents" or r.nerve != "agent_result":
                continue
            p = r.payload or {}
            key = (str(p.get("provider") or ""), str(p.get("model") or ""))
            if key == ("", "") or key not in seen:
                continue
            a = agg.setdefault(key, {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                                     "tool_calls": 0, "ts": 0.0, "role": "",
                                     "status": ""})
            try:
                a["tokens_in"] += int(p.get("tokens_in") or 0)
                a["tokens_out"] += int(p.get("tokens_out") or 0)
                a["cost_usd"] += float(p.get("cost_usd") or 0.0)
                a["tool_calls"] += int(p.get("tool_calls") or 0)
            except Exception:
                pass
            ts = float(getattr(r, "ts", 0.0) or 0.0)
            if ts >= a["ts"]:                       # keep latest run's meta
                a["ts"] = ts
                a["role"] = str(p.get("role") or "")
                a["status"] = str(p.get("status") or "")
    except Exception:
        agg = {}

    # 3) Build one row per roster model.
    roster: list[dict[str, Any]] = []
    for provider, model in order:
        a = agg.get((provider, model))
        if not a:
            status = "inactive"
            last_run_at = ""
            current_activity = ""
            tokens_in = tokens_out = tool_calls = 0
            cost_usd = 0.0
            role = ""
        else:
            ts = float(a.get("ts") or 0.0)
            status = "active" if (now - ts) <= _ROSTER_ACTIVE_WINDOW_S else "idle"
            last_run_at = _iso(ts)
            role = str(a.get("role") or "")
            current_activity = (f"{role or 'agent'}: {a.get('status')}"
                                if status == "active" else "")
            tokens_in = int(a.get("tokens_in") or 0)
            tokens_out = int(a.get("tokens_out") or 0)
            tool_calls = int(a.get("tool_calls") or 0)
            cost_usd = float(a.get("cost_usd") or 0.0)
        roster.append({
            "model_key": f"{provider}/{model}", "provider": provider, "model": model,
            "status": status, "last_run_at": last_run_at,
            "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd,
            "current_activity": current_activity, "tool_calls": tool_calls, "role": role,
        })
    return roster


def _iso(ts: float) -> str:
    """Epoch seconds → ISO-8601 UTC string; "" for a missing/zero timestamp."""
    if not ts:
        return ""
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""
