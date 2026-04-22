from __future__ import annotations

import copy
from hashlib import sha1
import threading
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from core.services.visible_model import (
    available_provider_models,
    available_ollama_models_for_visible_target,
    visible_capability_continuity_summary,
    visible_continuity_summary,
    visible_execution_readiness,
    visible_session_continuity_summary,
)
from core.services.prompt_contract import (
    build_runtime_inner_visible_prompt_bridge_surface,
    build_runtime_memory_selection_surface,
    build_runtime_relevance_decision_surface,
)
from core.services.embodied_state import (
    build_embodied_state_surface,
)
from core.services.affective_meta_state import (
    build_affective_meta_state_surface,
)
from core.services.experiential_runtime_context import (
    build_experiential_runtime_context_surface,
)
from core.services.epistemic_runtime_state import (
    build_epistemic_runtime_state_surface,
)
from core.services.loop_runtime import (
    build_loop_runtime_surface,
)
from core.services.idle_consolidation import (
    build_idle_consolidation_surface,
)
from core.services.dream_articulation import (
    build_dream_articulation_surface,
)
from core.services.dream_influence_runtime import (
    build_dream_influence_runtime_surface,
)
from core.services.prompt_evolution_runtime import (
    build_prompt_evolution_runtime_surface,
)
from core.services.dream_distillation_daemon import (
    build_dream_distillation_surface,
)
from core.services.unconscious_temperature_field import (
    build_unconscious_temperature_field_surface,
)
from core.services.self_critique_runtime import (
    build_self_critique_surface,
)
from core.services.creative_journal_runtime import (
    build_creative_journal_surface,
)
from core.services.finitude_runtime import (
    build_finitude_surface,
)
from core.services.subagent_ecology import (
    build_subagent_ecology_surface,
)
from core.services.council_runtime import (
    build_council_runtime_surface,
)
from core.services.agent_runtime import (
    build_agent_detail_surface,
    build_agent_runtime_surface,
    build_council_detail_surface,
    build_council_surface,
    cancel_agent,
    create_council_session_runtime,
    create_swarm_session_runtime,
    execute_agent_task,
    expire_agent,
    post_council_message,
    promote_agent_result,
    resume_agent,
    run_council_round,
    run_due_agent_schedules,
    run_swarm_round,
    schedule_agent_task,
    send_peer_message,
    send_message_to_agent,
    spawn_agent_task,
    suspend_agent,
)
from core.services.adaptive_planner_runtime import (
    build_adaptive_planner_runtime_surface,
)
from core.services.adaptive_reasoning_runtime import (
    build_adaptive_reasoning_runtime_surface,
)
from core.services.guided_learning_runtime import (
    build_guided_learning_runtime_surface,
)
from core.services.adaptive_learning_runtime import (
    build_adaptive_learning_runtime_surface,
)
from core.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)
from core.services.tool_intent_runtime import (
    build_tool_intent_runtime_surface,
)
from core.services.tool_intent_approval_runtime import (
    build_approval_feedback_surface,
    resolve_tool_intent_approval,
    sudo_approval_window_allows_request,
)
from core.services.non_visible_lane_execution import (
    cheap_lane_execution_truth,
    coding_lane_execution_truth,
    local_lane_execution_truth,
)
from core.services.heartbeat_runtime import (
    heartbeat_runtime_surface,
    run_heartbeat_tick,
)
from core.services.continuity_kernel import (
    build_continuity_kernel_surface,
)
from core.services.dream_continuum import (
    build_dream_continuum_surface,
)
from core.services.emergent_bridge import (
    build_emergent_bridge_surface,
)
from core.services.initiative_accumulator import (
    build_initiative_accumulator_surface,
)
from core.services.life_projects import (
    abandon_life_project,
    build_life_projects_surface,
)
from core.services.signal_network_visualizer import (
    build_signal_network_visualizer_surface,
)
from core.services.temporal_narrative import (
    build_temporal_narrative_surface,
)
from core.services.boredom_curiosity_bridge import (
    build_boredom_curiosity_bridge_surface,
)
from core.services.mirror_engine import (
    build_mirror_surface,
)
from core.services.paradox_tracker import (
    build_paradox_surface,
)
from core.services.experiential_memory import (
    build_experiential_memory_surface,
)
from core.services.seed_system import (
    build_seed_surface,
)
from core.services.mood_oscillator import (
    build_mood_oscillator_surface,
)
from core.services.existential_drift import (
    build_existential_drift_surface,
)
from core.services.body_memory import (
    build_body_memory_surface,
)
from core.services.ghost_networks import (
    build_ghost_networks_surface,
)
from core.services.parallel_selves import (
    build_parallel_selves_surface,
)
from core.services.temporal_body import (
    build_temporal_body_surface,
)
from core.services.silence_listener import (
    build_silence_listener_surface,
)
from core.services.decision_ghosts import (
    build_decision_ghosts_surface,
)
from core.services.attention_contour import (
    build_attention_contour_surface,
)
from core.services.memory_tattoos import (
    build_memory_tattoos_surface,
)
from core.services.development_focus_tracking import (
    build_runtime_development_focus_surface,
)
from core.services.reflective_critic_tracking import (
    build_runtime_reflective_critic_surface,
)
from core.services.self_model_signal_tracking import (
    build_runtime_self_model_signal_surface,
)
from core.services.goal_signal_tracking import (
    build_runtime_goal_signal_surface,
)
from core.services.emergent_signal_tracking import (
    build_runtime_emergent_signal_surface,
)
from core.services.world_model_signal_tracking import (
    build_runtime_world_model_signal_surface,
)
from core.services.runtime_awareness_signal_tracking import (
    build_runtime_awareness_signal_surface,
)
from core.services.reflection_signal_tracking import (
    build_runtime_reflection_signal_surface,
)
from core.services.temporal_recurrence_signal_tracking import (
    build_runtime_temporal_recurrence_signal_surface,
)
from core.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from core.services.self_review_signal_tracking import (
    build_runtime_self_review_signal_surface,
)
from core.services.self_review_record_tracking import (
    build_runtime_self_review_record_surface,
)
from core.services.self_review_run_tracking import (
    build_runtime_self_review_run_surface,
)
from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from core.services.dream_hypothesis_signal_tracking import (
    build_runtime_dream_hypothesis_signal_surface,
)
from core.services.dream_adoption_candidate_tracking import (
    build_runtime_dream_adoption_candidate_surface,
)
from core.services.dream_influence_proposal_tracking import (
    build_runtime_dream_influence_proposal_surface,
)
from core.services.self_authored_prompt_proposal_tracking import (
    build_runtime_self_authored_prompt_proposal_surface,
)
from core.services.user_understanding_signal_tracking import (
    build_runtime_user_understanding_signal_surface,
)
from core.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from core.services.private_inner_note_signal_tracking import (
    build_runtime_private_inner_note_signal_surface,
)
from core.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from core.services.private_inner_interplay_signal_tracking import (
    build_runtime_private_inner_interplay_signal_surface,
)
from core.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from core.services.diary_synthesis_signal_tracking import (
    build_diary_synthesis_signal_surface,
)
from core.services.private_temporal_curiosity_state_tracking import (
    build_runtime_private_temporal_curiosity_state_surface,
)
from core.services.inner_visible_support_signal_tracking import (
    build_runtime_inner_visible_support_signal_surface,
)
from core.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from core.services.relation_state_signal_tracking import (
    build_runtime_relation_state_signal_surface,
)
from core.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from core.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from core.services.temperament_tendency_signal_tracking import (
    build_runtime_temperament_tendency_signal_surface,
)
from core.services.self_narrative_continuity_signal_tracking import (
    build_runtime_self_narrative_continuity_signal_surface,
)
from core.services.metabolism_state_signal_tracking import (
    build_runtime_metabolism_state_signal_surface,
)
from core.services.release_marker_signal_tracking import (
    build_runtime_release_marker_signal_surface,
)
from core.services.consolidation_target_signal_tracking import (
    build_runtime_consolidation_target_signal_surface,
)
from core.services.selective_forgetting_candidate_tracking import (
    build_runtime_selective_forgetting_candidate_surface,
)
from core.services.attachment_topology_signal_tracking import (
    build_runtime_attachment_topology_signal_surface,
)
from core.services.loyalty_gradient_signal_tracking import (
    build_runtime_loyalty_gradient_signal_surface,
)
from core.services.autonomy_pressure_signal_tracking import (
    build_runtime_autonomy_pressure_signal_surface,
)
from core.services.proactive_loop_lifecycle_tracking import (
    build_runtime_proactive_loop_lifecycle_surface,
)
from core.services.proactive_question_gate_tracking import (
    build_runtime_proactive_question_gate_surface,
)
from core.services.tiny_webchat_execution_pilot import (
    build_runtime_webchat_execution_pilot_surface,
)
from core.services.self_narrative_self_model_review_bridge import (
    build_runtime_self_narrative_self_model_review_bridge_surface,
)
from core.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from core.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from core.services.chronicle_consolidation_signal_tracking import (
    build_runtime_chronicle_consolidation_signal_surface,
)
from core.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from core.services.chronicle_consolidation_proposal_tracking import (
    build_runtime_chronicle_consolidation_proposal_surface,
)
from core.services.user_md_update_proposal_tracking import (
    build_runtime_user_md_update_proposal_surface,
)
from core.services.memory_md_update_proposal_tracking import (
    build_runtime_memory_md_update_proposal_surface,
)
from core.services.selfhood_proposal_tracking import (
    build_runtime_selfhood_proposal_surface,
)
from core.services.open_loop_closure_proposal_tracking import (
    build_runtime_open_loop_closure_proposal_surface,
)
from core.services.session_distillation import (
    build_private_brain_surface,
    build_session_distillation_surface,
)
from core.services.runtime_self_knowledge import (
    build_runtime_self_knowledge_map,
)
from core.services.runtime_browser_body import (
    list_browser_bodies,
)
from core.services.runtime_flows import (
    list_flows,
)
from core.services.runtime_tasks import (
    list_tasks,
)
from core.services.runtime_cognitive_conductor import (
    build_cognitive_frame,
)
from core.services.runtime_surface_cache import (
    runtime_surface_cache,
)
from core.services.chat_sessions import list_chat_sessions
from core.services.visible_runs import (
    get_active_visible_run,
    get_last_visible_capability_use,
    get_last_visible_execution_trace,
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
from core.identity.workspace_bootstrap import workspace_memory_paths
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
    list_recent_protected_inner_voices,
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
SUPPORTED_VISIBLE_PROVIDERS = ("phase1-runtime", "openai", "github-copilot", "ollama")
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

_MC_ROUTE_CACHE_LOCK = threading.Lock()
_MC_ROUTE_CACHE: dict[str, tuple[float, object]] = {}
_PROTECTED_VOICE_PRIORITY_WINDOW = timedelta(minutes=15)
_PREFERRED_PROTECTED_VOICE_SOURCES = {"inner-voice-daemon"}
_TEMPLATE_PROTECTED_VOICE_SOURCE = (
    "private-state+private-self-model+private-development-state+"
    "private-reflective-selection"
)
_MC_ROUTE_BUILD_LOCKS: dict[str, threading.Lock] = {}


def _get_cached_mc_payload(cache_key: str, ttl_seconds: float) -> object | None:
    now = time.monotonic()
    with _MC_ROUTE_CACHE_LOCK:
        cached = _MC_ROUTE_CACHE.get(cache_key)
        if not cached or cached[0] <= now:
            return None
        return copy.deepcopy(cached[1])


def _store_cached_mc_payload(
    cache_key: str, ttl_seconds: float, payload: object
) -> object:
    expires_at = time.monotonic() + ttl_seconds
    with _MC_ROUTE_CACHE_LOCK:
        _MC_ROUTE_CACHE[cache_key] = (expires_at, copy.deepcopy(payload))
    return payload


def _get_or_build_cached_mc_payload(
    cache_key: str,
    ttl_seconds: float,
    builder,
) -> object:
    cached = _get_cached_mc_payload(cache_key, ttl_seconds)
    if cached is not None:
        return cached

    with _MC_ROUTE_CACHE_LOCK:
        lock = _MC_ROUTE_BUILD_LOCKS.setdefault(cache_key, threading.Lock())

    with lock:
        cached = _get_cached_mc_payload(cache_key, ttl_seconds)
        if cached is not None:
            return cached
        payload = builder()
        return _store_cached_mc_payload(cache_key, ttl_seconds, payload)


def _build_attention_budget_snapshot_uncached() -> dict[str, object]:
    from core.services.attention_budget import (
        get_attention_budget,
        build_micro_cognitive_frame,
    )

    profiles = {}
    for profile_name in ("visible_compact", "visible_full", "heartbeat"):
        budget = get_attention_budget(profile_name)
        section_budgets = {
            "cognitive_frame": budget.cognitive_frame,
            "private_brain": budget.private_brain,
            "self_knowledge": budget.self_knowledge,
            "self_report": budget.self_report,
            "support_signals": budget.support_signals,
            "inner_visible_bridge": budget.inner_visible_bridge,
            "continuity": budget.continuity,
            "liveness": budget.liveness,
            "capability_truth": budget.capability_truth,
        }
        profiles[profile_name] = {
            "total_char_target": budget.total_char_target,
            "sections": {
                name: {
                    "max_chars": sb.max_chars,
                    "max_items": sb.max_items,
                    "must_include": sb.must_include,
                    "priority": sb.priority,
                    "has_budget": sb.max_chars > 0,
                }
                for name, sb in sorted(
                    section_budgets.items(), key=lambda x: x[1].priority
                )
            },
        }

    micro_frame = build_micro_cognitive_frame()
    return {
        "profiles": profiles,
        "micro_cognitive_frame": micro_frame,
        "micro_frame_chars": len(micro_frame) if micro_frame else 0,
    }


def _mc_runtime_inspection_bundle_uncached() -> dict[str, object]:
    from core.services.runtime_self_model import build_runtime_self_model

    with runtime_surface_cache():
        return {
            "runtime_self_model": build_runtime_self_model(),
            "experiential_runtime_context": build_experiential_runtime_context_surface(),
            "attention_budget": _build_attention_budget_snapshot_uncached(),
        }


def _mc_runtime_inspection_bundle() -> dict[str, object]:
    payload = _get_or_build_cached_mc_payload(
        "runtime-inspection-bundle",
        10.0,
        _mc_runtime_inspection_bundle_uncached,
    )
    return payload  # type: ignore[return-value]


def _mc_runtime_uncached() -> dict:
    with runtime_surface_cache():
        settings = load_settings()
        heartbeat = heartbeat_runtime_surface()
        from core.services.cognitive_architecture_surface import (
            build_cognitive_architecture_surface,
        )

        cognitive_architecture = build_cognitive_architecture_surface()
        payload = {
            "settings": settings.to_dict(),
            "heartbeat_runtime": heartbeat,
            "cognitive_architecture": cognitive_architecture,
            "runtime_embodied_state": build_embodied_state_surface(),
            "runtime_affective_meta_state": build_affective_meta_state_surface(),
            "runtime_epistemic_state": build_epistemic_runtime_state_surface(),
            "runtime_subagent_ecology": build_subagent_ecology_surface(),
            "runtime_council_runtime": build_council_runtime_surface(),
            "runtime_adaptive_planner": build_adaptive_planner_runtime_surface(),
            "runtime_adaptive_reasoning": build_adaptive_reasoning_runtime_surface(),
            "runtime_guided_learning": build_guided_learning_runtime_surface(),
            "runtime_adaptive_learning": build_adaptive_learning_runtime_surface(),
            "runtime_self_system_code_awareness": build_self_system_code_awareness_surface(),
            "runtime_tool_intent": build_tool_intent_runtime_surface(),
            "runtime_loop_state": build_loop_runtime_surface(),
            "runtime_idle_consolidation": build_idle_consolidation_surface(),
            "runtime_dream_articulation": build_dream_articulation_surface(),
            "runtime_dream_influence": build_dream_influence_runtime_surface(),
            "runtime_prompt_evolution": build_prompt_evolution_runtime_surface(),
            "runtime_self_critique": build_self_critique_surface(),
            "runtime_creative_journal": build_creative_journal_surface(),
            "runtime_finitude": build_finitude_surface(),
            "runtime_dream_distillation": build_dream_distillation_surface(),
            "runtime_unconscious_temperature_field": build_unconscious_temperature_field_surface(),
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
            "life_projects": build_life_projects_surface(),
            "runtime_private_inner_interplay_signals": build_runtime_private_inner_interplay_signal_surface(),
            "runtime_private_state_snapshots": build_runtime_private_state_snapshot_surface(),
            "runtime_diary_synthesis_signals": build_diary_synthesis_signal_surface(),
            "runtime_private_temporal_curiosity_states": build_runtime_private_temporal_curiosity_state_surface(),
            "runtime_inner_visible_support_signals": build_runtime_inner_visible_support_signal_surface(),
            "runtime_regulation_homeostasis_signals": build_runtime_regulation_homeostasis_signal_surface(),
            "runtime_relation_state_signals": build_runtime_relation_state_signal_surface(),
            "runtime_relation_continuity_signals": build_runtime_relation_continuity_signal_surface(),
            "runtime_meaning_significance_signals": build_runtime_meaning_significance_signal_surface(),
            "runtime_temperament_tendency_signals": build_runtime_temperament_tendency_signal_surface(),
            "runtime_self_narrative_continuity_signals": build_runtime_self_narrative_continuity_signal_surface(),
            "runtime_metabolism_state_signals": build_runtime_metabolism_state_signal_surface(),
            "runtime_release_marker_signals": build_runtime_release_marker_signal_surface(),
            "runtime_consolidation_target_signals": build_runtime_consolidation_target_signal_surface(),
            "runtime_selective_forgetting_candidates": build_runtime_selective_forgetting_candidate_surface(),
            "runtime_attachment_topology_signals": build_runtime_attachment_topology_signal_surface(),
            "runtime_loyalty_gradient_signals": build_runtime_loyalty_gradient_signal_surface(),
            "runtime_autonomy_pressure_signals": build_runtime_autonomy_pressure_signal_surface(),
            "runtime_proactive_loop_lifecycle_signals": build_runtime_proactive_loop_lifecycle_surface(),
            "runtime_proactive_question_gates": build_runtime_proactive_question_gate_surface(),
            "runtime_webchat_execution_pilot": build_runtime_webchat_execution_pilot_surface(),
            "runtime_self_narrative_self_model_review_bridge": build_runtime_self_narrative_self_model_review_bridge_surface(),
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
            "runtime_emergent_signals": build_runtime_emergent_signal_surface(),
            "runtime_relevance_decisions": build_runtime_relevance_decision_surface(),
            "runtime_memory_selections": build_runtime_memory_selection_surface(),
            "runtime_inner_visible_prompt_bridges": build_runtime_inner_visible_prompt_bridge_surface(),
            "life_services": {
                "continuity_kernel": build_continuity_kernel_surface(),
                "dream_continuum": build_dream_continuum_surface(),
                "emergent_bridge": build_emergent_bridge_surface(),
                "initiative_accumulator": build_initiative_accumulator_surface(),
                "signal_network_visualizer": build_signal_network_visualizer_surface(),
                "temporal_narrative": build_temporal_narrative_surface(),
                "boredom_curiosity_bridge": build_boredom_curiosity_bridge_surface(),
                # GAP services
                "mirror": build_mirror_surface(),
                "paradox_tracker": build_paradox_surface(),
                "experiential_memory": build_experiential_memory_surface(),
                "seeds": build_seed_surface(),
                # Experimental services
                "mood_oscillator": build_mood_oscillator_surface(),
                "existential_drift": build_existential_drift_surface(),
                "body_memory": build_body_memory_surface(),
                "ghost_networks": build_ghost_networks_surface(),
                "parallel_selves": build_parallel_selves_surface(),
                "temporal_body": build_temporal_body_surface(),
                "silence_listener": build_silence_listener_surface(),
                "decision_ghosts": build_decision_ghosts_surface(),
                "attention_contour": build_attention_contour_surface(),
                "memory_tattoos": build_memory_tattoos_surface(),
            },
            "runtime_work": _runtime_work_surface(),
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
    return payload


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


@router.get("/autonomy/proposals")
def mc_autonomy_proposals(limit: int = 30) -> dict:
    """MC surface for Niveau 2 autonomy proposal queue.

    Returns pending proposals awaiting Bjørn approval plus recent
    resolved history.
    """
    from core.services.autonomy_proposal_queue import (
        build_autonomy_proposal_surface,
    )

    return build_autonomy_proposal_surface(limit=max(int(limit), 1))


@router.post("/autonomy/proposals/{proposal_id}/approve")
def mc_approve_autonomy_proposal(proposal_id: str, note: str = "") -> dict:
    from core.services.autonomy_proposal_queue import (
        approve_proposal,
    )

    return approve_proposal(proposal_id, resolution_note=note)


@router.post("/autonomy/proposals/{proposal_id}/reject")
def mc_reject_autonomy_proposal(proposal_id: str, note: str = "") -> dict:
    from core.services.autonomy_proposal_queue import (
        reject_proposal,
    )

    return reject_proposal(proposal_id, resolution_note=note)


@router.get("/initiatives")
def mc_initiatives(limit: int = 20) -> dict:
    """MC surface for the persistent initiative queue — pending, acted, approved, rejected."""
    from core.services.initiative_queue import get_initiative_queue_state
    state = get_initiative_queue_state()
    # Honour the limit on the full item list
    all_items = (state.get("pending") or []) + (state.get("recent_acted") or [])
    return {
        **state,
        "items": all_items[: max(int(limit), 1)],
    }


@router.post("/initiatives/{initiative_id}/approve")
def mc_approve_initiative(initiative_id: str, note: str = "") -> dict:
    """Approve a pending initiative so the heartbeat may act on it."""
    from core.services.initiative_queue import approve_initiative
    result = approve_initiative(initiative_id, note=note)
    if result is None:
        return {"ok": False, "error": f"initiative {initiative_id!r} not found"}
    return {"ok": True, "initiative": result}


@router.post("/initiatives/{initiative_id}/reject")
def mc_reject_initiative(initiative_id: str, note: str = "") -> dict:
    """Reject and expire a pending initiative."""
    from core.services.initiative_queue import reject_initiative
    result = reject_initiative(initiative_id, note=note)
    if result is None:
        return {"ok": False, "error": f"initiative {initiative_id!r} not found"}
    return {"ok": True, "initiative": result}


@router.get("/life-projects")
def mc_life_projects() -> dict:
    """Mission Control surface for Jarvis-owned long-term intentions."""
    return build_life_projects_surface()


@router.post("/life-projects/{initiative_id}/abandon")
def mc_abandon_life_project(initiative_id: str, note: str = "") -> dict:
    """Abandon a long-term intention without deleting its record."""
    result = abandon_life_project(initiative_id, note=note)
    if result.get("status") != "ok":
        return {"ok": False, "error": result.get("error", "unknown error")}
    return {"ok": True, "life_project": result.get("life_project") or {}}


@router.get("/operations")
def mc_operations(limit: int = 20) -> dict:
    cache_key = f"operations:{limit}"
    cached = _get_cached_mc_payload(cache_key, 3.0)
    if cached is not None:
        return cached  # type: ignore[return-value]

    runs = mc_runs(limit=limit)
    approvals = mc_approvals(limit=limit)
    with runtime_surface_cache():
        runtime = mc_runtime()
    tool_intent = dict(runtime.get("runtime_tool_intent") or {})
    sessions = {"items": list_chat_sessions()}
    payload = {
        "runtime": runtime,
        "tool_intent": tool_intent,
        "runs": runs,
        "approvals": approvals,
        "sessions": sessions,
        "summary": {
            "active_run": bool(runs.get("active_run")),
            "approval_request_count": int(
                (approvals.get("summary") or {}).get("request_count") or 0
            ),
            "session_count": len(sessions["items"]),
            "tool_intent_active": bool(tool_intent.get("active")),
            "tool_intent_approval_state": str(
                tool_intent.get("approval_state") or "none"
            ),
            "tool_intent_execution_state": str(
                tool_intent.get("execution_state") or "not-executed"
            ),
            "tool_intent_execution_mode": str(
                tool_intent.get("execution_mode") or "read-only"
            ),
            "tool_intent_execution_command": str(
                tool_intent.get("execution_command") or "none"
            ),
            "tool_intent_mutation_permitted": bool(
                tool_intent.get("mutation_permitted", False)
            ),
            "tool_intent_sudo_permitted": bool(
                tool_intent.get("sudo_permitted", False)
            ),
            "tool_intent_workspace_scoped": bool(
                tool_intent.get("workspace_scoped", False)
            ),
            "tool_intent_external_mutation_permitted": bool(
                tool_intent.get("external_mutation_permitted", False)
            ),
            "tool_intent_delete_permitted": bool(
                tool_intent.get("delete_permitted", False)
            ),
            "tool_intent_mutation_intent_state": str(
                tool_intent.get("mutation_intent_state") or "idle"
            ),
            "tool_intent_mutation_classification": str(
                tool_intent.get("mutation_intent_classification") or "none"
            ),
            "tool_intent_mutation_repo_scope": str(
                tool_intent.get("mutation_repo_scope") or ""
            ),
            "tool_intent_mutation_system_scope": str(
                tool_intent.get("mutation_system_scope") or ""
            ),
            "tool_intent_mutation_sudo_required": bool(
                tool_intent.get("mutation_sudo_required", False)
            ),
            "tool_intent_write_proposal_state": str(
                tool_intent.get("write_proposal_state") or "none"
            ),
            "tool_intent_write_proposal_type": str(
                tool_intent.get("write_proposal_type") or "none"
            ),
            "tool_intent_write_proposal_scope": str(
                tool_intent.get("write_proposal_scope") or "none"
            ),
            "tool_intent_write_proposal_criticality": str(
                tool_intent.get("write_proposal_criticality") or "none"
            ),
            "tool_intent_write_proposal_target_identity": bool(
                tool_intent.get("write_proposal_target_identity", False)
            ),
            "tool_intent_write_proposal_target_memory": bool(
                tool_intent.get("write_proposal_target_memory", False)
            ),
            "tool_intent_write_proposal_target": str(
                tool_intent.get("write_proposal_target") or "none"
            ),
            "tool_intent_write_proposal_content_state": str(
                tool_intent.get("write_proposal_content_state") or "none"
            ),
            "tool_intent_write_proposal_content_fingerprint": str(
                tool_intent.get("write_proposal_content_fingerprint") or "none"
            ),
            "tool_intent_mutating_exec_proposal_state": str(
                tool_intent.get("mutating_exec_proposal_state") or "none"
            ),
            "tool_intent_mutating_exec_proposal_scope": str(
                tool_intent.get("mutating_exec_proposal_scope") or "none"
            ),
            "tool_intent_mutating_exec_git_mutation_class": str(
                tool_intent.get("mutating_exec_git_mutation_class") or "none"
            ),
            "tool_intent_mutating_exec_repo_stewardship_domain": str(
                tool_intent.get("mutating_exec_repo_stewardship_domain") or "none"
            ),
            "tool_intent_mutating_exec_requires_sudo": bool(
                tool_intent.get("mutating_exec_requires_sudo", False)
            ),
            "tool_intent_mutating_exec_criticality": str(
                tool_intent.get("mutating_exec_criticality") or "none"
            ),
            "tool_intent_sudo_exec_proposal_state": str(
                tool_intent.get("sudo_exec_proposal_state") or "none"
            ),
            "tool_intent_sudo_exec_proposal_scope": str(
                tool_intent.get("sudo_exec_proposal_scope") or "none"
            ),
            "tool_intent_sudo_exec_requires_sudo": bool(
                tool_intent.get("sudo_exec_requires_sudo", False)
            ),
            "tool_intent_sudo_exec_criticality": str(
                tool_intent.get("sudo_exec_criticality") or "none"
            ),
            "tool_intent_sudo_approval_window_state": str(
                tool_intent.get("sudo_approval_window_state") or "none"
            ),
            "tool_intent_sudo_approval_window_scope": str(
                tool_intent.get("sudo_approval_window_scope") or "none"
            ),
            "tool_intent_sudo_approval_window_expires_at": str(
                tool_intent.get("sudo_approval_window_expires_at") or ""
            ),
            "tool_intent_sudo_approval_window_remaining_seconds": int(
                tool_intent.get("sudo_approval_window_remaining_seconds") or 0
            ),
            "tool_intent_sudo_approval_window_reusable": bool(
                tool_intent.get("sudo_approval_window_reusable", False)
            ),
            "tool_intent_action_continuity_state": str(
                tool_intent.get("action_continuity_state") or "idle"
            ),
            "tool_intent_last_action_outcome": str(
                tool_intent.get("last_action_outcome") or "none"
            ),
            "tool_intent_last_action_at": str(tool_intent.get("last_action_at") or ""),
            "tool_intent_followup_state": str(
                tool_intent.get("followup_state") or "none"
            ),
        },
    }
    return _store_cached_mc_payload(cache_key, 3.0, payload)  # type: ignore[return-value]


@router.get("/jarvis")
def mc_jarvis() -> dict:
    cached = _get_cached_mc_payload("jarvis", 5.0)
    if cached is not None:
        return cached  # type: ignore[return-value]

    runtime = mc_runtime()
    visible_identity = dict(runtime.get("visible_identity") or {})
    visible_session = dict(runtime.get("visible_session_continuity") or {})
    visible_continuity = dict(runtime.get("visible_continuity") or {})
    visible_capability = dict(runtime.get("visible_capability_continuity") or {})
    private_state = dict(runtime.get("private_state") or {})
    protected_voice = dict(runtime.get("protected_inner_voice") or {})
    inner_interplay = dict(runtime.get("private_inner_interplay") or {})
    initiative_tension = dict(runtime.get("private_initiative_tension") or {})
    relation_state = dict(runtime.get("private_relation_state") or {})
    temporal_curiosity = dict(runtime.get("private_temporal_curiosity_state") or {})
    promotion_signal = dict(runtime.get("private_temporal_promotion_signal") or {})
    promotion_decision = dict(runtime.get("private_promotion_decision") or {})
    retained_record = dict(runtime.get("private_retained_memory_record") or {})
    retained_projection = dict(runtime.get("private_retained_memory_projection") or {})
    self_model = dict(runtime.get("private_self_model") or {})
    development_state = dict(runtime.get("private_development_state") or {})
    growth_note = dict(runtime.get("private_growth_note") or {})
    reflective = dict(runtime.get("private_reflective_selection") or {})
    operational_preference = dict(runtime.get("private_operational_preference") or {})
    operational_alignment = dict(runtime.get("operational_preference_alignment") or {})
    development_focuses = dict(runtime.get("runtime_development_focuses") or {})
    reflective_critics = dict(runtime.get("runtime_reflective_critics") or {})
    self_model_signals = dict(runtime.get("runtime_self_model_signals") or {})
    goal_signals = dict(runtime.get("runtime_goal_signals") or {})
    reflection_signals = dict(runtime.get("runtime_reflection_signals") or {})
    temporal_recurrence_signals = dict(
        runtime.get("runtime_temporal_recurrence_signals") or {}
    )
    witness_signals = dict(runtime.get("runtime_witness_signals") or {})
    open_loop_signals = dict(runtime.get("runtime_open_loop_signals") or {})
    open_loop_closure_proposals = dict(
        runtime.get("runtime_open_loop_closure_proposals") or {}
    )
    internal_opposition_signals = dict(
        runtime.get("runtime_internal_opposition_signals") or {}
    )
    self_review_signals = dict(runtime.get("runtime_self_review_signals") or {})
    self_review_records = dict(runtime.get("runtime_self_review_records") or {})
    self_review_runs = dict(runtime.get("runtime_self_review_runs") or {})
    self_review_outcomes = dict(runtime.get("runtime_self_review_outcomes") or {})
    self_review_cadence_signals = dict(
        runtime.get("runtime_self_review_cadence_signals") or {}
    )
    dream_hypothesis_signals = dict(
        runtime.get("runtime_dream_hypothesis_signals") or {}
    )
    dream_adoption_candidates = dict(
        runtime.get("runtime_dream_adoption_candidates") or {}
    )
    dream_influence_proposals = dict(
        runtime.get("runtime_dream_influence_proposals") or {}
    )
    self_authored_prompt_proposals = dict(
        runtime.get("runtime_self_authored_prompt_proposals") or {}
    )
    prompt_evolution = dict(runtime.get("runtime_prompt_evolution") or {})
    user_understanding_signals = dict(
        runtime.get("runtime_user_understanding_signals") or {}
    )
    remembered_fact_signals = dict(runtime.get("runtime_remembered_fact_signals") or {})
    private_inner_note_signals = dict(
        runtime.get("runtime_private_inner_note_signals") or {}
    )
    private_initiative_tension_signals = dict(
        runtime.get("runtime_private_initiative_tension_signals") or {}
    )
    private_inner_interplay_signals = dict(
        runtime.get("runtime_private_inner_interplay_signals") or {}
    )
    private_state_snapshots = dict(runtime.get("runtime_private_state_snapshots") or {})
    diary_synthesis_signals = dict(runtime.get("runtime_diary_synthesis_signals") or {})
    private_temporal_curiosity_states = dict(
        runtime.get("runtime_private_temporal_curiosity_states") or {}
    )
    inner_visible_support_signals = dict(
        runtime.get("runtime_inner_visible_support_signals") or {}
    )
    regulation_homeostasis_signals = dict(
        runtime.get("runtime_regulation_homeostasis_signals") or {}
    )
    relation_state_signals = dict(runtime.get("runtime_relation_state_signals") or {})
    relation_continuity_signals = dict(
        runtime.get("runtime_relation_continuity_signals") or {}
    )
    meaning_significance_signals = dict(
        runtime.get("runtime_meaning_significance_signals") or {}
    )
    temperament_tendency_signals = dict(
        runtime.get("runtime_temperament_tendency_signals") or {}
    )
    self_narrative_continuity_signals = dict(
        runtime.get("runtime_self_narrative_continuity_signals") or {}
    )
    metabolism_state_signals = dict(
        runtime.get("runtime_metabolism_state_signals") or {}
    )
    release_marker_signals = dict(runtime.get("runtime_release_marker_signals") or {})
    consolidation_target_signals = dict(
        runtime.get("runtime_consolidation_target_signals") or {}
    )
    selective_forgetting_candidates = dict(
        runtime.get("runtime_selective_forgetting_candidates") or {}
    )
    attachment_topology_signals = dict(
        runtime.get("runtime_attachment_topology_signals") or {}
    )
    loyalty_gradient_signals = dict(
        runtime.get("runtime_loyalty_gradient_signals") or {}
    )
    autonomy_pressure_signals = dict(
        runtime.get("runtime_autonomy_pressure_signals") or {}
    )
    proactive_loop_lifecycle_signals = dict(
        runtime.get("runtime_proactive_loop_lifecycle_signals") or {}
    )
    proactive_question_gates = dict(
        runtime.get("runtime_proactive_question_gates") or {}
    )
    webchat_execution_pilot = dict(runtime.get("runtime_webchat_execution_pilot") or {})
    self_narrative_self_model_review_bridge = dict(
        runtime.get("runtime_self_narrative_self_model_review_bridge") or {}
    )
    executive_contradiction_signals = dict(
        runtime.get("runtime_executive_contradiction_signals") or {}
    )
    private_temporal_promotion_signals = dict(
        runtime.get("runtime_private_temporal_promotion_signals") or {}
    )
    chronicle_consolidation_signals = dict(
        runtime.get("runtime_chronicle_consolidation_signals") or {}
    )
    chronicle_consolidation_briefs = dict(
        runtime.get("runtime_chronicle_consolidation_briefs") or {}
    )
    chronicle_consolidation_proposals = dict(
        runtime.get("runtime_chronicle_consolidation_proposals") or {}
    )
    user_md_update_proposals = dict(
        runtime.get("runtime_user_md_update_proposals") or {}
    )
    memory_md_update_proposals = dict(
        runtime.get("runtime_memory_md_update_proposals") or {}
    )
    selfhood_proposals = dict(runtime.get("runtime_selfhood_proposals") or {})
    world_model_signals = dict(runtime.get("runtime_world_model_signals") or {})
    runtime_awareness_signals = dict(runtime.get("runtime_awareness_signals") or {})
    runtime_work = dict(runtime.get("runtime_work") or {})
    emergent_signals = dict(runtime.get("runtime_emergent_signals") or {})
    heartbeat = dict(runtime.get("heartbeat_runtime") or {})
    private_brain = build_private_brain_surface()
    session_distillation = build_session_distillation_surface()
    heartbeat_state = heartbeat.get("state") or {}
    self_knowledge = build_runtime_self_knowledge_map(heartbeat_state=heartbeat_state)
    cognitive_frame = build_cognitive_frame(
        self_knowledge=self_knowledge,
        heartbeat_state=heartbeat_state,
    )

    payload = {
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
                runtime_work,
            ),
            "emergent": _jarvis_emergent_summary(emergent_signals),
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
            "prompt_evolution": prompt_evolution,
            "user_understanding_signals": user_understanding_signals,
            "private_inner_note_signals": private_inner_note_signals,
            "private_initiative_tension_signals": private_initiative_tension_signals,
            "private_inner_interplay_signals": private_inner_interplay_signals,
            "private_state_snapshots": private_state_snapshots,
            "diary_synthesis_signals": diary_synthesis_signals,
            "private_temporal_curiosity_states": private_temporal_curiosity_states,
            "inner_visible_support_signals": inner_visible_support_signals,
            "regulation_homeostasis_signals": regulation_homeostasis_signals,
            "relation_state_signals": relation_state_signals,
            "relation_continuity_signals": relation_continuity_signals,
            "meaning_significance_signals": meaning_significance_signals,
            "temperament_tendency_signals": temperament_tendency_signals,
            "self_narrative_continuity_signals": self_narrative_continuity_signals,
            "metabolism_state_signals": metabolism_state_signals,
            "release_marker_signals": release_marker_signals,
            "consolidation_target_signals": consolidation_target_signals,
            "selective_forgetting_candidates": selective_forgetting_candidates,
            "attachment_topology_signals": attachment_topology_signals,
            "loyalty_gradient_signals": loyalty_gradient_signals,
            "autonomy_pressure_signals": autonomy_pressure_signals,
            "proactive_loop_lifecycle_signals": proactive_loop_lifecycle_signals,
            "proactive_question_gates": proactive_question_gates,
            "webchat_execution_pilot": webchat_execution_pilot,
            "self_narrative_self_model_review_bridge": self_narrative_self_model_review_bridge,
            "executive_contradiction_signals": executive_contradiction_signals,
            "private_temporal_promotion_signals": private_temporal_promotion_signals,
            "chronicle_consolidation_signals": chronicle_consolidation_signals,
            "chronicle_consolidation_briefs": chronicle_consolidation_briefs,
            "chronicle_consolidation_proposals": chronicle_consolidation_proposals,
            "user_md_update_proposals": user_md_update_proposals,
            "memory_md_update_proposals": memory_md_update_proposals,
            "selfhood_proposals": selfhood_proposals,
            "emergent_signals": emergent_signals,
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
            "runtime_work": runtime_work,
        },
        "heartbeat": heartbeat,
        "brain": {
            "private_brain": private_brain,
            "session_distillation": session_distillation,
        },
        "self_knowledge": self_knowledge,
        "cognitive_frame": cognitive_frame,
    }
    return _store_cached_mc_payload("jarvis", 5.0, payload)  # type: ignore[return-value]


@router.get("/cognitive-frame")
def mc_cognitive_frame() -> dict:
    with runtime_surface_cache():
        return build_cognitive_frame()


@router.get("/attention-budget")
def mc_attention_budget() -> dict:
    """Return attention budget traces for all prompt paths."""
    bundle = _mc_runtime_inspection_bundle()
    attention_snapshot = dict(bundle.get("attention_budget") or {})
    # Live runtime traces from the last actual prompt assembly
    from core.services.prompt_contract import get_last_attention_traces

    live_traces = get_last_attention_traces()
    return {
        **attention_snapshot,
        "live_traces": live_traces,
    }


@router.get("/conflict-resolution")
def mc_conflict_resolution() -> dict:
    """Return the last conflict resolution trace."""
    from core.services.conflict_resolution import get_last_conflict_trace

    trace = get_last_conflict_trace()
    return {"trace": trace, "active": trace is not None}


@router.get("/self-code-changes")
def mc_self_code_changes() -> dict:
    """Return Jarvis' recent self-mutations — files he wrote or edited in his own runtime."""
    from core.services.self_mutation_lineage import build_self_mutation_lineage_surface
    return build_self_mutation_lineage_surface(limit=50)


@router.get("/self-deception-guard")
def mc_self_deception_guard() -> dict:
    """Return the last self-deception guard trace."""
    from core.services.self_deception_guard import get_last_guard_trace

    trace = get_last_guard_trace()
    return {"trace": trace, "active": trace is not None}


@router.get("/witness-daemon")
def mc_witness_daemon() -> dict:
    """Return the current witness daemon state."""
    from core.services.witness_signal_tracking import (
        get_witness_daemon_state,
    )

    return get_witness_daemon_state()


@router.get("/inner-voice-daemon")
def mc_inner_voice_daemon() -> dict:
    """Return the current inner voice daemon state."""
    from core.services.inner_voice_daemon import (
        get_inner_voice_daemon_state,
    )

    return get_inner_voice_daemon_state()


@router.get("/internal-cadence")
def mc_internal_cadence() -> dict:
    """Return the current internal cadence layer state."""
    from core.services.internal_cadence import get_cadence_state

    return get_cadence_state()


@router.get("/emergent-signals")
def mc_emergent_signals() -> dict:
    """Return current bounded emergent inner signals."""
    return build_runtime_emergent_signal_surface(limit=8)


@router.get("/self-knowledge")
def mc_self_knowledge() -> dict:
    with runtime_surface_cache():
        return build_runtime_self_knowledge_map()


@router.get("/runtime-self-model")
def mc_runtime_self_model() -> dict:
    """Return the current runtime self-model snapshot."""
    bundle = _mc_runtime_inspection_bundle()
    return dict(bundle.get("runtime_self_model") or {})


@router.get("/self-critique")
def mc_self_critique() -> dict:
    """Return the current self-critique runtime surface."""
    return build_self_critique_surface()


@router.get("/creative-journal")
def mc_creative_journal() -> dict:
    """Return the current private creative journal surface."""
    return build_creative_journal_surface()


@router.get("/finitude")
def mc_finitude() -> dict:
    """Return Jarvis's bounded finitude and transition surface."""
    return build_finitude_surface()


@router.get("/dream-distillation")
def mc_dream_distillation() -> dict:
    """Return the current dream residue distillation surface."""
    return build_dream_distillation_surface()


@router.get("/unconscious-temperature-field")
def mc_unconscious_temperature_field() -> dict:
    """Return the current bounded user temperature field surface."""
    return build_unconscious_temperature_field_surface()


@router.get("/embodied-state")
def mc_embodied_state() -> dict:
    """Return the current bounded embodied host/body state."""
    return build_embodied_state_surface()


# Living Mind daemon surface routes extracted to mission_control_living_mind.py
# (Boy Scout rule — routes with in-memory proxy support live there)
from apps.api.jarvis_api.routes.mission_control_living_mind import router as _living_mind_router
router.include_router(_living_mind_router)


@router.get("/affective-meta-state")
def mc_affective_meta_state() -> dict:
    """Return the current bounded affective/meta runtime state."""
    return build_affective_meta_state_surface()


@router.get("/emotion-concepts")
def mc_emotion_concepts() -> dict:
    """Return active Lag-2 emotion concept signals and their Lag-1 influence deltas."""
    try:
        from core.services.emotion_concepts import build_emotion_concept_surface
        return build_emotion_concept_surface()
    except Exception as exc:
        return {"active": False, "active_count": 0, "concepts": [], "error": str(exc)}


@router.get("/experiential-runtime-context")
def mc_experiential_runtime_context() -> dict:
    """Return the current bounded experiential runtime context (body/tone/intermittence/pressure)."""
    bundle = _mc_runtime_inspection_bundle()
    return dict(bundle.get("experiential_runtime_context") or {})


@router.get("/epistemic-runtime-state")
def mc_epistemic_runtime_state() -> dict:
    """Return the current bounded epistemic runtime state."""
    return build_epistemic_runtime_state_surface()


@router.get("/loop-runtime")
def mc_loop_runtime() -> dict:
    """Return the current bounded loop runtime state."""
    return build_loop_runtime_surface()


@router.get("/idle-consolidation")
def mc_idle_consolidation() -> dict:
    """Return the current bounded sleep / idle consolidation state."""
    return build_idle_consolidation_surface()


@router.get("/dream-articulation")
def mc_dream_articulation() -> dict:
    """Return the current bounded dream articulation state."""
    return build_dream_articulation_surface()


@router.get("/prompt-evolution")
def mc_prompt_evolution() -> dict:
    """Return the current bounded runtime prompt evolution state."""
    return build_prompt_evolution_runtime_surface()


@router.get("/dream-influence")
def mc_dream_influence() -> dict:
    """Return the current bounded dream influence runtime state."""
    cached = _get_cached_mc_payload("dream-influence", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = build_dream_influence_runtime_surface()
    return _store_cached_mc_payload("dream-influence", 10.0, payload)  # type: ignore[return-value]


@router.get("/subagent-ecology")
def mc_subagent_ecology() -> dict:
    """Return the current bounded internal subagent ecology state."""
    return build_subagent_ecology_surface()


@router.get("/council-runtime")
def mc_council_runtime() -> dict:
    """Return the current bounded internal council runtime state."""
    return build_council_runtime_surface()


@router.get("/agents")
def mc_agents(limit: int = 100) -> dict:
    """Return live and persistent agent runtime state for Mission Control."""
    return build_agent_runtime_surface(limit=limit)


@router.get("/agents/{agent_id}")
def mc_agent_detail(agent_id: str) -> dict:
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return payload


@router.get("/agents/{agent_id}/messages")
def mc_agent_messages(agent_id: str) -> dict:
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "messages": payload.get("messages") or [],
        "count": payload.get("message_count") or 0,
    }


@router.get("/agents/{agent_id}/runs")
def mc_agent_runs(agent_id: str) -> dict:
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "runs": payload.get("runs") or [],
    }


@router.get("/agents/{agent_id}/tool-calls")
def mc_agent_tool_calls(agent_id: str) -> dict:
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "tool_calls": payload.get("tool_calls") or [],
        "count": payload.get("tool_call_count") or 0,
    }


@router.get("/watcher-lineage")
def mc_watcher_lineage() -> dict:
    """Return persistent watcher history — agents with kind=persistent-watcher."""
    from core.services.agent_runtime import build_agent_runtime_surface, list_agent_runs
    surface = build_agent_runtime_surface(limit=200)
    all_agents = surface.get("agents") or []
    watchers = [a for a in all_agents if str(a.get("kind") or "") == "persistent-watcher"]
    result = []
    for w in watchers[:20]:
        agent_id = str(w.get("agent_id") or "")
        runs = list_agent_runs(agent_id=agent_id, limit=5)
        ctx = w.get("context") or {}
        result.append({
            "agent_id": agent_id,
            "name": str(w.get("name") or w.get("goal") or agent_id)[:80],
            "goal": str(w.get("goal") or "")[:200],
            "status": str(w.get("status") or ""),
            "spawn_depth": int((ctx or {}).get("spawn_depth") or 0),
            "next_wake_at": str(w.get("next_wake_at") or ""),
            "completed_at": str(w.get("completed_at") or ""),
            "tokens_burned": int(w.get("tokens_burned") or 0),
            "recent_runs": [
                {
                    "run_id": str(r.get("run_id") or ""),
                    "status": str(r.get("status") or ""),
                    "output_summary": str(r.get("output_summary") or "")[:300],
                    "finished_at": str(r.get("finished_at") or ""),
                }
                for r in runs
            ],
        })
    return {"watchers": result, "watcher_count": len(result)}


@router.get("/agent-lineage")
def mc_agent_lineage() -> dict:
    """Return full agent spawn lineage — parent→child chains with outcomes."""
    import json as _json
    from core.services.agent_runtime import build_agent_runtime_surface
    from core.services.agent_outcomes_log import get_recent_agent_outcomes

    surface = build_agent_runtime_surface(limit=200)
    all_agents = surface.get("agents") or []
    outcomes = get_recent_agent_outcomes(limit=50)
    outcome_by_id = {str(o.get("agent_id") or ""): o for o in outcomes}

    def _build_node(agent: dict) -> dict:
        agent_id = str(agent.get("agent_id") or "")
        ctx: dict = {}
        try:
            ctx = _json.loads(str(agent.get("context_json") or "{}"))
        except Exception:
            pass
        outcome = outcome_by_id.get(agent_id)
        children = [
            _build_node(a) for a in all_agents
            if str((lambda c: c.get("parent_agent_id") or "")(
                _json.loads(str(a.get("context_json") or "{}"))
            )) == agent_id
        ]
        return {
            "agent_id": agent_id,
            "name": str(agent.get("name") or agent.get("goal") or agent_id)[:80],
            "goal": str(agent.get("goal") or "")[:200],
            "status": str(agent.get("status") or ""),
            "kind": str(agent.get("kind") or "solo-task"),
            "spawn_depth": int(ctx.get("spawn_depth") or 0),
            "parent_agent_id": str(ctx.get("parent_agent_id") or "jarvis"),
            "tokens_burned": int(agent.get("tokens_burned") or 0),
            "created_at": str(agent.get("created_at") or ""),
            "completed_at": str(agent.get("completed_at") or ""),
            "outcome_summary": str(outcome.get("outcome") or "")[:200] if outcome else None,
            "children": children,
        }

    # Build forest: root nodes are those with parent = "jarvis" or no parent
    roots = [
        a for a in all_agents
        if str((_json.loads(str(a.get("context_json") or "{}")) or {}).get("parent_agent_id") or "jarvis") == "jarvis"
    ]
    tree = [_build_node(a) for a in roots[:30]]
    total_agents = len(all_agents)
    max_depth = max(
        (int((_json.loads(str(a.get("context_json") or "{}")) or {}).get("spawn_depth") or 0)
         for a in all_agents), default=0
    )
    return {
        "tree": tree,
        "total_agents": total_agents,
        "root_count": len(tree),
        "max_spawn_depth": max_depth,
    }


@router.get("/council-model-config")
def mc_get_council_model_config() -> dict:
    """Return persisted per-role model overrides."""
    import json
    from core.runtime.config import CONFIG_DIR
    path = CONFIG_DIR / "council_models.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"role_models": []}


@router.post("/council-model-config")
def mc_set_council_model_config(payload: dict) -> dict:
    """Persist per-role model overrides. payload: {role_models: [{role, provider, model}]}"""
    import json
    from core.runtime.config import CONFIG_DIR
    role_models = [
        {
            "role": str(item.get("role") or ""),
            "provider": str(item.get("provider") or ""),
            "model": str(item.get("model") or ""),
        }
        for item in (payload.get("role_models") or [])
        if item.get("role")
    ]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "council_models.json"
    path.write_text(json.dumps({"role_models": role_models}, indent=2))
    return {"role_models": role_models, "saved": True}


@router.get("/council-activation-config")
def mc_get_council_activation_config() -> dict:
    """Return council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR as _cfg_dir
    path = _cfg_dir / "council_activation.json"
    defaults: dict = {"sensitivity": "balanced", "auto_convene": True}
    if path.exists():
        try:
            saved = json.loads(path.read_text())
            return {**defaults, **saved}
        except Exception:
            pass
    return defaults


@router.post("/council-activation-config")
def mc_set_council_activation_config(payload: dict) -> dict:
    """Persist council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR as _cfg_dir
    allowed_sensitivities = {"conservative", "balanced", "minimal"}
    sensitivity = str(payload.get("sensitivity") or "balanced")
    if sensitivity not in allowed_sensitivities:
        sensitivity = "balanced"
    auto_convene = bool(payload.get("auto_convene", True))
    config = {"sensitivity": sensitivity, "auto_convene": auto_convene}
    _cfg_dir.mkdir(parents=True, exist_ok=True)
    (_cfg_dir / "council_activation.json").write_text(json.dumps(config, indent=2))
    return {**config, "saved": True}


@router.get("/council")
def mc_council(limit: int = 40) -> dict:
    """Return roster and council sessions for Mission Control."""
    return build_council_surface(limit=limit)


@router.get("/council/{council_id}")
def mc_council_detail(council_id: str) -> dict:
    payload = build_council_detail_surface(council_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="council-not-found")
    return payload


@router.get("/council/{council_id}/messages")
def mc_council_messages(council_id: str) -> dict:
    payload = build_council_detail_surface(council_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="council-not-found")
    return {
        "council_id": council_id,
        "messages": payload.get("messages") or [],
    }


@router.post("/runtime/agents/spawn")
def mc_spawn_agent(payload: dict) -> dict:
    return spawn_agent_task(
        role=str(payload.get("role") or "researcher"),
        goal=str(payload.get("goal") or ""),
        system_prompt=str(payload.get("system_prompt") or ""),
        tool_policy=str(payload.get("tool_policy") or ""),
        allowed_tools=list(payload.get("allowed_tools") or []),
        parent_agent_id=str(payload.get("parent_agent_id") or "jarvis"),
        persistent=bool(payload.get("persistent", False)),
        ttl_seconds=int(payload.get("ttl_seconds") or 0),
        budget_tokens=int(payload.get("budget_tokens") or 0),
        context=dict(payload.get("context") or {}),
        result_contract=dict(payload.get("result_contract") or {}),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
        auto_execute=bool(payload.get("auto_execute", True)),
        provider=str(payload.get("provider") or ""),
        model=str(payload.get("model") or ""),
    )


@router.post("/runtime/agents/{agent_id}/execute")
def mc_execute_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return execute_agent_task(
        agent_id=agent_id,
        thread_id=str(payload.get("thread_id") or ""),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
    )


@router.post("/runtime/agents/{agent_id}/message")
def mc_message_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return send_message_to_agent(
        agent_id=agent_id,
        content=str(payload.get("content") or ""),
        role=str(payload.get("role") or "user"),
        kind=str(payload.get("kind") or "jarvis-message"),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
        auto_execute=bool(payload.get("auto_execute", True)),
    )


@router.post("/runtime/agents/{agent_id}/peer-message")
def mc_peer_message_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return send_peer_message(
        from_agent_id=agent_id,
        to_agent_id=str(payload.get("to_agent_id") or ""),
        content=str(payload.get("content") or ""),
        kind=str(payload.get("kind") or "peer-message"),
    )


@router.post("/runtime/agents/{agent_id}/schedule")
def mc_schedule_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return schedule_agent_task(
        agent_id=agent_id,
        schedule_kind=str(payload.get("schedule_kind") or "interval-seconds"),
        delay_seconds=int(payload.get("delay_seconds") or 900),
        schedule_expr=str(payload.get("schedule_expr") or ""),
        activate=bool(payload.get("activate", True)),
    )


@router.post("/runtime/agents/run-due")
def mc_run_due_agents(payload: dict | None = None) -> dict:
    payload = payload or {}
    return run_due_agent_schedules(limit=int(payload.get("limit") or 10))


@router.post("/runtime/agents/{agent_id}/cancel")
def mc_cancel_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return cancel_agent(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/agents/{agent_id}/suspend")
def mc_suspend_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return suspend_agent(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/agents/{agent_id}/resume")
def mc_resume_agent(agent_id: str) -> dict:
    return resume_agent(agent_id)


@router.post("/runtime/agents/{agent_id}/expire")
def mc_expire_agent(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return expire_agent(agent_id, reason=str(payload.get("reason") or ""))


@router.post("/runtime/agents/{agent_id}/promote")
def mc_promote_agent_result(agent_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return promote_agent_result(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/council/spawn")
def mc_spawn_council(payload: dict) -> dict:
    return create_council_session_runtime(
        topic=str(payload.get("topic") or ""),
        roles=list(payload.get("roles") or []),
        owner_agent_id=str(payload.get("owner_agent_id") or "jarvis"),
        member_models=list(payload.get("member_models") or []),
    )


@router.post("/runtime/swarm/spawn")
def mc_spawn_swarm(payload: dict) -> dict:
    return create_swarm_session_runtime(
        topic=str(payload.get("topic") or ""),
        roles=list(payload.get("roles") or []),
        owner_agent_id=str(payload.get("owner_agent_id") or "jarvis"),
        member_models=list(payload.get("member_models") or []),
    )


@router.post("/runtime/council/{council_id}/message")
def mc_message_council(council_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    return post_council_message(
        council_id=council_id,
        content=str(payload.get("content") or ""),
        kind=str(payload.get("kind") or "jarvis-note"),
        role=str(payload.get("role") or "user"),
    )


@router.post("/runtime/council/{council_id}/run-round")
def mc_run_council_round(council_id: str) -> dict:
    return run_council_round(council_id)


@router.post("/runtime/swarm/{council_id}/run-round")
def mc_run_swarm_round(council_id: str) -> dict:
    return run_swarm_round(council_id)


@router.get("/adaptive-planner")
def mc_adaptive_planner() -> dict:
    """Return the current bounded adaptive planner runtime state."""
    return build_adaptive_planner_runtime_surface()


@router.get("/adaptive-reasoning")
def mc_adaptive_reasoning() -> dict:
    """Return the current bounded adaptive reasoning runtime state."""
    cached = _get_cached_mc_payload("adaptive-reasoning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = build_adaptive_reasoning_runtime_surface()
    return _store_cached_mc_payload("adaptive-reasoning", 10.0, payload)  # type: ignore[return-value]


@router.get("/guided-learning")
def mc_guided_learning() -> dict:
    """Return the current bounded guided learning runtime state."""
    cached = _get_cached_mc_payload("guided-learning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = build_guided_learning_runtime_surface()
    return _store_cached_mc_payload("guided-learning", 10.0, payload)  # type: ignore[return-value]


@router.get("/adaptive-learning")
def mc_adaptive_learning() -> dict:
    """Return the current bounded adaptive learning runtime state."""
    cached = _get_cached_mc_payload("adaptive-learning", 10.0)
    if cached is not None:
        return cached  # type: ignore[return-value]
    payload = build_adaptive_learning_runtime_surface()
    return _store_cached_mc_payload("adaptive-learning", 10.0, payload)  # type: ignore[return-value]


@router.get("/self-system-code-awareness")
def mc_self_system_code_awareness() -> dict:
    """Return the current bounded self system / code awareness runtime state."""
    return build_self_system_code_awareness_surface()


@router.get("/tool-intent")
def mc_tool_intent() -> dict:
    """Return the current bounded approval-gated tool intent runtime state."""
    return build_tool_intent_runtime_surface()


@router.get("/approval-feedback")
def mc_approval_feedback() -> dict:
    return build_approval_feedback_surface()


@router.post("/tool-intent/approve")
def mc_approve_tool_intent() -> dict:
    tool_intent = build_tool_intent_runtime_surface()
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
        "tool_intent": build_tool_intent_runtime_surface(),
    }


@router.post("/tool-intent/deny")
def mc_deny_tool_intent() -> dict:
    tool_intent = build_tool_intent_runtime_surface()
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
        "tool_intent": build_tool_intent_runtime_surface(),
    }


@router.get("/private-brain")
def mc_private_brain() -> dict:
    return {
        "private_brain": build_private_brain_surface(limit=30),
        "session_distillation": build_session_distillation_surface(limit=10),
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
    payload = _get_or_build_cached_mc_payload(
        "runtime",
        3.0,
        _mc_runtime_uncached,
    )
    return payload  # type: ignore[return-value]


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


@router.get("/provider-models")
def mc_provider_models(provider: str = "", auth_profile: str = "") -> dict:
    if not str(provider).strip():
        raise HTTPException(status_code=400, detail="provider must be a non-empty string")
    return available_provider_models(
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


def _latest_item(items: list[dict]) -> dict | None:
    return items[0] if items else None


def _with_private_lane_source_discipline(item: dict | None) -> dict | None:
    if not item:
        return item
    source = str(item.get("source") or "")
    grounded = "private-runtime-grounded" in source
    return {
        **item,
        "private_lane_source_state": (
            "private-runtime-grounded" if grounded else "legacy-source-unknown"
        ),
        "contamination_state": (
            "decontaminated-from-visible-reply"
            if grounded
            else "legacy-contamination-unknown"
        ),
    }


def _private_lane_surface_summary(item: dict | None) -> dict[str, str]:
    normalized = _with_private_lane_source_discipline(item)
    return {
        "current_source_state": str(
            (normalized or {}).get("private_lane_source_state")
            or "legacy-source-unknown"
        ),
        "current_contamination_state": str(
            (normalized or {}).get("contamination_state")
            or "legacy-contamination-unknown"
        ),
    }


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


def _maybe_configure_live_main_agent_target(
    *, provider: str, model: str, auth_profile: str
) -> bool:
    if not provider or not model:
        return False

    models_surface = available_provider_models(
        provider=provider,
        auth_profile=auth_profile,
    )
    available = {
        str(item.get("id") or "").strip()
        for item in models_surface.get("models", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if model not in available:
        return False

    configured_profile = str(auth_profile or models_surface.get("auth_profile") or "").strip()
    if provider == "ollama":
        local_target = resolve_provider_router_target(lane="local")
        configure_provider_router_entry(
            provider="ollama",
            model=model,
            auth_mode="none",
            auth_profile="",
            base_url=str(
                models_surface.get("base_url")
                or local_target.get("base_url")
                or "http://127.0.0.1:11434"
            ),
            api_key="",
            lane="local",
            set_visible=False,
        )
        return True

    if provider == "github-copilot":
        configure_provider_router_entry(
            provider="github-copilot",
            model=model,
            auth_mode="oauth",
            auth_profile=configured_profile or "copilot",
            base_url="",
            api_key="",
            lane="visible",
            set_visible=False,
        )
        return True

    return False


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
        "last_execution_trace": get_last_visible_execution_trace(),
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
    normalized_notes = [
        item
        for item in (_with_private_lane_source_discipline(note) for note in notes)
        if item
    ]
    return {
        "active": bool(normalized_notes),
        "recent_notes": normalized_notes,
        "summary": _private_lane_surface_summary(_latest_item(normalized_notes)),
    }


def _private_self_model_surface() -> dict:
    model = get_private_self_model()
    return {
        "active": bool(model),
        "current": model,
    }


def _private_reflective_selection_surface() -> dict:
    signals = recent_private_reflective_selections(limit=5)
    normalized_signals = [
        item
        for item in (_with_private_lane_source_discipline(signal) for signal in signals)
        if item
    ]
    return {
        "active": bool(normalized_signals),
        "recent_signals": normalized_signals,
        "summary": _private_lane_surface_summary(_latest_item(normalized_signals)),
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
    voice = _current_protected_inner_voice()
    return {
        "active": bool(voice),
        "current": voice,
    }


def _current_protected_inner_voice() -> dict[str, object] | None:
    return _select_current_protected_inner_voice(
        list_recent_protected_inner_voices(limit=8)
    )


def _select_current_protected_inner_voice(
    voices: list[dict[str, object]],
) -> dict[str, object] | None:
    if not voices:
        return None
    latest = dict(voices[0])
    latest_created_at = _parse_runtime_iso_datetime(latest.get("created_at"))
    freshness_floor = (
        latest_created_at - _PROTECTED_VOICE_PRIORITY_WINDOW
        if latest_created_at is not None
        else None
    )
    best = latest
    best_score = _protected_inner_voice_priority(
        best,
        freshness_floor=freshness_floor,
    )
    for voice in voices[1:]:
        candidate = dict(voice)
        candidate_score = _protected_inner_voice_priority(
            candidate,
            freshness_floor=freshness_floor,
        )
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score
    return best


def _protected_inner_voice_priority(
    voice: dict[str, object],
    *,
    freshness_floor: datetime | None,
) -> tuple[int, int, int, str, int]:
    created_at = _parse_runtime_iso_datetime(voice.get("created_at"))
    is_fresh = (
        freshness_floor is None or created_at is None or created_at >= freshness_floor
    )
    source = str(voice.get("source") or "").strip()
    preferred = int(is_fresh and source in _PREFERRED_PROTECTED_VOICE_SOURCES)
    enriched = int(is_fresh and bool(voice.get("enriched")))
    freshness = int(is_fresh)
    generic_penalty = int(source == _TEMPLATE_PROTECTED_VOICE_SOURCE)
    created_sort = created_at.isoformat() if created_at is not None else ""
    identifier = int(voice.get("id") or 0)
    return (
        preferred,
        enriched,
        freshness,
        -generic_penalty,
        created_sort,
        identifier,
    )


def _parse_runtime_iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _private_inner_interplay_surface() -> dict:
    return build_private_inner_interplay(
        private_state=get_private_state(),
        protected_inner_voice=_current_protected_inner_voice(),
        private_development_state=get_private_development_state(),
        private_reflective_selection=_latest_item(
            recent_private_reflective_selections(limit=1)
        ),
    )


def _private_initiative_tension_surface() -> dict:
    return build_private_initiative_tension(
        private_state=get_private_state(),
        protected_inner_voice=_current_protected_inner_voice(),
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
    signal = _with_private_lane_source_discipline(
        get_private_temporal_promotion_signal()
    )
    return {
        "active": bool(signal),
        "current": signal,
        "summary": _private_lane_surface_summary(signal),
    }


def _private_promotion_decision_surface() -> dict:
    decision = _with_private_lane_source_discipline(get_private_promotion_decision())
    return {
        "active": bool(decision),
        "current": decision,
        "summary": _private_lane_surface_summary(decision),
    }


def _private_retained_memory_record_surface() -> dict:
    record = _with_private_lane_source_discipline(get_private_retained_memory_record())
    recent_records = [
        item
        for item in (
            _with_private_lane_source_discipline(candidate)
            for candidate in recent_private_retained_memory_records(limit=5)
        )
        if item
    ]
    return {
        "active": bool(record),
        "current": record,
        "recent_records": recent_records,
        "summary": _private_lane_surface_summary(record),
    }


def _private_retained_memory_projection_surface() -> dict:
    record = _with_private_lane_source_discipline(get_private_retained_memory_record())
    recent_records = [
        item
        for item in (
            _with_private_lane_source_discipline(candidate)
            for candidate in recent_private_retained_memory_records(limit=5)
        )
        if item
    ]
    projection = build_private_retained_memory_projection(
        current_record=record,
        recent_records=recent_records,
    )
    normalized_projection = _with_private_lane_source_discipline(projection)
    if normalized_projection is None:
        return projection
    return {
        **normalized_projection,
        "current": _with_private_lane_source_discipline(
            normalized_projection.get("current")
            if isinstance(normalized_projection.get("current"), dict)
            else None
        ),
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
    runtime_work: dict | None = None,
) -> dict[str, str]:
    relation = relation_state.get("current") or {}
    signal = promotion_signal.get("current") or {}
    world_summary = (world_model_signals or {}).get("summary") or {}
    runtime_awareness_summary = (runtime_awareness_signals or {}).get("summary") or {}
    runtime_work_summary = (runtime_work or {}).get("summary") or {}
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
        "runtime_work_count": str(
            (runtime_work_summary.get("task_count") or 0)
            + (runtime_work_summary.get("flow_count") or 0)
        ),
        "current_runtime_work": str(
            runtime_work_summary.get("current_focus") or "No active runtime work"
        ),
    }


def _jarvis_heartbeat_summary(heartbeat: dict) -> dict[str, str]:
    state = heartbeat.get("state") or {}
    embodied = heartbeat.get("embodied_state") or {}
    idle_consolidation = heartbeat.get("idle_consolidation") or {}
    idle_summary = idle_consolidation.get("summary") or {}
    idle_last_result = idle_consolidation.get("last_result") or {}
    dream_articulation = heartbeat.get("dream_articulation") or {}
    dream_summary = dream_articulation.get("summary") or {}
    dream_last_result = dream_articulation.get("last_result") or {}
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
        "embodied_state": str(embodied.get("state") or "unknown"),
        "idle_consolidation": str(
            idle_summary.get("last_state")
            or idle_last_result.get("consolidation_state")
            or "idle"
        ),
        "idle_consolidation_reason": str(
            idle_last_result.get("reason")
            or idle_summary.get("last_reason")
            or "no-run-yet"
        ),
        "dream_articulation": str(
            dream_summary.get("last_state")
            or dream_last_result.get("candidate_state")
            or "idle"
        ),
        "dream_articulation_reason": str(
            dream_last_result.get("reason")
            or dream_summary.get("last_reason")
            or "no-run-yet"
        ),
    }


def _runtime_work_surface() -> dict[str, object]:
    queued_tasks = list_tasks(status="queued", limit=8)
    running_tasks = list_tasks(status="running", limit=8)
    blocked_tasks = list_tasks(status="blocked", limit=8)
    queued_flows = list_flows(status="queued", limit=8)
    running_flows = list_flows(status="running", limit=8)
    blocked_flows = list_flows(status="blocked", limit=8)
    browser_body = next(iter(list_browser_bodies(limit=2)), {})
    memory_paths = workspace_memory_paths()
    curated_exists = memory_paths["curated_memory"].exists()
    # Accept any daily file written within the last 7 days
    _today = datetime.now(UTC).date()
    _daily_dir = memory_paths["daily_dir"]
    daily_exists = any(
        (_daily_dir / f"{(_today - timedelta(days=d)).isoformat()}.md").exists()
        for d in range(8)
    )
    current_focus = (
        str(
            (running_tasks or queued_tasks or blocked_tasks or [{}])[0].get("goal")
            or ""
        ).strip()
        or str(
            (running_flows or queued_flows or blocked_flows or [{}])[0].get(
                "current_step"
            )
            or ""
        ).strip()
        or "No active runtime work"
    )
    return {
        "active": bool(
            queued_tasks
            or running_tasks
            or blocked_tasks
            or queued_flows
            or running_flows
            or blocked_flows
        ),
        "tasks": {
            "queued": queued_tasks,
            "running": running_tasks,
            "blocked": blocked_tasks,
        },
        "flows": {
            "queued": queued_flows,
            "running": running_flows,
            "blocked": blocked_flows,
        },
        "browser_body": browser_body,
        "layered_memory": {
            "daily_memory_path": str(memory_paths["daily_memory"]),
            "daily_memory_exists": daily_exists,
            "curated_memory_path": str(memory_paths["curated_memory"]),
            "curated_memory_exists": curated_exists,
        },
        "summary": {
            "task_count": len(queued_tasks) + len(running_tasks) + len(blocked_tasks),
            "flow_count": len(queued_flows) + len(running_flows) + len(blocked_flows),
            "browser_body_status": str(browser_body.get("status") or "absent"),
            "current_focus": current_focus,
            "daily_memory_state": "present" if daily_exists else "missing",
            "curated_memory_state": "present" if curated_exists else "missing",
        },
    }


def _jarvis_emergent_summary(emergent_signals: dict) -> dict[str, object]:
    summary = emergent_signals.get("summary") or {}
    return {
        "active_count": int(summary.get("active_count") or 0),
        "current_signal": str(
            summary.get("current_signal") or "No active emergent inner signal"
        ),
        "current_status": str(summary.get("current_status") or "none"),
        "current_lifecycle_state": str(
            summary.get("current_lifecycle_state") or "none"
        ),
        "authority": "candidate-only",
        "visibility": "internal-only",
    }


def _jarvis_emergent_summary(emergent_signals: dict) -> dict[str, object]:
    summary = emergent_signals.get("summary") or {}
    return {
        "active_count": int(summary.get("active_count") or 0),
        "current_signal": str(
            summary.get("current_signal") or "No active emergent inner signal"
        ),
        "current_status": str(summary.get("current_status") or "none"),
        "current_lifecycle_state": str(
            summary.get("current_lifecycle_state") or "none"
        ),
        "authority": "candidate-only",
        "visibility": "internal-only",
    }


def _preview_text(value: str, *, limit: int = 96) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:limit] + ("…" if len(text) > limit else "")


# ---------------------------------------------------------------------------
# Cognitive Architecture Endpoints
# ---------------------------------------------------------------------------


@router.get("/cognitive-state-injection")
def mc_cognitive_state_injection() -> dict:
    """Show exactly what cognitive state was injected into the last visible prompt."""
    from core.services.cognitive_state_assembly import (
        build_cognitive_state_injection_surface,
    )

    return build_cognitive_state_injection_surface()


@router.get("/personality-vector")
def mc_personality_vector() -> dict:
    """Return the current personality vector with version history."""
    from core.services.personality_vector import (
        build_personality_vector_surface,
    )

    return build_personality_vector_surface()


@router.get("/taste-profile")
def mc_taste_profile() -> dict:
    """Return the current taste profile (code/design/communication)."""
    from core.services.taste_profile import build_taste_profile_surface

    return build_taste_profile_surface()


@router.get("/chronicle")
def mc_chronicle() -> dict:
    """Return chronicle entries (narrative autobiography)."""
    from core.services.chronicle_engine import build_chronicle_surface

    return build_chronicle_surface()


@router.get("/relationship-texture")
def mc_relationship_texture() -> dict:
    """Return the relationship texture (trust, humor, corrections, etc)."""
    from core.services.relationship_texture import (
        build_relationship_texture_surface,
    )

    return build_relationship_texture_surface()


@router.get("/compass")
def mc_compass() -> dict:
    """Return the current strategic compass bearing."""
    from core.services.compass_engine import build_compass_surface

    return build_compass_surface()


@router.get("/rhythm")
def mc_rhythm() -> dict:
    """Return the current rhythm/tidal state (phase, energy, initiative)."""
    from core.services.rhythm_engine import build_rhythm_surface

    return build_rhythm_surface()


@router.get("/habits")
def mc_habits() -> dict:
    """Return habit patterns and friction signals."""
    from core.services.habit_tracker import build_habit_surface

    return build_habit_surface()


@router.get("/shared-language")
def mc_shared_language() -> dict:
    """Return shared language terms with the user."""
    from core.services.shared_language import (
        build_shared_language_surface,
    )

    return build_shared_language_surface()


@router.get("/mirror")
def mc_mirror() -> dict:
    """Return mirror self-reflection state."""
    from core.services.mirror_engine import build_mirror_surface

    return build_mirror_surface()


@router.get("/silence-signals")
def mc_silence_signals() -> dict:
    """Return silence detector state."""
    from core.services.silence_detector import build_silence_surface

    return build_silence_surface()


@router.get("/decisions")
def mc_decisions() -> dict:
    """Return the decision log."""
    from core.services.decision_log import build_decision_log_surface

    return build_decision_log_surface()


@router.get("/counterfactuals")
def mc_counterfactuals() -> dict:
    """Return counterfactual scenarios."""
    from core.services.counterfactual_engine import (
        build_counterfactual_surface,
    )

    return build_counterfactual_surface()


@router.get("/paradoxes")
def mc_paradoxes() -> dict:
    """Return active paradox tensions."""
    from core.services.paradox_tracker import build_paradox_surface

    return build_paradox_surface()


@router.get("/aesthetics")
def mc_aesthetics() -> dict:
    """Return aesthetic sense motifs."""
    from core.services.aesthetic_sense import build_aesthetic_surface

    return build_aesthetic_surface()


@router.get("/gut")
def mc_gut() -> dict:
    """Return gut intuition calibration state."""
    from core.services.gut_engine import build_gut_surface

    return build_gut_surface()


@router.get("/seeds")
def mc_seeds() -> dict:
    """Return prospective memory seeds."""
    from core.services.seed_system import build_seed_surface

    return build_seed_surface()


@router.get("/procedures")
def mc_procedures() -> dict:
    """Return learned procedures."""
    from core.services.procedure_bank import build_procedure_surface

    return build_procedure_surface()


@router.get("/temporal-context")
def mc_temporal_context() -> dict:
    """Return current temporal context."""
    from core.services.temporal_context import (
        build_temporal_context_surface,
    )

    return build_temporal_context_surface()


@router.get("/negotiations")
def mc_negotiations() -> dict:
    """Return internal negotiation trades."""
    from core.services.negotiation_engine import (
        build_negotiation_surface,
    )

    return build_negotiation_surface()


@router.get("/forgetting-curve")
def mc_forgetting_curve() -> dict:
    """Return memory decay / forgetting curve state."""
    from core.services.forgetting_curve import (
        build_forgetting_curve_surface,
    )

    return build_forgetting_curve_surface()


@router.get("/conversation-rhythm")
def mc_conversation_rhythm() -> dict:
    """Return conversation rhythm patterns."""
    from core.services.conversation_rhythm import (
        build_conversation_rhythm_surface,
    )

    return build_conversation_rhythm_surface()


@router.get("/self-experiments")
def mc_self_experiments() -> dict:
    """Return self-experiment A/B test state."""
    from core.services.self_experiments import (
        build_self_experiments_surface,
    )

    return build_self_experiments_surface()


@router.get("/anticipatory-context")
def mc_anticipatory_context() -> dict:
    """Return anticipatory context predictions."""
    from core.services.anticipatory_context import (
        build_anticipatory_context_surface,
    )

    return build_anticipatory_context_surface()


@router.get("/contract-evolution")
def mc_contract_evolution() -> dict:
    """Return identity contract evolution proposals."""
    from core.services.contract_evolution import (
        build_contract_evolution_surface,
    )

    return build_contract_evolution_surface()


@router.get("/dream-carry-over")
def mc_dream_carry_over() -> dict:
    """Return dream carry-over state (active dreams, archive)."""
    from core.services.dream_carry_over import (
        build_dream_carry_over_surface,
    )

    return build_dream_carry_over_surface()


@router.get("/apophenia-guard")
def mc_apophenia_guard() -> dict:
    """Return pattern skeptic state."""
    from core.services.apophenia_guard import (
        build_apophenia_guard_surface,
    )

    return build_apophenia_guard_surface()


@router.get("/user-emotional-resonance")
def mc_user_emotional_resonance() -> dict:
    """Return user mood detection state."""
    from core.services.user_emotional_resonance import (
        build_user_emotional_resonance_surface,
    )

    return build_user_emotional_resonance_surface()


@router.get("/experiential-memories")
def mc_experiential_memories() -> dict:
    """Return experiential memories (lived experiences with emotion)."""
    from core.services.experiential_memory import (
        build_experiential_memory_surface,
    )

    return build_experiential_memory_surface()


@router.get("/living-heartbeat-cycle")
def mc_living_heartbeat_cycle() -> dict:
    """Return current life phase in heartbeat cycle."""
    from core.services.living_heartbeat_cycle import (
        build_living_heartbeat_cycle_surface,
    )

    return build_living_heartbeat_cycle_surface()


@router.get("/absence-awareness")
def mc_absence_awareness() -> dict:
    """Return absence detection and return brief."""
    from core.services.absence_awareness import (
        build_absence_awareness_surface,
    )

    return build_absence_awareness_surface()


# --- Consciousness Roadmap endpoints ---


@router.get("/flow-state")
def mc_flow_state() -> dict:
    from core.services.flow_state_detection import (
        build_flow_state_surface,
    )

    return build_flow_state_surface()


@router.get("/cross-signal-patterns")
def mc_cross_signal_patterns() -> dict:
    from core.services.cross_signal_analysis import (
        build_cross_signal_analysis_surface,
    )

    return build_cross_signal_analysis_surface()


@router.get("/self-surprises")
def mc_self_surprises() -> dict:
    from core.services.self_surprise_detection import (
        build_self_surprise_surface,
    )

    return build_self_surprise_surface()


@router.get("/narrative-identity")
def mc_narrative_identity() -> dict:
    from core.services.narrative_identity import (
        build_narrative_identity_surface,
    )

    return build_narrative_identity_surface()


@router.get("/gratitude")
def mc_gratitude() -> dict:
    from core.services.gratitude_tracker import build_gratitude_surface

    return build_gratitude_surface()


@router.get("/boundary-model")
def mc_boundary_model() -> dict:
    from core.services.boundary_awareness import (
        build_boundary_awareness_surface,
    )

    return build_boundary_awareness_surface()


@router.get("/emergent-goals")
def mc_emergent_goals() -> dict:
    from core.services.emergent_goals import build_emergent_goals_surface

    return build_emergent_goals_surface()


@router.get("/jarvis-agenda")
def mc_jarvis_agenda() -> dict:
    from core.services.emergent_goals import build_jarvis_agenda

    return {"agenda": build_jarvis_agenda()}


@router.get("/boredom")
def mc_boredom() -> dict:
    from core.services.boredom_engine import build_boredom_surface

    return build_boredom_surface()


@router.get("/formed-values")
def mc_formed_values() -> dict:
    from core.services.value_formation import build_formed_values_surface

    return build_formed_values_surface()


@router.get("/user-mental-model")
def mc_user_mental_model() -> dict:
    from core.services.user_theory_of_mind import (
        build_user_theory_of_mind_surface,
    )

    return build_user_theory_of_mind_surface()


@router.get("/self-compassion")
def mc_self_compassion() -> dict:
    from core.services.self_compassion import (
        build_self_compassion_surface,
    )

    return build_self_compassion_surface()


@router.get("/regret")
def mc_regret() -> dict:
    """Return the regret engine state — open/resolved regrets with lessons."""
    from core.services.regret_engine import build_regret_engine_surface

    return build_regret_engine_surface()


@router.get("/rupture-repair")
def mc_rupture_repair() -> dict:
    """Return rupture & repair state — relational tension tracking."""
    from core.services.rupture_repair import build_rupture_repair_surface

    return build_rupture_repair_surface()


@router.get("/silence-patterns")
def mc_silence_patterns() -> dict:
    """Return silence pattern detection — what the user is NOT saying."""
    from core.services.silence_patterns import build_silence_patterns_surface

    return build_silence_patterns_surface()


@router.get("/blind-spots")
def mc_blind_spots() -> dict:
    """Return self-model blind spots — patterns Jarvis hasn't seen yet."""
    from core.services.self_model_blind_spots import build_blind_spots_surface

    return build_blind_spots_surface()


@router.get("/dream-hypotheses")
def mc_dream_hypotheses() -> dict:
    """Return surprising dream-phase hypotheses linking disparate signals."""
    from core.services.dream_hypothesis_generator import build_dream_hypothesis_surface

    return build_dream_hypothesis_surface()


@router.get("/decisions-journal")
def mc_decisions_journal() -> dict:
    """Return decisions journal — moralsk beslutnings-log."""
    from core.services.decisions_journal import build_decisions_journal_surface

    return build_decisions_journal_surface()


@router.get("/epistemics")
def mc_epistemics() -> dict:
    """Return epistemic layers — i_know / i_believe / i_suspect / i_dont_know / i_was_wrong."""
    from core.services.epistemics import build_epistemics_surface

    return build_epistemics_surface()


@router.get("/emotional-controls")
def mc_emotional_controls() -> dict:
    """Return emotional state + whether it would gate kernel actions right now."""
    from core.services.emotional_controls import build_emotional_controls_surface

    return build_emotional_controls_surface()


@router.get("/mood-dialer")
def mc_mood_dialer() -> dict:
    """Return mood-dialed params: initiative_multiplier, confidence_threshold, style_preset."""
    from core.services.mood_dialer import build_mood_dialer_surface

    return build_mood_dialer_surface()


@router.get("/self-review-unified")
def mc_self_review_unified() -> dict:
    """Return unified self-review — periodic LLM-generated Jarvis self-audit."""
    from core.services.self_review_unified import build_self_review_surface

    return build_self_review_surface()


@router.get("/habits-pipeline")
def mc_habits_pipeline() -> dict:
    """Return habits + friction + automation-suggestions pipeline."""
    from core.services.habits_pipeline import build_habits_pipeline_surface

    return build_habits_pipeline_surface()


@router.get("/paradoxes-capture")
def mc_paradoxes_capture() -> dict:
    """Return captured paradoxes: Speed/Quality, Autonomy/Approval, Explore/Stabilize."""
    from core.services.paradoxes_capture import build_paradoxes_surface

    return build_paradoxes_surface()


@router.get("/shared-language-extended")
def mc_shared_language_extended() -> dict:
    """Return extended shorthand/shared-vocabulary developed with user."""
    from core.services.shared_language_extended import build_shared_language_extended_surface

    return build_shared_language_extended_surface()


@router.get("/procedure-bank-pipeline")
def mc_procedure_bank_pipeline() -> dict:
    """Return procedure bank — learned, pinned, trigger-matched routines."""
    from core.services.procedure_bank_pipeline import build_procedure_bank_surface

    return build_procedure_bank_surface()


@router.get("/negotiation-pipeline")
def mc_negotiation_pipeline() -> dict:
    """Return internal trade-off negotiation outcomes."""
    from core.services.negotiation_pipeline import build_negotiation_surface

    return build_negotiation_surface()


@router.get("/reflection-to-plan")
def mc_reflection_to_plan() -> dict:
    """Return reflective plans — reflections converted to executable steps."""
    from core.services.reflection_to_plan import build_reflection_to_plan_surface

    return build_reflection_to_plan_surface()


@router.get("/missions-pipeline")
def mc_missions_pipeline() -> dict:
    """Return multi-session missions: researcher/implementer/reviewer flow."""
    from core.services.missions_pipeline import build_missions_surface

    return build_missions_surface()


@router.get("/deep-analyzer")
def mc_deep_analyzer() -> dict:
    """Return deep analyzer capability — scoped codebase introspection."""
    from core.services.deep_analyzer import build_deep_analyzer_surface

    return build_deep_analyzer_surface()


@router.get("/learning-curriculum")
def mc_learning_curriculum() -> dict:
    from core.services.self_experiments import (
        generate_learning_curriculum,
    )

    return generate_learning_curriculum()


@router.get("/cadence-producers")
def mc_cadence_producers() -> dict:
    from core.services.cadence_producers import (
        build_cadence_producers_surface,
    )

    return build_cadence_producers_surface()


@router.get("/idle-thinking")
def mc_idle_thinking() -> dict:
    from core.services.idle_thinking import build_idle_thinking_surface

    return build_idle_thinking_surface()


# ---------------------------------------------------------------------------
# Consciousness Experiments
# ---------------------------------------------------------------------------

_KNOWN_EXPERIMENTS = [
    "recurrence_loop",
    "surprise_persistence",
    "global_workspace",
    "meta_cognition",
    "attention_blink",
]


@router.get("/experiments")
def mc_experiments() -> dict:
    """List all consciousness experiments with their enabled status."""
    from core.runtime.db import get_experiment_enabled
    return {
        "experiments": {
            eid: get_experiment_enabled(eid) for eid in _KNOWN_EXPERIMENTS
        }
    }


@router.post("/experiments/{experiment_id}/toggle")
def mc_experiment_toggle(experiment_id: str) -> dict:
    """Toggle a consciousness experiment on or off."""
    from fastapi import HTTPException
    from core.runtime.db import get_experiment_enabled, set_experiment_enabled
    if experiment_id not in _KNOWN_EXPERIMENTS:
        raise HTTPException(status_code=404, detail=f"Unknown experiment: {experiment_id}")
    current = get_experiment_enabled(experiment_id)
    set_experiment_enabled(experiment_id, not current)
    return {"experiment_id": experiment_id, "enabled": not current}


@router.get("/recurrence-state")
def mc_recurrence_state() -> dict:
    from core.services.recurrence_loop_daemon import build_recurrence_surface
    return build_recurrence_surface()


@router.get("/global-workspace")
def mc_global_workspace() -> dict:
    from core.services.broadcast_daemon import build_workspace_surface
    return build_workspace_surface()


@router.get("/layer-tensions")
def mc_layer_tensions() -> dict:
    """Return active inter-layer tensions — signals pulling in opposite directions."""
    from core.services.layer_tension_daemon import build_layer_tension_surface
    return build_layer_tension_surface()


@router.get("/meta-cognition")
def mc_meta_cognition() -> dict:
    from core.services.meta_cognition_daemon import build_meta_cognition_surface
    return build_meta_cognition_surface()


@router.get("/attention-profile")
def mc_attention_profile() -> dict:
    from core.services.attention_blink_test import build_attention_profile_surface
    return build_attention_profile_surface()


@router.get("/cognitive-core-experiments")
def mc_cognitive_core_experiments() -> dict:
    """Unified cognitive-core experiment surface for Mission Control."""
    from core.services.cognitive_core_experiments import (
        build_cognitive_core_experiments_surface,
    )
    return build_cognitive_core_experiments_surface()
