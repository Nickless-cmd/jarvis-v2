"""Mission Control endpoints for cheap_lane_balancer telemetry + controls.

Spec: docs/superpowers/plans/2026-05-02-cheap-lane-balancer.md
"""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/mc", tags=["mc-cheap-balancer"])


@router.get("/cheap-balancer-state")
def get_state() -> dict:
    """Return full snapshot: pool, slot states, recent calls."""
    from core.services.cheap_lane_balancer import balancer_snapshot
    return balancer_snapshot()


@router.post("/cheap-balancer/slot/{slot_id:path}/reset")
def reset(slot_id: str) -> dict:
    """Clear breaker, cooldown, and consecutive_failures for a slot."""
    from core.services.cheap_lane_balancer import reset_slot
    return reset_slot(slot_id)


@router.post("/cheap-balancer/slot/{slot_id:path}/disable")
def disable(slot_id: str) -> dict:
    """Force a slot's weight to 0 (excluded from selection until enabled)."""
    from core.services.cheap_lane_balancer import disable_slot
    return disable_slot(slot_id)


@router.post("/cheap-balancer/slot/{slot_id:path}/enable")
def enable(slot_id: str) -> dict:
    """Restore a manually-disabled slot to selection eligibility."""
    from core.services.cheap_lane_balancer import enable_slot
    return enable_slot(slot_id)


@router.post("/cheap-balancer/refresh-pool")
def refresh() -> dict:
    """Rebuild slot pool from provider_router.json."""
    from core.services.cheap_lane_balancer import refresh_pool
    return refresh_pool()


# ── Historik (16/9-2026) ──────────────────────────────────────────────────
# Balancerens snapshot viser NU. Disse tre viser FORLOEBET: hver eneste kald er
# bogfoert i `cheap_provider_invocations` (90.498 raekker, 32 % fejl), og intet
# endepunkt har nogensinde vist dem. Bjoern: «jeg ander intet om hvordan cheap
# lane klarer sig».

@router.get("/cheap-lane/history")
def history(timer: float = 24, lane: str = "cheap") -> dict:
    """Pr. udbyder+model i vinduet: kald, fejl, succesrate, latens, pris."""
    from core.services.cheap_lane_history import udbyder_historik
    return udbyder_historik(timer=timer, lane=lane)


@router.get("/cheap-lane/errors")
def errors(timer: float = 24, lane: str = "cheap", loft: int = 100) -> dict:
    """De nyeste fejl med besked. `antal_i_vinduet` taelles separat fra loftet."""
    from core.services.cheap_lane_history import seneste_fejl
    return seneste_fejl(timer=timer, lane=lane, loft=loft)


@router.get("/cheap-lane/timeseries")
def timeseries(timer: float = 24, lane: str = "cheap", spand_minutter: int = 60) -> dict:
    """Kald, fejl og latens pr. tidsspand."""
    from core.services.cheap_lane_history import tidsserie
    return tidsserie(timer=timer, lane=lane, spand_minutter=spand_minutter)
