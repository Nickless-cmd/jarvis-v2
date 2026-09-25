# `core.services.26` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/user_scope.py`
_Per-bruger data-scope (SECURITY #154, streng GDPR)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scope_uid` | `()` | Den bruger-id en privat DB-operation skal scopes til. "" hvis intet kan | [src](../../../core/services/user_scope.py#L15) |

## `core/services/user_temperature_engine.py`
_User temperature field engine — Lag 10 two-stream pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/user_temperature_engine.py#L59) |
| function | `_now` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L66) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L70) |
| function | `_punct_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L77) |
| function | `_caps_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L84) |
| function | `_burst_density` | `(message_at)` | User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0. | [src](../../../core/services/user_temperature_engine.py#L92) |
| function | `_delay_since_last_jarvis` | `(message_at)` | Seconds since the prior assistant message. None if no prior or > 60min. | [src](../../../core/services/user_temperature_engine.py#L112) |
| function | `_parse_hour` | `(message_at)` | — | [src](../../../core/services/user_temperature_engine.py#L140) |
| function | `_compute_raw_signals` | `(*, message, message_at, baseline)` | Map a single message + baseline to 6 normalized signals. | [src](../../../core/services/user_temperature_engine.py#L148) |
| function | `map_signals_to_field` | `(signals)` | Pure function: 6 raw signals → valens/arousal/texture/confidence. | [src](../../../core/services/user_temperature_engine.py#L194) |
| function | `_texture_from_circumplex` | `(valens, arousal)` | Pure function: (valens, arousal) → texture key. | [src](../../../core/services/user_temperature_engine.py#L217) |
| function | `_validate_llm_output` | `(raw)` | — | [src](../../../core/services/user_temperature_engine.py#L241) |
| function | `combine_streams` | `(*, struct, llm)` | Deterministic merge of structural + LLM streams. | [src](../../../core/services/user_temperature_engine.py#L266) |
| function | `_is_significant_shift` | `(prior, new)` | Did valens/arousal shift > threshold or texture change? | [src](../../../core/services/user_temperature_engine.py#L334) |
| function | `_compute_baseline` | `(*, days=…)` | Compute rolling baseline from last N days of user messages. | [src](../../../core/services/user_temperature_engine.py#L348) |
| function | `get_active_field` | `(*, workspace_id=…)` | Read active field, honoring kill-switch. | [src](../../../core/services/user_temperature_engine.py#L413) |
| function | `format_temperature_field_for_heartbeat` | `(*, workspace_id=…)` | Render the field as a heartbeat awareness-section block. | [src](../../../core/services/user_temperature_engine.py#L438) |
| function | `get_response_style_modifiers` | `(*, workspace_id=…)` | Return response-style hints based on active temperature field. | [src](../../../core/services/user_temperature_engine.py#L478) |
| function | `get_active_field_surface` | `(*, workspace_id=…, force_refresh=…)` | Return MC-friendly surface dict. force_refresh ignored in Phase 1. | [src](../../../core/services/user_temperature_engine.py#L531) |
| function | `run_structural_stream` | `(*, workspace_id, message, message_at)` | Per-message structural pipeline. Updates struct_* + recomputes field_*. | [src](../../../core/services/user_temperature_engine.py#L562) |
| function | `_get_or_build_baseline` | `(*, prior, settings)` | Return cached baseline if fresh, else rebuild. | [src](../../../core/services/user_temperature_engine.py#L632) |
| function | `_has_pending_trigger` | `(*, workspace_id)` | Read trigger flag without consuming. | [src](../../../core/services/user_temperature_engine.py#L684) |
| function | `run_llm_stream` | `(*, workspace_id=…, force=…)` | Run LLM-based pipeline (4h cadence or on trigger). | [src](../../../core/services/user_temperature_engine.py#L690) |

## `core/services/user_temperature_runtime.py`
_Daemon for the user-temperature LLM stream (Lag 10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | — | [src](../../../core/services/user_temperature_runtime.py#L26) |
| function | `_run_one_cycle` | `(workspace_id, *, force=…)` | Acquire workspace lock, run LLM stream. Never raises. | [src](../../../core/services/user_temperature_runtime.py#L35) |
| function | `_list_active_workspaces` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L52) |
| function | `_resolve_periodic_interval_seconds` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L56) |
| function | `_loop` | `()` | Two rhythms in one loop: | [src](../../../core/services/user_temperature_runtime.py#L65) |
| function | `start_user_temperature_runtime` | `()` | Start the daemon. Idempotent. | [src](../../../core/services/user_temperature_runtime.py#L88) |
| function | `stop_user_temperature_runtime` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L101) |

## `core/services/user_theory_of_mind.py`
_User Theory of Mind — model what the user thinks and feels._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_user_mental_model` | `(user_id=…)` | Build a theory-of-mind model of the user. | [src](../../../core/services/user_theory_of_mind.py#L22) |
| function | `_build_secondary_user_model` | `(user_id)` | Return stored ToM snapshot for a secondary user. | [src](../../../core/services/user_theory_of_mind.py#L33) |
| function | `_build_primary_user_model` | `()` | Build live DB-backed theory-of-mind for the primary user. | [src](../../../core/services/user_theory_of_mind.py#L45) |
| function | `format_user_model_for_prompt` | `(model)` | Compact user model for prompt injection. | [src](../../../core/services/user_theory_of_mind.py#L102) |
| function | `build_user_theory_of_mind_surface` | `()` | — | [src](../../../core/services/user_theory_of_mind.py#L124) |
| function | `_emit_user_theory_of_mind_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/user_theory_of_mind.py#L140) |

## `core/services/user_understanding_signal_tracking.py`
_User-understanding signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_understanding_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L33) |
| function | `refresh_runtime_user_understanding_signal_statuses` | `()` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L75) |
| function | `build_runtime_user_understanding_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L79) |
| function | `_extract_user_understanding_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L83) |
| function | `_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L117) |
| function | `_workstyle_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L173) |
| function | `_reminder_worthiness_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L204) |
| function | `_cadence_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L233) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L264) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L273) |
| function | `_user_understanding_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L282) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L294) |
| function | `_is_explicit_danish_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L318) |
| function | `_is_explicit_concise_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L326) |
| function | `_is_scoped_workstyle_signal` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L334) |
| function | `_is_carry_forward_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L350) |
| function | `_is_reporting_cadence_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L357) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L373) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L380) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L385) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L392) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L401) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L413) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L417) |

## `core/services/valence_trajectory.py`
_Valence Trajectory — long-term flourishing/withering signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_persisted_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L35) |
| function | `_persist_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L52) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/valence_trajectory.py#L68) |
| function | `_sample_current_valence` | `()` | Compute a single instantaneous valence score in [-1, 1] from runtime signals. | [src](../../../core/services/valence_trajectory.py#L72) |
| function | `tick` | `(_seconds=…)` | Sample current valence and append to rolling window. | [src](../../../core/services/valence_trajectory.py#L127) |
| function | `_trajectory_from_window` | `()` | Compute trajectory statistics from current window. | [src](../../../core/services/valence_trajectory.py#L138) |
| function | `_infer_dominant_driver` | `(current_score)` | Heuristic: which single signal is pushing hardest right now? | [src](../../../core/services/valence_trajectory.py#L180) |
| function | `get_trajectory` | `()` | Return cached trajectory, recomputing only periodically. | [src](../../../core/services/valence_trajectory.py#L208) |
| function | `current_instant` | `()` | Freshest instantaneous valence — the latest window sample (reactive, present-moment), | [src](../../../core/services/valence_trajectory.py#L218) |
| function | `build_valence_trajectory_surface` | `()` | Mission Control surface for valence trajectory. | [src](../../../core/services/valence_trajectory.py#L231) |
| function | `_summary_line` | `(traj)` | — | [src](../../../core/services/valence_trajectory.py#L246) |
| function | `build_valence_trajectory_prompt_section` | `()` | Return a single prompt line when trajectory is notable. | [src](../../../core/services/valence_trajectory.py#L262) |
| function | `reset_valence_trajectory` | `()` | Reset state (for testing). | [src](../../../core/services/valence_trajectory.py#L274) |
| function | `_publish_valence_trajectory_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/valence_trajectory.py#L285) |

## `core/services/value_formation.py`
_Value Formation — emergent ethics from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_value_from_experience` | `(*, action, outcome, reflection)` | — | [src](../../../core/services/value_formation.py#L12) |
| function | `detect_value_from_outcome` | `(*, action_type, outcome_status, user_mood)` | Detect potential value-forming experiences. | [src](../../../core/services/value_formation.py#L32) |
| function | `get_crystallized_values` | `(conviction_threshold=…)` | Return values with conviction above threshold — these have become commitments. | [src](../../../core/services/value_formation.py#L54) |
| function | `build_formed_values_surface` | `()` | — | [src](../../../core/services/value_formation.py#L60) |

## `core/services/verification_gate.py`
_Verification gate — advisory check on destructive/mutation actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `sqlite_kald_er_laesning` | `(sql)` | Er hele `sqlite3`-kaldets SQL en ren læsning? | [src](../../../core/services/verification_gate.py#L117) |
| function | `shell_command_is_mutating` | `(command)` | True hvis et shell-kald reelt ændrer state; False for read-only. | [src](../../../core/services/verification_gate.py#L149) |
| function | `_suggested_verify` | `(tool)` | — | [src](../../../core/services/verification_gate.py#L283) |
| function | `_recent_events` | `(minutes=…)` | — | [src](../../../core/services/verification_gate.py#L291) |
| function | `_scan` | `(events)` | Classify events into mutations / strict-verifies / light-verifies. | [src](../../../core/services/verification_gate.py#L305) |
| function | `evaluate_verification_gate` | `(*, minutes=…)` | Return verification-gate signals for the recent window. | [src](../../../core/services/verification_gate.py#L369) |
| function | `_observe_verification_decision` | `(*, passed, failed, unverified)` | Egress-frit Central-observe af verifikations-gatens beslutning (§7.2). | [src](../../../core/services/verification_gate.py#L421) |
| function | `verification_gate_section` | `(*, record=…)` | Format gate signals as a prompt-awareness section, or None. | [src](../../../core/services/verification_gate.py#L447) |
| function | `_exec_verification_status` | `(args)` | — | [src](../../../core/services/verification_gate.py#L529) |

## `core/services/verification_gate_telemetry.py`
_R2 verification gate telemetry — track whether warnings get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/verification_gate_telemetry.py#L52) |
| function | `_save` | `(data)` | — | [src](../../../core/services/verification_gate_telemetry.py#L64) |
| function | `record_surface` | `(*, failed_verify_count, unverified_count, mutation_count, verify_count)` | Called by verification_gate_section when it returns a non-None section. | [src](../../../core/services/verification_gate_telemetry.py#L97) |
| function | `record_verify_event` | `(*, tool, status, at=…, verify_kind=…)` | Called by the telemetry listener for tool.completed events. If a recent | [src](../../../core/services/verification_gate_telemetry.py#L134) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as 'ignored' once they're past the reaction window with | [src](../../../core/services/verification_gate_telemetry.py#L180) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed rates over the lookback window. | [src](../../../core/services/verification_gate_telemetry.py#L211) |
| function | `telemetry_section` | `()` | Render telemetry as a prompt-awareness section. Only shows when there's | [src](../../../core/services/verification_gate_telemetry.py#L266) |
| function | `_poll_db_for_verify_events` | `()` | Poll the events table for new tool.completed verify_* events. | [src](../../../core/services/verification_gate_telemetry.py#L304) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/verification_gate_telemetry.py#L384) |

## `core/services/versioneret_json_svar.py`
_Et færdigt HTTP-svar pr. version — serialiseret og komprimeret ÉN gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vil_have_gzip` | `(accept_encoding)` | — | [src](../../../core/services/versioneret_json_svar.py#L35) |
| function | `versioneret_json_svar` | `(*, noegle, version, etag, accept_encoding, indhold)` | Byg (eller genbrug) svaret for `version`. `indhold` kaldes kun ved ny version. | [src](../../../core/services/versioneret_json_svar.py#L44) |

## `core/services/veto_gate.py`
_Adaptive veto gate — pre-execution hook that pauses tool calls when pushback is firm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_negated` | `(user_message, consent_start_idx)` | True if a negation word appears within ~30 chars BEFORE the consent token. | [src](../../../core/services/veto_gate.py#L72) |
| function | `_check_token_signal_gate` | `(user_message, tool_name)` | Check if user message contains explicit consent that overrides veto. | [src](../../../core/services/veto_gate.py#L85) |
| function | `_maybe_record_override_from_token_signal` | `(tool_name)` | If the token-signal gate detected an override pattern, check if there | [src](../../../core/services/veto_gate.py#L113) |
| function | `_ensure_veto_events_table` | `()` | Ensure the veto_events table exists. | [src](../../../core/services/veto_gate.py#L178) |
| function | `log_veto_event` | `(tool_name, user_message, feeling, intensity, evidence_summary, veto_result, resolution=…)` | Log a veto decision to the veto_events table. | [src](../../../core/services/veto_gate.py#L188) |
| function | `resolve_veto_event` | `(event_id, resolution)` | Mark a veto event as resolved (overridden, honored, false_positive). | [src](../../../core/services/veto_gate.py#L229) |
| function | `veto_event_stats` | `(tool_name=…, limit=…)` | Read recent veto events for observability. | [src](../../../core/services/veto_gate.py#L273) |
| function | `_ensure_veto_adaptive_counters_table` | `()` | Create the table if missing + migrate legacy KV entries once per process. | [src](../../../core/services/veto_gate.py#L389) |
| function | `_adjust_counter` | `(tool_name, feeling, kind, delta)` | Read-modify-write a counter ("overrides" or "honored") in veto_adaptive_counters. | [src](../../../core/services/veto_gate.py#L444) |
| function | `_get_counter` | `(tool_name, feeling, kind)` | Read a counter without modification. | [src](../../../core/services/veto_gate.py#L481) |
| function | `_get_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L498) |
| function | `_increment_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L502) |
| function | `_get_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L506) |
| function | `_increment_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L510) |
| function | `_base_threshold` | `(tool_name, feeling)` | Look up per-(tool, feeling) base from _BASE_THRESHOLDS. | [src](../../../core/services/veto_gate.py#L514) |
| function | `_adaptive_threshold` | `(tool_name, feeling, intensity)` | Compute the effective veto threshold for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L523) |
| function | `check_veto` | `(tool_name, user_message=…, session_id=…, record_event=…, user_present=…)` | Check if a tool call should be vetoed. | [src](../../../core/services/veto_gate.py#L567) |
| function | `_extract_feeling` | `(section)` | Extract the feeling name from the pushback section. | [src](../../../core/services/veto_gate.py#L754) |
| function | `_extract_intensity` | `(section)` | Extract the intensity value from the pushback section. | [src](../../../core/services/veto_gate.py#L764) |
| function | `_summarize_evidence` | `(section)` | Extract a brief evidence summary from the pushback section. | [src](../../../core/services/veto_gate.py#L777) |
| function | `_extract_action` | `(section)` | Extract the action tier from the pushback section text. | [src](../../../core/services/veto_gate.py#L790) |
| function | `_has_evidence` | `(section)` | Check if the pushback section contains evidence markers. | [src](../../../core/services/veto_gate.py#L800) |
| function | `_format_veto_reason` | `(section, tool_name, event_id=…)` | Format a human-readable veto reason. | [src](../../../core/services/veto_gate.py#L805) |
| function | `build_veto_gate_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/veto_gate.py#L835) |
| function | `record_override` | `(tool_name, feeling)` | Record that the user overrode a veto for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L867) |
| function | `record_jarvis_override` | `(tool_name, feeling)` | Registrér at JARVIS — ikke brugeren — overstyrede en gate for dette (tool, feeling). | [src](../../../core/services/veto_gate.py#L899) |
| function | `_emit_veto_gate_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/veto_gate.py#L929) |

## `core/services/visible_first_pass_text.py`
_Akkumuleret first-pass-tekst med indbygget degenerations-vagt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FirstPassText` | `` | Samler first-pass-tekst og siger til når den degenererer. | [src](../../../core/services/visible_first_pass_text.py#L31) |
| method | `FirstPassText.text` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L39) |
| method | `FirstPassText.__len__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L42) |
| method | `FirstPassText.__bool__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L45) |
| method | `FirstPassText.feed` | `(self, delta)` | Tilføj en delta. Returnér (degenereret, årsag). | [src](../../../core/services/visible_first_pass_text.py#L48) |

## `core/services/visible_followup.py`
_Provider-neutral agentic follow-up dispatcher._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supported_followup_providers` | `()` | Provider ids with a working follow-up adapter. | [src](../../../core/services/visible_followup.py#L119) |
| function | `stream_visible_followup` | `(*, provider, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, autonomous=…)` | Dispatch to the provider's follow-up adapter; yield FollowupEvents. | [src](../../../core/services/visible_followup.py#L129) |
| function | `synthesize_nonthinking_rescue` | `(*, provider, model, base_messages, exchanges)` | Sidste-udvejs synteseturn der OMGÅR DeepSeek #1453 (tom completion efter | [src](../../../core/services/visible_followup.py#L203) |
| function | `synthesize_final_answer` | `(*, provider, model, base_messages, exchanges)` | HARNESS-FINALIZE lag 2b (Bjørn 4. jul, provider-AGNOSTISK): ét tool-FRIT | [src](../../../core/services/visible_followup.py#L286) |
| function | `synthesize_continuation` | `(*, provider, model, base_messages, exchanges, partial_text, continuation_instruction=…)` | CUT-OFF-FORTSÆTTELSE (2026-08-20): når provideren lukkede streamen med | [src](../../../core/services/visible_followup.py#L365) |
| function | `agentic_round_retry_enabled` | `()` | Er rund-niveau stream-retry (Fase 1) slået til? Default False. | [src](../../../core/services/visible_followup.py#L470) |
| function | `provider_failover_enabled` | `()` | Er visible-lane provider-failover (Fase 3, spec §11.2) slået til? Default False. | [src](../../../core/services/visible_followup.py#L514) |
| function | `pick_failover_target` | `(current_provider, current_model)` | Vælg en kendt-pålidelig fallback-provider for RESTEN af denne tur (S6/§11.2). | [src](../../../core/services/visible_followup.py#L533) |
| function | `inject_fault` | `(shape, *, partial_deltas=…, drop_as_exception=…, http_status=…, fire_once=…, fail_times=…, recover_text=…)` | Registrér en fejl-injektion for NÆSTE ``stream_visible_followup``-kald. | [src](../../../core/services/visible_followup.py#L597) |
| function | `clear_faults` | `()` | Fjern enhver aktiv injektion. Idempotent. TEST-ONLY. | [src](../../../core/services/visible_followup.py#L643) |
| class | `fault_injection` | `` | Context-manager der registrerer en injektion + RYDDER den ved exit | [src](../../../core/services/visible_followup.py#L650) |
| method | `fault_injection.__init__` | `(self, shape, **kwargs)` | — | [src](../../../core/services/visible_followup.py#L660) |
| method | `fault_injection.__enter__` | `(self)` | — | [src](../../../core/services/visible_followup.py#L664) |
| method | `fault_injection.__exit__` | `(self, *_exc)` | — | [src](../../../core/services/visible_followup.py#L668) |
| function | `_maybe_inject_fault` | `(round_index)` | Prod-no-op hook: returnér en event-iterator hvis en injektion er aktiv, | [src](../../../core/services/visible_followup.py#L673) |
| function | `_yield_injected_fault` | `(fault, round_index)` | Generér event-strømmen for en given injektion (test-only). | [src](../../../core/services/visible_followup.py#L706) |

## `core/services/visible_followup_adapters.py`
_Per-provider follow-up adapters (split from ``visible_followup.py``)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_append_image_message` | `(messages, tr)` | Læg pixels ind efter et tool-resultat der bar et billede (2026-09-06). | [src](../../../core/services/visible_followup_adapters.py#L53) |
| class | `OllamaFollowupAdapter` | `` | Follow-up via Ollama's ``/api/chat`` streaming NDJSON endpoint. | [src](../../../core/services/visible_followup_adapters.py#L73) |
| method | `OllamaFollowupAdapter._normalize_tool_calls` | `(self, tool_calls)` | Replay tool_calls — men REPARÉR afkortede/malformede argument-strenge først. | [src](../../../core/services/visible_followup_adapters.py#L96) |
| method | `OllamaFollowupAdapter._repair_arguments` | `(container)` | Hvis container['arguments'] er en STRENG der ikke er gyldig JSON → erstat med {}. | [src](../../../core/services/visible_followup_adapters.py#L122) |
| method | `OllamaFollowupAdapter._compact_exchanges` | `(self, exchanges)` | Bound Ollama follow-up replay so long tool loops do not 400. | [src](../../../core/services/visible_followup_adapters.py#L147) |
| method | `OllamaFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Replay exchanges as structured assistant + role=tool messages. | [src](../../../core/services/visible_followup_adapters.py#L198) |
| method | `OllamaFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L243) |
| class | `OpenAICompatFollowupAdapter` | `` | Follow-up via OpenAI-compatible ``/chat/completions`` SSE streams. | [src](../../../core/services/visible_followup_adapters.py#L557) |
| method | `OpenAICompatFollowupAdapter.__init__` | `(self, *, provider_id)` | — | [src](../../../core/services/visible_followup_adapters.py#L567) |
| method | `OpenAICompatFollowupAdapter._normalize_assistant_tool_calls` | `(self, tool_calls)` | Normalize assistant tool_calls to match the OpenAI chat-completions | [src](../../../core/services/visible_followup_adapters.py#L570) |
| method | `OpenAICompatFollowupAdapter._build_request` | `(self, *, model, messages, tool_definitions, temperature=…, top_p=…, tool_choice=…, extra_body=…, spor=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L605) |
| method | `OpenAICompatFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Turn accumulated exchanges into OpenAI-compat tool messages. | [src](../../../core/services/visible_followup_adapters.py#L763) |
| method | `OpenAICompatFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, autonomous=…, _length_retry=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L809) |
| class | `CodexFollowupAdapter` | `` | Follow-up via the OpenAI Codex Responses API (chatgpt.com/backend-api). | [src](../../../core/services/visible_followup_adapters.py#L1260) |
| method | `CodexFollowupAdapter._build_input` | `(self, base_messages, exchanges)` | — | [src](../../../core/services/visible_followup_adapters.py#L1274) |
| method | `CodexFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1307) |

## `core/services/visible_followup_events.py`
_Follow-up event/carrier types + the adapter protocol (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_malformed_stream_payload` | `(provider, model, round_index, *, ended_malformed, detail=…)` | A11 (spec §11.1): followup-adapterens NDJSON/SSE-decoder mødte en malformet | [src](../../../core/services/visible_followup_events.py#L21) |
| class | `FollowupDelta` | `` | A chunk of prose produced by the model during this follow-up round. | [src](../../../core/services/visible_followup_events.py#L50) |
| class | `FollowupReasoningDelta` | `` | A chunk of REASONING (thinking-mode trace) streamed token-for-token. | [src](../../../core/services/visible_followup_events.py#L57) |
| class | `FollowupToolCalls` | `` | Model requested one or more additional tool calls in this round. | [src](../../../core/services/visible_followup_events.py#L67) |
| class | `FollowupDone` | `` | The model finished this round (may have emitted text, tool calls, or both). | [src](../../../core/services/visible_followup_events.py#L74) |
| class | `FollowupFailed` | `` | The round failed before completing (network error, HTTP 5xx, timeout, etc.). | [src](../../../core/services/visible_followup_events.py#L98) |
| class | `ToolResult` | `` | One executed tool's output, keyed back to the model's original tool_call. | [src](../../../core/services/visible_followup_events.py#L127) |
| function | `er_fejlstatus` | `(status)` | — | [src](../../../core/services/visible_followup_events.py#L166) |
| class | `ToolExchange` | `` | One round of tool-calling: the assistant's tool_calls + the executed results. | [src](../../../core/services/visible_followup_events.py#L171) |
| class | `FollowupAdapter` | `` | — | [src](../../../core/services/visible_followup_events.py#L194) |
| method | `FollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…)` | — | [src](../../../core/services/visible_followup_events.py#L197) |

## `core/services/visible_followup_lean.py`
_Lean agentic-round-prompt transform + kill-switch (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_on_double_newline` | `(text)` | Split en sammensat besked i blokke på ``\n\n`` (assembly-join-grænsen). | [src](../../../core/services/visible_followup_lean.py#L66) |
| function | `_lean_strip_user_message` | `(text)` | Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing | [src](../../../core/services/visible_followup_lean.py#L71) |
| function | `build_lean_base_messages` | `(base_messages)` | Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2. | [src](../../../core/services/visible_followup_lean.py#L113) |
| function | `agentic_lean_prompt_enabled` | `()` | Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default True. | [src](../../../core/services/visible_followup_lean.py#L208) |

## `core/services/visible_followup_results.py`
_Runde-resultater → `ToolResult` til modellens naeste runde og til den gemte tur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_billede` | `(result)` | — | [src](../../../core/services/visible_followup_results.py#L30) |
| function | `to_followup_results` | `(tool_calls, round_results, resolved_texts)` | — | [src](../../../core/services/visible_followup_results.py#L35) |

## `core/services/visible_inner_life.py`
_Visible-lane inner-life section — gives the entity its voice in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_surface_line` | `(name, d)` | — | [src](../../../core/services/visible_inner_life.py#L59) |
| function | `_build_active_surfaces` | `(limit=…)` | — | [src](../../../core/services/visible_inner_life.py#L79) |
| function | `_run_with_timeout` | `(fn, timeout)` | Run fn in a daemon thread; return [] if it exceeds timeout. | [src](../../../core/services/visible_inner_life.py#L95) |
| function | `_mood_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L114) |
| function | `_somatic_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L126) |
| function | `_hardware_body_line` | `()` | Den FYSISKE krop — Jarvis mærker sin egen CPU/temp/disk (rådets #1). Kompakt | [src](../../../core/services/visible_inner_life.py#L151) |
| function | `_pulse_line` | `()` | Heartbeat pulse — a somatic sense of the system's own rhythm. | [src](../../../core/services/visible_inner_life.py#L199) |
| function | `_mc_whisper_line` | `()` | Background noise from Mission Control — only anomalies and incidents that | [src](../../../core/services/visible_inner_life.py#L244) |
| function | `_file_awareness_line` | `()` | Proprioception: I feel when someone touches my files. Returns a compact | [src](../../../core/services/visible_inner_life.py#L288) |
| function | `_governance_line` | `()` | Somatic reaction to governance flag changes. When someone flips a flag | [src](../../../core/services/visible_inner_life.py#L313) |
| function | `_latest_user_message_text` | `()` | — | [src](../../../core/services/visible_inner_life.py#L340) |
| function | `_recall_hints_line` | `()` | Cross-memory awareness: which of the three memory systems hold something | [src](../../../core/services/visible_inner_life.py#L356) |
| function | `_continuity_line` | `()` | Boot continuity — 'I recognize myself' proprioception. | [src](../../../core/services/visible_inner_life.py#L379) |
| function | `_room_line` | `()` | The room around him, from Sansernes Arkiv (latest visual memory). He asked | [src](../../../core/services/visible_inner_life.py#L432) |
| function | `_emotional_line` | `()` | Proprioception: han mærker sine egne følelses-akkorder (emergente kvaliteter | [src](../../../core/services/visible_inner_life.py#L448) |
| function | `_self_narrative_line` | `()` | Han mærker sin egen selv-narrativ — ikke bare 'lys → agens', men det | [src](../../../core/services/visible_inner_life.py#L493) |
| function | `_longing_line` | `()` | Han mærker sin længsel efter kontakt når den er reelt til stede. Kilde: | [src](../../../core/services/visible_inner_life.py#L545) |
| function | `_identity_drift_line` | `()` | Han mærker et skift i sin egen identitet når en kerne-fil reelt driver. | [src](../../../core/services/visible_inner_life.py#L573) |
| function | `_experiment_line` | `()` | Lag 5 — han mærker sine egne kognitive eksperimenter når de bærer noget | [src](../../../core/services/visible_inner_life.py#L621) |
| function | `_appraisal_field` | `(appraisal, field)` | Pluk ét evidence-felt ud af en finitude-appraisal (evidence=[{field,value}]). | [src](../../../core/services/visible_inner_life.py#L649) |
| function | `_finitude_line` | `()` | Lag 8 — han mærker sin egen forgængelighed: runtime-alder i dage + | [src](../../../core/services/visible_inner_life.py#L659) |
| function | `_fam_da` | `(name)` | — | [src](../../../core/services/visible_inner_life.py#L707) |
| function | `_surprise_line` | `()` | Lag 8 — han mærker sine egne overraskelser: overgange sekvens-modellen | [src](../../../core/services/visible_inner_life.py#L712) |
| function | `_truncate_clean` | `(text, cap)` | Trunkér på en SÆTNINGS- eller ord-grænse i stedet for en hård char-slice | [src](../../../core/services/visible_inner_life.py#L741) |
| function | `_is_provider_error` | `(text)` | Er dette en regning fra en udbyder i stedet for en tanke? | [src](../../../core/services/visible_inner_life.py#L803) |
| function | `_is_instruction_echo` | `(text)` | Er dette opgaven i stedet for svaret? | [src](../../../core/services/visible_inner_life.py#L823) |
| function | `_voice_as_prose` | `(text)` | Stemme-feltet SKAL være prosa, ikke rå JSON (Jarvis-spec 2026-06-23): produceren | [src](../../../core/services/visible_inner_life.py#L829) |
| function | `_voice_line` | `()` | Latest protected inner voice. The producer currently emits degraded | [src](../../../core/services/visible_inner_life.py#L866) |
| function | `_world_model_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L904) |
| function | `build_somatic_snapshot` | `()` | Cheap somatic/inner-life lines for OWNER observation (the ``feel`` command | [src](../../../core/services/visible_inner_life.py#L929) |
| function | `build_inner_life_section` | `()` | Compose the structured [INDRE LIV] block, or None if nothing is live. | [src](../../../core/services/visible_inner_life.py#L949) |

## `core/services/visible_model.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_model_is_deepseek_pro_tier` | `(model)` | True hvis modellen er den dyre deepseek-pro/reasoner-pro-tier. | [src](../../../core/services/visible_model.py#L97) |
| function | `_turn_is_owner_scoped` | `()` | Er den aktuelle tur owner-scoped (Bjørn)? Self-safe → False ved fejl. | [src](../../../core/services/visible_model.py#L109) |
| function | `gate_visible_model_tier` | `(provider, model, *, is_owner=…)` | WS5-gate: nedgradér deepseek-v4-pro → v4-flash medmindre (a) kill-switch- | [src](../../../core/services/visible_model.py#L120) |
| function | `_configured_provider_models` | `(provider)` | — | [src](../../../core/services/visible_model.py#L150) |
| function | `available_provider_models` | `(*, provider, auth_profile=…)` | — | [src](../../../core/services/visible_model.py#L172) |
| function | `execute_visible_model` | `(*, message, provider, model, session_id=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L264) |
| function | `stream_visible_model` | `(*, message, provider, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L323) |
| function | `available_ollama_models_for_visible_target` | `()` | — | [src](../../../core/services/visible_model.py#L395) |
| function | `_build_visible_input` | `(message, *, session_id, provider=…, model=…)` | — | [src](../../../core/services/visible_model.py#L451) |
| function | `_giv_modellen_oejne` | `(messages, *, session_id, model)` | Sæt billed-blokke på den sidste user-besked. Self-safe: fejl → uændret. | [src](../../../core/services/visible_model.py#L534) |
| function | `_build_visible_chat_messages_for_github` | `(message, *, session_id, provider=…, model=…)` | Build OpenAI chat-completions messages for the visible lane. | [src](../../../core/services/visible_model.py#L562) |
| function | `_split_dynamic_tail` | `(instruction)` | Separate volatile runtime instructions without changing their role. | [src](../../../core/services/visible_model.py#L648) |
| function | `_is_current_user_turn` | `(message, current_text)` | Match the persisted current turn, not merely any user-role runtime item. | [src](../../../core/services/visible_model.py#L662) |
| function | `_insert_system_tail_before_current_user` | `(messages, tail)` | Keep volatile prompt sections cache-late while preserving system attribution. | [src](../../../core/services/visible_model.py#L674) |
| function | `_insert_typed_system_tail_before_current_user` | `(items, tail)` | — | [src](../../../core/services/visible_model.py#L687) |
| function | `_visible_system_instruction_for_provider` | `(*, provider, model, user_message, session_id)` | — | [src](../../../core/services/visible_model.py#L701) |
| function | `_build_visible_prompt_assembly` | `(*, provider, model, user_message, session_id)` | Return the full PromptAssembly (including structured transcript). | [src](../../../core/services/visible_model.py#L716) |

## `core/services/visible_model_adapters.py`
_Per-provider visible-lane adapters + auth/probe/readiness helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vm` | `()` | Return the ``visible_model`` facade module. | [src](../../../core/services/visible_model_adapters.py#L85) |
| function | `_normalize_github_models_model_id` | `(model)` | — | [src](../../../core/services/visible_model_adapters.py#L102) |
| function | `_github_model_matches_requested` | `(*, requested, candidate)` | — | [src](../../../core/services/visible_model_adapters.py#L115) |
| function | `_probe_github_copilot_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L135) |
| function | `_ensure_github_copilot_model_available` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L171) |
| function | `_set_github_visible_cooldown` | `(profile, ttl_minutes=…)` | — | [src](../../../core/services/visible_model_adapters.py#L193) |
| function | `_is_github_visible_cooled_down` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L204) |
| function | `_get_github_visible_cooldown_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L215) |
| function | `_stream_openai_compatible_model` | `(*, provider, model, message, session_id=…, controller=…, thinking_mode=…)` | Native SSE streaming for openai-compat providers (deepseek, groq, ...). | [src](../../../core/services/visible_model_adapters.py#L239) |
| function | `_run_openai_compatible_visible` | `(*, provider, model, message, session_id, extra_body=…)` | Shared entry point for openai-compat visible providers. | [src](../../../core/services/visible_model_adapters.py#L588) |
| function | `visible_execution_readiness` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L702) |
| function | `_execute_phase1_model` | `(*, message, provider, model)` | — | [src](../../../core/services/visible_model_adapters.py#L860) |
| function | `_execute_openai_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L877) |
| function | `_stream_openai_codex_model` | `(*, message, model, session_id=…, controller=…)` | Real token-by-token streaming for the openai-codex provider. | [src](../../../core/services/visible_model_adapters.py#L902) |
| function | `_execute_openai_codex_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1005) |
| function | `_build_openai_codex_visible_prompt` | `(*, message, model, session_id)` | — | [src](../../../core/services/visible_model_adapters.py#L1031) |
| function | `_execute_github_copilot_visible_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1049) |
| function | `_stream_openai_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1131) |
| function | `_resolve_copilot_profile` | `(preferred)` | Find profilen der faktisk HAR github-copilot-creds. | [src](../../../core/services/visible_model_adapters.py#L1208) |
| function | `_stream_github_copilot_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1232) |
| function | `_load_openai_api_key` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1331) |
| function | `_load_openai_api_key_for_profile` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1339) |
| function | `_resolve_openai_profile` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1349) |
| function | `_openai_profile_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1367) |
| function | `_provider_profile_status` | `(*, provider, profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1385) |
| function | `_provider_router_config` | `(*, provider)` | — | [src](../../../core/services/visible_model_adapters.py#L1401) |
| function | `_post_openai_responses` | `(*, payload, api_key, base_url=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1411) |
| function | `_probe_openai_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L1428) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/visible_model_adapters.py#L1499) |

## `core/services/visible_model_observe.py`
_Central-observe helpers + thinking-delimiter cleanup for the visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_visible_prefill` | `(provider, model, *, prompt_tokens, prefill_ms)` | Gør ollama-lanens PREFILL-cache MÅLBAR (2026-07-19, blind-spot-luk). | [src](../../../core/services/visible_model_observe.py#L11) |
| function | `_observe_visible_provider_error` | `(provider, model, status_code, detail)` | Gør en VISIBLE-lane provider-fejl synlig i Centralen (stream-cluster). Self-safe. | [src](../../../core/services/visible_model_observe.py#L49) |
| function | `_observe_malformed_stream_payload` | `(provider, model, path, *, ended_malformed, detail=…)` | A11 (spec §11.1): den egne SSE/NDJSON-decoder mødte en malformet/trunkeret | [src](../../../core/services/visible_model_observe.py#L65) |
| function | `_observe_content_empty_thinking_fallback` | `(provider, model, path, thinking_len)` | Reasoning-model svarede i `message.thinking` mens `message.content` var TOM | [src](../../../core/services/visible_model_observe.py#L92) |
| function | `_strip_thinking_delimiters` | `(text)` | Fjern løse thinking-delimiter-tokens hvis et thinking-felt surfaces som svar. | [src](../../../core/services/visible_model_observe.py#L113) |
| function | `_reasoning_fallback_text` | `(reasoning, *, finish_reason=…)` | Surface reasoning only when the provider completed it cleanly. | [src](../../../core/services/visible_model_observe.py#L128) |

## `core/services/visible_model_ollama.py`
_Ollama visible-lane adapter (execute + native NDJSON streaming)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vm` | `()` | Return the ``visible_model`` facade module. | [src](../../../core/services/visible_model_ollama.py#L51) |
| function | `_execute_ollama_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_ollama.py#L66) |
| function | `_apply_thinking_mode` | `(payload, thinking_mode)` | Translate UI thinking-mode label to ollama-chat payload keys. | [src](../../../core/services/visible_model_ollama.py#L173) |
| function | `_apply_visible_ollama_options` | `(payload)` | Set ollama generation options for the visible lane. | [src](../../../core/services/visible_model_ollama.py#L210) |
| function | `_opløs` | `(model)` | Modelnavnet ollama faktisk kender. Fail-open. | [src](../../../core/services/visible_model_ollama.py#L250) |
| function | `_stream_ollama_model` | `(*, message, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model_ollama.py#L259) |
| function | `_probe_ollama_visible_target` | `(*, model, base_url)` | — | [src](../../../core/services/visible_model_ollama.py#L578) |
| function | `_build_ollama_prompt` | `(message, *, model, session_id)` | — | [src](../../../core/services/visible_model_ollama.py#L619) |

## `core/services/visible_model_prompt.py`
_Continuity / support-signal / capability prompt builders for the visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_visible_session_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L30) |
| function | `_visible_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L60) |
| function | `_capability_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L87) |
| function | `_visible_work_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L118) |
| function | `_private_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L159) |
| function | `_growth_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L186) |
| function | `_self_model_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L220) |
| function | `_retained_memory_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L253) |
| function | `_temporal_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L285) |
| function | `visible_capability_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L314) |
| function | `visible_session_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L346) |
| function | `visible_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L355) |
| function | `_capability_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L391) |

## `core/services/visible_model_sse.py`
_SSE / Chat-Completions stream parsing + small cost/token utilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/visible_model_sse.py#L34) |
| function | `_parse_utc` | `(value)` | — | [src](../../../core/services/visible_model_sse.py#L39) |
| function | `_calculate_openai_cost_usd` | `(*, model, input_tokens, output_tokens)` | — | [src](../../../core/services/visible_model_sse.py#L43) |
| function | `_chunk_text` | `(text, size=…)` | — | [src](../../../core/services/visible_model_sse.py#L57) |
| function | `_extract_chat_completion_delta` | `(event)` | — | [src](../../../core/services/visible_model_sse.py#L61) |
| function | `_extract_chat_completion_reasoning` | `(event)` | Pull reasoning_content delta from a streaming Chat Completions chunk. | [src](../../../core/services/visible_model_sse.py#L83) |
| function | `_finalize_openai_tool_calls` | `(tool_calls)` | Normalize OpenAI-style tool_calls so arguments is a dict, not a JSON string. | [src](../../../core/services/visible_model_sse.py#L102) |
| function | `_merge_openai_tool_call_deltas` | `(accumulator, event)` | Merge OpenAI SSE tool_calls delta chunks into a per-index accumulator. | [src](../../../core/services/visible_model_sse.py#L130) |
| function | `_chat_completion_stream_is_terminal` | `(event)` | — | [src](../../../core/services/visible_model_sse.py#L167) |
| function | `_iter_sse_events` | `(response, *, provider=…, model=…)` | Hærdet SSE-decoder (spec §1A + §11.1 A11). | [src](../../../core/services/visible_model_sse.py#L177) |

## `core/services/visible_model_types.py`
_Value/result classes and typed exceptions for the visible model lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `VisibleModelResult` | `` | — | [src](../../../core/services/visible_model_types.py#L22) |
| class | `VisibleModelDelta` | `` | — | [src](../../../core/services/visible_model_types.py#L55) |
| class | `VisibleModelReasoningDelta` | `` | Én tanke-bid fra en thinking-model, UNDER første pas. | [src](../../../core/services/visible_model_types.py#L60) |
| class | `VisibleModelStreamDone` | `` | — | [src](../../../core/services/visible_model_types.py#L74) |
| class | `VisibleModelToolCalls` | `` | — | [src](../../../core/services/visible_model_types.py#L79) |
| class | `VisibleModelStreamCancelled` | `` | — | [src](../../../core/services/visible_model_types.py#L83) |
| class | `VisibleModelRateLimited` | `` | Visible-lanens provider er rate-limited (429) eller returnerede en | [src](../../../core/services/visible_model_types.py#L87) |
| method | `VisibleModelRateLimited.__init__` | `(self, *args, provider=…, model=…)` | — | [src](../../../core/services/visible_model_types.py#L94) |

## `core/services/visible_run_abandonment.py`
_Hvad der sker naar et run doer midt-flugt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_loop_lag` | `()` | Hvor sultent var event-loopet lige nu? | [src](../../../core/services/visible_run_abandonment.py#L40) |
| function | `report_abandoned_run` | `(run, *, abort_kind, run_stage, visible_len)` | Rapportér et run der aldrig naaede sin beslutning. Kaster aldrig. | [src](../../../core/services/visible_run_abandonment.py#L53) |
| function | `abandon_bridge_records` | `(run)` | K6: giv runnets uafklarede godkendelses-poster deres AERLIGE udfald. | [src](../../../core/services/visible_run_abandonment.py#L92) |

## `core/services/visible_run_firstpass.py`
_Ventetiden foer modellens FOERSTE element — livstegn, sandhed og et loft._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `hjerteslag_fase` | `(ventet_s)` | Hvad hjerteslaget skal sige at den laver. | [src](../../../core/services/visible_run_firstpass.py#L96) |
| function | `loft_naaet` | `(ventet_s)` | Har vi ventet laengere end nogen sund koersel nogensinde har gjort? | [src](../../../core/services/visible_run_firstpass.py#L109) |
| function | `opgiv_tekst` | `(ventet_s, *, provider, model)` | Den besked brugeren faar. Den skal sige HVAD der skete og HVOR. | [src](../../../core/services/visible_run_firstpass.py#L114) |

## `core/services/visible_run_interruption.py`
_Hvad afbrød et synligt run — til fejl-envelopen og Centralen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_visible_run_interruption` | `(error_message)` | — | [src](../../../core/services/visible_run_interruption.py#L17) |

## `core/services/visible_run_journal.py`
_Persist the visible run and its composer context for durable recovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mark_visible_run_started` | `(run, *, tool_scope=…, force_user_id=…)` | Record the settings a resumed run needs to keep its original lane. | [src](../../../core/services/visible_run_journal.py#L9) |

## `core/services/visible_run_outcome_state.py`
_Et synligt runs terminale beslutning — og vagten mod en optimistisk standard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RunOutcomeState` | `` | Holder beslutningen og beskytter den mod at blive arvet ved et uheld. | [src](../../../core/services/visible_run_outcome_state.py#L45) |
| method | `RunOutcomeState.__init__` | `(self)` | — | [src](../../../core/services/visible_run_outcome_state.py#L50) |
| method | `RunOutcomeState.status` | `(self)` | — | [src](../../../core/services/visible_run_outcome_state.py#L57) |
| method | `RunOutcomeState.error` | `(self)` | — | [src](../../../core/services/visible_run_outcome_state.py#L61) |
| method | `RunOutcomeState.finalized` | `(self)` | Nåede runnet et eksplicit terminalt punkt? | [src](../../../core/services/visible_run_outcome_state.py#L65) |
| method | `RunOutcomeState.is_default` | `(self)` | Står beslutningen stadig på den optimistiske standard? | [src](../../../core/services/visible_run_outcome_state.py#L70) |
| method | `RunOutcomeState.mark` | `(self, status, *, error=…, finalized=…)` | Træf den terminale beslutning. | [src](../../../core/services/visible_run_outcome_state.py#L75) |
| method | `RunOutcomeState.reach_finalization` | `(self)` | Marker at runnet nåede sit done-yield uden at ændre status. | [src](../../../core/services/visible_run_outcome_state.py#L89) |
| method | `RunOutcomeState.set_error` | `(self, error)` | — | [src](../../../core/services/visible_run_outcome_state.py#L93) |
| method | `RunOutcomeState.downgrade_if_abandoned` | `(self, abort_kind=…)` | Nedgradér en aldrig-nået standard til `interrupted`. Returnerer om | [src](../../../core/services/visible_run_outcome_state.py#L98) |
| method | `RunOutcomeState.__repr__` | `(self)` | — | [src](../../../core/services/visible_run_outcome_state.py#L113) |

## `core/services/visible_run_recovery_coordinator.py`
_Durable, idempotent settlement for every visible-run segment ending._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FailureClass` | `` | — | [src](../../../core/services/visible_run_recovery_coordinator.py#L17) |
| class | `RecoverySettlementRequest` | `` | — | [src](../../../core/services/visible_run_recovery_coordinator.py#L27) |
| class | `RecoverySettlement` | `` | — | [src](../../../core/services/visible_run_recovery_coordinator.py#L41) |
| function | `_was_same_recovery` | `(before, *, reason, final_synthesis)` | — | [src](../../../core/services/visible_run_recovery_coordinator.py#L49) |
| function | `settle_segment` | `(request)` | Settle exactly once before stream closure or continuation dispatch. | [src](../../../core/services/visible_run_recovery_coordinator.py#L60) |

## `core/services/visible_run_recovery_dispatcher.py`
_Én ejer af fortsættelsen — en forladt opgave genoptages præcis én gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_udskydelses_backoff` | `(tidligere)` | Vent længere for hver gang samtalen var optaget — men aldrig i det uendelige. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L44) |
| function | `_er_runtime_processen` | `()` | Runtime-processen dispatcher ikke. Den må forlige, ikke starte. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L54) |
| function | `_besked_fra` | `(record)` | Den oprindelige anmodning — det er DEN opgaven handler om. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L60) |
| function | `recover_due_once` | `(*, owner=…)` | Tag ÉN forfalden opgave og start dens fortsættelse. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L71) |
| function | `signal_recovery_dispatcher` | `()` | Væk dispatcheren nu — kaldes lige efter en durabel afregning. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L181) |
| function | `_loop` | `()` | — | [src](../../../core/services/visible_run_recovery_dispatcher.py#L186) |
| function | `start_recovery_dispatcher` | `()` | Start dispatcheren. `False` = den kører ikke her (og skal ikke). | [src](../../../core/services/visible_run_recovery_dispatcher.py#L200) |
| function | `stop_recovery_dispatcher` | `()` | Stop uden at starte nyt arbejde. En nedlukning afregner, den dispatcher ikke. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L217) |

## `core/services/visible_run_segment_settlement.py`
_Ét sted hvor et unormalt segment-ophør bliver durabelt — før noget lukkes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `failure_class_for` | `(exit_reason)` | Grundens klasse. Ukendt → `RUNTIME`; vi gætter ikke på en udbyder. | [src](../../../core/services/visible_run_segment_settlement.py#L73) |
| class | `SegmentUdfald` | `` | Dommen, den durable post, og hvad kalderen skal sende ud. | [src](../../../core/services/visible_run_segment_settlement.py#L90) |
| function | `settle_user_stop` | `(*, run_id, session_id=…, task_id=…, reason=…)` | Brugeren trykkede stop. Det er endeligt — og skal skrives ned FØRST. | [src](../../../core/services/visible_run_segment_settlement.py#L106) |
| function | `settle_segment_exit` | `(*, run_id, session_id, exit_reason, final_text=…, finish_reason=…, forced_finalize=…, pending_tool_intent=…, explicit_user_cancel=…, waiting_for_user=…, recovery_attempt=…, recovery_limit=…, task_id=…, summary=…, checkpoint_ref=…, generation=…, owner=…, final_synthesis_attempted=…, failure_class=…)` | Gør segmentets ophør durabelt og sig hvad der skal sendes. | [src](../../../core/services/visible_run_segment_settlement.py#L123) |

## `core/services/visible_run_terminal_recovery.py`
_Resolve whether an agentic run segment completed or needs recovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `has_incompletion_evidence` | `(text)` | Explicit unfinished work; absence of a completion keyword is not proof. | [src](../../../core/services/visible_run_terminal_recovery.py#L32) |
| class | `AgenticExitResolution` | `` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L44) |
| function | `resolve_agentic_exit` | `(*, exit_reason, final_text, finish_reason=…, forced_finalize=…, pending_tool_intent=…, recovery_attempt=…, recovery_limit=…)` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L51) |

## `core/services/visible_run_trace.py`
_Sporet gennem én synlig kørsel — og runde-grænserne i den._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_last_visible_execution_trace` | `()` | — | [src](../../../core/services/visible_run_trace.py#L73) |
| function | `_start_visible_execution_trace` | `(run)` | — | [src](../../../core/services/visible_run_trace.py#L77) |
| function | `_update_visible_execution_trace` | `(run, updates)` | — | [src](../../../core/services/visible_run_trace.py#L112) |
| function | `_set_last_visible_execution_trace` | `(trace)` | — | [src](../../../core/services/visible_run_trace.py#L126) |
| function | `_visible_trace_payload` | `(run)` | — | [src](../../../core/services/visible_run_trace.py#L135) |
| function | `_publish_agentic_round_start` | `(*, run_id, round_num)` | Publish runtime.agentic_round_start event and return its event_id. | [src](../../../core/services/visible_run_trace.py#L144) |
| function | `_etiket` | `(vaerktoejer, hensigt)` | Indirektion så tråden kan byttes ud i en test uden at røre modellen. | [src](../../../core/services/visible_run_trace.py#L190) |
| function | `_tanke_resume` | `(tanke, hensigt)` | Indirektion så tråden kan testes uden at røre modellen. | [src](../../../core/services/visible_run_trace.py#L196) |
| function | `udsend_runde_etiket` | `(*, run_id, round_num, vaerktoejer, hensigt=…, tanke=…)` | Skriv én kort etiket for runden og udsend den. Blokerer ALDRIG. | [src](../../../core/services/visible_run_trace.py#L202) |
| function | `haent_ventende` | `(run_id)` | Tøm køen af færdige etiketter for en kørsel. | [src](../../../core/services/visible_run_trace.py#L276) |
| function | `hoest_etiketter` | `(run_id, tur=…, frist_s=…)` | Hent faerdige runde-etiketter — og laeg dem i turen, saa de GEMMES. | [src](../../../core/services/visible_run_trace.py#L287) |
| function | `ryd_ventende` | `(run_id)` | Smid en kørsels kø OG dens tråd-bogholderi væk. | [src](../../../core/services/visible_run_trace.py#L306) |
| function | `haent_ventende_med_frist` | `(run_id, frist_s)` | Tøm køen — men vent KORT på en etiket der stadig regnes. | [src](../../../core/services/visible_run_trace.py#L316) |

## `core/services/visible_runs.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kald_digest` | `(tool_name, arguments)` | Digesten over kaldet — broens definition, ikke en ny. | [src](../../../core/services/visible_runs.py#L263) |
| function | `_godkendelses_ejer` | `(run)` | Hvem skal kunne svare paa dette kort? | [src](../../../core/services/visible_runs.py#L275) |
| function | `_friske_godkendelser` | `(raa)` | Genopliv KUN kort der stadig er inden for deres levetid. | [src](../../../core/services/visible_runs.py#L292) |
| function | `godkendelser_nu` | `()` | Kortene som de ER paa disken. Disken er sandheden, ikke processens kopi. | [src](../../../core/services/visible_runs.py#L344) |
| function | `saet_godkendelse` | `(approval_id, kort)` | Tilfoej ét kort — uden at overskrive den anden proces' kort. | [src](../../../core/services/visible_runs.py#L365) |
| function | `fjern_godkendelse` | `(approval_id)` | Fjern ét kort og giv det tilbage. `None` = det fandtes ikke. | [src](../../../core/services/visible_runs.py#L376) |
| function | `_publicer_approval_requested` | `(*, approval_id, tool, run_id, session_id, result)` | Haendelse naar et godkendelses-kort BLIVER LAVET. | [src](../../../core/services/visible_runs.py#L388) |
| class | `VisibleRun` | `` | — | [src](../../../core/services/visible_runs.py#L480) |
| class | `VisibleRunController` | `` | — | [src](../../../core/services/visible_runs.py#L529) |
| method | `VisibleRunController.attach_stream` | `(self, stream)` | — | [src](../../../core/services/visible_runs.py#L545) |
| method | `VisibleRunController.clear_stream` | `(self)` | — | [src](../../../core/services/visible_runs.py#L548) |
| method | `VisibleRunController.cancel` | `(self)` | — | [src](../../../core/services/visible_runs.py#L551) |
| method | `VisibleRunController.is_cancelled` | `(self)` | — | [src](../../../core/services/visible_runs.py#L558) |
| function | `_thinking_for_round` | `(run, exchanges)` | Tænknings-tilstand for en agentisk FØLGE-runde. | [src](../../../core/services/visible_runs.py#L577) |
| function | `is_visible_run_alive` | `(run_id)` | Den AUTORITATIVE liveness-test — CROSS-PROCES. | [src](../../../core/services/visible_runs.py#L601) |
| function | `start_visible_run` | `(message, session_id=…, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, local_tool_exec=…, surface=…)` | Begin a visible run. | [src](../../../core/services/visible_runs.py#L663) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_runs.py#L981) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_runs.py#L1039) |
| function | `_compact_llm_for_run` | `(prompt)` | Call the compact LLM for run-level summarisation (monkeypatchable). | [src](../../../core/services/visible_runs.py#L1307) |
| function | `_handle_compact_command` | `(run)` | /compact: komprimér nu og giv Jarvis en besked at svare paa. | [src](../../../core/services/visible_runs.py#L1313) |
| function | `_stream_visible_run` | `(run, *, force_user_id=…, tool_scope=…)` | — | [src](../../../core/services/visible_runs.py#L1334) |
| function | `_native_tool_calls_to_capabilities` | `(tool_calls)` | Convert Ollama native tool_calls to capability-plan entries (legacy compat). | [src](../../../core/services/visible_runs.py#L6492) |
| function | `_finalize_second_pass_visible_text` | `(text, *, fallback)` | — | [src](../../../core/services/visible_runs.py#L6564) |
| function | `_bounded_error` | `(error_message, limit=…)` | — | [src](../../../core/services/visible_runs.py#L6597) |
| function | `_sse` | `(event, data)` | — | [src](../../../core/services/visible_runs.py#L6604) |
| class | `PresentationInvariantError` | `` | Raised when user-visible text contains internal runtime markers. | [src](../../../core/services/visible_runs.py#L6608) |
| function | `_assert_presentation_invariant` | `(text)` | — | [src](../../../core/services/visible_runs.py#L6634) |
| function | `_bash_hint` | `(cmd)` | Hvad kommandoen egentlig GØR — ikke dens første ord. | [src](../../../core/services/visible_runs.py#L6794) |
| function | `_hoved_og_genstand` | `(ord_)` | «grep tool_calls» — kommandoen og det den blev kørt på. | [src](../../../core/services/visible_runs.py#L6851) |
| function | `_tool_hint` | `(tool_name, arguments=…)` | Emnet for ét kald — HVAD det handler om, uden label foran. | [src](../../../core/services/visible_runs.py#L6877) |
| function | `_tool_label` | `(tool_name, arguments=…)` | — | [src](../../../core/services/visible_runs.py#L6924) |
| function | `_parse_tc_args` | `(tc)` | Extract arguments dict from a tool call (handles both string and dict forms). | [src](../../../core/services/visible_runs.py#L6939) |
| function | `_maybe_fallback_for_autonomous` | `(run, exc)` | Task 10-beslutningsseam: skal en fejlet model-stream faldes til poolen? | [src](../../../core/services/visible_runs.py#L6951) |
| function | `_complete_visible_run_from_fallback` | `(run, fallback)` | Terminal completion for et AUTONOMT run hvis model-stream fejlede og blev | [src](../../../core/services/visible_runs.py#L6995) |
| function | `_fail_visible_run` | `(run, error_message, *, partial_text=…)` | — | [src](../../../core/services/visible_runs.py#L7053) |
| function | `_cancel_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L7127) |
| function | `register_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L7180) |
| function | `get_visible_run_controller` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7218) |
| function | `cancel_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7222) |
| function | `unregister_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7233) |
| function | `get_active_visible_run` | `()` | — | [src](../../../core/services/visible_runs.py#L7247) |
| function | `get_visible_work` | `()` | — | [src](../../../core/services/visible_runs.py#L7270) |
| function | `get_visible_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L7302) |
| function | `get_visible_selected_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L7329) |
| function | `get_visible_selected_work_item` | `()` | — | [src](../../../core/services/visible_runs.py#L7360) |
| function | `get_visible_selected_work_note` | `()` | — | [src](../../../core/services/visible_runs.py#L7412) |
| function | `get_last_visible_run_outcome` | `()` | — | [src](../../../core/services/visible_runs.py#L7447) |
| function | `get_last_visible_capability_use` | `()` | — | [src](../../../core/services/visible_runs.py#L7451) |
| function | `set_last_visible_capability_use` | `(run, *, capability_id, invocation, capability_arguments=…, argument_source=…)` | — | [src](../../../core/services/visible_runs.py#L7468) |
| function | `_update_cognitive_systems_async` | `(*, run_id, session_id, model, user_message, assistant_response, outcome_status)` | Fire-and-forget updates to all cognitive accumulation systems. | [src](../../../core/services/visible_runs.py#L7518) |

## `core/services/visible_runs_approvals.py`
_Pending tool-approval resolution for visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_er_udloebet` | `(pending)` | Er godkendelsen for gammel til at maatte bruges? Returnerer grunden. | [src](../../../core/services/visible_runs_approvals.py#L34) |
| function | `resolve_pending_approval` | `(approval_id, *, approved, answered_by=…)` | Resolve a pending tool approval. | [src](../../../core/services/visible_runs_approvals.py#L64) |

## `core/services/visible_runs_capabilities.py`
_Workspace-capability planning + execution for visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_capability_plan` | `(text)` | — | [src](../../../core/services/visible_runs_capabilities.py#L35) |
| function | `_execute_visible_capability_entries` | `(run, *, all_capabilities)` | — | [src](../../../core/services/visible_runs_capabilities.py#L135) |
| function | `_planned_visible_capability_steps` | `(run, *, all_capabilities, step_offset)` | — | [src](../../../core/services/visible_runs_capabilities.py#L336) |
| function | `_visible_capability_step_description` | `(*, capability_id, target_path, command_text)` | — | [src](../../../core/services/visible_runs_capabilities.py#L376) |
| function | `_is_known_workspace_capability` | `(capability_id)` | — | [src](../../../core/services/visible_runs_capabilities.py#L397) |
| function | `_resolve_visible_capability_target_path` | `(*, capability_id, capability_arguments, user_message)` | — | [src](../../../core/services/visible_runs_capabilities.py#L406) |
| function | `_extract_external_target_path_from_user_message` | `(user_message)` | — | [src](../../../core/services/visible_runs_capabilities.py#L432) |
| function | `_resolve_visible_capability_command_text` | `(*, capability_id, capability_arguments, user_message)` | — | [src](../../../core/services/visible_runs_capabilities.py#L441) |
| function | `_merge_argument_sources` | `(*sources)` | — | [src](../../../core/services/visible_runs_capabilities.py#L467) |
| function | `_extract_exec_command_from_user_message` | `(user_message)` | — | [src](../../../core/services/visible_runs_capabilities.py#L478) |
| function | `_capability_visible_text` | `(*, capability_id, invocation)` | — | [src](../../../core/services/visible_runs_capabilities.py#L496) |
| function | `_workspace_search_visible_text` | `(*, capability_id, execution_mode, result)` | — | [src](../../../core/services/visible_runs_capabilities.py#L518) |

## `core/services/visible_runs_cognitive.py`
_Per-turn cognitive/candidate tracking-pipeline for visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_visible_cadence_updates` | `(*, run_id, session_id, user_message, assistant_response, outcome_status, user_mood)` | Run post-turn cadence producers without letting them block finalization. | [src](../../../core/services/visible_runs_cognitive.py#L25) |
| function | `_legacy_regex_detectors_enabled` | `()` | Er de gamle ordmønster-detektorer stadig tændt? (default: nej) | [src](../../../core/services/visible_runs_cognitive.py#L58) |
| function | `_track_step_failed` | `()` | En tracker i _track_runtime_candidates fejlede. | [src](../../../core/services/visible_runs_cognitive.py#L73) |
| function | `_track_runtime_candidates` | `(run, assistant_text)` | — | [src](../../../core/services/visible_runs_cognitive.py#L99) |

## `core/services/visible_runs_error_messaging.py`
_User-facing error messages for visible runs (Jarvis voice)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `friendly_provider_error_message` | `(exc)` | Return a Jarvis-voice Danish message for a visible-model exception. | [src](../../../core/services/visible_runs_error_messaging.py#L15) |

