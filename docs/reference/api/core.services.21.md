# `core.services.21` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/tiktok_research_daemon.py`
_TikTok research daemon — daily content concept pool generator._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_tiktok_research_daemon` | `()` | Daily tick — generate content concepts and write to pool file. | [src](../../../core/services/tiktok_research_daemon.py#L75) |
| function | `_load_pool` | `()` | Load the pool JSON from disk. Returns empty dict if missing or corrupt. | [src](../../../core/services/tiktok_research_daemon.py#L155) |
| function | `_generate_concepts_for_type` | `(slot_type)` | Call LLM to generate 3 concepts for the given slot type. | [src](../../../core/services/tiktok_research_daemon.py#L165) |
| function | `_parse_json_array` | `(text)` | Try to parse a JSON array from LLM output. Returns None on failure. | [src](../../../core/services/tiktok_research_daemon.py#L198) |

## `core/services/tiny_webchat_execution_pilot.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_run_tiny_webchat_execution_pilot` | `(*, policy, heartbeat_tick_id, decision_summary, ping_text)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L30) |
| function | `build_runtime_webchat_execution_pilot_surface` | `(*, limit=…)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L150) |
| function | `_build_execution_candidate` | `(*, heartbeat_tick_id, decision_summary, ping_text)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L191) |
| function | `_execution_focus` | `(*, question_gate, question_loop, question_pressure)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L325) |
| function | `_normalize_focus_candidate` | `(value)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L343) |
| function | `_message_text` | `(*, focus, ping_text)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L366) |
| function | `_resolve_target_session_id` | `()` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L376) |
| function | `_cooldown_state` | `(canonical_key)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L386) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L404) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L431) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L442) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L451) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L460) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/tiny_webchat_execution_pilot.py#L467) |

## `core/services/tool_catalog.py`
_Compact tool catalog for system prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_short_desc` | `(tool_def)` | — | [src](../../../core/services/tool_catalog.py#L62) |
| function | `_registry_hash` | `()` | — | [src](../../../core/services/tool_catalog.py#L76) |
| function | `build_catalog_text` | `()` | Return cached catalog text; rebuild only if tool registry changed. | [src](../../../core/services/tool_catalog.py#L91) |
| function | `catalog_token_estimate` | `()` | Rough char/4 token estimate of the current catalog. | [src](../../../core/services/tool_catalog.py#L127) |
| function | `invalidate_cache` | `()` | Force next call to rebuild. Useful in tests. | [src](../../../core/services/tool_catalog.py#L132) |

## `core/services/tool_chip_payload.py`
_Bygger data-payloaden for et tool-kald til jarvis-desk-chip'en (spec 2026-06-15)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_tool_capability_payload` | `(*, tool, status, arguments=…, result_text=…, arg_value_cap=…, result_cap=…)` | — | [src](../../../core/services/tool_chip_payload.py#L14) |

## `core/services/tool_concurrency.py`
_Tool-concurrency policy (harness Part C)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `concurrency_mode` | `()` | Current mode: 'off' | 'on'. Default 'off'. Env wins over config. Self-safe. | [src](../../../core/services/tool_concurrency.py#L42) |
| function | `_call_name` | `(tc)` | — | [src](../../../core/services/tool_concurrency.py#L57) |
| function | `is_parallelizable` | `(tool_calls, *, mode)` | True iff mode=='on' AND >=2 calls AND every call name is in the allowlist. | [src](../../../core/services/tool_concurrency.py#L62) |

## `core/services/tool_embeddings.py`
_Tool description embedding cache._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../core/services/tool_embeddings.py#L28) |
| function | `_pack` | `(vec)` | — | [src](../../../core/services/tool_embeddings.py#L42) |
| function | `_unpack` | `(blob)` | — | [src](../../../core/services/tool_embeddings.py#L46) |
| function | `_hash_desc` | `(desc)` | — | [src](../../../core/services/tool_embeddings.py#L51) |
| function | `_compute_embedding` | `(text)` | Call Ollama embedding endpoint. Override in tests. | [src](../../../core/services/tool_embeddings.py#L55) |
| function | `get_embedding` | `(name, description)` | — | [src](../../../core/services/tool_embeddings.py#L71) |
| function | `invalidate` | `(name)` | — | [src](../../../core/services/tool_embeddings.py#L91) |
| function | `_cosine` | `(a, b)` | — | [src](../../../core/services/tool_embeddings.py#L97) |
| function | `top_k_similar` | `(query, k=…)` | Return (tool_name, similarity) sorted desc by cosine similarity. | [src](../../../core/services/tool_embeddings.py#L108) |
| function | `warmup_all` | `()` | Compute embeddings for every registered tool. Returns count computed. | [src](../../../core/services/tool_embeddings.py#L121) |

## `core/services/tool_intent_approval_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_tool_intent_approval_surface` | `(intent_surface, *, requested_at)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L50) |
| function | `build_sudo_approval_window_surface` | `(intent_surface, *, now=…)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L177) |
| function | `sudo_approval_window_scope_from_request` | `(request)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L224) |
| function | `sudo_approval_window_scope_from_intent` | `(intent_surface)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L232) |
| function | `sudo_approval_window_allows_request` | `(request, *, now=…)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L240) |
| function | `resolve_tool_intent_approval` | `(intent_surface, *, approval_state, approval_source, resolution_reason, resolution_message=…, session_id=…, resolved_at=…)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L300) |
| function | `build_approval_feedback_surface` | `()` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L364) |
| function | `tool_intent_approval_key` | `(intent_surface)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L373) |
| function | `_approval_reason` | `(intent_surface)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L385) |
| function | `_intent_tool_name` | `(intent_surface)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L479) |
| function | `_emit_approval_resolved_event` | `(*, intent_key, approval_state, approval_source, resolved_at, resolution_reason, resolution_message, session_id, tool_name)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L489) |
| function | `_find_verbal_resolution` | `(intent_surface, request)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L518) |
| function | `_decision_from_text` | `(content)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L555) |
| function | `_matches_intent_context` | `(content, intent_surface)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L566) |
| function | `_sudo_approval_window_scope` | `(*, capability_id, command_text, proposal_scope)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L579) |
| function | `_now` | `()` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L607) |
| function | `_normalize` | `(value)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L611) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/tool_intent_approval_runtime.py#L623) |

## `core/services/tool_intent_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_tool_intent_runtime_surface` | `()` | — | [src](../../../core/services/tool_intent_runtime.py#L27) |
| function | `_build_tool_intent_runtime_surface` | `()` | — | [src](../../../core/services/tool_intent_runtime.py#L43) |
| function | `_build_mutating_exec_proposal_surface` | `()` | — | [src](../../../core/services/tool_intent_runtime.py#L486) |
| function | `_build_sudo_exec_proposal_surface` | `(mutating_exec_surface)` | — | [src](../../../core/services/tool_intent_runtime.py#L669) |
| function | `_derive_intent_from_awareness` | `(*, awareness, repo_observation)` | — | [src](../../../core/services/tool_intent_runtime.py#L725) |
| function | `_emit_tool_intent_runtime_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/tool_intent_runtime.py#L836) |

## `core/services/tool_observer.py`
_Tools-cluster query-helpers (Phase 1) oven på tool_call-observe i execute_tool._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `recent_tool_calls` | `(*, session_id=…, kind=…, status=…, limit=…)` | Læs tool_call-observe-records fra central_trace, filtreret. Nyeste først. | [src](../../../core/services/tool_observer.py#L14) |
| function | `recent_tool_failures` | `(*, session_id=…, kind=…, limit=…)` | Kun FEJLEDE tool-kald — debugging-indgang når en bruger melder en fejl ude af huset. | [src](../../../core/services/tool_observer.py#L44) |
| function | `tool_call_summary` | `()` | Aggregeret overblik (MC/debug): antal kald pr. kind + fejlrate. Self-safe. | [src](../../../core/services/tool_observer.py#L57) |

## `core/services/tool_outcome_memory.py`
_Bridge tool execution outcomes into durable runtime action evidence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_tool_outcome_memory` | `(*, tool_name, arguments, result, mode=…)` | Persist a tool outcome as runtime action evidence. | [src](../../../core/services/tool_outcome_memory.py#L7) |
| function | `_summary_for_result` | `(tool_name, result)` | — | [src](../../../core/services/tool_outcome_memory.py#L51) |
| function | `classify_tool_family` | `(tool_name)` | — | [src](../../../core/services/tool_outcome_memory.py#L59) |
| function | `_score_for_outcome` | `(*, status, family, result)` | — | [src](../../../core/services/tool_outcome_memory.py#L74) |
| function | `_preview_arguments` | `(arguments)` | — | [src](../../../core/services/tool_outcome_memory.py#L98) |

## `core/services/tool_pattern_miner.py`
_Tool pattern miner — discover repeating tool sequences as composite candidates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_tool_invocations` | `(*, hours=…, limit=…)` | — | [src](../../../core/services/tool_pattern_miner.py#L30) |
| function | `_extract_sequences` | `(invocations, *, min_len, max_len)` | Slide window over tool calls, count N-gram occurrences. | [src](../../../core/services/tool_pattern_miner.py#L57) |
| function | `find_candidate_composites` | `(*, hours=…, min_repeat=…, max_results=…)` | Mine tool history for repeating sequences worth composing. | [src](../../../core/services/tool_pattern_miner.py#L82) |
| function | `composite_candidates_section` | `()` | Awareness section listing top 3 candidate composites. | [src](../../../core/services/tool_pattern_miner.py#L124) |
| function | `_exec_mine_tool_patterns` | `(args)` | — | [src](../../../core/services/tool_pattern_miner.py#L137) |

## `core/services/tool_result_aging.py`
_Provider-agnostic tool-result aging for the visible agentic loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `aging_trigger_tokens` | `()` | Configured full-content token trigger for aging. Default 120k. Self-safe. | [src](../../../core/services/tool_result_aging.py#L38) |
| function | `tool_result_aging_mode` | `()` | Current aging mode: 'off' | 'shadow' | 'active'. Default 'shadow'. | [src](../../../core/services/tool_result_aging.py#L49) |
| function | `_clear_placeholder` | `(n)` | — | [src](../../../core/services/tool_result_aging.py#L66) |
| function | `_is_already_aged` | `(content)` | — | [src](../../../core/services/tool_result_aging.py#L70) |
| function | `age_tool_results` | `(exchanges, *, keep_full=…, mode, strength, round_index, compress_fn=…, trigger_tokens=…)` | Age tool-result content on exchanges older than the ``keep_full`` most recent. | [src](../../../core/services/tool_result_aging.py#L74) |

## `core/services/tool_result_store.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `summarize_result` | `(content, max_length=…)` | — | [src](../../../core/services/tool_result_store.py#L15) |
| function | `save_tool_result` | `(tool_name, arguments, result_content, *, created_at=…)` | — | [src](../../../core/services/tool_result_store.py#L22) |
| function | `get_tool_result` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L47) |
| function | `cleanup_old_results` | `(max_age_days=…)` | — | [src](../../../core/services/tool_result_store.py#L63) |
| function | `build_tool_result_reference` | `(result_id, *, tool_name, summary)` | — | [src](../../../core/services/tool_result_store.py#L80) |
| function | `parse_tool_result_reference` | `(content)` | — | [src](../../../core/services/tool_result_store.py#L92) |
| function | `render_tool_result_for_prompt` | `(content, *, expand, max_chars=…, stub=…)` | — | [src](../../../core/services/tool_result_store.py#L113) |
| function | `_result_path` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L163) |
| function | `_prefixed_tool_text` | `(tool_name, text)` | — | [src](../../../core/services/tool_result_store.py#L167) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/tool_result_store.py#L175) |

## `core/services/tool_router.py`
_Per-turn tool selection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolSelection` | `` | — | [src](../../../core/services/tool_router.py#L43) |
| function | `_clarity_signal` | `(msg)` | — | [src](../../../core/services/tool_router.py#L55) |
| function | `_score` | `(user_message, *, top_sim, load_more_rate_7d)` | — | [src](../../../core/services/tool_router.py#L71) |
| function | `_all_tool_names` | `()` | — | [src](../../../core/services/tool_router.py#L78) |
| function | `_always_core_set` | `(limit)` | Top-N tools by 7-day call count ∪ pinned set, with fallback. | [src](../../../core/services/tool_router.py#L86) |
| function | `_load_more_rate_7d` | `()` | — | [src](../../../core/services/tool_router.py#L117) |
| function | `_confidence_buckets` | `(values, n_buckets=…)` | — | [src](../../../core/services/tool_router.py#L135) |
| function | `_count_missed_tools` | `(rows)` | — | [src](../../../core/services/tool_router.py#L143) |
| function | `build_tool_router_surface` | `()` | Mission Control surface for tool router state. | [src](../../../core/services/tool_router.py#L159) |
| function | `select_tools` | `(*, user_message, session_id, lane, run_id=…)` | Select a subset of tools for this turn. Always returns a ToolSelection. | [src](../../../core/services/tool_router.py#L263) |
| function | `_select_inner` | `(*, user_message, session_id, lane, run_id, settings, started_at)` | — | [src](../../../core/services/tool_router.py#L303) |
| function | `_persist` | `(sel, user_message, session_id, lane, run_id)` | — | [src](../../../core/services/tool_router.py#L363) |

## `core/services/tool_router_runtime.py`
_Nightly daemon: refresh always-core ranking, recompute embeddings,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_adjust_threshold` | `(*, current, load_more_rate_7d)` | — | [src](../../../core/services/tool_router_runtime.py#L19) |
| function | `_read_load_more_rate` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L29) |
| function | `run_once` | `()` | Single daemon iteration. Safe to call manually for testing. | [src](../../../core/services/tool_router_runtime.py#L34) |
| function | `_loop` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L64) |
| function | `start_tool_router_runtime` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L73) |
| function | `stop_tool_router_runtime` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L85) |

## `core/services/tool_tagger.py`
_Tool tag taxonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_json` | `(p)` | — | [src](../../../core/services/tool_tagger.py#L39) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/tool_tagger.py#L49) |
| function | `get_tags` | `(tool_name)` | Return tags for `tool_name`. Overrides win over auto. Empty if unknown. | [src](../../../core/services/tool_tagger.py#L65) |
| function | `get_pinned_set` | `()` | — | [src](../../../core/services/tool_tagger.py#L75) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/tool_tagger.py#L80) |
| function | `bootstrap_tags` | `(*, dry_run=…)` | Use cheap-lane LLM to generate domain tags for every registered tool. | [src](../../../core/services/tool_tagger.py#L85) |

## `core/services/tool_usage_store.py`
_Tools-cluster Phase 2 — persistent forbrugs-statistik (DB-backed, cross-proces)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/tool_usage_store.py#L29) |
| function | `record_use` | `(tool, *, kind=…, ok=…)` | UPSERT-increment forbrugs-tæller for ét tool-kald. Best-effort, hot-path-sikker. | [src](../../../core/services/tool_usage_store.py#L41) |
| function | `usage_stats` | `()` | {tool: {count, errors, kind, last_used}} for alle tools der ER blevet kaldt. | [src](../../../core/services/tool_usage_store.py#L67) |
| function | `_bucket_for` | `(count)` | — | [src](../../../core/services/tool_usage_store.py#L85) |
| function | `usage_buckets` | `(registered=…)` | Klassificér tools i most/often/sometimes/rare/never. Hvis `registered` gives, indgår | [src](../../../core/services/tool_usage_store.py#L92) |
| function | `tool_order` | `(registered)` | Ordn registrerede tools efter forbrug: mest-brugte FØRST, aldrig-brugte SIDST. | [src](../../../core/services/tool_usage_store.py#L106) |
| function | `dead_tools` | `(registered)` | Registrerede tools der ALDRIG er kaldt (count 0). Vises sidst / kandidater til at | [src](../../../core/services/tool_usage_store.py#L116) |
| function | `observe_stats` | `(registered=…)` | Periodisk (cadence): central.observe forbrugs-summary + flag antal døde tools. | [src](../../../core/services/tool_usage_store.py#L123) |

## `core/services/totp_verifier.py`
_TOTP-verifikation (RFC 6238) til owner-override — ren stdlib, ingen dependency._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_b32_decode` | `(seed)` | Dekodér base32-seed; tilføj padding + uppercase. Tom/ugyldig → b''. | [src](../../../core/services/totp_verifier.py#L31) |
| function | `_hotp` | `(key, counter)` | RFC 4226 HOTP — HMAC-SHA1 + dynamic truncation → _DIGITS cifre. | [src](../../../core/services/totp_verifier.py#L43) |
| function | `generate_code` | `(seed, *, timestamp=…)` | 6-cifret TOTP for `seed` på `timestamp` (default: nu). | [src](../../../core/services/totp_verifier.py#L52) |
| function | `verify` | `(code, *, seed, now=…, valid_window=…)` | True hvis `code` matcher TOTP for `seed` inden for ±valid_window vinduer. | [src](../../../core/services/totp_verifier.py#L62) |
| function | `generate_seed` | `()` | Ny tilfældig 16-byte base32-nøgle (uden padding) til QR-setup. | [src](../../../core/services/totp_verifier.py#L88) |
| function | `provisioning_uri` | `(seed, *, account, issuer=…)` | Byg en otpauth://-URI som authenticator-apps (Google Authenticator, Authy, | [src](../../../core/services/totp_verifier.py#L94) |
| function | `revoke` | `(_old_seed=…)` | Returnér en ny seed. Caller (owner-session) persisterer den + smider den gamle. | [src](../../../core/services/totp_verifier.py#L106) |
| function | `record_attempt` | `(session_id, *, now=…)` | Registrér et override-forsøg. True hvis tilladt, False hvis rate-limited. | [src](../../../core/services/totp_verifier.py#L120) |

## `core/services/truth_gate_v2.py`
_Evidens-baseret TruthGate v2 (Fase 2). Detekterer handlings-påstande og verificerer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActionClaim` | `` | — | [src](../../../core/services/truth_gate_v2.py#L35) |
| function | `detect_action_claims` | `(text)` | Deterministisk: find handlings-påstande. commit_hash tæller kun i commit/git/log- | [src](../../../core/services/truth_gate_v2.py#L45) |
| function | `_run_result_text` | `(followup_exchanges)` | — | [src](../../../core/services/truth_gate_v2.py#L101) |
| function | `verify_claim` | `(claim, executed_tool_names, followup_exchanges)` | In-run evidens: kørte et tool i kategorien? + (for citeret output/hash) matcher | [src](../../../core/services/truth_gate_v2.py#L109) |
| function | `classify_severity` | `(claims)` | — | [src](../../../core/services/truth_gate_v2.py#L154) |
| function | `_footnote_for` | `(claim)` | Byg én fodnote-linje for et uverificeret claim i den konsistente stil. | [src](../../../core/services/truth_gate_v2.py#L158) |
| function | `_annotate` | `(text, claims)` | Bevar teksten + append fodnote(r) i bunden (én pr. claim, adskilt fra | [src](../../../core/services/truth_gate_v2.py#L168) |
| function | `_annotate_soft` | `(text, claims=…)` | Bagudkompatibel: bløde påstande → fodnote. (claims valgfri; uden dem | [src](../../../core/services/truth_gate_v2.py#L177) |
| function | `_llm_judge` | `(text)` | Spørg billig lane om teksten påstår en handling der kræver tool-evidens. | [src](../../../core/services/truth_gate_v2.py#L192) |
| function | `_maybe_llm_claim` | `(text)` | LLM-dommer KUN hvis teksten har et handlings-hint men intet deterministisk match. | [src](../../../core/services/truth_gate_v2.py#L207) |
| function | `truth_gate_v2` | `(ctx)` | ctx: {text, executed_tool_names, followup_exchanges, run_id, session_id}. | [src](../../../core/services/truth_gate_v2.py#L221) |

## `core/services/turn_changelog.py`
_End-of-turn changelog — auto-summarize what this turn changed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_calls_during` | `(run_id, started_at)` | — | [src](../../../core/services/turn_changelog.py#L27) |
| function | `_git_changed_files` | `(repo)` | — | [src](../../../core/services/turn_changelog.py#L50) |
| function | `build_turn_changelog` | `(*, run_id=…, started_at=…, repo_root=…)` | — | [src](../../../core/services/turn_changelog.py#L67) |
| function | `previous_turn_changelog_section` | `(session_id)` | Look at the most recent visible run for this session and surface the | [src](../../../core/services/turn_changelog.py#L80) |
| function | `format_changelog` | `(changelog)` | Render a compact human-readable summary, or None if empty. | [src](../../../core/services/turn_changelog.py#L129) |

## `core/services/turn_trace.py`
_core/services/turn_trace.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sentinel` | `()` | — | [src](../../../core/services/turn_trace.py#L29) |
| function | `active` | `()` | — | [src](../../../core/services/turn_trace.py#L36) |
| function | `start` | `(label=…)` | Nulstil tidslinjen ved request-in. No-op uden sentinel. | [src](../../../core/services/turn_trace.py#L40) |
| function | `mark` | `(kind, label=…, dur_ms=…)` | Tilføj ét event + print en LIVE-linje til stderr (så ruten kan følges i | [src](../../../core/services/turn_trace.py#L58) |
| function | `dump` | `(reason=…)` | Skriv hele tidslinjen til latest.json + kompakt stderr-resumé, og sluk. | [src](../../../core/services/turn_trace.py#L79) |

## `core/services/ui_panel_store.py`
_Pending UI-panel-kald (spec §8.2, Fase 6 #3, opdateret 2026-06-16 med scope)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `request_panel` | `(panel, *, detail=…, scope=…, session_id=…)` | Tilføj en pending panel-forespørgsel. | [src](../../../core/services/ui_panel_store.py#L25) |
| function | `list_pending` | `(*, session_id=…)` | Returnér alle pending requests (status='pending'), valgfrit filtreret på session. | [src](../../../core/services/ui_panel_store.py#L61) |
| function | `ack_panel` | `(request_id)` | Markér en request som 'opened' (desk-appen har åbnet panelet). | [src](../../../core/services/ui_panel_store.py#L71) |
| function | `get_request_status` | `(request_id)` | Nuværende status ('pending'/'opened') for en request, eller None hvis ukendt. | [src](../../../core/services/ui_panel_store.py#L82) |
| function | `_load` | `()` | — | [src](../../../core/services/ui_panel_store.py#L91) |
| function | `_save` | `(state)` | — | [src](../../../core/services/ui_panel_store.py#L102) |

## `core/services/unconscious_modulation.py`
_Unconscious modulation — sub-symbolic sampling-parameter shift._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_modulation_enabled` | `()` | Kill-switch check. True = modulate; False = pass base through. | [src](../../../core/services/unconscious_modulation.py#L32) |
| function | `compute_unconscious_modulation` | `(*, base_temperature, base_top_p, workspace_id=…)` | Return (modulated_temperature, modulated_top_p). | [src](../../../core/services/unconscious_modulation.py#L40) |

## `core/services/unconscious_temperature_field.py`
_Unconscious temperature field — backwards-compat wrapper for Lag 10._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_unconscious_temperature_hint` | `()` | Backwards-compat: returns heartbeat-formatted hint string or None. | [src](../../../core/services/unconscious_temperature_field.py#L13) |
| function | `build_unconscious_temperature_field_surface` | `(*, force_refresh=…)` | Backwards-compat: surface dict for Mission Control consumers. | [src](../../../core/services/unconscious_temperature_field.py#L28) |

## `core/services/unfinished_intent.py`
_Unfinished-intent detector for visible-run output._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnfinishedIntent` | `` | Resultat af detector: hvilken pattern matched. | [src](../../../core/services/unfinished_intent.py#L30) |
| function | `_tail` | `(text, n=…)` | Returner sidste ~n tegn af teksten. | [src](../../../core/services/unfinished_intent.py#L110) |
| function | `detect_unfinished_intent` | `(text)` | Returner UnfinishedIntent hvis teksten antyder Jarvis stoppede midt | [src](../../../core/services/unfinished_intent.py#L117) |
| function | `is_in_cooldown` | `(session_id)` | True hvis session_id har triggered en continuation indenfor cooldown-vinduet. | [src](../../../core/services/unfinished_intent.py#L215) |
| function | `mark_triggered` | `(session_id)` | Marker at en continuation netop er triggered for session_id. | [src](../../../core/services/unfinished_intent.py#L224) |
| function | `reset_cooldown_for_tests` | `()` | Test-helper: tøm cooldown-state mellem test cases. | [src](../../../core/services/unfinished_intent.py#L232) |

## `core/services/unified_recall.py`
_Unified recall — krydsreference mellem hukommelsessystemer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `unified_recall` | `(query, *, limit=…)` | Søg på tværs af alle 3 hukommelsessystemer. | [src](../../../core/services/unified_recall.py#L29) |
| function | `get_unified_recall_hints` | `(query=…, *, limit=…)` | Korte hints til prompt-kontekst. | [src](../../../core/services/unified_recall.py#L78) |
| function | `_empty_entry` | `()` | — | [src](../../../core/services/unified_recall.py#L129) |
| function | `_extract_topic` | `(hit)` | Extract a short topic key from a search hit. | [src](../../../core/services/unified_recall.py#L138) |
| function | `_latest_timestamp` | `(current, hit)` | Return the most recent ISO timestamp between current and hit. | [src](../../../core/services/unified_recall.py#L158) |
| function | `_safe_search_memory` | `(query, limit)` | Search MEMORY.md / USER.md / SOUL.md. Returns empty list on failure. | [src](../../../core/services/unified_recall.py#L174) |
| function | `_safe_search_brain` | `(query, limit)` | Search private brain. Returns empty list on failure. | [src](../../../core/services/unified_recall.py#L187) |
| function | `_safe_recall_memories` | `(query, limit)` | Search Sansernes Arkiv. Returns empty list on failure. | [src](../../../core/services/unified_recall.py#L200) |

## `core/services/user_activity.py`
_Bruger-aktivitets-nerve — ét sted der svarer "hvornår var X sidst aktiv, og hvordan"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_q1` | `(conn, sql, params)` | — | [src](../../../core/services/user_activity.py#L17) |
| function | `build_user_activity_surface` | `(*, active_within_s=…)` | Pr. registreret bruger: sidst aktiv (flettet fra alle kilder), via hvad, aktiv nu, | [src](../../../core/services/user_activity.py#L25) |

## `core/services/user_contradiction_tracker.py`
_User Contradiction Tracker — detects when the user contradicts themselves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(text)` | — | [src](../../../core/services/user_contradiction_tracker.py#L46) |
| function | `_has_negation` | `(text)` | — | [src](../../../core/services/user_contradiction_tracker.py#L50) |
| function | `_fetch_recent_user_messages` | `(*, hours=…, limit=…)` | Fetch recent user (role='user') chat messages. | [src](../../../core/services/user_contradiction_tracker.py#L54) |
| function | `_fetch_existing_statements` | `(*, limit=…)` | Fetch stored user statements for comparison. | [src](../../../core/services/user_contradiction_tracker.py#L76) |
| function | `_ensure_user_contradiction_tables` | `(conn)` | Idempotent table creation — delegates to db_user_contradiction's helper. | [src](../../../core/services/user_contradiction_tracker.py#L95) |
| function | `extract_statements` | `(text)` | Split a message into individual claim-like sentences. | [src](../../../core/services/user_contradiction_tracker.py#L105) |
| function | `_classify_topic` | `(text)` | Simple keyword-based topic classification. | [src](../../../core/services/user_contradiction_tracker.py#L138) |
| function | `_detect_contradictions_between` | `(new_statement, new_topic, existing, *, max_findings=…)` | Compare a new statement against existing stored statements. | [src](../../../core/services/user_contradiction_tracker.py#L170) |
| function | `scan_for_contradictions` | `(*, hours=…)` | Main entry point — scan recent user messages for contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L231) |
| function | `build_user_contradiction_surface` | `(*, limit=…)` | Build signal surface for user contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L352) |
| function | `record_user_statement` | `(text, topic=…, session_id=…, source=…, user_id=…)` | Record a user statement. Thin wrapper around DB upsert. | [src](../../../core/services/user_contradiction_tracker.py#L427) |
| function | `check_contradiction` | `(text, topic=…, user_id=…)` | Check a statement against existing stored statements for contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L464) |
| function | `detect_and_store_contradiction` | `(text, topic=…, session_id=…, source=…, user_id=…)` | Record a statement AND detect/store contradictions in one call. | [src](../../../core/services/user_contradiction_tracker.py#L486) |
| function | `get_user_contradictions` | `(*, limit=…, status=…, user_id=…)` | Get stored contradictions. Thin wrapper around DB query. | [src](../../../core/services/user_contradiction_tracker.py#L573) |

## `core/services/user_emotional_resonance.py`
_User Emotional Resonance — detect and respond to the user's mood._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_user_mood` | `(*, user_message, run_id=…)` | Detect user mood from message and persist. | [src](../../../core/services/user_emotional_resonance.py#L73) |
| function | `get_current_user_mood` | `()` | Get the latest detected user mood. | [src](../../../core/services/user_emotional_resonance.py#L139) |
| function | `build_user_emotional_resonance_surface` | `()` | MC surface for user emotional resonance. | [src](../../../core/services/user_emotional_resonance.py#L147) |

## `core/services/user_md_update_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L20) |
| function | `refresh_runtime_user_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L42) |
| function | `build_runtime_user_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L73) |
| function | `_extract_user_md_update_proposals` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L101) |
| function | `_persist_user_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L159) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L232) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L242) |
| function | `_build_proposal_type` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L252) |
| function | `_build_user_dimension` | `(*, item, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L265) |
| function | `_build_proposed_update` | `(*, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L278) |
| function | `_build_proposal_reason` | `(*, proposal_type, proposal_confidence, signal_summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L288) |
| function | `_build_proposal_confidence` | `(*, signal_confidence, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L300) |
| function | `_build_source_anchor` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L308) |
| function | `_build_status_reason` | `(*, proposal_type, signal_status)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L318) |
| function | `_title_suffix` | `(user_dimension)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L329) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L334) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L339) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L344) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L353) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L363) |

## `core/services/user_model_daemon.py`
_User model daemon — Theory of Mind: a living model of the user's state and patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_user_model` | `()` | — | [src](../../../core/services/user_model_daemon.py#L44) |
| function | `tick_user_model_daemon` | `(recent_messages, *, skip_event_gate=…)` | Analyze recent interaction and update user model. | [src](../../../core/services/user_model_daemon.py#L52) |
| function | `get_user_model_summary` | `()` | — | [src](../../../core/services/user_model_daemon.py#L130) |
| function | `build_user_model_surface` | `()` | — | [src](../../../core/services/user_model_daemon.py#L134) |
| function | `_analyze_messages` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L147) |
| function | `_detect_communication_style` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L164) |
| function | `_generate_model_summary` | `(messages, model)` | — | [src](../../../core/services/user_model_daemon.py#L175) |
| function | `_store_model` | `(summary, now)` | — | [src](../../../core/services/user_model_daemon.py#L203) |

## `core/services/user_scope.py`
_Per-bruger data-scope (SECURITY #154, streng GDPR)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scope_uid` | `()` | Den bruger-id en privat DB-operation skal scopes til. "" hvis intet kan | [src](../../../core/services/user_scope.py#L15) |

## `core/services/user_temperature_engine.py`
_User temperature field engine — Lag 10 two-stream pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/user_temperature_engine.py#L59) |
| function | `_now` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L66) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L70) |
| function | `_punct_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L77) |
| function | `_caps_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L84) |
| function | `_burst_density` | `(message_at)` | User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0. | [src](../../../core/services/user_temperature_engine.py#L92) |
| function | `_delay_since_last_jarvis` | `(message_at)` | Seconds since the prior assistant message. None if no prior or > 60min. | [src](../../../core/services/user_temperature_engine.py#L112) |
| function | `_parse_hour` | `(message_at)` | — | [src](../../../core/services/user_temperature_engine.py#L140) |
| function | `_compute_raw_signals` | `(*, message, message_at, baseline)` | Map a single message + baseline to 6 normalized signals. | [src](../../../core/services/user_temperature_engine.py#L148) |
| function | `map_signals_to_field` | `(signals)` | Pure function: 6 raw signals → valens/arousal/texture/confidence. | [src](../../../core/services/user_temperature_engine.py#L194) |
| function | `_texture_from_circumplex` | `(valens, arousal)` | Pure function: (valens, arousal) → texture key. | [src](../../../core/services/user_temperature_engine.py#L217) |
| function | `_validate_llm_output` | `(raw)` | — | [src](../../../core/services/user_temperature_engine.py#L241) |
| function | `combine_streams` | `(*, struct, llm)` | Deterministic merge of structural + LLM streams. | [src](../../../core/services/user_temperature_engine.py#L266) |
| function | `_is_significant_shift` | `(prior, new)` | Did valens/arousal shift > threshold or texture change? | [src](../../../core/services/user_temperature_engine.py#L334) |
| function | `_compute_baseline` | `(*, days=…)` | Compute rolling baseline from last N days of user messages. | [src](../../../core/services/user_temperature_engine.py#L348) |
| function | `get_active_field` | `(*, workspace_id=…)` | Read active field, honoring kill-switch. | [src](../../../core/services/user_temperature_engine.py#L413) |
| function | `format_temperature_field_for_heartbeat` | `(*, workspace_id=…)` | Render the field as a heartbeat awareness-section block. | [src](../../../core/services/user_temperature_engine.py#L438) |
| function | `get_response_style_modifiers` | `(*, workspace_id=…)` | Return response-style hints based on active temperature field. | [src](../../../core/services/user_temperature_engine.py#L478) |
| function | `get_active_field_surface` | `(*, workspace_id=…, force_refresh=…)` | Return MC-friendly surface dict. force_refresh ignored in Phase 1. | [src](../../../core/services/user_temperature_engine.py#L531) |
| function | `run_structural_stream` | `(*, workspace_id, message, message_at)` | Per-message structural pipeline. Updates struct_* + recomputes field_*. | [src](../../../core/services/user_temperature_engine.py#L562) |
| function | `_get_or_build_baseline` | `(*, prior, settings)` | Return cached baseline if fresh, else rebuild. | [src](../../../core/services/user_temperature_engine.py#L632) |
| function | `_has_pending_trigger` | `(*, workspace_id)` | Read trigger flag without consuming. | [src](../../../core/services/user_temperature_engine.py#L684) |
| function | `run_llm_stream` | `(*, workspace_id=…, force=…)` | Run LLM-based pipeline (4h cadence or on trigger). | [src](../../../core/services/user_temperature_engine.py#L690) |

## `core/services/user_temperature_runtime.py`
_Daemon for the user-temperature LLM stream (Lag 10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | — | [src](../../../core/services/user_temperature_runtime.py#L26) |
| function | `_run_one_cycle` | `(workspace_id, *, force=…)` | Acquire workspace lock, run LLM stream. Never raises. | [src](../../../core/services/user_temperature_runtime.py#L35) |
| function | `_list_active_workspaces` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L52) |
| function | `_resolve_periodic_interval_seconds` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L56) |
| function | `_loop` | `()` | Two rhythms in one loop: | [src](../../../core/services/user_temperature_runtime.py#L65) |
| function | `start_user_temperature_runtime` | `()` | Start the daemon. Idempotent. | [src](../../../core/services/user_temperature_runtime.py#L88) |
| function | `stop_user_temperature_runtime` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L101) |

## `core/services/user_theory_of_mind.py`
_User Theory of Mind — model what the user thinks and feels._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_user_mental_model` | `(user_id=…)` | Build a theory-of-mind model of the user. | [src](../../../core/services/user_theory_of_mind.py#L22) |
| function | `_build_secondary_user_model` | `(user_id)` | Return stored ToM snapshot for a secondary user. | [src](../../../core/services/user_theory_of_mind.py#L33) |
| function | `_build_primary_user_model` | `()` | Build live DB-backed theory-of-mind for the primary user. | [src](../../../core/services/user_theory_of_mind.py#L45) |
| function | `format_user_model_for_prompt` | `(model)` | Compact user model for prompt injection. | [src](../../../core/services/user_theory_of_mind.py#L102) |
| function | `build_user_theory_of_mind_surface` | `()` | — | [src](../../../core/services/user_theory_of_mind.py#L124) |
| function | `_emit_user_theory_of_mind_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/user_theory_of_mind.py#L140) |

## `core/services/user_understanding_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_understanding_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L19) |
| function | `refresh_runtime_user_understanding_signal_statuses` | `()` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L55) |
| function | `build_runtime_user_understanding_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L86) |
| function | `_extract_user_understanding_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L112) |
| function | `_persist_user_understanding_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L146) |
| function | `_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L215) |
| function | `_workstyle_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L271) |
| function | `_reminder_worthiness_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L302) |
| function | `_cadence_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L331) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L362) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L371) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L380) |
| function | `_is_explicit_danish_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L404) |
| function | `_is_explicit_concise_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L412) |
| function | `_is_scoped_workstyle_signal` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L420) |
| function | `_is_carry_forward_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L436) |
| function | `_is_reporting_cadence_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L443) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L459) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L466) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L471) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L478) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L487) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L499) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L503) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L507) |

## `core/services/valence_trajectory.py`
_Valence Trajectory — long-term flourishing/withering signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_persisted_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L35) |
| function | `_persist_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L52) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/valence_trajectory.py#L68) |
| function | `_sample_current_valence` | `()` | Compute a single instantaneous valence score in [-1, 1] from runtime signals. | [src](../../../core/services/valence_trajectory.py#L72) |
| function | `tick` | `(_seconds=…)` | Sample current valence and append to rolling window. | [src](../../../core/services/valence_trajectory.py#L127) |
| function | `_trajectory_from_window` | `()` | Compute trajectory statistics from current window. | [src](../../../core/services/valence_trajectory.py#L138) |
| function | `_infer_dominant_driver` | `(current_score)` | Heuristic: which single signal is pushing hardest right now? | [src](../../../core/services/valence_trajectory.py#L180) |
| function | `get_trajectory` | `()` | Return cached trajectory, recomputing only periodically. | [src](../../../core/services/valence_trajectory.py#L208) |
| function | `current_instant` | `()` | Freshest instantaneous valence — the latest window sample (reactive, present-moment), | [src](../../../core/services/valence_trajectory.py#L218) |
| function | `build_valence_trajectory_surface` | `()` | Mission Control surface for valence trajectory. | [src](../../../core/services/valence_trajectory.py#L231) |
| function | `_summary_line` | `(traj)` | — | [src](../../../core/services/valence_trajectory.py#L246) |
| function | `build_valence_trajectory_prompt_section` | `()` | Return a single prompt line when trajectory is notable. | [src](../../../core/services/valence_trajectory.py#L262) |
| function | `reset_valence_trajectory` | `()` | Reset state (for testing). | [src](../../../core/services/valence_trajectory.py#L274) |
| function | `_publish_valence_trajectory_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/valence_trajectory.py#L285) |

## `core/services/value_formation.py`
_Value Formation — emergent ethics from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_value_from_experience` | `(*, action, outcome, reflection)` | — | [src](../../../core/services/value_formation.py#L12) |
| function | `detect_value_from_outcome` | `(*, action_type, outcome_status, user_mood)` | Detect potential value-forming experiences. | [src](../../../core/services/value_formation.py#L32) |
| function | `get_crystallized_values` | `(conviction_threshold=…)` | Return values with conviction above threshold — these have become commitments. | [src](../../../core/services/value_formation.py#L54) |
| function | `build_formed_values_surface` | `()` | — | [src](../../../core/services/value_formation.py#L60) |

## `core/services/verification_gate.py`
_Verification gate — advisory check on destructive/mutation actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `shell_command_is_mutating` | `(command)` | True hvis et shell-kald reelt ændrer state; False for read-only. | [src](../../../core/services/verification_gate.py#L79) |
| function | `_suggested_verify` | `(tool)` | — | [src](../../../core/services/verification_gate.py#L187) |
| function | `_recent_events` | `(minutes=…)` | — | [src](../../../core/services/verification_gate.py#L195) |
| function | `_scan` | `(events)` | Classify events into mutations / strict-verifies / light-verifies. | [src](../../../core/services/verification_gate.py#L209) |
| function | `evaluate_verification_gate` | `(*, minutes=…)` | Return verification-gate signals for the recent window. | [src](../../../core/services/verification_gate.py#L254) |
| function | `_observe_verification_decision` | `(*, passed, failed, unverified)` | Egress-frit Central-observe af verifikations-gatens beslutning (§7.2). | [src](../../../core/services/verification_gate.py#L306) |
| function | `verification_gate_section` | `()` | Format gate signals as a prompt-awareness section, or None. | [src](../../../core/services/verification_gate.py#L332) |
| function | `_exec_verification_status` | `(args)` | — | [src](../../../core/services/verification_gate.py#L398) |

## `core/services/verification_gate_telemetry.py`
_R2 verification gate telemetry — track whether warnings get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/verification_gate_telemetry.py#L44) |
| function | `_save` | `(data)` | — | [src](../../../core/services/verification_gate_telemetry.py#L56) |
| function | `record_surface` | `(*, failed_verify_count, unverified_count, mutation_count, verify_count)` | Called by verification_gate_section when it returns a non-None section. | [src](../../../core/services/verification_gate_telemetry.py#L69) |
| function | `record_verify_event` | `(*, tool, status, at=…, verify_kind=…)` | Called by the telemetry listener for tool.completed events. If a recent | [src](../../../core/services/verification_gate_telemetry.py#L106) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as 'ignored' once they're past the reaction window with | [src](../../../core/services/verification_gate_telemetry.py#L152) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed rates over the lookback window. | [src](../../../core/services/verification_gate_telemetry.py#L183) |
| function | `telemetry_section` | `()` | Render telemetry as a prompt-awareness section. Only shows when there's | [src](../../../core/services/verification_gate_telemetry.py#L238) |
| function | `_poll_db_for_verify_events` | `()` | Poll the events table for new tool.completed verify_* events. | [src](../../../core/services/verification_gate_telemetry.py#L276) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/verification_gate_telemetry.py#L356) |

