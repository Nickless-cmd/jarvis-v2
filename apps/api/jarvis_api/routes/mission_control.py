from __future__ import annotations

from fastapi import APIRouter

from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from core.costing.ledger import recent_costs, telemetry_summary
from core.eventbus.bus import event_bus
from core.runtime.config import (
    AUTH_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    LOG_DIR,
    SETTINGS_FILE,
    STATE_DIR,
    WORKSPACES_DIR,
)
from core.runtime.db import connect
from core.runtime.settings import load_settings

router = APIRouter(prefix="/mc", tags=["mission-control"])


@router.get("/overview")
def mc_overview() -> dict:
    with connect() as conn:
        event_count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    costs = telemetry_summary()
    latest_event = _latest_item(event_bus.recent(limit=1))
    latest_cost = _latest_item(recent_costs(limit=1))
    settings = load_settings()
    visible = visible_execution_readiness()

    return {
        "ok": True,
        "events": int(event_count),
        "cost_rows": costs["cost_rows"],
        "input_tokens": costs["input_tokens"],
        "output_tokens": costs["output_tokens"],
        "total_cost_usd": costs["total_cost_usd"],
        "runtime": {
            "app": settings.app_name,
            "environment": settings.environment,
            "host": settings.host,
            "port": settings.port,
            "settings_path": str(SETTINGS_FILE),
            "state_dir": str(STATE_DIR),
            "workspaces_dir": str(WORKSPACES_DIR),
        },
        "visible_execution": visible,
        "latest_event": latest_event,
        "latest_cost": latest_cost,
    }


@router.get("/events")
def mc_events(limit: int = 50, family: str | None = None) -> dict:
    items = event_bus.recent(limit=max(limit, 1))
    if family:
        items = [item for item in items if item["family"] == family]
        items = items[:limit]
    return {
        "items": items,
        "meta": {
            "limit": limit,
            "family": family,
            "returned": len(items),
        },
    }


@router.get("/costs")
def mc_costs(limit: int = 50) -> dict:
    return {
        "summary": telemetry_summary(),
        "items": recent_costs(limit=limit),
    }


@router.get("/runtime")
def mc_runtime() -> dict:
    settings = load_settings()
    return {
        "settings": settings.to_dict(),
        "visible_execution": visible_execution_readiness(),
        "paths": {
            "config_dir": _path_state(CONFIG_DIR),
            "settings_file": _path_state(SETTINGS_FILE),
            "state_dir": _path_state(STATE_DIR),
            "log_dir": _path_state(LOG_DIR),
            "cache_dir": _path_state(CACHE_DIR),
            "auth_dir": _path_state(AUTH_DIR),
            "workspaces_dir": _path_state(WORKSPACES_DIR),
        },
    }


def _latest_item(items: list[dict]) -> dict | None:
    return items[0] if items else None


def _path_state(path) -> dict[str, str | bool]:
    return {
        "path": str(path),
        "exists": path.exists(),
    }
