# `core.services.23` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/visible_followup_lean.py`
_Lean agentic-round-prompt transform + kill-switch (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_on_double_newline` | `(text)` | Split en sammensat besked i blokke på ``\n\n`` (assembly-join-grænsen). | [src](../../../core/services/visible_followup_lean.py#L66) |
| function | `_lean_strip_user_message` | `(text)` | Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing | [src](../../../core/services/visible_followup_lean.py#L71) |
| function | `build_lean_base_messages` | `(base_messages)` | Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2. | [src](../../../core/services/visible_followup_lean.py#L113) |
| function | `agentic_lean_prompt_enabled` | `()` | Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default True. | [src](../../../core/services/visible_followup_lean.py#L208) |

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
| function | `_build_visible_chat_messages_for_github` | `(message, *, session_id, provider=…, model=…)` | Build OpenAI chat-completions messages for the visible lane. | [src](../../../core/services/visible_model.py#L534) |
| function | `_split_dynamic_tail` | `(instruction)` | Separate volatile runtime instructions without changing their role. | [src](../../../core/services/visible_model.py#L608) |
| function | `_is_current_user_turn` | `(message, current_text)` | Match the persisted current turn, not merely any user-role runtime item. | [src](../../../core/services/visible_model.py#L622) |
| function | `_insert_system_tail_before_current_user` | `(messages, tail)` | Keep volatile prompt sections cache-late while preserving system attribution. | [src](../../../core/services/visible_model.py#L634) |
| function | `_insert_typed_system_tail_before_current_user` | `(items, tail)` | — | [src](../../../core/services/visible_model.py#L647) |
| function | `_visible_system_instruction_for_provider` | `(*, provider, model, user_message, session_id)` | — | [src](../../../core/services/visible_model.py#L661) |
| function | `_build_visible_prompt_assembly` | `(*, provider, model, user_message, session_id)` | Return the full PromptAssembly (including structured transcript). | [src](../../../core/services/visible_model.py#L676) |

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
| function | `_run_openai_compatible_visible` | `(*, provider, model, message, session_id, extra_body=…)` | Shared entry point for openai-compat visible providers. | [src](../../../core/services/visible_model_adapters.py#L546) |
| function | `visible_execution_readiness` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L660) |
| function | `_execute_phase1_model` | `(*, message, provider, model)` | — | [src](../../../core/services/visible_model_adapters.py#L818) |
| function | `_execute_openai_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L835) |
| function | `_stream_openai_codex_model` | `(*, message, model, session_id=…, controller=…)` | Real token-by-token streaming for the openai-codex provider. | [src](../../../core/services/visible_model_adapters.py#L860) |
| function | `_execute_openai_codex_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L963) |
| function | `_build_openai_codex_visible_prompt` | `(*, message, model, session_id)` | — | [src](../../../core/services/visible_model_adapters.py#L989) |
| function | `_execute_github_copilot_visible_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1007) |
| function | `_stream_openai_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1089) |
| function | `_resolve_copilot_profile` | `(preferred)` | Find profilen der faktisk HAR github-copilot-creds. | [src](../../../core/services/visible_model_adapters.py#L1166) |
| function | `_stream_github_copilot_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1190) |
| function | `_load_openai_api_key` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1289) |
| function | `_load_openai_api_key_for_profile` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1297) |
| function | `_resolve_openai_profile` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1307) |
| function | `_openai_profile_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1325) |
| function | `_provider_profile_status` | `(*, provider, profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1343) |
| function | `_provider_router_config` | `(*, provider)` | — | [src](../../../core/services/visible_model_adapters.py#L1359) |
| function | `_post_openai_responses` | `(*, payload, api_key, base_url=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1369) |
| function | `_probe_openai_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L1386) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/visible_model_adapters.py#L1457) |

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
| function | `_apply_thinking_mode` | `(payload, thinking_mode)` | Translate UI thinking-mode label to ollama-chat payload keys. | [src](../../../core/services/visible_model_ollama.py#L170) |
| function | `_apply_visible_ollama_options` | `(payload)` | Set ollama generation options for the visible lane. | [src](../../../core/services/visible_model_ollama.py#L207) |
| function | `_stream_ollama_model` | `(*, message, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model_ollama.py#L247) |
| function | `_probe_ollama_visible_target` | `(*, model, base_url)` | — | [src](../../../core/services/visible_model_ollama.py#L563) |
| function | `_build_ollama_prompt` | `(message, *, model, session_id)` | — | [src](../../../core/services/visible_model_ollama.py#L604) |

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
| class | `VisibleModelDelta` | `` | — | [src](../../../core/services/visible_model_types.py#L47) |
| class | `VisibleModelReasoningDelta` | `` | Én tanke-bid fra en thinking-model, UNDER første pas. | [src](../../../core/services/visible_model_types.py#L52) |
| class | `VisibleModelStreamDone` | `` | — | [src](../../../core/services/visible_model_types.py#L66) |
| class | `VisibleModelToolCalls` | `` | — | [src](../../../core/services/visible_model_types.py#L71) |
| class | `VisibleModelStreamCancelled` | `` | — | [src](../../../core/services/visible_model_types.py#L75) |
| class | `VisibleModelRateLimited` | `` | Visible-lanens provider er rate-limited (429) eller returnerede en | [src](../../../core/services/visible_model_types.py#L79) |
| method | `VisibleModelRateLimited.__init__` | `(self, *args, provider=…, model=…)` | — | [src](../../../core/services/visible_model_types.py#L86) |

## `core/services/visible_runs.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_pending_approvals` | `()` | — | [src](../../../core/services/visible_runs.py#L260) |
| class | `VisibleRun` | `` | — | [src](../../../core/services/visible_runs.py#L310) |
| class | `VisibleRunController` | `` | — | [src](../../../core/services/visible_runs.py#L332) |
| method | `VisibleRunController.attach_stream` | `(self, stream)` | — | [src](../../../core/services/visible_runs.py#L348) |
| method | `VisibleRunController.clear_stream` | `(self)` | — | [src](../../../core/services/visible_runs.py#L351) |
| method | `VisibleRunController.cancel` | `(self)` | — | [src](../../../core/services/visible_runs.py#L354) |
| method | `VisibleRunController.is_cancelled` | `(self)` | — | [src](../../../core/services/visible_runs.py#L361) |
| function | `_thinking_for_round` | `(run, exchanges)` | Tænknings-tilstand for en agentisk FØLGE-runde. | [src](../../../core/services/visible_runs.py#L381) |
| function | `is_visible_run_alive` | `(run_id)` | Den AUTORITATIVE liveness-test — CROSS-PROCES. | [src](../../../core/services/visible_runs.py#L405) |
| function | `_classify_visible_run_interruption` | `(error_message)` | — | [src](../../../core/services/visible_runs.py#L453) |
| function | `start_visible_run` | `(message, session_id=…, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, local_tool_exec=…)` | Begin a visible run. | [src](../../../core/services/visible_runs.py#L510) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_runs.py#L787) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_runs.py#L845) |
| function | `_compact_llm_for_run` | `(prompt)` | Call the compact LLM for run-level summarisation (monkeypatchable). | [src](../../../core/services/visible_runs.py#L1047) |
| function | `_handle_compact_command` | `(run)` | Run session compact and return a message for Jarvis to respond to. | [src](../../../core/services/visible_runs.py#L1053) |
| function | `_stream_visible_run` | `(run, *, force_user_id=…, tool_scope=…)` | — | [src](../../../core/services/visible_runs.py#L1079) |
| function | `_native_tool_calls_to_capabilities` | `(tool_calls)` | Convert Ollama native tool_calls to capability-plan entries (legacy compat). | [src](../../../core/services/visible_runs.py#L5708) |
| function | `_run_grounded_capability_followup` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5764) |
| function | `_build_grounded_capability_followup_message` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5795) |
| function | `_run_grounded_multi_capability_followup` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5837) |
| function | `_build_grounded_multi_capability_followup_message` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/visible_runs.py#L5866) |
| function | `_is_code_analysis_request` | `(user_message)` | — | [src](../../../core/services/visible_runs.py#L5911) |
| function | `_is_memory_commit_request` | `(user_message)` | — | [src](../../../core/services/visible_runs.py#L5930) |
| function | `_finalize_second_pass_visible_text` | `(text, *, fallback)` | — | [src](../../../core/services/visible_runs.py#L5950) |
| function | `_bounded_error` | `(error_message, limit=…)` | — | [src](../../../core/services/visible_runs.py#L5983) |
| function | `_sse` | `(event, data)` | — | [src](../../../core/services/visible_runs.py#L5990) |
| class | `PresentationInvariantError` | `` | Raised when user-visible text contains internal runtime markers. | [src](../../../core/services/visible_runs.py#L5994) |
| function | `_assert_presentation_invariant` | `(text)` | — | [src](../../../core/services/visible_runs.py#L6020) |
| function | `_tool_label` | `(tool_name, arguments=…)` | — | [src](../../../core/services/visible_runs.py#L6136) |
| function | `_parse_tc_args` | `(tc)` | Extract arguments dict from a tool call (handles both string and dict forms). | [src](../../../core/services/visible_runs.py#L6166) |
| function | `_maybe_fallback_for_autonomous` | `(run, exc)` | Task 10-beslutningsseam: skal en fejlet model-stream faldes til poolen? | [src](../../../core/services/visible_runs.py#L6178) |
| function | `_complete_visible_run_from_fallback` | `(run, fallback)` | Terminal completion for et AUTONOMT run hvis model-stream fejlede og blev | [src](../../../core/services/visible_runs.py#L6222) |
| function | `_fail_visible_run` | `(run, error_message, *, partial_text=…)` | — | [src](../../../core/services/visible_runs.py#L6280) |
| function | `_cancel_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6354) |
| function | `register_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6407) |
| function | `get_visible_run_controller` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6437) |
| function | `cancel_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6441) |
| function | `unregister_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6452) |
| function | `get_active_visible_run` | `()` | — | [src](../../../core/services/visible_runs.py#L6466) |
| function | `get_visible_work` | `()` | — | [src](../../../core/services/visible_runs.py#L6489) |
| function | `get_visible_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L6521) |
| function | `get_visible_selected_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L6548) |
| function | `get_visible_selected_work_item` | `()` | — | [src](../../../core/services/visible_runs.py#L6579) |
| function | `get_visible_selected_work_note` | `()` | — | [src](../../../core/services/visible_runs.py#L6631) |
| function | `get_last_visible_run_outcome` | `()` | — | [src](../../../core/services/visible_runs.py#L6666) |
| function | `get_last_visible_capability_use` | `()` | — | [src](../../../core/services/visible_runs.py#L6670) |
| function | `get_last_visible_execution_trace` | `()` | — | [src](../../../core/services/visible_runs.py#L6679) |
| function | `set_last_visible_capability_use` | `(run, *, capability_id, invocation, capability_arguments=…, argument_source=…)` | — | [src](../../../core/services/visible_runs.py#L6689) |
| function | `_update_cognitive_systems_async` | `(*, run_id, user_message, assistant_response, outcome_status)` | Fire-and-forget updates to all cognitive accumulation systems. | [src](../../../core/services/visible_runs.py#L6739) |
| function | `_start_visible_execution_trace` | `(run)` | — | [src](../../../core/services/visible_runs.py#L7022) |
| function | `_update_visible_execution_trace` | `(run, updates)` | — | [src](../../../core/services/visible_runs.py#L7057) |
| function | `_set_last_visible_execution_trace` | `(trace)` | — | [src](../../../core/services/visible_runs.py#L7071) |
| function | `_visible_trace_payload` | `(run)` | — | [src](../../../core/services/visible_runs.py#L7080) |
| function | `_publish_agentic_round_start` | `(*, run_id, round_num)` | Publish runtime.agentic_round_start event and return its event_id. | [src](../../../core/services/visible_runs.py#L7089) |

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
| function | `_legacy_regex_detectors_enabled` | `()` | Er de gamle ordmønster-detektorer stadig tændt? (default: nej) | [src](../../../core/services/visible_runs_cognitive.py#L25) |
| function | `_track_step_failed` | `()` | En tracker i _track_runtime_candidates fejlede. | [src](../../../core/services/visible_runs_cognitive.py#L40) |
| function | `_track_runtime_candidates` | `(run, assistant_text)` | — | [src](../../../core/services/visible_runs_cognitive.py#L66) |

## `core/services/visible_runs_error_messaging.py`
_User-facing error messages for visible runs (Jarvis voice)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `friendly_provider_error_message` | `(exc)` | Return a Jarvis-voice Danish message for a visible-model exception. | [src](../../../core/services/visible_runs_error_messaging.py#L15) |

## `core/services/visible_runs_learning_signals.py`
_Post-run learning signals for a visible run (extracted from visible_runs.py,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tool_names` | `(collected_native_tool_calls)` | Names of the native tool calls in order (objects or OpenAI-style dicts). | [src](../../../core/services/visible_runs_learning_signals.py#L22) |
| function | `record_visible_run_learning_signals` | `(*, run_ref, collected_native_tool_calls, outcome_status, outcome_error, followup_text, output_tokens)` | — | [src](../../../core/services/visible_runs_learning_signals.py#L40) |

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
| function | `_origin_of_session` | `(session_id)` | «auto-dream-20260902» → «dream». Tom for almindelige samtaler. | [src](../../../core/services/visible_runs_outcomes.py#L79) |
| function | `_with_thinking_block` | `(blocks, run, reasoning)` | Sæt turens tænkning FORREST i blok-arrayet, hvis der blev tænkt. | [src](../../../core/services/visible_runs_outcomes.py#L88) |
| function | `_persist_session_assistant_message` | `(run, text, *, reasoning_content=…, blocks=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L126) |
| function | `_append_chat_message_with_retry` | `(*, session_id, role, content, reasoning_content=…, content_json=…, _backoffs=…)` | H5 persist-retry (spec §11.2 P5): persistering må ALDRIG tabes tavst pga. | [src](../../../core/services/visible_runs_outcomes.py#L338) |
| function | `_survival_or_fallback` | `()` | OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen svigter, lad Jarvis TALE fra | [src](../../../core/services/visible_runs_outcomes.py#L382) |
| function | `_session_last_role` | `(session_id)` | Sidste persisterede besked-rolle for en session (idempotens for invarianten). | [src](../../../core/services/visible_runs_outcomes.py#L396) |
| function | `_guarantee_visible_outcome` | `(run)` | LIVSCYKLUS-INVARIANT (Bjørn 29. jun, #1): en completed INTERAKTIV run må ALDRIG | [src](../../../core/services/visible_runs_outcomes.py#L411) |
| function | `set_last_visible_run_outcome` | `(run, *, status, error=…, text_preview=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L432) |
| function | `_persist_visible_run_outcome` | `(run, *, status, finished_at, text_preview=…, error=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L493) |

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
| function | `_run_still_active` | `(run_id)` | True hvis dette run stadig kører server-side. Fail-safe: antag AKTIVT ved fejl, | [src](../../../core/services/visible_runs_sse_v2.py#L187) |
| function | `translate_to_v2` | `(legacy_iter, *, run_id=…, model=…, provider=…, lane=…, session_id=…, ping_interval_s=…)` | Konverter legacy SSE-stream til Anthropic-style v2 protokol. | [src](../../../core/services/visible_runs_sse_v2.py#L215) |

## `core/services/visible_runs_watchdog.py`
_Agentic-round watchdog — hvornår skal en runde opgives?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `effective_silence_budget_s` | `(max_silence_s, loop_lag_peak_ms)` | Tavsheds-budget justeret for hvor blokeret vores eget loop har været. | [src](../../../core/services/visible_runs_watchdog.py#L34) |
| function | `agentic_watchdog_timeout_reason` | `(*, started_at, last_progress_at, now, max_total_s, max_silence_s, loop_lag_peak_ms=…)` | Returnér watchdog-timeout-grunden, eller None hvis runden må fortsætte. | [src](../../../core/services/visible_runs_watchdog.py#L47) |

## `core/services/visible_self_state_summary.py`
_Visible-chat self-state summary — let Jarvis answer questions about_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decision_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L29) |
| function | `_goals_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L56) |
| function | `_recent_tick_quality` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L87) |
| function | `build_self_state_block` | `()` | Return a short prompt section. Empty string when nothing useful to add. | [src](../../../core/services/visible_self_state_summary.py#L112) |

## `core/services/visible_stream_gate.py`
_In-process real-time gate: is a VISIBLE turn actively assembling/streaming right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `visible_streaming` | `()` | True hvis mindst én synlig tur i øjeblikket assembler/streamer i denne proces. | [src](../../../core/services/visible_stream_gate.py#L27) |
| function | `enter_visible_stream` | `()` | — | [src](../../../core/services/visible_stream_gate.py#L38) |
| function | `exit_visible_stream` | `()` | — | [src](../../../core/services/visible_stream_gate.py#L44) |
| function | `visible_stream` | `()` | Context manager: markér at en synlig tur er aktiv i dens levetid. Self-safe — | [src](../../../core/services/visible_stream_gate.py#L52) |

## `core/services/visible_thinking_trace.py`
_Hvor længe tænkte han? — målt ét sted, læst ét sted._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_evict_if_needed` | `()` | Hold kortet lille. Ældste post ryger — kaldes altid under _lock. | [src](../../../core/services/visible_thinking_trace.py#L31) |
| function | `mark_start` | `(run_id)` | Første tænke-blok i turen. Senere kald ignoreres. | [src](../../../core/services/visible_thinking_trace.py#L38) |
| function | `mark_end` | `(run_id)` | Seneste tænke-blok lukkede. Sidste lukning vinder — se mark_start. | [src](../../../core/services/visible_thinking_trace.py#L54) |
| function | `take_seconds` | `(run_id)` | Varigheden i sekunder, og RYD posten. None hvis der ikke blev tænkt. | [src](../../../core/services/visible_thinking_trace.py#L66) |
| function | `peek_seconds` | `(run_id)` | Som take_seconds, men uden at rydde. Til observation/test. | [src](../../../core/services/visible_thinking_trace.py#L90) |

## `core/services/visible_tool_exec.py`
_Shared tool-exec pump for the visible run (Boy-Scout extraction, 2026-07-19)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_tool_batch` | `(tool_calls, *, run, loop, tool_scope, step_counter, heartbeat_interval_s, heartbeat_phase, out, heartbeat_extra=…, exec_start=…)` | Announce → execute → heartbeat pump for one tool batch. | [src](../../../core/services/visible_tool_exec.py#L33) |

## `core/services/visible_turn_blocks.py`
_Den kanoniske content-blok-array for en assistent-tur (spec §4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_label` | `(tool_name, arguments=…)` | Narrationen for ét værktøjskald — samme tekst som live-visningen brugte. | [src](../../../core/services/visible_turn_blocks.py#L31) |
| function | `_build_progress_blocks` | `(tool_calls, tool_results)` | Byg det FLADE progress-spor for en tur (spec §5). | [src](../../../core/services/visible_turn_blocks.py#L42) |
| function | `_build_turn_blocks` | `(*, text, tool_calls, tool_results, interleave=…, text_segments=…)` | Byg den kanoniske content-blok-array for en assistant-tur (spec §4). | [src](../../../core/services/visible_turn_blocks.py#L88) |

## `core/services/vision_backend.py`
_Hvilke øjne bruger han? — valg af vision-model (2026-09-05)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `model_can_see` | `(model)` | Kan DENNE model selv se et billede? | [src](../../../core/services/vision_backend.py#L56) |
| function | `active_visible_target` | `()` | (provider, model) for den synlige tur der koerer lige nu — ("","") hvis ingen. | [src](../../../core/services/vision_backend.py#L69) |
| function | `resolve_vision_target` | `()` | (provider, model, kilde) for syns-vaerktoejerne lige nu. | [src](../../../core/services/vision_backend.py#L81) |
| function | `resolve_vision_provider` | `(model)` | `"ollama"` eller `"deepseek"`. Eksplicit konfig vinder over gættet. | [src](../../../core/services/vision_backend.py#L95) |
| function | `describe_via_deepseek` | `(image_b64, *, model, prompt, run_id=…)` | Send billedet til DeepSeeks vision-model og returnér svaret. | [src](../../../core/services/vision_backend.py#L111) |
| function | `_record_cost` | `(usage, *, model, run_id)` | — | [src](../../../core/services/vision_backend.py#L146) |
| function | `describe` | `(image_bytes=…, *, image_b64=…, model, prompt, run_id=…, provider=…)` | Beskriv/besvar et billede med den valgte backend. | [src](../../../core/services/vision_backend.py#L169) |
| function | `build_vision_backend_surface` | `()` | — | [src](../../../core/services/vision_backend.py#L192) |

## `core/services/visual_memory.py`
_Visual memory — webcam snapshots beskrevet af vision-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compare_suffix` | `(previous_desc, time_ago_label)` | Mandatory instruction: always describe what has changed. | [src](../../../core/services/visual_memory.py#L91) |
| function | `_ollama_base_url` | `()` | Pull Ollama base URL from provider_router.json (falls back to localhost). | [src](../../../core/services/visual_memory.py#L104) |
| function | `tick_visual_memory_daemon` | `()` | Capture webcam snapshot and describe it via vision model. | [src](../../../core/services/visual_memory.py#L124) |
| function | `get_visual_memories` | `(*, limit=…)` | Return most recent visual memory records (newest first). | [src](../../../core/services/visual_memory.py#L196) |
| function | `get_latest_visual_memory_for_prompt` | `()` | Return the most recent visual memory as a quiet prompt hint. | [src](../../../core/services/visual_memory.py#L203) |
| function | `_coarse_age_label` | `(minutes_ago)` | Bucket minutes-since into coarse labels so prompt cache stays stable. | [src](../../../core/services/visual_memory.py#L226) |
| function | `look_around_now` | `(*, where=…, prompt_override=…)` | On-demand capture — Jarvis chooses to look. Bypasses cadence-limit. | [src](../../../core/services/visual_memory.py#L251) |
| function | `build_visual_memory_surface` | `()` | MC observability surface. | [src](../../../core/services/visual_memory.py#L338) |
| function | `_fold` | `(text)` | Sammenlign navne uden at snuble over æøå, store bogstaver og bindestreger. | [src](../../../core/services/visual_memory.py#L403) |
| function | `known_cameras` | `()` | Alle kendte kameraer — config vinder over det indbyggede kort. | [src](../../../core/services/visual_memory.py#L416) |
| function | `default_camera` | `()` | Nøglen på det kamera der bruges når ingen har sagt hvor der skal kigges. | [src](../../../core/services/visual_memory.py#L430) |
| function | `resolve_camera` | `(where=…)` | Slå et menneskeligt stednavn op. Tom streng giver standardkameraet. | [src](../../../core/services/visual_memory.py#L451) |
| function | `capture_from_camera` | `(where=…)` | Hent et billede. Returnerer (base64-jpeg, kamera-nøgle, læsbart navn). | [src](../../../core/services/visual_memory.py#L495) |
| function | `describe_cameras` | `()` | Én linje pr. kamera — til værktøjsbeskrivelser og prompten. | [src](../../../core/services/visual_memory.py#L510) |
| function | `_capture_image` | `(where=…)` | Hent et billede fra et navngivet kamera. Returnerer (base64-jpeg, kameranavn). | [src](../../../core/services/visual_memory.py#L524) |
| function | `_capture_source` | `()` | Return 'ha_camera' or 'webcam' based on runtime config. | [src](../../../core/services/visual_memory.py#L545) |
| function | `_ha_camera_entity` | `()` | Return HA camera entity_id from runtime config. | [src](../../../core/services/visual_memory.py#L551) |
| function | `_capture_ha_camera` | `(entity_id=…)` | Fetch snapshot from Home Assistant camera and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L557) |
| function | `_capture_webcam` | `(device_index=…)` | Capture one frame from webcam and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L593) |
| function | `_describe_image` | `(image_b64, *, model, provider, prompt=…, previous=…)` | Send image to vision model and return description. | [src](../../../core/services/visual_memory.py#L618) |
| function | `_previous_time_label` | `(captured_at)` | — | [src](../../../core/services/visual_memory.py#L640) |
| function | `_build_prompt` | `(previous=…, prompt_index=…)` | Assemble the full vision prompt: prefix + rotating focus + optional compare. | [src](../../../core/services/visual_memory.py#L655) |
| function | `_describe_via_ollama` | `(image_b64, *, model, prompt=…, previous=…)` | Call Ollama generate API with image payload. | [src](../../../core/services/visual_memory.py#L677) |
| function | `_load_records` | `()` | — | [src](../../../core/services/visual_memory.py#L732) |
| function | `_prune_old_records` | `()` | — | [src](../../../core/services/visual_memory.py#L739) |
| function | `_vision_model` | `()` | Return (model_name, provider) — den valgte model vinder over config. | [src](../../../core/services/visual_memory.py#L747) |
| function | `_enabled` | `()` | — | [src](../../../core/services/visual_memory.py#L780) |
| function | `_archive_sensory` | `(description, *, metadata)` | Mirror every visual memory into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/visual_memory.py#L785) |

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
| function | `_observe_world_model` | `(nerve, *, value=…, meta=…)` | EGRESS-FRI binding til Centralen (§24.4): world-model-livscyklus (prediction lavet, | [src](../../../core/services/world_model_signal_tracking.py#L86) |
| function | `record_runtime_world_model_prediction` | `(*, subject, expectation, horizon=…, confidence=…, evidence=…, source=…, now=…)` | Record an explicit, falsifiable world-model expectation. | [src](../../../core/services/world_model_signal_tracking.py#L103) |
| function | `resolve_runtime_world_model_prediction` | `(prediction_id, *, observed, outcome, now=…, resolved_via=…)` | Resolve a prediction with a later observation. | [src](../../../core/services/world_model_signal_tracking.py#L167) |
| function | `build_runtime_world_model_prediction_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L217) |
| function | `track_runtime_world_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L253) |
| function | `refresh_runtime_world_model_signal_statuses` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L293) |
| function | `build_runtime_world_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L322) |
| function | `_extract_pattern_matches` | `(text, patterns)` | Return list of {matched_phrase, context_excerpt} for each regex hit. | [src](../../../core/services/world_model_signal_tracking.py#L348) |
| function | `extract_prediction_language` | `(text)` | Find prediction-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L377) |
| function | `extract_resolution_language` | `(text)` | Find resolution-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L382) |
| function | `_loop_enabled` | `()` | World-model-loop kill-switch check. | [src](../../../core/services/world_model_signal_tracking.py#L387) |
| function | `_load_nudges` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L395) |
| function | `_save_nudges` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L405) |
| function | `record_prediction_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt)` | Append a prediction-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L409) |
| function | `record_resolution_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id=…)` | Append a resolution-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L436) |
| function | `_next_weekday` | `(d, target_weekday)` | Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day. | [src](../../../core/services/world_model_signal_tracking.py#L469) |
| function | `_parse_horizon` | `(horizon, created)` | Return the cutoff datetime when horizon would have elapsed. | [src](../../../core/services/world_model_signal_tracking.py#L477) |
| function | `_ttl_sweep_open_predictions` | `(*, now=…)` | Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace. | [src](../../../core/services/world_model_signal_tracking.py#L501) |
| function | `format_world_model_nudges_for_awareness` | `(*, session_id=…)` | Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block. | [src](../../../core/services/world_model_signal_tracking.py#L539) |
| function | `_load_milestones` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L587) |
| function | `_save_milestones` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L594) |
| function | `_resolved_predictions_chrono` | `()` | Return resolved predictions in chronological order (oldest first). | [src](../../../core/services/world_model_signal_tracking.py#L598) |
| function | `_calibration_of` | `(predictions)` | % supported among supported+contradicted; uncertain is excluded. | [src](../../../core/services/world_model_signal_tracking.py#L610) |
| function | `_has_milestone` | `(kind, value=…)` | Check if a milestone of given kind (+ optional value) has been recorded. | [src](../../../core/services/world_model_signal_tracking.py#L619) |
| function | `_append_milestone` | `(kind, value, message, now)` | — | [src](../../../core/services/world_model_signal_tracking.py#L630) |
| function | `_compute_calibration_milestone` | `(*, now=…)` | Compute the latest calibration milestone if any rule fires. | [src](../../../core/services/world_model_signal_tracking.py#L647) |
| function | `format_world_model_milestone_for_awareness` | `()` | Surface one unrendered milestone per call. Returns '' when nothing. | [src](../../../core/services/world_model_signal_tracking.py#L719) |
| function | `_load_predictions` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L735) |
| function | `_save_predictions` | `(predictions)` | — | [src](../../../core/services/world_model_signal_tracking.py#L742) |
| function | `_extract_world_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L746) |
| function | `_project_context_signal` | `(message, *, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L773) |
| function | `_workspace_scope_signal` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L808) |
| function | `_persist_world_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L830) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L903) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/world_model_signal_tracking.py#L947) |
| function | `_matches_project_context` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L968) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L973) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L980) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/world_model_signal_tracking.py#L984) |

