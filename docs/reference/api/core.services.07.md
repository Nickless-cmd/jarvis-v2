# `core.services.07` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/cognitive_chronicle.py`
_Cognitive Chronicle — user-scoped read layer for chronicle entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `query_chronicle_for_user` | `(limit=…)` | Return chronicle entries visible to the current user. | [src](../../../core/services/cognitive_chronicle.py#L15) |

## `core/services/cognitive_core_experiments.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_build` | `(builder, system_id, label)` | Call a builder function, returning a disabled-stub on any error. | [src](../../../core/services/cognitive_core_experiments.py#L6) |
| function | `build_cognitive_core_experiments_surface` | `()` | Build shared runtime truth for the bounded cognitive-core experiment state. | [src](../../../core/services/cognitive_core_experiments.py#L31) |
| function | `_build_recurrence_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L100) |
| function | `_build_global_workspace_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L127) |
| function | `_build_hot_meta_cognition_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L155) |
| function | `_build_surprise_afterimage_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L182) |
| function | `_build_attention_blink_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L212) |
| function | `_activity_state` | `(*, enabled, active)` | — | [src](../../../core/services/cognitive_core_experiments.py#L239) |
| function | `_strongest_carry_item` | `(items)` | — | [src](../../../core/services/cognitive_core_experiments.py#L247) |

## `core/services/cognitive_episodes.py`
_Cognitive episodes as an active learning primitive._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_episode` | `(*, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Persist a cognitive episode and publish an eventbus signal. | [src](../../../core/services/cognitive_episodes.py#L25) |
| function | `record_visible_run_episode` | `(*, run_id, session_id=…, provider=…, model=…, status=…, user_message=…, assistant_text=…, error=…)` | Record a post-run episode grounded in the visible-run event trail. | [src](../../../core/services/cognitive_episodes.py#L176) |
| function | `derive_episode_fields` | `(*, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Derive the five cognitive dimensions plus next-behavior policy. | [src](../../../core/services/cognitive_episodes.py#L209) |
| function | `build_cognitive_episode_surface` | `(*, limit=…)` | Return active directives for the conductor/prompt path. | [src](../../../core/services/cognitive_episodes.py#L295) |
| function | `build_cognitive_episode_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/cognitive_episodes.py#L325) |
| function | `_tool_names_for_run` | `(run_id)` | — | [src](../../../core/services/cognitive_episodes.py#L341) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/cognitive_episodes.py#L368) |
| function | `_summarize_visible_run` | `(*, status, tool_names, assistant_text, error)` | — | [src](../../../core/services/cognitive_episodes.py#L387) |
| function | `_fallback_summary` | `(*, status, tool_names, error)` | — | [src](../../../core/services/cognitive_episodes.py#L398) |
| function | `_confidence` | `(*, status, error, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L406) |
| function | `_uncertainty_sources` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L416) |
| function | `_self_check` | `(*, status, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L435) |
| function | `_what_would_change_mind` | `(*, interrupted, proposal_error)` | — | [src](../../../core/services/cognitive_episodes.py#L445) |
| function | `_salience` | `(*, interrupted, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L453) |
| function | `_attention_directive` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L461) |
| function | `_ignore_or_defer` | `(*, tool_heavy, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L479) |
| function | `_learning_lesson` | `(*, interrupted, proposal_error, status, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L487) |
| function | `_policy_update` | `(*, interrupted, proposal_error, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L505) |
| function | `_social_directive` | `(*, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L515) |
| function | `_user_state_hypothesis` | `(*, user_l, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L521) |
| function | `_perception_directive` | `(*, tool_names, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L531) |
| function | `_observed_changes` | `(*, tool_names, status, error)` | — | [src](../../../core/services/cognitive_episodes.py#L539) |
| function | `_next_behavior` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy, status)` | — | [src](../../../core/services/cognitive_episodes.py#L548) |
| function | `_prompt_priority` | `(*, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L569) |

## `core/services/cognitive_state_assembly.py`
_Cognitive state assembly — closes the loop between accumulated state and visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cognitive_cache_key` | `(mode_key)` | — | [src](../../../core/services/cognitive_state_assembly.py#L68) |
| function | `_cache_ttl_seconds` | `()` | Read TTL from settings; default 120s. TTL=0 disables caching. | [src](../../../core/services/cognitive_state_assembly.py#L72) |
| function | `_cache_enabled` | `()` | Check if caching is enabled in settings. TTL=0 also disables. | [src](../../../core/services/cognitive_state_assembly.py#L82) |
| function | `_build_invalidation_snapshot` | `()` | Snapshot the key state signals that invalidate the cache. | [src](../../../core/services/cognitive_state_assembly.py#L94) |
| function | `_is_cache_valid` | `(cache_key)` | Check if cached state for `mode_key` (e.g. 'full') is fresh+coherent. | [src](../../../core/services/cognitive_state_assembly.py#L129) |
| function | `_get_cached_state` | `(cache_key)` | Return cached cognitive state string if valid, None otherwise. | [src](../../../core/services/cognitive_state_assembly.py#L145) |
| function | `_set_cached_state` | `(cache_key, text, sources)` | Store assembled cognitive state in shared_cache (cross-worker). | [src](../../../core/services/cognitive_state_assembly.py#L193) |
| function | `invalidate_cognitive_state_cache` | `()` | Explicitly invalidate all cognitive state caches across workers. | [src](../../../core/services/cognitive_state_assembly.py#L227) |
| function | `get_cognitive_state_cache_status` | `()` | Return cache status for MC transparency. | [src](../../../core/services/cognitive_state_assembly.py#L242) |
| function | `build_cognitive_state_for_prompt` | `(*, compact=…, force=…)` | Build the [COGNITIVE STATE] section for visible chat prompt injection. | [src](../../../core/services/cognitive_state_assembly.py#L295) |
| function | `build_cognitive_state_injection_surface` | `()` | MC surface showing exactly what was injected into the last visible prompt. | [src](../../../core/services/cognitive_state_assembly.py#L1024) |
| function | `_safe_call` | `(fn)` | Call a DB function, return None on any error. | [src](../../../core/services/cognitive_state_assembly.py#L1044) |
| function | `_safe_json` | `(value)` | Parse JSON string or return dict/list directly. | [src](../../../core/services/cognitive_state_assembly.py#L1053) |
| function | `_appraisal_record` | `(*, kind, state, evidence, allowed_effects, confidence, ttl_minutes=…)` | Structured truth record for optional narrative rendering. | [src](../../../core/services/cognitive_state_assembly.py#L1068) |
| function | `_build_cognitive_core_experiment_state_line` | `(*, compact)` | Build a bounded cognitive-state line for mainline experiment carry. | [src](../../../core/services/cognitive_state_assembly.py#L1093) |
| function | `_safe_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1157) |
| function | `_safe_cognitive_experiment_carry_frame` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1168) |
| function | `_narrativize_embodied_state` | `()` | LLM-narrativize current embodied state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1180) |
| function | `_narrativize_affective_state` | `()` | LLM-narrativize current affective meta state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1237) |
| function | `_narrativize_self_anchor` | `()` | LLM-narrativize the [SELF] ownership line from real personality state. | [src](../../../core/services/cognitive_state_assembly.py#L1290) |
| function | `_narrativize_boundary` | `()` | LLM-narrativize boundary awareness from real runtime context. | [src](../../../core/services/cognitive_state_assembly.py#L1339) |

## `core/services/cognitive_state_narrativizer.py`
_LLM-based narrativizer for cognitive state lines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_narrativizer_llm` | `(system_prompt, user_message)` | Call the compact LLM (heartbeat model) for narrative line generation. | [src](../../../core/services/cognitive_state_narrativizer.py#L44) |
| class | `_CachedNarrative` | `` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L101) |
| function | `_fingerprint` | `(state)` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L114) |
| function | `_generate_in_background` | `(*, line_key, fingerprint, system_prompt, user_message)` | Run the LLM call in a background thread and update cache. | [src](../../../core/services/cognitive_state_narrativizer.py#L119) |
| function | `narrativize_line` | `(*, line_key, state, system_prompt, user_message_builder, fallback=…)` | Return an LLM-narrativized line for this state, or fallback. | [src](../../../core/services/cognitive_state_narrativizer.py#L151) |
| function | `cache_snapshot` | `()` | Expose current cache state for MC observability. | [src](../../../core/services/cognitive_state_narrativizer.py#L228) |

## `core/services/collective_pulse_daemon.py`
_Collective Pulse — what is the air full of right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L43) |
| function | `_collective_dir` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L47) |
| function | `_load` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L51) |
| function | `_save` | `(data)` | — | [src](../../../core/services/collective_pulse_daemon.py#L67) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/collective_pulse_daemon.py#L79) |
| function | `_gather_week_text` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L86) |
| function | `_week_mood_trajectory` | `()` | Average mood over the week, if mood samples are available. | [src](../../../core/services/collective_pulse_daemon.py#L123) |
| function | `_describe_zeitgeist` | `(top_terms, mood_info)` | — | [src](../../../core/services/collective_pulse_daemon.py#L142) |
| function | `_write_weekly_note` | `(pulse)` | — | [src](../../../core/services/collective_pulse_daemon.py#L156) |
| function | `run_pulse` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L192) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/collective_pulse_daemon.py#L233) |
| function | `build_collective_pulse_surface` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L246) |
| function | `_surface_summary` | `(latest)` | — | [src](../../../core/services/collective_pulse_daemon.py#L259) |
| function | `build_collective_pulse_prompt_section` | `()` | Surface the week's zeitgeist while it's still current (within 7 days). | [src](../../../core/services/collective_pulse_daemon.py#L266) |

## `core/services/commit_attribution.py`
_Canonical, audit-only attribution metadata for Git commit messages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActorRule` | `` | Stable actor type and the origins that actor may claim. | [src](../../../core/services/commit_attribution.py#L28) |
| class | `CommitAttribution` | `` | The six required audit fields stored in a commit trailer block. | [src](../../../core/services/commit_attribution.py#L36) |
| method | `CommitAttribution.as_trailers` | `(self)` | — | [src](../../../core/services/commit_attribution.py#L46) |
| class | `AttributionError` | `` | Raised when attribution cannot satisfy the commit contract. | [src](../../../core/services/commit_attribution.py#L57) |
| function | `new_manual_run_id` | `(now=…, suffix=…)` | Return a sortable id for a commit without an existing runtime run. | [src](../../../core/services/commit_attribution.py#L69) |
| function | `parse_git_trailers` | `(message)` | Parse the final trailer block with Git's own trailer semantics. | [src](../../../core/services/commit_attribution.py#L85) |
| function | `validate_trailers` | `(trailers)` | Validate parsed trailers without reading process or repository state. | [src](../../../core/services/commit_attribution.py#L106) |
| function | `validate_commit_message` | `(message)` | Return every attribution error in a complete commit message. | [src](../../../core/services/commit_attribution.py#L159) |
| function | `_split_final_trailer_block` | `(message)` | — | [src](../../../core/services/commit_attribution.py#L165) |
| function | `render_attributed_message` | `(message, attribution)` | Replace managed trailers and return a deterministic commit message. | [src](../../../core/services/commit_attribution.py#L180) |

## `core/services/commit_gate_arbiter.py`
_Pre-eksekverings commit-gate arbitrage — udskilt fra visible_runs (Boy Scout, 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CommitGateOutcome` | `` | Udfald af commit-gate-arbitrage. ``blocked`` → værktøjet må ikke køre; ``soft_warn`` → | [src](../../../core/services/commit_gate_arbiter.py#L21) |
| function | `evaluate_commit_gates` | `(*, name, arguments, user_message, session_id, run_id)` | Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér | [src](../../../core/services/commit_gate_arbiter.py#L30) |

## `core/services/communication_guard.py`
_Communication guard — scanner assistant-output for boundary violations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_hard` | `(trigger)` | Er denne trigger en HÅRD blok (afvis besked før send) eller blød | [src](../../../core/services/communication_guard.py#L143) |
| function | `_load` | `()` | — | [src](../../../core/services/communication_guard.py#L160) |
| function | `_save` | `(triggers)` | — | [src](../../../core/services/communication_guard.py#L172) |
| function | `add_trigger` | `(phrase, *, kind=…, reason=…, ttl_turns=…, ttl_hours=…)` | Tilfoj en triggerfrase til guarden. | [src](../../../core/services/communication_guard.py#L177) |
| function | `remove_trigger` | `(phrase)` | Fjern en triggerfrase. Returner True hvis den blev fjernet. | [src](../../../core/services/communication_guard.py#L224) |
| function | `scan` | `(text)` | Skan en tekst for triggerfraser. | [src](../../../core/services/communication_guard.py#L235) |
| function | `_trigger_active` | `(t, now)` | Er en trigger aktiv lige nu (permanent, eller TTL ikke udløbet)? | [src](../../../core/services/communication_guard.py#L282) |
| function | `enforce_outgoing` | `(text)` | Hård-gate for udga°ende assistant-tekst — kaldes FØR afsendelse. | [src](../../../core/services/communication_guard.py#L299) |
| function | `record_breach` | `(channel, removed, *, original=…)` | Log en boundary-breach (hård frase fanget ved kanal-dispatch). | [src](../../../core/services/communication_guard.py#L350) |
| function | `guard_channel_text` | `(text, channel)` | Convenience for kanal-dispatch: scrub hård afslutnings-fraser fra | [src](../../../core/services/communication_guard.py#L374) |
| function | `_active_hard_phrases` | `(now)` | — | [src](../../../core/services/communication_guard.py#L394) |
| function | `scrub_outgoing` | `(text)` | Kanal-backstop: fjern den SÆTNING/linje der indeholder en hård | [src](../../../core/services/communication_guard.py#L402) |
| function | `prompt_section` | `()` | Bygger en høj-salient påmindelse til system-prompten med de aktive | [src](../../../core/services/communication_guard.py#L433) |
| function | `consume_turn` | `()` | Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver | [src](../../../core/services/communication_guard.py#L467) |
| function | `cleanup_expired` | `()` | Rens udloebne TTL-triggers og triggers med ttl_turns <= 0. | [src](../../../core/services/communication_guard.py#L485) |
| function | `_safe_parse_iso` | `(s, now)` | — | [src](../../../core/services/communication_guard.py#L510) |
| function | `list_triggers` | `()` | Returner alle aktive triggers. | [src](../../../core/services/communication_guard.py#L519) |
| function | `active_count` | `()` | Antal aktive triggerfraser (permanente + ikke-udloebne TTL). | [src](../../../core/services/communication_guard.py#L524) |

## `core/services/communication_guard_daemon.py`
_Communication guard daemon — vedligeholder TTL-rydning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_communication_guard_daemon` | `()` | Daemon tick: cleanup expired TTL triggers + log active count. | [src](../../../core/services/communication_guard_daemon.py#L18) |

## `core/services/companion_initiative.py`
_Proaktivitet — Jarvis må dele en tanke uden at blive spurgt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Offer` | `` | — | [src](../../../core/services/companion_initiative.py#L44) |
| method | `Offer.as_dict` | `(self)` | — | [src](../../../core/services/companion_initiative.py#L49) |
| function | `_now` | `()` | — | [src](../../../core/services/companion_initiative.py#L54) |
| function | `_parse` | `(ts)` | — | [src](../../../core/services/companion_initiative.py#L58) |
| function | `_read_journal` | `()` | — | [src](../../../core/services/companion_initiative.py#L69) |
| function | `_write_journal` | `(entries)` | — | [src](../../../core/services/companion_initiative.py#L86) |
| function | `is_quiet_hour` | `(moment)` | Er det tidspunkt hvor en tanke ville vække frem for at nå frem? | [src](../../../core/services/companion_initiative.py#L94) |
| function | `next_quiet_end` | `(moment)` | Hvornår må den stille periode brydes igen. | [src](../../../core/services/companion_initiative.py#L103) |
| function | `_recent_for` | `(user_id, journal)` | — | [src](../../../core/services/companion_initiative.py#L113) |
| function | `check_allowed` | `(user_id, *, now=…)` | Må en tanke sendes lige nu? Ren vurdering — sender ingenting. | [src](../../../core/services/companion_initiative.py#L117) |
| function | `offer_thought` | `(user_id, text, *, title=…, now=…)` | Tilbyd en tanke. Sender kun hvis grænserne tillader det. | [src](../../../core/services/companion_initiative.py#L144) |
| function | `recent_thoughts` | `(user_id, *, limit=…)` | Tankerne, nyeste først — også dem der blev holdt tilbage. | [src](../../../core/services/companion_initiative.py#L184) |

## `core/services/companion_presence.py`
_Livstegn — er Jarvis vågen lige nu, og hvad lavede han sidst?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse` | `(ts)` | — | [src](../../../core/services/companion_presence.py#L29) |
| function | `_last_heartbeat` | `()` | Seneste hjerteslag: hvornår, og hvad det endte med at gøre. | [src](../../../core/services/companion_presence.py#L40) |
| function | `_running_now` | `()` | Er en synlig kørsel i gang? Det er stærkere end et hjerteslag: det | [src](../../../core/services/companion_presence.py#L63) |
| function | `_short` | `(text, limit=…)` | — | [src](../../../core/services/companion_presence.py#L74) |
| function | `build_presence` | `(*, now=…)` | Det ærlige livstegn. Kaster aldrig — men lyver heller aldrig. | [src](../../../core/services/companion_presence.py#L79) |

## `core/services/compass_engine.py`
_Compass Engine — weekly strategic bearing based on open loops and priorities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_update_compass` | `(*, open_loops=…, recent_decisions=…)` | Update compass if >3 days since last update. | [src](../../../core/services/compass_engine.py#L21) |
| function | `build_compass_surface` | `()` | — | [src](../../../core/services/compass_engine.py#L65) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/compass_engine.py#L74) |

## `core/services/completion_satisfaction.py`
_Completion Satisfaction — "det er nok, jeg er tilfreds."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_completion_satisfaction` | `(*, task_outcomes, repetition_on_same_topic=…, user_mood=…)` | — | [src](../../../core/services/completion_satisfaction.py#L8) |
| function | `build_completion_satisfaction_surface` | `()` | — | [src](../../../core/services/completion_satisfaction.py#L45) |
| function | `_publish_completion_satisfaction_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/completion_satisfaction.py#L48) |

## `core/services/composite_tools.py`
_Composite tools — safe self-extension through composition only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose` | `(*, name, description, input_schema, steps, created_by=…)` | Validate and store a proposal. Raises ValueError on invalid input. | [src](../../../core/services/composite_tools.py#L44) |
| function | `approve` | `(name, *, approved_by=…)` | — | [src](../../../core/services/composite_tools.py#L115) |
| function | `revoke` | `(name)` | — | [src](../../../core/services/composite_tools.py#L128) |
| function | `delete` | `(name)` | — | [src](../../../core/services/composite_tools.py#L138) |
| function | `get` | `(name)` | — | [src](../../../core/services/composite_tools.py#L148) |
| function | `list_available` | `(*, status=…)` | — | [src](../../../core/services/composite_tools.py#L152) |
| function | `invoke` | `(name, args)` | Execute an approved composite. Returns {status, steps, result}. | [src](../../../core/services/composite_tools.py#L156) |
| function | `get_stats` | `()` | — | [src](../../../core/services/composite_tools.py#L224) |
| function | `_substitute` | `(value, context)` | — | [src](../../../core/services/composite_tools.py#L237) |
| function | `_resolve_string` | `(s, context)` | Resolve {{...}} templates. | [src](../../../core/services/composite_tools.py#L247) |
| function | `_lookup` | `(path, context)` | — | [src](../../../core/services/composite_tools.py#L267) |

## `core/services/computer_use_policy.py`
_Computer-use-politik (§4.7) — per-bruger on/off for operator/computer-tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_computer_use_tool` | `(name)` | — | [src](../../../core/services/computer_use_policy.py#L25) |
| function | `_load` | `()` | — | [src](../../../core/services/computer_use_policy.py#L30) |
| function | `computer_use_enabled` | `(user_id)` | Default TIL — kun eksplicit fravalg slår fra. | [src](../../../core/services/computer_use_policy.py#L37) |
| function | `set_computer_use` | `(user_id, enabled)` | — | [src](../../../core/services/computer_use_policy.py#L42) |

## `core/services/concept_baseline_tracker.py`
_Concept baseline tracker — Layer 3 of emotion concepts integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cluster_for_concept` | `(concept)` | Look up cluster for a concept. Falls back to UNKNOWN. | [src](../../../core/services/concept_baseline_tracker.py#L19) |
| function | `_tracker_enabled` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L31) |
| function | `_now` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L39) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L43) |
| function | `record_concept_trigger` | `(*, concept, intensity, triggered_at, source)` | Real-time: update per-concept stats when a concept fires. | [src](../../../core/services/concept_baseline_tracker.py#L47) |
| function | `_aggregate_clusters` | `()` | Compute cluster-level share from total_triggers across all concepts. | [src](../../../core/services/concept_baseline_tracker.py#L87) |
| function | `_detect_drift` | `(cluster_stats, per_concept_stats)` | Detect drift signals from current stats. | [src](../../../core/services/concept_baseline_tracker.py#L129) |
| function | `_workspace_dir` | `()` | Return path to Jarvis' shared state directory. Indirected for tests. | [src](../../../core/services/concept_baseline_tracker.py#L156) |
| function | `_write_concept_baseline_md` | `(cluster_stats, per_concept_stats)` | Write auto-managed CONCEPT_BASELINE.md to workspace dir. | [src](../../../core/services/concept_baseline_tracker.py#L162) |
| function | `_propose_identity_update` | `(signal)` | Forward a drift signal to identity_drift_proposer. | [src](../../../core/services/concept_baseline_tracker.py#L210) |
| function | `evaluate_baseline_drift` | `()` | Daily: compute stats, write MD, propose drift updates if stable. | [src](../../../core/services/concept_baseline_tracker.py#L242) |
| function | `build_concept_baseline_surface` | `()` | Read-only: return current state for Mission Control consumption. | [src](../../../core/services/concept_baseline_tracker.py#L300) |

## `core/services/config_drift.py`
_Config-drift-nerve (§7) — fang når DEKLARERET config og RUNTIME-virkelighed er ude af sync._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_declared_port` | `()` | Læs den DEKLAREREDE port DIREKTE fra runtime.json på disk — IKKE in-memory settings. | [src](../../../core/services/config_drift.py#L19) |
| function | `_api_responds` | `(port)` | True hvis NOGET svarer HTTP på 127.0.0.1:port (selv 4xx/5xx = porten lytter). | [src](../../../core/services/config_drift.py#L42) |
| function | `check_port_drift` | `()` | Probe deklareret port + alternativer. drift=True hvis API'en svarer, men IKKE på den | [src](../../../core/services/config_drift.py#L55) |
| function | `observe_config_drift` | `()` | Kør drift-check → observe til Centralen + flag incident hvis drift. Kadence-kaldt. | [src](../../../core/services/config_drift.py#L73) |
| function | `build_config_drift_surface` | `()` | MC-surface — read-only config-drift-projektion. | [src](../../../core/services/config_drift.py#L119) |

## `core/services/conflict_daemon.py`
_Conflict daemon — detects when Jarvis' signals pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_conflict_daemon` | `(snapshot, skip_event_gate=…)` | Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode, | [src](../../../core/services/conflict_daemon.py#L31) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/conflict_daemon.py#L81) |
| function | `_conflict_tension` | `(conflict_type, snapshot)` | Rå spændings-score 0–1 fra rule-based signaler. Ingen LLM. | [src](../../../core/services/conflict_daemon.py#L95) |
| function | `_build_raw_conflict_phrase` | `(conflict_type, snapshot)` | Byg frasen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/conflict_daemon.py#L111) |
| function | `_detect_conflict` | `(snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L121) |
| function | `_generate_conflict_phrase` | `(conflict_type, snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L147) |
| function | `_store_conflict` | `(phrase, conflict_type)` | — | [src](../../../core/services/conflict_daemon.py#L196) |
| function | `get_latest_conflict` | `()` | — | [src](../../../core/services/conflict_daemon.py#L227) |
| function | `build_conflict_surface` | `()` | — | [src](../../../core/services/conflict_daemon.py#L231) |

## `core/services/conflict_prompt_service.py`
_Conflict memory prompt service — surfaces recent conversation conflicts in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_conflict_memory_prompt_section` | `(limit=…)` | Return a prompt section with recent conflict lessons, or None if empty. | [src](../../../core/services/conflict_prompt_service.py#L11) |
| function | `build_conflict_memory_surface` | `(limit=…)` | — | [src](../../../core/services/conflict_prompt_service.py#L37) |

## `core/services/conflict_resolution.py`
_Bounded conflict resolution — deterministic arbitration between competing runtime pressures._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ConflictTrace` | `` | Observable trace of a conflict resolution decision. | [src](../../../core/services/conflict_resolution.py#L29) |
| method | `ConflictTrace.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L40) |
| class | `QuietInitiative` | `` | A quietly held user-facing initiative under maturation. | [src](../../../core/services/conflict_resolution.py#L61) |
| method | `QuietInitiative.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L73) |
| function | `get_quiet_initiative` | `()` | Return the current quiet initiative state for MC observability. | [src](../../../core/services/conflict_resolution.py#L92) |
| function | `_start_quiet_hold` | `(*, focus, reason_code, dominant_factor, decision_type)` | Start or refresh a quiet hold on a user-facing initiative. | [src](../../../core/services/conflict_resolution.py#L97) |
| function | `_expire_quiet_initiative` | `(reason=…)` | Mark the current quiet initiative as expired/released. | [src](../../../core/services/conflict_resolution.py#L126) |
| function | `_promote_quiet_initiative` | `()` | Mark the current quiet initiative as promoted to user-facing. | [src](../../../core/services/conflict_resolution.py#L135) |
| function | `resolve_heartbeat_initiative_conflict` | `(*, decision_type, liveness, question_gate, autonomy_pressure, open_loops, conductor_mode=…, cognitive_frame=…, policy_allow_propose=…, policy_allow_ping=…)` | Resolve competing pressures into a single bounded initiative outcome. | [src](../../../core/services/conflict_resolution.py#L148) |
| function | `apply_conflict_resolution` | `(*, decision, trace)` | Apply conflict resolution outcome to modify the heartbeat decision. | [src](../../../core/services/conflict_resolution.py#L508) |
| function | `get_last_conflict_trace` | `()` | Return the last conflict resolution trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L591) |
| function | `set_last_conflict_trace` | `(trace)` | Store the latest conflict trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L600) |
| function | `build_conflict_resolution_surface` | `()` | — | [src](../../../core/services/conflict_resolution.py#L605) |
| function | `_emit_resolved_event` | `(winning, losing)` | — | [src](../../../core/services/conflict_resolution.py#L614) |

## `core/services/connections.py`
_Connections-cluster — gør forbindelses-LIVSCYKLUSSEN synlig i Den Intelligente Central:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/connections.py#L18) |
| function | `note_presence` | `(user_id, device_key, platform=…, **meta)` | En device-presence-ping (jarvis-desk/mobile companion). Metadata-only. | [src](../../../core/services/connections.py#L26) |
| function | `note_ws` | `(event, client=…, **meta)` | MC-websocket-livscyklus: event ∈ {connected, disconnected, error}. client = host:port. | [src](../../../core/services/connections.py#L35) |
| function | `note_connection_error` | `(client, reason, **meta)` | Forbindelses-FEJL (WS-error, broken pipe, abort). → observe (synlig, ikke severe). | [src](../../../core/services/connections.py#L41) |
| function | `note_unauthorized` | `(user_id, session_id, resource, reason, *, role=…, run_id=…)` | UAUTORISERET adgang (tool-deny / identity-spoof / rate-limit) på en forbindelse → | [src](../../../core/services/connections.py#L46) |
| function | `session_activity` | `(session_id, *, limit=…)` | Forbindelses-debugging pr. session: hvilke tools blev brugt, hvilke FEJLEDE (+ årsag), | [src](../../../core/services/connections.py#L75) |
| function | `active_summary` | `(*, window=…)` | Read-only: hvem/hvad har været forbundet i den seneste trace (til MC/adaptiv-læring). | [src](../../../core/services/connections.py#L112) |

## `core/services/connectors.py`
_Connector-katalog + per-bruger status (v1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_enabled_store` | `()` | — | [src](../../../core/services/connectors.py#L143) |
| function | `is_enabled` | `(user_id, connector_id)` | Default ON; kun False hvis brugeren eksplicit har slået den fra. | [src](../../../core/services/connectors.py#L148) |
| function | `set_enabled` | `(user_id, connector_id, enabled)` | — | [src](../../../core/services/connectors.py#L157) |
| function | `_provider_of` | `(c)` | OAuth-provider for en connector. Google-pakken deler provider='google'. | [src](../../../core/services/connectors.py#L171) |
| function | `_connected` | `(user_id, c)` | — | [src](../../../core/services/connectors.py#L176) |
| function | `oauth_request_for` | `(connector_id)` | Map et connector-id → (oauth_provider, scopes) til /api/oauth/{id}/start. | [src](../../../core/services/connectors.py#L182) |
| function | `list_for_user` | `(user_id)` | Hele kataloget beriget med per-bruger `connected` + `enabled`. | [src](../../../core/services/connectors.py#L194) |
| function | `_audit` | `(event, user_id, connector_id)` | — | [src](../../../core/services/connectors.py#L213) |
| function | `delete_for_user` | `(user_id, connector_id)` | Afbryd & slet: revoke hos provider (best-effort) + lokal token-wipe + ryd flag. | [src](../../../core/services/connectors.py#L221) |

## `core/services/consent_registry.py`
_Consent Registry — user preferences and boundaries that persist across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_file` | `()` | — | [src](../../../core/services/consent_registry.py#L26) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/consent_registry.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/consent_registry.py#L44) |
| function | `_save` | `()` | — | [src](../../../core/services/consent_registry.py#L55) |
| function | `register_consent` | `(*, kind, statement, source_session_id=…, confidence=…)` | Register a user preference or boundary. | [src](../../../core/services/consent_registry.py#L67) |
| function | `revoke_consent` | `(consent_id)` | Mark a consent entry as inactive. | [src](../../../core/services/consent_registry.py#L101) |
| function | `get_active_consents` | `()` | — | [src](../../../core/services/consent_registry.py#L112) |
| function | `build_consent_prompt_section` | `()` | Return a prompt section with active consent entries, or None if empty. | [src](../../../core/services/consent_registry.py#L117) |
| function | `build_consent_registry_surface` | `()` | — | [src](../../../core/services/consent_registry.py#L143) |

## `core/services/consolidation_judge_daemon.py`
_Consolidation Judge Daemon — nightly reckoning, not observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_consolidation_judge_daemon` | `()` | Run the nightly consolidation judge if cadence allows. | [src](../../../core/services/consolidation_judge_daemon.py#L29) |
| function | `_gather_evidence` | `()` | Collect today's operational data for judgment. | [src](../../../core/services/consolidation_judge_daemon.py#L74) |
| function | `_build_stillingtagen` | `(evidence)` | Construct 3-5 concrete stillingtagen (items requiring judgment). | [src](../../../core/services/consolidation_judge_daemon.py#L126) |
| function | `_render_judgments` | `(items, evidence)` | Present each stillingtagen to the LLM and force a verdict. | [src](../../../core/services/consolidation_judge_daemon.py#L207) |
| function | `_parse_judgment` | `(raw, item)` | Parse the LLM's judgment response. | [src](../../../core/services/consolidation_judge_daemon.py#L248) |
| function | `_enforce_judgments` | `(judgments)` | Carry out the concrete actions from judgments. | [src](../../../core/services/consolidation_judge_daemon.py#L279) |
| function | `_enforce_reject` | `(j)` | Handle rejected items — typically revoke or pause. | [src](../../../core/services/consolidation_judge_daemon.py#L289) |
| function | `_enforce_accept` | `(j)` | Handle accepted items — typically recommit or flag. | [src](../../../core/services/consolidation_judge_daemon.py#L322) |
| function | `_record_judgment_session` | `(judgments, evidence)` | Write the full judgment session as a private brain record. | [src](../../../core/services/consolidation_judge_daemon.py#L342) |
| function | `build_consolidation_judge_surface` | `()` | Build surface data for prompt injection. | [src](../../../core/services/consolidation_judge_daemon.py#L377) |
| function | `now_date_str` | `()` | — | [src](../../../core/services/consolidation_judge_daemon.py#L385) |

## `core/services/consolidation_target_signal_tracking.py`
_Consolidation-target signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_consolidation_target_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L41) |
| function | `refresh_runtime_consolidation_target_signal_statuses` | `()` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L51) |
| function | `build_runtime_consolidation_target_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L55) |
| function | `_extract_consolidation_target_candidates` | `(*, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L59) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, chronicle, chronicle_brief, meaning, temperament, self_narrative, relation_continuity)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L179) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L302) |
| function | `_consolidation_target_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L327) |
| function | `_derive_consolidation_state` | `(*, witness_status, chronicle_status, brief_status, active_like_count, session_count)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L349) |
| function | `_derive_consolidation_focus` | `(*, domain_key, chronicle, chronicle_brief)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L364) |
| function | `_derive_consolidation_weight` | `(*, active_like_count, support_count, session_count, brief_status)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L382) |
| function | `_consolidation_summary` | `(*, focus, consolidation_state, consolidation_weight)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L399) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L419) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L426) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L438) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L450) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L461) |

## `core/services/content_blocks.py`
_Rene content-blok-funktioner: tekst-projektion + serve-on-read rekonstruktion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `content_blocks_to_text` | `(blocks)` | Flad en content-blok-array til markdown-tekst-projektionen. KUN text-blokke | [src](../../../core/services/content_blocks.py#L17) |
| function | `reconstruct_blocks_from_legacy` | `(role, content, *, load_result)` | Serve-on-read: byg blok-array for en GAMMEL besked (uden content_json). | [src](../../../core/services/content_blocks.py#L24) |

## `core/services/context_window_manager.py`
_Context window manager — strategies for keeping prompts within budget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_visible_window` | `()` | Resolve the visible lane model's context window in tokens. Fallback 200k. | [src](../../../core/services/context_window_manager.py#L45) |
| function | `_window_scaled_thresholds` | `()` | Compaction target + pressure levels as a fraction of the ACTUAL model window. | [src](../../../core/services/context_window_manager.py#L62) |
| function | `_estimate_session_tokens` | `()` | — | [src](../../../core/services/context_window_manager.py#L90) |
| function | `_list_session_messages` | `(session_id=…, limit=…)` | — | [src](../../../core/services/context_window_manager.py#L98) |
| function | `_is_anchor` | `(message)` | — | [src](../../../core/services/context_window_manager.py#L120) |
| function | `apply_sliding` | `(messages, *, keep_recent=…, preserve_anchors=…)` | Keep last N messages, drop middle. Optionally preserve anchor messages. | [src](../../../core/services/context_window_manager.py#L127) |
| function | `estimate_pressure` | `()` | Read current session size + classify pressure level against the ACTUAL | [src](../../../core/services/context_window_manager.py#L152) |
| function | `degradation_signal` | `()` | Detect signs that long context is hurting performance. | [src](../../../core/services/context_window_manager.py#L177) |
| function | `adaptive_pick_strategy` | `()` | Pick the best strategy for current state. | [src](../../../core/services/context_window_manager.py#L242) |
| function | `context_window_section` | `()` | Awareness-section warning when degradation detected. | [src](../../../core/services/context_window_manager.py#L253) |
| function | `_exec_context_pressure` | `(args)` | — | [src](../../../core/services/context_window_manager.py#L269) |
| function | `_exec_manage_context_window` | `(args)` | Apply a chosen context-management strategy. | [src](../../../core/services/context_window_manager.py#L277) |

## `core/services/continuity.py`
_Continuity Kernel — state capsule + live update + graded wake-up._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/continuity.py#L87) |
| function | `_ensure_dir` | `()` | — | [src](../../../core/services/continuity.py#L91) |
| function | `_truncate_capsule` | `(data)` | Ensure capsule stays under _MAX_CAPSULE_SIZE_BYTES. | [src](../../../core/services/continuity.py#L95) |
| function | `capture_state` | `(*, mood=…, attention=…, relation=…, somatic=…, goals=…, recent_activity=…, workspace_id=…, session_id=…)` | Build a complete state capsule dict from partial inputs. | [src](../../../core/services/continuity.py#L129) |
| function | `write_capsule` | `(capsule)` | Write capsule to disk with rotation. | [src](../../../core/services/continuity.py#L210) |
| function | `sync_capsule_mood` | `()` | Sync capsule mood from mood_oscillator's live state. | [src](../../../core/services/continuity.py#L228) |
| function | `read_capsule` | `()` | Read the latest capsule from disk. | [src](../../../core/services/continuity.py#L278) |
| function | `get_wake_tier` | `(hours_since_last)` | Determine wake tier based on time since last session. | [src](../../../core/services/continuity.py#L296) |
| function | `build_conversation_continuity` | `(*, limit=…)` | Build a 'hvad talte vi om' block from recent session data. | [src](../../../core/services/continuity.py#L308) |
| function | `build_wake_up_block` | `(capsule=…)` | Build the wake-up block for prompt injection. | [src](../../../core/services/continuity.py#L402) |
| function | `live_update_after_turn` | `(*, mood=…, attention=…, relation=…, somatic=…, goals=…, recent_activity=…, session_id=…)` | Call this after every visible turn to persist the state capsule. | [src](../../../core/services/continuity.py#L519) |

## `core/services/continuity_kernel.py`
_Bounded Continuity Kernel — existence feel between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/continuity_kernel.py#L27) |
| function | `record_tick_elapsed` | `(seconds)` | Record elapsed time since last tick and update existence feel. | [src](../../../core/services/continuity_kernel.py#L31) |
| function | `_compute_existence_feeling` | `(gap_seconds)` | Compute existence feeling based on gap duration. | [src](../../../core/services/continuity_kernel.py#L57) |
| function | `_compute_narrative` | `(gap_seconds)` | Compute a narrative description of the gap. | [src](../../../core/services/continuity_kernel.py#L73) |
| function | `get_existence_narrative` | `()` | Get the current existence narrative. | [src](../../../core/services/continuity_kernel.py#L92) |
| function | `get_existence_feeling` | `()` | Get the current existence feeling (0-1). | [src](../../../core/services/continuity_kernel.py#L97) |
| function | `should_express_continuity` | `()` | Determine if continuity should be expressed in visible prompt. | [src](../../../core/services/continuity_kernel.py#L102) |
| function | `get_continuity_state` | `()` | Get full continuity state for debugging/MC. | [src](../../../core/services/continuity_kernel.py#L108) |
| function | `reset_continuity_state` | `()` | Reset continuity state (for testing). | [src](../../../core/services/continuity_kernel.py#L113) |
| function | `format_continuity_for_prompt` | `()` | Format continuity info for heartbeat prompt injection. | [src](../../../core/services/continuity_kernel.py#L127) |
| function | `build_continuity_kernel_surface` | `()` | Build MC surface for continuity kernel. | [src](../../../core/services/continuity_kernel.py#L136) |

## `core/services/contract_evolution.py`
_Contract Evolution — Jarvis proposes changes to his own identity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose_identity_change` | `(*, target_file, proposed_addition, rationale, confidence=…, evidence_count=…)` | Propose a change to SOUL.md, IDENTITY.md, or USER.md. | [src](../../../core/services/contract_evolution.py#L22) |
| function | `approve_proposal` | `(proposal_id)` | Mark a proposal as approved (MC action). | [src](../../../core/services/contract_evolution.py#L57) |
| function | `reject_proposal` | `(proposal_id)` | Mark a proposal as rejected (MC action). | [src](../../../core/services/contract_evolution.py#L70) |
| function | `maybe_propose_identity_evolution` | `()` | Analyze personality vector trends and propose IDENTITY.md changes. | [src](../../../core/services/contract_evolution.py#L83) |
| function | `build_contract_evolution_surface` | `()` | — | [src](../../../core/services/contract_evolution.py#L148) |

## `core/services/contradiction_engine.py`
_Contradiction engine — detect semantic conflicts between commitments and reviews._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/contradiction_engine.py#L44) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/contradiction_engine.py#L48) |
| function | `_has_negation` | `(text)` | — | [src](../../../core/services/contradiction_engine.py#L52) |
| function | `_fetch_active_decisions` | `(*, limit=…)` | Return active behavioral_decisions with their directive text. | [src](../../../core/services/contradiction_engine.py#L56) |
| function | `_fetch_recent_self_reviews` | `(*, hours=…, limit=…)` | Return cognitive_self_reviews from the last `hours` hours. | [src](../../../core/services/contradiction_engine.py#L76) |
| function | `_timedelta` | `(*, hours)` | — | [src](../../../core/services/contradiction_engine.py#L97) |
| function | `_critique_texts_from_review` | `(review)` | Extract per-lesson + next_focus strings as candidate critique texts. | [src](../../../core/services/contradiction_engine.py#L102) |
| function | `detect_contradictions` | `(*, max_findings=…)` | Find semantic contradictions between active decisions and recent reviews. | [src](../../../core/services/contradiction_engine.py#L121) |
| function | `run_contradiction_tick` | `()` | One detection cycle. Publishes contradiction.detected events. | [src](../../../core/services/contradiction_engine.py#L178) |
| function | `build_contradiction_engine_surface` | `(*, limit=…)` | Mission-control/read-surface for semantic contradiction detection. | [src](../../../core/services/contradiction_engine.py#L212) |

## `core/services/contradiction_resolver.py`
_Contradiction resolver (spec 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_meaningful_overlap` | `(finding)` | Overlap-tokens uden stopord og rene tal — kun disse tæller som ægte signal. | [src](../../../core/services/contradiction_resolver.py#L44) |
| function | `_confidence` | `(finding)` | — | [src](../../../core/services/contradiction_resolver.py#L55) |
| function | `pick_survivor` | `(finding)` | Authority-first, recency-tiebreak. Decision og self-review-critique er begge | [src](../../../core/services/contradiction_resolver.py#L64) |
| function | `classify_tier` | `(finding)` | 'auto' | 'escalate'. Escalate naar den tabende beslutning roerer identitet/ | [src](../../../core/services/contradiction_resolver.py#L79) |
| function | `_apply_supersede` | `(decision_id, *, review_id, rule)` | Marker den tabende decision superseded (status-flip, reversibel, aldrig slettet). | [src](../../../core/services/contradiction_resolver.py#L92) |
| function | `revert_supersede` | `(decision_id)` | Owner-reversal (Central-CLI): superseded → active igen. | [src](../../../core/services/contradiction_resolver.py#L121) |
| function | `_write_escalation_proposal` | `(finding, *, rule, seen)` | Escalate-tier: publicer et resolution-FORSLAG (muterer intet). Deduppet pr. | [src](../../../core/services/contradiction_resolver.py#L140) |
| function | `resolve_contradictions` | `(*, live)` | Resolve modsigelser. ``live=True`` muterer (supersede); ``live=False`` er | [src](../../../core/services/contradiction_resolver.py#L162) |
| function | `run_resolver_tick` | `()` | Cadence-indgang. Kaldes gennem central().decide saa Centralen ER aktoeren; gate_enforcement | [src](../../../core/services/contradiction_resolver.py#L200) |
| function | `build_contradiction_resolver_surface` | `(*, limit=…)` | Side-effect-fri read-surface til Central-CLI (jc raw /central/contradictions). | [src](../../../core/services/contradiction_resolver.py#L226) |

## `core/services/conversation_rhythm.py`
_Conversation Rhythm — tracks conversation signature patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_conversation` | `(*, turn_count, correction_count, avg_message_length, duration_minutes, outcome_status)` | Classify the conversation rhythm pattern. | [src](../../../core/services/conversation_rhythm.py#L20) |
| function | `track_conversation_rhythm` | `(*, run_id, session_id=…, turn_count=…, correction_count=…, avg_message_length=…, duration_minutes=…, outcome_status=…)` | Track and classify the conversation rhythm. | [src](../../../core/services/conversation_rhythm.py#L40) |
| function | `build_conversation_rhythm_surface` | `()` | — | [src](../../../core/services/conversation_rhythm.py#L74) |

## `core/services/cost_optimization_daemon.py`
_D5 — Cost optimization daemon._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick` | `()` | Run the cost optimization check cycle. | [src](../../../core/services/cost_optimization_daemon.py#L23) |
| function | `_load_budgets` | `()` | Read cost budget settings from runtime.json `extra` dict. | [src](../../../core/services/cost_optimization_daemon.py#L118) |
| function | `_emit` | `(kind, payload)` | Emit an eventbus event — defensive, never blocks. | [src](../../../core/services/cost_optimization_daemon.py#L133) |
| function | `_emit_savings_estimate` | `()` | Estimate potential savings from routing more calls to cheap lane. | [src](../../../core/services/cost_optimization_daemon.py#L142) |

## `core/services/council_deliberation_controller.py`
_Council Deliberation Controller — active agent dynamics inside deliberation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DeliberationResult` | `` | — | [src](../../../core/services/council_deliberation_controller.py#L28) |
| function | `_cosine_similarity` | `(a, b)` | Bag-of-words cosine similarity between two strings. Returns 0.0–1.0. | [src](../../../core/services/council_deliberation_controller.py#L37) |
| function | `_is_deadlocked` | `(round_outputs)` | Return True if round N is semantically similar to round N-2 (1-indexed rounds). | [src](../../../core/services/council_deliberation_controller.py#L54) |
| function | `_check_witness_escalation` | `(witness_output)` | Return True if the witness is requesting to escalate to active participant. | [src](../../../core/services/council_deliberation_controller.py#L63) |
| function | `build_witness_prompt` | `(*, transcript)` | Build the system prompt for the witness agent. | [src](../../../core/services/council_deliberation_controller.py#L68) |
| function | `_call_recruitment_llm` | `(*, topic, transcript)` | — | [src](../../../core/services/council_deliberation_controller.py#L79) |
| function | `_analyze_recruitment_need` | `(*, topic, transcript, active_members)` | Ask LLM if a new role is needed. Returns role name or None. | [src](../../../core/services/council_deliberation_controller.py#L91) |
| class | `DeliberationController` | `` | Manages a deliberation with witness escalation, recruitment, and deadlock handling. | [src](../../../core/services/council_deliberation_controller.py#L110) |
| method | `DeliberationController.__init__` | `(self, *, topic, members, max_rounds=…)` | — | [src](../../../core/services/council_deliberation_controller.py#L113) |
| method | `DeliberationController.run` | `(self)` | Run the full deliberation. Returns DeliberationResult. | [src](../../../core/services/council_deliberation_controller.py#L130) |
| method | `DeliberationController._run_round` | `(self)` | Run one round of deliberation. Override in subclasses for real agent execution. | [src](../../../core/services/council_deliberation_controller.py#L207) |
| method | `DeliberationController._synthesize` | `(self, *, forced=…)` | Produce council conclusion. Override in real integration. | [src](../../../core/services/council_deliberation_controller.py#L211) |

## `core/services/council_memory_daemon.py`
_Council Memory Daemon — injects relevant past council conclusions into heartbeat context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_council_memory_daemon` | `(*, recent_context=…)` | Check COUNCIL_LOG.md for relevant past deliberations and inject into context. | [src](../../../core/services/council_memory_daemon.py#L23) |
| function | `build_council_memory_surface` | `()` | — | [src](../../../core/services/council_memory_daemon.py#L65) |
| function | `_load_entries` | `()` | — | [src](../../../core/services/council_memory_daemon.py#L75) |
| function | `_call_similarity_llm` | `(*, recent_context, index_text)` | — | [src](../../../core/services/council_memory_daemon.py#L83) |
| function | `_parse_indices` | `(response, max_idx)` | Extract valid 1-based indices from LLM response. Returns [] if 'ingen'. | [src](../../../core/services/council_memory_daemon.py#L95) |
| function | `_format_for_heartbeat` | `(entries)` | Compact representation for heartbeat context injection. | [src](../../../core/services/council_memory_daemon.py#L110) |

## `core/services/council_memory_service.py`
_Council Memory Service — persists council conclusions to COUNCIL_LOG.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_log_file` | `()` | — | [src](../../../core/services/council_memory_service.py#L16) |
| function | `append_council_conclusion` | `(*, topic, score, members, signals, transcript, conclusion, initiative)` | Append a council conclusion entry to COUNCIL_LOG.md. | [src](../../../core/services/council_memory_service.py#L20) |
| function | `read_all_entries` | `()` | Parse COUNCIL_LOG.md and return list of entry dicts. | [src](../../../core/services/council_memory_service.py#L51) |
| function | `_parse_entries` | `(content)` | Parse markdown content into list of entry dicts. | [src](../../../core/services/council_memory_service.py#L64) |
| function | `_parse_single_entry` | `(block)` | Parse a single markdown entry block. | [src](../../../core/services/council_memory_service.py#L78) |
| function | `_extract_section` | `(block, heading)` | Extract text content between a heading and the next heading. | [src](../../../core/services/council_memory_service.py#L122) |
| function | `build_council_memory_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/council_memory_service.py#L129) |

## `core/services/council_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_council_runtime_surface` | `()` | — | [src](../../../core/services/council_runtime.py#L10) |
| function | `_build_council_runtime_surface_uncached` | `()` | — | [src](../../../core/services/council_runtime.py#L18) |
| function | `build_council_runtime_from_sources` | `(*, subagent_ecology, affective_meta_state, epistemic_runtime_state, conflict_trace)` | — | [src](../../../core/services/council_runtime.py#L27) |
| function | `build_council_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/council_runtime.py#L107) |
| function | `_role_position` | `(*, role, affective, epistemic, conflict)` | — | [src](../../../core/services/council_runtime.py#L134) |
| function | `_derive_divergence_level` | `(role_positions)` | — | [src](../../../core/services/council_runtime.py#L177) |
| function | `_derive_recommendation` | `(role_positions)` | — | [src](../../../core/services/council_runtime.py#L188) |
| function | `_derive_recommendation_reason` | `(*, recommendation, divergence_level, affective, epistemic, conflict)` | — | [src](../../../core/services/council_runtime.py#L203) |
| function | `_derive_confidence` | `(*, recommendation, divergence_level, role_positions)` | — | [src](../../../core/services/council_runtime.py#L223) |
| function | `_derive_council_state` | `(*, role_positions, divergence_level)` | — | [src](../../../core/services/council_runtime.py#L237) |
| function | `_source_contributors` | `(*, ecology, affective, epistemic, conflict)` | — | [src](../../../core/services/council_runtime.py#L255) |
| function | `_guidance_for_council` | `(*, state)` | — | [src](../../../core/services/council_runtime.py#L305) |
| function | `_safe_subagent_ecology` | `()` | — | [src](../../../core/services/council_runtime.py#L319) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/council_runtime.py#L329) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/council_runtime.py#L339) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/council_runtime.py#L349) |
| function | `get_latest_council_conclusion` | `()` | Return the most recent closed council session summary, or None. | [src](../../../core/services/council_runtime.py#L359) |

## `core/services/counterfactual_engine.py`
_Counterfactual reflection orchestrator._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run` | `(*, workspace_id=…, dry_run=…)` | One full pipeline cycle. Always returns a summary dict, never raises. | [src](../../../core/services/counterfactual_engine.py#L41) |
| function | `_dry_run_placeholder` | `(trigger)` | Phase 1: every unique trigger becomes a TODO counterfactual. | [src](../../../core/services/counterfactual_engine.py#L245) |
| function | `_failed_generation_placeholder` | `(trigger)` | Phase 2+: when LLM call fails, store with a marker so we can see frequency. | [src](../../../core/services/counterfactual_engine.py#L262) |
| function | `_dedup_filter` | `(triggers)` | Remove triggers whose cf_key is already stored in the DB. | [src](../../../core/services/counterfactual_engine.py#L279) |
| function | `_extract_json_from_llm` | `(text)` | Strip markdown fences and trim to outermost JSON object. | [src](../../../core/services/counterfactual_engine.py#L322) |
| function | `_generate_one_via_llm` | `(trigger)` | Single cheap-lane call to produce structured CF fields for one trigger. | [src](../../../core/services/counterfactual_engine.py#L335) |
| function | `_generate_counterfactuals_via_llm` | `(triggers)` | Phase 2 (2026-05-14): one cheap-lane LLM call per unique trigger. | [src](../../../core/services/counterfactual_engine.py#L389) |
| function | `_count_similar_trigger_events` | `(event_kind, *, window_days=…)` | Count eventbus rows of ``event_kind`` in the last ``window_days``. | [src](../../../core/services/counterfactual_engine.py#L439) |
| function | `_modulate_with_apophenia` | `(counterfactuals)` | Phase 3 (2026-05-14): rate each counterfactual via apophenia_guard. | [src](../../../core/services/counterfactual_engine.py#L461) |
| function | `_store_counterfactual` | `(*, workspace_id, **cf)` | INSERT OR IGNORE — UNIQUE(cf_key) makes this idempotent. | [src](../../../core/services/counterfactual_engine.py#L514) |
| function | `_publish_event` | `(*, cf_id, workspace_id, cluster_size, final_confidence, status, caused_by_trigger_id=…)` | Publish counterfactual event. If caused_by_trigger_id is given, | [src](../../../core/services/counterfactual_engine.py#L540) |
| function | `_publish_cycle_complete` | `(summary)` | — | [src](../../../core/services/counterfactual_engine.py#L571) |
| function | `classify_event_to_counterfactual` | `(event_kind, payload)` | Classify an event into a specific counterfactual, or None if no match. | [src](../../../core/services/counterfactual_engine.py#L637) |
| function | `generate_classified_counterfactual` | `(event_kind, payload)` | Convenience: classify event → persist counterfactual if matched. | [src](../../../core/services/counterfactual_engine.py#L699) |
| function | `generate_counterfactual` | `(*, trigger_type, anchor, source=…, confidence=…, cf_question=…, event_kind=…)` | Generate a counterfactual question from a trigger event. | [src](../../../core/services/counterfactual_engine.py#L719) |
| function | `generate_dream_counterfactual` | `(*, recent_decisions=…)` | Generate a speculative counterfactual during idle time. | [src](../../../core/services/counterfactual_engine.py#L787) |
| function | `narrativize_regret` | `(*, trigger_type, anchor, actual_outcome=…, time_cost=…)` | Turn a regret into a felt narrative, not just data. | [src](../../../core/services/counterfactual_engine.py#L810) |
| function | `narrativize_aspiration` | `(*, trigger_type, anchor, actual_outcome=…, positive_effect=…)` | Turn a success/kept-decision into an aspiration narrative. | [src](../../../core/services/counterfactual_engine.py#L834) |
| function | `build_counterfactual_surface` | `()` | — | [src](../../../core/services/counterfactual_engine.py#L867) |

