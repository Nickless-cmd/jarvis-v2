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
from core.services.modulator_witness import (
    build_modulator_witness_surface,
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

