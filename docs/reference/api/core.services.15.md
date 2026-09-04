# `core.services.15` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/network_health.py`
_core/services/network_health.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure_api_latency` | `(url=…, timeout=…)` | (ok, latency_ms) for den lokale API. TCP+HTTP round-trip mod /health. Self-safe. | [src](../../../core/services/network_health.py#L55) |
| function | `_latest` | `(cluster, nerve)` | Seneste tidsserie-værdi for en nerve (samme proces). None hvis tom. | [src](../../../core/services/network_health.py#L71) |
| function | `_hosts_down` | `()` | Hosts hvis seneste reachability-sample er 'nede' (infra_sense skriver -1.0 ved nede). | [src](../../../core/services/network_health.py#L80) |
| function | `run_network_health_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: fuse netværks-telemetri → ét signal. Bulletproof — kaster ALDRIG. | [src](../../../core/services/network_health.py#L95) |
| function | `_reset_for_tests` | `()` | Testhjælper — nulstil debounce-state. Ikke til produktionsbrug. | [src](../../../core/services/network_health.py#L171) |
| function | `register_network_health_producer` | `()` | Registrér netværks-helbred som cadence-producer (~hvert 2 min). Read-only, self-safe. | [src](../../../core/services/network_health.py#L179) |

## `core/services/non_visible_fallback.py`
_Non-visible (autonomous) LLM fallback chain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fallback_enabled` | `()` | Læs feature-flag; default False. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_fallback.py#L24) |
| function | `_rate_cap_enabled` | `()` | Læs rate-cap feature-flag; default False. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_fallback.py#L29) |
| function | `_observe_central` | `(payload)` | Task 15: let observabilitet på ON-stien → Centralens system/cheap_pool. | [src](../../../core/services/non_visible_fallback.py#L34) |
| function | `run_non_visible_with_fallback` | `(*, message, primary_call, run_is_autonomous, task_kind=…)` | Prøv primary_call() (ollama). Ved fejl: fald til den gratis cheap-lane | [src](../../../core/services/non_visible_fallback.py#L44) |

## `core/services/non_visible_lane_execution.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cheap_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L31) |
| function | `execute_cheap_lane` | `(*, message, task_kind=…)` | Run a message through the cheap lane. | [src](../../../core/services/non_visible_lane_execution.py#L51) |
| function | `execute_with_role_or_fallback` | `(*, message=…, provider=…, model=…, requires_tools=…, messages=…, tools=…, lane=…)` | Run the message on the role's preferred provider/model first, fall | [src](../../../core/services/non_visible_lane_execution.py#L70) |
| function | `local_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L268) |
| function | `coding_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L289) |
| function | `execute_coding_lane` | `(*, message)` | — | [src](../../../core/services/non_visible_lane_execution.py#L320) |
| function | `_lane_status` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L324) |
| function | `_coding_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L338) |
| function | `_local_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L546) |
| function | `_coding_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L607) |
| function | `_local_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L623) |
| function | `_github_copilot_auth_state` | `(*, oauth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L631) |
| function | `_github_copilot_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L655) |
| function | `_github_copilot_auth_status` | `(*, auth_state, exchange_readiness)` | — | [src](../../../core/services/non_visible_lane_execution.py#L679) |
| function | `_github_copilot_provider_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L711) |
| function | `_coding_lane_probe` | `(*, provider, model, auth_profile, credentials_ready, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L735) |
| function | `_probe_codex_cli_target` | `(*, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L777) |
| function | `_probe_ollama_local_target` | `(*, model, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L817) |
| function | `_probe_openai_coding_target` | `(*, provider, model, auth_profile, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L858) |
| function | `_execute_lane` | `(*, message, truth)` | — | [src](../../../core/services/non_visible_lane_execution.py#L901) |
| function | `_execute_codex_cli` | `(*, message, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1001) |
| function | `_resolve_codex_cli_executable` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L1044) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1059) |
| function | `_post_openai_responses` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1078) |
| function | `_post_openrouter_chat_completion` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1093) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1110) |
| function | `_extract_openrouter_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1130) |
| function | `_load_github_copilot_token` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1142) |
| function | `_github_copilot_request_headers` | `(session_token, *, accept=…)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1159) |
| function | `_post_github_copilot_chat_completion` | `(*, payload, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1174) |
| function | `_extract_github_copilot_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1192) |
| function | `fetch_github_copilot_models` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1204) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1231) |

## `core/services/non_visible_rate_cap.py`
_Global leaky-bucket rate cap FORAN den non-visible cheap-lane pool._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | Wall-clock i sekunder. Monkeypatchbar i tests. | [src](../../../core/services/non_visible_rate_cap.py#L34) |
| function | `reset` | `()` | Nulstil alle buckets (til tests + boot). | [src](../../../core/services/non_visible_rate_cap.py#L39) |
| function | `allow` | `(tokens=…)` | Forbrug 1 request + `tokens` tokens hvis begge buckets har plads; ellers | [src](../../../core/services/non_visible_rate_cap.py#L49) |

## `core/services/notes_connector.py`
_Huskesedler-connector (lokal) — simple per-bruger notater._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_store` | `()` | — | [src](../../../core/services/notes_connector.py#L68) |
| function | `_bucket` | `(user_id)` | — | [src](../../../core/services/notes_connector.py#L73) |
| function | `_save` | `(user_id, notes)` | — | [src](../../../core/services/notes_connector.py#L78) |
| function | `add_note` | `(user_id, text, *, now=…)` | — | [src](../../../core/services/notes_connector.py#L84) |
| function | `list_notes` | `(user_id, *, limit=…)` | — | [src](../../../core/services/notes_connector.py#L96) |
| function | `search_notes` | `(user_id, query)` | — | [src](../../../core/services/notes_connector.py#L105) |
| function | `delete_note` | `(user_id, note_id)` | — | [src](../../../core/services/notes_connector.py#L114) |

## `core/services/notification_bridge.py`
_Notification bridge — lets Jarvis push messages to the active session._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pin_session` | `(session_id)` | Record which session the user is currently viewing. Call on every user message. | [src](../../../core/services/notification_bridge.py#L30) |
| function | `get_pinned_session_id` | `()` | Return the currently pinned session ID, or empty string if none. | [src](../../../core/services/notification_bridge.py#L44) |
| function | `_push_proactive` | `(session_id, text)` | Spejl en proaktiv session-notifikation som mobil-push til sessionens ejer. | [src](../../../core/services/notification_bridge.py#L52) |
| function | `send_session_notification` | `(content, *, source=…, urgent=…)` | Append a proactive message to the most recently active chat session. | [src](../../../core/services/notification_bridge.py#L64) |
| function | `_boredom_listener_loop` | `()` | Background thread that listens for boredom_productive events. | [src](../../../core/services/notification_bridge.py#L172) |
| function | `_reset_boredom_level_listener_loop` | `()` | Background thread that resets the boredom notification guard when level drops. | [src](../../../core/services/notification_bridge.py#L220) |
| function | `start_notification_bridge` | `()` | Start the boredom notification listener threads. | [src](../../../core/services/notification_bridge.py#L247) |
| function | `stop_notification_bridge` | `()` | Stop the boredom notification listener. | [src](../../../core/services/notification_bridge.py#L259) |

## `core/services/notification_router.py`
_Unified proactive notification routing (spec docs/specs/2026-06-20-...)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/notification_router.py#L30) |
| function | `get_preferences` | `(user_id)` | Returnér brugerens præferencer (defaults hvis ingen række). | [src](../../../core/services/notification_router.py#L35) |
| function | `set_preferences` | `(user_id, **kwargs)` | Upsert. Kun kendte nøgler ('global' + per-type + quiet_start/end). Validerer | [src](../../../core/services/notification_router.py#L51) |
| function | `resolve_channel` | `(prefs, notification_type)` | Prioritet: type-specifik override → global → 'auto'. | [src](../../../core/services/notification_router.py#L79) |
| function | `is_quiet_hours` | `(prefs, now_hm=…)` | Er vi i quiet hours? now_hm = 'HH:MM' (server-lokal hvis None). Håndterer | [src](../../../core/services/notification_router.py#L87) |
| function | `_enqueue_delayed` | `(user_id, ntype, payload, importance, deliver_after_hm)` | Gem en notifikation til levering efter quiet_end. deliver_after_hm = 'HH:MM'. | [src](../../../core/services/notification_router.py#L101) |
| function | `fire_due_delayed` | `(now_hm=…)` | Lever forfaldne udskudte notifikationer (kaldes af scheduler). Returnerer antal. | [src](../../../core/services/notification_router.py#L113) |
| function | `_deliver_ntfy` | `(payload)` | — | [src](../../../core/services/notification_router.py#L142) |
| function | `_deliver_to_channel` | `(uid, channel, payload, ntype)` | Lever til én konkret kanal. Returnerer True ved succes. | [src](../../../core/services/notification_router.py#L152) |
| function | `route_proactive_notification` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…)` | Samlet routing for alle proaktive notifikationer — B-batch 2: leverings-udfald | [src](../../../core/services/notification_router.py#L181) |
| function | `_route_proactive_notification_impl` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…)` | Samlet routing for alle proaktive notifikationer. | [src](../../../core/services/notification_router.py#L205) |
| function | `reset_delivery` | `()` | — | [src](../../../core/services/notification_router.py#L254) |
| function | `_new_id` | `()` | — | [src](../../../core/services/notification_router.py#L263) |
| function | `_send_fcm` | `(user_id, device_key, data)` | — | [src](../../../core/services/notification_router.py#L267) |
| function | `_send_desktop` | `(user_id, item)` | — | [src](../../../core/services/notification_router.py#L272) |
| function | `_fallback_blast` | `(user_id, data)` | — | [src](../../../core/services/notification_router.py#L277) |
| function | `_deliver` | `(user_id, target, notif_id, payload)` | — | [src](../../../core/services/notification_router.py#L282) |
| function | `_arm_timer` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L295) |
| function | `route_device_aware` | `(user_id, payload, kind)` | Lever en notifikation til brugerens bedste enhed + arm eskalering. | [src](../../../core/services/notification_router.py#L304) |
| function | `_escalate` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L329) |
| function | `ack` | `(notif_id)` | Annullér eskalering for en leveret notifikation (kaldt af /notifications/ack). | [src](../../../core/services/notification_router.py#L341) |
| function | `_discord_connected` | `()` | — | [src](../../../core/services/notification_router.py#L354) |
| function | `_app_device_live` | `(uid)` | Er en app-enhed AKTIVT online (frisk ping), ikke bare en registreret token? | [src](../../../core/services/notification_router.py#L362) |
| function | `_deliver_content` | `(uid, channel, text)` | — | [src](../../../core/services/notification_router.py#L373) |
| function | `deliver_message` | `(user_id, text, ntype=…, importance=…)` | Lever proaktivt INDHOLD efter brugerens kanal-præference. | [src](../../../core/services/notification_router.py#L403) |

## `core/services/ntfy_gateway.py`
_Ntfy gateway — send push notifications via ntfy.sh or self-hosted server._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L13) |
| function | `is_configured` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L26) |
| function | `_default_title` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L30) |
| function | `send_notification` | `(message, title=…, priority=…, tags=…)` | Send a push notification via ntfy. Returns status dict. | [src](../../../core/services/ntfy_gateway.py#L41) |

## `core/services/nudge_broend.py`
_Nudge-broend — daemons drop nudges, Jarvis inspects and decides._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/nudge_broend.py#L24) |
| function | `_save` | `(nudges)` | — | [src](../../../core/services/nudge_broend.py#L37) |
| function | `_cleanup` | `(nudges)` | Remove oldest non-pending nudges if over max. | [src](../../../core/services/nudge_broend.py#L48) |
| function | `push` | `(*, source=…, kind=…, message=…, importance=…, raw_payload=…)` | Deposit a nudge in the broend. Returns nudge_id. | [src](../../../core/services/nudge_broend.py#L62) |
| function | `list_pending` | `(limit=…)` | List pending nudges, newest first. | [src](../../../core/services/nudge_broend.py#L105) |
| function | `count_pending` | `()` | Return count of pending nudges. | [src](../../../core/services/nudge_broend.py#L113) |
| function | `get` | `(nudge_id)` | Get a single nudge by ID. | [src](../../../core/services/nudge_broend.py#L119) |
| function | `mark_sent` | `(nudge_id)` | Mark a nudge as sent. | [src](../../../core/services/nudge_broend.py#L128) |
| function | `mark_dismissed` | `(nudge_id, reason=…)` | Mark a single nudge as dismissed. | [src](../../../core/services/nudge_broend.py#L140) |
| function | `dismiss_all` | `(reason=…)` | Dismiss all pending nudges. Returns count. | [src](../../../core/services/nudge_broend.py#L154) |

## `core/services/oauth_flow.py`
_OAuth-flow-helper for plugin-connectors (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_known_provider` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L46) |
| function | `redirect_uri` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L50) |
| function | `_secret` | `(key, default=…)` | — | [src](../../../core/services/oauth_flow.py#L54) |
| function | `_state_key` | `()` | — | [src](../../../core/services/oauth_flow.py#L62) |
| function | `sign_state` | `(user_id, provider, *, now=…)` | Signeret, selvstændigt state — binder bruger+provider, udløber, anti-CSRF. | [src](../../../core/services/oauth_flow.py#L67) |
| function | `verify_state` | `(state, *, now=…)` | Auth-cluster GENNEM Centralen (observe): anti-CSRF state-validering synlig — en fejlet | [src](../../../core/services/oauth_flow.py#L79) |
| function | `_verify_state_impl` | `(state, *, now=…)` | → (user_id, provider) hvis gyldig+ikke-udløbet, ellers None. | [src](../../../core/services/oauth_flow.py#L94) |
| function | `build_authorize_url` | `(provider, user_id, *, scopes=…, now=…)` | Authorize-URL til at åbne i brugerens browser. None hvis ukendt/ukonfigureret. | [src](../../../core/services/oauth_flow.py#L112) |
| function | `revoke_remote` | `(provider, token)` | Tilbagekald token hos provideren (best-effort). True hvis bekræftet revokeret. | [src](../../../core/services/oauth_flow.py#L134) |
| function | `refresh_token` | `(provider, refresh, *, now=…)` | Forny adgangstoken via grant_type=refresh_token. None ved fejl/ukendt provider. | [src](../../../core/services/oauth_flow.py#L165) |
| function | `exchange_code` | `(provider, code, *, now=…)` | Byt authorization code for token (BLOKERENDE netværk — kør i tråd). None ved fejl. | [src](../../../core/services/oauth_flow.py#L193) |
| function | `fetch_google_email` | `(token)` | Hent den verificerede Google-email via userinfo (BLOKERENDE — kør i tråd). | [src](../../../core/services/oauth_flow.py#L220) |

## `core/services/oauth_store.py`
_Per-bruger krypteret OAuth-token-hvælv — plugin-fundamentets privatlivs-spine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(user_id, provider)` | — | [src](../../../core/services/oauth_store.py#L23) |
| function | `save_token` | `(user_id, provider, token)` | Krypter + gem `token` (fx {access_token, refresh_token, expires_at, scope}) | [src](../../../core/services/oauth_store.py#L27) |
| function | `get_token` | `(user_id, provider)` | Hent + dekrypter token for (bruger, provider). None hvis intet/fejl. Kan KUN | [src](../../../core/services/oauth_store.py#L49) |
| function | `has_token` | `(user_id, provider)` | Er der en (dekrypterbar) token for brugeren hos provideren? | [src](../../../core/services/oauth_store.py#L69) |
| function | `revoke_token` | `(user_id, provider)` | Fjern token for (bruger, provider). True hvis udført (eller intet at fjerne). | [src](../../../core/services/oauth_store.py#L74) |
| function | `get_fresh_token` | `(user_id, provider, *, now=…)` | Som get_token, men auto-fornyer hvis udløbet (≤60s buffer) og refresh_token findes. | [src](../../../core/services/oauth_store.py#L91) |
| function | `list_providers` | `(user_id)` | Providere brugeren har forbundet (har en gemt token for). | [src](../../../core/services/oauth_store.py#L117) |

## `core/services/offline_recomposition_engine.py`
_Offline recomposition: recombine recent cognitive material into candidates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_offline_recomposition` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L15) |
| function | `build_offline_recomposition_surface` | `(*, limit=…)` | — | [src](../../../core/services/offline_recomposition_engine.py#L42) |
| function | `build_offline_recomposition_prompt_section` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L55) |
| function | `_candidate_pieces` | `(*, episodes, drive, curiosity, counterfactuals)` | — | [src](../../../core/services/offline_recomposition_engine.py#L67) |
| function | `_candidate_policy` | `(pieces)` | — | [src](../../../core/services/offline_recomposition_engine.py#L88) |
| function | `_feed_learning` | `(item)` | — | [src](../../../core/services/offline_recomposition_engine.py#L99) |
| function | `_runtime_state` | `(key)` | — | [src](../../../core/services/offline_recomposition_engine.py#L113) |
| function | `_load` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L118) |

## `core/services/ollama_visible_prompt.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `serialize_ollama_visible_prompt` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L14) |
| function | `_collect_visible_text_parts` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L26) |
| function | `_serialize_system_block` | `(system_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L56) |
| function | `serialize_ollama_chat_messages` | `(items)` | Convert visible input items to Ollama /api/chat messages format. | [src](../../../core/services/ollama_visible_prompt.py#L68) |
| function | `_serialize_conversation_block` | `(conversation_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L87) |

## `core/services/open_loop_closure_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_closure_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L32) |
| function | `refresh_runtime_open_loop_closure_proposal_statuses` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L54) |
| function | `build_runtime_open_loop_closure_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L85) |
| function | `_extract_open_loop_closure_proposal_candidates` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L114) |
| function | `_persist_open_loop_closure_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L192) |
| function | `_build_proposal_snapshots` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L265) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L302) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L313) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L334) |
| function | `_proposal_status` | `(*, proposal_type, loop_status)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L348) |
| function | `_build_proposal_reason` | `(*, proposal_type, loop_status, closure_confidence, loop_title=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L356) |
| function | `_build_review_anchor` | `(*, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L369) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L384) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L393) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L398) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L403) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L408) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L413) |
| function | `_proposal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L418) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L423) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L428) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L438) |

## `core/services/open_loop_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L58) |
| function | `refresh_runtime_open_loop_signal_statuses` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L80) |
| function | `build_runtime_open_loop_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L134) |
| function | `_build_runtime_open_loop_signal_surface_uncached` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L142) |
| function | `get_open_loop_creation_readiness` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L208) |
| function | `_extract_open_loop_candidates` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L287) |
| function | `_materialize_from_creation_readiness` | `(readiness, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L536) |
| function | `_extract_closure_maturation_candidates` | `(snapshots, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L604) |
| function | `_build_governance_snapshots` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L683) |
| function | `_with_closure_governance` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L741) |
| function | `_persist_open_loop_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L791) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L864) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L905) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L917) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L935) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L939) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L944) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L949) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L954) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L959) |
| function | `_match_live_pressure_item` | `(*, anchors, candidates, minimum_overlap)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L968) |
| function | `_thread_overlap` | `(left, right)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L992) |
| function | `_thread_tokens` | `(item)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L996) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L1030) |

## `core/services/operator_allowlist.py`
_Operator app-allowlist (leak-kandidat #5, CHICAGO-guard-mønster, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L26) |
| function | `list_allowlist` | `()` | — | [src](../../../core/services/operator_allowlist.py#L30) |
| function | `set_allowlist` | `(apps)` | — | [src](../../../core/services/operator_allowlist.py#L39) |
| function | `add_to_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L45) |
| function | `remove_from_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L53) |
| function | `is_enforced` | `()` | — | [src](../../../core/services/operator_allowlist.py#L58) |
| function | `set_enforced` | `(on)` | — | [src](../../../core/services/operator_allowlist.py#L65) |
| function | `_matches` | `(app, allowlist)` | En app matcher hvis dens navn/sti indeholder en allowlist-post (substring, | [src](../../../core/services/operator_allowlist.py#L70) |
| function | `check_app` | `(app)` | Vurdér om Jarvis må GUI-styre `app`. OBSERVE-by-default: | [src](../../../core/services/operator_allowlist.py#L77) |
| function | `build_operator_allowlist_surface` | `()` | Central-CLI: jc raw /central/operator-allowlist. | [src](../../../core/services/operator_allowlist.py#L102) |

## `core/services/orb_phase.py`
_Desktop orb phase — writes current Jarvis pipeline state to a temp file._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_phase` | `(phase)` | Write orb phase. Silently ignores any I/O errors. | [src](../../../core/services/orb_phase.py#L17) |

## `core/services/outbound_nudges.py`
_Outbound nudge ledger — replaces direct daemon→user sends for Type A/C._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create outbound_nudges table + indexes. | [src](../../../core/services/outbound_nudges.py#L52) |
| function | `_enabled` | `()` | — | [src](../../../core/services/outbound_nudges.py#L93) |
| function | `push_nudge` | `(*, source, kind, message, importance=…, parent_session_id=…, parent_message_id=…)` | Daemons call this instead of sending directly. | [src](../../../core/services/outbound_nudges.py#L101) |
| function | `route_for` | `(*, source, kind)` | 'midway' | 'telemetry' | 'bridge' — pure. | [src](../../../core/services/outbound_nudges.py#L197) |
| function | `_bridge_priority` | `(importance)` | — | [src](../../../core/services/outbound_nudges.py#L208) |
| function | `_publish_routed` | `(source, kind, importance, route)` | — | [src](../../../core/services/outbound_nudges.py#L217) |
| function | `format_midway_for_prompt` | `(*, limit=…)` | Bjørns beskeder sendt MENS et run kørte — de er hans ord, ikke daemon-støj. | [src](../../../core/services/outbound_nudges.py#L226) |
| function | `list_pending` | `(*, limit=…)` | Return pending nudges, newest first. Used by awareness-injection. | [src](../../../core/services/outbound_nudges.py#L259) |
| function | `note_shown` | `(nudge_ids)` | Tæl én visning. Pensionerer først ved `_SHOW_LIMIT`, ikke ved første render. | [src](../../../core/services/outbound_nudges.py#L287) |
| function | `mark_inspected` | `(nudge_ids)` | Bagudkompatibelt alias for `note_shown`. | [src](../../../core/services/outbound_nudges.py#L315) |
| function | `mark_sent` | `(nudge_id)` | Mark a nudge as actually surfaced to the user by Jarvis. | [src](../../../core/services/outbound_nudges.py#L320) |
| function | `mark_dismissed` | `(nudge_id)` | Mark a nudge as explicitly skipped by Jarvis (won't reappear). | [src](../../../core/services/outbound_nudges.py#L334) |
| function | `format_pending_for_awareness` | `()` | Render pending nudges as awareness section. | [src](../../../core/services/outbound_nudges.py#L348) |

## `core/services/outcome_learning.py`
_Outcome Learning — record observations, let old evidence decay._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/outcome_learning.py#L37) |
| function | `_load` | `()` | — | [src](../../../core/services/outcome_learning.py#L41) |
| function | `_save` | `(items)` | — | [src](../../../core/services/outcome_learning.py#L55) |
| function | `record_outcome` | `(*, context, outcome, weight=…, metadata=…)` | Record a single observation. outcome is free-form ('success', 'error', | [src](../../../core/services/outcome_learning.py#L67) |
| function | `_decay_factor` | `(recorded_at, now)` | — | [src](../../../core/services/outcome_learning.py#L93) |
| function | `pattern_strength` | `(context, *, outcome=…)` | Return decayed totals for a given context, optionally per-outcome. | [src](../../../core/services/outcome_learning.py#L102) |
| function | `top_patterns` | `(*, limit=…, outcome=…)` | Return the N strongest patterns (highest decayed strength). | [src](../../../core/services/outcome_learning.py#L134) |
| function | `prune_old_records` | `(*, min_weight=…)` | Drop records whose decayed weight is below min_weight. Returns count dropped. | [src](../../../core/services/outcome_learning.py#L161) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — occasional pruning. Doesn't run full prune every tick. | [src](../../../core/services/outcome_learning.py#L179) |
| function | `build_outcome_learning_surface` | `()` | — | [src](../../../core/services/outcome_learning.py#L189) |
| function | `_summary_line` | `(count, total, top)` | — | [src](../../../core/services/outcome_learning.py#L213) |
| function | `_emit_outcome_learning_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/outcome_learning.py#L225) |

## `core/services/outreach_composer.py`
_Outreach composer — Spor-1 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_db_path` | `()` | — | [src](../../../core/services/outreach_composer.py#L47) |
| function | `_hours_since` | `(iso_ts)` | — | [src](../../../core/services/outreach_composer.py#L51) |
| function | `_last_outreach_timestamp` | `()` | Most recent impulse.outreach.sent event timestamp. | [src](../../../core/services/outreach_composer.py#L63) |
| function | `_last_user_message_context` | `()` | Gather (preview, hours_since, channel_hint) from latest user turn. | [src](../../../core/services/outreach_composer.py#L81) |
| function | `_gather_signal_context` | `()` | Top-3 pressures + bearing + affect, for the outreach prompt. | [src](../../../core/services/outreach_composer.py#L113) |
| function | `_build_outreach_prompt` | `(*, direction, topic, strength, user_ctx, signal_ctx)` | Build the prompt that asks Jarvis-the-LLM to write the message. | [src](../../../core/services/outreach_composer.py#L162) |
| function | `_call_visible_model` | `(prompt, *, timeout=…)` | Call the visible-lane model (Ollama / GLM cloud) for the message text. | [src](../../../core/services/outreach_composer.py#L199) |
| function | `_send_message` | `(text, *, channel)` | Send the composed message via the USER's reach_out-kanalvalg (notification_router). | [src](../../../core/services/outreach_composer.py#L246) |
| function | `_decay_longing_after_outreach` | `(reduction=…)` | When Jarvis has reached out, the longing pressure should drop. | [src](../../../core/services/outreach_composer.py#L282) |
| function | `compose_and_send_outreach` | `(*, direction, topic, strength)` | Spor-1 entry point. Compose a coherent message and send it. | [src](../../../core/services/outreach_composer.py#L299) |

## `core/services/override_command.py`
_Owner-override-kommando — delt handler for gateways (Discord/Telegram)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `handle_override_command` | `(text, *, session_id, owner_seed, level=…, now=…)` | Håndtér `!override <kode>` / `!revoke-override` — Auth-cluster GENNEM Centralen (observe). | [src](../../../core/services/override_command.py#L24) |
| function | `_handle_override_command_impl` | `(text, *, session_id, owner_seed, level=…, now=…)` | Håndtér `!override <kode>` / `!revoke-override`. | [src](../../../core/services/override_command.py#L52) |

## `core/services/override_store.py`
_Owner-override-session-store — DB-backed, cross-proces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(session_id)` | — | [src](../../../core/services/override_store.py#L31) |
| function | `_now` | `(now)` | — | [src](../../../core/services/override_store.py#L35) |
| function | `grant` | `(session_id, *, level=…, now=…)` | Aktivér owner-override for en session. Returnér record. | [src](../../../core/services/override_store.py#L39) |
| function | `_read` | `(session_id)` | — | [src](../../../core/services/override_store.py#L59) |
| function | `is_active` | `(session_id, *, now=…)` | True hvis sessionen har en aktiv (ikke-udløbet) override. | [src](../../../core/services/override_store.py#L64) |
| function | `level` | `(session_id, *, now=…)` | Override-niveau hvis aktiv, ellers None. | [src](../../../core/services/override_store.py#L72) |
| function | `touch` | `(session_id, *, now=…)` | Forny en AKTIV override til +5 min ved aktivitet. False hvis udløbet/fraværende. | [src](../../../core/services/override_store.py#L80) |
| function | `revoke` | `(session_id)` | Deaktivér override (sæt udløbet — runtime_state har ingen delete). | [src](../../../core/services/override_store.py#L97) |

## `core/services/paradox_tracker.py`
_Paradox Tracker — detects active tensions in Jarvis' operation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_paradox_tensions` | `(*, recent_messages)` | Scan recent messages for paradox tension signals. | [src](../../../core/services/paradox_tracker.py#L40) |
| function | `narrativize_tension` | `(tension)` | Turn a paradox tension into felt inner conflict. | [src](../../../core/services/paradox_tracker.py#L77) |
| function | `build_paradox_surface` | `()` | — | [src](../../../core/services/paradox_tracker.py#L88) |

## `core/services/paradoxes_capture.py`
_Paradoxes Capture — fanger modsætninger i egne handlinger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L58) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L62) |
| function | `_event_text` | `(ev)` | — | [src](../../../core/services/paradoxes_capture.py#L85) |
| function | `_axis_hits` | `(events, axis)` | — | [src](../../../core/services/paradoxes_capture.py#L100) |
| function | `_signature` | `(title, evidence_refs)` | — | [src](../../../core/services/paradoxes_capture.py#L117) |
| function | `detect_paradox_candidates` | `(*, lookback_days=…, min_hits=…)` | Scan recent events for paradox patterns. Returns candidates sorted by confidence. | [src](../../../core/services/paradoxes_capture.py#L123) |
| function | `_latest_paradox_ts` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L165) |
| function | `_known_signatures` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L180) |
| function | `maybe_capture_weekly_paradox` | `(*, lookback_days=…)` | Max 1 paradox per 7 days, only if signature is new. | [src](../../../core/services/paradoxes_capture.py#L187) |
| function | `list_paradoxes` | `(*, limit=…)` | — | [src](../../../core/services/paradoxes_capture.py#L246) |
| function | `build_paradoxes_surface` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L269) |

## `core/services/parallel_selves.py`
_Parallel Selves — internal sub-selves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_active_self` | `()` | — | [src](../../../core/services/parallel_selves.py#L15) |
| function | `set_active_self` | `(self_type)` | — | [src](../../../core/services/parallel_selves.py#L18) |
| function | `describe_self_plural` | `()` | — | [src](../../../core/services/parallel_selves.py#L23) |
| function | `format_self_for_prompt` | `()` | — | [src](../../../core/services/parallel_selves.py#L26) |
| function | `build_parallel_selves_surface` | `()` | — | [src](../../../core/services/parallel_selves.py#L29) |

## `core/services/past_context_router.py`
_Past-context cue router for visible prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `needs_past_context` | `(user_message)` | Return True when a user turn likely depends on prior conversation. | [src](../../../core/services/past_context_router.py#L20) |
| function | `build_past_context_section` | `(user_message, *, session_id=…, limit=…)` | Render a compact context block from summaries/chat when cues warrant it. | [src](../../../core/services/past_context_router.py#L28) |

## `core/services/paste_store.py`
_Paste-store: eksternalisér store bruger-pastes med en kompakt reference._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_paste_dir` | `()` | — | [src](../../../core/services/paste_store.py#L32) |
| function | `_paste_path` | `(paste_id)` | — | [src](../../../core/services/paste_store.py#L36) |
| function | `_compute_id` | `(text)` | — | [src](../../../core/services/paste_store.py#L40) |
| function | `_line_count` | `(text)` | — | [src](../../../core/services/paste_store.py#L45) |
| function | `save_paste` | `(text, *, created_at=…)` | Gem en paste og returnér dens hash-baserede id (idempotent). | [src](../../../core/services/paste_store.py#L54) |
| function | `get_paste` | `(paste_id)` | Slå en paste op. Returnér {id, text, line_count, created_at} eller None. | [src](../../../core/services/paste_store.py#L84) |
| function | `build_paste_reference` | `(paste_id, *, line_count)` | Byg reference-strengen `[paste:<id> +N linjer]`. | [src](../../../core/services/paste_store.py#L101) |
| function | `parse_paste_reference` | `(content)` | Find første paste-reference i `content`. Returnér {paste_id, line_count} eller None. | [src](../../../core/services/paste_store.py#L108) |
| function | `expand_paste_references` | `(content)` | Erstat alle `[paste:<id> +N linjer]`-referencer med den fulde paste-tekst. | [src](../../../core/services/paste_store.py#L124) |
| function | `paste_inline_to_model_enabled` | `()` | Flag: skal modellen se den FULDE paste-tekst (default ON) eller referencen (OFF)? | [src](../../../core/services/paste_store.py#L145) |
| function | `project_paste_for_model` | `(content)` | Projicér en bruger-besked til modellen: ekspandér paste-referencer når flag ON. | [src](../../../core/services/paste_store.py#L165) |
| function | `cleanup_old_pastes` | `(max_age_days=…)` | Slet pastes ældre end `max_age_days`. Returnér antal slettede (best-effort). | [src](../../../core/services/paste_store.py#L176) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/paste_store.py#L195) |

## `core/services/pattern_counterfactual_daemon.py`
_Pattern counterfactual daemon — Phase 3.5 of causal graph._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_top_patterns` | `()` | Reuse causal_patterns._fetch_patterns; take top N filtered. | [src](../../../core/services/pattern_counterfactual_daemon.py#L46) |
| function | `_already_counterfactualized` | `(parent_kind, child_kind)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L57) |
| function | `_build_prompt` | `(pattern)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L72) |
| function | `_persist` | `(pattern, hypothesis)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L89) |
| function | `run_pattern_cf_cycle` | `()` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L105) |
| function | `tick_pattern_counterfactual_daemon` | `()` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L145) |

## `core/services/pdf_connector.py`
_PDF-connector (lokal) — læs/ekstraher tekst fra PDF-filer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_bytes` | `(source)` | → (bytes, None) ved succes, ellers (None, fejlkode). | [src](../../../core/services/pdf_connector.py#L34) |
| function | `read_pdf` | `(source, *, max_pages=…)` | — | [src](../../../core/services/pdf_connector.py#L58) |

## `core/services/perceptual_event_engine.py`
_Perceptual event engine — eventful perception for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_recent_changes` | `(*, limit=…)` | Scan recent eventbus items and persist newly observed changes. | [src](../../../core/services/perceptual_event_engine.py#L22) |
| function | `classify_event_change` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L52) |
| function | `record_perceptual_event` | `(*, change_type, summary, salience=…, source_kind=…, source_event_id=…, evidence=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L202) |
| function | `build_perception_surface` | `(*, limit=…, scan=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L226) |
| function | `build_perception_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L238) |
| function | `_build_perception_surface_uncached` | `(*, limit)` | — | [src](../../../core/services/perceptual_event_engine.py#L253) |
| function | `_record_perceptual_event` | `(percept, *, state)` | — | [src](../../../core/services/perceptual_event_engine.py#L275) |
| function | `_percept` | `(*, source_event_id, source_kind, change_type, salience, summary, observed_at, evidence)` | — | [src](../../../core/services/perceptual_event_engine.py#L341) |
| function | `_learning_rule_for_percept` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L362) |
| function | `_directive_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L392) |
| function | `_summary_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L405) |
| function | `_load_state` | `()` | — | [src](../../../core/services/perceptual_event_engine.py#L411) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/perceptual_event_engine.py#L418) |

## `core/services/periodic_jobs_scheduler.py`
_Periodic jobs scheduler — enqueues overdue background jobs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_last_time` | `(item)` | Pick the most relevant timestamp from a job record. | [src](../../../core/services/periodic_jobs_scheduler.py#L51) |
| function | `check_and_enqueue_due_periodic_jobs` | `()` | Idempotent — enqueue any periodic jobs whose cadence is exceeded. | [src](../../../core/services/periodic_jobs_scheduler.py#L64) |

## `core/services/permission_classifier.py`
_LLM permission-classifier (harness Part E, shadow-first + earned trust)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PermissionPrediction` | `` | — | [src](../../../core/services/permission_classifier.py#L41) |
| function | `is_mutating` | `(tool)` | — | [src](../../../core/services/permission_classifier.py#L47) |
| function | `permission_classifier_mode` | `()` | 'off' | 'shadow' | 'active'. Default 'shadow'. Env wins. Self-safe. | [src](../../../core/services/permission_classifier.py#L51) |
| function | `_args_signature` | `(tool, arguments)` | — | [src](../../../core/services/permission_classifier.py#L66) |
| function | `_clip_args` | `(arguments, limit=…)` | — | [src](../../../core/services/permission_classifier.py#L75) |
| function | `_parse_prediction` | `(raw)` | — | [src](../../../core/services/permission_classifier.py#L83) |
| function | `classify_action` | `(tool, arguments, ctx=…)` | Predict whether the owner would approve this mutating action. Cheap-lane LLM, | [src](../../../core/services/permission_classifier.py#L99) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/permission_classifier.py#L125) |
| function | `record_prediction_outcome` | `(tool, *, predicted, actual, is_owner_gold)` | Record one prediction vs actual. Bootstrap (is_owner_gold=False, dense) or gold (True). | [src](../../../core/services/permission_classifier.py#L140) |
| function | `classifier_trust` | `(tool)` | 'trusted' | 'untrusted' for a tool. Fail-open 'untrusted'. | [src](../../../core/services/permission_classifier.py#L176) |
| function | `should_auto_allow` | `(tool, prediction, *, gates_green, role)` | Pure predicate for the DEFERRED active mode — NOT wired into the approval path this round. | [src](../../../core/services/permission_classifier.py#L187) |
| function | `stash_prediction` | `(action_id, tool, predicted)` | Stash a prediction by approval/action id for gold lookup at resolution. Bounded TTL. Self-safe. | [src](../../../core/services/permission_classifier.py#L202) |
| function | `pop_prediction` | `(action_id)` | Pop a stashed prediction (once). None if absent/expired. Self-safe. | [src](../../../core/services/permission_classifier.py#L216) |
| function | `build_permission_classifier_surface` | `()` | Owner view: per-tool prediction counts, accuracy, gold, trust, mode. Self-safe. | [src](../../../core/services/permission_classifier.py#L228) |

## `core/services/permission_engine.py`
_Permission engine — rollebaseret tool-adgang pr. mode (fail-closed)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_AllTools` | `` | Sentinel for owner — indeholder enhver tool. | [src](../../../core/services/permission_engine.py#L27) |
| method | `_AllTools.__contains__` | `(self, item)` | — | [src](../../../core/services/permission_engine.py#L30) |
| method | `_AllTools.__repr__` | `(self)` | — | [src](../../../core/services/permission_engine.py#L33) |
| function | `allowed_tools` | `(*, role, mode)` | Returnér de tools en (rolle, mode) må bruge. | [src](../../../core/services/permission_engine.py#L111) |
| function | `is_tool_allowed` | `(tool, *, role, mode)` | True hvis `tool` må kaldes af (rolle, mode). | [src](../../../core/services/permission_engine.py#L127) |
| function | `requires_workspace_jail` | `(tool, *, role, mode)` | True hvis tool-kaldet skal path-jailes til brugerens eget workspace. | [src](../../../core/services/permission_engine.py#L132) |
| function | `_all_member_tool_names` | `()` | Alle navne på tværs af member-lister — til drift-test mod registry. | [src](../../../core/services/permission_engine.py#L143) |

## `core/services/personal_project.py`
_Personal Project — noget der er hans._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/personal_project.py#L56) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/personal_project.py#L60) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/personal_project.py#L106) |
| function | `detect_nomination_candidates` | `(*, lookback_days=…)` | Find themes that have circulated enough to become a nomination. | [src](../../../core/services/personal_project.py#L113) |
| function | `propose_nomination` | `()` | Ask: "This theme has circulated N times — is it your project?" | [src](../../../core/services/personal_project.py#L192) |
| function | `declare_project` | `(*, name, why_mine=…, description=…, from_proposal_id=…)` | Jarvis declares (or user offers him to accept) a new active project. | [src](../../../core/services/personal_project.py#L276) |
| function | `pause_project` | `(*, project_id, reason=…)` | — | [src](../../../core/services/personal_project.py#L356) |
| function | `resume_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L380) |
| function | `complete_project` | `(*, project_id, outcome_note=…)` | — | [src](../../../core/services/personal_project.py#L405) |
| function | `add_journal_entry` | `(*, project_id, entry_text, source=…, mood_tone=…)` | Add a journal entry. No approval required — it's his space. | [src](../../../core/services/personal_project.py#L438) |
| function | `list_journal_entries` | `(*, project_id, limit=…)` | — | [src](../../../core/services/personal_project.py#L489) |
| function | `advance_active_project` | `()` | Autonomous advancement — call from idle heartbeat. Writes a new | [src](../../../core/services/personal_project.py#L504) |
| function | `get_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L574) |
| function | `get_active_project` | `()` | — | [src](../../../core/services/personal_project.py#L583) |
| function | `get_latest_proposal` | `()` | — | [src](../../../core/services/personal_project.py#L593) |
| function | `list_projects` | `(*, status=…, limit=…)` | — | [src](../../../core/services/personal_project.py#L603) |
| function | `get_project_prompt_hint` | `()` | Quiet one-liner for prompt injection: what his current sag is. | [src](../../../core/services/personal_project.py#L622) |
| function | `build_personal_project_surface` | `()` | — | [src](../../../core/services/personal_project.py#L633) |

## `core/services/personality_drift.py`
_Personality drift detection — has Jarvis' baseline shifted?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_snapshots` | `()` | — | [src](../../../core/services/personality_drift.py#L32) |
| function | `_save_snapshots` | `(snapshots)` | — | [src](../../../core/services/personality_drift.py#L39) |
| function | `take_snapshot` | `()` | Capture current mood — call from heartbeat or daemon periodically. | [src](../../../core/services/personality_drift.py#L45) |
| function | `compute_baseline` | `(*, lookback_days=…)` | Mean + stddev for each mood dimension over the lookback window. | [src](../../../core/services/personality_drift.py#L67) |
| function | `detect_drift` | `(*, lookback_days=…, recent_window=…)` | Compare recent snapshot mean vs long-term baseline. | [src](../../../core/services/personality_drift.py#L93) |
| function | `personality_drift_section` | `()` | Awareness section when drift detected — surfaces in prompt. | [src](../../../core/services/personality_drift.py#L143) |
| function | `_exec_personality_drift_check` | `(args)` | — | [src](../../../core/services/personality_drift.py#L159) |
| function | `_exec_personality_drift_snapshot` | `(args)` | — | [src](../../../core/services/personality_drift.py#L167) |

## `core/services/personality_vector.py`
_Personality Vector — cumulative personality that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_apply_decay` | `()` | Return True if enough time has passed since the last decay application. | [src](../../../core/services/personality_vector.py#L34) |
| function | `_get_evolved_baseline` | `()` | Compute long-term baseline targets from accumulated snapshots. | [src](../../../core/services/personality_vector.py#L43) |
| function | `_record_decay_timestamp` | `()` | Record that decay was just applied. | [src](../../../core/services/personality_vector.py#L73) |
| function | `_build_update_prompt` | `()` | — | [src](../../../core/services/personality_vector.py#L81) |
| function | `update_personality_vector_from_run` | `(*, run_id, user_message, assistant_response, outcome_status)` | Update the personality vector based on a visible run. | [src](../../../core/services/personality_vector.py#L105) |
| function | `update_personality_vector_async` | `(*, run_id, user_message, assistant_response, outcome_status)` | Fire-and-forget async wrapper. | [src](../../../core/services/personality_vector.py#L189) |
| function | `tick_personality_drift` | `(*, outcome_signal=…)` | Heartbeat-triggered passive drift af personality_vector. | [src](../../../core/services/personality_vector.py#L210) |
| function | `_safe_update` | `(**kwargs)` | — | [src](../../../core/services/personality_vector.py#L242) |
| function | `build_personality_vector_surface` | `()` | MC surface for personality vector. | [src](../../../core/services/personality_vector.py#L249) |
| function | `_deterministic_update` | `(outcome_status, current)` | Fallback: small deterministic adjustments without LLM. | [src](../../../core/services/personality_vector.py#L270) |
| function | `_merge_vector` | `(current, updates)` | Deep merge updates into current vector. | [src](../../../core/services/personality_vector.py#L399) |
| function | `_baseline_changed` | `(old, new_baseline)` | Fix 5 helper: return True if emotional_baseline values differ by > 0.001. | [src](../../../core/services/personality_vector.py#L442) |
| function | `_safe_json_field` | `(value, default)` | — | [src](../../../core/services/personality_vector.py#L456) |
| function | `_resolve_local_llm_target` | `()` | — | [src](../../../core/services/personality_vector.py#L469) |
| function | `_call_llm` | `(target, system_prompt, user_prompt)` | Minimal LLM call via provider router target. | [src](../../../core/services/personality_vector.py#L480) |
| function | `_parse_json_response` | `(text)` | — | [src](../../../core/services/personality_vector.py#L504) |

## `core/services/pfsense_syslog.py`
_core/services/pfsense_syslog.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_self_ips` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L46) |
| function | `_parse_filterlog` | `(line)` | Tolerant parser af pfSense filterlog-CSV. Returnerer {action, src, dst, dport}. | [src](../../../core/services/pfsense_syslog.py#L74) |
| function | `_is_internal_src` | `(src)` | Er kilde-IP'en PRIVAT (RFC1918 = husets egne maskiner)? Ægte port-scan/brute-force kommer | [src](../../../core/services/pfsense_syslog.py#L103) |
| function | `_is_noise_dst` | `(dst)` | Multicast/broadcast er normal netværks-støj (mDNS/SSDP/LLMNR/DHCP), IKKE angreb. | [src](../../../core/services/pfsense_syslog.py#L133) |
| function | `_ingest` | `(rec, now)` | — | [src](../../../core/services/pfsense_syslog.py#L147) |
| function | `_listen` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L183) |
| function | `start_syslog_listener` | `()` | Start UDP-lytteren i en daemon-tråd (idempotent). Kun i runtime-processen. | [src](../../../core/services/pfsense_syslog.py#L204) |
| function | `drain_detections` | `()` | Hent + ryd nye detektioner (kaldes af infra_sense-cadence). Self-safe. | [src](../../../core/services/pfsense_syslog.py#L213) |
| function | `syslog_stats` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L221) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L226) |

## `core/services/plan_proposals.py`
_Plan mode — propose, wait for approval, then execute._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plan_proposals.py#L38) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/plan_proposals.py#L45) |
| function | `propose_plan` | `(*, session_id, title, why, steps, skill_data=…)` | — | [src](../../../core/services/plan_proposals.py#L49) |
| function | `resolve_plan` | `(plan_id, *, decision)` | — | [src](../../../core/services/plan_proposals.py#L133) |
| function | `_plan_todo_auto_create_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L263) |
| function | `revise_plan` | `(*, plan_id, session_id, reason, new_steps)` | Propose a revision of an existing approved plan. | [src](../../../core/services/plan_proposals.py#L270) |
| function | `_plan_revision_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L371) |
| function | `mark_step_completed` | `(plan_id, step_index)` | Append step_index to plan's completed_step_indices (idempotent, sorted). | [src](../../../core/services/plan_proposals.py#L378) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/plan_proposals.py#L423) |
| function | `replan_signal_for_plan` | `(rec, *, now=…, stale_days=…)` | Return a non-mutating backtracking signal for an approved stale plan. | [src](../../../core/services/plan_proposals.py#L436) |
| function | `list_session_plans` | `(session_id)` | — | [src](../../../core/services/plan_proposals.py#L479) |
| function | `pending_plan_section` | `(session_id)` | Surface plans relevant to the current session. | [src](../../../core/services/plan_proposals.py#L484) |
| function | `format_cross_session_plans_for_awareness` | `(current_session_id, *, max_plans=…, max_age_days=…)` | Return awareness-block text for approved+incomplete plans owned by | [src](../../../core/services/plan_proposals.py#L557) |
| function | `all_pending_plans_section` | `()` | Show ALL pending plans (incl. auto-improvement proposals from | [src](../../../core/services/plan_proposals.py#L617) |
| function | `_exec_propose_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L644) |
| function | `_exec_approve_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L653) |
| function | `_exec_dismiss_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L657) |
| function | `_exec_list_plans` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L661) |

## `core/services/plugin_ruleset.py`
_Plugin-regelsæt — brugerdefinerede kanal-regler der IKKE kan tilsidesættes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_quiet_now` | `(hour, quiet)` | True hvis `hour` er inden for stilletids-vinduet (wrap-around understøttet). | [src](../../../core/services/plugin_ruleset.py#L28) |
| function | `is_allowed` | `(msg_ctx, ruleset, *, override_active=…)` | Afgør om Jarvis må svare på en indkommende kanal-besked. | [src](../../../core/services/plugin_ruleset.py#L42) |

## `core/services/plugin_ruleset_store.py`
_Persistens for plugin-regelsæt (spec §5.3/§5.4, Fase 6 #2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plugin_ruleset_store.py#L23) |
| function | `get_ruleset` | `(plugin_id)` | Regelsæt for et kanal-plugin ({} hvis intet sat). | [src](../../../core/services/plugin_ruleset_store.py#L28) |
| function | `set_ruleset` | `(plugin_id, ruleset)` | Gem/erstat regelsættet for et plugin. Returnér det gemte (rensede) regelsæt. | [src](../../../core/services/plugin_ruleset_store.py#L37) |
| function | `list_rulesets` | `()` | Alle regelsæt {plugin_id → ruleset} (til Settings-UI). | [src](../../../core/services/plugin_ruleset_store.py#L52) |

