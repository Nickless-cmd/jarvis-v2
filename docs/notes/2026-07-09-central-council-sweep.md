# Rådets Dom — Central-gennemgang (Matrix-tematiseret audit)

> Genereret 2026-07-09 via 7-medlems råds-workflow (fan-out → adversariel verifikation → syntese).
> 26/27 fund code-verificeret. Hver fund grounded i fil:linje.

---

RÅDETS DOM

## Intro

Centralen lever, men den ser sig selv gennem et sprækket spejl. Kernemønstret er sundt — assess→record→surface→route — men de kritiske sidste led er gang på gang kappet: instrumenter er bygget og aldrig wired, værn håndhæver §11.3 med håndholdte denylister i stedet for klassen, og broen melder grønt mens den kaster halvdelen af nervesignalet på gulvet. Ingen af fundene er en aktiv produktionsbrand; de fleste er tavse blindspots i observabilitet og governance — men to af dem (Keymaker-klassefiltret, fail-open owner-gate) er sikkerheds-fundamentet der hviler på at et menneske husker at opdatere to strenge.

Efter dedup: 23 fund → 21 distinkte. To sammenfletninger:
- **central_gardener ORPHAN** rejst af både Morpheus (low) og The Architect (medium, self-mutation-vinkel). Fusioneret under Architects stærkere ramme (live-repo-mutation bag ugoverneret execute-gate).
- **Keymaker _NEVER-denylist** (critical) og **approve_key uden klassetjek** (high) er samme rod (fail-open navne-antagelse i to lag) men holdes adskilt: de kræver hver sin fix og er begge nødvendige lag.

---

## FEJL (bugs)

| Medlem | Titel | Sev | Sted | Bygbar fix |
|---|---|---|---|---|
| Agent Smith | gate_shadow._is_enforced omgår §11.3 SECURITY-pariteten | medium | gate_shadow.py:60-68 | Slå klass op i _GATES-tuplen; `if klass is GateClass.SECURITY: return True` før flag-læsning |
| The Architect | {model}/{provider} interpoleret i stabil cache-prefix → failover koldstarter identitets-cachen | medium | prompt_contract.py:408-412 / 622-626 | Flyt model/provider-linjen til `_tail_add` (:936); behold model-agnostisk identitetslinje i prefix |
| Morpheus | 13 surfaces returnerer hardcodet `{active:True,'Module loaded...'}` og fodrer Central-digests falsk grønt | medium | self_deception_guard.py:281-294 (+12 filer) | Læs ægte state: `t=get_last_guard_trace(); return {'active':t is not None,...}` — MC-ruten gør det allerede korrekt |
| The Architect | central_timeseries._maybe_persist check-then-act uden lås → dublerede persist-tråde | low | central_timeseries.py:228-238 | Flyt tærskel-tjek + `_last_persist=now` under dedikeret lock; spawn tråd efter frigivelse |
| The Sentinel | discord _typing_loop `ensure_future` uden ref → kan GC'es mid-sleep (samme bug som _send_outbound_loop) | low | discord_gateway.py:829 | Modul-global `_typing_tasks[cid]=task` + `add_done_callback(pop)` — spejl 206f57e2 |
| The Oracle | connectivity-matrix fejlmærker ~20 routede cognitive-familier som DARK | low | docs/central_connectivity_matrix.md | Kør `python scripts/capability_audit.py` / connectivity-audit — doc'en er STALE, scriptet er allerede korrekt |

Note på Oracle-fundet: diagnosen i det oprindelige fund var forkert (scriptet parser allerede begge dicts). Reelt = stale doc. Fix = regenerér, ikke ret script.

---

## MANGLER (gaps)

| Medlem | Titel | Sev | Sted | Bygbar fix |
|---|---|---|---|---|
| The Sentinel | central.daemon_dead har healer men INGEN detektor — stale daemons flagges aldrig | high | daemon_manager.py:518-537 · error_healers.py:285-331 | Ny stale-detektor: iterér get_all_daemon_states(), `hours_since_last_run > 3×cadence` → emit kind; ret `_ALLOWED_UNITS`-mismatch (in-process ≠ systemd) |
| The Keymaker | approve_key re-validerer ikke §11.3 og flipper flaget med COGNITIVE-klasse | high | central_keymaker.py:142-165 | Efter row-fetch: hvis SECURITY-klasse/_NEVER → reject + markér 'rejected'; kald set_enabled med eksplicit katalog-klasse |
| The Merovingian | 5 build_*_surface() defineret med NUL kaldere — eksponerings-stien død | medium | central_causal_quality.py:156 · central_sequence.py:216 · central_notation.py:212 · central_signal_health.py:187 · central_model_meta.py:227 | Tilføj route pr. modul ELLER wire til heartbeat `_build_cognitive_surfaces` allowlist. Prioritér causal_quality+sequence+notation |
| Agent Smith | _kv_get/_kv_set byte-identisk kopieret i 25 central_*-moduler | medium | 25 central_*.py | Opret core/services/central_kv.py; erstat lokale med `from ... import kv_get as _kv_get` (alias → nul call-site-ændring) |
| The Architect | central_gardener ORPHAN + live-repo-mutation bag ugoverneret execute-gate (fusioneret m. Morpheus' low) | medium | central_gardener.py:26,90-143 | (A) flyt til scripts/ som eksplicit owner-CLI, ELLER (B) repo-root-detektion + route + gate bag owner-approval |
| The Architect | 46 filer >1000 linjer; 12 core-filer bryder hård 2000-grænse (worst >3×) | medium | heartbeat_runtime.py=7499 · visible_runs.py=6571 | Boy Scout: udskil tick-conductor-tilstandsmaskinen fra heartbeat; reasoning-interceptor-søm fra visible_runs. (Titlens '25' er forkert — reelt 46) |

Note: `_execute_simple_tool_calls` er ALLEREDE udskilt (57287fcc → simple_tool_executor.py). Architects fil-fund #1 er delvist forældet; brug reasoning-interceptor-sømmet som næste snit i stedet.

---

## BLINDSPOTS

| Medlem | Titel | Sev | Sted | Bygbar fix |
|---|---|---|---|---|
| **The Keymaker** | **_NEVER-denylist (7 navne) er delmængde af ~25 SECURITY-nerver → nye security-gates kan optjene decentraliserings-nøgle** | **critical** | central_keymaker.py:33-34 · central_decentralization.py:19-22 | Tilføj `nerve_klass(name)→GateClass` i central_catalog; erstat `if nerve in _NEVER` med `if nerve_klass(nerve) is SECURITY or nerve in _NEVER` begge steder |
| The Architect | observe_conservation() (cutoff-instrumentet) wired NOWHERE — 0 call-sites | high | central_output_conservation.py:27-66 | Kald fra provider-stream (cheap_provider_runtime) + run-persist (visible_runs, `_fp_deg_accum` vs result.text) |
| The Sentinel | Canonical Error healing-pipeline har NUL producenter — healers fyrer aldrig | high | internal_errors.py:152-158 | `report_canonical_error()`-helfer der POST'er loopback, ELLER lad emit() kalde heal_error() in-process når recoverable=='auto' |
| Morpheus | Bridge tæller uroutede families i én bulk-int uden at logge HVILKE — 50 DARK + enhver ny nerve forsvinder | high | eventbus_central_bridge.py:626 | `skipped_families[family]+=1`; efter loop `_observe_skipped_families()` (spejl _observe_failure_summary:547) |
| The Oracle | file_awareness.change events droppes tavst — Centralen blind for ekstern tampering af sin egen kode | high | eventbus_central_bridge.py + file_awareness_daemon.py:189 | `"file_awareness":("system","file_change")` i FAMILY_ROUTES (metadata-only, matcher process_watcher) |
| The Keymaker | require_central_owner: `uid is None → owner` → token-løs sti auto-autoriserer /central/keys/approve | high | central_auth.py:33-34 · central_keys.py:41-44 | Gør approve fail-closed: kræv positiv owner-uid/bearer; betinget 'unbound=owner' bag eksplicit dev-flag (default False i prod) |
| The Oracle | composite tool-familie (invoked/revoked/deleted) ikke routet — capability-mutationer usynlige | medium | composite_tools.py:132/142/216 | `"composite":("tools","composite")` i FAMILY_ROUTES; erstat `except: pass` med `logger.debug` |
| Morpheus | bridge last_seen_id på 24t TTL → killswitch/cadence-død >24t re-seeder og springer backlog tavst | medium | eventbus_central_bridge.py:470 | Hæv TTL til ~1 år (spejl _FLAG_TTL) el. durabel set_runtime_state_value; emit 'bridge_backlog_skipped' ved cold-seed>0 |
| The Oracle | apophenia_guard brænder LLM men rapporterer count=0 for evigt | medium | apophenia_guard.py:120-129 | Modul-tællere `_COUNTS{rejected,candidate,upgraded}`; returnér som liste/int så _first_count fanger magnitude |
| Agent Smith | gate-enforce-observabilitet skrives til 2 sinks m. 2 kinds for samme begreb | low | gate_enforcement.py:47-60 · gate_shadow.py:71-94 | Fælles `note_gate_enforce(...,suppressed:bool)` → observe + (RED) incident; build_gate_enforce_surface ovenpå |
| The Merovingian | central_notation finder modsigelser i egen tilstand hver 30. min og smider dem væk | low | central_notation.py:177-197 | Ved ikke-tom `contradictions`: emit observe/hypotese pr. par (spejl prediction_error-bro :404-433) |
| The Keymaker | decentralize-switch-flag er dobbelt sandhed (skrevet, ulæst); zombie-'approved' hvis cadence dør | low | central_keymaker.py:159,168-190 | Fjern ulæst flip ELLER beregn effektiv status on-read (`approved AND expires_at>now`) i list_keys/surface |
| The Keymaker | central_layer_contract lader strenge krydse mod OPERATIONAL-egress; kun ydre lag redder | low | central_layer_contract.py:78-80 | Strip strenge i _sink OPERATIONAL-gren (genbrug _egress_safe). Bemærk: OPERATIONAL er pt. UBRUGT — latent |

---

## TOP 5 AT BYGGE NU

Rangeret efter severity × bygbarhed. To sikkerhedsfund topper fordi de er fail-open på §11.3-fundamentet; de tre næste er høj-værdi, lav-indsats wiring der genopretter Centralens selvsyn.

**1. [The Keymaker] Klasse-baseret SECURITY-filter i Keymaker + approve_key — `critical`+`high` · S**
Byg `nerve_klass(name)→GateClass` i central_catalog og erstat begge `if nerve in _NEVER` med klasse-tjek. Tilføj samtidig reject i approve_key. **Hvorfor nu:** hele optjent-nøgle-modellens sikkerhedsgaranti (§11.3: sikkerhed decentraliseres ALDRIG) hviler lige nu på at et menneske husker at synkronisere to håndholdte 7-navns-frozensets mod ~25 SECURITY-nerver. Det er fail-open, og de altid-grønne security-instrumenter (outbound_scrub, abuse_monitor) er præcis dem der kan krydse 100 grønne og optjene en nøgle. Lille kode, størst blast-radius. Byg begge lag samme dag — defense-in-depth kræver det.

**2. [The Keymaker] Fail-closed owner-gate på privilege-eskalerende ruter — `high` · S**
Gør `/central/keys/{id}/approve` fail-closed; betinget 'unbound=owner' bag eksplicit dev-flag. **Hvorfor nu:** verifikationen afslørede at den PRIMÆRE sti er simplere end oprindeligt antaget — `auth_required()` defaulter False + `--host 0.0.0.0` betyder en uautentificeret LAN-request rammer `uid is None → owner`. Den ene handling der giver Jarvis mere autonomi auto-autoriseres. S i indsats, men parres bedst med #1 (samme governance-domæne).

**3. [Morpheus] Bridge unrouted-families observabilitet — `high` · S**
`skipped_families[family]+=1` + `_observe_skipped_families()`, spejlet direkte fra `_observe_failure_summary` der allerede findes ti linjer væk. **Hvorfor nu:** dette er meta-fixet der gør ALLE andre routing-blindspots (file_awareness, composite, + de 50 DARK + fremtidige nerver) selv-opdagende i stedet for at kræve en manuel audit hver gang. Broen melder grønt mens den taber signal — dette gør tabet pollbart. Højeste leverage pr. linje i hele listen.

**4. [The Oracle] Route file_awareness + composite (protected-core capability/tamper) — `high`+`medium` · S**
To FAMILY_ROUTES-linjer, metadata-only, samme mønster som allerede-wirede process_watcher. **Hvorfor nu:** "code/runtime awareness" er PROTECTED CORE pr. CLAUDE.md. `external=True` fil-ændringer af Jarvis' egen kode og capability-mutationer (composite.revoked/deleted) er præcis de tamper/drift-signaler protected core skal fange — og de er usynlige for Centralen i dag. Trivielt bygbar, direkte analog til det seneste bridge-commit (7a763448) allerede lukkede for andre familier.

**5. [The Architect] Wire observe_conservation() ind på provider-stream + run-persist — `high` · M**
To call-sites docstringen selv navngiver. **Hvorfor nu:** dette er instrumentet for projektets mest tilbagevendende bugklasse — cutoff-spøgelset (bytes forsvinder mens turen ser 'completed' ud, jf. et halvt dusin reference_*cutoff*-noter). Uden call-sites forbliver hvert byte-tab flygtigt i stedet for stående, per-provider-korrelerbar data. M ikke S fordi det rører hot-path (skal være self-safe, kaster aldrig), men det er den ene wiring der forvandler den dyreste bug fra "gætværk hver gang" til "målt".

---

**Ærlig bundlinje:** #1–2 er ikke valgfri — de er sikkerhedshuller i selve autonomi-governance. #3–5 er billig wiring der betaler tilbage i selvsyn. Alt i BLINDSPOTS-tabellens `low` (layer_contract, notation, decentralize-flag, gate-enforce-dobbelt-sink) er ægte men kosmetisk/hygiejnisk — byg dem som Boy Scout når du alligevel er i filen, ikke som dedikeret arbejde. Sentinel's daemon_dead-detektor (high) faldt uden for top 5 kun fordi den kræver at man samtidig retter `_ALLOWED_UNITS`-mismatchet (in-process-daemons er ikke systemd-units) — reel M-indsats, men næste efter top 5.
