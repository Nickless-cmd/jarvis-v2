# `core.services.09` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/development_sense.py`
_Development senses — realtime felt-sense of growth, stuck, appetite, resistance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_crisis_resolution_ratio` | `(days=…)` | Resolved-vs-opened over window. None when insufficient data. | [src](../../../core/services/development_sense.py#L34) |
| function | `_adherence_score` | `()` | — | [src](../../../core/services/development_sense.py#L50) |
| function | `_skill_principles_recent` | `(days=…)` | Count skill_mutations recorded in the last N days. Each is a | [src](../../../core/services/development_sense.py#L66) |
| function | `_tick_quality_trend_bonus` | `()` | — | [src](../../../core/services/development_sense.py#L86) |
| function | `growth_pulse` | `()` | Composite 0-1 pulse + components. None-safe. | [src](../../../core/services/development_sense.py#L96) |
| function | `stuck_signal` | `()` | Detect repeating friction without resolution. | [src](../../../core/services/development_sense.py#L139) |
| function | `_topic_words_from_thought_fragments` | `(limit=…)` | — | [src](../../../core/services/development_sense.py#L198) |
| function | `appetite_signal` | `()` | What words/topics show up unprompted in his thought stream + open | [src](../../../core/services/development_sense.py#L214) |
| function | `resistance_signal` | `()` | Where am I acting against my own commitments / drifting from baseline? | [src](../../../core/services/development_sense.py#L233) |
| function | `_is_after` | `(ts, cutoff)` | — | [src](../../../core/services/development_sense.py#L278) |
| function | `development_sense_section` | `()` | Render all 4 senses as one COMPACT prompt-awareness block (2026-05-03). | [src](../../../core/services/development_sense.py#L288) |

## `core/services/developmental_valence.py`
_Developmental Valence — compass needle for flourishing vs withering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_within_window` | `(iso_str, days=…)` | — | [src](../../../core/services/developmental_valence.py#L41) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/developmental_valence.py#L49) |
| function | `_intention_closure_rate` | `()` | Of goal_signals updated in the window, what fraction are still active? | [src](../../../core/services/developmental_valence.py#L55) |
| function | `_dream_confirmation_rate` | `()` | Of dream_hypothesis_signals in window, fraction still carried. | [src](../../../core/services/developmental_valence.py#L76) |
| function | `_loop_health` | `()` | Closed vs total loops in window. Higher = closing what opens. | [src](../../../core/services/developmental_valence.py#L93) |
| function | `_relation_sustained` | `()` | Trust trajectory tail + recent contact density. | [src](../../../core/services/developmental_valence.py#L111) |
| function | `_metabolism` | `()` | Signal → action conversion. | [src](../../../core/services/developmental_valence.py#L149) |
| function | `_compute_components` | `()` | — | [src](../../../core/services/developmental_valence.py#L175) |
| function | `_components_to_vector` | `(components)` | Average of available components, re-centered to [-1, +1]. | [src](../../../core/services/developmental_valence.py#L185) |
| function | `_trajectory_label` | `(vector, delta)` | Map vector + derivative to trajectory label. | [src](../../../core/services/developmental_valence.py#L198) |
| function | `_recompute` | `()` | — | [src](../../../core/services/developmental_valence.py#L211) |
| function | `get_developmental_state` | `()` | Return cached compass state, recomputing only periodically. | [src](../../../core/services/developmental_valence.py#L242) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — no hot work, just trigger recompute when due. | [src](../../../core/services/developmental_valence.py#L252) |
| function | `build_developmental_valence_surface` | `()` | — | [src](../../../core/services/developmental_valence.py#L257) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/developmental_valence.py#L274) |
| function | `build_developmental_valence_prompt_section` | `()` | Speaks up when trajectory is notable — quiet when steady. | [src](../../../core/services/developmental_valence.py#L282) |
| function | `reset_developmental_valence` | `()` | Reset cached state (for testing). | [src](../../../core/services/developmental_valence.py#L305) |

## `core/services/device_pairing.py`
_QR-device-pairing (mobile companion ↔ desktop). Kort-levende engangs-koder._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gc` | `(now)` | — | [src](../../../core/services/device_pairing.py#L22) |
| function | `create_pairing` | `(user_id, role=…, *, now=…)` | Opret en pairing-kode for en (autentificeret) bruger. Returnerer {code, expires_in}. | [src](../../../core/services/device_pairing.py#L30) |
| function | `redeem` | `(code, *, now=…)` | Indløs en pairing-kode (engangs) → udsted friskt token. None hvis ukendt/udløbet. | [src](../../../core/services/device_pairing.py#L41) |
| function | `status` | `(code, *, now=…)` | Status på en pairing-kode (til desktop-poll): redeemed | pending | expired. | [src](../../../core/services/device_pairing.py#L54) |

## `core/services/device_presence.py`
_In-memory device-presence pr. bruger. Efemær — genopbygges af klient-pings._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DeviceState` | `` | — | [src](../../../core/services/device_presence.py#L40) |
| function | `reset` | `()` | Kun til tests. | [src](../../../core/services/device_presence.py#L53) |
| function | `record_ping` | `(user_id, device_key, platform, *, foreground, awake, network, interaction=…, location=…)` | — | [src](../../../core/services/device_presence.py#L59) |
| function | `_sanitize_location` | `(location)` | Validér og normalisér en indkommen lokation. Returnerer None ved ugyldigt. | [src](../../../core/services/device_presence.py#L98) |
| class | `RankedDevice` | `` | — | [src](../../../core/services/device_presence.py#L116) |
| function | `_recency_weight` | `(now, last_interaction_at)` | — | [src](../../../core/services/device_presence.py#L123) |
| function | `rank` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L130) |
| function | `prune` | `(user_id=…)` | — | [src](../../../core/services/device_presence.py#L189) |
| function | `summary` | `(user_id)` | — | [src](../../../core/services/device_presence.py#L202) |
| function | `location_for` | `(user_id)` | Bedst-kendte lokation for en bruger på tværs af enheder (til geo-tools). | [src](../../../core/services/device_presence.py#L226) |
| function | `debug_snapshot` | `(user_id)` | Diagnostik: live presence-tilstande + rank-resultat for én bruger. | [src](../../../core/services/device_presence.py#L246) |

## `core/services/device_tokens.py`
_Per-bruger FCM device-tokens. Egen tabel — rører ikke db.py's 33k linjer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/device_tokens.py#L11) |
| function | `register` | `(user_id, token, platform=…)` | — | [src](../../../core/services/device_tokens.py#L28) |
| function | `list_for_user` | `(user_id)` | — | [src](../../../core/services/device_tokens.py#L45) |
| function | `delete` | `(token)` | — | [src](../../../core/services/device_tokens.py#L57) |

## `core/services/diagnosis_gate.py`
_Diagnosis-gate (spec 2026-06-14) — fanger uverificerede diagnostiske konklusioner._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_promise_footnote` | `(claim_snippet)` | Fodnote-linje for en uverificeret completion-claim (konsistent stil). | [src](../../../core/services/diagnosis_gate.py#L53) |
| class | `DiagnosisResult` | `` | — | [src](../../../core/services/diagnosis_gate.py#L88) |
| class | `DiagnosisEvent` | `` | — | [src](../../../core/services/diagnosis_gate.py#L97) |
| function | `analyze_diagnosis` | `(text, *, tools_used=…)` | Ren detektion: er der en uverificeret diagnostisk konklusion i teksten? | [src](../../../core/services/diagnosis_gate.py#L110) |
| function | `analyze_completion_claim` | `(text, *, tools_used=…)` | Promise-ledger §8: påstår teksten en FULDFØRT handling ('det er committet/ | [src](../../../core/services/diagnosis_gate.py#L151) |
| function | `diagnosis_gate_enforce` | `(text, *, session_id=…, run_id=…, tools_used=…)` | Pipeline-hook (spec §3.2): kører efter fact-gate, før append_chat_message. | [src](../../../core/services/diagnosis_gate.py#L185) |

## `core/services/diary_synthesis_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_diary_synthesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L20) |
| function | `refresh_diary_synthesis_signal_statuses` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L54) |
| function | `build_diary_synthesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L58) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L62) |
| function | `_latest_carried_witness` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L124) |
| function | `_latest_chronicle_brief` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L134) |
| function | `_latest_self_narrative_continuity` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L141) |
| function | `_latest_metabolism_or_release` | `()` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L148) |
| function | `_diary_focus` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L158) |
| function | `_diary_state` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L172) |
| function | `_extract_release_state` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L193) |
| function | `_diary_weight` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L202) |
| function | `_extract_release_state_from_signal` | `(sig)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L227) |
| function | `_diary_summary` | `(witness, chronicle, self_narrative, metabolism, state)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L238) |
| function | `_extract_focus_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L281) |
| function | `_extract_release_semantics` | `(metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L305) |
| function | `_source_anchor_from_signals` | `(witness, chronicle, self_narrative, metabolism)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L329) |
| function | `_diary_confidence` | `(*signals)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L365) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L394) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L413) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L437) |
| function | `_diary_synthesis_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/diary_synthesis_signal_tracking.py#L449) |

## `core/services/dictation.py`
_Dictation-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_model_size` | `(explicit)` | — | [src](../../../core/services/dictation.py#L22) |
| function | `_get_model` | `(model_size, device=…, compute_type=…)` | — | [src](../../../core/services/dictation.py#L35) |
| function | `_join_segments` | `(segments)` | Saml whisper-segmenter til én streng. Ren funktion (testbar). | [src](../../../core/services/dictation.py#L45) |
| function | `transcribe_file` | `(path, *, model_size=…, language=…)` | Transskribér en lydfil. Returnerer {status, text, language}. | [src](../../../core/services/dictation.py#L50) |

## `core/services/discord_config.py`
_Discord config — load/save ~/.jarvis-v2/config/discord.json._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_discord_config` | `()` | Return config dict or None if missing/invalid. | [src](../../../core/services/discord_config.py#L16) |
| function | `save_discord_config` | `(config)` | Write config with chmod 600. Creates parent dir if needed. | [src](../../../core/services/discord_config.py#L29) |
| function | `is_discord_configured` | `()` | Return True if config exists and has all required keys. | [src](../../../core/services/discord_config.py#L36) |

## `core/services/discord_gateway.py`
_Discord gateway — runs discord.py in a dedicated daemon thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_discord_channel_for_session` | `(session_id)` | Lookup which Discord channel (if any) ejer denne session. | [src](../../../core/services/discord_gateway.py#L46) |
| function | `_persist_status` | `()` | Mirror current _status to runtime_state_kv for cross-process readers. | [src](../../../core/services/discord_gateway.py#L135) |
| function | `_status_heartbeat_loop` | `()` | Refresh persisted status every _STATUS_HB_INTERVAL seconds. | [src](../../../core/services/discord_gateway.py#L152) |
| function | `get_discord_status` | `()` | Return current gateway status. | [src](../../../core/services/discord_gateway.py#L167) |
| function | `_is_gateway_owner` | `()` | True if the discord client thread is running in this process. | [src](../../../core/services/discord_gateway.py#L210) |
| function | `_dispatch_to_runtime` | `(action, args)` | Forward a send intent to the runtime process via internal HTTP. | [src](../../../core/services/discord_gateway.py#L215) |
| function | `send_discord_message` | `(channel_id, text)` | Thread-safe: queue a message to be sent to a Discord channel. | [src](../../../core/services/discord_gateway.py#L236) |
| function | `_download_attachment` | `(attachment, session_id)` | Download a single discord.Attachment via attachment_service. | [src](../../../core/services/discord_gateway.py#L264) |
| function | `_build_attachment_prefix` | `(attachments, session_id)` | Build content prefix lines for all attachments in a Discord message. | [src](../../../core/services/discord_gateway.py#L277) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/discord_gateway.py#L297) |
| function | `send_discord_file` | `(channel_id, text, file_path)` | Queue a file send to a Discord channel. Validates path first. | [src](../../../core/services/discord_gateway.py#L302) |
| function | `_open_dm_and_send` | `(recipient_discord_id, text, timeout, max_retries=…, retry_delay=…)` | Open DM channel with a Discord user and queue a message. Gateway-process only. | [src](../../../core/services/discord_gateway.py#L316) |
| function | `send_dm_to_owner` | `(text, timeout=…)` | Send a DM directly to the owner via owner_discord_id. | [src](../../../core/services/discord_gateway.py#L395) |
| function | `send_dm_to_user` | `(recipient_discord_id, text, timeout=…)` | DM a known Discord user by ID. | [src](../../../core/services/discord_gateway.py#L409) |
| function | `_get_or_create_discord_session` | `(channel_id, is_dm, owner_discord_id, author_id=…)` | Return session_id for this Discord channel. Creates session if needed. | [src](../../../core/services/discord_gateway.py#L451) |
| function | `_split_message` | `(text, limit)` | Split text into chunks of at most `limit` characters. | [src](../../../core/services/discord_gateway.py#L489) |
| function | `_typing_loop` | `(channel_id)` | Keep showing 'typing...' indicator until the outbound message is sent. | [src](../../../core/services/discord_gateway.py#L500) |
| function | `_send_outbound_loop` | `()` | Asyncio coroutine that drains the outbound queue and sends to Discord. | [src](../../../core/services/discord_gateway.py#L526) |
| function | `_run_client` | `(config)` | Main coroutine: set up discord client and run until stopped. | [src](../../../core/services/discord_gateway.py#L579) |
| function | `_discord_thread_func` | `(config)` | Entry point for the daemon thread. | [src](../../../core/services/discord_gateway.py#L891) |
| function | `_announce_user_message_appended` | `(session_id, message)` | Udsend channel.chat_message_appended for en Discord-brugerbesked (Spor B). | [src](../../../core/services/discord_gateway.py#L909) |
| function | `_eventbus_subscriber_loop` | `()` | Background thread: watch eventbus for assistant responses in Discord sessions. | [src](../../../core/services/discord_gateway.py#L929) |
| function | `_resolve_channel_for_session` | `(session_id)` | Look up the Discord channel that originated a given session. | [src](../../../core/services/discord_gateway.py#L1051) |
| function | `start_discord_gateway` | `()` | Start gateway if config exists. Safe to call unconditionally. | [src](../../../core/services/discord_gateway.py#L1074) |
| function | `stop_discord_gateway` | `()` | Stop the gateway gracefully. | [src](../../../core/services/discord_gateway.py#L1118) |

## `core/services/dispatch_envelope.py`
_Robustness envelope builder + plausibility guard for the dispatch-redesign._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_to_int` | `(value)` | Coerce to int; on any failure return 0. | [src](../../../core/services/dispatch_envelope.py#L16) |
| function | `_to_float` | `(value)` | Coerce to float; on any failure return 0.0. | [src](../../../core/services/dispatch_envelope.py#L27) |
| function | `build_envelope` | `(*, status, tokens_in=…, tokens_out=…, cost_usd=…, duration_ms=…, tool_calls=…, result=…)` | Build a fixed 7-key dispatch envelope with coerced types. | [src](../../../core/services/dispatch_envelope.py#L35) |
| function | `validate_envelope` | `(env)` | Return plausibility warnings for an envelope. Empty list = clean. | [src](../../../core/services/dispatch_envelope.py#L60) |

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
_Dream-hypothesis signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_dream_hypothesis_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L60) |
| function | `refresh_runtime_dream_hypothesis_signal_statuses` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L85) |
| function | `build_runtime_dream_hypothesis_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L89) |
| function | `_extract_dream_hypothesis_candidates` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L95) |
| function | `_build_dream_snapshots` | `()` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L165) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L199) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L208) |
| function | `_dream_surface_item_view` | `(item)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L219) |
| function | `_dream_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L223) |
| function | `_dream_early_retire` | `(item)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L234) |
| function | `_build_hypothesis_type` | `(*, item, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L242) |
| function | `_build_signal_status` | `(*, hypothesis_type, recurrence_status, cadence_state)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L257) |
| function | `_build_hypothesis_note` | `(*, hypothesis_type, recurrence_type, domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L265) |
| function | `_build_hypothesis_anchor` | `(*, snapshot)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L284) |
| function | `_build_status_reason` | `(*, hypothesis_type)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L300) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L308) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L317) |
| function | `_recurrence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L322) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L327) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L332) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L337) |
| function | `_signal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L342) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L347) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/dream_hypothesis_signal_tracking.py#L352) |

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

## `core/services/egress_routing.py`
_Egress routing — which network egress a (provider, auth_profile) slot uses._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_egress` | `(provider, auth_profile)` | Which egress a slot uses. default profile -> 'home'; other profiles -> | [src](../../../core/services/egress_routing.py#L27) |
| function | `resolve_v6bind_source` | `(provider, auth_profile)` | Native-IPv6 account2 egress: bind the outbound socket to a distinct v6 | [src](../../../core/services/egress_routing.py#L40) |
| function | `_source_addr_usable` | `(addr)` | True if ``addr`` can be bound as an IPv6 source on this host (cheap check). | [src](../../../core/services/egress_routing.py#L75) |
| function | `resolve_nat64` | `(provider, auth_profile)` | True if this (provider, auth_profile) slot should egress via NAT64 instead | [src](../../../core/services/egress_routing.py#L100) |
| function | `nat64_synthesize` | `(host)` | Resolve ``host`` to a NAT64 synthetic IPv6 address via a DNS64 server. | [src](../../../core/services/egress_routing.py#L125) |
| function | `proxy_endpoints` | `()` | Return {egress: url|None}. Reads runtime config override if present, else | [src](../../../core/services/egress_routing.py#L166) |

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

