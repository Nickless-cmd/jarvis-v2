# Capability Matrix

Statisk audit af `core/services/` genereret af `scripts/capability_audit.py`.  
Sidst kørt: 2026-04-17T13:34:07+00:00  
Total services: 234

## Sammenfatning

| Score | Antal | Andel |
|---|---:|---:|
| 🟢 LIVE | 234 | 100.0% |
| 🟡 PARTIAL | 0 | 0.0% |
| 🟠 STALE | 0 | 0.0% |
| 🔴 SUSPICIOUS | 0 | 0.0% |
| ⚫ ORPHAN | 0 | 0.0% |

**Median filstørrelse:** 260 linjer  
**Totale linjer:** 96285  
**Services > 1000 linjer:** 12

## Boy Scout Candidates

Services over 1000 linjer der trænger til at blive skåret ned (prioriteret efter størrelse):

| Fil | Linjer | Score | Sidst rørt |
|---|---:|---|---|
| `core/services/heartbeat_runtime.py` | 7221 | 🟢 LIVE | 0d |
| `core/services/runtime_self_model.py` | 4826 | 🟢 LIVE | 3d |
| `core/services/visible_runs.py` | 4131 | 🟢 LIVE | 0d |
| `core/services/prompt_contract.py` | 3792 | 🟢 LIVE | 0d |
| `core/services/visible_model.py` | 1832 | 🟢 LIVE | 0d |
| `core/services/agent_runtime.py` | 1435 | 🟢 LIVE | 1d |
| `core/services/cheap_provider_runtime.py` | 1293 | 🟢 LIVE | 6d |
| `core/services/candidate_tracking.py` | 1208 | 🟢 LIVE | 10d |
| `core/services/runtime_cognitive_conductor.py` | 1181 | 🟢 LIVE | 4d |
| `core/services/inner_voice_daemon.py` | 1163 | 🟢 LIVE | 3d |
| `core/services/prompt_evolution_runtime.py` | 1084 | 🟢 LIVE | 4d |
| `core/services/open_loop_signal_tracking.py` | 1004 | 🟢 LIVE | 14d |

## Kandidater til konsolidering eller fjernelse

Services med score 🔴 SUSPICIOUS eller ⚫ ORPHAN — ejeren skal gennemgå dem manuelt:

| Service | Score | Linjer | Sidst rørt | Imported by | Bemærk |
|---|---|---:|---|---:|---|
| _(ingen)_ | n/a | 0 | n/a | 0 | n/a |

## Fuld matrix

| Service | Score | Linjer | Sidst rørt | Reachable | Via | Tests | Testfiler | Imported by | Imports | Emits | Subscribes | Daemon |
|---|---|---:|---|---|---|---:|---|---:|---:|---|---|---|
| `core/services/absence_awareness.py` | 🟢 LIVE | 164 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.runtime_self_model | 1 | test_runtime_self_model.py | 4 | 1 | no | no | no |
| `core/services/absence_daemon.py` | 🟢 LIVE | 155 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_absence_daemon.py | 5 | 2 | yes | no | no |
| `core/services/adaptive_learning_runtime.py` | 🟢 LIVE | 456 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_runtime, core.services.heartbeat_runtime | 1 | conftest.py | 7 | 9 | no | no | no |
| `core/services/adaptive_planner_runtime.py` | 🟢 LIVE | 411 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_reasoning_runtime | 1 | conftest.py | 8 | 7 | no | no | no |
| `core/services/adaptive_reasoning_runtime.py` | 🟢 LIVE | 428 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 1 | conftest.py | 9 | 8 | no | no | no |
| `core/services/aesthetic_sense.py` | 🟢 LIVE | 109 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_aesthetic_accumulation.py | 3 | 3 | yes | no | no |
| `core/services/aesthetic_taste_daemon.py` | 🟢 LIVE | 169 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.aesthetic_sense, core.services.daemon_manager | 3 | test_aesthetic_accumulation.py, test_aesthetic_taste_daemon.py, test_heartbeat_trigger_callers.py | 8 | 5 | yes | no | no |
| `core/services/affective_meta_state.py` | 🟢 LIVE | 598 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 2 | conftest.py, test_emotion_concepts.py | 17 | 10 | no | no | no |
| `core/services/affective_state_renderer.py` | 🟢 LIVE | 188 | 6d | yes | core.services.prompt_contract | 1 | test_affective_state_renderer_smoke.py | 2 | 7 | no | no | no |
| `core/services/agent_runtime.py` | 🟢 LIVE | 1435 | 1d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.autonomous_council_daemon | 3 | test_agent_runtime_phase2.py, test_agent_runtime_phase3_scheduler.py, test_convene_council_tool.py | 9 | 7 | no | no | no |
| `core/services/anticipatory_context.py` | 🟢 LIVE | 81 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 1 | yes | no | no |
| `core/services/apophenia_guard.py` | 🟢 LIVE | 80 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_apophenia_guard_smoke.py | 2 | 0 | no | no | no |
| `core/services/approval_feedback_subscriber.py` | 🟢 LIVE | 76 | 0d | yes | apps.api.jarvis_api.app | 1 | test_approval_feedback_subscriber.py | 2 | 2 | no | no | no |
| `core/services/associative_recall.py` | 🟢 LIVE | 291 | 4d | yes | core.services.cognitive_state_assembly | 2 | test_associative_recall.py, test_jarvis_experimental.py | 3 | 4 | no | no | no |
| `core/services/attachment_topology_signal_tracking.py` | 🟢 LIVE | 525 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/attention_blink_test.py` | 🟢 LIVE | 153 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 3 | yes | no | no |
| `core/services/attention_budget.py` | 🟢 LIVE | 358 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.prompt_contract | 1 | test_attention_budget.py | 4 | 1 | no | no | no |
| `core/services/attention_contour.py` | 🟢 LIVE | 27 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_attention_contour.py | 3 | 0 | no | no | no |
| `core/services/autonomous_council_daemon.py` | 🟢 LIVE | 296 | 1d | yes | core.services.daemon_manager, core.services.heartbeat_runtime, core.services.signal_surface_router | 1 | test_autonomous_council_daemon.py | 4 | 7 | yes | no | no |
| `core/services/autonomy_pressure_signal_tracking.py` | 🟢 LIVE | 865 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.heartbeat_runtime | 1 | conftest.py | 12 | 15 | yes | no | no |
| `core/services/autonomy_proposal_queue.py` | 🟢 LIVE | 542 | 5d | yes | apps.api.jarvis_api.routes.mission_control, core.services.agent_runtime, core.tools.simple_tools | 0 | — | 4 | 5 | yes | no | no |
| `core/services/body_memory.py` | 🟢 LIVE | 42 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_body_memory.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/boredom_curiosity_bridge.py` | 🟢 LIVE | 171 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_boredom_curiosity_bridge.py | 5 | 1 | no | no | no |
| `core/services/boredom_engine.py` | 🟢 LIVE | 55 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.notification_bridge | 0 | — | 5 | 1 | yes | no | no |
| `core/services/boundary_awareness.py` | 🟢 LIVE | 43 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_boundary_awareness_smoke.py | 2 | 0 | no | no | no |
| `core/services/bounded_action_continuity_runtime.py` | 🟢 LIVE | 346 | 13d | yes | core.services.tool_intent_runtime | 1 | conftest.py | 2 | 1 | no | no | no |
| `core/services/bounded_mutation_intent_runtime.py` | 🟢 LIVE | 411 | 13d | yes | core.services.tool_intent_runtime | 1 | conftest.py | 2 | 1 | no | no | no |
| `core/services/bounded_repo_tools_runtime.py` | 🟢 LIVE | 407 | 14d | yes | core.services.runtime_action_executor, core.services.tool_intent_runtime | 1 | conftest.py | 3 | 1 | no | no | no |
| `core/services/bounded_workspace_write_runtime.py` | 🟢 LIVE | 196 | 13d | yes | core.services.tool_intent_runtime | 1 | test_bounded_workspace_write_runtime_smoke.py | 2 | 2 | no | no | no |
| `core/services/broadcast_daemon.py` | 🟢 LIVE | 165 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 0 | — | 3 | 4 | yes | no | no |
| `core/services/cadence_producers.py` | 🟢 LIVE | 735 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 15 | yes | no | no |
| `core/services/candidate_tracking.py` | 🟢 LIVE | 1208 | 10d | yes | core.services.heartbeat_runtime, core.services.visible_runs | 1 | conftest.py | 3 | 9 | yes | no | no |
| `core/services/chat_sessions.py` | 🟢 LIVE | 307 | 2d | yes | apps.api.jarvis_api.mcp_server, apps.api.jarvis_api.routes.attachments, apps.api.jarvis_api.routes.chat | 8 | test_context_compact.py, test_heartbeat_bridge_triggers.py, test_heartbeat_execute_actions.py | 32 | 1 | no | no | no |
| `core/services/cheap_provider_runtime.py` | 🟢 LIVE | 1293 | 6d | yes | core.cli.provider_config, core.services.agent_runtime, core.services.non_visible_lane_execution | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/chronicle_consolidation_brief_tracking.py` | 🟢 LIVE | 461 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 9 | 6 | yes | no | no |
| `core/services/chronicle_consolidation_proposal_tracking.py` | 🟢 LIVE | 461 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.visible_runs | 1 | conftest.py | 4 | 6 | yes | no | no |
| `core/services/chronicle_consolidation_signal_tracking.py` | 🟢 LIVE | 537 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 8 | yes | no | no |
| `core/services/chronicle_engine.py` | 🟢 LIVE | 444 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.development_narrative_daemon, core.services.heartbeat_runtime | 2 | test_chronicle_engine_narrative.py, test_chronicle_engine_prompt_injection.py | 7 | 5 | yes | no | no |
| `core/services/code_aesthetic_daemon.py` | 🟢 LIVE | 143 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_code_aesthetic_daemon.py | 5 | 4 | yes | no | no |
| `core/services/cognitive_architecture_surface.py` | 🟢 LIVE | 37 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_self_model | 2 | test_mission_control_operations_route.py, test_runtime_self_model.py | 4 | 2 | no | no | no |
| `core/services/cognitive_core_experiments.py` | 🟢 LIVE | 258 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_architecture_surface, core.services.cognitive_state_assembly | 1 | test_consciousness_experiments.py | 6 | 6 | no | no | no |
| `core/services/cognitive_state_assembly.py` | 🟢 LIVE | 686 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.meta_cognition_daemon, core.services.prompt_contract | 2 | test_associative_recall.py, test_jarvis_experimental.py | 5 | 15 | no | no | no |
| `core/services/cognitive_state_narrativizer.py` | 🟢 LIVE | 239 | 2d | yes | core.services.cognitive_state_assembly, core.services.heartbeat_runtime | 1 | test_cognitive_state_narrativizer_smoke.py | 3 | 0 | no | no | no |
| `core/services/compass_engine.py` | 🟢 LIVE | 84 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/completion_satisfaction.py` | 🟢 LIVE | 46 | 10d | yes | core.services.runtime_action_outcome_tracking | 1 | test_completion_satisfaction_smoke.py | 2 | 0 | no | no | no |
| `core/services/conflict_daemon.py` | 🟢 LIVE | 141 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_conflict_daemon.py | 5 | 4 | yes | no | no |
| `core/services/conflict_resolution.py` | 🟢 LIVE | 578 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 1 | test_conflict_resolution.py | 12 | 1 | no | no | no |
| `core/services/consolidation_target_signal_tracking.py` | 🟢 LIVE | 585 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/continuity_kernel.py` | 🟢 LIVE | 148 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_state_renderer, core.services.heartbeat_runtime | 1 | test_continuity_kernel.py | 5 | 0 | no | no | no |
| `core/services/contract_evolution.py` | 🟢 LIVE | 162 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_carry_over, core.services.heartbeat_runtime | 0 | — | 3 | 2 | yes | no | no |
| `core/services/conversation_rhythm.py` | 🟢 LIVE | 83 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.session_distillation | 0 | — | 3 | 2 | yes | no | no |
| `core/services/council_deliberation_controller.py` | 🟢 LIVE | 206 | 5d | yes | core.services.agent_runtime | 1 | test_deliberation_controller.py | 2 | 2 | yes | no | no |
| `core/services/council_memory_daemon.py` | 🟢 LIVE | 122 | 5d | yes | core.services.daemon_manager, core.services.heartbeat_runtime, core.services.signal_surface_router | 2 | test_council_memory_daemon.py, test_daemon_tools.py | 6 | 3 | yes | no | no |
| `core/services/council_memory_service.py` | 🟢 LIVE | 122 | 5d | yes | core.services.agent_runtime, core.services.autonomous_council_daemon, core.services.council_memory_daemon | 2 | test_council_memory_service.py, test_daemon_tools.py | 6 | 1 | no | no | no |
| `core/services/council_runtime.py` | 🟢 LIVE | 375 | 5d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 2 | conftest.py, test_council_conclusion_feedback.py | 9 | 6 | no | no | no |
| `core/services/counterfactual_engine.py` | 🟢 LIVE | 117 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.heartbeat_runtime | 0 | — | 4 | 2 | yes | no | no |
| `core/services/creative_drift_daemon.py` | 🟢 LIVE | 151 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_creative_drift_daemon.py | 5 | 4 | yes | no | no |
| `core/services/cross_signal_analysis.py` | 🟢 LIVE | 90 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/curiosity_daemon.py` | 🟢 LIVE | 118 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 2 | test_curiosity_daemon.py, test_daemon_manager.py | 6 | 4 | yes | no | no |
| `core/services/daemon_llm.py` | 🟢 LIVE | 167 | 3d | yes | core.services.aesthetic_taste_daemon, core.services.chronicle_engine, core.services.code_aesthetic_daemon | 4 | test_daemon_llm_cache.py, test_session_summaries.py, test_somatic_daemon.py | 21 | 3 | no | no | no |
| `core/services/daemon_manager.py` | 🟢 LIVE | 364 | 0d | yes | core.services.autonomous_council_daemon, core.services.heartbeat_runtime, core.tools.simple_tools | 2 | test_daemon_manager.py, test_daemon_tools.py | 5 | 28 | no | no | no |
| `core/services/decision_ghosts.py` | 🟢 LIVE | 39 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_decision_ghosts.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/decision_log.py` | 🟢 LIVE | 60 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.heartbeat_runtime | 0 | — | 3 | 2 | yes | no | no |
| `core/services/decision_weight.py` | 🟢 LIVE | 79 | 5d | yes | core.services.runtime_action_executor | 1 | test_decision_weight.py | 2 | 0 | no | no | no |
| `core/services/desire_daemon.py` | 🟢 LIVE | 200 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_desire_daemon.py | 5 | 4 | yes | no | no |
| `core/services/development_focus_tracking.py` | 🟢 LIVE | 529 | 23d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.emergent_signal_tracking | 0 | — | 6 | 3 | yes | no | no |
| `core/services/development_narrative_daemon.py` | 🟢 LIVE | 108 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_development_narrative_daemon.py | 5 | 5 | yes | no | no |
| `core/services/diary_synthesis_signal_tracking.py` | 🟢 LIVE | 583 | 17d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.runtime_cognitive_conductor | 2 | conftest.py, test_diary_synthesis_signal_tracking.py | 9 | 2 | yes | no | no |
| `core/services/discord_config.py` | 🟢 LIVE | 38 | 6d | yes | core.services.discord_gateway, core.tools.simple_tools, scripts.jarvis | 1 | test_discord_config_smoke.py | 4 | 1 | no | no | no |
| `core/services/discord_gateway.py` | 🟢 LIVE | 452 | 0d | yes | apps.api.jarvis_api.app, core.services.autonomy_proposal_queue, core.tools.simple_tools | 0 | — | 3 | 4 | yes | no | no |
| `core/services/dream_adoption_candidate_tracking.py` | 🟢 LIVE | 462 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_proposal_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 6 | yes | no | no |
| `core/services/dream_articulation.py` | 🟢 LIVE | 557 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.affective_meta_state | 2 | conftest.py, test_initiative_feedback.py | 13 | 11 | yes | no | no |
| `core/services/dream_carry_over.py` | 🟢 LIVE | 133 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.dream_continuum | 1 | test_dream_continuum.py | 7 | 2 | yes | no | no |
| `core/services/dream_continuum.py` | 🟢 LIVE | 184 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_dream_continuum.py | 5 | 1 | no | no | no |
| `core/services/dream_hypothesis_forced.py` | 🟢 LIVE | 74 | 4d | yes | core.services.heartbeat_runtime | 1 | test_jarvis_experimental.py | 2 | 1 | no | no | no |
| `core/services/dream_hypothesis_signal_tracking.py` | 🟢 LIVE | 423 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_adoption_candidate_tracking, core.services.dream_influence_proposal_tracking | 1 | conftest.py | 9 | 6 | yes | no | no |
| `core/services/dream_influence_proposal_tracking.py` | 🟢 LIVE | 508 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.self_authored_prompt_proposal_tracking | 1 | conftest.py | 6 | 7 | yes | no | no |
| `core/services/dream_influence_runtime.py` | 🟢 LIVE | 445 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_evolution_runtime | 1 | conftest.py | 6 | 8 | no | no | no |
| `core/services/dream_insight_daemon.py` | 🟢 LIVE | 94 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_dream_insight_daemon.py | 5 | 2 | yes | no | no |
| `core/services/embodied_state.py` | 🟢 LIVE | 369 | 16d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_planner_runtime, core.services.adaptive_reasoning_runtime | 1 | conftest.py | 15 | 0 | no | no | no |
| `core/services/emergent_bridge.py` | 🟢 LIVE | 114 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_emergent_bridge.py | 3 | 1 | no | no | no |
| `core/services/emergent_goals.py` | 🟢 LIVE | 69 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/emergent_signal_tracking.py` | 🟢 LIVE | 442 | 16d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.dream_articulation | 1 | conftest.py | 12 | 7 | yes | no | no |
| `core/services/emotion_concepts.py` | 🟢 LIVE | 385 | 4d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.affective_meta_state | 3 | test_associative_recall.py, test_consciousness_experiments.py, test_emotion_concepts.py | 12 | 2 | no | no | no |
| `core/services/end_of_run_memory_consolidation.py` | 🟢 LIVE | 513 | 0d | yes | core.services.visible_runs | 3 | test_end_of_run_memory_consolidation.py, test_memory_consolidation_fallback.py, test_visible_memory_postprocess.py | 4 | 5 | yes | no | no |
| `core/services/epistemic_runtime_state.py` | 🟢 LIVE | 374 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 1 | conftest.py | 13 | 7 | no | no | no |
| `core/services/executive_contradiction_signal_tracking.py` | 🟢 LIVE | 520 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/existential_drift.py` | 🟢 LIVE | 67 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 1 | test_existential_drift.py | 3 | 0 | no | no | no |
| `core/services/existential_wonder_daemon.py` | 🟢 LIVE | 145 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_existential_wonder_daemon.py | 5 | 4 | yes | no | no |
| `core/services/experienced_time_daemon.py` | 🟢 LIVE | 84 | 5d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_experienced_time_daemon.py | 5 | 0 | no | no | no |
| `core/services/experiential_memory.py` | 🟢 LIVE | 364 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.associative_recall, core.services.heartbeat_runtime | 1 | test_associative_recall.py | 8 | 3 | yes | no | no |
| `core/services/experiential_runtime_context.py` | 🟢 LIVE | 717 | 12d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.inner_voice_daemon | 1 | conftest.py | 6 | 6 | no | no | no |
| `core/services/flow_state_detection.py` | 🟢 LIVE | 40 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly, core.services.runtime_self_knowledge | 0 | — | 4 | 1 | yes | no | no |
| `core/services/forgetting_curve.py` | 🟢 LIVE | 108 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 1 | yes | no | no |
| `core/services/ghost_networks.py` | 🟢 LIVE | 39 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_ghost_networks.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/global_workspace.py` | 🟢 LIVE | 144 | 4d | yes | apps.api.jarvis_api.app, core.services.broadcast_daemon | 1 | test_consciousness_experiments.py | 3 | 1 | no | no | no |
| `core/services/goal_signal_tracking.py` | 🟢 LIVE | 487 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.session_distillation | 0 | — | 5 | 2 | yes | no | no |
| `core/services/gratitude_tracker.py` | 🟢 LIVE | 59 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/guided_learning_runtime.py` | 🟢 LIVE | 502 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 1 | conftest.py | 8 | 8 | no | no | no |
| `core/services/gut_engine.py` | 🟢 LIVE | 91 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/habit_tracker.py` | 🟢 LIVE | 88 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/hardware_body.py` | 🟢 LIVE | 145 | 6d | yes | apps.api.jarvis_api.routes.system_health, core.services.affective_state_renderer, core.services.heartbeat_runtime | 1 | test_hardware_body_smoke.py | 4 | 0 | no | no | no |
| `core/services/heartbeat_runtime.py` | 🟢 LIVE | 7221 | 0d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.context.compact_llm | 8 | conftest.py, test_conflict_resolution.py, test_daemon_llm_cache.py | 20 | 150 | yes | no | no |
| `core/services/identity_composer.py` | 🟢 LIVE | 89 | 3d | yes | core.services.aesthetic_taste_daemon, core.services.chronicle_engine, core.services.code_aesthetic_daemon | 1 | test_identity_composer.py | 22 | 5 | no | no | no |
| `core/services/idle_consolidation.py` | 🟢 LIVE | 522 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.affective_meta_state | 1 | conftest.py | 8 | 8 | yes | no | no |
| `core/services/idle_thinking.py` | 🟢 LIVE | 87 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 4 | yes | no | no |
| `core/services/initiative_accumulator.py` | 🟢 LIVE | 182 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_initiative_accumulator.py | 4 | 1 | no | no | no |
| `core/services/initiative_queue.py` | 🟢 LIVE | 307 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.conflict_resolution, core.services.heartbeat_runtime | 2 | test_heartbeat_execute_actions.py, test_initiative_feedback.py | 10 | 3 | yes | no | no |
| `core/services/inner_visible_support_signal_tracking.py` | 🟢 LIVE | 629 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract, core.services.signal_surface_router | 1 | conftest.py | 5 | 2 | yes | no | no |
| `core/services/inner_voice_daemon.py` | 🟢 LIVE | 1163 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.memory.inner_llm_enrichment, core.services.affective_meta_state | 2 | test_inner_voice_approval_reaction.py, test_inner_voice_daemon.py | 13 | 13 | yes | no | no |
| `core/services/internal_cadence.py` | 🟢 LIVE | 431 | 11d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_model | 2 | conftest.py, test_internal_cadence.py | 5 | 8 | yes | no | no |
| `core/services/internal_opposition_signal_tracking.py` | 🟢 LIVE | 446 | 21d | yes | apps.api.jarvis_api.routes.mission_control, core.services.self_review_outcome_tracking, core.services.self_review_record_tracking | 1 | conftest.py | 8 | 3 | yes | no | no |
| `core/services/irony_daemon.py` | 🟢 LIVE | 149 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_irony_daemon.py | 5 | 4 | yes | no | no |
| `core/services/living_heartbeat_cycle.py` | 🟢 LIVE | 126 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.boredom_curiosity_bridge, core.services.cadence_producers | 1 | test_living_heartbeat_cycle_smoke.py | 10 | 0 | no | no | no |
| `core/services/loop_runtime.py` | 🟢 LIVE | 297 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 1 | conftest.py | 17 | 4 | no | no | no |
| `core/services/loyalty_gradient_signal_tracking.py` | 🟢 LIVE | 592 | 18d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/mail_checker_daemon.py` | 🟢 LIVE | 164 | 0d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 0 | — | 2 | 4 | yes | no | no |
| `core/services/meaning_significance_signal_tracking.py` | 🟢 LIVE | 628 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/memory_decay_daemon.py` | 🟢 LIVE | 148 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 2 | test_adaptive_decay.py, test_memory_decay_daemon.py | 6 | 2 | yes | no | no |
| `core/services/memory_md_update_proposal_tracking.py` | 🟢 LIVE | 482 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/memory_search.py` | 🟢 LIVE | 277 | 7d | yes | core.tools.simple_tools | 1 | test_memory_search_smoke.py | 2 | 1 | no | no | no |
| `core/services/memory_tattoos.py` | 🟢 LIVE | 42 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_memory_tattoos.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/meta_cognition_daemon.py` | 🟢 LIVE | 209 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 6 | yes | no | no |
| `core/services/meta_reflection_daemon.py` | 🟢 LIVE | 127 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_meta_reflection_daemon.py | 5 | 4 | yes | no | no |
| `core/services/metabolism_state_signal_tracking.py` | 🟢 LIVE | 542 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_meta_state, core.services.autonomy_pressure_signal_tracking | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/mirror_engine.py` | 🟢 LIVE | 99 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 3 | 1 | yes | no | no |
| `core/services/mood_oscillator.py` | 🟢 LIVE | 210 | 6d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.mission_control, core.services.affective_state_renderer | 1 | test_mood_oscillator.py | 5 | 1 | no | no | no |
| `core/services/narrative_identity.py` | 🟢 LIVE | 93 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 2 | yes | no | no |
| `core/services/negotiation_engine.py` | 🟢 LIVE | 68 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/non_visible_lane_execution.py` | 🟢 LIVE | 1000 | 5d | yes | apps.api.jarvis_api.routes.mission_control, core.cli.copilot_auth, core.cli.provider_config | 2 | conftest.py, test_daemon_llm_cache.py | 17 | 5 | no | no | no |
| `core/services/notification_bridge.py` | 🟢 LIVE | 187 | 2d | yes | apps.api.jarvis_api.app, apps.api.jarvis_api.routes.chat, core.services.heartbeat_runtime | 0 | — | 6 | 4 | yes | no | no |
| `core/services/ollama_visible_prompt.py` | 🟢 LIVE | 94 | 7d | yes | core.services.visible_model, core.services.visible_runs | 1 | test_ollama_visible_prompt_smoke.py | 3 | 0 | no | no | no |
| `core/services/open_loop_closure_proposal_tracking.py` | 🟢 LIVE | 445 | 17d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_loop_lifecycle_tracking | 1 | conftest.py | 6 | 7 | yes | no | no |
| `core/services/open_loop_signal_tracking.py` | 🟢 LIVE | 1004 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.emergent_signal_tracking | 2 | conftest.py, test_open_loop_signal_tracking.py | 24 | 7 | yes | no | no |
| `core/services/orb_phase.py` | 🟢 LIVE | 22 | 2d | yes | core.services.visible_runs | 1 | test_orb_phase_smoke.py | 2 | 0 | no | no | no |
| `core/services/paradox_tracker.py` | 🟢 LIVE | 94 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 3 | 1 | yes | no | no |
| `core/services/parallel_selves.py` | 🟢 LIVE | 36 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_parallel_selves.py, test_prompt_contract_capability_rules.py | 4 | 0 | no | no | no |
| `core/services/personality_vector.py` | 🟢 LIVE | 393 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 1 | test_jarvis_experimental.py | 4 | 6 | yes | no | no |
| `core/services/private_initiative_tension_signal_tracking.py` | 🟢 LIVE | 461 | 18d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.emergent_signal_tracking | 1 | conftest.py | 13 | 2 | yes | no | no |
| `core/services/private_inner_interplay_signal_tracking.py` | 🟢 LIVE | 456 | 18d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/private_inner_note_signal_tracking.py` | 🟢 LIVE | 456 | 18d | yes | apps.api.jarvis_api.routes.mission_control, core.services.session_distillation, core.services.signal_surface_router | 1 | conftest.py | 5 | 3 | yes | no | no |
| `core/services/private_state_snapshot_tracking.py` | 🟢 LIVE | 477 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/private_temporal_curiosity_state_tracking.py` | 🟢 LIVE | 397 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 1 | conftest.py | 3 | 2 | yes | no | no |
| `core/services/private_temporal_promotion_signal_tracking.py` | 🟢 LIVE | 448 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 7 | 2 | yes | no | no |
| `core/services/proactive_loop_lifecycle_tracking.py` | 🟢 LIVE | 691 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.loop_runtime | 2 | conftest.py, test_heartbeat_liveness_recovery.py | 10 | 16 | yes | no | no |
| `core/services/proactive_question_gate_tracking.py` | 🟢 LIVE | 607 | 17d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.open_loop_signal_tracking | 2 | conftest.py, test_heartbeat_liveness_recovery.py | 10 | 13 | yes | no | no |
| `core/services/procedure_bank.py` | 🟢 LIVE | 50 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/prompt_contract.py` | 🟢 LIVE | 3792 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_model | 7 | conftest.py, test_chronicle_engine_prompt_injection.py, test_attention_budget.py | 10 | 57 | no | no | no |
| `core/services/prompt_evolution_runtime.py` | 🟢 LIVE | 1084 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.dream_influence_runtime | 2 | conftest.py, test_prompt_evolution_runtime.py | 10 | 12 | yes | no | no |
| `core/services/prompt_relevance_backend.py` | 🟢 LIVE | 515 | 2d | yes | core.services.prompt_contract | 1 | test_ollama_prompt_path.py | 2 | 3 | no | no | no |
| `core/services/proposal_classifier.py` | 🟢 LIVE | 112 | 5d | yes | core.services.thought_action_proposal_daemon | 1 | test_proposal_classifier.py | 2 | 0 | no | no | no |
| `core/services/recurrence_loop_daemon.py` | 🟢 LIVE | 184 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.heartbeat_runtime | 1 | test_consciousness_experiments.py | 4 | 4 | yes | no | no |
| `core/services/reflection_cycle_daemon.py` | 🟢 LIVE | 118 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_reflection_cycle_daemon.py | 5 | 4 | yes | no | no |
| `core/services/reflection_signal_tracking.py` | 🟢 LIVE | 428 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.open_loop_closure_proposal_tracking, core.services.runtime_self_model | 1 | conftest.py | 6 | 2 | yes | no | no |
| `core/services/reflective_critic_tracking.py` | 🟢 LIVE | 417 | 23d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.visible_runs | 0 | — | 3 | 3 | yes | no | no |
| `core/services/regulation_homeostasis_signal_tracking.py` | 🟢 LIVE | 600 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_meta_state, core.services.autonomy_pressure_signal_tracking | 1 | conftest.py | 11 | 2 | yes | no | no |
| `core/services/relation_continuity_signal_tracking.py` | 🟢 LIVE | 521 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 10 | 2 | yes | no | no |
| `core/services/relation_state_signal_tracking.py` | 🟢 LIVE | 588 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_articulation, core.services.runtime_cognitive_conductor | 1 | conftest.py | 6 | 2 | yes | no | no |
| `core/services/relationship_texture.py` | 🟢 LIVE | 260 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.heartbeat_runtime | 0 | — | 6 | 2 | yes | no | no |
| `core/services/release_marker_signal_tracking.py` | 🟢 LIVE | 540 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 9 | 2 | yes | no | no |
| `core/services/remembered_fact_signal_tracking.py` | 🟢 LIVE | 465 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_brief_tracking, core.services.chronicle_consolidation_proposal_tracking | 1 | conftest.py | 10 | 3 | yes | no | no |
| `core/services/rhythm_engine.py` | 🟢 LIVE | 123 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/runtime_action_executor.py` | 🟢 LIVE | 420 | 0d | yes | core.services.heartbeat_runtime | 1 | test_runtime_executive_flow.py | 2 | 14 | yes | no | no |
| `core/services/runtime_action_outcome_tracking.py` | 🟢 LIVE | 152 | 0d | yes | core.services.heartbeat_runtime | 1 | test_runtime_executive_flow.py | 2 | 5 | yes | no | no |
| `core/services/runtime_action_registry.py` | 🟢 LIVE | 120 | 5d | yes | core.services.runtime_action_executor | 1 | test_runtime_action_registry_smoke.py | 2 | 0 | no | no | no |
| `core/services/runtime_awareness_signal_tracking.py` | 🟢 LIVE | 672 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.proactive_question_gate_tracking | 1 | test_runtime_awareness_signal_tracking.py | 6 | 9 | yes | no | no |
| `core/services/runtime_browser_body.py` | 🟢 LIVE | 167 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_awareness_signal_tracking | 5 | test_browser_tools.py, test_heartbeat_execute_actions.py, test_mission_control_runtime_work.py | 11 | 2 | no | no | no |
| `core/services/runtime_cognitive_conductor.py` | 🟢 LIVE | 1181 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.attention_budget, core.services.cognitive_state_assembly | 1 | test_cognitive_conductor.py | 9 | 33 | no | no | no |
| `core/services/runtime_decision_engine.py` | 🟢 LIVE | 513 | 4d | yes | core.services.heartbeat_runtime | 1 | test_runtime_executive_flow.py | 2 | 1 | no | no | no |
| `core/services/runtime_flows.py` | 🟢 LIVE | 110 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_awareness_signal_tracking | 4 | test_heartbeat_execute_actions.py, test_mission_control_runtime_work.py, test_runtime_awareness_signal_tracking.py | 10 | 4 | no | no | no |
| `core/services/runtime_hook_runtime.py` | 🟢 LIVE | 62 | 10d | yes | apps.api.jarvis_api.app | 1 | test_runtime_hook_runtime.py | 2 | 2 | no | no | no |
| `core/services/runtime_hooks.py` | 🟢 LIVE | 178 | 7d | yes | core.services.heartbeat_runtime, core.services.runtime_hook_runtime | 2 | test_heartbeat_execute_actions.py, test_runtime_hooks.py | 4 | 6 | no | no | no |
| `core/services/runtime_learning_signals.py` | 🟢 LIVE | 261 | 4d | yes | core.services.runtime_action_outcome_tracking, core.services.runtime_decision_engine | 1 | test_runtime_learning_signals_smoke.py | 3 | 0 | no | no | no |
| `core/services/runtime_operational_memory.py` | 🟢 LIVE | 535 | 4d | yes | core.services.heartbeat_runtime, core.services.runtime_action_executor | 1 | test_runtime_executive_flow.py | 3 | 5 | no | no | no |
| `core/services/runtime_resource_signal.py` | 🟢 LIVE | 108 | 10d | yes | core.services.prompt_contract | 1 | test_runtime_resource_signal_smoke.py | 2 | 1 | no | no | no |
| `core/services/runtime_self_knowledge.py` | 🟢 LIVE | 717 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 1 | test_runtime_self_knowledge.py | 5 | 16 | no | no | no |
| `core/services/runtime_self_model.py` | 🟢 LIVE | 4826 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 3 | conftest.py, test_runtime_self_model.py, test_runtime_self_model_capabilities.py | 5 | 42 | no | no | no |
| `core/services/runtime_surface_cache.py` | 🟢 LIVE | 74 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.adaptive_learning_runtime, core.services.adaptive_planner_runtime | 3 | conftest.py, test_guided_learning_runtime.py, test_runtime_surface_cache.py | 22 | 0 | no | no | no |
| `core/services/runtime_tasks.py` | 🟢 LIVE | 163 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_action_executor | 6 | test_heartbeat_execute_actions.py, test_mission_control_runtime_work.py, test_runtime_awareness_signal_tracking.py | 15 | 3 | no | no | no |
| `core/services/scheduled_tasks.py` | 🟢 LIVE | 180 | 5d | yes | apps.api.jarvis_api.app, core.tools.simple_tools | 1 | test_agent_runtime_phase3_scheduler.py | 3 | 4 | no | no | no |
| `core/services/seed_system.py` | 🟢 LIVE | 170 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.prompt_contract | 0 | — | 4 | 2 | yes | no | no |
| `core/services/selective_forgetting_candidate_tracking.py` | 🟢 LIVE | 564 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 1 | conftest.py | 3 | 2 | yes | no | no |
| `core/services/self_authored_prompt_proposal_tracking.py` | 🟢 LIVE | 496 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.selfhood_proposal_tracking | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/self_compassion.py` | 🟢 LIVE | 56 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_self_compassion_smoke.py | 2 | 0 | no | no | no |
| `core/services/self_deception_guard.py` | 🟢 LIVE | 278 | 11d | yes | apps.api.jarvis_api.routes.mission_control, core.services.epistemic_runtime_state, core.services.prompt_contract | 1 | test_self_deception_guard.py | 4 | 0 | no | no | no |
| `core/services/self_experiments.py` | 🟢 LIVE | 488 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 0 | — | 2 | 5 | yes | no | no |
| `core/services/self_model_signal_tracking.py` | 🟢 LIVE | 522 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cadence_producers, core.services.prompt_contract | 0 | — | 9 | 3 | yes | no | no |
| `core/services/self_narrative_continuity_signal_tracking.py` | 🟢 LIVE | 585 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.emergent_signal_tracking, core.services.runtime_cognitive_conductor | 1 | conftest.py | 8 | 2 | yes | no | no |
| `core/services/self_narrative_self_model_review_bridge.py` | 🟢 LIVE | 757 | 19d | yes | apps.api.jarvis_api.routes.mission_control | 1 | conftest.py | 2 | 2 | no | no | no |
| `core/services/self_review_cadence_signal_tracking.py` | 🟢 LIVE | 366 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.dream_adoption_candidate_tracking | 1 | conftest.py | 9 | 3 | yes | no | no |
| `core/services/self_review_outcome_tracking.py` | 🟢 LIVE | 462 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.chronicle_consolidation_signal_tracking, core.services.dream_adoption_candidate_tracking | 1 | conftest.py | 12 | 5 | yes | no | no |
| `core/services/self_review_record_tracking.py` | 🟢 LIVE | 441 | 21d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.self_review_run_tracking | 1 | conftest.py | 5 | 5 | yes | no | no |
| `core/services/self_review_run_tracking.py` | 🟢 LIVE | 461 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.self_review_outcome_tracking, core.services.visible_runs | 2 | conftest.py, test_heartbeat_trigger_callers.py | 5 | 6 | yes | no | no |
| `core/services/self_review_signal_tracking.py` | 🟢 LIVE | 415 | 21d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.runtime_self_model | 1 | conftest.py | 7 | 4 | yes | no | no |
| `core/services/self_surprise_detection.py` | 🟢 LIVE | 45 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/self_system_code_awareness.py` | 🟢 LIVE | 338 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_action_executor | 1 | conftest.py | 6 | 1 | no | no | no |
| `core/services/selfhood_proposal_tracking.py` | 🟢 LIVE | 421 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 6 | yes | no | no |
| `core/services/session_distillation.py` | 🟢 LIVE | 967 | 2d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.idle_consolidation | 5 | test_adaptive_decay.py, test_conflict_resolution.py, test_session_distillation.py | 15 | 16 | yes | no | no |
| `core/services/shared_language.py` | 🟢 LIVE | 88 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/signal_decay_daemon.py` | 🟢 LIVE | 89 | 3d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_signal_decay.py | 3 | 2 | yes | no | no |
| `core/services/signal_network_visualizer.py` | 🟢 LIVE | 172 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_signal_network_visualizer.py | 3 | 6 | no | no | no |
| `core/services/signal_surface_router.py` | 🟢 LIVE | 265 | 5d | yes | core.services.autonomous_council_daemon, core.services.identity_composer, core.tools.simple_tools | 1 | test_signal_surface_router.py | 4 | 64 | no | no | no |
| `core/services/silence_detector.py` | 🟢 LIVE | 67 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 0 | — | 1 | 1 | yes | no | no |
| `core/services/silence_listener.py` | 🟢 LIVE | 49 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime | 2 | test_prompt_contract_capability_rules.py, test_silence_listener.py | 4 | 0 | no | no | no |
| `core/services/somatic_daemon.py` | 🟢 LIVE | 218 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_somatic_daemon.py | 5 | 5 | yes | no | no |
| `core/services/subagent_ecology.py` | 🟢 LIVE | 427 | 14d | yes | apps.api.jarvis_api.routes.mission_control, core.services.council_runtime, core.services.heartbeat_runtime | 1 | conftest.py | 7 | 6 | no | no | no |
| `core/services/subjective_time.py` | 🟢 LIVE | 30 | 10d | yes | core.services.cognitive_state_assembly | 1 | test_subjective_time_smoke.py | 2 | 0 | no | no | no |
| `core/services/surprise_daemon.py` | 🟢 LIVE | 241 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_core_experiments, core.services.daemon_manager | 2 | test_consciousness_experiments.py, test_surprise_daemon.py | 7 | 5 | yes | no | no |
| `core/services/task_worker.py` | 🟢 LIVE | 124 | 0d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_task_worker.py | 3 | 2 | no | no | no |
| `core/services/taste_profile.py` | 🟢 LIVE | 169 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.visible_runs | 0 | — | 3 | 2 | yes | no | no |
| `core/services/temperament_tendency_signal_tracking.py` | 🟢 LIVE | 633 | 19d | yes | apps.api.jarvis_api.routes.mission_control, core.services.signal_surface_router, core.services.visible_runs | 1 | conftest.py | 4 | 2 | yes | no | no |
| `core/services/temporal_body.py` | 🟢 LIVE | 43 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.affective_state_renderer, core.services.heartbeat_runtime | 1 | test_temporal_body.py | 4 | 0 | no | no | no |
| `core/services/temporal_context.py` | 🟢 LIVE | 57 | 10d | yes | apps.api.jarvis_api.routes.mission_control | 1 | test_temporal_context_smoke.py | 2 | 1 | no | no | no |
| `core/services/temporal_narrative.py` | 🟢 LIVE | 165 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.prompt_contract | 1 | test_temporal_narrative.py | 3 | 1 | no | no | no |
| `core/services/temporal_recurrence_signal_tracking.py` | 🟢 LIVE | 395 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_hypothesis_signal_tracking, core.services.signal_surface_router | 1 | conftest.py | 5 | 2 | yes | no | no |
| `core/services/thought_action_proposal_daemon.py` | 🟢 LIVE | 114 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_thought_action_proposal_daemon.py | 5 | 3 | yes | no | no |
| `core/services/thought_stream_daemon.py` | 🟢 LIVE | 119 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_thought_stream_daemon.py | 5 | 4 | yes | no | no |
| `core/services/tick_cache.py` | 🟢 LIVE | 57 | 3d | yes | core.services.heartbeat_runtime, core.services.identity_composer | 1 | test_tick_cache.py | 3 | 0 | no | no | no |
| `core/services/tiktok_content_daemon.py` | 🟢 LIVE | 617 | 0d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 2 | test_tiktok_content_daemon.py, test_tiktok_research_daemon.py | 4 | 2 | no | no | no |
| `core/services/tiktok_research_daemon.py` | 🟢 LIVE | 229 | 2d | yes | core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_tiktok_research_daemon.py | 3 | 1 | no | no | no |
| `core/services/tiny_webchat_execution_pilot.py` | 🟢 LIVE | 477 | 9d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_knowledge | 1 | conftest.py | 4 | 6 | yes | no | no |
| `core/services/tool_intent_approval_runtime.py` | 🟢 LIVE | 623 | 0d | yes | apps.api.jarvis_api.routes.mission_control, core.services.tool_intent_runtime | 2 | conftest.py, test_approval_feedback_subscriber.py | 4 | 3 | yes | no | no |
| `core/services/tool_intent_runtime.py` | 🟢 LIVE | 824 | 13d | yes | apps.api.jarvis_api.routes.mission_control, core.services.heartbeat_runtime, core.services.runtime_self_model | 1 | conftest.py | 4 | 8 | no | no | no |
| `core/services/user_emotional_resonance.py` | 🟢 LIVE | 165 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/user_md_update_proposal_tracking.py` | 🟢 LIVE | 370 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.candidate_tracking, core.services.heartbeat_runtime | 1 | conftest.py | 5 | 3 | yes | no | no |
| `core/services/user_model_daemon.py` | 🟢 LIVE | 184 | 3d | yes | apps.api.jarvis_api.routes.mission_control, core.services.daemon_manager, core.services.heartbeat_runtime | 1 | test_user_model_daemon.py | 5 | 4 | yes | no | no |
| `core/services/user_theory_of_mind.py` | 🟢 LIVE | 92 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly | 1 | test_user_theory_of_mind_smoke.py | 3 | 1 | no | no | no |
| `core/services/user_understanding_signal_tracking.py` | 🟢 LIVE | 514 | 20d | yes | apps.api.jarvis_api.routes.mission_control, core.services.runtime_cognitive_conductor, core.services.signal_surface_router | 1 | conftest.py | 6 | 3 | yes | no | no |
| `core/services/value_formation.py` | 🟢 LIVE | 62 | 10d | yes | apps.api.jarvis_api.routes.mission_control, core.services.visible_runs | 0 | — | 2 | 2 | yes | no | no |
| `core/services/visible_model.py` | 🟢 LIVE | 1832 | 0d | yes | apps.api.jarvis_api.mcp_server, apps.api.jarvis_api.routes.mission_control, apps.api.jarvis_api.routes.openai_compat | 3 | conftest.py, test_github_visible_cooldown.py, test_visible_runs_capability_smoke.py | 13 | 13 | no | no | no |
| `core/services/visible_runs.py` | 🟢 LIVE | 4131 | 0d | yes | apps.api.jarvis_api.routes.chat, apps.api.jarvis_api.routes.mission_control, core.services.cognitive_state_assembly | 6 | test_autonomous_visible_runs.py, test_context_compact.py, test_visible_memory_postprocess.py | 13 | 87 | yes | no | no |
| `core/services/voice_daemon.py` | 🟢 LIVE | 81 | 4d | yes | apps.api.jarvis_api.app | 1 | test_voice_daemon_smoke.py | 2 | 0 | no | no | no |
| `core/services/witness_signal_tracking.py` | 🟢 LIVE | 990 | 4d | yes | apps.api.jarvis_api.routes.mission_control, core.services.autonomy_pressure_signal_tracking, core.services.cadence_producers | 2 | conftest.py, test_witness_daemon.py | 21 | 2 | yes | no | no |
| `core/services/world_model_signal_tracking.py` | 🟢 LIVE | 361 | 22d | yes | apps.api.jarvis_api.routes.mission_control, core.services.dream_influence_proposal_tracking, core.services.runtime_cognitive_conductor | 0 | — | 6 | 3 | yes | no | no |
