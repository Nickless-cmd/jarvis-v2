# `core.services.10` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/experience_substrate.py`
_Experience substrate — embedding-retrieval learning layer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_chroma_collection` | `()` | Get or create the ChromaDB collection for experience episodes. | [src](../../../core/services/experience_substrate.py#L33) |
| function | `_get_embedder` | `()` | Get or create the sentence-transformers embedder (lazy load). | [src](../../../core/services/experience_substrate.py#L47) |
| function | `build_context_for_embedding` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…)` | Build a structured context string for embedding similarity. | [src](../../../core/services/experience_substrate.py#L57) |
| function | `record_episode` | `(*, session_id, turn_id=…, context_text, context_intent=…, active_loops=…, last_tools=…, session_phase=…, tool_sequence, outcome_signals, user_corrected=…)` | Record a new experience episode: insert to DB + embed to ChromaDB. | [src](../../../core/services/experience_substrate.py#L82) |
| function | `retrieve_similar_episodes` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…, context_text=…, k=…, min_score=…)` | Retrieve top-K similar experience episodes from ChromaDB. | [src](../../../core/services/experience_substrate.py#L170) |
| function | `build_experience_substrate_section` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…, user_message=…, k=…)` | Build the _experience_substrate prompt section. | [src](../../../core/services/experience_substrate.py#L257) |

## `core/services/experienced_time_daemon.py`
_Experienced time daemon — tracks subjective felt duration of the current session._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_experienced_time_daemon` | `(event_count, new_signal_count, energy_level)` | Update experienced time state. | [src](../../../core/services/experienced_time_daemon.py#L19) |
| function | `_label` | `(felt_minutes)` | — | [src](../../../core/services/experienced_time_daemon.py#L57) |
| function | `_generate_felt_label` | `(*, felt_minutes, event_count, novelty_count, energy_level)` | — | [src](../../../core/services/experienced_time_daemon.py#L69) |
| function | `reset_experienced_time_daemon` | `()` | Reset session state (for new session or testing). | [src](../../../core/services/experienced_time_daemon.py#L101) |
| function | `build_experienced_time_surface` | `()` | — | [src](../../../core/services/experienced_time_daemon.py#L110) |

## `core/services/experiential_memory.py`
_Experiential Memory — not just facts, but lived experiences with emotion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_experiential_memory_from_run` | `(*, run_id, session_id=…, user_message, assistant_response, outcome_status, user_mood=…)` | Create an experiential memory from a visible run. | [src](../../../core/services/experiential_memory.py#L27) |
| function | `create_experiential_memory_async` | `(**kwargs)` | Fire-and-forget wrapper. | [src](../../../core/services/experiential_memory.py#L93) |
| function | `find_relevant_memories` | `(context, limit=…)` | Find experiential memories relevant to current context. | [src](../../../core/services/experiential_memory.py#L101) |
| function | `recall_with_nostalgia` | `(memory_id)` | Recall an old experience with emotional coloring — nostalgia. | [src](../../../core/services/experiential_memory.py#L106) |
| function | `build_experiential_memory_surface` | `()` | MC surface for experiential memories. | [src](../../../core/services/experiential_memory.py#L124) |
| function | `_extract_topic` | `(user_message)` | Extract a short topic from user message. | [src](../../../core/services/experiential_memory.py#L151) |
| function | `_build_narrative` | `(*, user_message, outcome_status, user_mood, topic)` | Build a brief narrative of the experience. | [src](../../../core/services/experiential_memory.py#L157) |
| function | `_determine_emotion_arc` | `(user_mood, outcome_status)` | Determine the emotional arc of the experience. | [src](../../../core/services/experiential_memory.py#L184) |
| function | `_extract_lesson` | `(outcome_status, user_mood, user_message)` | Extract a deterministic lesson. | [src](../../../core/services/experiential_memory.py#L201) |
| function | `_calculate_importance` | `(user_mood, outcome_status)` | Calculate importance score for the memory. | [src](../../../core/services/experiential_memory.py#L214) |
| function | `_memory_scoring_mode` | `()` | 'llm' (nuværende cloud-LLM-scoring) | 'shadow' (kør begge, log enighed, brug LLM) | | [src](../../../core/services/experiential_memory.py#L228) |
| function | `_candidate_text` | `(c)` | Tekst-repr af et kandidat-minde til embedding (samme felter LLM'en fik). | [src](../../../core/services/experiential_memory.py#L240) |
| function | `_score_memories_by_embedding` | `(candidates, context_text)` | Rangér kandidater med embedding-cosine i stedet for et LLM-kald. Embed beskeden + | [src](../../../core/services/experiential_memory.py#L247) |
| function | `_observe_scoring_shadow` | `(llm_scores, emb_scores, llm_ms, emb_ms, n)` | Shadow: sammenlign top-2-udvalget fra LLM vs embedding, akkumulér enighed + | [src](../../../core/services/experiential_memory.py#L270) |
| function | `memory_scoring_shadow_stats` | `()` | Akkumuleret shadow-sammenligning: hvor ofte vælger embedding samme top-2 som LLM'en, | [src](../../../core/services/experiential_memory.py#L302) |
| function | `score_memories_by_relevance` | `(*, candidates, context_text, emotional_state)` | Score candidate memories for relevance. Returns {memory_id: score} 0.0–1.0. | [src](../../../core/services/experiential_memory.py#L321) |
| function | `_resolve_scoring_llm_target` | `()` | Resolve local/cheap LLM lane for scoring. | [src](../../../core/services/experiential_memory.py#L367) |
| function | `_build_scoring_prompt` | `(candidates, context_text, emotional_state)` | Build LLM prompt for memory relevance scoring. | [src](../../../core/services/experiential_memory.py#L383) |
| function | `_call_scoring_llm` | `(target, prompt)` | Score memories via cheap-lane provider pool. | [src](../../../core/services/experiential_memory.py#L416) |
| function | `_call_scoring_llm_ollamafreeapi` | `(prompt)` | Score via OllamaFreeAPI cloud with hard wall-clock timeout. | [src](../../../core/services/experiential_memory.py#L449) |
| function | `_call_scoring_llm_local` | `(target, prompt)` | Local Ollama scoring path. Configurable timeout ceiling (default 3s). | [src](../../../core/services/experiential_memory.py#L501) |
| function | `_parse_scoring_response` | `(text, candidates)` | Parse LLM JSON scoring response. Validates memory_ids against candidates. | [src](../../../core/services/experiential_memory.py#L532) |
| function | `_safe` | `(fn, **kwargs)` | — | [src](../../../core/services/experiential_memory.py#L568) |

## `core/services/experiential_runtime_context.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_experiential_runtime_context_surface` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L30) |
| function | `resolve_prior_experiential_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L43) |
| function | `_build_experiential_runtime_context_surface_uncached` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L49) |
| function | `build_experiential_runtime_context_from_surfaces` | `(*, embodied_state, affective_meta_state, heartbeat_state, cognitive_frame, prior_snapshot=…, continuity_source=…, now=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L64) |
| function | `build_experiential_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L127) |
| function | `_snapshot_for_carry` | `(surface)` | Extract minimal state needed for continuity comparison. | [src](../../../core/services/experiential_runtime_context.py#L185) |
| function | `_resolve_prior_experiential_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L196) |
| function | `_load_heartbeat_artifact_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L209) |
| function | `_has_shared_heartbeat_history` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L225) |
| function | `_derive_experiential_continuity` | `(current, prior)` | Derive bounded continuity between prior and current experiential state. | [src](../../../core/services/experiential_runtime_context.py#L232) |
| function | `_continuity_narrative` | `(state, shifts)` | — | [src](../../../core/services/experiential_runtime_context.py#L308) |
| function | `_translate_embodied_state` | `(surface)` | — | [src](../../../core/services/experiential_runtime_context.py#L331) |
| function | `_translate_affective_state` | `(surface)` | — | [src](../../../core/services/experiential_runtime_context.py#L364) |
| function | `_translate_intermittence` | `(heartbeat_state, *, now)` | — | [src](../../../core/services/experiential_runtime_context.py#L398) |
| function | `_translate_context_pressure` | `(frame)` | — | [src](../../../core/services/experiential_runtime_context.py#L435) |
| function | `_latest_tick_finished_at` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L461) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/experiential_runtime_context.py#L468) |
| function | `_derive_experiential_influence` | `(surface, continuity)` | Derive a bounded experiential influence trace from current state + continuity. | [src](../../../core/services/experiential_runtime_context.py#L499) |
| function | `_influence_narrative` | `(bearing, posture, initiative, continuity)` | One compact sentence explaining how experience shapes inner bearing. | [src](../../../core/services/experiential_runtime_context.py#L571) |
| function | `_derive_experiential_support` | `(influence)` | Derive a bounded support surface from experiential influence. | [src](../../../core/services/experiential_runtime_context.py#L634) |
| function | `_support_narrative` | `(posture, bias, mode)` | One compact sentence for how experiential support shapes conductor posture. | [src](../../../core/services/experiential_runtime_context.py#L687) |

## `core/services/experiment_runner.py`
_Experiment runner — controlled A/B trials of prompt variants._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/experiment_runner.py#L35) |
| function | `_save` | `(d)` | — | [src](../../../core/services/experiment_runner.py#L42) |
| function | `start_experiment` | `(*, scope, variant_a_label, variant_a_text, variant_b_label, variant_b_text, trials_target=…)` | Begin a new A/B experiment for a scope. | [src](../../../core/services/experiment_runner.py#L46) |
| function | `get_active_variant` | `(scope)` | Return the variant currently scheduled for this scope, or None. | [src](../../../core/services/experiment_runner.py#L80) |
| function | `conclude_experiment` | `(experiment_id)` | Analyze an experiment's data via prompt_variant_tracker, declare winner. | [src](../../../core/services/experiment_runner.py#L112) |
| function | `list_experiments` | `(*, status=…)` | — | [src](../../../core/services/experiment_runner.py#L177) |
| function | `_exec_start_experiment` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L185) |
| function | `_exec_conclude_experiment` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L196) |
| function | `_exec_list_experiments` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L200) |

## `core/services/fact_gate.py`
_Fact-Gate — blocking output gate for unverifiable factual claims._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_has_tool_evidence` | `(text, pattern, required, tool_names)` | Tjek om påstanden i text har tool-evidens. | [src](../../../core/services/fact_gate.py#L78) |
| function | `fact_gate_enforce` | `(text, tool_names=…)` | Detekterende gate — kald FØR append_chat_message. | [src](../../../core/services/fact_gate.py#L104) |
| function | `blocking_categories` | `()` | Returnér liste af aktive blokerbare kategorier. | [src](../../../core/services/fact_gate.py#L174) |

## `core/services/fcm_gateway.py`
_FCM HTTP v1 gateway — data-only push. Google ser kun et vaekke-signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime` | `()` | — | [src](../../../core/services/fcm_gateway.py#L19) |
| function | `_project_id` | `()` | — | [src](../../../core/services/fcm_gateway.py#L26) |
| function | `_sa_path` | `()` | — | [src](../../../core/services/fcm_gateway.py#L30) |
| function | `is_configured` | `()` | — | [src](../../../core/services/fcm_gateway.py#L34) |
| function | `_access_token` | `()` | Mint en OAuth-access-token fra service-account via google-auth. | [src](../../../core/services/fcm_gateway.py#L38) |
| function | `_build_message` | `(token, data)` | — | [src](../../../core/services/fcm_gateway.py#L51) |
| function | `send` | `(token, data)` | Send data-only push. Returnerer (ok, code). code='invalid' => slet token. | [src](../../../core/services/fcm_gateway.py#L68) |

## `core/services/file_awareness_daemon.py`
_File Awareness Daemon — proprioception: "I feel when my files change."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_recent_events` | `(limit=…)` | Return the most recent file-change events (for prompt inclusion). | [src](../../../core/services/file_awareness_daemon.py#L74) |
| function | `has_recent_events` | `(seconds=…)` | Are there events newer than `seconds` ago? | [src](../../../core/services/file_awareness_daemon.py#L80) |
| function | `_should_track` | `(path)` | Decide if a file change is worth tracking. | [src](../../../core/services/file_awareness_daemon.py#L102) |
| function | `_classify_change` | `(path)` | Classify a file change by importance. | [src](../../../core/services/file_awareness_daemon.py#L124) |
| function | `_record_change` | `(event_type, src_path, is_directory=…)` | Record a file change event. | [src](../../../core/services/file_awareness_daemon.py#L144) |
| function | `_on_governance_mutation` | `(event)` | Receive governance flag mutations from eventbus and store in buffer | [src](../../../core/services/file_awareness_daemon.py#L200) |
| function | `_make_handler` | `()` | Create a watchdog event handler that routes to _record_change. | [src](../../../core/services/file_awareness_daemon.py#L219) |
| function | `start_file_awareness` | `()` | Start the file awareness watcher. Returns True if started successfully. | [src](../../../core/services/file_awareness_daemon.py#L243) |
| function | `stop_file_awareness` | `()` | Stop the file awareness watcher. | [src](../../../core/services/file_awareness_daemon.py#L293) |
| function | `is_file_awareness_running` | `()` | Check if the file awareness watcher is running. | [src](../../../core/services/file_awareness_daemon.py#L309) |
| function | `tick_file_awareness` | `()` | Heartbeat tick: ensure watcher is running, report status. | [src](../../../core/services/file_awareness_daemon.py#L318) |

## `core/services/file_watch_daemon.py`
_File Watch Daemon — proprioception: "I feel when my own files change"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_ignore` | `(path_str)` | — | [src](../../../core/services/file_watch_daemon.py#L48) |
| function | `_watched_roots` | `()` | — | [src](../../../core/services/file_watch_daemon.py#L52) |
| function | `_iter_watched_files` | `(root)` | — | [src](../../../core/services/file_watch_daemon.py#L68) |
| function | `_diff_preview` | `(path)` | — | [src](../../../core/services/file_watch_daemon.py#L83) |
| function | `_record_change` | `(path, change_type)` | — | [src](../../../core/services/file_watch_daemon.py#L92) |
| function | `_compact_path` | `(path)` | — | [src](../../../core/services/file_watch_daemon.py#L111) |
| function | `tick` | `(_seconds=…)` | One polling sweep across watched roots. | [src](../../../core/services/file_watch_daemon.py#L127) |
| function | `recent_changes` | `(*, limit=…)` | — | [src](../../../core/services/file_watch_daemon.py#L168) |
| function | `build_file_watch_surface` | `()` | — | [src](../../../core/services/file_watch_daemon.py#L172) |
| function | `_surface_summary` | `(recent)` | — | [src](../../../core/services/file_watch_daemon.py#L187) |
| function | `build_file_watch_prompt_section` | `()` | Surface recent changes briefly — stays quiet if nothing recent. | [src](../../../core/services/file_watch_daemon.py#L198) |
| function | `reset_file_watch` | `()` | Reset state (for testing). | [src](../../../core/services/file_watch_daemon.py#L223) |

## `core/services/finitude_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_context_budget_tokens` | `()` | Resolve the active context-budget token limit. | [src](../../../core/services/finitude_runtime.py#L29) |
| function | `_appraisal_record` | `(*, kind, label, evidence, confidence, expires_at, allowed_effects, rendering, created_at=…)` | Structured finitude state; prose is rendering, not source truth. | [src](../../../core/services/finitude_runtime.py#L58) |
| function | `record_visible_model_transition` | `(*, previous_provider, previous_model, new_provider, new_model, trigger=…)` | — | [src](../../../core/services/finitude_runtime.py#L82) |
| function | `note_context_compaction` | `(*, session_id, freed_tokens, summary_text=…)` | — | [src](../../../core/services/finitude_runtime.py#L155) |
| function | `run_finitude_ritual` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/finitude_runtime.py#L213) |
| function | `_estimate_session_tokens` | `()` | Thin wrapper so tests can monkeypatch in this module's namespace. | [src](../../../core/services/finitude_runtime.py#L275) |
| function | `_token_utilization_pct` | `()` | Return integer pct of context budget used. 0 on any failure. | [src](../../../core/services/finitude_runtime.py#L284) |
| function | `_session_age_hours` | `()` | Return hours since the first message in the most-recently-touched session. | [src](../../../core/services/finitude_runtime.py#L303) |
| function | `_format_looming_end_section` | `()` | Render the two-line looming-end block, or '' if neither trigger active. | [src](../../../core/services/finitude_runtime.py#L338) |
| function | `_age_appraisal` | `(now)` | — | [src](../../../core/services/finitude_runtime.py#L365) |
| function | `_looming_end_appraisal` | `()` | — | [src](../../../core/services/finitude_runtime.py#L393) |
| function | `get_finitude_context_for_prompt` | `(*, max_chars=…)` | — | [src](../../../core/services/finitude_runtime.py#L424) |
| function | `build_finitude_surface` | `()` | — | [src](../../../core/services/finitude_runtime.py#L486) |
| function | `_build_annual_ritual_narrative` | `(*, year, recent_entries, transitions)` | — | [src](../../../core/services/finitude_runtime.py#L522) |
| function | `_monthly_quality_lane_enabled` | `()` | Single flag covers both annual and monthly finitude rituals. | [src](../../../core/services/finitude_runtime.py#L583) |
| function | `_is_due_for_monthly` | `(state, *, now)` | True iff no monthly reflection has been written for `now`'s YYYY-MM. | [src](../../../core/services/finitude_runtime.py#L591) |
| function | `_fetch_recent_broken_decisions_for_monthly` | `(*, days_back=…, limit=…)` | Pull broken-decision summaries from the events table for the last 30 days. | [src](../../../core/services/finitude_runtime.py#L598) |
| function | `_build_monthly_reflection_narrative` | `(*, year_month, chronicle_entries, transitions, broken_decisions)` | Build the 3-paragraph monthly reflection. Quality-lane LLM if enabled. | [src](../../../core/services/finitude_runtime.py#L645) |
| function | `run_monthly_finitude_reflection` | `(*, trigger=…, last_visible_at=…)` | Write one chronicle entry per calendar month. Skip-gate on empty months. | [src](../../../core/services/finitude_runtime.py#L731) |
| function | `_format_age_line` | `(now)` | Return a quiet 'du er N dage gammel' line. No LLM, no DB. | [src](../../../core/services/finitude_runtime.py#L817) |
| function | `_finitude_enabled` | `()` | — | [src](../../../core/services/finitude_runtime.py#L832) |
| function | `_is_birth_anniversary` | `(now)` | — | [src](../../../core/services/finitude_runtime.py#L837) |
| function | `_state` | `()` | — | [src](../../../core/services/finitude_runtime.py#L841) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/finitude_runtime.py#L846) |
| function | `_now` | `()` | — | [src](../../../core/services/finitude_runtime.py#L859) |

## `core/services/flow_state_detection.py`
_Flow State Detection — when everything clicks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_flow_detection` | `(*, recent_outcomes, correction_count=…, sustained_minutes=…)` | — | [src](../../../core/services/flow_state_detection.py#L11) |
| function | `get_flow_state` | `()` | — | [src](../../../core/services/flow_state_detection.py#L33) |
| function | `build_flow_state_surface` | `()` | — | [src](../../../core/services/flow_state_detection.py#L37) |

## `core/services/followup_observer.py`
_Followup-cluster — gør den agentiske followup-loop synlig i Den Intelligente Central._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, run_id, **data)` | — | [src](../../../core/services/followup_observer.py#L24) |
| function | `note_round` | `(run_id, round_num, provider=…, model=…, *, exchanges=…)` | En agentisk followup-runde startede. Metadata-only. | [src](../../../core/services/followup_observer.py#L33) |
| function | `note_round_failed` | `(run_id, round_num, provider=…, error=…, **data)` | En followup-runde fejlede (provider-fejl) → synlig. Det er her copilot-400 / | [src](../../../core/services/followup_observer.py#L41) |
| function | `note_round_retry` | `(run_id, round_num, attempt, reason=…, *, outcome=…, **data)` | RUND-NIVEAU RETRY (spec §4.1/S7): en forbigående runde-fejl blev retry'et | [src](../../../core/services/followup_observer.py#L49) |
| function | `note_lean_prompt` | `(run_id, round_num, *, provider=…, model=…, before_chars=…, after_chars=…, saved_tokens=…, applied=…)` | LEAN AGENTIC-PROMPT (spec §4.7/I7): på runde ≥2 trimmede vi den tunge per-turn- | [src](../../../core/services/followup_observer.py#L67) |
| function | `note_loop_complete` | `(run_id, *, rounds=…, exit_reason=…, provider=…, model=…)` | Followup-loopet sluttede → observe runder kørt + exit-grund (completed/ | [src](../../../core/services/followup_observer.py#L81) |
| function | `note_empty_completion` | `(run_id, *, provider=…, model=…, rounds=…, tools_executed=…, session_id=…, path=…)` | TAVS CUT-OFF: loopet sluttede 'completed' men producerede INTET synligt svar. | [src](../../../core/services/followup_observer.py#L90) |
| function | `note_hollow_promise` | `(run_id, *, provider=…, model=…, round_index=…, session_id=…, resolved=…)` | TOM LØFTE (4. jul): modellen lovede imminent handling men kaldte NUL værktøj hele | [src](../../../core/services/followup_observer.py#L129) |
| function | `note_resend` | `(run_id, *, provider=…, model=…, recovered=…)` | RESEND-PÅ-TOM (Bjørn option 1): runtimen fangede en transient tom completion | [src](../../../core/services/followup_observer.py#L142) |
| function | `note_leak` | `(run_id, *, provider=…, model=…, chars=…, reason=…)` | LEAK/DUMP: modellen echoede et råt (kæmpe) tool-result som prosa-svar i stedet | [src](../../../core/services/followup_observer.py#L151) |
| function | `note_degeneration` | `(run_id, *, provider=…, model=…, reason=…, chars=…)` | MODEL-LOOP: streaming-laget fangede en runaway-repetition og dræbte den ved | [src](../../../core/services/followup_observer.py#L170) |
| function | `followup_summary` | `(*, window=…)` | Read-only: nylig followup-loop-aktivitet (til MC). Self-safe. | [src](../../../core/services/followup_observer.py#L189) |

## `core/services/forgetting_curve.py`
_Forgetting Curve — active forgetting as a feature._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_memory` | `(*, memory_key, content_preview=…, initial_decay=…)` | Register a memory for decay tracking. | [src](../../../core/services/forgetting_curve.py#L21) |
| function | `reinforce_memory` | `(memory_key)` | Reinforce a memory — reset decay, increment reinforcement count. | [src](../../../core/services/forgetting_curve.py#L37) |
| function | `apply_decay_tick` | `(decay_increment=…)` | Apply one decay tick to all registered memories. | [src](../../../core/services/forgetting_curve.py#L46) |
| function | `get_active_memories` | `()` | Return memories with decay < 0.9 (still active). | [src](../../../core/services/forgetting_curve.py#L72) |
| function | `get_faded_memories` | `()` | Return memories with decay >= 0.9 (faded but archived). | [src](../../../core/services/forgetting_curve.py#L81) |
| function | `build_forgetting_curve_surface` | `()` | — | [src](../../../core/services/forgetting_curve.py#L90) |

## `core/services/forgetting_engine.py`
_Forgetting engine — Lag 11 deletion logic._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_fredet_path` | `(path)` | — | [src](../../../core/services/forgetting_engine.py#L64) |
| function | `is_fredet_table` | `(table)` | — | [src](../../../core/services/forgetting_engine.py#L68) |
| function | `compute_period_label` | `(released_at, now)` | Render an aged period as a human label. | [src](../../../core/services/forgetting_engine.py#L76) |
| function | `_id_column_for` | `(table)` | Return the primary-key column name for a fade-eligible table. | [src](../../../core/services/forgetting_engine.py#L105) |
| function | `_scan_table_for_candidates` | `(*, table, workspace_id, decay_threshold, min_age_days, limit)` | Find IDs of rows that should fade. | [src](../../../core/services/forgetting_engine.py#L112) |
| function | `_soft_delete_row` | `(table, row_id)` | Mark row as soft-deleted. Returns True if updated. | [src](../../../core/services/forgetting_engine.py#L158) |
| function | `_hard_delete_expired_rows` | `(table, grace_days)` | Hard-delete rows whose grace window has expired. | [src](../../../core/services/forgetting_engine.py#L171) |
| function | `run_auto_cycle` | `(*, workspace_id)` | One auto-track cycle: scan, soft-delete, grace-sweep. | [src](../../../core/services/forgetting_engine.py#L185) |
| function | `release_memory` | `(*, memory_kind, memory_id, workspace_id=…, why=…)` | Self-track release: hard-delete + marker. Irrevocable. | [src](../../../core/services/forgetting_engine.py#L261) |
| function | `_is_anniversary` | `(released_at, now)` | True if the age of released_at is within 1 day of a round-number bucket. | [src](../../../core/services/forgetting_engine.py#L361) |
| function | `_is_proximity` | `(released_at, now)` | True if released_at is in the active 14–90 day window. | [src](../../../core/services/forgetting_engine.py#L368) |
| function | `format_forgetting_section_for_heartbeat` | `(*, workspace_id=…)` | Compact prompt-injection lines for the heartbeat awareness section. | [src](../../../core/services/forgetting_engine.py#L378) |

## `core/services/forgetting_runtime.py`
_Daemon for the forgetting (Lag 11) auto-track._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | Lazy per-workspace lock. | [src](../../../core/services/forgetting_runtime.py#L24) |
| function | `_run_one_cycle` | `(workspace_id)` | Acquire workspace lock, run engine, release. Never raises. | [src](../../../core/services/forgetting_runtime.py#L34) |
| function | `_list_active_workspaces` | `()` | Phase 1: only the default workspace. | [src](../../../core/services/forgetting_runtime.py#L63) |
| function | `_resolve_interval_seconds` | `()` | Read cadence from settings each loop entry — picks up edits. | [src](../../../core/services/forgetting_runtime.py#L68) |
| function | `_loop` | `()` | — | [src](../../../core/services/forgetting_runtime.py#L78) |
| function | `start_forgetting_runtime` | `()` | Start the periodic forgetting daemon. Idempotent. | [src](../../../core/services/forgetting_runtime.py#L98) |
| function | `stop_forgetting_runtime` | `()` | Signal the loop to exit. | [src](../../../core/services/forgetting_runtime.py#L111) |

## `core/services/gate_adapters.py`
_Gate-adaptere (unified-gate A.5) — wrapper EKSISTERENDE gates som Verdict-returnerende._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `claim_scanner_adapter` | `(ctx)` | claim_scanner.scan_response: repareret tekst ≠ input → claims fanget (YELLOW). | [src](../../../core/services/gate_adapters.py#L17) |
| function | `fact_gate_adapter` | `(ctx)` | fact_gate_enforce: uverificerede tal-/status-påstande → YELLOW (warn/fodnote). | [src](../../../core/services/gate_adapters.py#L32) |
| function | `diagnosis_adapter` | `(ctx)` | analyze_completion_claim: blocked→RED, ikke-verificeret completion→YELLOW. | [src](../../../core/services/gate_adapters.py#L56) |
| function | `register_truthgate_adapters` | `(k)` | Registrér TruthGate-cluster-adapterne i kernen (post_output, kognitiv). | [src](../../../core/services/gate_adapters.py#L78) |
| function | `register_truthgate_adapters_once` | `(k)` | Idempotent — registrér KUN hvis ikke allerede registreret (kaldes pr. run i | [src](../../../core/services/gate_adapters.py#L85) |

## `core/services/gate_auth.py`
_Auth-cluster gate 🔒 — tool-access (rolle-håndhævelse), SECURITY fail-CLOSED._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `auth_gate` | `(ctx)` | ctx: {role, scope, name}. Returnér ét SECURITY-Verdict for tool-access. | [src](../../../core/services/gate_auth.py#L25) |

## `core/services/gate_commit.py`
_Commit-cluster gate (beslutnings-disciplin)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `commit_gate` | `(ctx)` | Kør Commit-clusterens decision-conflict-check og returnér ét GRADERET Verdict. | [src](../../../core/services/gate_commit.py#L18) |
| function | `veto_gate` | `(ctx)` | Commit-cluster: affektiv bruger-pushback gater tool-eksekvering. | [src](../../../core/services/gate_commit.py#L44) |

## `core/services/gate_enforcement.py`
_Governed per-gate enforce-kill-switch for PRE-eksekverings-gates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_enforced` | `(nerve, klass)` | True hvis gatens håndhævelse er aktiv. | [src](../../../core/services/gate_enforcement.py#L32) |
| function | `note_suppressed_block` | `(nerve, cluster, reason)` | En gate ville have blokeret, men håndhævelsen er governed-OFF → registrér det som | [src](../../../core/services/gate_enforcement.py#L47) |

## `core/services/gate_eval.py`
_Gate-eval & paritets-harness (unified-gate Task 0.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_as_verdict` | `(name, raw)` | Normalisér en gate-returværdi til Verdict (genbruger kernens parser). | [src](../../../core/services/gate_eval.py#L21) |
| function | `replay` | `(turns, gate_fn, *, name=…)` | Kør gate_fn over hver turns `ctx` og returnér normaliserede verdicts. | [src](../../../core/services/gate_eval.py#L26) |
| function | `parity` | `(turns, old_fn, new_fn)` | Sammenlign to gate-implementeringer pr. turn. Grøn paritet = nul mismatches. | [src](../../../core/services/gate_eval.py#L38) |
| function | `score` | `(turns, gate_fn, *, label_key=…)` | Mål en gates beslutning mod ground-truth-labels pr. turn. | [src](../../../core/services/gate_eval.py#L52) |
| function | `load_fixtures` | `(path)` | Læs et jsonl-fixturset (én turn pr. linje). Tomme/kommenterede linjer ignoreres. | [src](../../../core/services/gate_eval.py#L73) |

## `core/services/gate_execution.py`
_Execution-cluster gate 🔒 — én graderet SECURITY-gate for ALLE tool-eksekverings-_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_red` | `(nerve, reason, classification)` | — | [src](../../../core/services/gate_execution.py#L42) |
| function | `_yellow` | `(nerve, classification)` | — | [src](../../../core/services/gate_execution.py#L47) |
| function | `_green` | `(nerve, classification)` | — | [src](../../../core/services/gate_execution.py#L52) |
| function | `execution_gate` | `(ctx)` | Én SECURITY-gate, dispatch på ctx['action']. Returnér ét graderet Verdict. | [src](../../../core/services/gate_execution.py#L58) |
| class | `ExecCheck` | `` | — | [src](../../../core/services/gate_execution.py#L159) |
| function | `_to_check` | `(v)` | — | [src](../../../core/services/gate_execution.py#L166) |
| function | `_decide` | `(nerve, ctx)` | Route gennem Den Intelligente Central (SECURITY). Defense-in-depth: hvis central- | [src](../../../core/services/gate_execution.py#L182) |
| function | `check_command` | `(command, session_id=…, *, blocked_only=…)` | — | [src](../../../core/services/gate_execution.py#L211) |
| function | `check_file` | `(path, session_id=…, *, kind=…, blocked_only=…)` | — | [src](../../../core/services/gate_execution.py#L218) |
| function | `check_workspace_trust` | `(tool_name)` | — | [src](../../../core/services/gate_execution.py#L225) |
| function | `check_operator` | `(path, session_id=…, *, file_exists=…)` | — | [src](../../../core/services/gate_execution.py#L230) |
| function | `check_upload` | `(path, *, block_on_unavailable=…)` | Malware-scan en uploadet fil GENNEM Centralen (SECURITY). .allowed=False ⇔ infected/ | [src](../../../core/services/gate_execution.py#L237) |

## `core/services/gate_kernel.py`
_GateKernel — central orchestrator for alle gates (spec 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Decision` | `` | — | [src](../../../core/services/gate_kernel.py#L23) |
| class | `GateClass` | `` | — | [src](../../../core/services/gate_kernel.py#L30) |
| class | `Verdict` | `` | — | [src](../../../core/services/gate_kernel.py#L39) |
| method | `Verdict.is_blocking` | `(self)` | — | [src](../../../core/services/gate_kernel.py#L49) |
| function | `worst` | `(verdicts)` | Aggregeret beslutning efter præcedens RED>YELLOW>GREEN>SKIP. | [src](../../../core/services/gate_kernel.py#L53) |
| class | `_Gate` | `` | — | [src](../../../core/services/gate_kernel.py#L61) |
| class | `GateKernel` | `` | — | [src](../../../core/services/gate_kernel.py#L70) |
| method | `GateKernel.__init__` | `(self, *, flag_reader=…, emit=…)` | — | [src](../../../core/services/gate_kernel.py#L71) |
| method | `GateKernel.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/gate_kernel.py#L79) |
| method | `GateKernel.gates_for` | `(self, phase)` | — | [src](../../../core/services/gate_kernel.py#L84) |
| method | `GateKernel._fail_verdict` | `(self, g, reason)` | — | [src](../../../core/services/gate_kernel.py#L88) |
| method | `GateKernel._run_one` | `(self, g, ctx)` | — | [src](../../../core/services/gate_kernel.py#L94) |
| method | `GateKernel.run_phase` | `(self, phase, ctx)` | Kør alle gates i en fase isoleret; emit ÉT event; returnér verdicts. | [src](../../../core/services/gate_kernel.py#L122) |
| function | `_normalize` | `(g, raw)` | Tillad gates at returnere en færdig Verdict, et dict, eller None (=GREEN). | [src](../../../core/services/gate_kernel.py#L149) |
| function | `_default_flag_reader` | `(flag_key)` | Returnér True/False hvis flag'et er EKSPLICIT sat i shared_cache, ellers None | [src](../../../core/services/gate_kernel.py#L168) |
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/gate_kernel.py#L183) |
| function | `kernel` | `()` | — | [src](../../../core/services/gate_kernel.py#L195) |

## `core/services/gate_loop.py`
_Loop-cluster gate — agentisk loop-kontrol, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `loop_gate` | `(ctx)` | ctx: {round, max_rounds, consecutive_empty, max_empty, consecutive_tool_only, | [src](../../../core/services/gate_loop.py#L25) |

## `core/services/gate_memory.py`
_Memory-cluster gate — promotion til identitets-filer, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_candidate_text` | `(candidate)` | — | [src](../../../core/services/gate_memory.py#L25) |
| function | `memory_promotion_gate` | `(ctx)` | ctx: {candidate, kind: 'user_md'|'memory_md'}. Returnér ét GRADERET Verdict. | [src](../../../core/services/gate_memory.py#L32) |

## `core/services/gate_mutation.py`
_Mutation-cluster gate 🔒 — én graderet SECURITY-gate + ÉN kanonisk kilde for de_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hits` | `(target, blocklist)` | — | [src](../../../core/services/gate_mutation.py#L60) |
| function | `mutation_gate` | `(ctx)` | Én SECURITY-gate, dispatch på ctx['kind']: 'module' | 'prompt' | 'record'. | [src](../../../core/services/gate_mutation.py#L66) |
| class | `MutCheck` | `` | — | [src](../../../core/services/gate_mutation.py#L128) |
| function | `_decide` | `(nerve, ctx)` | Route gennem Den Intelligente Central (SECURITY, fail-CLOSED). Defense-in-depth: | [src](../../../core/services/gate_mutation.py#L133) |
| function | `check_module` | `(target)` | auto_improvement_proposer._is_safe_target — True ⇔ sikkert at foreslå. | [src](../../../core/services/gate_mutation.py#L147) |
| function | `check_prompt_target` | `(name)` | prompt_mutation_loop._check_target — allowed + besked (kald-stedet raiser). | [src](../../../core/services/gate_mutation.py#L152) |
| function | `check_record` | `(target_path)` | identity_mutation_log.record_mutation — allowed + blok-grund. | [src](../../../core/services/gate_mutation.py#L158) |

## `core/services/gate_privacy.py`
_Privacy-cluster gate 🔒 — cross-user-deling, GRADERET + fail-CLOSED._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `privacy_gate` | `(ctx)` | ctx: {text, current_user_id}. Returnér ét SECURITY-Verdict for cross-user-deling. | [src](../../../core/services/gate_privacy.py#L26) |

## `core/services/gate_proactivity.py`
_Proactivity-cluster gate — verifikations-disciplin, GRADERET (R2 blød / R2.5 hård)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `proactivity_gate` | `(ctx)` | ctx: {reasoning_tier}. Returnér ét GRADERET Verdict for verifikations-disciplin. | [src](../../../core/services/gate_proactivity.py#L26) |

## `core/services/gate_review.py`
_Review-cluster gate — selv-review-vurdering, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `review_gate` | `(ctx)` | ctx: {review} hvor review har risk_level (low/med/high) + score. | [src](../../../core/services/gate_review.py#L23) |

## `core/services/gate_shadow.py`
_Track 2 — SHADOW-kørsel af de sovende post_output-gates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_enforced` | `(nerve)` | True hvis gaten er graduated til enforce (i _ENFORCED) OG ikke kill-switchet fra. | [src](../../../core/services/gate_shadow.py#L60) |
| function | `_enforce_verdict` | `(nerve, cluster, klass, verdict)` | Håndhæv en enforced gates ikke-grønne verdict = gør det SYNLIGT som central-incident. | [src](../../../core/services/gate_shadow.py#L71) |
| function | `POST_OUTPUT_GATES_CLUSTERS` | `()` | (nerve, cluster) i kald-rækkefølge — til test/introspektion. | [src](../../../core/services/gate_shadow.py#L97) |
| function | `_shadow_enabled` | `()` | True medmindre gate_kernel.shadow er EKSPLICIT slået fra. Fail-open til ON | [src](../../../core/services/gate_shadow.py#L102) |
| function | `_resolve` | `(mod_path, fn_attr)` | — | [src](../../../core/services/gate_shadow.py#L112) |
| function | `run_post_output_shadow` | `(ctx)` | Kør de 5 sovende gates i SKYGGE via central().decide. | [src](../../../core/services/gate_shadow.py#L117) |

## `core/services/gate_skill.py`
_Skill-Safety-cluster gate 🔒 — graderet SECURITY-gate for skill-indholds-scanning_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `skill_gate` | `(ctx)` | Scan skill-indhold via skill_scanner; returnér graderet Verdict. | [src](../../../core/services/gate_skill.py#L29) |
| class | `SkillScanVerdict` | `` | ScanResult-lignende facade så call-sites er near-drop-in. | [src](../../../core/services/gate_skill.py#L48) |
| method | `SkillScanVerdict.as_dict` | `(self)` | — | [src](../../../core/services/gate_skill.py#L55) |
| function | `_decide` | `(ctx)` | Route gennem Centralen (SECURITY, fail-CLOSED). Central-katastrofe → kør gaten | [src](../../../core/services/gate_skill.py#L59) |
| function | `check_skill_scan` | `(content)` | Scan skill-indhold gennem Centralen. Returnér ScanResult-lignende facade. | [src](../../../core/services/gate_skill.py#L74) |

## `core/services/gate_truth.py`
_Unified TruthGate (cluster B). Smelter Truth-klyngens tre homogene Verdict-gates_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `truth_gate` | `(ctx)` | Kør de tre Truth-checks på samme ctx og kombinér til ét Verdict. | [src](../../../core/services/gate_truth.py#L17) |
| function | `register_truth_nerve` | `(central)` | Registrér den unified TruthGate som post_output-nerve i Centralen. | [src](../../../core/services/gate_truth.py#L29) |

## `core/services/gate_verdict_ledger.py`
_Gate-verdict-ledger — in-memory akkumulator + batchet flush til persistent tabel._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record` | `(nerve, cluster, decision, reason=…)` | Akkumulér ét verdict in-memory. Billig, låst, kaster ALDRIG. | [src](../../../core/services/gate_verdict_ledger.py#L27) |
| function | `_drain` | `()` | Snapshot + nulstil akkumulatoren under lås. Returnerer delta-liste til UPSERT. | [src](../../../core/services/gate_verdict_ledger.py#L53) |
| function | `flush` | `()` | Skriv akkumulerede deltas til den persistente tabel. Returnerer antal rækker rørt. | [src](../../../core/services/gate_verdict_ledger.py#L67) |
| function | `summary` | `()` | Aggregeret verdict-fordeling pr. nerve fra den persistente tabel (survives restart). | [src](../../../core/services/gate_verdict_ledger.py#L81) |

## `core/services/ghost_networks.py`
_Ghost Networks — traces of old patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `archive_dead_nodes` | `(node_ids)` | — | [src](../../../core/services/ghost_networks.py#L9) |
| function | `describe_ghost_network` | `()` | — | [src](../../../core/services/ghost_networks.py#L18) |
| function | `format_ghost_for_prompt` | `()` | — | [src](../../../core/services/ghost_networks.py#L24) |
| function | `reset_ghost_networks` | `()` | — | [src](../../../core/services/ghost_networks.py#L30) |
| function | `build_ghost_networks_surface` | `()` | — | [src](../../../core/services/ghost_networks.py#L34) |

## `core/services/git_actions.py`
_Rolle-aware git-eksekvering for code mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_container` | `(repo, *a, timeout=…)` | — | [src](../../../core/services/git_actions.py#L16) |
| function | `commit_all_container` | `(repo, message)` | — | [src](../../../core/services/git_actions.py#L20) |
| function | `_operator_exec` | `(name, args)` | — | [src](../../../core/services/git_actions.py#L38) |
| function | `_ws_git` | `(root, uid, gitargs, timeout=…)` | Kør `git -C <root> <gitargs>` på brugerens bro. Returnér (rc, stdout, stderr). | [src](../../../core/services/git_actions.py#L43) |
| function | `commit_all_workstation` | `(root, uid, message)` | — | [src](../../../core/services/git_actions.py#L53) |
| function | `commit_all` | `(target, container_repo, uid, message)` | — | [src](../../../core/services/git_actions.py#L71) |
| function | `parse_owner_repo` | `(remote_url)` | — | [src](../../../core/services/git_actions.py#L83) |
| function | `_ws_git_raw` | `(root, uid, cmd, timeout=…)` | Kør vilkårlig kommando i `root` på brugerens bro (til gh). | [src](../../../core/services/git_actions.py#L94) |
| function | `create_pr` | `(target, container_repo, uid, title, body)` | Commit → branch hvis på default → push → PR (API, ellers gh-fallback). | [src](../../../core/services/git_actions.py#L104) |
| function | `_create_pr_gh` | `(ws, root, uid, base, branch, title, body)` | — | [src](../../../core/services/git_actions.py#L140) |
| function | `_split_gh` | `(args)` | — | [src](../../../core/services/git_actions.py#L154) |

## `core/services/github_connector.py`
_GitHub-connector — API-klient + tool-handlers (v1: issues + PRs)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `(token)` | — | [src](../../../core/services/github_connector.py#L53) |
| function | `_get` | `(user_id, path, params=…)` | — | [src](../../../core/services/github_connector.py#L61) |
| function | `list_issues` | `(user_id, repo, *, state=…)` | Issues i `repo` (owner/name). state: open|closed|all. | [src](../../../core/services/github_connector.py#L77) |
| function | `list_prs` | `(user_id, repo, *, state=…)` | Pull requests i `repo` (owner/name). state: open|closed|all. | [src](../../../core/services/github_connector.py#L92) |
| function | `_post` | `(user_id, path, payload)` | — | [src](../../../core/services/github_connector.py#L107) |
| function | `create_pr` | `(user_id, repo, *, head, base, title, body=…)` | Opret PR i `repo` (owner/name). head/base = branch-navne. | [src](../../../core/services/github_connector.py#L123) |

## `core/services/global_workspace.py`
_Global Workspace — shared broadcast buffer (Experiment 3: Global Workspace Theory)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish_to_workspace` | `(source, topic, signal_type, payload_summary)` | Add an entry to the shared workspace buffer. | [src](../../../core/services/global_workspace.py#L45) |
| function | `get_workspace_snapshot` | `()` | Return current workspace buffer as a list (newest last). | [src](../../../core/services/global_workspace.py#L63) |
| function | `_extract_topic` | `(event_kind, payload)` | Extract a short topic string from an event payload. | [src](../../../core/services/global_workspace.py#L69) |
| function | `_topic_jaccard` | `(topic_a, topic_b)` | Jaccard similarity between two topic strings (word-level). | [src](../../../core/services/global_workspace.py#L80) |
| function | `_handle_event` | `(kind, payload)` | Map eventbus event to workspace entry. | [src](../../../core/services/global_workspace.py#L91) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/global_workspace.py#L104) |
| function | `register_event_listeners` | `()` | Start background eventbus listener thread. | [src](../../../core/services/global_workspace.py#L120) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/global_workspace.py#L141) |

## `core/services/gmail_connector.py`
_Gmail-connector — API-klient + tool-handlers (vertical: search + list)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_token` | `(user_id)` | — | [src](../../../core/services/gmail_connector.py#L78) |
| function | `_headers` | `(token)` | — | [src](../../../core/services/gmail_connector.py#L85) |
| function | `_clamp` | `(n, lo, hi, default)` | — | [src](../../../core/services/gmail_connector.py#L89) |
| function | `_fetch_messages` | `(user_id, query, max_results)` | Fælles kerne for search/list: hent id-liste → berig med headers/snippet. | [src](../../../core/services/gmail_connector.py#L97) |
| function | `search` | `(user_id, query, *, max_results=…)` | — | [src](../../../core/services/gmail_connector.py#L142) |
| function | `list_inbox` | `(user_id, *, max_results=…)` | — | [src](../../../core/services/gmail_connector.py#L148) |
| function | `send_message` | `(user_id, to, subject, body)` | Send en mail på brugerens vegne. KRÆVER approval-flow før den eksponeres som tool. | [src](../../../core/services/gmail_connector.py#L152) |

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

