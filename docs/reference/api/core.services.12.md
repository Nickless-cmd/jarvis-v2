# `core.services.12` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/heartbeat_phases.py`
_Heartbeat phases — explicit Sense / Reflect / Act structure on top of existing tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_active_recently` | `(*, window_minutes=…)` | Cheap check: has any user-role chat message landed in the last N minutes? | [src](../../../core/services/heartbeat_phases.py#L39) |
| function | `_inner_tick_during_chat_enabled` | `()` | Skal de indre daemoner køre mens brugeren aktivt chatter (hans sind vågent mens I | [src](../../../core/services/heartbeat_phases.py#L61) |
| function | `sense_phase` | `(*, name=…)` | Gather signals for this tick. Pure-read — no side effects. | [src](../../../core/services/heartbeat_phases.py#L76) |
| function | `_classify_activity` | `(signals)` | Classify current activity level from signals. | [src](../../../core/services/heartbeat_phases.py#L161) |
| function | `_identify_priorities` | `(signals)` | Heuristic — what should this tick attend to? | [src](../../../core/services/heartbeat_phases.py#L171) |
| function | `reflect_phase` | `(signals)` | Synthesize reflection. Heuristic-only by default; LLM optional. | [src](../../../core/services/heartbeat_phases.py#L187) |
| function | `_collect_active_goals` | `()` | Fetch active goals for chain proposal targeting. | [src](../../../core/services/heartbeat_phases.py#L247) |
| function | `_propose_skill_chains_in_idle` | `(max_goals=…)` | Propose skill chains for active goals. Time-bounded, never blocks. | [src](../../../core/services/heartbeat_phases.py#L256) |
| function | `format_chain_proposals` | `(max_chars=…)` | Format recent chain proposals for awareness injection. | [src](../../../core/services/heartbeat_phases.py#L303) |
| function | `clear_chain_proposals` | `()` | Clear cached chain proposals (e.g. after execution or user dismiss). | [src](../../../core/services/heartbeat_phases.py#L326) |
| function | `get_chain_proposals` | `()` | Return current chain proposals for inspection. | [src](../../../core/services/heartbeat_phases.py#L331) |
| function | `productive_idle` | `(*, budget_seconds=…)` | Run light maintenance work when there's no clear action. Time-bounded. | [src](../../../core/services/heartbeat_phases.py#L336) |
| function | `act_phase` | `(*, signals, reflection, name=…, trigger=…)` | Either run normal heartbeat tick OR productive idle, based on reflection. | [src](../../../core/services/heartbeat_phases.py#L576) |
| function | `tick_with_phases` | `(*, name=…, trigger=…)` | Run all 3 phases in sequence, return structured result. | [src](../../../core/services/heartbeat_phases.py#L664) |
| function | `_exec_phased_tick` | `(args)` | — | [src](../../../core/services/heartbeat_phases.py#L709) |
| function | `_exec_sense_only` | `(args)` | Read-only: gather current signals without running reflection or action. | [src](../../../core/services/heartbeat_phases.py#L716) |

## `core/services/heartbeat_provider_fallback.py`
_Heartbeat provider fallback — cheap cloud lane when primary (Groq) fails._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute_openai_compat_heartbeat_prompt` | `(*, prompt, target, max_tokens=…, temperature=…)` | Call an OpenAI-chat/completions-compatible provider for heartbeat. | [src](../../../core/services/heartbeat_provider_fallback.py#L53) |
| function | `try_heartbeat_cheap_fallback` | `(prompt)` | Try cheap lane providers (skip groq + ollamafreeapi) as heartbeat fallback. | [src](../../../core/services/heartbeat_provider_fallback.py#L125) |

## `core/services/heartbeat_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_inner_life_action_hints` | `()` | Tynd delegation til `heartbeat_action_hints` (Boy Scout: denne fil er 7.6k linjer). | [src](../../../core/services/heartbeat_runtime.py#L154) |
| class | `HeartbeatExecutionResult` | `` | — | [src](../../../core/services/heartbeat_runtime.py#L250) |
| function | `start_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L256) |
| function | `stop_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L298) |
| function | `_cheap_heartbeat_schedule_state` | `(name)` | Compute just the schedule-state dict without touching sub-surfaces. | [src](../../../core/services/heartbeat_runtime.py#L310) |
| function | `poll_heartbeat_schedule` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L328) |
| function | `_advance_schedule_after_idle_beat` | `(*, name)` | Avancér skemaet let hvis det STADIG er 'due' efter en beat — dvs. beat'en landede i | [src](../../../core/services/heartbeat_runtime.py#L379) |
| function | `_run_heartbeat_tick_with_deadline` | `(*, name, trigger, deadline_seconds=…)` | Run a heartbeat tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L411) |
| function | `_poll_heartbeat_schedule_with_trigger` | `(*, name, due_trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L472) |
| function | `heartbeat_runtime_surface` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L502) |
| function | `_heartbeat_runtime_surface_uncached` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L526) |
| function | `_build_cognitive_surfaces` | `()` | Build cognitive architecture surfaces safely (never raise). | [src](../../../core/services/heartbeat_runtime.py#L624) |
| function | `_safe_surface` | `(target, key, builder)` | Call builder and store result; swallow any errors. | [src](../../../core/services/heartbeat_runtime.py#L1199) |
| function | `run_heartbeat_tick` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1228) |
| function | `_daemon_tick_with_deadline` | `(name, fn, *args, deadline_seconds=…, **kwargs)` | Run a daemon tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L1247) |
| function | `_run_heartbeat_tick_locked` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1310) |
| function | `load_heartbeat_policy` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L2282) |
| function | `_build_heartbeat_context` | `(*, policy, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2328) |
| function | `_build_heartbeat_cognitive_frame` | `(*, merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L2541) |
| function | `_build_executive_visible_state` | `(*, merged_state, context)` | — | [src](../../../core/services/heartbeat_runtime.py#L2561) |
| function | `_decide_executive_action` | `(*, merged_state, context, now_iso)` | — | [src](../../../core/services/heartbeat_runtime.py#L2580) |
| function | `_execute_executive_decision` | `(executive_decision)` | — | [src](../../../core/services/heartbeat_runtime.py#L2647) |
| function | `_log_liveness_dedup` | `(signal, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2687) |
| function | `_build_heartbeat_liveness_signal` | `(*, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2710) |
| function | `_select_heartbeat_target` | `(policy=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3314) |
| function | `_runtime_selected_local_target` | `(*, settings)` | — | [src](../../../core/services/heartbeat_runtime.py#L3439) |
| function | `_phase1_rule_based_decision` | `(*, policy, open_loops, liveness=…, prompt=…)` | Rule-based heartbeat decision for phase1-runtime or LLM-failure fallback. | [src](../../../core/services/heartbeat_runtime.py#L3462) |
| function | `_execute_heartbeat_model` | `(*, prompt, target, policy, open_loops, liveness=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3571) |
| function | `_recent_ping_history` | `(*, limit=…)` | Return the last N assistant ping_text strings already delivered. | [src](../../../core/services/heartbeat_runtime.py#L3658) |
| function | `_user_recently_active` | `(minutes)` | Return True if any user-role chat message landed within the window. | [src](../../../core/services/heartbeat_runtime.py#L3692) |
| function | `_active_chat_gate_blocked_result` | `(*, tick_id, decision_type, minutes)` | Build the blocked-result + emit deferred event for active-chat gate. | [src](../../../core/services/heartbeat_runtime.py#L3724) |
| function | `_heartbeat_prompt_text` | `(base_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3754) |
| function | `_parse_heartbeat_decision` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3881) |
| function | `_parse_heartbeat_decision_bounded` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3903) |
| function | `_bounded_heartbeat_failure_decision` | `(*, failure_kind, detail, target)` | — | [src](../../../core/services/heartbeat_runtime.py#L3917) |
| function | `_validate_heartbeat_decision` | `(*, decision, policy, workspace_dir, tick_id)` | — | [src](../../../core/services/heartbeat_runtime.py#L3943) |
| function | `_deliver_heartbeat_proposal` | `(*, policy, tick_id, summary, proposed_action)` | — | [src](../../../core/services/heartbeat_runtime.py#L4491) |
| function | `_deliver_heartbeat_ping_directly` | `(*, policy, tick_id, ping_text, summary)` | Deliver an LLM-authored ping straight to webchat. | [src](../../../core/services/heartbeat_runtime.py#L4648) |
| function | `_dispatch_runtime_hook_events_safely` | `(*, event_kinds=…, limit=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L4868) |
| function | `_recover_bounded_heartbeat_liveness_decision` | `(*, decision, policy, liveness)` | — | [src](../../../core/services/heartbeat_runtime.py#L4888) |
| function | `_run_bounded_conflict_resolution` | `(*, decision, context, policy)` | Run conflict resolution using existing runtime signals. | [src](../../../core/services/heartbeat_runtime.py#L4946) |
| function | `_apply_conflict_resolution_to_decision` | `(*, decision, conflict_trace)` | Apply conflict resolution to modify or preserve the decision. | [src](../../../core/services/heartbeat_runtime.py#L5033) |
| function | `_execute_continue_internal` | `(*, conflict_trace, trigger)` | Execute a bounded internal continuation when conflict chose continue_internal. | [src](../../../core/services/heartbeat_runtime.py#L5049) |
| function | `_heartbeat_ping_candidate_ready` | `(*, policy)` | — | [src](../../../core/services/heartbeat_runtime.py#L5104) |
| function | `_execute_heartbeat_internal_action` | `(*, action_type, tick_id, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L5125) |
| function | `_summarize_heartbeat_capability_invocations` | `(invocations)` | — | [src](../../../core/services/heartbeat_runtime.py#L6642) |
| function | `_record_heartbeat_outcome` | `(*, policy, persisted, tick_id, trigger, tick_status, decision_type, decision_summary, decision_reason, blocked_reason, currently_ticking, last_trigger_source, provider, model, lane, budget_status, model_source=…, resolution_status=…, fallback_used=…, execution_status=…, parse_status=…, ping_eligible, ping_result, action_status, action_summary, action_type, action_artifact, raw_response, input_tokens, output_tokens, cost_usd, started_at, finished_at, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L6682) |
| function | `_merge_runtime_state` | `(*, policy, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6860) |
| function | `_tick_blocked_reason` | `(merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L6947) |
| function | `_compute_next_tick_at` | `(*, interval_minutes, last_tick_at, enabled)` | — | [src](../../../core/services/heartbeat_runtime.py#L6961) |
| function | `_resolve_tick_activity_state` | `(*, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6971) |
| function | `_write_heartbeat_state_artifact` | `(*, workspace_dir, payload)` | — | [src](../../../core/services/heartbeat_runtime.py#L7007) |
| function | `_default_persisted_state` | `()` | — | [src](../../../core/services/heartbeat_runtime.py#L7018) |
| function | `_heartbeat_state_summary` | `(*, enabled, schedule_status, last_decision_type, last_result)` | — | [src](../../../core/services/heartbeat_runtime.py#L7057) |
| function | `_persist_runtime_state` | `(*, policy, persisted, now, overrides)` | — | [src](../../../core/services/heartbeat_runtime.py#L7071) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/heartbeat_runtime.py#L7134) |
| function | `_heartbeat_busy_result` | `(*, name, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L7161) |
| function | `_heartbeat_scheduler_loop` | `(*, name, startup_recovery_requested)` | — | [src](../../../core/services/heartbeat_runtime.py#L7211) |
| function | `_detect_startup_drift` | `(*, name, phase, overrides, actual_state)` | Compare intended overrides against what SELECT-back actually returned. | [src](../../../core/services/heartbeat_runtime.py#L7252) |
| function | `_persist_runtime_state_with_diagnostics` | `(*, name, phase, policy, persisted, now, overrides)` | Wrapper around _persist_runtime_state that re-raises with stack trace | [src](../../../core/services/heartbeat_runtime.py#L7316) |
| function | `_prepare_scheduler_startup` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7357) |
| function | `_mark_scheduler_stopped` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7495) |
| function | `_emit_schedule_transitions` | `(state)` | — | [src](../../../core/services/heartbeat_runtime.py#L7520) |
| function | `_heartbeat_runtime_bias_from_recent_work` | `(*, kind)` | — | [src](../../../core/services/heartbeat_runtime.py#L7561) |
| function | `call_heartbeat_llm_simple` | `(prompt, *, max_tokens=…)` | Call the heartbeat model with a plain prompt. Returns the response text. | [src](../../../core/services/heartbeat_runtime.py#L7601) |

## `core/services/heartbeat_runtime_helpers.py`
_Pure leaf helpers extracted from ``heartbeat_runtime``._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_log_debug` | `(message, **fields)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L25) |
| function | `_hours_since_iso` | `(value)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L33) |
| function | `_detect_visible_language` | `()` | Detect the language Bjørn is currently using in webchat. | [src](../../../core/services/heartbeat_runtime_helpers.py#L47) |
| function | `_classify_heartbeat_execution_exception` | `(exc)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L105) |
| function | `_http_error_detail` | `(exc)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L114) |
| function | `_parse_heartbeat_key_values` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L124) |
| function | `_parse_bool` | `(value, *, default, truthy=…)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L136) |
| function | `_parse_int` | `(value, *, default, minimum)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L154) |
| function | `_extract_json_object` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L164) |
| function | `_extract_openai_text` | `(data)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L192) |
| function | `_extract_openrouter_text` | `(data)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L208) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L219) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L228) |
| function | `_value_drifted` | `(expected, actual)` | True if expected ≠ actual under tolerant comparison. | [src](../../../core/services/heartbeat_runtime_helpers.py#L232) |

## `core/services/heartbeat_runtime_influence.py`
_``_build_influence_trace`` extracted from ``heartbeat_runtime`` (Boy-Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_influence_trace` | `(*, private_brain, liveness, self_knowledge_summary, embodied_state=…, affective_meta_state=…, epistemic_runtime_state=…, loop_runtime=…, prompt_evolution=…, subagent_ecology=…, council_runtime=…, adaptive_planner=…, adaptive_reasoning=…, dream_influence=…, guided_learning=…, adaptive_learning=…, self_system_code_awareness=…, tool_intent=…)` | Build a bounded trace of what cognitive inputs were available to heartbeat. | [src](../../../core/services/heartbeat_runtime_influence.py#L27) |

## `core/services/heartbeat_runtime_providers.py`
_Concrete heartbeat provider-executor bodies extracted from ``heartbeat_runtime``._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_execute_ollama_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L23) |
| function | `_execute_openai_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L66) |
| function | `_execute_openrouter_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L92) |
| function | `_execute_groq_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L136) |

## `core/services/hf_connector.py`
_Hugging Face-connector — søg modeller/datasets via Hub API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `()` | — | [src](../../../core/services/hf_connector.py#L43) |
| function | `_get` | `(path, params=…)` | — | [src](../../../core/services/hf_connector.py#L52) |
| function | `search_models` | `(query, *, limit=…)` | — | [src](../../../core/services/hf_connector.py#L67) |
| function | `model_info` | `(model_id)` | — | [src](../../../core/services/hf_connector.py#L85) |

## `core/services/hollow_promise_guard.py`
_Hollow-promise guard (4. jul) — fang "lovede handling, kaldte intet værktøj"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_promise_of_action` | `(text)` | True hvis `text` lover at assistenten tager en handling imminent. Self-safe. | [src](../../../core/services/hollow_promise_guard.py#L73) |
| function | `is_hollow_promise` | `(final_text, total_tool_calls, user_message=…, nudged_already=…, last_round_tool_calls=…)` | Tom løfte = lovede handling + NUL tool-kald i SIDSTE runde + ikke allerede nudget. | [src](../../../core/services/hollow_promise_guard.py#L88) |
| function | `hollow_promise_guard_enabled` | `()` | Default TRUE (Bjørn bad om værnet 4. jul). Env `JARVIS_HOLLOW_PROMISE_GUARD` vinder; | [src](../../../core/services/hollow_promise_guard.py#L120) |

## `core/services/identity_canon.py`
_Kanonisk identitets-narrativ-store — den strukturelle kur mod sonnet-spøgelset._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/identity_canon.py#L47) |
| function | `_ensure_identity_canon_table` | `(conn)` | Lazy DDL for begge tabeller. Idempotent. Self-safe (kalderen wrapper). | [src](../../../core/services/identity_canon.py#L51) |
| function | `_seed_if_empty` | `(conn)` | Idempotent seed: sonnet-korrektionen (kritisk) + valgfrit voice-canon. Kaldes under _ensure. | [src](../../../core/services/identity_canon.py#L77) |
| function | `_ensure_and_seed` | `(conn)` | — | [src](../../../core/services/identity_canon.py#L104) |
| function | `set_canon_thread` | `(*, thread, canon_text, updated_by=…)` | Owner/governed-self-surgery opdaterer en kanon-tråd. Upsert. Self-safe. | [src](../../../core/services/identity_canon.py#L117) |
| function | `get_canon` | `()` | Alle aktive kanon-tråde som {thread: canon_text}. Self-safe (tom dict ved fejl). | [src](../../../core/services/identity_canon.py#L138) |
| function | `list_acknowledged_corrections` | `(*, active_only=…)` | De kendte konfabulationer (anti-drift-listen). Self-safe (tom liste ved fejl). | [src](../../../core/services/identity_canon.py#L151) |
| function | `add_acknowledged_correction` | `(*, claim_pattern, reason)` | Tilføj en konfabulation til anti-drift-listen. Self-safe. | [src](../../../core/services/identity_canon.py#L168) |
| function | `build_identity_canon_surface` | `()` | Central-CLI-view: kanon-tråde + anerkendte korrektioner + seneste drift-fangster. Self-safe. | [src](../../../core/services/identity_canon.py#L187) |
| function | `_recent_drift_catches` | `(limit=…)` | Seneste identity_drift-observe-hændelser fra central trace, hvis let tilgængeligt. Self-safe. | [src](../../../core/services/identity_canon.py#L206) |

## `core/services/identity_composer.py`
_Identity Composer — entity name lookup and signal-driven preamble._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_identity_file` | `()` | Resolve IDENTITY.md path lazily so shared_dir() reads env at call time. | [src](../../../core/services/identity_composer.py#L18) |
| function | `get_entity_name` | `()` | Return the entity name from IDENTITY.md. Cached after first read. | [src](../../../core/services/identity_composer.py#L24) |
| function | `get_entity_pronouns` | `()` | Return the entity pronouns from IDENTITY.md. Cached after first read. | [src](../../../core/services/identity_composer.py#L32) |
| function | `invalidate_identity_cache` | `()` | Clear name + pronouns caches. Call after editing IDENTITY.md. | [src](../../../core/services/identity_composer.py#L43) |
| function | `identity_prompt_prefix` | `()` | Return 'Du er <name>' — used as role-setting prefix in cheap-lane prompts. | [src](../../../core/services/identity_composer.py#L55) |
| function | `_parse_field_from_identity` | `(field, fallback)` | — | [src](../../../core/services/identity_composer.py#L64) |
| function | `_read_bearing` | `()` | Read current_bearing from personality vector. Returns '' on failure. | [src](../../../core/services/identity_composer.py#L77) |
| function | `_read_energy` | `()` | Read energy_level from body_state surface. Returns '' on failure. | [src](../../../core/services/identity_composer.py#L87) |
| function | `build_identity_preamble` | `()` | Return signal-driven identity string: '{name}. {bearing}. {energy}.' | [src](../../../core/services/identity_composer.py#L97) |
| function | `build_identity_composer_surface` | `()` | Mission Control surface for the identity preamble composer. | [src](../../../core/services/identity_composer.py#L130) |

## `core/services/identity_drift_daemon.py`
_Identity drift daemon — detect unauthorized changes to identity files._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/identity_drift_daemon.py#L58) |
| function | `_sha256` | `(content)` | — | [src](../../../core/services/identity_drift_daemon.py#L62) |
| function | `_workspace_dir` | `()` | Resolve the shared state dir for identity files. | [src](../../../core/services/identity_drift_daemon.py#L71) |
| function | `_was_change_logged` | `(filename, change_at)` | Check identity_mutation_log for any entry on this file within | [src](../../../core/services/identity_drift_daemon.py#L82) |
| function | `_classify_drift_via_llm` | `(*, filename, prior_content, current_content)` | Ask the quality lane to classify the change. | [src](../../../core/services/identity_drift_daemon.py#L110) |
| function | `_check_one_file` | `(workspace_dir, filename, now)` | Examine one watched file. Returns a per-file result dict. | [src](../../../core/services/identity_drift_daemon.py#L173) |
| function | `tick_identity_drift_daemon` | `()` | Run one identity-drift detection cycle if cadence elapsed. | [src](../../../core/services/identity_drift_daemon.py#L280) |
| function | `build_identity_drift_surface` | `()` | — | [src](../../../core/services/identity_drift_daemon.py#L318) |

## `core/services/identity_drift_guard.py`
_Anti-drift-validator — kernen i den kanoniske identitets-store (Spec H §2.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_enforce` | `()` | Shadow-først: strip er OFF indtil flag EKSPLICIT flippes efter shadow-eval. Self-safe. | [src](../../../core/services/identity_drift_guard.py#L20) |
| function | `_patterns` | `()` | Aktive acknowledged_corrections. Self-safe (tom liste ved fejl). | [src](../../../core/services/identity_drift_guard.py#L30) |
| function | `_matches` | `(text_low, claim_pattern)` | Returnér det første matchende nøgleord/alternativ (pipe-separeret) — ellers None. Self-safe. | [src](../../../core/services/identity_drift_guard.py#L39) |
| function | `_observe` | `(source, flags)` | Metadata-only observe (correction_id/source/count) — ALDRIG narrativ-teksten (§24.4). Self-safe. | [src](../../../core/services/identity_drift_guard.py#L52) |
| function | `identity_drift_guard` | `(text, *, source)` | Scan `text` for kendte konfabulationer → observe drift. | [src](../../../core/services/identity_drift_guard.py#L68) |
| function | `_strip` | `(text, flags)` | Fjern sætninger der indeholder et matchende nøgleord (senere-fase enforce). Self-safe. | [src](../../../core/services/identity_drift_guard.py#L104) |

## `core/services/identity_drift_proposer.py`
_Identity drift proposer — when drift is sustained, propose IDENTITY.md update._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_analyze_long_drift` | `(*, lookback_days=…)` | Compare last 7 days of snapshots against the rest of the lookback window. | [src](../../../core/services/identity_drift_proposer.py#L55) |
| function | `propose_identity_update_if_drifted` | `()` | If sustained drift detected, file a plan_proposal to update IDENTITY.md. | [src](../../../core/services/identity_drift_proposer.py#L120) |
| function | `_exec_propose_identity_drift` | `(args)` | — | [src](../../../core/services/identity_drift_proposer.py#L176) |

## `core/services/identity_guard.py`
_Identity-mismatch-detection + pushback (spec 2026-06-21 §3, §4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `extract_claimed_name` | `(message)` | Returnér det erklærede navn (normaliseret, Title-case) eller None. | [src](../../../core/services/identity_guard.py#L37) |
| function | `_known_user_names` | `()` | Map normaliseret display-navn → user_id, fra users.json (best-effort). | [src](../../../core/services/identity_guard.py#L49) |
| function | `_pushback_count` | `(session_id)` | — | [src](../../../core/services/identity_guard.py#L64) |
| function | `_bump_pushback` | `(session_id)` | — | [src](../../../core/services/identity_guard.py#L72) |
| function | `reset_pushback` | `(session_id)` | — | [src](../../../core/services/identity_guard.py#L81) |
| function | `_display_name_for` | `(user_id)` | — | [src](../../../core/services/identity_guard.py#L88) |
| function | `guard_incoming` | `(message, *, session_id, user_id)` | Samlet gate FØR LLM-kald — Auth-cluster GENNEM Den Intelligente Central (observe). | [src](../../../core/services/identity_guard.py#L100) |
| function | `_guard_incoming_impl` | `(message, *, session_id, user_id)` | Samlet gate FØR LLM-kald: (1) låst session/konto → mute, (2) identity-mismatch | [src](../../../core/services/identity_guard.py#L120) |
| function | `check_identity` | `(message, *, session_id, session_user_id, session_display_name=…)` | Kør identity-guard på en indgående besked. | [src](../../../core/services/identity_guard.py#L150) |

## `core/services/identity_mutation_log.py`
_Identity mutation log — full audit trail for Tier 3 auto-mutations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_auto_mutation_enabled` | `()` | Read kill switch from authorization file. | [src](../../../core/services/identity_mutation_log.py#L48) |
| function | `is_target_authorized` | `(path)` | Check if a target path is in the authorized Tier 3 list. | [src](../../../core/services/identity_mutation_log.py#L63) |
| function | `is_infrastructure_blocked` | `(target)` | Check if target hits an infrastructure-blocked module. | [src](../../../core/services/identity_mutation_log.py#L71) |
| function | `_hash_text` | `(text)` | — | [src](../../../core/services/identity_mutation_log.py#L77) |
| function | `_diff_summary` | `(before, after)` | Compact diff stats. | [src](../../../core/services/identity_mutation_log.py#L81) |
| function | `record_mutation` | `(*, target_path, before_content, after_content, reason, proposer=…)` | Record a mutation for audit. Returns mutation_id for rollback reference. | [src](../../../core/services/identity_mutation_log.py#L95) |
| function | `rollback_mutation` | `(mutation_id)` | Restore the BEFORE content for a recorded mutation. | [src](../../../core/services/identity_mutation_log.py#L163) |
| function | `list_mutations` | `(*, limit=…, target_filter=…)` | — | [src](../../../core/services/identity_mutation_log.py#L206) |
| function | `_exec_list_identity_mutations` | `(args)` | — | [src](../../../core/services/identity_mutation_log.py#L230) |
| function | `_exec_rollback_identity_mutation` | `(args)` | — | [src](../../../core/services/identity_mutation_log.py#L240) |
| function | `_exec_identity_mutation_status` | `(args)` | — | [src](../../../core/services/identity_mutation_log.py#L244) |

## `core/services/identity_sketch.py`
_Persistent Identity Sketch — dynamic "who am I right now" document._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_identity_sketch` | `()` | Read current sketch from state file. Returns {} if never written. | [src](../../../core/services/identity_sketch.py#L48) |
| function | `identity_sketch_surface` | `()` | Mission Control surface — current sketch status. | [src](../../../core/services/identity_sketch.py#L53) |
| function | `update_identity_sketch` | `(trigger=…)` | Generate fresh sketch from live signals and persist it. | [src](../../../core/services/identity_sketch.py#L72) |
| function | `_gather_signals` | `()` | Collect live signals for sketch generation. Gracefully handles failures. | [src](../../../core/services/identity_sketch.py#L112) |
| function | `_generate_sketch_text` | `(signals)` | Call compact_llm to generate sketch text from signals. | [src](../../../core/services/identity_sketch.py#L202) |
| function | `_fallback_sketch` | `(signals)` | Simple fallback sketch when compact_llm is unavailable. | [src](../../../core/services/identity_sketch.py#L250) |
| function | `_is_stale` | `(updated_at, *, ttl_seconds=…)` | Check if sketch is older than ttl_seconds (default 6 hours). | [src](../../../core/services/identity_sketch.py#L276) |
| function | `tick_identity_sketch_daemon` | `()` | Heartbeat daemon tick — refresh the sketch when stale (>6h). | [src](../../../core/services/identity_sketch.py#L295) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/identity_sketch.py#L340) |

## `core/services/idle_consolidation.py`
_Bounded sleep / idle consolidation light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_idle_consolidation` | `(*, trigger=…, last_visible_at=…)` | Run one bounded idle consolidation pass. | [src](../../../core/services/idle_consolidation.py#L25) |
| function | `build_idle_consolidation_from_inputs` | `(*, private_brain_context, witness_surface, emergent_surface, embodied_state, loop_runtime, inner_voice_state, now=…)` | Build a bounded consolidation plan from runtime truth inputs. | [src](../../../core/services/idle_consolidation.py#L183) |
| function | `build_idle_consolidation_surface` | `()` | — | [src](../../../core/services/idle_consolidation.py#L312) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/idle_consolidation.py#L342) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/idle_consolidation.py#L368) |
| function | `_latest_sleep_consolidation_record` | `()` | — | [src](../../../core/services/idle_consolidation.py#L393) |
| function | `_classify_consolidation_state` | `(*, witness_surface, emergent_surface, embodied_state, loop_runtime)` | — | [src](../../../core/services/idle_consolidation.py#L400) |
| function | `_choose_focus` | `(*, witness_summary, emergent_summary, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L419) |
| function | `_build_summary` | `(*, consolidation_state, source_inputs, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L435) |
| function | `_build_detail` | `(*, brain_summary, source_inputs, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L451) |
| function | `_is_near_duplicate` | `(summary, recent_records)` | — | [src](../../../core/services/idle_consolidation.py#L471) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/idle_consolidation.py#L487) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/idle_consolidation.py#L512) |

## `core/services/idle_thinking.py`
_Idle Thinking — Jarvis tænker frit når han er alene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_idle_thought` | `()` | Run a single idle thought when in appropriate phase. | [src](../../../core/services/idle_thinking.py#L18) |
| function | `build_idle_thinking_surface` | `()` | — | [src](../../../core/services/idle_thinking.py#L83) |

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
| function | `initiatives_prompt_section` | `()` | Awareness-sektion: de impulser han SELV har rejst, men aldrig fik sagt. | [src](../../../core/services/initiative_queue.py#L516) |

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
_Inner-visible support signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_inner_visible_support_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L36) |
| function | `refresh_runtime_inner_visible_support_signal_statuses` | `()` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L70) |
| function | `build_runtime_inner_visible_support_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L74) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L78) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L212) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L222) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L232) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L248) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L278) |
| function | `_inner_visible_support_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L341) |
| function | `_focus_key` | `(private_state, curiosity_state)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L369) |
| function | `_derive_support_tone` | `(*, state_tone, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L380) |
| function | `_derive_support_stance` | `(*, state_tone, curiosity_type, contradiction_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L394) |
| function | `_derive_support_directness` | `(*, state_pressure, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L406) |
| function | `_derive_support_watchfulness` | `(*, state_pressure, curiosity_pull, curiosity_type, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L416) |
| function | `_derive_support_momentum` | `(*, state_pressure, curiosity_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L432) |
| function | `_bounded_support_summary` | `(*, private_state, curiosity_state, executive_contradiction, tone, stance)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L440) |
| function | `_grounding_mode` | `(*, has_curiosity, has_executive_contradiction)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L463) |
| function | `_supports_executive_sharpening` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L473) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L482) |
| function | `_canonical_focus_segment` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L488) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L495) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L502) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L514) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L525) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L533) |

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
| function | `_build_voice_line_prompt` | `(*, mood_tone, self_position, current_concern, current_pull, **_extra)` | Prompt for protected_inner_voice._voice_line's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L359) |
| function | `_build_private_summary_prompt` | `(*, status, focus, uncertainty, work_signal, **_extra)` | Prompt for private_inner_note._private_summary's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L388) |
| function | `shadow_helpful_signal` | `(*, status, focus, work_signal, template_output)` | — | [src](../../../core/services/inner_voice_shadow.py#L417) |
| function | `generate_appraisal` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…, expiry_seconds=…, allowed_effects=…)` | State-first appraisal: returns the full structured record. | [src](../../../core/services/inner_voice_shadow.py#L431) |
| function | `_persist_record` | `(record, *, template_output)` | Persist an AppraisalRecord to the shadow audit table. | [src](../../../core/services/inner_voice_shadow.py#L526) |
| function | `_generate_via_llm` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…)` | Narrative-first wrapper for backwards compatibility. | [src](../../../core/services/inner_voice_shadow.py#L550) |
| function | `generate_helpful_signal_via_llm` | `(*, status, focus, work_signal, fallback, timeout_seconds=…)` | Production path for private_growth_note._helpful_signal. | [src](../../../core/services/inner_voice_shadow.py#L579) |
| function | `generate_private_summary_via_llm` | `(*, status, focus, uncertainty, work_signal, fallback, timeout_seconds=…)` | Production path for private_inner_note._private_summary. | [src](../../../core/services/inner_voice_shadow.py#L601) |
| function | `generate_voice_line_via_llm` | `(*, mood_tone, self_position, current_concern, current_pull, fallback, timeout_seconds=…)` | Production path for protected_inner_voice._voice_line. | [src](../../../core/services/inner_voice_shadow.py#L628) |
| function | `recent_comparisons` | `(function_name=…, *, limit=…)` | Pull recent shadow records for human comparison. | [src](../../../core/services/inner_voice_shadow.py#L657) |
| function | `shadow_stats` | `(function_name=…)` | Aggregate stats across all shadow records for one function. | [src](../../../core/services/inner_voice_shadow.py#L679) |

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
| function | `_run_producer_bounded` | `(spec, *, trigger, last_visible_at, timeout_s)` | Kør en producer i sin EGEN dæmon-tråd med en hård timeout. | [src](../../../core/services/internal_cadence.py#L166) |
| function | `run_cadence_tick` | `(*, trigger=…, last_visible_at_iso=…)` | Run one cadence tick: evaluate and dispatch all registered producers. | [src](../../../core/services/internal_cadence.py#L211) |
| function | `get_cadence_state` | `()` | Return current cadence layer state for MC observability. | [src](../../../core/services/internal_cadence.py#L387) |
| function | `_ensure_producers_registered` | `()` | Register known producers if not already registered. | [src](../../../core/services/internal_cadence.py#L426) |
| function | `run_cadence_tick_with_bootstrap` | `(*, trigger=…, last_visible_at_iso=…)` | Bootstrap producers and run a cadence tick. | [src](../../../core/services/internal_cadence.py#L454) |
| function | `_run_injection_refresh_tick` | `()` | Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path). | [src](../../../core/services/internal_cadence.py#L477) |
| function | `_scheduler_loop` | `()` | Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds. | [src](../../../core/services/internal_cadence.py#L492) |
| function | `start_cadence_scheduler` | `()` | Spawn the standalone cadence scheduler thread. Idempotent. | [src](../../../core/services/internal_cadence.py#L545) |
| function | `stop_cadence_scheduler` | `()` | Signal the scheduler thread to exit. Best-effort; daemon dies with process. | [src](../../../core/services/internal_cadence.py#L560) |

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
_Internal-opposition signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_internal_opposition_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L41) |
| function | `refresh_runtime_internal_opposition_signal_statuses` | `()` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L49) |
| function | `build_runtime_internal_opposition_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L53) |
| function | `_extract_internal_opposition_candidates` | `(*_args, **_kwargs)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L58) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L237) |
| function | `_internal_opposition_track_summary` | `(items, message)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L267) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L303) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L308) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L313) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L318) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L323) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L328) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L333) |
| function | `_world_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L338) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L343) |

## `core/services/irony_daemon.py`
_Irony daemon — situational self-distance and absurd self-observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_irony_daemon` | `(*, skip_event_gate=…)` | — | [src](../../../core/services/irony_daemon.py#L20) |
| function | `get_latest_irony_observation` | `()` | — | [src](../../../core/services/irony_daemon.py#L52) |
| function | `build_irony_surface` | `()` | — | [src](../../../core/services/irony_daemon.py#L56) |
| function | `_maybe_reset_daily_count` | `()` | — | [src](../../../core/services/irony_daemon.py#L65) |
| function | `_collect_snapshot` | `()` | — | [src](../../../core/services/irony_daemon.py#L73) |
| function | `_detect_irony_conditions` | `(snapshot)` | — | [src](../../../core/services/irony_daemon.py#L98) |
| function | `_generate_observation` | `(snapshot, condition)` | — | [src](../../../core/services/irony_daemon.py#L111) |
| function | `_store_observation` | `(observation, condition)` | — | [src](../../../core/services/irony_daemon.py#L138) |

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
| function | `_embed_texts` | `(texts)` | Batch-variant af _embed_text: ÉT ollama round-trip for hele listen (via | [src](../../../core/services/jarvis_brain.py#L565) |
| function | `_embedding_to_blob` | `(v)` | — | [src](../../../core/services/jarvis_brain.py#L582) |
| function | `_embedding_from_blob` | `(blob, dim)` | — | [src](../../../core/services/jarvis_brain.py#L586) |
| function | `embed_pending_entries` | `()` | Embed alle entries i index'et der mangler embedding. Returnerer antal. | [src](../../../core/services/jarvis_brain.py#L590) |
| function | `search_brain` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Hybrid embedding search: 0.7*cosine + 0.3*effective_salience + temporal boost. | [src](../../../core/services/jarvis_brain.py#L621) |
| function | `_compute_search_temporal_boost` | `(candidate_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost for search candidates. | [src](../../../core/services/jarvis_brain.py#L739) |
| function | `bump_salience` | `(entry_id, now=…)` | Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil. | [src](../../../core/services/jarvis_brain.py#L780) |
| function | `archive_entry` | `(entry_id, *, reason=…, now=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/services/jarvis_brain.py#L824) |
| function | `supersede` | `(*, old_ids, new_id, now=…)` | Mark old entries as superseded by new_id (keeps files in place). | [src](../../../core/services/jarvis_brain.py#L855) |
| function | `rebuild_index_from_files` | `()` | Scan brain_dir() for .md files; new/changed hash → update index. | [src](../../../core/services/jarvis_brain.py#L881) |
| function | `_extract_text_for_entry` | `(entry_id)` | Read entry content from disk for entity/semantic analysis. | [src](../../../core/services/jarvis_brain.py#L977) |
| function | `_temporal_similarity_score` | `(hours_apart)` | Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h. | [src](../../../core/services/jarvis_brain.py#L983) |
| function | `_cosine_similarity` | `(a_vec, b_vec)` | — | [src](../../../core/services/jarvis_brain.py#L993) |
| function | `_compute_temporal_confidence` | `(*, temporal, semantic, entity, is_chain, chain_score=…)` | Combine four signals into a single confidence score (0.0–1.0). | [src](../../../core/services/jarvis_brain.py#L1000) |
| function | `_compute_chain_score` | `(*, new_entry, cand_entry, hours_apart, cand_related)` | Compute chain signal score (0.0–1.0) between two entries. | [src](../../../core/services/jarvis_brain.py#L1019) |
| function | `infer_temporal_edges` | `(new_entry_id, now=…)` | Run four-signal inference between a new entry and all existing active entries. | [src](../../../core/services/jarvis_brain.py#L1069) |
| function | `_store_temporal_edge` | `(from_id, to_id, confidence, reasoning, now)` | Insert or update a temporal edge with combined confidence. | [src](../../../core/services/jarvis_brain.py#L1199) |
| function | `get_temporal_neighbors` | `(entry_id, min_confidence=…, limit=…)` | Get tidligere inferred temporal neighbors for an entry. | [src](../../../core/services/jarvis_brain.py#L1225) |
| function | `temporal_boost_recall` | `(entry_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost scores for a set of entry IDs. | [src](../../../core/services/jarvis_brain.py#L1255) |
| function | `prune_stale_edges` | `(*, max_age_days=…, min_confidence=…)` | Remove stale temporal edges with low confidence. | [src](../../../core/services/jarvis_brain.py#L1311) |
| function | `prune_unreadable_edges` | `()` | Fjern kanter der beviseligt ALDRIG læses — uanset alder. | [src](../../../core/services/jarvis_brain.py#L1338) |
| function | `prune_dense_edges` | `(*, max_per_node=…)` | Loft pr. node: behold kun de ``max_per_node`` stærkeste kanter pr. endepunkt. | [src](../../../core/services/jarvis_brain.py#L1360) |
| function | `full_rebuild` | `(*, batch_size=…)` | Genberegn alle temporale edges fra bunden. | [src](../../../core/services/jarvis_brain.py#L1393) |
| function | `_emit_jarvis_brain_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/jarvis_brain.py#L1455) |

