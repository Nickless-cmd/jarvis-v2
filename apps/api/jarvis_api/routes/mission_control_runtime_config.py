"""Mission Control routes: adaptive/tool-intent, runtime-contract, heartbeat, visible-execution, capability-approval

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/adaptive-planner")
def mc_adaptive_planner() -> dict:
    """Return the current bounded adaptive planner runtime state."""
    return _mc_facade("build_adaptive_planner_runtime_surface")()


@router.get("/adaptive-reasoning")
def mc_adaptive_reasoning() -> dict:
    """Return the current bounded adaptive reasoning runtime state."""
    cached = _get_cached_mc_payload("adaptive-reasoning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = _mc_facade("build_adaptive_reasoning_runtime_surface")()
    return _store_cached_mc_payload("adaptive-reasoning", 10.0, payload)  # type: ignore[return-value]


@router.get("/guided-learning")
def mc_guided_learning() -> dict:
    """Return the current bounded guided learning runtime state."""
    cached = _get_cached_mc_payload("guided-learning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = _mc_facade("build_guided_learning_runtime_surface")()
    return _store_cached_mc_payload("guided-learning", 10.0, payload)  # type: ignore[return-value]


@router.get("/adaptive-learning")
def mc_adaptive_learning() -> dict:
    """Return the current bounded adaptive learning runtime state."""
    cached = _get_cached_mc_payload("adaptive-learning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = _mc_facade("build_adaptive_learning_runtime_surface")()
    return _store_cached_mc_payload("adaptive-learning", 10.0, payload)  # type: ignore[return-value]


@router.get("/self-system-code-awareness")
def mc_self_system_code_awareness() -> dict:
    """Return the current bounded self system / code awareness runtime state."""
    return _mc_facade("build_self_system_code_awareness_surface")()


@router.get("/tool-intent")
def mc_tool_intent() -> dict:
    """Return the current bounded approval-gated tool intent runtime state."""
    return _mc_facade("build_tool_intent_runtime_surface")()


@router.get("/approval-feedback")
def mc_approval_feedback() -> dict:
    """Return the approval-feedback surface (learning signal from past approvals/denials)."""
    return build_approval_feedback_surface()


@router.post("/tool-intent/approve")
def mc_approve_tool_intent() -> dict:
    """Approve the current pending tool intent from Mission Control.

    Resolves the active tool intent as approved (source "mc") and returns the
    resolved request plus the refreshed tool-intent surface. Raises 409 if the
    intent cannot be resolved.
    """
    tool_intent = _mc_facade("build_tool_intent_runtime_surface")()
    try:
        request = resolve_tool_intent_approval(
            tool_intent,
            approval_state="approved",
            approval_source="mc",
            resolution_reason="Explicit bounded Mission Control approval resolved the current tool intent.",
            resolution_message="Mission Control Operations approve control",
            session_id="mission-control-operations",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "request": request,
        "tool_intent": _mc_facade("build_tool_intent_runtime_surface")(),
    }


@router.post("/tool-intent/deny")
def mc_deny_tool_intent() -> dict:
    """Deny the current pending tool intent from Mission Control.

    Resolves the active tool intent as denied (source "mc") and returns the
    resolved request plus the refreshed tool-intent surface. Raises 409 if the
    intent cannot be resolved.
    """
    tool_intent = _mc_facade("build_tool_intent_runtime_surface")()
    try:
        request = resolve_tool_intent_approval(
            tool_intent,
            approval_state="denied",
            approval_source="mc",
            resolution_reason="Explicit bounded Mission Control denial resolved the current tool intent.",
            resolution_message="Mission Control Operations deny control",
            session_id="mission-control-operations",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "request": request,
        "tool_intent": _mc_facade("build_tool_intent_runtime_surface")(),
    }


@router.get("/private-brain")
def mc_private_brain() -> dict:
    """Return the private-brain overview plus recent session-distillation entries."""
    return {
        "private_brain": _mc_facade("build_private_brain_surface")(limit=30),
        "session_distillation": _mc_facade("build_session_distillation_surface")(limit=10),
    }


@router.get("/runtime-contract")
def mc_runtime_contract() -> dict:
    """Return the current runtime-contract state (active contract + candidates)."""
    return build_runtime_contract_state()


@router.get("/heartbeat")
def mc_heartbeat() -> dict:
    """Return the heartbeat runtime surface (current heartbeat state and policy)."""
    return heartbeat_runtime_surface()


@router.get("/emotional-memory")
def mc_emotional_memory(limit: int = 20) -> dict:
    """Closes cartographer dark-edge (2026-05-13): emotional_memory_engine
    had causal influence + protected agency/continuity reach but no MC
    surface. Now exposed as read-only overview."""
    from core.services.emotional_memory_engine import build_emotional_memory_overview
    return build_emotional_memory_overview(limit=limit)


@router.post("/heartbeat/tick")
def mc_heartbeat_tick() -> dict:
    """Manually trigger one heartbeat tick and return its resulting state/tick/policy."""
    result = run_heartbeat_tick(trigger="manual")
    return {
        "ok": True,
        "state": result.state,
        "tick": result.tick,
        "policy": result.policy,
    }


@router.post("/runtime-contract/candidates/{candidate_id}/approve")
def mc_approve_runtime_contract_candidate(candidate_id: str) -> dict:
    """Approve a runtime-contract candidate by id; returns the updated candidate. Raises 400 on invalid id."""
    try:
        candidate = approve_runtime_contract_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "candidate": candidate,
    }


@router.post("/runtime-contract/candidates/{candidate_id}/reject")
def mc_reject_runtime_contract_candidate(candidate_id: str) -> dict:
    """Reject a runtime-contract candidate by id; returns the updated candidate. Raises 400 on invalid id."""
    try:
        candidate = reject_runtime_contract_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "candidate": candidate,
    }


@router.post("/runtime-contract/candidates/{candidate_id}/apply")
def mc_apply_runtime_contract_candidate(candidate_id: str) -> dict:
    """Apply an approved runtime-contract candidate by id; returns the apply result. Raises 400 on invalid id."""
    try:
        result = apply_runtime_contract_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        **result,
    }


@router.get("/runtime")
def mc_runtime() -> dict:
    """Return the aggregate Mission Control runtime surface."""
    return _mc_runtime()


@router.get("/visible-execution")
def mc_visible_execution() -> dict:
    """Return the visible-execution surface (current visible model/provider/auth) from live settings."""
    settings = load_settings()
    return _visible_execution_surface(settings)


@router.get("/main-agent-selection")
def mc_main_agent_selection() -> dict:
    """Return the current main-agent selection surface (selected provider/model/auth profile)."""
    return _main_agent_selection_surface()


@router.get("/ollama-models")
def mc_ollama_models() -> dict:
    """Return the Ollama models available for use as the visible target."""
    return available_ollama_models_for_visible_target()


@router.get("/provider-models")
def mc_provider_models(provider: str = "", auth_profile: str = "") -> dict:
    """Return the models available for the given provider (optionally scoped to an auth profile).

    Raises 400 if provider is empty.
    """
    if not str(provider).strip():
        raise HTTPException(status_code=400, detail="provider must be a non-empty string")
    return _mc_facade("available_provider_models")(
        provider=str(provider).strip(),
        auth_profile=str(auth_profile or "").strip(),
    )


@router.post("/workspace-capabilities/{capability_id}/invoke")
def mc_invoke_workspace_capability(
    capability_id: str,
    approved: bool = False,
    write_content: str | None = None,
    target_path: str | None = None,
    command_text: str | None = None,
) -> dict:
    """Invoke a workspace capability by id, passing through the approval flag and optional
    write/target/command payload. Returns the invocation result with ok=True when executed."""
    result = invoke_workspace_capability(
        capability_id,
        approved=approved,
        write_content=write_content,
        target_path=target_path,
        command_text=command_text,
    )
    return {
        "ok": result["status"] == "executed",
        **result,
    }


@router.post("/capability-approval-requests/{request_id}/approve")
def mc_approve_capability_request(request_id: str) -> dict:
    """Approve a capability-approval request by id (stamping approved_at now).

    Returns the projected request; raises 404 if the request does not exist.
    """
    request = approve_capability_approval_request(
        request_id,
        approved_at=datetime.now(UTC).isoformat(),
    )
    if request is None:
        raise HTTPException(
            status_code=404, detail="Capability approval request not found"
        )
    return {
        "ok": True,
        "request": request,
    }


@router.post("/capability-approval-requests/{request_id}/execute")
def mc_execute_capability_request(
    request_id: str,
    write_content: str | None = None,
    command_text: str | None = None,
) -> dict:
    """Execute a previously approved capability-approval request.

    Requires the request to be approved (a pending sudo-exec proposal may be
    auto-approved if it falls within a reusable sudo approval window). Falls back
    to the stored proposal content when no write/command is supplied, verifies the
    supplied content against the approved proposal fingerprint, then invokes the
    capability and records the execution. Returns error dicts (not exceptions) for
    not-found / not-approved / fingerprint-mismatch cases.
    """
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
    reusable_sudo_window = None
    if request.get("status") != "approved":
        if (
            request.get("status") == "pending"
            and str(request.get("execution_mode") or "") == "sudo-exec-proposal"
        ):
            reusable_sudo_window = sudo_approval_window_allows_request(request)
            if reusable_sudo_window.get("allowed"):
                request = (
                    approve_capability_approval_request(
                        request_id,
                        approved_at=datetime.now(UTC).isoformat(),
                    )
                    or request
                )
        if request.get("status") == "approved":
            pass
        else:
            detail = "Capability approval request must be approved before execution"
            if reusable_sudo_window is not None:
                detail = str(reusable_sudo_window.get("detail") or detail)
            return {
                "ok": False,
                "request_id": request_id,
                "status": "not-approved",
                "detail": detail,
                "request": request,
                "invocation": None,
            }
    proposed_content = str(request.get("proposal_content") or "")
    proposed_fingerprint = str(request.get("proposal_content_fingerprint") or "")
    final_write_content = write_content
    final_command_text = command_text
    if proposed_content and final_write_content is None and final_command_text is None:
        if str(request.get("execution_mode") or "") == "workspace-file-write":
            final_write_content = proposed_content
        elif str(request.get("execution_mode") or "") in {
            "mutating-exec-proposal",
            "sudo-exec-proposal",
        }:
            final_command_text = proposed_content
    fingerprint_source = final_write_content
    if str(request.get("execution_mode") or "") in {
        "mutating-exec-proposal",
        "sudo-exec-proposal",
    }:
        fingerprint_source = final_command_text
    if proposed_fingerprint and fingerprint_source is not None:
        supplied_fingerprint = sha1(fingerprint_source.encode("utf-8")).hexdigest()[:16]
        if supplied_fingerprint != proposed_fingerprint:
            return {
                "ok": False,
                "request_id": request_id,
                "status": "proposal-content-mismatch",
                "detail": (
                    "Execution content does not match the approved bounded proposal content fingerprint."
                ),
                "request": request,
                "invocation": None,
            }

    invocation = invoke_workspace_capability(
        str(request.get("capability_id") or ""),
        approved=True,
        run_id=str(request.get("run_id") or "") or None,
        write_content=final_write_content,
        command_text=final_command_text,
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


@router.post("/development-focus/{focus_id}/complete")
def mc_complete_development_focus(focus_id: str) -> dict:
    """Manually mark a development focus as completed."""
    from core.eventbus.bus import event_bus

    updated = update_runtime_development_focus_status(
        focus_id=focus_id,
        status="completed",
        updated_at=datetime.now(UTC).isoformat(),
        status_reason="Manually marked completed by operator via Mission Control.",
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Development focus not found")

    event_bus.publish(
        "runtime.development_focus_completed",
        {
            "focus_id": updated.get("focus_id"),
            "focus_type": updated.get("focus_type"),
            "status": updated.get("status"),
            "summary": updated.get("summary"),
            "status_reason": updated.get("status_reason"),
            "actor": "operator",
        },
    )

    return {
        "ok": True,
        "focus": updated,
    }


@router.put("/visible-execution")
def mc_update_visible_execution(payload: dict) -> dict:
    """Update the visible-execution settings (visible model provider/name/auth profile).

    Rejects unknown fields, non-string or empty values, unsupported providers, and
    auth-profile names containing path separators (all raise 400). Returns the
    refreshed visible-execution surface.
    """
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
    """Select the main-agent target (provider/model, optional auth_profile).

    Rejects unknown fields and missing/empty provider or model (400). If selection
    fails, attempts to configure the target live and retries once. Returns the
    refreshed main-agent selection surface.
    """
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
        raise HTTPException(
            status_code=400, detail="provider must be a non-empty string"
        )
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
        if _maybe_configure_live_main_agent_target(
            provider=str(provider).strip(),
            model=str(model).strip(),
            auth_profile=str(auth_profile or "").strip(),
        ):
            try:
                select_main_agent_target(
                    provider=provider,
                    model=model,
                    auth_profile=auth_profile,
                )
            except ValueError as nested_exc:
                raise HTTPException(
                    status_code=400, detail=str(nested_exc)
                ) from nested_exc
            return _main_agent_selection_surface()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _main_agent_selection_surface()


