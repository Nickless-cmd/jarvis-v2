# `core.services.07` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `tick_conflict_daemon` | `(snapshot)` | Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode, | [src](../../../core/services/conflict_daemon.py#L31) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/conflict_daemon.py#L59) |
| function | `_conflict_tension` | `(conflict_type, snapshot)` | Rå spændings-score 0–1 fra rule-based signaler. Ingen LLM. | [src](../../../core/services/conflict_daemon.py#L73) |
| function | `_build_raw_conflict_phrase` | `(conflict_type, snapshot)` | Byg frasen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/conflict_daemon.py#L89) |
| function | `_detect_conflict` | `(snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L99) |
| function | `_generate_conflict_phrase` | `(conflict_type, snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L125) |
| function | `_store_conflict` | `(phrase, conflict_type)` | — | [src](../../../core/services/conflict_daemon.py#L174) |
| function | `get_latest_conflict` | `()` | — | [src](../../../core/services/conflict_daemon.py#L205) |
| function | `build_conflict_surface` | `()` | — | [src](../../../core/services/conflict_daemon.py#L209) |

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
| function | `get_last_conflict_trace` | `()` | Return the last conflict resolution trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L566) |
| function | `set_last_conflict_trace` | `(trace)` | Store the latest conflict trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L575) |
| function | `build_conflict_resolution_surface` | `()` | — | [src](../../../core/services/conflict_resolution.py#L580) |
| function | `_emit_resolved_event` | `(winning, losing)` | — | [src](../../../core/services/conflict_resolution.py#L589) |

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_consolidation_target_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L28) |
| function | `refresh_runtime_consolidation_target_signal_statuses` | `()` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L51) |
| function | `build_runtime_consolidation_target_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L82) |
| function | `_extract_consolidation_target_candidates` | `(*, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L118) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, chronicle, chronicle_brief, meaning, temperament, self_narrative, relation_continuity)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L238) |
| function | `_persist_consolidation_target_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L361) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L430) |
| function | `_derive_consolidation_state` | `(*, witness_status, chronicle_status, brief_status, active_like_count, session_count)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L455) |
| function | `_derive_consolidation_focus` | `(*, domain_key, chronicle, chronicle_brief)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L470) |
| function | `_derive_consolidation_weight` | `(*, active_like_count, support_count, session_count, brief_status)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L488) |
| function | `_consolidation_summary` | `(*, focus, consolidation_state, consolidation_weight)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L505) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L525) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L532) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L544) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L556) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L567) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/consolidation_target_signal_tracking.py#L581) |

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
| function | `_estimate_session_tokens` | `()` | — | [src](../../../core/services/context_window_manager.py#L39) |
| function | `_list_session_messages` | `(session_id=…, limit=…)` | — | [src](../../../core/services/context_window_manager.py#L47) |
| function | `_is_anchor` | `(message)` | — | [src](../../../core/services/context_window_manager.py#L69) |
| function | `apply_sliding` | `(messages, *, keep_recent=…, preserve_anchors=…)` | Keep last N messages, drop middle. Optionally preserve anchor messages. | [src](../../../core/services/context_window_manager.py#L76) |
| function | `estimate_pressure` | `()` | Read current session size + classify pressure level. | [src](../../../core/services/context_window_manager.py#L101) |
| function | `degradation_signal` | `()` | Detect signs that long context is hurting performance. | [src](../../../core/services/context_window_manager.py#L121) |
| function | `adaptive_pick_strategy` | `()` | Pick the best strategy for current state. | [src](../../../core/services/context_window_manager.py#L186) |
| function | `context_window_section` | `()` | Awareness-section warning when degradation detected. | [src](../../../core/services/context_window_manager.py#L197) |
| function | `_exec_context_pressure` | `(args)` | — | [src](../../../core/services/context_window_manager.py#L213) |
| function | `_exec_manage_context_window` | `(args)` | Apply a chosen context-management strategy. | [src](../../../core/services/context_window_manager.py#L221) |

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
| function | `get_latest_drift` | `()` | — | [src](../../../core/services/creative_drift_daemon.py#L86) |
| function | `build_creative_drift_surface` | `()` | — | [src](../../../core/services/creative_drift_daemon.py#L90) |
| function | `_gather_concrete_anchor` | `()` | Returns (anchor_text, anchor_kind) — a single concrete thing to drift | [src](../../../core/services/creative_drift_daemon.py#L104) |
| function | `_generate_drift_idea` | `(fragments)` | — | [src](../../../core/services/creative_drift_daemon.py#L138) |
| function | `_store_drift` | `(idea, now)` | — | [src](../../../core/services/creative_drift_daemon.py#L192) |

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

