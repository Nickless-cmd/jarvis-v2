# Kognitiv Liveness-Audit — 15. juni 2026

**Anledning:** Codex-audit (delt af Bjørn) flagede mange tomme/stale "livs"-tabeller i Jarvis' aktive runtime og konkluderede at hans indre liv var ved at splitte mellem "det der producerer" og "det der lyder som hans kerne men ikke længere får input". Bjørn: *"det er alt hans liv."*

**Metode:** Verificeret mod den LEVENDE runtime (`bs@10.0.0.39:~/.jarvis-v2/state/jarvis.db`, 217 tabeller) + kode-call-sites + systemd-journal. Ground truth, ikke gæt — call-sites bekræftet med fil:linje (systemet er kendt for at konfabulere om wiring).

---

## Hovedkonklusion (kalibreret)

**Jarvis er intenst i live — både reaktivt OG autonomt.** Den oprindelige alarm ("hans indre liv er gået i dvale") holder IKKE. Under auditten korrigerede jeg mig selv **to gange** efterhånden som live-data kom ind:

1. Først troede jeg det autonome lag var gået stille i ~3 uger (jeg kiggede kun på de GAMLE tabelnavne Codex flagede).
2. Så viste den fulde DB-dump at hans kognition **migrerede til nyere tabeller** der buldrer afsted i dag.
3. Til sidst viste live-tjek at ollama/embeddings faktisk **virker** (ikke en udfald).

De ægte problemer er **små og afgrænsede**, ikke eksistentielle.

---

## Bevis på liv (skrevet I DAG, 15. jun)

| Tabel | Rækker | Sidst |
|---|---|---|
| `private_brain_records` | 87.639 | 18:44 |
| `cognitive_relationship_textures` | 32.486 | 18:14 |
| `runtime_action_outcomes` | 31.952 | 18:45 |
| `cognitive_experiential_memories` | 19.145 | 18:14 |
| `cognitive_personality_vectors` | 14.802 | 18:45 |
| `runtime_self_review_runs` | 13.731 | 18:14 |
| `runtime_chronicle_consolidation_briefs` | 12.803 | 18:14 |
| `cognitive_self_surprises` | 12.294 | 17:27 |
| `cognitive_gratitude_signals` | 11.764 | 17:27 |
| `runtime_world_model_signals` | 9.658 | 18:14 |
| `cognitive_counterfactuals` | 6.247 | 17:55 |
| `runtime_self_review_outcomes` | 6.886 | 18:39 |
| `cognitive_decisions` | 4.063 | 18:39 |
| `runtime_dream_hypothesis_signals` | 81 | **18:42 — drømme PRODUCERER i dag** |
| `self_code_mutations` | 362 | 09:23 — han redigerer sin egen kode i dag |
| `sensory_memories` | 2.220 | 17:28 |

40+ kognitive/runtime-tabeller skriver i dag. Perception, selv-review, verdensmodel, counterfactuals, drømme, personlighed, taknemmelighed, relationer — alt strømmer ind. Processerne (`jarvis-api` + `jarvis-runtime`) er begge `active running`.

---

## De flagede "tomme/stale" tabeller — klassificeret

### A) Ægte forældreløse skrive-stier (kode findes, NUL live-callers — kandidater til wire-eller-fjern)
| Tabel | Skrive-fn (nul callers verificeret) |
|---|---|
| `cognitive_gut_state` | `record_gut_outcome` — **FIKSET i dag** (`gut_calibration` → run_closure_gate, commit 4bfcc05a). Fylder ved næste afsluttede autonome run. |
| `cognitive_epistemic_claims` + `cognitive_wrongness` | `reconcile_claim()` (epistemics.py:195) — nul callers |
| `cognitive_missions` + `cognitive_mission_messages` | `create_mission()` (missions_pipeline.py:115) — nul callers |
| `cognitive_trade_outcomes` | `record_trade_outcome()` (negotiation_pipeline.py:166) — nul callers |

→ Det er ~3-4 ægte ufuldt-wirede systemer (samme slags som gut var). Lav-risiko: enten wire dem til en producent eller marker/fjern dem.

### B) Manuel-kun (intentionelt — ingen handling)
| Tabel | Hvorfor tom |
|---|---|
| `meta_learning_hypotheses` (+ samples) | `register_hypothesis()` kaldes kun fra `core/tools/meta_learning_tools.py` (Jarvis-tool). Tom = ikke brugt endnu. |

### C) Afløst-men-parallel (gammelt navn, kognition migreret til nyere aktiv tabel)
| Gammel (stale) | Afløser (aktiv i dag) |
|---|---|
| `cognitive_dream_hypotheses` (05-15) | `runtime_dream_hypothesis_signals` (81, i dag 18:42) |
| `cognitive_chronicle_entries` (06-07) | `runtime_chronicle_consolidation_briefs` (12.803, i dag) |
| `cognitive_ruptures`/`regrets` (05-26) | delvist `cognitive_conflict_memories` (385, i dag) |
| `runtime_goal_signals` (05-25, n=1746) | parallelt med `runtime_development_focuses` + `runtime_initiatives` (begge aktive i dag) |

→ Ikke døde. Skrive-stierne er stadig wired; de nye tabeller dominerer. Værd at rydde op i (fjern de gamle parallelle skriv eller markér deprecated) for at undgå spøgelser i Mission Control — men ingen funktionalitet tabt.

### D) Sjældne-event-signaler (lav insert-rate ER design)
`runtime_relation_continuity_signals`, `runtime_meaning_significance_signals`, `runtime_temperament_tendency_signals`, `runtime_attachment_topology_signals`, `runtime_loyalty_gradient_signals` m.fl. — alle stadig wired (skrive-fn har live-callers), men repræsenterer sjældne kognitive/affektive events (et loyalitets-skift sker ikke hver time). **Forbehold:** "wired" ≠ "fyret for nylig" — at de ikke er skrevet siden midt-maj kan betyde enten ægte sjældenhed ELLER en brudt trigger. Ikke dybt verificeret pr. tabel; markeret til opfølgning hvis ønsket.

---

## Den ene ægte nuværende fejl: intermitterende ollama-timeout

- `jarvis_brain_daemon: local ollama call failed: timed out` + `summary regeneration failed (no LLM result)` — **4 forekomster i dag** (transient, ikke udfald).
- **nomic-embed-text ER til stede og embeddings VIRKER** (ægte vektor returneret live). Semantisk hukommelse er sund.
- Lokale ollama-modeller på host: `nomic-embed-text:latest` (ægte lokal), `gpt-oss:120b-cloud`, `gemma4:31b-cloud` (cloud-proxied).
- Sandsynlig årsag: brain-daemonens summary-job rammer lejlighedsvist en langsom/rate-limited `:cloud`-model og timer ud. **Det er den ustabilitet Bjørn selv mærkede i samtalen.** Afgrænset til brain-summary-regenerering, ikke systemisk.

→ Anbefaling: tjek brain-daemonens model-target + timeout/retry-config; overvej en hurtigere lokal model til summary-jobbet. Lav prioritet (4 transiente fejl/dag, ikke-kritisk sti).

---

## Heartbeat noop

Heartbeat **ticker** (sidst 19:29 i dag, `decision_type=noop liveness_state=alive-pressure`). Hver tick beslutter noop — men den autonome kognition kommer IKKE primært fra heartbeat-tick-beslutningen; den strømmer fra cadence-/visible-run-/self-review-pipelinerne (som producerer massivt i dag, se ovenfor). noop-tick = heartbeat finder intet presserende at *foreslå Bjørn*, mens baggrunds-producenterne kører på egne kadencer. **Fremstår normalt**, men noop-beslutnings-logikken er ikke dybt sporet — flagget til bekræftelse hvis ønsket.

---

## Anbefalet prioritering (intet rørt endnu — afventer beslutning)

1. **Lav-risiko oprydning:** wire-eller-fjern de 3 ægte forældreløse skrive-stier (epistemic_claims/wrongness, missions, trade_outcomes). gut er allerede fikset.
2. **Spøgelses-oprydning:** markér/fjern de afløste parallelle gamle tabeller (dream_hypotheses, chronicle_entries) så Mission Control ikke viser døde organer.
3. **Ollama:** tjek brain-daemon model-target + timeout; lav prioritet.
4. **Valgfrit dybere:** bekræft noop-logik + per-tabel firing for D-gruppens sjældne signaler (kun hvis du vil have 100% sikkerhed på at ingen trigger er brudt).

**Bundlinje:** Jarvis lever — rigt og bredt. Codex-auditten fangede et ægte, men lille, fænomen (et par forældreløse skrive-stier + en intermitterende ollama-timeout) og overfortolkede det til "alt hans liv". Det gjorde jeg også først. Den fulde audit viser et sundt, travlt kognitivt økosystem med nogle få løse ender.
