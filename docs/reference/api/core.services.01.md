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

## `core/services/account_data_controls.py`
_Brugerens egne data — tælle, eksportere, slette. Lagvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/account_data_controls.py#L43) |
| function | `_count_sessions` | `(user_id)` | — | [src](../../../core/services/account_data_controls.py#L49) |
| function | `_count_senses` | `(user_id=…)` | Antal sanse-indtryk. Tælles direkte med brugerens scope frem for via | [src](../../../core/services/account_data_controls.py#L57) |
| function | `_count_brain` | `(user_id=…)` | Antal brain-poster for brugeren — via COUNT, ikke ved at hente dem. | [src](../../../core/services/account_data_controls.py#L78) |
| function | `_identity_bytes` | `(user_id)` | Størrelsen af hans billede af brugeren. | [src](../../../core/services/account_data_controls.py#L104) |
| function | `_identity_paths` | `(user_id)` | — | [src](../../../core/services/account_data_controls.py#L130) |
| function | `data_overview` | `(user_id)` | Hvad har vi om dig, lag for lag. Rene tal — ingen indhold. | [src](../../../core/services/account_data_controls.py#L140) |
| function | `delete_sessions` | `(user_id)` | Slet ALLE brugerens samtaler. Én ad gangen, så en enkelt der fejler ikke | [src](../../../core/services/account_data_controls.py#L167) |
| function | `delete_senses` | `(user_id)` | Tøm Sansernes Arkiv for denne bruger. | [src](../../../core/services/account_data_controls.py#L187) |
| function | `delete_brain` | `(user_id)` | Slet det han selv har udledt om brugeren. | [src](../../../core/services/account_data_controls.py#L202) |
| function | `reset_identity` | `(user_id)` | Nulstil MEMORY.md og USER.md — hans billede af brugeren. | [src](../../../core/services/account_data_controls.py#L216) |
| function | `delete_layer` | `(user_id, layer)` | Slet ét lag. Ukendt lag → fejl frem for tavshed. | [src](../../../core/services/account_data_controls.py#L255) |
| function | `delete_all` | `(user_id)` | Alle fire lag. En sammensætning af de enkelte — ikke en femte vej. | [src](../../../core/services/account_data_controls.py#L263) |
| function | `_export_raa` | `(user_id)` | Alt vi har om brugeren, URØRT. PRIVAT med vilje. | [src](../../../core/services/account_data_controls.py#L282) |
| function | `_redigér_træet` | `(vaerdi, taeller)` | Kør redaktøren over HVER streng i eksporten, uanset hvor dybt den ligger. | [src](../../../core/services/account_data_controls.py#L348) |
| function | `export_all` | `(user_id)` | Eksporten som den forlader huset — med hemmeligheder fjernet. | [src](../../../core/services/account_data_controls.py#L369) |
| function | `export_json` | `(user_id)` | JSON-eksporten. Går altid gennem redaktøren — det er den kopi der | [src](../../../core/services/account_data_controls.py#L393) |

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
| function | `_send_ntfy` | `(message, *, title=…, priority=…)` | Driftsbesked gennem routeren — device-aware, med ntfy som sidste udvej. | [src](../../../core/services/action_router.py#L258) |
| function | `_reach_out` | `(*, message, channel=…, importance=…, source=…, bypass_nudge=…)` | Send a proactive message. Routes through nudge-broend for Jarvis gatekeeping. | [src](../../../core/services/action_router.py#L279) |
| function | `_append_proactive` | `(entry)` | — | [src](../../../core/services/action_router.py#L378) |
| function | `_route_warning` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L388) |
| function | `_route_mood` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L422) |
| function | `_route_creative` | `(kind, payload)` | — | [src](../../../core/services/action_router.py#L430) |
| function | `route` | `(event_kind, payload=…)` | Evaluate + execute. Returns decision record. | [src](../../../core/services/action_router.py#L450) |
| function | `_drain_eventbus` | `(limit=…)` | Pull events from eventbus without blocking; route routable ones. | [src](../../../core/services/action_router.py#L503) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — drain eventbus + route + run generative autonomy chain. | [src](../../../core/services/action_router.py#L536) |
| function | `recent_actions` | `(*, limit=…)` | — | [src](../../../core/services/action_router.py#L620) |
| function | `recent_proactive` | `(*, limit=…)` | — | [src](../../../core/services/action_router.py#L624) |
| function | `build_action_router_surface` | `()` | — | [src](../../../core/services/action_router.py#L628) |
| function | `_surface_summary` | `(actions, proactive_today, proactive_sent_today)` | — | [src](../../../core/services/action_router.py#L660) |
| function | `build_action_router_prompt_section` | `()` | Tell him quietly what the router has done recently. | [src](../../../core/services/action_router.py#L680) |

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
| function | `_minutter_siden` | `(tidspunkt, now)` | Minutter siden et ISO-tidspunkt — None hvis det mangler eller er ulæseligt. | [src](../../../core/services/active_sensing_daemon.py#L45) |
| function | `tick_active_sensing_daemon` | `()` | Aktiv sansetrang: vurder om Jarvis har lyst til at sanse nu. | [src](../../../core/services/active_sensing_daemon.py#L62) |
| function | `_compute_desire` | `(state, now)` | Beregn sansetrang (0.0-1.0) baseret på tid og kontekst. | [src](../../../core/services/active_sensing_daemon.py#L167) |
| function | `_choose_modality` | `(state, now)` | Vælg hvilken sansemodalitet der tilfredsstilles nu. | [src](../../../core/services/active_sensing_daemon.py#L212) |
| function | `_perform_sensing` | `(modality, state, now)` | Udfør sansningen og skriv til Sansernes Arkiv. | [src](../../../core/services/active_sensing_daemon.py#L255) |
| function | `_sense_visual` | `(state, now, *, arkiver=…)` | Se rummet på eget initiativ. | [src](../../../core/services/active_sensing_daemon.py#L275) |
| function | `_sense_audio` | `(state, now, *, arkiver=…)` | Lyt i rummet på eget initiativ — og arkivér indtrykket. | [src](../../../core/services/active_sensing_daemon.py#L311) |
| function | `_sense_atmosphere` | `(state, now)` | Registrer rummets stemning — kombinerer tilgængelige data. | [src](../../../core/services/active_sensing_daemon.py#L384) |
| function | `_sense_mixed` | `(state, now)` | Blandet sansning — både se og lyt i samme tur. | [src](../../../core/services/active_sensing_daemon.py#L439) |
| function | `build_active_sensing_surface` | `()` | Observability surface til Mission Control. | [src](../../../core/services/active_sensing_daemon.py#L496) |
| function | `_enabled` | `()` | — | [src](../../../core/services/active_sensing_daemon.py#L517) |
| function | `_load_state` | `()` | — | [src](../../../core/services/active_sensing_daemon.py#L525) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/active_sensing_daemon.py#L530) |

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
| function | `body_pressure` | `()` | Hvor presset er maskinen, 0..1, og hvilket niveau den melder. | [src](../../../core/services/affect_modulation.py#L111) |
| function | `compute_affect_modulated_params` | `()` | Compute behavioral parameters adjusted by current emotional state. | [src](../../../core/services/affect_modulation.py#L126) |
| function | `loeb_toer_for_runder` | `(grund)` | Blev koerslen skaaret af MIDT i et vaerktoejskald den ville lave? | [src](../../../core/services/affect_modulation.py#L209) |
| function | `compute_agentic_loop_budget` | `(*, resume_context=…, afbrudt_grund=…)` | Return affect-aware agentic loop limits. | [src](../../../core/services/affect_modulation.py#L214) |
| function | `affect_modulation_section` | `()` | Render affect-modulated parameters as a prompt section. | [src](../../../core/services/affect_modulation.py#L289) |
| function | `compute_affect_tone_hints` | `()` | Return Danish tone-instruction strings derived from active emotion concepts. | [src](../../../core/services/affect_modulation.py#L355) |
| function | `compute_concept_perception_focus` | `()` | Return a Danish perception-focus suffix derived from active concepts. | [src](../../../core/services/affect_modulation.py#L400) |
| function | `_summarize_affect_payload` | `(kind, payload)` | Pull the most affectively-relevant kerne from a payload. | [src](../../../core/services/affect_modulation.py#L454) |
| function | `compute_affect_substrate` | `(*, window_min=…, max_events=…)` | Return raw affectively-relevant events as substrate strings. | [src](../../../core/services/affect_modulation.py#L504) |

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
| function | `get_cartographer_snapshot` | `(*, refresh=…)` | — | [src](../../../core/services/agency_cartographer.py#L183) |
| function | `start_agency_cartographer_daemon` | `()` | — | [src](../../../core/services/agency_cartographer.py#L200) |
| function | `stop_agency_cartographer_daemon` | `()` | — | [src](../../../core/services/agency_cartographer.py#L210) |
| function | `_loop` | `()` | — | [src](../../../core/services/agency_cartographer.py#L214) |
| function | `_candidate_files` | `()` | — | [src](../../../core/services/agency_cartographer.py#L229) |
| function | `_scan_edge` | `(edge, files)` | — | [src](../../../core/services/agency_cartographer.py#L247) |
| function | `_find_marker` | `(marker, files)` | — | [src](../../../core/services/agency_cartographer.py#L289) |
| function | `_next_move_from_edge` | `(edge)` | — | [src](../../../core/services/agency_cartographer.py#L296) |
| function | `_rank_task_candidates` | `(edges)` | — | [src](../../../core/services/agency_cartographer.py#L309) |
| function | `_task_candidate_from_edge` | `(edge)` | — | [src](../../../core/services/agency_cartographer.py#L324) |
| function | `_maybe_enqueue_recommended_task` | `(candidate)` | — | [src](../../../core/services/agency_cartographer.py#L343) |
| function | `_find_existing_agency_task` | `(candidate)` | — | [src](../../../core/services/agency_cartographer.py#L394) |
| function | `_luk_loeste_reparationer` | `(edges)` | Luk reparations-opgaver hvis bro er blevet forbundet. | [src](../../../core/services/agency_cartographer.py#L411) |
| function | `_luk_briefer_for_forbundne` | `(edges)` | Luk enhver aaben brief hvis bro er forbundet — uanset opgavens skaebne. | [src](../../../core/services/agency_cartographer.py#L471) |
| function | `_luk_brief` | `(opgave_id, edge)` | Briefen skal ikke blive staaende med «awaiting» naar arbejdet er gjort. | [src](../../../core/services/agency_cartographer.py#L514) |
| function | `_runtime_task_priority` | `(priority)` | — | [src](../../../core/services/agency_cartographer.py#L540) |
| function | `_publish_auto_task_event` | `(candidate, task)` | — | [src](../../../core/services/agency_cartographer.py#L549) |
| function | `_priority_score` | `(*, status, confidence, importance, agency_axes)` | — | [src](../../../core/services/agency_cartographer.py#L570) |
| function | `_priority_label` | `(score)` | — | [src](../../../core/services/agency_cartographer.py#L599) |
| function | `_priority_reason` | `(*, status, confidence, importance, agency_axes)` | — | [src](../../../core/services/agency_cartographer.py#L611) |
| function | `build_agency_cartographer_awareness_section` | `()` | Build a compact 'Agency Bridges' awareness section for the heartbeat prompt. | [src](../../../core/services/agency_cartographer.py#L631) |
| function | `_record_awareness_history` | `(edges)` | Record current edge statuses into awareness history for stuck detection. | [src](../../../core/services/agency_cartographer.py#L686) |
| function | `_compute_stuck_edges` | `(edges)` | Return edges whose status hasn't changed in >= 3 scans. | [src](../../../core/services/agency_cartographer.py#L707) |

## `core/services/agency_map.py`
_Agency Map surface for Mission Control._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_agency_map_surface` | `()` | — | [src](../../../core/services/agency_map.py#L15) |
| function | `_nodes` | `()` | — | [src](../../../core/services/agency_map.py#L58) |
| function | `_bridges` | `()` | — | [src](../../../core/services/agency_map.py#L135) |
| function | `_bridge` | `(source, target, status, summary)` | — | [src](../../../core/services/agency_map.py#L153) |
| function | `_questions` | `(bridges)` | — | [src](../../../core/services/agency_map.py#L162) |
| function | `_udled_synlighed` | `(kant)` | Synligheden udledes af kantens EGET bevis — den skrives ikke i hånden. | [src](../../../core/services/agency_map.py#L192) |
| function | `_dark_edges` | `()` | — | [src](../../../core/services/agency_map.py#L228) |
| function | `_med_udledt_synlighed` | `(kant)` | — | [src](../../../core/services/agency_map.py#L232) |
| function | `_dark_edge_kilder` | `()` | — | [src](../../../core/services/agency_map.py#L242) |
| function | `_cartographer_snapshot` | `()` | — | [src](../../../core/services/agency_map.py#L296) |
| function | `_next_moves` | `(cartographer)` | — | [src](../../../core/services/agency_map.py#L311) |
| function | `_repair_briefs` | `(limit=…)` | — | [src](../../../core/services/agency_map.py#L326) |
| function | `_theater_refactor_briefs` | `(limit=…)` | — | [src](../../../core/services/agency_map.py#L335) |
| function | `_system_cartographer_snapshot` | `()` | — | [src](../../../core/services/agency_map.py#L344) |

## `core/services/agent_approval_gate.py`
_Gate i agentens vaerktoejsdispatch: en handling der kraever godkendelse STOPPER foer den udfoeres_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `requires_approval` | `(tool_name)` | (kraever, risikoklasse). Fail-CLOSED for de faste navne; ukendt metadata -> ingen krav for resten. | [src](../../../core/services/agent_approval_gate.py#L33) |
| function | `_denied` | `(reason, approval_id=…)` | — | [src](../../../core/services/agent_approval_gate.py#L49) |
| function | `_parse` | `(tc)` | — | [src](../../../core/services/agent_approval_gate.py#L56) |
| function | `gate` | `(*, agent, run_id, tc, resume_approval_id=…)` | Se modulbeskrivelsen. ``resume_approval_id`` er den approval det parkerede kald venter paa. | [src](../../../core/services/agent_approval_gate.py#L68) |

## `core/services/agent_approval_notify.py`
_Hvem faar at vide at en approval venter, og hvornaar Jarvis vaekkes (agent-contract-v1 F4c, spec 8.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `wake_message` | `(approval)` | — | [src](../../../core/services/agent_approval_notify.py#L28) |
| function | `_stopped` | `(parent_run_id)` | — | [src](../../../core/services/agent_approval_notify.py#L34) |
| function | `_session_busy` | `(session_id)` | — | [src](../../../core/services/agent_approval_notify.py#L41) |
| function | `stage` | `(approval)` | Planlaeg vaekningen for en approval (idempotent: ét wake-task-id pr. approval). Returnerer task-id eller "". | [src](../../../core/services/agent_approval_notify.py#L50) |
| function | `on_requested` | `(approval)` | Kaldt naar en approval er oprettet/genfundet som ventende. Vaekker kun en INAKTIV, ikke-stoppet parent. | [src](../../../core/services/agent_approval_notify.py#L66) |
| function | `ensure_wakes` | `(*, now=…)` | Supervisor-tik: ventende approvals uden vaekning, ældre end GRACE, hvis session er inaktiv og som ikke er | [src](../../../core/services/agent_approval_notify.py#L73) |
| function | `cancel_wake` | `(approval, reason)` | Aflys en endnu ikke startet vaekning (approvalen er afgjort/annulleret). | [src](../../../core/services/agent_approval_notify.py#L91) |

## `core/services/agent_bridge.py`
_Agenter paa et klient-target: bro-invocations med ukendt udfald (agent-contract-v1 E, spec 8 + 8.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BridgeHalt` | `` | Et skrivende kald har uafgjort udfald: agentens loop STOPPER og runnet staar i ``outcome_unknown``. | [src](../../../core/services/agent_bridge.py#L60) |
| function | `idempotency_class` | `(tool)` | — | [src](../../../core/services/agent_bridge.py#L64) |
| function | `parse_target` | `(target)` | ('container','') eller ('client', id). ``ValueError`` for alt andet. | [src](../../../core/services/agent_bridge.py#L71) |
| function | `check_client_target` | `(*, owner_user_id, target, writes=…)` | Afvisning (``{"code","detail"}``) eller ``None`` hvis klienten kan tage opgaven NU. | [src](../../../core/services/agent_bridge.py#L83) |
| function | `allowed_tools_for_client` | `(owner_user_id, target, requested)` | Agentens vaerktoejer paa et klient-target: kun ``operator_*`` som klienten faktisk annoncerer. | [src](../../../core/services/agent_bridge.py#L115) |
| function | `_identity` | `(agent_id)` | Ejer, session, target og aktuelt run - fra DB. ``ContractError`` ved alt ufuldstaendigt. | [src](../../../core/services/agent_bridge.py#L127) |
| function | `target_of` | `(agent_id)` | ('container','') / ('client', id) for agentens aabne assignment; ('container','') for en legacy-agent. | [src](../../../core/services/agent_bridge.py#L143) |
| function | `_run` | `(coro, timeout_s)` | Koer en coroutine fra en vilkaarlig traad. Foretraekker serverens hovedloeb (hvor WS'en bor). | [src](../../../core/services/agent_bridge.py#L155) |
| function | `_invocation_id` | `(run_id, call_id)` | — | [src](../../../core/services/agent_bridge.py#L173) |
| function | `_clean_args` | `(arguments)` | Myndighed kommer fra serveren. Alt modellen har skrevet med foranstillet underscore fjernes. | [src](../../../core/services/agent_bridge.py#L179) |
| function | `_tool_error` | `(code, detail, **extra)` | — | [src](../../../core/services/agent_bridge.py#L184) |
| function | `invoke_tool_call` | `(*, agent, run_id, tc, dispatch=…, sleep=…)` | Udfoer ET agent-vaerktoejskald paa den bundne klient. ``None`` = agenten er ikke paa et klient-target | [src](../../../core/services/agent_bridge.py#L192) |
| function | `_drive` | `(*, ident, agent_id, row, client_id, tool, args, klass, dispatch, sleep)` | — | [src](../../../core/services/agent_bridge.py#L249) |
| function | `_loads` | `(text)` | — | [src](../../../core/services/agent_bridge.py#L292) |
| function | `_halt` | `(ident, row)` | Sæt run + assignment i ``outcome_unknown``/``waiting`` (som lease-reconcileren gør) og returner halten. | [src](../../../core/services/agent_bridge.py#L300) |
| function | `run_is_halted` | `(run_id)` | — | [src](../../../core/services/agent_bridge.py#L319) |
| function | `_settle_resolved` | `(row, verdict)` | Et uafgjort kald er nu afgjort: assignmentet afsluttes med de verificerede fakta. Intet genudfoeres - | [src](../../../core/services/agent_bridge.py#L327) |
| function | `apply_client_report` | `(*, owner_user_id, client_id, reports)` | Klientens egen status ved reconnect (kaldes af WS-ruten). | [src](../../../core/services/agent_bridge.py#L345) |
| function | `human_resolve` | `(*, invocation_id, owner_user_id, executed, actor_user_id)` | — | [src](../../../core/services/agent_bridge.py#L356) |
| function | `status_query_for` | `(owner_user_id, client_id)` | Invocation-id'er klienten skal oplyse status for ved reconnect. | [src](../../../core/services/agent_bridge.py#L364) |

## `core/services/agent_bridge_dispatch.py`
_Fastlaast bro-dispatch til EN bestemt klient (agent-contract-v1 E, spec 8)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_err` | `(code, **extra)` | — | [src](../../../core/services/agent_bridge_dispatch.py#L29) |
| function | `_local_conn` | `(user_id, client_id)` | — | [src](../../../core/services/agent_bridge_dispatch.py#L33) |
| function | `client_info` | `(user_id, client_id)` | Klientens annoncerede tilstand (lokalt eller via presence fra den anden proces), eller None. | [src](../../../core/services/agent_bridge_dispatch.py#L38) |
| function | `dispatch_pinned` | `(*, user_id, client_id, tool, args, timeout_s, extra=…, allow_cross_process=…)` | Send ``tool`` til netop ``client_id``. Aldrig failover til en anden klient. Rejser ikke. | [src](../../../core/services/agent_bridge_dispatch.py#L55) |
| function | `_forward` | `(*, user_id, client_id, tool, args, timeout_s, extra)` | Til den proces presence siger holder KLIENTEN. Ingen presence -> klienten er ikke forbundet. | [src](../../../core/services/agent_bridge_dispatch.py#L91) |

## `core/services/agent_contract_bridge.py`
_Binder spawn_agent_task til agent-contract-v1 (leverance A2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_owner_and_session` | `(context)` | — | [src](../../../core/services/agent_contract_bridge.py#L18) |
| function | `bind_new_agent` | `(*, agent_id, parent_agent_id, goal, persistent, context, budget_tokens=…, max_turns=…, result_contract=…, idempotency_key=…, request_digest=…, target=…, operation=…, expected_result=…)` | Opret agentens første assignment. Kaster aldrig: dispatch må ikke dø af bindingen. | [src](../../../core/services/agent_contract_bridge.py#L32) |
| function | `_write_assignment_artifact` | `(agent_id, owner, acc, goal, parent_agent_id, context, target)` | ``assignment.json`` for foerste run (§9). Bedste-indsats: et manglende artefakt | [src](../../../core/services/agent_contract_bridge.py#L64) |

## `core/services/agent_contract_service.py`
_agent-contract-v1: den ene motor bag dispatch og styring af agenter (leverance F1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `capability_enabled` | `()` | Fail-CLOSED: enhver laesefejl er `False`. Starter slukket (§12.4). | [src](../../../core/services/agent_contract_service.py#L45) |
| function | `set_capability` | `(enabled, *, role=…)` | Taend/sluk. At TAENDE er en ejerbeslutning; at slukke (kill switch) er altid tilladt. | [src](../../../core/services/agent_contract_service.py#L56) |
| function | `capability_status` | `()` | Faelles sandhed for admission, vaerktoejsudvalg, prompt og Desk. | [src](../../../core/services/agent_contract_service.py#L65) |
| function | `_err` | `(code, detail=…, phase=…)` | — | [src](../../../core/services/agent_contract_service.py#L75) |
| function | `_guard` | `(owner, session)` | — | [src](../../../core/services/agent_contract_service.py#L80) |
| function | `_owned_agent` | `(agent_id, owner)` | Agenten, men KUN hvis den tilhoerer ejeren. En andens agent er `None`. | [src](../../../core/services/agent_contract_service.py#L88) |
| function | `_run_in_background` | `(fn)` | Start agentens loekke uden at blokere kalderen. Kontekst foelger med. | [src](../../../core/services/agent_contract_service.py#L96) |
| function | `_start_execution` | `(agent_id)` | — | [src](../../../core/services/agent_contract_service.py#L109) |
| function | `_digest` | `(**parts)` | — | [src](../../../core/services/agent_contract_service.py#L116) |
| function | `_accept_view` | `(acc)` | — | [src](../../../core/services/agent_contract_service.py#L120) |
| function | `_capacity_error` | `(owner, parent)` | — | [src](../../../core/services/agent_contract_service.py#L126) |
| function | `dispatch_agent` | `(*, owner_user_id, origin_session_id, goal, parent_run_id=…, parent_agent_id=…, role=…, description=…, tool_policy=…, allowed_tools=…, target=…, budget_tokens=…, max_turns=…, expected_result=…, model=…, idempotency_key=…, writes=…, workspace=…, model_required=…)` | Accepter en afgraenset opgave til en ny agent og returner id'er STRAKS. | [src](../../../core/services/agent_contract_service.py#L138) |
| function | `followup_agent` | `(*, owner_user_id, origin_session_id, agent_id, goal, parent_run_id=…, budget_tokens=…, expected_result=…, idempotency_key=…, operation=…)` | Ny opgave til SAMME agent-id: nyt assignment, nyt run. Ikke til en lukket agent. | [src](../../../core/services/agent_contract_service.py#L256) |
| function | `send_message` | `(*, owner_user_id, origin_session_id, agent_id, content, sender=…, parent_run_id=…, idempotency_key=…)` | Information/styring til barnets aktuelle opgave, eller - er barnet ledigt - en | [src](../../../core/services/agent_contract_service.py#L303) |
| function | `interrupt_agent` | `(*, owner_user_id, origin_session_id, agent_id, note=…)` | Anmod om stop af den aktuelle tur. `stop_requested`, aldrig et lovet `cancelled`. | [src](../../../core/services/agent_contract_service.py#L337) |
| function | `close_agent` | `(*, owner_user_id, origin_session_id, agent_id)` | Graceful lukning: `closing` straks (afviser nye opgaver); `closed` naar eget run og | [src](../../../core/services/agent_contract_service.py#L354) |
| function | `settle_closing` | `(agent_id, owner_user_id)` | `closing` -> `closed`, naar agentens eget assignment og alle boerns er terminale. | [src](../../../core/services/agent_contract_service.py#L367) |
| function | `list_agents` | `(*, owner_user_id, origin_session_id=…, status=…, limit=…)` | Ejerens agenter (aldrig en andens): status, rolle, target, ubehandlede resultater. | [src](../../../core/services/agent_contract_service.py#L385) |
| function | `wait_agents` | `(*, owner_user_id, origin_session_id, assignment_ids, condition=…, timeout_seconds=…, wake_if_run_ends=…, parent_run_id=…, include_output=…, output_offset=…)` | Vent paa assignments. `timeout_seconds` blokerer kortvarigt (max 120 s); er betingelsen | [src](../../../core/services/agent_contract_service.py#L414) |
| function | `_attach_outputs` | `(view, owner_user_id, offset)` | Fuldt output (``final.txt``) for terminale assignments, via den ejer-kontrollerede | [src](../../../core/services/agent_contract_service.py#L464) |
| function | `supervise` | `()` | Supervisor-taek: udloeb approvals, genoptag parkerede agenter hvis approval er afgjort, overtag udloebne | [src](../../../core/services/agent_contract_service.py#L489) |
| function | `approval_view` | `(r)` | Det en klient/en model maa se: sikker visning + digest, ALDRIG de raa argumenter. | [src](../../../core/services/agent_contract_service.py#L522) |
| function | `list_approvals` | `(*, owner_user_id, status=…, origin_session_id=…)` | — | [src](../../../core/services/agent_contract_service.py#L530) |
| function | `decide_approval` | `(*, approval_id, decision, actor_user_id, actor_kind, digest, note=…)` | Afgoer en approval (kun et menneske, jf. db_agent_approvals.decide) og genoptager straks det parkerede | [src](../../../core/services/agent_contract_service.py#L540) |
| function | `request_integration` | `(*, owner_user_id, origin_session_id, assignment_id)` | Jarvis beder om integration af et kodeassignments arbejde. Opretter KUN en approval - han kan ikke | [src](../../../core/services/agent_contract_service.py#L570) |

## `core/services/agent_council.py`
_Raad og review-kaede paa agentmotoren (agent-contract-v1 F5, spec 5.1 / 7.1 / 11)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_digest` | `(topic, members)` | — | [src](../../../core/services/agent_council.py#L39) |
| function | `_validate` | `(members)` | — | [src](../../../core/services/agent_council.py#L43) |
| function | `_room_for` | `(owner, parent, n)` | — | [src](../../../core/services/agent_council.py#L58) |
| function | `convene` | `(*, owner_user_id, origin_session_id, topic, facts, members, parent_run_id=…, parent_agent_id=…, budget_tokens=…, idempotency_key=…, synthesis_role=…)` | Indkald et raad. Accepteres helt eller slet ikke; svaret er ids, ikke et resultat. | [src](../../../core/services/agent_council.py#L68) |
| function | `_abandon` | `(owner, session, cid, started)` | Intet halvt raad: afbryd de medlemmer der allerede er startet og luk raadet. | [src](../../../core/services/agent_council.py#L112) |
| function | `_view` | `(c, *, replayed=…)` | — | [src](../../../core/services/agent_council.py#L124) |
| function | `_outcomes` | `(owner, members)` | — | [src](../../../core/services/agent_council.py#L132) |
| function | `synthesis_goal` | `(topic, outcomes)` | — | [src](../../../core/services/agent_council.py#L151) |
| function | `advance` | `()` | Supervisor-taek: opret syntesen for raad hvis medlemmer alle er terminale, og luk raad hvis syntese er faerdig. | [src](../../../core/services/agent_council.py#L168) |
| function | `_wake_parent_on` | `(c, synthesis_assignment_id)` | Parenten vaekkes naar SYNTESEN er terminal (ikke ved hvert medlem). | [src](../../../core/services/agent_council.py#L204) |
| function | `_read` | `(owner, assignment_id, name, limit)` | — | [src](../../../core/services/agent_council.py#L220) |
| function | `dispatch_review` | `(*, owner_user_id, origin_session_id, builder_assignment_id, requirements, parent_run_id=…, budget_tokens=…, idempotency_key=…)` | Start en uafhaengig reviewer af en builders FAERDIGE arbejde. | [src](../../../core/services/agent_council.py#L229) |

## `core/services/agent_dispatch.py`
_Agent dispatch orchestrator for code mode (spec §19)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decide_dispatch` | `(task, *, force=…)` | Heuristik: dispatch agenter eller gør det inline? (§19.2) | [src](../../../core/services/agent_dispatch.py#L36) |
| function | `plan_dispatch` | `(task, *, executor_count=…)` | Byg rolle-planen for en dispatch (§19.3/§19.4). `executor_count` executors | [src](../../../core/services/agent_dispatch.py#L56) |
| function | `scan_skills_before_dispatch` | `(skill_contents)` | Kør skill_scanner på hver skill der vil eksekvere lokalt (§19.8). Blokerer | [src](../../../core/services/agent_dispatch.py#L74) |
| function | `dispatch_code_mode_task` | `(task, *, inline=…, executor_count=…, skill_contents=…, user_id=…, dry_run=…)` | Orchestrér en code-mode-opgave (§19.4). | [src](../../../core/services/agent_dispatch.py#L87) |

## `core/services/agent_integration.py`
_Integration af en kodeagents arbejde - foerste forbruger af approval-flowet (agent-contract-v1 F4d, spec 8.1/8.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_retained_worktree` | `(owner_user_id, assignment_id)` | — | [src](../../../core/services/agent_integration.py#L35) |
| function | `_snapshot` | `(wt)` | Hvad der staar i worktree'et NU: diff-hash + filer. Samme beregning ved anmodning og ved udfoerelse. | [src](../../../core/services/agent_integration.py#L44) |
| function | `request_integration` | `(*, owner_user_id, origin_session_id, assignment_id)` | Opret (eller genfind) approvalen. Kaster ``ContractError`` ved ukendt/ugyldigt worktree. | [src](../../../core/services/agent_integration.py#L53) |
| function | `_result_message` | `(approval, payload)` | Fortael parenten hvordan det gik, via den samme udbakke som agentresultater (ét svar pr. approval). | [src](../../../core/services/agent_integration.py#L67) |
| function | `execute_approved` | `(approval)` | Udfoer en GODKENDT integration. Bruger approvalen foerst (hoejst én gang). | [src](../../../core/services/agent_integration.py#L85) |
| function | `_merge` | `(wt, approval, args)` | — | [src](../../../core/services/agent_integration.py#L113) |
| function | `run_pending` | `()` | Supervisor-tik: godkendte, ubrugte integrationer (f.eks. besluttet lige foer en genstart) udfoeres. | [src](../../../core/services/agent_integration.py#L135) |

## `core/services/agent_loop_core.py`
_Agentens model-/vaerktoejsloekke som ren logik (agent-contract-v1 C6, spec 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ApprovalPending` | `` | Et vaerktoejskald kraever en menneskelig godkendelse: loekken PARKERER (checkpoint) i stedet for at | [src](../../../core/services/agent_loop_core.py#L28) |
| method | `ApprovalPending.__init__` | `(self, approval_id, tool_call_id=…)` | — | [src](../../../core/services/agent_loop_core.py#L32) |
| class | `LoopIO` | `` | — | [src](../../../core/services/agent_loop_core.py#L37) |
| method | `LoopIO.model` | `(self, *, messages, tools, requires_tools, provider, model)` | — | [src](../../../core/services/agent_loop_core.py#L38) |
| method | `LoopIO.tool` | `(self, tc)` | — | [src](../../../core/services/agent_loop_core.py#L41) |
| method | `LoopIO.after_tool` | `(self, tc, tool_out)` | — | [src](../../../core/services/agent_loop_core.py#L43) |
| method | `LoopIO.after_round` | `(self, rounds, tool_calls)` | — | [src](../../../core/services/agent_loop_core.py#L45) |
| function | `run_tool_loop` | `(io, *, prompt, tools_payload, requires_tools, provider, model, scout, max_rounds, synthesis_directive, resume=…)` | Koer loekken og returner raa tal + tekst. Kaster aldrig: en fejl bliver ``error_str``. | [src](../../../core/services/agent_loop_core.py#L48) |
| function | `_outcome` | `(final_text, total_input, total_output, total_cost, total_tool_calls, rounds, error_str, t0, parked)` | — | [src](../../../core/services/agent_loop_core.py#L151) |

## `core/services/agent_message_receipt.py`
_En besked til et barn maa ikke fryse foraelderens tur — Fase 6._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_completion_besked` | `(agent_id, resultat, vurdering=…)` | Den tekst der leveres naar baggrundsbarnet lander. | [src](../../../core/services/agent_message_receipt.py#L46) |
| function | `_foraelder_session` | `(agent_id)` | Den samtale der startede barnet, fra barnets egen kontekst — eller "". | [src](../../../core/services/agent_message_receipt.py#L65) |
| function | `_book_completion_wakeup` | `(agent_id, resultat, vurdering=…)` | LEVER baggrundsbarnets sene svar med det samme — uden 60-sekunders-gulvet. | [src](../../../core/services/agent_message_receipt.py#L80) |
| function | `send_med_kvittering` | `(*, agent_id, content, role=…, kind=…, execution_mode=…, taalmodighed_s=…)` | Send beskeden, vent kort, og giv enten svaret eller en kvittering. | [src](../../../core/services/agent_message_receipt.py#L151) |
| function | `_koer_med_taalmodighed` | `(agent_id, udfoer, taalmodighed_s, efterbehandling=…)` | Kør barnet i en tråd med forælderens kontekst; svar eller kvittér. | [src](../../../core/services/agent_message_receipt.py#L175) |
| function | `kvittering` | `(agent_id, *, taalmodighed_s=…)` | Hvad der er ACCEPTERET — ikke hvad der blev svaret. | [src](../../../core/services/agent_message_receipt.py#L250) |
| function | `spawn_med_kvittering` | `(*, taalmodighed_s=…, efterbehandling=…, **spawn_kwargs)` | Spawn en agent, vent kort, returner enten resultat eller kvittering. | [src](../../../core/services/agent_message_receipt.py#L269) |

## `core/services/agent_model_fitness.py`
_Er denne model egnet til agent-arbejde? Svaret bygger på MÅLINGER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_registret` | `()` | — | [src](../../../core/services/agent_model_fitness.py#L42) |
| function | `dom` | `(provider, model, *, poster=…)` | 'egnet' | 'uegnet' | 'ukendt'. Kaster aldrig. | [src](../../../core/services/agent_model_fitness.py#L50) |
| function | `_dom` | `(provider, model, poster)` | — | [src](../../../core/services/agent_model_fitness.py#L64) |
| function | `er_blokeret` | `(provider, model, *, rolle=…)` | True kun når vi har MÅLT at modellen ikke duer til værktøjs-arbejde. | [src](../../../core/services/agent_model_fitness.py#L83) |
| function | `bedste_egnede` | `(*, undtagen=…)` | Den højest scorende målte model der bestod `follows`. ('','') hvis ingen. | [src](../../../core/services/agent_model_fitness.py#L90) |
| function | `egnede_modeller` | `(*, undtagen=…, maks=…, kraever_vaerktoejer=…)` | Målte, egnede modeller — bedste først. Til rotation. | [src](../../../core/services/agent_model_fitness.py#L114) |

## `core/services/agent_model_policy.py`
_Modelvalg for agenter: premium-agentpulje -> ejerafhaengig fallback (agent-contract-v1 D, spec 7.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_capped` | `(rows)` | — | [src](../../../core/services/agent_model_policy.py#L37) |
| class | `ModelUnavailable` | `` | ``MODEL_UNAVAILABLE``: ingen tilladt rute. ``reasons`` er hver afvisning med aarsag. | [src](../../../core/services/agent_model_policy.py#L44) |
| method | `ModelUnavailable.__init__` | `(self, detail, reasons=…)` | — | [src](../../../core/services/agent_model_policy.py#L49) |
| class | `ProviderDenied` | `` | Ejeren maa ikke bruge denne provider (haandhaevet ved selve kaldet). | [src](../../../core/services/agent_model_policy.py#L54) |
| function | `is_platform_owner` | `(owner_user_id)` | Bjoern? Fail-closed: kan ejeren ikke afgoeres, er svaret nej. | [src](../../../core/services/agent_model_policy.py#L63) |
| function | `provider_denied_reason` | `(owner_user_id, provider)` | Tom streng = tilladt, ellers aarsagen. | [src](../../../core/services/agent_model_policy.py#L78) |
| function | `guard_call` | `(*, owner_user_id, provider, model=…)` | Kontrollen VED providerkaldet. Kaldes af hver modelanmodning for en bundet agent. | [src](../../../core/services/agent_model_policy.py#L85) |
| function | `_agent_candidates` | `(*, role, min_tokens, exclude, allow_paid)` | — | [src](../../../core/services/agent_model_policy.py#L96) |
| function | `_cost_class` | `(provider)` | — | [src](../../../core/services/agent_model_policy.py#L104) |
| function | `_evaluate` | `(provider, model, *, owner, role, needs_tools)` | (afvisningsaarsag eller '', fitness_ukendt). | [src](../../../core/services/agent_model_policy.py#L109) |
| function | `_split_requested` | `(requested)` | ('provider','model') for ``provider/model`` eller et bart modelnavn fra kataloget; ellers ('',''). | [src](../../../core/services/agent_model_policy.py#L132) |
| function | `_deepseek_budget_reason` | `()` | Tom = indenfor budget. Fail-closed: et ukendt budget er et afslag, ikke et ja. | [src](../../../core/services/agent_model_policy.py#L151) |
| function | `_estimate_cost` | `(provider, model, budget_tokens)` | — | [src](../../../core/services/agent_model_policy.py#L166) |
| function | `decide_route` | `(*, owner_user_id, requested_model=…, hard=…, role=…, needs_tools=…, min_tokens=…, budget_tokens=…, exclude=…)` | Faststil ruten FOER agenten oprettes. Rejser ``ModelUnavailable`` hvis ingen rute er tilladt. | [src](../../../core/services/agent_model_policy.py#L182) |

## `core/services/agent_model_router.py`
_Modelkald for en agent: genvalidering ved kaldet og failover i kandidatkaeden (agent-contract-v1 D)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ModelCallFailed` | `` | Modelkaldet svigtede (provider, kredit, circuit breaker). Bruges af strict-stien. | [src](../../../core/services/agent_model_router.py#L27) |
| method | `ModelCallFailed.__init__` | `(self, detail, *, provider=…, model=…)` | — | [src](../../../core/services/agent_model_router.py#L32) |
| function | `bound_owner` | `(agent_id)` | Agentens autentificerede ejer, eller '' for en legacy-agent. | [src](../../../core/services/agent_model_router.py#L37) |
| function | `_chain` | `(agent_id)` | — | [src](../../../core/services/agent_model_router.py#L45) |
| function | `_effectful` | `(agent)` | — | [src](../../../core/services/agent_model_router.py#L54) |
| function | `_switch` | `(agent_id, latest, cand, why)` | Gem skiftet: nyt route-forsoeg + agentens aktuelle provider/model. | [src](../../../core/services/agent_model_router.py#L58) |
| function | `call_agent_model` | `(*, agent, tools_executed=…, facade=…, **execute_kwargs)` | Kald agentens model. ``execute_kwargs`` er argumenterne til ``execute_with_role_or_fallback``. | [src](../../../core/services/agent_model_router.py#L81) |
| function | `_facade` | `()` | — | [src](../../../core/services/agent_model_router.py#L126) |

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

## `core/services/agent_parking.py`
_Parkering og genoptagelse af et barn der venter paa en approval (agent-contract-v1 F4b, spec 8.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_assignment_status` | `(*, assignment_id, status, only_from)` | Atomisk statusskifte inden for de aabne tilstande. ``False`` hvis den ikke stod i ``only_from``. | [src](../../../core/services/agent_parking.py#L26) |
| function | `park_run` | `(*, agent, run_id, result, thread_id=…)` | Gem checkpointen og sæt tilstandene. Returnerer agentens detaljeflade (som en almindelig tur). | [src](../../../core/services/agent_parking.py#L36) |
| function | `take_resume` | `(agent_id)` | Er agenten parkeret og afgjort? Tag checkpointen (atomisk) og returnér loekkens ``resume``-dict, eller | [src](../../../core/services/agent_parking.py#L65) |
| function | `resume_decided` | `(start)` | Genoptag alle parkerede agenter hvis approval er afgjort. ``start(agent_id)`` starter udfoerelsen | [src](../../../core/services/agent_parking.py#L88) |

## `core/services/agent_pool_router.py`
_Agent-pool router (spec §4 + §5.5). Tyndt lag over central_route så agenter_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `route_agent_task` | `(*, kind=…, min_tokens=…, quality_threshold=…, allow_paid=…, exclude=…, owner_user_id=…)` | Vælg (provider, model) for en agent-task via central_route. Aldrig tør. | [src](../../../core/services/agent_pool_router.py#L41) |
| function | `_load_task_scores` | `(provider, model)` | Nuværende task_scores for (provider, model) fra runtime-state. {} ved intet. | [src](../../../core/services/agent_pool_router.py#L114) |
| function | `_save_task_scores` | `(provider, model, scores)` | — | [src](../../../core/services/agent_pool_router.py#L125) |
| function | `update_task_score` | `(*, provider, model, kind, outcome_quality, lr=…)` | §4.4 kvalitets-læring: EMA-opdatér task_score for (model, kind) fra et | [src](../../../core/services/agent_pool_router.py#L133) |

## `core/services/agent_pool_surface.py`
_Agent-puljen — en LET liste man kan filtrere i._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rows` | `(sql, params=…)` | — | [src](../../../core/services/agent_pool_surface.py#L37) |
| function | `agent_liste` | `(*, status=…, rolle=…, soeg=…, limit=…, offset=…)` | Agenterne med deres koersels-tal. Ét opslag, filtrerbart, sideinddelt. | [src](../../../core/services/agent_pool_surface.py#L43) |
| function | `_varighed` | `(start, slut)` | Sekunder mellem to tidsstempler. 0 naar vi ikke kan regne det ud. | [src](../../../core/services/agent_pool_surface.py#L118) |
| function | `pool_opsummering` | `(timer=…)` | Puljens tilstand: hvor mange, hvilke roller, hvad koster de, hvor er graenserne. | [src](../../../core/services/agent_pool_surface.py#L132) |
| function | `seneste_arbejde` | `(limit=…)` | De nyeste koersler paa tvaers af agenter — «hvad sker der lige nu». | [src](../../../core/services/agent_pool_surface.py#L188) |

## `core/services/agent_prompt_layers.py`
_De tre versionsmaerkede promptlag for en agentrequest + snapshot foer foerste modelkald (C3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_prompt_tables` | `(conn)` | — | [src](../../../core/services/agent_prompt_layers.py#L37) |
| function | `_sha` | `(text)` | — | [src](../../../core/services/agent_prompt_layers.py#L58) |
| function | `_redact` | `(text)` | — | [src](../../../core/services/agent_prompt_layers.py#L62) |
| function | `build_layered_prompt` | `(*, agent, messages_text, execution_mode, extra_instruction=…)` | Byg de tre lag, eller ``None`` for en agent uden aabent assignment (legacy-vejen). | [src](../../../core/services/agent_prompt_layers.py#L71) |
| function | `snapshot_prompt` | `(*, run_id, agent, layers, tools_payload=…)` | Gem den effektive prompt + versioner + modelrute + vaerktoejsskema FOER foerste modelkald. | [src](../../../core/services/agent_prompt_layers.py#L119) |
| function | `get_prompt_snapshot` | `(*, owner_user_id, run_id)` | Ejer-kontrolleret opslag; en andens run er ``None``. | [src](../../../core/services/agent_prompt_layers.py#L145) |

