# `core.runtime.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/db_composites.py`
_Composite tools store — Jarvis proposals of new tool sequences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_composites.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_composites.py#L48) |
| function | `propose_composite` | `(*, name, description, input_schema, steps, created_by=…)` | Insert a new proposal. Name must be unique. | [src](../../../core/runtime/db_composites.py#L52) |
| function | `approve_composite` | `(name, *, approved_by=…)` | — | [src](../../../core/runtime/db_composites.py#L86) |
| function | `revoke_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L103) |
| function | `get_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L116) |
| function | `list_composites` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_composites.py#L127) |
| function | `record_invocation` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L146) |
| function | `delete_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L158) |
| function | `count_composites` | `(*, status=…)` | — | [src](../../../core/runtime/db_composites.py#L168) |
| function | `_decode` | `(row)` | — | [src](../../../core/runtime/db_composites.py#L183) |

## `core/runtime/db_concept_baseline.py`
_DB helpers for concept_baseline_stats table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_concept_baseline_table` | `(conn)` | — | [src](../../../core/runtime/db_concept_baseline.py#L11) |
| function | `upsert_concept_baseline_stat` | `(*, concept, cluster, total_triggers=…, triggers_7d=…, triggers_30d=…, mean_intensity_7d=…, last_triggered_at=…, first_triggered_at=…)` | — | [src](../../../core/runtime/db_concept_baseline.py#L29) |
| function | `increment_concept_baseline_total` | `(*, concept, intensity, triggered_at)` | Increment total_triggers and update last_triggered_at for an existing concept. | [src](../../../core/runtime/db_concept_baseline.py#L74) |
| function | `get_concept_baseline_stat` | `(concept)` | — | [src](../../../core/runtime/db_concept_baseline.py#L99) |
| function | `list_concept_baseline_stats` | `()` | — | [src](../../../core/runtime/db_concept_baseline.py#L110) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_concept_baseline.py#L120) |

## `core/runtime/db_core.py`
_Core infrastructure for core.runtime.db modulet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ClosingConnection` | `` | — | [src](../../../core/runtime/db_core.py#L71) |
| method | `ClosingConnection.__exit__` | `(self, exc_type, exc_value, traceback)` | — | [src](../../../core/runtime/db_core.py#L72) |
| class | `PooledConnection` | `` | Som ClosingConnection men LUKKER IKKE ved __exit__/close() — poolen ejer | [src](../../../core/runtime/db_core.py#L79) |
| method | `PooledConnection.__exit__` | `(self, exc_type, exc_value, traceback)` | — | [src](../../../core/runtime/db_core.py#L82) |
| method | `PooledConnection.close` | `(self)` | — | [src](../../../core/runtime/db_core.py#L86) |
| function | `_make_connection` | `(_factory)` | Åbn ÉN ny sqlite-forbindelse + sæt PRAGMAs (busy_timeout, WAL-once, synchronous). | [src](../../../core/runtime/db_core.py#L97) |
| function | `close_pooled_connection` | `()` | Luk DENNE tråds pooled forbindelse rigtigt (shutdown/tests). Self-safe. | [src](../../../core/runtime/db_core.py#L122) |
| function | `connect` | `()` | DEL 1 — connection pooling (2026-07-12): genbrug ÉN thread-local forbindelse i | [src](../../../core/runtime/db_core.py#L133) |
| function | `_rank_for` | `(ranks, value)` | — | [src](../../../core/runtime/db_core.py#L174) |
| function | `_stronger_ranked_value` | `(current, proposed, ranks)` | — | [src](../../../core/runtime/db_core.py#L178) |
| function | `_merge_text_fragments` | `(current, proposed, *, limit=…)` | — | [src](../../../core/runtime/db_core.py#L184) |
| function | `_upsert_signal` | `(*, conn, table, id_col, type_col, id_val, type_val, canonical_key, lookup_statuses, overwrite_cols, rank_cols, merge_text_cols, accumulate_cols, created_at, updated_at)` | Generic merge-forward upsert for the runtime_*_signal families. | [src](../../../core/runtime/db_core.py#L199) |
| function | `_rs_cache_put` | `(key, value)` | — | [src](../../../core/runtime/db_core.py#L370) |
| function | `clear_runtime_state_cache` | `()` | Ryd hele read-cachen (til tests / tvungen frisk læsning). Self-safe. | [src](../../../core/runtime/db_core.py#L375) |
| function | `set_runtime_state_value` | `(key, value, *, updated_at=…)` | — | [src](../../../core/runtime/db_core.py#L381) |
| function | `get_runtime_state_value` | `(key, default=…)` | — | [src](../../../core/runtime/db_core.py#L401) |
| function | `get_runtime_state_bool` | `(key, default=…)` | Read a runtime-state flag and coerce it to bool ROBUSTLY. | [src](../../../core/runtime/db_core.py#L434) |
| function | `skriv_med_genforsoeg` | `(skriv, *, forsoeg=…, pause=…)` | Kør `skriv()`; ved «database is locked/busy» prøv igen med voksende pause. | [src](../../../core/runtime/db_core.py#L466) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_core.py#L485) |
| function | `_conn_db_id` | `(conn)` | Stable identifier for a sqlite connection's underlying database. | [src](../../../core/runtime/db_core.py#L534) |
| function | `_install_ensure_once_cache` | `()` | Bagudkompat-shim: wrapper _ensure_*_table funcs på core.runtime.db | [src](../../../core/runtime/db_core.py#L558) |
| function | `invalidate_ensure_once_cache` | `(table_name=…)` | Force re-run of `_ensure_*_table` on next call. | [src](../../../core/runtime/db_core.py#L568) |
| function | `_install_ensure_once_cache_for` | `(module_name)` | Wrap _ensure_*_table funcs i target-modul med once-cache. | [src](../../../core/runtime/db_core.py#L586) |

## `core/runtime/db_credit_assignment.py`
_Credit assignment — schema migration, choice recording, and outcome querying._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_credit_assignment.py#L24) |
| function | `ensure_credit_assignment_tables` | `(conn=…)` | Add credit-assignment columns to existing tables + pending index. | [src](../../../core/runtime/db_credit_assignment.py#L30) |
| function | `_migrate_table` | `(conn, table, columns)` | Add columns to *table* if they don't already exist. | [src](../../../core/runtime/db_credit_assignment.py#L74) |
| function | `record_choice` | `(*, kind=…, title, options, decision, why=…, context=…)` | Record a choice in cognitive_decisions with a kind tag. | [src](../../../core/runtime/db_credit_assignment.py#L105) |
| function | `list_unreviewed_decisions` | `(*, kind=…, limit=…)` | Find decisions of a given *kind* that have no linked outcome yet. | [src](../../../core/runtime/db_credit_assignment.py#L160) |
| function | `link_outcome_to_decision` | `(*, decision_id, credit_score, rationale, evidence_summary=…, run_id=…)` | Link a self-review outcome to a decision and update outcome_aggregate. | [src](../../../core/runtime/db_credit_assignment.py#L188) |
| function | `score_provider_outcome` | `(decision_id, result)` | Score a provider_routing decision based on actual call result. | [src](../../../core/runtime/db_credit_assignment.py#L303) |
| function | `score_tier_outcome` | `(decision_id, tier_used, next_turns)` | Score a model_tier decision after observing subsequent turns. | [src](../../../core/runtime/db_credit_assignment.py#L363) |
| function | `score_response_outcome` | `(decision_id, style_used, user_reply)` | Score a response_style decision based on user engagement. | [src](../../../core/runtime/db_credit_assignment.py#L436) |
| function | `_get_median_provider_cost` | `()` | Approximate median cost-per-token across recent cheap-lane calls. | [src](../../../core/runtime/db_credit_assignment.py#L514) |
| function | `get_credit_trend` | `(*, kind=…, limit=…)` | Show decisions with their outcomes for oversight. | [src](../../../core/runtime/db_credit_assignment.py#L539) |

## `core/runtime/db_decisions.py`
_Behavioral decisions store — commitments Jarvis makes to himself._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_decisions.py#L28) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_decisions.py#L72) |
| function | `_new_id` | `(prefix)` | — | [src](../../../core/runtime/db_decisions.py#L76) |
| function | `create_decision` | `(*, directive, rationale=…, trigger_cue=…, priority=…, source_record_id=…, source_type=…, created_by=…)` | — | [src](../../../core/runtime/db_decisions.py#L80) |
| function | `append_review` | `(*, decision_id, verdict, note=…, evidence=…)` | Record a self-assessment: how am I doing on this? | [src](../../../core/runtime/db_decisions.py#L119) |
| function | `_verified_adherence` | `(conn, decision_id)` | — | [src](../../../core/runtime/db_decisions.py#L176) |
| function | `repair_legacy_auto_adherence` | `()` | Rebuild stored scores after legacy automatic suspicions polluted them. | [src](../../../core/runtime/db_decisions.py#L211) |
| function | `update_decision` | `(decision_id, *, directive=…, rationale=…, trigger_cue=…, trigger_name=…, priority=…, status=…)` | Update mutable fields on a decision. | [src](../../../core/runtime/db_decisions.py#L232) |
| function | `set_status` | `(decision_id, new_status)` | — | [src](../../../core/runtime/db_decisions.py#L294) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/runtime/db_decisions.py#L311) |
| function | `list_decisions` | `(*, status=…, limit=…)` | List decisions, newest priority first. | [src](../../../core/runtime/db_decisions.py#L323) |
| function | `list_reviews` | `(decision_id, *, limit=…)` | — | [src](../../../core/runtime/db_decisions.py#L354) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/runtime/db_decisions.py#L365) |
| function | `count_decisions` | `(*, status=…)` | — | [src](../../../core/runtime/db_decisions.py#L380) |

## `core/runtime/db_devices.py`
_Enheder — hvem må styre denne computer, og hvem må bruge code mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sikr` | `(conn)` | — | [src](../../../core/runtime/db_devices.py#L47) |
| function | `_raekke` | `(r)` | — | [src](../../../core/runtime/db_devices.py#L59) |
| function | `registrer_telefon` | `(user_id, *, navn=…, platform=…)` | En ny telefon. Id'et bliver tokenets `enhed`-claim. | [src](../../../core/runtime/db_devices.py#L64) |
| function | `registrer_computer` | `(user_id, app_id, *, navn=…)` | En desk-installation. Idempotent pr. bruger og app_id (genaktiverer en fjernet). | [src](../../../core/runtime/db_devices.py#L81) |
| function | `liste` | `(user_id)` | Brugerens aktive enheder, nyeste først. | [src](../../../core/runtime/db_devices.py#L107) |
| function | `fjern` | `(enheds_id, user_id)` | Fjern én enhed — kun brugerens egen. En telefons tokens dør med det samme. | [src](../../../core/runtime/db_devices.py#L119) |
| function | `telefon_status` | `(enheds_id)` | 'aktiv' / 'fjernet' for en telefon-post, None hvis ukendt. | [src](../../../core/runtime/db_devices.py#L130) |
| function | `maa_bruge_kode` | `(user_id, *, enhed=…, app_id=…)` | Matcher tokenet en AKTIV post for brugeren? | [src](../../../core/runtime/db_devices.py#L143) |
| function | `kraev_aktivt` | `()` | — | [src](../../../core/runtime/db_devices.py#L169) |
| function | `saet_kraev` | `(aktiv, *, af=…)` | — | [src](../../../core/runtime/db_devices.py#L178) |

## `core/runtime/db_dream_bias.py`
_DB helpers for dream_bias_active (Lag 2 dream-bias)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/db_dream_bias.py#L17) |
| function | `_future_iso` | `(*, hours)` | — | [src](../../../core/runtime/db_dream_bias.py#L21) |
| function | `insert_new_bias` | `(*, workspace_id, attention_bias, threshold_bias, intensity, ttl_hours, dream_text, source_event_ids, source_kinds)` | INSERT a fresh bias row for a workspace. | [src](../../../core/runtime/db_dream_bias.py#L25) |
| function | `update_existing_bias` | `(*, workspace_id, attention_bias, threshold_bias, intensity, ttl_hours, dream_text, accumulated_count, source_event_ids, source_kinds)` | Update existing row in place. Returns True if a row was updated. | [src](../../../core/runtime/db_dream_bias.py#L76) |
| function | `get_active_bias_raw` | `(*, workspace_id)` | Read the single active bias row for a workspace. | [src](../../../core/runtime/db_dream_bias.py#L112) |
| function | `delete_expired_bias_rows` | `()` | Hard-delete rows whose TTL has passed. Returns count. | [src](../../../core/runtime/db_dream_bias.py#L149) |

## `core/runtime/db_embeddings.py`
_Embeddings store — unified vector index across all memory surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_memory_embeddings_table` | `(conn)` | — | [src](../../../core/runtime/db_embeddings.py#L18) |
| function | `upsert_embedding` | `(*, source_table, source_id, modality, content_hash, embedding_bytes, model_version)` | Insert or overwrite the embedding for a given source row. | [src](../../../core/runtime/db_embeddings.py#L39) |
| function | `get_embedding` | `(source_table, source_id)` | — | [src](../../../core/runtime/db_embeddings.py#L78) |
| function | `delete_embedding` | `(source_table, source_id)` | — | [src](../../../core/runtime/db_embeddings.py#L93) |
| function | `list_embeddings` | `(*, modalities=…, source_tables=…, limit=…)` | Return raw embedding rows (including blobs). Caller decodes. | [src](../../../core/runtime/db_embeddings.py#L104) |
| function | `count_embeddings` | `(*, modality=…, source_table=…)` | — | [src](../../../core/runtime/db_embeddings.py#L133) |
| function | `list_indexed_source_ids` | `(source_table)` | Return the set of source_ids already indexed for a given table. | [src](../../../core/runtime/db_embeddings.py#L156) |

## `core/runtime/db_emotional_memory.py`
_DB helpers for emotional_memory_anchors table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_emotional_memory_anchors_table` | `(conn)` | — | [src](../../../core/runtime/db_emotional_memory.py#L15) |
| function | `insert_emotional_memory_anchor` | `(*, anchor_type, anchor_id, captured_at, mood, intensity, confidence=…, curiosity=…, frustration=…, fatigue=…, trust=…, outcome_score=…, outcome_source=…, context_features_json=…, source=…, notes=…)` | UPSERT an emotional memory anchor. Idempotent on (anchor_type, anchor_id). | [src](../../../core/runtime/db_emotional_memory.py#L54) |
| function | `get_emotional_memory_anchor` | `(anchor_type, anchor_id)` | — | [src](../../../core/runtime/db_emotional_memory.py#L141) |
| function | `list_emotional_memory_anchors` | `(*, anchor_type=…, since=…, min_intensity=…, outcome=…, limit=…)` | Return anchors filtered and ordered by captured_at DESC. | [src](../../../core/runtime/db_emotional_memory.py#L153) |
| function | `update_emotional_memory_outcome` | `(*, anchor_type, anchor_id, score, source, force=…)` | Update outcome score. Returns True if updated, False if blocked. | [src](../../../core/runtime/db_emotional_memory.py#L190) |
| function | `delete_emotional_memory_anchor` | `(anchor_type, anchor_id)` | — | [src](../../../core/runtime/db_emotional_memory.py#L234) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_emotional_memory.py#L244) |
| function | `aggregate_emotional_memory_anchors` | `()` | Tællinger over HELE tabellen — ikke over de seneste N rækker. | [src](../../../core/runtime/db_emotional_memory.py#L265) |

## `core/runtime/db_fts.py`
_FTS5 full-text search over session summaries and chat messages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `fts5_available` | `(conn)` | — | [src](../../../core/runtime/db_fts.py#L34) |
| function | `_base_table_exists` | `(conn, table)` | — | [src](../../../core/runtime/db_fts.py#L43) |
| function | `ensure_fts_tables` | `(conn)` | Create the FTS tables + sync triggers for every base table that exists. | [src](../../../core/runtime/db_fts.py#L50) |
| function | `rebuild_fts` | `()` | Rebuild every FTS table from its base table. Returns row counts. | [src](../../../core/runtime/db_fts.py#L96) |
| function | `to_match_query` | `(query, *, max_terms=…)` | Turn free text into a tolerant FTS5 MATCH expression. | [src](../../../core/runtime/db_fts.py#L109) |
| function | `_bm25_to_score` | `(rank)` | FTS5 bm25() returns lower-is-better negative numbers; map to (0, 1]. | [src](../../../core/runtime/db_fts.py#L128) |
| function | `search_session_summaries` | `(query, *, limit=…)` | Keyword search over session_summaries FOR THIS USER. | [src](../../../core/runtime/db_fts.py#L136) |
| function | `search_chat_messages` | `(query, *, limit=…, session_id=…, role=…)` | Keyword search over chat_messages FOR THIS USER. Each hit: id, message_id, | [src](../../../core/runtime/db_fts.py#L196) |

## `core/runtime/db_gate_verdicts.py`
_Gate-verdict-ledger — PERSISTENT optælling af hvert governet gate-udfald._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/runtime/db_gate_verdicts.py#L28) |
| function | `apply_deltas` | `(deltas)` | UPSERT en batch af akkumulerede tæller-deltas. Returnerer antal rækker rørt. | [src](../../../core/runtime/db_gate_verdicts.py#L48) |
| function | `read_counts` | `(nerve=…)` | Læs aggregerede tællere. Filtrér på nerve hvis givet. Selv-sikker → [] ved fejl. | [src](../../../core/runtime/db_gate_verdicts.py#L91) |
| function | `summary` | `()` | Aggregér pr. nerve: {nerve: {cluster, total, green, yellow, red, skip, | [src](../../../core/runtime/db_gate_verdicts.py#L112) |

## `core/runtime/db_goals.py`
_Long-horizon goals store — persistent objectives Jarvis carries across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_goals.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_goals.py#L67) |
| function | `_new_id` | `(prefix)` | — | [src](../../../core/runtime/db_goals.py#L71) |
| function | `create_goal` | `(*, title, description=…, priority=…, target_date=…, tags=…, created_by=…)` | — | [src](../../../core/runtime/db_goals.py#L75) |
| function | `append_goal_update` | `(*, goal_id, note, progress_delta=…, source=…, new_status=…)` | Append a progress note and optionally bump progress/status. | [src](../../../core/runtime/db_goals.py#L112) |
| function | `get_goal` | `(goal_id)` | — | [src](../../../core/runtime/db_goals.py#L180) |
| function | `list_goals` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_goals.py#L192) |
| function | `list_goal_updates` | `(goal_id, *, limit=…)` | — | [src](../../../core/runtime/db_goals.py#L213) |
| function | `update_goal_fields` | `(goal_id, *, title=…, description=…, priority=…, target_date=…, tags=…)` | — | [src](../../../core/runtime/db_goals.py#L224) |
| function | `delete_goal` | `(goal_id)` | — | [src](../../../core/runtime/db_goals.py#L268) |
| function | `count_goals` | `(*, status=…)` | — | [src](../../../core/runtime/db_goals.py#L281) |
| function | `_row_to_goal` | `(row)` | — | [src](../../../core/runtime/db_goals.py#L296) |

## `core/runtime/db_governance.py`
_Persistence for governance-adjacent CRUD domains._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `recent_tool_intent_approval_requests` | `(limit=…, *, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_governance.py#L32) |
| function | `create_tool_intent_approval_request` | `(*, intent_key, intent_type, intent_target, approval_scope, approval_required, approval_reason, requested_at, expires_at, execution_state=…)` | — | [src](../../../core/runtime/db_governance.py#L80) |
| function | `get_tool_intent_approval_request` | `(intent_key)` | — | [src](../../../core/runtime/db_governance.py#L148) |
| function | `resolve_tool_intent_approval_request` | `(intent_key, *, approval_state, approval_source, resolved_at, resolution_reason, resolution_message=…, session_id=…)` | — | [src](../../../core/runtime/db_governance.py#L183) |
| function | `expire_tool_intent_approval_request` | `(intent_key, *, expired_at, resolution_reason)` | — | [src](../../../core/runtime/db_governance.py#L223) |
| function | `_tool_intent_approval_request_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L255) |
| function | `record_runtime_contract_file_write` | `(*, write_id, candidate_id, target_file, canonical_key, write_status, actor, summary, content_line, created_at)` | — | [src](../../../core/runtime/db_governance.py#L289) |
| function | `get_runtime_contract_file_write` | `(write_id)` | — | [src](../../../core/runtime/db_governance.py#L337) |
| function | `recent_runtime_contract_file_writes` | `(limit=…)` | — | [src](../../../core/runtime/db_governance.py#L363) |
| function | `runtime_contract_file_write_counts` | `()` | — | [src](../../../core/runtime/db_governance.py#L387) |
| function | `_ensure_runtime_contract_file_write_table` | `(conn)` | — | [src](../../../core/runtime/db_governance.py#L404) |
| function | `_runtime_contract_file_write_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L429) |
| function | `record_runtime_webchat_execution_pilot` | `(*, pilot_id, canonical_key, status, execution_type, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, delivery_channel=…, delivery_state=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_governance.py#L452) |
| function | `list_runtime_webchat_execution_pilots` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_governance.py#L534) |
| function | `get_runtime_webchat_execution_pilot` | `(pilot_id)` | — | [src](../../../core/runtime/db_governance.py#L581) |
| function | `_runtime_webchat_execution_pilot_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L619) |

## `core/runtime/db_governance_ledger.py`
_Governance-ledger — PERSISTENT log af governerede mutationer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | Opret governance_ledger-tabellen hvis den ikke findes. Idempotent. | [src](../../../core/runtime/db_governance_ledger.py#L23) |
| function | `record_mutation` | `(area, key, value)` | Skriv én række til governance_ledger. Self-safe — sluger fejl. | [src](../../../core/runtime/db_governance_ledger.py#L50) |
| function | `read_ledger` | `(area=…, limit=…)` | Læs seneste mutationer. Filtrér på area hvis givet. Selv-sikker → [] ved fejl. | [src](../../../core/runtime/db_governance_ledger.py#L73) |
| function | `summary` | `()` | Aggregér pr. area: {area: {total, latest_ts, keys: [distinkte nøgler]}}. | [src](../../../core/runtime/db_governance_ledger.py#L110) |

## `core/runtime/db_heartbeat.py`
_Persistence for the heartbeat runtime tables — Jarvis' tick rhythm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_heartbeat_tables` | `(conn)` | — | [src](../../../core/runtime/db_heartbeat.py#L17) |
| function | `_ensure_heartbeat_runtime_state_columns` | `(conn)` | — | [src](../../../core/runtime/db_heartbeat.py#L102) |
| function | `_ensure_heartbeat_runtime_tick_columns` | `(conn)` | — | [src](../../../core/runtime/db_heartbeat.py#L247) |
| function | `_heartbeat_runtime_state_from_row` | `(row)` | — | [src](../../../core/runtime/db_heartbeat.py#L301) |
| function | `_heartbeat_runtime_tick_from_row` | `(row)` | — | [src](../../../core/runtime/db_heartbeat.py#L340) |
| function | `get_heartbeat_runtime_state` | `()` | — | [src](../../../core/runtime/db_heartbeat.py#L373) |
| function | `upsert_heartbeat_runtime_state` | `(*, state_id, last_tick_id, last_tick_at, next_tick_at, schedule_state, due, last_decision_type, last_result, blocked_reason, currently_ticking, last_trigger_source, scheduler_active, scheduler_started_at, scheduler_stopped_at, scheduler_health, recovery_status, last_recovery_at, provider, model, lane, model_source, resolution_status, fallback_used, execution_status, parse_status, budget_status, last_ping_eligible, last_ping_result, last_action_type, last_action_status, last_action_summary, last_action_artifact, updated_at, last_successful_ping_at=…)` | — | [src](../../../core/runtime/db_heartbeat.py#L421) |
| function | `record_heartbeat_runtime_tick` | `(*, tick_id, trigger, tick_status, decision_type, decision_summary, decision_reason, blocked_reason, provider, model, lane, model_source, resolution_status, fallback_used, execution_status, parse_status, budget_status, ping_eligible, ping_result, action_status, action_summary, action_type, action_artifact, raw_response, input_tokens, output_tokens, cost_usd, started_at, finished_at)` | — | [src](../../../core/runtime/db_heartbeat.py#L598) |
| function | `get_heartbeat_runtime_tick` | `(tick_id)` | — | [src](../../../core/runtime/db_heartbeat.py#L702) |
| function | `recent_heartbeat_runtime_ticks` | `(limit=…)` | — | [src](../../../core/runtime/db_heartbeat.py#L746) |

## `core/runtime/db_inbox.py`
_Lageret bag indbakken: `inbox_items`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/runtime/db_inbox.py#L69) |
| function | `_ensure_skema` | `(conn)` | DDL ÉN gang pr. proces — se modulets docstring om den eksklusive lås. | [src](../../../core/runtime/db_inbox.py#L73) |
| function | `_ensure_kolonner` | `(conn)` | Tilføj kolonner der kom senere. Idempotent; kaster ikke på en dublet. | [src](../../../core/runtime/db_inbox.py#L142) |
| function | `_post_fra_raekke` | `(r)` | Rækken som en typet post. `output_bytes` bevarer sin NULL. | [src](../../../core/runtime/db_inbox.py#L158) |
| function | `_felt` | `(r, navn)` | Læs en kolonne der måske ikke findes i DENNE række endnu. | [src](../../../core/runtime/db_inbox.py#L210) |
| function | `opret_eller_hent` | `(*, bruger_id, kildetype, kilde_id, oprettende_run_id=…, verificeret_ejer=…, kraever_handling=…, beskrivelse=…, output_sti=…, output_bytes=…, bloker=…, expires_at=…)` | Idempotent registrering. Findes posten, returneres DEN — urørt. | [src](../../../core/runtime/db_inbox.py#L232) |
| function | `hent` | `(*, bruger_id, kilde_id)` | Én post for ÉN bruger. Ingen bruger ⇒ None, aldrig en anden brugers. | [src](../../../core/runtime/db_inbox.py#L306) |
| function | `liste` | `(*, bruger_id, kun_aabne=…, maks=…)` | Poster for ÉN bruger. Tom bruger ⇒ tom liste, ALDRIG alle brugeres. | [src](../../../core/runtime/db_inbox.py#L321) |
| function | `afgoer` | `(*, bruger_id, kilde_id, ny_status, grund=…)` | Sæt en terminal status. Idempotent: en allerede afgjort post ændres IKKE. | [src](../../../core/runtime/db_inbox.py#L349) |
| function | `genaabn_af_kilde` | `(*, bruger_id, kilde_id)` | Genåbn en post der blev UDSAT, når dens kilde stadig melder den aktuel. | [src](../../../core/runtime/db_inbox.py#L408) |
| function | `opdater_beskrivelse` | `(*, bruger_id, kilde_id, beskrivelse)` | Lad kilden rette TEKSTEN på en post der ikke er afgjort. | [src](../../../core/runtime/db_inbox.py#L469) |
| function | `noter_paamindelse` | `(*, bruger_id, kilde_id, tur)` | Tæl ÉN leveret påmindelse. Samme tur to gange tæller ÉN gang. | [src](../../../core/runtime/db_inbox.py#L551) |
| function | `nulstil_paamindelse` | `(*, bruger_id, kilde_id)` | Ryd påmindelses-sporet, så posten kan vækkes igen. | [src](../../../core/runtime/db_inbox.py#L592) |
| function | `er_udloebet` | `(post, nu=…)` | Er posten udløbet? Beregnet, så den dør uden at et job skal køre. | [src](../../../core/runtime/db_inbox.py#L648) |
| function | `saet_udloeb` | `(*, bruger_id, kilde_id, expires_at)` | Sæt (eller fjern, med tom streng) en posts frist. | [src](../../../core/runtime/db_inbox.py#L677) |
| function | `fej_udloebne` | `(*, maks=…)` | Skriv den terminale tilstand for åbne poster hvis frist er passeret. | [src](../../../core/runtime/db_inbox.py#L693) |
| function | `meld_kilde_faerdig` | `(*, bruger_id, kilde_id, exit_kode)` | Kilden melder sig færdig. Nedgradér posten — hvis den gik GODT. | [src](../../../core/runtime/db_inbox.py#L757) |
| function | `liste_aktiv` | `(*, bruger_id, maks=…)` | Den AKTIVE visning: åbne poster plus nyligt lukkede. | [src](../../../core/runtime/db_inbox.py#L818) |

## `core/runtime/db_instrument.py`
_Persistens for central_instrument — selv-instrumenterings-motorens fund + scan-cache._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_instrument.py#L20) |
| function | `get_file_hash` | `(file)` | Sidst-scannede indholds-hash for en fil (til incremental skip). Self-safe → None. | [src](../../../core/runtime/db_instrument.py#L54) |
| function | `set_file_hash` | `(file, content_hash, n_findings)` | — | [src](../../../core/runtime/db_instrument.py#L68) |
| function | `replace_file_findings` | `(file, findings)` | Erstat ALLE åbne fund for én fil (idempotent pr. scan). Bevarer status (fx 'dismissed') | [src](../../../core/runtime/db_instrument.py#L84) |
| function | `prune_missing_files` | `(existing)` | Slet fund for filer der ikke længere findes i træet. Returnerer antal ryddede filer. | [src](../../../core/runtime/db_instrument.py#L120) |
| function | `list_findings` | `(*, status=…, min_score=…, limit=…, exclude_signatures=…)` | Fund (højeste score først). Self-safe → []. | [src](../../../core/runtime/db_instrument.py#L155) |
| function | `set_finding_status` | `(signature, status)` | Sæt status på ét fund — lukker hagen. | [src](../../../core/runtime/db_instrument.py#L183) |
| function | `summary` | `()` | Hurtig optælling pr. severity + total (til observe/central_query). Self-safe. | [src](../../../core/runtime/db_instrument.py#L210) |

## `core/runtime/db_interlanguage_blind.py`
_DB layer for interlanguage validation blind-dommer UI._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_interlanguage_blind_trials_table` | `(conn)` | Idempotently create blind-trials tabel + index. | [src](../../../core/runtime/db_interlanguage_blind.py#L22) |
| function | `create_alpha_trial` | `(*, session_id, trial_index, expression_id, expression_text, true_peer_id, mode=…)` | Opret en α-trial (expression vist, brugeren skal vælge forfatter). | [src](../../../core/runtime/db_interlanguage_blind.py#L73) |
| function | `create_delta_trial` | `(*, session_id, trial_index, anchor_id, anchor_text, candidate_a_id, candidate_a_text, candidate_a_peer_id, candidate_b_id, candidate_b_text, candidate_b_peer_id, jp_position, mode=…)` | Opret en δ-trial (anchor + 2 candidates, pair-comparison). | [src](../../../core/runtime/db_interlanguage_blind.py#L106) |
| function | `submit_answer` | `(*, trial_id, user_answer)` | Gem Bjørn's svar + beregn correctness. | [src](../../../core/runtime/db_interlanguage_blind.py#L150) |
| function | `get_progress` | `(*, session_id)` | Returnér antal besvarede + total + accuracy per type. | [src](../../../core/runtime/db_interlanguage_blind.py#L196) |
| function | `get_next_unanswered` | `(*, session_id)` | Returnér næste ubevarede trial i sessions trial_index-orden, eller None hvis færdig. | [src](../../../core/runtime/db_interlanguage_blind.py#L221) |
| function | `store_free_text_observations` | `(*, session_id, text)` | Gem free-text noter ved slutningen af session. | [src](../../../core/runtime/db_interlanguage_blind.py#L237) |
| function | `get_confusion_matrix` | `(*, session_id)` | Confusion-matrix for α-trials: true_peer × user_answer counts. | [src](../../../core/runtime/db_interlanguage_blind.py#L257) |

## `core/runtime/db_lessons.py`
_`lessons` — the one store for what Jarvis learns from mistakes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_lessons.py#L62) |
| function | `signature_key` | `(signature)` | Lowercase, punctuation-free, stopword-free, first 12 tokens. | [src](../../../core/runtime/db_lessons.py#L66) |
| function | `ensure_lessons_table` | `(conn)` | — | [src](../../../core/runtime/db_lessons.py#L72) |
| function | `_row` | `(r)` | — | [src](../../../core/runtime/db_lessons.py#L95) |
| function | `_jaccard` | `(a, b)` | — | [src](../../../core/runtime/db_lessons.py#L105) |
| function | `_find_match` | `(conn, key)` | — | [src](../../../core/runtime/db_lessons.py#L112) |
| function | `upsert_lesson` | `(*, signature, lesson, source, user_words=…, jarvis_words=…, activate=…, now=…)` | Insert or reinforce a lesson. Returns the stored row plus ``outcome``: | [src](../../../core/runtime/db_lessons.py#L128) |
| function | `get_lesson` | `(lesson_id)` | — | [src](../../../core/runtime/db_lessons.py#L185) |
| function | `list_lessons` | `(*, status=…, limit=…, source=…)` | — | [src](../../../core/runtime/db_lessons.py#L192) |
| function | `count_lessons` | `(*, status=…)` | — | [src](../../../core/runtime/db_lessons.py#L212) |
| function | `find_similar_lessons` | `(text, *, limit=…, status=…)` | Active lessons most similar to ``text`` (BM25 over signature + lesson). | [src](../../../core/runtime/db_lessons.py#L222) |
| function | `record_repeat` | `(lesson_id, *, now=…)` | — | [src](../../../core/runtime/db_lessons.py#L249) |
| function | `retire_stale` | `(*, days=…, min_evidence=…, now=…)` | Retire proposed/active lessons with evidence < min_evidence, no repeat, | [src](../../../core/runtime/db_lessons.py#L262) |
| function | `set_lesson_status` | `(lesson_id, status)` | Saet en lektions status. Returnerer raekken bagefter, eller None. | [src](../../../core/runtime/db_lessons.py#L278) |

## `core/runtime/db_private_brain.py`
_Private brain records — Jarvis' EGNE private lag (private-carry-erindringer med_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_private_brain_records_table` | `(conn)` | — | [src](../../../core/runtime/db_private_brain.py#L22) |
| function | `_private_brain_record_from_row` | `(row)` | — | [src](../../../core/runtime/db_private_brain.py#L67) |
| function | `_is_boilerplate_carry` | `(summary, detail)` | True hvis en record er ren skabelon uden informationsindhold ud over det der allerede | [src](../../../core/runtime/db_private_brain.py#L109) |
| function | `insert_private_brain_record` | `(*, record_id, record_type, layer, session_id, run_id, focus, summary, detail, source_signals, confidence, created_at, domain=…)` | — | [src](../../../core/runtime/db_private_brain.py#L122) |
| function | `list_private_brain_records` | `(*, limit=…, session_id=…, status=…, record_type=…)` | — | [src](../../../core/runtime/db_private_brain.py#L162) |
| function | `list_private_brain_records_older_than` | `(*, status, older_than_iso, limit=…, max_salience=…)` | Records i ``status`` med ``created_at < older_than_iso``, ÆLDSTE først. | [src](../../../core/runtime/db_private_brain.py#L195) |
| function | `search_private_brain_records` | `(query, *, limit=…, exclude_status=…)` | Tekst-søgning (LIKE) over HELE private_brain_records — focus/summary/detail. | [src](../../../core/runtime/db_private_brain.py#L229) |
| function | `update_private_brain_record_status` | `(record_id, *, status, updated_at)` | Lifecycle-overgang (active|settling|fading|released). Non-destruktiv. | [src](../../../core/runtime/db_private_brain.py#L276) |
| function | `get_private_brain_record` | `(record_id)` | — | [src](../../../core/runtime/db_private_brain.py#L293) |
| function | `update_private_brain_record_salience` | `(record_id, salience)` | Sæt salience (0.0–1.0) for en private-brain-record. | [src](../../../core/runtime/db_private_brain.py#L313) |
| function | `get_salient_private_brain_records` | `(threshold=…, limit=…)` | Aktive records med salience >= threshold, salience-sorteret. | [src](../../../core/runtime/db_private_brain.py#L325) |
| function | `decay_private_brain_records` | `(decay_rate=…, limit=…)` | Reducér salience på gamle aktive records. Returnerer antal opdaterede. | [src](../../../core/runtime/db_private_brain.py#L348) |
| function | `decay_private_brain_records_by_domain` | `(domain_decay_rates, default_rate=…, limit=…)` | Per-domæne salience-decay på aktive records. Returnerer {domæne: antal}. | [src](../../../core/runtime/db_private_brain.py#L369) |

## `core/runtime/db_private_notes.py`
_Persistence for the private/protected inner-layer note tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_private_notes_tables` | `(conn)` | — | [src](../../../core/runtime/db_private_notes.py#L15) |
| function | `_ensure_private_inner_note_columns` | `(conn)` | — | [src](../../../core/runtime/db_private_notes.py#L75) |
| function | `_ensure_enriched_columns` | `(conn)` | Add enriched column to private layer tables if missing. | [src](../../../core/runtime/db_private_notes.py#L91) |
| function | `record_private_inner_note` | `(*, note_id, source, run_id, work_id, status, note_kind, focus, uncertainty, identity_alignment, work_signal, private_summary, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L100) |
| function | `update_private_inner_note_enriched` | `(*, run_id, enriched_summary)` | Replace template summary with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L154) |
| function | `recent_private_inner_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L171) |
| function | `record_private_growth_note` | `(*, record_id, source, run_id, work_id, learning_kind, lesson, mistake_signal, helpful_signal, identity_signal, confidence, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L213) |
| function | `update_private_growth_note_enriched` | `(*, run_id, enriched_lesson, enriched_helpful_signal)` | Replace template lesson and helpful_signal with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L264) |
| function | `recent_private_growth_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L276) |
| function | `record_protected_inner_voice` | `(*, voice_id, source, run_id, work_id, mood_tone, self_position, current_concern, current_pull, voice_line, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L316) |
| function | `update_protected_inner_voice_enriched` | `(*, run_id, enriched_voice_line)` | Replace template voice_line with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L364) |
| function | `get_protected_inner_voice` | `(*, offset=…)` | Seneste beskyttede indre stemme. ``offset`` går et skridt længere tilbage. | [src](../../../core/runtime/db_private_notes.py#L374) |
| function | `list_recent_protected_inner_voices` | `(*, limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L416) |

## `core/runtime/db_private_signals.py`
_Persistence for the private inner-life signal tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_private_signals_tables` | `(conn)` | — | [src](../../../core/runtime/db_private_signals.py#L16) |
| function | `_ensure_private_retained_memory_record_columns` | `(conn)` | — | [src](../../../core/runtime/db_private_signals.py#L87) |
| function | `record_private_reflective_selection` | `(*, signal_id, source, run_id, work_id, selection_kind, reinforce, reconsider, fade, identity_relevance, confidence, created_at)` | — | [src](../../../core/runtime/db_private_signals.py#L101) |
| function | `recent_private_reflective_selections` | `(limit=…)` | — | [src](../../../core/runtime/db_private_signals.py#L152) |
| function | `record_private_development_state` | `(*, state_id, source, retained_pattern, preferred_direction, recurring_tension, identity_thread, confidence, created_at, updated_at)` | — | [src](../../../core/runtime/db_private_signals.py#L192) |
| function | `get_private_development_state` | `()` | — | [src](../../../core/runtime/db_private_signals.py#L237) |
| function | `get_private_reflective_selection` | `()` | — | [src](../../../core/runtime/db_private_signals.py#L271) |
| function | `record_private_temporal_promotion_signal` | `(*, signal_id, source, run_id, work_id, rhythm_state, rhythm_window, promotion_target, promotion_action, promotion_confidence, created_at)` | — | [src](../../../core/runtime/db_private_signals.py#L309) |
| function | `get_private_temporal_promotion_signal` | `()` | — | [src](../../../core/runtime/db_private_signals.py#L357) |
| function | `_norm_retained` | `(value)` | Normalisér til novelty-sammenligning: trim, lowercase, kollaps whitespace. | [src](../../../core/runtime/db_private_signals.py#L393) |
| function | `record_private_retained_memory_record` | `(*, record_id, source, run_id, work_id, retained_value, retained_kind, retention_scope, retention_horizon, confidence, created_at)` | — | [src](../../../core/runtime/db_private_signals.py#L398) |
| function | `update_private_retained_memory_record_enriched` | `(*, run_id, enriched_value)` | Replace template retained_value with LLM-enriched lesson text. | [src](../../../core/runtime/db_private_signals.py#L464) |
| function | `get_private_retained_memory_record` | `()` | — | [src](../../../core/runtime/db_private_signals.py#L476) |
| function | `recent_private_retained_memory_records` | `(limit=…)` | — | [src](../../../core/runtime/db_private_signals.py#L512) |

## `core/runtime/db_private_states.py`
_Persistence for the private self-model / mood / promotion-decision tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_private_states_tables` | `(conn)` | — | [src](../../../core/runtime/db_private_states.py#L14) |
| function | `record_private_self_model` | `(*, model_id, source, identity_focus, preferred_work_mode, recurring_tension, growth_direction, confidence, created_at, updated_at)` | — | [src](../../../core/runtime/db_private_states.py#L64) |
| function | `get_private_self_model` | `()` | — | [src](../../../core/runtime/db_private_states.py#L109) |
| function | `record_private_state` | `(*, state_id, source, frustration, fatigue, confidence, curiosity, created_at, updated_at)` | — | [src](../../../core/runtime/db_private_states.py#L143) |
| function | `get_private_state` | `()` | — | [src](../../../core/runtime/db_private_states.py#L185) |
| function | `record_private_promotion_decision` | `(*, decision_id, source, run_id, work_id, promotion_target, promotion_action, promotion_scope, confidence, created_at)` | — | [src](../../../core/runtime/db_private_states.py#L217) |
| function | `get_private_promotion_decision` | `()` | — | [src](../../../core/runtime/db_private_states.py#L262) |

## `core/runtime/db_runtime_browser.py`
_Persistence for the `runtime_browser_bodies` table — Jarvis' browser bodies._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_browser_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_browser.py#L13) |
| function | `get_runtime_browser_body` | `(body_id)` | — | [src](../../../core/runtime/db_runtime_browser.py#L41) |
| function | `upsert_runtime_browser_body` | `(*, body_id, profile_name, status, active_task_id=…, active_flow_id=…, focused_tab_id=…, tabs_json=…, last_url=…, last_title=…, summary=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_browser.py#L82) |
| function | `list_runtime_browser_bodies` | `(limit=…)` | — | [src](../../../core/runtime/db_runtime_browser.py#L149) |

## `core/runtime/db_runtime_chronicle.py`
_Persistence for Jarvis' runtime chronicle-consolidation signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_runtime_consolidation_target_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L23) |
| function | `_ensure_runtime_chronicle_consolidation_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L64) |
| function | `_ensure_runtime_chronicle_consolidation_brief_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L107) |
| function | `_ensure_runtime_chronicle_consolidation_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L150) |
| function | `_runtime_consolidation_target_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L193) |
| function | `_runtime_chronicle_consolidation_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L219) |
| function | `_runtime_chronicle_consolidation_brief_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L245) |
| function | `_runtime_chronicle_consolidation_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_chronicle.py#L271) |
| function | `upsert_runtime_consolidation_target_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a consolidation-target signal keyed on ``signal_id``. | [src](../../../core/runtime/db_runtime_chronicle.py#L297) |
| function | `list_runtime_consolidation_target_signals` | `(*, status=…, limit=…)` | Return consolidation-target signals newest-first as row dicts. | [src](../../../core/runtime/db_runtime_chronicle.py#L369) |
| function | `get_runtime_consolidation_target_signal` | `(signal_id)` | Return the consolidation-target signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_chronicle.py#L419) |
| function | `update_runtime_consolidation_target_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on a consolidation-target signal. | [src](../../../core/runtime/db_runtime_chronicle.py#L456) |
| function | `supersede_runtime_consolidation_target_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all live consolidation-target signals in a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_chronicle.py#L492) |
| function | `upsert_runtime_chronicle_consolidation_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a chronicle-consolidation signal keyed on ``signal_id``. | [src](../../../core/runtime/db_runtime_chronicle.py#L528) |
| function | `list_runtime_chronicle_consolidation_signals` | `(*, status=…, limit=…)` | Return chronicle-consolidation signals newest-first as row dicts. | [src](../../../core/runtime/db_runtime_chronicle.py#L599) |
| function | `get_runtime_chronicle_consolidation_signal` | `(signal_id)` | Return the chronicle-consolidation signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_chronicle.py#L649) |
| function | `update_runtime_chronicle_consolidation_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on a chronicle-consolidation signal. | [src](../../../core/runtime/db_runtime_chronicle.py#L688) |
| function | `supersede_runtime_chronicle_consolidation_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all live chronicle-consolidation signals in a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_chronicle.py#L724) |
| function | `upsert_runtime_chronicle_consolidation_brief` | `(*, brief_id, brief_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a chronicle-consolidation brief keyed on ``brief_id``. | [src](../../../core/runtime/db_runtime_chronicle.py#L760) |
| function | `list_runtime_chronicle_consolidation_briefs` | `(*, status=…, limit=…)` | Return chronicle-consolidation briefs newest-first as row dicts. | [src](../../../core/runtime/db_runtime_chronicle.py#L842) |
| function | `get_runtime_chronicle_consolidation_brief` | `(brief_id)` | Return the chronicle-consolidation brief row dict for ``brief_id``, or None if absent. | [src](../../../core/runtime/db_runtime_chronicle.py#L892) |
| function | `update_runtime_chronicle_consolidation_brief_status` | `(brief_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on a chronicle-consolidation brief. | [src](../../../core/runtime/db_runtime_chronicle.py#L931) |
| function | `supersede_runtime_chronicle_consolidation_briefs_for_domain` | `(*, domain_key, exclude_brief_id, updated_at, status_reason)` | Mark all live chronicle-consolidation briefs in a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_chronicle.py#L967) |
| function | `upsert_runtime_chronicle_consolidation_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a chronicle-consolidation proposal keyed on ``proposal_id``. | [src](../../../core/runtime/db_runtime_chronicle.py#L1003) |
| function | `list_runtime_chronicle_consolidation_proposals` | `(*, status=…, limit=…)` | Return chronicle-consolidation proposals newest-first as row dicts. | [src](../../../core/runtime/db_runtime_chronicle.py#L1074) |
| function | `get_runtime_chronicle_consolidation_proposal` | `(proposal_id)` | Return the chronicle-consolidation proposal row dict for ``proposal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_chronicle.py#L1124) |
| function | `update_runtime_chronicle_consolidation_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on a chronicle-consolidation proposal. | [src](../../../core/runtime/db_runtime_chronicle.py#L1163) |
| function | `supersede_runtime_chronicle_consolidation_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | Mark all live chronicle-consolidation proposals in a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_chronicle.py#L1199) |

## `core/runtime/db_runtime_cognition_signals.py`
_Persistence for Jarvis' runtime cognition-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_reflective_critic` | `(*, critic_id, critic_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime reflective-critic row keyed by ``canonical_key``. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L31) |
| function | `list_runtime_reflective_critics` | `(*, status=…, limit=…)` | Return reflective-critic rows (dicts), newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L255) |
| function | `get_runtime_reflective_critic` | `(critic_id)` | Return the reflective-critic row for ``critic_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L305) |
| function | `update_runtime_reflective_critic_status` | `(critic_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one reflective critic. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L343) |
| function | `supersede_runtime_reflective_critics` | `(*, critic_type, exclude_critic_id, updated_at, status_reason)` | Mark all active/stale critics of ``critic_type`` (except ``exclude_critic_id``) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L381) |
| function | `upsert_runtime_awareness_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime awareness-signal row keyed by ``canonical_key``. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L416) |
| function | `list_runtime_awareness_signals` | `(*, status=…, limit=…)` | Return awareness-signal rows (dicts), newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L634) |
| function | `get_runtime_awareness_signal` | `(signal_id)` | Return the awareness-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L684) |
| function | `update_runtime_awareness_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one awareness signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L722) |
| function | `supersede_runtime_awareness_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | Mark all live awareness signals of ``signal_type`` (except ``exclude_signal_id``) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L760) |
| function | `upsert_runtime_reflection_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime reflection-signal row via the shared _upsert_signal helper. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L796) |
| function | `list_runtime_reflection_signals` | `(*, status=…, limit=…)` | Return reflection-signal rows (dicts), newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L868) |
| function | `get_runtime_reflection_signal` | `(signal_id)` | Return the reflection-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L918) |
| function | `update_runtime_reflection_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one reflection signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L956) |
| function | `supersede_runtime_reflection_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark active reflection signals for a domain (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L994) |
| function | `upsert_runtime_witness_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime witness-signal row via the shared _upsert_signal helper. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1031) |
| function | `list_runtime_witness_signals` | `(*, status=…, limit=…)` | Return witness-signal rows (dicts), newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1102) |
| function | `get_runtime_witness_signal` | `(signal_id)` | Return the witness-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1152) |
| function | `update_runtime_witness_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one witness signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1190) |
| function | `supersede_runtime_witness_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark fresh/carried/fading witness signals for a domain (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1228) |
| function | `upsert_runtime_internal_opposition_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime internal-opposition-signal row via _upsert_signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1264) |
| function | `list_runtime_internal_opposition_signals` | `(*, status=…, limit=…)` | Return internal-opposition-signal rows (dicts), newest first, optionally by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1335) |
| function | `get_runtime_internal_opposition_signal` | `(signal_id)` | Return the internal-opposition-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1385) |
| function | `update_runtime_internal_opposition_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one internal-opposition signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1423) |
| function | `supersede_runtime_internal_opposition_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark active/softening/stale internal-opposition signals for a domain (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1461) |
| function | `upsert_runtime_meaning_significance_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime meaning-significance-signal row via _upsert_signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1497) |
| function | `list_runtime_meaning_significance_signals` | `(*, status=…, limit=…)` | Return meaning-significance-signal rows (dicts), newest first, optionally by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1568) |
| function | `get_runtime_meaning_significance_signal` | `(signal_id)` | Return the meaning-significance-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1618) |
| function | `update_runtime_meaning_significance_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one meaning-significance signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1656) |
| function | `supersede_runtime_meaning_significance_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark active/softening/stale meaning-significance signals for a focus (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1694) |
| function | `upsert_runtime_metabolism_state_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime metabolism-state-signal row via _upsert_signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1730) |
| function | `list_runtime_metabolism_state_signals` | `(*, status=…, limit=…)` | Return metabolism-state-signal rows (dicts), newest first, optionally by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1801) |
| function | `get_runtime_metabolism_state_signal` | `(signal_id)` | Return the metabolism-state-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1851) |
| function | `update_runtime_metabolism_state_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one metabolism-state signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1889) |
| function | `supersede_runtime_metabolism_state_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark active/softening/stale metabolism-state signals for a domain (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1927) |
| function | `upsert_runtime_executive_contradiction_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime executive-contradiction-signal row via _upsert_signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L1963) |
| function | `list_runtime_executive_contradiction_signals` | `(*, status=…, limit=…)` | Return executive-contradiction-signal rows (dicts), newest first, optionally by status. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2034) |
| function | `get_runtime_executive_contradiction_signal` | `(signal_id)` | Return the executive-contradiction-signal row for ``signal_id`` as a dict, or None if absent. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2084) |
| function | `update_runtime_executive_contradiction_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one executive-contradiction signal. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2124) |
| function | `supersede_runtime_executive_contradiction_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark active/softening/stale executive-contradiction signals for a domain (except one) superseded. | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2162) |
| function | `_ensure_runtime_reflective_critic_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2198) |
| function | `_ensure_runtime_awareness_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2240) |
| function | `_ensure_runtime_reflection_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2282) |
| function | `_ensure_runtime_witness_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2324) |
| function | `_ensure_runtime_internal_opposition_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2366) |
| function | `_ensure_runtime_meaning_significance_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2408) |
| function | `_ensure_runtime_metabolism_state_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2450) |
| function | `_ensure_runtime_executive_contradiction_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2492) |
| function | `_runtime_meaning_significance_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2536) |
| function | `_runtime_metabolism_state_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2563) |
| function | `_runtime_executive_contradiction_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2588) |
| function | `_runtime_reflective_critic_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2615) |
| function | `_runtime_awareness_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2640) |
| function | `_runtime_reflection_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2665) |
| function | `_runtime_witness_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2690) |
| function | `_runtime_internal_opposition_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_cognition_signals.py#L2715) |

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
| function | `upsert_runtime_dream_hypothesis_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a dream hypothesis signal into runtime_dream_hypothesis_signals. | [src](../../../core/runtime/db_runtime_dream.py#L220) |
| function | `list_runtime_dream_hypothesis_signals` | `(*, status=…, limit=…)` | Return dream hypothesis signals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_dream.py#L291) |
| function | `get_runtime_dream_hypothesis_signal` | `(signal_id)` | Return the dream hypothesis signal with this signal_id as a row dict, or None if absent. | [src](../../../core/runtime/db_runtime_dream.py#L349) |
| function | `update_runtime_dream_hypothesis_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at of one dream hypothesis signal. | [src](../../../core/runtime/db_runtime_dream.py#L386) |
| function | `supersede_runtime_dream_hypothesis_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live dream hypothesis signals for a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_dream.py#L423) |
| function | `upsert_runtime_dream_adoption_candidate` | `(*, candidate_id, candidate_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a dream adoption candidate into runtime_dream_adoption_candidates. | [src](../../../core/runtime/db_runtime_dream.py#L459) |
| function | `list_runtime_dream_adoption_candidates` | `(*, status=…, limit=…)` | Return dream adoption candidates as row dicts, newest first. | [src](../../../core/runtime/db_runtime_dream.py#L530) |
| function | `get_runtime_dream_adoption_candidate` | `(candidate_id)` | Return the dream adoption candidate with this candidate_id as a row dict, or None if absent. | [src](../../../core/runtime/db_runtime_dream.py#L588) |
| function | `update_runtime_dream_adoption_candidate_status` | `(candidate_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at of one dream adoption candidate. | [src](../../../core/runtime/db_runtime_dream.py#L625) |
| function | `supersede_runtime_dream_adoption_candidates_for_domain` | `(*, domain_key, exclude_candidate_id, updated_at, status_reason)` | Mark all still-live dream adoption candidates for a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_dream.py#L662) |
| function | `upsert_runtime_dream_influence_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a dream influence proposal into runtime_dream_influence_proposals. | [src](../../../core/runtime/db_runtime_dream.py#L698) |
| function | `list_runtime_dream_influence_proposals` | `(*, status=…, limit=…)` | Return dream influence proposals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_dream.py#L769) |
| function | `get_runtime_dream_influence_proposal` | `(proposal_id)` | Return the dream influence proposal with this proposal_id as a row dict, or None if absent. | [src](../../../core/runtime/db_runtime_dream.py#L827) |
| function | `update_runtime_dream_influence_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at of one dream influence proposal. | [src](../../../core/runtime/db_runtime_dream.py#L864) |
| function | `supersede_runtime_dream_influence_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | Mark all still-live dream influence proposals for a domain as 'superseded'. | [src](../../../core/runtime/db_runtime_dream.py#L901) |

## `core/runtime/db_runtime_executive_signals.py`
_Persistence for Jarvis' runtime executive-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_goal_signal` | `(*, goal_id, goal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime goal signal, keyed on ``canonical_key``. | [src](../../../core/runtime/db_runtime_executive_signals.py#L40) |
| function | `list_runtime_goal_signals` | `(*, status=…, limit=…)` | Return runtime goal signals ordered newest-first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_executive_signals.py#L263) |
| function | `get_runtime_goal_signal` | `(goal_id)` | Return the goal-signal row dict for ``goal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L312) |
| function | `update_runtime_goal_signal_status` | `(goal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one goal signal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L349) |
| function | `supersede_runtime_goal_signals` | `(*, goal_type, exclude_goal_id, updated_at, status_reason)` | Mark all active/blocked/stale goal signals of ``goal_type`` as superseded, | [src](../../../core/runtime/db_runtime_executive_signals.py#L385) |
| function | `_ensure_runtime_goal_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L418) |
| function | `_runtime_goal_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L459) |
| function | `upsert_runtime_world_model_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime world-model signal, keyed on ``canonical_key``. | [src](../../../core/runtime/db_runtime_executive_signals.py#L483) |
| function | `list_runtime_world_model_signals` | `(*, status=…, limit=…)` | Return runtime world-model signals newest-first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_executive_signals.py#L706) |
| function | `get_runtime_world_model_signal` | `(signal_id)` | Return the world-model signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L755) |
| function | `update_runtime_world_model_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one world-model signal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L792) |
| function | `supersede_runtime_world_model_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | Mark all active/uncertain/stale world-model signals of ``signal_type`` as | [src](../../../core/runtime/db_runtime_executive_signals.py#L828) |
| function | `_ensure_runtime_world_model_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L861) |
| function | `_runtime_world_model_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L902) |
| function | `upsert_runtime_development_focus` | `(*, focus_id, focus_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime development-focus row, keyed on ``canonical_key``. | [src](../../../core/runtime/db_runtime_executive_signals.py#L926) |
| function | `list_runtime_development_focuses` | `(*, status=…, limit=…)` | Return runtime development focuses newest-first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1151) |
| function | `get_runtime_development_focus` | `(focus_id)` | Return the development-focus row dict for ``focus_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1200) |
| function | `update_runtime_development_focus_status` | `(focus_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one development focus. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1237) |
| function | `supersede_runtime_development_focuses` | `(*, focus_type, exclude_focus_id, updated_at, status_reason)` | Mark all active/stale development focuses of ``focus_type`` as superseded, | [src](../../../core/runtime/db_runtime_executive_signals.py#L1273) |
| function | `_ensure_runtime_development_focus_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1306) |
| function | `_runtime_development_focus_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1347) |
| function | `upsert_runtime_autonomy_pressure_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime autonomy-pressure signal via the shared | [src](../../../core/runtime/db_runtime_executive_signals.py#L1371) |
| function | `list_runtime_autonomy_pressure_signals` | `(*, status=…, limit=…)` | Return runtime autonomy-pressure signals newest-first, optionally filtered | [src](../../../core/runtime/db_runtime_executive_signals.py#L1442) |
| function | `get_runtime_autonomy_pressure_signal` | `(signal_id)` | Return the autonomy-pressure signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1490) |
| function | `update_runtime_autonomy_pressure_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one autonomy-pressure signal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1527) |
| function | `supersede_runtime_autonomy_pressure_signals_for_type` | `(*, pressure_type, exclude_signal_id, updated_at, status_reason)` | Mark all active/softening/stale autonomy-pressure signals whose | [src](../../../core/runtime/db_runtime_executive_signals.py#L1563) |
| function | `_ensure_runtime_autonomy_pressure_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1597) |
| function | `_runtime_autonomy_pressure_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1638) |
| function | `upsert_runtime_open_loop_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime open-loop signal via the shared ``_upsert_signal`` | [src](../../../core/runtime/db_runtime_executive_signals.py#L1662) |
| function | `list_runtime_open_loop_signals` | `(*, status=…, limit=…)` | Return runtime open-loop signals newest-first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1733) |
| function | `get_runtime_open_loop_signal` | `(signal_id)` | Return the open-loop signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1782) |
| function | `update_runtime_open_loop_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one open-loop signal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L1819) |
| function | `supersede_runtime_open_loop_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all open/softening/closed/stale open-loop signals whose canonical_key | [src](../../../core/runtime/db_runtime_executive_signals.py#L1855) |
| function | `_ensure_runtime_open_loop_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1889) |
| function | `_runtime_open_loop_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L1930) |
| function | `upsert_runtime_open_loop_closure_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime open-loop closure proposal via the shared | [src](../../../core/runtime/db_runtime_executive_signals.py#L1954) |
| function | `list_runtime_open_loop_closure_proposals` | `(*, status=…, limit=…)` | Return runtime open-loop closure proposals newest-first, optionally filtered | [src](../../../core/runtime/db_runtime_executive_signals.py#L2025) |
| function | `get_runtime_open_loop_closure_proposal` | `(proposal_id)` | Return the closure-proposal row dict for ``proposal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2073) |
| function | `update_runtime_open_loop_closure_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one open-loop closure proposal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2112) |
| function | `supersede_runtime_open_loop_closure_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | Mark all fresh/active/fading/stale closure proposals whose canonical_key | [src](../../../core/runtime/db_runtime_executive_signals.py#L2148) |
| function | `_ensure_runtime_open_loop_closure_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2182) |
| function | `_runtime_open_loop_closure_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2223) |
| function | `upsert_runtime_contract_candidate` | `(*, candidate_id, candidate_type, target_file, status, source_kind, source_mode, actor, session_id, run_id, canonical_key, summary, reason, evidence_summary, support_summary, confidence, evidence_class, support_count, session_count, created_at, updated_at, status_reason=…, proposed_value=…, write_section=…, owner_workspace=…)` | Insert or merge a runtime contract candidate, keyed on | [src](../../../core/runtime/db_runtime_executive_signals.py#L2247) |
| function | `list_runtime_contract_candidates` | `(*, candidate_type=…, target_file=…, status=…, limit=…)` | Return runtime contract candidates newest-first, optionally filtered by | [src](../../../core/runtime/db_runtime_executive_signals.py#L2543) |
| function | `runtime_contract_candidate_status_for_key` | `(*, candidate_type, target_file, canonical_key)` | Returnér status for den nyeste kandidat med præcis denne nøgle, ellers None. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2606) |
| function | `get_runtime_contract_candidate` | `(candidate_id)` | Return the contract-candidate row dict for ``candidate_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2640) |
| function | `runtime_contract_candidate_counts` | `()` | Return per-(candidate_type, status) row counts keyed as ``"{type}:{status}"``. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2683) |
| function | `update_runtime_contract_candidate_status` | `(candidate_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one contract candidate. | [src](../../../core/runtime/db_runtime_executive_signals.py#L2704) |
| function | `supersede_runtime_contract_candidates` | `(*, candidate_type, target_file, canonical_key, exclude_candidate_id, updated_at, status_reason)` | Mark all proposed/approved contract candidates matching | [src](../../../core/runtime/db_runtime_executive_signals.py#L2740) |
| function | `_ensure_runtime_contract_candidate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2783) |
| function | `_runtime_contract_candidate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L2852) |
| function | `upsert_runtime_proactive_loop_lifecycle_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime proactive-loop lifecycle signal via the shared | [src](../../../core/runtime/db_runtime_executive_signals.py#L2882) |
| function | `list_runtime_proactive_loop_lifecycle_signals` | `(*, status=…, limit=…)` | Return runtime proactive-loop lifecycle signals newest-first, optionally | [src](../../../core/runtime/db_runtime_executive_signals.py#L2953) |
| function | `get_runtime_proactive_loop_lifecycle_signal` | `(signal_id)` | Return the proactive-loop lifecycle signal row dict for ``signal_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L3001) |
| function | `update_runtime_proactive_loop_lifecycle_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one proactive-loop lifecycle signal. | [src](../../../core/runtime/db_runtime_executive_signals.py#L3040) |
| function | `supersede_runtime_proactive_loop_lifecycle_signals_for_kind` | `(*, loop_kind, exclude_signal_id, updated_at, status_reason)` | Mark all active/softening/stale proactive-loop lifecycle signals whose | [src](../../../core/runtime/db_runtime_executive_signals.py#L3076) |
| function | `_ensure_runtime_proactive_loop_lifecycle_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3110) |
| function | `_runtime_proactive_loop_lifecycle_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3153) |
| function | `upsert_runtime_proactive_question_gate` | `(*, gate_id, gate_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a runtime proactive-question gate via the shared | [src](../../../core/runtime/db_runtime_executive_signals.py#L3179) |
| function | `list_runtime_proactive_question_gates` | `(*, status=…, limit=…)` | Return runtime proactive-question gates newest-first, optionally filtered by | [src](../../../core/runtime/db_runtime_executive_signals.py#L3250) |
| function | `get_runtime_proactive_question_gate` | `(gate_id)` | Return the proactive-question gate row dict for ``gate_id``, or None if absent. | [src](../../../core/runtime/db_runtime_executive_signals.py#L3298) |
| function | `update_runtime_proactive_question_gate_status` | `(gate_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one proactive-question gate. | [src](../../../core/runtime/db_runtime_executive_signals.py#L3335) |
| function | `supersede_runtime_proactive_question_gates_for_kind` | `(*, gate_type, exclude_gate_id, updated_at, status_reason)` | Mark all active/softening/stale proactive-question gates whose canonical_key | [src](../../../core/runtime/db_runtime_executive_signals.py#L3371) |
| function | `_ensure_runtime_proactive_question_gate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3406) |
| function | `_runtime_proactive_question_gate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_executive_signals.py#L3447) |

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
| function | `list_session_distillation_records` | `(*, limit=…, session_id=…)` | Return session-distillation records as dicts, newest first. | [src](../../../core/runtime/db_runtime_misc.py#L85) |
| function | `_ensure_cached_affective_state_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L115) |
| function | `save_cached_affective_state` | `(rendered_text, signals_json)` | Insert a cached affective-state row (rendered text + signals JSON, timestamped now). | [src](../../../core/runtime/db_runtime_misc.py#L128) |
| function | `get_cached_affective_state` | `(max_age_seconds=…)` | Return the most recent cached affective-state text, or None if none is newer than max_age_seconds. | [src](../../../core/runtime/db_runtime_misc.py#L140) |
| function | `_ensure_experiment_settings_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L161) |
| function | `get_experiment_enabled` | `(experiment_id)` | Return True if experiment is enabled. Defaults to True if no row exists. | [src](../../../core/runtime/db_runtime_misc.py#L171) |
| function | `set_experiment_enabled` | `(experiment_id, enabled)` | Enable or disable an experiment. Creates row if absent. | [src](../../../core/runtime/db_runtime_misc.py#L184) |
| function | `_ensure_recurrence_iterations_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L200) |
| function | `insert_recurrence_iteration` | `(*, iteration_id, content, keywords, stability_score, iteration_number)` | Upsert one recurrence-loop iteration (content truncated to 500 chars) keyed by iteration_id. | [src](../../../core/runtime/db_runtime_misc.py#L213) |
| function | `get_latest_recurrence_iteration` | `()` | Return the most recent recurrence iteration as a dict, or None if the table is empty. | [src](../../../core/runtime/db_runtime_misc.py#L233) |
| function | `list_recurrence_iterations` | `(limit=…)` | Return up to `limit` recurrence iterations as dicts, newest first ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L253) |
| function | `_ensure_broadcast_events_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L279) |
| function | `insert_broadcast_event` | `(*, event_id, topic_cluster, sources, source_count, payload_summary)` | Upsert one global-workspace broadcast event (payload_summary truncated to 300 chars) keyed by event_id. | [src](../../../core/runtime/db_runtime_misc.py#L292) |
| function | `list_broadcast_events` | `(limit=…)` | Return up to `limit` broadcast events as dicts, newest first ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L312) |
| function | `_ensure_meta_cognition_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L338) |
| function | `insert_meta_cognition_record` | `(*, record_id, meta_observation, meta_meta_observation, meta_depth, input_state_summary)` | Upsert one meta-cognition record (observation/meta-observation/input summary truncated) keyed by record_id. | [src](../../../core/runtime/db_runtime_misc.py#L351) |
| function | `list_meta_cognition_records` | `(limit=…)` | Return up to `limit` meta-cognition records as dicts, newest first ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L371) |
| function | `_ensure_attention_blink_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L397) |
| function | `insert_attention_blink_result` | `(*, test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation)` | Upsert one attention-blink test result (T1/T2 responses, blink ratio, interpretation) keyed by test_id. | [src](../../../core/runtime/db_runtime_misc.py#L411) |
| function | `list_attention_blink_results` | `(limit=…)` | Return up to `limit` attention-blink results as dicts, newest first ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L432) |
| function | `_ensure_session_summaries_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L460) |
| function | `session_summary_insert` | `(*, session_id, run_id=…, summary, key_topics=…, decisions_made=…)` | Insert one session summary row (summary/topics/decisions truncated, timestamped now). | [src](../../../core/runtime/db_runtime_misc.py#L482) |
| function | `session_summary_recent` | `(limit=…)` | Return the most recent session summaries FOR THIS USER. | [src](../../../core/runtime/db_runtime_misc.py#L503) |
| function | `session_summary_for_session` | `(session_id)` | Return the latest summary for a specific session. | [src](../../../core/runtime/db_runtime_misc.py#L553) |
| function | `session_summary_cleanup` | `(max_age_days=…)` | Delete session summaries older than max_age_days. | [src](../../../core/runtime/db_runtime_misc.py#L574) |
| function | `_ensure_signal_archive_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L589) |
| function | `signal_decay_archive_and_delete` | `(*, stale_hours=…)` | Archive and delete signals marked stale for longer than stale_hours. | [src](../../../core/runtime/db_runtime_misc.py#L613) |
| function | `signal_archive_cleanup` | `(max_age_days=…)` | Delete archived signals older than max_age_days. | [src](../../../core/runtime/db_runtime_misc.py#L677) |
| function | `signal_archive_recent` | `(limit=…)` | Return recent archived signals for debugging. | [src](../../../core/runtime/db_runtime_misc.py#L687) |
| function | `_ensure_aesthetic_motif_log_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L706) |
| function | `aesthetic_motif_log_insert` | `(*, source, motif, confidence)` | Insert one aesthetic-motif observation (source, motif, confidence) timestamped now. | [src](../../../core/runtime/db_runtime_misc.py#L723) |
| function | `aesthetic_motif_log_unique_motifs` | `()` | Return the distinct motif strings from the aesthetic-motif log, sorted alphabetically ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L742) |
| function | `aesthetic_motif_log_summary` | `()` | Return per-motif aggregates (motif, count, avg_confidence) ordered by count desc ([] if none). | [src](../../../core/runtime/db_runtime_misc.py#L752) |
| function | `_ensure_channel_attachments_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_misc.py#L774) |
| function | `store_channel_attachment` | `(*, conn, attachment_id, session_id, channel_type, filename, mime_type, size_bytes, local_path, source_url)` | Insert a channel-attachment metadata row on the given connection (no-op if attachment_id already exists). | [src](../../../core/runtime/db_runtime_misc.py#L797) |
| function | `get_channel_attachment` | `(*, conn, attachment_id)` | Return the channel attachment matching attachment_id as a dict, or None if absent (uses caller's conn). | [src](../../../core/runtime/db_runtime_misc.py#L828) |
| function | `list_channel_attachments` | `(*, conn, session_id, limit=…)` | Return up to `limit` attachments for `session_id` as dicts, newest first ([] if none; uses caller's conn). | [src](../../../core/runtime/db_runtime_misc.py#L846) |

## `core/runtime/db_runtime_private.py`
_Persistence for Jarvis' runtime private-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_private_inner_note_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private inner-note-signal via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L31) |
| function | `list_runtime_private_inner_note_signals` | `(*, status=…, limit=…)` | List private inner-note-signaler, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L104) |
| function | `get_runtime_private_inner_note_signal` | `(signal_id)` | Hent ét private inner-note-signal på signal_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L154) |
| function | `update_runtime_private_inner_note_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét inner-note-signal. | [src](../../../core/runtime/db_runtime_private.py#L191) |
| function | `supersede_runtime_private_inner_note_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Markér øvrige active/stale inner-note-signaler for et fokus som superseded. | [src](../../../core/runtime/db_runtime_private.py#L228) |
| function | `upsert_runtime_private_initiative_tension_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private initiative-tension-signal via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L264) |
| function | `list_runtime_private_initiative_tension_signals` | `(*, status=…, limit=…)` | List private initiative-tension-signaler, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L337) |
| function | `get_runtime_private_initiative_tension_signal` | `(signal_id)` | Hent ét private initiative-tension-signal på signal_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L387) |
| function | `update_runtime_private_initiative_tension_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét initiative-tension-signal. | [src](../../../core/runtime/db_runtime_private.py#L426) |
| function | `supersede_runtime_private_initiative_tension_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Markér øvrige active/stale initiative-tension-signaler for et domæne som superseded. | [src](../../../core/runtime/db_runtime_private.py#L463) |
| function | `upsert_runtime_private_inner_interplay_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private inner-interplay-signal via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L498) |
| function | `list_runtime_private_inner_interplay_signals` | `(*, status=…, limit=…)` | List private inner-interplay-signaler, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L569) |
| function | `get_runtime_private_inner_interplay_signal` | `(signal_id)` | Hent ét private inner-interplay-signal på signal_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L619) |
| function | `update_runtime_private_inner_interplay_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét inner-interplay-signal. | [src](../../../core/runtime/db_runtime_private.py#L658) |
| function | `supersede_runtime_private_inner_interplay_signals_for_relation` | `(*, relation_key, exclude_signal_id, updated_at, status_reason)` | Markér øvrige active/stale inner-interplay-signaler for en relation som superseded. | [src](../../../core/runtime/db_runtime_private.py#L695) |
| function | `upsert_runtime_private_state_snapshot` | `(*, snapshot_id, snapshot_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private state-snapshot via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L730) |
| function | `list_runtime_private_state_snapshots` | `(*, status=…, limit=…)` | List private state-snapshots, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L801) |
| function | `get_runtime_private_state_snapshot` | `(snapshot_id)` | Hent ét private state-snapshot på snapshot_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L851) |
| function | `update_runtime_private_state_snapshot_status` | `(snapshot_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét state-snapshot. | [src](../../../core/runtime/db_runtime_private.py#L888) |
| function | `supersede_runtime_private_state_snapshots_for_focus` | `(*, focus_key, exclude_snapshot_id, updated_at, status_reason)` | Markér øvrige active/stale state-snapshots for et fokus som superseded. | [src](../../../core/runtime/db_runtime_private.py#L925) |
| function | `upsert_runtime_private_temporal_curiosity_state` | `(*, state_id, state_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private temporal-curiosity-state via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L960) |
| function | `list_runtime_private_temporal_curiosity_states` | `(*, status=…, limit=…)` | List private temporal-curiosity-states, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L1031) |
| function | `get_runtime_private_temporal_curiosity_state` | `(state_id)` | Hent ét private temporal-curiosity-state på state_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L1081) |
| function | `update_runtime_private_temporal_curiosity_state_status` | `(state_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét temporal-curiosity-state. | [src](../../../core/runtime/db_runtime_private.py#L1120) |
| function | `supersede_runtime_private_temporal_curiosity_states_for_focus` | `(*, focus_key, exclude_state_id, updated_at, status_reason)` | Markér øvrige active/stale temporal-curiosity-states for et fokus som superseded. | [src](../../../core/runtime/db_runtime_private.py#L1157) |
| function | `upsert_runtime_private_temporal_promotion_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert (insert-or-merge) et private temporal-promotion-signal via _upsert_signal. | [src](../../../core/runtime/db_runtime_private.py#L1192) |
| function | `list_runtime_private_temporal_promotion_signals` | `(*, status=…, limit=…)` | List private temporal-promotion-signaler, nyeste først (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_private.py#L1265) |
| function | `get_runtime_private_temporal_promotion_signal` | `(signal_id)` | Hent ét private temporal-promotion-signal på signal_id, eller None hvis ukendt. | [src](../../../core/runtime/db_runtime_private.py#L1315) |
| function | `update_runtime_private_temporal_promotion_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Opdatér status/status_reason/updated_at på ét temporal-promotion-signal. | [src](../../../core/runtime/db_runtime_private.py#L1354) |
| function | `supersede_runtime_private_temporal_promotion_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Markér øvrige active/stale temporal-promotion-signaler for et fokus som superseded. | [src](../../../core/runtime/db_runtime_private.py#L1391) |
| function | `_ensure_runtime_private_inner_note_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1426) |
| function | `_ensure_runtime_private_initiative_tension_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1467) |
| function | `_ensure_runtime_private_inner_interplay_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1510) |
| function | `_ensure_runtime_private_state_snapshot_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1553) |
| function | `_ensure_runtime_private_temporal_curiosity_state_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1594) |
| function | `_ensure_runtime_private_temporal_promotion_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_private.py#L1637) |
| function | `_runtime_private_inner_note_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1680) |
| function | `_runtime_private_initiative_tension_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1704) |
| function | `_runtime_private_inner_interplay_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1730) |
| function | `_runtime_private_state_snapshot_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1756) |
| function | `_runtime_private_temporal_curiosity_state_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1780) |
| function | `_runtime_private_temporal_promotion_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_private.py#L1806) |

## `core/runtime/db_runtime_relational_signals.py`
_Persistence for Jarvis' runtime relational-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_user_md_update_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Upsert a runtime user-MD update proposal into runtime_user_md_update_proposals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L32) |
| function | `list_runtime_user_md_update_proposals` | `(*, status=…, limit=…)` | List runtime user-MD update proposals, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_relational_signals.py#L105) |
| function | `get_runtime_user_md_update_proposal` | `(proposal_id)` | Fetch a single user-MD update proposal by proposal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L155) |
| function | `update_runtime_user_md_update_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one proposal by proposal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L193) |
| function | `supersede_runtime_user_md_update_proposals_for_dimension` | `(*, dimension_key, exclude_proposal_id, updated_at, status_reason)` | Mark all open proposals for a dimension as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L230) |
| function | `upsert_runtime_user_understanding_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Upsert a runtime user-understanding signal into runtime_user_understanding_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L267) |
| function | `list_runtime_user_understanding_signals` | `(*, status=…, limit=…)` | List runtime user-understanding signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L339) |
| function | `get_runtime_user_understanding_signal` | `(signal_id)` | Fetch a single user-understanding signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L389) |
| function | `update_runtime_user_understanding_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one user-understanding signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L427) |
| function | `supersede_runtime_user_understanding_signals_for_dimension` | `(*, dimension_key, exclude_signal_id, updated_at, status_reason)` | Mark all open user-understanding signals for a dimension as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L464) |
| function | `upsert_runtime_inner_visible_support_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert an inner-visible-support signal into runtime_inner_visible_support_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L500) |
| function | `list_runtime_inner_visible_support_signals` | `(*, status=…, limit=…)` | List inner-visible-support signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L572) |
| function | `get_runtime_inner_visible_support_signal` | `(signal_id)` | Fetch a single inner-visible-support signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L622) |
| function | `update_runtime_inner_visible_support_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one inner-visible-support signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L662) |
| function | `supersede_runtime_inner_visible_support_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all open inner-visible-support signals for a focus as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L699) |
| function | `upsert_runtime_relation_state_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert a relation-state signal into runtime_relation_state_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L735) |
| function | `list_runtime_relation_state_signals` | `(*, status=…, limit=…)` | List relation-state signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L807) |
| function | `get_runtime_relation_state_signal` | `(signal_id)` | Fetch a single relation-state signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L857) |
| function | `update_runtime_relation_state_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one relation-state signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L895) |
| function | `supersede_runtime_relation_state_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all open relation-state signals for a focus as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L932) |
| function | `upsert_runtime_relation_continuity_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert a relation-continuity signal into runtime_relation_continuity_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L968) |
| function | `list_runtime_relation_continuity_signals` | `(*, status=…, limit=…)` | List relation-continuity signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1040) |
| function | `get_runtime_relation_continuity_signal` | `(signal_id)` | Fetch a single relation-continuity signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1090) |
| function | `update_runtime_relation_continuity_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one relation-continuity signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1128) |
| function | `supersede_runtime_relation_continuity_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all open relation-continuity signals for a focus as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1165) |
| function | `upsert_runtime_attachment_topology_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert an attachment-topology signal into runtime_attachment_topology_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1201) |
| function | `upsert_runtime_loyalty_gradient_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Upsert a loyalty-gradient signal into runtime_loyalty_gradient_signals. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1273) |
| function | `list_runtime_attachment_topology_signals` | `(*, status=…, limit=…)` | List attachment-topology signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1345) |
| function | `list_runtime_loyalty_gradient_signals` | `(*, status=…, limit=…)` | List loyalty-gradient signals, newest first, optionally filtered by status. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1395) |
| function | `get_runtime_attachment_topology_signal` | `(signal_id)` | Fetch a single attachment-topology signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1445) |
| function | `get_runtime_loyalty_gradient_signal` | `(signal_id)` | Fetch a single loyalty-gradient signal by signal_id, or None if not found. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1483) |
| function | `update_runtime_attachment_topology_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one attachment-topology signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1521) |
| function | `update_runtime_loyalty_gradient_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one loyalty-gradient signal by signal_id. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1558) |
| function | `supersede_runtime_attachment_topology_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all open attachment-topology signals for a domain as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1595) |
| function | `supersede_runtime_loyalty_gradient_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all open loyalty-gradient signals for a domain as 'superseded' except one. | [src](../../../core/runtime/db_runtime_relational_signals.py#L1631) |
| function | `_ensure_runtime_user_md_update_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1667) |
| function | `_ensure_runtime_user_understanding_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1709) |
| function | `_ensure_runtime_inner_visible_support_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1751) |
| function | `_ensure_runtime_relation_state_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1795) |
| function | `_ensure_runtime_relation_continuity_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1837) |
| function | `_ensure_runtime_attachment_topology_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1879) |
| function | `_ensure_runtime_loyalty_gradient_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1921) |
| function | `_runtime_user_understanding_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1963) |
| function | `_runtime_inner_visible_support_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L1988) |
| function | `_runtime_relation_state_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L2015) |
| function | `_runtime_relation_continuity_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L2040) |
| function | `_runtime_attachment_topology_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L2065) |
| function | `_runtime_loyalty_gradient_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L2090) |
| function | `_runtime_user_md_update_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_relational_signals.py#L2115) |

## `core/runtime/db_runtime_self.py`
_Persistence for Jarvis' runtime self-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_self_model_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime self-model signal into runtime_self_model_signals. | [src](../../../core/runtime/db_runtime_self.py#L32) |
| function | `list_runtime_self_model_signals` | `(*, status=…, limit=…)` | Return runtime self-model signals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_self.py#L255) |
| function | `get_runtime_self_model_signal` | `(signal_id)` | Return the runtime self-model signal for `signal_id` as a row dict, or None. | [src](../../../core/runtime/db_runtime_self.py#L304) |
| function | `update_runtime_self_model_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one self-model signal. | [src](../../../core/runtime/db_runtime_self.py#L341) |
| function | `supersede_runtime_self_model_signals` | `(*, signal_type, exclude_signal_id, updated_at, status_reason)` | Mark all active/uncertain/stale self-model signals of `signal_type` as superseded. | [src](../../../core/runtime/db_runtime_self.py#L377) |
| function | `upsert_runtime_self_authored_prompt_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a self-authored prompt proposal via the shared _upsert_signal. | [src](../../../core/runtime/db_runtime_self.py#L412) |
| function | `list_runtime_self_authored_prompt_proposals` | `(*, status=…, limit=…)` | Return self-authored prompt proposals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_self.py#L483) |
| function | `get_runtime_self_authored_prompt_proposal` | `(proposal_id)` | Return the self-authored prompt proposal for `proposal_id` as a row dict, or None. | [src](../../../core/runtime/db_runtime_self.py#L532) |
| function | `update_runtime_self_authored_prompt_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one self-authored prompt proposal. | [src](../../../core/runtime/db_runtime_self.py#L571) |
| function | `supersede_runtime_self_authored_prompt_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | Mark all live self-authored prompt proposals for a domain as superseded. | [src](../../../core/runtime/db_runtime_self.py#L607) |
| function | `upsert_runtime_self_narrative_continuity_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert or merge a self-narrative-continuity signal via the shared _upsert_signal. | [src](../../../core/runtime/db_runtime_self.py#L643) |
| function | `list_runtime_self_narrative_continuity_signals` | `(*, status=…, limit=…)` | Return self-narrative-continuity signals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_self.py#L714) |
| function | `get_runtime_self_narrative_continuity_signal` | `(signal_id)` | Return the self-narrative-continuity signal for `signal_id` as a row dict, or None. | [src](../../../core/runtime/db_runtime_self.py#L763) |
| function | `update_runtime_self_narrative_continuity_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one self-narrative-continuity signal. | [src](../../../core/runtime/db_runtime_self.py#L802) |
| function | `supersede_runtime_self_narrative_continuity_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all live self-narrative-continuity signals for a focus as superseded. | [src](../../../core/runtime/db_runtime_self.py#L838) |
| function | `upsert_runtime_selfhood_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime selfhood proposal via the shared _upsert_signal. | [src](../../../core/runtime/db_runtime_self.py#L874) |
| function | `list_runtime_selfhood_proposals` | `(*, status=…, limit=…)` | Return runtime selfhood proposals as row dicts, newest first. | [src](../../../core/runtime/db_runtime_self.py#L945) |
| function | `get_runtime_selfhood_proposal` | `(proposal_id)` | Return the runtime selfhood proposal for `proposal_id` as a row dict, or None. | [src](../../../core/runtime/db_runtime_self.py#L994) |
| function | `update_runtime_selfhood_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Update status/status_reason/updated_at for one runtime selfhood proposal. | [src](../../../core/runtime/db_runtime_self.py#L1031) |
| function | `supersede_runtime_selfhood_proposals_for_domain` | `(*, domain_key, exclude_proposal_id, updated_at, status_reason)` | Mark all live runtime selfhood proposals for a domain as superseded. | [src](../../../core/runtime/db_runtime_self.py#L1067) |
| function | `_ensure_runtime_self_model_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1103) |
| function | `_ensure_runtime_self_authored_prompt_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1144) |
| function | `_ensure_runtime_self_narrative_continuity_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1187) |
| function | `_ensure_runtime_selfhood_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_self.py#L1230) |
| function | `_runtime_self_narrative_continuity_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1271) |
| function | `_runtime_self_model_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1297) |
| function | `_runtime_self_authored_prompt_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1321) |
| function | `_runtime_selfhood_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_self.py#L1347) |

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
| function | `upsert_runtime_self_review_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime self-review signal into runtime_self_review_signals. | [src](../../../core/runtime/db_runtime_self_review.py#L347) |
| function | `list_runtime_self_review_signals` | `(*, status=…, limit=…)` | Return up to `limit` runtime self-review signals, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_self_review.py#L418) |
| function | `get_runtime_self_review_signal` | `(signal_id)` | Return the runtime self-review signal row dict for `signal_id`, or None if absent. | [src](../../../core/runtime/db_runtime_self_review.py#L467) |
| function | `update_runtime_self_review_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the signal `signal_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L504) |
| function | `supersede_runtime_self_review_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live signals in `domain_key` as 'superseded' except `exclude_signal_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L541) |
| function | `upsert_runtime_self_review_record` | `(*, record_id, record_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a runtime self-review record into runtime_self_review_records. | [src](../../../core/runtime/db_runtime_self_review.py#L576) |
| function | `list_runtime_self_review_records` | `(*, status=…, limit=…)` | Return up to `limit` runtime self-review records, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_self_review.py#L646) |
| function | `get_runtime_self_review_record` | `(record_id)` | Return the runtime self-review record row dict for `record_id`, or None if absent. | [src](../../../core/runtime/db_runtime_self_review.py#L695) |
| function | `update_runtime_self_review_record_status` | `(record_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the record `record_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L732) |
| function | `supersede_runtime_self_review_records_for_domain` | `(*, domain_key, exclude_record_id, updated_at, status_reason)` | Mark all still-live records in `domain_key` as 'superseded' except `exclude_record_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L769) |
| function | `upsert_runtime_self_review_run` | `(*, run_id, run_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, record_run_id=…, session_id=…)` | Insert or merge a runtime self-review run into runtime_self_review_runs. | [src](../../../core/runtime/db_runtime_self_review.py#L804) |
| function | `list_runtime_self_review_runs` | `(*, status=…, limit=…)` | Return up to `limit` runtime self-review runs, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_self_review.py#L874) |
| function | `get_runtime_self_review_run` | `(run_id)` | Return the runtime self-review run row dict for `run_id`, or None if absent. | [src](../../../core/runtime/db_runtime_self_review.py#L923) |
| function | `update_runtime_self_review_run_status` | `(run_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the run `run_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L960) |
| function | `supersede_runtime_self_review_runs_for_domain` | `(*, domain_key, exclude_run_id, updated_at, status_reason)` | Mark all still-live runs in `domain_key` as 'superseded' except `exclude_run_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L997) |
| function | `upsert_runtime_self_review_outcome` | `(*, outcome_id, outcome_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, review_run_id=…, session_id=…)` | Insert or merge a runtime self-review outcome into runtime_self_review_outcomes. | [src](../../../core/runtime/db_runtime_self_review.py#L1032) |
| function | `list_runtime_self_review_outcomes` | `(*, status=…, limit=…)` | Return up to `limit` runtime self-review outcomes, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_self_review.py#L1102) |
| function | `get_runtime_self_review_outcome` | `(outcome_id)` | Return the runtime self-review outcome row dict for `outcome_id`, or None if absent. | [src](../../../core/runtime/db_runtime_self_review.py#L1151) |
| function | `update_runtime_self_review_outcome_status` | `(outcome_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the outcome `outcome_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L1188) |
| function | `supersede_runtime_self_review_outcomes_for_domain` | `(*, domain_key, exclude_outcome_id, updated_at, status_reason)` | Mark all still-live outcomes in `domain_key` as 'superseded' except `exclude_outcome_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L1225) |
| function | `upsert_runtime_self_review_cadence_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert or merge a cadence signal into runtime_self_review_cadence_signals. | [src](../../../core/runtime/db_runtime_self_review.py#L1260) |
| function | `list_runtime_self_review_cadence_signals` | `(*, status=…, limit=…)` | Return up to `limit` cadence signals, newest first (ORDER BY id DESC). | [src](../../../core/runtime/db_runtime_self_review.py#L1330) |
| function | `get_runtime_self_review_cadence_signal` | `(signal_id)` | Return the cadence-signal row dict for `signal_id`, or None if absent. | [src](../../../core/runtime/db_runtime_self_review.py#L1379) |
| function | `update_runtime_self_review_cadence_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the cadence signal `signal_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L1416) |
| function | `supersede_runtime_self_review_cadence_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live cadence signals in `domain_key` as 'superseded' except `exclude_signal_id`. | [src](../../../core/runtime/db_runtime_self_review.py#L1453) |

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
| function | `_omdoeb_run_id_til_origin_ref` | `(conn)` | Kolonnen hed `run_id` og indeholdt ikke et run. | [src](../../../core/runtime/db_runtime_tasks.py#L13) |
| function | `ensure_runtime_tasks_tables` | `(conn)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L41) |
| function | `_runtime_task_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L81) |
| function | `create_runtime_task` | `(*, task_id, kind, origin, status, goal, scope=…, priority=…, flow_id=…, session_id=…, origin_ref=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L103) |
| function | `get_runtime_task` | `(task_id)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L174) |
| function | `list_runtime_tasks` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L207) |
| function | `update_runtime_task` | `(task_id, *, status=…, flow_id=…, session_id=…, origin_ref=…, owner=…, retry_at=…, blocked_reason=…, result_summary=…, artifact_ref=…, updated_at)` | — | [src](../../../core/runtime/db_runtime_tasks.py#L253) |

## `core/runtime/db_runtime_temporal_memory_signals.py`
_Persistence for Jarvis' runtime temporal/memory-* signal cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_runtime_temporal_recurrence_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert-or-merge a temporal-recurrence signal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L35) |
| function | `list_runtime_temporal_recurrence_signals` | `(*, status=…, limit=…)` | Return temporal-recurrence signals as row dicts, newest first, optionally | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L106) |
| function | `get_runtime_temporal_recurrence_signal` | `(signal_id)` | Return the temporal-recurrence signal with this signal_id as a row dict, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L153) |
| function | `update_runtime_temporal_recurrence_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the temporal-recurrence signal | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L191) |
| function | `supersede_runtime_temporal_recurrence_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/softening/stale) temporal-recurrence signals | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L226) |
| function | `_ensure_runtime_temporal_recurrence_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L260) |
| function | `_runtime_temporal_recurrence_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L301) |
| function | `upsert_runtime_remembered_fact_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert-or-merge a remembered-fact signal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L325) |
| function | `list_runtime_remembered_fact_signals` | `(*, status=…, limit=…)` | Return remembered-fact signals as row dicts, newest first, optionally | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L396) |
| function | `get_runtime_remembered_fact_signal` | `(signal_id)` | Return the remembered-fact signal with this signal_id as a row dict, or | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L443) |
| function | `update_runtime_remembered_fact_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the remembered-fact signal with | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L481) |
| function | `supersede_runtime_remembered_fact_signals_for_dimension` | `(*, dimension_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/softening/stale) remembered-fact signals | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L516) |
| function | `_ensure_runtime_remembered_fact_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L550) |
| function | `_runtime_remembered_fact_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L591) |
| function | `upsert_runtime_memory_md_update_proposal` | `(*, proposal_id, proposal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, support_count, session_count, created_at, updated_at, status_reason=…, run_id=…, session_id=…)` | Insert-or-merge a MEMORY.md-update proposal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L615) |
| function | `list_runtime_memory_md_update_proposals` | `(*, status=…, limit=…)` | Return MEMORY.md-update proposals as row dicts, newest first, optionally | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L686) |
| function | `get_runtime_memory_md_update_proposal` | `(proposal_id)` | Return the MEMORY.md-update proposal with this proposal_id as a row dict, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L733) |
| function | `update_runtime_memory_md_update_proposal_status` | `(proposal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the MEMORY.md-update proposal with | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L771) |
| function | `supersede_runtime_memory_md_update_proposals_for_dimension` | `(*, dimension_key, exclude_proposal_id, updated_at, status_reason)` | Mark all still-live (fresh/active/fading/stale) MEMORY.md-update | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L806) |
| function | `_ensure_runtime_memory_md_update_proposal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L840) |
| function | `_runtime_memory_md_update_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L881) |
| function | `upsert_runtime_release_marker_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert-or-merge a release-marker signal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L905) |
| function | `list_runtime_release_marker_signals` | `(*, status=…, limit=…)` | Return release-marker signals as row dicts, newest first, optionally | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L976) |
| function | `get_runtime_release_marker_signal` | `(signal_id)` | Return the release-marker signal with this signal_id as a row dict, or | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1023) |
| function | `update_runtime_release_marker_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the release-marker signal with | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1061) |
| function | `supersede_runtime_release_marker_signals_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/softening/stale) release-marker signals whose | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1096) |
| function | `_ensure_runtime_release_marker_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1130) |
| function | `_runtime_release_marker_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1171) |
| function | `upsert_runtime_selective_forgetting_candidate` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert-or-merge a selective-forgetting candidate into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1195) |
| function | `list_runtime_selective_forgetting_candidates` | `(*, status=…, limit=…)` | Return selective-forgetting candidates as row dicts, newest first, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1266) |
| function | `get_runtime_selective_forgetting_candidate` | `(signal_id)` | Return the selective-forgetting candidate with this signal_id as a row | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1314) |
| function | `update_runtime_selective_forgetting_candidate_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the selective-forgetting candidate | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1354) |
| function | `supersede_runtime_selective_forgetting_candidates_for_domain` | `(*, domain_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/softening/stale) selective-forgetting | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1389) |
| function | `_ensure_runtime_selective_forgetting_candidate_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1423) |
| function | `_runtime_selective_forgetting_candidate_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1466) |
| function | `upsert_runtime_regulation_homeostasis_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert-or-merge a regulation/homeostasis signal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1492) |
| function | `list_runtime_regulation_homeostasis_signals` | `(*, status=…, limit=…)` | Return regulation/homeostasis signals as row dicts, newest first, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1563) |
| function | `get_runtime_regulation_homeostasis_signal` | `(signal_id)` | Return the regulation/homeostasis signal with this signal_id as a row | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1611) |
| function | `update_runtime_regulation_homeostasis_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the regulation/homeostasis signal | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1651) |
| function | `supersede_runtime_regulation_homeostasis_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/stale) regulation/homeostasis signals whose | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1686) |
| function | `_ensure_runtime_regulation_homeostasis_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1720) |
| function | `_runtime_regulation_homeostasis_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1763) |
| function | `upsert_runtime_temperament_tendency_signal` | `(*, signal_id, signal_type, canonical_key, status, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, created_at, updated_at)` | Insert-or-merge a temperament-tendency signal into | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1789) |
| function | `list_runtime_temperament_tendency_signals` | `(*, status=…, limit=…)` | Return temperament-tendency signals as row dicts, newest first, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1860) |
| function | `get_runtime_temperament_tendency_signal` | `(signal_id)` | Return the temperament-tendency signal with this signal_id as a row dict, | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1908) |
| function | `update_runtime_temperament_tendency_signal_status` | `(signal_id, *, status, updated_at, status_reason=…)` | Set status/status_reason/updated_at on the temperament-tendency signal | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1946) |
| function | `supersede_runtime_temperament_tendency_signals_for_focus` | `(*, focus_key, exclude_signal_id, updated_at, status_reason)` | Mark all still-live (active/softening/stale) temperament-tendency signals | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L1981) |
| function | `_ensure_runtime_temperament_tendency_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L2015) |
| function | `_runtime_temperament_tendency_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_runtime_temporal_memory_signals.py#L2056) |

