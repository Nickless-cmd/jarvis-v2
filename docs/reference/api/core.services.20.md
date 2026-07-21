# `core.services.20` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/structured_content_flag.py`
_Governed kill-switch for struktureret content-persist + wire. Default ON._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_flag` | `()` | Læs rå flag-værdi fra runtime-state. None = usat. | [src](../../../core/services/structured_content_flag.py#L12) |
| function | `structured_content_v2_enabled` | `()` | True medmindre eksplicit slået fra ('off'/'0'/'false'/'no'). Læse-fejl → True | [src](../../../core/services/structured_content_flag.py#L18) |

## `core/services/subagent_digest.py`
_Surface recently-completed subagents into the visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_marks` | `()` | — | [src](../../../core/services/subagent_digest.py#L30) |
| function | `_save_marks` | `(marks)` | — | [src](../../../core/services/subagent_digest.py#L37) |
| function | `_last_seen` | `(session_id)` | — | [src](../../../core/services/subagent_digest.py#L41) |
| function | `_mark_seen` | `(session_id, when_iso)` | — | [src](../../../core/services/subagent_digest.py#L45) |
| function | `subagent_digest_section` | `(session_id)` | Format completed subagents (since this session last looked) as a block. | [src](../../../core/services/subagent_digest.py#L52) |

## `core/services/subagent_ecology.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_subagent_ecology_surface` | `()` | — | [src](../../../core/services/subagent_ecology.py#L13) |
| function | `_build_subagent_ecology_surface_uncached` | `()` | — | [src](../../../core/services/subagent_ecology.py#L21) |
| function | `build_subagent_ecology_from_sources` | `(*, affective_meta_state, epistemic_runtime_state, conflict_trace, loop_runtime, prompt_evolution, quiet_initiative)` | — | [src](../../../core/services/subagent_ecology.py#L32) |
| function | `build_subagent_ecology_prompt_section` | `(surface=…)` | — | [src](../../../core/services/subagent_ecology.py#L119) |
| function | `_build_critic_role` | `(*, epistemic, conflict, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L153) |
| function | `_build_witness_helper_role` | `(*, affective, quiet, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L182) |
| function | `_build_planner_helper_role` | `(*, loop_summary, prompt_summary, latest_prompt, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L212) |
| function | `_role` | `(*, role_name, role_kind, current_status, activation_reason, last_activation_at)` | — | [src](../../../core/services/subagent_ecology.py#L246) |
| function | `_source_contributors` | `(*, affective, epistemic, conflict, loop_summary, prompt_summary, quiet)` | — | [src](../../../core/services/subagent_ecology.py#L266) |
| function | `_summary_text` | `(active_roles, cooling_roles, blocked_roles)` | — | [src](../../../core/services/subagent_ecology.py#L338) |
| function | `_guidance_for_ecology` | `(*, active_roles, roles)` | — | [src](../../../core/services/subagent_ecology.py#L352) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/subagent_ecology.py#L371) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/subagent_ecology.py#L381) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/subagent_ecology.py#L391) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/subagent_ecology.py#L401) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/subagent_ecology.py#L411) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/subagent_ecology.py#L421) |

## `core/services/subjective_time.py`
_Subjective Time — how time FEELS, not just passes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_subjective_time_perception` | `(*, tick_count_last_hour=…, conversation_intensity=…, novelty_score=…, idle_hours=…)` | — | [src](../../../core/services/subjective_time.py#L9) |
| function | `build_subjective_time_surface` | `()` | — | [src](../../../core/services/subjective_time.py#L29) |

## `core/services/surprise_daemon.py`
_Surprise daemon — first-person surprise when Jarvis's reactions diverge from baseline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/surprise_daemon.py#L29) |
| function | `_surprise_type_to_concept` | `(surprise_type)` | Map surprise classification to primary emotion concept. | [src](../../../core/services/surprise_daemon.py#L37) |
| function | `_afterimage_concept` | `(surprise_type)` | Map surprise classification to afterimage emotion concept. | [src](../../../core/services/surprise_daemon.py#L45) |
| function | `_process_pending_afterimages` | `()` | Trigger afterimage emotion concepts whose delay has elapsed. | [src](../../../core/services/surprise_daemon.py#L50) |
| function | `tick_surprise_daemon` | `(inner_voice_mode=…, somatic_energy=…, skip_event_gate=…)` | — | [src](../../../core/services/surprise_daemon.py#L73) |
| function | `_raw_signal_mode` | `()` | Self-safe læsning af runtime-state-flaget `raw_signal_mode` (default off). | [src](../../../core/services/surprise_daemon.py#L123) |
| function | `_render_raw_divergence` | `(divergence)` | Byg rå kategorisk divergens-streng (ingen LLM, ingen prosa). | [src](../../../core/services/surprise_daemon.py#L132) |
| function | `get_latest_surprise` | `()` | — | [src](../../../core/services/surprise_daemon.py#L146) |
| function | `build_surprise_surface` | `()` | — | [src](../../../core/services/surprise_daemon.py#L150) |
| function | `_record_snapshot` | `(mode, energy)` | — | [src](../../../core/services/surprise_daemon.py#L175) |
| function | `_compute_divergence` | `(current_mode, current_energy)` | — | [src](../../../core/services/surprise_daemon.py#L187) |
| function | `_generate_surprise` | `(mode, energy, divergence)` | — | [src](../../../core/services/surprise_daemon.py#L209) |
| function | `_store_surprise` | `(phrase, divergence)` | — | [src](../../../core/services/surprise_daemon.py#L238) |
| function | `_classify_surprise` | `(phrase)` | — | [src](../../../core/services/surprise_daemon.py#L293) |

## `core/services/surprise_detector.py`
_Surprise detector — anomaly signals for the proactive/autonomous lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_state` | `()` | — | [src](../../../core/services/surprise_detector.py#L39) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/surprise_detector.py#L44) |
| function | `_publish` | `(kind, summary, detail=…)` | — | [src](../../../core/services/surprise_detector.py#L48) |
| function | `_check_error_burst` | `()` | — | [src](../../../core/services/surprise_detector.py#L63) |
| function | `_check_first_of_its_kind` | `()` | Track every event kind we've ever seen; new ones become surprises. | [src](../../../core/services/surprise_detector.py#L87) |
| function | `_check_approval_starvation` | `()` | Check pending_approvals state for cards older than threshold. | [src](../../../core/services/surprise_detector.py#L116) |
| function | `check_surprises` | `()` | Run all anomaly checks; return a summary of what fired. | [src](../../../core/services/surprise_detector.py#L151) |
| function | `_exec_check_surprises` | `(_args)` | — | [src](../../../core/services/surprise_detector.py#L160) |

## `core/services/sustained_attention.py`
_Sustained Attention — ongoing projects that survive across ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/sustained_attention.py#L37) |
| function | `_load` | `()` | — | [src](../../../core/services/sustained_attention.py#L41) |
| function | `_save` | `(items)` | — | [src](../../../core/services/sustained_attention.py#L55) |
| function | `create_project` | `(*, name, description=…, why=…, priority=…, autonomy_level=…, context_snapshot=…)` | — | [src](../../../core/services/sustained_attention.py#L67) |
| function | `add_progress` | `(project_id, note, *, context=…)` | — | [src](../../../core/services/sustained_attention.py#L105) |
| function | `set_status` | `(project_id, status)` | — | [src](../../../core/services/sustained_attention.py#L124) |
| function | `set_autonomy` | `(project_id, level)` | — | [src](../../../core/services/sustained_attention.py#L138) |
| function | `list_projects` | `(*, status=…)` | — | [src](../../../core/services/sustained_attention.py#L150) |
| function | `get_project` | `(project_id)` | — | [src](../../../core/services/sustained_attention.py#L157) |
| function | `_hours_since` | `(iso_str)` | — | [src](../../../core/services/sustained_attention.py#L164) |
| function | `_auto_pause_stale` | `(items)` | — | [src](../../../core/services/sustained_attention.py#L174) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/sustained_attention.py#L187) |
| function | `build_sustained_attention_surface` | `()` | — | [src](../../../core/services/sustained_attention.py#L196) |
| function | `_surface_summary` | `(active, paused, completed)` | — | [src](../../../core/services/sustained_attention.py#L229) |
| function | `build_sustained_attention_prompt_section` | `()` | — | [src](../../../core/services/sustained_attention.py#L246) |

## `core/services/system_cartographer.py`
_System Cartographer — broad map of Jarvis' runtime and inner layers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_system_cartographer_surface` | `(*, auto_enqueue=…)` | — | [src](../../../core/services/system_cartographer.py#L42) |
| function | `start_system_cartographer_daemon` | `()` | — | [src](../../../core/services/system_cartographer.py#L123) |
| function | `stop_system_cartographer_daemon` | `()` | — | [src](../../../core/services/system_cartographer.py#L133) |
| function | `_observe_to_central` | `(surface)` | System-cluster: MELD kartografens kort til Den Intelligente Central (self-safe). | [src](../../../core/services/system_cartographer.py#L137) |
| function | `_observe_gaps_to_central` | `(surface)` | Jarvis' handlingsordre (docs/notes/2026-07-01-cartographer-to-central.md, P1): meld | [src](../../../core/services/system_cartographer.py#L170) |
| function | `_loop` | `()` | — | [src](../../../core/services/system_cartographer.py#L227) |
| function | `_service_files` | `()` | — | [src](../../../core/services/system_cartographer.py#L241) |
| function | `_service_node` | `(path, text)` | — | [src](../../../core/services/system_cartographer.py#L257) |
| function | `_daemon_nodes` | `()` | — | [src](../../../core/services/system_cartographer.py#L284) |
| function | `_surface_nodes` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L307) |
| function | `_event_family_nodes` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L319) |
| function | `_edges` | `(*, services, daemons, surfaces, event_families, causal)` | — | [src](../../../core/services/system_cartographer.py#L331) |
| function | `_causal_runtime_evidence` | `(limit=…)` | — | [src](../../../core/services/system_cartographer.py#L362) |
| function | `_dark_edges` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L421) |
| function | `_rank_dark_edges` | `(dark_edges, *, causal, daemons)` | — | [src](../../../core/services/system_cartographer.py#L435) |
| function | `_coverage_summary` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L475) |
| function | `_is_pure_utility` | `(service)` | Detect services that are pure helpers — no observable state, no IO, | [src](../../../core/services/system_cartographer.py#L498) |
| function | `_coverage_score` | `(service)` | — | [src](../../../core/services/system_cartographer.py#L524) |
| function | `_system_health_from_jarvis_perspective` | `(*, dark_edges, coverage, theater, recommended)` | — | [src](../../../core/services/system_cartographer.py#L554) |
| function | `_dark_edge_score` | `(*, service, kind, is_daemon, has_causal_family)` | — | [src](../../../core/services/system_cartographer.py#L584) |
| function | `_priority_label` | `(score)` | — | [src](../../../core/services/system_cartographer.py#L608) |
| function | `_observability_task_from_dark_edge` | `(edge)` | — | [src](../../../core/services/system_cartographer.py#L616) |
| function | `_maybe_enqueue_observability_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L634) |
| function | `_find_existing_observability_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L681) |
| function | `_maybe_enqueue_theater_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L698) |
| function | `_find_existing_theater_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L745) |
| function | `_runtime_task_priority` | `(priority)` | — | [src](../../../core/services/system_cartographer.py#L763) |
| function | `_theater_audit_surface` | `()` | — | [src](../../../core/services/system_cartographer.py#L770) |
| function | `_tool_count` | `()` | — | [src](../../../core/services/system_cartographer.py#L783) |
| function | `_classify_service` | `(*, name, text)` | — | [src](../../../core/services/system_cartographer.py#L792) |

## `core/services/task_worker.py`
_Task worker — consumes queued runtime_tasks in heartbeat tick cadence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `claim_next_task` | `(kinds=…)` | Claim the next queued task and mark it `running`. | [src](../../../core/services/task_worker.py#L33) |
| function | `_handle_initiative_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L51) |
| function | `_handle_heartbeat_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L56) |
| function | `_handle_open_loop_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L61) |
| function | `_handle_agency_bridge_repair` | `(task)` | Prepare a repair brief for a weak agency bridge. | [src](../../../core/services/task_worker.py#L66) |
| function | `_handle_observability_bridge_repair` | `(task)` | — | [src](../../../core/services/task_worker.py#L107) |
| function | `_handle_theater_refactor` | `(task)` | — | [src](../../../core/services/task_worker.py#L138) |
| function | `_execute_task` | `(task)` | Execute a single task and persist its final status. Never raises. | [src](../../../core/services/task_worker.py#L177) |
| function | `tick_task_worker` | `(budget=…)` | Run one worker tick: claim and execute up to ``budget`` tasks. | [src](../../../core/services/task_worker.py#L240) |
| function | `_matching_agency_edge` | `(*, scope, goal)` | — | [src](../../../core/services/task_worker.py#L278) |
| function | `_edge_by_id` | `(edges, edge_id)` | — | [src](../../../core/services/task_worker.py#L300) |
| function | `_store_agency_repair_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L307) |
| function | `_store_observability_repair_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L315) |
| function | `_store_theater_refactor_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L323) |
| function | `_matching_theater_file` | `(*, scope)` | — | [src](../../../core/services/task_worker.py#L331) |
| function | `_suggested_agency_files` | `(*, scope, edge)` | — | [src](../../../core/services/task_worker.py#L346) |
| function | `_suggested_observability_files` | `(*, scope, service)` | — | [src](../../../core/services/task_worker.py#L382) |
| function | `_suggested_theater_files` | `(*, scope)` | — | [src](../../../core/services/task_worker.py#L396) |

## `core/services/taste_profile.py`
_Taste Profile — accumulating aesthetic preferences for code, design, and communication._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_taste_from_run` | `(*, run_id, user_message, was_corrected, outcome_status)` | Update taste profile based on a visible run interaction. | [src](../../../core/services/taste_profile.py#L67) |
| function | `update_taste_async` | `(*, run_id, user_message, was_corrected, outcome_status)` | — | [src](../../../core/services/taste_profile.py#L125) |
| function | `get_crystallized_tastes` | `()` | Return taste dimensions that have moved decisively (>0.72 or <0.28). | [src](../../../core/services/taste_profile.py#L140) |
| function | `build_taste_profile_surface` | `()` | — | [src](../../../core/services/taste_profile.py#L155) |
| function | `_safe` | `(fn, **kwargs)` | — | [src](../../../core/services/taste_profile.py#L167) |
| function | `_safe_json` | `(value, default)` | — | [src](../../../core/services/taste_profile.py#L174) |

## `core/services/team_mentions.py`
_@mention-parsing for team-sessioner (Teams-feature, spec 2026-06-20 §5.2-5.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `extract_mentions` | `(text)` | Rå @-tokens i teksten (lowercased, dedupe, rækkefølge bevaret). | [src](../../../core/services/team_mentions.py#L17) |
| function | `parse_mentions` | `(text, member_ids)` | Klassificér mentions mod et teams medlemskab. | [src](../../../core/services/team_mentions.py#L27) |
| function | `should_jarvis_respond` | `(text, *, is_reply_to_jarvis=…)` | v1 (summoned baseline, spec §5.2): Jarvis svarer i en team-session KUN når | [src](../../../core/services/team_mentions.py#L47) |

## `core/services/teams.py`
_Team data-lag: CRUD, medlemskab, rolle-opslag, scope-helper (Teams-feature,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/teams.py#L19) |
| function | `_new_id` | `()` | — | [src](../../../core/services/teams.py#L23) |
| function | `_new_token` | `()` | — | [src](../../../core/services/teams.py#L27) |
| function | `_invite_expiry_iso` | `()` | — | [src](../../../core/services/teams.py#L31) |
| function | `create_team` | `(name, *, owner_user_id)` | Opret team + git-workspace; opretteren bliver owner, Jarvis bliver deltager. | [src](../../../core/services/teams.py#L35) |
| function | `add_member` | `(team_id, user_id, team_role=…)` | — | [src](../../../core/services/teams.py#L58) |
| function | `member_role` | `(team_id, user_id)` | — | [src](../../../core/services/teams.py#L67) |
| function | `is_member` | `(team_id, user_id)` | — | [src](../../../core/services/teams.py#L76) |
| function | `list_members` | `(team_id)` | — | [src](../../../core/services/teams.py#L80) |
| function | `list_teams_for_user` | `(user_id)` | — | [src](../../../core/services/teams.py#L89) |
| function | `get_team` | `(team_id)` | — | [src](../../../core/services/teams.py#L101) |
| function | `list_team_sessions` | `(team_id)` | Delte sessioner der hører til et team (nyeste først). | [src](../../../core/services/teams.py#L114) |
| function | `create_invite` | `(team_id, *, invited_email, invited_by)` | Opret et pending invite-token (gemmer email → muliggør email-onboarding | [src](../../../core/services/teams.py#L126) |
| function | `get_invite` | `(token)` | — | [src](../../../core/services/teams.py#L139) |
| function | `list_pending_invites_for` | `(*, user_id, email=…)` | Pull-baseret invite-levering: alle pending, ikke-udløbne invites hvor | [src](../../../core/services/teams.py#L152) |
| function | `accept_invite` | `(token, *, accepting_user_id)` | Valider + acceptér et invite. Tilføjer brugeren som editor og markerer | [src](../../../core/services/teams.py#L179) |
| function | `autocommit` | `(team_id, *, message, author_user_id)` | Stage alt i team-repoet og commit med den handlende bruger som author. | [src](../../../core/services/teams.py#L199) |
| function | `team_scope_sql` | `(session_alias=…)` | SQL-fragment: 'sessionen er en team-session jeg er medlem af'. Bruger | [src](../../../core/services/teams.py#L218) |
| function | `can_admin` | `(team_id, user_id)` | — | [src](../../../core/services/teams.py#L229) |
| function | `remove_member` | `(team_id, user_id, *, acting_user_id)` | — | [src](../../../core/services/teams.py#L233) |

## `core/services/telegram_gateway.py`
_Telegram gateway — bidirectional messaging via Telegram Bot API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/telegram_gateway.py#L43) |
| function | `is_configured` | `()` | — | [src](../../../core/services/telegram_gateway.py#L57) |
| function | `get_status` | `()` | — | [src](../../../core/services/telegram_gateway.py#L61) |
| function | `_api` | `(token, method, payload)` | — | [src](../../../core/services/telegram_gateway.py#L67) |
| function | `_api_get` | `(token, method, payload)` | HTTP GET to Telegram Bot API (used for getFile). | [src](../../../core/services/telegram_gateway.py#L77) |
| function | `_api_post_file` | `(token, method, data, files)` | HTTP POST multipart/form-data to Telegram Bot API (sendPhoto etc.). | [src](../../../core/services/telegram_gateway.py#L87) |
| function | `_resolve_telegram_file_url` | `(*, token, file_id)` | Call getFile to get a download URL for a Telegram file_id. | [src](../../../core/services/telegram_gateway.py#L120) |
| function | `_extract_telegram_media` | `(msg)` | Extract media items from a Telegram message dict. | [src](../../../core/services/telegram_gateway.py#L135) |
| function | `_download_tg_attachment` | `(url, filename, mime, size, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L179) |
| function | `_build_telegram_attachment_prefix` | `(media_items, *, token, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L193) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/telegram_gateway.py#L220) |
| function | `send_telegram_file` | `(text, file_path, chat_id=…)` | Send a file to owner (or chat_id) via Telegram. | [src](../../../core/services/telegram_gateway.py#L225) |
| function | `send_message` | `(text, chat_id=…, parse_mode=…)` | Send a message to owner (or specific chat_id). Returns status dict. | [src](../../../core/services/telegram_gateway.py#L267) |
| function | `_get_or_create_session` | `(chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L302) |
| function | `_poll_loop` | `(token, owner_chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L313) |
| function | `_eventbus_subscriber_loop` | `()` | Buffer assistant responses per session, flush when run completes. | [src](../../../core/services/telegram_gateway.py#L408) |
| function | `start_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L464) |
| function | `stop_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L495) |

## `core/services/temperament_tendency_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_temperament_tendency_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L24) |
| function | `refresh_runtime_temperament_tendency_signal_statuses` | `()` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L47) |
| function | `build_runtime_temperament_tendency_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L78) |
| function | `_extract_temperament_tendency_candidates` | `(*, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L112) |
| function | `_build_candidate` | `(*, focus, meaning_signal, relation_continuity, regulation, private_state, executive_contradiction, temporal_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L141) |
| function | `_persist_temperament_tendency_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L263) |
| function | `_latest_relation_continuity` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L332) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L344) |
| function | `_latest_private_state` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L356) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L368) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L380) |
| function | `_derive_temperament_type` | `(*, meaning_weight, continuity_state, continuity_watchfulness, regulation_state, regulation_watchfulness, contradiction_pressure, promotion_pull, state_tone)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L392) |
| function | `_derive_temperament_balance` | `(*, temperament_type, regulation_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L414) |
| function | `_derive_temperament_weight` | `(*, meaning_weight, continuity_weight, contradiction_pressure)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L434) |
| function | `_derive_status` | `(*, meaning_status, continuity_status, regulation_status)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L447) |
| function | `_grounding_mode` | `(*, has_regulation, has_private_state, has_contradiction, has_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L453) |
| function | `_temperament_summary` | `(*, focus, temperament_type, temperament_balance, temperament_weight)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L472) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L485) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L493) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L501) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L512) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L524) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L535) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L542) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L559) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L602) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L609) |
| function | `_weight_from_support_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L617) |
| function | `_balance_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L628) |

## `core/services/temporal_body.py`
_Temporal Body — sense of age._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `age_journey` | `(thoughts=…)` | — | [src](../../../core/services/temporal_body.py#L8) |
| function | `get_temporal_body_age` | `()` | — | [src](../../../core/services/temporal_body.py#L13) |
| function | `describe_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L23) |
| function | `format_age_for_prompt` | `()` | — | [src](../../../core/services/temporal_body.py#L27) |
| function | `reset_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L30) |
| function | `build_temporal_body_surface` | `()` | — | [src](../../../core/services/temporal_body.py#L35) |

## `core/services/temporal_context.py`
_Temporal Context — time-based situational awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_temporal_context` | `()` | Build current temporal context in local (CEST/CET) time. | [src](../../../core/services/temporal_context.py#L20) |
| function | `build_temporal_context_surface` | `()` | — | [src](../../../core/services/temporal_context.py#L44) |
| function | `_classify_day_phase` | `(hour)` | — | [src](../../../core/services/temporal_context.py#L53) |
| function | `_emit_temporal_context_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/temporal_context.py#L67) |

## `core/services/temporal_depth.py`
_Temporal Depth — predictive coding for internal signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TemporalSignal` | `` | Compact representation of temporal context. | [src](../../../core/services/temporal_depth.py#L33) |
| class | `TemporalDepth` | `` | Reads current signal state + recent history to produce temporal modulation. | [src](../../../core/services/temporal_depth.py#L41) |
| method | `TemporalDepth.__init__` | `(self)` | — | [src](../../../core/services/temporal_depth.py#L48) |
| method | `TemporalDepth.assess` | `(self, assembly_state, now_iso)` | Main entry point. Returns a TemporalSignal that assembly uses | [src](../../../core/services/temporal_depth.py#L52) |
| method | `TemporalDepth.invalidate` | `(self)` | Clear cache so next call recomputes. | [src](../../../core/services/temporal_depth.py#L73) |
| method | `TemporalDepth._compute_temporal` | `(self, state, now_iso)` | Compute temporal modulation from assembly state. | [src](../../../core/services/temporal_depth.py#L77) |
| method | `TemporalDepth._compute_recall` | `(self, state)` | How present is recent history in current experience? | [src](../../../core/services/temporal_depth.py#L109) |
| method | `TemporalDepth._compute_anticipation` | `(self, state)` | Does reality match what I expected? | [src](../../../core/services/temporal_depth.py#L131) |
| method | `TemporalDepth._compute_rhythm` | `(self, state)` | Does now match the expected recurring cadence? | [src](../../../core/services/temporal_depth.py#L149) |
| method | `TemporalDepth._build_summary` | `(self, recall, anticipation, rhythm)` | Build a short human-readable phrase for the assembly output. | [src](../../../core/services/temporal_depth.py#L160) |
| function | `get_temporal_depth` | `()` | — | [src](../../../core/services/temporal_depth.py#L180) |

## `core/services/temporal_narrative.py`
_Temporal Narrative — continuous self-history over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NarrativeBeat` | `` | A beat in Jarvis' narrative thread. | [src](../../../core/services/temporal_narrative.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/temporal_narrative.py#L36) |
| function | `add_beat` | `(mood, event)` | Add a beat to the narrative thread. | [src](../../../core/services/temporal_narrative.py#L40) |
| function | `add_beat_from_affective` | `()` | Add a beat based on current affective state. | [src](../../../core/services/temporal_narrative.py#L66) |
| function | `summarize_current_self` | `()` | Summarize current self based on narrative thread. | [src](../../../core/services/temporal_narrative.py#L80) |
| function | `ask_self_question` | `()` | Jarvis asks himself a question based on narrative. | [src](../../../core/services/temporal_narrative.py#L100) |
| function | `format_narrative_for_prompt` | `()` | Format narrative for prompt injection. | [src](../../../core/services/temporal_narrative.py#L117) |
| function | `get_thread` | `()` | Get the full narrative thread. | [src](../../../core/services/temporal_narrative.py#L130) |
| function | `reset_temporal_narrative` | `()` | Reset temporal narrative state (for testing). | [src](../../../core/services/temporal_narrative.py#L143) |
| function | `build_temporal_narrative_surface` | `()` | Build MC surface for temporal narrative. | [src](../../../core/services/temporal_narrative.py#L150) |

## `core/services/temporal_recurrence_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_temporal_recurrence_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L21) |
| function | `refresh_runtime_temporal_recurrence_signal_statuses` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L43) |
| function | `build_runtime_temporal_recurrence_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L74) |
| function | `_extract_recurrence_candidates` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L97) |
| function | `_persist_recurrence_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L216) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items, record_count)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L285) |
| function | `_empty_snapshot` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L322) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L338) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L350) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L362) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L366) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L371) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L376) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L385) |

## `core/services/temporal_rhythm.py`
_Temporal Rhythm — felt time, not computed time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_pending_initiatives_count` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L35) |
| function | `_recent_tool_calls_per_min` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L43) |
| function | `_recent_chat_activity_per_min` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L53) |
| function | `_eventbus_queue_depth` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L73) |
| function | `_compute_pulse_rate` | `(*, initiatives, tool_rate, chat_rate, queue)` | Combine inputs into pulse in [0.1, 2.0]. | [src](../../../core/services/temporal_rhythm.py#L94) |
| function | `_label_from_pulse` | `(pulse)` | — | [src](../../../core/services/temporal_rhythm.py#L111) |
| function | `_perceived_elapsed_factor` | `(pulse)` | When pulse is high, subjective time moves slower relative to clock. | [src](../../../core/services/temporal_rhythm.py#L121) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/temporal_rhythm.py#L129) |
| function | `get_current_rhythm` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L168) |
| function | `build_temporal_rhythm_surface` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L172) |
| function | `_surface_summary` | `(current, baseline)` | — | [src](../../../core/services/temporal_rhythm.py#L191) |
| function | `build_temporal_rhythm_prompt_section` | `()` | Surface only when tempo is unusual. | [src](../../../core/services/temporal_rhythm.py#L199) |

## `core/services/temporal_self_continuity.py`
_Temporal self-continuity: past/current/future self handoff._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_temporal_continuity_from_latest_episode` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L16) |
| function | `update_temporal_continuity_from_episode` | `(episode)` | — | [src](../../../core/services/temporal_self_continuity.py#L23) |
| function | `build_temporal_self_continuity_surface` | `(*, limit=…)` | — | [src](../../../core/services/temporal_self_continuity.py#L51) |
| function | `build_temporal_self_continuity_prompt_section` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L66) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/temporal_self_continuity.py#L79) |
| function | `_load` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L89) |

## `core/services/text_clip.py`
_core/services/text_clip.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `clip_text` | `(value, *, limit, hard=…)` | Klip tekst til <= ~limit tegn UDEN at hugge midt i et ord. | [src](../../../core/services/text_clip.py#L16) |
| function | `clip_head_tail` | `(value, *, limit, tail_frac=…)` | Bevar HOVED + HALE ved LINJE-grænser når tekst overskrider limit. Til tool-output (bash/read/ | [src](../../../core/services/text_clip.py#L53) |
| function | `clip_words` | `(value, *, max_words)` | Klip til et antal ORD (ikke tegn) — når ord er den meningsfulde enhed. Self-safe. | [src](../../../core/services/text_clip.py#L88) |

## `core/services/text_resonance.py`
_Text Resonance — I feel what I read, before I analyze it._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resonate` | `(text, *, source=…)` | Compute warmth, cold, urgency scores for a piece of text. | [src](../../../core/services/text_resonance.py#L61) |
| function | `recent_resonances` | `(*, limit=…)` | — | [src](../../../core/services/text_resonance.py#L139) |
| function | `build_text_resonance_surface` | `()` | — | [src](../../../core/services/text_resonance.py#L143) |
| function | `build_text_resonance_prompt_section` | `()` | Only surface when recent reading is strongly toned. | [src](../../../core/services/text_resonance.py#L168) |
| function | `reset_text_resonance` | `()` | — | [src](../../../core/services/text_resonance.py#L185) |

## `core/services/theater_audit.py`
_Theater Audit -- find narrative-first inner-life patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_theater_audit_surface` | `()` | — | [src](../../../core/services/theater_audit.py#L85) |
| function | `_scan_findings` | `()` | — | [src](../../../core/services/theater_audit.py#L113) |
| function | `_scan_files` | `()` | — | [src](../../../core/services/theater_audit.py#L160) |
| function | `_python_line_state` | `(line, in_docstring)` | Track multi-line docstring state and decide whether to skip this line. | [src](../../../core/services/theater_audit.py#L178) |
| function | `_skip_python_line` | `(line)` | Backwards-compatible wrapper. Use _python_line_state for new code. | [src](../../../core/services/theater_audit.py#L226) |
| function | `_strip_trailing_inline_comment` | `(line)` | Drop trailing `  # ...` or `\t# ...` comment so its prose isn't scanned. | [src](../../../core/services/theater_audit.py#L232) |
| function | `_rank_files` | `(findings)` | — | [src](../../../core/services/theater_audit.py#L247) |
| function | `_recommended_task` | `(files)` | — | [src](../../../core/services/theater_audit.py#L284) |
| function | `_counts` | `(findings)` | — | [src](../../../core/services/theater_audit.py#L309) |
| function | `_priority_label` | `(score)` | — | [src](../../../core/services/theater_audit.py#L317) |
| function | `_excerpt` | `(line)` | — | [src](../../../core/services/theater_audit.py#L325) |

## `core/services/theory_of_mind.py`
_Theory of Mind — Step A.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/theory_of_mind.py#L97) |
| function | `_connect` | `()` | — | [src](../../../core/services/theory_of_mind.py#L123) |
| function | `_normalize_to_key` | `(text)` | Build a stable dedupe key from a sentence. | [src](../../../core/services/theory_of_mind.py#L133) |
| function | `_split_factual_sentences` | `(text)` | Return sentences from text that look like factual claims. | [src](../../../core/services/theory_of_mind.py#L149) |
| function | `record_fact` | `(*, partner_id, origin, fact_summary, session_id=…, message_id=…, evidence=…)` | Upsert a fact into the ledger. | [src](../../../core/services/theory_of_mind.py#L168) |
| function | `record_message` | `(*, role, content, partner_id=…, session_id=…, message_id=…)` | Extract factual sentences from a message and record each one. | [src](../../../core/services/theory_of_mind.py#L235) |
| function | `recent_facts` | `(*, partner_id=…, origin=…, hours=…, limit=…)` | — | [src](../../../core/services/theory_of_mind.py#L272) |
| function | `has_been_told` | `(fact_text, *, partner_id=…, hours=…)` | Has Jarvis told partner this fact within the time window? | [src](../../../core/services/theory_of_mind.py#L298) |
| function | `repetition_warnings` | `(*, partner_id=…, hours=…, threshold=…)` | Facts Jarvis has repeated to partner at or above threshold within window. | [src](../../../core/services/theory_of_mind.py#L323) |
| function | `communication_ledger_section` | `(*, partner_id=…)` | Quiet by default. Surfaces only when Jarvis is repeating himself. | [src](../../../core/services/theory_of_mind.py#L349) |
| function | `_listener_loop` | `()` | Poll events table for channel.chat_message_appended events. | [src](../../../core/services/theory_of_mind.py#L376) |
| function | `start_theory_of_mind_tracker` | `()` | Start the DB-polling listener. Idempotent. | [src](../../../core/services/theory_of_mind.py#L440) |
| function | `stop_theory_of_mind_tracker` | `()` | — | [src](../../../core/services/theory_of_mind.py#L457) |

## `core/services/theory_of_mind_engine.py`
_Active theory-of-mind engine for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_theory_of_mind_surface` | `(*, user_message=…, assistant_text=…, user_id=…)` | Build active social hypotheses and response policy. | [src](../../../core/services/theory_of_mind_engine.py#L20) |
| function | `build_theory_of_mind_prompt_section` | `(*, user_message=…, assistant_text=…, user_id=…)` | — | [src](../../../core/services/theory_of_mind_engine.py#L53) |
| function | `record_theory_of_mind_update` | `(*, user_message=…, assistant_text=…, outcome_status=…, source_run_id=…, user_id=…)` | Persist a lightweight outcome update for future hypotheses. | [src](../../../core/services/theory_of_mind_engine.py#L84) |
| function | `_load_state` | `()` | — | [src](../../../core/services/theory_of_mind_engine.py#L135) |
| function | `_safe_user_model` | `(agent_id)` | — | [src](../../../core/services/theory_of_mind_engine.py#L142) |
| function | `_derive_hypotheses` | `(*, base_model, recent_updates, user_message, assistant_text)` | — | [src](../../../core/services/theory_of_mind_engine.py#L150) |
| function | `_hypothesis` | `(label, confidence, evidence, implication)` | — | [src](../../../core/services/theory_of_mind_engine.py#L214) |
| function | `_derive_response_policy` | `(*, hypotheses, user_message)` | — | [src](../../../core/services/theory_of_mind_engine.py#L225) |
| function | `_derive_uncertainty` | `(*, hypotheses, user_message)` | — | [src](../../../core/services/theory_of_mind_engine.py#L252) |
| function | `_summary` | `(*, hypotheses, policy)` | — | [src](../../../core/services/theory_of_mind_engine.py#L263) |

## `core/services/thought_action_proposal_daemon.py`
_Thought-action proposal daemon — turns action impulses in thought stream into MC proposals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_proposals` | `()` | — | [src](../../../core/services/thought_action_proposal_daemon.py#L26) |
| function | `tick_thought_action_proposal_daemon` | `(fragment)` | Classify fragment and create a proposal if an action impulse is detected. | [src](../../../core/services/thought_action_proposal_daemon.py#L35) |
| function | `resolve_proposal` | `(proposal_id, decision)` | Move a proposal from pending to resolved. decision: 'approved' | 'dismissed'. | [src](../../../core/services/thought_action_proposal_daemon.py#L114) |
| function | `get_pending_proposals` | `()` | — | [src](../../../core/services/thought_action_proposal_daemon.py#L138) |
| function | `build_proposal_surface` | `()` | — | [src](../../../core/services/thought_action_proposal_daemon.py#L142) |

## `core/services/thought_stream_daemon.py`
_Thought stream daemon — continuous associative fragment stream for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/thought_stream_daemon.py#L20) |
| function | `tick_thought_stream_daemon` | `(energy_level=…, inner_voice_mode=…, *, skip_event_gate=…)` | — | [src](../../../core/services/thought_stream_daemon.py#L28) |
| function | `_gather_concrete_priors` | `()` | Pull a few specific recent things so the fragment has material to drift | [src](../../../core/services/thought_stream_daemon.py#L69) |
| function | `_generate_fragment` | `(energy_level, previous_fragment, inner_voice_mode=…)` | — | [src](../../../core/services/thought_stream_daemon.py#L104) |
| function | `_store_fragment` | `(fragment)` | — | [src](../../../core/services/thought_stream_daemon.py#L142) |
| function | `get_latest_thought_fragment` | `()` | — | [src](../../../core/services/thought_stream_daemon.py#L175) |
| function | `inject_rediscovery_fragment` | `(summary)` | Inject a re-discovered memory as a thought fragment. | [src](../../../core/services/thought_stream_daemon.py#L179) |
| function | `build_thought_stream_surface` | `()` | — | [src](../../../core/services/thought_stream_daemon.py#L189) |

## `core/services/thought_thread.py`
_Thought Thread — continuity of attention across ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_ts` | `(value)` | — | [src](../../../core/services/thought_thread.py#L57) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/thought_thread.py#L66) |
| function | `_recent_thoughts` | `()` | Pull recent private-brain records that represent inner thinking. | [src](../../../core/services/thought_thread.py#L74) |
| function | `_find_thread` | `(thoughts)` | Identify the dominant theme across recent thoughts via keyword overlap. | [src](../../../core/services/thought_thread.py#L103) |
| function | `get_current_thread` | `()` | Return cached thread state, recomputing only periodically. | [src](../../../core/services/thought_thread.py#L171) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — no heavy work, just trigger recompute when due. | [src](../../../core/services/thought_thread.py#L187) |
| function | `build_thought_thread_surface` | `()` | — | [src](../../../core/services/thought_thread.py#L192) |
| function | `_surface_summary` | `(thread)` | — | [src](../../../core/services/thought_thread.py#L216) |
| function | `build_thought_thread_prompt_section` | `()` | Tell him what thread he was holding before this turn. | [src](../../../core/services/thought_thread.py#L227) |
| function | `reset_thought_thread` | `()` | Reset cached state (for testing). | [src](../../../core/services/thought_thread.py#L249) |
| function | `_emit_thought_thread_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/thought_thread.py#L256) |

## `core/services/tick_cache.py`
_Tick-scoped in-memory cache — lives exactly one heartbeat tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_tick` | `()` | Activate cache for this tick. Resets any previous data. | [src](../../../core/services/tick_cache.py#L14) |
| function | `end_tick` | `()` | Deactivate cache and clear all data. | [src](../../../core/services/tick_cache.py#L22) |
| function | `get` | `(key)` | Return cached value or None. Safe to call when inactive. | [src](../../../core/services/tick_cache.py#L30) |
| function | `set` | `(key, value)` | Store value for this tick. No-op when inactive. | [src](../../../core/services/tick_cache.py#L43) |
| function | `get_tick_cache_stats` | `()` | Return hit/miss stats for current tick. | [src](../../../core/services/tick_cache.py#L50) |

## `core/services/tiktok_content_daemon.py`
_TikTok content daemon — autonomous 3x/day video generation and upload._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tiktok_setting` | `(key, fallback=…)` | Load a TikTok setting from runtime config. | [src](../../../core/services/tiktok_content_daemon.py#L83) |
| function | `tick_tiktok_content_daemon` | `()` | Main tick — generate and upload a TikTok video for the current time slot. | [src](../../../core/services/tiktok_content_daemon.py#L138) |
| function | `_detect_slot` | `(hour)` | Return slot name for the given UTC hour, or None if outside windows. | [src](../../../core/services/tiktok_content_daemon.py#L292) |
| function | `_generate_quote` | `(slot)` | Generate a quote/line for the slot via LLM. Returns fallback on failure. | [src](../../../core/services/tiktok_content_daemon.py#L300) |
| function | `_get_source_image` | `(slot)` | Return path to a source image for the slot. | [src](../../../core/services/tiktok_content_daemon.py#L316) |
| function | `_generate_flux_image` | `(slot)` | Generate a high-quality image via pollinations.ai flux model (free API). | [src](../../../core/services/tiktok_content_daemon.py#L339) |
| function | `_generate_sdxl_image` | `(slot)` | Generate a unique image for the slot via ComfyUI SDXL (fallback). | [src](../../../core/services/tiktok_content_daemon.py#L402) |
| function | `_create_solid_image` | `(slot)` | Create a 1080x1920 solid color PNG using PIL. Returns path or None. | [src](../../../core/services/tiktok_content_daemon.py#L437) |
| function | `_do_upload` | `(video_path, title)` | Upload via _exec_tiktok_upload. Returns result dict. | [src](../../../core/services/tiktok_content_daemon.py#L454) |
| function | `_refill_pool` | `(slot_type=…)` | Auto-refill the pool with fresh LLM-generated concepts when running low. | [src](../../../core/services/tiktok_content_daemon.py#L470) |
| function | `_count_unused` | `(pool, slot_type)` | Count how many unused concepts of a given type remain in the pool. | [src](../../../core/services/tiktok_content_daemon.py#L545) |
| function | `_get_concept_from_pool` | `(slot_type)` | Read pool file and return (text, hashtags) for the first unused concept of slot_type. | [src](../../../core/services/tiktok_content_daemon.py#L550) |

## `core/services/tiktok_research_daemon.py`
_TikTok research daemon — daily content concept pool generator._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_tiktok_research_daemon` | `()` | Daily tick — generate content concepts and write to pool file. | [src](../../../core/services/tiktok_research_daemon.py#L75) |
| function | `_load_pool` | `()` | Load the pool JSON from disk. Returns empty dict if missing or corrupt. | [src](../../../core/services/tiktok_research_daemon.py#L155) |
| function | `_generate_concepts_for_type` | `(slot_type)` | Call LLM to generate 3 concepts for the given slot type. | [src](../../../core/services/tiktok_research_daemon.py#L165) |
| function | `_parse_json_array` | `(text)` | Try to parse a JSON array from LLM output. Returns None on failure. | [src](../../../core/services/tiktok_research_daemon.py#L198) |

