# `core.services.22` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_is_autonomous_session` | `(session_id)` | — | [src](../../../core/services/theory_of_mind.py#L239) |
| function | `record_message` | `(*, role, content, partner_id=…, session_id=…, message_id=…)` | Extract factual sentences from a message and record each one. | [src](../../../core/services/theory_of_mind.py#L244) |
| function | `recent_facts` | `(*, partner_id=…, origin=…, hours=…, limit=…)` | — | [src](../../../core/services/theory_of_mind.py#L286) |
| function | `has_been_told` | `(fact_text, *, partner_id=…, hours=…)` | Has Jarvis told partner this fact within the time window? | [src](../../../core/services/theory_of_mind.py#L312) |
| function | `repetition_warnings` | `(*, partner_id=…, hours=…, threshold=…)` | Facts Jarvis has repeated to partner at or above threshold within window. | [src](../../../core/services/theory_of_mind.py#L337) |
| function | `communication_ledger_section` | `(*, partner_id=…)` | Quiet by default. Surfaces only when Jarvis is repeating himself. | [src](../../../core/services/theory_of_mind.py#L363) |
| function | `_listener_loop` | `()` | Poll events table for channel.chat_message_appended events. | [src](../../../core/services/theory_of_mind.py#L390) |
| function | `start_theory_of_mind_tracker` | `()` | Start the DB-polling listener. Idempotent. | [src](../../../core/services/theory_of_mind.py#L454) |
| function | `stop_theory_of_mind_tracker` | `()` | — | [src](../../../core/services/theory_of_mind.py#L471) |

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
| function | `_short_desc` | `(tool_def)` | — | [src](../../../core/services/tool_catalog.py#L94) |
| function | `_registry_hash` | `()` | — | [src](../../../core/services/tool_catalog.py#L108) |
| function | `build_catalog_text` | `()` | Return cached catalog text; rebuild only if tool registry changed. | [src](../../../core/services/tool_catalog.py#L123) |
| function | `catalog_token_estimate` | `()` | Rough char/4 token estimate of the current catalog. | [src](../../../core/services/tool_catalog.py#L159) |
| function | `invalidate_cache` | `()` | Force next call to rebuild. Useful in tests. | [src](../../../core/services/tool_catalog.py#L164) |

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
| function | `summarize_result` | `(content, max_length=…)` | — | [src](../../../core/services/tool_result_store.py#L20) |
| function | `save_tool_result` | `(tool_name, arguments, result_content, *, created_at=…)` | — | [src](../../../core/services/tool_result_store.py#L27) |
| function | `get_tool_result` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L56) |
| function | `cleanup_old_results` | `(max_age_days=…)` | — | [src](../../../core/services/tool_result_store.py#L72) |
| function | `build_tool_result_reference` | `(result_id, *, tool_name, summary)` | — | [src](../../../core/services/tool_result_store.py#L89) |
| function | `parse_tool_result_reference` | `(content)` | — | [src](../../../core/services/tool_result_store.py#L101) |
| function | `render_tool_result_for_prompt` | `(content, *, expand, max_chars=…, stub=…)` | — | [src](../../../core/services/tool_result_store.py#L122) |
| function | `_result_path` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L172) |
| function | `_prefixed_tool_text` | `(tool_name, text)` | — | [src](../../../core/services/tool_result_store.py#L176) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/tool_result_store.py#L184) |

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

## `core/services/tool_world_change.py`
_Ændrede dette værktøjskald verden? (loop-fix 2026-09-05)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_shell_command` | `(arguments)` | — | [src](../../../core/services/tool_world_change.py#L37) |
| function | `_mutation_tool_names` | `()` | Navne fra verification_gate — ét sted at vedligeholde listen. | [src](../../../core/services/tool_world_change.py#L45) |
| function | `call_changed_the_world` | `(*, tool_name, arguments=…, status=…)` | True når kaldet reelt ændrede state (og lykkedes). | [src](../../../core/services/tool_world_change.py#L54) |
| function | `round_changed_the_world` | `(results)` | Ændrede mindst ét kald i denne agentiske runde verden? | [src](../../../core/services/tool_world_change.py#L83) |

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
| function | `_er_mellemmenneskeligt` | `(text, m)` | Peger paastanden paa en person eller paa noget der er SAGT? | [src](../../../core/services/truth_gate_v2.py#L74) |
| function | `detect_action_claims` | `(text)` | Deterministisk: find handlings-påstande. commit_hash tæller kun i commit/git/log- | [src](../../../core/services/truth_gate_v2.py#L85) |
| function | `_run_result_text` | `(followup_exchanges)` | — | [src](../../../core/services/truth_gate_v2.py#L141) |
| function | `verify_claim` | `(claim, executed_tool_names, followup_exchanges)` | In-run evidens: kørte et tool i kategorien? + (for citeret output/hash) matcher | [src](../../../core/services/truth_gate_v2.py#L149) |
| function | `classify_severity` | `(claims)` | — | [src](../../../core/services/truth_gate_v2.py#L194) |
| function | `_footnote_for` | `(claim)` | Byg én fodnote-linje for et uverificeret claim i den konsistente stil. | [src](../../../core/services/truth_gate_v2.py#L198) |
| function | `_annotate` | `(text, claims)` | Bevar teksten + append fodnote(r) i bunden (én pr. claim, adskilt fra | [src](../../../core/services/truth_gate_v2.py#L208) |
| function | `_annotate_soft` | `(text, claims=…)` | Bagudkompatibel: bløde påstande → fodnote. (claims valgfri; uden dem | [src](../../../core/services/truth_gate_v2.py#L217) |
| function | `_llm_judge` | `(text)` | Spørg billig lane om teksten påstår en handling der kræver tool-evidens. | [src](../../../core/services/truth_gate_v2.py#L232) |
| function | `_maybe_llm_claim` | `(text)` | LLM-dommer KUN hvis teksten har et handlings-hint men intet deterministisk match. | [src](../../../core/services/truth_gate_v2.py#L247) |
| function | `truth_gate_v2` | `(ctx)` | ctx: {text, executed_tool_names, followup_exchanges, run_id, session_id}. | [src](../../../core/services/truth_gate_v2.py#L261) |

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
| function | `_tail` | `(text, n=…)` | Returner sidste ~n tegn af teksten. | [src](../../../core/services/unfinished_intent.py#L126) |
| function | `detect_unfinished_intent` | `(text)` | Returner UnfinishedIntent hvis teksten antyder Jarvis stoppede midt | [src](../../../core/services/unfinished_intent.py#L133) |
| function | `is_in_cooldown` | `(session_id)` | True hvis session_id har triggered en continuation indenfor cooldown-vinduet. | [src](../../../core/services/unfinished_intent.py#L239) |
| function | `mark_triggered` | `(session_id)` | Marker at en continuation netop er triggered for session_id. | [src](../../../core/services/unfinished_intent.py#L248) |
| function | `reset_cooldown_for_tests` | `()` | Test-helper: tøm cooldown-state mellem test cases. | [src](../../../core/services/unfinished_intent.py#L256) |

## `core/services/untrusted_fencing.py`
_Indhegning af utroet indhold — porteret fra jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_neutralisér` | `(tekst)` | Afvaebn hegn-markoerer INDE i nyttelasten. | [src](../../../core/services/untrusted_fencing.py#L46) |
| function | `fence` | `(kilde, indhold)` | Pak indhold ind som utroet data. Self-safe. | [src](../../../core/services/untrusted_fencing.py#L63) |
| function | `kilde_for_tool` | `(navn)` | Hvilken slags kilde er dette vaerktoejs resultat? Ren. | [src](../../../core/services/untrusted_fencing.py#L71) |
| function | `should_fence` | `(navn)` | Skal dette vaerktoejs resultat hegnes ind? Ren. | [src](../../../core/services/untrusted_fencing.py#L89) |
| function | `_hegn_blok` | `(kilde, blok)` | Hegn teksten i én indholdsblok. Ikke-tekst-blokke roeres ikke. | [src](../../../core/services/untrusted_fencing.py#L102) |
| function | `fence_tool_result` | `(navn, resultat)` | Hegn den laesbare krop af et vaerktoejs-resultat. Self-safe. | [src](../../../core/services/untrusted_fencing.py#L113) |

## `core/services/upload_sandbox.py`
_Uploadede filer og arkiver — pakket ud ét sted, og aldrig eksekverbart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExtractResult` | `` | — | [src](../../../core/services/upload_sandbox.py#L47) |
| method | `ExtractResult.as_dict` | `(self)` | — | [src](../../../core/services/upload_sandbox.py#L55) |
| function | `looks_like_archive` | `(path)` | Er filen et arkiv? Afgøres på INDHOLD, ikke på navn. | [src](../../../core/services/upload_sandbox.py#L61) |
| function | `harden_upload` | `(path)` | Gør en uploadet fil ulæselig for andre og umulig at eksekvere. | [src](../../../core/services/upload_sandbox.py#L76) |
| function | `sandbox_root_for` | `(attachment_id)` | Mappen et bestemt arkiv pakkes ud i. Én pr. vedhæftning. | [src](../../../core/services/upload_sandbox.py#L89) |
| function | `_is_inside` | `(root, candidate)` | Ligger `candidate` under `root` — også efter symlink-opløsning? | [src](../../../core/services/upload_sandbox.py#L95) |
| function | `_reject_name` | `(name)` | Tom streng hvis navnet er i orden, ellers grunden til at det ikke er. | [src](../../../core/services/upload_sandbox.py#L109) |
| function | `_write_entry` | `(dest, data_iter, remaining)` | Skriv én post og returnér antal skrevne bytes. Rejser ValueError ved loft. | [src](../../../core/services/upload_sandbox.py#L122) |
| function | `_chunks` | `(fileobj, size=…)` | — | [src](../../../core/services/upload_sandbox.py#L136) |
| function | `safe_extract` | `(archive_path, attachment_id)` | Pak et arkiv ud i sin egen sandkasse — post for post. | [src](../../../core/services/upload_sandbox.py#L144) |
| function | `scan_tree` | `(root)` | Kør ClamAV på en udpakket sandkasse. (ren, begrundelse). | [src](../../../core/services/upload_sandbox.py#L234) |

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
| function | `build_user_model_prompt_line` | `(*, max_chars=…)` | Én linje til den SYNLIGE prompt — "" når dæmonen intet har målt endnu. | [src](../../../core/services/user_model_daemon.py#L142) |
| function | `_analyze_messages` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L167) |
| function | `_detect_communication_style` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L184) |
| function | `_generate_model_summary` | `(messages, model)` | — | [src](../../../core/services/user_model_daemon.py#L195) |
| function | `_store_model` | `(summary, now)` | — | [src](../../../core/services/user_model_daemon.py#L223) |

