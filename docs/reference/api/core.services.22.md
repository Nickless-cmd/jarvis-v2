# `core.services.22` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/voice_anchor.py`
_Voice anchor — combined static seed + auto-refreshed external exemplars._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_voice_anchor` | `()` | Return concatenated VOICE.md + VOICE_RECENT.md, or empty string. | [src](../../../core/services/voice_anchor.py#L20) |

## `core/services/voice_curator.py`
_Voice curator — refresh VOICE_RECENT.md from EXTERNAL output only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `refresh_voice_recent` | `()` | Rebuild workspace/VOICE_RECENT.md from external output. | [src](../../../core/services/voice_curator.py#L34) |
| function | `_pick_diverse` | `(*, chat, chronicle, journals)` | Pick up to _TARGET_TOTAL exemplars, max _MAX_PER_SOURCE per source. | [src](../../../core/services/voice_curator.py#L65) |
| function | `_format_recent` | `(exemplars)` | Render exemplars as a markdown blob for VOICE_RECENT.md. | [src](../../../core/services/voice_curator.py#L96) |
| function | `_fetch_chat_exemplars` | `(*, limit)` | Pull recent assistant replies from chat_messages (all sessions). | [src](../../../core/services/voice_curator.py#L112) |
| function | `_fetch_chronicle_exemplars` | `(*, limit)` | Pull recent chronicle narratives as voice exemplars. | [src](../../../core/services/voice_curator.py#L149) |
| function | `_fetch_journal_exemplars` | `(*, limit)` | Pull recent journal entry bodies as voice exemplars. | [src](../../../core/services/voice_curator.py#L170) |
| function | `_strip_frontmatter` | `(text)` | Drop a leading `---\n...\n---\n` YAML block if present. | [src](../../../core/services/voice_curator.py#L203) |

## `core/services/voice_daemon.py`
_Voice daemon — runs the Hey Jarvis voice loop as a background thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_voice_enabled` | `()` | Check if voice is enabled via config or env. | [src](../../../core/services/voice_daemon.py#L24) |
| function | `_run_loop` | `()` | Supervisor thread: start worker, restart on crash until stopped. | [src](../../../core/services/voice_daemon.py#L30) |
| function | `start_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L60) |
| function | `stop_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L73) |
| function | `build_voice_daemon_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/voice_daemon.py#L84) |

## `core/services/wakeup_dispatcher.py`
_Wakeup dispatcher — autonomous fire of self-wakeups._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pick_wakeup_run_target` | `(*, channel, record_session, app_resolver, owner_resolver, is_external)` | Beslut hvilken session et wakeup-run skal lande i — med Discord-guard. | [src](../../../core/services/wakeup_dispatcher.py#L33) |
| function | `dispatch_due_wakeups` | `()` | Find newly-fired wakeups, push them out via webchat + heartbeat tick. | [src](../../../core/services/wakeup_dispatcher.py#L64) |
| function | `_exec_dispatch_due_wakeups` | `(args)` | — | [src](../../../core/services/wakeup_dispatcher.py#L185) |

## `core/services/weekly_manifest.py`
_Weekly manifest — Jarvis' running self-reflection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_weekly_manifest_path` | `()` | — | [src](../../../core/services/weekly_manifest.py#L32) |
| function | `_gather_context` | `()` | Pull recent self-state to ground the reflection. | [src](../../../core/services/weekly_manifest.py#L36) |
| function | `_build_prompt` | `(ctx)` | — | [src](../../../core/services/weekly_manifest.py#L58) |
| function | `build_weekly_manifest` | `()` | Generate weekly manifest, write to WEEKLY_MANIFEST.md, return summary. | [src](../../../core/services/weekly_manifest.py#L73) |

## `core/services/witness_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_witness_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L29) |
| function | `refresh_runtime_witness_signal_statuses` | `()` | — | [src](../../../core/services/witness_signal_tracking.py#L51) |
| function | `build_runtime_witness_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/witness_signal_tracking.py#L120) |
| function | `_extract_witness_candidates` | `(*, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L156) |
| function | `_persist_witness_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L254) |
| function | `_build_candidate` | `(*, domain_key, signal_type, title, summary, rationale, status_reason, source_items, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L323) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L456) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L468) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L472) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L477) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L482) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L487) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L496) |
| function | `_latest_self_narrative_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L569) |
| function | `_latest_meaning_significance` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L577) |
| function | `_latest_temperament_tendency` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L585) |
| function | `_latest_relation_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L593) |
| function | `_latest_signal_for_domain` | `(items, *, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L601) |
| function | `_focus_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L618) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L623) |
| function | `_derive_becoming_direction` | `(*, signal_type, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L628) |
| function | `_derive_becoming_weight` | `(*, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L657) |
| function | `_derive_maturation_hint` | `(*, signal_type, self_narrative, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L677) |
| function | `_derive_maturation_state` | `(*, signal_type, status, becoming_direction, becoming_weight, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L698) |
| function | `_derive_maturation_marker` | `(*, maturation_state, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L719) |
| function | `_derive_persistence_state` | `(*, status, becoming_direction, maturation_state, support_count, session_count)` | — | [src](../../../core/services/witness_signal_tracking.py#L739) |
| function | `_derive_persistence_marker` | `(*, persistence_state, maturation_state)` | — | [src](../../../core/services/witness_signal_tracking.py#L760) |
| function | `_becoming_summary` | `(*, domain_title, becoming_direction, becoming_weight, signal_type)` | — | [src](../../../core/services/witness_signal_tracking.py#L780) |
| function | `_maturation_summary` | `(*, domain_title, becoming_direction, maturation_state, maturation_marker)` | — | [src](../../../core/services/witness_signal_tracking.py#L796) |
| function | `_persistence_summary` | `(*, domain_title, persistence_state, persistence_marker, becoming_direction)` | — | [src](../../../core/services/witness_signal_tracking.py#L811) |
| function | `_summary_marker` | `(text, key)` | — | [src](../../../core/services/witness_signal_tracking.py#L826) |
| function | `_last_summary_fragment` | `(text)` | — | [src](../../../core/services/witness_signal_tracking.py#L835) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L841) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/witness_signal_tracking.py#L847) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L860) |
| function | `run_witness_daemon` | `(*, trigger=…, last_visible_at=…)` | Bounded inner witness daemon — produces witness signals without visible turn. | [src](../../../core/services/witness_signal_tracking.py#L884) |
| function | `get_witness_daemon_state` | `()` | Return current witness daemon state for MC observability. | [src](../../../core/services/witness_signal_tracking.py#L1000) |

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
| function | `set_trusted` | `(user_id, kind, root, trusted)` | Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand. | [src](../../../core/services/workspace_trust.py#L57) |
| function | `set_trust_context` | `(*, kind, root, trusted)` | — | [src](../../../core/services/workspace_trust.py#L80) |
| function | `clear_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L84) |
| function | `current_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L88) |
| function | `guard_code_write` | `(tool_name)` | Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et | [src](../../../core/services/workspace_trust.py#L92) |

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
| function | `_observe_world_model` | `(nerve, *, value=…, meta=…)` | EGRESS-FRI binding til Centralen (§24.4): world-model-livscyklus (prediction lavet, | [src](../../../core/services/world_model_signal_tracking.py#L70) |
| function | `record_runtime_world_model_prediction` | `(*, subject, expectation, horizon=…, confidence=…, evidence=…, source=…, now=…)` | Record an explicit, falsifiable world-model expectation. | [src](../../../core/services/world_model_signal_tracking.py#L87) |
| function | `resolve_runtime_world_model_prediction` | `(prediction_id, *, observed, outcome, now=…, resolved_via=…)` | Resolve a prediction with a later observation. | [src](../../../core/services/world_model_signal_tracking.py#L151) |
| function | `build_runtime_world_model_prediction_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L201) |
| function | `track_runtime_world_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L237) |
| function | `refresh_runtime_world_model_signal_statuses` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L277) |
| function | `build_runtime_world_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L306) |
| function | `_extract_pattern_matches` | `(text, patterns)` | Return list of {matched_phrase, context_excerpt} for each regex hit. | [src](../../../core/services/world_model_signal_tracking.py#L332) |
| function | `extract_prediction_language` | `(text)` | Find prediction-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L361) |
| function | `extract_resolution_language` | `(text)` | Find resolution-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L366) |
| function | `_loop_enabled` | `()` | World-model-loop kill-switch check. | [src](../../../core/services/world_model_signal_tracking.py#L371) |
| function | `_load_nudges` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L379) |
| function | `_save_nudges` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L389) |
| function | `record_prediction_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt)` | Append a prediction-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L393) |
| function | `record_resolution_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id=…)` | Append a resolution-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L420) |
| function | `_next_weekday` | `(d, target_weekday)` | Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day. | [src](../../../core/services/world_model_signal_tracking.py#L453) |
| function | `_parse_horizon` | `(horizon, created)` | Return the cutoff datetime when horizon would have elapsed. | [src](../../../core/services/world_model_signal_tracking.py#L461) |
| function | `_ttl_sweep_open_predictions` | `(*, now=…)` | Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace. | [src](../../../core/services/world_model_signal_tracking.py#L485) |
| function | `format_world_model_nudges_for_awareness` | `(*, session_id=…)` | Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block. | [src](../../../core/services/world_model_signal_tracking.py#L523) |
| function | `_load_milestones` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L571) |
| function | `_save_milestones` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L578) |
| function | `_resolved_predictions_chrono` | `()` | Return resolved predictions in chronological order (oldest first). | [src](../../../core/services/world_model_signal_tracking.py#L582) |
| function | `_calibration_of` | `(predictions)` | % supported among supported+contradicted; uncertain is excluded. | [src](../../../core/services/world_model_signal_tracking.py#L594) |
| function | `_has_milestone` | `(kind, value=…)` | Check if a milestone of given kind (+ optional value) has been recorded. | [src](../../../core/services/world_model_signal_tracking.py#L603) |
| function | `_append_milestone` | `(kind, value, message, now)` | — | [src](../../../core/services/world_model_signal_tracking.py#L614) |
| function | `_compute_calibration_milestone` | `(*, now=…)` | Compute the latest calibration milestone if any rule fires. | [src](../../../core/services/world_model_signal_tracking.py#L631) |
| function | `format_world_model_milestone_for_awareness` | `()` | Surface one unrendered milestone per call. Returns '' when nothing. | [src](../../../core/services/world_model_signal_tracking.py#L703) |
| function | `_load_predictions` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L719) |
| function | `_save_predictions` | `(predictions)` | — | [src](../../../core/services/world_model_signal_tracking.py#L726) |
| function | `_extract_world_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L730) |
| function | `_project_context_signal` | `(message, *, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L757) |
| function | `_workspace_scope_signal` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L792) |
| function | `_persist_world_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L814) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L887) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/world_model_signal_tracking.py#L931) |
| function | `_matches_project_context` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L952) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L957) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L964) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/world_model_signal_tracking.py#L968) |

