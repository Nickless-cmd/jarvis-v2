# `core.services.12` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/goal_signal_synthesizer.py`
_Goal signal synthesizer — surface candidate goals from dreams/reflections._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gather_signals` | `()` | Collect recent introspective signals as text for LLM. | [src](../../../core/services/goal_signal_synthesizer.py#L23) |
| function | `synthesize_candidate_goals` | `(*, max_candidates=…)` | Run one synthesis pass — propose new goals from recent signals. | [src](../../../core/services/goal_signal_synthesizer.py#L46) |

## `core/services/goal_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_goal_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/goal_signal_tracking.py#L23) |
| function | `refresh_runtime_goal_signal_statuses` | `()` | — | [src](../../../core/services/goal_signal_tracking.py#L64) |
| function | `build_runtime_goal_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/goal_signal_tracking.py#L101) |
| function | `_extract_goal_candidates` | `(*, user_message, completed_domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L126) |
| function | `_goal_from_active_focus` | `(focus, *, user_message, completed_domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L152) |
| function | `_persist_goal_signals` | `(*, goals, session_id, run_id)` | — | [src](../../../core/services/goal_signal_tracking.py#L225) |
| function | `_apply_completion_signals` | `(domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L292) |
| function | `_supersede_replaced_goal_signals` | `(persisted_item, *, updated_at)` | — | [src](../../../core/services/goal_signal_tracking.py#L347) |
| function | `_completed_goal_domains` | `(message)` | — | [src](../../../core/services/goal_signal_tracking.py#L377) |
| function | `_blocking_state_for_domain` | `(domain_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L385) |
| function | `_has_completed_goal_history` | `(domain_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L430) |
| function | `_domain_key_from_focus` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L439) |
| function | `_domain_key_from_critic` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L454) |
| function | `_domain_key_from_self_model` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L463) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L472) |
| function | `_message_domain_key` | `(text)` | — | [src](../../../core/services/goal_signal_tracking.py#L476) |
| function | `_goal_title` | `(domain_key, fallback)` | — | [src](../../../core/services/goal_signal_tracking.py#L485) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/goal_signal_tracking.py#L493) |
| function | `_rank` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L502) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L506) |

## `core/services/good_enough_gate.py`
_Good-enough gate — completion criterion for autonomous runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_run_signals` | `(run_id, limit=…)` | — | [src](../../../core/services/good_enough_gate.py#L34) |
| function | `evaluate_good_enough` | `(*, run_id=…, iterations_done=…, iteration_budget=…, minutes_elapsed=…, minutes_budget=…)` | — | [src](../../../core/services/good_enough_gate.py#L57) |
| function | `_exec_check_good_enough` | `(args)` | — | [src](../../../core/services/good_enough_gate.py#L148) |

## `core/services/google_connector.py`
_Google-pakke-connector — Calendar/Drive/Docs/Sheets/Slides (læse-tools)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get` | `(user_id, url, params, err_prefix)` | Fælles GET med brugerens Google-token. → {status, data} | {status:error,...}. | [src](../../../core/services/google_connector.py#L168) |
| function | `_send` | `(user_id, method, url, *, json_body=…, params=…, err_prefix=…)` | Skrive-kald (POST/PUT) med brugerens Google-token. Bruges af create/edit-tools. | [src](../../../core/services/google_connector.py#L188) |
| function | `_clamp` | `(n, lo, hi, default)` | — | [src](../../../core/services/google_connector.py#L209) |
| function | `list_events` | `(user_id, *, max_results=…)` | — | [src](../../../core/services/google_connector.py#L216) |
| function | `drive_search` | `(user_id, *, query=…, max_results=…)` | — | [src](../../../core/services/google_connector.py#L237) |
| function | `_doc_text` | `(content)` | — | [src](../../../core/services/google_connector.py#L259) |
| function | `docs_read` | `(user_id, document_id)` | — | [src](../../../core/services/google_connector.py#L272) |
| function | `sheets_read` | `(user_id, spreadsheet_id, cell_range)` | — | [src](../../../core/services/google_connector.py#L283) |
| function | `_slides_text` | `(pres)` | — | [src](../../../core/services/google_connector.py#L297) |
| function | `slides_read` | `(user_id, presentation_id)` | — | [src](../../../core/services/google_connector.py#L311) |
| function | `create_event` | `(user_id, summary, start, *, end=…, description=…, location=…)` | Opret en begivenhed i brugerens primære kalender. start/end = ISO-8601. | [src](../../../core/services/google_connector.py#L325) |
| function | `append_doc` | `(user_id, document_id, text)` | Tilføj tekst i slutningen af et Google Docs-dokument. | [src](../../../core/services/google_connector.py#L355) |
| function | `write_sheet` | `(user_id, spreadsheet_id, cell_range, values)` | Skriv celler i et Google Sheets-regneark (overskriver range). values = liste af rækker. | [src](../../../core/services/google_connector.py#L370) |

## `core/services/google_login.py`
_Google app-login (§12) — kort-levende login-resultat-store + orkestrering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_role` | `(user_id)` | Find brugerens faktiske rolle (SQLite-user_db → ellers users.json → member). | [src](../../../core/services/google_login.py#L25) |
| function | `_gc` | `(now)` | — | [src](../../../core/services/google_login.py#L44) |
| function | `begin_login` | `(app_id=…, *, now=…)` | Start et login. Returnerer (nonce, state_uid) — state_uid lægges i OAuth-state. | [src](../../../core/services/google_login.py#L49) |
| function | `begin_link` | `(user_id, *, now=…)` | Start en Google-linking for en EKSISTERENDE (indlogget) bruger. | [src](../../../core/services/google_login.py#L58) |
| function | `is_login_state` | `(state_uid)` | — | [src](../../../core/services/google_login.py#L67) |
| function | `complete` | `(state_uid, google_email, *, now=…)` | Kaldt af callbacken med den VERIFICEREDE Google-email. Returnerer en kort | [src](../../../core/services/google_login.py#L71) |
| function | `take_result` | `(nonce, *, now=…)` | Engangs-hent af login-resultatet (fjernes ved hentning når det er færdigt). | [src](../../../core/services/google_login.py#L108) |

## `core/services/governance_bootstrap.py`
_Governance bootstrap — idempotent setup of default windows, jobs handlers, automations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_default_windows` | `()` | Ensure default scheduled job windows exist. Returns list of window_ids | [src](../../../core/services/governance_bootstrap.py#L15) |
| function | `ensure_default_job_handlers` | `()` | Register default job-type handlers. Returns list of job_type names registered. | [src](../../../core/services/governance_bootstrap.py#L73) |
| function | `ensure_default_automations` | `()` | Seed a couple of baseline automations so the DSL surface has examples. | [src](../../../core/services/governance_bootstrap.py#L290) |
| function | `ensure_warmup_job` | `()` | Enqueue a single low-priority warmup job on first boot so the | [src](../../../core/services/governance_bootstrap.py#L354) |
| function | `bootstrap_all` | `()` | Run all idempotent bootstrap helpers. Safe at any startup. | [src](../../../core/services/governance_bootstrap.py#L379) |

## `core/services/gratitude_tracker.py`
_Gratitude Tracker — accumulated appreciation over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_gratitude` | `(*, trigger_event, detail=…)` | — | [src](../../../core/services/gratitude_tracker.py#L20) |
| function | `detect_gratitude_from_interaction` | `(*, user_mood, outcome_status, was_corrected, autonomy_granted=…)` | — | [src](../../../core/services/gratitude_tracker.py#L44) |
| function | `build_gratitude_surface` | `()` | — | [src](../../../core/services/gratitude_tracker.py#L59) |

## `core/services/ground_truth_registry.py`
_Ground Truth Registry — Layer 3 of the Lying Engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_detect_host` | `()` | Detect which machine Jarvis runs on — hostname + primary IP. | [src](../../../core/services/ground_truth_registry.py#L146) |
| function | `_read_config_provider` | `()` | Read the current provider name from runtime.json. | [src](../../../core/services/ground_truth_registry.py#L169) |
| function | `_read_config_model` | `()` | Read the current model name from runtime.json. | [src](../../../core/services/ground_truth_registry.py#L186) |
| function | `_query_expression_count` | `()` | Count expressions from the DB. Returns None on failure. | [src](../../../core/services/ground_truth_registry.py#L204) |
| function | `_query_commit_count` | `()` | Count total commits in the repo. | [src](../../../core/services/ground_truth_registry.py#L218) |
| function | `_query_recent_commit_sha` | `()` | Get the current HEAD SHA (short). | [src](../../../core/services/ground_truth_registry.py#L232) |
| function | `_query_daemon_count` | `()` | Count active (enabled) daemons via daemon manager. | [src](../../../core/services/ground_truth_registry.py#L244) |
| function | `_query_gpu_info` | `()` | Quick GPU summary if available. | [src](../../../core/services/ground_truth_registry.py#L254) |
| function | `_query_uname` | `()` | Kernel/OS info. | [src](../../../core/services/ground_truth_registry.py#L269) |
| function | `collect_ground_truth` | `()` | Collect all available ground truth about Jarvis. Slow — call rarely. | [src](../../../core/services/ground_truth_registry.py#L282) |
| function | `refresh_ground_truth` | `()` | Force refresh the ground truth cache. Returns the fresh registry. | [src](../../../core/services/ground_truth_registry.py#L300) |
| function | `get_ground_truth` | `(key=…, force_refresh=…)` | Get ground truth from cache, auto-refreshing if stale. | [src](../../../core/services/ground_truth_registry.py#L315) |
| function | `ground_truth_summary` | `()` | Return a human-readable summary block for injection or repair. | [src](../../../core/services/ground_truth_registry.py#L343) |
| function | `verify_system_claim` | `(claim_text)` | Verify a system claim (IP, host, path) against ground truth. | [src](../../../core/services/ground_truth_registry.py#L370) |
| function | `lookup_infrastructure_fact` | `(key)` | Look up a known infrastructure fact (host/path/port) for ground-truth | [src](../../../core/services/ground_truth_registry.py#L438) |
| function | `verify_stats_claim` | `(claim_text)` | Verify a statistic claim (counts of expressions, daemons, commits) | [src](../../../core/services/ground_truth_registry.py#L455) |
| function | `ground_truth_daemon_tick` | `()` | Called by heartbeat daemon — refreshes cache and returns summary. | [src](../../../core/services/ground_truth_registry.py#L506) |

## `core/services/guided_learning_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_guided_learning_runtime_surface` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L11) |
| function | `_build_guided_learning_runtime_surface_uncached` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L19) |
| function | `build_guided_learning_runtime_from_sources` | `(*, adaptive_planner, adaptive_reasoning, epistemic_runtime_state, prompt_evolution, dream_articulation, dream_influence, loop_runtime, council_runtime)` | — | [src](../../../core/services/guided_learning_runtime.py#L32) |
| function | `build_guided_learning_prompt_section` | `(surface=…)` | — | [src](../../../core/services/guided_learning_runtime.py#L150) |
| function | `_derive_learning_focus` | `(*, planner, reasoning, epistemic, prompt_summary, dream_summary, dream_influence, loop_summary, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L177) |
| function | `_derive_learning_mode` | `(*, learning_focus, planner, reasoning, epistemic, prompt_summary, dream_summary, dream_influence, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L214) |
| function | `_derive_learning_posture` | `(*, learning_mode, council, reasoning, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L247) |
| function | `_derive_next_learning_bias` | `(*, learning_mode, learning_focus, planner, reasoning, epistemic, prompt_summary, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L265) |
| function | `_derive_learning_pressure` | `(*, learning_mode, planner, epistemic, council, prompt_summary, dream_summary, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L296) |
| function | `_derive_confidence` | `(*, learning_mode, learning_focus, learning_pressure, council, epistemic)` | — | [src](../../../core/services/guided_learning_runtime.py#L321) |
| function | `_source_contributors` | `(*, adaptive_planner, adaptive_reasoning, epistemic, prompt_summary, dream_summary, dream_influence, loop_summary, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L340) |
| function | `_guidance_for_learning` | `(state)` | — | [src](../../../core/services/guided_learning_runtime.py#L427) |
| function | `_safe_adaptive_planner` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L442) |
| function | `_safe_adaptive_reasoning` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L450) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L458) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L466) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L474) |
| function | `_safe_dream_influence` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L482) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L489) |
| function | `_safe_council_runtime` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L497) |

## `core/services/gut_calibration.py`
_Gut-calibration wiring — fodrer cognitive_gut_state fra run-livscyklussen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_run_event` | `(kind, payload)` | Dispatch fra run_closure_gate's listener. Kaster aldrig. | [src](../../../core/services/gut_calibration.py#L29) |
| function | `_on_started` | `(payload)` | — | [src](../../../core/services/gut_calibration.py#L40) |
| function | `_on_outcome` | `(payload, actual_outcome)` | — | [src](../../../core/services/gut_calibration.py#L70) |

## `core/services/gut_engine.py`
_Gut Engine — intuition and calibration tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `derive_gut_signal` | `(*, task_description, confidence=…, recent_error_count=…, recent_success_count=…)` | Generate a gut-feel hunch about a task. | [src](../../../core/services/gut_engine.py#L21) |
| function | `_consumer_mode` | `()` | — | [src](../../../core/services/gut_engine.py#L94) |
| function | `_gate_threshold` | `()` | — | [src](../../../core/services/gut_engine.py#L104) |
| function | `gut_gate` | `(proceed_confidence, *, context=…)` | Beslut om et proceed-valg må fortsætte, gated på gut-confidence. | [src](../../../core/services/gut_engine.py#L112) |
| function | `record_gut_outcome` | `(*, hunch, actual_outcome)` | Record whether the gut hunch was correct. | [src](../../../core/services/gut_engine.py#L159) |
| function | `build_gut_surface` | `()` | — | [src](../../../core/services/gut_engine.py#L181) |

## `core/services/habit_tracker.py`
_Habit Tracker — detects recurring patterns and friction points._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_habit_from_run` | `(*, run_id, task_signature, outcome_status, attempt_count=…)` | Track habit pattern and friction from a visible run. | [src](../../../core/services/habit_tracker.py#L24) |
| function | `build_habit_surface` | `()` | — | [src](../../../core/services/habit_tracker.py#L69) |
| function | `_normalize_signature` | `(text)` | Create a stable signature from task description. | [src](../../../core/services/habit_tracker.py#L83) |

## `core/services/habits_pipeline.py`
_Habits Pipeline — detect → track → suggest automation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/habits_pipeline.py#L34) |
| function | `_ensure_tables` | `()` | Tables exist from v2 db.py — this is idempotent no-op unless schema changes. | [src](../../../core/services/habits_pipeline.py#L38) |
| function | `_normalize_signature` | `(message)` | — | [src](../../../core/services/habits_pipeline.py#L91) |
| function | `_upsert_habit` | `(pattern_key, now)` | — | [src](../../../core/services/habits_pipeline.py#L105) |
| function | `_upsert_friction` | `(task_signature, now)` | — | [src](../../../core/services/habits_pipeline.py#L136) |
| function | `_maybe_create_suggestion` | `(*, source_type, source_id, suggestion_text, confidence, now)` | — | [src](../../../core/services/habits_pipeline.py#L167) |
| function | `record_habit_signal` | `(*, message)` | Main entry: record a habit signal from a chat message. | [src](../../../core/services/habits_pipeline.py#L199) |
| function | `list_habits` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L286) |
| function | `list_friction` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L298) |
| function | `list_suggestions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L310) |
| function | `accept_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L323) |
| function | `reject_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L350) |
| function | `build_habits_pipeline_surface` | `()` | — | [src](../../../core/services/habits_pipeline.py#L369) |

## `core/services/hallucination_guard.py`
_Hallucination Guard — forced memory-check before answering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_word_present` | `(word, text_lower)` | Word-boundary check: True if `word` appears as a standalone token (with optional plural). | [src](../../../core/services/hallucination_guard.py#L110) |
| function | `_section_keywords_for_message` | `(message)` | Derive keywords from the message so we can find the right MEMORY section. | [src](../../../core/services/hallucination_guard.py#L126) |
| function | `classify_question` | `(message)` | Classify the message: 'factual' | 'casual' | 'tool_call'. | [src](../../../core/services/hallucination_guard.py#L140) |
| function | `_ws_has_content` | `(path)` | Eksistens-tjek encryption-aware: plaintext eller member .enc. | [src](../../../core/services/hallucination_guard.py#L170) |
| function | `_find_memory_path` | `()` | Find MEMORY.md — look in runtime workspace first, then repo. | [src](../../../core/services/hallucination_guard.py#L178) |
| function | `_find_curated_paths` | `()` | Locate all curated workspace files for hallucination-guard recall. | [src](../../../core/services/hallucination_guard.py#L207) |
| function | `_extract_relevant_sections` | `(memory_text, keywords, max_chars=…)` | Find MEMORY.md-sektioner der matcher keywords, returnér som tekst. | [src](../../../core/services/hallucination_guard.py#L241) |
| function | `_observe_guard_decision` | `(*, activated, reason)` | Egress-frit Central-observe af hallucination-guardens beslutning (§7.2). | [src](../../../core/services/hallucination_guard.py#L325) |
| function | `inject_memory_into_prompt` | `(message, chat_messages, *, memory_path=…)` | Inject relevant memory as a system-role message into the prompt. | [src](../../../core/services/hallucination_guard.py#L349) |

## `core/services/hardware_body.py`
_Hardware body — collects CPU/GPU/RAM/VRAM/disk/temp signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_hardware_state` | `()` | Return current hardware state. Cached for 30s. Never raises. | [src](../../../core/services/hardware_body.py#L22) |
| function | `_collect` | `()` | — | [src](../../../core/services/hardware_body.py#L34) |
| function | `_somatic_overlay` | `(state)` | — | [src](../../../core/services/hardware_body.py#L98) |
| function | `_compute_pressure` | `(state)` | Compute overall pressure: low / medium / high / critical. | [src](../../../core/services/hardware_body.py#L121) |
| function | `_derive_energy_budget` | `(energy_level, drain_score, pressure)` | — | [src](../../../core/services/hardware_body.py#L172) |
| function | `_derive_circadian_preference` | `(clock_phase)` | — | [src](../../../core/services/hardware_body.py#L189) |
| function | `_derive_wake_state` | `(clock_phase, energy_level)` | — | [src](../../../core/services/hardware_body.py#L195) |
| function | `build_hardware_body_surface` | `()` | — | [src](../../../core/services/hardware_body.py#L204) |
| function | `run_hardware_body_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: Jarvis mærker sin egen krop (rådets #1 — "start med kroppen"). | [src](../../../core/services/hardware_body.py#L213) |
| function | `register_hardware_body_producer` | `()` | Registrér krop-sansningen som cadence-producer (~hvert 60s — hardware ændrer sig | [src](../../../core/services/hardware_body.py#L270) |
| function | `_emit_body_event` | `(metric, value)` | — | [src](../../../core/services/hardware_body.py#L283) |

## `core/services/heartbeat_action_hints.py`
_Hvornår er en indre-livs-handling det rigtige valg? Vink til heartbeat-beslutningen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/heartbeat_action_hints.py#L34) |
| function | `chronicle_days_stale` | `()` | Døgn siden seneste kronik-post. ``None`` hvis ukendt. Self-safe. | [src](../../../core/services/heartbeat_action_hints.py#L45) |
| function | `chronicle_hint` | `()` | Vink om at skrive kronik — kun når handlingen FAKTISK ville skrive noget. | [src](../../../core/services/heartbeat_action_hints.py#L61) |
| function | `inner_life_hints` | `()` | Alle aktive vink for indre-livs-handlinger. Tom liste når intet er forfaldent. | [src](../../../core/services/heartbeat_action_hints.py#L86) |

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
| function | `_scheduler_stop_event` | `()` | — | [src](../../../core/services/heartbeat_runtime.py#L210) |
| class | `HeartbeatExecutionResult` | `` | — | [src](../../../core/services/heartbeat_runtime.py#L256) |
| function | `start_heartbeat_scheduler` | `(*, name=…)` | Start planlægger-dæmonen. Selve tråden bor i heartbeat_scheduler. | [src](../../../core/services/heartbeat_runtime.py#L262) |
| function | `stop_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L272) |
| function | `_heartbeat_scheduler_running` | `()` | Lever planlægger-tråden? Ét sted, så de fire kaldesteder ikke driver fra | [src](../../../core/services/heartbeat_runtime.py#L277) |
| function | `_cheap_heartbeat_schedule_state` | `(name)` | Compute just the schedule-state dict without touching sub-surfaces. | [src](../../../core/services/heartbeat_runtime.py#L284) |
| function | `poll_heartbeat_schedule` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L302) |
| function | `_advance_schedule_after_idle_beat` | `(*, name)` | Avancér skemaet let hvis det STADIG er 'due' efter en beat — dvs. beat'en landede i | [src](../../../core/services/heartbeat_runtime.py#L353) |
| function | `_run_heartbeat_tick_with_deadline` | `(*, name, trigger, deadline_seconds=…)` | Run a heartbeat tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L385) |
| function | `_poll_heartbeat_schedule_with_trigger` | `(*, name, due_trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L446) |
| function | `heartbeat_runtime_surface` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L476) |
| function | `_heartbeat_runtime_surface_uncached` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L500) |
| function | `_build_cognitive_surfaces` | `()` | Build cognitive architecture surfaces safely (never raise). | [src](../../../core/services/heartbeat_runtime.py#L598) |
| function | `_safe_surface` | `(target, key, builder)` | Call builder and store result; swallow any errors. | [src](../../../core/services/heartbeat_runtime.py#L1173) |
| function | `run_heartbeat_tick` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1202) |
| function | `_daemon_tick_with_deadline` | `(name, fn, *args, deadline_seconds=…, **kwargs)` | Run a daemon tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L1221) |
| function | `_run_heartbeat_tick_locked` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1284) |
| function | `load_heartbeat_policy` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L2256) |
| function | `_build_heartbeat_context` | `(*, policy, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2302) |
| function | `_build_heartbeat_cognitive_frame` | `(*, merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L2515) |
| function | `_build_executive_visible_state` | `(*, merged_state, context)` | — | [src](../../../core/services/heartbeat_runtime.py#L2535) |
| function | `_decide_executive_action` | `(*, merged_state, context, now_iso)` | — | [src](../../../core/services/heartbeat_runtime.py#L2554) |
| function | `_execute_executive_decision` | `(executive_decision)` | — | [src](../../../core/services/heartbeat_runtime.py#L2621) |
| function | `_log_liveness_dedup` | `(signal, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2661) |
| function | `_build_heartbeat_liveness_signal` | `(*, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2684) |
| function | `_select_heartbeat_target` | `(policy=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3288) |
| function | `_runtime_selected_local_target` | `(*, settings)` | — | [src](../../../core/services/heartbeat_runtime.py#L3413) |
| function | `_phase1_rule_based_decision` | `(*, policy, open_loops, liveness=…, prompt=…)` | Rule-based heartbeat decision for phase1-runtime or LLM-failure fallback. | [src](../../../core/services/heartbeat_runtime.py#L3436) |
| function | `_execute_heartbeat_model` | `(*, prompt, target, policy, open_loops, liveness=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3545) |
| function | `_recent_ping_history` | `(*, limit=…)` | Return the last N assistant ping_text strings already delivered. | [src](../../../core/services/heartbeat_runtime.py#L3632) |
| function | `_user_recently_active` | `(minutes)` | Return True if any user-role chat message landed within the window. | [src](../../../core/services/heartbeat_runtime.py#L3666) |
| function | `_active_chat_gate_blocked_result` | `(*, tick_id, decision_type, minutes)` | Build the blocked-result + emit deferred event for active-chat gate. | [src](../../../core/services/heartbeat_runtime.py#L3698) |
| function | `_heartbeat_prompt_text` | `(base_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3728) |
| function | `_parse_heartbeat_decision` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3855) |
| function | `_parse_heartbeat_decision_bounded` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3877) |
| function | `_bounded_heartbeat_failure_decision` | `(*, failure_kind, detail, target)` | — | [src](../../../core/services/heartbeat_runtime.py#L3891) |
| function | `_validate_heartbeat_decision` | `(*, decision, policy, workspace_dir, tick_id)` | — | [src](../../../core/services/heartbeat_runtime.py#L3917) |
| function | `_deliver_heartbeat_proposal` | `(*, policy, tick_id, summary, proposed_action)` | — | [src](../../../core/services/heartbeat_runtime.py#L4465) |
| function | `_deliver_heartbeat_ping_directly` | `(*, policy, tick_id, ping_text, summary)` | Deliver an LLM-authored ping straight to webchat. | [src](../../../core/services/heartbeat_runtime.py#L4622) |
| function | `_dispatch_runtime_hook_events_safely` | `(*, event_kinds=…, limit=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L4842) |
| function | `_recover_bounded_heartbeat_liveness_decision` | `(*, decision, policy, liveness)` | — | [src](../../../core/services/heartbeat_runtime.py#L4862) |
| function | `_run_bounded_conflict_resolution` | `(*, decision, context, policy)` | Run conflict resolution using existing runtime signals. | [src](../../../core/services/heartbeat_runtime.py#L4920) |
| function | `_apply_conflict_resolution_to_decision` | `(*, decision, conflict_trace)` | Apply conflict resolution to modify or preserve the decision. | [src](../../../core/services/heartbeat_runtime.py#L5007) |
| function | `_execute_continue_internal` | `(*, conflict_trace, trigger)` | Execute a bounded internal continuation when conflict chose continue_internal. | [src](../../../core/services/heartbeat_runtime.py#L5023) |
| function | `_heartbeat_ping_candidate_ready` | `(*, policy)` | — | [src](../../../core/services/heartbeat_runtime.py#L5078) |
| function | `_execute_heartbeat_internal_action` | `(*, action_type, tick_id, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L5099) |
| function | `_summarize_heartbeat_capability_invocations` | `(invocations)` | — | [src](../../../core/services/heartbeat_runtime.py#L6629) |
| function | `_record_heartbeat_outcome` | `(*, policy, persisted, tick_id, trigger, tick_status, decision_type, decision_summary, decision_reason, blocked_reason, currently_ticking, last_trigger_source, provider, model, lane, budget_status, model_source=…, resolution_status=…, fallback_used=…, execution_status=…, parse_status=…, ping_eligible, ping_result, action_status, action_summary, action_type, action_artifact, raw_response, input_tokens, output_tokens, cost_usd, started_at, finished_at, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L6669) |
| function | `_merge_runtime_state` | `(*, policy, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6847) |
| function | `_tick_blocked_reason` | `(merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L6934) |
| function | `_compute_next_tick_at` | `(*, interval_minutes, last_tick_at, enabled)` | — | [src](../../../core/services/heartbeat_runtime.py#L6948) |
| function | `_resolve_tick_activity_state` | `(*, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6958) |
| function | `_write_heartbeat_state_artifact` | `(*, workspace_dir, payload)` | — | [src](../../../core/services/heartbeat_runtime.py#L6994) |
| function | `_default_persisted_state` | `()` | — | [src](../../../core/services/heartbeat_runtime.py#L7005) |
| function | `_heartbeat_state_summary` | `(*, enabled, schedule_status, last_decision_type, last_result)` | — | [src](../../../core/services/heartbeat_runtime.py#L7044) |
| function | `_persist_runtime_state` | `(*, policy, persisted, now, overrides)` | — | [src](../../../core/services/heartbeat_runtime.py#L7058) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/heartbeat_runtime.py#L7121) |
| function | `_heartbeat_busy_result` | `(*, name, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L7148) |
| function | `_detect_startup_drift` | `(*, name, phase, overrides, actual_state)` | Compare intended overrides against what SELECT-back actually returned. | [src](../../../core/services/heartbeat_runtime.py#L7198) |
| function | `_persist_runtime_state_with_diagnostics` | `(*, name, phase, policy, persisted, now, overrides)` | Wrapper around _persist_runtime_state that re-raises with stack trace | [src](../../../core/services/heartbeat_runtime.py#L7262) |
| function | `_prepare_scheduler_startup` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7303) |
| function | `_mark_scheduler_stopped` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7441) |
| function | `_emit_schedule_transitions` | `(state)` | — | [src](../../../core/services/heartbeat_runtime.py#L7466) |
| function | `_heartbeat_runtime_bias_from_recent_work` | `(*, kind)` | — | [src](../../../core/services/heartbeat_runtime.py#L7507) |
| function | `call_heartbeat_llm_simple` | `(prompt, *, max_tokens=…)` | Call the heartbeat model with a plain prompt. Returns the response text. | [src](../../../core/services/heartbeat_runtime.py#L7547) |

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

## `core/services/heartbeat_scheduler.py`
_Hjerteslagets dæmon — tråden der spørger «er det tid?» hvert 30. sekund._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_running` | `()` | Lever planlægger-tråden? | [src](../../../core/services/heartbeat_scheduler.py#L49) |
| function | `iterations` | `()` | Antal gennemløb siden tråden startede. Står tallet stille, er løkken væk. | [src](../../../core/services/heartbeat_scheduler.py#L59) |
| function | `stop_event` | `()` | — | [src](../../../core/services/heartbeat_scheduler.py#L64) |
| function | `start` | `(*, name=…)` | Start dæmonen. Er den allerede i gang, sker der ingenting. | [src](../../../core/services/heartbeat_scheduler.py#L68) |
| function | `stop` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_scheduler.py#L113) |
| function | `_loop` | `(*, name, startup_recovery_requested)` | — | [src](../../../core/services/heartbeat_scheduler.py#L127) |

## `core/services/hf_connector.py`
_Hugging Face-connector — søg modeller/datasets via Hub API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `()` | — | [src](../../../core/services/hf_connector.py#L43) |
| function | `_get` | `(path, params=…)` | — | [src](../../../core/services/hf_connector.py#L52) |
| function | `search_models` | `(query, *, limit=…)` | — | [src](../../../core/services/hf_connector.py#L67) |
| function | `model_info` | `(model_id)` | — | [src](../../../core/services/hf_connector.py#L85) |

## `core/services/hollow_promise_census.py`
_Optælling af tomme løfter — så Centralen kan SE Jarvis' værste mønster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_since` | `(hours)` | ISO-UTC-grænse. DB'en gemmer `2026-09-05T16:20:19.213749+00:00`, så en | [src](../../../core/services/hollow_promise_census.py#L71) |
| function | `census` | `(hours=…)` | Den ægte rate pr. model + hvor meget værnet fangede. Self-safe. | [src](../../../core/services/hollow_promise_census.py#L79) |
| function | `_guard_counts` | `(grænse)` | Hvad værnet selv greb, fra dets egne events. Self-safe. | [src](../../../core/services/hollow_promise_census.py#L129) |

## `core/services/hollow_promise_guard.py`
_Hollow-promise guard (4. jul) — fang "lovede handling, kaldte intet værktøj"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_last_sentence` | `(text)` | Sidste hele sætning. Løftet står dér — det er dét man efterlades med. | [src](../../../core/services/hollow_promise_guard.py#L131) |
| function | `is_promise_of_action` | `(text)` | True hvis `text` lover at assistenten tager en handling imminent. Self-safe. | [src](../../../core/services/hollow_promise_guard.py#L137) |
| function | `is_deferred_text_promise` | `(text)` | True for a promise to emit another prose section after this run ends. | [src](../../../core/services/hollow_promise_guard.py#L158) |
| function | `is_hollow_promise` | `(final_text, total_tool_calls, user_message=…, nudged_already=…, last_round_tool_calls=…)` | Tom løfte = lovede handling + NUL tool-kald i SIDSTE runde + ikke allerede nudget. | [src](../../../core/services/hollow_promise_guard.py#L169) |
| function | `hollow_promise_guard_enabled` | `()` | Default TRUE (Bjørn bad om værnet 4. jul). Env `JARVIS_HOLLOW_PROMISE_GUARD` vinder; | [src](../../../core/services/hollow_promise_guard.py#L201) |

## `core/services/hollow_promise_round.py`
_Hollow-promise follow-through (redesign 2026-09-04)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `supports_forced_tool_choice` | `(provider)` | — | [src](../../../core/services/hollow_promise_round.py#L33) |
| function | `next_round_tool_choice` | `(*, force_summary, hollow_force, provider)` | Sampling param for the next follow-up round. | [src](../../../core/services/hollow_promise_round.py#L37) |
| function | `_publish` | `(kind, payload)` | — | [src](../../../core/services/hollow_promise_round.py#L50) |
| function | `note_detected` | `(*, run_id, provider, model, round_index, session_id, forced)` | — | [src](../../../core/services/hollow_promise_round.py#L58) |
| function | `note_outcome` | `(*, run_id, provider, model, round_index, session_id, forced, tool_calls)` | Persist the outcome of the round after a hollow promise. Returns resolved. | [src](../../../core/services/hollow_promise_round.py#L65) |

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
| function | `_tcp_probe` | `(host, port, timeout=…)` | (oppe, latency_ms) — TCP-connect. Undgår ICMP-privilegier; åben port = servicen lever. | [src](../../../core/services/infra_sense.py#L51) |
| function | `poll_reachability` | `()` | Puls på huset: op/ned + latency for hver host → observe(cluster=infra). Self-safe. | [src](../../../core/services/infra_sense.py#L61) |
| function | `_http_json` | `(url, *, headers=…, method=…, body=…, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L82) |
| function | `poll_pihole` | `()` | PiHole DNS-helbred: blok-rate + klienter (spike = mulig malware). Self-safe. | [src](../../../core/services/infra_sense.py#L95) |
| function | `poll_pfsense` | `()` | pfSense gateway-liveness + uptime via REST API (X-API-Key). Read-only. Self-safe. | [src](../../../core/services/infra_sense.py#L127) |
| function | `_ssh_run` | `(target, remote_cmd, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L165) |
| function | `_parse_kv` | `(s)` | — | [src](../../../core/services/infra_sense.py#L176) |
| function | `poll_ssh_hosts` | `()` | Dyb health (disk/services/guests) via read-only SSH. Self-safe pr. host. | [src](../../../core/services/infra_sense.py#L188) |
| function | `poll_ha` | `()` | Home Assistant: tilstedeværelse + enheder offline (netværks-/device-signal). Self-safe. | [src](../../../core/services/infra_sense.py#L209) |
| function | `_notify_owner_security` | `(title, message)` | — | [src](../../../core/services/infra_sense.py#L235) |
| function | `_pfsense_syslogd_running` | `()` | Lever syslogd-PROCESSEN på pfSense? Via REST-API command_prompt (root-shell, read-only ps). | [src](../../../core/services/infra_sense.py#L266) |
| function | `_pfsense_restart_syslogd` | `()` | AUTO-HEAL: genstart syslogd på pfSense via REST-API command_prompt (root) og bekræft | [src](../../../core/services/infra_sense.py#L289) |
| function | `poll_syslog` | `()` | Dræn pfSense-syslog-detektioner (port-scan/brute-force) → Centralen: observe + incident | [src](../../../core/services/infra_sense.py#L306) |
| function | `_safe` | `(fn)` | — | [src](../../../core/services/infra_sense.py#L403) |
| function | `run_infra_sense_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: sans huset read-only. Bulletproof — kaster ALDRIG. | [src](../../../core/services/infra_sense.py#L410) |
| function | `register_infra_sense_producer` | `()` | Registrér infra-sansningen som cadence-producer (~hvert 3 min). Read-only. | [src](../../../core/services/infra_sense.py#L426) |

