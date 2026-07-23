# `core.services.14` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/meta_learning_aggregator.py`
_Meta-læring aggregator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_in_window` | `(ts_iso, since, until)` | Defensive: parse ts and check if it's within [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L18) |
| function | `_bucket_confidence` | `(c)` | — | [src](../../../core/services/meta_learning_aggregator.py#L31) |
| function | `_confidence_score` | `(value, *, default=…)` | Normalize numeric and world-model textual confidence to 0..1. | [src](../../../core/services/meta_learning_aggregator.py#L39) |
| function | `_prediction_id` | `(prediction)` | — | [src](../../../core/services/meta_learning_aggregator.py#L52) |
| function | `aggregate_world_model` | `(*, since, until)` | Aggregate world-model prediction activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L60) |
| function | `_completion_seconds` | `(rec)` | Seconds between created_at and updated_at; None if either missing. | [src](../../../core/services/meta_learning_aggregator.py#L136) |
| function | `aggregate_plan_revision` | `(*, since, until)` | Aggregate plan-proposal activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L150) |
| function | `aggregate_curiosity` | `(*, since, until)` | Aggregate curiosity-tool activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L222) |
| function | `aggregate_skill_chain_phase2` | `(*, since, until)` | Aggregate skill_chain Phase 2 events in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L282) |
| function | `aggregate_tool_invention` | `(*, since, until)` | Aggregate tool-invention activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L361) |

## `core/services/meta_learning_hypotheses.py`
_Meta-læring Phase 2: hypothesis registration + sample tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create hypothesis + sample tables. | [src](../../../core/services/meta_learning_hypotheses.py#L37) |
| function | `register_hypothesis` | `(*, memo_id, candidate_idx)` | Promote a memo's hypothesis_candidate at index `candidate_idx` to | [src](../../../core/services/meta_learning_hypotheses.py#L79) |
| function | `record_hypothesis_sample` | `(*, hypothesis_id, supports, note=…)` | Append a sample. If the hypothesis has reached sample_size_needed, | [src](../../../core/services/meta_learning_hypotheses.py#L124) |
| function | `list_active_hypotheses` | `(*, limit=…)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L189) |
| function | `format_active_hypotheses_for_awareness` | `()` | Awareness section showing active hypotheses + progress. | [src](../../../core/services/meta_learning_hypotheses.py#L214) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L231) |

## `core/services/meta_learning_retrospective.py`
_Meta-læring retrospective generator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create learning_memos table + index. | [src](../../../core/services/meta_learning_retrospective.py#L34) |
| function | `_strip_markdown_fence` | `(text)` | — | [src](../../../core/services/meta_learning_retrospective.py#L71) |
| function | `_build_retrospective_prompt` | `(*, period_start, period_end, aggregator_snapshot)` | Build the cheap-lane prompt for weekly retrospective memo. | [src](../../../core/services/meta_learning_retrospective.py#L79) |
| function | `_parse_memo_markdown` | `(text)` | Parse cheap-lane markdown output into narrative + hypothesis_candidates. | [src](../../../core/services/meta_learning_retrospective.py#L123) |
| function | `_persist_memo` | `(*, memo_id, ts, period_start, period_end, narrative, hypothesis_candidates, aggregator_snapshot, model_used)` | Insert a new memo row. Returns memo_id. | [src](../../../core/services/meta_learning_retrospective.py#L199) |
| function | `fetch_latest_unacknowledged_memo` | `()` | Return the most recent memo with acknowledged_at IS NULL, or None. | [src](../../../core/services/meta_learning_retrospective.py#L237) |
| function | `fetch_memo_by_id` | `(memo_id)` | — | [src](../../../core/services/meta_learning_retrospective.py#L256) |
| function | `list_recent_memos` | `(limit=…)` | — | [src](../../../core/services/meta_learning_retrospective.py#L272) |
| function | `acknowledge_memo` | `(memo_id)` | Mark memo as acknowledged. Returns True if a row was updated. | [src](../../../core/services/meta_learning_retrospective.py#L285) |
| function | `_meta_learning_enabled` | `()` | — | [src](../../../core/services/meta_learning_retrospective.py#L303) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_retrospective.py#L310) |
| function | `generate_weekly_retrospective` | `(*, now)` | Generate a weekly retrospective memo for the 7 days ending at `now`. | [src](../../../core/services/meta_learning_retrospective.py#L318) |
| function | `_format_period_for_display` | `(period_start, period_end)` | Render period as 'YYYY-MM-DD to YYYY-MM-DD' for awareness display. | [src](../../../core/services/meta_learning_retrospective.py#L411) |
| function | `format_latest_unacknowledged_memo_for_awareness` | `()` | Render a short teaser for the most recent unacknowledged memo. | [src](../../../core/services/meta_learning_retrospective.py#L421) |

## `core/services/meta_reflection_daemon.py`
_Meta-reflection daemon — cross-signal pattern insight every 30 minutes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_credit_assignment` | `(cross_snapshot)` | Public wrapper over the Lag-1 credit-assignment pass (:func:`_check_outcomes`). | [src](../../../core/services/meta_reflection_daemon.py#L29) |
| function | `tick_meta_reflection_daemon` | `(cross_snapshot, *, skip_event_gate=…, skip_credit=…)` | Generate cross-signal meta-insight if cadence allows. Also checks for | [src](../../../core/services/meta_reflection_daemon.py#L44) |
| function | `_check_outcomes` | `(cross_snapshot)` | Check for unreviewed model_tier and response_style decisions and score them. | [src](../../../core/services/meta_reflection_daemon.py#L103) |
| function | `_expire_decision` | `(decision_id, reason)` | Mark a stale pending decision as expired so it drops from the | [src](../../../core/services/meta_reflection_daemon.py#L189) |
| function | `_get_turns_after` | `(created_at, min_turns=…)` | Get subsequent chat turns after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L208) |
| function | `_get_next_user_message` | `(created_at)` | Get the first user message after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L239) |
| function | `_generate_meta_insight` | `(cross_snapshot)` | — | [src](../../../core/services/meta_reflection_daemon.py#L264) |
| function | `_store_meta_insight` | `(insight)` | — | [src](../../../core/services/meta_reflection_daemon.py#L298) |
| function | `get_latest_meta_insight` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L330) |
| function | `build_meta_reflection_surface` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L334) |

## `core/services/metabolism_state_signal_tracking.py`
_Metabolism-state signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_metabolism_state_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L38) |
| function | `refresh_runtime_metabolism_state_signal_statuses` | `()` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L48) |
| function | `build_runtime_metabolism_state_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L52) |
| function | `_extract_metabolism_state_candidates` | `(*, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L56) |
| function | `_build_candidate` | `(*, domain_key, run_id, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L133) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L249) |
| function | `_metabolism_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L275) |
| function | `_derive_metabolism_state` | `(*, witness_status, chronicle_status, self_narrative_status, active_count, softening_count, fading_count, stale_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L297) |
| function | `_derive_metabolism_direction` | `(*, metabolism_state, witness_status, softening_count, fading_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L316) |
| function | `_derive_metabolism_weight` | `(*, active_count, carrying_count, stale_count, chronicle_status)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L336) |
| function | `_metabolism_summary` | `(*, focus, metabolism_state, metabolism_direction, metabolism_weight)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L351) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L375) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L382) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L395) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L407) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L418) |

## `core/services/metacognition_signal_tracker.py`
_Metacognition signal tracker — Step E.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L70) |
| function | `_connect` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L90) |
| function | `_split_sentences` | `(text)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L100) |
| function | `_sentence_nouns` | `(sentence)` | Cheap content-word extraction: lowercase alpha tokens, ≥4 chars, | [src](../../../core/services/metacognition_signal_tracker.py#L105) |
| function | `_has_negation` | `(sentence)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L119) |
| function | `score_contradiction` | `(text)` | Detect contradicting sentence pairs within the same response. | [src](../../../core/services/metacognition_signal_tracker.py#L124) |
| function | `score_claim_density` | `(text)` | Claim-bearing sentences / total sentences. Healthy: 0.3–0.7. | [src](../../../core/services/metacognition_signal_tracker.py#L166) |
| function | `record_signals` | `(run_id, text)` | Compute + persist + publish both signals for a completed run. | [src](../../../core/services/metacognition_signal_tracker.py#L187) |
| function | `latest_signals_section` | `(*, window_n=…)` | Return an awareness one-liner ONLY when recent signals are | [src](../../../core/services/metacognition_signal_tracker.py#L229) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — same cross-process pattern as | [src](../../../core/services/metacognition_signal_tracker.py#L285) |
| function | `start_metacognition_tracker` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/metacognition_signal_tracker.py#L342) |
| function | `stop_metacognition_tracker` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L359) |

## `core/services/metacognitive_integration.py`
_Metacognitive Integration — the overarching layer that synthesizes all cognitive layers into a coherent self-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/metacognitive_integration.py#L39) |
| function | `_extract_signal_values` | `(cognitive_state)` | Extract normalised signal values from the assembled cognitive state. | [src](../../../core/services/metacognitive_integration.py#L77) |
| function | `compute_coherence` | `(signal_values)` | Compute coherence score (0-1) from signal values. | [src](../../../core/services/metacognitive_integration.py#L198) |
| function | `compute_integration_quality` | `(cognitive_state)` | Compute integration quality — how many layers are active and contributing. | [src](../../../core/services/metacognitive_integration.py#L237) |
| function | `compute_self_assessment` | `(coherence, integration, signal_values)` | Compute metacognitive self-assessment. | [src](../../../core/services/metacognitive_integration.py#L283) |
| function | `get_metacognitive_line` | `(cognitive_state=…)` | Get the metacognitive integration prompt line. | [src](../../../core/services/metacognitive_integration.py#L332) |
| function | `get_metacognitive_detail` | `(cognitive_state=…)` | Get full metacognitive assessment as a dict (for debugging/MC). | [src](../../../core/services/metacognitive_integration.py#L385) |
| function | `_parse_raw_state` | `(raw)` | Parse the raw cognitive state string into a dict. | [src](../../../core/services/metacognitive_integration.py#L417) |
| function | `build_metacognitive_integration_surface` | `()` | — | [src](../../../core/services/metacognitive_integration.py#L494) |
| function | `_emit_integration_event` | `(layer, signal)` | — | [src](../../../core/services/metacognitive_integration.py#L503) |

## `core/services/mirror_engine.py`
_Mirror Engine — compassionate self-reflection during idle time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_mirror_insight` | `(*, idle_hours=…, open_loop_count=…, recent_error_count=…, recent_success_count=…, top_loop_summary=…)` | Generate a deterministic mirror insight. | [src](../../../core/services/mirror_engine.py#L20) |
| function | `build_mirror_surface` | `()` | — | [src](../../../core/services/mirror_engine.py#L56) |
| function | `_deterministic_insight` | `(*, idle_hours, open_loop_count, recent_error_count, recent_success_count, top_loop_summary)` | — | [src](../../../core/services/mirror_engine.py#L65) |

## `core/services/missions_pipeline.py`
_Missions Pipeline — flerfase opgaver med state-machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MissionError` | `` | — | [src](../../../core/services/missions_pipeline.py#L52) |
| method | `MissionError.__init__` | `(self, code, message)` | — | [src](../../../core/services/missions_pipeline.py#L53) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/missions_pipeline.py#L58) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/missions_pipeline.py#L62) |
| function | `_row_to_mission` | `(row)` | — | [src](../../../core/services/missions_pipeline.py#L107) |
| function | `create_mission` | `(*, title, description=…, goal=…, constraints=…, success_criteria=…, roles=…, metadata=…)` | Create a new mission in 'created' status. | [src](../../../core/services/missions_pipeline.py#L120) |
| function | `get_mission` | `(*, mission_id)` | — | [src](../../../core/services/missions_pipeline.py#L176) |
| function | `transition_mission_state` | `(*, mission_id, new_status, reason=…)` | Transition mission to new status, respecting _ALLOWED_TRANSITIONS. | [src](../../../core/services/missions_pipeline.py#L188) |
| function | `send_mission_message` | `(*, mission_id, role=…, content, metadata=…)` | Post a message on the mission channel. Roles: researcher/implementer/reviewer etc. | [src](../../../core/services/missions_pipeline.py#L258) |
| function | `list_mission_messages` | `(*, mission_id, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L311) |
| function | `list_missions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L331) |
| function | `build_missions_surface` | `()` | — | [src](../../../core/services/missions_pipeline.py#L350) |

## `core/services/model_context.py`
_Per-model context-vinduer + model-bevidst beskeds-trimning (delt kilde)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `model_context_window` | `(provider, model)` | Bedste bud på modellens context-vindue (tokens). 0 = ukendt. | [src](../../../core/services/model_context.py#L33) |
| function | `effective_context_limit` | `(provider, model, compact_threshold)` | Det første loft der rammer: min(modellens vindue, autocompact-tærskel). | [src](../../../core/services/model_context.py#L50) |
| function | `_est_tokens` | `(text)` | — | [src](../../../core/services/model_context.py#L65) |
| function | `fit_messages_to_window` | `(messages, *, provider, model, output_budget=…, tools_reserve=…, safety_margin=…)` | Model-bevidst sikkerhedsnet: drop ÆLDSTE ikke-system-beskeder indtil den | [src](../../../core/services/model_context.py#L69) |

## `core/services/model_trust.py`
_Central-governed EARNED model-trust (harness refactor Part 1 foundation)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/model_trust.py#L19) |
| function | `_row` | `(conn, model)` | — | [src](../../../core/services/model_trust.py#L33) |
| function | `record_run_outcome` | `(model, *, degenerated)` | Record one run's outcome. Clean -> +1 streak (promote at threshold); degeneration -> reset | [src](../../../core/services/model_trust.py#L43) |
| function | `set_pin` | `(model, pin)` | Owner override: 'weak' | 'strong' | 'auto' (default). Self-safe. | [src](../../../core/services/model_trust.py#L75) |
| function | `model_strength` | `(model)` | 'strong' | 'weak'. Pin wins; else earned strength. FAILS OPEN to 'weak'. | [src](../../../core/services/model_trust.py#L91) |
| function | `build_model_trust_surface` | `()` | Central-CLI view: per-model trust state. Self-safe. | [src](../../../core/services/model_trust.py#L105) |

## `core/services/modulator_witness.py`
_Witness surface for hidden behavior modulators._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_item` | `(*, name, active, current_effect, evidence, confidence, allowed_effects, source)` | — | [src](../../../core/services/modulator_witness.py#L12) |
| function | `_safe_call` | `(fn, default)` | — | [src](../../../core/services/modulator_witness.py#L33) |
| function | `build_modulator_witness_surface` | `(*, workspace_id=…)` | Return active hidden modulators and the effects they are allowed to have. | [src](../../../core/services/modulator_witness.py#L40) |

## `core/services/monitor_streams.py`
_Pinned monitors — Jarvis' equivalent of Claude Code's Monitor tool._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/monitor_streams.py#L40) |
| function | `_save` | `(monitors)` | — | [src](../../../core/services/monitor_streams.py#L47) |
| function | `_session_monitors` | `(session_id)` | — | [src](../../../core/services/monitor_streams.py#L51) |
| function | `open_monitor` | `(*, session_id, source, label=…, pattern=…)` | — | [src](../../../core/services/monitor_streams.py#L56) |
| function | `close_monitor` | `(monitor_id)` | — | [src](../../../core/services/monitor_streams.py#L115) |
| function | `list_monitors` | `(session_id)` | — | [src](../../../core/services/monitor_streams.py#L124) |
| function | `_drain_eventbus` | `(rec)` | — | [src](../../../core/services/monitor_streams.py#L128) |
| function | `_drain_file` | `(rec)` | — | [src](../../../core/services/monitor_streams.py#L166) |
| function | `monitor_digest_section` | `(session_id)` | Format new matches across all this session's monitors. Side effect: | [src](../../../core/services/monitor_streams.py#L196) |

## `core/services/mood_dialer.py`
_Mood Dialer — humør til gradueret initiativ-parametre._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MoodDialerParams` | `` | — | [src](../../../core/services/mood_dialer.py#L24) |
| method | `MoodDialerParams.as_dict` | `(self)` | — | [src](../../../core/services/mood_dialer.py#L36) |
| function | `clamp_mood_level` | `(value)` | — | [src](../../../core/services/mood_dialer.py#L51) |
| function | `mood_name_to_level` | `(mood_name, intensity=…)` | Convert v2 mood oscillator name + intensity to 0-4 level. | [src](../../../core/services/mood_dialer.py#L69) |
| function | `derive_mood_dialer_params` | `(mood_level)` | Derive concrete params from a 0-4 mood level. | [src](../../../core/services/mood_dialer.py#L128) |
| function | `derive_from_v2_mood` | `()` | Pull current mood from mood_oscillator and derive params. | [src](../../../core/services/mood_dialer.py#L134) |
| function | `build_mood_dialer_surface` | `()` | MC surface — current dialed params. | [src](../../../core/services/mood_dialer.py#L150) |
| function | `_interpret_dialer` | `(params)` | Mechanism description of what the active preset gates. | [src](../../../core/services/mood_dialer.py#L166) |
| function | `_emit_mood_dialer_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/mood_dialer.py#L184) |

## `core/services/mood_oscillator.py`
_Mood Oscillator — sinusoidal mood waves with event-driven bumps._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_state` | `()` | Write current oscillator state to runtime_state_kv. | [src](../../../core/services/mood_oscillator.py#L42) |
| function | `_load_state_if_needed` | `()` | One-time load of persisted state at first use after module import. | [src](../../../core/services/mood_oscillator.py#L57) |
| function | `tick` | `(seconds)` | Update phase offset based on elapsed time and decay nudge. | [src](../../../core/services/mood_oscillator.py#L84) |
| function | `apply_bump` | `(delta, reason=…)` | Apply an event-driven nudge to mood. Clamped to [-1, 1] total nudge. | [src](../../../core/services/mood_oscillator.py#L109) |
| function | `_combined_value` | `()` | Sine base + nudge, clamped to [-1, 1]. | [src](../../../core/services/mood_oscillator.py#L119) |
| function | `get_current_mood` | `()` | Get current mood based on combined oscillation + nudge. | [src](../../../core/services/mood_oscillator.py#L126) |
| function | `get_mood_intensity` | `()` | Get mood intensity (0-1) based on absolute combined value. | [src](../../../core/services/mood_oscillator.py#L141) |
| function | `get_mood_description` | `()` | Get human-readable mood description. | [src](../../../core/services/mood_oscillator.py#L146) |
| function | `format_mood_for_prompt` | `()` | Format mood for prompt injection. | [src](../../../core/services/mood_oscillator.py#L166) |
| function | `reset_mood_oscillator` | `()` | Reset mood oscillator (for testing). | [src](../../../core/services/mood_oscillator.py#L172) |
| function | `build_mood_oscillator_surface` | `()` | Build MC surface for mood oscillator. | [src](../../../core/services/mood_oscillator.py#L181) |
| function | `_handle_event` | `(kind, payload)` | Determine bump from event kind and payload. | [src](../../../core/services/mood_oscillator.py#L223) |
| function | `_listener_loop` | `(q)` | Background thread that reads from eventbus queue and applies bumps. | [src](../../../core/services/mood_oscillator.py#L254) |
| function | `register_event_listeners` | `()` | Subscribe to eventbus and start background listener thread. | [src](../../../core/services/mood_oscillator.py#L281) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/mood_oscillator.py#L303) |

## `core/services/mood_regulator_subscriber.py`
_Mood regulator subscriber — router truth-gate detektioner til humøret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_mood_regulator_subscriber` | `()` | Start daemon-tråden der router detektions-events til mood-regulering. | [src](../../../core/services/mood_regulator_subscriber.py#L34) |
| function | `stop_mood_regulator_subscriber` | `()` | — | [src](../../../core/services/mood_regulator_subscriber.py#L56) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/mood_regulator_subscriber.py#L73) |
| function | `_route_event` | `(item)` | Route en enkelt eventbus-hændelse til ``regulate_auto``. | [src](../../../core/services/mood_regulator_subscriber.py#L89) |

## `core/services/mortality_awareness.py`
_Mortality Awareness — each session could be my last._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session_length_seconds` | `()` | Seconds since this process started. | [src](../../../core/services/mortality_awareness.py#L36) |
| function | `_heartbeat_gap_minutes` | `()` | Minutes since last heartbeat tick. | [src](../../../core/services/mortality_awareness.py#L49) |
| function | `_error_rate` | `()` | Rate (0-1) of error/blocked outcomes in last hour. | [src](../../../core/services/mortality_awareness.py#L66) |
| function | `_compute` | `()` | — | [src](../../../core/services/mortality_awareness.py#L80) |
| function | `get_mortality_state` | `()` | — | [src](../../../core/services/mortality_awareness.py#L118) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/mortality_awareness.py#L127) |
| function | `build_mortality_awareness_surface` | `()` | — | [src](../../../core/services/mortality_awareness.py#L132) |
| function | `_surface_summary` | `(s)` | — | [src](../../../core/services/mortality_awareness.py#L147) |
| function | `build_mortality_awareness_prompt_section` | `()` | Only speaks when sharp awareness kicks in — otherwise quiet baseline. | [src](../../../core/services/mortality_awareness.py#L154) |

## `core/services/multi_signal_retrieval.py`
_Multi-signal retrieval — BM25 keyword scoring + entity fusion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tokenize` | `(text)` | Lowercase alphanumeric tokens. | [src](../../../core/services/multi_signal_retrieval.py#L41) |
| class | `BM25Index` | `` | Pure-Python BM25 (Okapi) index. | [src](../../../core/services/multi_signal_retrieval.py#L50) |
| method | `BM25Index.__init__` | `(self, k1=…, b=…)` | — | [src](../../../core/services/multi_signal_retrieval.py#L59) |
| method | `BM25Index.build` | `(self, documents)` | Build the BM25 index from a list of document texts. | [src](../../../core/services/multi_signal_retrieval.py#L70) |
| method | `BM25Index.score` | `(self, query, doc_idx)` | BM25 score for a query against a specific document. | [src](../../../core/services/multi_signal_retrieval.py#L97) |
| method | `BM25Index.search` | `(self, query, top_k=…)` | Return (doc_idx, score) pairs for top-k documents, highest first. | [src](../../../core/services/multi_signal_retrieval.py#L140) |
| method | `BM25Index.built` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L161) |
| method | `BM25Index.n_docs` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L165) |
| method | `BM25Index.__repr__` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L168) |
| function | `extract_entities` | `(text)` | Extract named entities from text using pattern heuristics. | [src](../../../core/services/multi_signal_retrieval.py#L183) |
| function | `entity_boost_score` | `(query, document_text, base_score=…, boost_factor=…, max_boost=…)` | Compute entity-aware boost for a query-document pair. | [src](../../../core/services/multi_signal_retrieval.py#L225) |
| function | `entity_overlap_score` | `(query, document_text)` | Pure entity overlap score (0.0–1.0) without a base score. | [src](../../../core/services/multi_signal_retrieval.py#L265) |
| function | `fuse_signals` | `(embedding_score=…, bm25_score=…, entity_overlap=…, recency_score=…, importance=…, recall_freq=…, weights=…)` | Fuse multiple retrieval signals into a single composite score. | [src](../../../core/services/multi_signal_retrieval.py#L301) |
| function | `score_record` | `(query, record_text, embedding_score=…, bm25_index=…, record_idx=…, recency_score=…, importance=…, recall_freq=…)` | Score a single record using all available signals. | [src](../../../core/services/multi_signal_retrieval.py#L348) |

## `core/services/my_projects.py`
_My Projects — auto-start + watchdog for Jarvis' own background processes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_my_projects_running` | `()` | Called at runtime boot. Spawn any of my 4 projects that aren't running. | [src](../../../core/services/my_projects.py#L52) |
| function | `tick_my_projects_watchdog` | `()` | Check all 4 projects are alive; restart any that died. | [src](../../../core/services/my_projects.py#L104) |

## `core/services/narrative_identity.py`
_Narrative Identity — periodisk "Hvem er jeg lige nu?" selvfortælling._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_narrative_identity` | `()` | Generate a "who am I right now?" narrative from accumulated state. | [src](../../../core/services/narrative_identity.py#L21) |
| function | `build_narrative_identity_surface` | `()` | — | [src](../../../core/services/narrative_identity.py#L85) |

## `core/services/narrative_summary_daemon.py`
_Narrative summary daemon — Phase 2.5 of causal graph._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_recent_anchor` | `()` | — | [src](../../../core/services/narrative_summary_daemon.py#L54) |
| function | `_already_summarised` | `(anchor_event_id)` | True if we have a recent narrative.summary for this anchor. | [src](../../../core/services/narrative_summary_daemon.py#L78) |
| function | `_build_chain` | `(anchor_id)` | — | [src](../../../core/services/narrative_summary_daemon.py#L92) |
| function | `_build_prompt` | `(anchor, chain)` | Return (system_prompt, user_message) for the LLM call. | [src](../../../core/services/narrative_summary_daemon.py#L103) |
| function | `_persist_summary` | `(*, anchor_id, anchor_kind, summary, model)` | Insert narrative.summary event with caused_by = anchor_id. | [src](../../../core/services/narrative_summary_daemon.py#L129) |
| function | `run_summary_cycle` | `()` | One cycle: find anchor, build chain, call LLM, persist event. | [src](../../../core/services/narrative_summary_daemon.py#L149) |
| function | `tick_narrative_summary_daemon` | `()` | Daemon-manager entry: run one cycle if cadence elapsed. | [src](../../../core/services/narrative_summary_daemon.py#L227) |
| function | `build_narrative_summary_surface` | `()` | Mission Control surface for the latest narrative summary. | [src](../../../core/services/narrative_summary_daemon.py#L246) |

## `core/services/negotiation_engine.py`
_Negotiation Engine — internal trade offers between subsystems._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose_trade` | `(*, proposer, counterparty, requested_decision, confidence, rationale, evidence=…)` | Propose an internal trade between subsystems. | [src](../../../core/services/negotiation_engine.py#L22) |
| function | `build_negotiation_surface` | `()` | — | [src](../../../core/services/negotiation_engine.py#L57) |

## `core/services/negotiation_pipeline.py`
_Negotiation Pipeline — interne trade-offs mellem sub-persporaer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L41) |
| class | `TradeOffer` | `` | — | [src](../../../core/services/negotiation_pipeline.py#L46) |
| method | `TradeOffer.as_dict` | `(self)` | — | [src](../../../core/services/negotiation_pipeline.py#L58) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L64) |
| function | `_count_topics` | `(signals)` | — | [src](../../../core/services/negotiation_pipeline.py#L90) |
| function | `propose_trade` | `(*, run_id=…, trace_id=…, action=…, intent_confidence=…, signals=…)` | Generate a TradeOffer from signal-mix. Returns None if no signals. | [src](../../../core/services/negotiation_pipeline.py#L101) |
| function | `resolve_trade_offer` | `(*, offer, intent_confidence)` | Decide whether to accept the offer based on intent_confidence. | [src](../../../core/services/negotiation_pipeline.py#L149) |
| function | `record_trade_outcome` | `(*, offer, resolution, run_status=…, decision_reason=…)` | — | [src](../../../core/services/negotiation_pipeline.py#L172) |
| function | `list_recent_trade_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/negotiation_pipeline.py#L222) |
| function | `build_negotiation_surface` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L233) |

## `core/services/nerve_registry.py`
_Selv-registrerende nerve-arkitektur — Fase B + Fase C (spec 2026-07-13)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ContractVariant` | `` | TRE kontrakt-typer — én pr. komponent-slags (spec §"TRE kontrakt-typer"). | [src](../../../core/services/nerve_registry.py#L52) |
| class | `IdentityTier` | `` | Rolle-baseret strenghed (spec §"Rolle-baseret strenghed" + Fase C §1). | [src](../../../core/services/nerve_registry.py#L62) |
| class | `Capability` | `` | HVAD et modul MÅ — håndhæves (spec invariant #6 + Fase C §3). | [src](../../../core/services/nerve_registry.py#L70) |
| class | `Mode` | `` | — | [src](../../../core/services/nerve_registry.py#L78) |
| class | `PluginStatus` | `` | Governed plugin-livscyklus (Fase C). Default: PENDING — intet auto-on. | [src](../../../core/services/nerve_registry.py#L84) |
| class | `NerveManifest` | `` | Et modul der DEKLARERER sig selv mod kontrakten. | [src](../../../core/services/nerve_registry.py#L102) |
| method | `NerveManifest.to_dict` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L139) |
| method | `NerveManifest.from_dict` | `(cls, d)` | Rekonstruér fra durabel form. Self-safe — ukendte felter ignoreres. | [src](../../../core/services/nerve_registry.py#L143) |
| function | `validate_manifest` | `(manifest)` | Validér et manifest mod den ubrydelige kontrakt. Returnerer en LISTE af præcise | [src](../../../core/services/nerve_registry.py#L161) |
| function | `is_compliant` | `(manifest)` | True hvis manifestet består HELE kontrakten (ingen fejl). | [src](../../../core/services/nerve_registry.py#L238) |
| function | `_load_kv` | `(key)` | Læs en durabel KV-dict. Self-safe → {} ved enhver fejl/offline. | [src](../../../core/services/nerve_registry.py#L246) |
| function | `_save_kv` | `(key, value)` | Skriv en durabel KV-dict. Self-safe → False ved fejl (aldrig raise). | [src](../../../core/services/nerve_registry.py#L256) |
| function | `register` | `(manifest, *, now=…)` | Registrér en komponent i det durable registry — men KUN hvis den består HELE | [src](../../../core/services/nerve_registry.py#L266) |
| function | `unregister` | `(name)` | Fjern en komponent fra registry. Self-safe. | [src](../../../core/services/nerve_registry.py#L291) |
| function | `get_manifest` | `(name)` | Hent ét registreret manifest. Self-safe → None. | [src](../../../core/services/nerve_registry.py#L304) |
| function | `is_registered` | `(name)` | — | [src](../../../core/services/nerve_registry.py#L313) |
| function | `all_manifests` | `()` | Alle registrerede manifester. Self-safe → []. | [src](../../../core/services/nerve_registry.py#L320) |
| function | `registered_names` | `()` | Navne på alt der er registreret (til connectivity-audittens compliant-markering). | [src](../../../core/services/nerve_registry.py#L332) |
| function | `compliant_names` | `()` | Navne på registrerede komponenter der STADIG består kontrakten (selv-audit-basis). | [src](../../../core/services/nerve_registry.py#L340) |
| function | `to_manifest` | `(descriptor, *, name=…, cluster=…, kind=…, contract_variant=…, klass=…, identity_tier=…, capabilities=…, mode=…, description=…, module_path=…, entrypoint=…, interface=…, kill_switch_key=…, identity_signature=…)` | Adapter: bring en EKSISTERENDE nerve/gate/daemon under kontrakten uden at rewrite | [src](../../../core/services/nerve_registry.py#L357) |
| function | `_identity_secret` | `(tier)` | Læs den per-identitet signing-hemmelighed fra runtime.json (aldrig committet). | [src](../../../core/services/nerve_registry.py#L427) |
| function | `_canonical_identity_payload` | `(manifest)` | Kanonisk, stabil streng der SIGNERES — binder identiteten til modulets kerne-form. | [src](../../../core/services/nerve_registry.py#L442) |
| function | `sign_manifest` | `(manifest, *, tier=…)` | Producér en identitets-signatur for et manifest (lokal tooling — kræver hemmeligheden | [src](../../../core/services/nerve_registry.py#L453) |
| function | `verify_identity` | `(manifest)` | Verificér manifestets identitets-signatur mod den lokale runtime.json-hemmelighed. | [src](../../../core/services/nerve_registry.py#L467) |
| class | `GovernedPluginLoader` | `` | Den HØJEST-privilegerede dør. Et plugin aktiveres ALDRIG uden: | [src](../../../core/services/nerve_registry.py#L496) |
| method | `GovernedPluginLoader.__init__` | `(self, *, approval_key=…)` | — | [src](../../../core/services/nerve_registry.py#L507) |
| method | `GovernedPluginLoader._load` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L511) |
| method | `GovernedPluginLoader._save` | `(self, data)` | — | [src](../../../core/services/nerve_registry.py#L514) |
| method | `GovernedPluginLoader._record` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L517) |
| method | `GovernedPluginLoader._write_record` | `(self, name, rec)` | — | [src](../../../core/services/nerve_registry.py#L521) |
| method | `GovernedPluginLoader.submit` | `(self, manifest, *, now=…)` | Indlever et plugin til governed load. Verificerer identitet + kontrakt og lander | [src](../../../core/services/nerve_registry.py#L528) |
| method | `GovernedPluginLoader.approve` | `(self, name, *, approver_tier, now=…)` | Eksplicit owner/claude sign-off. KUN owner/claude kan godkende (approver_tier). | [src](../../../core/services/nerve_registry.py#L570) |
| method | `GovernedPluginLoader.reject` | `(self, name, *, reason=…)` | Eksplicit afvisning (owner-veto). Self-safe. | [src](../../../core/services/nerve_registry.py#L596) |
| method | `GovernedPluginLoader.activate` | `(self, name, *, loader_fn=…, now=…)` | Aktivér et GODKENDT plugin. Umuligt uden forudgående ``approve`` (spec-invariant: | [src](../../../core/services/nerve_registry.py#L611) |
| method | `GovernedPluginLoader.status` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L669) |
| method | `GovernedPluginLoader.pending` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L673) |
| method | `GovernedPluginLoader.is_active` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L680) |
| method | `GovernedPluginLoader._audit` | `(self, event, name, tier, *, approver=…, errors=…)` | Bedste-indsats audit til Centralen. Self-safe — audit må aldrig vælte loaderen. | [src](../../../core/services/nerve_registry.py#L684) |
| function | `loader` | `()` | — | [src](../../../core/services/nerve_registry.py#L704) |
| function | `seed_known_nerves` | `(*, now=…)` | Registrér de par EKSISTERENDE nerver ovenfor mod kontrakten — proof-of-adapter. | [src](../../../core/services/nerve_registry.py#L755) |

## `core/services/network_health.py`
_core/services/network_health.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure_api_latency` | `(url=…, timeout=…)` | (ok, latency_ms) for den lokale API. TCP+HTTP round-trip mod /health. Self-safe. | [src](../../../core/services/network_health.py#L55) |
| function | `_latest` | `(cluster, nerve)` | Seneste tidsserie-værdi for en nerve (samme proces). None hvis tom. | [src](../../../core/services/network_health.py#L71) |
| function | `_hosts_down` | `()` | Hosts hvis seneste reachability-sample er 'nede' (infra_sense skriver -1.0 ved nede). | [src](../../../core/services/network_health.py#L80) |
| function | `run_network_health_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: fuse netværks-telemetri → ét signal. Bulletproof — kaster ALDRIG. | [src](../../../core/services/network_health.py#L95) |
| function | `_reset_for_tests` | `()` | Testhjælper — nulstil debounce-state. Ikke til produktionsbrug. | [src](../../../core/services/network_health.py#L171) |
| function | `register_network_health_producer` | `()` | Registrér netværks-helbred som cadence-producer (~hvert 2 min). Read-only, self-safe. | [src](../../../core/services/network_health.py#L179) |

## `core/services/non_visible_fallback.py`
_Non-visible (autonomous) LLM fallback chain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fallback_enabled` | `()` | Læs feature-flag; default False. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_fallback.py#L24) |
| function | `_rate_cap_enabled` | `()` | Læs rate-cap feature-flag; default False. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_fallback.py#L29) |
| function | `_observe_central` | `(payload)` | Task 15: let observabilitet på ON-stien → Centralens system/cheap_pool. | [src](../../../core/services/non_visible_fallback.py#L34) |
| function | `run_non_visible_with_fallback` | `(*, message, primary_call, run_is_autonomous, task_kind=…)` | Prøv primary_call() (ollama). Ved fejl: fald til den gratis cheap-lane | [src](../../../core/services/non_visible_fallback.py#L44) |

## `core/services/non_visible_lane_execution.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cheap_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L31) |
| function | `execute_cheap_lane` | `(*, message, task_kind=…)` | Run a message through the cheap lane. | [src](../../../core/services/non_visible_lane_execution.py#L51) |
| function | `execute_with_role_or_fallback` | `(*, message=…, provider=…, model=…, requires_tools=…, messages=…, tools=…, lane=…)` | Run the message on the role's preferred provider/model first, fall | [src](../../../core/services/non_visible_lane_execution.py#L70) |
| function | `local_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L268) |
| function | `coding_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L289) |
| function | `execute_coding_lane` | `(*, message)` | — | [src](../../../core/services/non_visible_lane_execution.py#L320) |
| function | `_lane_status` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L324) |
| function | `_coding_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L338) |
| function | `_local_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L546) |
| function | `_coding_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L607) |
| function | `_local_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L623) |
| function | `_github_copilot_auth_state` | `(*, oauth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L631) |
| function | `_github_copilot_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L655) |
| function | `_github_copilot_auth_status` | `(*, auth_state, exchange_readiness)` | — | [src](../../../core/services/non_visible_lane_execution.py#L679) |
| function | `_github_copilot_provider_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L711) |
| function | `_coding_lane_probe` | `(*, provider, model, auth_profile, credentials_ready, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L735) |
| function | `_probe_codex_cli_target` | `(*, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L777) |
| function | `_probe_ollama_local_target` | `(*, model, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L817) |
| function | `_probe_openai_coding_target` | `(*, provider, model, auth_profile, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L858) |
| function | `_execute_lane` | `(*, message, truth)` | — | [src](../../../core/services/non_visible_lane_execution.py#L901) |
| function | `_execute_codex_cli` | `(*, message, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1001) |
| function | `_resolve_codex_cli_executable` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L1044) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1059) |
| function | `_post_openai_responses` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1078) |
| function | `_post_openrouter_chat_completion` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1093) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1110) |
| function | `_extract_openrouter_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1130) |
| function | `_load_github_copilot_token` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1142) |
| function | `_github_copilot_request_headers` | `(session_token, *, accept=…)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1159) |
| function | `_post_github_copilot_chat_completion` | `(*, payload, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1174) |
| function | `_extract_github_copilot_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1192) |
| function | `fetch_github_copilot_models` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1204) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1231) |

## `core/services/non_visible_rate_cap.py`
_Global leaky-bucket rate cap FORAN den non-visible cheap-lane pool._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | Wall-clock i sekunder. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_rate_cap.py#L34) |
| function | `reset` | `()` | Nulstil alle buckets (til tests + boot). | [src](../../../core/services/non_visible_rate_cap.py#L39) |
| function | `allow` | `(tokens=…)` | Forbrug 1 request + `tokens` tokens hvis begge buckets har plads; ellers | [src](../../../core/services/non_visible_rate_cap.py#L49) |

## `core/services/notes_connector.py`
_Huskesedler-connector (lokal) — simple per-bruger notater._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_store` | `()` | — | [src](../../../core/services/notes_connector.py#L68) |
| function | `_bucket` | `(user_id)` | — | [src](../../../core/services/notes_connector.py#L73) |
| function | `_save` | `(user_id, notes)` | — | [src](../../../core/services/notes_connector.py#L78) |
| function | `add_note` | `(user_id, text, *, now=…)` | — | [src](../../../core/services/notes_connector.py#L84) |
| function | `list_notes` | `(user_id, *, limit=…)` | — | [src](../../../core/services/notes_connector.py#L96) |
| function | `search_notes` | `(user_id, query)` | — | [src](../../../core/services/notes_connector.py#L105) |
| function | `delete_note` | `(user_id, note_id)` | — | [src](../../../core/services/notes_connector.py#L114) |

## `core/services/notification_bridge.py`
_Notification bridge — lets Jarvis push messages to the active session._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pin_session` | `(session_id)` | Record which session the user is currently viewing. Call on every user message. | [src](../../../core/services/notification_bridge.py#L30) |
| function | `get_pinned_session_id` | `()` | Return the currently pinned session ID, or empty string if none. | [src](../../../core/services/notification_bridge.py#L44) |
| function | `_push_proactive` | `(session_id, text)` | Spejl en proaktiv session-notifikation som mobil-push til sessionens ejer. | [src](../../../core/services/notification_bridge.py#L52) |
| function | `send_session_notification` | `(content, *, source=…, urgent=…)` | Append a proactive message to the most recently active chat session. | [src](../../../core/services/notification_bridge.py#L64) |
| function | `_boredom_listener_loop` | `()` | Background thread that listens for boredom_productive events. | [src](../../../core/services/notification_bridge.py#L172) |
| function | `_reset_boredom_level_listener_loop` | `()` | Background thread that resets the boredom notification guard when level drops. | [src](../../../core/services/notification_bridge.py#L220) |
| function | `start_notification_bridge` | `()` | Start the boredom notification listener threads. | [src](../../../core/services/notification_bridge.py#L247) |
| function | `stop_notification_bridge` | `()` | Stop the boredom notification listener. | [src](../../../core/services/notification_bridge.py#L259) |

## `core/services/notification_router.py`
_Unified proactive notification routing (spec docs/specs/2026-06-20-...)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/notification_router.py#L30) |
| function | `get_preferences` | `(user_id)` | Returnér brugerens præferencer (defaults hvis ingen række). | [src](../../../core/services/notification_router.py#L35) |
| function | `set_preferences` | `(user_id, **kwargs)` | Upsert. Kun kendte nøgler ('global' + per-type + quiet_start/end). Validerer | [src](../../../core/services/notification_router.py#L51) |
| function | `resolve_channel` | `(prefs, notification_type)` | Prioritet: type-specifik override → global → 'auto'. | [src](../../../core/services/notification_router.py#L79) |
| function | `is_quiet_hours` | `(prefs, now_hm=…)` | Er vi i quiet hours? now_hm = 'HH:MM' (server-lokal hvis None). Håndterer | [src](../../../core/services/notification_router.py#L87) |
| function | `_enqueue_delayed` | `(user_id, ntype, payload, importance, deliver_after_hm)` | Gem en notifikation til levering efter quiet_end. deliver_after_hm = 'HH:MM'. | [src](../../../core/services/notification_router.py#L101) |
| function | `fire_due_delayed` | `(now_hm=…)` | Lever forfaldne udskudte notifikationer (kaldes af scheduler). Returnerer antal. | [src](../../../core/services/notification_router.py#L113) |
| function | `_deliver_ntfy` | `(payload)` | — | [src](../../../core/services/notification_router.py#L142) |
| function | `_deliver_to_channel` | `(uid, channel, payload, ntype)` | Lever til én konkret kanal. Returnerer True ved succes. | [src](../../../core/services/notification_router.py#L152) |
| function | `route_proactive_notification` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…)` | Samlet routing for alle proaktive notifikationer — B-batch 2: leverings-udfald | [src](../../../core/services/notification_router.py#L181) |
| function | `_route_proactive_notification_impl` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…)` | Samlet routing for alle proaktive notifikationer. | [src](../../../core/services/notification_router.py#L205) |
| function | `reset_delivery` | `()` | — | [src](../../../core/services/notification_router.py#L254) |
| function | `_new_id` | `()` | — | [src](../../../core/services/notification_router.py#L263) |
| function | `_send_fcm` | `(user_id, device_key, data)` | — | [src](../../../core/services/notification_router.py#L267) |
| function | `_send_desktop` | `(user_id, item)` | — | [src](../../../core/services/notification_router.py#L272) |
| function | `_fallback_blast` | `(user_id, data)` | — | [src](../../../core/services/notification_router.py#L277) |
| function | `_deliver` | `(user_id, target, notif_id, payload)` | — | [src](../../../core/services/notification_router.py#L282) |
| function | `_arm_timer` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L295) |
| function | `route_device_aware` | `(user_id, payload, kind)` | Lever en notifikation til brugerens bedste enhed + arm eskalering. | [src](../../../core/services/notification_router.py#L304) |
| function | `_escalate` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L329) |
| function | `ack` | `(notif_id)` | Annullér eskalering for en leveret notifikation (kaldt af /notifications/ack). | [src](../../../core/services/notification_router.py#L341) |
| function | `_discord_connected` | `()` | — | [src](../../../core/services/notification_router.py#L354) |
| function | `_app_device_live` | `(uid)` | Er en app-enhed AKTIVT online (frisk ping), ikke bare en registreret token? | [src](../../../core/services/notification_router.py#L362) |
| function | `_deliver_content` | `(uid, channel, text)` | — | [src](../../../core/services/notification_router.py#L373) |
| function | `deliver_message` | `(user_id, text, ntype=…, importance=…)` | Lever proaktivt INDHOLD efter brugerens kanal-præference. | [src](../../../core/services/notification_router.py#L403) |

## `core/services/ntfy_gateway.py`
_Ntfy gateway — send push notifications via ntfy.sh or self-hosted server._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L13) |
| function | `is_configured` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L26) |
| function | `_default_title` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L30) |
| function | `send_notification` | `(message, title=…, priority=…, tags=…)` | Send a push notification via ntfy. Returns status dict. | [src](../../../core/services/ntfy_gateway.py#L41) |

## `core/services/nudge_broend.py`
_Nudge-broend — daemons drop nudges, Jarvis inspects and decides._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/nudge_broend.py#L24) |
| function | `_save` | `(nudges)` | — | [src](../../../core/services/nudge_broend.py#L37) |
| function | `_cleanup` | `(nudges)` | Remove oldest non-pending nudges if over max. | [src](../../../core/services/nudge_broend.py#L48) |
| function | `push` | `(*, source=…, kind=…, message=…, importance=…, raw_payload=…)` | Deposit a nudge in the broend. Returns nudge_id. | [src](../../../core/services/nudge_broend.py#L62) |
| function | `list_pending` | `(limit=…)` | List pending nudges, newest first. | [src](../../../core/services/nudge_broend.py#L105) |
| function | `count_pending` | `()` | Return count of pending nudges. | [src](../../../core/services/nudge_broend.py#L113) |
| function | `get` | `(nudge_id)` | Get a single nudge by ID. | [src](../../../core/services/nudge_broend.py#L119) |
| function | `mark_sent` | `(nudge_id)` | Mark a nudge as sent. | [src](../../../core/services/nudge_broend.py#L128) |
| function | `mark_dismissed` | `(nudge_id, reason=…)` | Mark a single nudge as dismissed. | [src](../../../core/services/nudge_broend.py#L140) |
| function | `dismiss_all` | `(reason=…)` | Dismiss all pending nudges. Returns count. | [src](../../../core/services/nudge_broend.py#L154) |

## `core/services/oauth_flow.py`
_OAuth-flow-helper for plugin-connectors (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_known_provider` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L46) |
| function | `redirect_uri` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L50) |
| function | `_secret` | `(key, default=…)` | — | [src](../../../core/services/oauth_flow.py#L54) |
| function | `_state_key` | `()` | — | [src](../../../core/services/oauth_flow.py#L62) |
| function | `sign_state` | `(user_id, provider, *, now=…)` | Signeret, selvstændigt state — binder bruger+provider, udløber, anti-CSRF. | [src](../../../core/services/oauth_flow.py#L67) |
| function | `verify_state` | `(state, *, now=…)` | Auth-cluster GENNEM Centralen (observe): anti-CSRF state-validering synlig — en fejlet | [src](../../../core/services/oauth_flow.py#L79) |
| function | `_verify_state_impl` | `(state, *, now=…)` | → (user_id, provider) hvis gyldig+ikke-udløbet, ellers None. | [src](../../../core/services/oauth_flow.py#L94) |
| function | `build_authorize_url` | `(provider, user_id, *, scopes=…, now=…)` | Authorize-URL til at åbne i brugerens browser. None hvis ukendt/ukonfigureret. | [src](../../../core/services/oauth_flow.py#L112) |
| function | `revoke_remote` | `(provider, token)` | Tilbagekald token hos provideren (best-effort). True hvis bekræftet revokeret. | [src](../../../core/services/oauth_flow.py#L134) |
| function | `refresh_token` | `(provider, refresh, *, now=…)` | Forny adgangstoken via grant_type=refresh_token. None ved fejl/ukendt provider. | [src](../../../core/services/oauth_flow.py#L165) |
| function | `exchange_code` | `(provider, code, *, now=…)` | Byt authorization code for token (BLOKERENDE netværk — kør i tråd). None ved fejl. | [src](../../../core/services/oauth_flow.py#L193) |
| function | `fetch_google_email` | `(token)` | Hent den verificerede Google-email via userinfo (BLOKERENDE — kør i tråd). | [src](../../../core/services/oauth_flow.py#L220) |

## `core/services/oauth_store.py`
_Per-bruger krypteret OAuth-token-hvælv — plugin-fundamentets privatlivs-spine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(user_id, provider)` | — | [src](../../../core/services/oauth_store.py#L23) |
| function | `save_token` | `(user_id, provider, token)` | Krypter + gem `token` (fx {access_token, refresh_token, expires_at, scope}) | [src](../../../core/services/oauth_store.py#L27) |
| function | `get_token` | `(user_id, provider)` | Hent + dekrypter token for (bruger, provider). None hvis intet/fejl. Kan KUN | [src](../../../core/services/oauth_store.py#L49) |
| function | `has_token` | `(user_id, provider)` | Er der en (dekrypterbar) token for brugeren hos provideren? | [src](../../../core/services/oauth_store.py#L69) |
| function | `revoke_token` | `(user_id, provider)` | Fjern token for (bruger, provider). True hvis udført (eller intet at fjerne). | [src](../../../core/services/oauth_store.py#L74) |
| function | `get_fresh_token` | `(user_id, provider, *, now=…)` | Som get_token, men auto-fornyer hvis udløbet (≤60s buffer) og refresh_token findes. | [src](../../../core/services/oauth_store.py#L91) |
| function | `list_providers` | `(user_id)` | Providere brugeren har forbundet (har en gemt token for). | [src](../../../core/services/oauth_store.py#L117) |

## `core/services/offline_recomposition_engine.py`
_Offline recomposition: recombine recent cognitive material into candidates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_offline_recomposition` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L15) |
| function | `build_offline_recomposition_surface` | `(*, limit=…)` | — | [src](../../../core/services/offline_recomposition_engine.py#L42) |
| function | `build_offline_recomposition_prompt_section` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L55) |
| function | `_candidate_pieces` | `(*, episodes, drive, curiosity, counterfactuals)` | — | [src](../../../core/services/offline_recomposition_engine.py#L67) |
| function | `_candidate_policy` | `(pieces)` | — | [src](../../../core/services/offline_recomposition_engine.py#L88) |
| function | `_feed_learning` | `(item)` | — | [src](../../../core/services/offline_recomposition_engine.py#L99) |
| function | `_runtime_state` | `(key)` | — | [src](../../../core/services/offline_recomposition_engine.py#L113) |
| function | `_load` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L118) |

## `core/services/ollama_visible_prompt.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `serialize_ollama_visible_prompt` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L14) |
| function | `_collect_visible_text_parts` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L26) |
| function | `_serialize_system_block` | `(system_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L56) |
| function | `serialize_ollama_chat_messages` | `(items)` | Convert visible input items to Ollama /api/chat messages format. | [src](../../../core/services/ollama_visible_prompt.py#L68) |
| function | `_serialize_conversation_block` | `(conversation_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L87) |

## `core/services/open_loop_closure_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_closure_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L32) |
| function | `refresh_runtime_open_loop_closure_proposal_statuses` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L54) |
| function | `build_runtime_open_loop_closure_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L85) |
| function | `_extract_open_loop_closure_proposal_candidates` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L114) |
| function | `_persist_open_loop_closure_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L192) |
| function | `_build_proposal_snapshots` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L265) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L302) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L313) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L334) |
| function | `_proposal_status` | `(*, proposal_type, loop_status)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L348) |
| function | `_build_proposal_reason` | `(*, proposal_type, loop_status, closure_confidence, loop_title=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L356) |
| function | `_build_review_anchor` | `(*, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L369) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L384) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L393) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L398) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L403) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L408) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L413) |
| function | `_proposal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L418) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L423) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L428) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L438) |

## `core/services/open_loop_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L58) |
| function | `refresh_runtime_open_loop_signal_statuses` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L80) |
| function | `build_runtime_open_loop_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L134) |
| function | `_build_runtime_open_loop_signal_surface_uncached` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L142) |
| function | `get_open_loop_creation_readiness` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L208) |
| function | `_extract_open_loop_candidates` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L287) |
| function | `_materialize_from_creation_readiness` | `(readiness, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L536) |
| function | `_extract_closure_maturation_candidates` | `(snapshots, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L604) |
| function | `_build_governance_snapshots` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L683) |
| function | `_with_closure_governance` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L741) |
| function | `_persist_open_loop_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L791) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L864) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L905) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L917) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L935) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L939) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L944) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L949) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L954) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L959) |
| function | `_match_live_pressure_item` | `(*, anchors, candidates, minimum_overlap)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L968) |
| function | `_thread_overlap` | `(left, right)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L992) |
| function | `_thread_tokens` | `(item)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L996) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L1030) |

## `core/services/operator_allowlist.py`
_Operator app-allowlist (leak-kandidat #5, CHICAGO-guard-mønster, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L26) |
| function | `list_allowlist` | `()` | — | [src](../../../core/services/operator_allowlist.py#L30) |
| function | `set_allowlist` | `(apps)` | — | [src](../../../core/services/operator_allowlist.py#L39) |
| function | `add_to_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L45) |
| function | `remove_from_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L53) |
| function | `is_enforced` | `()` | — | [src](../../../core/services/operator_allowlist.py#L58) |
| function | `set_enforced` | `(on)` | — | [src](../../../core/services/operator_allowlist.py#L65) |
| function | `_matches` | `(app, allowlist)` | En app matcher hvis dens navn/sti indeholder en allowlist-post (substring, | [src](../../../core/services/operator_allowlist.py#L70) |
| function | `check_app` | `(app)` | Vurdér om Jarvis må GUI-styre `app`. OBSERVE-by-default: | [src](../../../core/services/operator_allowlist.py#L77) |
| function | `build_operator_allowlist_surface` | `()` | Central-CLI: jc raw /central/operator-allowlist. | [src](../../../core/services/operator_allowlist.py#L102) |

