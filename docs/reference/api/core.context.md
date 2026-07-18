# `core.context` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/context/__init__.py`

_(no top-level classes or functions)_

## `core/context/auto_compact.py`
_Auto-compact: triggers smart session compaction when approaching context limit._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compaction_threshold` | `(*, provider, model, flat_fallback)` | Model-window-aware compaction threshold: window × 0.70. So a 1M-window lane compacts at ~700k | [src](../../../core/context/auto_compact.py#L19) |
| function | `maybe_auto_compact_session` | `(session_id, *, provider=…, model=…)` | Check session token count and compact if above threshold. Returns True if compacted. | [src](../../../core/context/auto_compact.py#L32) |

## `core/context/compact_ground_truth.py`
_Ground-truth injection and freshness checking for context compaction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_current_git_sha` | `()` | Get the current git HEAD SHA of the Jarvis repo. Returns empty string on failure. | [src](../../../core/context/compact_ground_truth.py#L57) |
| function | `get_commit_count_since` | `(start_sha=…)` | Count commits between start_sha and HEAD. Returns None if start_sha is empty or unknown. | [src](../../../core/context/compact_ground_truth.py#L70) |
| function | `get_recent_commit_log` | `(since=…, count=…)` | Get recent git log as oneline. Optionally since an ISO timestamp. | [src](../../../core/context/compact_ground_truth.py#L86) |
| function | `check_key_files` | `(key_files=…)` | Check existence of key files. Returns dict of {relative_path: 'exists'|'missing'}. | [src](../../../core/context/compact_ground_truth.py#L104) |
| function | `check_cognitive_decisions_count` | `()` | Return count of cognitive_decision records in DB, or None on failure. | [src](../../../core/context/compact_ground_truth.py#L114) |
| function | `collect_compact_ground_truth` | `(session_id=…)` | Collect ground-truth data before compaction. | [src](../../../core/context/compact_ground_truth.py#L127) |
| function | `format_ground_truth_block` | `(gt)` | Format a ground-truth dict into a human-readable block for prompt injection. | [src](../../../core/context/compact_ground_truth.py#L162) |
| function | `_parse_compact_claims` | `(marker_text)` | Extract suspicious claims from a compact marker text. | [src](../../../core/context/compact_ground_truth.py#L212) |
| function | `_check_claim_against_ground_truth` | `(claim, ground_truth)` | Check a single claim against ground truth. Returns verification result. | [src](../../../core/context/compact_ground_truth.py#L271) |
| function | `_ensure_compaction_validation_table` | `()` | Create compaction_validation_failures table if it doesn't exist (Lag D prep). | [src](../../../core/context/compact_ground_truth.py#L354) |
| function | `_log_validation_failure` | `(session_id, marker_id, failures)` | Log a validation failure to DB. Returns the row ID or None. | [src](../../../core/context/compact_ground_truth.py#L377) |
| function | `validate_compact_marker` | `(session_id, marker_text, marker_id=…, ground_truth=…)` | Post-compact validation of a compact marker against ground truth. | [src](../../../core/context/compact_ground_truth.py#L428) |
| function | `auto_regenerate_compact_marker` | `(session_id, original_marker_id=…)` | Auto-regenerate a compact marker if post-compact validation failed. | [src](../../../core/context/compact_ground_truth.py#L514) |
| function | `get_validation_failures` | `(session_id=…, limit=…)` | Read recent compaction validation failures from DB. | [src](../../../core/context/compact_ground_truth.py#L598) |
| function | `get_validation_failures_summary` | `(session_id=…)` | Get a summary of validation failures for awareness / heartbeat. | [src](../../../core/context/compact_ground_truth.py#L644) |
| function | `get_compact_marker_freshness` | `(stored_sha)` | Check freshness of a stored compact marker against current git HEAD. | [src](../../../core/context/compact_ground_truth.py#L655) |
| function | `_extract_topic_words` | `(text)` | Extract meaningful topic/noun words from a text, filtering noise. | [src](../../../core/context/compact_ground_truth.py#L727) |
| function | `_check_user_message_against_marker` | `(user_msg, marker_text, marker_failures=…)` | Check if a user message corrects a compact marker's false claim. | [src](../../../core/context/compact_ground_truth.py#L749) |
| function | `detect_compact_mismatch_in_chat` | `(session_id)` | Scan recent user messages for corrections contradicting the latest compact marker. | [src](../../../core/context/compact_ground_truth.py#L803) |
| function | `resolve_stale_markers_on_load` | `(session_id)` | Boot-time check: auto-regenerate stale/unresolved compact markers. | [src](../../../core/context/compact_ground_truth.py#L838) |
| function | `compact_healthcheck_daemon_tick` | `()` | Periodic healthcheck: scan all sessions with unresolved validation failures. | [src](../../../core/context/compact_ground_truth.py#L880) |

## `core/context/compact_llm.py`
_Thin wrapper for compact summarisation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_cheap_no_groq` | `(prompt)` | Try cheap lane providers, skipping Groq. Returns text or None. | [src](../../../core/context/compact_llm.py#L20) |
| function | `_call_heartbeat_llm_simple` | `(prompt, max_tokens)` | — | [src](../../../core/context/compact_llm.py#L31) |
| function | `call_compact_llm` | `(prompt, *, max_tokens=…)` | Summarise prompt. Tries non-Groq cheap providers first, Groq as fallback. | [src](../../../core/context/compact_llm.py#L36) |

## `core/context/compaction_policy.py`
_Model-aware, round-atomic compaction policy (PURE — no DB, no clock, no LLM)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CompactionDecision` | `` | — | [src](../../../core/context/compaction_policy.py#L38) |
| function | `compaction_decision` | `(transcript_tokens, *, provider, model, attention_budget, low_water, safety_fraction, model_window_fn)` | Decide whether to compact, model-aware. | [src](../../../core/context/compaction_policy.py#L47) |
| function | `group_rounds` | `(messages)` | A round = a user message + everything up to (not including) the next user message. | [src](../../../core/context/compaction_policy.py#L97) |
| function | `round_is_open` | `(round_msgs)` | True when the round ends with tool_calls whose results haven't all arrived — | [src](../../../core/context/compaction_policy.py#L114) |
| function | `_msg_tokens` | `(m)` | — | [src](../../../core/context/compaction_policy.py#L127) |
| function | `select_for_compaction` | `(messages, *, keep_recent_tokens)` | Split messages into (old_to_summarize, kept_tail), ROUND-ATOMIC. | [src](../../../core/context/compaction_policy.py#L134) |
| function | `_is_stub` | `(content)` | — | [src](../../../core/context/compaction_policy.py#L176) |
| function | `fold_old_tool_results` | `(messages, keep=…)` | Fold every tool_result (role=="tool") OLDER than the newest `keep` into a short stub, | [src](../../../core/context/compaction_policy.py#L181) |
| function | `render_transcript_for_summary` | `(messages)` | Flatten messages to a text transcript for the summarizer. tool_use/tool_result | [src](../../../core/context/compaction_policy.py#L208) |
| function | `_cap_transcript` | `(transcript, max_chars)` | Cap the rendered transcript so a (free/cheap) summariser model isn't handed a huge | [src](../../../core/context/compaction_policy.py#L254) |
| function | `build_structured_summary_prompt` | `(old_messages, *, focus=…, ground_truth=…, max_transcript_chars=…)` | Structured, thread-preserving summary prompt over the OLD messages. | [src](../../../core/context/compaction_policy.py#L265) |
| function | `extract_summary` | `(raw)` | Pull the usable summary out of a raw model response: drop any <thinking> scratchpad, | [src](../../../core/context/compaction_policy.py#L298) |
| function | `summary_looks_valid` | `(summary_text, *, min_chars=…)` | Quality gate on the EXTRACTED summary. Rejects empty/too-short, the mechanical-fallback | [src](../../../core/context/compaction_policy.py#L309) |

## `core/context/session_compact.py`
_Session-level context compaction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CompactResult` | `` | — | [src](../../../core/context/session_compact.py#L18) |
| function | `compact_session_history` | `(session_id, *, keep_recent=…, keep_recent_tokens=…, summarise_fn, git_sha=…)` | Compact old session history for session_id. | [src](../../../core/context/session_compact.py#L25) |
| function | `_get_all_session_messages` | `(session_id)` | — | [src](../../../core/context/session_compact.py#L146) |
| function | `_store_marker` | `(session_id, summary_text, git_sha=…)` | — | [src](../../../core/context/session_compact.py#L151) |

## `core/context/token_estimate.py`
_Token estimation utilities — heuristic only, no tokenizer required._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `estimate_tokens` | `(text)` | Estimate token count from raw text. | [src](../../../core/context/token_estimate.py#L7) |
| function | `estimate_messages_tokens` | `(messages)` | Estimate total tokens for a list of chat messages. | [src](../../../core/context/token_estimate.py#L12) |

## `core/context/tool_result_lifecycle.py`
_Tool-result lifecycle (visible-lane). Spec 2026-07-16._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `user_message_ids` | `(messages)` | Ids for role=='user' messages, ascending (= run boundaries). | [src](../../../core/context/tool_result_lifecycle.py#L11) |
| function | `estimate_tool_tokens` | `(messages)` | Sum of tool-result tokens (heuristic len//4). Only role=='tool'. | [src](../../../core/context/tool_result_lifecycle.py#L23) |
| function | `_candidate_by_runs` | `(user_ids, run_window)` | Floor so exactly the last `run_window` user-turns stay warm. | [src](../../../core/context/tool_result_lifecycle.py#L32) |
| function | `_candidate_by_tokens` | `(messages, token_ceiling)` | Floor so warm tool-tokens <= ceiling. Walks newest->oldest. | [src](../../../core/context/tool_result_lifecycle.py#L40) |
| function | `compute_new_floor` | `(messages, *, current_floor, run_window, token_ceiling, hysteresis)` | New cold_floor. Monotonic (>= current_floor). 0 = nothing cold yet. | [src](../../../core/context/tool_result_lifecycle.py#L53) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/context/tool_result_lifecycle.py#L88) |
| function | `get_cold_floor` | `(session_id)` | — | [src](../../../core/context/tool_result_lifecycle.py#L96) |
| function | `set_cold_floor` | `(session_id, floor_id)` | Monotonic: writes only if floor_id > existing. | [src](../../../core/context/tool_result_lifecycle.py#L113) |
| function | `_load_session_messages` | `(session_id)` | Growing-window messages WITH id (a later task adds id to the return dict). | [src](../../../core/context/tool_result_lifecycle.py#L131) |
| function | `_load_settings` | `()` | — | [src](../../../core/context/tool_result_lifecycle.py#L137) |
| function | `evaluate_and_advance` | `(session_id, *, settings=…)` | Called at RUN-END (sole writer). Returns new cold_floor (0=none). | [src](../../../core/context/tool_result_lifecycle.py#L142) |

