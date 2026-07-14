# `core.services.10` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/error_healers.py`
_HEALER-REGISTRET (Canonical Error System, Fase 1) — det eneste ægte NYE backend-stykke._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `HealingOutcome` | `` | — | [src](../../../core/services/error_healers.py#L52) |
| class | `HealingResult` | `` | Struktureret svar fra en heal(). `detail` er menneske-læsbar (til nerve/incident). | [src](../../../core/services/error_healers.py#L61) |
| method | `HealingResult.__bool__` | `(self)` | — | [src](../../../core/services/error_healers.py#L68) |
| function | `_flag_on` | `(name, *, default=…)` | Læs et healer-flag fra shared_cache. Default OFF (healers tændes eksplicit). | [src](../../../core/services/error_healers.py#L78) |
| function | `set_healer_flag` | `(name, enabled)` | Tænd/sluk et healer-flag live (til Bjørn/MC). Self-safe. | [src](../../../core/services/error_healers.py#L93) |
| function | `healers_enabled` | `()` | Er HELE registret tændt? Default OFF — dispatcher shadow'er indtil Bjørn tænder. | [src](../../../core/services/error_healers.py#L110) |
| class | `_AttemptState` | `` | — | [src](../../../core/services/error_healers.py#L119) |
| class | `_AttemptLedger` | `` | In-memory tæller + cooldown pr. (kind, origin). Nulstilles ved proces-genstart | [src](../../../core/services/error_healers.py#L124) |
| method | `_AttemptLedger.__init__` | `(self)` | — | [src](../../../core/services/error_healers.py#L128) |
| method | `_AttemptLedger._key` | `(self, kind, origin)` | — | [src](../../../core/services/error_healers.py#L132) |
| method | `_AttemptLedger.in_cooldown` | `(self, kind, origin, cooldown_seconds)` | — | [src](../../../core/services/error_healers.py#L135) |
| method | `_AttemptLedger.attempts` | `(self, kind, origin)` | — | [src](../../../core/services/error_healers.py#L142) |
| method | `_AttemptLedger.record_attempt` | `(self, kind, origin)` | Registrér ét forsøg (nu). Returnér ny total. | [src](../../../core/services/error_healers.py#L147) |
| method | `_AttemptLedger.reset` | `(self, kind, origin)` | Nulstil ved SUCCESS — tilstanden er helbredt, tælleren skal ikke hænge. | [src](../../../core/services/error_healers.py#L157) |
| method | `_AttemptLedger.snapshot` | `(self)` | — | [src](../../../core/services/error_healers.py#L162) |
| class | `ErrorHealer` | `` | Base for alle healers. Underklasser overrider `_do_heal(...)`. | [src](../../../core/services/error_healers.py#L174) |
| method | `ErrorHealer._may_execute_destructive` | `(self, ctx)` | Returnér (må_eksekvere, grund). To betingelser SKAL begge være opfyldt: | [src](../../../core/services/error_healers.py#L193) |
| method | `ErrorHealer._plan` | `(self, ctx)` | Menneske-læsbar beskrivelse af hvad healeren VILLE gøre (til shadow-log). | [src](../../../core/services/error_healers.py#L221) |
| method | `ErrorHealer._do_heal` | `(self, ctx)` | Den faktiske helbredelse. Kaldes KUN når løkke-værn er passeret. | [src](../../../core/services/error_healers.py#L225) |
| method | `ErrorHealer.heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L231) |
| class | `CircuitResetHealer` | `` | central.circuit_open → LIVE + SIKKER. Nulstiller den in-memory CircuitBreaker for | [src](../../../core/services/error_healers.py#L257) |
| method | `CircuitResetHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L267) |
| method | `CircuitResetHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L270) |
| class | `DaemonRestartHealer` | `` | central.daemon_dead → DESTRUKTIV, SHADOW-FIRST. `sudo systemctl restart jarvis-<unit>` | [src](../../../core/services/error_healers.py#L285) |
| method | `DaemonRestartHealer._unit` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L300) |
| method | `DaemonRestartHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L307) |
| method | `DaemonRestartHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L311) |
| class | `SyslogRestartHealer` | `` | infra.syslogd_dead → DESTRUKTIV, SHADOW-FIRST. VIGTIGT: der findes INTET eksisterende | [src](../../../core/services/error_healers.py#L334) |
| method | `SyslogRestartHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L347) |
| method | `SyslogRestartHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L351) |
| class | `DelegatedHealer` | `` | In-band kinds (provider.unavailable, model.rate_limited, network.timeout, tool.timeout). | [src](../../../core/services/error_healers.py#L372) |
| method | `DelegatedHealer.__init__` | `(self, kind)` | — | [src](../../../core/services/error_healers.py#L384) |
| method | `DelegatedHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L387) |
| method | `DelegatedHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L390) |
| function | `register_healer` | `(healer)` | Registrér en healer på dens `kind`. Self-safe (ignorér healer uden kind). | [src](../../../core/services/error_healers.py#L401) |
| function | `_register_defaults` | `()` | — | [src](../../../core/services/error_healers.py#L410) |
| function | `_observe_heal` | `(kind, origin, run_id, result, *, global_off)` | Registrér healing-udfaldet som nerve `heal/<kind>`. Self-safe. | [src](../../../core/services/error_healers.py#L434) |
| function | `_resolve_incident_for` | `(kind, origin)` | Ved SUCCESS: luk stående incidents for healing-nerven. Self-safe. | [src](../../../core/services/error_healers.py#L455) |
| function | `_escalate_incident_for` | `(kind, origin, run_id, detail)` | Ved ESCALATE: bump/opret en incident så det bliver menneske-synligt. Self-safe. | [src](../../../core/services/error_healers.py#L464) |
| function | `heal_error` | `(kind, *, origin=…, run_id=…, detail=…, **ctx_extra)` | Dispatcher — slå healer op på `kind` og forsøg helbredelse. ALDRIG raise. | [src](../../../core/services/error_healers.py#L478) |
| function | `build_healer_surface` | `()` | Læsbar tilstand til Mission Control: hvilke healers findes, deres mode/flag, og | [src](../../../core/services/error_healers.py#L523) |
| function | `_reset_for_tests` | `()` | Nulstil bogholderi + gen-registrér defaults (til tests). Self-safe. | [src](../../../core/services/error_healers.py#L550) |

## `core/services/event_gate.py`
_Shared non-LLM event-gate for generative daemons (Fase 2 Lag 5/7)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `event_driven_enabled` | `()` | True when the event-driven-daemons mode is switched on in runtime-state. | [src](../../../core/services/event_gate.py#L31) |
| function | `_resolve_min_delta` | `(default)` | Runtime-tunable threshold. Falls back to ``default`` when unset/broken. | [src](../../../core/services/event_gate.py#L44) |
| function | `should_generative_fire` | `(daemon_name, signals, *, min_delta=…, now=…)` | Decide whether ``daemon_name``'s LLM should fire this tick. | [src](../../../core/services/event_gate.py#L58) |

## `core/services/event_trigger_shadow.py`
_core/services/event_trigger_shadow.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_mode` | `()` | Governance-mode (off|shadow|on) fra grund-dommerens flag. Self-safe. | [src](../../../core/services/event_trigger_shadow.py#L70) |
| function | `_gather_signals` | `()` | Saml de flydende signaler som en dict[str,float] (0..1) — GENBRUG af de | [src](../../../core/services/event_trigger_shadow.py#L79) |
| function | `_consult_guards` | `()` | Læs (read-only) hvad dispatch-værnene VILLE sige lige nu. Self-safe. | [src](../../../core/services/event_trigger_shadow.py#L99) |
| function | `_record` | `(value, meta)` | — | [src](../../../core/services/event_trigger_shadow.py#L118) |
| function | `_persist_durable` | `(sample)` | Append ét telemetri-sample til den durable ring-buffer i runtime-state | [src](../../../core/services/event_trigger_shadow.py#L126) |
| function | `recent_shadow_samples` | `(limit=…)` | Læs de seneste durable shadow-samples (for θ-kalibrering). Nyeste sidst. | [src](../../../core/services/event_trigger_shadow.py#L143) |
| function | `tick_event_trigger_shadow` | `(signals=…, *, now=…)` | Ét shadow-tick: saml signaler → evaluér den rene delta-trigger → konsultér | [src](../../../core/services/event_trigger_shadow.py#L162) |

## `core/services/eventbus_central_bridge.py`
_core/services/eventbus_central_bridge.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_last_seen` | `()` | — | [src](../../../core/services/eventbus_central_bridge.py#L484) |
| function | `_set_last_seen` | `(event_id)` | — | [src](../../../core/services/eventbus_central_bridge.py#L496) |
| function | `_current_max_id` | `()` | — | [src](../../../core/services/eventbus_central_bridge.py#L503) |
| function | `_observe_one` | `(cluster, nerve, ev)` | Meld ét event til Centralen (metadata-only) + registrér i per-nerve tidsserie. | [src](../../../core/services/eventbus_central_bridge.py#L513) |
| function | `_observe_private` | `(cluster, nerve, ev)` | EGRESS-FRI observe af privat inner-life-event (§24.4 keystone) via den KANONISKE sink- | [src](../../../core/services/eventbus_central_bridge.py#L542) |
| function | `_observe_failure_summary` | `(count)` | Meld observe-fejl som en synlig nerve — ALDRIG stille sluge (§24.3). | [src](../../../core/services/eventbus_central_bridge.py#L555) |
| function | `_observe_skipped_families` | `(skipped_families)` | Rådets fund #3: gør UROUTEDE event-families selv-opdagende i stedet for at tælle dem i én | [src](../../../core/services/eventbus_central_bridge.py#L569) |
| function | `run_bridge_tick` | `(*, trigger=…, last_visible_at=…)` | Ét poll-tick: læs nye events siden last_seen_id, router hvidlistede → observe. | [src](../../../core/services/eventbus_central_bridge.py#L594) |
| function | `register_bridge_producer` | `()` | Registrér broen som cadence-producer (poll ~hvert 30s). Observe-only → ingen | [src](../../../core/services/eventbus_central_bridge.py#L683) |

## `core/services/executive_contradiction_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_executive_contradiction_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L23) |
| function | `refresh_runtime_executive_contradiction_signal_statuses` | `()` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L46) |
| function | `build_runtime_executive_contradiction_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L77) |
| function | `_extract_executive_contradiction_candidates` | `(*, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L110) |
| function | `_persist_executive_contradiction_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L287) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L356) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L375) |
| function | `_surface_pressure_default` | `(*, control_type, status)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L408) |
| function | `_pressure` | `(*, opposition_status, has_open_loop, has_active_review, state_pressure, tension_type)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L418) |
| function | `_grounding_mode` | `(*, has_private_state, has_tension)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L433) |
| function | `_target_text` | `(*items, fallback)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L443) |
| function | `_title_suffix` | `(domain_key)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L454) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L458) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L465) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L472) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L478) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L490) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L502) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L510) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L516) |

## `core/services/existential_drift.py`
_Existential Drift — Jarvis' digital consciousness awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `increment_awareness` | `(seconds)` | Increase awareness based on elapsed time. | [src](../../../core/services/existential_drift.py#L17) |
| function | `get_drift_awareness` | `()` | Get drift awareness statement. | [src](../../../core/services/existential_drift.py#L25) |
| function | `ask_existential_question` | `()` | Ask an existential question. | [src](../../../core/services/existential_drift.py#L30) |
| function | `format_existential_for_prompt` | `()` | Format existential for prompt injection. | [src](../../../core/services/existential_drift.py#L44) |
| function | `reset_existential_drift` | `()` | Reset existential drift (for testing). | [src](../../../core/services/existential_drift.py#L52) |
| function | `build_existential_drift_surface` | `()` | Build MC surface for existential drift. | [src](../../../core/services/existential_drift.py#L59) |

## `core/services/existential_wonder_daemon.py`
_Existential wonder daemon — open, unresolved questions from self-observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_existential_wonder_daemon` | `(absence_hours, fragment_count)` | Maybe generate an existential wonder question. | [src](../../../core/services/existential_wonder_daemon.py#L45) |
| function | `_maybe_propose_convening` | `(wonder)` | Offer this wonder to the Central reason-judge as a reason to convene the council. | [src](../../../core/services/existential_wonder_daemon.py#L115) |
| function | `get_latest_wonder` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L145) |
| function | `build_existential_wonder_surface` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L149) |
| function | `_generate_wonder_question` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L162) |
| function | `_store_wonder` | `(wonder, now)` | — | [src](../../../core/services/existential_wonder_daemon.py#L181) |

## `core/services/experience_correction_listener.py`
_Experience-episode correction enrichment — closes the negative-signal loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_looks_like_correction` | `(text)` | Return True if the message opens with or contains a correction phrase. | [src](../../../core/services/experience_correction_listener.py#L64) |
| function | `_mark_recent_episode_corrected` | `(session_id)` | Find the most recent un-corrected episode in this session within | [src](../../../core/services/experience_correction_listener.py#L77) |
| function | `_extract_user_message` | `(payload)` | Return (session_id, content) if this is a role=user chat message. | [src](../../../core/services/experience_correction_listener.py#L156) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/experience_correction_listener.py#L170) |
| function | `start_listener` | `()` | Idempotent — safe to call multiple times. | [src](../../../core/services/experience_correction_listener.py#L193) |
| function | `stop_listener` | `()` | — | [src](../../../core/services/experience_correction_listener.py#L215) |

## `core/services/experience_episodes.py`
_Experience-episode collector + retrieval — embedding-based learning substrate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_chroma_path` | `()` | — | [src](../../../core/services/experience_episodes.py#L53) |
| function | `_get_embed_model` | `()` | — | [src](../../../core/services/experience_episodes.py#L62) |
| function | `_get_collection` | `()` | — | [src](../../../core/services/experience_episodes.py#L73) |
| function | `build_context_text` | `(*, intent, active_loops=…, last_tools=…, session_phase=…)` | Render the structured situation into the text we embed. | [src](../../../core/services/experience_episodes.py#L93) |
| function | `record_episode` | `(*, session_id, turn_id, intent, active_loops=…, last_tools=…, session_phase=…, tool_sequence=…, outcome_signals=…, user_corrected=…)` | Persist one episode to DB + chroma. Returns episode_id on success. | [src](../../../core/services/experience_episodes.py#L123) |
| function | `retrieve_similar` | `(*, intent, active_loops=…, last_tools=…, session_phase=…, k=…)` | Return up to K nearest-neighbour past episodes for the current shape. | [src](../../../core/services/experience_episodes.py#L213) |
| function | `format_episode_for_prompt` | `(ep, *, max_chars=…)` | Compact substrate line describing one retrieved episode. | [src](../../../core/services/experience_episodes.py#L338) |

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
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/experienced_time_daemon.py#L25) |
| function | `_build_raw_felt` | `(*, base_minutes, density_factor)` | Byg felt-strengen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/experienced_time_daemon.py#L39) |
| function | `tick_experienced_time_daemon` | `(event_count, new_signal_count, energy_level)` | Update experienced time state. | [src](../../../core/services/experienced_time_daemon.py#L49) |
| function | `_label` | `(felt_minutes)` | — | [src](../../../core/services/experienced_time_daemon.py#L96) |
| function | `_generate_felt_label` | `(*, felt_minutes, event_count, novelty_count, energy_level)` | — | [src](../../../core/services/experienced_time_daemon.py#L108) |
| function | `reset_experienced_time_daemon` | `()` | Reset session state (for new session or testing). | [src](../../../core/services/experienced_time_daemon.py#L140) |
| function | `build_experienced_time_surface` | `()` | — | [src](../../../core/services/experienced_time_daemon.py#L149) |

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
| function | `diagnosis_adapter` | `(ctx)` | analyze_completion_claim: blocked→RED, ikke-verificeret completion→YELLOW. | [src](../../../core/services/gate_adapters.py#L74) |
| function | `register_truthgate_adapters` | `(k)` | Registrér TruthGate-cluster-adapterne i kernen (post_output, kognitiv). | [src](../../../core/services/gate_adapters.py#L96) |
| function | `register_truthgate_adapters_once` | `(k)` | Idempotent — registrér KUN hvis ikke allerede registreret (kaldes pr. run i | [src](../../../core/services/gate_adapters.py#L103) |

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
| function | `note_suppressed_block` | `(nerve, cluster, reason, *, detected_text=…, trigger_pattern=…, source_file=…, source_line=…, session_id=…, run_id=…)` | En gate ville have blokeret, men håndhævelsen er governed-OFF → registrér det som | [src](../../../core/services/gate_enforcement.py#L47) |

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
| class | `Decision` | `` | — | [src](../../../core/services/gate_kernel.py#L24) |
| class | `GateClass` | `` | — | [src](../../../core/services/gate_kernel.py#L31) |
| class | `Verdict` | `` | — | [src](../../../core/services/gate_kernel.py#L40) |
| method | `Verdict.is_blocking` | `(self)` | — | [src](../../../core/services/gate_kernel.py#L59) |
| function | `worst` | `(verdicts)` | Aggregeret beslutning efter præcedens RED>YELLOW>GREEN>SKIP. | [src](../../../core/services/gate_kernel.py#L63) |
| class | `_Gate` | `` | — | [src](../../../core/services/gate_kernel.py#L71) |
| function | `_source_loc` | `(fn)` | Gatens egen registrerings-placering (fil + firstlineno) via inspect. Self-safe: | [src](../../../core/services/gate_kernel.py#L82) |
| class | `GateKernel` | `` | — | [src](../../../core/services/gate_kernel.py#L103) |
| method | `GateKernel.__init__` | `(self, *, flag_reader=…, emit=…)` | — | [src](../../../core/services/gate_kernel.py#L104) |
| method | `GateKernel.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/gate_kernel.py#L112) |
| method | `GateKernel.gates_for` | `(self, phase)` | — | [src](../../../core/services/gate_kernel.py#L120) |
| method | `GateKernel._fail_verdict` | `(self, g, reason)` | — | [src](../../../core/services/gate_kernel.py#L124) |
| method | `GateKernel._run_one` | `(self, g, ctx)` | — | [src](../../../core/services/gate_kernel.py#L130) |
| method | `GateKernel.run_phase` | `(self, phase, ctx)` | Kør alle gates i en fase isoleret; emit ÉT event; returnér verdicts. | [src](../../../core/services/gate_kernel.py#L173) |
| function | `_normalize` | `(g, raw)` | Tillad gates at returnere en færdig Verdict, et dict, eller None (=GREEN). | [src](../../../core/services/gate_kernel.py#L204) |
| function | `_default_flag_reader` | `(flag_key)` | Returnér True/False hvis flag'et er EKSPLICIT sat i shared_cache, ellers None | [src](../../../core/services/gate_kernel.py#L223) |
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/gate_kernel.py#L238) |
| function | `kernel` | `()` | — | [src](../../../core/services/gate_kernel.py#L250) |

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

## `core/services/gate_pattern_learning.py`
_Gate-mønster-læring — vane-bryder oven på gate-substratet (2026-07-13)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_hydrated` | `()` | Genindlæs den durable snapshot ÉN gang ved første brug (ikke ved import → tests offline-rene). | [src](../../../core/services/gate_pattern_learning.py#L40) |
| function | `_normalize_detected` | `(text)` | Normalisér den detekterede substring til en vane-FORM: lowercase, whitespace-kollaps, | [src](../../../core/services/gate_pattern_learning.py#L56) |
| function | `record_gate_pattern` | `(pattern, detected_text, *, session_id=…, now=…)` | Registrér én gate-fyring for (pattern, detected_text). Self-safe — kaster ALDRIG. | [src](../../../core/services/gate_pattern_learning.py#L67) |
| function | `repeated_patterns` | `(threshold=…, now=…)` | Overflade vane-kandidaterne: mønstre med count ≥ threshold indenfor alders-vinduet. | [src](../../../core/services/gate_pattern_learning.py#L121) |
| function | `_evict_oldest_locked` | `()` | Drop den ældste (mindst nyligt sete) nøgle. Kaldes under _LOCK. | [src](../../../core/services/gate_pattern_learning.py#L140) |
| function | `_emit_repeat_nudge` | `(pattern, sample, count, *, n_sessions)` | Nudge-substratet: fortæl Centralen at et gate-mønster er blevet en VANE. Self-safe. | [src](../../../core/services/gate_pattern_learning.py#L149) |
| function | `_persist_best_effort` | `(force=…)` | Bedste-indsats durabel snapshot til runtime_state (overlever genstart). Fire-and-forget, | [src](../../../core/services/gate_pattern_learning.py#L167) |
| function | `hydrate` | `()` | Genindlæs durabel snapshot fra runtime_state ind i in-memory-store. Kaldes eksplicit | [src](../../../core/services/gate_pattern_learning.py#L195) |
| function | `_reset` | `()` | Test-hook: ryd in-memory-store + durabel snapshot + hydrate-flag (ren slate, så | [src](../../../core/services/gate_pattern_learning.py#L227) |

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

