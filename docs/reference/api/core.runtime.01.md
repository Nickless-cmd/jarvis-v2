# `core.runtime.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/__init__.py`

_(no top-level classes or functions)_

## `core/runtime/arko_provider.py`
_Arko Studio adapter for cheap-lane inference._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_config` | `()` | Pull base_url, api_key, agent_id from runtime.json. Returns None | [src](../../../core/runtime/arko_provider.py#L35) |
| function | `collapse_messages_to_prompt` | `(messages)` | Flatten OpenAI-style messages into one labelled prompt for Arko. | [src](../../../core/runtime/arko_provider.py#L51) |
| function | `call_arko` | `(*, messages=…, prompt=…, timeout=…)` | Send a message to the Arko cheap-lane agent and return an | [src](../../../core/runtime/arko_provider.py#L69) |
| function | `is_configured` | `()` | Cheap probe so the cheap-lane router can skip Arko silently when | [src](../../../core/runtime/arko_provider.py#L146) |

## `core/runtime/bootstrap.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_dirs` | `()` | — | [src](../../../core/runtime/bootstrap.py#L32) |
| function | `ensure_settings_file` | `()` | — | [src](../../../core/runtime/bootstrap.py#L38) |

## `core/runtime/circadian_state.py`
_Circadian state — energy level from clock + activity density._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_activity_event` | `()` | Call on each heartbeat run or visible turn to track activity density. | [src](../../../core/runtime/circadian_state.py#L33) |
| function | `get_circadian_context` | `()` | Compute and return current energy context. Fast — no LLM, no DB. | [src](../../../core/runtime/circadian_state.py#L42) |
| function | `load_persisted_state` | `()` | Load previously persisted energy level. Call once on startup. | [src](../../../core/runtime/circadian_state.py#L89) |
| function | `_clock_baseline` | `(hour)` | — | [src](../../../core/runtime/circadian_state.py#L109) |
| function | `_clock_phase_label` | `(hour)` | — | [src](../../../core/runtime/circadian_state.py#L123) |
| function | `_drain_score` | `()` | — | [src](../../../core/runtime/circadian_state.py#L139) |
| function | `_drain_label` | `(score)` | — | [src](../../../core/runtime/circadian_state.py#L143) |
| function | `_quiet_minutes_since_last_activity` | `(now)` | — | [src](../../../core/runtime/circadian_state.py#L151) |
| function | `_lower_energy` | `(level)` | — | [src](../../../core/runtime/circadian_state.py#L158) |
| function | `_raise_energy` | `(level)` | — | [src](../../../core/runtime/circadian_state.py#L163) |
| function | `_persist_state` | `(energy)` | — | [src](../../../core/runtime/circadian_state.py#L168) |

## `core/runtime/config.py`

_(no top-level classes or functions)_

## `core/runtime/db.py`
_Facade for core.runtime.db submodules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session_distillation_record_from_row` | `(row)` | — | [src](../../../core/runtime/db.py#L76) |

## `core/runtime/db_absence_traces.py`
_DB helpers for absence_traces (Lag 11 forgetting)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/db_absence_traces.py#L16) |
| function | `_month_key` | `(at=…)` | — | [src](../../../core/runtime/db_absence_traces.py#L20) |
| function | `increment_auto_counter` | `(*, workspace_id, delta=…, at=…)` | UPSERT the monthly auto-counter row. | [src](../../../core/runtime/db_absence_traces.py#L25) |
| function | `decrement_auto_counter` | `(*, workspace_id, month_key, delta=…)` | Used by revive_soft_deleted to undo a counted fade. | [src](../../../core/runtime/db_absence_traces.py#L69) |
| function | `insert_self_marker` | `(*, workspace_id, period_label)` | Record an irrevocable self-release. NO memory reference is stored. | [src](../../../core/runtime/db_absence_traces.py#L88) |
| function | `list_self_markers` | `(*, workspace_id, include_released=…)` | List self-markers for a workspace, ordered oldest first. | [src](../../../core/runtime/db_absence_traces.py#L108) |
| function | `get_auto_counter` | `(*, workspace_id, month_key=…)` | Get the counter row for a given month (default: current month). | [src](../../../core/runtime/db_absence_traces.py#L135) |
| function | `mark_self_released` | `(*, trace_id)` | Recursive release: mark an existing self-marker as released. | [src](../../../core/runtime/db_absence_traces.py#L157) |

## `core/runtime/db_agent_audit.py`
_Agent-audit-trail — PERSISTENT per-user/per-tool execution log for_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/runtime/db_agent_audit.py#L24) |
| function | `write_row` | `(*, user_id, role, tool, target_summary=…, decision=…)` | Insert one audit row. Returns True on success, False on any failure | [src](../../../core/runtime/db_agent_audit.py#L44) |
| function | `read_rows` | `(user_id=…, limit=…)` | Read audit rows, most recent first. Filters by user_id when given. | [src](../../../core/runtime/db_agent_audit.py#L72) |

## `core/runtime/db_agent_runtime.py`
_Persistence for Jarvis' agent + council runtime cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_agent_runtime_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_runtime.py#L17) |
| function | `create_agent_registry_entry` | `(*, agent_id, parent_agent_id=…, owner_agent_id=…, council_id=…, kind=…, role=…, goal=…, status=…, lane=…, provider=…, model=…, system_prompt=…, system_prompt_version=…, tool_policy=…, allowed_tools_json=…, persistent=…, ttl_seconds=…, schedule_json=…, next_wake_at=…, budget_tokens=…, tokens_burned=…, max_turns=…, turns_completed=…, failure_count=…, last_error=…, context_json=…, result_contract_json=…)` | Insert a new row into agent_registry and return the stored entry as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L192) |
| function | `get_agent_registry_entry` | `(agent_id)` | Return the agent_registry row for agent_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L278) |
| function | `update_agent_registry_entry` | `(agent_id, *, status=…, next_wake_at=…, schedule_json=…, tokens_burned_delta=…, max_turns=…, turns_completed_delta=…, failure_increment=…, last_error=…, completed_at=…, expired_at=…)` | Patch selected columns of one agent_registry row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L291) |
| function | `list_agent_registry_entries` | `(*, status=…, include_completed=…, limit=…)` | Return agent_registry rows as dicts, newest-updated first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L354) |
| function | `create_agent_run` | `(*, run_id, agent_id, status=…, execution_mode=…, provider=…, model=…, input_summary=…, output_summary=…, input_payload_json=…, output_payload_json=…, started_at=…, finished_at=…, input_tokens=…, output_tokens=…, cost_usd=…, provider_status=…, failure_reason=…)` | Insert a new row into agent_runs and return the stored run as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L380) |
| function | `get_agent_run` | `(run_id)` | Return the agent_runs row for run_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L444) |
| function | `update_agent_run` | `(run_id, *, status=…, output_summary=…, output_payload_json=…, started_at=…, finished_at=…, input_tokens=…, output_tokens=…, cost_usd=…, provider_status=…, failure_reason=…)` | Patch selected columns of one agent_runs row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L457) |
| function | `list_agent_runs` | `(*, agent_id=…, limit=…)` | Return agent_runs rows as dicts, newest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L505) |
| function | `create_agent_message` | `(*, message_id, thread_id, run_id=…, council_id=…, agent_id=…, peer_agent_id=…, direction=…, role=…, content=…, kind=…)` | Insert a new row into agent_messages and return the stored message as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L523) |
| function | `get_agent_message` | `(message_id)` | Return the agent_messages row for message_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L570) |
| function | `list_agent_messages` | `(*, thread_id=…, run_id=…, council_id=…, agent_id=…, limit=…)` | Return agent_messages rows as dicts, oldest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L583) |
| function | `create_agent_tool_call` | `(*, tool_call_id, run_id, agent_id, tool_name, status=…, arguments_json=…, result_preview=…, started_at=…, finished_at=…)` | Insert a new row into agent_tool_calls and return the stored call as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L618) |
| function | `get_agent_tool_call` | `(tool_call_id)` | Return the agent_tool_calls row for tool_call_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L663) |
| function | `list_agent_tool_calls` | `(*, run_id=…, agent_id=…, limit=…)` | Return agent_tool_calls rows as dicts, newest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L676) |
| function | `create_agent_schedule` | `(*, schedule_id, agent_id, schedule_kind=…, schedule_expr=…, next_fire_at=…, last_fire_at=…, missed_run_policy=…, active=…)` | Upsert a row in agent_schedules by schedule_id and return the stored dict. | [src](../../../core/runtime/db_agent_runtime.py#L698) |
| function | `get_agent_schedule` | `(schedule_id)` | Return the agent_schedules row for schedule_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L752) |
| function | `update_agent_schedule` | `(schedule_id, *, schedule_expr=…, next_fire_at=…, last_fire_at=…, active=…)` | Patch selected columns of one agent_schedules row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L765) |
| function | `list_agent_schedules` | `(*, agent_id=…, active_only=…, due_before=…, limit=…)` | Return agent_schedules rows as dicts, ordered by next_fire_at then created_at. | [src](../../../core/runtime/db_agent_runtime.py#L804) |
| function | `create_council_session` | `(*, council_id, owner_agent_id=…, topic=…, status=…, mode=…, summary=…)` | Insert a new row into council_sessions and return the stored session as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L829) |
| function | `get_council_session` | `(council_id)` | Return the council_sessions row for council_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L861) |
| function | `update_council_session` | `(council_id, *, status=…, summary=…, finished_at=…)` | Patch selected columns of one council_sessions row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L880) |
| function | `list_council_sessions` | `(limit=…)` | Return council_sessions rows as dicts, newest-updated first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L915) |
| function | `add_council_member` | `(*, council_id, agent_id, role, position_summary=…, vote=…, confidence=…)` | Upsert a council member by (council_id, agent_id) and return the stored dict. | [src](../../../core/runtime/db_agent_runtime.py#L933) |
| function | `update_council_member` | `(*, council_id, agent_id, position_summary=…, vote=…, confidence=…)` | Patch a council member's position/vote/confidence by (council_id, agent_id). | [src](../../../core/runtime/db_agent_runtime.py#L969) |
| function | `get_council_member` | `(*, council_id, agent_id)` | Return the council_members row for (council_id, agent_id) as a dict, or None. | [src](../../../core/runtime/db_agent_runtime.py#L1007) |
| function | `list_council_members` | `(*, council_id)` | Return all council_members rows for council_id as dicts, oldest-created first. | [src](../../../core/runtime/db_agent_runtime.py#L1020) |
| function | `_agent_registry_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1034) |
| function | `_agent_run_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1070) |
| function | `_agent_message_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1094) |
| function | `_agent_tool_call_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1110) |
| function | `_agent_schedule_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1125) |
| function | `_council_session_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1140) |
| function | `_council_member_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1154) |

## `core/runtime/db_anomalies.py`
_Central-anomalier — persistent register over UDEFINEREDE fejl Centralen ikke selv har_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_anomalies_table` | `(conn)` | — | [src](../../../core/runtime/db_anomalies.py#L22) |
| function | `record_anomaly_signature` | `(*, signature, category, importance, source, sample, location=…)` | UPSERT en anomali-signatur. Returnerer True hvis det er FØRSTE gang (ny fejl-type | [src](../../../core/runtime/db_anomalies.py#L77) |
| function | `list_anomalies` | `(*, limit=…, unresolved_only=…, min_importance=…, exclude_known=…)` | Læs anomalier (nyeste først). `exclude_known=True` (default) filtrerer promoverede | [src](../../../core/runtime/db_anomalies.py#L134) |
| function | `resolve_anomaly` | `(signature)` | Markér én anomali-signatur som håndteret (forsvinder fra det live register). Selv-sikker. | [src](../../../core/runtime/db_anomalies.py#L169) |
| function | `anomaly_counts` | `()` | Hurtig optælling pr. importance (til realtime-panelet). Selv-sikker. | [src](../../../core/runtime/db_anomalies.py#L185) |
| function | `_within_hours` | `(iso_ts, hours)` | True hvis iso_ts ligger inden for de seneste `hours` timer. Self-safe → False. | [src](../../../core/runtime/db_anomalies.py#L206) |
| function | `promote_to_known` | `(*, signature, count, first_seen, importance=…, category=…, auto_threshold=…, auto_window_hours=…, force=…)` | Promovér en anomali-signatur til 'kendt signal' hvis tærskel nået. Self-safe. | [src](../../../core/runtime/db_anomalies.py#L216) |
| function | `route_anomaly_to_nerve` | `(*, signature, cluster, nerve, action=…, notes=…, promoted_by=…)` | Knyt én anomali-signatur til en nerve (manuel routing). Sætter known_signal=1 + | [src](../../../core/runtime/db_anomalies.py#L264) |
| function | `get_known_signal` | `(signature)` | Slå en signatur op i known_anomaly_signals. Returnerer {cluster, nerve, action} | [src](../../../core/runtime/db_anomalies.py#L296) |
| function | `bump_known_signal_count` | `(signature)` | Tæl en ny forekomst af et allerede-kendt signal (uden at vise det som anomali). Self-safe. | [src](../../../core/runtime/db_anomalies.py#L313) |
| function | `list_known_signals` | `(*, limit=…)` | Liste over promoverede 'kendte signaler' (nyeste først). Self-sikker → []. | [src](../../../core/runtime/db_anomalies.py#L328) |
| function | `depromote_known_signal` | `(signature)` | Angre en promotion: slet known_anomaly_signals-rækken + sæt known_signal=0 i | [src](../../../core/runtime/db_anomalies.py#L349) |

## `core/runtime/db_api_connections.py`
_API-forbindelses-nerve — persistent, GDPR-bundet metadata om hvem/hvad der rammer API'et._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_api_connections.py#L33) |
| function | `flush_records` | `(presence_deltas, log_rows)` | Batch-skriv: UPSERT presence-aggregater + INSERT detalje-log. Én DB-tur. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L70) |
| function | `anonymize_and_prune` | `(*, retention_hours=…, delete_days=…)` | GDPR-retention: trunkér fuld IP → /24 i log-rækker ældre end retention_hours, slet | [src](../../../core/runtime/db_api_connections.py#L123) |
| function | `anonymize_ip` | `(ip)` | Trunkér til /24 (ipv4) eller /64 (ipv6). GDPR-anonymisering — beholder subnet, taber vært. | [src](../../../core/runtime/db_api_connections.py#L164) |
| function | `read_presence` | `(*, active_within_s=…, limit=…)` | Presence-view: forbindelser set for nylig. active=set inden for active_within_s. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L178) |
| function | `read_recent_errors` | `(*, limit=…)` | Seneste fejl-requests (status ≥ 400) til fejl-sporing. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L201) |

## `core/runtime/db_autonomy.py`
_Autonomy-proposals — niveau-2 autonomi: pending forslag fra Jarvis der afventer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_autonomy_proposals_table` | `(conn)` | Pending proposals from Jarvis awaiting Bjørn approval. | [src](../../../core/runtime/db_autonomy.py#L21) |
| function | `_autonomy_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_autonomy.py#L65) |
| function | `create_autonomy_proposal` | `(*, proposal_id, kind, title, rationale=…, payload=…, created_by=…, session_id=…, run_id=…, tick_id=…, canonical_key=…)` | — | [src](../../../core/runtime/db_autonomy.py#L82) |
| function | `list_autonomy_proposals` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/runtime/db_autonomy.py#L123) |
| function | `get_autonomy_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_autonomy.py#L152) |
| function | `resolve_autonomy_proposal` | `(proposal_id, *, status, resolved_by=…, resolution_note=…, execution_result=…)` | — | [src](../../../core/runtime/db_autonomy.py#L163) |

## `core/runtime/db_bounded_action.py`
_Persistence for the `bounded_action_continuity_state` table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_bounded_action_tables` | `(conn)` | — | [src](../../../core/runtime/db_bounded_action.py#L13) |
| function | `_bounded_action_continuity_state_from_row` | `(row)` | — | [src](../../../core/runtime/db_bounded_action.py#L41) |
| function | `get_bounded_action_continuity_state` | `()` | — | [src](../../../core/runtime/db_bounded_action.py#L72) |
| function | `upsert_bounded_action_continuity_state` | `(*, active, kind, continuity_id, action_continuity_state, last_action_type, last_action_target, last_action_summary, last_action_outcome, last_action_at, action_mode, read_only, mutation_permitted, followup_state, followup_hint, post_action_understanding, post_action_concern, confidence, source_contributors, boundary, updated_at, source)` | — | [src](../../../core/runtime/db_bounded_action.py#L105) |

## `core/runtime/db_capability.py`
_Persistence for the `capability_invocations` table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_capability_tables` | `(conn)` | — | [src](../../../core/runtime/db_capability.py#L14) |
| function | `recent_capability_invocations` | `(limit=…)` | — | [src](../../../core/runtime/db_capability.py#L38) |
| function | `_ensure_capability_invocation_approval_columns` | `(conn)` | — | [src](../../../core/runtime/db_capability.py#L86) |

## `core/runtime/db_capability_approval.py`
_Capability approval + approval feedback CRUD._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `recent_capability_approval_requests` | `(limit=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L27) |
| function | `get_capability_approval_request` | `(request_id)` | — | [src](../../../core/runtime/db_capability_approval.py#L61) |
| function | `approve_capability_approval_request` | `(request_id, *, approved_at)` | — | [src](../../../core/runtime/db_capability_approval.py#L96) |
| function | `record_capability_approval_request_execution` | `(request_id, *, executed_at, invocation_status, invocation_execution_mode)` | — | [src](../../../core/runtime/db_capability_approval.py#L153) |
| function | `_capability_approval_request_from_row` | `(row, *, status=…, approved_at=…, executed=…, executed_at=…, invocation_status=…, invocation_execution_mode=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L213) |
| function | `_ensure_capability_approval_request_columns` | `(conn)` | — | [src](../../../core/runtime/db_capability_approval.py#L255) |
| function | `latest_capability_approval_request` | `(*, execution_mode=…, include_executed=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L279) |
| function | `latest_approved_capability_approval_request` | `(*, execution_mode=…, capability_id=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L328) |
| function | `insert_approval_feedback` | `(*, recorded_at, intent_key, approval_state, approval_source, tool_name=…, resolution_reason=…, resolution_message=…, session_id=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L378) |
| function | `list_approval_feedback` | `(limit=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L456) |
| function | `approval_feedback_stats_by_tool` | `(days=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L471) |
| function | `count_approval_feedback` | `()` | — | [src](../../../core/runtime/db_capability_approval.py#L501) |
| function | `_approval_feedback_from_row` | `(row)` | — | [src](../../../core/runtime/db_capability_approval.py#L509) |

## `core/runtime/db_central_incidents.py`
_Central-incidents — persistent log af det Den Intelligente Central GRIBER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_central_incidents_table` | `(conn)` | — | [src](../../../core/runtime/db_central_incidents.py#L21) |
| function | `record_central_incident` | `(*, cluster, nerve, kind, severity=…, message=…, run_id=…, session_id=…, dedup=…)` | Persistér én incident. Returnerer row-id (eller None ved fejl/dedup). Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L44) |
| function | `bump_open_incident` | `(*, cluster, nerve, run_id=…, session_id=…, note=…)` | Refresh den STÅENDE åbne incident for (cluster, nerve) i stedet for at dedup'e | [src](../../../core/runtime/db_central_incidents.py#L82) |
| function | `list_central_incidents` | `(*, limit=…, unresolved_only=…, min_severity=…)` | Læs incidents (nyeste først). Claude poller denne. Selv-sikker → [] ved fejl. | [src](../../../core/runtime/db_central_incidents.py#L128) |
| function | `resolve_central_incident` | `(incident_id)` | Markér en incident som håndteret. Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L156) |
| function | `resolve_central_incidents` | `(*, cluster, nerve)` | Auto-resolve ALLE uløste incidents for én (cluster, nerve). Returnerer antal lukkede. | [src](../../../core/runtime/db_central_incidents.py#L169) |
| function | `has_unresolved_message` | `(*, cluster, nerve, message, within_seconds=…)` | True hvis en uløst incident med SAMME besked allerede findes inden for tidsvinduet. | [src](../../../core/runtime/db_central_incidents.py#L188) |
| function | `count_unresolved` | `(*, min_severity=…, exclude_nerve=…)` | Antal uhåndterede incidents (til hurtig live-status). Selv-sikker → 0. | [src](../../../core/runtime/db_central_incidents.py#L214) |
| function | `has_open_incident` | `(*, cluster, nerve)` | True hvis der allerede findes en uløst incident for (cluster, nerve). Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L241) |

## `core/runtime/db_cheap_provider.py`
_Persistence for the cheap-provider runtime-state + invocation cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `upsert_cheap_provider_runtime_state` | `(*, provider, model=…, lane=…, status=…, auth_ready=…, quota_limited=…, cooldown_until=…, last_error_code=…, last_error_message=…, last_success_at=…, last_failure_at=…, metadata_json=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L14) |
| function | `get_cheap_provider_runtime_state` | `(*, provider, model=…, lane=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L106) |
| function | `list_cheap_provider_runtime_states` | `(*, lane=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L162) |
| function | `record_cheap_provider_invocation` | `(*, provider, model=…, lane=…, status, error_code=…, error_message=…, retry_after_seconds=…, latency_ms=…, input_tokens=…, output_tokens=…, cost_usd=…, auth_profile=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L214) |
| function | `count_cheap_provider_invocations` | `(*, provider, lane=…, since, status=…, auth_profile=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L303) |

## `core/runtime/db_claude_dispatch.py`
_Schema for the claude_dispatch_* tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_claude_dispatch_tables` | `(conn)` | — | [src](../../../core/runtime/db_claude_dispatch.py#L11) |

## `core/runtime/db_cognitive.py`
_Persistence for the cognitive + experiential-memory domain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_session_distillation_records_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L28) |
| function | `insert_session_distillation_record` | `(*, distillation_id, session_id, run_id, private_brain_count, workspace_memory_count, discard_count, summary, detail, created_at)` | Insert a session-distillation record (INSERT OR IGNORE on distillation_id). | [src](../../../core/runtime/db_cognitive.py#L53) |
| function | `get_session_distillation_record` | `(distillation_id)` | Return the session-distillation record for the given id, or None if absent. | [src](../../../core/runtime/db_cognitive.py#L90) |
| function | `_ensure_cognitive_personality_vector_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L110) |
| function | `upsert_cognitive_personality_vector` | `(*, confidence_by_domain=…, communication_style=…, learned_preferences=…, recurring_mistakes=…, strengths_discovered=…, current_bearing=…, emotional_baseline=…)` | Insert a new personality-vector version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L130) |
| function | `get_latest_cognitive_personality_vector` | `()` | Return the highest-version personality-vector row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L178) |
| function | `list_cognitive_personality_vectors` | `(*, limit=…)` | Return up to `limit` personality-vector rows (newest version first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L201) |
| function | `_ensure_cognitive_taste_profile_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L223) |
| function | `upsert_cognitive_taste_profile` | `(*, code_taste=…, design_taste=…, communication_taste=…, evidence_count=…)` | Insert a new taste-profile version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L240) |
| function | `get_latest_cognitive_taste_profile` | `()` | Return the highest-version taste-profile row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L270) |
| function | `_ensure_cognitive_chronicle_entries_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L290) |
| function | `insert_cognitive_chronicle_entry` | `(*, entry_id, period, narrative, key_events=…, lessons=…, affective_signature=…)` | Insert or replace a chronicle entry keyed by entry_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L309) |
| function | `get_latest_cognitive_chronicle_entry` | `()` | Return the most recently created chronicle entry as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L334) |
| function | `list_cognitive_chronicle_entries` | `(*, limit=…)` | Return up to `limit` chronicle entries (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L355) |
| function | `_ensure_cognitive_episodes_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L396) |
| function | `insert_cognitive_episode` | `(*, episode_id, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, metacognition_json=…, attention_json=…, learning_json=…, social_json=…, perception_json=…, policy_json=…)` | Insert or replace a cognitive episode keyed by episode_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L431) |
| function | `list_cognitive_episodes` | `(*, limit=…)` | Return up to `limit` cognitive episodes (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L479) |
| function | `get_latest_cognitive_episode` | `()` | Return the most recent cognitive episode as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L490) |
| function | `_cognitive_episode_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_cognitive.py#L496) |
| function | `_ensure_cognitive_relationship_texture_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L514) |
| function | `upsert_cognitive_relationship_texture` | `(*, humor_frequency=…, inside_references=…, correction_patterns=…, trust_trajectory=…, productive_hours=…, conversation_rhythm=…, unspoken_rules=…)` | Insert a new relationship-texture version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L534) |
| function | `get_latest_cognitive_relationship_texture` | `()` | Return the highest-version relationship-texture row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L569) |
| function | `_ensure_cognitive_compass_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L592) |
| function | `upsert_cognitive_compass_state` | `(*, bearing, rationale=…, open_loop_count=…)` | Upsert the singleton compass state ('compass-current', INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L607) |
| function | `get_latest_cognitive_compass_state` | `()` | Return the most recently updated compass-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L630) |
| function | `_ensure_cognitive_rhythm_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L648) |
| function | `upsert_cognitive_rhythm_state` | `(*, phase, energy=…, social=…, recovery_needed=…, focus_protection=…, initiative_multiplier=…, confidence_threshold_delta=…)` | Upsert the singleton rhythm state ('rhythm-current', INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L667) |
| function | `get_latest_cognitive_rhythm_state` | `()` | Return the most recently updated rhythm-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L698) |
| function | `_ensure_cognitive_habit_patterns_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L720) |
| function | `upsert_cognitive_habit_pattern` | `(*, pattern_key, description=…)` | Upsert a habit pattern by pattern_key. | [src](../../../core/runtime/db_cognitive.py#L751) |
| function | `upsert_cognitive_friction_signal` | `(*, task_signature, inefficiency_score=…, description=…)` | Upsert a friction signal by task_signature. | [src](../../../core/runtime/db_cognitive.py#L790) |
| function | `list_cognitive_habit_patterns` | `(*, limit=…)` | Return up to `limit` habit patterns (most recurrent first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L831) |
| function | `list_cognitive_friction_signals` | `(*, limit=…)` | Return up to `limit` friction signals (most repeated first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L852) |
| function | `_ensure_cognitive_decisions_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L873) |
| function | `insert_cognitive_decision` | `(*, decision_id, title, context=…, options=…, decision=…, why=…, regrets=…, refs=…)` | Insert or replace a decision record keyed by decision_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L892) |
| function | `list_cognitive_decisions` | `(*, limit=…)` | Return up to `limit` decision records (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L919) |
| function | `_ensure_cognitive_counterfactuals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L942) |
| function | `insert_cognitive_counterfactual` | `(*, cf_id, trigger_type, anchor=…, cf_question=…, source=…, confidence=…)` | Insert or replace a counterfactual keyed by cf_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L959) |
| function | `list_cognitive_counterfactuals` | `(*, limit=…)` | Return up to `limit` counterfactuals (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L984) |
| function | `_ensure_cognitive_shared_language_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1006) |
| function | `upsert_cognitive_shared_language_term` | `(*, phrase, meaning=…, anchors=…, confidence=…)` | Upsert a shared-language term by phrase. | [src](../../../core/runtime/db_cognitive.py#L1023) |
| function | `list_cognitive_shared_language` | `(*, limit=…)` | Return up to `limit` shared-language terms (highest confidence first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1064) |
| function | `_ensure_cognitive_seeds_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1085) |
| function | `insert_cognitive_seed` | `(*, seed_id, title, summary=…, activate_at=…, activate_on_event=…, activate_on_context=…, relevance_score=…, linked_goal=…)` | Insert or replace a seed keyed by seed_id, status forced to 'planted'. | [src](../../../core/runtime/db_cognitive.py#L1106) |
| function | `update_cognitive_seed_status` | `(*, seed_id, status)` | Update the status (and updated_at) of the seed with the given seed_id. Returns None. | [src](../../../core/runtime/db_cognitive.py#L1136) |
| function | `list_cognitive_seeds` | `(*, status=…, limit=…)` | Return up to `limit` seeds (newest first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1147) |
| function | `_ensure_cognitive_gut_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1174) |
| function | `update_cognitive_gut_state` | `(*, prediction_correct, last_hunch=…)` | Update the singleton gut state ('gut-current') with one prediction outcome. | [src](../../../core/runtime/db_cognitive.py#L1190) |
| function | `get_cognitive_gut_state` | `()` | Return the singleton gut-state row ('gut-current') as a dict, or None if unset. | [src](../../../core/runtime/db_cognitive.py#L1230) |
| function | `_ensure_cognitive_experiments_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1248) |
| function | `upsert_cognitive_experiment` | `(*, experiment_id, hypothesis, metric=…, cohorts=…, n=…, status=…, result=…)` | Insert or replace an experiment keyed by experiment_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1267) |
| function | `list_cognitive_experiments` | `(*, status=…, limit=…)` | Return up to `limit` experiments (most recently updated first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1294) |
| function | `_ensure_cognitive_conversation_signatures_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1323) |
| function | `upsert_cognitive_conversation_signature` | `(*, signature_type, success, context=…, duration_min=…)` | Upsert a conversation signature by signature_type. | [src](../../../core/runtime/db_cognitive.py#L1341) |
| function | `list_cognitive_conversation_signatures` | `(*, limit=…)` | Return up to `limit` conversation signatures (most frequent first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1387) |
| function | `_ensure_cognitive_user_emotional_states_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1408) |
| function | `insert_cognitive_user_emotional_state` | `(*, state_id, detected_mood, confidence=…, evidence=…, user_message_preview=…, response_adjustment=…, run_id=…)` | Insert or replace a user-emotional-state row keyed by state_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1426) |
| function | `get_latest_cognitive_user_emotional_state` | `()` | Return the most recently created user-emotional-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L1455) |
| function | `list_cognitive_user_emotional_states` | `(*, limit=…)` | Return up to `limit` user-emotional-state rows (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1476) |
| function | `_ensure_cognitive_experiential_memories_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1497) |
| function | `insert_cognitive_experiential_memory` | `(*, memory_id, session_id=…, run_id=…, narrative=…, user_mood=…, jarvis_mood=…, key_lesson=…, emotion_arc=…, topic=…, importance=…)` | Insert or replace an experiential memory keyed by memory_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1521) |
| function | `reinforce_experiential_memory` | `(memory_id)` | Bump reinforcement_count by 1 and reset decay_score to 0 for the given memory. Returns None. | [src](../../../core/runtime/db_cognitive.py#L1554) |
| function | `list_cognitive_experiential_memories` | `(*, limit=…)` | Return up to `limit` experiential memories (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1568) |
| function | `get_experiential_memory_candidates` | `(*, limit=…)` | Return candidate memories for LLM-based associative scoring. | [src](../../../core/runtime/db_cognitive.py#L1594) |
| function | `_ensure_cognitive_self_surprises_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1628) |
| function | `insert_cognitive_self_surprise` | `(*, surprise_id, surprise_type, narrative, expected_confidence=…, actual_outcome=…, domain=…, run_id=…)` | Insert or replace a self-surprise keyed by surprise_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1646) |
| function | `list_cognitive_self_surprises` | `(*, limit=…)` | Return up to `limit` self-surprises (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1669) |
| function | `_ensure_cognitive_narrative_identities_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1688) |
| function | `insert_cognitive_narrative_identity` | `(*, identity_id, narrative, key_changes=…, personality_version=…)` | Insert or replace a narrative-identity keyed by identity_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1703) |
| function | `get_latest_cognitive_narrative_identity` | `()` | Return the most recently created narrative-identity row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L1723) |
| function | `list_cognitive_narrative_identities` | `(*, limit=…)` | Return up to `limit` narrative-identity rows (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1740) |
| function | `_ensure_cognitive_gratitude_signals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1753) |
| function | `insert_cognitive_gratitude_signal` | `(*, gratitude_id, trigger_event, detail=…, intensity=…)` | Insert or replace a gratitude signal keyed by gratitude_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1768) |
| function | `list_cognitive_gratitude_signals` | `(*, limit=…)` | Return up to `limit` gratitude signals (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1788) |
| function | `_ensure_cognitive_emergent_goals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1801) |
| function | `upsert_cognitive_emergent_goal` | `(*, goal_id, desire, source=…, intensity=…, status=…)` | Insert or replace an emergent goal keyed by goal_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1818) |
| function | `list_cognitive_emergent_goals` | `(*, status=…, limit=…)` | Return up to `limit` emergent goals (highest intensity first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1838) |
| function | `_ensure_cognitive_formed_values_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1857) |
| function | `upsert_cognitive_formed_value` | `(*, value_id, value_statement, source_experience=…, conviction=…)` | Upsert a formed value by value_id. | [src](../../../core/runtime/db_cognitive.py#L1874) |
| function | `list_cognitive_formed_values` | `(*, limit=…)` | Return up to `limit` formed values (highest conviction first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1909) |
| function | `_ensure_cognitive_conflict_memories_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1922) |
| function | `insert_cognitive_conflict_memory` | `(*, conflict_id, topic, jarvis_position=…, user_position=…, resolution=…, lesson=…)` | Insert or replace a conflict memory keyed by conflict_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1939) |
| function | `list_cognitive_conflict_memories` | `(*, limit=…)` | Return up to `limit` conflict memories (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1961) |
| function | `_ensure_cognitive_emotion_concept_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1975) |
| function | `upsert_cognitive_emotion_concept_signal` | `(*, signal_id, concept, intensity, direction=…, trigger=…, source=…, influences=…, expires_at)` | Upsert a time-bounded emotion-concept signal by signal_id. | [src](../../../core/runtime/db_cognitive.py#L1995) |
| function | `list_active_cognitive_emotion_concept_signals` | `(*, now_iso, min_intensity=…, limit=…)` | Return active emotion-concept signals as dicts (highest intensity first). | [src](../../../core/runtime/db_cognitive.py#L2037) |

## `core/runtime/db_cognitive_utility.py`
_Persistence for the cognitive-domain utility caches._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_web_cache_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L27) |
| function | `web_cache_store` | `(*, conn, cache_key, query_raw, query_normalized, source_url, title, body, ttl_policy, expires_at)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L52) |
| function | `web_cache_lookup` | `(*, conn, cache_key)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L87) |
| function | `web_cache_cleanup` | `(*, conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L122) |
| function | `_ensure_session_topics_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L132) |
| function | `session_topic_accumulate` | `(session_id, topic_label, mention_count=…, first_seen=…, last_seen=…)` | Upsert a topic for a session — merge if exists, insert if not. | [src](../../../core/runtime/db_cognitive_utility.py#L157) |
| function | `session_topics_for_session` | `(session_id)` | Return all accumulated topics for a session, ordered by mention_count DESC. | [src](../../../core/runtime/db_cognitive_utility.py#L198) |
| function | `session_topic_cleanup` | `(max_age_days=…)` | Delete session topics not seen for max_age_days. | [src](../../../core/runtime/db_cognitive_utility.py#L219) |
| function | `_ensure_daemon_output_log_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L229) |
| function | `daemon_output_log_insert` | `(*, daemon_name, raw_llm_output, parsed_result, success, provider=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L248) |
| function | `daemon_output_log_recent` | `(daemon_name=…, limit=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L275) |
| function | `daemon_output_log_cleanup` | `(max_age_days=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L302) |

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
| class | `ClosingConnection` | `` | — | [src](../../../core/runtime/db_core.py#L61) |
| method | `ClosingConnection.__exit__` | `(self, exc_type, exc_value, traceback)` | — | [src](../../../core/runtime/db_core.py#L62) |
| class | `PooledConnection` | `` | Som ClosingConnection men LUKKER IKKE ved __exit__/close() — poolen ejer | [src](../../../core/runtime/db_core.py#L69) |
| method | `PooledConnection.__exit__` | `(self, exc_type, exc_value, traceback)` | — | [src](../../../core/runtime/db_core.py#L72) |
| method | `PooledConnection.close` | `(self)` | — | [src](../../../core/runtime/db_core.py#L76) |
| function | `_make_connection` | `(_factory)` | Åbn ÉN ny sqlite-forbindelse + sæt PRAGMAs (busy_timeout, WAL-once, synchronous). | [src](../../../core/runtime/db_core.py#L87) |
| function | `close_pooled_connection` | `()` | Luk DENNE tråds pooled forbindelse rigtigt (shutdown/tests). Self-safe. | [src](../../../core/runtime/db_core.py#L112) |
| function | `connect` | `()` | DEL 1 — connection pooling (2026-07-12): genbrug ÉN thread-local forbindelse i | [src](../../../core/runtime/db_core.py#L123) |
| function | `_rank_for` | `(ranks, value)` | — | [src](../../../core/runtime/db_core.py#L164) |
| function | `_stronger_ranked_value` | `(current, proposed, ranks)` | — | [src](../../../core/runtime/db_core.py#L168) |
| function | `_merge_text_fragments` | `(current, proposed, *, limit=…)` | — | [src](../../../core/runtime/db_core.py#L174) |
| function | `_upsert_signal` | `(*, conn, table, id_col, type_col, id_val, type_val, canonical_key, lookup_statuses, overwrite_cols, rank_cols, merge_text_cols, accumulate_cols, created_at, updated_at)` | Generic merge-forward upsert for the runtime_*_signal families. | [src](../../../core/runtime/db_core.py#L189) |
| function | `_rs_cache_put` | `(key, value)` | — | [src](../../../core/runtime/db_core.py#L360) |
| function | `clear_runtime_state_cache` | `()` | Ryd hele read-cachen (til tests / tvungen frisk læsning). Self-safe. | [src](../../../core/runtime/db_core.py#L365) |
| function | `set_runtime_state_value` | `(key, value, *, updated_at=…)` | — | [src](../../../core/runtime/db_core.py#L371) |
| function | `get_runtime_state_value` | `(key, default=…)` | — | [src](../../../core/runtime/db_core.py#L391) |
| function | `get_runtime_state_bool` | `(key, default=…)` | Read a runtime-state flag and coerce it to bool ROBUSTLY. | [src](../../../core/runtime/db_core.py#L424) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_core.py#L444) |
| function | `_conn_db_id` | `(conn)` | Stable identifier for a sqlite connection's underlying database. | [src](../../../core/runtime/db_core.py#L493) |
| function | `_install_ensure_once_cache` | `()` | Bagudkompat-shim: wrapper _ensure_*_table funcs på core.runtime.db | [src](../../../core/runtime/db_core.py#L517) |
| function | `invalidate_ensure_once_cache` | `(table_name=…)` | Force re-run of `_ensure_*_table` on next call. | [src](../../../core/runtime/db_core.py#L527) |
| function | `_install_ensure_once_cache_for` | `(module_name)` | Wrap _ensure_*_table funcs i target-modul med once-cache. | [src](../../../core/runtime/db_core.py#L545) |

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
| function | `set_status` | `(decision_id, new_status)` | — | [src](../../../core/runtime/db_decisions.py#L187) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/runtime/db_decisions.py#L204) |
| function | `list_decisions` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_decisions.py#L216) |
| function | `list_reviews` | `(decision_id, *, limit=…)` | — | [src](../../../core/runtime/db_decisions.py#L237) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/runtime/db_decisions.py#L248) |
| function | `count_decisions` | `(*, status=…)` | — | [src](../../../core/runtime/db_decisions.py#L263) |

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
| function | `create_tool_intent_approval_request` | `(*, intent_key, intent_type, intent_target, approval_scope, approval_required, approval_reason, requested_at, expires_at, execution_state=…)` | — | [src](../../../core/runtime/db_governance.py#L31) |
| function | `get_tool_intent_approval_request` | `(intent_key)` | — | [src](../../../core/runtime/db_governance.py#L99) |
| function | `resolve_tool_intent_approval_request` | `(intent_key, *, approval_state, approval_source, resolved_at, resolution_reason, resolution_message=…, session_id=…)` | — | [src](../../../core/runtime/db_governance.py#L134) |
| function | `expire_tool_intent_approval_request` | `(intent_key, *, expired_at, resolution_reason)` | — | [src](../../../core/runtime/db_governance.py#L174) |
| function | `_tool_intent_approval_request_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L206) |
| function | `record_runtime_contract_file_write` | `(*, write_id, candidate_id, target_file, canonical_key, write_status, actor, summary, content_line, created_at)` | — | [src](../../../core/runtime/db_governance.py#L234) |
| function | `get_runtime_contract_file_write` | `(write_id)` | — | [src](../../../core/runtime/db_governance.py#L282) |
| function | `recent_runtime_contract_file_writes` | `(limit=…)` | — | [src](../../../core/runtime/db_governance.py#L308) |
| function | `runtime_contract_file_write_counts` | `()` | — | [src](../../../core/runtime/db_governance.py#L332) |
| function | `_ensure_runtime_contract_file_write_table` | `(conn)` | — | [src](../../../core/runtime/db_governance.py#L349) |
| function | `_runtime_contract_file_write_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L374) |
| function | `record_runtime_webchat_execution_pilot` | `(*, pilot_id, canonical_key, status, execution_type, title, summary, rationale, source_kind, confidence, evidence_summary, support_summary, status_reason=…, run_id=…, session_id=…, support_count=…, session_count=…, delivery_channel=…, delivery_state=…, created_at, updated_at)` | — | [src](../../../core/runtime/db_governance.py#L397) |
| function | `list_runtime_webchat_execution_pilots` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_governance.py#L479) |
| function | `get_runtime_webchat_execution_pilot` | `(pilot_id)` | — | [src](../../../core/runtime/db_governance.py#L526) |
| function | `_runtime_webchat_execution_pilot_from_row` | `(row)` | — | [src](../../../core/runtime/db_governance.py#L564) |

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

## `core/runtime/db_instrument.py`
_Persistens for central_instrument — selv-instrumenterings-motorens fund + scan-cache._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_instrument.py#L20) |
| function | `get_file_hash` | `(file)` | Sidst-scannede indholds-hash for en fil (til incremental skip). Self-safe → None. | [src](../../../core/runtime/db_instrument.py#L54) |
| function | `set_file_hash` | `(file, content_hash, n_findings)` | — | [src](../../../core/runtime/db_instrument.py#L68) |
| function | `replace_file_findings` | `(file, findings)` | Erstat ALLE åbne fund for én fil (idempotent pr. scan). Bevarer status (fx 'dismissed') | [src](../../../core/runtime/db_instrument.py#L84) |
| function | `list_findings` | `(*, status=…, min_score=…, limit=…)` | Fund (højeste score først). Self-safe → []. | [src](../../../core/runtime/db_instrument.py#L120) |
| function | `summary` | `()` | Hurtig optælling pr. severity + total (til observe/central_query). Self-safe. | [src](../../../core/runtime/db_instrument.py#L135) |

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

## `core/runtime/db_private_brain.py`
_Private brain records — Jarvis' EGNE private lag (private-carry-erindringer med_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_private_brain_records_table` | `(conn)` | — | [src](../../../core/runtime/db_private_brain.py#L22) |
| function | `_private_brain_record_from_row` | `(row)` | — | [src](../../../core/runtime/db_private_brain.py#L67) |
| function | `insert_private_brain_record` | `(*, record_id, record_type, layer, session_id, run_id, focus, summary, detail, source_signals, confidence, created_at, domain=…)` | — | [src](../../../core/runtime/db_private_brain.py#L88) |
| function | `list_private_brain_records` | `(*, limit=…, session_id=…, status=…)` | — | [src](../../../core/runtime/db_private_brain.py#L124) |
| function | `search_private_brain_records` | `(query, *, limit=…, exclude_status=…)` | Tekst-søgning (LIKE) over HELE private_brain_records — focus/summary/detail. | [src](../../../core/runtime/db_private_brain.py#L153) |
| function | `update_private_brain_record_status` | `(record_id, *, status, updated_at)` | Lifecycle-overgang (active|settling|fading|released). Non-destruktiv. | [src](../../../core/runtime/db_private_brain.py#L200) |
| function | `get_private_brain_record` | `(record_id)` | — | [src](../../../core/runtime/db_private_brain.py#L217) |
| function | `update_private_brain_record_salience` | `(record_id, salience)` | Sæt salience (0.0–1.0) for en private-brain-record. | [src](../../../core/runtime/db_private_brain.py#L237) |
| function | `get_salient_private_brain_records` | `(threshold=…, limit=…)` | Aktive records med salience >= threshold, salience-sorteret. | [src](../../../core/runtime/db_private_brain.py#L249) |
| function | `decay_private_brain_records` | `(decay_rate=…, limit=…)` | Reducér salience på gamle aktive records. Returnerer antal opdaterede. | [src](../../../core/runtime/db_private_brain.py#L272) |
| function | `decay_private_brain_records_by_domain` | `(domain_decay_rates, default_rate=…, limit=…)` | Per-domæne salience-decay på aktive records. Returnerer {domæne: antal}. | [src](../../../core/runtime/db_private_brain.py#L293) |

## `core/runtime/db_private_notes.py`
_Persistence for the private/protected inner-layer note tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_private_notes_tables` | `(conn)` | — | [src](../../../core/runtime/db_private_notes.py#L15) |
| function | `_ensure_private_inner_note_columns` | `(conn)` | — | [src](../../../core/runtime/db_private_notes.py#L75) |
| function | `_ensure_enriched_columns` | `(conn)` | Add enriched column to private layer tables if missing. | [src](../../../core/runtime/db_private_notes.py#L91) |
| function | `record_private_inner_note` | `(*, note_id, source, run_id, work_id, status, note_kind, focus, uncertainty, identity_alignment, work_signal, private_summary, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L100) |
| function | `update_private_inner_note_enriched` | `(*, run_id, enriched_summary)` | Replace template summary with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L154) |
| function | `recent_private_inner_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L164) |
| function | `record_private_growth_note` | `(*, record_id, source, run_id, work_id, learning_kind, lesson, mistake_signal, helpful_signal, identity_signal, confidence, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L206) |
| function | `update_private_growth_note_enriched` | `(*, run_id, enriched_lesson, enriched_helpful_signal)` | Replace template lesson and helpful_signal with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L257) |
| function | `recent_private_growth_notes` | `(limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L269) |
| function | `record_protected_inner_voice` | `(*, voice_id, source, run_id, work_id, mood_tone, self_position, current_concern, current_pull, voice_line, created_at)` | — | [src](../../../core/runtime/db_private_notes.py#L309) |
| function | `update_protected_inner_voice_enriched` | `(*, run_id, enriched_voice_line)` | Replace template voice_line with LLM-enriched text. | [src](../../../core/runtime/db_private_notes.py#L357) |
| function | `get_protected_inner_voice` | `()` | — | [src](../../../core/runtime/db_private_notes.py#L367) |
| function | `list_recent_protected_inner_voices` | `(*, limit=…)` | — | [src](../../../core/runtime/db_private_notes.py#L403) |

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
| function | `record_private_retained_memory_record` | `(*, record_id, source, run_id, work_id, retained_value, retained_kind, retention_scope, retention_horizon, confidence, created_at)` | — | [src](../../../core/runtime/db_private_signals.py#L393) |
| function | `update_private_retained_memory_record_enriched` | `(*, run_id, enriched_value)` | Replace template retained_value with LLM-enriched lesson text. | [src](../../../core/runtime/db_private_signals.py#L441) |
| function | `get_private_retained_memory_record` | `()` | — | [src](../../../core/runtime/db_private_signals.py#L453) |
| function | `recent_private_retained_memory_records` | `(limit=…)` | — | [src](../../../core/runtime/db_private_signals.py#L489) |

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

