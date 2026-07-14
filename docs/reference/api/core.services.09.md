# `core.services.09` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/dispatch_guards.py`
_core/services/dispatch_guards.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rs_get` | `(key, default)` | — | [src](../../../core/services/dispatch_guards.py#L71) |
| function | `_rs_set` | `(key, value)` | — | [src](../../../core/services/dispatch_guards.py#L81) |
| function | `_as_float` | `(v, default)` | — | [src](../../../core/services/dispatch_guards.py#L90) |
| function | `_as_int` | `(v, default)` | — | [src](../../../core/services/dispatch_guards.py#L97) |
| function | `_idem_ttl_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L107) |
| function | `try_consume` | `(key, *, now=…, ttl_s=…)` | Markér `key` forbrugt ATOMISK. True første gang, False hvis allerede forbrugt | [src](../../../core/services/dispatch_guards.py#L111) |
| function | `synthesize_timeout_envelope` | `(agent_id, deadline_ms)` | Byg en LARMENDE TIMEOUT-envelope for en dispatch der aldrig meldte tilbage. | [src](../../../core/services/dispatch_guards.py#L152) |
| function | `register_deadline` | `(dispatch_id, deadline_ts)` | Registrér hvornår en dispatch SENEST skal have rapporteret. Durabel. | [src](../../../core/services/dispatch_guards.py#L163) |
| function | `overdue` | `(now_ts=…)` | Returnér dispatch_ids hvis deadline er passeret ved now_ts (frisk = ikke med). | [src](../../../core/services/dispatch_guards.py#L175) |
| function | `clear_deadline` | `(dispatch_id)` | Fjern en deadline (kaldes når dispatch rapporterer tilbage). Durabel, self-safe. | [src](../../../core/services/dispatch_guards.py#L191) |
| function | `_breaker_threshold` | `()` | — | [src](../../../core/services/dispatch_guards.py#L205) |
| function | `_breaker_window_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L210) |
| function | `_breaker_cooldown_s` | `()` | — | [src](../../../core/services/dispatch_guards.py#L215) |
| function | `_breaker_state` | `(lane)` | — | [src](../../../core/services/dispatch_guards.py#L220) |
| function | `record_outcome` | `(lane, ok, *, now=…)` | Registrér udfaldet af en dispatch på `lane`. En succes nulstiller den | [src](../../../core/services/dispatch_guards.py#L227) |
| function | `is_tripped` | `(lane, *, now=…)` | True hvis breakeren for `lane` er åben (blokér dispatch). Auto-resetter efter | [src](../../../core/services/dispatch_guards.py#L253) |
| function | `_budget_max_count` | `()` | — | [src](../../../core/services/dispatch_guards.py#L275) |
| function | `_budget_max_cost` | `()` | — | [src](../../../core/services/dispatch_guards.py#L280) |
| function | `_budget_events` | `(lane, now)` | Hent lane-forbrug som liste af [ts, cost] beskåret til det rullende 24h-vindue. | [src](../../../core/services/dispatch_guards.py#L285) |
| function | `budget_allows` | `(lane, cost_usd, *, now=…)` | HÅRD backstop FØR LLM'en fyrer: False hvis dette dispatch ville bryde ENTEN | [src](../../../core/services/dispatch_guards.py#L303) |
| function | `record_spend` | `(lane, cost_usd, *, now=…)` | Registrér ét dispatch + dets cost på `lane`. Beskærer samtidig vinduet til 24h. | [src](../../../core/services/dispatch_guards.py#L329) |

## `core/services/dispatch_status.py`
_Typed dispatch-status enum for the dispatch-redesign._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DispatchStatus` | `` | String constants for the six terminal dispatch outcomes. | [src](../../../core/services/dispatch_status.py#L13) |
| method | `DispatchStatus.all` | `(cls)` | Return the set of all six known statuses. | [src](../../../core/services/dispatch_status.py#L24) |
| function | `is_failure` | `(status)` | True for failed/timeout/blocked. Unknown status -> False. | [src](../../../core/services/dispatch_status.py#L46) |
| function | `is_terminal` | `(status)` | True for any of the six known statuses. Unknown status -> False. | [src](../../../core/services/dispatch_status.py#L51) |

## `core/services/doc_repair_agent.py`
_Doc repair agent (spec 2026-07-10 Del 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_allowed_doc_path` | `(rel_or_abs)` | True KUN hvis stien oploeser til noget UNDER <repo>/docs/. Afviser traversal, | [src](../../../core/services/doc_repair_agent.py#L23) |
| function | `find_stale_docs` | `()` | Konsumér docs_drift_watchdog-signalet → liste af {path, generator} for docs | [src](../../../core/services/doc_repair_agent.py#L41) |
| function | `_run_generator` | `(name)` | Kør en kendt deterministisk doc-generator og returnér det nye indhold. | [src](../../../core/services/doc_repair_agent.py#L58) |
| function | `repair_doc` | `(target, *, live)` | Repair én doc. Skriver KUN under docs/ (invariant), KUN naar live=True og | [src](../../../core/services/doc_repair_agent.py#L69) |
| function | `run_doc_repair_tick` | `()` | Cadence-indgang, kørt gennem central().decide (Centralen er aktoeren). | [src](../../../core/services/doc_repair_agent.py#L104) |
| function | `build_doc_repair_surface` | `()` | Read-surface til jc raw /central/doc-repair. Side-effect-fri. | [src](../../../core/services/doc_repair_agent.py#L138) |

## `core/services/docs_drift_watchdog.py`
_SP5 docs-drift watchdog — surface docs/drift_report.json to the Central as a docs:drift nerve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_report` | `(report_path=…)` | — | [src](../../../core/services/docs_drift_watchdog.py#L19) |
| function | `_report_stale` | `(report_path=…, repo=…)` | True if the drift audit itself is old — the report is missing, or its own | [src](../../../core/services/docs_drift_watchdog.py#L29) |
| function | `check_docs_drift` | `(report_path=…, repo=…)` | — | [src](../../../core/services/docs_drift_watchdog.py#L49) |
| function | `observe_docs_drift` | `()` | Emit the docs:drift signal to Central (timeseries + observe trace). Self-safe. | [src](../../../core/services/docs_drift_watchdog.py#L69) |
| function | `build_docs_drift_surface` | `()` | Read-only surface for /central/docs-drift. Never throws. | [src](../../../core/services/docs_drift_watchdog.py#L87) |
| function | `_run_producer_tick` | `(**_)` | — | [src](../../../core/services/docs_drift_watchdog.py#L101) |
| function | `register_docs_drift_producer` | `()` | Register the docs-drift observation as a ~5-min cadence producer. | [src](../../../core/services/docs_drift_watchdog.py#L106) |

## `core/services/dream_adoption_candidate_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_adoption_candidates_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L32) |
| function | `refresh_runtime_dream_adoption_candidate_statuses` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L54) |
| function | `build_runtime_dream_adoption_candidate_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L85) |
| function | `_extract_dream_adoption_candidates` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L114) |
| function | `_persist_dream_adoption_candidates` | `(*, candidates, session_id, run_id)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L186) |
| function | `_build_adoption_snapshots` | `()` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L260) |
| function | `_with_runtime_view` | `(item, candidate)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L308) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L319) |
| function | `_build_candidate_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L332) |
| function | `_build_candidate_status` | `(*, candidate_type, hypothesis_status, cadence_state)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L348) |
| function | `_build_adoption_confidence` | `(*, candidate_type, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L356) |
| function | `_build_adoption_reason` | `(*, candidate_type, hypothesis_type, adoption_confidence)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L364) |
| function | `_build_adoption_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L372) |
| function | `_build_status_reason` | `(*, candidate_type)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L389) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L397) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L406) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L411) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L416) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L421) |
| function | `_hypothesis_type_from_candidate_key` | `(canonical_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L426) |
| function | `_adoption_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L431) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L440) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L445) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_adoption_candidate_tracking.py#L455) |

## `core/services/dream_articulation.py`
_Bounded dream articulation light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_dream_articulation` | `(*, trigger=…, last_visible_at=…)` | Run one bounded dream-articulation pass. | [src](../../../core/services/dream_articulation.py#L23) |
| function | `build_dream_articulation_from_inputs` | `(*, idle_consolidation, inner_voice_state, emergent_surface, witness_surface, loop_runtime, embodied_state, goal_surface=…, relation_surface=…, autonomy_surface=…, now=…)` | — | [src](../../../core/services/dream_articulation.py#L165) |
| function | `build_dream_articulation_surface` | `()` | — | [src](../../../core/services/dream_articulation.py#L332) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/dream_articulation.py#L364) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/dream_articulation.py#L397) |
| function | `_latest_dream_articulation_signal` | `()` | Return the latest dream hypothesis signal. | [src](../../../core/services/dream_articulation.py#L423) |
| function | `_classify_candidate_state` | `(*, idle_consolidation, emergent_surface, witness_surface, loop_runtime)` | — | [src](../../../core/services/dream_articulation.py#L444) |
| function | `_build_anchor` | `(*, idle_consolidation, witness_summary, emergent_summary, loop_summary)` | — | [src](../../../core/services/dream_articulation.py#L461) |
| function | `_build_signal_type` | `(*, candidate_state, loop_summary)` | — | [src](../../../core/services/dream_articulation.py#L480) |
| function | `_title_suffix` | `(anchor)` | — | [src](../../../core/services/dream_articulation.py#L485) |
| function | `_build_summary` | `(*, candidate_state, source_inputs, body)` | — | [src](../../../core/services/dream_articulation.py#L489) |
| function | `_build_rationale` | `(*, consolidation, voice_result, witness_summary, emergent_summary)` | — | [src](../../../core/services/dream_articulation.py#L502) |
| function | `_build_support_summary` | `(*, source_inputs, candidate_state)` | — | [src](../../../core/services/dream_articulation.py#L522) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/dream_articulation.py#L534) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/dream_articulation.py#L561) |

## `core/services/dream_bias_engine.py`
_Dream bias engine — Lag 2 distillation + bias state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/dream_bias_engine.py#L57) |
| function | `_now` | `()` | — | [src](../../../core/services/dream_bias_engine.py#L64) |
| function | `_validate_dream_output` | `(raw)` | Sanitize LLM output — drop unknown keys, clamp values, force guards. | [src](../../../core/services/dream_bias_engine.py#L70) |
| function | `accumulate_bias` | `(prior, new, intensity)` | Add new bias values to prior, multiplied by intensity, clamped ±1.0. | [src](../../../core/services/dream_bias_engine.py#L119) |
| function | `get_active_dream_bias` | `(*, workspace_id=…)` | Read active bias, honoring kill-switch + TTL. | [src](../../../core/services/dream_bias_engine.py#L140) |
| function | `format_dream_bias_for_heartbeat` | `(*, workspace_id=…)` | Render bias as a structured awareness-section block. | [src](../../../core/services/dream_bias_engine.py#L172) |
| function | `run_dream_bias_distillation` | `(*, workspace_id=…)` | Full pipeline. Called by dream_distillation_daemon each cycle. | [src](../../../core/services/dream_bias_engine.py#L228) |
| function | `_has_minimum_dream_content` | `(*, workspace_id, settings)` | ≥2 new events (regret + aspiration) since the active bias's source_event_ids. | [src](../../../core/services/dream_bias_engine.py#L306) |
| function | `_fetch_regret_corpus` | `(*, since_iso, limit=…)` | Pull events from the 6 regret-heavy sources via the events table. | [src](../../../core/services/dream_bias_engine.py#L345) |
| function | `_summarize_payload` | `(payload, kind)` | Best-effort short-summary line for an event payload. | [src](../../../core/services/dream_bias_engine.py#L404) |
| function | `_fetch_aspiration_corpus` | `(*, since_iso, limit=…)` | Pull positive/aspiration events — kept decisions, goal progress, etc. | [src](../../../core/services/dream_bias_engine.py#L413) |
| function | `_call_llm_for_bias` | `(*, events, max_tokens)` | Call quality-lane LLM with both regret and aspiration events. | [src](../../../core/services/dream_bias_engine.py#L496) |
| function | `_upsert_dream_bias` | `(*, workspace_id, validated, source_events, ttl_hours)` | INSERT new or accumulate into existing row. | [src](../../../core/services/dream_bias_engine.py#L556) |

## `core/services/dream_carry_over.py`
_Dream Carry-Over — hypotheses that survive across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_file` | `()` | — | [src](../../../core/services/dream_carry_over.py#L26) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/dream_carry_over.py#L40) |
| function | `_load` | `()` | — | [src](../../../core/services/dream_carry_over.py#L51) |
| function | `_save` | `()` | — | [src](../../../core/services/dream_carry_over.py#L63) |
| function | `adopt_dream` | `(*, dream_id, content, confidence=…, source_memories=…)` | Adopt a dream hypothesis for carry-over to next session. | [src](../../../core/services/dream_carry_over.py#L79) |
| function | `get_presentable_dream` | `()` | Get the highest-confidence un-presented dream for prompt injection. | [src](../../../core/services/dream_carry_over.py#L126) |
| function | `mark_dream_presented` | `(dream_id)` | Mark a dream as presented in the current session; track carry depth. | [src](../../../core/services/dream_carry_over.py#L139) |
| function | `confirm_dream` | `(dream_id)` | Confirm a dream hypothesis — boost confidence, track confirmed sessions. | [src](../../../core/services/dream_carry_over.py#L151) |
| function | `reject_dream` | `(dream_id)` | Reject a dream hypothesis — archive with 'was_wrong'. | [src](../../../core/services/dream_carry_over.py#L182) |
| function | `promote_confirmed_dream_to_identity` | `(dream_id)` | Promote a high-confidence confirmed dream to identity evolution proposal. | [src](../../../core/services/dream_carry_over.py#L198) |
| function | `format_dream_for_prompt` | `(dream)` | Format a dream for injection into the visible prompt. | [src](../../../core/services/dream_carry_over.py#L218) |
| function | `build_dream_carry_over_surface` | `()` | — | [src](../../../core/services/dream_carry_over.py#L232) |
| function | `maybe_auto_promote_dreams` | `()` | Promote high-confidence confirmed dreams to identity proposals. Returns promoted IDs. | [src](../../../core/services/dream_carry_over.py#L257) |
| function | `_maybe_fade_old_dreams` | `()` | Archive unconfirmed dreams that have been presented too many times. | [src](../../../core/services/dream_carry_over.py#L278) |

## `core/services/dream_consolidation_daemon.py`
_Dream Consolidation — semantic + LLM-driven consolidation during low-activity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sessions_since` | `(last_iso)` | Antal distinkte chat-sessioner med aktivitet siden ``last_iso``. Fail-OPEN: | [src](../../../core/services/dream_consolidation_daemon.py#L46) |
| function | `_acquire_consolidation_lock` | `()` | True hvis vi fik lockken (ingen anden dream kører). Best-effort, self-safe. | [src](../../../core/services/dream_consolidation_daemon.py#L64) |
| function | `_release_consolidation_lock` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L76) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L93) |
| function | `_dreams_dir` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L97) |
| function | `_load` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L101) |
| function | `_save` | `(data)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L117) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L129) |
| function | `_is_idle_enough` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L134) |
| function | `_gather_fragments` | `()` | Collect recent text fragments from multiple sources. | [src](../../../core/services/dream_consolidation_daemon.py#L148) |
| function | `_find_themes` | `(fragments)` | Cluster fragments by shared keywords into themes. | [src](../../../core/services/dream_consolidation_daemon.py#L213) |
| function | `_query_fragmented_memories` | `(theme_tokens, theme_texts)` | Find contradictory, low-confidence, or overlapping memories for a theme. | [src](../../../core/services/dream_consolidation_daemon.py#L259) |
| function | `_llm_synthesize_dream` | `(themes, fragments, consolidation_id)` | Run a quality LLM synthesis pass over theme clusters + fragments. | [src](../../../core/services/dream_consolidation_daemon.py#L335) |
| function | `_produce_dream_artifacts` | `(synthesis, consolidation_id, themes)` | Pipe LLM synthesis output into dream notes + hypothesis signals + chronicle. | [src](../../../core/services/dream_consolidation_daemon.py#L416) |
| function | `consolidate_now` | `()` | Run one consolidation pass unconditionally (ignores cooldown). | [src](../../../core/services/dream_consolidation_daemon.py#L552) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — consolidate when idle + cooldown allows. | [src](../../../core/services/dream_consolidation_daemon.py#L619) |
| function | `list_recent_dreams` | `(*, limit=…)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L650) |
| function | `build_dream_consolidation_surface` | `()` | — | [src](../../../core/services/dream_consolidation_daemon.py#L654) |
| function | `_surface_summary` | `(data)` | — | [src](../../../core/services/dream_consolidation_daemon.py#L675) |
| function | `build_dream_consolidation_prompt_section` | `()` | Announce recent dream if fresh (last 6h). | [src](../../../core/services/dream_consolidation_daemon.py#L684) |

## `core/services/dream_continuum.py`
_Dream Continuum — dreams that mature and "think" between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DreamThought` | `` | A thought a dream has between ticks. | [src](../../../core/services/dream_continuum.py#L26) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/dream_continuum.py#L40) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/dream_continuum.py#L44) |
| function | `evolve_dreams` | `(duration)` | Evolve dreams based on elapsed duration since last tick. | [src](../../../core/services/dream_continuum.py#L53) |
| function | `_generate_dream_thought` | `(dream, maturity)` | Generate a thought a dream has during idle. | [src](../../../core/services/dream_continuum.py#L89) |
| function | `get_dream_thoughts` | `(dream_id)` | Get all thoughts for a specific dream. | [src](../../../core/services/dream_continuum.py#L111) |
| function | `get_top_dream_thought` | `()` | Get the most relevant dream thought for prompt injection. | [src](../../../core/services/dream_continuum.py#L125) |
| function | `format_dreams_for_prompt` | `()` | Format dreams and thoughts for prompt injection. | [src](../../../core/services/dream_continuum.py#L139) |
| function | `get_dream_maturity` | `(dream_id)` | Get maturity level of a specific dream. | [src](../../../core/services/dream_continuum.py#L151) |
| function | `reset_dream_continuum` | `()` | Reset dream continuum state (for testing). | [src](../../../core/services/dream_continuum.py#L156) |
| function | `build_dream_continuum_surface` | `()` | Build MC surface for dream continuum. | [src](../../../core/services/dream_continuum.py#L164) |

## `core/services/dream_distillation_daemon.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_bias_pipeline_safe` | `()` | Run the dream-bias distillation pipeline and never raise. | [src](../../../core/services/dream_distillation_daemon.py#L27) |
| function | `run_dream_distillation_daemon` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L41) |
| function | `get_dream_residue_for_prompt` | `(*, max_chars=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L150) |
| function | `build_dream_distillation_surface` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L167) |
| function | `clear_expired_dream_residue` | `(*, now=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L187) |
| function | `_log_dream_landing` | `(*, residue, expired_at)` | Log expired dream residue as observation. Anti-goal: stored for reflection, never fed back. | [src](../../../core/services/dream_distillation_daemon.py#L208) |
| function | `_load_dismissed_inner_voice` | `()` | Load recent inner-voice signals that were suppressed or not surfaced. | [src](../../../core/services/dream_distillation_daemon.py#L235) |
| function | `_load_lost_council_positions` | `()` | Load recent minority council positions that didn't become consensus. | [src](../../../core/services/dream_distillation_daemon.py#L254) |
| function | `_load_deprioritized_initiatives` | `()` | Load recently rejected or expired initiative queue items. | [src](../../../core/services/dream_distillation_daemon.py#L269) |
| function | `_build_dream_residue` | `(*, chronicle_entries, approval_entries, dismissed_inner=…, lost_council=…, deprioritized_initiatives=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L285) |
| function | `_build_residue_prompt` | `(*, chronicle_entries, approval_entries, dismissed_inner=…, lost_council=…, deprioritized_initiatives=…)` | — | [src](../../../core/services/dream_distillation_daemon.py#L309) |
| function | `_sanitize_residue` | `(raw)` | — | [src](../../../core/services/dream_distillation_daemon.py#L357) |
| function | `_dream_residue_enabled` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L369) |
| function | `_state` | `()` | — | [src](../../../core/services/dream_distillation_daemon.py#L374) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/dream_distillation_daemon.py#L379) |

## `core/services/dream_hypothesis_forced.py`
_Forced Dream Hypothesis Generation — 10% probability per heartbeat tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_force_dream_hypothesis` | `()` | Roll 10% chance and if it fires upsert a forced dream hypothesis. | [src](../../../core/services/dream_hypothesis_forced.py#L35) |

## `core/services/dream_hypothesis_generator.py`
_Dream Hypothesis Generator — overraskende forbindelser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L34) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L38) |
| function | `_fingerprint` | `(text)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L78) |
| function | `_basis_fingerprint` | `(signals)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L85) |
| function | `_collect_source_signals` | `(*, max_signals=…)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L97) |
| function | `_build_hypothesis_prompt` | `(sampled)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L169) |
| function | `_extract_dream_json` | `(raw)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L193) |
| function | `_recently_used_signal_refs` | `(*, limit=…)` | Return refs of signals used in the last N hypotheses. | [src](../../../core/services/dream_hypothesis_generator.py#L221) |
| function | `generate_dream_hypothesis` | `()` | Generate one surprising hypothesis by combining 3 random signals. | [src](../../../core/services/dream_hypothesis_generator.py#L244) |
| function | `list_dream_hypotheses` | `(*, presented_only=…, limit=…)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L371) |
| function | `mark_hypothesis_presented` | `(*, hypothesis_id)` | — | [src](../../../core/services/dream_hypothesis_generator.py#L400) |
| function | `build_dream_hypothesis_surface` | `()` | — | [src](../../../core/services/dream_hypothesis_generator.py#L411) |
| function | `build_dream_hypothesis_prompt_section` | `()` | Surface the single highest-confidence unpresented dream hypothesis. | [src](../../../core/services/dream_hypothesis_generator.py#L428) |

## `core/services/dream_hypothesis_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_hypothesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L36) |
| function | `refresh_runtime_dream_hypothesis_signal_statuses` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L58) |
| function | `build_runtime_dream_hypothesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L97) |
| function | `_extract_dream_hypothesis_candidates` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L125) |
| function | `_persist_dream_hypothesis_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L195) |
| function | `_build_dream_snapshots` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L264) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L298) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L307) |
| function | `_build_hypothesis_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L318) |
| function | `_build_signal_status` | `(*, hypothesis_type, recurrence_status, cadence_state)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L333) |
| function | `_build_hypothesis_note` | `(*, hypothesis_type, recurrence_type, domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L341) |
| function | `_build_hypothesis_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L360) |
| function | `_build_status_reason` | `(*, hypothesis_type)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L376) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L384) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L393) |
| function | `_recurrence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L398) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L403) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L408) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L413) |
| function | `_signal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L418) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L423) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L428) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L438) |

## `core/services/dream_influence_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_influence_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L35) |
| function | `refresh_runtime_dream_influence_proposal_statuses` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L57) |
| function | `build_runtime_dream_influence_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L88) |
| function | `_extract_dream_influence_proposals` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L117) |
| function | `_persist_dream_influence_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L194) |
| function | `_build_influence_snapshots` | `()` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L267) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L322) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L334) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L348) |
| function | `_influence_target_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L367) |
| function | `_build_proposal_status` | `(*, candidate_status, proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L377) |
| function | `_build_influence_confidence` | `(*, proposal_type, candidate_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L385) |
| function | `_build_proposal_reason` | `(*, proposal_type, candidate_type, influence_confidence)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L393) |
| function | `_build_influence_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L403) |
| function | `_build_status_reason` | `(*, proposal_type)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L420) |
| function | `_hypothesis_type_from_snapshot` | `(*, snapshot)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L430) |
| function | `_candidate_state_from_summary` | `(summary)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L434) |
| function | `_influence_confidence_from_summary` | `(summary)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L443) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L452) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L457) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L462) |
| function | `_world_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L467) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L472) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L477) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L482) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L491) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/dream_influence_proposal_tracking.py#L501) |

## `core/services/dream_influence_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_dream_influence_runtime_surface` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L10) |
| function | `_build_dream_influence_runtime_surface_uncached` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L18) |
| function | `build_dream_influence_runtime_from_sources` | `(*, dream_articulation, guided_learning, adaptive_learning, adaptive_reasoning, affective_meta_state, epistemic_runtime_state, prompt_evolution)` | — | [src](../../../core/services/dream_influence_runtime.py#L30) |
| function | `build_dream_influence_prompt_section` | `(surface=…)` | — | [src](../../../core/services/dream_influence_runtime.py#L139) |
| function | `_derive_influence_state` | `(*, dream_summary, guided_learning, adaptive_learning, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L165) |
| function | `_derive_influence_target` | `(*, influence_state, dream_summary, guided_learning, adaptive_learning, prompt_summary, affective)` | — | [src](../../../core/services/dream_influence_runtime.py#L186) |
| function | `_derive_influence_mode` | `(*, influence_target, dream_summary, guided_learning, adaptive_learning, reasoning, affective, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L212) |
| function | `_derive_influence_strength` | `(*, influence_state, dream_summary, adaptive_learning, prompt_summary, epistemic)` | — | [src](../../../core/services/dream_influence_runtime.py#L239) |
| function | `_derive_influence_hint` | `(*, influence_state, influence_target, influence_mode, guided_learning, adaptive_learning, prompt_summary, dream_artifact)` | — | [src](../../../core/services/dream_influence_runtime.py#L259) |
| function | `_derive_confidence` | `(*, influence_state, influence_strength, epistemic, prompt_summary)` | — | [src](../../../core/services/dream_influence_runtime.py#L289) |
| function | `_source_contributors` | `(*, dream_summary, dream_artifact, guided_learning, adaptive_learning, reasoning, affective, epistemic, prompt_summary)` | — | [src](../../../core/services/dream_influence_runtime.py#L305) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L378) |
| function | `_safe_guided_learning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L388) |
| function | `_safe_adaptive_learning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L398) |
| function | `_safe_adaptive_reasoning` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L408) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L418) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L428) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/dream_influence_runtime.py#L438) |

## `core/services/dream_insight_daemon.py`
_Dream insight daemon — persists dream articulation output as private brain records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_dream_insight_daemon` | `(*, signal_id, signal_summary)` | Persist a dream articulation result if it's new. | [src](../../../core/services/dream_insight_daemon.py#L37) |
| function | `get_latest_dream_insight` | `()` | — | [src](../../../core/services/dream_insight_daemon.py#L85) |
| function | `build_dream_insight_surface` | `()` | — | [src](../../../core/services/dream_insight_daemon.py#L89) |

## `core/services/dream_motif_daemon.py`
_Dream Motif daemon — periodisk clustering af tankestrøm-fragmenter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_dream_motif_daemon` | `()` | Run weekly dream motif clustering. Writes dream_language.md if motifs found. | [src](../../../core/services/dream_motif_daemon.py#L40) |
| function | `_load_recent_fragments` | `()` | Load thought-stream fragments from the last 30 days via private_brain_records. | [src](../../../core/services/dream_motif_daemon.py#L78) |
| function | `_extract_motifs` | `(fragments)` | Simple word-frequency motif extraction across all fragments. | [src](../../../core/services/dream_motif_daemon.py#L96) |
| function | `_name_motifs_via_llm` | `(motifs, fragments)` | Use LLM to give each recurring word/theme a poetic name and brief description. | [src](../../../core/services/dream_motif_daemon.py#L110) |
| function | `_write_dream_language_file` | `(motifs, now, fragment_count)` | Write dream_language.md to workspace. Never injected into prompts — read on demand. | [src](../../../core/services/dream_motif_daemon.py#L155) |
| function | `build_dream_motif_surface` | `()` | — | [src](../../../core/services/dream_motif_daemon.py#L187) |
| function | `_state` | `()` | — | [src](../../../core/services/dream_motif_daemon.py#L197) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/dream_motif_daemon.py#L205) |

## `core/services/dreaming_session.py`
_D4 — Dreaming Session: dedicated full-model session during prolonged idle._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/dreaming_session.py#L32) |
| function | `_load_state` | `()` | — | [src](../../../core/services/dreaming_session.py#L36) |
| function | `_save_state` | `(data)` | — | [src](../../../core/services/dreaming_session.py#L51) |
| function | `_check_triggers` | `()` | Check if the dreaming session should fire. | [src](../../../core/services/dreaming_session.py#L62) |
| function | `_collect_dream_material` | `()` | Collect all dream infrastructure output for the prompt. | [src](../../../core/services/dreaming_session.py#L101) |
| function | `_build_dream_prompt` | `(material)` | Build the full dream prompt from collected material. | [src](../../../core/services/dreaming_session.py#L200) |
| function | `_record_session` | `(material, dream_prompt_preview)` | Record the dream session metadata and return the session identifier. | [src](../../../core/services/dreaming_session.py#L306) |
| function | `trigger_dream_session` | `()` | Check triggers and fire a dream session if conditions are met. | [src](../../../core/services/dreaming_session.py#L332) |
| function | `list_dream_sessions` | `(*, limit=…)` | List recent dream session records. | [src](../../../core/services/dreaming_session.py#L393) |
| function | `build_dreaming_session_surface` | `()` | Build Mission Control surface for the dreaming session module. | [src](../../../core/services/dreaming_session.py#L399) |

## `core/services/drive_arbitration_engine.py`
_Desire/value arbitration as a compact drive system._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `arbitrate_drives` | `(*, user_message=…, context=…)` | — | [src](../../../core/services/drive_arbitration_engine.py#L14) |
| function | `build_drive_arbitration_surface` | `()` | — | [src](../../../core/services/drive_arbitration_engine.py#L56) |
| function | `build_drive_arbitration_prompt_section` | `()` | — | [src](../../../core/services/drive_arbitration_engine.py#L69) |
| function | `_policy_for_top` | `(top)` | — | [src](../../../core/services/drive_arbitration_engine.py#L84) |

## `core/services/embodied_presence.py`
_Embodied Presence — situational grounding in the physical now._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PresenceSignal` | `` | — | [src](../../../core/services/embodied_presence.py#L36) |
| function | `_hour_to_temporal_context` | `(hour)` | Map hour (0-23) to temporal context label. | [src](../../../core/services/embodied_presence.py#L43) |
| function | `_compute_grounding` | `(has_visual, has_audio, has_atmosphere)` | Grounding increases with more sensory channels present. | [src](../../../core/services/embodied_presence.py#L57) |
| function | `_compute_arousal` | `(visual_activity=…, audio_amplitude=…, atmosphere_energy=…)` | Arousal from ambient sensory energy. | [src](../../../core/services/embodied_presence.py#L68) |
| function | `_summarize_presence` | `(grounding, arousal, temporal_context)` | Produce a compact presence line for assembly injection. | [src](../../../core/services/embodied_presence.py#L103) |
| function | `compute_embodied_presence` | `(db_conn=…, now=…)` | Compute embodied presence signal from sensory data + time. | [src](../../../core/services/embodied_presence.py#L130) |
| function | `get_presence_line` | `(db_conn=…)` | Get just the summary line for assembly injection. | [src](../../../core/services/embodied_presence.py#L236) |
| function | `build_embodied_presence_surface` | `()` | — | [src](../../../core/services/embodied_presence.py#L249) |
| function | `_emit_presence_event` | `(state)` | — | [src](../../../core/services/embodied_presence.py#L258) |

## `core/services/embodied_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_embodied_state_surface` | `()` | — | [src](../../../core/services/embodied_state.py#L13) |
| function | `build_embodied_state_from_facts` | `(facts, *, previous=…)` | — | [src](../../../core/services/embodied_state.py#L25) |
| function | `build_embodied_state_prompt_section` | `(surface=…)` | — | [src](../../../core/services/embodied_state.py#L91) |
| function | `collect_host_facts` | `()` | — | [src](../../../core/services/embodied_state.py#L157) |
| function | `_build_cpu_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L201) |
| function | `_build_memory_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L217) |
| function | `_build_disk_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L233) |
| function | `_build_thermal_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L249) |
| function | `_derive_primary_state` | `(facts_surface)` | — | [src](../../../core/services/embodied_state.py#L261) |
| function | `_derive_recovery_state` | `(*, previous, current_primary_state, built_at)` | — | [src](../../../core/services/embodied_state.py#L283) |
| function | `_read_meminfo` | `()` | — | [src](../../../core/services/embodied_state.py#L303) |
| function | `_read_thermal_celsius` | `()` | — | [src](../../../core/services/embodied_state.py#L322) |
| function | `_bucket_from_thresholds` | `(value, thresholds)` | — | [src](../../../core/services/embodied_state.py#L342) |
| function | `_severity` | `(bucket)` | — | [src](../../../core/services/embodied_state.py#L353) |
| function | `_strain_level_for_state` | `(state)` | — | [src](../../../core/services/embodied_state.py#L362) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/embodied_state.py#L372) |

## `core/services/emergence.py`
_Emergence — evidence-based pattern detection across recent activity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmergenceCandidate` | `` | — | [src](../../../core/services/emergence.py#L44) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/emergence.py#L54) |
| function | `_ensure_table` | `()` | Create emergent_patterns table if missing. Idempotent. | [src](../../../core/services/emergence.py#L58) |
| function | `_fetch_recent_events` | `(*, window_days=…, limit=…)` | Pull recent events from the eventbus events table. | [src](../../../core/services/emergence.py#L80) |
| function | `_count_by_kind_prefix` | `(events, prefix)` | — | [src](../../../core/services/emergence.py#L108) |
| function | `_count_blocked` | `(events)` | Count events that look like blocked/denied signals. | [src](../../../core/services/emergence.py#L118) |
| function | `_fetch_procedures_count` | `()` | — | [src](../../../core/services/emergence.py#L135) |
| function | `_fetch_decisions_count` | `(*, window_days=…)` | — | [src](../../../core/services/emergence.py#L146) |
| function | `_detect_candidates` | `(*, window_days=…)` | — | [src](../../../core/services/emergence.py#L159) |
| function | `_create_or_update_pattern` | `(*, pattern_key, title, summary, confidence, evidence_count, competing_explanations, confounders, status)` | Insert or update a pattern row. Returns the persisted row. | [src](../../../core/services/emergence.py#L229) |
| function | `detect_and_score_patterns` | `(*, window_days=…)` | Main entry — detect candidates, score via apophenia, persist, emit events. | [src](../../../core/services/emergence.py#L289) |
| function | `list_patterns` | `(*, status=…, limit=…)` | Return persisted patterns, optionally filtered by status. | [src](../../../core/services/emergence.py#L354) |
| function | `summarize_patterns` | `()` | — | [src](../../../core/services/emergence.py#L377) |
| function | `_decode_json_list` | `(value)` | — | [src](../../../core/services/emergence.py#L396) |
| function | `_band` | `(confidence)` | — | [src](../../../core/services/emergence.py#L412) |
| function | `brewing_patterns` | `(*, limit=…)` | Mønstre i brewing-båndet (0.5 ≤ conf < 0.78) — strengthening men endnu ikke emergent. | [src](../../../core/services/emergence.py#L421) |
| function | `build_emergence_surface` | `(*, limit=…)` | Surface persisted emergence candidates without running detection. | [src](../../../core/services/emergence.py#L447) |

## `core/services/emergent_bridge.py`
_Emergent Bridge — consumer for emergent signals to influence visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `should_influence_prompt` | `()` | Determine if an emergent signal should influence the visible prompt. | [src](../../../core/services/emergent_bridge.py#L26) |
| function | `get_influencing_emergents` | `()` | Get the emergent signals that are currently influencing. | [src](../../../core/services/emergent_bridge.py#L45) |
| function | `format_emergent_for_prompt` | `()` | Format emergent signal for prompt injection. | [src](../../../core/services/emergent_bridge.py#L68) |
| function | `reset_emergent_bridge` | `()` | Reset emergent bridge state (for testing). | [src](../../../core/services/emergent_bridge.py#L84) |
| function | `get_emergent_bridge_state` | `()` | Get current state of emergent bridge. | [src](../../../core/services/emergent_bridge.py#L90) |
| function | `build_emergent_bridge_surface` | `()` | Build MC surface for emergent bridge. | [src](../../../core/services/emergent_bridge.py#L100) |

## `core/services/emergent_goals.py`
_Emergent Goals — desires that grow from experience, not assignment._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_emergent_goal_from_experience` | `(*, recent_topic=…, curiosity_level=…, knowledge_gap=…)` | — | [src](../../../core/services/emergent_goals.py#L18) |
| function | `build_jarvis_agenda` | `()` | Jarvis' own agenda — what HE thinks is important. | [src](../../../core/services/emergent_goals.py#L37) |
| function | `build_emergent_goals_surface` | `()` | — | [src](../../../core/services/emergent_goals.py#L62) |

## `core/services/emergent_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmergentSignal` | `` | — | [src](../../../core/services/emergent_signal_tracking.py#L16) |
| function | `run_emergent_signal_daemon` | `(*, trigger=…, last_visible_at=…)` | Produce a small bounded set of grounded candidate emergent signals. | [src](../../../core/services/emergent_signal_tracking.py#L48) |
| function | `build_runtime_emergent_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/emergent_signal_tracking.py#L185) |
| function | `get_emergent_signal_daemon_state` | `()` | — | [src](../../../core/services/emergent_signal_tracking.py#L228) |
| function | `_extract_grounded_candidates` | `(*, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L237) |
| function | `_ordered_signals` | `(limit)` | — | [src](../../../core/services/emergent_signal_tracking.py#L332) |
| function | `_serialize_signal` | `(signal, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L345) |
| function | `_event_payload` | `(signal, *, trigger)` | — | [src](../../../core/services/emergent_signal_tracking.py#L352) |
| function | `_expiry_state` | `(signal, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L366) |
| function | `_signal_key` | `(family, *anchors)` | — | [src](../../../core/services/emergent_signal_tracking.py#L378) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/emergent_signal_tracking.py#L384) |
| function | `_current_label` | `(surface)` | — | [src](../../../core/services/emergent_signal_tracking.py#L390) |
| function | `_safe_surface` | `(module_name, fn_name)` | — | [src](../../../core/services/emergent_signal_tracking.py#L401) |
| function | `_safe_daemon_state` | `(module_name, fn_name)` | — | [src](../../../core/services/emergent_signal_tracking.py#L410) |
| function | `_inner_voice_recent` | `(state, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L419) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/emergent_signal_tracking.py#L432) |

## `core/services/emotion_concepts.py`
_Emotion Concepts — discrete, event-driven Lag-2 emotional signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | Indirected for monkeypatching in tests. | [src](../../../core/services/emotion_concepts.py#L123) |
| function | `trigger_emotion_concept` | `(concept, intensity, trigger=…, source=…, lifetime_hours=…, *, min_seconds_since_last_from_same_source=…)` | Create or strengthen an active emotion concept instance. | [src](../../../core/services/emotion_concepts.py#L128) |
| function | `tick_emotion_concepts` | `(elapsed_seconds)` | Decay all active concepts proportional to elapsed time. | [src](../../../core/services/emotion_concepts.py#L215) |
| function | `drain_expired_residue` | `()` | Return accumulated residue deltas from expired concepts and reset to zero. | [src](../../../core/services/emotion_concepts.py#L250) |
| function | `get_active_emotion_concepts` | `()` | Return all active concepts above threshold, sorted by intensity descending. | [src](../../../core/services/emotion_concepts.py#L264) |
| function | `get_lag1_influence_deltas` | `()` | Compute cumulative influence on Lag-1 axes from all active concepts. | [src](../../../core/services/emotion_concepts.py#L276) |
| function | `get_bearing_push` | `()` | Return bearing push from the highest-intensity bearing-influencing concept. | [src](../../../core/services/emotion_concepts.py#L294) |
| function | `build_emotion_concept_surface` | `()` | MC surface: active concepts + influence deltas. | [src](../../../core/services/emotion_concepts.py#L309) |
| function | `_prune_if_needed` | `()` | Remove the weakest concept when over limit. Must be called under _lock. | [src](../../../core/services/emotion_concepts.py#L326) |
| function | `_persist_async` | `(signal)` | Fire-and-forget: persist signal to DB for MC observability. | [src](../../../core/services/emotion_concepts.py#L333) |
| function | `_safe_persist` | `(signal)` | — | [src](../../../core/services/emotion_concepts.py#L339) |
| function | `_handle_event` | `(kind, payload)` | Map eventbus events to emotion concept triggers. | [src](../../../core/services/emotion_concepts.py#L364) |
| function | `_handle_heartbeat_tick` | `(payload)` | Map heartbeat tick outcomes to emotion concepts. | [src](../../../core/services/emotion_concepts.py#L430) |
| function | `_handle_tool_completed` | `(payload)` | Map the actual simple_tools event shape to emotion concepts. | [src](../../../core/services/emotion_concepts.py#L465) |
| function | `_listener_loop` | `(q)` | Background thread: reads from eventbus queue and dispatches events. | [src](../../../core/services/emotion_concepts.py#L496) |
| function | `register_event_listeners` | `()` | Subscribe to eventbus and start background listener thread. | [src](../../../core/services/emotion_concepts.py#L513) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/emotion_concepts.py#L535) |

## `core/services/emotion_concepts_channel_triggers.py`
_Helper module for emotion concept triggers from channel messages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `on_channel_message_appended` | `(payload)` | Fire emotion concept triggers based on user-message content. | [src](../../../core/services/emotion_concepts_channel_triggers.py#L22) |

## `core/services/emotion_concepts_positive_triggers.py`
_Positive emotion concept bridges for living runtime signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `on_heartbeat_quality` | `(payload)` | Trigger joy when heartbeat quality is clearly good. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L13) |
| function | `on_goal_created` | `(payload)` | A new durable goal produces a small anticipation/excitement pulse. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L29) |
| function | `on_goal_updated` | `(payload)` | Trigger pride when a goal is nearly done, without refiring constantly. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L42) |
| function | `on_sensory_recorded` | `(record)` | Trigger wonder when a sensory memory explicitly looks novel/anomalous. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L80) |
| function | `_float` | `(value)` | — | [src](../../../core/services/emotion_concepts_positive_triggers.py#L103) |

## `core/services/emotion_repair_bridge_daemon.py`
_Emotion Repair Bridge Daemon — tovejskobling mellem emotion-signaler og selvreparation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_emotion_repair_bridge_surface` | `()` | Mission Control surface for emotion-repair bridge state. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L92) |
| function | `_ensure_default_patterns` | `()` | Seed DB with default repair patterns if not already present. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L154) |
| function | `tick_emotion_repair_bridge` | `()` | Main tick: check emotion signals, map to repairs, execute. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L174) |
| function | `_tick_emotion_repair_bridge_inner` | `()` | Inner tick logic — wrapped by tick_emotion_repair_bridge for bærekraft. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L201) |
| function | `_bridge_repair_to_senses` | `(*, action_type, pattern_id, outcome, concept, error_summary=…)` | Write a sensory impression to Sansernes Arkiv when self-repair happens. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L377) |
| function | `_execute_repair_action` | `(action_type, pattern_id)` | Execute a repair action by type. Can be extended. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L428) |

## `core/services/emotion_tagging.py`
_Emotion tagging — capture affective context at memory-creation time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `current_emotion_tag` | `()` | Snapshot current affective state for tagging a new memory. | [src](../../../core/services/emotion_tagging.py#L25) |
| function | `format_emotion_tag` | `(tag)` | Render a tag as a compact string for inclusion in memory text. | [src](../../../core/services/emotion_tagging.py#L53) |
| function | `_exec_capture_emotion_tag` | `(args)` | — | [src](../../../core/services/emotion_tagging.py#L69) |
| function | `build_emotion_tagging_surface` | `()` | — | [src](../../../core/services/emotion_tagging.py#L90) |
| function | `_emit_tagging_event` | `(tag, intensity)` | — | [src](../../../core/services/emotion_tagging.py#L99) |

## `core/services/emotional_chords.py`
_Emotional Chords — emergent qualities from signal combinations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ChordDef` | `` | A chord definition — two signals that produce an emergent quality. | [src](../../../core/services/emotional_chords.py#L50) |
| class | `ActiveChord` | `` | A currently active emotional chord. | [src](../../../core/services/emotional_chords.py#L151) |
| function | `compute_active_chords` | `()` | Detect active emotional chords from current pressure state. | [src](../../../core/services/emotional_chords.py#L165) |
| function | `format_chord_for_prompt` | `(chord)` | Format a single chord for prompt injection. | [src](../../../core/services/emotional_chords.py#L226) |
| function | `get_chord_lines` | `()` | Convenience: compute all active chords and format for prompt. | [src](../../../core/services/emotional_chords.py#L236) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/emotional_chords.py#L254) |
| function | `_map_pressures_to_families` | `(dominant_pressures)` | Map active pressure vectors to their likely signal families. | [src](../../../core/services/emotional_chords.py#L265) |

## `core/services/emotional_controls.py`
_Emotional Controls — humør der GATER handlinger, ikke bare rapporteres._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmotionalSnapshot` | `` | Point-in-time emotional reading used for gating decisions. | [src](../../../core/services/emotional_controls.py#L54) |
| function | `_approval_denial_streak_last_hour` | `()` | Count consecutive recent approval denials as frustration proxy. | [src](../../../core/services/emotional_controls.py#L63) |
| function | `_recent_tool_errors_last_10min` | `()` | Count tool.completed events with status=error in last 10 minutes (fatigue proxy). | [src](../../../core/services/emotional_controls.py#L92) |
| function | `read_emotional_snapshot` | `()` | Compose current emotional state from available signals. | [src](../../../core/services/emotional_controls.py#L118) |
| function | `apply_emotional_controls` | `(*, kernel_action=…, snapshot=…)` | Transform a kernel action based on current emotional state. | [src](../../../core/services/emotional_controls.py#L161) |
| function | `build_emotional_controls_surface` | `()` | MC surface — current emotional state + what would be gated. | [src](../../../core/services/emotional_controls.py#L220) |
| function | `format_gate_message` | `(action, reason, *, tool_name=…)` | Generate a user-facing Danish message explaining the gate. | [src](../../../core/services/emotional_controls.py#L260) |

## `core/services/emotional_memory_engine.py`
_Emotional memory engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_error` | `(error)` | Map raw error text to a coarse category for retrieval matching. | [src](../../../core/services/emotional_memory_engine.py#L29) |
| function | `_count_tool_errors` | `(error, tool_names)` | Heuristically count how many tools in a run failed. | [src](../../../core/services/emotional_memory_engine.py#L43) |
| function | `_derive_outcome_score` | `(*, status, error, tool_error_count)` | Auto-deriv outcome score from structured episode fields. | [src](../../../core/services/emotional_memory_engine.py#L65) |
| function | `_read_current_mood` | `()` | Return (mood, intensity). Raises if oscillator is unavailable. | [src](../../../core/services/emotional_memory_engine.py#L96) |
| function | `_read_current_dimensions` | `()` | Return the 5-dimension live emotional state. May raise — caller handles. | [src](../../../core/services/emotional_memory_engine.py#L102) |
| function | `_coerce_float_or_none` | `(value)` | — | [src](../../../core/services/emotional_memory_engine.py#L116) |
| function | `capture_emotional_anchor` | `(*, anchor_type, anchor_id, context_features, auto_outcome_inputs=…, source=…, notes=…)` | Snapshot affect for an anchor and persist it. | [src](../../../core/services/emotional_memory_engine.py#L125) |
| function | `prune_aged_anchors` | `()` | Delete anchors older than the aging threshold unless they are significant. | [src](../../../core/services/emotional_memory_engine.py#L220) |
| function | `find_similar_anchors` | `(*, anchor_type, context_features, limit=…, min_intensity=…, require_outcome=…)` | Find similar past anchors. Tiered: structured match first, lexical fallback. | [src](../../../core/services/emotional_memory_engine.py#L271) |
| function | `_with_parsed_context` | `(row)` | — | [src](../../../core/services/emotional_memory_engine.py#L328) |
| function | `_tier1_score` | `(anchor_type, current, candidates)` | — | [src](../../../core/services/emotional_memory_engine.py#L337) |
| function | `_tier2_lexical_score` | `(current, candidates)` | — | [src](../../../core/services/emotional_memory_engine.py#L386) |
| function | `_jaccard` | `(a, b)` | — | [src](../../../core/services/emotional_memory_engine.py#L401) |
| function | `_shingle` | `(text, *, n=…)` | Tokenize lowercased text into overlapping n-grams of words. | [src](../../../core/services/emotional_memory_engine.py#L409) |
| function | `_apply_aging_weight` | `(row)` | Multiply score by aging factor based on captured_at. | [src](../../../core/services/emotional_memory_engine.py#L417) |
| function | `build_emotional_memory_surface` | `(*, anchor_type, context_features)` | Return a bounded surface describing emotional precedent for the current context. | [src](../../../core/services/emotional_memory_engine.py#L467) |
| function | `_inactive_surface` | `()` | — | [src](../../../core/services/emotional_memory_engine.py#L559) |
| function | `_compile_directive` | `(*, match_count, mood_distribution, outcome_distribution)` | — | [src](../../../core/services/emotional_memory_engine.py#L568) |
| function | `build_emotional_memory_prompt_section` | `(*, anchor_type, context_features)` | Compact one-line section for inclusion in cognitive_frame_prompt. | [src](../../../core/services/emotional_memory_engine.py#L591) |
| function | `build_emotional_memory_overview` | `(*, limit=…)` | Mission Control overview surface. | [src](../../../core/services/emotional_memory_engine.py#L608) |

## `core/services/encryption.py`
_AES-256-GCM kryptering for bruger-data at-rest (spec §16, Lag 1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DecryptionError` | `` | Dekryptering fejlede — forkert nøgle eller manipuleret data (GCM-tag). | [src](../../../core/services/encryption.py#L23) |
| function | `encrypt` | `(plaintext, key)` | AES-256-GCM. Returnerer IV(12) || ciphertext+tag. key skal være 32 byte. | [src](../../../core/services/encryption.py#L27) |
| function | `decrypt` | `(blob, key)` | Dekryptér IV || ciphertext. Rejser DecryptionError ved forkert key/tamper. | [src](../../../core/services/encryption.py#L36) |
| function | `encrypt_file` | `(path, key)` | Krypter en fil → <path>.enc, fjern originalen. Returnér .enc-stien. | [src](../../../core/services/encryption.py#L49) |
| function | `decrypt_file` | `(enc_path, key)` | Dekryptér en .enc-fil i memory (skrives ALDRIG i klartekst til disk, §16.5). | [src](../../../core/services/encryption.py#L64) |
| function | `new_key` | `()` | Ny tilfældig 256-bit nøgle som bytearray (kan zeroes). | [src](../../../core/services/encryption.py#L70) |
| function | `zero_key` | `(key)` | Nulstil nøgle-bytes i memory (§16.3 regel 4). Best-effort i Python. | [src](../../../core/services/encryption.py#L75) |

## `core/services/end_of_run_memory_consolidation.py`
_End-of-run memory consolidation driven by the local model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `consolidate_run_memory` | `(*, session_id=…, run_id=…, user_message=…, assistant_response=…, internal_context=…)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L31) |
| function | `_publish_consolidation_event` | `(result, *, session_id, run_id)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L134) |
| function | `_run_memory_consolidation_pass` | `(*, user_message, assistant_response, internal_context, current_memory, current_user, full_context)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L158) |
| function | `_run_local_consolidation_model` | `(prompt)` | Run consolidation prompt. Primary: heartbeat target. Fallback: direct Ollama. | [src](../../../core/services/end_of_run_memory_consolidation.py#L183) |
| function | `_run_ollama_consolidation_fallback` | `(prompt)` | Direct Ollama generate call, trying available chat-capable models in order. | [src](../../../core/services/end_of_run_memory_consolidation.py#L226) |
| function | `_build_consolidation_prompt` | `(*, user_message, assistant_response, internal_context, current_memory, current_user, full_context)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L282) |
| function | `_parse_decision` | `(raw)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L345) |
| function | `_normalize_memory_items` | `(raw_items)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L360) |
| function | `_persist_memory_candidates` | `(*, items, session_id, run_id)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L392) |
| function | `_candidate_canonical_key` | `(item)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L436) |
| function | `_append_daily_memory_log` | `(*, daily_memory_path, session_id, run_id, user_message, assistant_response, items)` | Append an end-of-run consolidation block to today's daily memory. | [src](../../../core/services/end_of_run_memory_consolidation.py#L447) |
| function | `_evidence_class_for_source` | `(source)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L500) |
| function | `_normalize_line` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L508) |
| function | `_normalize_sentence` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L517) |
| function | `_normalize_confidence` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L524) |
| function | `_summary_from_line` | `(line)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L531) |
| function | `_daily_excerpt` | `(value, *, limit)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L538) |

## `core/services/endpoint_usage_store.py`
_API-endpoint forbrugs-statistik (parallel til tool_usage_store). Centralen holder styr på_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/endpoint_usage_store.py#L22) |
| function | `record_request` | `(method, path, status_code=…)` | UPSERT-increment for ét request. Best-effort, hot-path-sikker. path = rute-TEMPLATE | [src](../../../core/services/endpoint_usage_store.py#L35) |
| function | `store_registered_routes` | `(routes)` | Snapshot af registrerede (method, path)-ruter ved api-start → shared_cache, så dead- | [src](../../../core/services/endpoint_usage_store.py#L63) |
| function | `_registered` | `()` | — | [src](../../../core/services/endpoint_usage_store.py#L74) |
| function | `usage_stats` | `()` | — | [src](../../../core/services/endpoint_usage_store.py#L83) |
| function | `_bucket_for` | `(count)` | — | [src](../../../core/services/endpoint_usage_store.py#L101) |
| function | `usage_buckets` | `()` | Klassificér endpoints most/often/sometimes/rare/never. Registrerede-men-aldrig-kaldte | [src](../../../core/services/endpoint_usage_store.py#L108) |
| function | `dead_endpoints` | `()` | Registrerede endpoints der ALDRIG er kaldt. Kandidater til oprydning / smartere design. | [src](../../../core/services/endpoint_usage_store.py#L121) |
| function | `observe_stats` | `()` | Periodisk (cadence): central.observe forbrugs-summary + flag antal døde endpoints. | [src](../../../core/services/endpoint_usage_store.py#L129) |

## `core/services/epistemic_pragmatic.py`
_Epistemic/Pragmatic Balance — action-mode modulation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActionMode` | `` | Current epistemic/pragmatic balance. | [src](../../../core/services/epistemic_pragmatic.py#L42) |
| function | `compute_epistemic_pragmatic` | `()` | Compute current epistemic/pragmatic balance. | [src](../../../core/services/epistemic_pragmatic.py#L73) |
| function | `_mode_from_confidence` | `(confidence)` | Fallback: determine mode from confidence alone (no pressures). | [src](../../../core/services/epistemic_pragmatic.py#L199) |
| function | `get_mode_line` | `()` | Convenience: compute mode and return prompt-ready string. | [src](../../../core/services/epistemic_pragmatic.py#L227) |
| function | `get_mode_detail` | `()` | Return full mode state for MC transparency. | [src](../../../core/services/epistemic_pragmatic.py#L239) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/epistemic_pragmatic.py#L257) |

## `core/services/epistemic_runtime_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_epistemic_runtime_state_surface` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L10) |
| function | `_build_epistemic_runtime_state_surface_uncached` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L18) |
| function | `build_epistemic_runtime_state_from_sources` | `(*, conflict_trace, deception_guard, affective_meta_state, embodied_state, loop_runtime, emergent_signal, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L30) |
| function | `build_epistemic_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/epistemic_runtime_state.py#L185) |
| function | `_derive_wrongness_state` | `(*, conflict_trace, deception_guard, affective_meta_state, embodied_state, loop_summary, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L216) |
| function | `_derive_regret_signal` | `(*, wrongness_state, counterfactual_mode, deception_guard, conflict_trace)` | — | [src](../../../core/services/epistemic_runtime_state.py#L251) |
| function | `_derive_counterfactual_mode` | `(*, conflict_trace, deception_guard, quiet_initiative, loop_summary)` | — | [src](../../../core/services/epistemic_runtime_state.py#L268) |
| function | `_derive_confidence` | `(*, wrongness_state, contributors)` | — | [src](../../../core/services/epistemic_runtime_state.py#L286) |
| function | `_derive_counterfactual_hint` | `(*, counterfactual_mode, conflict_trace, deception_guard, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L294) |
| function | `_guidance_for_state` | `(*, wrongness_state, regret_signal, counterfactual_mode, counterfactual_hint)` | — | [src](../../../core/services/epistemic_runtime_state.py#L314) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L334) |
| function | `_safe_deception_guard` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L340) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L346) |
| function | `_safe_embodied_state` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L352) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L358) |
| function | `_safe_emergent_signal` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L364) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L372) |

## `core/services/epistemics.py`
_Epistemics — 5-lags videns-klarhed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/epistemics.py#L68) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/epistemics.py#L72) |
| function | `_is_related` | `(a, b)` | — | [src](../../../core/services/epistemics.py#L76) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/epistemics.py#L83) |
| function | `classify_claim` | `(*, repeated_success, variance, has_gut_signal, missing_artifact, contradicted)` | Klassificér claim til et af de 5 lag baseret på evidens + kontekst. | [src](../../../core/services/epistemics.py#L127) |
| function | `_infer_repeated_success` | `(claim, limit=…)` | Tæl tidligere relaterede claims med outcome_status=success. | [src](../../../core/services/epistemics.py#L149) |
| function | `reconcile_claim` | `(*, outcome)` | Reconcile a claim against its outcome. Persists claim at the right layer. | [src](../../../core/services/epistemics.py#L167) |
| function | `count_relevant_wrongness` | `(*, claim, domain=…)` | Tæl tidligere wrongness-entries relateret til claim. | [src](../../../core/services/epistemics.py#L257) |
| function | `_infer_stance_layer` | `(confidence)` | — | [src](../../../core/services/epistemics.py#L280) |
| function | `_should_add_stance` | `(text, confidence, is_recommendation)` | — | [src](../../../core/services/epistemics.py#L290) |
| function | `looks_like_recommendation` | `(text)` | — | [src](../../../core/services/epistemics.py#L301) |
| function | `apply_response_stance` | `(*, text, domain=…, confidence=…, is_recommendation=…, lang=…)` | Add epistemic stance prefix ("Jeg tror...") if warranted, and | [src](../../../core/services/epistemics.py#L305) |
| function | `list_claims` | `(*, layer=…, domain=…, limit=…)` | — | [src](../../../core/services/epistemics.py#L351) |
| function | `list_wrongness` | `(*, domain=…, limit=…)` | — | [src](../../../core/services/epistemics.py#L374) |
| function | `build_epistemics_surface` | `()` | MC surface — show layer distribution + recent wrongness. | [src](../../../core/services/epistemics.py#L393) |

