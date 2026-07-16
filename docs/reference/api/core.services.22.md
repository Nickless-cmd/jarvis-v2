# `core.services.22` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| class | `VisibleModelDelta` | `` | — | [src](../../../core/services/visible_model_types.py#L44) |
| class | `VisibleModelStreamDone` | `` | — | [src](../../../core/services/visible_model_types.py#L49) |
| class | `VisibleModelToolCalls` | `` | — | [src](../../../core/services/visible_model_types.py#L54) |
| class | `VisibleModelStreamCancelled` | `` | — | [src](../../../core/services/visible_model_types.py#L58) |
| class | `VisibleModelRateLimited` | `` | Visible-lanens provider er rate-limited (429) eller returnerede en | [src](../../../core/services/visible_model_types.py#L62) |
| method | `VisibleModelRateLimited.__init__` | `(self, *args, provider=…, model=…)` | — | [src](../../../core/services/visible_model_types.py#L69) |

## `core/services/visible_runs.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_pending_approvals` | `()` | — | [src](../../../core/services/visible_runs.py#L242) |
| function | `_build_turn_blocks` | `(*, text, tool_calls, tool_results, interleave=…)` | Byg den kanoniske content-blok-array for en assistant-tur (spec §4). | [src](../../../core/services/visible_runs.py#L271) |
| function | `_build_progress_blocks` | `(tool_calls, tool_results)` | Byg det FLADE progress-spor for en tur (spec §5). | [src](../../../core/services/visible_runs.py#L405) |
| class | `VisibleRun` | `` | — | [src](../../../core/services/visible_runs.py#L452) |
| class | `VisibleRunController` | `` | — | [src](../../../core/services/visible_runs.py#L465) |
| method | `VisibleRunController.attach_stream` | `(self, stream)` | — | [src](../../../core/services/visible_runs.py#L481) |
| method | `VisibleRunController.clear_stream` | `(self)` | — | [src](../../../core/services/visible_runs.py#L484) |
| method | `VisibleRunController.cancel` | `(self)` | — | [src](../../../core/services/visible_runs.py#L487) |
| method | `VisibleRunController.is_cancelled` | `(self)` | — | [src](../../../core/services/visible_runs.py#L494) |
| function | `is_visible_run_alive` | `(run_id)` | Den AUTORITATIVE liveness-test — CROSS-PROCES. | [src](../../../core/services/visible_runs.py#L512) |
| function | `_classify_visible_run_interruption` | `(error_message)` | — | [src](../../../core/services/visible_runs.py#L560) |
| function | `_agentic_watchdog_timeout_reason` | `(*, started_at, last_progress_at, now, max_total_s, max_silence_s)` | Return the watchdog timeout reason, or None if the round can continue. | [src](../../../core/services/visible_runs.py#L608) |
| function | `start_visible_run` | `(message, session_id=…, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…)` | Begin a visible run. | [src](../../../core/services/visible_runs.py#L624) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_runs.py#L873) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_runs.py#L898) |
| function | `_compact_llm_for_run` | `(prompt)` | Call the compact LLM for run-level summarisation (monkeypatchable). | [src](../../../core/services/visible_runs.py#L1090) |
| function | `_handle_compact_command` | `(run)` | Run session compact and return a message for Jarvis to respond to. | [src](../../../core/services/visible_runs.py#L1096) |
| function | `_stream_visible_run` | `(run, *, force_user_id=…, tool_scope=…)` | — | [src](../../../core/services/visible_runs.py#L1122) |
| function | `_native_tool_calls_to_capabilities` | `(tool_calls)` | Convert Ollama native tool_calls to capability-plan entries (legacy compat). | [src](../../../core/services/visible_runs.py#L5570) |
| function | `_run_grounded_capability_followup` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5620) |
| function | `_build_grounded_capability_followup_message` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5651) |
| function | `_run_grounded_multi_capability_followup` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5693) |
| function | `_build_grounded_multi_capability_followup_message` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5722) |
| function | `_is_code_analysis_request` | `(user_message)` | — | [src](../../../core/services/visible_runs.py#L5767) |
| function | `_is_memory_commit_request` | `(user_message)` | — | [src](../../../core/services/visible_runs.py#L5786) |
| function | `_finalize_second_pass_visible_text` | `(text, *, fallback)` | — | [src](../../../core/services/visible_runs.py#L5806) |
| function | `_bounded_error` | `(error_message, limit=…)` | — | [src](../../../core/services/visible_runs.py#L5818) |
| function | `_sse` | `(event, data)` | — | [src](../../../core/services/visible_runs.py#L5825) |
| class | `PresentationInvariantError` | `` | Raised when user-visible text contains internal runtime markers. | [src](../../../core/services/visible_runs.py#L5829) |
| function | `_assert_presentation_invariant` | `(text)` | — | [src](../../../core/services/visible_runs.py#L5855) |
| function | `_tool_label` | `(tool_name, arguments=…)` | — | [src](../../../core/services/visible_runs.py#L5974) |
| function | `_parse_tc_args` | `(tc)` | Extract arguments dict from a tool call (handles both string and dict forms). | [src](../../../core/services/visible_runs.py#L6004) |
| function | `_fail_visible_run` | `(run, error_message, *, partial_text=…)` | — | [src](../../../core/services/visible_runs.py#L6016) |
| function | `_cancel_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6090) |
| function | `register_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6143) |
| function | `get_visible_run_controller` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6173) |
| function | `cancel_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6177) |
| function | `unregister_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6188) |
| function | `get_active_visible_run` | `()` | — | [src](../../../core/services/visible_runs.py#L6202) |
| function | `get_visible_work` | `()` | — | [src](../../../core/services/visible_runs.py#L6225) |
| function | `get_visible_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L6257) |
| function | `get_visible_selected_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L6284) |
| function | `get_visible_selected_work_item` | `()` | — | [src](../../../core/services/visible_runs.py#L6315) |
| function | `get_visible_selected_work_note` | `()` | — | [src](../../../core/services/visible_runs.py#L6367) |
| function | `get_last_visible_run_outcome` | `()` | — | [src](../../../core/services/visible_runs.py#L6402) |
| function | `get_last_visible_capability_use` | `()` | — | [src](../../../core/services/visible_runs.py#L6406) |
| function | `get_last_visible_execution_trace` | `()` | — | [src](../../../core/services/visible_runs.py#L6415) |
| function | `set_last_visible_capability_use` | `(run, *, capability_id, invocation, capability_arguments=…, argument_source=…)` | — | [src](../../../core/services/visible_runs.py#L6425) |
| function | `_update_cognitive_systems_async` | `(*, run_id, user_message, assistant_response, outcome_status)` | Fire-and-forget updates to all cognitive accumulation systems. | [src](../../../core/services/visible_runs.py#L6475) |
| function | `_start_visible_execution_trace` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6752) |
| function | `_update_visible_execution_trace` | `(run, updates)` | — | [src](../../../core/services/visible_runs.py#L6787) |
| function | `_set_last_visible_execution_trace` | `(trace)` | — | [src](../../../core/services/visible_runs.py#L6801) |
| function | `_visible_trace_payload` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6810) |
| function | `_publish_agentic_round_start` | `(*, run_id, round_num)` | Publish runtime.agentic_round_start event and return its event_id. | [src](../../../core/services/visible_runs.py#L6819) |

## `core/services/visible_runs_approvals.py`
_Pending tool-approval resolution for visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_pending_approval` | `(approval_id, *, approved)` | Resolve a pending tool approval. | [src](../../../core/services/visible_runs_approvals.py#L27) |

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
| function | `_track_step_failed` | `()` | En tracker i _track_runtime_candidates fejlede. | [src](../../../core/services/visible_runs_cognitive.py#L25) |
| function | `_track_runtime_candidates` | `(run, assistant_text)` | — | [src](../../../core/services/visible_runs_cognitive.py#L51) |

## `core/services/visible_runs_error_messaging.py`
_User-facing error messages for visible runs (Jarvis voice)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `friendly_provider_error_message` | `(exc)` | Return a Jarvis-voice Danish message for a visible-model exception. | [src](../../../core/services/visible_runs_error_messaging.py#L15) |

## `core/services/visible_runs_memory.py`
_Memory/continuity post-processing for visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_internal_tool_context` | `(session_id, *, limit=…)` | — | [src](../../../core/services/visible_runs_memory.py#L24) |
| function | `_run_memory_postprocess` | `(run, assistant_text)` | — | [src](../../../core/services/visible_runs_memory.py#L50) |
| function | `_maybe_trigger_continuation` | `(run, assistant_text)` | If Jarvis stopped mid-task, trigger an autonomous-run | [src](../../../core/services/visible_runs_memory.py#L229) |

## `core/services/visible_runs_outcomes.py`
_Persistence + terminal outcome for visible runs (fail/cancel forbliver i main)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_preview_text` | `(text, limit=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L33) |
| function | `_mark_mid_word_truncation` | `(text)` | Append "…" if the assistant text ends abruptly mid-word. | [src](../../../core/services/visible_runs_outcomes.py#L40) |
| function | `_persist_session_assistant_message` | `(run, text, *, reasoning_content=…, blocks=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L78) |
| function | `_append_chat_message_with_retry` | `(*, session_id, role, content, reasoning_content=…, content_json=…, _backoffs=…)` | H5 persist-retry (spec §11.2 P5): persistering må ALDRIG tabes tavst pga. | [src](../../../core/services/visible_runs_outcomes.py#L239) |
| function | `_survival_or_fallback` | `()` | OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen svigter, lad Jarvis TALE fra | [src](../../../core/services/visible_runs_outcomes.py#L283) |
| function | `_session_last_role` | `(session_id)` | Sidste persisterede besked-rolle for en session (idempotens for invarianten). | [src](../../../core/services/visible_runs_outcomes.py#L297) |
| function | `_guarantee_visible_outcome` | `(run)` | LIVSCYKLUS-INVARIANT (Bjørn 29. jun, #1): en completed INTERAKTIV run må ALDRIG | [src](../../../core/services/visible_runs_outcomes.py#L312) |
| function | `set_last_visible_run_outcome` | `(run, *, status, error=…, text_preview=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L333) |
| function | `_persist_visible_run_outcome` | `(run, *, status, finished_at, text_preview=…, error=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L386) |

## `core/services/visible_runs_sse_v2.py`
_Translator: legacy SSE-events → Anthropic-style v2-protokol._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolEchoFilter` | `` | Streaming-backstop mod at modellen ekkoer rå tool-output i sit svar. | [src](../../../core/services/visible_runs_sse_v2.py#L73) |
| method | `ToolEchoFilter.__init__` | `(self, tool_names=…)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L84) |
| method | `ToolEchoFilter._is_echo_line` | `(self, line)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L96) |
| method | `ToolEchoFilter.feed` | `(self, text)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L100) |
| method | `ToolEchoFilter.flush` | `(self)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L149) |
| function | `_parse_legacy_sse` | `(chunk)` | Parse en legacy SSE event-blok til (event_name, payload_dict). | [src](../../../core/services/visible_runs_sse_v2.py#L159) |
| function | `_run_still_active` | `(run_id)` | True hvis dette run stadig er det aktive visible-run server-side. Fail-safe: | [src](../../../core/services/visible_runs_sse_v2.py#L187) |
| function | `translate_to_v2` | `(legacy_iter, *, run_id=…, model=…, provider=…, lane=…, session_id=…, ping_interval_s=…)` | Konverter legacy SSE-stream til Anthropic-style v2 protokol. | [src](../../../core/services/visible_runs_sse_v2.py#L198) |

## `core/services/visible_self_state_summary.py`
_Visible-chat self-state summary — let Jarvis answer questions about_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decision_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L29) |
| function | `_goals_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L56) |
| function | `_recent_tick_quality` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L87) |
| function | `build_self_state_block` | `()` | Return a short prompt section. Empty string when nothing useful to add. | [src](../../../core/services/visible_self_state_summary.py#L112) |

## `core/services/visual_memory.py`
_Visual memory — webcam snapshots beskrevet af vision-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compare_suffix` | `(previous_desc, time_ago_label)` | Mandatory instruction: always describe what has changed. | [src](../../../core/services/visual_memory.py#L80) |
| function | `_ollama_base_url` | `()` | Pull Ollama base URL from provider_router.json (falls back to localhost). | [src](../../../core/services/visual_memory.py#L93) |
| function | `tick_visual_memory_daemon` | `()` | Capture webcam snapshot and describe it via vision model. | [src](../../../core/services/visual_memory.py#L113) |
| function | `get_visual_memories` | `(*, limit=…)` | Return most recent visual memory records (newest first). | [src](../../../core/services/visual_memory.py#L185) |
| function | `get_latest_visual_memory_for_prompt` | `()` | Return the most recent visual memory as a quiet prompt hint. | [src](../../../core/services/visual_memory.py#L192) |
| function | `_coarse_age_label` | `(minutes_ago)` | Bucket minutes-since into coarse labels so prompt cache stays stable. | [src](../../../core/services/visual_memory.py#L215) |
| function | `look_around_now` | `(*, prompt_override=…)` | On-demand capture — Jarvis chooses to look. Bypasses cadence-limit. | [src](../../../core/services/visual_memory.py#L240) |
| function | `build_visual_memory_surface` | `()` | MC observability surface. | [src](../../../core/services/visual_memory.py#L319) |
| function | `_capture_image` | `()` | Capture image from configured source (HA camera or webcam) and return as base64 JPEG. | [src](../../../core/services/visual_memory.py#L343) |
| function | `_capture_source` | `()` | Return 'ha_camera' or 'webcam' based on runtime config. | [src](../../../core/services/visual_memory.py#L355) |
| function | `_ha_camera_entity` | `()` | Return HA camera entity_id from runtime config. | [src](../../../core/services/visual_memory.py#L361) |
| function | `_capture_ha_camera` | `()` | Fetch snapshot from Home Assistant camera and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L367) |
| function | `_capture_webcam` | `(device_index=…)` | Capture one frame from webcam and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L403) |
| function | `_describe_image` | `(image_b64, *, model, provider, prompt=…, previous=…)` | Send image to vision model and return description. | [src](../../../core/services/visual_memory.py#L428) |
| function | `_previous_time_label` | `(captured_at)` | — | [src](../../../core/services/visual_memory.py#L444) |
| function | `_build_prompt` | `(previous=…, prompt_index=…)` | Assemble the full vision prompt: prefix + rotating focus + optional compare. | [src](../../../core/services/visual_memory.py#L459) |
| function | `_describe_via_ollama` | `(image_b64, *, model, prompt=…, previous=…)` | Call Ollama generate API with image payload. | [src](../../../core/services/visual_memory.py#L481) |
| function | `_load_records` | `()` | — | [src](../../../core/services/visual_memory.py#L536) |
| function | `_prune_old_records` | `()` | — | [src](../../../core/services/visual_memory.py#L543) |
| function | `_vision_model` | `()` | Return (model_name, provider) from runtime config or defaults. | [src](../../../core/services/visual_memory.py#L551) |
| function | `_enabled` | `()` | — | [src](../../../core/services/visual_memory.py#L567) |
| function | `_archive_sensory` | `(description, *, metadata)` | Mirror every visual memory into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/visual_memory.py#L572) |

## `core/services/voice_anchor.py`
_Voice anchor — combined static seed + auto-refreshed external exemplars._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_voice_anchor` | `()` | Return concatenated VOICE.md + VOICE_RECENT.md, or empty string. | [src](../../../core/services/voice_anchor.py#L20) |

## `core/services/voice_curator.py`
_Voice curator — refresh VOICE_RECENT.md from EXTERNAL output only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `refresh_voice_recent` | `()` | Rebuild workspace/VOICE_RECENT.md from external output. | [src](../../../core/services/voice_curator.py#L34) |
| function | `_pick_diverse` | `(*, chat, chronicle, journals)` | Pick up to _TARGET_TOTAL exemplars, max _MAX_PER_SOURCE per source. | [src](../../../core/services/voice_curator.py#L65) |
| function | `_format_recent` | `(exemplars)` | Render exemplars as a markdown blob for VOICE_RECENT.md. | [src](../../../core/services/voice_curator.py#L96) |
| function | `_fetch_chat_exemplars` | `(*, limit)` | Pull recent assistant replies from chat_messages (all sessions). | [src](../../../core/services/voice_curator.py#L112) |
| function | `_fetch_chronicle_exemplars` | `(*, limit)` | Pull recent chronicle narratives as voice exemplars. | [src](../../../core/services/voice_curator.py#L149) |
| function | `_fetch_journal_exemplars` | `(*, limit)` | Pull recent journal entry bodies as voice exemplars. | [src](../../../core/services/voice_curator.py#L170) |
| function | `_strip_frontmatter` | `(text)` | Drop a leading `---\n...\n---\n` YAML block if present. | [src](../../../core/services/voice_curator.py#L203) |

## `core/services/voice_daemon.py`
_Voice daemon — runs the Hey Jarvis voice loop as a background thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_voice_enabled` | `()` | Check if voice is enabled via config or env. | [src](../../../core/services/voice_daemon.py#L24) |
| function | `_run_loop` | `()` | Supervisor thread: start worker, restart on crash until stopped. | [src](../../../core/services/voice_daemon.py#L30) |
| function | `start_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L60) |
| function | `stop_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L73) |
| function | `build_voice_daemon_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/voice_daemon.py#L84) |

## `core/services/wakeup_dispatcher.py`
_Wakeup dispatcher — autonomous fire of self-wakeups._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pick_wakeup_run_target` | `(*, channel, record_session, app_resolver, owner_resolver, is_external)` | Beslut hvilken session et wakeup-run skal lande i — med Discord-guard. | [src](../../../core/services/wakeup_dispatcher.py#L33) |
| function | `dispatch_due_wakeups` | `()` | Find newly-fired wakeups, push them out via webchat + heartbeat tick. | [src](../../../core/services/wakeup_dispatcher.py#L64) |
| function | `_exec_dispatch_due_wakeups` | `(args)` | — | [src](../../../core/services/wakeup_dispatcher.py#L185) |

## `core/services/weekly_manifest.py`
_Weekly manifest — Jarvis' running self-reflection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_weekly_manifest_path` | `()` | — | [src](../../../core/services/weekly_manifest.py#L32) |
| function | `_gather_context` | `()` | Pull recent self-state to ground the reflection. | [src](../../../core/services/weekly_manifest.py#L36) |
| function | `_build_prompt` | `(ctx)` | — | [src](../../../core/services/weekly_manifest.py#L58) |
| function | `build_weekly_manifest` | `()` | Generate weekly manifest, write to WEEKLY_MANIFEST.md, return summary. | [src](../../../core/services/weekly_manifest.py#L73) |

## `core/services/witness_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_witness_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L29) |
| function | `refresh_runtime_witness_signal_statuses` | `()` | — | [src](../../../core/services/witness_signal_tracking.py#L51) |
| function | `build_runtime_witness_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/witness_signal_tracking.py#L120) |
| function | `_extract_witness_candidates` | `(*, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L156) |
| function | `_persist_witness_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L254) |
| function | `_build_candidate` | `(*, domain_key, signal_type, title, summary, rationale, status_reason, source_items, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L323) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L456) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L468) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L472) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L477) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L482) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L487) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L496) |
| function | `_latest_self_narrative_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L569) |
| function | `_latest_meaning_significance` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L577) |
| function | `_latest_temperament_tendency` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L585) |
| function | `_latest_relation_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L593) |
| function | `_latest_signal_for_domain` | `(items, *, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L601) |
| function | `_focus_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L618) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L623) |
| function | `_derive_becoming_direction` | `(*, signal_type, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L628) |
| function | `_derive_becoming_weight` | `(*, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L657) |
| function | `_derive_maturation_hint` | `(*, signal_type, self_narrative, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L677) |
| function | `_derive_maturation_state` | `(*, signal_type, status, becoming_direction, becoming_weight, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L698) |
| function | `_derive_maturation_marker` | `(*, maturation_state, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L719) |
| function | `_derive_persistence_state` | `(*, status, becoming_direction, maturation_state, support_count, session_count)` | — | [src](../../../core/services/witness_signal_tracking.py#L739) |
| function | `_derive_persistence_marker` | `(*, persistence_state, maturation_state)` | — | [src](../../../core/services/witness_signal_tracking.py#L760) |
| function | `_becoming_summary` | `(*, domain_title, becoming_direction, becoming_weight, signal_type)` | — | [src](../../../core/services/witness_signal_tracking.py#L780) |
| function | `_maturation_summary` | `(*, domain_title, becoming_direction, maturation_state, maturation_marker)` | — | [src](../../../core/services/witness_signal_tracking.py#L796) |
| function | `_persistence_summary` | `(*, domain_title, persistence_state, persistence_marker, becoming_direction)` | — | [src](../../../core/services/witness_signal_tracking.py#L811) |
| function | `_summary_marker` | `(text, key)` | — | [src](../../../core/services/witness_signal_tracking.py#L826) |
| function | `_last_summary_fragment` | `(text)` | — | [src](../../../core/services/witness_signal_tracking.py#L835) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L841) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/witness_signal_tracking.py#L847) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L860) |
| function | `run_witness_daemon` | `(*, trigger=…, last_visible_at=…)` | Bounded inner witness daemon — produces witness signals without visible turn. | [src](../../../core/services/witness_signal_tracking.py#L884) |
| function | `get_witness_daemon_state` | `()` | Return current witness daemon state for MC observability. | [src](../../../core/services/witness_signal_tracking.py#L1000) |

## `core/services/workspace_crypto.py`
_Krypteret workspace-fil-I/O (spec §16, Lag 3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `encrypt_on_write` | `()` | True hvis non-owner skrivninger faktisk skal krypteres (sti-nøglet path). | [src](../../../core/services/workspace_crypto.py#L33) |
| function | `should_encrypt` | `(user_id)` | True hvis denne brugers data skal krypteres (alle undtagen owner, §16.2). | [src](../../../core/services/workspace_crypto.py#L46) |
| function | `write_workspace_file` | `(path, content, user_id)` | Skriv en workspace-fil. Non-owner → krypteret (.enc); owner → plaintext. | [src](../../../core/services/workspace_crypto.py#L65) |
| function | `read_workspace_file` | `(path, user_id)` | Læs en workspace-fil. Prøver krypteret (.enc) først for non-owner, ellers | [src](../../../core/services/workspace_crypto.py#L91) |
| function | `member_user_id_for_path` | `(path)` | Udled discord_id for filens NON-owner ejer ud fra `workspaces/<navn>/…`. | [src](../../../core/services/workspace_crypto.py#L113) |
| function | `read_text_for_path` | `(path, *, encoding=…)` | Læs workspace-fil-tekst sti-nøglet. Returnerer None hvis hverken plaintext | [src](../../../core/services/workspace_crypto.py#L153) |
| function | `write_text_for_path` | `(path, content)` | Skriv workspace-fil-tekst sti-nøglet. Mens ENCRYPT_ON_WRITE er FRA skrives | [src](../../../core/services/workspace_crypto.py#L171) |

## `core/services/workspace_trust.py`
_Trusted-folder gate for code/cowork workspaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/workspace_trust.py#L30) |
| function | `is_trusted` | `(user_id, kind, root)` | True hvis (user_id, kind, root) er markeret betroet. | [src](../../../core/services/workspace_trust.py#L44) |
| function | `set_trusted` | `(user_id, kind, root, trusted)` | Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand. | [src](../../../core/services/workspace_trust.py#L57) |
| function | `set_trust_context` | `(*, kind, root, trusted)` | — | [src](../../../core/services/workspace_trust.py#L80) |
| function | `clear_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L84) |
| function | `current_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L88) |
| function | `guard_code_write` | `(tool_name)` | Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et | [src](../../../core/services/workspace_trust.py#L92) |

## `core/services/world_model_auto_extraction.py`
_World Model Phase 2: auto-extract structured predictions from Jarvis' replies._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today_iso` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L35) |
| function | `_load_rate_state` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L39) |
| function | `_increment_rate` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L48) |
| function | `_under_rate_limit` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L55) |
| function | `_extract_json` | `(text)` | — | [src](../../../core/services/world_model_auto_extraction.py#L59) |
| function | `_build_prompt` | `(context_excerpt, matched_phrase)` | — | [src](../../../core/services/world_model_auto_extraction.py#L71) |
| function | `auto_extract_and_record` | `(*, matched_phrase, context_excerpt, session_id=…)` | Try to extract a structured prediction from a matched phrase. | [src](../../../core/services/world_model_auto_extraction.py#L89) |
| function | `_emit_world_model_auto_extraction_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/world_model_auto_extraction.py#L172) |

## `core/services/world_model_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_world_model` | `(nerve, *, value=…, meta=…)` | EGRESS-FRI binding til Centralen (§24.4): world-model-livscyklus (prediction lavet, | [src](../../../core/services/world_model_signal_tracking.py#L70) |
| function | `record_runtime_world_model_prediction` | `(*, subject, expectation, horizon=…, confidence=…, evidence=…, source=…, now=…)` | Record an explicit, falsifiable world-model expectation. | [src](../../../core/services/world_model_signal_tracking.py#L87) |
| function | `resolve_runtime_world_model_prediction` | `(prediction_id, *, observed, outcome, now=…, resolved_via=…)` | Resolve a prediction with a later observation. | [src](../../../core/services/world_model_signal_tracking.py#L151) |
| function | `build_runtime_world_model_prediction_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L201) |
| function | `track_runtime_world_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L237) |
| function | `refresh_runtime_world_model_signal_statuses` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L277) |
| function | `build_runtime_world_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L306) |
| function | `_extract_pattern_matches` | `(text, patterns)` | Return list of {matched_phrase, context_excerpt} for each regex hit. | [src](../../../core/services/world_model_signal_tracking.py#L332) |
| function | `extract_prediction_language` | `(text)` | Find prediction-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L361) |
| function | `extract_resolution_language` | `(text)` | Find resolution-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L366) |
| function | `_loop_enabled` | `()` | World-model-loop kill-switch check. | [src](../../../core/services/world_model_signal_tracking.py#L371) |
| function | `_load_nudges` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L379) |
| function | `_save_nudges` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L389) |
| function | `record_prediction_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt)` | Append a prediction-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L393) |
| function | `record_resolution_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id=…)` | Append a resolution-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L420) |
| function | `_next_weekday` | `(d, target_weekday)` | Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day. | [src](../../../core/services/world_model_signal_tracking.py#L453) |
| function | `_parse_horizon` | `(horizon, created)` | Return the cutoff datetime when horizon would have elapsed. | [src](../../../core/services/world_model_signal_tracking.py#L461) |
| function | `_ttl_sweep_open_predictions` | `(*, now=…)` | Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace. | [src](../../../core/services/world_model_signal_tracking.py#L485) |
| function | `format_world_model_nudges_for_awareness` | `(*, session_id=…)` | Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block. | [src](../../../core/services/world_model_signal_tracking.py#L523) |
| function | `_load_milestones` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L571) |
| function | `_save_milestones` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L578) |
| function | `_resolved_predictions_chrono` | `()` | Return resolved predictions in chronological order (oldest first). | [src](../../../core/services/world_model_signal_tracking.py#L582) |
| function | `_calibration_of` | `(predictions)` | % supported among supported+contradicted; uncertain is excluded. | [src](../../../core/services/world_model_signal_tracking.py#L594) |
| function | `_has_milestone` | `(kind, value=…)` | Check if a milestone of given kind (+ optional value) has been recorded. | [src](../../../core/services/world_model_signal_tracking.py#L603) |
| function | `_append_milestone` | `(kind, value, message, now)` | — | [src](../../../core/services/world_model_signal_tracking.py#L614) |
| function | `_compute_calibration_milestone` | `(*, now=…)` | Compute the latest calibration milestone if any rule fires. | [src](../../../core/services/world_model_signal_tracking.py#L631) |
| function | `format_world_model_milestone_for_awareness` | `()` | Surface one unrendered milestone per call. Returns '' when nothing. | [src](../../../core/services/world_model_signal_tracking.py#L703) |
| function | `_load_predictions` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L719) |
| function | `_save_predictions` | `(predictions)` | — | [src](../../../core/services/world_model_signal_tracking.py#L726) |
| function | `_extract_world_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L730) |
| function | `_project_context_signal` | `(message, *, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L757) |
| function | `_workspace_scope_signal` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L792) |
| function | `_persist_world_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L814) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L887) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/world_model_signal_tracking.py#L931) |
| function | `_matches_project_context` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L952) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L957) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L964) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/world_model_signal_tracking.py#L968) |

