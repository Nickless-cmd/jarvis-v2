from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
from core.runtime.settings import load_settings, update_visible_execution_settings

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


@router.get("/visible-execution")
def mc_visible_execution() -> dict:
    settings = load_settings()
    return _visible_execution_surface(settings)


@router.put("/visible-execution")
def mc_update_visible_execution(payload: dict) -> dict:
    allowed_fields = {
        "visible_model_provider",
        "visible_model_name",
        "visible_auth_profile",
    }
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported visible execution fields: {', '.join(unknown_fields)}",
        )

    updates: dict[str, str] = {}
    for field in allowed_fields:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"{field} must be a string")
        normalized = value.strip()
        if field in {"visible_model_provider", "visible_model_name"} and not normalized:
            raise HTTPException(status_code=400, detail=f"{field} must not be empty")
        if field == "visible_auth_profile":
            if any(part in normalized for part in ("/", "\\")):
                raise HTTPException(
                    status_code=400,
                    detail="visible_auth_profile must be a simple profile name",
                )
            updates[field] = normalized
            continue
        updates[field] = normalized

    settings = update_visible_execution_settings(**updates)
    return _visible_execution_surface(settings)


def _latest_item(items: list[dict]) -> dict | None:
    return items[0] if items else None


def _path_state(path) -> dict[str, str | bool]:
    return {
        "path": str(path),
        "exists": path.exists(),
    }


def _visible_execution_surface(settings) -> dict:
    return {
        "authority": {
            "visible_model_provider": settings.visible_model_provider,
            "visible_model_name": settings.visible_model_name,
            "visible_auth_profile": settings.visible_auth_profile,
        },
        "readiness": visible_execution_readiness(),
    }
