from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.jarvis_api.services.visible_model import (
    visible_capability_continuity_summary,
    visible_continuity_summary,
    visible_execution_readiness,
    visible_session_continuity_summary,
)
from apps.api.jarvis_api.services.visible_runs import (
    get_active_visible_run,
    get_last_visible_capability_use,
    get_last_visible_run_outcome,
)
from core.auth.profiles import get_provider_state, list_auth_profiles
from core.costing.ledger import recent_costs, telemetry_summary
from core.eventbus.bus import event_bus
from core.identity.visible_identity import load_visible_identity_summary
from core.runtime.config import (
    AUTH_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    LOG_DIR,
    SETTINGS_FILE,
    STATE_DIR,
    WORKSPACES_DIR,
)
from core.runtime.db import connect, recent_capability_invocations, recent_visible_runs
from core.runtime.settings import load_settings, update_visible_execution_settings
from core.tools.workspace_capabilities import (
    get_capability_invocation_truth,
    invoke_workspace_capability,
    load_workspace_capabilities,
)

router = APIRouter(prefix="/mc", tags=["mission-control"])
SUPPORTED_VISIBLE_PROVIDERS = ("phase1-runtime", "openai")
VISIBLE_RUN_EVENT_KINDS = (
    "runtime.visible_run_started",
    "runtime.visible_run_completed",
    "runtime.visible_run_failed",
    "runtime.visible_run_cancelled",
)
CAPABILITY_INVOCATION_EVENT_KINDS = (
    "runtime.capability_invocation_started",
    "runtime.capability_invocation_completed",
)


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
        "visible_run": _visible_run_surface(),
        "capability_invocation": _capability_invocation_surface(),
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
        "visible_identity": load_visible_identity_summary(),
        "visible_session_continuity": visible_session_continuity_summary(),
        "visible_continuity": visible_continuity_summary(),
        "visible_capability_continuity": visible_capability_continuity_summary(),
        "visible_run": _visible_run_surface(),
        "workspace_capabilities": load_workspace_capabilities(),
        "capability_invocation": _capability_invocation_surface(),
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


@router.post("/workspace-capabilities/{capability_id}/invoke")
def mc_invoke_workspace_capability(capability_id: str, approved: bool = False) -> dict:
    result = invoke_workspace_capability(capability_id, approved=approved)
    return {
        "ok": result["status"] == "executed",
        **result,
    }


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
        if field == "visible_model_provider":
            if normalized not in SUPPORTED_VISIBLE_PROVIDERS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "visible_model_provider must be one of: "
                        + ", ".join(SUPPORTED_VISIBLE_PROVIDERS)
                    ),
                )
            updates[field] = normalized
            continue
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
        "visible_identity": load_visible_identity_summary(),
        "visible_session_continuity": visible_session_continuity_summary(),
        "visible_continuity": visible_continuity_summary(),
        "visible_capability_continuity": visible_capability_continuity_summary(),
        "workspace_capabilities": load_workspace_capabilities(),
        "capability_invocation": _capability_invocation_surface(),
        "supported_providers": list(SUPPORTED_VISIBLE_PROVIDERS),
        "available_auth_profiles": _available_openai_profiles(),
        "visible_run": _visible_run_surface(),
    }


def _available_openai_profiles() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for profile in list_auth_profiles():
        name = str(profile.get("profile", "")).strip()
        if not name:
            continue
        state = get_provider_state(profile=name, provider="openai")
        items.append(
            {
                "profile": name,
                "auth_status": str(state.get("status", "missing")) if state else "missing",
            }
        )
    return items


def _visible_run_surface() -> dict:
    active = get_active_visible_run()
    last_outcome = get_last_visible_run_outcome()
    return {
        "active": bool(active),
        "active_run": active,
        "last_outcome": last_outcome,
        "last_capability_use": get_last_visible_capability_use(),
        "persisted_recent_runs": recent_visible_runs(limit=5),
        "recent_events": _recent_visible_run_events(),
    }


def _capability_invocation_surface() -> dict:
    truth = get_capability_invocation_truth()
    return {
        **truth,
        "persisted_recent_invocations": recent_capability_invocations(limit=5),
        "recent_events": _recent_capability_invocation_events(),
    }


def _recent_visible_run_events(limit: int = 5, scan_limit: int = 40) -> list[dict]:
    items = event_bus.recent(limit=max(scan_limit, limit))
    visible_items = [item for item in items if item["kind"] in VISIBLE_RUN_EVENT_KINDS]
    return visible_items[:limit]


def _recent_capability_invocation_events(
    limit: int = 5, scan_limit: int = 40
) -> list[dict]:
    items = event_bus.recent(limit=max(scan_limit, limit))
    capability_items = [
        item for item in items if item["kind"] in CAPABILITY_INVOCATION_EVENT_KINDS
    ]
    return capability_items[:limit]
