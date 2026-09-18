# `core.services.27` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `list_trusted` | `(user_id, kind=…)` | De mapper brugeren har betroet — nyeste foerst. | [src](../../../core/services/workspace_trust.py#L57) |
| function | `set_trusted` | `(user_id, kind, root, trusted)` | Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand. | [src](../../../core/services/workspace_trust.py#L87) |
| function | `set_trust_context` | `(*, kind, root, trusted)` | — | [src](../../../core/services/workspace_trust.py#L110) |
| function | `clear_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L114) |
| function | `current_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L118) |
| function | `guard_code_write` | `(tool_name)` | Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et | [src](../../../core/services/workspace_trust.py#L122) |

## `core/services/world_facts.py`
_Evidence-bounded world facts and their visible prompt representation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_world_fact` | `(*, canonical_key, statement, status, confidence, source_kind, source_ref=…, observed_at=…, valid_from=…, valid_until=…, contradicts_fact_id=…, supersedes_fact_id=…, evidence_count=…, distinct_source_count=…)` | — | [src](../../../core/services/world_facts.py#L37) |
| function | `list_world_facts` | `(*, status=…, limit=…)` | — | [src](../../../core/services/world_facts.py#L98) |
| function | `build_world_fact_prompt_section` | `(*, limit=…, facts=…)` | — | [src](../../../core/services/world_facts.py#L107) |

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
| function | `_observe_world_model` | `(nerve, *, value=…, meta=…)` | EGRESS-FRI binding til Centralen (§24.4): world-model-livscyklus (prediction lavet, | [src](../../../core/services/world_model_signal_tracking.py#L88) |
| function | `record_runtime_world_model_prediction` | `(*, subject, expectation, horizon=…, confidence=…, evidence=…, source=…, now=…)` | Record an explicit, falsifiable world-model expectation. | [src](../../../core/services/world_model_signal_tracking.py#L105) |
| function | `resolve_runtime_world_model_prediction` | `(prediction_id, *, observed, outcome, now=…, resolved_via=…)` | Resolve a prediction with a later observation. | [src](../../../core/services/world_model_signal_tracking.py#L169) |
| function | `build_runtime_world_model_prediction_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L219) |
| function | `track_runtime_world_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L255) |
| function | `refresh_runtime_world_model_signal_statuses` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L295) |
| function | `build_runtime_world_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L324) |
| function | `_extract_pattern_matches` | `(text, patterns)` | Return list of {matched_phrase, context_excerpt} for each regex hit. | [src](../../../core/services/world_model_signal_tracking.py#L350) |
| function | `extract_prediction_language` | `(text)` | Find prediction-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L379) |
| function | `extract_resolution_language` | `(text)` | Find resolution-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L384) |
| function | `_loop_enabled` | `()` | World-model-loop kill-switch check. | [src](../../../core/services/world_model_signal_tracking.py#L389) |
| function | `_load_nudges` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L397) |
| function | `_save_nudges` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L407) |
| function | `record_prediction_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt)` | Append a prediction-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L411) |
| function | `record_resolution_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id=…)` | Append a resolution-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L438) |
| function | `_next_weekday` | `(d, target_weekday)` | Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day. | [src](../../../core/services/world_model_signal_tracking.py#L471) |
| function | `_parse_horizon` | `(horizon, created)` | Return the cutoff datetime when horizon would have elapsed. | [src](../../../core/services/world_model_signal_tracking.py#L479) |
| function | `_ttl_sweep_open_predictions` | `(*, now=…)` | Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace. | [src](../../../core/services/world_model_signal_tracking.py#L503) |
| function | `format_world_model_nudges_for_awareness` | `(*, session_id=…)` | Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block. | [src](../../../core/services/world_model_signal_tracking.py#L541) |
| function | `_load_milestones` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L589) |
| function | `_save_milestones` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L596) |
| function | `_resolved_predictions_chrono` | `()` | Return resolved predictions in chronological order (oldest first). | [src](../../../core/services/world_model_signal_tracking.py#L600) |
| function | `_calibration_of` | `(predictions)` | % supported among supported+contradicted; uncertain is excluded. | [src](../../../core/services/world_model_signal_tracking.py#L612) |
| function | `_has_milestone` | `(kind, value=…)` | Check if a milestone of given kind (+ optional value) has been recorded. | [src](../../../core/services/world_model_signal_tracking.py#L621) |
| function | `_append_milestone` | `(kind, value, message, now)` | — | [src](../../../core/services/world_model_signal_tracking.py#L632) |
| function | `_compute_calibration_milestone` | `(*, now=…)` | Compute the latest calibration milestone if any rule fires. | [src](../../../core/services/world_model_signal_tracking.py#L649) |
| function | `format_world_model_milestone_for_awareness` | `()` | Surface one unrendered milestone per call. Returns '' when nothing. | [src](../../../core/services/world_model_signal_tracking.py#L721) |
| function | `_load_predictions` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L737) |
| function | `_save_predictions` | `(predictions)` | — | [src](../../../core/services/world_model_signal_tracking.py#L744) |
| function | `_extract_world_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L748) |
| function | `_project_context_signal` | `(message, *, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L775) |
| function | `_workspace_scope_signal` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L810) |
| function | `_persist_world_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L832) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L905) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/world_model_signal_tracking.py#L949) |
| function | `_matches_project_context` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L970) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L975) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L982) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/world_model_signal_tracking.py#L986) |

