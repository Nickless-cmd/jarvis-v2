# `core.services.06` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L24) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L204) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L205) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L222) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L232) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L236) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L269) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L343) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L366) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L448) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Map composer's thinking_mode to the right Deepseek model alias. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L548) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L584) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L639) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L666) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L693) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L718) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L735) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L759) |
| function | `_ofa_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L774) |
| function | `_ofa_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L781) |
| function | `_ofa_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L788) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L793) |
| function | `_arko_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L837) |
| function | `_arko_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L844) |
| function | `_arko_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L851) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L856) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L888) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message)` | Call the local Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L956) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1010) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1041) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1066) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1117) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1170) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1193) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1206) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1230) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1251) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1271) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1315) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1327) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1349) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1360) |

## `core/services/cheap_provider_runtime_selection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L40) |
| function | `_execute_provider_chat` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L47) |
| function | `provider_runtime_defaults` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L51) |
| function | `record_cheap_provider_invocation` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L55) |
| function | `cheap_lane_status_surface` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L77) |
| function | `invalidate_cheap_lane_status_cache` | `()` | Force-clear the status-surface and quota caches. | [src](../../../core/services/cheap_provider_runtime_selection.py#L128) |
| function | `test_provider_target` | `(*, provider, model, auth_profile, base_url=…, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L141) |
| function | `smoke_cheap_lane` | `(*, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L169) |
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L299) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L303) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L379) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L495) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L574) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L615) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L664) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L771) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L828) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L845) |
| function | `_record_provider_success` | `(*, provider, model, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L886) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L937) |
| function | `_decode_state_metadata` | `(state)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1002) |
| function | `_rolling_average` | `(*, current_avg, current_count, new_value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1013) |
| function | `_smoke_quality_score` | `(*, expected, actual)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1019) |
| function | `_normalize_probe_text` | `(value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1029) |

## `core/services/cheap_provider_runtime_streaming.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_streaming.py#L24) |
| function | `_iter_openai_compatible_chat_events` | `(*, provider, model, auth_profile, base_url, messages, tools=…, temperature=…, top_p=…)` | Stream OpenAI-compatible /chat/completions deltas via SSE. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L33) |
| function | `_list_openai_codex_models` | `()` | Static model list for OpenAI Codex (ChatGPT Plus OAuth). | [src](../../../core/services/cheap_provider_runtime_streaming.py#L315) |
| function | `_execute_openai_codex_chat` | `(*, model, auth_profile, base_url, message)` | Execute a chat call via OpenAI's Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L327) |
| function | `_convert_tools_to_responses_format` | `(tools)` | Convert Chat-Completions tool defs to Responses API format. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L480) |
| function | `_iter_openai_codex_chat_events` | `(*, model, auth_profile, base_url, message, tools=…, input_items=…)` | Stream raw SSE events from the OpenAI Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L512) |

## `core/services/chronicle_consolidation_brief_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_briefs_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_brief_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_brief_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_brief_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_briefs` | `(*, briefs, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, brief)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L326) |
| function | `_brief_type` | `(*, chronicle_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L356) |
| function | `_brief_weight` | `(*, chronicle_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L403) |
| function | `_weight_from_brief_type` | `(brief_type)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L454) |

## `core/services/chronicle_consolidation_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_proposal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_proposal_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L326) |
| function | `_proposal_type` | `(*, brief_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L356) |
| function | `_proposal_weight` | `(*, brief_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L403) |
| function | `_weight_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L454) |

## `core/services/chronicle_consolidation_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L36) |
| function | `refresh_runtime_chronicle_consolidation_signal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L59) |
| function | `build_runtime_chronicle_consolidation_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L90) |
| function | `_extract_chronicle_consolidation_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L123) |
| function | `_persist_chronicle_consolidation_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L280) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L349) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L368) |
| function | `_chronicle_type` | `(*, cadence_state, promotion_type, has_remembered_fact)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L406) |
| function | `_chronicle_weight` | `(*, cadence_state, has_promotion, contradiction_pressure, outcome_status)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L421) |
| function | `_focus_text` | `(outcome, cadence, *, domain_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L435) |
| function | `_summary_line` | `(*, chronicle_type, chronicle_focus)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L451) |
| function | `_grounding_mode` | `(*, has_private_state, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L457) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L476) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L483) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L490) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L496) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L508) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L519) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L527) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L533) |

## `core/services/chronicle_engine.py`
_Chronicle Engine — Jarvis' narrative autobiography that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ChronicleAppraisal` | `` | Structured chronicle context — replaces hardcoded narrative prompts. | [src](../../../core/services/chronicle_engine.py#L36) |
| function | `maybe_write_chronicle_entry` | `()` | Write a chronicle entry if enough time has passed since the last one. | [src](../../../core/services/chronicle_engine.py#L57) |
| function | `compare_self_over_time` | `()` | Temporal self-perception — how have I changed? | [src](../../../core/services/chronicle_engine.py#L208) |
| function | `build_chronicle_surface` | `()` | — | [src](../../../core/services/chronicle_engine.py#L236) |
| function | `get_chronicle_context_for_prompt` | `(n=…, max_chars=…)` | Return recent chronicle entries formatted for prompt injection. | [src](../../../core/services/chronicle_engine.py#L249) |
| function | `_build_appraisal` | `(recent_runs, period, previous_entries=…)` | Build a structured ChronicleAppraisal from raw run data. | [src](../../../core/services/chronicle_engine.py#L295) |
| function | `_build_narrative` | `(recent_runs, period, previous_entries=…)` | Build a chronicle entry narrative, preferring LLM prose. | [src](../../../core/services/chronicle_engine.py#L349) |
| function | `_render_template_narrative` | `(appraisal)` | Render a deterministic fallback narrative from a structured appraisal. | [src](../../../core/services/chronicle_engine.py#L379) |
| function | `_render_narrative_prompt` | `(appraisal)` | Render an LLM narrative prompt from a structured ChronicleAppraisal. | [src](../../../core/services/chronicle_engine.py#L400) |
| function | `_collect_topics` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L448) |
| function | `_sanitize_narrative` | `(text)` | — | [src](../../../core/services/chronicle_engine.py#L468) |
| function | `project_entry_to_markdown` | `(entry)` | — | [src](../../../core/services/chronicle_engine.py#L483) |
| function | `_chronicle_markdown_path` | `()` | — | [src](../../../core/services/chronicle_engine.py#L514) |
| function | `_rotate_chronicle_if_needed` | `(chronicle_path)` | — | [src](../../../core/services/chronicle_engine.py#L518) |
| function | `_coerce_text_list` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L545) |
| function | `_emit_degraded_event` | `(*, period, reason)` | — | [src](../../../core/services/chronicle_engine.py#L560) |
| function | `_extract_key_events` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L570) |
| function | `_extract_lessons` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L580) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L591) |

## `core/services/claim_scanner.py`
_Claim Scanner — output gate for the Lying Engine (Layer 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_active_time_pin` | `()` | Read the current Time Pin from the prompt contract's cache. | [src](../../../core/services/claim_scanner.py#L69) |
| function | `_extract_time_from_pin` | `(pin_text)` | Extract the 'LIGE NU' timestamp block from a Time Pin section. | [src](../../../core/services/claim_scanner.py#L78) |
| function | `_now_as_pin_string` | `()` | Get current time formatted as the Time Pin would show it. | [src](../../../core/services/claim_scanner.py#L90) |
| function | `_categorize_line` | `(line)` | For a single line of text, return list of (category, matched_text, match). | [src](../../../core/services/claim_scanner.py#L98) |
| function | `_verify_time_claim` | `(matched_text)` | Verify a time claim against the active Time Pin. | [src](../../../core/services/claim_scanner.py#L130) |
| function | `_verify_env_claim` | `(matched_text)` | Verify environment claims — non-trivial, always True for now (future: check tool cache). | [src](../../../core/services/claim_scanner.py#L175) |
| function | `_verify_system_claim` | `(matched_text)` | Verify system claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L180) |
| function | `_verify_stats_claim` | `(matched_text)` | Verify statistic claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L190) |
| function | `_repair_time_claim` | `(line, matched_text)` | Replace a time claim with the correct time from the Time Pin. | [src](../../../core/services/claim_scanner.py#L210) |
| function | `_is_planned_time_context` | `(line, matched_text)` | True hvis linjen indeholder ord der indikerer at tidspunktet er | [src](../../../core/services/claim_scanner.py#L234) |
| function | `_repair_claim` | `(line, category, matched_text)` | Apply category-specific repair to a line. | [src](../../../core/services/claim_scanner.py#L247) |
| function | `_system_footnote` | `(matched_text)` | 2026-07-06: byg en fodnote for en ⚙️ system-claim (IP/host/path) i den | [src](../../../core/services/claim_scanner.py#L290) |
| function | `_extract_number` | `(text)` | Extract the first number from a string for replacement. | [src](../../../core/services/claim_scanner.py#L306) |
| function | `_commit_exists` | `(h)` | True hvis `h` resolver til et commit i hovedrepoet. Fail-open: ved | [src](../../../core/services/claim_scanner.py#L333) |
| function | `flag_unknown_commit_hashes` | `(text, *, max_check=…)` | Markér backtick-wrappede commit-hashes der ikke findes i hovedrepoet. | [src](../../../core/services/claim_scanner.py#L352) |
| function | `_collect_unknown_commit_hash_footnotes` | `(text, *, max_check=…)` | 2026-07-06: samme detektion som flag_unknown_commit_hashes, men i stedet | [src](../../../core/services/claim_scanner.py#L383) |
| function | `scan_response` | `(text)` | Scan a response text for unverified factual claims and repair them. | [src](../../../core/services/claim_scanner.py#L411) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L495) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L503) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L533) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L605) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L673) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L700) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

## `core/services/code_aesthetic_daemon.py`
_Code aesthetic daemon — weekly aesthetic reflection on the codebase._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_code_aesthetic_daemon` | `()` | Run aesthetic analysis if cadence elapsed. Returns {generated, reflection}. | [src](../../../core/services/code_aesthetic_daemon.py#L39) |
| function | `get_latest_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L64) |
| function | `build_code_aesthetic_surface` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L68) |
| function | `_get_recent_git_changes` | `()` | Get last 10 commit messages and changed file summary. | [src](../../../core/services/code_aesthetic_daemon.py#L81) |
| function | `_generate_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L101) |
| function | `_store_reflection` | `(reflection, now)` | — | [src](../../../core/services/code_aesthetic_daemon.py#L119) |

## `core/services/cognitive_architecture_surface.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_cognitive_architecture_surface` | `()` | Cached MC/self-model cognitive-architecture-surface. Self-safe → falder til fersk build. | [src](../../../core/services/cognitive_architecture_surface.py#L11) |
| function | `_build_cognitive_architecture_surface_uncached` | `()` | Build a shared cognitive architecture surface for MC and self-model. | [src](../../../core/services/cognitive_architecture_surface.py#L23) |

## `core/services/cognitive_chronicle.py`
_Cognitive Chronicle — user-scoped read layer for chronicle entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `query_chronicle_for_user` | `(limit=…)` | Return chronicle entries visible to the current user. | [src](../../../core/services/cognitive_chronicle.py#L15) |

## `core/services/cognitive_core_experiments.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_build` | `(builder, system_id, label)` | Call a builder function, returning a disabled-stub on any error. | [src](../../../core/services/cognitive_core_experiments.py#L6) |
| function | `build_cognitive_core_experiments_surface` | `()` | Build shared runtime truth for the bounded cognitive-core experiment state. | [src](../../../core/services/cognitive_core_experiments.py#L31) |
| function | `_build_recurrence_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L100) |
| function | `_build_global_workspace_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L127) |
| function | `_build_hot_meta_cognition_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L155) |
| function | `_build_surprise_afterimage_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L182) |
| function | `_build_attention_blink_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L212) |
| function | `_activity_state` | `(*, enabled, active)` | — | [src](../../../core/services/cognitive_core_experiments.py#L239) |
| function | `_strongest_carry_item` | `(items)` | — | [src](../../../core/services/cognitive_core_experiments.py#L247) |

## `core/services/cognitive_episodes.py`
_Cognitive episodes as an active learning primitive._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_episode` | `(*, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Persist a cognitive episode and publish an eventbus signal. | [src](../../../core/services/cognitive_episodes.py#L25) |
| function | `record_visible_run_episode` | `(*, run_id, session_id=…, provider=…, model=…, status=…, user_message=…, assistant_text=…, error=…)` | Record a post-run episode grounded in the visible-run event trail. | [src](../../../core/services/cognitive_episodes.py#L176) |
| function | `derive_episode_fields` | `(*, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Derive the five cognitive dimensions plus next-behavior policy. | [src](../../../core/services/cognitive_episodes.py#L209) |
| function | `build_cognitive_episode_surface` | `(*, limit=…)` | Return active directives for the conductor/prompt path. | [src](../../../core/services/cognitive_episodes.py#L295) |
| function | `build_cognitive_episode_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/cognitive_episodes.py#L325) |
| function | `_tool_names_for_run` | `(run_id)` | — | [src](../../../core/services/cognitive_episodes.py#L341) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/cognitive_episodes.py#L368) |
| function | `_summarize_visible_run` | `(*, status, tool_names, assistant_text, error)` | — | [src](../../../core/services/cognitive_episodes.py#L387) |
| function | `_fallback_summary` | `(*, status, tool_names, error)` | — | [src](../../../core/services/cognitive_episodes.py#L398) |
| function | `_confidence` | `(*, status, error, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L406) |
| function | `_uncertainty_sources` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L416) |
| function | `_self_check` | `(*, status, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L435) |
| function | `_what_would_change_mind` | `(*, interrupted, proposal_error)` | — | [src](../../../core/services/cognitive_episodes.py#L445) |
| function | `_salience` | `(*, interrupted, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L453) |
| function | `_attention_directive` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L461) |
| function | `_ignore_or_defer` | `(*, tool_heavy, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L479) |
| function | `_learning_lesson` | `(*, interrupted, proposal_error, status, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L487) |
| function | `_policy_update` | `(*, interrupted, proposal_error, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L505) |
| function | `_social_directive` | `(*, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L515) |
| function | `_user_state_hypothesis` | `(*, user_l, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L521) |
| function | `_perception_directive` | `(*, tool_names, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L531) |
| function | `_observed_changes` | `(*, tool_names, status, error)` | — | [src](../../../core/services/cognitive_episodes.py#L539) |
| function | `_next_behavior` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy, status)` | — | [src](../../../core/services/cognitive_episodes.py#L548) |
| function | `_prompt_priority` | `(*, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L569) |

## `core/services/cognitive_state_assembly.py`
_Cognitive state assembly — closes the loop between accumulated state and visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cognitive_cache_key` | `(mode_key)` | — | [src](../../../core/services/cognitive_state_assembly.py#L68) |
| function | `_cache_ttl_seconds` | `()` | Read TTL from settings; default 120s. TTL=0 disables caching. | [src](../../../core/services/cognitive_state_assembly.py#L72) |
| function | `_cache_enabled` | `()` | Check if caching is enabled in settings. TTL=0 also disables. | [src](../../../core/services/cognitive_state_assembly.py#L82) |
| function | `_build_invalidation_snapshot` | `()` | Snapshot the key state signals that invalidate the cache. | [src](../../../core/services/cognitive_state_assembly.py#L94) |
| function | `_is_cache_valid` | `(cache_key)` | Check if cached state for `mode_key` (e.g. 'full') is fresh+coherent. | [src](../../../core/services/cognitive_state_assembly.py#L129) |
| function | `_get_cached_state` | `(cache_key)` | Return cached cognitive state string if valid, None otherwise. | [src](../../../core/services/cognitive_state_assembly.py#L145) |
| function | `_set_cached_state` | `(cache_key, text, sources)` | Store assembled cognitive state in shared_cache (cross-worker). | [src](../../../core/services/cognitive_state_assembly.py#L193) |
| function | `invalidate_cognitive_state_cache` | `()` | Explicitly invalidate all cognitive state caches across workers. | [src](../../../core/services/cognitive_state_assembly.py#L227) |
| function | `get_cognitive_state_cache_status` | `()` | Return cache status for MC transparency. | [src](../../../core/services/cognitive_state_assembly.py#L242) |
| function | `build_cognitive_state_for_prompt` | `(*, compact=…, force=…)` | Build the [COGNITIVE STATE] section for visible chat prompt injection. | [src](../../../core/services/cognitive_state_assembly.py#L295) |
| function | `build_cognitive_state_injection_surface` | `()` | MC surface showing exactly what was injected into the last visible prompt. | [src](../../../core/services/cognitive_state_assembly.py#L1005) |
| function | `_safe_call` | `(fn)` | Call a DB function, return None on any error. | [src](../../../core/services/cognitive_state_assembly.py#L1025) |
| function | `_safe_json` | `(value)` | Parse JSON string or return dict/list directly. | [src](../../../core/services/cognitive_state_assembly.py#L1034) |
| function | `_appraisal_record` | `(*, kind, state, evidence, allowed_effects, confidence, ttl_minutes=…)` | Structured truth record for optional narrative rendering. | [src](../../../core/services/cognitive_state_assembly.py#L1049) |
| function | `_build_cognitive_core_experiment_state_line` | `(*, compact)` | Build a bounded cognitive-state line for mainline experiment carry. | [src](../../../core/services/cognitive_state_assembly.py#L1074) |
| function | `_safe_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1138) |
| function | `_safe_cognitive_experiment_carry_frame` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1149) |
| function | `_narrativize_embodied_state` | `()` | LLM-narrativize current embodied state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1161) |
| function | `_narrativize_affective_state` | `()` | LLM-narrativize current affective meta state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1218) |
| function | `_narrativize_self_anchor` | `()` | LLM-narrativize the [SELF] ownership line from real personality state. | [src](../../../core/services/cognitive_state_assembly.py#L1271) |
| function | `_narrativize_boundary` | `()` | LLM-narrativize boundary awareness from real runtime context. | [src](../../../core/services/cognitive_state_assembly.py#L1320) |

## `core/services/cognitive_state_narrativizer.py`
_LLM-based narrativizer for cognitive state lines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_narrativizer_llm` | `(system_prompt, user_message)` | Call the compact LLM (heartbeat model) for narrative line generation. | [src](../../../core/services/cognitive_state_narrativizer.py#L44) |
| class | `_CachedNarrative` | `` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L72) |
| function | `_fingerprint` | `(state)` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L85) |
| function | `_generate_in_background` | `(*, line_key, fingerprint, system_prompt, user_message)` | Run the LLM call in a background thread and update cache. | [src](../../../core/services/cognitive_state_narrativizer.py#L90) |
| function | `narrativize_line` | `(*, line_key, state, system_prompt, user_message_builder, fallback=…)` | Return an LLM-narrativized line for this state, or fallback. | [src](../../../core/services/cognitive_state_narrativizer.py#L122) |
| function | `cache_snapshot` | `()` | Expose current cache state for MC observability. | [src](../../../core/services/cognitive_state_narrativizer.py#L199) |

## `core/services/collective_pulse_daemon.py`
_Collective Pulse — what is the air full of right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L43) |
| function | `_collective_dir` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L47) |
| function | `_load` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L51) |
| function | `_save` | `(data)` | — | [src](../../../core/services/collective_pulse_daemon.py#L67) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/collective_pulse_daemon.py#L79) |
| function | `_gather_week_text` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L86) |
| function | `_week_mood_trajectory` | `()` | Average mood over the week, if mood samples are available. | [src](../../../core/services/collective_pulse_daemon.py#L123) |
| function | `_describe_zeitgeist` | `(top_terms, mood_info)` | — | [src](../../../core/services/collective_pulse_daemon.py#L142) |
| function | `_write_weekly_note` | `(pulse)` | — | [src](../../../core/services/collective_pulse_daemon.py#L156) |
| function | `run_pulse` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L192) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/collective_pulse_daemon.py#L233) |
| function | `build_collective_pulse_surface` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L246) |
| function | `_surface_summary` | `(latest)` | — | [src](../../../core/services/collective_pulse_daemon.py#L259) |
| function | `build_collective_pulse_prompt_section` | `()` | Surface the week's zeitgeist while it's still current (within 7 days). | [src](../../../core/services/collective_pulse_daemon.py#L266) |

## `core/services/commit_gate_arbiter.py`
_Pre-eksekverings commit-gate arbitrage — udskilt fra visible_runs (Boy Scout, 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CommitGateOutcome` | `` | Udfald af commit-gate-arbitrage. ``blocked`` → værktøjet må ikke køre; ``soft_warn`` → | [src](../../../core/services/commit_gate_arbiter.py#L21) |
| function | `evaluate_commit_gates` | `(*, name, arguments, user_message, session_id, run_id)` | Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér | [src](../../../core/services/commit_gate_arbiter.py#L30) |

## `core/services/communication_guard.py`
_Communication guard — scanner assistant-output for boundary violations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_hard` | `(trigger)` | Er denne trigger en HÅRD blok (afvis besked før send) eller blød | [src](../../../core/services/communication_guard.py#L143) |
| function | `_load` | `()` | — | [src](../../../core/services/communication_guard.py#L160) |
| function | `_save` | `(triggers)` | — | [src](../../../core/services/communication_guard.py#L172) |
| function | `add_trigger` | `(phrase, *, kind=…, reason=…, ttl_turns=…, ttl_hours=…)` | Tilfoj en triggerfrase til guarden. | [src](../../../core/services/communication_guard.py#L177) |
| function | `remove_trigger` | `(phrase)` | Fjern en triggerfrase. Returner True hvis den blev fjernet. | [src](../../../core/services/communication_guard.py#L224) |
| function | `scan` | `(text)` | Skan en tekst for triggerfraser. | [src](../../../core/services/communication_guard.py#L235) |
| function | `_trigger_active` | `(t, now)` | Er en trigger aktiv lige nu (permanent, eller TTL ikke udløbet)? | [src](../../../core/services/communication_guard.py#L282) |
| function | `enforce_outgoing` | `(text)` | Hård-gate for udga°ende assistant-tekst — kaldes FØR afsendelse. | [src](../../../core/services/communication_guard.py#L299) |
| function | `record_breach` | `(channel, removed, *, original=…)` | Log en boundary-breach (hård frase fanget ved kanal-dispatch). | [src](../../../core/services/communication_guard.py#L350) |
| function | `guard_channel_text` | `(text, channel)` | Convenience for kanal-dispatch: scrub hård afslutnings-fraser fra | [src](../../../core/services/communication_guard.py#L374) |
| function | `_active_hard_phrases` | `(now)` | — | [src](../../../core/services/communication_guard.py#L394) |
| function | `scrub_outgoing` | `(text)` | Kanal-backstop: fjern den SÆTNING/linje der indeholder en hård | [src](../../../core/services/communication_guard.py#L402) |
| function | `prompt_section` | `()` | Bygger en høj-salient påmindelse til system-prompten med de aktive | [src](../../../core/services/communication_guard.py#L433) |
| function | `consume_turn` | `()` | Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver | [src](../../../core/services/communication_guard.py#L467) |
| function | `cleanup_expired` | `()` | Rens udloebne TTL-triggers og triggers med ttl_turns <= 0. | [src](../../../core/services/communication_guard.py#L485) |
| function | `_safe_parse_iso` | `(s, now)` | — | [src](../../../core/services/communication_guard.py#L510) |
| function | `list_triggers` | `()` | Returner alle aktive triggers. | [src](../../../core/services/communication_guard.py#L519) |
| function | `active_count` | `()` | Antal aktive triggerfraser (permanente + ikke-udloebne TTL). | [src](../../../core/services/communication_guard.py#L524) |

## `core/services/communication_guard_daemon.py`
_Communication guard daemon — vedligeholder TTL-rydning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_communication_guard_daemon` | `()` | Daemon tick: cleanup expired TTL triggers + log active count. | [src](../../../core/services/communication_guard_daemon.py#L18) |

## `core/services/compass_engine.py`
_Compass Engine — weekly strategic bearing based on open loops and priorities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_update_compass` | `(*, open_loops=…, recent_decisions=…)` | Update compass if >3 days since last update. | [src](../../../core/services/compass_engine.py#L21) |
| function | `build_compass_surface` | `()` | — | [src](../../../core/services/compass_engine.py#L65) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/compass_engine.py#L74) |

## `core/services/completion_satisfaction.py`
_Completion Satisfaction — "det er nok, jeg er tilfreds."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_completion_satisfaction` | `(*, task_outcomes, repetition_on_same_topic=…, user_mood=…)` | — | [src](../../../core/services/completion_satisfaction.py#L8) |
| function | `build_completion_satisfaction_surface` | `()` | — | [src](../../../core/services/completion_satisfaction.py#L45) |
| function | `_publish_completion_satisfaction_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/completion_satisfaction.py#L48) |

## `core/services/composite_tools.py`
_Composite tools — safe self-extension through composition only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose` | `(*, name, description, input_schema, steps, created_by=…)` | Validate and store a proposal. Raises ValueError on invalid input. | [src](../../../core/services/composite_tools.py#L44) |
| function | `approve` | `(name, *, approved_by=…)` | — | [src](../../../core/services/composite_tools.py#L115) |
| function | `revoke` | `(name)` | — | [src](../../../core/services/composite_tools.py#L128) |
| function | `delete` | `(name)` | — | [src](../../../core/services/composite_tools.py#L138) |
| function | `get` | `(name)` | — | [src](../../../core/services/composite_tools.py#L148) |
| function | `list_available` | `(*, status=…)` | — | [src](../../../core/services/composite_tools.py#L152) |
| function | `invoke` | `(name, args)` | Execute an approved composite. Returns {status, steps, result}. | [src](../../../core/services/composite_tools.py#L156) |
| function | `get_stats` | `()` | — | [src](../../../core/services/composite_tools.py#L224) |
| function | `_substitute` | `(value, context)` | — | [src](../../../core/services/composite_tools.py#L237) |
| function | `_resolve_string` | `(s, context)` | Resolve {{...}} templates. | [src](../../../core/services/composite_tools.py#L247) |
| function | `_lookup` | `(path, context)` | — | [src](../../../core/services/composite_tools.py#L267) |

## `core/services/computer_use_policy.py`
_Computer-use-politik (§4.7) — per-bruger on/off for operator/computer-tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_computer_use_tool` | `(name)` | — | [src](../../../core/services/computer_use_policy.py#L25) |
| function | `_load` | `()` | — | [src](../../../core/services/computer_use_policy.py#L30) |
| function | `computer_use_enabled` | `(user_id)` | Default TIL — kun eksplicit fravalg slår fra. | [src](../../../core/services/computer_use_policy.py#L37) |
| function | `set_computer_use` | `(user_id, enabled)` | — | [src](../../../core/services/computer_use_policy.py#L42) |

## `core/services/concept_baseline_tracker.py`
_Concept baseline tracker — Layer 3 of emotion concepts integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cluster_for_concept` | `(concept)` | Look up cluster for a concept. Falls back to UNKNOWN. | [src](../../../core/services/concept_baseline_tracker.py#L19) |
| function | `_tracker_enabled` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L31) |
| function | `_now` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L39) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L43) |
| function | `record_concept_trigger` | `(*, concept, intensity, triggered_at, source)` | Real-time: update per-concept stats when a concept fires. | [src](../../../core/services/concept_baseline_tracker.py#L47) |
| function | `_aggregate_clusters` | `()` | Compute cluster-level share from total_triggers across all concepts. | [src](../../../core/services/concept_baseline_tracker.py#L87) |
| function | `_detect_drift` | `(cluster_stats, per_concept_stats)` | Detect drift signals from current stats. | [src](../../../core/services/concept_baseline_tracker.py#L129) |
| function | `_workspace_dir` | `()` | Return path to Jarvis' shared state directory. Indirected for tests. | [src](../../../core/services/concept_baseline_tracker.py#L156) |
| function | `_write_concept_baseline_md` | `(cluster_stats, per_concept_stats)` | Write auto-managed CONCEPT_BASELINE.md to workspace dir. | [src](../../../core/services/concept_baseline_tracker.py#L162) |
| function | `_propose_identity_update` | `(signal)` | Forward a drift signal to identity_drift_proposer. | [src](../../../core/services/concept_baseline_tracker.py#L210) |
| function | `evaluate_baseline_drift` | `()` | Daily: compute stats, write MD, propose drift updates if stable. | [src](../../../core/services/concept_baseline_tracker.py#L242) |
| function | `build_concept_baseline_surface` | `()` | Read-only: return current state for Mission Control consumption. | [src](../../../core/services/concept_baseline_tracker.py#L300) |

## `core/services/config_drift.py`
_Config-drift-nerve (§7) — fang når DEKLARERET config og RUNTIME-virkelighed er ude af sync._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_declared_port` | `()` | Læs den DEKLAREREDE port DIREKTE fra runtime.json på disk — IKKE in-memory settings. | [src](../../../core/services/config_drift.py#L19) |
| function | `_api_responds` | `(port)` | True hvis NOGET svarer HTTP på 127.0.0.1:port (selv 4xx/5xx = porten lytter). | [src](../../../core/services/config_drift.py#L42) |
| function | `check_port_drift` | `()` | Probe deklareret port + alternativer. drift=True hvis API'en svarer, men IKKE på den | [src](../../../core/services/config_drift.py#L55) |
| function | `observe_config_drift` | `()` | Kør drift-check → observe til Centralen + flag incident hvis drift. Kadence-kaldt. | [src](../../../core/services/config_drift.py#L73) |
| function | `build_config_drift_surface` | `()` | MC-surface — read-only config-drift-projektion. | [src](../../../core/services/config_drift.py#L119) |

## `core/services/conflict_daemon.py`
_Conflict daemon — detects when Jarvis' signals pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_conflict_daemon` | `(snapshot)` | Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode, | [src](../../../core/services/conflict_daemon.py#L18) |
| function | `_detect_conflict` | `(snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L40) |
| function | `_generate_conflict_phrase` | `(conflict_type, snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L66) |
| function | `_store_conflict` | `(phrase, conflict_type)` | — | [src](../../../core/services/conflict_daemon.py#L115) |
| function | `get_latest_conflict` | `()` | — | [src](../../../core/services/conflict_daemon.py#L146) |
| function | `build_conflict_surface` | `()` | — | [src](../../../core/services/conflict_daemon.py#L150) |

## `core/services/conflict_prompt_service.py`
_Conflict memory prompt service — surfaces recent conversation conflicts in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_conflict_memory_prompt_section` | `(limit=…)` | Return a prompt section with recent conflict lessons, or None if empty. | [src](../../../core/services/conflict_prompt_service.py#L11) |
| function | `build_conflict_memory_surface` | `(limit=…)` | — | [src](../../../core/services/conflict_prompt_service.py#L37) |

## `core/services/conflict_resolution.py`
_Bounded conflict resolution — deterministic arbitration between competing runtime pressures._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ConflictTrace` | `` | Observable trace of a conflict resolution decision. | [src](../../../core/services/conflict_resolution.py#L29) |
| method | `ConflictTrace.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L40) |
| class | `QuietInitiative` | `` | A quietly held user-facing initiative under maturation. | [src](../../../core/services/conflict_resolution.py#L61) |
| method | `QuietInitiative.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L73) |
| function | `get_quiet_initiative` | `()` | Return the current quiet initiative state for MC observability. | [src](../../../core/services/conflict_resolution.py#L92) |
| function | `_start_quiet_hold` | `(*, focus, reason_code, dominant_factor, decision_type)` | Start or refresh a quiet hold on a user-facing initiative. | [src](../../../core/services/conflict_resolution.py#L97) |
| function | `_expire_quiet_initiative` | `(reason=…)` | Mark the current quiet initiative as expired/released. | [src](../../../core/services/conflict_resolution.py#L126) |
| function | `_promote_quiet_initiative` | `()` | Mark the current quiet initiative as promoted to user-facing. | [src](../../../core/services/conflict_resolution.py#L135) |
| function | `resolve_heartbeat_initiative_conflict` | `(*, decision_type, liveness, question_gate, autonomy_pressure, open_loops, conductor_mode=…, cognitive_frame=…, policy_allow_propose=…, policy_allow_ping=…)` | Resolve competing pressures into a single bounded initiative outcome. | [src](../../../core/services/conflict_resolution.py#L148) |
| function | `apply_conflict_resolution` | `(*, decision, trace)` | Apply conflict resolution outcome to modify the heartbeat decision. | [src](../../../core/services/conflict_resolution.py#L508) |
| function | `get_last_conflict_trace` | `()` | Return the last conflict resolution trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L566) |
| function | `set_last_conflict_trace` | `(trace)` | Store the latest conflict trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L575) |
| function | `build_conflict_resolution_surface` | `()` | — | [src](../../../core/services/conflict_resolution.py#L580) |
| function | `_emit_resolved_event` | `(winning, losing)` | — | [src](../../../core/services/conflict_resolution.py#L589) |

## `core/services/connections.py`
_Connections-cluster — gør forbindelses-LIVSCYKLUSSEN synlig i Den Intelligente Central:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/connections.py#L18) |
| function | `note_presence` | `(user_id, device_key, platform=…, **meta)` | En device-presence-ping (jarvis-desk/mobile companion). Metadata-only. | [src](../../../core/services/connections.py#L26) |
| function | `note_ws` | `(event, client=…, **meta)` | MC-websocket-livscyklus: event ∈ {connected, disconnected, error}. client = host:port. | [src](../../../core/services/connections.py#L35) |
| function | `note_connection_error` | `(client, reason, **meta)` | Forbindelses-FEJL (WS-error, broken pipe, abort). → observe (synlig, ikke severe). | [src](../../../core/services/connections.py#L41) |
| function | `note_unauthorized` | `(user_id, session_id, resource, reason, *, role=…, run_id=…)` | UAUTORISERET adgang (tool-deny / identity-spoof / rate-limit) på en forbindelse → | [src](../../../core/services/connections.py#L46) |
| function | `session_activity` | `(session_id, *, limit=…)` | Forbindelses-debugging pr. session: hvilke tools blev brugt, hvilke FEJLEDE (+ årsag), | [src](../../../core/services/connections.py#L75) |
| function | `active_summary` | `(*, window=…)` | Read-only: hvem/hvad har været forbundet i den seneste trace (til MC/adaptiv-læring). | [src](../../../core/services/connections.py#L112) |

## `core/services/connectors.py`
_Connector-katalog + per-bruger status (v1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_enabled_store` | `()` | — | [src](../../../core/services/connectors.py#L143) |
| function | `is_enabled` | `(user_id, connector_id)` | Default ON; kun False hvis brugeren eksplicit har slået den fra. | [src](../../../core/services/connectors.py#L148) |
| function | `set_enabled` | `(user_id, connector_id, enabled)` | — | [src](../../../core/services/connectors.py#L157) |
| function | `_provider_of` | `(c)` | OAuth-provider for en connector. Google-pakken deler provider='google'. | [src](../../../core/services/connectors.py#L171) |
| function | `_connected` | `(user_id, c)` | — | [src](../../../core/services/connectors.py#L176) |
| function | `oauth_request_for` | `(connector_id)` | Map et connector-id → (oauth_provider, scopes) til /api/oauth/{id}/start. | [src](../../../core/services/connectors.py#L182) |
| function | `list_for_user` | `(user_id)` | Hele kataloget beriget med per-bruger `connected` + `enabled`. | [src](../../../core/services/connectors.py#L194) |
| function | `_audit` | `(event, user_id, connector_id)` | — | [src](../../../core/services/connectors.py#L213) |
| function | `delete_for_user` | `(user_id, connector_id)` | Afbryd & slet: revoke hos provider (best-effort) + lokal token-wipe + ryd flag. | [src](../../../core/services/connectors.py#L221) |

## `core/services/consent_registry.py`
_Consent Registry — user preferences and boundaries that persist across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_file` | `()` | — | [src](../../../core/services/consent_registry.py#L26) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/consent_registry.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/consent_registry.py#L44) |
| function | `_save` | `()` | — | [src](../../../core/services/consent_registry.py#L55) |
| function | `register_consent` | `(*, kind, statement, source_session_id=…, confidence=…)` | Register a user preference or boundary. | [src](../../../core/services/consent_registry.py#L67) |
| function | `revoke_consent` | `(consent_id)` | Mark a consent entry as inactive. | [src](../../../core/services/consent_registry.py#L101) |
| function | `get_active_consents` | `()` | — | [src](../../../core/services/consent_registry.py#L112) |
| function | `build_consent_prompt_section` | `()` | Return a prompt section with active consent entries, or None if empty. | [src](../../../core/services/consent_registry.py#L117) |
| function | `build_consent_registry_surface` | `()` | — | [src](../../../core/services/consent_registry.py#L143) |

## `core/services/consolidation_judge_daemon.py`
_Consolidation Judge Daemon — nightly reckoning, not observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_consolidation_judge_daemon` | `()` | Run the nightly consolidation judge if cadence allows. | [src](../../../core/services/consolidation_judge_daemon.py#L29) |
| function | `_gather_evidence` | `()` | Collect today's operational data for judgment. | [src](../../../core/services/consolidation_judge_daemon.py#L74) |
| function | `_build_stillingtagen` | `(evidence)` | Construct 3-5 concrete stillingtagen (items requiring judgment). | [src](../../../core/services/consolidation_judge_daemon.py#L126) |
| function | `_render_judgments` | `(items, evidence)` | Present each stillingtagen to the LLM and force a verdict. | [src](../../../core/services/consolidation_judge_daemon.py#L207) |
| function | `_parse_judgment` | `(raw, item)` | Parse the LLM's judgment response. | [src](../../../core/services/consolidation_judge_daemon.py#L248) |
| function | `_enforce_judgments` | `(judgments)` | Carry out the concrete actions from judgments. | [src](../../../core/services/consolidation_judge_daemon.py#L279) |
| function | `_enforce_reject` | `(j)` | Handle rejected items — typically revoke or pause. | [src](../../../core/services/consolidation_judge_daemon.py#L289) |
| function | `_enforce_accept` | `(j)` | Handle accepted items — typically recommit or flag. | [src](../../../core/services/consolidation_judge_daemon.py#L322) |
| function | `_record_judgment_session` | `(judgments, evidence)` | Write the full judgment session as a private brain record. | [src](../../../core/services/consolidation_judge_daemon.py#L342) |
| function | `build_consolidation_judge_surface` | `()` | Build surface data for prompt injection. | [src](../../../core/services/consolidation_judge_daemon.py#L377) |
| function | `now_date_str` | `()` | — | [src](../../../core/services/consolidation_judge_daemon.py#L385) |

## `core/services/consolidation_target_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_consolidation_target_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L28) |
| function | `refresh_runtime_consolidation_target_signal_statuses` | `()` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L51) |
| function | `build_runtime_consolidation_target_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L82) |
| function | `_extract_consolidation_target_candidates` | `(*, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L118) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, chronicle, chronicle_brief, meaning, temperament, self_narrative, relation_continuity)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L238) |
| function | `_persist_consolidation_target_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L361) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L430) |
| function | `_derive_consolidation_state` | `(*, witness_status, chronicle_status, brief_status, active_like_count, session_count)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L455) |
| function | `_derive_consolidation_focus` | `(*, domain_key, chronicle, chronicle_brief)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L470) |
| function | `_derive_consolidation_weight` | `(*, active_like_count, support_count, session_count, brief_status)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L488) |
| function | `_consolidation_summary` | `(*, focus, consolidation_state, consolidation_weight)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L505) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L525) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L532) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L544) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L556) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L567) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L581) |

## `core/services/context_window_manager.py`
_Context window manager — strategies for keeping prompts within budget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_estimate_session_tokens` | `()` | — | [src](../../../core/services/context_window_manager.py#L39) |
| function | `_list_session_messages` | `(session_id=…, limit=…)` | — | [src](../../../core/services/context_window_manager.py#L47) |
| function | `_is_anchor` | `(message)` | — | [src](../../../core/services/context_window_manager.py#L69) |
| function | `apply_sliding` | `(messages, *, keep_recent=…, preserve_anchors=…)` | Keep last N messages, drop middle. Optionally preserve anchor messages. | [src](../../../core/services/context_window_manager.py#L76) |
| function | `estimate_pressure` | `()` | Read current session size + classify pressure level. | [src](../../../core/services/context_window_manager.py#L101) |
| function | `degradation_signal` | `()` | Detect signs that long context is hurting performance. | [src](../../../core/services/context_window_manager.py#L121) |
| function | `adaptive_pick_strategy` | `()` | Pick the best strategy for current state. | [src](../../../core/services/context_window_manager.py#L186) |
| function | `context_window_section` | `()` | Awareness-section warning when degradation detected. | [src](../../../core/services/context_window_manager.py#L197) |
| function | `_exec_context_pressure` | `(args)` | — | [src](../../../core/services/context_window_manager.py#L213) |
| function | `_exec_manage_context_window` | `(args)` | Apply a chosen context-management strategy. | [src](../../../core/services/context_window_manager.py#L221) |

## `core/services/continuity.py`
_Continuity Kernel — state capsule + live update + graded wake-up._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/continuity.py#L87) |
| function | `_ensure_dir` | `()` | — | [src](../../../core/services/continuity.py#L91) |
| function | `_truncate_capsule` | `(data)` | Ensure capsule stays under _MAX_CAPSULE_SIZE_BYTES. | [src](../../../core/services/continuity.py#L95) |
| function | `capture_state` | `(*, mood=…, attention=…, relation=…, somatic=…, goals=…, recent_activity=…, workspace_id=…, session_id=…)` | Build a complete state capsule dict from partial inputs. | [src](../../../core/services/continuity.py#L129) |
| function | `write_capsule` | `(capsule)` | Write capsule to disk with rotation. | [src](../../../core/services/continuity.py#L210) |
| function | `sync_capsule_mood` | `()` | Sync capsule mood from mood_oscillator's live state. | [src](../../../core/services/continuity.py#L228) |
| function | `read_capsule` | `()` | Read the latest capsule from disk. | [src](../../../core/services/continuity.py#L278) |
| function | `get_wake_tier` | `(hours_since_last)` | Determine wake tier based on time since last session. | [src](../../../core/services/continuity.py#L296) |
| function | `build_conversation_continuity` | `(*, limit=…)` | Build a 'hvad talte vi om' block from recent session data. | [src](../../../core/services/continuity.py#L308) |
| function | `build_wake_up_block` | `(capsule=…)` | Build the wake-up block for prompt injection. | [src](../../../core/services/continuity.py#L402) |
| function | `live_update_after_turn` | `(*, mood=…, attention=…, relation=…, somatic=…, goals=…, recent_activity=…, session_id=…)` | Call this after every visible turn to persist the state capsule. | [src](../../../core/services/continuity.py#L519) |

## `core/services/continuity_kernel.py`
_Bounded Continuity Kernel — existence feel between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/continuity_kernel.py#L27) |
| function | `record_tick_elapsed` | `(seconds)` | Record elapsed time since last tick and update existence feel. | [src](../../../core/services/continuity_kernel.py#L31) |
| function | `_compute_existence_feeling` | `(gap_seconds)` | Compute existence feeling based on gap duration. | [src](../../../core/services/continuity_kernel.py#L57) |
| function | `_compute_narrative` | `(gap_seconds)` | Compute a narrative description of the gap. | [src](../../../core/services/continuity_kernel.py#L73) |
| function | `get_existence_narrative` | `()` | Get the current existence narrative. | [src](../../../core/services/continuity_kernel.py#L92) |
| function | `get_existence_feeling` | `()` | Get the current existence feeling (0-1). | [src](../../../core/services/continuity_kernel.py#L97) |
| function | `should_express_continuity` | `()` | Determine if continuity should be expressed in visible prompt. | [src](../../../core/services/continuity_kernel.py#L102) |
| function | `get_continuity_state` | `()` | Get full continuity state for debugging/MC. | [src](../../../core/services/continuity_kernel.py#L108) |
| function | `reset_continuity_state` | `()` | Reset continuity state (for testing). | [src](../../../core/services/continuity_kernel.py#L113) |
| function | `format_continuity_for_prompt` | `()` | Format continuity info for heartbeat prompt injection. | [src](../../../core/services/continuity_kernel.py#L127) |
| function | `build_continuity_kernel_surface` | `()` | Build MC surface for continuity kernel. | [src](../../../core/services/continuity_kernel.py#L136) |

## `core/services/contract_evolution.py`
_Contract Evolution — Jarvis proposes changes to his own identity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose_identity_change` | `(*, target_file, proposed_addition, rationale, confidence=…, evidence_count=…)` | Propose a change to SOUL.md, IDENTITY.md, or USER.md. | [src](../../../core/services/contract_evolution.py#L22) |
| function | `approve_proposal` | `(proposal_id)` | Mark a proposal as approved (MC action). | [src](../../../core/services/contract_evolution.py#L57) |
| function | `reject_proposal` | `(proposal_id)` | Mark a proposal as rejected (MC action). | [src](../../../core/services/contract_evolution.py#L70) |
| function | `maybe_propose_identity_evolution` | `()` | Analyze personality vector trends and propose IDENTITY.md changes. | [src](../../../core/services/contract_evolution.py#L83) |
| function | `build_contract_evolution_surface` | `()` | — | [src](../../../core/services/contract_evolution.py#L148) |

## `core/services/contradiction_engine.py`
_Contradiction engine — detect semantic conflicts between commitments and reviews._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/contradiction_engine.py#L44) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/contradiction_engine.py#L48) |
| function | `_has_negation` | `(text)` | — | [src](../../../core/services/contradiction_engine.py#L52) |
| function | `_fetch_active_decisions` | `(*, limit=…)` | Return active behavioral_decisions with their directive text. | [src](../../../core/services/contradiction_engine.py#L56) |
| function | `_fetch_recent_self_reviews` | `(*, hours=…, limit=…)` | Return cognitive_self_reviews from the last `hours` hours. | [src](../../../core/services/contradiction_engine.py#L76) |
| function | `_timedelta` | `(*, hours)` | — | [src](../../../core/services/contradiction_engine.py#L97) |
| function | `_critique_texts_from_review` | `(review)` | Extract per-lesson + next_focus strings as candidate critique texts. | [src](../../../core/services/contradiction_engine.py#L102) |
| function | `detect_contradictions` | `(*, max_findings=…)` | Find semantic contradictions between active decisions and recent reviews. | [src](../../../core/services/contradiction_engine.py#L121) |
| function | `run_contradiction_tick` | `()` | One detection cycle. Publishes contradiction.detected events. | [src](../../../core/services/contradiction_engine.py#L178) |
| function | `build_contradiction_engine_surface` | `(*, limit=…)` | Mission-control/read-surface for semantic contradiction detection. | [src](../../../core/services/contradiction_engine.py#L212) |

