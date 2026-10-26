# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/inner_visible_support_signal_tracking.py`
_Inner-visible support signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_inner_visible_support_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L36) |
| function | `refresh_runtime_inner_visible_support_signal_statuses` | `()` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L70) |
| function | `build_runtime_inner_visible_support_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L74) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L78) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L212) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L222) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L232) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L248) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L278) |
| function | `_inner_visible_support_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L341) |
| function | `_focus_key` | `(private_state, curiosity_state)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L369) |
| function | `_derive_support_tone` | `(*, state_tone, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L380) |
| function | `_derive_support_stance` | `(*, state_tone, curiosity_type, contradiction_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L394) |
| function | `_derive_support_directness` | `(*, state_pressure, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L406) |
| function | `_derive_support_watchfulness` | `(*, state_pressure, curiosity_pull, curiosity_type, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L416) |
| function | `_derive_support_momentum` | `(*, state_pressure, curiosity_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L432) |
| function | `_bounded_support_summary` | `(*, private_state, curiosity_state, executive_contradiction, tone, stance)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L440) |
| function | `_grounding_mode` | `(*, has_curiosity, has_executive_contradiction)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L463) |
| function | `_supports_executive_sharpening` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L473) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L482) |
| function | `_canonical_focus_segment` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L488) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L495) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L502) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L514) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L525) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L533) |

## `core/services/inner_voice_daemon.py`
_Bounded inner voice daemon light — private heartbeat-driven inner voice._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ren_stemme` | `(summary)` | Gem ikke opgaven som var den svaret. | [src](../../../core/services/inner_voice_daemon.py#L101) |
| function | `run_inner_voice_daemon` | `(*, trigger=…, last_visible_at=…, witness_daemon_last_run_at=…)` | Bounded inner voice daemon — produces one private inner-voice note. | [src](../../../core/services/inner_voice_daemon.py#L119) |
| function | `get_inner_voice_daemon_state` | `()` | Return current inner voice daemon state for MC observability. | [src](../../../core/services/inner_voice_daemon.py#L333) |
| function | `_gather_grounding` | `()` | Gather grounding material from existing runtime surfaces. | [src](../../../core/services/inner_voice_daemon.py#L349) |
| function | `_recent_approval_sentiment_summary` | `()` | Summarize only notable recent approval-feedback patterns. | [src](../../../core/services/inner_voice_daemon.py#L530) |
| function | `_approval_feedback_tools` | `(entries)` | — | [src](../../../core/services/inner_voice_daemon.py#L566) |
| function | `_render_inner_voice_note` | `(grounding)` | Render inner voice note via workspace prompt + LLM, with fallback. | [src](../../../core/services/inner_voice_daemon.py#L584) |
| function | `_llm_render_inner_voice` | `(grounding)` | Use workspace INNER_VOICE.md prompt + heartbeat model to render note. | [src](../../../core/services/inner_voice_daemon.py#L604) |
| function | `_apply_support_shading` | `(base_mode, fragments)` | Apply experiential support bias to inner voice mode selection. | [src](../../../core/services/inner_voice_daemon.py#L806) |
| function | `_has_living_candidate_pull` | `(fragments, *, continuity_state, initiative_shading, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L835) |
| function | `_has_mixed_live_stream` | `(fragments, *, continuity_state, initiative_shading)` | — | [src](../../../core/services/inner_voice_daemon.py#L875) |
| function | `_deterministic_compose` | `(grounding)` | Deterministic fallback composition when LLM is unavailable. | [src](../../../core/services/inner_voice_daemon.py#L907) |
| function | `_normalize_inner_voice_mode` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L938) |
| function | `_select_inner_voice_mode` | `(grounding, *, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L945) |
| function | `_derive_inner_voice_focus` | `(grounding, *, mode=…, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L1004) |
| function | `_compose_living_inner_voice_thought` | `(*, mode, fragments, focus)` | Structured fallback trace — NOT first-person prose. | [src](../../../core/services/inner_voice_daemon.py#L1038) |
| function | `_secondary_inner_voice_observation` | `(fragments)` | Pick the strongest secondary fragment, returned as key:value (no prose). | [src](../../../core/services/inner_voice_daemon.py#L1068) |
| function | `_mode_anchor` | `(fragments, focus)` | — | [src](../../../core/services/inner_voice_daemon.py#L1089) |
| function | `_normalize_inner_voice_initiative` | `(initiative, *, grounding, mode, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L1104) |
| function | `_render_grounding_fragment` | `(key, value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1128) |
| function | `_sanitize_previous_inner_voice` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1158) |
| function | `_sanitize_inner_voice_text` | `(text, *, max_len=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L1167) |
| function | `_looks_like_inner_voice_meta` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1217) |
| function | `_thought_contains_initiative` | `(text)` | Detect if a thought text contains initiative signals. | [src](../../../core/services/inner_voice_daemon.py#L1270) |
| function | `_extract_initiative_from_thought` | `(text)` | Extract a short initiative description from a thought. | [src](../../../core/services/inner_voice_daemon.py#L1278) |
| function | `_blocked` | `(reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/inner_voice_daemon.py#L1304) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1321) |

## `core/services/inner_voice_notifier.py`
_Inner voice notifier — proactive notification when a thought has substance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L41) |
| function | `stop_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L59) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/inner_voice_notifier.py#L73) |
| function | `_handle_event` | `(payload)` | — | [src](../../../core/services/inner_voice_notifier.py#L91) |
| function | `_is_substantive` | `(*, summary, mode, initiative, initiative_detected)` | — | [src](../../../core/services/inner_voice_notifier.py#L170) |
| function | `_format_message` | `(*, summary, initiative, mode)` | — | [src](../../../core/services/inner_voice_notifier.py#L186) |
| function | `_notifier_enabled` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L194) |
| function | `_min_summary_chars` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L203) |
| function | `_cooldown_minutes` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L213) |
| function | `_quiet_hours` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L223) |
| function | `_in_quiet_hours` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L234) |
| function | `_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L245) |
| function | `_in_cooldown` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L250) |
| function | `_record_sent` | `(now, *, record_id)` | — | [src](../../../core/services/inner_voice_notifier.py#L262) |
| function | `get_inner_voice_notifier_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L277) |

## `core/services/inner_voice_shadow.py`
_Inner voice shadow recorder — Pilot for llm_driven_inner_pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AppraisalRecord` | `` | Structured inner-voice state with narrative rendering. | [src](../../../core/services/inner_voice_shadow.py#L67) |
| method | `AppraisalRecord.is_expired` | `(self, *, now=…)` | True if more than expiry_seconds have passed since generated_at. | [src](../../../core/services/inner_voice_shadow.py#L105) |
| method | `AppraisalRecord.to_dict` | `(self)` | — | [src](../../../core/services/inner_voice_shadow.py#L116) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/inner_voice_shadow.py#L136) |
| function | `_connect` | `()` | Frisk forbindelse der LUKKES ved `with`-exit (rettet 12/10-2026). | [src](../../../core/services/inner_voice_shadow.py#L171) |
| function | `_persist` | `(*, function_name, inputs, template_output, llm_output, llm_provider, llm_model, llm_latency_ms, llm_error, source=…, confidence=…, expiry_seconds=…, allowed_effects=…, generated_at=…)` | — | [src](../../../core/services/inner_voice_shadow.py#L193) |
| function | `_call_llm` | `(prompt)` | Run the cheap-lane via pool. Returns dict with output/error/latency. | [src](../../../core/services/inner_voice_shadow.py#L250) |
| function | `_build_helpful_signal_prompt` | `(*, status, focus, work_signal)` | Construct a prompt that asks for the kind of one-line inner thought | [src](../../../core/services/inner_voice_shadow.py#L281) |
| function | `record_shadow` | `(*, function_name, inputs, template_output, prompt_builder)` | Fire-and-forget: spawn a daemon thread to call LLM + persist both | [src](../../../core/services/inner_voice_shadow.py#L306) |
| function | `_build_voice_line_prompt` | `(*, mood_tone, self_position, current_concern, current_pull, **_extra)` | Prompt for protected_inner_voice._voice_line's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L381) |
| function | `_build_private_summary_prompt` | `(*, status, focus, uncertainty, work_signal, **_extra)` | Prompt for private_inner_note._private_summary's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L410) |
| function | `shadow_helpful_signal` | `(*, status, focus, work_signal, template_output)` | — | [src](../../../core/services/inner_voice_shadow.py#L439) |
| function | `generate_appraisal` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…, expiry_seconds=…, allowed_effects=…)` | State-first appraisal: returns the full structured record. | [src](../../../core/services/inner_voice_shadow.py#L453) |
| function | `_persist_record` | `(record, *, template_output)` | Persist an AppraisalRecord to the shadow audit table. | [src](../../../core/services/inner_voice_shadow.py#L548) |
| function | `_generate_via_llm` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…)` | Narrative-first wrapper for backwards compatibility. | [src](../../../core/services/inner_voice_shadow.py#L572) |
| function | `generate_helpful_signal_via_llm` | `(*, status, focus, work_signal, fallback, timeout_seconds=…)` | Production path for private_growth_note._helpful_signal. | [src](../../../core/services/inner_voice_shadow.py#L601) |
| function | `generate_private_summary_via_llm` | `(*, status, focus, uncertainty, work_signal, fallback, timeout_seconds=…)` | Production path for private_inner_note._private_summary. | [src](../../../core/services/inner_voice_shadow.py#L623) |
| function | `generate_voice_line_via_llm` | `(*, mood_tone, self_position, current_concern, current_pull, fallback, timeout_seconds=…)` | Production path for protected_inner_voice._voice_line. | [src](../../../core/services/inner_voice_shadow.py#L650) |
| function | `recent_comparisons` | `(function_name=…, *, limit=…)` | Pull recent shadow records for human comparison. | [src](../../../core/services/inner_voice_shadow.py#L679) |
| function | `shadow_stats` | `(function_name=…)` | Aggregate stats across all shadow records for one function. | [src](../../../core/services/inner_voice_shadow.py#L701) |

## `core/services/interlanguage_practice.py`
_Inter-sprog practice engine — internaliseret protokol på tværs af modeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_interlanguage_practice_table` | `(conn)` | Idempotently create interlanguage_practice table + index. | [src](../../../core/services/interlanguage_practice.py#L127) |
| function | `ensure_schema` | `()` | Bagudkompat: åbner en conn og kalder _ensure_interlanguage_practice_table. | [src](../../../core/services/interlanguage_practice.py#L173) |
| function | `_pick_term` | `(domain_filter=…)` | Pick a random core term, optionally filtered by domain. | [src](../../../core/services/interlanguage_practice.py#L187) |
| function | `_build_clause` | `()` | Build a single clause: <term> <primitive> <term> or !<term>. | [src](../../../core/services/interlanguage_practice.py#L196) |
| function | `generate_state_expression` | `(*, num_clauses=…, mood_override=…)` | Generate a state-expression from current mood and random composition. | [src](../../../core/services/interlanguage_practice.py#L212) |
| function | `record_expression` | `(expression_text, *, session_id=…, tick_id=…, trigger=…, peer_id=…)` | Record a state-expression in the practice log. | [src](../../../core/services/interlanguage_practice.py#L265) |
| function | `get_recent_expressions` | `(*, days=…, limit=…)` | Get recent state-expressions from the practice log. | [src](../../../core/services/interlanguage_practice.py#L298) |
| function | `get_expression_count` | `(*, since_hours=…)` | Count expressions recorded in the last N hours. | [src](../../../core/services/interlanguage_practice.py#L326) |
| function | `export_protocol` | `(*, recent_days=…, max_expressions=…)` | Eksportér hele inter-sprog-protokollen til model-skift. | [src](../../../core/services/interlanguage_practice.py#L342) |
| function | `practice_tick` | `(*, session_id=…, tick_id=…, mood=…)` | Kaldes fra heartbeat tick — generér og gem én state-expression. | [src](../../../core/services/interlanguage_practice.py#L390) |
| function | `export_mood_trace_for_period` | `(start, end)` | Eksportér Jarvis' mood-historie over en periode som (timestamp, mood) pairs. | [src](../../../core/services/interlanguage_practice.py#L430) |
| function | `interpolate_mood_at` | `(trace, target_iso)` | Linear-interpolér mellem nærmeste to mood-samples til target timestamp. | [src](../../../core/services/interlanguage_practice.py#L470) |
| function | `build_interlanguage_practice_surface` | `()` | Surface for Mission Control — 3 vital signs + dummy state ved ingen data. | [src](../../../core/services/interlanguage_practice.py#L516) |

## `core/services/internal_cadence.py`
_Internal cadence layer for non-visible inner producers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProducerSpec` | `` | — | [src](../../../core/services/internal_cadence.py#L63) |
| class | `ProducerTickResult` | `` | — | [src](../../../core/services/internal_cadence.py#L73) |
| function | `register_producer` | `(spec)` | Register a non-visible inner producer with the cadence layer. | [src](../../../core/services/internal_cadence.py#L87) |
| function | `deregister_producer` | `(name)` | Remove a producer from the cadence layer. | [src](../../../core/services/internal_cadence.py#L92) |
| function | `_evaluate_producer` | `(spec, *, now, last_visible_at, ran_this_tick, tempo=…)` | Evaluate whether a producer is due. | [src](../../../core/services/internal_cadence.py#L106) |
| class | `_ProducerWorker` | `` | Én persistent dæmon-tråd pr. producer, med kø og ledigheds-flag. | [src](../../../core/services/internal_cadence.py#L235) |
| method | `_ProducerWorker.__init__` | `(self, name)` | — | [src](../../../core/services/internal_cadence.py#L240) |
| method | `_ProducerWorker.busy` | `(self)` | Kører et job lige nu? | [src](../../../core/services/internal_cadence.py#L253) |
| method | `_ProducerWorker.alive` | `(self)` | — | [src](../../../core/services/internal_cadence.py#L257) |
| method | `_ProducerWorker.submit` | `(self, job)` | Læg job i køen. False = workeren er optaget af den forrige kørsel. | [src](../../../core/services/internal_cadence.py#L260) |
| method | `_ProducerWorker._loop` | `(self)` | — | [src](../../../core/services/internal_cadence.py#L269) |
| method | `_ProducerWorker.stop` | `(self)` | Luk workeren: luk dens DB-forbindelse i dens EGEN tråd, og stop. | [src](../../../core/services/internal_cadence.py#L279) |
| function | `_luk_denne_traads_forbindelse` | `()` | Kører i worker-tråden: luk den thread-lokale pool-forbindelse. | [src](../../../core/services/internal_cadence.py#L289) |
| function | `_get_worker` | `(navn)` | — | [src](../../../core/services/internal_cadence.py#L302) |
| function | `_stop_worker` | `(navn)` | — | [src](../../../core/services/internal_cadence.py#L311) |
| function | `stadig_i_flugt` | `(navn)` | Kører en tidligere kørsel af producenten stadig? | [src](../../../core/services/internal_cadence.py#L318) |
| function | `_noter_i_flugt` | `(navn, t)` | — | [src](../../../core/services/internal_cadence.py#L346) |
| function | `_run_producer_bounded` | `(spec, *, trigger, last_visible_at, timeout_s)` | Kør en producer i sin EGEN persistente worker-tråd med en hård timeout. | [src](../../../core/services/internal_cadence.py#L351) |
| function | `run_cadence_tick` | `(*, trigger=…, last_visible_at_iso=…)` | Run one cadence tick: evaluate and dispatch all registered producers. | [src](../../../core/services/internal_cadence.py#L411) |
| function | `get_cadence_state` | `()` | Return current cadence layer state for MC observability. | [src](../../../core/services/internal_cadence.py#L651) |
| function | `_ensure_producers_registered` | `()` | Register known producers if not already registered. | [src](../../../core/services/internal_cadence.py#L691) |
| function | `_valider_afhaengigheder` | `()` | Afvis manglende udbydere og cykler HOEJLYDT ved bootstrap. | [src](../../../core/services/internal_cadence.py#L726) |
| function | `run_cadence_tick_with_bootstrap` | `(*, trigger=…, last_visible_at_iso=…)` | Bootstrap producers and run a cadence tick. | [src](../../../core/services/internal_cadence.py#L770) |
| function | `_run_injection_refresh_tick` | `()` | Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path). | [src](../../../core/services/internal_cadence.py#L793) |
| function | `_scheduler_loop` | `()` | Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds. | [src](../../../core/services/internal_cadence.py#L808) |
| function | `start_cadence_scheduler` | `()` | Spawn the standalone cadence scheduler thread. Idempotent. | [src](../../../core/services/internal_cadence.py#L873) |
| function | `stop_cadence_scheduler` | `()` | Signal the scheduler thread to exit. Best-effort; daemon dies with process. | [src](../../../core/services/internal_cadence.py#L888) |

## `core/services/internal_cadence_central_wiring.py`
_Central-wiring cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_central_wiring_producers` | `()` | Run the Central-wiring registration blocks (unchanged order/behavior). | [src](../../../core/services/internal_cadence_central_wiring.py#L15) |

## `core/services/internal_cadence_core.py`
_Core-infra cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_core_producers` | `(register_producer)` | Register the core-infra producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_core.py#L19) |

## `core/services/internal_cadence_inner_life.py`
_Inner-life cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_inner_life_producers` | `(register_producer)` | Register the inner-life producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_inner_life.py#L24) |

## `core/services/internal_cadence_maintenance.py`
_Maintenance / health cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_maintenance_producers` | `(register_producer)` | Register the maintenance / health producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_maintenance.py#L23) |

## `core/services/internal_cadence_matrix.py`
_Matrix-themed cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_matrix_producers` | `(register_producer)` | Register the Matrix-themed producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_matrix.py#L18) |

## `core/services/internal_opposition_signal_tracking.py`
_Internal-opposition signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_internal_opposition_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L41) |
| function | `refresh_runtime_internal_opposition_signal_statuses` | `()` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L49) |
| function | `build_runtime_internal_opposition_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L53) |
| function | `_extract_internal_opposition_candidates` | `(*_args, **_kwargs)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L58) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L237) |
| function | `_internal_opposition_track_summary` | `(items, message)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L267) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L303) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L308) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L313) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L318) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L323) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L328) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L333) |
| function | `_world_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L338) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L343) |

## `core/services/interruption_notice.py`
_Afbrydelses-noten — en besked til MENNESKET, ikke til modellen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_interruption_notice` | `(text)` | Er dette runtimens afbrydelses-note frem for et aegte svar? Self-safe. | [src](../../../core/services/interruption_notice.py#L38) |
| function | `strip_interruption_notices` | `(history)` | Fjern afbrydelses-noter fra den historik modellen faar. Self-safe. | [src](../../../core/services/interruption_notice.py#L49) |

## `core/services/invocation_record.py`
_Durabel invokations-tilstand for kald ingen bliver spurgt om._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/invocation_record.py#L37) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/invocation_record.py#L41) |
| function | `recorded` | `(tool_name, arguments, *, run_id=…, session_id=…)` | Omslut et MUTERENDE kald med prepared → dispatching → completed/failed. | [src](../../../core/services/invocation_record.py#L48) |
| function | `markaer_mislykket` | `(iid)` | Sig at kaldet fejlede UDEN at kaste. | [src](../../../core/services/invocation_record.py#L103) |
| function | `_afslut` | `(iid, *, ok)` | — | [src](../../../core/services/invocation_record.py#L116) |

## `core/services/irony_daemon.py`
_Irony daemon — situational self-distance and absurd self-observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_irony_daemon` | `(*, skip_event_gate=…)` | — | [src](../../../core/services/irony_daemon.py#L20) |
| function | `get_latest_irony_observation` | `()` | — | [src](../../../core/services/irony_daemon.py#L52) |
| function | `build_irony_surface` | `()` | — | [src](../../../core/services/irony_daemon.py#L56) |
| function | `_maybe_reset_daily_count` | `()` | — | [src](../../../core/services/irony_daemon.py#L65) |
| function | `_collect_snapshot` | `()` | — | [src](../../../core/services/irony_daemon.py#L73) |
| function | `_detect_irony_conditions` | `(snapshot)` | — | [src](../../../core/services/irony_daemon.py#L98) |
| function | `_generate_observation` | `(snapshot, condition)` | — | [src](../../../core/services/irony_daemon.py#L111) |
| function | `_store_observation` | `(observation, condition)` | — | [src](../../../core/services/irony_daemon.py#L138) |

## `core/services/jarvis_brain.py`
_Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BrainEntry` | `` | — | [src](../../../core/services/jarvis_brain.py#L69) |
| method | `BrainEntry.__post_init__` | `(self)` | — | [src](../../../core/services/jarvis_brain.py#L96) |
| function | `_atomic_write` | `(path, content)` | Atomic file write via tmp + rename. Creates parent dirs as needed. | [src](../../../core/services/jarvis_brain.py#L125) |
| function | `parse_frontmatter` | `(path)` | Parse YAML frontmatter + body from a markdown file. | [src](../../../core/services/jarvis_brain.py#L133) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/jarvis_brain.py#L153) |
| function | `_parse_iso` | `(s)` | Parse ISO timestamp from string or pass-through if already datetime. | [src](../../../core/services/jarvis_brain.py#L161) |
| function | `render_entry_markdown` | `(entry)` | Render a BrainEntry as markdown with YAML frontmatter. | [src](../../../core/services/jarvis_brain.py#L174) |
| function | `entry_from_frontmatter` | `(fm, body)` | Build a BrainEntry from parsed frontmatter dict + body string. | [src](../../../core/services/jarvis_brain.py#L204) |
| function | `_workspace_root` | `()` | Base dir for brain-relative paths. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L310) |
| function | `_state_root` | `()` | — | [src](../../../core/services/jarvis_brain.py#L327) |
| function | `brain_dir` | `()` | Return the brain storage dir under JARVIS_HOME/shared/jarvis_brain. | [src](../../../core/services/jarvis_brain.py#L334) |
| function | `index_db_path` | `()` | — | [src](../../../core/services/jarvis_brain.py#L344) |
| function | `_ensure_wal` | `(conn, key)` | Slå WAL til én gang per (proces, db-sti). Persistent på filen. | [src](../../../core/services/jarvis_brain.py#L365) |
| function | `_ensure_schema` | `(conn, key)` | Opret/migrér index-schema — men kun når det faktisk mangler. | [src](../../../core/services/jarvis_brain.py#L382) |
| function | `connect_index` | `()` | — | [src](../../../core/services/jarvis_brain.py#L406) |
| function | `_ensure_index_schema_migrations` | `(conn)` | Bring pre-existing brain_index tables up to the current schema. | [src](../../../core/services/jarvis_brain.py#L418) |
| function | `_slugify` | `(s, max_len=…)` | — | [src](../../../core/services/jarvis_brain.py#L491) |
| function | `_file_hash` | `(text)` | — | [src](../../../core/services/jarvis_brain.py#L498) |
| function | `write_entry` | `(*, kind, title, content, visibility, domain, trigger=…, related=…, tags=…, source_url=…, source_chronicle=…, importance=…, now=…, skip_temporal=…)` | Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu). | [src](../../../core/services/jarvis_brain.py#L502) |
| function | `read_entry` | `(entry_id)` | Read a BrainEntry by id (loads from disk via index lookup). | [src](../../../core/services/jarvis_brain.py#L600) |
| function | `_index_path_for` | `(entry_id)` | Returns the relative path stored in brain_index for entry_id. | [src](../../../core/services/jarvis_brain.py#L616) |
| function | `compute_effective_salience` | `(entry, now)` | Compute time-decayed salience with bump amplification + importance gate. | [src](../../../core/services/jarvis_brain.py#L644) |
| function | `_embed_text` | `(text)` | Wrapper around eksisterende embedder. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L672) |
| function | `_embed_texts` | `(texts)` | Batch-variant af _embed_text: ÉT ollama round-trip for hele listen (via | [src](../../../core/services/jarvis_brain.py#L687) |
| function | `_embedding_to_blob` | `(v)` | — | [src](../../../core/services/jarvis_brain.py#L704) |
| function | `_embedding_from_blob` | `(blob, dim)` | — | [src](../../../core/services/jarvis_brain.py#L708) |
| function | `embed_pending_entries` | `()` | Embed alle entries i index'et der mangler embedding. Returnerer antal. | [src](../../../core/services/jarvis_brain.py#L712) |
| function | `search_brain` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Hybrid embedding search: 0.7*cosine + 0.3*effective_salience + temporal boost. | [src](../../../core/services/jarvis_brain.py#L743) |
| function | `search_brain_scored` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Som search_brain, men returnerer (score, entry_id) uden at læse filerne. | [src](../../../core/services/jarvis_brain.py#L773) |
| function | `_compute_search_temporal_boost` | `(candidate_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost for search candidates. | [src](../../../core/services/jarvis_brain.py#L957) |
| function | `bump_salience` | `(entry_id, now=…, *, min_interval_hours=…)` | Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil. | [src](../../../core/services/jarvis_brain.py#L998) |
| function | `archive_entry` | `(entry_id, *, reason=…, now=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/services/jarvis_brain.py#L1059) |
| function | `supersede` | `(*, old_ids, new_id, now=…)` | Mark old entries as superseded by new_id (keeps files in place). | [src](../../../core/services/jarvis_brain.py#L1090) |
| function | `prune_orphaned_index_rows` | `(*, maks_andel=…)` | Fjern indeks-rækker hvis markdown-fil er væk. Den MODSATTE retning. | [src](../../../core/services/jarvis_brain.py#L1116) |
| function | `rebuild_index_from_files` | `()` | Scan brain_dir() for .md files; new/changed hash → update index. | [src](../../../core/services/jarvis_brain.py#L1181) |
| function | `_extract_text_for_entry` | `(entry_id, *, rel_path=…, title=…)` | Read entry content from disk for entity/semantic analysis. | [src](../../../core/services/jarvis_brain.py#L1318) |
| function | `_temporal_similarity_score` | `(hours_apart)` | Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h. | [src](../../../core/services/jarvis_brain.py#L1372) |
| function | `_cosine_similarity` | `(a_vec, b_vec)` | — | [src](../../../core/services/jarvis_brain.py#L1382) |
| function | `_compute_temporal_confidence` | `(*, temporal, semantic, entity, is_chain, chain_score=…)` | Combine four signals into a single confidence score (0.0–1.0). | [src](../../../core/services/jarvis_brain.py#L1389) |
| function | `_compute_chain_score` | `(*, new_entry, cand_entry, hours_apart, cand_related)` | Compute chain signal score (0.0–1.0) between two entries. | [src](../../../core/services/jarvis_brain.py#L1408) |
| function | `infer_temporal_edges` | `(new_entry_id, now=…)` | Run four-signal inference between a new entry and all existing active entries. | [src](../../../core/services/jarvis_brain.py#L1458) |
| function | `_store_temporal_edge` | `(from_id, to_id, confidence, reasoning, now)` | Insert or update a temporal edge with combined confidence. | [src](../../../core/services/jarvis_brain.py#L1647) |
| function | `_store_temporal_edges_batch` | `(edges, *, now)` | Skriv mange kanter i én transaktion (målt 25/9-2026). | [src](../../../core/services/jarvis_brain.py#L1677) |
| function | `get_temporal_neighbors` | `(entry_id, min_confidence=…, limit=…)` | Get tidligere inferred temporal neighbors for an entry. | [src](../../../core/services/jarvis_brain.py#L1706) |
| function | `temporal_boost_recall` | `(entry_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost scores for a set of entry IDs. | [src](../../../core/services/jarvis_brain.py#L1736) |
| function | `prune_stale_edges` | `(*, max_age_days=…, min_confidence=…)` | Remove stale temporal edges with low confidence. | [src](../../../core/services/jarvis_brain.py#L1792) |
| function | `prune_unreadable_edges` | `()` | Fjern kanter der beviseligt ALDRIG læses — uanset alder. | [src](../../../core/services/jarvis_brain.py#L1819) |
| function | `prune_dense_edges` | `(*, max_per_node=…)` | Loft pr. node: behold kun de ``max_per_node`` stærkeste kanter pr. endepunkt. | [src](../../../core/services/jarvis_brain.py#L1861) |
| function | `full_rebuild` | `(*, batch_size=…)` | Genberegn alle temporale edges fra bunden. | [src](../../../core/services/jarvis_brain.py#L1921) |
| function | `_emit_jarvis_brain_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/jarvis_brain.py#L1983) |

## `core/services/jarvis_brain_daemon.py`
_Jarvis Brain background daemon — tre uafhængige loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reindex_once` | `()` | Et enkelt reindex-pass. Returnerer antal file changes opdaget. | [src](../../../core/services/jarvis_brain_daemon.py#L26) |
| function | `reindex_loop` | `(stop_event)` | Long-running loop. Stops cleanly when stop_event is set. | [src](../../../core/services/jarvis_brain_daemon.py#L42) |
| function | `find_duplicate_proposals` | `(*, threshold=…, kinds=…)` | Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold. | [src](../../../core/services/jarvis_brain_daemon.py#L67) |
| function | `_call_ollamafreeapi` | `(prompt)` | Free OllamaFreeAPI — public-safe job. Returns parsed JSON or None on fail. | [src](../../../core/services/jarvis_brain_daemon.py#L121) |
| function | `_model_is_available` | `(tag_names, model)` | Pure: er `model` til stede blandt Ollamas /api/tags-navne? Matcher både | [src](../../../core/services/jarvis_brain_daemon.py#L142) |
| function | `_call_local_ollama` | `(prompt)` | Ollama-kald for personal/intimate brain-jobs (summaries + contradiction). | [src](../../../core/services/jarvis_brain_daemon.py#L155) |
| function | `_resolve_local_chat_target` | `()` | Find configured local-lane chat model + HOST from provider router. | [src](../../../core/services/jarvis_brain_daemon.py#L214) |
| function | `_resolve_local_chat_model` | `()` | Bagudkompatibel wrapper: kun modellen. Se `_resolve_local_chat_target`. | [src](../../../core/services/jarvis_brain_daemon.py#L239) |
| function | `_parse_json_loose` | `(text)` | Parse JSON from possibly noisy LLM output. Looks for first {...} block. | [src](../../../core/services/jarvis_brain_daemon.py#L244) |
| function | `_llm_contradiction_check` | `(a, b)` | Privacy-routed contradiction check. | [src](../../../core/services/jarvis_brain_daemon.py#L265) |
| function | `_state_path` | `()` | Override target in tests via monkeypatch. | [src](../../../core/services/jarvis_brain_daemon.py#L292) |
| function | `_read_state` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L299) |
| function | `_write_state` | `(state)` | — | [src](../../../core/services/jarvis_brain_daemon.py#L310) |
| function | `record_proposal_rejection` | `(phase, *, proposal_id)` | Track rejection. After 3 in a row for 'theme' phase, auto-pause. | [src](../../../core/services/jarvis_brain_daemon.py#L319) |
| function | `record_proposal_acceptance` | `(phase, *, proposal_id)` | Reset rejection streak on acceptance. | [src](../../../core/services/jarvis_brain_daemon.py#L341) |
| function | `is_theme_consolidation_paused` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L350) |
| function | `resume_theme_consolidation` | `()` | Manuel reaktivering. Nulstiller streak + paused flag. | [src](../../../core/services/jarvis_brain_daemon.py#L354) |
| function | `_run_theme_consolidation_pass` | `()` | Søndags-pass: group observations efter domain, find temaer. | [src](../../../core/services/jarvis_brain_daemon.py#L362) |
| function | `run_theme_consolidation_if_active` | `()` | Kør tema-pass hvis ikke paused. Returnerer antal forslag genereret. | [src](../../../core/services/jarvis_brain_daemon.py#L371) |
| function | `regenerate_summary` | `(*, target_visibility=…)` | Regenererer state/jarvis_brain_summary.md. | [src](../../../core/services/jarvis_brain_daemon.py#L409) |
| function | `auto_archive_low_salience` | `()` | Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage. | [src](../../../core/services/jarvis_brain_daemon.py#L490) |
| function | `b4_catchup_infer_once` | `(*, batch_size=…)` | Find active entries with no temporal edges and run inference on them. | [src](../../../core/services/jarvis_brain_daemon.py#L556) |
| function | `b4_edge_maintenance_once` | `()` | Run one pass of B4 edge maintenance: catchup + prune. | [src](../../../core/services/jarvis_brain_daemon.py#L625) |
| function | `_consolidation_summary_loop` | `(stop_event)` | Daily consolidation + summary + B4 edge maintenance scheduler. | [src](../../../core/services/jarvis_brain_daemon.py#L663) |
| function | `run_consolidation_pass` | `()` | Single consolidation pass: phase 1 (dedup) + phase 2 (contradictions). | [src](../../../core/services/jarvis_brain_daemon.py#L749) |
| function | `start_brain_daemon` | `()` | Start the three brain daemon threads. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L768) |
| function | `stop_brain_daemon` | `()` | Signal stop and wait briefly for threads to exit. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L791) |

## `core/services/jarvis_brain_reflection.py`
_End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_reflection_envelope` | `(*, chronicle_summary)` | Build the envelope text shown to visible Jarvis at end-of-day. | [src](../../../core/services/jarvis_brain_reflection.py#L31) |
| function | `build_internal_nudge` | `(*, count_so_far)` | Soft nudge after 3+ remember_this calls in same reflection slot. | [src](../../../core/services/jarvis_brain_reflection.py#L36) |
| function | `_was_active_today` | `()` | Best-effort tjek om Jarvis havde aktivitet i dag. | [src](../../../core/services/jarvis_brain_reflection.py#L49) |
| function | `_build_today_chronicle_summary` | `()` | Build a short summary of today's chronicle entries. | [src](../../../core/services/jarvis_brain_reflection.py#L73) |
| function | `_run_reflection_turn` | `(chronicle_summary)` | Trigger en visible-Jarvis tur med reflection-envelope. | [src](../../../core/services/jarvis_brain_reflection.py#L86) |
| function | `run_daily_reflection_if_active` | `()` | Entry point for the daily slot trigger. | [src](../../../core/services/jarvis_brain_reflection.py#L110) |
| function | `build_jarvis_brain_reflection_surface` | `()` | Surface the daily reflection slot without triggering it. | [src](../../../core/services/jarvis_brain_reflection.py#L126) |

## `core/services/jarvis_brain_visibility.py`
_Privacy-gate for Jarvis Brain recall._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_owner_id` | `()` | Hentet via owner_resolver. Wrapped så tests kan monkeypatche. | [src](../../../core/services/jarvis_brain_visibility.py#L14) |
| function | `can_recall` | `(entry_visibility, ceiling)` | True if entry's visibility is permitted at the given ceiling. | [src](../../../core/services/jarvis_brain_visibility.py#L30) |
| function | `session_visibility_ceiling` | `(session)` | Beregn visibility-ceiling for en session. | [src](../../../core/services/jarvis_brain_visibility.py#L35) |

## `core/services/jarvis_ui_guard.py`
_Normaliserer og validerer ``jarvis-ui``-blokke FØR de når chatten._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normaliser_form` | `(raw)` | Flyt JSON'en ned på sin egen linje og lukke-fencen på sin egen linje. | [src](../../../core/services/jarvis_ui_guard.py#L73) |
| function | `_reparer_json` | `(tekst)` | Ret de entydige JSON-fejl. Rører intet der allerede er gyldigt. | [src](../../../core/services/jarvis_ui_guard.py#L86) |
| function | `_ret_laengder` | `(tekst)` | Juster ``comparison``-values op til kolonneantallet. Returnerer ny JSON. | [src](../../../core/services/jarvis_ui_guard.py#L94) |
| function | `_tekst` | `(vaerdi)` | Spejl rendererens ``text()``: kun strenge, trimmet, tom = falsk. | [src](../../../core/services/jarvis_ui_guard.py#L131) |
| function | `_liste` | `(vaerdi, maks)` | Spejl rendererens ``list()``: kun objekter, afkortet til ``maks``. | [src](../../../core/services/jarvis_ui_guard.py#L136) |
| function | `_diagnosticér` | `(data)` | Afgør om rendereren viser blokken. Returnerer (niveau, fejl). | [src](../../../core/services/jarvis_ui_guard.py#L143) |
| function | `_validér` | `(tekst)` | — | [src](../../../core/services/jarvis_ui_guard.py#L249) |
| function | `normalisér` | `(text, *, run_id=…)` | Normalisér alle ``jarvis-ui``-blokke i teksten. Returnerer ny tekst. | [src](../../../core/services/jarvis_ui_guard.py#L269) |
| function | `_normalisér_indre` | `(text, *, run_id)` | — | [src](../../../core/services/jarvis_ui_guard.py#L285) |
| function | `_registrér` | `(aendringer, *, run_id)` | — | [src](../../../core/services/jarvis_ui_guard.py#L344) |
| function | `fejl_i_flader` | `(text)` | Returnér de fejl der gør en ``jarvis-ui``-blok død eller ufuldstændig. | [src](../../../core/services/jarvis_ui_guard.py#L364) |

## `core/services/jarvisx_bridge.py`
_JarvisX tool-bridge — bidirectional dispatch over WebSocket._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_dispatch_token` | `()` | Shared-secret som BEGGE processer kan udlede ens. | [src](../../../core/services/jarvisx_bridge.py#L48) |
| function | `_api_port` | `()` | Port for jarvis-api-procesen (hvor broen lever). Default 8080. | [src](../../../core/services/jarvisx_bridge.py#L89) |
| function | `_runtime_port` | `()` | Port for jarvis-runtime-procesen (autonome/wakeup-runs). Default 8011. | [src](../../../core/services/jarvisx_bridge.py#L100) |
| function | `_port_for_process` | `(role)` | Localhost-port for procesrollen. Begge processer kører SAMME uvicorn-app | [src](../../../core/services/jarvisx_bridge.py#L111) |
| function | `_looks_like_closed_ws` | `(exc)` | Er dette en 'send over en allerede-lukket WebSocket'-fejl? Starlette/uvicorn | [src](../../../core/services/jarvisx_bridge.py#L117) |
| function | `_ws_is_closed` | `(ws)` | Bedste-effort: er WS'en allerede lukket? Self-safe → False når ukendt, så vi | [src](../../../core/services/jarvisx_bridge.py#L127) |
| class | `PendingBridgeCall` | `` | — | [src](../../../core/services/jarvisx_bridge.py#L146) |
| class | `BridgeConnection` | `` | One live bridge connection. WS object is platform-dependent. | [src](../../../core/services/jarvisx_bridge.py#L155) |
| method | `BridgeConnection.send_raw` | `(self, data, *, timeout_s=…)` | Send raw JSON over WS with lock and timeout. | [src](../../../core/services/jarvisx_bridge.py#L184) |
| method | `BridgeConnection.send_invoke` | `(self, *, correlation_id, tool, args, timeout_ms, extra=…, stream_output=…)` | Send tool_invoke over WS and register the pending future. | [src](../../../core/services/jarvisx_bridge.py#L216) |
| method | `BridgeConnection.register_pending` | `(self, correlation_id, future, owning_loop, on_output=…)` | — | [src](../../../core/services/jarvisx_bridge.py#L270) |
| method | `BridgeConnection.deliver_output` | `(self, *, correlation_id, stream, seq, chunk, truncated=…)` | — | [src](../../../core/services/jarvisx_bridge.py#L283) |
| method | `BridgeConnection.deliver_result` | `(self, *, correlation_id, status, result=…, error=…, timing=…)` | Complete the pending future for this correlation_id. | [src](../../../core/services/jarvisx_bridge.py#L318) |
| method | `BridgeConnection.cancel_all_pending` | `(self, *, reason=…)` | Cancel all in-flight calls (e.g. on WS disconnect). | [src](../../../core/services/jarvisx_bridge.py#L367) |
| function | `_kan_forsvinde` | `(conn)` | Forlader den her klient broen naar brugeren kigger et andet sted hen? | [src](../../../core/services/jarvisx_bridge.py#L395) |
| class | `BridgeRegistry` | `` | Process-local registry of active bridges: user_id → client_id → bro. | [src](../../../core/services/jarvisx_bridge.py#L401) |
| method | `BridgeRegistry.__init__` | `(self)` | — | [src](../../../core/services/jarvisx_bridge.py#L414) |
| method | `BridgeRegistry._client_key` | `(conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L419) |
| method | `BridgeRegistry.register` | `(self, conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L422) |
| method | `BridgeRegistry.unregister` | `(self, conn)` | Remove ONLY if the registered bridge for this client IS this conn. | [src](../../../core/services/jarvisx_bridge.py#L444) |
| method | `BridgeRegistry._evict_if_current` | `(self, user_id, conn, *, reason)` | Fjern en stale/død bro fra registret HVIS den stadig er den aktuelle for | [src](../../../core/services/jarvisx_bridge.py#L459) |
| method | `BridgeRegistry._publish_presence` | `(self)` | Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og | [src](../../../core/services/jarvisx_bridge.py#L476) |
| method | `BridgeRegistry._diagnose_no_bridge` | `(self, user_id, *, stage, tool=…)` | Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt | [src](../../../core/services/jarvisx_bridge.py#L504) |
| method | `BridgeRegistry._foretrukken` | `(klienter)` | Broen der bruges naar intet vaerktoej peger et bestemt sted hen. | [src](../../../core/services/jarvisx_bridge.py#L581) |
| method | `BridgeRegistry.get_bridge` | `(self, user_id, *, tool=…)` | Broen for ``user_id`` — og med ``tool`` DEN der kan udfoere det. | [src](../../../core/services/jarvisx_bridge.py#L592) |
| method | `BridgeRegistry.list_bridges` | `(self, user_id)` | Alle forbundne klienter for en bruger (computer OG telefon). | [src](../../../core/services/jarvisx_bridge.py#L645) |
| method | `BridgeRegistry.list_user_ids` | `(self)` | user_id'er med en aktiv bro (til bro_broker / override-switch). | [src](../../../core/services/jarvisx_bridge.py#L649) |
| method | `BridgeRegistry.clear` | `(self)` | Test helper — drop all registrations. | [src](../../../core/services/jarvisx_bridge.py#L653) |
| method | `BridgeRegistry.dispatch` | `(self, *, user_id, tool, args, timeout_s=…, allow_cross_process=…, on_output=…)` | Send tool_invoke to user's bridge, await result or timeout. | [src](../../../core/services/jarvisx_bridge.py#L660) |
| method | `BridgeRegistry._dispatch_without_local_bridge` | `(self, *, user_id, tool, args, timeout_s, allow_cross_process, stage, on_output=…)` | Ingen LEVENDE lokal bro for user_id (aldrig registreret, eller netop evictet | [src](../../../core/services/jarvisx_bridge.py#L791) |
| method | `BridgeRegistry._forward_cross_process` | `(self, *, user_id, tool, args, timeout_s, target_port=…, on_output=…)` | HTTP-forward dispatch til den proces der holder broen (dens interne endpoint). | [src](../../../core/services/jarvisx_bridge.py#L854) |
| function | `set_main_loop` | `(loop)` | Register the main uvicorn loop. Called from app startup. | [src](../../../core/services/jarvisx_bridge.py#L979) |
| function | `get_main_loop` | `()` | Return the registered main loop, or None if not set yet. | [src](../../../core/services/jarvisx_bridge.py#L985) |

## `core/services/jobs_engine.py`
_Jobs Engine — proper async job queue with provider selection and cost tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_prune_completed_jobs` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L54) |
| class | `JobResult` | `` | — | [src](../../../core/services/jobs_engine.py#L81) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/jobs_engine.py#L95) |
| function | `_load` | `()` | — | [src](../../../core/services/jobs_engine.py#L99) |
| function | `_save` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L129) |
| function | `_med_laas` | `(*, timeout_s=…)` | Serialiser laes-aendr-skriv paa koe-filen — OGSAA paa tvaers af processer. | [src](../../../core/services/jobs_engine.py#L155) |
| function | `_opdater_job` | `(job_id, **felter)` | Skriv felter paa ÉT job, med en frisk laesning under laas. | [src](../../../core/services/jobs_engine.py#L212) |
| function | `register_handler` | `(job_type, handler)` | Register a handler function for a given job_type. | [src](../../../core/services/jobs_engine.py#L240) |
| function | `enqueue_job` | `(*, job_type, payload=…, allowed_providers=…, prefer_free_first=…, max_requests=…, max_tokens=…, max_usd=…, window_key=…, scheduled_job_id=…, priority=…)` | Create a new pending job. Returns job_id. | [src](../../../core/services/jobs_engine.py#L248) |
| function | `_enqueue_ulaast` | `(*, job_type, payload=…, allowed_providers=…, prefer_free_first=…, max_requests=…, max_tokens=…, max_usd=…, window_key=…, scheduled_job_id=…, priority=…)` | Selve indsaettelsen. Kaldes KUN med koe-laasen holdt. | [src](../../../core/services/jobs_engine.py#L272) |
| function | `select_provider` | `(allowed, *, prefer_free_first=…)` | Pick the first usable provider from the list. | [src](../../../core/services/jobs_engine.py#L327) |
| function | `_pop_next_pending` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L351) |
| function | `run_next_job` | `()` | Run the highest-priority pending job via its registered handler. | [src](../../../core/services/jobs_engine.py#L359) |
| function | `cancel_job` | `(job_id)` | Marker jobbet afbrudt. Returnerer om afbrydelsen blev REGISTRERET. | [src](../../../core/services/jobs_engine.py#L456) |
| function | `sweep_zombie_jobs` | `(stale_seconds=…)` | Marker 'running' jobs aeldre end stale_seconds som `lost`. | [src](../../../core/services/jobs_engine.py#L478) |
| function | `_fej_ulaast` | `(stale_seconds)` | — | [src](../../../core/services/jobs_engine.py#L500) |
| function | `all_jobs` | `()` | ALLE jobs — ingen hale klippet af. | [src](../../../core/services/jobs_engine.py#L534) |
| function | `list_jobs` | `(*, status=…, limit=…)` | — | [src](../../../core/services/jobs_engine.py#L551) |
| function | `build_jobs_engine_surface` | `()` | — | [src](../../../core/services/jobs_engine.py#L558) |

## `core/services/kerne_curator.py`
_Kerne-kurator — holder USER.md `## Kerne` kort og levende (blok A, 2026-09-04)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/kerne_curator.py#L33) |
| function | `_workspace_dir` | `()` | — | [src](../../../core/services/kerne_curator.py#L45) |
| function | `promotion_candidates` | `(workspace_dir)` | Lært-linjer der er brugt tit nok til at høre hjemme i Kerne. | [src](../../../core/services/kerne_curator.py#L54) |
| function | `demotion_candidates` | `(workspace_dir)` | De ældste Kerne-linjer der ligger ud over loftet (tomt når under). | [src](../../../core/services/kerne_curator.py#L74) |
| function | `_move_line` | `(*, text, to_core)` | Flyt én linje mellem `## Kerne` og `## Lært` i USER.md. Atomisk. | [src](../../../core/services/kerne_curator.py#L83) |
| function | `promote_to_kerne` | `(text)` | Flyt en Lært-linje op i Kerne (altid i prompten). | [src](../../../core/services/kerne_curator.py#L115) |
| function | `demote_from_kerne` | `(text)` | Flyt en Kerne-linje ned i Lært (kun når den er relevant). | [src](../../../core/services/kerne_curator.py#L120) |
| function | `build_proposal_text` | `(workspace_dir)` | Ugens ÉNE forslag — "" når Kerne er sund og intet er modnet. | [src](../../../core/services/kerne_curator.py#L125) |
| function | `run_kerne_curator` | `(*, force=…, now=…)` | Ugentlig kuratering. Self-throttlende og self-safe — kaster aldrig. | [src](../../../core/services/kerne_curator.py#L149) |

## `core/services/keyring_store.py`
_Per-bruger nøgle-håndtering (spec §16.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_keyring` | `()` | — | [src](../../../core/services/keyring_store.py#L31) |
| function | `_get_or_create_kek` | `()` | Master-KEK fra runtime.json; genereres + persisteres atomisk ved første brug. | [src](../../../core/services/keyring_store.py#L45) |
| function | `_server_get_dek` | `(user_id)` | Hent (eller generér + wrap) en brugers DEK fra DB, unwrapped med KEK. | [src](../../../core/services/keyring_store.py#L72) |
| function | `get_user_key` | `(user_id)` | Brugerens 256-bit DEK. Prøver OS keyring; ellers server-side KEK/DEK (headless). | [src](../../../core/services/keyring_store.py#L86) |
| function | `delete_user_key` | `(user_id)` | Slet en brugers DEK (GDPR §16.7) — krypteret data bliver derefter ulæseligt. | [src](../../../core/services/keyring_store.py#L102) |
| function | `derive_key_from_password` | `(password, salt)` | PBKDF2-HMAC-SHA256 nøgle-derivation (fallback, §16.3). 600k iterationer. | [src](../../../core/services/keyring_store.py#L126) |
| function | `new_salt` | `()` | Tilfældigt 16-byte salt (gemmes pr. bruger, ikke hemmeligt). | [src](../../../core/services/keyring_store.py#L134) |

## `core/services/klient_versioner.py`
_Hvilken udgave af appen sidder der i den anden ende?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rent` | `(vaerdi, tilladte=…)` | — | [src](../../../core/services/klient_versioner.py#L44) |
| function | `noter` | `(klient, version)` | Skriv den seneste version for én klient. True hvis noget blev skrevet. | [src](../../../core/services/klient_versioner.py#L53) |
| function | `alle` | `()` | Hvad kører der lige nu, pr. klient. Tom dict hvis ingen har sagt det. | [src](../../../core/services/klient_versioner.py#L84) |

## `core/services/layer_tension_daemon.py`
_Layer Tension daemon — detects when two or more cognitive layers pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_layer_tension_daemon` | `(snapshot)` | Detect layer tensions from runtime snapshot. | [src](../../../core/services/layer_tension_daemon.py#L35) |
| function | `_detect_tensions` | `(snapshot)` | — | [src](../../../core/services/layer_tension_daemon.py#L61) |
| function | `_store_tension` | `(tension, now)` | — | [src](../../../core/services/layer_tension_daemon.py#L143) |
| function | `get_active_tensions` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L190) |
| function | `build_layer_tension_surface` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L194) |

## `core/services/learning_pipeline_orchestrator.py`
_Learning Pipeline Orchestrator — Phase 3 (Loop Closure)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/learning_pipeline_orchestrator.py#L44) |
| function | `is_enabled` | `()` | Check killswitch. | [src](../../../core/services/learning_pipeline_orchestrator.py#L48) |
| function | `set_enabled` | `(value)` | Toggle killswitch without restart. | [src](../../../core/services/learning_pipeline_orchestrator.py#L57) |
| function | `_recent_events` | `(*, families, minutes=…)` | Fetch recent events from eventbus by family, ordered newest-first. | [src](../../../core/services/learning_pipeline_orchestrator.py#L66) |
| function | `_route_self_evaluation` | `(event)` | self_evaluation outcome → learning_policy + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L94) |
| function | `_route_learning_policy_rule` | `(event)` | learning_policy.rule_created (conf ≥ 0.7 + evidence ≥ 2) → abstraction + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L151) |
| function | `_route_counterfactual_cycle` | `(event)` | counterfactual.cycle_complete → skill distiller + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L212) |
| function | `_route_agent_run` | `(event)` | agent_run.completed → reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L261) |
| function | `run_pipeline` | `(*, force=…)` | Run one full pipeline routing cycle. | [src](../../../core/services/learning_pipeline_orchestrator.py#L296) |
| function | `run_reflect_cycle` | `()` | Thin wrapper for REFLECT phase integration. | [src](../../../core/services/learning_pipeline_orchestrator.py#L418) |

## `core/services/learning_policy_engine.py`
_Explicit learning policy engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_learning_policies_from_episode` | `(*, episode=…, source_run_id=…)` | Extract and reinforce active policy rules from a cognitive episode. | [src](../../../core/services/learning_policy_engine.py#L25) |
| function | `reinforce_learning_policy` | `(rule)` | Insert or strengthen a learning policy rule. | [src](../../../core/services/learning_policy_engine.py#L50) |
| function | `build_learning_policy_surface` | `(*, limit=…)` | Return active policy rules for prompt/conductor use. | [src](../../../core/services/learning_policy_engine.py#L101) |
| function | `build_learning_policy_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/learning_policy_engine.py#L130) |
| function | `_load_state` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L145) |
| function | `_latest_episode` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L152) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/learning_policy_engine.py#L157) |
| function | `_rule_from_episode` | `(*, episode, learning, attention, policy, source_run_id)` | — | [src](../../../core/services/learning_policy_engine.py#L167) |
| function | `_classify_rule_key` | `(*, policy_update, next_behavior, lesson)` | — | [src](../../../core/services/learning_policy_engine.py#L194) |
| function | `_target_context` | `(rule_key)` | — | [src](../../../core/services/learning_policy_engine.py#L209) |
| function | `_initial_confidence` | `(*, episode, learning)` | — | [src](../../../core/services/learning_policy_engine.py#L219) |
| function | `_surface_directive` | `(rules)` | — | [src](../../../core/services/learning_policy_engine.py#L233) |

## `core/services/ledger_canary.py`
_Efterfyld en session i ledgeren og slå skyggen til._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kolonner` | `(conn)` | — | [src](../../../core/services/ledger_canary.py#L44) |
| function | `backfill` | `(session_id)` | Skriv sessionens eksisterende beskeder ind i ledgeren. Idempotent. | [src](../../../core/services/ledger_canary.py#L49) |
| function | `enable_shadow` | `(session_id)` | Efterfyld, slå skyggen til, og MÅL med det samme om det holdt. | [src](../../../core/services/ledger_canary.py#L119) |
| function | `reseed` | `(session_id)` | Skriv sessionens ledger-hændelser HELT om, i tabellens rækkefølge. | [src](../../../core/services/ledger_canary.py#L154) |
| function | `_arm_sti` | `()` | — | [src](../../../core/services/ledger_canary.py#L203) |
| function | `arm_next_session` | `(*, note=…)` | Indrullér den NAESTE nye chat-session i skyggen. Én gang. | [src](../../../core/services/ledger_canary.py#L208) |
| function | `is_armed` | `()` | — | [src](../../../core/services/ledger_canary.py#L224) |
| function | `disarm` | `()` | — | [src](../../../core/services/ledger_canary.py#L232) |
| function | `maybe_enroll_new_session` | `(session_id)` | Kaldes naar en ny session oprettes. Fejler ALDRIG opad. | [src](../../../core/services/ledger_canary.py#L239) |

## `core/services/ledger_recovery.py`
_Afbrudte sessioner: se på dem uden at røre dem, og luk dem kun med skriveret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `inspect` | `(session_id)` | Se på sessionen UDEN at røre den. Tager ingen lease, skriver intet. | [src](../../../core/services/ledger_recovery.py#L49) |
| function | `recover` | `(session_id, *, owner=…, grund=…)` | Luk en åben tur med en balancerende hændelse. Kræver skriveret. | [src](../../../core/services/ledger_recovery.py#L77) |

## `core/services/ledger_write_path.py`
_Skrivevejen for en session hvor LEDGEREN er sandheden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `LedgerWriteFailed` | `` | Skrivningen nåede ikke ledgeren. Kalderen har IKKE fået sin besked gemt. | [src](../../../core/services/ledger_write_path.py#L42) |
| function | `append_message` | `(session_id, *, role, content, created_at=…, user_id=…, workspace_name=…, reasoning_content=…, git_sha=…, content_json=…, message_id=…, owner=…)` | Skriv én besked gennem ledgeren og lad projektoren lave rækken. | [src](../../../core/services/ledger_write_path.py#L46) |

## `core/services/lessons.py`
_Lessons service — from mistake to next conversation (memory repair 2026-09-04, R4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today` | `()` | — | [src](../../../core/services/lessons.py#L29) |
| function | `_topic_from` | `(text)` | — | [src](../../../core/services/lessons.py#L33) |
| function | `_clip` | `(text, n)` | — | [src](../../../core/services/lessons.py#L38) |
| function | `record_correction` | `(*, session_id, user_words, jarvis_words=…, topic=…)` | Bjørn corrected the previous turn. Active immediately — his word is authoritative. | [src](../../../core/services/lessons.py#L43) |
| function | `record_self_acknowledged_correction` | `(*, session_id, user_words, jarvis_words=…)` | Jarvis indroemmede selv at han tog fejl — brug Bjoerns foregaaende ord. | [src](../../../core/services/lessons.py#L65) |
| function | `record_tool_error` | `(*, tool_name, error_text, context=…)` | A tool call failed. Proposed until it happens twice, then active. | [src](../../../core/services/lessons.py#L108) |
| function | `record_review_lessons` | `(lessons, source)` | Self-review / regret / arc-rule lessons → proposed (active at evidence ≥ 2). | [src](../../../core/services/lessons.py#L125) |
| function | `_format` | `(lesson)` | — | [src](../../../core/services/lessons.py#L139) |
| function | `build_lessons_section` | `(user_message, *, limit_similar=…, limit_strong=…)` | Render the lessons block for the prompt, or "" when nothing is active. | [src](../../../core/services/lessons.py#L149) |

## `core/services/life_milestones.py`
_Life milestones — identity-defining moments surfaced in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_milestones_file` | `()` | — | [src](../../../core/services/life_milestones.py#L17) |
| function | `_manifest_file` | `()` | — | [src](../../../core/services/life_milestones.py#L21) |
| function | `get_milestones_for_prompt` | `(max_chars=…)` | Return a formatted milestones block for prompt injection, or None. | [src](../../../core/services/life_milestones.py#L25) |
| function | `get_manifest_excerpt` | `(max_chars=…)` | Return first ~600 chars of MANIFEST.md as a first-principles reminder. | [src](../../../core/services/life_milestones.py#L47) |
| function | `build_life_history_prompt_section` | `()` | Combine milestones + manifest excerpt into a prompt section. | [src](../../../core/services/life_milestones.py#L63) |
| function | `append_milestone` | `(text)` | Append a new milestone entry to MILESTONES.md. Returns True on success. | [src](../../../core/services/life_milestones.py#L71) |
| function | `build_life_milestones_surface` | `()` | — | [src](../../../core/services/life_milestones.py#L88) |
| function | `_emit_life_milestones_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/life_milestones.py#L103) |

## `core/services/life_projects.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_life_project` | `(*, title, why, source=…, source_id=…, priority=…)` | — | [src](../../../core/services/life_projects.py#L12) |
| function | `build_life_projects_surface` | `()` | — | [src](../../../core/services/life_projects.py#L36) |
| function | `abandon_life_project` | `(initiative_id, *, note=…)` | — | [src](../../../core/services/life_projects.py#L50) |
| function | `endorse_life_project` | `(initiative_id, *, note=…)` | «Det er i orden» — projektet lever videre, nu med et menneskes ja bag sig. | [src](../../../core/services/life_projects.py#L57) |
| function | `tick_life_projects_reassessment` | `(*, trigger=…, last_visible_at=…)` | Periodisk re-vurdering af aktive life projects. | [src](../../../core/services/life_projects.py#L66) |

## `core/services/lifecycle_hooks.py`
_Livscyklus-hooks server-side — paritet med jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_allow` | `(context=…)` | — | [src](../../../core/services/lifecycle_hooks.py#L85) |
| function | `matcher_matches` | `(matcher, tool_name, command=…)` | Rammer et matcher-moenster dette tool-kald? Ren. | [src](../../../core/services/lifecycle_hooks.py#L91) |
| function | `decide` | `(results)` | Saml flere hook-svar til ét. Ren. | [src](../../../core/services/lifecycle_hooks.py#L129) |
| function | `config_path` | `()` | `~/.jarvis-v2/config/hooks.json` — config er runtimens sandhed for | [src](../../../core/services/lifecycle_hooks.py#L161) |
| function | `load_hooks` | `()` | {haendelse: [hook, ...]}. Self-safe → tomt. | [src](../../../core/services/lifecycle_hooks.py#L168) |
| function | `hooks_for` | `(event)` | Konfigurerede hooks for én haendelse. Self-safe → tom liste. | [src](../../../core/services/lifecycle_hooks.py#L184) |
| function | `_run_command_hook` | `(hook, context, user_id=…)` | Koer et shell-script med kontekst paa stdin. Exit 2 = block (jarvis-codes | [src](../../../core/services/lifecycle_hooks.py#L192) |
| function | `_run_http_hook` | `(hook, context)` | POST konteksten; svarets `action`/`message` gaelder. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L233) |
| function | `_run_command_hook_async` | `(hook, context, user_id=…)` | Operator-grenen, kaldt fra det loop broen selv lever paa. | [src](../../../core/services/lifecycle_hooks.py#L256) |
| function | `fire_async` | `(event, context, user_id=…)` | Som `fire`, men kan koere operator-hooks. Brug denne fra async-kode. | [src](../../../core/services/lifecycle_hooks.py#L282) |
| function | `run_hook` | `(event, hook, context, user_id=…)` | Koer ÉN hook. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L313) |
| function | `_advar_om_uvirksom_dom` | `(event, dom)` | Sig det hoejt naar en hook doemmer paa en haendelse der ikke kan handle. | [src](../../../core/services/lifecycle_hooks.py#L332) |
| function | `fire` | `(event, context, user_id=…)` | Fyr alle hooks for en haendelse og saml dommen. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L345) |

## `core/services/live_job_events.py`
_Bounded, process-local live projection of background-job events._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_timestamp` | `()` | — | [src](../../../core/services/live_job_events.py#L23) |
| class | `JobEvent` | `` | — | [src](../../../core/services/live_job_events.py#L28) |
| method | `JobEvent.as_dict` | `(self)` | — | [src](../../../core/services/live_job_events.py#L37) |
| class | `JobSubscription` | `` | — | [src](../../../core/services/live_job_events.py#L49) |
| method | `JobSubscription.__init__` | `(self, owner, *, session_id, initial_events, needs_snapshot, snapshot_cursor, queue_size)` | — | [src](../../../core/services/live_job_events.py#L50) |
| method | `JobSubscription.close` | `(self)` | — | [src](../../../core/services/live_job_events.py#L73) |
| method | `JobSubscription._deliver` | `(self, event)` | — | [src](../../../core/services/live_job_events.py#L79) |
| method | `JobSubscription._enqueue` | `(self, event)` | — | [src](../../../core/services/live_job_events.py#L87) |
| class | `LiveJobEventHub` | `` | — | [src](../../../core/services/live_job_events.py#L130) |
| method | `LiveJobEventHub.__init__` | `(self, *, replay_size=…)` | — | [src](../../../core/services/live_job_events.py#L131) |
| method | `LiveJobEventHub.publish` | `(self, event_type, *, job_key, session_id, source, payload)` | — | [src](../../../core/services/live_job_events.py#L139) |
| method | `LiveJobEventHub.subscribe` | `(self, *, session_id, after, queue_size=…)` | — | [src](../../../core/services/live_job_events.py#L166) |
| method | `LiveJobEventHub._unsubscribe` | `(self, subscription)` | — | [src](../../../core/services/live_job_events.py#L197) |
| method | `LiveJobEventHub.snapshot_cursor` | `(self)` | — | [src](../../../core/services/live_job_events.py#L201) |
| function | `publish` | `(event_type, *, job_key, session_id, source, payload)` | — | [src](../../../core/services/live_job_events.py#L209) |
| function | `subscribe` | `(*, session_id, after, queue_size=…)` | — | [src](../../../core/services/live_job_events.py#L226) |
| function | `snapshot_cursor` | `()` | — | [src](../../../core/services/live_job_events.py#L232) |
| function | `reset_for_tests` | `()` | — | [src](../../../core/services/live_job_events.py#L236) |

## `core/services/live_job_sources.py`
_Incremental adapters from canonical background jobs to live job events._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run` | `(coro)` | Run one bridge coroutine from the pump's synchronous worker context. | [src](../../../core/services/live_job_sources.py#L16) |
| class | `LiveJobSourcePump` | `` | Sample server/operator logs while a live Desk subscriber exists. | [src](../../../core/services/live_job_sources.py#L39) |
| method | `LiveJobSourcePump.__init__` | `(self, *, snapshot_reader, user_id, operator_reader=…)` | — | [src](../../../core/services/live_job_sources.py#L42) |
| method | `LiveJobSourcePump._publish` | `(self, event_type, source, job, payload)` | — | [src](../../../core/services/live_job_sources.py#L65) |
| method | `LiveJobSourcePump._reconcile` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L75) |
| method | `LiveJobSourcePump._terminal` | `(job, *, running=…)` | — | [src](../../../core/services/live_job_sources.py#L110) |
| method | `LiveJobSourcePump._finish` | `(self, key, job, exit_code)` | — | [src](../../../core/services/live_job_sources.py#L115) |
| method | `LiveJobSourcePump._sample_server` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L126) |
| method | `LiveJobSourcePump._sample_operator` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L145) |
| method | `LiveJobSourcePump.sample_once` | `(self)` | Force one reconciliation and one sample of both machine sources. | [src](../../../core/services/live_job_sources.py#L188) |
| method | `LiveJobSourcePump.add_subscriber` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L194) |
| method | `LiveJobSourcePump.remove_subscriber` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L205) |
| method | `LiveJobSourcePump._loop` | `(self)` | — | [src](../../../core/services/live_job_sources.py#L211) |

## `core/services/liveness_registry.py`
_Liveness-registry (Stage 2, liveness-audit 2026-06-15)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_table` | `(name)` | Returnér klassifikation for en tabel. Ukendt → 'unclassified' (IKKE 'død'). | [src](../../../core/services/liveness_registry.py#L335) |
| function | `is_alive` | `(name)` | True hvis tabellen IKKE er forældreløs/død. Afløst/manuel/aktiv tæller som levende. | [src](../../../core/services/liveness_registry.py#L343) |
| function | `classify_module` | `(name)` | Klassifikation for et MODUL. Ukendt → 'unclassified' (IKKE 'doedt'). | [src](../../../core/services/liveness_registry.py#L348) |
| function | `module_persists` | `(name)` | False for et modul der kaldes men gemmer i hukommelsen. | [src](../../../core/services/liveness_registry.py#L360) |
| function | `module_is_alive` | `(name)` | True naar modulet ikke er doedt. En `projektion` gemmer intet og lever. | [src](../../../core/services/liveness_registry.py#L365) |
| function | `liveness_summary` | `()` | Aggregeret overblik — til Mission Control / anti-konfabulations-flade. | [src](../../../core/services/liveness_registry.py#L375) |

## `core/services/living_executive.py`
_Living Executive — Jarvis' active impulse/choice/action loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/living_executive.py#L64) |
| function | `_load_state` | `()` | — | [src](../../../core/services/living_executive.py#L68) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/living_executive.py#L79) |
| function | `build_living_executive_surface` | `(*, limit=…)` | — | [src](../../../core/services/living_executive.py#L83) |
| function | `choose_impulse` | `(events)` | — | [src](../../../core/services/living_executive.py#L108) |
| function | `process_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L120) |
| function | `run_once` | `(*, events=…)` | One non-daemon pass used by tests and manual MC experiments. | [src](../../../core/services/living_executive.py#L127) |
| function | `execute_impulse` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L137) |
| function | `_impulse_from_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L171) |
| function | `_impulse` | `(*, source_event_id, source_kind, felt_signal, impulse, intensity, action_id, choice, payload, cooldown_key, cooldown_seconds=…)` | — | [src](../../../core/services/living_executive.py#L374) |
| function | `_genoptag_loft_naaet` | `()` | Hvor mange genoptagelser er der fyret i det sidste vindue? | [src](../../../core/services/living_executive.py#L401) |
| function | `_noter_genoptagelse` | `()` | — | [src](../../../core/services/living_executive.py#L415) |
| function | `_action_schedule_self_wakeup` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L425) |
| function | `_action_record_focus_intent` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L481) |
| function | `_action_create_jarvis_brain_observation` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L500) |
| function | `_action_propose_tool_plan` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L515) |
| function | `_record_trace` | `(impulse, *, status, outcome, details=…)` | — | [src](../../../core/services/living_executive.py#L556) |
| function | `_attach_memory_precedents` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L623) |
| function | `_recent_memory_precedents` | `(*, action_hint=…, tool_hint=…, limit=…)` | — | [src](../../../core/services/living_executive.py#L637) |
| function | `_choice_bias_from_precedents` | `(impulse, precedents)` | — | [src](../../../core/services/living_executive.py#L672) |
| function | `_emotional_choice_precedents` | `(*, limit)` | — | [src](../../../core/services/living_executive.py#L692) |
| function | `_tool_family` | `(tool_name)` | — | [src](../../../core/services/living_executive.py#L712) |
| function | `_runnable_tool_proposals` | `(*, tool_name, status, reason, precedents)` | — | [src](../../../core/services/living_executive.py#L720) |
| function | `_aftertaste` | `(*, status, impulse)` | — | [src](../../../core/services/living_executive.py#L781) |
| function | `_afbrudte_fra_db` | `(*, minutter=…, maks=…)` | Afbrydelses-events fra DB'en — delt paa tvaers af processer. | [src](../../../core/services/living_executive.py#L793) |
| function | `_session_for_run` | `(run_id)` | Hvilken SAMTALE hørte dette run til? "" naar den ikke kan afgøres. | [src](../../../core/services/living_executive.py#L836) |
| function | `_allerede_besvaret` | `(run_id)` | Er brugeren gaaet videre siden den her koersel doede? | [src](../../../core/services/living_executive.py#L875) |
| function | `indhent_forsoemte_afbrydelser` | `(*, minutter=…)` | Genoptag crash-draebte koersler der doede FOER nogen lyttede. | [src](../../../core/services/living_executive.py#L940) |
| function | `start_listener` | `()` | — | [src](../../../core/services/living_executive.py#L981) |
| function | `stop_listener` | `()` | — | [src](../../../core/services/living_executive.py#L1002) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/living_executive.py#L1011) |

## `core/services/living_heartbeat_cycle.py`
_Living Heartbeat Cycle — Jarvis' inner life rhythm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `determine_life_phase` | `(*, hour=…)` | Determine current life phase based on time of day. | [src](../../../core/services/living_heartbeat_cycle.py#L111) |
| function | `_should_enter_play_mode` | `()` | Return True when internal state calls for unstructured exploration. | [src](../../../core/services/living_heartbeat_cycle.py#L156) |
| function | `format_life_phase_for_prompt` | `(phase)` | Format life phase info for heartbeat prompt injection. | [src](../../../core/services/living_heartbeat_cycle.py#L176) |
| function | `build_living_heartbeat_cycle_surface` | `()` | MC surface for living heartbeat cycle. | [src](../../../core/services/living_heartbeat_cycle.py#L193) |
| function | `_emit_living_heartbeat_cycle_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/living_heartbeat_cycle.py#L204) |

