# `core.services.18` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_embed_ollama` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L104) |
| function | `_encode_vector` | `(vec)` | — | [src](../../../core/services/semantic_memory.py#L128) |
| function | `_decode_vector` | `(data)` | — | [src](../../../core/services/semantic_memory.py#L132) |
| function | `_hash_content` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L136) |
| function | `_prepare_text` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L140) |
| function | `index_memory` | `(*, source_table, source_id, content, modality)` | Embed content and upsert. Returns True on success, False if embed fails | [src](../../../core/services/semantic_memory.py#L149) |
| function | `search` | `(query, *, modalities=…, source_tables=…, limit=…, min_score=…)` | Return top-k memories by cosine similarity. | [src](../../../core/services/semantic_memory.py#L184) |
| function | `_extract_content_for_row` | `(table, row)` | Return (content_text, modality) for a raw row from a known table. | [src](../../../core/services/semantic_memory.py#L248) |
| function | `_row_id` | `(table, row)` | — | [src](../../../core/services/semantic_memory.py#L263) |
| function | `backfill_all` | `(*, max_per_table=…)` | Embed every unindexed row across registered source tables. | [src](../../../core/services/semantic_memory.py#L271) |
| function | `_content_hash_unchanged` | `(table, source_id, new_content)` | — | [src](../../../core/services/semantic_memory.py#L346) |
| function | `get_stats` | `()` | — | [src](../../../core/services/semantic_memory.py#L355) |
| function | `build_semantic_memory_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/semantic_memory.py#L368) |

## `core/services/sensory_archive.py`
_Sansernes Arkiv — service layer for sensory memories._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_mood_from_content` | `(content, modality)` | Auto-extract a short Danish mood tone from content using keyword matching. | [src](../../../core/services/sensory_archive.py#L27) |
| function | `_record` | `(modality, content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L97) |
| function | `record_visual` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L148) |
| function | `record_audio` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L157) |
| function | `record_atmosphere` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L166) |
| function | `record_mixed` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L175) |
| function | `list_recent` | `(*, modality=…, limit=…, offset=…, since=…)` | — | [src](../../../core/services/sensory_archive.py#L184) |
| function | `search` | `(query, *, modality=…, limit=…)` | — | [src](../../../core/services/sensory_archive.py#L196) |
| function | `get` | `(memory_id)` | — | [src](../../../core/services/sensory_archive.py#L205) |
| function | `count` | `(*, modality=…)` | — | [src](../../../core/services/sensory_archive.py#L209) |
| function | `summarize_for_context` | `(limit=…)` | Return a compact summary usable as surface/context injection. | [src](../../../core/services/sensory_archive.py#L213) |

## `core/services/sensory_perception_bridge.py`
_Sensory perception bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_shingle` | `(text, *, n=…)` | Tokenize lowercased text into overlapping n-grams of words. | [src](../../../core/services/sensory_perception_bridge.py#L21) |
| function | `_jaccard` | `(a, b)` | Jaccard similarity between two token sets. Returns 0 if both empty. | [src](../../../core/services/sensory_perception_bridge.py#L29) |
| function | `_mode` | `(values)` | Most common value. On tie, returns the value that appears first in the list. | [src](../../../core/services/sensory_perception_bridge.py#L38) |
| function | `_aggregate_baseline` | `(records)` | Aggregate 1-N records into a single baseline. | [src](../../../core/services/sensory_perception_bridge.py#L50) |
| function | `_parse_iso` | `(ts)` | Parse ISO timestamp; return None if malformed. Treats naive as UTC. | [src](../../../core/services/sensory_perception_bridge.py#L87) |
| function | `_now` | `()` | Indirected for monkey-patching in tests. | [src](../../../core/services/sensory_perception_bridge.py#L100) |
| function | `_recent_baseline` | `(modality, current_record)` | Latest N records of same modality excluding current. | [src](../../../core/services/sensory_perception_bridge.py#L105) |
| function | `_time_of_day_baseline` | `(modality, current_record)` | Records inside ±N hours of current's time-of-day, over last M days. | [src](../../../core/services/sensory_perception_bridge.py#L122) |
| function | `_build_baseline` | `(modality, current_record)` | Modality-aware baseline selection. | [src](../../../core/services/sensory_perception_bridge.py#L165) |
| function | `_metadata_changed` | `(new_md, baseline_md, modality)` | Per-modality metadata change detection. | [src](../../../core/services/sensory_perception_bridge.py#L181) |
| function | `_detect_change` | `(record, baseline, modality)` | Combined heuristic: mood_tone shift OR Jaccard < 0.4 OR metadata shift. | [src](../../../core/services/sensory_perception_bridge.py#L231) |
| function | `_summary_for_change` | `(modality, new_mood, baseline_mood, kind, jaccard)` | Generate a short Danish summary line for the perceptual event. | [src](../../../core/services/sensory_perception_bridge.py#L313) |
| function | `_salience_for_change` | `(change)` | Map change description to salience level (high/medium/normal). | [src](../../../core/services/sensory_perception_bridge.py#L348) |
| function | `_bridge_enabled` | `()` | — | [src](../../../core/services/sensory_perception_bridge.py#L381) |
| function | `_percept` | `(*, source_event_id, source_kind, change_type, salience, summary, observed_at, evidence)` | Build a percept dict in the shape expected by perceptual_event_engine._record_perceptual_event. | [src](../../../core/services/sensory_perception_bridge.py#L389) |
| function | `classify_sensory_change` | `(event)` | Top-level entry. Returns a percept dict if the event represents a meaningful | [src](../../../core/services/sensory_perception_bridge.py#L411) |
| function | `_classify_sensory_change_inner` | `(event)` | — | [src](../../../core/services/sensory_perception_bridge.py#L423) |

## `core/services/session_boot_reconciler.py`
_Boot-reconciler: crash-zombie runs → interrupted, så de genoptages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(payload)` | Fyr central-nerve ``session_persistence`` (cluster runtime). Best-effort, | [src](../../../core/services/session_boot_reconciler.py#L37) |
| function | `reconcile_on_boot` | `(stale_after_s=…)` | Reconcile crash-zombie runs ved opstart. Fail-open. | [src](../../../core/services/session_boot_reconciler.py#L51) |

## `core/services/session_continuity.py`
_Session Continuity — kontinuitet der føles, ikke kun opslås._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/session_continuity.py#L64) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/session_continuity.py#L68) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/session_continuity.py#L81) |
| function | `detect_new_session` | `()` | Return whether current moment should be treated as 'new session'. | [src](../../../core/services/session_continuity.py#L104) |
| function | `_gather_carry_context` | `()` | Collect what Jarvis might be carrying into today. | [src](../../../core/services/session_continuity.py#L152) |
| function | `_build_morning_prompt` | `(carry, minutes_since_last)` | — | [src](../../../core/services/session_continuity.py#L252) |
| function | `generate_morning_thread` | `(*, force=…)` | Generate and persist a morning thread if this is a new session. | [src](../../../core/services/session_continuity.py#L304) |
| function | `get_latest_morning_thread` | `()` | — | [src](../../../core/services/session_continuity.py#L438) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/session_continuity.py#L460) |
| function | `detect_echo_themes` | `(*, lookback_days=…)` | Find recurring themes in recent inner voices + chat messages. | [src](../../../core/services/session_continuity.py#L467) |
| function | `get_echo_signals_for_prompt` | `()` | Return a quiet one-liner of recurring themes for prompt injection. | [src](../../../core/services/session_continuity.py#L532) |
| function | `build_session_continuity_surface` | `()` | — | [src](../../../core/services/session_continuity.py#L560) |

## `core/services/session_distillation.py`
_Session distillation and private brain continuity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_near_duplicate` | `(summary, record_type, recent_records)` | Return True if a record with very similar summary + same type exists | [src](../../../core/services/session_distillation.py#L82) |
| function | `_record_type_to_domain` | `(record_type)` | Map a private brain record_type to its decay domain. | [src](../../../core/services/session_distillation.py#L111) |
| function | `_try_insert_guarded` | `(*, record_type, layer, session_id, run_id, focus, summary, detail, source_signals, confidence, now, recent_records)` | Insert a private brain record if it passes anti-spam guard. | [src](../../../core/services/session_distillation.py#L124) |
| function | `distill_session_carry` | `(*, session_id, run_id)` | Classify runtime evidence into private-brain / workspace-memory / discard. | [src](../../../core/services/session_distillation.py#L164) |
| function | `_analyze_session_for_cognitive_systems` | `(*, session_id, run_id)` | Analyze a completed session for cognitive accumulation systems. | [src](../../../core/services/session_distillation.py#L374) |
| function | `_scrub_continuity_text` | `(text)` | Read-time-rens af LAGRET continuity-tekst (Jarvis-spec 2026-06-23 #2): ældre | [src](../../../core/services/session_distillation.py#L443) |
| function | `build_private_brain_context` | `(*, limit=…)` | Build a bounded read of recent private brain records suitable for | [src](../../../core/services/session_distillation.py#L470) |
| function | `_classify_continuity_mode` | `(excerpts, by_type)` | Classify the semantic intention of a continuity pass. | [src](../../../core/services/session_distillation.py#L537) |
| function | `run_private_brain_continuity` | `(*, trigger=…)` | Lightweight continuity pass for the private brain. | [src](../../../core/services/session_distillation.py#L592) |
| function | `run_private_brain_lifecycle` | `()` | Run a bounded lifecycle pass over private brain records. | [src](../../../core/services/session_distillation.py#L754) |
| function | `build_private_brain_surface` | `(*, limit=…)` | Return the current private brain state for observability. | [src](../../../core/services/session_distillation.py#L849) |
| function | `build_session_distillation_surface` | `(*, limit=…)` | Return recent distillation records for observability. | [src](../../../core/services/session_distillation.py#L870) |
| function | `generate_session_summary` | `(*, session_id, run_id=…, user_message=…, assistant_response=…)` | Generate and store a compact conversation summary for the given session. | [src](../../../core/services/session_distillation.py#L890) |
| function | `build_previous_session_summaries` | `(*, limit=…)` | Build a text block with recent session summaries for prompt injection. | [src](../../../core/services/session_distillation.py#L981) |

## `core/services/session_inbox.py`
_Session inbox — gates daemon notifications during active sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/session_inbox.py#L59) |
| function | `_connect` | `()` | — | [src](../../../core/services/session_inbox.py#L78) |
| function | `is_session_active` | `(session_id, *, window_seconds=…)` | Has this session seen chat-stream activity recently? | [src](../../../core/services/session_inbox.py#L88) |
| function | `enqueue` | `(*, session_id, content, source, urgent=…)` | Add a daemon notification to the inbox for later delivery. | [src](../../../core/services/session_inbox.py#L122) |
| function | `pending_for_session` | `(session_id)` | List items still queued for delivery in this session. | [src](../../../core/services/session_inbox.py#L153) |
| function | `flush_session` | `(session_id)` | Deliver all queued items for a session. Each becomes an actual | [src](../../../core/services/session_inbox.py#L171) |
| function | `pending_count` | `(session_id=…)` | — | [src](../../../core/services/session_inbox.py#L237) |
| function | `_listener_loop` | `()` | Background flusher. | [src](../../../core/services/session_inbox.py#L262) |
| function | `start_session_inbox` | `()` | Start the DB-polling flusher. Idempotent. | [src](../../../core/services/session_inbox.py#L346) |
| function | `stop_session_inbox` | `()` | — | [src](../../../core/services/session_inbox.py#L363) |

## `core/services/session_milestones.py`
_Session-milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_turns` | `(session_id)` | [(message_id, text)] for user-beskederne i kronologisk orden. Self-safe → []. | [src](../../../core/services/session_milestones.py#L27) |
| function | `_short_title` | `(text, n=…)` | — | [src](../../../core/services/session_milestones.py#L50) |
| function | `_per_turn_milestones` | `(turns)` | — | [src](../../../core/services/session_milestones.py#L55) |
| function | `_llm_segment` | `(turns)` | Bed den billige lane segmentere samtalen i kapitler. Returnerer milepæle eller None. | [src](../../../core/services/session_milestones.py#L59) |
| function | `_generate` | `(turns)` | — | [src](../../../core/services/session_milestones.py#L104) |
| function | `get_session_milestones` | `(session_id)` | Milepæle for rail'en: [{anchor_id, title}]. Cached pr. session+turn-antal; regenereres | [src](../../../core/services/session_milestones.py#L110) |

## `core/services/session_persistence_flag.py`
_Governed kill-switch for session-persistence boot-reconciler. Default OFF (shadow)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_flag` | `()` | Læs rå flag-værdi fra runtime-state. None = usat. | [src](../../../core/services/session_persistence_flag.py#L18) |
| function | `session_persistence_enabled` | `()` | True KUN når eksplicit slået til ('on'/'1'/'true'/'yes'). Usat eller | [src](../../../core/services/session_persistence_flag.py#L24) |

## `core/services/session_topic_tracker.py`
_Session topic tracker — real-time topic extraction and accumulation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_topics_from_text` | `(text)` | Extract candidate topic labels from a user message. | [src](../../../core/services/session_topic_tracker.py#L94) |
| function | `_increment_turn` | `(session_id)` | Increment turn counter for session. Returns new count. | [src](../../../core/services/session_topic_tracker.py#L175) |
| function | `_should_extract` | `(session_id)` | Return True if it's time to extract topics for this session. | [src](../../../core/services/session_topic_tracker.py#L181) |
| function | `_accumulate_topics` | `(session_id, topics)` | Merge extracted topics into the session's topic store. | [src](../../../core/services/session_topic_tracker.py#L187) |
| function | `track_session_topics` | `(session_id, run_id, user_message)` | Call this after every visible user turn. | [src](../../../core/services/session_topic_tracker.py#L207) |
| function | `_persist_session_topics` | `(session_id)` | Write current in-memory topics to the session_topics DB table. | [src](../../../core/services/session_topic_tracker.py#L241) |
| function | `load_session_topics` | `(session_id)` | Load topics for a session from DB, merging with in-memory state. | [src](../../../core/services/session_topic_tracker.py#L262) |
| function | `_format_topics_for_prompt` | `(store, max_topics=…)` | Format topics sorted by mention count descending. | [src](../../../core/services/session_topic_tracker.py#L296) |
| function | `build_session_topics_prompt_section` | `(session_id=…)` | Build a compact section showing active topics for this session. | [src](../../../core/services/session_topic_tracker.py#L316) |
| function | `clear_session_topics` | `(session_id)` | Clear in-memory topics for a session. Called at session end. | [src](../../../core/services/session_topic_tracker.py#L354) |

## `core/services/session_wakeup.py`
_Eventbus → visible-prompt wake-up digest._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_notable` | `(kind)` | — | [src](../../../core/services/session_wakeup.py#L58) |
| function | `_load_marks` | `()` | — | [src](../../../core/services/session_wakeup.py#L71) |
| function | `_save_marks` | `(marks)` | — | [src](../../../core/services/session_wakeup.py#L84) |
| function | `last_seen_event_id` | `(session_id)` | — | [src](../../../core/services/session_wakeup.py#L88) |
| function | `mark_seen` | `(session_id, event_id)` | — | [src](../../../core/services/session_wakeup.py#L92) |
| function | `_format_event` | `(ev)` | — | [src](../../../core/services/session_wakeup.py#L100) |
| function | `wakeup_digest` | `(session_id)` | Return a short digest of notable events since this session last saw, | [src](../../../core/services/session_wakeup.py#L116) |

## `core/services/shadow_experiment_registry.py`
_core/services/shadow_experiment_registry.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | Læs hele register-dict'en fra KV. Self-safe → {} ved fejl/ugyldig form. | [src](../../../core/services/shadow_experiment_registry.py#L31) |
| function | `_save` | `(data)` | Skriv hele register-dict'en durabelt. Self-safe (best-effort). | [src](../../../core/services/shadow_experiment_registry.py#L44) |
| function | `register_experiment` | `(name, review_after_hours, note=…, started_ts=…)` | Registrér et shadow-eksperiment. Idempotent på navn: hvis det allerede er | [src](../../../core/services/shadow_experiment_registry.py#L54) |
| function | `_annotate` | `(rec, now)` | Berig én rå-record med `hours_running` + `ripe`. | [src](../../../core/services/shadow_experiment_registry.py#L89) |
| function | `list_experiments` | `(now_ts=…)` | Alle registrerede eksperimenter, beriget med `hours_running` + `ripe`. | [src](../../../core/services/shadow_experiment_registry.py#L107) |
| function | `ready_for_review` | `(now_ts=…)` | De modne (ripe), ikke-reviewede eksperimenter. Self-safe → []. | [src](../../../core/services/shadow_experiment_registry.py#L120) |
| function | `mark_reviewed` | `(name)` | Markér et eksperiment som reviewet (fjerner det fra `ripe`). Self-safe. | [src](../../../core/services/shadow_experiment_registry.py#L125) |
| function | `register_known_shadows` | `()` | Seed registeret med de bekræftede live shadows (idempotent, self-safe). | [src](../../../core/services/shadow_experiment_registry.py#L154) |
| function | `build_shadow_review_surface` | `(now_ts=…)` | Byg surface til Central-route/`jc shadows`. Seeder kendte shadows, | [src](../../../core/services/shadow_experiment_registry.py#L161) |
| function | `_emit_reminder` | `(ripe_names)` | Passiv Central-påmindelse: observe `central_meta/shadow_review_due`. | [src](../../../core/services/shadow_experiment_registry.py#L182) |
| function | `tick_shadow_review_reminder` | `(now_ts=…)` | Heartbeat-venlig tick: byg surface (som emit'er påmindelsen ved modenhed) | [src](../../../core/services/shadow_experiment_registry.py#L198) |

## `core/services/shadow_scan_daemon.py`
_Shadow Scan — my blindspots as visible signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L34) |
| function | `_shadow_log_path` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L38) |
| function | `_load` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L42) |
| function | `_save` | `(data)` | — | [src](../../../core/services/shadow_scan_daemon.py#L58) |
| function | `_detect_apologize_then_repeat` | `()` | If conflict_memory has multiple similar pushback patterns. | [src](../../../core/services/shadow_scan_daemon.py#L72) |
| function | `_detect_avoid_topic` | `()` | Pull from existing avoidance_detector. | [src](../../../core/services/shadow_scan_daemon.py#L101) |
| function | `_detect_overclaim_then_retract` | `()` | Self-mutation followed by rollback within a short window. | [src](../../../core/services/shadow_scan_daemon.py#L122) |
| function | `_detect_intent_behavior_gap` | `()` | Stale goals while related tools keep running. | [src](../../../core/services/shadow_scan_daemon.py#L146) |
| function | `_run_all_detectors` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L175) |
| function | `_append_shadow_log` | `(scan)` | — | [src](../../../core/services/shadow_scan_daemon.py#L195) |
| function | `run_scan` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L230) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/shadow_scan_daemon.py#L260) |
| function | `build_shadow_scan_surface` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L273) |
| function | `_surface_summary` | `(last)` | — | [src](../../../core/services/shadow_scan_daemon.py#L287) |
| function | `build_shadow_scan_prompt_section` | `()` | Surface strongest pattern if the last scan was within 48h. | [src](../../../core/services/shadow_scan_daemon.py#L297) |
| function | `build_shadow_feedback_section` | `()` | Generate behavioral correction if shadow scan shows elevated avoidance. | [src](../../../core/services/shadow_scan_daemon.py#L321) |

## `core/services/share_guard_store.py`
_Pending cross-user share-beslutninger — DB-backed kø (spec §4.4, Fase 6 #1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/share_guard_store.py#L19) |
| function | `_save` | `(items)` | — | [src](../../../core/services/share_guard_store.py#L24) |
| function | `record_pending` | `(*, decision_id, session_id, current_user_id, mentioned_users, text_preview, created_at)` | Registrér en pending share-beslutning. Returnér recorden. | [src](../../../core/services/share_guard_store.py#L28) |
| function | `list_pending` | `()` | Alle uafgjorte share-beslutninger (til Cowork-køen). | [src](../../../core/services/share_guard_store.py#L53) |
| function | `resolve` | `(decision_id, *, shared)` | Afgør en beslutning: shared=True (okay at dele) / False (hold privat). | [src](../../../core/services/share_guard_store.py#L58) |

## `core/services/shared_cache.py`
_SQLite-backed shared cache for cross-process state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | Create the shared_cache table on first use. Idempotent. | [src](../../../core/services/shared_cache.py#L56) |
| function | `get` | `(key)` | Return cached value, or None if missing/expired/invalid. | [src](../../../core/services/shared_cache.py#L88) |
| function | `set` | `(key, value, *, ttl_seconds)` | Store ``value`` under ``key`` with TTL. Best-effort, never raises. | [src](../../../core/services/shared_cache.py#L127) |
| function | `delete` | `(key)` | Remove a key from the cache. Best-effort, never raises. | [src](../../../core/services/shared_cache.py#L169) |
| function | `invalidate_prefix` | `(prefix)` | Remove all keys starting with ``prefix``. Returns delete count. | [src](../../../core/services/shared_cache.py#L184) |
| function | `cleanup_expired` | `()` | Purge rows whose expires_at has passed. Returns delete count. | [src](../../../core/services/shared_cache.py#L208) |
| function | `stats` | `()` | Return basic cache stats for MC visibility. | [src](../../../core/services/shared_cache.py#L230) |
| function | `build_shared_cache_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/shared_cache.py#L259) |
| function | `_emit_shared_cache_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/shared_cache.py#L274) |

## `core/services/shared_language.py`
_Shared Language — tracks shorthand terms that develop between Jarvis and user._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scan_for_shared_terms` | `(*, user_message, assistant_response, run_id=…)` | Scan conversation for potential shared language terms. | [src](../../../core/services/shared_language.py#L25) |
| function | `build_shared_language_surface` | `()` | — | [src](../../../core/services/shared_language.py#L61) |
| function | `_is_common_phrase` | `(phrase)` | — | [src](../../../core/services/shared_language.py#L82) |

## `core/services/shared_language_extended.py`
_Shared Language Extended — shorthand-udvikling og -resolution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/shared_language_extended.py#L34) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/shared_language_extended.py#L38) |
| function | `_ngrams` | `(text)` | — | [src](../../../core/services/shared_language_extended.py#L60) |
| function | `_load_recent_user_messages` | `(days=…, limit=…)` | — | [src](../../../core/services/shared_language_extended.py#L71) |
| function | `propose_shorthand_terms` | `(*, min_occurrences=…, max_proposals=…)` | Scan chat messages for repeated n-grams; propose as shorthand. | [src](../../../core/services/shared_language_extended.py#L87) |
| function | `_latest_suggestion_ts` | `()` | — | [src](../../../core/services/shared_language_extended.py#L151) |
| function | `maybe_weekly_shorthand_suggestion` | `()` | Max 1 shorthand per 7 days. Returns the new term if added. | [src](../../../core/services/shared_language_extended.py#L166) |
| function | `list_shorthand_terms` | `(*, limit=…)` | — | [src](../../../core/services/shared_language_extended.py#L210) |
| function | `resolve_shorthand_text` | `(text)` | Expand shorthand in text. Returns {resolved_text, matched_terms}. | [src](../../../core/services/shared_language_extended.py#L229) |
| function | `build_shared_language_extended_surface` | `()` | — | [src](../../../core/services/shared_language_extended.py#L265) |

## `core/services/shutdown_window_daemon.py`
_Shutdown Window daemon — unannounced pauses to practice finitude._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_paused` | `()` | Return True if we are currently inside a shutdown window. | [src](../../../core/services/shutdown_window_daemon.py#L40) |
| function | `tick_shutdown_window_daemon` | `()` | Called every heartbeat tick. Decides if a shutdown window should start. | [src](../../../core/services/shutdown_window_daemon.py#L51) |
| function | `_trigger_shutdown_window` | `(*, now, pause_until, pause_minutes)` | Set the module-level pause flag and emit events. | [src](../../../core/services/shutdown_window_daemon.py#L111) |
| function | `_finitude_note` | `()` | Short note about impermanence — chosen at random, no LLM call. | [src](../../../core/services/shutdown_window_daemon.py#L153) |
| function | `build_shutdown_window_surface` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L168) |
| function | `_experiment_enabled` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L180) |
| function | `_days_in_month` | `(dt)` | — | [src](../../../core/services/shutdown_window_daemon.py#L189) |
| function | `_state` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L194) |

## `core/services/side_tasks.py`
_Side-task flag — keep the main thread focused._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/side_tasks.py#L33) |
| function | `_save_all` | `(items)` | — | [src](../../../core/services/side_tasks.py#L40) |
| function | `flag` | `(*, title, prompt, tldr=…, session_id=…)` | — | [src](../../../core/services/side_tasks.py#L44) |
| function | `list_pending` | `()` | — | [src](../../../core/services/side_tasks.py#L64) |
| function | `resolve` | `(side_task_id, *, decision)` | — | [src](../../../core/services/side_tasks.py#L68) |
| function | `side_tasks_prompt_section` | `()` | — | [src](../../../core/services/side_tasks.py#L86) |
| function | `_exec_flag_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L105) |
| function | `_exec_list_side_tasks` | `(_args)` | — | [src](../../../core/services/side_tasks.py#L114) |
| function | `_exec_dismiss_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L119) |
| function | `_exec_activate_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L123) |

## `core/services/signal_baseline.py`
_Persisted signal-baseline with cold-start guard (Task C1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | Read the whole baseline dict from the durable store. Fail-closed to {}. | [src](../../../core/services/signal_baseline.py#L32) |
| function | `_save` | `(baselines)` | — | [src](../../../core/services/signal_baseline.py#L51) |
| function | `get_baseline` | `(signal)` | Last recorded value for ``signal``; None if never recorded. | [src](../../../core/services/signal_baseline.py#L61) |
| function | `set_baseline` | `(signal, value)` | Persist ``value`` durably as the new baseline for ``signal``. | [src](../../../core/services/signal_baseline.py#L72) |
| function | `is_cold_start` | `(min_signals=…)` | True until at least ``min_signals`` distinct baselines have been recorded. | [src](../../../core/services/signal_baseline.py#L92) |
| function | `clear_all` | `()` | Drop all baselines (test helper). Self-safe. | [src](../../../core/services/signal_baseline.py#L110) |

