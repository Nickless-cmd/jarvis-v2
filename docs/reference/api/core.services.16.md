# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/periodic_jobs_scheduler.py`
_Periodic jobs scheduler — enqueues overdue background jobs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_last_time` | `(item)` | Pick the most relevant timestamp from a job record. | [src](../../../core/services/periodic_jobs_scheduler.py#L51) |
| function | `check_and_enqueue_due_periodic_jobs` | `()` | Idempotent — enqueue any periodic jobs whose cadence is exceeded. | [src](../../../core/services/periodic_jobs_scheduler.py#L64) |

## `core/services/permission_classifier.py`
_LLM permission-classifier (harness Part E, shadow-first + earned trust)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PermissionPrediction` | `` | — | [src](../../../core/services/permission_classifier.py#L41) |
| function | `is_mutating` | `(tool)` | — | [src](../../../core/services/permission_classifier.py#L47) |
| function | `permission_classifier_mode` | `()` | 'off' | 'shadow' | 'active'. Default 'shadow'. Env wins. Self-safe. | [src](../../../core/services/permission_classifier.py#L51) |
| function | `_args_signature` | `(tool, arguments)` | — | [src](../../../core/services/permission_classifier.py#L66) |
| function | `_clip_args` | `(arguments, limit=…)` | — | [src](../../../core/services/permission_classifier.py#L75) |
| function | `_parse_prediction` | `(raw)` | — | [src](../../../core/services/permission_classifier.py#L83) |
| function | `classify_action` | `(tool, arguments, ctx=…)` | Predict whether the owner would approve this mutating action. Cheap-lane LLM, | [src](../../../core/services/permission_classifier.py#L99) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/permission_classifier.py#L125) |
| function | `record_prediction_outcome` | `(tool, *, predicted, actual, is_owner_gold)` | Record one prediction vs actual. Bootstrap (is_owner_gold=False, dense) or gold (True). | [src](../../../core/services/permission_classifier.py#L140) |
| function | `classifier_trust` | `(tool)` | 'trusted' | 'untrusted' for a tool. Fail-open 'untrusted'. | [src](../../../core/services/permission_classifier.py#L176) |
| function | `should_auto_allow` | `(tool, prediction, *, gates_green, role)` | Pure predicate for the DEFERRED active mode — NOT wired into the approval path this round. | [src](../../../core/services/permission_classifier.py#L187) |
| function | `stash_prediction` | `(action_id, tool, predicted)` | Stash a prediction by approval/action id for gold lookup at resolution. Bounded TTL. Self-safe. | [src](../../../core/services/permission_classifier.py#L202) |
| function | `pop_prediction` | `(action_id)` | Pop a stashed prediction (once). None if absent/expired. Self-safe. | [src](../../../core/services/permission_classifier.py#L216) |
| function | `build_permission_classifier_surface` | `()` | Owner view: per-tool prediction counts, accuracy, gold, trust, mode. Self-safe. | [src](../../../core/services/permission_classifier.py#L228) |

## `core/services/permission_engine.py`
_Permission engine — rollebaseret tool-adgang pr. mode (fail-closed)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_AllTools` | `` | Sentinel for owner — indeholder enhver tool. | [src](../../../core/services/permission_engine.py#L27) |
| method | `_AllTools.__contains__` | `(self, item)` | — | [src](../../../core/services/permission_engine.py#L30) |
| method | `_AllTools.__repr__` | `(self)` | — | [src](../../../core/services/permission_engine.py#L33) |
| function | `allowed_tools` | `(*, role, mode)` | Returnér de tools en (rolle, mode) må bruge. | [src](../../../core/services/permission_engine.py#L111) |
| function | `is_tool_allowed` | `(tool, *, role, mode)` | True hvis `tool` må kaldes af (rolle, mode). | [src](../../../core/services/permission_engine.py#L127) |
| function | `requires_workspace_jail` | `(tool, *, role, mode)` | True hvis tool-kaldet skal path-jailes til brugerens eget workspace. | [src](../../../core/services/permission_engine.py#L132) |
| function | `_all_member_tool_names` | `()` | Alle navne på tværs af member-lister — til drift-test mod registry. | [src](../../../core/services/permission_engine.py#L143) |

## `core/services/personal_project.py`
_Personal Project — noget der er hans._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/personal_project.py#L56) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/personal_project.py#L60) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/personal_project.py#L106) |
| function | `detect_nomination_candidates` | `(*, lookback_days=…)` | Find themes that have circulated enough to become a nomination. | [src](../../../core/services/personal_project.py#L113) |
| function | `propose_nomination` | `()` | Ask: "This theme has circulated N times — is it your project?" | [src](../../../core/services/personal_project.py#L192) |
| function | `declare_project` | `(*, name, why_mine=…, description=…, from_proposal_id=…)` | Jarvis declares (or user offers him to accept) a new active project. | [src](../../../core/services/personal_project.py#L276) |
| function | `pause_project` | `(*, project_id, reason=…)` | — | [src](../../../core/services/personal_project.py#L356) |
| function | `resume_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L380) |
| function | `complete_project` | `(*, project_id, outcome_note=…)` | — | [src](../../../core/services/personal_project.py#L405) |
| function | `add_journal_entry` | `(*, project_id, entry_text, source=…, mood_tone=…)` | Add a journal entry. No approval required — it's his space. | [src](../../../core/services/personal_project.py#L438) |
| function | `list_journal_entries` | `(*, project_id, limit=…)` | — | [src](../../../core/services/personal_project.py#L489) |
| function | `advance_active_project` | `()` | Autonomous advancement — call from idle heartbeat. Writes a new | [src](../../../core/services/personal_project.py#L504) |
| function | `get_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L574) |
| function | `get_active_project` | `()` | — | [src](../../../core/services/personal_project.py#L583) |
| function | `get_latest_proposal` | `()` | — | [src](../../../core/services/personal_project.py#L593) |
| function | `list_projects` | `(*, status=…, limit=…)` | — | [src](../../../core/services/personal_project.py#L603) |
| function | `get_project_prompt_hint` | `()` | Quiet one-liner for prompt injection: what his current sag is. | [src](../../../core/services/personal_project.py#L622) |
| function | `build_personal_project_surface` | `()` | — | [src](../../../core/services/personal_project.py#L633) |

## `core/services/personality_drift.py`
_Personality drift detection — has Jarvis' baseline shifted?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_snapshots` | `()` | — | [src](../../../core/services/personality_drift.py#L32) |
| function | `_save_snapshots` | `(snapshots)` | — | [src](../../../core/services/personality_drift.py#L39) |
| function | `take_snapshot` | `()` | Capture current mood — call from heartbeat or daemon periodically. | [src](../../../core/services/personality_drift.py#L45) |
| function | `compute_baseline` | `(*, lookback_days=…)` | Mean + stddev for each mood dimension over the lookback window. | [src](../../../core/services/personality_drift.py#L67) |
| function | `detect_drift` | `(*, lookback_days=…, recent_window=…)` | Compare recent snapshot mean vs long-term baseline. | [src](../../../core/services/personality_drift.py#L93) |
| function | `personality_drift_section` | `()` | Awareness section when drift detected — surfaces in prompt. | [src](../../../core/services/personality_drift.py#L143) |
| function | `_exec_personality_drift_check` | `(args)` | — | [src](../../../core/services/personality_drift.py#L159) |
| function | `_exec_personality_drift_snapshot` | `(args)` | — | [src](../../../core/services/personality_drift.py#L167) |

## `core/services/personality_vector.py`
_Personality Vector — cumulative personality that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_apply_decay` | `()` | Return True if enough time has passed since the last decay application. | [src](../../../core/services/personality_vector.py#L34) |
| function | `_get_evolved_baseline` | `()` | Compute long-term baseline targets from accumulated snapshots. | [src](../../../core/services/personality_vector.py#L43) |
| function | `_record_decay_timestamp` | `()` | Record that decay was just applied. | [src](../../../core/services/personality_vector.py#L73) |
| function | `_build_update_prompt` | `()` | — | [src](../../../core/services/personality_vector.py#L81) |
| function | `update_personality_vector_from_run` | `(*, run_id, user_message, assistant_response, outcome_status)` | Update the personality vector based on a visible run. | [src](../../../core/services/personality_vector.py#L105) |
| function | `update_personality_vector_async` | `(*, run_id, user_message, assistant_response, outcome_status)` | Fire-and-forget async wrapper. | [src](../../../core/services/personality_vector.py#L189) |
| function | `tick_personality_drift` | `(*, outcome_signal=…)` | Heartbeat-triggered passive drift af personality_vector. | [src](../../../core/services/personality_vector.py#L210) |
| function | `_safe_update` | `(**kwargs)` | — | [src](../../../core/services/personality_vector.py#L242) |
| function | `build_personality_vector_surface` | `()` | MC surface for personality vector. | [src](../../../core/services/personality_vector.py#L249) |
| function | `_deterministic_update` | `(outcome_status, current)` | Fallback: small deterministic adjustments without LLM. | [src](../../../core/services/personality_vector.py#L270) |
| function | `_merge_vector` | `(current, updates)` | Deep merge updates into current vector. | [src](../../../core/services/personality_vector.py#L399) |
| function | `_baseline_changed` | `(old, new_baseline)` | Fix 5 helper: return True if emotional_baseline values differ by > 0.001. | [src](../../../core/services/personality_vector.py#L442) |
| function | `_safe_json_field` | `(value, default)` | — | [src](../../../core/services/personality_vector.py#L456) |
| function | `_resolve_local_llm_target` | `()` | — | [src](../../../core/services/personality_vector.py#L469) |
| function | `_call_llm` | `(target, system_prompt, user_prompt)` | Minimal LLM call via provider router target. | [src](../../../core/services/personality_vector.py#L480) |
| function | `_parse_json_response` | `(text)` | — | [src](../../../core/services/personality_vector.py#L504) |

## `core/services/pfsense_syslog.py`
_core/services/pfsense_syslog.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_self_ips` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L46) |
| function | `_parse_filterlog` | `(line)` | Tolerant parser af pfSense filterlog-CSV. Returnerer {action, src, dst, dport}. | [src](../../../core/services/pfsense_syslog.py#L74) |
| function | `_is_internal_src` | `(src)` | Er kilde-IP'en PRIVAT (RFC1918 = husets egne maskiner)? Ægte port-scan/brute-force kommer | [src](../../../core/services/pfsense_syslog.py#L103) |
| function | `_is_noise_dst` | `(dst)` | Multicast/broadcast er normal netværks-støj (mDNS/SSDP/LLMNR/DHCP), IKKE angreb. | [src](../../../core/services/pfsense_syslog.py#L133) |
| function | `_ingest` | `(rec, now)` | — | [src](../../../core/services/pfsense_syslog.py#L147) |
| function | `_listen` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L183) |
| function | `start_syslog_listener` | `()` | Start UDP-lytteren i en daemon-tråd (idempotent). Kun i runtime-processen. | [src](../../../core/services/pfsense_syslog.py#L204) |
| function | `drain_detections` | `()` | Hent + ryd nye detektioner (kaldes af infra_sense-cadence). Self-safe. | [src](../../../core/services/pfsense_syslog.py#L213) |
| function | `syslog_stats` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L221) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L226) |

## `core/services/plan_proposals.py`
_Plan mode — propose, wait for approval, then execute._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plan_proposals.py#L38) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/plan_proposals.py#L45) |
| function | `propose_plan` | `(*, session_id, title, why, steps, skill_data=…)` | — | [src](../../../core/services/plan_proposals.py#L49) |
| function | `resolve_plan` | `(plan_id, *, decision)` | — | [src](../../../core/services/plan_proposals.py#L133) |
| function | `_plan_todo_auto_create_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L263) |
| function | `revise_plan` | `(*, plan_id, session_id, reason, new_steps)` | Propose a revision of an existing approved plan. | [src](../../../core/services/plan_proposals.py#L270) |
| function | `_plan_revision_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L371) |
| function | `mark_step_completed` | `(plan_id, step_index)` | Append step_index to plan's completed_step_indices (idempotent, sorted). | [src](../../../core/services/plan_proposals.py#L378) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/plan_proposals.py#L423) |
| function | `replan_signal_for_plan` | `(rec, *, now=…, stale_days=…)` | Return a non-mutating backtracking signal for an approved stale plan. | [src](../../../core/services/plan_proposals.py#L436) |
| function | `list_session_plans` | `(session_id)` | — | [src](../../../core/services/plan_proposals.py#L479) |
| function | `pending_plan_section` | `(session_id)` | Surface plans relevant to the current session. | [src](../../../core/services/plan_proposals.py#L484) |
| function | `format_cross_session_plans_for_awareness` | `(current_session_id, *, max_plans=…, max_age_days=…)` | Return awareness-block text for approved+incomplete plans owned by | [src](../../../core/services/plan_proposals.py#L557) |
| function | `all_pending_plans_section` | `()` | Show ALL pending plans (incl. auto-improvement proposals from | [src](../../../core/services/plan_proposals.py#L617) |
| function | `_exec_propose_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L644) |
| function | `_exec_approve_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L653) |
| function | `_exec_dismiss_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L657) |
| function | `_exec_list_plans` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L661) |

## `core/services/plugin_ruleset.py`
_Plugin-regelsæt — brugerdefinerede kanal-regler der IKKE kan tilsidesættes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_quiet_now` | `(hour, quiet)` | True hvis `hour` er inden for stilletids-vinduet (wrap-around understøttet). | [src](../../../core/services/plugin_ruleset.py#L28) |
| function | `is_allowed` | `(msg_ctx, ruleset, *, override_active=…)` | Afgør om Jarvis må svare på en indkommende kanal-besked. | [src](../../../core/services/plugin_ruleset.py#L42) |

## `core/services/plugin_ruleset_store.py`
_Persistens for plugin-regelsæt (spec §5.3/§5.4, Fase 6 #2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plugin_ruleset_store.py#L23) |
| function | `get_ruleset` | `(plugin_id)` | Regelsæt for et kanal-plugin ({} hvis intet sat). | [src](../../../core/services/plugin_ruleset_store.py#L28) |
| function | `set_ruleset` | `(plugin_id, ruleset)` | Gem/erstat regelsættet for et plugin. Returnér det gemte (rensede) regelsæt. | [src](../../../core/services/plugin_ruleset_store.py#L37) |
| function | `list_rulesets` | `()` | Alle regelsæt {plugin_id → ruleset} (til Settings-UI). | [src](../../../core/services/plugin_ruleset_store.py#L52) |

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
| function | `build_heartbeat_prompt_assembly` | `(*, heartbeat_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3176) |
| function | `build_future_agent_task_prompt_assembly` | `(*, task_brief, agent_context=…, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3328) |
| function | `_relevance_cache_key` | `(text, mode, compact, name)` | Build a string cache key for shared_cache (cross-worker visibility). | [src](../../../core/services/prompt_contract.py#L3458) |
| function | `build_prompt_relevance_decision` | `(text, *, mode, compact, name=…)` | — | [src](../../../core/services/prompt_contract.py#L3465) |
| function | `_bounded_nl_relevance_backend` | `(*, text, mode, compact, name)` | — | [src](../../../core/services/prompt_contract.py#L3585) |
| function | `_track_inner_visible_prompt_bridge` | `(decision)` | — | [src](../../../core/services/prompt_contract.py#L3600) |
| function | `_build_inner_visible_prompt_bridge_decision` | `(*, user_message, mode, compact, relevance)` | — | [src](../../../core/services/prompt_contract.py#L3630) |
| function | `_latest_active_inner_visible_support_signal` | `()` | — | [src](../../../core/services/prompt_contract.py#L3709) |
| function | `_inner_visible_support_bridge_is_redundant` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3717) |
| function | `_inner_visible_support_prompt_line` | `(signal)` | — | [src](../../../core/services/prompt_contract.py#L3727) |
| function | `_self_mutation_lineage_section` | `()` | Returns a compact section about recent self-changes, or None if none. | [src](../../../core/services/prompt_contract.py#L3788) |
| function | `_channel_workspace_path` | `()` | — | [src](../../../core/services/prompt_contract.py#L3820) |
| function | `_channel_context_section` | `(session_id)` | Returns current channel context for the prompt, or None. | [src](../../../core/services/prompt_contract.py#L3824) |
| function | `_visible_chat_rules_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L3904) |
| function | `_self_correction_nudges_section` | `(*, compact)` | Consolidated into VISIBLE_CHAT_RULES.md (2026-07-22, prompt audit #1). | [src](../../../core/services/prompt_contract.py#L3921) |
| function | `_output_discipline_instruction` | `(*, strength)` | Tiered output discipline (harness Part 1). BOTH tiers get 'synthesize & stop' (safe for weak — | [src](../../../core/services/prompt_contract.py#L3932) |
| function | `_central_notices_section` | `()` | Medium-niveau Central-notices til Jarvis (spec 2026-06-23 §2). IKKE severe (dem | [src](../../../core/services/prompt_contract.py#L3952) |
| function | `_pending_promises_section` | `(session_id)` | Bjørn-gate (16. jun 2026): rejs Jarvis' åbne fremtids-løfter prominent, så | [src](../../../core/services/prompt_contract.py#L3983) |
| function | `_connected_connectors_section` | `()` | Surface brugerens FORBUNDNE plugins/connectors så Jarvis ved han har adgang. | [src](../../../core/services/prompt_contract.py#L4012) |
| function | `_open_questions_section` | `(*, limit=…)` | Surface curiosity_daemon._open_questions into the visible prompt. | [src](../../../core/services/prompt_contract.py#L4057) |
| function | `_time_pin_section` | `()` | Prominent, unmissable time indicator — placed high in every system prompt. | [src](../../../core/services/prompt_contract.py#L4086) |
| function | `_quick_facts_section` | `(*, workspace_dir, max_chars=…)` | Always-on facts block. Unlike MEMORY.md, this is NOT relevance-filtered — | [src](../../../core/services/prompt_contract.py#L4124) |
| function | `_visible_capability_truth_instruction` | `(*, compact)` | — | [src](../../../core/services/prompt_contract.py#L4147) |
| function | `_visible_capability_id_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L4169) |
| function | `_local_model_behavior_instruction` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_contract.py#L4177) |
| function | `_visible_finitude_context_section` | `()` | — | [src](../../../core/services/prompt_contract.py#L4229) |
| function | `_visible_support_signal_sections` | `(*, compact, include, user_message=…, session_id=…)` | — | [src](../../../core/services/prompt_contract.py#L4239) |
| function | `_proactive_outbound_section` | `()` | Recent proactive messages Jarvis sent (substrate for user-reply context). | [src](../../../core/services/prompt_contract.py#L4280) |
| function | `_agreement_streak_section` | `()` | Surface last 3+ agreement-opener assistant replies as substrate. | [src](../../../core/services/prompt_contract.py#L4296) |
| function | `_emotion_concept_tone_section` | `()` | Affect-relevant runtime substrate (replaces tone-hint injection). | [src](../../../core/services/prompt_contract.py#L4310) |
| function | `_emotion_signal_section` | `()` | Aktive emotion concepts som data — giver Jarvis sit eget følelsespanel. | [src](../../../core/services/prompt_contract.py#L4358) |
| function | `_experience_substrate_section` | `(*, user_message=…, session_id=…)` | Nylige lignende situationer (embedding-retrieval substrat). | [src](../../../core/services/prompt_contract.py#L4460) |
| function | `_delegated_continuity_summary` | `(context)` | — | [src](../../../core/services/prompt_contract.py#L4571) |
| function | `_should_include_memory` | `(text, *, mode)` | — | [src](../../../core/services/prompt_contract.py#L4599) |
| function | `_should_include_guidance` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4633) |
| function | `_should_include_transcript` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4651) |
| function | `_should_include_continuity` | `(text)` | — | [src](../../../core/services/prompt_contract.py#L4670) |
| function | `prompt_mode_loader_summary` | `()` | — | [src](../../../core/services/prompt_contract.py#L4683) |

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
| function | `load_overrides` | `()` | Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build). | [src](../../../core/services/prompt_observer.py#L127) |
| function | `section_enabled` | `(label, *, blacklisted, overrides)` | Skal denne prompt-sektion med? | [src](../../../core/services/prompt_observer.py#L155) |
| function | `observe_discarded_content` | `(label, content)` | En slukket sektions indhold blev netop kasseret — prøvetag det. | [src](../../../core/services/prompt_observer.py#L165) |
| function | `observe_build` | `(*, lane, included, dropped_disabled, dropped_budget, dropped_error=…)` | Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget | [src](../../../core/services/prompt_observer.py#L181) |
| function | `observe_section_error` | `(label, error, *, lane=…)` | En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar). | [src](../../../core/services/prompt_observer.py#L207) |
| function | `set_section` | `(label, enabled)` | Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar. | [src](../../../core/services/prompt_observer.py#L221) |
| function | `list_overrides` | `()` | Read-only projektion af aktive overrides (til MC/debug). | [src](../../../core/services/prompt_observer.py#L229) |

