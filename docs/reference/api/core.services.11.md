# `core.services.11` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `ensure_default_automations` | `()` | Seed a couple of baseline automations so the DSL surface has examples. | [src](../../../core/services/governance_bootstrap.py#L277) |
| function | `ensure_warmup_job` | `()` | Enqueue a single low-priority warmup job on first boot so the | [src](../../../core/services/governance_bootstrap.py#L341) |
| function | `bootstrap_all` | `()` | Run all idempotent bootstrap helpers. Safe at any startup. | [src](../../../core/services/governance_bootstrap.py#L366) |

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
| function | `_word_present` | `(word, text_lower)` | Word-boundary check: True if `word` appears as a standalone token (with optional plural). | [src](../../../core/services/hallucination_guard.py#L85) |
| function | `_section_keywords_for_message` | `(message)` | Derive keywords from the message so we can find the right MEMORY section. | [src](../../../core/services/hallucination_guard.py#L101) |
| function | `classify_question` | `(message)` | Classify the message: 'factual' | 'casual' | 'tool_call'. | [src](../../../core/services/hallucination_guard.py#L115) |
| function | `_ws_has_content` | `(path)` | Eksistens-tjek encryption-aware: plaintext eller member .enc. | [src](../../../core/services/hallucination_guard.py#L145) |
| function | `_find_memory_path` | `()` | Find MEMORY.md — look in runtime workspace first, then repo. | [src](../../../core/services/hallucination_guard.py#L153) |
| function | `_find_curated_paths` | `()` | Locate all curated workspace files for hallucination-guard recall. | [src](../../../core/services/hallucination_guard.py#L182) |
| function | `_extract_relevant_sections` | `(memory_text, keywords, max_chars=…)` | Find MEMORY.md-sektioner der matcher keywords, returnér som tekst. | [src](../../../core/services/hallucination_guard.py#L216) |
| function | `_observe_guard_decision` | `(*, activated, reason)` | Egress-frit Central-observe af hallucination-guardens beslutning (§7.2). | [src](../../../core/services/hallucination_guard.py#L300) |
| function | `inject_memory_into_prompt` | `(message, chat_messages, *, memory_path=…)` | Inject relevant memory as a system-role message into the prompt. | [src](../../../core/services/hallucination_guard.py#L324) |

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

## `core/services/heartbeat_phases.py`
_Heartbeat phases — explicit Sense / Reflect / Act structure on top of existing tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_active_recently` | `(*, window_minutes=…)` | Cheap check: has any user-role chat message landed in the last N minutes? | [src](../../../core/services/heartbeat_phases.py#L39) |
| function | `sense_phase` | `(*, name=…)` | Gather signals for this tick. Pure-read — no side effects. | [src](../../../core/services/heartbeat_phases.py#L64) |
| function | `_classify_activity` | `(signals)` | Classify current activity level from signals. | [src](../../../core/services/heartbeat_phases.py#L149) |
| function | `_identify_priorities` | `(signals)` | Heuristic — what should this tick attend to? | [src](../../../core/services/heartbeat_phases.py#L159) |
| function | `reflect_phase` | `(signals)` | Synthesize reflection. Heuristic-only by default; LLM optional. | [src](../../../core/services/heartbeat_phases.py#L175) |
| function | `_collect_active_goals` | `()` | Fetch active goals for chain proposal targeting. | [src](../../../core/services/heartbeat_phases.py#L235) |
| function | `_propose_skill_chains_in_idle` | `(max_goals=…)` | Propose skill chains for active goals. Time-bounded, never blocks. | [src](../../../core/services/heartbeat_phases.py#L244) |
| function | `format_chain_proposals` | `(max_chars=…)` | Format recent chain proposals for awareness injection. | [src](../../../core/services/heartbeat_phases.py#L291) |
| function | `clear_chain_proposals` | `()` | Clear cached chain proposals (e.g. after execution or user dismiss). | [src](../../../core/services/heartbeat_phases.py#L314) |
| function | `get_chain_proposals` | `()` | Return current chain proposals for inspection. | [src](../../../core/services/heartbeat_phases.py#L319) |
| function | `productive_idle` | `(*, budget_seconds=…)` | Run light maintenance work when there's no clear action. Time-bounded. | [src](../../../core/services/heartbeat_phases.py#L324) |
| function | `act_phase` | `(*, signals, reflection, name=…, trigger=…)` | Either run normal heartbeat tick OR productive idle, based on reflection. | [src](../../../core/services/heartbeat_phases.py#L518) |
| function | `tick_with_phases` | `(*, name=…, trigger=…)` | Run all 3 phases in sequence, return structured result. | [src](../../../core/services/heartbeat_phases.py#L594) |
| function | `_exec_phased_tick` | `(args)` | — | [src](../../../core/services/heartbeat_phases.py#L639) |
| function | `_exec_sense_only` | `(args)` | Read-only: gather current signals without running reflection or action. | [src](../../../core/services/heartbeat_phases.py#L646) |

## `core/services/heartbeat_provider_fallback.py`
_Heartbeat provider fallback — cheap cloud lane when primary (Groq) fails._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute_openai_compat_heartbeat_prompt` | `(*, prompt, target)` | Call an OpenAI-chat/completions-compatible provider for heartbeat. | [src](../../../core/services/heartbeat_provider_fallback.py#L53) |
| function | `try_heartbeat_cheap_fallback` | `(prompt)` | Try cheap lane providers (skip groq + ollamafreeapi) as heartbeat fallback. | [src](../../../core/services/heartbeat_provider_fallback.py#L121) |

## `core/services/heartbeat_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `HeartbeatExecutionResult` | `` | — | [src](../../../core/services/heartbeat_runtime.py#L239) |
| function | `start_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L245) |
| function | `stop_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L287) |
| function | `_cheap_heartbeat_schedule_state` | `(name)` | Compute just the schedule-state dict without touching sub-surfaces. | [src](../../../core/services/heartbeat_runtime.py#L299) |
| function | `poll_heartbeat_schedule` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L317) |
| function | `_run_heartbeat_tick_with_deadline` | `(*, name, trigger, deadline_seconds=…)` | Run a heartbeat tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L360) |
| function | `_poll_heartbeat_schedule_with_trigger` | `(*, name, due_trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L421) |
| function | `heartbeat_runtime_surface` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L451) |
| function | `_heartbeat_runtime_surface_uncached` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L475) |
| function | `_build_cognitive_surfaces` | `()` | Build cognitive architecture surfaces safely (never raise). | [src](../../../core/services/heartbeat_runtime.py#L573) |
| function | `_safe_surface` | `(target, key, builder)` | Call builder and store result; swallow any errors. | [src](../../../core/services/heartbeat_runtime.py#L1148) |
| function | `run_heartbeat_tick` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1177) |
| function | `_daemon_tick_with_deadline` | `(name, fn, *args, deadline_seconds=…, **kwargs)` | Run a daemon tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L1196) |
| function | `_run_heartbeat_tick_locked` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1259) |
| function | `load_heartbeat_policy` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L2173) |
| function | `_build_heartbeat_context` | `(*, policy, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2219) |
| function | `_build_heartbeat_cognitive_frame` | `(*, merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L2432) |
| function | `_build_executive_visible_state` | `(*, merged_state, context)` | — | [src](../../../core/services/heartbeat_runtime.py#L2452) |
| function | `_decide_executive_action` | `(*, merged_state, context, now_iso)` | — | [src](../../../core/services/heartbeat_runtime.py#L2471) |
| function | `_execute_executive_decision` | `(executive_decision)` | — | [src](../../../core/services/heartbeat_runtime.py#L2538) |
| function | `_log_liveness_dedup` | `(signal, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2578) |
| function | `_build_heartbeat_liveness_signal` | `(*, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2601) |
| function | `_select_heartbeat_target` | `(policy=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3205) |
| function | `_runtime_selected_local_target` | `(*, settings)` | — | [src](../../../core/services/heartbeat_runtime.py#L3330) |
| function | `_phase1_rule_based_decision` | `(*, policy, open_loops, liveness=…, prompt=…)` | Rule-based heartbeat decision for phase1-runtime or LLM-failure fallback. | [src](../../../core/services/heartbeat_runtime.py#L3353) |
| function | `_execute_heartbeat_model` | `(*, prompt, target, policy, open_loops, liveness=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3462) |
| function | `_recent_ping_history` | `(*, limit=…)` | Return the last N assistant ping_text strings already delivered. | [src](../../../core/services/heartbeat_runtime.py#L3549) |
| function | `_user_recently_active` | `(minutes)` | Return True if any user-role chat message landed within the window. | [src](../../../core/services/heartbeat_runtime.py#L3583) |
| function | `_active_chat_gate_blocked_result` | `(*, tick_id, decision_type, minutes)` | Build the blocked-result + emit deferred event for active-chat gate. | [src](../../../core/services/heartbeat_runtime.py#L3615) |
| function | `_heartbeat_prompt_text` | `(base_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3645) |
| function | `_parse_heartbeat_decision` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3767) |
| function | `_parse_heartbeat_decision_bounded` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3789) |
| function | `_bounded_heartbeat_failure_decision` | `(*, failure_kind, detail, target)` | — | [src](../../../core/services/heartbeat_runtime.py#L3803) |
| function | `_validate_heartbeat_decision` | `(*, decision, policy, workspace_dir, tick_id)` | — | [src](../../../core/services/heartbeat_runtime.py#L3829) |
| function | `_deliver_heartbeat_proposal` | `(*, policy, tick_id, summary, proposed_action)` | — | [src](../../../core/services/heartbeat_runtime.py#L4377) |
| function | `_deliver_heartbeat_ping_directly` | `(*, policy, tick_id, ping_text, summary)` | Deliver an LLM-authored ping straight to webchat. | [src](../../../core/services/heartbeat_runtime.py#L4534) |
| function | `_dispatch_runtime_hook_events_safely` | `(*, event_kinds=…, limit=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L4754) |
| function | `_recover_bounded_heartbeat_liveness_decision` | `(*, decision, policy, liveness)` | — | [src](../../../core/services/heartbeat_runtime.py#L4774) |
| function | `_run_bounded_conflict_resolution` | `(*, decision, context, policy)` | Run conflict resolution using existing runtime signals. | [src](../../../core/services/heartbeat_runtime.py#L4832) |
| function | `_apply_conflict_resolution_to_decision` | `(*, decision, conflict_trace)` | Apply conflict resolution to modify or preserve the decision. | [src](../../../core/services/heartbeat_runtime.py#L4919) |
| function | `_execute_continue_internal` | `(*, conflict_trace, trigger)` | Execute a bounded internal continuation when conflict chose continue_internal. | [src](../../../core/services/heartbeat_runtime.py#L4935) |
| function | `_heartbeat_ping_candidate_ready` | `(*, policy)` | — | [src](../../../core/services/heartbeat_runtime.py#L4990) |
| function | `_execute_heartbeat_internal_action` | `(*, action_type, tick_id, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L5011) |
| function | `_summarize_heartbeat_capability_invocations` | `(invocations)` | — | [src](../../../core/services/heartbeat_runtime.py#L6518) |
| function | `_record_heartbeat_outcome` | `(*, policy, persisted, tick_id, trigger, tick_status, decision_type, decision_summary, decision_reason, blocked_reason, currently_ticking, last_trigger_source, provider, model, lane, budget_status, model_source=…, resolution_status=…, fallback_used=…, execution_status=…, parse_status=…, ping_eligible, ping_result, action_status, action_summary, action_type, action_artifact, raw_response, input_tokens, output_tokens, cost_usd, started_at, finished_at, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L6558) |
| function | `_merge_runtime_state` | `(*, policy, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6736) |
| function | `_tick_blocked_reason` | `(merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L6823) |
| function | `_compute_next_tick_at` | `(*, interval_minutes, last_tick_at, enabled)` | — | [src](../../../core/services/heartbeat_runtime.py#L6837) |
| function | `_resolve_tick_activity_state` | `(*, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6847) |
| function | `_write_heartbeat_state_artifact` | `(*, workspace_dir, payload)` | — | [src](../../../core/services/heartbeat_runtime.py#L6883) |
| function | `_default_persisted_state` | `()` | — | [src](../../../core/services/heartbeat_runtime.py#L6894) |
| function | `_heartbeat_state_summary` | `(*, enabled, schedule_status, last_decision_type, last_result)` | — | [src](../../../core/services/heartbeat_runtime.py#L6933) |
| function | `_persist_runtime_state` | `(*, policy, persisted, now, overrides)` | — | [src](../../../core/services/heartbeat_runtime.py#L6947) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/heartbeat_runtime.py#L7010) |
| function | `_heartbeat_busy_result` | `(*, name, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L7037) |
| function | `_heartbeat_scheduler_loop` | `(*, name, startup_recovery_requested)` | — | [src](../../../core/services/heartbeat_runtime.py#L7087) |
| function | `_detect_startup_drift` | `(*, name, phase, overrides, actual_state)` | Compare intended overrides against what SELECT-back actually returned. | [src](../../../core/services/heartbeat_runtime.py#L7128) |
| function | `_persist_runtime_state_with_diagnostics` | `(*, name, phase, policy, persisted, now, overrides)` | Wrapper around _persist_runtime_state that re-raises with stack trace | [src](../../../core/services/heartbeat_runtime.py#L7192) |
| function | `_prepare_scheduler_startup` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7233) |
| function | `_mark_scheduler_stopped` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7371) |
| function | `_emit_schedule_transitions` | `(state)` | — | [src](../../../core/services/heartbeat_runtime.py#L7396) |
| function | `_heartbeat_runtime_bias_from_recent_work` | `(*, kind)` | — | [src](../../../core/services/heartbeat_runtime.py#L7437) |
| function | `call_heartbeat_llm_simple` | `(prompt, *, max_tokens=…)` | Call the heartbeat model with a plain prompt. Returns the response text. | [src](../../../core/services/heartbeat_runtime.py#L7477) |

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
| function | `is_promise_of_action` | `(text)` | True hvis `text` lover at assistenten tager en handling imminent. Self-safe. | [src](../../../core/services/hollow_promise_guard.py#L54) |
| function | `is_hollow_promise` | `(final_text, total_tool_calls, user_message=…, nudged_already=…)` | Tom løfte = lovede handling + NUL tool-kald hele runnet + ikke allerede nudget. | [src](../../../core/services/hollow_promise_guard.py#L69) |
| function | `hollow_promise_guard_enabled` | `()` | Default TRUE (Bjørn bad om værnet 4. jul). Env `JARVIS_HOLLOW_PROMISE_GUARD` vinder; | [src](../../../core/services/hollow_promise_guard.py#L92) |

## `core/services/identity_canon.py`
_Kanonisk identitets-narrativ-store — den strukturelle kur mod sonnet-spøgelset._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/identity_canon.py#L42) |
| function | `_ensure_identity_canon_table` | `(conn)` | Lazy DDL for begge tabeller. Idempotent. Self-safe (kalderen wrapper). | [src](../../../core/services/identity_canon.py#L46) |
| function | `_seed_if_empty` | `(conn)` | Idempotent seed: sonnet-korrektionen (kritisk) + valgfrit voice-canon. Kaldes under _ensure. | [src](../../../core/services/identity_canon.py#L72) |
| function | `_ensure_and_seed` | `(conn)` | — | [src](../../../core/services/identity_canon.py#L99) |
| function | `set_canon_thread` | `(*, thread, canon_text, updated_by=…)` | Owner/governed-self-surgery opdaterer en kanon-tråd. Upsert. Self-safe. | [src](../../../core/services/identity_canon.py#L112) |
| function | `get_canon` | `()` | Alle aktive kanon-tråde som {thread: canon_text}. Self-safe (tom dict ved fejl). | [src](../../../core/services/identity_canon.py#L133) |
| function | `list_acknowledged_corrections` | `(*, active_only=…)` | De kendte konfabulationer (anti-drift-listen). Self-safe (tom liste ved fejl). | [src](../../../core/services/identity_canon.py#L146) |
| function | `add_acknowledged_correction` | `(*, claim_pattern, reason)` | Tilføj en konfabulation til anti-drift-listen. Self-safe. | [src](../../../core/services/identity_canon.py#L163) |
| function | `build_identity_canon_surface` | `()` | Central-CLI-view: kanon-tråde + anerkendte korrektioner + seneste drift-fangster. Self-safe. | [src](../../../core/services/identity_canon.py#L182) |
| function | `_recent_drift_catches` | `(limit=…)` | Seneste identity_drift-observe-hændelser fra central trace, hvis let tilgængeligt. Self-safe. | [src](../../../core/services/identity_canon.py#L201) |

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

