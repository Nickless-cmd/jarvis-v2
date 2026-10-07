# `core.services.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/auto_remember_subscriber.py`
_Auto-remember subscriber — closes cross-session memory loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_SkipMemoryShadow` | `` | Sentinel: spring den valgfrie memory_write_policy-shadow over (ingen brugerkontekst). | [src](../../../core/services/auto_remember_subscriber.py#L43) |
| function | `_is_trivial_user_turn` | `(text)` | True hvis user-beskeden er en ren acknowledgment uden nyt indhold. | [src](../../../core/services/auto_remember_subscriber.py#L75) |
| function | `_is_trivial_assistant_turn` | `(text)` | True hvis assistant-svaret er en kort acknowledgment uden indhold. | [src](../../../core/services/auto_remember_subscriber.py#L94) |
| function | `_connect` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L112) |
| function | `_parse_json_loose` | `(text)` | Find første gyldige JSON-objekt i tekst. Robust over for LLM | [src](../../../core/services/auto_remember_subscriber.py#L160) |
| function | `evaluate_turn_for_memory` | `(user_text, assistant_text)` | Spørg cheap LLM: "skal denne tur gemmes?" | [src](../../../core/services/auto_remember_subscriber.py#L191) |
| function | `_find_preceding_user_text` | `(session_id, before_message_id)` | Find seneste user-besked i session FØR den givne assistant-besked. | [src](../../../core/services/auto_remember_subscriber.py#L275) |
| function | `_process_visible_assistant_turn` | `(payload)` | Evaluér én assistant-tur og kald remember_this hvis salient. | [src](../../../core/services/auto_remember_subscriber.py#L309) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — samme pattern som metacognition_signal_tracker. | [src](../../../core/services/auto_remember_subscriber.py#L398) |
| function | `start_auto_remember_subscriber` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/auto_remember_subscriber.py#L440) |
| function | `stop_auto_remember_subscriber` | `()` | — | [src](../../../core/services/auto_remember_subscriber.py#L457) |

## `core/services/automation_dsl.py`
_Automation DSL — declarative triggers → actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L33) |
| class | `ActionSpec` | `` | — | [src](../../../core/services/automation_dsl.py#L39) |
| class | `AutomationDSL` | `` | — | [src](../../../core/services/automation_dsl.py#L47) |
| class | `AutomationDSLValidationError` | `` | — | [src](../../../core/services/automation_dsl.py#L56) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/automation_dsl.py#L67) |
| function | `_load` | `()` | — | [src](../../../core/services/automation_dsl.py#L71) |
| function | `_save` | `(items)` | — | [src](../../../core/services/automation_dsl.py#L85) |
| function | `validate_automation` | `(raw)` | Validate and construct an AutomationDSL from a raw dict. | [src](../../../core/services/automation_dsl.py#L97) |
| function | `register_automation` | `(dsl)` | Persist an AutomationDSL. Returns automation_id. | [src](../../../core/services/automation_dsl.py#L154) |
| function | `deactivate_automation` | `(automation_id)` | — | [src](../../../core/services/automation_dsl.py#L180) |
| function | `list_automations` | `(*, status=…)` | — | [src](../../../core/services/automation_dsl.py#L190) |
| function | `_expire_due` | `()` | Mark expired automations as inactive. Returns count of newly expired. | [src](../../../core/services/automation_dsl.py#L197) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — expire due automations, no other side-effects here. | [src](../../../core/services/automation_dsl.py#L222) |
| function | `build_automation_dsl_surface` | `()` | — | [src](../../../core/services/automation_dsl.py#L228) |
| function | `_emit_automation_dsl_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/automation_dsl.py#L257) |

## `core/services/autonomous_goals.py`
_Autonomous goals — persistent top-level goals with decomposition._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm_title` | `(title)` | Normalisér til dedup: trim, lowercase, kollaps whitespace, cap 200. | [src](../../../core/services/autonomous_goals.py#L35) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_goals.py#L40) |
| function | `_save` | `(goals)` | — | [src](../../../core/services/autonomous_goals.py#L47) |
| function | `_now` | `()` | — | [src](../../../core/services/autonomous_goals.py#L51) |
| function | `create_goal` | `(*, title, description=…, parent_id=…, priority=…, source=…)` | Create a new goal. Returns the created entry. | [src](../../../core/services/autonomous_goals.py#L55) |
| function | `update_goal_status` | `(goal_id, new_status)` | — | [src](../../../core/services/autonomous_goals.py#L108) |
| function | `list_goals` | `(*, status=…, priority=…, parent_id=…, limit=…)` | List goals matching filters. parent_id='any' = no filter, None = top-level only. | [src](../../../core/services/autonomous_goals.py#L129) |
| function | `decompose_goal` | `(goal_id)` | Use cheap-lane LLM to split a goal into 3-5 concrete sub-goals. | [src](../../../core/services/autonomous_goals.py#L150) |
| function | `goals_prompt_section` | `()` | Awareness section listing active high-priority goals. | [src](../../../core/services/autonomous_goals.py#L214) |
| function | `_exec_goal_create` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L231) |
| function | `_exec_goal_list` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L241) |
| function | `_exec_goal_decompose` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L251) |
| function | `_exec_goal_update_status` | `(args)` | — | [src](../../../core/services/autonomous_goals.py#L255) |

## `core/services/autonomous_lease.py`
_visible↔autonomous mutual-exclusion lease (marker-default)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `(now_ts)` | — | [src](../../../core/services/autonomous_lease.py#L37) |
| function | `acquire_visible` | `(ttl_s=…, now_ts=…)` | Visible lane claims the lease for ``ttl_s`` seconds (fail-open). | [src](../../../core/services/autonomous_lease.py#L41) |
| function | `release_visible` | `()` | Visible lane releases the lease (fail-open). | [src](../../../core/services/autonomous_lease.py#L52) |
| function | `visible_active` | `(now_ts=…)` | True if a visible lease is currently held and not expired (fail-open). | [src](../../../core/services/autonomous_lease.py#L60) |
| function | `_read_markers` | `()` | — | [src](../../../core/services/autonomous_lease.py#L75) |
| function | `_write_markers` | `(markers)` | — | [src](../../../core/services/autonomous_lease.py#L85) |
| function | `pending_markers` | `()` | Read (without draining) the deferred autonomous markers. | [src](../../../core/services/autonomous_lease.py#L92) |
| function | `consume_markers` | `()` | Read AND drain the deferred markers (a second call returns empty). | [src](../../../core/services/autonomous_lease.py#L97) |
| function | `try_autonomous_dispatch` | `(payload, now_ts=…, *, scope=…, session_id=…, control_plane=…)` | Gate an autonomous dispatch against the visible lane. | [src](../../../core/services/autonomous_lease.py#L105) |
| function | `_resolve_role` | `(user_id, role)` | Resolve the member role, preferring an explicit ``role``. | [src](../../../core/services/autonomous_lease.py#L149) |
| function | `nudge_allowed_for` | `(marker, *, user_id=…, session_id=…, role=…)` | Role- AND session-gate: may this nudge surface for this user/session? | [src](../../../core/services/autonomous_lease.py#L170) |
| function | `markers_for` | `(*, user_id=…, session_id=…, role=…, drain=…)` | Return the deferred markers this user/session/role is allowed to see. | [src](../../../core/services/autonomous_lease.py#L213) |

## `core/services/autonomous_outreach_daemon.py`
_Autonomous Outreach Daemon — Jarvis reaches out on his own initiative._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L39) |
| function | `_load_log` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L43) |
| function | `_save_log` | `(items)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L57) |
| function | `_last_outreach_sent` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L71) |
| function | `_is_quiet_hours` | `(now_local)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L81) |
| function | `_hours_since_last_user_contact` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L87) |
| function | `_gather_interesting_events` | `()` | Collect potentially noteworthy signals from other services. | [src](../../../core/services/autonomous_outreach_daemon.py#L112) |
| function | `_compose_message` | `(events)` | Build a concrete, value-carrying outreach message from events. | [src](../../../core/services/autonomous_outreach_daemon.py#L177) |
| function | `_highest_priority` | `(events)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L189) |
| function | `_log_decision` | `(*, outcome, reason, events=…, message=…, priority=…, channel=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L196) |
| function | `_owner_uid` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L218) |
| function | `_send_outreach` | `(message, *, priority=…)` | Deliver outreach via the canonical proactive router — device-aware | [src](../../../core/services/autonomous_outreach_daemon.py#L226) |
| function | `attempt_outreach` | `()` | Consider whether to reach out, do so if appropriate. Returns decision dict. | [src](../../../core/services/autonomous_outreach_daemon.py#L252) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — evaluate outreach candidacy. | [src](../../../core/services/autonomous_outreach_daemon.py#L347) |
| function | `recent_log` | `(*, limit=…)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L356) |
| function | `build_autonomous_outreach_surface` | `()` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L360) |
| function | `_surface_summary` | `(sent, skipped, last)` | — | [src](../../../core/services/autonomous_outreach_daemon.py#L378) |

## `core/services/autonomous_run_digest.py`
_Referat af en autonom koersel — kort, i hans egen samtale._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_slags_af` | `(session_id)` | — | [src](../../../core/services/autonomous_run_digest.py#L55) |
| function | `_foerste_afsnit` | `(tekst)` | Hans egen konklusion, ikke hele udskriften. | [src](../../../core/services/autonomous_run_digest.py#L63) |
| function | `_pænt_vaerktoej` | `(navn)` | — | [src](../../../core/services/autonomous_run_digest.py#L80) |
| function | `byg_referat` | `(*, session_id, tool_calls=…, output=…, aendrede_filer=…, committet=…)` | Referatet, eller tom streng hvis der ikke er noget at fortaelle. | [src](../../../core/services/autonomous_run_digest.py#L84) |
| function | `post_referat` | `(*, run_id, session_id, tool_calls=…, output=…, aendrede_filer=…, committet=…)` | Skriv referatet i hans sidst aktive samtale. Returnerer session_id ('' = intet skrevet). | [src](../../../core/services/autonomous_run_digest.py#L121) |

## `core/services/autonomous_run_failures.py`
_Fejlede autonome kørsler — set af Jarvis selv, ikke gemt i hans mund._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L45) |
| function | `_kv_get` | `(default)` | — | [src](../../../core/services/autonomous_run_failures.py#L49) |
| function | `_kv_set` | `(value)` | — | [src](../../../core/services/autonomous_run_failures.py#L58) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L66) |
| function | `record_failure` | `(*, run_id, session_id=…, origin=…, provider=…, model=…, detail=…, kind=…)` | Journalisér at en autonom kørsel mislykkedes. Kaster aldrig. | [src](../../../core/services/autonomous_run_failures.py#L76) |
| function | `recent_failures` | `(limit=…)` | Nyeste først. | [src](../../../core/services/autonomous_run_failures.py#L109) |
| function | `_within_window` | `(post, hours)` | — | [src](../../../core/services/autonomous_run_failures.py#L114) |
| function | `request_retry` | `(failure_id)` | Marker at HAN vil forsøge igen. Runtime gør det ikke af sig selv. | [src](../../../core/services/autonomous_run_failures.py#L124) |
| function | `pending_retries` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L137) |
| function | `mark_retried` | `(failure_id)` | — | [src](../../../core/services/autonomous_run_failures.py#L141) |
| function | `clear` | `()` | — | [src](../../../core/services/autonomous_run_failures.py#L149) |
| function | `prompt_section` | `()` | Blokken Jarvis ser. Tom streng når der intet er at vide. | [src](../../../core/services/autonomous_run_failures.py#L153) |

## `core/services/autonomous_sessions.py`
_Autonome sessioner — rotér pr. oprindelse+dag, og gør historien synlig._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_origin` | `(origin)` | — | [src](../../../core/services/autonomous_sessions.py#L35) |
| function | `_today` | `()` | — | [src](../../../core/services/autonomous_sessions.py#L40) |
| function | `resolve_autonomous_session` | `(origin)` | Returnér (opret idempotent) sessionen for (oprindelse, i dag). | [src](../../../core/services/autonomous_sessions.py#L44) |
| function | `_origin_of_session` | `(session_id)` | Udled oprindelse fra et ``auto-{origin}-{dato}``-id. | [src](../../../core/services/autonomous_sessions.py#L63) |
| function | `build_autonomous_history_surface` | `(*, days=…, per_origin_limit=…)` | Projicér den autonome historie for owner-visning (§24.4-sikker). | [src](../../../core/services/autonomous_sessions.py#L73) |

## `core/services/autonomous_stream_run.py`
_Server-authoritative streaming lifecycle for autonomous visible runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_autonomous_stream_run` | `(message, *, session_id, origin=…)` | Start autonomous work and relay its v2 frames through ``run_event_log``. | [src](../../../core/services/autonomous_stream_run.py#L9) |

## `core/services/autonomous_supervisor.py`
_Autonom run-supervision (#3) — Centralen følger HVERT autonomt run, korrelerer det på tværs_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supervise` | `(run_id, outcome, error=…)` | Vurdér ét autonomt run. outcome ∈ {completed, failed, interrupted}. Returnér verdict + | [src](../../../core/services/autonomous_supervisor.py#L23) |

## `core/services/autonomous_work_daemon.py`
_Autonomous Work Daemon — Jarvis works on his own when Bjørn is away._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L48) |
| function | `_load` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L52) |
| function | `_save` | `(items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L66) |
| function | `_proposals_last_hour` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L80) |
| function | `_is_low_activity` | `()` | Low-activity = no visible runs in last _LOW_ACTIVITY_MINUTES. | [src](../../../core/services/autonomous_work_daemon.py#L96) |
| function | `_pending_initiatives` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L117) |
| function | `_log_entry` | `(entry)` | — | [src](../../../core/services/autonomous_work_daemon.py#L125) |
| function | `_file_proposal` | `(*, proposal_type, title, details, rationale)` | Record a work proposal for later execution/approval. | [src](../../../core/services/autonomous_work_daemon.py#L131) |
| function | `_maybe_propose_memory_consolidate` | `()` | Propose a daily memory consolidation when ~end of day locally. | [src](../../../core/services/autonomous_work_daemon.py#L169) |
| function | `_maybe_nudge_incubator` | `()` | If incubator is sparse, nudge creative_instinct to generate. | [src](../../../core/services/autonomous_work_daemon.py#L189) |
| function | `_maybe_propose_research` | `()` | Pick one maturing incubator seed and propose a research topic for it. | [src](../../../core/services/autonomous_work_daemon.py#L213) |
| function | `_plan_once` | `()` | Run planning passes and return list of created proposal_ids. | [src](../../../core/services/autonomous_work_daemon.py#L231) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L253) |
| function | `list_proposals` | `(*, status=…, limit=…)` | — | [src](../../../core/services/autonomous_work_daemon.py#L268) |
| function | `resolve_proposal` | `(proposal_id, *, outcome, note=…)` | Close a proposal. outcome in {'approved', 'rejected', 'completed'}. | [src](../../../core/services/autonomous_work_daemon.py#L275) |
| function | `build_autonomous_work_surface` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L291) |
| function | `_surface_summary` | `(pending, all_items)` | — | [src](../../../core/services/autonomous_work_daemon.py#L310) |
| function | `build_autonomous_work_prompt_section` | `()` | — | [src](../../../core/services/autonomous_work_daemon.py#L318) |

## `core/services/autonomy_budget.py`
_Dagligt budget for selvvalgte handlinger + tælling af stilheden (blok E, 4/9)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_get` | `(key, default=…)` | — | [src](../../../core/services/autonomy_budget.py#L41) |
| function | `_state_set` | `(key, value)` | — | [src](../../../core/services/autonomy_budget.py#L50) |
| function | `daily_budget` | `()` | — | [src](../../../core/services/autonomy_budget.py#L58) |
| function | `set_daily_budget` | `(value)` | — | [src](../../../core/services/autonomy_budget.py#L65) |
| function | `_today` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L71) |
| function | `_spent_today` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L75) |
| function | `remaining` | `(now=…)` | — | [src](../../../core/services/autonomy_budget.py#L86) |
| function | `may_act` | `(action=…, *, now=…)` | Er der plads i dagens budget? Fail-open: enhver fejl → ja. | [src](../../../core/services/autonomy_budget.py#L90) |
| function | `note_action` | `(action, *, now=…)` | Registrér en selvvalgt handling. Synlig log, ikke en tavs bremse. | [src](../../../core/services/autonomy_budget.py#L102) |
| function | `note_silence` | `(*, outcome, reason_code=…)` | Han valgte at tie. Tæl det — det er den eneste måde vægten kan vurderes. | [src](../../../core/services/autonomy_budget.py#L122) |
| function | `silence_counts` | `()` | — | [src](../../../core/services/autonomy_budget.py#L135) |
| function | `build_weekly_summary` | `()` | Ugens stilhed i én linje — "" når han ikke har tiet nævneværdigt. | [src](../../../core/services/autonomy_budget.py#L142) |
| function | `run_weekly_review` | `(*, force=…, now=…)` | Ugentligt: læg stilheds-resuméet i den proaktive kø og nulstil tælleren. | [src](../../../core/services/autonomy_budget.py#L161) |
| function | `build_autonomy_budget_surface` | `()` | — | [src](../../../core/services/autonomy_budget.py#L190) |

## `core/services/autonomy_pressure_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_autonomy_pressure_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L60) |
| function | `refresh_runtime_autonomy_pressure_signal_statuses` | `()` | Mark signals as stale based on multiple criteria. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L83) |
| function | `retire_autonomy_pressure_signal` | `(signal_id, *, reason=…)` | Explicitly retire/close an autonomy pressure signal. | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L143) |
| function | `build_runtime_autonomy_pressure_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L170) |
| function | `_extract_autonomy_pressure_candidates` | `()` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L213) |
| function | `_persist_autonomy_pressure_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L549) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L613) |
| function | `_candidate` | `(*, pressure_type, pressure_state, weight, confidence, title, summary, rationale, source_anchor, evidence_summary, support_summary, support_count, session_count, status_reason)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L645) |
| function | `_source_anchor` | `(surface, *, fallback)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L684) |
| function | `_question_continuity_support` | `(*, relation, meaning, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L693) |
| function | `_initiative_loop_question_support` | `(*, open_loops, initiative, regulation, awareness, witness, chronicle, attachment, loyalty)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L734) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L826) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L835) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L843) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/autonomy_pressure_signal_tracking.py#L855) |

## `core/services/autonomy_proposal_queue.py`
_Autonomy proposal queue — Niveau 2 fundament._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_proposal_executor` | `(kind, fn)` | Register an executor for a proposal kind. | [src](../../../core/services/autonomy_proposal_queue.py#L49) |
| function | `get_registered_proposal_kinds` | `()` | — | [src](../../../core/services/autonomy_proposal_queue.py#L54) |
| function | `file_proposal` | `(*, kind, title, rationale=…, payload=…, created_by=…, session_id=…, run_id=…, tick_id=…, canonical_key=…)` | File a new proposal in the queue. | [src](../../../core/services/autonomy_proposal_queue.py#L58) |
| function | `_notify_discord_proposal` | `(proposal_id, kind, title)` | Send a DM to the owner when a proposal is filed — fire and forget. | [src](../../../core/services/autonomy_proposal_queue.py#L109) |
| function | `list_pending_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L155) |
| function | `list_recent_proposals` | `(*, limit=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L159) |
| function | `approve_proposal` | `(proposal_id, *, resolution_note=…)` | Bjørn approves a proposal — execute it immediately if we have an | [src](../../../core/services/autonomy_proposal_queue.py#L163) |
| function | `reject_proposal` | `(proposal_id, *, resolution_note=…)` | — | [src](../../../core/services/autonomy_proposal_queue.py#L279) |
| function | `build_autonomy_proposal_surface` | `(*, limit=…)` | MC-friendly view of the proposal queue. | [src](../../../core/services/autonomy_proposal_queue.py#L309) |
| function | `_execute_memory_rewrite_proposal` | `(payload)` | Execute an approved memory-rewrite proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L332) |
| function | `_execute_source_edit_proposal` | `(payload)` | Execute an approved source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L357) |
| function | `_auto_commit_after_source_edit` | `(proposal, result)` | Auto-commit the file changed by a source-edit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L441) |
| function | `_execute_git_commit_proposal` | `(payload)` | Execute an approved git-commit proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L532) |
| function | `_execute_instrument_fix_proposal` | `(payload)` | Execute an approved instrument_fix proposal. | [src](../../../core/services/autonomy_proposal_queue.py#L635) |

## `core/services/avoidance_detector.py`
_Avoidance Detector — unbidden self-observation of patterns over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens_from_title` | `(title)` | — | [src](../../../core/services/avoidance_detector.py#L37) |
| function | `_cluster_key` | `(title)` | Pick a short cluster key from the first meaningful keyword(s). | [src](../../../core/services/avoidance_detector.py#L45) |
| function | `_parse_ts` | `(value)` | — | [src](../../../core/services/avoidance_detector.py#L54) |
| function | `_gather_signals` | `()` | Pull goal/dream/focus signals with common shape. | [src](../../../core/services/avoidance_detector.py#L63) |
| function | `detect_avoidances` | `()` | Identify clusters with real prior support that have gone silent. | [src](../../../core/services/avoidance_detector.py#L108) |
| function | `build_avoidance_surface` | `()` | — | [src](../../../core/services/avoidance_detector.py#L161) |
| function | `_surface_summary` | `(findings)` | — | [src](../../../core/services/avoidance_detector.py#L175) |
| function | `build_avoidance_prompt_section` | `()` | Only speaks when there's a real pattern to notice. | [src](../../../core/services/avoidance_detector.py#L185) |

## `core/services/background_job_watch.py`
_Færdige baggrunds-shells — set, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/background_job_watch.py#L76) |
| function | `_laes_tid` | `(vaerdi)` | ISO-tidsstempel fra state eller registry — eller None. | [src](../../../core/services/background_job_watch.py#L80) |
| function | `_grundlinje` | `()` | Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang. | [src](../../../core/services/background_job_watch.py#L94) |
| function | `_rapporterede` | `()` | {noegle: iso-tidsstempel} for det vi allerede har sagt. | [src](../../../core/services/background_job_watch.py#L114) |
| function | `_husk` | `(noegler)` | Skriv noeglerne som rapporterede — atomisk, så api og runtime ikke | [src](../../../core/services/background_job_watch.py#L136) |
| function | `_noegle` | `(job)` | Stabil identitet for et job. | [src](../../../core/services/background_job_watch.py#L153) |
| function | `scan_finished` | `(*, uid)` | Nye fuldførte jobs siden sidst, plus om operator-siden var laesbar. | [src](../../../core/services/background_job_watch.py#L167) |
| function | `_beskriv` | `(job)` | — | [src](../../../core/services/background_job_watch.py#L211) |
| function | `_bruger_id` | `()` | Brugeren der ejer baggrunds-shellene. Tom streng når konteksten ikke | [src](../../../core/services/background_job_watch.py#L222) |
| function | `_sekunder_siden` | `(sidste)` | Sekunder siden forrige tjek — eller None når stemplet mangler eller er | [src](../../../core/services/background_job_watch.py#L237) |
| function | `tik` | `(*, uid=…)` | Tjek for færdige jobs og læg én followup. Kaster aldrig. | [src](../../../core/services/background_job_watch.py#L247) |

## `core/services/background_jobs.py`
_Alle kørende baggrundsopgaver — uanset hvor de kører._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/background_jobs.py#L100) |
| function | `_operator_jobs` | `(uid, exec_fn)` | Baggrunds-shells på operatørens maskine. Tom liste hvis broen tier. | [src](../../../core/services/background_jobs.py#L104) |
| class | `BroTier` | `` | Broen svarede ikke — vi VED ikke hvad der kører på operatørens maskine. | [src](../../../core/services/background_jobs.py#L150) |
| function | `_tal` | `(v)` | — | [src](../../../core/services/background_jobs.py#L154) |
| function | `_sekunder` | `(v)` | Sekunder der kan komme som float. | [src](../../../core/services/background_jobs.py#L161) |
| function | `_supervisor_jobs` | `()` | — | [src](../../../core/services/background_jobs.py#L175) |
| function | `_iso_ts` | `(v)` | — | [src](../../../core/services/background_jobs.py#L210) |
| function | `_scout_jobs` | `()` | Scout-agenter der kører — og dem der blev færdige den seneste time. | [src](../../../core/services/background_jobs.py#L217) |
| function | `_tool_jobs` | `()` | Værktøjskald fra et model-run — dem der kører lige nu. | [src](../../../core/services/background_jobs.py#L269) |
| function | `_default_bash_sid` | `()` | Id'et på den DELTE shell som det almindelige `bash`-værktøj bruger. | [src](../../../core/services/background_jobs.py#L391) |
| function | `_shell_kort` | `(sid, *, egen_maskine, idle, cwd=…, arbejds_shell=…, koerer=…, titel=…)` | Ét kort for en åben shell — samme form som de øvrige kilder. | [src](../../../core/services/background_jobs.py#L414) |
| function | `_lokale_shell_sessioner` | `()` | Åbne `bash_session`-shells — KUN hvis daemonen allerede kører. | [src](../../../core/services/background_jobs.py#L470) |
| function | `_operator_shell_sessioner` | `()` | Åbne `operator_bash_session`-shells på Bjørns maskine. | [src](../../../core/services/background_jobs.py#L531) |
| function | `_shell_sessioner` | `()` | Begge slags åbne shells. Den ene kilde må ikke kunne tie den anden. | [src](../../../core/services/background_jobs.py#L562) |
| function | `liste` | `(*, uid=…, exec_fn=…, kun_aktive=…)` | Alle jobs fra alle kilder. | [src](../../../core/services/background_jobs.py#L575) |
| function | `_skal_vises` | `(job)` | Kører den, eller gik den galt? | [src](../../../core/services/background_jobs.py#L613) |

## `core/services/background_resume.py`
_Turen maa ikke slutte mens en baggrunds-shell stadig producerer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/background_resume.py#L43) |
| function | `_save` | `(state)` | — | [src](../../../core/services/background_resume.py#L52) |
| function | `note_started` | `(session_id, shell_id)` | Husk at DENNE session har startet den shell. Self-safe. | [src](../../../core/services/background_resume.py#L60) |
| function | `forget_session` | `(session_id)` | Ryd op naar en session er faerdig, saa staten ikke vokser uendeligt. | [src](../../../core/services/background_resume.py#L75) |
| function | `tracked` | `(session_id)` | — | [src](../../../core/services/background_resume.py#L85) |
| function | `build_note` | `(deltas)` | Systemnoten der faar Jarvis til at forholde sig til det nye output. Ren. | [src](../../../core/services/background_resume.py#L89) |
| function | `_sig_til_hvis_lang` | `(shell, sidste_output)` | Push besked hvis shellen koerte >= 30 s. Self-safe: fejl → tavshed. | [src](../../../core/services/background_resume.py#L116) |
| function | `poll_async` | `(session_id, user_id)` | Er der nyt fra sessionens baggrunds-shells? Returnerer en note, ellers "". | [src](../../../core/services/background_resume.py#L137) |

## `core/services/baggrundsjob_vagt.py`
_Et faerdigt baggrundsjob melder sig selv — i inboxen, eller med en vaekning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu_iso` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L62) |
| function | `_hent_state` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L66) |
| function | `_gem_state` | `(state)` | — | [src](../../../core/services/baggrundsjob_vagt.py#L78) |
| function | `_bro` | `(navn, args)` | Bro-kald til operatoerens maskine. Egen funktion, saa testen har en soem. | [src](../../../core/services/baggrundsjob_vagt.py#L88) |
| function | `_ejer_uid` | `()` | — | [src](../../../core/services/baggrundsjob_vagt.py#L94) |
| function | `_varighed` | `(sekunder)` | — | [src](../../../core/services/baggrundsjob_vagt.py#L102) |
| function | `beskedtekst` | `(job)` | Én linje der kan staa alene i en inbox. Udfaldet FOERST — det er det der | [src](../../../core/services/baggrundsjob_vagt.py#L116) |
| function | `_meld` | `(job)` | Levér meldingen. Returnerer (leveret, hvordan). | [src](../../../core/services/baggrundsjob_vagt.py#L138) |
| function | `tick_baggrundsjob_vagt` | `(*, trigger=…, last_visible_at=…)` | Kadence-producer: meld hvert nyligt afsluttet baggrundsjob ÉN gang. | [src](../../../core/services/baggrundsjob_vagt.py#L182) |

## `core/services/bash_sandbox.py`
_bwrap-indespærring om én bash-kommando. SLUKKET som standard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_conda_rod` | `(sti)` | Base-installationen bag et conda-env: `<rod>/envs/<navn>` → `<rod>`. | [src](../../../core/services/bash_sandbox.py#L65) |
| function | `_python_roedder` | `()` | Tolkens EGEN rod — oploest gennem symlinks. | [src](../../../core/services/bash_sandbox.py#L77) |
| function | `_runtime_hjem` | `()` | Jarvis' runtime-hjem, hvis det findes. | [src](../../../core/services/bash_sandbox.py#L103) |
| function | `is_available` | `()` | Findes bwrap på DENNE maskine? | [src](../../../core/services/bash_sandbox.py#L122) |
| function | `kan_koere` | `(*, tving=…)` | Kan bwrap FAKTISK starte her? (svar, grund) | [src](../../../core/services/bash_sandbox.py#L138) |
| function | `is_enabled` | `()` | Eksplicit tændt? Usat betyder SLUKKET — modsat central_switches' default. | [src](../../../core/services/bash_sandbox.py#L213) |
| function | `set_enabled` | `(on)` | — | [src](../../../core/services/bash_sandbox.py#L223) |
| function | `status` | `()` | Tilstanden — og «findes» holdes adskilt fra «kører». | [src](../../../core/services/bash_sandbox.py#L230) |
| function | `wrap_bwrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | Byg argv'en. Ren funktion — tjekker hverken flag eller tilgængelighed. | [src](../../../core/services/bash_sandbox.py#L258) |
| function | `maybe_wrap` | `(command, cwd, *, writable_roots=…, allow_egress=…)` | argv hvis sandboxen er tændt OG mulig her — ellers None (kør normalt). | [src](../../../core/services/bash_sandbox.py#L284) |
| class | `ConfinementUnavailable` | `` | Der blev KRÆVET indespærring, og den kunne ikke leveres. | [src](../../../core/services/bash_sandbox.py#L339) |
| class | `Enforcement` | `` | Hvad der blev bedt om, og hvad der faktisk skete. | [src](../../../core/services/bash_sandbox.py#L344) |
| method | `Enforcement.honored` | `(self)` | Fik vi det vi bad om? | [src](../../../core/services/bash_sandbox.py#L355) |
| method | `Enforcement.as_dict` | `(self)` | — | [src](../../../core/services/bash_sandbox.py#L359) |
| function | `enforcement` | `(command, cwd, *, writable_roots=…, allow_egress=…, require=…)` | Afgør indespærringen OG rapportér den. Kaster kun når `require` er sat. | [src](../../../core/services/bash_sandbox.py#L365) |

## `core/services/behavioral_decisions.py`
_Behavioral decisions — closing the reflection→behavior loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_directive` | `(value)` | — | [src](../../../core/services/behavioral_decisions.py#L36) |
| function | `_commit_observe` | `(outcome, decision_id)` | Commit-cluster instrument: decision_create → central observe (best-effort). | [src](../../../core/services/behavioral_decisions.py#L40) |
| function | `_recently_revoked` | `(normalized)` | En revokeret beslutning med samme direktiv, revokeret for nylig. | [src](../../../core/services/behavioral_decisions.py#L62) |
| function | `_dedup_result` | `(existing, reason, source_type)` | Returnér den række der allerede dækker direktivet — uden at oprette. | [src](../../../core/services/behavioral_decisions.py#L73) |
| function | `create_decision` | `(*, directive, rationale=…, trigger_cue=…, priority=…, source_record_id=…, source_type=…, created_by=…)` | — | [src](../../../core/services/behavioral_decisions.py#L97) |
| function | `review_decision` | `(*, decision_id, verdict, note=…, evidence=…)` | — | [src](../../../core/services/behavioral_decisions.py#L145) |
| function | `update_decision` | `(decision_id, *, directive=…, rationale=…, trigger_cue=…, trigger_name=…, priority=…, status=…)` | Update a decision's mutable fields (None = unchanged, "" = cleared). | [src](../../../core/services/behavioral_decisions.py#L195) |
| function | `change_status` | `(decision_id, new_status)` | — | [src](../../../core/services/behavioral_decisions.py#L236) |
| function | `revoke_decision` | `(decision_id, *, reason=…)` | — | [src](../../../core/services/behavioral_decisions.py#L254) |
| function | `delete_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L272) |
| function | `get_decision` | `(decision_id)` | — | [src](../../../core/services/behavioral_decisions.py#L282) |
| function | `get_decision_with_reviews` | `(decision_id, *, review_limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L286) |
| function | `list_active_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L313) |
| function | `list_all_decisions` | `(*, limit=…)` | — | [src](../../../core/services/behavioral_decisions.py#L317) |
| function | `format_active_decisions_for_heartbeat` | `(*, max_items=…)` | Compact line of top active commitments for heartbeat injection. | [src](../../../core/services/behavioral_decisions.py#L321) |
| function | `get_stats` | `()` | — | [src](../../../core/services/behavioral_decisions.py#L340) |

## `core/services/besked_run_kobling.py`
_Hvilket run skrev denne besked? — så klienten ikke skal gætte ud fra prosa._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_laes` | `()` | — | [src](../../../core/services/besked_run_kobling.py#L84) |
| function | `noter` | `(message_id, run_id)` | Husk at ``run_id`` skrev ``message_id``. Self-safe: kaster aldrig. | [src](../../../core/services/besked_run_kobling.py#L91) |
| function | `run_for` | `(message_id)` | Run'et der skrev beskeden, eller "" hvis vi ikke ved det. | [src](../../../core/services/besked_run_kobling.py#L118) |
| function | `antal` | `()` | Hvor mange koblinger der huskes nu. Til test og diagnostik. | [src](../../../core/services/besked_run_kobling.py#L134) |
| function | `ryd` | `()` | Tøm kortet. Kun til test — ingen produktionsvej rydder det. | [src](../../../core/services/besked_run_kobling.py#L142) |

## `core/services/body_memory.py`
_Body Memory — Jarvis' kropslige erindringer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/body_memory.py#L51) |
| function | `_save` | `(snapshots)` | — | [src](../../../core/services/body_memory.py#L61) |
| function | `_fornemmelse` | `(fakta, belastning)` | Giver (ord, styrke, begrundelse) ud fra kroppens faktiske tal. | [src](../../../core/services/body_memory.py#L70) |
| function | `record_body_snapshot` | `(context, sensation=…, intensity=…)` | Gem en kropslig erindring. Kaster aldrig. | [src](../../../core/services/body_memory.py#L88) |
| function | `describe_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L124) |
| function | `format_body_for_prompt` | `()` | — | [src](../../../core/services/body_memory.py#L133) |
| function | `reset_body_memory` | `()` | — | [src](../../../core/services/body_memory.py#L138) |
| function | `build_body_memory_surface` | `()` | — | [src](../../../core/services/body_memory.py#L142) |
| function | `tick` | `(_seconds=…)` | Hjerteslags-krog: gem en erindring naar kroppen SKIFTER. | [src](../../../core/services/body_memory.py#L152) |

## `core/services/boredom_curiosity_bridge.py`
_Boredom to Curiosity Bridge — transforms boredom into curiosity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Curiosity` | `` | A curiosity that emerges from boredom. | [src](../../../core/services/boredom_curiosity_bridge.py#L23) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L49) |
| function | `_fra_raa` | `(raa)` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L53) |
| function | `_alder_s` | `(c, nu)` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L68) |
| function | `_levende` | `(cs, nu=…)` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L76) |
| function | `_synk` | `()` | Hent fra disk hvis filen er aendret siden sidste laesning. | [src](../../../core/services/boredom_curiosity_bridge.py#L81) |
| function | `_gem` | `()` | — | [src](../../../core/services/boredom_curiosity_bridge.py#L111) |
| function | `add_boredom` | `(duration)` | Add boredom based on elapsed duration. | [src](../../../core/services/boredom_curiosity_bridge.py#L124) |
| function | `_spawn_curiosity` | `()` | Spawn a curiosity when boredom is high enough. | [src](../../../core/services/boredom_curiosity_bridge.py#L185) |
| function | `should_spawn_curiosity` | `()` | Check if curiosity should spawn based on boredom level. | [src](../../../core/services/boredom_curiosity_bridge.py#L225) |
| function | `get_curiosity_prompt` | `()` | Get the most relevant curiosity prompt. | [src](../../../core/services/boredom_curiosity_bridge.py#L231) |
| function | `get_active_curiosities` | `()` | Get all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L242) |
| function | `clear_curiosities` | `()` | Clear all active curiosities. | [src](../../../core/services/boredom_curiosity_bridge.py#L257) |
| function | `reset_boredom_curiosity_bridge` | `()` | Reset boredom curiosity bridge state (for testing). | [src](../../../core/services/boredom_curiosity_bridge.py#L266) |
| function | `get_boredom_curiosity_state` | `()` | Get current state of boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L279) |
| function | `build_boredom_curiosity_bridge_surface` | `()` | Build MC surface for boredom curiosity bridge. | [src](../../../core/services/boredom_curiosity_bridge.py#L290) |

## `core/services/boredom_engine.py`
_Boredom Engine — productive restlessness as first-class experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_boredom_state` | `(*, idle_hours=…, tick_monotony=…, novelty_score=…, open_loop_count=…)` | — | [src](../../../core/services/boredom_engine.py#L11) |
| function | `get_boredom_state` | `()` | — | [src](../../../core/services/boredom_engine.py#L49) |
| function | `build_boredom_surface` | `()` | — | [src](../../../core/services/boredom_engine.py#L53) |

## `core/services/boundary_awareness.py`
_Boundary Awareness — "Where do I end?"_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_boundary_model` | `()` | Build Jarvis' sense of his own boundaries. | [src](../../../core/services/boundary_awareness.py#L8) |
| function | `format_boundary_for_prompt` | `()` | Compact boundary awareness for prompt injection. | [src](../../../core/services/boundary_awareness.py#L31) |
| function | `build_boundary_awareness_surface` | `()` | — | [src](../../../core/services/boundary_awareness.py#L40) |

## `core/services/bounded_action_continuity_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface=…)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L12) |
| function | `_derive_current_action_continuity_surface` | `(tool_intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L40) |
| function | `_derive_followup_from_awareness` | `(*, execution_state, action_type, action_target, awareness_surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L143) |
| function | `_derive_continuity_state` | `(*, execution_state, followup_state)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L243) |
| function | `_continuity_id` | `(*, action_type, action_target, action_summary, action_outcome, approval_resolved_at, approval_source)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L267) |
| function | `_default_action_continuity_surface` | `()` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L291) |
| function | `_normalize_action_continuity_surface` | `(surface)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L323) |
| function | `_merge_unique` | `(left, right)` | — | [src](../../../core/services/bounded_action_continuity_runtime.py#L337) |

## `core/services/bounded_mutation_intent_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_mutation_intent_surface` | `(intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L25) |
| function | `_build_write_proposal_surface` | `(*, classification, mutation_near, intent_state, intent_type, approval_scope, target_files, target_paths, repo_scope, system_scope, sudo_required, mutation_critical)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L127) |
| function | `_derive_write_proposal_confidence` | `(*, proposal_type, target_files, repo_scope, system_scope)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L224) |
| function | `_write_proposal_reason` | `(*, proposal_type, approval_scope, target_files, repo_scope, system_scope, sudo_required, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L240) |
| function | `_derive_classification` | `(*, intent_state, intent_type, approval_scope, awareness_surface, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L275) |
| function | `_derive_targets` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L310) |
| function | `_derive_repo_mutation_scope` | `(*, classification, approval_scope, repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L327) |
| function | `_derive_system_mutation_scope` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L342) |
| function | `_derive_sudo_required` | `(*, classification, approval_scope, intent_type)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L355) |
| function | `_derive_deleted_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L367) |
| function | `_derive_modified_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L371) |
| function | `_derive_untracked_paths` | `(repo_observation)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L375) |
| function | `_bounded_path_list` | `(value)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L379) |
| function | `_approval_required_mutation_capability_summary` | `()` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L385) |
| function | `_unique` | `(values)` | — | [src](../../../core/services/bounded_mutation_intent_runtime.py#L403) |

## `core/services/bounded_repo_tools_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_repo_tool_execution_surface` | `(intent_surface, *, awareness_surface=…)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L14) |
| function | `_build_bounded_repo_tool_execution_surface` | `(intent_surface, *, awareness_surface)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L40) |
| function | `_allowed_operation` | `(intent_type)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L145) |
| function | `_inspect_repo_status` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L175) |
| function | `_inspect_working_tree` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L198) |
| function | `_inspect_local_changes` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L219) |
| function | `_inspect_upstream_divergence` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L236) |
| function | `_request_bounded_diagnostic` | `(*, repo_root, intent_target)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L268) |
| function | `_git_status_observation` | `(repo_root)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L293) |
| function | `_run_git_command` | `(repo_root, args)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L374) |
| function | `_trim_lines` | `(value)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L392) |
| function | `_safe_int` | `(value)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L396) |
| function | `_merge_unique` | `(primary, secondary)` | — | [src](../../../core/services/bounded_repo_tools_runtime.py#L403) |

## `core/services/bounded_workspace_write_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_bounded_workspace_write_execution_surface` | `()` | — | [src](../../../core/services/bounded_workspace_write_runtime.py#L7) |

## `core/services/brain_edge_worker.py`
_Kant-udledningen for en ny hjerne-post flyttes ud af værktøjets ventetid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_arbejd` | `()` | — | [src](../../../core/services/brain_edge_worker.py#L58) |
| function | `koesaet` | `(entry_id, now=…)` | Læg en post i kø til kant-udledning. `False` = køen er fuld. | [src](../../../core/services/brain_edge_worker.py#L74) |
| function | `venter` | `()` | Hvor mange poster der står i kø. Til test og til at se hvor langt bagud. | [src](../../../core/services/brain_edge_worker.py#L100) |

## `core/services/brain_vector_cache.py`
_Embedding-matricen for `jarvis_brain`, holdt i hukommelsen mellem søgninger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ryd` | `()` | Smid alt væk. Bruges af tests og af en eksplicit genopbygning. | [src](../../../core/services/brain_vector_cache.py#L79) |
| function | `status` | `()` | Hvad ligger der lige nu. Til diagnostik — ikke en del af søgevejen. | [src](../../../core/services/brain_vector_cache.py#L89) |
| function | `cosinus` | `(noegler, qv)` | Cosinus mellem `qv` og hver nøgle, i samme rækkefølge som `noegler`. | [src](../../../core/services/brain_vector_cache.py#L100) |
| function | `_nulstil_hvis_anden_db` | `()` | Kaldes under `_LAAS`. | [src](../../../core/services/brain_vector_cache.py#L145) |
| function | `_hent_ind` | `(mangler, dim)` | Hent de manglende vektorer og udvid matricen. Kaldes under `_LAAS`. | [src](../../../core/services/brain_vector_cache.py#L158) |

## `core/services/bridge_presence.py`
_Cross-proces bro-tilstedeværelse via shared_cache (samme mønster som central_xproc)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish` | `(bridges)` | Publicér denne proces' bro-registry-snapshot (kaldes ved register/unregister/dispatch). | [src](../../../core/services/bridge_presence.py#L25) |
| function | `all_presence` | `()` | Bro-tilstedeværelse fra ALLE processer → {user_id: {process, client, capabilities, ...}}. | [src](../../../core/services/bridge_presence.py#L40) |
| function | `process_for_user` | `(user_id)` | Hvilken proces holder en levende bro for user_id? None hvis ingen. | [src](../../../core/services/bridge_presence.py#L59) |

## `core/services/bro_broker.py`
_Bro-broker — owner-styret skift mellem aktive bro-forbindelser (spec §6.6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `summarize_tool_result_for_server` | `(tool_name, result, *, max_error_chars=…)` | Filtrér et code-mode tool-resultat så KUN metadata/summary krydser til | [src](../../../core/services/bro_broker.py#L31) |
| function | `_active_user_ids` | `()` | user_id'er med en aktiv bro (process-local registry). | [src](../../../core/services/bro_broker.py#L70) |
| function | `list_active_bros` | `()` | Alle brugere med en aktiv bro lige nu. | [src](../../../core/services/bro_broker.py#L79) |
| function | `switch` | `(target_user, *, requester_session, now=…)` | Skift requester-sessionen til target-brugerens bro — kræver gyldig override. | [src](../../../core/services/bro_broker.py#L84) |

## `core/services/broadcast_daemon.py`
_Broadcast Daemon — detects emergent coherence across daemons (Experiment 3: GWT)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_broadcast_daemon` | `()` | Run one coherence analysis pass. Returns dict with broadcast_count/coherence. | [src](../../../core/services/broadcast_daemon.py#L23) |
| function | `build_workspace_surface` | `()` | MC surface for global workspace experiment. | [src](../../../core/services/broadcast_daemon.py#L102) |
| function | `_silent_reason` | `(snapshot)` | Hvorfor fladen er tom — uden at koere en ny analyse. | [src](../../../core/services/broadcast_daemon.py#L131) |
| function | `_cluster_by_topic` | `(entries)` | Group entries into clusters where Jaccard similarity of topics >= threshold. | [src](../../../core/services/broadcast_daemon.py#L142) |
| function | `_representative_topic` | `(cluster)` | Return the most common meaningful words across all topics in cluster. | [src](../../../core/services/broadcast_daemon.py#L159) |
| function | `_fire_broadcast` | `(cluster, unique_sources, topic_cluster)` | Persist broadcast event and publish to eventbus. | [src](../../../core/services/broadcast_daemon.py#L169) |
| function | `_compute_coherence` | `()` | workspace_coherence = broadcast events with 3+ sources / total events (rolling 24h). | [src](../../../core/services/broadcast_daemon.py#L199) |

## `core/services/cache_boundary_observer.py`
_Cache-boundary drift observer (harness Part B, Mechanism A)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_static_prefix` | `(*, provider, model, section_shape, static_prefix_sha)` | Record the static-prefix hash for (provider, model, shape); on a same-shape | [src](../../../core/services/cache_boundary_observer.py#L17) |

## `core/services/cache_maintenance_daemon.py`
_Cache maintenance daemon — periodic cleanup of expired web cache entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_cache_maintenance_daemon` | `()` | Run cache cleanup if cadence elapsed. Returns stats dict. | [src](../../../core/services/cache_maintenance_daemon.py#L36) |
| function | `checkpoint_wal` | `()` | Checkpoint and record the actual SQLite result, including busy frames. | [src](../../../core/services/cache_maintenance_daemon.py#L210) |
| function | `get_cache_maintenance_stats` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L230) |
| function | `build_cache_maintenance_surface` | `()` | — | [src](../../../core/services/cache_maintenance_daemon.py#L237) |

## `core/services/cache_telemetry.py`
_Per-request cache-telemetri for den synlige DeepSeek-lane (2026-06-30)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `prefix_signature` | `(system_content, tools)` | Beregn (sha-prefix, længde) for det cachebare [system + tools]. | [src](../../../core/services/cache_telemetry.py#L25) |
| function | `message_signatures` | `(messages)` | Ét fingeraftryk og én laengde pr. besked, i den raekkefoelge de sendes. | [src](../../../core/services/cache_telemetry.py#L51) |
| function | `_tool_name` | `(tool)` | Navnet ud af en OpenAI-formet tool-definition — tolerant over for formen. | [src](../../../core/services/cache_telemetry.py#L114) |
| function | `_remember_tool_names` | `(tools_sha, tools)` | Gem navnene bag deres hash, saa `record_visible_cache` kan slaa dem op. | [src](../../../core/services/cache_telemetry.py#L124) |
| function | `_note_tools_churn` | `(lane, tools_sha)` | Skriv ÉN linje naar værktøjssættet ændrer sig: hvad kom, hvad gik. | [src](../../../core/services/cache_telemetry.py#L138) |
| function | `component_signatures` | `(messages, tools)` | Fingerprint prompt regions separately, without recording their contents. | [src](../../../core/services/cache_telemetry.py#L180) |
| function | `record_visible_cache` | `(*, run_id=…, round_index=…, autonomous=…, lane=…, provider=…, model=…, prefix_sha=…, prefix_len=…, cache_hit=…, cache_miss=…, session_id=…, system_sha=…, tools_sha=…, tail_sha=…, system_len=…, tools_len=…, tools_n=…, tail_len=…, system_chunks=…, msg_shas=…, msg_lens=…, msg_count=…)` | Append én telemetri-linje. Self-safe (sluger alt). | [src](../../../core/services/cache_telemetry.py#L217) |

## `core/services/cadence_claims.py`
_Ét krav ad gangen, og en nedkoeling der overlever en genstart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ClaimResult` | `` | — | [src](../../../core/services/cadence_claims.py#L34) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/cadence_claims.py#L40) |
| function | `_dt` | `(raa)` | — | [src](../../../core/services/cadence_claims.py#L64) |
| function | `claim_producer` | `(name, *, cooldown_minutes, lease_seconds, now=…)` | Tag kravet paa en producent, hvis den er moden og ledig. | [src](../../../core/services/cadence_claims.py#L75) |
| function | `complete_producer` | `(name, lease_token, *, succeeded, now=…)` | Giv kravet fri. KUN et gennemfoert pas saetter nedkoelings-maerket. | [src](../../../core/services/cadence_claims.py#L126) |
| function | `claim_idempotency_key` | `(scope, key, *, now=…)` | Foerste kalder vinder. Returnerer False hvis noeglen er brugt foer. | [src](../../../core/services/cadence_claims.py#L162) |
| function | `last_success_at` | `(name)` | Hvornaar loeb producenten sidst IGENNEM? Tom streng hvis aldrig. | [src](../../../core/services/cadence_claims.py#L183) |
| function | `note_producer_ran` | `(name, *, now=…)` | Bogfoer et gennemfoert pas — uden at gaa gennem lease-dansen. | [src](../../../core/services/cadence_claims.py#L210) |

## `core/services/cadence_producers.py`
_Cadence Producers — central orchestration for waking up dead MC fields._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/cadence_producers.py#L56) |
| function | `_meaningful_run_topic` | `(user_message)` | — | [src](../../../core/services/cadence_producers.py#L60) |
| function | `produce_signals_from_run` | `(*, run_id, session_id, user_message, assistant_response, outcome_status, user_mood=…)` | Fire all relevant signals after a visible run, bypassing chain dependencies. | [src](../../../core/services/cadence_producers.py#L65) |
| function | `produce_emergent_signals_from_history` | `()` | Run the emergent signal daemon to scan timeline for patterns. | [src](../../../core/services/cadence_producers.py#L654) |
| function | `detect_decision_in_message` | `(*, user_message, assistant_response, run_id)` | Detect decisions in conversation and log them. | [src](../../../core/services/cadence_producers.py#L669) |
| function | `run_adoption_pipelines` | `()` | Move things from candidate → adopted state. | [src](../../../core/services/cadence_producers.py#L703) |
| function | `sync_personality_to_self_model` | `()` | Bridge: sync personality_vector changes to self_model_signal. | [src](../../../core/services/cadence_producers.py#L734) |
| function | `progress_signal_lifecycles` | `()` | Move signals through lifecycle stages: active → carried → fading → released. | [src](../../../core/services/cadence_producers.py#L812) |
| function | `_observe_frozen` | `(nerve, meta)` | EGRESS-FRI liveness for en vækket frossen detektor (rettet 2026-07-01: var central().observe). | [src](../../../core/services/cadence_producers.py#L847) |
| function | `tick_frozen_detectors` | `(tick_count)` | LivingNeuron Fase B: væk de frosne detektorer på LAV cadence (deres consumers sultede på | [src](../../../core/services/cadence_producers.py#L856) |
| function | `build_cadence_producers_surface` | `()` | MC surface for cadence producer status. | [src](../../../core/services/cadence_producers.py#L913) |
| function | `_levende_register` | `()` | Registrets producenter i prioritetsraekkefoelge. Selv-sikker: tomt ved | [src](../../../core/services/cadence_producers.py#L941) |
| function | `_graf_rapport` | `()` | Sidste validering af producent-grafen. Selv-sikker: en flade maa ikke | [src](../../../core/services/cadence_producers.py#L962) |

