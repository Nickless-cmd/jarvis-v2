# `core.services.28` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/versioneret_json_svar.py`
_Et færdigt HTTP-svar pr. version — serialiseret og komprimeret ÉN gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vil_have_gzip` | `(accept_encoding)` | — | [src](../../../core/services/versioneret_json_svar.py#L35) |
| function | `versioneret_json_svar` | `(*, noegle, version, etag, accept_encoding, indhold)` | Byg (eller genbrug) svaret for `version`. `indhold` kaldes kun ved ny version. | [src](../../../core/services/versioneret_json_svar.py#L44) |

## `core/services/veto_gate.py`
_Adaptive veto gate — pre-execution hook that pauses tool calls when pushback is firm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_negated` | `(user_message, consent_start_idx)` | True if a negation word appears within ~30 chars BEFORE the consent token. | [src](../../../core/services/veto_gate.py#L72) |
| function | `_check_token_signal_gate` | `(user_message, tool_name)` | Check if user message contains explicit consent that overrides veto. | [src](../../../core/services/veto_gate.py#L85) |
| function | `_maybe_record_override_from_token_signal` | `(tool_name)` | If the token-signal gate detected an override pattern, check if there | [src](../../../core/services/veto_gate.py#L113) |
| function | `_ensure_veto_events_table` | `()` | Ensure the veto_events table exists. | [src](../../../core/services/veto_gate.py#L178) |
| function | `log_veto_event` | `(tool_name, user_message, feeling, intensity, evidence_summary, veto_result, resolution=…)` | Log a veto decision to the veto_events table. | [src](../../../core/services/veto_gate.py#L188) |
| function | `resolve_veto_event` | `(event_id, resolution)` | Mark a veto event as resolved (overridden, honored, false_positive). | [src](../../../core/services/veto_gate.py#L229) |
| function | `veto_event_stats` | `(tool_name=…, limit=…)` | Read recent veto events for observability. | [src](../../../core/services/veto_gate.py#L273) |
| function | `_ensure_veto_adaptive_counters_table` | `()` | Create the table if missing + migrate legacy KV entries once per process. | [src](../../../core/services/veto_gate.py#L389) |
| function | `_adjust_counter` | `(tool_name, feeling, kind, delta)` | Read-modify-write a counter ("overrides" or "honored") in veto_adaptive_counters. | [src](../../../core/services/veto_gate.py#L444) |
| function | `_get_counter` | `(tool_name, feeling, kind)` | Read a counter without modification. | [src](../../../core/services/veto_gate.py#L481) |
| function | `_get_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L498) |
| function | `_increment_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L502) |
| function | `_get_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L506) |
| function | `_increment_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L510) |
| function | `_base_threshold` | `(tool_name, feeling)` | Look up per-(tool, feeling) base from _BASE_THRESHOLDS. | [src](../../../core/services/veto_gate.py#L514) |
| function | `_adaptive_threshold` | `(tool_name, feeling, intensity)` | Compute the effective veto threshold for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L523) |
| function | `check_veto` | `(tool_name, user_message=…, session_id=…, record_event=…, user_present=…)` | Check if a tool call should be vetoed. | [src](../../../core/services/veto_gate.py#L593) |
| function | `_extract_feeling` | `(section)` | Extract the feeling name from the pushback section. | [src](../../../core/services/veto_gate.py#L780) |
| function | `_extract_intensity` | `(section)` | Extract the intensity value from the pushback section. | [src](../../../core/services/veto_gate.py#L790) |
| function | `_summarize_evidence` | `(section)` | Extract a brief evidence summary from the pushback section. | [src](../../../core/services/veto_gate.py#L803) |
| function | `_extract_action` | `(section)` | Extract the action tier from the pushback section text. | [src](../../../core/services/veto_gate.py#L816) |
| function | `_has_evidence` | `(section)` | Check if the pushback section contains evidence markers. | [src](../../../core/services/veto_gate.py#L826) |
| function | `_format_veto_reason` | `(section, tool_name, event_id=…)` | Format a human-readable veto reason. | [src](../../../core/services/veto_gate.py#L831) |
| function | `build_veto_gate_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/veto_gate.py#L861) |
| function | `record_override` | `(tool_name, feeling)` | Record that the user overrode a veto for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L893) |
| function | `record_jarvis_override` | `(tool_name, feeling)` | Registrér at JARVIS — ikke brugeren — overstyrede en gate for dette (tool, feeling). | [src](../../../core/services/veto_gate.py#L925) |
| function | `_emit_veto_gate_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/veto_gate.py#L955) |

## `core/services/visible_autonomous_run.py`
_Autonome (heartbeat-startede) synlige runs: starter og observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_autonomous_run.py#L21) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_autonomous_run.py#L79) |

## `core/services/visible_first_pass_pump.py`
_Worker-thread pump for the first visible model stream._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pump_first_pass` | `(run, *, controller, tool_scope, loop, queue, sentinel, stream_fn=…)` | — | [src](../../../core/services/visible_first_pass_pump.py#L10) |

## `core/services/visible_first_pass_text.py`
_Akkumuleret first-pass-tekst med indbygget degenerations-vagt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FirstPassText` | `` | Samler first-pass-tekst og siger til når den degenererer. | [src](../../../core/services/visible_first_pass_text.py#L31) |
| method | `FirstPassText.text` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L39) |
| method | `FirstPassText.__len__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L42) |
| method | `FirstPassText.__bool__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L45) |
| method | `FirstPassText.feed` | `(self, delta)` | Tilføj en delta. Returnér (degenereret, årsag). | [src](../../../core/services/visible_first_pass_text.py#L48) |

## `core/services/visible_followup.py`
_Provider-neutral agentic follow-up dispatcher._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supported_followup_providers` | `()` | Provider ids with a working follow-up adapter. | [src](../../../core/services/visible_followup.py#L121) |
| function | `stream_visible_followup` | `(*, provider, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, session_id=…, autonomous=…, trailing_messages=…)` | Dispatch to the provider's follow-up adapter; yield FollowupEvents. | [src](../../../core/services/visible_followup.py#L131) |
| function | `synthesize_nonthinking_rescue` | `(*, provider, model, base_messages, exchanges)` | Sidste-udvejs synteseturn der OMGÅR DeepSeek #1453 (tom completion efter | [src](../../../core/services/visible_followup.py#L217) |
| function | `synthesize_final_answer` | `(*, provider, model, base_messages, exchanges, on_delta=…)` | HARNESS-FINALIZE lag 2b (Bjørn 4. jul, provider-AGNOSTISK): ét tool-FRIT | [src](../../../core/services/visible_followup.py#L301) |
| function | `synthesize_continuation` | `(*, provider, model, base_messages, exchanges, partial_text, continuation_instruction=…)` | CUT-OFF-FORTSÆTTELSE (2026-08-20): når provideren lukkede streamen med | [src](../../../core/services/visible_followup.py#L380) |
| function | `agentic_round_retry_enabled` | `()` | Er rund-niveau stream-retry (Fase 1) slået til? Default False. | [src](../../../core/services/visible_followup.py#L485) |
| function | `provider_failover_enabled` | `()` | Er visible-lane provider-failover (Fase 3, spec §11.2) slået til? Default False. | [src](../../../core/services/visible_followup.py#L529) |
| function | `pick_failover_target` | `(current_provider, current_model)` | Vælg en kendt-pålidelig fallback-provider for RESTEN af denne tur (S6/§11.2). | [src](../../../core/services/visible_followup.py#L548) |
| function | `inject_fault` | `(shape, *, partial_deltas=…, drop_as_exception=…, http_status=…, fire_once=…, fail_times=…, recover_text=…)` | Registrér en fejl-injektion for NÆSTE ``stream_visible_followup``-kald. | [src](../../../core/services/visible_followup.py#L612) |
| function | `clear_faults` | `()` | Fjern enhver aktiv injektion. Idempotent. TEST-ONLY. | [src](../../../core/services/visible_followup.py#L658) |
| class | `fault_injection` | `` | Context-manager der registrerer en injektion + RYDDER den ved exit | [src](../../../core/services/visible_followup.py#L665) |
| method | `fault_injection.__init__` | `(self, shape, **kwargs)` | — | [src](../../../core/services/visible_followup.py#L675) |
| method | `fault_injection.__enter__` | `(self)` | — | [src](../../../core/services/visible_followup.py#L679) |
| method | `fault_injection.__exit__` | `(self, *_exc)` | — | [src](../../../core/services/visible_followup.py#L683) |
| function | `_maybe_inject_fault` | `(round_index)` | Prod-no-op hook: returnér en event-iterator hvis en injektion er aktiv, | [src](../../../core/services/visible_followup.py#L688) |
| function | `_yield_injected_fault` | `(fault, round_index)` | Generér event-strømmen for en given injektion (test-only). | [src](../../../core/services/visible_followup.py#L721) |

## `core/services/visible_followup_adapters.py`
_Per-provider follow-up adapters (split from ``visible_followup.py``)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_billed_besked` | `(tr)` | Pixels som en user-besked — eller None naar resultatet ikke bar et billede. | [src](../../../core/services/visible_followup_adapters.py#L53) |
| function | `_billeder_efter_tool_svarene` | `(messages, billeder)` | Laeg billederne EFTER alle tool-svarene i runden, ikke mellem dem. | [src](../../../core/services/visible_followup_adapters.py#L72) |
| function | `_dt_ind` | `(session_id, tekst)` | Notér én delta i delta-sporets punkt «ind» — fra UDBYDEREN. | [src](../../../core/services/visible_followup_adapters.py#L104) |
| class | `OllamaFollowupAdapter` | `` | Follow-up via Ollama's ``/api/chat`` streaming NDJSON endpoint. | [src](../../../core/services/visible_followup_adapters.py#L135) |
| method | `OllamaFollowupAdapter._normalize_tool_calls` | `(self, tool_calls)` | Replay tool_calls — men REPARÉR afkortede/malformede argument-strenge først. | [src](../../../core/services/visible_followup_adapters.py#L158) |
| method | `OllamaFollowupAdapter._repair_arguments` | `(container)` | Hvis container['arguments'] er en STRENG der ikke er gyldig JSON → erstat med {}. | [src](../../../core/services/visible_followup_adapters.py#L184) |
| method | `OllamaFollowupAdapter._compact_exchanges` | `(self, exchanges)` | Bound Ollama follow-up replay so long tool loops do not 400. | [src](../../../core/services/visible_followup_adapters.py#L209) |
| method | `OllamaFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Replay exchanges as structured assistant + role=tool messages. | [src](../../../core/services/visible_followup_adapters.py#L264) |
| method | `OllamaFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L323) |
| class | `OpenAICompatFollowupAdapter` | `` | Follow-up via OpenAI-compatible ``/chat/completions`` SSE streams. | [src](../../../core/services/visible_followup_adapters.py#L639) |
| method | `OpenAICompatFollowupAdapter.__init__` | `(self, *, provider_id)` | — | [src](../../../core/services/visible_followup_adapters.py#L649) |
| method | `OpenAICompatFollowupAdapter._normalize_assistant_tool_calls` | `(self, tool_calls)` | Normalize assistant tool_calls to match the OpenAI chat-completions | [src](../../../core/services/visible_followup_adapters.py#L652) |
| method | `OpenAICompatFollowupAdapter._build_request` | `(self, *, model, messages, tool_definitions, temperature=…, top_p=…, tool_choice=…, extra_body=…, spor=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L687) |
| method | `OpenAICompatFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Turn accumulated exchanges into OpenAI-compat tool messages. | [src](../../../core/services/visible_followup_adapters.py#L859) |
| method | `OpenAICompatFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, session_id=…, autonomous=…, trailing_messages=…, _length_retry=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L919) |
| class | `CodexFollowupAdapter` | `` | Follow-up via the OpenAI Codex Responses API (chatgpt.com/backend-api). | [src](../../../core/services/visible_followup_adapters.py#L1415) |
| method | `CodexFollowupAdapter._build_input` | `(self, base_messages, exchanges, *, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1429) |
| method | `CodexFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1471) |

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
| class | `FollowupAdapter` | `` | — | [src](../../../core/services/visible_followup_events.py#L202) |
| method | `FollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…)` | — | [src](../../../core/services/visible_followup_events.py#L205) |

## `core/services/visible_followup_lean.py`
_Lean agentic-round-prompt transform + kill-switch (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_on_double_newline` | `(text)` | Split en sammensat besked i blokke på ``\n\n`` (assembly-join-grænsen). | [src](../../../core/services/visible_followup_lean.py#L66) |
| function | `_lean_strip_user_message` | `(text)` | Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing | [src](../../../core/services/visible_followup_lean.py#L71) |
| function | `build_lean_base_messages` | `(base_messages)` | Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2. | [src](../../../core/services/visible_followup_lean.py#L113) |
| function | `agentic_lean_prompt_enabled` | `()` | Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default True. | [src](../../../core/services/visible_followup_lean.py#L224) |

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
| function | `_model_is_deepseek_pro_tier` | `(model)` | True hvis modellen er den dyre deepseek-pro/reasoner-pro-tier. | [src](../../../core/services/visible_model.py#L100) |
| function | `_turn_is_owner_scoped` | `()` | Er den aktuelle tur owner-scoped (Bjørn)? Self-safe → False ved fejl. | [src](../../../core/services/visible_model.py#L112) |
| function | `gate_visible_model_tier` | `(provider, model, *, is_owner=…)` | WS5-gate: nedgradér deepseek-v4-pro → v4-flash medmindre (a) kill-switch- | [src](../../../core/services/visible_model.py#L123) |
| function | `_configured_provider_models` | `(provider)` | — | [src](../../../core/services/visible_model.py#L153) |
| function | `available_provider_models` | `(*, provider, auth_profile=…)` | — | [src](../../../core/services/visible_model.py#L175) |
| function | `execute_visible_model` | `(*, message, provider, model, session_id=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L267) |
| function | `stream_visible_model` | `(*, message, provider, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L326) |
| function | `available_ollama_models_for_visible_target` | `()` | — | [src](../../../core/services/visible_model.py#L398) |
| function | `_build_visible_input` | `(message, *, session_id, provider=…, model=…)` | — | [src](../../../core/services/visible_model.py#L454) |
| function | `_giv_modellen_oejne` | `(messages, *, session_id, model)` | Sæt billed-blokke på den sidste user-besked. Self-safe: fejl → uændret. | [src](../../../core/services/visible_model.py#L543) |
| function | `_build_visible_chat_messages_for_github` | `(message, *, session_id, provider=…, model=…)` | Build OpenAI chat-completions messages for the visible lane. | [src](../../../core/services/visible_model.py#L571) |
| function | `_split_dynamic_tail` | `(instruction)` | Separate volatile runtime instructions without changing their role. | [src](../../../core/services/visible_model.py#L663) |
| function | `_is_current_user_turn` | `(message, current_text)` | Match the persisted current turn, not merely any user-role runtime item. | [src](../../../core/services/visible_model.py#L677) |
| function | `_insert_system_tail_before_current_user` | `(messages, tail)` | Keep volatile prompt sections cache-late while preserving system attribution. | [src](../../../core/services/visible_model.py#L689) |
| function | `_insert_typed_system_tail_before_current_user` | `(items, tail)` | — | [src](../../../core/services/visible_model.py#L702) |
| function | `_visible_system_instruction_for_provider` | `(*, provider, model, user_message, session_id)` | — | [src](../../../core/services/visible_model.py#L716) |
| function | `_build_visible_prompt_assembly` | `(*, provider, model, user_message, session_id)` | Return the full PromptAssembly (including structured transcript). | [src](../../../core/services/visible_model.py#L731) |

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
| function | `_run_openai_compatible_visible` | `(*, provider, model, message, session_id, extra_body=…)` | Shared entry point for openai-compat visible providers. | [src](../../../core/services/visible_model_adapters.py#L607) |
| function | `visible_execution_readiness` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L715) |
| function | `_execute_phase1_model` | `(*, message, provider, model)` | — | [src](../../../core/services/visible_model_adapters.py#L873) |
| function | `_execute_openai_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L890) |
| function | `_stream_openai_codex_model` | `(*, message, model, session_id=…, controller=…)` | Real token-by-token streaming for the openai-codex provider. | [src](../../../core/services/visible_model_adapters.py#L915) |
| function | `_execute_openai_codex_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1018) |
| function | `_build_openai_codex_visible_prompt` | `(*, message, model, session_id)` | — | [src](../../../core/services/visible_model_adapters.py#L1044) |
| function | `_execute_github_copilot_visible_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1062) |
| function | `_stream_openai_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1144) |
| function | `_resolve_copilot_profile` | `(preferred)` | Find profilen der faktisk HAR github-copilot-creds. | [src](../../../core/services/visible_model_adapters.py#L1221) |
| function | `_stream_github_copilot_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1245) |
| function | `_load_openai_api_key` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1344) |
| function | `_load_openai_api_key_for_profile` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1352) |
| function | `_resolve_openai_profile` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1362) |
| function | `_openai_profile_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1380) |
| function | `_provider_profile_status` | `(*, provider, profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1398) |
| function | `_provider_router_config` | `(*, provider)` | — | [src](../../../core/services/visible_model_adapters.py#L1414) |
| function | `_post_openai_responses` | `(*, payload, api_key, base_url=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1424) |
| function | `_probe_openai_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L1441) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/visible_model_adapters.py#L1512) |

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
| function | `_raa_linjer` | `(response, maale_noegle=…)` | Rå linjer fra streamen — og, når sporet er tændt, HVOR tiden gik. | [src](../../../core/services/visible_model_sse.py#L177) |
| function | `_iter_sse_events` | `(response, *, provider=…, model=…, maale_noegle=…)` | Hærdet SSE-decoder (spec §1A + §11.1 A11). | [src](../../../core/services/visible_model_sse.py#L226) |

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

## `core/services/visible_post_tool_synthesis.py`
_Stream the existing tool-free final synthesis without buffering its deltas._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SynthesisDelta` | `` | — | [src](../../../core/services/visible_post_tool_synthesis.py#L17) |
| class | `SynthesisDone` | `` | — | [src](../../../core/services/visible_post_tool_synthesis.py#L22) |
| function | `stream_final_synthesis` | `(*, provider, model, base_messages, exchanges, min_chars=…)` | Yield clean text deltas, then the exact text the caller should persist. | [src](../../../core/services/visible_post_tool_synthesis.py#L26) |

## `core/services/visible_preview_crypto.py`
_Encrypt durable previews for visible member runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `member_for_run` | `(run)` | — | [src](../../../core/services/visible_preview_crypto.py#L7) |
| function | `protect_preview` | `(text, member)` | — | [src](../../../core/services/visible_preview_crypto.py#L19) |
| function | `reveal_preview` | `(text, user_id)` | — | [src](../../../core/services/visible_preview_crypto.py#L23) |

## `core/services/visible_run_abandonment.py`
_Hvad der sker naar et run doer midt-flugt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_loop_lag` | `()` | Hvor sultent var event-loopet lige nu? | [src](../../../core/services/visible_run_abandonment.py#L40) |
| function | `report_abandoned_run` | `(run, *, abort_kind, run_stage, visible_len)` | Rapportér et run der aldrig naaede sin beslutning. Kaster aldrig. | [src](../../../core/services/visible_run_abandonment.py#L53) |
| function | `abandon_bridge_records` | `(run)` | K6: giv runnets uafklarede godkendelses-poster deres AERLIGE udfald. | [src](../../../core/services/visible_run_abandonment.py#L92) |

## `core/services/visible_run_cost.py`
_Bogfoer en koersels omkostning — ét sted._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `bogfoer_koerslens_omkostning` | `(run, *, input_tokens, output_tokens, cache_hit_tokens, cache_miss_tokens, cost_usd=…)` | Skriv koerslens raekke i hovedbogen. | [src](../../../core/services/visible_run_cost.py#L37) |

## `core/services/visible_run_firstpass.py`
_Ventetiden foer modellens FOERSTE element — livstegn, sandhed og et loft._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `hjerteslag_fase` | `(ventet_s)` | Hvad hjerteslaget skal sige at den laver. | [src](../../../core/services/visible_run_firstpass.py#L100) |
| function | `loft_naaet` | `(ventet_s)` | Har vi ventet laengere end nogen sund koersel nogensinde har gjort? | [src](../../../core/services/visible_run_firstpass.py#L113) |
| function | `opgiv_tekst` | `(ventet_s, *, provider, model)` | Den besked brugeren faar. Den skal sige HVAD der skete og HVOR. | [src](../../../core/services/visible_run_firstpass.py#L118) |

## `core/services/visible_run_guard_notices.py`
_Værns-noterne — hvad Bjørn ser, og hvad modellen må se._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `forbindelsen_glippede` | `()` | P6 graceful-degrade: forbindelsen svigtede gentagne gange. Klasse 3. | [src](../../../core/services/visible_run_guard_notices.py#L85) |
| function | `loekken_tvang_en_afslutning` | `()` | Løkken tvang en afslutning med et ventende tool-intent. Klasse 3. | [src](../../../core/services/visible_run_guard_notices.py#L94) |
| function | `tool_call_loekke` | `(runder)` | Flere runder med værktøjskald og intet synligt svar. Klasse 3. | [src](../../../core/services/visible_run_guard_notices.py#L103) |
| function | `ingen_tekst_i_runder` | `(runder)` | Runder uden tekst overhovedet — KLASSE 1, den holder runnet i gang. | [src](../../../core/services/visible_run_guard_notices.py#L112) |
| function | `tomt_loefte_advarsel` | `()` | Advarslen til NÆSTE runde om et tomt løfte. Klasse 2 — MÆRKET. | [src](../../../core/services/visible_run_guard_notices.py#L128) |
| function | `systemmaerket` | `(tekst)` | Mærk en vilkårlig runtime-besked som fra systemet. Klasse 1 og 2. | [src](../../../core/services/visible_run_guard_notices.py#L151) |
| function | `er_menneske_note` | `(tekst)` | Er dette en klasse-3-note — altså til Bjørn og ikke til modellen? | [src](../../../core/services/visible_run_guard_notices.py#L183) |
| function | `er_handler_note` | `(tekst)` | Er dette en klasse-1-note? Den SKAL naa modellen; her kun til mærkning. | [src](../../../core/services/visible_run_guard_notices.py#L201) |
| function | `fjern_menneske_noter` | `(dele)` | Fjern klasse-3-noter fra de dele der bliver model-input. | [src](../../../core/services/visible_run_guard_notices.py#L213) |
| function | `fjern_menneske_noter_fra_historik` | `(historik)` | Fjern klasse-3-noter fra den PERSISTEREDE historik modellen får. | [src](../../../core/services/visible_run_guard_notices.py#L230) |

## `core/services/visible_run_interruption.py`
_Hvad afbrød et synligt run — til fejl-envelopen og Centralen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_visible_run_interruption` | `(error_message)` | — | [src](../../../core/services/visible_run_interruption.py#L17) |

## `core/services/visible_run_journal.py`
_Persist the visible run and its composer context for durable recovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mark_visible_run_started` | `(run, *, tool_scope=…, force_user_id=…)` | Record the settings a resumed run needs to keep its original lane. | [src](../../../core/services/visible_run_journal.py#L9) |

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
| function | `_udskydelses_backoff` | `(tidligere)` | Vent længere for hver gang samtalen var optaget — men aldrig i det uendelige. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L44) |
| function | `_er_runtime_processen` | `()` | Runtime-processen dispatcher ikke. Den må forlige, ikke starte. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L54) |
| function | `_besked_fra` | `(record)` | Den oprindelige anmodning — det er DEN opgaven handler om. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L60) |
| function | `_luk_afloest_raekke` | `(run_id, *, reason)` | Luk den afløste kørsels EGEN række i `visible_runs`. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L70) |
| function | `_samtalen_gik_videre` | `(session_id, efter)` | Er brugeren gået videre, siden den her kørsel døde? | [src](../../../core/services/visible_run_recovery_dispatcher.py#L111) |
| function | `recover_due_once` | `(*, owner=…)` | Tag ÉN forfalden opgave og start dens fortsættelse. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L157) |
| function | `signal_recovery_dispatcher` | `()` | Væk dispatcheren nu — kaldes lige efter en durabel afregning. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L332) |
| function | `_loop` | `()` | — | [src](../../../core/services/visible_run_recovery_dispatcher.py#L337) |
| function | `start_recovery_dispatcher` | `()` | Start dispatcheren. `False` = den kører ikke her (og skal ikke). | [src](../../../core/services/visible_run_recovery_dispatcher.py#L351) |
| function | `stop_recovery_dispatcher` | `()` | Stop uden at starte nyt arbejde. En nedlukning afregner, den dispatcher ikke. | [src](../../../core/services/visible_run_recovery_dispatcher.py#L368) |

## `core/services/visible_run_segment_exit.py`
_Afgoer hvad et agentisk segment blev til, og goer det durabelt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kaede_nr_eller_loft` | `(session_id)` | Hvor langt er genoptagelses-kaeden naaet for denne samtale? | [src](../../../core/services/visible_run_segment_exit.py#L46) |
| function | `afgoer_segment_udfald` | `(*, run_id, session_id, exit_reason, final_text=…, finish_reason=…, forced_finalize=…, pending_tool_intent=…, truncated=…)` | Skriv segmentets ophoer durabelt og giv dommen tilbage. | [src](../../../core/services/visible_run_segment_exit.py#L62) |

## `core/services/visible_run_segment_settlement.py`
_Ét sted hvor et unormalt segment-ophør bliver durabelt — før noget lukkes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `failure_class_for` | `(exit_reason)` | Grundens klasse. Ukendt → `RUNTIME`; vi gætter ikke på en udbyder. | [src](../../../core/services/visible_run_segment_settlement.py#L73) |
| class | `SegmentUdfald` | `` | Dommen, den durable post, og hvad kalderen skal sende ud. | [src](../../../core/services/visible_run_segment_settlement.py#L90) |
| function | `settle_user_stop` | `(*, run_id, session_id=…, task_id=…, reason=…)` | Brugeren trykkede stop. Det er endeligt — og skal skrives ned FØRST. | [src](../../../core/services/visible_run_segment_settlement.py#L106) |
| function | `settle_segment_exit` | `(*, run_id, session_id, exit_reason, final_text=…, finish_reason=…, forced_finalize=…, pending_tool_intent=…, explicit_user_cancel=…, waiting_for_user=…, recovery_attempt=…, recovery_limit=…, task_id=…, summary=…, checkpoint_ref=…, generation=…, owner=…, final_synthesis_attempted=…, failure_class=…)` | Gør segmentets ophør durabelt og sig hvad der skal sendes. | [src](../../../core/services/visible_run_segment_settlement.py#L132) |

## `core/services/visible_run_steers.py`
_Keep real mid-flight user steers distinct from runtime turn notices._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `append_real_user_steers` | `(exchanges, steers)` | Læg ægte klient-styringer i HISTORIKKEN — ikke i halen. | [src](../../../core/services/visible_run_steers.py#L12) |

## `core/services/visible_run_terminal_recovery.py`
_Resolve whether an agentic run segment completed or needs recovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `has_incompletion_evidence` | `(text)` | Explicit unfinished work; absence of a completion keyword is not proof. | [src](../../../core/services/visible_run_terminal_recovery.py#L32) |
| class | `AgenticExitResolution` | `` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L44) |
| function | `resolve_agentic_exit` | `(*, exit_reason, final_text, finish_reason=…, forced_finalize=…, pending_tool_intent=…, recovery_attempt=…, recovery_limit=…)` | — | [src](../../../core/services/visible_run_terminal_recovery.py#L51) |

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
| function | `_kald_digest` | `(tool_name, arguments)` | Digesten over kaldet — broens definition, ikke en ny. | [src](../../../core/services/visible_runs.py#L260) |
| function | `_godkendelses_ejer` | `(run)` | Hvem skal kunne svare paa dette kort? | [src](../../../core/services/visible_runs.py#L272) |
| function | `_friske_godkendelser` | `(raa)` | Genopliv KUN kort der stadig er inden for deres levetid. | [src](../../../core/services/visible_runs.py#L289) |
| function | `godkendelser_nu` | `()` | Kortene som de ER paa disken. Disken er sandheden, ikke processens kopi. | [src](../../../core/services/visible_runs.py#L341) |
| function | `saet_godkendelse` | `(approval_id, kort)` | Tilfoej ét kort — uden at overskrive den anden proces' kort. | [src](../../../core/services/visible_runs.py#L362) |
| function | `fjern_godkendelse` | `(approval_id)` | Fjern ét kort og giv det tilbage. `None` = det fandtes ikke. | [src](../../../core/services/visible_runs.py#L373) |
| function | `_publicer_approval_requested` | `(*, approval_id, tool, run_id, session_id, result)` | Haendelse naar et godkendelses-kort BLIVER LAVET. | [src](../../../core/services/visible_runs.py#L385) |
| class | `VisibleRun` | `` | — | [src](../../../core/services/visible_runs.py#L477) |
| class | `VisibleRunController` | `` | — | [src](../../../core/services/visible_runs.py#L526) |
| method | `VisibleRunController.attach_stream` | `(self, stream)` | — | [src](../../../core/services/visible_runs.py#L542) |
| method | `VisibleRunController.clear_stream` | `(self)` | — | [src](../../../core/services/visible_runs.py#L545) |
| method | `VisibleRunController.cancel` | `(self)` | — | [src](../../../core/services/visible_runs.py#L548) |
| method | `VisibleRunController.is_cancelled` | `(self)` | — | [src](../../../core/services/visible_runs.py#L555) |
| function | `_thinking_for_round` | `(run, exchanges)` | Tænknings-tilstand for en agentisk FØLGE-runde. | [src](../../../core/services/visible_runs.py#L574) |
| function | `is_visible_run_alive` | `(run_id)` | Den AUTORITATIVE liveness-test — CROSS-PROCES. | [src](../../../core/services/visible_runs.py#L598) |
| function | `start_visible_run` | `(message, session_id=…, approval_mode=…, thinking_mode=…, force_user_id=…, tool_scope=…, provider_override=…, model_override=…, local_tool_exec=…, surface=…)` | Begin a visible run. | [src](../../../core/services/visible_runs.py#L660) |
| function | `_compact_llm_for_run` | `(prompt)` | Call the compact LLM for run-level summarisation (monkeypatchable). | [src](../../../core/services/visible_runs.py#L1004) |
| function | `_handle_compact_command` | `(run)` | /compact: komprimér nu og giv Jarvis en besked at svare paa. | [src](../../../core/services/visible_runs.py#L1010) |
| function | `_stream_visible_run` | `(run, *, force_user_id=…, tool_scope=…)` | — | [src](../../../core/services/visible_runs.py#L1031) |
| function | `_native_tool_calls_to_capabilities` | `(tool_calls)` | Convert Ollama native tool_calls to capability-plan entries (legacy compat). | [src](../../../core/services/visible_runs.py#L6371) |
| function | `_finalize_second_pass_visible_text` | `(text, *, fallback)` | — | [src](../../../core/services/visible_runs.py#L6443) |
| function | `_bounded_error` | `(error_message, limit=…)` | — | [src](../../../core/services/visible_runs.py#L6476) |
| function | `_sse` | `(event, data)` | — | [src](../../../core/services/visible_runs.py#L6483) |
| class | `PresentationInvariantError` | `` | Raised when user-visible text contains internal runtime markers. | [src](../../../core/services/visible_runs.py#L6487) |
| function | `_assert_presentation_invariant` | `(text)` | — | [src](../../../core/services/visible_runs.py#L6513) |
| function | `_parse_tc_args` | `(tc)` | Extract arguments dict from a tool call (handles both string and dict forms). | [src](../../../core/services/visible_runs.py#L6544) |
| function | `_maybe_fallback_for_autonomous` | `(run, exc)` | Task 10-beslutningsseam: skal en fejlet model-stream faldes til poolen? | [src](../../../core/services/visible_runs.py#L6556) |
| function | `_complete_visible_run_from_fallback` | `(run, fallback)` | Terminal completion for et AUTONOMT run hvis model-stream fejlede og blev | [src](../../../core/services/visible_runs.py#L6600) |
| function | `_fail_visible_run` | `(run, error_message, *, partial_text=…)` | — | [src](../../../core/services/visible_runs.py#L6658) |
| function | `_cancel_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6732) |
| function | `register_visible_run` | `(run)` | — | [src](../../../core/services/visible_runs.py#L6785) |
| function | `get_visible_run_controller` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6823) |
| function | `cancel_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6827) |
| function | `unregister_visible_run` | `(run_id)` | — | [src](../../../core/services/visible_runs.py#L6838) |
| function | `get_active_visible_run` | `()` | — | [src](../../../core/services/visible_runs.py#L6852) |
| function | `get_last_visible_run_outcome` | `()` | — | [src](../../../core/services/visible_runs.py#L6886) |
| function | `get_last_visible_capability_use` | `()` | — | [src](../../../core/services/visible_runs.py#L6890) |
| function | `set_last_visible_capability_use` | `(run, *, capability_id, invocation, capability_arguments=…, argument_source=…)` | — | [src](../../../core/services/visible_runs.py#L6907) |
| function | `_update_cognitive_systems_async` | `(*, run_id, session_id, model, user_message, assistant_response, outcome_status)` | Fire-and-forget updates to all cognitive accumulation systems. | [src](../../../core/services/visible_runs.py#L6957) |

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

