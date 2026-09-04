# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/policy_abstraction.py`
_Policy Abstraktion — Phase 2 of Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/policy_abstraction.py#L32) |
| function | `_ensure_table` | `(conn)` | Idempotent table creation for generalized policies. | [src](../../../core/services/policy_abstraction.py#L36) |
| function | `is_enabled` | `()` | — | [src](../../../core/services/policy_abstraction.py#L71) |
| function | `set_enabled` | `(value)` | — | [src](../../../core/services/policy_abstraction.py#L75) |
| function | `abstract_rule` | `(*, rule_key, policy, lesson, target_context, evidence_count, confidence, source_domain=…)` | Generate a generalized principle from a specific learning policy rule. | [src](../../../core/services/policy_abstraction.py#L82) |
| function | `match_generalized_policies` | `(*, task_description=…, context_domain=…, limit=…, min_confidence=…)` | Retrieve generalized policies relevant to the current task/context. | [src](../../../core/services/policy_abstraction.py#L196) |
| function | `build_generalized_policies_surface` | `(*, limit=…)` | Compact surface for prompt injection — top generalized policies. | [src](../../../core/services/policy_abstraction.py#L280) |
| function | `count_abstraction_candidates` | `()` | Count how many active learning policy rules are ready for abstraction. | [src](../../../core/services/policy_abstraction.py#L309) |
| function | `sweep_abstraction_candidates` | `(max_rules=…)` | Find all rules ready for abstraction and abstract them. | [src](../../../core/services/policy_abstraction.py#L326) |
| function | `_llm_generalize` | `(*, specific_rule, target_context, evidence_count, confidence, source_domain)` | Generate a generalized principle via cheap-lane LLM. | [src](../../../core/services/policy_abstraction.py#L382) |
| function | `_compute_relevance` | `(*, principle, transfer_domains, task_description, context_domain, base_confidence)` | Score how relevant a generalized policy is to the current task. | [src](../../../core/services/policy_abstraction.py#L457) |
| function | `build_policy_abstraction_prompt_section` | `(*, limit=…)` | Build a compact awareness section with top generalized policies. | [src](../../../core/services/policy_abstraction.py#L499) |

## `core/services/post_tool_answer_guard.py`
_Guards for tool turns that end in hollow final prose._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tool_call_count` | `(exchanges)` | — | [src](../../../core/services/post_tool_answer_guard.py#L13) |
| function | `is_hollow_post_tool_answer` | `(answer_text, exchanges)` | — | [src](../../../core/services/post_tool_answer_guard.py#L17) |
| function | `should_replace_with_synthesis` | `(current_text, candidate_text)` | — | [src](../../../core/services/post_tool_answer_guard.py#L26) |

## `core/services/precision_bias.py`
_Precision Bias — emotional color-mapping for action style._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PrecisionProfile` | `` | Computed precision bias for one turn. | [src](../../../core/services/precision_bias.py#L129) |
| function | `compute_precision_bias` | `()` | Compute the current precision bias from pressure state. | [src](../../../core/services/precision_bias.py#L144) |
| function | `format_precision_for_prompt` | `(profile)` | Format a precision profile for prompt injection. | [src](../../../core/services/precision_bias.py#L203) |
| function | `get_precision_line` | `()` | Convenience: compute + format in one call. Returns None on any failure. | [src](../../../core/services/precision_bias.py#L223) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/precision_bias.py#L235) |
| function | `_find_style_dominant_signal` | `(dominant_pressures)` | Find which signal family should drive style when multiple pressures exist. | [src](../../../core/services/precision_bias.py#L246) |
| function | `build_precision_bias_surface` | `()` | — | [src](../../../core/services/precision_bias.py#L285) |
| function | `_emit_bias_event` | `(class_id, bias)` | — | [src](../../../core/services/precision_bias.py#L294) |

## `core/services/pressure_threshold_gate.py`
_Pressure Threshold Gate — konverterer presning til impuls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Impulse` | `` | En impuls — en presning der har krydset tærsklen og bliver til vilje. | [src](../../../core/services/pressure_threshold_gate.py#L65) |
| function | `_get_threshold` | `(direction)` | Get the current threshold for a direction, creating default if needed. | [src](../../../core/services/pressure_threshold_gate.py#L88) |
| function | `_adapt_threshold` | `(direction, crossed)` | Adapt threshold based on whether it was crossed. | [src](../../../core/services/pressure_threshold_gate.py#L95) |
| function | `_is_on_cooldown` | `(direction)` | Check if a direction is still in cooldown from a recent impulse. | [src](../../../core/services/pressure_threshold_gate.py#L109) |
| function | `evaluate_pressures` | `(pressures)` | Evaluate all pressure vectors and generate impulses for those that cross thresholds. | [src](../../../core/services/pressure_threshold_gate.py#L122) |
| function | `get_pending_impulses` | `()` | Return all pending impulses that haven't been executed yet. | [src](../../../core/services/pressure_threshold_gate.py#L197) |
| function | `mark_impulse_executing` | `(impulse_id, action=…)` | Mark an impulse as currently being executed. | [src](../../../core/services/pressure_threshold_gate.py#L202) |
| function | `mark_impulse_completed` | `(impulse_id, action=…)` | Mark an impulse as completed. | [src](../../../core/services/pressure_threshold_gate.py#L211) |
| function | `mark_impulse_failed` | `(impulse_id, reason=…)` | Mark an impulse as failed. | [src](../../../core/services/pressure_threshold_gate.py#L221) |
| function | `snapshot` | `()` | Return serializable snapshot of gate state. | [src](../../../core/services/pressure_threshold_gate.py#L230) |
| function | `run_threshold_gate_tick` | `()` | Run one tick of the threshold gate. | [src](../../../core/services/pressure_threshold_gate.py#L244) |

## `core/services/priors_feedback.py`
_Priors feedback — surfaces past patterns relevant to NOW._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_crisis_summary` | `(days=…)` | — | [src](../../../core/services/priors_feedback.py#L31) |
| function | `_decision_priors` | `()` | Pull active decisions + flag any with low adherence. | [src](../../../core/services/priors_feedback.py#L53) |
| function | `_quality_outlier_priors` | `(days=…)` | If recent ticks dropped sharply, surface that as context. | [src](../../../core/services/priors_feedback.py#L84) |
| function | `build_priors_feedback` | `()` | Return up to ~6 prior lines. Empty list = no signal. | [src](../../../core/services/priors_feedback.py#L109) |
| function | `priors_feedback_section` | `()` | — | [src](../../../core/services/priors_feedback.py#L118) |

## `core/services/private_initiative_tension_signal_tracking.py`
_Private initiative-tension signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_initiative_tension_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L36) |
| function | `refresh_runtime_private_initiative_tension_signal_statuses` | `()` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L71) |
| function | `build_runtime_private_initiative_tension_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L75) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L81) |
| function | `_latest_visible_work_note_for_run` | `(run_id)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L188) |
| function | `_latest_open_loop_pressure` | `()` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L201) |
| function | `_latest_development_focus` | `()` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L209) |
| function | `_latest_inner_note_support` | `(*, run_id)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L217) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L228) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L249) |
| function | `_private_initiative_tension_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L276) |
| function | `_domain_key` | `(item, *, fallback)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L321) |
| function | `_source_anchor_from_visible_note` | `(visible_note)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L328) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L340) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L350) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L362) |
| function | `_canonical_tension_type` | `(canonical_key)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L372) |
| function | `_title_target` | `(title)` | — | [src](../../../core/services/private_initiative_tension_signal_tracking.py#L379) |

## `core/services/private_inner_interplay_signal_tracking.py`
_Private inner-interplay signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_inner_interplay_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L35) |
| function | `refresh_runtime_private_inner_interplay_signal_statuses` | `()` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L69) |
| function | `build_runtime_private_inner_interplay_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L73) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L79) |
| function | `_latest_inner_note_support` | `(*, run_id)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L158) |
| function | `_latest_initiative_tension_support` | `(*, run_id)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L168) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L178) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L199) |
| function | `_private_inner_interplay_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L228) |
| function | `_relation_key` | `(*, note_focus, tension)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L244) |
| function | `_note_focus` | `(item)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L260) |
| function | `_note_summary` | `(item)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L270) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L281) |
| function | `_title_target` | `(title)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L291) |
| function | `_canonical_tension_type` | `(canonical_key)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L299) |
| function | `_canonical_interplay_type` | `(canonical_key)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L308) |
| function | `_stronger_confidence` | `(left, right)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L317) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L326) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/private_inner_interplay_signal_tracking.py#L340) |

## `core/services/private_inner_note_signal_tracking.py`
_Private inner-note signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_inner_note_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L38) |
| function | `refresh_runtime_private_inner_note_signal_statuses` | `()` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L73) |
| function | `build_runtime_private_inner_note_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L77) |
| function | `_latest_visible_work_note_for_run` | `(run_id)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L83) |
| function | `_latest_cognitive_signal_for_run` | `(run_id)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L96) |
| function | `_cognitive_source_label` | `(signal)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L118) |
| function | `_candidate_from_visible_note` | `(visible_note)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L138) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L217) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L244) |
| function | `_private_inner_note_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L285) |
| function | `_confidence_from_uncertainty` | `(value)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L307) |
| function | `_source_anchor` | `(visible_note)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L314) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L326) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L338) |
| function | `_find_support_value` | `(summary, key)` | — | [src](../../../core/services/private_inner_note_signal_tracking.py#L348) |

## `core/services/private_state_snapshot_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_state_snapshots_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L20) |
| function | `refresh_runtime_private_state_snapshot_statuses` | `()` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L52) |
| function | `build_runtime_private_state_snapshot_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L85) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L124) |
| function | `_persist_private_state_snapshots` | `(*, snapshots, session_id, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L213) |
| function | `_latest_inner_note_support` | `(*, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L284) |
| function | `_latest_initiative_tension_support` | `(*, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L294) |
| function | `_latest_inner_interplay_support` | `(*, run_id)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L304) |
| function | `_with_runtime_view` | `(item, snapshot)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L314) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L337) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L369) |
| function | `_bounded_state_summary` | `(*, inner_note, initiative_tension, inner_interplay, tone)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L380) |
| function | `_state_pressure` | `(level, *, interplay_type)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L408) |
| function | `_pressure_from_tone` | `(tone)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L417) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L423) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L431) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L446) |
| function | `_value` | `(*candidates, default)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L453) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L461) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/private_state_snapshot_tracking.py#L473) |

## `core/services/private_temporal_curiosity_state_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_temporal_curiosity_states_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L19) |
| function | `refresh_runtime_private_temporal_curiosity_state_statuses` | `()` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L51) |
| function | `build_runtime_private_temporal_curiosity_state_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L82) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L111) |
| function | `_persist_private_temporal_curiosity_states` | `(*, states, session_id, run_id)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L190) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L259) |
| function | `_latest_initiative_tension_support` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L269) |
| function | `_with_runtime_view` | `(item, state)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L279) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L297) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L318) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L326) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L337) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L352) |
| function | `_value` | `(*candidates, default)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L359) |
| function | `_pull_from_type` | `(curiosity_type)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L367) |
| function | `_title_target` | `(title)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L373) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L381) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/private_temporal_curiosity_state_tracking.py#L393) |

## `core/services/private_temporal_promotion_signal_tracking.py`
_Private temporal-promotion signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_private_temporal_promotion_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L35) |
| function | `refresh_runtime_private_temporal_promotion_signal_statuses` | `()` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L69) |
| function | `build_runtime_private_temporal_promotion_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L73) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L77) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L181) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L191) |
| function | `_latest_initiative_tension_support` | `(*, run_id)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L201) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L211) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L228) |
| function | `_private_temporal_promotion_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L248) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L265) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L278) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L289) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L304) |
| function | `_value` | `(*candidates, default)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L311) |
| function | `_pull_from_type` | `(promotion_type)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L319) |
| function | `_pull_from_curiosity_type` | `(curiosity_type)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L325) |
| function | `_pressure_from_state_tone` | `(state_tone)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L331) |
| function | `_title_target` | `(title)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L337) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/private_temporal_promotion_signal_tracking.py#L345) |

## `core/services/proactive_candidates.py`
_Proactive candidates — the ONE queue for "Jarvis wants to tell Bjørn something"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/proactive_candidates.py#L53) |
| function | `_terms` | `(text)` | — | [src](../../../core/services/proactive_candidates.py#L57) |
| function | `lexical_coverage` | `(query, text)` | — | [src](../../../core/services/proactive_candidates.py#L66) |
| function | `_norm_text` | `(text)` | — | [src](../../../core/services/proactive_candidates.py#L73) |
| function | `ensure_table` | `(conn)` | — | [src](../../../core/services/proactive_candidates.py#L77) |
| function | `_row` | `(r)` | — | [src](../../../core/services/proactive_candidates.py#L99) |
| function | `normalize_priority` | `(importance)` | — | [src](../../../core/services/proactive_candidates.py#L107) |
| function | `add_candidate` | `(*, source, text, priority=…, kind=…)` | Queue a message for Bjørn. Deduped on normalized text within 24 h. | [src](../../../core/services/proactive_candidates.py#L116) |
| function | `list_pending` | `(*, limit=…, priorities=…)` | — | [src](../../../core/services/proactive_candidates.py#L156) |
| function | `mark` | `(candidate_ids, status, *, run_id=…)` | — | [src](../../../core/services/proactive_candidates.py#L170) |
| function | `expire_stale` | `(*, days=…)` | — | [src](../../../core/services/proactive_candidates.py#L191) |
| function | `counts` | `()` | — | [src](../../../core/services/proactive_candidates.py#L204) |
| function | `relevant_for` | `(user_message, *, limit=…, min_coverage=…)` | Pending items lexically relevant to what Bjørn just wrote (best first). | [src](../../../core/services/proactive_candidates.py#L214) |
| function | `remember_shown` | `(session_id, candidate_ids)` | — | [src](../../../core/services/proactive_candidates.py#L228) |
| function | `build_since_last_line` | `(user_message, *, session_id=…)` | At most ONE line: 'Siden sidst: …' when a pending item is relevant to the message. | [src](../../../core/services/proactive_candidates.py#L239) |
| function | `mark_mentioned_if_overlap` | `(*, session_id, answer_text, run_id=…, min_coverage=…)` | Auto-deliver: the shown item counts as delivered when Jarvis' answer overlaps it. | [src](../../../core/services/proactive_candidates.py#L254) |
| function | `bridge_candidates` | `()` | Shape expected by proactivity_bridge.collect_candidates(). | [src](../../../core/services/proactive_candidates.py#L282) |
| function | `build_proactive_candidates_surface` | `()` | — | [src](../../../core/services/proactive_candidates.py#L297) |

## `core/services/proactive_context_governor.py`
_Proactive context governor — auto-trigger compaction + sub-agent slicing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `should_auto_compact` | `()` | Decide whether prompt_contract should trigger compaction now. | [src](../../../core/services/proactive_context_governor.py#L50) |
| function | `auto_compact_if_needed` | `()` | Run compaction if threshold crossed. Idempotent (cooldown protected). | [src](../../../core/services/proactive_context_governor.py#L101) |
| function | `auto_compact_if_needed_deferred` | `()` | Schedulér auto-compact til at køre EFTER den nuværende synlige tur (off critical | [src](../../../core/services/proactive_context_governor.py#L145) |
| function | `build_subagent_context_slice` | `(*, role, goal, max_chars=…)` | Compose a tailored context slice for a sub-agent based on goal. | [src](../../../core/services/proactive_context_governor.py#L195) |
| function | `_load_versions` | `()` | — | [src](../../../core/services/proactive_context_governor.py#L252) |
| function | `_save_versions` | `(versions)` | — | [src](../../../core/services/proactive_context_governor.py#L259) |
| function | `save_context_version` | `(*, reason=…)` | Snapshot the current session state. Returns version_id. | [src](../../../core/services/proactive_context_governor.py#L263) |
| function | `list_context_versions` | `(*, limit=…)` | — | [src](../../../core/services/proactive_context_governor.py#L301) |
| function | `recall_context_version` | `(version_id)` | — | [src](../../../core/services/proactive_context_governor.py#L316) |
| function | `_exec_should_auto_compact` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L327) |
| function | `_exec_auto_compact_if_needed` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L331) |
| function | `_exec_build_subagent_context` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L335) |
| function | `_exec_list_context_versions` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L343) |
| function | `_exec_recall_context_version` | `(args)` | — | [src](../../../core/services/proactive_context_governor.py#L347) |

## `core/services/proactive_loop_lifecycle_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_proactive_loop_lifecycle_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L73) |
| function | `refresh_runtime_proactive_loop_lifecycle_signal_statuses` | `()` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L96) |
| function | `build_runtime_proactive_loop_lifecycle_surface` | `(*, limit=…)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L159) |
| function | `_build_runtime_proactive_loop_lifecycle_surface_uncached` | `(*, limit=…)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L169) |
| function | `_extract_proactive_loop_lifecycle_candidates` | `()` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L216) |
| function | `_build_lifecycle_candidate` | `(*, loop_kind, loop_focus, open_loop, autonomy_pressure, source_anchor, question_readiness, closure_readiness, relation, meaning, witness, chronicle, metabolism, release, initiative, regulation)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L379) |
| function | `_persist_proactive_loop_lifecycle_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L492) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L554) |
| function | `_best_loop_focus` | `(*, latest_loop, attachment, loyalty, relation, meaning)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L586) |
| function | `_normalize_focus_candidate` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L607) |
| function | `_derive_loop_state` | `(*, loop_kind, open_status, question_readiness, closure_readiness, witness_persistence, release_state)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L633) |
| function | `_loop_summary` | `(*, loop_kind, loop_state, loop_focus, question_readiness, closure_readiness)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L653) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L677) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L685) |
| function | `_max_ranked` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L696) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L705) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L714) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L723) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/proactive_loop_lifecycle_tracking.py#L730) |

## `core/services/proactive_outbound_substrate.py`
_Proactive-outbound substrate — what Jarvis just said proactively._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_summarize_outbound_payload` | `(kind, payload)` | Extract the actual question/message text from a delivered event. | [src](../../../core/services/proactive_outbound_substrate.py#L36) |
| function | `compute_proactive_outbound_substrate` | `(*, window_min=…, max_events=…)` | Return raw proactive-outbound events as substrate strings. | [src](../../../core/services/proactive_outbound_substrate.py#L49) |
| function | `build_proactive_outbound_section` | `()` | Prompt section — proactive messages Jarvis sent in last 30 min. | [src](../../../core/services/proactive_outbound_substrate.py#L101) |

## `core/services/proactive_question_gate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_proactive_question_gates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L52) |
| function | `refresh_runtime_proactive_question_gate_statuses` | `()` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L75) |
| function | `build_runtime_proactive_question_gate_surface` | `(*, limit=…)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L105) |
| function | `_extract_proactive_question_gate_candidates` | `()` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L149) |
| function | `_persist_proactive_question_gates` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L345) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L396) |
| function | `_gate_reason` | `(*, awareness_constrained, release_state, witness_carried, chronicle_weight, loyalty_weight, attachment_weight, question_readiness, continuity_mode)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L419) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L447) |
| function | `_question_continuity_support` | `(*, relation, meaning, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L455) |
| function | `_initiative_loop_gate_continuity_support` | `(*, question_pressure, question_loop, regulation, awareness)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L498) |
| function | `_question_loop_focus` | `(question_loop)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L523) |
| function | `_normalize_focus_candidate` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L535) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L552) |
| function | `_max_ranked` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L563) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L572) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L581) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L590) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/proactive_question_gate_tracking.py#L597) |

## `core/services/proactivity_bridge.py`
_Proaktivitets-broen — samler Jarvis' indre spørgsmål/initiativer/undren og overflader dem til_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify` | `(candidate)` | 'urgent' hvis høj/kritisk prioritet eller kritisk kind; ellers 'normal'. Ren. | [src](../../../core/services/proactivity_bridge.py#L21) |
| function | `select` | `(candidates)` | Dedup på source_id, split i urgent/normal, sortér (urgent først/friskest), cap normal-listen. | [src](../../../core/services/proactivity_bridge.py#L30) |
| function | `should_reach_owner` | `(*, owner_present, is_quiet, sent_today, cap, within_cooldown, urgent)` | Ren contact-gate (kalderen injicerer signalerne). Rækkefølge = spam-værn: | [src](../../../core/services/proactivity_bridge.py#L46) |
| function | `build_urgent` | `(item)` | Enkelt-item besked (urgent-gren). | [src](../../../core/services/proactivity_bridge.py#L62) |
| function | `build_digest` | `(normal)` | 'Mens du var væk'-digest af normale items (kort, prioriteret). | [src](../../../core/services/proactivity_bridge.py#L69) |
| function | `_norm_digest` | `(text)` | Normalisér digest til gentagelses-sammenligning (trim/lowercase/kollaps whitespace). | [src](../../../core/services/proactivity_bridge.py#L79) |
| function | `_digest_is_repeat` | `(text)` | True hvis digest-teksten ~= den sidst postede assistant-besked i proactivity-sessionen. | [src](../../../core/services/proactivity_bridge.py#L84) |
| function | `_owner_uid` | `()` | Kanonisk owner-uid = owner-resolver'ens discord-id (samme som den virkende outreach-daemon | [src](../../../core/services/proactivity_bridge.py#L111) |
| function | `_owner_presence` | `(uid)` | (present, away_seconds) fra ÆGTE owner-signaler — IKKE runs (som inkluderer autonome → | [src](../../../core/services/proactivity_bridge.py#L128) |
| function | `collect_candidates` | `()` | Læs de EKSISTERENDE kilder (egress-frit, skriver intet). Self-safe → []. | [src](../../../core/services/proactivity_bridge.py#L157) |
| function | `_route` | `(uid, text, importance)` | Send direkte via den eksisterende notifikations-router (springer nudge-brønden over — broen | [src](../../../core/services/proactivity_bridge.py#L188) |
| function | `_persist_as_chat` | `(uid, text)` | Skriv beskeden som en RIGTIG chat-besked i den dedikerede proactivity-session, så | [src](../../../core/services/proactivity_bridge.py#L203) |
| function | `_mark_sent_items_acted` | `(items)` | Markér afsendte initiativer som acted, så de ikke sendes igen senere (før kun | [src](../../../core/services/proactivity_bridge.py#L218) |
| function | `_observe` | `(nerve, meta)` | — | [src](../../../core/services/proactivity_bridge.py#L242) |
| function | `run_proactivity_bridge_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn. Hybrid: urgent straks / ellers digest / ellers observe suppressed. | [src](../../../core/services/proactivity_bridge.py#L250) |
| function | `register_proactivity_bridge_producer` | `()` | Registrér broen som cadence-producer (~10 min, visible_grace 15 min). | [src](../../../core/services/proactivity_bridge.py#L318) |
| function | `build_proactivity_bridge_surface` | `()` | Read-only surface til /central/proactivity + jc. Self-safe. | [src](../../../core/services/proactivity_bridge.py#L325) |

## `core/services/procedure_bank.py`
_Procedure Bank — reusable procedures learned from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_procedure` | `(*, name, trigger_pattern, procedure_text, success_count=…)` | Record or update a learned procedure. | [src](../../../core/services/procedure_bank.py#L19) |
| function | `build_procedure_surface` | `()` | — | [src](../../../core/services/procedure_bank.py#L45) |

## `core/services/procedure_bank_pipeline.py`
_Procedure Bank Pipeline — lærte rutiner der kan pin'es og matches._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L35) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L39) |
| function | `upsert_procedure` | `(*, name, trigger=…, procedure, pinned=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L64) |
| function | `get_procedure` | `(*, procedure_id=…, procedure_name=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L116) |
| function | `list_procedures` | `(*, query=…, pinned_only=…, limit=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L136) |
| function | `set_procedure_pinned` | `(*, procedure_id=…, procedure_name=…, pinned)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L155) |
| function | `delete_procedure` | `(*, procedure_id=…, procedure_name=…)` | — | [src](../../../core/services/procedure_bank_pipeline.py#L179) |
| function | `match_procedures_for_text` | `(text, *, limit=…)` | Find procedures whose trigger-string matches given text. | [src](../../../core/services/procedure_bank_pipeline.py#L201) |
| function | `maybe_record_procedure_from_run` | `(*, session_id, tool_calls)` | LivingNeuron Fase B (surface-only): udled en NAVNGIVEN kandidat-procedure fra en kørsel der | [src](../../../core/services/procedure_bank_pipeline.py#L242) |
| function | `build_procedure_bank_surface` | `()` | — | [src](../../../core/services/procedure_bank_pipeline.py#L275) |

## `core/services/process_supervisor.py`
_Process supervisor — track long-running background processes Jarvis spawns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/process_supervisor.py#L44) |
| function | `_ensure_dirs` | `()` | — | [src](../../../core/services/process_supervisor.py#L48) |
| function | `_safe_name` | `(name)` | Sanitize a process name for use in filenames. | [src](../../../core/services/process_supervisor.py#L52) |
| function | `_load_registry` | `()` | — | [src](../../../core/services/process_supervisor.py#L58) |
| function | `_save_registry` | `(reg)` | — | [src](../../../core/services/process_supervisor.py#L70) |
| function | `_pid_alive` | `(pid)` | — | [src](../../../core/services/process_supervisor.py#L78) |
| function | `_read_status` | `(entry)` | Snapshot of a registry entry's live status. | [src](../../../core/services/process_supervisor.py#L93) |
| function | `spawn_process` | `(*, name, command, cwd=…, env=…, replace_if_running=…)` | Spawn a detached background process under supervision. | [src](../../../core/services/process_supervisor.py#L125) |
| function | `list_processes` | `(*, include_stopped=…)` | — | [src](../../../core/services/process_supervisor.py#L219) |
| function | `_stop_locked` | `(reg, name, grace)` | Caller must hold _LOCK. Stops the named process gracefully. | [src](../../../core/services/process_supervisor.py#L229) |
| function | `stop_process` | `(name, *, grace=…)` | — | [src](../../../core/services/process_supervisor.py#L264) |
| function | `tail_process_log` | `(name, *, lines=…)` | — | [src](../../../core/services/process_supervisor.py#L271) |
| function | `remove_process` | `(name)` | Remove an entry from the registry. Refuses if still alive. | [src](../../../core/services/process_supervisor.py#L303) |

## `core/services/process_watcher.py`
_Process watcher — push-notification primitive for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/process_watcher.py#L74) |
| function | `_state_path` | `(state_file)` | Resolve a state file path. Accepts absolute, ~ expansion, or | [src](../../../core/services/process_watcher.py#L78) |
| function | `_walk_field` | `(obj, path)` | Walk a dotted path through nested dicts. Returns None if any | [src](../../../core/services/process_watcher.py#L90) |
| class | `Watch` | `` | — | [src](../../../core/services/process_watcher.py#L105) |
| function | `_load_all` | `()` | — | [src](../../../core/services/process_watcher.py#L121) |
| function | `_save_all` | `(watches)` | — | [src](../../../core/services/process_watcher.py#L158) |
| function | `add_watch` | `(*, label, conditions, on_match, notify_text=…, cooldown_seconds=…, one_shot=…)` | Register a new watch. Returns the created Watch as dict, or error. | [src](../../../core/services/process_watcher.py#L172) |
| function | `remove_watch` | `(watch_id)` | — | [src](../../../core/services/process_watcher.py#L224) |
| function | `list_watches` | `()` | — | [src](../../../core/services/process_watcher.py#L234) |
| function | `set_watch_enabled` | `(watch_id, enabled)` | — | [src](../../../core/services/process_watcher.py#L239) |
| function | `_eval_condition` | `(cond, runtime_state)` | Evaluate a single condition. Returns (matched, reason). | [src](../../../core/services/process_watcher.py#L252) |
| function | `_fire_action` | `(watch, reason)` | Execute the watch's on_match action. Errors are logged, not raised. | [src](../../../core/services/process_watcher.py#L436) |
| function | `_evaluate_watches_once` | `()` | One pass: evaluate every enabled watch; fire matched ones. | [src](../../../core/services/process_watcher.py#L510) |
| function | `_watcher_loop` | `()` | — | [src](../../../core/services/process_watcher.py#L580) |
| function | `start_watcher_daemon` | `()` | Start the daemon if not already running. Called once at jarvis-api boot. | [src](../../../core/services/process_watcher.py#L597) |
| function | `stop_watcher_daemon` | `()` | Signal the daemon to exit. For tests / shutdown hooks. | [src](../../../core/services/process_watcher.py#L609) |

## `core/services/producer_novelty.py`
_core/services/producer_novelty.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `infer_caller` | `()` | Gæt den originerende service fra call-stacken når cadence-thread-local mangler (fx | [src](../../../core/services/producer_novelty.py#L34) |
| function | `set_producer` | `(name)` | Sæt hvilken producer der kører NU (cadence-tråden). Self-safe. | [src](../../../core/services/producer_novelty.py#L58) |
| function | `clear_producer` | `()` | — | [src](../../../core/services/producer_novelty.py#L66) |
| function | `get_producer` | `()` | — | [src](../../../core/services/producer_novelty.py#L73) |
| function | `_similarity` | `(a, b)` | — | [src](../../../core/services/producer_novelty.py#L77) |
| function | `record_output` | `(producer, text)` | Registrér en producers LLM-output + mål nyhed = 1 - (max-lighed vs dens seneste N). | [src](../../../core/services/producer_novelty.py#L84) |
| function | `snapshot` | `()` | Read-only overblik: pr. producer antal kald + gennemsnitlig nyhed. Lav avg = repetitiv | [src](../../../core/services/producer_novelty.py#L115) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/producer_novelty.py#L127) |

## `core/services/promise_ledger.py`
_Promise-ledger (Bjørn-gate) — 16. jun 2026._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_promise` | `(session_id, text, *, now=…)` | Notér at Jarvis lovede en handling i `session_id`. Capper til de seneste N. | [src](../../../core/services/promise_ledger.py#L22) |
| function | `pending_promises` | `(session_id, *, within_s=…, now=…)` | Ikke-forældede løfter for `session_id` (nyeste sidst). [] ved fejl/tomt. | [src](../../../core/services/promise_ledger.py#L41) |
| function | `clear_promises` | `(session_id)` | Ryd løfterne for en session (fx når Bjørn bekræfter de er indfriet). | [src](../../../core/services/promise_ledger.py#L62) |

## `core/services/prompt_cache_probe.py`
_Prompt-cache-sonde — find hvad der bryder prefix-cachen MELLEM to rigtige ture._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProbeVerdict` | `` | Resultatet af at sammenligne to beskeds-arrays. | [src](../../../core/services/prompt_cache_probe.py#L47) |
| method | `ProbeVerdict.as_line` | `(self)` | — | [src](../../../core/services/prompt_cache_probe.py#L61) |
| function | `flatten` | `(items)` | Fold provider-item-formen ud til (rolle, tekst). | [src](../../../core/services/prompt_cache_probe.py#L73) |
| function | `compare` | `(prev, cur)` | Find hvor langt det byte-identiske prefix rækker. Ren funktion. | [src](../../../core/services/prompt_cache_probe.py#L97) |
| function | `_nearby_sections` | `(text, offset)` | De sidste sektions-overskrifter før bruddet — peger på synderen. | [src](../../../core/services/prompt_cache_probe.py#L130) |
| function | `enabled` | `()` | Sonden er slukket med mindre gate-filen findes. | [src](../../../core/services/prompt_cache_probe.py#L147) |
| function | `probe` | `(items, *, session_id=…, source=…)` | Skriv turens beskeds-array og sammenlign med forrige tur. | [src](../../../core/services/prompt_cache_probe.py#L155) |

## `core/services/prompt_contract.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_track_relevance_decision` | `(decision)` | — | [src](../../../core/services/prompt_contract.py#L44) |
| function | `_track_memory_selection` | `(selection, mode, candidate_count)` | — | [src](../../../core/services/prompt_contract.py#L76) |
| function | `build_runtime_memory_selection_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L99) |
| function | `build_runtime_relevance_decision_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L126) |
| function | `build_runtime_inner_visible_prompt_bridge_surface` | `(*, limit=…)` | — | [src](../../../core/services/prompt_contract.py#L151) |
| class | `PromptAssembly` | `` | — | [src](../../../core/services/prompt_contract.py#L223) |
| class | `PromptRelevanceDecision` | `` | — | [src](../../../core/services/prompt_contract.py#L238) |
| function | `_phase_timeout` | `(elapsed, *, max_s=…)` | Deadline for én phase-future: cappet mod resten af det globale assembly-budget, | [src](../../../core/services/prompt_contract.py#L284) |
| function | `_permissive_relevance` | `(mode=…)` | All-on relevance-default når relevance-futuren timer ud — inkludér ALT (berigelse | [src](../../../core/services/prompt_contract.py#L292) |
| class | `InnerVisiblePromptBridgeDecision` | `` | — | [src](../../../core/services/prompt_contract.py#L312) |
| function | `_safe_build_cognitive_state_for_prompt` | `(*, compact)` | — | [src](../../../core/services/prompt_contract.py#L329) |
| function | `_safe_build_self_state_block` | `()` | — | [src](../../../core/services/prompt_contract.py#L339) |
| function | `_honesty_rules_section` | `(*, compact)` | Consolidated into VISIBLE_CHAT_RULES.md (2026-07-22, prompt audit #1). | [src](../../../core/services/prompt_contract.py#L348) |
| function | `_compact_curated_index` | `(raw)` | Render the stored curated INDEX.md compactly for the prompt (audit #2, | [src](../../../core/services/prompt_contract.py#L365) |
| function | `_curated_memory_index_section` | `(name=…)` | Kurateret memory-INDEX (spec 2026-07-10 Spec B): altid-loadet én-linjers for | [src](../../../core/services/prompt_contract.py#L387) |
| function | `build_visible_stable_prefix` | `(*, provider=…, model=…, name=…, compact=…)` | Build ONLY the stable cacheable prefix of a visible chat prompt. | [src](../../../core/services/prompt_contract.py#L425) |
| function | `_device_awareness_on` | `()` | — | [src](../../../core/services/prompt_contract.py#L523) |
| function | `_device_presence_line` | `(user_id)` | Hvilken enhed Bjørn er ved (routing-awareness). Killswitch-gatet, best-effort. | [src](../../../core/services/prompt_contract.py#L531) |
| function | `_latest_user_msg_id` | `(session_id)` | Cheap indexed lookup of the newest USER message id for the session. It's the SAME | [src](../../../core/services/prompt_contract.py#L572) |
| function | `build_visible_chat_prompt_assembly` | `(*, provider, model, user_message, session_id=…, name=…, runtime_self_report_context=…)` | Turn-scoped cached wrapper — see _ASSEMBLY_TURN_CACHE. Reuses round 0's assembly for | [src](../../../core/services/prompt_contract.py#L593) |
| function | `_build_visible_chat_prompt_assembly_impl` | `(*, provider, model, user_message, session_id=…, name=…, runtime_self_report_context=…)` | — | [src](../../../core/services/prompt_contract.py#L630) |
| function | `build_heartbeat_prompt_assembly` | `(*, heartbeat_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3081) |
| function | `build_future_agent_task_prompt_assembly` | `(*, task_brief, agent_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3233) |
| function | `_relevance_cache_key` | `(text, mode, compact, name)` | Build a string cache key for shared_cache (cross-worker visibility). | [src](../../../core/services/prompt_contract.py#L3363) |
| function | `build_prompt_relevance_decision` | `(text, *, mode, compact, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3370) |
| function | `_bounded_nl_relevance_backend` | `(*, text, mode, compact, name)` | — | [src](../../../core/services/prompt_contract.py#L3490) |
| function | `_track_inner_visible_prompt_bridge` | `(decision)` | — | [src](../../../core/services/prompt_contract.py#L3505) |
| function | `_build_inner_visible_prompt_bridge_decision` | `(*, user_message, mode, compact, relevance)` | — | [src](../../../core/services/prompt_contract.py#L3535) |
| function | `_latest_active_inner_visible_support_signal` | `()` | — | [src](../../../core/services/prompt_contract.py#L3614) |
| function | `_inner_visible_support_bridge_is_redundant` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3622) |
| function | `_inner_visible_support_prompt_line` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3632) |
| function | `_self_mutation_lineage_section` | `()` | Returns a compact section about recent self-changes, or None if none. | [src](../../../core/services/prompt_contract.py#L3693) |
| function | `_channel_workspace_path` | `()` | — | [src](../../../core/services/prompt_contract.py#L3725) |
| function | `_channel_context_section` | `(session_id)` | Returns current channel context for the prompt, or None. | [src](../../../core/services/prompt_contract.py#L3729) |
| function | `_visible_chat_rules_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L3809) |
| function | `_self_correction_nudges_section` | `(*, compact)` | Consolidated into VISIBLE_CHAT_RULES.md (2026-07-22, prompt audit #1). | [src](../../../core/services/prompt_contract.py#L3826) |
| function | `_output_discipline_instruction` | `(*, strength)` | Tiered output discipline (harness Part 1). BOTH tiers get 'synthesize & stop' (safe for weak — | [src](../../../core/services/prompt_contract.py#L3837) |
| function | `_central_notices_section` | `()` | Medium-niveau Central-notices til Jarvis (spec 2026-06-23 §2). IKKE severe (dem | [src](../../../core/services/prompt_contract.py#L3857) |
| function | `_pending_promises_section` | `(session_id)` | Bjørn-gate (16. jun 2026): rejs Jarvis' åbne fremtids-løfter prominent, så | [src](../../../core/services/prompt_contract.py#L3888) |
| function | `_connected_connectors_section` | `()` | Surface brugerens FORBUNDNE plugins/connectors så Jarvis ved han har adgang. | [src](../../../core/services/prompt_contract.py#L3917) |
| function | `_open_questions_section` | `(*, limit=…)` | Surface curiosity_daemon._open_questions into the visible prompt. | [src](../../../core/services/prompt_contract.py#L3962) |
| function | `_time_pin_section` | `()` | Prominent, unmissable time indicator — placed high in every system prompt. | [src](../../../core/services/prompt_contract.py#L3991) |
| function | `_quick_facts_section` | `(*, workspace_dir, max_chars=…)` | Always-on facts block. Unlike MEMORY.md, this is NOT relevance-filtered — | [src](../../../core/services/prompt_contract.py#L4029) |
| function | `_visible_capability_truth_instruction` | `(*, compact)` | — | [src](../../../core/services/prompt_contract.py#L4052) |
| function | `_visible_capability_id_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L4074) |
| function | `_local_model_behavior_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L4082) |
| function | `_visible_finitude_context_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L4134) |
| function | `_visible_support_signal_sections` | `(*, compact, include, user_message=…, session_id=…)` | — | [src](../../../core/services/prompt_contract.py#L4144) |
| function | `_proactive_outbound_section` | `()` | Recent proactive messages Jarvis sent (substrate for user-reply context). | [src](../../../core/services/prompt_contract.py#L4185) |
| function | `_agreement_streak_section` | `()` | Surface last 3+ agreement-opener assistant replies as substrate. | [src](../../../core/services/prompt_contract.py#L4201) |
| function | `_emotion_concept_tone_section` | `()` | Affect-relevant runtime substrate (replaces tone-hint injection). | [src](../../../core/services/prompt_contract.py#L4215) |
| function | `_emotion_signal_section` | `()` | Aktive emotion concepts som data — giver Jarvis sit eget følelsespanel. | [src](../../../core/services/prompt_contract.py#L4263) |
| function | `_experience_substrate_section` | `(*, user_message=…, session_id=…)` | Nylige lignende situationer (embedding-retrieval substrat). | [src](../../../core/services/prompt_contract.py#L4365) |
| function | `_delegated_continuity_summary` | `(context)` | — | [src](../../../core/services/prompt_contract.py#L4476) |
| function | `_should_include_memory` | `(text, *, mode)` | — | [src](../../../core/services/prompt_contract.py#L4504) |
| function | `_should_include_guidance` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4538) |
| function | `_should_include_transcript` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4556) |
| function | `_should_include_continuity` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4575) |
| function | `prompt_mode_loader_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L4588) |

## `core/services/prompt_evolution.py`
_Prompt evolution — versioning + rollback safety net for workspace prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/prompt_evolution.py#L41) |
| function | `_ensure_table` | `()` | Create workspace_prompt_versions table if missing. Idempotent. | [src](../../../core/services/prompt_evolution.py#L45) |
| function | `snapshot_workspace_file` | `(*, filename, content, reason=…, workspace_id=…, created_by=…)` | Persist a snapshot of a workspace file. | [src](../../../core/services/prompt_evolution.py#L70) |
| function | `list_prompt_history` | `(*, filename, limit=…)` | Return recent versions of a file, newest first. Excludes content | [src](../../../core/services/prompt_evolution.py#L145) |
| function | `get_version` | `(*, version_id)` | Fetch a specific version including full content. | [src](../../../core/services/prompt_evolution.py#L171) |
| function | `rollback_to_version` | `(*, workspace_dir, filename, version_id, snapshot_current_first=…)` | Restore a workspace file to a specific historical version. | [src](../../../core/services/prompt_evolution.py#L190) |
| function | `recommend_rollback_after_change` | `(*, filename, hours=…)` | Score recent telemetry to assess whether the most recent change to | [src](../../../core/services/prompt_evolution.py#L248) |

## `core/services/prompt_evolution_runtime.py`
_Bounded runtime prompt evolution / self-authored prompt proposals light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_prompt_evolution_runtime` | `(*, trigger=…, last_visible_at=…)` | Run one bounded prompt-evolution proposal pass. | [src](../../../core/services/prompt_evolution_runtime.py#L28) |
| function | `build_prompt_evolution_from_inputs` | `(*, dream_articulation, dream_influence, self_model_surface, inner_voice_state, emergent_surface, embodied_state, loop_runtime, adaptive_learning, guided_learning, adaptive_reasoning, now=…)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L179) |
| function | `build_prompt_evolution_runtime_surface` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L424) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L486) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L524) |
| function | `_latest_prompt_evolution_proposal` | `()` | — | [src](../../../core/services/prompt_evolution_runtime.py#L548) |
| function | `_choose_proposal_type` | `(*, dream_articulation, dream_influence, self_model_surface, embodied_state, loop_runtime, adaptive_learning)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L555) |
| function | `_target_asset_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L601) |
| function | `_prompt_target_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L611) |
| function | `_build_anchor` | `(*, dream_articulation, self_model_surface, loop_runtime)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L621) |
| function | `_build_rationale` | `(*, proposal_type, target_asset, learning_influence, dream_influence, candidate_fragment, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L651) |
| function | `_proposal_state_from_type` | `(proposal_type)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L705) |
| function | `_confidence_from_inputs` | `(*, proposal_type, source_input_count, self_model_surface)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L713) |
| function | `_build_learning_influence` | `(adaptive_learning)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L728) |
| function | `_build_dream_influence_summary` | `(dream_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L738) |
| function | `_build_fragment_co_influence` | `(*, adaptive_learning, dream_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L748) |
| function | `_build_candidate_fragment` | `(*, proposal_type, target_asset, prompt_target, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, embodied_state)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L772) |
| function | `_build_fragment_grounding` | `(*, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L843) |
| function | `_build_review_light` | `(*, proposal_type, prompt_target, adaptive_learning, dream_influence, guided_learning, adaptive_reasoning, embodied_state, fragment_co_influence)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L874) |
| function | `_sanitize_fragment` | `(text)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L981) |
| function | `_support_fields_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L985) |
| function | `_learning_influence_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L998) |
| function | `_fragment_grounding_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1011) |
| function | `_dream_influence_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1024) |
| function | `_review_light_from_latest` | `(latest)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1036) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1048) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/prompt_evolution_runtime.py#L1077) |

## `core/services/prompt_heartbeat_self_knowledge.py`
_Heartbeat self-knowledge section builder._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_heartbeat_self_knowledge_section` | `()` | Build a compact self-knowledge section for the heartbeat prompt. | [src](../../../core/services/prompt_heartbeat_self_knowledge.py#L19) |

## `core/services/prompt_mutation_loop.py`
_Prompt Mutation Loop — apply, score, auto-rollback on negative score._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L55) |
| function | `_workspace_path` | `(target_file)` | — | [src](../../../core/services/prompt_mutation_loop.py#L59) |
| function | `_load` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L63) |
| function | `_save` | `(items)` | — | [src](../../../core/services/prompt_mutation_loop.py#L77) |
| class | `PromptMutationError` | `` | — | [src](../../../core/services/prompt_mutation_loop.py#L91) |
| function | `_check_target` | `(target_file)` | Raise PromptMutationError if the target is not safely mutable. | [src](../../../core/services/prompt_mutation_loop.py#L95) |
| function | `_active_mutation_for_file` | `(items, target_file)` | — | [src](../../../core/services/prompt_mutation_loop.py#L111) |
| function | `_recent_mutation_for_file` | `(items, target_file, now)` | — | [src](../../../core/services/prompt_mutation_loop.py#L121) |
| function | `_snapshot_signals` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L139) |
| function | `_score_mutation` | `(item)` | — | [src](../../../core/services/prompt_mutation_loop.py#L171) |
| function | `apply_mutation` | `(*, target_file, new_content, source=…, reason=…, metadata=…)` | Write new_content to target_file, snapshotting previous content. | [src](../../../core/services/prompt_mutation_loop.py#L194) |
| function | `rollback_mutation` | `(mutation_id, *, note=…, auto=…)` | Restore the file to its pre-mutation content. Returns True on success. | [src](../../../core/services/prompt_mutation_loop.py#L269) |
| function | `record_mutation` | `(*, target_file, source=…, reason=…, metadata=…)` | Record that a mutation was applied externally (no file write). | [src](../../../core/services/prompt_mutation_loop.py#L321) |
| function | `resolve_mutation` | `(mutation_id, *, outcome, note=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L359) |
| function | `_update_and_maybe_auto_rollback` | `(item, now)` | Returns 'unchanged' | 'updated' | 'auto_rolled_back'. | [src](../../../core/services/prompt_mutation_loop.py#L376) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L423) |
| function | `list_mutations` | `(*, status=…, limit=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L446) |
| function | `get_mutation` | `(mutation_id, *, include_snapshot=…)` | — | [src](../../../core/services/prompt_mutation_loop.py#L457) |
| function | `list_evolvable_files` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L466) |
| function | `list_protected_files` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L470) |
| function | `build_prompt_mutation_loop_surface` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L476) |
| function | `_surface_summary` | `(monitoring, adopted, rolled_back, auto_rolled)` | — | [src](../../../core/services/prompt_mutation_loop.py#L508) |
| function | `build_prompt_mutation_loop_prompt_section` | `()` | — | [src](../../../core/services/prompt_mutation_loop.py#L528) |

## `core/services/prompt_observer.py`
_Prompt-cluster (Den Intelligente Central) — Phase 1: live on/off + trace for de_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_overrides` | `()` | Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build). | [src](../../../core/services/prompt_observer.py#L66) |
| function | `section_enabled` | `(label, *, blacklisted, overrides)` | Skal denne prompt-sektion med? | [src](../../../core/services/prompt_observer.py#L94) |
| function | `observe_discarded_content` | `(label, content)` | En slukket sektions indhold blev netop kasseret — prøvetag det. | [src](../../../core/services/prompt_observer.py#L104) |
| function | `observe_build` | `(*, lane, included, dropped_disabled, dropped_budget, dropped_error=…)` | Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget | [src](../../../core/services/prompt_observer.py#L120) |
| function | `observe_section_error` | `(label, error, *, lane=…)` | En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar). | [src](../../../core/services/prompt_observer.py#L146) |
| function | `set_section` | `(label, enabled)` | Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar. | [src](../../../core/services/prompt_observer.py#L160) |
| function | `list_overrides` | `()` | Read-only projektion af aktive overrides (til MC/debug). | [src](../../../core/services/prompt_observer.py#L168) |

## `core/services/prompt_relevance_backend.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_with_wall_clock_timeout` | `(fn, *, timeout)` | Run ``fn()`` in a daemon thread with a hard wall-clock deadline. | [src](../../../core/services/prompt_relevance_backend.py#L22) |
| class | `_BoundedLLMCall` | `` | Result of a bounded LLM call — neutral across Ollama / OllamaFreeAPI. | [src](../../../core/services/prompt_relevance_backend.py#L51) |
| function | `_call_bounded_relevance_llm` | `(prompt)` | Dispatch a bounded relevance/memory-selection prompt. | [src](../../../core/services/prompt_relevance_backend.py#L62) |
| function | `_call_openai_compat_relevance` | `(*, provider, prompt, model, timeout)` | Generic openai-compat relevance call (mistral, nim, openrouter, ...). | [src](../../../core/services/prompt_relevance_backend.py#L123) |
| function | `_call_opencode_relevance` | `(*, prompt, model, timeout)` | Call OpenCode Zen free models via the OpenAI-compatible cheap lane. | [src](../../../core/services/prompt_relevance_backend.py#L244) |
| function | `_call_ollamafreeapi_relevance` | `(*, prompt, model, timeout)` | OllamaFreeAPI silently drops its ``timeout`` kwarg, so we run the call | [src](../../../core/services/prompt_relevance_backend.py#L319) |
| function | `_call_local_ollama_relevance` | `(*, prompt)` | — | [src](../../../core/services/prompt_relevance_backend.py#L381) |
| class | `BoundedPromptRelevanceResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L445) |
| class | `BoundedPromptRelevanceAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L457) |
| class | `BoundedMemorySelectionResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L468) |
| class | `BoundedMemorySelectionAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L475) |
| function | `run_bounded_nl_prompt_relevance` | `(*, text, mode, compact, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L485) |
| function | `bounded_nl_prompt_relevance_smoke` | `(*, text, workspace_dir, mode=…, compact=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L556) |
| function | `run_bounded_nl_memory_entry_selection` | `(*, user_message, entries, max_lines, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L581) |
| function | `load_visible_relevance_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L658) |
| function | `load_visible_memory_selection_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L672) |
| function | `_resolve_relevance_target` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L686) |
| function | `_selected_relevance_model` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L706) |
| function | `_build_relevance_prompt` | `(*, instructions, text, mode, compact)` | — | [src](../../../core/services/prompt_relevance_backend.py#L712) |
| function | `_build_memory_selection_prompt` | `(*, instructions, user_message, entries, max_lines, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L733) |
| function | `_parse_relevance_response` | `(text, mode)` | — | [src](../../../core/services/prompt_relevance_backend.py#L758) |
| function | `_parse_memory_selection_response` | `(text, *, entry_count, max_lines)` | — | [src](../../../core/services/prompt_relevance_backend.py#L795) |
| function | `_bounded_memory_candidates` | `(entries)` | — | [src](../../../core/services/prompt_relevance_backend.py#L846) |
| function | `_coerce_bool` | `(value)` | — | [src](../../../core/services/prompt_relevance_backend.py#L857) |

## `core/services/prompt_section_impact.py`
_Lightweight prompt-section answer-impact telemetry._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SectionImpact` | `` | — | [src](../../../core/services/prompt_section_impact.py#L19) |
| function | `_terms` | `(text)` | — | [src](../../../core/services/prompt_section_impact.py#L27) |
| function | `estimate_section_impact` | `(label, section_text, answer_text)` | — | [src](../../../core/services/prompt_section_impact.py#L35) |
| function | `observe_answer_impact` | `(*, run_id, answer_text, sections)` | — | [src](../../../core/services/prompt_section_impact.py#L50) |
| function | `remember_prompt_sections` | `(*, session_id, sections)` | — | [src](../../../core/services/prompt_section_impact.py#L75) |
| function | `observe_last_prompt_answer_impact` | `(*, session_id, run_id, answer_text)` | — | [src](../../../core/services/prompt_section_impact.py#L86) |

## `core/services/prompt_section_reevaluation.py`
_Revurderings-løkke for slukkede prompt-sektioner._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_digest` | `(text)` | — | [src](../../../core/services/prompt_section_reevaluation.py#L54) |
| function | `_lines` | `(text)` | — | [src](../../../core/services/prompt_section_reevaluation.py#L58) |
| function | `substance` | `(text)` | Scorer om indholdet er værd at læse. ``{score: 0..1, reasons: [...]}``. | [src](../../../core/services/prompt_section_reevaluation.py#L62) |
| function | `observe_discarded` | `(label, content)` | Prøvetag indhold som blacklisten netop har forkastet. Gratis og selv-sikker. | [src](../../../core/services/prompt_section_reevaluation.py#L105) |
| function | `_read_samples` | `()` | — | [src](../../../core/services/prompt_section_reevaluation.py#L148) |
| function | `evaluate` | `()` | Vurdér alle prøvetagne, slukkede kanaler. Ren læsning — tænder intet. | [src](../../../core/services/prompt_section_reevaluation.py#L173) |
| function | `_review_enabled` | `()` | — | [src](../../../core/services/prompt_section_reevaluation.py#L225) |
| function | `_review` | `(candidates)` | Lad Jarvis dømme sine egne slukkede kanaler. Ét billigt kald pr. sweep (≤1/døgn). | [src](../../../core/services/prompt_section_reevaluation.py#L241) |
| function | `_propose` | `(candidates)` | Læg forslaget hvor Bjørn og Centralen kan se det — med sin egen begrundelse. | [src](../../../core/services/prompt_section_reevaluation.py#L303) |
| function | `maybe_run_sweep` | `()` | Kør vurderingen højst én gang i døgnet. Ren DB-læsning + aritmetik (~ms). | [src](../../../core/services/prompt_section_reevaluation.py#L337) |
| function | `reevaluation_surface` | `()` | Overflade til Centralen/MC: hvilke slukkede kanaler fortjener et nyt blik? | [src](../../../core/services/prompt_section_reevaluation.py#L363) |

## `core/services/prompt_support_signals.py`
_Bounded inner-layer support signal builders._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_private_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L37) |
| function | `_growth_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L54) |
| function | `_self_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L72) |
| function | `_retained_memory_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L89) |
| function | `_reflection_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L117) |
| function | `_world_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L163) |
| function | `_goal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L209) |
| function | `_runtime_awareness_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L256) |
| function | `_development_focus_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L302) |
| function | `_temporal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L349) |
| function | `_reflection_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L366) |
| function | `_world_model_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L377) |
| function | `_goal_direction_label` | `(goal_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L386) |
| function | `_runtime_awareness_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L394) |
| function | `_development_focus_direction_label` | `(focus_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L407) |

## `core/services/prompt_variant_tracker.py`
_Prompt variant tracker — log per-variant performance for self-improvement._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `log_variant_outcome` | `(*, scope, variant_label, outcome_score, notes=…)` | Record a variant's outcome. scope is e.g. 'awareness.tier_recommendation'. | [src](../../../core/services/prompt_variant_tracker.py#L39) |
| function | `variant_performance` | `(*, scope=…, min_samples=…)` | Aggregate per-variant performance, optionally filtered by scope. | [src](../../../core/services/prompt_variant_tracker.py#L76) |
| function | `winning_variant` | `(scope, *, min_samples=…)` | Return the best-performing variant for a scope, or None if not enough data. | [src](../../../core/services/prompt_variant_tracker.py#L119) |
| function | `_exec_log_variant_outcome` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L128) |
| function | `_exec_variant_performance` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L137) |

## `core/services/proposal_classifier.py`
_Proposal classifier — detects action impulses in thought fragments and scores destructiveness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_fragment` | `(fragment)` | Classify a thought fragment for action impulses. | [src](../../../core/services/proposal_classifier.py#L59) |

## `core/services/proprioception_metrics.py`
_Proprioception Metrics — process-level body sense._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_psutil` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L32) |
| function | `_current_snapshot` | `()` | Sample current process stats. | [src](../../../core/services/proprioception_metrics.py#L40) |
| function | `_measure_self_latency_ms` | `()` | Measure trivial self-dispatch as a crude latency proxy. | [src](../../../core/services/proprioception_metrics.py#L70) |
| function | `_emit` | `(kind, payload)` | — | [src](../../../core/services/proprioception_metrics.py#L83) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/proprioception_metrics.py#L91) |
| function | `recent_snapshots` | `(*, limit=…)` | — | [src](../../../core/services/proprioception_metrics.py#L134) |
| function | `build_proprioception_metrics_surface` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L138) |
| function | `_surface_summary` | `(current, rss_trend)` | — | [src](../../../core/services/proprioception_metrics.py#L171) |
| function | `build_proprioception_metrics_prompt_section` | `()` | Only surfaces when something is actively worth noticing. | [src](../../../core/services/proprioception_metrics.py#L187) |
| function | `reset_proprioception_metrics` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L207) |

## `core/services/prose_tool_calls.py`
_Parser for prosa-emitterede tool-kald (cluster: tool-leak-fix 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_match_json_object` | `(s, start)` | s[start] skal være '{'. Returnér (objekt-streng, slut-index) via brace-matching | [src](../../../core/services/prose_tool_calls.py#L26) |
| function | `extract_prose_tool_calls` | `(text, valid_tool_names)` | Find `[navn]: {json}`-prosa-kald hvor navn er et kendt tool og args er et | [src](../../../core/services/prose_tool_calls.py#L55) |

## `core/services/provider_autodiscovery.py`
_Provider auto-discovery (spec Fase C). Dagligt scan af providers' /models,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_list_remote_models` | `(provider)` | Modeller providerens /models-endpoint rapporterer. [] ved fejl. | [src](../../../core/services/provider_autodiscovery.py#L18) |
| function | `_known_models` | `()` | Modeller allerede i provider_router.json (uanset lane). | [src](../../../core/services/provider_autodiscovery.py#L28) |
| function | `_stage_pending` | `(provider, model)` | Skriv (provider, model) til pending_models-staging, status='pending'. | [src](../../../core/services/provider_autodiscovery.py#L38) |
| function | `_add_to_router` | `(provider, model)` | Faktisk optagelse i routbar pool. Kaldes KUN af promote_pending efter gates. | [src](../../../core/services/provider_autodiscovery.py#L56) |
| function | `_configured_providers` | `()` | Alle providers i provider_router.json (til daglig re-scan). [] ved fejl. | [src](../../../core/services/provider_autodiscovery.py#L69) |
| function | `tick_provider_autodiscovery_daemon` | `()` | Fase C daemon-tick: dagligt scan af alle providers' /models → nye modeller til | [src](../../../core/services/provider_autodiscovery.py#L80) |
| function | `discover_provider` | `(provider)` | Scan provider, stage nye modeller. Returnér de nye (staged). Auto-adder ALDRIG. | [src](../../../core/services/provider_autodiscovery.py#L100) |
| function | `_smoke_ok` | `(provider, model)` | Svarer modellen på et minimalt kald? | [src](../../../core/services/provider_autodiscovery.py#L109) |
| function | `_is_free` | `(provider, model)` | Konservativ gratis-verifikation. Default False (governed — hellere afvise). | [src](../../../core/services/provider_autodiscovery.py#L125) |
| function | `_score_model` | `(provider, model)` | Seed kvalitets-score (§4.4). Grov til at komme i gang. | [src](../../../core/services/provider_autodiscovery.py#L130) |
| function | `promote_pending` | `(provider, model, *, min_score=…)` | Gated promotion: kræver smoke + gratis + score ≥ tærskel. Kun da optages | [src](../../../core/services/provider_autodiscovery.py#L135) |

## `core/services/provider_circuit_breaker.py`
_Provider circuit breaker — skip primaries that have been failing recently._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(provider, model)` | — | [src](../../../core/services/provider_circuit_breaker.py#L39) |
| function | `_prune_old_failures` | `(failures, now)` | — | [src](../../../core/services/provider_circuit_breaker.py#L43) |
| function | `record_failure` | `(provider, model)` | Record a primary-call failure. Returns updated state for this key. | [src](../../../core/services/provider_circuit_breaker.py#L49) |
| function | `record_success` | `(provider, model)` | Clear failure tracking on success — provider seems healthy again. | [src](../../../core/services/provider_circuit_breaker.py#L67) |
| function | `should_skip` | `(provider, model)` | True when breaker is open for this (provider, model). | [src](../../../core/services/provider_circuit_breaker.py#L77) |
| function | `breaker_state` | `()` | Observability snapshot — returns open breakers + recent failure counts. | [src](../../../core/services/provider_circuit_breaker.py#L95) |
| function | `reset_all` | `()` | Test/admin helper — clear all state. | [src](../../../core/services/provider_circuit_breaker.py#L128) |
| class | `_PPState` | `` | Per-provider breaker-state (consecutive-i-træk-state-maskine). | [src](../../../core/services/provider_circuit_breaker.py#L160) |
| method | `_PPState.__init__` | `(self, threshold, cooldown_s, window_s)` | — | [src](../../../core/services/provider_circuit_breaker.py#L168) |
| class | `_PerProviderBreaker` | `` | Proces-lokal per-provider-keyed breaker. Trådsikker, self-safe. | [src](../../../core/services/provider_circuit_breaker.py#L179) |
| method | `_PerProviderBreaker.__init__` | `(self, *, threshold=…, cooldown_s=…, window_s=…)` | — | [src](../../../core/services/provider_circuit_breaker.py#L189) |
| method | `_PerProviderBreaker._key` | `(provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L204) |
| method | `_PerProviderBreaker.configure` | `(self, provider_id, *, threshold=…, cooldown_s=…, window_s=…)` | Per-provider-tærskler (ofa/arko bevarer deres historiske tal). | [src](../../../core/services/provider_circuit_breaker.py#L207) |
| method | `_PerProviderBreaker._state` | `(self, pid)` | — | [src](../../../core/services/provider_circuit_breaker.py#L235) |
| method | `_PerProviderBreaker.record_failure` | `(self, provider_id, *, now=…)` | Fejl → opdatér state. True hvis breakeren NETOP åbnede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L247) |
| method | `_PerProviderBreaker.record_success` | `(self, provider_id)` | Success → luk (reset). True hvis den netop lukkede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L273) |
| method | `_PerProviderBreaker.is_open` | `(self, provider_id, *, now=…)` | OPEN nu (→ kort-slut)? Cooldown udløbet → half-open (slip én probe → | [src](../../../core/services/provider_circuit_breaker.py#L288) |
| method | `_PerProviderBreaker.snapshot` | `(self, provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L306) |
| method | `_PerProviderBreaker.reset_all` | `(self)` | — | [src](../../../core/services/provider_circuit_breaker.py#L323) |
| function | `_observe_pp` | `(nerve, provider_id, **data)` | Observér en per-provider breaker-kant til Centralen (cluster="stream"). | [src](../../../core/services/provider_circuit_breaker.py#L332) |
| function | `pp_configure` | `(provider_id, **kw)` | Sæt per-provider-tærskler på den delte breaker (ofa/arko-løft). | [src](../../../core/services/provider_circuit_breaker.py#L346) |
| function | `pp_record_failure` | `(provider_id)` | Registrér en provider-fejl på den DELTE per-provider breaker + observér | [src](../../../core/services/provider_circuit_breaker.py#L351) |
| function | `pp_record_success` | `(provider_id)` | Registrér success på den delte per-provider breaker + observér close-kant. | [src](../../../core/services/provider_circuit_breaker.py#L366) |
| function | `pp_is_open` | `(provider_id)` | Er ``provider_id``'s delte breaker OPEN lige nu? (Fail-open.) | [src](../../../core/services/provider_circuit_breaker.py#L374) |
| function | `pp_snapshot` | `(provider_id)` | Debug/observe-snapshot af den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L379) |
| function | `pp_reset_all` | `()` | Test/admin: nulstil HELE den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L384) |

