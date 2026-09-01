# `core.services.06` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_surgery.py`
_Self-Surgery Kit — så Jarvis kan operere på sig selv uden at skære i blinde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_surgery.py#L37) |
| function | `_now` | `()` | — | [src](../../../core/services/central_surgery.py#L61) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_surgery.py#L65) |
| function | `_dotted` | `(target)` | — | [src](../../../core/services/central_surgery.py#L73) |
| function | `_blast_count` | `(target)` | Antal filer i repoet der refererer target-modulet (import-graf-proxy). Self-safe. | [src](../../../core/services/central_surgery.py#L80) |
| function | `assess_risk` | `(target, *, kind=…)` | Blast-radius FØR nogen rører noget: hvor mange filer/områder + rører det selvbilledet + | [src](../../../core/services/central_surgery.py#L98) |
| function | `propose_surgery` | `(target, *, kind=…, rationale=…)` | Registrér et kirurgisk forslag + kør risikovurdering. INGEN kode-ændring. Self-safe. | [src](../../../core/services/central_surgery.py#L129) |
| function | `_set_status` | `(pid, status, note=…)` | — | [src](../../../core/services/central_surgery.py#L149) |
| function | `_get` | `(pid)` | — | [src](../../../core/services/central_surgery.py#L164) |
| function | `simulate` | `(pid)` | Projicér indgrebets effekt (som The Construct): dækning + blast. Ingen mutation. Self-safe. | [src](../../../core/services/central_surgery.py#L174) |
| function | `_is_tested` | `(target)` | — | [src](../../../core/services/central_surgery.py#L186) |
| function | `verify` | `(pid)` | Kør SECURITY-mutation_gate: frossen kerne → blocked, ellers verified. Self-safe. | [src](../../../core/services/central_surgery.py#L197) |
| function | `escalate` | `(pid)` | Send forslaget til Bjørn (owner-godkendelse). Kun et verificeret forslag kan eskaleres. | [src](../../../core/services/central_surgery.py#L211) |
| function | `list_proposals` | `(*, limit=…)` | — | [src](../../../core/services/central_surgery.py#L224) |
| function | `snapshot_file` | `(target)` | Sikkerhedsnet: fang en fils NUVÆRENDE indhold durabelt FØR et indgreb (undo uden git). | [src](../../../core/services/central_surgery.py#L234) |
| function | `rollback` | `(snapshot_id)` | OWNER-handling: gendan en fil atomisk fra et tidligere snapshot (undo uden git). Nægter | [src](../../../core/services/central_surgery.py#L256) |
| function | `build_surgery_surface` | `()` | Owner/self-view: åbne forslag + felt-linje. Self-safe. | [src](../../../core/services/central_surgery.py#L281) |

## `core/services/central_switches.py`
_Live-kontrol for Centralen (§11). On/off pr. nerve/cluster via shared_cache-flag._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(scope, name)` | — | [src](../../../core/services/central_switches.py#L14) |
| function | `set_enabled` | `(scope, name, enabled, *, klass=…)` | Slå en nerve/cluster on/off live. Sikkerheds-nerve + enabled=False afvises. | [src](../../../core/services/central_switches.py#L18) |
| function | `is_enabled` | `(scope, name)` | — | [src](../../../core/services/central_switches.py#L28) |
| function | `set_cluster_enabled` | `(cluster, enabled)` | Slå et HELT cluster on/off live (Jarvis' idé). Sikkerheds-cluster + enabled=False | [src](../../../core/services/central_switches.py#L41) |
| function | `is_cluster_enabled` | `(cluster)` | True medmindre clusteret er EKSPLICIT slået fra. Default ON. | [src](../../../core/services/central_switches.py#L57) |
| class | `CircuitBreaker` | `` | Tæl fejl pr. nerve; isolér efter `threshold` på stribe. Nulstil ved succes. | [src](../../../core/services/central_switches.py#L62) |
| method | `CircuitBreaker.__init__` | `(self, threshold=…)` | — | [src](../../../core/services/central_switches.py#L65) |
| method | `CircuitBreaker.record` | `(self, nerve, ok)` | Returnér True hvis kredsen NETOP blev (eller fortsat er) åben/isoleret. | [src](../../../core/services/central_switches.py#L70) |
| method | `CircuitBreaker.is_open` | `(self, nerve)` | — | [src](../../../core/services/central_switches.py#L79) |
| method | `CircuitBreaker.open_nerves` | `(self)` | Nerver hvis kreds NETOP er åben/isoleret (til Centralens self-helbreds-check). | [src](../../../core/services/central_switches.py#L83) |
| method | `CircuitBreaker.reset` | `(self, nerve)` | — | [src](../../../core/services/central_switches.py#L90) |
| function | `drift_flag` | `(name, value, *, baseline, tol)` | Flag-on-change-skelet (§7): returnér en flag-dict hvis |value-baseline| > tol, | [src](../../../core/services/central_switches.py#L95) |

## `core/services/central_terminal.py`
_central_terminal — en command-line ind i Den Intelligente Central (owner-terminal)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_q` | `(action, **kw)` | — | [src](../../../core/services/central_terminal.py#L35) |
| function | `_fmt_envelope` | `(env)` | central_query-envelope → terminal-linjer (kompakt, læsbar). | [src](../../../core/services/central_terminal.py#L40) |
| function | `run_command` | `(line)` | Parse + udfør én terminal-kommando. Returnerer {ok, command, lines}. Self-safe. | [src](../../../core/services/central_terminal.py#L76) |

## `core/services/central_timeseries.py`
_core/services/central_timeseries.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_timeseries.py#L46) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_timeseries.py#L55) |
| function | `_durability_on` | `()` | Hot-path-durabilitet (auto-restore/persist i record/recent) er AKTIV i produktion, men | [src](../../../core/services/central_timeseries.py#L63) |
| class | `Sample` | `` | — | [src](../../../core/services/central_timeseries.py#L71) |
| function | `record` | `(cluster, nerve, value=…, *, meta=…)` | Tilføj ét sample til (cluster, nerve)'s serie. Best-effort, kaster aldrig. | [src](../../../core/services/central_timeseries.py#L77) |
| function | `recent` | `(cluster, nerve, *, limit=…)` | Læs de seneste samples for én nerve (nyeste sidst). READ-ONLY. | [src](../../../core/services/central_timeseries.py#L108) |
| function | `nerves` | `()` | Alle (cluster, nerve)-nøgler der har mindst ét sample. READ-ONLY. | [src](../../../core/services/central_timeseries.py#L125) |
| function | `stats` | `()` | Samlet overblik: antal nerver + samples pr. nerve. READ-ONLY, til observabilitet. | [src](../../../core/services/central_timeseries.py#L134) |
| function | `snapshot` | `(*, recent=…)` | Kompakt cross-proces-snapshot: pr. nerve seneste værdi(er) + count. Read-only, self-safe. | [src](../../../core/services/central_timeseries.py#L149) |
| function | `persist_snapshot` | `()` | Flush de bounded per-nerve-serier til durabel kv, så nervesystemet OVERLEVER genstart. | [src](../../../core/services/central_timeseries.py#L173) |
| function | `_load_durable` | `()` | Genindlæs det durable snapshot ind i _series (merge-append). Self-safe. | [src](../../../core/services/central_timeseries.py#L191) |
| function | `_maybe_restore` | `()` | Restore-on-first-access (dobbelt-tjekket): genindlæs durabelt snapshot ÉN gang efter boot. | [src](../../../core/services/central_timeseries.py#L214) |
| function | `_maybe_persist` | `()` | Throttlet flush i baggrundstråd (hot-path stalles ALDRIG af DB-skrivning). | [src](../../../core/services/central_timeseries.py#L228) |
| function | `_reset_for_tests` | `()` | Testhjælper — ryd al state. Ikke til produktionsbrug. | [src](../../../core/services/central_timeseries.py#L241) |

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
| function | `_is_vague_theme` | `(theme)` | True hvis temaet er tomt, for kort, eller et rent fyldeord. Ren, self-safe. | [src](../../../core/services/central_trainman.py#L47) |
| function | `_recent_dreams` | `(limit=…)` | Seneste distillerede/konsoliderede drømme (id, tema, timestamp). Self-safe. | [src](../../../core/services/central_trainman.py#L57) |
| function | `_existing_dream_memories` | `(limit=…)` | Trainmans allerede-vævede erindringer i private_brain (til idempotens + tema-forbindelser). | [src](../../../core/services/central_trainman.py#L66) |
| function | `_dream_id_of` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L80) |
| function | `_dream_theme` | `(dream)` | Øverste tema for en drøm. Konsoliderings-drømme bærer en themes-liste; distillat en top_theme. | [src](../../../core/services/central_trainman.py#L84) |
| function | `_dream_timestamp` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L95) |
| function | `_sig_of` | `(rec)` | Afkod source_signals-JSON på en vævet erindring (dream_id, theme, connected_to …). Self-safe. | [src](../../../core/services/central_trainman.py#L99) |
| function | `_interlanguage` | `(theme)` | Byg en interlanguage-notation for temaet. Prøv lexicon (bundne termer); ellers spec-stil | [src](../../../core/services/central_trainman.py#L109) |
| function | `_emotional_tone` | `(theme)` | Simpel deterministisk klang ud fra tema-ord. Ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L126) |
| function | `_weave_narrative` | `(*, theme, dream)` | Væv drømmen til en 1.-persons erindrings-historie. Ren tekst, ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L138) |
| function | `_connected_ids` | `(theme, existing, *, limit=…)` | record_id'er for tidligere vævede erindringer om SAMME tema (drømme-kontinuitet). Self-safe. | [src](../../../core/services/central_trainman.py#L147) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_trainman.py#L160) |
| function | `_write_memory` | `(*, dream_id, theme, narrative, interlanguage, connected_to, emotional_tone, now)` | Skriv den vævede erindring til private_brain (source='dream'). Returnerer record_id ('' ved fejl). | [src](../../../core/services/central_trainman.py#L170) |
| function | `_signal_agenda` | `(*, theme, count, dream_id)` | 3+ drømme om samme tema på 7 dage → lav-prioritets initiativ til Agendaen. Self-safe. | [src](../../../core/services/central_trainman.py#L204) |
| function | `transform_dreams` | `(*, trigger=…, last_visible_at=…)` | Væv nye drømme til narrative erindringer i private_brain (source='dream'). | [src](../../../core/services/central_trainman.py#L225) |
| function | `_count_theme_recent` | `(theme, memories, *, now)` | Antal vævede erindringer om `theme` indenfor RECURRENCE_WINDOW_DAYS. Self-safe. | [src](../../../core/services/central_trainman.py#L292) |
| function | `_theme_distribution` | `(memories, *, now, days=…)` | Tema→antal over de sidste `days` dage. Self-safe. | [src](../../../core/services/central_trainman.py#L309) |
| function | `_last_reflection_at` | `(existing)` | — | [src](../../../core/services/central_trainman.py#L330) |
| function | `_maybe_reflect` | `(*, existing, now)` | Én gang pr. ~døgn: skriv en metakognitiv erindring om de sidste 7 dages tema-fordeling. | [src](../../../core/services/central_trainman.py#L337) |
| function | `_maybe_silence_note` | `(*, existing, now)` | Temaer der før var tilbagevendende men har været tavse i 14 dage → nysgerrigheds-note. | [src](../../../core/services/central_trainman.py#L370) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_trainman.py#L422) |
| function | `build_trainman_surface` | `()` | Seneste vævede erindringer + tema-fordeling for Central-CLI. READ-ONLY. Self-safe. | [src](../../../core/services/central_trainman.py#L439) |
| function | `record_trainman` | `(*, trigger=…, last_visible_at=…)` | Cadence: væv nye drømme til erindringer. Self-safe — kaster aldrig. | [src](../../../core/services/central_trainman.py#L474) |

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
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L104) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L109) |
| function | `_event_is_recent` | `(r, *, max_age_min=…)` | True hvis event-record er nyere end max_age_min. Fail-open ved ukendt/uparsbar | [src](../../../core/services/central_watch.py#L324) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen NYLIGT. Cross-proces. | [src](../../../core/services/central_watch.py#L339) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L353) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, exhausted) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L361) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra NYLIGE tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L384) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L402) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L411) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L425) |

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
| function | `create_chat_session` | `(*, title=…, workspace_kind=…, workspace_root=…)` | — | [src](../../../core/services/chat_sessions.py#L51) |
| function | `get_or_create_named_session` | `(session_id, title)` | Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny). | [src](../../../core/services/chat_sessions.py#L83) |
| function | `most_recent_session_id` | `()` | Lightweight: session_id of the most recently updated session. | [src](../../../core/services/chat_sessions.py#L110) |
| function | `list_chat_sessions` | `(*, user_id=…)` | List chat sessions, optionally filtered to one user. | [src](../../../core/services/chat_sessions.py#L127) |
| function | `_make_snippet` | `(content, query, width=…)` | Byg et kort uddrag centreret om første match (case-insensitive). | [src](../../../core/services/chat_sessions.py#L205) |
| function | `search_chat_sessions` | `(query, *, user_id=…, limit=…)` | Søg sessioner på titel ELLER besked-indhold (user/assistant). | [src](../../../core/services/chat_sessions.py#L220) |
| function | `session_version` | `(session_id)` | Billig nøgle der ændrer sig præcis når sessionens indhold gør. | [src](../../../core/services/chat_sessions.py#L297) |
| function | `get_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L335) |
| function | `set_session_workspace` | `(session_id, *, kind, root)` | Bind (eller skift) en sessions Code-mode workspace. | [src](../../../core/services/chat_sessions.py#L387) |
| function | `append_chat_message` | `(*, session_id, role, content, created_at=…, tool_name=…, tool_arguments=…, user_id=…, workspace_name=…, reasoning_content=…, content_json=…)` | — | [src](../../../core/services/chat_sessions.py#L402) |
| function | `_recent_duplicate_user_message` | `(session_id, content, now_ts)` | Returnér den seneste besked-række HVIS den er en identisk brugerbesked inden | [src](../../../core/services/chat_sessions.py#L561) |
| function | `_infer_tool_name_from_content` | `(content)` | — | [src](../../../core/services/chat_sessions.py#L596) |
| function | `recent_chat_session_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L603) |
| function | `chat_session_messages_since_last_compact` | `(session_id, *, max_total=…)` | Hent ALT efter seneste compact_marker (eller hele session hvis ingen). | [src](../../../core/services/chat_sessions.py#L630) |
| function | `recent_chat_session_messages_by_user_turns` | `(session_id, *, user_turns=…, max_total=…)` | Hent de seneste N *user-turns* og alt der hører til dem. | [src](../../../core/services/chat_sessions.py#L692) |
| function | `_ensure_compact_marker_git_sha_column` | `()` | Add git_sha column to chat_messages if it doesn't exist (idempotent migration). | [src](../../../core/services/chat_sessions.py#L768) |
| function | `store_compact_marker` | `(session_id, summary_text, git_sha=…)` | Store a compact marker for the session. Returns the marker message_id. | [src](../../../core/services/chat_sessions.py#L780) |
| function | `get_compact_marker_with_sha` | `(session_id)` | Return (summary, git_sha) of the most recent compact marker, or (None, None). | [src](../../../core/services/chat_sessions.py#L811) |
| function | `get_compact_marker` | `(session_id)` | Return the most recent compact marker summary for the session, or None. | [src](../../../core/services/chat_sessions.py#L835) |
| function | `recent_chat_tool_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L853) |
| function | `rename_chat_session` | `(session_id, *, title)` | — | [src](../../../core/services/chat_sessions.py#L878) |
| function | `delete_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L892) |
| function | `_session_summary` | `(row)` | — | [src](../../../core/services/chat_sessions.py#L902) |
| function | `_normalize_title` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L914) |
| function | `_preview_text` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L921) |
| function | `_time_label` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L928) |
| function | `parse_channel_from_session_title` | `(title)` | Parse channel type and detail from a session title. | [src](../../../core/services/chat_sessions.py#L936) |
| function | `get_session_owner` | `(session_id)` | Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel. | [src](../../../core/services/chat_sessions.py#L966) |

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
| function | `_slot_status` | `(slot, state, now)` | Single derived status string for a slot, most-severe-wins. | [src](../../../core/services/cheap_lane_balancer.py#L369) |
| function | `_flag_adaptive_quota` | `()` | Learn real daily ceilings from genuine daily-quota 429s. Default OFF. | [src](../../../core/services/cheap_lane_balancer.py#L427) |
| function | `_maybe_daily_reset` | `(state, now)` | Reset per-day adaptive-quota learning at the UTC day boundary. | [src](../../../core/services/cheap_lane_balancer.py#L440) |
| function | `_register_failure` | `(state, error_kind, *, retry_after_s=…, now, error_message=…, observed_used=…, config_daily=…)` | Update state after a failed call. | [src](../../../core/services/cheap_lane_balancer.py#L455) |
| function | `_register_success` | `(state, now)` | Update state after a successful call. | [src](../../../core/services/cheap_lane_balancer.py#L537) |
| function | `_is_dns_or_connection_error` | `(error_kind, exc=…)` | True if error indicates network-level (provider-wide) issue, not slot-specific. | [src](../../../core/services/cheap_lane_balancer.py#L554) |
| function | `_register_provider_wide_failure` | `(states, pool, provider, now, *, reason, cooldown_s=…)` | Apply cooldown to ALL slots from `provider`. Returns number of slots affected. | [src](../../../core/services/cheap_lane_balancer.py#L572) |
| function | `_select_slot` | `(states, pool, now)` | Pick a slot via weighted-random; returns None if all blocked. | [src](../../../core/services/cheap_lane_balancer.py#L615) |
| function | `_central_route_shadow` | `()` | Kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_lane_balancer.py#L663) |
| function | `_central_route_live` | `()` | Brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_lane_balancer.py#L672) |
| function | `_flag_multiprofile` | `()` | Byg én slot pr. (provider, klar auth-profil) i stedet for kun entry-profilen. | [src](../../../core/services/cheap_lane_balancer.py#L681) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_lane_balancer.py#L693) |
| function | `_central_route_slot` | `(eligible_pool, tried_slot_ids)` | Spørg central_route om lane='cheap'-pick og map til en EGNET (untried) slot i | [src](../../../core/services/cheap_lane_balancer.py#L710) |
| function | `_maybe_central_route_slot` | `(weighted_slot, eligible_pool, tried_slot_ids)` | Hook før slot bruges: shadow-compare (OFF → no-op) + live-apply. Aldrig-tør | [src](../../../core/services/cheap_lane_balancer.py#L731) |
| function | `_call_provider_chat` | `(*, provider, model, auth_profile, base_url, message)` | Wrapper around cheap_provider_runtime._execute_provider_chat. | [src](../../../core/services/cheap_lane_balancer.py#L752) |
| function | `_append_recent_call` | `(slot_id, daemon, status, latency_ms, *, error=…)` | — | [src](../../../core/services/cheap_lane_balancer.py#L777) |
| function | `recent_calls` | `()` | Returns ring-buffer of last 75 calls (newest first). | [src](../../../core/services/cheap_lane_balancer.py#L795) |
| function | `call_balanced` | `(*, prompt, daemon_name=…, max_retries=…)` | Pick a slot via weighted-random; execute; on failure retry next slot. | [src](../../../core/services/cheap_lane_balancer.py#L800) |
| function | `build_slot_pool` | `()` | Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS. | [src](../../../core/services/cheap_lane_balancer.py#L1037) |
| function | `reset_slot` | `(slot_id)` | Clear breaker, cooldown, and consecutive-failure streak for a slot. | [src](../../../core/services/cheap_lane_balancer.py#L1165) |
| function | `disable_slot` | `(slot_id)` | Force a slot's weight to 0 until enable_slot is called. | [src](../../../core/services/cheap_lane_balancer.py#L1177) |
| function | `enable_slot` | `(slot_id)` | Re-enable a manually-disabled slot. | [src](../../../core/services/cheap_lane_balancer.py#L1186) |
| function | `refresh_pool` | `()` | Re-build the slot pool from provider_router.json. Returns current size. | [src](../../../core/services/cheap_lane_balancer.py#L1195) |
| function | `_is_enabled` | `()` | Check RuntimeSettings.daemon_balancer_enabled. Default True. | [src](../../../core/services/cheap_lane_balancer.py#L1206) |
| function | `balancer_snapshot` | `()` | Return full state surface for Mission Control telemetry. | [src](../../../core/services/cheap_lane_balancer.py#L1215) |

## `core/services/cheap_lane_failure_policy.py`
_Hvor længe skal et cheap-lane-slot i karantæne? Afhænger af HVORFOR det fejlede._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify` | `(error_kind, message=…)` | ``'permanent'`` | ``'depleted'`` | ``'transient'``. | [src](../../../core/services/cheap_lane_failure_policy.py#L79) |
| function | `quarantine_seconds` | `(error_kind, *, retry_after_s=…, message=…)` | Karantæne-længde, eller ``0`` når slottet skal følge den normale breaker-trappe. | [src](../../../core/services/cheap_lane_failure_policy.py#L102) |

## `core/services/cheap_lane_floor.py`
_Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `floor_targets` | `()` | Bund-kæden, config-overstyrbar. Self-safe → default ved fejl. | [src](../../../core/services/cheap_lane_floor.py#L42) |
| function | `floor_result` | `(*, lane, reason, provider=…, model=…, text=…, status=…, extra=…)` | Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund. | [src](../../../core/services/cheap_lane_floor.py#L56) |
| function | `_execute_floor_target` | `(*, provider, model, message, lane)` | Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles | [src](../../../core/services/cheap_lane_floor.py#L70) |
| function | `attempt_floor` | `(*, message, lane, reason)` | Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT | [src](../../../core/services/cheap_lane_floor.py#L90) |

## `core/services/cheap_lane_selfheal.py`
_cheap_lane_selfheal — cheap-lane maa ALDRIG stale eller doe (Bjoern 16.jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_stale_targets` | `(limit)` | (provider, model) der skal re-probes. To kilder: | [src](../../../core/services/cheap_lane_selfheal.py#L32) |
| function | `reprobe` | `(provider, model)` | Minimalt sundheds-probe. Healer state ved succes, saetter frisk cooldown ved fejl. | [src](../../../core/services/cheap_lane_selfheal.py#L93) |
| function | `run_selfheal` | `(*, max_probes=…)` | Re-probe op til max_probes fastlaaste providere. Returnér {healed, still_down}. | [src](../../../core/services/cheap_lane_selfheal.py#L126) |

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

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L24) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L625) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L626) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L643) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L653) |
| function | `provider_cost_class` | `(provider)` | 'free' (default) eller 'paid'. Betalte providers (copilot-premium) må KUN | [src](../../../core/services/cheap_provider_runtime_adapters.py#L657) |
| function | `is_routable_provider` | `(provider)` | False = provideren må IKKE vælges i normal routing (kun evt. som nød-bund). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L664) |
| function | `_huggingface_runtime_token` | `()` | Delt owner-token for HuggingFace Router — læses fra runtime.json | [src](../../../core/services/cheap_provider_runtime_adapters.py#L672) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L690) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L736) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L810) |
| function | `_resolve_egress_proxy` | `(*, provider, auth_profile)` | Task 8b: resolve the egress proxy URL for a (provider, auth_profile) slot. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L833) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L852) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…, extra_body=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L937) |
| function | `deepseek_request_for_thinking_mode` | `(model, thinking_mode)` | Map composer thinking_mode -> (model, extra_body) WITHOUT the deprecated aliases | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1137) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Backward-compat: return only the model (never the deprecated alias). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1158) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1167) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1222) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1249) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1276) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1301) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1318) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1342) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1352) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1392) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1424) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message, provider=…)` | Call an Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1492) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1564) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1595) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…, proxy=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1643) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…, proxy=…, source_address=…, nat64_sni=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1706) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1796) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1824) |
| function | `_notify_checkin_required` | `(provider)` | Læg en nudge i Jarvis' awareness når en checkin-gated provider (FreeTheAi) er låst, | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1841) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1863) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1887) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1908) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1928) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1972) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1984) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L2006) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L2017) |

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
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L315) |
| function | `_central_route_shadow` | `()` | Task 9: kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_provider_runtime_selection.py#L319) |
| function | `_central_route_live` | `()` | Task 9: brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_provider_runtime_selection.py#L328) |
| function | `_flag_multiprofile` | `()` | Task 6: yield én kandidat pr. (provider, klar auth-profil) i stedet for kun | [src](../../../core/services/cheap_provider_runtime_selection.py#L337) |
| function | `_flag_profile_roundrobin` | `()` | A (2026-07-24): when multiprofile is on AND a provider has >1 ready auth | [src](../../../core/services/cheap_provider_runtime_selection.py#L348) |
| function | `_roundrobin_profiles` | `(provider, profiles)` | Rotate ``profiles`` by a per-provider counter (PEEK — does not advance) so | [src](../../../core/services/cheap_provider_runtime_selection.py#L367) |
| function | `_advance_profile_rr` | `(provider)` | Advance the round-robin counter for ``provider`` by one — call exactly once | [src](../../../core/services/cheap_provider_runtime_selection.py#L381) |
| function | `_resolve_proxy` | `(egress, endpoints=…)` | Task 8b: map an egress ('home'|'vpn'|'he6') to its proxy endpoint URL. | [src](../../../core/services/cheap_provider_runtime_selection.py#L387) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_provider_runtime_selection.py#L409) |
| function | `_maybe_shadow_compare` | `(old_target)` | Shadow-hook før select returnerer. OFF → no-op, byte-identisk. | [src](../../../core/services/cheap_provider_runtime_selection.py#L426) |
| function | `_maybe_central_route_live` | `(old_target, candidates, kind, skip_providers)` | Task 9 live: når central_route_live er ON henter selection sit pick fra det | [src](../../../core/services/cheap_provider_runtime_selection.py#L438) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L478) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…, lane=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L579) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L738) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L817) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L858) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L907) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1055) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1112) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1129) |
| function | `_record_provider_success` | `(*, provider, model, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1170) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1221) |
| function | `_decode_state_metadata` | `(state)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1287) |
| function | `_rolling_average` | `(*, current_avg, current_count, new_value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1298) |
| function | `_smoke_quality_score` | `(*, expected, actual)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1304) |
| function | `_normalize_probe_text` | `(value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1314) |

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
| function | `_fabricated_tool_result_footnote` | `(text)` | Kør fabrikations-gaten og gør verdiktet SYNLIGT — uden at dræbe runden. | [src](../../../core/services/claim_scanner.py#L502) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L542) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L550) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L580) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L652) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L720) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L747) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

## `core/services/client_turn_absorb.py`
_client_turn_absorb.py — fyr den fulde post-tur-hjerne for en KLIENT-drevet tur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_do_absorb` | `(run, assistant_response, user_id)` | Synkron post-process-firing (testbar). Kører i user_context så memory/workspace | [src](../../../core/services/client_turn_absorb.py#L23) |
| function | `persist_client_turn` | `(*, session_id, user_message, assistant_response, user_id=…)` | Fase C1 (delte sessioner): persistér en KLIENT-drevet turs beskeder til den DELTE | [src](../../../core/services/client_turn_absorb.py#L45) |
| function | `absorb_client_turn` | `(*, session_id, run_id, user_message, assistant_response, provider=…, model=…, user_id=…, lane=…)` | Konstruér en VisibleRun fra klient-data og fyr post-process i en baggrundstråd | [src](../../../core/services/client_turn_absorb.py#L69) |

## `core/services/client_turn_live.py`
_client_turn_live.py — cross-device live-broadcast for en KLIENT-drevet tur (C2b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `begin_live_turn` | `(*, session_id, run_id, user_message=…, provider=…, model=…, user_id=…)` | Registrér turen som det aktive visible run + åbn run_follow (kun for ægte | [src](../../../core/services/client_turn_live.py#L23) |
| function | `end_live_turn` | `(*, session_id, run_id=…)` | Ryd active-run (kun hvis det stadig er DETTE run — undgå at rydde en efterfølger) | [src](../../../core/services/client_turn_live.py#L66) |

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
| function | `_somatic_signals` | `(snapshot)` | Somatic member gate-signal: machine pressure (drain + energy band). | [src](../../../core/services/cluster_daemon.py#L308) |
| function | `_somatic_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L320) |
| function | `_experienced_time_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L329) |
| function | `_experienced_time_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L346) |
| function | `_absence_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L355) |
| function | `_absence_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L366) |
| function | `_collect_somatic_snapshot` | `()` | Gather the somatic family's shared snapshot. | [src](../../../core/services/cluster_daemon.py#L374) |
| function | `_somatic_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L435) |
| function | `_experienced_time_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L440) |
| function | `_absence_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L449) |
| function | `build_somatic_family` | `()` | Construct the somatic/embodiment cluster-daemon (family #1). | [src](../../../core/services/cluster_daemon.py#L463) |
| function | `somatic_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L498) |
| function | `_run_somatic_members` | `(snap, result)` | Run every somatic member UNCONDITIONALLY (no generative gate — they are | [src](../../../core/services/cluster_daemon.py#L505) |
| function | `tick_cluster_somatic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the somatic cluster-daemon family (#1). | [src](../../../core/services/cluster_daemon.py#L522) |
| function | `_iv_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (mirrors the daemons' | [src](../../../core/services/cluster_daemon.py#L601) |
| function | `_collect_innervoice_snapshot` | `()` | Gather the inner-voice family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L609) |
| function | `_iv_thought_stream_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L696) |
| function | `_iv_reflection_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L704) |
| function | `_iv_meta_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L712) |
| function | `_iv_irony_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L720) |
| function | `_iv_wonder_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L727) |
| function | `_iv_drift_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L737) |
| function | `_iv_thought_stream_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L748) |
| function | `_iv_reflection_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L757) |
| function | `_iv_meta_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L771) |
| function | `_iv_irony_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L789) |
| function | `_iv_wonder_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L794) |
| function | `_iv_drift_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L803) |
| function | `_iv_surface_observe` | `(builder_path, keys)` | — | [src](../../../core/services/cluster_daemon.py#L811) |
| function | `build_innervoice_family` | `()` | Construct the inner-voice cluster-daemon (family #2), LIVE. | [src](../../../core/services/cluster_daemon.py#L823) |
| function | `innervoice_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L899) |
| function | `tick_cluster_innervoice` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the inner-voice cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L906) |
| function | `_affect_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (no hash randomisation). | [src](../../../core/services/cluster_daemon.py#L980) |
| function | `_collect_affect_snapshot` | `()` | Gather the affect family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L987) |
| function | `_affect_surprise_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1071) |
| function | `_affect_conflict_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1078) |
| function | `_affect_desire_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1087) |
| function | `_affect_surprise_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1099) |
| function | `_affect_conflict_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1108) |
| function | `_affect_desire_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1113) |
| function | `build_affect_family` | `()` | Construct the affect cluster-daemon (family #3), LIVE. | [src](../../../core/services/cluster_daemon.py#L1118) |
| function | `affect_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1166) |
| function | `_run_affect_nonllm_members` | `(snap, result)` | Run the NON-LLM affect members UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon.py#L1173) |
| function | `tick_cluster_affect` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the affect cluster-daemon family (#3). | [src](../../../core/services/cluster_daemon.py#L1199) |
| function | `_narrative_no_signals` | `(_snap)` | No gate signals — this family is TIME-BASED, not event-gated. Declaring | [src](../../../core/services/cluster_daemon.py#L1275) |
| function | `_narrative_development_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1284) |
| function | `_narrative_summary_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1289) |
| function | `_narrative_identity_drift_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1294) |
| function | `_narrative_identity_sketch_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1299) |
| function | `_narrative_consolidation_judge_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1304) |
| function | `build_narrative_family` | `()` | Construct the narrative/self-history cluster-daemon (family #4), LIVE. | [src](../../../core/services/cluster_daemon.py#L1309) |
| function | `narrative_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1376) |
| function | `_run_narrative_members` | `(snap, result)` | Run every narrative member UNCONDITIONALLY (no event-gate — time-based), | [src](../../../core/services/cluster_daemon.py#L1383) |
| function | `tick_cluster_narrative` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the narrative cluster-daemon family (#4). | [src](../../../core/services/cluster_daemon.py#L1402) |
| function | `_collect_cognition_snapshot` | `()` | Gather the cognition family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L1482) |
| function | `_cog_pattern_cf_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1504) |
| function | `_cog_pattern_cf_observe` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1511) |
| function | `_cog_pattern_cf_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1515) |
| function | `build_cognition_family` | `()` | Construct the cognition cluster-daemon (family #5), LIVE. | [src](../../../core/services/cluster_daemon.py#L1520) |
| function | `cognition_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1546) |
| function | `_cog_causal_inference_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1556) |
| function | `_cog_active_sensing_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1561) |
| function | `_cog_dream_insight_live` | `(_snap)` | dream_insight is signal-driven (not a timer): gather the latest dream- | [src](../../../core/services/cluster_daemon.py#L1566) |
| function | `_run_cognition_nonllm_members` | `(snap, result)` | Run the NON-LLM cognition members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon.py#L1592) |
| function | `tick_cluster_cognition` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the cognition cluster-daemon family (#5). | [src](../../../core/services/cluster_daemon.py#L1608) |

## `core/services/cluster_daemon_families.py`
_Cluster-daemon FAMILIES — the second file of consolidated nerve-families._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_collect_memory_snapshot` | `()` | Gather the memory family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L81) |
| function | `_mem_council_signals` | `(snap)` | council_memory gate signal: how much council history there is to weigh. | [src](../../../core/services/cluster_daemon_families.py#L111) |
| function | `_mem_council_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L117) |
| function | `build_memory_family` | `()` | Construct the memory/maintenance cluster-daemon (family #6), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L122) |
| function | `memory_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L152) |
| function | `_mem_decay_live` | `(_snap)` | Daily decay + re-discovery. Replicates the old heartbeat influence site: | [src](../../../core/services/cluster_daemon_families.py#L164) |
| function | `_mem_pruning_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L182) |
| function | `_mem_maintenance_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L187) |
| function | `_mem_safeguard_live` | `(_snap)` | The safeguard daemon exposes ``run()`` (its old heartbeat site imported a | [src](../../../core/services/cluster_daemon_families.py#L192) |
| function | `_mem_selective_consolidation_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L200) |
| function | `_mem_associative_recall_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L205) |
| function | `_mem_write_queue_live` | `(_snap)` | LOAD-BEARING + FREQUENT — drains the deferred write queue every 120s. | [src](../../../core/services/cluster_daemon_families.py#L210) |
| function | `_run_memory_nonllm_members` | `(snap, result)` | Run the NON-LLM maintenance members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon_families.py#L229) |
| function | `tick_cluster_memory` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the memory/maintenance cluster-daemon family (#6). | [src](../../../core/services/cluster_daemon_families.py#L245) |
| function | `_feed_aesthetic_choice` | `()` | Record the latest visible run's style/mode into the taste daemon. | [src](../../../core/services/cluster_daemon_families.py#L314) |
| function | `_collect_aesthetic_snapshot` | `()` | Gather the aesthetic family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L344) |
| function | `_aesthetic_taste_signals` | `(snap)` | aesthetic_taste gate signals: how much taste-evidence has accumulated. | [src](../../../core/services/cluster_daemon_families.py#L379) |
| function | `_aesthetic_taste_live` | `(_snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L394) |
| function | `build_aesthetic_family` | `()` | Construct the aesthetic/curiosity cluster-daemon (family #7), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L405) |
| function | `aesthetic_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L435) |
| function | `_aesthetic_curiosity_live` | `(snap)` | Rules-based gap scan over the thought-stream fragment buffer. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L447) |
| function | `_run_aesthetic_nonllm_members` | `(snap, result)` | Run the NON-LLM member(s) UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon_families.py#L463) |
| function | `tick_cluster_aesthetic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the aesthetic/curiosity cluster-daemon family (#7). | [src](../../../core/services/cluster_daemon_families.py#L478) |
| function | `_collect_relation_snapshot` | `()` | Gather the relation family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L559) |
| function | `_relation_user_model_signals` | `(snap)` | user_model gate signals: how much (and what shape of) user interaction has | [src](../../../core/services/cluster_daemon_families.py#L601) |
| function | `_relation_user_model_live` | `(snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L616) |
| function | `build_relation_family` | `()` | Construct the relation cluster-daemon (family #8), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L629) |
| function | `relation_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L659) |
| function | `_relation_comm_guard_live` | `(_snap)` | Godnat-split guard: sweep expired TTL communication-triggers + log active | [src](../../../core/services/cluster_daemon_families.py#L671) |
| function | `_relation_map_refresh_live` | `(_snap)` | Refresh the relation map (primary last_seen + stale secondary ToM stamps). | [src](../../../core/services/cluster_daemon_families.py#L679) |
| function | `_run_relation_nonllm_members` | `(snap, result)` | Run the NON-LLM members UNCONDITIONALLY (independent of the family generative | [src](../../../core/services/cluster_daemon_families.py#L696) |
| function | `tick_cluster_relation` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the relation cluster-daemon family (#8). | [src](../../../core/services/cluster_daemon_families.py#L712) |
| function | `_projects_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L800) |
| function | `_collect_projects_snapshot` | `()` | Gather the projects family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L818) |
| function | `build_projects_family` | `()` | Construct the projects/work-execution cluster-daemon (family #9), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L838) |
| function | `projects_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L860) |
| function | `_projects_task_worker_live` | `(_snap)` | LOAD-BEARING + EVERY TICK — drain up to 3 queued runtime_tasks. NO throttle: | [src](../../../core/services/cluster_daemon_families.py#L872) |
| function | `_projects_my_projects_live` | `(_snap)` | Restart Jarvis' dead background processes. Rules-based, no LLM. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L880) |
| function | `_projects_life_reassessment_live` | `(_snap)` | Re-assess active life projects; publish reassessment_due for stale ones. | [src](../../../core/services/cluster_daemon_families.py#L890) |
| function | `_projects_thought_action_live` | `(snap)` | Classify the latest thought-stream fragment into an action-proposal. Rules- | [src](../../../core/services/cluster_daemon_families.py#L901) |
| function | `_run_projects_unconditional` | `(snap, result)` | Run every projects member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L925) |
| function | `tick_cluster_projects` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the projects/work-execution cluster-daemon family (#9). | [src](../../../core/services/cluster_daemon_families.py#L941) |
| function | `_infra_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L1087) |
| function | `_collect_infra_snapshot` | `()` | Gather the infra family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L1106) |
| function | `build_infra_family` | `()` | Construct the infra/maintenance cluster-daemon (family #10), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L1117) |
| function | `infra_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L1142) |
| function | `_infra_file_awareness_live` | `(_snap)` | Ensure the file-awareness watcher thread is running (tamper detection). | [src](../../../core/services/cluster_daemon_families.py#L1154) |
| function | `_infra_cache_maintenance_live` | `(_snap)` | 6h web_cache cleanup. Rules-based, no LLM. Self-throttles INTERNALLY | [src](../../../core/services/cluster_daemon_families.py#L1163) |
| function | `_infra_signal_decay_live` | `(_snap)` | Archive+delete stale signals + refresh signal runtime statuses. Rules-based, | [src](../../../core/services/cluster_daemon_families.py#L1171) |
| function | `_infra_wakeup_cleanup_live` | `(_snap)` | Prune stale consumed/cancelled/fired wakeups. Rules-based, no LLM. Self- | [src](../../../core/services/cluster_daemon_families.py#L1179) |
| function | `_infra_cost_optimization_live` | `(_snap)` | Monitor daily/weekly spend vs budget; emit cost.* events. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1189) |
| function | `_infra_ground_truth_live` | `(_snap)` | Refresh the Ground-Truth Registry cache (Lying Engine, Lag 3). Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1199) |
| function | `_infra_mail_checker_live` | `(_snap)` | Poll IMAP for new mail; publish events for unseen messages. Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1210) |
| function | `_infra_visual_memory_live` | `(_snap)` | Webcam snapshot + LOCAL ollama vision-model description (Lag 6, 0 API tokens). | [src](../../../core/services/cluster_daemon_families.py#L1220) |
| function | `_run_infra_unconditional` | `(snap, result)` | Run every infra member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L1247) |
| function | `tick_cluster_infra` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the infra/maintenance cluster-daemon family (#10). | [src](../../../core/services/cluster_daemon_families.py#L1264) |

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

