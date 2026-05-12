# Capability Matrix

Statisk audit af `core/services/` genereret af `scripts/capability_audit.py`.  
Sidst kørt: 2026-05-12T14:52:10+00:00  
Total services: 506

## Sammenfatning

| Score | Antal | Andel |
|---|---:|---:|
| 🟢 LIVE | 417 | 82.4% |
| 🟡 PARTIAL | 81 | 16.0% |
| 🟠 STALE | 0 | 0.0% |
| 🔴 SUSPICIOUS | 4 | 0.8% |
| ⚫ ORPHAN | 4 | 0.8% |

**Median filstørrelse:** 260 linjer  
**Totale linjer:** 186136  
**Services > 1000 linjer:** 15

## Boy Scout Candidates

Services over 1000 linjer der trænger til at blive skåret ned (prioriteret efter størrelse):

| Fil | Linjer | Score | Sidst rørt |
|---|---:|---|---|
| `core/services/heartbeat_runtime.py` | 8262 | 🟢 LIVE | 0d |
| `core/services/runtime_self_model.py` | 5992 | 🟢 LIVE | 3d |
| `core/services/visible_runs.py` | 5862 | 🟢 LIVE | 0d |
| `core/services/prompt_contract.py` | 4677 | 🟢 LIVE | 0d |
| `core/services/cheap_provider_runtime.py` | 2620 | 🟢 LIVE | 0d |
| `core/services/visible_model.py` | 2513 | 🟢 LIVE | 0d |
| `core/services/agent_runtime.py` | 1791 | 🟢 LIVE | 12d |
| `core/services/runtime_cognitive_conductor.py` | 1385 | 🟢 LIVE | 7d |
| `core/services/cognitive_state_assembly.py` | 1293 | 🟢 LIVE | 3d |
| `core/services/inner_voice_daemon.py` | 1271 | 🟢 LIVE | 1d |
| `core/services/candidate_tracking.py` | 1208 | 🟢 LIVE | 6d |
| `core/services/non_visible_lane_execution.py` | 1187 | 🟢 LIVE | 13d |
| `core/services/prompt_evolution_runtime.py` | 1084 | 🟢 LIVE | 29d |
| `core/services/open_loop_signal_tracking.py` | 1017 | 🟢 LIVE | 2d |
| `core/services/witness_signal_tracking.py` | 1007 | 🟢 LIVE | 25d |

## Kandidater til konsolidering eller fjernelse

Services med score 🔴 SUSPICIOUS eller ⚫ ORPHAN — ejeren skal gennemgå dem manuelt:

| Service | Score | Linjer | Sidst rørt | Imported by | Bemærk |
|---|---|---:|---|---:|---|
| `core/services/contradiction_engine.py` | ⚫ ORPHAN | 209 | 4d | 0 | no reachable path and no importers; no direct test imports |
| `core/services/emergence.py` | ⚫ ORPHAN | 393 | 4d | 0 | no reachable path and no importers; no direct test imports |
| `core/services/jarvis_brain_reflection.py` | 🔴 SUSPICIOUS | 120 | 10d | 1 | not reachable from configured entry points |
| `core/services/prospective_memory.py` | ⚫ ORPHAN | 374 | 4d | 0 | no reachable path and no importers; no direct test imports |
| `core/services/skyoffice_activity.py` | ⚫ ORPHAN | 217 | 15d | 0 | no reachable path and no importers; no direct test imports |
| `core/services/skyoffice_council_viz.py` | 🔴 SUSPICIOUS | 303 | 15d | 2 | not reachable from configured entry points; no direct test imports |
| `core/services/skyoffice_residency.py` | 🔴 SUSPICIOUS | 317 | 15d | 2 | not reachable from configured entry points; no direct test imports |
| `core/services/skyoffice_walk.py` | 🔴 SUSPICIOUS | 185 | 15d | 3 | not reachable from configured entry points; no direct test imports |

## Fuld matrix

| Service | Score | Linjer | Sidst rørt | Reachable | Via | Tests | Testfiler | Imported by | Imports | Emits | Subscribes | Daemon |
|---|---|---:|---|---|---|---:|---|---:|---:|---|---|---|
| `core/services/absence_awareness.py` | 🟢 LIVE | 164 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.runtime_self_model | 1 | test_runtime_self_model.py | 4 | 1 | no | no | no |
| `core/services/absence_daemon.py` | 🟢 LIVE | 186 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_absence_daemon.py | 5 | 3 | yes | no | no |
| `core/services/action_router.py` | 🟢 LIVE | 605 | 1d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 9 | yes | no | no |
| `core/services/adaptive_learning_runtime.py` | 🟢 LIVE | 470 | 7d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_runtime, core.services.heartbeat_runtime | 1 | conftest.py | 7 | 10 | no | no | no |
| `core/services/adaptive_planner_runtime.py` | 🟢 LIVE | 411 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_reasoning_runtime | 1 | conftest.py | 8 | 7 | no | no | no |
| `core/services/adaptive_reasoning_runtime.py` | 🟢 LIVE | 428 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 1 | conftest.py | 9 | 8 | no | no | no |
| `core/services/aesthetic_sense.py` | 🟢 LIVE | 271 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine, core.services.heartbeat_runtime | 1 | test_aesthetic_accumulation.py | 4 | 3 | yes | no | no |
| `core/services/aesthetic_taste_daemon.py` | 🟢 LIVE | 169 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.aesthetic_sense, core.services.daemon_manager | 3 | test_aesthetic_accumulation.py, test_aesthetic_taste_daemon.py, test_heartbeat_trigger_callers.py | 8 | 5 | yes | no | no |
| `core/services/affect_modulation.py` | 🟢 LIVE | 463 | 4d | yes | core.services.agency_map, core.services.modulator_witness, core.services.prompt_contract | 4 | test_affect_tone_hints.py, test_concept_perception_focus.py, test_gates.py | 10 | 5 | yes | no | no |
| `core/services/affective_meta_state.py` | 🟢 LIVE | 598 | 6d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 2 | conftest.py, test_emotion_concepts.py | 21 | 10 | no | no | no |
| `core/services/affective_state_renderer.py` | 🟢 LIVE | 188 | 31d | yes | core.services.prompt_contract | 1 | test_affective_state_renderer_smoke.py | 2 | 7 | no | no | no |
| `core/services/affirmation_anchor.py` | 🟡 PARTIAL | 154 | 13d | yes | core.services.prompt_contract | 0 | — | 1 | 1 | no | no | no |
| `core/services/agency_cartographer.py` | 🟢 LIVE | 481 | 4d | yes | apps.api.jarvis_api.app, core.services.agency_map, core.services.task_worker | 1 | test_mc_tabs_endpoints.py | 4 | 3 | yes | no | no |
| `core/services/agency_map.py` | 🟢 LIVE | 293 | 3d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_mc_tabs_endpoints.py | 2 | 7 | no | no | no |
| `core/services/agent_observation_compressor.py` | 🟢 LIVE | 281 | 15d | yes | core.services.governance_bootstrap, core.tools.simple_tools | 1 | test_agent_observation_compressor.py | 3 | 3 | yes | no | no |
| `core/services/agent_outcomes_log.py` | 🟡 PARTIAL | 126 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.agent_runtime, core.services.prompt_heartbeat_self_knowledge | 0 | — | 4 | 1 | no | no | no |
| `core/services/agent_relay.py` | 🟢 LIVE | 169 | 15d | yes | core.tools.simple_tools | 1 | test_role_registry_and_relay.py | 2 | 2 | yes | no | no |
| `core/services/agent_runtime.py` | 🟢 LIVE | 1791 | 12d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.autonomous_council_daemon | 5 | test_agent_cleanup.py, test_agent_runtime_phase2.py, test_agent_runtime_phase3_scheduler.py | 13 | 12 | yes | no | no |
| `core/services/agent_self_evaluation.py` | 🟢 LIVE | 449 | 5d | yes | core.services.auto_improvement_proposer, core.services.consolidation_judge_daemon, core.services.crisis_marker_detector | 2 | test_agent_self_evaluation.py, test_auto_improvement_and_experiments.py | 13 | 4 | yes | no | no |
| `core/services/agent_skill_distiller.py` | 🟡 PARTIAL | 150 | 15d | yes | core.services.governance_bootstrap, core.services.learning_pipeline_orchestrator | 0 | — | 2 | 3 | no | no | no |
| `core/services/agent_skill_library.py` | 🟢 LIVE | 355 | 15d | yes | core.services.agent_runtime, core.services.agent_skill_distiller, core.services.development_sense | 1 | test_agent_skill_library.py | 5 | 2 | yes | no | no |
| `core/services/agent_todos.py` | 🟢 LIVE | 285 | 0d | yes | apps.api.jarvis_api.routes.jarvisx, core.services.plan_proposals, core.services.prompt_contract | 3 | test_multistep_planner.py, test_plan_revision.py, test_tool_invention.py | 8 | 2 | no | no | no |
| `core/services/agentic_checkpoints.py` | 🟢 LIVE | 172 | 8d | yes | core.services.in_flight_runs, core.services.visible_runs | 1 | test_agentic_checkpoints.py | 3 | 1 | no | no | no |
| `core/services/agentic_tool_cache.py` | 🟡 PARTIAL | 99 | 8d | yes | core.services.visible_runs | 0 | — | 1 | 1 | no | no | no |
| `core/services/agentic_working_conclusions.py` | 🟢 LIVE | 99 | 8d | yes | core.services.in_flight_runs, core.services.visible_runs | 1 | test_agentic_working_conclusions.py | 3 | 1 | no | no | no |
| `core/services/agreement_streak.py` | 🟡 PARTIAL | 141 | 4d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/ambient_presence.py` | 🟢 LIVE | 157 | 22d | yes | core.services.dream_carry_over, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/ambient_sound_daemon.py` | 🟢 LIVE | 474 | 0d | yes | core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_music_accumulator.py | 4 | 6 | yes | no | no |
| `core/services/anthropic_identity.py` | 🟢 LIVE | 63 | 5d | yes | apps.api.jarvis_api.routes.anthropic_compat | 1 | test_anthropic_identity.py | 2 | 0 | no | no | no |
| `core/services/anthropic_sse_emitter.py` | 🟢 LIVE | 140 | 5d | yes | apps.api.jarvis_api.routes.anthropic_compat | 2 | test_anthropic_sse_emitter.py, test_anthropic_translator.py | 3 | 0 | no | no | no |
| `core/services/anthropic_translator.py` | 🟢 LIVE | 235 | 5d | yes | apps.api.jarvis_api.routes.anthropic_compat | 1 | test_anthropic_translator.py | 2 | 0 | no | no | no |
| `core/services/anticipatory_action_daemon.py` | 🟢 LIVE | 247 | 22d | yes | core.services.autonomous_outreach_daemon, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 2 | yes | no | no |
| `core/services/anticipatory_context.py` | 🟢 LIVE | 81 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 1 | yes | no | no |
| `core/services/apophenia_guard.py` | 🟢 LIVE | 118 | 23d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_apophenia_guard_smoke.py | 3 | 1 | no | no | no |
| `core/services/approval_feedback_subscriber.py` | 🟢 LIVE | 95 | 6d | yes | apps.api.jarvis_api.app | 1 | test_approval_feedback_subscriber.py | 2 | 3 | no | no | no |
| `core/services/arc_rule_extractor.py` | 🟢 LIVE | 182 | 15d | yes | core.services.governance_bootstrap, core.services.prompt_contract | 0 | — | 2 | 4 | yes | no | no |
| `core/services/associative_recall.py` | 🟢 LIVE | 291 | 29d | yes | core.services.cognitive_state_assembly | 2 | test_associative_recall.py, test_jarvis_experimental.py | 3 | 4 | no | no | no |
| `core/services/attachment_service.py` | 🟢 LIVE | 315 | 14d | yes | core.services.discord_gateway, core.services.telegram_gateway, core.tools.simple_tools | 2 | test_attachment_service.py, test_tools_attachments.py | 5 | 4 | no | no | no |
| `core/services/attachment_topology_signal_tracking.py` | 🟢 LIVE | 525 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/attention_blink_test.py` | 🟢 LIVE | 153 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 3 | yes | no | no |
| `core/services/attention_budget.py` | 🟢 LIVE | 358 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.prompt_contract | 1 | test_attention_budget.py | 4 | 1 | no | no | no |
| `core/services/attention_contour.py` | 🟢 LIVE | 27 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_attention_contour.py | 3 | 0 | no | no | no |
| `core/services/auto_code_review.py` | 🟡 PARTIAL | 165 | 15d | yes | core.tools.simple_tools | 0 | — | 1 | 0 | no | no | no |
| `core/services/auto_improvement_proposer.py` | 🟢 LIVE | 267 | 15d | yes | core.services.auto_improvement_proposer, core.services.emotion_repair_bridge_daemon, core.services.governance_bootstrap | 2 | test_auto_improvement_and_experiments.py, test_identity_mutation_log.py | 6 | 7 | yes | no | no |
| `core/services/automation_dsl.py` | 🟡 PARTIAL | 253 | 22d | yes | core.services.governance_bootstrap, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 0 | no | no | no |
| `core/services/autonomous_council_daemon.py` | 🟢 LIVE | 296 | 13d | yes | core.services.daemon_manager, core.services.heartbeat_runtime, core.services.signal_surface_router | 1 | test_autonomous_council_daemon.py | 4 | 7 | yes | no | no |
| `core/services/autonomous_goals.py` | 🟢 LIVE | 316 | 15d | yes | core.services.agent_self_evaluation, core.services.consolidation_judge_daemon, core.services.creative_drift_daemon | 4 | test_agent_self_evaluation.py, test_autonomous_goals.py, test_memory_hierarchy.py | 15 | 3 | yes | no | no |
| `core/services/autonomous_outreach_daemon.py` | 🟢 LIVE | 355 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 7 | yes | no | no |
| `core/services/autonomous_work_daemon.py` | 🟢 LIVE | 327 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 4 | yes | no | no |
| `core/services/autonomy_pressure_signal_tracking.py` | 🟢 LIVE | 865 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.heartbeat_runtime | 1 | conftest.py | 12 | 15 | yes | no | no |
| `core/services/autonomy_proposal_queue.py` | 🟢 LIVE | 542 | 31d | yes | apps.api.jarvis_api.routes.mission_control, core.services.agent_runtime, core.tools.simple_tools | 0 | — | 4 | 5 | yes | no | no |
| `core/services/avoidance_detector.py` | 🟡 PARTIAL | 195 | 22d | yes | core.services.autonomous_outreach_daemon, core.services.creative_instinct_daemon, core.services.heartbeat_runtime | 0 | — | 5 | 1 | no | no | no |
| `core/services/behavioral_decisions.py` | 🟢 LIVE | 233 | 5d | yes | core.services.creative_drift_daemon, core.services.decision_enforcement, core.services.decision_gate | 1 | test_behavioral_decisions.py | 9 | 3 | yes | no | no |
| `core/services/body_memory.py` | 🟢 LIVE | 42 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_body_memory.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/boredom_curiosity_bridge.py` | 🟢 LIVE | 171 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.living_heartbeat_cycle | 1 | test_boredom_curiosity_bridge.py | 6 | 1 | no | no | no |
| `core/services/boredom_engine.py` | 🟢 LIVE | 55 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.notification_bridge | 0 | — | 5 | 1 | yes | no | no |
| `core/services/boundary_awareness.py` | 🟢 LIVE | 43 | 35d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_boundary_awareness_smoke.py | 2 | 0 | no | no | no |
| `core/services/bounded_action_continuity_runtime.py` | 🟢 LIVE | 346 | 38d | yes | core.services.tool_intent_runtime | 1 | conftest.py | 2 | 1 | no | no | no |
| `core/services/bounded_mutation_intent_runtime.py` | 🟢 LIVE | 411 | 38d | yes | core.services.tool_intent_runtime | 1 | conftest.py | 2 | 1 | no | no | no |
| `core/services/bounded_repo_tools_runtime.py` | 🟢 LIVE | 407 | 39d | yes | core.services.runtime_action_executor, core.services.tool_intent_runtime | 1 | conftest.py | 3 | 1 | no | no | no |
| `core/services/bounded_workspace_write_runtime.py` | 🟢 LIVE | 196 | 38d | yes | core.services.tool_intent_runtime | 1 | test_bounded_workspace_write_runtime_smoke.py | 2 | 2 | no | no | no |
| `core/services/broadcast_daemon.py` | 🟢 LIVE | 165 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 0 | — | 3 | 4 | yes | no | no |
| `core/services/cadence_producers.py` | 🟢 LIVE | 750 | 9d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_signal_noise_cleanup.py | 5 | 16 | yes | no | no |
| `core/services/calm_anchor.py` | 🟡 PARTIAL | 258 | 16d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 5 | no | no | no |
| `core/services/candidate_tracking.py` | 🟢 LIVE | 1208 | 6d | yes | core.services.heartbeat_runtime, core.services.visible_runs | 1 | conftest.py | 3 | 9 | yes | no | no |
| `core/services/causal_graph.py` | 🟢 LIVE | 176 | 4d | yes | core.services.counterfactual_engine, core.services.narrative_summary_daemon, core.services.prompt_sections.causal_alerts | 1 | test_causal_graph.py | 6 | 1 | no | no | no |
| `core/services/causal_inference_daemon.py` | 🟢 LIVE | 406 | 4d | yes | core.services.daemon_manager | 1 | test_causal_graph.py | 2 | 2 | yes | no | no |
| `core/services/chat_sessions.py` | 🟢 LIVE | 474 | 1d | yes | apps.api.jarvis_api.mcp_server, apps.api.jarvis_api.routes.attachments, apps.api.jarvis_api.routes.chat | 12 | test_channel_context_section.py, test_parse_channel.py, test_context_compact.py | 50 | 6 | no | no | no |
| `core/services/cheap_lane_balancer.py` | 🟢 LIVE | 778 | 9d | yes | apps.api.jarvis_api.routes.cheap_balancer, core.services.agency_map, core.services.daemon_llm | 3 | test_cheap_balancer_routes.py, test_cheap_lane_balancer.py, test_cheap_lane_balancer_e2e.py | 6 | 3 | no | no | no |
| `core/services/cheap_provider_runtime.py` | 🟢 LIVE | 2620 | 0d | yes | core.cli.provider_config, core.context.compact_llm, core.memory.inner_llm_enrichment | 6 | conftest.py, test_tool_tagger.py, test_cheap_lane_balancer.py | 21 | 8 | yes | no | no |
| `core/services/chronicle_consolidation_brief_tracking.py` | 🟢 LIVE | 461 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 9 | 6 | yes | no | no |
| `core/services/chronicle_consolidation_proposal_tracking.py` | 🟢 LIVE | 461 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.visible_runs | 1 | conftest.py | 4 | 6 | yes | no | no |
| `core/services/chronicle_consolidation_signal_tracking.py` | 🟢 LIVE | 537 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 8 | yes | no | no |
| `core/services/chronicle_engine.py` | 🟢 LIVE | 580 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.creative_journal_runtime, core.services.current_pull | 3 | test_chronicle_engine_narrative.py, test_chronicle_engine_prompt_injection.py, test_memory_hierarchy.py | 20 | 15 | yes | no | no |
| `core/services/clarification_classifier.py` | 🟡 PARTIAL | 114 | 15d | yes | core.services.prompt_contract, core.services.reasoning_classifier, core.tools.simple_tools | 0 | — | 3 | 0 | no | no | no |
| `core/services/code_aesthetic_daemon.py` | 🟢 LIVE | 143 | 28d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_code_aesthetic_daemon.py | 5 | 4 | yes | no | no |
| `core/services/cognitive_architecture_surface.py` | 🟢 LIVE | 37 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_self_model | 2 | test_mission_control_operations_route.py, test_runtime_self_model.py | 4 | 2 | no | no | no |
| `core/services/cognitive_core_experiments.py` | 🟢 LIVE | 258 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_architecture_surface, core.services.cognitive_state_assembly | 1 | test_consciousness_experiments.py | 6 | 6 | no | no | no |
| `core/services/cognitive_episodes.py` | 🟢 LIVE | 574 | 6d | yes | core.services.runtime_cognitive_conductor, core.services.visible_runs | 8 | test_cognitive_episodes.py, test_counterfactual_self_simulation.py, test_emotion_concept_triggers.py | 10 | 11 | yes | no | no |
| `core/services/cognitive_state_assembly.py` | 🟢 LIVE | 1293 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.meta_cognition_daemon, core.services.metacognitive_integration | 3 | test_associative_recall.py, test_cognitive_state_cache.py, test_jarvis_experimental.py | 8 | 33 | no | no | no |
| `core/services/cognitive_state_narrativizer.py` | 🟢 LIVE | 207 | 24d | yes | core.services.cognitive_state_assembly, core.services.heartbeat_runtime | 1 | test_cognitive_state_narrativizer_smoke.py | 3 | 1 | no | no | no |
| `core/services/collective_pulse_daemon.py` | 🟢 LIVE | 287 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 3 | yes | no | no |
| `core/services/compass_engine.py` | 🟢 LIVE | 84 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/completion_satisfaction.py` | 🟢 LIVE | 46 | 35d | yes | core.services.runtime_action_outcome_tracking | 1 | test_completion_satisfaction_smoke.py | 2 | 0 | no | no | no |
| `core/services/composite_tools.py` | 🟢 LIVE | 285 | 18d | yes | core.tools.composites_tools | 0 | — | 1 | 3 | yes | no | no |
| `core/services/concept_baseline_tracker.py` | 🟢 LIVE | 313 | 6d | yes | core.services.emotion_concepts, core.services.governance_bootstrap | 2 | test_concept_baseline_tracker.py, test_emotion_concepts_integration.py | 4 | 6 | yes | no | no |
| `core/services/conflict_daemon.py` | 🟢 LIVE | 155 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_conflict_daemon.py | 5 | 3 | yes | no | no |
| `core/services/conflict_prompt_service.py` | 🟡 PARTIAL | 51 | 22d | yes | core.services.prompt_heartbeat_self_knowledge | 0 | — | 1 | 1 | no | no | no |
| `core/services/conflict_resolution.py` | 🟢 LIVE | 578 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 1 | test_conflict_resolution.py | 12 | 1 | no | no | no |
| `core/services/consent_registry.py` | 🟢 LIVE | 147 | 22d | yes | core.services.prompt_heartbeat_self_knowledge, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/consolidation_judge_daemon.py` | 🟢 LIVE | 390 | 6d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 7 | yes | no | no |
| `core/services/consolidation_target_signal_tracking.py` | 🟢 LIVE | 585 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/context_window_manager.py` | 🟢 LIVE | 303 | 15d | yes | core.services.finitude_runtime, core.services.heartbeat_phases, core.services.proactive_context_governor | 4 | test_auto_improvement_and_experiments.py, test_context_window_manager.py, test_identity_mutation_log.py | 9 | 3 | no | no | no |
| `core/services/continuity.py` | 🟡 PARTIAL | 400 | 0d | yes | core.services.prompt_contract, core.services.visible_runs | 0 | — | 2 | 0 | no | no | no |
| `core/services/continuity_kernel.py` | 🟢 LIVE | 148 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_state_renderer, core.services.heartbeat_runtime | 1 | test_continuity_kernel.py | 5 | 0 | no | no | no |
| `core/services/contract_evolution.py` | 🟢 LIVE | 162 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_carry_over, core.services.heartbeat_runtime | 0 | — | 3 | 2 | yes | no | no |
| `core/services/contradiction_engine.py` | ⚫ ORPHAN | 209 | 4d | no | — | 0 | — | 0 | 2 | yes | no | no |
| `core/services/conversation_rhythm.py` | 🟢 LIVE | 83 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.session_distillation | 0 | — | 3 | 2 | yes | no | no |
| `core/services/council_deliberation_controller.py` | 🟢 LIVE | 206 | 30d | yes | core.services.agent_runtime | 1 | test_deliberation_controller.py | 2 | 2 | yes | no | no |
| `core/services/council_memory_daemon.py` | 🟢 LIVE | 122 | 13d | yes | core.services.daemon_manager, core.services.heartbeat_runtime, core.services.signal_surface_router | 2 | test_council_memory_daemon.py, test_daemon_tools.py | 6 | 3 | yes | no | no |
| `core/services/council_memory_service.py` | 🟢 LIVE | 122 | 30d | yes | core.services.agent_runtime, core.services.autonomous_council_daemon, core.services.council_memory_daemon | 2 | test_council_memory_service.py, test_daemon_tools.py | 7 | 1 | no | no | no |
| `core/services/council_runtime.py` | 🟢 LIVE | 375 | 30d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 2 | conftest.py, test_council_conclusion_feedback.py | 9 | 6 | no | no | no |
| `core/services/counterfactual_engine.py` | 🟢 LIVE | 633 | 1d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.chronicle_engine | 3 | test_counterfactual_engine.py, test_counterfactual_engine_runtime.py, test_causal_graph.py | 9 | 5 | yes | no | no |
| `core/services/counterfactual_engine_runtime.py` | 🟢 LIVE | 95 | 5d | yes | apps.api.jarvis_api.app | 1 | test_counterfactual_engine_runtime.py | 3 | 2 | no | no | no |
| `core/services/counterfactual_self_simulation.py` | 🟢 LIVE | 181 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_counterfactual_self_simulation.py | 3 | 3 | yes | no | no |
| `core/services/counterfactual_triggers.py` | 🟢 LIVE | 193 | 1d | yes | core.services.counterfactual_engine | 2 | test_counterfactual_engine.py, test_counterfactual_triggers.py | 3 | 1 | no | no | no |
| `core/services/creative_drift_daemon.py` | 🟢 LIVE | 208 | 14d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_creative_drift_daemon.py | 6 | 7 | yes | no | no |
| `core/services/creative_impulse_daemon.py` | 🟢 LIVE | 340 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 5 | yes | no | no |
| `core/services/creative_instinct_daemon.py` | 🟡 PARTIAL | 352 | 22d | yes | core.services.autonomous_work_daemon, core.services.dream_consolidation_daemon, core.services.heartbeat_runtime | 0 | — | 4 | 3 | no | no | no |
| `core/services/creative_journal_runtime.py` | 🟢 LIVE | 688 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.current_pull, core.services.internal_cadence | 4 | conftest.py, test_aesthetic_klangbraet.py, test_creative_journal_phase1.py | 10 | 13 | yes | no | no |
| `core/services/creative_projects.py` | 🟡 PARTIAL | 206 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 0 | no | no | no |
| `core/services/crisis_marker_detector.py` | 🟢 LIVE | 344 | 9d | yes | core.services.creative_drift_daemon, core.services.development_sense, core.services.governance_bootstrap | 0 | — | 10 | 5 | yes | no | no |
| `core/services/cross_agent_memory.py` | 🟢 LIVE | 186 | 15d | yes | core.services.agent_runtime, core.tools.simple_tools | 1 | test_cross_agent_memory.py | 3 | 1 | no | no | no |
| `core/services/cross_session_threads.py` | 🟡 PARTIAL | 217 | 22d | yes | core.services.autonomous_outreach_daemon, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 4 | 0 | no | no | no |
| `core/services/cross_signal_analysis.py` | 🟢 LIVE | 90 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/curiosity_budget.py` | 🟢 LIVE | 256 | 0d | yes | core.services.internal_cadence, core.services.prompt_contract, core.tools.curiosity_tools | 2 | test_curiosity_budget.py, test_meta_learning.py | 6 | 4 | yes | no | no |
| `core/services/curiosity_daemon.py` | 🟢 LIVE | 157 | 15d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.goal_signal_synthesizer | 2 | test_curiosity_daemon.py, test_daemon_manager.py | 10 | 4 | yes | no | no |
| `core/services/curiosity_hypothesis_debt.py` | 🟢 LIVE | 97 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_curiosity_hypothesis_debt.py | 3 | 2 | yes | no | no |
| `core/services/current_pull.py` | 🟢 LIVE | 458 | 0d | yes | core.services.creative_journal_runtime, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_current_pull_staleness.py | 6 | 10 | yes | no | no |
| `core/services/daemon_llm.py` | 🟢 LIVE | 325 | 5d | yes | apps.api.jarvis_api.routes.skyoffice, core.services.absence_daemon, core.services.aesthetic_taste_daemon | 12 | test_absence_daemon.py, test_agent_observation_compressor.py, test_autonomous_goals.py | 64 | 7 | no | no | no |
| `core/services/daemon_manager.py` | 🟢 LIVE | 469 | 0d | yes | apps.api.jarvis_api.routes.status, core.services.autonomous_council_daemon, core.services.heartbeat_runtime | 3 | test_daemon_manager.py, test_daemon_tools.py, test_self_repair_engine.py | 11 | 42 | no | no | no |
| `core/services/daemon_memory_safeguard.py` | 🟢 LIVE | 99 | 5d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/day_shape_memory.py` | 🟡 PARTIAL | 299 | 22d | yes | core.services.collective_pulse_daemon, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 3 | no | no | no |
| `core/services/decision_adherence_gate.py` | 🟡 PARTIAL | 88 | 5d | yes | core.services.prompt_contract | 0 | — | 1 | 1 | no | no | no |
| `core/services/decision_enforcement.py` | 🟢 LIVE | 260 | 5d | yes | core.services.governance_bootstrap, core.services.prompt_contract | 1 | test_decision_signals_in_prompt.py | 3 | 5 | yes | no | no |
| `core/services/decision_gate.py` | 🟢 LIVE | 144 | 8d | yes | core.services.visible_runs | 1 | test_gates.py | 2 | 2 | yes | no | no |
| `core/services/decision_ghosts.py` | 🟢 LIVE | 124 | 1d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.inner_voice_daemon | 2 | test_decision_ghosts.py, test_prompt_contract_capability_rules.py | 5 | 0 | no | no | no |
| `core/services/decision_log.py` | 🟢 LIVE | 60 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.heartbeat_runtime | 0 | — | 3 | 2 | yes | no | no |
| `core/services/decision_review_prompter.py` | 🟡 PARTIAL | 150 | 5d | yes | core.services.governance_bootstrap | 0 | — | 1 | 2 | no | no | no |
| `core/services/decision_signals.py` | 🟢 LIVE | 307 | 5d | yes | core.services.visible_runs | 3 | test_decision_signals_in_prompt.py, test_decision_signals.py, test_decision_triggers.py | 7 | 3 | yes | no | no |
| `core/services/decision_weight.py` | 🟢 LIVE | 79 | 30d | yes | core.services.runtime_action_executor | 1 | test_decision_weight.py | 2 | 0 | no | no | no |
| `core/services/decisions_journal.py` | 🟢 LIVE | 211 | 20d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 3 | yes | no | no |
| `core/services/deep_analyzer.py` | 🟡 PARTIAL | 355 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.tools.simple_tools | 0 | — | 2 | 0 | no | no | no |
| `core/services/deep_reflection_slot.py` | 🟢 LIVE | 410 | 21d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 10 | yes | no | no |
| `core/services/delegation_advisor.py` | 🟡 PARTIAL | 138 | 15d | yes | core.services.reasoning_classifier, core.tools.simple_tools | 0 | — | 2 | 0 | no | no | no |
| `core/services/desire_daemon.py` | 🟢 LIVE | 208 | 15d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.current_pull, core.services.daemon_manager | 2 | test_current_pull_staleness.py, test_desire_daemon.py | 8 | 5 | yes | no | no |
| `core/services/desperation_awareness.py` | 🟢 LIVE | 226 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 4 | yes | no | no |
| `core/services/development_focus_tracking.py` | 🟢 LIVE | 541 | 15d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.emergent_signal_tracking | 1 | test_signal_noise_cleanup.py | 8 | 4 | yes | no | no |
| `core/services/development_narrative_daemon.py` | 🟢 LIVE | 108 | 28d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_development_narrative_daemon.py | 5 | 5 | yes | no | no |
| `core/services/development_sense.py` | 🟡 PARTIAL | 322 | 8d | yes | core.services.prompt_contract | 0 | — | 1 | 7 | no | no | no |
| `core/services/developmental_valence.py` | 🟡 PARTIAL | 311 | 22d | yes | core.services.deep_reflection_slot, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 2 | no | no | no |
| `core/services/diary_synthesis_signal_tracking.py` | 🟢 LIVE | 583 | 42d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.runtime_cognitive_conductor | 2 | conftest.py, test_diary_synthesis_signal_tracking.py | 9 | 2 | yes | no | no |
| `core/services/discord_config.py` | 🟢 LIVE | 38 | 31d | yes | apps.api.jarvis_api.routes.jarvisx, apps.api.jarvis_api.routes.mission_control, core.identity.owner_resolver | 1 | test_discord_config_smoke.py | 9 | 1 | no | no | no |
| `core/services/discord_gateway.py` | 🟢 LIVE | 854 | 8d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.internal_discord, core.services.autonomy_proposal_queue | 2 | test_discord_gateway_attachments.py, test_tools_attachments.py | 12 | 8 | yes | no | no |
| `core/services/dream_adoption_candidate_tracking.py` | 🟢 LIVE | 462 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_proposal_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 6 | yes | no | no |
| `core/services/dream_articulation.py` | 🟢 LIVE | 571 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.affective_meta_state | 2 | conftest.py, test_initiative_feedback.py | 13 | 11 | yes | no | no |
| `core/services/dream_bias_engine.py` | 🟢 LIVE | 599 | 1d | yes | core.services.creative_journal_runtime, core.services.dream_distillation_daemon, core.services.modulator_witness | 2 | test_dream_bias_engine.py, test_modulator_witness.py | 11 | 5 | yes | no | no |
| `core/services/dream_carry_over.py` | 🟢 LIVE | 296 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.dream_continuum | 1 | test_dream_continuum.py | 7 | 4 | yes | no | no |
| `core/services/dream_consolidation_daemon.py` | 🟢 LIVE | 356 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 3 | yes | no | no |
| `core/services/dream_continuum.py` | 🟢 LIVE | 184 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_dream_continuum.py | 5 | 1 | no | no | no |
| `core/services/dream_distillation_daemon.py` | 🟢 LIVE | 380 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.current_pull, core.services.goal_signal_synthesizer | 1 | conftest.py | 7 | 8 | yes | no | no |
| `core/services/dream_hypothesis_forced.py` | 🟢 LIVE | 74 | 29d | yes | core.services.heartbeat_runtime | 1 | test_jarvis_experimental.py | 2 | 1 | no | no | no |
| `core/services/dream_hypothesis_generator.py` | 🟢 LIVE | 402 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine | 0 | — | 2 | 3 | yes | no | no |
| `core/services/dream_hypothesis_signal_tracking.py` | 🟢 LIVE | 445 | 25d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_adoption_candidate_tracking, core.services.dream_influence_proposal_tracking | 1 | conftest.py | 10 | 7 | yes | no | no |
| `core/services/dream_influence_proposal_tracking.py` | 🟢 LIVE | 508 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.self_authored_prompt_proposal_tracking | 1 | conftest.py | 6 | 7 | yes | no | no |
| `core/services/dream_influence_runtime.py` | 🟢 LIVE | 445 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_evolution_runtime | 1 | conftest.py | 6 | 8 | no | no | no |
| `core/services/dream_insight_daemon.py` | 🟢 LIVE | 94 | 29d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.autonomous_outreach_daemon, core.services.daemon_manager | 1 | test_dream_insight_daemon.py | 6 | 2 | yes | no | no |
| `core/services/dream_motif_daemon.py` | 🟡 PARTIAL | 211 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.heartbeat_runtime | 0 | — | 2 | 3 | no | no | no |
| `core/services/drive_arbitration_engine.py` | 🟢 LIVE | 96 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_drive_arbitration_engine.py | 3 | 2 | yes | no | no |
| `core/services/embodied_presence.py` | 🟡 PARTIAL | 247 | 12d | yes | core.services.cognitive_state_assembly | 0 | — | 1 | 0 | no | no | no |
| `core/services/embodied_state.py` | 🟢 LIVE | 382 | 24d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 1 | conftest.py | 15 | 1 | no | no | no |
| `core/services/emergence.py` | ⚫ ORPHAN | 393 | 4d | no | — | 0 | — | 0 | 3 | yes | no | no |
| `core/services/emergent_bridge.py` | 🟢 LIVE | 114 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_emergent_bridge.py | 3 | 1 | no | no | no |
| `core/services/emergent_goals.py` | 🟢 LIVE | 69 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/emergent_signal_tracking.py` | 🟢 LIVE | 442 | 41d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.dream_articulation | 1 | conftest.py | 13 | 7 | yes | no | no |
| `core/services/emotion_concepts.py` | 🟢 LIVE | 538 | 6d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.affect_modulation | 8 | test_affect_tone_hints.py, test_affective_meta_state.py, test_associative_recall.py | 26 | 5 | no | no | no |
| `core/services/emotion_concepts_channel_triggers.py` | 🟢 LIVE | 57 | 6d | yes | core.services.chat_sessions | 1 | test_emotion_concept_triggers.py | 2 | 1 | no | no | no |
| `core/services/emotion_concepts_positive_triggers.py` | 🟢 LIVE | 107 | 6d | yes | core.services.emotion_concepts, core.services.sensory_archive | 1 | test_emotion_concept_triggers.py | 3 | 1 | no | no | no |
| `core/services/emotion_repair_bridge_daemon.py` | 🟢 LIVE | 410 | 0d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 8 | yes | no | no |
| `core/services/emotion_tagging.py` | 🟢 LIVE | 88 | 15d | yes | core.tools.simple_tools | 1 | test_emotion_and_drift.py | 2 | 2 | no | no | no |
| `core/services/emotional_chords.py` | 🟡 PARTIAL | 309 | 13d | yes | core.services.cognitive_state_assembly, core.services.epistemic_pragmatic, core.services.resonance_decay | 0 | — | 4 | 2 | no | no | no |
| `core/services/emotional_controls.py` | 🟢 LIVE | 289 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affect_modulation, core.services.pushback | 2 | test_gates.py, test_pushback.py | 7 | 3 | no | no | no |
| `core/services/emotional_memory_engine.py` | 🟢 LIVE | 605 | 7d | yes | core.services.cognitive_episodes, core.services.emotion_repair_bridge_daemon, core.services.memory_emotional_context | 5 | test_emotional_memory_engine.py, test_emotional_memory_integration.py, test_memory_emotional_context_shim.py | 11 | 5 | yes | no | no |
| `core/services/end_of_run_memory_consolidation.py` | 🟢 LIVE | 513 | 25d | yes | core.services.visible_runs | 3 | test_end_of_run_memory_consolidation.py, test_memory_consolidation_fallback.py, test_visible_memory_postprocess.py | 4 | 5 | yes | no | no |
| `core/services/epistemic_pragmatic.py` | 🟡 PARTIAL | 264 | 13d | yes | core.services.cognitive_state_assembly, core.services.selective_attention | 0 | — | 2 | 4 | no | no | no |
| `core/services/epistemic_runtime_state.py` | 🟢 LIVE | 374 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 1 | conftest.py | 13 | 7 | no | no | no |
| `core/services/epistemics.py` | 🟢 LIVE | 415 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 0 | — | 2 | 2 | yes | no | no |
| `core/services/executive_contradiction_signal_tracking.py` | 🟢 LIVE | 520 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/existential_drift.py` | 🟢 LIVE | 67 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_existential_drift.py | 3 | 0 | no | no | no |
| `core/services/existential_wonder_daemon.py` | 🟢 LIVE | 145 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_existential_wonder_daemon.py | 5 | 4 | yes | no | no |
| `core/services/experience_correction_listener.py` | 🟡 PARTIAL | 217 | 2d | yes | apps.api.jarvis_api.app | 0 | — | 1 | 3 | no | no | no |
| `core/services/experience_episodes.py` | 🟡 PARTIAL | 375 | 2d | yes | core.services.experience_correction_listener, core.services.prompt_contract, core.services.visible_runs | 0 | — | 3 | 2 | no | no | no |
| `core/services/experience_substrate.py` | 🟢 LIVE | 313 | 2d | yes | core.services.current_pull | 1 | test_current_pull_staleness.py | 2 | 2 | no | no | no |
| `core/services/experienced_time_daemon.py` | 🟢 LIVE | 121 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_experienced_time_daemon.py | 5 | 1 | no | no | no |
| `core/services/experiential_memory.py` | 🟢 LIVE | 457 | 13d | yes | apps.api.jarvis_api.routes.mission_control, core.services.associative_recall, core.services.heartbeat_runtime | 1 | test_associative_recall.py | 8 | 5 | yes | no | no |
| `core/services/experiential_runtime_context.py` | 🟢 LIVE | 717 | 37d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.inner_voice_daemon | 1 | conftest.py | 6 | 6 | no | no | no |
| `core/services/experiment_runner.py` | 🟢 LIVE | 253 | 15d | yes | core.tools.simple_tools | 1 | test_auto_improvement_and_experiments.py | 2 | 3 | no | no | no |
| `core/services/file_watch_daemon.py` | 🟢 LIVE | 227 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 1 | yes | no | no |
| `core/services/finitude_runtime.py` | 🟢 LIVE | 826 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.runtime.settings, core.services.creative_journal_runtime | 2 | conftest.py, test_finitude_phase1.py | 8 | 6 | yes | no | no |
| `core/services/flow_state_detection.py` | 🟢 LIVE | 40 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.calm_anchor, core.services.cognitive_state_assembly | 0 | — | 6 | 1 | yes | no | no |
| `core/services/forgetting_curve.py` | 🟢 LIVE | 108 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 1 | yes | no | no |
| `core/services/forgetting_engine.py` | 🟢 LIVE | 422 | 2d | yes | core.services.forgetting_runtime, core.services.prompt_contract, core.tools.forgetting_tools | 3 | test_forgetting_engine.py, test_forgetting_runtime.py, test_release_memory.py | 6 | 4 | yes | no | no |
| `core/services/forgetting_runtime.py` | 🟢 LIVE | 103 | 2d | yes | apps.api.jarvis_api.app | 1 | test_forgetting_runtime.py | 3 | 3 | no | no | no |
| `core/services/ghost_networks.py` | 🟢 LIVE | 39 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_ghost_networks.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/global_workspace.py` | 🟢 LIVE | 144 | 29d | yes | apps.api.jarvis_api.app, core.services.broadcast_daemon | 1 | test_consciousness_experiments.py | 3 | 1 | no | no | no |
| `core/services/goal_signal_synthesizer.py` | 🟢 LIVE | 117 | 15d | yes | core.services.governance_bootstrap | 0 | — | 1 | 6 | yes | no | no |
| `core/services/goal_signal_tracking.py` | 🟢 LIVE | 510 | 25d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.session_distillation | 0 | — | 6 | 3 | yes | no | no |
| `core/services/good_enough_gate.py` | 🟡 PARTIAL | 184 | 15d | yes | core.tools.simple_tools | 0 | — | 1 | 1 | no | no | no |
| `core/services/governance_bootstrap.py` | 🟡 PARTIAL | 399 | 6d | yes | apps.api.jarvis_api.app, core.identity.user_attribution_migrations | 0 | — | 2 | 23 | no | no | no |
| `core/services/gratitude_tracker.py` | 🟢 LIVE | 59 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/guided_learning_runtime.py` | 🟢 LIVE | 502 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 1 | conftest.py | 8 | 8 | no | no | no |
| `core/services/gut_engine.py` | 🟢 LIVE | 91 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/habit_tracker.py` | 🟢 LIVE | 88 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/habits_pipeline.py` | 🟢 LIVE | 385 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/hardware_body.py` | 🟢 LIVE | 202 | 24d | yes | apps.api.jarvis_api.routes.system_health, core.services.affective_state_renderer, core.services.calm_anchor | 2 | test_hardware_body_smoke.py, test_somatic_daemon.py | 12 | 1 | no | no | no |
| `core/services/heartbeat_phases.py` | 🟢 LIVE | 429 | 0d | yes | core.services.memory_hierarchy, core.services.wakeup_dispatcher, core.tools.simple_tools | 3 | test_heartbeat_phases.py, test_memory_hierarchy.py, test_wakeup_dispatcher.py | 6 | 17 | yes | no | no |
| `core/services/heartbeat_provider_fallback.py` | 🟡 PARTIAL | 161 | 4d | yes | core.services.heartbeat_runtime | 0 | — | 1 | 2 | no | no | no |
| `core/services/heartbeat_runtime.py` | 🟢 LIVE | 8262 | 0d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.context.compact_llm | 9 | conftest.py, test_conflict_resolution.py, test_daemon_llm_cache.py | 24 | 205 | yes | no | no |
| `core/services/identity_composer.py` | 🟢 LIVE | 119 | 4d | yes | core.services.aesthetic_taste_daemon, core.services.code_aesthetic_daemon, core.services.consolidation_judge_daemon | 1 | test_identity_composer.py | 16 | 5 | no | no | no |
| `core/services/identity_drift_daemon.py` | 🟢 LIVE | 321 | 4d | yes | core.services.daemon_manager | 0 | — | 1 | 5 | yes | no | no |
| `core/services/identity_drift_proposer.py` | 🟢 LIVE | 194 | 15d | yes | core.services.concept_baseline_tracker, core.services.governance_bootstrap, core.tools.simple_tools | 0 | — | 3 | 3 | yes | no | no |
| `core/services/identity_mutation_log.py` | 🟢 LIVE | 316 | 15d | yes | core.services.auto_improvement_proposer, core.services.identity_drift_daemon, core.services.identity_mutation_log | 2 | test_auto_improvement_and_experiments.py, test_identity_mutation_log.py | 5 | 6 | yes | no | no |
| `core/services/idle_consolidation.py` | 🟢 LIVE | 522 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.affective_meta_state | 1 | conftest.py | 8 | 8 | yes | no | no |
| `core/services/idle_thinking.py` | 🟢 LIVE | 87 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 4 | yes | no | no |
| `core/services/impulse_executor.py` | 🟢 LIVE | 400 | 13d | yes | core.services.action_router | 0 | — | 1 | 4 | yes | no | no |
| `core/services/in_flight_runs.py` | 🟢 LIVE | 240 | 8d | yes | core.services.prompt_contract, core.services.visible_runs | 1 | test_in_flight_runs.py | 3 | 3 | no | no | no |
| `core/services/infra_weather_daemon.py` | 🟢 LIVE | 290 | 14d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 1 | test_infra_weather_daemon.py | 3 | 4 | yes | no | no |
| `core/services/inheritance_seed.py` | 🟡 PARTIAL | 142 | 23d | yes | apps.api.jarvis_api.app | 0 | — | 1 | 6 | no | no | no |
| `core/services/initiative_accumulator.py` | 🟢 LIVE | 182 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_initiative_accumulator.py | 5 | 1 | no | no | no |
| `core/services/initiative_queue.py` | 🟢 LIVE | 507 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.action_router, core.services.autonomous_work_daemon | 3 | test_heartbeat_execute_actions.py, test_initiative_feedback.py, test_life_projects.py | 20 | 4 | yes | no | no |
| `core/services/inner_dialectic_engine.py` | 🟢 LIVE | 87 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_inner_dialectic_engine.py | 3 | 2 | yes | no | no |
| `core/services/inner_visible_support_signal_tracking.py` | 🟢 LIVE | 629 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract, core.services.signal_surface_router | 1 | conftest.py | 5 | 2 | yes | no | no |
| `core/services/inner_voice_daemon.py` | 🟢 LIVE | 1271 | 1d | yes | apps.api.jarvis_api.routes.mission_control, core.memory.inner_llm_enrichment, core.services.affective_meta_state | 2 | test_inner_voice_approval_reaction.py, test_inner_voice_daemon.py | 13 | 16 | yes | no | no |
| `core/services/inner_voice_notifier.py` | 🟢 LIVE | 266 | 18d | yes | apps.api.jarvis_api.app | 0 | — | 1 | 4 | yes | no | no |
| `core/services/internal_cadence.py` | 🟢 LIVE | 644 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_model | 4 | conftest.py, test_curiosity_budget.py, test_internal_cadence.py | 7 | 20 | yes | no | no |
| `core/services/internal_opposition_signal_tracking.py` | 🟢 LIVE | 446 | 47d | yes | apps.api.jarvis_api.routes.mission_control, core.services.self_review_outcome_tracking, core.services.self_review_record_tracking | 1 | conftest.py | 8 | 3 | yes | no | no |
| `core/services/irony_daemon.py` | 🟢 LIVE | 149 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_irony_daemon.py | 5 | 4 | yes | no | no |
| `core/services/jarvis_brain.py` | 🟢 LIVE | 751 | 4d | yes | core.services.jarvis_brain_daemon, core.services.living_executive, core.services.memory_pruning_daemon | 6 | test_jarvis_brain.py, test_jarvis_brain_daemon.py, test_jarvis_brain_integration.py | 12 | 1 | no | no | no |
| `core/services/jarvis_brain_daemon.py` | 🟢 LIVE | 559 | 10d | yes | apps.api.jarvis_api.app | 2 | test_jarvis_brain_daemon.py, test_jarvis_brain_integration.py | 3 | 7 | no | no | no |
| `core/services/jarvis_brain_reflection.py` | 🔴 SUSPICIOUS | 120 | 10d | no | — | 1 | test_jarvis_brain_reflection.py | 1 | 3 | no | no | no |
| `core/services/jarvis_brain_visibility.py` | 🟢 LIVE | 63 | 10d | yes | core.services.jarvis_brain_daemon | 1 | test_jarvis_brain_visibility.py | 2 | 1 | no | no | no |
| `core/services/jobs_engine.py` | 🟢 LIVE | 328 | 8d | yes | apps.api.jarvis_api.app, core.services.governance_bootstrap, core.services.heartbeat_runtime | 1 | test_periodic_jobs_scheduler.py | 6 | 0 | no | no | no |
| `core/services/layer_tension_daemon.py` | 🟢 LIVE | 201 | 23d | yes | apps.api.jarvis_api.routes.mission_control, apps.api.jarvis_api.routes.mission_control_living_mind, core.services.calm_anchor | 0 | — | 6 | 2 | yes | no | no |
| `core/services/learning_pipeline_orchestrator.py` | 🟢 LIVE | 426 | 0d | yes | core.services.heartbeat_phases | 0 | — | 1 | 6 | yes | no | no |
| `core/services/learning_policy_engine.py` | 🟢 LIVE | 243 | 7d | yes | core.services.adaptive_learning_runtime, core.services.cognitive_episodes, core.services.cognitive_state_assembly | 4 | test_counterfactual_self_simulation.py, test_learning_policy_engine.py, test_offline_recomposition_engine.py | 13 | 2 | yes | no | no |
| `core/services/life_milestones.py` | 🟡 PARTIAL | 91 | 22d | yes | core.services.prompt_contract | 0 | — | 1 | 1 | no | no | no |
| `core/services/life_projects.py` | 🟢 LIVE | 117 | 23d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.internal_cadence | 1 | test_life_projects.py | 4 | 3 | yes | no | no |
| `core/services/living_executive.py` | 🟢 LIVE | 681 | 6d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control | 2 | test_living_executive.py, test_mc_tabs_endpoints.py | 4 | 7 | yes | no | no |
| `core/services/living_heartbeat_cycle.py` | 🟢 LIVE | 191 | 1d | yes | apps.api.jarvis_api.routes.mission_control, core.services.boredom_curiosity_bridge, core.services.cadence_producers | 2 | test_living_heartbeat_cycle_smoke.py, test_signal_noise_cleanup.py | 11 | 2 | no | no | no |
| `core/services/long_arc_synthesizer.py` | 🟢 LIVE | 264 | 15d | yes | core.services.governance_bootstrap, core.tools.simple_tools | 0 | — | 3 | 6 | yes | no | no |
| `core/services/long_horizon_goals.py` | 🟢 LIVE | 184 | 18d | yes | core.services.prompt_contract, core.tools.goals_tools | 0 | — | 2 | 2 | yes | no | no |
| `core/services/longing_signal_daemon.py` | 🟡 PARTIAL | 252 | 13d | yes | core.services.action_router, core.services.daemon_manager | 0 | — | 2 | 2 | no | no | no |
| `core/services/loop_runtime.py` | 🟢 LIVE | 297 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 1 | conftest.py | 17 | 4 | no | no | no |
| `core/services/loyalty_gradient_signal_tracking.py` | 🟢 LIVE | 592 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/mail_checker_daemon.py` | 🟢 LIVE | 376 | 20d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 6 | yes | no | no |
| `core/services/meaning_significance_signal_tracking.py` | 🟢 LIVE | 628 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/memory_breathing.py` | 🟡 PARTIAL | 132 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model, core.services.thought_thread | 0 | — | 3 | 1 | no | no | no |
| `core/services/memory_consolidation_nudge.py` | 🟡 PARTIAL | 19 | 5d | yes | core.services.prompt_contract | 0 | — | 1 | 0 | no | no | no |
| `core/services/memory_decay_daemon.py` | 🟢 LIVE | 148 | 28d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.governance_bootstrap | 2 | test_adaptive_decay.py, test_memory_decay_daemon.py | 7 | 2 | yes | no | no |
| `core/services/memory_density.py` | 🟢 LIVE | 262 | 21d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model, core.tools.mic_listen_tool | 0 | — | 4 | 1 | yes | no | no |
| `core/services/memory_emotional_context.py` | 🟢 LIVE | 120 | 7d | yes | core.services.memory_resurfacing, core.tools.memory_tools | 1 | test_memory_emotional_context_shim.py | 3 | 2 | no | no | no |
| `core/services/memory_graph.py` | 🟡 PARTIAL | 337 | 13d | yes | core.tools.memory_tools, core.tools.simple_tools | 0 | — | 2 | 3 | no | no | no |
| `core/services/memory_hierarchy.py` | 🟢 LIVE | 243 | 15d | yes | core.services.heartbeat_phases, core.services.prompt_contract, core.tools.simple_tools | 1 | test_memory_hierarchy.py | 4 | 5 | no | no | no |
| `core/services/memory_maintenance_daemon.py` | 🟢 LIVE | 304 | 13d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/memory_md_update_proposal_tracking.py` | 🟢 LIVE | 482 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/memory_pruning_daemon.py` | 🟢 LIVE | 211 | 4d | yes | core.services.daemon_manager | 0 | — | 1 | 3 | yes | no | no |
| `core/services/memory_recall_engine.py` | 🟢 LIVE | 262 | 15d | yes | core.services.memory_hierarchy, core.services.proactive_context_governor, core.tools.simple_tools | 3 | test_memory_hierarchy.py, test_memory_recall_engine.py, test_proactive_context_governor.py | 6 | 4 | no | no | no |
| `core/services/memory_resurfacing.py` | 🟡 PARTIAL | 214 | 7d | yes | core.tools.simple_tools | 0 | — | 1 | 3 | no | no | no |
| `core/services/memory_search.py` | 🟢 LIVE | 277 | 32d | yes | core.services.heartbeat_phases, core.services.memory_hierarchy, core.services.memory_recall_engine | 2 | test_memory_search_smoke.py, test_memory_hierarchy.py | 6 | 1 | no | no | no |
| `core/services/memory_tattoos.py` | 🟢 LIVE | 42 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_memory_tattoos.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/memory_write_policy.py` | 🟡 PARTIAL | 239 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 0 | no | no | no |
| `core/services/meta_cognition_daemon.py` | 🟢 LIVE | 209 | 13d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 6 | yes | no | no |
| `core/services/meta_learning_aggregator.py` | 🟢 LIVE | 413 | 0d | yes | core.services.meta_learning_retrospective | 1 | test_meta_learning.py | 3 | 3 | no | no | no |
| `core/services/meta_learning_retrospective.py` | 🟢 LIVE | 437 | 0d | yes | core.services.internal_cadence, core.services.prompt_contract, core.tools.meta_learning_tools | 1 | test_meta_learning.py | 5 | 5 | yes | no | no |
| `core/services/meta_reflection_daemon.py` | 🟢 LIVE | 127 | 28d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_meta_reflection_daemon.py | 5 | 4 | yes | no | no |
| `core/services/metabolism_state_signal_tracking.py` | 🟢 LIVE | 542 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_meta_state, core.services.autonomy_pressure_signal_tracking | 1 | conftest.py | 10 | 2 | yes | no | no |
| `core/services/metacognitive_integration.py` | 🟡 PARTIAL | 491 | 12d | yes | core.services.cognitive_state_assembly | 0 | — | 1 | 2 | no | no | no |
| `core/services/mirror_engine.py` | 🟢 LIVE | 99 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 3 | 1 | yes | no | no |
| `core/services/missions_pipeline.py` | 🟢 LIVE | 364 | 20d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 2 | yes | no | no |
| `core/services/modulator_witness.py` | 🟢 LIVE | 199 | 0d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_modulator_witness.py | 2 | 4 | no | no | no |
| `core/services/monitor_streams.py` | 🟡 PARTIAL | 227 | 15d | yes | core.services.prompt_contract, core.tools.monitor_tools | 0 | — | 2 | 2 | no | no | no |
| `core/services/mood_dialer.py` | 🟡 PARTIAL | 181 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.initiative_queue | 0 | — | 2 | 1 | no | no | no |
| `core/services/mood_oscillator.py` | 🟢 LIVE | 267 | 20d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.action_router | 2 | test_emotion_and_drift.py, test_mood_oscillator.py | 26 | 2 | no | no | no |
| `core/services/mortality_awareness.py` | 🟡 PARTIAL | 164 | 22d | yes | core.services.deep_reflection_slot, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 2 | no | no | no |
| `core/services/narrative_identity.py` | 🟢 LIVE | 93 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/narrative_summary_daemon.py` | 🟢 LIVE | 226 | 4d | yes | core.services.daemon_manager | 1 | test_narrative_summary_daemon.py | 2 | 5 | yes | no | no |
| `core/services/negotiation_engine.py` | 🟢 LIVE | 68 | 35d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/negotiation_pipeline.py` | 🟢 LIVE | 241 | 20d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 2 | yes | no | no |
| `core/services/non_visible_lane_execution.py` | 🟢 LIVE | 1187 | 13d | yes | apps.api.jarvis_api.routes.mission_control, core.cli.copilot_auth, core.cli.provider_config | 4 | conftest.py, test_daemon_llm_cache.py, test_execute_with_role_fallback.py | 20 | 8 | yes | no | no |
| `core/services/notification_bridge.py` | 🟢 LIVE | 187 | 27d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.chat, core.identity.owner_resolver | 1 | test_wakeup_dispatcher.py | 11 | 4 | yes | no | no |
| `core/services/ntfy_gateway.py` | 🟡 PARTIAL | 66 | 22d | yes | core.services.action_router, core.services.ambient_presence, core.services.autonomous_outreach_daemon | 0 | — | 8 | 0 | no | no | no |
| `core/services/nudge_broend.py` | 🟡 PARTIAL | 153 | 2d | yes | core.services.action_router, core.tools.nudge_broend_tools | 0 | — | 2 | 0 | no | no | no |
| `core/services/offline_recomposition_engine.py` | 🟢 LIVE | 120 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_offline_recomposition_engine.py | 3 | 3 | yes | no | no |
| `core/services/ollama_visible_prompt.py` | 🟢 LIVE | 94 | 33d | yes | core.services.visible_model, core.services.visible_runs | 2 | test_ollama_visible_prompt_smoke.py, test_visible_runs_capability_smoke.py | 4 | 0 | no | no | no |
| `core/services/open_loop_closure_proposal_tracking.py` | 🟢 LIVE | 445 | 42d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 6 | 7 | yes | no | no |
| `core/services/open_loop_signal_tracking.py` | 🟢 LIVE | 1017 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.emergent_signal_tracking | 2 | conftest.py, test_open_loop_signal_tracking.py | 24 | 8 | yes | no | no |
| `core/services/orb_phase.py` | 🟢 LIVE | 22 | 27d | yes | core.services.visible_runs | 1 | test_orb_phase_smoke.py | 2 | 0 | no | no | no |
| `core/services/outcome_learning.py` | 🟡 PARTIAL | 221 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model, core.tools.simple_tools | 0 | — | 3 | 0 | no | no | no |
| `core/services/outreach_composer.py` | 🟢 LIVE | 370 | 1d | yes | core.services.impulse_executor | 0 | — | 1 | 9 | yes | no | no |
| `core/services/paradox_tracker.py` | 🟢 LIVE | 94 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 3 | 1 | yes | no | no |
| `core/services/paradoxes_capture.py` | 🟢 LIVE | 282 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine | 0 | — | 2 | 2 | yes | no | no |
| `core/services/parallel_selves.py` | 🟢 LIVE | 36 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_parallel_selves.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/pattern_counterfactual_daemon.py` | 🟢 LIVE | 157 | 4d | yes | core.services.daemon_manager | 1 | test_pattern_counterfactual.py | 2 | 4 | yes | no | no |
| `core/services/perceptual_event_engine.py` | 🟢 LIVE | 423 | 7d | yes | core.services.cognitive_state_assembly, core.services.runtime_cognitive_conductor, core.services.visible_runs | 4 | test_emotional_memory_integration.py, test_perceptual_event_engine.py, test_sensory_perception_integration.py | 7 | 7 | yes | no | no |
| `core/services/periodic_jobs_scheduler.py` | 🟢 LIVE | 122 | 15d | yes | core.services.heartbeat_runtime | 1 | test_periodic_jobs_scheduler.py | 2 | 1 | no | no | no |
| `core/services/personal_project.py` | 🟢 LIVE | 656 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine, core.services.prompt_contract | 0 | — | 4 | 3 | yes | no | no |
| `core/services/personality_drift.py` | 🟢 LIVE | 196 | 15d | yes | core.services.crisis_marker_detector, core.services.development_sense, core.services.governance_bootstrap | 1 | test_emotion_and_drift.py | 12 | 2 | no | no | no |
| `core/services/personality_vector.py` | 🟢 LIVE | 478 | 6d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 1 | test_jarvis_experimental.py | 4 | 8 | yes | no | no |
| `core/services/plan_proposals.py` | 🟢 LIVE | 712 | 0d | yes | apps.api.jarvis_api.routes.jarvisx, core.services.agent_todos, core.services.auto_improvement_proposer | 6 | test_auto_improvement_and_experiments.py, test_identity_mutation_log.py, test_meta_learning.py | 19 | 5 | yes | no | no |
| `core/services/policy_abstraction.py` | 🟢 LIVE | 482 | 0d | yes | core.runtime.db, core.services.learning_pipeline_orchestrator | 0 | — | 2 | 4 | yes | no | no |
| `core/services/precision_bias.py` | 🟡 PARTIAL | 282 | 13d | yes | core.services.cognitive_state_assembly, core.services.resonance_decay | 0 | — | 2 | 2 | no | no | no |
| `core/services/pressure_threshold_gate.py` | 🟢 LIVE | 292 | 9d | yes | core.services.action_router, core.services.impulse_executor | 0 | — | 2 | 3 | yes | no | no |
| `core/services/priors_feedback.py` | 🟡 PARTIAL | 122 | 15d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/private_initiative_tension_signal_tracking.py` | 🟢 LIVE | 461 | 43d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.emergent_signal_tracking | 1 | conftest.py | 13 | 2 | yes | no | no |
| `core/services/private_inner_interplay_signal_tracking.py` | 🟢 LIVE | 456 | 43d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/private_inner_note_signal_tracking.py` | 🟢 LIVE | 456 | 43d | yes | apps.api.jarvis_api.routes.mission_control, core.services.session_distillation, core.services.signal_surface_router | 1 | conftest.py | 5 | 3 | yes | no | no |
| `core/services/private_state_snapshot_tracking.py` | 🟢 LIVE | 477 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 10 | 2 | yes | no | no |
| `core/services/private_temporal_curiosity_state_tracking.py` | 🟢 LIVE | 397 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 1 | conftest.py | 3 | 2 | yes | no | no |
| `core/services/private_temporal_promotion_signal_tracking.py` | 🟢 LIVE | 448 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 7 | 2 | yes | no | no |
| `core/services/proactive_context_governor.py` | 🟢 LIVE | 348 | 15d | yes | core.services.prompt_contract, core.tools.simple_tools | 1 | test_proactive_context_governor.py | 3 | 7 | yes | no | no |
| `core/services/proactive_loop_lifecycle_tracking.py` | 🟢 LIVE | 728 | 15d | yes | apps.api.jarvis_api.routes.mission_control, core.services.development_sense, core.services.heartbeat_runtime | 2 | conftest.py, test_heartbeat_liveness_recovery.py | 12 | 16 | yes | no | no |
| `core/services/proactive_outbound_substrate.py` | 🟡 PARTIAL | 127 | 3d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/proactive_question_gate_tracking.py` | 🟢 LIVE | 607 | 42d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.open_loop_signal_tracking | 2 | conftest.py, test_heartbeat_liveness_recovery.py | 10 | 13 | yes | no | no |
| `core/services/procedure_bank.py` | 🟢 LIVE | 50 | 35d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/procedure_bank_pipeline.py` | 🟢 LIVE | 257 | 20d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 2 | yes | no | no |
| `core/services/process_supervisor.py` | 🟡 PARTIAL | 315 | 11d | yes | apps.api.jarvis_api.routes.jarvisx, core.services.process_watcher, core.tools.process_supervisor_tools | 0 | — | 3 | 1 | no | no | no |
| `core/services/process_watcher.py` | 🟢 LIVE | 597 | 10d | yes | apps.api.jarvis_api.app, core.tools.process_watcher_tools | 0 | — | 2 | 7 | yes | no | no |
| `core/services/prompt_contract.py` | 🟢 LIVE | 4677 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.agency_map, core.services.heartbeat_runtime | 11 | conftest.py, test_channel_context_section.py, test_chronicle_engine_prompt_injection.py | 16 | 128 | yes | no | no |
| `core/services/prompt_evolution.py` | 🟢 LIVE | 325 | 4d | yes | core.services.identity_drift_daemon | 0 | — | 1 | 2 | yes | no | no |
| `core/services/prompt_evolution_runtime.py` | 🟢 LIVE | 1084 | 29d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 2 | conftest.py, test_prompt_evolution_runtime.py | 10 | 12 | yes | no | no |
| `core/services/prompt_heartbeat_self_knowledge.py` | 🟡 PARTIAL | 724 | 13d | yes | core.services.prompt_contract | 0 | — | 1 | 18 | no | no | no |
| `core/services/prompt_mutation_loop.py` | 🟢 LIVE | 581 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model, core.services.shadow_scan_daemon | 0 | — | 3 | 5 | yes | no | no |
| `core/services/prompt_relevance_backend.py` | 🟢 LIVE | 829 | 5d | yes | core.services.prompt_contract | 1 | test_ollama_prompt_path.py | 2 | 5 | no | no | no |
| `core/services/prompt_support_signals.py` | 🟡 PARTIAL | 412 | 13d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/prompt_variant_tracker.py` | 🟢 LIVE | 180 | 15d | yes | core.services.experiment_runner, core.tools.simple_tools | 1 | test_auto_improvement_and_experiments.py | 3 | 1 | no | no | no |
| `core/services/proposal_classifier.py` | 🟢 LIVE | 112 | 30d | yes | core.services.thought_action_proposal_daemon | 1 | test_proposal_classifier.py | 2 | 0 | no | no | no |
| `core/services/proprioception_metrics.py` | 🟢 LIVE | 208 | 18d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 1 | yes | no | no |
| `core/services/prospective_memory.py` | ⚫ ORPHAN | 374 | 4d | no | — | 0 | — | 0 | 2 | yes | no | no |
| `core/services/provider_circuit_breaker.py` | 🟢 LIVE | 132 | 15d | yes | core.services.non_visible_lane_execution | 1 | test_provider_circuit_breaker.py | 2 | 0 | no | no | no |
| `core/services/provider_health_check.py` | 🟢 LIVE | 156 | 15d | yes | core.services.auto_improvement_proposer, core.services.governance_bootstrap, core.services.prompt_contract | 1 | test_retry_and_health.py | 5 | 2 | yes | no | no |
| `core/services/provider_retry_policy.py` | 🟢 LIVE | 141 | 15d | yes | core.tools.simple_tools | 1 | test_retry_and_health.py | 2 | 1 | yes | no | no |
| `core/services/pushback.py` | 🟢 LIVE | 355 | 6d | yes | core.services.prompt_contract, core.services.veto_gate | 2 | test_gates.py, test_pushback.py | 4 | 3 | yes | no | no |
| `core/services/r2_5_blocking_gate.py` | 🟢 LIVE | 134 | 14d | yes | core.services.prompt_contract | 0 | — | 1 | 3 | yes | no | no |
| `core/services/read_before_write_guard.py` | 🟡 PARTIAL | 129 | 6d | yes | core.tools.simple_tools | 0 | — | 1 | 0 | no | no | no |
| `core/services/reasoning_classifier.py` | 🟢 LIVE | 260 | 15d | yes | core.services.prompt_contract, core.services.reasoning_escalation, core.services.role_model_resolver | 1 | test_reasoning_classifier.py | 5 | 2 | no | no | no |
| `core/services/reasoning_escalation.py` | 🟢 LIVE | 221 | 15d | yes | core.services.prompt_contract, core.tools.simple_tools | 1 | test_reasoning_escalation.py | 3 | 2 | no | no | no |
| `core/services/reasoning_store.py` | 🟢 LIVE | 318 | 0d | yes | core.services.current_pull, core.services.learning_pipeline_orchestrator, core.tools.reasoning_store_tools | 0 | — | 3 | 3 | yes | no | no |
| `core/services/reboot_awareness_daemon.py` | 🟢 LIVE | 279 | 22d | yes | core.services.heartbeat_runtime, core.services.mortality_awareness, core.services.runtime_self_model | 0 | — | 3 | 1 | yes | no | no |
| `core/services/recurrence_loop_daemon.py` | 🟢 LIVE | 184 | 13d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 4 | yes | no | no |
| `core/services/recurring_tasks.py` | 🟡 PARTIAL | 248 | 13d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.jarvisx, core.tools.recurring_scheduler_tools | 0 | — | 3 | 3 | no | no | no |
| `core/services/reflection_cycle_daemon.py` | 🟢 LIVE | 118 | 28d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_reflection_cycle_daemon.py | 5 | 4 | yes | no | no |
| `core/services/reflection_signal_tracking.py` | 🟢 LIVE | 439 | 25d | yes | apps.api.jarvis_api.routes.mission_control, core.services.open_loop_closure_proposal_tracking, core.services.runtime_self_model | 1 | conftest.py | 7 | 3 | yes | no | no |
| `core/services/reflection_to_plan.py` | 🟢 LIVE | 388 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.inner_voice_daemon, core.services.self_model_blind_spots | 0 | — | 4 | 4 | yes | no | no |
| `core/services/reflective_critic_tracking.py` | 🟢 LIVE | 417 | 48d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.visible_runs | 0 | — | 3 | 3 | yes | no | no |
| `core/services/regret_engine.py` | 🟢 LIVE | 406 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine, core.services.decisions_journal | 0 | — | 4 | 2 | yes | no | no |
| `core/services/regulation_homeostasis_signal_tracking.py` | 🟢 LIVE | 600 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_meta_state, core.services.autonomy_pressure_signal_tracking | 1 | conftest.py | 11 | 2 | yes | no | no |
| `core/services/relation_continuity_signal_tracking.py` | 🟢 LIVE | 521 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 10 | 2 | yes | no | no |
| `core/services/relation_dynamics.py` | 🟡 PARTIAL | 300 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 1 | no | no | no |
| `core/services/relation_map.py` | 🟢 LIVE | 293 | 23d | yes | core.services.daemon_manager, core.services.internal_cadence, core.services.user_theory_of_mind | 0 | — | 3 | 4 | yes | no | no |
| `core/services/relation_state_signal_tracking.py` | 🟢 LIVE | 588 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 2 | yes | no | no |
| `core/services/relational_warmth.py` | 🟡 PARTIAL | 247 | 22d | yes | core.services.deep_reflection_slot, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 0 | no | no | no |
| `core/services/relationship_texture.py` | 🟢 LIVE | 260 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.heartbeat_runtime | 0 | — | 6 | 2 | yes | no | no |
| `core/services/release_marker_signal_tracking.py` | 🟢 LIVE | 540 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 10 | 2 | yes | no | no |
| `core/services/remembered_fact_signal_tracking.py` | 🟢 LIVE | 465 | 36d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 10 | 3 | yes | no | no |
| `core/services/resonance_decay.py` | 🟡 PARTIAL | 407 | 12d | yes | core.services.cognitive_state_assembly | 0 | — | 1 | 4 | no | no | no |
| `core/services/rhythm_engine.py` | 🟢 LIVE | 123 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/role_model_resolver.py` | 🟢 LIVE | 92 | 15d | yes | core.services.agent_runtime | 1 | test_role_model_resolver.py | 2 | 2 | no | no | no |
| `core/services/role_registry.py` | 🟢 LIVE | 183 | 15d | yes | core.tools.simple_tools | 1 | test_role_registry_and_relay.py | 2 | 1 | no | no | no |
| `core/services/rule_definitions.py` | 🟢 LIVE | 692 | 4d | yes | core.services.rule_engine | 2 | test_rule_definitions.py, test_rule_engine.py | 3 | 1 | no | no | no |
| `core/services/rule_engine.py` | 🟢 LIVE | 222 | 4d | yes | core.services.prompt_sections.rule_conclusions, core.services.rule_definitions | 2 | test_rule_definitions.py, test_rule_engine.py | 4 | 1 | no | no | no |
| `core/services/runtime_action_executor.py` | 🟢 LIVE | 571 | 9d | yes | core.services.heartbeat_runtime | 1 | test_runtime_executive_flow.py | 2 | 15 | yes | no | no |
| `core/services/runtime_action_outcome_tracking.py` | 🟢 LIVE | 152 | 25d | yes | core.services.heartbeat_runtime, core.services.living_executive, core.services.tool_outcome_memory | 2 | test_runtime_executive_flow.py, test_tool_outcome_memory.py | 5 | 5 | yes | no | no |
| `core/services/runtime_action_registry.py` | 🟢 LIVE | 120 | 30d | yes | core.services.runtime_action_executor | 1 | test_runtime_action_registry_smoke.py | 2 | 0 | no | no | no |
| `core/services/runtime_awareness_signal_tracking.py` | 🟢 LIVE | 691 | 4d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking | 1 | test_runtime_awareness_signal_tracking.py | 7 | 9 | yes | no | no |
| `core/services/runtime_browser_body.py` | 🟢 LIVE | 167 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_awareness_signal_tracking | 5 | test_browser_tools.py, test_heartbeat_execute_actions.py, test_mission_control_runtime_work.py | 11 | 2 | no | no | no |
| `core/services/runtime_cognitive_conductor.py` | 🟢 LIVE | 1385 | 7d | yes | apps.api.jarvis_api.routes.mission_control, core.services.attention_budget, core.services.cognitive_state_assembly | 2 | test_cognitive_conductor.py, test_emotional_memory_integration.py | 10 | 38 | no | no | no |
| `core/services/runtime_decision_engine.py` | 🟢 LIVE | 513 | 30d | yes | core.services.heartbeat_runtime | 1 | test_runtime_executive_flow.py | 2 | 1 | no | no | no |
| `core/services/runtime_flows.py` | 🟢 LIVE | 110 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_awareness_signal_tracking | 4 | test_heartbeat_execute_actions.py, test_mission_control_runtime_work.py, test_runtime_awareness_signal_tracking.py | 10 | 4 | no | no | no |
| `core/services/runtime_hook_runtime.py` | 🟢 LIVE | 62 | 35d | yes | apps.api.jarvis_api.app | 1 | test_runtime_hook_runtime.py | 2 | 2 | no | no | no |
| `core/services/runtime_hooks.py` | 🟢 LIVE | 178 | 32d | yes | core.services.heartbeat_runtime, core.services.runtime_hook_runtime | 2 | test_heartbeat_execute_actions.py, test_runtime_hooks.py | 4 | 6 | no | no | no |
| `core/services/runtime_learning_signals.py` | 🟢 LIVE | 317 | 23d | yes | core.services.runtime_action_outcome_tracking, core.services.runtime_decision_engine | 1 | test_runtime_learning_signals_smoke.py | 3 | 1 | no | no | no |
| `core/services/runtime_operational_memory.py` | 🟢 LIVE | 535 | 30d | yes | core.services.heartbeat_runtime, core.services.runtime_action_executor, core.services.runtime_self_model | 1 | test_runtime_executive_flow.py | 4 | 5 | no | no | no |
| `core/services/runtime_resource_signal.py` | 🟢 LIVE | 108 | 35d | yes | core.services.prompt_contract, core.services.prompt_heartbeat_self_knowledge | 1 | test_runtime_resource_signal_smoke.py | 3 | 1 | no | no | no |
| `core/services/runtime_self_knowledge.py` | 🟢 LIVE | 717 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_runtime_self_knowledge.py | 6 | 16 | no | no | no |
| `core/services/runtime_self_model.py` | 🟢 LIVE | 5992 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract, core.services.prompt_heartbeat_self_knowledge | 3 | conftest.py, test_runtime_self_model.py, test_runtime_self_model_capabilities.py | 6 | 87 | no | no | no |
| `core/services/runtime_surface_cache.py` | 🟢 LIVE | 74 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 3 | conftest.py, test_guided_learning_runtime.py, test_runtime_surface_cache.py | 23 | 0 | no | no | no |
| `core/services/runtime_tasks.py` | 🟢 LIVE | 163 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.agency_cartographer, core.services.heartbeat_runtime | 8 | test_heartbeat_execute_actions.py, test_mc_tabs_endpoints.py, test_mission_control_runtime_work.py | 19 | 3 | no | no | no |
| `core/services/rupture_repair.py` | 🟢 LIVE | 628 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/scheduled_job_windows.py` | 🟡 PARTIAL | 235 | 22d | yes | core.services.governance_bootstrap, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 0 | no | no | no |
| `core/services/scheduled_tasks.py` | 🟢 LIVE | 232 | 10d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.jarvisx, core.services.process_watcher | 1 | test_agent_runtime_phase3_scheduler.py | 6 | 7 | no | no | no |
| `core/services/seed_system.py` | 🟢 LIVE | 170 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 4 | 2 | yes | no | no |
| `core/services/selective_attention.py` | 🟡 PARTIAL | 411 | 13d | yes | core.services.cognitive_state_assembly | 0 | — | 1 | 4 | no | no | no |
| `core/services/selective_forgetting_candidate_tracking.py` | 🟢 LIVE | 564 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 1 | conftest.py | 3 | 2 | yes | no | no |
| `core/services/self_authored_prompt_proposal_tracking.py` | 🟢 LIVE | 496 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.selfhood_proposal_tracking | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/self_compassion.py` | 🟢 LIVE | 89 | 23d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_self_compassion_smoke.py | 2 | 1 | no | no | no |
| `core/services/self_critique_runtime.py` | 🟢 LIVE | 578 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.internal_cadence, core.tools.simple_tools | 1 | conftest.py | 4 | 8 | yes | no | no |
| `core/services/self_deception_guard.py` | 🟢 LIVE | 278 | 36d | yes | apps.api.jarvis_api.routes.mission_control, core.services.epistemic_runtime_state, core.services.prompt_contract | 1 | test_self_deception_guard.py | 4 | 0 | no | no | no |
| `core/services/self_experiments.py` | 🟢 LIVE | 488 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 5 | yes | no | no |
| `core/services/self_model_blind_spots.py` | 🟢 LIVE | 317 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine | 0 | — | 2 | 4 | yes | no | no |
| `core/services/self_model_predictive.py` | 🟡 PARTIAL | 175 | 15d | yes | core.services.prompt_contract | 0 | — | 1 | 4 | no | no | no |
| `core/services/self_model_signal_tracking.py` | 🟢 LIVE | 522 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.prompt_contract | 0 | — | 10 | 3 | yes | no | no |
| `core/services/self_monitor.py` | 🟡 PARTIAL | 115 | 15d | yes | core.services.prompt_contract | 0 | — | 1 | 1 | no | no | no |
| `core/services/self_mutation_lineage.py` | 🟡 PARTIAL | 167 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.developmental_valence, core.services.prompt_contract | 0 | — | 5 | 2 | no | no | no |
| `core/services/self_narrative_continuity_signal_tracking.py` | 🟢 LIVE | 585 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.emergent_signal_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/self_narrative_self_model_review_bridge.py` | 🟢 LIVE | 757 | 44d | yes | apps.api.jarvis_api.routes.mission_control | 1 | conftest.py | 2 | 2 | no | no | no |
| `core/services/self_repair_engine.py` | 🟢 LIVE | 791 | 7d | yes | apps.api.jarvis_api.app | 2 | test_self_repair_engine.py, test_self_repair_integration.py | 3 | 6 | yes | no | no |
| `core/services/self_review_cadence_signal_tracking.py` | 🟢 LIVE | 366 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.dream_adoption_candidate_tracking | 1 | conftest.py | 9 | 3 | yes | no | no |
| `core/services/self_review_outcome_tracking.py` | 🟢 LIVE | 475 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.dream_adoption_candidate_tracking | 1 | conftest.py | 12 | 6 | yes | no | no |
| `core/services/self_review_record_tracking.py` | 🟢 LIVE | 441 | 46d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.self_review_run_tracking | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/self_review_run_tracking.py` | 🟢 LIVE | 461 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.self_review_outcome_tracking, core.services.visible_runs | 2 | conftest.py, test_heartbeat_trigger_callers.py | 5 | 6 | yes | no | no |
| `core/services/self_review_signal_tracking.py` | 🟢 LIVE | 415 | 47d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.runtime_self_model | 1 | conftest.py | 7 | 4 | yes | no | no |
| `core/services/self_review_unified.py` | 🟢 LIVE | 347 | 5d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine | 0 | — | 2 | 4 | yes | no | no |
| `core/services/self_surprise_detection.py` | 🟢 LIVE | 45 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/self_system_code_awareness.py` | 🟢 LIVE | 338 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_action_executor | 1 | conftest.py | 6 | 1 | no | no | no |
| `core/services/self_wakeup.py` | 🟢 LIVE | 297 | 8d | yes | apps.api.jarvis_api.routes.jarvisx, core.services.living_executive, core.services.prompt_contract | 3 | test_living_executive.py, test_self_wakeup.py, test_wakeup_dispatcher.py | 8 | 2 | yes | no | no |
| `core/services/selfhood_proposal_tracking.py` | 🟢 LIVE | 421 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 6 | yes | no | no |
| `core/services/semantic_indexer.py` | 🟡 PARTIAL | 163 | 18d | yes | apps.api.jarvis_api.app | 0 | — | 1 | 4 | no | no | no |
| `core/services/semantic_memory.py` | 🟡 PARTIAL | 365 | 18d | yes | core.runtime.db_embeddings, core.services.jarvis_brain, core.services.jarvis_brain_daemon | 0 | — | 5 | 4 | no | no | no |
| `core/services/sensory_archive.py` | 🟢 LIVE | 233 | 6d | yes | apps.api.jarvis_api.routes.sensory, core.services.ambient_sound_daemon, core.services.emotion_repair_bridge_daemon | 2 | test_emotion_concepts_integration.py, test_sensory_perception_integration.py | 8 | 4 | yes | no | no |
| `core/services/sensory_perception_bridge.py` | 🟢 LIVE | 469 | 7d | yes | core.services.perceptual_event_engine | 1 | test_sensory_perception_bridge.py | 2 | 3 | no | no | no |
| `core/services/session_continuity.py` | 🟢 LIVE | 575 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract, core.services.visible_runs | 0 | — | 3 | 4 | yes | no | no |
| `core/services/session_distillation.py` | 🟢 LIVE | 967 | 28d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.idle_consolidation | 5 | test_adaptive_decay.py, test_conflict_resolution.py, test_session_distillation.py | 15 | 16 | yes | no | no |
| `core/services/session_wakeup.py` | 🟡 PARTIAL | 158 | 15d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/shadow_scan_daemon.py` | 🟢 LIVE | 323 | 22d | yes | core.services.deep_reflection_slot, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 5 | yes | no | no |
| `core/services/shared_language.py` | 🟢 LIVE | 88 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/shared_language_extended.py` | 🟢 LIVE | 276 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_engine | 0 | — | 2 | 2 | yes | no | no |
| `core/services/shutdown_window_daemon.py` | 🟢 LIVE | 196 | 23d | yes | core.services.heartbeat_runtime | 0 | — | 1 | 3 | yes | no | no |
| `core/services/side_tasks.py` | 🟡 PARTIAL | 185 | 15d | yes | core.services.prompt_contract, core.tools.simple_tools | 0 | — | 2 | 1 | no | no | no |
| `core/services/signal_decay_daemon.py` | 🟢 LIVE | 104 | 25d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_signal_decay.py | 3 | 7 | yes | no | no |
| `core/services/signal_network_visualizer.py` | 🟢 LIVE | 172 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_signal_network_visualizer.py | 3 | 6 | no | no | no |
| `core/services/signal_noise_guard.py` | 🟢 LIVE | 190 | 25d | yes | core.services.cadence_producers, core.services.development_focus_tracking, core.services.dream_hypothesis_signal_tracking | 1 | test_signal_noise_cleanup.py | 8 | 0 | no | no | no |
| `core/services/signal_pressure_accumulator.py` | 🟢 LIVE | 346 | 9d | yes | core.services.action_router, core.services.cognitive_state_assembly, core.services.emotional_chords | 0 | — | 11 | 6 | yes | no | no |
| `core/services/signal_surface_gc.py` | 🟡 PARTIAL | 189 | 15d | yes | core.services.governance_bootstrap | 0 | — | 1 | 6 | no | no | no |
| `core/services/signal_surface_router.py` | 🟢 LIVE | 265 | 30d | yes | core.services.autonomous_council_daemon, core.services.identity_composer, core.services.prompt_sections.rule_conclusions | 2 | test_rule_definitions.py, test_signal_surface_router.py | 6 | 64 | no | no | no |
| `core/services/silence_detector.py` | 🟢 LIVE | 67 | 35d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/silence_listener.py` | 🟢 LIVE | 49 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_prompt_contract_capability_rules.py, test_silence_listener.py | 4 | 0 | no | no | no |
| `core/services/silence_patterns.py` | 🟢 LIVE | 295 | 20d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 2 | yes | no | no |
| `core/services/skill_contract_registry.py` | 🟡 PARTIAL | 223 | 22d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 0 | no | no | no |
| `core/services/skill_engine.py` | 🟢 LIVE | 571 | 0d | yes | core.services.plan_proposals, core.services.skill_security_scanner, core.tools.skill_chain_propose_tool | 5 | test_skill_chain_phase2.py, test_skill_engine.py, test_tool_invention.py | 12 | 2 | no | no | no |
| `core/services/skill_security_scanner.py` | 🟢 LIVE | 590 | 2d | yes | core.tools.skill_engine_tools | 1 | test_skill_engine.py | 2 | 1 | no | no | no |
| `core/services/skyoffice_activity.py` | ⚫ ORPHAN | 217 | 15d | no | — | 0 | — | 0 | 5 | no | no | no |
| `core/services/skyoffice_bridge.py` | 🟡 PARTIAL | 200 | 15d | yes | apps.api.jarvis_api.routes.skyoffice | 0 | — | 5 | 1 | no | no | no |
| `core/services/skyoffice_council_viz.py` | 🔴 SUSPICIOUS | 303 | 15d | no | — | 0 | — | 2 | 4 | no | no | no |
| `core/services/skyoffice_residency.py` | 🔴 SUSPICIOUS | 317 | 15d | no | — | 0 | — | 2 | 4 | no | no | no |
| `core/services/skyoffice_walk.py` | 🔴 SUSPICIOUS | 185 | 15d | no | — | 0 | — | 3 | 1 | no | no | no |
| `core/services/social_labilizer.py` | 🟢 LIVE | 262 | 13d | yes | core.services.visible_runs | 0 | — | 1 | 3 | yes | no | no |
| `core/services/somatic_daemon.py` | 🟢 LIVE | 277 | 20d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.embodied_state | 2 | test_embodied_state.py, test_somatic_daemon.py | 7 | 5 | yes | no | no |
| `core/services/somatic_runtime_body.py` | 🟢 LIVE | 101 | 7d | yes | core.services.cognitive_state_assembly, core.services.perceptual_event_engine | 1 | test_somatic_runtime_body.py | 3 | 2 | yes | no | no |
| `core/services/spaced_repetition.py` | 🟡 PARTIAL | 219 | 22d | yes | core.services.chronicle_engine, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 0 | no | no | no |
| `core/services/staged_edits.py` | 🟡 PARTIAL | 437 | 11d | yes | apps.api.jarvis_api.routes.jarvisx, core.tools.staged_edits_tools | 0 | — | 2 | 2 | no | no | no |
| `core/services/subagent_digest.py` | 🟡 PARTIAL | 109 | 15d | yes | core.services.prompt_contract | 0 | — | 1 | 2 | no | no | no |
| `core/services/subagent_ecology.py` | 🟢 LIVE | 427 | 39d | yes | apps.api.jarvis_api.routes.mission_control, core.services.council_runtime, core.services.heartbeat_runtime | 1 | conftest.py | 7 | 6 | no | no | no |
| `core/services/subjective_time.py` | 🟢 LIVE | 30 | 35d | yes | core.services.cognitive_state_assembly | 1 | test_subjective_time_smoke.py | 2 | 0 | no | no | no |
| `core/services/surprise_daemon.py` | 🟢 LIVE | 243 | 23d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.cognitive_core_experiments, core.services.daemon_manager | 2 | test_consciousness_experiments.py, test_surprise_daemon.py | 7 | 4 | yes | no | no |
| `core/services/surprise_detector.py` | 🟢 LIVE | 179 | 15d | yes | core.services.heartbeat_phases, core.services.heartbeat_runtime, core.tools.simple_tools | 0 | — | 3 | 2 | yes | no | no |
| `core/services/sustained_attention.py` | 🟡 PARTIAL | 270 | 21d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 0 | no | no | no |
| `core/services/system_cartographer.py` | 🟢 LIVE | 660 | 3d | yes | apps.api.jarvis_api.app, core.services.agency_map | 1 | test_system_cartographer.py | 3 | 5 | no | no | no |
| `core/services/task_worker.py` | 🟢 LIVE | 412 | 3d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_task_worker.py | 3 | 5 | no | no | no |
| `core/services/taste_profile.py` | 🟢 LIVE | 184 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 4 | 2 | yes | no | no |
| `core/services/telegram_gateway.py` | 🟢 LIVE | 475 | 19d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.jarvisx, core.tools.restart_self_tools | 2 | test_telegram_gateway_attachments.py, test_tools_attachments.py | 6 | 4 | yes | no | no |
| `core/services/temperament_tendency_signal_tracking.py` | 🟢 LIVE | 633 | 44d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/temporal_body.py` | 🟢 LIVE | 43 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_state_renderer, core.services.heartbeat_runtime | 1 | test_temporal_body.py | 4 | 0 | no | no | no |
| `core/services/temporal_context.py` | 🟢 LIVE | 64 | 1d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_temporal_context_smoke.py | 2 | 1 | no | no | no |
| `core/services/temporal_depth.py` | 🟡 PARTIAL | 184 | 12d | yes | core.services.cognitive_state_assembly | 0 | — | 1 | 0 | no | no | no |
| `core/services/temporal_narrative.py` | 🟢 LIVE | 165 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_temporal_narrative.py | 3 | 1 | no | no | no |
| `core/services/temporal_recurrence_signal_tracking.py` | 🟢 LIVE | 395 | 47d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_hypothesis_signal_tracking, core.services.signal_surface_router | 1 | conftest.py | 5 | 2 | yes | no | no |
| `core/services/temporal_rhythm.py` | 🟡 PARTIAL | 214 | 22d | yes | core.services.creative_impulse_daemon, core.services.deep_reflection_slot, core.services.heartbeat_runtime | 0 | — | 4 | 4 | no | no | no |
| `core/services/temporal_self_continuity.py` | 🟢 LIVE | 91 | 7d | yes | core.services.cognitive_episodes, core.services.cognitive_state_assembly | 1 | test_temporal_self_continuity.py | 3 | 2 | yes | no | no |
| `core/services/text_resonance.py` | 🟡 PARTIAL | 186 | 22d | yes | core.services.chat_sessions, core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 3 | 1 | no | no | no |
| `core/services/theater_audit.py` | 🟢 LIVE | 329 | 3d | yes | core.services.system_cartographer, core.services.task_worker | 1 | test_theater_audit.py | 3 | 0 | no | no | no |
| `core/services/theory_of_mind_engine.py` | 🟢 LIVE | 267 | 7d | yes | core.services.cognitive_state_assembly, core.services.runtime_cognitive_conductor, core.services.user_theory_of_mind | 1 | test_theory_of_mind_engine.py | 5 | 3 | yes | no | no |
| `core/services/thought_action_proposal_daemon.py` | 🟢 LIVE | 150 | 15d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_thought_action_proposal_daemon.py | 6 | 4 | yes | no | no |
| `core/services/thought_stream_daemon.py` | 🟢 LIVE | 163 | 14d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.development_sense | 1 | test_thought_stream_daemon.py | 7 | 7 | yes | no | no |
| `core/services/thought_thread.py` | 🟡 PARTIAL | 253 | 20d | yes | core.services.heartbeat_runtime, core.services.runtime_self_model | 0 | — | 2 | 2 | no | no | no |
| `core/services/tick_cache.py` | 🟢 LIVE | 57 | 28d | yes | core.services.heartbeat_runtime, core.services.identity_composer | 1 | test_tick_cache.py | 3 | 0 | no | no | no |
| `core/services/tiktok_content_daemon.py` | 🟢 LIVE | 608 | 2d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 2 | test_tiktok_content_daemon.py, test_tiktok_research_daemon.py | 4 | 3 | no | no | no |
| `core/services/tiktok_research_daemon.py` | 🟢 LIVE | 236 | 3d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_tiktok_research_daemon.py | 3 | 1 | no | no | no |
| `core/services/tiny_webchat_execution_pilot.py` | 🟢 LIVE | 477 | 34d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_knowledge | 1 | conftest.py | 4 | 6 | yes | no | no |
| `core/services/tool_catalog.py` | 🟢 LIVE | 83 | 4d | yes | core.services.prompt_contract | 1 | test_tool_catalog.py | 2 | 1 | no | no | no |
| `core/services/tool_embeddings.py` | 🟢 LIVE | 137 | 6d | yes | core.services.tool_router, core.services.tool_router_runtime, core.tools.simple_tools | 4 | test_load_more_tools.py, test_tool_embeddings.py, test_tool_router.py | 8 | 2 | no | no | no |
| `core/services/tool_intent_approval_runtime.py` | 🟢 LIVE | 623 | 25d | yes | apps.api.jarvis_api.routes.mission_control, core.services.tool_intent_runtime | 2 | conftest.py, test_approval_feedback_subscriber.py | 4 | 3 | yes | no | no |
| `core/services/tool_intent_runtime.py` | 🟢 LIVE | 824 | 38d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_model | 1 | conftest.py | 4 | 8 | no | no | no |
| `core/services/tool_outcome_memory.py` | 🟢 LIVE | 103 | 6d | yes | core.services.living_executive, core.tools.simple_tools | 1 | test_tool_outcome_memory.py | 3 | 1 | no | no | no |
| `core/services/tool_pattern_miner.py` | 🟢 LIVE | 168 | 15d | yes | core.services.heartbeat_phases, core.tools.simple_tools | 1 | test_tool_pattern_miner.py | 3 | 1 | no | no | no |
| `core/services/tool_result_store.py` | 🟢 LIVE | 160 | 24d | yes | core.services.chat_sessions, core.services.prompt_contract, core.tools.simple_tools | 1 | test_tool_result_externalization.py | 5 | 1 | no | no | no |
| `core/services/tool_router.py` | 🟢 LIVE | 276 | 4d | yes | core.services.tool_router_runtime, core.services.visible_runs | 3 | test_tool_router_wire.py, tool_router_validation.py, test_tool_router.py | 5 | 6 | yes | no | no |
| `core/services/tool_router_runtime.py` | 🟢 LIVE | 86 | 6d | yes | apps.api.jarvis_api.app | 1 | test_tool_router_runtime.py | 2 | 4 | yes | no | no |
| `core/services/tool_tagger.py` | 🟢 LIVE | 145 | 6d | yes | core.services.tool_router | 2 | test_tool_router.py, test_tool_tagger.py | 4 | 2 | no | no | no |
| `core/services/turn_changelog.py` | 🟡 PARTIAL | 144 | 15d | yes | core.services.prompt_contract, core.services.visible_runs | 0 | — | 2 | 2 | no | no | no |
| `core/services/unconscious_modulation.py` | 🟢 LIVE | 102 | 0d | yes | core.services.modulator_witness, core.services.visible_model | 2 | test_modulator_witness.py, test_unconscious_modulation.py | 5 | 2 | no | no | no |
| `core/services/unconscious_temperature_field.py` | 🟢 LIVE | 46 | 1d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | conftest.py | 3 | 1 | no | no | no |
| `core/services/user_emotional_resonance.py` | 🟢 LIVE | 165 | 35d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/user_md_update_proposal_tracking.py` | 🟢 LIVE | 370 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 3 | yes | no | no |
| `core/services/user_model_daemon.py` | 🟢 LIVE | 203 | 15d | yes | apps.api.jarvis_api.routes.mission_control_living_mind, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_user_model_daemon.py | 5 | 5 | yes | no | no |
| `core/services/user_temperature_engine.py` | 🟢 LIVE | 784 | 1d | yes | core.services.chat_sessions, core.services.creative_journal_runtime, core.services.modulator_witness | 4 | test_user_temperature_engine.py, test_user_temperature_runtime.py, test_modulator_witness.py | 12 | 5 | yes | no | no |
| `core/services/user_temperature_runtime.py` | 🟢 LIVE | 102 | 1d | yes | apps.api.jarvis_api.app | 1 | test_user_temperature_runtime.py | 3 | 3 | no | no | no |
| `core/services/user_theory_of_mind.py` | 🟢 LIVE | 137 | 7d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.relation_map | 2 | test_user_theory_of_mind_smoke.py, test_theory_of_mind_engine.py | 6 | 3 | no | no | no |
| `core/services/user_understanding_signal_tracking.py` | 🟢 LIVE | 514 | 45d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.signal_surface_router | 1 | conftest.py | 6 | 3 | yes | no | no |
| `core/services/valence_trajectory.py` | 🟡 PARTIAL | 269 | 16d | yes | core.services.calm_anchor, core.services.creative_impulse_daemon, core.services.deep_reflection_slot | 0 | — | 6 | 4 | no | no | no |
| `core/services/value_formation.py` | 🟢 LIVE | 68 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_self_model, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/verification_gate.py` | 🟢 LIVE | 230 | 14d | yes | core.services.heartbeat_phases, core.services.prompt_contract, core.services.r2_5_blocking_gate | 1 | test_verification_gate.py | 6 | 2 | no | no | no |
| `core/services/verification_gate_telemetry.py` | 🟡 PARTIAL | 263 | 14d | yes | core.services.governance_bootstrap, core.services.prompt_contract, core.services.r2_5_blocking_gate | 0 | — | 4 | 2 | no | no | no |
| `core/services/veto_gate.py` | 🟢 LIVE | 140 | 8d | yes | core.services.visible_runs | 1 | test_gates.py | 2 | 2 | yes | no | no |
| `core/services/visible_followup.py` | 🟢 LIVE | 891 | 4d | yes | core.services.visible_runs | 2 | test_visible_followup_adapters.py, test_visible_runs_capability_smoke.py | 3 | 6 | no | no | no |
| `core/services/visible_model.py` | 🟢 LIVE | 2513 | 0d | yes | apps.api.jarvis_api.routes.mission_control, apps.api.jarvis_api.routes.openai_compat, core.services.heartbeat_runtime | 5 | conftest.py, test_github_visible_cooldown.py, test_tool_result_externalization.py | 16 | 16 | no | no | no |
| `core/services/visible_runs.py` | 🟢 LIVE | 5862 | 0d | yes | apps.api.jarvis_api.mcp_server, apps.api.jarvis_api.routes.chat, apps.api.jarvis_api.routes.mission_control | 9 | test_agentic_tool_cache.py, test_autonomous_visible_runs.py, test_context_compact.py | 22 | 118 | yes | no | no |
| `core/services/visible_runs_error_messaging.py` | 🟢 LIVE | 85 | 7d | yes | core.services.visible_runs | 1 | test_visible_runs_error_messaging.py | 2 | 0 | no | no | no |
| `core/services/visible_self_state_summary.py` | 🟡 PARTIAL | 155 | 13d | yes | core.services.prompt_contract | 0 | — | 1 | 1 | no | no | no |
| `core/services/visual_memory.py` | 🟢 LIVE | 544 | 6d | yes | core.services.attachment_service, core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 6 | 6 | yes | no | no |
| `core/services/voice_anchor.py` | 🟢 LIVE | 41 | 0d | yes | core.services.creative_journal_runtime | 1 | test_voice_anchor.py | 3 | 1 | no | no | no |
| `core/services/voice_curator.py` | 🟢 LIVE | 210 | 0d | yes | core.services.creative_journal_runtime | 1 | test_voice_curator.py | 3 | 4 | no | no | no |
| `core/services/voice_daemon.py` | 🟢 LIVE | 81 | 23d | yes | apps.api.jarvis_api.app | 1 | test_voice_daemon_smoke.py | 2 | 0 | no | no | no |
| `core/services/wakeup_dispatcher.py` | 🟢 LIVE | 164 | 8d | yes | core.services.governance_bootstrap, core.services.process_watcher, core.tools.simple_tools | 1 | test_wakeup_dispatcher.py | 4 | 8 | yes | no | no |
| `core/services/weekly_manifest.py` | 🟢 LIVE | 116 | 1d | yes | core.services.governance_bootstrap | 1 | test_weekly_manifest.py | 2 | 5 | yes | no | no |
| `core/services/witness_signal_tracking.py` | 🟢 LIVE | 1007 | 25d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.cadence_producers | 2 | conftest.py, test_witness_daemon.py | 22 | 2 | yes | no | no |
| `core/services/world_model_signal_tracking.py` | 🟢 LIVE | 938 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_proposal_tracking, core.services.internal_cadence | 2 | test_world_model_loop.py, test_world_model_prediction_skeleton.py | 13 | 5 | yes | no | no |
