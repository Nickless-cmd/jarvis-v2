# `core.services.17` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_relation_state_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L23) |
| function | `refresh_runtime_relation_state_signal_statuses` | `()` | — | [src](../../../core/services/relation_state_signal_tracking.py#L55) |
| function | `build_runtime_relation_state_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L86) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L119) |
| function | `_persist_relation_state_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L239) |
| function | `_latest_user_understanding_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L308) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L318) |
| function | `_latest_regulation_homeostasis_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L328) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L338) |
| function | `_latest_inner_visible_support_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L350) |
| function | `_derive_relation_alignment` | `(*, user_confidence, user_signal_type, regulation_state, contradiction_status)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L362) |
| function | `_derive_relation_watchfulness` | `(*, regulation_watchfulness, contradiction_pressure, visible_watchfulness)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L376) |
| function | `_derive_relation_pressure` | `(*, regulation_pressure, contradiction_pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L389) |
| function | `_derive_relation_state` | `(*, alignment, watchfulness, pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L399) |
| function | `_relation_summary` | `(*, focus, relation_state, relation_alignment, relation_watchfulness, relation_pressure)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L414) |
| function | `_grounding_mode` | `(*, has_private_state, has_regulation, has_executive_contradiction, has_inner_visible_support)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L429) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L448) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L474) |
| function | `_focus_key` | `(*items)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L497) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L505) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L515) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L527) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L539) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L551) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L559) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L567) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/relation_state_signal_tracking.py#L581) |

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_release_marker_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L25) |
| function | `refresh_runtime_release_marker_signal_statuses` | `()` | — | [src](../../../core/services/release_marker_signal_tracking.py#L48) |
| function | `build_runtime_release_marker_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L79) |
| function | `_extract_release_marker_candidates` | `(*, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L117) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L214) |
| function | `_persist_release_marker_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L323) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L392) |
| function | `_derive_release_state` | `(*, metabolism_state, witness_status, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L419) |
| function | `_derive_release_direction` | `(*, release_state, witness_status, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L434) |
| function | `_derive_release_weight` | `(*, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L451) |
| function | `_release_summary` | `(*, focus, release_state, release_direction, release_weight)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L465) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L485) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L492) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L499) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L511) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L522) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L536) |

## `core/services/remembered_fact_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_remembered_fact_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L27) |
| function | `refresh_runtime_remembered_fact_signal_statuses` | `()` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L63) |
| function | `build_runtime_remembered_fact_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L94) |
| function | `_extract_remembered_fact_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L120) |
| function | `_persist_remembered_fact_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L153) |
| function | `_explicit_user_name_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L222) |
| function | `_explicit_project_anchor_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L252) |
| function | `_explicit_working_context_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L281) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L311) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L320) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L329) |
| function | `_extract_name_value` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L353) |
| function | `_is_project_anchor_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L366) |
| function | `_is_working_context_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L379) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L413) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L420) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L425) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L432) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L441) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L453) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L457) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L461) |

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
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/retention.py#L35) |
| function | `_prune_telemetry` | `(table, max_age_days, now)` | — | [src](../../../core/services/retention.py#L45) |
| function | `_prune_unmatched_policies` | `(max_age_days, now)` | Slet generaliserede principper der ALDRIG har matchet og er >max_age gamle — | [src](../../../core/services/retention.py#L57) |
| function | `run_retention_sweep` | `(*, force=…, now=…)` | Kør retention. Selv-throttlende (max 1×/24h) medmindre force=True. | [src](../../../core/services/retention.py#L74) |

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

## `core/services/rule_definitions.py`
_Rule definitions — production rules feeding the rule_engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get` | `(s, *keys, default=…)` | Walk a nested dict; return default if any step is missing. | [src](../../../core/services/rule_definitions.py#L25) |
| function | `_len` | `(s, surface, key=…)` | Count items in a surface list field. | [src](../../../core/services/rule_definitions.py#L38) |

## `core/services/rule_engine.py`
_Rule Engine — forward-chaining symbolic inference over signal surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuleConclusion` | `` | One conclusion from one rule firing. | [src](../../../core/services/rule_engine.py#L27) |
| class | `Rule` | `` | One production rule in the engine. | [src](../../../core/services/rule_engine.py#L49) |
| class | `RuleCycleResult` | `` | Result of one full evaluation cycle. | [src](../../../core/services/rule_engine.py#L61) |
| class | `RuleEngine` | `` | Forward-chaining rule engine. | [src](../../../core/services/rule_engine.py#L73) |
| method | `RuleEngine.__init__` | `(self)` | — | [src](../../../core/services/rule_engine.py#L80) |
| method | `RuleEngine.add_rule` | `(self, rule)` | — | [src](../../../core/services/rule_engine.py#L84) |
| method | `RuleEngine.register_rules` | `(self, rules)` | — | [src](../../../core/services/rule_engine.py#L88) |
| method | `RuleEngine.clear_rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L92) |
| method | `RuleEngine.rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L97) |
| method | `RuleEngine.evaluate` | `(self, signals)` | Evaluate all rules against current signal state. | [src](../../../core/services/rule_engine.py#L103) |
| method | `RuleEngine.get_rule` | `(self, name)` | — | [src](../../../core/services/rule_engine.py#L136) |
| method | `RuleEngine.rules_by_domain` | `(self, domain)` | — | [src](../../../core/services/rule_engine.py#L142) |
| function | `_get` | `(signals, *keys, default=…)` | Safely dig into nested signal dicts. | [src](../../../core/services/rule_engine.py#L149) |
| function | `signal_value` | `(signals, surface, field, default=…)` | Extract a scalar value from a named surface field. | [src](../../../core/services/rule_engine.py#L160) |
| function | `surface_has` | `(signals, surface)` | Check if a surface exists and has no error. | [src](../../../core/services/rule_engine.py#L170) |
| function | `get_engine` | `()` | — | [src](../../../core/services/rule_engine.py#L185) |
| function | `_load_default_rules` | `(engine)` | Import and register all default rule definitions. | [src](../../../core/services/rule_engine.py#L193) |
| function | `reset_engine` | `()` | Reset the engine (useful for testing or hot-reload). | [src](../../../core/services/rule_engine.py#L201) |
| function | `evaluate_rules` | `(signals)` | Convenience: get engine, evaluate, return result. | [src](../../../core/services/rule_engine.py#L207) |
| function | `get_all_rules` | `()` | Return all registered rules as serializable dicts (for tools). | [src](../../../core/services/rule_engine.py#L212) |
| function | `build_rule_engine_surface` | `()` | — | [src](../../../core/services/rule_engine.py#L224) |
| function | `_emit_rule_fired_event` | `(rule_name, urgency)` | — | [src](../../../core/services/rule_engine.py#L239) |

## `core/services/run_closure_gate.py`
_Run-closure gate — fang tomme replies og unstaged changes efter agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_porcelain_status` | `(*, cwd=…)` | Return the set of path-strings reported by ``git status --porcelain``. | [src](../../../core/services/run_closure_gate.py#L54) |
| function | `_git_dirty_content_hashes` | `(*, cwd=…)` | Return {path: content_hash} for every file currently dirty in working tree. | [src](../../../core/services/run_closure_gate.py#L73) |
| function | `_record_pre_run_state` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L152) |
| function | `_pop_pre_run_state` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L161) |
| function | `_set_current_run` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L183) |
| function | `_get_current_run` | `()` | — | [src](../../../core/services/run_closure_gate.py#L189) |
| function | `_record_tool_call` | `(run_id, tool_name)` | — | [src](../../../core/services/run_closure_gate.py#L194) |
| function | `_pop_tool_calls` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L208) |
| function | `_summarize_unstaged` | `(diff, limit=…)` | Build a structured summary of new unstaged/untracked paths. | [src](../../../core/services/run_closure_gate.py#L216) |
| function | `_on_run_completed` | `(payload)` | Handle a runtime.autonomous_run_completed event. | [src](../../../core/services/run_closure_gate.py#L232) |
| function | `_on_run_started` | `(payload)` | Handle runtime.autonomous_run_started — snapshot git state. | [src](../../../core/services/run_closure_gate.py#L340) |
| function | `_on_tool_used` | `(payload)` | Track tool calls so we can detect silent runs. | [src](../../../core/services/run_closure_gate.py#L348) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/run_closure_gate.py#L364) |
| function | `start_run_closure_gate` | `()` | Start the eventbus subscriber thread. Safe to call multiple times. | [src](../../../core/services/run_closure_gate.py#L392) |
| function | `stop_run_closure_gate` | `()` | — | [src](../../../core/services/run_closure_gate.py#L417) |

## `core/services/run_event_log.py`
_In-memory, append-only, offset-indekseret event-log PR. RUN._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_terminal_frame` | `(frame)` | Er denne SSE-frame en TERMINAL-frame (message_stop)? Klienterne forlader kun | [src](../../../core/services/run_event_log.py#L22) |
| function | `_is_ephemeral_frame` | `(frame)` | ping/retry-frames er KEEPALIVE-støj på den direkte stream — de er irrelevante | [src](../../../core/services/run_event_log.py#L29) |
| function | `synthetic_terminal_frame` | `(run_id=…, session_id=…, reason=…)` | H1/G6: byg en syntetisk terminal-SSE-frame til en subscriber der GIVER OP uden | [src](../../../core/services/run_event_log.py#L54) |
| function | `create` | `(run_id, session_id)` | — | [src](../../../core/services/run_event_log.py#L71) |
| function | `append` | `(run_id, frame)` | — | [src](../../../core/services/run_event_log.py#L88) |
| function | `_emit_cap_nerve` | `(run_id)` | Observe (cluster='stream', nerve='relay_frame_cap') at relay-bufferen ramte | [src](../../../core/services/run_event_log.py#L121) |
| function | `touch_liveness` | `(run_id)` | Opdatér et runs liveness (last_append_at) UDEN at persistere en frame. | [src](../../../core/services/run_event_log.py#L135) |
| function | `mark_done` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L150) |
| function | `read` | `(run_id, from_idx)` | — | [src](../../../core/services/run_event_log.py#L157) |
| function | `active_run_for_session` | `(session_id)` | — | [src](../../../core/services/run_event_log.py#L165) |
| function | `is_live` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L176) |
| function | `live_run_ids` | `()` | — | [src](../../../core/services/run_event_log.py#L187) |
| function | `session_for_run` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L199) |
| function | `prune` | `()` | Behold alle ikke-done runs + de seneste _KEEP_DONE_PER_SESSION done-runs | [src](../../../core/services/run_event_log.py#L205) |
| function | `subscriber_opened` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L222) |
| function | `subscriber_closed` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L229) |
| function | `mark_consumed` | `(run_id)` | En subscriber yieldede message_stop -> nogen saa runnet til ende. | [src](../../../core/services/run_event_log.py#L236) |
| function | `was_consumed_or_active` | `(run_id)` | True hvis en levende subscriber saa/ser runnet til ende -> undertryk push. | [src](../../../core/services/run_event_log.py#L244) |
| function | `claim_or_create` | `(session_id, stale_cap_s=…)` | Atomisk find-eller-opret pr. session — under én laas, saa samtidige POSTs | [src](../../../core/services/run_event_log.py#L253) |

## `core/services/run_follow.py`
_Follow-stream for runs → klienter kan token-streame dem live + liveness-kilde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `begin_follow` | `(session_id, run_id=…)` | Nulstil buffer for en NY run i sessionen (catch-up starter forfra). | [src](../../../core/services/run_follow.py#L38) |
| function | `publish_follow_frame` | `(session_id, frame)` | Append en v2-SSE-frame til sessionens buffer (kaldt fra run-tråden). | [src](../../../core/services/run_follow.py#L52) |
| function | `end_follow` | `(session_id)` | Markér sessionens follow-stream som færdig → pollende endpoint stopper | [src](../../../core/services/run_follow.py#L66) |
| function | `_snapshot` | `(session_id, from_idx)` | Returnér (nye frames fra from_idx, done). | [src](../../../core/services/run_follow.py#L78) |
| function | `has_active_follow` | `(session_id)` | True hvis der findes en (ikke-afsluttet) follow-buffer for sessionen. | [src](../../../core/services/run_follow.py#L88) |
| function | `session_is_live` | `(session_id, max_idle_s=…)` | Autoritativ: kører der et run i denne session LIGE NU? (ikke done OG | [src](../../../core/services/run_follow.py#L95) |
| function | `live_sessions` | `(max_idle_s=…)` | Alle sessioner med et run der aktivt streamer lige nu (desktop-prikker + | [src](../../../core/services/run_follow.py#L106) |

## `core/services/runtime_action_executor.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_action_risk` | `(action)` | Classify runtime action risk for emotional gating. | [src](../../../core/services/runtime_action_executor.py#L63) |
| class | `RuntimeExecutionResult` | `` | — | [src](../../../core/services/runtime_action_executor.py#L78) |
| function | `_publish_gate_event` | `(*, input_action, gated_action, gate_reason, snapshot, risk)` | Emit emotional gate decision to eventbus for telemetry. | [src](../../../core/services/runtime_action_executor.py#L87) |
| function | `execute_runtime_action` | `(*, action_id, payload)` | — | [src](../../../core/services/runtime_action_executor.py#L114) |
| function | `execute_refresh_memory_context` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L243) |
| function | `execute_follow_open_loop` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L259) |
| function | `execute_inspect_repo_context` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L307) |
| function | `execute_review_recent_conversations` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L368) |
| function | `execute_write_internal_work_note` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L380) |
| function | `execute_bounded_self_check` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L417) |
| function | `execute_propose_next_user_step` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L435) |
| function | `execute_promote_initiative_to_visible_lane` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L453) |
| function | `_publish_action_event` | `(result)` | — | [src](../../../core/services/runtime_action_executor.py#L487) |
| function | `_matching_loop_closure` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_action_executor.py#L501) |
| function | `_loop_domain_key` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_action_executor.py#L516) |
| function | `_repo_operation_from_focus` | `(focus)` | — | [src](../../../core/services/runtime_action_executor.py#L527) |
| function | `_repo_command_for_operation` | `(operation)` | — | [src](../../../core/services/runtime_action_executor.py#L540) |
| function | `_build_internal_work_note` | `(*, current_mode, emphasis)` | — | [src](../../../core/services/runtime_action_executor.py#L562) |

## `core/services/runtime_action_outcome_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_action_outcome` | `(*, action_id, mode, reason, score, payload, result)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L13) |
| function | `build_runtime_action_outcome_surface` | `(*, limit=…)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L53) |
| function | `recent_runtime_action_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L77) |
| function | `_persist_runtime_action_outcome` | `(outcome)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L86) |
| function | `_persist_learning_signals` | `(outcome)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L105) |
| function | `_completion_outcome_label` | `(status)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L130) |
| function | `_consecutive_repetition_count` | `(items)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L141) |

## `core/services/runtime_action_registry.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeActionSpec` | `` | — | [src](../../../core/services/runtime_action_registry.py#L12) |
| function | `list_runtime_action_specs` | `()` | — | [src](../../../core/services/runtime_action_registry.py#L109) |
| function | `get_runtime_action_spec` | `(action_id)` | — | [src](../../../core/services/runtime_action_registry.py#L113) |

## `core/services/runtime_awareness_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_awareness_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L42) |
| function | `refresh_runtime_awareness_signal_statuses` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L66) |
| function | `build_runtime_awareness_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L95) |
| function | `_machine_available_signal` | `(*, heartbeat)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L137) |
| function | `_extract_runtime_awareness_candidates` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L157) |
| function | `_visible_runtime_signal` | `(*, readiness)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L202) |
| function | `_local_lane_signal` | `(*, local_lane)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L267) |
| function | `_heartbeat_runtime_signal` | `(*, heartbeat, readiness)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L308) |
| function | `_runtime_task_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L335) |
| function | `_runtime_flow_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L375) |
| function | `_runtime_hook_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L415) |
| function | `_browser_body_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L464) |
| function | `_layered_memory_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L504) |
| function | `_persist_runtime_awareness_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L556) |
| function | `_latest_runtime_awareness_signal` | `(canonical_key)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L635) |
| function | `_history_item_from_signal` | `(item)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L642) |
| function | `_machine_state_summary` | `(*, constrained, active, recovered)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L656) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L687) |

## `core/services/runtime_browser_body.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_browser_body` | `(*, profile_name=…, active_task_id=…, active_flow_id=…)` | — | [src](../../../core/services/runtime_browser_body.py#L12) |
| function | `record_tab_snapshot` | `(*, body_id, tab_id, url, title=…, status=…, summary=…, selected=…)` | — | [src](../../../core/services/runtime_browser_body.py#L50) |
| function | `get_browser_body` | `(body_id)` | — | [src](../../../core/services/runtime_browser_body.py#L90) |
| function | `list_browser_bodies` | `(limit=…)` | — | [src](../../../core/services/runtime_browser_body.py#L97) |
| function | `update_browser_body` | `(body_id, *, status=…, active_task_id=…, active_flow_id=…, focused_tab_id=…, tabs=…, last_url=…, last_title=…, summary=…)` | — | [src](../../../core/services/runtime_browser_body.py#L101) |
| function | `_find_browser_body_by_profile` | `(profile_name)` | — | [src](../../../core/services/runtime_browser_body.py#L139) |
| function | `_decode_browser_body` | `(body)` | — | [src](../../../core/services/runtime_browser_body.py#L146) |
| function | `set_browser_status` | `(status, *, url=…, title=…)` | Update the default browser body status — called from browser tool handlers. | [src](../../../core/services/runtime_browser_body.py#L156) |

## `core/services/runtime_cognitive_conductor.py`
_Cognitive conductor — Jarvis' bounded mental state assembler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_temporal_depth` | `(*, brain_count, open_loop_count, continuity_mode)` | Classify the dominant time horizon of the current mental state. | [src](../../../core/services/runtime_cognitive_conductor.py#L47) |
| function | `_select_mode` | `(*, visible_active, question_gate_active, approval_pending, brain_count, open_loop_count, liveness_state, contradiction_active, experiment_carry=…, cognitive_episode=…)` | Select the bounded mental mode from runtime state. | [src](../../../core/services/runtime_cognitive_conductor.py#L69) |
| function | `_select_salient_items` | `(*, brain_excerpts, open_loop_items, private_signal_items, inner_forces, gate_items, relation_items, world_model_items, remembered_fact_items, user_understanding_items, contradiction_items, meaning_items, metabolism_items, release_items, self_review_items, dream_items, experiment_carry=…)` | Select the most salient items across all sources. | [src](../../../core/services/runtime_cognitive_conductor.py#L128) |
| function | `_collect_private_signal_items` | `(*, tension_surface, private_state)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L276) |
| function | `_select_affordances` | `(*, active_capabilities, gated_items, mode, contradiction_active)` | Build the current affordance map — what's possible, appropriate, or gated NOW. | [src](../../../core/services/runtime_cognitive_conductor.py#L322) |
| function | `build_cognitive_frame` | `(*, self_knowledge=…, heartbeat_state=…)` | Build the current bounded cognitive frame. | [src](../../../core/services/runtime_cognitive_conductor.py#L378) |
| function | `_build_frame_summary` | `(*, mode, salient, temporal, continuity_pressure, private_signal_pressure, brain_count, open_loop_count, experiment_carry=…)` | Build a compact one-line summary of the cognitive frame. | [src](../../../core/services/runtime_cognitive_conductor.py#L718) |
| function | `build_cognitive_frame_prompt_section` | `()` | Build a compact cognitive frame section for prompt inclusion. | [src](../../../core/services/runtime_cognitive_conductor.py#L749) |
| function | `_safe_brain_context` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L845) |
| function | `_safe_self_knowledge` | `(*, heartbeat_state=…)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L853) |
| function | `_safe_open_loops` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L865) |
| function | `_safe_question_gates` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L873) |
| function | `_safe_initiative_tension` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L881) |
| function | `_safe_private_state` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L889) |
| function | `_safe_visible_status` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L897) |
| function | `_safe_experiential_support` | `()` | Read experiential carry-forward support surface. | [src](../../../core/services/runtime_cognitive_conductor.py#L905) |
| function | `_safe_liveness_snapshot` | `(*, heartbeat_state=…)` | Get a lightweight liveness snapshot without triggering full liveness build. | [src](../../../core/services/runtime_cognitive_conductor.py#L929) |
| function | `_safe_cognitive_core_experiments` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L958) |
| function | `_derive_cognitive_experiment_carry` | `(surface)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L973) |
| function | `_safe_relation_state` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1072) |
| function | `_safe_cognitive_episode_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1082) |
| function | `_safe_theory_of_mind_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1090) |
| function | `_safe_learning_policy_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1098) |
| function | `_safe_perception_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1106) |
| function | `_safe_emotional_memory_surface` | `(*, context_features=…)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1114) |
| function | `_extract_context_features_from_episode` | `(cognitive_episode)` | Pull retrieval-relevant fields from a cognitive_episode surface entry. | [src](../../../core/services/runtime_cognitive_conductor.py#L1128) |
| function | `_safe_relation_continuity` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1152) |
| function | `_safe_self_narrative_continuity` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1162) |
| function | `_safe_world_model` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1172) |
| function | `_safe_remembered_facts` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1182) |
| function | `_safe_user_understanding` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1192) |
| function | `_safe_executive_contradiction` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1202) |
| function | `_safe_meaning_significance` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1212) |
| function | `_safe_metabolism` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1222) |
| function | `_safe_release_markers` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1232) |
| function | `_safe_attachment_topology` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1242) |
| function | `_safe_loyalty_gradient` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1252) |
| function | `_safe_diary_synthesis` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1262) |
| function | `_safe_chronicle_consolidation` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1272) |
| function | `_safe_self_review` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1282) |
| function | `_safe_dream_family` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1337) |

## `core/services/runtime_decision_engine.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeDecisionInput` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L13) |
| class | `RuntimeActionCandidate` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L24) |
| class | `RuntimeDecision` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L33) |
| function | `decide_next_action` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L42) |
| function | `build_action_candidates` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L47) |
| function | `choose_best_candidate` | `(candidates)` | — | [src](../../../core/services/runtime_decision_engine.py#L77) |
| function | `_open_loop_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L98) |
| function | `_initiative_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L142) |
| function | `_memory_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L168) |
| function | `_reflection_candidates` | `(inputs, *, visible_active, approval_pending)` | — | [src](../../../core/services/runtime_decision_engine.py#L189) |
| function | `_looks_repo_focused` | `(loop)` | — | [src](../../../core/services/runtime_decision_engine.py#L236) |
| function | `_apply_feedback` | `(candidate, inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L247) |
| function | `_matching_note_loop_synergy` | `(candidate, inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L333) |
| function | `_top_open_loop_title` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L352) |
| function | `_apply_semantic_feedback` | `(candidate, inputs, *, score, signal_stats)` | — | [src](../../../core/services/runtime_decision_engine.py#L360) |
| function | `_apply_persistent_learning` | `(candidate, runtime_learning_summary, *, score)` | — | [src](../../../core/services/runtime_decision_engine.py#L417) |
| function | `_signal_weight` | `(signal_stats, signal)` | — | [src](../../../core/services/runtime_decision_engine.py#L490) |
| function | `_candidate_is_repo_focused` | `(candidate)` | — | [src](../../../core/services/runtime_decision_engine.py#L495) |
| function | `_candidate_learning_domain` | `(candidate)` | — | [src](../../../core/services/runtime_decision_engine.py#L506) |

## `core/services/runtime_flows.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_flow` | `(*, task_id, current_step=…, step_state=…, plan=…, next_action=…)` | — | [src](../../../core/services/runtime_flows.py#L13) |
| function | `get_flow` | `(flow_id)` | — | [src](../../../core/services/runtime_flows.py#L41) |
| function | `list_flows` | `(*, status=…, task_id=…, limit=…)` | — | [src](../../../core/services/runtime_flows.py#L48) |
| function | `update_flow` | `(flow_id, *, status=…, current_step=…, step_state=…, plan=…, next_action=…, last_error=…, attempt_count=…)` | — | [src](../../../core/services/runtime_flows.py#L68) |
| function | `_decode_flow` | `(flow)` | — | [src](../../../core/services/runtime_flows.py#L103) |

## `core/services/runtime_hook_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_runtime_hook_runtime` | `()` | — | [src](../../../core/services/runtime_hook_runtime.py#L19) |
| function | `stop_runtime_hook_runtime` | `()` | — | [src](../../../core/services/runtime_hook_runtime.py#L36) |
| function | `_hook_runtime_loop` | `(*, subscriber)` | — | [src](../../../core/services/runtime_hook_runtime.py#L49) |

## `core/services/runtime_hooks.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dispatch_unhandled_hook_events` | `(*, limit=…, event_kinds=…)` | — | [src](../../../core/services/runtime_hooks.py#L16) |
| function | `dispatch_hook_event` | `(event)` | — | [src](../../../core/services/runtime_hooks.py#L41) |
| function | `_find_active_task` | `(*, kind, goal, scope)` | — | [src](../../../core/services/runtime_hooks.py#L164) |

## `core/services/runtime_learning_signals.py`
_Runtime learning signal extraction and digest generation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `action_family` | `(action_id)` | — | [src](../../../core/services/runtime_learning_signals.py#L24) |
| function | `action_domain` | `(*, action_id, outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L28) |
| function | `extract_runtime_learning_signals` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L50) |
| function | `_signal` | `(*, outcome_id, source_action_id, signal_key, weight, recorded_at, target_action_id=…, target_family=…, target_domain=…, metadata=…)` | — | [src](../../../core/services/runtime_learning_signals.py#L172) |
| function | `_extract_semantic_signals` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L198) |
| function | `_outcome_looks_like_no_change` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L239) |
| function | `_coerce_domain_key` | `(value)` | — | [src](../../../core/services/runtime_learning_signals.py#L259) |
| function | `generate_learning_digest` | `(summary)` | Distil accumulated runtime learning signals into one actionable insight. | [src](../../../core/services/runtime_learning_signals.py#L270) |

## `core/services/runtime_operational_memory.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_operational_memory_snapshot` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L26) |
| function | `recent_open_loops` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L82) |
| function | `recent_visible_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L93) |
| function | `active_internal_pressures` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L103) |
| function | `active_executive_contradictions` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L113) |
| function | `remembered_user_facts` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L123) |
| function | `active_work_context` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L141) |
| function | `queued_initiatives` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L157) |
| function | `recent_executive_feedback` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L161) |
| function | `recent_persisted_learning` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L165) |
| function | `summarize_executive_feedback` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L169) |
| function | `summarize_note_loop_synergies` | `(*, loops, notes)` | — | [src](../../../core/services/runtime_operational_memory.py#L245) |
| function | `summarize_runtime_learning_signals` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L307) |
| function | `summarize_semantic_feedback` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L347) |
| function | `_feedback_recency_weight` | `(recorded_at, *, now)` | — | [src](../../../core/services/runtime_operational_memory.py#L379) |
| function | `_feedback_age_seconds` | `(recorded_at, *, now)` | — | [src](../../../core/services/runtime_operational_memory.py#L387) |
| function | `_parse_iso_datetime` | `(value)` | — | [src](../../../core/services/runtime_operational_memory.py#L394) |
| function | `_outcome_looks_like_no_change` | `(item)` | — | [src](../../../core/services/runtime_operational_memory.py#L407) |
| function | `_extract_semantic_signals` | `(item)` | — | [src](../../../core/services/runtime_operational_memory.py#L434) |
| function | `_accumulate_signal_bucket` | `(buckets, signal_key, signal_weight, signal_count)` | — | [src](../../../core/services/runtime_operational_memory.py#L482) |
| function | `_domain_key` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_operational_memory.py#L499) |
| function | `_signal_tokens` | `(value)` | — | [src](../../../core/services/runtime_operational_memory.py#L507) |

## `core/services/runtime_resource_signal.py`
_Runtime resource awareness signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_resource_signal_surface` | `()` | — | [src](../../../core/services/runtime_resource_signal.py#L19) |
| function | `_derive_pressure` | `(today_total_tokens, today_cost_usd)` | Bounded heuristic for runtime resource pressure. | [src](../../../core/services/runtime_resource_signal.py#L65) |
| function | `build_runtime_resource_prompt_section` | `()` | — | [src](../../../core/services/runtime_resource_signal.py#L85) |

## `core/services/runtime_self_knowledge.py`
_Runtime self-knowledge — a bounded map of what Jarvis can do, what_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_self_knowledge_map` | `(*, heartbeat_state=…)` | Build a bounded self-knowledge map from existing runtime surfaces. | [src](../../../core/services/runtime_self_knowledge.py#L28) |
| function | `_build_active_capabilities` | `(*, heartbeat_state=…)` | Things Jarvis can actively use right now. | [src](../../../core/services/runtime_self_knowledge.py#L75) |
| function | `_build_approval_gated` | `()` | Things that exist but require user approval. | [src](../../../core/services/runtime_self_knowledge.py#L217) |
| function | `_build_passive_inner_forces` | `()` | Things that influence Jarvis but are not directly actionable tools. | [src](../../../core/services/runtime_self_knowledge.py#L265) |
| function | `_build_structural_constraints` | `()` | Things that are part of Jarvis' nature and boundaries. | [src](../../../core/services/runtime_self_knowledge.py#L522) |
| function | `_build_unavailable_or_inactive` | `()` | Things in the system that are currently not active. | [src](../../../core/services/runtime_self_knowledge.py#L607) |
| function | `build_self_knowledge_prompt_section` | `()` | Build a compact self-knowledge section suitable for prompt inclusion. | [src](../../../core/services/runtime_self_knowledge.py#L665) |
| function | `build_runtime_self_knowledge_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/runtime_self_knowledge.py#L720) |

## `core/services/runtime_self_model.py`
_Bounded runtime self-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_self_model_prompt_lines` | `()` | Build compact prompt lines for the visible self-report section. | [src](../../../core/services/runtime_self_model.py#L61) |

## `core/services/runtime_self_model_affect.py`
_Runtime self-model — affective awareness (flow, wonder, longing, relation)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_affect.py#L19) |
| function | `_derive_flow_state_awareness` | `(*, experiential, inner_voice, support_stream, temporal_feel, mineness)` | Derive a bounded flow-state awareness surface from runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L78) |
| function | `_flow_narrative` | `(*, flow_state, flow_coherence, interruption_signal, carried_flow, voice_mode, pressure_state)` | Compact flow narrative. Empty when flow_state is clear. | [src](../../../core/services/runtime_self_model_affect.py#L211) |
| function | `build_flow_state_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for flow-state awareness. | [src](../../../core/services/runtime_self_model_affect.py#L248) |
| function | `_wonder_source_snapshot` | `()` | Safely pull dream carry signal for wonder derivation. | [src](../../../core/services/runtime_self_model_affect.py#L307) |
| function | `_derive_wonder_awareness` | `(*, inner_voice, flow_state, temporal_feel, mineness, support_stream, sources, wonder_sources)` | Derive a bounded wonder/undren surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L327) |
| function | `_wonder_narrative` | `(*, wonder_state, wonder_source, opening_stream)` | Compact wonder narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L436) |
| function | `build_wonder_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for wonder awareness. | [src](../../../core/services/runtime_self_model_affect.py#L471) |
| function | `_longing_source_snapshot` | `()` | Safely gather bounded absence/relationship support for longing derivation. | [src](../../../core/services/runtime_self_model_affect.py#L556) |
| function | `_derive_longing_awareness` | `(*, temporal_feel, mineness, support_stream, inner_voice, sources, longing_sources)` | Derive a bounded longing/absence surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L623) |
| function | `_longing_narrative` | `(*, longing_state, absence_relation, longing_source)` | Compact longing narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L729) |
| function | `build_longing_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for longing awareness. | [src](../../../core/services/runtime_self_model_affect.py#L759) |
| function | `_relation_continuity_self_source_snapshot` | `()` | Gather bounded substrates for relation continuity as self-truth. | [src](../../../core/services/runtime_self_model_affect.py#L809) |
| function | `_derive_relation_continuity_self_awareness` | `(*, temporal_feel, mineness, longing, relation_sources)` | Derive a small runtime truth when relation continuity touches the self-stream. | [src](../../../core/services/runtime_self_model_affect.py#L892) |
| function | `_relation_continuity_self_narrative` | `(*, relation_continuity_state, relation_self_relation, relation_continuity_source, relation_anchor)` | Compact relation continuity narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L1026) |
| function | `build_relation_continuity_self_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for relation continuity as self-truth. | [src](../../../core/services/runtime_self_model_affect.py#L1053) |

## `core/services/runtime_self_model_boundary.py`
_Runtime self-model — self-boundary clarity + world-contact awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_boundary.py#L28) |
| function | `_internal_pressure_snapshot` | `()` | Pull internal pressure signals for self-boundary derivation. | [src](../../../core/services/runtime_self_model_boundary.py#L55) |
| function | `_external_pressure_snapshot` | `()` | Pull external pressure signals for self-boundary derivation. | [src](../../../core/services/runtime_self_model_boundary.py#L123) |
| function | `_derive_self_boundary_clarity` | `(*, internal, external)` | Synthesise internal + external pressure into a boundary-clarity surface. | [src](../../../core/services/runtime_self_model_boundary.py#L140) |
| function | `_self_boundary_narrative` | `(*, pressure_source, primary_internal, context_pressure, in_tension)` | Compact self-boundary narrative. Empty when ambient. | [src](../../../core/services/runtime_self_model_boundary.py#L209) |
| function | `build_self_boundary_clarity_prompt_section` | `()` | Compact prompt section for self-boundary clarity. None when ambient. | [src](../../../core/services/runtime_self_model_boundary.py#L236) |
| function | `_self_boundary_clarity_surface` | `()` | — | [src](../../../core/services/runtime_self_model_boundary.py#L264) |
| function | `_derive_world_contact` | `(*, tool_intent, browser_body, system_code)` | Synthesise tool/browser/system into a unified world-contact field. | [src](../../../core/services/runtime_self_model_boundary.py#L295) |
| function | `_world_contact_narrative` | `(*, contact_state, parts, concerns)` | Felt-sense world-contact narrative — signal-first, 6-14 words. | [src](../../../core/services/runtime_self_model_boundary.py#L389) |
| function | `build_world_contact_prompt_section` | `()` | Felt-sense prompt section for unified world awareness. None when idle. | [src](../../../core/services/runtime_self_model_boundary.py#L409) |
| function | `_world_contact_surface` | `()` | — | [src](../../../core/services/runtime_self_model_boundary.py#L436) |

## `core/services/runtime_self_model_builder.py`
_Runtime self-model — top-level builder (assembles the full snapshot)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_builder.py#L24) |
| function | `build_runtime_self_model` | `()` | Build a bounded runtime self-model snapshot. | [src](../../../core/services/runtime_self_model_builder.py#L36) |
| function | `_collect_layers` | `()` | Collect all known layers with type annotations. | [src](../../../core/services/runtime_self_model_builder.py#L204) |
| function | `_truth_boundaries` | `()` | Express the key distinctions Jarvis should maintain. | [src](../../../core/services/runtime_self_model_builder.py#L911) |
| function | `_build_summary` | `(layers, boundaries)` | Build a compact summary for prompt injection. | [src](../../../core/services/runtime_self_model_builder.py#L966) |

## `core/services/runtime_self_model_identity.py`
_Runtime self-model — identity awareness (self-insight, narrative identity,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_identity.py#L37) |
| function | `_self_insight_source_snapshot` | `()` | Safely gather bounded insight-bearing seams for self-insight derivation. | [src](../../../core/services/runtime_self_model_identity.py#L88) |
| function | `_derive_self_insight_awareness` | `(*, sources, mineness, flow_state, wonder, longing)` | Derive a bounded self-insight surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_identity.py#L200) |
| function | `_self_insight_narrative` | `(*, insight_state, identity_relation, insight_source)` | Compact self-insight narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L338) |
| function | `build_self_insight_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for self-insight awareness. | [src](../../../core/services/runtime_self_model_identity.py#L375) |
| function | `_derive_narrative_identity_continuity` | `(*, self_insight, sources, mineness, flow_state, wonder, longing)` | Derive a bounded narrative-identity-continuity surface. | [src](../../../core/services/runtime_self_model_identity.py#L476) |
| function | `_narrative_identity_continuity_narrative` | `(*, continuity_state, pattern_relation, identity_source)` | Compact identity-continuity narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L610) |
| function | `build_narrative_identity_continuity_prompt_section` | `()` | Compact heartbeat-side prompt section for narrative identity continuity. | [src](../../../core/services/runtime_self_model_identity.py#L645) |
| function | `_derive_dream_identity_carry_awareness` | `(*, self_insight, identity_continuity, sources, dream_influence, dream_articulation)` | Derive when dream carry begins to shape identity rather than just recur. | [src](../../../core/services/runtime_self_model_identity.py#L760) |
| function | `_dream_identity_carry_narrative` | `(*, carry_state, dream_self_relation, dream_identity_source, influence_target)` | Compact dream identity carry narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L862) |
| function | `build_dream_identity_carry_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for dream carry identity shaping. | [src](../../../core/services/runtime_self_model_identity.py#L893) |
| function | `build_cognitive_core_experiment_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for cognitive-core experiment state. | [src](../../../core/services/runtime_self_model_identity.py#L978) |
| function | `_idle_consolidation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1024) |
| function | `_epistemic_runtime_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1043) |
| function | `_subagent_ecology_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1059) |

## `core/services/runtime_self_model_state.py`
_Runtime self-model — base state surfaces + temporal/mineness awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_state.py#L17) |
| function | `_embodied_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L29) |
| function | `_loop_runtime_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L45) |
| function | `_runtime_task_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L64) |
| function | `_runtime_flow_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L87) |
| function | `_runtime_hook_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L110) |
| function | `_browser_body_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L144) |
| function | `_standing_orders_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L176) |
| function | `_layered_memory_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L197) |
| function | `_affective_meta_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L218) |
| function | `_experiential_runtime_context_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L233) |
| function | `_inner_voice_daemon_surface` | `()` | Read inner voice daemon state for self-model integration. | [src](../../../core/services/runtime_self_model_state.py#L249) |
| function | `_derive_support_stream_awareness` | `(experiential, inner_voice)` | Derive compact self-aware support stream state. | [src](../../../core/services/runtime_self_model_state.py#L265) |
| function | `_runtime_self_appraisal_record` | `(*, kind, state, evidence, confidence, allowed_effects, ttl_minutes)` | Structured source-truth record for runtime self-model renderings. | [src](../../../core/services/runtime_self_model_state.py#L342) |
| function | `_derive_subjective_temporal_feel` | `(experiential, inner_voice)` | Derive a compact subjective temporal feel from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L367) |
| function | `_temporal_narrative` | `(temporal_state, felt_proximity, return_signal, persistence_feel, gap_minutes)` | Compact self-awareness narrative for felt time. | [src](../../../core/services/runtime_self_model_state.py#L468) |
| function | `_mineness_source_snapshot` | `()` | Gather the minimal runtime truth needed for mineness derivation. | [src](../../../core/services/runtime_self_model_state.py#L528) |
| function | `_derive_mineness_ownership` | `(*, experiential, inner_voice, support_stream, temporal_feel, sources)` | Derive a bounded mineness/ownership surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L578) |
| function | `_mineness_narrative` | `(*, ownership_state, carried_thread_state, carried_thread_count, brain_top_focus, brain_continuity, open_loop_signal, voice_mode, support_posture, felt_proximity)` | Compact mineness narrative. Empty in ambient default. | [src](../../../core/services/runtime_self_model_state.py#L680) |
| function | `build_mineness_ownership_prompt_section` | `()` | Compact heartbeat-side prompt section for mineness/ownership. | [src](../../../core/services/runtime_self_model_state.py#L714) |

## `core/services/runtime_self_model_surfaces.py`
_Runtime self-model — small producer/subsystem surfaces + role helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_surfaces.py#L12) |
| function | `_council_runtime_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L24) |
| function | `_agent_outcomes_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L44) |
| function | `_adaptive_planner_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L59) |
| function | `_adaptive_reasoning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L77) |
| function | `_guided_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L95) |
| function | `_dream_influence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L113) |
| function | `_adaptive_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L131) |
| function | `_dream_articulation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L149) |
| function | `_prompt_evolution_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L168) |
| function | `_self_system_code_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L188) |
| function | `_tool_intent_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L208) |
| function | `_heartbeat_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L233) |
| function | `_visible_chat_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L243) |
| function | `_cheap_lane_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L255) |
| function | `_local_lane_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L270) |
| function | `_private_brain_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L285) |
| function | `_approval_pipeline_role` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L297) |
| function | `_producer_layers` | `()` | Build producer layers from internal cadence state. | [src](../../../core/services/runtime_self_model_surfaces.py#L308) |
| function | `_producer_label` | `(name)` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L367) |
| function | `_groundwork_layers` | `()` | Layers that exist but only as candidates/proposals. | [src](../../../core/services/runtime_self_model_surfaces.py#L380) |
| function | `_cognitive_architecture_awareness` | `()` | Build awareness of the cognitive architecture from shared runtime truth. | [src](../../../core/services/runtime_self_model_surfaces.py#L416) |
| function | `_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L435) |
| function | `_cognitive_core_experiment_carry_snapshot` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L466) |
| function | `build_authenticity_prompt_section` | `()` | Return a prompt line when Jarvis has crystallized tastes or values — suppressed otherwise. | [src](../../../core/services/runtime_self_model_surfaces.py#L478) |
| function | `_authenticity_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L507) |
| function | `_valence_trajectory_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L533) |
| function | `build_valence_trajectory_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L541) |
| function | `_developmental_valence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L549) |
| function | `build_developmental_valence_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L557) |
| function | `_desperation_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L565) |
| function | `build_desperation_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L573) |
| function | `_calm_anchor_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L581) |
| function | `build_calm_anchor_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L589) |
| function | `_memory_breathing_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L597) |
| function | `_creative_projects_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L605) |
| function | `build_creative_projects_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L613) |
| function | `_day_shape_memory_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L621) |
| function | `build_day_shape_memory_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L629) |
| function | `_avoidance_detector_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L637) |
| function | `build_avoidance_detector_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L645) |
| function | `_thought_thread_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L653) |
| function | `build_thought_thread_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L661) |
| function | `_skill_contract_registry_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L669) |
| function | `_memory_write_policy_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L677) |
| function | `build_memory_write_policy_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L685) |
| function | `_spaced_repetition_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L693) |
| function | `build_spaced_repetition_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L701) |
| function | `_scheduled_job_windows_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L709) |
| function | `_automation_dsl_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L717) |
| function | `_outcome_learning_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L725) |
| function | `_jobs_engine_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L733) |
| function | `_prompt_mutation_loop_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L741) |
| function | `build_prompt_mutation_loop_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L749) |
| function | `_file_watch_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L757) |
| function | `build_file_watch_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L765) |
| function | `_reboot_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L773) |
| function | `build_reboot_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L781) |
| function | `_proprioception_metrics_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L789) |
| function | `build_proprioception_metrics_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L797) |
| function | `_anticipatory_action_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L805) |
| function | `build_anticipatory_action_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L813) |
| function | `_cross_session_threads_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L821) |
| function | `build_cross_session_threads_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L829) |
| function | `_autonomous_outreach_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L837) |
| function | `_infra_weather_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L845) |
| function | `build_infra_weather_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L853) |
| function | `_temporal_rhythm_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L861) |
| function | `build_temporal_rhythm_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L869) |
| function | `_relation_dynamics_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L877) |
| function | `build_relation_dynamics_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L885) |
| function | `_creative_instinct_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L893) |
| function | `build_creative_instinct_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L901) |
| function | `_autonomous_work_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L909) |
| function | `build_autonomous_work_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L917) |
| function | `_dream_consolidation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L925) |
| function | `build_dream_consolidation_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L933) |
| function | `_text_resonance_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L941) |
| function | `build_text_resonance_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L949) |
| function | `_creative_impulse_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L957) |
| function | `build_creative_impulse_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L965) |
| function | `_shadow_scan_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L973) |
| function | `build_shadow_scan_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L981) |
| function | `_mortality_awareness_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L989) |
| function | `build_mortality_awareness_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L997) |
| function | `_relational_warmth_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1005) |
| function | `build_relational_warmth_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1013) |
| function | `_collective_pulse_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1021) |
| function | `build_collective_pulse_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1029) |
| function | `_action_router_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1037) |
| function | `build_action_router_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1045) |
| function | `_sustained_attention_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1053) |
| function | `build_sustained_attention_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1061) |
| function | `_memory_density_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1069) |
| function | `build_memory_density_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1077) |
| function | `_deep_reflection_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1085) |
| function | `build_deep_reflection_prompt_section` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1093) |
| function | `build_physical_presence_prompt_section` | `()` | Return a somatic line when hardware state is non-trivial — suppressed when all quiet. | [src](../../../core/services/runtime_self_model_surfaces.py#L1101) |
| function | `_physical_presence_surface` | `()` | — | [src](../../../core/services/runtime_self_model_surfaces.py#L1147) |

## `core/services/runtime_surface_cache.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `runtime_surface_cache` | `()` | — | [src](../../../core/services/runtime_surface_cache.py#L21) |
| function | `get_cached_runtime_surface` | `(key, builder)` | — | [src](../../../core/services/runtime_surface_cache.py#L35) |
| function | `peek_cached_runtime_surface` | `(key)` | — | [src](../../../core/services/runtime_surface_cache.py#L44) |
| function | `get_timed_runtime_surface` | `(key, ttl_seconds, builder)` | — | [src](../../../core/services/runtime_surface_cache.py#L51) |
| function | `invalidate_timed_runtime_surface` | `(*keys_or_prefixes)` | Drop matchende entries fra den KRYDS-TUR TIMED-cache (2026-06-30). | [src](../../../core/services/runtime_surface_cache.py#L86) |

## `core/services/runtime_tasks.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_task` | `(*, kind, goal, origin, scope=…, priority=…, flow_id=…, session_id=…, run_id=…, owner=…)` | — | [src](../../../core/services/runtime_tasks.py#L16) |
| function | `list_tasks` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/services/runtime_tasks.py#L58) |
| function | `get_task` | `(task_id)` | — | [src](../../../core/services/runtime_tasks.py#L77) |
| function | `update_task` | `(task_id, *, status=…, flow_id=…, session_id=…, run_id=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…)` | — | [src](../../../core/services/runtime_tasks.py#L81) |
| function | `_task_sort_key` | `(task)` | — | [src](../../../core/services/runtime_tasks.py#L117) |
| function | `_priority_with_runtime_bias` | `(requested_priority, *, kind, goal, scope, origin)` | — | [src](../../../core/services/runtime_tasks.py#L127) |

