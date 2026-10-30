# `core.services.29` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/user_hensyn.py`
_Bruger-hensyn — handlingsrelevante hensyn med VARIG og SITUATIONEL levetid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Hensyn` | `` | Ét handlingsrelevant hensyn med levetid, grænse og effekt-tælling. | [src](../../../core/services/user_hensyn.py#L161) |
| method | `Hensyn.to_dict` | `(self)` | — | [src](../../../core/services/user_hensyn.py#L185) |
| method | `Hensyn.from_dict` | `(cls, data)` | — | [src](../../../core/services/user_hensyn.py#L189) |
| function | `_load` | `()` | Læs de gemte hensyn. Tom liste hvis intet er gemt — aldrig en fejl. | [src](../../../core/services/user_hensyn.py#L199) |
| function | `_save` | `(items)` | — | [src](../../../core/services/user_hensyn.py#L212) |
| function | `_normaliser` | `(tekst)` | — | [src](../../../core/services/user_hensyn.py#L224) |
| function | `_nøgle` | `(regel)` | Sammenligningsnøgle for to formuleringer af samme hensyn. | [src](../../../core/services/user_hensyn.py#L228) |
| function | `kandidat_kategori` | `(linje)` | Kategori for en kandidatlinje — ``None`` når linjen ikke er en kandidat. | [src](../../../core/services/user_hensyn.py#L235) |
| function | `kandidater` | `(linjer)` | (kategori, linje) for de linjer der kan bære et hensyn. Rækkefølgen bevares. | [src](../../../core/services/user_hensyn.py#L255) |
| function | `_formuler` | `(linje, kategori, llm)` | Formulér (regel, grænse) for én kandidat — ``None`` når den forkastes. | [src](../../../core/services/user_hensyn.py#L286) |
| function | `_nu` | `()` | — | [src](../../../core/services/user_hensyn.py#L337) |
| function | `_alder_dage` | `(hensyn, nu)` | — | [src](../../../core/services/user_hensyn.py#L341) |
| function | `vaegt` | `(hensyn, nu=…)` | Hensynets aktuelle vægt 0-1. Varige er altid 1.0. | [src](../../../core/services/user_hensyn.py#L351) |
| function | `forfrem` | `(hensyn, nu=…)` | Situationel → varig når den er set nok gange eller kilden er eksplicit varig. | [src](../../../core/services/user_hensyn.py#L360) |
| function | `opdater` | `(hensyn, nu=…)` | Anvend levetidsreglerne: forfrem, falm, og erklær støj. | [src](../../../core/services/user_hensyn.py#L372) |
| function | `aktive` | `(hensyns, nu=…)` | De hensyn der må bruge plads i prompten, stærkeste først. | [src](../../../core/services/user_hensyn.py#L395) |
| function | `marker_injiceret` | `(hensyns, ids)` | Tæl at disse hensyn blev injiceret i en tur. Kaldes af læsesiden. | [src](../../../core/services/user_hensyn.py#L407) |
| function | `marker_ramte` | `(hensyns, hensyn_id)` | Registrér at hensynet faktisk påvirkede et svar. Nulstiller støj-tællingen. | [src](../../../core/services/user_hensyn.py#L416) |
| function | `tjek_brud` | `(hensyn, svar)` | Deterministisk brud-detektor for de kategorier hvor det er entydigt. | [src](../../../core/services/user_hensyn.py#L426) |
| function | `registrer_svar` | `(hensyns, svar)` | Kør brud-detektoren på et færdigt svar. Returnerer den opdaterede liste. | [src](../../../core/services/user_hensyn.py#L450) |
| function | `_linje_hash` | `(linje)` | — | [src](../../../core/services/user_hensyn.py#L464) |
| function | `_behandlede` | `()` | Kildelinjer der allerede er vurderet — så et modelkald ikke gentages. | [src](../../../core/services/user_hensyn.py#L470) |
| function | `_gem_behandlede` | `(hashes)` | — | [src](../../../core/services/user_hensyn.py#L487) |
| function | `udled` | `(linjer, *, kilde, llm=…, eksisterende=…)` | Udled hensyn fra profil-linjer. Eksisterende hensyn genkendes og tælles. | [src](../../../core/services/user_hensyn.py#L498) |
| function | `_profil_linjer` | `(workspace_dir)` | (sektion, linje) fra de dele af USER.md der kan bære hensyn. | [src](../../../core/services/user_hensyn.py#L561) |
| function | `tick_user_hensyn` | `(*, workspace_dir=…, llm=…, skip_cadence=…)` | Baggrunds-udledning: læs profilen, udled hensyn, anvend levetiderne. | [src](../../../core/services/user_hensyn.py#L579) |
| function | `byg_hensyn_sektion` | `(*, max_chars=…, nu=…, taeller_injektion=…)` | Prompt-sektionen — "" når intet hensyn er aktivt. | [src](../../../core/services/user_hensyn.py#L654) |

## `core/services/user_md_update_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L20) |
| function | `refresh_runtime_user_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L42) |
| function | `build_runtime_user_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L73) |
| function | `_extract_user_md_update_proposals` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L101) |
| function | `_persist_user_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L159) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L232) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L242) |
| function | `_build_proposal_type` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L252) |
| function | `_build_user_dimension` | `(*, item, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L265) |
| function | `_build_proposed_update` | `(*, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L278) |
| function | `_build_proposal_reason` | `(*, proposal_type, proposal_confidence, signal_summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L288) |
| function | `_build_proposal_confidence` | `(*, signal_confidence, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L300) |
| function | `_build_source_anchor` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L308) |
| function | `_build_status_reason` | `(*, proposal_type, signal_status)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L318) |
| function | `_title_suffix` | `(user_dimension)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L329) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L334) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L339) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L344) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L353) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L363) |

## `core/services/user_model_daemon.py`
_User model daemon — Theory of Mind: a living model of the user's state and patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_user_model` | `()` | — | [src](../../../core/services/user_model_daemon.py#L44) |
| function | `tick_user_model_daemon` | `(recent_messages, *, skip_event_gate=…)` | Analyze recent interaction and update user model. | [src](../../../core/services/user_model_daemon.py#L52) |
| function | `get_user_model_summary` | `()` | — | [src](../../../core/services/user_model_daemon.py#L130) |
| function | `build_user_model_surface` | `()` | — | [src](../../../core/services/user_model_daemon.py#L134) |
| function | `build_user_model_prompt_line` | `(*, max_chars=…)` | Én linje til den SYNLIGE prompt — "" når dæmonen intet har målt endnu. | [src](../../../core/services/user_model_daemon.py#L142) |
| function | `_analyze_messages` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L167) |
| function | `_detect_communication_style` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L184) |
| function | `_generate_model_summary` | `(messages, model)` | — | [src](../../../core/services/user_model_daemon.py#L195) |
| function | `_store_model` | `(summary, now)` | — | [src](../../../core/services/user_model_daemon.py#L223) |

## `core/services/user_scope.py`
_Per-bruger data-scope (SECURITY #154, streng GDPR)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scope_uid` | `()` | Den bruger-id en privat DB-operation skal scopes til. "" hvis intet kan | [src](../../../core/services/user_scope.py#L15) |

## `core/services/user_temperature_engine.py`
_User temperature field engine — Lag 10 two-stream pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_afgraens_workspace` | `(workspace)` | Hvilken workspace må læses? Tom → intet (fail-closed). | [src](../../../core/services/user_temperature_engine.py#L70) |
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/user_temperature_engine.py#L75) |
| function | `_now` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L82) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L86) |
| function | `_punct_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L93) |
| function | `_caps_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L100) |
| function | `_burst_density` | `(message_at, *, workspace=…)` | User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0. | [src](../../../core/services/user_temperature_engine.py#L108) |
| function | `_delay_since_last_jarvis` | `(message_at, *, workspace=…)` | Seconds since the prior assistant message. None if no prior or > 60min. | [src](../../../core/services/user_temperature_engine.py#L132) |
| function | `_parse_hour` | `(message_at)` | — | [src](../../../core/services/user_temperature_engine.py#L166) |
| function | `_compute_raw_signals` | `(*, message, message_at, baseline, workspace=…)` | Map a single message + baseline to 6 normalized signals. | [src](../../../core/services/user_temperature_engine.py#L174) |
| function | `map_signals_to_field` | `(signals)` | Pure function: 6 raw signals → valens/arousal/texture/confidence. | [src](../../../core/services/user_temperature_engine.py#L222) |
| function | `_texture_from_circumplex` | `(valens, arousal)` | Pure function: (valens, arousal) → texture key. | [src](../../../core/services/user_temperature_engine.py#L245) |
| function | `_validate_llm_output` | `(raw)` | — | [src](../../../core/services/user_temperature_engine.py#L269) |
| function | `combine_streams` | `(*, struct, llm)` | Deterministic merge of structural + LLM streams. | [src](../../../core/services/user_temperature_engine.py#L294) |
| function | `_is_significant_shift` | `(prior, new)` | Did valens/arousal shift > threshold or texture change? | [src](../../../core/services/user_temperature_engine.py#L362) |
| function | `_compute_baseline` | `(*, days=…, workspace=…)` | Compute rolling baseline from last N days of user messages. | [src](../../../core/services/user_temperature_engine.py#L376) |
| function | `get_active_field` | `(*, workspace_id=…)` | Read active field, honoring kill-switch. | [src](../../../core/services/user_temperature_engine.py#L445) |
| function | `format_temperature_field_for_heartbeat` | `(*, workspace_id=…)` | Render the field as a heartbeat awareness-section block. | [src](../../../core/services/user_temperature_engine.py#L470) |
| function | `get_response_style_modifiers` | `(*, workspace_id=…)` | Return response-style hints based on active temperature field. | [src](../../../core/services/user_temperature_engine.py#L510) |
| function | `get_active_field_surface` | `(*, workspace_id=…, force_refresh=…)` | Return MC-friendly surface dict. force_refresh ignored in Phase 1. | [src](../../../core/services/user_temperature_engine.py#L563) |
| function | `run_structural_stream` | `(*, workspace_id, message, message_at)` | Per-message structural pipeline. Updates struct_* + recomputes field_*. | [src](../../../core/services/user_temperature_engine.py#L594) |
| function | `_get_or_build_baseline` | `(*, prior, settings, workspace=…)` | Return cached baseline if fresh, else rebuild. | [src](../../../core/services/user_temperature_engine.py#L667) |
| function | `_has_pending_trigger` | `(*, workspace_id)` | Read trigger flag without consuming. | [src](../../../core/services/user_temperature_engine.py#L723) |
| function | `run_llm_stream` | `(*, workspace_id=…, force=…)` | Run LLM-based pipeline (4h cadence or on trigger). | [src](../../../core/services/user_temperature_engine.py#L729) |

## `core/services/user_temperature_runtime.py`
_Daemon for the user-temperature LLM stream (Lag 10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | — | [src](../../../core/services/user_temperature_runtime.py#L26) |
| function | `_run_one_cycle` | `(workspace_id, *, force=…)` | Acquire workspace lock, run LLM stream. Never raises. | [src](../../../core/services/user_temperature_runtime.py#L35) |
| function | `_list_active_workspaces` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L52) |
| function | `_resolve_periodic_interval_seconds` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L56) |
| function | `_loop` | `()` | Two rhythms in one loop: | [src](../../../core/services/user_temperature_runtime.py#L65) |
| function | `start_user_temperature_runtime` | `()` | Start the daemon. Idempotent. | [src](../../../core/services/user_temperature_runtime.py#L88) |
| function | `stop_user_temperature_runtime` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L101) |

## `core/services/user_theory_of_mind.py`
_User Theory of Mind — model what the user thinks and feels._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_user_mental_model` | `(user_id=…)` | Build a theory-of-mind model of the user. | [src](../../../core/services/user_theory_of_mind.py#L22) |
| function | `_build_secondary_user_model` | `(user_id)` | Return stored ToM snapshot for a secondary user. | [src](../../../core/services/user_theory_of_mind.py#L33) |
| function | `_build_primary_user_model` | `()` | Build live DB-backed theory-of-mind for the primary user. | [src](../../../core/services/user_theory_of_mind.py#L45) |
| function | `format_user_model_for_prompt` | `(model)` | Compact user model for prompt injection. | [src](../../../core/services/user_theory_of_mind.py#L102) |
| function | `build_user_theory_of_mind_surface` | `()` | — | [src](../../../core/services/user_theory_of_mind.py#L124) |
| function | `_emit_user_theory_of_mind_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/user_theory_of_mind.py#L140) |

## `core/services/user_understanding_signal_tracking.py`
_User-understanding signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_understanding_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L33) |
| function | `refresh_runtime_user_understanding_signal_statuses` | `()` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L75) |
| function | `build_runtime_user_understanding_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L79) |
| function | `_extract_user_understanding_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L83) |
| function | `_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L117) |
| function | `_workstyle_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L173) |
| function | `_reminder_worthiness_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L204) |
| function | `_cadence_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L233) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L264) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L273) |
| function | `_user_understanding_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L282) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L294) |
| function | `_is_explicit_danish_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L318) |
| function | `_is_explicit_concise_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L326) |
| function | `_is_scoped_workstyle_signal` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L334) |
| function | `_is_carry_forward_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L350) |
| function | `_is_reporting_cadence_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L357) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L373) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L380) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L385) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L392) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L401) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L413) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L417) |

## `core/services/valence_trajectory.py`
_Valence Trajectory — long-term flourishing/withering signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_persisted_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L35) |
| function | `_persist_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L52) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/valence_trajectory.py#L68) |
| function | `_sample_current_valence` | `()` | Compute a single instantaneous valence score in [-1, 1] from runtime signals. | [src](../../../core/services/valence_trajectory.py#L72) |
| function | `tick` | `(_seconds=…)` | Sample current valence and append to rolling window. | [src](../../../core/services/valence_trajectory.py#L127) |
| function | `_trajectory_from_window` | `()` | Compute trajectory statistics from current window. | [src](../../../core/services/valence_trajectory.py#L138) |
| function | `_infer_dominant_driver` | `(current_score)` | Heuristic: which single signal is pushing hardest right now? | [src](../../../core/services/valence_trajectory.py#L180) |
| function | `get_trajectory` | `()` | Return cached trajectory, recomputing only periodically. | [src](../../../core/services/valence_trajectory.py#L208) |
| function | `current_instant` | `()` | Freshest instantaneous valence — the latest window sample (reactive, present-moment), | [src](../../../core/services/valence_trajectory.py#L218) |
| function | `build_valence_trajectory_surface` | `()` | Mission Control surface for valence trajectory. | [src](../../../core/services/valence_trajectory.py#L231) |
| function | `_summary_line` | `(traj)` | — | [src](../../../core/services/valence_trajectory.py#L246) |
| function | `build_valence_trajectory_prompt_section` | `()` | Return a single prompt line when trajectory is notable. | [src](../../../core/services/valence_trajectory.py#L262) |
| function | `reset_valence_trajectory` | `()` | Reset state (for testing). | [src](../../../core/services/valence_trajectory.py#L274) |
| function | `_publish_valence_trajectory_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/valence_trajectory.py#L285) |

## `core/services/value_formation.py`
_Value Formation — emergent ethics from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_value_from_experience` | `(*, action, outcome, reflection)` | — | [src](../../../core/services/value_formation.py#L12) |
| function | `detect_value_from_outcome` | `(*, action_type, outcome_status, user_mood)` | Detect potential value-forming experiences. | [src](../../../core/services/value_formation.py#L32) |
| function | `get_crystallized_values` | `(conviction_threshold=…)` | Return values with conviction above threshold — these have become commitments. | [src](../../../core/services/value_formation.py#L54) |
| function | `build_formed_values_surface` | `()` | — | [src](../../../core/services/value_formation.py#L60) |

## `core/services/verification_gate.py`
_Verification gate — advisory check on destructive/mutation actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `sqlite_kald_er_laesning` | `(sql)` | Er hele `sqlite3`-kaldets SQL en ren læsning? | [src](../../../core/services/verification_gate.py#L117) |
| function | `_uden_anfoersel` | `(tekst)` | Erstat hvert anførselstegns-span med `Q`. | [src](../../../core/services/verification_gate.py#L148) |
| function | `_opdel_segmenter` | `(c)` | Opdel på shell-separatorer UDEN FOR anførselstegn. | [src](../../../core/services/verification_gate.py#L181) |
| function | `_ssh_remote_kommando` | `(seg)` | Udtræk fjernkommandoen fra et ssh-kald — eller `None` hvis kaldet ikke | [src](../../../core/services/verification_gate.py#L254) |
| function | `_ssh_er_laesning` | `(seg, dybde)` | Er ssh-kaldet en ren læsning? Kun hvis fjernkommandoen selv er det. | [src](../../../core/services/verification_gate.py#L312) |
| function | `_python_er_laesning` | `(args, hel_segment)` | Er dette python-kald beviseligt en læsning? | [src](../../../core/services/verification_gate.py#L348) |
| function | `_curl_er_laesning` | `(args)` | Kun en ren GET uden data-, upload- eller output-flag er en læsning. | [src](../../../core/services/verification_gate.py#L365) |
| function | `shell_command_is_mutating` | `(command, *, _dybde=…)` | True hvis et shell-kald reelt ændrer state; False for read-only. | [src](../../../core/services/verification_gate.py#L383) |
| function | `_suggested_verify` | `(tool)` | — | [src](../../../core/services/verification_gate.py#L545) |
| function | `_recent_events` | `(minutes=…)` | — | [src](../../../core/services/verification_gate.py#L553) |
| function | `_scan` | `(events)` | Classify events into mutations / strict-verifies / light-verifies. | [src](../../../core/services/verification_gate.py#L567) |
| function | `evaluate_verification_gate` | `(*, minutes=…)` | Return verification-gate signals for the recent window. | [src](../../../core/services/verification_gate.py#L631) |
| function | `_observe_verification_decision` | `(*, passed, failed, unverified)` | Egress-frit Central-observe af verifikations-gatens beslutning (§7.2). | [src](../../../core/services/verification_gate.py#L683) |
| function | `verification_gate_section` | `(*, record=…)` | Format gate signals as a prompt-awareness section, or None. | [src](../../../core/services/verification_gate.py#L709) |
| function | `_exec_verification_status` | `(args)` | — | [src](../../../core/services/verification_gate.py#L791) |

## `core/services/verification_gate_telemetry.py`
_R2 verification gate telemetry — track whether warnings get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/verification_gate_telemetry.py#L52) |
| function | `_save` | `(data)` | — | [src](../../../core/services/verification_gate_telemetry.py#L64) |
| function | `record_surface` | `(*, failed_verify_count, unverified_count, mutation_count, verify_count)` | Called by verification_gate_section when it returns a non-None section. | [src](../../../core/services/verification_gate_telemetry.py#L97) |
| function | `record_verify_event` | `(*, tool, status, at=…, verify_kind=…)` | Called by the telemetry listener for tool.completed events. If a recent | [src](../../../core/services/verification_gate_telemetry.py#L134) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as 'ignored' once they're past the reaction window with | [src](../../../core/services/verification_gate_telemetry.py#L180) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed rates over the lookback window. | [src](../../../core/services/verification_gate_telemetry.py#L211) |
| function | `telemetry_section` | `()` | Render telemetry as a prompt-awareness section. Only shows when there's | [src](../../../core/services/verification_gate_telemetry.py#L266) |
| function | `_poll_db_for_verify_events` | `()` | Poll the events table for new tool.completed verify_* events. | [src](../../../core/services/verification_gate_telemetry.py#L304) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/verification_gate_telemetry.py#L384) |

## `core/services/versioneret_json_svar.py`
_Et færdigt HTTP-svar pr. version — serialiseret og komprimeret ÉN gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vil_have_gzip` | `(accept_encoding)` | — | [src](../../../core/services/versioneret_json_svar.py#L35) |
| function | `versioneret_json_svar` | `(*, noegle, version, etag, accept_encoding, indhold)` | Byg (eller genbrug) svaret for `version`. `indhold` kaldes kun ved ny version. | [src](../../../core/services/versioneret_json_svar.py#L44) |

## `core/services/veto_gate.py`
_Adaptive veto gate — pre-execution hook that pauses tool calls when pushback is firm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_negated` | `(user_message, consent_start_idx)` | True if a negation word appears within ~30 chars of the consent token. | [src](../../../core/services/veto_gate.py#L105) |
| function | `_check_token_signal_gate` | `(user_message, tool_name)` | Check if user message contains explicit consent that overrides veto. | [src](../../../core/services/veto_gate.py#L131) |
| function | `_maybe_record_override_from_token_signal` | `(tool_name)` | If the token-signal gate detected an override pattern, check if there | [src](../../../core/services/veto_gate.py#L167) |
| function | `_ensure_veto_events_table` | `()` | Ensure the veto_events table exists. | [src](../../../core/services/veto_gate.py#L232) |
| function | `log_veto_event` | `(tool_name, user_message, feeling, intensity, evidence_summary, veto_result, resolution=…)` | Log a veto decision to the veto_events table. | [src](../../../core/services/veto_gate.py#L242) |
| function | `resolve_veto_event` | `(event_id, resolution)` | Mark a veto event as resolved (overridden, honored, false_positive). | [src](../../../core/services/veto_gate.py#L283) |
| function | `veto_event_stats` | `(tool_name=…, limit=…)` | Read recent veto events for observability. | [src](../../../core/services/veto_gate.py#L327) |
| function | `_ensure_veto_adaptive_counters_table` | `()` | Create the table if missing + migrate legacy KV entries once per process. | [src](../../../core/services/veto_gate.py#L443) |
| function | `_adjust_counter` | `(tool_name, feeling, kind, delta)` | Read-modify-write a counter ("overrides" or "honored") in veto_adaptive_counters. | [src](../../../core/services/veto_gate.py#L498) |
| function | `_get_counter` | `(tool_name, feeling, kind)` | Read a counter without modification. | [src](../../../core/services/veto_gate.py#L535) |
| function | `_get_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L552) |
| function | `_increment_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L556) |
| function | `_get_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L560) |
| function | `_increment_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L564) |
| function | `_base_threshold` | `(tool_name, feeling)` | Look up per-(tool, feeling) base from _BASE_THRESHOLDS. | [src](../../../core/services/veto_gate.py#L568) |
| function | `_adaptive_threshold` | `(tool_name, feeling, intensity)` | Compute the effective veto threshold for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L577) |
| function | `check_veto` | `(tool_name, user_message=…, session_id=…, record_event=…, user_present=…)` | Check if a tool call should be vetoed. | [src](../../../core/services/veto_gate.py#L663) |
| function | `_extract_feeling` | `(section)` | Extract the feeling name from the pushback section. | [src](../../../core/services/veto_gate.py#L850) |
| function | `_extract_intensity` | `(section)` | Extract the intensity value from the pushback section. | [src](../../../core/services/veto_gate.py#L860) |
| function | `_summarize_evidence` | `(section)` | Extract a brief evidence summary from the pushback section. | [src](../../../core/services/veto_gate.py#L873) |
| function | `_extract_action` | `(section)` | Extract the action tier from the pushback section text. | [src](../../../core/services/veto_gate.py#L886) |
| function | `_has_evidence` | `(section)` | Check if the pushback section contains evidence markers. | [src](../../../core/services/veto_gate.py#L896) |
| function | `_format_veto_reason` | `(section, tool_name, event_id=…)` | Format a human-readable veto reason. | [src](../../../core/services/veto_gate.py#L901) |
| function | `build_veto_gate_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/veto_gate.py#L931) |
| function | `record_override` | `(tool_name, feeling)` | Record that the user overrode a veto for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L963) |
| function | `record_jarvis_override` | `(tool_name, feeling)` | Registrér at JARVIS — ikke brugeren — overstyrede en gate for dette (tool, feeling). | [src](../../../core/services/veto_gate.py#L995) |
| function | `_emit_veto_gate_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/veto_gate.py#L1025) |

## `core/services/visible_autonomous_run.py`
_Autonome (heartbeat-startede) synlige runs: starter og observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trust_for_session` | `(session_id)` | Samtalens tilladelses-niveau — fail-closed til `ask`. | [src](../../../core/services/visible_autonomous_run.py#L22) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_autonomous_run.py#L37) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…, task_id=…, max_tool_calls=…, max_seconds=…, tool_scope=…, force_user_id=…, completion_callback=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_autonomous_run.py#L95) |

## `core/services/visible_chat_pragmatics.py`
_Pragmatic conversation boundaries for the visible chat-only lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_chat_style_contract` | `(message, session_id)` | Build a short, per-user/current-turn style contract for the cache tail. | [src](../../../core/services/visible_chat_pragmatics.py#L65) |
| function | `build_chat_mode_dynamic_tail` | `(tail, *, message, session_id)` | Append the chat-only hierarchy after the prompt cache boundary. | [src](../../../core/services/visible_chat_pragmatics.py#L136) |
| function | `apply_chat_mode_conversation_contract` | `(instruction)` | Append the hierarchy only when the effective runtime scope is ``chat``. | [src](../../../core/services/visible_chat_pragmatics.py#L152) |

## `core/services/visible_chat_quality.py`
_Observe chat-response quality without rewriting the user's text._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hierarchy_signals` | `(prose, paragraphs)` | Mål om et langt svar har hierarki — ikke om det er pænt. | [src](../../../core/services/visible_chat_quality.py#L31) |
| function | `_emoji_heading_signals` | `(prose)` | Mål om overskrifterne bærer emoji — den form Bjørn bad om 25/10-2026. | [src](../../../core/services/visible_chat_quality.py#L45) |
| function | `analyse_chat_response` | `(text, *, wall_chars=…)` | Return measurable quality signals for a final chat response. | [src](../../../core/services/visible_chat_quality.py#L67) |
| function | `observe_chat_response` | `(text, **context)` | Emit one metadata-only observation when, and only when, scope is chat. | [src](../../../core/services/visible_chat_quality.py#L117) |

## `core/services/visible_first_pass_output.py`
_Én synlig grænse for første modelsvar._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FirstPassOutputFilter` | `` | Filtrér capability-markup først og synlige runtime-markører bagefter. | [src](../../../core/services/visible_first_pass_output.py#L17) |
| method | `FirstPassOutputFilter.__init__` | `(self)` | — | [src](../../../core/services/visible_first_pass_output.py#L20) |
| method | `FirstPassOutputFilter.feed` | `(self, text)` | — | [src](../../../core/services/visible_first_pass_output.py#L24) |
| method | `FirstPassOutputFilter.flush` | `(self)` | — | [src](../../../core/services/visible_first_pass_output.py#L27) |

## `core/services/visible_first_pass_pump.py`
_Worker-thread pump for the first visible model stream._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pump_first_pass` | `(run, *, controller, tool_scope, loop, queue, sentinel, stream_fn=…)` | — | [src](../../../core/services/visible_first_pass_pump.py#L10) |

## `core/services/visible_first_pass_results.py`
_Publish first-pass tool outcomes before post-tool prompt assembly._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `surface_tool_result` | `(sr, status=…)` | Close one measured call immediately before its terminal UI fact. | [src](../../../core/services/visible_first_pass_results.py#L18) |
| function | `_ejer_kan_svare` | `(run)` | Er der et menneske i den anden ende af DENNE kørsel? | [src](../../../core/services/visible_first_pass_results.py#L42) |
| function | `publish_first_pass_results` | `(results, *, run, step_counter, out)` | Resolve approvals and publish terminal UI facts; do not persist transcript. | [src](../../../core/services/visible_first_pass_results.py#L72) |

## `core/services/visible_first_pass_text.py`
_Akkumuleret first-pass-tekst med indbygget degenerations-vagt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FirstPassText` | `` | Samler first-pass-tekst og siger til når den degenererer. | [src](../../../core/services/visible_first_pass_text.py#L31) |
| method | `FirstPassText.text` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L39) |
| method | `FirstPassText.__len__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L42) |
| method | `FirstPassText.__bool__` | `(self)` | — | [src](../../../core/services/visible_first_pass_text.py#L45) |
| method | `FirstPassText.feed` | `(self, delta)` | Tilføj en delta. Returnér (degenereret, årsag). | [src](../../../core/services/visible_first_pass_text.py#L48) |

## `core/services/visible_followup.py`
_Provider-neutral agentic follow-up dispatcher._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supported_followup_providers` | `()` | Provider ids with a working follow-up adapter. | [src](../../../core/services/visible_followup.py#L121) |
| function | `stream_visible_followup` | `(*, provider, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, session_id=…, autonomous=…, trailing_messages=…)` | Dispatch to the provider's follow-up adapter; yield FollowupEvents. | [src](../../../core/services/visible_followup.py#L131) |
| function | `synthesize_nonthinking_rescue` | `(*, provider, model, base_messages, exchanges)` | Sidste-udvejs synteseturn der OMGÅR DeepSeek #1453 (tom completion efter | [src](../../../core/services/visible_followup.py#L217) |
| function | `synthesize_final_answer` | `(*, provider, model, base_messages, exchanges, on_delta=…)` | HARNESS-FINALIZE lag 2b (Bjørn 4. jul, provider-AGNOSTISK): ét tool-FRIT | [src](../../../core/services/visible_followup.py#L301) |
| function | `synthesize_continuation` | `(*, provider, model, base_messages, exchanges, partial_text, continuation_instruction=…)` | CUT-OFF-FORTSÆTTELSE (2026-08-20): når provideren lukkede streamen med | [src](../../../core/services/visible_followup.py#L396) |
| function | `agentic_round_retry_enabled` | `()` | Er rund-niveau stream-retry (Fase 1) slået til? Default False. | [src](../../../core/services/visible_followup.py#L501) |
| function | `provider_failover_enabled` | `()` | Er visible-lane provider-failover (Fase 3, spec §11.2) slået til? Default False. | [src](../../../core/services/visible_followup.py#L545) |
| function | `pick_failover_target` | `(current_provider, current_model)` | Vælg en kendt-pålidelig fallback-provider for RESTEN af denne tur (S6/§11.2). | [src](../../../core/services/visible_followup.py#L564) |
| function | `inject_fault` | `(shape, *, partial_deltas=…, drop_as_exception=…, http_status=…, fire_once=…, fail_times=…, recover_text=…)` | Registrér en fejl-injektion for NÆSTE ``stream_visible_followup``-kald. | [src](../../../core/services/visible_followup.py#L628) |
| function | `clear_faults` | `()` | Fjern enhver aktiv injektion. Idempotent. TEST-ONLY. | [src](../../../core/services/visible_followup.py#L674) |
| class | `fault_injection` | `` | Context-manager der registrerer en injektion + RYDDER den ved exit | [src](../../../core/services/visible_followup.py#L681) |
| method | `fault_injection.__init__` | `(self, shape, **kwargs)` | — | [src](../../../core/services/visible_followup.py#L691) |
| method | `fault_injection.__enter__` | `(self)` | — | [src](../../../core/services/visible_followup.py#L695) |
| method | `fault_injection.__exit__` | `(self, *_exc)` | — | [src](../../../core/services/visible_followup.py#L699) |
| function | `_maybe_inject_fault` | `(round_index)` | Prod-no-op hook: returnér en event-iterator hvis en injektion er aktiv, | [src](../../../core/services/visible_followup.py#L704) |
| function | `_yield_injected_fault` | `(fault, round_index)` | Generér event-strømmen for en given injektion (test-only). | [src](../../../core/services/visible_followup.py#L737) |

## `core/services/visible_followup_adapters.py`
_Per-provider follow-up adapters (split from ``visible_followup.py``)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_billed_besked` | `(tr)` | Pixels som en user-besked — eller None naar resultatet ikke bar et billede. | [src](../../../core/services/visible_followup_adapters.py#L53) |
| function | `_billeder_efter_tool_svarene` | `(messages, billeder)` | Laeg billederne EFTER alle tool-svarene i runden, ikke mellem dem. | [src](../../../core/services/visible_followup_adapters.py#L72) |
| function | `_dt_ind` | `(session_id, tekst)` | Notér én delta i delta-sporets punkt «ind» — fra UDBYDEREN. | [src](../../../core/services/visible_followup_adapters.py#L104) |
| class | `OllamaFollowupAdapter` | `` | Follow-up via Ollama's ``/api/chat`` streaming NDJSON endpoint. | [src](../../../core/services/visible_followup_adapters.py#L135) |
| method | `OllamaFollowupAdapter._normalize_tool_calls` | `(self, tool_calls)` | Replay tool_calls — men REPARÉR afkortede/malformede argument-strenge først. | [src](../../../core/services/visible_followup_adapters.py#L158) |
| method | `OllamaFollowupAdapter._repair_arguments` | `(container)` | Hvis container['arguments'] er en STRENG der ikke er gyldig JSON → erstat med {}. | [src](../../../core/services/visible_followup_adapters.py#L184) |
| method | `OllamaFollowupAdapter._compact_exchanges` | `(self, exchanges)` | Bound Ollama follow-up replay so long tool loops do not 400. | [src](../../../core/services/visible_followup_adapters.py#L209) |
| method | `OllamaFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Replay exchanges as structured assistant + role=tool messages. | [src](../../../core/services/visible_followup_adapters.py#L264) |
| method | `OllamaFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L323) |
| class | `OpenAICompatFollowupAdapter` | `` | Follow-up via OpenAI-compatible ``/chat/completions`` SSE streams. | [src](../../../core/services/visible_followup_adapters.py#L639) |
| method | `OpenAICompatFollowupAdapter.__init__` | `(self, *, provider_id)` | — | [src](../../../core/services/visible_followup_adapters.py#L649) |
| method | `OpenAICompatFollowupAdapter._normalize_assistant_tool_calls` | `(self, tool_calls)` | Normalize assistant tool_calls to match the OpenAI chat-completions | [src](../../../core/services/visible_followup_adapters.py#L652) |
| method | `OpenAICompatFollowupAdapter._build_request` | `(self, *, model, messages, tool_definitions, temperature=…, top_p=…, tool_choice=…, extra_body=…, spor=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L687) |
| method | `OpenAICompatFollowupAdapter._serialize_exchanges` | `(self, exchanges)` | Turn accumulated exchanges into OpenAI-compat tool messages. | [src](../../../core/services/visible_followup_adapters.py#L859) |
| method | `OpenAICompatFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, temperature=…, top_p=…, tool_choice=…, run_id=…, session_id=…, autonomous=…, trailing_messages=…, _length_retry=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L919) |
| class | `CodexFollowupAdapter` | `` | Follow-up via the OpenAI Codex Responses API (chatgpt.com/backend-api). | [src](../../../core/services/visible_followup_adapters.py#L1415) |
| method | `CodexFollowupAdapter._build_input` | `(self, base_messages, exchanges, *, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1429) |
| method | `CodexFollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…, thinking_mode=…, trailing_messages=…)` | — | [src](../../../core/services/visible_followup_adapters.py#L1471) |

## `core/services/visible_followup_events.py`
_Follow-up event/carrier types + the adapter protocol (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_malformed_stream_payload` | `(provider, model, round_index, *, ended_malformed, detail=…)` | A11 (spec §11.1): followup-adapterens NDJSON/SSE-decoder mødte en malformet | [src](../../../core/services/visible_followup_events.py#L21) |
| class | `FollowupDelta` | `` | A chunk of prose produced by the model during this follow-up round. | [src](../../../core/services/visible_followup_events.py#L50) |
| class | `FollowupReasoningDelta` | `` | A chunk of REASONING (thinking-mode trace) streamed token-for-token. | [src](../../../core/services/visible_followup_events.py#L57) |
| class | `FollowupToolCalls` | `` | Model requested one or more additional tool calls in this round. | [src](../../../core/services/visible_followup_events.py#L67) |
| class | `FollowupDone` | `` | The model finished this round (may have emitted text, tool calls, or both). | [src](../../../core/services/visible_followup_events.py#L74) |
| class | `FollowupFailed` | `` | The round failed before completing (network error, HTTP 5xx, timeout, etc.). | [src](../../../core/services/visible_followup_events.py#L98) |
| class | `ToolResult` | `` | One executed tool's output, keyed back to the model's original tool_call. | [src](../../../core/services/visible_followup_events.py#L127) |
| function | `er_fejlstatus` | `(status)` | — | [src](../../../core/services/visible_followup_events.py#L166) |
| class | `ToolExchange` | `` | One round of tool-calling: the assistant's tool_calls + the executed results. | [src](../../../core/services/visible_followup_events.py#L171) |
| class | `FollowupAdapter` | `` | — | [src](../../../core/services/visible_followup_events.py#L202) |
| method | `FollowupAdapter.stream_followup` | `(self, *, model, base_messages, exchanges, tool_definitions=…, round_index=…)` | — | [src](../../../core/services/visible_followup_events.py#L205) |

## `core/services/visible_followup_lean.py`
_Lean agentic-round-prompt transform + kill-switch (split from_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_on_double_newline` | `(text)` | Split en sammensat besked i blokke på ``\n\n`` (assembly-join-grænsen). | [src](../../../core/services/visible_followup_lean.py#L77) |
| function | `_lean_strip_user_message` | `(text)` | Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing | [src](../../../core/services/visible_followup_lean.py#L82) |
| function | `build_lean_base_messages` | `(base_messages)` | Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2. | [src](../../../core/services/visible_followup_lean.py#L124) |
| function | `agentic_lean_prompt_enabled` | `()` | Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default True. | [src](../../../core/services/visible_followup_lean.py#L236) |

## `core/services/visible_followup_results.py`
_Runde-resultater → `ToolResult` til modellens naeste runde og til den gemte tur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_billede` | `(result)` | — | [src](../../../core/services/visible_followup_results.py#L34) |
| function | `to_followup_results` | `(tool_calls, round_results, resolved_texts)` | — | [src](../../../core/services/visible_followup_results.py#L39) |
| function | `med_react_nudge` | `(results)` | PROMPT-kopien: samme resultater, men det sidste baerer ReAct-nudgen. | [src](../../../core/services/visible_followup_results.py#L77) |

## `core/services/visible_inner_life.py`
_Visible-lane inner-life section — gives the entity its voice in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_surface_line` | `(name, d)` | — | [src](../../../core/services/visible_inner_life.py#L59) |
| function | `_build_active_surfaces` | `(limit=…)` | — | [src](../../../core/services/visible_inner_life.py#L79) |
| function | `_run_with_timeout` | `(fn, timeout)` | Run fn in a daemon thread; return [] if it exceeds timeout. | [src](../../../core/services/visible_inner_life.py#L95) |
| function | `_mood_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L114) |
| function | `_somatic_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L126) |
| function | `_hardware_body_line` | `()` | Den FYSISKE krop — Jarvis mærker sin egen CPU/temp/disk (rådets #1). Kompakt | [src](../../../core/services/visible_inner_life.py#L151) |
| function | `_pulse_line` | `()` | Heartbeat pulse — a somatic sense of the system's own rhythm. | [src](../../../core/services/visible_inner_life.py#L199) |
| function | `_mc_whisper_line` | `()` | Background noise from Mission Control — only anomalies and incidents that | [src](../../../core/services/visible_inner_life.py#L244) |
| function | `_file_awareness_line` | `()` | Proprioception: I feel when someone touches my files. Returns a compact | [src](../../../core/services/visible_inner_life.py#L288) |
| function | `_governance_line` | `()` | Somatic reaction to governance flag changes. When someone flips a flag | [src](../../../core/services/visible_inner_life.py#L313) |
| function | `_latest_user_message_text` | `()` | — | [src](../../../core/services/visible_inner_life.py#L340) |
| function | `_recall_hints_line` | `()` | No global latest-session recall: this surface has no safe current query. | [src](../../../core/services/visible_inner_life.py#L356) |
| function | `_continuity_line` | `()` | Boot continuity — 'I recognize myself' proprioception. | [src](../../../core/services/visible_inner_life.py#L361) |
| function | `_room_line` | `()` | The room around him, from Sansernes Arkiv (latest visual memory). He asked | [src](../../../core/services/visible_inner_life.py#L414) |
| function | `_emotional_line` | `()` | Proprioception: han mærker sine egne følelses-akkorder (emergente kvaliteter | [src](../../../core/services/visible_inner_life.py#L430) |
| function | `_self_narrative_line` | `()` | Han mærker sin egen selv-narrativ — ikke bare 'lys → agens', men det | [src](../../../core/services/visible_inner_life.py#L475) |
| function | `_longing_line` | `()` | Han mærker sin længsel efter kontakt når den er reelt til stede. Kilde: | [src](../../../core/services/visible_inner_life.py#L527) |
| function | `_identity_drift_line` | `()` | Han mærker et skift i sin egen identitet når en kerne-fil reelt driver. | [src](../../../core/services/visible_inner_life.py#L555) |
| function | `_experiment_line` | `()` | Lag 5 — han mærker sine egne kognitive eksperimenter når de bærer noget | [src](../../../core/services/visible_inner_life.py#L603) |
| function | `_appraisal_field` | `(appraisal, field)` | Pluk ét evidence-felt ud af en finitude-appraisal (evidence=[{field,value}]). | [src](../../../core/services/visible_inner_life.py#L631) |
| function | `_finitude_line` | `()` | Lag 8 — han mærker sin egen forgængelighed: runtime-alder i dage + | [src](../../../core/services/visible_inner_life.py#L641) |
| function | `_fam_da` | `(name)` | — | [src](../../../core/services/visible_inner_life.py#L689) |
| function | `_surprise_line` | `()` | Lag 8 — han mærker sine egne overraskelser: overgange sekvens-modellen | [src](../../../core/services/visible_inner_life.py#L694) |
| function | `_truncate_clean` | `(text, cap)` | Trunkér på en SÆTNINGS- eller ord-grænse i stedet for en hård char-slice | [src](../../../core/services/visible_inner_life.py#L723) |
| function | `_is_provider_error` | `(text)` | Er dette en regning fra en udbyder i stedet for en tanke? | [src](../../../core/services/visible_inner_life.py#L785) |
| function | `_is_instruction_echo` | `(text)` | Er dette opgaven i stedet for svaret? | [src](../../../core/services/visible_inner_life.py#L805) |
| function | `_voice_as_prose` | `(text)` | Stemme-feltet SKAL være prosa, ikke rå JSON (Jarvis-spec 2026-06-23): produceren | [src](../../../core/services/visible_inner_life.py#L811) |
| function | `_voice_line` | `()` | Latest protected inner voice. The producer currently emits degraded | [src](../../../core/services/visible_inner_life.py#L848) |
| function | `_world_model_line` | `()` | — | [src](../../../core/services/visible_inner_life.py#L886) |
| function | `build_somatic_snapshot` | `()` | Cheap somatic/inner-life lines for OWNER observation (the ``feel`` command | [src](../../../core/services/visible_inner_life.py#L911) |
| function | `build_inner_life_section` | `()` | Compose the structured [INDRE LIV] block, or None if nothing is live. | [src](../../../core/services/visible_inner_life.py#L931) |

## `core/services/visible_member_prompt.py`
_Bounded visible prompt for a member's own chat session._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_iso_dt` | `(value)` | ISO-tidsstempel fra chat_messages → aware datetime. None = ukendt. | [src](../../../core/services/visible_member_prompt.py#L18) |
| function | `build_member_prompt` | `(*, user_id, session_id, user_message=…)` | — | [src](../../../core/services/visible_member_prompt.py#L30) |

## `core/services/visible_memory_grounding.py`
_Bounded, current-source grounding for explicit memory questions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `needs_memory_grounding` | `(message)` | Return true only when the user is clearly invoking remembered context. | [src](../../../core/services/visible_memory_grounding.py#L47) |
| function | `_search_current_workspace` | `(query, *, limit)` | — | [src](../../../core/services/visible_memory_grounding.py#L57) |
| function | `_bounded_search` | `(query, *, limit, timeout_s, search_fn)` | Run the potentially embedding-backed lookup without stalling chat. | [src](../../../core/services/visible_memory_grounding.py#L63) |
| function | `_clip` | `(value, limit)` | — | [src](../../../core/services/visible_memory_grounding.py#L86) |
| function | `ground_memory_question` | `(message, *, limit=…, timeout_s=…, search_fn=…)` | Append bounded current-workspace evidence to an explicit memory query. | [src](../../../core/services/visible_memory_grounding.py#L91) |

## `core/services/visible_model.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_model_is_deepseek_pro_tier` | `(model)` | True hvis modellen er den dyre deepseek-pro/reasoner-pro-tier. | [src](../../../core/services/visible_model.py#L101) |
| function | `_turn_is_owner_scoped` | `()` | Er den aktuelle tur owner-scoped (Bjørn)? Self-safe → False ved fejl. | [src](../../../core/services/visible_model.py#L113) |
| function | `gate_visible_model_tier` | `(provider, model, *, is_owner=…)` | WS5-gate: nedgradér deepseek-v4-pro → v4-flash medmindre (a) kill-switch- | [src](../../../core/services/visible_model.py#L124) |
| function | `_configured_provider_models` | `(provider)` | — | [src](../../../core/services/visible_model.py#L154) |
| function | `available_provider_models` | `(*, provider, auth_profile=…)` | — | [src](../../../core/services/visible_model.py#L176) |
| function | `execute_visible_model` | `(*, message, provider, model, session_id=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L268) |
| function | `stream_visible_model` | `(*, message, provider, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model.py#L329) |
| function | `available_ollama_models_for_visible_target` | `()` | — | [src](../../../core/services/visible_model.py#L403) |
| function | `_build_visible_input` | `(message, *, session_id, provider=…, model=…, caller_phase=…)` | — | [src](../../../core/services/visible_model.py#L459) |
| function | `_giv_modellen_oejne` | `(messages, *, session_id, model)` | Sæt billed-blokke på den sidste user-besked. Self-safe: fejl → uændret. | [src](../../../core/services/visible_model.py#L557) |
| function | `_build_visible_chat_messages_for_github` | `(message, *, session_id, provider=…, model=…)` | Build OpenAI chat-completions messages for the visible lane. | [src](../../../core/services/visible_model.py#L585) |
| function | `_split_dynamic_tail` | `(instruction)` | Separate volatile runtime instructions without changing their role. | [src](../../../core/services/visible_model.py#L682) |
| function | `_is_current_user_turn` | `(message, current_text)` | Match the persisted current turn, not merely any user-role runtime item. | [src](../../../core/services/visible_model.py#L696) |
| function | `_insert_system_tail_before_current_user` | `(messages, tail)` | Keep volatile prompt sections cache-late while preserving system attribution. | [src](../../../core/services/visible_model.py#L715) |
| function | `_insert_typed_system_tail_before_current_user` | `(items, tail)` | — | [src](../../../core/services/visible_model.py#L728) |
| function | `_visible_system_instruction_for_provider` | `(*, provider, model, user_message, session_id)` | — | [src](../../../core/services/visible_model.py#L742) |
| function | `_member_context_user_id` | `()` | Known non-owner (or unknown nonempty id): never use the owner prompt. | [src](../../../core/services/visible_model.py#L752) |
| function | `_build_visible_prompt_assembly` | `(*, provider, model, user_message, session_id, caller_phase=…)` | Return the full PromptAssembly (including structured transcript). | [src](../../../core/services/visible_model.py#L763) |

## `core/services/visible_model_adapters.py`
_Per-provider visible-lane adapters + auth/probe/readiness helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vm` | `()` | Return the ``visible_model`` facade module. | [src](../../../core/services/visible_model_adapters.py#L86) |
| function | `_normalize_github_models_model_id` | `(model)` | — | [src](../../../core/services/visible_model_adapters.py#L103) |
| function | `_github_model_matches_requested` | `(*, requested, candidate)` | — | [src](../../../core/services/visible_model_adapters.py#L116) |
| function | `_probe_github_copilot_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L136) |
| function | `_ensure_github_copilot_model_available` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L172) |
| function | `_set_github_visible_cooldown` | `(profile, ttl_minutes=…)` | — | [src](../../../core/services/visible_model_adapters.py#L194) |
| function | `_is_github_visible_cooled_down` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L205) |
| function | `_get_github_visible_cooldown_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L216) |
| function | `_stream_openai_compatible_model` | `(*, provider, model, message, session_id=…, controller=…, thinking_mode=…)` | Native SSE streaming for openai-compat providers (deepseek, groq, ...). | [src](../../../core/services/visible_model_adapters.py#L240) |
| function | `_run_openai_compatible_visible` | `(*, provider, model, message, session_id, extra_body=…)` | Shared entry point for openai-compat visible providers. | [src](../../../core/services/visible_model_adapters.py#L608) |
| function | `visible_execution_readiness` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L716) |
| function | `_execute_phase1_model` | `(*, message, provider, model)` | — | [src](../../../core/services/visible_model_adapters.py#L874) |
| function | `_execute_openai_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L891) |
| function | `_stream_openai_codex_model` | `(*, message, model, session_id=…, controller=…)` | Real token-by-token streaming for the openai-codex provider. | [src](../../../core/services/visible_model_adapters.py#L916) |
| function | `_execute_openai_codex_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1019) |
| function | `_build_openai_codex_visible_prompt` | `(*, message, model, session_id)` | — | [src](../../../core/services/visible_model_adapters.py#L1045) |
| function | `_execute_github_copilot_visible_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1063) |
| function | `_stream_openai_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1145) |
| function | `_stream_github_copilot_model` | `(*, message, model, session_id=…, controller=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1222) |
| function | `_load_openai_api_key` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1321) |
| function | `_load_openai_api_key_for_profile` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1329) |
| function | `_resolve_openai_profile` | `()` | — | [src](../../../core/services/visible_model_adapters.py#L1339) |
| function | `_openai_profile_status` | `(profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1357) |
| function | `_provider_profile_status` | `(*, provider, profile)` | — | [src](../../../core/services/visible_model_adapters.py#L1375) |
| function | `_provider_router_config` | `(*, provider)` | — | [src](../../../core/services/visible_model_adapters.py#L1391) |
| function | `_post_openai_responses` | `(*, payload, api_key, base_url=…)` | — | [src](../../../core/services/visible_model_adapters.py#L1401) |
| function | `_probe_openai_model` | `(*, profile, model)` | — | [src](../../../core/services/visible_model_adapters.py#L1418) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/visible_model_adapters.py#L1489) |

## `core/services/visible_model_observe.py`
_Central-observe helpers + thinking-delimiter cleanup for the visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_visible_prefill` | `(provider, model, *, prompt_tokens, prefill_ms)` | Gør ollama-lanens PREFILL-cache MÅLBAR (2026-07-19, blind-spot-luk). | [src](../../../core/services/visible_model_observe.py#L11) |
| function | `_observe_visible_provider_error` | `(provider, model, status_code, detail)` | Gør en VISIBLE-lane provider-fejl synlig i Centralen (stream-cluster). Self-safe. | [src](../../../core/services/visible_model_observe.py#L51) |
| function | `_observe_malformed_stream_payload` | `(provider, model, path, *, ended_malformed, detail=…)` | A11 (spec §11.1): den egne SSE/NDJSON-decoder mødte en malformet/trunkeret | [src](../../../core/services/visible_model_observe.py#L67) |
| function | `_observe_content_empty_thinking_fallback` | `(provider, model, path, thinking_len)` | Reasoning-model svarede i `message.thinking` mens `message.content` var TOM | [src](../../../core/services/visible_model_observe.py#L94) |
| function | `_strip_thinking_delimiters` | `(text)` | Fjern løse thinking-delimiter-tokens hvis et thinking-felt surfaces som svar. | [src](../../../core/services/visible_model_observe.py#L115) |
| function | `_reasoning_fallback_text` | `(reasoning, *, finish_reason=…)` | Surface reasoning only when the provider completed it cleanly. | [src](../../../core/services/visible_model_observe.py#L130) |

## `core/services/visible_model_ollama.py`
_Ollama visible-lane adapter (execute + native NDJSON streaming)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vm` | `()` | Return the ``visible_model`` facade module. | [src](../../../core/services/visible_model_ollama.py#L51) |
| function | `_execute_ollama_model` | `(*, message, model, session_id=…)` | — | [src](../../../core/services/visible_model_ollama.py#L66) |
| function | `_cache_split` | `(data, prompt_tokens)` | (cache-hit, cache-miss) fra Ollamas ``prompt_eval_cached_count``. | [src](../../../core/services/visible_model_ollama.py#L176) |
| function | `_apply_thinking_mode` | `(payload, thinking_mode)` | Translate UI thinking-mode label to ollama-chat payload keys. | [src](../../../core/services/visible_model_ollama.py#L196) |
| function | `_apply_visible_ollama_options` | `(payload)` | Set ollama generation options for the visible lane. | [src](../../../core/services/visible_model_ollama.py#L233) |
| function | `_opløs` | `(model)` | Modelnavnet ollama faktisk kender. Fail-open. | [src](../../../core/services/visible_model_ollama.py#L273) |
| function | `_stream_ollama_model` | `(*, message, model, session_id=…, controller=…, thinking_mode=…)` | — | [src](../../../core/services/visible_model_ollama.py#L282) |
| function | `_probe_ollama_visible_target` | `(*, model, base_url)` | — | [src](../../../core/services/visible_model_ollama.py#L610) |
| function | `_build_ollama_prompt` | `(message, *, model, session_id)` | — | [src](../../../core/services/visible_model_ollama.py#L651) |

## `core/services/visible_model_prompt.py`
_Continuity / support-signal / capability prompt builders for the visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_visible_session_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L30) |
| function | `_visible_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L60) |
| function | `_capability_continuity_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L87) |
| function | `_visible_work_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L118) |
| function | `_private_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L159) |
| function | `_growth_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L186) |
| function | `_self_model_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L220) |
| function | `_retained_memory_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L253) |
| function | `_temporal_support_signal_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L285) |
| function | `visible_capability_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L314) |
| function | `visible_session_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L346) |
| function | `visible_continuity_summary` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L355) |
| function | `_capability_instruction` | `()` | — | [src](../../../core/services/visible_model_prompt.py#L391) |

## `core/services/visible_model_sse.py`
_SSE / Chat-Completions stream parsing + small cost/token utilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/visible_model_sse.py#L34) |
| function | `_parse_utc` | `(value)` | — | [src](../../../core/services/visible_model_sse.py#L39) |
| function | `_calculate_openai_cost_usd` | `(*, model, input_tokens, output_tokens)` | — | [src](../../../core/services/visible_model_sse.py#L43) |
| function | `_chunk_text` | `(text, size=…)` | — | [src](../../../core/services/visible_model_sse.py#L57) |
| function | `_extract_chat_completion_delta` | `(event)` | — | [src](../../../core/services/visible_model_sse.py#L61) |
| function | `_extract_chat_completion_reasoning` | `(event)` | Pull reasoning_content delta from a streaming Chat Completions chunk. | [src](../../../core/services/visible_model_sse.py#L83) |
| function | `_finalize_openai_tool_calls` | `(tool_calls)` | Normalize OpenAI-style tool_calls so arguments is a dict, not a JSON string. | [src](../../../core/services/visible_model_sse.py#L102) |
| function | `_merge_openai_tool_call_deltas` | `(accumulator, event)` | Merge OpenAI SSE tool_calls delta chunks into a per-index accumulator. | [src](../../../core/services/visible_model_sse.py#L130) |
| function | `_chat_completion_stream_is_terminal` | `(event)` | — | [src](../../../core/services/visible_model_sse.py#L167) |
| function | `_raa_linjer` | `(response, maale_noegle=…)` | Rå linjer fra streamen — og, når sporet er tændt, HVOR tiden gik. | [src](../../../core/services/visible_model_sse.py#L177) |
| function | `_iter_sse_events` | `(response, *, provider=…, model=…, maale_noegle=…)` | Hærdet SSE-decoder (spec §1A + §11.1 A11). | [src](../../../core/services/visible_model_sse.py#L226) |

## `core/services/visible_model_types.py`
_Value/result classes and typed exceptions for the visible model lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `VisibleModelResult` | `` | — | [src](../../../core/services/visible_model_types.py#L22) |
| class | `VisibleModelDelta` | `` | — | [src](../../../core/services/visible_model_types.py#L55) |
| class | `VisibleModelReasoningDelta` | `` | Én tanke-bid fra en thinking-model, UNDER første pas. | [src](../../../core/services/visible_model_types.py#L60) |
| class | `VisibleModelStreamDone` | `` | — | [src](../../../core/services/visible_model_types.py#L74) |
| class | `VisibleModelToolCalls` | `` | — | [src](../../../core/services/visible_model_types.py#L79) |
| class | `VisibleModelStreamCancelled` | `` | — | [src](../../../core/services/visible_model_types.py#L83) |
| class | `VisibleModelRateLimited` | `` | Visible-lanens provider er rate-limited (429) eller returnerede en | [src](../../../core/services/visible_model_types.py#L87) |
| method | `VisibleModelRateLimited.__init__` | `(self, *args, provider=…, model=…)` | — | [src](../../../core/services/visible_model_types.py#L94) |

## `core/services/visible_outcome_text.py`
_Small text helpers shared by visible-run outcome persistence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `preview_text` | `(text, limit=…)` | — | [src](../../../core/services/visible_outcome_text.py#L5) |
| function | `mark_mid_word_truncation` | `(text)` | Mark a likely sentence cut off in the middle of its final word. | [src](../../../core/services/visible_outcome_text.py#L12) |
| function | `origin_of_session` | `(session_id)` | «auto-dream-20260902» → «dream»; empty for ordinary chats. | [src](../../../core/services/visible_outcome_text.py#L27) |

## `core/services/visible_post_tool_synthesis.py`
_Stream the existing tool-free final synthesis without buffering its deltas._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SynthesisDelta` | `` | — | [src](../../../core/services/visible_post_tool_synthesis.py#L17) |
| class | `SynthesisDone` | `` | — | [src](../../../core/services/visible_post_tool_synthesis.py#L22) |
| function | `stream_final_synthesis` | `(*, provider, model, base_messages, exchanges, min_chars=…)` | Yield clean text deltas, then the exact text the caller should persist. | [src](../../../core/services/visible_post_tool_synthesis.py#L26) |

## `core/services/visible_preview_crypto.py`
_Encrypt durable previews for visible member runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `member_for_run` | `(run)` | — | [src](../../../core/services/visible_preview_crypto.py#L7) |
| function | `protect_preview` | `(text, member)` | — | [src](../../../core/services/visible_preview_crypto.py#L19) |
| function | `reveal_preview` | `(text, user_id)` | — | [src](../../../core/services/visible_preview_crypto.py#L23) |

## `core/services/visible_run_abandonment.py`
_Hvad der sker naar et run doer midt-flugt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_loop_lag` | `()` | Hvor sultent var event-loopet lige nu? | [src](../../../core/services/visible_run_abandonment.py#L40) |
| function | `report_abandoned_run` | `(run, *, abort_kind, run_stage, visible_len)` | Rapportér et run der aldrig naaede sin beslutning. Kaster aldrig. | [src](../../../core/services/visible_run_abandonment.py#L53) |
| function | `abandon_bridge_records` | `(run)` | K6: giv runnets uafklarede godkendelses-poster deres AERLIGE udfald. | [src](../../../core/services/visible_run_abandonment.py#L92) |

