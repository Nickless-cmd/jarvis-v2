# `core.services.19` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_store_key` | `(scope)` | Durable KV key for ``scope``. None/empty → the global key, unchanged. | [src](../../../core/services/signal_baseline.py#L47) |
| function | `_load` | `(scope=…)` | Read the whole baseline dict for ``scope``. Fail-closed to {}. | [src](../../../core/services/signal_baseline.py#L55) |
| function | `_save` | `(baselines, scope=…)` | — | [src](../../../core/services/signal_baseline.py#L74) |
| function | `get_baseline` | `(signal, scope=…)` | Last recorded value for ``signal`` in ``scope``; None if never recorded. | [src](../../../core/services/signal_baseline.py#L84) |
| function | `set_baseline` | `(signal, value, scope=…)` | Persist ``value`` durably as the new baseline for ``signal`` in ``scope``. | [src](../../../core/services/signal_baseline.py#L95) |
| function | `is_cold_start` | `(min_signals=…, scope=…)` | True until ``min_signals`` distinct baselines exist *within* ``scope``. | [src](../../../core/services/signal_baseline.py#L115) |
| function | `clear_all` | `(scope=…)` | Drop all baselines in ``scope`` (test helper). Self-safe. | [src](../../../core/services/signal_baseline.py#L134) |

## `core/services/signal_decay_daemon.py`
_Signal decay daemon — archive and delete stale signals across all signal tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_signal_decay_daemon` | `()` | Run signal decay if cadence elapsed. Returns stats dict. | [src](../../../core/services/signal_decay_daemon.py#L35) |
| function | `get_signal_decay_stats` | `()` | — | [src](../../../core/services/signal_decay_daemon.py#L91) |
| function | `build_signal_decay_surface` | `()` | — | [src](../../../core/services/signal_decay_daemon.py#L98) |

## `core/services/signal_delta_trigger.py`
_Signal-delta trigger (C2) — pure, NON-LLM event-driven dispatch decision._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_scoped_key` | `(base, scope)` | Namespace a durable key by ``scope``. None → the global key, unchanged. | [src](../../../core/services/signal_delta_trigger.py#L43) |
| function | `_db` | `()` | Lazy import so this module is importable/pure without a live DB, and so | [src](../../../core/services/signal_delta_trigger.py#L57) |
| function | `_baseline` | `()` | Lazy import of C1's baseline module (built in parallel). | [src](../../../core/services/signal_delta_trigger.py#L65) |
| function | `_bl_is_cold_start` | `(baseline, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L76) |
| function | `_bl_get` | `(baseline, name, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L82) |
| function | `_bl_set` | `(baseline, name, val, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L88) |
| function | `_cfg_float` | `(db, name, default)` | — | [src](../../../core/services/signal_delta_trigger.py#L95) |
| function | `_load_float` | `(db, key, default)` | — | [src](../../../core/services/signal_delta_trigger.py#L102) |
| function | `_store_float` | `(db, key, value)` | — | [src](../../../core/services/signal_delta_trigger.py#L109) |
| function | `_load_hot` | `(db, key=…)` | — | [src](../../../core/services/signal_delta_trigger.py#L116) |
| function | `_store_hot` | `(db, hot, key=…)` | — | [src](../../../core/services/signal_delta_trigger.py#L126) |
| function | `_reason` | `(crossed, movements, theta_abs)` | — | [src](../../../core/services/signal_delta_trigger.py#L133) |
| function | `evaluate` | `(signals, scope=…)` | Decide whether a real change warrants a dispatch. | [src](../../../core/services/signal_delta_trigger.py#L141) |

## `core/services/signal_network_visualizer.py`
_Signal Network Visualizer — Jarvis' self-model as a living network._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_current_network_state` | `()` | Get current network state with nodes and edges. | [src](../../../core/services/signal_network_visualizer.py#L36) |
| function | `describe_inner_network` | `()` | Get a description of the inner network. | [src](../../../core/services/signal_network_visualizer.py#L113) |
| function | `get_signal_strengths` | `()` | Get signal strengths for each signal type. | [src](../../../core/services/signal_network_visualizer.py#L132) |
| function | `format_network_for_prompt` | `()` | Format network state for prompt injection. | [src](../../../core/services/signal_network_visualizer.py#L149) |
| function | `build_signal_network_visualizer_surface` | `()` | Build MC surface for signal network visualizer. | [src](../../../core/services/signal_network_visualizer.py#L157) |
| function | `_emit_signal_network_visualizer_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/signal_network_visualizer.py#L175) |

## `core/services/signal_noise_guard.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_signal_text` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L110) |
| function | `strip_signal_wrappers` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L114) |
| function | `is_noisy_signal_text` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L140) |
| function | `looks_like_substantive_runtime_topic` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L157) |
| function | `stable_signal_slug` | `(text, *, fallback=…)` | — | [src](../../../core/services/signal_noise_guard.py#L172) |
| function | `build_bounded_hypothesis_text` | `(topic)` | — | [src](../../../core/services/signal_noise_guard.py#L185) |

## `core/services/signal_pressure_accumulator.py`
_Signal Pressure Accumulator — generativ autonomi: fra signal til presning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PressureVector` | `` | En akkumuleret presningsvektor — retning + styrke over tid. | [src](../../../core/services/signal_pressure_accumulator.py#L68) |
| function | `_make_id` | `(direction, topic)` | Stable key for a pressure vector based on direction+topic. | [src](../../../core/services/signal_pressure_accumulator.py#L91) |
| function | `ingest_signal` | `(signal_family, signal_data)` | Ingest a single signal into the pressure accumulator. | [src](../../../core/services/signal_pressure_accumulator.py#L100) |
| function | `decay_all` | `()` | Apply decay to all pressure vectors. Called once per tick. | [src](../../../core/services/signal_pressure_accumulator.py#L161) |
| function | `get_all_pressures` | `()` | Return all active pressure vectors, sorted by accumulated (strongest first). | [src](../../../core/services/signal_pressure_accumulator.py#L187) |
| function | `get_pressure` | `(direction, topic)` | Get a specific pressure vector. | [src](../../../core/services/signal_pressure_accumulator.py#L192) |
| function | `get_dominant_pressures` | `(min_accumulated=…)` | Return pressures above a minimum threshold — these are the ones that matter. | [src](../../../core/services/signal_pressure_accumulator.py#L197) |
| function | `snapshot` | `()` | Return a serializable snapshot of current pressure state. | [src](../../../core/services/signal_pressure_accumulator.py#L202) |
| function | `run_pressure_accumulator_tick` | `()` | Run one tick of the pressure accumulator. | [src](../../../core/services/signal_pressure_accumulator.py#L219) |

## `core/services/signal_surface_gc.py`
_Garbage collector for runtime signal-surface trackers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_force_archive` | `(*, items, id_field, update_fn, label)` | — | [src](../../../core/services/signal_surface_gc.py#L33) |
| function | `collect` | `()` | Run a full GC pass across the three signal-surface trackers. | [src](../../../core/services/signal_surface_gc.py#L75) |

## `core/services/signal_surface_router.py`
_Signal Surface Router — maps surface names to build functions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_router` | `()` | Build name → function mapping. Local imports stay lazy. | [src](../../../core/services/signal_surface_router.py#L11) |
| function | `_get_router` | `()` | — | [src](../../../core/services/signal_surface_router.py#L267) |
| function | `get_surface_names` | `()` | — | [src](../../../core/services/signal_surface_router.py#L274) |
| function | `resolve_surface` | `(name)` | — | [src](../../../core/services/signal_surface_router.py#L278) |
| function | `read_surface` | `(name)` | Read a named surface. Returns {"error": ..., "valid": [...]} for unknown names. | [src](../../../core/services/signal_surface_router.py#L282) |
| function | `list_all_surfaces` | `()` | Call all registered surfaces. Per-surface exceptions caught and returned as errors. | [src](../../../core/services/signal_surface_router.py#L294) |

## `core/services/silence_detector.py`
_Silence Detector — what is the user NOT saying?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_silence_signals` | `(*, recent_topics, expected_topics, conversation_length=…, user_corrections=…)` | Detect what's missing from the conversation. | [src](../../../core/services/silence_detector.py#L17) |
| function | `build_silence_surface` | `()` | — | [src](../../../core/services/silence_detector.py#L62) |

## `core/services/silence_listener.py`
_Silence Listener — experience of empty space._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `experience_silence` | `(duration_seconds)` | — | [src](../../../core/services/silence_listener.py#L11) |
| function | `describe_silence` | `()` | — | [src](../../../core/services/silence_listener.py#L24) |
| function | `format_silence_for_prompt` | `()` | — | [src](../../../core/services/silence_listener.py#L31) |
| function | `reset_silence_listener` | `()` | — | [src](../../../core/services/silence_listener.py#L38) |
| function | `build_silence_listener_surface` | `()` | — | [src](../../../core/services/silence_listener.py#L43) |

## `core/services/silence_patterns.py`
_Silence Patterns — hvad brugeren IKKE siger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SilenceSignal` | `` | — | [src](../../../core/services/silence_patterns.py#L27) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/silence_patterns.py#L35) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/silence_patterns.py#L39) |
| function | `_topic_key` | `(text)` | — | [src](../../../core/services/silence_patterns.py#L52) |
| function | `_load_recent_user_messages` | `(lookback_days)` | Load recent user messages from chat_messages table. | [src](../../../core/services/silence_patterns.py#L59) |
| function | `_load_recent_events` | `(lookback_days)` | Pull recent events from event_bus — filtered for execution + tool signals. | [src](../../../core/services/silence_patterns.py#L81) |
| function | `_load_open_loop_topics` | `(limit=…)` | Pull open loop titles/summaries for avoidance detection. | [src](../../../core/services/silence_patterns.py#L97) |
| function | `detect_silence_patterns` | `(*, lookback_days=…)` | Detect silence signals from chat history + event stream. | [src](../../../core/services/silence_patterns.py#L119) |
| function | `render_soft_question` | `(signal)` | Generate a natural Danish follow-up question for a silence signal. | [src](../../../core/services/silence_patterns.py#L253) |
| function | `build_silence_patterns_surface` | `()` | MC surface for silence patterns. | [src](../../../core/services/silence_patterns.py#L277) |

## `core/services/simple_tool_executor.py`
_Native tool_calls executor (extracted from visible_runs.py, Boy-Scout 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_prepare_call` | `(tc, *, force, run_id, session_id, user_message, controller, round_seen)` | Single-thread prep for one call: parse/stamp args, signature, dedup, cache, | [src](../../../core/services/simple_tool_executor.py#L23) |
| function | `_finalize_call` | `(token, raw_result, *, controller, exec_fmt)` | Single-thread finalize for one executed call: soft-warn wrap, mark-seen on | [src](../../../core/services/simple_tool_executor.py#L104) |
| function | `_execute_simple_tool_calls` | `(tool_calls, *, force=…, run_id=…, session_id=…, user_message=…)` | Execute native tool_calls directly via simple_tools. Returns results. | [src](../../../core/services/simple_tool_executor.py#L126) |

## `core/services/skill_autosurface.py`
_Owner-approved allowlist governing jarvis-code skill auto-surfacing (Fase 3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_store` | `()` | — | [src](../../../core/services/skill_autosurface.py#L30) |
| function | `_write_store` | `(data)` | — | [src](../../../core/services/skill_autosurface.py#L46) |
| function | `_emit_governance_event` | `(kind, payload=…)` | Self-safe eventbus emission — observability must never break approval flow. | [src](../../../core/services/skill_autosurface.py#L54) |
| function | `list_approved` | `()` | Owner-approved skill names eligible for auto-surfacing. Empty on a fresh/corrupt store. | [src](../../../core/services/skill_autosurface.py#L63) |
| function | `approve_skill` | `(name, *, role)` | Owner-only. Validates against installed skills (skill_engine.skill_exists). | [src](../../../core/services/skill_autosurface.py#L68) |
| function | `revoke_skill` | `(name, *, role)` | Owner-only. Removes `name` from the allowlist if present. | [src](../../../core/services/skill_autosurface.py#L91) |
| function | `filter_to_approved` | `(names)` | Narrow `names` to the owner-approved allowlist, gated by the master flag. | [src](../../../core/services/skill_autosurface.py#L106) |

## `core/services/skill_contract_registry.py`
_Skill Contract Registry — formal contracts for capabilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SkillSpec` | `` | Immutable skill identity. | [src](../../../core/services/skill_contract_registry.py#L23) |
| class | `SkillPermissionSpec` | `` | Required scopes for a skill to run. | [src](../../../core/services/skill_contract_registry.py#L32) |
| class | `SkillManifest` | `` | Bundle of spec + permissions + schemas. | [src](../../../core/services/skill_contract_registry.py#L40) |
| function | `register_skill` | `(manifest)` | Register a skill manifest. Overwrites prior entry with same name. | [src](../../../core/services/skill_contract_registry.py#L54) |
| function | `get_manifest` | `(name)` | — | [src](../../../core/services/skill_contract_registry.py#L59) |
| function | `list_manifests` | `()` | — | [src](../../../core/services/skill_contract_registry.py#L63) |
| function | `check_permissions` | `(name, granted_scopes)` | Evaluate whether granted scopes satisfy a skill's required scopes. | [src](../../../core/services/skill_contract_registry.py#L67) |
| function | `_auto_register_known_skills` | `()` | Seed registry with contracts for well-known built-in capabilities. | [src](../../../core/services/skill_contract_registry.py#L93) |
| function | `build_skill_contract_registry_surface` | `()` | Mission Control surface. | [src](../../../core/services/skill_contract_registry.py#L194) |
| function | `_emit_skill_contract_registry_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/skill_contract_registry.py#L226) |

## `core/services/skill_engine.py`
_Skill Engine — SKILL.md loader for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Skill` | `` | A loaded skill from disk. | [src](../../../core/services/skill_engine.py#L48) |
| function | `_parse_skill_md` | `(path)` | Parse a SKILL.md file and return a Skill dataclass. | [src](../../../core/services/skill_engine.py#L71) |
| function | `_scan_skills` | `()` | Scan SKILLS_ROOT for all skills (mappe med SKILL.md). | [src](../../../core/services/skill_engine.py#L174) |
| function | `reload_skills` | `()` | Force-reload all skills from disk. Returns summary. | [src](../../../core/services/skill_engine.py#L194) |
| function | `get_skill` | `(name)` | Get a single skill by name. Lazy-loads if not cached. | [src](../../../core/services/skill_engine.py#L213) |
| function | `list_skills` | `(tag=…)` | List all skills, optionally filtered by tag. | [src](../../../core/services/skill_engine.py#L228) |
| function | `skill_exists` | `(name)` | Check if a skill exists on disk. | [src](../../../core/services/skill_engine.py#L254) |
| function | `_collect_registered_tool_names` | `()` | Return the set of registered tool names (normalized form). | [src](../../../core/services/skill_engine.py#L259) |
| function | `_skill_quality_nudges` | `(name, description, instructions, use_when=…, tags=…)` | Return non-blocking quality nudges for installable skill proposals. | [src](../../../core/services/skill_engine.py#L291) |
| function | `validate_skill_proposal` | `(name, description, instructions, use_when=…, tags=…)` | Validate that a proposed skill would be installable by create_skill(). | [src](../../../core/services/skill_engine.py#L362) |
| function | `create_skill` | `(name, description, instructions, use_when=…, tags=…, readonly=…)` | Create a new skill directory with SKILL.md on disk. | [src](../../../core/services/skill_engine.py#L443) |
| function | `delete_skill` | `(name, *, force=…)` | Delete a skill directory from disk. | [src](../../../core/services/skill_engine.py#L523) |
| function | `get_skill_instructions` | `(name)` | Get the full instructions + context for a skill (for prompt injection). | [src](../../../core/services/skill_engine.py#L554) |
| function | `search_skills` | `(query)` | Simple keyword search across skill names, descriptions, and instructions. | [src](../../../core/services/skill_engine.py#L593) |
| function | `build_skill_engine_surface` | `()` | Mission Control surface. | [src](../../../core/services/skill_engine.py#L616) |
| function | `_ensure_audit_table` | `()` | Idempotent: ensure skill_audit_log table exists. | [src](../../../core/services/skill_engine.py#L640) |
| function | `_build_skill_snapshot` | `(name)` | Build a portable snapshot dict for a skill. | [src](../../../core/services/skill_engine.py#L668) |
| function | `_record_audit_entry` | `(skill_name, action, *, diff_summary=…, reason=…, snapshot=…)` | Record a skill mutation in the audit log. Never raises. | [src](../../../core/services/skill_engine.py#L687) |
| function | `get_skill_history` | `(name, limit=…)` | Return audit trail for a single skill, newest first. | [src](../../../core/services/skill_engine.py#L731) |
| function | `list_recent_skill_changes` | `(limit=…)` | Return most recent skill mutations across all skills. | [src](../../../core/services/skill_engine.py#L768) |
| function | `update_skill` | `(name, *, description=…, instructions=…, use_when=…, tags=…, reason=…)` | Update an existing skill's metadata and/or instructions. Logs audit. | [src](../../../core/services/skill_engine.py#L794) |
| function | `_emit_skill_engine_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/skill_engine.py#L886) |
| function | `record_skill_usage` | `(skill_name, *, source=…, success=…, query=…, context_tags=…, score=…)` | Record that a skill was used. Never raises. | [src](../../../core/services/skill_engine.py#L902) |
| function | `analyze_skill_usage` | `(days=…, min_invocations=…)` | Analyze skill usage patterns and generate improvement proposals. | [src](../../../core/services/skill_engine.py#L948) |
| function | `get_skill_usage_stats` | `(name=…, days=…, limit=…)` | Return raw usage stats for a skill (or all skills if name is None). | [src](../../../core/services/skill_engine.py#L1078) |

## `core/services/skill_scanner.py`
_Skill-scanning før lokal eksekvering (spec §19.8 / §15.3.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Finding` | `` | — | [src](../../../core/services/skill_scanner.py#L27) |
| class | `ScanResult` | `` | — | [src](../../../core/services/skill_scanner.py#L35) |
| method | `ScanResult.max_severity` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L40) |
| method | `ScanResult.blocked_reasons` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L46) |
| method | `ScanResult.as_dict` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L49) |
| function | `_normalize` | `(content)` | Fold skjult/forvirrende unicode til NFKC så injection ikke gemmer sig i | [src](../../../core/services/skill_scanner.py#L102) |
| function | `_has_hidden_format_chars` | `(content)` | — | [src](../../../core/services/skill_scanner.py#L110) |
| function | `scan_skill` | `(content, *, path=…, block_severity=…)` | Scan en skill-definition (tekst/kode) for injection/malware/boundary. | [src](../../../core/services/skill_scanner.py#L114) |

## `core/services/skill_security_scanner.py`
_Skill Security Scanner — single canonical scanner for SKILL.md + scripts/._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ScanFinding` | `` | — | [src](../../../core/services/skill_security_scanner.py#L54) |
| class | `ScanResult` | `` | — | [src](../../../core/services/skill_security_scanner.py#L64) |
| method | `ScanResult.passed` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L71) |
| method | `ScanResult.has_critical` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L75) |
| method | `ScanResult.has_high` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L79) |
| method | `ScanResult.max_severity` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L83) |
| method | `ScanResult.summary` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L88) |
| method | `ScanResult.to_dict` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L105) |
| function | `_make_pattern` | `(name, desc, severity, *patterns)` | — | [src](../../../core/services/skill_security_scanner.py#L133) |
| function | `scan_skill_file` | `(skill_path)` | Scan a single SKILL.md file for security issues. | [src](../../../core/services/skill_security_scanner.py#L322) |
| function | `scan_skill_by_name` | `(name)` | Scan a skill by its registered name (lookup in skills root). | [src](../../../core/services/skill_security_scanner.py#L374) |
| function | `scan_all_skills` | `()` | Scan all installed skills. | [src](../../../core/services/skill_security_scanner.py#L391) |
| function | `format_scan_report` | `(results)` | Aggregate multiple scan results into a single report dict. | [src](../../../core/services/skill_security_scanner.py#L405) |
| function | `_risk_from_severity` | `(max_sev, score)` | Map (max_severity, total_score) to a risk label. | [src](../../../core/services/skill_security_scanner.py#L427) |
| function | `_verdict_for_risk` | `(risk)` | — | [src](../../../core/services/skill_security_scanner.py#L444) |
| function | `_scan_text_block` | `(content, source)` | Scan one text block against all patterns. Used for SKILL.md + scripts/. | [src](../../../core/services/skill_security_scanner.py#L464) |
| function | `scan_skill_directory` | `(path)` | Scan a skill directory (SKILL.md + scripts/) and return a risk dict. | [src](../../../core/services/skill_security_scanner.py#L496) |
| function | `scan_skill_directory_gated` | `(path)` | Som scan_skill_directory, men beslutningen GOVERNES af Centralen (SECURITY, | [src](../../../core/services/skill_security_scanner.py#L558) |
| function | `scan_skill_content` | `(content, name=…)` | Scan raw SKILL.md content (e.g. fetched from URL) before writing to disk. | [src](../../../core/services/skill_security_scanner.py#L594) |
| function | `is_skill_safe` | `(name, raise_on_critical=…)` | Check if a skill is safe to import. Returns True if clean. | [src](../../../core/services/skill_security_scanner.py#L609) |

## `core/services/social_labilizer.py`
_Social labilizer — Fase 2 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_matches_any` | `(text, patterns)` | — | [src](../../../core/services/social_labilizer.py#L84) |
| function | `_classify` | `(user_message)` | Return a dict of detected social signals in the user message. | [src](../../../core/services/social_labilizer.py#L91) |
| function | `_flatten_longing` | `(reduction)` | Reduce longing-toward-user pressure by `reduction` (0.0–1.0). | [src](../../../core/services/social_labilizer.py#L107) |
| function | `_boost_caution` | `(boost, target_topic=…)` | Add caution-pressure (push-away from a topic). Used for critique modulation. | [src](../../../core/services/social_labilizer.py#L133) |
| function | `_sharpen_self_anchor` | `()` | When the user asks about Jarvis' state, add a small self-orient signal. | [src](../../../core/services/social_labilizer.py#L155) |
| function | `labilize_pressures_from_user_message` | `(user_message, *, run_id=…)` | Apply social-input deltas to the pressure state. | [src](../../../core/services/social_labilizer.py#L180) |

## `core/services/somatic_daemon.py`
_Somatic daemon — LLM-generated body-state description from structured metrics._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_request_start` | `()` | — | [src](../../../core/services/somatic_daemon.py#L42) |
| function | `record_request_end` | `()` | — | [src](../../../core/services/somatic_daemon.py#L47) |
| function | `record_latency_sample` | `(ms)` | — | [src](../../../core/services/somatic_daemon.py#L52) |
| function | `get_latest_somatic_phrase` | `()` | — | [src](../../../core/services/somatic_daemon.py#L59) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/somatic_daemon.py#L63) |
| function | `build_body_state_surface` | `()` | Returns body state for Mission Control surface. | [src](../../../core/services/somatic_daemon.py#L77) |
| function | `tick_somatic_daemon` | `(energy_level=…)` | Called each heartbeat. May trigger a new somatic phrase generation. | [src](../../../core/services/somatic_daemon.py#L104) |
| function | `_collect_snapshot` | `(energy_level)` | — | [src](../../../core/services/somatic_daemon.py#L132) |
| function | `_should_generate` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L172) |
| function | `_read_cpu_temp_c` | `()` | Læs CPU-temp fra hardware_body. None hvis utilgængelig (graceful omit). | [src](../../../core/services/somatic_daemon.py#L188) |
| function | `_read_loadavg` | `()` | 1-minut system load average. Self-safe → 0.0. | [src](../../../core/services/somatic_daemon.py#L201) |
| function | `_build_raw_phrase` | `(snapshot)` | Byg frasen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/somatic_daemon.py#L210) |
| function | `_generate_phrase` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L231) |
| function | `_pressure_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L276) |
| function | `_load_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L286) |
| function | `_latency_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L299) |
| function | `_store_phrase` | `(phrase, snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L308) |

## `core/services/somatic_runtime_body.py`
_Somatic runtime body: turn runtime signals into bodily regulation cues._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decay_levels` | `(levels, age_seconds)` | Apply time-based decay to stress/arousal levels. | [src](../../../core/services/somatic_runtime_body.py#L38) |
| function | `update_somatic_body` | `(*, event_type, intensity=…, detail=…)` | — | [src](../../../core/services/somatic_runtime_body.py#L53) |
| function | `build_somatic_body_surface` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L104) |
| function | `build_somatic_body_prompt_section` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L116) |
| function | `_base_levels` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L129) |
| function | `_posture` | `(levels)` | — | [src](../../../core/services/somatic_runtime_body.py#L133) |
| function | `_regulation` | `(posture)` | — | [src](../../../core/services/somatic_runtime_body.py#L145) |

## `core/services/source_confidence_gate.py`
_Source-confidence gate (epistemisk gate, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_names` | `(tools_used)` | — | [src](../../../core/services/source_confidence_gate.py#L38) |
| function | `assess_source_confidence` | `(*, output_text, tools_used=…)` | Vurdér epistemisk kilde-konfidens for en tur. | [src](../../../core/services/source_confidence_gate.py#L47) |
| function | `build_source_confidence_surface` | `(*, output_text=…, tools_used=…)` | Central-CLI: jc raw /central/source-confidence (senest vurderede tur, hvis givet). | [src](../../../core/services/source_confidence_gate.py#L88) |

## `core/services/spaced_repetition.py`
_Spaced Repetition — schedule reviews for things Jarvis learned._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/spaced_repetition.py#L39) |
| function | `_load` | `()` | — | [src](../../../core/services/spaced_repetition.py#L43) |
| function | `_save` | `(data)` | — | [src](../../../core/services/spaced_repetition.py#L59) |
| function | `schedule_reviews_on_completion` | `(*, topic, plan_id=…, intervals_days=…)` | Create review entries for a topic at expanding intervals. | [src](../../../core/services/spaced_repetition.py#L71) |
| function | `list_due_reviews` | `(*, now=…, limit=…)` | — | [src](../../../core/services/spaced_repetition.py#L103) |
| function | `complete_review` | `(review_id, *, score)` | Mark a review as completed with score in [0, 1], update profile. | [src](../../../core/services/spaced_repetition.py#L120) |
| function | `_update_profile` | `(profile, score)` | — | [src](../../../core/services/spaced_repetition.py#L150) |
| function | `get_profile` | `(topic)` | — | [src](../../../core/services/spaced_repetition.py#L170) |
| function | `build_spaced_repetition_surface` | `()` | — | [src](../../../core/services/spaced_repetition.py#L174) |
| function | `_summary_line` | `(due, profiles, avg_conf)` | — | [src](../../../core/services/spaced_repetition.py#L205) |
| function | `build_spaced_repetition_prompt_section` | `()` | — | [src](../../../core/services/spaced_repetition.py#L214) |

## `core/services/spatial_entity_ledger.py`
_Spatial entity ledger — Step D.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/spatial_entity_ledger.py#L75) |
| function | `_connect` | `()` | — | [src](../../../core/services/spatial_entity_ledger.py#L92) |
| function | `_lemmatize` | `(token)` | Lemmatize-then-check approach for Danish room nouns. | [src](../../../core/services/spatial_entity_ledger.py#L102) |
| function | `extract_entities` | `(text)` | Pull lexicon-matching entity labels from a sensory description. | [src](../../../core/services/spatial_entity_ledger.py#L138) |
| function | `record_observation` | `(text, *, when=…)` | Process a single sensory description: extract entities, upsert | [src](../../../core/services/spatial_entity_ledger.py#L162) |
| function | `list_observed_entities` | `(*, limit=…)` | — | [src](../../../core/services/spatial_entity_ledger.py#L218) |
| function | `co_entities_for` | `(entity_label, *, limit=…)` | What other entities tend to co-occur with this one? | [src](../../../core/services/spatial_entity_ledger.py#L232) |
| function | `recently_observed` | `(*, hours=…, limit=…)` | — | [src](../../../core/services/spatial_entity_ledger.py#L252) |
| function | `room_entities_section` | `(*, top_n=…)` | One-liner of top-observed entities. Quiet when ledger is empty | [src](../../../core/services/spatial_entity_ledger.py#L271) |
| function | `_listener_loop` | `()` | Poll events table for memory.sensory.recorded (visual only). | [src](../../../core/services/spatial_entity_ledger.py#L291) |
| function | `start_spatial_entity_ledger` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/spatial_entity_ledger.py#L354) |
| function | `stop_spatial_entity_ledger` | `()` | — | [src](../../../core/services/spatial_entity_ledger.py#L371) |
| function | `backfill_from_existing` | `()` | Process all historical visual sensory_memories once. Useful first | [src](../../../core/services/spatial_entity_ledger.py#L379) |

## `core/services/staged_edits.py`
_Staged edits — compose multi-file changes, review, then commit atomically._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StagedEdit` | `` | — | [src](../../../core/services/staged_edits.py#L52) |
| method | `StagedEdit.to_dict` | `(self)` | — | [src](../../../core/services/staged_edits.py#L63) |
| method | `StagedEdit.from_dict` | `(cls, d)` | — | [src](../../../core/services/staged_edits.py#L67) |
| class | `StagedBatch` | `` | All staged edits for a single session (the unit of commit/discard). | [src](../../../core/services/staged_edits.py#L82) |
| method | `StagedBatch.to_dict` | `(self)` | — | [src](../../../core/services/staged_edits.py#L89) |
| method | `StagedBatch.from_dict` | `(cls, d)` | — | [src](../../../core/services/staged_edits.py#L98) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/staged_edits.py#L110) |
| function | `_path_for` | `(session_id)` | — | [src](../../../core/services/staged_edits.py#L114) |
| function | `_load` | `(session_id)` | — | [src](../../../core/services/staged_edits.py#L119) |
| function | `_save` | `(batch)` | — | [src](../../../core/services/staged_edits.py#L132) |
| function | `_make_diff` | `(path, old, new)` | — | [src](../../../core/services/staged_edits.py#L142) |
| function | `stage_edit` | `(*, session_id, path, old_text, new_text, replace_all=…, note=…)` | Stage an edit_file-style change without writing to disk. | [src](../../../core/services/staged_edits.py#L157) |
| function | `stage_write` | `(*, session_id, path, content, note=…)` | Stage a write_file-style overwrite/create. If the target exists, | [src](../../../core/services/staged_edits.py#L205) |
| function | `_persist_edit` | `(*, session_id, kind, path, old_content, new_content, note, file_existed)` | — | [src](../../../core/services/staged_edits.py#L234) |
| function | `list_staged` | `(session_id, *, full_diffs=…)` | Return all staged edits for the session. | [src](../../../core/services/staged_edits.py#L280) |
| function | `commit_staged` | `(session_id, *, stage_ids=…)` | Apply staged edits to disk in stage order. | [src](../../../core/services/staged_edits.py#L319) |
| function | `discard_staged` | `(session_id, *, stage_ids=…)` | Drop staged edits without applying. | [src](../../../core/services/staged_edits.py#L417) |

## `core/services/standing_orders_registry.py`
_Standing-orders registry — INDEPENDENT grounding for the reasoning-interceptor's standing-orders_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/standing_orders_registry.py#L13) |
| function | `add_standing_order` | `(*, text, match_key=…)` | — | [src](../../../core/services/standing_orders_registry.py#L25) |
| function | `set_standing_order_active` | `(order_id, *, active)` | — | [src](../../../core/services/standing_orders_registry.py#L36) |
| function | `list_active_standing_orders` | `()` | — | [src](../../../core/services/standing_orders_registry.py#L47) |

## `core/services/state_flag_store.py`
_State-flag store (leak-kandidat #1, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/state_flag_store.py#L22) |
| function | `_key` | `(user_id)` | — | [src](../../../core/services/state_flag_store.py#L26) |
| function | `_load` | `(user_id)` | — | [src](../../../core/services/state_flag_store.py#L30) |
| function | `_save` | `(user_id, flags)` | — | [src](../../../core/services/state_flag_store.py#L39) |
| function | `_prune` | `(flags)` | Fjern udløbne flag. Returnerer den rensede dict (muterer input). | [src](../../../core/services/state_flag_store.py#L43) |
| function | `set_flag` | `(key, value, *, ttl_minutes=…, user_id=…)` | Sæt/opdatér et flag. ttl_minutes=None/0 → intet udløb. Returnerer den lagrede | [src](../../../core/services/state_flag_store.py#L53) |
| function | `get_flag` | `(key, *, user_id=…)` | Læs et flag (prune udløbne først). None hvis ukendt/udløbet. | [src](../../../core/services/state_flag_store.py#L70) |
| function | `clear_flag` | `(key, *, user_id=…)` | Fjern et flag. True hvis det fandtes. | [src](../../../core/services/state_flag_store.py#L81) |
| function | `list_flags` | `(*, user_id=…)` | Alle aktive (ikke-udløbne) flag. | [src](../../../core/services/state_flag_store.py#L94) |

## `core/services/stream_degeneration.py`
_Degenerations-guard — fang model-repetitions-løkker i streaming-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_degeneration` | `(text)` | → (er_degenereret, menneskelæsbar_grund). Self-safe → (False, '') ved enhver fejl. | [src](../../../core/services/stream_degeneration.py#L29) |

## `core/services/stream_failure_kind.py`
_Struktureret failure-taksonomi for streaming/followup (spec §11.1 B11, I5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FailureKind` | `` | Kanoniske failure-kind-strenge (str-const set fremfor Enum så de | [src](../../../core/services/stream_failure_kind.py#L37) |
| function | `_scan_http_status` | `(text)` | — | [src](../../../core/services/stream_failure_kind.py#L121) |
| function | `_contains` | `(text, needles)` | — | [src](../../../core/services/stream_failure_kind.py#L131) |
| function | `classify_failure` | `(*, http_status=…, error_text=…, kind_hint=…)` | Klassificér en streaming/followup-fejl → (failure_kind, retryable). | [src](../../../core/services/stream_failure_kind.py#L135) |
| function | `is_retryable_kind` | `(failure_kind)` | Er ``failure_kind`` retryable på SAMME provider? (provider_stall = False.) | [src](../../../core/services/stream_failure_kind.py#L225) |
| function | `compute_backoff_with_jitter` | `(attempt, *, base=…, cap=…, retry_after=…)` | Eksponentiel backoff MED jitter (spec §11.2, OpenAI-SDK-mønster). | [src](../../../core/services/stream_failure_kind.py#L242) |
| class | `MalformedStreamPayload` | `` | Streamen sluttede malformet (trunkeret final-JSON / ingen terminal/``done``) | [src](../../../core/services/stream_failure_kind.py#L291) |
| function | `safe_decode_line` | `(raw_line)` | Decode én rå stream-linje UDEN nogensinde at rejse. | [src](../../../core/services/stream_failure_kind.py#L298) |
| function | `try_parse_json_line` | `(data)` | Parse én JSON ``data:``-streng → ``(payload, ok)``, ALDRIG rejsende. | [src](../../../core/services/stream_failure_kind.py#L319) |

## `core/services/stream_sentinel.py`
_Stream-cluster — observabilitet for SSE-lanen. IKKE en blokerende gate: streaming er_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, run_id, session_id, **data)` | — | [src](../../../core/services/stream_sentinel.py#L32) |
| function | `note_start` | `(run_id, session_id=…, **meta)` | En SSE-stream sendte message_start. Registrér + observe + opportunistisk stall-sweep. | [src](../../../core/services/stream_sentinel.py#L43) |
| function | `note_stop` | `(run_id, *, reason=…)` | En SSE-stream sendte message_stop (reason='done' normalt, 'fallback' = terminal-garanti). | [src](../../../core/services/stream_sentinel.py#L58) |
| function | `note_event` | `(run_id, kind, session_id=…, **data)` | Andre lane-fejl/edge-cases: idle / cancel / error / zombie_slot / subscriber_timeout. | [src](../../../core/services/stream_sentinel.py#L80) |
| function | `_sweep_stalled` | `(timeout_s=…)` | message_start uden message_stop i >timeout_s → ægte zombie → flag ÉN gang pr. run | [src](../../../core/services/stream_sentinel.py#L88) |
| function | `sweep` | `()` | Eksternt-kaldbar stall-sweep (fx fra heartbeat-kadence). Returnér antal live streams. | [src](../../../core/services/stream_sentinel.py#L115) |
| function | `live_count` | `()` | — | [src](../../../core/services/stream_sentinel.py#L125) |

