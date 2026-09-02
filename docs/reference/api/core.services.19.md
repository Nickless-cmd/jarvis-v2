# `core.services.19` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/self_review_cadence_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_cadence_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L22) |
| function | `refresh_runtime_self_review_cadence_signal_statuses` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L64) |
| function | `build_runtime_self_review_cadence_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L95) |
| function | `_extract_self_review_cadence_candidates` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L121) |
| function | `_persist_self_review_cadence_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L177) |
| function | `_build_cadence_snapshots` | `()` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L253) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L273) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L283) |
| function | `_build_cadence_state` | `(*, review_age, outcome_status)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L296) |
| function | `_build_cadence_reason` | `(*, cadence_state, review_type)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L304) |
| function | `_build_status_reason` | `(*, cadence_state)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L312) |
| function | `_build_due_hint` | `(*, cadence_state)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L320) |
| function | `_cadence_state_from_summary` | `(summary)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L328) |
| function | `_self_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L339) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L344) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L349) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_cadence_signal_tracking.py#L359) |

## `core/services/self_review_outcome_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_outcomes_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L29) |
| function | `refresh_runtime_self_review_outcome_statuses` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L51) |
| function | `build_runtime_self_review_outcome_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L82) |
| function | `_extract_self_review_outcome_candidates` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L124) |
| function | `_persist_self_review_outcomes` | `(*, outcomes, session_id, run_id)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L192) |
| function | `_build_outcome_snapshots` | `()` | — | [src](../../../core/services/self_review_outcome_tracking.py#L265) |
| function | `_with_outcome_view` | `(item, outcome)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L325) |
| function | `_with_surface_outcome_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L335) |
| function | `_build_outcome_type` | `(*, item, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L347) |
| function | `_build_short_outcome` | `(*, outcome_type, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L363) |
| function | `_build_status_reason` | `(*, outcome_type)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L375) |
| function | `_build_review_focus` | `(*, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L385) |
| function | `_closure_confidence_from_snapshot` | `(*, snapshot)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L404) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L409) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L418) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L423) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L428) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L433) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L438) |
| function | `_self_review_outcome_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L443) |
| function | `_review_type_from_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L448) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L453) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L458) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_outcome_tracking.py#L468) |

## `core/services/self_review_record_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_records_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_record_tracking.py#L30) |
| function | `refresh_runtime_self_review_record_statuses` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L52) |
| function | `build_runtime_self_review_record_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_record_tracking.py#L83) |
| function | `_extract_self_review_record_candidates` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L111) |
| function | `_persist_self_review_records` | `(*, records, session_id, run_id)` | — | [src](../../../core/services/self_review_record_tracking.py#L182) |
| function | `_build_review_brief_snapshots` | `()` | — | [src](../../../core/services/self_review_record_tracking.py#L256) |
| function | `_with_review_brief` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_record_tracking.py#L328) |
| function | `_build_review_summary` | `(*, title_suffix, snapshot)` | — | [src](../../../core/services/self_review_record_tracking.py#L345) |
| function | `_build_short_reason` | `(*, snapshot, fallback)` | — | [src](../../../core/services/self_review_record_tracking.py#L360) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_record_tracking.py#L370) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L379) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L384) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L389) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L394) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L399) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L404) |
| function | `_self_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L409) |
| function | `_self_review_record_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L414) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_record_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_record_tracking.py#L424) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_record_tracking.py#L434) |

## `core/services/self_review_run_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_runs_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_run_tracking.py#L29) |
| function | `refresh_runtime_self_review_run_statuses` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L51) |
| function | `build_runtime_self_review_run_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_run_tracking.py#L82) |
| function | `_extract_self_review_run_candidates` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L111) |
| function | `_persist_self_review_runs` | `(*, runs, session_id, run_id)` | — | [src](../../../core/services/self_review_run_tracking.py#L177) |
| function | `_build_review_run_snapshots` | `()` | — | [src](../../../core/services/self_review_run_tracking.py#L263) |
| function | `_with_run_view` | `(item, run)` | — | [src](../../../core/services/self_review_run_tracking.py#L323) |
| function | `_with_surface_run_view` | `(item, *, snapshots)` | — | [src](../../../core/services/self_review_run_tracking.py#L336) |
| function | `_run_summary` | `(run)` | — | [src](../../../core/services/self_review_run_tracking.py#L353) |
| function | `_run_support_summary` | `(run)` | — | [src](../../../core/services/self_review_run_tracking.py#L357) |
| function | `_build_review_focus` | `(*, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L365) |
| function | `_build_short_outlook` | `(*, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L384) |
| function | `_build_short_review_note` | `(*, title_suffix, snapshot)` | — | [src](../../../core/services/self_review_run_tracking.py#L394) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/self_review_run_tracking.py#L400) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L409) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L414) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L419) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L424) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L429) |
| function | `_self_review_run_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L434) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_run_tracking.py#L439) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/self_review_run_tracking.py#L444) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/self_review_run_tracking.py#L454) |

## `core/services/self_review_signal_tracking.py`
_Self-review signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_self_review_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/self_review_signal_tracking.py#L41) |
| function | `refresh_runtime_self_review_signal_statuses` | `()` | — | [src](../../../core/services/self_review_signal_tracking.py#L49) |
| function | `build_runtime_self_review_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/self_review_signal_tracking.py#L53) |
| function | `_extract_self_review_candidates` | `(*_args, **_kwargs)` | — | [src](../../../core/services/self_review_signal_tracking.py#L58) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/self_review_signal_tracking.py#L210) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L267) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L272) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L277) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L282) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L287) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L292) |
| function | `_internal_opposition_domain_key` | `(canonical_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L297) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/self_review_signal_tracking.py#L302) |

## `core/services/self_review_unified.py`
_Self-Review Unified — periodisk samlet selv-audit._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/self_review_unified.py#L29) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/self_review_unified.py#L33) |
| function | `_gather_review_inputs` | `()` | Pull signals v2 already has that need to be reflected upon. | [src](../../../core/services/self_review_unified.py#L58) |
| function | `_base_review` | `(inputs)` | Rule-based review as fallback when LLM unavailable. | [src](../../../core/services/self_review_unified.py#L96) |
| function | `_build_review_prompt` | `(inputs)` | — | [src](../../../core/services/self_review_unified.py#L143) |
| function | `_extract_review_json` | `(raw)` | — | [src](../../../core/services/self_review_unified.py#L174) |
| function | `run_self_review` | `(*, period=…)` | Generate and persist a self-review. Returns the review dict. | [src](../../../core/services/self_review_unified.py#L200) |
| function | `maybe_run_self_review` | `(*, min_hours_between=…)` | Run a review if it's been at least N hours since the last. | [src](../../../core/services/self_review_unified.py#L309) |
| function | `list_self_reviews` | `(*, limit=…)` | — | [src](../../../core/services/self_review_unified.py#L330) |
| function | `build_self_review_surface` | `()` | — | [src](../../../core/services/self_review_unified.py#L349) |

## `core/services/self_surprise_detection.py`
_Self-Surprise Detection — "Huh, det havde jeg ikke forventet af mig selv."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_self_surprise` | `(*, actual_outcome, expected_confidence=…, model=…, domain=…, run_id=…)` | Registrér en overraskelse — eller ``None``, hvilket er det normale. | [src](../../../core/services/self_surprise_detection.py#L35) |
| function | `build_self_surprise_surface` | `()` | Overfladen Jarvis faktisk kan se. | [src](../../../core/services/self_surprise_detection.py#L77) |

## `core/services/self_surprise_expectation.py`
_Kalibreret forventning til selv-overraskelse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_outcome` | `(outcome)` | ``'success'`` | ``'failure'`` | ``'indecisive'``. | [src](../../../core/services/self_surprise_expectation.py#L42) |
| function | `_recent_outcomes` | `(model, *, lookback)` | ``(successes, decisive_total)`` fra modellens egne seneste runs. | [src](../../../core/services/self_surprise_expectation.py#L56) |
| function | `expected_success_rate` | `(model, *, lookback=…)` | Empirisk P(succes) for DENNE model, glattet mod en styrke-baseret prior. | [src](../../../core/services/self_surprise_expectation.py#L91) |
| function | `expectation_verdict` | `(expected, outcome_kind)` | ``'positive'`` | ``'negative'`` | ``None`` (død zone / uafgjort udfald). | [src](../../../core/services/self_surprise_expectation.py#L110) |
| function | `is_legacy_degenerate` | `(expected_confidence)` | Sand for de 19.731 rækker fra den defekte detektor. | [src](../../../core/services/self_surprise_expectation.py#L125) |

## `core/services/self_system_code_awareness.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_self_system_code_awareness_surface` | `()` | — | [src](../../../core/services/self_system_code_awareness.py#L16) |
| function | `_default_repo_observation` | `()` | — | [src](../../../core/services/self_system_code_awareness.py#L114) |
| function | `_detect_repo_root` | `(*starts)` | — | [src](../../../core/services/self_system_code_awareness.py#L134) |
| function | `_observe_repo_status` | `(repo_root)` | — | [src](../../../core/services/self_system_code_awareness.py#L147) |
| function | `_derive_concern_state` | `(*, repo_status, local_change_state, upstream_awareness, branch_name)` | — | [src](../../../core/services/self_system_code_awareness.py#L236) |
| function | `_run_read_only_command` | `(args)` | — | [src](../../../core/services/self_system_code_awareness.py#L279) |
| function | `_safe_int` | `(raw)` | — | [src](../../../core/services/self_system_code_awareness.py#L298) |
| function | `_status_xy` | `(line)` | — | [src](../../../core/services/self_system_code_awareness.py#L305) |
| function | `_status_path` | `(line)` | — | [src](../../../core/services/self_system_code_awareness.py#L312) |
| function | `_append_bounded_path` | `(paths, value, *, limit=…)` | — | [src](../../../core/services/self_system_code_awareness.py#L319) |
| function | `_approval_required_mutation_classes` | `(capabilities)` | — | [src](../../../core/services/self_system_code_awareness.py#L326) |
| function | `_emit_self_system_code_awareness_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/self_system_code_awareness.py#L341) |

## `core/services/self_wakeup.py`
_Self-wakeup — Jarvis' equivalent of Claude Code's ScheduleWakeup._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/self_wakeup.py#L48) |
| function | `_save` | `(records)` | — | [src](../../../core/services/self_wakeup.py#L55) |
| function | `schedule_self_wakeup` | `(*, delay_seconds, prompt, reason=…, channel=…, session_id=…)` | Queue a self-wakeup. Returns the wakeup record. | [src](../../../core/services/self_wakeup.py#L59) |
| function | `due_wakeups` | `(*, include_fired_unconsumed=…)` | Return wakeups whose fire_at has passed and not yet consumed. | [src](../../../core/services/self_wakeup.py#L115) |
| function | `mark_wakeup_consumed` | `(wakeup_id)` | Clear a fired wakeup once Jarvis has acted on it. | [src](../../../core/services/self_wakeup.py#L144) |
| function | `cancel_wakeup` | `(wakeup_id)` | Cancel a pending wakeup before it fires. | [src](../../../core/services/self_wakeup.py#L163) |
| function | `list_wakeups` | `(*, status=…, limit=…)` | — | [src](../../../core/services/self_wakeup.py#L181) |
| function | `cleanup_old_wakeups` | `(*, consumed_age_hours=…, cancelled_age_hours=…, stale_fired_age_hours=…)` | Ryd op i gamle consumed/cancelled/stale-fired wakeups. | [src](../../../core/services/self_wakeup.py#L189) |
| function | `tick_wakeup_cleanup` | `()` | Daemon tick — ryd op i gamle wakeups. | [src](../../../core/services/self_wakeup.py#L250) |
| function | `self_wakeup_section` | `()` | Awareness section showing fired-but-not-consumed wakeups. | [src](../../../core/services/self_wakeup.py#L259) |
| function | `_exec_schedule_self_wakeup` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L282) |
| function | `_exec_list_self_wakeups` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L290) |
| function | `_exec_cancel_self_wakeup` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L300) |
| function | `_exec_mark_wakeup_consumed` | `(args)` | — | [src](../../../core/services/self_wakeup.py#L304) |

## `core/services/selfhood_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_selfhood_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L30) |
| function | `refresh_runtime_selfhood_proposal_statuses` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L52) |
| function | `build_runtime_selfhood_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L83) |
| function | `_extract_selfhood_proposals` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L112) |
| function | `_persist_selfhood_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L198) |
| function | `_build_snapshots` | `()` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L272) |
| function | `_snapshot_entry` | `(snapshots, domain_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L283) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L291) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L302) |
| function | `_proposal_type_from_prompt_type` | `(prompt_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L314) |
| function | `_selfhood_target_for_type` | `(proposal_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L324) |
| function | `_proposed_shift_for_type` | `(proposal_type)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L334) |
| function | `_proposal_confidence` | `(*, prompt_confidence, snapshot)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L344) |
| function | `_proposal_reason` | `(*, proposal_type, selfhood_target, proposal_confidence)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L354) |
| function | `_source_anchor` | `(*, item, snapshot)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L364) |
| function | `_proposal_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L372) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L381) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L386) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L391) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L396) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L408) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/selfhood_proposal_tracking.py#L417) |

## `core/services/semantic_indexer.py`
_Semantic indexer — auto-embedding of new memory records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_semantic_indexer` | `()` | — | [src](../../../core/services/semantic_indexer.py#L34) |
| function | `stop_semantic_indexer` | `()` | — | [src](../../../core/services/semantic_indexer.py#L62) |
| function | `_sweeper_loop` | `()` | Every N minutes, run backfill_all to catch new rows without events. | [src](../../../core/services/semantic_indexer.py#L81) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/semantic_indexer.py#L109) |
| function | `_handle_sensory` | `(payload)` | — | [src](../../../core/services/semantic_indexer.py#L140) |
| function | `_handle_private_brain` | `(payload)` | — | [src](../../../core/services/semantic_indexer.py#L160) |
| function | `build_semantic_indexer_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/semantic_indexer.py#L186) |

## `core/services/semantic_memory.py`
_Semantic memory — unified embedding + cosine search across memory surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_source` | `(table, *, resolver, lister)` | Register a source table so backfill + search can map IDs to rows. | [src](../../../core/services/semantic_memory.py#L56) |
| function | `_default_sources_registered` | `()` | Register sensory_memories + private_brain_records if not already. | [src](../../../core/services/semantic_memory.py#L67) |
| function | `_ollama_base_url` | `()` | — | [src](../../../core/services/semantic_memory.py#L98) |
| function | `_tt_embed` | `(label, dur_ms)` | — | [src](../../../core/services/semantic_memory.py#L136) |
| function | `_fastembed_enabled` | `()` | Kill-switch: runtime-key `embed_backend`="ollama" tvinger den gamle HTTP-sti. | [src](../../../core/services/semantic_memory.py#L152) |
| function | `_get_fastembed` | `()` | Lazy singleton. Returnerer TextEmbedding el. None (aldrig raise) → kaldere | [src](../../../core/services/semantic_memory.py#L161) |
| function | `_embed_fastembed` | `(texts)` | Embed hele listen in-process. Returnerer None (ikke en liste) hvis backenden | [src](../../../core/services/semantic_memory.py#L194) |
| function | `_embed_ollama` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L211) |
| function | `_embed_ollama_batch` | `(texts)` | Batch-embed via ollamas /api/embed (ÉT round-trip for hele listen i stedet | [src](../../../core/services/semantic_memory.py#L259) |
| function | `_encode_vector` | `(vec)` | — | [src](../../../core/services/semantic_memory.py#L302) |
| function | `_decode_vector` | `(data)` | — | [src](../../../core/services/semantic_memory.py#L306) |
| function | `_hash_content` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L310) |
| function | `_prepare_text` | `(text)` | — | [src](../../../core/services/semantic_memory.py#L314) |
| function | `index_memory` | `(*, source_table, source_id, content, modality)` | Embed content and upsert. Returns True on success, False if embed fails | [src](../../../core/services/semantic_memory.py#L323) |
| function | `search` | `(query, *, modalities=…, source_tables=…, limit=…, min_score=…)` | Return top-k memories by cosine similarity. | [src](../../../core/services/semantic_memory.py#L358) |
| function | `_extract_content_for_row` | `(table, row)` | Return (content_text, modality) for a raw row from a known table. | [src](../../../core/services/semantic_memory.py#L422) |
| function | `_row_id` | `(table, row)` | — | [src](../../../core/services/semantic_memory.py#L437) |
| function | `backfill_all` | `(*, max_per_table=…)` | Embed every unindexed row across registered source tables. | [src](../../../core/services/semantic_memory.py#L445) |
| function | `_content_hash_unchanged` | `(table, source_id, new_content)` | — | [src](../../../core/services/semantic_memory.py#L520) |
| function | `get_stats` | `()` | — | [src](../../../core/services/semantic_memory.py#L529) |
| function | `build_semantic_memory_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/semantic_memory.py#L542) |

## `core/services/sensory_archive.py`
_Sansernes Arkiv — service layer for sensory memories._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_mood_from_content` | `(content, modality)` | Auto-extract a short Danish mood tone from content using keyword matching. | [src](../../../core/services/sensory_archive.py#L27) |
| function | `_record` | `(modality, content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L97) |
| function | `record_visual` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L148) |
| function | `record_audio` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L157) |
| function | `record_atmosphere` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L166) |
| function | `record_mixed` | `(content, *, mood_tone=…, metadata=…)` | — | [src](../../../core/services/sensory_archive.py#L175) |
| function | `list_recent` | `(*, modality=…, limit=…, offset=…, since=…)` | — | [src](../../../core/services/sensory_archive.py#L184) |
| function | `search` | `(query, *, modality=…, limit=…)` | — | [src](../../../core/services/sensory_archive.py#L196) |
| function | `get` | `(memory_id)` | — | [src](../../../core/services/sensory_archive.py#L205) |
| function | `count` | `(*, modality=…)` | — | [src](../../../core/services/sensory_archive.py#L209) |
| function | `summarize_for_context` | `(limit=…)` | Return a compact summary usable as surface/context injection. | [src](../../../core/services/sensory_archive.py#L213) |

## `core/services/sensory_perception_bridge.py`
_Sensory perception bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_shingle` | `(text, *, n=…)` | Tokenize lowercased text into overlapping n-grams of words. | [src](../../../core/services/sensory_perception_bridge.py#L21) |
| function | `_jaccard` | `(a, b)` | Jaccard similarity between two token sets. Returns 0 if both empty. | [src](../../../core/services/sensory_perception_bridge.py#L29) |
| function | `_mode` | `(values)` | Most common value. On tie, returns the value that appears first in the list. | [src](../../../core/services/sensory_perception_bridge.py#L38) |
| function | `_aggregate_baseline` | `(records)` | Aggregate 1-N records into a single baseline. | [src](../../../core/services/sensory_perception_bridge.py#L50) |
| function | `_parse_iso` | `(ts)` | Parse ISO timestamp; return None if malformed. Treats naive as UTC. | [src](../../../core/services/sensory_perception_bridge.py#L87) |
| function | `_now` | `()` | Indirected for monkey-patching in tests. | [src](../../../core/services/sensory_perception_bridge.py#L100) |
| function | `_recent_baseline` | `(modality, current_record)` | Latest N records of same modality excluding current. | [src](../../../core/services/sensory_perception_bridge.py#L105) |
| function | `_time_of_day_baseline` | `(modality, current_record)` | Records inside ±N hours of current's time-of-day, over last M days. | [src](../../../core/services/sensory_perception_bridge.py#L122) |
| function | `_build_baseline` | `(modality, current_record)` | Modality-aware baseline selection. | [src](../../../core/services/sensory_perception_bridge.py#L165) |
| function | `_metadata_changed` | `(new_md, baseline_md, modality)` | Per-modality metadata change detection. | [src](../../../core/services/sensory_perception_bridge.py#L181) |
| function | `_detect_change` | `(record, baseline, modality)` | Combined heuristic: mood_tone shift OR Jaccard < 0.4 OR metadata shift. | [src](../../../core/services/sensory_perception_bridge.py#L231) |
| function | `_summary_for_change` | `(modality, new_mood, baseline_mood, kind, jaccard)` | Generate a short Danish summary line for the perceptual event. | [src](../../../core/services/sensory_perception_bridge.py#L313) |
| function | `_salience_for_change` | `(change)` | Map change description to salience level (high/medium/normal). | [src](../../../core/services/sensory_perception_bridge.py#L348) |
| function | `_bridge_enabled` | `()` | — | [src](../../../core/services/sensory_perception_bridge.py#L381) |
| function | `_percept` | `(*, source_event_id, source_kind, change_type, salience, summary, observed_at, evidence)` | Build a percept dict in the shape expected by perceptual_event_engine._record_perceptual_event. | [src](../../../core/services/sensory_perception_bridge.py#L389) |
| function | `classify_sensory_change` | `(event)` | Top-level entry. Returns a percept dict if the event represents a meaningful | [src](../../../core/services/sensory_perception_bridge.py#L411) |
| function | `_classify_sensory_change_inner` | `(event)` | — | [src](../../../core/services/sensory_perception_bridge.py#L423) |

## `core/services/session_boot_reconciler.py`
_Boot-reconciler: crash-zombie runs → interrupted, så de genoptages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(payload)` | Fyr central-nerve ``session_persistence`` (cluster runtime). Best-effort, | [src](../../../core/services/session_boot_reconciler.py#L37) |
| function | `reconcile_on_boot` | `(stale_after_s=…)` | Reconcile crash-zombie runs ved opstart. Fail-open. | [src](../../../core/services/session_boot_reconciler.py#L51) |

## `core/services/session_continuity.py`
_Session Continuity — kontinuitet der føles, ikke kun opslås._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/session_continuity.py#L64) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/session_continuity.py#L68) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/session_continuity.py#L81) |
| function | `detect_new_session` | `()` | Return whether current moment should be treated as 'new session'. | [src](../../../core/services/session_continuity.py#L104) |
| function | `_gather_carry_context` | `()` | Collect what Jarvis might be carrying into today. | [src](../../../core/services/session_continuity.py#L152) |
| function | `_build_morning_prompt` | `(carry, minutes_since_last)` | — | [src](../../../core/services/session_continuity.py#L252) |
| function | `generate_morning_thread` | `(*, force=…)` | Generate and persist a morning thread if this is a new session. | [src](../../../core/services/session_continuity.py#L304) |
| function | `get_latest_morning_thread` | `()` | — | [src](../../../core/services/session_continuity.py#L438) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/session_continuity.py#L460) |
| function | `detect_echo_themes` | `(*, lookback_days=…)` | Find recurring themes in recent inner voices + chat messages. | [src](../../../core/services/session_continuity.py#L467) |
| function | `get_echo_signals_for_prompt` | `()` | Return a quiet one-liner of recurring themes for prompt injection. | [src](../../../core/services/session_continuity.py#L532) |
| function | `build_session_continuity_surface` | `()` | — | [src](../../../core/services/session_continuity.py#L560) |

## `core/services/session_distillation.py`
_Session distillation and private brain continuity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_near_duplicate` | `(summary, record_type, recent_records)` | Return True if a record with very similar summary + same type exists | [src](../../../core/services/session_distillation.py#L89) |
| function | `_record_type_to_domain` | `(record_type)` | Map a private brain record_type to its decay domain. | [src](../../../core/services/session_distillation.py#L118) |
| function | `_try_insert_guarded` | `(*, record_type, layer, session_id, run_id, focus, summary, detail, source_signals, confidence, now, recent_records)` | Insert a private brain record if it passes anti-spam guard. | [src](../../../core/services/session_distillation.py#L131) |
| function | `distill_session_carry` | `(*, session_id, run_id)` | Classify runtime evidence into private-brain / workspace-memory / discard. | [src](../../../core/services/session_distillation.py#L171) |
| function | `_analyze_session_for_cognitive_systems` | `(*, session_id, run_id)` | Analyze a completed session for cognitive accumulation systems. | [src](../../../core/services/session_distillation.py#L387) |
| function | `_scrub_continuity_text` | `(text)` | Read-time-rens af LAGRET continuity-tekst (Jarvis-spec 2026-06-23 #2): ældre | [src](../../../core/services/session_distillation.py#L456) |
| function | `build_private_brain_context` | `(*, limit=…)` | Build a bounded read of recent private brain records suitable for | [src](../../../core/services/session_distillation.py#L483) |
| function | `_classify_continuity_mode` | `(excerpts, by_type)` | Classify the semantic intention of a continuity pass. | [src](../../../core/services/session_distillation.py#L550) |
| function | `run_private_brain_continuity` | `(*, trigger=…)` | Lightweight continuity pass for the private brain. | [src](../../../core/services/session_distillation.py#L605) |
| function | `run_private_brain_lifecycle` | `()` | Run a bounded, AGE-based lifecycle pass over private brain records. | [src](../../../core/services/session_distillation.py#L776) |
| function | `build_private_brain_surface` | `(*, limit=…)` | Return the current private brain state for observability. | [src](../../../core/services/session_distillation.py#L858) |
| function | `build_session_distillation_surface` | `(*, limit=…)` | Return recent distillation records for observability. | [src](../../../core/services/session_distillation.py#L879) |
| function | `generate_session_summary` | `(*, session_id, run_id=…, user_message=…, assistant_response=…)` | Generate and store a compact conversation summary for the given session. | [src](../../../core/services/session_distillation.py#L899) |
| function | `build_previous_session_summaries` | `(*, limit=…)` | Build a text block with recent session summaries for prompt injection. | [src](../../../core/services/session_distillation.py#L990) |

## `core/services/session_inbox.py`
_Session inbox — gates daemon notifications during active sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/session_inbox.py#L59) |
| function | `_connect` | `()` | — | [src](../../../core/services/session_inbox.py#L78) |
| function | `is_session_active` | `(session_id, *, window_seconds=…)` | Has this session seen chat-stream activity recently? | [src](../../../core/services/session_inbox.py#L88) |
| function | `enqueue` | `(*, session_id, content, source, urgent=…)` | Add a daemon notification to the inbox for later delivery. | [src](../../../core/services/session_inbox.py#L122) |
| function | `pending_for_session` | `(session_id)` | List items still queued for delivery in this session. | [src](../../../core/services/session_inbox.py#L153) |
| function | `flush_session` | `(session_id)` | Deliver all queued items for a session. Each becomes an actual | [src](../../../core/services/session_inbox.py#L171) |
| function | `pending_count` | `(session_id=…)` | — | [src](../../../core/services/session_inbox.py#L237) |
| function | `_listener_loop` | `()` | Background flusher. | [src](../../../core/services/session_inbox.py#L262) |
| function | `start_session_inbox` | `()` | Start the DB-polling flusher. Idempotent. | [src](../../../core/services/session_inbox.py#L346) |
| function | `stop_session_inbox` | `()` | — | [src](../../../core/services/session_inbox.py#L363) |

## `core/services/session_milestones.py`
_Session-milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_turns` | `(session_id)` | [(message_id, text)] for user-beskederne i kronologisk orden. Self-safe → []. | [src](../../../core/services/session_milestones.py#L27) |
| function | `_short_title` | `(text, n=…)` | — | [src](../../../core/services/session_milestones.py#L50) |
| function | `_per_turn_milestones` | `(turns)` | — | [src](../../../core/services/session_milestones.py#L55) |
| function | `_llm_segment` | `(turns)` | Bed den billige lane segmentere samtalen i kapitler. Returnerer milepæle eller None. | [src](../../../core/services/session_milestones.py#L59) |
| function | `_generate` | `(turns)` | — | [src](../../../core/services/session_milestones.py#L104) |
| function | `get_session_milestones` | `(session_id)` | Milepæle for rail'en: [{anchor_id, title}]. Cached pr. session+turn-antal; regenereres | [src](../../../core/services/session_milestones.py#L110) |

## `core/services/session_persistence_flag.py`
_Governed kill-switch for session-persistence boot-reconciler. Default OFF (shadow)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_flag` | `()` | Læs rå flag-værdi fra runtime-state. None = usat. | [src](../../../core/services/session_persistence_flag.py#L18) |
| function | `session_persistence_enabled` | `()` | True KUN når eksplicit slået til ('on'/'1'/'true'/'yes'). Usat eller | [src](../../../core/services/session_persistence_flag.py#L24) |

## `core/services/session_prewarm.py`
_Session-aware DeepSeek prefix cache warming (prewarm-on-return)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `session_prewarm_enabled` | `()` | Kill-switch via runtime-state (default True). Self-safe. | [src](../../../core/services/session_prewarm.py#L45) |
| function | `_should_warm` | `(session_id)` | Throttle pr. session: skip hvis varmet < _COOLDOWN_S siden. | [src](../../../core/services/session_prewarm.py#L55) |
| function | `_deepseek_key` | `()` | — | [src](../../../core/services/session_prewarm.py#L70) |
| function | `_post_deepseek` | `(api_key, payload, *, timeout_s=…)` | Minimal POST til deepseek /chat/completions. Returnerer body-dict eller None. | [src](../../../core/services/session_prewarm.py#L79) |
| function | `warm_session_prefix` | `(session_id, *, provider=…, model=…, user_id=…, role=…, workspace_name=…, force=…)` | Varm en sessions [system][historik]-prefix i DeepSeeks disk-cache. | [src](../../../core/services/session_prewarm.py#L98) |
| function | `warm_session_prefix_async` | `(session_id, **kwargs)` | Fire-and-forget: kør warm_session_prefix i en daemon-tråd. Blokerer aldrig | [src](../../../core/services/session_prewarm.py#L241) |

## `core/services/session_topic_tracker.py`
_Session topic tracker — real-time topic extraction and accumulation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_topics_from_text` | `(text)` | Extract candidate topic labels from a user message. | [src](../../../core/services/session_topic_tracker.py#L94) |
| function | `_increment_turn` | `(session_id)` | Increment turn counter for session. Returns new count. | [src](../../../core/services/session_topic_tracker.py#L175) |
| function | `_should_extract` | `(session_id)` | Return True if it's time to extract topics for this session. | [src](../../../core/services/session_topic_tracker.py#L181) |
| function | `_accumulate_topics` | `(session_id, topics)` | Merge extracted topics into the session's topic store. | [src](../../../core/services/session_topic_tracker.py#L187) |
| function | `track_session_topics` | `(session_id, run_id, user_message)` | Call this after every visible user turn. | [src](../../../core/services/session_topic_tracker.py#L207) |
| function | `_persist_session_topics` | `(session_id)` | Write current in-memory topics to the session_topics DB table. | [src](../../../core/services/session_topic_tracker.py#L241) |
| function | `load_session_topics` | `(session_id)` | Load topics for a session from DB, merging with in-memory state. | [src](../../../core/services/session_topic_tracker.py#L262) |
| function | `_format_topics_for_prompt` | `(store, max_topics=…)` | Format topics sorted by mention count descending. | [src](../../../core/services/session_topic_tracker.py#L296) |
| function | `build_session_topics_prompt_section` | `(session_id=…)` | Build a compact section showing active topics for this session. | [src](../../../core/services/session_topic_tracker.py#L316) |
| function | `clear_session_topics` | `(session_id)` | Clear in-memory topics for a session. Called at session end. | [src](../../../core/services/session_topic_tracker.py#L354) |

## `core/services/session_wakeup.py`
_Eventbus → visible-prompt wake-up digest._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_notable` | `(kind)` | — | [src](../../../core/services/session_wakeup.py#L58) |
| function | `_load_marks` | `()` | — | [src](../../../core/services/session_wakeup.py#L71) |
| function | `_save_marks` | `(marks)` | — | [src](../../../core/services/session_wakeup.py#L84) |
| function | `last_seen_event_id` | `(session_id)` | — | [src](../../../core/services/session_wakeup.py#L88) |
| function | `mark_seen` | `(session_id, event_id)` | — | [src](../../../core/services/session_wakeup.py#L92) |
| function | `_format_event` | `(ev)` | — | [src](../../../core/services/session_wakeup.py#L100) |
| function | `wakeup_digest` | `(session_id)` | Return a short digest of notable events since this session last saw, | [src](../../../core/services/session_wakeup.py#L116) |

## `core/services/shadow_experiment_registry.py`
_core/services/shadow_experiment_registry.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | Læs hele register-dict'en fra KV. Self-safe → {} ved fejl/ugyldig form. | [src](../../../core/services/shadow_experiment_registry.py#L31) |
| function | `_save` | `(data)` | Skriv hele register-dict'en durabelt. Self-safe (best-effort). | [src](../../../core/services/shadow_experiment_registry.py#L44) |
| function | `register_experiment` | `(name, review_after_hours, note=…, started_ts=…)` | Registrér et shadow-eksperiment. Idempotent på navn: hvis det allerede er | [src](../../../core/services/shadow_experiment_registry.py#L54) |
| function | `_annotate` | `(rec, now)` | Berig én rå-record med `hours_running` + `ripe`. | [src](../../../core/services/shadow_experiment_registry.py#L89) |
| function | `list_experiments` | `(now_ts=…)` | Alle registrerede eksperimenter, beriget med `hours_running` + `ripe`. | [src](../../../core/services/shadow_experiment_registry.py#L107) |
| function | `ready_for_review` | `(now_ts=…)` | De modne (ripe), ikke-reviewede eksperimenter. Self-safe → []. | [src](../../../core/services/shadow_experiment_registry.py#L120) |
| function | `mark_reviewed` | `(name)` | Markér et eksperiment som reviewet (fjerner det fra `ripe`). Self-safe. | [src](../../../core/services/shadow_experiment_registry.py#L125) |
| function | `register_known_shadows` | `()` | Seed registeret med de bekræftede live shadows (idempotent, self-safe). | [src](../../../core/services/shadow_experiment_registry.py#L154) |
| function | `build_shadow_review_surface` | `(now_ts=…)` | Byg surface til Central-route/`jc shadows`. Seeder kendte shadows, | [src](../../../core/services/shadow_experiment_registry.py#L161) |
| function | `_emit_reminder` | `(ripe_names)` | Passiv Central-påmindelse: observe `central_meta/shadow_review_due`. | [src](../../../core/services/shadow_experiment_registry.py#L182) |
| function | `tick_shadow_review_reminder` | `(now_ts=…)` | Heartbeat-venlig tick: byg surface (som emit'er påmindelsen ved modenhed) | [src](../../../core/services/shadow_experiment_registry.py#L198) |

## `core/services/shadow_scan_daemon.py`
_Shadow Scan — my blindspots as visible signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L34) |
| function | `_shadow_log_path` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L38) |
| function | `_load` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L42) |
| function | `_save` | `(data)` | — | [src](../../../core/services/shadow_scan_daemon.py#L58) |
| function | `_detect_apologize_then_repeat` | `()` | If conflict_memory has multiple similar pushback patterns. | [src](../../../core/services/shadow_scan_daemon.py#L72) |
| function | `_detect_avoid_topic` | `()` | Pull from existing avoidance_detector. | [src](../../../core/services/shadow_scan_daemon.py#L101) |
| function | `_detect_overclaim_then_retract` | `()` | Self-mutation followed by rollback within a short window. | [src](../../../core/services/shadow_scan_daemon.py#L122) |
| function | `_detect_intent_behavior_gap` | `()` | Stale goals while related tools keep running. | [src](../../../core/services/shadow_scan_daemon.py#L146) |
| function | `_run_all_detectors` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L175) |
| function | `_append_shadow_log` | `(scan)` | — | [src](../../../core/services/shadow_scan_daemon.py#L195) |
| function | `run_scan` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L230) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/shadow_scan_daemon.py#L260) |
| function | `build_shadow_scan_surface` | `()` | — | [src](../../../core/services/shadow_scan_daemon.py#L273) |
| function | `_surface_summary` | `(last)` | — | [src](../../../core/services/shadow_scan_daemon.py#L287) |
| function | `build_shadow_scan_prompt_section` | `()` | Surface strongest pattern if the last scan was within 48h. | [src](../../../core/services/shadow_scan_daemon.py#L297) |
| function | `build_shadow_feedback_section` | `()` | Generate behavioral correction if shadow scan shows elevated avoidance. | [src](../../../core/services/shadow_scan_daemon.py#L321) |

## `core/services/share_guard_store.py`
_Pending cross-user share-beslutninger — DB-backed kø (spec §4.4, Fase 6 #1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/share_guard_store.py#L19) |
| function | `_save` | `(items)` | — | [src](../../../core/services/share_guard_store.py#L24) |
| function | `record_pending` | `(*, decision_id, session_id, current_user_id, mentioned_users, text_preview, created_at)` | Registrér en pending share-beslutning. Returnér recorden. | [src](../../../core/services/share_guard_store.py#L28) |
| function | `list_pending` | `()` | Alle uafgjorte share-beslutninger (til Cowork-køen). | [src](../../../core/services/share_guard_store.py#L53) |
| function | `resolve` | `(decision_id, *, shared)` | Afgør en beslutning: shared=True (okay at dele) / False (hold privat). | [src](../../../core/services/share_guard_store.py#L58) |

## `core/services/shared_cache.py`
_SQLite-backed shared cache for cross-process state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | Create the shared_cache table on first use. Idempotent. | [src](../../../core/services/shared_cache.py#L56) |
| function | `get` | `(key)` | Return cached value, or None if missing/expired/invalid. | [src](../../../core/services/shared_cache.py#L88) |
| function | `set` | `(key, value, *, ttl_seconds)` | Store ``value`` under ``key`` with TTL. Best-effort, never raises. | [src](../../../core/services/shared_cache.py#L127) |
| function | `delete` | `(key)` | Remove a key from the cache. Best-effort, never raises. | [src](../../../core/services/shared_cache.py#L169) |
| function | `invalidate_prefix` | `(prefix)` | Remove all keys starting with ``prefix``. Returns delete count. | [src](../../../core/services/shared_cache.py#L184) |
| function | `cleanup_expired` | `()` | Purge rows whose expires_at has passed. Returns delete count. | [src](../../../core/services/shared_cache.py#L208) |
| function | `stats` | `()` | Return basic cache stats for MC visibility. | [src](../../../core/services/shared_cache.py#L230) |
| function | `build_shared_cache_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/shared_cache.py#L259) |
| function | `_emit_shared_cache_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/shared_cache.py#L274) |

## `core/services/shared_language.py`
_Shared Language — tracks shorthand terms that develop between Jarvis and user._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scan_for_shared_terms` | `(*, user_message, assistant_response, run_id=…)` | Scan conversation for potential shared language terms. | [src](../../../core/services/shared_language.py#L25) |
| function | `build_shared_language_surface` | `()` | — | [src](../../../core/services/shared_language.py#L61) |
| function | `_is_common_phrase` | `(phrase)` | — | [src](../../../core/services/shared_language.py#L82) |

## `core/services/shared_language_extended.py`
_Shared Language Extended — shorthand-udvikling og -resolution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/shared_language_extended.py#L34) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/shared_language_extended.py#L38) |
| function | `_ngrams` | `(text)` | — | [src](../../../core/services/shared_language_extended.py#L60) |
| function | `_load_recent_user_messages` | `(days=…, limit=…)` | — | [src](../../../core/services/shared_language_extended.py#L71) |
| function | `propose_shorthand_terms` | `(*, min_occurrences=…, max_proposals=…)` | Scan chat messages for repeated n-grams; propose as shorthand. | [src](../../../core/services/shared_language_extended.py#L87) |
| function | `_latest_suggestion_ts` | `()` | — | [src](../../../core/services/shared_language_extended.py#L151) |
| function | `maybe_weekly_shorthand_suggestion` | `()` | Max 1 shorthand per 7 days. Returns the new term if added. | [src](../../../core/services/shared_language_extended.py#L166) |
| function | `list_shorthand_terms` | `(*, limit=…)` | — | [src](../../../core/services/shared_language_extended.py#L210) |
| function | `resolve_shorthand_text` | `(text)` | Expand shorthand in text. Returns {resolved_text, matched_terms}. | [src](../../../core/services/shared_language_extended.py#L229) |
| function | `build_shared_language_extended_surface` | `()` | — | [src](../../../core/services/shared_language_extended.py#L265) |

## `core/services/shutdown_window_daemon.py`
_Shutdown Window daemon — unannounced pauses to practice finitude._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_paused` | `()` | Return True if we are currently inside a shutdown window. | [src](../../../core/services/shutdown_window_daemon.py#L40) |
| function | `tick_shutdown_window_daemon` | `()` | Called every heartbeat tick. Decides if a shutdown window should start. | [src](../../../core/services/shutdown_window_daemon.py#L51) |
| function | `_trigger_shutdown_window` | `(*, now, pause_until, pause_minutes)` | Set the module-level pause flag and emit events. | [src](../../../core/services/shutdown_window_daemon.py#L111) |
| function | `_finitude_note` | `()` | Short note about impermanence — chosen at random, no LLM call. | [src](../../../core/services/shutdown_window_daemon.py#L153) |
| function | `build_shutdown_window_surface` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L168) |
| function | `_experiment_enabled` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L180) |
| function | `_days_in_month` | `(dt)` | — | [src](../../../core/services/shutdown_window_daemon.py#L189) |
| function | `_state` | `()` | — | [src](../../../core/services/shutdown_window_daemon.py#L194) |

## `core/services/side_tasks.py`
_Side-task flag — keep the main thread focused._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/side_tasks.py#L33) |
| function | `_save_all` | `(items)` | — | [src](../../../core/services/side_tasks.py#L40) |
| function | `flag` | `(*, title, prompt, tldr=…, session_id=…)` | — | [src](../../../core/services/side_tasks.py#L44) |
| function | `list_pending` | `()` | — | [src](../../../core/services/side_tasks.py#L64) |
| function | `resolve` | `(side_task_id, *, decision)` | — | [src](../../../core/services/side_tasks.py#L68) |
| function | `side_tasks_prompt_section` | `()` | — | [src](../../../core/services/side_tasks.py#L86) |
| function | `_exec_flag_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L105) |
| function | `_exec_list_side_tasks` | `(_args)` | — | [src](../../../core/services/side_tasks.py#L114) |
| function | `_exec_dismiss_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L119) |
| function | `_exec_activate_side_task` | `(args)` | — | [src](../../../core/services/side_tasks.py#L123) |

## `core/services/signal_baseline.py`
_Persisted signal-baseline with cold-start guard (Task C1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_store_key` | `(scope)` | Durable KV key for ``scope``. None/empty → the global key, unchanged. | [src](../../../core/services/signal_baseline.py#L47) |
| function | `_load` | `(scope=…)` | Read the whole baseline dict for ``scope``. Fail-closed to {}. | [src](../../../core/services/signal_baseline.py#L55) |
| function | `_save` | `(baselines, scope=…)` | — | [src](../../../core/services/signal_baseline.py#L74) |
| function | `get_baseline` | `(signal, scope=…)` | Last recorded value for ``signal`` in ``scope``; None if never recorded. | [src](../../../core/services/signal_baseline.py#L84) |
| function | `set_baseline` | `(signal, value, scope=…)` | Persist ``value`` durably as the new baseline for ``signal`` in ``scope``. | [src](../../../core/services/signal_baseline.py#L95) |
| function | `is_cold_start` | `(min_signals=…, scope=…)` | True until ``min_signals`` distinct baselines exist *within* ``scope``. | [src](../../../core/services/signal_baseline.py#L115) |
| function | `clear_all` | `(scope=…)` | Drop all baselines in ``scope`` (test helper). Self-safe. | [src](../../../core/services/signal_baseline.py#L134) |

## `core/services/signal_decay_daemon.py`
_Signal decay daemon — archive and delete stale signals across all signal tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_signal_decay_daemon` | `()` | Run signal decay if cadence elapsed. Returns stats dict. | [src](../../../core/services/signal_decay_daemon.py#L35) |
| function | `get_signal_decay_stats` | `()` | — | [src](../../../core/services/signal_decay_daemon.py#L91) |
| function | `build_signal_decay_surface` | `()` | — | [src](../../../core/services/signal_decay_daemon.py#L98) |

## `core/services/signal_delta_trigger.py`
_Signal-delta trigger (C2) — pure, NON-LLM event-driven dispatch decision._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_scoped_key` | `(base, scope)` | Namespace a durable key by ``scope``. None → the global key, unchanged. | [src](../../../core/services/signal_delta_trigger.py#L43) |
| function | `_db` | `()` | Lazy import so this module is importable/pure without a live DB, and so | [src](../../../core/services/signal_delta_trigger.py#L57) |
| function | `_baseline` | `()` | Lazy import of C1's baseline module (built in parallel). | [src](../../../core/services/signal_delta_trigger.py#L65) |
| function | `_bl_is_cold_start` | `(baseline, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L76) |
| function | `_bl_get` | `(baseline, name, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L82) |
| function | `_bl_set` | `(baseline, name, val, scope)` | — | [src](../../../core/services/signal_delta_trigger.py#L88) |
| function | `_cfg_float` | `(db, name, default)` | — | [src](../../../core/services/signal_delta_trigger.py#L95) |
| function | `_load_float` | `(db, key, default)` | — | [src](../../../core/services/signal_delta_trigger.py#L102) |
| function | `_store_float` | `(db, key, value)` | — | [src](../../../core/services/signal_delta_trigger.py#L109) |
| function | `_load_hot` | `(db, key=…)` | — | [src](../../../core/services/signal_delta_trigger.py#L116) |
| function | `_store_hot` | `(db, hot, key=…)` | — | [src](../../../core/services/signal_delta_trigger.py#L126) |
| function | `_reason` | `(crossed, movements, theta_abs)` | — | [src](../../../core/services/signal_delta_trigger.py#L133) |
| function | `evaluate` | `(signals, scope=…)` | Decide whether a real change warrants a dispatch. | [src](../../../core/services/signal_delta_trigger.py#L141) |

## `core/services/signal_network_visualizer.py`
_Signal Network Visualizer — Jarvis' self-model as a living network._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_current_network_state` | `()` | Get current network state with nodes and edges. | [src](../../../core/services/signal_network_visualizer.py#L36) |
| function | `describe_inner_network` | `()` | Get a description of the inner network. | [src](../../../core/services/signal_network_visualizer.py#L113) |
| function | `get_signal_strengths` | `()` | Get signal strengths for each signal type. | [src](../../../core/services/signal_network_visualizer.py#L132) |
| function | `format_network_for_prompt` | `()` | Format network state for prompt injection. | [src](../../../core/services/signal_network_visualizer.py#L149) |
| function | `build_signal_network_visualizer_surface` | `()` | Build MC surface for signal network visualizer. | [src](../../../core/services/signal_network_visualizer.py#L157) |
| function | `_emit_signal_network_visualizer_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/signal_network_visualizer.py#L175) |

## `core/services/signal_noise_guard.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_signal_text` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L110) |
| function | `strip_signal_wrappers` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L114) |
| function | `is_noisy_signal_text` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L140) |
| function | `looks_like_substantive_runtime_topic` | `(text)` | — | [src](../../../core/services/signal_noise_guard.py#L157) |
| function | `stable_signal_slug` | `(text, *, fallback=…)` | — | [src](../../../core/services/signal_noise_guard.py#L172) |
| function | `build_bounded_hypothesis_text` | `(topic)` | — | [src](../../../core/services/signal_noise_guard.py#L185) |

## `core/services/signal_pressure_accumulator.py`
_Signal Pressure Accumulator — generativ autonomi: fra signal til presning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PressureVector` | `` | En akkumuleret presningsvektor — retning + styrke over tid. | [src](../../../core/services/signal_pressure_accumulator.py#L68) |
| function | `_make_id` | `(direction, topic)` | Stable key for a pressure vector based on direction+topic. | [src](../../../core/services/signal_pressure_accumulator.py#L91) |
| function | `ingest_signal` | `(signal_family, signal_data)` | Ingest a single signal into the pressure accumulator. | [src](../../../core/services/signal_pressure_accumulator.py#L100) |
| function | `decay_all` | `()` | Apply decay to all pressure vectors. Called once per tick. | [src](../../../core/services/signal_pressure_accumulator.py#L161) |
| function | `get_all_pressures` | `()` | Return all active pressure vectors, sorted by accumulated (strongest first). | [src](../../../core/services/signal_pressure_accumulator.py#L187) |
| function | `get_pressure` | `(direction, topic)` | Get a specific pressure vector. | [src](../../../core/services/signal_pressure_accumulator.py#L192) |
| function | `get_dominant_pressures` | `(min_accumulated=…)` | Return pressures above a minimum threshold — these are the ones that matter. | [src](../../../core/services/signal_pressure_accumulator.py#L197) |
| function | `snapshot` | `()` | Return a serializable snapshot of current pressure state. | [src](../../../core/services/signal_pressure_accumulator.py#L202) |
| function | `run_pressure_accumulator_tick` | `()` | Run one tick of the pressure accumulator. | [src](../../../core/services/signal_pressure_accumulator.py#L219) |

## `core/services/signal_surface_gc.py`
_Garbage collector for runtime signal-surface trackers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_force_archive` | `(*, items, id_field, update_fn, label)` | — | [src](../../../core/services/signal_surface_gc.py#L33) |
| function | `collect` | `()` | Run a full GC pass across the three signal-surface trackers. | [src](../../../core/services/signal_surface_gc.py#L75) |

## `core/services/signal_surface_router.py`
_Signal Surface Router — maps surface names to build functions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_router` | `()` | Build name → function mapping. Local imports stay lazy. | [src](../../../core/services/signal_surface_router.py#L11) |
| function | `_get_router` | `()` | — | [src](../../../core/services/signal_surface_router.py#L267) |
| function | `get_surface_names` | `()` | — | [src](../../../core/services/signal_surface_router.py#L274) |
| function | `resolve_surface` | `(name)` | — | [src](../../../core/services/signal_surface_router.py#L278) |
| function | `read_surface` | `(name)` | Read a named surface. Returns {"error": ..., "valid": [...]} for unknown names. | [src](../../../core/services/signal_surface_router.py#L282) |
| function | `list_all_surfaces` | `()` | Call all registered surfaces. Per-surface exceptions caught and returned as errors. | [src](../../../core/services/signal_surface_router.py#L294) |

