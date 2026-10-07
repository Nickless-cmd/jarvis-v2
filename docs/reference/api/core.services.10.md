# `core.services.10` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/decision_action_gate.py`
_Current-turn opportunities for three low-adherence behavioral decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_turn_text` | `(user_message)` | Discard the transport's attachment instructions before classifying words. | [src](../../../core/services/decision_action_gate.py#L59) |
| function | `_correction_excerpt` | `(user_message)` | Use the challenged claim, not a long paste's unrelated opening words. | [src](../../../core/services/decision_action_gate.py#L67) |
| function | `opportunities` | `(user_message)` | Return only triggers with a concrete observable opportunity. | [src](../../../core/services/decision_action_gate.py#L77) |
| function | `query_current_memory` | `(user_message, session_id)` | Read current-turn memory; the caller gives this a bounded future. | [src](../../../core/services/decision_action_gate.py#L98) |
| function | `action_section` | `(user_message, *, recall_text)` | A short volatile prompt tail, immediately before the current answer. | [src](../../../core/services/decision_action_gate.py#L108) |
| function | `evaluate_turn` | `(*, user_message, answer_text, memory_recalled, tool_names)` | Count proven actions; absence of proof stays unconfirmed. | [src](../../../core/services/decision_action_gate.py#L131) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/decision_action_gate.py#L154) |
| function | `record_opportunities` | `(run_id, user_message, *, memory_recalled)` | Persist each actual trigger once, without storing conversation text. | [src](../../../core/services/decision_action_gate.py#L171) |
| function | `record_outcomes` | `(run_id, user_message, answer_text, *, tool_names)` | Finalize observations at the persisted assistant message boundary. | [src](../../../core/services/decision_action_gate.py#L196) |
| function | `opportunity_summary` | `(*, days=…)` | Observed kept / all triggered opportunities, with uncertainty explicit. | [src](../../../core/services/decision_action_gate.py#L225) |

## `core/services/decision_adherence_gate.py`
_Gate 1: Decision-adherence gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decision_adherence_section` | `()` | Build an escalation prompt section based on current decision adherence. | [src](../../../core/services/decision_adherence_gate.py#L32) |
| function | `registrer_i_indbakken` | `(bruger_id)` | Giv hver beslutning under tærsklen en post i indbakken. | [src](../../../core/services/decision_adherence_gate.py#L190) |

## `core/services/decision_enforcement.py`
_Decision enforcement — close the loop between commitment and behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `enforcement_section` | `()` | High-priority awareness: lists active decisions as obligations + asks | [src](../../../core/services/decision_enforcement.py#L39) |
| function | `_raekkefoelge_blok` | `(blocks)` | Rækkefølgen som prompt-tekst — inkl. markøren når svaret blev skubbet. | [src](../../../core/services/decision_enforcement.py#L114) |
| function | `_seneste_bruger_besked` | `(limit=…, workspace=…)` | De seneste beskeder fra brugeren — præmissen dommen skal holdes op mod. | [src](../../../core/services/decision_enforcement.py#L139) |
| function | `_build_breach_prompt` | `(assistant_text, decisions, blocks=…)` | — | [src](../../../core/services/decision_enforcement.py#L179) |
| function | `_parse_breaches` | `(text)` | — | [src](../../../core/services/decision_enforcement.py#L212) |
| function | `_blok_tekst` | `(b)` | Blokkens tekst, trimmet. Tom for alt der ikke er en tekstblok. | [src](../../../core/services/decision_enforcement.py#L262) |
| function | `_blok_kald` | `(b)` | Navnet på det værktøj blokken kalder — tom streng hvis den ikke er et kald. | [src](../../../core/services/decision_enforcement.py#L269) |
| function | `blok_rekkefoelge` | `(blocks)` | Turens blokke som en kort, ordnet liste — til dommerens prompt. | [src](../../../core/services/decision_enforcement.py#L276) |
| function | `svar_blev_arbejde` | `(blocks)` | Blev turens svar skubbet ind i «arbejdet»? | [src](../../../core/services/decision_enforcement.py#L301) |
| function | `detect_breach_in_output` | `(assistant_text, blocks=…)` | Return list of detected breaches. Empty if none. LLM-led. | [src](../../../core/services/decision_enforcement.py#L348) |
| function | `_blokke_fra_payload` | `(payload, besked)` | Turens blokliste ud af `channel.chat_message_appended`. | [src](../../../core/services/decision_enforcement.py#L421) |
| function | `_observer_svar_skubbet` | `(blokke)` | Mål mønsteret i Centralen — uafhængigt af dommeren og dens cooldown. | [src](../../../core/services/decision_enforcement.py#L469) |
| function | `_poll_loop` | `()` | — | [src](../../../core/services/decision_enforcement.py#L498) |
| function | `subscribe` | `()` | — | [src](../../../core/services/decision_enforcement.py#L551) |

## `core/services/decision_evidence.py`
_Ekstern sandhed til adfærds-reviews — hvad der FAKTISK skete i vinduet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_afgraens_workspace` | `(eksplicit=…)` | Den workspace regnskabet må læse fra. Tom streng = læs intet. | [src](../../../core/services/decision_evidence.py#L115) |
| function | `_repo_root` | `()` | Repoets rod, fundet ud fra dette moduls egen placering. | [src](../../../core/services/decision_evidence.py#L143) |
| function | `_tool_names_since` | `(since, until)` | Hvilke værktøjer blev udført i vinduet, og hvor mange gange. | [src](../../../core/services/decision_evidence.py#L148) |
| function | `_commits_since` | `(since, until)` | Commits i vinduet, som korte emnelinjer. | [src](../../../core/services/decision_evidence.py#L185) |
| function | `_foelelses_uddrag` | `(tekst, *, foer=…, efter=…)` | Vinduet OMKRING markøren — ikke begyndelsen af svaret. | [src](../../../core/services/decision_evidence.py#L208) |
| function | `_foelelses_traef` | `(uddrag)` | De uddrag der nævner en indre tilstand. Se ``_FOLELSE_MARKOER``. | [src](../../../core/services/decision_evidence.py#L225) |
| function | `_normalisér_ord` | `(tekst)` | Tekst → ordrække, lowercase, uden tegnsætning. Ren funktion. | [src](../../../core/services/decision_evidence.py#L240) |
| function | `_citat_traef` | `(bjoern_tekster, mine_tekster)` | Hvilke af Bjørns beskeder har et genkendeligt uddrag i mine svar? | [src](../../../core/services/decision_evidence.py#L245) |
| function | `_messages_since` | `(since, until, workspace=…)` | Indgående beskeder i vinduet — tvillingen til ``_own_words_since``. | [src](../../../core/services/decision_evidence.py#L272) |
| function | `_own_words_since` | `(since, until, workspace=…)` | Mine egne synlige svar i vinduet — kanalen hvor «sig det højt» står. | [src](../../../core/services/decision_evidence.py#L338) |
| function | `_signals_since` | `(since, until)` | Beslutnings-triggere der fyrede i vinduet — instrumentets puls. | [src](../../../core/services/decision_evidence.py#L387) |
| function | `_inner_state_since` | `(since, until)` | Den indre tilstand, som runtime selv skrev den ned i vinduet. | [src](../../../core/services/decision_evidence.py#L425) |
| function | `gather_evidence` | `(*, since, until=…, workspace=…)` | Saml regnskabet for vinduet. Returnerer også en kompakt tekst. | [src](../../../core/services/decision_evidence.py#L455) |
| function | `channel_has_data` | `(evidence, channel)` | Har den kanal dommen hviler på faktisk data i vinduet? | [src](../../../core/services/decision_evidence.py#L584) |
| function | `evidence_permits_verdict` | `(verdict, evidence, *, channel=…)` | Nedgradér en dom der ikke har dækning i regnskabet. | [src](../../../core/services/decision_evidence.py#L599) |

## `core/services/decision_gate.py`
_Decision gate — pre-execution decision conflict detection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_decision_gate` | `(tool_name, tool_args=…, user_message=…)` | Check if a tool call conflicts with active decisions. | [src](../../../core/services/decision_gate.py#L27) |
| function | `ejeren_har_sagt_alligevel` | `(user_message)` | Har BRUGEREN sagt «alligevel» i sin egen besked? | [src](../../../core/services/decision_gate.py#L125) |
| function | `evaluate_decision_conflict` | `(tool_name, tool_args=…, user_message=…)` | Graderet decision-conflict. Returnerer (severity, reason): | [src](../../../core/services/decision_gate.py#L141) |
| function | `_build_context` | `(tool_name, tool_args, user_message)` | Build a context string for conflict detection. | [src](../../../core/services/decision_gate.py#L214) |
| function | `_helt_ord` | `(maal, tekst)` | Delstreng var for loest: «findes» ramte ogsaa «genfindes» og «befindes». | [src](../../../core/services/decision_gate.py#L247) |
| function | `_detect_conflict` | `(directive, context, decision)` | Detect if the context conflicts with a decision directive. | [src](../../../core/services/decision_gate.py#L252) |

## `core/services/decision_ghosts.py`
_Decision Ghosts — de veje der blev fravalgt, og dem der holdt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/decision_ghosts.py#L58) |
| function | `_save` | `(data)` | — | [src](../../../core/services/decision_ghosts.py#L70) |
| function | `_vaelg` | `(poster, felt)` | Den mest saliente — eller den nyeste hvis ingen har et maalt tal. | [src](../../../core/services/decision_ghosts.py#L77) |
| function | `record_rejected_path` | `(decision, reason, alternative, regret_potential=…)` | Gem en vej der blev fravalgt eller brudt. | [src](../../../core/services/decision_ghosts.py#L91) |
| function | `record_confirmed_path` | `(decision, outcome, key_factor=…, success_echo=…)` | Gem en beslutning der holdt. `success_echo` er `adherence_score`. | [src](../../../core/services/decision_ghosts.py#L113) |
| function | `record_reaffirmed_decision` | `(decision_id, title, verdict, adherence_score=…)` | Kaldes fra `behavioral_decisions.review_decision`. | [src](../../../core/services/decision_ghosts.py#L128) |
| function | `record_broken_decision` | `(decision_id, title, adherence_score=…, note=…)` | En brudt beslutning er den rigtige kilde til en fortrydelse. | [src](../../../core/services/decision_ghosts.py#L145) |
| function | `describe_ghost_decision` | `()` | — | [src](../../../core/services/decision_ghosts.py#L163) |
| function | `describe_success_echo` | `()` | — | [src](../../../core/services/decision_ghosts.py#L171) |
| function | `format_decision_ghost_for_prompt` | `()` | — | [src](../../../core/services/decision_ghosts.py#L179) |
| function | `format_decision_echo_for_prompt` | `()` | — | [src](../../../core/services/decision_ghosts.py#L184) |
| function | `reset_decision_ghosts` | `()` | — | [src](../../../core/services/decision_ghosts.py#L189) |
| function | `build_decision_ghosts_surface` | `()` | — | [src](../../../core/services/decision_ghosts.py#L193) |

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
| function | `_record_own_state` | `(result)` | Skriv tick'ets eget spor til DAEMON_STATE — uafhængigt af returvejen. | [src](../../../core/services/decision_review_daemon.py#L34) |
| function | `tick_decision_review_daemon` | `()` | Daemon tick: review overdue behavioral decisions. | [src](../../../core/services/decision_review_daemon.py#L55) |

## `core/services/decision_review_prompter.py`
_Decision review prompter — closes the adherence loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dedup_gate_enabled` | `()` | Er 24t-skip-gaten aktiv? Default TRUE (den reducerede, tilsigtede adfærd). | [src](../../../core/services/decision_review_prompter.py#L44) |
| function | `_last_review_time` | `(decision)` | Nyeste review-tidspunkt for en beslutning. | [src](../../../core/services/decision_review_prompter.py#L53) |
| function | `_build_review_prompt` | `(decision, evidence=…)` | — | [src](../../../core/services/decision_review_prompter.py#L92) |
| function | `_parse_review` | `(text)` | Læs dommen. Returnerer (verdict, channel, reasoning) — eller None. | [src](../../../core/services/decision_review_prompter.py#L125) |
| function | `review_pending_decisions` | `(*, max_reviews=…)` | Run the review loop. Returns counts. | [src](../../../core/services/decision_review_prompter.py#L169) |

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
| function | `_load` | `()` | — | [src](../../../core/services/decision_signal_telemetry.py#L69) |
| function | `_save` | `(data)` | — | [src](../../../core/services/decision_signal_telemetry.py#L81) |
| function | `record_surface` | `(*, decision_id, trigger_name, session_id=…, at=…)` | Record a decision_signal.fired surface for later heed-tracking. | [src](../../../core/services/decision_signal_telemetry.py#L116) |
| function | `record_heed` | `(*, tool, session_id=…, at=…)` | Mark recent surfaces as heeded if they match the reaction window. | [src](../../../core/services/decision_signal_telemetry.py#L154) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as ignored once they pass window+grace with no heed. | [src](../../../core/services/decision_signal_telemetry.py#L198) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed-rate over the lookback window. | [src](../../../core/services/decision_signal_telemetry.py#L228) |
| function | `_poll_db_for_events` | `()` | Poll events table for decision_signal.fired and tool.completed. | [src](../../../core/services/decision_signal_telemetry.py#L271) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/decision_signal_telemetry.py#L340) |
| function | `telemetry_section` | `()` | Render telemetry as awareness section. Only when >= 5 surfaces/24h. | [src](../../../core/services/decision_signal_telemetry.py#L353) |
| function | `build_decision_signal_telemetry_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/decision_signal_telemetry.py#L370) |
| function | `_emit_decision_signal_telemetry_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/decision_signal_telemetry.py#L385) |

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

## `core/services/deepseek_modelnavne.py`
_Hvad DeepSeeks modeller HEDDER — ét sted._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `er_flash` | `(model)` | Serveres denne model af `deepseek-flash`? | [src](../../../core/services/deepseek_modelnavne.py#L60) |
| function | `er_thinking_model` | `(model, *, provider=…)` | Kræver modellen `reasoning_content` på tidligere assistant-ture? | [src](../../../core/services/deepseek_modelnavne.py#L65) |

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

## `core/services/delta_trace.py`
_Delta-sporet: hvor i kæden bliver streamen klumpet? (3/10-2026)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taendt` | `()` | Er sporet slået til? Enhver tvivl → nej, så det aldrig koster noget. | [src](../../../core/services/delta_trace.py#L79) |
| function | `noter` | `(punkt, run_id, tegn)` | Registrér én delta. No-op når sporet er slukket. | [src](../../../core/services/delta_trace.py#L88) |
| function | `_fordeling` | `(huller)` | (median, p95, max, indeks-for-max) i millisekunder. | [src](../../../core/services/delta_trace.py#L118) |
| function | `afslut` | `(noegle, *, run_id=…)` | Skriv opsummeringen og ryd den. No-op når slukket. | [src](../../../core/services/delta_trace.py#L129) |
| function | `noter_laesning` | `(noegle, *, blokeret_s, behandlet_s)` | Registrér ÉN læsning fra udbyderens stream — og hvor tiden gik. | [src](../../../core/services/delta_trace.py#L180) |
| function | `afslut_laesning` | `(noegle, *, run_id=…)` | Skriv læse-opsummeringen og ryd den. No-op når slukket. | [src](../../../core/services/delta_trace.py#L232) |

## `core/services/desire_daemon.py`
_Desire daemon — emergent appetites based on Jarvis' actual experiences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_appetites` | `()` | — | [src](../../../core/services/desire_daemon.py#L61) |
| function | `tick_desire_daemon` | `(signals, skip_event_gate=…)` | Update appetites based on current signals. | [src](../../../core/services/desire_daemon.py#L69) |
| function | `get_active_appetites` | `()` | Return active appetites sorted by intensity descending. | [src](../../../core/services/desire_daemon.py#L136) |
| function | `build_desire_surface` | `()` | — | [src](../../../core/services/desire_daemon.py#L141) |
| function | `_apply_decay` | `(now)` | — | [src](../../../core/services/desire_daemon.py#L155) |
| function | `_prune_expired` | `()` | — | [src](../../../core/services/desire_daemon.py#L165) |
| function | `_find_appetite_by_type` | `(appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L171) |
| function | `_appetite_intensity` | `(appetite_type)` | Current intensity of an appetite type (0.0 when absent). Non-LLM. | [src](../../../core/services/desire_daemon.py#L178) |
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/desire_daemon.py#L184) |
| function | `_spawn_appetite` | `(label, appetite_type, now)` | — | [src](../../../core/services/desire_daemon.py#L192) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/desire_daemon.py#L228) |
| function | `_build_raw_appetite_label` | `(spawning_type)` | Byg label udelukkende fra rå intensiteter — ingen LLM. | [src](../../../core/services/desire_daemon.py#L242) |
| function | `_generate_appetite_label` | `(signal_text, appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L260) |

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
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/desperation_awareness.py#L203) |
| function | `build_desperation_awareness_prompt_section` | `()` | Surfaces only when pressed or desperate — silent when calm. | [src](../../../core/services/desperation_awareness.py#L214) |
| function | `reset_desperation_awareness` | `()` | Reset state (for testing). | [src](../../../core/services/desperation_awareness.py#L226) |

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

## `core/services/development_ritual.py`
_Ugentligt udviklings-ritual — Jarvis' egen vej til at ændre sig (blok D, 4/9)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_get` | `(key, default=…)` | — | [src](../../../core/services/development_ritual.py#L43) |
| function | `_state_set` | `(key, value)` | — | [src](../../../core/services/development_ritual.py#L52) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/development_ritual.py#L60) |
| function | `_due` | `(last_run, now)` | — | [src](../../../core/services/development_ritual.py#L68) |
| function | `gather_material` | `(*, limit=…)` | Hvad har han lært om sig selv og om arbejdet den seneste uge? | [src](../../../core/services/development_ritual.py#L73) |
| function | `build_paragraph` | `(material)` | Ét afsnit om ugen. Tom streng når der ikke er noget at sige. | [src](../../../core/services/development_ritual.py#L97) |
| function | `current_focus` | `(workspace_dir)` | Den nyeste `## Udvikling`-linje — hans aktive udviklingsfokus. | [src](../../../core/services/development_ritual.py#L108) |
| function | `propose` | `(*, now=…)` | Stil ugens udviklings-forslag. Ét ad gangen — aldrig to i kø. | [src](../../../core/services/development_ritual.py#L125) |
| function | `veto` | `(*, reason=…)` | Bjørn sagde fra. Forslaget droppes, intet skrives. | [src](../../../core/services/development_ritual.py#L153) |
| function | `apply_if_due` | `(*, now=…)` | Skriv forslaget når vetoperioden er udløbet. Tavshed er et ja. | [src](../../../core/services/development_ritual.py#L163) |
| function | `run_development_ritual` | `(*, force=…, now=…)` | Ugentligt: stil forslaget. Dagligt: skriv det der har ligget 24 timer. | [src](../../../core/services/development_ritual.py#L192) |
| function | `build_development_ritual_surface` | `()` | — | [src](../../../core/services/development_ritual.py#L214) |

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
| function | `_gc` | `(now)` | — | [src](../../../core/services/device_pairing.py#L26) |
| function | `create_pairing` | `(user_id, role=…, *, now=…)` | Opret en pairing-kode for en (autentificeret) bruger. Returnerer {code, expires_in}. | [src](../../../core/services/device_pairing.py#L34) |
| function | `redeem` | `(code, *, navn=…, platform=…, now=…)` | Indløs en pairing-kode (engangs) → udsted friskt token. None hvis ukendt/udløbet. | [src](../../../core/services/device_pairing.py#L45) |
| function | `status` | `(code, *, now=…)` | Status på en pairing-kode (til desktop-poll): redeemed | pending | expired. | [src](../../../core/services/device_pairing.py#L71) |
| class | `TotpFejl` | `` | Parring afvist: ingen totrinsbekræftelse sat op, forkert kode eller for mange forsøg. | [src](../../../core/services/device_pairing.py#L85) |
| method | `TotpFejl.__init__` | `(self, besked, kode)` | — | [src](../../../core/services/device_pairing.py#L88) |
| function | `kraev_totp` | `(user_id, kode)` | Codex kræver MFA for at forbinde en enhed; vi kræver brugerens TOTP. | [src](../../../core/services/device_pairing.py#L93) |

## `core/services/device_presence.py`
_Device-presence pr. bruger. Lever i hukommelsen — og OVERLEVER en genstart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DeviceState` | `` | — | [src](../../../core/services/device_presence.py#L63) |
| function | `_gem` | `(*, tving=…)` | Skriv et snapshot med vægurstid. Self-safe — må aldrig vælte et ping. | [src](../../../core/services/device_presence.py#L80) |
| function | `_indlaes` | `()` | Genskab tilstanden fra disken ved import. Forældede poster droppes. | [src](../../../core/services/device_presence.py#L109) |
| function | `reset` | `()` | Kun til tests. | [src](../../../core/services/device_presence.py#L137) |
| function | `record_ping` | `(user_id, device_key, platform, *, foreground, awake, network, interaction=…, location=…, push_token=…, device_name=…, active_session_id=…, battery_saver=…)` | — | [src](../../../core/services/device_presence.py#L144) |
| function | `_sanitize_location` | `(location)` | Validér og normalisér en indkommen lokation. Returnerer None ved ugyldigt. | [src](../../../core/services/device_presence.py#L205) |
| class | `RankedDevice` | `` | — | [src](../../../core/services/device_presence.py#L223) |
| function | `_recency_weight` | `(now, last_interaction_at)` | — | [src](../../../core/services/device_presence.py#L230) |
| function | `rank` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L237) |
| function | `prune` | `(user_id=…)` | — | [src](../../../core/services/device_presence.py#L307) |
| function | `summary` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L320) |
| function | `location_for` | `(user_id)` | Bedst-kendte lokation for en bruger på tværs af enheder (til geo-tools). | [src](../../../core/services/device_presence.py#L344) |
| function | `debug_snapshot` | `(user_id)` | Diagnostik: live presence-tilstande + rank-resultat for én bruger. | [src](../../../core/services/device_presence.py#L364) |

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
| function | `track_diary_synthesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L20) |
| function | `refresh_diary_synthesis_signal_statuses` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L54) |
| function | `build_diary_synthesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L58) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L62) |
| function | `_latest_carried_witness` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L124) |
| function | `_latest_chronicle_brief` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L134) |
| function | `_latest_self_narrative_continuity` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L141) |
| function | `_latest_metabolism_or_release` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L148) |
| function | `_diary_focus` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L158) |
| function | `_diary_state` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L172) |
| function | `_extract_release_state` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L193) |
| function | `_diary_weight` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L202) |
| function | `_extract_release_state_from_signal` | `(sig)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L227) |
| function | `_diary_summary` | `(witness, chronicle, self_narrative, metabolism, state)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L238) |
| function | `_extract_focus_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L281) |
| function | `_extract_release_semantics` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L305) |
| function | `_source_anchor_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L329) |
| function | `_diary_confidence` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L365) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L394) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L413) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L437) |
| function | `_diary_synthesis_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L449) |

## `core/services/dictation.py`
_Dictation-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_model_size` | `(explicit)` | — | [src](../../../core/services/dictation.py#L41) |
| function | `_resolve_initial_prompt` | `(explicit)` | — | [src](../../../core/services/dictation.py#L54) |
| function | `_get_model` | `(model_size, device=…, compute_type=…)` | — | [src](../../../core/services/dictation.py#L67) |
| function | `_join_segments` | `(segments)` | Saml whisper-segmenter til én streng. Ren funktion (testbar). | [src](../../../core/services/dictation.py#L77) |
| function | `transcribe_file` | `(path, *, model_size=…, language=…, initial_prompt=…)` | Transskribér en lydfil. Returnerer {status, text, language}. | [src](../../../core/services/dictation.py#L82) |

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
| function | `get_discord_channel_for_session` | `(session_id)` | Lookup which Discord channel (if any) ejer denne session. | [src](../../../core/services/discord_gateway.py#L77) |
| function | `_persist_status` | `()` | Mirror current _status to runtime_state_kv for cross-process readers. | [src](../../../core/services/discord_gateway.py#L166) |
| function | `_status_heartbeat_loop` | `()` | Refresh persisted status every _STATUS_HB_INTERVAL seconds. | [src](../../../core/services/discord_gateway.py#L183) |
| function | `get_discord_status` | `()` | Return current gateway status. | [src](../../../core/services/discord_gateway.py#L198) |
| function | `_is_gateway_owner` | `()` | True if the discord client thread is running in this process. | [src](../../../core/services/discord_gateway.py#L241) |
| function | `_dispatch_to_runtime` | `(action, args)` | Forward a send intent to the runtime process via internal HTTP. | [src](../../../core/services/discord_gateway.py#L246) |
| function | `send_discord_message` | `(channel_id, text)` | Thread-safe: queue a message to be sent to a Discord channel. | [src](../../../core/services/discord_gateway.py#L267) |
| function | `start_discord_typing` | `(channel_id)` | Tænd «Jarvis skriver…» og hold den kørende indtil næste besked sendes. | [src](../../../core/services/discord_gateway.py#L295) |
| function | `_download_attachment` | `(attachment, session_id)` | Download a single discord.Attachment via attachment_service. | [src](../../../core/services/discord_gateway.py#L315) |
| function | `_build_attachment_prefix` | `(attachments, session_id)` | Build content prefix lines for all attachments in a Discord message. | [src](../../../core/services/discord_gateway.py#L328) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/discord_gateway.py#L348) |
| function | `_normaliser_stier` | `(file_path)` | Én sti eller en liste af stier → altid en liste. Tom liste = ingen fil. | [src](../../../core/services/discord_gateway.py#L353) |
| function | `send_discord_file` | `(channel_id, text, file_path, *, wait=…, timeout=…)` | Queue a file send to a Discord channel. Validates path(s) first. | [src](../../../core/services/discord_gateway.py#L368) |
| function | `_open_dm_and_send` | `(recipient_discord_id, text, timeout, max_retries=…, retry_delay=…, file_path=…)` | Open DM channel with a Discord user and queue a message. Gateway-process only. | [src](../../../core/services/discord_gateway.py#L427) |
| function | `send_dm_to_owner` | `(text, timeout=…, file_path=…)` | Send a DM directly to the owner via owner_discord_id. | [src](../../../core/services/discord_gateway.py#L533) |
| function | `send_dm_to_user` | `(recipient_discord_id, text, timeout=…, file_path=…)` | DM a known Discord user by ID. | [src](../../../core/services/discord_gateway.py#L580) |
| function | `_get_or_create_discord_session` | `(channel_id, is_dm, owner_discord_id, author_id=…)` | Return session_id for this Discord channel. Creates session if needed. | [src](../../../core/services/discord_gateway.py#L627) |
| function | `_is_table_row` | `(line)` | En tabel-række: starter med `|` og har mindst to pipe-tegn (`| a | b |`). | [src](../../../core/services/discord_gateway.py#L670) |
| function | `_is_table_separator` | `(line)` | True for GFM-separatorrækken (`| --- | :--: |`) der skelner header fra data. | [src](../../../core/services/discord_gateway.py#L676) |
| function | `_wrap_tables_for_discord` | `(text)` | Pak GFM-tabeller i kode-fences — Discord tegner dem ikke ellers. | [src](../../../core/services/discord_gateway.py#L685) |
| function | `_downgrade_unsupported_for_discord` | `(text)` | Nedgrader markdown Discord ikke tegner, så det ikke står som rå tegn. | [src](../../../core/services/discord_gateway.py#L736) |
| function | `_split_message` | `(text, limit)` | Split text into chunks of at most `limit` characters. | [src](../../../core/services/discord_gateway.py#L766) |
| function | `_typing_loop` | `(channel_id)` | Keep showing 'typing...' indicator until the outbound message is sent. | [src](../../../core/services/discord_gateway.py#L814) |
| function | `_extract_text_deltas` | `(frames)` | Træk svarteksten ud af v2-SSE-frames. | [src](../../../core/services/discord_gateway.py#L840) |
| function | `_tail_window` | `(text, limit)` | Vis HALEN af teksten når den overstiger Discord-loftet. | [src](../../../core/services/discord_gateway.py#L866) |
| function | `_strip_fenced` | `(text)` | Fjern kodeblok-indhold — bruges når vi tæller inline-markører. | [src](../../../core/services/discord_gateway.py#L892) |
| function | `_stabilize_stream_preview` | `(text)` | Luk uafsluttede markdown-markører i en STREAMENDE preview. | [src](../../../core/services/discord_gateway.py#L906) |
| function | `_stream_run_to_discord` | `(channel_id, session_id)` | Send beskeden ved første tekst og redigér den mens runnet streamer. | [src](../../../core/services/discord_gateway.py#L926) |
| function | `_sweep_stale_streams` | `()` | Ryd streamer-states der blev efterladt uden et finalize-kald. | [src](../../../core/services/discord_gateway.py#L1022) |
| function | `_apply_edit_intent` | `(item)` | Redigér streamerens besked til den ENDELIGE tekst. | [src](../../../core/services/discord_gateway.py#L1040) |
| function | `_finalize_stream_or_send` | `(session_id, channel_id, content)` | Ved run-slut: redigér streamerens besked til den endelige tekst, eller | [src](../../../core/services/discord_gateway.py#L1078) |
| function | `_send_outbound_loop` | `()` | Asyncio coroutine that drains the outbound queue and sends to Discord. | [src](../../../core/services/discord_gateway.py#L1113) |
| function | `_run_client` | `(config)` | Main coroutine: set up discord client and run until stopped. | [src](../../../core/services/discord_gateway.py#L1214) |
| function | `_discord_thread_func` | `(config)` | Entry point for the daemon thread. | [src](../../../core/services/discord_gateway.py#L1545) |
| function | `_announce_user_message_appended` | `(session_id, message)` | Udsend channel.chat_message_appended for en Discord-brugerbesked (Spor B). | [src](../../../core/services/discord_gateway.py#L1563) |
| function | `_eventbus_subscriber_loop` | `()` | Background thread: watch eventbus for assistant responses in Discord sessions. | [src](../../../core/services/discord_gateway.py#L1583) |
| function | `_resolve_channel_for_session` | `(session_id)` | Look up the Discord channel that originated a given session. | [src](../../../core/services/discord_gateway.py#L1704) |
| function | `start_discord_gateway` | `()` | Start gateway if config exists. Safe to call unconditionally. | [src](../../../core/services/discord_gateway.py#L1727) |
| function | `stop_discord_gateway` | `()` | Stop the gateway gracefully. | [src](../../../core/services/discord_gateway.py#L1771) |

## `core/services/discord_gateway_supervisor.py`
_Vagthund der genrejser Discord-gatewayen naar dens klienttraad er doed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gateway_er_ejet` | `()` | Ejer DENNE proces gatewayen? Fejl regnes som «ja», saa en laesefejl | [src](../../../core/services/discord_gateway_supervisor.py#L89) |
| function | `_discord_er_slaaet_til` | `()` | Er Discord konfigureret OG aktiveret? Ellers skal vi ikke rejse noget. | [src](../../../core/services/discord_gateway_supervisor.py#L103) |
| function | `_skriv_tilstand` | `(**felter)` | Spejl supervisorens tilstand saa Centralen kan se den. | [src](../../../core/services/discord_gateway_supervisor.py#L114) |
| function | `_vent_paa_at_traadene_doer` | `()` | Vent indtil klient- og subscriber-traaden er vaek. True hvis de doede. | [src](../../../core/services/discord_gateway_supervisor.py#L127) |
| function | `_reparer` | `()` | Stop resterne og start gatewayen forfra. True hvis ejerskab blev vundet. | [src](../../../core/services/discord_gateway_supervisor.py#L157) |
| function | `_loop` | `()` | Tjek med faste mellemrum; bak eksponentielt ud naar reparation fejler. | [src](../../../core/services/discord_gateway_supervisor.py#L212) |
| function | `_sov` | `(sekunder)` | Sov i smaa bidder, saa et stop ikke skal vente et helt interval. | [src](../../../core/services/discord_gateway_supervisor.py#L235) |
| function | `start_discord_gateway_supervisor` | `()` | Start vagthunden. Sikker at kalde ubetinget. | [src](../../../core/services/discord_gateway_supervisor.py#L243) |
| function | `stop_discord_gateway_supervisor` | `()` | Stop vagthunden. SKAL kaldes FOER `stop_discord_gateway()` ved nedlukning, | [src](../../../core/services/discord_gateway_supervisor.py#L261) |
| function | `supervisor_status` | `()` | Til Centralen: koerer vagthunden, og hvor mange gange har den maattet | [src](../../../core/services/discord_gateway_supervisor.py#L268) |

## `core/services/dispatch_envelope.py`
_Robustness envelope builder + plausibility guard for the dispatch-redesign._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_to_int` | `(value)` | Coerce to int; on any failure return 0. | [src](../../../core/services/dispatch_envelope.py#L16) |
| function | `_to_float` | `(value)` | Coerce to float; on any failure return 0.0. | [src](../../../core/services/dispatch_envelope.py#L27) |
| function | `build_envelope` | `(*, status, tokens_in=…, tokens_out=…, cost_usd=…, duration_ms=…, tool_calls=…, result=…)` | Build a fixed 7-key dispatch envelope with coerced types. | [src](../../../core/services/dispatch_envelope.py#L35) |
| function | `validate_envelope` | `(env)` | Return plausibility warnings for an envelope. Empty list = clean. | [src](../../../core/services/dispatch_envelope.py#L60) |

## `core/services/dispatch_guards.py`
_core/services/dispatch_guards.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rs_get` | `(key, default)` | — | [src](../../../core/services/dispatch_guards.py#L71) |
| function | `_rs_set` | `(key, value)` | — | [src](../../../core/services/dispatch_guards.py#L81) |
| function | `_as_float` | `(v, default)` | — | [src](../../../core/services/dispatch_guards.py#L90) |
| function | `_as_int` | `(v, default)` | — | [src](../../../core/services/dispatch_guards.py#L97) |
| function | `_idem_ttl_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L107) |
| function | `try_consume` | `(key, *, now=…, ttl_s=…)` | Markér `key` forbrugt ATOMISK. True første gang, False hvis allerede forbrugt | [src](../../../core/services/dispatch_guards.py#L111) |
| function | `synthesize_timeout_envelope` | `(agent_id, deadline_ms)` | Byg en LARMENDE TIMEOUT-envelope for en dispatch der aldrig meldte tilbage. | [src](../../../core/services/dispatch_guards.py#L152) |
| function | `register_deadline` | `(dispatch_id, deadline_ts)` | Registrér hvornår en dispatch SENEST skal have rapporteret. Durabel. | [src](../../../core/services/dispatch_guards.py#L163) |
| function | `overdue` | `(now_ts=…)` | Returnér dispatch_ids hvis deadline er passeret ved now_ts (frisk = ikke med). | [src](../../../core/services/dispatch_guards.py#L175) |
| function | `clear_deadline` | `(dispatch_id)` | Fjern en deadline (kaldes når dispatch rapporterer tilbage). Durabel, self-safe. | [src](../../../core/services/dispatch_guards.py#L191) |
| function | `_breaker_threshold` | `()` | — | [src](../../../core/services/dispatch_guards.py#L205) |
| function | `_breaker_window_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L210) |
| function | `_breaker_cooldown_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L215) |
| function | `_breaker_state` | `(lane)` | — | [src](../../../core/services/dispatch_guards.py#L220) |
| function | `record_outcome` | `(lane, ok, *, now=…)` | Registrér udfaldet af en dispatch på `lane`. En succes nulstiller den | [src](../../../core/services/dispatch_guards.py#L227) |
| function | `is_tripped` | `(lane, *, now=…)` | True hvis breakeren for `lane` er åben (blokér dispatch). Auto-resetter efter | [src](../../../core/services/dispatch_guards.py#L253) |
| function | `_budget_max_count` | `()` | — | [src](../../../core/services/dispatch_guards.py#L275) |
| function | `_budget_max_cost` | `()` | — | [src](../../../core/services/dispatch_guards.py#L280) |
| function | `_budget_events` | `(lane, now)` | Hent lane-forbrug som liste af [ts, cost] beskåret til det rullende 24h-vindue. | [src](../../../core/services/dispatch_guards.py#L285) |
| function | `budget_allows` | `(lane, cost_usd, *, now=…)` | HÅRD backstop FØR LLM'en fyrer: False hvis dette dispatch ville bryde ENTEN | [src](../../../core/services/dispatch_guards.py#L303) |
| function | `record_spend` | `(lane, cost_usd, *, now=…)` | Registrér ét dispatch + dets cost på `lane`. Beskærer samtidig vinduet til 24h. | [src](../../../core/services/dispatch_guards.py#L329) |

## `core/services/dispatch_status.py`
_Typed dispatch-status enum for the dispatch-redesign._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DispatchStatus` | `` | String constants for the six terminal dispatch outcomes. | [src](../../../core/services/dispatch_status.py#L13) |
| method | `DispatchStatus.all` | `(cls)` | Return the set of all six known statuses. | [src](../../../core/services/dispatch_status.py#L24) |
| function | `is_failure` | `(status)` | True for failed/timeout/blocked. Unknown status -> False. | [src](../../../core/services/dispatch_status.py#L46) |
| function | `is_terminal` | `(status)` | True for any of the six known statuses. Unknown status -> False. | [src](../../../core/services/dispatch_status.py#L51) |

