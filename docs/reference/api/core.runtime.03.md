# `core.runtime.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `list_scheduled_tasks` | `(limit=…, status=…)` | List scheduled tasks — nyeste ``run_at`` først. | [src](../../../core/runtime/db_scheduled_tasks.py#L169) |
| function | `count_scheduled_tasks` | `(status=…)` | Count scheduled tasks, optionally filtered by status. Observability helper. | [src](../../../core/runtime/db_scheduled_tasks.py#L205) |

## `core/runtime/db_schema.py`
_Schema layer for core.runtime.db — init_db + all _ensure_*/_migrate_* helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_multiuser_columns` | `(conn)` | Additive: tag scheduling tables with scheduled_for_user_id + | [src](../../../core/runtime/db_schema.py#L90) |
| function | `_ensure_user_scope_154` | `(conn)` | Additivt: tilføj user_id-kolonne + BACKFILL eksisterende NULL-rækker til | [src](../../../core/runtime/db_schema.py#L144) |
| function | `_ensure_skill_audit_table` | `(conn)` | Create skill_audit_log table for skills versionering (C1). | [src](../../../core/runtime/db_schema.py#L175) |
| function | `_ensure_skill_usage_table` | `(conn)` | Create skill_usage_stats table for auto-learning (C4). | [src](../../../core/runtime/db_schema.py#L198) |
| function | `_ensure_chat_session_workspace_columns` | `(conn)` | Tilføj nullable workspace-kolonner til chat_sessions (Code-mode binding). | [src](../../../core/runtime/db_schema.py#L228) |
| function | `_ensure_notification_tables` | `(conn)` | Unified notification routing (spec 2026-06-20 §3.1): per-bruger-præferencer | [src](../../../core/runtime/db_schema.py#L238) |
| function | `_ensure_security_guard_tables` | `(conn)` | Identity-verification-guard & abuse-monitoring (spec 2026-06-21). Idempotent. | [src](../../../core/runtime/db_schema.py#L301) |
| function | `init_db` | `()` | — | [src](../../../core/runtime/db_schema.py#L348) |
| function | `_ensure_decision_trigger_column` | `(conn)` | Add behavioral_decisions.trigger_name column and wire known decisions. | [src](../../../core/runtime/db_schema.py#L978) |
| function | `_ensure_chat_messages_reasoning_column` | `(conn)` | Add chat_messages.reasoning_content column. Idempotent. | [src](../../../core/runtime/db_schema.py#L1012) |
| function | `_ensure_chat_messages_content_json_column` | `(conn)` | Add chat_messages.content_json column. Idempotent. | [src](../../../core/runtime/db_schema.py#L1038) |
| function | `_ensure_chat_messages_encrypted_column` | `(conn)` | Tilføj `chat_messages.encrypted`. Idempotent. (Spec §16.2, task 3.3.) | [src](../../../core/runtime/db_schema.py#L1051) |
| function | `_ensure_causal_edges_table` | `(conn)` | Create causal_edges table for the causal graph layer. | [src](../../../core/runtime/db_schema.py#L1072) |
| function | `_ensure_tool_router_tables` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1109) |
| function | `_ensure_counterfactuals_table` | `(conn)` | Create counterfactuals table with UNIQUE(cf_key) constraint. | [src](../../../core/runtime/db_schema.py#L1149) |
| function | `_ensure_absence_traces_table` | `(conn)` | Create absence_traces table for Lag 11 forgetting (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1187) |
| function | `_ensure_reasoning_conclusions_table` | `(conn)` | Create reasoning_conclusions table for Phase 1 Generalized Learning. | [src](../../../core/runtime/db_schema.py#L1225) |
| function | `_ensure_soft_deleted_at_columns` | `(conn)` | Add soft_deleted_at column to episodic tables (Lag 11 Phase 1). | [src](../../../core/runtime/db_schema.py#L1259) |
| function | `_ensure_dream_bias_active_table` | `(conn)` | Create dream_bias_active table for Lag 2 dream-bias (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1292) |
| function | `_ensure_user_temperature_active_table` | `(conn)` | Create user_temperature_active table for Lag 10 (added 2026-05-10). | [src](../../../core/runtime/db_schema.py#L1332) |
| function | `_ensure_experience_episodes_table` | `(conn)` | Append-only log of (context, tool_choice, outcome) episodes. | [src](../../../core/runtime/db_schema.py#L1388) |
| function | `_ensure_tool_intent_approval_request_columns` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1444) |
| function | `_ensure_runtime_webchat_execution_pilot_table` | `(conn)` | — | [src](../../../core/runtime/db_schema.py#L1502) |
| function | `_migrate_chronicle_table_add_affective_signature` | `()` | Add affective_signature column to existing tables missing it. | [src](../../../core/runtime/db_schema.py#L1544) |

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

## `core/runtime/db_session_ledger.py`
_Append-only session-ledger — Fase 1 af DeepSeek-harness-spec'en._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/db_session_ledger.py#L60) |
| function | `_iso` | `(dt)` | — | [src](../../../core/runtime/db_session_ledger.py#L64) |
| function | `_ensure_session_ledger_table` | `(conn)` | — | [src](../../../core/runtime/db_session_ledger.py#L68) |
| function | `acquire_write_lease` | `(session_id, *, owner, ttl_s=…, now=…)` | Tag skrive-ejerskabet over én session. Returnér møntet, eller None. | [src](../../../core/runtime/db_session_ledger.py#L103) |
| function | `release_write_lease` | `(session_id, *, owner, token)` | Giv ejerskabet fra sig. Kun den nuværende ejer med den rigtige mønt kan. | [src](../../../core/runtime/db_session_ledger.py#L145) |
| function | `lease_state` | `(session_id)` | Diagnostik: hvem ejer sessionen, med hvilken mønt, hvor længe. | [src](../../../core/runtime/db_session_ledger.py#L160) |
| class | `LeaseLost` | `` | Skrivningen blev afvist: leasen er væk eller møntet er forældet. | [src](../../../core/runtime/db_session_ledger.py#L179) |
| function | `append_session_events` | `(session_id, *, owner, token, events, now=…)` | Tilføj hændelser ATOMISK og IDEMPOTENT. | [src](../../../core/runtime/db_session_ledger.py#L183) |
| function | `_annoncer` | `(session_id, skrevet, seq)` | Fortæl bussen at der er kommet hændelser — EFTER commit, og aldrig fatalt. | [src](../../../core/runtime/db_session_ledger.py#L256) |
| function | `append_unowned` | `(session_id, *, events, now=…)` | Tilføj hændelser i ÉN transaktion, uden lease. Kun for skygge-sessioner. | [src](../../../core/runtime/db_session_ledger.py#L280) |
| function | `read_session_events` | `(session_id, *, from_seq=…, to_seq=…)` | Læs hændelser i rækkefølge. Halvåbent interval: (from_seq, to_seq]. | [src](../../../core/runtime/db_session_ledger.py#L369) |
| function | `current_seq` | `(session_id)` | Sessionens højeste sekvensnummer — 0 hvis ledgeren er tom for den. | [src](../../../core/runtime/db_session_ledger.py#L403) |
| function | `_parse` | `(value)` | — | [src](../../../core/runtime/db_session_ledger.py#L414) |
| function | `_ensure_storage_mode_column` | `(conn)` | — | [src](../../../core/runtime/db_session_ledger.py#L440) |
| function | `storage_mode` | `(session_id, *, conn=…)` | Hvilken kilde er kanonisk for denne session? | [src](../../../core/runtime/db_session_ledger.py#L449) |
| function | `_storage_mode_on` | `(conn, session_id)` | — | [src](../../../core/runtime/db_session_ledger.py#L470) |
| function | `advance_storage_mode` | `(session_id, *, to)` | Ryk EN session fremad. Envejs — der er ingen vej tilbage. | [src](../../../core/runtime/db_session_ledger.py#L482) |
| function | `abandon_shadow` | `(session_id)` | Sluk skyggen igen: `shadow` → `legacy`. Aldrig fra `ledger`. | [src](../../../core/runtime/db_session_ledger.py#L509) |

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

## `core/runtime/db_view_requests.py`
_Visnings-forespørgsler: Jarvis spørger desk, desk SVARER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_laes` | `()` | — | [src](../../../core/runtime/db_view_requests.py#L36) |
| function | `_gem` | `(tilstand)` | — | [src](../../../core/runtime/db_view_requests.py#L44) |
| function | `opret` | `(op, args, *, session_id)` | — | [src](../../../core/runtime/db_view_requests.py#L48) |
| function | `ventende` | `()` | Ubesvarede, ikke-forældede forespørgsler. | [src](../../../core/runtime/db_view_requests.py#L66) |
| function | `hent` | `(request_id)` | — | [src](../../../core/runtime/db_view_requests.py#L73) |
| function | `svar` | `(request_id, resultat)` | Desk svarer. Kun én gang: et andet vindue må ikke overskrive svaret. | [src](../../../core/runtime/db_view_requests.py#L80) |
| function | `vent_paa_svar` | `(request_id, *, frist_s, interval_s=…)` | — | [src](../../../core/runtime/db_view_requests.py#L94) |

## `core/runtime/db_visible.py`
_Persistence for the visible-lane projection tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_visible_tables` | `(conn)` | — | [src](../../../core/runtime/db_visible.py#L16) |
| function | `_run_user_scope` | `(user_id, include_unassigned)` | WHERE-fragment + parametre for bruger-scoping af runs. | [src](../../../core/runtime/db_visible.py#L90) |
| function | `recent_visible_runs` | `(limit=…, *, user_id=…, include_unassigned=…, include_running=…)` | De seneste runs. UDEN `user_id` er der intet filter. | [src](../../../core/runtime/db_visible.py#L110) |
| function | `recent_visible_work_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_visible.py#L172) |
| function | `recent_visible_work_units` | `(limit=…)` | — | [src](../../../core/runtime/db_visible.py#L216) |
| function | `record_visible_work_note` | `(*, note_id, work_id, run_id, status, lane, provider, model, user_message_preview=…, capability_id=…, work_preview=…, projection_source=…, created_at, finished_at)` | — | [src](../../../core/runtime/db_visible.py#L256) |
| function | `visible_session_continuity` | `()` | — | [src](../../../core/runtime/db_visible.py#L370) |

## `core/runtime/db_world_self_truth.py`
_Persistence for conversation topics and evidence-bounded world facts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_conversation_topic` | `(*, topic_id, canonical_key, title, summary, source_kind, session_id, run_id, created_at, updated_at)` | — | [src](../../../core/runtime/db_world_self_truth.py#L14) |
| function | `select_conversation_topics` | `(*, limit=…)` | — | [src](../../../core/runtime/db_world_self_truth.py#L109) |
| function | `insert_world_fact` | `(*, fact_id, canonical_key, statement, status, confidence, source_kind, source_ref, observed_at, valid_from, valid_until, contradicts_fact_id, supersedes_fact_id, evidence_count, distinct_source_count, created_at, updated_at)` | — | [src](../../../core/runtime/db_world_self_truth.py#L126) |
| function | `select_world_facts` | `(*, statuses=…, limit=…)` | — | [src](../../../core/runtime/db_world_self_truth.py#L185) |
| function | `list_legacy_world_model_signals_excluding_topics` | `(*, status=…, limit=…)` | Read the old signal store without allowing conversation topics through. | [src](../../../core/runtime/db_world_self_truth.py#L223) |
| function | `quarantine_legacy_world_topics` | `(batch_size=…)` | Quarantine at most ``batch_size`` old conversation-topic signal rows. | [src](../../../core/runtime/db_world_self_truth.py#L255) |
| function | `_ensure_conversation_topic_evidence_table` | `(conn)` | Én raekke pr. (emne, koersel). Primaernoeglen ER afvisningen af dubletter: | [src](../../../core/runtime/db_world_self_truth.py#L349) |
| function | `_ensure_conversation_topics_table` | `(conn)` | — | [src](../../../core/runtime/db_world_self_truth.py#L366) |
| function | `_ensure_runtime_world_facts_table` | `(conn)` | — | [src](../../../core/runtime/db_world_self_truth.py#L386) |
| function | `_ensure_world_self_truth_migrations_table` | `(conn)` | — | [src](../../../core/runtime/db_world_self_truth.py#L423) |
| function | `_table_exists` | `(conn, table_name)` | — | [src](../../../core/runtime/db_world_self_truth.py#L436) |
| function | `_sqlite_now` | `(conn)` | — | [src](../../../core/runtime/db_world_self_truth.py#L443) |
| function | `_conversation_topic_from_row` | `(row)` | — | [src](../../../core/runtime/db_world_self_truth.py#L447) |
| function | `_world_fact_from_row` | `(row)` | — | [src](../../../core/runtime/db_world_self_truth.py#L470) |
| function | `_legacy_world_signal_from_row` | `(row)` | — | [src](../../../core/runtime/db_world_self_truth.py#L477) |

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
| class | `_UlaeseligConfig` | `` | runtime.json FINDES, men kunne ikke læses som et settings-dokument. | [src](../../../core/runtime/jarvisx_auth.py#L64) |
| function | `_load_settings` | `()` | Læs runtime.json. | [src](../../../core/runtime/jarvisx_auth.py#L74) |
| function | `_save_settings` | `(data)` | — | [src](../../../core/runtime/jarvisx_auth.py#L94) |
| function | `_read_secret` | `()` | Read the auth secret, generating one on first use. | [src](../../../core/runtime/jarvisx_auth.py#L101) |
| function | `issue_token` | `(*, user_id, role=…, ttl_days=…, ttl_seconds=…, app_id=…, extra_claims=…)` | Mint a signed bearer token for a user. | [src](../../../core/runtime/jarvisx_auth.py#L151) |
| function | `verify_token` | `(token)` | Verify signature + expiry, return the parsed claims. | [src](../../../core/runtime/jarvisx_auth.py#L210) |
| function | `session_needs_override` | `(claims, *, owner_app_id, session_id, now=…)` | True hvis owner-autoritet i denne session KRÆVER en TOTP-override (§6.1). | [src](../../../core/runtime/jarvisx_auth.py#L277) |
| function | `auth_required` | `()` | Should the API reject requests without a valid bearer token? | [src](../../../core/runtime/jarvisx_auth.py#L307) |
| function | `require_owner` | `(request)` | Raise 401/403 unless the caller carries an owner bearer token. | [src](../../../core/runtime/jarvisx_auth.py#L348) |
| function | `require_household` | `(request)` | Raise 401/403 unless the caller lives in the household (owner|partner). | [src](../../../core/runtime/jarvisx_auth.py#L381) |

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

## `core/runtime/opmaerksomhed.py`
_Tilstands-hjernen — ÉN samlet opmærksomhedstilstand pr. arbejdsrum._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_standard_rum` | `()` | — | [src](../../../core/runtime/opmaerksomhed.py#L75) |
| function | `rum_for_session` | `(session_id)` | Samtalens arbejdsrum. Ustemplede (legacy) samtaler hører til | [src](../../../core/runtime/opmaerksomhed.py#L80) |
| function | `_noegle` | `(rum)` | — | [src](../../../core/runtime/opmaerksomhed.py#L99) |
| function | `_laes` | `(rum)` | — | [src](../../../core/runtime/opmaerksomhed.py#L103) |
| function | `_skriv` | `(rum, punkter)` | — | [src](../../../core/runtime/opmaerksomhed.py#L113) |
| function | `_friske` | `(punkter, nu)` | — | [src](../../../core/runtime/opmaerksomhed.py#L118) |
| function | `_titel` | `(session_id)` | — | [src](../../../core/runtime/opmaerksomhed.py#L124) |
| function | `_noter` | `(*, session_id, run_id, tilstand, tekst=…)` | — | [src](../../../core/runtime/opmaerksomhed.py#L133) |
| function | `_vurder_afsluttet` | `(log_run_id, indre_run_id, session_id)` | — | [src](../../../core/runtime/opmaerksomhed.py#L145) |
| function | `noter_afsluttet` | `(log_run_id, indre_run_id, session_id)` | Kaldes fra detached_run når en tur slutter. Vurderes efter samme grace | [src](../../../core/runtime/opmaerksomhed.py#L171) |
| function | `set` | `(session_id, rum=…)` | Brugeren har åbnet samtalen — dens punkt forsvinder. | [src](../../../core/runtime/opmaerksomhed.py#L184) |
| function | `glem_session` | `(session_id)` | En ny tur starter — den forrige turs udfald er ikke længere nyheden. | [src](../../../core/runtime/opmaerksomhed.py#L199) |
| function | `_pynt_navn` | `(navn)` | — | [src](../../../core/runtime/opmaerksomhed.py#L209) |
| function | `aktivitet` | `(frames)` | Hvad laver han LIGE NU — læst bagfra i runnets egen strøm. | [src](../../../core/runtime/opmaerksomhed.py#L217) |
| function | `_koerende` | `(rum)` | — | [src](../../../core/runtime/opmaerksomhed.py#L264) |
| function | `_baggrund` | `()` | Autonome kørsler i gang (sidste halve time — friskheds-vagt mod zombier). | [src](../../../core/runtime/opmaerksomhed.py#L282) |
| function | `_koe` | `(user_id, is_owner)` | (blokerende punkter, antal i indbakken). | [src](../../../core/runtime/opmaerksomhed.py#L299) |
| function | `_venter` | `(items)` | — | [src](../../../core/runtime/opmaerksomhed.py#L311) |
| function | `tilstand_for` | `(*, rum=…, user_id=…, is_owner=…)` | Den samlede tilstand. Rækkefølge: prioritet, så nyeste først. | [src](../../../core/runtime/opmaerksomhed.py#L321) |

## `core/runtime/plugin_graph.py`
_Afhængighedsgrafen — Fase 9: «plugin boot rejects missing/cyclic dependencies»._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GrafFejl` | `` | Grafen kan ikke bære arbejde. Rejses kun i streng tilstand. | [src](../../../core/runtime/plugin_graph.py#L48) |
| class | `Rapport` | `` | Hvad grafen fejler — og hvad den kan, hvis noget. | [src](../../../core/runtime/plugin_graph.py#L53) |
| method | `Rapport.rask` | `(self)` | — | [src](../../../core/runtime/plugin_graph.py#L66) |
| method | `Rapport.forklar` | `(self)` | Menneskelæsbart. Hver linje skal kunne handles på uden opslag. | [src](../../../core/runtime/plugin_graph.py#L69) |
| function | `valider` | `(graf, *, streng=…)` | Find manglende udbydere og cykler, og læg knuderne i en gyldig orden. | [src](../../../core/runtime/plugin_graph.py#L79) |
| function | `_find_cykler` | `(knuder)` | Dybde-først med tre farver. Hver fundet cyklus returneres som sin sti. | [src](../../../core/runtime/plugin_graph.py#L115) |
| function | `_toposorter` | `(knuder)` | Kahn. Afhængigheder først, og navne-sorteret inden for hvert lag. | [src](../../../core/runtime/plugin_graph.py#L155) |

## `core/runtime/plugin_lifecycle.py`
_Ejerskab over registreringer — Fase 9, `RuntimePluginLifecycle`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Post` | `` | Én registrering og vejen tilbage. | [src](../../../core/runtime/plugin_lifecycle.py#L82) |
| class | `Rapport` | `` | Hvad en afhændelse efterlod. Det er den her der gør nedlukningen ærlig. | [src](../../../core/runtime/plugin_lifecycle.py#L96) |
| method | `Rapport.ren` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L111) |
| method | `Rapport.forklar` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L114) |
| class | `Omfang` | `` | Ejer af et sæt registreringer. Alt lagt heri forsvinder sammen. | [src](../../../core/runtime/plugin_lifecycle.py#L124) |
| method | `Omfang.__init__` | `(self, navn)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L127) |
| method | `Omfang.registrer` | `(self, navn, afhaend)` | Læg en post i omfanget. Returnerer dens EGEN afhændelses-vej. | [src](../../../core/runtime/plugin_lifecycle.py#L136) |
| method | `Omfang._afhaend_en` | `(self, post)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L161) |
| method | `Omfang.arbejde_startet` | `(self)` | Meld at omfanget har arbejde i gang. Afhændelsen venter på det. | [src](../../../core/runtime/plugin_lifecycle.py#L180) |
| method | `Omfang.arbejde_slut` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L185) |
| method | `Omfang.arbejde_i_gang` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L192) |
| method | `Omfang.antal` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L197) |
| method | `Omfang.tom` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L202) |
| method | `Omfang.afhaend` | `(self, frist_s=…)` | Stop tilgang, tøm til fristen, afregistrér i modsat orden. | [src](../../../core/runtime/plugin_lifecycle.py#L207) |
| class | `Registret` | `` | De levende omfang. Tomme lag ryddes, så registret ikke samler lig. | [src](../../../core/runtime/plugin_lifecycle.py#L284) |
| method | `Registret.__init__` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L287) |
| method | `Registret.aabn` | `(self, navn)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L291) |
| method | `Registret.afhaend` | `(self, navn, frist_s=…)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L299) |
| method | `Registret.afhaend_alle` | `(self, frist_s=…)` | Luk alt. Nyeste omfang først — samme modsatte orden som inden i ét. | [src](../../../core/runtime/plugin_lifecycle.py#L312) |
| method | `Registret.ryd_tomme` | `(self)` | Fjern omfang uden poster. Returnerer antallet der blev ryddet. | [src](../../../core/runtime/plugin_lifecycle.py#L318) |
| method | `Registret.navne` | `(self)` | — | [src](../../../core/runtime/plugin_lifecycle.py#L327) |
| method | `Registret.status` | `(self)` | Hvad Centralen skal kunne vise. | [src](../../../core/runtime/plugin_lifecycle.py#L331) |
| function | `koer_nedlukning` | `(trin, *, navn=…)` | Kør en håndholdt nedluknings-liste i DEN GIVNE orden, og rapportér. | [src](../../../core/runtime/plugin_lifecycle.py#L345) |

## `core/runtime/process_lifecycle.py`
_Lukker processen ned? Ét sted der ejer svaret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `markér_nedlukning` | `(grund=…)` | Sig at processen er på vej ned. Idempotent. | [src](../../../core/runtime/process_lifecycle.py#L46) |
| function | `lukker_ned` | `()` | Er processen på vej ned? Spørg ved en naturlig grænse, ikke midt i noget. | [src](../../../core/runtime/process_lifecycle.py#L57) |
| function | `grund` | `()` | — | [src](../../../core/runtime/process_lifecycle.py#L63) |
| function | `installer_signalvagt` | `()` | Sæt flaget når SIGNALET ankommer — ikke når lifespan når sin shutdown. | [src](../../../core/runtime/process_lifecycle.py#L68) |
| function | `nulstil_til_test` | `()` | Kun til tests — en proces vender ikke tilbage fra nedlukning. | [src](../../../core/runtime/process_lifecycle.py#L115) |

## `core/runtime/profile_composer.py`
_Profil-komponisten — Fase 9 i DeepSeek-harness-spec'en._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EffektivProfil` | `` | Resultatet af en komposition — og det en kørsel gemmer om sig selv. | [src](../../../core/runtime/profile_composer.py#L66) |
| method | `EffektivProfil.hash` | `(self)` | Hash over det EFFEKTIVE resultat, ikke over navnet. | [src](../../../core/runtime/profile_composer.py#L75) |
| method | `EffektivProfil.forklar` | `(self)` | Hvad Mission Control skal kunne vise. Exit-kriteriet kræver at | [src](../../../core/runtime/profile_composer.py#L87) |
| method | `EffektivProfil.haandhaevelse` | `(self)` | Maalt virkelighed for de tre akser i kriterium 7. | [src](../../../core/runtime/profile_composer.py#L108) |
| method | `EffektivProfil.afvigelser` | `(self)` | Hvor holder virkeligheden ikke hvad profilen lover? | [src](../../../core/runtime/profile_composer.py#L121) |
| function | `_er_indsnaevring` | `(akse, fra, til)` | Bevæger `til` sig væk fra «mest tilladt» i forhold til `fra`? | [src](../../../core/runtime/profile_composer.py#L139) |
| function | `komponer` | `(lag, *, navn=…)` | Sæt lagene sammen i rækkefølge. Senere lag vinder — undtagen sikkerhed, | [src](../../../core/runtime/profile_composer.py#L154) |

## `core/runtime/profile_enforcement.py`
_ANMODET vs FAKTISK — Fase 9, exit-kriterium 7._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Skygge` | `` | Håndhæveren findes, men er slået fra. Hverken «mangler» eller «fejlet». | [src](../../../core/runtime/profile_enforcement.py#L52) |
| function | `_maal_sandkasse` | `()` | Sandkassen har en ægte håndhæver — samme kilde som exec-stien. | [src](../../../core/runtime/profile_enforcement.py#L65) |
| function | `_maal_kryds_session` | `()` | Findes der en gate på kontekst fra andre sessioner? | [src](../../../core/runtime/profile_enforcement.py#L94) |
| function | `_maal_telemetri` | `()` | Findes der en gate på udgående telemetri? | [src](../../../core/runtime/profile_enforcement.py#L111) |
| function | `maal` | `(anmodet=…)` | Anmodet vs faktisk for hver af de tre akser. | [src](../../../core/runtime/profile_enforcement.py#L132) |
| function | `afvigelser` | `(maalt)` | Hvor holder virkeligheden ikke hvad profilen lover? | [src](../../../core/runtime/profile_enforcement.py#L170) |

## `core/runtime/profiles.py`
_De navngivne profiler — Fase 9 i DeepSeek-harness-spec'en._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `byg` | `(navn, *, overstyring=…)` | Den effektive profil for `navn`, eventuelt med en kørselsspecifik | [src](../../../core/runtime/profiles.py#L105) |
| function | `kendte` | `()` | — | [src](../../../core/runtime/profiles.py#L122) |

## `core/runtime/provider_router.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_provider_router_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L21) |
| function | `configure_provider_router_entry` | `(*, provider, model, auth_mode, auth_profile, base_url, api_key, lane, set_visible)` | — | [src](../../../core/runtime/provider_router.py#L33) |
| function | `provider_router_summary` | `()` | — | [src](../../../core/runtime/provider_router.py#L128) |
| function | `main_agent_target` | `()` | — | [src](../../../core/runtime/provider_router.py#L165) |
| function | `main_agent_selection` | `()` | — | [src](../../../core/runtime/provider_router.py#L186) |
| function | `select_main_agent_target` | `(*, provider, model, auth_profile=…)` | — | [src](../../../core/runtime/provider_router.py#L203) |
| function | `resolve_provider_router_target` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L265) |
| function | `provider_router_lane_targets` | `()` | — | [src](../../../core/runtime/provider_router.py#L331) |
| function | `list_provider_router_targets` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L336) |
| function | `_provider_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L371) |
| function | `_model_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L389) |
| function | `_latest_model_for_lane` | `(*, registry, lane)` | — | [src](../../../core/runtime/provider_router.py#L399) |
| function | `_configured_main_agent_targets` | `(*, registry)` | — | [src](../../../core/runtime/provider_router.py#L416) |
| function | `_configured_target_match` | `(*, registry, provider, model)` | — | [src](../../../core/runtime/provider_router.py#L458) |
| function | `_readiness_hint` | `(*, provider, auth_mode, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L470) |
| function | `_provider_entry` | `(*, registry, provider)` | — | [src](../../../core/runtime/provider_router.py#L483) |
| function | `_provider_auth_mode` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L494) |
| function | `_provider_base_url` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L501) |
| function | `_credentials_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L508) |
| function | `_upsert_provider` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L525) |
| function | `_upsert_model` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L534) |
| function | `_default_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L547) |
| function | `_normalize_simple_id` | `(value, *, label)` | — | [src](../../../core/runtime/provider_router.py#L554) |
| function | `_normalize_auth_mode` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L561) |
| function | `_ollama_model_exists` | `(*, registry, model)` | Er *model* tilgængelig i den kørende Ollama? | [src](../../../core/runtime/provider_router.py#L568) |
| function | `_normalize_profile` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L590) |
| function | `_normalize_lane` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L597) |
| function | `_now` | `()` | — | [src](../../../core/runtime/provider_router.py#L604) |

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

## `core/runtime/run_profile.py`
_Hvilken profil koerer en given koersel under — Fase 9._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `profil_navn_for` | `(run, *, research=…)` | Profilnavnet for en koersel. Falder altid ud i noget kendt. | [src](../../../core/runtime/run_profile.py#L30) |
| function | `_synlig_profil` | `(run)` | Ejeren eller et husstandsmedlem? | [src](../../../core/runtime/run_profile.py#L45) |
| function | `profil_for` | `(run, *, research=…, overstyring=…)` | Den effektive profil for en koersel — klar til at gemmes paa raekken. | [src](../../../core/runtime/run_profile.py#L83) |

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
| class | `MailConfig` | `` | — | [src](../../../core/runtime/secrets.py#L18) |
| function | `_backup_file` | `()` | — | [src](../../../core/runtime/secrets.py#L27) |
| function | `_missing_key_message` | `(key)` | — | [src](../../../core/runtime/secrets.py#L31) |
| function | `ensure_runtime_file_perms` | `()` | Garantér at runtime.json kun er læsbar af ejeren (0600). | [src](../../../core/runtime/secrets.py#L41) |
| function | `_parse_int` | `(value, key)` | — | [src](../../../core/runtime/secrets.py#L59) |
| function | `read_runtime_key` | `(key, env_override=…, *, as_int=…)` | Read a top-level key from ~/.jarvis-v2/config/runtime.json. | [src](../../../core/runtime/secrets.py#L68) |
| function | `mail_config` | `()` | — | [src](../../../core/runtime/secrets.py#L103) |

## `core/runtime/session_handle.py`
_`SessionHandle` — én ejer, én lease, én sekvens._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SessionFormatError` | `` | Sessionens format kan ikke åbnes. Bærer hvilken slags. | [src](../../../core/runtime/session_handle.py#L63) |
| method | `SessionFormatError.__init__` | `(self, verdict, besked)` | — | [src](../../../core/runtime/session_handle.py#L66) |
| class | `NotWritable` | `` | Der blev forsøgt en skrivning gennem et skrivebeskyttet håndtag. | [src](../../../core/runtime/session_handle.py#L71) |
| class | `SessionHeader` | `` | Uforanderlig. Skrives ÉN gang ved oprettelsen og ændres aldrig. | [src](../../../core/runtime/session_handle.py#L76) |
| method | `SessionHeader.as_json` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L87) |
| function | `_ensure_header_column` | `(conn)` | — | [src](../../../core/runtime/session_handle.py#L93) |
| function | `write_header` | `(session_id, *, generation=…)` | Skriv headeren én gang. Et andet forsøg er en fejl, ikke en opdatering. | [src](../../../core/runtime/session_handle.py#L100) |
| function | `read_header` | `(session_id)` | — | [src](../../../core/runtime/session_handle.py#L119) |
| function | `classify_format` | `(session_id)` | Fire udfald der kan skelnes. En session uden header er `current`: | [src](../../../core/runtime/session_handle.py#L142) |
| class | `SessionHandle` | `` | Ejerskabet gjort til noget man holder. Brug som context manager. | [src](../../../core/runtime/session_handle.py#L159) |
| method | `SessionHandle.__init__` | `(self, session_id, *, owner, token, header, format_verdict)` | — | [src](../../../core/runtime/session_handle.py#L162) |
| method | `SessionHandle.writable` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L174) |
| method | `SessionHandle.token` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L178) |
| method | `SessionHandle.seq` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L181) |
| method | `SessionHandle.append` | `(self, event)` | Læg i kø. Intet rører databasen før `flush()` eller `close()`. | [src](../../../core/runtime/session_handle.py#L186) |
| method | `SessionHandle.flush` | `(self)` | Skriv køen som ÉN batch. Returnerer antal skrevne hændelser. | [src](../../../core/runtime/session_handle.py#L202) |
| method | `SessionHandle._projicer` | `(self)` | Kør projektionerne EFTER commit — kun for en kanonisk session. | [src](../../../core/runtime/session_handle.py#L222) |
| method | `SessionHandle.close` | `(self)` | Flush og GIV LEASE'N FRA DIG. Uden det venter næste proces på | [src](../../../core/runtime/session_handle.py#L251) |
| method | `SessionHandle.__enter__` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L270) |
| method | `SessionHandle.__exit__` | `(self, *exc)` | — | [src](../../../core/runtime/session_handle.py#L273) |
| function | `_bedoem` | `(session_id)` | — | [src](../../../core/runtime/session_handle.py#L277) |
| function | `open_readonly` | `(session_id)` | Kig uden at tage noget. Skriver intet — heller ikke en lease-række. | [src](../../../core/runtime/session_handle.py#L289) |
| function | `open_for_write` | `(session_id, *, owner, ttl_s=…)` | Tag skriveretten. Returnerer et skrivebeskyttet håndtag hvis en anden | [src](../../../core/runtime/session_handle.py#L296) |

## `core/runtime/session_ledger_crypto.py`
_Protect private message payloads at the durable ledger boundary._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `protect_event` | `(session_id, event, *, conn=…)` | — | [src](../../../core/runtime/session_ledger_crypto.py#L12) |
| function | `reveal_event` | `(session_id, event, *, conn=…)` | — | [src](../../../core/runtime/session_ledger_crypto.py#L34) |

## `core/runtime/settings.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeSettings` | `` | — | [src](../../../core/runtime/settings.py#L11) |
| method | `RuntimeSettings.to_dict` | `(self)` | — | [src](../../../core/runtime/settings.py#L715) |
| function | `_som_bool` | `(v)` | Streng bool. bool("false") er True — og et flag i runtime.json skrevet | [src](../../../core/runtime/settings.py#L727) |
| function | `_som_felt` | `(data, defaults, navn)` | Læs ét felt med typen fra standardværdien. | [src](../../../core/runtime/settings.py#L738) |
| function | `load_settings` | `()` | — | [src](../../../core/runtime/settings.py#L771) |
| function | `update_visible_execution_settings` | `(*, visible_model_provider=…, visible_model_name=…, visible_auth_profile=…)` | — | [src](../../../core/runtime/settings.py#L1248) |

## `core/runtime/state_store.py`
_Tiny JSON-file state store for module-globals that must survive restart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_path` | `(name)` | — | [src](../../../core/runtime/state_store.py#L29) |
| function | `load_json` | `(name, default)` | Read ``state/<name>.json``; return ``default`` if missing/corrupt. | [src](../../../core/runtime/state_store.py#L33) |
| function | `save_json` | `(name, data)` | Atomically persist ``data`` to ``state/<name>.json``. | [src](../../../core/runtime/state_store.py#L50) |
| function | `save_json_strict` | `(name, data)` | Atomically persist JSON and propagate failures to authoritative callers. | [src](../../../core/runtime/state_store.py#L61) |
| function | `med_laas` | `(name)` | Serialisér read-modify-write paa én state-fil paa tvaers af processer. | [src](../../../core/runtime/state_store.py#L88) |
| function | `aendret_ns` | `(name)` | Filens mtime i nanosekunder, eller 0 naar den ikke findes. | [src](../../../core/runtime/state_store.py#L110) |

## `core/runtime/token_renewal.py`
_Fornyelse af bearer-tokens — så en klient ikke låses ude af tiden alene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/token_renewal.py#L80) |
| function | `_afkod_uden_udloeb` | `(raw)` | Verificér signatur + udsteder, men LAD udløb passere. | [src](../../../core/runtime/token_renewal.py#L84) |
| function | `_gemt_bruger` | `(user_id)` | Slå brugeren op i BEGGE kartoteker. | [src](../../../core/runtime/token_renewal.py#L106) |
| function | `_klem_rolle` | `(token_rolle, gemt)` | Laveste af (token-rolle, gemt rolle). Ukendt bruger → token-rollen. | [src](../../../core/runtime/token_renewal.py#L130) |
| function | `_husk_jti` | `(user_id, jti)` | Skriv jti'en i brugerens liste, så den kan sortlistes senere. | [src](../../../core/runtime/token_renewal.py#L145) |
| function | `udloebs_alder_dage` | `(raw_token)` | Hvor mange dage er tokenet udløbet? Kun til LOGNING. | [src](../../../core/runtime/token_renewal.py#L163) |
| function | `renew` | `(raw_token, *, now=…)` | Veksl et bearer-token til et friskt et. | [src](../../../core/runtime/token_renewal.py#L189) |
| function | `revoke_user_tokens` | `(user_id)` | Sortlist alle fornyede tokens for én bruger. Returnerer antallet. | [src](../../../core/runtime/token_renewal.py#L268) |

## `core/runtime/work_ref.py`
_Én præfikset reference til et stykke arbejde — og ét sted at opløse den._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UgyldigReference` | `` | Referencen kan ikke opløses. Rejses hellere end at gætte en art. | [src](../../../core/runtime/work_ref.py#L62) |
| function | `lav` | `(art, id_)` | Byg en reference. Afviser ukendte arter og tomme id'er. | [src](../../../core/runtime/work_ref.py#L66) |
| function | `opløs` | `(reference)` | `art:id` → `(art, id)`. Afviser alt den ikke kan opløse. | [src](../../../core/runtime/work_ref.py#L88) |
| function | `er_gyldig` | `(reference)` | Kan referencen opløses? Til steder der skal filtrere, ikke fejle. | [src](../../../core/runtime/work_ref.py#L109) |
| function | `lager_for` | `(reference)` | Hvilket lager peger referencen ind i? Til fejlbeskeder og flader. | [src](../../../core/runtime/work_ref.py#L118) |
| function | `fra_run` | `(run_id)` | Genvej for den hyppigste rod: en synlig eller autonom kørsel. | [src](../../../core/runtime/work_ref.py#L124) |
| function | `fra_task` | `(task_id)` | — | [src](../../../core/runtime/work_ref.py#L129) |

## `core/runtime/workspace_paths.py`
_Workspace path resolver — single source of truth for filesystem layout._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NoUserContextError` | `` | Raised when workspace_dir() is called without a resolvable user_id. | [src](../../../core/runtime/workspace_paths.py#L17) |
| function | `_jarvis_home` | `()` | JARVIS_HOME resolved at call time (so tests can override via env). | [src](../../../core/runtime/workspace_paths.py#L26) |
| function | `shared_dir` | `()` | Jarvis' own state. All users see the same instance. | [src](../../../core/runtime/workspace_paths.py#L31) |
| function | `workspace_dir` | `(user_id=…)` | Per-relation workspace. Defaults to current_user_id() from context. | [src](../../../core/runtime/workspace_paths.py#L40) |
| function | `workspace_dir_or_owner` | `()` | workspace_dir() with an owner fallback, then shared/ as last resort. | [src](../../../core/runtime/workspace_paths.py#L65) |
| function | `_user_id_to_workspace_name` | `(user_id)` | Resolve user_id → workspace folder name. | [src](../../../core/runtime/workspace_paths.py#L89) |
| function | `rent_mappe_eller_filnavn` | `(navn)` | Et BLOT navn — ingen sti, ingen `..`. Tom streng når det ikke er det. | [src](../../../core/runtime/workspace_paths.py#L125) |
| function | `published_files_dir` | `(user_id=…, *, opret=…)` | Hvor ÉN brugers udgivne filer bor. `~/.jarvis-v2/files/u/<workspace>/`. | [src](../../../core/runtime/workspace_paths.py#L147) |
| function | `published_file_path` | `(filnavn, user_id=…, *, opret_mappe=…)` | Den fulde sti til ÉN brugers fil. Rejser ValueError på en sti. | [src](../../../core/runtime/workspace_paths.py#L194) |

## `core/runtime/ws_auth.py`
_Legitimation paa en WebSocket — uden at skrive tokenet i adgangsloggen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_foerste_bearer` | `(vaerdi)` | — | [src](../../../core/runtime/ws_auth.py#L41) |
| function | `token_fra_handshake` | `(headers)` | Find tokenet i et WS-handshake. | [src](../../../core/runtime/ws_auth.py#L48) |
| function | `verificer` | `(token)` | Verificér tokenet. Returnerer claims, eller None hvis det ikke holder. | [src](../../../core/runtime/ws_auth.py#L77) |
| function | `kraeves_auth` | `()` | Er auth slaaet til i denne runtime? | [src](../../../core/runtime/ws_auth.py#L94) |
| function | `_private_familier` | `()` | — | [src](../../../core/runtime/ws_auth.py#L129) |
| function | `er_ejer` | `(krav)` | Ejer = rollen «owner» i et verificeret token. Uden token (auth slået fra, | [src](../../../core/runtime/ws_auth.py#L139) |
| function | `til_klient` | `(item, *, ejer)` | Hvad der må sendes til denne klient, eller None. | [src](../../../core/runtime/ws_auth.py#L147) |

