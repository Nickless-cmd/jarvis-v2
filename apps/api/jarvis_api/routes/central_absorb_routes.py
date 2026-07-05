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
