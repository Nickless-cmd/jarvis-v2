from __future__ import annotations


def visible_execution_section(
    visible_execution: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "visible_execution_source": source,
        "visible_execution_api_unavailable": api_unavailable,
        "authority": normalize_visible_authority(visible_execution.get("authority")),
        "readiness": normalize_visible_readiness(visible_execution.get("readiness")),
        "visible_identity": normalize_visible_identity(
            visible_execution.get("visible_identity")
        ),
        "visible_work": normalize_visible_work(visible_execution.get("visible_work")),
        "visible_work_surface": normalize_visible_work_surface(
            visible_execution.get("visible_work_surface")
        ),
        "visible_selected_work_surface": normalize_visible_selected_work_surface(
            visible_execution.get("visible_selected_work_surface")
        ),
        "visible_selected_work_item": normalize_visible_selected_work_item(
            visible_execution.get("visible_selected_work_item")
        ),
        "visible_session_continuity": normalize_visible_session_continuity(
            visible_execution.get("visible_session_continuity")
        ),
        "visible_continuity": normalize_visible_continuity(
            visible_execution.get("visible_continuity")
        ),
        "visible_capability_continuity": normalize_visible_capability_continuity(
            visible_execution.get("visible_capability_continuity")
        ),
    }


def visible_run_section(
    visible_run: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "visible_run_source": source,
        "visible_run_api_unavailable": api_unavailable,
        "active": bool(visible_run.get("active")),
        "active_run": normalize_active_run(visible_run.get("active_run")),
        "last_outcome": normalize_last_outcome(visible_run.get("last_outcome")),
        "last_capability_use": normalize_visible_capability_use(
            visible_run.get("last_capability_use")
        ),
        "persisted_recent_runs": normalize_persisted_recent_runs(
            visible_run.get("persisted_recent_runs")
        ),
        "recent_events": visible_run.get("recent_events", []),
    }


def capability_invocation_section(
    capability_invocation: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "capability_invocation_source": source,
        "capability_invocation_api_unavailable": api_unavailable,
        "active": bool(capability_invocation.get("active")),
        "last_invocation": normalize_capability_invocation(
            capability_invocation.get("last_invocation")
        ),
        "persisted_recent_invocations": normalize_persisted_capability_invocations(
            capability_invocation.get("persisted_recent_invocations")
        ),
        "recent_approval_requests": normalize_approval_requests(
            capability_invocation.get("recent_approval_requests")
        ),
        "recent_events": capability_invocation.get("recent_events", []),
    }


def normalize_visible_authority(authority: dict | None) -> dict:
    authority = authority or {}
    return {
        "visible_model_provider": authority.get("visible_model_provider"),
        "visible_model_name": authority.get("visible_model_name"),
        "visible_auth_profile": authority.get("visible_auth_profile"),
    }


def normalize_visible_readiness(readiness: dict | None) -> dict:
    readiness = readiness or {}
    return {
        "provider": readiness.get("provider"),
        "model": readiness.get("model"),
        "mode": readiness.get("mode"),
        "auth_ready": readiness.get("auth_ready"),
        "auth_status": readiness.get("auth_status"),
        "auth_profile": readiness.get("auth_profile"),
        "provider_reachable": readiness.get("provider_reachable"),
        "live_verified": readiness.get("live_verified"),
        "provider_status": readiness.get("provider_status"),
        "probe_cache": readiness.get("probe_cache"),
        "checked_at": readiness.get("checked_at"),
    }


def normalize_visible_identity(visible_identity: dict | None) -> dict:
    visible_identity = visible_identity or {}
    return {
        "workspace": visible_identity.get("workspace"),
        "name": visible_identity.get("name"),
        "active": bool(visible_identity.get("active")),
        "source_files": list(visible_identity.get("source_files") or []),
        "extracted_line_count": visible_identity.get("extracted_line_count"),
        "prompt_chars": visible_identity.get("prompt_chars"),
        "fingerprint": visible_identity.get("fingerprint"),
    }


def normalize_visible_work(visible_work: dict | None) -> dict:
    visible_work = visible_work or {}
    return {
        "active": bool(visible_work.get("active")),
        "run_id": visible_work.get("run_id"),
        "status": visible_work.get("status"),
        "lane": visible_work.get("lane"),
        "provider": visible_work.get("provider"),
        "model": visible_work.get("model"),
        "started_at": visible_work.get("started_at"),
        "current_user_message_preview": visible_work.get("current_user_message_preview"),
        "capability_id": visible_work.get("capability_id"),
        "persisted_recent_units": normalize_visible_work_units(
            visible_work.get("persisted_recent_units")
        ),
        "persisted_recent_notes": normalize_visible_work_notes(
            visible_work.get("persisted_recent_notes")
        ),
    }


def normalize_visible_work_units(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "work_id": item.get("work_id"),
                "run_id": item.get("run_id"),
                "status": item.get("status"),
                "finished_at": item.get("finished_at"),
                "user_message_preview": item.get("user_message_preview"),
                "capability_id": item.get("capability_id"),
                "work_preview": item.get("work_preview"),
            }
        )
    return normalized


def normalize_visible_work_notes(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "note_id": item.get("note_id"),
                "work_id": item.get("work_id"),
                "run_id": item.get("run_id"),
                "status": item.get("status"),
                "user_message_preview": item.get("user_message_preview"),
                "capability_id": item.get("capability_id"),
                "work_preview": item.get("work_preview"),
                "projection_source": item.get("projection_source"),
                "finished_at": item.get("finished_at"),
            }
        )
    return normalized


def normalize_visible_work_surface(visible_work_surface: dict | None) -> dict:
    visible_work_surface = visible_work_surface or {}
    return {
        "active": bool(visible_work_surface.get("active")),
        "current_work_id": visible_work_surface.get("current_work_id"),
        "current_run_id": visible_work_surface.get("current_run_id"),
        "status": visible_work_surface.get("status"),
        "lane": visible_work_surface.get("lane"),
        "provider": visible_work_surface.get("provider"),
        "model": visible_work_surface.get("model"),
        "started_at": visible_work_surface.get("started_at"),
        "finished_at": visible_work_surface.get("finished_at"),
        "current_user_message_preview": visible_work_surface.get(
            "current_user_message_preview"
        ),
        "capability_id": visible_work_surface.get("capability_id"),
        "recent_work_ids": list(visible_work_surface.get("recent_work_ids") or []),
        "latest_work_preview": visible_work_surface.get("latest_work_preview"),
    }


def normalize_visible_selected_work_surface(
    visible_selected_work_surface: dict | None,
) -> dict:
    visible_selected_work_surface = visible_selected_work_surface or {}
    return {
        "active": bool(visible_selected_work_surface.get("active")),
        "selected_work_id": visible_selected_work_surface.get("selected_work_id"),
        "selected_run_id": visible_selected_work_surface.get("selected_run_id"),
        "status": visible_selected_work_surface.get("status"),
        "lane": visible_selected_work_surface.get("lane"),
        "provider": visible_selected_work_surface.get("provider"),
        "model": visible_selected_work_surface.get("model"),
        "selected_user_message_preview": visible_selected_work_surface.get(
            "selected_user_message_preview"
        ),
        "selected_capability_id": visible_selected_work_surface.get(
            "selected_capability_id"
        ),
        "selected_work_preview": visible_selected_work_surface.get(
            "selected_work_preview"
        ),
        "recent_work_ids": list(
            visible_selected_work_surface.get("recent_work_ids") or []
        ),
    }


def normalize_visible_selected_work_item(
    visible_selected_work_item: dict | None,
) -> dict:
    visible_selected_work_item = visible_selected_work_item or {}
    return {
        "active": bool(visible_selected_work_item.get("active")),
        "selected_work_id": visible_selected_work_item.get("selected_work_id"),
        "selected_run_id": visible_selected_work_item.get("selected_run_id"),
        "selected_status": visible_selected_work_item.get("selected_status"),
        "selected_lane": visible_selected_work_item.get("selected_lane"),
        "selected_provider": visible_selected_work_item.get("selected_provider"),
        "selected_model": visible_selected_work_item.get("selected_model"),
        "selected_user_message_preview": visible_selected_work_item.get(
            "selected_user_message_preview"
        ),
        "selected_capability_id": visible_selected_work_item.get(
            "selected_capability_id"
        ),
        "selected_work_preview": visible_selected_work_item.get(
            "selected_work_preview"
        ),
        "recent_work_ids": list(visible_selected_work_item.get("recent_work_ids") or []),
        "selection_source": visible_selected_work_item.get("selection_source"),
        "recent_count": visible_selected_work_item.get("recent_count"),
    }


def normalize_visible_continuity(visible_continuity: dict | None) -> dict:
    visible_continuity = visible_continuity or {}
    return {
        "active": bool(visible_continuity.get("active")),
        "source": visible_continuity.get("source"),
        "included_rows": visible_continuity.get("included_rows"),
        "included_run_ids": list(visible_continuity.get("included_run_ids") or []),
        "statuses": list(visible_continuity.get("statuses") or []),
        "preview_count": visible_continuity.get("preview_count"),
        "error_count": visible_continuity.get("error_count"),
        "capability_count": visible_continuity.get("capability_count"),
        "chars": visible_continuity.get("chars"),
    }


def normalize_visible_session_continuity(
    visible_session_continuity: dict | None,
) -> dict:
    visible_session_continuity = visible_session_continuity or {}
    return {
        "active": bool(visible_session_continuity.get("active")),
        "source": visible_session_continuity.get("source"),
        "latest_run_id": visible_session_continuity.get("latest_run_id"),
        "latest_status": visible_session_continuity.get("latest_status"),
        "latest_finished_at": visible_session_continuity.get("latest_finished_at"),
        "latest_text_preview": visible_session_continuity.get("latest_text_preview"),
        "latest_capability_id": visible_session_continuity.get("latest_capability_id"),
        "recent_capability_ids": list(
            visible_session_continuity.get("recent_capability_ids") or []
        ),
        "recent_run_summaries": list(
            visible_session_continuity.get("recent_run_summaries") or []
        ),
        "included_run_rows": visible_session_continuity.get("included_run_rows"),
        "included_capability_rows": visible_session_continuity.get(
            "included_capability_rows"
        ),
        "chars": visible_session_continuity.get("chars"),
    }


def normalize_visible_capability_continuity(
    visible_capability_continuity: dict | None,
) -> dict:
    visible_capability_continuity = visible_capability_continuity or {}
    return {
        "active": bool(visible_capability_continuity.get("active")),
        "source": visible_capability_continuity.get("source"),
        "included_rows": visible_capability_continuity.get("included_rows"),
        "included_capability_ids": list(
            visible_capability_continuity.get("included_capability_ids") or []
        ),
        "statuses": list(visible_capability_continuity.get("statuses") or []),
        "preview_count": visible_capability_continuity.get("preview_count"),
        "detail_count": visible_capability_continuity.get("detail_count"),
        "chars": visible_capability_continuity.get("chars"),
    }


def normalize_active_run(active_run: dict | None) -> dict | None:
    if not active_run:
        return None
    return {
        "run_id": active_run.get("run_id"),
        "lane": active_run.get("lane"),
        "provider": active_run.get("provider"),
        "model": active_run.get("model"),
        "started_at": active_run.get("started_at"),
        "cancelled": active_run.get("cancelled"),
    }


def normalize_last_outcome(last_outcome: dict | None) -> dict | None:
    if not last_outcome:
        return None
    return {
        "run_id": last_outcome.get("run_id"),
        "lane": last_outcome.get("lane"),
        "provider": last_outcome.get("provider"),
        "model": last_outcome.get("model"),
        "status": last_outcome.get("status"),
        "finished_at": last_outcome.get("finished_at"),
        "error": last_outcome.get("error"),
        "text_preview": last_outcome.get("text_preview"),
    }


def normalize_capability_invocation(last_invocation: dict | None) -> dict | None:
    if not last_invocation:
        return None
    return {
        "capability_id": last_invocation.get("capability_id"),
        "capability": last_invocation.get("capability"),
        "status": last_invocation.get("status"),
        "execution_mode": last_invocation.get("execution_mode"),
        "approval": normalize_approval(last_invocation.get("approval")),
        "invoked_at": last_invocation.get("invoked_at"),
        "finished_at": last_invocation.get("finished_at"),
        "result_preview": last_invocation.get("result_preview"),
        "detail": last_invocation.get("detail"),
        "run_id": last_invocation.get("run_id"),
    }


def normalize_persisted_capability_invocations(
    items: list[dict] | None,
) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "capability_id": item.get("capability_id"),
                "capability_name": item.get("capability_name"),
                "capability_kind": item.get("capability_kind"),
                "status": item.get("status"),
                "execution_mode": item.get("execution_mode"),
                "approval": normalize_approval(item.get("approval")),
                "invoked_at": item.get("invoked_at"),
                "finished_at": item.get("finished_at"),
                "result_preview": item.get("result_preview"),
                "detail": item.get("detail"),
                "run_id": item.get("run_id"),
            }
        )
    return normalized


def normalize_approval_requests(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "request_id": item.get("request_id"),
                "capability_id": item.get("capability_id"),
                "capability_name": item.get("capability_name"),
                "capability_kind": item.get("capability_kind"),
                "execution_mode": item.get("execution_mode"),
                "approval_policy": item.get("approval_policy"),
                "run_id": item.get("run_id"),
                "requested_at": item.get("requested_at"),
                "status": item.get("status"),
                "approved_at": item.get("approved_at"),
                "executed": bool(item.get("executed")),
                "executed_at": item.get("executed_at"),
                "invocation_status": item.get("invocation_status"),
                "invocation_execution_mode": item.get("invocation_execution_mode"),
            }
        )
    return normalized


def normalize_approval(approval: dict | None) -> dict | None:
    if not approval:
        return None
    return {
        "policy": approval.get("policy"),
        "required": bool(approval.get("required")),
        "approved": bool(approval.get("approved")),
        "granted": bool(approval.get("granted")),
    }


def normalize_visible_capability_use(last_capability_use: dict | None) -> dict | None:
    if not last_capability_use:
        return None
    return {
        "run_id": last_capability_use.get("run_id"),
        "lane": last_capability_use.get("lane"),
        "provider": last_capability_use.get("provider"),
        "model": last_capability_use.get("model"),
        "capability_id": last_capability_use.get("capability_id"),
        "capability": last_capability_use.get("capability"),
        "status": last_capability_use.get("status"),
        "execution_mode": last_capability_use.get("execution_mode"),
        "used_at": last_capability_use.get("used_at"),
        "result_preview": last_capability_use.get("result_preview"),
        "detail": last_capability_use.get("detail"),
    }


def normalize_persisted_recent_runs(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "run_id": item.get("run_id"),
                "lane": item.get("lane"),
                "provider": item.get("provider"),
                "model": item.get("model"),
                "status": item.get("status"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "text_preview": item.get("text_preview"),
                "error": item.get("error"),
                "capability_id": item.get("capability_id"),
            }
        )
    return normalized
