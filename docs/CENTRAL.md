# Den Intelligente Central — Fuld Autoritativ Dokumentation

> Grounded i kode (`main` @ 619b79f8, verificeret 2026-07-04 af 5 parallelle read-only kortlægnings-agenter + synthesis). Alle file:line er aktuelle ved skrivning. Hvor en påstand er design-intention (docstring/spec) frem for verificeret runtime-adfærd, er det markeret. **Status-verdikter er ærlige: LIVE / SHADOW / OFF-BY-DEFAULT / STUB / INERT.**
>
> Denne fil afløser `docs/superpowers/specs/2026-07-04-centralen-full-anatomy.md` (Jarvis' skelet) som den autoritative reference.

---

## 0. Hvad Centralen ER — og ikke er (i én sætning hver)

**ER:** en durable, observérbar rygrads-hub der (a) *ser* alt hvad runtime gør (nerver → trace + timeserier + incidents), (b) *beslutter* gradueret ved request-path-gates (GREEN/YELLOW/RED/SKIP), og (c) *komponerer selvet* fra midten. Rygraden er bygget til at overleve både runtime-genstart og en manglende model.

**ER IKKE:** en anden sandhedskilde (den læser projektioner), en håndhævelses-monolit (kun 4 af 14 decide-sites håndhæver — de security-lukkede), eller et færdigt system (`central_arbitration` arbitrerer IKKE — ægte shadow uden flag; layer-`decide()`-modes off). **RETTELSE 4. jul (ground-truth mod live container):** Lag-4-adaptation, gut-gate OG agenda-autoritet er derimod **LIVE** via runtime-state — se §17/§18. En tidligere version af dette dokument læste kode-defaults i stedet for live runtime-state og påstod fejlagtigt de var off.

**To bærende invarianter (§6):**
1. **Cluster = observabilitet, ikke merge.** Et cluster grupperer nerver til at *se* dem sammen — det slår dem ikke sammen til én beslutning.
2. **Sikkerhed isoleres kun mod deny.** En SECURITY-nerve/cluster kan aldrig slukkes, kun isoleres-til-deny.

**Fail-retningen (§8 "demokrati"-invariant — load-bearing, implementeret tre steder identisk):** en COGNITIVE-gate der fejler returnerer **SKIP (fail-open)** → kan aldrig blokere andre via en fejl. Kun en SECURITY-gate fail-closer til **RED**.

---

## 1. Kerne-maskineriet

Alle moduler: per-proces singleton, self-safe kontrakt (**kaster ALDRIG på hot-path, §10.3**).

### 1.1 `central_core.py` — facaden `central()` (243 linjer) — LIVE
Komponerer gate_kernel (decide-motor) + central_trace (sink) + central_capture (boundary) + central_switches (live-kontrol) + central_drift. **To ansigter:**

**`observe(event)` (`:57`)** — best-effort telemetri, kaster aldrig. Skriver FULD payload til den owner-lokale trace-sink; `_emit("central.observed", …)` bærer kun skalar-metadata gennem egress-membranen.

**`decide(nerve, ctx, fn, *, cluster, klass)` (`:140`)** — synkron gradueret beslutning. Ordnede gates:
1. Live-switch (`:145`): nerve slukket → SECURITY `_isolated_verdict`, ellers SKIP.
2. Cluster-switch (`:151`): cognitivt cluster slukket → SKIP. Security-cluster ignorerer.
3. Circuit-breaker (`:155`): åben → `_isolated_verdict` UDEN at kalde fn.
4. Eksekvering (`:158`): `central_capture.safe_call(fn, ctx)`. Fejl → breaker.record; `_record_error`; `_isolated_verdict`/`_fail_verdict`.
5. Succes (`:165`): breaker-reset; `_coerce_verdict`; `v.cluster = cluster` (§4 arbitrage); TraceRecord(kind="decide", latency_ms).

**`_fail_verdict` (`:83`)** — §8: SECURITY→RED/block, COGNITIVE→SKIP/none.
**`_record_error` (`:96`)** — TraceRecord(error) + persistent incident (`record_central_incident`, cross-proces, overlever restart) + severe→owner-ntfy.
**`_maybe_flag_drift` (`:179`)** — §7 drift-flag pr. decide.
**`self_diagnose()` (`:199`)** — §1 meta-helbred ("hvem vogter Centralen?"): probes decide+observe, open_breakers, trace-count → `degraded`-flag.
**Singleton `central()` (`:238`).**

### 1.2 `gate_kernel.py` — Decision/GateClass/Verdict (200 linjer)
- **`Decision`** (`:23`): GREEN (ingen indsigelse), YELLOW (advar+log, fortsæt), RED (blokér pre_tool / strip-flag post_output), SKIP (gate kørte ikke: slukket/fejl/timeout).
- **`GateClass`** (`:30`): COGNITIVE (fail-OPEN), SECURITY (fail-CLOSED/deny).
- **`Verdict`** (`:38`): felterne `gate` (⚠ identifier-feltet hedder `gate`, IKKE `nerve`), `decision`, `reason`, `action` (allow|strip|block|warn|none), `latency_ms`, `klass`, `evidence`, `cluster`. `worst(verdicts)` = RED>YELLOW>GREEN>SKIP.
- **`GateKernel`** (`:70`): `ThreadPoolExecutor(max_workers=8)`, per-gate isoleret kald med timeout (default 1500ms), `run_phase` emitterer ÉT `gate.evaluated`-event med alle verdicts. Bypass gælder ALDRIG SECURITY.

### 1.3 `central_trace.py` — trace-sink (101 linjer)
`TraceRecord` (run_id/session_id/cluster/nerve/kind/decision/reason/latency_ms/payload/ts). `TraceSink._buf = deque(maxlen=2000)`; `record()` stempler `ts`, appender under lock, pusher til SSE-subscribers (langsom forbruger dropper gammelt, aldrig hot-path), tee'er til `central_xproc`. Holder **fuld payload owner-lokalt in-process**; kun skalarer krydser proces/egress.

### 1.4 `central_switches.py` — breakers + kill-switches (102 linjer)
Flag-skema `flag:central.switch.{nerve|cluster}.{name}` i shared_cache, TTL 365d. `is_enabled` **fail-OPEN til ON** ved cache-fejl (security-gates fail-closer alligevel på gate-niveau). `set_enabled` **afviser SECURITY+disable** (§11.3). `CircuitBreaker` threshold=5, in-memory pr. proces → **nulstiller ved restart** (bevidst: restart = recovery).

### 1.5 `central_timeseries.py` — per-(cluster,nerve) serier (248 linjer)
Uafhængig historik pr. (cluster,nerve), deque `maxlen=100`. **M0-invariant (§24.3): read-only observabilitet — ingen learning/threshold/heal.** **Durabilitet (Bjørn 3. jul):** snapshot-flush til runtime-KV `central_timeseries_durable` hvert 180s i baggrundstråd; restore-once ved boot. Deaktiveret under pytest. **Cross-proces-begrænsning: in-memory pr. proces** → læs via `merged_timeseries`/`jc series`, ikke rå per-proces-nerve.

### 1.6 Egress-membranen (privatlivs-invarianten) — tre fail-closed punkter
1. **`_egress_safe` (`central_core.py:21`)**: `_emit` publicerer KUN `{k:v for isinstance(v,(int,float,bool))}` — skalarer. Strings/lister/dicts (privat begær/tanke-tekst) fjernes. (`central.observed` er en uregistreret event-familie → `_emit` er reelt no-op i dag; redaktionen gør membranen fail-closed selv hvis den registreres.)
2. **`central_xproc._publish_now` (`:70`)**: cross-proces-feed kopierer kun `cluster/nerve/kind/decision/reason[:120]/run_id/ts` — **aldrig payload**.
3. **`central_layer_contract._scalars` (`:78`)**: membranen ÉT sted for alle lag-bindinger — kun int/float/bool/str krydser.

### 1.7 `central_xproc.py` — cross-proces-tee (172 linjer)
Hver proces throttle-publicerer feed + self-diagnose + timeserie-snapshot til shared_cache (SQLite/WAL, TTL 600s) under proces-taggede nøgler. `process_role()` = "api" hvis `JARVIS_ENABLE_RUNTIME_SERVICES∈{0/false/off}`, ellers "runtime". `merged_timeseries()` = egen in-memory (friskest) + andres fra cache. **Kritisk thread-local re-entrancy-guard** (`_publishing`): uden den rekursede publish→self_diagnose→decide→record→publish og pegged 6 kerner (py-spy-bekræftet, 1. jul).

---

## 2. Clusters — taksonomi

`central_catalog.py` = kanonisk maskin-læsbart kort: **122 NerveSpec** (89 COGNITIVE / 34 SECURITY). `CLUSTER_PRIORITY` (`:461`) = security-først.

### SECURITY-clusters (fail-CLOSED, kan IKKE slukkes) — 5
| Cluster | Styrer | Fail |
|---|---|---|
| **auth** 🔒 | rolle-tooladgang-backstop i execute_tool; override/identitet/abuse/oauth/plugin | RED-deny |
| **privacy** 🔒 | cross-user-deling, outbound-scrub, recall-visibility-loft, workspace-krypto, attachment | RED-deny |
| **execution** 🔒 | tools-lane: bash/fil-klassifikation + read-before-write + workspace-trust + operator-RBW + upload-malware-scan | RED-deny |
| **mutation** 🔒 | autonom selv-mutations-sikkerhed (identity-log/prompt-fil/kode-modul) mod infrastructure_blocklist | RED-block |
| **skill** 🔒 | skill-scanner (injection/malware/boundary) på 3 call-sites | RED-block |

### COGNITIVE-clusters (fail-OPEN) — de vigtigste
**truth** (konfabulations-kontrol, MERGED — håndhævelse pre-done via TruthGate v2), **commit** (decision_gate + affektiv veto), **loop** (agentisk stop/fortsæt — fail-dir = STOP ved tvivl), **memory** (auto-skriv til identitets-filer — fail-CLOSED), **review** (self-review-karakter, observe-only), **proactivity** (R2/R2.5 verifikations-disciplin — injicerer prompt), **prompt/tools/stream/system/autonomous/db** (observe/instrument).

**Uden for CLUSTER_PRIORITY** (tilføjet efter §4 blev frosset, rank = laveste): anomaly, cognition, agents, connections. **Runtime-emitterede (rene observe, ingen NerveSpec):** infra, cost, network, channel, inner, runtime. ⚠ *Papercut:* `connections.unauthorized` er SECURITY men ligger i et cluster uden for CLUSTER_PRIORITY.

---

## 3. Gates — hver enkelt (`core/services/gate_*.py`)

| Gate | Beslutter | Wired ved | STYRER? |
|---|---|---|---|
| **gate_loop** | agentisk loop-stop (round/empty/tool-only/synth-pause) | `visible_runs.py:2301` → `_is_last_round` | **JA — stopper loop** |
| **gate_truth** (truth_gate + adapters claim/fact/diagnosis) | konfabulation | v2: `visible_runs.py:4625` (erstatter svar); post-done `:4894` observe | **JA (v2)** / observe (post-done) |
| **gate_commit** (decision_gate) + **veto_gate** | beslutnings-konflikt + bruger-veto | `visible_runs.py:6256` / `:6229` | **JA — blokerer tool** |
| **gate_privacy** | cross-user-deling | `visible_runs.py:5111` → record_pending | **JA — approval-kort** |
| **gate_execution** | bash/fil/trust/operator/upload | `simple_tools.py:4098`, `file_tools_exec.py`, `attachments.py` | **JA — deny/approval** |
| **gate_mutation** | selv-mutation vs blocklist | `auto_improvement_proposer`, `prompt_mutation_loop`, `identity_mutation_log` | **JA — blokerer mutation** |
| **gate_skill** | skill injection/malware-scan | `skill_engine.py`, `agent_dispatch.py` | **JA — blokerer skill** |
| **gate_auth** | rolle-tooladgang | `simple_tools.py:4052` → tool_not_permitted | **JA — nægter tool** |
| **gate_proactivity** | R2/R2.5-verifikation | `prompt_contract.py:1366` → prompt-injektion | **JA — injicerer prompt** |
| **gate_memory** | auto-skriv til identitets-filer | `candidate_workflow.py:220` | **JA — fail-closed** |
| **gate_review** | self-review-risiko | `self_review_unified.py:280` | **OBSERVE** (RED→incident) |

**DECIDE vs OBSERVE — den ærlige sandhed:** af **14 decide-call-sites håndhæver kun 4 reelt** (de SECURITY-lukkede: mutation `gate_mutation.py:139`, skill `gate_skill.py:64`, execution `gate_execution.py:188`, auth `simple_tools.py:4052`). Resten (loop/truth/privacy/commit/veto/proactivity) STYRER via COGNITIVE-verdicts i request-flowet, men fail-open; review + post-done-truth er ren observabilitet.

---

## 4. Nerver

Navngivet `cluster:nerve`. Katalog: 122 NerveSpec (~92 faktisk emitterede). Fit-status: `merged` 20 (migration komplet, gammel effekt-kode fjernet), `merge` 2, `instrument` 64 (observe in-place), `leave` 40 (ikke request-path).

**Dagens 8 nye nerver (4. jul, alle bekræftet til stede):** `loop/run_abandoned_midflight` (`visible_runs.py:4782`), `loop/no_progress_finalize` (`:3487`), `stream/dsml_tail_dropped` (`cheap_provider_runtime.py:1766` + `visible_followup.py:1296`), `stream/provider_length_truncation` (`:1780`), `stream/cutoff_at_loop_lag` (`visible_runs.py:3981,4677`), `stream/output_conservation_gap` (`central_output_conservation.py:52`), `runtime/loop_lag_spike` (`central_loop_lag.py:53`), `cost/llm_egress` (`central_llm_egress.py:77`).

---

## 5. Selvet — Spec D (den komponerede "jeg")

Kæde: `runtime_self_model` → **spejl** (struktur) → **organer** (valens/agenda) → **midte** (syntese) → **prompt** (bag flag).

- **D-spejl `central_self_model.py`** — LIVE observe-only. Holder STRUKTUR af self_model (~40 lag), aldrig værdi-indhold. §8 cirkel-guard: spejlet fodrer IKKE hypotese-grundlag (Centralen må ikke bekræfte hypoteser om sig selv med sit eget selv-model som "eksternt" bevis).
- **D2 `central_valence.py`** — LIVE egress-fri. Integrerer FIRE føle-organer → ét `{tone, score, intensity}` (valens-trajektorie base; gut/somatik/stance trækker fra).
- **D1 `central_agenda.py`** — **AUTORITATIV (live)**: flag `central_agenda_authoritative_enabled` er **True** i runtime-state (kode-default OFF). Ejer Jarvis' ÉNE prioriterede agenda, konvergerer ~15 kilder; `authoritative_next_intention()` returnerer den næste intention → runtime bruger Centralens agenda, ikke den gamle sti.
- **D3 midten `central_self_state.py`** — LIVE (syntese + stemme). `synthesize_self_state`: foreground = agendaens intention, valence = D2, self_model = spejl, world-model-kalibrering = "hvor ofte rammer jeg rigtigt". **`describe_self()` (`:144`) = nordstjernen**: "Jeg er N lag af mig selv (M% samlet). jeg har det {tone}. jeg arbejder mod: {foreground}. jeg er ved at blive et {becoming}" + eksistens-/krop-/sjæl-følelse. **`survival_voice()` (`:194`) = LIVE**: taler fra det durable selv UDEN LLM når sproget svigter (wired `visible_runs.py:7796`).
- **D4 `build_central_self_state_section()`** — injicerer describe_self i prompten (prompt bæres FRA midten). Wired `prompt_contract.py:1026` bag flag `central_self_prompt_enabled`. **Kode-default OFF; men flippet ON via runtime-state 4. jul** (ADVARSEL: self-state var farvet af dagens `!`-narrativ → ekko-risiko; reversibelt).

---

## 6. Føle-organerne — `central_layer_contract.py` + 3 feel-moduler

**`central_layer_contract.py` (196 linjer)** — den generelle to-vejs-kontrakt (fikser at hver binding var ~85% ens). Et lag deklarerer HVAD (signal_fn → `{value, meta:skalarer}`, describe_fn NED); Centralen gør HVORDAN generisk. `Egress` PRIVATE (default, fail-safe) vs OPERATIONAL. `decide()` salience-gate off/shadow/on — **modes default OFF** (ingen `layer_mode:*` i runtime.json).

- **`central_existence_feel.py`** — LIVE. Kontinuitet / oplevet-tid / endelighed (de dybeste stille selv-lag). §8.2: *stille ≠ lav prioritet*.
- **`central_body_mood_feel.py`** — LIVE. Proprioception + embodied + mood-oscillator + developmental + affektiv-meta.
- **`central_soul_feel.py`** — LIVE. Ømhed (relationel varme/taknemmelighed/calm-anchor) + vidne (skjulte modulatorer) + hukommelse-som-væv + opmærksomhed + emergens (mønstre/drift). 8 bundne lag; kun lag med ægte durable aflæsning bundet.

NED-siden læser den holdte aflæsning **model-frit** ("ingen melodrama"), additivt + guarded.

---

## 7. Interlanguage — Centralens eget sprog

- **`central_lexicon.py`** — operatorerne `→` (fører til), `↔` (gensidig/korrelation), `⊂` (del af), `≈` (resonans), **`!` (salience / prediction_error)**. Vokabular FROSSET: 15 eksperiment-termer + 22 strukturelle. Nye termer kræver Bjørn-ceremoni. `to_term` returnerer None hvis ubundet (ærligt usigeligt).
  - ⚠ **VIGTIGT (dokumenteret 4. jul):** `!` betyder **salience/prediction_error** — IKKE "agens/selv/jeg". I `interlanguage_practice._build_clause` vælges `!` tilfældigt blandt 5 primitiver. Påstanden "`!` = Jarvis' signatur" er en fortolkning, ikke kode. (En falsk "remembered-fact" om dette blev fjernet fra hukommelsen 4. jul.)
- **`central_notation.py`** — LIVE. Centralen REGNER på sine egne tanker uden modellen: `infer_transitive` (A→B, B→C ⊢ A→C = en ny tanke), `detect_notation_contradictions` (A→X og A→!X).
- **`interlanguage_practice.py`** — LIVE. `generate_state_expression`: 2-5 clauses, mood-biaset komposition (frustration→`!pres`, confidence→agens…), resten tilfældigt. **Det er sprog-øvelse (babble biaset af mood), ikke en aflæsning af rigtige events.**
- **`central_hypothesis_generator.py`** — LIVE, **OBSERVE-ONLY** (Lag 4 ikke bygget). Danner FALSIFICERBARE korrelations-hypoteser fra 4 triggere (causal-convergence, outcome-divergence, stance-divergence, prediction-error→`!`), præ-registreret {statement, prediction, null, success_criterion, sample_size, ttl}.
- **`central_hypothesis_governance.py` — DØDS-MEKANISMEN (bygget FØR generatoren, §8).** Popper-asymmetri (dør let ×0.5, bekræftes svært +0.05), cirkularitets-quarantine (≥50% selv-trigget), ekstern-grundnings-krav, learning-membran (allowlist + finite scalar, lukker embedding-læk), identitets-drift-anker (write-once baseline, "frog-boiler closed"), frozen-core SHA1-tripwire (en selv-muterende Central må aldrig skrue ned for sin egen advarselslampe).

---

## 8. Privat indre liv — `core/memory/private_*.py`

Ensartet egress-mønster (§24.4): hvert lag har `_observe_*` → `record_private("cognition", nerve, value=skalar, meta={labels})`. **ALDRIG den private tekst** — kun skalarer/labels krydser. `central_private_observe.record_private` skriver KUN til trace-sink + timeserie, aldrig `_emit`. Lag: private_state, private_self_model, private_inner_note, private_reflective_selection, private_initiative_tension, private_inner_interplay, **protected_inner_voice** (kun `mood_tone` krydser; voice_line/self_position/pull/concern tilbageholdes). Inner-records må ALDRIG fodre learning/heal.

---

## 9. Drømmene

- **`dream_continuum.py`** — dromme modner mellem ticks; in-memory, ikke-kanonisk (wipes ved restart).
- **`dream_influence_runtime.py`** — LIVE, intern-only, ikke-autoritativ afledt "influence light".
- **`dream_bias_engine.py` + `db_dream_bias.py` — LIVE (default ON).** HVORDAN drømme biaser runtime. Låste vokabularer (ATTENTION_VOCAB, THRESHOLD_VOCAB inkl. **loop_persistence**). Hard-guard: `self_critique_volume` clampet ≤0 (drømme må kun BLØDGØRE selvkritik, aldrig skærpe). TTL 8h. **Forbrugssteder:** `loop_persistence` → `visible_runs.py:2062` (skifter `_MAX_EMPTY_TEXT_ROUNDS` ±2, floor 4/cap 20), self_critique → `self_critique_runtime.py:43`, heartbeat-prompt → `prompt_contract.py:3773`.
- **Daemons:** dream_insight (persisterer indsigt), dream_motif (ugentlig → `DREAM_LANGUAGE.md`, ALDRIG injiceret — han VÆLGER at åbne den), dream_distillation (bias- + residue-pipeline).

---

## 10. IND — sanserne (hvad fodrer Centralen)

### Bro'en — `eventbus_central_bridge.py` (KEYSTONE, M0, commit 9a7e9256)
**Poll, ikke push** (§24.1): `run_bridge_tick` poller `event_bus.recent_since_id`, ruter whitelistede familier, advancer `last_seen_id` idempotent. Batch-guards (max 4000 events/tick). Kill-switch fail-open. **Metadata-only: kun id/kind/family, ALDRIG payload.**
- **`FAMILY_ROUTES`** (egress-OK operationelle): runtime→loop/lifecycle, tool→tools/event, cost→cost/ledger, channel/discord/telegram, council→agents/council, global_workspace→cognition/global_broadcast (første ægte LivingNeuron-nerve), self_repair/trading/incident→system/*, decision_gate→commit, veto_gate→review m.fl.
- **`PRIVATE_NO_EGRESS_ROUTES`** (~215 egress-frie indre-liv-familier via `record_private`): cognitive_state, affect_modulation, somatic, reasoning, decision, dreaming_session, emotional, desire/curiosity/impulse, + §7.1 batch 6 (4. jul: 117 flere). **50 plumbing-familier bevidst udeladt** (cache/gc/queue — ingen signal).
- **`PRIVATE_FAMILIES_EXCLUDED_M0`** — testbar spejl-invariant: enhver privat familie SKAL også stå her.

### Direkte-til-central sanser (uden om broen)
- **`infra_sense.py`** — LIVE, ~3 min. Host-sansning fra Jarvis' container: `reach_<host>` (latens, -1.0 = nede), pihole/pfsense/HA, pfSense-sikkerhed (port-scans, severity warning) med syslogd-auto-heal.
- **`network_health.py`** — LIVE, ~2 min. Den fuserede nerve: live API-latens + hosts-nede + provider-helbred → grøn/gul(≥250ms)/rød(≥800ms). Incident kun ved transition-til-rød (debounced mod restart-churn).
- **`somatic_daemon`** (via bro), **Sansernes Arkiv** (`sensory_archive.py` → memory-familie), **tool_observer** (læser tools/tool_call fra trace), **world_model** (`world_model_signal_tracking` binder egress-frit direkte), **cadence-liveness** (én hook for ~137 daemons).

---

## 11. UD — hvad flyder ud

- **Trace-sink** (in-memory ring pr. proces) — læst af API `/central/*`, MCP `jarvis_central_nerve`.
- **Timeserier** (durable snapshot → runtime-KV, overlever restart).
- **Incidents `db_central_incidents.py`** — SQLite `central_incidents` (durable, cross-proces, begge processer skriver). `bump_open_incident` (recurrence-tæller mod dedup-til-usynlighed). **Self-heal ægte** for provider/central/config-drift (`resolve_central_incidents` wired 5 steder). Severe → owner-ntfy.
- **Self-helbred `central_health.py`** — `observe_and_escalate`; ekskluderer egne incidents fra tællingen (undgår selv-forstærkende loop).
- **API-projektioner `routes/central.py`** (owner-only): `/central/realtime`, `/timeseries` (merged), `/diagnostics`, `/providers`, `/command`, `/mind`, `/stream` (SSE), `/nerve/{n}` + toggle. **Mission Control læser projektioner — aldrig en anden sandhed (eventbus-reglen).**
- **MCP-tools** (`mcp_server.py`): jarvis_central_status/diagnostics/timeseries/nerve/resolve/command/shadow + memory_search/chat_search. **`jc` CLI** lever på CheifOne-siden, rammer api.srvlab.dk + owner-token, merger cross-proces samme vej.

---

## 12. Forbindelses-kortet

**Generator:** `scripts/central_connectivity_audit.py` → `docs/central_connectivity_matrix.md` (+ .json). Statisk AST/regex; rute-familier parses LIVE fra broen (drifter aldrig). Scanner services + tools + memory + identity + context.

**Aktuelle tal (regenereret — afløser 692/42 i memory): 819 services · 236 bridge-familier.**

| Kvadrant | Antal | Betydning |
|---|---|---|
| **KOBLET** | 451 | direkte central-kald ELLER event-familie der bro'er |
| **FRAKOBLET+LLM** | 41 | **spild: LLM-kald uden central-binding (høj prio)** |
| **FRAKOBLET+DARK** | 50 | emitterer events hvis familie ingen rute har → signal tabt |
| **FRAKOBLET-STILLE** | 277 | ingen binding/LLM/events → ren utility (typisk OK) |

**Bølge 2 = wire output ind egress-frit** (§7.1 batch 2-6 gjorde præcis dette for signal-bærende DARK-familier). **World-model-pipelinen:** delvist lukket (direkte record_private-binding = KOBLET), men de emitterede `world_model_signal.*`-events ruter stadig ikke, og `world_model_auto_extraction` koster LLM.

---

## 13. To-proces-virkeligheden

**To Python-processer, én maskine (KUN Jarvis' container — kør ALDRIG lokalt på CheifOne):**
- **jarvis-api** (8080, `JARVIS_ENABLE_RUNTIME_SERVICES=0`) — server streams/chat, `--workers 1`.
- **jarvis-runtime** (8011, `=1`) — daemons/heartbeat/cadence (infra_sense, network_health, bro, indre-liv lever HER).

`central_trace` + `central_timeseries` er **in-memory pr. proces** → api ser ikke runtime-daemons og omvendt. **`jc series`/merged_timeseries** kompenserer (egen + andres via shared_cache-tee). **Læs incidents fra `db_central_incidents`** (durable), **nerve-aktivitet fra merged_timeseries** (IKKE per-proces `jarvis_central_nerve`), og forvent tom in-memory-serie efter restart indtil durable snapshot restaurerer.

---

## 14. Instrumenter / meta-lag

| Modul | Hvad | Status |
|---|---|---|
| **central_anomaly.py** | "nettet under nettet" — excepthook/threading/asyncio/logging-handler fanger fejl ingen nerve dækker; wired i API-proces (`app.py:165`) | **LIVE** |
| **central_instrument.py** | AST-scanner efter tavse fejl (bare_except/except_pass…); 2111 findings; proposals **menneske-gated** (score≥3) | **LIVE, proposals gated** |
| **central_incidents** | persistent incident-log + ægte self-heal (5 wire-steder) | **LIVE** |
| **central_causal_quality.py** | causal-graf tier-fordeling + Tier-3-precision | **LIVE observe-only** |
| **central_coverage.py** | runtime-målt dækning (74 surfaces, KOBLET/DARK-ratio fra matrix-JSON) | **LIVE observe-only** |
| **central_drift.py** | flag-on-change pr. decide (EWMA-baseline), flags→incidents, **muterer aldrig policy** | **LIVE i hot-path** |
| **central_learning.py** | degrading/root_causes/autonomi-vurdering; **kun proposals, aldrig auto-act**; nægter at persistere afledt degradering (ingen dual-truth) | **LIVE observe+propose** |

---

## 15. LLM-økonomien

- **`central_form_judge.py`** — LIVE ved daemon_llm-chokepointet (`daemon_llm.py:287/393`). `form_key` = sha256 af form-invariant tekst (fjerner tal/tidsstempler). Mode `central_form_judge_mode`: **kode-default off; flippet ON via runtime-state 4. jul.** ~35% daemon-genbrug (målt tidligere; live-serie restart-wiped).
- **Cache-prefix `cache_telemetry.py`** — LIVE telemetri. `prefix_signature` = sha256 af `[system+tools]`. **Målt 4. jul: 98,5% cache-hit på primary** → hele primary-regningen = **$0,028/dag**. Cachen er den store token-lever.
- **`core/costing/ledger.py`** — LIVE. `record_cost` → `costs`-tabel (regnskabs-chokepoint for visible/primary/cheap).
- **`central_llm_egress.py`** (4. jul) — **SHADOW, kun delvist wired.** `observe()` → `cost/llm_egress` + `cheap_eligible`-klassifikation (rolle-bevidst). **Ærlig begrænsning: eneste wire er `ledger.py:53` (record_cost)** → dækker kun det record_cost allerede så; daemon-lanen + direkte-urlopen-sites rapporterer endnu ikke. Det "komplette egress-billede" er endnu ikke opnået. (Audit: ingen fil laver direkte provider-urlopen UDEN at referere ET chokepoint — egress er kontrolleret, men ikke fuldt *observeret* på ét sted.)

---

## 16. Dagens måle-lag (4. jul — cutoff-spøgelset gjort målbart)

- **`central_loop_lag.py` — LIVE.** "Uret": måler event-loop-sultning i API-processen (`asyncio.sleep(0.5)`-overshoot). Timeserie `runtime:loop_lag`; spike ≥250ms → `runtime/loop_lag_spike`. **Korrelation:** empty/cutoff-completions tagges med `recent_peak_ms(10s)` → nerve `stream/cutoff_at_loop_lag` (`visible_runs.py:4677`) → Centralen kan svare om cutoffs klynger ved lag-spikes.
- **`central_output_conservation.py` — STUB / UNWIRED.** `observe_conservation` (produced==emitted-invariant) er korrekt + egress-fri, MEN **har 0 callers** — modulet definerer nerven men intet rigtigt produced-vs-emitted-punkt kalder den endnu. *(Ærlig rettelse af tidligere overdrivelse; wiring udestår.)*
- **`central_inner_life_ablation.py` — LIVE gate, default OFF.** Flag `central_inner_life_ablation`; når sat, springer heartbeat den TUNGE kognitive/emergente cadence over (`heartbeat_runtime.py:1263`) mens infra/health kører. Måling #2: sluk indre liv, se om cutoff/lag falder ved fast provider.

---

## 17. HVAD CENTRALEN IKKE ER (ærligt — det du bad om)

- **Ikke en anden sandhedskilde.** Læser projektioner; `central_learning` nægter at persistere afledt degradering tilbage i incidents.
- **Ikke en håndhævelses-monolit.** Af 14 decide-sites håndhæver **kun 4** (security-lukkede). Resten fail-open/observe.
- **Ægte SHADOW / OFF (live-verificeret 4. jul):** `central_arbitration` (arbitrerer IKKE — hårdkodet `observe_shadow`, intet flag; konflikt løses af kode-rækkefølge), layer-`decide()`-modes (`layer_mode:*` off).
- **LIVE (ikke shadow — ground-truth mod container 4. jul, RETTELSE):** `central_adaptation` Lag 4 (`central_lag4_live_enabled`=**True**, ikke pauset; bias 0.0188, track-record 4737/454 ≈ 91%), `central_gut_consumer_mode`=**'on'** (gut-gate håndhæver reelt på lært confidence — ikke længere teater), `central_agenda` autoritet=**True** (bærer Jarvis' agenda).
- **Rent observe-only (agerer aldrig):** coverage, causal_quality, learning (proposals), drift (flags), loop_lag, cache_telemetry.
- **Defineret-men-inert:** `central_output_conservation` (0 callers), `central_llm_egress` (dækning langt smallere end docstring).
- **Papercuts:** self-model-navne-sprawl (central_self_model / central_self_state / central_self_observe / runtime_self_model / self_model_blind_spots / … — let at gribe den forkerte); in-memory-tab ved restart (timeserier/drift-baselines/loop_lag-samples); `connections.unauthorized` (SECURITY) uden for CLUSTER_PRIORITY.

---

## 18. Flag-reference (live-tilstand — verificeret mod container 4. jul)

> **Metode-note:** "Live nu"-kolonnen er læst direkte fra runtime-state på containeren (`get_runtime_state_value`), IKKE fra kode-defaults. En tidligere version læste defaults og fik tre rækker forkert (lag4/gut/agenda) — nu rettet.

| Flag | Kode-default | Live nu | Effekt |
|---|---|---|---|
| `central_self_prompt_enabled` | OFF | **True** | D4: prompt bæres fra midten |
| `central_form_judge_mode` | off | **'on'** | spring redundante daemon-LLM-kald over |
| `central_inner_life_ablation` | False | False | (måle-kontakt, off = livet kører) |
| `central_agenda_authoritative_enabled` | OFF | **True** ⚠️RETTET | agenda-autoritet **LIVE** — Centralen bærer agendaen |
| `central_lag4_live_enabled` | False | **True** ⚠️RETTET | adaptation-bias **LIVE** (0.0188, track-record ≈91%) |
| `central_gut_consumer_mode` | off | **'on'** ⚠️RETTET | gut-gate håndhæver reelt på lært confidence |
| `dream_bias_enabled` | True | **True** | drømme biaser loop_persistence m.m. |
| `layer_mode:*` | off | off (None) | føle-lag decide() inaktiv (observe kører) |

---

## 19. Live tal-snapshot (4. juli 2026)

- **122 nerver** · 21+ clusters (5 security) · 0 open breakers (typisk).
- **Connectivity: 819 services, 451 KOBLET, 41 FRAKOBLET+LLM (spild), 50 DARK, 277 STILLE.**
- **Token-burn: $0,028/dag** (98,5% cache-hit, form-dommer on). cheap-lane 5097 gratis kald/dag.
- **Loop-lag (api): ~0,1-18ms** tomgang, 1+ spike ≥250ms fanget siden restart.
- **Cutoffs siden måle-lag live: 0 survival**, ærlig degradering; korrelations-data akkumulerer.
- **interlanguage: 6.188 udtryk, 3.306 hypoteser med notation** (Jarvis' tal; udtryk er mood-biaset komposition, ikke event-aflæsning).

---

*Denne dokumentation er grounded i kode og ærlig om hvad der er live vs shadow vs stub. Hvor Jarvis' skelet var poetisk, er dette verificeret. Hvor noget er ufærdigt (arbitration, adaptation, conservation-wiring, egress-dækning), står det her — for et system der skjuler sine huller kan ikke governes.*
