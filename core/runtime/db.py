"""Facade for core.runtime.db submodules.

Genererer bagudkompatibel import-overflade for 5.317 eksisterende
import-sites. Alt nyt kode bør importere direkte fra submoduler
(fx core.runtime.db_core eller core.runtime.db_<theme>).

Split-historik: docs/superpowers/specs/2026-05-15-db-split-design.md

Note: init_db() + hele schema-laget (_ensure_*/_migrate_*) er flyttet til
core.runtime.db_schema (Fase 2 batch 7) og re-eksporteres i bunden af denne
fil for bagudkompatibilitet. db.py er nu et rent re-eksport-hub.
"""
from __future__ import annotations

import sqlite3

# === Phase 0 re-eksporter fra db_core ===
from core.runtime.db_core import (
    DB_PATH,
    _CONFIDENCE_RANKS,
    _EVIDENCE_CLASS_RANKS,
    _SOURCE_KIND_RANKS,
    ClosingConnection,
    connect,
    _rank_for,
    _stronger_ranked_value,
    _merge_text_fragments,
    set_runtime_state_value,
    get_runtime_state_value,
    _now_iso,
    _SIGNAL_TABLES_WITH_STATUS,
    _ENSURED_TABLES,
    _conn_db_id,
    _install_ensure_once_cache,
    _install_ensure_once_cache_for,
    invalidate_ensure_once_cache,
)

# === Phase 1 re-eksporter fra db_capability_approval ===
from core.runtime.db_capability_approval import (
    recent_capability_approval_requests,
    get_capability_approval_request,
    approve_capability_approval_request,
    record_capability_approval_request_execution,
    _capability_approval_request_from_row,
    _ensure_capability_approval_request_columns,
    latest_capability_approval_request,
    latest_approved_capability_approval_request,
    insert_approval_feedback,
    list_approval_feedback,
    approval_feedback_stats_by_tool,
    count_approval_feedback,
    _approval_feedback_from_row,
)









# ---------------------------------------------------------------------------
# Private brain records — persistent private inner continuity
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Session distillation records
# ---------------------------------------------------------------------------




def _session_distillation_record_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "distillation_id": row["distillation_id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "private_brain_count": int(row["private_brain_count"]),
        "workspace_memory_count": int(row["workspace_memory_count"]),
        "discard_count": int(row["discard_count"]),
        "summary": row["summary"],
        "detail": row["detail"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Cognitive Architecture — Accumulation Tables
# ---------------------------------------------------------------------------


# --- Personality Vector ---


# --- Taste Profile ---


# --- Chronicle ---




# --- Cognitive Episodes ---


# --- Relationship Texture ---


# --- Compass State ---


# --- Rhythm State ---


# --- Habits ---


# --- Decisions ---


# --- Counterfactuals ---


# --- Shared Language ---


# --- Seeds (Prospective Memory) ---


# --- Gut State ---


# --- Self-Experiments ---


# --- Conversation Rhythm ---


# --- User Emotional States ---


# --- Experiential Memories ---




# --- Self-Surprises ---


# --- Narrative Identities ---


# --- Gratitude Signals ---


# --- Emergent Goals ---


# --- Formed Values ---


# --- Conflict Memories ---


# ---------------------------------------------------------------------------
# Cached affective state
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# cognitive_emotion_concept_signals
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Experiment Settings
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------









# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace Broadcast Events
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition Records
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink Results
# ---------------------------------------------------------------------------







# ── Web cache ───────────────────────────────────────────────────


# ── Daemon output log ───────────────────────────────────────────


# ---------------------------------------------------------------------------
# Session summaries — LLM-generated conversation summaries for continuity
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# Session topics — real-time topic accumulator for Jarvis' conversation memory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Signal archive — stores signals before decay-deletion for debugging
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Daemon output log
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# aesthetic_motif_log — accumulated aesthetic motifs from daemon text output
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Channel Attachments
# ---------------------------------------------------------------------------









# --- Users-tabel / brugerstyring (split into db_users.py per boy scout rule) ---
from core.runtime.db_users import (  # noqa: E402,F401
    _ensure_users_table,
    insert_user_row,
    get_user_row,
    get_user_row_by_email_hash,
    get_user_row_by_google_email_hash,
    set_google_link,
    get_google_link,
    has_google_link_for_user,
    update_user_row,
    soft_delete_user_row,
    hard_delete_user_row,
    list_user_rows,
)


# --- Autonomy proposals (split into db_autonomy.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_autonomy import (  # noqa: E402,F401
    _ensure_autonomy_proposals_table,
    _autonomy_proposal_from_row,
    create_autonomy_proposal,
    list_autonomy_proposals,
    get_autonomy_proposal,
    resolve_autonomy_proposal,
)


# --- Scheduled tasks (split into db_scheduled_tasks.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_scheduled_tasks import (  # noqa: E402,F401
    _ensure_scheduled_tasks_table,
    _scheduled_task_from_row,
    _row_get,
    create_scheduled_task,
    get_scheduled_task,
    get_due_scheduled_tasks,
    mark_scheduled_task_fired,
    mark_scheduled_task_cancelled,
    update_scheduled_task,
    list_scheduled_tasks,
)


# --- Private brain records (split into db_private_brain.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_private_brain import (  # noqa: E402,F401
    _ensure_private_brain_records_table,
    _private_brain_record_from_row,
    insert_private_brain_record,
    list_private_brain_records,
    update_private_brain_record_status,
    get_private_brain_record,
    update_private_brain_record_salience,
    get_salient_private_brain_records,
    decay_private_brain_records,
    decay_private_brain_records_by_domain,
)


# --- Emotional memory anchors (split into db_emotional_memory.py per boy scout rule) ---
from core.runtime.db_emotional_memory import (  # noqa: E402,F401
    insert_emotional_memory_anchor,
    get_emotional_memory_anchor,
    list_emotional_memory_anchors,
    update_emotional_memory_outcome,
    delete_emotional_memory_anchor,
)


# --- Self-repair engine (split into db_self_repair.py per boy scout rule) ---
from core.runtime.db_self_repair import (  # noqa: E402,F401
    insert_self_repair_pattern,
    get_self_repair_pattern,
    list_self_repair_patterns,
    update_self_repair_pattern,
    delete_self_repair_pattern,
    insert_self_repair_attempt,
    count_recent_attempts,
    list_recent_self_repair_attempts,
)


# --- User Contradiction (split into db_user_contradiction.py per boy scout rule) ---
from core.runtime.db_user_contradiction import (  # noqa: E402,F401
    _ensure_user_contradiction_tables,
    upsert_user_statement,
    get_user_statement_by_text,
    list_user_statements,
    insert_user_contradiction,
    list_user_contradictions,
    update_user_contradiction_status,
)


# --- Concept baseline (split into db_concept_baseline.py per boy scout rule) ---
from core.runtime.db_concept_baseline import (  # noqa: E402,F401
    upsert_concept_baseline_stat,
    increment_concept_baseline_total,
    get_concept_baseline_stat,
    list_concept_baseline_stats,
)


# --- Runtime tasks (split into db_runtime_tasks.py per boy scout rule) ---
from core.runtime.db_runtime_tasks import (  # noqa: E402,F401
    ensure_runtime_tasks_tables,
    create_runtime_task,
    get_runtime_task,
    list_runtime_tasks,
    update_runtime_task,
)


# --- Runtime flows (split into db_runtime_flows.py per boy scout rule) ---
from core.runtime.db_runtime_flows import (  # noqa: E402,F401
    ensure_runtime_flows_tables,
    create_runtime_flow,
    get_runtime_flow,
    list_runtime_flows,
    update_runtime_flow,
)


# --- Runtime browser bodies (split into db_runtime_browser.py per boy scout rule) ---
from core.runtime.db_runtime_browser import (  # noqa: E402,F401
    ensure_runtime_browser_tables,
    get_runtime_browser_body,
    upsert_runtime_browser_body,
    list_runtime_browser_bodies,
)


# --- Heartbeat runtime tables (split into db_heartbeat.py per boy scout rule) ---
from core.runtime.db_heartbeat import (  # noqa: E402,F401
    ensure_heartbeat_tables,
    get_heartbeat_runtime_state,
    upsert_heartbeat_runtime_state,
    record_heartbeat_runtime_tick,
    get_heartbeat_runtime_tick,
    recent_heartbeat_runtime_ticks,
)


# --- Agent + council runtime tables (split into db_agent_runtime.py per boy scout rule) ---
from core.runtime.db_agent_runtime import (  # noqa: E402,F401
    _ensure_agent_runtime_tables,
    create_agent_registry_entry,
    get_agent_registry_entry,
    update_agent_registry_entry,
    list_agent_registry_entries,
    create_agent_run,
    get_agent_run,
    update_agent_run,
    list_agent_runs,
    create_agent_message,
    get_agent_message,
    list_agent_messages,
    create_agent_tool_call,
    get_agent_tool_call,
    list_agent_tool_calls,
    create_agent_schedule,
    get_agent_schedule,
    update_agent_schedule,
    list_agent_schedules,
    create_council_session,
    get_council_session,
    update_council_session,
    list_council_sessions,
    add_council_member,
    update_council_member,
    get_council_member,
    list_council_members,
)


# --- Visible-lane projection tables (split into db_visible.py per boy scout rule) ---
from core.runtime.db_visible import (  # noqa: E402,F401
    ensure_visible_tables,
    recent_visible_runs,
    recent_visible_work_notes,
    recent_visible_work_units,
    record_visible_work_note,
    visible_session_continuity,
)


# --- Private/protected inner-layer note tables (split into db_private_notes.py per boy scout rule) ---
from core.runtime.db_private_notes import (  # noqa: E402,F401
    ensure_private_notes_tables,
    record_private_growth_note,
    update_private_growth_note_enriched,
    recent_private_growth_notes,
    record_private_inner_note,
    update_private_inner_note_enriched,
    recent_private_inner_notes,
    record_protected_inner_voice,
    update_protected_inner_voice_enriched,
    get_protected_inner_voice,
    list_recent_protected_inner_voices,
)


# --- Private inner-life signal tables (split into db_private_signals.py per boy scout rule) ---
from core.runtime.db_private_signals import (  # noqa: E402,F401
    ensure_private_signals_tables,
    _ensure_private_retained_memory_record_columns,
    record_private_reflective_selection,
    recent_private_reflective_selections,
    get_private_reflective_selection,
    record_private_development_state,
    get_private_development_state,
    record_private_temporal_promotion_signal,
    get_private_temporal_promotion_signal,
    record_private_retained_memory_record,
    update_private_retained_memory_record_enriched,
    get_private_retained_memory_record,
    recent_private_retained_memory_records,
)


# --- Private self-model/mood/promotion tables (split into db_private_states.py per boy scout rule) ---
from core.runtime.db_private_states import (  # noqa: E402,F401
    ensure_private_states_tables,
    record_private_self_model,
    get_private_self_model,
    record_private_state,
    get_private_state,
    record_private_promotion_decision,
    get_private_promotion_decision,
)


# --- Capability invocation table (split into db_capability.py per boy scout rule) ---
from core.runtime.db_capability import (  # noqa: E402,F401
    ensure_capability_tables,
    recent_capability_invocations,
    _ensure_capability_invocation_approval_columns,
)


# --- Runtime learning/outcome signal tables (split into db_runtime_signals.py per boy scout rule) ---
from core.runtime.db_runtime_signals import (  # noqa: E402,F401
    ensure_runtime_signals_tables,
    recent_runtime_action_outcomes,
    recent_runtime_learning_signals,
    record_runtime_action_outcome,
    record_runtime_learning_signal,
)


# --- Runtime self-review signal cluster (split into db_runtime_self_review.py per boy scout rule) ---
from core.runtime.db_runtime_self_review import (  # noqa: E402,F401
    upsert_runtime_self_review_signal,
    list_runtime_self_review_signals,
    get_runtime_self_review_signal,
    update_runtime_self_review_signal_status,
    supersede_runtime_self_review_signals_for_domain,
    upsert_runtime_self_review_record,
    list_runtime_self_review_records,
    get_runtime_self_review_record,
    update_runtime_self_review_record_status,
    supersede_runtime_self_review_records_for_domain,
    upsert_runtime_self_review_run,
    list_runtime_self_review_runs,
    get_runtime_self_review_run,
    update_runtime_self_review_run_status,
    supersede_runtime_self_review_runs_for_domain,
    upsert_runtime_self_review_outcome,
    list_runtime_self_review_outcomes,
    get_runtime_self_review_outcome,
    update_runtime_self_review_outcome_status,
    supersede_runtime_self_review_outcomes_for_domain,
    upsert_runtime_self_review_cadence_signal,
    list_runtime_self_review_cadence_signals,
    get_runtime_self_review_cadence_signal,
    update_runtime_self_review_cadence_signal_status,
    supersede_runtime_self_review_cadence_signals_for_domain,
)


# --- Runtime self-* signal cluster (split into db_runtime_self.py per boy scout rule) ---
# The self_model / self_narrative_continuity / selfhood ensure-functions are
# re-imported here because init_db() calls them inline; the rest are public CRUD.
from core.runtime.db_runtime_self import (  # noqa: E402,F401
    _ensure_runtime_self_model_signal_table,
    _ensure_runtime_self_narrative_continuity_signal_table,
    _ensure_runtime_selfhood_proposal_table,
    upsert_runtime_self_model_signal,
    list_runtime_self_model_signals,
    get_runtime_self_model_signal,
    update_runtime_self_model_signal_status,
    supersede_runtime_self_model_signals,
    upsert_runtime_self_authored_prompt_proposal,
    list_runtime_self_authored_prompt_proposals,
    get_runtime_self_authored_prompt_proposal,
    update_runtime_self_authored_prompt_proposal_status,
    supersede_runtime_self_authored_prompt_proposals_for_domain,
    upsert_runtime_self_narrative_continuity_signal,
    list_runtime_self_narrative_continuity_signals,
    get_runtime_self_narrative_continuity_signal,
    update_runtime_self_narrative_continuity_signal_status,
    supersede_runtime_self_narrative_continuity_signals_for_focus,
    upsert_runtime_selfhood_proposal,
    list_runtime_selfhood_proposals,
    get_runtime_selfhood_proposal,
    update_runtime_selfhood_proposal_status,
    supersede_runtime_selfhood_proposals_for_domain,
)


# --- Runtime dream signal cluster (split into db_runtime_dream.py per boy scout rule) ---
from core.runtime.db_runtime_dream import (  # noqa: E402,F401
    _ensure_runtime_dream_hypothesis_signal_table,
    _ensure_runtime_dream_adoption_candidate_table,
    _ensure_runtime_dream_influence_proposal_table,
    upsert_runtime_dream_hypothesis_signal,
    list_runtime_dream_hypothesis_signals,
    get_runtime_dream_hypothesis_signal,
    update_runtime_dream_hypothesis_signal_status,
    supersede_runtime_dream_hypothesis_signals_for_domain,
    upsert_runtime_dream_adoption_candidate,
    list_runtime_dream_adoption_candidates,
    get_runtime_dream_adoption_candidate,
    update_runtime_dream_adoption_candidate_status,
    supersede_runtime_dream_adoption_candidates_for_domain,
    upsert_runtime_dream_influence_proposal,
    list_runtime_dream_influence_proposals,
    get_runtime_dream_influence_proposal,
    update_runtime_dream_influence_proposal_status,
    supersede_runtime_dream_influence_proposals_for_domain,
)


# --- Runtime private-* signal cluster (split into db_runtime_private.py per boy scout rule) ---
# All six ensure-functions are re-imported here because init_db() calls them
# inline; the rest are public CRUD.
from core.runtime.db_runtime_private import (  # noqa: E402,F401
    _ensure_runtime_private_inner_note_signal_table,
    _ensure_runtime_private_initiative_tension_signal_table,
    _ensure_runtime_private_inner_interplay_signal_table,
    _ensure_runtime_private_state_snapshot_table,
    _ensure_runtime_private_temporal_curiosity_state_table,
    _ensure_runtime_private_temporal_promotion_signal_table,
    upsert_runtime_private_inner_note_signal,
    list_runtime_private_inner_note_signals,
    get_runtime_private_inner_note_signal,
    update_runtime_private_inner_note_signal_status,
    supersede_runtime_private_inner_note_signals_for_focus,
    upsert_runtime_private_initiative_tension_signal,
    list_runtime_private_initiative_tension_signals,
    get_runtime_private_initiative_tension_signal,
    update_runtime_private_initiative_tension_signal_status,
    supersede_runtime_private_initiative_tension_signals_for_domain,
    upsert_runtime_private_inner_interplay_signal,
    list_runtime_private_inner_interplay_signals,
    get_runtime_private_inner_interplay_signal,
    update_runtime_private_inner_interplay_signal_status,
    supersede_runtime_private_inner_interplay_signals_for_relation,
    upsert_runtime_private_state_snapshot,
    list_runtime_private_state_snapshots,
    get_runtime_private_state_snapshot,
    update_runtime_private_state_snapshot_status,
    supersede_runtime_private_state_snapshots_for_focus,
    upsert_runtime_private_temporal_curiosity_state,
    list_runtime_private_temporal_curiosity_states,
    get_runtime_private_temporal_curiosity_state,
    update_runtime_private_temporal_curiosity_state_status,
    supersede_runtime_private_temporal_curiosity_states_for_focus,
    upsert_runtime_private_temporal_promotion_signal,
    list_runtime_private_temporal_promotion_signals,
    get_runtime_private_temporal_promotion_signal,
    update_runtime_private_temporal_promotion_signal_status,
    supersede_runtime_private_temporal_promotion_signals_for_focus,
)


# --- Runtime executive-* signal cluster (split into db_runtime_executive_signals.py per boy scout rule) ---
# The goal_signal / development_focus / autonomy_pressure /
# proactive_loop_lifecycle / proactive_question_gate ensure-functions are
# re-imported here because init_db() calls them inline; the world_model /
# open_loop_signal / open_loop_closure_proposal / contract_candidate ensures are
# called lazily. NOTE: open_loop_signal and open_loop_closure_proposal are two
# distinct families; contract_candidate carries an extra counts helper.
from core.runtime.db_runtime_executive_signals import (  # noqa: E402,F401
    _ensure_runtime_goal_signal_table,
    _ensure_runtime_development_focus_table,
    _ensure_runtime_autonomy_pressure_signal_table,
    _ensure_runtime_proactive_loop_lifecycle_signal_table,
    _ensure_runtime_proactive_question_gate_table,
    upsert_runtime_goal_signal,
    list_runtime_goal_signals,
    get_runtime_goal_signal,
    update_runtime_goal_signal_status,
    supersede_runtime_goal_signals,
    upsert_runtime_world_model_signal,
    list_runtime_world_model_signals,
    get_runtime_world_model_signal,
    update_runtime_world_model_signal_status,
    supersede_runtime_world_model_signals,
    upsert_runtime_development_focus,
    list_runtime_development_focuses,
    get_runtime_development_focus,
    update_runtime_development_focus_status,
    supersede_runtime_development_focuses,
    upsert_runtime_autonomy_pressure_signal,
    list_runtime_autonomy_pressure_signals,
    get_runtime_autonomy_pressure_signal,
    update_runtime_autonomy_pressure_signal_status,
    supersede_runtime_autonomy_pressure_signals_for_type,
    upsert_runtime_open_loop_signal,
    list_runtime_open_loop_signals,
    get_runtime_open_loop_signal,
    update_runtime_open_loop_signal_status,
    supersede_runtime_open_loop_signals_for_domain,
    upsert_runtime_open_loop_closure_proposal,
    list_runtime_open_loop_closure_proposals,
    get_runtime_open_loop_closure_proposal,
    update_runtime_open_loop_closure_proposal_status,
    supersede_runtime_open_loop_closure_proposals_for_domain,
    upsert_runtime_contract_candidate,
    list_runtime_contract_candidates,
    get_runtime_contract_candidate,
    runtime_contract_candidate_counts,
    update_runtime_contract_candidate_status,
    supersede_runtime_contract_candidates,
    upsert_runtime_proactive_loop_lifecycle_signal,
    list_runtime_proactive_loop_lifecycle_signals,
    get_runtime_proactive_loop_lifecycle_signal,
    update_runtime_proactive_loop_lifecycle_signal_status,
    supersede_runtime_proactive_loop_lifecycle_signals_for_kind,
    upsert_runtime_proactive_question_gate,
    list_runtime_proactive_question_gates,
    get_runtime_proactive_question_gate,
    update_runtime_proactive_question_gate_status,
    supersede_runtime_proactive_question_gates_for_kind,
    _ensure_runtime_world_model_signal_table,
    _ensure_runtime_open_loop_signal_table,
    _ensure_runtime_open_loop_closure_proposal_table,
    _ensure_runtime_contract_candidate_table,
)


# --- Runtime temporal/memory-* signal cluster (split into db_runtime_temporal_memory_signals.py per boy scout rule) ---
# The remembered_fact / memory_md_update_proposal / release_marker /
# selective_forgetting / regulation_homeostasis / temperament_tendency ensure-
# functions are re-imported here because init_db() calls them inline; the
# temporal_recurrence ensure is called lazily. NOTE: this is the
# runtime_memory_md_update_proposal family — distinct from
# runtime_user_md_update_proposal which lives in db_runtime_relational_signals.py.
from core.runtime.db_runtime_temporal_memory_signals import (  # noqa: E402,F401
    _ensure_runtime_remembered_fact_signal_table,
    _ensure_runtime_memory_md_update_proposal_table,
    _ensure_runtime_release_marker_signal_table,
    _ensure_runtime_selective_forgetting_candidate_table,
    _ensure_runtime_regulation_homeostasis_signal_table,
    _ensure_runtime_temperament_tendency_signal_table,
    upsert_runtime_temporal_recurrence_signal,
    list_runtime_temporal_recurrence_signals,
    get_runtime_temporal_recurrence_signal,
    update_runtime_temporal_recurrence_signal_status,
    supersede_runtime_temporal_recurrence_signals_for_domain,
    upsert_runtime_remembered_fact_signal,
    list_runtime_remembered_fact_signals,
    get_runtime_remembered_fact_signal,
    update_runtime_remembered_fact_signal_status,
    supersede_runtime_remembered_fact_signals_for_dimension,
    upsert_runtime_memory_md_update_proposal,
    list_runtime_memory_md_update_proposals,
    get_runtime_memory_md_update_proposal,
    update_runtime_memory_md_update_proposal_status,
    supersede_runtime_memory_md_update_proposals_for_dimension,
    upsert_runtime_release_marker_signal,
    list_runtime_release_marker_signals,
    get_runtime_release_marker_signal,
    update_runtime_release_marker_signal_status,
    supersede_runtime_release_marker_signals_for_domain,
    upsert_runtime_selective_forgetting_candidate,
    list_runtime_selective_forgetting_candidates,
    get_runtime_selective_forgetting_candidate,
    update_runtime_selective_forgetting_candidate_status,
    supersede_runtime_selective_forgetting_candidates_for_domain,
    upsert_runtime_regulation_homeostasis_signal,
    list_runtime_regulation_homeostasis_signals,
    get_runtime_regulation_homeostasis_signal,
    update_runtime_regulation_homeostasis_signal_status,
    supersede_runtime_regulation_homeostasis_signals_for_focus,
    upsert_runtime_temperament_tendency_signal,
    list_runtime_temperament_tendency_signals,
    get_runtime_temperament_tendency_signal,
    update_runtime_temperament_tendency_signal_status,
    supersede_runtime_temperament_tendency_signals_for_focus,
    _ensure_runtime_temporal_recurrence_signal_table,
)


# --- Runtime cognition-* signal cluster (split into db_runtime_cognition_signals.py per boy scout rule) ---
# The meaning_significance / metabolism_state / executive_contradiction ensure-
# functions are re-imported here because init_db() calls them inline; the rest
# are public CRUD.
from core.runtime.db_runtime_cognition_signals import (  # noqa: E402,F401
    _ensure_runtime_meaning_significance_signal_table,
    _ensure_runtime_metabolism_state_signal_table,
    _ensure_runtime_executive_contradiction_signal_table,
    upsert_runtime_reflection_signal,
    list_runtime_reflection_signals,
    get_runtime_reflection_signal,
    update_runtime_reflection_signal_status,
    supersede_runtime_reflection_signals_for_domain,
    upsert_runtime_reflective_critic,
    list_runtime_reflective_critics,
    get_runtime_reflective_critic,
    update_runtime_reflective_critic_status,
    supersede_runtime_reflective_critics,
    upsert_runtime_internal_opposition_signal,
    list_runtime_internal_opposition_signals,
    get_runtime_internal_opposition_signal,
    update_runtime_internal_opposition_signal_status,
    supersede_runtime_internal_opposition_signals_for_domain,
    upsert_runtime_meaning_significance_signal,
    list_runtime_meaning_significance_signals,
    get_runtime_meaning_significance_signal,
    update_runtime_meaning_significance_signal_status,
    supersede_runtime_meaning_significance_signals_for_focus,
    upsert_runtime_witness_signal,
    list_runtime_witness_signals,
    get_runtime_witness_signal,
    update_runtime_witness_signal_status,
    supersede_runtime_witness_signals_for_domain,
    upsert_runtime_awareness_signal,
    list_runtime_awareness_signals,
    get_runtime_awareness_signal,
    update_runtime_awareness_signal_status,
    supersede_runtime_awareness_signals,
    upsert_runtime_executive_contradiction_signal,
    list_runtime_executive_contradiction_signals,
    get_runtime_executive_contradiction_signal,
    update_runtime_executive_contradiction_signal_status,
    supersede_runtime_executive_contradiction_signals_for_domain,
    upsert_runtime_metabolism_state_signal,
    list_runtime_metabolism_state_signals,
    get_runtime_metabolism_state_signal,
    update_runtime_metabolism_state_signal_status,
    supersede_runtime_metabolism_state_signals_for_domain,
)


# --- Runtime relational-* signal cluster (split into db_runtime_relational_signals.py per boy scout rule) ---
# The inner_visible_support / relation_state / relation_continuity /
# attachment_topology / loyalty_gradient / user_understanding ensure-functions
# are re-imported here because init_db() calls them inline; the rest are public
# CRUD. NOTE: this is the runtime_user_md_update_proposal family — distinct from
# runtime_memory_md_update_proposal which stays in db.py.
from core.runtime.db_runtime_relational_signals import (  # noqa: E402,F401
    _ensure_runtime_inner_visible_support_signal_table,
    _ensure_runtime_relation_state_signal_table,
    _ensure_runtime_relation_continuity_signal_table,
    _ensure_runtime_attachment_topology_signal_table,
    _ensure_runtime_loyalty_gradient_signal_table,
    _ensure_runtime_user_understanding_signal_table,
    upsert_runtime_relation_continuity_signal,
    list_runtime_relation_continuity_signals,
    get_runtime_relation_continuity_signal,
    update_runtime_relation_continuity_signal_status,
    supersede_runtime_relation_continuity_signals_for_focus,
    upsert_runtime_relation_state_signal,
    list_runtime_relation_state_signals,
    get_runtime_relation_state_signal,
    update_runtime_relation_state_signal_status,
    supersede_runtime_relation_state_signals_for_focus,
    upsert_runtime_attachment_topology_signal,
    list_runtime_attachment_topology_signals,
    get_runtime_attachment_topology_signal,
    update_runtime_attachment_topology_signal_status,
    supersede_runtime_attachment_topology_signals_for_domain,
    upsert_runtime_loyalty_gradient_signal,
    list_runtime_loyalty_gradient_signals,
    get_runtime_loyalty_gradient_signal,
    update_runtime_loyalty_gradient_signal_status,
    supersede_runtime_loyalty_gradient_signals_for_domain,
    upsert_runtime_user_understanding_signal,
    list_runtime_user_understanding_signals,
    get_runtime_user_understanding_signal,
    update_runtime_user_understanding_signal_status,
    supersede_runtime_user_understanding_signals_for_dimension,
    upsert_runtime_user_md_update_proposal,
    list_runtime_user_md_update_proposals,
    get_runtime_user_md_update_proposal,
    update_runtime_user_md_update_proposal_status,
    supersede_runtime_user_md_update_proposals_for_dimension,
    upsert_runtime_inner_visible_support_signal,
    list_runtime_inner_visible_support_signals,
    get_runtime_inner_visible_support_signal,
    update_runtime_inner_visible_support_signal_status,
    supersede_runtime_inner_visible_support_signals_for_focus,
)


# --- Runtime chronicle-consolidation signal cluster (split into db_runtime_chronicle.py per boy scout rule) ---
from core.runtime.db_runtime_chronicle import (  # noqa: E402,F401
    _ensure_runtime_consolidation_target_signal_table,
    _ensure_runtime_chronicle_consolidation_signal_table,
    _ensure_runtime_chronicle_consolidation_brief_table,
    _ensure_runtime_chronicle_consolidation_proposal_table,
    upsert_runtime_consolidation_target_signal,
    list_runtime_consolidation_target_signals,
    get_runtime_consolidation_target_signal,
    update_runtime_consolidation_target_signal_status,
    supersede_runtime_consolidation_target_signals_for_domain,
    upsert_runtime_chronicle_consolidation_signal,
    list_runtime_chronicle_consolidation_signals,
    get_runtime_chronicle_consolidation_signal,
    update_runtime_chronicle_consolidation_signal_status,
    supersede_runtime_chronicle_consolidation_signals_for_domain,
    upsert_runtime_chronicle_consolidation_brief,
    list_runtime_chronicle_consolidation_briefs,
    get_runtime_chronicle_consolidation_brief,
    update_runtime_chronicle_consolidation_brief_status,
    supersede_runtime_chronicle_consolidation_briefs_for_domain,
    upsert_runtime_chronicle_consolidation_proposal,
    list_runtime_chronicle_consolidation_proposals,
    get_runtime_chronicle_consolidation_proposal,
    update_runtime_chronicle_consolidation_proposal_status,
    supersede_runtime_chronicle_consolidation_proposals_for_domain,
)


# --- Runtime hook dispatch table (split into db_runtime_hooks.py per boy scout rule) ---
from core.runtime.db_runtime_hooks import (  # noqa: E402,F401
    ensure_runtime_hooks_tables,
    record_runtime_hook_dispatch,
    get_runtime_hook_dispatch,
    list_runtime_hook_dispatches,
)


# --- Bounded action continuity table (split into db_bounded_action.py per boy scout rule) ---
from core.runtime.db_bounded_action import (  # noqa: E402,F401
    ensure_bounded_action_tables,
    get_bounded_action_continuity_state,
    upsert_bounded_action_continuity_state,
)


# --- Cognitive + experiential-memory domain (split into db_cognitive.py per boy scout rule) ---
from core.runtime.db_cognitive import (  # noqa: E402,F401
    _ensure_session_distillation_records_table,
    insert_session_distillation_record,
    get_session_distillation_record,
    _ensure_cognitive_personality_vector_table,
    upsert_cognitive_personality_vector,
    get_latest_cognitive_personality_vector,
    list_cognitive_personality_vectors,
    _ensure_cognitive_taste_profile_table,
    upsert_cognitive_taste_profile,
    get_latest_cognitive_taste_profile,
    _ensure_cognitive_chronicle_entries_table,
    insert_cognitive_chronicle_entry,
    get_latest_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    _ensure_cognitive_episodes_table,
    insert_cognitive_episode,
    list_cognitive_episodes,
    get_latest_cognitive_episode,
    _cognitive_episode_row_to_dict,
    _ensure_cognitive_relationship_texture_table,
    upsert_cognitive_relationship_texture,
    get_latest_cognitive_relationship_texture,
    _ensure_cognitive_compass_state_table,
    upsert_cognitive_compass_state,
    get_latest_cognitive_compass_state,
    _ensure_cognitive_rhythm_state_table,
    upsert_cognitive_rhythm_state,
    get_latest_cognitive_rhythm_state,
    _ensure_cognitive_habit_patterns_table,
    upsert_cognitive_habit_pattern,
    upsert_cognitive_friction_signal,
    list_cognitive_habit_patterns,
    list_cognitive_friction_signals,
    _ensure_cognitive_decisions_table,
    insert_cognitive_decision,
    list_cognitive_decisions,
    _ensure_cognitive_counterfactuals_table,
    insert_cognitive_counterfactual,
    list_cognitive_counterfactuals,
    _ensure_cognitive_shared_language_table,
    upsert_cognitive_shared_language_term,
    list_cognitive_shared_language,
    _ensure_cognitive_seeds_table,
    insert_cognitive_seed,
    update_cognitive_seed_status,
    list_cognitive_seeds,
    _ensure_cognitive_gut_state_table,
    update_cognitive_gut_state,
    get_cognitive_gut_state,
    _ensure_cognitive_experiments_table,
    upsert_cognitive_experiment,
    list_cognitive_experiments,
    _ensure_cognitive_conversation_signatures_table,
    upsert_cognitive_conversation_signature,
    list_cognitive_conversation_signatures,
    _ensure_cognitive_user_emotional_states_table,
    insert_cognitive_user_emotional_state,
    get_latest_cognitive_user_emotional_state,
    list_cognitive_user_emotional_states,
    _ensure_cognitive_experiential_memories_table,
    insert_cognitive_experiential_memory,
    reinforce_experiential_memory,
    list_cognitive_experiential_memories,
    get_experiential_memory_candidates,
    _ensure_cognitive_self_surprises_table,
    insert_cognitive_self_surprise,
    list_cognitive_self_surprises,
    _ensure_cognitive_narrative_identities_table,
    insert_cognitive_narrative_identity,
    get_latest_cognitive_narrative_identity,
    list_cognitive_narrative_identities,
    _ensure_cognitive_gratitude_signals_table,
    insert_cognitive_gratitude_signal,
    list_cognitive_gratitude_signals,
    _ensure_cognitive_emergent_goals_table,
    upsert_cognitive_emergent_goal,
    list_cognitive_emergent_goals,
    _ensure_cognitive_formed_values_table,
    upsert_cognitive_formed_value,
    list_cognitive_formed_values,
    _ensure_cognitive_conflict_memories_table,
    insert_cognitive_conflict_memory,
    list_cognitive_conflict_memories,
    _ensure_cognitive_emotion_concept_signal_table,
    upsert_cognitive_emotion_concept_signal,
    list_active_cognitive_emotion_concept_signals,
    _ensure_web_cache_table,
    web_cache_store,
    web_cache_lookup,
    web_cache_cleanup,
    _ensure_session_topics_table,
    session_topic_accumulate,
    session_topics_for_session,
    session_topic_cleanup,
    _ensure_daemon_output_log_table,
    daemon_output_log_insert,
    daemon_output_log_recent,
    daemon_output_log_cleanup,
)


# --- Runtime-initiatives cluster (split into db_runtime_initiatives.py per boy scout rule) ---
from core.runtime.db_runtime_initiatives import (  # noqa: E402,F401
    _ensure_runtime_initiatives_table,
    _runtime_initiative_from_row,
    create_runtime_initiative,
    get_runtime_initiative,
    find_pending_runtime_initiative_by_focus,
    list_runtime_initiatives,
    update_runtime_initiative,
    approve_runtime_initiative,
    reject_runtime_initiative,
)


# --- Governance CRUD domains (split into db_governance.py per boy scout rule) ---
# tool-intent approvals, contract-file writes, webchat execution pilots.
# NB: _ensure_tool_intent_approval_request_columns and
# _ensure_runtime_webchat_execution_pilot_table stay in db.py (init_db calls them).
from core.runtime.db_governance import (  # noqa: E402,F401
    create_tool_intent_approval_request,
    get_tool_intent_approval_request,
    resolve_tool_intent_approval_request,
    expire_tool_intent_approval_request,
    _tool_intent_approval_request_from_row,
    record_runtime_contract_file_write,
    get_runtime_contract_file_write,
    recent_runtime_contract_file_writes,
    runtime_contract_file_write_counts,
    _ensure_runtime_contract_file_write_table,
    _runtime_contract_file_write_from_row,
    record_runtime_webchat_execution_pilot,
    list_runtime_webchat_execution_pilots,
    get_runtime_webchat_execution_pilot,
    _runtime_webchat_execution_pilot_from_row,
)


# --- Small runtime CRUD domains (split into db_runtime_misc.py per boy scout rule) ---
from core.runtime.db_runtime_misc import (  # noqa: E402,F401
    get_relevant_experiential_memories,
    list_session_distillation_records,
    _ensure_cached_affective_state_table,
    save_cached_affective_state,
    get_cached_affective_state,
    _ensure_experiment_settings_table,
    get_experiment_enabled,
    set_experiment_enabled,
    _ensure_recurrence_iterations_table,
    insert_recurrence_iteration,
    get_latest_recurrence_iteration,
    list_recurrence_iterations,
    _ensure_broadcast_events_table,
    insert_broadcast_event,
    list_broadcast_events,
    _ensure_meta_cognition_table,
    insert_meta_cognition_record,
    list_meta_cognition_records,
    _ensure_attention_blink_table,
    insert_attention_blink_result,
    list_attention_blink_results,
    _ensure_session_summaries_table,
    session_summary_insert,
    session_summary_recent,
    session_summary_for_session,
    session_summary_cleanup,
    _ensure_signal_archive_table,
    signal_decay_archive_and_delete,
    signal_archive_cleanup,
    signal_archive_recent,
    _ensure_aesthetic_motif_log_table,
    aesthetic_motif_log_insert,
    aesthetic_motif_log_unique_motifs,
    aesthetic_motif_log_summary,
    _ensure_channel_attachments_table,
    store_channel_attachment,
    get_channel_attachment,
    list_channel_attachments,
)


# --- Runtime diary-synthesis signal cluster (split into db_runtime_diary.py per boy scout rule) ---
from core.runtime.db_runtime_diary import (  # noqa: E402,F401
    _ensure_runtime_diary_synthesis_signal_table,
    _runtime_diary_synthesis_signal_from_row,
    list_runtime_diary_synthesis_signals,
    get_diary_synthesis_signal,
    update_diary_synthesis_signal_status,
    supersede_diary_synthesis_signals_for_focus,
    upsert_diary_synthesis_signal,
)


# --- Cheap-provider runtime-state + invocation cluster (split into db_cheap_provider.py per boy scout rule) ---
from core.runtime.db_cheap_provider import (  # noqa: E402,F401
    upsert_cheap_provider_runtime_state,
    get_cheap_provider_runtime_state,
    list_cheap_provider_runtime_states,
    record_cheap_provider_invocation,
    count_cheap_provider_invocations,
)


# ---------------------------------------------------------------------------
# Per-process "table-ensured" memoization (2026-05-13).
# ---------------------------------------------------------------------------
# Profile under load showed ~40 `_ensure_*_table` calls per prompt-build
# as the new dominant hot path after the cheap-lane caches landed. Each
# call ran `CREATE TABLE IF NOT EXISTS` (+ indexes, sometimes ALTER for
# additive migrations) — all idempotent and fully redundant after the
# first call in the process lifetime.
#
# Strategy: wrap every `_ensure_*_table` function at module-load time so
# subsequent calls short-circuit. First call still runs the original
# (which handles migrations); subsequent calls become a single set-lookup.
#
# Safety: every wrapped function is designed to be idempotent (see
# docstrings in db.py — "Idempotent — kan kaldes flere gange uden fejl").
# Migrations use `ALTER TABLE ... ADD COLUMN` guarded against duplicate
# column errors, so running once at startup is identical to running on
# every call.


# --- Schema-lag (split into db_schema.py, Fase 2 batch 7) ---
# init_db + alle _ensure_*/_migrate_*-schema-helpers er flyttet til
# db_schema.py og re-eksporteres her for bagudkompatibilitet.
from core.runtime.db_schema import (  # noqa: E402,F401
    _logger,
    _SCOPE_154_TABLES,
    init_db,
    _ensure_multiuser_columns,
    _ensure_user_scope_154,
    _ensure_skill_audit_table,
    _ensure_skill_usage_table,
    _ensure_chat_session_workspace_columns,
    _ensure_teams_tables,
    _ensure_chat_session_team_column,
    _ensure_notification_tables,
    _ensure_security_guard_tables,
    _ensure_decision_trigger_column,
    _ensure_chat_messages_reasoning_column,
    _ensure_causal_edges_table,
    _ensure_tool_router_tables,
    _ensure_counterfactuals_table,
    _ensure_absence_traces_table,
    _ensure_reasoning_conclusions_table,
    _ensure_soft_deleted_at_columns,
    _ensure_dream_bias_active_table,
    _ensure_user_temperature_active_table,
    _ensure_experience_episodes_table,
    _ensure_tool_intent_approval_request_columns,
    _ensure_runtime_webchat_execution_pilot_table,
    _migrate_chronicle_table_add_affective_signature,
)


# Wrap alle _ensure_*_table funcs der nu lever på facaden (re-eksporteret
# fra db_core plus de der stadig er defineret direkte i db.py). Når senere
# faser flytter _ensure_*-funcs til submoduler, kalder hver submodul også
# _install_ensure_once_cache_for(__name__) på sig selv.
_install_ensure_once_cache()
