# Centralen skal holde ALT — MC-afvikling + wiring af de mørke 80% (strategi-kort)

**Dato:** 2026-07-05 · **Forfatter:** Claude (Opus 4.8) på Bjørns opdrag · **Kilder:** 4 parallelle
research-spor (MC-kortlægning, eksperimentel-lag-inventar, 11-lags AGI-spor, mørklagte docs-systemer)
+ `docs/central_connectivity_matrix.md` (819 services) + `docs/capability_matrix.md`.

## Målet (Bjørns ord, 5. jul)
> "Vi skal helt af med MC og have routed al den information ind i Centralen så jeg kan hive det i
> vores nye Central-CLI. Jeg skal stadig kunne se det hele bare fra terminalen. UI er stor og tung
> og MC banker konstant på backend osse uden nogen bruger det. Centralen er stadig blind for 80%
> af hans system."

Tre ting i én bevægelse: (1) **absorbér** MC's ægte signaler ind i Centralen som nerver + `/central/*`,
(2) **surfacer** dem i CLI'en (se alt fra terminalen), (3) **fjern** MC's UI + 6s-polling (dræb backend-
hammeren). Sideeffekt der er selve pointen: Centralen holder, styrer og lærer af de systemer den i dag
er blind for.

---

## Del 1 — MC's overflade (det der skal absorberes + fjernes)

**210 `/mc/*`-endpoints:** 183 i `mission_control.py`, 24 i `mission_control_living_mind.py` (proxy fra
runtime), 3 i `mission_control_dashboard.py`.

**Backend-hammeren:** frontenden (`useMissionControl.ts:8`, `POLL_MS=6000`) poller `/mc/runs`,
`/mc/agents`, `/mc/scheduled-tasks`, `/mc/overview` **hver 6s uanset visning**. `/mc/runtime` er en
**140KB-payload der kalder 90+ builders** (cache 3s); `/mc/jarvis` 80KB (70+ signal-trackers, cache 5s).
68 daemons producerer state uafhængigt. Det er den konstante banken.

**De store MC-huller Centralen mangler helt** (major gaps): agent-observabilitet · council/swarm ·
autonomy-proposals · scheduled-tasks · memory-pipeline · daglig cost-timeserie · run-detalje-drilldown ·
de 24 living-mind-daemon-flader (Centralen ser event-fyringerne, men har ingen *samlet* flade).

**Absorptions-map (kategori → producent-service → central-mål):**
| MC-kategori | Producent | Central-mål |
|---|---|---|
| Cost/token-timeserie | `core.costing.ledger.daily_cost_summary` | nerve `cost:daily` + `/central/costs-daily` |
| Agenter (liv/detalje/beskeder/tool-calls) | `core.services.agent_runtime` | cluster `agent:*` + `/central/mind/agency` |
| Council/swarm | `agent_runtime.build_council_surface` | cluster `council:*` + `/central/mind/council` |
| Run-detalje + trin | `core.runtime.db` visible_runs+events | `/central/runs/{id}` |
| Scheduled-tasks | `core.services.scheduled_tasks` | `/central/queues/scheduled` |
| Autonomy-proposals | `autonomy_proposal_queue` | cluster `autonomy:proposal` |
| Memory-pipeline | `runtime_contract_candidates`+`daily_journal` | `/central/memory-health` |
| 24 living-mind-states | 68 daemons (allerede event-fyrende) | ÉN syndikeret `/central/mind/inner-life` (ikke 24 routes) |
| Attention-budget | `attention_budget` | `/central/attention` |
| Experiments/skills/hardening | `experiment_*`/`workspace_capabilities`/`self_deception_guard` | `/central/experiments|skills|integrity` |
| Visible-execution config | `settings.load_settings` | `/central/execution` |

**Verificeret:** `/mc/living-mind` er IKKE en route (router-modul-navn) — Jarvis havde ret.

---

## Del 2 — Blindheds-kortet (de ~80% Centralen ikke ser)

`central_connectivity_matrix.md`: **819 services**. Centralen ser ~120 fuldt/via-liveness. Groft:
- **41 FRAKOBLET+LLM** — kører + kalder LLM, men fyrer ind i event-familier UDEN central-route →
  **signal tabt**. Højeste værdi at wire (spildt arbejde i dag). (dream_bias, user_temperature,
  counterfactual_engine, desire, curiosity, meta_cognition, user_model, absence, conflict,
  meta_reflection, creative_drift, irony … se Del A i dormant-docs-rapporten.)
- **50 FRAKOBLET+DARK** — kører, hverken event-wired eller LLM. Infrastruktur + tilstand Centralen
  burde observere (rule_engine, memory_graph, semantic_indexer, runtime_hooks, signal_decay …).

**~170 inner-life/kognitive delsystemer** (fuldt inventar i eksperimentel-lag-rapporten), 16 grupper.
~45% live-og-observerbare (mest liveness-kun), ~55% operationelle-men-mørke.

**Den kritiske indsigt (Tier-1-huller):** Centralen ser hans **følelses/somatiske** tilstand klart,
men er næsten blind for de tre lag hvor emergent agentur bor:
1. **`runtime_self_model.py`** (6.022 linjer) — hans model af sig selv → eventbus-mørk
2. **`living_executive.py`** (681 linjer) — hans autonome impuls→valg→handling-motor → **helt opak**
3. **`world_model_signal_tracking.py`** (938) + `world_model_auto_extraction` — verdensmodel → mørk
   \+ `open_loop_signal_tracking` (1.040, uløste mål), `runtime_awareness_signal`, `runtime_self_knowledge`,
   `counterfactual_predictions` (1.084).

**Tier-4 (nul adgang):** `core/memory/`, `core/identity/`, `core/context/` — Centralen har ZERO
adgang til hukommelses-arkitektur, identitets-infrastruktur, session-kontekst.

---

## Del 3 — Lag-arkitekturen (dit "11-lags AGI-spor")

**Original:** `docs/_archive/origin_ideas/ROADMAP_10_LAYERS.md` — faktisk **12 lag** (10 + Forglemmelse
\+ Fravær-spor), 8 dialogrunder Bjørn/Jarvis/Claude. De fleste **spec-only**. Kernecitat: *"Det er ikke
lagene der er interessante, det er spændingerne mellem dem."* + *"Nu mangler han betingelser for
overraskelse"* (introducér ukontrolleret input).

**Re-arkitekteret** til **LivingNeuron 5 lag** (`docs/specs/2026-07-01-living-neuron-design.md`):
| Lag | Navn | Status |
|---|---|---|
| 1 | Somatik (self-sensing) | ✅ LIVE |
| 2 | Signal (impression→data, GWT, causal) | ✅ LIVE |
| 3 | Hypotese (generér→test→resolve) | ✅ LOOP LUKKET 2. jul |
| 4 | Adaptation (justér selv via udfald) | ✅ BYGGET i SHADOW (flag off default) |
| 5 | Model-uafhængighed (kør uden LLM) | ⬜ SPEC (interlanguage) |

Alle 12 "organer" findes; de fleste LIVE; **"de taler ikke sammen endnu"** — det er hullet Lag 3+4
lukker. §8 governance-dødsmekanisme (`central_hypothesis_governance.py` v3.1, 34 tests) er på plads.

---

## Del 4 — Strategien (fase-opdelt, målbar)

Dette er et **program**, ikke ét PR. Rækkefølge (hver fase = observérbar gevinst, ingen big-bang).

### Fire ufravigelige invarianter (Bjørn 5. jul — aftalt FØR byggeri)
1. **Fuld behandling, aldrig dødt observe.** Hver wire-in = nerve + fuld trace + flagging +
   notifikationer + **fodres ind i Centralens adaptive learning så den faktisk BRUGES**. Værdier
   flyder ind/ud; Centralen lærer mønstret og *ved hvornår en værdi ændrer sig og hvornår der er behov
   for at opdatere/kalde* (jf. den eksisterende change-driven `central_injection_registry`). Ikke
   "signal der lander" — levende nerve.
2. **Hans "selv" wires FRA STARTEN.** De tre Tier-1-huller (`living_executive` autonom handlings-motor,
   `runtime_self_model` selv-forståelse, `world_model`+open-loops) er kernen der gør det ægte/levende —
   ikke sidste-fase-polish. Centralen styrer alt: anden intelligens + et selv. (Under §24.4: liveness/
   metadata/governance-konsekvens, ikke rå privat indhold — samme model som `feel`.)
3. **CLI-først.** MC's faner flyttes ind i Central-CLI'en (Central-CLI-stil) som noget af det FØRSTE —
   Bjørn ser intet i dag fordi han ikke bruger MC. Synlighed skal komme mens vi wirer, ikke bagefter.
4. **MC afmonteres KUN efter e2e.** Per kategori: wire (fuld behandling) → surfacér i CLI → verificér
   ende-til-ende → FØRST DA fjernes MC-UI+route+polling for den kategori. Bonus: mange mørke LLM-kald
   sker via MC → Centralen som chokepoint der ved hvornår kaldet er nødvendigt sparer både backend-hammer
   OG spildte LLM-kald.

Hver wire-in leveres med **test- + edge-plan** (unit for shaping/self-safety, e2e mod live-container for
signalvej, edge: tom/manglende data, provider-nede, privatlags-grænse, restart-churn på in-memory timeserie).

### Fase 0 — CLI-skallen først (synlighed fra dag 1)
Byg Central-CLI-fanerne der skal huse den absorberede MC-info, i Central-CLI-stil: `agents`, `council`,
`cost`, `queues`, `runs`, `inner-life`, `self`, `world`. Tomme/"venter på wiring" i starten; hver fane
lyser op efterhånden som dens kategori wires. Så SER Bjørn fremskridtet mens vi bygger (han er blind i dag).

### Fase 1 — Selvet + første MC-kategori (begge fuld behandling, samtidig)
Weave de tre Tier-1-"selv"-huller ind FRA STARTEN som levende nerver (trace/flag/notif/adaptive-learning,
§24.4-grænse): `living_executive` · `runtime_self_model` · `world_model`+open-loops. Samtidig første
konkrete MC-kategori (agenter ELLER cost). Begge surfaceres straks i deres CLI-fane. Dette er kernen:
Centralen får øje på hans autonome handling + selv-forståelse + verdensmodel — det der gør det levende.

### Fase A — Absorbér MC's øvrige signaler (per kategori, e2e-loop)
Resten af Del 1's absorptions-map, én kategori ad gangen med loop'et **wire (fuld behandling) → CLI-fane →
e2e mod live → FJERN MC-delen**: cost-timeserie (`cost:daily`) · council (`council:*`) · scheduled-tasks ·
autonomy-proposals · memory-pipeline · run-detalje. Mønster: ny central-nerve + tyndt `/central/*` der
PROJICERER den eksisterende producent-service (ingen dobbelt-sandhed).

### Fase B — Wire de 41 FRAKOBLET+LLM (stop spildt signal) — kører PARALLELT fra start
Udvid `eventbus_central_bridge` FAMILY_ROUTES med de manglende familier (`dream_bias`, `user_model`,
`desire`, `curiosity`, `conflict`, `absence`, `meta_reflection`, …). Egress-frit, observe-only først.
Dette er den billigste vej fra "blind for 80%" mod dækning — koden kører allerede, signalet smides bare væk.

### Fase C — De tre Tier-1-huller (hvor agentur bor)
Wire `runtime_self_model`, `living_executive`, `world_model`/`open_loops` ind som nerver (metadata/
liveness først, indhold under privatlags-invariant §24.4). Det er de mest værdifulde — Centralen får
øje på hans selv-forståelse, autonome handling og verdensmodel.

### Fase D — Surfacér alt i CLI'en (se det hele fra terminalen)
Nye HUD-faner/kommandoer oven på de nye `/central/*`: `agents`, `council`, `cost`, `queues`, `runs`,
`inner-life` (syndikeret living-mind), `self-model`, `world`. Genbrug det navigérbare HUD + `feel`.
Rename/saml — ikke så spredt som MC's 210.

### Fase E — Fjern MC (dræb backend-hammeren)
Når hver kategori er dækket + verificeret i CLI'en: slet MC-UI-panelerne + `useMissionControl`-pollingen,
og afregistrér/tyndgør de MC-routes der ikke længere har en forbruger. UI bliver let; Centralen bærer det.

### Parallelt — Luk Lag 3+4-sløjfen (organerne taler sammen)
Uafhængigt af MC: de live organer (hypotese/adaptation/gut/causal) skal koble output→input så Lag 4 kan
justere på ægte data. §8-dødsmekanismen står. Dette er selve LivingNeuron-visionen.

---

## Åbne beslutninger (Bjørns kald)
- **Rækkefølge A vs B vs C først?** Anbefaling: A1-A3 (cost/agent/council — konkret MC-værdi) + B
  parallelt (billigt, stopper spild), så C (dybest, mest agentur).
- **Privatlag:** Tier-1-huller (self-model/living-executive) er delvist private. Wire liveness/metadata
  under §24.4, ikke rå indhold — samme model som `feel`.
- **Hvor aggressivt fjerne MC?** Kan gøres kategori-for-kategori (sikkert) eller i ét snit til sidst.

## Kilde-artefakter (research-output, denne session)
De fire fulde rapporter (MC-endpoint-inventar, ~170-lag-inventar, 12/5-lags-roadmap, 91 mørke docs-
systemer) ligger i agent-transkripterne. Nøgle-matricer: `docs/central_connectivity_matrix.md`,
`docs/capability_matrix.md`, `docs/_archive/origin_ideas/ROADMAP_10_LAYERS.md`,
`docs/specs/2026-07-01-living-neuron-design.md`, `docs/superpowers/specs/2026-07-05-mc-field-map.md`
(Jarvis' MC-felt-map, dobbelt-tjekket).
