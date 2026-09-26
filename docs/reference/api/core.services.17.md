# `core.services.17` — reference

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
| function | `cheap_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L36) |
| function | `execute_cheap_lane` | `(*, message, task_kind=…)` | Run a message through the cheap lane. | [src](../../../core/services/non_visible_lane_execution.py#L56) |
| function | `_prompt_fra_messages` | `(messages)` | Fald tilbage til samtalen når kalderen kun gav `messages`. | [src](../../../core/services/non_visible_lane_execution.py#L75) |
| function | `_observeret_navn` | `(svar, bedt_om_provider)` | Hvem svarede — med udbyder foran hvis det ikke var den vi spurgte. | [src](../../../core/services/non_visible_lane_execution.py#L102) |
| function | `execute_with_role_or_fallback` | `(*, message=…, provider=…, model=…, requires_tools=…, messages=…, tools=…, lane=…)` | Run the message on the role's preferred provider/model first, fall | [src](../../../core/services/non_visible_lane_execution.py#L112) |
| function | `local_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L363) |
| function | `coding_lane_execution_truth` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L384) |
| function | `execute_coding_lane` | `(*, message)` | — | [src](../../../core/services/non_visible_lane_execution.py#L415) |
| function | `_lane_status` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L419) |
| function | `_coding_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L433) |
| function | `_local_lane_readiness` | `(target)` | — | [src](../../../core/services/non_visible_lane_execution.py#L641) |
| function | `_coding_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L702) |
| function | `_local_auth_path` | `(*, provider, auth_mode)` | — | [src](../../../core/services/non_visible_lane_execution.py#L718) |
| function | `_github_copilot_auth_state` | `(*, oauth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L726) |
| function | `_github_copilot_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L750) |
| function | `_github_copilot_auth_status` | `(*, auth_state, exchange_readiness)` | — | [src](../../../core/services/non_visible_lane_execution.py#L774) |
| function | `_github_copilot_provider_status` | `(*, auth_state)` | — | [src](../../../core/services/non_visible_lane_execution.py#L806) |
| function | `_coding_lane_probe` | `(*, provider, model, auth_profile, credentials_ready, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L830) |
| function | `_probe_codex_cli_target` | `(*, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L872) |
| function | `_probe_ollama_local_target` | `(*, model, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L912) |
| function | `_probe_openai_coding_target` | `(*, provider, model, auth_profile, base_url)` | — | [src](../../../core/services/non_visible_lane_execution.py#L953) |
| function | `_execute_lane` | `(*, message, truth)` | — | [src](../../../core/services/non_visible_lane_execution.py#L996) |
| function | `_execute_codex_cli` | `(*, message, model)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1096) |
| function | `_resolve_codex_cli_executable` | `()` | — | [src](../../../core/services/non_visible_lane_execution.py#L1139) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1154) |
| function | `_post_openai_responses` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1173) |
| function | `_post_openrouter_chat_completion` | `(*, base_url, payload, api_key)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1188) |
| function | `_extract_output_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1205) |
| function | `_extract_openrouter_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1225) |
| function | `_load_github_copilot_token` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1237) |
| function | `_github_copilot_request_headers` | `(session_token, *, accept=…)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1254) |
| function | `_post_github_copilot_chat_completion` | `(*, payload, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1269) |
| function | `_extract_github_copilot_text` | `(data)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1287) |
| function | `fetch_github_copilot_models` | `(*, profile)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1299) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/non_visible_lane_execution.py#L1326) |

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
| function | `_push_proactive` | `(session_id, text)` | Spejl en proaktiv session-notifikation som mobil-push til sessionens ejer. | [src](../../../core/services/notification_bridge.py#L74) |
| function | `delivery_succeeded` | `(result)` | True når notifikationen er ANTAGET til levering. | [src](../../../core/services/notification_bridge.py#L94) |
| function | `send_session_notification` | `(content, *, source=…, urgent=…)` | Append a proactive message to the most recently active chat session. | [src](../../../core/services/notification_bridge.py#L107) |
| function | `_boredom_listener_loop` | `()` | Background thread that listens for boredom_productive events. | [src](../../../core/services/notification_bridge.py#L215) |
| function | `_reset_boredom_level_listener_loop` | `()` | Background thread that resets the boredom notification guard when level drops. | [src](../../../core/services/notification_bridge.py#L263) |
| function | `start_notification_bridge` | `()` | Start the boredom notification listener threads. | [src](../../../core/services/notification_bridge.py#L290) |
| function | `stop_notification_bridge` | `()` | Stop the boredom notification listener. | [src](../../../core/services/notification_bridge.py#L302) |

## `core/services/notification_router.py`
_Unified proactive notification routing (spec docs/specs/2026-06-20-...)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/notification_router.py#L41) |
| function | `get_preferences` | `(user_id)` | Returnér brugerens præferencer (defaults hvis ingen række). | [src](../../../core/services/notification_router.py#L46) |
| function | `set_preferences` | `(user_id, **kwargs)` | Upsert. Kun kendte nøgler ('global' + per-type + quiet_start/end). Validerer | [src](../../../core/services/notification_router.py#L62) |
| function | `resolve_channel` | `(prefs, notification_type)` | Prioritet: type-specifik override → global → 'auto'. | [src](../../../core/services/notification_router.py#L90) |
| function | `is_quiet_hours` | `(prefs, now_hm=…)` | Er vi i quiet hours? now_hm = 'HH:MM' (server-lokal hvis None). Håndterer | [src](../../../core/services/notification_router.py#L98) |
| function | `_enqueue_delayed` | `(user_id, ntype, payload, importance, deliver_after_hm)` | Gem en notifikation til levering efter quiet_end. deliver_after_hm = 'HH:MM'. | [src](../../../core/services/notification_router.py#L112) |
| function | `_alder_timer` | `(created_at, nu)` | Timer siden rækken blev lagt i kø. None hvis tidspunktet er ulæseligt — | [src](../../../core/services/notification_router.py#L139) |
| function | `fire_due_delayed` | `(now_hm=…, *, max_per_run=…)` | Lever forfaldne udskudte notifikationer (kaldes af heartbeat-poll'en). | [src](../../../core/services/notification_router.py#L152) |
| function | `_deliver_ntfy` | `(payload)` | — | [src](../../../core/services/notification_router.py#L217) |
| function | `_deliver_to_channel` | `(uid, channel, payload, ntype)` | Lever til én konkret kanal. Returnerer True ved succes. | [src](../../../core/services/notification_router.py#L227) |
| function | `_feed_titel_og_tekst` | `(notification_type, payload)` | Payloads er ikke ens — nogle sender title+body, andre title+preview+body, | [src](../../../core/services/notification_router.py#L284) |
| function | `_foed_feed_raekke` | `(user_id, notification_type, payload)` | Læg én åben række i notifikations-feeden for en router-drevet slags. | [src](../../../core/services/notification_router.py#L298) |
| function | `route_proactive_notification` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…, feed=…)` | Samlet routing for alle proaktive notifikationer — B-batch 2: leverings-udfald | [src](../../../core/services/notification_router.py#L314) |
| function | `_route_proactive_notification_impl` | `(user_id, notification_type, payload, importance=…, *, _skip_quiet=…)` | Samlet routing for alle proaktive notifikationer. | [src](../../../core/services/notification_router.py#L372) |
| function | `reset_delivery` | `()` | — | [src](../../../core/services/notification_router.py#L431) |
| function | `_new_id` | `()` | — | [src](../../../core/services/notification_router.py#L440) |
| function | `_send_fcm` | `(user_id, device_key, data)` | — | [src](../../../core/services/notification_router.py#L444) |
| function | `_send_desktop` | `(user_id, item)` | — | [src](../../../core/services/notification_router.py#L449) |
| function | `_fallback_blast` | `(user_id, data)` | — | [src](../../../core/services/notification_router.py#L454) |
| function | `_deliver` | `(user_id, target, notif_id, payload)` | — | [src](../../../core/services/notification_router.py#L459) |
| function | `_arm_timer` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L472) |
| function | `_ordn_efter_flade` | `(ranked, surface)` | Saet enhederne paa DEN flade turen blev skrevet fra forrest. | [src](../../../core/services/notification_router.py#L486) |
| function | `route_device_aware` | `(user_id, payload, kind)` | Lever en notifikation til brugerens bedste enhed + arm eskalering. | [src](../../../core/services/notification_router.py#L511) |
| function | `_escalate` | `(notif_id)` | — | [src](../../../core/services/notification_router.py#L537) |
| function | `ack` | `(notif_id)` | Annullér eskalering for en leveret notifikation (kaldt af /notifications/ack). | [src](../../../core/services/notification_router.py#L549) |
| function | `_discord_connected` | `()` | — | [src](../../../core/services/notification_router.py#L562) |
| function | `_app_device_live` | `(uid)` | Er en app-enhed AKTIVT online (frisk ping), ikke bare en registreret token? | [src](../../../core/services/notification_router.py#L570) |
| function | `_deliver_content` | `(uid, channel, text)` | — | [src](../../../core/services/notification_router.py#L587) |
| function | `deliver_message` | `(user_id, text, ntype=…, importance=…)` | Lever proaktivt INDHOLD efter brugerens kanal-præference. | [src](../../../core/services/notification_router.py#L622) |

## `core/services/notifikationer.py`
_Notifikations-feedens lager (spec docs/superpowers/specs/2026-09-21-...)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_udsend` | `(slags_haendelse, nid, user_id, slags)` | Live-vejen til klokken. Fejler den, skal FEEDEN stadig virke — men den | [src](../../../core/services/notifikationer.py#L26) |
| function | `_nu` | `()` | — | [src](../../../core/services/notifikationer.py#L43) |
| function | `opret` | `(*, user_id, slags, kilde, titel, tekst=…, ref=…, session_id=…)` | Laeg en notifikation. Returnerer id. | [src](../../../core/services/notifikationer.py#L47) |
| function | `aabne` | `(user_id, *, er_owner)` | Aabne raekker for denne bruger. RAA — se hydreringen for den rigtige feed. | [src](../../../core/services/notifikationer.py#L97) |
| function | `afsluttede` | `(user_id, *, dage=…)` | KLAREDE raekker for denne bruger — de sidste `dage`. RAA. | [src](../../../core/services/notifikationer.py#L120) |
| function | `luk` | `(notif_id, udfald)` | Klaret — vaek fra fladen. Raekken bliver liggende til `ryd_gamle`. | [src](../../../core/services/notifikationer.py#L147) |
| function | `genaabn` | `(slags, ref)` | Genaabn en LUKKET raekke for (slags, ref). Returnerer True hvis en | [src](../../../core/services/notifikationer.py#L165) |
| function | `ryd_gamle` | `(dage=…)` | Fjern KLAREDE raekker aeldre end `dage`. Returnerer antal fjernede. | [src](../../../core/services/notifikationer.py#L193) |

## `core/services/notifikationer_hydrering.py`
_Feedens laesning — den slaar op hos EJEREN, ikke i sin egen kopi._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hydrer_approval` | `(raekke)` | None = ejeren er faerdig, luk raekken. Kaster = ejeren er utilgaengelig. | [src](../../../core/services/notifikationer_hydrering.py#L42) |
| function | `_hydrer_run` | `(raekke)` | None = koerslen er ikke laengere i den tilstand der skabte raekken. | [src](../../../core/services/notifikationer_hydrering.py#L59) |
| function | `_hydrer` | `(raekke)` | (felter, foraeldet). felter=None betyder «luk raekken». | [src](../../../core/services/notifikationer_hydrering.py#L96) |
| function | `feed` | `(user_id, *, er_owner, aktiv_session=…)` | Aabne notifikationer, hydreret hos deres ejere. | [src](../../../core/services/notifikationer_hydrering.py#L115) |
| function | `tidligere` | `(user_id, *, er_owner, dage=…)` | KLAREDE notifikationer — ren laesning, ingen hydrering. | [src](../../../core/services/notifikationer_hydrering.py#L160) |

## `core/services/notifikations_emittere.py`
_Hvor notifikationer foedes (spec 2026-09-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_id` | `()` | Ejeren. Systemraekker hoerer til ham — de handler om maskinen. | [src](../../../core/services/notifikations_emittere.py#L21) |
| function | `_maaske_push` | `(user_id, slags, titel, tekst, *, session_id=…)` | — | [src](../../../core/services/notifikations_emittere.py#L43) |
| function | `_foed` | `(*, user_id, slags, kilde, titel, tekst=…, ref=…, session_id=…)` | — | [src](../../../core/services/notifikations_emittere.py#L74) |
| function | `paa_godkendelse` | `(approval_id, *, user_id, session_id, vaerktoej)` | — | [src](../../../core/services/notifikations_emittere.py#L82) |
| function | `paa_koersel_fejlet` | `(run_id, *, user_id, session_id, titel)` | — | [src](../../../core/services/notifikations_emittere.py#L92) |
| function | `paa_koersel_faerdig` | `(run_id, *, user_id, session_id, titel)` | — | [src](../../../core/services/notifikations_emittere.py#L98) |
| function | `fra_jarvis` | `(user_id, slags, titel, tekst=…)` | Det Jarvis selv sender. Har ingen ejer — raekken ER sandheden. | [src](../../../core/services/notifikations_emittere.py#L104) |
| function | `system` | `(slags, titel, tekst=…)` | — | [src](../../../core/services/notifikations_emittere.py#L109) |
| function | `afstem_godkendelser` | `(user_id)` | Laeg raekker for ALLE ventende godkendelser der mangler. Returnerer | [src](../../../core/services/notifikations_emittere.py#L116) |

## `core/services/notifikations_opstart.py`
_Det notifikations-feeden skal have gjort ved hver opstart (spec 2026-09-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `koer_ved_opstart` | `()` | — | [src](../../../core/services/notifikations_opstart.py#L13) |

## `core/services/notifikations_valg.py`
_Push-valg per slags (spec 2026-09-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kanal_for` | `(user_id, slags)` | — | [src](../../../core/services/notifikations_valg.py#L100) |
| function | `saet` | `(user_id, slags, kanal)` | — | [src](../../../core/services/notifikations_valg.py#L117) |
| function | `alle` | `(user_id)` | Alle slags med brugerens valg lagt oven paa standarden. | [src](../../../core/services/notifikations_valg.py#L128) |
| function | `migrer_kolonner` | `()` | Baer de gamle kolonner over som raekker. Idempotent. | [src](../../../core/services/notifikations_valg.py#L139) |

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

## `core/services/ollama_model_names.py`
_Opløs et bart ollama-modelnavn til det tag ollama faktisk serverer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_base_url` | `()` | — | [src](../../../core/services/ollama_model_names.py#L41) |
| function | `served_tags` | `()` | De modelnavne ollama serverer lige nu. Cachet 120 s; tom maengde ved fejl. | [src](../../../core/services/ollama_model_names.py#L53) |
| function | `resolve_model_name` | `(model)` | `glm-5.2` → `glm-5.2:cloud` naar den variant findes. Ellers uaendret. | [src](../../../core/services/ollama_model_names.py#L75) |

## `core/services/ollama_visible_prompt.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `serialize_ollama_visible_prompt` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L14) |
| function | `_collect_visible_text_parts` | `(items)` | Del elementerne i en ledende system-blok og selve samtalen. | [src](../../../core/services/ollama_visible_prompt.py#L26) |
| function | `_serialize_system_block` | `(system_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L63) |
| function | `serialize_ollama_chat_messages` | `(items)` | Convert visible input items to Ollama /api/chat messages format. | [src](../../../core/services/ollama_visible_prompt.py#L75) |
| function | `_serialize_conversation_block` | `(conversation_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L132) |

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

## `core/services/operator_channel.py`
_Operator-kanalen — owner-gated bro fra containerens bash til Bjørns maskine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/operator_channel.py#L41) |
| function | `_save` | `(state)` | — | [src](../../../core/services/operator_channel.py#L50) |
| function | `_aktiv` | `(post)` | — | [src](../../../core/services/operator_channel.py#L58) |
| function | `status` | `(session_id)` | Læse-kun. Ingen owner-gate — at spørge er harmløst. | [src](../../../core/services/operator_channel.py#L65) |
| function | `is_open` | `(session_id)` | — | [src](../../../core/services/operator_channel.py#L76) |
| function | `open_channel` | `(session_id, *, is_owner)` | — | [src](../../../core/services/operator_channel.py#L80) |
| function | `close_channel` | `(session_id, *, is_owner)` | — | [src](../../../core/services/operator_channel.py#L94) |
| function | `current_session_id` | `()` | Samme opslags-raekkefoelge som staged_edits_tools — ét moenster, ikke to. | [src](../../../core/services/operator_channel.py#L105) |
| function | `current_is_owner` | `()` | Owner-gaten. Fail-CLOSED: kan rollen ikke afgoeres, er svaret nej. | [src](../../../core/services/operator_channel.py#L120) |
| function | `_absolutte_stier` | `(command)` | — | [src](../../../core/services/operator_channel.py#L136) |
| function | `looks_like_workstation_path` | `(command, cwd=…)` | — | [src](../../../core/services/operator_channel.py#L149) |
| function | `maybe_reroute_bash` | `(command, cwd, *, is_owner, session_id)` | Kør kommandoen på Bjørns maskine hvis kanalen er åben. Ellers None. | [src](../../../core/services/operator_channel.py#L156) |
| function | `closed_channel_hint` | `(command, cwd, *, is_owner, session_id)` | Én linje til modellen når et kald tydeligvis sigtede mod hans maskine. | [src](../../../core/services/operator_channel.py#L182) |

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

## `core/services/outcome_projector.py`
_`OutcomeProjector` — ét terminalt udfald pr. run, uden at opfinde sandhed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SurfaceEvent` | `` | En besked til brugeren med sin EGEN herkomst. | [src](../../../core/services/outcome_projector.py#L60) |
| class | `RunOutcome` | `` | — | [src](../../../core/services/outcome_projector.py#L75) |
| class | `DoubleTerminal` | `` | Et run fik to terminale udfald. Så kan ingen rapportere på det. | [src](../../../core/services/outcome_projector.py#L85) |
| function | `project` | `(settlements, *, terminal_event_id=…, recovered=…, stop_reason=…)` | Ét udfald ud af de afregnede forsøg. Ren funktion. | [src](../../../core/services/outcome_projector.py#L89) |
| function | `_fejltekst` | `(s, stop_reason)` | Sig hvad der skete. Ingen undskyldninger, ingen opdigtet forklaring. | [src](../../../core/services/outcome_projector.py#L155) |
| class | `OutcomeLedger` | `` | Nøjagtig ét terminalt udfald pr. run, nøglet på den terminale hændelse. | [src](../../../core/services/outcome_projector.py#L168) |
| method | `OutcomeLedger.__init__` | `(self)` | — | [src](../../../core/services/outcome_projector.py#L176) |
| method | `OutcomeLedger.record` | `(self, run_id, outcome)` | — | [src](../../../core/services/outcome_projector.py#L179) |
| method | `OutcomeLedger.outcome` | `(self, run_id)` | — | [src](../../../core/services/outcome_projector.py#L195) |
| method | `OutcomeLedger.is_terminal` | `(self, run_id)` | — | [src](../../../core/services/outcome_projector.py#L198) |

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
| function | `_decay_longing_after_outreach` | `(reduction=…)` | When Jarvis has reached out, the longing pressure should drop. | [src](../../../core/services/outreach_composer.py#L285) |
| function | `compose_and_send_outreach` | `(*, direction, topic, strength)` | Spor-1 entry point. Compose a coherent message and send it. | [src](../../../core/services/outreach_composer.py#L302) |

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

## `core/services/paid_lane_guard.py`
_Vagt: kun Bjørns egen lane må ramme den betalte DeepSeek-API (2026-09-05)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_host` | `(url)` | — | [src](../../../core/services/paid_lane_guard.py#L55) |
| function | `is_paid` | `(base_url)` | — | [src](../../../core/services/paid_lane_guard.py#L62) |
| function | `audit_paid_lanes` | `()` | Hvilke lanes peger på en betalt vært uden at måtte? | [src](../../../core/services/paid_lane_guard.py#L66) |
| function | `_tilhoerer_ham` | `(run_id)` | Er kaldet en del af en af Bjørns egne ture? | [src](../../../core/services/paid_lane_guard.py#L103) |
| function | `audit_paid_spend` | `(timer=…)` | Hvilke BETALTE kald hørte ikke til en af hans ture? | [src](../../../core/services/paid_lane_guard.py#L114) |
| function | `check_paid_spend` | `(timer=…)` | Kør hovedbogs-revisionen: log + Central-nerve ved brud. | [src](../../../core/services/paid_lane_guard.py#L152) |
| function | `audit_heartbeat_provider` | `()` | Kører hjerteslaget på en betalt udbyder? None = nej. | [src](../../../core/services/paid_lane_guard.py#L179) |
| function | `check_paid_lanes` | `()` | Kør vagten: log + Central-nerve ved brud. Retter aldrig noget selv. | [src](../../../core/services/paid_lane_guard.py#L207) |
| function | `build_paid_lane_guard_surface` | `()` | Begge domme: hvad routeren LOVER, og hvad hovedbogen REGISTREREDE. | [src](../../../core/services/paid_lane_guard.py#L233) |

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
| function | `_er_rutine_gentagelse` | `(percept, set_foer, now)` | Er det her et værktøj der lige har kørt — altså ikke en ændring? | [src](../../../core/services/perceptual_event_engine.py#L37) |
| function | `observe_recent_changes` | `(*, limit=…)` | Scan recent eventbus items and persist newly observed changes. | [src](../../../core/services/perceptual_event_engine.py#L95) |
| function | `classify_event_change` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L146) |
| function | `record_perceptual_event` | `(*, change_type, summary, salience=…, source_kind=…, source_event_id=…, evidence=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L296) |
| function | `build_perception_surface` | `(*, limit=…, scan=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L320) |
| function | `build_perception_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L332) |
| function | `_build_perception_surface_uncached` | `(*, limit)` | — | [src](../../../core/services/perceptual_event_engine.py#L347) |
| function | `_record_perceptual_event` | `(percept, *, state)` | — | [src](../../../core/services/perceptual_event_engine.py#L369) |
| function | `_percept` | `(*, source_event_id, source_kind, change_type, salience, summary, observed_at, evidence)` | — | [src](../../../core/services/perceptual_event_engine.py#L435) |
| function | `_learning_rule_for_percept` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L456) |
| function | `_directive_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L486) |
| function | `_summary_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L499) |
| function | `_load_state` | `()` | — | [src](../../../core/services/perceptual_event_engine.py#L505) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/perceptual_event_engine.py#L512) |

## `core/services/periodic_jobs_scheduler.py`
_Periodic jobs scheduler — enqueues overdue background jobs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_last_time` | `(item)` | Pick the most relevant timestamp from a job record. | [src](../../../core/services/periodic_jobs_scheduler.py#L51) |
| function | `check_and_enqueue_due_periodic_jobs` | `()` | Idempotent — enqueue any periodic jobs whose cadence is exceeded. | [src](../../../core/services/periodic_jobs_scheduler.py#L64) |

