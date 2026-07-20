# `core.services.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `get_cache_maintenance_stats` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L150) |
| function | `build_cache_maintenance_surface` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L157) |

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
| function | `produce_emergent_signals_from_history` | `()` | Run the emergent signal daemon to scan timeline for patterns. | [src](../../../core/services/cadence_producers.py#L569) |
| function | `detect_decision_in_message` | `(*, user_message, assistant_response, run_id)` | Detect decisions in conversation and log them. | [src](../../../core/services/cadence_producers.py#L584) |
| function | `run_adoption_pipelines` | `()` | Move things from candidate → adopted state. | [src](../../../core/services/cadence_producers.py#L618) |
| function | `sync_personality_to_self_model` | `()` | Bridge: sync personality_vector changes to self_model_signal. | [src](../../../core/services/cadence_producers.py#L649) |
| function | `progress_signal_lifecycles` | `()` | Move signals through lifecycle stages: active → carried → fading → released. | [src](../../../core/services/cadence_producers.py#L727) |
| function | `_observe_frozen` | `(nerve, meta)` | EGRESS-FRI liveness for en vækket frossen detektor (rettet 2026-07-01: var central().observe). | [src](../../../core/services/cadence_producers.py#L762) |
| function | `tick_frozen_detectors` | `(tick_count)` | LivingNeuron Fase B: væk de frosne detektorer på LAV cadence (deres consumers sultede på | [src](../../../core/services/cadence_producers.py#L771) |
| function | `build_cadence_producers_surface` | `()` | MC surface for cadence producer status. | [src](../../../core/services/cadence_producers.py#L828) |

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
| function | `track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L250) |
| function | `auto_apply_safe_user_md_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L281) |
| function | `auto_apply_safe_memory_md_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/candidate_tracking.py#L290) |
| function | `_preference_candidates` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L299) |
| function | `_extract_candidates_from_user_md_update_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L388) |
| function | `_extract_candidates_from_memory_md_update_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L407) |
| function | `_extract_candidates_from_self_authored_prompt_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L426) |
| function | `_extract_candidates_from_selfhood_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L445) |
| function | `_extract_candidates_from_chronicle_consolidation_proposals` | `()` | — | [src](../../../core/services/candidate_tracking.py#L464) |
| function | `_memory_candidates` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L488) |
| function | `_is_explicit_repo_context_memory` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L543) |
| function | `_repo_context_memory_line` | `(message)` | — | [src](../../../core/services/candidate_tracking.py#L561) |
| function | `_candidate_from_user_md_update_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L570) |
| function | `_candidate_from_memory_md_update_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L637) |
| function | `_candidate_from_self_authored_prompt_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L704) |
| function | `_candidate_from_selfhood_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L767) |
| function | `_candidate_from_chronicle_consolidation_proposal` | `(proposal)` | — | [src](../../../core/services/candidate_tracking.py#L820) |
| function | `_extract_candidates_from_messages` | `(messages, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L872) |
| function | `_persist_candidates` | `(*, candidates, session_id, run_id, source_mode, actor, status_reason)` | — | [src](../../../core/services/candidate_tracking.py#L894) |
| function | `_candidate_already_applied` | `(candidate)` | — | [src](../../../core/services/candidate_tracking.py#L983) |
| function | `_memory_proposal_domain` | `(canonical_key)` | — | [src](../../../core/services/candidate_tracking.py#L998) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/candidate_tracking.py#L1003) |
| function | `_enrich_candidate_evidence` | `(candidate, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L1011) |
| function | `_candidate_history` | `(candidate, *, session_id)` | — | [src](../../../core/services/candidate_tracking.py#L1061) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/candidate_tracking.py#L1085) |
| function | `_message_matches_candidate` | `(*, canonical_key, message)` | — | [src](../../../core/services/candidate_tracking.py#L1106) |
| function | `_evidence_class_label` | `(value)` | — | [src](../../../core/services/candidate_tracking.py#L1130) |
| function | `_stronger_confidence` | `(current, proposed)` | — | [src](../../../core/services/candidate_tracking.py#L1141) |
| function | `_unique_nonempty` | `(values)` | — | [src](../../../core/services/candidate_tracking.py#L1147) |
| function | `_candidate` | `(*, candidate_type, target_file, source_kind, canonical_key, summary, reason, evidence_summary, support_summary, proposed_value, write_section, confidence)` | — | [src](../../../core/services/candidate_tracking.py#L1159) |
| function | `_dedupe_candidates` | `(candidates)` | — | [src](../../../core/services/candidate_tracking.py#L1191) |
| function | `_quote` | `(message, *, limit=…)` | — | [src](../../../core/services/candidate_tracking.py#L1203) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/candidate_tracking.py#L1210) |

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
| function | `_read_goals` | `()` | — | [src](../../../core/services/central_agenda.py#L47) |
| function | `_read_plans` | `()` | — | [src](../../../core/services/central_agenda.py#L61) |
| function | `_read_todos` | `()` | — | [src](../../../core/services/central_agenda.py#L71) |
| function | `_read_initiatives` | `()` | — | [src](../../../core/services/central_agenda.py#L82) |
| function | `_top_want` | `()` | — | [src](../../../core/services/central_agenda.py#L98) |
| function | `build_agenda` | `()` | Konvergér de spredte kilder til Centralens ene ejede dagsorden. Self-safe. | [src](../../../core/services/central_agenda.py#L112) |
| function | `choose_next_intention` | `(agenda)` | Centralens VALG: hvad skal Jarvis bevæge sig mod nu. Prioritet: aktiv plan-næste-trin > | [src](../../../core/services/central_agenda.py#L126) |
| function | `run_agenda_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: byg + EJ dagsordenen durabelt + vælg næste-intention. Egress-frit observe (kun tællere + | [src](../../../core/services/central_agenda.py#L154) |
| function | `get_agenda` | `()` | Centralens durable ejede dagsorden (overlever genstart). Self-safe. | [src](../../../core/services/central_agenda.py#L173) |
| function | `authoritative_next_intention` | `()` | KONSUMENT-KONTRAKT: Centralens valgte næste-intention — KUN bag flag (default OFF → None → | [src](../../../core/services/central_agenda.py#L180) |
| function | `register_agenda_producer` | `()` | Registrér agenda-ejerskabet som cadence-producer (~hvert 20 min). SHADOW medmindre flag ON. | [src](../../../core/services/central_agenda.py#L189) |
| function | `build_agenda_surface` | `()` | Mission Control — read-only: Centralens ejede dagsorden + valgte næste-intention. | [src](../../../core/services/central_agenda.py#L201) |

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
| function | `score` | `(phrases, similarity, patterns)` | Samlet selv-lighed 0..1 (vægtet: cosine-klynge + frase-tæthed + sekvens-gentagelse). Ren. | [src](../../../core/services/central_agent_smith.py#L82) |
| function | `smith_voice` | `(phrases, similarity, patterns, score_val)` | Tør Agent-Smith-felt. Tavs-neutral når lav; peger på det top-gentagne når høj. | [src](../../../core/services/central_agent_smith.py#L90) |
| function | `_recent_assistant` | `(n=…)` | Jarvis' seneste N assistant-beskeder (egress-frit). Self-safe → []. | [src](../../../core/services/central_agent_smith.py#L125) |
| function | `_recent_run_sigs` | `(n=…)` | Beslutnings-signaturer = capability_name pr. nylig invocation. visible_runs.capability_id er | [src](../../../core/services/central_agent_smith.py#L138) |
| function | `assess` | `()` | Kør de 3 detektorer over Jarvis' eget nylige output. Read-only, egress-fri, self-safe. | [src](../../../core/services/central_agent_smith.py#L150) |
| function | `_load_escalation_state` | `()` | Eskalerings-tilstandsmaskinens persistente state. Self-safe → tom. | [src](../../../core/services/central_agent_smith.py#L166) |
| function | `_save_escalation_state` | `(state)` | — | [src](../../../core/services/central_agent_smith.py#L176) |
| function | `_detected_patterns` | `(a, corroborated=…)` | Byg {pattern_key: {kind,label,metric,corroborated}} fra assess() — fraser + beslutnings- | [src](../../../core/services/central_agent_smith.py#L184) |
| function | `_escalation_criteria` | `()` | Drift-kriteriet (benign_terms/risky_terms/spike_factor) — default + runtime-state overstyring. | [src](../../../core/services/central_agent_smith.py#L205) |
| function | `_corroboration_signal` | `()` | Labels/signaturer et ANDET værn nyligt flagede som en bekymring → drift-signal (b). | [src](../../../core/services/central_agent_smith.py#L224) |
| function | `_execute_mint` | `(key, label, kind, metric)` | Trin 2/BIND: auto-mint en bindende behavioral_decision (Jarvis' egen idé, automatisk). | [src](../../../core/services/central_agent_smith.py#L239) |
| function | `_execute_revoke` | `(decision_id)` | De-eskalering: pensionér et Smith-mintet direktiv når mønsteret er løst (compliance). | [src](../../../core/services/central_agent_smith.py#L272) |
| function | `_execute_observe` | `(act)` | — | [src](../../../core/services/central_agent_smith.py#L281) |
| function | `_agent_smith_enforced` | `()` | Trin 3 real-time konfront default OFF (shadow) — modsat gate-default. Læs råt fra | [src](../../../core/services/central_agent_smith.py#L292) |
| function | `_execute_arm_confront` | `(pattern_key, label)` | Trin 3/KONFRONTÉR: registrér en standing-order så reasoning-interceptoren fanger Jarvis | [src](../../../core/services/central_agent_smith.py#L308) |
| function | `_execute_deactivate_order` | `(order_id)` | De-eskalering: deaktivér Smiths standing-order når mønsteret er løst (compliance). | [src](../../../core/services/central_agent_smith.py#L325) |
| function | `run_escalation_tick` | `(assessment=…)` | Kør eskalerings-stigen over de aktuelt detekterede mønstre: mål compliance, | [src](../../../core/services/central_agent_smith.py#L334) |
| function | `record_agent_smith` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn: assess → kør eskalerings-stigen → cache til kv (så prompt-halen læser | [src](../../../core/services/central_agent_smith.py#L371) |
| function | `agent_smith_prompt_section` | `()` | Modstemme til Jarvis — LÆSER den cachede assess (billigt). None hvis switch OFF, score under | [src](../../../core/services/central_agent_smith.py#L396) |
| function | `register_agent_smith_producer` | `()` | Registrér Agent Smith som stående cadence-producer (~3t). | [src](../../../core/services/central_agent_smith.py#L423) |
| function | `build_agent_smith_surface` | `()` | Read-only surface til /central/agent-smith + jc. Kør assess frisk (route er ikke hot-path). | [src](../../../core/services/central_agent_smith.py#L430) |

## `core/services/central_agent_smith_escalation.py`
_Agent Smith — eskalerings-stige ("The Confrontation")._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `default_config` | `()` | Default drift-kriterium. I/O-laget flettter runtime-state overstyringer ind. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L68) |
| function | `pattern_key` | `(kind, label)` | Stabil nøgle så SAMME mønster spores på tværs af cyklusser. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L77) |
| function | `_matches_any` | `(label, terms)` | — | [src](../../../core/services/central_agent_smith_escalation.py#L82) |
| function | `_is_spike` | `(baseline, current, factor)` | Drift-signal (a): afviger mønsteret OP fra sin egen baseline (gør det MERE end før)? Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L87) |
| function | `_is_corroborated` | `(entry)` | Drift-signal (b): har et andet værn flagget samme aktivitet? Ren (læser detected-entry). | [src](../../../core/services/central_agent_smith_escalation.py#L98) |
| function | `_may_escalate` | `(pat, metric, label, entry, cfg)` | Må dette mønster klatre forbi Trin 1? KUN med et ægte drift-signal. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L103) |
| function | `_metric_dropped` | `(baseline, current)` | Compliance: er mønsteret målbart svagere end da vi sidst satte baseline? Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L117) |
| function | `_active_directive_count` | `(patterns)` | — | [src](../../../core/services/central_agent_smith_escalation.py#L128) |
| function | `_empty_state` | `()` | — | [src](../../../core/services/central_agent_smith_escalation.py#L132) |
| function | `_voice` | `(kind, label, metric=…)` | Teatralsk Smith-stemme pr. trin. Ren. | [src](../../../core/services/central_agent_smith_escalation.py#L136) |
| function | `_resolve_actions` | `(state, key, pat, now, reason)` | Byg de-eskalerings-actions: pensionér direktiv (hvis mintet), anerkend, observ. | [src](../../../core/services/central_agent_smith_escalation.py#L152) |
| function | `step_escalation` | `(state, detected, now, cfg=…)` | REN kerne. `detected` = {pattern_key: {kind, label, metric, corroborated?}} for mønstre | [src](../../../core/services/central_agent_smith_escalation.py#L174) |
| function | `top_line` | `(actions)` | Vælg den mest alvorlige stemme-linje til prompt-halen (confront>bind>resolved>comment). | [src](../../../core/services/central_agent_smith_escalation.py#L277) |

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

## `core/services/central_construct.py`
_The Construct — Sentinel's Shadow Self: en sandbox der tester radikale forenklinger MOD_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_construct.py#L24) |
| function | `simulate_silence` | `(nerve)` | Projicér effekten af at SLUKKE én nerve i 24t — udelukkende fra optaget data. READ-ONLY. | [src](../../../core/services/central_construct.py#L32) |
| function | `build_construct_surface` | `()` | Sandbox-oversigt: hvilke nerver kunne jeg slukke uden tab (safe) vs hvilke ser noget (risky). | [src](../../../core/services/central_construct.py#L67) |
| function | `record_construct` | `()` | Cadence: observér sandbox-fundet til nerve system/construct (metadata-only). Self-safe. | [src](../../../core/services/central_construct.py#L92) |

## `core/services/central_continuity_healer.py`
_Continuity Healer — så Jarvis vågner som SIG, ikke som et fragment._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_continuity_healer.py#L40) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_continuity_healer.py#L49) |
| function | `_now` | `()` | — | [src](../../../core/services/central_continuity_healer.py#L57) |
| function | `_present` | `(state, dim)` | Er dimensionen faktisk til stede (ikke tom) i en selv-tilstand? | [src](../../../core/services/central_continuity_healer.py#L61) |
| function | `_present_dims` | `(state)` | — | [src](../../../core/services/central_continuity_healer.py#L81) |
| function | `_snapshot_age_h` | `(snap)` | — | [src](../../../core/services/central_continuity_healer.py#L85) |
| function | `measure_fidelity` | `()` | continuity_fidelity: hvor meget af mit sidste hele selv er stadig til stede nu. READ-ONLY. | [src](../../../core/services/central_continuity_healer.py#L98) |
| function | `capture_snapshot` | `()` | Gem det nuværende hele selv som 'sidst kendte mig' — KUN når det er rimeligt helt og IKKE | [src](../../../core/services/central_continuity_healer.py#L114) |
| function | `heal` | `()` | Merge-forward: bær tomme dimensioner frem fra sidste hele snapshot (aldrig opfundet). Kun | [src](../../../core/services/central_continuity_healer.py#L127) |
| function | `build_continuity_surface` | `()` | Owner/self-view: fidelity + hvad der gik tabt + følt linje. Self-safe. | [src](../../../core/services/central_continuity_healer.py#L155) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_continuity_healer.py#L173) |
| function | `run_continuity_healer` | `(*, trigger=…, last_visible_at=…)` | Cadence: mål fidelity → hel hvis noget gik tabt (frisk reboot) → ellers fæst et frisk snapshot. | [src](../../../core/services/central_continuity_healer.py#L181) |

## `core/services/central_convene_judge.py`
_core/services/central_convene_judge.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_convene_judge.py#L51) |
| function | `current_mode` | `()` | — | [src](../../../core/services/central_convene_judge.py#L60) |
| function | `_movement_from_signal` | `(name, surface)` | Normalise ONE signal surface to a 0..1 'how much is this moving' reading. | [src](../../../core/services/central_convene_judge.py#L69) |
| function | `_read_flowing_values` | `(surfaces)` | Read the flowing values: signal movement + affective valence + agenda hint. | [src](../../../core/services/central_convene_judge.py#L96) |
| function | `_mood_to_valence` | `(mood)` | Map a coarse mood word to a signed valence in [-1, 1]. Unknown → 0. | [src](../../../core/services/central_convene_judge.py#L155) |
| function | `_derive_topic_hint` | `(movement, latest_wonder, agenda_hint, mood)` | Build a short subject hint from what is actually moving — fed to derive_topic. | [src](../../../core/services/central_convene_judge.py#L171) |
| function | `_observe` | `(verdict, mode)` | — | [src](../../../core/services/central_convene_judge.py#L193) |
| function | `judge_convene` | `(*, surfaces, top_signals, score, score_override=…)` | Decide whether there is a real reason to convene the council now. | [src](../../../core/services/central_convene_judge.py#L211) |

## `core/services/central_core.py`
_Den Intelligente Central — facade (§3.1). Komponerer gate_kernel (decide-motor)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/central_core.py#L13) |
| function | `_egress_safe` | `(payload)` | §24.4 privatlags-membran. observe() skriver FULD payload til den lokale | [src](../../../core/services/central_core.py#L21) |
| function | `_coerce_verdict` | `(nerve, raw, klass)` | Normalisér en nerve-returværdi til Verdict (genbruger kernens parser). | [src](../../../core/services/central_core.py#L36) |
| class | `Central` | `` | — | [src](../../../core/services/central_core.py#L43) |
| method | `Central.__init__` | `(self, *, k=…, sink=…, breaker=…, emit=…)` | — | [src](../../../core/services/central_core.py#L44) |
| method | `Central.observe` | `(self, event, *, emit=…)` | Best-effort telemetri. Kaster ALDRIG (§10.3). | [src](../../../core/services/central_core.py#L57) |
| method | `Central._fail_verdict` | `(self, nerve, klass, reason)` | — | [src](../../../core/services/central_core.py#L106) |
| method | `Central._isolated_verdict` | `(self, nerve, klass)` | — | [src](../../../core/services/central_core.py#L114) |
| method | `Central._record_error` | `(self, err, *, severe=…)` | — | [src](../../../core/services/central_core.py#L119) |
| method | `Central.decide` | `(self, nerve, ctx, fn, *, cluster=…, klass=…)` | Kør én nerve med live-switch + boundary-capture + circuit-breaker + trace. | [src](../../../core/services/central_core.py#L163) |
| method | `Central._maybe_flag_drift` | `(self, nerve, cluster, *, is_error, is_red)` | §7 flag-on-change: opdatér drift-monitor; hvis nervens fejl-/red-rate netop drev | [src](../../../core/services/central_core.py#L220) |
| method | `Central.self_diagnose` | `(self)` | Meta-helbreds-check: virker Centralen SELV? Probe decide+observe, rapportér åbne | [src](../../../core/services/central_core.py#L240) |
| method | `Central.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/central_core.py#L271) |
| function | `central` | `()` | — | [src](../../../core/services/central_core.py#L281) |

## `core/services/central_correlate.py`
_Cross-cluster korrelation — saml ALT hvad der skete for ét run_id på tværs af ALLE clusters_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `correlate` | `(run_id)` | Saml ét run_id's fulde rejse på tværs af clusters. break_point = hvor filmen knækker | [src](../../../core/services/central_correlate.py#L14) |
| function | `recent_broken_runs` | `(*, window=…)` | Nylige run_ids hvor filmen knækkede (RED/error) → til TODO/debugging. Nyeste pr. run. | [src](../../../core/services/central_correlate.py#L50) |

## `core/services/central_cost_surface.py`
_Central cost-surface (WS3, 13. jul 2026) — gør det nyfixede cost-regnskab synligt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_window_threshold` | `(window)` | ISO8601-tærskel for et vindue (samme format som costs.created_at → lex-sammenlignelig). | [src](../../../core/services/central_cost_surface.py#L27) |
| function | `_agg_for_window` | `(conn, window, provider)` | — | [src](../../../core/services/central_cost_surface.py#L37) |
| function | `_breakdown` | `(conn, window, provider)` | — | [src](../../../core/services/central_cost_surface.py#L67) |
| function | `_deepseek_balance` | `()` | Live DeepSeek-saldo (USD, streng), cachet 5 min. Fejl/offline → None. | [src](../../../core/services/central_cost_surface.py#L104) |
| function | `build_cost_surface` | `(*, window=…, provider=…)` | Cost-aggregat til /central/cost + `jc cost`. | [src](../../../core/services/central_cost_surface.py#L140) |

## `core/services/central_coverage.py`
_core/services/central_coverage.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | — | [src](../../../core/services/central_coverage.py#L35) |
| function | `load_connectivity_matrix` | `()` | Læs det committede connectivity-kort ved runtime (cachet). Self-safe → None ved fejl. | [src](../../../core/services/central_coverage.py#L40) |
| function | `_reset_matrix_cache_for_tests` | `()` | — | [src](../../../core/services/central_coverage.py#L61) |
| function | `structural_coverage` | `(*, top_dark=…)` | Reducér connectivity-kortet til RUNTIME-signal-skalarer: total/koblet/dark/llm-spild + | [src](../../../core/services/central_coverage.py#L66) |
| function | `measure` | `(*, window=…)` | Mål surface-count + dækning LIVE fra registry + routing-tabeller + event-vinduet. Self-safe. | [src](../../../core/services/central_coverage.py#L110) |
| function | `record_coverage` | `(*, window=…)` | Mål + skriv nøgletal til tidsserien (cluster=system) så dækning kan plottes over tid. | [src](../../../core/services/central_coverage.py#L170) |
| function | `run_coverage_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål + registrér dækning (~hvert 30 min). Self-safe. | [src](../../../core/services/central_coverage.py#L207) |
| function | `register_coverage_producer` | `()` | Registrér dæknings-målingen som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_coverage.py#L216) |
| function | `build_central_coverage_surface` | `()` | Mission Control surface — read-only, runtime-målt dæknings-projektion (volumen + struktur). | [src](../../../core/services/central_coverage.py#L228) |

## `core/services/central_coverage_action.py`
_core/services/central_coverage_action.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_mode` | `()` | Læs handlings-tilstanden fra runtime-state kv. Default "off" → ingen adfærdsændring. Self-safe. | [src](../../../core/services/central_coverage_action.py#L38) |
| function | `_dark_family_live_signal` | `(top_dark_families, *, window)` | Kryds de strukturelt-mørke families med hvad der FAKTISK flyder i event-vinduet: en dark-family | [src](../../../core/services/central_coverage_action.py#L49) |
| function | `_formulate_structural_blindness_hypothesis` | `(sc)` | Lav strukturel dækning → fuldt pre-registreret hypotese om at de mørke filer bærer signal der | [src](../../../core/services/central_coverage_action.py#L71) |
| function | `_formulate_dark_family_hypothesis` | `(hot)` | En VARM dark-family (bærer live-signal Centralen ikke ser) → fuldt pre-registreret hypotese. | [src](../../../core/services/central_coverage_action.py#L96) |
| function | `compute_candidates` | `(*, window=…)` | Beregn HVAD blindheden VILLE udløse (uafhængigt af flag): pre-registrerede hypotese-kandidater | [src](../../../core/services/central_coverage_action.py#L117) |
| function | `run_coverage_action_tick` | `(*, trigger=…, last_visible_at=…)` | Handlings-tick (§11 #5): beregn kandidater → agér EFTER flag. Self-safe, kaster aldrig. | [src](../../../core/services/central_coverage_action.py#L136) |
| function | `register_coverage_action_producer` | `()` | Registrér handlings-tricket som cadence-producer (~hvert 60 min, lav prioritet). Flag=off | [src](../../../core/services/central_coverage_action.py#L185) |
| function | `build_central_coverage_action_surface` | `()` | Mission Control surface — read-only: nuværende mode + hvad blindheden VILLE flagge lige nu. | [src](../../../core/services/central_coverage_action.py#L198) |

