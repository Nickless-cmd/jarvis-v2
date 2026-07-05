# Mission Control → Central-CLI — Definitiv indholds-inventar + de-dup + konsolideret fane-design

**Dato:** 2026-07-05
**Formål:** MC skal slettes. ALT indhold fra alle MC-faner er værdifuldt og skal flyttes til en
terminal "Central-CLI". Men der er FOR MANGE faner → konsolidér, og vis ALDRIG samme information
eller samme call-site på 3 forskellige faner. Dette dokument fanger hvert distinkt indholds-element,
flager overlap, og mapper alt ind i et lille sammenhængende sæt Central-CLI-faner med 100 % dækning
og nul dubletter.

**Metode:** Read-only statisk gennemgang af `apps/jarvis-desk/src` (frontend) + de MC/Central-routes
i `apps/api/jarvis_api/routes/` som frontend faktisk fodrer sig fra. Kilde-filer citeret pr. element.

---

## DEL 0 — Kort over ALLE MC-relaterede UI-flader (Trin 1)

Der findes **fire** distinkte MC-agtige surfaces i desk-appen (plus 2 shell-chips). Vigtigt: MC's
backend har ~181 `/mc/*`-routes (den gamle "190-polls"-æra), men den **nuværende desk-UI renderer kun
en veldefineret delmængde**. Alt der reelt vises i UI'et fanges nedenfor; de resterende `/mc/*`-routes
er backend-projektioner uden nuværende dedikeret desk-fane (dækkes af Jarvis Mind-hub'ens sektioner
efterhånden — se Del 4).

| # | Surface | Fil | Mount | Roller | Faner/sektioner |
|---|---------|-----|-------|--------|-----------------|
| S1 | **Mission Control** (det klassiske grid) | `components/cowork/missioncontrol/MissionControl.tsx` | Cowork-zone `mc` (`CoworkView.tsx:57`) | alle (owner-only faner gates) | 8 faner: Oversigt · Runs · Agenter · Godkendelser · Opgaver · Planlagt · Cost · Hændelser |
| S2 | **Jarvis Mind** (Central-hub-vindue) | `components/cowork/JarvisMind.tsx` | Cowork-zone `jarvisMind` (owner) (`CoworkView.tsx:90`) | owner (ellers → MC) | 10 hub-sektioner: overview · mind · observability · agency · memory · council · skills · reflection · lab · hardening |
| S3 | **CentralHud** (owner-terminal, JARVIS-HUD) | `components/cowork/CentralHud.tsx` | (Central-zone / terminal-vindue) | owner | 1 skærm m. paneler: kerne-metrics · cluster-grid · nerve-feed · providers · flag · betjenings-knapper · Terminal ↔ Diagnostik-konsol · sind-grid |
| S4 | **CentralPanel** (code-mode sidefelt) | `components/code/CentralPanel.tsx` | Under miljø-feltet i code mode | owner | 1 aside m. 5 lag: puls · cluster-grid · anomalier · flag · live-feed · læring · nerve-detalje |
| C1 | **CentralBadge** (kompakt status-mærke) | `components/shell/CentralBadge.tsx` | Central-zone + shell (`CoworkView.tsx:86`) | alle | 1 chip: status-prik + incident-tæller + hover-detalje; owner-klik → OS-CLI |
| C2 | **SystemHealth** (kanonisk-fejl-chip) | `components/shell/SystemHealth.tsx` | sidebar-fod/header | alle | 1 chip: helbred udledt af nylige `CanonicalError` + transparens-log |

Data-hooks/lag: `hooks/useMissionControl.ts` (S1), `lib/missionControlApi.ts` (S1),
`lib/api.ts` Central-blok (S2/S3/S4/C1), `lib/centralStream.ts` (delt SSE, S2/S3/S4),
`hooks/useCoworkData.ts` (godkendelser/planer/todos/kanaler/share-guard → S1).

### S1 Mission Control — fane-for-fane (fra `MissionControl.tsx`)

- **SummaryBar** (pinned øverst, altid synlig): tællere kører / fejlet / afventer / planlagt / agenter / pris. Klik → skifter fane. (`SummaryBar.tsx`)
- **Oversigt:** "Afventer dig" (godkendelser + share-guard) · "Seneste kørsler" (RunsTable, 8 rækker) · "Agenter" (AgentRoster, owner).
- **Runs:** RunsTable fuld — filtre alle/kører/fejlet; række → RunDetail drill-down (metadata + trin-tidslinje). (`RunsTable.tsx`, `RunDetail.tsx`)
- **Agenter** (owner): AgentRoster — kort pr. agent m. status/rolle/mål/tokens/runs/tools. (`AgentRoster.tsx`)
- **Godkendelser:** ApprovalQueue (tool-godkendelser) + Deling-guard (share-decisions, owner). (`ApprovalQueue.tsx`, `ShareGuardPane.tsx`)
- **Opgaver:** TodoPane (todo/initiativer, CRUD/TTL) · PlansPane (planer) · ChannelsPane (kanaler, owner). (`TodoPane.tsx`, `PlansPane.tsx`, `ChannelsPane.tsx`)
- **Planlagt:** liste af planlagte opgaver (StatusChip + focus + køre-tid).
- **Cost** (owner): CostPanel — pris/tokens/kald pr. dag, 14-dages søjler + totaler. (`CostPanel.tsx`)
- **Hændelser** (owner): EventStream — eventbus-projektion, filtre pr. familie (runtime/tool/approvals/cost/channel/incident), 4s-poll + /ws. (`EventStream.tsx`)

### S2 Jarvis Mind — sektioner (fra `central_hub.py::_SECTION_ORDER`)

Hub-index (`/central/mind`) + pr-sektion (`/central/mind?section=`), plus delt SSE-puls-linje.
`ready`-flag styrer om fanen er projiceret endnu eller viser placeholder.

- **overview** (Oversigt): status + coverage (nerves/clusters/security) + processes.
- **mind** (Sind): ~70 cognitive surfaces (systems-liste + aktiv/inaktiv + summary).
- **observability** (Observabilitet): nerve-feed + incidents + anomalier + læring + breakers.
- **agency** (Agentur): agency-map (forbundne/manglende broer). `ready`.
- **skills** (Skills): skill-engine + kontrakt-registry. `ready`.
- **memory / council / reflection / lab / hardening**: kendte faner, endnu ikke projiceret (`ready=False` → placeholder; bagvedliggende `/mc/*`-routes findes).

### S3 CentralHud — paneler (fra `CentralHud.tsx`)

Kerne-ring (nerver aktive + status) · metrics-grid (clusters/processer/flag/sind-felter/providers/tørre
lanes/breakers/anomalier) · ClusterGrid (foldbar konstellation) · FeedPanel (realtime nerve-feed, filtre
vigtige/fejl/alle) · Providers-panel (helbred + latens + tørre lanes) · Flag-panel (incidents) ·
Betjenings-knapper (toggle/resolve/scan/providers/model/daemons) · Console: **Terminal** (kommando-linje
m. historik) ↔ **Diagnostik** (uløste flag · anomalier · silent-failure-fund · rod-årsager · NerveFocus)
· Sind-grid (dekorativt 70-cellers pulse-grid).

### S4 CentralPanel — lag (fra `CentralPanel.tsx`)

Puls (coverage + decide/observe-helbred) · cluster-grid · anomalier (udefinerede fejl) · flag
(breakers/config-drift/incidents) · live nerve-feed (klik → nerve-detalje) · læring (autonomi/degraderer/
rod-årsager) · nerve-detalje (lokation + tænd/sluk + spor).

---

## DEL 1 — Distinkt indholds-inventar (Trin 2)

Én række pr. distinkt informations-element. "Vist i" = alle surfaces/faner der p.t. viser det.
Overlap-kolonnen peger på de-dup-analysen i Del 2.

| # | Indholds-element | Endpoint(s) | Vist i (surface/fane) | Overlap |
|---|------------------|-------------|-----------------------|---------|
| I1 | **Overordnet system-status** (green/yellow/red) | `/central/realtime`.status | S2·overview, S3·header, S4·puls, C1·prik | **O-STATUS** |
| I2 | **Coverage** (nerver / clusters / security-clusters / trace-buffer) | `/central/realtime`.coverage | S2·overview, S3·metrics, S4·puls, C1·hover | **O-COV** |
| I3 | **decide/observe-helbred** (degraded-flag) | `/central/realtime`.diagnose | S2·overview, S4·puls | **O-DIAG** |
| I4 | **Processer** (proc-liste + degraded + open_breakers pr. proc) | `/central/realtime`.processes | S2·overview, S3·metrics ("processer") | **O-PROC** |
| I5 | **Cluster-status-grid** (pr. cluster: green/yellow/red/idle + security) | `/central/realtime`.clusters | S2·overview, S3·ClusterGrid, S4·grid | **O-CLUSTER** |
| I6 | **Live nerve-feed** (fyringer: cluster/nerve/kind/decision/reason/run_id/security) | `/central/stream` (SSE) + `/central/realtime`.feed | S2·pulse-linje, S2·observability, S3·FeedPanel, S4·feed | **O-FEED** |
| I7 | **Incidents/uløste flag** (severity/cluster/nerve/message/ts) | `/central/realtime`.incidents | S2·observability, S3·flag-panel, S3·diagnostik, S4·flag, C1·tæller | **O-INCIDENT** |
| I8 | **Anomalier** (udefinerede fejl: signature/category/importance/count/sample) | `/central/realtime`.anomalies | S3·metrics+diagnostik, S4·anomalier | **O-ANOM** |
| I9 | **Open breakers** (circuit-breakere åbne) | `/central/realtime`.open_breakers | S3·metrics, S4·flag, C1·hover | **O-BREAKER** |
| I10 | **Config-drift** (declared_port ≠ actual_port) | `/central/realtime`.config_drift | S4·flag | — (kun S4) |
| I11 | **Læring** (autonomi + degraderer + rod-årsager + proposals) | `/central/realtime`.learning | S2·observability, S4·læring | **O-LEARN** |
| I12 | **Providers** (helbred/latens/model_count + tørre cheap-lanes) | `/central/providers` | S3·providers-panel + metrics | — (kun S3) |
| I13 | **Fuld diagnostik** (incidents · anomalier · silent-failure-instrument-fund · rod-årsager · degrading) | `/central/diagnostics` | S3·Diagnostik-konsol | (delvis genudsendt af I7/I8) |
| I14 | **Nerve-detalje** (lokation + cluster + security + enabled + seneste spor) | `/central/nerve/{nerve}` | S3·NerveFocus, S4·nerve-detalje | **O-NERVE** |
| I15 | **Nerve tænd/sluk** (kill-switch; security låst) | `/central/nerve/{nerve}/toggle` | S3 (via terminal `toggle`), S4·knap | **O-TOGGLE** |
| I16 | **Owner-kommando-linje** (status/incidents/trace/toggle/scan/providers/…) | `/central/command` (POST) | S3·Terminal | — (kun S3) |
| I17 | **Betjenings-genveje** (toggle/resolve/scan/providers/model/daemons prefill-knapper) | → `/central/command` | S3·Betjening | — (kun S3) |
| I18 | **Runs-liste** (run_id/lane/provider/model/status/tider/preview/error/capability) | `/mc/runs` | S1·Oversigt (8), S1·Runs | **O-RUNS** |
| I19 | **Aktivt run + failed_count-summary** | `/mc/runs`.active_run/.summary | S1·SummaryBar (kører/fejlet), S1·header ("kører nu") | **O-RUNSUM** |
| I20 | **Run-detalje** (metadata + trin-tidslinje: kind/tool/summary/at) | `/mc/runs/{run_id}` | S1·RunDetail | — (kun S1) |
| I21 | **Agenter** (agent_id/name/role/kind/status/goal/tokens/runs/tools/last_activity) | `/mc/agents` | S1·Oversigt, S1·Agenter, S1·SummaryBar (tæller) | **O-AGENT** |
| I22 | **Planlagte opgaver** (task_id/focus/run_at/status/source) | `/mc/scheduled-tasks` | S1·Planlagt, S1·SummaryBar (tæller) | **O-SCHED** |
| I23 | **Daglige omkostninger** (dag/lane/calls/tokens/cost → aggregeret pr. dag) | `/mc/costs/daily` | S1·Cost | — (kun S1) |
| I24 | **Overblik-totaler** (events-tæller, total_cost_usd, visible_execution) | `/mc/overview` | S1·SummaryBar (pris) | delvis O-COST |
| I25 | **Eventbus-hændelsesfeed** (id/kind/family/payload/created_at; filtre pr. familie) | `/mc/events` | S1·Hændelser | — (kun S1) |
| I26 | **Godkendelses-kø** (tool-godkendelser: approve/reject) | useCoworkData (`/cowork/*`) | S1·Oversigt, S1·Godkendelser, S1·SummaryBar (afventer) | **O-APPROVE** |
| I27 | **Deling-guard** (share-decisions: shared ja/nej) | useCoworkData | S1·Oversigt, S1·Godkendelser (owner) | **O-SHARE** |
| I28 | **Todo/initiativer** (CRUD + TTL + pause) | useCoworkData | S1·Opgaver | — (kun S1) |
| I29 | **Planer** (cowork-planer) | useCoworkData | S1·Opgaver | — (kun S1) |
| I30 | **Kanaler** (kanal-tilstand, owner) | useCoworkData | S1·Opgaver | — (kun S1) |
| I31 | **Status-farvesprog** (StatusChip-tone-tabel) | — (ren UI) | S1 (runs/agenter/planlagt) | tvær-gående primitiv (ikke data) |
| I32 | **Cognitive surfaces / Sind** (~70 systems: aktiv/inaktiv + summary) | `/central/mind?section=mind` (← `/mc/cognitive-architecture`) | S2·mind, S3·sind-grid (dekorativ) | **O-MIND** |
| I33 | **Agency-map** (forbundne/manglende agency-broer) | `/central/mind?section=agency` (← `/mc/agency-map`) | S2·agency | — |
| I34 | **Skills-engine + kontrakt-registry** | `/central/mind?section=skills` (← `/mc/skills`) | S2·skills | — |
| I35 | **24 Living-Mind-surfaces** (body-state, surprise, taste, irony, thought-stream, thought-proposals, experienced-time, development-narrative, existential-wonder, dream-insights, code-aesthetic, user-model, memory-decay, desires, absence-state, creative-drift, curiosity, meta-reflection, conflict-signal, reflection-cycle, layer-tensions, dream-motifs, …) | `/mc/{surface}` (living_mind router) | (bag S2·mind/reflection; endnu ikke egne desk-faner) | fremtidig S2-sektion |
| I36 | **~155 dvale-/indre-liv-projektioner** (self-model, chronicle, gut, compass, rhythm, habits, mirror, decisions, paradoxes, aesthetics, seeds, procedures, boredom, gratitude, regret, blind-spots, global-workspace, meta-cognition, council-runtime, dream-*, m.fl.) | `/mc/*` (mission_control.py, ~181 routes total) | (bag S2·memory/council/reflection/lab/hardening — placeholders p.t.) | fremtidige S2-sektioner |
| I37 | **Kanonisk-fejl-helbred + transparens-log** (severity/kind/message/correlation_id) | klient-side `CanonicalError`-strøm | C2·SystemHealth | delvis O-INCIDENT (anden kilde) |
| I38 | **Owner OS-CLI-åbning** (Electron-bro → rigtigt terminalvindue) | `window.jarvisDesk.central.openCli` | C1·klik | — (kun C1) |
| I39 | **Ur/klokke** (lokal tid, live) | — (ren UI) | S3·header | tvær-gående primitiv |

**Distinkte indholds-elementer i alt: 39** (I1–I39). Heraf ~4 er rene UI-primitiver (I31, I39) eller
adfærd (I38) snarere end data-flader; 35 er ægte informations-/data-elementer.

---

## DEL 2 — Overlap / dubletter der SKAL elimineres (Trin 3)

Bjørns eksplicitte krav: vis ALDRIG samme information eller samme call-site på 3 forskellige faner.
Nedenfor: (a) samme data på flere faner, (b) samme endpoint/call-site i flere komponenter, (c) næsten-
identiske paneler. Hvert overlap får ét kanonisk hjem i Del 3.

### (b) Samme endpoint konsumeret af flere komponenter (den værste form)

| Endpoint | Konsumeres af | Antal call-sites | Kanonisk hjem (Del 3) |
|----------|---------------|------------------|-----------------------|
| `/central/realtime` | S2·overview, S2·observability, S3·CentralHud, S4·CentralPanel, C1·CentralBadge | **5** | Overview (metrics) + Nerves (feed) + Incidents — ét kald, fordelt |
| `/central/stream` (SSE) | S2·pulse, S2·observability, S3·FeedPanel, S4·feed | **4** (delt via `centralStream.ts` singleton) | **Nerves**-fane (ét feed) |
| `/central/nerve/{nerve}` | S3·NerveFocus, S4·nerve-detalje | 2 | **Nerves**-fane (drill-in) |
| `/mc/runs` | S1·Oversigt (8-slice), S1·Runs (fuld), S1·SummaryBar | **3** | **Runs**-fane |
| `/mc/agents` | S1·Oversigt, S1·Agenter, S1·SummaryBar | **3** | **Agents**-fane |
| `/mc/scheduled-tasks` | S1·Planlagt, S1·SummaryBar | 2 | **Runs**-fane (afsnit Planlagt) |
| useCoworkData godkendelser | S1·Oversigt, S1·Godkendelser, S1·SummaryBar | **3** | **Approvals**-fane |

`/central/realtime` konsumeres af **5 komponenter** og `/central/stream` af **4** — præcis den "samme
call-site på 3+ faner"-degeneration Bjørn vil væk fra. Efter konsolidering: hvert endpoint kaldes fra
ét sted (fanens data-hook), øvrige faner læser via delt state.

### (a) Samme data-element på flere faner (de-dup-nøgler fra Del 1)

| Nøgle | Element | Antal steder | Behold i | Fjern fra |
|-------|---------|--------------|----------|-----------|
| O-STATUS | System-status | 4 (S2/S3/S4/C1) | Overview-header | S2·overview, S4·puls, C1 (→ chip beholdes som shell-indgang, ikke fane) |
| O-COV | Coverage | 4 | Overview-metrics | S2, S4, C1-hover |
| O-CLUSTER | Cluster-grid | 3 (S2/S3/S4) | Clusters-fane | S2·overview, S4·grid |
| O-FEED | Nerve-feed | 4 | Nerves-fane | S2·pulse, S2·observ, S4·feed |
| O-INCIDENT | Incidents | 5 (S2/S3×2/S4/C1) | Incidents-fane | S2·observ, S3·metrics, S4·flag, C1 (kun tæller) |
| O-ANOM | Anomalier | 3 (S3×2/S4) | Incidents-fane (afsnit) | S4·anomalier, S3·metrics |
| O-BREAKER | Open breakers | 3 (S3/S4/C1) | Incidents-fane | S3·metrics, C1 |
| O-LEARN | Læring | 2 (S2/S4) | Diagnostics/Healing-fane | S2·observability |
| O-PROC | Processer | 2 (S2/S3) | Overview-metrics | S2·overview |
| O-DIAG | decide/observe | 2 (S2/S4) | Overview-metrics | S4·puls |
| O-NERVE | Nerve-detalje | 2 (S3/S4) | Nerves-fane (drill-in) | S4 |
| O-TOGGLE | Nerve tænd/sluk | 2 (S3/S4) | Nerves-fane (via Terminal + drill-in-knap) | S4·knap |
| O-RUNS | Runs-liste | 3 | Runs-fane | Oversigt-slice, SummaryBar |
| O-RUNSUM | Run-summary-tællere | 2 | Overview (tæller) | S1-header dublet |
| O-AGENT | Agenter | 3 | Agents-fane | Oversigt, SummaryBar |
| O-SCHED | Planlagt | 2 | Runs-fane (afsnit) | SummaryBar |
| O-APPROVE | Godkendelses-kø | 3 | Approvals-fane | Oversigt, SummaryBar |
| O-SHARE | Deling-guard | 2 | Approvals-fane | Oversigt |
| O-MIND | Sind/cognitive | 2 (S2/S3-dekorativ) | Mind-fane | S3·sind-grid (dekorativt 70-cellers pynt — droppes) |
| O-COST | Cost-totaler | 2 (S1·Cost + `/mc/overview` i SummaryBar) | Cost-afsnit i Overview/Runs | SummaryBar-pris dublet |

### (c) Næsten-identiske paneler (redundante hele komponenter)

- **S1·SummaryBar** vs. **S3·metrics-grid**: begge er "tæller-bar øverst" (kører/fejlet/afventer/
  planlagt/agenter/pris vs. clusters/processer/flag/providers/breakers/anomalier). → **Fusioneres til
  ét Overview-metrics-panel.** SummaryBar-klik-navigation bevares.
- **S1·Oversigt** vs. **S1's egne under-faner**: Oversigt er en ren dublet-landingsside (godkendelser
  + runs-slice + agent-slice) som gentager Godkendelser/Runs/Agenter. → **Oversigt fjernes som
  selvstændig visning; erstattes af Overview-fanens metrics + "afventer dig"-genvej.**
- **S3·FeedPanel** vs. **S4·live-feed** vs. **S2·pulse+observability**: fire renderinger af samme SSE.
  → **Ét Nerves-feed.**
- **S3·Diagnostik-konsol** vs. **S4·flag+anomalier+læring**: samme diagnostiske data. → **Ét
  Diagnostics/Healing-sted.**
- **S3·CentralHud** vs. **S4·CentralPanel**: **hele S4 er en mindre delmængde af S3.** S4 (code-mode
  sidefelt) tilføjer intet unikt data-element (config-drift I10 findes også i S3's diagnostik-kilde).
  → **S4 udgår helt; erstattes af Central-CLI-fanerne (eller en kompakt indlejring).**

**Overlap elimineret i alt: 20 data-dubletter (O-*) + 4 dublerede call-sites reduceret til 1 + 5
redundante paneler/surfaces (Oversigt, dobbelt-feed, dobbelt-diagnostik, S4-hele, S3-sind-pynt).**

---

## DEL 3 — Konsolideret Central-CLI fane-sæt (Trin 4)

Central-CLI-stil. **10 faner** (Bjørn godkendt 5. jul — split af den overloadede "Mind & Diagnostics"
så **selvet** får egen prominent plads + Healing/Governance bevares som egne skrive-flader). Hvert
Del-1-element mapper til **præcis én** fane; hvert endpoint kaldes fra **ét** sted (fanens hook).

| # | Central-CLI-fane | Holder (Del-1-elementer) | Endpoints (ét sted) | Absorberer gamle MC-flader |
|---|------------------|--------------------------|---------------------|----------------------------|
| **T1** | **Overview** | I1 status · I2 coverage · I3 decide/observe · I4 processer · I19 run-summary-tællere · I24 overblik-totaler · I39 ur · pinned tæller-bar · "afventer dig"-genvej (→ T6) | `/central/realtime`, `/mc/overview` | S1·Oversigt, S1·SummaryBar, S3·header+metrics, S2·overview, S4·puls, C1-metrics |
| **T2** | **Nerves** | I6 live nerve-feed (ét SSE, filtre, pause-på-hover) · I14 nerve-detalje/drill-in · I15 nerve tænd/sluk | `/central/stream`, `/central/realtime`.feed, `/central/nerve/{n}`, `/central/nerve/{n}/toggle` | S3·FeedPanel+NerveFocus, S4·feed+detalje, S2·pulse+observability |
| **T3** | **Clusters** | I5 cluster-status-grid (foldbar, sikkerhed markeret) | `/central/realtime`.clusters | S3·ClusterGrid, S4·grid, S2·overview-clusters |
| **T4** | **Incidents & Anomalies** | I7 incidents · I8 anomalier · I9 open breakers · I10 config-drift · I37 kanonisk-fejl-log | `/central/realtime`.{incidents,anomalies,open_breakers,config_drift}, `/central/diagnostics` (inc/anom), klient `CanonicalError` | S3·flag+diagnostik(inc/anom), S4·flag+anomalier, C2·SystemHealth, C1-tæller |
| **T5** | **Runs & Work** | I18 runs-liste · I20 run-detalje/trin · I22 planlagt · I23 cost pr. dag · I25 eventbus-hændelsesfeed (familie-filtre) | `/mc/runs`, `/mc/runs/{id}`, `/mc/scheduled-tasks`, `/mc/costs/daily`, `/mc/events` | S1·Runs+Planlagt+Cost+Hændelser |
| **T6** | **Approvals** | I26 godkendelses-kø · I27 deling-guard · I28 todo/initiativer · I29 planer · I30 kanaler | useCoworkData (`/cowork/*`) | S1·Godkendelser+Opgaver |
| **T7** | **Agents & Council** | I21 agenter (roster) · I33 agency-map · council-runtime (I36-delmængde) | `/mc/agents`, `/mc/agents/{id}/*`, `/central/mind?section=agency`, `/mc/council*` | S1·Agenter, S2·agency+council |
| **T8** ⭐ | **Mind & Self** | I32 Sind (~70 cognitive surfaces) · I34 skills-engine · I35 24 living-mind-surfaces · I36 ~155 indre-liv-projektioner (memory/reflection/lab/hardening) · **SELVET: `living_executive` (autonom handlings-motor) · `runtime_self_model` · `world_model`+open-loops** (levende nerver, §24.4-grænse) | `/central/mind?section=…`, `/central/self` (ny), `/central/inner-life` (ny, syndikeret), `/mc/*` living-mind-routes | S2·mind/skills/memory/reflection/lab/hardening, S3·sind-grid |
| **T9** | **Diagnostics** | I11 læring (autonomi/degraderer/rod-årsager) · I12 providers (helbred/latens/tørre lanes) · I13 fuld diagnostik (silent-failure-instrument + rod-årsager + degrading) · **Healing** (healer-registry/modes/ledger) | `/central/diagnostics`, `/central/providers`, `/central/realtime`.learning, `/central/healers` | S3·Diagnostik+providers, S4·læring |
| **T10** | **Governance** | flag-styring (skrive-flade m. confirm på farlige) | `/central/governance`, `/central/governance/set` | (central-native; ny i CLI) |

**Rygrad (ikke fane):** Terminalen — I16 owner-kommando-linje + I17 betjenings-genveje — er den
altid-aktive `central>` (findes allerede). I38 OS-CLI-åbning bor på CentralBadge-klik (shell).

**Fra 8 MC-faner (S1) + 10 hub-sektioner (S2) + 2 hele HUD-surfaces (S3/S4) + 2 chips (C1/C2)** →
**10 Central-CLI-faner** (T1–T10) + terminal-rygrad. Bemærk: **Terminalen er selve rygraden** — Central-CLI er en
terminal, så T8's kommando-linje er altid tilgængelig; fanerne er strukturerede visninger ovenpå.

### Bevarede shell-indgange (ikke faner — undgå at gen-vise fane-data)

- **C1 CentralBadge** beholdes som **shell-chip** (status-prik + incident-tæller + owner-klik → åbn
  Central-CLI). Den viser KUN et sammenkog (status + antal) og fungerer som *indgang* til T1/T4 —
  ingen data-dublet ud over prik+tal. Dens hover-detalje trimmes til status-ord (fuld metrics bor i T1).
- **C2 SystemHealth** foldes ind i **T4** (kanonisk-fejl-log er en anden kilde end central-incidents,
  men samme fane = "hvad er galt"). Chippen i sidebar-foden kan pege på T4.

---

## COVERAGE CHECK — 100 % dækning, nul dubletter

**Hvert Del-1-element (I1–I39) → præcis én Central-CLI-fane** (rettet til 10-fane-designet + self-review):

| Fane | Elementer |
|------|-----------|
| T1 Overview | I1, I2, I3, I4, I19, I24, I39 |
| T2 Nerves | I6, I14, I15 |
| T3 Clusters | I5 |
| T4 Incidents & Anomalies | I7, I8, I9, I10, I37 |
| T5 Runs & Work | I18, I20, I22, I23, I25 |
| T6 Approvals | I26, I27, I28, I29, I30 |
| T7 Agents & Council | I21, I33, **I36a** (council-runtime-del) |
| T8 Mind & Self ⭐ | I32, I34, I35, **I36b** (resten af indre-liv-projektionerne) + SELVET (living_executive/self_model/world_model) |
| T9 Diagnostics | I11, I12, I13 + Healing (central-native `/central/healers`) |
| T10 Governance | flag-governance (central-native `/central/governance`) |
| Rygrad (ikke fane) | I16 kommando-linje · I17 betjenings-genveje (Terminal, altid-aktiv) · I38 OS-CLI-åbning (CentralBadge-klik) |
| tvær-gående | I31 StatusChip (delt UI-primitiv), C1/C2 shell-chips |

**I36 splittes** (self-review-fund I-3): I36a = council-runtime → T7; I36b = resten (self-model/chronicle/
gut/memory/reflection/lab/hardening m.fl.) → T8. Så holder "præcis én fane" bogstaveligt.

**Verifikation:** I1–I39 optræder alle præcis én gang (I16/I17/I38 = rygrad/shell, ikke T-fane; I31 delt
primitiv). **Nul data-dublet.** Hvert endpoint har ét ejer-fane-hook; tidligere 5×`/central/realtime` og
4×`/central/stream` → ét kald hver, delt via state.

**Aggregatorer pensioneres, ikke foldes (self-review-fund C1):** `/mc/runtime` (140KB) + `/mc/jarvis`
(80KB) er IKKE egne I-items — de er mega-bundles af de konstituerende surfaces (I32/I35/I36). CLI gen-skaber
dem ALDRIG; den læser de konstituerende central-sektioner. De to aggregatorer fjernes med resten af MC.

### Owner-only vs. member-synligt

| Central-CLI-fane | Synlighed |
|------------------|-----------|
| T1 Overview | **member** — MEN `/central/*` er owner-gated (403). Member-T1 SKAL bruge CentralBadge'ens member-sikre summary-kilde, ikke `/central/realtime` (self-review-fund I-4). |
| T2 Nerves | **owner-only** (`/central/*`) |
| T3 Clusters | **owner-only** |
| T4 Incidents & Anomalies | **blandet** — central-incidents owner; C2 kanonisk-fejl-log member |
| T5 Runs & Work | **member** for egne runs; Cost (I23)+Hændelser (I25) **owner** |
| T6 Approvals | **member** for egen kø; Deling (I27)+Kanaler (I30) **owner** |
| T7 Agents & Council | **owner-only**. NB: action-POSTs (`run-round`/`execute`/`spawn`) er LLM-triggende → gates eksplicit, ikke blind observabilitet (self-review-fund I-5). |
| T8 Mind & Self | **owner-only** + **§24.4-projektion** (liveness/metadata, ikke rå privat indhold — konkret reducer defineres FØR Fase 1, jf. strategi-doc self-review) |
| T9 Diagnostics | **owner-only** |
| T10 Governance | **owner-only** (skrive-flade, confirm på farlige) |
| C1 CentralBadge | **alle roller** (member: status-ord; owner: metrics + CLI-klik) |
| C2 SystemHealth | **alle roller** |

**Deployment-forbehold (self-review-fund C2):** `/central/mind` + selvet er runtime-proces-tilstand (8011);
`central_hub` læser in-process uden proxy. CLI'en (remote via api) får TOMME mind/self-sektioner når api
kører api-only → de nye buildere skal proxy'e til 8011 (som living_mind), ELLER CLI kræver api+runtime samme proces. Afklares FØR Fase 1.

Owner-gating er allerede håndhævet backend-side: `/central/*` kalder `_require_owner()` (403), og
S1's Agenter/Cost/Hændelser er `ownerOnly` i `TABS`. Konsolideringen bevarer disse grænser 1:1.

---

## Noter til implementering (ikke en del af inventaret, men afledt)

- **Ét data-lag pr. fane:** hver T-fane får ét hook der ejer sine endpoints; tællere i T1
  (kører/fejlet/afventer/agenter/planlagt/pris) læser fra delt state, ikke egne kald → dræber
  5×/4×-call-site-dubletten.
- **Terminalen (T8/I16) er rygraden** — Central-CLI *er* en terminal; strukturerede faner ligger
  ovenpå kommando-linjen.
- **Droppes uden tab:** S3's dekorative 70-cellers sind-grid (rent pynt, ingen data), S1·Oversigt
  (ren dublet-landing), S4 som selvstændig surface (delmængde af S3).
- **Placeholder-sektioner (S2 memory/council/reflection/lab/hardening) er IKKE tomme lovninger:**
  deres backend-routes findes (I36); de projiceres ind i T7/T8 efterhånden via `central_hub`.
