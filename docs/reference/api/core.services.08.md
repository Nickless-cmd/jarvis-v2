# `core.services.08` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/current_pull.py`
_Current pull — Jarvis' weekly self-set desire field._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_current_pull_daemon` | `()` | Weekly daemon tick. Generates a new pull if none active, expired, or stale. | [src](../../../core/services/current_pull.py#L44) |
| function | `_collect_appetite_texts` | `(*, days_back)` | Pull active appetite labels for landscape embedding. | [src](../../../core/services/current_pull.py#L142) |
| function | `_collect_chronicle_texts` | `(*, days_back)` | Pull chronicle narratives from the last `days_back` days. | [src](../../../core/services/current_pull.py#L163) |
| function | `_collect_journal_texts` | `(*, days_back)` | Pull journal entry bodies from the last `days_back` days. | [src](../../../core/services/current_pull.py#L191) |
| function | `_compute_landscape_embedding` | `()` | Build a mean-pooled embedding from the last 3 days of desire signals. | [src](../../../core/services/current_pull.py#L236) |
| function | `_pull_is_stale` | `(pull_text)` | Return (is_stale, cos_score). | [src](../../../core/services/current_pull.py#L264) |
| function | `_staleness_check_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L291) |
| function | `_should_run_staleness_check` | `(state, *, interval_hours)` | Throttle: only run the embedding check every `interval_hours`. | [src](../../../core/services/current_pull.py#L298) |
| function | `_archive_refresh_event` | `(*, state, refreshed_at, reason, stale_score, previous_pull)` | Append a refresh event to state['refresh_history'], capped at 5 (FIFO). | [src](../../../core/services/current_pull.py#L312) |
| function | `get_current_pull_for_prompt` | `()` | Return prompt fragment for visible chat injection — or empty string. | [src](../../../core/services/current_pull.py#L333) |
| function | `build_current_pull_surface` | `()` | — | [src](../../../core/services/current_pull.py#L360) |
| function | `_generate_pull` | `()` | Ask Jarvis what pulls at him right now. Returns one Danish sentence. | [src](../../../core/services/current_pull.py#L386) |
| function | `_sanitize` | `(raw)` | — | [src](../../../core/services/current_pull.py#L431) |
| function | `_expire_if_stale` | `()` | — | [src](../../../core/services/current_pull.py#L438) |
| function | `_load_state` | `()` | — | [src](../../../core/services/current_pull.py#L459) |
| function | `_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L464) |

## `core/services/daemon_health.py`
_Daemon-helbred (Fase 1) — gør de standalone daemon-tråde + silent eventbus-listeners_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `note_error` | `(daemon, error, **data)` | En daemon/listener fejlede. → observe (cluster=system, nerve=daemon_health, ok=False). | [src](../../../core/services/daemon_health.py#L17) |
| function | `note_tick` | `(daemon, *, ok=…, **data)` | En daemon kørte en cyklus. Valgfri helbreds-puls (brug sparsomt — fejl er hovedsignalet). | [src](../../../core/services/daemon_health.py#L30) |
| function | `daemon_health_summary` | `(*, window=…)` | Read-only: hvilke daemons har fejlet i seneste trace (til MC/debug). Self-safe. | [src](../../../core/services/daemon_health.py#L42) |

## `core/services/daemon_llm.py`
_Shared LLM call for daemons — cheap lane first, heartbeat model fallback._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_note_call` | `(daemon_name, hit)` | Registrér ét daemon_llm-kald + om det ramte cachen → central_timeseries. Self-safe. | [src](../../../core/services/daemon_llm.py#L25) |
| function | `daemon_llm_cache_snapshot` | `()` | Read-only: pr. daemon kald + cache-hits + hit-rate. Lav hit-rate + højt kald = | [src](../../../core/services/daemon_llm.py#L58) |
| function | `_get_cache_ttl` | `(daemon_name)` | Return TTL in seconds for a daemon. 0 means no caching. | [src](../../../core/services/daemon_llm.py#L99) |
| function | `_check_cache` | `(cache_key)` | Return cached response if present and not expired, else None. | [src](../../../core/services/daemon_llm.py#L104) |
| function | `_store_cache` | `(cache_key, text, daemon_name)` | Store response in cache with daemon-specific TTL. | [src](../../../core/services/daemon_llm.py#L116) |
| function | `daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call LLM for daemon output. Tries cache first, then cheap lane (Groq), | [src](../../../core/services/daemon_llm.py#L129) |
| function | `quality_daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path for QUALITY-CRITICAL daemons (self-review, decision-review, | [src](../../../core/services/daemon_llm.py#L149) |
| function | `daemon_public_safe_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path reserved for PUBLIC-SAFE prompts. | [src](../../../core/services/daemon_llm.py#L259) |
| function | `_daemon_llm_call_impl` | `(prompt, *, max_len, fallback, daemon_name, public_safe)` | — | [src](../../../core/services/daemon_llm.py#L281) |

## `core/services/daemon_manager.py`
_Daemon Manager — registry, lifecycle control, and state persistence for all daemons._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_file` | `()` | — | [src](../../../core/services/daemon_manager.py#L20) |
| function | `get_daemon_names` | `()` | — | [src](../../../core/services/daemon_manager.py#L449) |
| function | `_load_state` | `()` | — | [src](../../../core/services/daemon_manager.py#L453) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/daemon_manager.py#L463) |
| function | `_get_daemon_state` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L469) |
| function | `_set_daemon_state` | `(name, updates)` | — | [src](../../../core/services/daemon_manager.py#L473) |
| function | `_require_known` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L481) |
| function | `is_enabled` | `(name)` | Return True if the named daemon should run. Unknown daemons return True (safe default). | [src](../../../core/services/daemon_manager.py#L487) |
| function | `set_daemon_enabled` | `(name, enabled)` | — | [src](../../../core/services/daemon_manager.py#L496) |
| function | `get_effective_cadence` | `(name)` | Return interval in minutes: override if set, else default. | [src](../../../core/services/daemon_manager.py#L501) |
| function | `record_daemon_tick` | `(name, result)` | Record last_run_at and a summary of the tick result. Called by heartbeat_runtime. | [src](../../../core/services/daemon_manager.py#L510) |
| function | `_hours_since` | `(iso)` | — | [src](../../../core/services/daemon_manager.py#L519) |
| function | `get_all_daemon_states` | `()` | Return status for all registered daemons. | [src](../../../core/services/daemon_manager.py#L531) |
| function | `control_daemon` | `(name, action, *, interval_minutes=…)` | Control a daemon. Actions: enable, disable, restart, set_interval. | [src](../../../core/services/daemon_manager.py#L554) |
| function | `_restart_daemon` | `(name)` | Clear the module-level state variable so the daemon fires on next heartbeat tick. | [src](../../../core/services/daemon_manager.py#L585) |

## `core/services/daemon_memory_safeguard.py`
_Daemon memory safeguard — post-hoc check that Jarvis saved what mattered._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_memory_safeguard_surface` | `()` | Mission Control surface for the memory safeguard daemon. | [src](../../../core/services/daemon_memory_safeguard.py#L41) |
| function | `run` | `(**kwargs)` | Check last assistant turn for missed saves. Called by heartbeat. | [src](../../../core/services/daemon_memory_safeguard.py#L101) |

## `core/services/daily_journal.py`
_Daily journal synthesizer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../core/services/daily_journal.py#L49) |
| function | `_journal_path_for` | `(day)` | — | [src](../../../core/services/daily_journal.py#L56) |
| function | `journal_exists_for` | `(day)` | Findes der allerede en journal for denne dato? | [src](../../../core/services/daily_journal.py#L61) |
| function | `_fetch_chat_pairs_for_day` | `(day, limit=…)` | Hent user/assistant beskeder fra visible-chat sessions for denne dag. | [src](../../../core/services/daily_journal.py#L66) |
| function | `_fetch_brain_carries_for_day` | `(day, limit=…)` | Hent private_brain_records carry-snapshots fra dagen. | [src](../../../core/services/daily_journal.py#L97) |
| function | `_render_chat_excerpt` | `(pairs)` | — | [src](../../../core/services/daily_journal.py#L158) |
| function | `_render_brain_excerpt` | `(carries)` | — | [src](../../../core/services/daily_journal.py#L168) |
| function | `synthesize_daily_journal` | `(day=…, *, force=…)` | Generér og skriv dagens journal. | [src](../../../core/services/daily_journal.py#L180) |
| function | `_should_synthesize_now` | `(now=…)` | Returnér True hvis vi er i sengetids-vinduet og dagens journal mangler. | [src](../../../core/services/daily_journal.py#L250) |
| function | `_daemon_loop` | `()` | Wakes hver time, syntesizer dagens journal hvis vi er i vinduet. | [src](../../../core/services/daily_journal.py#L260) |
| function | `start_daily_journal_daemon` | `()` | Start daemon. Idempotent. | [src](../../../core/services/daily_journal.py#L279) |
| function | `stop_daily_journal_daemon` | `()` | — | [src](../../../core/services/daily_journal.py#L296) |

## `core/services/data_erasure.py`
_GDPR Art. 17 (ret til at blive glemt) — orkestrering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_id_tables` | `(conn)` | Tabeller der HAR en user_id-kolonne (minus beskyttede). Eksplicit opdaget, | [src](../../../core/services/data_erasure.py#L23) |
| function | `_sweep_user_tables` | `(user_id, *, connect=…)` | — | [src](../../../core/services/data_erasure.py#L38) |
| function | `_wipe_workspace` | `(user_id)` | Slet brugerens workspace-mappe — med STRAM sti-sikkerhed (kun en undermappe | [src](../../../core/services/data_erasure.py#L49) |
| function | `erase_user` | `(user_id, *, mode=…, actor=…, connect=…)` | Slet en brugers data. mode='soft' (reversibel) | 'hard' (permanent). | [src](../../../core/services/data_erasure.py#L63) |

## `core/services/day_shape_memory.py`
_Day Shape Memory — sensory depth over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/day_shape_memory.py#L31) |
| function | `_load` | `()` | — | [src](../../../core/services/day_shape_memory.py#L36) |
| function | `_save` | `(data)` | — | [src](../../../core/services/day_shape_memory.py#L54) |
| function | `_today_iso` | `()` | — | [src](../../../core/services/day_shape_memory.py#L66) |
| function | `_empty_day` | `(date_iso)` | — | [src](../../../core/services/day_shape_memory.py#L70) |
| function | `capture_sample` | `()` | Add one sample to today's accumulating shape. | [src](../../../core/services/day_shape_memory.py#L82) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — capture one shape sample per tick. | [src](../../../core/services/day_shape_memory.py#L165) |
| function | `_finalize_day` | `(day)` | Collapse raw sample arrays into summary stats for storage. | [src](../../../core/services/day_shape_memory.py#L170) |
| function | `_compute_today_shape` | `()` | — | [src](../../../core/services/day_shape_memory.py#L188) |
| function | `_median_historical_shape` | `(days)` | — | [src](../../../core/services/day_shape_memory.py#L196) |
| function | `detect_today_anomaly` | `()` | Compare today's running shape to recent-days median. | [src](../../../core/services/day_shape_memory.py#L215) |
| function | `build_day_shape_surface` | `()` | — | [src](../../../core/services/day_shape_memory.py#L261) |
| function | `_surface_summary` | `(current, history, anomaly)` | — | [src](../../../core/services/day_shape_memory.py#L277) |
| function | `build_day_shape_prompt_section` | `()` | Surfaces only when today differs noticeably from baseline. | [src](../../../core/services/day_shape_memory.py#L292) |

## `core/services/db_sentinel.py`
_DB-cluster — observabilitet + flag for jarvis.db's helbred. IKKE en blokerende gate og_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_list_tables` | `()` | — | [src](../../../core/services/db_sentinel.py#L27) |
| function | `census` | `()` | Row-count pr. tabel. Best-effort; en fejlende tabel udelades. | [src](../../../core/services/db_sentinel.py#L40) |
| function | `dead_table_candidates` | `()` | Tabeller med 0 rækker = KANDIDATER til oprydning. KUN til menneskelig review — | [src](../../../core/services/db_sentinel.py#L57) |
| function | `_load_prev` | `()` | — | [src](../../../core/services/db_sentinel.py#L64) |
| function | `_save` | `(c)` | — | [src](../../../core/services/db_sentinel.py#L73) |
| function | `scan` | `()` | Census + vækst-delta vs forrige snapshot + flag egregious vækst. Returnér rapport. | [src](../../../core/services/db_sentinel.py#L81) |
| function | `observe` | `()` | Kør scan + central.observe(summary) + flag egregious vækst som incident (review). | [src](../../../core/services/db_sentinel.py#L105) |
| function | `build_db_health_surface` | `()` | MC-surface — read-only meta-projektion af DB-helbred + kandidat-død-liste til review. | [src](../../../core/services/db_sentinel.py#L131) |

## `core/services/decision_adherence_gate.py`
_Gate 1: Decision-adherence gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decision_adherence_section` | `()` | Build an escalation prompt section based on current decision adherence. | [src](../../../core/services/decision_adherence_gate.py#L27) |

## `core/services/decision_enforcement.py`
_Decision enforcement — close the loop between commitment and behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `enforcement_section` | `()` | High-priority awareness: lists active decisions as obligations + asks | [src](../../../core/services/decision_enforcement.py#L38) |
| function | `_build_breach_prompt` | `(assistant_text, decisions)` | — | [src](../../../core/services/decision_enforcement.py#L106) |
| function | `_parse_breaches` | `(text)` | — | [src](../../../core/services/decision_enforcement.py#L125) |
| function | `detect_breach_in_output` | `(assistant_text)` | Return list of detected breaches. Empty if none. LLM-led. | [src](../../../core/services/decision_enforcement.py#L145) |
| function | `_poll_loop` | `()` | — | [src](../../../core/services/decision_enforcement.py#L226) |
| function | `subscribe` | `()` | — | [src](../../../core/services/decision_enforcement.py#L266) |

## `core/services/decision_gate.py`
_Decision gate — pre-execution decision conflict detection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_decision_gate` | `(tool_name, tool_args=…, user_message=…)` | Check if a tool call conflicts with active decisions. | [src](../../../core/services/decision_gate.py#L27) |
| function | `evaluate_decision_conflict` | `(tool_name, tool_args=…, user_message=…)` | Graderet decision-conflict. Returnerer (severity, reason): | [src](../../../core/services/decision_gate.py#L115) |
| function | `_build_context` | `(tool_name, tool_args, user_message)` | Build a context string for conflict detection. | [src](../../../core/services/decision_gate.py#L182) |
| function | `_detect_conflict` | `(directive, context, decision)` | Detect if the context conflicts with a decision directive. | [src](../../../core/services/decision_gate.py#L199) |

## `core/services/decision_ghosts.py`
_Decision Ghosts — paths not taken AND paths confirmed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_rejected_path` | `(decision, reason, alternative)` | Record a path that was rejected and may carry regret potential. | [src](../../../core/services/decision_ghosts.py#L21) |
| function | `record_confirmed_path` | `(decision, outcome, key_factor=…)` | Record a decision that was kept and proved successful. | [src](../../../core/services/decision_ghosts.py#L35) |
| function | `record_reaffirmed_decision` | `(decision_id, title, verdict)` | Record that a decision was reviewed and kept. | [src](../../../core/services/decision_ghosts.py#L53) |
| function | `describe_ghost_decision` | `()` | Return the most salient regret-ghost. | [src](../../../core/services/decision_ghosts.py#L67) |
| function | `describe_success_echo` | `()` | Return the most salient success-echo, or empty string. | [src](../../../core/services/decision_ghosts.py#L75) |
| function | `format_decision_ghost_for_prompt` | `()` | Format the regret ghost for prompt injection (legacy). | [src](../../../core/services/decision_ghosts.py#L84) |
| function | `format_decision_echo_for_prompt` | `()` | Format the success echo for prompt injection. | [src](../../../core/services/decision_ghosts.py#L92) |
| function | `reset_decision_ghosts` | `()` | Reset both rejected and confirmed paths. | [src](../../../core/services/decision_ghosts.py#L104) |
| function | `build_decision_ghosts_surface` | `()` | Build observable surface for Mission Control. | [src](../../../core/services/decision_ghosts.py#L111) |

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
| function | `_persist_appetites` | `()` | — | [src](../../../core/services/desire_daemon.py#L61) |
| function | `tick_desire_daemon` | `(signals)` | Update appetites based on current signals. | [src](../../../core/services/desire_daemon.py#L69) |
| function | `get_active_appetites` | `()` | Return active appetites sorted by intensity descending. | [src](../../../core/services/desire_daemon.py#L114) |
| function | `build_desire_surface` | `()` | — | [src](../../../core/services/desire_daemon.py#L119) |
| function | `_apply_decay` | `(now)` | — | [src](../../../core/services/desire_daemon.py#L133) |
| function | `_prune_expired` | `()` | — | [src](../../../core/services/desire_daemon.py#L143) |
| function | `_find_appetite_by_type` | `(appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L149) |
| function | `_spawn_appetite` | `(label, appetite_type, now)` | — | [src](../../../core/services/desire_daemon.py#L156) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/desire_daemon.py#L192) |
| function | `_build_raw_appetite_label` | `(spawning_type)` | Byg label udelukkende fra rå intensiteter — ingen LLM. | [src](../../../core/services/desire_daemon.py#L206) |
| function | `_generate_appetite_label` | `(signal_text, appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L224) |

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

