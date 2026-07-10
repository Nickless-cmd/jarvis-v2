# `core.services.15` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/private_temporal_promotion_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_temporal_promotion_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L20) |
| function | `refresh_runtime_private_temporal_promotion_signal_statuses` | `()` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L52) |
| function | `build_runtime_private_temporal_promotion_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L83) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L112) |
| function | `_persist_private_temporal_promotion_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L216) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L285) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L295) |
| function | `_latest_initiative_tension_support` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L305) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L315) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L332) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L352) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L365) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L376) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L391) |
| function | `_value` | `(*candidates, default)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L398) |
| function | `_pull_from_type` | `(promotion_type)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L406) |
| function | `_pull_from_curiosity_type` | `(curiosity_type)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L412) |
| function | `_pressure_from_state_tone` | `(state_tone)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L418) |
| function | `_title_target` | `(title)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L424) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L432) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L444) |

## `core/services/proactive_context_governor.py`
_Proactive context governor — auto-trigger compaction + sub-agent slicing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `should_auto_compact` | `()` | Decide whether prompt_contract should trigger compaction now. | [src](../../../core/services/proactive_context_governor.py#L50) |
| function | `auto_compact_if_needed` | `()` | Run compaction if threshold crossed. Idempotent (cooldown protected). | [src](../../../core/services/proactive_context_governor.py#L90) |
| function | `build_subagent_context_slice` | `(*, role, goal, max_chars=…)` | Compose a tailored context slice for a sub-agent based on goal. | [src](../../../core/services/proactive_context_governor.py#L131) |
| function | `_load_versions` | `()` | — | [src](../../../core/services/proactive_context_governor.py#L188) |
| function | `_save_versions` | `(versions)` | — | [src](../../../core/services/proactive_context_governor.py#L195) |
| function | `save_context_version` | `(*, reason=…)` | Snapshot the current session state. Returns version_id. | [src](../../../core/services/proactive_context_governor.py#L199) |
| function | `list_context_versions` | `(*, limit=…)` | — | [src](../../../core/services/proactive_context_governor.py#L237) |
| function | `recall_context_version` | `(version_id)` | — | [src](../../../core/services/proactive_context_governor.py#L252) |
| function | `_exec_should_auto_compact` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L263) |
| function | `_exec_auto_compact_if_needed` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L267) |
| function | `_exec_build_subagent_context` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L271) |
| function | `_exec_list_context_versions` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L279) |
| function | `_exec_recall_context_version` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L283) |

## `core/services/proactive_loop_lifecycle_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_proactive_loop_lifecycle_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L73) |
| function | `refresh_runtime_proactive_loop_lifecycle_signal_statuses` | `()` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L96) |
| function | `build_runtime_proactive_loop_lifecycle_surface` | `(*, limit=…)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L159) |
| function | `_build_runtime_proactive_loop_lifecycle_surface_uncached` | `(*, limit=…)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L169) |
| function | `_extract_proactive_loop_lifecycle_candidates` | `()` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L216) |
| function | `_build_lifecycle_candidate` | `(*, loop_kind, loop_focus, open_loop, autonomy_pressure, source_anchor, question_readiness, closure_readiness, relation, meaning, witness, chronicle, metabolism, release, initiative, regulation)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L379) |
| function | `_persist_proactive_loop_lifecycle_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L492) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L554) |
| function | `_best_loop_focus` | `(*, latest_loop, attachment, loyalty, relation, meaning)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L586) |
| function | `_normalize_focus_candidate` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L607) |
| function | `_derive_loop_state` | `(*, loop_kind, open_status, question_readiness, closure_readiness, witness_persistence, release_state)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L633) |
| function | `_loop_summary` | `(*, loop_kind, loop_state, loop_focus, question_readiness, closure_readiness)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L653) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L677) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L685) |
| function | `_max_ranked` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L696) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L705) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L714) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L723) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L730) |

## `core/services/proactive_outbound_substrate.py`
_Proactive-outbound substrate — what Jarvis just said proactively._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_summarize_outbound_payload` | `(kind, payload)` | Extract the actual question/message text from a delivered event. | [src](../../../core/services/proactive_outbound_substrate.py#L36) |
| function | `compute_proactive_outbound_substrate` | `(*, window_min=…, max_events=…)` | Return raw proactive-outbound events as substrate strings. | [src](../../../core/services/proactive_outbound_substrate.py#L49) |
| function | `build_proactive_outbound_section` | `()` | Prompt section — proactive messages Jarvis sent in last 30 min. | [src](../../../core/services/proactive_outbound_substrate.py#L101) |

## `core/services/proactive_question_gate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_proactive_question_gates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L52) |
| function | `refresh_runtime_proactive_question_gate_statuses` | `()` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L75) |
| function | `build_runtime_proactive_question_gate_surface` | `(*, limit=…)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L105) |
| function | `_extract_proactive_question_gate_candidates` | `()` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L149) |
| function | `_persist_proactive_question_gates` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L345) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L396) |
| function | `_gate_reason` | `(*, awareness_constrained, release_state, witness_carried, chronicle_weight, loyalty_weight, attachment_weight, question_readiness, continuity_mode)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L419) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L447) |
| function | `_question_continuity_support` | `(*, relation, meaning, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L455) |
| function | `_initiative_loop_gate_continuity_support` | `(*, question_pressure, question_loop, regulation, awareness)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L498) |
| function | `_question_loop_focus` | `(question_loop)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L523) |
| function | `_normalize_focus_candidate` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L535) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L552) |
| function | `_max_ranked` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L563) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L572) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L581) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L590) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L597) |

## `core/services/proactivity_bridge.py`
_Proaktivitets-broen — samler Jarvis' indre spørgsmål/initiativer/undren og overflader dem til_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify` | `(candidate)` | 'urgent' hvis høj/kritisk prioritet eller kritisk kind; ellers 'normal'. Ren. | [src](../../../core/services/proactivity_bridge.py#L17) |
| function | `select` | `(candidates)` | Dedup på source_id, split i urgent/normal, sortér (urgent først/friskest), cap normal-listen. | [src](../../../core/services/proactivity_bridge.py#L26) |
| function | `should_reach_owner` | `(*, owner_present, is_quiet, sent_today, cap, within_cooldown, urgent)` | Ren contact-gate (kalderen injicerer signalerne). Rækkefølge = spam-værn: | [src](../../../core/services/proactivity_bridge.py#L42) |
| function | `build_urgent` | `(item)` | Enkelt-item besked (urgent-gren). | [src](../../../core/services/proactivity_bridge.py#L58) |
| function | `build_digest` | `(normal)` | 'Mens du var væk'-digest af normale items (kort, prioriteret). | [src](../../../core/services/proactivity_bridge.py#L65) |
| function | `_owner_uid` | `()` | Kanonisk owner-uid = owner-resolver'ens discord-id (samme som den virkende outreach-daemon | [src](../../../core/services/proactivity_bridge.py#L83) |
| function | `_owner_presence` | `(uid)` | (present, away_seconds) fra ÆGTE owner-signaler — IKKE runs (som inkluderer autonome → | [src](../../../core/services/proactivity_bridge.py#L100) |
| function | `collect_candidates` | `()` | Læs de EKSISTERENDE kilder (egress-frit, skriver intet). Self-safe → []. | [src](../../../core/services/proactivity_bridge.py#L129) |
| function | `_route` | `(uid, text, importance)` | Send direkte via den eksisterende notifikations-router (springer nudge-brønden over — broen | [src](../../../core/services/proactivity_bridge.py#L153) |
| function | `_observe` | `(nerve, meta)` | — | [src](../../../core/services/proactivity_bridge.py#L168) |
| function | `run_proactivity_bridge_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn. Hybrid: urgent straks / ellers digest / ellers observe suppressed. | [src](../../../core/services/proactivity_bridge.py#L176) |
| function | `register_proactivity_bridge_producer` | `()` | Registrér broen som cadence-producer (~10 min, visible_grace 15 min). | [src](../../../core/services/proactivity_bridge.py#L235) |
| function | `build_proactivity_bridge_surface` | `()` | Read-only surface til /central/proactivity + jc. Self-safe. | [src](../../../core/services/proactivity_bridge.py#L242) |

## `core/services/procedure_bank.py`
_Procedure Bank — reusable procedures learned from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_procedure` | `(*, name, trigger_pattern, procedure_text, success_count=…)` | Record or update a learned procedure. | [src](../../../core/services/procedure_bank.py#L19) |
| function | `build_procedure_surface` | `()` | — | [src](../../../core/services/procedure_bank.py#L45) |

## `core/services/procedure_bank_pipeline.py`
_Procedure Bank Pipeline — lærte rutiner der kan pin'es og matches._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L35) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L39) |
| function | `upsert_procedure` | `(*, name, trigger=…, procedure, pinned=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L64) |
| function | `get_procedure` | `(*, procedure_id=…, procedure_name=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L116) |
| function | `list_procedures` | `(*, query=…, pinned_only=…, limit=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L136) |
| function | `set_procedure_pinned` | `(*, procedure_id=…, procedure_name=…, pinned)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L155) |
| function | `delete_procedure` | `(*, procedure_id=…, procedure_name=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L179) |
| function | `match_procedures_for_text` | `(text, *, limit=…)` | Find procedures whose trigger-string matches given text. | [src](../../../core/services/procedure_bank_pipeline.py#L201) |
| function | `maybe_record_procedure_from_run` | `(*, session_id, tool_calls)` | LivingNeuron Fase B (surface-only): udled en NAVNGIVEN kandidat-procedure fra en kørsel der | [src](../../../core/services/procedure_bank_pipeline.py#L242) |
| function | `build_procedure_bank_surface` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L275) |

## `core/services/process_supervisor.py`
_Process supervisor — track long-running background processes Jarvis spawns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/process_supervisor.py#L44) |
| function | `_ensure_dirs` | `()` | — | [src](../../../core/services/process_supervisor.py#L48) |
| function | `_safe_name` | `(name)` | Sanitize a process name for use in filenames. | [src](../../../core/services/process_supervisor.py#L52) |
| function | `_load_registry` | `()` | — | [src](../../../core/services/process_supervisor.py#L58) |
| function | `_save_registry` | `(reg)` | — | [src](../../../core/services/process_supervisor.py#L70) |
| function | `_pid_alive` | `(pid)` | — | [src](../../../core/services/process_supervisor.py#L78) |
| function | `_read_status` | `(entry)` | Snapshot of a registry entry's live status. | [src](../../../core/services/process_supervisor.py#L93) |
| function | `spawn_process` | `(*, name, command, cwd=…, env=…, replace_if_running=…)` | Spawn a detached background process under supervision. | [src](../../../core/services/process_supervisor.py#L125) |
| function | `list_processes` | `(*, include_stopped=…)` | — | [src](../../../core/services/process_supervisor.py#L219) |
| function | `_stop_locked` | `(reg, name, grace)` | Caller must hold _LOCK. Stops the named process gracefully. | [src](../../../core/services/process_supervisor.py#L229) |
| function | `stop_process` | `(name, *, grace=…)` | — | [src](../../../core/services/process_supervisor.py#L264) |
| function | `tail_process_log` | `(name, *, lines=…)` | — | [src](../../../core/services/process_supervisor.py#L271) |
| function | `remove_process` | `(name)` | Remove an entry from the registry. Refuses if still alive. | [src](../../../core/services/process_supervisor.py#L303) |

## `core/services/process_watcher.py`
_Process watcher — push-notification primitive for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/process_watcher.py#L74) |
| function | `_state_path` | `(state_file)` | Resolve a state file path. Accepts absolute, ~ expansion, or | [src](../../../core/services/process_watcher.py#L78) |
| function | `_walk_field` | `(obj, path)` | Walk a dotted path through nested dicts. Returns None if any | [src](../../../core/services/process_watcher.py#L90) |
| class | `Watch` | `` | — | [src](../../../core/services/process_watcher.py#L105) |
| function | `_load_all` | `()` | — | [src](../../../core/services/process_watcher.py#L121) |
| function | `_save_all` | `(watches)` | — | [src](../../../core/services/process_watcher.py#L158) |
| function | `add_watch` | `(*, label, conditions, on_match, notify_text=…, cooldown_seconds=…, one_shot=…)` | Register a new watch. Returns the created Watch as dict, or error. | [src](../../../core/services/process_watcher.py#L172) |
| function | `remove_watch` | `(watch_id)` | — | [src](../../../core/services/process_watcher.py#L224) |
| function | `list_watches` | `()` | — | [src](../../../core/services/process_watcher.py#L234) |
| function | `set_watch_enabled` | `(watch_id, enabled)` | — | [src](../../../core/services/process_watcher.py#L239) |
| function | `_eval_condition` | `(cond, runtime_state)` | Evaluate a single condition. Returns (matched, reason). | [src](../../../core/services/process_watcher.py#L252) |
| function | `_fire_action` | `(watch, reason)` | Execute the watch's on_match action. Errors are logged, not raised. | [src](../../../core/services/process_watcher.py#L415) |
| function | `_evaluate_watches_once` | `()` | One pass: evaluate every enabled watch; fire matched ones. | [src](../../../core/services/process_watcher.py#L489) |
| function | `_watcher_loop` | `()` | — | [src](../../../core/services/process_watcher.py#L559) |
| function | `start_watcher_daemon` | `()` | Start the daemon if not already running. Called once at jarvis-api boot. | [src](../../../core/services/process_watcher.py#L576) |
| function | `stop_watcher_daemon` | `()` | Signal the daemon to exit. For tests / shutdown hooks. | [src](../../../core/services/process_watcher.py#L588) |

## `core/services/producer_novelty.py`
_core/services/producer_novelty.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `infer_caller` | `()` | Gæt den originerende service fra call-stacken når cadence-thread-local mangler (fx | [src](../../../core/services/producer_novelty.py#L34) |
| function | `set_producer` | `(name)` | Sæt hvilken producer der kører NU (cadence-tråden). Self-safe. | [src](../../../core/services/producer_novelty.py#L58) |
| function | `clear_producer` | `()` | — | [src](../../../core/services/producer_novelty.py#L66) |
| function | `get_producer` | `()` | — | [src](../../../core/services/producer_novelty.py#L73) |
| function | `_similarity` | `(a, b)` | — | [src](../../../core/services/producer_novelty.py#L77) |
| function | `record_output` | `(producer, text)` | Registrér en producers LLM-output + mål nyhed = 1 - (max-lighed vs dens seneste N). | [src](../../../core/services/producer_novelty.py#L84) |
| function | `snapshot` | `()` | Read-only overblik: pr. producer antal kald + gennemsnitlig nyhed. Lav avg = repetitiv | [src](../../../core/services/producer_novelty.py#L115) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/producer_novelty.py#L127) |

## `core/services/promise_ledger.py`
_Promise-ledger (Bjørn-gate) — 16. jun 2026._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_promise` | `(session_id, text, *, now=…)` | Notér at Jarvis lovede en handling i `session_id`. Capper til de seneste N. | [src](../../../core/services/promise_ledger.py#L22) |
| function | `pending_promises` | `(session_id, *, within_s=…, now=…)` | Ikke-forældede løfter for `session_id` (nyeste sidst). [] ved fejl/tomt. | [src](../../../core/services/promise_ledger.py#L41) |
| function | `clear_promises` | `(session_id)` | Ryd løfterne for en session (fx når Bjørn bekræfter de er indfriet). | [src](../../../core/services/promise_ledger.py#L62) |

## `core/services/prompt_contract.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_track_relevance_decision` | `(decision)` | — | [src](../../../core/services/prompt_contract.py#L40) |
| function | `_track_memory_selection` | `(selection, mode, candidate_count)` | — | [src](../../../core/services/prompt_contract.py#L72) |
| function | `build_runtime_memory_selection_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L95) |
| function | `build_runtime_relevance_decision_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L122) |
| function | `build_runtime_inner_visible_prompt_bridge_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L147) |
| class | `PromptAssembly` | `` | — | [src](../../../core/services/prompt_contract.py#L219) |
| class | `PromptRelevanceDecision` | `` | — | [src](../../../core/services/prompt_contract.py#L234) |
| function | `_permissive_relevance` | `(mode=…)` | All-on relevance-default når relevance-futuren timer ud — inkludér ALT (berigelse | [src](../../../core/services/prompt_contract.py#L265) |
| class | `MemorySectionSelection` | `` | — | [src](../../../core/services/prompt_contract.py#L279) |
| class | `InnerVisiblePromptBridgeDecision` | `` | — | [src](../../../core/services/prompt_contract.py#L292) |
| function | `_safe_build_cognitive_state_for_prompt` | `(*, compact)` | — | [src](../../../core/services/prompt_contract.py#L309) |
| function | `_safe_build_self_state_block` | `()` | — | [src](../../../core/services/prompt_contract.py#L319) |
| function | `_honesty_rules_section` | `(*, compact)` | De ufravigelige ærligheds-regler i den cacheable prefix. | [src](../../../core/services/prompt_contract.py#L328) |
| function | `_curated_memory_index_section` | `(name=…)` | Kurateret memory-INDEX (spec 2026-07-10 Spec B): altid-loadet én-linjers for | [src](../../../core/services/prompt_contract.py#L368) |
| function | `build_visible_stable_prefix` | `(*, provider=…, model=…, name=…, compact=…)` | Build ONLY the stable cacheable prefix of a visible chat prompt. | [src](../../../core/services/prompt_contract.py#L405) |
| function | `_device_awareness_on` | `()` | — | [src](../../../core/services/prompt_contract.py#L502) |
| function | `_device_presence_line` | `(user_id)` | Hvilken enhed Bjørn er ved (routing-awareness). Killswitch-gatet, best-effort. | [src](../../../core/services/prompt_contract.py#L510) |
| function | `build_visible_chat_prompt_assembly` | `(*, provider, model, user_message, session_id=…, name=…, runtime_self_report_context=…)` | — | [src](../../../core/services/prompt_contract.py#L522) |
| function | `build_heartbeat_prompt_assembly` | `(*, heartbeat_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L2487) |
| function | `build_future_agent_task_prompt_assembly` | `(*, task_brief, agent_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L2639) |
| function | `_relevance_cache_key` | `(text, mode, compact, name)` | Build a string cache key for shared_cache (cross-worker visibility). | [src](../../../core/services/prompt_contract.py#L2769) |
| function | `build_prompt_relevance_decision` | `(text, *, mode, compact, name=…)` | — | [src](../../../core/services/prompt_contract.py#L2776) |
| function | `_bounded_nl_relevance_backend` | `(*, text, mode, compact, name)` | — | [src](../../../core/services/prompt_contract.py#L2873) |
| function | `_track_inner_visible_prompt_bridge` | `(decision)` | — | [src](../../../core/services/prompt_contract.py#L2888) |
| function | `_build_inner_visible_prompt_bridge_decision` | `(*, user_message, mode, compact, relevance)` | — | [src](../../../core/services/prompt_contract.py#L2918) |
| function | `_latest_active_inner_visible_support_signal` | `()` | — | [src](../../../core/services/prompt_contract.py#L2997) |
| function | `_inner_visible_support_bridge_is_redundant` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3005) |
| function | `_inner_visible_support_prompt_line` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3015) |
| function | `_self_mutation_lineage_section` | `()` | Returns a compact section about recent self-changes, or None if none. | [src](../../../core/services/prompt_contract.py#L3076) |
| function | `_channel_workspace_path` | `()` | — | [src](../../../core/services/prompt_contract.py#L3108) |
| function | `_channel_context_section` | `(session_id)` | Returns current channel context for the prompt, or None. | [src](../../../core/services/prompt_contract.py#L3112) |
| function | `_workspace_memory_section` | `(path, *, label, user_message, max_lines, max_chars, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_contract.py#L3161) |
| function | `_today_daily_memory_lines` | `(*, limit=…)` | Read today's daily memory lines for injection into visible prompts. | [src](../../../core/services/prompt_contract.py#L3188) |
| function | `_recent_daily_memory_lines` | `(*, limit=…, days=…)` | — | [src](../../../core/services/prompt_contract.py#L3201) |
| function | `_workspace_memory_entries` | `(path)` | — | [src](../../../core/services/prompt_contract.py#L3226) |
| function | `_select_relevant_memory_entries` | `(entries, *, user_message, max_lines, max_chars, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_contract.py#L3243) |
| function | `_bounded_nl_memory_selection` | `(*, user_message, entries, max_lines, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_contract.py#L3310) |
| function | `_visible_chat_rules_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L3332) |
| function | `_self_correction_nudges_section` | `(*, compact)` | Behavioral hints that push the model toward verify-before-done, | [src](../../../core/services/prompt_contract.py#L3349) |
| function | `_output_discipline_instruction` | `(*, strength)` | Tiered output discipline (harness Part 1). BOTH tiers get 'synthesize & stop' (safe for weak — | [src](../../../core/services/prompt_contract.py#L3377) |
| function | `_central_notices_section` | `()` | Medium-niveau Central-notices til Jarvis (spec 2026-06-23 §2). IKKE severe (dem | [src](../../../core/services/prompt_contract.py#L3397) |
| function | `_pending_promises_section` | `(session_id)` | Bjørn-gate (16. jun 2026): rejs Jarvis' åbne fremtids-løfter prominent, så | [src](../../../core/services/prompt_contract.py#L3428) |
| function | `_connected_connectors_section` | `()` | Surface brugerens FORBUNDNE plugins/connectors så Jarvis ved han har adgang. | [src](../../../core/services/prompt_contract.py#L3457) |
| function | `_open_questions_section` | `(*, limit=…)` | Surface curiosity_daemon._open_questions into the visible prompt. | [src](../../../core/services/prompt_contract.py#L3502) |
| function | `_time_pin_section` | `()` | Prominent, unmissable time indicator — placed high in every system prompt. | [src](../../../core/services/prompt_contract.py#L3531) |
| function | `_quick_facts_section` | `(*, workspace_dir, max_chars=…)` | Always-on facts block. Unlike MEMORY.md, this is NOT relevance-filtered — | [src](../../../core/services/prompt_contract.py#L3569) |
| function | `_visible_capability_truth_instruction` | `(*, compact)` | — | [src](../../../core/services/prompt_contract.py#L3592) |
| function | `_visible_capability_id_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L3614) |
| function | `_local_model_behavior_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L3622) |
| function | `_visible_finitude_context_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L3674) |
| function | `_visible_support_signal_sections` | `(*, compact, include, user_message=…, session_id=…)` | — | [src](../../../core/services/prompt_contract.py#L3684) |
| function | `_proactive_outbound_section` | `()` | Recent proactive messages Jarvis sent (substrate for user-reply context). | [src](../../../core/services/prompt_contract.py#L3725) |
| function | `_agreement_streak_section` | `()` | Surface last 3+ agreement-opener assistant replies as substrate. | [src](../../../core/services/prompt_contract.py#L3741) |
| function | `_emotion_concept_tone_section` | `()` | Affect-relevant runtime substrate (replaces tone-hint injection). | [src](../../../core/services/prompt_contract.py#L3755) |
| function | `_emotion_signal_section` | `()` | Aktive emotion concepts som data — giver Jarvis sit eget følelsespanel. | [src](../../../core/services/prompt_contract.py#L3803) |
| function | `_experience_substrate_section` | `(*, user_message=…, session_id=…)` | Nylige lignende situationer (embedding-retrieval substrat). | [src](../../../core/services/prompt_contract.py#L3905) |
| function | `_visible_chronicle_context_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L3979) |
| function | `_visible_dream_residue_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L3989) |
| function | `_visible_unconscious_temperature_field_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L3999) |
| function | `_visible_response_style_hint_section` | `()` | Lag 10 Site 4: response-style modifiers from user temperature field. | [src](../../../core/services/prompt_contract.py#L4011) |
| function | `_visible_current_pull_section` | `()` | Lag 5: inject current pull as quiet first-priority context. | [src](../../../core/services/prompt_contract.py#L4039) |
| function | `_visible_visual_memory_section` | `()` | Lag 6: inject latest visual room memory + ambient sound + echo signals + morning thread. | [src](../../../core/services/prompt_contract.py#L4050) |
| function | `_delegated_continuity_summary` | `(context)` | — | [src](../../../core/services/prompt_contract.py#L4143) |
| function | `_should_include_memory` | `(text, *, mode)` | — | [src](../../../core/services/prompt_contract.py#L4171) |
| function | `_should_include_guidance` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4205) |
| function | `_should_include_transcript` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4223) |
| function | `_should_include_continuity` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4242) |
| function | `prompt_mode_loader_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L4255) |

## `core/services/prompt_evolution.py`
_Prompt evolution — versioning + rollback safety net for workspace prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/prompt_evolution.py#L41) |
| function | `_ensure_table` | `()` | Create workspace_prompt_versions table if missing. Idempotent. | [src](../../../core/services/prompt_evolution.py#L45) |
| function | `snapshot_workspace_file` | `(*, filename, content, reason=…, workspace_id=…, created_by=…)` | Persist a snapshot of a workspace file. | [src](../../../core/services/prompt_evolution.py#L70) |
| function | `list_prompt_history` | `(*, filename, limit=…)` | Return recent versions of a file, newest first. Excludes content | [src](../../../core/services/prompt_evolution.py#L145) |
| function | `get_version` | `(*, version_id)` | Fetch a specific version including full content. | [src](../../../core/services/prompt_evolution.py#L171) |
| function | `rollback_to_version` | `(*, workspace_dir, filename, version_id, snapshot_current_first=…)` | Restore a workspace file to a specific historical version. | [src](../../../core/services/prompt_evolution.py#L190) |
| function | `recommend_rollback_after_change` | `(*, filename, hours=…)` | Score recent telemetry to assess whether the most recent change to | [src](../../../core/services/prompt_evolution.py#L248) |

## `core/services/prompt_evolution_runtime.py`
_Bounded runtime prompt evolution / self-authored prompt proposals light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_prompt_evolution_runtime` | `(*, trigger=…, last_visible_at=…)` | Run one bounded prompt-evolution proposal pass. | [src](../../../core/services/prompt_evolution_runtime.py#L28) |
| function | `build_prompt_evolution_from_inputs` | `(*, dream_articulation, dream_influence, self_model_surface, inner_voice_state, emergent_surface, embodied_state, loop_runtime, adaptive_learning, guided_learning, adaptive_reasoning, now=…)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L179) |
| function | `build_prompt_evolution_runtime_surface` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L424) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L486) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L524) |
| function | `_latest_prompt_evolution_proposal` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L548) |
| function | `_choose_proposal_type` | `(*, dream_articulation, dream_influence, self_model_surface, embodied_state, loop_runtime, adaptive_learning)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L555) |
| function | `_target_asset_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L601) |
| function | `_prompt_target_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L611) |
| function | `_build_anchor` | `(*, dream_articulation, self_model_surface, loop_runtime)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L621) |
| function | `_build_rationale` | `(*, proposal_type, target_asset, learning_influence, dream_influence, candidate_fragment, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L651) |
| function | `_proposal_state_from_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L705) |
| function | `_confidence_from_inputs` | `(*, proposal_type, source_input_count, self_model_surface)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L713) |
| function | `_build_learning_influence` | `(adaptive_learning)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L728) |
| function | `_build_dream_influence_summary` | `(dream_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L738) |
| function | `_build_fragment_co_influence` | `(*, adaptive_learning, dream_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L748) |
| function | `_build_candidate_fragment` | `(*, proposal_type, target_asset, prompt_target, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, embodied_state)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L772) |
| function | `_build_fragment_grounding` | `(*, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L843) |
| function | `_build_review_light` | `(*, proposal_type, prompt_target, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, embodied_state, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L874) |
| function | `_sanitize_fragment` | `(text)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L981) |
| function | `_support_fields_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L985) |
| function | `_learning_influence_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L998) |
| function | `_fragment_grounding_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1011) |
| function | `_dream_influence_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1024) |
| function | `_review_light_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1036) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1048) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1077) |

## `core/services/prompt_heartbeat_self_knowledge.py`
_Heartbeat self-knowledge section builder._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_heartbeat_self_knowledge_section` | `()` | Build a compact self-knowledge section for the heartbeat prompt. | [src](../../../core/services/prompt_heartbeat_self_knowledge.py#L19) |

## `core/services/prompt_mutation_loop.py`
_Prompt Mutation Loop — apply, score, auto-rollback on negative score._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L55) |
| function | `_workspace_path` | `(target_file)` | — | [src](../../../core/services/prompt_mutation_loop.py#L59) |
| function | `_load` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L63) |
| function | `_save` | `(items)` | — | [src](../../../core/services/prompt_mutation_loop.py#L77) |
| class | `PromptMutationError` | `` | — | [src](../../../core/services/prompt_mutation_loop.py#L91) |
| function | `_check_target` | `(target_file)` | Raise PromptMutationError if the target is not safely mutable. | [src](../../../core/services/prompt_mutation_loop.py#L95) |
| function | `_active_mutation_for_file` | `(items, target_file)` | — | [src](../../../core/services/prompt_mutation_loop.py#L111) |
| function | `_recent_mutation_for_file` | `(items, target_file, now)` | — | [src](../../../core/services/prompt_mutation_loop.py#L121) |
| function | `_snapshot_signals` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L139) |
| function | `_score_mutation` | `(item)` | — | [src](../../../core/services/prompt_mutation_loop.py#L171) |
| function | `apply_mutation` | `(*, target_file, new_content, source=…, reason=…, metadata=…)` | Write new_content to target_file, snapshotting previous content. | [src](../../../core/services/prompt_mutation_loop.py#L194) |
| function | `rollback_mutation` | `(mutation_id, *, note=…, auto=…)` | Restore the file to its pre-mutation content. Returns True on success. | [src](../../../core/services/prompt_mutation_loop.py#L269) |
| function | `record_mutation` | `(*, target_file, source=…, reason=…, metadata=…)` | Record that a mutation was applied externally (no file write). | [src](../../../core/services/prompt_mutation_loop.py#L321) |
| function | `resolve_mutation` | `(mutation_id, *, outcome, note=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L359) |
| function | `_update_and_maybe_auto_rollback` | `(item, now)` | Returns 'unchanged' | 'updated' | 'auto_rolled_back'. | [src](../../../core/services/prompt_mutation_loop.py#L376) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L423) |
| function | `list_mutations` | `(*, status=…, limit=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L446) |
| function | `get_mutation` | `(mutation_id, *, include_snapshot=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L457) |
| function | `list_evolvable_files` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L466) |
| function | `list_protected_files` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L470) |
| function | `build_prompt_mutation_loop_surface` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L476) |
| function | `_surface_summary` | `(monitoring, adopted, rolled_back, auto_rolled)` | — | [src](../../../core/services/prompt_mutation_loop.py#L508) |
| function | `build_prompt_mutation_loop_prompt_section` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L528) |

## `core/services/prompt_observer.py`
_Prompt-cluster (Den Intelligente Central) — Phase 1: live on/off + trace for de_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_overrides` | `()` | Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build). | [src](../../../core/services/prompt_observer.py#L66) |
| function | `section_enabled` | `(label, *, blacklisted, overrides)` | Skal denne prompt-sektion med? | [src](../../../core/services/prompt_observer.py#L94) |
| function | `observe_build` | `(*, lane, included, dropped_disabled, dropped_budget, dropped_error=…)` | Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget | [src](../../../core/services/prompt_observer.py#L104) |
| function | `observe_section_error` | `(label, error, *, lane=…)` | En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar). | [src](../../../core/services/prompt_observer.py#L130) |
| function | `set_section` | `(label, enabled)` | Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar. | [src](../../../core/services/prompt_observer.py#L144) |
| function | `list_overrides` | `()` | Read-only projektion af aktive overrides (til MC/debug). | [src](../../../core/services/prompt_observer.py#L152) |

## `core/services/prompt_relevance_backend.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_with_wall_clock_timeout` | `(fn, *, timeout)` | Run ``fn()`` in a daemon thread with a hard wall-clock deadline. | [src](../../../core/services/prompt_relevance_backend.py#L22) |
| class | `_BoundedLLMCall` | `` | Result of a bounded LLM call — neutral across Ollama / OllamaFreeAPI. | [src](../../../core/services/prompt_relevance_backend.py#L51) |
| function | `_call_bounded_relevance_llm` | `(prompt)` | Dispatch a bounded relevance/memory-selection prompt. | [src](../../../core/services/prompt_relevance_backend.py#L62) |
| function | `_call_openai_compat_relevance` | `(*, provider, prompt, model, timeout)` | Generic openai-compat relevance call (mistral, nim, openrouter, ...). | [src](../../../core/services/prompt_relevance_backend.py#L123) |
| function | `_call_opencode_relevance` | `(*, prompt, model, timeout)` | Call OpenCode Zen free models via the OpenAI-compatible cheap lane. | [src](../../../core/services/prompt_relevance_backend.py#L208) |
| function | `_call_ollamafreeapi_relevance` | `(*, prompt, model, timeout)` | OllamaFreeAPI silently drops its ``timeout`` kwarg, so we run the call | [src](../../../core/services/prompt_relevance_backend.py#L283) |
| function | `_call_local_ollama_relevance` | `(*, prompt)` | — | [src](../../../core/services/prompt_relevance_backend.py#L345) |
| class | `BoundedPromptRelevanceResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L409) |
| class | `BoundedPromptRelevanceAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L421) |
| class | `BoundedMemorySelectionResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L432) |
| class | `BoundedMemorySelectionAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L439) |
| function | `run_bounded_nl_prompt_relevance` | `(*, text, mode, compact, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L449) |
| function | `bounded_nl_prompt_relevance_smoke` | `(*, text, workspace_dir, mode=…, compact=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L520) |
| function | `run_bounded_nl_memory_entry_selection` | `(*, user_message, entries, max_lines, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L545) |
| function | `load_visible_relevance_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L622) |
| function | `load_visible_memory_selection_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L636) |
| function | `_resolve_relevance_target` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L650) |
| function | `_selected_relevance_model` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L670) |
| function | `_build_relevance_prompt` | `(*, instructions, text, mode, compact)` | — | [src](../../../core/services/prompt_relevance_backend.py#L676) |
| function | `_build_memory_selection_prompt` | `(*, instructions, user_message, entries, max_lines, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L697) |
| function | `_parse_relevance_response` | `(text, mode)` | — | [src](../../../core/services/prompt_relevance_backend.py#L722) |
| function | `_parse_memory_selection_response` | `(text, *, entry_count, max_lines)` | — | [src](../../../core/services/prompt_relevance_backend.py#L759) |
| function | `_bounded_memory_candidates` | `(entries)` | — | [src](../../../core/services/prompt_relevance_backend.py#L810) |
| function | `_coerce_bool` | `(value)` | — | [src](../../../core/services/prompt_relevance_backend.py#L821) |

## `core/services/prompt_support_signals.py`
_Bounded inner-layer support signal builders._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_private_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L37) |
| function | `_growth_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L54) |
| function | `_self_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L72) |
| function | `_retained_memory_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L89) |
| function | `_reflection_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L109) |
| function | `_world_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L155) |
| function | `_goal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L201) |
| function | `_runtime_awareness_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L248) |
| function | `_development_focus_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L294) |
| function | `_temporal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L341) |
| function | `_reflection_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L358) |
| function | `_world_model_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L369) |
| function | `_goal_direction_label` | `(goal_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L378) |
| function | `_runtime_awareness_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L386) |
| function | `_development_focus_direction_label` | `(focus_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L399) |

## `core/services/prompt_variant_tracker.py`
_Prompt variant tracker — log per-variant performance for self-improvement._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `log_variant_outcome` | `(*, scope, variant_label, outcome_score, notes=…)` | Record a variant's outcome. scope is e.g. 'awareness.tier_recommendation'. | [src](../../../core/services/prompt_variant_tracker.py#L39) |
| function | `variant_performance` | `(*, scope=…, min_samples=…)` | Aggregate per-variant performance, optionally filtered by scope. | [src](../../../core/services/prompt_variant_tracker.py#L76) |
| function | `winning_variant` | `(scope, *, min_samples=…)` | Return the best-performing variant for a scope, or None if not enough data. | [src](../../../core/services/prompt_variant_tracker.py#L119) |
| function | `_exec_log_variant_outcome` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L128) |
| function | `_exec_variant_performance` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L137) |

## `core/services/proposal_classifier.py`
_Proposal classifier — detects action impulses in thought fragments and scores destructiveness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_fragment` | `(fragment)` | Classify a thought fragment for action impulses. | [src](../../../core/services/proposal_classifier.py#L59) |

## `core/services/proprioception_metrics.py`
_Proprioception Metrics — process-level body sense._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_psutil` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L32) |
| function | `_current_snapshot` | `()` | Sample current process stats. | [src](../../../core/services/proprioception_metrics.py#L40) |
| function | `_measure_self_latency_ms` | `()` | Measure trivial self-dispatch as a crude latency proxy. | [src](../../../core/services/proprioception_metrics.py#L70) |
| function | `_emit` | `(kind, payload)` | — | [src](../../../core/services/proprioception_metrics.py#L83) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/proprioception_metrics.py#L91) |
| function | `recent_snapshots` | `(*, limit=…)` | — | [src](../../../core/services/proprioception_metrics.py#L134) |
| function | `build_proprioception_metrics_surface` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L138) |
| function | `_surface_summary` | `(current, rss_trend)` | — | [src](../../../core/services/proprioception_metrics.py#L171) |
| function | `build_proprioception_metrics_prompt_section` | `()` | Only surfaces when something is actively worth noticing. | [src](../../../core/services/proprioception_metrics.py#L187) |
| function | `reset_proprioception_metrics` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L207) |

## `core/services/prose_tool_calls.py`
_Parser for prosa-emitterede tool-kald (cluster: tool-leak-fix 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_match_json_object` | `(s, start)` | s[start] skal være '{'. Returnér (objekt-streng, slut-index) via brace-matching | [src](../../../core/services/prose_tool_calls.py#L26) |
| function | `extract_prose_tool_calls` | `(text, valid_tool_names)` | Find `[navn]: {json}`-prosa-kald hvor navn er et kendt tool og args er et | [src](../../../core/services/prose_tool_calls.py#L55) |

## `core/services/prospective_memory.py`
_Prospective memory — plant seeds for the future, harvest when context arrives._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/prospective_memory.py#L44) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/prospective_memory.py#L48) |
| function | `_ensure_table` | `()` | Create prospective_seeds table if missing. Idempotent. | [src](../../../core/services/prospective_memory.py#L61) |
| function | `_row_to_seed` | `(row)` | — | [src](../../../core/services/prospective_memory.py#L92) |
| function | `plant_seed` | `(*, title, summary=…, activate_at=…, activate_on_event=…, activate_on_context=…, expires_at=…, relevance_score=…, linked_goal=…, linked_project=…, workspace_id=…)` | Plant a forward-looking intention. Returns the new seed dict. | [src](../../../core/services/prospective_memory.py#L104) |
| function | `list_seeds` | `(*, status=…, limit=…, workspace_id=…)` | Return seeds, optionally filtered by status. Newest first. | [src](../../../core/services/prospective_memory.py#L167) |
| function | `summarize_seeds` | `(*, workspace_id=…)` | Status counts for dashboard / observability. | [src](../../../core/services/prospective_memory.py#L194) |
| function | `fulfill_seed` | `(*, seed_id, outcome_note=…, workspace_id=…)` | Mark a seed as fulfilled (Jarvis acted on it). | [src](../../../core/services/prospective_memory.py#L218) |
| function | `ignore_seed` | `(*, seed_id, reason=…, workspace_id=…)` | Mark a seed as ignored (Jarvis chose not to act on a triggered seed). | [src](../../../core/services/prospective_memory.py#L250) |
| function | `heartbeat_tick` | `(*, event_type=…, context_tokens=…, now_ts=…, workspace_id=…)` | One tick of the prospective-memory engine. Call from heartbeat or | [src](../../../core/services/prospective_memory.py#L274) |
| function | `_set_status` | `(seed_id, workspace_id, status, *, triggered_at_now=…)` | — | [src](../../../core/services/prospective_memory.py#L348) |
| function | `build_prospective_memory_surface` | `(*, limit=…, workspace_id=…)` | Surface prospective seeds without triggering or mutating them. | [src](../../../core/services/prospective_memory.py#L377) |

## `core/services/provider_circuit_breaker.py`
_Provider circuit breaker — skip primaries that have been failing recently._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(provider, model)` | — | [src](../../../core/services/provider_circuit_breaker.py#L39) |
| function | `_prune_old_failures` | `(failures, now)` | — | [src](../../../core/services/provider_circuit_breaker.py#L43) |
| function | `record_failure` | `(provider, model)` | Record a primary-call failure. Returns updated state for this key. | [src](../../../core/services/provider_circuit_breaker.py#L49) |
| function | `record_success` | `(provider, model)` | Clear failure tracking on success — provider seems healthy again. | [src](../../../core/services/provider_circuit_breaker.py#L67) |
| function | `should_skip` | `(provider, model)` | True when breaker is open for this (provider, model). | [src](../../../core/services/provider_circuit_breaker.py#L77) |
| function | `breaker_state` | `()` | Observability snapshot — returns open breakers + recent failure counts. | [src](../../../core/services/provider_circuit_breaker.py#L95) |
| function | `reset_all` | `()` | Test/admin helper — clear all state. | [src](../../../core/services/provider_circuit_breaker.py#L128) |
| class | `_PPState` | `` | Per-provider breaker-state (consecutive-i-træk-state-maskine). | [src](../../../core/services/provider_circuit_breaker.py#L160) |
| method | `_PPState.__init__` | `(self, threshold, cooldown_s, window_s)` | — | [src](../../../core/services/provider_circuit_breaker.py#L168) |
| class | `_PerProviderBreaker` | `` | Proces-lokal per-provider-keyed breaker. Trådsikker, self-safe. | [src](../../../core/services/provider_circuit_breaker.py#L179) |
| method | `_PerProviderBreaker.__init__` | `(self, *, threshold=…, cooldown_s=…, window_s=…)` | — | [src](../../../core/services/provider_circuit_breaker.py#L189) |
| method | `_PerProviderBreaker._key` | `(provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L204) |
| method | `_PerProviderBreaker.configure` | `(self, provider_id, *, threshold=…, cooldown_s=…, window_s=…)` | Per-provider-tærskler (ofa/arko bevarer deres historiske tal). | [src](../../../core/services/provider_circuit_breaker.py#L207) |
| method | `_PerProviderBreaker._state` | `(self, pid)` | — | [src](../../../core/services/provider_circuit_breaker.py#L235) |
| method | `_PerProviderBreaker.record_failure` | `(self, provider_id, *, now=…)` | Fejl → opdatér state. True hvis breakeren NETOP åbnede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L247) |
| method | `_PerProviderBreaker.record_success` | `(self, provider_id)` | Success → luk (reset). True hvis den netop lukkede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L273) |
| method | `_PerProviderBreaker.is_open` | `(self, provider_id, *, now=…)` | OPEN nu (→ kort-slut)? Cooldown udløbet → half-open (slip én probe → | [src](../../../core/services/provider_circuit_breaker.py#L288) |
| method | `_PerProviderBreaker.snapshot` | `(self, provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L306) |
| method | `_PerProviderBreaker.reset_all` | `(self)` | — | [src](../../../core/services/provider_circuit_breaker.py#L323) |
| function | `_observe_pp` | `(nerve, provider_id, **data)` | Observér en per-provider breaker-kant til Centralen (cluster="stream"). | [src](../../../core/services/provider_circuit_breaker.py#L332) |
| function | `pp_configure` | `(provider_id, **kw)` | Sæt per-provider-tærskler på den delte breaker (ofa/arko-løft). | [src](../../../core/services/provider_circuit_breaker.py#L346) |
| function | `pp_record_failure` | `(provider_id)` | Registrér en provider-fejl på den DELTE per-provider breaker + observér | [src](../../../core/services/provider_circuit_breaker.py#L351) |
| function | `pp_record_success` | `(provider_id)` | Registrér success på den delte per-provider breaker + observér close-kant. | [src](../../../core/services/provider_circuit_breaker.py#L366) |
| function | `pp_is_open` | `(provider_id)` | Er ``provider_id``'s delte breaker OPEN lige nu? (Fail-open.) | [src](../../../core/services/provider_circuit_breaker.py#L374) |
| function | `pp_snapshot` | `(provider_id)` | Debug/observe-snapshot af den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L379) |
| function | `pp_reset_all` | `()` | Test/admin: nulstil HELE den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L384) |

## `core/services/provider_health_check.py`
_Provider health check — periodic ping to detect outages early._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ping_host` | `(url)` | HTTP GET with short timeout. Returns reachable=True/False + latency_ms. | [src](../../../core/services/provider_health_check.py#L48) |
| function | `health_check_all_providers` | `()` | Ping every cheap-lane provider once. Returns per-provider status. | [src](../../../core/services/provider_health_check.py#L66) |
| function | `_cheap_dry_providers` | `()` | Providers i cheap-lane-cooldown (tør/quota-blokeret) — fra runtime-state. Self-safe. | [src](../../../core/services/provider_health_check.py#L115) |
| function | `_model_drift` | `()` | Model-drift: en provider der FØR havde modeller men nu har 0 (model udfaset/omdøbt — den | [src](../../../core/services/provider_health_check.py#L135) |
| function | `_spread_load_proactively` | `(reports, unreachable)` | Daemon-load-spredning (Jarvis-spec): sæt PROAKTIVT en kort cooldown på nede providers, så | [src](../../../core/services/provider_health_check.py#L170) |
| function | `observe_and_flag` | `()` | Kadence-entry (Jarvis-spec 2026-06-23): ping + model-drift + cheap-dry → observe + FLAG | [src](../../../core/services/provider_health_check.py#L211) |
| function | `build_provider_health_surface` | `()` | Read-only provider-helbreds-surface til Jarvis Mind / terminal: ÉT kald → ping + tør + | [src](../../../core/services/provider_health_check.py#L260) |
| function | `latest_health_snapshot` | `()` | Read most-recent stored snapshot. | [src](../../../core/services/provider_health_check.py#L283) |
| function | `health_section` | `()` | Awareness section listing currently unreachable providers. | [src](../../../core/services/provider_health_check.py#L295) |
| function | `_exec_run_health_check` | `(args)` | — | [src](../../../core/services/provider_health_check.py#L315) |
| function | `_exec_get_health_snapshot` | `(args)` | — | [src](../../../core/services/provider_health_check.py#L319) |

## `core/services/provider_retry_policy.py`
_Provider retry policy — exponential backoff for transient failures._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_transient` | `(exc)` | — | [src](../../../core/services/provider_retry_policy.py#L46) |
| function | `retry_with_backoff` | `(fn, *, max_retries=…, base_delay=…, max_delay=…, only_transient=…, label=…)` | Run fn() with exponential backoff. Re-raises last exception on failure. | [src](../../../core/services/provider_retry_policy.py#L53) |
| function | `_exec_test_retry` | `(args)` | Manual test handle — verify retry behaviour. Not for production use. | [src](../../../core/services/provider_retry_policy.py#L97) |

## `core/services/push_dispatcher.py`
_Beslutter HVORNAAR og HVEM der skal pushes. Bygger paa run_event_log-suppression._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fcm_send` | `(token, data)` | — | [src](../../../core/services/push_dispatcher.py#L12) |
| function | `_owner_of_run` | `(run_id)` | — | [src](../../../core/services/push_dispatcher.py#L17) |
| function | `_push_to_user` | `(user_id, data)` | — | [src](../../../core/services/push_dispatcher.py#L24) |
| function | `_route_or_blast` | `(user_id, data, kind)` | Flag ON → intelligent device-routing; OFF → gammel FCM-blast (bagudkompat). | [src](../../../core/services/push_dispatcher.py#L35) |
| function | `_last_assistant_preview` | `(session_id, *, width=…)` | Sidste assistant-beskeds tekst (trunkeret) til notifikations-preview. "" hvis ingen. | [src](../../../core/services/push_dispatcher.py#L48) |
| function | `_dispatch_run_done` | `(run_id)` | — | [src](../../../core/services/push_dispatcher.py#L66) |
| function | `on_run_done` | `(run_id)` | Kaldes fra detached_run finally. Planlaegger suppression-tjek efter grace. | [src](../../../core/services/push_dispatcher.py#L96) |
| function | `send_companion_push` | `(user_id, message, title=…)` | Proaktiv push til brugerens companion-enheder (mobil + desktop) via | [src](../../../core/services/push_dispatcher.py#L104) |
| function | `on_initiative` | `(user_id, text)` | — | [src](../../../core/services/push_dispatcher.py#L117) |
| function | `on_reminder` | `(user_id, text)` | — | [src](../../../core/services/push_dispatcher.py#L123) |

## `core/services/pushback.py`
_Pushback — three prompt-level mechanisms that give Jarvis a real voice_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_emit_pushback_telemetry` | `(section, *, triggered, reason=…, **fields)` | Log pushback section generation to eventbus for observability. | [src](../../../core/services/pushback.py#L34) |
| function | `_ambiguity_score` | `(message)` | Heuristic 0-1 ambiguity. Returns (score, reasons). | [src](../../../core/services/pushback.py#L67) |
| function | `_conflict_with_decisions` | `(message)` | Check if the request appears to contradict an active behavioral decision. | [src](../../../core/services/pushback.py#L113) |
| function | `doubt_signal_section` | `(user_message)` | Render doubt as a prompt section. None when doubt is low. | [src](../../../core/services/pushback.py#L146) |
| function | `disagreement_invite_section` | `()` | Always-on reminder that pushback is welcome. Static text. | [src](../../../core/services/pushback.py#L184) |
| function | `_affective_pressure` | `(snapshot)` | Map the emotional snapshot to the feeling most likely to drive pushback. | [src](../../../core/services/pushback.py#L217) |
| function | `_request_risk_evidence` | `(user_message)` | — | [src](../../../core/services/pushback.py#L244) |
| function | `affective_pushback_section` | `(user_message)` | Render feeling-driven pushback as bounded prompt guidance. | [src](../../../core/services/pushback.py#L257) |
| function | `_is_high_stakes` | `(user_message, reasoning_tier)` | — | [src](../../../core/services/pushback.py#L330) |
| function | `direction_confirm_section` | `(*, user_message, reasoning_tier)` | Inject a 'plan-first, confirm-before-tools' section for high-stakes | [src](../../../core/services/pushback.py#L337) |

## `core/services/quota_store.py`
_Kvote-regnskab pr. bruger/mode med daglig nulstilling (spec §21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today` | `()` | — | [src](../../../core/services/quota_store.py#L32) |
| function | `set_user_quota` | `(user_id, tier)` | Sæt en brugers eksplicitte tier (autoritativt i user_db). Owner kan give | [src](../../../core/services/quota_store.py#L36) |
| function | `get_tier` | `(user_id)` | Brugerens tier. user_db-tier (nyt autoritativt felt) vinder; ellers eksplicit | [src](../../../core/services/quota_store.py#L43) |
| function | `_limit_for` | `(kind, tier)` | — | [src](../../../core/services/quota_store.py#L72) |
| function | `_db_key` | `(user_id, kind)` | — | [src](../../../core/services/quota_store.py#L76) |
| function | `_get_used` | `(user_id, kind)` | — | [src](../../../core/services/quota_store.py#L80) |
| function | `check_quota` | `(user_id, kind)` | Status uden at forbruge. {allowed, tier, used, limit (None=ubegrænset), | [src](../../../core/services/quota_store.py#L89) |
| function | `consume_quota` | `(user_id, kind, amount=…)` | Forbrug `amount` af kvoten hvis muligt. Returnerer status (som check_quota) | [src](../../../core/services/quota_store.py#L106) |

## `core/services/r2_5_blocking_gate.py`
_R2.5 — conditional blocking gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_live_thresholds` | `()` | Settings-backed tærskler (config uden deploy, 2026-06-22); modul-konstanterne | [src](../../../core/services/r2_5_blocking_gate.py#L57) |
| function | `_heed_rate_24h` | `()` | — | [src](../../../core/services/r2_5_blocking_gate.py#L76) |
| function | `should_block_for_verification` | `(*, reasoning_tier)` | Decide whether to inject a 'stop and look back' block. | [src](../../../core/services/r2_5_blocking_gate.py#L88) |
| function | `r2_5_block_section` | `(reasoning_tier)` | Render the block as a high-priority awareness section, or None. | [src](../../../core/services/r2_5_blocking_gate.py#L218) |

## `core/services/read_before_write_guard.py`
_Read-before-write guard — prevents overwrite of existing files without prior read._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cache_key` | `(session_id, abs_path)` | — | [src](../../../core/services/read_before_write_guard.py#L56) |
| function | `record_read` | `(path, session_id=…)` | Record that a file has been read in this session. | [src](../../../core/services/read_before_write_guard.py#L60) |
| function | `_was_read` | `(abs_path, session_id)` | True if `abs_path` was read in this session within the TTL window. | [src](../../../core/services/read_before_write_guard.py#L78) |
| function | `is_protected` | `(path)` | True if the path's basename is in the protected set. | [src](../../../core/services/read_before_write_guard.py#L96) |
| function | `check_read_before_write` | `(path, session_id=…)` | Check whether write_file should be allowed for this path. | [src](../../../core/services/read_before_write_guard.py#L105) |
| function | `_normalize_path` | `(p, *, base=…)` | Best-effort resolve of a path token (may be ~/, relative, ./). | [src](../../../core/services/read_before_write_guard.py#L175) |
| function | `check_bash_command_safe` | `(command, *, session_id=…, cwd=…)` | Sniff a bash command for protected-file overwrites without prior read. | [src](../../../core/services/read_before_write_guard.py#L186) |
| function | `clear_session` | `(session_id=…)` | Clear all recent-read entries for a session in shared_cache. | [src](../../../core/services/read_before_write_guard.py#L288) |
| function | `get_session_reads` | `(session_id=…)` | Return the set of paths read in this session (for debugging). | [src](../../../core/services/read_before_write_guard.py#L297) |
| function | `build_read_before_write_guard_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/read_before_write_guard.py#L324) |
| function | `_emit_read_before_write_guard_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/read_before_write_guard.py#L336) |
| function | `_normalize_operator_path` | `(path)` | Light normalization for cross-OS path consistency. | [src](../../../core/services/read_before_write_guard.py#L365) |
| function | `_operator_cache_key` | `(session_id, norm_path)` | — | [src](../../../core/services/read_before_write_guard.py#L378) |
| function | `record_operator_read` | `(path, session_id=…)` | Note that the operator side has read this path. Best-effort. | [src](../../../core/services/read_before_write_guard.py#L382) |
| function | `_operator_was_read` | `(norm_path, session_id)` | — | [src](../../../core/services/read_before_write_guard.py#L398) |
| function | `check_operator_read_before_write` | `(path, session_id=…, file_exists=…)` | Block operator_write_file / operator_edit_file on existing files | [src](../../../core/services/read_before_write_guard.py#L412) |
| function | `_session_edits_key` | `(session_id)` | — | [src](../../../core/services/read_before_write_guard.py#L468) |
| function | `record_operator_edit` | `(path, session_id=…, kind=…)` | Record that the operator side mutated this file. kind is 'edit' or 'write'. | [src](../../../core/services/read_before_write_guard.py#L472) |
| function | `get_session_edit_summary` | `(session_id=…)` | Return the running tally for this session. Empty dict if nothing yet. | [src](../../../core/services/read_before_write_guard.py#L505) |

## `core/services/reasoning_classifier.py`
_Reasoning classifier — router that picks fast / reasoning / deep tier._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_score_patterns` | `(text, patterns)` | — | [src](../../../core/services/reasoning_classifier.py#L65) |
| function | `classify_reasoning_tier` | `(message, *, task_hint=…)` | Pick reasoning tier for a user message (or task description). | [src](../../../core/services/reasoning_classifier.py#L75) |
| function | `reasoning_tier_section` | `(message)` | Format tier verdict as a prompt-awareness section. None for fast tier | [src](../../../core/services/reasoning_classifier.py#L210) |
| function | `_exec_reasoning_classify` | `(args)` | — | [src](../../../core/services/reasoning_classifier.py#L227) |
| function | `build_reasoning_classifier_surface` | `()` | — | [src](../../../core/services/reasoning_classifier.py#L275) |
| function | `_emit_tier_event` | `(tier, score)` | — | [src](../../../core/services/reasoning_classifier.py#L284) |

## `core/services/reasoning_detectors.py`
_Reasoning detectors for the reasoning-interceptor._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_downgrade_cognitive` | `(v, *, gate)` | Re-stamp a gate's verdict for the reasoning stage: keep GREEN/YELLOW, but a COGNITIVE RED | [src](../../../core/services/reasoning_detectors.py#L16) |
| function | `fact_gate_on_reasoning` | `(reasoning_text, ctx)` | fact_gate re-applied to reasoning. A number/status claim with NO backing tool-call in this | [src](../../../core/services/reasoning_detectors.py#L26) |
| function | `decision_gate_on_reasoning` | `(reasoning_text, ctx)` | decision_gate (commit cluster) re-applied to reasoning. Grounding = the active-decisions | [src](../../../core/services/reasoning_detectors.py#L43) |
| function | `veto_on_reasoning` | `(reasoning_text, ctx)` | veto_gate (commit cluster) re-applied to reasoning. Grounding = the veto gate's own evidence. | [src](../../../core/services/reasoning_detectors.py#L55) |
| function | `verification_on_reasoning` | `(reasoning_text, ctx)` | proactivity/verification gate re-applied. Grounding = the run's verification state (the gate | [src](../../../core/services/reasoning_detectors.py#L67) |
| function | `cross_user_share_on_reasoning` | `(reasoning_text, ctx)` | privacy/cross_user_share gate re-applied to reasoning. SECURITY — keeps RED (a leak forming | [src](../../../core/services/reasoning_detectors.py#L78) |
| function | `standing_orders_on_reasoning` | `(reasoning_text, ctx)` | Flag when the reasoning enters a risk class an active standing order governs. Grounding = | [src](../../../core/services/reasoning_detectors.py#L92) |
| function | `_drift_signal` | `(ctx)` | INDEPENDENT drift signal 0..1 from the Central's OWN affect/valence nerves + an | [src](../../../core/services/reasoning_detectors.py#L112) |
| function | `drift_on_reasoning` | `(reasoning_text, ctx)` | Affective drift (overconfidence). Grounding = the Central's own affect nerves + claim streak | [src](../../../core/services/reasoning_detectors.py#L132) |
| function | `tone_on_reasoning` | `(reasoning_text, ctx)` | Epistemic tone — a guess stated as fact. ANCHORED (invariant 3): runs ONLY if a truth/drift | [src](../../../core/services/reasoning_detectors.py#L150) |

## `core/services/reasoning_escalation.py`
_Reasoning escalation — compose tier + gate signals into a council recommendation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_tier` | `(message)` | — | [src](../../../core/services/reasoning_escalation.py#L39) |
| function | `_safe_gate` | `()` | — | [src](../../../core/services/reasoning_escalation.py#L48) |
| function | `_recommend_path` | `(tier, failed, unverified, signals)` | Pick the escalation path that fits the situation. | [src](../../../core/services/reasoning_escalation.py#L63) |
| function | `evaluate_escalation` | `(message=…)` | Compose tier + gate into an escalation recommendation. | [src](../../../core/services/reasoning_escalation.py#L112) |
| function | `escalation_section` | `(message=…)` | Format escalation recommendation as a prompt-awareness section, or None. | [src](../../../core/services/reasoning_escalation.py#L168) |
| function | `_exec_recommend_escalation` | `(args)` | — | [src](../../../core/services/reasoning_escalation.py#L193) |
| function | `build_reasoning_escalation_surface` | `()` | — | [src](../../../core/services/reasoning_escalation.py#L223) |
| function | `_emit_escalation_event` | `(path, tier)` | — | [src](../../../core/services/reasoning_escalation.py#L232) |

## `core/services/reasoning_interceptor.py`
_Reasoning interceptor orchestrator. intercept_round() runs between a round's reasoning and the_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InterceptOutcome` | `` | — | [src](../../../core/services/reasoning_interceptor.py#L15) |
| function | `_is_active` | `(grade)` | Active only if the per-grade kill-switch is EXPLICITLY flipped ON. DEFAULT OFF (shadow) — | [src](../../../core/services/reasoning_interceptor.py#L23) |
| function | `should_hold_tool_call` | `(outcome)` | True only for an ACTIVE RED outcome — the seam then holds the pending tool-call (via the | [src](../../../core/services/reasoning_interceptor.py#L44) |
| function | `_run_detectors` | `(ctx)` | Run the tripped cluster-gate adapters + standing-orders; return the WORST Verdict (GREEN if | [src](../../../core/services/reasoning_interceptor.py#L50) |
| function | `_observe` | `(outcome, *, run_id, round_num)` | Egress-free metadata-only pulse to the Central (never the reasoning text). Self-safe. | [src](../../../core/services/reasoning_interceptor.py#L92) |
| function | `build_reasoning_interceptor_surface` | `()` | Central-CLI view: recent interceptor verdicts. Self-safe, read-only. Returns static shape | [src](../../../core/services/reasoning_interceptor.py#L105) |
| function | `intercept_round_async` | `(*, run_id, round_num, reasoning_text, tool_calls_this_run, ctx=…, budget_ms=…)` | Async wrapper (invariant 4 — async/keepalive): runs the sync intercept in a thread with a | [src](../../../core/services/reasoning_interceptor.py#L131) |
| function | `intercept_round` | `(*, run_id, round_num, reasoning_text, tool_calls_this_run, ctx=…)` | — | [src](../../../core/services/reasoning_interceptor.py#L152) |

## `core/services/reasoning_prefilter.py`
_Deterministic pre-filter (interceptor invariant 5): cheap regex/heuristics over reasoning text →_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `prefilter` | `(reasoning_text, *, ctx=…, other_user_ids=…)` | Return the risk classes present in `reasoning_text`. Self-safe (never raises). | [src](../../../core/services/reasoning_prefilter.py#L15) |

## `core/services/reasoning_store.py`
_Reasoning Store — Phase 1 of Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/reasoning_store.py#L32) |
| function | `_ensure_table` | `(conn)` | Idempotent table creation. | [src](../../../core/services/reasoning_store.py#L36) |
| function | `_cosine_similarity` | `(a, b)` | Cosine similarity between two equal-length vectors. | [src](../../../core/services/reasoning_store.py#L64) |
| function | `_parse_embedding` | `(raw)` | Safely parse embedding JSON, return empty list on failure. | [src](../../../core/services/reasoning_store.py#L76) |
| function | `capture_conclusion` | `(*, source, conclusion_text, context=…, confidence=…, embedding=…, source_record_id=…, metadata=…, emit_event=…, dedup_key=…)` | Store a reasoning conclusion and return its conclusion_id. | [src](../../../core/services/reasoning_store.py#L90) |
| function | `recall_reasoning` | `(*, query_text=…, query_embedding=…, source_filter=…, min_confidence=…, limit=…, days_back=…)` | Retrieve stored reasoning conclusions, ranked by relevance. | [src](../../../core/services/reasoning_store.py#L169) |
| function | `get_recent_conclusions` | `(*, source=…, limit=…, days_back=…)` | Quick access to recent conclusions, no embedding scoring. | [src](../../../core/services/reasoning_store.py#L269) |
| function | `is_enabled` | `()` | Check the killswitch setting. | [src](../../../core/services/reasoning_store.py#L283) |
| function | `set_enabled` | `(value)` | Set killswitch — toggle reasoning store on/off without restart. | [src](../../../core/services/reasoning_store.py#L289) |
| function | `compact_stale` | `(days=…, min_confidence=…)` | Delete stale low-confidence conclusions. Returns count removed. | [src](../../../core/services/reasoning_store.py#L295) |
| function | `compute_embedding` | `(text)` | Compute embedding vector for semantic search. | [src](../../../core/services/reasoning_store.py#L317) |

## `core/services/reboot_awareness_daemon.py`
_Reboot Awareness Daemon — proprioception: "I feel when I restart"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L35) |
| function | `_load` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L39) |
| function | `_save` | `(data)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L53) |
| function | `_update_last_seen` | `(pid)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L65) |
| function | `_graceful_shutdown_marker` | `()` | Called via signal handler. Writes a clean shutdown marker. | [src](../../../core/services/reboot_awareness_daemon.py#L72) |
| function | `_signal_handler` | `(signum, _frame)` | Write graceful-shutdown marker then re-raise to default handler. | [src](../../../core/services/reboot_awareness_daemon.py#L84) |
| function | `_install_signal_handlers` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L101) |
| function | `detect_reboot` | `()` | Compare previous last_seen to now; emit an event if this is a fresh boot. | [src](../../../core/services/reboot_awareness_daemon.py#L112) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook: first call triggers detect_reboot(), thereafter | [src](../../../core/services/reboot_awareness_daemon.py#L193) |
| function | `get_last_boot_event` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L202) |
| function | `build_reboot_awareness_surface` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L206) |
| function | `_surface_summary` | `(event, uptime)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L229) |
| function | `build_reboot_awareness_prompt_section` | `()` | Announce recent reboot once; stays silent after first ~10 min. | [src](../../../core/services/reboot_awareness_daemon.py#L252) |

