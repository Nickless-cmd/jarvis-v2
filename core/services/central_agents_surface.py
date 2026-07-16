"""Central agents-/council-surface (B3, 13. jul 2026) — gør de nye agent-/council-
observabilitets-data synlige (owner-only).

To surfaces, samme mønster som central_cost_surface:
  build_agents_surface  → costs-aggregat (lane in agent/council) + agent-dispatch-udfald
                          (status/nerve fra agents-cluster-trace) + recent results.
  build_council_surface → council-convocations/roller/event-vs-ondemand-split (læser
                          agents-cluster council_session/council_convene-events).

Datakilder (instrumenteret af tidligere tasks — vi re-instrumenterer IKKE):
  - costs-tabellen, rækker med lane in ('agent','council') (via record_cost).
  - agents-cluster trace-events (agent_result/agent_blocked/agent_error/council_session)
    læst fra central_trace-ring-bufferen (samme kilde som agents.agents_summary).

Self-safe: en DB/read-fejl må ALDRIG vælte surfacen — den returnerer et validt
skelet-dict. Serves via /central/agents + /central/council + `jc agents|council`.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

_WINDOWS = {"today": None, "7d": 7}
_AGENT_LANES = ("agent", "council")
_TRACE_LIMIT = 1500  # hvor mange trace-records vi scanner for agents-cluster-signal


def _window_threshold(window: str) -> str:
    """ISO8601-tærskel (samme format som costs.created_at → lex-sammenlignelig).

    VIGTIGT: vi sammenligner mod Python-genereret isoformat (…T…+00:00), IKKE
    sqlite datetime('now',…) (mellemrum-format) som ville mis-sortere."""
    now = datetime.now(UTC)
    if window == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=_WINDOWS.get(window) or 7)
    return start.isoformat()


def _agg_for_window(conn, window: str) -> dict:
    thr = _window_threshold(window)
    placeholders = ",".join("?" for _ in _AGENT_LANES)
    row = conn.execute(
        f"""SELECT COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens),0) AS inp,
                   COALESCE(SUM(output_tokens),0) AS outp,
                   COALESCE(SUM(cost_usd),0.0) AS cost
            FROM costs
            WHERE created_at >= ? AND lane IN ({placeholders})""",
        [thr, *_AGENT_LANES],
    ).fetchone()
    return {
        "calls": int(row["calls"]),
        "input_tokens": int(row["inp"]),
        "output_tokens": int(row["outp"]),
        "cost_usd": round(float(row["cost"]), 4),
    }


def _lane_breakdown(conn, window: str) -> list[dict]:
    thr = _window_threshold(window)
    placeholders = ",".join("?" for _ in _AGENT_LANES)
    rows = conn.execute(
        f"""SELECT COALESCE(lane,'') AS lane, provider, model,
                   COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens),0) AS inp,
                   COALESCE(SUM(output_tokens),0) AS outp,
                   COALESCE(SUM(cost_usd),0.0) AS cost
            FROM costs
            WHERE created_at >= ? AND lane IN ({placeholders})
            GROUP BY lane, provider, model
            ORDER BY cost DESC, calls DESC""",
        [thr, *_AGENT_LANES],
    ).fetchall()
    return [{
        "lane": str(r["lane"] or ""),
        "provider": str(r["provider"] or ""),
        "model": str(r["model"] or ""),
        "calls": int(r["calls"]),
        "input_tokens": int(r["inp"]),
        "output_tokens": int(r["outp"]),
        "cost_usd": round(float(r["cost"]), 4),
    } for r in rows]


def _agents_trace() -> list:
    """De seneste agents-cluster trace-records (nyeste sidst). Self-safe."""
    try:
        from core.services import central_trace
        return [r for r in central_trace.sink().recent(limit=_TRACE_LIMIT)
                if str(getattr(r, "cluster", "")) == "agents"]
    except Exception:
        return []


def _dispatch_signal(records: list) -> dict:
    """Per-status + recent fra agent_result/agent_blocked/agent_error-events."""
    by_status: dict[str, int] = {}
    recent: list[dict] = []
    total = 0
    for r in records:
        nerve = str(getattr(r, "nerve", ""))
        p = getattr(r, "payload", None) or {}
        if nerve == "agent_result":
            status = str(p.get("status") or "unknown")
        elif nerve == "agent_blocked":
            status = "blocked"
        elif nerve == "agent_error":
            status = "error"
        else:
            continue
        total += 1
        by_status[status] = by_status.get(status, 0) + 1
        recent.append({
            "agent_id": str(p.get("agent_id") or ""),
            "status": status,
            "role": str(p.get("role") or ""),
            "nerve": nerve,
            "tokens_in": int(p.get("tokens_in") or 0),
            "tokens_out": int(p.get("tokens_out") or 0),
            "cost_usd": round(float(p.get("cost_usd") or 0.0), 4),
            "duration_ms": int(p.get("duration_ms") or 0),
            "reason": str(p.get("reason") or "")[:120],
        })
    recent.reverse()  # nyeste først
    return {"total": total, "by_status": by_status, "recent": recent[:20]}


def build_agents_surface(*, window: str = "today") -> dict:
    """Agent-observabilitet til /central/agents + `jc agents`.

    window: hvilket vindue lane-breakdown vises for (today/7d). Totaler for begge
    vinduer returneres altid. Self-safe — DB/read-fejl → skelet-dict."""
    if window not in _WINDOWS:
        window = "today"
    windows: dict = {}
    breakdown: list = []
    try:
        with connect() as conn:
            windows = {w: _agg_for_window(conn, w) for w in _WINDOWS}
            breakdown = _lane_breakdown(conn, window)
    except Exception:
        windows = {w: {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                       "cost_usd": 0.0} for w in _WINDOWS}
        breakdown = []
    try:
        dispatches = _dispatch_signal(_agents_trace())
    except Exception:
        dispatches = {"total": 0, "by_status": {}, "recent": []}
    roster = _roster()
    return {
        "windows": windows,
        "lane_breakdown": breakdown,
        "breakdown_window": window,
        "dispatches": {"total": dispatches["total"],
                       "by_status": dispatches["by_status"]},
        "recent": dispatches["recent"],
        "roster": roster,
        "note": "costs lane in (agent,council); dispatch-status fra agents-cluster-trace.",
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _roster() -> list[dict]:
    """Full model roster (every pool model as a row) fra core.services.agents.

    Self-safe: en roster-fejl må ALDRIG vælte /central/agents — falder tilbage til
    [] så den øvrige surface altid svarer. CLI'en konsumerer denne nøgle."""
    try:
        from core.services.agents import agents_summary
        roster = agents_summary().get("roster", [])
        return roster if isinstance(roster, list) else []
    except Exception:
        return []


def build_council_surface(*, window: str = "today") -> dict:
    """Council-observabilitet til /central/council + `jc council`.

    Læser agents-cluster council_session/council_convene-events: convocations,
    deadlocks, escalations, roller (recruited), event-vs-ondemand-split. Empty-safe
    (ingen council-data → zeros). Self-safe."""
    if window not in _WINDOWS:
        window = "today"
    convocations = deadlocks = escalations = 0
    roles: dict[str, int] = {}
    split = {"event": 0, "ondemand": 0}
    recent: list[dict] = []
    try:
        for r in _agents_trace():
            nerve = str(getattr(r, "nerve", ""))
            if nerve not in ("council_session", "council_convene"):
                continue
            p = getattr(r, "payload", None) or {}
            convocations += 1
            if p.get("deadlocked"):
                deadlocks += 1
            if p.get("escalated"):
                escalations += 1
            recruited = str(p.get("recruited") or "").strip()
            if recruited:
                roles[recruited] = roles.get(recruited, 0) + 1
            trigger = str(p.get("trigger") or "").strip().lower()
            if trigger in split:
                split[trigger] += 1
            elif trigger:
                split.setdefault(trigger, 0)
                split[trigger] += 1
            recent.append({
                "topic": str(p.get("topic") or "")[:80],
                "rounds": int(p.get("rounds") or 0),
                "deadlocked": bool(p.get("deadlocked")),
                "escalated": bool(p.get("escalated")),
                "recruited": recruited,
            })
    except Exception:
        pass
    recent.reverse()
    return {
        "convocations": convocations,
        "deadlocks": deadlocks,
        "escalations": escalations,
        "roles": roles,
        "split": split,
        "recent": recent[:20],
        "window": window,
        "note": "council_convene kan være tom indtil WS-C; håndteret empty-safe.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
