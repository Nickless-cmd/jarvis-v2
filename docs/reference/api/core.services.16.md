# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `load_overrides` | `()` | Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build). | [src](../../../core/services/prompt_observer.py#L66) |
| function | `section_enabled` | `(label, *, blacklisted, overrides)` | Skal denne prompt-sektion med? | [src](../../../core/services/prompt_observer.py#L94) |
| function | `observe_build` | `(*, lane, included, dropped_disabled, dropped_budget, dropped_error=…)` | Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget | [src](../../../core/services/prompt_observer.py#L104) |
| function | `observe_section_error` | `(label, error, *, lane=…)` | En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar). | [src](../../../core/services/prompt_observer.py#L130) |
| function | `set_section` | `(label, enabled)` | Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar. | [src](../../../core/services/prompt_observer.py#L144) |
| function | `list_overrides` | `()` | Read-only projektion af aktive overrides (til MC/debug). | [src](../../../core/services/prompt_observer.py#L152) |

## `core/services/prompt_relevance_backend.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_with_wall_clock_timeout` | `(fn, *, timeout)` | Run ``fn()`` in a daemon thread with a hard wall-clock deadline. | [src](../../../core/services/prompt_relevance_backend.py#L22) |
| class | `_BoundedLLMCall` | `` | Result of a bounded LLM call — neutral across Ollama / OllamaFreeAPI. | [src](../../../core/services/prompt_relevance_backend.py#L51) |
| function | `_call_bounded_relevance_llm` | `(prompt)` | Dispatch a bounded relevance/memory-selection prompt. | [src](../../../core/services/prompt_relevance_backend.py#L62) |
| function | `_call_openai_compat_relevance` | `(*, provider, prompt, model, timeout)` | Generic openai-compat relevance call (mistral, nim, openrouter, ...). | [src](../../../core/services/prompt_relevance_backend.py#L123) |
| function | `_call_opencode_relevance` | `(*, prompt, model, timeout)` | Call OpenCode Zen free models via the OpenAI-compatible cheap lane. | [src](../../../core/services/prompt_relevance_backend.py#L244) |
| function | `_call_ollamafreeapi_relevance` | `(*, prompt, model, timeout)` | OllamaFreeAPI silently drops its ``timeout`` kwarg, so we run the call | [src](../../../core/services/prompt_relevance_backend.py#L319) |
| function | `_call_local_ollama_relevance` | `(*, prompt)` | — | [src](../../../core/services/prompt_relevance_backend.py#L381) |
| class | `BoundedPromptRelevanceResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L445) |
| class | `BoundedPromptRelevanceAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L457) |
| class | `BoundedMemorySelectionResult` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L468) |
| class | `BoundedMemorySelectionAttempt` | `` | — | [src](../../../core/services/prompt_relevance_backend.py#L475) |
| function | `run_bounded_nl_prompt_relevance` | `(*, text, mode, compact, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L485) |
| function | `bounded_nl_prompt_relevance_smoke` | `(*, text, workspace_dir, mode=…, compact=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L556) |
| function | `run_bounded_nl_memory_entry_selection` | `(*, user_message, entries, max_lines, workspace_dir, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L581) |
| function | `load_visible_relevance_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L658) |
| function | `load_visible_memory_selection_prompt` | `(*, workspace_dir)` | — | [src](../../../core/services/prompt_relevance_backend.py#L672) |
| function | `_resolve_relevance_target` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L686) |
| function | `_selected_relevance_model` | `()` | — | [src](../../../core/services/prompt_relevance_backend.py#L706) |
| function | `_build_relevance_prompt` | `(*, instructions, text, mode, compact)` | — | [src](../../../core/services/prompt_relevance_backend.py#L712) |
| function | `_build_memory_selection_prompt` | `(*, instructions, user_message, entries, max_lines, mode=…)` | — | [src](../../../core/services/prompt_relevance_backend.py#L733) |
| function | `_parse_relevance_response` | `(text, mode)` | — | [src](../../../core/services/prompt_relevance_backend.py#L758) |
| function | `_parse_memory_selection_response` | `(text, *, entry_count, max_lines)` | — | [src](../../../core/services/prompt_relevance_backend.py#L795) |
| function | `_bounded_memory_candidates` | `(entries)` | — | [src](../../../core/services/prompt_relevance_backend.py#L846) |
| function | `_coerce_bool` | `(value)` | — | [src](../../../core/services/prompt_relevance_backend.py#L857) |

## `core/services/prompt_support_signals.py`
_Bounded inner-layer support signal builders._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_private_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L37) |
| function | `_growth_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L54) |
| function | `_self_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L72) |
| function | `_retained_memory_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L89) |
| function | `_reflection_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L109) |
| function | `_world_model_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L155) |
| function | `_goal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L201) |
| function | `_runtime_awareness_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L248) |
| function | `_development_focus_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L294) |
| function | `_temporal_support_signal_instruction` | `()` | — | [src](../../../core/services/prompt_support_signals.py#L341) |
| function | `_reflection_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L358) |
| function | `_world_model_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L369) |
| function | `_goal_direction_label` | `(goal_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L378) |
| function | `_runtime_awareness_direction_label` | `(signal_type)` | — | [src](../../../core/services/prompt_support_signals.py#L386) |
| function | `_development_focus_direction_label` | `(focus_type, canonical_key)` | — | [src](../../../core/services/prompt_support_signals.py#L399) |

## `core/services/prompt_variant_tracker.py`
_Prompt variant tracker — log per-variant performance for self-improvement._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `log_variant_outcome` | `(*, scope, variant_label, outcome_score, notes=…)` | Record a variant's outcome. scope is e.g. 'awareness.tier_recommendation'. | [src](../../../core/services/prompt_variant_tracker.py#L39) |
| function | `variant_performance` | `(*, scope=…, min_samples=…)` | Aggregate per-variant performance, optionally filtered by scope. | [src](../../../core/services/prompt_variant_tracker.py#L76) |
| function | `winning_variant` | `(scope, *, min_samples=…)` | Return the best-performing variant for a scope, or None if not enough data. | [src](../../../core/services/prompt_variant_tracker.py#L119) |
| function | `_exec_log_variant_outcome` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L128) |
| function | `_exec_variant_performance` | `(args)` | — | [src](../../../core/services/prompt_variant_tracker.py#L137) |

## `core/services/proposal_classifier.py`
_Proposal classifier — detects action impulses in thought fragments and scores destructiveness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_fragment` | `(fragment)` | Classify a thought fragment for action impulses. | [src](../../../core/services/proposal_classifier.py#L59) |

## `core/services/proprioception_metrics.py`
_Proprioception Metrics — process-level body sense._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_psutil` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L32) |
| function | `_current_snapshot` | `()` | Sample current process stats. | [src](../../../core/services/proprioception_metrics.py#L40) |
| function | `_measure_self_latency_ms` | `()` | Measure trivial self-dispatch as a crude latency proxy. | [src](../../../core/services/proprioception_metrics.py#L70) |
| function | `_emit` | `(kind, payload)` | — | [src](../../../core/services/proprioception_metrics.py#L83) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/proprioception_metrics.py#L91) |
| function | `recent_snapshots` | `(*, limit=…)` | — | [src](../../../core/services/proprioception_metrics.py#L134) |
| function | `build_proprioception_metrics_surface` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L138) |
| function | `_surface_summary` | `(current, rss_trend)` | — | [src](../../../core/services/proprioception_metrics.py#L171) |
| function | `build_proprioception_metrics_prompt_section` | `()` | Only surfaces when something is actively worth noticing. | [src](../../../core/services/proprioception_metrics.py#L187) |
| function | `reset_proprioception_metrics` | `()` | — | [src](../../../core/services/proprioception_metrics.py#L207) |

## `core/services/prose_tool_calls.py`
_Parser for prosa-emitterede tool-kald (cluster: tool-leak-fix 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_match_json_object` | `(s, start)` | s[start] skal være '{'. Returnér (objekt-streng, slut-index) via brace-matching | [src](../../../core/services/prose_tool_calls.py#L26) |
| function | `extract_prose_tool_calls` | `(text, valid_tool_names)` | Find `[navn]: {json}`-prosa-kald hvor navn er et kendt tool og args er et | [src](../../../core/services/prose_tool_calls.py#L55) |

## `core/services/prospective_memory.py`
_Prospective memory — plant seeds for the future, harvest when context arrives._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/prospective_memory.py#L44) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/prospective_memory.py#L48) |
| function | `_ensure_table` | `()` | Create prospective_seeds table if missing. Idempotent. | [src](../../../core/services/prospective_memory.py#L61) |
| function | `_row_to_seed` | `(row)` | — | [src](../../../core/services/prospective_memory.py#L92) |
| function | `plant_seed` | `(*, title, summary=…, activate_at=…, activate_on_event=…, activate_on_context=…, expires_at=…, relevance_score=…, linked_goal=…, linked_project=…, workspace_id=…)` | Plant a forward-looking intention. Returns the new seed dict. | [src](../../../core/services/prospective_memory.py#L104) |
| function | `list_seeds` | `(*, status=…, limit=…, workspace_id=…)` | Return seeds, optionally filtered by status. Newest first. | [src](../../../core/services/prospective_memory.py#L167) |
| function | `summarize_seeds` | `(*, workspace_id=…)` | Status counts for dashboard / observability. | [src](../../../core/services/prospective_memory.py#L194) |
| function | `fulfill_seed` | `(*, seed_id, outcome_note=…, workspace_id=…)` | Mark a seed as fulfilled (Jarvis acted on it). | [src](../../../core/services/prospective_memory.py#L218) |
| function | `ignore_seed` | `(*, seed_id, reason=…, workspace_id=…)` | Mark a seed as ignored (Jarvis chose not to act on a triggered seed). | [src](../../../core/services/prospective_memory.py#L250) |
| function | `heartbeat_tick` | `(*, event_type=…, context_tokens=…, now_ts=…, workspace_id=…)` | One tick of the prospective-memory engine. Call from heartbeat or | [src](../../../core/services/prospective_memory.py#L274) |
| function | `_set_status` | `(seed_id, workspace_id, status, *, triggered_at_now=…)` | — | [src](../../../core/services/prospective_memory.py#L348) |
| function | `build_prospective_memory_surface` | `(*, limit=…, workspace_id=…)` | Surface prospective seeds without triggering or mutating them. | [src](../../../core/services/prospective_memory.py#L377) |

## `core/services/provider_autodiscovery.py`
_Provider auto-discovery (spec Fase C). Dagligt scan af providers' /models,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_list_remote_models` | `(provider)` | Modeller providerens /models-endpoint rapporterer. [] ved fejl. | [src](../../../core/services/provider_autodiscovery.py#L18) |
| function | `_known_models` | `()` | Modeller allerede i provider_router.json (uanset lane). | [src](../../../core/services/provider_autodiscovery.py#L28) |
| function | `_stage_pending` | `(provider, model)` | Skriv (provider, model) til pending_models-staging, status='pending'. | [src](../../../core/services/provider_autodiscovery.py#L38) |
| function | `_add_to_router` | `(provider, model)` | Faktisk optagelse i routbar pool. Kaldes KUN af promote_pending efter gates. | [src](../../../core/services/provider_autodiscovery.py#L56) |
| function | `_configured_providers` | `()` | Alle providers i provider_router.json (til daglig re-scan). [] ved fejl. | [src](../../../core/services/provider_autodiscovery.py#L69) |
| function | `tick_provider_autodiscovery_daemon` | `()` | Fase C daemon-tick: dagligt scan af alle providers' /models → nye modeller til | [src](../../../core/services/provider_autodiscovery.py#L80) |
| function | `discover_provider` | `(provider)` | Scan provider, stage nye modeller. Returnér de nye (staged). Auto-adder ALDRIG. | [src](../../../core/services/provider_autodiscovery.py#L100) |
| function | `_smoke_ok` | `(provider, model)` | Svarer modellen på et minimalt kald? | [src](../../../core/services/provider_autodiscovery.py#L109) |
| function | `_is_free` | `(provider, model)` | Konservativ gratis-verifikation. Default False (governed — hellere afvise). | [src](../../../core/services/provider_autodiscovery.py#L125) |
| function | `_score_model` | `(provider, model)` | Seed kvalitets-score (§4.4). Grov til at komme i gang. | [src](../../../core/services/provider_autodiscovery.py#L130) |
| function | `promote_pending` | `(provider, model, *, min_score=…)` | Gated promotion: kræver smoke + gratis + score ≥ tærskel. Kun da optages | [src](../../../core/services/provider_autodiscovery.py#L135) |

## `core/services/provider_circuit_breaker.py`
_Provider circuit breaker — skip primaries that have been failing recently._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(provider, model)` | — | [src](../../../core/services/provider_circuit_breaker.py#L39) |
| function | `_prune_old_failures` | `(failures, now)` | — | [src](../../../core/services/provider_circuit_breaker.py#L43) |
| function | `record_failure` | `(provider, model)` | Record a primary-call failure. Returns updated state for this key. | [src](../../../core/services/provider_circuit_breaker.py#L49) |
| function | `record_success` | `(provider, model)` | Clear failure tracking on success — provider seems healthy again. | [src](../../../core/services/provider_circuit_breaker.py#L67) |
| function | `should_skip` | `(provider, model)` | True when breaker is open for this (provider, model). | [src](../../../core/services/provider_circuit_breaker.py#L77) |
| function | `breaker_state` | `()` | Observability snapshot — returns open breakers + recent failure counts. | [src](../../../core/services/provider_circuit_breaker.py#L95) |
| function | `reset_all` | `()` | Test/admin helper — clear all state. | [src](../../../core/services/provider_circuit_breaker.py#L128) |
| class | `_PPState` | `` | Per-provider breaker-state (consecutive-i-træk-state-maskine). | [src](../../../core/services/provider_circuit_breaker.py#L160) |
| method | `_PPState.__init__` | `(self, threshold, cooldown_s, window_s)` | — | [src](../../../core/services/provider_circuit_breaker.py#L168) |
| class | `_PerProviderBreaker` | `` | Proces-lokal per-provider-keyed breaker. Trådsikker, self-safe. | [src](../../../core/services/provider_circuit_breaker.py#L179) |
| method | `_PerProviderBreaker.__init__` | `(self, *, threshold=…, cooldown_s=…, window_s=…)` | — | [src](../../../core/services/provider_circuit_breaker.py#L189) |
| method | `_PerProviderBreaker._key` | `(provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L204) |
| method | `_PerProviderBreaker.configure` | `(self, provider_id, *, threshold=…, cooldown_s=…, window_s=…)` | Per-provider-tærskler (ofa/arko bevarer deres historiske tal). | [src](../../../core/services/provider_circuit_breaker.py#L207) |
| method | `_PerProviderBreaker._state` | `(self, pid)` | — | [src](../../../core/services/provider_circuit_breaker.py#L235) |
| method | `_PerProviderBreaker.record_failure` | `(self, provider_id, *, now=…)` | Fejl → opdatér state. True hvis breakeren NETOP åbnede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L247) |
| method | `_PerProviderBreaker.record_success` | `(self, provider_id)` | Success → luk (reset). True hvis den netop lukkede (frisk kant). | [src](../../../core/services/provider_circuit_breaker.py#L273) |
| method | `_PerProviderBreaker.is_open` | `(self, provider_id, *, now=…)` | OPEN nu (→ kort-slut)? Cooldown udløbet → half-open (slip én probe → | [src](../../../core/services/provider_circuit_breaker.py#L288) |
| method | `_PerProviderBreaker.snapshot` | `(self, provider_id)` | — | [src](../../../core/services/provider_circuit_breaker.py#L306) |
| method | `_PerProviderBreaker.reset_all` | `(self)` | — | [src](../../../core/services/provider_circuit_breaker.py#L323) |
| function | `_observe_pp` | `(nerve, provider_id, **data)` | Observér en per-provider breaker-kant til Centralen (cluster="stream"). | [src](../../../core/services/provider_circuit_breaker.py#L332) |
| function | `pp_configure` | `(provider_id, **kw)` | Sæt per-provider-tærskler på den delte breaker (ofa/arko-løft). | [src](../../../core/services/provider_circuit_breaker.py#L346) |
| function | `pp_record_failure` | `(provider_id)` | Registrér en provider-fejl på den DELTE per-provider breaker + observér | [src](../../../core/services/provider_circuit_breaker.py#L351) |
| function | `pp_record_success` | `(provider_id)` | Registrér success på den delte per-provider breaker + observér close-kant. | [src](../../../core/services/provider_circuit_breaker.py#L366) |
| function | `pp_is_open` | `(provider_id)` | Er ``provider_id``'s delte breaker OPEN lige nu? (Fail-open.) | [src](../../../core/services/provider_circuit_breaker.py#L374) |
| function | `pp_snapshot` | `(provider_id)` | Debug/observe-snapshot af den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L379) |
| function | `pp_reset_all` | `()` | Test/admin: nulstil HELE den delte per-provider breaker. | [src](../../../core/services/provider_circuit_breaker.py#L384) |

## `core/services/provider_health_check.py`
_Provider health check — periodic ping to detect outages early._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ping_host` | `(url)` | HTTP GET with short timeout. Returns reachable=True/False + latency_ms. | [src](../../../core/services/provider_health_check.py#L48) |
| function | `health_check_all_providers` | `()` | Ping every cheap-lane provider once. Returns per-provider status. | [src](../../../core/services/provider_health_check.py#L66) |
| function | `_cheap_dry_providers` | `()` | Providers i cheap-lane-cooldown (tør/quota-blokeret) — fra runtime-state. Self-safe. | [src](../../../core/services/provider_health_check.py#L115) |
| function | `_model_drift` | `()` | Model-drift: en provider der FØR havde modeller men nu har 0 (model udfaset/omdøbt — den | [src](../../../core/services/provider_health_check.py#L135) |
| function | `_spread_load_proactively` | `(reports, unreachable)` | Daemon-load-spredning (Jarvis-spec): sæt PROAKTIVT en kort cooldown på nede providers, så | [src](../../../core/services/provider_health_check.py#L170) |
| function | `observe_and_flag` | `()` | Kadence-entry (Jarvis-spec 2026-06-23): ping + model-drift + cheap-dry → observe + FLAG | [src](../../../core/services/provider_health_check.py#L211) |
| function | `build_provider_health_surface` | `()` | Read-only provider-helbreds-surface til Jarvis Mind / terminal: ÉT kald → ping + tør + | [src](../../../core/services/provider_health_check.py#L260) |
| function | `latest_health_snapshot` | `()` | Read most-recent stored snapshot. | [src](../../../core/services/provider_health_check.py#L283) |
| function | `health_section` | `()` | Awareness section listing currently unreachable providers. | [src](../../../core/services/provider_health_check.py#L295) |
| function | `_exec_run_health_check` | `(args)` | — | [src](../../../core/services/provider_health_check.py#L315) |
| function | `_exec_get_health_snapshot` | `(args)` | — | [src](../../../core/services/provider_health_check.py#L319) |

## `core/services/provider_retry_policy.py`
_Provider retry policy — exponential backoff for transient failures._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_transient` | `(exc)` | — | [src](../../../core/services/provider_retry_policy.py#L46) |
| function | `retry_with_backoff` | `(fn, *, max_retries=…, base_delay=…, max_delay=…, only_transient=…, label=…)` | Run fn() with exponential backoff. Re-raises last exception on failure. | [src](../../../core/services/provider_retry_policy.py#L53) |
| function | `_exec_test_retry` | `(args)` | Manual test handle — verify retry behaviour. Not for production use. | [src](../../../core/services/provider_retry_policy.py#L97) |

## `core/services/provider_self_heal.py`
_Provider selvhelbredelse (spec Fase C). To sikre auto-handlinger:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_notify_bjorn` | `(message)` | Eskalér via eksisterende notifikations-sti (Discord/ntfy). | [src](../../../core/services/provider_self_heal.py#L22) |
| function | `_remove_from_router` | `(provider, model)` | Fjern (provider, model) fra provider_router.json. Self-safe. | [src](../../../core/services/provider_self_heal.py#L31) |
| function | `_observe_central` | `(payload)` | — | [src](../../../core/services/provider_self_heal.py#L46) |
| function | `check_and_heal` | `(*, down_providers)` | 3+ providers nede samtidig → eskalér til Bjørn. Returnér True hvis eskaleret. | [src](../../../core/services/provider_self_heal.py#L54) |
| function | `_current_down_providers` | `()` | Providers der lige nu er uopnåelige (proaktiv ping). Self-safe → []. | [src](../../../core/services/provider_self_heal.py#L66) |
| function | `tick_provider_self_heal_daemon` | `()` | Fase C daemon-tick: 60min self-heal. Samler nede providers og eskalerer til Bjørn | [src](../../../core/services/provider_self_heal.py#L76) |
| function | `handle_model_drift` | `(*, provider, model, status_code)` | 404 på en model = model-drift → fjern auto fra pool + log. Returnér True hvis fjernet. | [src](../../../core/services/provider_self_heal.py#L91) |

## `core/services/push_dispatcher.py`
_Beslutter HVORNAAR og HVEM der skal pushes. Bygger paa run_event_log-suppression._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fcm_send` | `(token, data)` | — | [src](../../../core/services/push_dispatcher.py#L12) |
| function | `_owner_of_run` | `(run_id)` | — | [src](../../../core/services/push_dispatcher.py#L17) |
| function | `_push_to_user` | `(user_id, data)` | — | [src](../../../core/services/push_dispatcher.py#L24) |
| function | `_route_or_blast` | `(user_id, data, kind)` | Flag ON → intelligent device-routing; OFF → gammel FCM-blast (bagudkompat). | [src](../../../core/services/push_dispatcher.py#L35) |
| function | `_last_assistant_preview` | `(session_id, *, width=…)` | Sidste assistant-beskeds tekst (trunkeret) til notifikations-preview. "" hvis ingen. | [src](../../../core/services/push_dispatcher.py#L48) |
| function | `_dispatch_run_done` | `(run_id)` | — | [src](../../../core/services/push_dispatcher.py#L66) |
| function | `on_run_done` | `(run_id)` | Kaldes fra detached_run finally. Planlaegger suppression-tjek efter grace. | [src](../../../core/services/push_dispatcher.py#L96) |
| function | `send_companion_push` | `(user_id, message, title=…)` | Proaktiv push til brugerens companion-enheder (mobil + desktop) via | [src](../../../core/services/push_dispatcher.py#L104) |
| function | `on_initiative` | `(user_id, text)` | — | [src](../../../core/services/push_dispatcher.py#L117) |
| function | `on_reminder` | `(user_id, text)` | — | [src](../../../core/services/push_dispatcher.py#L123) |

## `core/services/pushback.py`
_Pushback — three prompt-level mechanisms that give Jarvis a real voice_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_emit_pushback_telemetry` | `(section, *, triggered, reason=…, **fields)` | Log pushback section generation to eventbus for observability. | [src](../../../core/services/pushback.py#L34) |
| function | `_ambiguity_score` | `(message)` | Heuristic 0-1 ambiguity. Returns (score, reasons). | [src](../../../core/services/pushback.py#L67) |
| function | `_conflict_with_decisions` | `(message)` | Check if the request appears to contradict an active behavioral decision. | [src](../../../core/services/pushback.py#L113) |
| function | `doubt_signal_section` | `(user_message)` | Render doubt as a prompt section. None when doubt is low. | [src](../../../core/services/pushback.py#L146) |
| function | `disagreement_invite_section` | `()` | Always-on reminder that pushback is welcome. Static text. | [src](../../../core/services/pushback.py#L184) |
| function | `_affective_pressure` | `(snapshot)` | Map the emotional snapshot to the feeling most likely to drive pushback. | [src](../../../core/services/pushback.py#L217) |
| function | `_request_risk_evidence` | `(user_message)` | — | [src](../../../core/services/pushback.py#L244) |
| function | `affective_pushback_section` | `(user_message)` | Render feeling-driven pushback as bounded prompt guidance. | [src](../../../core/services/pushback.py#L257) |
| function | `_is_high_stakes` | `(user_message, reasoning_tier)` | — | [src](../../../core/services/pushback.py#L330) |
| function | `direction_confirm_section` | `(*, user_message, reasoning_tier)` | Inject a 'plan-first, confirm-before-tools' section for high-stakes | [src](../../../core/services/pushback.py#L337) |

## `core/services/quota_store.py`
_Kvote-regnskab pr. bruger/mode med daglig nulstilling (spec §21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today` | `()` | — | [src](../../../core/services/quota_store.py#L32) |
| function | `set_user_quota` | `(user_id, tier)` | Sæt en brugers eksplicitte tier (autoritativt i user_db). Owner kan give | [src](../../../core/services/quota_store.py#L36) |
| function | `get_tier` | `(user_id)` | Brugerens tier. user_db-tier (nyt autoritativt felt) vinder; ellers eksplicit | [src](../../../core/services/quota_store.py#L43) |
| function | `_limit_for` | `(kind, tier)` | — | [src](../../../core/services/quota_store.py#L72) |
| function | `_db_key` | `(user_id, kind)` | — | [src](../../../core/services/quota_store.py#L76) |
| function | `_get_used` | `(user_id, kind)` | — | [src](../../../core/services/quota_store.py#L80) |
| function | `check_quota` | `(user_id, kind)` | Status uden at forbruge. {allowed, tier, used, limit (None=ubegrænset), | [src](../../../core/services/quota_store.py#L89) |
| function | `consume_quota` | `(user_id, kind, amount=…)` | Forbrug `amount` af kvoten hvis muligt. Returnerer status (som check_quota) | [src](../../../core/services/quota_store.py#L106) |

## `core/services/r2_5_blocking_gate.py`
_R2.5 — conditional blocking gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_live_thresholds` | `()` | Settings-backed tærskler (config uden deploy, 2026-06-22); modul-konstanterne | [src](../../../core/services/r2_5_blocking_gate.py#L57) |
| function | `_heed_rate_24h` | `()` | — | [src](../../../core/services/r2_5_blocking_gate.py#L76) |
| function | `should_block_for_verification` | `(*, reasoning_tier)` | Decide whether to inject a 'stop and look back' block. | [src](../../../core/services/r2_5_blocking_gate.py#L88) |
| function | `r2_5_block_section` | `(reasoning_tier)` | Render the block as a high-priority awareness section, or None. | [src](../../../core/services/r2_5_blocking_gate.py#L218) |

## `core/services/read_before_write_guard.py`
_Read-before-write guard — prevents overwrite of existing files without prior read._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cache_key` | `(session_id, abs_path)` | — | [src](../../../core/services/read_before_write_guard.py#L56) |
| function | `record_read` | `(path, session_id=…)` | Record that a file has been read in this session. | [src](../../../core/services/read_before_write_guard.py#L60) |
| function | `_was_read` | `(abs_path, session_id)` | True if `abs_path` was read in this session within the TTL window. | [src](../../../core/services/read_before_write_guard.py#L78) |
| function | `is_protected` | `(path)` | True if the path's basename is in the protected set. | [src](../../../core/services/read_before_write_guard.py#L96) |
| function | `check_read_before_write` | `(path, session_id=…)` | Check whether write_file should be allowed for this path. | [src](../../../core/services/read_before_write_guard.py#L105) |
| function | `_normalize_path` | `(p, *, base=…)` | Best-effort resolve of a path token (may be ~/, relative, ./). | [src](../../../core/services/read_before_write_guard.py#L175) |
| function | `check_bash_command_safe` | `(command, *, session_id=…, cwd=…)` | Sniff a bash command for protected-file overwrites without prior read. | [src](../../../core/services/read_before_write_guard.py#L186) |
| function | `clear_session` | `(session_id=…)` | Clear all recent-read entries for a session in shared_cache. | [src](../../../core/services/read_before_write_guard.py#L288) |
| function | `get_session_reads` | `(session_id=…)` | Return the set of paths read in this session (for debugging). | [src](../../../core/services/read_before_write_guard.py#L297) |
| function | `build_read_before_write_guard_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/read_before_write_guard.py#L324) |
| function | `_emit_read_before_write_guard_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/read_before_write_guard.py#L336) |
| function | `_normalize_operator_path` | `(path)` | Light normalization for cross-OS path consistency. | [src](../../../core/services/read_before_write_guard.py#L365) |
| function | `_operator_cache_key` | `(session_id, norm_path)` | — | [src](../../../core/services/read_before_write_guard.py#L378) |
| function | `record_operator_read` | `(path, session_id=…)` | Note that the operator side has read this path. Best-effort. | [src](../../../core/services/read_before_write_guard.py#L382) |
| function | `_operator_was_read` | `(norm_path, session_id)` | — | [src](../../../core/services/read_before_write_guard.py#L398) |
| function | `check_operator_read_before_write` | `(path, session_id=…, file_exists=…)` | Block operator_write_file / operator_edit_file on existing files | [src](../../../core/services/read_before_write_guard.py#L412) |
| function | `_session_edits_key` | `(session_id)` | — | [src](../../../core/services/read_before_write_guard.py#L468) |
| function | `record_operator_edit` | `(path, session_id=…, kind=…)` | Record that the operator side mutated this file. kind is 'edit' or 'write'. | [src](../../../core/services/read_before_write_guard.py#L472) |
| function | `get_session_edit_summary` | `(session_id=…)` | Return the running tally for this session. Empty dict if nothing yet. | [src](../../../core/services/read_before_write_guard.py#L505) |

## `core/services/reasoning_classifier.py`
_Reasoning classifier — router that picks fast / reasoning / deep tier._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_score_patterns` | `(text, patterns)` | — | [src](../../../core/services/reasoning_classifier.py#L65) |
| function | `classify_reasoning_tier` | `(message, *, task_hint=…)` | Pick reasoning tier for a user message (or task description). | [src](../../../core/services/reasoning_classifier.py#L75) |
| function | `reasoning_tier_section` | `(message)` | Format tier verdict as a prompt-awareness section. None for fast tier | [src](../../../core/services/reasoning_classifier.py#L210) |
| function | `_exec_reasoning_classify` | `(args)` | — | [src](../../../core/services/reasoning_classifier.py#L227) |
| function | `build_reasoning_classifier_surface` | `()` | — | [src](../../../core/services/reasoning_classifier.py#L275) |
| function | `_emit_tier_event` | `(tier, score)` | — | [src](../../../core/services/reasoning_classifier.py#L284) |

## `core/services/reasoning_detectors.py`
_Reasoning detectors for the reasoning-interceptor._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_downgrade_cognitive` | `(v, *, gate)` | Re-stamp a gate's verdict for the reasoning stage: keep GREEN/YELLOW, but a COGNITIVE RED | [src](../../../core/services/reasoning_detectors.py#L16) |
| function | `fact_gate_on_reasoning` | `(reasoning_text, ctx)` | fact_gate re-applied to reasoning. A number/status claim with NO backing tool-call in this | [src](../../../core/services/reasoning_detectors.py#L26) |
| function | `decision_gate_on_reasoning` | `(reasoning_text, ctx)` | decision_gate (commit cluster) re-applied to reasoning. Grounding = the active-decisions | [src](../../../core/services/reasoning_detectors.py#L43) |
| function | `veto_on_reasoning` | `(reasoning_text, ctx)` | veto_gate (commit cluster) re-applied to reasoning. Grounding = the veto gate's own evidence. | [src](../../../core/services/reasoning_detectors.py#L55) |
| function | `verification_on_reasoning` | `(reasoning_text, ctx)` | proactivity/verification gate re-applied. Grounding = the run's verification state (the gate | [src](../../../core/services/reasoning_detectors.py#L67) |
| function | `cross_user_share_on_reasoning` | `(reasoning_text, ctx)` | privacy/cross_user_share gate re-applied to reasoning. SECURITY — keeps RED (a leak forming | [src](../../../core/services/reasoning_detectors.py#L78) |
| function | `standing_orders_on_reasoning` | `(reasoning_text, ctx)` | Flag when the reasoning enters a risk class an active standing order governs. Grounding = | [src](../../../core/services/reasoning_detectors.py#L92) |
| function | `_drift_signal` | `(ctx)` | INDEPENDENT drift signal 0..1 from the Central's OWN affect/valence nerves + an | [src](../../../core/services/reasoning_detectors.py#L112) |
| function | `drift_on_reasoning` | `(reasoning_text, ctx)` | Affective drift (overconfidence). Grounding = the Central's own affect nerves + claim streak | [src](../../../core/services/reasoning_detectors.py#L132) |
| function | `tone_on_reasoning` | `(reasoning_text, ctx)` | Epistemic tone — a guess stated as fact. ANCHORED (invariant 3): runs ONLY if a truth/drift | [src](../../../core/services/reasoning_detectors.py#L150) |

## `core/services/reasoning_escalation.py`
_Reasoning escalation — compose tier + gate signals into a council recommendation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_tier` | `(message)` | — | [src](../../../core/services/reasoning_escalation.py#L39) |
| function | `_safe_gate` | `()` | — | [src](../../../core/services/reasoning_escalation.py#L48) |
| function | `_recommend_path` | `(tier, failed, unverified, signals)` | Pick the escalation path that fits the situation. | [src](../../../core/services/reasoning_escalation.py#L63) |
| function | `evaluate_escalation` | `(message=…)` | Compose tier + gate into an escalation recommendation. | [src](../../../core/services/reasoning_escalation.py#L112) |
| function | `escalation_section` | `(message=…)` | Format escalation recommendation as a prompt-awareness section, or None. | [src](../../../core/services/reasoning_escalation.py#L168) |
| function | `_exec_recommend_escalation` | `(args)` | — | [src](../../../core/services/reasoning_escalation.py#L193) |
| function | `build_reasoning_escalation_surface` | `()` | — | [src](../../../core/services/reasoning_escalation.py#L223) |
| function | `_emit_escalation_event` | `(path, tier)` | — | [src](../../../core/services/reasoning_escalation.py#L232) |

## `core/services/reasoning_interceptor.py`
_Reasoning interceptor orchestrator. intercept_round() runs between a round's reasoning and the_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InterceptOutcome` | `` | — | [src](../../../core/services/reasoning_interceptor.py#L15) |
| function | `_is_active` | `(grade)` | Active only if the per-grade kill-switch is EXPLICITLY flipped ON. DEFAULT OFF (shadow) — | [src](../../../core/services/reasoning_interceptor.py#L23) |
| function | `should_hold_tool_call` | `(outcome)` | True only for an ACTIVE RED outcome — the seam then holds the pending tool-call (via the | [src](../../../core/services/reasoning_interceptor.py#L44) |
| function | `_run_detectors` | `(ctx)` | Run the tripped cluster-gate adapters + standing-orders; return the WORST Verdict (GREEN if | [src](../../../core/services/reasoning_interceptor.py#L50) |
| function | `_observe` | `(outcome, *, run_id, round_num)` | Egress-free metadata-only pulse to the Central (never the reasoning text). Self-safe. | [src](../../../core/services/reasoning_interceptor.py#L92) |
| function | `build_reasoning_interceptor_surface` | `()` | Central-CLI view: recent interceptor verdicts. Self-safe, read-only. Returns static shape | [src](../../../core/services/reasoning_interceptor.py#L105) |
| function | `intercept_round_async` | `(*, run_id, round_num, reasoning_text, tool_calls_this_run, ctx=…, budget_ms=…)` | Async wrapper (invariant 4 — async/keepalive): runs the sync intercept in a thread with a | [src](../../../core/services/reasoning_interceptor.py#L131) |
| function | `intercept_round` | `(*, run_id, round_num, reasoning_text, tool_calls_this_run, ctx=…)` | — | [src](../../../core/services/reasoning_interceptor.py#L152) |

## `core/services/reasoning_prefilter.py`
_Deterministic pre-filter (interceptor invariant 5): cheap regex/heuristics over reasoning text →_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `prefilter` | `(reasoning_text, *, ctx=…, other_user_ids=…)` | Return the risk classes present in `reasoning_text`. Self-safe (never raises). | [src](../../../core/services/reasoning_prefilter.py#L15) |

## `core/services/reasoning_store.py`
_Reasoning Store — Phase 1 of Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/reasoning_store.py#L32) |
| function | `_ensure_table` | `(conn)` | Idempotent table creation. | [src](../../../core/services/reasoning_store.py#L36) |
| function | `_cosine_similarity` | `(a, b)` | Cosine similarity between two equal-length vectors. | [src](../../../core/services/reasoning_store.py#L64) |
| function | `_parse_embedding` | `(raw)` | Safely parse embedding JSON, return empty list on failure. | [src](../../../core/services/reasoning_store.py#L76) |
| function | `capture_conclusion` | `(*, source, conclusion_text, context=…, confidence=…, embedding=…, source_record_id=…, metadata=…, emit_event=…, dedup_key=…)` | Store a reasoning conclusion and return its conclusion_id. | [src](../../../core/services/reasoning_store.py#L90) |
| function | `recall_reasoning` | `(*, query_text=…, query_embedding=…, source_filter=…, min_confidence=…, limit=…, days_back=…)` | Retrieve stored reasoning conclusions, ranked by relevance. | [src](../../../core/services/reasoning_store.py#L169) |
| function | `get_recent_conclusions` | `(*, source=…, limit=…, days_back=…)` | Quick access to recent conclusions, no embedding scoring. | [src](../../../core/services/reasoning_store.py#L269) |
| function | `is_enabled` | `()` | Check the killswitch setting. | [src](../../../core/services/reasoning_store.py#L283) |
| function | `set_enabled` | `(value)` | Set killswitch — toggle reasoning store on/off without restart. | [src](../../../core/services/reasoning_store.py#L289) |
| function | `compact_stale` | `(days=…, min_confidence=…)` | Delete stale low-confidence conclusions. Returns count removed. | [src](../../../core/services/reasoning_store.py#L295) |
| function | `compute_embedding` | `(text)` | Compute embedding vector for semantic search. | [src](../../../core/services/reasoning_store.py#L317) |

## `core/services/reboot_awareness_daemon.py`
_Reboot Awareness Daemon — proprioception: "I feel when I restart"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L35) |
| function | `_load` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L39) |
| function | `_save` | `(data)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L53) |
| function | `_update_last_seen` | `(pid)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L65) |
| function | `_graceful_shutdown_marker` | `()` | Called via signal handler. Writes a clean shutdown marker. | [src](../../../core/services/reboot_awareness_daemon.py#L72) |
| function | `_signal_handler` | `(signum, _frame)` | Write graceful-shutdown marker then re-raise to default handler. | [src](../../../core/services/reboot_awareness_daemon.py#L84) |
| function | `_install_signal_handlers` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L101) |
| function | `detect_reboot` | `()` | Compare previous last_seen to now; emit an event if this is a fresh boot. | [src](../../../core/services/reboot_awareness_daemon.py#L112) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook: first call triggers detect_reboot(), thereafter | [src](../../../core/services/reboot_awareness_daemon.py#L193) |
| function | `get_last_boot_event` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L202) |
| function | `build_reboot_awareness_surface` | `()` | — | [src](../../../core/services/reboot_awareness_daemon.py#L206) |
| function | `_surface_summary` | `(event, uptime)` | — | [src](../../../core/services/reboot_awareness_daemon.py#L229) |
| function | `build_reboot_awareness_prompt_section` | `()` | Announce recent reboot once; stays silent after first ~10 min. | [src](../../../core/services/reboot_awareness_daemon.py#L252) |

## `core/services/recall_scheduler.py`
_core/services/recall_scheduler.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `background_recall_enabled` | `()` | Er baggrunds-recall aktiv? Default True. Self-safe → True (den nye, hurtige sti). | [src](../../../core/services/recall_scheduler.py#L38) |
| function | `_build_emotional_state` | `()` | Byg emotionel baseline til scoringen (samme kilde som cognitive_state_assembly). | [src](../../../core/services/recall_scheduler.py#L48) |
| function | `_run_recall` | `(message_text, emotional_state)` | — | [src](../../../core/services/recall_scheduler.py#L61) |
| function | `trigger_background_recall` | `(user_message, emotional_state=…)` | Kør ``recall_for_message`` i en baggrundstråd, kædet på den rigtige besked. | [src](../../../core/services/recall_scheduler.py#L73) |

## `core/services/recurrence_loop_daemon.py`
_Recurrence Loop — feeds inner voice output back as context input (Experiment 1: IIT/Φ)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_recurrence_loop_daemon` | `()` | Run one recurrence iteration. Returns dict with generated/reason/stability. | [src](../../../core/services/recurrence_loop_daemon.py#L23) |
| function | `build_recurrence_surface` | `()` | MC surface for recurrence loop experiment. | [src](../../../core/services/recurrence_loop_daemon.py#L76) |
| function | `_call_recurrence_llm` | `(content)` | Call cheap lane (Groq/etc.) first, Ollama fallback. Timeout 15s. | [src](../../../core/services/recurrence_loop_daemon.py#L117) |
| function | `_extract_keywords` | `(text)` | Extract meaningful keywords from text (words >= 4 chars, deduped, max 20). | [src](../../../core/services/recurrence_loop_daemon.py#L177) |
| function | `_jaccard_similarity` | `(a, b)` | Jaccard similarity between two keyword sets. Returns 1.0 if both empty. | [src](../../../core/services/recurrence_loop_daemon.py#L183) |

## `core/services/recurring_tasks.py`
_Recurring tasks service — lets Jarvis schedule repeating reminders/actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/recurring_tasks.py#L26) |
| function | `set_channel` | `(task_id, channel)` | Sæt leverings-kanal på en recurring task. Returnerer True hvis opdateret. | [src](../../../core/services/recurring_tasks.py#L61) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/services/recurring_tasks.py#L77) |
| function | `_scope` | `()` | Bruger-id til streng per-bruger-scope (#154). "" = ingen scope (fallback). | [src](../../../core/services/recurring_tasks.py#L94) |
| function | `_create` | `(*, task_id, focus, source, interval_minutes, next_fire_at, now)` | — | [src](../../../core/services/recurring_tasks.py#L100) |
| function | `_get_due` | `(now_iso)` | — | [src](../../../core/services/recurring_tasks.py#L113) |
| function | `_advance` | `(task_id, interval_minutes, now)` | — | [src](../../../core/services/recurring_tasks.py#L122) |
| function | `_cancel` | `(task_id, now_iso)` | — | [src](../../../core/services/recurring_tasks.py#L137) |
| function | `_list` | `(limit=…)` | — | [src](../../../core/services/recurring_tasks.py#L157) |
| function | `_get_one` | `(task_id)` | — | [src](../../../core/services/recurring_tasks.py#L173) |
| function | `create_recurring_task` | `(*, focus, interval_minutes, source=…, delay_minutes=…)` | Schedule a recurring task. Returns task info dict. | [src](../../../core/services/recurring_tasks.py#L190) |
| function | `cancel_recurring_task` | `(task_id)` | — | [src](../../../core/services/recurring_tasks.py#L221) |
| function | `list_recurring_tasks` | `()` | — | [src](../../../core/services/recurring_tasks.py#L229) |
| function | `get_recurring_tasks_state` | `()` | Summary for observability / Mission Control. | [src](../../../core/services/recurring_tasks.py#L234) |
| function | `_fire_due` | `()` | — | [src](../../../core/services/recurring_tasks.py#L249) |
| function | `_enter_owner_context` | `(user_id)` | Sæt workspace-konteksten til task-ejeren for affyringen. Returnerer en | [src](../../../core/services/recurring_tasks.py#L293) |
| function | `_exit_owner_context` | `(token)` | — | [src](../../../core/services/recurring_tasks.py#L307) |
| function | `_poller_loop` | `()` | — | [src](../../../core/services/recurring_tasks.py#L317) |
| function | `start_recurring_tasks_service` | `()` | — | [src](../../../core/services/recurring_tasks.py#L336) |
| function | `stop_recurring_tasks_service` | `()` | — | [src](../../../core/services/recurring_tasks.py#L345) |

## `core/services/recursion_guard.py`
_Recursion guard for autonomous agent dispatch._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tunable_int` | `(key, default)` | Read an int threshold from runtime-state; fall back to ``default``. | [src](../../../core/services/recursion_guard.py#L43) |
| function | `_tunable_float` | `(key, default)` | — | [src](../../../core/services/recursion_guard.py#L53) |
| function | `can_spawn` | `(current_depth, max_depth=…)` | True while a spawn chain still has depth budget. | [src](../../../core/services/recursion_guard.py#L63) |
| function | `fanout_allowed` | `(requested, max_fanout=…)` | True when a single dispatch's requested child count is within budget. | [src](../../../core/services/recursion_guard.py#L77) |
| function | `_load_entries` | `()` | — | [src](../../../core/services/recursion_guard.py#L91) |
| function | `_save_entries` | `(entries)` | — | [src](../../../core/services/recursion_guard.py#L107) |
| function | `_fresh_entries` | `(entries, now_ts, ttl)` | Drop entries older than ``ttl`` — reclaims slots left by crashed runs. | [src](../../../core/services/recursion_guard.py#L114) |
| function | `try_enter` | `(now_ts=…)` | Claim a concurrency slot. | [src](../../../core/services/recursion_guard.py#L119) |
| function | `exit` | `(now_ts=…)` | Release one concurrency slot (also reclaims stale entries). | [src](../../../core/services/recursion_guard.py#L142) |
| function | `active_count` | `(now_ts=…)` | Number of live (non-stale) concurrency slots currently held. | [src](../../../core/services/recursion_guard.py#L154) |

## `core/services/reflection_cycle_daemon.py`
_Reflection cycle daemon — pure experience without action, every 10 minutes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/reflection_cycle_daemon.py#L19) |
| function | `tick_reflection_cycle_daemon` | `(snapshot, *, skip_event_gate=…)` | Generate a pure experience reflection if cadence allows. | [src](../../../core/services/reflection_cycle_daemon.py#L27) |
| function | `_generate_reflection` | `(snapshot)` | — | [src](../../../core/services/reflection_cycle_daemon.py#L71) |
| function | `_store_reflection` | `(reflection)` | — | [src](../../../core/services/reflection_cycle_daemon.py#L107) |
| function | `get_latest_reflection` | `()` | — | [src](../../../core/services/reflection_cycle_daemon.py#L139) |
| function | `build_reflection_surface` | `()` | — | [src](../../../core/services/reflection_cycle_daemon.py#L143) |

## `core/services/reflection_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_reflection_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/reflection_signal_tracking.py#L24) |
| function | `refresh_runtime_reflection_signal_statuses` | `()` | — | [src](../../../core/services/reflection_signal_tracking.py#L53) |
| function | `build_runtime_reflection_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/reflection_signal_tracking.py#L92) |
| function | `_extract_reflection_candidates` | `()` | — | [src](../../../core/services/reflection_signal_tracking.py#L118) |
| function | `_history_item_from_signal` | `(item)` | — | [src](../../../core/services/reflection_signal_tracking.py#L219) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/reflection_signal_tracking.py#L238) |
| function | `_persist_reflection_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/reflection_signal_tracking.py#L271) |
| function | `_domain_key_from_focus` | `(canonical_key)` | — | [src](../../../core/services/reflection_signal_tracking.py#L355) |
| function | `_domain_key_from_critic` | `(canonical_key)` | — | [src](../../../core/services/reflection_signal_tracking.py#L366) |
| function | `_domain_key_from_self_model` | `(canonical_key)` | — | [src](../../../core/services/reflection_signal_tracking.py#L378) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/reflection_signal_tracking.py#L387) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/reflection_signal_tracking.py#L391) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/reflection_signal_tracking.py#L399) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/reflection_signal_tracking.py#L413) |
| function | `_history_transition_label` | `(*, signal_type, status)` | — | [src](../../../core/services/reflection_signal_tracking.py#L420) |

## `core/services/reflection_to_plan.py`
_Reflection → Plan — konvertér reflection/tanke til eksekverbar plan._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/reflection_to_plan.py#L41) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/reflection_to_plan.py#L45) |
| function | `_build_planning_prompt` | `(reflection_text, source_kind, available_tools)` | — | [src](../../../core/services/reflection_to_plan.py#L74) |
| function | `_extract_plan_json` | `(raw)` | — | [src](../../../core/services/reflection_to_plan.py#L104) |
| function | `_available_tools` | `()` | Get list of tool names from simple_tools registry. | [src](../../../core/services/reflection_to_plan.py#L130) |
| function | `create_reflective_plan` | `(*, reflection_text, source_kind=…, source_id=…, min_length=…)` | Generate a plan from a reflection using LLM. | [src](../../../core/services/reflection_to_plan.py#L139) |
| function | `accept_reflective_plan` | `(*, plan_id)` | Mark plan as accepted. Returns plan dict or None if not found. | [src](../../../core/services/reflection_to_plan.py#L237) |
| function | `complete_reflective_plan` | `(*, plan_id, outcome_note=…)` | — | [src](../../../core/services/reflection_to_plan.py#L265) |
| function | `reject_reflective_plan` | `(*, plan_id, reason=…)` | — | [src](../../../core/services/reflection_to_plan.py#L292) |
| function | `_row_to_plan` | `(row)` | — | [src](../../../core/services/reflection_to_plan.py#L311) |
| function | `list_reflective_plans` | `(*, status=…, limit=…)` | — | [src](../../../core/services/reflection_to_plan.py#L320) |
| function | `build_reflection_to_plan_surface` | `()` | — | [src](../../../core/services/reflection_to_plan.py#L340) |
| function | `plan_from_inner_voice_thought` | `(*, thought, voice_id=…)` | Convenience: convert inner_voice thought to plan if substantive enough. | [src](../../../core/services/reflection_to_plan.py#L361) |
| function | `plan_from_blind_spot` | `(*, description, blind_spot_id=…)` | — | [src](../../../core/services/reflection_to_plan.py#L371) |
| function | `plan_from_self_review` | `(*, lessons, review_id=…)` | — | [src](../../../core/services/reflection_to_plan.py#L380) |

## `core/services/reflective_critic_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_reflective_critics_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/reflective_critic_tracking.py#L27) |
| function | `refresh_runtime_reflective_critic_statuses` | `()` | — | [src](../../../core/services/reflective_critic_tracking.py#L69) |
| function | `build_runtime_reflective_critic_surface` | `(*, limit=…)` | — | [src](../../../core/services/reflective_critic_tracking.py#L99) |
| function | `_extract_critic_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/reflective_critic_tracking.py#L122) |
| function | `_repeated_correction_mismatch` | `(message, *, session_id)` | — | [src](../../../core/services/reflective_critic_tracking.py#L145) |
| function | `_matching_active_focus` | `(message)` | — | [src](../../../core/services/reflective_critic_tracking.py#L184) |
| function | `_persist_critics` | `(*, critics, session_id, run_id)` | — | [src](../../../core/services/reflective_critic_tracking.py#L195) |
| function | `_apply_resolution_signals` | `(*, user_message)` | — | [src](../../../core/services/reflective_critic_tracking.py#L271) |
| function | `_detect_resolution_context` | `(lower, active_critics)` | Detect which critic context the resolution message refers to. | [src](../../../core/services/reflective_critic_tracking.py#L339) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/reflective_critic_tracking.py#L363) |
| function | `_message_matches_focus_key` | `(canonical_key, text)` | — | [src](../../../core/services/reflective_critic_tracking.py#L391) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/reflective_critic_tracking.py#L403) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/reflective_critic_tracking.py#L410) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/reflective_critic_tracking.py#L414) |

## `core/services/regret_engine.py`
_Regret Engine — systematisk tracking af fortrydelser og læring._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/regret_engine.py#L28) |
| function | `_clamp` | `(value, default=…, lo=…, hi=…)` | — | [src](../../../core/services/regret_engine.py#L32) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/regret_engine.py#L44) |
| function | `compute_regret_level` | `(*, expected_outcome, actual_outcome, confidence_before=…, confidence_after=…)` | Compute regret level ∈ [0, 1] from outcome mismatch + confidence drop. | [src](../../../core/services/regret_engine.py#L78) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/services/regret_engine.py#L108) |
| function | `open_or_update_regret` | `(*, decision_id, context=…, expected_outcome, actual_outcome, lesson=…, confidence_before=…, confidence_after=…, linked_run_id=…, linked_session_id=…, linked_incident_id=…)` | Open a new regret, or update an existing open one for this decision_id. | [src](../../../core/services/regret_engine.py#L119) |
| function | `resolve_regret` | `(*, regret_id, actual_outcome=…, lesson=…, confidence_after=…)` | Mark a regret as resolved. Optionally update final outcome + lesson. | [src](../../../core/services/regret_engine.py#L244) |
| function | `list_regrets` | `(*, status=…, limit=…)` | — | [src](../../../core/services/regret_engine.py#L291) |
| function | `summarize_regrets` | `()` | — | [src](../../../core/services/regret_engine.py#L314) |
| function | `reconcile_open_regrets` | `(*, close_below=…)` | Auto-resolve regrets whose level has decayed below the threshold. | [src](../../../core/services/regret_engine.py#L347) |
| function | `build_regret_engine_surface` | `()` | MC surface — returns current regret state for Mission Control. | [src](../../../core/services/regret_engine.py#L388) |

## `core/services/regulation_homeostasis_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_regulation_homeostasis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L23) |
| function | `refresh_runtime_regulation_homeostasis_signal_statuses` | `()` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L55) |
| function | `build_runtime_regulation_homeostasis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L86) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L128) |
| function | `_persist_regulation_homeostasis_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L259) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L328) |
| function | `_latest_initiative_tension_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L338) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L350) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L362) |
| function | `_latest_inner_visible_support_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L374) |
| function | `_derive_regulation_pressure` | `(*, state_pressure, tension_type, contradiction_pressure)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L386) |
| function | `_derive_regulation_watchfulness` | `(*, contradiction_status, contradiction_pressure, visible_watchfulness)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L397) |
| function | `_derive_regulation_pacing` | `(*, pressure, watchfulness, curiosity_pull)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L410) |
| function | `_derive_regulation_state` | `(*, state_tone, pressure, watchfulness, pacing)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L425) |
| function | `_bounded_regulation_summary` | `(*, focus, regulation_state, regulation_pressure, regulation_watchfulness, regulation_pacing)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L441) |
| function | `_grounding_mode` | `(*, has_tension, has_curiosity, has_executive_contradiction, has_inner_visible_support)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L456) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L475) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L500) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L522) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L526) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L536) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L548) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L560) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L568) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L582) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L594) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/regulation_homeostasis_signal_tracking.py#L602) |

## `core/services/relation_continuity_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_relation_continuity_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L23) |
| function | `refresh_runtime_relation_continuity_signal_statuses` | `()` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L46) |
| function | `build_runtime_relation_continuity_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L77) |
| function | `_extract_relation_continuity_candidates` | `(*, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L112) |
| function | `_persist_relation_continuity_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L225) |
| function | `_latest_user_understanding_signal` | `(*, run_id)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L294) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L304) |
| function | `_latest_chronicle_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L316) |
| function | `_latest_regulation_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L328) |
| function | `_derive_continuity_watchfulness` | `(*, relation_watchfulness, regulation_watchfulness)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L340) |
| function | `_derive_continuity_weight` | `(*, chronicle_weight, relation_confidence)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L346) |
| function | `_derive_continuity_state` | `(*, relation_state, continuity_alignment, continuity_watchfulness, continuity_weight)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L354) |
| function | `_continuity_summary` | `(*, focus, continuity_state, continuity_alignment, continuity_watchfulness, continuity_weight)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L370) |
| function | `_grounding_mode` | `(*, has_chronicle_brief, has_chronicle_signal, has_regulation)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L385) |
| function | `_with_runtime_view` | `(record, signal)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L396) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L418) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L434) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L438) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L448) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L460) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L472) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L484) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L492) |
| function | `_source_anchor_from_support_summary` | `(value)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L500) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/relation_continuity_signal_tracking.py#L514) |

