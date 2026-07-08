# `core.services.08` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/decision_log.py`
_Decision Log — records high-stakes decisions with context, options, and rationale._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_decision` | `(*, title, context=…, options=…, decision=…, why=…, refs=…)` | Record a decision in the log. | [src](../../../core/services/decision_log.py#L20) |
| function | `build_decision_log_surface` | `()` | — | [src](../../../core/services/decision_log.py#L50) |

## `core/services/decision_review_daemon.py`
_Decision review daemon — closes the adherence loop automatically._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_decision_review_daemon` | `()` | Daemon tick: review overdue behavioral decisions. | [src](../../../core/services/decision_review_daemon.py#L34) |

## `core/services/decision_review_prompter.py`
_Decision review prompter — closes the adherence loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_last_review_time` | `(decision)` | — | [src](../../../core/services/decision_review_prompter.py#L30) |
| function | `_build_review_prompt` | `(decision)` | — | [src](../../../core/services/decision_review_prompter.py#L46) |
| function | `_parse_review` | `(text)` | — | [src](../../../core/services/decision_review_prompter.py#L61) |
| function | `review_pending_decisions` | `()` | Run the review loop. Returns counts. | [src](../../../core/services/decision_review_prompter.py#L82) |

## `core/services/decision_signal_staging.py`
_Efemer staging af decision-signals til model-kontekst (2026-07-04 runaway-fix)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compose_signal_note` | `(decision_id, trigger_name, context_summary)` | Den efemere note modellen ser næste runde (omgivet af blanke linjer). | [src](../../../core/services/decision_signal_staging.py#L22) |
| function | `stage_signal` | `(active, decision_id, note, *, cap=…)` | Dedup pr. decision-id (erstat, akkumulér ALDRIG) + cap antal distinkte | [src](../../../core/services/decision_signal_staging.py#L30) |
| function | `compose_exchange_text` | `(base_parts, active)` | Assistant-turen til næste rundes model-input = det ægte svar (`base_parts`) | [src](../../../core/services/decision_signal_staging.py#L46) |

## `core/services/decision_signal_telemetry.py`
_Decision-signal telemetry — track whether decision signals get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/decision_signal_telemetry.py#L51) |
| function | `_save` | `(data)` | — | [src](../../../core/services/decision_signal_telemetry.py#L63) |
| function | `record_surface` | `(*, decision_id, trigger_name, session_id=…, at=…)` | Record a decision_signal.fired surface for later heed-tracking. | [src](../../../core/services/decision_signal_telemetry.py#L75) |
| function | `record_heed` | `(*, tool, session_id=…, at=…)` | Mark recent surfaces as heeded if they match the reaction window. | [src](../../../core/services/decision_signal_telemetry.py#L113) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as ignored once they pass window+grace with no heed. | [src](../../../core/services/decision_signal_telemetry.py#L157) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed-rate over the lookback window. | [src](../../../core/services/decision_signal_telemetry.py#L187) |
| function | `_poll_db_for_events` | `()` | Poll events table for decision_signal.fired and tool.completed. | [src](../../../core/services/decision_signal_telemetry.py#L230) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/decision_signal_telemetry.py#L299) |
| function | `telemetry_section` | `()` | Render telemetry as awareness section. Only when >= 5 surfaces/24h. | [src](../../../core/services/decision_signal_telemetry.py#L312) |
| function | `build_decision_signal_telemetry_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/decision_signal_telemetry.py#L329) |
| function | `_emit_decision_signal_telemetry_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/decision_signal_telemetry.py#L344) |

## `core/services/decision_signals.py`
_Decisions-as-signals: per-turn evaluation of behavioral decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerContext` | `` | Snapshot of state available to a trigger function. | [src](../../../core/services/decision_signals.py#L25) |
| class | `TriggerSpec` | `` | — | [src](../../../core/services/decision_signals.py#L38) |
| class | `FiredDecision` | `` | — | [src](../../../core/services/decision_signals.py#L46) |
| function | `register` | `(name, fire_fn, *, cooldown_seconds=…, cooldown_turns=…)` | — | [src](../../../core/services/decision_signals.py#L60) |
| function | `_active_decisions_with_triggers` | `()` | Return active decisions that have a trigger_name set. | [src](../../../core/services/decision_signals.py#L77) |
| function | `_read_last_fired` | `(decision_id)` | — | [src](../../../core/services/decision_signals.py#L92) |
| function | `_read_last_fired_seq` | `(decision_id)` | — | [src](../../../core/services/decision_signals.py#L106) |
| function | `_write_last_fired` | `(decision_id, iso_ts)` | — | [src](../../../core/services/decision_signals.py#L120) |
| function | `_write_last_fired_seq` | `(decision_id, seq, iso_ts)` | — | [src](../../../core/services/decision_signals.py#L135) |
| function | `_cooldown_active` | `(spec, decision_id, ctx)` | — | [src](../../../core/services/decision_signals.py#L150) |
| function | `_publish_fired_event` | `(*, decision_id, trigger_name, ctx)` | — | [src](../../../core/services/decision_signals.py#L171) |
| function | `evaluate_decision_triggers` | `(ctx)` | Evaluate all active decisions with triggers; return those that fire. | [src](../../../core/services/decision_signals.py#L185) |
| function | `fired_decisions_section` | `(ctx)` | Build the [FIRED_DECISIONS] section text. None if nothing fired. | [src](../../../core/services/decision_signals.py#L251) |
| function | `build_trigger_context` | `(*, user_message=…, session_id=…, run_id=…, consecutive_tool_only_rounds=…, recent_tool_calls=…, recent_assistant_text=…, agentic_round_seq=…)` | Build a TriggerContext from explicit fields. Used in tests and as | [src](../../../core/services/decision_signals.py#L262) |
| function | `get_current_trigger_context_or_build` | `(*, user_message=…, session_id=…)` | Return the bound ContextVar if set, else build a minimal fallback. | [src](../../../core/services/decision_signals.py#L286) |
| function | `bind_context` | `(ctx)` | Bind the per-run TriggerContext. Caller must reset_token after use. | [src](../../../core/services/decision_signals.py#L301) |
| function | `reset_context` | `(token)` | — | [src](../../../core/services/decision_signals.py#L306) |

## `core/services/decision_weight.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_decision_weight` | `(action_description)` | Score an action description on a 1–4 risk scale. | [src](../../../core/services/decision_weight.py#L35) |

## `core/services/decisions_journal.py`
_Decisions Journal — moralsk beslutnings-log (extension of decision_log)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(text)` | — | [src](../../../core/services/decisions_journal.py#L34) |
| function | `_fingerprint` | `(title, decision)` | — | [src](../../../core/services/decisions_journal.py#L38) |
| function | `create_decision_record` | `(*, title, context, options, decision, why, regrets=…, refs=…)` | Journalize a decision. Required: title, decision, why. | [src](../../../core/services/decisions_journal.py#L42) |
| function | `capture_decision_signal` | `(*, event_type, payload, refs=…, strong_signal=…, user_confirmed=…)` | Capture an automatic decision-signal from runtime events. | [src](../../../core/services/decisions_journal.py#L107) |
| function | `find_relevant_decisions` | `(query, *, limit=…)` | Token-overlap search: find decisions matching the query. | [src](../../../core/services/decisions_journal.py#L177) |
| function | `build_decisions_journal_surface` | `()` | MC surface for decisions journal (extension view vs decision_log's basic view). | [src](../../../core/services/decisions_journal.py#L198) |

## `core/services/deep_analyzer.py`
_Deep Analyzer — scoped kodebase-introspection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SelectedFile` | `` | — | [src](../../../core/services/deep_analyzer.py#L43) |
| function | `_keywords` | `(chunks)` | — | [src](../../../core/services/deep_analyzer.py#L50) |
| function | `_file_score` | `(path, keywords)` | Score a file by filename + path match against keywords. | [src](../../../core/services/deep_analyzer.py#L59) |
| function | `_scan_repo` | `(*, root, paths, keywords, max_files, max_file_bytes, max_total_bytes)` | — | [src](../../../core/services/deep_analyzer.py#L68) |
| function | `_is_ignored` | `(path, root)` | — | [src](../../../core/services/deep_analyzer.py#L133) |
| function | `_find_first_keyword_line` | `(lines, keywords)` | — | [src](../../../core/services/deep_analyzer.py#L144) |
| function | `_build_outline` | `(*, goal, question_set, max_sections)` | — | [src](../../../core/services/deep_analyzer.py#L154) |
| function | `_build_findings` | `(*, scope, selected, keywords, max_findings=…)` | — | [src](../../../core/services/deep_analyzer.py#L169) |
| function | `_build_risks` | `(findings)` | — | [src](../../../core/services/deep_analyzer.py#L221) |
| function | `_build_next_steps` | `(*, findings, scope)` | — | [src](../../../core/services/deep_analyzer.py#L241) |
| function | `run_deep_analysis` | `(*, goal, scope=…, paths=…, question_set=…, repo_root=…, max_files=…, max_file_bytes=…, max_total_bytes=…, max_sections=…)` | Run a scoped deep analysis. Returns {summary, findings, risks, next_steps, meta}. | [src](../../../core/services/deep_analyzer.py#L252) |
| function | `build_deep_analyzer_surface` | `()` | MC surface — deep analyzer is stateless but advertises capability + recent runs. | [src](../../../core/services/deep_analyzer.py#L318) |
| function | `evidence_paths_exist` | `(result, repo_root=…)` | Verify all evidence paths referenced in findings actually exist. | [src](../../../core/services/deep_analyzer.py#L334) |

## `core/services/deep_reflection_slot.py`
_Deep Reflection Slot — real think-time, not tick-to-tick alert._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L36) |
| function | `_reflection_dir` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L40) |
| function | `_load` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L44) |
| function | `_save` | `(data)` | — | [src](../../../core/services/deep_reflection_slot.py#L60) |
| function | `_chronicle_summary` | `()` | Pull last-24h visible runs + inner thought fragments. | [src](../../../core/services/deep_reflection_slot.py#L74) |
| function | `_active_dreams` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L112) |
| function | `_shadow_patterns` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L125) |
| function | `_signal_surfaces` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L138) |
| function | `_compose_prompt` | `(chronicle, dreams, shadow, signals)` | — | [src](../../../core/services/deep_reflection_slot.py#L185) |
| function | `_fallback_content` | `(chronicle, dreams, shadow, signals)` | Structural fallback if LLM is unavailable. | [src](../../../core/services/deep_reflection_slot.py#L213) |
| function | `_write_reflection_md` | `(reflection_id, text, sources)` | — | [src](../../../core/services/deep_reflection_slot.py#L237) |
| function | `run_reflection` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L260) |
| function | `_should_run_now` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L328) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/deep_reflection_slot.py#L357) |
| function | `list_recent` | `(*, limit=…)` | — | [src](../../../core/services/deep_reflection_slot.py#L364) |
| function | `build_deep_reflection_surface` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L368) |
| function | `_surface_summary` | `(latest, all_items)` | — | [src](../../../core/services/deep_reflection_slot.py#L384) |
| function | `build_deep_reflection_prompt_section` | `()` | Surface newly completed deep reflection for 12h. | [src](../../../core/services/deep_reflection_slot.py#L393) |

## `core/services/delegation_advisor.py`
_Delegation advisor — inline vs which subagent role._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `advise` | `(task)` | — | [src](../../../core/services/delegation_advisor.py#L46) |
| function | `_exec_delegation_advisor` | `(args)` | — | [src](../../../core/services/delegation_advisor.py#L114) |

## `core/services/delete_policy.py`
_Slette-model — hvem må slette hvad, og hvor hårdt (spec §4.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_delete_action` | `(*, role, is_own_workspace, gdpr_erasure=…)` | Afgør slette-mode for (rolle, om det er eget workspace). | [src](../../../core/services/delete_policy.py#L22) |
| function | `is_delete_confirmed` | `(*, role, confirmations_received)` | True hvis sletningen må udføres givet antal modtagne bekræftelser. | [src](../../../core/services/delete_policy.py#L55) |

## `core/services/desire_daemon.py`
_Desire daemon — emergent appetites based on Jarvis' actual experiences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_appetites` | `()` | — | [src](../../../core/services/desire_daemon.py#L48) |
| function | `tick_desire_daemon` | `(signals)` | Update appetites based on current signals. | [src](../../../core/services/desire_daemon.py#L56) |
| function | `get_active_appetites` | `()` | Return active appetites sorted by intensity descending. | [src](../../../core/services/desire_daemon.py#L95) |
| function | `build_desire_surface` | `()` | — | [src](../../../core/services/desire_daemon.py#L100) |
| function | `_apply_decay` | `(now)` | — | [src](../../../core/services/desire_daemon.py#L114) |
| function | `_prune_expired` | `()` | — | [src](../../../core/services/desire_daemon.py#L124) |
| function | `_find_appetite_by_type` | `(appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L130) |
| function | `_spawn_appetite` | `(label, appetite_type, now)` | — | [src](../../../core/services/desire_daemon.py#L137) |
| function | `_generate_appetite_label` | `(signal_text, appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L173) |

## `core/services/desktop_notifications.py`
_Per-bruger in-memory kø af proaktive desktop-notifikationer. Desktop poller_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reset` | `()` | — | [src](../../../core/services/desktop_notifications.py#L15) |
| function | `enqueue` | `(user_id, item)` | — | [src](../../../core/services/desktop_notifications.py#L20) |
| function | `drain` | `(user_id)` | — | [src](../../../core/services/desktop_notifications.py#L30) |
| function | `prune` | `()` | — | [src](../../../core/services/desktop_notifications.py#L37) |

## `core/services/desperation_awareness.py`
_Desperation Awareness — self-noticing safety signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hardware_component` | `()` | 0..1 contribution from hardware pressure. | [src](../../../core/services/desperation_awareness.py#L28) |
| function | `_tension_component` | `()` | 0..1 contribution from active layer tensions. | [src](../../../core/services/desperation_awareness.py#L42) |
| function | `_isolation_component` | `()` | 0..1 contribution from time since last user interaction. | [src](../../../core/services/desperation_awareness.py#L58) |
| function | `_error_component` | `()` | 0..1 contribution from recent error rate in heartbeat outcomes. | [src](../../../core/services/desperation_awareness.py#L81) |
| function | `compute_desperation_score` | `()` | Compute current desperation composite score in [0, 1] with reasons. | [src](../../../core/services/desperation_awareness.py#L100) |
| function | `tick` | `(_seconds=…)` | Evaluate desperation and emit inner-voice event on threshold crossing. | [src](../../../core/services/desperation_awareness.py#L138) |
| function | `_emit_crossing_event` | `(state, *, direction)` | Publish an inner-voice event so the crossing lands in chronicle. | [src](../../../core/services/desperation_awareness.py#L159) |
| function | `_narrative_for` | `(state, direction)` | — | [src](../../../core/services/desperation_awareness.py#L176) |
| function | `is_currently_pressed` | `()` | — | [src](../../../core/services/desperation_awareness.py#L183) |
| function | `build_desperation_awareness_surface` | `()` | — | [src](../../../core/services/desperation_awareness.py#L187) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/desperation_awareness.py#L199) |
| function | `build_desperation_awareness_prompt_section` | `()` | Surfaces only when pressed or desperate — silent when calm. | [src](../../../core/services/desperation_awareness.py#L210) |
| function | `reset_desperation_awareness` | `()` | Reset state (for testing). | [src](../../../core/services/desperation_awareness.py#L222) |

## `core/services/development_focus_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_development_focuses_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/development_focus_tracking.py#L32) |
| function | `refresh_runtime_development_focus_statuses` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L76) |
| function | `build_runtime_development_focus_surface` | `(*, limit=…)` | — | [src](../../../core/services/development_focus_tracking.py#L120) |
| function | `_extract_focus_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L143) |
| function | `_explicit_learning_focus` | `(message)` | — | [src](../../../core/services/development_focus_tracking.py#L177) |
| function | `_repeated_correction_focus` | `(message, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L222) |
| function | `_runtime_development_focus` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L276) |
| function | `_persist_focuses` | `(*, focuses, session_id, run_id)` | — | [src](../../../core/services/development_focus_tracking.py#L316) |
| function | `_apply_completion_signals` | `(*, user_message, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L391) |
| function | `_enrich_focus_support` | `(candidate, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L438) |
| function | `_candidate_history` | `(canonical_key, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L457) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/development_focus_tracking.py#L477) |
| function | `_matches_correction_key` | `(canonical_key, message)` | — | [src](../../../core/services/development_focus_tracking.py#L498) |
| function | `_after_marker` | `(text, markers)` | — | [src](../../../core/services/development_focus_tracking.py#L509) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/development_focus_tracking.py#L517) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/development_focus_tracking.py#L524) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/development_focus_tracking.py#L528) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/development_focus_tracking.py#L535) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L540) |

## `core/services/development_narrative_daemon.py`
_Development narrative daemon — daily LLM narrative about how Jarvis has changed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_development_narrative_daemon` | `()` | Generate a daily development narrative if cadence allows. | [src](../../../core/services/development_narrative_daemon.py#L16) |
| function | `_generate_narrative` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L33) |
| function | `_store_narrative` | `(narrative)` | — | [src](../../../core/services/development_narrative_daemon.py#L71) |
| function | `get_latest_development_narrative` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L100) |
| function | `build_development_narrative_surface` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L104) |

## `core/services/development_sense.py`
_Development senses — realtime felt-sense of growth, stuck, appetite, resistance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_crisis_resolution_ratio` | `(days=…)` | Resolved-vs-opened over window. None when insufficient data. | [src](../../../core/services/development_sense.py#L34) |
| function | `_adherence_score` | `()` | — | [src](../../../core/services/development_sense.py#L50) |
| function | `_skill_principles_recent` | `(days=…)` | Count skill_mutations recorded in the last N days. Each is a | [src](../../../core/services/development_sense.py#L66) |
| function | `_tick_quality_trend_bonus` | `()` | — | [src](../../../core/services/development_sense.py#L86) |
| function | `growth_pulse` | `()` | Composite 0-1 pulse + components. None-safe. | [src](../../../core/services/development_sense.py#L96) |
| function | `stuck_signal` | `()` | Detect repeating friction without resolution. | [src](../../../core/services/development_sense.py#L139) |
| function | `_topic_words_from_thought_fragments` | `(limit=…)` | — | [src](../../../core/services/development_sense.py#L198) |
| function | `appetite_signal` | `()` | What words/topics show up unprompted in his thought stream + open | [src](../../../core/services/development_sense.py#L214) |
| function | `resistance_signal` | `()` | Where am I acting against my own commitments / drifting from baseline? | [src](../../../core/services/development_sense.py#L233) |
| function | `_is_after` | `(ts, cutoff)` | — | [src](../../../core/services/development_sense.py#L278) |
| function | `development_sense_section` | `()` | Render all 4 senses as one COMPACT prompt-awareness block (2026-05-03). | [src](../../../core/services/development_sense.py#L288) |

## `core/services/developmental_valence.py`
_Developmental Valence — compass needle for flourishing vs withering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_within_window` | `(iso_str, days=…)` | — | [src](../../../core/services/developmental_valence.py#L41) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/developmental_valence.py#L49) |
| function | `_intention_closure_rate` | `()` | Of goal_signals updated in the window, what fraction are still active? | [src](../../../core/services/developmental_valence.py#L55) |
| function | `_dream_confirmation_rate` | `()` | Of dream_hypothesis_signals in window, fraction still carried. | [src](../../../core/services/developmental_valence.py#L76) |
| function | `_loop_health` | `()` | Closed vs total loops in window. Higher = closing what opens. | [src](../../../core/services/developmental_valence.py#L93) |
| function | `_relation_sustained` | `()` | Trust trajectory tail + recent contact density. | [src](../../../core/services/developmental_valence.py#L111) |
| function | `_metabolism` | `()` | Signal → action conversion. | [src](../../../core/services/developmental_valence.py#L149) |
| function | `_compute_components` | `()` | — | [src](../../../core/services/developmental_valence.py#L175) |
| function | `_components_to_vector` | `(components)` | Average of available components, re-centered to [-1, +1]. | [src](../../../core/services/developmental_valence.py#L185) |
| function | `_trajectory_label` | `(vector, delta)` | Map vector + derivative to trajectory label. | [src](../../../core/services/developmental_valence.py#L198) |
| function | `_recompute` | `()` | — | [src](../../../core/services/developmental_valence.py#L211) |
| function | `get_developmental_state` | `()` | Return cached compass state, recomputing only periodically. | [src](../../../core/services/developmental_valence.py#L242) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — no hot work, just trigger recompute when due. | [src](../../../core/services/developmental_valence.py#L252) |
| function | `build_developmental_valence_surface` | `()` | — | [src](../../../core/services/developmental_valence.py#L257) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/developmental_valence.py#L274) |
| function | `build_developmental_valence_prompt_section` | `()` | Speaks up when trajectory is notable — quiet when steady. | [src](../../../core/services/developmental_valence.py#L282) |
| function | `reset_developmental_valence` | `()` | Reset cached state (for testing). | [src](../../../core/services/developmental_valence.py#L305) |

## `core/services/device_pairing.py`
_QR-device-pairing (mobile companion ↔ desktop). Kort-levende engangs-koder._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gc` | `(now)` | — | [src](../../../core/services/device_pairing.py#L22) |
| function | `create_pairing` | `(user_id, role=…, *, now=…)` | Opret en pairing-kode for en (autentificeret) bruger. Returnerer {code, expires_in}. | [src](../../../core/services/device_pairing.py#L30) |
| function | `redeem` | `(code, *, now=…)` | Indløs en pairing-kode (engangs) → udsted friskt token. None hvis ukendt/udløbet. | [src](../../../core/services/device_pairing.py#L41) |
| function | `status` | `(code, *, now=…)` | Status på en pairing-kode (til desktop-poll): redeemed | pending | expired. | [src](../../../core/services/device_pairing.py#L54) |

## `core/services/device_presence.py`
_In-memory device-presence pr. bruger. Efemær — genopbygges af klient-pings._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DeviceState` | `` | — | [src](../../../core/services/device_presence.py#L40) |
| function | `reset` | `()` | Kun til tests. | [src](../../../core/services/device_presence.py#L53) |
| function | `record_ping` | `(user_id, device_key, platform, *, foreground, awake, network, interaction=…, location=…)` | — | [src](../../../core/services/device_presence.py#L59) |
| function | `_sanitize_location` | `(location)` | Validér og normalisér en indkommen lokation. Returnerer None ved ugyldigt. | [src](../../../core/services/device_presence.py#L98) |
| class | `RankedDevice` | `` | — | [src](../../../core/services/device_presence.py#L116) |
| function | `_recency_weight` | `(now, last_interaction_at)` | — | [src](../../../core/services/device_presence.py#L123) |
| function | `rank` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L130) |
| function | `prune` | `(user_id=…)` | — | [src](../../../core/services/device_presence.py#L189) |
| function | `summary` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L202) |
| function | `location_for` | `(user_id)` | Bedst-kendte lokation for en bruger på tværs af enheder (til geo-tools). | [src](../../../core/services/device_presence.py#L226) |
| function | `debug_snapshot` | `(user_id)` | Diagnostik: live presence-tilstande + rank-resultat for én bruger. | [src](../../../core/services/device_presence.py#L246) |

## `core/services/device_tokens.py`
_Per-bruger FCM device-tokens. Egen tabel — rører ikke db.py's 33k linjer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/device_tokens.py#L11) |
| function | `register` | `(user_id, token, platform=…)` | — | [src](../../../core/services/device_tokens.py#L28) |
| function | `list_for_user` | `(user_id)` | — | [src](../../../core/services/device_tokens.py#L45) |
| function | `delete` | `(token)` | — | [src](../../../core/services/device_tokens.py#L57) |

## `core/services/diagnosis_gate.py`
_Diagnosis-gate (spec 2026-06-14) — fanger uverificerede diagnostiske konklusioner._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_promise_footnote` | `(claim_snippet)` | Fodnote-linje for en uverificeret completion-claim (konsistent stil). | [src](../../../core/services/diagnosis_gate.py#L53) |
| class | `DiagnosisResult` | `` | — | [src](../../../core/services/diagnosis_gate.py#L88) |
| class | `DiagnosisEvent` | `` | — | [src](../../../core/services/diagnosis_gate.py#L97) |
| function | `analyze_diagnosis` | `(text, *, tools_used=…)` | Ren detektion: er der en uverificeret diagnostisk konklusion i teksten? | [src](../../../core/services/diagnosis_gate.py#L110) |
| function | `analyze_completion_claim` | `(text, *, tools_used=…)` | Promise-ledger §8: påstår teksten en FULDFØRT handling ('det er committet/ | [src](../../../core/services/diagnosis_gate.py#L151) |
| function | `diagnosis_gate_enforce` | `(text, *, session_id=…, run_id=…, tools_used=…)` | Pipeline-hook (spec §3.2): kører efter fact-gate, før append_chat_message. | [src](../../../core/services/diagnosis_gate.py#L185) |

## `core/services/diary_synthesis_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_diary_synthesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L22) |
| function | `refresh_diary_synthesis_signal_statuses` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L54) |
| function | `build_diary_synthesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L87) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L123) |
| function | `_persist_diary_synthesis_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L185) |
| function | `_latest_carried_witness` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L254) |
| function | `_latest_chronicle_brief` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L264) |
| function | `_latest_self_narrative_continuity` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L271) |
| function | `_latest_metabolism_or_release` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L278) |
| function | `_diary_focus` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L288) |
| function | `_diary_state` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L302) |
| function | `_extract_release_state` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L323) |
| function | `_diary_weight` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L332) |
| function | `_extract_release_state_from_signal` | `(sig)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L357) |
| function | `_diary_summary` | `(witness, chronicle, self_narrative, metabolism, state)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L368) |
| function | `_extract_focus_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L411) |
| function | `_extract_release_semantics` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L435) |
| function | `_source_anchor_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L459) |
| function | `_diary_confidence` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L495) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L524) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L543) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L567) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L579) |

## `core/services/dictation.py`
_Dictation-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_model_size` | `(explicit)` | — | [src](../../../core/services/dictation.py#L22) |
| function | `_get_model` | `(model_size, device=…, compute_type=…)` | — | [src](../../../core/services/dictation.py#L35) |
| function | `_join_segments` | `(segments)` | Saml whisper-segmenter til én streng. Ren funktion (testbar). | [src](../../../core/services/dictation.py#L45) |
| function | `transcribe_file` | `(path, *, model_size=…, language=…)` | Transskribér en lydfil. Returnerer {status, text, language}. | [src](../../../core/services/dictation.py#L50) |

## `core/services/discord_config.py`
_Discord config — load/save ~/.jarvis-v2/config/discord.json._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_discord_config` | `()` | Return config dict or None if missing/invalid. | [src](../../../core/services/discord_config.py#L16) |
| function | `save_discord_config` | `(config)` | Write config with chmod 600. Creates parent dir if needed. | [src](../../../core/services/discord_config.py#L29) |
| function | `is_discord_configured` | `()` | Return True if config exists and has all required keys. | [src](../../../core/services/discord_config.py#L36) |

## `core/services/discord_gateway.py`
_Discord gateway — runs discord.py in a dedicated daemon thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_discord_channel_for_session` | `(session_id)` | Lookup which Discord channel (if any) ejer denne session. | [src](../../../core/services/discord_gateway.py#L46) |
| function | `_persist_status` | `()` | Mirror current _status to runtime_state_kv for cross-process readers. | [src](../../../core/services/discord_gateway.py#L135) |
| function | `_status_heartbeat_loop` | `()` | Refresh persisted status every _STATUS_HB_INTERVAL seconds. | [src](../../../core/services/discord_gateway.py#L152) |
| function | `get_discord_status` | `()` | Return current gateway status. | [src](../../../core/services/discord_gateway.py#L167) |
| function | `_is_gateway_owner` | `()` | True if the discord client thread is running in this process. | [src](../../../core/services/discord_gateway.py#L210) |
| function | `_dispatch_to_runtime` | `(action, args)` | Forward a send intent to the runtime process via internal HTTP. | [src](../../../core/services/discord_gateway.py#L215) |
| function | `send_discord_message` | `(channel_id, text)` | Thread-safe: queue a message to be sent to a Discord channel. | [src](../../../core/services/discord_gateway.py#L236) |
| function | `_download_attachment` | `(attachment, session_id)` | Download a single discord.Attachment via attachment_service. | [src](../../../core/services/discord_gateway.py#L264) |
| function | `_build_attachment_prefix` | `(attachments, session_id)` | Build content prefix lines for all attachments in a Discord message. | [src](../../../core/services/discord_gateway.py#L277) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/discord_gateway.py#L297) |
| function | `send_discord_file` | `(channel_id, text, file_path)` | Queue a file send to a Discord channel. Validates path first. | [src](../../../core/services/discord_gateway.py#L302) |
| function | `_open_dm_and_send` | `(recipient_discord_id, text, timeout, max_retries=…, retry_delay=…)` | Open DM channel with a Discord user and queue a message. Gateway-process only. | [src](../../../core/services/discord_gateway.py#L316) |
| function | `send_dm_to_owner` | `(text, timeout=…)` | Send a DM directly to the owner via owner_discord_id. | [src](../../../core/services/discord_gateway.py#L395) |
| function | `send_dm_to_user` | `(recipient_discord_id, text, timeout=…)` | DM a known Discord user by ID. | [src](../../../core/services/discord_gateway.py#L409) |
| function | `_get_or_create_discord_session` | `(channel_id, is_dm, owner_discord_id, author_id=…)` | Return session_id for this Discord channel. Creates session if needed. | [src](../../../core/services/discord_gateway.py#L451) |
| function | `_split_message` | `(text, limit)` | Split text into chunks of at most `limit` characters. | [src](../../../core/services/discord_gateway.py#L489) |
| function | `_typing_loop` | `(channel_id)` | Keep showing 'typing...' indicator until the outbound message is sent. | [src](../../../core/services/discord_gateway.py#L500) |
| function | `_send_outbound_loop` | `()` | Asyncio coroutine that drains the outbound queue and sends to Discord. | [src](../../../core/services/discord_gateway.py#L526) |
| function | `_run_client` | `(config)` | Main coroutine: set up discord client and run until stopped. | [src](../../../core/services/discord_gateway.py#L579) |
| function | `_discord_thread_func` | `(config)` | Entry point for the daemon thread. | [src](../../../core/services/discord_gateway.py#L891) |
| function | `_announce_user_message_appended` | `(session_id, message)` | Udsend channel.chat_message_appended for en Discord-brugerbesked (Spor B). | [src](../../../core/services/discord_gateway.py#L909) |
| function | `_eventbus_subscriber_loop` | `()` | Background thread: watch eventbus for assistant responses in Discord sessions. | [src](../../../core/services/discord_gateway.py#L929) |
| function | `_resolve_channel_for_session` | `(session_id)` | Look up the Discord channel that originated a given session. | [src](../../../core/services/discord_gateway.py#L1051) |
| function | `start_discord_gateway` | `()` | Start gateway if config exists. Safe to call unconditionally. | [src](../../../core/services/discord_gateway.py#L1074) |
| function | `stop_discord_gateway` | `()` | Stop the gateway gracefully. | [src](../../../core/services/discord_gateway.py#L1118) |

## `core/services/docs_drift_watchdog.py`
_SP5 docs-drift watchdog — surface docs/drift_report.json to the Central as a docs:drift nerve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_report` | `(report_path=…)` | — | [src](../../../core/services/docs_drift_watchdog.py#L17) |
| function | `_report_stale` | `(report_path=…, repo=…)` | Cheap proxy: True if any generated doc under docs/reference is newer than the report | [src](../../../core/services/docs_drift_watchdog.py#L27) |
| function | `check_docs_drift` | `(report_path=…, repo=…)` | — | [src](../../../core/services/docs_drift_watchdog.py#L45) |
| function | `observe_docs_drift` | `()` | Emit the docs:drift signal to Central (timeseries + observe trace). Self-safe. | [src](../../../core/services/docs_drift_watchdog.py#L65) |
| function | `build_docs_drift_surface` | `()` | Read-only surface for /central/docs-drift. Never throws. | [src](../../../core/services/docs_drift_watchdog.py#L83) |
| function | `_run_producer_tick` | `(**_)` | — | [src](../../../core/services/docs_drift_watchdog.py#L97) |
| function | `register_docs_drift_producer` | `()` | Register the docs-drift observation as a ~5-min cadence producer. | [src](../../../core/services/docs_drift_watchdog.py#L102) |

## `core/services/dream_adoption_candidate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_adoption_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L32) |
| function | `refresh_runtime_dream_adoption_candidate_statuses` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L54) |
| function | `build_runtime_dream_adoption_candidate_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L85) |
| function | `_extract_dream_adoption_candidates` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L114) |
| function | `_persist_dream_adoption_candidates` | `(*, candidates, session_id, run_id)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L186) |
| function | `_build_adoption_snapshots` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L260) |
| function | `_with_runtime_view` | `(item, candidate)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L308) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L319) |
| function | `_build_candidate_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L332) |
| function | `_build_candidate_status` | `(*, candidate_type, hypothesis_status, cadence_state)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L348) |
| function | `_build_adoption_confidence` | `(*, candidate_type, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L356) |
| function | `_build_adoption_reason` | `(*, candidate_type, hypothesis_type, adoption_confidence)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L364) |
| function | `_build_adoption_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L372) |
| function | `_build_status_reason` | `(*, candidate_type)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L389) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L397) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L406) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L411) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L416) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L421) |
| function | `_hypothesis_type_from_candidate_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L426) |
| function | `_adoption_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L431) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L440) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L445) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L455) |

## `core/services/dream_articulation.py`
_Bounded dream articulation light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_dream_articulation` | `(*, trigger=…, last_visible_at=…)` | Run one bounded dream-articulation pass. | [src](../../../core/services/dream_articulation.py#L23) |
| function | `build_dream_articulation_from_inputs` | `(*, idle_consolidation, inner_voice_state, emergent_surface, witness_surface, loop_runtime, embodied_state, goal_surface=…, relation_surface=…, autonomy_surface=…, now=…)` | — | [src](../../../core/services/dream_articulation.py#L165) |
| function | `build_dream_articulation_surface` | `()` | — | [src](../../../core/services/dream_articulation.py#L332) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/dream_articulation.py#L364) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/dream_articulation.py#L397) |
| function | `_latest_dream_articulation_signal` | `()` | Return the latest dream hypothesis signal. | [src](../../../core/services/dream_articulation.py#L423) |
| function | `_classify_candidate_state` | `(*, idle_consolidation, emergent_surface, witness_surface, loop_runtime)` | — | [src](../../../core/services/dream_articulation.py#L444) |
| function | `_build_anchor` | `(*, idle_consolidation, witness_summary, emergent_summary, loop_summary)` | — | [src](../../../core/services/dream_articulation.py#L461) |
| function | `_build_signal_type` | `(*, candidate_state, loop_summary)` | — | [src](../../../core/services/dream_articulation.py#L480) |
| function | `_title_suffix` | `(anchor)` | — | [src](../../../core/services/dream_articulation.py#L485) |
| function | `_build_summary` | `(*, candidate_state, source_inputs, body)` | — | [src](../../../core/services/dream_articulation.py#L489) |
| function | `_build_rationale` | `(*, consolidation, voice_result, witness_summary, emergent_summary)` | — | [src](../../../core/services/dream_articulation.py#L502) |
| function | `_build_support_summary` | `(*, source_inputs, candidate_state)` | — | [src](../../../core/services/dream_articulation.py#L522) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/dream_articulation.py#L534) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/dream_articulation.py#L561) |

## `core/services/dream_bias_engine.py`
_Dream bias engine — Lag 2 distillation + bias state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/dream_bias_engine.py#L57) |
| function | `_now` | `()` | — | [src](../../../core/services/dream_bias_engine.py#L64) |
| function | `_validate_dream_output` | `(raw)` | Sanitize LLM output — drop unknown keys, clamp values, force guards. | [src](../../../core/services/dream_bias_engine.py#L70) |
| function | `accumulate_bias` | `(prior, new, intensity)` | Add new bias values to prior, multiplied by intensity, clamped ±1.0. | [src](../../../core/services/dream_bias_engine.py#L119) |
| function | `get_active_dream_bias` | `(*, workspace_id=…)` | Read active bias, honoring kill-switch + TTL. | [src](../../../core/services/dream_bias_engine.py#L140) |
| function | `format_dream_bias_for_heartbeat` | `(*, workspace_id=…)` | Render bias as a structured awareness-section block. | [src](../../../core/services/dream_bias_engine.py#L159) |
| function | `run_dream_bias_distillation` | `(*, workspace_id=…)` | Full pipeline. Called by dream_distillation_daemon each cycle. | [src](../../../core/services/dream_bias_engine.py#L215) |
| function | `_has_minimum_dream_content` | `(*, workspace_id, settings)` | ≥2 new events (regret + aspiration) since the active bias's source_event_ids. | [src](../../../core/services/dream_bias_engine.py#L293) |
| function | `_fetch_regret_corpus` | `(*, since_iso, limit=…)` | Pull events from the 6 regret-heavy sources via the events table. | [src](../../../core/services/dream_bias_engine.py#L332) |
| function | `_summarize_payload` | `(payload, kind)` | Best-effort short-summary line for an event payload. | [src](../../../core/services/dream_bias_engine.py#L391) |
| function | `_fetch_aspiration_corpus` | `(*, since_iso, limit=…)` | Pull positive/aspiration events — kept decisions, goal progress, etc. | [src](../../../core/services/dream_bias_engine.py#L400) |
| function | `_call_llm_for_bias` | `(*, events, max_tokens)` | Call quality-lane LLM with both regret and aspiration events. | [src](../../../core/services/dream_bias_engine.py#L483) |
| function | `_upsert_dream_bias` | `(*, workspace_id, validated, source_events, ttl_hours)` | INSERT new or accumulate into existing row. | [src](../../../core/services/dream_bias_engine.py#L543) |

## `core/services/dream_carry_over.py`
_Dream Carry-Over — hypotheses that survive across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_file` | `()` | — | [src](../../../core/services/dream_carry_over.py#L26) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/dream_carry_over.py#L40) |
| function | `_load` | `()` | — | [src](../../../core/services/dream_carry_over.py#L51) |
| function | `_save` | `()` | — | [src](../../../core/services/dream_carry_over.py#L63) |
| function | `adopt_dream` | `(*, dream_id, content, confidence=…, source_memories=…)` | Adopt a dream hypothesis for carry-over to next session. | [src](../../../core/services/dream_carry_over.py#L79) |
| function | `get_presentable_dream` | `()` | Get the highest-confidence un-presented dream for prompt injection. | [src](../../../core/services/dream_carry_over.py#L126) |
| function | `mark_dream_presented` | `(dream_id)` | Mark a dream as presented in the current session; track carry depth. | [src](../../../core/services/dream_carry_over.py#L139) |
| function | `confirm_dream` | `(dream_id)` | Confirm a dream hypothesis — boost confidence, track confirmed sessions. | [src](../../../core/services/dream_carry_over.py#L151) |
| function | `reject_dream` | `(dream_id)` | Reject a dream hypothesis — archive with 'was_wrong'. | [src](../../../core/services/dream_carry_over.py#L182) |
| function | `promote_confirmed_dream_to_identity` | `(dream_id)` | Promote a high-confidence confirmed dream to identity evolution proposal. | [src](../../../core/services/dream_carry_over.py#L198) |
| function | `format_dream_for_prompt` | `(dream)` | Format a dream for injection into the visible prompt. | [src](../../../core/services/dream_carry_over.py#L218) |
| function | `build_dream_carry_over_surface` | `()` | — | [src](../../../core/services/dream_carry_over.py#L232) |
| function | `maybe_auto_promote_dreams` | `()` | Promote high-confidence confirmed dreams to identity proposals. Returns promoted IDs. | [src](../../../core/services/dream_carry_over.py#L257) |
| function | `_maybe_fade_old_dreams` | `()` | Archive unconfirmed dreams that have been presented too many times. | [src](../../../core/services/dream_carry_over.py#L278) |

## `core/services/dream_consolidation_daemon.py`
_Dream Consolidation — semantic + LLM-driven consolidation during low-activity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L49) |
| function | `_dreams_dir` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L53) |
| function | `_load` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L57) |
| function | `_save` | `(data)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L73) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L85) |
| function | `_is_idle_enough` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L90) |
| function | `_gather_fragments` | `()` | Collect recent text fragments from multiple sources. | [src](../../../core/services/dream_consolidation_daemon.py#L104) |
| function | `_find_themes` | `(fragments)` | Cluster fragments by shared keywords into themes. | [src](../../../core/services/dream_consolidation_daemon.py#L169) |
| function | `_query_fragmented_memories` | `(theme_tokens, theme_texts)` | Find contradictory, low-confidence, or overlapping memories for a theme. | [src](../../../core/services/dream_consolidation_daemon.py#L215) |
| function | `_llm_synthesize_dream` | `(themes, fragments, consolidation_id)` | Run a quality LLM synthesis pass over theme clusters + fragments. | [src](../../../core/services/dream_consolidation_daemon.py#L291) |
| function | `_produce_dream_artifacts` | `(synthesis, consolidation_id, themes)` | Pipe LLM synthesis output into dream notes + hypothesis signals + chronicle. | [src](../../../core/services/dream_consolidation_daemon.py#L372) |
| function | `consolidate_now` | `()` | Run one consolidation pass unconditionally (ignores cooldown). | [src](../../../core/services/dream_consolidation_daemon.py#L508) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — consolidate when idle + cooldown allows. | [src](../../../core/services/dream_consolidation_daemon.py#L575) |
| function | `list_recent_dreams` | `(*, limit=…)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L596) |
| function | `build_dream_consolidation_surface` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L600) |
| function | `_surface_summary` | `(data)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L621) |
| function | `build_dream_consolidation_prompt_section` | `()` | Announce recent dream if fresh (last 6h). | [src](../../../core/services/dream_consolidation_daemon.py#L630) |

## `core/services/dream_continuum.py`
_Dream Continuum — dreams that mature and "think" between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DreamThought` | `` | A thought a dream has between ticks. | [src](../../../core/services/dream_continuum.py#L26) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/dream_continuum.py#L40) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/dream_continuum.py#L44) |
| function | `evolve_dreams` | `(duration)` | Evolve dreams based on elapsed duration since last tick. | [src](../../../core/services/dream_continuum.py#L53) |
| function | `_generate_dream_thought` | `(dream, maturity)` | Generate a thought a dream has during idle. | [src](../../../core/services/dream_continuum.py#L89) |
| function | `get_dream_thoughts` | `(dream_id)` | Get all thoughts for a specific dream. | [src](../../../core/services/dream_continuum.py#L111) |
| function | `get_top_dream_thought` | `()` | Get the most relevant dream thought for prompt injection. | [src](../../../core/services/dream_continuum.py#L125) |
| function | `format_dreams_for_prompt` | `()` | Format dreams and thoughts for prompt injection. | [src](../../../core/services/dream_continuum.py#L139) |
| function | `get_dream_maturity` | `(dream_id)` | Get maturity level of a specific dream. | [src](../../../core/services/dream_continuum.py#L151) |
| function | `reset_dream_continuum` | `()` | Reset dream continuum state (for testing). | [src](../../../core/services/dream_continuum.py#L156) |
| function | `build_dream_continuum_surface` | `()` | Build MC surface for dream continuum. | [src](../../../core/services/dream_continuum.py#L164) |

## `core/services/dream_distillation_daemon.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_bias_pipeline_safe` | `()` | Run the dream-bias distillation pipeline and never raise. | [src](../../../core/services/dream_distillation_daemon.py#L27) |
| function | `run_dream_distillation_daemon` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L41) |
| function | `get_dream_residue_for_prompt` | `(*, max_chars=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L150) |
| function | `build_dream_distillation_surface` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L167) |
| function | `clear_expired_dream_residue` | `(*, now=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L187) |
| function | `_log_dream_landing` | `(*, residue, expired_at)` | Log expired dream residue as observation. Anti-goal: stored for reflection, never fed back. | [src](../../../core/services/dream_distillation_daemon.py#L208) |
| function | `_load_dismissed_inner_voice` | `()` | Load recent inner-voice signals that were suppressed or not surfaced. | [src](../../../core/services/dream_distillation_daemon.py#L235) |
| function | `_load_lost_council_positions` | `()` | Load recent minority council positions that didn't become consensus. | [src](../../../core/services/dream_distillation_daemon.py#L254) |
| function | `_load_deprioritized_initiatives` | `()` | Load recently rejected or expired initiative queue items. | [src](../../../core/services/dream_distillation_daemon.py#L269) |
| function | `_build_dream_residue` | `(*, chronicle_entries, approval_entries, dismissed_inner=…, lost_council=…, deprioritized_initiatives=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L285) |
| function | `_build_residue_prompt` | `(*, chronicle_entries, approval_entries, dismissed_inner=…, lost_council=…, deprioritized_initiatives=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L309) |
| function | `_sanitize_residue` | `(raw)` | — | [src](../../../core/services/dream_distillation_daemon.py#L357) |
| function | `_dream_residue_enabled` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L369) |
| function | `_state` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L374) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/dream_distillation_daemon.py#L379) |

## `core/services/dream_hypothesis_forced.py`
_Forced Dream Hypothesis Generation — 10% probability per heartbeat tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_force_dream_hypothesis` | `()` | Roll 10% chance and if it fires upsert a forced dream hypothesis. | [src](../../../core/services/dream_hypothesis_forced.py#L35) |

## `core/services/dream_hypothesis_generator.py`
_Dream Hypothesis Generator — overraskende forbindelser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L34) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L38) |
| function | `_fingerprint` | `(text)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L78) |
| function | `_basis_fingerprint` | `(signals)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L85) |
| function | `_collect_source_signals` | `(*, max_signals=…)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L97) |
| function | `_build_hypothesis_prompt` | `(sampled)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L169) |
| function | `_extract_dream_json` | `(raw)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L193) |
| function | `_recently_used_signal_refs` | `(*, limit=…)` | Return refs of signals used in the last N hypotheses. | [src](../../../core/services/dream_hypothesis_generator.py#L221) |
| function | `generate_dream_hypothesis` | `()` | Generate one surprising hypothesis by combining 3 random signals. | [src](../../../core/services/dream_hypothesis_generator.py#L244) |
| function | `list_dream_hypotheses` | `(*, presented_only=…, limit=…)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L371) |
| function | `mark_hypothesis_presented` | `(*, hypothesis_id)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L400) |
| function | `build_dream_hypothesis_surface` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L411) |
| function | `build_dream_hypothesis_prompt_section` | `()` | Surface the single highest-confidence unpresented dream hypothesis. | [src](../../../core/services/dream_hypothesis_generator.py#L428) |

## `core/services/dream_hypothesis_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_hypothesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L36) |
| function | `refresh_runtime_dream_hypothesis_signal_statuses` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L58) |
| function | `build_runtime_dream_hypothesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L97) |
| function | `_extract_dream_hypothesis_candidates` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L125) |
| function | `_persist_dream_hypothesis_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L195) |
| function | `_build_dream_snapshots` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L264) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L298) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L307) |
| function | `_build_hypothesis_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L318) |
| function | `_build_signal_status` | `(*, hypothesis_type, recurrence_status, cadence_state)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L333) |
| function | `_build_hypothesis_note` | `(*, hypothesis_type, recurrence_type, domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L341) |
| function | `_build_hypothesis_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L360) |
| function | `_build_status_reason` | `(*, hypothesis_type)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L376) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L384) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L393) |
| function | `_recurrence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L398) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L403) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L408) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L413) |
| function | `_signal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L418) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L423) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L428) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L438) |

## `core/services/dream_influence_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_influence_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L35) |
| function | `refresh_runtime_dream_influence_proposal_statuses` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L57) |
| function | `build_runtime_dream_influence_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L88) |
| function | `_extract_dream_influence_proposals` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L117) |
| function | `_persist_dream_influence_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L194) |
| function | `_build_influence_snapshots` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L267) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L322) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L334) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L348) |
| function | `_influence_target_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L367) |
| function | `_build_proposal_status` | `(*, candidate_status, proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L377) |
| function | `_build_influence_confidence` | `(*, proposal_type, candidate_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L385) |
| function | `_build_proposal_reason` | `(*, proposal_type, candidate_type, influence_confidence)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L393) |
| function | `_build_influence_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L403) |
| function | `_build_status_reason` | `(*, proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L420) |
| function | `_hypothesis_type_from_snapshot` | `(*, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L430) |
| function | `_candidate_state_from_summary` | `(summary)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L434) |
| function | `_influence_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L443) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L452) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L457) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L462) |
| function | `_world_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L467) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L472) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L477) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L482) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L491) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L501) |

## `core/services/dream_influence_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_dream_influence_runtime_surface` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L10) |
| function | `_build_dream_influence_runtime_surface_uncached` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L18) |
| function | `build_dream_influence_runtime_from_sources` | `(*, dream_articulation, guided_learning, adaptive_learning, adaptive_reasoning, affective_meta_state, epistemic_runtime_state, prompt_evolution)` | — | [src](../../../core/services/dream_influence_runtime.py#L30) |
| function | `build_dream_influence_prompt_section` | `(surface=…)` | — | [src](../../../core/services/dream_influence_runtime.py#L139) |
| function | `_derive_influence_state` | `(*, dream_summary, guided_learning, adaptive_learning, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L165) |
| function | `_derive_influence_target` | `(*, influence_state, dream_summary, guided_learning, adaptive_learning, prompt_summary, affective)` | — | [src](../../../core/services/dream_influence_runtime.py#L186) |
| function | `_derive_influence_mode` | `(*, influence_target, dream_summary, guided_learning, adaptive_learning, reasoning, affective, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L212) |
| function | `_derive_influence_strength` | `(*, influence_state, dream_summary, adaptive_learning, prompt_summary, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L239) |
| function | `_derive_influence_hint` | `(*, influence_state, influence_target, influence_mode, guided_learning, adaptive_learning, prompt_summary, dream_artifact)` | — | [src](../../../core/services/dream_influence_runtime.py#L259) |
| function | `_derive_confidence` | `(*, influence_state, influence_strength, epistemic, prompt_summary)` | — | [src](../../../core/services/dream_influence_runtime.py#L289) |
| function | `_source_contributors` | `(*, dream_summary, dream_artifact, guided_learning, adaptive_learning, reasoning, affective, epistemic, prompt_summary)` | — | [src](../../../core/services/dream_influence_runtime.py#L305) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L378) |
| function | `_safe_guided_learning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L388) |
| function | `_safe_adaptive_learning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L398) |
| function | `_safe_adaptive_reasoning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L408) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L418) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L428) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L438) |

