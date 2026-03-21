from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from apps.api.jarvis_api.services.visible_model import (
    visible_capability_continuity_summary,
    visible_continuity_summary,
    visible_execution_readiness,
    visible_session_continuity_summary,
)
from apps.api.jarvis_api.services.non_visible_lane_execution import (
    cheap_lane_execution_truth,
    coding_lane_execution_truth,
    local_lane_execution_truth,
)
from apps.api.jarvis_api.services.visible_runs import (
    get_active_visible_run,
    get_last_visible_capability_use,
    get_last_visible_run_outcome,
    get_visible_selected_work_note,
    get_visible_selected_work_item,
    get_visible_selected_work_surface,
    get_visible_work,
    get_visible_work_surface,
)
from core.auth.profiles import get_provider_state, list_auth_profiles
from core.costing.ledger import recent_costs, telemetry_summary
from core.eventbus.bus import event_bus
from core.identity.visible_identity import load_visible_identity_summary
from core.memory.private_inner_interplay import build_private_inner_interplay
from core.memory.private_initiative_tension import build_private_initiative_tension
from core.memory.private_operational_preference import (
    build_private_operational_preference,
)
from core.memory.private_relation_state import build_private_relation_state
from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.memory.private_temporal_curiosity_state import (
    build_private_temporal_curiosity_state,
)
from core.runtime.config import (
    AUTH_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    LOG_DIR,
    PROVIDER_ROUTER_FILE,
    SETTINGS_FILE,
    STATE_DIR,
    WORKSPACES_DIR,
)
from core.runtime.operational_preference_alignment import (
    build_operational_preference_alignment,
)
from core.runtime.provider_router import provider_router_summary, select_main_agent_target
from core.runtime.db import (
    approve_capability_approval_request,
    connect,
    get_capability_approval_request,
    get_private_development_state,
    get_private_retained_memory_record,
    get_private_promotion_decision,
    get_private_temporal_promotion_signal,
    get_protected_inner_voice,
    get_private_state,
    get_private_self_model,
    record_capability_approval_request_execution,
    recent_capability_approval_requests,
    recent_capability_invocations,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_reflective_selections,
    recent_private_retained_memory_records,
    recent_visible_work_notes,
    recent_visible_work_units,
    recent_visible_runs,
)
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
        "visible_work": _visible_work_surface(),
        "visible_work_surface": get_visible_work_surface(),
        "visible_selected_work_surface": get_visible_selected_work_surface(),
        "visible_selected_work_item": get_visible_selected_work_item(),
        "visible_selected_work_note": get_visible_selected_work_note(),
        "visible_run": _visible_run_surface(),
        "workspace_capabilities": load_workspace_capabilities(),
        "provider_router": provider_router_summary(),
        "cheap_lane_execution": cheap_lane_execution_truth(),
        "coding_lane_execution": coding_lane_execution_truth(),
        "local_lane_execution": local_lane_execution_truth(),
        "capability_invocation": _capability_invocation_surface(),
        "private_inner_note": _private_inner_note_surface(),
        "private_growth_note": _private_growth_note_surface(),
        "private_self_model": _private_self_model_surface(),
        "private_reflective_selection": _private_reflective_selection_surface(),
        "private_development_state": _private_development_state_surface(),
        "private_state": _private_state_surface(),
        "protected_inner_voice": _protected_inner_voice_surface(),
        "private_inner_interplay": _private_inner_interplay_surface(),
        "private_initiative_tension": _private_initiative_tension_surface(),
        "private_operational_preference": _private_operational_preference_surface(),
        "operational_preference_alignment": _operational_preference_alignment_surface(),
        "private_relation_state": _private_relation_state_surface(),
        "private_temporal_curiosity_state": _private_temporal_curiosity_state_surface(),
        "private_temporal_promotion_signal": _private_temporal_promotion_signal_surface(),
        "private_promotion_decision": _private_promotion_decision_surface(),
        "private_retained_memory_record": _private_retained_memory_record_surface(),
        "private_retained_memory_projection": _private_retained_memory_projection_surface(),
        "paths": {
            "config_dir": _path_state(CONFIG_DIR),
            "settings_file": _path_state(SETTINGS_FILE),
            "provider_router_file": _path_state(PROVIDER_ROUTER_FILE),
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


@router.get("/main-agent-selection")
def mc_main_agent_selection() -> dict:
    return _main_agent_selection_surface()


@router.post("/workspace-capabilities/{capability_id}/invoke")
def mc_invoke_workspace_capability(capability_id: str, approved: bool = False) -> dict:
    result = invoke_workspace_capability(capability_id, approved=approved)
    return {
        "ok": result["status"] == "executed",
        **result,
    }


@router.post("/capability-approval-requests/{request_id}/approve")
def mc_approve_capability_request(request_id: str) -> dict:
    request = approve_capability_approval_request(
        request_id,
        approved_at=datetime.now(UTC).isoformat(),
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Capability approval request not found")
    return {
        "ok": True,
        "request": request,
    }


@router.post("/capability-approval-requests/{request_id}/execute")
def mc_execute_capability_request(request_id: str) -> dict:
    request = get_capability_approval_request(request_id)
    if request is None:
        return {
            "ok": False,
            "request_id": request_id,
            "status": "not-found",
            "detail": "Capability approval request not found",
            "request": None,
            "invocation": None,
        }
    if request.get("status") != "approved":
        return {
            "ok": False,
            "request_id": request_id,
            "status": "not-approved",
            "detail": "Capability approval request must be approved before execution",
            "request": request,
            "invocation": None,
        }

    invocation = invoke_workspace_capability(
        str(request.get("capability_id") or ""),
        approved=True,
        run_id=str(request.get("run_id") or "") or None,
    )
    projected_request = record_capability_approval_request_execution(
        request_id,
        executed_at=datetime.now(UTC).isoformat(),
        invocation_status=str(invocation.get("status") or ""),
        invocation_execution_mode=str(invocation.get("execution_mode") or ""),
    )
    return {
        "ok": invocation["status"] == "executed",
        "request_id": request_id,
        "status": invocation["status"],
        "request": projected_request or request,
        "invocation": invocation,
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


@router.put("/main-agent-selection")
def mc_update_main_agent_selection(payload: dict) -> dict:
    allowed_fields = {"provider", "model", "auth_profile"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported main agent selection fields: {', '.join(unknown_fields)}",
        )

    provider = payload.get("provider")
    model = payload.get("model")
    auth_profile = payload.get("auth_profile", "")

    if not isinstance(provider, str) or not provider.strip():
        raise HTTPException(status_code=400, detail="provider must be a non-empty string")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=400, detail="model must be a non-empty string")
    if not isinstance(auth_profile, str):
        raise HTTPException(status_code=400, detail="auth_profile must be a string")

    try:
        select_main_agent_target(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _main_agent_selection_surface()


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
        "visible_work": _visible_work_surface(),
        "visible_work_surface": get_visible_work_surface(),
        "visible_selected_work_surface": get_visible_selected_work_surface(),
        "visible_selected_work_item": get_visible_selected_work_item(),
        "visible_selected_work_note": get_visible_selected_work_note(),
        "workspace_capabilities": load_workspace_capabilities(),
        "provider_router": provider_router_summary(),
        "cheap_lane_execution": cheap_lane_execution_truth(),
        "coding_lane_execution": coding_lane_execution_truth(),
        "local_lane_execution": local_lane_execution_truth(),
        "capability_invocation": _capability_invocation_surface(),
        "private_inner_note": _private_inner_note_surface(),
        "private_growth_note": _private_growth_note_surface(),
        "private_self_model": _private_self_model_surface(),
        "private_reflective_selection": _private_reflective_selection_surface(),
        "private_development_state": _private_development_state_surface(),
        "private_state": _private_state_surface(),
        "protected_inner_voice": _protected_inner_voice_surface(),
        "private_inner_interplay": _private_inner_interplay_surface(),
        "private_initiative_tension": _private_initiative_tension_surface(),
        "private_operational_preference": _private_operational_preference_surface(),
        "operational_preference_alignment": _operational_preference_alignment_surface(),
        "private_relation_state": _private_relation_state_surface(),
        "private_temporal_curiosity_state": _private_temporal_curiosity_state_surface(),
        "private_temporal_promotion_signal": _private_temporal_promotion_signal_surface(),
        "private_promotion_decision": _private_promotion_decision_surface(),
        "private_retained_memory_record": _private_retained_memory_record_surface(),
        "private_retained_memory_projection": _private_retained_memory_projection_surface(),
        "supported_providers": list(SUPPORTED_VISIBLE_PROVIDERS),
        "available_auth_profiles": _available_openai_profiles(),
        "visible_run": _visible_run_surface(),
    }


def _main_agent_selection_surface() -> dict:
    provider_router = provider_router_summary()
    return {
        "selection": provider_router.get("main_agent_selection"),
        "target": provider_router.get("main_agent_target"),
        "provider_router": provider_router,
        "readiness": visible_execution_readiness(),
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


def _visible_work_surface() -> dict:
    return {
        **get_visible_work(),
        "persisted_recent_units": recent_visible_work_units(limit=5),
        "persisted_recent_notes": recent_visible_work_notes(limit=5),
    }


def _capability_invocation_surface() -> dict:
    truth = get_capability_invocation_truth()
    return {
        **truth,
        "persisted_recent_invocations": recent_capability_invocations(limit=5),
        "recent_approval_requests": recent_capability_approval_requests(limit=5),
        "recent_events": _recent_capability_invocation_events(),
    }


def _private_inner_note_surface() -> dict:
    notes = recent_private_inner_notes(limit=5)
    return {
        "active": bool(notes),
        "recent_notes": notes,
    }


def _private_growth_note_surface() -> dict:
    notes = recent_private_growth_notes(limit=5)
    return {
        "active": bool(notes),
        "recent_notes": notes,
    }


def _private_self_model_surface() -> dict:
    model = get_private_self_model()
    return {
        "active": bool(model),
        "current": model,
    }


def _private_reflective_selection_surface() -> dict:
    signals = recent_private_reflective_selections(limit=5)
    return {
        "active": bool(signals),
        "recent_signals": signals,
    }


def _private_development_state_surface() -> dict:
    state = get_private_development_state()
    return {
        "active": bool(state),
        "current": state,
    }


def _private_state_surface() -> dict:
    state = get_private_state()
    return {
        "active": bool(state),
        "current": state,
    }


def _protected_inner_voice_surface() -> dict:
    voice = get_protected_inner_voice()
    return {
        "active": bool(voice),
        "current": voice,
    }


def _private_inner_interplay_surface() -> dict:
    return build_private_inner_interplay(
        private_state=get_private_state(),
        protected_inner_voice=get_protected_inner_voice(),
        private_development_state=get_private_development_state(),
        private_reflective_selection=_latest_item(
            recent_private_reflective_selections(limit=1)
        ),
    )


def _private_initiative_tension_surface() -> dict:
    return build_private_initiative_tension(
        private_state=get_private_state(),
        protected_inner_voice=get_protected_inner_voice(),
        private_development_state=get_private_development_state(),
        private_reflective_selection=_latest_item(
            recent_private_reflective_selections(limit=1)
        ),
        private_temporal_promotion_signal=get_private_temporal_promotion_signal(),
        private_temporal_curiosity_state=_private_temporal_curiosity_state_surface().get(
            "current"
        ),
        private_retained_memory_projection=_private_retained_memory_projection_surface().get(
            "current"
        ),
    )


def _private_relation_state_surface() -> dict:
    return build_private_relation_state(
        visible_session_continuity=visible_session_continuity_summary(),
        visible_continuity=visible_continuity_summary(),
        visible_selected_work_item=get_visible_selected_work_item(),
        private_retained_memory_projection=_private_retained_memory_projection_surface().get(
            "current"
        ),
    )


def _private_operational_preference_surface() -> dict:
    return build_private_operational_preference(
        private_initiative_tension=_private_initiative_tension_surface().get("current"),
        private_temporal_curiosity_state=_private_temporal_curiosity_state_surface().get(
            "current"
        ),
        private_relation_state=_private_relation_state_surface().get("current"),
    )


def _operational_preference_alignment_surface() -> dict:
    provider_router = provider_router_summary()
    return build_operational_preference_alignment(
        private_operational_preference=_private_operational_preference_surface().get(
            "current"
        ),
        lane_targets=provider_router.get("lane_targets"),
    )


def _private_temporal_curiosity_state_surface() -> dict:
    return build_private_temporal_curiosity_state(
        private_state=get_private_state(),
        private_temporal_promotion_signal=get_private_temporal_promotion_signal(),
        private_development_state=get_private_development_state(),
    )


def _private_temporal_promotion_signal_surface() -> dict:
    signal = get_private_temporal_promotion_signal()
    return {
        "active": bool(signal),
        "current": signal,
    }


def _private_promotion_decision_surface() -> dict:
    decision = get_private_promotion_decision()
    return {
        "active": bool(decision),
        "current": decision,
    }


def _private_retained_memory_record_surface() -> dict:
    record = get_private_retained_memory_record()
    return {
        "active": bool(record),
        "current": record,
        "recent_records": recent_private_retained_memory_records(limit=5),
    }


def _private_retained_memory_projection_surface() -> dict:
    record = get_private_retained_memory_record()
    recent_records = recent_private_retained_memory_records(limit=5)
    return build_private_retained_memory_projection(
        current_record=record,
        recent_records=recent_records,
    )


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
