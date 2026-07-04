# Central-connectivity-kort (core/services)

Statisk, genkørbart kort: `python scripts/central_connectivity_audit.py`.
Svarer på ét spørgsmål pr. service: **når laget Centralen?** Rute-familier læses
live fra `eventbus_central_bridge.py`, så kortet aldrig driver fra broen.

**819 services** · 236 bridge-familier. Fordeling:

| Kvadrant | Antal | Betydning |
|----------|-------|-----------|
| KOBLET | 451 | direkte central-kald ELLER event-family der bridges |
| FRAKOBLET+LLM | 41 | **spilder: LLM-kald uden central-binding (§3, høj prio)** |
| FRAKOBLET+DARK | 50 | emitterer events hvis family INGEN rute har → signal tabt |
| FRAKOBLET-STILLE | 277 | ingen binding/LLM/events → ren utility (oftest OK) |

## KOBLET (451)

| Service | Direkte | Indirekte (bridges) | LLM |
|---------|---------|---------------------|-----|
| `absence_awareness` | — | absence_awareness | — |
| `action_router` | ✓ | — | — |
| `active_sensing_daemon` | — | cognitive_state | — |
| `aesthetic_sense` | — | cognitive_aesthetic | — |
| `aesthetic_taste_daemon` | — | cognitive_taste | ✓ |
| `affect_modulation` | — | affect_modulation | — |
| `affective_state_renderer` | — | affective_state_renderer | — |
| `affirmation_anchor` | — | affirmation_anchor | — |
| `agency_cartographer` | — | agency_cartographer | — |
| `agent_runtime` | — | runtime | ✓ |
| `agent_self_evaluation` | — | tick_quality | — |
| `agentic_checkpoints` | — | agentic_checkpoints | — |
| `agentic_working_conclusions` | — | agentic_working_conclusions | — |
| `agents` | ✓ | — | — |
| `agreement_streak` | — | agreement_streak | — |
| `ambient_presence` | — | runtime | — |
| `anticipatory_context` | — | cognitive_anticipation | — |
| `associative_recall` | ✓ | memory | ✓ |
| `attachment_service` | ✓ | — | — |
| `attachment_topology_signal_tracking` | — | attachment_topology_signal | — |
| `attention_blink_test` | — | cognitive_surprise, tool | — |
| `attention_budget` | — | attention_budget | — |
| `auto_improvement_proposer` | — | auto_improvement | — |
| `autonomous_council_daemon` | ✓ | council | ✓ |
| `autonomous_goals` | — | goal | ✓ |
| `autonomous_supervisor` | ✓ | — | — |
| `autonomy_pressure_signal_tracking` | — | autonomy_pressure_signal | — |
| `autonomy_proposal_queue` | — | autonomy_proposal | — |
| `avoidance_detector` | — | avoidance_detector | — |
| `behavioral_decisions` | ✓ | decision | — |
| `boredom_curiosity_bridge` | ✓ | — | — |
| `boredom_engine` | — | cognitive_state | — |
| `broadcast_daemon` | — | workspace | — |
| `cache_telemetry` | ✓ | — | — |
| `cadence_producers` | ✓ | cognitive_state | — |
| `calm_anchor` | — | calm_anchor | — |
| `candidate_tracking` | — | runtime | — |
| `causal_graph` | — | causal_graph | — |
| `causal_inference_daemon` | — | causal | — |
| `central_adaptation` | ✓ | egen-central | — |
| `central_agenda` | ✓ | egen-central | — |
| `central_anomaly` | ✓ | anomaly | — |
| `central_arbitration` | ✓ | egen-central | — |
| `central_body_mood_feel` | — | egen-central | — |
| `central_brain_link` | ✓ | egen-central | — |
| `central_capture` | — | egen-central | — |
| `central_catalog` | — | egen-central | — |
| `central_causal_quality` | ✓ | egen-central | — |
| `central_convene_judge` | ✓ | egen-central | — |
| `central_core` | ✓ | egen-central | — |
| `central_correlate` | ✓ | egen-central | — |
| `central_coverage` | ✓ | egen-central | — |
| `central_coverage_action` | ✓ | egen-central | — |
| `central_drift` | — | egen-central | — |
| `central_error_envelope` | ✓ | egen-central | — |
| `central_existence_feel` | — | egen-central | — |
| `central_form_judge` | ✓ | egen-central | — |
| `central_growth_observe` | ✓ | egen-central | — |
| `central_health` | ✓ | egen-central | — |
| `central_hub` | — | egen-central | — |
| `central_hypothesis_generator` | ✓ | egen-central | — |
| `central_hypothesis_governance` | ✓ | egen-central | — |
| `central_hypothesis_sampler` | ✓ | egen-central | — |
| `central_inner_salience` | ✓ | egen-central | — |
| `central_instrument` | ✓ | egen-central | — |
| `central_layer_contract` | ✓ | egen-central | — |
| `central_learning` | ✓ | egen-central | — |
| `central_lexicon` | — | egen-central | — |
| `central_model_meta` | ✓ | egen-central | — |
| `central_noise_filter` | — | egen-central | — |
| `central_notation` | ✓ | egen-central | — |
| `central_private_observe` | ✓ | egen-central | — |
| `central_prompt_composer` | ✓ | egen-central | — |
| `central_prompt_explore` | ✓ | egen-central | — |
| `central_proposal` | — | egen-central | — |
| `central_realtime` | ✓ | egen-central | — |
| `central_render` | — | egen-central | — |
| `central_router_adapt` | ✓ | egen-central | — |
| `central_router_explore` | — | egen-central | — |
| `central_self_model` | ✓ | egen-central | — |
| `central_self_observe` | ✓ | egen-central | — |
| `central_self_state` | ✓ | egen-central | — |
| `central_sequence` | ✓ | egen-central | — |
| `central_shadow` | ✓ | egen-central | — |
| `central_signal_health` | ✓ | egen-central | — |
| `central_soul_feel` | — | egen-central | — |
| `central_stance` | ✓ | egen-central | — |
| `central_switches` | — | egen-central | — |
| `central_terminal` | ✓ | egen-central | — |
| `central_timeseries` | — | egen-central | — |
| `central_todo` | — | egen-central | — |
| `central_trace` | ✓ | egen-central | — |
| `central_valence` | ✓ | egen-central | — |
| `central_watch` | ✓ | egen-central | — |
| `central_xproc` | ✓ | egen-central | — |
| `channel_inbound` | ✓ | — | — |
| `cheap_provider_runtime` | — | runtime | ✓ |
| `chronicle_consolidation_brief_tracking` | — | chronicle_consolidation_brief | — |
| `chronicle_consolidation_proposal_tracking` | — | chronicle_consolidation_proposal | — |
| `chronicle_consolidation_signal_tracking` | — | chronicle_consolidation_signal | — |
| `clarification_classifier` | — | clarification_classifier | — |
| `code_aesthetic_daemon` | — | cognitive_aesthetic | ✓ |
| `cognitive_episodes` | — | cognitive_state | — |
| `cognitive_state_assembly` | ✓ | — | — |
| `communication_guard` | ✓ | communication | — |
| `compass_engine` | — | cognitive_compass | — |
| `completion_satisfaction` | — | completion_satisfaction | — |
| `concept_baseline_tracker` | — | concept_baseline | — |
| `config_drift` | ✓ | — | — |
| `conflict_prompt_service` | — | conflict_prompt_service | — |
| `conflict_resolution` | — | conflict_resolution | — |
| `connections` | ✓ | — | — |
| `consent_registry` | — | cognitive_state | — |
| `consolidation_judge_daemon` | — | consolidation_judge | — |
| `consolidation_target_signal_tracking` | — | consolidation_target_signal | — |
| `contract_evolution` | — | cognitive_state | — |
| `contradiction_engine` | — | contradiction | — |
| `conversation_rhythm` | — | cognitive_state | — |
| `council_deliberation_controller` | — | council | ✓ |
| `council_memory_daemon` | — | council | ✓ |
| `council_memory_service` | — | council_memory | — |
| `counterfactual_engine` | — | cognitive_counterfactual | ✓ |
| `counterfactual_engine_runtime` | — | counterfactual_engine_runtime | — |
| `counterfactual_predictions` | — | counterfactual_predictions | — |
| `counterfactual_self_simulation` | — | cognitive_state | — |
| `counterfactual_triggers` | — | counterfactual_triggers | — |
| `cowork_dispatch` | — | cowork | — |
| `creative_drift_daemon` | — | creative_drift | — |
| `creative_journal_runtime` | — | cognitive_state | ✓ |
| `crisis_marker_detector` | — | crisis_marker | — |
| `cross_agent_memory` | — | cross_agent_memory | — |
| `cross_signal_analysis` | — | cognitive_state | — |
| `curiosity_consolidation` | — | cognitive_state | ✓ |
| `curiosity_daemon` | — | curiosity | — |
| `curiosity_hypothesis_debt` | ✓ | cognitive_state | — |
| `current_pull` | — | cognitive_state | ✓ |
| `daemon_health` | ✓ | — | — |
| `daemon_llm` | ✓ | — | ✓ |
| `day_shape_memory` | — | day_shape_memory | — |
| `db_sentinel` | ✓ | — | — |
| `decision_enforcement` | — | decision | ✓ |
| `decision_gate` | — | decision_gate | — |
| `decision_log` | — | cognitive_decision | — |
| `decision_signal_telemetry` | — | decision_signal_telemetry | — |
| `decision_signals` | — | decision_signal | — |
| `decisions_journal` | — | cognitive_decision | — |
| `delegation_advisor` | — | delegation_advisor | — |
| `desire_daemon` | — | desire | — |
| `desperation_awareness` | — | inner_voice | — |
| `development_focus_tracking` | — | runtime | — |
| `development_sense` | — | development_sense | — |
| `diagnosis_gate` | — | diagnosis, promise | — |
| `diary_synthesis_signal_tracking` | — | diary_synthesis_signal | — |
| `discord_gateway` | — | channel, discord | — |
| `dream_adoption_candidate_tracking` | — | dream_adoption_candidate | — |
| `dream_articulation` | — | runtime | — |
| `dream_carry_over` | — | cognitive_state | — |
| `dream_distillation_daemon` | — | cognitive_state | ✓ |
| `dream_hypothesis_forced` | — | dream_hypothesis_forced | — |
| `dream_hypothesis_generator` | — | cognitive_dream | ✓ |
| `dream_hypothesis_signal_tracking` | — | dream_hypothesis_signal | — |
| `dream_influence_proposal_tracking` | — | dream_influence_proposal | — |
| `dream_insight_daemon` | — | dream_hypothesis_signal | — |
| `dreaming_session` | — | dreaming_session | — |
| `drive_arbitration_engine` | — | cognitive_state | — |
| `embodied_presence` | — | embodied_presence | — |
| `emergent_goals` | — | cognitive_state | — |
| `emergent_signal_tracking` | — | runtime | — |
| `emotion_concepts_positive_triggers` | — | emotion_concepts_positive_triggers | — |
| `emotion_repair_bridge_daemon` | — | self_repair | ✓ |
| `emotion_tagging` | — | emotion_tagging | — |
| `emotional_chords` | — | emotional_chords | — |
| `emotional_memory_engine` | — | emotional_memory | — |
| `end_of_run_memory_consolidation` | ✓ | memory | — |
| `endpoint_usage_store` | ✓ | — | — |
| `epistemic_pragmatic` | — | epistemic_pragmatic | — |
| `epistemics` | — | cognitive_epistemic | — |
| `eventbus_central_bridge` | ✓ | egen-central | — |
| `executive_contradiction_signal_tracking` | — | executive_contradiction_signal | — |
| `existential_wonder_daemon` | ✓ | — | ✓ |
| `experience_correction_listener` | — | experience_correction_listener | — |
| `experience_episodes` | — | experience_episodes | — |
| `experience_substrate` | — | experience_substrate | — |
| `finitude_runtime` | — | cognitive_state | ✓ |
| `flow_state_detection` | — | cognitive_state | — |
| `followup_observer` | ✓ | — | — |
| `forgetting_curve` | — | cognitive_forgetting | — |
| `forgetting_engine` | ✓ | cognitive_forgetting | — |
| `gate_execution` | ✓ | — | — |
| `gate_mutation` | ✓ | — | — |
| `gate_skill` | ✓ | — | — |
| `global_workspace` | — | global_workspace | — |
| `goal_signal_synthesizer` | — | goal | ✓ |
| `goal_signal_tracking` | — | goal_signal | — |
| `good_enough_gate` | — | good_enough_gate | — |
| `gratitude_tracker` | ✓ | cognitive_state | — |
| `gut_calibration` | ✓ | — | — |
| `gut_engine` | ✓ | cognitive_gut | — |
| `habit_tracker` | — | cognitive_habit | — |
| `habits_pipeline` | — | cognitive_habit | — |
| `hallucination_guard` | ✓ | — | — |
| `hardware_body` | — | hardware_body | — |
| `heartbeat_phases` | — | heartbeat | — |
| `heartbeat_provider_fallback` | ✓ | — | ✓ |
| `heartbeat_runtime` | ✓ | channel, heartbeat, runtime | ✓ |
| `identity_composer` | — | identity_composer | — |
| `identity_drift_proposer` | — | identity_drift | — |
| `identity_guard` | ✓ | — | — |
| `identity_mutation_log` | — | identity_mutation | — |
| `idle_consolidation` | — | runtime | — |
| `idle_thinking` | — | cognitive_state | — |
| `impulse_executor` | ✓ | impulse | — |
| `infra_sense` | ✓ | — | — |
| `inheritance_seed` | — | inheritance_seed | — |
| `initiative_accumulator` | — | initiative_accumulator | — |
| `initiative_queue` | — | heartbeat | — |
| `inner_dialectic_engine` | — | cognitive_state | — |
| `inner_visible_support_signal_tracking` | — | inner_visible_support_signal | — |
| `inner_voice_daemon` | — | private_inner_note_signal | ✓ |
| `inner_voice_notifier` | — | inner_voice_notifier | — |
| `internal_cadence` | ✓ | heartbeat | — |
| `internal_opposition_signal_tracking` | — | internal_opposition_signal | — |
| `jarvis_brain` | ✓ | — | — |
| `jarvisx_bridge` | ✓ | — | — |
| `layer_tension_daemon` | — | layer_tension | — |
| `learning_pipeline_orchestrator` | — | learning_pipeline | — |
| `learning_policy_engine` | — | cognitive_state | — |
| `life_milestones` | — | life_milestones | — |
| `life_projects` | — | life_projects | — |
| `living_executive` | — | living_executive | — |
| `long_horizon_goals` | — | goal | — |
| `longing_signal_daemon` | ✓ | — | — |
| `loyalty_gradient_signal_tracking` | — | loyalty_gradient_signal | — |
| `meaning_significance_signal_tracking` | — | meaning_significance_signal | — |
| `memory_consolidation_nudge` | — | memory_consolidation_nudge | — |
| `memory_decay_daemon` | ✓ | memory | — |
| `memory_emotional_context` | — | memory_emotional_context | — |
| `memory_maintenance_daemon` | — | memory | — |
| `memory_md_update_proposal_tracking` | — | memory_md_update_proposal | — |
| `memory_recall_engine` | ✓ | memory | — |
| `memory_recall_telemetry` | — | memory | — |
| `memory_resurfacing` | — | memory_resurfacing | — |
| `memory_write_policy` | — | memory_write_policy | — |
| `memory_write_queue` | — | memory | — |
| `meta_cognition_daemon` | — | experiment | ✓ |
| `meta_learning_aggregator` | — | meta_learning_aggregator | — |
| `meta_learning_hypotheses` | — | meta_learning_hypotheses | — |
| `metabolism_state_signal_tracking` | — | metabolism_state_signal | — |
| `metacognition_signal_tracker` | — | runtime | — |
| `metacognitive_integration` | — | metacognitive_integration | — |
| `mirror_engine` | — | cognitive_mirror | — |
| `missions_pipeline` | — | cognitive_mission | — |
| `mood_dialer` | — | mood_dialer | — |
| `narrative_identity` | — | cognitive_state | — |
| `narrative_summary_daemon` | — | narrative | — |
| `negotiation_engine` | — | cognitive_negotiation | — |
| `negotiation_pipeline` | — | cognitive_trade | — |
| `network_health` | ✓ | — | — |
| `non_visible_lane_execution` | — | runtime | ✓ |
| `notification_bridge` | — | channel | — |
| `notification_router` | ✓ | — | — |
| `nudge_broend` | — | nudge_broend | — |
| `oauth_flow` | ✓ | — | — |
| `offline_recomposition_engine` | — | cognitive_state | — |
| `open_loop_closure_proposal_tracking` | — | open_loop_closure_proposal | — |
| `open_loop_signal_tracking` | — | open_loop_signal | — |
| `outbound_nudges` | — | nudge | — |
| `outcome_learning` | — | outcome_learning | — |
| `outreach_composer` | — | impulse | — |
| `override_command` | ✓ | — | — |
| `paradox_tracker` | — | cognitive_paradox | — |
| `paradoxes_capture` | — | cognitive_paradox | — |
| `pattern_counterfactual_daemon` | — | counterfactual | — |
| `perceptual_event_engine` | — | cognitive_state | — |
| `personal_project` | — | cognitive_personal_project | ✓ |
| `personality_drift` | — | personality_drift | — |
| `personality_vector` | — | cognitive_personality | — |
| `plan_proposals` | — | cognitive_state | — |
| `policy_abstraction` | — | learning_policy | — |
| `precision_bias` | — | precision_bias | — |
| `pressure_threshold_gate` | ✓ | impulse | — |
| `priors_feedback` | — | priors_feedback | — |
| `private_initiative_tension_signal_tracking` | — | private_initiative_tension_signal | — |
| `private_inner_interplay_signal_tracking` | — | private_inner_interplay_signal | — |
| `private_inner_note_signal_tracking` | — | private_inner_note_signal | — |
| `private_state_snapshot_tracking` | — | private_state_snapshot | — |
| `private_temporal_curiosity_state_tracking` | — | private_temporal_curiosity_state | — |
| `private_temporal_promotion_signal_tracking` | — | private_temporal_promotion_signal | — |
| `proactive_context_governor` | — | context | — |
| `proactive_loop_lifecycle_tracking` | — | proactive_loop_lifecycle | — |
| `proactive_outbound_substrate` | — | proactive_outbound_substrate | — |
| `proactive_question_gate_tracking` | — | proactive_question_gate | — |
| `procedure_bank` | — | cognitive_procedure | — |
| `procedure_bank_pipeline` | — | cognitive_procedure | — |
| `producer_novelty` | ✓ | — | — |
| `prompt_contract` | ✓ | prompt | ✓ |
| `prompt_evolution` | — | runtime | — |
| `prompt_evolution_runtime` | — | runtime | — |
| `prompt_observer` | ✓ | — | — |
| `prompt_support_signals` | — | prompt_support_signals | — |
| `prompt_variant_tracker` | — | prompt_variant_tracker | — |
| `proposal_classifier` | — | proposal_classifier | — |
| `prospective_memory` | — | memory | — |
| `provider_circuit_breaker` | ✓ | — | — |
| `provider_health_check` | ✓ | runtime | ✓ |
| `provider_retry_policy` | — | runtime | — |
| `pushback` | — | pushback | — |
| `r2_5_blocking_gate` | — | r2_5_blocking_gate, r2_5_gate | — |
| `read_before_write_guard` | — | read_before_write_guard | — |
| `reasoning_classifier` | — | reasoning_classifier | — |
| `reasoning_escalation` | — | reasoning_escalation | — |
| `reasoning_store` | — | reasoning | — |
| `reboot_awareness_daemon` | — | reboot | — |
| `recurrence_loop_daemon` | — | experiment | ✓ |
| `reflection_signal_tracking` | — | reflection_signal | — |
| `reflection_to_plan` | — | cognitive_reflective_plan | ✓ |
| `reflective_critic_tracking` | — | reflective_critic | — |
| `regret_engine` | — | regret | — |
| `regulation_homeostasis_signal_tracking` | ✓ | — | — |
| `relation_continuity_signal_tracking` | — | relation_continuity_signal | — |
| `relation_map` | — | relation_map | — |
| `relation_state_signal_tracking` | — | relation_state_signal | — |
| `relationship_texture` | — | cognitive_relationship | — |
| `release_marker_signal_tracking` | — | release_marker_signal | — |
| `remembered_fact_signal_tracking` | — | remembered_fact_signal | — |
| `rhythm_engine` | — | cognitive_rhythm | — |
| `run_closure_gate` | ✓ | runtime | — |
| `run_event_log` | ✓ | — | — |
| `runtime_action_executor` | — | runtime | — |
| `runtime_action_outcome_tracking` | — | runtime | — |
| `runtime_cognitive_conductor` | ✓ | — | ✓ |
| `runtime_decision_engine` | — | runtime_decision_engine | — |
| `runtime_self_model` | — | runtime_self_model | ✓ |
| `rupture_repair` | — | rupture | — |
| `scheduled_tasks` | ✓ | — | — |
| `seed_system` | — | cognitive_seed | — |
| `selective_attention` | — | selective_attention | — |
| `selective_forgetting_candidate_tracking` | — | selective_forgetting_candidate | — |
| `self_authored_prompt_proposal_tracking` | — | self_authored_prompt_proposal | — |
| `self_critique_runtime` | — | cognitive_state | ✓ |
| `self_deception_guard` | — | self_deception_guard | — |
| `self_experiments` | — | cognitive_experiment | — |
| `self_model_blind_spots` | — | cognitive_blind_spot | ✓ |
| `self_model_predictive` | — | self_model_predictive | — |
| `self_model_signal_tracking` | — | self_model_signal | — |
| `self_monitor` | — | self_monitor | — |
| `self_mutation_lineage` | — | self_mutation_lineage | — |
| `self_narrative_continuity_signal_tracking` | — | self_narrative_continuity_signal | — |
| `self_narrative_self_model_review_bridge` | — | self_narrative_self_model_review_bridge | — |
| `self_repair_engine` | — | self_repair | — |
| `self_review_cadence_signal_tracking` | — | self_review_cadence_signal | — |
| `self_review_outcome_tracking` | — | self_review_outcome | — |
| `self_review_record_tracking` | — | self_review_record | — |
| `self_review_run_tracking` | — | self_review_run | — |
| `self_review_signal_tracking` | — | self_review_signal | — |
| `self_review_unified` | ✓ | cognitive_self_review | ✓ |
| `self_surprise_detection` | — | cognitive_state | — |
| `self_system_code_awareness` | — | self_system_code_awareness | — |
| `self_wakeup` | — | self_wakeup | — |
| `selfhood_proposal_tracking` | — | selfhood_proposal | — |
| `sensory_archive` | — | memory | — |
| `session_continuity` | — | cognitive_morning_thread | ✓ |
| `session_inbox` | — | channel | — |
| `shared_language` | — | cognitive_shared_language | — |
| `shared_language_extended` | — | cognitive_shared_language | — |
| `signal_noise_guard` | — | signal_noise_guard | — |
| `signal_pressure_accumulator` | — | pressure | — |
| `signal_surface_router` | ✓ | — | — |
| `silence_detector` | — | cognitive_silence | — |
| `silence_patterns` | — | cognitive_silence | — |
| `social_labilizer` | — | pressure, social_labilizer | — |
| `somatic_daemon` | — | somatic | ✓ |
| `somatic_runtime_body` | — | cognitive_state | — |
| `stream_sentinel` | ✓ | — | — |
| `subagent_digest` | — | subagent_digest | — |
| `surprise_daemon` | — | cognitive_surprise | ✓ |
| `surprise_detector` | — | surprise | — |
| `system_cartographer` | ✓ | — | — |
| `taste_profile` | — | cognitive_taste | — |
| `telegram_gateway` | — | telegram | — |
| `temperament_tendency_signal_tracking` | — | temperament_tendency_signal | — |
| `temporal_context` | — | temporal_context | — |
| `temporal_depth` | — | temporal_depth | — |
| `temporal_recurrence_signal_tracking` | — | temporal_recurrence_signal | — |
| `temporal_self_continuity` | — | cognitive_state | — |
| `theory_of_mind_engine` | — | cognitive_state | — |
| `thought_action_proposal_daemon` | — | thought_action_proposal | — |
| `thought_thread` | — | thought_thread | — |
| `tiny_webchat_execution_pilot` | — | channel | — |
| `tool_observer` | ✓ | — | — |
| `tool_outcome_memory` | — | tool_outcome_memory | — |
| `tool_pattern_miner` | — | tool_pattern_miner | — |
| `tool_router` | — | tool_router | — |
| `tool_router_runtime` | — | tool_router | — |
| `tool_usage_store` | ✓ | — | — |
| `unconscious_modulation` | ✓ | — | — |
| `user_contradiction_tracker` | — | user_contradiction | — |
| `user_emotional_resonance` | — | cognitive_user_emotion | — |
| `user_md_update_proposal_tracking` | — | user_md_update_proposal | — |
| `user_temperature_runtime` | — | user_temperature_runtime | — |
| `user_theory_of_mind` | — | user_theory_of_mind | — |
| `user_understanding_signal_tracking` | — | user_understanding_signal | — |
| `valence_trajectory` | — | valence_trajectory | — |
| `value_formation` | — | cognitive_state | — |
| `verification_gate` | ✓ | — | — |
| `veto_gate` | — | veto_gate | — |
| `visible_followup` | ✓ | — | ✓ |
| `visible_model` | ✓ | — | ✓ |
| `visible_runs` | ✓ | channel, cost, memory, runtime, tool | ✓ |
| `visible_self_state_summary` | — | visible_self_state_summary | — |
| `visual_memory` | — | cognitive_state | — |
| `voice_curator` | — | voice_curator | — |
| `wakeup_dispatcher` | — | self_wakeup | — |
| `witness_signal_tracking` | — | witness_signal | — |
| `world_model_auto_extraction` | ✓ | — | ✓ |
| `world_model_signal_tracking` | ✓ | — | — |
| `central_query_tool` | ✓ | egen-central | — |
| `mic_listen_tool` | ✓ | — | — |
| `pause_and_ask_tools` | — | tool | — |
| `screen_tool` | ✓ | — | — |
| `sensory_tools` | ✓ | — | — |
| `simple_tools` | ✓ | emotional, incident, tool, tool_router | — |
| `skill_chain_propose_tool` | — | cognitive_skill_chain | ✓ |
| `skill_chain_revise_tool` | — | cognitive_skill_chain | — |
| `skill_chain_tool` | — | cognitive_skill_chain | — |
| `skill_engine_tools` | — | cognitive_state | — |
| `speak_tool` | ✓ | — | — |
| `visual_memory_tool` | ✓ | — | — |
| `voice_journal_tool` | ✓ | — | — |
| `wake_word_tool` | ✓ | — | — |
| `workspace_capabilities` | — | runtime | — |
| `inner_llm_enrichment` | ✓ | — | ✓ |
| `private_development_state` | ✓ | — | — |
| `private_growth_note` | ✓ | — | — |
| `private_initiative_tension` | ✓ | — | — |
| `private_inner_interplay` | ✓ | — | — |
| `private_inner_note` | ✓ | — | — |
| `private_operational_preference` | ✓ | — | — |
| `private_promotion_decision` | ✓ | — | — |
| `private_reflective_selection` | ✓ | — | — |
| `private_relation_state` | ✓ | — | — |
| `private_retained_memory_record` | ✓ | — | — |
| `private_self_model` | ✓ | — | — |
| `private_state` | ✓ | — | — |
| `private_temporal_curiosity_state` | ✓ | — | — |
| `private_temporal_promotion_signal` | ✓ | — | — |
| `protected_inner_voice` | ✓ | — | — |
| `candidate_workflow` | ✓ | memory, runtime | — |
| `runtime_candidates` | ✓ | — | — |
| `runtime_contract` | ✓ | — | — |
| `visible_identity` | ✓ | — | — |

## FRAKOBLET+LLM (41)

| Service | Dark event-families (tabt signal) |
|---------|-----------------------------------|
| `absence_daemon` | absence |
| `agent_observation_compressor` | agent_observation |
| `agent_skill_distiller` | agent_skill_distiller |
| `ambient_sound_daemon` | ambient_sound |
| `apophenia_guard` | — |
| `arc_rule_extractor` | arc_rules |
| `cheap_lane_balancer` | — |
| `chronicle_engine` | cognitive_chronicle |
| `conflict_daemon` | conflict |
| `decision_review_prompter` | decision_review_prompter |
| `deep_reflection_slot` | — |
| `development_narrative_daemon` | development_narrative |
| `dream_bias_engine` | cognitive_dream_bias |
| `dream_consolidation_daemon` | — |
| `dream_motif_daemon` | — |
| `experienced_time_daemon` | experienced_time_daemon |
| `experiential_memory` | cognitive_experiential |
| `identity_drift_daemon` | identity |
| `inner_voice_shadow` | — |
| `irony_daemon` | irony |
| `jarvis_brain_daemon` | — |
| `long_arc_synthesizer` | long_arc |
| `mail_checker_daemon` | mail_checker |
| `memory_graph` | memory_graph |
| `meta_learning_retrospective` | — |
| `meta_reflection_daemon` | meta_reflection |
| `prompt_relevance_backend` | prompt_relevance_backend |
| `reflection_cycle_daemon` | reflection |
| `runtime_awareness_signal_tracking` | runtime_awareness_signal |
| `runtime_learning_signals` | runtime_learning_signals |
| `runtime_self_knowledge` | runtime_self_knowledge |
| `session_distillation` | private_brain, session, session_distillation |
| `thought_stream_daemon` | thought_stream |
| `tiktok_content_daemon` | tiktok_content_daemon |
| `tiktok_research_daemon` | tiktok_research_daemon |
| `tool_tagger` | tool_tagger |
| `user_model_daemon` | user_model |
| `user_temperature_engine` | cognitive_temperature |
| `weekly_manifest` | weekly_manifest |
| `coding_lane_tools` | coding_lane |
| `compact_llm` | — |

## FRAKOBLET+DARK (50)

| Service | Dark event-families |
|---------|---------------------|
| `agent_relay` | agent |
| `agent_skill_library` | agent_skill |
| `agent_todos` | agent_todos |
| `agentic_tool_cache` | agentic_tool_cache |
| `anthropic_sse_emitter` | anthropic_sse_emitter |
| `anthropic_translator` | anthropic_translator |
| `automation_dsl` | automation_dsl |
| `bounded_mutation_intent_runtime` | bounded_mutation_intent_runtime |
| `bounded_repo_tools_runtime` | bounded_repo_tools_runtime |
| `bro_broker` | bro_broker |
| `cache_maintenance_daemon` | cache_maintenance |
| `chat_sessions` | chat_sessions |
| `composite_tools` | composite |
| `connectors` | connector |
| `context_window_manager` | context_window_manager |
| `daemon_manager` | daemon_manager |
| `daemon_memory_safeguard` | memory_safeguard |
| `experiment_runner` | experiment_runner |
| `forgetting_runtime` | forgetting_runtime |
| `in_flight_runs` | in_flight_runs |
| `living_heartbeat_cycle` | living_heartbeat_cycle |
| `memory_pruning_daemon` | memory_pruning |
| `process_watcher` | process_watcher |
| `recurring_tasks` | recurring_tasks |
| `resonance_decay` | resonance_decay |
| `role_registry` | role_registry |
| `rule_definitions` | rule_definitions |
| `rule_engine` | rule_engine |
| `runtime_flows` | runtime_flows |
| `runtime_hook_runtime` | runtime_hook_runtime |
| `runtime_hooks` | runtime_hooks |
| `runtime_operational_memory` | runtime_operational_memory |
| `selective_consolidation_daemon` | selective_consolidation |
| `semantic_indexer` | semantic_indexer |
| `semantic_memory` | semantic_memory |
| `session_wakeup` | session_wakeup |
| `shared_cache` | shared_cache |
| `shutdown_window_daemon` | shutdown_window |
| `side_tasks` | side_tasks |
| `signal_decay_daemon` | signal_decay |
| `signal_network_visualizer` | signal_network_visualizer |
| `signal_surface_gc` | signal_surface_gc |
| `skill_contract_registry` | skill_contract_registry |
| `skill_engine` | skill_engine |
| `staged_edits` | staged_edits |
| `task_worker` | task_worker |
| `tool_embeddings` | tool_embeddings |
| `tool_intent_runtime` | tool_intent_runtime |
| `tool_result_store` | tool_result_store |
| `voice_daemon` | voice_daemon |

## FRAKOBLET-STILLE (277)

`abuse_monitor`, `active_file_store`, `active_model_state`, `adaptive_learning_runtime`, `adaptive_planner_runtime`, `adaptive_reasoning_runtime`, `affective_meta_state`, `agency_map`, `agent_dispatch`, `agent_outcomes_log`, `anthropic_identity`, `anticipatory_action_daemon`, `app_dispatch_store`, `approval_feedback_subscriber`, `attention_contour`, `auto_code_review`, `auto_remember_subscriber`, `autonomous_outreach_daemon`, `autonomous_work_daemon`, `body_memory`, `boundary_awareness`, `bounded_action_continuity_runtime`, `bounded_workspace_write_runtime`, `bridge_presence`, `claim_scanner`, `cognitive_architecture_surface`, `cognitive_chronicle`, `cognitive_core_experiments`, `cognitive_state_narrativizer`, `collective_pulse_daemon`, `communication_guard_daemon`, `computer_use_policy`, `continuity`, `continuity_kernel`, `cost_optimization_daemon`, `council_runtime`, `cowork_feed`, `creative_impulse_daemon`, `creative_instinct_daemon`, `creative_projects`, `cross_session_threads`, `cross_user_share_guard`, `curiosity_budget`, `daily_journal`, `data_erasure`, `decision_adherence_gate`, `decision_ghosts`, `decision_review_daemon`, `decision_weight`, `deep_analyzer`, `delete_policy`, `desktop_notifications`, `developmental_valence`, `device_pairing`, `device_presence`, `device_tokens`, `dictation`, `discord_config`, `dream_continuum`, `dream_influence_runtime`, `embodied_state`, `emergence`, `emergent_bridge`, `emotion_concepts`, `emotion_concepts_channel_triggers`, `emotional_controls`, `encryption`, `epistemic_runtime_state`, `existential_drift`, `experiential_runtime_context`, `fact_gate`, `fcm_gateway`, `file_watch_daemon`, `gate_adapters`, `gate_auth`, `gate_commit`, `gate_eval`, `gate_kernel`, `gate_loop`, `gate_memory`, `gate_privacy`, `gate_proactivity`, `gate_review`, `gate_truth`, `ghost_networks`, `git_actions`, `github_connector`, `gmail_connector`, `google_connector`, `google_login`, `governance_bootstrap`, `ground_truth_registry`, `guided_learning_runtime`, `hf_connector`, `identity_sketch`, `infra_weather_daemon`, `interlanguage_practice`, `jarvis_brain_reflection`, `jarvis_brain_visibility`, `jobs_engine`, `keyring_store`, `liveness_registry`, `loop_runtime`, `malware_scan`, `markdown_structure`, `mcp_registry`, `memory_breathing`, `memory_density`, `memory_hierarchy`, `memory_search`, `memory_tattoos`, `model_context`, `modulator_witness`, `monitor_streams`, `mood_oscillator`, `mortality_awareness`, `multi_signal_retrieval`, `my_projects`, `notes_connector`, `ntfy_gateway`, `oauth_store`, `ollama_visible_prompt`, `orb_phase`, `override_store`, `parallel_selves`, `pdf_connector`, `periodic_jobs_scheduler`, `permission_engine`, `pfsense_syslog`, `plugin_ruleset`, `plugin_ruleset_store`, `process_supervisor`, `promise_ledger`, `prompt_heartbeat_self_knowledge`, `prompt_mutation_loop`, `proprioception_metrics`, `prose_tool_calls`, `push_dispatcher`, `quota_store`, `relation_dynamics`, `relational_warmth`, `retention`, `role_model_resolver`, `run_follow`, `runtime_action_registry`, `runtime_browser_body`, `runtime_resource_signal`, `runtime_surface_cache`, `runtime_tasks`, `scheduled_job_windows`, `scheduled_task_runner`, `security_guard`, `self_compassion`, `sensory_perception_bridge`, `session_milestones`, `session_topic_tracker`, `shadow_scan_daemon`, `share_guard_store`, `silence_listener`, `skill_scanner`, `skill_security_scanner`, `spaced_repetition`, `spatial_entity_ledger`, `stream_degeneration`, `stream_failure_kind`, `subagent_ecology`, `subjective_time`, `sustained_attention`, `team_mentions`, `teams`, `temporal_body`, `temporal_narrative`, `temporal_rhythm`, `text_clip`, `text_resonance`, `theater_audit`, `theory_of_mind`, `tick_cache`, `tool_catalog`, `tool_chip_payload`, `tool_intent_approval_runtime`, `totp_verifier`, `truth_gate_v2`, `turn_changelog`, `ui_panel_store`, `unconscious_temperature_field`, `unfinished_intent`, `user_scope`, `verification_gate_telemetry`, `visible_inner_life`, `visible_runs_error_messaging`, `visible_runs_sse_v2`, `voice_anchor`, `workspace_crypto`, `workspace_trust`, `agent_todo_tools`, `app_control_tool`, `auto_ensure_tests`, `bash_session`, `browser_tools`, `calendar_tools`, `code_navigation_tools`, `comfyui_tools`, `companion_push_tools`, `composites_tools`, `copilot_tool_pruning`, `counterfactual_tools`, `curiosity_tools`, `daemon_alert_tools`, `decisions_tools`, `file_tools_exec`, `forgetting_tools`, `geolocation_tools`, `github_tools`, `goals_tools`, `health_monitor_tools`, `hf_inference_tools`, `identity_pin_tools`, `identity_sketch_tools`, `jarvis_brain_tools`, `mail_tools`, `math_tools`, `memory_tools`, `meta_learning_tools`, `monitor_tools`, `notification_tools`, `notify_out_tools`, `nudge_broend_tools`, `nudge_tools`, `operator_bash_session`, `operator_tools`, `plan_revise_tool`, `pollinations_tools`, `process_supervisor_tools`, `process_tools`, `process_watcher_tools`, `project_notes_tools`, `reasoning_store_tools`, `recall_memory_tools`, `recurring_scheduler_tools`, `restart_self_tools`, `semantic_search_tools`, `session_search`, `skill_gate_tool`, `smart_compact_tools`, `smart_outline`, `staged_edits_tools`, `stripe_tools`, `team_tools`, `tiktok_analytics_tools`, `tiktok_content_tools`, `tiktok_tools`, `tool_scoping`, `ui_panel_tools`, `verify_tools`, `web_cache`, `web_scrape_tool`, `webhook_tools`, `workspace_capability_decl`, `worktree_tools`, `world_model_tools`, `private_layer_pipeline`, `private_retained_memory_projection`, `email_verify`, `owner_resolver`, `passwords`, `project_context`, `user_attribution_migrations`, `user_db`, `users`, `workspace_bootstrap`, `workspace_context`, `auto_compact`, `compact_ground_truth`, `run_compact`, `session_compact`, `token_estimate`
