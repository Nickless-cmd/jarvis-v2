# `core.runtime.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/db_runtime_cognition_signals.py`
_Persistence for Jarvis' runtime cognition-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_reflective_critic` | `(*, critic_id, critic_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L31) |
| function | `list_runtime_reflective_critics` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L247) |
| function | `get_runtime_reflective_critic` | `(critic_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L293) |
| function | `update_runtime_reflective_critic_status` | `(critic_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L330) |
| function | `supersede_runtime_reflective_critics` | `(*, critic_type, exclude_critic_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L363) |
| function | `upsert_runtime_awareness_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L394) |
| function | `list_runtime_awareness_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L604) |
| function | `get_runtime_awareness_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L650) |
| function | `update_runtime_awareness_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L687) |
| function | `supersede_runtime_awareness_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L720) |
| function | `upsert_runtime_reflection_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L751) |
| function | `list_runtime_reflection_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L816) |
| function | `get_runtime_reflection_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L862) |
| function | `update_runtime_reflection_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L899) |
| function | `supersede_runtime_reflection_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L932) |
| function | `upsert_runtime_witness_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L963) |
| function | `list_runtime_witness_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1028) |
| function | `get_runtime_witness_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1074) |
| function | `update_runtime_witness_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1111) |
| function | `supersede_runtime_witness_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1144) |
| function | `upsert_runtime_internal_opposition_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1175) |
| function | `list_runtime_internal_opposition_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1240) |
| function | `get_runtime_internal_opposition_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1286) |
| function | `update_runtime_internal_opposition_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1323) |
| function | `supersede_runtime_internal_opposition_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1356) |
| function | `upsert_runtime_meaning_significance_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1387) |
| function | `list_runtime_meaning_significance_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1452) |
| function | `get_runtime_meaning_significance_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1498) |
| function | `update_runtime_meaning_significance_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1535) |
| function | `supersede_runtime_meaning_significance_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1568) |
| function | `upsert_runtime_metabolism_state_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1599) |
| function | `list_runtime_metabolism_state_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1664) |
| function | `get_runtime_metabolism_state_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1710) |
| function | `update_runtime_metabolism_state_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1747) |
| function | `supersede_runtime_metabolism_state_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1780) |
| function | `upsert_runtime_executive_contradiction_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1811) |
| function | `list_runtime_executive_contradiction_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1876) |
| function | `get_runtime_executive_contradiction_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1922) |
| function | `update_runtime_executive_contradiction_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1961) |
| function | `supersede_runtime_executive_contradiction_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1994) |
| function | `_ensure_runtime_reflective_critic_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2025) |
| function | `_ensure_runtime_awareness_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2067) |
| function | `_ensure_runtime_reflection_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2109) |
| function | `_ensure_runtime_witness_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2151) |
| function | `_ensure_runtime_internal_opposition_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2193) |
| function | `_ensure_runtime_meaning_significance_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2235) |
| function | `_ensure_runtime_metabolism_state_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2277) |
| function | `_ensure_runtime_executive_contradiction_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2319) |
| function | `_runtime_meaning_significance_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2363) |
| function | `_runtime_metabolism_state_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2390) |
| function | `_runtime_executive_contradiction_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2415) |
| function | `_runtime_reflective_critic_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2442) |
| function | `_runtime_awareness_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2467) |
| function | `_runtime_reflection_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2492) |
| function | `_runtime_witness_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2517) |
| function | `_runtime_internal_opposition_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2542) |

## `core/runtime/db_runtime_diary.py`
_Persistence for the runtime diary-synthesis signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_runtime_diary_synthesis_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_diary.py#L16) |
| function | `get_diary_synthesis_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_diary.py#L61) |
| function | `update_diary_synthesis_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_diary.py#L97) |
| function | `supersede_diary_synthesis_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_diary.py#L131) |
| function | `upsert_diary_synthesis_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_diary.py#L161) |
| function | `_runtime_diary_synthesis_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_diary.py#L324) |
| function | `_ensure_runtime_diary_synthesis_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_diary.py#L350) |

## `core/runtime/db_runtime_dream.py`
_Persistence for Jarvis' runtime dream signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_runtime_dream_hypothesis_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_dream.py#L22) |
| function | `_ensure_runtime_dream_adoption_candidate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_dream.py#L64) |
| function | `_ensure_runtime_dream_influence_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_dream.py#L106) |
| function | `_runtime_dream_hypothesis_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_dream.py#L148) |
| function | `_runtime_dream_adoption_candidate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_dream.py#L172) |
| function | `_runtime_dream_influence_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_dream.py#L196) |
| function | `upsert_runtime_dream_hypothesis_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L220) |
| function | `list_runtime_dream_hypothesis_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L284) |
| function | `get_runtime_dream_hypothesis_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_dream.py#L336) |
| function | `update_runtime_dream_hypothesis_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L372) |
| function | `supersede_runtime_dream_hypothesis_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_dream.py#L404) |
| function | `upsert_runtime_dream_adoption_candidate` | `(*, candidate_id, candidate_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L434) |
| function | `list_runtime_dream_adoption_candidates` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L498) |
| function | `get_runtime_dream_adoption_candidate` | `(candidate_id)` | — | [src](../../../core/runtime/db_runtime_dream.py#L550) |
| function | `update_runtime_dream_adoption_candidate_status` | `(candidate_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L586) |
| function | `supersede_runtime_dream_adoption_candidates_for_domain` | `(*, domain_key, exclude_candidate_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_dream.py#L618) |
| function | `upsert_runtime_dream_influence_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L648) |
| function | `list_runtime_dream_influence_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L712) |
| function | `get_runtime_dream_influence_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_dream.py#L764) |
| function | `update_runtime_dream_influence_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_dream.py#L800) |
| function | `supersede_runtime_dream_influence_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_dream.py#L832) |

## `core/runtime/db_runtime_executive_signals.py`
_Persistence for Jarvis' runtime executive-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_goal_signal` | `(*, goal_id, goal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L39) |
| function | `list_runtime_goal_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L254) |
| function | `get_runtime_goal_signal` | `(goal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L299) |
| function | `update_runtime_goal_signal_status` | `(goal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L335) |
| function | `supersede_runtime_goal_signals` | `(*, goal_type, exclude_goal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L367) |
| function | `_ensure_runtime_goal_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L397) |
| function | `_runtime_goal_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L438) |
| function | `upsert_runtime_world_model_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L462) |
| function | `list_runtime_world_model_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L677) |
| function | `get_runtime_world_model_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L722) |
| function | `update_runtime_world_model_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L758) |
| function | `supersede_runtime_world_model_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L790) |
| function | `_ensure_runtime_world_model_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L820) |
| function | `_runtime_world_model_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L861) |
| function | `upsert_runtime_development_focus` | `(*, focus_id, focus_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L885) |
| function | `list_runtime_development_focuses` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1102) |
| function | `get_runtime_development_focus` | `(focus_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1147) |
| function | `update_runtime_development_focus_status` | `(focus_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1183) |
| function | `supersede_runtime_development_focuses` | `(*, focus_type, exclude_focus_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1215) |
| function | `_ensure_runtime_development_focus_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1245) |
| function | `_runtime_development_focus_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1286) |
| function | `upsert_runtime_autonomy_pressure_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1310) |
| function | `list_runtime_autonomy_pressure_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1374) |
| function | `get_runtime_autonomy_pressure_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1419) |
| function | `update_runtime_autonomy_pressure_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1455) |
| function | `supersede_runtime_autonomy_pressure_signals_for_type` | `(*, pressure_type, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1487) |
| function | `_ensure_runtime_autonomy_pressure_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1517) |
| function | `_runtime_autonomy_pressure_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1558) |
| function | `upsert_runtime_open_loop_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1582) |
| function | `list_runtime_open_loop_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1646) |
| function | `get_runtime_open_loop_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1691) |
| function | `update_runtime_open_loop_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1727) |
| function | `supersede_runtime_open_loop_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1759) |
| function | `_ensure_runtime_open_loop_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1789) |
| function | `_runtime_open_loop_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1830) |
| function | `upsert_runtime_open_loop_closure_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1854) |
| function | `list_runtime_open_loop_closure_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1918) |
| function | `get_runtime_open_loop_closure_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1963) |
| function | `update_runtime_open_loop_closure_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2001) |
| function | `supersede_runtime_open_loop_closure_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2033) |
| function | `_ensure_runtime_open_loop_closure_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2063) |
| function | `_runtime_open_loop_closure_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2104) |
| function | `upsert_runtime_contract_candidate` | `(*, candidate_id, candidate_type, target_file, status, source_kind, source_mode, actor, session_id, run_id, canonical_key, summary, reason, evidence_summary, support_summary, confidence, evidence_class, support_count, session_count, created_at, updated_at, status_reason=…, proposed_value=…, write_section=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2128) |
| function | `list_runtime_contract_candidates` | `(*, candidate_type=…, target_file=…, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2393) |
| function | `get_runtime_contract_candidate` | `(candidate_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2451) |
| function | `runtime_contract_candidate_counts` | `()` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2492) |
| function | `update_runtime_contract_candidate_status` | `(candidate_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2509) |
| function | `supersede_runtime_contract_candidates` | `(*, candidate_type, target_file, canonical_key, exclude_candidate_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2541) |
| function | `_ensure_runtime_contract_candidate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2579) |
| function | `_runtime_contract_candidate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2642) |
| function | `upsert_runtime_proactive_loop_lifecycle_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2671) |
| function | `list_runtime_proactive_loop_lifecycle_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2735) |
| function | `get_runtime_proactive_loop_lifecycle_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2780) |
| function | `update_runtime_proactive_loop_lifecycle_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2818) |
| function | `supersede_runtime_proactive_loop_lifecycle_signals_for_kind` | `(*, loop_kind, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2850) |
| function | `_ensure_runtime_proactive_loop_lifecycle_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2880) |
| function | `_runtime_proactive_loop_lifecycle_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2923) |
| function | `upsert_runtime_proactive_question_gate` | `(*, gate_id, gate_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2949) |
| function | `list_runtime_proactive_question_gates` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3013) |
| function | `get_runtime_proactive_question_gate` | `(gate_id)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3058) |
| function | `update_runtime_proactive_question_gate_status` | `(gate_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3094) |
| function | `supersede_runtime_proactive_question_gates_for_kind` | `(*, gate_type, exclude_gate_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3126) |
| function | `_ensure_runtime_proactive_question_gate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3156) |
| function | `_runtime_proactive_question_gate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3197) |

## `core/runtime/db_runtime_flows.py`
_Persistence for the `runtime_flows` table — multi-step flow state per task._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_flows_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_flows.py#L13) |
| function | `_runtime_flow_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_flows.py#L40) |
| function | `create_runtime_flow` | `(*, flow_id, task_id, status, current_step=…, step_state=…, plan_json=…, next_action=…, last_error=…, attempt_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_flows.py#L56) |
| function | `get_runtime_flow` | `(flow_id)` | — | [src](../../../core/runtime/db_runtime_flows.py#L109) |
| function | `list_runtime_flows` | `(*, status=…, task_id=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_flows.py#L136) |
| function | `update_runtime_flow` | `(flow_id, *, status=…, current_step=…, step_state=…, plan_json=…, next_action=…, last_error=…, attempt_count=…, updated_at)` | — | [src](../../../core/runtime/db_runtime_flows.py#L176) |

## `core/runtime/db_runtime_hooks.py`
_Persistence for the `runtime_hook_dispatches` table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_hooks_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_hooks.py#L13) |
| function | `record_runtime_hook_dispatch` | `(*, event_id, event_kind, status, task_id=…, flow_id=…, summary=…, created_at)` | — | [src](../../../core/runtime/db_runtime_hooks.py#L36) |
| function | `get_runtime_hook_dispatch` | `(event_id)` | — | [src](../../../core/runtime/db_runtime_hooks.py#L84) |
| function | `list_runtime_hook_dispatches` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_hooks.py#L115) |

## `core/runtime/db_runtime_initiatives.py`
_Persistence for the runtime-initiatives cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_runtime_initiatives_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L16) |
| function | `_runtime_initiative_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L78) |
| function | `create_runtime_initiative` | `(*, initiative_id, initiative_type=…, focus, why_text=…, source=…, source_id=…, status=…, priority=…, detected_at, first_seeded_at=…, next_attempt_at=…, updated_at, scheduled_for_user_id=…, initiated_by=…)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L106) |
| function | `get_runtime_initiative` | `(initiative_id)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L178) |
| function | `find_pending_runtime_initiative_by_focus` | `(focus, *, initiative_type=…)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L217) |
| function | `list_runtime_initiatives` | `(*, status=…, initiative_type=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L269) |
| function | `update_runtime_initiative` | `(initiative_id, *, status=…, initiative_type=…, priority=…, detected_at=…, why_text=…, first_seeded_at=…, attempt_count=…, last_attempt_at=…, next_attempt_at=…, blocked_reason=…, acted_at=…, last_action_at=…, abandoned_at=…, action_summary=…, updated_at)` | — | [src](../../../core/runtime/db_runtime_initiatives.py#L328) |
| function | `approve_runtime_initiative` | `(initiative_id, *, outcome_note=…, updated_at)` | Mark an initiative as user-approved. Sets user_approved_at and outcome='approved'. | [src](../../../core/runtime/db_runtime_initiatives.py#L391) |
| function | `reject_runtime_initiative` | `(initiative_id, *, outcome_note=…, updated_at)` | Mark an initiative as user-rejected. Sets outcome='rejected' and expires it. | [src](../../../core/runtime/db_runtime_initiatives.py#L418) |

## `core/runtime/db_runtime_misc.py`
_Persistence for small self-contained runtime CRUD domains._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_relevant_experiential_memories` | `(*, context, limit=…)` | Find experiential memories relevant to the given context. | [src](../../../core/runtime/db_runtime_misc.py#L44) |
| function | `list_session_distillation_records` | `(*, limit=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L85) |
| function | `_ensure_cached_affective_state_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L110) |
| function | `save_cached_affective_state` | `(rendered_text, signals_json)` | — | [src](../../../core/runtime/db_runtime_misc.py#L123) |
| function | `get_cached_affective_state` | `(max_age_seconds=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L134) |
| function | `_ensure_experiment_settings_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L154) |
| function | `get_experiment_enabled` | `(experiment_id)` | Return True if experiment is enabled. Defaults to True if no row exists. | [src](../../../core/runtime/db_runtime_misc.py#L164) |
| function | `set_experiment_enabled` | `(experiment_id, enabled)` | Enable or disable an experiment. Creates row if absent. | [src](../../../core/runtime/db_runtime_misc.py#L177) |
| function | `_ensure_recurrence_iterations_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L193) |
| function | `insert_recurrence_iteration` | `(*, iteration_id, content, keywords, stability_score, iteration_number)` | — | [src](../../../core/runtime/db_runtime_misc.py#L206) |
| function | `get_latest_recurrence_iteration` | `()` | — | [src](../../../core/runtime/db_runtime_misc.py#L225) |
| function | `list_recurrence_iterations` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L244) |
| function | `_ensure_broadcast_events_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L269) |
| function | `insert_broadcast_event` | `(*, event_id, topic_cluster, sources, source_count, payload_summary)` | — | [src](../../../core/runtime/db_runtime_misc.py#L282) |
| function | `list_broadcast_events` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L301) |
| function | `_ensure_meta_cognition_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L326) |
| function | `insert_meta_cognition_record` | `(*, record_id, meta_observation, meta_meta_observation, meta_depth, input_state_summary)` | — | [src](../../../core/runtime/db_runtime_misc.py#L339) |
| function | `list_meta_cognition_records` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L358) |
| function | `_ensure_attention_blink_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L383) |
| function | `insert_attention_blink_result` | `(*, test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation)` | — | [src](../../../core/runtime/db_runtime_misc.py#L397) |
| function | `list_attention_blink_results` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L417) |
| function | `_ensure_session_summaries_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L444) |
| function | `session_summary_insert` | `(*, session_id, run_id=…, summary, key_topics=…, decisions_made=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L466) |
| function | `session_summary_recent` | `(limit=…)` | Return the most recent session summaries (across all sessions). | [src](../../../core/runtime/db_runtime_misc.py#L486) |
| function | `session_summary_for_session` | `(session_id)` | Return the latest summary for a specific session. | [src](../../../core/runtime/db_runtime_misc.py#L508) |
| function | `session_summary_cleanup` | `(max_age_days=…)` | Delete session summaries older than max_age_days. | [src](../../../core/runtime/db_runtime_misc.py#L529) |
| function | `_ensure_signal_archive_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L544) |
| function | `signal_decay_archive_and_delete` | `(*, stale_hours=…)` | Archive and delete signals marked stale for longer than stale_hours. | [src](../../../core/runtime/db_runtime_misc.py#L568) |
| function | `signal_archive_cleanup` | `(max_age_days=…)` | Delete archived signals older than max_age_days. | [src](../../../core/runtime/db_runtime_misc.py#L632) |
| function | `signal_archive_recent` | `(limit=…)` | Return recent archived signals for debugging. | [src](../../../core/runtime/db_runtime_misc.py#L642) |
| function | `_ensure_aesthetic_motif_log_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L661) |
| function | `aesthetic_motif_log_insert` | `(*, source, motif, confidence)` | — | [src](../../../core/runtime/db_runtime_misc.py#L678) |
| function | `aesthetic_motif_log_unique_motifs` | `()` | — | [src](../../../core/runtime/db_runtime_misc.py#L696) |
| function | `aesthetic_motif_log_summary` | `()` | — | [src](../../../core/runtime/db_runtime_misc.py#L705) |
| function | `_ensure_channel_attachments_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L726) |
| function | `store_channel_attachment` | `(*, conn, attachment_id, session_id, channel_type, filename, mime_type, size_bytes, local_path, source_url)` | — | [src](../../../core/runtime/db_runtime_misc.py#L749) |
| function | `get_channel_attachment` | `(*, conn, attachment_id)` | — | [src](../../../core/runtime/db_runtime_misc.py#L775) |
| function | `list_channel_attachments` | `(*, conn, session_id, limit=…)` | — | [src](../../../core/runtime/db_runtime_misc.py#L792) |

## `core/runtime/db_runtime_private.py`
_Persistence for Jarvis' runtime private-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_private_inner_note_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L31) |
| function | `list_runtime_private_inner_note_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L95) |
| function | `get_runtime_private_inner_note_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L140) |
| function | `update_runtime_private_inner_note_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L176) |
| function | `supersede_runtime_private_inner_note_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L208) |
| function | `upsert_runtime_private_initiative_tension_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L238) |
| function | `list_runtime_private_initiative_tension_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L304) |
| function | `get_runtime_private_initiative_tension_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L349) |
| function | `update_runtime_private_initiative_tension_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L387) |
| function | `supersede_runtime_private_initiative_tension_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L419) |
| function | `upsert_runtime_private_inner_interplay_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L449) |
| function | `list_runtime_private_inner_interplay_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L513) |
| function | `get_runtime_private_inner_interplay_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L558) |
| function | `update_runtime_private_inner_interplay_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L596) |
| function | `supersede_runtime_private_inner_interplay_signals_for_relation` | `(*, relation_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L628) |
| function | `upsert_runtime_private_state_snapshot` | `(*, snapshot_id, snapshot_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L658) |
| function | `list_runtime_private_state_snapshots` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L722) |
| function | `get_runtime_private_state_snapshot` | `(snapshot_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L767) |
| function | `update_runtime_private_state_snapshot_status` | `(snapshot_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L803) |
| function | `supersede_runtime_private_state_snapshots_for_focus` | `(*, focus_key, exclude_snapshot_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L835) |
| function | `upsert_runtime_private_temporal_curiosity_state` | `(*, state_id, state_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L865) |
| function | `list_runtime_private_temporal_curiosity_states` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L929) |
| function | `get_runtime_private_temporal_curiosity_state` | `(state_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L974) |
| function | `update_runtime_private_temporal_curiosity_state_status` | `(state_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L1012) |
| function | `supersede_runtime_private_temporal_curiosity_states_for_focus` | `(*, focus_key, exclude_state_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L1044) |
| function | `upsert_runtime_private_temporal_promotion_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_private.py#L1074) |
| function | `list_runtime_private_temporal_promotion_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L1140) |
| function | `get_runtime_private_temporal_promotion_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_private.py#L1185) |
| function | `update_runtime_private_temporal_promotion_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_private.py#L1223) |
| function | `supersede_runtime_private_temporal_promotion_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_private.py#L1255) |
| function | `_ensure_runtime_private_inner_note_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1285) |
| function | `_ensure_runtime_private_initiative_tension_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1326) |
| function | `_ensure_runtime_private_inner_interplay_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1369) |
| function | `_ensure_runtime_private_state_snapshot_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1412) |
| function | `_ensure_runtime_private_temporal_curiosity_state_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1453) |
| function | `_ensure_runtime_private_temporal_promotion_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1496) |
| function | `_runtime_private_inner_note_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1539) |
| function | `_runtime_private_initiative_tension_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1563) |
| function | `_runtime_private_inner_interplay_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1589) |
| function | `_runtime_private_state_snapshot_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1615) |
| function | `_runtime_private_temporal_curiosity_state_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1639) |
| function | `_runtime_private_temporal_promotion_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1665) |

## `core/runtime/db_runtime_relational_signals.py`
_Persistence for Jarvis' runtime relational-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_user_md_update_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L32) |
| function | `list_runtime_user_md_update_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L97) |
| function | `get_runtime_user_md_update_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L143) |
| function | `update_runtime_user_md_update_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L180) |
| function | `supersede_runtime_user_md_update_proposals_for_dimension` | `(*, dimension_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L213) |
| function | `upsert_runtime_user_understanding_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L244) |
| function | `list_runtime_user_understanding_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L309) |
| function | `get_runtime_user_understanding_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L355) |
| function | `update_runtime_user_understanding_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L392) |
| function | `supersede_runtime_user_understanding_signals_for_dimension` | `(*, dimension_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L425) |
| function | `upsert_runtime_inner_visible_support_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L456) |
| function | `list_runtime_inner_visible_support_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L521) |
| function | `get_runtime_inner_visible_support_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L567) |
| function | `update_runtime_inner_visible_support_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L606) |
| function | `supersede_runtime_inner_visible_support_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L639) |
| function | `upsert_runtime_relation_state_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L670) |
| function | `list_runtime_relation_state_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L735) |
| function | `get_runtime_relation_state_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L781) |
| function | `update_runtime_relation_state_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L818) |
| function | `supersede_runtime_relation_state_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L851) |
| function | `upsert_runtime_relation_continuity_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L882) |
| function | `list_runtime_relation_continuity_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L947) |
| function | `get_runtime_relation_continuity_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L993) |
| function | `update_runtime_relation_continuity_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1030) |
| function | `supersede_runtime_relation_continuity_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1063) |
| function | `upsert_runtime_attachment_topology_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1094) |
| function | `upsert_runtime_loyalty_gradient_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1159) |
| function | `list_runtime_attachment_topology_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1224) |
| function | `list_runtime_loyalty_gradient_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1270) |
| function | `get_runtime_attachment_topology_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1316) |
| function | `get_runtime_loyalty_gradient_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1353) |
| function | `update_runtime_attachment_topology_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1390) |
| function | `update_runtime_loyalty_gradient_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1423) |
| function | `supersede_runtime_attachment_topology_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1456) |
| function | `supersede_runtime_loyalty_gradient_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1487) |
| function | `_ensure_runtime_user_md_update_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1518) |
| function | `_ensure_runtime_user_understanding_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1560) |
| function | `_ensure_runtime_inner_visible_support_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1602) |
| function | `_ensure_runtime_relation_state_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1646) |
| function | `_ensure_runtime_relation_continuity_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1688) |
| function | `_ensure_runtime_attachment_topology_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1730) |
| function | `_ensure_runtime_loyalty_gradient_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1772) |
| function | `_runtime_user_understanding_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1814) |
| function | `_runtime_inner_visible_support_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1839) |
| function | `_runtime_relation_state_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1866) |
| function | `_runtime_relation_continuity_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1891) |
| function | `_runtime_attachment_topology_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1916) |
| function | `_runtime_loyalty_gradient_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1941) |
| function | `_runtime_user_md_update_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1966) |

## `core/runtime/db_runtime_self.py`
_Persistence for Jarvis' runtime self-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_self_model_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L32) |
| function | `list_runtime_self_model_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L247) |
| function | `get_runtime_self_model_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_self.py#L292) |
| function | `update_runtime_self_model_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L328) |
| function | `supersede_runtime_self_model_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self.py#L360) |
| function | `upsert_runtime_self_authored_prompt_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L390) |
| function | `list_runtime_self_authored_prompt_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L454) |
| function | `get_runtime_self_authored_prompt_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_self.py#L499) |
| function | `update_runtime_self_authored_prompt_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L537) |
| function | `supersede_runtime_self_authored_prompt_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self.py#L569) |
| function | `upsert_runtime_self_narrative_continuity_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_self.py#L599) |
| function | `list_runtime_self_narrative_continuity_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L663) |
| function | `get_runtime_self_narrative_continuity_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_self.py#L708) |
| function | `update_runtime_self_narrative_continuity_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L746) |
| function | `supersede_runtime_self_narrative_continuity_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self.py#L778) |
| function | `upsert_runtime_selfhood_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L808) |
| function | `list_runtime_selfhood_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L872) |
| function | `get_runtime_selfhood_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_self.py#L917) |
| function | `update_runtime_selfhood_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self.py#L953) |
| function | `supersede_runtime_selfhood_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self.py#L985) |
| function | `_ensure_runtime_self_model_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1015) |
| function | `_ensure_runtime_self_authored_prompt_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1056) |
| function | `_ensure_runtime_self_narrative_continuity_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1099) |
| function | `_ensure_runtime_selfhood_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1142) |
| function | `_runtime_self_narrative_continuity_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1183) |
| function | `_runtime_self_model_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1209) |
| function | `_runtime_self_authored_prompt_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1233) |
| function | `_runtime_selfhood_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1259) |

## `core/runtime/db_runtime_self_review.py`
_Persistence for Jarvis' runtime self-review signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_runtime_self_review_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L22) |
| function | `_ensure_runtime_self_review_record_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L63) |
| function | `_ensure_runtime_self_review_run_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L104) |
| function | `_ensure_runtime_self_review_outcome_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L145) |
| function | `_ensure_runtime_self_review_cadence_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L186) |
| function | `_runtime_self_review_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L227) |
| function | `_runtime_self_review_record_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L251) |
| function | `_runtime_self_review_run_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L275) |
| function | `_runtime_self_review_outcome_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L299) |
| function | `_runtime_self_review_cadence_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L323) |
| function | `upsert_runtime_self_review_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L347) |
| function | `list_runtime_self_review_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L411) |
| function | `get_runtime_self_review_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L456) |
| function | `update_runtime_self_review_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L492) |
| function | `supersede_runtime_self_review_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L524) |
| function | `upsert_runtime_self_review_record` | `(*, record_id, record_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L554) |
| function | `list_runtime_self_review_records` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L618) |
| function | `get_runtime_self_review_record` | `(record_id)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L663) |
| function | `update_runtime_self_review_record_status` | `(record_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L699) |
| function | `supersede_runtime_self_review_records_for_domain` | `(*, domain_key, exclude_record_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L731) |
| function | `upsert_runtime_self_review_run` | `(*, run_id, run_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, record_run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L761) |
| function | `list_runtime_self_review_runs` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L825) |
| function | `get_runtime_self_review_run` | `(run_id)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L870) |
| function | `update_runtime_self_review_run_status` | `(run_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L906) |
| function | `supersede_runtime_self_review_runs_for_domain` | `(*, domain_key, exclude_run_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L938) |
| function | `upsert_runtime_self_review_outcome` | `(*, outcome_id, outcome_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, review_run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L968) |
| function | `list_runtime_self_review_outcomes` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1032) |
| function | `get_runtime_self_review_outcome` | `(outcome_id)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1077) |
| function | `update_runtime_self_review_outcome_status` | `(outcome_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1113) |
| function | `supersede_runtime_self_review_outcomes_for_domain` | `(*, domain_key, exclude_outcome_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1145) |
| function | `upsert_runtime_self_review_cadence_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1175) |
| function | `list_runtime_self_review_cadence_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1239) |
| function | `get_runtime_self_review_cadence_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1284) |
| function | `update_runtime_self_review_cadence_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1320) |
| function | `supersede_runtime_self_review_cadence_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_self_review.py#L1352) |

## `core/runtime/db_runtime_signals.py`
_Persistence for the runtime learning/outcome signal tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_signals_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_signals.py#L17) |
| function | `_runtime_action_outcome_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_signals.py#L76) |
| function | `_runtime_learning_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_signals.py#L101) |
| function | `recent_runtime_action_outcomes` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_signals.py#L122) |
| function | `recent_runtime_learning_signals` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_signals.py#L146) |
| function | `record_runtime_action_outcome` | `(*, action_id, decision_mode, decision_reason, decision_score, payload_json, result_status, result_summary, result_json, recorded_at)` | — | [src](../../../core/runtime/db_runtime_signals.py#L171) |
| function | `record_runtime_learning_signal` | `(*, outcome_id, source_action_id, target_action_id, target_family, target_domain, signal_key, signal_weight, signal_count, metadata_json, recorded_at)` | — | [src](../../../core/runtime/db_runtime_signals.py#L239) |

## `core/runtime/db_runtime_tasks.py`
_Persistence for the `runtime_tasks` table — Jarvis' durable task queue._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_tasks_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L13) |
| function | `_runtime_task_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L52) |
| function | `create_runtime_task` | `(*, task_id, kind, origin, status, goal, scope=…, priority=…, flow_id=…, session_id=…, run_id=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L74) |
| function | `get_runtime_task` | `(task_id)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L145) |
| function | `list_runtime_tasks` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L178) |
| function | `update_runtime_task` | `(task_id, *, status=…, flow_id=…, session_id=…, run_id=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…, updated_at)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L224) |

## `core/runtime/db_runtime_temporal_memory_signals.py`
_Persistence for Jarvis' runtime temporal/memory-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_temporal_recurrence_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L35) |
| function | `list_runtime_temporal_recurrence_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L99) |
| function | `get_runtime_temporal_recurrence_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L144) |
| function | `update_runtime_temporal_recurrence_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L180) |
| function | `supersede_runtime_temporal_recurrence_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L212) |
| function | `_ensure_runtime_temporal_recurrence_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L242) |
| function | `_runtime_temporal_recurrence_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L283) |
| function | `upsert_runtime_remembered_fact_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L307) |
| function | `list_runtime_remembered_fact_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L371) |
| function | `get_runtime_remembered_fact_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L416) |
| function | `update_runtime_remembered_fact_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L452) |
| function | `supersede_runtime_remembered_fact_signals_for_dimension` | `(*, dimension_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L484) |
| function | `_ensure_runtime_remembered_fact_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L514) |
| function | `_runtime_remembered_fact_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L555) |
| function | `upsert_runtime_memory_md_update_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L579) |
| function | `list_runtime_memory_md_update_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L643) |
| function | `get_runtime_memory_md_update_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L688) |
| function | `update_runtime_memory_md_update_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L724) |
| function | `supersede_runtime_memory_md_update_proposals_for_dimension` | `(*, dimension_key, exclude_proposal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L756) |
| function | `_ensure_runtime_memory_md_update_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L786) |
| function | `_runtime_memory_md_update_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L827) |
| function | `upsert_runtime_release_marker_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L851) |
| function | `list_runtime_release_marker_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L915) |
| function | `get_runtime_release_marker_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L960) |
| function | `update_runtime_release_marker_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L996) |
| function | `supersede_runtime_release_marker_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1028) |
| function | `_ensure_runtime_release_marker_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1058) |
| function | `_runtime_release_marker_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1099) |
| function | `upsert_runtime_selective_forgetting_candidate` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1123) |
| function | `list_runtime_selective_forgetting_candidates` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1187) |
| function | `get_runtime_selective_forgetting_candidate` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1232) |
| function | `update_runtime_selective_forgetting_candidate_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1270) |
| function | `supersede_runtime_selective_forgetting_candidates_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1302) |
| function | `_ensure_runtime_selective_forgetting_candidate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1332) |
| function | `_runtime_selective_forgetting_candidate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1375) |
| function | `upsert_runtime_regulation_homeostasis_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1401) |
| function | `list_runtime_regulation_homeostasis_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1465) |
| function | `get_runtime_regulation_homeostasis_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1510) |
| function | `update_runtime_regulation_homeostasis_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1548) |
| function | `supersede_runtime_regulation_homeostasis_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1580) |
| function | `_ensure_runtime_regulation_homeostasis_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1610) |
| function | `_runtime_regulation_homeostasis_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1653) |
| function | `upsert_runtime_temperament_tendency_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1679) |
| function | `list_runtime_temperament_tendency_signals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1743) |
| function | `get_runtime_temperament_tendency_signal` | `(signal_id)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1788) |
| function | `update_runtime_temperament_tendency_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1824) |
| function | `supersede_runtime_temperament_tendency_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1856) |
| function | `_ensure_runtime_temperament_tendency_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1886) |
| function | `_runtime_temperament_tendency_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1927) |

## `core/runtime/db_scheduled_tasks.py`
_Scheduled tasks — engangs-planlagte opgaver Jarvis skal udføre på et tidspunkt_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_scheduled_tasks_table` | `(conn)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L22) |
| function | `_row_get` | `(row, key, default=…)` | Safe column access — returns default if column missing from row. | [src](../../../core/runtime/db_scheduled_tasks.py#L47) |
| function | `_scheduled_task_from_row` | `(row)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L55) |
| function | `create_scheduled_task` | `(*, task_id, focus, source=…, run_at, created_at, updated_at)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L70) |
| function | `get_scheduled_task` | `(task_id)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L92) |
| function | `get_due_scheduled_tasks` | `(now_iso)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L101) |
| function | `mark_scheduled_task_fired` | `(task_id, fired_at, updated_at)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L115) |
| function | `mark_scheduled_task_cancelled` | `(task_id, cancelled_at, updated_at)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L129) |
| function | `update_scheduled_task` | `(task_id, *, focus=…, run_at=…, updated_at)` | Opdater focus og/eller run_at på en pending task. Returnerer den opdaterede | [src](../../../core/runtime/db_scheduled_tasks.py#L143) |
| function | `list_scheduled_tasks` | `(limit=…)` | — | [src](../../../core/runtime/db_scheduled_tasks.py#L169) |

## `core/runtime/db_schema.py`
_Schema layer for core.runtime.db — init_db + all _ensure_*/_migrate_* helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_multiuser_columns` | `(conn)` | Additive: tag scheduling tables with scheduled_for_user_id + | [src](../../../core/runtime/db_schema.py#L90) |
| function | `_ensure_user_scope_154` | `(conn)` | Additivt: tilføj user_id-kolonne + BACKFILL eksisterende NULL-rækker til | [src](../../../core/runtime/db_schema.py#L144) |
| function | `_ensure_skill_audit_table` | `(conn)` | Create skill_audit_log table for skills versionering (C1). | [src](../../../core/runtime/db_schema.py#L175) |
| function | `_ensure_skill_usage_table` | `(conn)` | Create skill_usage_stats table for auto-learning (C4). | [src](../../../core/runtime/db_schema.py#L198) |
| function | `_ensure_chat_session_workspace_columns` | `(conn)` | Tilføj nullable workspace-kolonner til chat_sessions (Code-mode binding). | [src](../../../core/runtime/db_schema.py#L228) |
| function | `_ensure_teams_tables` | `(conn)` | Teams-feature (spec 2026-06-20): teams + medlemskab + invites. Idempotent. | [src](../../../core/runtime/db_schema.py#L238) |
| function | `_ensure_chat_session_team_column` | `(conn)` | team_id på chat_sessions: NULL = privat (urørt), sat = team-session. Idempotent. | [src](../../../core/runtime/db_schema.py#L268) |
| function | `_ensure_notification_tables` | `(conn)` | Unified notification routing (spec 2026-06-20 §3.1): per-bruger-præferencer | [src](../../../core/runtime/db_schema.py#L275) |
| function | `_ensure_security_guard_tables` | `(conn)` | Identity-verification-guard & abuse-monitoring (spec 2026-06-21). Idempotent. | [src](../../../core/runtime/db_schema.py#L304) |
| function | `init_db` | `()` | — | [src](../../../core/runtime/db_schema.py#L351) |
| function | `_ensure_decision_trigger_column` | `(conn)` | Add behavioral_decisions.trigger_name column and wire known decisions. | [src](../../../core/runtime/db_schema.py#L932) |
| function | `_ensure_chat_messages_reasoning_column` | `(conn)` | Add chat_messages.reasoning_content column. Idempotent. | [src](../../../core/runtime/db_schema.py#L966) |
| function | `_ensure_causal_edges_table` | `(conn)` | Create causal_edges table for the causal graph layer. | [src](../../../core/runtime/db_schema.py#L992) |
| function | `_ensure_tool_router_tables` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1029) |
| function | `_ensure_counterfactuals_table` | `(conn)` | Create counterfactuals table with UNIQUE(cf_key) constraint. | [src](../../../core/runtime/db_schema.py#L1069) |
| function | `_ensure_absence_traces_table` | `(conn)` | Create absence_traces table for Lag 11 forgetting (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1107) |
| function | `_ensure_reasoning_conclusions_table` | `(conn)` | Create reasoning_conclusions table for Phase 1 Generalized Learning. | [src](../../../core/runtime/db_schema.py#L1145) |
| function | `_ensure_soft_deleted_at_columns` | `(conn)` | Add soft_deleted_at column to episodic tables (Lag 11 Phase 1). | [src](../../../core/runtime/db_schema.py#L1179) |
| function | `_ensure_dream_bias_active_table` | `(conn)` | Create dream_bias_active table for Lag 2 dream-bias (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1212) |
| function | `_ensure_user_temperature_active_table` | `(conn)` | Create user_temperature_active table for Lag 10 (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1252) |
| function | `_ensure_experience_episodes_table` | `(conn)` | Append-only log of (context, tool_choice, outcome) episodes. | [src](../../../core/runtime/db_schema.py#L1308) |
| function | `_ensure_tool_intent_approval_request_columns` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1364) |
| function | `_ensure_runtime_webchat_execution_pilot_table` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1422) |
| function | `_migrate_chronicle_table_add_affective_signature` | `()` | Add affective_signature column to existing tables missing it. | [src](../../../core/runtime/db_schema.py#L1464) |

## `core/runtime/db_self_repair.py`
_DB helpers for self_repair_patterns + self_repair_attempts tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_self_repair_tables` | `(conn)` | — | [src](../../../core/runtime/db_self_repair.py#L14) |
| function | `insert_self_repair_pattern` | `(*, pattern_id, name, trigger_event_kind, trigger_match_json=…, action_type, action_params_json=…, enabled=…, cooldown_seconds=…, max_attempts_per_window=…, window_seconds=…, auto_disable_after_escalations=…, auto_disable_window_hours=…, source=…, source_evidence_json=…)` | UPSERT a self-repair pattern. Idempotent on pattern_id. | [src](../../../core/runtime/db_self_repair.py#L104) |
| function | `get_self_repair_pattern` | `(pattern_id)` | — | [src](../../../core/runtime/db_self_repair.py#L173) |
| function | `list_self_repair_patterns` | `(*, enabled=…, trigger_event_kind=…)` | — | [src](../../../core/runtime/db_self_repair.py#L183) |
| function | `update_self_repair_pattern` | `(pattern_id, **fields)` | Update specific fields. Supports `<field>_increment` for atomic counters. | [src](../../../core/runtime/db_self_repair.py#L206) |
| function | `delete_self_repair_pattern` | `(pattern_id)` | — | [src](../../../core/runtime/db_self_repair.py#L247) |
| function | `insert_self_repair_attempt` | `(*, pattern_id, attempted_at, triggered_by_event_id, outcome, error_summary, elapsed_ms)` | — | [src](../../../core/runtime/db_self_repair.py#L257) |
| function | `count_recent_attempts` | `(*, pattern_id, since_iso, outcome=…)` | — | [src](../../../core/runtime/db_self_repair.py#L287) |
| function | `list_recent_self_repair_attempts` | `(*, pattern_id=…, limit=…)` | — | [src](../../../core/runtime/db_self_repair.py#L305) |
| function | `_pattern_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_self_repair.py#L336) |

## `core/runtime/db_sensory.py`
_Sensory memories — persistent archive of Jarvis's sensory experiences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_scope` | `()` | Bruger-id til streng per-bruger-scope (#154). "" = ingen scope (fallback). | [src](../../../core/runtime/db_sensory.py#L23) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_sensory.py#L29) |
| function | `_ensure_sensory_memories_table` | `(conn)` | — | [src](../../../core/runtime/db_sensory.py#L33) |
| function | `insert_sensory_memory` | `(*, modality, content, mood_tone=…, metadata=…, embedding=…, timestamp=…)` | — | [src](../../../core/runtime/db_sensory.py#L58) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_sensory.py#L93) |
| function | `list_sensory_memories` | `(*, modality=…, limit=…, offset=…, since=…)` | — | [src](../../../core/runtime/db_sensory.py#L108) |
| function | `search_sensory_memories` | `(*, query, modality=…, limit=…)` | Simple LIKE-based substring search over content and mood_tone. | [src](../../../core/runtime/db_sensory.py#L139) |
| function | `count_sensory_memories` | `(*, modality=…)` | — | [src](../../../core/runtime/db_sensory.py#L172) |
| function | `get_sensory_memory` | `(memory_id)` | — | [src](../../../core/runtime/db_sensory.py#L189) |

## `core/runtime/db_user_contradiction.py`
_DB helpers for user_contradictions + user_statements tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_user_contradiction_tables` | `(conn)` | — | [src](../../../core/runtime/db_user_contradiction.py#L19) |
| function | `upsert_user_statement` | `(*, statement_id, user_id, text, topic, session_id, source, created_at, updated_at)` | Gem eller opdater et user statement. | [src](../../../core/runtime/db_user_contradiction.py#L72) |
| function | `get_user_statement_by_text` | `(*, text, user_id=…, topic=…)` | Find et eksisterende statement med samme tekst (case-insensitive). | [src](../../../core/runtime/db_user_contradiction.py#L148) |
| function | `list_user_statements` | `(*, user_id=…, topic=…, limit=…)` | Hent statements for en bruger, filtreret på topic hvis angivet. | [src](../../../core/runtime/db_user_contradiction.py#L175) |
| function | `insert_user_contradiction` | `(*, contradiction_id, user_id, statement_a_id, statement_a_text, statement_a_source, statement_a_created_at, statement_b_text, statement_b_source, statement_b_created_at, topic, overlap_tokens, created_at, updated_at)` | Gem en fundet bruger-modsigelse. | [src](../../../core/runtime/db_user_contradiction.py#L211) |
| function | `list_user_contradictions` | `(*, user_id=…, topic=…, limit=…, status=…)` | Hent lagrede modsigelser for en bruger. | [src](../../../core/runtime/db_user_contradiction.py#L262) |
| function | `update_user_contradiction_status` | `(*, contradiction_id, status, notes=…, updated_at=…)` | Opdater status på en modsigelse (fx 'resolved' eller 'dismissed'). | [src](../../../core/runtime/db_user_contradiction.py#L309) |

## `core/runtime/db_user_temperature.py`
_DB helpers for user_temperature_active (Lag 10 user temperature field)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/db_user_temperature.py#L16) |
| function | `upsert_active_field` | `(*, workspace_id, struct, struct_signals, llm, combined, baseline)` | INSERT or UPDATE the single active field row for a workspace. | [src](../../../core/runtime/db_user_temperature.py#L20) |
| function | `get_active_field_raw` | `(*, workspace_id)` | Read the active field row, parsed JSON columns expanded. | [src](../../../core/runtime/db_user_temperature.py#L106) |
| function | `set_llm_trigger_pending` | `(*, workspace_id)` | Mark LLM stream as needing a refresh on next daemon cycle. | [src](../../../core/runtime/db_user_temperature.py#L156) |
| function | `consume_llm_trigger_pending` | `(*, workspace_id)` | Read+clear the trigger flag atomically. Returns True if was pending. | [src](../../../core/runtime/db_user_temperature.py#L169) |

## `core/runtime/db_users.py`
_DB helpers for users-tabellen (spec 2026-06-15)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_users_table` | `(conn)` | Idempotent: brugerstyring. Følsomme felter lagres krypteret | [src](../../../core/runtime/db_users.py#L16) |
| function | `get_user_row_by_google_email_hash` | `(h)` | — | [src](../../../core/runtime/db_users.py#L59) |
| function | `_ensure_google_links_table` | `(conn)` | — | [src](../../../core/runtime/db_users.py#L77) |
| function | `set_google_link` | `(email_hash, user_id, role, updated_at)` | — | [src](../../../core/runtime/db_users.py#L91) |
| function | `get_google_link` | `(email_hash)` | — | [src](../../../core/runtime/db_users.py#L106) |
| function | `has_google_link_for_user` | `(user_id)` | Har brugeren (user_id) en Google-konto linket? (vedvarende indikator). | [src](../../../core/runtime/db_users.py#L118) |
| function | `insert_user_row` | `(*, user_id, email_hash, email_enc, name, role, workspace, password_hash, discord_id_enc, totp_seed_enc, created_at, updated_at)` | — | [src](../../../core/runtime/db_users.py#L130) |
| function | `get_user_row` | `(user_id)` | — | [src](../../../core/runtime/db_users.py#L151) |
| function | `get_user_row_by_email_hash` | `(email_hash)` | — | [src](../../../core/runtime/db_users.py#L158) |
| function | `get_user_row_by_workspace` | `(workspace)` | Opslag pr. workspace-mappenavn (omvendt lookup). Bruges af cutover-resolveren | [src](../../../core/runtime/db_users.py#L165) |
| function | `update_user_row` | `(user_id, fields)` | — | [src](../../../core/runtime/db_users.py#L191) |
| function | `soft_delete_user_row` | `(user_id, *, deleted_at)` | — | [src](../../../core/runtime/db_users.py#L204) |
| function | `hard_delete_user_row` | `(user_id)` | — | [src](../../../core/runtime/db_users.py#L208) |
| function | `list_user_rows` | `(*, include_deleted=…)` | — | [src](../../../core/runtime/db_users.py#L216) |

## `core/runtime/db_visible.py`
_Persistence for the visible-lane projection tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_visible_tables` | `(conn)` | — | [src](../../../core/runtime/db_visible.py#L15) |
| function | `recent_visible_runs` | `(limit=…)` | — | [src](../../../core/runtime/db_visible.py#L73) |
| function | `recent_visible_work_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_visible.py#L111) |
| function | `recent_visible_work_units` | `(limit=…)` | — | [src](../../../core/runtime/db_visible.py#L155) |
| function | `record_visible_work_note` | `(*, note_id, work_id, run_id, status, lane, provider, model, user_message_preview=…, capability_id=…, work_preview=…, projection_source=…, created_at, finished_at)` | — | [src](../../../core/runtime/db_visible.py#L195) |
| function | `visible_session_continuity` | `()` | — | [src](../../../core/runtime/db_visible.py#L303) |

## `core/runtime/heartbeat_triggers.py`
_Heartbeat trigger queue._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_triggers_path` | `(workspace_dir)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L20) |
| function | `_read` | `(workspace_dir)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L24) |
| function | `_write` | `(workspace_dir, triggers)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L35) |
| function | `set_trigger` | `(workspace_dir, *, reason, source, text=…)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L44) |
| function | `peek_trigger` | `(workspace_dir)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L63) |
| function | `consume_trigger` | `(workspace_dir)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L68) |
| function | `clear_triggers` | `(workspace_dir)` | — | [src](../../../core/runtime/heartbeat_triggers.py#L77) |
| function | `set_trigger_for_default_workspace` | `(*, reason, source, text=…)` | Resolve the default workspace and queue a trigger. | [src](../../../core/runtime/heartbeat_triggers.py#L83) |

## `core/runtime/jarvisx_auth.py`
_JarvisX bearer-token authentication._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AuthError` | `` | Raised when a token is missing, malformed, expired, or forged. | [src](../../../core/runtime/jarvisx_auth.py#L60) |
| function | `_load_settings` | `()` | — | [src](../../../core/runtime/jarvisx_auth.py#L64) |
| function | `_save_settings` | `(data)` | — | [src](../../../core/runtime/jarvisx_auth.py#L73) |
| function | `_read_secret` | `()` | Read the auth secret, generating one on first use. | [src](../../../core/runtime/jarvisx_auth.py#L80) |
| function | `issue_token` | `(*, user_id, role=…, ttl_days=…, ttl_seconds=…, app_id=…, extra_claims=…)` | Mint a signed bearer token for a user. | [src](../../../core/runtime/jarvisx_auth.py#L117) |
| function | `verify_token` | `(token)` | Verify signature + expiry, return the parsed claims. | [src](../../../core/runtime/jarvisx_auth.py#L175) |
| function | `session_needs_override` | `(claims, *, owner_app_id, session_id, now=…)` | True hvis owner-autoritet i denne session KRÆVER en TOTP-override (§6.1). | [src](../../../core/runtime/jarvisx_auth.py#L226) |
| function | `auth_required` | `()` | Should the API reject requests without a valid bearer token? | [src](../../../core/runtime/jarvisx_auth.py#L256) |
| function | `require_owner` | `(request)` | Raise 401/403 unless the caller carries an owner bearer token. | [src](../../../core/runtime/jarvisx_auth.py#L287) |

## `core/runtime/ollamafreeapi_provider.py`
_OllamaFreeAPI adapter for PUBLIC-SAFE cheap-lane calls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_client` | `()` | — | [src](../../../core/runtime/ollamafreeapi_provider.py#L19) |
| function | `collapse_messages_to_prompt` | `(messages)` | — | [src](../../../core/runtime/ollamafreeapi_provider.py#L26) |
| function | `list_ollamafreeapi_models` | `()` | — | [src](../../../core/runtime/ollamafreeapi_provider.py#L39) |
| function | `call_ollamafreeapi` | `(*, model, messages=…, prompt=…, timeout=…)` | Call OllamaFreeAPI and return an Ollama-compatible response shape. | [src](../../../core/runtime/ollamafreeapi_provider.py#L43) |

## `core/runtime/operational_preference_alignment.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_operational_preference_alignment` | `(*, private_operational_preference, lane_targets)` | — | [src](../../../core/runtime/operational_preference_alignment.py#L4) |
| function | `_alignment_status` | `(*, preferred_lane, preferred_target)` | — | [src](../../../core/runtime/operational_preference_alignment.py#L49) |
| function | `_mismatch_reason` | `(*, preferred_lane, preferred_target)` | — | [src](../../../core/runtime/operational_preference_alignment.py#L61) |
| function | `_recommended_action` | `(*, preferred_lane, preferred_target)` | — | [src](../../../core/runtime/operational_preference_alignment.py#L73) |

## `core/runtime/provider_router.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_provider_router_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L18) |
| function | `configure_provider_router_entry` | `(*, provider, model, auth_mode, auth_profile, base_url, api_key, lane, set_visible)` | — | [src](../../../core/runtime/provider_router.py#L30) |
| function | `provider_router_summary` | `()` | — | [src](../../../core/runtime/provider_router.py#L125) |
| function | `main_agent_target` | `()` | — | [src](../../../core/runtime/provider_router.py#L162) |
| function | `main_agent_selection` | `()` | — | [src](../../../core/runtime/provider_router.py#L183) |
| function | `select_main_agent_target` | `(*, provider, model, auth_profile=…)` | — | [src](../../../core/runtime/provider_router.py#L200) |
| function | `resolve_provider_router_target` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L254) |
| function | `provider_router_lane_targets` | `()` | — | [src](../../../core/runtime/provider_router.py#L320) |
| function | `list_provider_router_targets` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L325) |
| function | `_provider_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L360) |
| function | `_model_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L378) |
| function | `_latest_model_for_lane` | `(*, registry, lane)` | — | [src](../../../core/runtime/provider_router.py#L388) |
| function | `_configured_main_agent_targets` | `(*, registry)` | — | [src](../../../core/runtime/provider_router.py#L405) |
| function | `_configured_target_match` | `(*, registry, provider, model)` | — | [src](../../../core/runtime/provider_router.py#L447) |
| function | `_readiness_hint` | `(*, provider, auth_mode, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L459) |
| function | `_provider_entry` | `(*, registry, provider)` | — | [src](../../../core/runtime/provider_router.py#L472) |
| function | `_provider_auth_mode` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L483) |
| function | `_provider_base_url` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L490) |
| function | `_credentials_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L497) |
| function | `_upsert_provider` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L514) |
| function | `_upsert_model` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L523) |
| function | `_default_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L536) |
| function | `_normalize_simple_id` | `(value, *, label)` | — | [src](../../../core/runtime/provider_router.py#L543) |
| function | `_normalize_auth_mode` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L550) |
| function | `_ollama_model_exists` | `(*, registry, model)` | Return True if *model* is available in the live Ollama instance. | [src](../../../core/runtime/provider_router.py#L557) |
| function | `_normalize_profile` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L572) |
| function | `_normalize_lane` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L579) |
| function | `_now` | `()` | — | [src](../../../core/runtime/provider_router.py#L586) |

## `core/runtime/refresh_tokens.py`
_Refresh-token-rotation (spec §22.6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hash` | `(token)` | — | [src](../../../core/runtime/refresh_tokens.py#L26) |
| function | `_now` | `()` | — | [src](../../../core/runtime/refresh_tokens.py#L30) |
| function | `_kv` | `()` | — | [src](../../../core/runtime/refresh_tokens.py#L34) |
| function | `_index_add` | `(user_id, h)` | — | [src](../../../core/runtime/refresh_tokens.py#L39) |
| function | `issue_refresh_token` | `(user_id)` | Udsted en ny refresh-token til brugeren. Returnerer den RÅ token (vises kun | [src](../../../core/runtime/refresh_tokens.py#L51) |
| function | `verify_refresh_token` | `(token)` | Returnér user_id hvis refresh-token er gyldig (aktiv + ikke udløbet), ellers None. | [src](../../../core/runtime/refresh_tokens.py#L67) |
| function | `_deactivate` | `(h)` | — | [src](../../../core/runtime/refresh_tokens.py#L81) |
| function | `rotate_refresh_token` | `(token, *, app_id=…)` | Veksl en refresh-token til et nyt access+refresh-par. Den gamle refresh-token | [src](../../../core/runtime/refresh_tokens.py#L92) |
| function | `revoke_all` | `(user_id)` | Invalidér ALLE brugerens refresh-tokens (§22.6 + !revoke-override). Returnerer | [src](../../../core/runtime/refresh_tokens.py#L115) |

## `core/runtime/runtime_json_io.py`
_Safe read/merge/write helpers for runtime.json._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_runtime_raw` | `()` | Return current runtime.json as a plain dict. Empty dict if file missing. | [src](../../../core/runtime/runtime_json_io.py#L30) |
| function | `_prune_old_backups` | `()` | — | [src](../../../core/runtime/runtime_json_io.py#L40) |
| function | `_write_backup` | `(payload)` | — | [src](../../../core/runtime/runtime_json_io.py#L56) |
| function | `write_runtime_merged` | `(updates)` | Merge `updates` into runtime.json, writing atomically. | [src](../../../core/runtime/runtime_json_io.py#L68) |

## `core/runtime/secrets.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MailConfig` | `` | — | [src](../../../core/runtime/secrets.py#L11) |
| function | `_backup_file` | `()` | — | [src](../../../core/runtime/secrets.py#L20) |
| function | `_missing_key_message` | `(key)` | — | [src](../../../core/runtime/secrets.py#L24) |
| function | `ensure_runtime_file_perms` | `()` | Garantér at runtime.json kun er læsbar af ejeren (0600). | [src](../../../core/runtime/secrets.py#L34) |
| function | `_parse_int` | `(value, key)` | — | [src](../../../core/runtime/secrets.py#L52) |
| function | `read_runtime_key` | `(key, env_override=…, *, as_int=…)` | Read a top-level key from ~/.jarvis-v2/config/runtime.json. | [src](../../../core/runtime/secrets.py#L61) |
| function | `mail_config` | `()` | — | [src](../../../core/runtime/secrets.py#L96) |

## `core/runtime/settings.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeSettings` | `` | — | [src](../../../core/runtime/settings.py#L11) |
| method | `RuntimeSettings.to_dict` | `(self)` | — | [src](../../../core/runtime/settings.py#L438) |
| function | `load_settings` | `()` | — | [src](../../../core/runtime/settings.py#L529) |
| function | `update_visible_execution_settings` | `(*, visible_model_provider=…, visible_model_name=…, visible_auth_profile=…)` | — | [src](../../../core/runtime/settings.py#L944) |

## `core/runtime/state_store.py`
_Tiny JSON-file state store for module-globals that must survive restart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_path` | `(name)` | — | [src](../../../core/runtime/state_store.py#L26) |
| function | `load_json` | `(name, default)` | Read ``state/<name>.json``; return ``default`` if missing/corrupt. | [src](../../../core/runtime/state_store.py#L30) |
| function | `save_json` | `(name, data)` | Atomically persist ``data`` to ``state/<name>.json``. | [src](../../../core/runtime/state_store.py#L47) |

## `core/runtime/workspace_paths.py`
_Workspace path resolver — single source of truth for filesystem layout._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NoUserContextError` | `` | Raised when workspace_dir() is called without a resolvable user_id. | [src](../../../core/runtime/workspace_paths.py#L17) |
| function | `_jarvis_home` | `()` | JARVIS_HOME resolved at call time (so tests can override via env). | [src](../../../core/runtime/workspace_paths.py#L26) |
| function | `shared_dir` | `()` | Jarvis' own state. All users see the same instance. | [src](../../../core/runtime/workspace_paths.py#L31) |
| function | `workspace_dir` | `(user_id=…)` | Per-relation workspace. Defaults to current_user_id() from context. | [src](../../../core/runtime/workspace_paths.py#L40) |
| function | `team_dir` | `(team_id)` | Delt team-workspace som git-repo (Teams-feature, spec 2026-06-20). | [src](../../../core/runtime/workspace_paths.py#L66) |
| function | `_user_id_to_workspace_name` | `(user_id)` | Resolve user_id → workspace folder name. | [src](../../../core/runtime/workspace_paths.py#L90) |

