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
