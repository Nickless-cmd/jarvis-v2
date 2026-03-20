from __future__ import annotations

from fastapi import APIRouter

from core.eventbus.bus import event_bus
from core.runtime.db import connect

router = APIRouter(prefix="/mc", tags=["mission-control"])


@router.get("/overview")
def mc_overview() -> dict:
    with connect() as conn:
        event_count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        cost_count = conn.execute("SELECT COUNT(*) AS n FROM costs").fetchone()["n"]
        total_cost = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total_cost FROM costs"
        ).fetchone()["total_cost"]

    return {
        "ok": True,
        "events": int(event_count),
        "cost_rows": int(cost_count),
        "total_cost_usd": float(total_cost),
    }


@router.get("/events")
def mc_events(limit: int = 50) -> dict:
    return {"items": event_bus.recent(limit=limit)}
