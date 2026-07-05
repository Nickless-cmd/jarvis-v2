"""Central-absorb routes — MC-kategorier PROJICERET som levende central-nerver.

Hver route her tager en eksisterende producent-service (den samme data som et
``/mc/*``-endpoint viser) og:

  1. **Projicerer** producentens surface uændret ud til owner (owner-gated).
  2. **Absorberer** en kompakt liveness-værdi som en levende central-nerve via
     ``central_absorb.absorb`` (fuld behandling: observe + trace + flag + notif
     + learning-hook).

Dette er første skridt i "Centralen absorberer ALT": hver MC-kategori flyttes
ind i Centralen som en nerve, før MC-delen afmonteres.

SELF-SAFE: en producent-fejl må aldrig vælte routen — den falder tilbage til en
tom liste og svarer 200. Owner-gaten håndhæves altid først.
"""
from __future__ import annotations

from fastapi import APIRouter

from apps.api.jarvis_api.routes.central_auth import require_central_owner
from core.services.central_absorb import absorb

router = APIRouter(prefix="/central", tags=["central-agents"])


@router.get("/agents")
async def get_agents() -> dict:
    """Projicér agent-runtime-surfacen (samme som ``/mc/agents``) + absorbér den.

    Owner-gated. Self-safe: producent-fejl → tom roster, stadig 200.
    """
    require_central_owner()

    try:
        from core.services.agent_runtime import build_agent_runtime_surface
        surface = build_agent_runtime_surface()
    except Exception:
        surface = {}

    if isinstance(surface, dict):
        agents = surface.get("agents")
    else:
        agents = surface
    agents = agents or []

    # Absorbér som levende nerve — tæller + flag hvis der ingen agenter er.
    absorb(
        "agent",
        "roster",
        {"count": len(agents)},
        flag_if=lambda v: v["count"] == 0,
        flag_reason="ingen aktive agenter",
    )

    return {"agents": agents, "count": len(agents)}


@router.get("/costs-daily")
async def get_costs_daily() -> dict:
    """Projicér cost-timeserien (samme data som ``/mc/costs``) + absorbér den.

    Owner-gated. Self-safe: hver producent-fejl → tom/nul-fallback, stadig 200.
    Absorberer en kompakt dags-omkostnings-værdi som en levende central-nerve og
    flagger hvis i dag > 150% af i går.
    """
    require_central_owner()

    from core.costing import ledger

    try:
        days = ledger.daily_cost_summary()
    except Exception:
        days = []
    if not isinstance(days, list):
        days = []

    try:
        today = float(ledger.today_cost())
    except Exception:
        today = 0.0

    try:
        week = float(ledger.this_week_cost())
    except Exception:
        week = 0.0

    try:
        summary = ledger.telemetry_summary()
    except Exception:
        summary = {}
    if not isinstance(summary, dict):
        summary = {}

    # Dag-over-dag: aggregér total_cost pr. dag (sum over lanes). ──────────────
    per_day: dict[str, float] = {}
    order: list[str] = []
    for row in days:
        if not isinstance(row, dict):
            continue
        day = row.get("day")
        if not isinstance(day, str):
            continue
        try:
            cost = float(row.get("total_cost") or 0.0)
        except Exception:
            cost = 0.0
        if day not in per_day:
            per_day[day] = 0.0
            order.append(day)
        per_day[day] += cost

    today_total = per_day[order[0]] if len(order) >= 1 else 0.0
    prev_total = per_day[order[1]] if len(order) >= 2 else 0.0

    absorb(
        "cost",
        "daily",
        {"today": today_total, "prev": prev_total, "usd_today": today},
        flag_if=lambda v: v["prev"] > 0 and v["today"] > v["prev"] * 1.5,
        flag_reason="dags-omkostning >150% af går",
        learn_key="cost_daily",
    )

    return {
        "days": days,
        "today_cost": today,
        "week_cost": week,
        "summary": summary,
        "today_total": today_total,
        "prev_total": prev_total,
    }
