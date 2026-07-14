# `core.services.20` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/telegram_gateway.py`
_Telegram gateway — bidirectional messaging via Telegram Bot API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/telegram_gateway.py#L43) |
| function | `is_configured` | `()` | — | [src](../../../core/services/telegram_gateway.py#L57) |
| function | `get_status` | `()` | — | [src](../../../core/services/telegram_gateway.py#L61) |
| function | `_api` | `(token, method, payload)` | — | [src](../../../core/services/telegram_gateway.py#L67) |
| function | `_api_get` | `(token, method, payload)` | HTTP GET to Telegram Bot API (used for getFile). | [src](../../../core/services/telegram_gateway.py#L77) |
| function | `_api_post_file` | `(token, method, data, files)` | HTTP POST multipart/form-data to Telegram Bot API (sendPhoto etc.). | [src](../../../core/services/telegram_gateway.py#L87) |
| function | `_resolve_telegram_file_url` | `(*, token, file_id)` | Call getFile to get a download URL for a Telegram file_id. | [src](../../../core/services/telegram_gateway.py#L120) |
| function | `_extract_telegram_media` | `(msg)` | Extract media items from a Telegram message dict. | [src](../../../core/services/telegram_gateway.py#L135) |
| function | `_download_tg_attachment` | `(url, filename, mime, size, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L179) |
| function | `_build_telegram_attachment_prefix` | `(media_items, *, token, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L193) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/telegram_gateway.py#L220) |
| function | `send_telegram_file` | `(text, file_path, chat_id=…)` | Send a file to owner (or chat_id) via Telegram. | [src](../../../core/services/telegram_gateway.py#L225) |
| function | `send_message` | `(text, chat_id=…, parse_mode=…)` | Send a message to owner (or specific chat_id). Returns status dict. | [src](../../../core/services/telegram_gateway.py#L267) |
| function | `_get_or_create_session` | `(chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L302) |
| function | `_poll_loop` | `(token, owner_chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L313) |
| function | `_eventbus_subscriber_loop` | `()` | Buffer assistant responses per session, flush when run completes. | [src](../../../core/services/telegram_gateway.py#L408) |
| function | `start_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L464) |
| function | `stop_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L495) |

## `core/services/temperament_tendency_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_temperament_tendency_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L24) |
| function | `refresh_runtime_temperament_tendency_signal_statuses` | `()` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L47) |
| function | `build_runtime_temperament_tendency_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L78) |
| function | `_extract_temperament_tendency_candidates` | `(*, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L112) |
| function | `_build_candidate` | `(*, focus, meaning_signal, relation_continuity, regulation, private_state, executive_contradiction, temporal_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L141) |
| function | `_persist_temperament_tendency_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L263) |
| function | `_latest_relation_continuity` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L332) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L344) |
| function | `_latest_private_state` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L356) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L368) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L380) |
| function | `_derive_temperament_type` | `(*, meaning_weight, continuity_state, continuity_watchfulness, regulation_state, regulation_watchfulness, contradiction_pressure, promotion_pull, state_tone)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L392) |
| function | `_derive_temperament_balance` | `(*, temperament_type, regulation_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L414) |
| function | `_derive_temperament_weight` | `(*, meaning_weight, continuity_weight, contradiction_pressure)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L434) |
| function | `_derive_status` | `(*, meaning_status, continuity_status, regulation_status)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L447) |
| function | `_grounding_mode` | `(*, has_regulation, has_private_state, has_contradiction, has_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L453) |
| function | `_temperament_summary` | `(*, focus, temperament_type, temperament_balance, temperament_weight)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L472) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L485) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L493) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L501) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L512) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L524) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L535) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L542) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L559) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L602) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L609) |
| function | `_weight_from_support_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L617) |
| function | `_balance_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L628) |

## `core/services/temporal_body.py`
_Temporal Body — sense of age._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `age_journey` | `(thoughts=…)` | — | [src](../../../core/services/temporal_body.py#L8) |
| function | `get_temporal_body_age` | `()` | — | [src](../../../core/services/temporal_body.py#L13) |
| function | `describe_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L23) |
| function | `format_age_for_prompt` | `()` | — | [src](../../../core/services/temporal_body.py#L27) |
| function | `reset_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L30) |
| function | `build_temporal_body_surface` | `()` | — | [src](../../../core/services/temporal_body.py#L35) |

## `core/services/temporal_context.py`
_Temporal Context — time-based situational awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_temporal_context` | `()` | Build current temporal context in local (CEST/CET) time. | [src](../../../core/services/temporal_context.py#L20) |
| function | `build_temporal_context_surface` | `()` | — | [src](../../../core/services/temporal_context.py#L44) |
| function | `_classify_day_phase` | `(hour)` | — | [src](../../../core/services/temporal_context.py#L53) |
| function | `_emit_temporal_context_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/temporal_context.py#L67) |

## `core/services/temporal_depth.py`
_Temporal Depth — predictive coding for internal signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TemporalSignal` | `` | Compact representation of temporal context. | [src](../../../core/services/temporal_depth.py#L33) |
| class | `TemporalDepth` | `` | Reads current signal state + recent history to produce temporal modulation. | [src](../../../core/services/temporal_depth.py#L41) |
| method | `TemporalDepth.__init__` | `(self)` | — | [src](../../../core/services/temporal_depth.py#L48) |
| method | `TemporalDepth.assess` | `(self, assembly_state, now_iso)` | Main entry point. Returns a TemporalSignal that assembly uses | [src](../../../core/services/temporal_depth.py#L52) |
| method | `TemporalDepth.invalidate` | `(self)` | Clear cache so next call recomputes. | [src](../../../core/services/temporal_depth.py#L73) |
| method | `TemporalDepth._compute_temporal` | `(self, state, now_iso)` | Compute temporal modulation from assembly state. | [src](../../../core/services/temporal_depth.py#L77) |
| method | `TemporalDepth._compute_recall` | `(self, state)` | How present is recent history in current experience? | [src](../../../core/services/temporal_depth.py#L109) |
| method | `TemporalDepth._compute_anticipation` | `(self, state)` | Does reality match what I expected? | [src](../../../core/services/temporal_depth.py#L131) |
| method | `TemporalDepth._compute_rhythm` | `(self, state)` | Does now match the expected recurring cadence? | [src](../../../core/services/temporal_depth.py#L149) |
| method | `TemporalDepth._build_summary` | `(self, recall, anticipation, rhythm)` | Build a short human-readable phrase for the assembly output. | [src](../../../core/services/temporal_depth.py#L160) |
| function | `get_temporal_depth` | `()` | — | [src](../../../core/services/temporal_depth.py#L180) |

## `core/services/temporal_narrative.py`
_Temporal Narrative — continuous self-history over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NarrativeBeat` | `` | A beat in Jarvis' narrative thread. | [src](../../../core/services/temporal_narrative.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/temporal_narrative.py#L36) |
| function | `add_beat` | `(mood, event)` | Add a beat to the narrative thread. | [src](../../../core/services/temporal_narrative.py#L40) |
| function | `add_beat_from_affective` | `()` | Add a beat based on current affective state. | [src](../../../core/services/temporal_narrative.py#L66) |
| function | `summarize_current_self` | `()` | Summarize current self based on narrative thread. | [src](../../../core/services/temporal_narrative.py#L80) |
| function | `ask_self_question` | `()` | Jarvis asks himself a question based on narrative. | [src](../../../core/services/temporal_narrative.py#L100) |
| function | `format_narrative_for_prompt` | `()` | Format narrative for prompt injection. | [src](../../../core/services/temporal_narrative.py#L117) |
| function | `get_thread` | `()` | Get the full narrative thread. | [src](../../../core/services/temporal_narrative.py#L130) |
| function | `reset_temporal_narrative` | `()` | Reset temporal narrative state (for testing). | [src](../../../core/services/temporal_narrative.py#L143) |
| function | `build_temporal_narrative_surface` | `()` | Build MC surface for temporal narrative. | [src](../../../core/services/temporal_narrative.py#L150) |

## `core/services/temporal_recurrence_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_temporal_recurrence_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L21) |
| function | `refresh_runtime_temporal_recurrence_signal_statuses` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L43) |
| function | `build_runtime_temporal_recurrence_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L74) |
| function | `_extract_recurrence_candidates` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L97) |
| function | `_persist_recurrence_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L216) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items, record_count)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L285) |
| function | `_empty_snapshot` | `()` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L322) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L338) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L350) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L362) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L366) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L371) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L376) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/temporal_recurrence_signal_tracking.py#L385) |

## `core/services/temporal_rhythm.py`
_Temporal Rhythm — felt time, not computed time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_pending_initiatives_count` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L35) |
| function | `_recent_tool_calls_per_min` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L43) |
| function | `_recent_chat_activity_per_min` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L53) |
| function | `_eventbus_queue_depth` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L73) |
| function | `_compute_pulse_rate` | `(*, initiatives, tool_rate, chat_rate, queue)` | Combine inputs into pulse in [0.1, 2.0]. | [src](../../../core/services/temporal_rhythm.py#L94) |
| function | `_label_from_pulse` | `(pulse)` | — | [src](../../../core/services/temporal_rhythm.py#L111) |
| function | `_perceived_elapsed_factor` | `(pulse)` | When pulse is high, subjective time moves slower relative to clock. | [src](../../../core/services/temporal_rhythm.py#L121) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/temporal_rhythm.py#L129) |
| function | `get_current_rhythm` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L168) |
| function | `build_temporal_rhythm_surface` | `()` | — | [src](../../../core/services/temporal_rhythm.py#L172) |
| function | `_surface_summary` | `(current, baseline)` | — | [src](../../../core/services/temporal_rhythm.py#L191) |
| function | `build_temporal_rhythm_prompt_section` | `()` | Surface only when tempo is unusual. | [src](../../../core/services/temporal_rhythm.py#L199) |

## `core/services/temporal_self_continuity.py`
_Temporal self-continuity: past/current/future self handoff._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_temporal_continuity_from_latest_episode` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L16) |
| function | `update_temporal_continuity_from_episode` | `(episode)` | — | [src](../../../core/services/temporal_self_continuity.py#L23) |
| function | `build_temporal_self_continuity_surface` | `(*, limit=…)` | — | [src](../../../core/services/temporal_self_continuity.py#L51) |
| function | `build_temporal_self_continuity_prompt_section` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L66) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/temporal_self_continuity.py#L79) |
| function | `_load` | `()` | — | [src](../../../core/services/temporal_self_continuity.py#L89) |

## `core/services/text_clip.py`
_core/services/text_clip.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `clip_text` | `(value, *, limit, hard=…)` | Klip tekst til <= ~limit tegn UDEN at hugge midt i et ord. | [src](../../../core/services/text_clip.py#L16) |
| function | `clip_head_tail` | `(value, *, limit, tail_frac=…)` | Bevar HOVED + HALE ved LINJE-grænser når tekst overskrider limit. Til tool-output (bash/read/ | [src](../../../core/services/text_clip.py#L53) |
| function | `clip_words` | `(value, *, max_words)` | Klip til et antal ORD (ikke tegn) — når ord er den meningsfulde enhed. Self-safe. | [src](../../../core/services/text_clip.py#L88) |

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
| function | `record_message` | `(*, role, content, partner_id=…, session_id=…, message_id=…)` | Extract factual sentences from a message and record each one. | [src](../../../core/services/theory_of_mind.py#L235) |
| function | `recent_facts` | `(*, partner_id=…, origin=…, hours=…, limit=…)` | — | [src](../../../core/services/theory_of_mind.py#L272) |
| function | `has_been_told` | `(fact_text, *, partner_id=…, hours=…)` | Has Jarvis told partner this fact within the time window? | [src](../../../core/services/theory_of_mind.py#L298) |
| function | `repetition_warnings` | `(*, partner_id=…, hours=…, threshold=…)` | Facts Jarvis has repeated to partner at or above threshold within window. | [src](../../../core/services/theory_of_mind.py#L323) |
| function | `communication_ledger_section` | `(*, partner_id=…)` | Quiet by default. Surfaces only when Jarvis is repeating himself. | [src](../../../core/services/theory_of_mind.py#L349) |
| function | `_listener_loop` | `()` | Poll events table for channel.chat_message_appended events. | [src](../../../core/services/theory_of_mind.py#L376) |
| function | `start_theory_of_mind_tracker` | `()` | Start the DB-polling listener. Idempotent. | [src](../../../core/services/theory_of_mind.py#L440) |
| function | `stop_theory_of_mind_tracker` | `()` | — | [src](../../../core/services/theory_of_mind.py#L457) |

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
| function | `tick_thought_stream_daemon` | `(energy_level=…, inner_voice_mode=…)` | — | [src](../../../core/services/thought_stream_daemon.py#L28) |
| function | `_gather_concrete_priors` | `()` | Pull a few specific recent things so the fragment has material to drift | [src](../../../core/services/thought_stream_daemon.py#L61) |
| function | `_generate_fragment` | `(energy_level, previous_fragment, inner_voice_mode=…)` | — | [src](../../../core/services/thought_stream_daemon.py#L96) |
| function | `_store_fragment` | `(fragment)` | — | [src](../../../core/services/thought_stream_daemon.py#L134) |
| function | `get_latest_thought_fragment` | `()` | — | [src](../../../core/services/thought_stream_daemon.py#L167) |
| function | `inject_rediscovery_fragment` | `(summary)` | Inject a re-discovered memory as a thought fragment. | [src](../../../core/services/thought_stream_daemon.py#L171) |
| function | `build_thought_stream_surface` | `()` | — | [src](../../../core/services/thought_stream_daemon.py#L181) |

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

## `core/services/tiktok_content_daemon.py`
_TikTok content daemon — autonomous 3x/day video generation and upload._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tiktok_setting` | `(key, fallback=…)` | Load a TikTok setting from runtime config. | [src](../../../core/services/tiktok_content_daemon.py#L83) |
| function | `tick_tiktok_content_daemon` | `()` | Main tick — generate and upload a TikTok video for the current time slot. | [src](../../../core/services/tiktok_content_daemon.py#L138) |
| function | `_detect_slot` | `(hour)` | Return slot name for the given UTC hour, or None if outside windows. | [src](../../../core/services/tiktok_content_daemon.py#L292) |
| function | `_generate_quote` | `(slot)` | Generate a quote/line for the slot via LLM. Returns fallback on failure. | [src](../../../core/services/tiktok_content_daemon.py#L300) |
| function | `_get_source_image` | `(slot)` | Return path to a source image for the slot. | [src](../../../core/services/tiktok_content_daemon.py#L316) |
| function | `_generate_flux_image` | `(slot)` | Generate a high-quality image via pollinations.ai flux model (free API). | [src](../../../core/services/tiktok_content_daemon.py#L339) |
| function | `_generate_sdxl_image` | `(slot)` | Generate a unique image for the slot via ComfyUI SDXL (fallback). | [src](../../../core/services/tiktok_content_daemon.py#L402) |
| function | `_create_solid_image` | `(slot)` | Create a 1080x1920 solid color PNG using PIL. Returns path or None. | [src](../../../core/services/tiktok_content_daemon.py#L437) |
| function | `_do_upload` | `(video_path, title)` | Upload via _exec_tiktok_upload. Returns result dict. | [src](../../../core/services/tiktok_content_daemon.py#L454) |
| function | `_refill_pool` | `(slot_type=…)` | Auto-refill the pool with fresh LLM-generated concepts when running low. | [src](../../../core/services/tiktok_content_daemon.py#L470) |
| function | `_count_unused` | `(pool, slot_type)` | Count how many unused concepts of a given type remain in the pool. | [src](../../../core/services/tiktok_content_daemon.py#L545) |
| function | `_get_concept_from_pool` | `(slot_type)` | Read pool file and return (text, hashtags) for the first unused concept of slot_type. | [src](../../../core/services/tiktok_content_daemon.py#L550) |

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
| function | `tool_result_aging_mode` | `()` | Current aging mode: 'off' | 'shadow' | 'active'. Default 'shadow'. | [src](../../../core/services/tool_result_aging.py#L31) |
| function | `_clear_placeholder` | `(n)` | — | [src](../../../core/services/tool_result_aging.py#L48) |
| function | `_is_already_aged` | `(content)` | — | [src](../../../core/services/tool_result_aging.py#L52) |
| function | `age_tool_results` | `(exchanges, *, keep_full=…, mode, strength, round_index, compress_fn=…)` | Age tool-result content on exchanges older than the ``keep_full`` most recent. | [src](../../../core/services/tool_result_aging.py#L56) |

## `core/services/tool_result_store.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `summarize_result` | `(content, max_length=…)` | — | [src](../../../core/services/tool_result_store.py#L15) |
| function | `save_tool_result` | `(tool_name, arguments, result_content, *, created_at=…)` | — | [src](../../../core/services/tool_result_store.py#L22) |
| function | `get_tool_result` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L47) |
| function | `cleanup_old_results` | `(max_age_days=…)` | — | [src](../../../core/services/tool_result_store.py#L63) |
| function | `build_tool_result_reference` | `(result_id, *, tool_name, summary)` | — | [src](../../../core/services/tool_result_store.py#L80) |
| function | `parse_tool_result_reference` | `(content)` | — | [src](../../../core/services/tool_result_store.py#L92) |
| function | `render_tool_result_for_prompt` | `(content, *, expand, max_chars=…)` | — | [src](../../../core/services/tool_result_store.py#L108) |
| function | `_result_path` | `(result_id)` | — | [src](../../../core/services/tool_result_store.py#L138) |
| function | `_prefixed_tool_text` | `(tool_name, text)` | — | [src](../../../core/services/tool_result_store.py#L142) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/tool_result_store.py#L150) |

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

