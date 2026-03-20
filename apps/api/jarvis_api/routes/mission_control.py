from __future__ import annotations

from fastapi import APIRouter

from core.costing.ledger import recent_costs, telemetry_summary
from core.eventbus.bus import event_bus
from core.runtime.db import connect

router = APIRouter(prefix="/mc", tags=["mission-control"])


@router.get("/overview")
def mc_overview() -> dict:
    with connect() as conn:
        event_count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    costs = telemetry_summary()

    return {
        "ok": True,
        "events": int(event_count),
        "cost_rows": costs["cost_rows"],
        "input_tokens": costs["input_tokens"],
        "output_tokens": costs["output_tokens"],
        "total_cost_usd": costs["total_cost_usd"],
    }


@router.get("/events")
def mc_events(limit: int = 50) -> dict:
    return {"items": event_bus.recent(limit=limit)}


@router.get("/costs")
def mc_costs(limit: int = 50) -> dict:
    return {"items": recent_costs(limit=limit)}
