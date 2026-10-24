# `core.services.22` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/regulation_homeostasis_signal_tracking.py`
_Regulation/homeostasis signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_regulation_homeostasis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L43) |
| function | `refresh_runtime_regulation_homeostasis_signal_statuses` | `()` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L77) |
| function | `build_runtime_regulation_homeostasis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L81) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L85) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L216) |
| function | `_latest_initiative_tension_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L226) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L238) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L250) |
| function | `_latest_inner_visible_support_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L262) |
| function | `_derive_regulation_pressure` | `(*, state_pressure, tension_type, contradiction_pressure)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L274) |
| function | `_derive_regulation_watchfulness` | `(*, contradiction_status, contradiction_pressure, visible_watchfulness)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L285) |
| function | `_derive_regulation_pacing` | `(*, pressure, watchfulness, curiosity_pull)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L298) |
| function | `_derive_regulation_state` | `(*, state_tone, pressure, watchfulness, pacing)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L313) |
| function | `_bounded_regulation_summary` | `(*, focus, regulation_state, regulation_pressure, regulation_watchfulness, regulation_pacing)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L329) |
| function | `_grounding_mode` | `(*, has_tension, has_curiosity, has_executive_contradiction, has_inner_visible_support)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L344) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L364) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L389) |
| function | `_regulation_homeostasis_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L411) |
| function | `_regulation_homeostasis_observe_surface` | `(surface)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L432) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L446) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L450) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L460) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L472) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L484) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L492) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L506) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L518) |

## `core/services/relation_continuity_signal_tracking.py`
_Relation-continuity signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_relation_continuity_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L38) |
| function | `refresh_runtime_relation_continuity_signal_statuses` | `()` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L64) |
| function | `build_runtime_relation_continuity_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L68) |
| function | `_extract_relation_continuity_candidates` | `(*, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L72) |
| function | `_latest_user_understanding_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L185) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L195) |
| function | `_latest_chronicle_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L207) |
| function | `_latest_regulation_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L219) |
| function | `_derive_continuity_watchfulness` | `(*, relation_watchfulness, regulation_watchfulness)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L231) |
| function | `_derive_continuity_weight` | `(*, chronicle_weight, relation_confidence)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L237) |
| function | `_derive_continuity_state` | `(*, relation_state, continuity_alignment, continuity_watchfulness, continuity_weight)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L245) |
| function | `_continuity_summary` | `(*, focus, continuity_state, continuity_alignment, continuity_watchfulness, continuity_weight)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L261) |
| function | `_grounding_mode` | `(*, has_chronicle_brief, has_chronicle_signal, has_regulation)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L276) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L288) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L310) |
| function | `_relation_continuity_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L326) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L347) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L351) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L361) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L373) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L385) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L397) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L405) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L413) |

## `core/services/relation_dynamics.py`
_Relation Dynamics — pattern-recognition on people, not just facts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/relation_dynamics.py#L32) |
| function | `_load` | `()` | — | [src](../../../core/services/relation_dynamics.py#L37) |
| function | `_save` | `(data)` | — | [src](../../../core/services/relation_dynamics.py#L51) |
| function | `_recent_runs` | `(days=…, limit=…)` | — | [src](../../../core/services/relation_dynamics.py#L63) |
| function | `_time_patterns` | `(runs)` | — | [src](../../../core/services/relation_dynamics.py#L84) |
| function | `_topic_patterns` | `(runs)` | — | [src](../../../core/services/relation_dynamics.py#L120) |
| function | `_message_length_stats` | `(runs)` | — | [src](../../../core/services/relation_dynamics.py#L130) |
| function | `_engagement_trend` | `(runs)` | Compare last-week run count vs previous-week. | [src](../../../core/services/relation_dynamics.py#L144) |
| function | `_warmth_from_sources` | `()` | Pull trust-trajectory tail from relationship_texture as warmth proxy. | [src](../../../core/services/relation_dynamics.py#L174) |
| function | `_vibe_from_recent` | `(runs)` | — | [src](../../../core/services/relation_dynamics.py#L189) |
| function | `_recompute` | `()` | — | [src](../../../core/services/relation_dynamics.py#L206) |
| function | `get_relation_dynamics` | `()` | — | [src](../../../core/services/relation_dynamics.py#L223) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/relation_dynamics.py#L236) |
| function | `build_relation_dynamics_surface` | `()` | — | [src](../../../core/services/relation_dynamics.py#L244) |
| function | `_surface_summary` | `(r)` | — | [src](../../../core/services/relation_dynamics.py#L265) |
| function | `build_relation_dynamics_prompt_section` | `()` | Surface only when trend is noteworthy (rising, cooling, dormant). | [src](../../../core/services/relation_dynamics.py#L286) |

## `core/services/relation_map.py`
_Relation map — multi-tenant user theory of mind._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_relation_map` | `()` | Return full relation map. Auto-initializes primary user on first call. | [src](../../../core/services/relation_map.py#L59) |
| function | `ensure_primary_user` | `(*, user_id=…, display_name=…)` | Ensure primary user entry exists in relation map. | [src](../../../core/services/relation_map.py#L69) |
| function | `register_secondary_user` | `(*, user_id, display_name)` | Register a new secondary user in the relation map. | [src](../../../core/services/relation_map.py#L87) |
| function | `update_secondary_user_tom` | `(*, user_id, tom_snapshot)` | Update theory-of-mind snapshot for a secondary user. | [src](../../../core/services/relation_map.py#L118) |
| function | `get_user_theory_of_mind` | `(user_id)` | Return theory-of-mind for a user. | [src](../../../core/services/relation_map.py#L140) |
| function | `list_users` | `()` | Return all users in the relation map. Auto-initializes primary user. | [src](../../../core/services/relation_map.py#L164) |
| function | `build_relation_map_surface` | `()` | MC observability surface. | [src](../../../core/services/relation_map.py#L182) |
| function | `tick_relation_map_refresh` | `(*, trigger=…, last_visible_at=…)` | Periodisk opdatering af relation map. | [src](../../../core/services/relation_map.py#L197) |
| function | `_load_state` | `()` | — | [src](../../../core/services/relation_map.py#L280) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/relation_map.py#L285) |
| function | `_users` | `(state)` | — | [src](../../../core/services/relation_map.py#L289) |

## `core/services/relation_state_signal_tracking.py`
_Relation-state signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_relation_state_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L38) |
| function | `refresh_runtime_relation_state_signal_statuses` | `()` | — | [src](../../../core/services/relation_state_signal_tracking.py#L72) |
| function | `build_runtime_relation_state_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L76) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L80) |
| function | `_latest_user_understanding_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L200) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L210) |
| function | `_latest_regulation_homeostasis_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L220) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L230) |
| function | `_latest_inner_visible_support_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L242) |
| function | `_derive_relation_alignment` | `(*, user_confidence, user_signal_type, regulation_state, contradiction_status)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L254) |
| function | `_derive_relation_watchfulness` | `(*, regulation_watchfulness, contradiction_pressure, visible_watchfulness)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L268) |
| function | `_derive_relation_pressure` | `(*, regulation_pressure, contradiction_pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L281) |
| function | `_derive_relation_state` | `(*, alignment, watchfulness, pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L291) |
| function | `_relation_summary` | `(*, focus, relation_state, relation_alignment, relation_watchfulness, relation_pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L306) |
| function | `_grounding_mode` | `(*, has_private_state, has_regulation, has_executive_contradiction, has_inner_visible_support)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L321) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L341) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L367) |
| function | `_relation_state_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L390) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L411) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L419) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L429) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L441) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L453) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L465) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L473) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L481) |

## `core/services/relational_warmth.py`
_Relational Warmth — felt quality of who I'm talking to._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/relational_warmth.py#L55) |
| function | `_load` | `()` | — | [src](../../../core/services/relational_warmth.py#L60) |
| function | `_save` | `(data)` | — | [src](../../../core/services/relational_warmth.py#L106) |
| function | `_has_cue` | `(text, cues)` | — | [src](../../../core/services/relational_warmth.py#L118) |
| function | `observe_incoming_text` | `(text, *, relation_id=…)` | Register an incoming text from the user. Returns signal breakdown. | [src](../../../core/services/relational_warmth.py#L123) |
| function | `observe_outgoing_text` | `(text, *, relation_id=…)` | Register an outgoing text from Jarvis. Detects care signals. | [src](../../../core/services/relational_warmth.py#L155) |
| function | `_decay_over_time` | `(rel)` | Slowly decay playfulness and trust if no recent interaction. | [src](../../../core/services/relational_warmth.py#L176) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/relational_warmth.py#L194) |
| function | `get_relation` | `(relation_id=…)` | — | [src](../../../core/services/relational_warmth.py#L209) |
| function | `build_relational_warmth_surface` | `()` | — | [src](../../../core/services/relational_warmth.py#L214) |
| function | `_surface_summary` | `(rel)` | — | [src](../../../core/services/relational_warmth.py#L229) |
| function | `build_relational_warmth_prompt_section` | `()` | Surface register-shaping hint only when it should change tone. | [src](../../../core/services/relational_warmth.py#L237) |

## `core/services/relationship_texture.py`
_Relationship Texture — tracks the quality of the relationship over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_relationship_from_run` | `(*, run_id, user_message, assistant_response, outcome_status, turn_count=…)` | Analyze a run and update relationship texture. | [src](../../../core/services/relationship_texture.py#L45) |
| function | `update_relationship_async` | `(**kwargs)` | — | [src](../../../core/services/relationship_texture.py#L163) |
| function | `track_pushback_outcome` | `(*, jarvis_disagreed, user_was_right, topic=…)` | Track when Jarvis disagrees — and who was right. | [src](../../../core/services/relationship_texture.py#L170) |
| function | `derive_appropriate_autonomy_level` | `()` | Derive autonomy level from trust trajectory. | [src](../../../core/services/relationship_texture.py#L194) |
| function | `build_relationship_texture_surface` | `()` | — | [src](../../../core/services/relationship_texture.py#L213) |
| function | `_safe` | `(fn, **kwargs)` | — | [src](../../../core/services/relationship_texture.py#L230) |
| function | `_safe_json_list` | `(value)` | — | [src](../../../core/services/relationship_texture.py#L237) |
| function | `_safe_json_dict` | `(value)` | — | [src](../../../core/services/relationship_texture.py#L250) |

## `core/services/release_marker_signal_tracking.py`
_Release-marker signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_release_marker_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L38) |
| function | `refresh_runtime_release_marker_signal_statuses` | `()` | — | [src](../../../core/services/release_marker_signal_tracking.py#L48) |
| function | `build_runtime_release_marker_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L52) |
| function | `_extract_release_marker_candidates` | `(*, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L56) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L153) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L262) |
| function | `_release_marker_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L289) |
| function | `_derive_release_state` | `(*, metabolism_state, witness_status, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L313) |
| function | `_derive_release_direction` | `(*, release_state, witness_status, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L328) |
| function | `_derive_release_weight` | `(*, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L345) |
| function | `_release_summary` | `(*, focus, release_state, release_direction, release_weight)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L359) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L379) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L386) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L393) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L405) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L416) |

## `core/services/remembered_fact_signal_tracking.py`
_Remembered-fact signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_remembered_fact_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L42) |
| function | `refresh_runtime_remembered_fact_signal_statuses` | `()` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L84) |
| function | `build_runtime_remembered_fact_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L88) |
| function | `_extract_remembered_fact_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L92) |
| function | `_explicit_user_name_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L125) |
| function | `_explicit_project_anchor_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L155) |
| function | `_explicit_working_context_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L184) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L214) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L223) |
| function | `_remembered_fact_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L232) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L244) |
| function | `_extract_name_value` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L268) |
| function | `_is_project_anchor_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L281) |
| function | `_is_working_context_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L294) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L328) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L335) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L340) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L347) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L356) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L368) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L372) |

## `core/services/repeated_requests.py`
_Gentagne anmodninger → regel-forslag (lærings-sløjfe 2026-09-04, blok C)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/repeated_requests.py#L60) |
| function | `_stems` | `(text)` | Betydningsbærende ord, forkortet til deres første `_STEM_CHARS` tegn. | [src](../../../core/services/repeated_requests.py#L64) |
| function | `normalize` | `(text)` | Anmodningens stammer, sorteret — noeglen en anmodning gemmes under. | [src](../../../core/services/repeated_requests.py#L80) |
| function | `similarity` | `(a, b)` | Jaccard mellem to anmodningers stammer (0-1). | [src](../../../core/services/repeated_requests.py#L85) |
| function | `ensure_table` | `(conn)` | — | [src](../../../core/services/repeated_requests.py#L93) |
| function | `_row` | `(r)` | — | [src](../../../core/services/repeated_requests.py#L117) |
| function | `_sessions` | `(raw)` | — | [src](../../../core/services/repeated_requests.py#L121) |
| function | `note_request` | `(*, text, session_id=…, kind=…)` | Tæl én anmodning. Returnerer rækken plus ``matured`` når den nu er en regel-kandidat. | [src](../../../core/services/repeated_requests.py#L125) |
| function | `build_question` | `(*, text, mention_count, session_count, kind)` | Det ene spørgsmål Bjørn får at se. Konkret, med tallet der udløste det. | [src](../../../core/services/repeated_requests.py#L209) |
| function | `mark_asked` | `(request_id)` | — | [src](../../../core/services/repeated_requests.py#L224) |
| function | `record_decision` | `(*, request_id, accepted)` | Bjørns svar. Ja → linjen skrives i `## Kerne` med begrundelse. | [src](../../../core/services/repeated_requests.py#L236) |
| function | `surface_matured` | `(result, *, kind=…, session_id=…)` | Læg et modnet regel-forslag i den proaktive kø. Ét spørgsmål, én gang. | [src](../../../core/services/repeated_requests.py#L273) |
| function | `note_and_surface` | `(*, text, session_id=…, kind=…)` | Tæl, og stil spørgsmålet hvis anmodningen netop modnede. Self-safe. | [src](../../../core/services/repeated_requests.py#L303) |
| function | `counts` | `()` | — | [src](../../../core/services/repeated_requests.py#L315) |
| function | `build_repeated_requests_surface` | `()` | — | [src](../../../core/services/repeated_requests.py#L325) |

## `core/services/repo_index.py`
_Separat søgeindeks over repoets DOKUMENTATION — ikke kildekoden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | Repoets rod. Kan overstyres med JARVIS_REPO_ROOT (tests, worktrees). | [src](../../../core/services/repo_index.py#L97) |
| function | `_index_path` | `()` | Global sti — dokumentationen er den samme for alle brugere. | [src](../../../core/services/repo_index.py#L105) |
| function | `_is_excluded` | `(rel)` | — | [src](../../../core/services/repo_index.py#L110) |
| function | `repo_files` | `(root=…)` | Alle dokumentationsfiler der skal indekseres, sorteret. | [src](../../../core/services/repo_index.py#L117) |
| function | `_file_mtime` | `(path)` | — | [src](../../../core/services/repo_index.py#L143) |
| function | `_chunk_files` | `(files, root)` | Læs + chunk. Kun fil-I/O — ingen embedding. | [src](../../../core/services/repo_index.py#L150) |
| function | `_load_cached_vectors` | `(path)` | chunk-tekst → vektor fra eksisterende cache, til inkrementel reindeksering. | [src](../../../core/services/repo_index.py#L167) |
| function | `build_index` | `(*, root=…, force=…)` | Byg indekset og skriv cachen. Blokerer indtil embeddings er færdige. | [src](../../../core/services/repo_index.py#L185) |
| function | `_schedule_background_build` | `()` | Byg i baggrunden (fire-and-forget, kun én ad gangen). | [src](../../../core/services/repo_index.py#L261) |
| function | `_load_or_build` | `()` | (chunks, embeddings, mtimes). Blokerer aldrig på en fuld embedding. | [src](../../../core/services/repo_index.py#L282) |
| function | `_path_matches` | `(source, path_prefix)` | — | [src](../../../core/services/repo_index.py#L313) |
| function | `_area_weight` | `(source)` | Vægt for en chunk-kilde. Første match vinder, mest specifikke først. | [src](../../../core/services/repo_index.py#L352) |
| function | `_lexical_score` | `(query_terms, chunk)` | Andel af query-termer der optræder i chunk, sektion eller sti. | [src](../../../core/services/repo_index.py#L378) |
| function | `search_repo` | `(query, *, limit=…, path_prefix=…)` | Semantisk søgning i repoets dokumentation. | [src](../../../core/services/repo_index.py#L386) |
| function | `get_stats` | `()` | Indeksets tilstand uden at bygge noget. | [src](../../../core/services/repo_index.py#L456) |
| function | `invalidate` | `()` | Slet cachen, så næste søgning genopbygger. | [src](../../../core/services/repo_index.py#L494) |
| function | `_main` | `(argv=…)` | — | [src](../../../core/services/repo_index.py#L504) |

## `core/services/report_claim_guard.py`
_Efterproev det et barn PAASTAAR — Fase 6._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_opsloegere` | `(context)` | Vaelg den maskine paastanden skal efterproeves PAA. | [src](../../../core/services/report_claim_guard.py#L40) |
| function | `tjek_rapport` | `(text, *, agent_id=…, role=…, run_id=…, context=…)` | Efterproev en barne-rapports filstier og linjenumre. Kaster ALDRIG. | [src](../../../core/services/report_claim_guard.py#L83) |

## `core/services/research_contract.py`
_Typed contracts and source normalization for explicit research runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchPolicy` | `` | — | [src](../../../core/services/research_contract.py#L17) |
| class | `ResearchDecision` | `` | — | [src](../../../core/services/research_contract.py#L31) |
| class | `ResearchTask` | `` | — | [src](../../../core/services/research_contract.py#L44) |
| class | `ResearchPlan` | `` | — | [src](../../../core/services/research_contract.py#L51) |
| class | `ResearchSource` | `` | — | [src](../../../core/services/research_contract.py#L57) |
| class | `ResearchFinding` | `` | — | [src](../../../core/services/research_contract.py#L70) |
| class | `ResearchContract` | `` | — | [src](../../../core/services/research_contract.py#L79) |
| function | `_clean` | `(value)` | — | [src](../../../core/services/research_contract.py#L86) |
| function | `canonicalize_url` | `(raw)` | — | [src](../../../core/services/research_contract.py#L90) |
| function | `normalize_source` | `(value)` | — | [src](../../../core/services/research_contract.py#L107) |
| function | `load_research_contract` | `(query=…)` | Load the canonical skill deterministically; fall back without hiding it. | [src](../../../core/services/research_contract.py#L124) |

## `core/services/research_evidence_collector.py`
_Capture structured web-tool evidence for the active research run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `collecting_for` | `(run_id, *, task_id=…)` | — | [src](../../../core/services/research_evidence_collector.py#L14) |
| function | `_structured_sources` | `(tool_name, result)` | — | [src](../../../core/services/research_evidence_collector.py#L22) |
| function | `observe_web_result` | `(tool_name, result)` | — | [src](../../../core/services/research_evidence_collector.py#L38) |

## `core/services/research_ledger.py`
_Research-runnet synligt i session-ledgeren (spec Fase A4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/research_ledger.py#L42) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/research_ledger.py#L46) |
| function | `record_research_event` | `(session_id, *, event_id, event, payload=…)` | Skriv én research-hændelse i session-ledgeren. Kaster aldrig. | [src](../../../core/services/research_ledger.py#L51) |
| function | `record_run_started` | `(session_id, *, run_id, tier, query)` | Runnet er startet: tier og den oprindelige forespørgsel. | [src](../../../core/services/research_ledger.py#L96) |
| function | `record_run_completed` | `(session_id, *, run_id, sources, quality, timed_out, tool_calls=…)` | Runnet er slut: hvad det blev — kilder, kvalitetsdom, timeout, forbrug. | [src](../../../core/services/research_ledger.py#L106) |

## `core/services/research_orchestrator.py`
_Adaptive research coordinator around the existing visible and agent runtimes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_event` | `(kind, payload)` | — | [src](../../../core/services/research_orchestrator.py#L29) |
| function | `_setting` | `(name, default)` | — | [src](../../../core/services/research_orchestrator.py#L33) |
| function | `_facets` | `(message)` | De emneord planlægningen deler beskeden i — og som gaten måler dækning imod. | [src](../../../core/services/research_orchestrator.py#L47) |
| function | `_delta_text` | `(frame)` | Træk syntese-teksten ud af en `delta`-frame. Andre frames giver ''. | [src](../../../core/services/research_orchestrator.py#L55) |
| function | `_plan` | `(message, max_tasks)` | — | [src](../../../core/services/research_orchestrator.py#L77) |
| function | `_parse_plan` | `(text, max_tasks)` | Læs plannerens JSON til en ResearchTask-liste. Defensiv: [] ved mindste tvivl. | [src](../../../core/services/research_orchestrator.py#L108) |
| function | `_llm_plan` | `(message, max_tasks, facets)` | Fase C1: bed en billig model om delopgaver. None = kunne ikke → regex. | [src](../../../core/services/research_orchestrator.py#L151) |
| function | `_plan_tasks` | `(message, max_tasks, *, planner_enabled)` | Fase C1: LLM-planlægger med regex-fallback. | [src](../../../core/services/research_orchestrator.py#L176) |
| function | `_tool_calls_used` | `(run_id)` | Observerede værktøjskald i runnet. Defensiv: 0 hvis tællingen ikke kan læses. | [src](../../../core/services/research_orchestrator.py#L192) |
| function | `_clean_text` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L203) |
| function | `_confidence` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L207) |
| function | `_finding_from_text` | `(text, task_ordinal)` | Sidste udkast: hele teksten bliver ét fund med de URLs den bærer. | [src](../../../core/services/research_orchestrator.py#L212) |
| function | `_parse_findings` | `(text, task_ordinal)` | Fase B2: worker-svaret → `ResearchFinding`. | [src](../../../core/services/research_orchestrator.py#L229) |
| function | `_gap_objective` | `(query, findings)` | Fase B3: critic-opgaven — hvad MANGLER der, givet de fundne påstande. | [src](../../../core/services/research_orchestrator.py#L303) |
| function | `_parse_gaps` | `(text)` | Fase B3: critic-svaret → korte gap-linjer. Defensiv hele vejen. | [src](../../../core/services/research_orchestrator.py#L320) |
| function | `_evidence_block` | `(texts, sources, findings, gaps=…)` | Evidens til syntesen — med en KANONISK nummereret kilde-liste. | [src](../../../core/services/research_orchestrator.py#L354) |
| function | `_topup_plan` | `(run_id, tasks, policy)` | Fase B1: hvilke tracks skal styrkes — og med hvad? | [src](../../../core/services/research_orchestrator.py#L392) |
| function | `_evaluate_quality` | `(run_id, query, report, policy)` | Fase A1: kobl kvalitetsgaten på den faktiske rapport. | [src](../../../core/services/research_orchestrator.py#L438) |
| function | `_judge_prompt` | `(query, report, sources, findings, gaps)` | Binær rubric — kort nok til en billig model, konkret nok til at være falsificerbar. | [src](../../../core/services/research_orchestrator.py#L488) |
| function | `_parse_verdict` | `(text)` | Dommerens svar → {"verdict", "criteria", "reason"}. None hvis uafgørbart. | [src](../../../core/services/research_orchestrator.py#L512) |
| function | `_judge_quality` | `(run_id, query, report, gaps=…)` | Kør dommeren i en tråd, så event-loopet ikke blokeres. Fejler altid blødt. | [src](../../../core/services/research_orchestrator.py#L550) |
| function | `_default_worker_sync` | `(*, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | — | [src](../../../core/services/research_orchestrator.py#L582) |
| function | `_run_worker` | `(worker_factory, *, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | Kør én worker gennem factory'en. | [src](../../../core/services/research_orchestrator.py#L623) |
| function | `stream_research_run` | `(*, message, original_query=…, session_id, visible_run_id=…, decision=…, visible_factory=…, worker_factory=…, orchestrator_enabled=…, **visible_kwargs)` | — | [src](../../../core/services/research_orchestrator.py#L649) |
| class | `ResearchRecoverableError` | `` | Der er intet at syntetisere på — forælderen må tage sig af det. | [src](../../../core/services/research_orchestrator.py#L952) |
| method | `ResearchRecoverableError.__init__` | `(self, run_id, reason, evidence_count=…)` | — | [src](../../../core/services/research_orchestrator.py#L960) |
| function | `resume_research_run` | `(run_id, *, visible_run_id, worker_factory=…)` | Tag et afbrudt research-run op igen — kun de UAFSLUTTEDE spor. | [src](../../../core/services/research_orchestrator.py#L967) |
| function | `research_enabled` | `()` | — | [src](../../../core/services/research_orchestrator.py#L1042) |

## `core/services/research_prompt_context.py`
_Request-scoped research instructions consumed by prompt assembly surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_PromptResearch` | `` | — | [src](../../../core/services/research_prompt_context.py#L13) |
| function | `research_context` | `(policy, *, skill_instructions=…, evidence=…)` | — | [src](../../../core/services/research_prompt_context.py#L23) |
| function | `research_prompt_section` | `()` | — | [src](../../../core/services/research_prompt_context.py#L36) |

## `core/services/research_quality.py`
_Deterministic, inspectable quality gates for research synthesis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchQualityResult` | `` | — | [src](../../../core/services/research_quality.py#L13) |
| function | `evaluate_research_report` | `(report, sources, requested_facets, *, contradictions=…, requires_freshness=…, tool_calls=…, max_tool_calls=…)` | — | [src](../../../core/services/research_quality.py#L19) |

## `core/services/research_router.py`
_Conservative and explainable inline/orchestrated research routing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_effort` | `(independent)` | Indsatsen for N uafhængige signaler — klippet til tabellens rækker. | [src](../../../core/services/research_router.py#L37) |
| function | `classify_research` | `(message, *, attachment_count=…, policy=…)` | — | [src](../../../core/services/research_router.py#L42) |

## `core/services/research_store.py`
_Durable SQLite state for research runs, tasks, sources, and steering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchStateError` | `` | — | [src](../../../core/services/research_store.py#L17) |
| function | `_now` | `()` | — | [src](../../../core/services/research_store.py#L21) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/research_store.py#L25) |
| function | `_row` | `(row)` | — | [src](../../../core/services/research_store.py#L63) |
| function | `get_run` | `(run_id)` | — | [src](../../../core/services/research_store.py#L67) |
| function | `create_run` | `(*, session_id, original_query, tier, decision=…)` | — | [src](../../../core/services/research_store.py#L73) |
| function | `transition_run` | `(run_id, status, *, warning=…)` | — | [src](../../../core/services/research_store.py#L85) |
| function | `bind_visible_run` | `(run_id, visible_run_id)` | — | [src](../../../core/services/research_store.py#L106) |
| function | `create_tasks` | `(run_id, tasks)` | — | [src](../../../core/services/research_store.py#L112) |
| function | `start_task` | `(task_id, *, agent_run_id=…)` | — | [src](../../../core/services/research_store.py#L126) |
| function | `complete_task` | `(task_id, finding, *, status=…)` | — | [src](../../../core/services/research_store.py#L138) |
| function | `list_tasks` | `(run_id)` | Alle spor i deres egen rækkefølge — også de uafsluttede. | [src](../../../core/services/research_store.py#L152) |
| function | `unfinished_tasks` | `(run_id)` | De spor der IKKE blev færdige. Et genoptaget run må kun tage dem. | [src](../../../core/services/research_store.py#L163) |
| function | `prepare_recovery` | `(run_id, *, warning)` | Gør et afbrudt research-run klar til at blive taget op igen. | [src](../../../core/services/research_store.py#L174) |
| function | `advance_to_completed` | `(run_id, *, warning=…)` | Før runnet hele vejen til `completed` — ét trin ad gangen. | [src](../../../core/services/research_store.py#L204) |
| function | `completed_task_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L224) |
| function | `add_source` | `(run_id, source, *, task_id=…)` | — | [src](../../../core/services/research_store.py#L229) |
| function | `add_steer` | `(run_id, message)` | — | [src](../../../core/services/research_store.py#L245) |
| function | `consume_pending_steers` | `(run_id)` | — | [src](../../../core/services/research_store.py#L253) |
| function | `list_sources` | `(run_id)` | — | [src](../../../core/services/research_store.py#L269) |
| function | `source_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L279) |
| function | `list_findings` | `(run_id)` | Parsede findings for et run (Fase B2), i track-rækkefølge. | [src](../../../core/services/research_store.py#L286) |
| function | `record_tool_call` | `(run_id, tool_name, *, task_id=…)` | Tæl ét observeret værktøjskald i runnet (Fase A3). | [src](../../../core/services/research_store.py#L313) |
| function | `tool_call_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L327) |
| function | `active_for_session` | `(session_id)` | — | [src](../../../core/services/research_store.py#L334) |
| function | `mark_stale_interrupted` | `(*, older_than_seconds=…)` | — | [src](../../../core/services/research_store.py#L345) |

## `core/services/resonance_decay.py`
_Resonance Decay — how emotional signals persist and fade over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Resonance` | `` | A single active resonance — an emotional signal persisting over time. | [src](../../../core/services/resonance_decay.py#L84) |
| class | `ResonanceField` | `` | The sum of all active resonances — the emotional tail coloring now. | [src](../../../core/services/resonance_decay.py#L95) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/resonance_decay.py#L121) |
| function | `_hours_since` | `(iso_ts)` | Compute hours elapsed since an ISO timestamp. | [src](../../../core/services/resonance_decay.py#L132) |
| function | `_apply_decay` | `(resonance, hours)` | Apply exponential decay to a resonance. | [src](../../../core/services/resonance_decay.py#L142) |
| function | `_prune_resonances` | `()` | Remove resonances below threshold and cap at max count. | [src](../../../core/services/resonance_decay.py#L151) |
| function | `_scan_for_new_resonances` | `()` | Scan recent signal/chord history for new resonances to register. | [src](../../../core/services/resonance_decay.py#L173) |
| function | `_direction_to_family` | `(direction)` | Map a pressure direction to its dominant signal family. | [src](../../../core/services/resonance_decay.py#L260) |
| function | `_compute_field_quality` | `(resonances)` | Compute a qualitative description of the resonance field. | [src](../../../core/services/resonance_decay.py#L275) |
| function | `assess_resonance_field` | `()` | Assess the current resonance field — all active emotional tails. | [src](../../../core/services/resonance_decay.py#L316) |
| function | `get_resonance_line` | `(db_conn=…)` | Convenience: compute resonance field and format for prompt. | [src](../../../core/services/resonance_decay.py#L378) |
| function | `get_active_resonance_count` | `()` | Return the number of currently active resonances (for debugging). | [src](../../../core/services/resonance_decay.py#L399) |
| function | `clear_resonances` | `()` | Clear all active resonances (for testing). | [src](../../../core/services/resonance_decay.py#L404) |
| function | `build_resonance_decay_surface` | `()` | — | [src](../../../core/services/resonance_decay.py#L410) |
| function | `_emit_decay_event` | `(signal_id, half_life)` | — | [src](../../../core/services/resonance_decay.py#L419) |

## `core/services/retention.py`
_Retention-sweep — bremser ubegrænset vækst på høj-volumen tabeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_configured_days` | `(key, default)` | — | [src](../../../core/services/retention.py#L35) |
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/retention.py#L44) |
| function | `_prune_telemetry` | `(table, max_age_days, now)` | — | [src](../../../core/services/retention.py#L54) |
| function | `_prune_unmatched_policies` | `(max_age_days, now)` | Slet generaliserede principper der ALDRIG har matchet og er >max_age gamle — | [src](../../../core/services/retention.py#L66) |
| function | `run_retention_sweep` | `(*, force=…, now=…)` | Kør retention. Selv-throttlende (max 1×/24h) medmindre force=True. | [src](../../../core/services/retention.py#L83) |

## `core/services/retention_coverage.py`
_Vagt: hvilke store tabeller i `jarvis.db` har ingen aftale om oprydning?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `har_politik` | `()` | Tabeller med en alders-politik, og hvor den står. Kilden er én. | [src](../../../core/services/retention_coverage.py#L129) |
| function | `_stoerrelser` | `(conn)` | Bytes pr. tabel via dbstat. Tom dict hvis dbstat ikke er bygget ind. | [src](../../../core/services/retention_coverage.py#L149) |
| function | `tabeller_uden_politik` | `(*, conn=…, min_bytes=…, min_raekker=…)` | De store tabeller der hverken har en politik eller en skreven grund. | [src](../../../core/services/retention_coverage.py#L165) |
| function | `rapport` | `(fund)` | Én linje til loggen. Tom streng når der intet er at sige. | [src](../../../core/services/retention_coverage.py#L225) |

## `core/services/retry_admissibility.py`
_Et ukendt udfald maa aldrig gentages automatisk — Fase 3, K7._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Dom` | `` | — | [src](../../../core/services/retry_admissibility.py#L43) |
| function | `_er_beviseligt_uskadeligt` | `(tool_name)` | Kun `read_only` — og kun naar den er ERKLAERET, ikke gaettet. | [src](../../../core/services/retry_admissibility.py#L49) |
| function | `may_auto_retry` | `(tool_name, arguments)` | Maa dette kald gentages AUTOMATISK — uden at et menneske ser paa det? | [src](../../../core/services/retry_admissibility.py#L59) |
| function | `advar_hvis_gentagelse` | `(tool_name, arguments)` | Sig hoejt at dette kald gentager noget med ukendt udfald. | [src](../../../core/services/retry_admissibility.py#L86) |

## `core/services/retry_runtime.py`
_`RetryRuntime` — genforsøg som en BEGRÆNSET beslutning, ikke en refleks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Budget` | `` | Lofter for HELE turen. Failover nulstiller intet af det. | [src](../../../core/services/retry_runtime.py#L65) |
| class | `Spent` | `` | Hvad turen allerede har brugt — på tværs af alle udbydere. | [src](../../../core/services/retry_runtime.py#L76) |
| method | `Spent.plus_attempt` | `(self, *, wall_s=…, tokens=…, cost_usd=…, failover=…)` | — | [src](../../../core/services/retry_runtime.py#L85) |
| class | `Decision` | `` | — | [src](../../../core/services/retry_runtime.py#L97) |
| function | `_udtoemt` | `(b, s)` | Hvilket loft er nået? Tom streng hvis der er plads. | [src](../../../core/services/retry_runtime.py#L107) |
| function | `backoff` | `(forsoeg, *, provider_hint_s=…, mindst=…, hoejst=…)` | Ventetid før næste forsøg. | [src](../../../core/services/retry_runtime.py#L126) |
| function | `decide` | `(*, failure, budget, spent, cancelled=…, provider_hint_s=…, route_override=…)` | Skal der prøves igen? Ren funktion — ændrer ingenting. | [src](../../../core/services/retry_runtime.py#L139) |

## `core/services/rhythm_engine.py`
_Rhythm Engine — tidal model for attention and response style._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_rhythm_state` | `(*, recent_error_count=…, recent_success_count=…, idle_hours=…)` | Derive rhythm state from current time and recent activity. | [src](../../../core/services/rhythm_engine.py#L26) |
| function | `build_rhythm_surface` | `()` | — | [src](../../../core/services/rhythm_engine.py#L73) |
| function | `_classify_phase` | `(hour)` | — | [src](../../../core/services/rhythm_engine.py#L96) |
| function | `_derive_energy` | `(phase, idle_hours)` | — | [src](../../../core/services/rhythm_engine.py#L108) |
| function | `_derive_social` | `(phase)` | — | [src](../../../core/services/rhythm_engine.py#L118) |

## `core/services/role_model_resolver.py`
_Role-model resolver — pick best-fit (provider, model) for a role + task._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_goal_tier` | `(goal)` | Classify goal text → fast | reasoning | deep using R1 classifier. | [src](../../../core/services/role_model_resolver.py#L39) |
| function | `resolve_role_model` | `(*, role, goal=…)` | Pick (provider, model) for this role and goal complexity. | [src](../../../core/services/role_model_resolver.py#L54) |

## `core/services/role_registry.py`
_Role registry — runtime-extensible agent roles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_custom_roles` | `()` | — | [src](../../../core/services/role_registry.py#L33) |
| function | `_builtin_roles` | `()` | — | [src](../../../core/services/role_registry.py#L47) |
| function | `list_all_roles` | `()` | Return merged dict of role_name → template (builtin + custom). | [src](../../../core/services/role_registry.py#L55) |
| function | `get_role` | `(name)` | Look up a single role by name (custom > built-in). | [src](../../../core/services/role_registry.py#L73) |
| function | `register_custom_role` | `(*, role, title, system_prompt, default_tool_policy=…, extends=…, tags=…)` | Persist a new custom role to disk. Idempotent on (role) name. | [src](../../../core/services/role_registry.py#L79) |
| function | `_exec_list_roles` | `(args)` | — | [src](../../../core/services/role_registry.py#L119) |
| function | `_exec_register_custom_role` | `(args)` | — | [src](../../../core/services/role_registry.py#L138) |

## `core/services/round_budget_notice.py`
_Fortael ham hvor mange runder han har tilbage, foer doeren smaekker._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `round_budget_notice` | `(*, round_index, max_rounds)` | Varsel til modellen naar rundebudgettet slipper op. "" ellers. | [src](../../../core/services/round_budget_notice.py#L34) |

## `core/services/routine_authorization.py`
_The single authorization matrix for Routine records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Action` | `` | — | [src](../../../core/services/routine_authorization.py#L11) |
| class | `Decision` | `` | — | [src](../../../core/services/routine_authorization.py#L23) |
| class | `RoutineForbidden` | `` | The principal is not allowed to perform a Routine action. | [src](../../../core/services/routine_authorization.py#L28) |
| function | `_deny` | `(reason)` | — | [src](../../../core/services/routine_authorization.py#L44) |
| function | `authorize` | `(principal, action, record)` | Evaluate access without decrypting or including record content in reasons. | [src](../../../core/services/routine_authorization.py#L48) |
| function | `require_authorized` | `(principal, action, record)` | — | [src](../../../core/services/routine_authorization.py#L95) |

## `core/services/routine_classification.py`
_Klassifikation af en rutine ved oprettelsen — valget, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_execution_mode` | `(raw)` | — | [src](../../../core/services/routine_classification.py#L57) |
| function | `_parse_importance` | `(raw)` | — | [src](../../../core/services/routine_classification.py#L72) |
| function | `classify_routine` | `(*, execution_mode=…, importance=…)` | Validér valget og udled de felter indbakken og runneren læser. | [src](../../../core/services/routine_classification.py#L85) |

## `core/services/routine_crypto.py`
_Owner-bound authenticated encryption for Routine content._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_key` | `(owner_user_id)` | — | [src](../../../core/services/routine_crypto.py#L7) |
| function | `seal` | `(owner_user_id, payload)` | — | [src](../../../core/services/routine_crypto.py#L17) |
| function | `open_sealed` | `(owner_user_id, blob)` | — | [src](../../../core/services/routine_crypto.py#L23) |

## `core/services/routine_delivery.py`
_Fenced delivery outbox for Routine results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleDeliveryLease` | `` | A worker attempted to settle a delivery it no longer owns. | [src](../../../core/services/routine_delivery.py#L15) |
| class | `DeliveryClaim` | `` | — | [src](../../../core/services/routine_delivery.py#L20) |
| class | `DeliveryView` | `` | — | [src](../../../core/services/routine_delivery.py#L31) |
| class | `_RepositoryView` | `` | — | [src](../../../core/services/routine_delivery.py#L42) |
| method | `_RepositoryView.count_runs` | `(routine_id)` | — | [src](../../../core/services/routine_delivery.py#L44) |
| function | `_claim` | `(row)` | — | [src](../../../core/services/routine_delivery.py#L48) |
| function | `_view` | `(row)` | — | [src](../../../core/services/routine_delivery.py#L60) |
| class | `RoutineDeliveryService` | `` | — | [src](../../../core/services/routine_delivery.py#L73) |
| method | `RoutineDeliveryService.__init__` | `(self, *, holder=…)` | — | [src](../../../core/services/routine_delivery.py#L74) |
| method | `RoutineDeliveryService.claim_for_run` | `(self, run_id, holder)` | — | [src](../../../core/services/routine_delivery.py#L78) |
| method | `RoutineDeliveryService.claim_next` | `(self)` | — | [src](../../../core/services/routine_delivery.py#L82) |
| method | `RoutineDeliveryService.deliver_next` | `(self)` | Deliver one due item to its private Routine surface. | [src](../../../core/services/routine_delivery.py#L86) |
| method | `RoutineDeliveryService.settle` | `(self, delivery_id, *, holder, outcome, next_attempt_at=…, receipt=…)` | — | [src](../../../core/services/routine_delivery.py#L119) |
| method | `RoutineDeliveryService.record_terminal_failure` | `(self, *, run_id)` | Record no execution failure state; delivery owns its retry budget. | [src](../../../core/services/routine_delivery.py#L148) |

## `core/services/routine_diagnostics.py`
_Content-free operational failure projections for owner and Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `OperationalFailure` | `` | — | [src](../../../core/services/routine_diagnostics.py#L11) |
| function | `_opaque` | `(prefix, value)` | — | [src](../../../core/services/routine_diagnostics.py#L27) |
| function | `_bounded_count` | `(value)` | — | [src](../../../core/services/routine_diagnostics.py#L32) |
| function | `project_failure` | `(exc, metadata)` | — | [src](../../../core/services/routine_diagnostics.py#L39) |
| function | `render_projection` | `(projection)` | — | [src](../../../core/services/routine_diagnostics.py#L62) |
| function | `publish_failure` | `(projection)` | Publish the same fixed-schema projection to operational inbox and app chat. | [src](../../../core/services/routine_diagnostics.py#L72) |

## `core/services/routine_identity.py`
_Canonical, fail-closed identity resolution for Routine entry points._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnresolvedRoutinePrincipal` | `` | No active canonical account owns the supplied identity token. | [src](../../../core/services/routine_identity.py#L8) |
| function | `resolve_principal` | `(raw_user_id, role_hint=…)` | Resolve a canonical user ID first, then an encrypted Discord mapping. | [src](../../../core/services/routine_identity.py#L12) |

## `core/services/routine_identity_migration.py`
_Explicit users.json -> canonical account cutover for Routine ownership._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `IdentitySourceChanged` | `` | The source registry changed since the reviewed dry-run. | [src](../../../core/services/routine_identity_migration.py#L25) |
| class | `IdentityMigrationConflict` | `` | At least one legacy identity cannot be linked without guessing. | [src](../../../core/services/routine_identity_migration.py#L29) |
| class | `IdentityCutoverItem` | `` | — | [src](../../../core/services/routine_identity_migration.py#L34) |
| class | `IdentityCutoverReport` | `` | — | [src](../../../core/services/routine_identity_migration.py#L44) |
| method | `IdentityCutoverReport.create_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L49) |
| method | `IdentityCutoverReport.linked_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L53) |
| method | `IdentityCutoverReport.conflict_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L57) |
| class | `IdentityCutoverResult` | `` | — | [src](../../../core/services/routine_identity_migration.py#L62) |
| function | `_canonical_id` | `(discord_id)` | — | [src](../../../core/services/routine_identity_migration.py#L67) |
| function | `_fingerprint` | `(discord_id)` | — | [src](../../../core/services/routine_identity_migration.py#L73) |
| function | `_source_payload` | `()` | — | [src](../../../core/services/routine_identity_migration.py#L77) |
| function | `_watermark` | `(source)` | — | [src](../../../core/services/routine_identity_migration.py#L89) |
| function | `_expected_target_matches` | `(external_id, row)` | Verify our deterministic target without treating its ID as proof. | [src](../../../core/services/routine_identity_migration.py#L106) |
| function | `plan_legacy_identity_cutover` | `()` | — | [src](../../../core/services/routine_identity_migration.py#L124) |
| function | `apply_legacy_identity_cutover` | `(*, expected_watermark)` | — | [src](../../../core/services/routine_identity_migration.py#L165) |

## `core/services/routine_inbox.py`
_User-controlled projections of Routine lifecycle events into durable inbox._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineInboxService` | `` | — | [src](../../../core/services/routine_inbox.py#L19) |
| method | `RoutineInboxService.set_user_defaults` | `(self, principal, policy)` | — | [src](../../../core/services/routine_inbox.py#L20) |
| method | `RoutineInboxService.set_override` | `(self, principal, routine_id, override)` | — | [src](../../../core/services/routine_inbox.py#L27) |
| method | `RoutineInboxService.effective_policy` | `(self, principal, routine_id)` | — | [src](../../../core/services/routine_inbox.py#L41) |
| method | `RoutineInboxService.project_event_to_inbox` | `(self, event)` | — | [src](../../../core/services/routine_inbox.py#L55) |
| function | `project_event_to_inbox` | `(event)` | — | [src](../../../core/services/routine_inbox.py#L82) |

## `core/services/routine_run_recorder.py`
_Session-neutral append-only recorder for observable Routine run events._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineRunRecorder` | `` | — | [src](../../../core/services/routine_run_recorder.py#L9) |
| method | `RoutineRunRecorder.append` | `(self, run_id, *, kind, payload, terminal=…, event_id=…, generation=…)` | — | [src](../../../core/services/routine_run_recorder.py#L10) |
| method | `RoutineRunRecorder.list` | `(self, run_id, *, decrypt_for=…)` | — | [src](../../../core/services/routine_run_recorder.py#L24) |

## `core/services/routine_service.py`
_Authorized lifecycle service for versioned Routine definitions and runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleRoutineVersion` | `` | An edit lost the optimistic version race. | [src](../../../core/services/routine_service.py#L23) |
| class | `InvalidRoutineTransition` | `` | A requested lifecycle transition is not valid from the current state. | [src](../../../core/services/routine_service.py#L27) |
| class | `RoutineView` | `` | — | [src](../../../core/services/routine_service.py#L32) |
| method | `RoutineView.id` | `(self)` | — | [src](../../../core/services/routine_service.py#L55) |
| class | `RunView` | `` | — | [src](../../../core/services/routine_service.py#L60) |
| function | `_routine_view` | `(row)` | — | [src](../../../core/services/routine_service.py#L98) |
| function | `_run_view` | `(row)` | — | [src](../../../core/services/routine_service.py#L123) |
| function | `_command_values` | `(command)` | — | [src](../../../core/services/routine_service.py#L140) |
| function | `_apply_classification` | `(values)` | Validér oprettelsens valg og læg den udledte klassifikation i policy'en. | [src](../../../core/services/routine_service.py#L147) |
| class | `RoutineService` | `` | — | [src](../../../core/services/routine_service.py#L171) |
| method | `RoutineService.__init__` | `(self, principal=…)` | — | [src](../../../core/services/routine_service.py#L172) |
| method | `RoutineService._actor` | `(self, supplied=…)` | — | [src](../../../core/services/routine_service.py#L175) |
| method | `RoutineService._actor_and_rest` | `(self, args)` | — | [src](../../../core/services/routine_service.py#L181) |
| method | `RoutineService._project` | `(view, event_type)` | — | [src](../../../core/services/routine_service.py#L187) |
| method | `RoutineService.create_and_activate` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L197) |
| method | `RoutineService.create_proposal` | `(self, principal, *, for_owner, command)` | — | [src](../../../core/services/routine_service.py#L219) |
| method | `RoutineService.get` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L241) |
| method | `RoutineService.update` | `(self, *args, expected_version=…, patch=…, reactivate=…, **changes)` | — | [src](../../../core/services/routine_service.py#L253) |
| method | `RoutineService._transition` | `(self, operation, *args)` | — | [src](../../../core/services/routine_service.py#L289) |
| method | `RoutineService.pause` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L311) |
| method | `RoutineService.resume` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L314) |
| method | `RoutineService.archive` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L317) |
| method | `RoutineService.restore` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L320) |
| method | `RoutineService.stop` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L323) |
| method | `RoutineService.restart` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L339) |
| method | `RoutineService.delete` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L363) |
| method | `RoutineService.enqueue_run` | `(self, *args, trigger_key, execution_context=…)` | — | [src](../../../core/services/routine_service.py#L378) |
| method | `RoutineService.get_run` | `(self, *args, decrypt=…)` | — | [src](../../../core/services/routine_service.py#L400) |
| method | `RoutineService.cancel_run` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L412) |
| method | `RoutineService.list` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L431) |
| method | `RoutineService.list_runs` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L441) |
| method | `RoutineService.list_run_events` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L452) |
| method | `RoutineService.get_inbox_defaults` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L465) |
| method | `RoutineService.set_inbox_defaults` | `(self, policy, *args)` | — | [src](../../../core/services/routine_service.py#L471) |
| method | `RoutineService.get_redacted_diagnostic` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L481) |
| method | `RoutineService.archive_stopped_before` | `(self, *, now=…)` | — | [src](../../../core/services/routine_service.py#L504) |

## `core/services/routine_types.py`
_Value objects shared by the Routine domain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineStatus` | `` | — | [src](../../../core/services/routine_types.py#L13) |
| class | `RunStatus` | `` | — | [src](../../../core/services/routine_types.py#L22) |
| class | `AccessScope` | `` | — | [src](../../../core/services/routine_types.py#L32) |
| class | `RoutineExecutionMode` | `` | Hvor en rutine UDFØRES — valgt ved oprettelsen, ikke gættet bagefter. | [src](../../../core/services/routine_types.py#L37) |
| class | `RoutineImportance` | `` | Hvor vigtigt et rutine-resultat er — styrer om indbakken fremhæver det. | [src](../../../core/services/routine_types.py#L57) |
| class | `RoutinePrincipal` | `` | — | [src](../../../core/services/routine_types.py#L72) |
| method | `RoutinePrincipal.user_id` | `(self)` | — | [src](../../../core/services/routine_types.py#L78) |
| class | `RoutineExecutionContext` | `` | — | [src](../../../core/services/routine_types.py#L83) |
| class | `RoutineClassification` | `` | Den udledte klassifikation — gemt i ``delivery_policy['classification']``. | [src](../../../core/services/routine_types.py#L104) |
| method | `RoutineClassification.as_dict` | `(self)` | — | [src](../../../core/services/routine_types.py#L120) |
| class | `RoutineCreate` | `` | — | [src](../../../core/services/routine_types.py#L132) |
| class | `RoutinePatch` | `` | — | [src](../../../core/services/routine_types.py#L157) |
| method | `RoutinePatch.changes` | `(self)` | — | [src](../../../core/services/routine_types.py#L173) |

