# `core.services.18` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/runtime_self_model_identity.py`
_Runtime self-model — identity awareness (self-insight, narrative identity,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_identity.py#L37) |
| function | `_self_insight_source_snapshot` | `()` | Safely gather bounded insight-bearing seams for self-insight derivation. | [src](../../../core/services/runtime_self_model_identity.py#L88) |
| function | `_derive_self_insight_awareness` | `(*, sources, mineness, flow_state, wonder, longing)` | Derive a bounded self-insight surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_identity.py#L200) |
| function | `_self_insight_narrative` | `(*, insight_state, identity_relation, insight_source)` | Compact self-insight narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L338) |
| function | `build_self_insight_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for self-insight awareness. | [src](../../../core/services/runtime_self_model_identity.py#L375) |
| function | `_derive_narrative_identity_continuity` | `(*, self_insight, sources, mineness, flow_state, wonder, longing)` | Derive a bounded narrative-identity-continuity surface. | [src](../../../core/services/runtime_self_model_identity.py#L476) |
| function | `_narrative_identity_continuity_narrative` | `(*, continuity_state, pattern_relation, identity_source)` | Compact identity-continuity narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L610) |
| function | `build_narrative_identity_continuity_prompt_section` | `()` | Compact heartbeat-side prompt section for narrative identity continuity. | [src](../../../core/services/runtime_self_model_identity.py#L645) |
| function | `_derive_dream_identity_carry_awareness` | `(*, self_insight, identity_continuity, sources, dream_influence, dream_articulation)` | Derive when dream carry begins to shape identity rather than just recur. | [src](../../../core/services/runtime_self_model_identity.py#L760) |
| function | `_dream_identity_carry_narrative` | `(*, carry_state, dream_self_relation, dream_identity_source, influence_target)` | Compact dream identity carry narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L862) |
| function | `build_dream_identity_carry_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for dream carry identity shaping. | [src](../../../core/services/runtime_self_model_identity.py#L893) |
| function | `build_cognitive_core_experiment_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for cognitive-core experiment state. | [src](../../../core/services/runtime_self_model_identity.py#L978) |
| function | `_idle_consolidation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1024) |
| function | `_epistemic_runtime_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1043) |
| function | `_subagent_ecology_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1059) |

## `core/services/runtime_self_model_state.py`
_Runtime self-model — base state surfaces + temporal/mineness awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_state.py#L17) |
| function | `_embodied_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L29) |
| function | `_loop_runtime_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L45) |
| function | `_runtime_task_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L64) |
| function | `_runtime_flow_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L87) |
| function | `_runtime_hook_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L110) |
| function | `_browser_body_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L144) |
| function | `_standing_orders_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L176) |
| function | `_layered_memory_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L197) |
| function | `_affective_meta_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L218) |
| function | `_experiential_runtime_context_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L233) |
| function | `_inner_voice_daemon_surface` | `()` | Read inner voice daemon state for self-model integration. | [src](../../../core/services/runtime_self_model_state.py#L249) |
| function | `_derive_support_stream_awareness` | `(experiential, inner_voice)` | Derive compact self-aware support stream state. | [src](../../../core/services/runtime_self_model_state.py#L265) |
| function | `_runtime_self_appraisal_record` | `(*, kind, state, evidence, confidence, allowed_effects, ttl_minutes)` | Structured source-truth record for runtime self-model renderings. | [src](../../../core/services/runtime_self_model_state.py#L342) |
| function | `_derive_subjective_temporal_feel` | `(experiential, inner_voice)` | Derive a compact subjective temporal feel from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L367) |
| function | `_temporal_narrative` | `(temporal_state, felt_proximity, return_signal, persistence_feel, gap_minutes)` | Compact self-awareness narrative for felt time. | [src](../../../core/services/runtime_self_model_state.py#L468) |
| function | `_mineness_source_snapshot` | `()` | Gather the minimal runtime truth needed for mineness derivation. | [src](../../../core/services/runtime_self_model_state.py#L528) |
| function | `_derive_mineness_ownership` | `(*, experiential, inner_voice, support_stream, temporal_feel, sources)` | Derive a bounded mineness/ownership surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L578) |
| function | `_mineness_narrative` | `(*, ownership_state, carried_thread_state, carried_thread_count, brain_top_focus, brain_continuity, open_loop_signal, voice_mode, support_posture, felt_proximity)` | Compact mineness narrative. Empty in ambient default. | [src](../../../core/services/runtime_self_model_state.py#L680) |
| function | `build_mineness_ownership_prompt_section` | `()` | Compact heartbeat-side prompt section for mineness/ownership. | [src](../../../core/services/runtime_self_model_state.py#L714) |

## `core/services/runtime_self_model_surfaces.py`
_Runtime self-model — small producer/subsystem surfaces + role helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_surfaces.py#L12) |
| function | `_council_runtime_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L24) |
| function | `_agent_outcomes_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L44) |
| function | `_adaptive_planner_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L59) |
| function | `_adaptive_reasoning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L77) |
| function | `_guided_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L95) |
| function | `_dream_influence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L113) |
| function | `_adaptive_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L131) |
| function | `_dream_articulation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L149) |
| function | `_prompt_evolution_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L168) |
| function | `_self_system_code_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L188) |
| function | `_tool_intent_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L208) |
| function | `_heartbeat_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L233) |
| function | `_visible_chat_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L243) |
| function | `_cheap_lane_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L255) |
| function | `_local_lane_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L270) |
| function | `_private_brain_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L285) |
| function | `_approval_pipeline_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L297) |
| function | `_producer_layers` | `()` | Build producer layers from internal cadence state. | [src](../../../core/services/runtime_self_model_surfaces.py#L308) |
| function | `_producer_label` | `(name)` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L367) |
| function | `_groundwork_layers` | `()` | Layers that exist but only as candidates/proposals. | [src](../../../core/services/runtime_self_model_surfaces.py#L380) |
| function | `_cognitive_architecture_awareness` | `()` | Build awareness of the cognitive architecture from shared runtime truth. | [src](../../../core/services/runtime_self_model_surfaces.py#L416) |
| function | `_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L435) |
| function | `_cognitive_core_experiment_carry_snapshot` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L466) |
| function | `build_authenticity_prompt_section` | `()` | Return a prompt line when Jarvis has crystallized tastes or values — suppressed otherwise. | [src](../../../core/services/runtime_self_model_surfaces.py#L478) |
| function | `_authenticity_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L507) |
| function | `_valence_trajectory_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L533) |
| function | `build_valence_trajectory_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L541) |
| function | `_developmental_valence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L549) |
| function | `build_developmental_valence_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L557) |
| function | `_desperation_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L565) |
| function | `build_desperation_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L573) |
| function | `_calm_anchor_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L581) |
| function | `build_calm_anchor_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L589) |
| function | `_memory_breathing_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L597) |
| function | `_creative_projects_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L605) |
| function | `build_creative_projects_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L613) |
| function | `_day_shape_memory_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L621) |
| function | `build_day_shape_memory_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L629) |
| function | `_avoidance_detector_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L637) |
| function | `build_avoidance_detector_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L645) |
| function | `_thought_thread_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L653) |
| function | `build_thought_thread_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L661) |
| function | `_skill_contract_registry_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L669) |
| function | `_memory_write_policy_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L677) |
| function | `build_memory_write_policy_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L685) |
| function | `_spaced_repetition_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L693) |
| function | `build_spaced_repetition_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L701) |
| function | `_scheduled_job_windows_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L709) |
| function | `_automation_dsl_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L717) |
| function | `_outcome_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L725) |
| function | `_jobs_engine_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L733) |
| function | `_prompt_mutation_loop_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L741) |
| function | `build_prompt_mutation_loop_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L749) |
| function | `_file_watch_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L757) |
| function | `build_file_watch_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L765) |
| function | `_reboot_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L773) |
| function | `build_reboot_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L781) |
| function | `_proprioception_metrics_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L789) |
| function | `build_proprioception_metrics_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L797) |
| function | `_anticipatory_action_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L805) |
| function | `build_anticipatory_action_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L813) |
| function | `_cross_session_threads_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L821) |
| function | `build_cross_session_threads_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L829) |
| function | `_autonomous_outreach_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L837) |
| function | `_infra_weather_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L845) |
| function | `build_infra_weather_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L853) |
| function | `_temporal_rhythm_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L861) |
| function | `build_temporal_rhythm_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L869) |
| function | `_relation_dynamics_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L877) |
| function | `build_relation_dynamics_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L885) |
| function | `_creative_instinct_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L893) |
| function | `build_creative_instinct_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L901) |
| function | `_autonomous_work_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L909) |
| function | `build_autonomous_work_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L917) |
| function | `_dream_consolidation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L925) |
| function | `build_dream_consolidation_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L933) |
| function | `_text_resonance_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L941) |
| function | `build_text_resonance_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L949) |
| function | `_creative_impulse_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L957) |
| function | `build_creative_impulse_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L965) |
| function | `_shadow_scan_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L973) |
| function | `build_shadow_scan_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L981) |
| function | `_mortality_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L989) |
| function | `build_mortality_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L997) |
| function | `_relational_warmth_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1005) |
| function | `build_relational_warmth_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1013) |
| function | `_collective_pulse_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1021) |
| function | `build_collective_pulse_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1029) |
| function | `_action_router_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1037) |
| function | `build_action_router_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1045) |
| function | `_sustained_attention_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1053) |
| function | `build_sustained_attention_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1061) |
| function | `_memory_density_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1069) |
| function | `build_memory_density_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1077) |
| function | `_deep_reflection_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1085) |
| function | `build_deep_reflection_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1093) |
| function | `build_physical_presence_prompt_section` | `()` | Return a somatic line when hardware state is non-trivial — suppressed when all quiet. | [src](../../../core/services/runtime_self_model_surfaces.py#L1101) |
| function | `_physical_presence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1147) |

## `core/services/runtime_surface_cache.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `runtime_surface_cache` | `()` | — | [src](../../../core/services/runtime_surface_cache.py#L21) |
| function | `get_cached_runtime_surface` | `(key, builder)` | — | [src](../../../core/services/runtime_surface_cache.py#L35) |
| function | `peek_cached_runtime_surface` | `(key)` | — | [src](../../../core/services/runtime_surface_cache.py#L44) |
| function | `get_timed_runtime_surface` | `(key, ttl_seconds, builder)` | — | [src](../../../core/services/runtime_surface_cache.py#L51) |
| function | `invalidate_timed_runtime_surface` | `(*keys_or_prefixes)` | Drop matchende entries fra den KRYDS-TUR TIMED-cache (2026-06-30). | [src](../../../core/services/runtime_surface_cache.py#L86) |

## `core/services/runtime_tasks.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_task` | `(*, kind, goal, origin, scope=…, priority=…, flow_id=…, session_id=…, run_id=…, owner=…)` | — | [src](../../../core/services/runtime_tasks.py#L16) |
| function | `list_tasks` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/services/runtime_tasks.py#L58) |
| function | `get_task` | `(task_id)` | — | [src](../../../core/services/runtime_tasks.py#L77) |
| function | `update_task` | `(task_id, *, status=…, flow_id=…, session_id=…, run_id=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…)` | — | [src](../../../core/services/runtime_tasks.py#L81) |
| function | `_task_sort_key` | `(task)` | — | [src](../../../core/services/runtime_tasks.py#L117) |
| function | `_priority_with_runtime_bias` | `(requested_priority, *, kind, goal, scope, origin)` | — | [src](../../../core/services/runtime_tasks.py#L127) |

## `core/services/rupture_repair.py`
_Rupture & Repair — relationel tension-tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/rupture_repair.py#L86) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/rupture_repair.py#L90) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/rupture_repair.py#L103) |
| function | `_rupture_key` | `(*, source_kind, topic)` | — | [src](../../../core/services/rupture_repair.py#L154) |
| function | `_normalize_topic` | `(payload, *, event_kind)` | — | [src](../../../core/services/rupture_repair.py#L159) |
| function | `_classify_rupture` | `(event_kind, payload)` | Returns (is_rupture, source_kind, tension_level ∈ [0,1]). | [src](../../../core/services/rupture_repair.py#L170) |
| function | `_is_repair_attempt` | `(event_kind, payload)` | — | [src](../../../core/services/rupture_repair.py#L202) |
| function | `_is_repair_complete` | `(event_kind, payload)` | — | [src](../../../core/services/rupture_repair.py#L212) |
| function | `_row_to_rupture` | `(row)` | — | [src](../../../core/services/rupture_repair.py#L232) |
| function | `_row_to_repair` | `(row)` | — | [src](../../../core/services/rupture_repair.py#L243) |
| function | `_upsert_rupture` | `(conn, *, rupture_key, topic, source_kind, reason, evidence, tension_level, linked_run_id, linked_session_id, linked_incident_id, status, last_seen_at)` | Insert or update a rupture by rupture_key. Returns (row_dict, mutation). | [src](../../../core/services/rupture_repair.py#L254) |
| function | `_create_repair` | `(conn, *, rupture_id, repair_kind, repair_note, change_summary, evidence, status, linked_run_id, linked_session_id)` | — | [src](../../../core/services/rupture_repair.py#L338) |
| function | `evaluate_ruptures` | `(*, lookback_hours=…, event_limit=…)` | Scan recent events and detect/update ruptures and repairs. | [src](../../../core/services/rupture_repair.py#L372) |
| function | `list_ruptures` | `(*, status=…, limit=…)` | — | [src](../../../core/services/rupture_repair.py#L517) |
| function | `list_repairs` | `(*, rupture_id=…, status=…, limit=…)` | — | [src](../../../core/services/rupture_repair.py#L540) |
| function | `summarize_ruptures` | `()` | — | [src](../../../core/services/rupture_repair.py#L570) |
| function | `build_rupture_repair_surface` | `()` | MC surface for Rupture & Repair. | [src](../../../core/services/rupture_repair.py#L607) |

## `core/services/scheduled_job_windows.py`
_Scheduled Job Windows — time-window batch scheduling with provider preferences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/scheduled_job_windows.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/scheduled_job_windows.py#L37) |
| function | `_save` | `(data)` | — | [src](../../../core/services/scheduled_job_windows.py#L53) |
| function | `register_window` | `(*, name, start_hour, end_hour, max_requests=…, allowed_providers=…, prefer_free_first=…, active=…)` | Register a scheduled window. Hours in local time. | [src](../../../core/services/scheduled_job_windows.py#L65) |
| function | `set_window_active` | `(window_id, active)` | — | [src](../../../core/services/scheduled_job_windows.py#L103) |
| function | `is_inside_window` | `(now, start_hour, end_hour)` | Supports wraparound (end_hour <= start_hour means crosses midnight). | [src](../../../core/services/scheduled_job_windows.py#L113) |
| function | `current_window_day_key` | `(now, start_hour)` | Generate a unique key for (window, day) — e.g., '2026-04-20-22'. | [src](../../../core/services/scheduled_job_windows.py#L124) |
| function | `_already_fired` | `(history, window_id, day_key)` | — | [src](../../../core/services/scheduled_job_windows.py#L141) |
| function | `tick_windows` | `(*, now=…, callback=…)` | Evaluate all windows. For each window currently inside and not-yet-fired | [src](../../../core/services/scheduled_job_windows.py#L148) |
| function | `list_windows` | `()` | — | [src](../../../core/services/scheduled_job_windows.py#L194) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — evaluates windows, no-op when not inside any. | [src](../../../core/services/scheduled_job_windows.py#L198) |
| function | `build_scheduled_job_windows_surface` | `()` | — | [src](../../../core/services/scheduled_job_windows.py#L204) |
| function | `_surface_summary` | `(windows, active_now, history)` | — | [src](../../../core/services/scheduled_job_windows.py#L228) |

## `core/services/scheduled_task_runner.py`
_Scheduled task dispatcher — binds workspace_context before firing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `fire_scheduled_task` | `(task, *, runner)` | Bind workspace_context to task's scheduled_for_user_id and run. | [src](../../../core/services/scheduled_task_runner.py#L20) |

## `core/services/scheduled_tasks.py`
_Scheduled tasks service — lets Jarvis schedule future reminders/actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `push_scheduled_task` | `(*, focus, delay_minutes, source=…)` | Schedule a task to fire after delay_minutes. Returns task info dict. | [src](../../../core/services/scheduled_tasks.py#L24) |
| function | `cancel_scheduled_task` | `(task_id)` | Cancel a pending task. Returns True if found and cancelled. | [src](../../../core/services/scheduled_tasks.py#L53) |
| function | `edit_scheduled_task` | `(task_id, *, focus=…, delay_minutes=…)` | Edit an existing pending task. Returns updated task info or error dict. | [src](../../../core/services/scheduled_tasks.py#L64) |
| function | `list_pending_for_current_user` | `()` | Return scheduled tasks where scheduled_for_user_id matches current user. | [src](../../../core/services/scheduled_tasks.py#L90) |
| function | `get_scheduled_tasks_state` | `()` | Return all scheduled tasks for observability. | [src](../../../core/services/scheduled_tasks.py#L120) |
| function | `_fire_due_tasks` | `()` | — | [src](../../../core/services/scheduled_tasks.py#L137) |
| function | `_poller_loop` | `()` | — | [src](../../../core/services/scheduled_tasks.py#L299) |
| function | `start_scheduled_tasks_service` | `()` | — | [src](../../../core/services/scheduled_tasks.py#L318) |
| function | `stop_scheduled_tasks_service` | `()` | — | [src](../../../core/services/scheduled_tasks.py#L327) |
| function | `build_scheduled_tasks_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/scheduled_tasks.py#L332) |

## `core/services/security_guard.py`
_Identity-verification-guard & abuse-monitoring — kerne (spec 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/security_guard.py#L30) |
| function | `_iso` | `(dt=…)` | — | [src](../../../core/services/security_guard.py#L34) |
| function | `is_owner` | `(user_id)` | True hvis user_id er ejeren (Bjørn). Owner kan få session-lock men | [src](../../../core/services/security_guard.py#L39) |
| function | `record_audit` | `(user_id, action, *, session_id=…, details=…, device_info=…)` | Append-only. Aktioner: override_activated, sudo_executed, session_locked, | [src](../../../core/services/security_guard.py#L54) |
| function | `record_abuse` | `(user_id, session_id, event_type, severity, *, details=…)` | severity ∈ {low, medium, high}. Kun high eskalerer til lock (§11.4). | [src](../../../core/services/security_guard.py#L73) |
| function | `lock_session` | `(session_id, reason, *, user_id=…)` | — | [src](../../../core/services/security_guard.py#L93) |
| function | `unlock_session` | `(session_id, *, user_id=…)` | — | [src](../../../core/services/security_guard.py#L108) |
| function | `is_session_locked` | `(session_id)` | — | [src](../../../core/services/security_guard.py#L123) |
| function | `is_account_locked` | `(user_id)` | True hvis brugeren har en AKTIV (ikke-udløbet) 'locked'-flag. | [src](../../../core/services/security_guard.py#L138) |
| function | `_lock_account` | `(user_id, *, hours=…)` | Lås ALLE brugerens sessioner + sæt 'locked'-flag (udløber om `hours`). | [src](../../../core/services/security_guard.py#L156) |
| function | `_recent_session_lock_count` | `(user_id, *, hours=…)` | Antal session-lock-audit-entries for user_id i de sidste `hours`. | [src](../../../core/services/security_guard.py#L180) |
| function | `escalate_session_lock` | `(user_id, session_id, reason)` | Lås sessionen, og afgør om det også udløser account-lockdown. | [src](../../../core/services/security_guard.py#L198) |

## `core/services/seed_system.py`
_Seed System — prospective memory / dormant intentions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `plant_seed` | `(*, title, summary=…, activate_at=…, activate_on_event=…, activate_on_context=…, relevance_score=…, linked_goal=…)` | Plant a dormant intention seed. | [src](../../../core/services/seed_system.py#L26) |
| function | `check_seed_activation` | `(*, current_context=…, current_event=…)` | Check if any planted seeds should activate. | [src](../../../core/services/seed_system.py#L56) |
| function | `fulfill_seed` | `(seed_id)` | Mark a seed as fulfilled. | [src](../../../core/services/seed_system.py#L103) |
| function | `build_seed_surface` | `()` | — | [src](../../../core/services/seed_system.py#L109) |
| function | `auto_plant_seeds_from_conversation` | `(*, user_message)` | Scan user message for future-intent markers and auto-plant seeds. | [src](../../../core/services/seed_system.py#L123) |
| function | `_safe_json_list` | `(value)` | — | [src](../../../core/services/seed_system.py#L160) |

## `core/services/selective_attention.py`
_Selective Attention — metacognitive focus modulation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FocusDirective` | `` | A single attention directive — what to amplify or attenuate. | [src](../../../core/services/selective_attention.py#L48) |
| class | `AttentionSpotlight` | `` | Current attention spotlight — a set of focus directives. | [src](../../../core/services/selective_attention.py#L57) |
| function | `compute_selective_attention` | `()` | Compute current attention spotlight. | [src](../../../core/services/selective_attention.py#L124) |
| function | `get_attention_spotlight_line` | `()` | Convenience: compute spotlight and return prompt-ready string. | [src](../../../core/services/selective_attention.py#L237) |
| function | `get_attention_spotlight_detail` | `()` | Return full spotlight state for MC transparency. | [src](../../../core/services/selective_attention.py#L249) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/selective_attention.py#L274) |
| function | `_detect_context_cue` | `(family_pressures, dominant_pressures)` | Heuristic: detect the operational context from signal patterns. | [src](../../../core/services/selective_attention.py#L285) |
| function | `_generate_directives` | `(base_pressures, attention_weights)` | Generate focus directives by comparing base vs adjusted weights. | [src](../../../core/services/selective_attention.py#L319) |
| function | `_compute_focus_width` | `(attention_weights, directive_count)` | Compute how narrow or broad the attention spotlight is. | [src](../../../core/services/selective_attention.py#L380) |
| function | `build_selective_attention_surface` | `()` | Returns current attention spotlight if any. | [src](../../../core/services/selective_attention.py#L414) |
| function | `_emit_spotlight_event` | `(label)` | — | [src](../../../core/services/selective_attention.py#L430) |

## `core/services/selective_consolidation_daemon.py`
_Selective Consolidation Daemon — D1._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_selective_consolidation_daemon` | `()` | Run selective consolidation if cadence elapsed. | [src](../../../core/services/selective_consolidation_daemon.py#L42) |
| function | `_score_sensory` | `(row)` | Score a sensory memory 0.0-1.0. | [src](../../../core/services/selective_consolidation_daemon.py#L109) |
| function | `_consolidate_sensory` | `(today_start)` | Score and archive bottom (100-K)% of today's sensory memories. | [src](../../../core/services/selective_consolidation_daemon.py#L121) |
| function | `_score_brain` | `(entry)` | Score a brain entry 0.0-1.0. | [src](../../../core/services/selective_consolidation_daemon.py#L170) |
| function | `_consolidate_brain` | `(today_start)` | Score and archive bottom (100-K)% of today's brain entries. | [src](../../../core/services/selective_consolidation_daemon.py#L181) |
| function | `_score_private` | `(record)` | Score a private brain record 0.0-1.0. | [src](../../../core/services/selective_consolidation_daemon.py#L241) |
| function | `_consolidate_private` | `(today_start)` | Score and archive bottom (100-K)% of today's private brain records. | [src](../../../core/services/selective_consolidation_daemon.py#L252) |
| function | `build_selective_consolidation_surface` | `()` | Build surface data for mission control. | [src](../../../core/services/selective_consolidation_daemon.py#L306) |

## `core/services/selective_forgetting_candidate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_selective_forgetting_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L27) |
| function | `refresh_runtime_selective_forgetting_candidate_statuses` | `()` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L50) |
| function | `build_runtime_selective_forgetting_candidate_surface` | `(*, limit=…)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L81) |
| function | `_extract_selective_forgetting_candidates` | `(*, run_id)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L119) |
| function | `_build_candidate` | `(*, domain_key, metabolism, release_marker, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L231) |
| function | `_persist_selective_forgetting_candidates` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L348) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L417) |
| function | `_derive_candidate_state` | `(*, release_state, witness_status, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L444) |
| function | `_derive_candidate_reason` | `(*, release_state, witness_status, stale_count)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L459) |
| function | `_derive_candidate_weight` | `(*, fading_count, softening_count, stale_count, release_state)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L474) |
| function | `_candidate_summary` | `(*, focus, candidate_state, candidate_reason, candidate_weight)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L489) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L509) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L516) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L523) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L535) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L546) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/selective_forgetting_candidate_tracking.py#L560) |

## `core/services/self_authored_prompt_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_authored_prompt_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L29) |
| function | `refresh_runtime_self_authored_prompt_proposal_statuses` | `()` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L51) |
| function | `build_runtime_self_authored_prompt_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L82) |
| function | `_extract_self_authored_prompt_proposals` | `()` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L111) |
| function | `_persist_self_authored_prompt_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L188) |
| function | `_build_prompt_snapshots` | `()` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L262) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L303) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L316) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L332) |
| function | `_prompt_target_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L351) |
| function | `_build_proposed_nudge` | `(*, proposal_type)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L361) |
| function | `_build_prompt_status` | `(*, influence_status, proposal_type)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L371) |
| function | `_build_proposal_confidence` | `(*, proposal_type, influence_confidence)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L379) |
| function | `_build_proposal_reason` | `(*, proposal_type, proposal_confidence)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L387) |
| function | `_build_influence_anchor` | `(*, item, snapshot)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L397) |
| function | `_build_status_reason` | `(*, proposal_type)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L411) |
| function | `_hypothesis_type_from_snapshot` | `(*, snapshot)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L421) |
| function | `_influence_target_from_summary` | `(summary)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L425) |
| function | `_proposal_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L436) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L445) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L450) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L455) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L460) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L465) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L470) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L479) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_authored_prompt_proposal_tracking.py#L489) |

## `core/services/self_compassion.py`
_Self-Compassion & Resilience — counterweight to regret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compassion_label` | `(failure_count, regret_level, compassion_level)` | Return a descriptive state label, not a self-compassion sentence. | [src](../../../core/services/self_compassion.py#L12) |
| function | `process_failure_toward_acceptance` | `(*, failure_count_recent=…, regret_level=…, lesson_learned=…)` | — | [src](../../../core/services/self_compassion.py#L32) |
| function | `build_resilience_narrative` | `(*, consecutive_failures=…, current_bearing=…)` | Return a descriptive resilience-state label. | [src](../../../core/services/self_compassion.py#L56) |
| function | `build_self_compassion_surface` | `()` | — | [src](../../../core/services/self_compassion.py#L76) |

## `core/services/self_critique_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_self_critique_interval_days` | `()` | Read base interval, modulate by dream-bias self_critique_volume. | [src](../../../core/services/self_critique_runtime.py#L34) |
| function | `read_self_docs` | `(*, doc_id=…, include_history=…, max_chars_per_doc=…)` | — | [src](../../../core/services/self_critique_runtime.py#L68) |
| function | `run_self_critique_cycle` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/self_critique_runtime.py#L115) |
| function | `run_ontological_revision_check` | `()` | Check if a 90-day revision is due. If yes, append 'Er du stadig enig?' response. | [src](../../../core/services/self_critique_runtime.py#L229) |
| function | `build_self_critique_surface` | `()` | — | [src](../../../core/services/self_critique_runtime.py#L321) |
| function | `self_critique_path` | `()` | — | [src](../../../core/services/self_critique_runtime.py#L347) |
| function | `_self_doc_manifest` | `()` | — | [src](../../../core/services/self_critique_runtime.py#L352) |
| function | `_render_manifest` | `(manifest)` | — | [src](../../../core/services/self_critique_runtime.py#L370) |
| function | `_render_doc` | `(item, *, max_chars)` | — | [src](../../../core/services/self_critique_runtime.py#L377) |
| function | `_render_recent_chronicles` | `(entries)` | — | [src](../../../core/services/self_critique_runtime.py#L387) |
| function | `_render_recent_chronicles_extended` | `(entries)` | Extended rendering for blind-angle prompt — more entries, includes lessons too. | [src](../../../core/services/self_critique_runtime.py#L399) |
| function | `_append_self_critique_entry` | `(*, entry_id, created_at, next_review_at, prompt, critique, source_docs, cycle_type=…)` | — | [src](../../../core/services/self_critique_runtime.py#L416) |
| function | `_latest_entry_preview` | `(text)` | — | [src](../../../core/services/self_critique_runtime.py#L449) |
| function | `_self_critique_enabled` | `()` | — | [src](../../../core/services/self_critique_runtime.py#L456) |
| function | `_state` | `()` | — | [src](../../../core/services/self_critique_runtime.py#L461) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/self_critique_runtime.py#L466) |
| function | `_extract_key_words` | `(text)` | Extract meaningful Danish/English words (5+ chars) from text. | [src](../../../core/services/self_critique_runtime.py#L494) |
| function | `_check_absence_links` | `(*, entry_id, critique_text, now)` | After a blind-angle critique, look for convergence with recent absence signals. | [src](../../../core/services/self_critique_runtime.py#L501) |
| function | `get_absence_trace_links` | `()` | Return stored absence × blind-angle convergence records. | [src](../../../core/services/self_critique_runtime.py#L576) |

## `core/services/self_deception_guard.py`
_Bounded self-deception guard — deterministic truth-constraint on user-facing stance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GuardConstraint` | `` | A single guard constraint to be injected into user-facing contract. | [src](../../../core/services/self_deception_guard.py#L34) |
| class | `DeceptionGuardTrace` | `` | Observable trace of self-deception guard evaluation. | [src](../../../core/services/self_deception_guard.py#L43) |
| method | `DeceptionGuardTrace.has_blocks` | `(self)` | — | [src](../../../core/services/self_deception_guard.py#L54) |
| method | `DeceptionGuardTrace.has_reframes` | `(self)` | — | [src](../../../core/services/self_deception_guard.py#L60) |
| method | `DeceptionGuardTrace.guard_lines` | `(self)` | Return prompt-injectable guard constraint lines. | [src](../../../core/services/self_deception_guard.py#L65) |
| method | `DeceptionGuardTrace.to_dict` | `(self)` | — | [src](../../../core/services/self_deception_guard.py#L69) |
| function | `evaluate_self_deception_guard` | `(*, question_gate=…, autonomy_pressure=…, capability_truth=…, conflict_trace=…, quiet_initiative=…, open_loops=…)` | Evaluate self-deception guard against current runtime truth. | [src](../../../core/services/self_deception_guard.py#L95) |
| function | `get_last_guard_trace` | `()` | Return the last self-deception guard trace for MC observability. | [src](../../../core/services/self_deception_guard.py#L268) |
| function | `set_last_guard_trace` | `(trace)` | Store the latest guard trace for MC observability. | [src](../../../core/services/self_deception_guard.py#L275) |
| function | `build_self_deception_guard_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/self_deception_guard.py#L281) |

## `core/services/self_experiments.py`
_Self-Experiments — A/B testing on Jarvis' own behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_default_experiments` | `()` | Create default experiments if none exist. | [src](../../../core/services/self_experiments.py#L38) |
| function | `record_experiment_observation` | `(*, experiment_id, cohort, success, observed_run_id=…, observation_note=…)` | Record an observation for an experiment. | [src](../../../core/services/self_experiments.py#L57) |
| function | `_evaluate_experiment` | `(cohorts)` | Simple evaluation: compare success rates between cohorts. | [src](../../../core/services/self_experiments.py#L140) |
| function | `generate_learning_curriculum` | `()` | 3.8 Curriculum learning — analyze weaknesses, generate learning plan. | [src](../../../core/services/self_experiments.py#L169) |
| function | `observe_recent_visible_runs_for_self_experiments` | `(*, limit=…)` | Auto-observe recent visible runs for active self-experiments. | [src](../../../core/services/self_experiments.py#L242) |
| function | `materialize_learning_curriculum_tasks` | `(*, limit=…, origin=…, owner=…, run_id=…)` | Turn top curriculum focuses into bounded runtime tasks. | [src](../../../core/services/self_experiments.py#L320) |
| function | `build_self_experiments_surface` | `()` | — | [src](../../../core/services/self_experiments.py#L411) |
| function | `_parse_result_payload` | `(raw)` | — | [src](../../../core/services/self_experiments.py#L428) |
| function | `_cohort_for_visible_run` | `(*, experiment, run)` | — | [src](../../../core/services/self_experiments.py#L436) |
| function | `_success_for_visible_run` | `(*, experiment, run)` | — | [src](../../../core/services/self_experiments.py#L451) |
| function | `_build_visible_run_observation_note` | `(*, experiment, run, cohort, success)` | — | [src](../../../core/services/self_experiments.py#L462) |
| function | `_curriculum_focus_key` | `(value)` | — | [src](../../../core/services/self_experiments.py#L479) |
| function | `_curriculum_priority` | `(priority)` | — | [src](../../../core/services/self_experiments.py#L483) |

## `core/services/self_model_blind_spots.py`
_Self-Model Blind Spots — LLM-drevet opdagelse af egne usete fejlmønstre._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/self_model_blind_spots.py#L32) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/self_model_blind_spots.py#L36) |
| function | `_load_known_patterns` | `()` | Pull already-identified blind spots + known weaknesses. | [src](../../../core/services/self_model_blind_spots.py#L60) |
| function | `_load_recent_failed_runs` | `(limit=…)` | Pull recent failed visible runs with summary + run_id. | [src](../../../core/services/self_model_blind_spots.py#L76) |
| function | `_build_discovery_prompt` | `(*, known_patterns, failed_runs)` | — | [src](../../../core/services/self_model_blind_spots.py#L97) |
| function | `_extract_blind_spots` | `(raw_text)` | Parse LLM response. Tolerates preamble/fences — finds first {...} block. | [src](../../../core/services/self_model_blind_spots.py#L127) |
| function | `discover_blind_spots` | `()` | Run discovery: analyze recent failed runs for unseen patterns. | [src](../../../core/services/self_model_blind_spots.py#L160) |
| function | `acknowledge_blind_spot` | `(*, blind_spot_id)` | Mark a blind spot as acknowledged (Jarvis has now integrated it). | [src](../../../core/services/self_model_blind_spots.py#L253) |
| function | `list_blind_spots` | `(*, status=…, limit=…)` | — | [src](../../../core/services/self_model_blind_spots.py#L284) |
| function | `build_blind_spots_surface` | `()` | MC surface for self-model blind spots. | [src](../../../core/services/self_model_blind_spots.py#L303) |

## `core/services/self_model_distiller.py`
_Rig selv-model-distiller (#4, b + 2 guards) — genopliver validerings-ROLLEN._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_model` | `()` | — | [src](../../../core/services/self_model_distiller.py#L30) |
| function | `_richness` | `(model)` | Groft richness-mål: hvor meningsfuld/specifik er identiteten. Højere = rigere. | [src](../../../core/services/self_model_distiller.py#L38) |
| function | `_is_meaningful` | `(model)` | En model er meningsfuld hvis dens identity_focus er en ægte (ikke-generisk) frase. | [src](../../../core/services/self_model_distiller.py#L57) |
| function | `_fields_specificity` | `(fields)` | — | [src](../../../core/services/self_model_distiller.py#L66) |
| function | `_gather_inputs` | `()` | Saml Jarvis' egen nylige selv-historie + nuværende model som distillations-grundlag. | [src](../../../core/services/self_model_distiller.py#L77) |
| function | `_build_prompt` | `(inputs)` | — | [src](../../../core/services/self_model_distiller.py#L98) |
| function | `_parse` | `(raw)` | Parse det labelede LLM-svar defensivt. Manglende linjer → udeladt (kalder falder tilbage). | [src](../../../core/services/self_model_distiller.py#L111) |
| function | `distill_self_model` | `(*, trigger=…)` | Distillér en rig selv-model + anti-flatten-guard + skriv (kun hvis ikke tyndere). Self-safe. | [src](../../../core/services/self_model_distiller.py#L126) |
| function | `run_self_model_distill_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-indgang (GUARD 2: langsom rytme). Self-safe. | [src](../../../core/services/self_model_distiller.py#L173) |
| function | `register_self_model_distiller_producer` | `()` | Registrér distilleren som DAGLIG cadence-producer (GUARD 2). Identitet er stabil. | [src](../../../core/services/self_model_distiller.py#L178) |

## `core/services/self_model_predictive.py`
_Predictive self-model — frequencies, not aspirations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tick_quality_stats` | `(days=…)` | — | [src](../../../core/services/self_model_predictive.py#L32) |
| function | `_mood_baseline` | `(days=…)` | — | [src](../../../core/services/self_model_predictive.py#L48) |
| function | `_decision_adherence` | `()` | — | [src](../../../core/services/self_model_predictive.py#L56) |
| function | `_crisis_frequency` | `(days=…)` | — | [src](../../../core/services/self_model_predictive.py#L64) |
| function | `_productive_idle_ratio` | `(days=…)` | Fraction of ticks that ran productive idle vs all ticks. | [src](../../../core/services/self_model_predictive.py#L84) |
| function | `build_predictive_self_model` | `(days=…)` | Compute the empirical self-model. Cheap; fresh each call. | [src](../../../core/services/self_model_predictive.py#L111) |
| function | `_maybe_record_from_model` | `(model)` | Uddrag en verificerbar prediktion fra modellen og persistér den. | [src](../../../core/services/self_model_predictive.py#L136) |
| function | `predictive_self_model_section` | `()` | Render predictive self-model as a prompt awareness section. | [src](../../../core/services/self_model_predictive.py#L179) |
| function | `_load_predictions` | `()` | Læs udestående/scorede prediktions-records. Aldrig kast. | [src](../../../core/services/self_model_predictive.py#L253) |
| function | `_save_predictions` | `(preds)` | Persistér prediktions-records (kompakt, capped). Aldrig kast. | [src](../../../core/services/self_model_predictive.py#L263) |
| function | `_observe_actual` | `(metric)` | Hent den FAKTISKE observerede værdi for en metric — samme kilde som | [src](../../../core/services/self_model_predictive.py#L272) |
| function | `_absorb` | `(cluster, nerve, value, **kwargs)` | Indirektion over central_absorb.absorb — patchbar i test, self-safe. | [src](../../../core/services/self_model_predictive.py#L286) |
| function | `record_prediction` | `(metric, threshold, predicted_above, probability, made_at=…)` | Persistér en kompakt prediktions-record. Skalar, self-safe, aldrig kast. | [src](../../../core/services/self_model_predictive.py#L295) |
| function | `_age_hours` | `(made_at)` | — | [src](../../../core/services/self_model_predictive.py#L329) |
| function | `score_predictions` | `(min_age_hours=…)` | Scor modne, uscorede prediktioner mod virkeligheden. Aldrig kast. | [src](../../../core/services/self_model_predictive.py#L339) |
| function | `build_self_model_predictive_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/self_model_predictive.py#L400) |

## `core/services/self_model_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L26) |
| function | `refresh_runtime_self_model_signal_statuses` | `()` | — | [src](../../../core/services/self_model_signal_tracking.py#L66) |
| function | `build_self_model_signal_prompt_section` | `(*, limit=…)` | Compact prompt-line of active self-model signals. | [src](../../../core/services/self_model_signal_tracking.py#L95) |
| function | `_is_machine_id_title` | `(title)` | En self-model-titel der er et log/event-navn (snake_case maskin-id som | [src](../../../core/services/self_model_signal_tracking.py#L145) |
| function | `build_runtime_self_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_model_signal_tracking.py#L153) |
| function | `_extract_self_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/self_model_signal_tracking.py#L181) |
| function | `_current_limitation_signal` | `(message, *, session_id)` | — | [src](../../../core/services/self_model_signal_tracking.py#L208) |
| function | `_improving_edge_signal` | `(message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L238) |
| function | `_persist_self_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/self_model_signal_tracking.py#L266) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L333) |
| function | `_supersede_replaced_self_model_signals` | `(persisted_item, *, updated_at)` | — | [src](../../../core/services/self_model_signal_tracking.py#L371) |
| function | `_has_matching_self_model_history` | `(limitation_key)` | — | [src](../../../core/services/self_model_signal_tracking.py#L417) |
| function | `_matching_active_critic` | `(message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L429) |
| function | `_supporting_sessions_for_limitation` | `(limitation_key)` | — | [src](../../../core/services/self_model_signal_tracking.py#L444) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/self_model_signal_tracking.py#L454) |
| function | `_critic_limitation_key` | `(canonical_key)` | — | [src](../../../core/services/self_model_signal_tracking.py#L475) |
| function | `_message_limitation_key` | `(message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L486) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_model_signal_tracking.py#L495) |
| function | `_limitation_label` | `(limitation_key)` | — | [src](../../../core/services/self_model_signal_tracking.py#L504) |
| function | `_message_matches_limited_domain` | `(limitation_key, message)` | — | [src](../../../core/services/self_model_signal_tracking.py#L513) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/self_model_signal_tracking.py#L524) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/self_model_signal_tracking.py#L531) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/self_model_signal_tracking.py#L535) |

## `core/services/self_monitor.py`
_Self-monitor — anti-loop detection from tool call history._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_tool_events` | `(limit=…)` | — | [src](../../../core/services/self_monitor.py#L37) |
| function | `_looped_tools` | `(events)` | Find tools that errored repeatedly in succession. | [src](../../../core/services/self_monitor.py#L56) |
| function | `_thrashing_score` | `(events)` | Crude thrash signal: count of tool.invoked in the recent window. | [src](../../../core/services/self_monitor.py#L88) |
| function | `self_monitor_section` | `()` | Format anti-loop / thrash signals as a prompt section, or None. | [src](../../../core/services/self_monitor.py#L93) |

## `core/services/self_mutation_lineage.py`
_Runtime self-awareness of self-change and code mutation lineage._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/self_mutation_lineage.py#L33) |
| function | `_categorize_path` | `(path)` | Return category if path is a Jarvis self-file, else None. | [src](../../../core/services/self_mutation_lineage.py#L60) |
| function | `_relative_path` | `(path)` | — | [src](../../../core/services/self_mutation_lineage.py#L74) |
| function | `record_self_mutation` | `(*, target_path, change_type, session_id=…)` | Record a completed file mutation to a Jarvis self-file. | [src](../../../core/services/self_mutation_lineage.py#L81) |
| function | `build_self_mutation_lineage_surface` | `(*, limit=…)` | Returns recent self-mutations as a runtime-truth surface. | [src](../../../core/services/self_mutation_lineage.py#L112) |
| function | `build_self_mutation_prompt_lines` | `(*, limit=…)` | Returns compact prompt lines for recent self-mutations. | [src](../../../core/services/self_mutation_lineage.py#L157) |
| function | `_emit_self_mutation_lineage_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/self_mutation_lineage.py#L170) |

## `core/services/self_narrative_continuity_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_narrative_continuity_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L24) |
| function | `refresh_runtime_self_narrative_continuity_signal_statuses` | `()` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L47) |
| function | `build_runtime_self_narrative_continuity_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L78) |
| function | `_extract_self_narrative_continuity_candidates` | `(*, run_id)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L112) |
| function | `_build_candidate` | `(*, focus, meaning_signal, temperament_signal, relation_continuity, chronicle_brief, chronicle_proposal)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L143) |
| function | `_persist_self_narrative_continuity_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L255) |
| function | `_latest_temperament_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L324) |
| function | `_latest_relation_continuity` | `(*, run_id, focus_key)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L336) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L348) |
| function | `_latest_chronicle_proposal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L360) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L372) |
| function | `_with_runtime_view` | `(item)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L381) |
| function | `_derive_narrative_state` | `(*, meaning_type, temperament_type, continuity_state)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L414) |
| function | `_derive_narrative_direction` | `(*, meaning_type, temperament_type, has_proposal, continuity_state)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L431) |
| function | `_derive_narrative_weight` | `(*, meaning_weight, temperament_weight, continuity_weight, brief_weight, proposal_weight)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L449) |
| function | `_derive_status` | `(*, meaning_status, temperament_status, continuity_status)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L472) |
| function | `_grounding_mode` | `(*, has_brief, has_proposal)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L483) |
| function | `_narrative_summary` | `(*, focus, narrative_state, narrative_direction, narrative_weight)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L492) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L505) |
| function | `_canonical_segment` | `(canonical_key, index, *, default)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L512) |
| function | `_support_value` | `(support_summary, key)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L519) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L528) |
| function | `_anchor_from_support_summary` | `(support_summary)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L537) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L549) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L559) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L567) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/self_narrative_continuity_signal_tracking.py#L578) |

## `core/services/self_narrative_self_model_review_bridge.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_self_narrative_self_model_review_bridge_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L13) |
| function | `_build_bridge_item` | `(*, narrative_item, self_model_item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L162) |
| function | `_pattern_view` | `(item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L362) |
| function | `_review_input_view` | `(item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L378) |
| function | `_sharpening_input_view` | `(item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L400) |
| function | `_proposal_input_view` | `(item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L424) |
| function | `_pattern_type` | `(*, narrative_state, narrative_direction, review_state)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L456) |
| function | `_self_model_alignment` | `(self_model_item)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L475) |
| function | `_persistence_state` | `(*, session_count, support_count)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L486) |
| function | `_threshold_state` | `(*, narrative_weight, pattern_confidence, persistence_state, self_model_alignment)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L494) |
| function | `_sharpening_threshold_state` | `(*, review_input_state, pattern_confidence, persistence_state, self_model_alignment)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L511) |
| function | `_sharpening_input_reason` | `(*, review_input_state, pattern_confidence, persistence_state, self_model_alignment)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L528) |
| function | `_sharpening_input_summary` | `(*, sharpening_input_state, sharpening_threshold_state, self_model_title)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L549) |
| function | `_stable_alignment_state` | `(*, self_model_alignment, self_model_status, pattern_confidence)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L562) |
| function | `_stability_window_state` | `(*, session_count, support_count)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L577) |
| function | `_identity_relevance_state` | `(*, bridge_state, self_model_title, pattern_type)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L583) |
| function | `_proposal_input_threshold_state` | `(*, sharpening_input_state, session_count, stable_alignment_state, stability_window_state, identity_relevance_state, governance_state)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L605) |
| function | `_proposal_input_reason` | `(*, sharpening_input_state, session_count, stable_alignment_state, stability_window_state, identity_relevance_state, governance_state)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L626) |
| function | `_proposal_input_summary` | `(*, proposal_input_state, proposal_input_threshold_state, stability_window_state)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L653) |
| function | `_review_input_reason` | `(*, narrative_weight, pattern_confidence, persistence_state, self_model_alignment)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L669) |
| function | `_review_input_summary` | `(*, review_input_state, threshold_state, self_model_title)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L690) |
| function | `_pattern_summary` | `(*, pattern_type, narrative_direction, narrative_weight, self_model_title)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L703) |
| function | `_bridge_summary` | `(*, narrative_state, narrative_direction, self_model_title)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L721) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L738) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_narrative_self_model_review_bridge.py#L750) |

## `core/services/self_repair_engine.py`
_Self-repair engine — runtime-instigated repair actions for known patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SelfRepairPattern` | `` | — | [src](../../../core/services/self_repair_engine.py#L30) |
| function | `_decode_pattern` | `(row)` | Build a SelfRepairPattern from a DB row dict. May raise on malformed JSON. | [src](../../../core/services/self_repair_engine.py#L47) |
| function | `_pattern_matches_event` | `(pattern, event)` | True if event matches pattern's trigger_event_kind + trigger_match predicates. | [src](../../../core/services/self_repair_engine.py#L94) |
| function | `_payload_predicate_matches` | `(expected, actual)` | Predicate forms supported in trigger_match values: | [src](../../../core/services/self_repair_engine.py#L107) |
| function | `_now` | `()` | Indirected for monkeypatching in tests. | [src](../../../core/services/self_repair_engine.py#L132) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/self_repair_engine.py#L137) |
| function | `_action_control_daemon` | `(params)` | Allowlisted handler for control_daemon. Validates params then delegates. | [src](../../../core/services/self_repair_engine.py#L146) |
| function | `_check_cooldown` | `(pattern)` | Return 'ok' if attempt allowed, else reason string explaining why blocked. | [src](../../../core/services/self_repair_engine.py#L174) |
| function | `register_pattern` | `(*, pattern_id, name, trigger_event_kind, trigger_match=…, action_type, action_params=…, enabled=…, cooldown_seconds=…, max_attempts_per_window=…, window_seconds=…, auto_disable_after_escalations=…, auto_disable_window_hours=…, source=…, source_evidence=…)` | Register a self-repair pattern. Validates action_type against allowlist. | [src](../../../core/services/self_repair_engine.py#L224) |
| function | `list_patterns` | `(*, enabled=…, trigger_event_kind=…)` | — | [src](../../../core/services/self_repair_engine.py#L287) |
| function | `enable_pattern` | `(pattern_id)` | — | [src](../../../core/services/self_repair_engine.py#L297) |
| function | `disable_pattern` | `(pattern_id)` | — | [src](../../../core/services/self_repair_engine.py#L301) |
| function | `delete_pattern` | `(pattern_id)` | — | [src](../../../core/services/self_repair_engine.py#L305) |
| function | `list_recent_attempts` | `(*, pattern_id=…, limit=…)` | — | [src](../../../core/services/self_repair_engine.py#L309) |
| function | `build_self_repair_surface` | `()` | Compact surface for Mission Control consumption. | [src](../../../core/services/self_repair_engine.py#L315) |
| function | `_engine_enabled` | `()` | — | [src](../../../core/services/self_repair_engine.py#L328) |
| function | `_notify_owner_async` | `(message)` | Best-effort Discord DM to owner. Failure is silently swallowed. | [src](../../../core/services/self_repair_engine.py#L345) |
| function | `_repair_context_features` | `(pattern, *, triggered_by, outcome, error=…)` | — | [src](../../../core/services/self_repair_engine.py#L354) |
| function | `_capture_repair_emotional_anchor` | `(pattern, *, triggered_by, outcome, error=…)` | Best-effort emotional memory capture for repair outcomes. | [src](../../../core/services/self_repair_engine.py#L372) |
| function | `_find_repair_emotional_precedents` | `(pattern, *, triggered_by)` | Return similar repair anchors with outcomes, if emotional memory is available. | [src](../../../core/services/self_repair_engine.py#L399) |
| function | `_record_executed` | `(pattern, triggered_by, result, elapsed_ms)` | — | [src](../../../core/services/self_repair_engine.py#L420) |
| function | `_record_attempt_and_escalate` | `(pattern, triggered_by, *, outcome, error, elapsed_ms)` | — | [src](../../../core/services/self_repair_engine.py#L469) |
| function | `_auto_disable_pattern` | `(pattern, failure_count)` | — | [src](../../../core/services/self_repair_engine.py#L538) |
| function | `_attempt_repair` | `(pattern, event)` | Run cooldown check, execute action, record audit, escalate if needed. | [src](../../../core/services/self_repair_engine.py#L571) |
| function | `_process_event` | `(event)` | Match event against enabled patterns, execute if any match. | [src](../../../core/services/self_repair_engine.py#L655) |
| function | `_process_emotional_gate_event` | `(event)` | Observe repeated emotional gates as candidates for repair pattern design. | [src](../../../core/services/self_repair_engine.py#L682) |
| function | `start_listener` | `()` | Start the eventbus listener daemon. Idempotent. | [src](../../../core/services/self_repair_engine.py#L751) |
| function | `stop_listener` | `()` | Signal the listener to exit. Best-effort. | [src](../../../core/services/self_repair_engine.py#L768) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/self_repair_engine.py#L778) |

## `core/services/self_review_cadence_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_cadence_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L22) |
| function | `refresh_runtime_self_review_cadence_signal_statuses` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L64) |
| function | `build_runtime_self_review_cadence_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L95) |
| function | `_extract_self_review_cadence_candidates` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L121) |
| function | `_persist_self_review_cadence_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L177) |
| function | `_build_cadence_snapshots` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L253) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L273) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L283) |
| function | `_build_cadence_state` | `(*, review_age, outcome_status)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L296) |
| function | `_build_cadence_reason` | `(*, cadence_state, review_type)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L304) |
| function | `_build_status_reason` | `(*, cadence_state)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L312) |
| function | `_build_due_hint` | `(*, cadence_state)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L320) |
| function | `_cadence_state_from_summary` | `(summary)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L328) |
| function | `_self_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L339) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L344) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L349) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L359) |

## `core/services/self_review_outcome_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_outcomes_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L29) |
| function | `refresh_runtime_self_review_outcome_statuses` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L51) |
| function | `build_runtime_self_review_outcome_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L82) |
| function | `_extract_self_review_outcome_candidates` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L124) |
| function | `_persist_self_review_outcomes` | `(*, outcomes, session_id, run_id)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L192) |
| function | `_build_outcome_snapshots` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L265) |
| function | `_with_outcome_view` | `(item, outcome)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L325) |
| function | `_with_surface_outcome_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L335) |
| function | `_build_outcome_type` | `(*, item, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L347) |
| function | `_build_short_outcome` | `(*, outcome_type, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L363) |
| function | `_build_status_reason` | `(*, outcome_type)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L375) |
| function | `_build_review_focus` | `(*, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L385) |
| function | `_closure_confidence_from_snapshot` | `(*, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L404) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L409) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L418) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L423) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L428) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L433) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L438) |
| function | `_self_review_outcome_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L443) |
| function | `_review_type_from_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L448) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L453) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L458) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L468) |

## `core/services/self_review_record_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_records_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_record_tracking.py#L30) |
| function | `refresh_runtime_self_review_record_statuses` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L52) |
| function | `build_runtime_self_review_record_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_record_tracking.py#L83) |
| function | `_extract_self_review_record_candidates` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L111) |
| function | `_persist_self_review_records` | `(*, records, session_id, run_id)` | — | [src](../../../core/services/self_review_record_tracking.py#L182) |
| function | `_build_review_brief_snapshots` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L256) |
| function | `_with_review_brief` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_record_tracking.py#L328) |
| function | `_build_review_summary` | `(*, title_suffix, snapshot)` | — | [src](../../../core/services/self_review_record_tracking.py#L345) |
| function | `_build_short_reason` | `(*, snapshot, fallback)` | — | [src](../../../core/services/self_review_record_tracking.py#L360) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_record_tracking.py#L370) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L379) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L384) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L389) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L394) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L399) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L404) |
| function | `_self_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L409) |
| function | `_self_review_record_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L414) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_record_tracking.py#L424) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_record_tracking.py#L434) |

## `core/services/self_review_run_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_runs_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_run_tracking.py#L29) |
| function | `refresh_runtime_self_review_run_statuses` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L51) |
| function | `build_runtime_self_review_run_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_run_tracking.py#L82) |
| function | `_extract_self_review_run_candidates` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L111) |
| function | `_persist_self_review_runs` | `(*, runs, session_id, run_id)` | — | [src](../../../core/services/self_review_run_tracking.py#L177) |
| function | `_build_review_run_snapshots` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L263) |
| function | `_with_run_view` | `(item, run)` | — | [src](../../../core/services/self_review_run_tracking.py#L323) |
| function | `_with_surface_run_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_run_tracking.py#L336) |
| function | `_run_summary` | `(run)` | — | [src](../../../core/services/self_review_run_tracking.py#L353) |
| function | `_run_support_summary` | `(run)` | — | [src](../../../core/services/self_review_run_tracking.py#L357) |
| function | `_build_review_focus` | `(*, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L365) |
| function | `_build_short_outlook` | `(*, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L384) |
| function | `_build_short_review_note` | `(*, title_suffix, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L394) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_run_tracking.py#L400) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L409) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L414) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L419) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L424) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L429) |
| function | `_self_review_run_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L434) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L439) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_run_tracking.py#L444) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_run_tracking.py#L454) |

## `core/services/self_review_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_signal_tracking.py#L28) |
| function | `refresh_runtime_self_review_signal_statuses` | `()` | — | [src](../../../core/services/self_review_signal_tracking.py#L50) |
| function | `build_runtime_self_review_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_signal_tracking.py#L81) |
| function | `_extract_self_review_candidates` | `()` | — | [src](../../../core/services/self_review_signal_tracking.py#L104) |
| function | `_persist_self_review_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/self_review_signal_tracking.py#L256) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/self_review_signal_tracking.py#L325) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L358) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L363) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L368) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L373) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L378) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L383) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L388) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L393) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_signal_tracking.py#L398) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_signal_tracking.py#L408) |

## `core/services/self_review_unified.py`
_Self-Review Unified — periodisk samlet selv-audit._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/self_review_unified.py#L29) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/self_review_unified.py#L33) |
| function | `_gather_review_inputs` | `()` | Pull signals v2 already has that need to be reflected upon. | [src](../../../core/services/self_review_unified.py#L58) |
| function | `_base_review` | `(inputs)` | Rule-based review as fallback when LLM unavailable. | [src](../../../core/services/self_review_unified.py#L96) |
| function | `_build_review_prompt` | `(inputs)` | — | [src](../../../core/services/self_review_unified.py#L143) |
| function | `_extract_review_json` | `(raw)` | — | [src](../../../core/services/self_review_unified.py#L174) |
| function | `run_self_review` | `(*, period=…)` | Generate and persist a self-review. Returns the review dict. | [src](../../../core/services/self_review_unified.py#L200) |
| function | `maybe_run_self_review` | `(*, min_hours_between=…)` | Run a review if it's been at least N hours since the last. | [src](../../../core/services/self_review_unified.py#L309) |
| function | `list_self_reviews` | `(*, limit=…)` | — | [src](../../../core/services/self_review_unified.py#L330) |
| function | `build_self_review_surface` | `()` | — | [src](../../../core/services/self_review_unified.py#L349) |

## `core/services/self_surprise_detection.py`
_Self-Surprise Detection — "Huh, det havde jeg ikke forventet af mig selv."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_self_surprise` | `(*, expected_confidence, actual_outcome, domain=…, run_id=…)` | — | [src](../../../core/services/self_surprise_detection.py#L11) |
| function | `build_self_surprise_surface` | `()` | — | [src](../../../core/services/self_surprise_detection.py#L39) |

## `core/services/self_system_code_awareness.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_self_system_code_awareness_surface` | `()` | — | [src](../../../core/services/self_system_code_awareness.py#L16) |
| function | `_default_repo_observation` | `()` | — | [src](../../../core/services/self_system_code_awareness.py#L114) |
| function | `_detect_repo_root` | `(*starts)` | — | [src](../../../core/services/self_system_code_awareness.py#L134) |
| function | `_observe_repo_status` | `(repo_root)` | — | [src](../../../core/services/self_system_code_awareness.py#L147) |
| function | `_derive_concern_state` | `(*, repo_status, local_change_state, upstream_awareness, branch_name)` | — | [src](../../../core/services/self_system_code_awareness.py#L236) |
| function | `_run_read_only_command` | `(args)` | — | [src](../../../core/services/self_system_code_awareness.py#L279) |
| function | `_safe_int` | `(raw)` | — | [src](../../../core/services/self_system_code_awareness.py#L298) |
| function | `_status_xy` | `(line)` | — | [src](../../../core/services/self_system_code_awareness.py#L305) |
| function | `_status_path` | `(line)` | — | [src](../../../core/services/self_system_code_awareness.py#L312) |
| function | `_append_bounded_path` | `(paths, value, *, limit=…)` | — | [src](../../../core/services/self_system_code_awareness.py#L319) |
| function | `_approval_required_mutation_classes` | `(capabilities)` | — | [src](../../../core/services/self_system_code_awareness.py#L326) |
| function | `_emit_self_system_code_awareness_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/self_system_code_awareness.py#L341) |

## `core/services/self_wakeup.py`
_Self-wakeup — Jarvis' equivalent of Claude Code's ScheduleWakeup._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/self_wakeup.py#L48) |
| function | `_save` | `(records)` | — | [src](../../../core/services/self_wakeup.py#L55) |
| function | `schedule_self_wakeup` | `(*, delay_seconds, prompt, reason=…, channel=…, session_id=…)` | Queue a self-wakeup. Returns the wakeup record. | [src](../../../core/services/self_wakeup.py#L59) |
| function | `due_wakeups` | `(*, include_fired_unconsumed=…)` | Return wakeups whose fire_at has passed and not yet consumed. | [src](../../../core/services/self_wakeup.py#L115) |
| function | `mark_wakeup_consumed` | `(wakeup_id)` | Clear a fired wakeup once Jarvis has acted on it. | [src](../../../core/services/self_wakeup.py#L144) |
| function | `cancel_wakeup` | `(wakeup_id)` | Cancel a pending wakeup before it fires. | [src](../../../core/services/self_wakeup.py#L163) |
| function | `list_wakeups` | `(*, status=…, limit=…)` | — | [src](../../../core/services/self_wakeup.py#L181) |
| function | `cleanup_old_wakeups` | `(*, consumed_age_hours=…, cancelled_age_hours=…, stale_fired_age_hours=…)` | Ryd op i gamle consumed/cancelled/stale-fired wakeups. | [src](../../../core/services/self_wakeup.py#L189) |
| function | `tick_wakeup_cleanup` | `()` | Daemon tick — ryd op i gamle wakeups. | [src](../../../core/services/self_wakeup.py#L250) |
| function | `self_wakeup_section` | `()` | Awareness section showing fired-but-not-consumed wakeups. | [src](../../../core/services/self_wakeup.py#L259) |
| function | `_exec_schedule_self_wakeup` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L282) |
| function | `_exec_list_self_wakeups` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L290) |
| function | `_exec_cancel_self_wakeup` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L300) |
| function | `_exec_mark_wakeup_consumed` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L304) |

## `core/services/selfhood_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_selfhood_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L30) |
| function | `refresh_runtime_selfhood_proposal_statuses` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L52) |
| function | `build_runtime_selfhood_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L83) |
| function | `_extract_selfhood_proposals` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L112) |
| function | `_persist_selfhood_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L198) |
| function | `_build_snapshots` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L272) |
| function | `_snapshot_entry` | `(snapshots, domain_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L283) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L291) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L302) |
| function | `_proposal_type_from_prompt_type` | `(prompt_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L314) |
| function | `_selfhood_target_for_type` | `(proposal_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L324) |
| function | `_proposed_shift_for_type` | `(proposal_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L334) |
| function | `_proposal_confidence` | `(*, prompt_confidence, snapshot)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L344) |
| function | `_proposal_reason` | `(*, proposal_type, selfhood_target, proposal_confidence)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L354) |
| function | `_source_anchor` | `(*, item, snapshot)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L364) |
| function | `_proposal_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L372) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L381) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L386) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L391) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L396) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L408) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L417) |

## `core/services/semantic_indexer.py`
_Semantic indexer — auto-embedding of new memory records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_semantic_indexer` | `()` | — | [src](../../../core/services/semantic_indexer.py#L34) |
| function | `stop_semantic_indexer` | `()` | — | [src](../../../core/services/semantic_indexer.py#L62) |
| function | `_sweeper_loop` | `()` | Every N minutes, run backfill_all to catch new rows without events. | [src](../../../core/services/semantic_indexer.py#L81) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/semantic_indexer.py#L109) |
| function | `_handle_sensory` | `(payload)` | — | [src](../../../core/services/semantic_indexer.py#L140) |
| function | `_handle_private_brain` | `(payload)` | — | [src](../../../core/services/semantic_indexer.py#L160) |
| function | `build_semantic_indexer_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/semantic_indexer.py#L186) |

## `core/services/semantic_memory.py`
_Semantic memory — unified embedding + cosine search across memory surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_source` | `(table, *, resolver, lister)` | Register a source table so backfill + search can map IDs to rows. | [src](../../../core/services/semantic_memory.py#L48) |
| function | `_default_sources_registered` | `()` | Register sensory_memories + private_brain_records if not already. | [src](../../../core/services/semantic_memory.py#L59) |
| function | `_ollama_base_url` | `()` | — | [src](../../../core/services/semantic_memory.py#L90) |
| function | `_tt_embed` | `(label, dur_ms)` | — | [src](../../../core/services/semantic_memory.py#L128) |
| function | `_embed_ollama` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L136) |
| function | `_embed_ollama_batch` | `(texts)` | Batch-embed via ollamas /api/embed (ÉT round-trip for hele listen i stedet | [src](../../../core/services/semantic_memory.py#L170) |
| function | `_encode_vector` | `(vec)` | — | [src](../../../core/services/semantic_memory.py#L205) |
| function | `_decode_vector` | `(data)` | — | [src](../../../core/services/semantic_memory.py#L209) |
| function | `_hash_content` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L213) |
| function | `_prepare_text` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L217) |
| function | `index_memory` | `(*, source_table, source_id, content, modality)` | Embed content and upsert. Returns True on success, False if embed fails | [src](../../../core/services/semantic_memory.py#L226) |
| function | `search` | `(query, *, modalities=…, source_tables=…, limit=…, min_score=…)` | Return top-k memories by cosine similarity. | [src](../../../core/services/semantic_memory.py#L261) |
| function | `_extract_content_for_row` | `(table, row)` | Return (content_text, modality) for a raw row from a known table. | [src](../../../core/services/semantic_memory.py#L325) |
| function | `_row_id` | `(table, row)` | — | [src](../../../core/services/semantic_memory.py#L340) |
| function | `backfill_all` | `(*, max_per_table=…)` | Embed every unindexed row across registered source tables. | [src](../../../core/services/semantic_memory.py#L348) |
| function | `_content_hash_unchanged` | `(table, source_id, new_content)` | — | [src](../../../core/services/semantic_memory.py#L423) |
| function | `get_stats` | `()` | — | [src](../../../core/services/semantic_memory.py#L432) |
| function | `build_semantic_memory_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/semantic_memory.py#L445) |

