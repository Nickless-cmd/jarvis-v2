# `core.services.07` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_trinity.py`
_Trinity 💜 — trust-bridge (Matrix-ensemble, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/central_trinity.py#L27) |
| function | `_is_enforced` | `()` | Default OFF (shadow) — modsat gate-default. Læs råt fra shared_cache, unset = shadow. | [src](../../../core/services/central_trinity.py#L41) |
| function | `_mature_hypotheses` | `()` | Modne hypoteser (Seraphs kriterium: grounded_fraction ≥ 0.6 + abs-gulv). Self-safe → []. | [src](../../../core/services/central_trinity.py#L55) |
| function | `_ledger` | `()` | — | [src](../../../core/services/central_trinity.py#L80) |
| function | `assess_affirmations` | `()` | Konvergens-vurdering pr. moden hypotese → affirmationer med progress mod nøgle. Read-only. | [src](../../../core/services/central_trinity.py#L91) |
| function | `_bump` | `(pattern_key, title, now)` | Registrér én affirmation → returnér ny streak. Self-safe → 0. | [src](../../../core/services/central_trinity.py#L111) |
| function | `_merovingian_blocks` | `(pattern_key)` | Værn ④: Merovingian kan udfordre en Trinity-optjent nøgle. Self-safe → False (fail-open). | [src](../../../core/services/central_trinity.py#L134) |
| function | `_earn_pending_key` | `(pattern_key, title, streak)` | Fase 2: opret en PENDING trust-nøgle i central_keys (samme tabel Keymaker bruger, | [src](../../../core/services/central_trinity.py#L143) |
| function | `record_trinity` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn: assess → opdatér streaks → (KUN hvis enforced) optjen pending nøgle. | [src](../../../core/services/central_trinity.py#L181) |
| function | `build_trinity_surface` | `()` | Read-only surface til /central/trinity + jc + ensemble-label. | [src](../../../core/services/central_trinity.py#L211) |

## `core/services/central_twins.py`
_The Twins — gentagelses-detektor på tværs af tid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_twins.py#L32) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_twins.py#L36) |
| function | `_incidents` | `(limit=…)` | — | [src](../../../core/services/central_twins.py#L46) |
| function | `_gate_counts` | `()` | — | [src](../../../core/services/central_twins.py#L54) |
| function | `_dissents` | `(limit=…)` | — | [src](../../../core/services/central_twins.py#L62) |
| function | `_incident_patterns` | `(incidents, *, now)` | Gentagne incident-mønstre indenfor vinduet: (nerve, kind) og (nerve, tidspunkt-på-dagen). Self-safe. | [src](../../../core/services/central_twins.py#L72) |
| function | `_gate_patterns` | `(counts, *, now)` | Gentagne yellow/red på samme gate (nerve) indenfor vinduet. Self-safe. | [src](../../../core/services/central_twins.py#L98) |
| function | `_dissent_patterns` | `(dissents, *, now)` | Gentagne uhørte indsigelser på samme gate indenfor vinduet. Self-safe. | [src](../../../core/services/central_twins.py#L124) |
| function | `_describe` | `(pat)` | Én linje der siger 'det her har jeg set før'. Deterministisk, ingen model. Self-safe. | [src](../../../core/services/central_twins.py#L140) |
| function | `detect_repeats` | `()` | Scan alle tre kilder for mønstre der gentager sig 3+ gange på 7 dage. READ-ONLY. | [src](../../../core/services/central_twins.py#L162) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_twins.py#L183) |
| function | `build_twins_surface` | `()` | Detekterede gentagende mønstre + følt linje. READ-ONLY. Self-safe. | [src](../../../core/services/central_twins.py#L200) |
| function | `record_twins` | `(*, trigger=…, last_visible_at=…)` | Cadence (240 min): scan for gentagelser → twins://-signaler (observe/surface only). Self-safe. | [src](../../../core/services/central_twins.py#L219) |

## `core/services/central_valence.py`
_core/services/central_valence.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_valence.py#L18) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_valence.py#L27) |
| function | `_read_valence_trajectory` | `()` | — | [src](../../../core/services/central_valence.py#L35) |
| function | `_read_somatic` | `()` | — | [src](../../../core/services/central_valence.py#L49) |
| function | `_read_stance` | `()` | — | [src](../../../core/services/central_valence.py#L60) |
| function | `_tone_label` | `(score)` | Ét felt-ord for tilstanden ud fra den FRISKE (present-moment) score. Bevidst få, tydelige toner. | [src](../../../core/services/central_valence.py#L72) |
| function | `integrate_valence` | `()` | Integrér de fire organer til ÉN følt tilstand {tone, score, intensitet}. Valens-trajektorien er | [src](../../../core/services/central_valence.py#L92) |
| function | `get_valence_state` | `()` | Centralens durable følte tilstand (senest integrerede). Self-safe. | [src](../../../core/services/central_valence.py#L120) |
| function | `run_valence_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: integrér følelses-organerne → gem durabelt + egress-fri observe (kun skalarer/tone-label, | [src](../../../core/services/central_valence.py#L126) |
| function | `register_valence_producer` | `()` | Registrér følt-tilstands-integrationen som cadence-producer (~hvert 15 min). Egress-frit. | [src](../../../core/services/central_valence.py#L142) |
| function | `build_valence_surface` | `()` | Mission Control — read-only: Centralens ene følte tilstand. | [src](../../../core/services/central_valence.py#L154) |

## `core/services/central_watch.py`
_core/services/central_watch.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_watch.py#L48) |
| function | `_notify_cooldown_active` | `(key, now)` | True hvis samme flag allerede har ringet inden for afkølingsvinduet. | [src](../../../core/services/central_watch.py#L68) |
| function | `_notify_cooldown_mark` | `(key, now)` | — | [src](../../../core/services/central_watch.py#L91) |
| function | `_notify_owner` | `(title, message, importance)` | — | [src](../../../core/services/central_watch.py#L115) |
| function | `_raise_flag` | `(cluster, nerve, *, severity, message, importance=…, make_incident=…)` | Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe. | [src](../../../core/services/central_watch.py#L138) |
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L172) |
| function | `_clear_flag` | `(cluster, nerve)` | Luk en ÅBEN flag-incident når TILSTANDEN er væk. Returnerer antal lukkede. | [src](../../../core/services/central_watch.py#L177) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L199) |
| function | `_event_is_recent` | `(r, *, max_age_min=…)` | True hvis event-record er nyere end max_age_min. Fail-open ved ukendt/uparsbar | [src](../../../core/services/central_watch.py#L428) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen NYLIGT. Cross-proces. | [src](../../../core/services/central_watch.py#L443) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L457) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, exhausted) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L465) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra NYLIGE tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L488) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L506) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L515) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L529) |

## `core/services/central_white_rabbit.py`
_Follow the White Rabbit — serendipitets-motoren._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dark_doors` | `()` | Mørke/stille nerver ingen rører — de uåbnede døre. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L25) |
| function | `follow_rabbit` | `(*, seed=…)` | Vælg én uåbnet dør at undre sig over — ren ikke-målrettet udforskning. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L36) |
| function | `_observe` | `(door, total)` | — | [src](../../../core/services/central_white_rabbit.py#L49) |
| function | `build_white_rabbit_surface` | `()` | — | [src](../../../core/services/central_white_rabbit.py#L58) |
| function | `record_white_rabbit` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_white_rabbit.py#L62) |

## `core/services/central_xproc.py`
_Cross-proces trace-tee for Den Intelligente Central._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `process_role` | `()` | 'api' (visible-lane, JARVIS_ENABLE_RUNTIME_SERVICES=0) eller 'runtime' (daemons). | [src](../../../core/services/central_xproc.py#L37) |
| function | `maybe_publish` | `()` | Throttled publish af denne proces' feed + sundhed. Kaldt fra trace-record (hot path) | [src](../../../core/services/central_xproc.py#L43) |
| function | `_publish_now` | `()` | — | [src](../../../core/services/central_xproc.py#L70) |
| function | `foreign_feeds` | `(own_role)` | Records fra ALLE andre processer end ens egen (ens egen har vi in-memory, friskere). | [src](../../../core/services/central_xproc.py#L120) |
| function | `merged_timeseries` | `()` | Alle processers per-nerve tidsserie merget: nerve-key → {proces: {latest,count,meta,recent}}. | [src](../../../core/services/central_xproc.py#L139) |
| function | `all_health` | `()` | Per-proces sundhed for hver kendt proces der har publiceret (ikke udløbet). Self-safe. | [src](../../../core/services/central_xproc.py#L161) |

## `core/services/channel_inbound.py`
_Kanal-plugin inbound-routing (spec §5.2/§5.3, Fase 5 Lag 1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_builtin_channel_plugins` | `()` | Idempotent registrering af indbyggede kanal-plugins (kaldes fra plugins-route). | [src](../../../core/services/channel_inbound.py#L33) |
| function | `resolve_inbound_mode` | `(requested_mode=…, *, author_role=…, override_active=…)` | Afgør den effektive mode for en indkommende kanal-besked (§18.9). | [src](../../../core/services/channel_inbound.py#L45) |
| function | `route_inbound` | `(**kwargs)` | Auth-cluster GENNEM Den Intelligente Central (observe). A2+A4: plugin-hardblock + | [src](../../../core/services/channel_inbound.py#L63) |
| function | `_route_inbound_impl` | `(*, plugin_id, channel, author_role=…, author_user_id=…, text=…, hour=…, now=…, mode=…, override_active=…)` | Afgør om en indkommende kanal-besked må nå Jarvis (plugin_ruleset hardblock), | [src](../../../core/services/channel_inbound.py#L84) |

## `core/services/chat_crypto.py`
_Kryptering af chat-historik i databasen (spec §16.2, plan-task 3.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kryptering_slaaet_til` | `()` | Nødbremse. Tændt med mindre nogen eksplicit slukker. | [src](../../../core/services/chat_crypto.py#L65) |
| function | `medlem_for_raekke` | `(*, workspace_name=…, user_id=…)` | `discord_id` for den registrerede NON-owner rækken tilhører, ellers None. | [src](../../../core/services/chat_crypto.py#L71) |
| function | `medlem_for_session` | `(session_id, conn=…)` | Samme svar som `medlem_for_raekke`, men udledt af sessionen. | [src](../../../core/services/chat_crypto.py#L101) |
| function | `er_krypteret` | `(raa)` | — | [src](../../../core/services/chat_crypto.py#L150) |
| function | `krypter` | `(tekst, medlem_id)` | ``enc:v1:<base64>``. Allerede krypteret tekst røres ikke. | [src](../../../core/services/chat_crypto.py#L154) |
| function | `dekrypter` | `(raa, medlem_id)` | Modsat `krypter`. Klartekst ind → klartekst ud, uændret. | [src](../../../core/services/chat_crypto.py#L164) |
| function | `medlem_for_skrivning` | `(raekke, *, session_id=…, conn=…)` | Hvem rækken tilhører — rækkens egne felter først, ellers SESSIONEN. | [src](../../../core/services/chat_crypto.py#L184) |
| function | `krypter_raekke` | `(raekke, *, session_id=…, conn=…)` | Krypter de tekstbærende felter i en chat-række, hvis den er en members. | [src](../../../core/services/chat_crypto.py#L216) |
| function | `dekrypter_sessionsraekker` | `(raekker, session_id, conn=…)` | Dekryptér en sessions egne rækker. Kun til sessions-læserne. | [src](../../../core/services/chat_crypto.py#L237) |
| function | `dekrypter_raekke` | `(raekke)` | Modsat `krypter_raekke`. Bruges KUN af sessions-læserne. | [src](../../../core/services/chat_crypto.py#L275) |

## `core/services/chat_sessions.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_tool_result_for_reconstruct` | `(result_id)` | Serve-on-read loader: slå et gammelt tool-resultat op fra tool_result_store. | [src](../../../core/services/chat_sessions.py#L24) |
| function | `_content_json_for_row` | `(role, content, raw_json, *, hent_resultat=…)` | Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort, | [src](../../../core/services/chat_sessions.py#L42) |
| function | `create_chat_session` | `(*, title=…, workspace_kind=…, workspace_root=…, kind=…)` | — | [src](../../../core/services/chat_sessions.py#L66) |
| function | `get_or_create_named_session` | `(session_id, title)` | Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny). | [src](../../../core/services/chat_sessions.py#L113) |
| function | `most_recent_session_id` | `()` | Lightweight: session_id of the most recently updated session. | [src](../../../core/services/chat_sessions.py#L140) |
| function | `_sikr_flag_kolonner` | `(conn)` | Doven migration: `pinned` og `archived` paa chat_sessions. | [src](../../../core/services/chat_sessions.py#L157) |
| function | `set_session_flags` | `(session_id, *, pinned=…, archived=…)` | Saet fastgjort/arkiveret paa én samtale. Kun de felter der gives. | [src](../../../core/services/chat_sessions.py#L203) |
| function | `list_chat_sessions` | `(*, user_id=…, inkluder_arkiverede=…, kind=…)` | List chat sessions, optionally filtered to one user. | [src](../../../core/services/chat_sessions.py#L248) |
| function | `_make_snippet` | `(content, query, width=…)` | Byg et kort uddrag centreret om første match (case-insensitive). | [src](../../../core/services/chat_sessions.py#L358) |
| function | `search_chat_sessions` | `(query, *, user_id=…, limit=…)` | Søg sessioner på titel ELLER besked-indhold (user/assistant). | [src](../../../core/services/chat_sessions.py#L373) |
| function | `session_version` | `(session_id)` | Billig nøgle der ændrer sig præcis når sessionens indhold gør. | [src](../../../core/services/chat_sessions.py#L455) |
| function | `session_kind` | `(session_id)` | Samtalens ART ('chat'/'code') — ét felt, ingen historik. | [src](../../../core/services/chat_sessions.py#L493) |
| function | `_client_message_content` | `(role, content)` | Hvad klienten må se. Intern bogholderi bliver til én kort, ærlig linje. | [src](../../../core/services/chat_sessions.py#L530) |
| function | `get_message_reasoning` | `(message_id)` | Den FULDE tankestrøm bag ét svar — dovent, kun når nogen beder om den. | [src](../../../core/services/chat_sessions.py#L537) |
| function | `_er_json` | `(tekst)` | — | [src](../../../core/services/chat_sessions.py#L573) |
| function | `_afkort_tool_resultater` | `(blokke)` | Lange værktøjs-resultater bærer kun deres begyndelse ud til klienten. | [src](../../../core/services/chat_sessions.py#L581) |
| function | `get_message_tool_result` | `(message_id, tool_use_id)` | Ét fuldt værktøjs-resultat — dovent, kun når nogen folder linjen ud. | [src](../../../core/services/chat_sessions.py#L618) |
| function | `get_chat_session` | `(session_id)` | HELE samtalens historik i ét synkront kald. UDFASET for nye kaldere. | [src](../../../core/services/chat_sessions.py#L643) |
| function | `set_session_workspace` | `(session_id, *, kind, root)` | Bind (eller skift) en sessions Code-mode workspace. | [src](../../../core/services/chat_sessions.py#L766) |
| function | `append_chat_message` | `(*, session_id, role, content, created_at=…, tool_name=…, tool_arguments=…, full_content=…, user_id=…, workspace_name=…, reasoning_content=…, content_json=…)` | — | [src](../../../core/services/chat_sessions.py#L781) |
| function | `_er_pladsholder` | `(titel)` | Er titlen en pladsholder — uanset hvordan den er stavet? | [src](../../../core/services/chat_sessions.py#L1057) |
| function | `_navngiv_fra_foerste_besked` | `(session_id, content)` | Doeb sessionen efter det foerste brugeren skrev i den. | [src](../../../core/services/chat_sessions.py#L1076) |
| function | `_recent_duplicate_user_message` | `(session_id, content, now_ts)` | Returnér den seneste besked-række HVIS den er en identisk brugerbesked inden | [src](../../../core/services/chat_sessions.py#L1113) |
| function | `_infer_tool_name_from_content` | `(content)` | — | [src](../../../core/services/chat_sessions.py#L1148) |
| function | `recent_user_message_texts` | `(*, limit=…)` | Brugerens seneste beskeder paa TVAERS af sessioner — kun teksten. | [src](../../../core/services/chat_sessions.py#L1155) |
| function | `recent_chat_session_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L1185) |
| function | `chat_session_messages_since_last_compact` | `(session_id, *, max_total=…)` | Hent ALT efter seneste compact_marker (eller hele session hvis ingen). | [src](../../../core/services/chat_sessions.py#L1223) |
| function | `recent_chat_session_messages_by_user_turns` | `(session_id, *, user_turns=…, max_total=…)` | Hent de seneste N *user-turns* og alt der hører til dem. | [src](../../../core/services/chat_sessions.py#L1292) |
| function | `_ensure_compact_marker_git_sha_column` | `()` | Add git_sha column to chat_messages if it doesn't exist (idempotent migration). | [src](../../../core/services/chat_sessions.py#L1375) |
| function | `store_compact_marker` | `(session_id, summary_text, git_sha=…)` | Store a compact marker for the session. Returns the marker message_id. | [src](../../../core/services/chat_sessions.py#L1387) |
| function | `get_compact_marker_with_sha` | `(session_id)` | Return (summary, git_sha) of the most recent compact marker, or (None, None). | [src](../../../core/services/chat_sessions.py#L1464) |
| function | `get_compact_marker` | `(session_id)` | Return the most recent compact marker summary for the session, or None. | [src](../../../core/services/chat_sessions.py#L1488) |
| function | `recent_chat_tool_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L1506) |
| function | `rename_chat_session` | `(session_id, *, title)` | — | [src](../../../core/services/chat_sessions.py#L1538) |
| function | `delete_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L1552) |
| function | `_session_summary` | `(row)` | — | [src](../../../core/services/chat_sessions.py#L1574) |
| function | `_normalize_title` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1596) |
| function | `_preview_text` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1603) |
| function | `_time_label` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1610) |
| function | `parse_channel_from_session_title` | `(title)` | Parse channel type and detail from a session title. | [src](../../../core/services/chat_sessions.py#L1618) |
| function | `get_session_owner` | `(session_id)` | Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel. | [src](../../../core/services/chat_sessions.py#L1648) |
| function | `latest_user_content_json` | `(session_id)` | `content_json` for sessionens SENESTE brugerbesked. | [src](../../../core/services/chat_sessions.py#L1664) |

## `core/services/cheap_lane_admission.py`
_Cross-process pause, drain, and active-call leases for Cheap Lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AdmissionRejected` | `` | — | [src](../../../core/services/cheap_lane_admission.py#L15) |
| method | `AdmissionRejected.__init__` | `(self, *, scope, target, mode)` | — | [src](../../../core/services/cheap_lane_admission.py#L16) |
| class | `AdmissionRevisionConflict` | `` | — | [src](../../../core/services/cheap_lane_admission.py#L23) |
| class | `AdmissionLease` | `` | — | [src](../../../core/services/cheap_lane_admission.py#L28) |
| function | `_prune_expired` | `(conn, now)` | — | [src](../../../core/services/cheap_lane_admission.py#L36) |
| function | `_active_count` | `(conn, *, scope, target)` | — | [src](../../../core/services/cheap_lane_admission.py#L44) |
| function | `set_admission_mode` | `(*, scope, target, mode, expected_revision=…)` | — | [src](../../../core/services/cheap_lane_admission.py#L60) |
| function | `admission_snapshot` | `(*, scope, target)` | — | [src](../../../core/services/cheap_lane_admission.py#L102) |
| function | `acquire_admission` | `(*, correlation_id, provider, slot_id, lease_seconds=…)` | — | [src](../../../core/services/cheap_lane_admission.py#L123) |
| function | `release_admission` | `(lease_id)` | — | [src](../../../core/services/cheap_lane_admission.py#L155) |

## `core/services/cheap_lane_balancer.py`
_Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BalancerSlot` | `` | Immutable identity of a (provider, model) lane. | [src](../../../core/services/cheap_lane_balancer.py#L21) |
| method | `BalancerSlot.slot_id` | `(self)` | — | [src](../../../core/services/cheap_lane_balancer.py#L33) |
| class | `SlotState` | `` | Per-slot mutable runtime state. Persisted to JSON (timestamps deque is in-memory only). | [src](../../../core/services/cheap_lane_balancer.py#L38) |
| function | `_provider_router_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L79) |
| function | `_router_enabled_models` | `()` | Return list of dicts {provider, model, enabled, auth_profile, lane} | [src](../../../core/services/cheap_lane_balancer.py#L86) |
| function | `_credentials_ready` | `(provider, auth_profile)` | Check if provider has working credentials. Wraps existing helper. | [src](../../../core/services/cheap_lane_balancer.py#L116) |
| function | `_provider_metadata` | `(provider)` | Lookup provider's static config (rpm_limit, daily_limit, base_url, etc.). | [src](../../../core/services/cheap_lane_balancer.py#L125) |
| function | `_state_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L142) |
| function | `_state_to_dict` | `(state)` | Serialize SlotState to JSON-safe dict (skips deque). | [src](../../../core/services/cheap_lane_balancer.py#L149) |
| function | `_state_from_dict` | `(d)` | — | [src](../../../core/services/cheap_lane_balancer.py#L171) |
| function | `_load_state` | `()` | Load all slot-states from disk. Returns empty dict on missing/corrupt file. | [src](../../../core/services/cheap_lane_balancer.py#L192) |
| function | `_save_state` | `(states)` | Atomic write to state file. | [src](../../../core/services/cheap_lane_balancer.py#L210) |
| function | `_save_state_debounced` | `(states)` | — | [src](../../../core/services/cheap_lane_balancer.py#L229) |
| function | `_ensure_state` | `(states, slot_id)` | Get-or-create slot state. Mutates `states` in place. | [src](../../../core/services/cheap_lane_balancer.py#L239) |
| function | `_today_iso` | `(now=…)` | Returns UTC date string. Override hookable via module-level _datetime_for_today. | [src](../../../core/services/cheap_lane_balancer.py#L258) |
| function | `_count_recent_calls` | `(timestamps, now, window_seconds)` | Count timestamps falling within [now - window, now]. | [src](../../../core/services/cheap_lane_balancer.py#L264) |
| function | `_daily_used_from_db` | `(provider, auth_profile=…)` | Task 4 / Fund 5: daglig brug fra SQLite cheap_provider_invocations (samme kilde | [src](../../../core/services/cheap_lane_balancer.py#L270) |
| function | `_daily_headroom_for` | `(slot, state=…)` | Daily headroom fra SQLite frem for balancerens private JSON daily_use_count. | [src](../../../core/services/cheap_lane_balancer.py#L287) |
| function | `_observe_central` | `(nerve, payload)` | Task 5: skriv til Centralens system/<nerve>. Self-safe — observabilitet må | [src](../../../core/services/cheap_lane_balancer.py#L303) |
| function | `_emit_balancer_event` | `(name, payload)` | Ét sted: emit til eventbus (bagudkompatibelt) + observe fejl-events til Central. | [src](../../../core/services/cheap_lane_balancer.py#L313) |
| function | `_compute_weight` | `(slot, state, now)` | Returns non-negative weight; 0 means slot is ineligible right now. | [src](../../../core/services/cheap_lane_balancer.py#L326) |
| function | `_slot_status` | `(slot, state, now)` | Single derived status string for a slot, most-severe-wins. | [src](../../../core/services/cheap_lane_balancer.py#L372) |
| function | `_flag_adaptive_quota` | `()` | Learn real daily ceilings from genuine daily-quota 429s. Default OFF. | [src](../../../core/services/cheap_lane_balancer.py#L433) |
| function | `_maybe_daily_reset` | `(state, now)` | Reset per-day adaptive-quota learning at the UTC day boundary. | [src](../../../core/services/cheap_lane_balancer.py#L446) |
| function | `_register_failure` | `(state, error_kind, *, retry_after_s=…, now, error_message=…, observed_used=…, config_daily=…)` | Update state after a failed call. | [src](../../../core/services/cheap_lane_balancer.py#L461) |
| function | `_register_success` | `(state, now)` | Update state after a successful call. | [src](../../../core/services/cheap_lane_balancer.py#L548) |
| function | `_is_dns_or_connection_error` | `(error_kind, exc=…)` | True if error indicates network-level (provider-wide) issue, not slot-specific. | [src](../../../core/services/cheap_lane_balancer.py#L570) |
| function | `_register_provider_wide_failure` | `(states, pool, provider, now, *, reason, auth_profile=…, cooldown_s=…)` | Apply cooldown to a provider's affected auth profile, or all when unspecified. | [src](../../../core/services/cheap_lane_balancer.py#L588) |
| function | `_select_slot` | `(states, pool, now)` | Pick a slot via weighted-random; returns None if all blocked. | [src](../../../core/services/cheap_lane_balancer.py#L634) |
| function | `_central_route_shadow` | `()` | Kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_lane_balancer.py#L682) |
| function | `_central_route_live` | `()` | Brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_lane_balancer.py#L691) |
| function | `_flag_multiprofile` | `()` | Byg én slot pr. (provider, klar auth-profil) i stedet for kun entry-profilen. | [src](../../../core/services/cheap_lane_balancer.py#L700) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_lane_balancer.py#L712) |
| function | `_central_route_slot` | `(eligible_pool, tried_slot_ids)` | Spørg central_route om lane='cheap'-pick og map til en EGNET (untried) slot i | [src](../../../core/services/cheap_lane_balancer.py#L729) |
| function | `_maybe_central_route_slot` | `(weighted_slot, eligible_pool, tried_slot_ids)` | Hook før slot bruges: shadow-compare (OFF → no-op) + live-apply. Aldrig-tør | [src](../../../core/services/cheap_lane_balancer.py#L750) |
| function | `_call_provider_chat` | `(*, provider, model, auth_profile, base_url, message)` | Wrapper around cheap_provider_runtime._execute_provider_chat. | [src](../../../core/services/cheap_lane_balancer.py#L771) |
| function | `_append_recent_call` | `(slot_id, daemon, status, latency_ms, *, error=…)` | — | [src](../../../core/services/cheap_lane_balancer.py#L796) |
| function | `recent_calls` | `()` | Returns ring-buffer of last 75 calls (newest first). | [src](../../../core/services/cheap_lane_balancer.py#L814) |
| function | `call_balanced` | `(*, prompt, daemon_name=…, max_retries=…)` | Pick a slot via weighted-random; execute; on failure retry next slot. | [src](../../../core/services/cheap_lane_balancer.py#L819) |
| function | `build_slot_pool` | `()` | Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS. | [src](../../../core/services/cheap_lane_balancer.py#L1062) |
| function | `reset_slot` | `(slot_id)` | Clear breaker, cooldown, and consecutive-failure streak for a slot. | [src](../../../core/services/cheap_lane_balancer.py#L1202) |
| function | `disable_slot` | `(slot_id)` | Force a slot's weight to 0 until enable_slot is called. | [src](../../../core/services/cheap_lane_balancer.py#L1214) |
| function | `enable_slot` | `(slot_id)` | Re-enable a manually-disabled slot. | [src](../../../core/services/cheap_lane_balancer.py#L1223) |
| function | `refresh_pool` | `()` | Re-build the slot pool from provider_router.json. Returns current size. | [src](../../../core/services/cheap_lane_balancer.py#L1232) |
| function | `_is_enabled` | `()` | Check RuntimeSettings.daemon_balancer_enabled. Default True. | [src](../../../core/services/cheap_lane_balancer.py#L1243) |
| function | `balancer_snapshot` | `()` | Return full state surface for Mission Control telemetry. | [src](../../../core/services/cheap_lane_balancer.py#L1252) |
| function | `orphan_slot_ids` | `(slot_ids, *, is_account_profile)` | Slot-ider hvis auth-profil ikke er en ægte konto. Ren udvælgelse. | [src](../../../core/services/cheap_lane_balancer.py#L1393) |
| function | `prune_orphan_slots` | `()` | Fjern state-poster for profiler balanceren aldrig vælger. Self-safe. | [src](../../../core/services/cheap_lane_balancer.py#L1413) |

## `core/services/cheap_lane_control.py`
_Audited operator commands for Cheap Lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ControlError` | `` | — | [src](../../../core/services/cheap_lane_control.py#L17) |
| class | `ControlAuditError` | `` | — | [src](../../../core/services/cheap_lane_control.py#L21) |
| class | `ControlRevisionConflict` | `` | — | [src](../../../core/services/cheap_lane_control.py#L25) |
| class | `ControlScopeError` | `` | — | [src](../../../core/services/cheap_lane_control.py#L29) |
| class | `ControlTargetNotFound` | `` | — | [src](../../../core/services/cheap_lane_control.py#L33) |
| class | `CheapLaneCommand` | `` | — | [src](../../../core/services/cheap_lane_control.py#L38) |
| function | `_revision` | `(value)` | — | [src](../../../core/services/cheap_lane_control.py#L46) |
| function | `_split_model` | `(target)` | — | [src](../../../core/services/cheap_lane_control.py#L51) |
| function | `_registry_state` | `(action, target)` | — | [src](../../../core/services/cheap_lane_control.py#L58) |
| function | `_authoritative_result` | `(command, mutation)` | — | [src](../../../core/services/cheap_lane_control.py#L77) |
| function | `_before` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L90) |
| function | `_require_reason` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L110) |
| function | `_require_cheap_scope` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L120) |
| function | `_admission_mutation` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L148) |
| function | `_registry_mutation` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L166) |
| function | `_mutate` | `(command)` | — | [src](../../../core/services/cheap_lane_control.py#L221) |
| function | `apply_control` | `(command, actor)` | — | [src](../../../core/services/cheap_lane_control.py#L262) |
| function | `simulate_route` | `(task_kind, skip_providers)` | — | [src](../../../core/services/cheap_lane_control.py#L313) |

## `core/services/cheap_lane_dashboard.py`
_Composite, partial-safe snapshot for the Cheap Lane control center._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `invocation_trends` | `(*, window_hours)` | — | [src](../../../core/services/cheap_lane_dashboard.py#L15) |
| function | `_section` | `(source, loader)` | — | [src](../../../core/services/cheap_lane_dashboard.py#L28) |
| function | `build_cheap_lane_dashboard` | `(window_hours=…)` | — | [src](../../../core/services/cheap_lane_dashboard.py#L49) |

## `core/services/cheap_lane_diagnostics.py`
_Read-only, deterministic diagnostics over Cheap Lane source-of-truth data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_time` | `(value)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L12) |
| function | `recent_invocations` | `(*, since, limit=…)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L20) |
| function | `central_evidence` | `(*, limit=…)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L36) |
| function | `route_integrity` | `(*, since)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L49) |
| function | `_finding` | `(code, severity, now, evidence, *, provider=…, slot_id=…)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L102) |
| function | `invocation_health` | `(rows)` | Summarize the full invocation window without merging account outcomes. | [src](../../../core/services/cheap_lane_diagnostics.py#L123) |
| function | `unrouted_pool_invocations` | `(rows)` | Find missing route IDs only where a cheap-pool route was expected. | [src](../../../core/services/cheap_lane_diagnostics.py#L150) |
| function | `health_divergence` | `(slots, *, since)` | Find cooldowns contradicted by a later success for the exact slot. | [src](../../../core/services/cheap_lane_diagnostics.py#L165) |
| function | `diagnose_cheap_lane` | `(now=…)` | — | [src](../../../core/services/cheap_lane_diagnostics.py#L220) |

## `core/services/cheap_lane_failure_policy.py`
_Hvor længe skal et cheap-lane-slot i karantæne? Afhænger af HVORFOR det fejlede._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify` | `(error_kind, message=…)` | ``'permanent'`` | ``'depleted'`` | ``'transient'``. | [src](../../../core/services/cheap_lane_failure_policy.py#L95) |
| function | `model_retired` | `(error_kind, message=…)` | Er selve MODELLEN væk — for alle konti? (Til den pr.-model-tilstand.) | [src](../../../core/services/cheap_lane_failure_policy.py#L129) |
| function | `quarantine_seconds` | `(error_kind, *, retry_after_s=…, message=…)` | Karantæne-længde, eller ``0`` når slottet skal følge den normale breaker-trappe. | [src](../../../core/services/cheap_lane_failure_policy.py#L147) |

## `core/services/cheap_lane_floor.py`
_Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `floor_targets` | `()` | Bund-kæden, config-overstyrbar. Self-safe → default ved fejl. | [src](../../../core/services/cheap_lane_floor.py#L46) |
| function | `floor_result` | `(*, lane, reason, provider=…, model=…, text=…, status=…, extra=…)` | Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund. | [src](../../../core/services/cheap_lane_floor.py#L60) |
| function | `_execute_floor_target` | `(*, provider, model, message, lane)` | Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles | [src](../../../core/services/cheap_lane_floor.py#L74) |
| function | `attempt_floor` | `(*, message, lane, reason)` | Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT | [src](../../../core/services/cheap_lane_floor.py#L94) |

## `core/services/cheap_lane_health_reconcile.py`
_Reconcile balancer cooldowns with successful calls from the shared cheap lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reconcile_successes` | `(states, now_epoch)` | A later successful invocation proves a profile's old failure has healed. | [src](../../../core/services/cheap_lane_health_reconcile.py#L12) |

## `core/services/cheap_lane_history.py`
_Hvordan klarer cheap lane sig? — historikken bag de 90.000 kald._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_siden` | `(timer)` | — | [src](../../../core/services/cheap_lane_history.py#L46) |
| function | `_sikr_skema` | `(conn)` | Tabellen og dens `auth_profile`-kolonne skal findes, ogsaa foer foerste kald. | [src](../../../core/services/cheap_lane_history.py#L50) |
| function | `_rows` | `(sql, params)` | — | [src](../../../core/services/cheap_lane_history.py#L74) |
| function | `_percentil` | `(vaerdier, p)` | p50/p95 uden numpy. Tom liste → 0. | [src](../../../core/services/cheap_lane_history.py#L82) |
| function | `udbyder_historik` | `(timer=…, lane=…)` | Én raekke pr. (udbyder, model) i vinduet: kald, fejl, latens, pris. | [src](../../../core/services/cheap_lane_history.py#L91) |
| function | `_fejlkoder_pr_udbyder` | `(lane, siden)` | De hyppigste fejlkoder pr. (udbyder, model). Tomt ved fejl. | [src](../../../core/services/cheap_lane_history.py#L177) |
| function | `seneste_fejl` | `(timer=…, lane=…, loft=…)` | De nyeste fejl med besked — halen man skal laese naar noget er galt. | [src](../../../core/services/cheap_lane_history.py#L197) |
| function | `tidsserie` | `(timer=…, lane=…, spand_minutter=…)` | Kald og fejl pr. tidsspand — kurven bag «klarer den sig bedre i dag?». | [src](../../../core/services/cheap_lane_history.py#L231) |

## `core/services/cheap_lane_payloads.py`
_Bounded, redacted payload capture for Cheap Lane invocations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RedactionResult` | `` | — | [src](../../../core/services/cheap_lane_payloads.py#L29) |
| function | `_configured_patterns` | `()` | — | [src](../../../core/services/cheap_lane_payloads.py#L35) |
| function | `_retention_days` | `()` | — | [src](../../../core/services/cheap_lane_payloads.py#L45) |
| function | `_redact_fields` | `(value)` | — | [src](../../../core/services/cheap_lane_payloads.py#L57) |
| function | `_bounded_utf8` | `(text)` | — | [src](../../../core/services/cheap_lane_payloads.py#L81) |
| function | `redact_payload` | `(value)` | Return a JSON-safe or textual payload with secrets removed and size bounded. | [src](../../../core/services/cheap_lane_payloads.py#L91) |
| function | `capture_invocation_payload` | `(*, invocation_id, prompt, response)` | Redact and persist payloads without ever failing the provider call. | [src](../../../core/services/cheap_lane_payloads.py#L115) |
| function | `purge_expired_payloads` | `(now=…)` | Delete expired payload bodies while retaining invocation metadata. | [src](../../../core/services/cheap_lane_payloads.py#L147) |

## `core/services/cheap_lane_quotas.py`
_Quota policy and measured capacity for the Cheap Lane control center._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_quota_policy` | `(*, provider, auth_profile, windows, expected_revision=…)` | — | [src](../../../core/services/cheap_lane_quotas.py#L18) |
| function | `observe_provider_quota` | `(*, provider, auth_profile, observation)` | Persist an adapter's normalized provider quota observation. | [src](../../../core/services/cheap_lane_quotas.py#L31) |
| function | `_utc` | `(value)` | — | [src](../../../core/services/cheap_lane_quotas.py#L65) |
| function | `_parse_time` | `(value)` | — | [src](../../../core/services/cheap_lane_quotas.py#L71) |
| function | `_period_bounds` | `(period, now)` | — | [src](../../../core/services/cheap_lane_quotas.py#L78) |
| function | `_monthly_bounds` | `(reset_day, now)` | Return the current UTC monthly window for a provider reset day. | [src](../../../core/services/cheap_lane_quotas.py#L98) |
| function | `_usage` | `(*, provider, auth_profile, unit, start, end)` | — | [src](../../../core/services/cheap_lane_quotas.py#L115) |
| function | `_cheap_providers` | `(registry)` | — | [src](../../../core/services/cheap_lane_quotas.py#L133) |
| function | `_active_profiles` | `(provider, registry_profile, *, multiprofile)` | Use the same ready account scan as the cheap-lane router. | [src](../../../core/services/cheap_lane_quotas.py#L150) |
| function | `_account_group` | `(provider, profile)` | Logical owner of usage; gateway Ollama Cloud uses its own account2 login. | [src](../../../core/services/cheap_lane_quotas.py#L160) |
| function | `_measured_usage` | `(now)` | Calendar-window token accounting, including profiles without policies. | [src](../../../core/services/cheap_lane_quotas.py#L173) |
| function | `_estimated_capacity` | `(now, members, usage)` | Upper-bound forecast from configured request caps and observed call size. | [src](../../../core/services/cheap_lane_quotas.py#L222) |
| function | `capacity_snapshot` | `(*, now=…)` | Combine configured policy, fresh provider truth, and observed usage. | [src](../../../core/services/cheap_lane_quotas.py#L300) |

## `core/services/cheap_lane_route_write.py`
_Best-effort persistence for cheap-lane route traces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_spor_uden_at_vaelte` | `(skriv, **felter)` | Write a route trace without letting telemetry interrupt the call. | [src](../../../core/services/cheap_lane_route_write.py#L4) |

## `core/services/cheap_lane_selfheal.py`
_cheap_lane_selfheal — cheap-lane maa ALDRIG stale eller doe (Bjoern 16.jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_slukket` | `()` | Udbydere og (udbyder, model) der er slået fra i registret. | [src](../../../core/services/cheap_lane_selfheal.py#L32) |
| function | `_stale_targets` | `(limit)` | (provider, model) der skal re-probes. To kilder: | [src](../../../core/services/cheap_lane_selfheal.py#L50) |
| function | `reprobe` | `(provider, model)` | Minimalt sundheds-probe. Healer state ved succes, saetter frisk cooldown ved fejl. | [src](../../../core/services/cheap_lane_selfheal.py#L116) |
| function | `run_selfheal` | `(*, max_probes=…)` | Re-probe op til max_probes fastlaaste providere. Returnér {healed, still_down}. | [src](../../../core/services/cheap_lane_selfheal.py#L159) |

## `core/services/cheap_lane_trace_context.py`
_Stable identity carried across Cheap Lane attempts and fallbacks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CheapLaneTraceContext` | `` | — | [src](../../../core/services/cheap_lane_trace_context.py#L9) |
| method | `CheapLaneTraceContext.create` | `(cls, *, correlation_id=…, daemon=…, task_kind=…, attempt=…, retry_parent_id=…, fallback_parent_id=…)` | — | [src](../../../core/services/cheap_lane_trace_context.py#L18) |
| method | `CheapLaneTraceContext.next_fallback` | `(self, parent_id)` | — | [src](../../../core/services/cheap_lane_trace_context.py#L37) |
| function | `candidate_slot_id` | `(candidate)` | — | [src](../../../core/services/cheap_lane_trace_context.py#L46) |

## `core/services/cheap_provider_breaker_adapters.py`
_Per-provider circuit-breaker adaptere for OllamaFreeAPI og Arko._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ofa_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L24) |
| function | `_ofa_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L31) |
| function | `_ofa_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L38) |
| function | `_arko_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L49) |
| function | `_arko_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L56) |
| function | `_arko_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L63) |

## `core/services/cheap_provider_catalogue.py`
_Kataloget over cheap-lane-udbydere — hvem findes, hvad koster de, hvad virker._

_(no top-level classes or functions)_

## `core/services/cheap_provider_reasoning_budget.py`
_Cheap lane: skeln «modellen tænkte budgettet op» fra «modellen er død»._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reasoning_exhausted` | `(data)` | Tomt svar fordi modellen tænkte budgettet op — ikke fordi den er død. | [src](../../../core/services/cheap_provider_reasoning_budget.py#L19) |

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L35) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L81) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L82) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L99) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L109) |
| function | `provider_cost_class` | `(provider)` | 'free' (default) eller 'paid'. Betalte providers (copilot-premium) må KUN | [src](../../../core/services/cheap_provider_runtime_adapters.py#L113) |
| function | `is_routable_provider` | `(provider)` | False = provideren må IKKE vælges i normal routing (kun evt. som nød-bund). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L120) |
| function | `_huggingface_runtime_token` | `()` | Bagudkompatibel indpakning. Se `cheap_provider_runtime_keys`. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L137) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L142) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L187) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L261) |
| function | `_resolve_egress_proxy` | `(*, provider, auth_profile)` | Task 8b: resolve the egress proxy URL for a (provider, auth_profile) slot. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L284) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L303) |
| function | `_with_quota_observation` | `(provider, auth_profile, result)` | Persist only explicitly normalized quota data returned by an adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L401) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…, extra_body=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L441) |
| function | `_execute_opencode_chat` | `(*, model, base_url, message, timeout=…)` | Kald OpenCode Zen gennem klientens lokale server. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L661) |
| function | `_opencode_chat_result` | `(*, entry, text)` | Normalisér en opencode-assistentbesked til lanens fælles returformat. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L755) |
| function | `deepseek_request_for_thinking_mode` | `(model, thinking_mode)` | Map composer thinking_mode -> (model, extra_body) WITHOUT the deprecated aliases | [src](../../../core/services/cheap_provider_runtime_adapters.py#L777) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Backward-compat: return only the model (never the deprecated alias). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L798) |
| function | `contains_dsml_tool_intent` | `(text)` | True for every DeepSeek DSML tool-call dialect observed in production. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L811) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L819) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L879) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L906) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L933) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L958) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L975) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L999) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1009) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1049) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1081) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message, provider=…)` | Call an Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1149) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1221) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1252) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…, proxy=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1300) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…, proxy=…, source_address=…, nat64_sni=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1363) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1453) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1481) |
| function | `provider_min_failure_cooldown_seconds` | `(provider)` | Mindste pause efter en fejl for `provider` (katalog-nøgle | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1498) |
| function | `_notify_checkin_required` | `(provider)` | Læg en nudge i Jarvis' awareness når en checkin-gated provider (FreeTheAi) er låst, | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1513) |
| function | `_afvis_udbyder_fejl` | `(provider, text)` | En kvote-besked leveret som modellens INDHOLD er ikke et svar. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1535) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1565) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1595) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1616) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1636) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1680) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1696) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1718) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1729) |

## `core/services/cheap_provider_runtime_keys.py`
_Udbydere hvis ejer-nøgle bor i `runtime.json` — ikke i auth-profil-arkivet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `runtime_owner_key` | `(provider)` | Den delte ejer-nøgle for `provider`, eller "" hvis den ikke findes. | [src](../../../core/services/cheap_provider_runtime_keys.py#L59) |
| function | `has_runtime_owner_key` | `(provider)` | Bruges af readiness. Adskilt fra `runtime_owner_key` så kaldere ikke | [src](../../../core/services/cheap_provider_runtime_keys.py#L78) |

## `core/services/cheap_provider_runtime_selection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L51) |
| function | `_execute_provider_chat` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L58) |
| function | `provider_runtime_defaults` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L62) |
| function | `record_cheap_provider_invocation` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L66) |
| function | `cheap_lane_status_surface` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L88) |
| function | `invalidate_cheap_lane_status_cache` | `()` | Force-clear the status-surface and quota caches. | [src](../../../core/services/cheap_provider_runtime_selection.py#L139) |
| function | `test_provider_target` | `(*, provider, model, auth_profile, base_url=…, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L152) |
| function | `smoke_cheap_lane` | `(*, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L180) |
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L357) |
| function | `_central_route_shadow` | `()` | Task 9: kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_provider_runtime_selection.py#L361) |
| function | `_central_route_live` | `()` | Task 9: brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_provider_runtime_selection.py#L370) |
| function | `_flag_multiprofile` | `()` | Task 6: yield én kandidat pr. (provider, klar auth-profil) i stedet for kun | [src](../../../core/services/cheap_provider_runtime_selection.py#L379) |
| function | `_flag_profile_roundrobin` | `()` | A (2026-07-24): when multiprofile is on AND a provider has >1 ready auth | [src](../../../core/services/cheap_provider_runtime_selection.py#L390) |
| function | `_roundrobin_profiles` | `(provider, profiles)` | Rotate ``profiles`` by a per-provider counter (PEEK — does not advance) so | [src](../../../core/services/cheap_provider_runtime_selection.py#L409) |
| function | `_advance_profile_rr` | `(provider)` | Advance the round-robin counter for ``provider`` by one — call exactly once | [src](../../../core/services/cheap_provider_runtime_selection.py#L423) |
| function | `_resolve_proxy` | `(egress, endpoints=…)` | Task 8b: map an egress ('home'|'vpn'|'he6') to its proxy endpoint URL. | [src](../../../core/services/cheap_provider_runtime_selection.py#L429) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_provider_runtime_selection.py#L451) |
| function | `_maybe_shadow_compare` | `(old_target)` | Shadow-hook før select returnerer. OFF → no-op, byte-identisk. | [src](../../../core/services/cheap_provider_runtime_selection.py#L468) |
| function | `_maybe_central_route_live` | `(old_target, candidates, kind, skip_providers, latency_sensitive=…)` | Task 9 live: når central_route_live er ON henter selection sit pick fra det | [src](../../../core/services/cheap_provider_runtime_selection.py#L480) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…, correlation_id=…, daemon=…, persist_trace=…, latency_sensitive=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L524) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…, lane=…, correlation_id=…, daemon=…, attempt=…, retry_parent_id=…, fallback_parent_id=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L726) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L970) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L1049) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1090) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1140) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1305) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1319) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1338) |
| function | `_record_provider_success` | `(*, provider, model, auth_profile, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1352) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…, trace_context=…, route_decision_id=…, egress=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1408) |

## `core/services/cheap_provider_runtime_streaming.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_streaming.py#L24) |
| function | `_iter_openai_compatible_chat_events` | `(*, provider, model, auth_profile, base_url, messages, tools=…, temperature=…, top_p=…, extra_body=…)` | Stream OpenAI-compatible /chat/completions deltas via SSE. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L33) |
| function | `_list_openai_codex_models` | `()` | Static model list for OpenAI Codex (ChatGPT Plus OAuth). | [src](../../../core/services/cheap_provider_runtime_streaming.py#L389) |
| function | `_execute_openai_codex_chat` | `(*, model, auth_profile, base_url, message)` | Execute a chat call via OpenAI's Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L401) |
| function | `_convert_tools_to_responses_format` | `(tools)` | Convert Chat-Completions tool defs to Responses API format. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L554) |
| function | `_iter_openai_codex_chat_events` | `(*, model, auth_profile, base_url, message, tools=…, input_items=…)` | Stream raw SSE events from the OpenAI Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L586) |

## `core/services/child_authority.py`
_Et barn maa ikke laane foraeldrens autoritet — Fase 5._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `uden_foraeldrens_godkendelse` | `()` | Koer barnets arbejde UDEN foraeldrens ejer-godkendelse. | [src](../../../core/services/child_authority.py#L41) |

## `core/services/child_failure_signal.py`
_Et barn der doer, skal kunne SES — Fase 5._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `note_child_ended` | `(agent_id, *, status, role=…, provider=…, model=…, error=…, parent_run_id=…)` | Sig hoejt at et barn endte uden at levere. Kaster ALDRIG. | [src](../../../core/services/child_failure_signal.py#L43) |
| function | `note_from_registry` | `(agent)` | Bekvem indgang naar man allerede har registry-raekken. | [src](../../../core/services/child_failure_signal.py#L92) |

## `core/services/chronicle_consolidation_brief_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_briefs_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_brief_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_brief_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_brief_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_briefs` | `(*, briefs, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, brief)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L326) |
| function | `_brief_type` | `(*, chronicle_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L356) |
| function | `_brief_weight` | `(*, chronicle_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L403) |
| function | `_weight_from_brief_type` | `(brief_type)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L454) |

## `core/services/chronicle_consolidation_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_proposal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_proposal_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L326) |
| function | `_proposal_type` | `(*, brief_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L356) |
| function | `_proposal_weight` | `(*, brief_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L403) |
| function | `_weight_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L454) |

## `core/services/chronicle_consolidation_signal_tracking.py`
_Chronicle/consolidation signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L51) |
| function | `refresh_runtime_chronicle_consolidation_signal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L77) |
| function | `build_runtime_chronicle_consolidation_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L81) |
| function | `_extract_chronicle_consolidation_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L85) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L243) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L262) |
| function | `_chronicle_consolidation_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L300) |
| function | `_chronicle_type` | `(*, cadence_state, promotion_type, has_remembered_fact)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L319) |
| function | `_chronicle_weight` | `(*, cadence_state, has_promotion, contradiction_pressure, outcome_status)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L334) |
| function | `_focus_text` | `(outcome, cadence, *, domain_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L348) |
| function | `_summary_line` | `(*, chronicle_type, chronicle_focus)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L364) |
| function | `_grounding_mode` | `(*, has_private_state, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L370) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L389) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L396) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L403) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L409) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L421) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L432) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L440) |

## `core/services/chronicle_engine.py`
_Chronicle Engine — Jarvis' narrative autobiography that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ChronicleAppraisal` | `` | Structured chronicle context — replaces hardcoded narrative prompts. | [src](../../../core/services/chronicle_engine.py#L36) |
| function | `maybe_write_chronicle_entry` | `()` | Write a chronicle entry if enough time has passed since the last one. | [src](../../../core/services/chronicle_engine.py#L57) |
| function | `compare_self_over_time` | `()` | Temporal self-perception — how have I changed? | [src](../../../core/services/chronicle_engine.py#L208) |
| function | `build_chronicle_surface` | `()` | — | [src](../../../core/services/chronicle_engine.py#L236) |
| function | `get_chronicle_context_for_prompt` | `(n=…, max_chars=…)` | Return recent chronicle entries formatted for prompt injection. | [src](../../../core/services/chronicle_engine.py#L249) |
| function | `_build_appraisal` | `(recent_runs, period, previous_entries=…)` | Build a structured ChronicleAppraisal from raw run data. | [src](../../../core/services/chronicle_engine.py#L295) |
| function | `_build_narrative` | `(recent_runs, period, previous_entries=…)` | Build a chronicle entry narrative, preferring LLM prose. | [src](../../../core/services/chronicle_engine.py#L349) |
| function | `_render_template_narrative` | `(appraisal)` | Render a deterministic fallback narrative from a structured appraisal. | [src](../../../core/services/chronicle_engine.py#L379) |
| function | `_render_narrative_prompt` | `(appraisal)` | Render an LLM narrative prompt from a structured ChronicleAppraisal. | [src](../../../core/services/chronicle_engine.py#L400) |
| function | `_collect_topics` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L448) |
| function | `_sanitize_narrative` | `(text)` | — | [src](../../../core/services/chronicle_engine.py#L468) |
| function | `project_entry_to_markdown` | `(entry)` | — | [src](../../../core/services/chronicle_engine.py#L483) |
| function | `_chronicle_markdown_path` | `()` | — | [src](../../../core/services/chronicle_engine.py#L514) |
| function | `_rotate_chronicle_if_needed` | `(chronicle_path)` | — | [src](../../../core/services/chronicle_engine.py#L518) |
| function | `_coerce_text_list` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L545) |
| function | `_emit_degraded_event` | `(*, period, reason)` | — | [src](../../../core/services/chronicle_engine.py#L560) |
| function | `_extract_key_events` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L570) |
| function | `_extract_lessons` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L580) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L591) |

## `core/services/ci_status_watch.py`
_CI-status — set, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/ci_status_watch.py#L74) |
| class | `ApiUkendt` | `` | Vi kunne ikke se CI. | [src](../../../core/services/ci_status_watch.py#L78) |
| function | `_rapporterede` | `()` | {run_id: iso-tidsstempel} for det vi allerede har set. | [src](../../../core/services/ci_status_watch.py#L88) |
| function | `_husk` | `(ids)` | Skriv id'erne som sete — atomisk, så api og runtime ikke overskriver | [src](../../../core/services/ci_status_watch.py#L111) |
| function | `_grundlinje` | `()` | Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang. | [src](../../../core/services/ci_status_watch.py#L127) |
| function | `_hent_runs` | `()` | Kørslerne på `main`. Rejser `ApiUkendt` når vi ikke kunne se dem. | [src](../../../core/services/ci_status_watch.py#L143) |
| function | `scan_roede` | `()` | Nye røde kørsler på `main` siden sidst — efter grundlinjen. | [src](../../../core/services/ci_status_watch.py#L167) |
| function | `_beskriv` | `(run)` | — | [src](../../../core/services/ci_status_watch.py#L208) |
| function | `_sekunder_siden` | `(sidste)` | Sekunder siden forrige tjek — eller None når stemplet mangler eller er | [src](../../../core/services/ci_status_watch.py#L218) |
| function | `tik` | `()` | Tjek CI på `main` og læg én followup for nye røde kørsler. | [src](../../../core/services/ci_status_watch.py#L230) |

## `core/services/claim_scanner.py`
_Claim Scanner — output gate for the Lying Engine (Layer 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_active_time_pin` | `()` | Read the current Time Pin from the prompt contract's cache. | [src](../../../core/services/claim_scanner.py#L69) |
| function | `_extract_time_from_pin` | `(pin_text)` | Extract the 'LIGE NU' timestamp block from a Time Pin section. | [src](../../../core/services/claim_scanner.py#L78) |
| function | `_now_as_pin_string` | `()` | Get current time formatted as the Time Pin would show it. | [src](../../../core/services/claim_scanner.py#L90) |
| function | `_categorize_line` | `(line)` | For a single line of text, return list of (category, matched_text, match). | [src](../../../core/services/claim_scanner.py#L98) |
| function | `_verify_time_claim` | `(matched_text)` | Verify a time claim against the active Time Pin. | [src](../../../core/services/claim_scanner.py#L130) |
| function | `_verify_env_claim` | `(matched_text)` | Verify environment claims — non-trivial, always True for now (future: check tool cache). | [src](../../../core/services/claim_scanner.py#L175) |
| function | `_verify_system_claim` | `(matched_text)` | Verify system claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L180) |
| function | `_verify_stats_claim` | `(matched_text)` | Verify statistic claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L190) |
| function | `_repair_time_claim` | `(line, matched_text)` | Replace a time claim with the correct time from the Time Pin. | [src](../../../core/services/claim_scanner.py#L210) |
| function | `_is_current_time_claim` | `(line, matched_text)` | True kun hvis linjen EKSPLICIT hævder hvad klokken er lige nu. | [src](../../../core/services/claim_scanner.py#L239) |
| function | `_repair_claim` | `(line, category, matched_text)` | Apply category-specific repair to a line. | [src](../../../core/services/claim_scanner.py#L248) |
| function | `_system_footnote` | `(matched_text)` | 2026-07-06: byg en fodnote for en ⚙️ system-claim (IP/host/path) i den | [src](../../../core/services/claim_scanner.py#L291) |
| function | `_extract_number` | `(text)` | Extract the first number from a string for replacement. | [src](../../../core/services/claim_scanner.py#L307) |
| function | `_commit_exists` | `(h)` | True hvis `h` resolver til et commit i hovedrepoet. Fail-open: ved | [src](../../../core/services/claim_scanner.py#L334) |
| function | `flag_unknown_commit_hashes` | `(text, *, max_check=…)` | Markér backtick-wrappede commit-hashes der ikke findes i hovedrepoet. | [src](../../../core/services/claim_scanner.py#L353) |
| function | `_collect_unknown_commit_hash_footnotes` | `(text, *, max_check=…)` | 2026-07-06: samme detektion som flag_unknown_commit_hashes, men i stedet | [src](../../../core/services/claim_scanner.py#L384) |
| function | `scan_response` | `(text)` | Scan a response text for unverified factual claims and repair them. | [src](../../../core/services/claim_scanner.py#L412) |
| function | `_fabricated_tool_result_footnote` | `(text)` | Kør fabrikations-gaten og gør verdiktet SYNLIGT — uden at dræbe runden. | [src](../../../core/services/claim_scanner.py#L505) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L552) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L560) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L590) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L662) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L730) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L757) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

