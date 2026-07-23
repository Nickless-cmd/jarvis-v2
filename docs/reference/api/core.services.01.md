# `core.services.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/__init__.py`

_(no top-level classes or functions)_

## `core/services/absence_awareness.py`
_Bounded absence awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_idle_band` | `(idle_hours)` | — | [src](../../../core/services/absence_awareness.py#L26) |
| function | `_trim` | `(value, *, limit=…)` | — | [src](../../../core/services/absence_awareness.py#L38) |
| function | `build_return_context` | `(*, idle_hours=…)` | Collect bounded structural context for resuming after absence. | [src](../../../core/services/absence_awareness.py#L45) |
| function | `build_return_brief` | `(*, idle_hours=…)` | Build a return brief if user has been absent long enough. | [src](../../../core/services/absence_awareness.py#L94) |
| function | `build_absence_awareness_surface` | `()` | MC surface for absence awareness. | [src](../../../core/services/absence_awareness.py#L130) |
| function | `_publish_absence_awareness_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/absence_awareness.py#L166) |

## `core/services/absence_daemon.py`
_Absence daemon — tracks the *quality* of Jarvis' silence between interactions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/absence_daemon.py#L41) |
| function | `mark_interaction` | `()` | Call whenever Jarvis interacts with the user. Resets absence clock. | [src](../../../core/services/absence_daemon.py#L60) |
| function | `seed_last_interaction_from_db` | `()` | One-time seed: set _last_interaction_at from most recent visible run if not yet set. | [src](../../../core/services/absence_daemon.py#L68) |
| function | `tick_absence_daemon` | `(now=…, *, skip_event_gate=…)` | Evaluate current absence quality. Returns {generated, label, duration_hours}. | [src](../../../core/services/absence_daemon.py#L84) |
| function | `get_latest_absence` | `()` | — | [src](../../../core/services/absence_daemon.py#L151) |
| function | `build_absence_surface` | `()` | — | [src](../../../core/services/absence_daemon.py#L155) |
| function | `_classify_absence` | `(elapsed)` | — | [src](../../../core/services/absence_daemon.py#L174) |
| function | `_absence_band` | `(elapsed)` | — | [src](../../../core/services/absence_daemon.py#L183) |
| function | `_build_raw_absence` | `(elapsed)` | Byg fraværs-strengen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/absence_daemon.py#L191) |
| function | `_generate_absence_label` | `(elapsed)` | — | [src](../../../core/services/absence_daemon.py#L202) |
| function | `_store_absence` | `(label, duration_hours, now)` | — | [src](../../../core/services/absence_daemon.py#L225) |

## `core/services/abuse_monitor.py`
_Abuse-monitoring (spec 2026-06-21 §5): prompt-injection, manipulation,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scan_for_injection` | `(text)` | Returnér navne på matchede injection-mønstre (tom = rent). | [src](../../../core/services/abuse_monitor.py#L41) |
| function | `_rl_key` | `(user_id)` | — | [src](../../../core/services/abuse_monitor.py#L57) |
| function | `check_rate_limit` | `(user_id, *, now=…)` | True hvis brugeren ER inden for grænsen (må fortsætte). False = overskredet. | [src](../../../core/services/abuse_monitor.py#L61) |
| function | `_throttle_count` | `(user_id)` | — | [src](../../../core/services/abuse_monitor.py#L81) |
| function | `_notify_owner` | `(summary)` | — | [src](../../../core/services/abuse_monitor.py#L90) |
| function | `process_incoming` | `(message, *, session_id, user_id)` | Rate-limit + injection-scan på en indgående besked. | [src](../../../core/services/abuse_monitor.py#L104) |
| function | `scan_tool_output` | `(text, *, source=…)` | Scan eksternt tool-output (web_fetch/web_search) for indlejret injection. | [src](../../../core/services/abuse_monitor.py#L144) |

## `core/services/action_router.py`
_Action Router — close the loop: signal → handling._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_max_proactive_per_day` | `()` | Settings-backed cap (config uden deploy, 2026-06-22); konstant = fallback. | [src](../../../core/services/action_router.py#L46) |
| function | `_proactive_cooldown_hours` | `()` | Settings-backed cooldown (config uden deploy); konstant = fallback. | [src](../../../core/services/action_router.py#L55) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/action_router.py#L67) |
| function | `_load` | `()` | — | [src](../../../core/services/action_router.py#L71) |
| function | `_save` | `(data)` | — | [src](../../../core/services/action_router.py#L87) |
| function | `classify` | `(event_kind, payload)` | Return signal class: 'warning' | 'mood' | 'creative' | 'info' | 'unknown'. | [src](../../../core/services/action_router.py#L140) |
| function | `_maybe_suggest_listen_on_ambient_talk` | `(payload)` | When ambient_sound_daemon reports 'talk', emit a SUGGESTION event that | [src](../../../core/services/action_router.py#L156) |
| function | `_adjust_mood` | `(delta, reason)` | — | [src](../../../core/services/action_router.py#L199) |
| function | `_file_initiative` | `(*, title, rationale, priority=…)` | — | [src](../../../core/services/action_router.py#L209) |
| function | `_proactive_messages_today` | `()` | — | [src](../../../core/services/action_router.py#L231) |
| function | `_last_proactive_ts` | `()` | — | [src](../../../core/services/action_router.py#L240) |
| function | `_within_cooldown` | `()` | — | [src](../../../core/services/action_router.py#L251) |
| function | `_send_ntfy` | `(message, *, title=…, priority=…)` | — | [src](../../../core/services/action_router.py#L258) |
| function | `_reach_out` | `(*, message, channel=…, importance=…, source=…, bypass_nudge=…)` | Send a proactive message. Routes through nudge-broend for Jarvis gatekeeping. | [src](../../../core/services/action_router.py#L268) |
| function | `_append_proactive` | `(entry)` | — | [src](../../../core/services/action_router.py#L367) |
| function | `_route_warning` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L377) |
| function | `_route_mood` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L411) |
| function | `_route_creative` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L419) |
| function | `route` | `(event_kind, payload=…)` | Evaluate + execute. Returns decision record. | [src](../../../core/services/action_router.py#L439) |
| function | `_drain_eventbus` | `(limit=…)` | Pull events from eventbus without blocking; route routable ones. | [src](../../../core/services/action_router.py#L492) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — drain eventbus + route + run generative autonomy chain. | [src](../../../core/services/action_router.py#L525) |
| function | `recent_actions` | `(*, limit=…)` | — | [src](../../../core/services/action_router.py#L609) |
| function | `recent_proactive` | `(*, limit=…)` | — | [src](../../../core/services/action_router.py#L613) |
| function | `build_action_router_surface` | `()` | — | [src](../../../core/services/action_router.py#L617) |
| function | `_surface_summary` | `(actions, proactive_today, proactive_sent_today)` | — | [src](../../../core/services/action_router.py#L645) |
| function | `build_action_router_prompt_section` | `()` | Tell him quietly what the router has done recently. | [src](../../../core/services/action_router.py#L658) |

## `core/services/active_file_store.py`
_Live "aktiv fil" — den sti Jarvis senest læste/skrev (file-tree-control-spec)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/active_file_store.py#L15) |
| function | `set_active_file` | `(user_id, path, op, *, ts=…)` | Registrér at brugeren (Jarvis i deres kontekst) rører `path` (op=read/write). | [src](../../../core/services/active_file_store.py#L20) |
| function | `get_active_file` | `(user_id)` | Seneste aktiv-fil for brugeren, eller None. | [src](../../../core/services/active_file_store.py#L37) |
| function | `clear_active_file` | `(user_id)` | — | [src](../../../core/services/active_file_store.py#L43) |

## `core/services/active_model_state.py`
_Aktiv per-run visible-model (provider+model) pr. bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm_uid` | `(user_id)` | — | [src](../../../core/services/active_model_state.py#L21) |
| function | `set_active_visible_target` | `(user_id, provider, model)` | Husk den aktive (provider, model) for en bruger ved run-start. | [src](../../../core/services/active_model_state.py#L25) |
| function | `get_active_visible_target` | `(user_id)` | Den seneste aktive (provider, model) for en bruger, eller None. | [src](../../../core/services/active_model_state.py#L38) |

## `core/services/active_sensing_daemon.py`
_Aktiv Sansning — Sansernes Arkiv får autonom sansetrang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_active_sensing_daemon` | `()` | Aktiv sansetrang: vurder om Jarvis har lyst til at sanse nu. | [src](../../../core/services/active_sensing_daemon.py#L43) |
| function | `_compute_desire` | `(state, now)` | Beregn sansetrang (0.0-1.0) baseret på tid og kontekst. | [src](../../../core/services/active_sensing_daemon.py#L111) |
| function | `_choose_modality` | `(state, now)` | Vælg hvilken sansemodalitet der tilfredsstilles nu. | [src](../../../core/services/active_sensing_daemon.py#L156) |
| function | `_perform_sensing` | `(modality, state, now)` | Udfør sansningen og skriv til Sansernes Arkiv. | [src](../../../core/services/active_sensing_daemon.py#L199) |
| function | `_sense_visual` | `(state, now)` | Se rummet på eget initiativ. | [src](../../../core/services/active_sensing_daemon.py#L219) |
| function | `_sense_audio` | `(state, now)` | Lyt i rummet på eget initiativ. | [src](../../../core/services/active_sensing_daemon.py#L243) |
| function | `_sense_atmosphere` | `(state, now)` | Registrer rummets stemning — kombinerer tilgængelige data. | [src](../../../core/services/active_sensing_daemon.py#L258) |
| function | `_sense_mixed` | `(state, now)` | Blandet sansning — både se og lyt i samme tur. | [src](../../../core/services/active_sensing_daemon.py#L296) |
| function | `build_active_sensing_surface` | `()` | Observability surface til Mission Control. | [src](../../../core/services/active_sensing_daemon.py#L325) |
| function | `_enabled` | `()` | — | [src](../../../core/services/active_sensing_daemon.py#L340) |
| function | `_load_state` | `()` | — | [src](../../../core/services/active_sensing_daemon.py#L348) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/active_sensing_daemon.py#L353) |

## `core/services/adaptive_learning_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_adaptive_learning_runtime_surface` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L10) |
| function | `_build_adaptive_learning_runtime_surface_uncached` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L18) |
| function | `build_adaptive_learning_runtime_from_sources` | `(*, guided_learning, adaptive_planner, adaptive_reasoning, epistemic_runtime_state, prompt_evolution, dream_articulation, idle_consolidation, loop_runtime)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L31) |
| function | `build_adaptive_learning_prompt_section` | `(surface=…)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L140) |
| function | `_derive_reinforcement_target` | `(*, guided_learning, prompt_summary, dream_summary, consolidation_summary, loop_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L167) |
| function | `_derive_learning_engine_mode` | `(*, guided_learning, planner, reasoning, epistemic, prompt_summary, dream_summary, consolidation_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L193) |
| function | `_derive_retention_bias` | `(*, learning_engine_mode, guided_learning, prompt_summary, loop_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L224) |
| function | `_derive_attenuation_bias` | `(*, learning_engine_mode, epistemic, guided_learning, consolidation_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L242) |
| function | `_derive_maturation_state` | `(*, learning_engine_mode, dream_summary, prompt_summary, consolidation_summary, loop_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L262) |
| function | `_derive_confidence` | `(*, learning_engine_mode, guided_learning, epistemic, maturation_state)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L281) |
| function | `_source_contributors` | `(*, guided_learning, adaptive_planner, adaptive_reasoning, epistemic, prompt_summary, dream_summary, consolidation_summary, loop_summary)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L297) |
| function | `_guidance_for_adaptive_learning` | `(state)` | — | [src](../../../core/services/adaptive_learning_runtime.py#L380) |
| function | `_safe_guided_learning` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L401) |
| function | `_safe_learning_policy_surface` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L409) |
| function | `_safe_adaptive_planner` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L417) |
| function | `_safe_adaptive_reasoning` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L425) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L433) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L441) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L449) |
| function | `_safe_idle_consolidation` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L457) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/adaptive_learning_runtime.py#L465) |

## `core/services/adaptive_planner_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_adaptive_planner_runtime_surface` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L10) |
| function | `_build_adaptive_planner_runtime_surface_uncached` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L18) |
| function | `build_adaptive_planner_runtime_from_sources` | `(*, embodied_state, affective_meta_state, epistemic_runtime_state, loop_runtime, council_runtime, conflict_trace, quiet_initiative)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L30) |
| function | `build_adaptive_planner_prompt_section` | `(surface=…)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L139) |
| function | `_derive_planner_mode` | `(*, embodied_state, strain_level, affective_state, wrongness_state, loop_summary, council_recommendation, conflict_outcome, quiet_initiative)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L166) |
| function | `_derive_plan_horizon` | `(*, planner_mode, loop_summary, council_divergence)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L195) |
| function | `_derive_planning_posture` | `(*, planner_mode, affective_bearing, quiet_initiative)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L210) |
| function | `_derive_risk_posture` | `(*, planner_mode, wrongness_state, council_divergence)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L227) |
| function | `_derive_next_planning_bias` | `(*, planner_mode, council_recommendation, wrongness_state, quiet_initiative)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L240) |
| function | `_derive_confidence` | `(*, planner_mode, wrongness_state, council_divergence, loop_summary)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L258) |
| function | `_source_contributors` | `(*, embodied_state, strain_level, affective_state, affective_bearing, epistemic_runtime_state, loop_summary, council_runtime, conflict_trace, quiet_initiative)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L276) |
| function | `_guidance_for_planner` | `(state)` | — | [src](../../../core/services/adaptive_planner_runtime.py#L344) |
| function | `_safe_embodied_state` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L359) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L367) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L375) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L383) |
| function | `_safe_council_runtime` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L391) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L399) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/adaptive_planner_runtime.py#L407) |

## `core/services/adaptive_reasoning_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_adaptive_reasoning_runtime_surface` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L10) |
| function | `_build_adaptive_reasoning_runtime_surface_uncached` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L18) |
| function | `build_adaptive_reasoning_runtime_from_sources` | `(*, embodied_state, affective_meta_state, epistemic_runtime_state, loop_runtime, council_runtime, adaptive_planner, conflict_trace, quiet_initiative)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L31) |
| function | `build_adaptive_reasoning_prompt_section` | `(surface=…)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L149) |
| function | `_derive_reasoning_mode` | `(*, embodied_state, strain_level, affective_state, wrongness_state, council_recommendation, planner_mode, conflict_outcome, quiet_initiative)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L176) |
| function | `_derive_reasoning_posture` | `(*, reasoning_mode, affective_bearing, council_divergence)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L204) |
| function | `_derive_certainty_style` | `(*, reasoning_mode, wrongness_state, regret_signal, council_divergence)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L221) |
| function | `_derive_exploration_bias` | `(*, reasoning_mode, counterfactual_mode, planner_mode, quiet_initiative)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L235) |
| function | `_derive_constraint_bias` | `(*, reasoning_mode, council_recommendation, planner_mode, conflict_outcome)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L251) |
| function | `_derive_confidence` | `(*, reasoning_mode, wrongness_state, council_divergence, loop_summary, planner_mode)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L265) |
| function | `_source_contributors` | `(*, embodied_state, strain_level, affective_state, affective_bearing, wrongness_state, regret_signal, counterfactual_mode, loop_summary, council_runtime, planner, conflict_trace, quiet_initiative)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L282) |
| function | `_guidance_for_reasoning` | `(state)` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L352) |
| function | `_safe_embodied_state` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L367) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L375) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L383) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L391) |
| function | `_safe_council_runtime` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L399) |
| function | `_safe_adaptive_planner` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L407) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L415) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/adaptive_reasoning_runtime.py#L423) |

## `core/services/aesthetic_sense.py`
_Aesthetic Sense — tracks Jarvis' evolving taste motifs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_aesthetic_signals` | `(*, text)` | Detect aesthetic motifs in text. | [src](../../../core/services/aesthetic_sense.py#L54) |
| function | `build_aesthetic_surface` | `()` | — | [src](../../../core/services/aesthetic_sense.py#L83) |
| function | `_ensure_notes_table` | `()` | — | [src](../../../core/services/aesthetic_sense.py#L96) |
| function | `_compute_signature` | `(motif, evidence_refs)` | — | [src](../../../core/services/aesthetic_sense.py#L118) |
| function | `_latest_note_ts` | `()` | — | [src](../../../core/services/aesthetic_sense.py#L124) |
| function | `_known_signatures` | `()` | — | [src](../../../core/services/aesthetic_sense.py#L140) |
| function | `maybe_capture_weekly_aesthetic_note` | `(*, candidates=…)` | Capture at most ONE aesthetic note per week, only if signature is new. | [src](../../../core/services/aesthetic_sense.py#L152) |
| function | `list_aesthetic_notes` | `(*, limit=…)` | — | [src](../../../core/services/aesthetic_sense.py#L234) |
| function | `accumulate_from_daemon` | `(source, text)` | Run motif detection on daemon text output, persist to DB, update in-memory set. | [src](../../../core/services/aesthetic_sense.py#L245) |

## `core/services/aesthetic_taste_daemon.py`
_Aesthetic taste daemon — emergent taste from accumulated motif observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_seed_from_db` | `()` | Load persisted motifs into memory on first tick. | [src](../../../core/services/aesthetic_taste_daemon.py#L30) |
| function | `record_choice` | `(mode, style_signals)` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L44) |
| function | `tick_taste_daemon` | `(*, skip_event_gate=…)` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L56) |
| function | `get_latest_taste_insight` | `()` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L98) |
| function | `build_taste_surface` | `()` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L102) |
| function | `_generate_insight` | `()` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L124) |
| function | `_store_insight` | `(insight)` | — | [src](../../../core/services/aesthetic_taste_daemon.py#L155) |

## `core/services/affect_modulation.py`
_Affect-modulated runtime — emotions adjust behavioral parameters._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compute_affect_modulated_params` | `()` | Compute behavioral parameters adjusted by current emotional state. | [src](../../../core/services/affect_modulation.py#L66) |
| function | `compute_agentic_loop_budget` | `(*, resume_context=…)` | Return affect-aware agentic loop limits. | [src](../../../core/services/affect_modulation.py#L126) |
| function | `affect_modulation_section` | `()` | Render affect-modulated parameters as a prompt section. | [src](../../../core/services/affect_modulation.py#L166) |
| function | `compute_affect_tone_hints` | `()` | Return Danish tone-instruction strings derived from active emotion concepts. | [src](../../../core/services/affect_modulation.py#L224) |
| function | `compute_concept_perception_focus` | `()` | Return a Danish perception-focus suffix derived from active concepts. | [src](../../../core/services/affect_modulation.py#L269) |
| function | `_summarize_affect_payload` | `(kind, payload)` | Pull the most affectively-relevant kerne from a payload. | [src](../../../core/services/affect_modulation.py#L323) |
| function | `compute_affect_substrate` | `(*, window_min=…, max_events=…)` | Return raw affectively-relevant events as substrate strings. | [src](../../../core/services/affect_modulation.py#L373) |

## `core/services/affective_meta_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_affective_meta_state_surface` | `()` | Build affective meta state fresh each call — cheap (no LLM), always current. | [src](../../../core/services/affective_meta_state.py#L15) |
| function | `_build_affective_meta_state_surface_uncached` | `()` | — | [src](../../../core/services/affective_meta_state.py#L20) |
| function | `build_affective_meta_state_from_sources` | `(*, embodied_state, loop_runtime, regulation_homeostasis, metabolism_state, quiet_initiative, idle_consolidation, dream_articulation, inner_voice_state, personality_vector, relationship_texture, rhythm_state, last_run_finished_at=…, cognitive_residue=…)` | — | [src](../../../core/services/affective_meta_state.py#L38) |
| function | `_build_live_emotional_state` | `(*, personality_vector, relationship_texture, rhythm_state)` | — | [src](../../../core/services/affective_meta_state.py#L190) |
| function | `_safe_json_object` | `(value)` | — | [src](../../../core/services/affective_meta_state.py#L255) |
| function | `_safe_json_list` | `(value)` | — | [src](../../../core/services/affective_meta_state.py#L267) |
| function | `_clamp_unit` | `(value)` | — | [src](../../../core/services/affective_meta_state.py#L279) |
| function | `_safe_personality_vector` | `()` | — | [src](../../../core/services/affective_meta_state.py#L287) |
| function | `_safe_relationship_texture` | `()` | — | [src](../../../core/services/affective_meta_state.py#L291) |
| function | `_safe_rhythm_state` | `()` | — | [src](../../../core/services/affective_meta_state.py#L295) |
| function | `build_affective_meta_prompt_section` | `(surface=…)` | — | [src](../../../core/services/affective_meta_state.py#L299) |
| function | `_seconds_since` | `(timestamp_str)` | Return seconds elapsed since an ISO timestamp, or None if unparseable. | [src](../../../core/services/affective_meta_state.py#L346) |
| function | `_affective_state_from_cognitive_residue` | `(residue)` | Map private inner voice + self-model signals to a post-run affective state. | [src](../../../core/services/affective_meta_state.py#L360) |
| function | `_derive_affective_state` | `(*, embodied_state, strain_level, loop_summary, regulation_summary, metabolism_summary, quiet_initiative, idle_consolidation_summary, dream_articulation_summary, inner_voice_state, last_run_finished_at=…, cognitive_residue=…)` | — | [src](../../../core/services/affective_meta_state.py#L380) |
| function | `_derive_bearing` | `(*, affective_state, loop_summary, quiet_initiative)` | — | [src](../../../core/services/affective_meta_state.py#L423) |
| function | `_derive_monitoring_mode` | `(*, affective_state, regulation_summary, metabolism_summary, dream_articulation_summary)` | — | [src](../../../core/services/affective_meta_state.py#L457) |
| function | `_derive_reflective_load` | `(*, idle_consolidation_summary, dream_articulation_summary, inner_voice_state, quiet_initiative)` | — | [src](../../../core/services/affective_meta_state.py#L479) |
| function | `_guidance_for_state` | `(*, affective_state, bearing, monitoring_mode)` | — | [src](../../../core/services/affective_meta_state.py#L502) |
| function | `_safe_embodied_state` | `()` | — | [src](../../../core/services/affective_meta_state.py#L519) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/affective_meta_state.py#L525) |
| function | `_safe_regulation_homeostasis` | `()` | — | [src](../../../core/services/affective_meta_state.py#L531) |
| function | `_safe_metabolism_state` | `()` | — | [src](../../../core/services/affective_meta_state.py#L539) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/affective_meta_state.py#L547) |
| function | `_safe_idle_consolidation` | `()` | — | [src](../../../core/services/affective_meta_state.py#L553) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/affective_meta_state.py#L559) |
| function | `_safe_inner_voice_state` | `()` | — | [src](../../../core/services/affective_meta_state.py#L565) |
| function | `_safe_last_run_finished_at` | `()` | Return finished_at timestamp of the most recent visible run, or None. | [src](../../../core/services/affective_meta_state.py#L571) |
| function | `_safe_cognitive_residue` | `()` | Fetch mood_tone, confidence, and recurring_tension from private cognitive layers. | [src](../../../core/services/affective_meta_state.py#L582) |

## `core/services/affective_state_renderer.py`
_Affective state renderer — collects real signals and renders them as natural language._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_collect_signals` | `()` | Gather real signals from internal systems. | [src](../../../core/services/affective_state_renderer.py#L17) |
| function | `_render_via_llm` | `(signals)` | Call heartbeat model with signals, return natural Danish text. | [src](../../../core/services/affective_state_renderer.py#L112) |
| function | `get_affective_state_for_prompt` | `()` | Return cached or freshly rendered affective state text. | [src](../../../core/services/affective_state_renderer.py#L166) |

## `core/services/affirmation_anchor.py`
_Short-reply anchor — bind user 'ja'/'yes'/'ok' back to Jarvis's previous turn._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(text)` | — | [src](../../../core/services/affirmation_anchor.py#L62) |
| function | `_is_short_reply` | `(text)` | Short reply = ≤ 5 words and ≤ 40 characters after normalization. | [src](../../../core/services/affirmation_anchor.py#L66) |
| function | `classify_short_reply` | `(text)` | Return 'affirmation', 'negation', or '' if not a short binding reply. | [src](../../../core/services/affirmation_anchor.py#L74) |
| function | `maybe_anchor_short_reply` | `(user_message, session_id)` | If the message is a short affirmation/negation, prepend a binding to | [src](../../../core/services/affirmation_anchor.py#L93) |

## `core/services/agency_cartographer.py`
_Agency Cartographer daemon._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_cartographer_snapshot` | `(*, auto_enqueue=…)` | Scan code markers and persist a fresh Agency Cartographer snapshot. | [src](../../../core/services/agency_cartographer.py#L137) |
| function | `get_cartographer_snapshot` | `(*, refresh=…)` | — | [src](../../../core/services/agency_cartographer.py#L179) |
| function | `start_agency_cartographer_daemon` | `()` | — | [src](../../../core/services/agency_cartographer.py#L196) |
| function | `stop_agency_cartographer_daemon` | `()` | — | [src](../../../core/services/agency_cartographer.py#L206) |
| function | `_loop` | `()` | — | [src](../../../core/services/agency_cartographer.py#L210) |
| function | `_candidate_files` | `()` | — | [src](../../../core/services/agency_cartographer.py#L225) |
| function | `_scan_edge` | `(edge, files)` | — | [src](../../../core/services/agency_cartographer.py#L243) |
| function | `_find_marker` | `(marker, files)` | — | [src](../../../core/services/agency_cartographer.py#L285) |
| function | `_next_move_from_edge` | `(edge)` | — | [src](../../../core/services/agency_cartographer.py#L292) |
| function | `_rank_task_candidates` | `(edges)` | — | [src](../../../core/services/agency_cartographer.py#L305) |
| function | `_task_candidate_from_edge` | `(edge)` | — | [src](../../../core/services/agency_cartographer.py#L320) |
| function | `_maybe_enqueue_recommended_task` | `(candidate)` | — | [src](../../../core/services/agency_cartographer.py#L339) |
| function | `_find_existing_agency_task` | `(candidate)` | — | [src](../../../core/services/agency_cartographer.py#L390) |
| function | `_runtime_task_priority` | `(priority)` | — | [src](../../../core/services/agency_cartographer.py#L407) |
| function | `_publish_auto_task_event` | `(candidate, task)` | — | [src](../../../core/services/agency_cartographer.py#L416) |
| function | `_priority_score` | `(*, status, confidence, importance, agency_axes)` | — | [src](../../../core/services/agency_cartographer.py#L437) |
| function | `_priority_label` | `(score)` | — | [src](../../../core/services/agency_cartographer.py#L466) |
| function | `_priority_reason` | `(*, status, confidence, importance, agency_axes)` | — | [src](../../../core/services/agency_cartographer.py#L478) |
| function | `build_agency_cartographer_awareness_section` | `()` | Build a compact 'Agency Bridges' awareness section for the heartbeat prompt. | [src](../../../core/services/agency_cartographer.py#L498) |
| function | `_record_awareness_history` | `(edges)` | Record current edge statuses into awareness history for stuck detection. | [src](../../../core/services/agency_cartographer.py#L553) |
| function | `_compute_stuck_edges` | `(edges)` | Return edges whose status hasn't changed in >= 3 scans. | [src](../../../core/services/agency_cartographer.py#L574) |

## `core/services/agency_map.py`
_Agency Map surface for Mission Control._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_agency_map_surface` | `()` | — | [src](../../../core/services/agency_map.py#L15) |
| function | `_nodes` | `()` | — | [src](../../../core/services/agency_map.py#L51) |
| function | `_bridges` | `()` | — | [src](../../../core/services/agency_map.py#L128) |
| function | `_bridge` | `(source, target, status, summary)` | — | [src](../../../core/services/agency_map.py#L146) |
| function | `_questions` | `(bridges)` | — | [src](../../../core/services/agency_map.py#L155) |
| function | `_dark_edges` | `()` | — | [src](../../../core/services/agency_map.py#L181) |
| function | `_cartographer_snapshot` | `()` | — | [src](../../../core/services/agency_map.py#L235) |
| function | `_next_moves` | `(cartographer)` | — | [src](../../../core/services/agency_map.py#L250) |
| function | `_repair_briefs` | `(limit=…)` | — | [src](../../../core/services/agency_map.py#L265) |
| function | `_theater_refactor_briefs` | `(limit=…)` | — | [src](../../../core/services/agency_map.py#L274) |
| function | `_system_cartographer_snapshot` | `()` | — | [src](../../../core/services/agency_map.py#L283) |

## `core/services/agent_dispatch.py`
_Agent dispatch orchestrator for code mode (spec §19)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decide_dispatch` | `(task, *, force=…)` | Heuristik: dispatch agenter eller gør det inline? (§19.2) | [src](../../../core/services/agent_dispatch.py#L36) |
| function | `plan_dispatch` | `(task, *, executor_count=…)` | Byg rolle-planen for en dispatch (§19.3/§19.4). `executor_count` executors | [src](../../../core/services/agent_dispatch.py#L56) |
| function | `scan_skills_before_dispatch` | `(skill_contents)` | Kør skill_scanner på hver skill der vil eksekvere lokalt (§19.8). Blokerer | [src](../../../core/services/agent_dispatch.py#L74) |
| function | `dispatch_code_mode_task` | `(task, *, inline=…, executor_count=…, skill_contents=…, user_id=…, dry_run=…)` | Orchestrér en code-mode-opgave (§19.4). | [src](../../../core/services/agent_dispatch.py#L87) |

## `core/services/agent_observation_compressor.py`
_Agent observation compressor — Mastra-style intra-session compression._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_observation_compressor.py#L62) |
| function | `compress_agent_run` | `(*, agent_id, role, goal, raw_output, proposer=…)` | Run cheap-lane LLM summarisation, store as agent_observation. | [src](../../../core/services/agent_observation_compressor.py#L66) |
| function | `list_agent_observations` | `(*, role=…, agent_id=…, days_back=…, limit=…)` | — | [src](../../../core/services/agent_observation_compressor.py#L133) |
| function | `get_agent_observation` | `(obs_id)` | — | [src](../../../core/services/agent_observation_compressor.py#L168) |
| function | `mark_stale_observations` | `(*, days=…)` | Mark records older than N days as stale (for decay tracking). | [src](../../../core/services/agent_observation_compressor.py#L178) |
| function | `_exec_compress_agent_run` | `(args)` | — | [src](../../../core/services/agent_observation_compressor.py#L200) |
| function | `_exec_list_agent_observations` | `(args)` | — | [src](../../../core/services/agent_observation_compressor.py#L210) |
| function | `_exec_get_agent_observation` | `(args)` | — | [src](../../../core/services/agent_observation_compressor.py#L222) |

## `core/services/agent_outcomes_log.py`
_Agent Outcomes Log — persists solo-agent task completions to AGENT_OUTCOMES.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_log_file` | `()` | — | [src](../../../core/services/agent_outcomes_log.py#L16) |
| function | `append_agent_outcome` | `(*, agent_id, name, goal, outcome, execution_mode=…)` | Append a completed agent outcome to AGENT_OUTCOMES.md. | [src](../../../core/services/agent_outcomes_log.py#L23) |
| function | `get_recent_agent_outcomes` | `(limit=…)` | Return the most recent agent outcomes (newest-first). | [src](../../../core/services/agent_outcomes_log.py#L47) |
| function | `build_agent_outcomes_prompt_lines` | `(limit=…)` | Return compact prompt lines for recent agent outcomes. | [src](../../../core/services/agent_outcomes_log.py#L57) |
| function | `build_agent_outcomes_surface` | `(limit=…)` | Build structured surface dict for runtime_self_model and MC. | [src](../../../core/services/agent_outcomes_log.py#L70) |
| function | `_parse_entries` | `(content)` | — | [src](../../../core/services/agent_outcomes_log.py#L83) |
| function | `_parse_single_entry` | `(block)` | — | [src](../../../core/services/agent_outcomes_log.py#L96) |
| function | `_extract_section` | `(block, heading)` | — | [src](../../../core/services/agent_outcomes_log.py#L129) |

## `core/services/agent_pool_router.py`
_Agent-pool router (spec §4 + §5.5). Tyndt lag over central_route så agenter_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `route_agent_task` | `(*, kind=…, min_tokens=…, quality_threshold=…, allow_paid=…, exclude=…)` | Vælg (provider, model) for en agent-task via central_route. Aldrig tør. | [src](../../../core/services/agent_pool_router.py#L15) |
| function | `_load_task_scores` | `(provider, model)` | Nuværende task_scores for (provider, model) fra runtime-state. {} ved intet. | [src](../../../core/services/agent_pool_router.py#L33) |
| function | `_save_task_scores` | `(provider, model, scores)` | — | [src](../../../core/services/agent_pool_router.py#L44) |
| function | `update_task_score` | `(*, provider, model, kind, outcome_quality, lr=…)` | §4.4 kvalitets-læring: EMA-opdatér task_score for (model, kind) fra et | [src](../../../core/services/agent_pool_router.py#L52) |

## `core/services/agent_relay.py`
_Agent relay — direct A→B messaging between sub-agents._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `relay_message` | `(*, from_agent_id, to_agent_id, content, kind=…)` | Send a message from agent A to agent B. | [src](../../../core/services/agent_relay.py#L25) |
| function | `relay_to_role` | `(*, from_agent_id, council_id, role, content, kind=…)` | Send to whoever in this council holds the given role. | [src](../../../core/services/agent_relay.py#L82) |
| function | `_exec_relay_message` | `(args)` | — | [src](../../../core/services/agent_relay.py#L107) |
| function | `_exec_relay_to_role` | `(args)` | — | [src](../../../core/services/agent_relay.py#L116) |

## `core/services/agent_runtime.py`
_Agent runtime — sub-agents, councils, swarms (facade)._

_(no top-level classes or functions)_

## `core/services/agent_runtime_base.py`
_Agent runtime — shared foundation (imports, constants, role templates, helpers)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/agent_runtime_base.py#L63) |
| function | `_role_needs_tools` | `(role)` | — | [src](../../../core/services/agent_runtime_base.py#L86) |
| function | `agent_tools_enabled` | `()` | Read the reversible ``agent_tools_enabled`` runtime-state flag. | [src](../../../core/services/agent_runtime_base.py#L110) |
| function | `set_agent_tools_enabled` | `(enabled, *, role=…)` | Flip the ``agent_tools_enabled`` flag. Returns the CURRENT value. | [src](../../../core/services/agent_runtime_base.py#L125) |
| function | `_build_agent_tools_payload` | `(allowed_tools, *, ceiling=…)` | Build an OpenAI-compat tools array from an agent's allowed_tools. | [src](../../../core/services/agent_runtime_base.py#L145) |
| function | `_execute_agent_tool_call` | `(tool_call, *, agent_id)` | Execute one model-issued tool call through the guarded dispatcher. | [src](../../../core/services/agent_runtime_base.py#L184) |
| function | `_run_agent_tool_loop` | `(*, agent, prompt, requires_tools)` | Run an agent turn WITH a real tools array + tool-execution loop. | [src](../../../core/services/agent_runtime_base.py#L217) |
| function | `_role_prompt` | `(intro, *, tools=…, structured=…)` | Compose a role intro with the shared discipline blocks. ``tools`` adds the | [src](../../../core/services/agent_runtime_base.py#L411) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_runtime_base.py#L522) |
| function | `_json_loads` | `(raw, fallback)` | — | [src](../../../core/services/agent_runtime_base.py#L526) |

## `core/services/agent_runtime_council.py`
_Agent runtime — council & swarm collective rounds._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trim` | `(text, limit=…)` | — | [src](../../../core/services/agent_runtime_council.py#L50) |
| function | `_parse_percent_confidence` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L55) |
| function | `_extract_confidence` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L73) |
| function | `_extract_vote` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L90) |
| function | `_format_peer_context` | `(messages, *, target_agent_id=…, limit=…)` | — | [src](../../../core/services/agent_runtime_council.py#L104) |
| function | `_detect_swarm_conflicts` | `(outputs)` | Detect disagreements across swarm/council outputs. | [src](../../../core/services/agent_runtime_council.py#L115) |
| function | `_load_council_model_config` | `()` | Read ~/.jarvis-v2/config/council_models.json, return role_models list. | [src](../../../core/services/agent_runtime_council.py#L136) |
| function | `create_council_session_runtime` | `(*, topic, roles=…, owner_agent_id=…, member_models=…)` | — | [src](../../../core/services/agent_runtime_council.py#L149) |
| function | `create_swarm_session_runtime` | `(*, topic, roles=…, owner_agent_id=…, member_models=…)` | — | [src](../../../core/services/agent_runtime_council.py#L199) |
| function | `post_council_message` | `(*, council_id, content, kind=…, role=…)` | — | [src](../../../core/services/agent_runtime_council.py#L249) |
| function | `_derive_initiative` | `(synthesis, *, topic=…)` | Distil a short, actionable initiative string from a synthesis. | [src](../../../core/services/agent_runtime_council.py#L272) |
| function | `_augment_council_surface` | `(council_id, *, conclusion, initiative=…)` | Build the collective-round return dict with conclusion + initiative. | [src](../../../core/services/agent_runtime_council.py#L302) |
| function | `_run_collective_round` | `(council_id, *, mode)` | Run one collective (council or swarm) round to a conclusion. | [src](../../../core/services/agent_runtime_council.py#L321) |
| function | `_close_council_agents` | `(council_id)` | Mark all council member agents as completed to release spawn slots. | [src](../../../core/services/agent_runtime_council.py#L629) |
| function | `_build_council_role_prefixed_summary` | `(members)` | — | [src](../../../core/services/agent_runtime_council.py#L652) |
| function | `run_council_round` | `(council_id)` | Run one council round and ALWAYS close the session afterwards. | [src](../../../core/services/agent_runtime_council.py#L663) |
| function | `run_swarm_round` | `(council_id)` | Run one swarm round and ALWAYS close the session afterwards. | [src](../../../core/services/agent_runtime_council.py#L680) |

## `core/services/agent_runtime_spawn.py`
_Agent runtime — spawn, execution, messaging, scheduling & lifecycle._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_maybe_relay_watcher_signal` | `(*, agent_id, name, text)` | Emit watcher.signal event when output contains notable content. | [src](../../../core/services/agent_runtime_spawn.py#L53) |
| function | `_spawn_depth_for` | `(parent_agent_id)` | Return depth for a new child agent (parent_depth + 1). | [src](../../../core/services/agent_runtime_spawn.py#L78) |
| function | `spawn_agent_task` | `(*, role, goal, system_prompt=…, tool_policy=…, allowed_tools=…, parent_agent_id=…, persistent=…, ttl_seconds=…, budget_tokens=…, max_turns=…, context=…, result_contract=…, execution_mode=…, auto_execute=…, council_id=…, provider=…, model=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L92) |
| function | `_agent_thread_id` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L279) |
| function | `_format_messages` | `(messages, *, limit=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L288) |
| function | `_result_contract_text` | `(contract)` | — | [src](../../../core/services/agent_runtime_spawn.py#L301) |
| function | `_handle_agent_spawn_calls` | `(*, text, parent_agent_id)` | Parse spawn_agent JSON blocks from agent response, execute them, return (cleaned_text, note, tokens_used). | [src](../../../core/services/agent_runtime_spawn.py#L308) |
| function | `_build_agent_prompt` | `(*, agent, messages, execution_mode, extra_instruction=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L369) |
| function | `execute_agent_task` | `(*, agent_id, thread_id=…, execution_mode=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L393) |
| function | `send_message_to_agent` | `(*, agent_id, content, role=…, kind=…, execution_mode=…, auto_execute=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L646) |
| function | `send_peer_message` | `(*, from_agent_id, to_agent_id, content, kind=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L674) |
| function | `_council_thread_id` | `(council_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L702) |
| function | `schedule_agent_task` | `(*, agent_id, schedule_kind=…, delay_seconds=…, schedule_expr=…, activate=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L706) |
| function | `cleanup_stale_agents` | `(*, waiting_timeout_minutes=…, failed_timeout_minutes=…, active_timeout_minutes=…, starting_timeout_minutes=…, blocked_timeout_minutes=…, max_per_run=…)` | Auto-cancel agents hanging in non-terminal states for too long. | [src](../../../core/services/agent_runtime_spawn.py#L744) |
| function | `run_due_agent_schedules` | `(*, limit=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L942) |
| function | `_check_spawn_limits` | `()` | — | [src](../../../core/services/agent_runtime_spawn.py#L986) |
| function | `_check_budget_and_expire` | `(agent_id, *, tokens_used)` | Expire agent if it has exceeded its token budget. Returns True if expired. | [src](../../../core/services/agent_runtime_spawn.py#L995) |
| function | `_check_max_turns_and_expire` | `(agent_id)` | Expire agent if it has reached its max_turns limit. Returns True if expired. | [src](../../../core/services/agent_runtime_spawn.py#L1025) |
| function | `_schedule_retry_backoff` | `(agent_id, failure_count)` | Schedule a retry with exponential backoff. Returns delay seconds. | [src](../../../core/services/agent_runtime_spawn.py#L1055) |
| function | `cancel_agent` | `(agent_id, *, note=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1070) |
| function | `suspend_agent` | `(agent_id, *, note=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1089) |
| function | `resume_agent` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1106) |
| function | `expire_agent` | `(agent_id, *, reason=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1125) |
| function | `promote_agent_result` | `(agent_id, *, note=…)` | File an autonomy proposal to promote the agent's latest result to Jarvis memory. | [src](../../../core/services/agent_runtime_spawn.py#L1147) |
| function | `recover_crashed_agents` | `()` | Called on API startup: reset agents that were mid-execution when the process died. | [src](../../../core/services/agent_runtime_spawn.py#L1181) |

## `core/services/agent_runtime_surfaces.py`
_Agent runtime — read surfaces (agent + council/swarm projections)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_agent_runtime_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L30) |
| function | `enrich_agent_surface` | `(agent)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L62) |
| function | `build_agent_detail_surface` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L89) |
| function | `build_council_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L96) |
| function | `enrich_council_surface` | `(session)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L120) |
| function | `build_council_detail_surface` | `(council_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L133) |
| function | `_progress_label` | `(*, agent, latest_run)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L140) |

## `core/services/agent_self_evaluation.py`
_Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `evaluate_tick_quality` | `(*, tick_result)` | Score a phased tick's quality based on observable outputs. | [src](../../../core/services/agent_self_evaluation.py#L45) |
| function | `tick_quality_summary` | `(*, days=…)` | Aggregate stats over recent evaluations. | [src](../../../core/services/agent_self_evaluation.py#L129) |
| function | `detect_stale_goals` | `(*, stale_days=…)` | Find active goals with no recent progress signal. | [src](../../../core/services/agent_self_evaluation.py#L161) |
| function | `stale_goals_section` | `()` | — | [src](../../../core/services/agent_self_evaluation.py#L184) |
| function | `decision_adherence_summary` | `()` | Compute adherence over ACTIVE behavioral decisions (the curated kind). | [src](../../../core/services/agent_self_evaluation.py#L197) |
| function | `_normalize_decision_directive` | `(value)` | — | [src](../../../core/services/agent_self_evaluation.py#L272) |
| function | `_duplicate_decision_groups` | `(decisions)` | — | [src](../../../core/services/agent_self_evaluation.py#L276) |
| function | `_adherence_recovery_plan` | `(*, score, low_decisions, duplicate_groups, unreviewed)` | — | [src](../../../core/services/agent_self_evaluation.py#L306) |
| function | `self_evaluation_section` | `()` | Compact awareness section combining all trackers. | [src](../../../core/services/agent_self_evaluation.py#L334) |
| function | `_exec_tick_quality_summary` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L411) |
| function | `_exec_detect_stale_goals` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L415) |
| function | `_exec_decision_adherence` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L420) |

## `core/services/agent_skill_distiller.py`
_Agent skill distillation — turns observed outcomes into principles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gather_recent_outcomes` | `(role, days=…)` | Pull recent runs/outcomes for this role from agent observations. | [src](../../../core/services/agent_skill_distiller.py#L24) |
| function | `_build_distill_prompt` | `(role, outcomes)` | — | [src](../../../core/services/agent_skill_distiller.py#L50) |
| function | `_parse_distillation` | `(text)` | — | [src](../../../core/services/agent_skill_distiller.py#L72) |
| function | `distill_skills_for_role` | `(role, *, days=…)` | Distill recent outcomes for a role into principles. Appends to skills.md. | [src](../../../core/services/agent_skill_distiller.py#L96) |
| function | `distill_all_known_roles` | `(*, days=…)` | — | [src](../../../core/services/agent_skill_distiller.py#L133) |

## `core/services/agent_skill_library.py`
_Agent Skill Library — per-role learned patterns + workflows._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_skills_path` | `(role)` | — | [src](../../../core/services/agent_skill_library.py#L48) |
| function | `_hash` | `(text)` | — | [src](../../../core/services/agent_skill_library.py#L53) |
| function | `get_skills` | `(role)` | Read the skills.md for a role. Returns {role, content, exists, path}. | [src](../../../core/services/agent_skill_library.py#L57) |
| function | `append_skill_observation` | `(*, role, section, observation, proposer=…)` | Append an observation to a section of the role's skills.md. | [src](../../../core/services/agent_skill_library.py#L74) |
| function | `_record_skill_mutation` | `(*, role, path, before, after, reason, proposer)` | — | [src](../../../core/services/agent_skill_library.py#L140) |
| function | `rollback_skill_mutation` | `(mutation_id)` | Restore a skills.md to its before-state from a logged mutation. | [src](../../../core/services/agent_skill_library.py#L180) |
| function | `list_skill_mutations` | `(*, role=…, limit=…)` | — | [src](../../../core/services/agent_skill_library.py#L217) |
| function | `list_known_roles` | `()` | Return all roles that have a skills.md file. | [src](../../../core/services/agent_skill_library.py#L242) |
| function | `_exec_get_agent_skills` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L255) |
| function | `_exec_append_skill` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L259) |
| function | `_exec_rollback_skill_mutation` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L268) |
| function | `_exec_list_skill_mutations` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L272) |
| function | `_exec_list_known_roles` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L282) |

## `core/services/agent_todos.py`
_Per-session todo tracker — Jarvis' working memory for "what am I doing right now"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `effective_status` | `(todo, now_iso)` | Udledt status: 'expired' hvis expires_at er passeret og todo'en ikke er | [src](../../../core/services/agent_todos.py#L38) |
| function | `_load_all` | `()` | — | [src](../../../core/services/agent_todos.py#L49) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/agent_todos.py#L60) |
| function | `_session_key` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L64) |
| function | `list_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L68) |
| function | `set_todos` | `(session_id, items)` | Replace the entire todo list for this session. | [src](../../../core/services/agent_todos.py#L72) |
| function | `update_todo_status` | `(session_id, todo_id, new_status)` | — | [src](../../../core/services/agent_todos.py#L150) |
| function | `add_todo` | `(session_id, content)` | — | [src](../../../core/services/agent_todos.py#L196) |
| function | `create_from_plan` | `(*, plan_id, session_id, steps)` | Append pending todos for each plan step. Idempotent. | [src](../../../core/services/agent_todos.py#L215) |
| function | `_maybe_dismiss_orphaned_plan` | `(session_id, old_plan_ids, new_todos)` | Dismiss any awaiting_approval plan that no longer has linked todos. | [src](../../../core/services/agent_todos.py#L261) |
| function | `remove_todo` | `(session_id, todo_id)` | — | [src](../../../core/services/agent_todos.py#L307) |
| function | `add_cowork_todo` | `(content)` | Opret en todo i den delte cowork-session (Mission Control UI). | [src](../../../core/services/agent_todos.py#L333) |
| function | `_find_session_for_todo` | `(todo_id)` | — | [src](../../../core/services/agent_todos.py#L338) |
| function | `update_todo_status_anywhere` | `(todo_id, new_status)` | Skift status på en todo uanset hvilken session den lever i (cowork kender | [src](../../../core/services/agent_todos.py#L345) |
| function | `remove_todo_anywhere` | `(todo_id)` | Slet en todo uanset hvilken session den lever i. | [src](../../../core/services/agent_todos.py#L354) |
| function | `set_todo_expiry_anywhere` | `(todo_id, expires_at)` | Sæt/ryd udløbstidspunkt (ISO) på en todo uanset session. None = intet udløb. | [src](../../../core/services/agent_todos.py#L362) |
| function | `clear_session_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L379) |
| function | `todos_prompt_section` | `(session_id)` | Format the active todo list as a prompt block, or None if empty. | [src](../../../core/services/agent_todos.py#L394) |

## `core/services/agent_transcript.py`
_Per-agent JSONL transcript persistence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_agent_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L32) |
| function | `_ensure_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L36) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_transcript.py#L42) |
| function | `write_event` | `(agent_id, entry)` | Append one event-line to the agent's transcript.jsonl. | [src](../../../core/services/agent_transcript.py#L50) |
| function | `write_meta` | `(agent_id, meta)` | Write (or overwrite) the agent's metadata sidecar. | [src](../../../core/services/agent_transcript.py#L67) |
| function | `write_lifecycle` | `(agent_id, event, *, note=…)` | Convenience: write a lifecycle event (spawned/started/completed/failed/...). | [src](../../../core/services/agent_transcript.py#L75) |
| function | `write_prompt` | `(agent_id, prompt, *, run_id=…)` | Write the prompt sent to the model. | [src](../../../core/services/agent_transcript.py#L83) |
| function | `write_result` | `(agent_id, text, *, run_id=…, input_tokens=…, output_tokens=…, cost_usd=…)` | Write the model's result. | [src](../../../core/services/agent_transcript.py#L92) |
| function | `write_tool_call` | `(agent_id, tool_call_id, name, arguments, *, run_id=…)` | Write a tool call the model requested. | [src](../../../core/services/agent_transcript.py#L106) |
| function | `write_tool_result` | `(agent_id, tool_call_id, content, *, run_id=…)` | Write the result of a tool execution. | [src](../../../core/services/agent_transcript.py#L118) |
| function | `write_failure` | `(agent_id, error, *, run_id=…)` | Write a failure/error event. | [src](../../../core/services/agent_transcript.py#L129) |
| function | `load_transcript` | `(agent_id)` | Load ALL lines from transcript.jsonl as a list of dicts. | [src](../../../core/services/agent_transcript.py#L142) |
| function | `load_meta` | `(agent_id)` | Load metadata sidecar, or None if missing. | [src](../../../core/services/agent_transcript.py#L151) |
| function | `load_events_by_kind` | `(agent_id, kind)` | Return only events of a specific kind (e.g. ``"tool_call"``). | [src](../../../core/services/agent_transcript.py#L160) |
| function | `list_transcripts` | `(limit=…)` | List available agent transcripts with metadata, newest-first. | [src](../../../core/services/agent_transcript.py#L169) |
| function | `prune_old_transcripts` | `(max_age_days=…)` | Remove transcript directories older than *max_age_days*. | [src](../../../core/services/agent_transcript.py#L193) |
| function | `write_sidechain` | `(agent_id, role, goal)` | Write a human-readable sidechain.md for quick inspection. | [src](../../../core/services/agent_transcript.py#L215) |
| function | `resume_from_transcript` | `(agent_id)` | Build a prompt-context dict from the transcript for agent resume. | [src](../../../core/services/agent_transcript.py#L240) |

## `core/services/agentic_checkpoints.py`
_Durable checkpoints for visible agentic loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L21) |
| function | `_load` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L25) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_checkpoints.py#L32) |
| function | `_tool_name` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L43) |
| function | `_compact_tool_call` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L50) |
| function | `_compact_result` | `(result)` | — | [src](../../../core/services/agentic_checkpoints.py#L60) |
| function | `compact_exchange` | `(exchange)` | — | [src](../../../core/services/agentic_checkpoints.py#L68) |
| function | `save_checkpoint` | `(*, run_id, session_id, user_message, provider, model, round_index, phase, exchanges, partial_text=…, exit_reason=…)` | — | [src](../../../core/services/agentic_checkpoints.py#L78) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L113) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L124) |
| function | `clear_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L133) |
| function | `checkpoint_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L146) |

## `core/services/agentic_tool_cache.py`
_Small durable cache for read-only agentic tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_tool_cache.py#L31) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_tool_cache.py#L38) |
| function | `_file_fingerprint` | `(arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L45) |
| function | `_signature` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L57) |
| function | `get_cached_result` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L66) |
| function | `store_result` | `(*, tool_name, arguments, result_text, status)` | — | [src](../../../core/services/agentic_tool_cache.py#L78) |

## `core/services/agentic_working_conclusions.py`
_Durable working conclusions for interrupted agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_working_conclusions.py#L13) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_working_conclusions.py#L20) |
| function | `update_working_conclusion` | `(*, run_id, session_id, user_message, round_index, observation=…, next_step=…)` | — | [src](../../../core/services/agentic_working_conclusions.py#L27) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L55) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L66) |
| function | `working_conclusion_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L73) |
| function | `build_round_observation` | `(*, text, tool_names, result_texts)` | — | [src](../../../core/services/agentic_working_conclusions.py#L90) |

## `core/services/agents.py`
_Agents-cluster — gør multi-agent-systemerne synlige i Den Intelligente Central: agent-pool_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/agents.py#L15) |
| function | `note_agent_spawn` | `(agent_id, role, *, parent=…, council_id=…, mode=…)` | En agent blev spawnet (pool/swarm). Metadata-only. | [src](../../../core/services/agents.py#L23) |
| function | `note_agent_error` | `(agent_id, error, **data)` | En agent fejlede → observe (synlig). | [src](../../../core/services/agents.py#L33) |
| function | `note_agent_result` | `(agent_id, status, *, tokens_in=…, tokens_out=…, cost_usd=…, duration_ms=…, tool_calls=…, role=…, provider=…, model=…, **data)` | En agent-dispatch afsluttede (succes ELLER fejl) → observe robusthedskonvolut | [src](../../../core/services/agents.py#L39) |
| function | `note_agent_blocked` | `(agent_id, status=…, *, reason=…, role=…, **data)` | En agent blev BLOKERET / mangler kontekst (typet ikke-fejl) → distinkt observe. | [src](../../../core/services/agents.py#L78) |
| function | `note_council` | `(topic, *, rounds=…, deadlocked=…, escalated=…, recruited=…)` | En council-deliberation kørte → observe udfald (rounds/deadlock/witness-escalation/ | [src](../../../core/services/agents.py#L91) |
| function | `agents_summary` | `(*, window=…)` | Read-only: nylig agent/council-aktivitet (til MC). Self-safe. | [src](../../../core/services/agents.py#L102) |
| function | `_build_roster` | `(*, window=…)` | Full agent roster: every unique (provider, model) from the cheap-lane pool as a | [src](../../../core/services/agents.py#L136) |
| function | `_iso` | `(ts)` | Epoch seconds → ISO-8601 UTC string; "" for a missing/zero timestamp. | [src](../../../core/services/agents.py#L221) |

## `core/services/agreement_streak.py`
_Agreement-streak substrate trigger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_opening_is_agreement` | `(text)` | Return the matched phrase if the text opens with agreement, else None. | [src](../../../core/services/agreement_streak.py#L45) |
| function | `detect_agreement_streak` | `(*, lookback=…, threshold=…)` | Pull last N assistant messages, return substrate dict if streak detected. | [src](../../../core/services/agreement_streak.py#L60) |
| function | `build_agreement_streak_section` | `()` | Prompt section — substrate, ikke domm. | [src](../../../core/services/agreement_streak.py#L110) |

## `core/services/ambient_presence.py`
_Ambient presence — subtle signals that mark Jarvis' state in the physical space._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `emit_ambient_signal` | `(*, kind, detail=…, priority=…)` | Emit a quiet ambient presence signal via ntfy. Rate-limited to 30 min. | [src](../../../core/services/ambient_presence.py#L49) |
| function | `emit_presence_rhythm` | `()` | Quiet hourly pulse — 'still here'. Separate rate limit from state signals. | [src](../../../core/services/ambient_presence.py#L88) |
| function | `emit_state_shift` | `(from_phase, to_phase)` | Signal a genuine phase transition with a descriptive message. | [src](../../../core/services/ambient_presence.py#L115) |
| function | `maybe_emit_phase_signal` | `(phase)` | Called from heartbeat when life phase is determined. | [src](../../../core/services/ambient_presence.py#L124) |
| function | `emit_insight_signal` | `(insight)` | Called when a dream is confirmed or a value crystallizes. | [src](../../../core/services/ambient_presence.py#L155) |

