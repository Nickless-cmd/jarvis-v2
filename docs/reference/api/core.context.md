# `core.context` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/context/__init__.py`

_(no top-level classes or functions)_

## `core/context/compact_ground_truth.py`
_Ground-truth injection and freshness checking for context compaction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_current_git_sha` | `()` | Get the current git HEAD SHA of the Jarvis repo. Returns empty string on failure. | [src](../../../core/context/compact_ground_truth.py#L58) |
| function | `get_commit_count_since` | `(start_sha=…)` | Count commits between start_sha and HEAD. Returns None if start_sha is empty or unknown. | [src](../../../core/context/compact_ground_truth.py#L71) |
| function | `get_recent_commit_log` | `(since=…, count=…)` | Get recent git log as oneline. Optionally since an ISO timestamp. | [src](../../../core/context/compact_ground_truth.py#L87) |
| function | `check_key_files` | `(key_files=…)` | Check existence of key files. Returns dict of {relative_path: 'exists'|'missing'}. | [src](../../../core/context/compact_ground_truth.py#L105) |
| function | `check_cognitive_decisions_count` | `()` | Return count of cognitive_decision records in DB, or None on failure. | [src](../../../core/context/compact_ground_truth.py#L115) |
| function | `collect_compact_ground_truth` | `(session_id=…)` | Collect ground-truth data before compaction. | [src](../../../core/context/compact_ground_truth.py#L128) |
| function | `format_ground_truth_block` | `(gt)` | Format a ground-truth dict into a human-readable block for prompt injection. | [src](../../../core/context/compact_ground_truth.py#L163) |
| function | `_parse_compact_claims` | `(marker_text)` | Extract suspicious claims from a compact marker text. | [src](../../../core/context/compact_ground_truth.py#L213) |
| function | `_identifikatorer` | `(tekst)` | Ord i teksten der ligner kode: backtick-citeret, sti/filnavn eller snake_case. | [src](../../../core/context/compact_ground_truth.py#L272) |
| function | `_check_claim_against_ground_truth` | `(claim, ground_truth)` | Check a single claim against ground truth. Returns verification result. | [src](../../../core/context/compact_ground_truth.py#L286) |
| function | `_ensure_compaction_validation_table` | `()` | Create compaction_validation_failures table if it doesn't exist (Lag D prep). | [src](../../../core/context/compact_ground_truth.py#L374) |
| function | `_log_validation_failure` | `(session_id, marker_id, failures)` | Log a validation failure to DB. Returns the row ID or None. | [src](../../../core/context/compact_ground_truth.py#L397) |
| function | `validate_compact_marker` | `(session_id, marker_text, marker_id=…, ground_truth=…)` | Post-compact validation of a compact marker against ground truth. | [src](../../../core/context/compact_ground_truth.py#L448) |
| function | `mark_failures_superseded` | `(session_id, *, new_marker_id)` | Luk aabne valideringsfejl for sessionen: en nyere markoer har afloest dem. | [src](../../../core/context/compact_ground_truth.py#L537) |
| function | `auto_regenerate_compact_marker` | `(session_id, original_marker_id=…)` | Auto-regenerate a compact marker if post-compact validation failed. | [src](../../../core/context/compact_ground_truth.py#L559) |
| function | `get_validation_failures` | `(session_id=…, limit=…)` | Read recent compaction validation failures from DB. | [src](../../../core/context/compact_ground_truth.py#L664) |
| function | `get_validation_failures_summary` | `(session_id=…)` | Get a summary of validation failures for awareness / heartbeat. | [src](../../../core/context/compact_ground_truth.py#L710) |
| function | `get_compact_marker_freshness` | `(stored_sha)` | Check freshness of a stored compact marker against current git HEAD. | [src](../../../core/context/compact_ground_truth.py#L721) |
| function | `_extract_topic_words` | `(text)` | Extract meaningful topic/noun words from a text, filtering noise. | [src](../../../core/context/compact_ground_truth.py#L793) |
| function | `_check_user_message_against_marker` | `(user_msg, marker_text, marker_failures=…)` | Check if a user message corrects a compact marker's false claim. | [src](../../../core/context/compact_ground_truth.py#L815) |
| function | `detect_compact_mismatch_in_chat` | `(session_id)` | Scan recent user messages for corrections contradicting the latest compact marker. | [src](../../../core/context/compact_ground_truth.py#L869) |
| function | `resolve_stale_markers_on_load` | `(session_id)` | Boot-time check: auto-regenerate stale/unresolved compact markers. | [src](../../../core/context/compact_ground_truth.py#L904) |
| function | `compact_healthcheck_daemon_tick` | `()` | Periodic healthcheck: scan all sessions with unresolved validation failures. | [src](../../../core/context/compact_ground_truth.py#L946) |

## `core/context/compact_llm.py`
_Thin wrapper for compact summarisation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_in_pytest` | `()` | Testværn: et betalt provider-kald må ALDRIG fyre fra en test. Fundet | [src](../../../core/context/compact_llm.py#L26) |
| function | `_call_primary` | `(prompt, *, max_tokens)` | Summarise via the PRIMARY (visible) lane — the model that defines Jarvis. | [src](../../../core/context/compact_llm.py#L36) |
| function | `_er_hans_tur` | `()` | Sker det her INDE i en af Bjørns egne kørsler? | [src](../../../core/context/compact_llm.py#L76) |
| function | `_call_cheap_no_groq` | `(prompt)` | Try cheap lane providers, skipping Groq. Returns text or None. | [src](../../../core/context/compact_llm.py#L112) |
| function | `_call_heartbeat_llm_simple` | `(prompt, max_tokens)` | — | [src](../../../core/context/compact_llm.py#L123) |
| function | `call_compact_llm` | `(prompt, *, max_tokens=…, tillad_betalt=…)` | Summarise prompt. Tries non-Groq cheap providers first, Groq as fallback. | [src](../../../core/context/compact_llm.py#L128) |

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
| function | `_cap_transcript` | `(transcript, max_chars)` | Cap the rendered transcript so a (free/cheap) summariser model isn't handed a huge | [src](../../../core/context/compaction_policy.py#L261) |
| function | `build_structured_summary_prompt` | `(old_messages, *, focus=…, ground_truth=…, max_transcript_chars=…)` | Structured, thread-preserving summary prompt over the OLD messages. | [src](../../../core/context/compaction_policy.py#L272) |
| function | `extract_summary` | `(raw)` | Pull the usable summary out of a raw model response: drop any <thinking> scratchpad, | [src](../../../core/context/compaction_policy.py#L305) |
| function | `summary_looks_valid` | `(summary_text, *, min_chars=…)` | Quality gate on the EXTRACTED summary. Rejects empty/too-short, the mechanical-fallback | [src](../../../core/context/compaction_policy.py#L316) |

## `core/context/compaction_signal.py`
_Er sessionen ved at blive komprimeret — og hvornaar blev den det sidst?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_noegle` | `(session_id)` | — | [src](../../../core/context/compaction_signal.py#L41) |
| function | `marker_start` | `(session_id)` | Komprimering startet for sessionen. Kaster aldrig. | [src](../../../core/context/compaction_signal.py#L45) |
| function | `marker_slut` | `(session_id)` | Komprimering faerdig — ogsaa naar den fejlede. Kaster aldrig. | [src](../../../core/context/compaction_signal.py#L61) |
| function | `er_i_gang` | `(session_id)` | Koerer der en komprimering for sessionen i NOGEN proces? | [src](../../../core/context/compaction_signal.py#L73) |
| function | `seneste_komprimering` | `(session_id)` | Tidspunktet for sessionens seneste komprimerings-markoer, ellers "". | [src](../../../core/context/compaction_signal.py#L85) |

## `core/context/kompaktering.py`
_Kontekst-komprimering: ÉN sti, med de garantier den manglede._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NotAdvancing` | `` | Komprimeringen gjorde ikke overfladen mindre. Et genforsoeg ville vaere | [src](../../../core/context/kompaktering.py#L53) |
| class | `StruktureretOpsummering` | `` | summarise_fn til `compact_session_history`, med sporet `vej` bagefter. | [src](../../../core/context/kompaktering.py#L61) |
| method | `StruktureretOpsummering.__init__` | `(self, focus=…, *, session_id=…)` | — | [src](../../../core/context/kompaktering.py#L73) |
| method | `StruktureretOpsummering.__call__` | `(self, old_msgs)` | — | [src](../../../core/context/kompaktering.py#L80) |
| function | `_kald_med_timeout` | `(fn, *args, **kwargs)` | Kald `fn` med en timeout der FAKTISK afbryder ventetiden. | [src](../../../core/context/kompaktering.py#L107) |
| function | `mekanisk_opsummering` | `(old_msgs)` | Deterministisk opsummering naar modellen ikke leverede. Aldrig tom. | [src](../../../core/context/kompaktering.py#L130) |
| function | `_ground_truth_for` | `(session_id)` | — | [src](../../../core/context/kompaktering.py#L160) |
| function | `_sikr_tabel` | `(conn)` | — | [src](../../../core/context/kompaktering.py#L172) |
| function | `_sidste_besked_id` | `(conn, session_id)` | — | [src](../../../core/context/kompaktering.py#L193) |
| function | `log_komprimering` | `(session_id, *, udloeser, vej, tokens_foer, tokens_efter, fremdrift, marker_id=…, fejl=…)` | — | [src](../../../core/context/kompaktering.py#L201) |
| function | `staar_fast` | `(session_id)` | Sidste forsoeg gav ingen fremdrift, og der er ikke kommet noget nyt siden. | [src](../../../core/context/kompaktering.py#L233) |
| function | `seneste_log` | `(session_id)` | — | [src](../../../core/context/kompaktering.py#L255) |
| function | `komprimer_session` | `(session_id, *, udloeser, focus=…, low_water_tokens=…)` | Komprimér sessionen. Returnerer `CompactResult`, eller None hvis der | [src](../../../core/context/kompaktering.py#L274) |

## `core/context/microcompact.py`
_Time-gap microcompaction for visible transcript tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_utc` | `()` | — | [src](../../../core/context/microcompact.py#L18) |
| function | `_enabled` | `()` | — | [src](../../../core/context/microcompact.py#L22) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/context/microcompact.py#L30) |
| function | `_latest_assistant_at` | `(messages)` | — | [src](../../../core/context/microcompact.py#L43) |
| function | `_is_stubbed` | `(content)` | — | [src](../../../core/context/microcompact.py#L52) |
| function | `_stub_tool_result` | `(message)` | — | [src](../../../core/context/microcompact.py#L56) |
| function | `apply_time_gap_microcompact` | `(messages, *, now=…, gap_minutes=…, keep_recent_tools=…)` | Stub old tool results after a long quiet gap. | [src](../../../core/context/microcompact.py#L63) |

## `core/context/session_compact.py`
_Session-level context compaction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CompactResult` | `` | — | [src](../../../core/context/session_compact.py#L18) |
| function | `compact_session_history` | `(session_id, *, keep_recent=…, keep_recent_tokens=…, summarise_fn, git_sha=…, kraev_fremdrift=…)` | Compact old session history for session_id. | [src](../../../core/context/session_compact.py#L33) |
| function | `_estimer` | `(m)` | — | [src](../../../core/context/session_compact.py#L212) |
| function | `_get_all_session_messages` | `(session_id)` | Det Jarvis SER: den forrige markoer + alle beskeder efter den. | [src](../../../core/context/session_compact.py#L216) |
| function | `_store_marker` | `(session_id, summary_text, git_sha=…)` | — | [src](../../../core/context/session_compact.py#L241) |

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
| function | `user_message_ids` | `(messages)` | Ids for role=='user' messages, ascending (= run boundaries). | [src](../../../core/context/tool_result_lifecycle.py#L52) |
| function | `estimate_tool_tokens` | `(messages)` | Sum of tool-result tokens (heuristic len//4). Only role=='tool'. | [src](../../../core/context/tool_result_lifecycle.py#L64) |
| function | `_candidate_by_runs` | `(user_ids, run_window)` | Floor so exactly the last `run_window` user-turns stay warm. | [src](../../../core/context/tool_result_lifecycle.py#L73) |
| function | `_candidate_by_tokens` | `(messages, token_ceiling)` | Floor so warm tool-tokens <= ceiling. Walks newest->oldest. | [src](../../../core/context/tool_result_lifecycle.py#L81) |
| function | `compute_new_floor` | `(messages, *, current_floor, run_window, token_ceiling, hysteresis)` | New cold_floor. Monotonic (>= current_floor). 0 = nothing cold yet. | [src](../../../core/context/tool_result_lifecycle.py#L94) |
| function | `as_bool` | `(value, default=…)` | Robust bool-tolkning. ``bool("off")`` er True — den fælde har kostet os før. | [src](../../../core/context/tool_result_lifecycle.py#L140) |
| function | `should_advance` | `(*, warm_tool_tokens, current_epoch, recorded_epoch, hard_ceiling, only_on_compact=…)` | Må gulvet rykke nu? Ren beslutning. Returnerer (ja/nej, grund). | [src](../../../core/context/tool_result_lifecycle.py#L160) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/context/tool_result_lifecycle.py#L199) |
| function | `latest_compact_marker_id` | `(session_id)` | Id på sessionens nyeste compact_marker, 0 hvis den aldrig er komprimeret. | [src](../../../core/context/tool_result_lifecycle.py#L216) |
| function | `get_cold_floor` | `(session_id)` | — | [src](../../../core/context/tool_result_lifecycle.py#L243) |
| function | `get_compact_epoch` | `(session_id)` | Compact-markør-id fra sidste gang gulvet rykkede (0 = aldrig). | [src](../../../core/context/tool_result_lifecycle.py#L260) |
| function | `set_cold_floor` | `(session_id, floor_id, compact_epoch=…)` | Monotonic: writes only if floor_id > existing. | [src](../../../core/context/tool_result_lifecycle.py#L281) |
| function | `_load_session_messages` | `(session_id)` | Growing-window messages WITH id (a later task adds id to the return dict). | [src](../../../core/context/tool_result_lifecycle.py#L304) |
| function | `_load_settings` | `()` | — | [src](../../../core/context/tool_result_lifecycle.py#L310) |
| function | `evaluate_and_advance` | `(session_id, *, settings=…)` | Called at RUN-END (sole writer). Returns new cold_floor (0=none). | [src](../../../core/context/tool_result_lifecycle.py#L315) |

