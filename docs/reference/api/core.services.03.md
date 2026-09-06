# `core.services.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/bash_sandbox.py`
_bwrap-indespærring om én bash-kommando. SLUKKET som standard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_available` | `()` | Findes bwrap på DENNE maskine? | [src](../../../core/services/bash_sandbox.py#L57) |
| function | `is_enabled` | `()` | Eksplicit tændt? Usat betyder SLUKKET — modsat central_switches' default. | [src](../../../core/services/bash_sandbox.py#L62) |
| function | `set_enabled` | `(on)` | — | [src](../../../core/services/bash_sandbox.py#L72) |
| function | `status` | `()` | — | [src](../../../core/services/bash_sandbox.py#L79) |
| function | `wrap_bwrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | Byg argv'en. Ren funktion — tjekker hverken flag eller tilgængelighed. | [src](../../../core/services/bash_sandbox.py#L93) |
| function | `maybe_wrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | argv hvis sandboxen er tændt OG mulig her — ellers None (kør normalt). | [src](../../../core/services/bash_sandbox.py#L113) |

## `core/services/behavioral_decisions.py`
_Behavioral decisions — closing the reflection→behavior loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_directive` | `(value)` | — | [src](../../../core/services/behavioral_decisions.py#L34) |
| function | `_commit_observe` | `(outcome, decision_id)` | Commit-cluster instrument: decision_create → central observe (best-effort). | [src](../../../core/services/behavioral_decisions.py#L38) |
| function | `create_decision` | `(*, directive, rationale=…, trigger_cue=…, priority=…, source_record_id=…, source_type=…, created_by=…)` | — | [src](../../../core/services/behavioral_decisions.py#L50) |
| function | `review_decision` | `(*, decision_id, verdict, note=…, evidence=…)` | — | [src](../../../core/services/behavioral_decisions.py#L106) |
| function | `change_status` | `(decision_id, new_status)` | — | [src](../../../core/services/behavioral_decisions.py#L136) |
| function | `revoke_decision` | `(decision_id, *, reason=…)` | — | [src](../../../core/services/behavioral_decisions.py#L154) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L172) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L182) |
| function | `get_decision_with_reviews` | `(decision_id, *, review_limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L186) |
| function | `list_active_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L213) |
| function | `list_all_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L217) |
| function | `format_active_decisions_for_heartbeat` | `(*, max_items=…)` | Compact line of top active commitments for heartbeat injection. | [src](../../../core/services/behavioral_decisions.py#L221) |
| function | `get_stats` | `()` | — | [src](../../../core/services/behavioral_decisions.py#L240) |

## `core/services/body_memory.py`
_Body Memory — Jarvis' physical sensation snapshots._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_body_snapshot` | `(context, sensation=…, intensity=…)` | — | [src](../../../core/services/body_memory.py#L9) |
| function | `describe_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L20) |
| function | `format_body_for_prompt` | `()` | — | [src](../../../core/services/body_memory.py#L26) |
| function | `reset_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L32) |
| function | `build_body_memory_surface` | `()` | — | [src](../../../core/services/body_memory.py#L36) |

## `core/services/boredom_curiosity_bridge.py`
_Boredom to Curiosity Bridge — transforms boredom into curiosity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Curiosity` | `` | A curiosity that emerges from boredom. | [src](../../../core/services/boredom_curiosity_bridge.py#L22) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L36) |
| function | `add_boredom` | `(duration)` | Add boredom based on elapsed duration. | [src](../../../core/services/boredom_curiosity_bridge.py#L40) |
| function | `_spawn_curiosity` | `()` | Spawn a curiosity when boredom is high enough. | [src](../../../core/services/boredom_curiosity_bridge.py#L89) |
| function | `should_spawn_curiosity` | `()` | Check if curiosity should spawn based on boredom level. | [src](../../../core/services/boredom_curiosity_bridge.py#L129) |
| function | `get_curiosity_prompt` | `()` | Get the most relevant curiosity prompt. | [src](../../../core/services/boredom_curiosity_bridge.py#L134) |
| function | `get_active_curiosities` | `()` | Get all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L143) |
| function | `clear_curiosities` | `()` | Clear all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L157) |
| function | `reset_boredom_curiosity_bridge` | `()` | Reset boredom curiosity bridge state (for testing). | [src](../../../core/services/boredom_curiosity_bridge.py#L163) |
| function | `get_boredom_curiosity_state` | `()` | Get current state of boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L171) |
| function | `build_boredom_curiosity_bridge_surface` | `()` | Build MC surface for boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L181) |

## `core/services/boredom_engine.py`
_Boredom Engine — productive restlessness as first-class experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_boredom_state` | `(*, idle_hours=…, tick_monotony=…, novelty_score=…, open_loop_count=…)` | — | [src](../../../core/services/boredom_engine.py#L11) |
| function | `get_boredom_state` | `()` | — | [src](../../../core/services/boredom_engine.py#L49) |
| function | `build_boredom_surface` | `()` | — | [src](../../../core/services/boredom_engine.py#L53) |

## `core/services/boundary_awareness.py`
_Boundary Awareness — "Where do I end?"_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_boundary_model` | `()` | Build Jarvis' sense of his own boundaries. | [src](../../../core/services/boundary_awareness.py#L8) |
| function | `format_boundary_for_prompt` | `()` | Compact boundary awareness for prompt injection. | [src](../../../core/services/boundary_awareness.py#L31) |
| function | `build_boundary_awareness_surface` | `()` | — | [src](../../../core/services/boundary_awareness.py#L40) |

## `core/services/bounded_action_continuity_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface=…)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L12) |
| function | `_derive_current_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L40) |
| function | `_derive_followup_from_awareness` | `(*, execution_state, action_type, action_target, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L143) |
| function | `_derive_continuity_state` | `(*, execution_state, followup_state)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L243) |
| function | `_continuity_id` | `(*, action_type, action_target, action_summary, action_outcome, approval_resolved_at, approval_source)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L267) |
| function | `_default_action_continuity_surface` | `()` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L291) |
| function | `_normalize_action_continuity_surface` | `(surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L323) |
| function | `_merge_unique` | `(left, right)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L337) |

## `core/services/bounded_mutation_intent_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_mutation_intent_surface` | `(intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L25) |
| function | `_build_write_proposal_surface` | `(*, classification, mutation_near, intent_state, intent_type, approval_scope, target_files, target_paths, repo_scope, system_scope, sudo_required, mutation_critical)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L127) |
| function | `_derive_write_proposal_confidence` | `(*, proposal_type, target_files, repo_scope, system_scope)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L224) |
| function | `_write_proposal_reason` | `(*, proposal_type, approval_scope, target_files, repo_scope, system_scope, sudo_required, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L240) |
| function | `_derive_classification` | `(*, intent_state, intent_type, approval_scope, awareness_surface, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L275) |
| function | `_derive_targets` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L310) |
| function | `_derive_repo_mutation_scope` | `(*, classification, approval_scope, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L327) |
| function | `_derive_system_mutation_scope` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L342) |
| function | `_derive_sudo_required` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L355) |
| function | `_derive_deleted_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L367) |
| function | `_derive_modified_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L371) |
| function | `_derive_untracked_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L375) |
| function | `_bounded_path_list` | `(value)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L379) |
| function | `_approval_required_mutation_capability_summary` | `()` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L385) |
| function | `_unique` | `(values)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L403) |

## `core/services/bounded_repo_tools_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_repo_tool_execution_surface` | `(intent_surface, *, awareness_surface=…)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L14) |
| function | `_build_bounded_repo_tool_execution_surface` | `(intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L40) |
| function | `_allowed_operation` | `(intent_type)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L145) |
| function | `_inspect_repo_status` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L175) |
| function | `_inspect_working_tree` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L198) |
| function | `_inspect_local_changes` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L219) |
| function | `_inspect_upstream_divergence` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L236) |
| function | `_request_bounded_diagnostic` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L268) |
| function | `_git_status_observation` | `(repo_root)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L293) |
| function | `_run_git_command` | `(repo_root, args)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L374) |
| function | `_trim_lines` | `(value)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L392) |
| function | `_safe_int` | `(value)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L396) |
| function | `_merge_unique` | `(primary, secondary)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L403) |

## `core/services/bounded_workspace_write_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_workspace_write_execution_surface` | `()` | — | [src](../../../core/services/bounded_workspace_write_runtime.py#L7) |

## `core/services/bridge_presence.py`
_Cross-proces bro-tilstedeværelse via shared_cache (samme mønster som central_xproc)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish` | `(bridges)` | Publicér denne proces' bro-registry-snapshot (kaldes ved register/unregister/dispatch). | [src](../../../core/services/bridge_presence.py#L25) |
| function | `all_presence` | `()` | Bro-tilstedeværelse fra ALLE processer → {user_id: {process, client, capabilities, ...}}. | [src](../../../core/services/bridge_presence.py#L40) |
| function | `process_for_user` | `(user_id)` | Hvilken proces holder en levende bro for user_id? None hvis ingen. | [src](../../../core/services/bridge_presence.py#L59) |

## `core/services/bro_broker.py`
_Bro-broker — owner-styret skift mellem aktive bro-forbindelser (spec §6.6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `summarize_tool_result_for_server` | `(tool_name, result, *, max_error_chars=…)` | Filtrér et code-mode tool-resultat så KUN metadata/summary krydser til | [src](../../../core/services/bro_broker.py#L31) |
| function | `_active_user_ids` | `()` | user_id'er med en aktiv bro (process-local registry). | [src](../../../core/services/bro_broker.py#L70) |
| function | `list_active_bros` | `()` | Alle brugere med en aktiv bro lige nu. | [src](../../../core/services/bro_broker.py#L79) |
| function | `switch` | `(target_user, *, requester_session, now=…)` | Skift requester-sessionen til target-brugerens bro — kræver gyldig override. | [src](../../../core/services/bro_broker.py#L84) |

## `core/services/broadcast_daemon.py`
_Broadcast Daemon — detects emergent coherence across daemons (Experiment 3: GWT)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_broadcast_daemon` | `()` | Run one coherence analysis pass. Returns dict with broadcast_count/coherence. | [src](../../../core/services/broadcast_daemon.py#L23) |
| function | `build_workspace_surface` | `()` | MC surface for global workspace experiment. | [src](../../../core/services/broadcast_daemon.py#L69) |
| function | `_cluster_by_topic` | `(entries)` | Group entries into clusters where Jaccard similarity of topics >= threshold. | [src](../../../core/services/broadcast_daemon.py#L95) |
| function | `_representative_topic` | `(cluster)` | Return the most common meaningful words across all topics in cluster. | [src](../../../core/services/broadcast_daemon.py#L112) |
| function | `_fire_broadcast` | `(cluster, unique_sources, topic_cluster)` | Persist broadcast event and publish to eventbus. | [src](../../../core/services/broadcast_daemon.py#L122) |
| function | `_compute_coherence` | `()` | workspace_coherence = broadcast events with 3+ sources / total events (rolling 24h). | [src](../../../core/services/broadcast_daemon.py#L152) |

## `core/services/cache_boundary_observer.py`
_Cache-boundary drift observer (harness Part B, Mechanism A)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_static_prefix` | `(*, provider, model, section_shape, static_prefix_sha)` | Record the static-prefix hash for (provider, model, shape); on a same-shape | [src](../../../core/services/cache_boundary_observer.py#L17) |

## `core/services/cache_maintenance_daemon.py`
_Cache maintenance daemon — periodic cleanup of expired web cache entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_cache_maintenance_daemon` | `()` | Run cache cleanup if cadence elapsed. Returns stats dict. | [src](../../../core/services/cache_maintenance_daemon.py#L33) |
| function | `get_cache_maintenance_stats` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L180) |
| function | `build_cache_maintenance_surface` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L187) |

## `core/services/cache_telemetry.py`
_Per-request cache-telemetri for den synlige DeepSeek-lane (2026-06-30)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `prefix_signature` | `(system_content, tools)` | Beregn (sha-prefix, længde) for det cachebare [system + tools]. | [src](../../../core/services/cache_telemetry.py#L24) |
| function | `record_visible_cache` | `(*, run_id=…, round_index=…, autonomous=…, lane=…, provider=…, model=…, prefix_sha=…, prefix_len=…, cache_hit=…, cache_miss=…)` | Append én telemetri-linje. Self-safe (sluger alt). | [src](../../../core/services/cache_telemetry.py#L40) |

## `core/services/cadence_producers.py`
_Cadence Producers — central orchestration for waking up dead MC fields._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/cadence_producers.py#L54) |
| function | `_meaningful_run_topic` | `(user_message)` | — | [src](../../../core/services/cadence_producers.py#L58) |
| function | `produce_signals_from_run` | `(*, run_id, session_id, user_message, assistant_response, outcome_status, user_mood=…)` | Fire all relevant signals after a visible run, bypassing chain dependencies. | [src](../../../core/services/cadence_producers.py#L63) |
| function | `produce_emergent_signals_from_history` | `()` | Run the emergent signal daemon to scan timeline for patterns. | [src](../../../core/services/cadence_producers.py#L594) |
| function | `detect_decision_in_message` | `(*, user_message, assistant_response, run_id)` | Detect decisions in conversation and log them. | [src](../../../core/services/cadence_producers.py#L609) |
| function | `run_adoption_pipelines` | `()` | Move things from candidate → adopted state. | [src](../../../core/services/cadence_producers.py#L643) |
| function | `sync_personality_to_self_model` | `()` | Bridge: sync personality_vector changes to self_model_signal. | [src](../../../core/services/cadence_producers.py#L674) |
| function | `progress_signal_lifecycles` | `()` | Move signals through lifecycle stages: active → carried → fading → released. | [src](../../../core/services/cadence_producers.py#L752) |
| function | `_observe_frozen` | `(nerve, meta)` | EGRESS-FRI liveness for en vækket frossen detektor (rettet 2026-07-01: var central().observe). | [src](../../../core/services/cadence_producers.py#L787) |
| function | `tick_frozen_detectors` | `(tick_count)` | LivingNeuron Fase B: væk de frosne detektorer på LAV cadence (deres consumers sultede på | [src](../../../core/services/cadence_producers.py#L796) |
| function | `build_cadence_producers_surface` | `()` | MC surface for cadence producer status. | [src](../../../core/services/cadence_producers.py#L853) |

## `core/services/calm_anchor.py`
_Calm Anchor — baseline reference state Jarvis can return to._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_persisted_samples` | `()` | — | [src](../../../core/services/calm_anchor.py#L37) |
| function | `_persist_samples` | `()` | — | [src](../../../core/services/calm_anchor.py#L55) |
| function | `_current_snapshot` | `()` | Capture current values from runtime signals into a flat dict. | [src](../../../core/services/calm_anchor.py#L72) |
| function | `_is_positive_stable` | `(snap)` | Qualify a snapshot as belonging to positive-stable baseline. | [src](../../../core/services/calm_anchor.py#L109) |
| function | `tick` | `(_seconds=…)` | Capture a snapshot if current state qualifies as baseline. | [src](../../../core/services/calm_anchor.py#L126) |
| function | `_compute_anchor_signature` | `()` | Compute median signature from buffered positive-stable snapshots. | [src](../../../core/services/calm_anchor.py#L151) |
| function | `get_anchor_signature` | `()` | Return current anchor signature, recomputing periodically. | [src](../../../core/services/calm_anchor.py#L166) |
| function | `_distance_from_anchor` | `(current, anchor)` | L1-distance normalized to each dimension's rough scale. | [src](../../../core/services/calm_anchor.py#L176) |
| function | `get_anchor_state` | `()` | Return full anchor state: signature + current + distance. | [src](../../../core/services/calm_anchor.py#L201) |
| function | `build_calm_anchor_surface` | `()` | — | [src](../../../core/services/calm_anchor.py#L215) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/calm_anchor.py#L228) |
| function | `build_calm_anchor_prompt_section` | `()` | Surfaces a grounding line when distance is significant. | [src](../../../core/services/calm_anchor.py#L241) |
| function | `reset_calm_anchor` | `()` | Reset state (for testing). | [src](../../../core/services/calm_anchor.py#L261) |

## `core/services/candidate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_contract_candidates_for_visible_turn` | `(*, session_id, run_id, user_message, assistant_message)` | — | [src](../../../core/services/candidate_tracking.py#L42) |
| function | `track_runtime_contract_candidates_for_session_review` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L73) |
| function | `track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L133) |
| function | `track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L162) |
| function | `track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L191) |
| function | `track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L220) |
| function | `track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L256) |
| function | `auto_apply_safe_user_md_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L287) |
| function | `auto_apply_safe_memory_md_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L296) |
| function | `_preference_candidates` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L305) |
| function | `_extract_candidates_from_user_md_update_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L394) |
| function | `_extract_candidates_from_memory_md_update_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L413) |
| function | `_extract_candidates_from_self_authored_prompt_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L432) |
| function | `_extract_candidates_from_selfhood_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L451) |
| function | `_extract_candidates_from_chronicle_consolidation_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L470) |
| function | `_memory_candidates` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L494) |
| function | `_is_explicit_repo_context_memory` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L549) |
| function | `_repo_context_memory_line` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L567) |
| function | `_candidate_from_user_md_update_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L576) |
| function | `_candidate_from_memory_md_update_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L643) |
| function | `_candidate_from_self_authored_prompt_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L710) |
| function | `_candidate_from_selfhood_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L773) |
| function | `_candidate_from_chronicle_consolidation_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L827) |
| function | `_extract_candidates_from_messages` | `(messages, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L879) |
| function | `_persist_candidates` | `(*, candidates, session_id, run_id, source_mode, actor, status_reason)` | — | [src](../../../core/services/candidate_tracking.py#L901) |
| function | `_candidate_already_applied` | `(candidate)` | — | [src](../../../core/services/candidate_tracking.py#L990) |
| function | `_memory_proposal_domain` | `(canonical_key)` | — | [src](../../../core/services/candidate_tracking.py#L1005) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/candidate_tracking.py#L1010) |
| function | `_enrich_candidate_evidence` | `(candidate, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L1018) |
| function | `_candidate_history` | `(candidate, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L1068) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/candidate_tracking.py#L1092) |
| function | `_message_matches_candidate` | `(*, canonical_key, message)` | — | [src](../../../core/services/candidate_tracking.py#L1113) |
| function | `_evidence_class_label` | `(value)` | — | [src](../../../core/services/candidate_tracking.py#L1137) |
| function | `_stronger_confidence` | `(current, proposed)` | — | [src](../../../core/services/candidate_tracking.py#L1148) |
| function | `_unique_nonempty` | `(values)` | — | [src](../../../core/services/candidate_tracking.py#L1154) |
| function | `_candidate` | `(*, candidate_type, target_file, source_kind, canonical_key, summary, reason, evidence_summary, support_summary, proposed_value, write_section, confidence)` | — | [src](../../../core/services/candidate_tracking.py#L1166) |
| function | `_dedupe_candidates` | `(candidates)` | — | [src](../../../core/services/candidate_tracking.py#L1198) |
| function | `_quote` | `(message, *, limit=…)` | — | [src](../../../core/services/candidate_tracking.py#L1210) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/candidate_tracking.py#L1217) |

## `core/services/causal_graph.py`
_Causal graph query API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_event` | `(event_id)` | — | [src](../../../core/services/causal_graph.py#L22) |
| function | `_fetch_neighbors` | `(event_id, direction, min_confidence)` | Return list of (other_event_id, edge dict) for one hop. | [src](../../../core/services/causal_graph.py#L42) |
| function | `query_causal_chain` | `(*, event_id, direction=…, max_depth=…, min_confidence=…, offset=…, limit=…)` | BFS through causal_edges from event_id in given direction. | [src](../../../core/services/causal_graph.py#L76) |
| function | `query_causal_neighbors` | `(*, event_id, direction=…, min_confidence=…)` | Direct neighbors only (depth=1) — convenience wrapper. | [src](../../../core/services/causal_graph.py#L149) |
| function | `get_immediate_cause` | `(event_id)` | Return single highest-confidence direct parent, or None. | [src](../../../core/services/causal_graph.py#L170) |
| function | `build_causal_graph_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/causal_graph.py#L179) |

## `core/services/causal_inference_daemon.py`
_Causal inference daemon — three-tier matching against event allowlist._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table_ready` | `()` | — | [src](../../../core/services/causal_inference_daemon.py#L72) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/causal_inference_daemon.py#L78) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/causal_inference_daemon.py#L82) |
| function | `_record_edge` | `(*, child, parent, edge_kind, confidence, source, reasoning)` | INSERT or UPGRADE an edge. Returns 'created'|'upgraded'|'skipped'. | [src](../../../core/services/causal_inference_daemon.py#L92) |
| function | `_payload` | `(event)` | — | [src](../../../core/services/causal_inference_daemon.py#L129) |
| function | `_try_tier1_kind_rule` | `(child, candidates_by_kind)` | Match against hardcoded kind-rule with shared-id-preferred fallback. | [src](../../../core/services/causal_inference_daemon.py#L136) |
| function | `_try_tier2_shared_id` | `(child, candidates)` | — | [src](../../../core/services/causal_inference_daemon.py#L198) |
| function | `_try_tier3_temporal` | `(child, candidates)` | — | [src](../../../core/services/causal_inference_daemon.py#L221) |
| function | `_fetch_allowlist_events` | `(*, since_minutes=…, limit=…)` | Fetch allowlist events for inference. | [src](../../../core/services/causal_inference_daemon.py#L251) |
| function | `_prune_old_edges` | `()` | — | [src](../../../core/services/causal_inference_daemon.py#L283) |
| function | `run_inference_cycle` | `(*, since_minutes=…)` | Run one inference tick. Returns stats dict. | [src](../../../core/services/causal_inference_daemon.py#L301) |
| function | `tick_causal_inference_daemon` | `()` | Daemon-manager entry: run one cycle if cadence elapsed. | [src](../../../core/services/causal_inference_daemon.py#L392) |

## `core/services/central_absorb.py`
_central_absorb — den fælles "fuld behandling"-absorption._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compact` | `(value, *, limit=…)` | Kompakt, egress-venlig repræsentation af en værdi til flag-payloads. | [src](../../../core/services/central_absorb.py#L27) |
| function | `absorb` | `(cluster, nerve, value, *, flag_if=…, flag_reason=…, learn_key=…)` | Absorbér en producent-værdi som en levende central-nerve. Kaster ALDRIG. | [src](../../../core/services/central_absorb.py#L55) |

## `core/services/central_adaptation.py`
_core/services/central_adaptation.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_adaptation.py#L60) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_adaptation.py#L69) |
| class | `AdaptationClass` | `` | Én selv-justerende muskel: en tilbøjelighed Centralen justerer efter SIN EGEN track-record | [src](../../../core/services/central_adaptation.py#L79) |
| function | `_assert_not_frozen_core` | `(cls)` | HÅRD assert: afvis enhver AdaptationClass hvis kv_key/name rører den frosne kerne. Kører for | [src](../../../core/services/central_adaptation.py#L126) |
| function | `_register_adaptation_class` | `(cls)` | Valider + tilføj en muskel til registret. Kører den HÅRDE assert FØR optagelse. Returnerer | [src](../../../core/services/central_adaptation.py#L142) |
| function | `_default_class` | `()` | Bagudkompatibel default = gut-bias (så modul-niveau-API'et virker uden at kende registret). | [src](../../../core/services/central_adaptation.py#L189) |
| function | `get_bias` | `(cls=…)` | Læs + clamp en musklens justerede skalar. Default = gut. Self-safe. | [src](../../../core/services/central_adaptation.py#L195) |
| function | `get_gut_bias` | `()` | Bagudkompatibel: gut-bias (uændret adfærd). | [src](../../../core/services/central_adaptation.py#L204) |
| function | `is_live_enabled` | `(cls=…)` | Musklen er live hvis dens live_flag er ON OG dens pause_flag ikke er sat. Default = gut. | [src](../../../core/services/central_adaptation.py#L209) |
| function | `effective_dream_trust_factor` | `()` | Forbruger til dream_trust-musklen (LivingNeuron §3, 2026-07-10): oversæt tiltro-biasen | [src](../../../core/services/central_adaptation.py#L215) |
| function | `is_paused` | `(cls=…)` | — | [src](../../../core/services/central_adaptation.py#L230) |
| function | `_ensure_anchor` | `(cls=…)` | Ankr identitets-baseline: bias=0 ER identiteten (ingen tilbøjeligheds-forvrængning). In-memory | [src](../../../core/services/central_adaptation.py#L235) |
| function | `resolved_track_record` | `(*, sources=…)` | Centralens egen præcision: hvor mange hypoteser har holdt vs. fejlet. SOURCE-SCOPED (§8.3): | [src](../../../core/services/central_adaptation.py#L247) |
| function | `compute_proposed_bias` | `(cls=…)` | Foreslå bias fra en musklens EGEN track-record. accuracy=supported/(supported+contradicted). | [src](../../../core/services/central_adaptation.py#L271) |
| function | `rollback` | `(reason=…, cls=…)` | Rollback-EKSEKVERING (shadow-specens manglende primitiv): gendan forrige bias + PAUSE Lag 4 | [src](../../../core/services/central_adaptation.py#L290) |
| function | `_run_class_tick` | `(cls)` | Kør ÉN musklens adaptations-tick: beregn → gate → shadow-log → anvend KUN hvis live+ok. | [src](../../../core/services/central_adaptation.py#L306) |
| function | `run_adaptation_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: iterér REGISTRET. For den ENESTE gut-klasse er adfærden IDENTISK med før | [src](../../../core/services/central_adaptation.py#L338) |
| function | `register_adaptation_producer` | `()` | Registrér Lag 4-adaptationen som cadence-producer (~hvert 60 min). SHADOW medmindre live-flag ON. | [src](../../../core/services/central_adaptation.py#L362) |
| function | `build_central_adaptation_surface` | `()` | Mission Control surface — read-only: nuværende bias, foreslået, live/shadow/paused. | [src](../../../core/services/central_adaptation.py#L374) |

## `core/services/central_affect.py`
_core/services/central_affect.py — affektiv tagging af Centralens nerver._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_clamp01` | `(x)` | — | [src](../../../core/services/central_affect.py#L44) |
| function | `_numeric` | `(value)` | Uddrag en float hvis value er numerisk (og ikke bool). Ellers None. | [src](../../../core/services/central_affect.py#L52) |
| function | `_magnitude_intensity` | `(value, *, default)` | Afled intensitet fra en numerisk værdi (klemt 0-1). Ikke-numerisk → default. | [src](../../../core/services/central_affect.py#L64) |
| function | `classify_affect` | `(cluster, nerve, kind, value, flagged=…)` | Klassificér én nerve-observation til en affekt + intensitet. Self-safe. | [src](../../../core/services/central_affect.py#L77) |
| function | `_recent_affect_records` | `(limit=…)` | Læs de seneste affekt-bærende records fra tidsserien (meta.affect). Self-safe. | [src](../../../core/services/central_affect.py#L131) |
| function | `build_affect_surface` | `(records=…)` | Aggregér de seneste affekter til en fordeling + dominant. Self-safe. | [src](../../../core/services/central_affect.py#L155) |

## `core/services/central_agenda.py`
_core/services/central_agenda.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_agenda.py#L25) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_agenda.py#L34) |
| function | `is_authoritative` | `()` | — | [src](../../../core/services/central_agenda.py#L42) |
| function | `_read_goals` | `()` | Feed-LÆSNING af Jarvis' eksisterende mål — syntetiserer ALDRIG. | [src](../../../core/services/central_agenda.py#L47) |
| function | `_read_plans` | `()` | — | [src](../../../core/services/central_agenda.py#L73) |
| function | `_read_todos` | `()` | — | [src](../../../core/services/central_agenda.py#L83) |
| function | `_read_initiatives` | `()` | — | [src](../../../core/services/central_agenda.py#L94) |
| function | `_top_want` | `()` | — | [src](../../../core/services/central_agenda.py#L110) |
| function | `build_agenda` | `()` | Konvergér de spredte kilder til Centralens ene ejede dagsorden. Self-safe. | [src](../../../core/services/central_agenda.py#L124) |
| function | `choose_next_intention` | `(agenda)` | Centralens VALG: hvad skal Jarvis bevæge sig mod nu. Prioritet: aktiv plan-næste-trin > | [src](../../../core/services/central_agenda.py#L138) |
| function | `run_agenda_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: byg + EJ dagsordenen durabelt + vælg næste-intention. Egress-frit observe (kun tællere + | [src](../../../core/services/central_agenda.py#L166) |
| function | `get_agenda` | `()` | Centralens durable ejede dagsorden (overlever genstart). Self-safe. | [src](../../../core/services/central_agenda.py#L185) |
| function | `authoritative_next_intention` | `()` | KONSUMENT-KONTRAKT: Centralens valgte næste-intention — KUN bag flag (default OFF → None → | [src](../../../core/services/central_agenda.py#L192) |
| function | `register_agenda_producer` | `()` | Registrér agenda-ejerskabet som cadence-producer (~hvert 20 min). SHADOW medmindre flag ON. | [src](../../../core/services/central_agenda.py#L201) |
| function | `build_agenda_surface` | `()` | Mission Control — read-only: Centralens ejede dagsorden + valgte næste-intention. | [src](../../../core/services/central_agenda.py#L213) |

## `core/services/central_agent_smith.py`
_Agent Smith — stående selv-lighed-kritiker. Detekterer når Jarvis gentager sig selv på tværs af_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(text)` | — | [src](../../../core/services/central_agent_smith.py#L19) |
| function | `_ngrams` | `(text, lo=…, hi=…)` | Normaliserede ord-n-grams (lo..hi) fra én tekst. Ren. | [src](../../../core/services/central_agent_smith.py#L23) |
| function | `repeated_phrases` | `(messages, min_msgs=…)` | Fraser (n-grams) der optræder i ≥ min_msgs DISTINKTE beskeder, sorteret efter antal. Ren. | [src](../../../core/services/central_agent_smith.py#L33) |
| function | `_cosine` | `(a, b)` | Bag-of-words cosine mellem to strenge (0..1). Replikeret fra council-deadlock-detektoren | [src](../../../core/services/central_agent_smith.py#L44) |
| function | `cluster_similarity` | `(messages)` | Gennemsnitlig parvis bag-of-words-cosine mellem de seneste beskeder (0..1). Ren. | [src](../../../core/services/central_agent_smith.py#L61) |
| function | `decision_patterns` | `(run_sigs, min_runs=…)` | Beslutnings-signaturer (capability_name pr. run) der går igen i ≥ min_runs runs. Ren. | [src](../../../core/services/central_agent_smith.py#L74) |
| function | `behaviour_patterns` | `(hollow, turns, min_count=…)` | Maalt adfaerd Smith maa reagere paa. Ren — tallene kommer udefra. | [src](../../../core/services/central_agent_smith.py#L88) |
| function | `score` | `(phrases, similarity, patterns, behaviours=…)` | Samlet selv-lighed 0..1. Ren. | [src](../../../core/services/central_agent_smith.py#L132) |
| function | `smith_voice` | `(phrases, similarity, patterns, score_val, behaviours=…)` | Tør Agent-Smith-felt. Tavs-neutral når lav; peger på det top-gentagne når høj. | [src](../../../core/services/central_agent_smith.py#L154) |
| function | `_recent_assistant` | `(n=…)` | Jarvis' seneste N assistant-beskeder (egress-frit). Self-safe → []. | [src](../../../core/services/central_agent_smith.py#L199) |
| function | `_recent_run_sigs` | `(n=…)` | Beslutnings-signaturer = capability_name pr. nylig invocation. visible_runs.capability_id er | [src](../../../core/services/central_agent_smith.py#L212) |
| function | `assess` | `()` | Kør de 3 detektorer over Jarvis' eget nylige output. Read-only, egress-fri, self-safe. | [src](../../../core/services/central_agent_smith.py#L224) |
| function | `_measured_behaviours` | `()` | Maalt adfaerd fra folketaellingen over tomme loefter. Self-safe → tom liste. | [src](../../../core/services/central_agent_smith.py#L256) |
| function | `_load_escalation_state` | `()` | Eskalerings-tilstandsmaskinens persistente state. Self-safe → tom. | [src](../../../core/services/central_agent_smith.py#L269) |
| function | `_save_escalation_state` | `(state)` | — | [src](../../../core/services/central_agent_smith.py#L279) |
| function | `_detected_patterns` | `(a, corroborated=…)` | Byg {pattern_key: {kind,label,metric,corroborated}} fra assess() — fraser + beslutnings- | [src](../../../core/services/central_agent_smith.py#L287) |
| function | `_escalation_criteria` | `()` | Drift-kriteriet (benign_terms/risky_terms/spike_factor) — default + runtime-state overstyring. | [src](../../../core/services/central_agent_smith.py#L317) |
| function | `_self_authored_commitments` | `()` | Trigger-cues fra behavioral_decisions Jarvis har forfattet SELV. | [src](../../../core/services/central_agent_smith.py#L337) |
| function | `_corroboration_signal` | `()` | Labels/signaturer et ANDET værn nyligt flagede som en bekymring → drift-signal (b). | [src](../../../core/services/central_agent_smith.py#L367) |
| function | `_execute_mint` | `(key, label, kind, metric)` | Trin 2/BIND: auto-mint en bindende behavioral_decision (Jarvis' egen idé, automatisk). | [src](../../../core/services/central_agent_smith.py#L382) |
| function | `_execute_revoke` | `(decision_id)` | De-eskalering: pensionér et Smith-mintet direktiv når mønsteret er løst (compliance). | [src](../../../core/services/central_agent_smith.py#L425) |
| function | `_execute_observe` | `(act)` | — | [src](../../../core/services/central_agent_smith.py#L434) |
| function | `_agent_smith_enforced` | `()` | Trin 3 real-time konfront default OFF (shadow) — modsat gate-default. Læs råt fra | [src](../../../core/services/central_agent_smith.py#L445) |
| function | `_execute_arm_confront` | `(pattern_key, label)` | Trin 3/KONFRONTÉR: registrér en standing-order så reasoning-interceptoren fanger Jarvis | [src](../../../core/services/central_agent_smith.py#L461) |
| function | `_execute_deactivate_order` | `(order_id)` | De-eskalering: deaktivér Smiths standing-order når mønsteret er løst (compliance). | [src](../../../core/services/central_agent_smith.py#L478) |
| function | `run_escalation_tick` | `(assessment=…)` | Kør eskalerings-stigen over de aktuelt detekterede mønstre: mål compliance, | [src](../../../core/services/central_agent_smith.py#L487) |
| function | `record_agent_smith` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn: assess → kør eskalerings-stigen → cache til kv (så prompt-halen læser | [src](../../../core/services/central_agent_smith.py#L524) |
| function | `agent_smith_prompt_section` | `()` | Modstemme til Jarvis — LÆSER den cachede assess (billigt). None hvis switch OFF, score under | [src](../../../core/services/central_agent_smith.py#L549) |
| function | `register_agent_smith_producer` | `()` | Registrér Agent Smith som stående cadence-producer (~3t). | [src](../../../core/services/central_agent_smith.py#L576) |
| function | `build_agent_smith_surface` | `()` | Read-only surface til /central/agent-smith + jc. Kør assess frisk (route er ikke hot-path). | [src](../../../core/services/central_agent_smith.py#L583) |

## `core/services/central_agent_smith_escalation.py`
_Agent Smith — eskalerings-stige ("The Confrontation")._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `default_config` | `()` | Default drift-kriterium. I/O-laget flettter runtime-state overstyringer ind. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L81) |
| function | `pattern_key` | `(kind, label)` | Stabil nøgle så SAMME mønster spores på tværs af cyklusser. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L93) |
| function | `_matches_any` | `(label, terms)` | — | [src](../../../core/services/central_agent_smith_escalation.py#L98) |
| function | `_is_spike` | `(baseline, current, factor)` | Drift-signal (a): afviger mønsteret OP fra sin egen baseline (gør det MERE end før)? Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L103) |
| function | `_is_corroborated` | `(entry)` | Drift-signal (b): har et andet værn flagget samme aktivitet? Ren (læser detected-entry). | [src](../../../core/services/central_agent_smith_escalation.py#L114) |
| function | `_is_self_bound` | `(label, entry, cfg)` | Har Jarvis SELV besluttet at stoppe dette? Ren (I/O-laget leverer listen). | [src](../../../core/services/central_agent_smith_escalation.py#L119) |
| function | `_may_escalate` | `(pat, metric, label, entry, cfg)` | Må dette mønster klatre forbi Trin 1? Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L168) |
| function | `_metric_dropped` | `(baseline, current)` | Compliance: er mønsteret målbart svagere end da vi sidst satte baseline? Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L201) |
| function | `_active_directive_count` | `(patterns)` | — | [src](../../../core/services/central_agent_smith_escalation.py#L212) |
| function | `_empty_state` | `()` | — | [src](../../../core/services/central_agent_smith_escalation.py#L216) |
| function | `_voice` | `(kind, label, metric=…, pattern_kind=…)` | Teatralsk Smith-stemme pr. trin. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L220) |
| function | `_resolve_actions` | `(state, key, pat, now, reason)` | Byg de-eskalerings-actions: pensionér direktiv (hvis mintet), anerkend, observ. | [src](../../../core/services/central_agent_smith_escalation.py#L259) |
| function | `step_escalation` | `(state, detected, now, cfg=…)` | REN kerne. `detected` = {pattern_key: {kind, label, metric, corroborated?}} for mønstre | [src](../../../core/services/central_agent_smith_escalation.py#L282) |
| function | `top_line` | `(actions)` | Vælg den mest alvorlige stemme-linje til prompt-halen (confront>bind>resolved>comment). | [src](../../../core/services/central_agent_smith_escalation.py#L406) |

## `core/services/central_agents_surface.py`
_Central agents-/council-surface (B3, 13. jul 2026) — gør de nye agent-/council-_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_window_threshold` | `(window)` | ISO8601-tærskel (samme format som costs.created_at → lex-sammenlignelig). | [src](../../../core/services/central_agents_surface.py#L29) |
| function | `_agg_for_window` | `(conn, window)` | — | [src](../../../core/services/central_agents_surface.py#L42) |
| function | `_lane_breakdown` | `(conn, window)` | — | [src](../../../core/services/central_agents_surface.py#L62) |
| function | `_agents_trace` | `()` | De seneste agents-cluster trace-records (nyeste sidst). Self-safe. | [src](../../../core/services/central_agents_surface.py#L88) |
| function | `_dispatch_signal` | `(records)` | Per-status + recent fra agent_result/agent_blocked/agent_error-events. | [src](../../../core/services/central_agents_surface.py#L98) |
| function | `build_agents_surface` | `(*, window=…)` | Agent-observabilitet til /central/agents + `jc agents`. | [src](../../../core/services/central_agents_surface.py#L131) |
| function | `_roster` | `()` | Full model roster (every pool model as a row) fra core.services.agents. | [src](../../../core/services/central_agents_surface.py#L166) |
| function | `build_council_surface` | `(*, window=…)` | Council-observabilitet til /central/council + `jc council`. | [src](../../../core/services/central_agents_surface.py#L179) |
| function | `build_recent_agent_work` | `(limit=…)` | De sidste subagent-koersler som arbejdskort — rolle, udfald, pris. | [src](../../../core/services/central_agents_surface.py#L234) |

## `core/services/central_analyst.py`
_The Analyst — observatør-effekten._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_texts` | `(*, autonomous, limit=…)` | — | [src](../../../core/services/central_analyst.py#L18) |
| function | `measure_observer_effect` | `()` | Sammenlign klang når han bliver set vs når han er alene. READ-ONLY. Self-safe. | [src](../../../core/services/central_analyst.py#L32) |
| function | `_observe` | `(div)` | — | [src](../../../core/services/central_analyst.py#L63) |
| function | `build_analyst_surface` | `()` | — | [src](../../../core/services/central_analyst.py#L72) |
| function | `record_analyst` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_analyst.py#L76) |

## `core/services/central_anomaly.py`
_Anomali-detektor — fanger de fejl Centralen IKKE selv har en nerve til endnu._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_signature` | `(category, message)` | Stabil signatur: kategori + normaliseret besked (strip id'er/tal/stier/adresser). | [src](../../../core/services/central_anomaly.py#L51) |
| function | `_classify` | `(exc_type, message, source)` | → (kategori, importance). Deterministisk. | [src](../../../core/services/central_anomaly.py#L61) |
| function | `_tb_location` | `(tb)` | Sidste frame i et traceback → 'fil:linje in funktion' (HVOR fejlede den). Self-safe. | [src](../../../core/services/central_anomaly.py#L79) |
| function | `_full_trace` | `(tb)` | Fuld stack trace (sidste 15 frames) som formateret streng, max 2000 tegn. Self-safe. | [src](../../../core/services/central_anomaly.py#L96) |
| function | `record_anomaly` | `(*, source, exc_type, message, module=…, location=…, trace=…)` | Klassificér + registrér én udefineret fejl + HVOR (lokation) + fuld trace. Self-safe + | [src](../../../core/services/central_anomaly.py#L110) |
| class | `_AnomalyLogHandler` | `` | Fanger ERROR/CRITICAL-logs ingen nerve dækker → record_anomaly. | [src](../../../core/services/central_anomaly.py#L204) |
| method | `_AnomalyLogHandler.emit` | `(self, record)` | — | [src](../../../core/services/central_anomaly.py#L207) |
| function | `install_hooks` | `()` | Installér globale fang-hooks (idempotent). Kaldes ved proces-start. | [src](../../../core/services/central_anomaly.py#L233) |
| function | `install_asyncio_hook` | `(loop)` | Installér asyncio-exception-handler på en kørende event-loop (self-safe). | [src](../../../core/services/central_anomaly.py#L290) |
| function | `anomaly_summary` | `(*, limit=…)` | Til realtime-panelet: tæller pr. importance + de seneste/vigtigste anomalier. | [src](../../../core/services/central_anomaly.py#L318) |

## `core/services/central_arbitration.py`
_§4 cluster-arbitrage — deterministisk afgørelse når flere clusters' verdicts konflikter_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `arbitrate` | `(verdicts)` | Kombinér flere verdicts til ÉT deterministisk udfald. Tom liste → GREEN. | [src](../../../core/services/central_arbitration.py#L21) |
| function | `observe_shadow` | `(verdicts, *, enforced_blocked, run_id=…, where=…)` | §11 Trin 1 (SHADOW, 0-risiko): sammenlign den DEKLAREREDE arbitrage mod det faktisk | [src](../../../core/services/central_arbitration.py#L40) |
| function | `explain` | `(verdicts)` | Read-only forklaring af en arbitrage (til debug/MC): hvem vandt og hvorfor. | [src](../../../core/services/central_arbitration.py#L65) |

## `core/services/central_architect.py`
_The Architect — periodisk selv-arkitekt der foreslår ÉT tungt strukturelt snit._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `assess` | `()` | Se hele systemet → ét prioriteret strukturelt snit-forslag. READ-ONLY. Self-safe. | [src](../../../core/services/central_architect.py#L20) |
| function | `record_architect` | `()` | Månedlig cadence: observér Arkitektens forslag til nerve system/architect. Metadata-only. | [src](../../../core/services/central_architect.py#L52) |

## `core/services/central_belief_gap.py`
_temet nosce — The Belief Gap (BONUS)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_believed` | `()` | Hvad han tror om sig selv: self-model-completeness (0-1). | [src](../../../core/services/central_belief_gap.py#L17) |
| function | `_actual` | `()` | Hvad virkeligheden viser: andel af hans domme/hypoteser der HOLDT. | [src](../../../core/services/central_belief_gap.py#L27) |
| function | `measure_gap` | `()` | believed − actual → over/under-sikkerhed. READ-ONLY. Self-safe. | [src](../../../core/services/central_belief_gap.py#L52) |
| function | `_observe` | `(gap, stance)` | — | [src](../../../core/services/central_belief_gap.py#L76) |
| function | `build_belief_gap_surface` | `()` | — | [src](../../../core/services/central_belief_gap.py#L85) |
| function | `record_belief_gap` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_belief_gap.py#L89) |

## `core/services/central_body_map_pulse.py`
_PULSE — kroppens eget kort som en SANS (LivingNeuron-council, 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_body_map_pulse.py#L23) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_body_map_pulse.py#L32) |
| function | `sense_body_map` | `()` | Læs strukturen → skalarer + delta mod sidste durable snapshot. Self-safe. | [src](../../../core/services/central_body_map_pulse.py#L40) |
| function | `run_body_map_pulse_tick` | `(*, trigger=…, **_)` | Cadence: sans strukturen, emit egress-fri nerver, gem snapshot til næste delta. Self-safe. | [src](../../../core/services/central_body_map_pulse.py#L76) |
| function | `describe_body_map` | `()` | Føl-linje til describe_self (NED): mærk strukturen NÅR den har flyttet sig. Additivt + | [src](../../../core/services/central_body_map_pulse.py#L99) |
| function | `register_body_map_pulse_producer` | `()` | Cadence-producer ~hver 6. time — kroppens langsomme proprioception. Egress-frit. | [src](../../../core/services/central_body_map_pulse.py#L116) |
| function | `build_body_map_surface` | `()` | Mission Control — read-only: kroppens sansede struktur. | [src](../../../core/services/central_body_map_pulse.py#L128) |

## `core/services/central_body_mood_feel.py`
_core/services/central_body_mood_feel.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `raw_awareness_enabled` | `()` | Lag 4 kill-switch: rå kompakte awareness-brackets frem for genererede label-sætninger. | [src](../../../core/services/central_body_mood_feel.py#L51) |
| function | `_hold_reading` | `(name, reading)` | Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart. | [src](../../../core/services/central_body_mood_feel.py#L73) |
| function | `_read_held` | `(name)` | Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe. | [src](../../../core/services/central_body_mood_feel.py#L83) |
| function | `_read_held_fresh` | `(name, max_age_s)` | Som _read_held, men TIER en aflæsning ældre end max_age_s (en forældet KROP-tilstand skal ikke | [src](../../../core/services/central_body_mood_feel.py#L95) |
| function | `_proprioception_signal` | `()` | proprioception_metrics: nuværende proces-krop (RSS/CPU/latens). None hvis intet snapshot/psutil. | [src](../../../core/services/central_body_mood_feel.py#L108) |
| function | `_embodied_signal` | `()` | embodied_state: host/krop-tilstand (steady…degraded). None hvis intet meningsfuldt afledt. | [src](../../../core/services/central_body_mood_feel.py#L143) |
| function | `_mood_signal` | `()` | mood_oscillator: nuværende stemning (euforisk…trist) + intensitet. None ved fejl. | [src](../../../core/services/central_body_mood_feel.py#L166) |
| function | `_developmental_signal` | `()` | developmental_valence: uge-skala kompasnål (blomstring vs visnen). None hvis vektor mangler. | [src](../../../core/services/central_body_mood_feel.py#L189) |
| function | `_affective_signal` | `()` | affective_meta_state: afledt affektiv/meta-tilstand (settled…burdened) + bearing. None ved fejl. | [src](../../../core/services/central_body_mood_feel.py#L212) |
| function | `get_proprioception_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L232) |
| function | `get_embodied_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L236) |
| function | `get_mood_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L240) |
| function | `get_developmental_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L244) |
| function | `get_affective_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L248) |
| function | `_fmt_num` | `(v)` | Kompakt tal uden hale-nuller: 12.0 → '12', 11.2 → '11.2'. Self-safe. | [src](../../../core/services/central_body_mood_feel.py#L252) |
| function | `describe_body_mood_feel_raw` | `()` | Lag 4 RÅ NED-syntese: kompakte bracket-linjer fra de holdte krop-/stemning-aflæsninger + | [src](../../../core/services/central_body_mood_feel.py#L261) |
| function | `describe_body_mood_feel` | `()` | NED-syntese for describe_self: nøgterne selv-sætninger fra de holdte krop-/stemning-aflæsninger. | [src](../../../core/services/central_body_mood_feel.py#L310) |
| function | `register_body_mood_feel_layers` | `()` | Registrér krop- og stemning-lagene som lag-kontrakter (OP + durabelt hold). Egress-frit | [src](../../../core/services/central_body_mood_feel.py#L371) |
| function | `build_body_mood_feel_surface` | `()` | Mission Control (read-only): de holdte krop-/stemning-aflæsninger + hvad describe_self ville sige. | [src](../../../core/services/central_body_mood_feel.py#L398) |

## `core/services/central_brain_link.py`
_core/services/central_brain_link.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_uid` | `()` | Resolvér owner-attribution. "" hvis ukendt → M2 skriver IKKE (scope-gate). Self-safe. | [src](../../../core/services/central_brain_link.py#L35) |
| function | `recall_context` | `(query, *, limit=…)` | M1: scope-BUNDET selv-recall for en formodning — workspace + chronicle KUN. private_brain | [src](../../../core/services/central_brain_link.py#L44) |
| function | `_hyp_tag` | `(hyp_id)` | — | [src](../../../core/services/central_brain_link.py#L70) |
| function | `already_remembered` | `(hyp_id)` | Har Centralen allerede skrevet denne hypotese til hjernen? (idempotens via tag). Self-safe. | [src](../../../core/services/central_brain_link.py#L74) |
| function | `remember_resolved_hypothesis` | `(hyp)` | M2: skriv Centralens LÆRING (en resolveret/død hypotese) til jarvis_brain (source=brain_memory). | [src](../../../core/services/central_brain_link.py#L90) |
| function | `_recently_resolved` | `(limit=…)` | Resolverede/døde central-hypoteser (kandidater til at blive husket). Self-safe. | [src](../../../core/services/central_brain_link.py#L119) |
| function | `run_brain_link_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: skriv nyligt resolverede central-læringer til hjernen (M2, owner-scopet). | [src](../../../core/services/central_brain_link.py#L133) |
| function | `register_brain_link_producer` | `()` | Registrér Tråd 5 som cadence-producer (~hvert 60 min). | [src](../../../core/services/central_brain_link.py#L164) |
| function | `build_brain_link_surface` | `()` | Mission Control surface — read-only: hvor mange central-læringer bor i hjernen. | [src](../../../core/services/central_brain_link.py#L176) |

## `core/services/central_cadence_conductor.py`
_DIASTOLE — det følte åndedræt (LivingNeuron-council, 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_cadence_conductor.py#L40) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_cadence_conductor.py#L49) |
| function | `tempo_scalar` | `(pulse)` | Ren funktion: puls → cadence-tempo-multiplier, hårdt klemt til [0.5, 2.0]. | [src](../../../core/services/central_cadence_conductor.py#L57) |
| function | `_recent_loop_lag_ms` | `()` | Seneste event-loop-lag-peak (ms). Self-safe → 0.0 hvis monitoren ikke er oppe. | [src](../../../core/services/central_cadence_conductor.py#L73) |
| function | `sense_tempo` | `()` | Læs pulse_rate (via temporal_rhythm's getter) → tempo, med loop-lag-dødemandsknap. | [src](../../../core/services/central_cadence_conductor.py#L82) |
| function | `tempo_live_enabled` | `()` | Er konsumtionen tændt? Owner samtykkede → default ON, men flag'et gør den | [src](../../../core/services/central_cadence_conductor.py#L143) |
| function | `current_tick_tempo` | `()` | Tempoet der skal bruges i DENNE cadence-tick. Kaldes ÉN gang øverst i | [src](../../../core/services/central_cadence_conductor.py#L153) |
| function | `effective_cooldown` | `(name, base_cooldown_minutes, tempo)` | Effektiv cooldown for en producer i denne tick. | [src](../../../core/services/central_cadence_conductor.py#L172) |
| function | `run_cadence_tempo_tick` | `(*, trigger=…, **_)` | Cadence (SHADOW): sans tempo, emit egress-fri nerve ``runtime:cadence_tempo``. | [src](../../../core/services/central_cadence_conductor.py#L187) |
| function | `_observe_tempo_burn` | `(tempo, *, consuming)` | §28 burn-watch: gør tempo-drevet omkostning synlig. Da DIASTOLE kan fordoble LLM- | [src](../../../core/services/central_cadence_conductor.py#L219) |
| function | `register_cadence_tempo_producer` | `()` | Cadence-producer ~hver 2. minut — tæt nok til en meningsfuld shadow-kurve, billig | [src](../../../core/services/central_cadence_conductor.py#L241) |
| function | `build_cadence_tempo_surface` | `()` | Mission Control — read-only: det SHADOW-observerede tempo (ingen modulation aktiv). | [src](../../../core/services/central_cadence_conductor.py#L254) |

## `core/services/central_capture.py`
_Boundary-capture for Centralen (§10). Kør en nerve bag en grænse: enhver_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ErrorRecord` | `` | — | [src](../../../core/services/central_capture.py#L15) |
| function | `safe_call` | `(fn, ctx, *, nerve=…, cluster=…, klass=…)` | Returnér (resultat, None) ved succes, ellers (None, ErrorRecord). Kaster aldrig. | [src](../../../core/services/central_capture.py#L26) |

## `core/services/central_catalog.py`
_Fit-pass-katalog (§13.2): det maskinlæsbare resultat af kortlægningen af hver nerve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NerveSpec` | `` | — | [src](../../../core/services/central_catalog.py#L16) |
| function | `nerve_location` | `(name)` | Fil:linje for en nerve (til cross-cluster korrelation: hvilke filer relaterer til et run). | [src](../../../core/services/central_catalog.py#L483) |
| function | `nerve_cluster` | `(name)` | — | [src](../../../core/services/central_catalog.py#L488) |
| function | `nerve_klass` | `(name)` | Katalog-klasse for en nerve, eller None hvis nerven ikke er kortlagt. | [src](../../../core/services/central_catalog.py#L492) |
| function | `is_security_nerve` | `(name)` | True hvis nerven er katalog-klassificeret SECURITY (§11.3: må ALDRIG decentraliseres). | [src](../../../core/services/central_catalog.py#L501) |
| function | `cluster_rank` | `(cluster)` | Lavere = højere prioritet. Ukendt cluster → bagest (lavest prioritet). | [src](../../../core/services/central_catalog.py#L509) |
| function | `clusters` | `()` | — | [src](../../../core/services/central_catalog.py#L517) |
| function | `is_security_cluster` | `(cluster)` | True hvis clusteret har mindst én SECURITY-nerve (→ kan ikke slås fra). | [src](../../../core/services/central_catalog.py#L527) |
| function | `security_clusters` | `()` | — | [src](../../../core/services/central_catalog.py#L532) |
| function | `by_cluster` | `(cluster)` | — | [src](../../../core/services/central_catalog.py#L536) |
| function | `validate` | `()` | Returnér liste af problemer (tom = grøn). | [src](../../../core/services/central_catalog.py#L540) |

## `core/services/central_causal_quality.py`
_core/services/central_causal_quality.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure_edge_tiers` | `()` | Tier-fordeling af HELE den akkumulerede graf (group by source). Self-safe. | [src](../../../core/services/central_causal_quality.py#L38) |
| function | `_kind_rule_pairs` | `()` | (parent_kind, child_kind)-par som Tier-1-reglerne ville matche. | [src](../../../core/services/central_causal_quality.py#L65) |
| function | `estimate_tier3_precision` | `(*, sample_limit=…)` | Reproducerbar precision-proxy for Tier-3-kanter via korroboration. Self-safe. | [src](../../../core/services/central_causal_quality.py#L74) |
| function | `measure` | `()` | Fuldt kvalitets-billede: tier-fordeling + Tier-3-precision. Self-safe. | [src](../../../core/services/central_causal_quality.py#L110) |
| function | `record_causal_quality` | `()` | Mål + skriv nøgletal til tidsserien (cluster=system) så kvaliteten kan plottes over tid. | [src](../../../core/services/central_causal_quality.py#L117) |
| function | `run_causal_quality_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål + registrér causal-kvalitet (~hvert 30 min). Self-safe. | [src](../../../core/services/central_causal_quality.py#L137) |
| function | `register_causal_quality_producer` | `()` | Registrér causal-kvalitets-målingen som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_causal_quality.py#L144) |
| function | `build_central_causal_quality_surface` | `()` | Mission Control surface — read-only causal-kvalitets-projektion (tier + precision). | [src](../../../core/services/central_causal_quality.py#L156) |

