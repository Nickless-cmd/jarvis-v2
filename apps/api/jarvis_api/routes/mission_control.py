from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from apps.api.jarvis_api.services.visible_model import (
    available_ollama_models_for_visible_target,
    visible_capability_continuity_summary,
    visible_continuity_summary,
    visible_execution_readiness,
    visible_session_continuity_summary,
)
from apps.api.jarvis_api.services.prompt_contract import (
    build_runtime_inner_visible_prompt_bridge_surface,
    build_runtime_memory_selection_surface,
    build_runtime_relevance_decision_surface,
)
from apps.api.jarvis_api.services.non_visible_lane_execution import (
    cheap_lane_execution_truth,
    coding_lane_execution_truth,
    local_lane_execution_truth,
)
from apps.api.jarvis_api.services.heartbeat_runtime import (
    heartbeat_runtime_surface,
    run_heartbeat_tick,
)
from apps.api.jarvis_api.services.development_focus_tracking import (
    build_runtime_development_focus_surface,
)
from apps.api.jarvis_api.services.reflective_critic_tracking import (
    build_runtime_reflective_critic_surface,
)
from apps.api.jarvis_api.services.self_model_signal_tracking import (
    build_runtime_self_model_signal_surface,
)
from apps.api.jarvis_api.services.goal_signal_tracking import (
    build_runtime_goal_signal_surface,
)
from apps.api.jarvis_api.services.world_model_signal_tracking import (
    build_runtime_world_model_signal_surface,
)
from apps.api.jarvis_api.services.runtime_awareness_signal_tracking import (
    build_runtime_awareness_signal_surface,
)
from apps.api.jarvis_api.services.reflection_signal_tracking import (
    build_runtime_reflection_signal_surface,
)
from apps.api.jarvis_api.services.temporal_recurrence_signal_tracking import (
    build_runtime_temporal_recurrence_signal_surface,
)
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from apps.api.jarvis_api.services.self_review_signal_tracking import (
    build_runtime_self_review_signal_surface,
)
from apps.api.jarvis_api.services.self_review_record_tracking import (
    build_runtime_self_review_record_surface,
)
from apps.api.jarvis_api.services.self_review_run_tracking import (
    build_runtime_self_review_run_surface,
)
from apps.api.jarvis_api.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from apps.api.jarvis_api.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from apps.api.jarvis_api.services.dream_hypothesis_signal_tracking import (
    build_runtime_dream_hypothesis_signal_surface,
)
from apps.api.jarvis_api.services.dream_adoption_candidate_tracking import (
    build_runtime_dream_adoption_candidate_surface,
)
from apps.api.jarvis_api.services.dream_influence_proposal_tracking import (
    build_runtime_dream_influence_proposal_surface,
)
from apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking import (
    build_runtime_self_authored_prompt_proposal_surface,
)
from apps.api.jarvis_api.services.user_understanding_signal_tracking import (
    build_runtime_user_understanding_signal_surface,
)
from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from apps.api.jarvis_api.services.private_inner_note_signal_tracking import (
    build_runtime_private_inner_note_signal_surface,
)
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from apps.api.jarvis_api.services.private_inner_interplay_signal_tracking import (
    build_runtime_private_inner_interplay_signal_surface,
)
from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from apps.api.jarvis_api.services.private_temporal_curiosity_state_tracking import (
    build_runtime_private_temporal_curiosity_state_surface,
)
from apps.api.jarvis_api.services.inner_visible_support_signal_tracking import (
    build_runtime_inner_visible_support_signal_surface,
)
from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from apps.api.jarvis_api.services.relation_state_signal_tracking import (
    build_runtime_relation_state_signal_surface,
)
from apps.api.jarvis_api.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from apps.api.jarvis_api.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from apps.api.jarvis_api.services.temperament_tendency_signal_tracking import (
    build_runtime_temperament_tendency_signal_surface,
)
from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from apps.api.jarvis_api.services.chronicle_consolidation_signal_tracking import (
    build_runtime_chronicle_consolidation_signal_surface,
)
from apps.api.jarvis_api.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from apps.api.jarvis_api.services.chronicle_consolidation_proposal_tracking import (
    build_runtime_chronicle_consolidation_proposal_surface,
)
from apps.api.jarvis_api.services.user_md_update_proposal_tracking import (
    build_runtime_user_md_update_proposal_surface,
)
from apps.api.jarvis_api.services.memory_md_update_proposal_tracking import (
    build_runtime_memory_md_update_proposal_surface,
)
from apps.api.jarvis_api.services.selfhood_proposal_tracking import (
    build_runtime_selfhood_proposal_surface,
)
from apps.api.jarvis_api.services.open_loop_closure_proposal_tracking import (
    build_runtime_open_loop_closure_proposal_surface,
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
from core.identity.runtime_contract import build_runtime_contract_state
from core.identity.candidate_workflow import (
    apply_runtime_contract_candidate,
    approve_runtime_contract_candidate,
    reject_runtime_contract_candidate,
)
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
from core.runtime.provider_router import (
    configure_provider_router_entry,
    provider_router_summary,
    resolve_provider_router_target,
    select_main_agent_target,
)
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
    update_runtime_development_focus_status,
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


@router.get("/runs")
def mc_runs(limit: int = 20) -> dict:
    surface = _visible_run_surface()
    work = _visible_work_surface()
    recent_runs = list(surface.get("persisted_recent_runs") or [])[: max(limit, 1)]
    failed_runs = [
        item
        for item in recent_runs
        if str(item.get("status") or "") in {"failed", "cancelled"}
    ]
    return {
        "active_run": surface.get("active_run"),
        "last_outcome": surface.get("last_outcome"),
        "last_capability_use": surface.get("last_capability_use"),
        "recent_runs": recent_runs,
        "recent_events": list(surface.get("recent_events") or []),
        "recent_work_units": list(work.get("persisted_recent_units") or [])[:8],
        "recent_work_notes": list(work.get("persisted_recent_notes") or [])[:8],
        "summary": {
            "active": bool(surface.get("active")),
            "recent_count": len(recent_runs),
            "failed_count": len(failed_runs),
        },
    }


@router.get("/approvals")
def mc_approvals(limit: int = 20) -> dict:
    surface = _capability_invocation_surface()
    requests = list(surface.get("recent_approval_requests") or [])[: max(limit, 1)]
    pending = [item for item in requests if str(item.get("status") or "") == "pending"]
    approved = [
        item for item in requests if str(item.get("status") or "") == "approved"
    ]
    return {
        "requests": requests,
        "recent_invocations": list(surface.get("persisted_recent_invocations") or [])[
            : max(limit, 1)
        ],
        "recent_events": list(surface.get("recent_events") or []),
        "summary": {
            "pending_count": len(pending),
            "approved_count": len(approved),
            "request_count": len(requests),
        },
    }


@router.get("/jarvis")
def mc_jarvis() -> dict:
    visible_identity = load_visible_identity_summary()
    visible_session = visible_session_continuity_summary()
    visible_continuity = visible_continuity_summary()
    visible_capability = visible_capability_continuity_summary()
    private_state = _private_state_surface()
    protected_voice = _protected_inner_voice_surface()
    inner_interplay = _private_inner_interplay_surface()
    initiative_tension = _private_initiative_tension_surface()
    relation_state = _private_relation_state_surface()
    temporal_curiosity = _private_temporal_curiosity_state_surface()
    promotion_signal = _private_temporal_promotion_signal_surface()
    promotion_decision = _private_promotion_decision_surface()
    retained_record = _private_retained_memory_record_surface()
    retained_projection = _private_retained_memory_projection_surface()
    self_model = _private_self_model_surface()
    development_state = _private_development_state_surface()
    growth_note = _private_growth_note_surface()
    reflective = _private_reflective_selection_surface()
    operational_preference = _private_operational_preference_surface()
    operational_alignment = _operational_preference_alignment_surface()
    development_focuses = build_runtime_development_focus_surface()
    reflective_critics = build_runtime_reflective_critic_surface()
    self_model_signals = build_runtime_self_model_signal_surface()
    goal_signals = build_runtime_goal_signal_surface()
    reflection_signals = build_runtime_reflection_signal_surface()
    temporal_recurrence_signals = build_runtime_temporal_recurrence_signal_surface()
    witness_signals = build_runtime_witness_signal_surface()
    open_loop_signals = build_runtime_open_loop_signal_surface()
    open_loop_closure_proposals = build_runtime_open_loop_closure_proposal_surface()
    internal_opposition_signals = build_runtime_internal_opposition_signal_surface()
    self_review_signals = build_runtime_self_review_signal_surface()
    self_review_records = build_runtime_self_review_record_surface()
    self_review_runs = build_runtime_self_review_run_surface()
    self_review_outcomes = build_runtime_self_review_outcome_surface()
    self_review_cadence_signals = build_runtime_self_review_cadence_signal_surface()
    dream_hypothesis_signals = build_runtime_dream_hypothesis_signal_surface()
    dream_adoption_candidates = build_runtime_dream_adoption_candidate_surface()
    dream_influence_proposals = build_runtime_dream_influence_proposal_surface()
    self_authored_prompt_proposals = (
        build_runtime_self_authored_prompt_proposal_surface()
    )
    user_understanding_signals = build_runtime_user_understanding_signal_surface()
    remembered_fact_signals = build_runtime_remembered_fact_signal_surface()
    private_inner_note_signals = build_runtime_private_inner_note_signal_surface()
    private_initiative_tension_signals = (
        build_runtime_private_initiative_tension_signal_surface()
    )
    private_inner_interplay_signals = build_runtime_private_inner_interplay_signal_surface()
    private_state_snapshots = build_runtime_private_state_snapshot_surface()
    private_temporal_curiosity_states = build_runtime_private_temporal_curiosity_state_surface()
    inner_visible_support_signals = build_runtime_inner_visible_support_signal_surface()
    regulation_homeostasis_signals = build_runtime_regulation_homeostasis_signal_surface()
    relation_state_signals = build_runtime_relation_state_signal_surface()
    relation_continuity_signals = build_runtime_relation_continuity_signal_surface()
    meaning_significance_signals = build_runtime_meaning_significance_signal_surface()
    temperament_tendency_signals = build_runtime_temperament_tendency_signal_surface()
    executive_contradiction_signals = build_runtime_executive_contradiction_signal_surface()
    private_temporal_promotion_signals = build_runtime_private_temporal_promotion_signal_surface()
    chronicle_consolidation_signals = build_runtime_chronicle_consolidation_signal_surface()
    chronicle_consolidation_briefs = build_runtime_chronicle_consolidation_brief_surface()
    chronicle_consolidation_proposals = build_runtime_chronicle_consolidation_proposal_surface()
    user_md_update_proposals = build_runtime_user_md_update_proposal_surface()
    memory_md_update_proposals = build_runtime_memory_md_update_proposal_surface()
    selfhood_proposals = build_runtime_selfhood_proposal_surface()
    world_model_signals = build_runtime_world_model_signal_surface()
    runtime_awareness_signals = build_runtime_awareness_signal_surface()
    heartbeat = heartbeat_runtime_surface()

    return {
        "summary": {
            "visible_identity": _jarvis_identity_summary(visible_identity),
            "state_signal": _jarvis_state_signal(
                protected_voice, initiative_tension, private_state
            ),
            "retained_memory": _jarvis_retained_summary(
                retained_projection, retained_record
            ),
            "development": _jarvis_development_summary(
                self_model,
                development_state,
                development_focuses,
                reflective_critics,
                self_model_signals,
                goal_signals,
                reflection_signals,
            ),
            "continuity": _jarvis_continuity_summary(
                relation_state,
                visible_session,
                promotion_signal,
                world_model_signals,
                runtime_awareness_signals,
            ),
            "heartbeat": _jarvis_heartbeat_summary(heartbeat),
        },
        "state": {
            "visible_identity": visible_identity,
            "private_state": private_state,
            "protected_inner_voice": protected_voice,
            "inner_interplay": inner_interplay,
            "initiative_tension": initiative_tension,
        },
        "memory": {
            "retained_projection": retained_projection,
            "retained_record": retained_record,
            "visible_capability_continuity": visible_capability,
        },
        "development": {
            "self_model": self_model,
            "development_state": development_state,
            "growth_note": growth_note,
            "reflective_selection": reflective,
            "operational_preference": operational_preference,
            "operational_alignment": operational_alignment,
            "temporal_curiosity": temporal_curiosity,
            "development_focuses": development_focuses,
            "reflective_critics": reflective_critics,
            "self_model_signals": self_model_signals,
            "goal_signals": goal_signals,
            "reflection_signals": reflection_signals,
            "temporal_recurrence_signals": temporal_recurrence_signals,
            "witness_signals": witness_signals,
            "open_loop_signals": open_loop_signals,
            "open_loop_closure_proposals": open_loop_closure_proposals,
            "internal_opposition_signals": internal_opposition_signals,
            "self_review_signals": self_review_signals,
            "self_review_records": self_review_records,
            "self_review_runs": self_review_runs,
            "self_review_outcomes": self_review_outcomes,
            "self_review_cadence_signals": self_review_cadence_signals,
            "dream_hypothesis_signals": dream_hypothesis_signals,
            "dream_adoption_candidates": dream_adoption_candidates,
            "dream_influence_proposals": dream_influence_proposals,
            "self_authored_prompt_proposals": self_authored_prompt_proposals,
            "user_understanding_signals": user_understanding_signals,
            "private_inner_note_signals": private_inner_note_signals,
            "private_initiative_tension_signals": private_initiative_tension_signals,
            "private_inner_interplay_signals": private_inner_interplay_signals,
            "private_state_snapshots": private_state_snapshots,
            "private_temporal_curiosity_states": private_temporal_curiosity_states,
            "inner_visible_support_signals": inner_visible_support_signals,
            "regulation_homeostasis_signals": regulation_homeostasis_signals,
            "relation_state_signals": relation_state_signals,
            "relation_continuity_signals": relation_continuity_signals,
            "meaning_significance_signals": meaning_significance_signals,
            "temperament_tendency_signals": temperament_tendency_signals,
            "executive_contradiction_signals": executive_contradiction_signals,
            "private_temporal_promotion_signals": private_temporal_promotion_signals,
            "chronicle_consolidation_signals": chronicle_consolidation_signals,
            "chronicle_consolidation_briefs": chronicle_consolidation_briefs,
            "chronicle_consolidation_proposals": chronicle_consolidation_proposals,
            "user_md_update_proposals": user_md_update_proposals,
            "memory_md_update_proposals": memory_md_update_proposals,
            "selfhood_proposals": selfhood_proposals,
        },
        "continuity": {
            "visible_session": visible_session,
            "visible_continuity": visible_continuity,
            "relation_state": relation_state,
            "promotion_signal": promotion_signal,
            "promotion_decision": promotion_decision,
            "remembered_fact_signals": remembered_fact_signals,
            "world_model_signals": world_model_signals,
            "runtime_awareness_signals": runtime_awareness_signals,
        },
        "heartbeat": heartbeat,
    }


@router.get("/runtime-contract")
def mc_runtime_contract() -> dict:
    return build_runtime_contract_state()


@router.get("/heartbeat")
def mc_heartbeat() -> dict:
    return heartbeat_runtime_surface()


@router.post("/heartbeat/tick")
def mc_heartbeat_tick() -> dict:
    result = run_heartbeat_tick(trigger="manual")
    return {
        "ok": True,
        "state": result.state,
        "tick": result.tick,
        "policy": result.policy,
    }


@router.post("/runtime-contract/candidates/{candidate_id}/approve")
def mc_approve_runtime_contract_candidate(candidate_id: str) -> dict:
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
    settings = load_settings()
    return {
        "settings": settings.to_dict(),
        "heartbeat_runtime": heartbeat_runtime_surface(),
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
        "runtime_development_focuses": build_runtime_development_focus_surface(),
        "runtime_reflective_critics": build_runtime_reflective_critic_surface(),
        "runtime_self_model_signals": build_runtime_self_model_signal_surface(),
        "runtime_goal_signals": build_runtime_goal_signal_surface(),
        "runtime_reflection_signals": build_runtime_reflection_signal_surface(),
        "runtime_temporal_recurrence_signals": build_runtime_temporal_recurrence_signal_surface(),
        "runtime_witness_signals": build_runtime_witness_signal_surface(),
        "runtime_open_loop_signals": build_runtime_open_loop_signal_surface(),
        "runtime_open_loop_closure_proposals": build_runtime_open_loop_closure_proposal_surface(),
        "runtime_internal_opposition_signals": build_runtime_internal_opposition_signal_surface(),
        "runtime_self_review_signals": build_runtime_self_review_signal_surface(),
        "runtime_self_review_records": build_runtime_self_review_record_surface(),
        "runtime_self_review_runs": build_runtime_self_review_run_surface(),
        "runtime_self_review_outcomes": build_runtime_self_review_outcome_surface(),
        "runtime_self_review_cadence_signals": build_runtime_self_review_cadence_signal_surface(),
        "runtime_dream_hypothesis_signals": build_runtime_dream_hypothesis_signal_surface(),
        "runtime_dream_adoption_candidates": build_runtime_dream_adoption_candidate_surface(),
        "runtime_dream_influence_proposals": build_runtime_dream_influence_proposal_surface(),
        "runtime_self_authored_prompt_proposals": build_runtime_self_authored_prompt_proposal_surface(),
        "runtime_user_understanding_signals": build_runtime_user_understanding_signal_surface(),
        "runtime_remembered_fact_signals": build_runtime_remembered_fact_signal_surface(),
        "runtime_private_inner_note_signals": build_runtime_private_inner_note_signal_surface(),
        "runtime_private_initiative_tension_signals": build_runtime_private_initiative_tension_signal_surface(),
        "runtime_private_inner_interplay_signals": build_runtime_private_inner_interplay_signal_surface(),
        "runtime_private_state_snapshots": build_runtime_private_state_snapshot_surface(),
        "runtime_private_temporal_curiosity_states": build_runtime_private_temporal_curiosity_state_surface(),
        "runtime_inner_visible_support_signals": build_runtime_inner_visible_support_signal_surface(),
        "runtime_regulation_homeostasis_signals": build_runtime_regulation_homeostasis_signal_surface(),
        "runtime_relation_state_signals": build_runtime_relation_state_signal_surface(),
        "runtime_relation_continuity_signals": build_runtime_relation_continuity_signal_surface(),
        "runtime_meaning_significance_signals": build_runtime_meaning_significance_signal_surface(),
        "runtime_temperament_tendency_signals": build_runtime_temperament_tendency_signal_surface(),
        "runtime_executive_contradiction_signals": build_runtime_executive_contradiction_signal_surface(),
        "runtime_private_temporal_promotion_signals": build_runtime_private_temporal_promotion_signal_surface(),
        "runtime_chronicle_consolidation_signals": build_runtime_chronicle_consolidation_signal_surface(),
        "runtime_chronicle_consolidation_briefs": build_runtime_chronicle_consolidation_brief_surface(),
        "runtime_chronicle_consolidation_proposals": build_runtime_chronicle_consolidation_proposal_surface(),
        "runtime_user_md_update_proposals": build_runtime_user_md_update_proposal_surface(),
        "runtime_memory_md_update_proposals": build_runtime_memory_md_update_proposal_surface(),
        "runtime_selfhood_proposals": build_runtime_selfhood_proposal_surface(),
        "runtime_world_model_signals": build_runtime_world_model_signal_surface(),
        "runtime_awareness_signals": build_runtime_awareness_signal_surface(),
        "runtime_relevance_decisions": build_runtime_relevance_decision_surface(),
        "runtime_memory_selections": build_runtime_memory_selection_surface(),
        "runtime_inner_visible_prompt_bridges": build_runtime_inner_visible_prompt_bridge_surface(),
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


@router.get("/ollama-models")
def mc_ollama_models() -> dict:
    return available_ollama_models_for_visible_target()


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
        raise HTTPException(
            status_code=404, detail="Capability approval request not found"
        )
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
        if str(provider).strip() == "ollama":
            ollama_models = available_ollama_models_for_visible_target()
            available = {
                str(item.get("name") or "").strip()
                for item in ollama_models.get("models", [])
                if isinstance(item, dict)
            }
            if model.strip() in available:
                local_target = resolve_provider_router_target(lane="local")
                configure_provider_router_entry(
                    provider="ollama",
                    model=model.strip(),
                    auth_mode="none",
                    auth_profile="",
                    base_url=str(
                        local_target.get("base_url") or "http://127.0.0.1:11434"
                    ),
                    api_key="",
                    lane="local",
                    set_visible=False,
                )
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
        "ollama_models": available_ollama_models_for_visible_target(),
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
                "auth_status": str(state.get("status", "missing"))
                if state
                else "missing",
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


def _jarvis_identity_summary(visible_identity: dict) -> dict[str, object]:
    files = list(visible_identity.get("source_files") or [])
    return {
        "active": bool(visible_identity.get("active")),
        "workspace": str(visible_identity.get("workspace") or ""),
        "source_files": files,
        "fingerprint": str(visible_identity.get("fingerprint") or ""),
        "line_count": int(visible_identity.get("extracted_line_count") or 0),
    }


def _jarvis_state_signal(
    protected_voice: dict, initiative_tension: dict, private_state: dict
) -> dict[str, str]:
    voice = protected_voice.get("current") or {}
    tension = initiative_tension.get("current") or {}
    state = private_state.get("current") or {}
    return {
        "mood_tone": str(voice.get("mood_tone") or "unknown"),
        "current_concern": _preview_text(
            str(voice.get("current_concern") or tension.get("reason") or "unknown"),
            limit=96,
        ),
        "current_pull": _preview_text(
            str(
                voice.get("current_pull") or tension.get("tension_target") or "unknown"
            ),
            limit=120,
        ),
        "confidence": str(
            state.get("confidence") or tension.get("confidence") or "unknown"
        ),
    }


def _jarvis_retained_summary(
    retained_projection: dict, retained_record: dict
) -> dict[str, str]:
    projection = retained_projection.get("current") or retained_projection or {}
    record = retained_record.get("current") or {}
    return {
        "focus": _preview_text(
            str(
                retained_projection.get("retained_focus")
                or projection.get("retained_value")
                or record.get("retained_value")
                or "none"
            ),
            limit=120,
        ),
        "kind": str(
            retained_projection.get("retained_kind")
            or projection.get("retained_kind")
            or record.get("retained_kind")
            or "unknown"
        ),
        "scope": str(
            retained_projection.get("retention_scope")
            or projection.get("retention_scope")
            or record.get("retention_scope")
            or "unknown"
        ),
        "confidence": str(
            retained_projection.get("confidence")
            or projection.get("confidence")
            or record.get("confidence")
            or "unknown"
        ),
    }


def _jarvis_development_summary(
    self_model: dict,
    development_state: dict,
    development_focuses: dict | None = None,
    reflective_critics: dict | None = None,
    self_model_signals: dict | None = None,
    goal_signals: dict | None = None,
    reflection_signals: dict | None = None,
) -> dict[str, str]:
    model = self_model.get("current") or {}
    state = development_state.get("current") or {}
    focus_summary = (development_focuses or {}).get("summary") or {}
    critic_summary = (reflective_critics or {}).get("summary") or {}
    self_signal_summary = (self_model_signals or {}).get("summary") or {}
    goal_summary = (goal_signals or {}).get("summary") or {}
    reflection_summary = (reflection_signals or {}).get("summary") or {}
    return {
        "direction": str(
            model.get("growth_direction")
            or state.get("preferred_direction")
            or "unknown"
        ),
        "identity_focus": str(
            model.get("identity_focus") or state.get("identity_thread") or "unknown"
        ),
        "work_mode": str(model.get("preferred_work_mode") or "unknown"),
        "tension": str(
            state.get("recurring_tension")
            or model.get("recurring_tension")
            or "unknown"
        ),
        "focus_count": str(focus_summary.get("active_count") or 0),
        "current_focus": str(
            focus_summary.get("current_focus") or "No active development focus"
        ),
        "critic_count": str(critic_summary.get("active_count") or 0),
        "current_critic": str(
            critic_summary.get("current_critic") or "No active critic signal"
        ),
        "self_model_signal_count": str(self_signal_summary.get("active_count") or 0),
        "current_self_model_signal": str(
            self_signal_summary.get("current_signal") or "No active self-model signal"
        ),
        "goal_count": str(
            (goal_summary.get("active_count") or 0)
            + (goal_summary.get("blocked_count") or 0)
        ),
        "current_goal": str(
            goal_summary.get("current_goal") or "No active goal signal"
        ),
        "reflection_signal_count": str(
            (reflection_summary.get("active_count") or 0)
            + (reflection_summary.get("integrating_count") or 0)
            + (reflection_summary.get("settled_count") or 0)
        ),
        "current_reflection_signal": str(
            reflection_summary.get("current_signal") or "No active reflection signal"
        ),
    }


def _jarvis_continuity_summary(
    relation_state: dict,
    visible_session: dict,
    promotion_signal: dict,
    world_model_signals: dict | None = None,
    runtime_awareness_signals: dict | None = None,
) -> dict[str, str]:
    relation = relation_state.get("current") or {}
    signal = promotion_signal.get("current") or {}
    world_summary = (world_model_signals or {}).get("summary") or {}
    runtime_awareness_summary = (runtime_awareness_signals or {}).get("summary") or {}
    return {
        "continuity_mode": str(
            relation.get("continuity_mode")
            or visible_session.get("latest_status")
            or "unknown"
        ),
        "interaction_mode": str(relation.get("interaction_mode") or "unknown"),
        "relation_pull": _preview_text(
            str(
                relation.get("relation_pull")
                or signal.get("promotion_target")
                or "unknown"
            ),
            limit=96,
        ),
        "session_status": str(visible_session.get("latest_status") or "unknown"),
        "world_model_count": str(world_summary.get("active_count") or 0),
        "current_world_model": str(
            world_summary.get("current_signal") or "No active world-model signal"
        ),
        "runtime_awareness_count": str(
            (runtime_awareness_summary.get("active_count") or 0)
            + (runtime_awareness_summary.get("constrained_count") or 0)
            + (runtime_awareness_summary.get("recovered_count") or 0)
        ),
        "current_runtime_awareness": str(
            runtime_awareness_summary.get("current_signal")
            or "No active runtime-awareness signal"
        ),
    }


def _jarvis_heartbeat_summary(heartbeat: dict) -> dict[str, str]:
    state = heartbeat.get("state") or {}
    return {
        "enabled": "enabled" if state.get("enabled") else "disabled",
        "status": str(
            state.get("schedule_state") or state.get("schedule_status") or "unknown"
        ),
        "decision": str(state.get("last_decision_type") or "none"),
        "result": _preview_text(
            str(
                state.get("last_result")
                or state.get("summary")
                or "No heartbeat result yet."
            ),
            limit=120,
        ),
        "next_tick_at": str(state.get("next_tick_at") or ""),
        "trigger": str(state.get("last_trigger_source") or "none"),
    }


def _preview_text(value: str, *, limit: int = 96) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:limit] + ("…" if len(text) > limit else "")
