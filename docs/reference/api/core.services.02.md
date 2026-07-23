# `core.services.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/ambient_sound_daemon.py`
_Ambient Sound daemon — Layer 6½: background acoustic context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_ambient_sound_daemon` | `()` | Sample ambient audio level and classify. Runs 4x/day. | [src](../../../core/services/ambient_sound_daemon.py#L44) |
| function | `_capture_sample` | `()` | Record 10 seconds of audio, classify, save to temp WAV. | [src](../../../core/services/ambient_sound_daemon.py#L117) |
| function | `_save_wav` | `(samples)` | Write float32 mono samples to a temp 16-bit PCM WAV. Returns path or None. | [src](../../../core/services/ambient_sound_daemon.py#L150) |
| function | `_transcribe_sample` | `(wav_path)` | Transcribe a WAV via HF Whisper. Returns empty string on failure. | [src](../../../core/services/ambient_sound_daemon.py#L169) |
| function | `_ambient_transcribe_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L184) |
| function | `_classify` | `(mean, std, peak=…)` | Classify amplitude stats into acoustic category. No content analysis. | [src](../../../core/services/ambient_sound_daemon.py#L193) |
| function | `_store_sample` | `(sample, now)` | — | [src](../../../core/services/ambient_sound_daemon.py#L221) |
| function | `_archive_sensory` | `(sample, now)` | Mirror every ambient sample into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/ambient_sound_daemon.py#L262) |
| function | `get_latest_ambient_sound_for_prompt` | `()` | Return a nuanced description of recent ambient sound for prompt injection. | [src](../../../core/services/ambient_sound_daemon.py#L294) |
| function | `build_ambient_sound_surface` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L331) |
| function | `_interpret_sound` | `(*, category, amplitude_mean, amplitude_std, now)` | Generate a nuanced Danish description from acoustic metadata via LLM. | [src](../../../core/services/ambient_sound_daemon.py#L368) |
| function | `_experiment_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L395) |
| function | `count_music_samples_last_hours` | `(hours=…)` | Return (music_count, total_count) for samples in the last `hours` hours. | [src](../../../core/services/ambient_sound_daemon.py#L404) |
| function | `_select_music_influence_phrase` | `(*, ratio)` | 3-tier rotating phrase based on music-to-total ratio. | [src](../../../core/services/ambient_sound_daemon.py#L441) |
| function | `get_music_accumulator_for_prompt` | `()` | Return prompt fragment if music threshold met, else empty string. | [src](../../../core/services/ambient_sound_daemon.py#L453) |
| function | `_state` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L476) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/ambient_sound_daemon.py#L481) |

## `core/services/anthropic_identity.py`
_Build Jarvis identity prefix from a workspace directory._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_signature` | `(workspace_dir)` | — | [src](../../../core/services/anthropic_identity.py#L20) |
| function | `build_identity_prefix` | `(workspace_dir)` | Return concatenated identity files for this workspace, or empty string. | [src](../../../core/services/anthropic_identity.py#L32) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/anthropic_identity.py#L62) |

## `core/services/anthropic_sse_emitter.py`
_Anthropic Messages API SSE state machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AnthropicSSEEmitter` | `` | Stateful emitter for one streamed message. | [src](../../../core/services/anthropic_sse_emitter.py#L13) |
| method | `AnthropicSSEEmitter.__init__` | `(self, *, message_id, model)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L25) |
| method | `AnthropicSSEEmitter._format` | `(event, data)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L35) |
| method | `AnthropicSSEEmitter.begin_message` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L38) |
| method | `AnthropicSSEEmitter._close_open_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L56) |
| method | `AnthropicSSEEmitter._open_text_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L67) |
| method | `AnthropicSSEEmitter.text_delta` | `(self, text)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L78) |
| method | `AnthropicSSEEmitter.tool_use_start` | `(self, tool_call_id, name)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L90) |
| method | `AnthropicSSEEmitter.tool_use_input_delta` | `(self, partial_json)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L107) |
| method | `AnthropicSSEEmitter.tool_result_block` | `(self, *, tool_use_id, status, content, is_error=…)` | Emit et første-klasses tool_result som content-blok (kanonisk wire-form). | [src](../../../core/services/anthropic_sse_emitter.py#L116) |
| method | `AnthropicSSEEmitter.end_message` | `(self, *, stop_reason, output_tokens=…)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L137) |
| method | `AnthropicSSEEmitter.ping` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L149) |
| method | `AnthropicSSEEmitter.error` | `(self, message)` | Emit a graceful error: close any open block, emit error stop. | [src](../../../core/services/anthropic_sse_emitter.py#L152) |

## `core/services/anthropic_translator.py`
_Translate between Anthropic Messages API format and Ollama /api/chat format._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `translate_request_to_ollama` | `(anthropic_body, *, identity_prefix, backend_model)` | Build an Ollama /api/chat payload from an Anthropic Messages request. | [src](../../../core/services/anthropic_translator.py#L13) |
| function | `_translate_message` | `(msg)` | Translate a single Anthropic message into 1-N Ollama messages. | [src](../../../core/services/anthropic_translator.py#L61) |
| function | `_stringify_tool_result_content` | `(content)` | Anthropic tool_result content can be string or list of blocks. | [src](../../../core/services/anthropic_translator.py#L130) |
| function | `drive_emitter_from_ollama_chunks` | `(emitter, chunks)` | Drive an AnthropicSSEEmitter from a stream of Ollama chat chunks. | [src](../../../core/services/anthropic_translator.py#L153) |
| function | `build_non_streaming_response` | `(*, message_id, model, text, tool_calls)` | Build the final Anthropic Messages response (non-streaming). | [src](../../../core/services/anthropic_translator.py#L200) |

## `core/services/anticipatory_action_daemon.py`
_Anticipatory Action Daemon — predict + pre-act._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L39) |
| function | `_load` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L43) |
| function | `_save` | `(data)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L60) |
| function | `_should_recompute` | `(data, now)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L72) |
| function | `_gather_contact_hours` | `()` | Collect contact hours from recent visible runs. | [src](../../../core/services/anticipatory_action_daemon.py#L83) |
| function | `_compute_peak_hours` | `(hour_counts)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L104) |
| function | `recompute_patterns` | `()` | Rebuild pattern signature from recent data. | [src](../../../core/services/anticipatory_action_daemon.py#L129) |
| function | `_local_now` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L141) |
| function | `_minutes_until_hour` | `(now_local, target_hour)` | Returns minutes until next occurrence of target_hour (always in [0, 1440)). | [src](../../../core/services/anticipatory_action_daemon.py#L146) |
| function | `_maybe_emit_anticipation` | `(peaks)` | Emit signals for peaks coming up within the anticipation window. | [src](../../../core/services/anticipatory_action_daemon.py#L156) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L184) |
| function | `build_anticipatory_action_surface` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L196) |
| function | `_surface_summary` | `(peaks, upcoming)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L223) |
| function | `build_anticipatory_action_prompt_section` | `()` | Surface imminent anticipated contact. | [src](../../../core/services/anticipatory_action_daemon.py#L235) |

## `core/services/anticipatory_context.py`
_Anticipatory Context — predict what the user will likely ask about next._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `predict_next_context` | `(*, recent_topics=…, hour=…, idle_hours=…, last_session_topic=…)` | Predict the most likely next context. | [src](../../../core/services/anticipatory_context.py#L17) |
| function | `build_anticipatory_context_surface` | `()` | — | [src](../../../core/services/anticipatory_context.py#L76) |

## `core/services/api_connection_nerve.py`
_API-forbindelses-nerve — Jarvis mærker hvem/hvad der forbinder til hans API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/api_connection_nerve.py#L41) |
| function | `record` | `(*, ip, method, path, status, latency_ms, user_id=…, session_id=…, error=…)` | Registrér én API-request (metadata-only). Billig, låst, kaster ALDRIG. | [src](../../../core/services/api_connection_nerve.py#L45) |
| function | `_maybe_flush_async` | `()` | Throttlet baggrunds-flush (api-proces ejer bufferen). Spawner en daemon-tråd så request- | [src](../../../core/services/api_connection_nerve.py#L99) |
| function | `_drain` | `()` | Snapshot dirty presence-deltas + log-buffer under lås; nulstil buffer + dirty-flag. | [src](../../../core/services/api_connection_nerve.py#L129) |
| function | `flush` | `()` | Batch-flush presence + log til DB (cadence). Self-safe. | [src](../../../core/services/api_connection_nerve.py#L147) |
| function | `retention_sweep` | `()` | GDPR-retention (cadence): anonymisér IP > 48t → /24, slet gammel log, prune presence. | [src](../../../core/services/api_connection_nerve.py#L158) |
| function | `presence_view` | `(*, active_within_s=…, limit=…)` | Hvem er forbundet til API'et? Fletter live in-memory + persistent DB. Self-safe. | [src](../../../core/services/api_connection_nerve.py#L166) |

## `core/services/apophenia_guard.py`
_Apophenia Guard — pattern skeptic that validates before elevation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_generate_assessment_rationale` | `(*, status, observation_count, adjusted_confidence, competitor_count, confounder_count)` | Generate a brief Danish explanation of the assessment. Falls back to empty string. | [src](../../../core/services/apophenia_guard.py#L21) |
| function | `assess_pattern` | `(*, observation_count, base_confidence, competing_explanations=…, confounders=…, include_rationale=…)` | Assess whether a pattern should be elevated or rejected. | [src](../../../core/services/apophenia_guard.py#L48) |
| function | `build_apophenia_guard_surface` | `()` | — | [src](../../../core/services/apophenia_guard.py#L120) |

## `core/services/app_dispatch_store.py`
_Pending runtime→app instruktioner (spec §18.5, Fase 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/app_dispatch_store.py#L24) |
| function | `_save` | `(items)` | — | [src](../../../core/services/app_dispatch_store.py#L29) |
| function | `enqueue` | `(instruction)` | Validér + kø en app-instruktion. Returnerer record (med id/created_at) eller | [src](../../../core/services/app_dispatch_store.py#L33) |
| function | `list_pending` | `()` | Uafgjorte instruktioner i kø-rækkefølge (desk poller). | [src](../../../core/services/app_dispatch_store.py#L58) |
| function | `ack` | `(dispatch_id)` | Markér en instruktion som udført (consumeret af desk). | [src](../../../core/services/app_dispatch_store.py#L63) |

## `core/services/approval_feedback_subscriber.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L19) |
| function | `stop_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L36) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/approval_feedback_subscriber.py#L49) |

## `core/services/arc_rule_extractor.py`
_Arc rule extractor — turns narrative arcs into actionable rules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rules_path` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L33) |
| function | `_arcs_dir` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L39) |
| function | `_build_extraction_prompt` | `(arc_text, period)` | — | [src](../../../core/services/arc_rule_extractor.py#L43) |
| function | `_parse_rules` | `(text)` | — | [src](../../../core/services/arc_rule_extractor.py#L59) |
| function | `extract_rules_from_arc` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L74) |
| function | `_mark_processed` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L128) |
| function | `_is_processed` | `(arc_name)` | — | [src](../../../core/services/arc_rule_extractor.py#L141) |
| function | `extract_rules_for_unprocessed_arcs` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L151) |
| function | `arc_rules_section` | `(*, max_lines=…)` | Render most recent extracted rules as prompt awareness section. | [src](../../../core/services/arc_rule_extractor.py#L170) |

## `core/services/assembly_prewarm.py`
_core/services/assembly_prewarm.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_max_created_at_real_deepseek` | `()` | Epoch seconds of the most recent NON-warmer deepseek call in costs. None if none. | [src](../../../core/services/assembly_prewarm.py#L36) |
| function | `_seconds_since_last_real_deepseek_call` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L54) |
| function | `_max_created_at_visible` | `()` | Epoch-sek. for seneste ÆGTE bruger↔Jarvis-aktivitet (visible-lanen). None hvis | [src](../../../core/services/assembly_prewarm.py#L59) |
| function | `_seconds_since_last_user_activity` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L76) |
| function | `_idle_window_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L85) |
| function | `is_prewarm_active` | `()` | True hvis den aktuelle tråd i øjeblikket kører en pre-warm-build. Self-safe. | [src](../../../core/services/assembly_prewarm.py#L109) |
| function | `assembly_prewarm_enabled` | `()` | Kill-switch. Default OFF (shadow) — flip via runtime-state. Self-safe → False. | [src](../../../core/services/assembly_prewarm.py#L114) |
| function | `_interval_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L124) |
| function | `_skip_if_recent_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L138) |
| function | `_seconds_since_last_prewarm` | `()` | Cross-process: seconds since ANY process last prewarmed. None if never. | [src](../../../core/services/assembly_prewarm.py#L147) |
| function | `_mark_prewarmed` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L157) |
| function | `_should_prewarm` | `()` | Event-drevet gate (15. jul — dræber 292M-tokens/13d-burnet). Warm KUN når det | [src](../../../core/services/assembly_prewarm.py#L165) |
| function | `_try_acquire_prewarm_lease` | `(interval_s)` | Atomisk cross-process: kun ÉN proces vinder retten til at warme pr. interval. | [src](../../../core/services/assembly_prewarm.py#L186) |
| function | `_record_stats` | `(elapsed_s, error=…)` | — | [src](../../../core/services/assembly_prewarm.py#L205) |
| function | `prewarm_once` | `()` | Byg én throwaway-assembly for at varme alle sektions-caches. Returnerer | [src](../../../core/services/assembly_prewarm.py#L220) |
| function | `_loop` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L250) |
| function | `start_prewarm_loop` | `()` | Start baggrunds-pre-warm-loopet én gang pr. proces. Idempotent. Loopet kører | [src](../../../core/services/assembly_prewarm.py#L266) |

## `core/services/associative_recall.py`
_Associative Recall — dormant memories triggered by context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_strong_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L47) |
| function | `_get_weak_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L55) |
| function | `_get_max_active` | `()` | — | [src](../../../core/services/associative_recall.py#L63) |
| function | `_get_repetition_multiplier` | `()` | — | [src](../../../core/services/associative_recall.py#L71) |
| function | `_ensure_active_memories_table` | `()` | Create recall_active_memories table if it doesn't exist (lazy init). | [src](../../../core/services/associative_recall.py#L83) |
| function | `_persist_active_memory` | `(memory)` | Save an active memory to DB (upsert). | [src](../../../core/services/associative_recall.py#L108) |
| function | `_remove_persisted_memory` | `(memory_id)` | Remove a memory from the DB persistence table. | [src](../../../core/services/associative_recall.py#L133) |
| function | `_load_active_memories_from_db` | `()` | Restore active memories from DB on module load. | [src](../../../core/services/associative_recall.py#L148) |
| function | `_clear_persisted_memories` | `()` | Remove all active memories from DB. | [src](../../../core/services/associative_recall.py#L177) |
| function | `recall_for_session` | `(session_context)` | Run associative recall at session start. Populates up to 3 active memories. | [src](../../../core/services/associative_recall.py#L196) |
| function | `_observe_assoc_recall` | `(memories)` | Fase 3 (§23.3 #4): meld recall-KVALITET til Centralen — KUN scalar-metadata, aldrig | [src](../../../core/services/associative_recall.py#L252) |
| function | `recall_for_message` | `(message_text, emotional_state)` | Run associative recall for a user message. Adds up to 2 active memories. | [src](../../../core/services/associative_recall.py#L282) |
| function | `build_recall_prompt_section` | `()` | Format active memories as [ASSOCIATIONER] awareness section (Danish, compact). | [src](../../../core/services/associative_recall.py#L369) |
| function | `apply_weak_recall_to_emotions` | `(memories)` | Trigger emotion concepts from weak-scoring memories. | [src](../../../core/services/associative_recall.py#L391) |
| function | `clear_session_recall` | `()` | Reset all active memories and topic history. Call at session end. | [src](../../../core/services/associative_recall.py#L422) |
| function | `_add_to_active` | `(memory)` | Add memory to active set. Evicts weakest if at cap. Persists to DB. | [src](../../../core/services/associative_recall.py#L435) |
| function | `_record_topic` | `(topic)` | Record a topic in the sliding window history. | [src](../../../core/services/associative_recall.py#L449) |
| function | `_get_topic_multiplier` | `(topic)` | Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0. | [src](../../../core/services/associative_recall.py#L454) |
| function | `_extract_keywords_llm` | `(text)` | Extract keywords via cheap-lane LLM. Returns empty list on failure. | [src](../../../core/services/associative_recall.py#L467) |
| function | `_extract_keywords_regex` | `(text)` | Regex fallback: capitalized words, technical terms, named entities. | [src](../../../core/services/associative_recall.py#L492) |
| function | `_extract_topic_hint` | `(text)` | Extract topic hints: LLM first, regex fallback, then simple fallback. | [src](../../../core/services/associative_recall.py#L522) |
| function | `_add_private_brain_candidates` | `(candidates, topic_hint, limit=…)` | Add private brain records as recall candidates. | [src](../../../core/services/associative_recall.py#L565) |
| function | `_add_sensory_candidates` | `(candidates, topic_hint, limit=…)` | Add recent sensory memories as recall candidates. | [src](../../../core/services/associative_recall.py#L597) |
| function | `_build_session_context_text` | `(session_context)` | Build a context description string for session-level scoring. | [src](../../../core/services/associative_recall.py#L629) |
| function | `build_associative_recall_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/associative_recall.py#L641) |
| function | `tick_associative_recall` | `()` | Heartbeat daemon tick — decay + periodic candidate scan. | [src](../../../core/services/associative_recall.py#L664) |

## `core/services/attachment_service.py`
_attachment_service — download, store, and read channel attachments._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_http_download` | `(url, headers)` | — | [src](../../../core/services/attachment_service.py#L45) |
| function | `_db_store` | `(*, attachment_id, session_id, channel_type, filename, mime_type, size_bytes, local_path, source_url)` | — | [src](../../../core/services/attachment_service.py#L54) |
| function | `_db_get` | `(attachment_id)` | — | [src](../../../core/services/attachment_service.py#L86) |
| function | `_db_list` | `(session_id, limit)` | — | [src](../../../core/services/attachment_service.py#L97) |
| function | `list_image_attachments` | `(*, user_id=…, limit=…)` | List billed-attachments på tværs af sessioner til galleriet (#6). | [src](../../../core/services/attachment_service.py#L108) |
| function | `attachment_visible_to_user` | `(attachment_id, user_id)` | Privacy-cluster GENNEM Centralen (observe): cross-user attachment-adgangs-beslutning | [src](../../../core/services/attachment_service.py#L146) |
| function | `_attachment_visible_to_user_impl` | `(attachment_id, user_id)` | Må denne bruger se attachment'et? user_id tom → ja (owner/legacy). | [src](../../../core/services/attachment_service.py#L162) |
| function | `_call_vision` | `(image_b64, *, model, prompt=…)` | — | [src](../../../core/services/attachment_service.py#L183) |
| function | `_vision_model` | `()` | — | [src](../../../core/services/attachment_service.py#L188) |
| function | `download_and_store` | `(*, url, filename, mime_type, size_bytes, session_id, channel_type, http_headers=…)` | Download file from URL and persist to uploads/ + DB. | [src](../../../core/services/attachment_service.py#L210) |
| function | `get_attachment` | `(attachment_id)` | Return attachment metadata dict, or None if not found. | [src](../../../core/services/attachment_service.py#L275) |
| function | `list_attachments` | `(session_id, limit=…)` | Return recent attachments for session, newest first. | [src](../../../core/services/attachment_service.py#L283) |
| function | `read_attachment_content` | `(attachment_id)` | Read attachment content for Jarvis. | [src](../../../core/services/attachment_service.py#L291) |
| function | `validate_send_path` | `(path)` | Return (ok, error_message) for outbound file send. | [src](../../../core/services/attachment_service.py#L371) |

## `core/services/attachment_topology_signal_tracking.py`
_Attachment-topology signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_attachment_topology_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L44) |
| function | `refresh_runtime_attachment_topology_signal_statuses` | `()` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L81) |
| function | `build_runtime_attachment_topology_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L85) |
| function | `_extract_attachment_topology_candidates` | `(*, run_id)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L89) |
| function | `_build_candidate` | `(*, domain_key, relation_continuity, meaning, witness, chronicle_brief, metabolism, self_narrative, temperament, forgetting_candidate)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L181) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L283) |
| function | `_attachment_topology_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L305) |
| function | `_derive_attachment_weight` | `(*, relation_weight, meaning_weight, witness_status, witness_persistence, brief_weight, metabolism_weight, narrative_weight, temperament_weight, forgetting_state)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L327) |
| function | `_derive_attachment_state` | `(*, weight, witness_status, metabolism_state)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L363) |
| function | `_attachment_summary` | `(*, focus, attachment_state, attachment_weight, forgetting_candidate)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L371) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L399) |
| function | `_humanize_focus` | `(value)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L406) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L411) |
| function | `_find_support_value` | `(summary, key, default=…)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L431) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L443) |

## `core/services/attention_blink_test.py`
_Attention Blink Test — capacity-limit measurement (Experiment 5: Serial consciousness)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_attention_blink_test_if_due` | `()` | Check cadence gate and launch test in background thread if due. | [src](../../../core/services/attention_blink_test.py#L33) |
| function | `build_attention_profile_surface` | `()` | MC surface for attention blink experiment. | [src](../../../core/services/attention_blink_test.py#L52) |
| function | `_run_test_body` | `()` | Full test: measure T1, inject T1 burst, wait 30s, inject T2, compare. | [src](../../../core/services/attention_blink_test.py#L87) |
| function | `_compute_blink_ratio` | `(t1, t2)` | T2 total intensity / T1 total intensity. Clamped 0-2. | [src](../../../core/services/attention_blink_test.py#L142) |
| function | `_interpret_blink_ratio` | `(ratio)` | < 0.7 → serial/blink-prone, >= 0.7 → parallel/blink-resistant. | [src](../../../core/services/attention_blink_test.py#L151) |

## `core/services/attention_budget.py`
_Adaptive attention economy — bounded context budgeting for prompt assembly._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SectionBudget` | `` | Budget for a single prompt section. | [src](../../../core/services/attention_budget.py#L23) |
| class | `AttentionBudget` | `` | Complete attention budget for a prompt assembly path. | [src](../../../core/services/attention_budget.py#L32) |
| function | `get_attention_budget` | `(profile)` | Get a named attention budget profile. | [src](../../../core/services/attention_budget.py#L102) |
| class | `SectionResult` | `` | Result of attempting to include a section under budget. | [src](../../../core/services/attention_budget.py#L112) |
| class | `AttentionTrace` | `` | Observable trace of what was included/omitted and why. | [src](../../../core/services/attention_budget.py#L123) |
| method | `AttentionTrace.included_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L137) |
| method | `AttentionTrace.omitted_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L141) |
| method | `AttentionTrace.trimmed_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L145) |
| method | `AttentionTrace.summary` | `(self)` | — | [src](../../../core/services/attention_budget.py#L148) |
| function | `apply_section_budget` | `(*, name, content, budget)` | Apply a section budget to content. | [src](../../../core/services/attention_budget.py#L175) |
| function | `build_micro_cognitive_frame` | `()` | Build a ~150 char micro cognitive frame for compact visible prompts. | [src](../../../core/services/attention_budget.py#L235) |
| function | `select_sections_under_budget` | `(*, budget, sections)` | Select and trim sections to fit within the attention budget. | [src](../../../core/services/attention_budget.py#L279) |
| function | `build_attention_budget_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/attention_budget.py#L361) |

## `core/services/attention_contour.py`
_Attention Contour — shape of attention._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_attention_shape` | `()` | — | [src](../../../core/services/attention_contour.py#L10) |
| function | `describe_attention` | `()` | — | [src](../../../core/services/attention_contour.py#L13) |
| function | `format_attention_for_prompt` | `()` | — | [src](../../../core/services/attention_contour.py#L17) |
| function | `build_attention_contour_surface` | `()` | — | [src](../../../core/services/attention_contour.py#L20) |

## `core/services/auth_profile_scan.py`
_Shared scanner for multi-profile provider auth slots._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_account_profile` | `(profile)` | True only for real account profiles (default, account2, account3, …). | [src](../../../core/services/auth_profile_scan.py#L41) |
| function | `clear_cache` | `()` | Drop all cached scan results (test helper / manual invalidation). | [src](../../../core/services/auth_profile_scan.py#L51) |
| function | `_profiles_root` | `()` | Return the auth/profiles directory (honoring JARVIS_CONFIG_DIR). | [src](../../../core/services/auth_profile_scan.py#L56) |
| function | `_is_keyless` | `(provider)` | True if the provider needs no per-profile credentials. | [src](../../../core/services/auth_profile_scan.py#L63) |
| function | `_sort_default_first` | `(profiles)` | — | [src](../../../core/services/auth_profile_scan.py#L75) |
| function | `ready_profiles_for` | `(provider)` | Return profiles with ready credentials for ``provider``. | [src](../../../core/services/auth_profile_scan.py#L80) |

## `core/services/auto_code_review.py`
_Auto code-review heuristic for git-commit proposals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_diff_stats` | `(repo, files)` | Return per-file added/removed line counts for the staged or unstaged diff. | [src](../../../core/services/auto_code_review.py#L36) |
| function | `_scope_for_path` | `(p)` | — | [src](../../../core/services/auto_code_review.py#L72) |
| function | `review_pending_commit` | `(*, repo_root, files, message, rationale)` | — | [src](../../../core/services/auto_code_review.py#L77) |
| function | `review_pending_commit_gated` | `(**kwargs)` | Som review_pending_commit, men GOVERNET af Centralen (COGNITIVE, cluster='commit') | [src](../../../core/services/auto_code_review.py#L168) |

## `core/services/auto_improvement_proposer.py`
_Auto improvement proposer — close the self-improvement loop SAFELY._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_safe_target` | `(target)` | Reject only infrastructure-protected modules. Identity files now allowed | [src](../../../core/services/auto_improvement_proposer.py#L47) |
| function | `_check_tick_quality_degraded` | `()` | Returns proposal payload if tick quality is degrading. | [src](../../../core/services/auto_improvement_proposer.py#L58) |
| function | `_check_stale_goals` | `()` | Returns proposal payload if stale goals exist. | [src](../../../core/services/auto_improvement_proposer.py#L86) |
| function | `_check_decision_adherence` | `()` | — | [src](../../../core/services/auto_improvement_proposer.py#L113) |
| function | `_check_provider_health_chronic` | `()` | If a provider is chronically down (>30 min), propose explicit demotion. | [src](../../../core/services/auto_improvement_proposer.py#L140) |
| function | `generate_improvement_proposals` | `(*, session_id=…)` | Run all checks, file plans for any that fire. | [src](../../../core/services/auto_improvement_proposer.py#L169) |
| function | `_exec_generate_improvement_proposals` | `(args)` | — | [src](../../../core/services/auto_improvement_proposer.py#L232) |

## `core/services/auto_remember_subscriber.py`
_Auto-remember subscriber — closes cross-session memory loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_SkipMemoryShadow` | `` | Sentinel: spring den valgfrie memory_write_policy-shadow over (ingen brugerkontekst). | [src](../../../core/services/auto_remember_subscriber.py#L43) |
| function | `_is_trivial_user_turn` | `(text)` | True hvis user-beskeden er en ren acknowledgment uden nyt indhold. | [src](../../../core/services/auto_remember_subscriber.py#L75) |
| function | `_is_trivial_assistant_turn` | `(text)` | True hvis assistant-svaret er en kort acknowledgment uden indhold. | [src](../../../core/services/auto_remember_subscriber.py#L94) |
| function | `_connect` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L112) |
| function | `_parse_json_loose` | `(text)` | Find første gyldige JSON-objekt i tekst. Robust over for LLM | [src](../../../core/services/auto_remember_subscriber.py#L160) |
| function | `evaluate_turn_for_memory` | `(user_text, assistant_text)` | Spørg cheap LLM: "skal denne tur gemmes?" | [src](../../../core/services/auto_remember_subscriber.py#L191) |
| function | `_find_preceding_user_text` | `(session_id, before_message_id)` | Find seneste user-besked i session FØR den givne assistant-besked. | [src](../../../core/services/auto_remember_subscriber.py#L275) |
| function | `_process_visible_assistant_turn` | `(payload)` | Evaluér én assistant-tur og kald remember_this hvis salient. | [src](../../../core/services/auto_remember_subscriber.py#L309) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — samme pattern som metacognition_signal_tracker. | [src](../../../core/services/auto_remember_subscriber.py#L398) |
| function | `start_auto_remember_subscriber` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/auto_remember_subscriber.py#L440) |
| function | `stop_auto_remember_subscriber` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L457) |

## `core/services/automation_dsl.py`
_Automation DSL — declarative triggers → actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L33) |
| class | `ActionSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L39) |
| class | `AutomationDSL` | `` | — | [src](../../../core/services/automation_dsl.py#L47) |
| class | `AutomationDSLValidationError` | `` | — | [src](../../../core/services/automation_dsl.py#L56) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/automation_dsl.py#L67) |
| function | `_load` | `()` | — | [src](../../../core/services/automation_dsl.py#L71) |
| function | `_save` | `(items)` | — | [src](../../../core/services/automation_dsl.py#L85) |
| function | `validate_automation` | `(raw)` | Validate and construct an AutomationDSL from a raw dict. | [src](../../../core/services/automation_dsl.py#L97) |
| function | `register_automation` | `(dsl)` | Persist an AutomationDSL. Returns automation_id. | [src](../../../core/services/automation_dsl.py#L154) |
| function | `deactivate_automation` | `(automation_id)` | — | [src](../../../core/services/automation_dsl.py#L180) |
| function | `list_automations` | `(*, status=…)` | — | [src](../../../core/services/automation_dsl.py#L190) |
| function | `_expire_due` | `()` | Mark expired automations as inactive. Returns count of newly expired. | [src](../../../core/services/automation_dsl.py#L197) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — expire due automations, no other side-effects here. | [src](../../../core/services/automation_dsl.py#L222) |
| function | `build_automation_dsl_surface` | `()` | — | [src](../../../core/services/automation_dsl.py#L228) |
| function | `_emit_automation_dsl_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/automation_dsl.py#L257) |

## `core/services/autonomous_council_daemon.py`
_Autonomous Council Daemon — spontaneous self-triggered deliberation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compute_signal_score` | `(surfaces)` | Compute weighted composite score from signal surface readings. Returns 0.0–1.0. | [src](../../../core/services/autonomous_council_daemon.py#L48) |
| function | `_cadence_gate_ok` | `()` | True if at least _CADENCE_MINUTES have passed since last council start. | [src](../../../core/services/autonomous_council_daemon.py#L88) |
| function | `_cooldown_gate_ok` | `()` | True if at least _COOLDOWN_MINUTES have passed since last council conclusion. | [src](../../../core/services/autonomous_council_daemon.py#L95) |
| function | `_daily_limit_ok` | `()` | True if the large council daily cap has not been reached. | [src](../../../core/services/autonomous_council_daemon.py#L102) |
| function | `_increment_daily_count` | `()` | — | [src](../../../core/services/autonomous_council_daemon.py#L112) |
| function | `_persist_durable_counters` | `()` | — | [src](../../../core/services/autonomous_council_daemon.py#L127) |
| function | `_restore_durable_counters` | `()` | Reload cadence/daily counters from durable kv once per process start. | [src](../../../core/services/autonomous_council_daemon.py#L140) |
| function | `_consult_convene_judge` | `(*, surfaces, top_signals, score, score_override)` | Consult the Central reason-judge (AKSE 4). Returns its verdict dict, or None | [src](../../../core/services/autonomous_council_daemon.py#L178) |
| function | `_call_llm` | `(prompt)` | — | [src](../../../core/services/autonomous_council_daemon.py#L200) |
| function | `derive_topic` | `(top_signals, *, topic_hint=…)` | Ask cheap LLM to generate a council topic from the top triggering signals. | [src](../../../core/services/autonomous_council_daemon.py#L206) |
| function | `compose_members` | `(score, top_signals)` | Return list of role names for this council. | [src](../../../core/services/autonomous_council_daemon.py#L231) |
| function | `tick_autonomous_council_daemon` | `(*, score_override=…)` | Evaluate signals and trigger council if warranted. | [src](../../../core/services/autonomous_council_daemon.py#L255) |
| function | `_land_initiative` | `(*, initiative, council_id)` | Land a council initiative into the initiative queue (AKSE 2). | [src](../../../core/services/autonomous_council_daemon.py#L363) |
| function | `_read_signal_surfaces` | `()` | Read all signal surfaces and return (surfaces_dict, top_2_signal_names). | [src](../../../core/services/autonomous_council_daemon.py#L385) |
| function | `_run_autonomous_council` | `(*, topic, members)` | Create and run a council session. Returns dict with council_id and conclusion. | [src](../../../core/services/autonomous_council_daemon.py#L424) |
| function | `build_autonomous_council_surface` | `()` | — | [src](../../../core/services/autonomous_council_daemon.py#L456) |

## `core/services/autonomous_goals.py`
_Autonomous goals — persistent top-level goals with decomposition._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_goals.py#L34) |
| function | `_save` | `(goals)` | — | [src](../../../core/services/autonomous_goals.py#L41) |
| function | `_now` | `()` | — | [src](../../../core/services/autonomous_goals.py#L45) |
| function | `create_goal` | `(*, title, description=…, parent_id=…, priority=…, source=…)` | Create a new goal. Returns the created entry. | [src](../../../core/services/autonomous_goals.py#L49) |
| function | `update_goal_status` | `(goal_id, new_status)` | — | [src](../../../core/services/autonomous_goals.py#L92) |
| function | `list_goals` | `(*, status=…, priority=…, parent_id=…, limit=…)` | List goals matching filters. parent_id='any' = no filter, None = top-level only. | [src](../../../core/services/autonomous_goals.py#L113) |
| function | `decompose_goal` | `(goal_id)` | Use cheap-lane LLM to split a goal into 3-5 concrete sub-goals. | [src](../../../core/services/autonomous_goals.py#L134) |
| function | `goals_prompt_section` | `()` | Awareness section listing active high-priority goals. | [src](../../../core/services/autonomous_goals.py#L198) |
| function | `_exec_goal_create` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L215) |
| function | `_exec_goal_list` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L225) |
| function | `_exec_goal_decompose` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L235) |
| function | `_exec_goal_update_status` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L239) |

## `core/services/autonomous_lease.py`
_visible↔autonomous mutual-exclusion lease (marker-default)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `(now_ts)` | — | [src](../../../core/services/autonomous_lease.py#L37) |
| function | `acquire_visible` | `(ttl_s=…, now_ts=…)` | Visible lane claims the lease for ``ttl_s`` seconds (fail-open). | [src](../../../core/services/autonomous_lease.py#L41) |
| function | `release_visible` | `()` | Visible lane releases the lease (fail-open). | [src](../../../core/services/autonomous_lease.py#L52) |
| function | `visible_active` | `(now_ts=…)` | True if a visible lease is currently held and not expired (fail-open). | [src](../../../core/services/autonomous_lease.py#L60) |
| function | `_read_markers` | `()` | — | [src](../../../core/services/autonomous_lease.py#L75) |
| function | `_write_markers` | `(markers)` | — | [src](../../../core/services/autonomous_lease.py#L85) |
| function | `pending_markers` | `()` | Read (without draining) the deferred autonomous markers. | [src](../../../core/services/autonomous_lease.py#L92) |
| function | `consume_markers` | `()` | Read AND drain the deferred markers (a second call returns empty). | [src](../../../core/services/autonomous_lease.py#L97) |
| function | `try_autonomous_dispatch` | `(payload, now_ts=…, *, scope=…, session_id=…, control_plane=…)` | Gate an autonomous dispatch against the visible lane. | [src](../../../core/services/autonomous_lease.py#L105) |
| function | `_resolve_role` | `(user_id, role)` | Resolve the member role, preferring an explicit ``role``. | [src](../../../core/services/autonomous_lease.py#L149) |
| function | `nudge_allowed_for` | `(marker, *, user_id=…, session_id=…, role=…)` | Role- AND session-gate: may this nudge surface for this user/session? | [src](../../../core/services/autonomous_lease.py#L170) |
| function | `markers_for` | `(*, user_id=…, session_id=…, role=…, drain=…)` | Return the deferred markers this user/session/role is allowed to see. | [src](../../../core/services/autonomous_lease.py#L213) |

## `core/services/autonomous_outreach_daemon.py`
_Autonomous Outreach Daemon — Jarvis reaches out on his own initiative._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L39) |
| function | `_load_log` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L43) |
| function | `_save_log` | `(items)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L57) |
| function | `_last_outreach_sent` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L71) |
| function | `_is_quiet_hours` | `(now_local)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L81) |
| function | `_hours_since_last_user_contact` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L87) |
| function | `_gather_interesting_events` | `()` | Collect potentially noteworthy signals from other services. | [src](../../../core/services/autonomous_outreach_daemon.py#L112) |
| function | `_compose_message` | `(events)` | Build a concrete, value-carrying outreach message from events. | [src](../../../core/services/autonomous_outreach_daemon.py#L177) |
| function | `_highest_priority` | `(events)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L189) |
| function | `_log_decision` | `(*, outcome, reason, events=…, message=…, priority=…, channel=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L196) |
| function | `_owner_uid` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L218) |
| function | `_send_outreach` | `(message, *, priority=…)` | Deliver outreach via the canonical proactive router — device-aware | [src](../../../core/services/autonomous_outreach_daemon.py#L226) |
| function | `attempt_outreach` | `()` | Consider whether to reach out, do so if appropriate. Returns decision dict. | [src](../../../core/services/autonomous_outreach_daemon.py#L252) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — evaluate outreach candidacy. | [src](../../../core/services/autonomous_outreach_daemon.py#L347) |
| function | `recent_log` | `(*, limit=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L356) |
| function | `build_autonomous_outreach_surface` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L360) |
| function | `_surface_summary` | `(sent, skipped, last)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L378) |

## `core/services/autonomous_sessions.py`
_Autonome sessioner — rotér pr. oprindelse+dag, og gør historien synlig._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_origin` | `(origin)` | — | [src](../../../core/services/autonomous_sessions.py#L35) |
| function | `_today` | `()` | — | [src](../../../core/services/autonomous_sessions.py#L40) |
| function | `resolve_autonomous_session` | `(origin)` | Returnér (opret idempotent) sessionen for (oprindelse, i dag). | [src](../../../core/services/autonomous_sessions.py#L44) |
| function | `_origin_of_session` | `(session_id)` | Udled oprindelse fra et ``auto-{origin}-{dato}``-id. | [src](../../../core/services/autonomous_sessions.py#L63) |
| function | `build_autonomous_history_surface` | `(*, days=…, per_origin_limit=…)` | Projicér den autonome historie for owner-visning (§24.4-sikker). | [src](../../../core/services/autonomous_sessions.py#L73) |

## `core/services/autonomous_supervisor.py`
_Autonom run-supervision (#3) — Centralen følger HVERT autonomt run, korrelerer det på tværs_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supervise` | `(run_id, outcome, error=…)` | Vurdér ét autonomt run. outcome ∈ {completed, failed, interrupted}. Returnér verdict + | [src](../../../core/services/autonomous_supervisor.py#L23) |

## `core/services/autonomous_work_daemon.py`
_Autonomous Work Daemon — Jarvis works on his own when Bjørn is away._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L48) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L52) |
| function | `_save` | `(items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L66) |
| function | `_proposals_last_hour` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L80) |
| function | `_is_low_activity` | `()` | Low-activity = no visible runs in last _LOW_ACTIVITY_MINUTES. | [src](../../../core/services/autonomous_work_daemon.py#L96) |
| function | `_pending_initiatives` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L117) |
| function | `_log_entry` | `(entry)` | — | [src](../../../core/services/autonomous_work_daemon.py#L125) |
| function | `_file_proposal` | `(*, proposal_type, title, details, rationale)` | Record a work proposal for later execution/approval. | [src](../../../core/services/autonomous_work_daemon.py#L131) |
| function | `_maybe_propose_memory_consolidate` | `()` | Propose a daily memory consolidation when ~end of day locally. | [src](../../../core/services/autonomous_work_daemon.py#L169) |
| function | `_maybe_nudge_incubator` | `()` | If incubator is sparse, nudge creative_instinct to generate. | [src](../../../core/services/autonomous_work_daemon.py#L189) |
| function | `_maybe_propose_research` | `()` | Pick one maturing incubator seed and propose a research topic for it. | [src](../../../core/services/autonomous_work_daemon.py#L213) |
| function | `_plan_once` | `()` | Run planning passes and return list of created proposal_ids. | [src](../../../core/services/autonomous_work_daemon.py#L231) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L253) |
| function | `list_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L268) |
| function | `resolve_proposal` | `(proposal_id, *, outcome, note=…)` | Close a proposal. outcome in {'approved', 'rejected', 'completed'}. | [src](../../../core/services/autonomous_work_daemon.py#L275) |
| function | `build_autonomous_work_surface` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L291) |
| function | `_surface_summary` | `(pending, all_items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L310) |
| function | `build_autonomous_work_prompt_section` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L318) |

## `core/services/autonomy_pressure_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_autonomy_pressure_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L60) |
| function | `refresh_runtime_autonomy_pressure_signal_statuses` | `()` | Mark signals as stale based on multiple criteria. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L83) |
| function | `retire_autonomy_pressure_signal` | `(signal_id, *, reason=…)` | Explicitly retire/close an autonomy pressure signal. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L143) |
| function | `build_runtime_autonomy_pressure_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L170) |
| function | `_extract_autonomy_pressure_candidates` | `()` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L213) |
| function | `_persist_autonomy_pressure_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L549) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L613) |
| function | `_candidate` | `(*, pressure_type, pressure_state, weight, confidence, title, summary, rationale, source_anchor, evidence_summary, support_summary, support_count, session_count, status_reason)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L645) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L684) |
| function | `_question_continuity_support` | `(*, relation, meaning, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L693) |
| function | `_initiative_loop_question_support` | `(*, open_loops, initiative, regulation, awareness, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L734) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L826) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L835) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L843) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L855) |

## `core/services/autonomy_proposal_queue.py`
_Autonomy proposal queue — Niveau 2 fundament._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_proposal_executor` | `(kind, fn)` | Register an executor for a proposal kind. | [src](../../../core/services/autonomy_proposal_queue.py#L47) |
| function | `get_registered_proposal_kinds` | `()` | — | [src](../../../core/services/autonomy_proposal_queue.py#L52) |
| function | `file_proposal` | `(*, kind, title, rationale=…, payload=…, created_by=…, session_id=…, run_id=…, tick_id=…, canonical_key=…)` | File a new proposal in the queue. | [src](../../../core/services/autonomy_proposal_queue.py#L56) |
| function | `_notify_discord_proposal` | `(proposal_id, kind, title)` | Send a DM to the owner when a proposal is filed — fire and forget. | [src](../../../core/services/autonomy_proposal_queue.py#L107) |
| function | `list_pending_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L153) |
| function | `list_recent_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L157) |
| function | `approve_proposal` | `(proposal_id, *, resolution_note=…)` | Bjørn approves a proposal — execute it immediately if we have an | [src](../../../core/services/autonomy_proposal_queue.py#L161) |
| function | `reject_proposal` | `(proposal_id, *, resolution_note=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L246) |
| function | `build_autonomy_proposal_surface` | `(*, limit=…)` | MC-friendly view of the proposal queue. | [src](../../../core/services/autonomy_proposal_queue.py#L276) |
| function | `_execute_memory_rewrite_proposal` | `(payload)` | Execute an approved memory-rewrite proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L299) |
| function | `_execute_source_edit_proposal` | `(payload)` | Execute an approved source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L324) |
| function | `_auto_commit_after_source_edit` | `(proposal, result)` | Auto-commit the file changed by a source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L408) |
| function | `_execute_git_commit_proposal` | `(payload)` | Execute an approved git-commit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L496) |

## `core/services/avoidance_detector.py`
_Avoidance Detector — unbidden self-observation of patterns over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens_from_title` | `(title)` | — | [src](../../../core/services/avoidance_detector.py#L37) |
| function | `_cluster_key` | `(title)` | Pick a short cluster key from the first meaningful keyword(s). | [src](../../../core/services/avoidance_detector.py#L45) |
| function | `_parse_ts` | `(value)` | — | [src](../../../core/services/avoidance_detector.py#L54) |
| function | `_gather_signals` | `()` | Pull goal/dream/focus signals with common shape. | [src](../../../core/services/avoidance_detector.py#L63) |
| function | `detect_avoidances` | `()` | Identify clusters with real prior support that have gone silent. | [src](../../../core/services/avoidance_detector.py#L108) |
| function | `build_avoidance_surface` | `()` | — | [src](../../../core/services/avoidance_detector.py#L161) |
| function | `_surface_summary` | `(findings)` | — | [src](../../../core/services/avoidance_detector.py#L175) |
| function | `build_avoidance_prompt_section` | `()` | Only speaks when there's a real pattern to notice. | [src](../../../core/services/avoidance_detector.py#L185) |

## `core/services/behavioral_decisions.py`
_Behavioral decisions — closing the reflection→behavior loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_directive` | `(value)` | — | [src](../../../core/services/behavioral_decisions.py#L34) |
| function | `_commit_observe` | `(outcome, decision_id)` | Commit-cluster instrument: decision_create → central observe (best-effort). | [src](../../../core/services/behavioral_decisions.py#L38) |
| function | `create_decision` | `(*, directive, rationale=…, trigger_cue=…, priority=…, source_record_id=…, source_type=…, created_by=…)` | — | [src](../../../core/services/behavioral_decisions.py#L50) |
| function | `review_decision` | `(*, decision_id, verdict, note=…, evidence=…)` | — | [src](../../../core/services/behavioral_decisions.py#L106) |
| function | `change_status` | `(decision_id, new_status)` | — | [src](../../../core/services/behavioral_decisions.py#L136) |
| function | `revoke_decision` | `(decision_id, *, reason=…)` | — | [src](../../../core/services/behavioral_decisions.py#L154) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L172) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L182) |
| function | `get_decision_with_reviews` | `(decision_id, *, review_limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L186) |
| function | `list_active_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L213) |
| function | `list_all_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L217) |
| function | `format_active_decisions_for_heartbeat` | `(*, max_items=…)` | Compact line of top active commitments for heartbeat injection. | [src](../../../core/services/behavioral_decisions.py#L221) |
| function | `get_stats` | `()` | — | [src](../../../core/services/behavioral_decisions.py#L240) |

## `core/services/body_memory.py`
_Body Memory — Jarvis' physical sensation snapshots._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_body_snapshot` | `(context, sensation=…, intensity=…)` | — | [src](../../../core/services/body_memory.py#L9) |
| function | `describe_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L20) |
| function | `format_body_for_prompt` | `()` | — | [src](../../../core/services/body_memory.py#L26) |
| function | `reset_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L32) |
| function | `build_body_memory_surface` | `()` | — | [src](../../../core/services/body_memory.py#L36) |

## `core/services/boredom_curiosity_bridge.py`
_Boredom to Curiosity Bridge — transforms boredom into curiosity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Curiosity` | `` | A curiosity that emerges from boredom. | [src](../../../core/services/boredom_curiosity_bridge.py#L22) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L36) |
| function | `add_boredom` | `(duration)` | Add boredom based on elapsed duration. | [src](../../../core/services/boredom_curiosity_bridge.py#L40) |
| function | `_spawn_curiosity` | `()` | Spawn a curiosity when boredom is high enough. | [src](../../../core/services/boredom_curiosity_bridge.py#L73) |
| function | `should_spawn_curiosity` | `()` | Check if curiosity should spawn based on boredom level. | [src](../../../core/services/boredom_curiosity_bridge.py#L113) |
| function | `get_curiosity_prompt` | `()` | Get the most relevant curiosity prompt. | [src](../../../core/services/boredom_curiosity_bridge.py#L118) |
| function | `get_active_curiosities` | `()` | Get all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L127) |
| function | `clear_curiosities` | `()` | Clear all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L141) |
| function | `reset_boredom_curiosity_bridge` | `()` | Reset boredom curiosity bridge state (for testing). | [src](../../../core/services/boredom_curiosity_bridge.py#L147) |
| function | `get_boredom_curiosity_state` | `()` | Get current state of boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L155) |
| function | `build_boredom_curiosity_bridge_surface` | `()` | Build MC surface for boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L165) |

## `core/services/boredom_engine.py`
_Boredom Engine — productive restlessness as first-class experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_boredom_state` | `(*, idle_hours=…, tick_monotony=…, novelty_score=…, open_loop_count=…)` | — | [src](../../../core/services/boredom_engine.py#L11) |
| function | `get_boredom_state` | `()` | — | [src](../../../core/services/boredom_engine.py#L49) |
| function | `build_boredom_surface` | `()` | — | [src](../../../core/services/boredom_engine.py#L53) |

## `core/services/boundary_awareness.py`
_Boundary Awareness — "Where do I end?"_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_boundary_model` | `()` | Build Jarvis' sense of his own boundaries. | [src](../../../core/services/boundary_awareness.py#L8) |
| function | `format_boundary_for_prompt` | `()` | Compact boundary awareness for prompt injection. | [src](../../../core/services/boundary_awareness.py#L31) |
| function | `build_boundary_awareness_surface` | `()` | — | [src](../../../core/services/boundary_awareness.py#L40) |

## `core/services/bounded_action_continuity_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface=…)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L12) |
| function | `_derive_current_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L40) |
| function | `_derive_followup_from_awareness` | `(*, execution_state, action_type, action_target, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L143) |
| function | `_derive_continuity_state` | `(*, execution_state, followup_state)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L243) |
| function | `_continuity_id` | `(*, action_type, action_target, action_summary, action_outcome, approval_resolved_at, approval_source)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L267) |
| function | `_default_action_continuity_surface` | `()` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L291) |
| function | `_normalize_action_continuity_surface` | `(surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L323) |
| function | `_merge_unique` | `(left, right)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L337) |

## `core/services/bounded_mutation_intent_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_mutation_intent_surface` | `(intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L25) |
| function | `_build_write_proposal_surface` | `(*, classification, mutation_near, intent_state, intent_type, approval_scope, target_files, target_paths, repo_scope, system_scope, sudo_required, mutation_critical)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L127) |
| function | `_derive_write_proposal_confidence` | `(*, proposal_type, target_files, repo_scope, system_scope)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L224) |
| function | `_write_proposal_reason` | `(*, proposal_type, approval_scope, target_files, repo_scope, system_scope, sudo_required, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L240) |
| function | `_derive_classification` | `(*, intent_state, intent_type, approval_scope, awareness_surface, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L275) |
| function | `_derive_targets` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L310) |
| function | `_derive_repo_mutation_scope` | `(*, classification, approval_scope, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L327) |
| function | `_derive_system_mutation_scope` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L342) |
| function | `_derive_sudo_required` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L355) |
| function | `_derive_deleted_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L367) |
| function | `_derive_modified_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L371) |
| function | `_derive_untracked_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L375) |
| function | `_bounded_path_list` | `(value)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L379) |
| function | `_approval_required_mutation_capability_summary` | `()` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L385) |
| function | `_unique` | `(values)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L403) |

