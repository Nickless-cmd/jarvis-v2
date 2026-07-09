# `core.services.07` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/counterfactual_engine_runtime.py`
_Daemon for periodic counterfactual reflection cycles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | Lazy per-workspace lock. Same workspace_id always returns same Lock. | [src](../../../core/services/counterfactual_engine_runtime.py#L23) |
| function | `_run_one_cycle` | `(workspace_id)` | Acquire workspace lock, run engine, release. Never raises. | [src](../../../core/services/counterfactual_engine_runtime.py#L33) |
| function | `_list_active_workspaces` | `()` | Phase 1: only the default workspace. | [src](../../../core/services/counterfactual_engine_runtime.py#L62) |
| function | `_loop` | `()` | — | [src](../../../core/services/counterfactual_engine_runtime.py#L70) |
| function | `start_counterfactual_runtime` | `()` | Start the periodic-evaluation daemon. Idempotent — safe to call multiple times. | [src](../../../core/services/counterfactual_engine_runtime.py#L80) |
| function | `stop_counterfactual_runtime` | `()` | Signal the loop to exit. | [src](../../../core/services/counterfactual_engine_runtime.py#L93) |

## `core/services/counterfactual_predictions.py`
_Counterfactual → world-model prediction binding._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_confidence_band` | `(numeric)` | Map a 0..1 confidence to the world-model band strings. | [src](../../../core/services/counterfactual_predictions.py#L68) |
| function | `bind_counterfactual_to_prediction` | `(*, cf_id, trigger_type, anchor=…, confidence=…, source=…, event_kind=…)` | Record a world-model prediction linked to a counterfactual. | [src](../../../core/services/counterfactual_predictions.py#L77) |
| function | `list_open_counterfactual_predictions` | `()` | Return all open predictions whose source=='counterfactual'. | [src](../../../core/services/counterfactual_predictions.py#L155) |
| function | `_is_horizon_expired` | `(prediction, now)` | Check if a prediction's horizon has passed (with grace period). | [src](../../../core/services/counterfactual_predictions.py#L173) |
| function | `_extract_event_kind` | `(prediction)` | Pull the event_kind tag out of a prediction's evidence list. | [src](../../../core/services/counterfactual_predictions.py#L183) |
| function | `_frequency_verdict` | `(*, event_kind, created_at)` | Compare event_kind frequency before vs after the prediction's birth. | [src](../../../core/services/counterfactual_predictions.py#L192) |
| function | `sweep_expired_counterfactual_predictions` | `(*, now=…)` | Auto-resolve counterfactual predictions whose horizon has expired. | [src](../../../core/services/counterfactual_predictions.py#L265) |
| function | `build_counterfactual_predictions_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/counterfactual_predictions.py#L354) |
| function | `_emit_counterfactual_predictions_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/counterfactual_predictions.py#L369) |

## `core/services/counterfactual_self_simulation.py`
_Counterfactual self-simulation for post-run learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `simulate_from_latest_episode` | `()` | — | [src](../../../core/services/counterfactual_self_simulation.py#L21) |
| function | `simulate_from_episode` | `(episode)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L28) |
| function | `build_counterfactual_surface` | `(*, limit=…)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L71) |
| function | `build_counterfactual_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L84) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L101) |
| function | `_actual_action` | `(episode)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L111) |
| function | `_alternatives_for_episode` | `(episode)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L119) |
| function | `_preferred_policy` | `(episode, alternatives)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L157) |
| function | `_confidence` | `(episode, alternatives)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L166) |
| function | `_load_records` | `()` | — | [src](../../../core/services/counterfactual_self_simulation.py#L174) |
| function | `_save_simulation` | `(sim)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L179) |
| function | `_feed_learning` | `(sim)` | — | [src](../../../core/services/counterfactual_self_simulation.py#L184) |

## `core/services/counterfactual_triggers.py`
_Trigger detection for counterfactual reflection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerEvent` | `` | A regret-worthy event normalized for counterfactual processing. | [src](../../../core/services/counterfactual_triggers.py#L22) |
| function | `_key_self_review` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L33) |
| function | `_key_conflict` | `(payload)` | Primary key for conflict.detected events. | [src](../../../core/services/counterfactual_triggers.py#L37) |
| function | `_key_decision` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L60) |
| function | `_key_review` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L64) |
| function | `_key_goal` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L68) |
| function | `_key_decision_kept` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L72) |
| function | `_key_conflict_resolved` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L76) |
| function | `cf_key` | `(workspace_id, event_type, primary_key)` | First-pass dedup hash. Same workspace+type+key = same hash = skip. | [src](../../../core/services/counterfactual_triggers.py#L99) |
| function | `_extract_summary` | `(payload)` | — | [src](../../../core/services/counterfactual_triggers.py#L105) |
| function | `fetch_recent_aspiration_triggers` | `(*, workspace_id, lookback_minutes=…)` | Query events table for recent aspiration-worthy (positive) events. | [src](../../../core/services/counterfactual_triggers.py#L113) |
| function | `fetch_recent_triggers` | `(*, workspace_id, lookback_minutes=…)` | Query events table for recent regret-worthy events. | [src](../../../core/services/counterfactual_triggers.py#L164) |

## `core/services/cowork_dispatch.py`
_Cowork dispatch — runtime→app instruktioner (spec §18.5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_app_instruction` | `(*, action, target_user, channel=…, payload=…, requester=…)` | Byg en struktureret app-instruktion. Rejser ValueError ved ugyldig action | [src](../../../core/services/cowork_dispatch.py#L17) |
| function | `dispatch_to_app` | `(*, action, target_user, channel=…, payload=…, requester=…)` | Byg + signalér en app-instruktion via eventbus. Appen udfører den lokalt. | [src](../../../core/services/cowork_dispatch.py#L38) |

## `core/services/cowork_feed.py`
_Cowork-feed: normaliserer items fra eksisterende kilder til én rolle-scopet_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_initiative_items` | `()` | Afventende initiativ-forslag fra initiative_queue. | [src](../../../core/services/cowork_feed.py#L13) |
| function | `_capability_items` | `()` | Afventende capability-/tool-godkendelses-requests (Mission Control surface). | [src](../../../core/services/cowork_feed.py#L23) |
| function | `_norm_initiative` | `(raw)` | — | [src](../../../core/services/cowork_feed.py#L34) |
| function | `_norm_capability` | `(raw)` | — | [src](../../../core/services/cowork_feed.py#L45) |
| function | `_proposal_items` | `()` | Afventende autonomy-proposals (prop-xxxxxx): commits, planer, prompt- | [src](../../../core/services/cowork_feed.py#L63) |
| function | `_norm_proposal` | `(raw)` | — | [src](../../../core/services/cowork_feed.py#L73) |
| function | `build_queue` | `(*, user_id, is_owner)` | Saml + normalisér + rolle-scope den fulde godkendelses-kø. | [src](../../../core/services/cowork_feed.py#L86) |
| function | `_all_plans` | `()` | Alle planer fra plan_proposals (normaliseret med trin-progress). | [src](../../../core/services/cowork_feed.py#L99) |
| function | `list_plans` | `(*, user_id, is_owner)` | — | [src](../../../core/services/cowork_feed.py#L121) |
| function | `list_active_agents` | `(*, limit=…)` | Aktive dispatch-agenter til cowork command center (§19.5). Læser | [src](../../../core/services/cowork_feed.py#L134) |
| function | `_all_todos` | `()` | Alle todos på tværs af sessioner (agent_todos er session-keyed). | [src](../../../core/services/cowork_feed.py#L157) |
| function | `list_todos_feed` | `(*, user_id, is_owner)` | Todos til cowork. Owner ser alle; member får [] (todos er ikke user- | [src](../../../core/services/cowork_feed.py#L178) |
| function | `_raw_channels` | `()` | Konfigurerede kanaler (online = konfigureret/aktiv). Live connection-state | [src](../../../core/services/cowork_feed.py#L186) |
| function | `channel_status` | `()` | — | [src](../../../core/services/cowork_feed.py#L205) |

## `core/services/creative_drift_daemon.py`
_Creative drift daemon — generates spontaneous, unexpected ideas unrelated to current tasks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_creative_drift_daemon` | `(fragments)` | Maybe generate a spontaneous associative idea. | [src](../../../core/services/creative_drift_daemon.py#L38) |
| function | `get_latest_drift` | `()` | — | [src](../../../core/services/creative_drift_daemon.py#L73) |
| function | `build_creative_drift_surface` | `()` | — | [src](../../../core/services/creative_drift_daemon.py#L77) |
| function | `_gather_concrete_anchor` | `()` | Returns (anchor_text, anchor_kind) — a single concrete thing to drift | [src](../../../core/services/creative_drift_daemon.py#L91) |
| function | `_generate_drift_idea` | `(fragments)` | — | [src](../../../core/services/creative_drift_daemon.py#L125) |
| function | `_store_drift` | `(idea, now)` | — | [src](../../../core/services/creative_drift_daemon.py#L179) |

## `core/services/creative_impulse_daemon.py`
_Creative Impulse — unasked-for creations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L36) |
| function | `_creative_dir` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L40) |
| function | `_load` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L44) |
| function | `_save` | `(data)` | — | [src](../../../core/services/creative_impulse_daemon.py#L62) |
| function | `_dream_residue` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L79) |
| function | `_current_signals` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L93) |
| function | `_tokens_from` | `(text)` | — | [src](../../../core/services/creative_impulse_daemon.py#L117) |
| function | `_compose_poem` | `(tokens, signals)` | Structural poem — not LLM. 4 lines composed from available tokens. | [src](../../../core/services/creative_impulse_daemon.py#L123) |
| function | `_compose_essay_fragment` | `(residue, signals)` | A few sentences woven from residue phrases. | [src](../../../core/services/creative_impulse_daemon.py#L138) |
| function | `_compose_concept` | `(tokens)` | A naming game — combine 2 tokens into a concept. | [src](../../../core/services/creative_impulse_daemon.py#L153) |
| function | `_compose_snippet` | `(tokens)` | A tiny Python-like pseudo snippet from tokens. | [src](../../../core/services/creative_impulse_daemon.py#L162) |
| function | `_compose` | `(form)` | — | [src](../../../core/services/creative_impulse_daemon.py#L175) |
| function | `_compute_next_due` | `(now)` | — | [src](../../../core/services/creative_impulse_daemon.py#L196) |
| function | `_write_creation` | `(creation)` | — | [src](../../../core/services/creative_impulse_daemon.py#L201) |
| function | `create_now` | `()` | Force a creation (bypasses scheduling). | [src](../../../core/services/creative_impulse_daemon.py#L230) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/creative_impulse_daemon.py#L264) |
| function | `list_creations` | `(*, limit=…)` | — | [src](../../../core/services/creative_impulse_daemon.py#L284) |
| function | `build_creative_impulse_surface` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L289) |
| function | `_surface_summary` | `(creations, next_due)` | — | [src](../../../core/services/creative_impulse_daemon.py#L315) |
| function | `build_creative_impulse_prompt_section` | `()` | — | [src](../../../core/services/creative_impulse_daemon.py#L322) |
| function | `_seed_confidence` | `(creation)` | Score a creation as a 'seed worth showing' — higher = better. | [src](../../../core/services/creative_impulse_daemon.py#L342) |
| function | `_select_best_unsurfaced` | `()` | Find the highest-confidence creation that hasn't been surfaced. | [src](../../../core/services/creative_impulse_daemon.py#L378) |
| function | `surface_daily_seed` | `()` | Pick the best unsurfaced creation and mark it as surfaced. | [src](../../../core/services/creative_impulse_daemon.py#L392) |
| function | `build_creative_seed_section` | `()` | Build a prompt-awareness section if there's an unsurfaced seed waiting. | [src](../../../core/services/creative_impulse_daemon.py#L428) |

## `core/services/creative_instinct_daemon.py`
_Creative Instinct — spontaneous idea-seeds written to INCUBATOR.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L39) |
| function | `_incubator_path` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L43) |
| function | `_load` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L47) |
| function | `_save` | `(data)` | — | [src](../../../core/services/creative_instinct_daemon.py#L63) |
| function | `_hours_since` | `(iso_str)` | — | [src](../../../core/services/creative_instinct_daemon.py#L75) |
| function | `_recent_chat_topics` | `(limit=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L87) |
| function | `_recent_dream_hypotheses` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L101) |
| function | `_recent_avoidances` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L111) |
| function | `_current_mood_label` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L119) |
| function | `_compose_spark` | `(source_phrases, mood)` | Combine two source phrases into a spark. | [src](../../../core/services/creative_instinct_daemon.py#L129) |
| function | `_short_phrase` | `(text)` | — | [src](../../../core/services/creative_instinct_daemon.py#L150) |
| function | `_generate_seeds` | `(*, max_new)` | — | [src](../../../core/services/creative_instinct_daemon.py#L157) |
| function | `_write_incubator_md` | `(seeds)` | Overwrite INCUBATOR.md with current active seed list. | [src](../../../core/services/creative_instinct_daemon.py#L194) |
| function | `_age_seeds` | `(seeds)` | Mature or wither seeds based on age. Returns True if any changed. | [src](../../../core/services/creative_instinct_daemon.py#L224) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L242) |
| function | `list_seeds` | `(*, status=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L273) |
| function | `mark_seed` | `(seed_id, *, status)` | — | [src](../../../core/services/creative_instinct_daemon.py#L280) |
| function | `build_creative_instinct_surface` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L295) |
| function | `_surface_summary` | `(active, adopted, withered)` | — | [src](../../../core/services/creative_instinct_daemon.py#L325) |
| function | `build_creative_instinct_prompt_section` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L342) |

## `core/services/creative_journal_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_creative_journal_cycle` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L23) |
| function | `build_creative_journal_surface` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L125) |
| function | `creative_journal_dir` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L144) |
| function | `list_creative_journal_entries` | `(*, limit=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L149) |
| function | `_build_journal_entry` | `(*, chronicle_entries, life_projects, broken_decisions, klangbraet, voice_anchor)` | — | [src](../../../core/services/creative_journal_runtime.py#L178) |
| function | `_build_prompt` | `(*, chronicle_entries, life_projects, broken_decisions, klangbraet, voice_anchor)` | — | [src](../../../core/services/creative_journal_runtime.py#L210) |
| function | `_sanitize_entry` | `(raw)` | — | [src](../../../core/services/creative_journal_runtime.py#L318) |
| function | `_write_journal_entry` | `(*, created_at, text, frontmatter=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L330) |
| function | `_should_skip_week` | `(*, chronicle_count, broken_decisions_count, life_projects_count)` | Return (skip?, reason). Skip when ALL three signals are absent/thin. | [src](../../../core/services/creative_journal_runtime.py#L360) |
| function | `_interval_days_for_state` | `(state)` | Return current cadence interval based on skip counter. | [src](../../../core/services/creative_journal_runtime.py#L378) |
| function | `_fetch_broken_decisions` | `(*, days_back=…, limit=…)` | Pull recent broken-decision summaries from the events table. | [src](../../../core/services/creative_journal_runtime.py#L388) |
| function | `_fetch_recent_top_motif` | `(*, days_back=…)` | Return the most-recent aesthetic motif from the last `days_back` days. | [src](../../../core/services/creative_journal_runtime.py#L440) |
| function | `_fetch_dominant_taste` | `(*, evidence_floor=…)` | Return 'dimension_name (value)' for the taste-dimension with largest |val - 0.5|. | [src](../../../core/services/creative_journal_runtime.py#L467) |
| function | `_fetch_affective_klangbraet` | `()` | Pull current affective signals — these shape tone, not content. | [src](../../../core/services/creative_journal_runtime.py#L512) |
| function | `_format_yaml_frontmatter` | `(*, created_at, chronicle_count, broken_decisions_count, life_projects_count, klangbraet, trigger)` | Render a YAML frontmatter block for journal entries. | [src](../../../core/services/creative_journal_runtime.py#L613) |
| function | `_quality_lane_enabled` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L662) |
| function | `_creative_journal_enabled` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L669) |
| function | `_state` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L674) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/creative_journal_runtime.py#L679) |

## `core/services/creative_projects.py`
_Creative Projects — multi-week persistent creative impulse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/creative_projects.py#L36) |
| function | `_load` | `()` | — | [src](../../../core/services/creative_projects.py#L40) |
| function | `_save` | `(data)` | — | [src](../../../core/services/creative_projects.py#L54) |
| function | `create_project` | `(*, title, intent, status=…)` | Create a new creative project. | [src](../../../core/services/creative_projects.py#L66) |
| function | `add_progress_note` | `(project_id, note)` | Append a progress note to a project. Updates updated_at. | [src](../../../core/services/creative_projects.py#L86) |
| function | `set_project_status` | `(project_id, status)` | — | [src](../../../core/services/creative_projects.py#L101) |
| function | `list_projects` | `(*, status=…)` | — | [src](../../../core/services/creative_projects.py#L115) |
| function | `get_project` | `(project_id)` | — | [src](../../../core/services/creative_projects.py#L123) |
| function | `_is_stale` | `(project)` | — | [src](../../../core/services/creative_projects.py#L130) |
| function | `build_creative_projects_surface` | `()` | — | [src](../../../core/services/creative_projects.py#L140) |
| function | `_surface_summary` | `(active, paused, dreaming, stale)` | — | [src](../../../core/services/creative_projects.py#L168) |
| function | `build_creative_projects_prompt_section` | `()` | Surface active/dreaming projects so he can resume or carry them. | [src](../../../core/services/creative_projects.py#L188) |

## `core/services/crisis_marker_detector.py`
_Crisis marker detector — flag identity-forming friction moments._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_detect_sustained_failure` | `(events)` | ≥5 consecutive errors of the same tool. | [src](../../../core/services/crisis_marker_detector.py#L43) |
| function | `_detect_unexpected_success` | `(events)` | Tick quality summary that jumped sharply. | [src](../../../core/services/crisis_marker_detector.py#L74) |
| function | `_detect_existential_moment` | `(events)` | Explicit identity-formation statements in recent messages. | [src](../../../core/services/crisis_marker_detector.py#L95) |
| function | `_detect_high_volatility` | `(events)` | Rapid mood shifts in recent personality snapshots. | [src](../../../core/services/crisis_marker_detector.py#L157) |
| function | `_recent_events` | `(hours=…)` | — | [src](../../../core/services/crisis_marker_detector.py#L196) |
| function | `scan_for_crisis_markers` | `()` | Run all detectors. Persist any new markers found. | [src](../../../core/services/crisis_marker_detector.py#L206) |
| function | `list_crisis_markers` | `(*, days_back=…, limit=…)` | — | [src](../../../core/services/crisis_marker_detector.py#L270) |
| function | `crisis_marker_section` | `()` | Awareness section showing recent crisis markers (last 7 days). | [src](../../../core/services/crisis_marker_detector.py#L283) |
| function | `_exec_scan_crisis_markers` | `(args)` | — | [src](../../../core/services/crisis_marker_detector.py#L301) |
| function | `_exec_list_crisis_markers` | `(args)` | — | [src](../../../core/services/crisis_marker_detector.py#L305) |

## `core/services/cross_agent_memory.py`
_Cross-agent memory — shared observations queryable across agents._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_all_observations` | `()` | Read full observation log from Layer 1 storage. | [src](../../../core/services/cross_agent_memory.py#L37) |
| function | `_filter_by_freshness` | `(records, days)` | — | [src](../../../core/services/cross_agent_memory.py#L49) |
| function | `_keyword_score` | `(text, query)` | Cheap relevance score: count of query keywords in text, normalised. | [src](../../../core/services/cross_agent_memory.py#L56) |
| function | `cross_agent_recall` | `(*, query, requesting_role=…, exclude_roles=…, days_back=…, limit=…, min_score=…)` | Find relevant observations from OTHER agents matching the query. | [src](../../../core/services/cross_agent_memory.py#L68) |
| function | `cross_agent_recall_section` | `(role, query)` | Format cross-agent recall as text for sub-agent system_prompt injection. | [src](../../../core/services/cross_agent_memory.py#L130) |
| function | `_exec_cross_agent_recall` | `(args)` | — | [src](../../../core/services/cross_agent_memory.py#L146) |

## `core/services/cross_session_threads.py`
_Cross-Session Threads — sustained thought lines across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/cross_session_threads.py#L26) |
| function | `_load` | `()` | — | [src](../../../core/services/cross_session_threads.py#L31) |
| function | `_save` | `(items)` | — | [src](../../../core/services/cross_session_threads.py#L45) |
| function | `create_thread` | `(*, topic, synopsis=…, status=…, opened_in_session=…)` | — | [src](../../../core/services/cross_session_threads.py#L57) |
| function | `pause_thread` | `(thread_id, *, note=…)` | — | [src](../../../core/services/cross_session_threads.py#L83) |
| function | `resume_thread` | `(thread_id, *, new_synopsis=…)` | — | [src](../../../core/services/cross_session_threads.py#L96) |
| function | `close_thread` | `(thread_id, *, reason=…)` | — | [src](../../../core/services/cross_session_threads.py#L112) |
| function | `update_synopsis` | `(thread_id, new_synopsis)` | — | [src](../../../core/services/cross_session_threads.py#L125) |
| function | `list_threads` | `(*, status=…)` | — | [src](../../../core/services/cross_session_threads.py#L136) |
| function | `get_thread` | `(thread_id)` | — | [src](../../../core/services/cross_session_threads.py#L143) |
| function | `build_cross_session_threads_surface` | `()` | — | [src](../../../core/services/cross_session_threads.py#L150) |
| function | `_surface_summary` | `(counts)` | — | [src](../../../core/services/cross_session_threads.py#L189) |
| function | `build_cross_session_threads_prompt_section` | `()` | Surface active + paused threads so Jarvis can resume them. | [src](../../../core/services/cross_session_threads.py#L202) |

## `core/services/cross_signal_analysis.py`
_Cross-Signal Analysis — find patterns across cognitive signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `analyze_signal_patterns` | `(*, limit_items=…)` | Find cross-signal patterns from accumulated cognitive data. | [src](../../../core/services/cross_signal_analysis.py#L20) |
| function | `build_cross_signal_analysis_surface` | `()` | — | [src](../../../core/services/cross_signal_analysis.py#L84) |

## `core/services/cross_user_share_guard.py`
_Altid-aktiv deling-guard — stopper Jarvis før han deler info om en ANDEN bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_outbound` | `(text, *, current_user_id, known_users, session_id=…)` | Tjek et udgående svar for omtale af andre brugere end samtalepartneren. | [src](../../../core/services/cross_user_share_guard.py#L25) |
| function | `check_against_registry` | `(text, *, current_user_id)` | Som check_outbound, men henter kendte brugere fra users-registry. | [src](../../../core/services/cross_user_share_guard.py#L80) |

## `core/services/curiosity_budget.py`
_Curiosity-budget service — Phase 1 (AGI track #6 Åben udforskning)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create curiosity_observations table + indexes. | [src](../../../core/services/curiosity_budget.py#L32) |
| function | `_today_iso` | `()` | — | [src](../../../core/services/curiosity_budget.py#L71) |
| function | `load_or_reset_budget` | `()` | Return current budget state. Resets to 5/5 if stored date != today. | [src](../../../core/services/curiosity_budget.py#L75) |
| function | `decrement_budget` | `(*, action, observation_id)` | Reduce remaining by 1, append to used_today, persist. | [src](../../../core/services/curiosity_budget.py#L92) |
| function | `remaining_today` | `()` | — | [src](../../../core/services/curiosity_budget.py#L121) |
| function | `record_observation` | `(action, args_json, observation_text, follow_up_hint)` | Persist an observation row; return the generated obs_id. | [src](../../../core/services/curiosity_budget.py#L129) |
| function | `fetch_recent_observations` | `(*, limit=…)` | Return newest-first list of recent observations (for awareness). | [src](../../../core/services/curiosity_budget.py#L156) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/curiosity_budget.py#L173) |
| function | `curiosity_enabled` | `()` | Read killswitch from settings. Fail-open: settings errors → True. | [src](../../../core/services/curiosity_budget.py#L185) |
| function | `idle_window_open` | `()` | — | [src](../../../core/services/curiosity_budget.py#L197) |
| function | `open_idle_window` | `()` | Mark window open IF there's still budget. No-op if budget exhausted. | [src](../../../core/services/curiosity_budget.py#L202) |
| function | `close_idle_window` | `(*, reason)` | Close the window. Reason is logged for diagnostics. | [src](../../../core/services/curiosity_budget.py#L212) |
| function | `format_curiosity_window_for_awareness` | `()` | Render the curiosity window text for prompt_contract injection. | [src](../../../core/services/curiosity_budget.py#L225) |

## `core/services/curiosity_consolidation.py`
_Curiosity-observations weekly consolidation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | — | [src](../../../core/services/curiosity_consolidation.py#L27) |
| function | `_fetch_observations` | `(since, until)` | — | [src](../../../core/services/curiosity_consolidation.py#L51) |
| function | `_build_prompt` | `(observations)` | — | [src](../../../core/services/curiosity_consolidation.py#L66) |
| function | `run_consolidation` | `(*, now=…)` | Build a consolidation note from last 7d observations. | [src](../../../core/services/curiosity_consolidation.py#L83) |
| function | `latest_consolidation_for_awareness` | `()` | Awareness section showing the most recent consolidation (≤7d old). | [src](../../../core/services/curiosity_consolidation.py#L127) |

## `core/services/curiosity_daemon.py`
_Curiosity daemon — detects gaps in Jarvis' thought stream and generates curiosity signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_open_questions` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L22) |
| function | `tick_curiosity_daemon` | `(fragments)` | Scan thought stream fragments for gaps. fragments: recent fragment buffer (latest first). | [src](../../../core/services/curiosity_daemon.py#L36) |
| function | `_detect_gap` | `(fragments)` | — | [src](../../../core/services/curiosity_daemon.py#L58) |
| function | `_generate_curiosity_signal` | `(topic, gap_type)` | Compose a short curiosity-signal label from the detected gap. | [src](../../../core/services/curiosity_daemon.py#L68) |
| function | `_curiosity_cue` | `(*, topic, gap_type)` | — | [src](../../../core/services/curiosity_daemon.py#L82) |
| function | `_store_curiosity` | `(signal)` | — | [src](../../../core/services/curiosity_daemon.py#L99) |
| function | `get_latest_curiosity` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L132) |
| function | `build_curiosity_surface` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L136) |

## `core/services/curiosity_hypothesis_debt.py`
_Active curiosity with hypothesis debt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_hypothesis_debt` | `(*, hypothesis, why_it_matters, resolving_observation, source=…, priority=…)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L15) |
| function | `maybe_register_from_text` | `(*, text, source=…)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L53) |
| function | `build_curiosity_debt_surface` | `(*, limit=…)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L74) |
| function | `build_curiosity_debt_prompt_section` | `()` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L87) |
| function | `_load` | `()` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L98) |
| function | `_save` | `(state)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L103) |

## `core/services/current_pull.py`
_Current pull — Jarvis' weekly self-set desire field._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_current_pull_daemon` | `()` | Weekly daemon tick. Generates a new pull if none active, expired, or stale. | [src](../../../core/services/current_pull.py#L44) |
| function | `_collect_appetite_texts` | `(*, days_back)` | Pull active appetite labels for landscape embedding. | [src](../../../core/services/current_pull.py#L142) |
| function | `_collect_chronicle_texts` | `(*, days_back)` | Pull chronicle narratives from the last `days_back` days. | [src](../../../core/services/current_pull.py#L163) |
| function | `_collect_journal_texts` | `(*, days_back)` | Pull journal entry bodies from the last `days_back` days. | [src](../../../core/services/current_pull.py#L191) |
| function | `_compute_landscape_embedding` | `()` | Build a mean-pooled embedding from the last 3 days of desire signals. | [src](../../../core/services/current_pull.py#L236) |
| function | `_pull_is_stale` | `(pull_text)` | Return (is_stale, cos_score). | [src](../../../core/services/current_pull.py#L264) |
| function | `_staleness_check_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L291) |
| function | `_should_run_staleness_check` | `(state, *, interval_hours)` | Throttle: only run the embedding check every `interval_hours`. | [src](../../../core/services/current_pull.py#L298) |
| function | `_archive_refresh_event` | `(*, state, refreshed_at, reason, stale_score, previous_pull)` | Append a refresh event to state['refresh_history'], capped at 5 (FIFO). | [src](../../../core/services/current_pull.py#L312) |
| function | `get_current_pull_for_prompt` | `()` | Return prompt fragment for visible chat injection — or empty string. | [src](../../../core/services/current_pull.py#L333) |
| function | `build_current_pull_surface` | `()` | — | [src](../../../core/services/current_pull.py#L360) |
| function | `_generate_pull` | `()` | Ask Jarvis what pulls at him right now. Returns one Danish sentence. | [src](../../../core/services/current_pull.py#L386) |
| function | `_sanitize` | `(raw)` | — | [src](../../../core/services/current_pull.py#L431) |
| function | `_expire_if_stale` | `()` | — | [src](../../../core/services/current_pull.py#L438) |
| function | `_load_state` | `()` | — | [src](../../../core/services/current_pull.py#L459) |
| function | `_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L464) |

## `core/services/daemon_health.py`
_Daemon-helbred (Fase 1) — gør de standalone daemon-tråde + silent eventbus-listeners_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `note_error` | `(daemon, error, **data)` | En daemon/listener fejlede. → observe (cluster=system, nerve=daemon_health, ok=False). | [src](../../../core/services/daemon_health.py#L17) |
| function | `note_tick` | `(daemon, *, ok=…, **data)` | En daemon kørte en cyklus. Valgfri helbreds-puls (brug sparsomt — fejl er hovedsignalet). | [src](../../../core/services/daemon_health.py#L30) |
| function | `daemon_health_summary` | `(*, window=…)` | Read-only: hvilke daemons har fejlet i seneste trace (til MC/debug). Self-safe. | [src](../../../core/services/daemon_health.py#L42) |

## `core/services/daemon_llm.py`
_Shared LLM call for daemons — cheap lane first, heartbeat model fallback._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_note_call` | `(daemon_name, hit)` | Registrér ét daemon_llm-kald + om det ramte cachen → central_timeseries. Self-safe. | [src](../../../core/services/daemon_llm.py#L25) |
| function | `daemon_llm_cache_snapshot` | `()` | Read-only: pr. daemon kald + cache-hits + hit-rate. Lav hit-rate + højt kald = | [src](../../../core/services/daemon_llm.py#L58) |
| function | `_get_cache_ttl` | `(daemon_name)` | Return TTL in seconds for a daemon. 0 means no caching. | [src](../../../core/services/daemon_llm.py#L99) |
| function | `_check_cache` | `(cache_key)` | Return cached response if present and not expired, else None. | [src](../../../core/services/daemon_llm.py#L104) |
| function | `_store_cache` | `(cache_key, text, daemon_name)` | Store response in cache with daemon-specific TTL. | [src](../../../core/services/daemon_llm.py#L116) |
| function | `daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call LLM for daemon output. Tries cache first, then cheap lane (Groq), | [src](../../../core/services/daemon_llm.py#L129) |
| function | `quality_daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path for QUALITY-CRITICAL daemons (self-review, decision-review, | [src](../../../core/services/daemon_llm.py#L149) |
| function | `daemon_public_safe_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path reserved for PUBLIC-SAFE prompts. | [src](../../../core/services/daemon_llm.py#L248) |
| function | `_daemon_llm_call_impl` | `(prompt, *, max_len, fallback, daemon_name, public_safe)` | — | [src](../../../core/services/daemon_llm.py#L270) |

## `core/services/daemon_manager.py`
_Daemon Manager — registry, lifecycle control, and state persistence for all daemons._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_file` | `()` | — | [src](../../../core/services/daemon_manager.py#L20) |
| function | `get_daemon_names` | `()` | — | [src](../../../core/services/daemon_manager.py#L436) |
| function | `_load_state` | `()` | — | [src](../../../core/services/daemon_manager.py#L440) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/daemon_manager.py#L450) |
| function | `_get_daemon_state` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L456) |
| function | `_set_daemon_state` | `(name, updates)` | — | [src](../../../core/services/daemon_manager.py#L460) |
| function | `_require_known` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L468) |
| function | `is_enabled` | `(name)` | Return True if the named daemon should run. Unknown daemons return True (safe default). | [src](../../../core/services/daemon_manager.py#L474) |
| function | `set_daemon_enabled` | `(name, enabled)` | — | [src](../../../core/services/daemon_manager.py#L483) |
| function | `get_effective_cadence` | `(name)` | Return interval in minutes: override if set, else default. | [src](../../../core/services/daemon_manager.py#L488) |
| function | `record_daemon_tick` | `(name, result)` | Record last_run_at and a summary of the tick result. Called by heartbeat_runtime. | [src](../../../core/services/daemon_manager.py#L497) |
| function | `_hours_since` | `(iso)` | — | [src](../../../core/services/daemon_manager.py#L506) |
| function | `get_all_daemon_states` | `()` | Return status for all registered daemons. | [src](../../../core/services/daemon_manager.py#L518) |
| function | `control_daemon` | `(name, action, *, interval_minutes=…)` | Control a daemon. Actions: enable, disable, restart, set_interval. | [src](../../../core/services/daemon_manager.py#L541) |
| function | `_restart_daemon` | `(name)` | Clear the module-level state variable so the daemon fires on next heartbeat tick. | [src](../../../core/services/daemon_manager.py#L572) |

## `core/services/daemon_memory_safeguard.py`
_Daemon memory safeguard — post-hoc check that Jarvis saved what mattered._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_memory_safeguard_surface` | `()` | Mission Control surface for the memory safeguard daemon. | [src](../../../core/services/daemon_memory_safeguard.py#L41) |
| function | `run` | `(**kwargs)` | Check last assistant turn for missed saves. Called by heartbeat. | [src](../../../core/services/daemon_memory_safeguard.py#L101) |

## `core/services/daily_journal.py`
_Daily journal synthesizer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../core/services/daily_journal.py#L49) |
| function | `_journal_path_for` | `(day)` | — | [src](../../../core/services/daily_journal.py#L56) |
| function | `journal_exists_for` | `(day)` | Findes der allerede en journal for denne dato? | [src](../../../core/services/daily_journal.py#L61) |
| function | `_fetch_chat_pairs_for_day` | `(day, limit=…)` | Hent user/assistant beskeder fra visible-chat sessions for denne dag. | [src](../../../core/services/daily_journal.py#L66) |
| function | `_fetch_brain_carries_for_day` | `(day, limit=…)` | Hent private_brain_records carry-snapshots fra dagen. | [src](../../../core/services/daily_journal.py#L97) |
| function | `_render_chat_excerpt` | `(pairs)` | — | [src](../../../core/services/daily_journal.py#L158) |
| function | `_render_brain_excerpt` | `(carries)` | — | [src](../../../core/services/daily_journal.py#L168) |
| function | `synthesize_daily_journal` | `(day=…, *, force=…)` | Generér og skriv dagens journal. | [src](../../../core/services/daily_journal.py#L180) |
| function | `_should_synthesize_now` | `(now=…)` | Returnér True hvis vi er i sengetids-vinduet og dagens journal mangler. | [src](../../../core/services/daily_journal.py#L250) |
| function | `_daemon_loop` | `()` | Wakes hver time, syntesizer dagens journal hvis vi er i vinduet. | [src](../../../core/services/daily_journal.py#L260) |
| function | `start_daily_journal_daemon` | `()` | Start daemon. Idempotent. | [src](../../../core/services/daily_journal.py#L279) |
| function | `stop_daily_journal_daemon` | `()` | — | [src](../../../core/services/daily_journal.py#L296) |

## `core/services/data_erasure.py`
_GDPR Art. 17 (ret til at blive glemt) — orkestrering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_id_tables` | `(conn)` | Tabeller der HAR en user_id-kolonne (minus beskyttede). Eksplicit opdaget, | [src](../../../core/services/data_erasure.py#L23) |
| function | `_sweep_user_tables` | `(user_id, *, connect=…)` | — | [src](../../../core/services/data_erasure.py#L38) |
| function | `_wipe_workspace` | `(user_id)` | Slet brugerens workspace-mappe — med STRAM sti-sikkerhed (kun en undermappe | [src](../../../core/services/data_erasure.py#L49) |
| function | `erase_user` | `(user_id, *, mode=…, actor=…, connect=…)` | Slet en brugers data. mode='soft' (reversibel) | 'hard' (permanent). | [src](../../../core/services/data_erasure.py#L63) |

## `core/services/day_shape_memory.py`
_Day Shape Memory — sensory depth over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/day_shape_memory.py#L31) |
| function | `_load` | `()` | — | [src](../../../core/services/day_shape_memory.py#L36) |
| function | `_save` | `(data)` | — | [src](../../../core/services/day_shape_memory.py#L54) |
| function | `_today_iso` | `()` | — | [src](../../../core/services/day_shape_memory.py#L66) |
| function | `_empty_day` | `(date_iso)` | — | [src](../../../core/services/day_shape_memory.py#L70) |
| function | `capture_sample` | `()` | Add one sample to today's accumulating shape. | [src](../../../core/services/day_shape_memory.py#L82) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — capture one shape sample per tick. | [src](../../../core/services/day_shape_memory.py#L165) |
| function | `_finalize_day` | `(day)` | Collapse raw sample arrays into summary stats for storage. | [src](../../../core/services/day_shape_memory.py#L170) |
| function | `_compute_today_shape` | `()` | — | [src](../../../core/services/day_shape_memory.py#L188) |
| function | `_median_historical_shape` | `(days)` | — | [src](../../../core/services/day_shape_memory.py#L196) |
| function | `detect_today_anomaly` | `()` | Compare today's running shape to recent-days median. | [src](../../../core/services/day_shape_memory.py#L215) |
| function | `build_day_shape_surface` | `()` | — | [src](../../../core/services/day_shape_memory.py#L261) |
| function | `_surface_summary` | `(current, history, anomaly)` | — | [src](../../../core/services/day_shape_memory.py#L277) |
| function | `build_day_shape_prompt_section` | `()` | Surfaces only when today differs noticeably from baseline. | [src](../../../core/services/day_shape_memory.py#L292) |

## `core/services/db_sentinel.py`
_DB-cluster — observabilitet + flag for jarvis.db's helbred. IKKE en blokerende gate og_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_list_tables` | `()` | — | [src](../../../core/services/db_sentinel.py#L27) |
| function | `census` | `()` | Row-count pr. tabel. Best-effort; en fejlende tabel udelades. | [src](../../../core/services/db_sentinel.py#L40) |
| function | `dead_table_candidates` | `()` | Tabeller med 0 rækker = KANDIDATER til oprydning. KUN til menneskelig review — | [src](../../../core/services/db_sentinel.py#L57) |
| function | `_load_prev` | `()` | — | [src](../../../core/services/db_sentinel.py#L64) |
| function | `_save` | `(c)` | — | [src](../../../core/services/db_sentinel.py#L73) |
| function | `scan` | `()` | Census + vækst-delta vs forrige snapshot + flag egregious vækst. Returnér rapport. | [src](../../../core/services/db_sentinel.py#L81) |
| function | `observe` | `()` | Kør scan + central.observe(summary) + flag egregious vækst som incident (review). | [src](../../../core/services/db_sentinel.py#L105) |
| function | `build_db_health_surface` | `()` | MC-surface — read-only meta-projektion af DB-helbred + kandidat-død-liste til review. | [src](../../../core/services/db_sentinel.py#L131) |

## `core/services/decision_adherence_gate.py`
_Gate 1: Decision-adherence gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decision_adherence_section` | `()` | Build an escalation prompt section based on current decision adherence. | [src](../../../core/services/decision_adherence_gate.py#L27) |

## `core/services/decision_enforcement.py`
_Decision enforcement — close the loop between commitment and behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `enforcement_section` | `()` | High-priority awareness: lists active decisions as obligations + asks | [src](../../../core/services/decision_enforcement.py#L38) |
| function | `_build_breach_prompt` | `(assistant_text, decisions)` | — | [src](../../../core/services/decision_enforcement.py#L106) |
| function | `_parse_breaches` | `(text)` | — | [src](../../../core/services/decision_enforcement.py#L125) |
| function | `detect_breach_in_output` | `(assistant_text)` | Return list of detected breaches. Empty if none. LLM-led. | [src](../../../core/services/decision_enforcement.py#L145) |
| function | `_poll_loop` | `()` | — | [src](../../../core/services/decision_enforcement.py#L226) |
| function | `subscribe` | `()` | — | [src](../../../core/services/decision_enforcement.py#L266) |

## `core/services/decision_gate.py`
_Decision gate — pre-execution decision conflict detection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_decision_gate` | `(tool_name, tool_args=…, user_message=…)` | Check if a tool call conflicts with active decisions. | [src](../../../core/services/decision_gate.py#L27) |
| function | `evaluate_decision_conflict` | `(tool_name, tool_args=…, user_message=…)` | Graderet decision-conflict. Returnerer (severity, reason): | [src](../../../core/services/decision_gate.py#L115) |
| function | `_build_context` | `(tool_name, tool_args, user_message)` | Build a context string for conflict detection. | [src](../../../core/services/decision_gate.py#L182) |
| function | `_detect_conflict` | `(directive, context, decision)` | Detect if the context conflicts with a decision directive. | [src](../../../core/services/decision_gate.py#L199) |

## `core/services/decision_ghosts.py`
_Decision Ghosts — paths not taken AND paths confirmed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_rejected_path` | `(decision, reason, alternative)` | Record a path that was rejected and may carry regret potential. | [src](../../../core/services/decision_ghosts.py#L21) |
| function | `record_confirmed_path` | `(decision, outcome, key_factor=…)` | Record a decision that was kept and proved successful. | [src](../../../core/services/decision_ghosts.py#L35) |
| function | `record_reaffirmed_decision` | `(decision_id, title, verdict)` | Record that a decision was reviewed and kept. | [src](../../../core/services/decision_ghosts.py#L53) |
| function | `describe_ghost_decision` | `()` | Return the most salient regret-ghost. | [src](../../../core/services/decision_ghosts.py#L67) |
| function | `describe_success_echo` | `()` | Return the most salient success-echo, or empty string. | [src](../../../core/services/decision_ghosts.py#L75) |
| function | `format_decision_ghost_for_prompt` | `()` | Format the regret ghost for prompt injection (legacy). | [src](../../../core/services/decision_ghosts.py#L84) |
| function | `format_decision_echo_for_prompt` | `()` | Format the success echo for prompt injection. | [src](../../../core/services/decision_ghosts.py#L92) |
| function | `reset_decision_ghosts` | `()` | Reset both rejected and confirmed paths. | [src](../../../core/services/decision_ghosts.py#L104) |
| function | `build_decision_ghosts_surface` | `()` | Build observable surface for Mission Control. | [src](../../../core/services/decision_ghosts.py#L111) |

