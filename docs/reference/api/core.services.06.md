# `core.services.06` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_todo.py`
_Central TODO — ÉN prioriteret, pollbar huskeliste på tværs af ALLE clusters. I stedet for_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_incident_is_fresh` | `(inc, *, max_age_h=…)` | True hvis incidentens ts er inden for max_age_h. Ukendt/uparsbar ts → True (fail-open: | [src](../../../core/services/central_todo.py#L28) |
| function | `_item` | `(priority, source, what, **extra)` | — | [src](../../../core/services/central_todo.py#L42) |
| function | `build_todo` | `(*, max_items=…)` | Saml + ranger todos fra alle clusters. Self-safe — en kilde der fejler udelades. | [src](../../../core/services/central_todo.py#L46) |
| function | `poll` | `(*, limit=…)` | Pollbar af Claude i tomgang: top-prioriterede todos + tælling pr. prioritet. | [src](../../../core/services/central_todo.py#L133) |
| function | `build_central_todo_surface` | `()` | MC-surface — read-only prioriteret huskeliste. | [src](../../../core/services/central_todo.py#L146) |

## `core/services/central_tone.py`
_core/services/central_tone.py — Centralens sproglige TONE-PROFIL (rådets #5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_valence` | `()` | Læs den ene FØLTE tilstand {tone, score, intensitet}. Kaster (fanges udenfor). | [src](../../../core/services/central_tone.py#L56) |
| function | `_read_affect` | `()` | Læs affekt-fordelingen {tryk,varme,uro,ro,dominant,total}. Kaster (fanges udenfor). | [src](../../../core/services/central_tone.py#L63) |
| function | `_read_pressure_signals` | `()` | Let central-status: åbne breakers + uløste severe incidents. Self-safe → {}. | [src](../../../core/services/central_tone.py#L70) |
| function | `_absorb` | `(cluster, nerve, value, **kw)` | Indirektion så absorb kan patches i test uden at ramme central_core. | [src](../../../core/services/central_tone.py#L86) |
| function | `_derive_register` | `(dominant_affect, *, under_pressure)` | Afled sprogligt register fra dominant affekt + system-pres. Deterministisk. | [src](../../../core/services/central_tone.py#L96) |
| function | `build_tone_profile` | `()` | Producér Centralens sproglige tone-profil fra system-tilstand. Self-safe. | [src](../../../core/services/central_tone.py#L114) |
| function | `build_tone_surface` | `()` | Mission Control / read-only surface for tone-profilen. Self-safe. | [src](../../../core/services/central_tone.py#L187) |

## `core/services/central_trace.py`
_Trace-sink for Centralen (§3.2/§7). En trådsikker, volumen-tolerant ring-buffer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TraceRecord` | `` | — | [src](../../../core/services/central_trace.py#L17) |
| class | `TraceSink` | `` | — | [src](../../../core/services/central_trace.py#L30) |
| method | `TraceSink.__init__` | `(self, maxlen=…)` | — | [src](../../../core/services/central_trace.py#L31) |
| method | `TraceSink.record` | `(self, rec)` | — | [src](../../../core/services/central_trace.py#L38) |
| method | `TraceSink.subscribe` | `(self)` | — | [src](../../../core/services/central_trace.py#L70) |
| method | `TraceSink.unsubscribe` | `(self, q)` | — | [src](../../../core/services/central_trace.py#L76) |
| method | `TraceSink.records_for_run` | `(self, run_id)` | — | [src](../../../core/services/central_trace.py#L84) |
| method | `TraceSink.recent` | `(self, limit=…)` | — | [src](../../../core/services/central_trace.py#L88) |
| function | `sink` | `()` | — | [src](../../../core/services/central_trace.py#L96) |

## `core/services/central_trainman.py`
_Trainman — drømme → narrative erindringer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_dreams` | `(limit=…)` | Seneste distillerede/konsoliderede drømme (id, tema, timestamp). Self-safe. | [src](../../../core/services/central_trainman.py#L40) |
| function | `_existing_dream_memories` | `(limit=…)` | Trainmans allerede-vævede erindringer i private_brain (til idempotens + tema-forbindelser). | [src](../../../core/services/central_trainman.py#L49) |
| function | `_dream_id_of` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L59) |
| function | `_dream_theme` | `(dream)` | Øverste tema for en drøm. Konsoliderings-drømme bærer en themes-liste; distillat en top_theme. | [src](../../../core/services/central_trainman.py#L63) |
| function | `_dream_timestamp` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L74) |
| function | `_sig_of` | `(rec)` | Afkod source_signals-JSON på en vævet erindring (dream_id, theme, connected_to …). Self-safe. | [src](../../../core/services/central_trainman.py#L78) |
| function | `_interlanguage` | `(theme)` | Byg en interlanguage-notation for temaet. Prøv lexicon (bundne termer); ellers spec-stil | [src](../../../core/services/central_trainman.py#L88) |
| function | `_emotional_tone` | `(theme)` | Simpel deterministisk klang ud fra tema-ord. Ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L105) |
| function | `_weave_narrative` | `(*, theme, dream)` | Væv drømmen til en 1.-persons erindrings-historie. Ren tekst, ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L117) |
| function | `_connected_ids` | `(theme, existing, *, limit=…)` | record_id'er for tidligere vævede erindringer om SAMME tema (drømme-kontinuitet). Self-safe. | [src](../../../core/services/central_trainman.py#L126) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_trainman.py#L139) |
| function | `_write_memory` | `(*, dream_id, theme, narrative, interlanguage, connected_to, emotional_tone, now)` | Skriv den vævede erindring til private_brain (source='dream'). Returnerer record_id ('' ved fejl). | [src](../../../core/services/central_trainman.py#L149) |
| function | `_signal_agenda` | `(*, theme, count, dream_id)` | 3+ drømme om samme tema på 7 dage → lav-prioritets initiativ til Agendaen. Self-safe. | [src](../../../core/services/central_trainman.py#L183) |
| function | `transform_dreams` | `(*, trigger=…, last_visible_at=…)` | Væv nye drømme til narrative erindringer i private_brain (source='dream'). | [src](../../../core/services/central_trainman.py#L201) |
| function | `_count_theme_recent` | `(theme, memories, *, now)` | Antal vævede erindringer om `theme` indenfor RECURRENCE_WINDOW_DAYS. Self-safe. | [src](../../../core/services/central_trainman.py#L268) |
| function | `_theme_distribution` | `(memories, *, now, days=…)` | Tema→antal over de sidste `days` dage. Self-safe. | [src](../../../core/services/central_trainman.py#L285) |
| function | `_last_reflection_at` | `(existing)` | — | [src](../../../core/services/central_trainman.py#L300) |
| function | `_maybe_reflect` | `(*, existing, now)` | Én gang pr. ~døgn: skriv en metakognitiv erindring om de sidste 7 dages tema-fordeling. | [src](../../../core/services/central_trainman.py#L307) |
| function | `_maybe_silence_note` | `(*, existing, now)` | Temaer der før var tilbagevendende men har været tavse i 14 dage → nysgerrigheds-note. | [src](../../../core/services/central_trainman.py#L340) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_trainman.py#L392) |
| function | `build_trainman_surface` | `()` | Seneste vævede erindringer + tema-fordeling for Central-CLI. READ-ONLY. Self-safe. | [src](../../../core/services/central_trainman.py#L409) |
| function | `record_trainman` | `(*, trigger=…, last_visible_at=…)` | Cadence: væv nye drømme til erindringer. Self-safe — kaster aldrig. | [src](../../../core/services/central_trainman.py#L444) |

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
| function | `_notify_owner` | `(title, message, importance)` | — | [src](../../../core/services/central_watch.py#L56) |
| function | `_raise_flag` | `(cluster, nerve, *, severity, message, importance=…, make_incident=…)` | Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe. | [src](../../../core/services/central_watch.py#L70) |
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L103) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L108) |
| function | `_event_is_recent` | `(r, *, max_age_min=…)` | True hvis event-record er nyere end max_age_min. Fail-open ved ukendt/uparsbar | [src](../../../core/services/central_watch.py#L323) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen NYLIGT. Cross-proces. | [src](../../../core/services/central_watch.py#L338) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L352) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, failed) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L360) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra NYLIGE tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L376) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L394) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L403) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L417) |

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

## `core/services/chat_sessions.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_tool_result_for_reconstruct` | `(result_id)` | Serve-on-read loader: slå et gammelt tool-resultat op fra tool_result_store. | [src](../../../core/services/chat_sessions.py#L18) |
| function | `_content_json_for_row` | `(role, content, raw_json)` | Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort, | [src](../../../core/services/chat_sessions.py#L36) |
| function | `create_chat_session` | `(*, title=…, workspace_kind=…, workspace_root=…, team_id=…)` | — | [src](../../../core/services/chat_sessions.py#L51) |
| function | `get_or_create_named_session` | `(session_id, title)` | Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny). | [src](../../../core/services/chat_sessions.py#L86) |
| function | `_teams` | `()` | Lazy-import af teams-modulet (undgår import-cyklus ved opstart). | [src](../../../core/services/chat_sessions.py#L117) |
| function | `list_chat_sessions` | `(*, user_id=…)` | List chat sessions, optionally filtered to one user. | [src](../../../core/services/chat_sessions.py#L123) |
| function | `_make_snippet` | `(content, query, width=…)` | Byg et kort uddrag centreret om første match (case-insensitive). | [src](../../../core/services/chat_sessions.py#L202) |
| function | `search_chat_sessions` | `(query, *, user_id=…, limit=…)` | Søg sessioner på titel ELLER besked-indhold (user/assistant). | [src](../../../core/services/chat_sessions.py#L217) |
| function | `get_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L294) |
| function | `set_session_workspace` | `(session_id, *, kind, root)` | Bind (eller skift) en sessions Code-mode workspace. | [src](../../../core/services/chat_sessions.py#L346) |
| function | `append_chat_message` | `(*, session_id, role, content, created_at=…, tool_name=…, tool_arguments=…, user_id=…, workspace_name=…, reasoning_content=…, content_json=…)` | — | [src](../../../core/services/chat_sessions.py#L361) |
| function | `_recent_duplicate_user_message` | `(session_id, content, now_ts)` | Returnér den seneste besked-række HVIS den er en identisk brugerbesked inden | [src](../../../core/services/chat_sessions.py#L520) |
| function | `_infer_tool_name_from_content` | `(content)` | — | [src](../../../core/services/chat_sessions.py#L555) |
| function | `recent_chat_session_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L562) |
| function | `chat_session_messages_since_last_compact` | `(session_id, *, max_total=…)` | Hent ALT efter seneste compact_marker (eller hele session hvis ingen). | [src](../../../core/services/chat_sessions.py#L589) |
| function | `recent_chat_session_messages_by_user_turns` | `(session_id, *, user_turns=…, max_total=…)` | Hent de seneste N *user-turns* og alt der hører til dem. | [src](../../../core/services/chat_sessions.py#L650) |
| function | `_ensure_compact_marker_git_sha_column` | `()` | Add git_sha column to chat_messages if it doesn't exist (idempotent migration). | [src](../../../core/services/chat_sessions.py#L726) |
| function | `store_compact_marker` | `(session_id, summary_text, git_sha=…)` | Store a compact marker for the session. Returns the marker message_id. | [src](../../../core/services/chat_sessions.py#L738) |
| function | `get_compact_marker_with_sha` | `(session_id)` | Return (summary, git_sha) of the most recent compact marker, or (None, None). | [src](../../../core/services/chat_sessions.py#L769) |
| function | `get_compact_marker` | `(session_id)` | Return the most recent compact marker summary for the session, or None. | [src](../../../core/services/chat_sessions.py#L793) |
| function | `recent_chat_tool_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L811) |
| function | `rename_chat_session` | `(session_id, *, title)` | — | [src](../../../core/services/chat_sessions.py#L836) |
| function | `delete_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L850) |
| function | `_session_summary` | `(row)` | — | [src](../../../core/services/chat_sessions.py#L860) |
| function | `_normalize_title` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L872) |
| function | `_preview_text` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L879) |
| function | `_time_label` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L886) |
| function | `parse_channel_from_session_title` | `(title)` | Parse channel type and detail from a session title. | [src](../../../core/services/chat_sessions.py#L894) |
| function | `get_session_owner` | `(session_id)` | Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel. | [src](../../../core/services/chat_sessions.py#L924) |

## `core/services/cheap_lane_balancer.py`
_Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BalancerSlot` | `` | Immutable identity of a (provider, model) lane. | [src](../../../core/services/cheap_lane_balancer.py#L19) |
| method | `BalancerSlot.slot_id` | `(self)` | — | [src](../../../core/services/cheap_lane_balancer.py#L30) |
| class | `SlotState` | `` | Per-slot mutable runtime state. Persisted to JSON (timestamps deque is in-memory only). | [src](../../../core/services/cheap_lane_balancer.py#L35) |
| function | `_provider_router_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L67) |
| function | `_router_enabled_models` | `()` | Return list of dicts {provider, model, enabled, auth_profile, lane} | [src](../../../core/services/cheap_lane_balancer.py#L74) |
| function | `_credentials_ready` | `(provider, auth_profile)` | Check if provider has working credentials. Wraps existing helper. | [src](../../../core/services/cheap_lane_balancer.py#L104) |
| function | `_provider_metadata` | `(provider)` | Lookup provider's static config (rpm_limit, daily_limit, base_url, etc.). | [src](../../../core/services/cheap_lane_balancer.py#L113) |
| function | `_state_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L130) |
| function | `_state_to_dict` | `(state)` | Serialize SlotState to JSON-safe dict (skips deque). | [src](../../../core/services/cheap_lane_balancer.py#L137) |
| function | `_state_from_dict` | `(d)` | — | [src](../../../core/services/cheap_lane_balancer.py#L155) |
| function | `_load_state` | `()` | Load all slot-states from disk. Returns empty dict on missing/corrupt file. | [src](../../../core/services/cheap_lane_balancer.py#L172) |
| function | `_save_state` | `(states)` | Atomic write to state file. | [src](../../../core/services/cheap_lane_balancer.py#L190) |
| function | `_save_state_debounced` | `(states)` | — | [src](../../../core/services/cheap_lane_balancer.py#L209) |
| function | `_ensure_state` | `(states, slot_id)` | Get-or-create slot state. Mutates `states` in place. | [src](../../../core/services/cheap_lane_balancer.py#L219) |
| function | `_today_iso` | `(now=…)` | Returns UTC date string. Override hookable via module-level _datetime_for_today. | [src](../../../core/services/cheap_lane_balancer.py#L238) |
| function | `_count_recent_calls` | `(timestamps, now, window_seconds)` | Count timestamps falling within [now - window, now]. | [src](../../../core/services/cheap_lane_balancer.py#L244) |
| function | `_daily_used_from_db` | `(provider)` | Task 4 / Fund 5: daglig brug fra SQLite cheap_provider_invocations (samme kilde | [src](../../../core/services/cheap_lane_balancer.py#L250) |
| function | `_daily_headroom_for` | `(slot)` | Daily headroom fra SQLite frem for balancerens private JSON daily_use_count. | [src](../../../core/services/cheap_lane_balancer.py#L263) |
| function | `_observe_central` | `(nerve, payload)` | Task 5: skriv til Centralens system/<nerve>. Self-safe — observabilitet må | [src](../../../core/services/cheap_lane_balancer.py#L271) |
| function | `_emit_balancer_event` | `(name, payload)` | Ét sted: emit til eventbus (bagudkompatibelt) + observe fejl-events til Central. | [src](../../../core/services/cheap_lane_balancer.py#L281) |
| function | `_compute_weight` | `(slot, state, now)` | Returns non-negative weight; 0 means slot is ineligible right now. | [src](../../../core/services/cheap_lane_balancer.py#L294) |
| function | `_register_failure` | `(state, error_kind, *, retry_after_s=…, now)` | Update state after a failed call. | [src](../../../core/services/cheap_lane_balancer.py#L329) |
| function | `_register_success` | `(state, now)` | Update state after a successful call. | [src](../../../core/services/cheap_lane_balancer.py#L361) |
| function | `_is_dns_or_connection_error` | `(error_kind, exc=…)` | True if error indicates network-level (provider-wide) issue, not slot-specific. | [src](../../../core/services/cheap_lane_balancer.py#L378) |
| function | `_register_provider_wide_failure` | `(states, pool, provider, now, *, reason, cooldown_s=…)` | Apply cooldown to ALL slots from `provider`. Returns number of slots affected. | [src](../../../core/services/cheap_lane_balancer.py#L396) |
| function | `_select_slot` | `(states, pool, now)` | Pick a slot via weighted-random; returns None if all blocked. | [src](../../../core/services/cheap_lane_balancer.py#L439) |
| function | `_central_route_shadow` | `()` | Kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_lane_balancer.py#L487) |
| function | `_central_route_live` | `()` | Brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_lane_balancer.py#L496) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_lane_balancer.py#L505) |
| function | `_central_route_slot` | `(eligible_pool, tried_slot_ids)` | Spørg central_route om lane='cheap'-pick og map til en EGNET (untried) slot i | [src](../../../core/services/cheap_lane_balancer.py#L522) |
| function | `_maybe_central_route_slot` | `(weighted_slot, eligible_pool, tried_slot_ids)` | Hook før slot bruges: shadow-compare (OFF → no-op) + live-apply. Aldrig-tør | [src](../../../core/services/cheap_lane_balancer.py#L543) |
| function | `_call_provider_chat` | `(*, provider, model, auth_profile, base_url, message)` | Wrapper around cheap_provider_runtime._execute_provider_chat. | [src](../../../core/services/cheap_lane_balancer.py#L564) |
| function | `_append_recent_call` | `(slot_id, daemon, status, latency_ms, *, error=…)` | — | [src](../../../core/services/cheap_lane_balancer.py#L589) |
| function | `recent_calls` | `()` | Returns ring-buffer of last 75 calls (newest first). | [src](../../../core/services/cheap_lane_balancer.py#L607) |
| function | `call_balanced` | `(*, prompt, daemon_name=…, max_retries=…)` | Pick a slot via weighted-random; execute; on failure retry next slot. | [src](../../../core/services/cheap_lane_balancer.py#L612) |
| function | `build_slot_pool` | `()` | Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS. | [src](../../../core/services/cheap_lane_balancer.py#L825) |
| function | `reset_slot` | `(slot_id)` | Clear breaker, cooldown, and consecutive-failure streak for a slot. | [src](../../../core/services/cheap_lane_balancer.py#L912) |
| function | `disable_slot` | `(slot_id)` | Force a slot's weight to 0 until enable_slot is called. | [src](../../../core/services/cheap_lane_balancer.py#L924) |
| function | `enable_slot` | `(slot_id)` | Re-enable a manually-disabled slot. | [src](../../../core/services/cheap_lane_balancer.py#L933) |
| function | `refresh_pool` | `()` | Re-build the slot pool from provider_router.json. Returns current size. | [src](../../../core/services/cheap_lane_balancer.py#L942) |
| function | `_is_enabled` | `()` | Check RuntimeSettings.daemon_balancer_enabled. Default True. | [src](../../../core/services/cheap_lane_balancer.py#L953) |
| function | `balancer_snapshot` | `()` | Return full state surface for Mission Control telemetry. | [src](../../../core/services/cheap_lane_balancer.py#L962) |

## `core/services/cheap_lane_floor.py`
_Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `floor_targets` | `()` | Bund-kæden, config-overstyrbar. Self-safe → default ved fejl. | [src](../../../core/services/cheap_lane_floor.py#L21) |
| function | `floor_result` | `(*, lane, reason, provider=…, model=…, text=…, status=…, extra=…)` | Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund. | [src](../../../core/services/cheap_lane_floor.py#L35) |
| function | `_execute_floor_target` | `(*, provider, model, message, lane)` | Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles | [src](../../../core/services/cheap_lane_floor.py#L49) |
| function | `attempt_floor` | `(*, message, lane, reason)` | Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT | [src](../../../core/services/cheap_lane_floor.py#L69) |

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L24) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L471) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L472) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L489) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L499) |
| function | `provider_cost_class` | `(provider)` | 'free' (default) eller 'paid'. Betalte providers (copilot-premium) må KUN | [src](../../../core/services/cheap_provider_runtime_adapters.py#L503) |
| function | `is_routable_provider` | `(provider)` | False = provideren må IKKE vælges i normal routing (kun evt. som nød-bund). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L510) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L518) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L554) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L628) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L651) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…, extra_body=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L733) |
| function | `deepseek_request_for_thinking_mode` | `(model, thinking_mode)` | Map composer thinking_mode -> (model, extra_body) WITHOUT the deprecated aliases | [src](../../../core/services/cheap_provider_runtime_adapters.py#L866) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Backward-compat: return only the model (never the deprecated alias). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L887) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L896) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L951) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L978) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1005) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1030) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1047) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1071) |
| function | `_ofa_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1086) |
| function | `_ofa_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1093) |
| function | `_ofa_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1100) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1105) |
| function | `_arko_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1149) |
| function | `_arko_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1156) |
| function | `_arko_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1163) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1168) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1200) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message)` | Call the local Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1268) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1322) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1353) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1394) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1445) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1498) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1521) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1534) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1558) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1579) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1599) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1643) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1655) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1677) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1688) |

## `core/services/cheap_provider_runtime_selection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L40) |
| function | `_execute_provider_chat` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L47) |
| function | `provider_runtime_defaults` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L51) |
| function | `record_cheap_provider_invocation` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L55) |
| function | `cheap_lane_status_surface` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L77) |
| function | `invalidate_cheap_lane_status_cache` | `()` | Force-clear the status-surface and quota caches. | [src](../../../core/services/cheap_provider_runtime_selection.py#L128) |
| function | `test_provider_target` | `(*, provider, model, auth_profile, base_url=…, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L141) |
| function | `smoke_cheap_lane` | `(*, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L169) |
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L299) |
| function | `_central_route_shadow` | `()` | Task 9: kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_provider_runtime_selection.py#L303) |
| function | `_central_route_live` | `()` | Task 9: brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_provider_runtime_selection.py#L312) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_provider_runtime_selection.py#L321) |
| function | `_maybe_shadow_compare` | `(old_target)` | Shadow-hook før select returnerer. OFF → no-op, byte-identisk. | [src](../../../core/services/cheap_provider_runtime_selection.py#L338) |
| function | `_maybe_central_route_live` | `(old_target, candidates, kind, skip_providers)` | Task 9 live: når central_route_live er ON henter selection sit pick fra det | [src](../../../core/services/cheap_provider_runtime_selection.py#L350) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L390) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…, lane=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L476) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L597) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L676) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L717) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L766) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L879) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L936) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L953) |
| function | `_record_provider_success` | `(*, provider, model, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L994) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1045) |
| function | `_decode_state_metadata` | `(state)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1110) |
| function | `_rolling_average` | `(*, current_avg, current_count, new_value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1121) |
| function | `_smoke_quality_score` | `(*, expected, actual)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1127) |
| function | `_normalize_probe_text` | `(value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1137) |

## `core/services/cheap_provider_runtime_streaming.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_streaming.py#L24) |
| function | `_iter_openai_compatible_chat_events` | `(*, provider, model, auth_profile, base_url, messages, tools=…, temperature=…, top_p=…, extra_body=…)` | Stream OpenAI-compatible /chat/completions deltas via SSE. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L33) |
| function | `_list_openai_codex_models` | `()` | Static model list for OpenAI Codex (ChatGPT Plus OAuth). | [src](../../../core/services/cheap_provider_runtime_streaming.py#L322) |
| function | `_execute_openai_codex_chat` | `(*, model, auth_profile, base_url, message)` | Execute a chat call via OpenAI's Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L334) |
| function | `_convert_tools_to_responses_format` | `(tools)` | Convert Chat-Completions tool defs to Responses API format. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L487) |
| function | `_iter_openai_codex_chat_events` | `(*, model, auth_profile, base_url, message, tools=…, input_items=…)` | Stream raw SSE events from the OpenAI Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L519) |

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L36) |
| function | `refresh_runtime_chronicle_consolidation_signal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L59) |
| function | `build_runtime_chronicle_consolidation_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L90) |
| function | `_extract_chronicle_consolidation_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L123) |
| function | `_persist_chronicle_consolidation_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L280) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L349) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L368) |
| function | `_chronicle_type` | `(*, cadence_state, promotion_type, has_remembered_fact)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L406) |
| function | `_chronicle_weight` | `(*, cadence_state, has_promotion, contradiction_pressure, outcome_status)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L421) |
| function | `_focus_text` | `(outcome, cadence, *, domain_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L435) |
| function | `_summary_line` | `(*, chronicle_type, chronicle_focus)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L451) |
| function | `_grounding_mode` | `(*, has_private_state, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L457) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L476) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L483) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L490) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L496) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L508) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L519) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L527) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L533) |

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
| function | `_is_planned_time_context` | `(line, matched_text)` | True hvis linjen indeholder ord der indikerer at tidspunktet er | [src](../../../core/services/claim_scanner.py#L234) |
| function | `_repair_claim` | `(line, category, matched_text)` | Apply category-specific repair to a line. | [src](../../../core/services/claim_scanner.py#L247) |
| function | `_system_footnote` | `(matched_text)` | 2026-07-06: byg en fodnote for en ⚙️ system-claim (IP/host/path) i den | [src](../../../core/services/claim_scanner.py#L290) |
| function | `_extract_number` | `(text)` | Extract the first number from a string for replacement. | [src](../../../core/services/claim_scanner.py#L306) |
| function | `_commit_exists` | `(h)` | True hvis `h` resolver til et commit i hovedrepoet. Fail-open: ved | [src](../../../core/services/claim_scanner.py#L333) |
| function | `flag_unknown_commit_hashes` | `(text, *, max_check=…)` | Markér backtick-wrappede commit-hashes der ikke findes i hovedrepoet. | [src](../../../core/services/claim_scanner.py#L352) |
| function | `_collect_unknown_commit_hash_footnotes` | `(text, *, max_check=…)` | 2026-07-06: samme detektion som flag_unknown_commit_hashes, men i stedet | [src](../../../core/services/claim_scanner.py#L383) |
| function | `scan_response` | `(text)` | Scan a response text for unverified factual claims and repair them. | [src](../../../core/services/claim_scanner.py#L411) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L495) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L503) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L533) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L605) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L673) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L700) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

## `core/services/cluster_daemon.py`
_Cluster-daemon primitive — one Central-governed daemon per FAMILY of nerves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `shadow_mode_enabled` | `()` | True when cluster-daemons run in SHADOW (observe-only) mode. | [src](../../../core/services/cluster_daemon.py#L65) |
| class | `ClusterMember` | `` | One function inside a cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L87) |
| class | `ClusterDaemon` | `` | One Central-governed daemon for a FAMILY of member functions. | [src](../../../core/services/cluster_daemon.py#L122) |
| method | `ClusterDaemon._snapshot` | `(self, snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L136) |
| method | `ClusterDaemon._aggregate_signals` | `(self, snapshot)` | Collect every member's signals into ONE namespaced dict for the gate. | [src](../../../core/services/cluster_daemon.py#L148) |
| method | `ClusterDaemon._gate_fires` | `(self, snapshot)` | Run the family's SINGLE event-gate. Fail-OPEN → fire. | [src](../../../core/services/cluster_daemon.py#L167) |
| method | `ClusterDaemon.tick` | `(self, snapshot=…, *, shadow=…)` | Run the family for one heartbeat tick. NEVER raises. | [src](../../../core/services/cluster_daemon.py#L188) |
| method | `ClusterDaemon._report_to_central` | `(self, result, is_shadow)` | Best-effort parity telemetry to the Central trace-sink. Never raises. | [src](../../../core/services/cluster_daemon.py#L242) |
| function | `_somatic_signals` | `(snapshot)` | Somatic member gate-signal: machine pressure (drain + energy band). | [src](../../../core/services/cluster_daemon.py#L285) |
| function | `_somatic_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L297) |
| function | `_experienced_time_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L306) |
| function | `_experienced_time_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L323) |
| function | `_absence_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L332) |
| function | `_absence_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L343) |
| function | `_collect_somatic_snapshot` | `()` | Gather the somatic family's shared snapshot from the members' own | [src](../../../core/services/cluster_daemon.py#L351) |
| function | `build_somatic_family` | `()` | Construct the somatic/embodiment cluster-daemon (family #1). | [src](../../../core/services/cluster_daemon.py#L380) |
| function | `somatic_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L412) |
| function | `tick_cluster_somatic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the somatic cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L419) |
| function | `_iv_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (mirrors the daemons' | [src](../../../core/services/cluster_daemon.py#L468) |
| function | `_collect_innervoice_snapshot` | `()` | Gather the inner-voice family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L476) |
| function | `_iv_thought_stream_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L563) |
| function | `_iv_reflection_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L571) |
| function | `_iv_meta_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L579) |
| function | `_iv_irony_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L587) |
| function | `_iv_wonder_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L594) |
| function | `_iv_drift_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L604) |
| function | `_iv_thought_stream_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L615) |
| function | `_iv_reflection_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L624) |
| function | `_iv_meta_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L638) |
| function | `_iv_irony_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L656) |
| function | `_iv_wonder_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L661) |
| function | `_iv_drift_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L670) |
| function | `_iv_surface_observe` | `(builder_path, keys)` | — | [src](../../../core/services/cluster_daemon.py#L678) |
| function | `build_innervoice_family` | `()` | Construct the inner-voice cluster-daemon (family #2), LIVE. | [src](../../../core/services/cluster_daemon.py#L690) |
| function | `innervoice_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L766) |
| function | `tick_cluster_innervoice` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the inner-voice cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L773) |
| function | `_affect_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (no hash randomisation). | [src](../../../core/services/cluster_daemon.py#L847) |
| function | `_collect_affect_snapshot` | `()` | Gather the affect family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L854) |
| function | `_affect_surprise_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L938) |
| function | `_affect_conflict_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L945) |
| function | `_affect_desire_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L954) |
| function | `_affect_surprise_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L966) |
| function | `_affect_conflict_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L975) |
| function | `_affect_desire_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L980) |
| function | `build_affect_family` | `()` | Construct the affect cluster-daemon (family #3), LIVE. | [src](../../../core/services/cluster_daemon.py#L985) |
| function | `affect_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1033) |
| function | `_run_affect_nonllm_members` | `(snap, result)` | Run the NON-LLM affect members UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon.py#L1040) |
| function | `tick_cluster_affect` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the affect cluster-daemon family (#3). | [src](../../../core/services/cluster_daemon.py#L1066) |
| function | `_narrative_no_signals` | `(_snap)` | No gate signals — this family is TIME-BASED, not event-gated. Declaring | [src](../../../core/services/cluster_daemon.py#L1142) |
| function | `_narrative_development_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1151) |
| function | `_narrative_summary_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1156) |
| function | `_narrative_identity_drift_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1161) |
| function | `_narrative_identity_sketch_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1166) |
| function | `_narrative_consolidation_judge_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1171) |
| function | `build_narrative_family` | `()` | Construct the narrative/self-history cluster-daemon (family #4), LIVE. | [src](../../../core/services/cluster_daemon.py#L1176) |
| function | `narrative_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1243) |
| function | `_run_narrative_members` | `(snap, result)` | Run every narrative member UNCONDITIONALLY (no event-gate — time-based), | [src](../../../core/services/cluster_daemon.py#L1250) |
| function | `tick_cluster_narrative` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the narrative cluster-daemon family (#4). | [src](../../../core/services/cluster_daemon.py#L1269) |
| function | `_collect_cognition_snapshot` | `()` | Gather the cognition family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L1349) |
| function | `_cog_pattern_cf_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1371) |
| function | `_cog_pattern_cf_observe` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1378) |
| function | `_cog_pattern_cf_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1382) |
| function | `build_cognition_family` | `()` | Construct the cognition cluster-daemon (family #5), LIVE. | [src](../../../core/services/cluster_daemon.py#L1387) |
| function | `cognition_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1413) |
| function | `_cog_causal_inference_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1423) |
| function | `_cog_active_sensing_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1428) |
| function | `_cog_dream_insight_live` | `(_snap)` | dream_insight is signal-driven (not a timer): gather the latest dream- | [src](../../../core/services/cluster_daemon.py#L1433) |
| function | `_run_cognition_nonllm_members` | `(snap, result)` | Run the NON-LLM cognition members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon.py#L1459) |
| function | `tick_cluster_cognition` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the cognition cluster-daemon family (#5). | [src](../../../core/services/cluster_daemon.py#L1475) |

## `core/services/code_aesthetic_daemon.py`
_Code aesthetic daemon — weekly aesthetic reflection on the codebase._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_code_aesthetic_daemon` | `()` | Run aesthetic analysis if cadence elapsed. Returns {generated, reflection}. | [src](../../../core/services/code_aesthetic_daemon.py#L39) |
| function | `get_latest_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L64) |
| function | `build_code_aesthetic_surface` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L68) |
| function | `_get_recent_git_changes` | `()` | Get last 10 commit messages and changed file summary. | [src](../../../core/services/code_aesthetic_daemon.py#L81) |
| function | `_generate_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L101) |
| function | `_store_reflection` | `(reflection, now)` | — | [src](../../../core/services/code_aesthetic_daemon.py#L119) |

## `core/services/cognitive_architecture_surface.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_cognitive_architecture_surface` | `()` | Cached MC/self-model cognitive-architecture-surface. Self-safe → falder til fersk build. | [src](../../../core/services/cognitive_architecture_surface.py#L11) |
| function | `_build_cognitive_architecture_surface_uncached` | `()` | Build a shared cognitive architecture surface for MC and self-model. | [src](../../../core/services/cognitive_architecture_surface.py#L23) |

## `core/services/cognitive_chronicle.py`
_Cognitive Chronicle — user-scoped read layer for chronicle entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `query_chronicle_for_user` | `(limit=…)` | Return chronicle entries visible to the current user. | [src](../../../core/services/cognitive_chronicle.py#L15) |

## `core/services/cognitive_core_experiments.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_build` | `(builder, system_id, label)` | Call a builder function, returning a disabled-stub on any error. | [src](../../../core/services/cognitive_core_experiments.py#L6) |
| function | `build_cognitive_core_experiments_surface` | `()` | Build shared runtime truth for the bounded cognitive-core experiment state. | [src](../../../core/services/cognitive_core_experiments.py#L31) |
| function | `_build_recurrence_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L100) |
| function | `_build_global_workspace_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L127) |
| function | `_build_hot_meta_cognition_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L155) |
| function | `_build_surprise_afterimage_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L182) |
| function | `_build_attention_blink_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L212) |
| function | `_activity_state` | `(*, enabled, active)` | — | [src](../../../core/services/cognitive_core_experiments.py#L239) |
| function | `_strongest_carry_item` | `(items)` | — | [src](../../../core/services/cognitive_core_experiments.py#L247) |

## `core/services/cognitive_episodes.py`
_Cognitive episodes as an active learning primitive._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_episode` | `(*, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Persist a cognitive episode and publish an eventbus signal. | [src](../../../core/services/cognitive_episodes.py#L25) |
| function | `record_visible_run_episode` | `(*, run_id, session_id=…, provider=…, model=…, status=…, user_message=…, assistant_text=…, error=…)` | Record a post-run episode grounded in the visible-run event trail. | [src](../../../core/services/cognitive_episodes.py#L176) |
| function | `derive_episode_fields` | `(*, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Derive the five cognitive dimensions plus next-behavior policy. | [src](../../../core/services/cognitive_episodes.py#L209) |
| function | `build_cognitive_episode_surface` | `(*, limit=…)` | Return active directives for the conductor/prompt path. | [src](../../../core/services/cognitive_episodes.py#L295) |
| function | `build_cognitive_episode_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/cognitive_episodes.py#L325) |
| function | `_tool_names_for_run` | `(run_id)` | — | [src](../../../core/services/cognitive_episodes.py#L341) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/cognitive_episodes.py#L368) |
| function | `_summarize_visible_run` | `(*, status, tool_names, assistant_text, error)` | — | [src](../../../core/services/cognitive_episodes.py#L387) |
| function | `_fallback_summary` | `(*, status, tool_names, error)` | — | [src](../../../core/services/cognitive_episodes.py#L398) |
| function | `_confidence` | `(*, status, error, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L406) |
| function | `_uncertainty_sources` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L416) |
| function | `_self_check` | `(*, status, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L435) |
| function | `_what_would_change_mind` | `(*, interrupted, proposal_error)` | — | [src](../../../core/services/cognitive_episodes.py#L445) |
| function | `_salience` | `(*, interrupted, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L453) |
| function | `_attention_directive` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L461) |
| function | `_ignore_or_defer` | `(*, tool_heavy, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L479) |
| function | `_learning_lesson` | `(*, interrupted, proposal_error, status, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L487) |
| function | `_policy_update` | `(*, interrupted, proposal_error, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L505) |
| function | `_social_directive` | `(*, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L515) |
| function | `_user_state_hypothesis` | `(*, user_l, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L521) |
| function | `_perception_directive` | `(*, tool_names, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L531) |
| function | `_observed_changes` | `(*, tool_names, status, error)` | — | [src](../../../core/services/cognitive_episodes.py#L539) |
| function | `_next_behavior` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy, status)` | — | [src](../../../core/services/cognitive_episodes.py#L548) |
| function | `_prompt_priority` | `(*, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L569) |

## `core/services/cognitive_state_assembly.py`
_Cognitive state assembly — closes the loop between accumulated state and visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cognitive_cache_key` | `(mode_key)` | — | [src](../../../core/services/cognitive_state_assembly.py#L68) |
| function | `_cache_ttl_seconds` | `()` | Read TTL from settings; default 120s. TTL=0 disables caching. | [src](../../../core/services/cognitive_state_assembly.py#L72) |
| function | `_cache_enabled` | `()` | Check if caching is enabled in settings. TTL=0 also disables. | [src](../../../core/services/cognitive_state_assembly.py#L82) |
| function | `_build_invalidation_snapshot` | `()` | Snapshot the key state signals that invalidate the cache. | [src](../../../core/services/cognitive_state_assembly.py#L94) |
| function | `_is_cache_valid` | `(cache_key)` | Check if cached state for `mode_key` (e.g. 'full') is fresh+coherent. | [src](../../../core/services/cognitive_state_assembly.py#L129) |
| function | `_get_cached_state` | `(cache_key)` | Return cached cognitive state string if valid, None otherwise. | [src](../../../core/services/cognitive_state_assembly.py#L145) |
| function | `_set_cached_state` | `(cache_key, text, sources)` | Store assembled cognitive state in shared_cache (cross-worker). | [src](../../../core/services/cognitive_state_assembly.py#L193) |
| function | `invalidate_cognitive_state_cache` | `()` | Explicitly invalidate all cognitive state caches across workers. | [src](../../../core/services/cognitive_state_assembly.py#L227) |
| function | `get_cognitive_state_cache_status` | `()` | Return cache status for MC transparency. | [src](../../../core/services/cognitive_state_assembly.py#L242) |
| function | `build_cognitive_state_for_prompt` | `(*, compact=…, force=…)` | Build the [COGNITIVE STATE] section for visible chat prompt injection. | [src](../../../core/services/cognitive_state_assembly.py#L295) |
| function | `build_cognitive_state_injection_surface` | `()` | MC surface showing exactly what was injected into the last visible prompt. | [src](../../../core/services/cognitive_state_assembly.py#L1024) |
| function | `_safe_call` | `(fn)` | Call a DB function, return None on any error. | [src](../../../core/services/cognitive_state_assembly.py#L1044) |
| function | `_safe_json` | `(value)` | Parse JSON string or return dict/list directly. | [src](../../../core/services/cognitive_state_assembly.py#L1053) |
| function | `_appraisal_record` | `(*, kind, state, evidence, allowed_effects, confidence, ttl_minutes=…)` | Structured truth record for optional narrative rendering. | [src](../../../core/services/cognitive_state_assembly.py#L1068) |
| function | `_build_cognitive_core_experiment_state_line` | `(*, compact)` | Build a bounded cognitive-state line for mainline experiment carry. | [src](../../../core/services/cognitive_state_assembly.py#L1093) |
| function | `_safe_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1157) |
| function | `_safe_cognitive_experiment_carry_frame` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1168) |
| function | `_narrativize_embodied_state` | `()` | LLM-narrativize current embodied state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1180) |
| function | `_narrativize_affective_state` | `()` | LLM-narrativize current affective meta state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1237) |
| function | `_narrativize_self_anchor` | `()` | LLM-narrativize the [SELF] ownership line from real personality state. | [src](../../../core/services/cognitive_state_assembly.py#L1290) |
| function | `_narrativize_boundary` | `()` | LLM-narrativize boundary awareness from real runtime context. | [src](../../../core/services/cognitive_state_assembly.py#L1339) |

## `core/services/cognitive_state_narrativizer.py`
_LLM-based narrativizer for cognitive state lines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_narrativizer_llm` | `(system_prompt, user_message)` | Call the compact LLM (heartbeat model) for narrative line generation. | [src](../../../core/services/cognitive_state_narrativizer.py#L44) |
| class | `_CachedNarrative` | `` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L72) |
| function | `_fingerprint` | `(state)` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L85) |
| function | `_generate_in_background` | `(*, line_key, fingerprint, system_prompt, user_message)` | Run the LLM call in a background thread and update cache. | [src](../../../core/services/cognitive_state_narrativizer.py#L90) |
| function | `narrativize_line` | `(*, line_key, state, system_prompt, user_message_builder, fallback=…)` | Return an LLM-narrativized line for this state, or fallback. | [src](../../../core/services/cognitive_state_narrativizer.py#L122) |
| function | `cache_snapshot` | `()` | Expose current cache state for MC observability. | [src](../../../core/services/cognitive_state_narrativizer.py#L199) |

## `core/services/collective_pulse_daemon.py`
_Collective Pulse — what is the air full of right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L43) |
| function | `_collective_dir` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L47) |
| function | `_load` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L51) |
| function | `_save` | `(data)` | — | [src](../../../core/services/collective_pulse_daemon.py#L67) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/collective_pulse_daemon.py#L79) |
| function | `_gather_week_text` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L86) |
| function | `_week_mood_trajectory` | `()` | Average mood over the week, if mood samples are available. | [src](../../../core/services/collective_pulse_daemon.py#L123) |
| function | `_describe_zeitgeist` | `(top_terms, mood_info)` | — | [src](../../../core/services/collective_pulse_daemon.py#L142) |
| function | `_write_weekly_note` | `(pulse)` | — | [src](../../../core/services/collective_pulse_daemon.py#L156) |
| function | `run_pulse` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L192) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/collective_pulse_daemon.py#L233) |
| function | `build_collective_pulse_surface` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L246) |
| function | `_surface_summary` | `(latest)` | — | [src](../../../core/services/collective_pulse_daemon.py#L259) |
| function | `build_collective_pulse_prompt_section` | `()` | Surface the week's zeitgeist while it's still current (within 7 days). | [src](../../../core/services/collective_pulse_daemon.py#L266) |

## `core/services/commit_gate_arbiter.py`
_Pre-eksekverings commit-gate arbitrage — udskilt fra visible_runs (Boy Scout, 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CommitGateOutcome` | `` | Udfald af commit-gate-arbitrage. ``blocked`` → værktøjet må ikke køre; ``soft_warn`` → | [src](../../../core/services/commit_gate_arbiter.py#L21) |
| function | `evaluate_commit_gates` | `(*, name, arguments, user_message, session_id, run_id)` | Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér | [src](../../../core/services/commit_gate_arbiter.py#L30) |

## `core/services/communication_guard.py`
_Communication guard — scanner assistant-output for boundary violations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_hard` | `(trigger)` | Er denne trigger en HÅRD blok (afvis besked før send) eller blød | [src](../../../core/services/communication_guard.py#L143) |
| function | `_load` | `()` | — | [src](../../../core/services/communication_guard.py#L160) |
| function | `_save` | `(triggers)` | — | [src](../../../core/services/communication_guard.py#L172) |
| function | `add_trigger` | `(phrase, *, kind=…, reason=…, ttl_turns=…, ttl_hours=…)` | Tilfoj en triggerfrase til guarden. | [src](../../../core/services/communication_guard.py#L177) |
| function | `remove_trigger` | `(phrase)` | Fjern en triggerfrase. Returner True hvis den blev fjernet. | [src](../../../core/services/communication_guard.py#L224) |
| function | `scan` | `(text)` | Skan en tekst for triggerfraser. | [src](../../../core/services/communication_guard.py#L235) |
| function | `_trigger_active` | `(t, now)` | Er en trigger aktiv lige nu (permanent, eller TTL ikke udløbet)? | [src](../../../core/services/communication_guard.py#L282) |
| function | `enforce_outgoing` | `(text)` | Hård-gate for udga°ende assistant-tekst — kaldes FØR afsendelse. | [src](../../../core/services/communication_guard.py#L299) |
| function | `record_breach` | `(channel, removed, *, original=…)` | Log en boundary-breach (hård frase fanget ved kanal-dispatch). | [src](../../../core/services/communication_guard.py#L350) |
| function | `guard_channel_text` | `(text, channel)` | Convenience for kanal-dispatch: scrub hård afslutnings-fraser fra | [src](../../../core/services/communication_guard.py#L374) |
| function | `_active_hard_phrases` | `(now)` | — | [src](../../../core/services/communication_guard.py#L394) |
| function | `scrub_outgoing` | `(text)` | Kanal-backstop: fjern den SÆTNING/linje der indeholder en hård | [src](../../../core/services/communication_guard.py#L402) |
| function | `prompt_section` | `()` | Bygger en høj-salient påmindelse til system-prompten med de aktive | [src](../../../core/services/communication_guard.py#L433) |
| function | `consume_turn` | `()` | Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver | [src](../../../core/services/communication_guard.py#L467) |
| function | `cleanup_expired` | `()` | Rens udloebne TTL-triggers og triggers med ttl_turns <= 0. | [src](../../../core/services/communication_guard.py#L485) |
| function | `_safe_parse_iso` | `(s, now)` | — | [src](../../../core/services/communication_guard.py#L510) |
| function | `list_triggers` | `()` | Returner alle aktive triggers. | [src](../../../core/services/communication_guard.py#L519) |
| function | `active_count` | `()` | Antal aktive triggerfraser (permanente + ikke-udloebne TTL). | [src](../../../core/services/communication_guard.py#L524) |

## `core/services/communication_guard_daemon.py`
_Communication guard daemon — vedligeholder TTL-rydning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_communication_guard_daemon` | `()` | Daemon tick: cleanup expired TTL triggers + log active count. | [src](../../../core/services/communication_guard_daemon.py#L18) |

## `core/services/compass_engine.py`
_Compass Engine — weekly strategic bearing based on open loops and priorities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_update_compass` | `(*, open_loops=…, recent_decisions=…)` | Update compass if >3 days since last update. | [src](../../../core/services/compass_engine.py#L21) |
| function | `build_compass_surface` | `()` | — | [src](../../../core/services/compass_engine.py#L65) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/compass_engine.py#L74) |

## `core/services/completion_satisfaction.py`
_Completion Satisfaction — "det er nok, jeg er tilfreds."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_completion_satisfaction` | `(*, task_outcomes, repetition_on_same_topic=…, user_mood=…)` | — | [src](../../../core/services/completion_satisfaction.py#L8) |
| function | `build_completion_satisfaction_surface` | `()` | — | [src](../../../core/services/completion_satisfaction.py#L45) |
| function | `_publish_completion_satisfaction_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/completion_satisfaction.py#L48) |

## `core/services/composite_tools.py`
_Composite tools — safe self-extension through composition only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose` | `(*, name, description, input_schema, steps, created_by=…)` | Validate and store a proposal. Raises ValueError on invalid input. | [src](../../../core/services/composite_tools.py#L44) |
| function | `approve` | `(name, *, approved_by=…)` | — | [src](../../../core/services/composite_tools.py#L115) |
| function | `revoke` | `(name)` | — | [src](../../../core/services/composite_tools.py#L128) |
| function | `delete` | `(name)` | — | [src](../../../core/services/composite_tools.py#L138) |
| function | `get` | `(name)` | — | [src](../../../core/services/composite_tools.py#L148) |
| function | `list_available` | `(*, status=…)` | — | [src](../../../core/services/composite_tools.py#L152) |
| function | `invoke` | `(name, args)` | Execute an approved composite. Returns {status, steps, result}. | [src](../../../core/services/composite_tools.py#L156) |
| function | `get_stats` | `()` | — | [src](../../../core/services/composite_tools.py#L224) |
| function | `_substitute` | `(value, context)` | — | [src](../../../core/services/composite_tools.py#L237) |
| function | `_resolve_string` | `(s, context)` | Resolve {{...}} templates. | [src](../../../core/services/composite_tools.py#L247) |
| function | `_lookup` | `(path, context)` | — | [src](../../../core/services/composite_tools.py#L267) |

## `core/services/computer_use_policy.py`
_Computer-use-politik (§4.7) — per-bruger on/off for operator/computer-tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_computer_use_tool` | `(name)` | — | [src](../../../core/services/computer_use_policy.py#L25) |
| function | `_load` | `()` | — | [src](../../../core/services/computer_use_policy.py#L30) |
| function | `computer_use_enabled` | `(user_id)` | Default TIL — kun eksplicit fravalg slår fra. | [src](../../../core/services/computer_use_policy.py#L37) |
| function | `set_computer_use` | `(user_id, enabled)` | — | [src](../../../core/services/computer_use_policy.py#L42) |

