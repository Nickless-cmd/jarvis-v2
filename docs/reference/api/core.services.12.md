# `core.services.12` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/impulse_executor.py`
_Impulse Executor — konverterer impulser til konkrete handlinger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExecutedAction` | `` | Record of an impulse that was executed as a concrete action. | [src](../../../core/services/impulse_executor.py#L96) |
| function | `select_action` | `(direction, strength)` | Select the most appropriate action for a given direction and strength. | [src](../../../core/services/impulse_executor.py#L122) |
| function | `execute_impulse` | `(impulse)` | Execute a single impulse — convert it to a concrete action. | [src](../../../core/services/impulse_executor.py#L145) |
| function | `_perform_action` | `(action_type, direction, topic, strength)` | Actually perform the selected action. Returns (result, detail). | [src](../../../core/services/impulse_executor.py#L215) |
| function | `_action_push_initiative` | `(direction, topic, strength)` | Push an initiative to the initiative queue. | [src](../../../core/services/impulse_executor.py#L246) |
| function | `_action_search_memory` | `(topic)` | Search memory for related information. | [src](../../../core/services/impulse_executor.py#L262) |
| function | `_action_deep_analyze` | `(topic)` | Trigger a deep analysis. | [src](../../../core/services/impulse_executor.py#L271) |
| function | `_action_propose_edit` | `(topic)` | Propose a source edit. | [src](../../../core/services/impulse_executor.py#L280) |
| function | `_action_notify` | `(action_type, direction, topic, strength)` | Notify the user about an impulse. | [src](../../../core/services/impulse_executor.py#L289) |
| function | `_action_adjust_mood` | `(direction)` | Adjust mood based on retreat impulse. | [src](../../../core/services/impulse_executor.py#L300) |
| function | `_action_journal` | `(topic, strength)` | Write a project journal entry. | [src](../../../core/services/impulse_executor.py#L309) |
| function | `_action_compose_outreach` | `(direction, topic, strength)` | Spor-1: compose and send an outreach message via outreach_composer. | [src](../../../core/services/impulse_executor.py#L318) |
| function | `_observe_impulse_tick` | `(*, pending, executed, starved)` | EGRESS-FRI liveness til Centralen (rettet 2026-07-01: var central().observe). Kaster aldrig. | [src](../../../core/services/impulse_executor.py#L344) |
| function | `run_impulse_executor_tick` | `()` | Run one tick of the impulse executor. | [src](../../../core/services/impulse_executor.py#L355) |
| function | `get_execution_log` | `(limit=…)` | Return recent execution log entries. | [src](../../../core/services/impulse_executor.py#L404) |
| function | `snapshot` | `()` | Return serializable snapshot of executor state. | [src](../../../core/services/impulse_executor.py#L409) |

## `core/services/in_flight_runs.py`
_In-flight run tracker for resume-after-interrupt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/in_flight_runs.py#L43) |
| function | `_save` | `(records)` | — | [src](../../../core/services/in_flight_runs.py#L54) |
| function | `mark_started` | `(*, run_id, session_id, user_message, kind=…, provider=…, model=…)` | Record that a run is in flight. Keyed by run_id (unique). | [src](../../../core/services/in_flight_runs.py#L58) |
| function | `mark_tool` | `(run_id, tool_name)` | Update the last-tool-attempted hint for an in-flight run. | [src](../../../core/services/in_flight_runs.py#L106) |
| function | `mark_completed` | `(run_id)` | Clear an in-flight record on success/fail/cancel — all the same to us; | [src](../../../core/services/in_flight_runs.py#L118) |
| function | `mark_interrupted` | `(run_id, *, reason=…, summary=…)` | Keep an in-flight record as a resumable interrupted run. | [src](../../../core/services/in_flight_runs.py#L129) |
| function | `interrupted_for_session` | `(session_id)` | Return the most recent in-flight record for this session, or None. | [src](../../../core/services/in_flight_runs.py#L144) |
| function | `list_running_orphans` | `(stale_after_s)` | Return records still marked ``running`` whose ``started_at`` is older than | [src](../../../core/services/in_flight_runs.py#L166) |
| function | `clear_session` | `(session_id)` | Drop all in-flight records for a session (used when user explicitly | [src](../../../core/services/in_flight_runs.py#L192) |
| function | `classify_resume_intent` | `(user_message)` | Classify whether a user message should resume an interrupted run. | [src](../../../core/services/in_flight_runs.py#L207) |
| function | `interruption_prompt_section` | `(session_id, user_message=…)` | Format an interrupted record as a system-prompt block, or None. | [src](../../../core/services/in_flight_runs.py#L219) |

## `core/services/infra_sense.py`
_core/services/infra_sense.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tcp_probe` | `(host, port, timeout=…)` | (oppe, latency_ms) — TCP-connect. Undgår ICMP-privilegier; åben port = servicen lever. | [src](../../../core/services/infra_sense.py#L47) |
| function | `poll_reachability` | `()` | Puls på huset: op/ned + latency for hver host → observe(cluster=infra). Self-safe. | [src](../../../core/services/infra_sense.py#L57) |
| function | `_http_json` | `(url, *, headers=…, method=…, body=…, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L78) |
| function | `poll_pihole` | `()` | PiHole DNS-helbred: blok-rate + klienter (spike = mulig malware). Self-safe. | [src](../../../core/services/infra_sense.py#L91) |
| function | `poll_pfsense` | `()` | pfSense gateway-liveness + uptime via REST API (X-API-Key). Read-only. Self-safe. | [src](../../../core/services/infra_sense.py#L123) |
| function | `_ssh_run` | `(target, remote_cmd, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L164) |
| function | `_parse_kv` | `(s)` | — | [src](../../../core/services/infra_sense.py#L175) |
| function | `poll_ssh_hosts` | `()` | Dyb health (disk/services/guests) via read-only SSH. Self-safe pr. host. | [src](../../../core/services/infra_sense.py#L187) |
| function | `poll_ha` | `()` | Home Assistant: tilstedeværelse + enheder offline (netværks-/device-signal). Self-safe. | [src](../../../core/services/infra_sense.py#L208) |
| function | `_notify_owner_security` | `(title, message)` | — | [src](../../../core/services/infra_sense.py#L234) |
| function | `_pfsense_syslogd_running` | `()` | Lever syslogd-PROCESSEN på pfSense? Via REST-API command_prompt (root-shell, read-only ps). | [src](../../../core/services/infra_sense.py#L265) |
| function | `_pfsense_restart_syslogd` | `()` | AUTO-HEAL: genstart syslogd på pfSense via REST-API command_prompt (root) og bekræft | [src](../../../core/services/infra_sense.py#L288) |
| function | `poll_syslog` | `()` | Dræn pfSense-syslog-detektioner (port-scan/brute-force) → Centralen: observe + incident | [src](../../../core/services/infra_sense.py#L305) |
| function | `_safe` | `(fn)` | — | [src](../../../core/services/infra_sense.py#L402) |
| function | `run_infra_sense_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: sans huset read-only. Bulletproof — kaster ALDRIG. | [src](../../../core/services/infra_sense.py#L409) |
| function | `register_infra_sense_producer` | `()` | Registrér infra-sansningen som cadence-producer (~hvert 3 min). Read-only. | [src](../../../core/services/infra_sense.py#L425) |

## `core/services/infra_weather_daemon.py`
_Infra Weather Daemon — "The atmosphere of my system"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_psutil` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L36) |
| function | `_system_load` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L44) |
| function | `_disk_pressure` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L59) |
| function | `_network_latency` | `()` | Lightweight network health check. | [src](../../../core/services/infra_weather_daemon.py#L79) |
| function | `_api_cost_today` | `()` | Sum of today's API costs via the costs ledger. | [src](../../../core/services/infra_weather_daemon.py#L122) |
| function | `_process_health` | `()` | Check some expected child processes / threads are alive. | [src](../../../core/services/infra_weather_daemon.py#L143) |
| function | `_weather_label` | `(load, disk_pct, cost)` | Return (label, emoji) — ☀️ clear, 🌧 under pressure, ⛈ critical. | [src](../../../core/services/infra_weather_daemon.py#L162) |
| function | `_compose_report` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L179) |
| function | `_maybe_emit_critical` | `(report)` | — | [src](../../../core/services/infra_weather_daemon.py#L211) |
| function | `get_weather` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L243) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/infra_weather_daemon.py#L253) |
| function | `build_infra_weather_surface` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L257) |
| function | `_surface_summary` | `(r)` | — | [src](../../../core/services/infra_weather_daemon.py#L273) |
| function | `build_infra_weather_prompt_section` | `()` | Silent when clear. Speaks when pressure or critical. | [src](../../../core/services/infra_weather_daemon.py#L282) |

## `core/services/inheritance_seed.py`
_Inheritance seed — writes near-thoughts before version transition or shutdown._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `write_inheritance_seed` | `()` | Collect near-thoughts from active daemons and write to workspace. | [src](../../../core/services/inheritance_seed.py#L23) |
| function | `read_inheritance_seed` | `()` | Read inheritance seed from workspace. Returns empty string if not found. | [src](../../../core/services/inheritance_seed.py#L67) |
| function | `_collect_sections` | `()` | — | [src](../../../core/services/inheritance_seed.py#L84) |
| function | `_collect_pending_proposals` | `()` | — | [src](../../../core/services/inheritance_seed.py#L94) |
| function | `_collect_open_curiosity` | `()` | — | [src](../../../core/services/inheritance_seed.py#L104) |
| function | `_collect_creative_drift` | `()` | — | [src](../../../core/services/inheritance_seed.py#L114) |
| function | `_collect_unresolved_tensions` | `()` | — | [src](../../../core/services/inheritance_seed.py#L124) |
| function | `_collect_thought_stream` | `()` | — | [src](../../../core/services/inheritance_seed.py#L135) |

## `core/services/initiative_accumulator.py`
_Initiative Accumulator — proactive wants that accumulate between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Want` | `` | A want that Jarvis develops between ticks. | [src](../../../core/services/initiative_accumulator.py#L23) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/initiative_accumulator.py#L37) |
| function | `accumulate_wants` | `(duration)` | Accumulate wants based on life phase and duration. | [src](../../../core/services/initiative_accumulator.py#L41) |
| function | `get_top_want` | `()` | Get the strongest current want. | [src](../../../core/services/initiative_accumulator.py#L110) |
| function | `get_wants_by_type` | `(want_type)` | Get all wants of a specific type. | [src](../../../core/services/initiative_accumulator.py#L118) |
| function | `format_wants_for_prompt` | `()` | Format wants for prompt injection. | [src](../../../core/services/initiative_accumulator.py#L123) |
| function | `clear_wants_by_type` | `(want_type)` | Clear wants of a specific type. | [src](../../../core/services/initiative_accumulator.py#L140) |
| function | `reset_initiative_accumulator` | `()` | Reset initiative accumulator state (for testing). | [src](../../../core/services/initiative_accumulator.py#L146) |
| function | `get_initiative_accumulator_state` | `()` | Get current state of initiative accumulator. | [src](../../../core/services/initiative_accumulator.py#L153) |
| function | `build_initiative_accumulator_surface` | `()` | Build MC surface for initiative accumulator. | [src](../../../core/services/initiative_accumulator.py#L170) |
| function | `_publish_initiative_accumulator_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/initiative_accumulator.py#L184) |

## `core/services/initiative_queue.py`
_Persistent initiative queue — bridges inner voice thoughts to heartbeat actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `push_initiative` | `(*, focus, source=…, source_id=…, priority=…)` | Push a new initiative to the queue. Returns the initiative_id. | [src](../../../core/services/initiative_queue.py#L29) |
| function | `seed_long_term_intention` | `(*, title, why, source=…, source_id=…, priority=…)` | Create or refresh a long-term intention owned by Jarvis. | [src](../../../core/services/initiative_queue.py#L130) |
| function | `get_pending_initiatives` | `()` | Return all pending (non-expired, non-acted) initiatives. | [src](../../../core/services/initiative_queue.py#L196) |
| function | `mark_acted` | `(initiative_id, *, action_summary=…)` | Mark an initiative as acted upon. Returns True if found. | [src](../../../core/services/initiative_queue.py#L213) |
| function | `mark_attempted` | `(initiative_id, *, blocked_reason=…, retry_delay_minutes=…, action_summary=…)` | Record a bounded attempt and schedule a retry if still pending. | [src](../../../core/services/initiative_queue.py#L269) |
| function | `approve_initiative` | `(initiative_id, *, note=…)` | Mark an initiative as user-approved. Returns the updated record or None if not found. | [src](../../../core/services/initiative_queue.py#L312) |
| function | `reject_initiative` | `(initiative_id, *, note=…)` | Mark an initiative as user-rejected and expire it. Returns updated record or None. | [src](../../../core/services/initiative_queue.py#L328) |
| function | `get_initiative_queue_state` | `()` | Return full queue state for MC observability. | [src](../../../core/services/initiative_queue.py#L344) |
| function | `_expire_stale` | `(now)` | Expire initiatives older than _EXPIRE_MINUTES. Must hold _QUEUE_LOCK. | [src](../../../core/services/initiative_queue.py#L382) |
| function | `_trim_pending` | `(now)` | — | [src](../../../core/services/initiative_queue.py#L400) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/initiative_queue.py#L420) |
| function | `_initiative_due` | `(initiative, now)` | — | [src](../../../core/services/initiative_queue.py#L430) |
| function | `_initiative_sort_key` | `(initiative)` | — | [src](../../../core/services/initiative_queue.py#L440) |
| function | `list_active_long_term_intentions` | `(*, limit=…)` | — | [src](../../../core/services/initiative_queue.py#L452) |
| function | `abandon_long_term_intention` | `(initiative_id, *, note=…)` | — | [src](../../../core/services/initiative_queue.py#L467) |
| function | `_find_active_long_term_intention_by_title` | `(title)` | — | [src](../../../core/services/initiative_queue.py#L493) |

## `core/services/inner_dialectic_engine.py`
_Compact inner critic / ally / synthesizer dialectic._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_inner_dialectic` | `(*, focus, context=…)` | — | [src](../../../core/services/inner_dialectic_engine.py#L13) |
| function | `build_inner_dialectic_surface` | `()` | — | [src](../../../core/services/inner_dialectic_engine.py#L35) |
| function | `build_inner_dialectic_prompt_section` | `()` | — | [src](../../../core/services/inner_dialectic_engine.py#L42) |
| function | `_critic` | `(lower)` | — | [src](../../../core/services/inner_dialectic_engine.py#L54) |
| function | `_ally` | `(lower)` | — | [src](../../../core/services/inner_dialectic_engine.py#L65) |
| function | `_synthesize` | `(critic, ally, context)` | — | [src](../../../core/services/inner_dialectic_engine.py#L76) |

## `core/services/inner_visible_support_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_inner_visible_support_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L21) |
| function | `refresh_runtime_inner_visible_support_signal_statuses` | `()` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L53) |
| function | `build_runtime_inner_visible_support_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L84) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L124) |
| function | `_persist_inner_visible_support_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L258) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L327) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L337) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L347) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L362) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L392) |
| function | `_focus_key` | `(private_state, curiosity_state)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L455) |
| function | `_derive_support_tone` | `(*, state_tone, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L466) |
| function | `_derive_support_stance` | `(*, state_tone, curiosity_type, contradiction_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L480) |
| function | `_derive_support_directness` | `(*, state_pressure, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L492) |
| function | `_derive_support_watchfulness` | `(*, state_pressure, curiosity_pull, curiosity_type, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L502) |
| function | `_derive_support_momentum` | `(*, state_pressure, curiosity_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L518) |
| function | `_bounded_support_summary` | `(*, private_state, curiosity_state, executive_contradiction, tone, stance)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L526) |
| function | `_grounding_mode` | `(*, has_curiosity, has_executive_contradiction)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L549) |
| function | `_supports_executive_sharpening` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L559) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L568) |
| function | `_canonical_focus_segment` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L574) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L581) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L588) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L600) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L611) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L619) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L625) |

## `core/services/inner_voice_daemon.py`
_Bounded inner voice daemon light — private heartbeat-driven inner voice._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_inner_voice_daemon` | `(*, trigger=…, last_visible_at=…, witness_daemon_last_run_at=…)` | Bounded inner voice daemon — produces one private inner-voice note. | [src](../../../core/services/inner_voice_daemon.py#L101) |
| function | `get_inner_voice_daemon_state` | `()` | Return current inner voice daemon state for MC observability. | [src](../../../core/services/inner_voice_daemon.py#L298) |
| function | `_gather_grounding` | `()` | Gather grounding material from existing runtime surfaces. | [src](../../../core/services/inner_voice_daemon.py#L314) |
| function | `_recent_approval_sentiment_summary` | `()` | Summarize only notable recent approval-feedback patterns. | [src](../../../core/services/inner_voice_daemon.py#L495) |
| function | `_approval_feedback_tools` | `(entries)` | — | [src](../../../core/services/inner_voice_daemon.py#L531) |
| function | `_render_inner_voice_note` | `(grounding)` | Render inner voice note via workspace prompt + LLM, with fallback. | [src](../../../core/services/inner_voice_daemon.py#L549) |
| function | `_llm_render_inner_voice` | `(grounding)` | Use workspace INNER_VOICE.md prompt + heartbeat model to render note. | [src](../../../core/services/inner_voice_daemon.py#L569) |
| function | `_apply_support_shading` | `(base_mode, fragments)` | Apply experiential support bias to inner voice mode selection. | [src](../../../core/services/inner_voice_daemon.py#L771) |
| function | `_has_living_candidate_pull` | `(fragments, *, continuity_state, initiative_shading, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L800) |
| function | `_has_mixed_live_stream` | `(fragments, *, continuity_state, initiative_shading)` | — | [src](../../../core/services/inner_voice_daemon.py#L840) |
| function | `_deterministic_compose` | `(grounding)` | Deterministic fallback composition when LLM is unavailable. | [src](../../../core/services/inner_voice_daemon.py#L872) |
| function | `_normalize_inner_voice_mode` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L903) |
| function | `_select_inner_voice_mode` | `(grounding, *, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L910) |
| function | `_derive_inner_voice_focus` | `(grounding, *, mode=…, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L969) |
| function | `_compose_living_inner_voice_thought` | `(*, mode, fragments, focus)` | Structured fallback trace — NOT first-person prose. | [src](../../../core/services/inner_voice_daemon.py#L1003) |
| function | `_secondary_inner_voice_observation` | `(fragments)` | Pick the strongest secondary fragment, returned as key:value (no prose). | [src](../../../core/services/inner_voice_daemon.py#L1033) |
| function | `_mode_anchor` | `(fragments, focus)` | — | [src](../../../core/services/inner_voice_daemon.py#L1054) |
| function | `_normalize_inner_voice_initiative` | `(initiative, *, grounding, mode, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L1069) |
| function | `_render_grounding_fragment` | `(key, value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1093) |
| function | `_sanitize_previous_inner_voice` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1123) |
| function | `_sanitize_inner_voice_text` | `(text, *, max_len=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L1132) |
| function | `_looks_like_inner_voice_meta` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1182) |
| function | `_thought_contains_initiative` | `(text)` | Detect if a thought text contains initiative signals. | [src](../../../core/services/inner_voice_daemon.py#L1235) |
| function | `_extract_initiative_from_thought` | `(text)` | Extract a short initiative description from a thought. | [src](../../../core/services/inner_voice_daemon.py#L1243) |
| function | `_blocked` | `(reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/inner_voice_daemon.py#L1269) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1286) |

## `core/services/inner_voice_notifier.py`
_Inner voice notifier — proactive notification when a thought has substance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L41) |
| function | `stop_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L59) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/inner_voice_notifier.py#L73) |
| function | `_handle_event` | `(payload)` | — | [src](../../../core/services/inner_voice_notifier.py#L91) |
| function | `_is_substantive` | `(*, summary, mode, initiative, initiative_detected)` | — | [src](../../../core/services/inner_voice_notifier.py#L169) |
| function | `_format_message` | `(*, summary, initiative, mode)` | — | [src](../../../core/services/inner_voice_notifier.py#L185) |
| function | `_notifier_enabled` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L193) |
| function | `_min_summary_chars` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L202) |
| function | `_cooldown_minutes` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L212) |
| function | `_quiet_hours` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L222) |
| function | `_in_quiet_hours` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L233) |
| function | `_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L244) |
| function | `_in_cooldown` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L249) |
| function | `_record_sent` | `(now, *, record_id)` | — | [src](../../../core/services/inner_voice_notifier.py#L261) |
| function | `get_inner_voice_notifier_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L276) |

## `core/services/inner_voice_shadow.py`
_Inner voice shadow recorder — Pilot for llm_driven_inner_pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AppraisalRecord` | `` | Structured inner-voice state with narrative rendering. | [src](../../../core/services/inner_voice_shadow.py#L65) |
| method | `AppraisalRecord.is_expired` | `(self, *, now=…)` | True if more than expiry_seconds have passed since generated_at. | [src](../../../core/services/inner_voice_shadow.py#L103) |
| method | `AppraisalRecord.to_dict` | `(self)` | — | [src](../../../core/services/inner_voice_shadow.py#L114) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/inner_voice_shadow.py#L134) |
| function | `_connect` | `()` | — | [src](../../../core/services/inner_voice_shadow.py#L169) |
| function | `_persist` | `(*, function_name, inputs, template_output, llm_output, llm_provider, llm_model, llm_latency_ms, llm_error, source=…, confidence=…, expiry_seconds=…, allowed_effects=…, generated_at=…)` | — | [src](../../../core/services/inner_voice_shadow.py#L176) |
| function | `_call_llm` | `(prompt)` | Run the cheap-lane via pool. Returns dict with output/error/latency. | [src](../../../core/services/inner_voice_shadow.py#L228) |
| function | `_build_helpful_signal_prompt` | `(*, status, focus, work_signal)` | Construct a prompt that asks for the kind of one-line inner thought | [src](../../../core/services/inner_voice_shadow.py#L259) |
| function | `record_shadow` | `(*, function_name, inputs, template_output, prompt_builder)` | Fire-and-forget: spawn a daemon thread to call LLM + persist both | [src](../../../core/services/inner_voice_shadow.py#L284) |
| function | `_build_voice_line_prompt` | `(*, mood_tone, self_position, current_concern, current_pull, **_extra)` | Prompt for protected_inner_voice._voice_line's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L346) |
| function | `_build_private_summary_prompt` | `(*, status, focus, uncertainty, work_signal, **_extra)` | Prompt for private_inner_note._private_summary's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L375) |
| function | `shadow_helpful_signal` | `(*, status, focus, work_signal, template_output)` | — | [src](../../../core/services/inner_voice_shadow.py#L404) |
| function | `generate_appraisal` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…, expiry_seconds=…, allowed_effects=…)` | State-first appraisal: returns the full structured record. | [src](../../../core/services/inner_voice_shadow.py#L418) |
| function | `_persist_record` | `(record, *, template_output)` | Persist an AppraisalRecord to the shadow audit table. | [src](../../../core/services/inner_voice_shadow.py#L513) |
| function | `_generate_via_llm` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…)` | Narrative-first wrapper for backwards compatibility. | [src](../../../core/services/inner_voice_shadow.py#L537) |
| function | `generate_helpful_signal_via_llm` | `(*, status, focus, work_signal, fallback, timeout_seconds=…)` | Production path for private_growth_note._helpful_signal. | [src](../../../core/services/inner_voice_shadow.py#L566) |
| function | `generate_private_summary_via_llm` | `(*, status, focus, uncertainty, work_signal, fallback, timeout_seconds=…)` | Production path for private_inner_note._private_summary. | [src](../../../core/services/inner_voice_shadow.py#L588) |
| function | `generate_voice_line_via_llm` | `(*, mood_tone, self_position, current_concern, current_pull, fallback, timeout_seconds=…)` | Production path for protected_inner_voice._voice_line. | [src](../../../core/services/inner_voice_shadow.py#L615) |
| function | `recent_comparisons` | `(function_name=…, *, limit=…)` | Pull recent shadow records for human comparison. | [src](../../../core/services/inner_voice_shadow.py#L644) |
| function | `shadow_stats` | `(function_name=…)` | Aggregate stats across all shadow records for one function. | [src](../../../core/services/inner_voice_shadow.py#L666) |

## `core/services/interlanguage_practice.py`
_Inter-sprog practice engine — internaliseret protokol på tværs af modeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_interlanguage_practice_table` | `(conn)` | Idempotently create interlanguage_practice table + index. | [src](../../../core/services/interlanguage_practice.py#L127) |
| function | `ensure_schema` | `()` | Bagudkompat: åbner en conn og kalder _ensure_interlanguage_practice_table. | [src](../../../core/services/interlanguage_practice.py#L173) |
| function | `_pick_term` | `(domain_filter=…)` | Pick a random core term, optionally filtered by domain. | [src](../../../core/services/interlanguage_practice.py#L187) |
| function | `_build_clause` | `()` | Build a single clause: <term> <primitive> <term> or !<term>. | [src](../../../core/services/interlanguage_practice.py#L196) |
| function | `generate_state_expression` | `(*, num_clauses=…, mood_override=…)` | Generate a state-expression from current mood and random composition. | [src](../../../core/services/interlanguage_practice.py#L212) |
| function | `record_expression` | `(expression_text, *, session_id=…, tick_id=…, trigger=…, peer_id=…)` | Record a state-expression in the practice log. | [src](../../../core/services/interlanguage_practice.py#L265) |
| function | `get_recent_expressions` | `(*, days=…, limit=…)` | Get recent state-expressions from the practice log. | [src](../../../core/services/interlanguage_practice.py#L298) |
| function | `get_expression_count` | `(*, since_hours=…)` | Count expressions recorded in the last N hours. | [src](../../../core/services/interlanguage_practice.py#L326) |
| function | `export_protocol` | `(*, recent_days=…, max_expressions=…)` | Eksportér hele inter-sprog-protokollen til model-skift. | [src](../../../core/services/interlanguage_practice.py#L342) |
| function | `practice_tick` | `(*, session_id=…, tick_id=…, mood=…)` | Kaldes fra heartbeat tick — generér og gem én state-expression. | [src](../../../core/services/interlanguage_practice.py#L390) |
| function | `export_mood_trace_for_period` | `(start, end)` | Eksportér Jarvis' mood-historie over en periode som (timestamp, mood) pairs. | [src](../../../core/services/interlanguage_practice.py#L430) |
| function | `interpolate_mood_at` | `(trace, target_iso)` | Linear-interpolér mellem nærmeste to mood-samples til target timestamp. | [src](../../../core/services/interlanguage_practice.py#L470) |
| function | `build_interlanguage_practice_surface` | `()` | Surface for Mission Control — 3 vital signs + dummy state ved ingen data. | [src](../../../core/services/interlanguage_practice.py#L516) |

## `core/services/internal_cadence.py`
_Internal cadence layer for non-visible inner producers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProducerSpec` | `` | — | [src](../../../core/services/internal_cadence.py#L56) |
| class | `ProducerTickResult` | `` | — | [src](../../../core/services/internal_cadence.py#L66) |
| function | `register_producer` | `(spec)` | Register a non-visible inner producer with the cadence layer. | [src](../../../core/services/internal_cadence.py#L80) |
| function | `deregister_producer` | `(name)` | Remove a producer from the cadence layer. | [src](../../../core/services/internal_cadence.py#L85) |
| function | `_evaluate_producer` | `(spec, *, now, last_visible_at, ran_this_tick, tempo=…)` | Evaluate whether a producer is due. | [src](../../../core/services/internal_cadence.py#L94) |
| function | `_run_producer_bounded` | `(spec, *, trigger, last_visible_at, timeout_s)` | Kør en producer i sin EGEN dæmon-tråd med en hård timeout. | [src](../../../core/services/internal_cadence.py#L147) |
| function | `run_cadence_tick` | `(*, trigger=…, last_visible_at_iso=…)` | Run one cadence tick: evaluate and dispatch all registered producers. | [src](../../../core/services/internal_cadence.py#L192) |
| function | `get_cadence_state` | `()` | Return current cadence layer state for MC observability. | [src](../../../core/services/internal_cadence.py#L368) |
| function | `_ensure_producers_registered` | `()` | Register known producers if not already registered. | [src](../../../core/services/internal_cadence.py#L407) |
| function | `run_cadence_tick_with_bootstrap` | `(*, trigger=…, last_visible_at_iso=…)` | Bootstrap producers and run a cadence tick. | [src](../../../core/services/internal_cadence.py#L435) |
| function | `_run_injection_refresh_tick` | `()` | Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path). | [src](../../../core/services/internal_cadence.py#L458) |
| function | `_scheduler_loop` | `()` | Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds. | [src](../../../core/services/internal_cadence.py#L473) |
| function | `start_cadence_scheduler` | `()` | Spawn the standalone cadence scheduler thread. Idempotent. | [src](../../../core/services/internal_cadence.py#L526) |
| function | `stop_cadence_scheduler` | `()` | Signal the scheduler thread to exit. Best-effort; daemon dies with process. | [src](../../../core/services/internal_cadence.py#L541) |

## `core/services/internal_cadence_central_wiring.py`
_Central-wiring cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_central_wiring_producers` | `()` | Run the Central-wiring registration blocks (unchanged order/behavior). | [src](../../../core/services/internal_cadence_central_wiring.py#L15) |

## `core/services/internal_cadence_core.py`
_Core-infra cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_core_producers` | `(register_producer)` | Register the core-infra producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_core.py#L19) |

## `core/services/internal_cadence_inner_life.py`
_Inner-life cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_inner_life_producers` | `(register_producer)` | Register the inner-life producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_inner_life.py#L24) |

## `core/services/internal_cadence_maintenance.py`
_Maintenance / health cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_maintenance_producers` | `(register_producer)` | Register the maintenance / health producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_maintenance.py#L23) |

## `core/services/internal_cadence_matrix.py`
_Matrix-themed cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_matrix_producers` | `(register_producer)` | Register the Matrix-themed producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_matrix.py#L18) |

## `core/services/internal_opposition_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_internal_opposition_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L27) |
| function | `refresh_runtime_internal_opposition_signal_statuses` | `()` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L49) |
| function | `build_runtime_internal_opposition_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L80) |
| function | `_extract_internal_opposition_candidates` | `()` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L103) |
| function | `_persist_internal_opposition_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L282) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L351) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L384) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L389) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L394) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L399) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L404) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L409) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L414) |
| function | `_world_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L419) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L424) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L429) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L439) |

## `core/services/irony_daemon.py`
_Irony daemon — situational self-distance and absurd self-observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_irony_daemon` | `()` | — | [src](../../../core/services/irony_daemon.py#L20) |
| function | `get_latest_irony_observation` | `()` | — | [src](../../../core/services/irony_daemon.py#L49) |
| function | `build_irony_surface` | `()` | — | [src](../../../core/services/irony_daemon.py#L53) |
| function | `_maybe_reset_daily_count` | `()` | — | [src](../../../core/services/irony_daemon.py#L62) |
| function | `_collect_snapshot` | `()` | — | [src](../../../core/services/irony_daemon.py#L70) |
| function | `_detect_irony_conditions` | `(snapshot)` | — | [src](../../../core/services/irony_daemon.py#L95) |
| function | `_generate_observation` | `(snapshot, condition)` | — | [src](../../../core/services/irony_daemon.py#L108) |
| function | `_store_observation` | `(observation, condition)` | — | [src](../../../core/services/irony_daemon.py#L135) |

## `core/services/jarvis_brain.py`
_Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BrainEntry` | `` | — | [src](../../../core/services/jarvis_brain.py#L64) |
| method | `BrainEntry.__post_init__` | `(self)` | — | [src](../../../core/services/jarvis_brain.py#L91) |
| function | `_atomic_write` | `(path, content)` | Atomic file write via tmp + rename. Creates parent dirs as needed. | [src](../../../core/services/jarvis_brain.py#L107) |
| function | `parse_frontmatter` | `(path)` | Parse YAML frontmatter + body from a markdown file. | [src](../../../core/services/jarvis_brain.py#L115) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/jarvis_brain.py#L135) |
| function | `_parse_iso` | `(s)` | Parse ISO timestamp from string or pass-through if already datetime. | [src](../../../core/services/jarvis_brain.py#L143) |
| function | `render_entry_markdown` | `(entry)` | Render a BrainEntry as markdown with YAML frontmatter. | [src](../../../core/services/jarvis_brain.py#L156) |
| function | `entry_from_frontmatter` | `(fm, body)` | Build a BrainEntry from parsed frontmatter dict + body string. | [src](../../../core/services/jarvis_brain.py#L183) |
| function | `_workspace_root` | `()` | Base dir for brain-relative paths. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L276) |
| function | `_state_root` | `()` | — | [src](../../../core/services/jarvis_brain.py#L293) |
| function | `brain_dir` | `()` | Return the brain storage dir under JARVIS_HOME/shared/jarvis_brain. | [src](../../../core/services/jarvis_brain.py#L300) |
| function | `index_db_path` | `()` | — | [src](../../../core/services/jarvis_brain.py#L310) |
| function | `connect_index` | `()` | — | [src](../../../core/services/jarvis_brain.py#L314) |
| function | `_ensure_index_schema_migrations` | `(conn)` | Bring pre-existing brain_index tables up to the current schema. | [src](../../../core/services/jarvis_brain.py#L324) |
| function | `_slugify` | `(s, max_len=…)` | — | [src](../../../core/services/jarvis_brain.py#L372) |
| function | `_file_hash` | `(text)` | — | [src](../../../core/services/jarvis_brain.py#L379) |
| function | `write_entry` | `(*, kind, title, content, visibility, domain, trigger=…, related=…, tags=…, source_url=…, source_chronicle=…, importance=…, now=…, skip_temporal=…)` | Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu). | [src](../../../core/services/jarvis_brain.py#L383) |
| function | `read_entry` | `(entry_id)` | Read a BrainEntry by id (loads from disk via index lookup). | [src](../../../core/services/jarvis_brain.py#L478) |
| function | `_index_path_for` | `(entry_id)` | Returns the relative path stored in brain_index for entry_id. | [src](../../../core/services/jarvis_brain.py#L494) |
| function | `compute_effective_salience` | `(entry, now)` | Compute time-decayed salience with bump amplification + importance gate. | [src](../../../core/services/jarvis_brain.py#L522) |
| function | `_embed_text` | `(text)` | Wrapper around eksisterende embedder. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L550) |
| function | `_embedding_to_blob` | `(v)` | — | [src](../../../core/services/jarvis_brain.py#L565) |
| function | `_embedding_from_blob` | `(blob, dim)` | — | [src](../../../core/services/jarvis_brain.py#L569) |
| function | `embed_pending_entries` | `()` | Embed alle entries i index'et der mangler embedding. Returnerer antal. | [src](../../../core/services/jarvis_brain.py#L573) |
| function | `search_brain` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Hybrid embedding search: 0.7*cosine + 0.3*effective_salience + temporal boost. | [src](../../../core/services/jarvis_brain.py#L604) |
| function | `_compute_search_temporal_boost` | `(candidate_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost for search candidates. | [src](../../../core/services/jarvis_brain.py#L709) |
| function | `bump_salience` | `(entry_id, now=…)` | Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil. | [src](../../../core/services/jarvis_brain.py#L750) |
| function | `archive_entry` | `(entry_id, *, reason=…, now=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/services/jarvis_brain.py#L794) |
| function | `supersede` | `(*, old_ids, new_id, now=…)` | Mark old entries as superseded by new_id (keeps files in place). | [src](../../../core/services/jarvis_brain.py#L825) |
| function | `rebuild_index_from_files` | `()` | Scan brain_dir() for .md files; new/changed hash → update index. | [src](../../../core/services/jarvis_brain.py#L851) |
| function | `_extract_text_for_entry` | `(entry_id)` | Read entry content from disk for entity/semantic analysis. | [src](../../../core/services/jarvis_brain.py#L947) |
| function | `_temporal_similarity_score` | `(hours_apart)` | Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h. | [src](../../../core/services/jarvis_brain.py#L953) |
| function | `_cosine_similarity` | `(a_vec, b_vec)` | — | [src](../../../core/services/jarvis_brain.py#L963) |
| function | `_compute_temporal_confidence` | `(*, temporal, semantic, entity, is_chain, chain_score=…)` | Combine four signals into a single confidence score (0.0–1.0). | [src](../../../core/services/jarvis_brain.py#L970) |
| function | `_compute_chain_score` | `(*, new_entry, cand_entry, hours_apart, cand_related)` | Compute chain signal score (0.0–1.0) between two entries. | [src](../../../core/services/jarvis_brain.py#L989) |
| function | `infer_temporal_edges` | `(new_entry_id, now=…)` | Run four-signal inference between a new entry and all existing active entries. | [src](../../../core/services/jarvis_brain.py#L1039) |
| function | `_store_temporal_edge` | `(from_id, to_id, confidence, reasoning, now)` | Insert or update a temporal edge with combined confidence. | [src](../../../core/services/jarvis_brain.py#L1169) |
| function | `get_temporal_neighbors` | `(entry_id, min_confidence=…, limit=…)` | Get tidligere inferred temporal neighbors for an entry. | [src](../../../core/services/jarvis_brain.py#L1195) |
| function | `temporal_boost_recall` | `(entry_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost scores for a set of entry IDs. | [src](../../../core/services/jarvis_brain.py#L1225) |
| function | `prune_stale_edges` | `(*, max_age_days=…, min_confidence=…)` | Remove stale temporal edges with low confidence. | [src](../../../core/services/jarvis_brain.py#L1281) |
| function | `full_rebuild` | `(*, batch_size=…)` | Genberegn alle temporale edges fra bunden. | [src](../../../core/services/jarvis_brain.py#L1308) |
| function | `_emit_jarvis_brain_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/jarvis_brain.py#L1370) |

## `core/services/jarvis_brain_daemon.py`
_Jarvis Brain background daemon — tre uafhængige loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reindex_once` | `()` | Et enkelt reindex-pass. Returnerer antal file changes opdaget. | [src](../../../core/services/jarvis_brain_daemon.py#L26) |
| function | `reindex_loop` | `(stop_event)` | Long-running loop. Stops cleanly when stop_event is set. | [src](../../../core/services/jarvis_brain_daemon.py#L36) |
| function | `find_duplicate_proposals` | `(*, threshold=…, kinds=…)` | Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold. | [src](../../../core/services/jarvis_brain_daemon.py#L61) |
| function | `_call_ollamafreeapi` | `(prompt)` | Free OllamaFreeAPI — public-safe job. Returns parsed JSON or None on fail. | [src](../../../core/services/jarvis_brain_daemon.py#L115) |
| function | `_model_is_available` | `(tag_names, model)` | Pure: er `model` til stede blandt Ollamas /api/tags-navne? Matcher både | [src](../../../core/services/jarvis_brain_daemon.py#L136) |
| function | `_call_local_ollama` | `(prompt)` | Ollama-kald for personal/intimate brain-jobs (summaries + contradiction). | [src](../../../core/services/jarvis_brain_daemon.py#L149) |
| function | `_resolve_local_chat_model` | `()` | Find configured local-lane chat model from provider router (best-effort). | [src](../../../core/services/jarvis_brain_daemon.py#L205) |
| function | `_parse_json_loose` | `(text)` | Parse JSON from possibly noisy LLM output. Looks for first {...} block. | [src](../../../core/services/jarvis_brain_daemon.py#L218) |
| function | `_llm_contradiction_check` | `(a, b)` | Privacy-routed contradiction check. | [src](../../../core/services/jarvis_brain_daemon.py#L239) |
| function | `_state_path` | `()` | Override target in tests via monkeypatch. | [src](../../../core/services/jarvis_brain_daemon.py#L266) |
| function | `_read_state` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L273) |
| function | `_write_state` | `(state)` | — | [src](../../../core/services/jarvis_brain_daemon.py#L284) |
| function | `record_proposal_rejection` | `(phase, *, proposal_id)` | Track rejection. After 3 in a row for 'theme' phase, auto-pause. | [src](../../../core/services/jarvis_brain_daemon.py#L293) |
| function | `record_proposal_acceptance` | `(phase, *, proposal_id)` | Reset rejection streak on acceptance. | [src](../../../core/services/jarvis_brain_daemon.py#L315) |
| function | `is_theme_consolidation_paused` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L324) |
| function | `resume_theme_consolidation` | `()` | Manuel reaktivering. Nulstiller streak + paused flag. | [src](../../../core/services/jarvis_brain_daemon.py#L328) |
| function | `_run_theme_consolidation_pass` | `()` | Søndags-pass: group observations efter domain, find temaer. | [src](../../../core/services/jarvis_brain_daemon.py#L336) |
| function | `run_theme_consolidation_if_active` | `()` | Kør tema-pass hvis ikke paused. Returnerer antal forslag genereret. | [src](../../../core/services/jarvis_brain_daemon.py#L345) |
| function | `regenerate_summary` | `(*, target_visibility=…)` | Regenererer state/jarvis_brain_summary.md. | [src](../../../core/services/jarvis_brain_daemon.py#L376) |
| function | `auto_archive_low_salience` | `()` | Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage. | [src](../../../core/services/jarvis_brain_daemon.py#L440) |
| function | `b4_catchup_infer_once` | `(*, batch_size=…)` | Find active entries with no temporal edges and run inference on them. | [src](../../../core/services/jarvis_brain_daemon.py#L506) |
| function | `b4_edge_maintenance_once` | `()` | Run one pass of B4 edge maintenance: catchup + prune. | [src](../../../core/services/jarvis_brain_daemon.py#L553) |
| function | `_consolidation_summary_loop` | `(stop_event)` | Daily consolidation + summary + B4 edge maintenance scheduler. | [src](../../../core/services/jarvis_brain_daemon.py#L583) |
| function | `run_consolidation_pass` | `()` | Single consolidation pass: phase 1 (dedup) + phase 2 (contradictions). | [src](../../../core/services/jarvis_brain_daemon.py#L663) |
| function | `start_brain_daemon` | `()` | Start the three brain daemon threads. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L682) |
| function | `stop_brain_daemon` | `()` | Signal stop and wait briefly for threads to exit. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L705) |

## `core/services/jarvis_brain_reflection.py`
_End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_reflection_envelope` | `(*, chronicle_summary)` | Build the envelope text shown to visible Jarvis at end-of-day. | [src](../../../core/services/jarvis_brain_reflection.py#L30) |
| function | `build_internal_nudge` | `(*, count_so_far)` | Soft nudge after 3+ remember_this calls in same reflection slot. | [src](../../../core/services/jarvis_brain_reflection.py#L35) |
| function | `_was_active_today` | `()` | Best-effort tjek om Jarvis havde aktivitet i dag. | [src](../../../core/services/jarvis_brain_reflection.py#L48) |
| function | `_build_today_chronicle_summary` | `()` | Build a short summary of today's chronicle entries. | [src](../../../core/services/jarvis_brain_reflection.py#L70) |
| function | `_run_reflection_turn` | `(chronicle_summary)` | Trigger en visible-Jarvis tur med reflection-envelope. | [src](../../../core/services/jarvis_brain_reflection.py#L83) |
| function | `run_daily_reflection_if_active` | `()` | Entry point for the daily slot trigger. | [src](../../../core/services/jarvis_brain_reflection.py#L107) |
| function | `build_jarvis_brain_reflection_surface` | `()` | Surface the daily reflection slot without triggering it. | [src](../../../core/services/jarvis_brain_reflection.py#L123) |

## `core/services/jarvis_brain_visibility.py`
_Privacy-gate for Jarvis Brain recall._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_owner_id` | `()` | Hentet via owner_resolver. Wrapped så tests kan monkeypatche. | [src](../../../core/services/jarvis_brain_visibility.py#L14) |
| function | `can_recall` | `(entry_visibility, ceiling)` | True if entry's visibility is permitted at the given ceiling. | [src](../../../core/services/jarvis_brain_visibility.py#L30) |
| function | `session_visibility_ceiling` | `(session)` | Beregn visibility-ceiling for en session. | [src](../../../core/services/jarvis_brain_visibility.py#L35) |

## `core/services/jarvisx_bridge.py`
_JarvisX tool-bridge — bidirectional dispatch over WebSocket._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_dispatch_token` | `()` | Shared-secret som BEGGE processer kan udlede ens. | [src](../../../core/services/jarvisx_bridge.py#L47) |
| function | `_api_port` | `()` | Port for jarvis-api-procesen (hvor broen lever). Default 8080. | [src](../../../core/services/jarvisx_bridge.py#L88) |
| function | `_runtime_port` | `()` | Port for jarvis-runtime-procesen (autonome/wakeup-runs). Default 8011. | [src](../../../core/services/jarvisx_bridge.py#L99) |
| function | `_port_for_process` | `(role)` | Localhost-port for procesrollen. Begge processer kører SAMME uvicorn-app | [src](../../../core/services/jarvisx_bridge.py#L110) |
| function | `_looks_like_closed_ws` | `(exc)` | Er dette en 'send over en allerede-lukket WebSocket'-fejl? Starlette/uvicorn | [src](../../../core/services/jarvisx_bridge.py#L116) |
| function | `_ws_is_closed` | `(ws)` | Bedste-effort: er WS'en allerede lukket? Self-safe → False når ukendt, så vi | [src](../../../core/services/jarvisx_bridge.py#L126) |
| class | `BridgeConnection` | `` | One live bridge connection. WS object is platform-dependent. | [src](../../../core/services/jarvisx_bridge.py#L145) |
| method | `BridgeConnection.send_raw` | `(self, data, *, timeout_s=…)` | Send raw JSON over WS with lock and timeout. | [src](../../../core/services/jarvisx_bridge.py#L164) |
| method | `BridgeConnection.send_invoke` | `(self, *, correlation_id, tool, args, timeout_ms)` | Send tool_invoke over WS and register the pending future. | [src](../../../core/services/jarvisx_bridge.py#L196) |
| method | `BridgeConnection.deliver_result` | `(self, *, correlation_id, status, result=…, error=…)` | Complete the pending future for this correlation_id. | [src](../../../core/services/jarvisx_bridge.py#L231) |
| method | `BridgeConnection.cancel_all_pending` | `(self, *, reason=…)` | Cancel all in-flight calls (e.g. on WS disconnect). | [src](../../../core/services/jarvisx_bridge.py#L276) |
| class | `BridgeRegistry` | `` | Process-local registry of active bridges, keyed by user_id. | [src](../../../core/services/jarvisx_bridge.py#L294) |
| method | `BridgeRegistry.__init__` | `(self)` | — | [src](../../../core/services/jarvisx_bridge.py#L297) |
| method | `BridgeRegistry.register` | `(self, conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L300) |
| method | `BridgeRegistry.unregister` | `(self, conn)` | Remove ONLY if the registered bridge for this user IS this conn. | [src](../../../core/services/jarvisx_bridge.py#L315) |
| method | `BridgeRegistry._evict_if_current` | `(self, user_id, conn, *, reason)` | Fjern en stale/død bro fra registret HVIS den stadig er den aktuelle for | [src](../../../core/services/jarvisx_bridge.py#L325) |
| method | `BridgeRegistry._publish_presence` | `(self)` | Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og | [src](../../../core/services/jarvisx_bridge.py#L336) |
| method | `BridgeRegistry._diagnose_no_bridge` | `(self, user_id, *, stage)` | Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt | [src](../../../core/services/jarvisx_bridge.py#L351) |
| method | `BridgeRegistry.get_bridge` | `(self, user_id)` | — | [src](../../../core/services/jarvisx_bridge.py#L388) |
| method | `BridgeRegistry.list_user_ids` | `(self)` | user_id'er med en aktiv bro (til bro_broker / override-switch). | [src](../../../core/services/jarvisx_bridge.py#L391) |
| method | `BridgeRegistry.clear` | `(self)` | Test helper — drop all registrations. | [src](../../../core/services/jarvisx_bridge.py#L395) |
| method | `BridgeRegistry.dispatch` | `(self, *, user_id, tool, args, timeout_s=…, allow_cross_process=…)` | Send tool_invoke to user's bridge, await result or timeout. | [src](../../../core/services/jarvisx_bridge.py#L401) |
| method | `BridgeRegistry._dispatch_without_local_bridge` | `(self, *, user_id, tool, args, timeout_s, allow_cross_process, stage)` | Ingen LEVENDE lokal bro for user_id (aldrig registreret, eller netop evictet | [src](../../../core/services/jarvisx_bridge.py#L501) |
| method | `BridgeRegistry._forward_cross_process` | `(self, *, user_id, tool, args, timeout_s, target_port=…)` | HTTP-forward dispatch til den proces der holder broen (dens interne endpoint). | [src](../../../core/services/jarvisx_bridge.py#L556) |
| function | `set_main_loop` | `(loop)` | Register the main uvicorn loop. Called from app startup. | [src](../../../core/services/jarvisx_bridge.py#L643) |
| function | `get_main_loop` | `()` | Return the registered main loop, or None if not set yet. | [src](../../../core/services/jarvisx_bridge.py#L649) |

## `core/services/jobs_engine.py`
_Jobs Engine — proper async job queue with provider selection and cost tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_prune_completed_jobs` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L46) |
| class | `JobResult` | `` | — | [src](../../../core/services/jobs_engine.py#L73) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/jobs_engine.py#L87) |
| function | `_load` | `()` | — | [src](../../../core/services/jobs_engine.py#L91) |
| function | `_save` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L121) |
| function | `register_handler` | `(job_type, handler)` | Register a handler function for a given job_type. | [src](../../../core/services/jobs_engine.py#L146) |
| function | `enqueue_job` | `(*, job_type, payload=…, allowed_providers=…, prefer_free_first=…, max_requests=…, max_tokens=…, max_usd=…, window_key=…, scheduled_job_id=…, priority=…)` | Create a new pending job. Returns job_id. | [src](../../../core/services/jobs_engine.py#L154) |
| function | `select_provider` | `(allowed, *, prefer_free_first=…)` | Pick the first usable provider from the list. | [src](../../../core/services/jobs_engine.py#L203) |
| function | `_pop_next_pending` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L227) |
| function | `run_next_job` | `()` | Run the highest-priority pending job via its registered handler. | [src](../../../core/services/jobs_engine.py#L235) |
| function | `cancel_job` | `(job_id)` | — | [src](../../../core/services/jobs_engine.py#L319) |
| function | `sweep_zombie_jobs` | `(stale_seconds=…)` | Mark 'running' jobs older than stale_seconds as error. | [src](../../../core/services/jobs_engine.py#L330) |
| function | `list_jobs` | `(*, status=…, limit=…)` | — | [src](../../../core/services/jobs_engine.py#L375) |
| function | `build_jobs_engine_surface` | `()` | — | [src](../../../core/services/jobs_engine.py#L382) |

## `core/services/keyring_store.py`
_Per-bruger nøgle-håndtering (spec §16.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_keyring` | `()` | — | [src](../../../core/services/keyring_store.py#L31) |
| function | `_get_or_create_kek` | `()` | Master-KEK fra runtime.json; genereres + persisteres atomisk ved første brug. | [src](../../../core/services/keyring_store.py#L45) |
| function | `_server_get_dek` | `(user_id)` | Hent (eller generér + wrap) en brugers DEK fra DB, unwrapped med KEK. | [src](../../../core/services/keyring_store.py#L72) |
| function | `get_user_key` | `(user_id)` | Brugerens 256-bit DEK. Prøver OS keyring; ellers server-side KEK/DEK (headless). | [src](../../../core/services/keyring_store.py#L86) |
| function | `delete_user_key` | `(user_id)` | Slet en brugers DEK (GDPR §16.7) — krypteret data bliver derefter ulæseligt. | [src](../../../core/services/keyring_store.py#L102) |
| function | `derive_key_from_password` | `(password, salt)` | PBKDF2-HMAC-SHA256 nøgle-derivation (fallback, §16.3). 600k iterationer. | [src](../../../core/services/keyring_store.py#L126) |
| function | `new_salt` | `()` | Tilfældigt 16-byte salt (gemmes pr. bruger, ikke hemmeligt). | [src](../../../core/services/keyring_store.py#L134) |

## `core/services/layer_tension_daemon.py`
_Layer Tension daemon — detects when two or more cognitive layers pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_layer_tension_daemon` | `(snapshot)` | Detect layer tensions from runtime snapshot. | [src](../../../core/services/layer_tension_daemon.py#L35) |
| function | `_detect_tensions` | `(snapshot)` | — | [src](../../../core/services/layer_tension_daemon.py#L61) |
| function | `_store_tension` | `(tension, now)` | — | [src](../../../core/services/layer_tension_daemon.py#L143) |
| function | `get_active_tensions` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L190) |
| function | `build_layer_tension_surface` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L194) |

## `core/services/learning_pipeline_orchestrator.py`
_Learning Pipeline Orchestrator — Phase 3 (Loop Closure)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/learning_pipeline_orchestrator.py#L44) |
| function | `is_enabled` | `()` | Check killswitch. | [src](../../../core/services/learning_pipeline_orchestrator.py#L48) |
| function | `set_enabled` | `(value)` | Toggle killswitch without restart. | [src](../../../core/services/learning_pipeline_orchestrator.py#L57) |
| function | `_recent_events` | `(*, families, minutes=…)` | Fetch recent events from eventbus by family, ordered newest-first. | [src](../../../core/services/learning_pipeline_orchestrator.py#L66) |
| function | `_route_self_evaluation` | `(event)` | self_evaluation outcome → learning_policy + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L94) |
| function | `_route_learning_policy_rule` | `(event)` | learning_policy.rule_created (conf ≥ 0.7 + evidence ≥ 2) → abstraction + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L151) |
| function | `_route_counterfactual_cycle` | `(event)` | counterfactual.cycle_complete → skill distiller + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L212) |
| function | `_route_agent_run` | `(event)` | agent_run.completed → reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L261) |
| function | `run_pipeline` | `(*, force=…)` | Run one full pipeline routing cycle. | [src](../../../core/services/learning_pipeline_orchestrator.py#L296) |
| function | `run_reflect_cycle` | `()` | Thin wrapper for REFLECT phase integration. | [src](../../../core/services/learning_pipeline_orchestrator.py#L418) |

## `core/services/learning_policy_engine.py`
_Explicit learning policy engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_learning_policies_from_episode` | `(*, episode=…, source_run_id=…)` | Extract and reinforce active policy rules from a cognitive episode. | [src](../../../core/services/learning_policy_engine.py#L25) |
| function | `reinforce_learning_policy` | `(rule)` | Insert or strengthen a learning policy rule. | [src](../../../core/services/learning_policy_engine.py#L50) |
| function | `build_learning_policy_surface` | `(*, limit=…)` | Return active policy rules for prompt/conductor use. | [src](../../../core/services/learning_policy_engine.py#L101) |
| function | `build_learning_policy_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/learning_policy_engine.py#L130) |
| function | `_load_state` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L145) |
| function | `_latest_episode` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L152) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/learning_policy_engine.py#L157) |
| function | `_rule_from_episode` | `(*, episode, learning, attention, policy, source_run_id)` | — | [src](../../../core/services/learning_policy_engine.py#L167) |
| function | `_classify_rule_key` | `(*, policy_update, next_behavior, lesson)` | — | [src](../../../core/services/learning_policy_engine.py#L194) |
| function | `_target_context` | `(rule_key)` | — | [src](../../../core/services/learning_policy_engine.py#L209) |
| function | `_initial_confidence` | `(*, episode, learning)` | — | [src](../../../core/services/learning_policy_engine.py#L219) |
| function | `_surface_directive` | `(rules)` | — | [src](../../../core/services/learning_policy_engine.py#L233) |

## `core/services/life_milestones.py`
_Life milestones — identity-defining moments surfaced in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_milestones_file` | `()` | — | [src](../../../core/services/life_milestones.py#L17) |
| function | `_manifest_file` | `()` | — | [src](../../../core/services/life_milestones.py#L21) |
| function | `get_milestones_for_prompt` | `(max_chars=…)` | Return a formatted milestones block for prompt injection, or None. | [src](../../../core/services/life_milestones.py#L25) |
| function | `get_manifest_excerpt` | `(max_chars=…)` | Return first ~600 chars of MANIFEST.md as a first-principles reminder. | [src](../../../core/services/life_milestones.py#L47) |
| function | `build_life_history_prompt_section` | `()` | Combine milestones + manifest excerpt into a prompt section. | [src](../../../core/services/life_milestones.py#L63) |
| function | `append_milestone` | `(text)` | Append a new milestone entry to MILESTONES.md. Returns True on success. | [src](../../../core/services/life_milestones.py#L71) |
| function | `build_life_milestones_surface` | `()` | — | [src](../../../core/services/life_milestones.py#L88) |
| function | `_emit_life_milestones_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/life_milestones.py#L103) |

## `core/services/life_projects.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_life_project` | `(*, title, why, source=…, source_id=…, priority=…)` | — | [src](../../../core/services/life_projects.py#L12) |
| function | `build_life_projects_surface` | `()` | — | [src](../../../core/services/life_projects.py#L36) |
| function | `abandon_life_project` | `(initiative_id, *, note=…)` | — | [src](../../../core/services/life_projects.py#L50) |
| function | `tick_life_projects_reassessment` | `(*, trigger=…, last_visible_at=…)` | Periodisk re-vurdering af aktive life projects. | [src](../../../core/services/life_projects.py#L57) |

## `core/services/liveness_registry.py`
_Liveness-registry (Stage 2, liveness-audit 2026-06-15)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_table` | `(name)` | Returnér klassifikation for en tabel. Ukendt → 'unclassified' (IKKE 'død'). | [src](../../../core/services/liveness_registry.py#L89) |
| function | `is_alive` | `(name)` | True hvis tabellen IKKE er forældreløs/død. Afløst/manuel/aktiv tæller som levende. | [src](../../../core/services/liveness_registry.py#L97) |
| function | `liveness_summary` | `()` | Aggregeret overblik — til Mission Control / anti-konfabulations-flade. | [src](../../../core/services/liveness_registry.py#L102) |

## `core/services/living_executive.py`
_Living Executive — Jarvis' active impulse/choice/action loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/living_executive.py#L31) |
| function | `_load_state` | `()` | — | [src](../../../core/services/living_executive.py#L35) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/living_executive.py#L46) |
| function | `build_living_executive_surface` | `(*, limit=…)` | — | [src](../../../core/services/living_executive.py#L50) |
| function | `choose_impulse` | `(events)` | — | [src](../../../core/services/living_executive.py#L75) |
| function | `process_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L87) |
| function | `run_once` | `(*, events=…)` | One non-daemon pass used by tests and manual MC experiments. | [src](../../../core/services/living_executive.py#L94) |
| function | `execute_impulse` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L104) |
| function | `_impulse_from_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L138) |
| function | `_impulse` | `(*, source_event_id, source_kind, felt_signal, impulse, intensity, action_id, choice, payload, cooldown_key, cooldown_seconds=…)` | — | [src](../../../core/services/living_executive.py#L284) |
| function | `_action_schedule_self_wakeup` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L311) |
| function | `_action_record_focus_intent` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L330) |
| function | `_action_create_jarvis_brain_observation` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L349) |
| function | `_action_propose_tool_plan` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L364) |
| function | `_record_trace` | `(impulse, *, status, outcome, details=…)` | — | [src](../../../core/services/living_executive.py#L405) |
| function | `_attach_memory_precedents` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L472) |
| function | `_recent_memory_precedents` | `(*, action_hint=…, tool_hint=…, limit=…)` | — | [src](../../../core/services/living_executive.py#L486) |
| function | `_choice_bias_from_precedents` | `(impulse, precedents)` | — | [src](../../../core/services/living_executive.py#L521) |
| function | `_emotional_choice_precedents` | `(*, limit)` | — | [src](../../../core/services/living_executive.py#L541) |
| function | `_tool_family` | `(tool_name)` | — | [src](../../../core/services/living_executive.py#L561) |
| function | `_runnable_tool_proposals` | `(*, tool_name, status, reason, precedents)` | — | [src](../../../core/services/living_executive.py#L569) |
| function | `_aftertaste` | `(*, status, impulse)` | — | [src](../../../core/services/living_executive.py#L630) |
| function | `start_listener` | `()` | — | [src](../../../core/services/living_executive.py#L642) |
| function | `stop_listener` | `()` | — | [src](../../../core/services/living_executive.py#L658) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/living_executive.py#L667) |

## `core/services/living_heartbeat_cycle.py`
_Living Heartbeat Cycle — Jarvis' inner life rhythm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `determine_life_phase` | `(*, hour=…)` | Determine current life phase based on time of day. | [src](../../../core/services/living_heartbeat_cycle.py#L111) |
| function | `_should_enter_play_mode` | `()` | Return True when internal state calls for unstructured exploration. | [src](../../../core/services/living_heartbeat_cycle.py#L146) |
| function | `format_life_phase_for_prompt` | `(phase)` | Format life phase info for heartbeat prompt injection. | [src](../../../core/services/living_heartbeat_cycle.py#L166) |
| function | `build_living_heartbeat_cycle_surface` | `()` | MC surface for living heartbeat cycle. | [src](../../../core/services/living_heartbeat_cycle.py#L183) |
| function | `_emit_living_heartbeat_cycle_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/living_heartbeat_cycle.py#L194) |

## `core/services/llm_pricing.py`
_Central LLM-pris-tabel + cost-beregner (WS2, 13. jul 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compute_cost_usd` | `(provider, model, *, cache_hit_tokens=…, cache_miss_tokens=…, output_tokens=…, input_tokens=…)` | Beregn cost_usd fra tokens × pris. Returnerer 0.0 for ukendte (provider, model). | [src](../../../core/services/llm_pricing.py#L22) |

## `core/services/long_arc_synthesizer.py`
_Long-arc synthesizer — monthly / quarterly / annual narrative integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_arcs_dir` | `()` | — | [src](../../../core/services/long_arc_synthesizer.py#L37) |
| function | `_existing_arcs` | `(period)` | — | [src](../../../core/services/long_arc_synthesizer.py#L43) |
| function | `_gather_weekly_manifests` | `(weeks_back)` | Read recent WEEKLY_MANIFEST.md files (only one exists; we read its current content). | [src](../../../core/services/long_arc_synthesizer.py#L47) |
| function | `_gather_crisis_markers` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L59) |
| function | `_gather_drift` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L67) |
| function | `_gather_closed_goals` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L75) |
| function | `_build_synthesis_prompt` | `(*, period, days, weekly, crises, drift, goals)` | — | [src](../../../core/services/long_arc_synthesizer.py#L89) |
| function | `synthesize_arc` | `(*, period)` | Generate a single arc (monthly/quarterly/annual). Skips if recent one exists. | [src](../../../core/services/long_arc_synthesizer.py#L133) |
| function | `list_arcs` | `(*, period=…)` | — | [src](../../../core/services/long_arc_synthesizer.py#L208) |
| function | `_exec_synthesize_arc` | `(args)` | — | [src](../../../core/services/long_arc_synthesizer.py#L228) |
| function | `_exec_list_arcs` | `(args)` | — | [src](../../../core/services/long_arc_synthesizer.py#L232) |

## `core/services/long_horizon_goals.py`
_Long-horizon goals — persistent objectives across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_goal` | `(*, title, description=…, priority=…, target_date=…, tags=…, created_by=…)` | — | [src](../../../core/services/long_horizon_goals.py#L32) |
| function | `update_goal` | `(*, goal_id, note, progress_delta=…, new_status=…, source=…)` | — | [src](../../../core/services/long_horizon_goals.py#L64) |
| function | `edit_goal` | `(goal_id, *, title=…, description=…, priority=…, target_date=…, tags=…)` | — | [src](../../../core/services/long_horizon_goals.py#L107) |
| function | `delete_goal` | `(goal_id)` | — | [src](../../../core/services/long_horizon_goals.py#L126) |
| function | `get_goal` | `(goal_id)` | — | [src](../../../core/services/long_horizon_goals.py#L136) |
| function | `get_goal_with_history` | `(goal_id, *, history_limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L140) |
| function | `list_active_goals` | `(*, limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L149) |
| function | `list_all_goals` | `(*, limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L153) |
| function | `format_active_goals_for_heartbeat` | `(*, max_goals=…)` | Compact single-paragraph summary for heartbeat prompt injection. | [src](../../../core/services/long_horizon_goals.py#L157) |
| function | `get_stats` | `()` | — | [src](../../../core/services/long_horizon_goals.py#L177) |

## `core/services/longing_signal_daemon.py`
_Longing-toward-user signal daemon — Spor-1 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_db_path` | `()` | — | [src](../../../core/services/longing_signal_daemon.py#L42) |
| function | `_hours_since` | `(iso_ts)` | Return hours since the given ISO timestamp, or None if invalid. | [src](../../../core/services/longing_signal_daemon.py#L46) |
| function | `_last_user_message_timestamp` | `()` | Return ISO timestamp of the most recent user-initiated visible turn. | [src](../../../core/services/longing_signal_daemon.py#L59) |
| function | `_last_jarvis_outreach_timestamp` | `()` | Return ISO timestamp of the last Jarvis-initiated outreach. | [src](../../../core/services/longing_signal_daemon.py#L88) |
| function | `_last_user_topic` | `()` | Best-effort recent user topic — short snippet from latest user message. | [src](../../../core/services/longing_signal_daemon.py#L115) |
| function | `compute_longing_intensity` | `()` | Compute current longing-toward-user intensity and supporting context. | [src](../../../core/services/longing_signal_daemon.py#L140) |
| function | `run_longing_signal_daemon_tick` | `()` | One tick of the longing daemon. Called by daemon_manager on cadence. | [src](../../../core/services/longing_signal_daemon.py#L200) |
| function | `build_longing_signal_daemon_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/longing_signal_daemon.py#L267) |

