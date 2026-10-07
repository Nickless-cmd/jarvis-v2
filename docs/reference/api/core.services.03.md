# `core.services.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/approval_feedback_subscriber.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L19) |
| function | `stop_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L36) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/approval_feedback_subscriber.py#L49) |

## `core/services/approval_outbox.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/approval_outbox.py#L19) |
| function | `ensure_approval_outbox_table` | `(conn)` | — | [src](../../../core/services/approval_outbox.py#L23) |
| function | `enqueue_approval_notification` | `(conn, *, request_id, user_id, envelope)` | — | [src](../../../core/services/approval_outbox.py#L48) |
| function | `pending_approval_notifications` | `(limit=…)` | — | [src](../../../core/services/approval_outbox.py#L68) |
| function | `make_approval_notification_due` | `(request_id)` | — | [src](../../../core/services/approval_outbox.py#L93) |
| function | `dispatch_pending_approval_notifications` | `(*, limit=…, deliver=…)` | — | [src](../../../core/services/approval_outbox.py#L106) |
| function | `_worker` | `()` | — | [src](../../../core/services/approval_outbox.py#L155) |
| function | `start_approval_outbox_dispatcher` | `()` | — | [src](../../../core/services/approval_outbox.py#L164) |

## `core/services/approval_runtime.py`
_Én doer ind og ud af en godkendelse — Fase 4's sidste stykke._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `new_id` | `()` | — | [src](../../../core/services/approval_runtime.py#L41) |
| function | `build_request` | `(*, tool_name, arguments, result, run, created_at=…)` | Byg et gyldigt godkendelses-kort. Det ENE sted formen bor. | [src](../../../core/services/approval_runtime.py#L45) |
| function | `pending_for_session` | `(session_id)` | Det ventende godkendelses-kort for ÉN samtale — eller ``None``. | [src](../../../core/services/approval_runtime.py#L71) |
| function | `pending_for_owner` | `(user_id)` | Det ventende kort for en EJER — uanset hvilken samtale det hører til. | [src](../../../core/services/approval_runtime.py#L104) |
| function | `alle_pending_for_owner` | `(user_id)` | ALLE ventende kort for en EJER — ikke kun det nyeste. | [src](../../../core/services/approval_runtime.py#L137) |
| function | `decide` | `(approval_id, *, approved, answered_by=…)` | Svar paa en godkendelse. Den ENE vej ind for enhver svarer. | [src](../../../core/services/approval_runtime.py#L172) |
| function | `state` | `(approval_id)` | Hvad ved vi om dette kort? None hvis det ikke findes. | [src](../../../core/services/approval_runtime.py#L186) |
| function | `sweep_expired` | `()` | Fjern udloebne kort. Returnerer hvad der blev fejet. | [src](../../../core/services/approval_runtime.py#L208) |

## `core/services/arc_rule_extractor.py`
_Arc rule extractor — turns narrative arcs into actionable rules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rules_path` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L33) |
| function | `_arcs_dir` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L39) |
| function | `_build_extraction_prompt` | `(arc_text, period)` | — | [src](../../../core/services/arc_rule_extractor.py#L43) |
| function | `_parse_rules` | `(text)` | — | [src](../../../core/services/arc_rule_extractor.py#L59) |
| function | `extract_rules_from_arc` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L74) |
| function | `_mark_processed` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L138) |
| function | `_is_processed` | `(arc_name)` | — | [src](../../../core/services/arc_rule_extractor.py#L151) |
| function | `extract_rules_for_unprocessed_arcs` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L161) |
| function | `arc_rules_section` | `(*, max_lines=…)` | Retired 2026-09-04 (memory repair, R4): arc rules reach the prompt only | [src](../../../core/services/arc_rule_extractor.py#L180) |
| function | `_legacy_arc_rules_section` | `(*, max_lines=…)` | Pre-2026-09-04 renderer, kept for reference/tests of the file format. | [src](../../../core/services/arc_rule_extractor.py#L188) |

## `core/services/assembly_load_probe.py`
_Hvad lavede maskinen MENS prompten blev samlet?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_proces_cpu_sek` | `()` | Processens samlede CPU-tid (alle tråde) i sekunder. | [src](../../../core/services/assembly_load_probe.py#L60) |
| function | `start` | `()` | Åbn en måling. Returnerer en uigennemsigtig nøgle til `afslut`. | [src](../../../core/services/assembly_load_probe.py#L79) |
| function | `afslut` | `(start_token)` | Luk målingen og returnér felterne som ÉN streng til log-linjen. | [src](../../../core/services/assembly_load_probe.py#L84) |

## `core/services/assembly_prewarm.py`
_core/services/assembly_prewarm.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_max_created_at_real_deepseek` | `()` | Epoch seconds of the most recent NON-warmer deepseek call in costs. None if none. | [src](../../../core/services/assembly_prewarm.py#L36) |
| function | `_seconds_since_last_real_deepseek_call` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L54) |
| function | `_max_created_at_visible` | `()` | Epoch-sek. for seneste ÆGTE bruger↔Jarvis-aktivitet (visible-lanen). None hvis | [src](../../../core/services/assembly_prewarm.py#L59) |
| function | `_seconds_since_last_user_activity` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L76) |
| function | `_idle_window_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L85) |
| function | `is_prewarm_active` | `()` | True hvis den aktuelle tråd i øjeblikket kører en pre-warm-build. Self-safe. | [src](../../../core/services/assembly_prewarm.py#L109) |
| function | `assembly_prewarm_enabled` | `()` | Kill-switch. Default OFF (shadow) — flip via runtime-state. Self-safe → False. | [src](../../../core/services/assembly_prewarm.py#L114) |
| function | `_interval_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L124) |
| function | `_skip_if_recent_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L138) |
| function | `_seconds_since_last_prewarm` | `()` | Cross-process: seconds since ANY process last prewarmed. None if never. | [src](../../../core/services/assembly_prewarm.py#L147) |
| function | `_mark_prewarmed` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L157) |
| function | `_should_prewarm` | `()` | Event-drevet gate (15. jul — dræber 292M-tokens/13d-burnet). Warm KUN når det | [src](../../../core/services/assembly_prewarm.py#L165) |
| function | `_try_acquire_prewarm_lease` | `(interval_s)` | Atomisk cross-process: kun ÉN proces vinder retten til at warme pr. interval. | [src](../../../core/services/assembly_prewarm.py#L186) |
| function | `_record_stats` | `(elapsed_s, error=…)` | — | [src](../../../core/services/assembly_prewarm.py#L205) |
| function | `prewarm_once` | `()` | Byg én throwaway-assembly for at varme alle sektions-caches. Returnerer | [src](../../../core/services/assembly_prewarm.py#L220) |
| function | `_loop` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L250) |
| function | `start_prewarm_loop` | `()` | Start baggrunds-pre-warm-loopet én gang pr. proces. Idempotent. Loopet kører | [src](../../../core/services/assembly_prewarm.py#L266) |

## `core/services/associative_recall.py`
_Associative Recall — dormant memories triggered by context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_strong_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L47) |
| function | `_get_weak_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L55) |
| function | `_get_max_active` | `()` | — | [src](../../../core/services/associative_recall.py#L63) |
| function | `_get_repetition_multiplier` | `()` | — | [src](../../../core/services/associative_recall.py#L71) |
| function | `_ensure_active_memories_table` | `()` | Create recall_active_memories table if it doesn't exist (lazy init). | [src](../../../core/services/associative_recall.py#L83) |
| function | `_persist_active_memory` | `(memory)` | Save an active memory to DB (upsert). | [src](../../../core/services/associative_recall.py#L108) |
| function | `_remove_persisted_memory` | `(memory_id)` | Remove a memory from the DB persistence table. | [src](../../../core/services/associative_recall.py#L133) |
| function | `_load_active_memories_from_db` | `()` | Restore active memories from DB on module load. | [src](../../../core/services/associative_recall.py#L148) |
| function | `_clear_persisted_memories` | `()` | Remove all active memories from DB. | [src](../../../core/services/associative_recall.py#L177) |
| function | `recall_for_session` | `(session_context)` | Run associative recall at session start. Populates up to 3 active memories. | [src](../../../core/services/associative_recall.py#L196) |
| function | `_observe_assoc_recall` | `(memories)` | Fase 3 (§23.3 #4): meld recall-KVALITET til Centralen — KUN scalar-metadata, aldrig | [src](../../../core/services/associative_recall.py#L252) |
| function | `recall_for_message` | `(message_text, emotional_state)` | Run associative recall for a user message. Adds up to 2 active memories. | [src](../../../core/services/associative_recall.py#L282) |
| function | `build_recall_prompt_section` | `()` | Format active memories as [ASSOCIATIONER] awareness section (Danish, compact). | [src](../../../core/services/associative_recall.py#L369) |
| function | `apply_weak_recall_to_emotions` | `(memories)` | Trigger emotion concepts from weak-scoring memories. | [src](../../../core/services/associative_recall.py#L391) |
| function | `clear_session_recall` | `()` | Reset all active memories and topic history. Call at session end. | [src](../../../core/services/associative_recall.py#L422) |
| function | `_add_to_active` | `(memory)` | Add memory to active set. Evicts weakest if at cap. Persists to DB. | [src](../../../core/services/associative_recall.py#L435) |
| function | `_record_topic` | `(topic)` | Record a topic in the sliding window history. | [src](../../../core/services/associative_recall.py#L449) |
| function | `_get_topic_multiplier` | `(topic)` | Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0. | [src](../../../core/services/associative_recall.py#L454) |
| function | `_extract_keywords_llm` | `(text)` | Extract keywords via cheap-lane LLM. Returns empty list on failure. | [src](../../../core/services/associative_recall.py#L467) |
| function | `_extract_keywords_regex` | `(text)` | Regex fallback: capitalized words, technical terms, named entities. | [src](../../../core/services/associative_recall.py#L492) |
| function | `_extract_topic_hint` | `(text)` | Extract topic hints: LLM first, regex fallback, then simple fallback. | [src](../../../core/services/associative_recall.py#L522) |
| function | `_add_private_brain_candidates` | `(candidates, topic_hint, limit=…)` | Add private brain records as recall candidates. | [src](../../../core/services/associative_recall.py#L565) |
| function | `_add_sensory_candidates` | `(candidates, topic_hint, limit=…)` | Add recent sensory memories as recall candidates. | [src](../../../core/services/associative_recall.py#L597) |
| function | `_build_session_context_text` | `(session_context)` | Build a context description string for session-level scoring. | [src](../../../core/services/associative_recall.py#L629) |
| function | `build_associative_recall_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/associative_recall.py#L641) |
| function | `tick_associative_recall` | `()` | Heartbeat daemon tick — decay + periodic candidate scan. | [src](../../../core/services/associative_recall.py#L664) |

## `core/services/attachment_blocks.py`
_Vedhæftninger som blokke på brugerens besked._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_attachment_blocks` | `(metas)` | Lav content_json-blokke for en brugerbeskeds vedhæftninger. | [src](../../../core/services/attachment_blocks.py#L30) |
| function | `user_message_content_json` | `(metas)` | Serialisér blokkene til det felt `append_chat_message` tager. | [src](../../../core/services/attachment_blocks.py#L59) |
| function | `image_ids_on_message` | `(content_json)` | attachment_id'er for BILLEDER i en besked. Tom liste ved alt andet. | [src](../../../core/services/attachment_blocks.py#L88) |
| function | `image_content_blocks` | `(content_json, *, limit=…)` | `image_url`-blokke klar til prompten. Tom liste hvis intet kan læses. | [src](../../../core/services/attachment_blocks.py#L104) |

## `core/services/attachment_service.py`
_attachment_service — download, store, and read channel attachments._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_allowed_send_roots` | `()` | Rødder et fil-svar må sendes fra — beregnet ved KALD, ikke ved import. | [src](../../../core/services/attachment_service.py#L30) |
| function | `_http_download` | `(url, headers)` | — | [src](../../../core/services/attachment_service.py#L66) |
| function | `_db_store` | `(*, attachment_id, session_id, channel_type, filename, mime_type, size_bytes, local_path, source_url)` | — | [src](../../../core/services/attachment_service.py#L75) |
| function | `_db_get` | `(attachment_id)` | — | [src](../../../core/services/attachment_service.py#L107) |
| function | `_db_list` | `(session_id, limit)` | — | [src](../../../core/services/attachment_service.py#L118) |
| function | `list_image_attachments` | `(*, user_id=…, limit=…, session_id=…)` | List billed-attachments til galleriet (#6). | [src](../../../core/services/attachment_service.py#L129) |
| function | `_send_generated_to_channel` | `(session_id, local_path)` | Send et NYLIGT genereret billede til den kanal sessionen hører til. | [src](../../../core/services/attachment_service.py#L188) |
| function | `register_generated_media` | `(*, local_path, mime_type=…, source_url=…, session_id=…)` | Gør en fil Jarvis LAVEDE synlig — returnerer attachment_id, ellers "". | [src](../../../core/services/attachment_service.py#L232) |
| function | `register_generated_image` | `(*, local_path, mime_type=…, source_url=…, session_id=…)` | Bagudkompatibelt navn. Se :func:`register_generated_media`. | [src](../../../core/services/attachment_service.py#L299) |
| function | `attachment_visible_to_user` | `(attachment_id, user_id)` | Privacy-cluster GENNEM Centralen (observe): cross-user attachment-adgangs-beslutning | [src](../../../core/services/attachment_service.py#L310) |
| function | `_attachment_visible_to_user_impl` | `(attachment_id, user_id)` | Må denne bruger se attachment'et? user_id tom → ja (owner/legacy). | [src](../../../core/services/attachment_service.py#L326) |
| function | `_call_vision` | `(image_b64, *, model, prompt=…)` | Send billedet til den VALGTE vision-backend. | [src](../../../core/services/attachment_service.py#L350) |
| function | `_vision_model` | `()` | — | [src](../../../core/services/attachment_service.py#L374) |
| function | `download_and_store` | `(*, url, filename, mime_type, size_bytes, session_id, channel_type, http_headers=…)` | Download file from URL and persist to uploads/ + DB. | [src](../../../core/services/attachment_service.py#L396) |
| function | `resolve_attachment_id` | `(vaerdi)` | Oversæt det brugeren SKREV til et rigtigt `attachment_id`. | [src](../../../core/services/attachment_service.py#L461) |
| function | `get_attachment` | `(attachment_id)` | Return attachment metadata dict, or None if not found. | [src](../../../core/services/attachment_service.py#L519) |
| function | `list_attachments` | `(session_id, limit=…)` | Return recent attachments for session, newest first. | [src](../../../core/services/attachment_service.py#L527) |
| function | `image_data_url` | `(attachment_id)` | `data:`-URL til et billede — modellens EGNE øjne (2026-09-06). | [src](../../../core/services/attachment_service.py#L538) |
| function | `read_attachment_content` | `(attachment_id, question=…)` | Read attachment content for Jarvis. | [src](../../../core/services/attachment_service.py#L564) |
| function | `validate_send_path` | `(path)` | Return (ok, error_message) for outbound file send. | [src](../../../core/services/attachment_service.py#L662) |

## `core/services/attachment_topology_signal_tracking.py`
_Attachment-topology signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_attachment_topology_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L44) |
| function | `refresh_runtime_attachment_topology_signal_statuses` | `()` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L81) |
| function | `build_runtime_attachment_topology_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L85) |
| function | `_extract_attachment_topology_candidates` | `(*, run_id)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L89) |
| function | `_build_candidate` | `(*, domain_key, relation_continuity, meaning, witness, chronicle_brief, metabolism, self_narrative, temperament, forgetting_candidate)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L181) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L283) |
| function | `_attachment_topology_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L305) |
| function | `_derive_attachment_weight` | `(*, relation_weight, meaning_weight, witness_status, witness_persistence, brief_weight, metabolism_weight, narrative_weight, temperament_weight, forgetting_state)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L327) |
| function | `_derive_attachment_state` | `(*, weight, witness_status, metabolism_state)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L363) |
| function | `_attachment_summary` | `(*, focus, attachment_state, attachment_weight, forgetting_candidate)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L371) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L399) |
| function | `_humanize_focus` | `(value)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L406) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L411) |
| function | `_find_support_value` | `(summary, key, default=…)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L431) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/attachment_topology_signal_tracking.py#L443) |

## `core/services/attention_blink_test.py`
_Attention Blink Test — capacity-limit measurement (Experiment 5: Serial consciousness)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_attention_blink_test_if_due` | `()` | Check cadence gate and launch test in background thread if due. | [src](../../../core/services/attention_blink_test.py#L33) |
| function | `build_attention_profile_surface` | `()` | MC surface for attention blink experiment. | [src](../../../core/services/attention_blink_test.py#L52) |
| function | `_run_test_body` | `()` | Full test: measure T1, inject T1 burst, wait 30s, inject T2, compare. | [src](../../../core/services/attention_blink_test.py#L87) |
| function | `_compute_blink_ratio` | `(t1, t2)` | T2 total intensity / T1 total intensity. Clamped 0-2. | [src](../../../core/services/attention_blink_test.py#L142) |
| function | `_interpret_blink_ratio` | `(ratio)` | < 0.7 → serial/blink-prone, >= 0.7 → parallel/blink-resistant. | [src](../../../core/services/attention_blink_test.py#L151) |

## `core/services/attention_budget.py`
_Adaptive attention economy — bounded context budgeting for prompt assembly._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SectionBudget` | `` | Budget for a single prompt section. | [src](../../../core/services/attention_budget.py#L23) |
| class | `AttentionBudget` | `` | Complete attention budget for a prompt assembly path. | [src](../../../core/services/attention_budget.py#L32) |
| function | `get_attention_budget` | `(profile)` | Get a named attention budget profile. | [src](../../../core/services/attention_budget.py#L105) |
| class | `SectionResult` | `` | Result of attempting to include a section under budget. | [src](../../../core/services/attention_budget.py#L115) |
| class | `AttentionTrace` | `` | Observable trace of what was included/omitted and why. | [src](../../../core/services/attention_budget.py#L126) |
| method | `AttentionTrace.included_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L140) |
| method | `AttentionTrace.omitted_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L144) |
| method | `AttentionTrace.trimmed_sections` | `(self)` | — | [src](../../../core/services/attention_budget.py#L148) |
| method | `AttentionTrace.summary` | `(self)` | — | [src](../../../core/services/attention_budget.py#L151) |
| function | `apply_section_budget` | `(*, name, content, budget)` | Apply a section budget to content. | [src](../../../core/services/attention_budget.py#L178) |
| function | `build_micro_cognitive_frame` | `()` | Build a ~150 char micro cognitive frame for compact visible prompts. | [src](../../../core/services/attention_budget.py#L272) |
| function | `select_sections_under_budget` | `(*, budget, sections)` | Select and trim sections to fit within the attention budget. | [src](../../../core/services/attention_budget.py#L316) |
| function | `build_attention_budget_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/attention_budget.py#L398) |

## `core/services/attention_contour.py`
_Attention Contour — shape of attention._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_maal` | `()` | (tråd, rytme) — tomme dicts når kilderne ikke kan læses. | [src](../../../core/services/attention_contour.py#L64) |
| function | `_form` | `(traad, rytme)` | (ord, grundlag) — ordet skal kunne føres tilbage til sit tal. | [src](../../../core/services/attention_contour.py#L81) |
| function | `get_attention_shape` | `()` | Formen lige nu. Samme input giver samme svar — hver gang. | [src](../../../core/services/attention_contour.py#L109) |
| function | `describe_attention` | `()` | — | [src](../../../core/services/attention_contour.py#L114) |
| function | `format_attention_for_prompt` | `()` | — | [src](../../../core/services/attention_contour.py#L118) |
| function | `build_attention_contour_surface` | `()` | — | [src](../../../core/services/attention_contour.py#L122) |

## `core/services/attributed_git_commit.py`
_Execute Git commits with canonical attribution and no staging side effects._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AttributedCommitResult` | `` | Process result plus the resulting commit hash when successful. | [src](../../../core/services/attributed_git_commit.py#L21) |
| function | `_git` | `(repo, *args, timeout, env=…)` | — | [src](../../../core/services/attributed_git_commit.py#L30) |
| function | `_linjer` | `(tekst)` | Beskeden som git gemmer den: uden tomme linjer og hale-mellemrum. | [src](../../../core/services/attributed_git_commit.py#L48) |
| function | `_besked_afveg` | `(root, *, sendt, timeout)` | Staar der i repoet det vi bad om? Tom streng = ingen afvigelse fundet. | [src](../../../core/services/attributed_git_commit.py#L53) |
| function | `_verify_staged_paths` | `(repo, paths, *, timeout)` | — | [src](../../../core/services/attributed_git_commit.py#L97) |
| function | `commit_with_attribution` | `(*, repo, message, attribution, paths=…, author=…, timeout=…, amend=…)` | Commit already-staged content with canonical audit trailers. | [src](../../../core/services/attributed_git_commit.py#L120) |

## `core/services/auth_profile_scan.py`
_Shared scanner for multi-profile provider auth slots._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_account_profile` | `(profile)` | True only for real account profiles (default, account2, account3, …). | [src](../../../core/services/auth_profile_scan.py#L41) |
| function | `clear_cache` | `()` | Drop all cached scan results (test helper / manual invalidation). | [src](../../../core/services/auth_profile_scan.py#L51) |
| function | `_profiles_root` | `()` | Return the auth/profiles directory (honoring JARVIS_CONFIG_DIR). | [src](../../../core/services/auth_profile_scan.py#L56) |
| function | `_is_keyless` | `(provider)` | True if the provider needs no per-profile credentials. | [src](../../../core/services/auth_profile_scan.py#L63) |
| function | `_sort_default_first` | `(profiles)` | — | [src](../../../core/services/auth_profile_scan.py#L83) |
| function | `ready_profiles_for` | `(provider)` | Return profiles with ready credentials for ``provider``. | [src](../../../core/services/auth_profile_scan.py#L88) |

## `core/services/auto_code_review.py`
_Auto code-review heuristic for git-commit proposals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_diff_stats` | `(repo, files)` | Return per-file added/removed line counts for the staged or unstaged diff. | [src](../../../core/services/auto_code_review.py#L36) |
| function | `_scope_for_path` | `(p)` | — | [src](../../../core/services/auto_code_review.py#L72) |
| function | `review_pending_commit` | `(*, repo_root, files, message, rationale)` | — | [src](../../../core/services/auto_code_review.py#L77) |
| function | `review_pending_commit_gated` | `(**kwargs)` | Som review_pending_commit, men GOVERNET af Centralen (COGNITIVE, cluster='commit') | [src](../../../core/services/auto_code_review.py#L168) |

## `core/services/auto_continuation.py`
_Fortsæt automatisk når et synligt run-segment sluttede før opgaven._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Beslutning` | `` | Svaret, med grunden. Grunden er ikke pynt — den skal i loggen, så en | [src](../../../core/services/auto_continuation.py#L62) |
| function | `beslut` | `(*, exit_reason, slaaet_til, autonom, kaede_nr, bruger_skrev_imens, maks_kaede=…)` | Skal denne tur fortsætte af sig selv? | [src](../../../core/services/auto_continuation.py#L70) |
| function | `fortsaettelses_besked` | `(kaede_nr, maks_kaede=…, *, reason=…)` | Teksten Jarvis får. Den siger hvor han er, og at han skal sige til når | [src](../../../core/services/auto_continuation.py#L103) |
| function | `noter_udfald` | `(run_id, exit_reason, session_id=…)` | Noter under BEGGE noegler: runnets eget id og sessionen. | [src](../../../core/services/auto_continuation.py#L140) |
| function | `glem_session_udfald` | `(session_id)` | Glem sessionens udfald — kaldes naar en NY tur starter. | [src](../../../core/services/auto_continuation.py#L167) |
| function | `hent_udfald` | `(run_id, session_id=…)` | Udfaldet for et run — slaa op paa run-id, og fald tilbage paa sessionen. | [src](../../../core/services/auto_continuation.py#L184) |
| function | `kaede_nr` | `(session_id)` | Hvor mange gange er DENNE samtale allerede genoptaget? | [src](../../../core/services/auto_continuation.py#L203) |
| function | `noter_brugerbesked` | `(session_id)` | Brugeren skrev selv. Bruges til at afgøre om han tog over MENS et run | [src](../../../core/services/auto_continuation.py#L231) |
| function | `bruger_skrev_efter` | `(session_id, tidspunkt)` | Har brugeren skrevet efter `tidspunkt`? Så har han taget over, og en | [src](../../../core/services/auto_continuation.py#L246) |

## `core/services/auto_improvement_proposer.py`
_Auto improvement proposer — close the self-improvement loop SAFELY._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_iso` | `(value)` | Parse an ISO-8601 timestamp leniently; None on garbage. | [src](../../../core/services/auto_improvement_proposer.py#L39) |
| function | `_is_safe_target` | `(target)` | Reject only infrastructure-protected modules. Identity files now allowed | [src](../../../core/services/auto_improvement_proposer.py#L58) |
| function | `_check_tick_quality_degraded` | `()` | Returns proposal payload if tick quality is degrading. | [src](../../../core/services/auto_improvement_proposer.py#L69) |
| function | `_check_stale_goals` | `()` | Returns proposal payload if stale goals exist. | [src](../../../core/services/auto_improvement_proposer.py#L101) |
| function | `_check_decision_adherence` | `()` | — | [src](../../../core/services/auto_improvement_proposer.py#L131) |
| function | `_already_disabled_providers` | `()` | Providers der eksplicit er slaaet fra paa provider-niveau. | [src](../../../core/services/auto_improvement_proposer.py#L160) |
| function | `_check_provider_health_chronic` | `()` | If a provider is chronically down (>30 min), propose explicit demotion. | [src](../../../core/services/auto_improvement_proposer.py#L184) |
| function | `generate_improvement_proposals` | `(*, session_id=…)` | Run all checks, file plans for any that fire. | [src](../../../core/services/auto_improvement_proposer.py#L239) |
| function | `_exec_generate_improvement_proposals` | `(args)` | — | [src](../../../core/services/auto_improvement_proposer.py#L302) |

## `core/services/auto_remember_subscriber.py`
_Auto-remember subscriber — closes cross-session memory loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_SkipMemoryShadow` | `` | Sentinel: spring den valgfrie memory_write_policy-shadow over (ingen brugerkontekst). | [src](../../../core/services/auto_remember_subscriber.py#L43) |
| function | `_is_trivial_user_turn` | `(text)` | True hvis user-beskeden er en ren acknowledgment uden nyt indhold. | [src](../../../core/services/auto_remember_subscriber.py#L75) |
| function | `_is_trivial_assistant_turn` | `(text)` | True hvis assistant-svaret er en kort acknowledgment uden indhold. | [src](../../../core/services/auto_remember_subscriber.py#L94) |
| function | `_connect` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L112) |
| function | `_parse_json_loose` | `(text)` | Find første gyldige JSON-objekt i tekst. Robust over for LLM | [src](../../../core/services/auto_remember_subscriber.py#L160) |
| function | `evaluate_turn_for_memory` | `(user_text, assistant_text)` | Spørg cheap LLM: "skal denne tur gemmes?" | [src](../../../core/services/auto_remember_subscriber.py#L191) |
| function | `_find_preceding_user_text` | `(session_id, before_message_id)` | Find seneste user-besked i session FØR den givne assistant-besked. | [src](../../../core/services/auto_remember_subscriber.py#L275) |
| function | `_process_visible_assistant_turn` | `(payload)` | Evaluér én assistant-tur og kald remember_this hvis salient. | [src](../../../core/services/auto_remember_subscriber.py#L309) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — samme pattern som metacognition_signal_tracker. | [src](../../../core/services/auto_remember_subscriber.py#L398) |
| function | `start_auto_remember_subscriber` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/auto_remember_subscriber.py#L440) |
| function | `stop_auto_remember_subscriber` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L457) |

## `core/services/automation_dsl.py`
_Automation DSL — declarative triggers → actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L33) |
| class | `ActionSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L39) |
| class | `AutomationDSL` | `` | — | [src](../../../core/services/automation_dsl.py#L47) |
| class | `AutomationDSLValidationError` | `` | — | [src](../../../core/services/automation_dsl.py#L56) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/automation_dsl.py#L67) |
| function | `_load` | `()` | — | [src](../../../core/services/automation_dsl.py#L71) |
| function | `_save` | `(items)` | — | [src](../../../core/services/automation_dsl.py#L85) |
| function | `validate_automation` | `(raw)` | Validate and construct an AutomationDSL from a raw dict. | [src](../../../core/services/automation_dsl.py#L97) |
| function | `register_automation` | `(dsl)` | Persist an AutomationDSL. Returns automation_id. | [src](../../../core/services/automation_dsl.py#L154) |
| function | `deactivate_automation` | `(automation_id)` | — | [src](../../../core/services/automation_dsl.py#L180) |
| function | `list_automations` | `(*, status=…)` | — | [src](../../../core/services/automation_dsl.py#L190) |
| function | `_expire_due` | `()` | Mark expired automations as inactive. Returns count of newly expired. | [src](../../../core/services/automation_dsl.py#L197) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — expire due automations, no other side-effects here. | [src](../../../core/services/automation_dsl.py#L222) |
| function | `build_automation_dsl_surface` | `()` | — | [src](../../../core/services/automation_dsl.py#L228) |
| function | `_emit_automation_dsl_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/automation_dsl.py#L257) |

## `core/services/autonomous_goals.py`
_Autonomous goals — persistent top-level goals with decomposition._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm_title` | `(title)` | Normalisér til dedup: trim, lowercase, kollaps whitespace, cap 200. | [src](../../../core/services/autonomous_goals.py#L35) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_goals.py#L40) |
| function | `_save` | `(goals)` | — | [src](../../../core/services/autonomous_goals.py#L47) |
| function | `_now` | `()` | — | [src](../../../core/services/autonomous_goals.py#L51) |
| function | `create_goal` | `(*, title, description=…, parent_id=…, priority=…, source=…)` | Create a new goal. Returns the created entry. | [src](../../../core/services/autonomous_goals.py#L55) |
| function | `update_goal_status` | `(goal_id, new_status)` | — | [src](../../../core/services/autonomous_goals.py#L108) |
| function | `list_goals` | `(*, status=…, priority=…, parent_id=…, limit=…)` | List goals matching filters. parent_id='any' = no filter, None = top-level only. | [src](../../../core/services/autonomous_goals.py#L129) |
| function | `decompose_goal` | `(goal_id)` | Use cheap-lane LLM to split a goal into 3-5 concrete sub-goals. | [src](../../../core/services/autonomous_goals.py#L150) |
| function | `goals_prompt_section` | `()` | Awareness section listing active high-priority goals. | [src](../../../core/services/autonomous_goals.py#L214) |
| function | `_exec_goal_create` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L231) |
| function | `_exec_goal_list` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L241) |
| function | `_exec_goal_decompose` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L251) |
| function | `_exec_goal_update_status` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L255) |

## `core/services/autonomous_lease.py`
_visible↔autonomous mutual-exclusion lease (marker-default)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `(now_ts)` | — | [src](../../../core/services/autonomous_lease.py#L37) |
| function | `acquire_visible` | `(ttl_s=…, now_ts=…)` | Visible lane claims the lease for ``ttl_s`` seconds (fail-open). | [src](../../../core/services/autonomous_lease.py#L41) |
| function | `release_visible` | `()` | Visible lane releases the lease (fail-open). | [src](../../../core/services/autonomous_lease.py#L52) |
| function | `visible_active` | `(now_ts=…)` | True if a visible lease is currently held and not expired (fail-open). | [src](../../../core/services/autonomous_lease.py#L60) |
| function | `_read_markers` | `()` | — | [src](../../../core/services/autonomous_lease.py#L75) |
| function | `_write_markers` | `(markers)` | — | [src](../../../core/services/autonomous_lease.py#L85) |
| function | `pending_markers` | `()` | Read (without draining) the deferred autonomous markers. | [src](../../../core/services/autonomous_lease.py#L92) |
| function | `consume_markers` | `()` | Read AND drain the deferred markers (a second call returns empty). | [src](../../../core/services/autonomous_lease.py#L97) |
| function | `try_autonomous_dispatch` | `(payload, now_ts=…, *, scope=…, session_id=…, control_plane=…)` | Gate an autonomous dispatch against the visible lane. | [src](../../../core/services/autonomous_lease.py#L105) |
| function | `_resolve_role` | `(user_id, role)` | Resolve the member role, preferring an explicit ``role``. | [src](../../../core/services/autonomous_lease.py#L149) |
| function | `nudge_allowed_for` | `(marker, *, user_id=…, session_id=…, role=…)` | Role- AND session-gate: may this nudge surface for this user/session? | [src](../../../core/services/autonomous_lease.py#L170) |
| function | `markers_for` | `(*, user_id=…, session_id=…, role=…, drain=…)` | Return the deferred markers this user/session/role is allowed to see. | [src](../../../core/services/autonomous_lease.py#L213) |

## `core/services/autonomous_outreach_daemon.py`
_Autonomous Outreach Daemon — Jarvis reaches out on his own initiative._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L39) |
| function | `_load_log` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L43) |
| function | `_save_log` | `(items)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L57) |
| function | `_last_outreach_sent` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L71) |
| function | `_is_quiet_hours` | `(now_local)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L81) |
| function | `_hours_since_last_user_contact` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L87) |
| function | `_gather_interesting_events` | `()` | Collect potentially noteworthy signals from other services. | [src](../../../core/services/autonomous_outreach_daemon.py#L112) |
| function | `_compose_message` | `(events)` | Build a concrete, value-carrying outreach message from events. | [src](../../../core/services/autonomous_outreach_daemon.py#L177) |
| function | `_highest_priority` | `(events)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L189) |
| function | `_log_decision` | `(*, outcome, reason, events=…, message=…, priority=…, channel=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L196) |
| function | `_owner_uid` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L218) |
| function | `_send_outreach` | `(message, *, priority=…)` | Deliver outreach via the canonical proactive router — device-aware | [src](../../../core/services/autonomous_outreach_daemon.py#L226) |
| function | `attempt_outreach` | `()` | Consider whether to reach out, do so if appropriate. Returns decision dict. | [src](../../../core/services/autonomous_outreach_daemon.py#L252) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — evaluate outreach candidacy. | [src](../../../core/services/autonomous_outreach_daemon.py#L347) |
| function | `recent_log` | `(*, limit=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L356) |
| function | `build_autonomous_outreach_surface` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L360) |
| function | `_surface_summary` | `(sent, skipped, last)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L378) |

## `core/services/autonomous_run_digest.py`
_Referat af en autonom koersel — kort, i hans egen samtale._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_slags_af` | `(session_id)` | — | [src](../../../core/services/autonomous_run_digest.py#L55) |
| function | `_foerste_afsnit` | `(tekst)` | Hans egen konklusion, ikke hele udskriften. | [src](../../../core/services/autonomous_run_digest.py#L63) |
| function | `_pænt_vaerktoej` | `(navn)` | — | [src](../../../core/services/autonomous_run_digest.py#L80) |
| function | `byg_referat` | `(*, session_id, tool_calls=…, output=…, aendrede_filer=…, committet=…)` | Referatet, eller tom streng hvis der ikke er noget at fortaelle. | [src](../../../core/services/autonomous_run_digest.py#L84) |
| function | `post_referat` | `(*, run_id, session_id, tool_calls=…, output=…, aendrede_filer=…, committet=…)` | Skriv referatet i hans sidst aktive samtale. Returnerer session_id ('' = intet skrevet). | [src](../../../core/services/autonomous_run_digest.py#L121) |

## `core/services/autonomous_run_failures.py`
_Fejlede autonome kørsler — set af Jarvis selv, ikke gemt i hans mund._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L45) |
| function | `_kv_get` | `(default)` | — | [src](../../../core/services/autonomous_run_failures.py#L49) |
| function | `_kv_set` | `(value)` | — | [src](../../../core/services/autonomous_run_failures.py#L58) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L66) |
| function | `record_failure` | `(*, run_id, session_id=…, origin=…, provider=…, model=…, detail=…, kind=…)` | Journalisér at en autonom kørsel mislykkedes. Kaster aldrig. | [src](../../../core/services/autonomous_run_failures.py#L76) |
| function | `recent_failures` | `(limit=…)` | Nyeste først. | [src](../../../core/services/autonomous_run_failures.py#L109) |
| function | `_within_window` | `(post, hours)` | — | [src](../../../core/services/autonomous_run_failures.py#L114) |
| function | `request_retry` | `(failure_id)` | Marker at HAN vil forsøge igen. Runtime gør det ikke af sig selv. | [src](../../../core/services/autonomous_run_failures.py#L124) |
| function | `pending_retries` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L137) |
| function | `mark_retried` | `(failure_id)` | — | [src](../../../core/services/autonomous_run_failures.py#L141) |
| function | `clear` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L149) |
| function | `prompt_section` | `()` | Blokken Jarvis ser. Tom streng når der intet er at vide. | [src](../../../core/services/autonomous_run_failures.py#L153) |

## `core/services/autonomous_sessions.py`
_Autonome sessioner — rotér pr. oprindelse+dag, og gør historien synlig._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_origin` | `(origin)` | — | [src](../../../core/services/autonomous_sessions.py#L35) |
| function | `_today` | `()` | — | [src](../../../core/services/autonomous_sessions.py#L40) |
| function | `resolve_autonomous_session` | `(origin)` | Returnér (opret idempotent) sessionen for (oprindelse, i dag). | [src](../../../core/services/autonomous_sessions.py#L44) |
| function | `_origin_of_session` | `(session_id)` | Udled oprindelse fra et ``auto-{origin}-{dato}``-id. | [src](../../../core/services/autonomous_sessions.py#L63) |
| function | `build_autonomous_history_surface` | `(*, days=…, per_origin_limit=…)` | Projicér den autonome historie for owner-visning (§24.4-sikker). | [src](../../../core/services/autonomous_sessions.py#L73) |

## `core/services/autonomous_stream_run.py`
_Server-authoritative streaming lifecycle for autonomous visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_autonomous_stream_run` | `(message, *, session_id, origin=…)` | Start autonomous work and relay its v2 frames through ``run_event_log``. | [src](../../../core/services/autonomous_stream_run.py#L9) |

## `core/services/autonomous_supervisor.py`
_Autonom run-supervision (#3) — Centralen følger HVERT autonomt run, korrelerer det på tværs_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supervise` | `(run_id, outcome, error=…)` | Vurdér ét autonomt run. outcome ∈ {completed, failed, interrupted}. Returnér verdict + | [src](../../../core/services/autonomous_supervisor.py#L23) |

## `core/services/autonomous_work_daemon.py`
_Autonomous Work Daemon — Jarvis works on his own when Bjørn is away._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L48) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L52) |
| function | `_save` | `(items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L66) |
| function | `_proposals_last_hour` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L80) |
| function | `_is_low_activity` | `()` | Low-activity = no visible runs in last _LOW_ACTIVITY_MINUTES. | [src](../../../core/services/autonomous_work_daemon.py#L96) |
| function | `_pending_initiatives` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L117) |
| function | `_log_entry` | `(entry)` | — | [src](../../../core/services/autonomous_work_daemon.py#L125) |
| function | `_file_proposal` | `(*, proposal_type, title, details, rationale)` | Record a work proposal for later execution/approval. | [src](../../../core/services/autonomous_work_daemon.py#L131) |
| function | `_maybe_propose_memory_consolidate` | `()` | Propose a daily memory consolidation when ~end of day locally. | [src](../../../core/services/autonomous_work_daemon.py#L169) |
| function | `_maybe_nudge_incubator` | `()` | If incubator is sparse, nudge creative_instinct to generate. | [src](../../../core/services/autonomous_work_daemon.py#L189) |
| function | `_maybe_propose_research` | `()` | Pick one maturing incubator seed and propose a research topic for it. | [src](../../../core/services/autonomous_work_daemon.py#L213) |
| function | `_plan_once` | `()` | Run planning passes and return list of created proposal_ids. | [src](../../../core/services/autonomous_work_daemon.py#L231) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L253) |
| function | `list_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L268) |
| function | `resolve_proposal` | `(proposal_id, *, outcome, note=…)` | Close a proposal. outcome in {'approved', 'rejected', 'completed'}. | [src](../../../core/services/autonomous_work_daemon.py#L275) |
| function | `build_autonomous_work_surface` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L291) |
| function | `_surface_summary` | `(pending, all_items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L310) |
| function | `build_autonomous_work_prompt_section` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L318) |

## `core/services/autonomy_budget.py`
_Dagligt budget for selvvalgte handlinger + tælling af stilheden (blok E, 4/9)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_get` | `(key, default=…)` | — | [src](../../../core/services/autonomy_budget.py#L41) |
| function | `_state_set` | `(key, value)` | — | [src](../../../core/services/autonomy_budget.py#L50) |
| function | `daily_budget` | `()` | — | [src](../../../core/services/autonomy_budget.py#L58) |
| function | `set_daily_budget` | `(value)` | — | [src](../../../core/services/autonomy_budget.py#L65) |
| function | `_today` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L71) |
| function | `_spent_today` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L75) |
| function | `remaining` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L86) |
| function | `may_act` | `(action=…, *, now=…)` | Er der plads i dagens budget? Fail-open: enhver fejl → ja. | [src](../../../core/services/autonomy_budget.py#L90) |
| function | `note_action` | `(action, *, now=…)` | Registrér en selvvalgt handling. Synlig log, ikke en tavs bremse. | [src](../../../core/services/autonomy_budget.py#L102) |
| function | `note_silence` | `(*, outcome, reason_code=…)` | Han valgte at tie. Tæl det — det er den eneste måde vægten kan vurderes. | [src](../../../core/services/autonomy_budget.py#L122) |
| function | `silence_counts` | `()` | — | [src](../../../core/services/autonomy_budget.py#L135) |
| function | `build_weekly_summary` | `()` | Ugens stilhed i én linje — "" når han ikke har tiet nævneværdigt. | [src](../../../core/services/autonomy_budget.py#L142) |
| function | `run_weekly_review` | `(*, force=…, now=…)` | Ugentligt: læg stilheds-resuméet i den proaktive kø og nulstil tælleren. | [src](../../../core/services/autonomy_budget.py#L161) |
| function | `build_autonomy_budget_surface` | `()` | — | [src](../../../core/services/autonomy_budget.py#L190) |

## `core/services/autonomy_pressure_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_autonomy_pressure_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L60) |
| function | `refresh_runtime_autonomy_pressure_signal_statuses` | `()` | Mark signals as stale based on multiple criteria. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L83) |
| function | `retire_autonomy_pressure_signal` | `(signal_id, *, reason=…)` | Explicitly retire/close an autonomy pressure signal. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L143) |
| function | `build_runtime_autonomy_pressure_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L170) |
| function | `_extract_autonomy_pressure_candidates` | `()` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L213) |
| function | `_persist_autonomy_pressure_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L549) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L613) |
| function | `_candidate` | `(*, pressure_type, pressure_state, weight, confidence, title, summary, rationale, source_anchor, evidence_summary, support_summary, support_count, session_count, status_reason)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L645) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L684) |
| function | `_question_continuity_support` | `(*, relation, meaning, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L693) |
| function | `_initiative_loop_question_support` | `(*, open_loops, initiative, regulation, awareness, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L734) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L826) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L835) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L843) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L855) |

## `core/services/autonomy_proposal_queue.py`
_Autonomy proposal queue — Niveau 2 fundament._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_proposal_executor` | `(kind, fn)` | Register an executor for a proposal kind. | [src](../../../core/services/autonomy_proposal_queue.py#L49) |
| function | `get_registered_proposal_kinds` | `()` | — | [src](../../../core/services/autonomy_proposal_queue.py#L54) |
| function | `file_proposal` | `(*, kind, title, rationale=…, payload=…, created_by=…, session_id=…, run_id=…, tick_id=…, canonical_key=…)` | File a new proposal in the queue. | [src](../../../core/services/autonomy_proposal_queue.py#L58) |
| function | `_notify_discord_proposal` | `(proposal_id, kind, title)` | Send a DM to the owner when a proposal is filed — fire and forget. | [src](../../../core/services/autonomy_proposal_queue.py#L109) |
| function | `list_pending_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L155) |
| function | `list_recent_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L159) |
| function | `approve_proposal` | `(proposal_id, *, resolution_note=…)` | Bjørn approves a proposal — execute it immediately if we have an | [src](../../../core/services/autonomy_proposal_queue.py#L163) |
| function | `reject_proposal` | `(proposal_id, *, resolution_note=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L279) |
| function | `build_autonomy_proposal_surface` | `(*, limit=…)` | MC-friendly view of the proposal queue. | [src](../../../core/services/autonomy_proposal_queue.py#L309) |
| function | `_execute_memory_rewrite_proposal` | `(payload)` | Execute an approved memory-rewrite proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L332) |
| function | `_execute_source_edit_proposal` | `(payload)` | Execute an approved source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L357) |
| function | `_auto_commit_after_source_edit` | `(proposal, result)` | Auto-commit the file changed by a source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L441) |
| function | `_execute_git_commit_proposal` | `(payload)` | Execute an approved git-commit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L532) |
| function | `_execute_instrument_fix_proposal` | `(payload)` | Execute an approved instrument_fix proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L635) |

## `core/services/avoidance_detector.py`
_Avoidance Detector — unbidden self-observation of patterns over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens_from_title` | `(title)` | — | [src](../../../core/services/avoidance_detector.py#L37) |
| function | `_cluster_key` | `(title)` | Pick a short cluster key from the first meaningful keyword(s). | [src](../../../core/services/avoidance_detector.py#L45) |
| function | `_parse_ts` | `(value)` | — | [src](../../../core/services/avoidance_detector.py#L54) |
| function | `_gather_signals` | `()` | Pull goal/dream/focus signals with common shape. | [src](../../../core/services/avoidance_detector.py#L63) |
| function | `detect_avoidances` | `()` | Identify clusters with real prior support that have gone silent. | [src](../../../core/services/avoidance_detector.py#L108) |
| function | `build_avoidance_surface` | `()` | — | [src](../../../core/services/avoidance_detector.py#L161) |
| function | `_surface_summary` | `(findings)` | — | [src](../../../core/services/avoidance_detector.py#L175) |
| function | `build_avoidance_prompt_section` | `()` | Only speaks when there's a real pattern to notice. | [src](../../../core/services/avoidance_detector.py#L185) |

## `core/services/background_job_watch.py`
_Færdige baggrunds-shells — set, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/background_job_watch.py#L76) |
| function | `_laes_tid` | `(vaerdi)` | ISO-tidsstempel fra state eller registry — eller None. | [src](../../../core/services/background_job_watch.py#L80) |
| function | `_grundlinje` | `()` | Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang. | [src](../../../core/services/background_job_watch.py#L94) |
| function | `_rapporterede` | `()` | {noegle: iso-tidsstempel} for det vi allerede har sagt. | [src](../../../core/services/background_job_watch.py#L114) |
| function | `_husk` | `(noegler)` | Skriv noeglerne som rapporterede — atomisk, så api og runtime ikke | [src](../../../core/services/background_job_watch.py#L136) |
| function | `_noegle` | `(job)` | Stabil identitet for et job. | [src](../../../core/services/background_job_watch.py#L153) |
| function | `scan_finished` | `(*, uid)` | Nye fuldførte jobs siden sidst, plus om operator-siden var laesbar. | [src](../../../core/services/background_job_watch.py#L167) |
| function | `_beskriv` | `(job)` | — | [src](../../../core/services/background_job_watch.py#L211) |
| function | `_bruger_id` | `()` | Brugeren der ejer baggrunds-shellene. Tom streng når konteksten ikke | [src](../../../core/services/background_job_watch.py#L222) |
| function | `_sekunder_siden` | `(sidste)` | Sekunder siden forrige tjek — eller None når stemplet mangler eller er | [src](../../../core/services/background_job_watch.py#L237) |
| function | `tik` | `(*, uid=…)` | Tjek for færdige jobs og læg én followup. Kaster aldrig. | [src](../../../core/services/background_job_watch.py#L247) |

## `core/services/background_jobs.py`
_Alle kørende baggrundsopgaver — uanset hvor de kører._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/background_jobs.py#L100) |
| function | `_operator_jobs` | `(uid, exec_fn)` | Baggrunds-shells på operatørens maskine. Tom liste hvis broen tier. | [src](../../../core/services/background_jobs.py#L104) |
| class | `BroTier` | `` | Broen svarede ikke — vi VED ikke hvad der kører på operatørens maskine. | [src](../../../core/services/background_jobs.py#L150) |
| function | `_tal` | `(v)` | — | [src](../../../core/services/background_jobs.py#L154) |
| function | `_sekunder` | `(v)` | Sekunder der kan komme som float. | [src](../../../core/services/background_jobs.py#L161) |
| function | `_supervisor_jobs` | `()` | — | [src](../../../core/services/background_jobs.py#L175) |
| function | `_iso_ts` | `(v)` | — | [src](../../../core/services/background_jobs.py#L210) |
| function | `_scout_jobs` | `()` | Scout-agenter der kører — og dem der blev færdige den seneste time. | [src](../../../core/services/background_jobs.py#L217) |
| function | `_tool_jobs` | `()` | Værktøjskald fra et model-run — dem der kører lige nu. | [src](../../../core/services/background_jobs.py#L269) |
| function | `_default_bash_sid` | `()` | Id'et på den DELTE shell som det almindelige `bash`-værktøj bruger. | [src](../../../core/services/background_jobs.py#L391) |
| function | `_shell_kort` | `(sid, *, egen_maskine, idle, cwd=…, arbejds_shell=…, koerer=…, titel=…)` | Ét kort for en åben shell — samme form som de øvrige kilder. | [src](../../../core/services/background_jobs.py#L414) |
| function | `_lokale_shell_sessioner` | `()` | Åbne `bash_session`-shells — KUN hvis daemonen allerede kører. | [src](../../../core/services/background_jobs.py#L470) |
| function | `_operator_shell_sessioner` | `()` | Åbne `operator_bash_session`-shells på Bjørns maskine. | [src](../../../core/services/background_jobs.py#L531) |
| function | `_shell_sessioner` | `()` | Begge slags åbne shells. Den ene kilde må ikke kunne tie den anden. | [src](../../../core/services/background_jobs.py#L562) |
| function | `liste` | `(*, uid=…, exec_fn=…, kun_aktive=…)` | Alle jobs fra alle kilder. | [src](../../../core/services/background_jobs.py#L575) |
| function | `_skal_vises` | `(job)` | Kører den, eller gik den galt? | [src](../../../core/services/background_jobs.py#L613) |

## `core/services/background_resume.py`
_Turen maa ikke slutte mens en baggrunds-shell stadig producerer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/background_resume.py#L43) |
| function | `_save` | `(state)` | — | [src](../../../core/services/background_resume.py#L52) |
| function | `note_started` | `(session_id, shell_id)` | Husk at DENNE session har startet den shell. Self-safe. | [src](../../../core/services/background_resume.py#L60) |
| function | `forget_session` | `(session_id)` | Ryd op naar en session er faerdig, saa staten ikke vokser uendeligt. | [src](../../../core/services/background_resume.py#L75) |
| function | `tracked` | `(session_id)` | — | [src](../../../core/services/background_resume.py#L85) |
| function | `build_note` | `(deltas)` | Systemnoten der faar Jarvis til at forholde sig til det nye output. Ren. | [src](../../../core/services/background_resume.py#L89) |
| function | `_sig_til_hvis_lang` | `(shell, sidste_output)` | Push besked hvis shellen koerte >= 30 s. Self-safe: fejl → tavshed. | [src](../../../core/services/background_resume.py#L116) |
| function | `poll_async` | `(session_id, user_id)` | Er der nyt fra sessionens baggrunds-shells? Returnerer en note, ellers "". | [src](../../../core/services/background_resume.py#L137) |

## `core/services/baggrundsjob_vagt.py`
_Et faerdigt baggrundsjob melder sig selv — i inboxen, eller med en vaekning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu_iso` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L62) |
| function | `_hent_state` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L66) |
| function | `_gem_state` | `(state)` | — | [src](../../../core/services/baggrundsjob_vagt.py#L78) |
| function | `_bro` | `(navn, args)` | Bro-kald til operatoerens maskine. Egen funktion, saa testen har en soem. | [src](../../../core/services/baggrundsjob_vagt.py#L88) |
| function | `_ejer_uid` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L94) |
| function | `_varighed` | `(sekunder)` | — | [src](../../../core/services/baggrundsjob_vagt.py#L102) |
| function | `beskedtekst` | `(job)` | Én linje der kan staa alene i en inbox. Udfaldet FOERST — det er det der | [src](../../../core/services/baggrundsjob_vagt.py#L116) |
| function | `_meld` | `(job)` | Levér meldingen. Returnerer (leveret, hvordan). | [src](../../../core/services/baggrundsjob_vagt.py#L138) |
| function | `tick_baggrundsjob_vagt` | `(*, trigger=…, last_visible_at=…)` | Kadence-producer: meld hvert nyligt afsluttet baggrundsjob ÉN gang. | [src](../../../core/services/baggrundsjob_vagt.py#L182) |

## `core/services/bash_sandbox.py`
_bwrap-indespærring om én bash-kommando. SLUKKET som standard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_conda_rod` | `(sti)` | Base-installationen bag et conda-env: `<rod>/envs/<navn>` → `<rod>`. | [src](../../../core/services/bash_sandbox.py#L65) |
| function | `_python_roedder` | `()` | Tolkens EGEN rod — oploest gennem symlinks. | [src](../../../core/services/bash_sandbox.py#L77) |
| function | `_runtime_hjem` | `()` | Jarvis' runtime-hjem, hvis det findes. | [src](../../../core/services/bash_sandbox.py#L103) |
| function | `is_available` | `()` | Findes bwrap på DENNE maskine? | [src](../../../core/services/bash_sandbox.py#L122) |
| function | `kan_koere` | `(*, tving=…)` | Kan bwrap FAKTISK starte her? (svar, grund) | [src](../../../core/services/bash_sandbox.py#L138) |
| function | `is_enabled` | `()` | Eksplicit tændt? Usat betyder SLUKKET — modsat central_switches' default. | [src](../../../core/services/bash_sandbox.py#L213) |
| function | `set_enabled` | `(on)` | — | [src](../../../core/services/bash_sandbox.py#L223) |
| function | `status` | `()` | Tilstanden — og «findes» holdes adskilt fra «kører». | [src](../../../core/services/bash_sandbox.py#L230) |
| function | `wrap_bwrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | Byg argv'en. Ren funktion — tjekker hverken flag eller tilgængelighed. | [src](../../../core/services/bash_sandbox.py#L258) |
| function | `maybe_wrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | argv hvis sandboxen er tændt OG mulig her — ellers None (kør normalt). | [src](../../../core/services/bash_sandbox.py#L284) |
| class | `ConfinementUnavailable` | `` | Der blev KRÆVET indespærring, og den kunne ikke leveres. | [src](../../../core/services/bash_sandbox.py#L339) |
| class | `Enforcement` | `` | Hvad der blev bedt om, og hvad der faktisk skete. | [src](../../../core/services/bash_sandbox.py#L344) |
| method | `Enforcement.honored` | `(self)` | Fik vi det vi bad om? | [src](../../../core/services/bash_sandbox.py#L355) |
| method | `Enforcement.as_dict` | `(self)` | — | [src](../../../core/services/bash_sandbox.py#L359) |
| function | `enforcement` | `(command, cwd, *, writable_roots=…, allow_egress=…, require=…)` | Afgør indespærringen OG rapportér den. Kaster kun når `require` er sat. | [src](../../../core/services/bash_sandbox.py#L365) |

## `core/services/behavioral_decisions.py`
_Behavioral decisions — closing the reflection→behavior loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_directive` | `(value)` | — | [src](../../../core/services/behavioral_decisions.py#L36) |
| function | `_commit_observe` | `(outcome, decision_id)` | Commit-cluster instrument: decision_create → central observe (best-effort). | [src](../../../core/services/behavioral_decisions.py#L40) |
| function | `_recently_revoked` | `(normalized)` | En revokeret beslutning med samme direktiv, revokeret for nylig. | [src](../../../core/services/behavioral_decisions.py#L62) |
| function | `_dedup_result` | `(existing, reason, source_type)` | Returnér den række der allerede dækker direktivet — uden at oprette. | [src](../../../core/services/behavioral_decisions.py#L73) |
| function | `create_decision` | `(*, directive, rationale=…, trigger_cue=…, priority=…, source_record_id=…, source_type=…, created_by=…)` | — | [src](../../../core/services/behavioral_decisions.py#L97) |
| function | `review_decision` | `(*, decision_id, verdict, note=…, evidence=…)` | — | [src](../../../core/services/behavioral_decisions.py#L145) |
| function | `update_decision` | `(decision_id, *, directive=…, rationale=…, trigger_cue=…, trigger_name=…, priority=…, status=…)` | Update a decision's mutable fields (None = unchanged, "" = cleared). | [src](../../../core/services/behavioral_decisions.py#L195) |
| function | `change_status` | `(decision_id, new_status)` | — | [src](../../../core/services/behavioral_decisions.py#L236) |
| function | `revoke_decision` | `(decision_id, *, reason=…)` | — | [src](../../../core/services/behavioral_decisions.py#L254) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L272) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L282) |
| function | `get_decision_with_reviews` | `(decision_id, *, review_limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L286) |
| function | `list_active_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L313) |
| function | `list_all_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L317) |
| function | `format_active_decisions_for_heartbeat` | `(*, max_items=…)` | Compact line of top active commitments for heartbeat injection. | [src](../../../core/services/behavioral_decisions.py#L321) |
| function | `get_stats` | `()` | — | [src](../../../core/services/behavioral_decisions.py#L340) |

## `core/services/besked_run_kobling.py`
_Hvilket run skrev denne besked? — så klienten ikke skal gætte ud fra prosa._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_laes` | `()` | — | [src](../../../core/services/besked_run_kobling.py#L84) |
| function | `noter` | `(message_id, run_id)` | Husk at ``run_id`` skrev ``message_id``. Self-safe: kaster aldrig. | [src](../../../core/services/besked_run_kobling.py#L91) |
| function | `run_for` | `(message_id)` | Run'et der skrev beskeden, eller "" hvis vi ikke ved det. | [src](../../../core/services/besked_run_kobling.py#L118) |
| function | `antal` | `()` | Hvor mange koblinger der huskes nu. Til test og diagnostik. | [src](../../../core/services/besked_run_kobling.py#L134) |
| function | `ryd` | `()` | Tøm kortet. Kun til test — ingen produktionsvej rydder det. | [src](../../../core/services/besked_run_kobling.py#L142) |

