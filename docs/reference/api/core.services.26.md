# `core.services.26` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_append_image_message` | `(messages, tr)` | Læg pixels ind efter et tool-resultat der bar et billede (2026-09-06). | [src](../../../core/services/visible_followup_adapters.py#L52) |
| class | `OllamaFollowupAdapter` | `` | Follow-up via Ollama's ``/api/chat`` streaming NDJSON endpoint. | [src](../../../core/services/visible_followup_adapters.py#L72) |
| method | `OllamaFollowupAdapter._normalize_tool_calls` | `(self, tool_calls)` | Replay tool_calls — men REPARÉR afkortede/malformede argument-strenge først. | [src](../../../core/services/visible_followup_adapters.py#L95) |
| method | `OllamaFollowupAdapter._repair_arguments` | `(container)` | Hvis container['arguments'] er en STRENG der ikke er gyldig JSON → erstat med {}. | [src](../../../core/services/visible_followup_adapters.py#L121) |
| method | `OllamaFollowupAdapter._compact_exchanges` | `(self, exchanges)` | Bound Ollama follow-up replay so long tool loops do not 400. | [src](../../../core/services/visible_followup_adapters.py#L146) |
| method | `OllamaFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Replay exchanges as structured assistant + role=tool messages. | [src](../../../core/services/visible_followup_adapters.py#L185) |
| method | `OllamaFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L230) |
| class | `OpenAICompatFollowupAdapter` | `` | Follow-up via OpenAI-compatible ``/chat/completions`` SSE streams. | [src](../../../core/services/visible_followup_adapters.py#L544) |
| method | `OpenAICompatFollowupAdapter.__init__` | `(self, *, provider_id)` | — | [src](../../../core/services/visible_followup_adapters.py#L554) |
| method | `OpenAICompatFollowupAdapter._normalize_assistant_tool_calls` | `(self, tool_calls)` | Normalize assistant tool_calls to match the OpenAI chat-completions | [src](../../../core/services/visible_followup_adapters.py#L557) |
| method | `OpenAICompatFollowupAdapter._build_request` | `(self, *, model, messages, tool_definitions, temperature=…, top_p=…, tool_choice=…, extra_body=…, spor=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L592) |
| method | `OpenAICompatFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Turn accumulated exchanges into OpenAI-compat tool messages. | [src](../../../core/services/visible_followup_adapters.py#L750) |
| method | `OpenAICompatFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, autonomous=…, _length_retry=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L796) |
| class | `CodexFollowupAdapter` | `` | Follow-up via the OpenAI Codex Responses API (chatgpt.com/backend-api). | [src](../../../core/services/visible_followup_adapters.py#L1247) |
| method | `CodexFollowupAdapter._build_input` | `(self, base_messages, exchanges)` | — | [src](../../../core/services/visible_followup_adapters.py#L1261) |
| method | `CodexFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1294) |

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
| function | `_er_runtime_processen` | `()` | Runtime-processen dispatcher ikke. Den må forlige, ikke starte. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L45) |
| function | `_besked_fra` | `(record)` | Den oprindelige anmodning — det er DEN opgaven handler om. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L51) |
| function | `recover_due_once` | `(*, owner=…)` | Tag ÉN forfalden opgave og start dens fortsættelse. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L62) |
| function | `signal_recovery_dispatcher` | `()` | Væk dispatcheren nu — kaldes lige efter en durabel afregning. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L129) |
| function | `_loop` | `()` | — | [src](../../../core/services/visible_run_recovery_dispatcher.py#L134) |
| function | `start_recovery_dispatcher` | `()` | Start dispatcheren. `False` = den kører ikke her (og skal ikke). | [src](../../../core/services/visible_run_recovery_dispatcher.py#L148) |
| function | `stop_recovery_dispatcher` | `()` | Stop uden at starte nyt arbejde. En nedlukning afregner, den dispatcher ikke. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L165) |

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
| function | `has_completion_evidence` | `(text)` | Conservative positive evidence used only after a forced final round. | [src](../../../core/services/visible_run_terminal_recovery.py#L31) |
| class | `AgenticExitResolution` | `` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L42) |
| function | `resolve_agentic_exit` | `(*, exit_reason, final_text, finish_reason=…, forced_finalize=…, pending_tool_intent=…, recovery_attempt=…, recovery_limit=…)` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L49) |

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
| function | `_publicer_approval_requested` | `(*, approval_id, tool, run_id, session_id, result)` | Haendelse naar et godkendelses-kort BLIVER LAVET. | [src](../../../core/services/visible_runs.py#L324) |
| function | `_persist_pending_approvals` | `()` | — | [src](../../../core/services/visible_runs.py#L353) |
| class | `VisibleRun` | `` | — | [src](../../../core/services/visible_runs.py#L405) |
| class | `VisibleRunController` | `` | — | [src](../../../core/services/visible_runs.py#L444) |
| method | `VisibleRunController.attach_stream` | `(self, stream)` | — | [src](../../../core/services/visible_runs.py#L460) |
| method | `VisibleRunController.clear_stream` | `(self)` | — | [src](../../../core/services/visible_runs.py#L463) |
| method | `VisibleRunController.cancel` | `(self)` | — | [src](../../../core/services/visible_runs.py#L466) |
| method | `VisibleRunController.is_cancelled` | `(self)` | — | [src](../../../core/services/visible_runs.py#L473) |
| function | `_thinking_for_round` | `(run, exchanges)` | Tænknings-tilstand for en agentisk FØLGE-runde. | [src](../../../core/services/visible_runs.py#L492) |
| function | `is_visible_run_alive` | `(run_id)` | Den AUTORITATIVE liveness-test — CROSS-PROCES. | [src](../../../core/services/visible_runs.py#L516) |
| function | `start_visible_run` | `(message, session_id=…, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, local_tool_exec=…)` | Begin a visible run. | [src](../../../core/services/visible_runs.py#L578) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_runs.py#L891) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_runs.py#L949) |
| function | `_compact_llm_for_run` | `(prompt)` | Call the compact LLM for run-level summarisation (monkeypatchable). | [src](../../../core/services/visible_runs.py#L1176) |
| function | `_handle_compact_command` | `(run)` | /compact: komprimér nu og giv Jarvis en besked at svare paa. | [src](../../../core/services/visible_runs.py#L1182) |
| function | `_stream_visible_run` | `(run, *, force_user_id=…, tool_scope=…)` | — | [src](../../../core/services/visible_runs.py#L1203) |
| function | `_native_tool_calls_to_capabilities` | `(tool_calls)` | Convert Ollama native tool_calls to capability-plan entries (legacy compat). | [src](../../../core/services/visible_runs.py#L6373) |
| function | `_finalize_second_pass_visible_text` | `(text, *, fallback)` | — | [src](../../../core/services/visible_runs.py#L6445) |
| function | `_bounded_error` | `(error_message, limit=…)` | — | [src](../../../core/services/visible_runs.py#L6478) |
| function | `_sse` | `(event, data)` | — | [src](../../../core/services/visible_runs.py#L6485) |
| class | `PresentationInvariantError` | `` | Raised when user-visible text contains internal runtime markers. | [src](../../../core/services/visible_runs.py#L6489) |
| function | `_assert_presentation_invariant` | `(text)` | — | [src](../../../core/services/visible_runs.py#L6515) |
| function | `_bash_hint` | `(cmd)` | Hvad kommandoen egentlig GØR — ikke dens første ord. | [src](../../../core/services/visible_runs.py#L6666) |
| function | `_hoved_og_genstand` | `(ord_)` | «grep tool_calls» — kommandoen og det den blev kørt på. | [src](../../../core/services/visible_runs.py#L6699) |
| function | `_tool_label` | `(tool_name, arguments=…)` | — | [src](../../../core/services/visible_runs.py#L6715) |
| function | `_parse_tc_args` | `(tc)` | Extract arguments dict from a tool call (handles both string and dict forms). | [src](../../../core/services/visible_runs.py#L6752) |
| function | `_maybe_fallback_for_autonomous` | `(run, exc)` | Task 10-beslutningsseam: skal en fejlet model-stream faldes til poolen? | [src](../../../core/services/visible_runs.py#L6764) |
| function | `_complete_visible_run_from_fallback` | `(run, fallback)` | Terminal completion for et AUTONOMT run hvis model-stream fejlede og blev | [src](../../../core/services/visible_runs.py#L6808) |
| function | `_fail_visible_run` | `(run, error_message, *, partial_text=…)` | — | [src](../../../core/services/visible_runs.py#L6866) |
| function | `_cancel_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6940) |
| function | `register_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6993) |
| function | `get_visible_run_controller` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7031) |
| function | `cancel_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7035) |
| function | `unregister_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L7046) |
| function | `get_active_visible_run` | `()` | — | [src](../../../core/services/visible_runs.py#L7060) |
| function | `get_visible_work` | `()` | — | [src](../../../core/services/visible_runs.py#L7083) |
| function | `get_visible_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L7115) |
| function | `get_visible_selected_work_surface` | `()` | — | [src](../../../core/services/visible_runs.py#L7142) |
| function | `get_visible_selected_work_item` | `()` | — | [src](../../../core/services/visible_runs.py#L7173) |
| function | `get_visible_selected_work_note` | `()` | — | [src](../../../core/services/visible_runs.py#L7225) |
| function | `get_last_visible_run_outcome` | `()` | — | [src](../../../core/services/visible_runs.py#L7260) |
| function | `get_last_visible_capability_use` | `()` | — | [src](../../../core/services/visible_runs.py#L7264) |
| function | `set_last_visible_capability_use` | `(run, *, capability_id, invocation, capability_arguments=…, argument_source=…)` | — | [src](../../../core/services/visible_runs.py#L7281) |
| function | `_update_cognitive_systems_async` | `(*, run_id, session_id, model, user_message, assistant_response, outcome_status)` | Fire-and-forget updates to all cognitive accumulation systems. | [src](../../../core/services/visible_runs.py#L7331) |

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

## `core/services/visible_runs_learning_signals.py`
_Post-run learning signals for a visible run (extracted from visible_runs.py,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `er_brugerafbrydelse` | `(fejl)` | True hvis fejlteksten beskriver en afbrydelse frem for en fejl. | [src](../../../core/services/visible_runs_learning_signals.py#L29) |
| function | `tool_names` | `(collected_native_tool_calls)` | Names of the native tool calls in order (objects or OpenAI-style dicts). | [src](../../../core/services/visible_runs_learning_signals.py#L35) |
| function | `record_visible_run_learning_signals` | `(*, run_ref, collected_native_tool_calls, outcome_status, outcome_error, followup_text, output_tokens)` | — | [src](../../../core/services/visible_runs_learning_signals.py#L53) |

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
| function | `_normaliser_tekstblokke` | `(blocks)` | Samme blokstruktur-rettelse på tekstblokkene som på `content`. | [src](../../../core/services/visible_runs_outcomes.py#L88) |
| function | `_med_udgivne_filer` | `(blocks, run)` | Laeg turens udgivne filer BAGEST i blok-arrayet. | [src](../../../core/services/visible_runs_outcomes.py#L108) |
| function | `_indsaet_ved_deres_vaerktoej` | `(blocks, filer)` | Sæt hver udgiven fil DÉR hvor den blev lavet. | [src](../../../core/services/visible_runs_outcomes.py#L128) |
| function | `_with_thinking_block` | `(blocks, run, reasoning)` | Sæt turens tænkning FORREST i blok-arrayet, hvis der blev tænkt. | [src](../../../core/services/visible_runs_outcomes.py#L176) |
| function | `_persist_session_assistant_message` | `(run, text, *, reasoning_content=…, blocks=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L224) |
| function | `run_er_terminal` | `(run_id)` | Er runnet slut? ``None`` = kunne ikke afgoeres. | [src](../../../core/services/visible_runs_outcomes.py#L441) |
| function | `_append_chat_message_with_retry` | `(*, session_id, role, content, reasoning_content=…, content_json=…, tool_name=…, tool_arguments=…, full_content=…, _backoffs=…)` | H5 persist-retry (spec §11.2 P5): persistering må ALDRIG tabes tavst pga. | [src](../../../core/services/visible_runs_outcomes.py#L482) |
| function | `_survival_or_fallback` | `()` | OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen svigter, lad Jarvis TALE fra | [src](../../../core/services/visible_runs_outcomes.py#L537) |
| function | `_session_last_role` | `(session_id)` | Sidste persisterede besked-rolle for en session (idempotens for invarianten). | [src](../../../core/services/visible_runs_outcomes.py#L551) |
| function | `_guarantee_visible_outcome` | `(run)` | LIVSCYKLUS-INVARIANT (Bjørn 29. jun, #1): en completed INTERAKTIV run må ALDRIG | [src](../../../core/services/visible_runs_outcomes.py#L566) |
| function | `set_last_visible_run_outcome` | `(run, *, status, error=…, text_preview=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L587) |
| function | `persist_visible_run_start` | `(run)` | Skriv en ``running``-række i ``visible_runs`` i det øjeblik runnet starter. | [src](../../../core/services/visible_runs_outcomes.py#L648) |
| function | `_sikr_profil_kolonner` | `(conn)` | Doven migration — samme moenster som `kind` paa chat_sessions. | [src](../../../core/services/visible_runs_outcomes.py#L697) |
| function | `_profil_for_raekken` | `(run)` | (navn, hash, skema-version) for koerslen. Selv-sikker. | [src](../../../core/services/visible_runs_outcomes.py#L718) |
| function | `stamp_visible_run_interrupted` | `(run_id, *, reason=…)` | Stempl en ``running``-række som ``interrupted`` — kun hvis den stadig kører. | [src](../../../core/services/visible_runs_outcomes.py#L732) |
| function | `_persist_visible_run_outcome` | `(run, *, status, finished_at, text_preview=…, error=…)` | — | [src](../../../core/services/visible_runs_outcomes.py#L796) |

## `core/services/visible_runs_sse_v2.py`
_Translator: legacy SSE-events → Anthropic-style v2-protokol._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolEchoFilter` | `` | Streaming-backstop mod at modellen ekkoer rå tool-output i sit svar. | [src](../../../core/services/visible_runs_sse_v2.py#L75) |
| method | `ToolEchoFilter.__init__` | `(self, tool_names=…)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L86) |
| method | `ToolEchoFilter._is_echo_line` | `(self, line)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L98) |
| method | `ToolEchoFilter.feed` | `(self, text)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L102) |
| method | `ToolEchoFilter.flush` | `(self)` | — | [src](../../../core/services/visible_runs_sse_v2.py#L151) |
| function | `_parse_legacy_sse` | `(chunk)` | Parse en legacy SSE event-blok til (event_name, payload_dict). | [src](../../../core/services/visible_runs_sse_v2.py#L161) |
| function | `_run_still_active` | `(run_id)` | True hvis dette run stadig kører server-side. Fail-safe: antag AKTIVT ved fejl, | [src](../../../core/services/visible_runs_sse_v2.py#L189) |
| function | `translate_to_v2` | `(legacy_iter, *, run_id=…, model=…, provider=…, lane=…, session_id=…, ping_interval_s=…)` | Konverter legacy SSE-stream til Anthropic-style v2 protokol. | [src](../../../core/services/visible_runs_sse_v2.py#L217) |

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

## `core/services/visible_terminal_policy.py`
_Single source of truth for visible task terminal decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TerminalState` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L14) |
| class | `TerminalEvidence` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L23) |
| class | `TerminalDecision` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L36) |
| function | `has_pending_tool_intent` | `(text)` | — | [src](../../../core/services/visible_terminal_policy.py#L51) |
| function | `is_recoverable_exit_reason` | `(reason)` | — | [src](../../../core/services/visible_terminal_policy.py#L55) |
| function | `classify_terminal` | `(evidence)` | — | [src](../../../core/services/visible_terminal_policy.py#L92) |
| function | `recovery_notice` | `(reason, *, continuing=…)` | — | [src](../../../core/services/visible_terminal_policy.py#L128) |

## `core/services/visible_text_scrub.py`
_Fjern runtime'ens interne markører fra den tekst brugeren ser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_slut_paa_note` | `(tekst, start)` | Indeks EFTER den klamme der lukker noten der begynder på `start`. | [src](../../../core/services/visible_text_scrub.py#L52) |
| function | `_foerste_markoer` | `(tekst, fra=…)` | Indeks på den tidligste interne markør fra `fra`, eller -1. | [src](../../../core/services/visible_text_scrub.py#L70) |
| function | `fjern_interne_markoerer` | `(tekst)` | Teksten uden runtime-noter, med tomme linjer ryddet op efter sig. | [src](../../../core/services/visible_text_scrub.py#L77) |
| function | `_ryd_tomrum` | `(tekst)` | Noten stod i sit eget afsnit. Fjerner man den, står der tre tomme | [src](../../../core/services/visible_text_scrub.py#L95) |
| function | `_uden_markoerord` | `(tekst)` | Teksten med selve markoer-ordene fjernet, men indholdet bevaret. | [src](../../../core/services/visible_text_scrub.py#L103) |
| class | `StroemSkrubber` | `` | Samme fjernelse, men på en strøm hvor markøren kan være delt over flere | [src](../../../core/services/visible_text_scrub.py#L110) |
| method | `StroemSkrubber.__init__` | `(self)` | — | [src](../../../core/services/visible_text_scrub.py#L119) |
| method | `StroemSkrubber.foed` | `(self, stykke)` | Den del af `stykke` der trygt kan sendes videre nu. | [src](../../../core/services/visible_text_scrub.py#L122) |
| method | `StroemSkrubber.skyl` | `(self)` | Resten, når strømmen er slut. Uafsluttede noter ryger. | [src](../../../core/services/visible_text_scrub.py#L137) |
| function | `fjern_interne_markoerer_stroem` | `(buffer)` | (klar-til-udsendelse, hale-der-skal-holdes-tilbage). | [src](../../../core/services/visible_text_scrub.py#L144) |
| function | `_klap_tomrum_sammen` | `(tekst)` | Tre eller flere linjeskift bliver til ét afsnitsbrud. | [src](../../../core/services/visible_text_scrub.py#L191) |
| function | `_muligt_praefiks` | `(buffer)` | Den slut-stump der kunne være starten på en markør — ellers «». | [src](../../../core/services/visible_text_scrub.py#L202) |

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
| function | `_bruger_til_stede` | `(run)` | Er der et menneske i den anden ende af den her tur? | [src](../../../core/services/visible_tool_exec.py#L36) |
| function | `run_tool_batch` | `(tool_calls, *, run, loop, tool_scope, step_counter, heartbeat_interval_s, heartbeat_phase, out, heartbeat_extra=…, exec_start=…, er_afbrudt=…)` | Announce → execute → heartbeat pump for one tool batch. | [src](../../../core/services/visible_tool_exec.py#L66) |

## `core/services/visible_turn_accumulator.py`
_Turens content-blokke, samlet i den rækkefølge de faktisk opstod._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TurnAccumulator` | `` | Samler tekst-segmenter, værktøjskald og deres rækkefølge for én tur. | [src](../../../core/services/visible_turn_accumulator.py#L30) |
| method | `TurnAccumulator.add_text` | `(self, chunk)` | Læg tekst i det ÅBNE segment, eller åbn et nyt. | [src](../../../core/services/visible_turn_accumulator.py#L62) |
| method | `TurnAccumulator.close_segment` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L76) |
| method | `TurnAccumulator.note_text` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L80) |
| method | `TurnAccumulator.note_tool` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L84) |
| method | `TurnAccumulator._luk_tanketid` | `(self)` | En tanke varer til det NÆSTE begynder — ikke til dens sidste token. | [src](../../../core/services/visible_turn_accumulator.py#L88) |
| method | `TurnAccumulator.add_tools` | `(self, tool_calls, results)` | Optag et batch af kald og deres resultater. Kaster ALDRIG. | [src](../../../core/services/visible_turn_accumulator.py#L102) |
| method | `TurnAccumulator.add_thinking` | `(self, chunk)` | Læg reasoning i det ÅBNE tanke-segment, eller åbn et nyt. | [src](../../../core/services/visible_turn_accumulator.py#L141) |
| method | `TurnAccumulator.close_thinking` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L160) |
| method | `TurnAccumulator._nu` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L163) |
| method | `TurnAccumulator.thinking_seconds` | `(self)` | Sekunder pr. tanke-segment; None hvor der ikke blev maalt noget. | [src](../../../core/services/visible_turn_accumulator.py#L169) |
| method | `TurnAccumulator.add_round_label` | `(self, etik)` | Gem en runde-etiket som den blok Claude Desktop selv gemmer. | [src](../../../core/services/visible_turn_accumulator.py#L182) |
| method | `TurnAccumulator.build_blocks` | `(self, text)` | Den kanoniske blok-liste for turen. | [src](../../../core/services/visible_turn_accumulator.py#L212) |
| function | `coerce_tool_input` | `(raw)` | Normalisér tool-input til et DICT. | [src](../../../core/services/visible_turn_accumulator.py#L232) |

## `core/services/visible_turn_blocks.py`
_Den kanoniske content-blok-array for en assistent-tur (spec §4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_label` | `(tool_name, arguments=…)` | Narrationen for ét værktøjskald — samme tekst som live-visningen brugte. | [src](../../../core/services/visible_turn_blocks.py#L31) |
| function | `_build_progress_blocks` | `(tool_calls, tool_results)` | Byg det FLADE progress-spor for en tur (spec §5). | [src](../../../core/services/visible_turn_blocks.py#L42) |
| function | `_tanke_blok` | `(par)` | Én tanke-blok. Halen er nok: klienten viser den foldet ud, og en hel | [src](../../../core/services/visible_turn_blocks.py#L88) |
| function | `_build_turn_blocks` | `(*, text, tool_calls, tool_results, interleave=…, text_segments=…, thinking_segments=…, thinking_seconds=…)` | Byg den kanoniske content-blok-array for en assistant-tur (spec §4). | [src](../../../core/services/visible_turn_blocks.py#L104) |

