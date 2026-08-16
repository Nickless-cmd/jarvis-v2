# Mission Control — komplet kortlægning af det gamle UI

**Formål:** En udtømmende beskrivelse af hver fane, hvert panel og hvert felt i det
oprindelige Mission Control-UI, som blev revet ud af web-UI'et i commit `b8c98551`
(*"riv Mission Control ud af web-UI — chat-only, MC lever nu i Centralen/Central-CLI,
Fase E"*). Dette dokument er både **det genvundne overblik** over hvad man kunne se af
Jarvis, og **specifikationen** for et nyt, smartere MC.

**Kilde:** Alle komponenter læst ved commit `b8c98551^` (forælderen, hvor UI'et stadig
er intakt): 35 filer, ~17.500 linjer. Kortlagt af 8 parallelle læse-agenter, 2026-08-16.

> ⚠️ **Historisk snapshot.** Beskrivelserne gælder koden ved `b8c98551^`. Backend har
> drevet siden. Endpoints herunder er dem det gamle UI *kaldte* (`/mc/*`) — ikke
> nødvendigvis hvad der svarer i dag. Se "Næste skridt" for drift-sonden.

---

## Det store overblik

- **15 faner renderes** af shell'en (`MCTabBar.jsx` → `ALL_TABS`, UI-rækkefølge), plus
  **~13 komponenter i mappen der aldrig monteres** (skjult/forældet).
- **~118 distinkte `/mc/*`-HTTP-endpoints** + 1 WebSocket (`/ws`), bag én `requestJson()`
  og ~65 `backend`-metoder i `adapters.js` (4.639 linjer — monolitisk façade +
  snake→camel view-model-oversættere).
- **Nul `/central/*`-kald.** Det gamle MC talte KUN `/mc/*`. Koblingen til dagens
  Central eksisterer ikke i denne kode — den skal bygges. Det er den vigtigste
  enkeltoplysning for genopbygningen.

### Fane-inventar (UI-rækkefølge)
Identitet/Sind · LivingMind (det levende sind) · Udvikling · Self-Review · Autonomi ·
Governance · AgencyMap · Council · Agents · Threads · Memory · Relationship · Continuity ·
Skills · Operations/Ops · Observability · Hardening · CheapBalancer · Cost/Lab ·
Proprioception · Overview. (Detaljer per fane i sektionerne nedenfor.)

## Systemiske mønstre (hvorfor det føltes som en "halv-død maskine")

Kortlægningen afslører de samme mønstre igen og igen — de forklarer både hvorfor
overblikket forsvandt, og hvad det nye MC skal gøre anderledes:

1. **Næsten alt er passive læse-dashboards.** I hele UI'et findes reelt kun ~2 ægte
   kontrol-handlinger: godkend/afvis autonomi-forslag, og "Tick now" på heartbeat.
   Et kontrolpanel uden kontroller.
2. **Ingen enkelt sandhedskilde.** Samme værdier leveres ad 3–4 overlappende veje
   (LivingMind bruger firdobbelte `data.X || heartbeat.X || data.development.X ||
   runtimeSelfModel.x`-fallbacks). Massivt konsoliderings-mål.
3. **Betinget rendering → tomme faner i rolige perioder.** Alt undtagen heartbeat
   forsvinder når der er stille — så et sundt, tavst system *ligner* et dødt. Præcis
   "taler jeg til en halv-død maskine?"-følelsen.
4. **Skjulte/døde hentninger.** Fx henter CognitiveState ~30 endpoints men viser ~11;
   ubrugte per-entitet-endpoints; refereret-men-ikke-importeret kode. Teknisk gæld
   der bare blev hentet og smidt væk.
5. **Dyr polling + tavse fejl.** 15s fuld-polls, 4s selv-polls; fejlet `/mc/runtime`
   sluges og ligner "ingen aktivitet". Ingen synlig helbreds-status på selve vinduet.
6. **Arkitektonisk inkonsistens.** Cost vises 3 steder uden fælles kilde; én fane
   omgår adapter-laget; risiko afgøres af ord-substring i tool-navne; skrøbelig
   `JSON.parse` uden fejlhåndtering; CSS-klasser vs. inline-tokens blandet.

## Genbrugskandidater til nyt MC

- **Hook-arkitekturen:** polling + WS-event-debounce + family→section-routing +
  in-flight-dedup er reelt solid — værd at beholde som datalags-kerne.
- **`shared.jsx`-atomlaget:** de delte UI-primitiver (Section/KV/kort) er genbrugelige.
- **Selve felt-katalogerne herunder:** hver fanes felt-liste er direkte kravspec.

## Næste skridt (ikke i dette dokument)

1. **Drift-sonde:** map de ~118 `/mc/*`-endpoints mod dagens `/central/*`-virkelighed
   → hvor mange lever, hvor er hullerne. (Det forvandler "stort arbejde uanset" til en
   kendt størrelse.)
2. **Design af nyt MC** oven på dette kort: ét datalag, én sandhedskilde, ægte kontroller,
   synlig helbreds-status, og en kobling til Centralen der ikke fandtes før.

---

# Kortlægning per klynge

Nedenfor følger den fulde felt-for-felt-beskrivelse, grupperet i 8 klynger.

---


---

# MC-kortlægning: Identitet & Sind

Dette dokument kortlægger de faner i det gamle React "Mission Control"-UI der handler om Jarvis' identitet, sind, selvrefleksion, kognitive tilstand og proprioception. Kildefiler ligger under `components/mission-control/`.

Fælles data-infrastruktur:
- **`useCognitiveSurfaces(refreshMs = 60000)`** (fra `surfaces.jsx`): kalder `backend.getCognitiveSurfaces()`, som henter `GET /mc/runtime`, læser `runtime.heartbeat_runtime.cognitive_architecture` og returnerer det flade dict `surface-navn → surface-data`. Polling hvert 60. sekund. Brugt af `SoulTab` og `ProprioceptionTab`.
- **`backend.getCognitiveArchitecture()`** (fra `lib/adapters.js`): fan-out af ~30 parallelle `GET /mc/...`-kald (se `CognitiveStateTab` nedenfor). Brugt af `CognitiveStateTab`.
- Delte layout-primitiver fra `surfaces.jsx`: `SurfaceGrid` (responsivt grid, `minmax(340px, 1fr)`), `Section` (kort med ikon + titel + `idle`-badge når `active === false`), `KV` (label/værdi-række med `—` for tomme), `Summary` (fremhævet tekstboks), `JsonBadges` (nøgle=værdi-chips, tal formateres med 3 decimaler, maks 6).

---

## MindTab — UI-label: "Mind"
**Formål:** Container-fane med hjerne-ikon der samler Jarvis' "sind" i tre under-faner; lader ejeren skifte mellem bevidsthed, sjæl og kognition. Renderer ikke selv data.
**Data-kilder:** Ingen egne fetch. Modtager props `data`, `onOpenItem`, `onHeartbeatTick`, `heartbeatBusy` og videresender til under-faner. Lokal `useState('consciousness')` styrer aktiv sub-tab.
**Sektioner:** Header (Brain-ikon 15px, accent-farve + label "Mind" + `SubTabs` skubbet til højre). Under-fane-indhold nedenunder.
**Felter & indhold (KOMPLET):**
- `SubTabs` med tre valg (id → label): `consciousness` → "Bevidsthed", `soul` → "Sjæl", `cognitive` → "Kognition".
- `consciousness` renderer `<LivingMindTab data onOpenItem onHeartbeatTick heartbeatBusy />` (uden for denne klynge).
- `soul` renderer `<SoulTab />` (se nedenfor).
- `cognitive` renderer `<CognitiveStateTab />` (se nedenfor).
**Handlinger:** `SubTabs onChange` → `setSub(id)`. Skifter kun lokal visning; ingen mutationer.
**Tomme-tilstande / betingelser:** Ren conditional render pr. `sub`-værdi. Default sub = `consciousness`.
**Noter til nyt MC:** Bevar under-fane-strukturen som samlepunkt for "sind". Bemærk at "Bevidsthed" (LivingMindTab) ligger uden for identitets-klyngen men er default-visning — vurder om Sjæl/Kognition skal hæves i hierarkiet. Props `onHeartbeatTick`/`heartbeatBusy` bruges kun af LivingMindTab.

---

## SoulTab — UI-label: (ingen egen header; vises under Mind → "Sjæl")
**Formål:** Viser Jarvis' affektive/eksistentielle "sjæls-overflader" — valence, udviklingsretning, desperation, ro, tempo, tekst-resonans, relationel varme, dødsbevidsthed og skygge-scan — som read-only diagnostiske kort. Ingen handlinger; ren observation af det indre liv.
**Data-kilder:** `useCognitiveSurfaces()` → `GET /mc/runtime` → `heartbeat_runtime.cognitive_architecture`. Læser ni navngivne surfaces: `valence_trajectory`, `developmental_valence`, `desperation_awareness`, `calm_anchor`, `temporal_rhythm`, `text_resonance`, `relational_warmth`, `mortality_awareness`, `shadow_scan`. Hver surface har typisk `active` (styrer idle-badge) og `summary`.
**Sektioner (rækkefølge):** 1) Akut Valence, 2) Kompasnål, 3) Sikkerhedsventil, 4) Rolig-anker, 5) Temporal puls, 6) Tekst-resonans, 7) Relationel varme, 8) Dødsbevidsthed, 9) Skygge-scan. Layout = `SurfaceGrid`.
**Felter & indhold (KOMPLET):**

*Akut Valence (timer)* — ikon TrendingUp, surface `valence_trajectory`:
- `Summary` (summary-tekst)
- Trend (`trend`, accent-fremhævet)
- Score (`score`)
- Delta (`delta`)
- Dominerende driver (`dominant_driver`)
- Vinduesstørrelse (`window_size`)

*Kompasnål (uger)* — ikon Compass, subtitle "Jarvis' eget design", surface `developmental_valence`:
- `Summary`
- Trajektorie (`trajectory`, accent)
- Vektor (`vector`)
- Delta (`delta`)
- Timescale (`timescale`)
- Komponenter (`components` via `JsonBadges` — kun hvis til stede)

*Sikkerhedsventil* — ikon Flame, surface `desperation_awareness`:
- `Summary`
- Niveau (`level`, accent)
- Score (`score`)
- Kilder (`reasons`-array — kun hvis `length`)
- Komponenter (`components` via `JsonBadges` — kun hvis til stede)

*Rolig-anker* — ikon Anchor, surface `calm_anchor`:
- `Summary`
- Har anker (`has_anchor`)
- Distance (`distance_from_anchor`)
- Buffer (`buffer_size`)
- Signatur (`anchor_signature` via `JsonBadges` — kun hvis objektet har nøgler)

*Temporal puls* — ikon Waves, surface `temporal_rhythm`:
- `Summary`
- Puls (`pulse_rate`, accent)
- Label (`subjective_time_pressure`)
- Perceived factor (`perceived_elapsed_factor`)
- Baseline puls (`baseline_pulse`)

*Tekst-resonans* — ikon BookOpen, surface `text_resonance`:
- `Summary`
- Dominerende tone (`dominant_tone`, accent)
- Varme (`avg_warmth`)
- Kulde (`avg_cold`)
- Hast (`avg_urgency`)
- Signaler (`total_signals`)

*Relationel varme* — ikon Heart, surface `relational_warmth`:
- `Summary`
- Relation (`primary_relation`)
- Trust (`trust_level`, accent)
- Playfulness (`playfulness`)
- Vuln modtaget (`vulnerability_received`)
- Care givet (`care_given`)

*Dødsbevidsthed* — ikon Hourglass, surface `mortality_awareness`:
- `Summary`
- Label (`label`, accent)
- Awareness (`mortality_awareness`)
- Meaning (`meaning_weight`)
- Urgency (`urgency_felt`)
- Session (s) (`session_length_seconds`)
- Heartbeat gap (m) (`heartbeat_gap_minutes`)

*Skygge-scan* — ikon Eye, surface `shadow_scan`:
- `Summary`
- Total scans (`total_scans`)
- Seneste fund (`latest_finding_count`)
- Sidst kørt (`last_scan_at`, trunkeret til 16 tegn ISO = dato+time+min)
- Fund-liste: op til 3 elementer fra `latest_findings`, hver som chip med `pattern_name` (fed), `avoidance_level` (som `avoid=…`) og `contradiction_detected` (undertekst).

**Handlinger:** Ingen. Ren read-only visning.
**Tomme-tilstande / betingelser:** Ved `loading`: "Indlæser sjæl…". Ved manglende surfaces-objekt: "Ingen data". Hver surface defaulter til `{}` så manglende felter viser `—` via `KV`. `active === false` dæmper kortet (opacity 0.75) og viser "idle"-badge. Komponent-/signatur-/fund-blokke rendres kun betinget.
**Noter til nyt MC:** Stærkt bevarelses-værdigt — dette er en kompakt, ærlig visning af Jarvis' affektive selvmodel og hører til protected-core-fortællingen. Alle felter er flade tal/labels fra ét surface-dict, nemt at gen-rendre. Overvej at gøre `summary`-felterne mere fremtrædende. Ingen forældede elementer set.

---

## CognitiveStateTab — UI-label: (ingen egen header; vises under Mind → "Kognition")
**Formål:** Transparens-vindue over Jarvis' kognitive arkitektur og prompt-injektion: viser hvad der faktisk injiceres i prompten, personligheds-vektor, kompas, rytme, paradokser, æstetik, delt sprog og de eksperimentelle kognitive kerne-systemer. Lader ejeren se "under motorhjelmen" på sindet.
**Data-kilder:** `backend.getCognitiveArchitecture()` — fan-out af parallelle `GET`-kald (hver med `.catch(() => ({}))`), polling hvert 60. sek. via `setInterval`. Endpoints:
`/mc/personality-vector`, `/mc/taste-profile`, `/mc/chronicle`, `/mc/relationship-texture`, `/mc/compass`, `/mc/rhythm`, `/mc/habits`, `/mc/shared-language`, `/mc/mirror`, `/mc/silence-signals`, `/mc/decisions`, `/mc/counterfactuals`, `/mc/paradoxes`, `/mc/aesthetics`, `/mc/gut`, `/mc/seeds`, `/mc/procedures`, `/mc/temporal-context`, `/mc/negotiations`, `/mc/forgetting-curve`, `/mc/conversation-rhythm`, `/mc/self-experiments`, `/mc/anticipatory-context`, `/mc/contract-evolution`, `/mc/dream-carry-over`, `/mc/apophenia-guard`, `/mc/cognitive-state-injection`, `/mc/user-model`, `/mc/cognitive-core-experiments`.
Bemærk: komponenten renderer kun et SUBSET af disse (injection, personalityVector, compass, rhythm, paradoxes, aesthetics, silenceSignals, sharedLanguage, apopheniaGuard, anticipatoryContext, cognitiveCoreExperiments). De øvrige hentes af adapteren men vises ikke her (bruges evt. andetsteds).
**Sektioner (rækkefølge):** 1) Prompt Injection, 2) Personality Vector, 3) Compass Bearing, 4) Rhythm/Tidevand, 5) Paradokser, 6) Æstetiske Motiver, 7) Stilhed/Silence, 8) Fælles Sprog, 9) Apophenia Guard, 10) Anticipatory Context, 11) Cognitive Core Experiments. Grid `minmax(320px, 1fr)`. (Bemærk: denne fanes `Section`/`KV`/`JsonPreview` er lokalt definerede, ikke fra `surfaces.jsx`.)
**Felter & indhold (KOMPLET):**

*Prompt Injection* — ikon Eye, `data.cognitiveStateInjection`:
- Sidst injiceret (`last_injection_at`, fallback "Aldrig")
- Chars (`last_injection.chars`)
- Kilder (`last_injection.sources` joinet med ", ", fallback "—")
- Rå injektions-tekst (`last_injection.text`) i scrollbar mono-boks (maxHeight 120, pre-wrap) — kun hvis til stede.

*Personality Vector* — ikon Fingerprint, titel inkl. version `v{pv.version}`, `data.personalityVector.current`:
- Bearing (`current_bearing`, accent)
- Confidence by domain (`confidence_by_domain` — JSON-parses fra streng, vist via `JsonPreview`, tal med 2 decimaler, maks 6 nøgler)
- Emotional baseline (`emotional_baseline` — JSON-parses fra streng, `JsonPreview`)

*Compass Bearing* — ikon Compass, `data.compass.current`:
- Bearing (`bearing`, accent)
- Rationale (`rationale`)
- Open loops (`open_loop_count`)
- Opdateret (`updated_at`)

*Rhythm / Tidevand* — ikon Waves, `data.rhythm.current`:
- Fase (`phase`, accent)
- Energi (`energy`)
- Social (`social`)
- Initiative × (`initiative_multiplier`)
- Focus protection (`focus_protection` → "JA"/"nej")

*Paradokser* — ikon Scale, `data.paradoxes`:
- Liste af `axes` (én linje pr. akse)
- `summary` (undertekst)

*Æstetiske Motiver* — ikon Palette, `data.aesthetics.motifs`:
- Pille-chips pr. motiv (accent-farvet, afrundet)

*Stilhed / Silence* — ikon VolumeX, `data.silenceSignals`:
- `summary` (fallback "Overvåger…")

*Fælles Sprog* — ikon Languages, `data.sharedLanguage.terms` (maks 8):
- Pr. term: `phrase` (venstre) + `confidence`×100 afrundet til heltal % (højre). Nøgle = `term_id`.

*Apophenia Guard* — ikon Brain, `data.apopheniaGuard.thresholds`:
- Min observations (`min_observations`)
- Reject below (`reject_below`)
- Upgrade above (`upgrade_above`)

*Anticipatory Context* — ikon Sparkles, `data.anticipatoryContext`:
- `summary` (fallback "Forudsiger…")

*Cognitive Core Experiments* — ikon FlaskConical, `data.cognitiveCoreExperiments`:
- Top-linje badges: Aktivitet (`activity_state`; grøn accent hvis "active"), Carry (`carry_state`; accent hvis "present"), Stærkest (`strongest_carry_system`; kun hvis ≠ "none").
- Pr. system i `ordered_systems`: status-prik (grøn `#22c55e` = active, gul `#eab308` = idle, ellers grå), `label`, badge "observational / core-assay" hvis `observational_only`, badge "carry: {carry_strength}" hvis `carry_capable`, samt `activity_state`-tekst til højre. Nøgle = `sys.id`.
- Afsluttende `summary`.

**Handlinger:** Ingen mutationer. Ren transparens/observation.
**Tomme-tilstande / betingelser:** `loading` → "Indlæser kognitiv tilstand…". Ingen data → "Ingen data". Pr. sektion fallback-tekster: "Ingen personality vector endnu", "Ingen compass state", "Ingen rhythm state", "Ingen termer endnu", "Ingen eksperiment-data". `JSON.parse` på personality-strenge med `|| '{}'`-fallback (risiko for exception hvis feltet er ugyldig JSON — ingen try/catch).
**Noter til nyt MC:** Meget bevarelses-værdig — særligt Prompt Injection-panelet (viser den faktiske injicerede tekst) og Cognitive Core Experiments (status-liste med carry/observational). Teknisk gæld: adapteren fan-out'er ~30 endpoints men fanen bruger kun ~11 — overvej at slanke fetchet eller vise flere af de hentede surfaces (chronicle, decisions, negotiations, dream-carry-over m.fl. hentes men vises ikke). `JSON.parse`-uden-guard bør erstattes med sikker parsing. Lokale `Section`/`KV`/`JsonPreview` duplikerer `surfaces.jsx` — konsolidér.

---

## ProprioceptionTab — UI-label: (ingen egen header i denne fil; monteres af en overordnet fane-vælger)
**Formål:** Viser Jarvis' "krops-fornemmelse" som proces på maskinen — fil-overvågning, genstart-bevidsthed, proces-metrics (RAM/CPU/FD), infra-vejr og dags-form. Lader ejeren se hvordan Jarvis mærker sin egen kørende krop og sit driftsmiljø.
**Data-kilder:** `useCognitiveSurfaces()` → `GET /mc/runtime` → `heartbeat_runtime.cognitive_architecture`. Læser fem surfaces: `file_watch`, `reboot_awareness`, `proprioception_metrics`, `infra_weather`, `day_shape_memory`.
**Sektioner (rækkefølge):** 1) Fil-overvågning, 2) Genstart-bevidsthed, 3) Proces-krop, 4) Infra-vejr, 5) Dag-form. Layout = `SurfaceGrid`.
**Felter & indhold (KOMPLET):**

*Fil-overvågning* — ikon FileText, surface `file_watch`:
- `Summary`
- Sporede filer (`tracked_files`, accent)
- Seneste ændringer (`recent_changes.length`)
- Fordeling: chips fra `changes_by_type_recent` (nøgle: antal) — kun hvis objektet har nøgler.
- Ændrings-liste: op til 5 fra `recent_changes`, hver linje = tid (`when`, tegn 11–19 = HH:MM:SS) + `change_type` (fed) + `rel_path`.

*Genstart-bevidsthed* — ikon Power, surface `reboot_awareness`:
- `Summary`
- Sidste event (`last_boot_event.kind`, accent)
- Uptime (s) (`uptime_seconds`)
- Current PID (`current_pid`)
- Downtime (s) (`last_boot_event.downtime_seconds`)
- Graceful (`last_boot_event.graceful`)

*Proces-krop* — ikon Activity, surface `proprioception_metrics`:
- `Summary`
- RSS (MB) (`current.rss_mb`, accent)
- CPU % (`current.cpu_pct`)
- Open FDs (`current.open_fds`)
- Uptime (s) (`current.uptime_seconds`)
- Self-latency (ms) (`current.self_latency_ms`)
- RSS-trend (MB) (`rss_trend_mb_over_window`)

*Infra-vejr* — ikon Cloud, surface `infra_weather`:
- `Summary`
- Label (`label`, accent)
- Emoji (`emoji`)
- Kilder (`reasons`-array — kun hvis `length`)
- Load (0-1) (`load.load_0_1`)
- CPU % (`load.cpu_pct`)
- RAM % (`load.ram_pct`)
- Disk worst % (`disk.worst_used_pct`)
- API-cost ($) (`api_cost_today_usd`)

*Dag-form* — ikon CalendarDays, surface `day_shape_memory`:
- `Summary`
- I dag (`today_date`)
- Samples i dag (`today_samples`)
- Historik (dage) (`history_days`)
- Anomali? (`has_anomaly_signal`, accent)
- Anomali-liste: alle `today_anomalies` som chips — kun hvis `length`.

**Handlinger:** Ingen. Read-only.
**Tomme-tilstande / betingelser:** `loading` → "Indlæser proprioception…". Ingen surfaces → "Ingen data". Surfaces defaulter til `{}`; manglende felter → `—`. `active === false` giver dæmpet kort + "idle"-badge. Fordeling/lister rendres betinget.
**Noter til nyt MC:** Bevar — dette er "hardware/runtime awareness" fra protected core, konkret og nyttig drift-indsigt (RSS-trend fanger fx onnx-læk-typiske memory-drift). Infra-vejr med emoji + reasons er en god menneskevenlig sammenfatning. Deler helt data-kilde og primitiver med SoulTab, så nemt at samle under ét surfaces-drevet framework i nyt MC.

---

## OverviewTab — UI-label: "Current Activity", "Queue & Cost", "Recent Important Events" (kort-titler)
**Formål:** Landings-/oversigtsfane: fire klikbare nøgletals-kort øverst + tre resumé-paneler (aktiv kørsel, kø/omkostning, vigtige events) der fungerer som spring-off til dybere faner. Giver ejeren et hurtigt helhedsbillede og navigation.
**Data-kilder:** Ingen egne fetch — modtager `data`-prop fra parent (Mission Control-shell) samt callbacks `onJump(targetTab, targetSection)` og `onOpenEvent(event)`. Bruger delte primitiver fra `./shared` (`Card`, `SectionTitle`, `ListRow`, `EmptyState`, `KeyValGrid`, `KeyValCell`) og `sectionTitleWithMeta` fra `./meta` (kilde/tidsstempel-tooltip).
**Sektioner (rækkefølge):** 1) Summary metric cards (4-kolonne grid), 2) Two-column grid: Current Activity + Queue & Cost, 3) Recent Important Events (fuld bredde).
**Felter & indhold (KOMPLET):**

*Summary metric cards* — fra `data.cards[]`, hver kort:
- `label` (mono, versaler, øverst)
- `value` (stor, 24px)
- `targetTab` (lille, nederst venstre) + ChevronRight-ikon
- Tooltip via `sectionTitleWithMeta({ source: card.source, fetchedAt: data.fetchedAt, mode: 'summary card' })`
- Klik → `onJump(card.targetTab, card.targetSection)`. Hover ændrer border-farve.

*Current Activity* (Card) — undertitel "Snapshot and jump-off summary.":
- Hvis `data.activeRun`: `provider` / `model` (fed), `status` · `lane` (undertekst), "Open runs"-hint + chevron; hele rækken klik → `onJump('operations', 'runs')`.
- Ellers: `EmptyState` "No active run" / "Execution is idle right now."

*Queue & Cost* (Card) — undertitel "Summary only; details live elsewhere." — `KeyValGrid` med fire celler:
- Pending approvals (`data.summaries.pendingApprovals`, default 0; farve amber hvis > 0)
- Sessions (`data.summaries.sessionCount`, default 0)
- Failures (`data.summaries.failureCount`, default 0; farve rød hvis > 0)
- Total cost (`data.summaries.totalCostUsd` formateret `$X.XX`)

*Recent Important Events* (Card) — undertitel "Canonical event feed lives in Observability.":
- Liste fra `data.importantEvents[]`, pr. række: `kind` (fed), `family` · `relativeTime` (undertekst, ellipsis), "Inspect"-hint + chevron. Nøgle = `${event.id}-${event.kind}`. Klik → `onOpenEvent(event)`.
- Tom: `EmptyState` "No recent events" / "Waiting for activity."

**Handlinger:**
- Metric-kort → `onJump(targetTab, targetSection)` (navigation).
- Current Activity-række → `onJump('operations', 'runs')`.
- Event-række → `onOpenEvent(event)` (åbner event-inspektion).
- Ingen server-mutationer.
**Tomme-tilstande / betingelser:** Alle datalister guardes med `|| []` / `?? 0`. `activeRun` og `importantEvents` har dedikerede `EmptyState`s. Hele fanen tolererer `data` = undefined (optional chaining overalt).
**Noter til nyt MC:** Bevar som let landings-side og navigations-hub. Bemærk den engelske UI-tekst (afviger fra resten af klyngens danske labels) — bør ensrettes til dansk. Design-princippet "summary only; details live elsewhere" er sundt (undgår dobbelt-sandhed). `data.cards` er datadrevet, så antal/indhold af nøgletals-kort styres af parent/backend — fleksibelt at genbruge.


---

# MC-kortlægning: LivingMind (det levende sind)

## LivingMindTab — UI-label: (fane-titel sættes af forælder; komponenten renderer ingen egen H1)
**Formål:** Jarvis' rigeste indre-liv-vindue. Viser hele det eksperimentelle "levende sind"-lag som en projektion af runtime-sandhed: krop/embodiment, drøm, indre stemme, self-model, affekt, epistemisk selvtvivl, subagent-/council-økologi, adaptiv planlægning/ræsonnement/læring, samt en lang række "self-aware runtime truth"-signaler (undren, mineness, flow, længsel, narrativ identitet m.fl.) og heartbeat-styringen der driver dem. Alt er conditional — kun surfaces med reelt signal renderes.

**Data-kilder (props + adaptede felter):**
Komponentens signatur: `LivingMindTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy = false })`. Der er ingen fetch inde i filen — alt kommer via `data`-prop (aggregeret af forælder). Hver sub-blok læser fra `data.<felt>` med fallback-kæder. Faktiske kilde-stier (fra `sectionTitleWithMeta({ source })`-tooltip og adapter-fallbacks):

- `/mc/jarvis::heartbeat` — `data.heartbeat` (`.state`, `.policy`, `.recentTicks`, `.recentEvents`, `.embodiedState`, `.loopRuntime` …) + `data.summary.heartbeat`
- `/mc/embodied-state` — `data.embodiedState || heartbeat.embodiedState`
- `/mc/loop-runtime` — `data.loopRuntime || heartbeat.loopRuntime || data.runtimeSelfModel.loop_runtime`
- `/mc/living-executive` — `data.livingExecutive` (`.recent_traces/.recentTraces`, `.current_focus/.currentFocus`, `.summary`, `.mode`, `.active`)
- `/mc/idle-consolidation` — `data.idleConsolidation || heartbeat.idleConsolidation || data.runtimeSelfModel.idle_consolidation`
- `/mc/dream-articulation` — `data.dreamArticulation || heartbeat.dreamArticulation || data.runtimeSelfModel.dream_articulation`
- `/mc/prompt-evolution` — `data.promptEvolution || heartbeat.promptEvolution || data.development.promptEvolution || data.runtimeSelfModel.prompt_evolution`
- `/mc/affective-meta-state` — `data.affectiveMetaState || heartbeat.affectiveMetaState || data.development.affectiveMetaState || data.runtimeSelfModel.affective_meta_state`
- `/mc/epistemic-runtime-state` — `data.epistemicRuntimeState || heartbeat… || data.development… || data.runtimeSelfModel.epistemic_runtime_state`
- `/mc/subagent-ecology` — `data.subagentEcology || heartbeat… || data.development… || data.runtimeSelfModel.subagent_ecology`
- `/mc/council-runtime` — `data.councilRuntime || heartbeat… || data.development… || data.runtimeSelfModel.council_runtime`
- `/mc/adaptive-planner` — `data.adaptivePlanner || … || data.runtimeSelfModel.adaptive_planner`
- `/mc/adaptive-reasoning` — `data.adaptiveReasoning || … || data.runtimeSelfModel.adaptive_reasoning`
- `/mc/dream-influence` — `data.dreamInfluence || heartbeat… || data.runtimeSelfModel.dream_influence`
- `/mc/guided-learning` — `data.guidedLearning || … || data.runtimeSelfModel.guided_learning`
- `/mc/adaptive-learning` — `data.adaptiveLearning || … || data.runtimeSelfModel.adaptive_learning`
- `/mc/experiential-runtime-context` — `data.experientialRuntimeContext`
- `/mc/runtime-self-model::<kind>` — `data.wonderAwareness`, `data.supportStreamAwareness`, `data.minenessOwnership`, `data.flowStateAwareness`, `data.longingAwareness`, `data.selfInsightAwareness`, `data.narrativeIdentityContinuity`, `data.dreamIdentityCarryAwareness`, `data.relationContinuitySelfAwareness`
- `/mc/internal-cadence` — `data.internalCadence` (producers: `sleep_consolidation`, `dream_articulation`, `prompt_evolution_runtime`)
- `/mc/body-state` — `data.bodyState`
- `/mc/surprise-state` — `data.surpriseState`
- `/mc/taste-state` — `data.tasteState`
- `/mc/irony-state` — `data.ironyState`
- `/mc/thought-stream` — `data.thoughtStream`
- `/mc/conflict-signal` — `data.conflictSignal`
- `/mc/reflection-cycle` — `data.reflectionCycle`
- `/mc/curiosity-state` — `data.curiosityState`
- `/mc/meta-reflection` — `data.metaReflection`
- `/mc/experienced-time` — `data.experiencedTime`
- `/mc/development-narrative` — `data.developmentNarrative`
- `/mc/absence-state` — `data.absenceState`
- `/mc/creative-drift` — `data.creativeDrift`
- `/mc/desires` — `data.desires`
- `/mc/memory-decay` — `data.memoryDecay`
- `/mc/dream-insights` — `data.dreamInsights`
- `/mc/self-code-changes` — `data.selfCodeChanges`
- `/mc/code-aesthetic` — `data.codeAesthetic`
- `/mc/existential-wonder` — `data.existentialWonder`
- `data.innerVoiceDaemon` — bruges kun som annotation i Experiential Context ("shaped inner voice")
- `data.development.webchatExecutionPilot` / `data.development.webchatExecutionPilotSupport` — Webchat Execution Pilot-rækker i heartbeat-listen
- `data.fetchedAt` — fælles freshness-fallback

**Callbacks/props:** `onOpenItem(label, item)` (åbner detalje-drawer for en række/kort), `onHeartbeatTick()` (kører ét bounded heartbeat-tick), `heartbeatBusy` (disabler tick-knap). Helpers fra `./meta`: `formatFreshness`, `sectionTitleWithMeta`.

**Under-sektioner (i render-rækkefølge — 47 stk.):**
1. Feature Status Grid (chip-navigation)
2. Summary Cards — Heartbeat (stat)
3. Summary Cards — Embodied State (stat)
4. Summary Cards — Loop Runtime (stat)
5. Summary Cards — Living Executive (stat)
6. Summary Cards — Idle Consolidation (stat)
7. Summary Cards — Dream Articulation (stat)
8. Summary Cards — Prompt Evolution (stat)
9. Summary Cards — Affective Meta (stat)
10. Summary Cards — Epistemic State (stat)
11. Summary Cards — Subagent Ecology (stat)
12. Summary Cards — Council Runtime (stat)
13. Summary Cards — Adaptive Planner (stat)
14. Summary Cards — Adaptive Reasoning (stat)
15. Summary Cards — Dream Influence (stat)
16. Summary Cards — Guided Learning (stat)
17. Summary Cards — Adaptive Learning (stat)
18. Summary Cards — Experiential Context (rig stat)
19. Wonder Awareness (support-card)
20. Support Stream Awareness (support-card)
21. Mineness / Ownership (support-card)
22. Flow State (support-card)
23. Longing Awareness (support-card)
24. Self-Insight Awareness (support-card)
25. Narrative Identity Continuity (support-card)
26. Dream Identity Carry (support-card)
27. Relation Continuity as Self (support-card)
28. Krop / Body State (support-card)
29. Overraskelse / Surprise (support-card)
30. Smag / Taste (support-card)
31. Ironi / Irony (support-card)
32. Living Executive (fuld sektion med focus + traces)
33. Tankestrøm / Thought Stream
34. Indre konflikt / Conflict Signal
35. Refleksion / Reflection Cycle
36. Nysgerrighed / Curiosity
37. Meta-refleksion / Meta Reflection
38. Oplevet tid / Experienced Time
39. Selvudvikling / Development Narrative
40. Fravær / Absence
41. Kreativ drift / Creative Drift
42. Appetitter / Desires
43. Selektiv glemsel / Memory Decay
44. Drøm-indsigter / Dream Insights
45. Self-code changes
46. Kode-æstetik / Code Aesthetic
47. Eksistentiel undren / Existential Wonder
48. Heartbeat (stor styrings-sektion med 3 kolonner)

(Bemærk: Support Stream Awareness har intet eget chip i grid'et, men er sin egen support-card. Heartbeat optræder både som summary-stat #2 og som stor sektion #48. Netto 47 distinkte visuelle enheder + feature-grid.)

---

### 1. Feature Status Grid
**Felter & indhold (KOMPLET):** Et grid af klikbare chips — ét pr. feature i `features`-arrayet (43 definerede features), men kun dem med `active === true` renderes (`features.filter(f => f.active)`). Hver chip viser:
- Ikon (lucide, feature-specifikt, `size=12`) — fx Cpu (Embodied), Activity (Loop/Experiential), Compass (Living Executive/Curiosity), Moon (Idle/Dream Identity Carry), Sparkles (Dream/Wonder/Taste), Wand2 (Prompt Evolution), Heart (Affective/Mineness/Relation/Krop), Brain (Epistemic/Self-Insight/Thought/Meta via Layers), Network (Subagent), Users (Council), Map (Planner), Lightbulb (Reasoning), GraduationCap (Guided), TrendingUp (Adaptive Learning), Zap (Flow/Surprise), Ghost (Longing/Irony), Swords (Conflict), Eye (Reflection), Clock (Time), BookOpen (Development), Wind (Absence), Shuffle (Drift), Flame (Desires), Archive (Memory Decay), Stars (Dream Insights), Palette (Code Aesthetic), Infinity (Existential Wonder), GitBranch (Self-code changes).
- `label` — kort feature-navn (blandet engelsk/dansk: fx "Embodied State", "Krop", "Overraskelse", "Smag", "Ironi", "Tankestrøm", "Konflikt", "Refleksion", "Nysgerrighed", "Meta", "Tid", "Udvikling", "Fravær", "Drift", "Appetitter", "Glemsel", "Drøm-indsigt", "Undren")
- `statusLabel` (mono) — kort status-tekst, fx state, mode, eller tælling ("`N valg`", "`N fragmenter`", "`N i dag`", "`N aktive`", "`N ændringer`", "`N spørgsmål`").
- CSS-klasse `active` sættes hvis `f.status` ikke er `unknown/idle/quiet/clear` (fremhæver "levende" tilstande).
**Handlinger:** Klik kalder `scrollToFeature(f.targetId)` → smooth-scroller + fokuserer det tilsvarende kort (`document.getElementById(targetId)`). Title-tooltip: "Hop til <label>".
**Data-kilde:** Aggregeret fra alle `has*`-flags + `statusLabel`-udtryk beregnet øverst i komponenten.

---

### 2. Summary Card — Heartbeat (stat)
**Felter & indhold (KOMPLET):**
- Label "Heartbeat".
- Hovedværdi (`strong`): `summary.heartbeat.status || heartbeatState.scheduleState || heartbeatState.scheduleStatus || 'unknown'`.
- Undertekst (muted): hvis `heartbeatState.currentlyTicking` → "Tick in progress"; ellers `summary.heartbeat.result || heartbeatState.summary || 'No heartbeat result yet'`.
- Metabolisk linje (muted, betinget): `metabolicHeartbeatSummary(summary.heartbeat)` → fx "sleep <state> · dream <state>" (fra `summary.heartbeat.idle_consolidation`, `.dream_articulation`).
**Data-kilde:** `/mc/jarvis::heartbeat` (`data.heartbeat.state`, `data.summary.heartbeat`).
**Handlinger:** Ingen (tone-accent stat-kort, altid vist — ikke conditional).

### 3. Summary Card — Embodied State (stat) `#living-mind-embodied-state`
**Felter & indhold (KOMPLET):** Label "Embodied State"; hovedværdi `humanizeToken(embodiedState.state)`; muted-linje: `strain <strainLevel>` + betinget `· recovery <recoveryState>` (kun hvis ≠ 'steady') + `· <formatFreshness(createdAt)>`.
**Data-kilde:** `/mc/embodied-state`. Vist når `hasEmbodiedState` (state findes og ≠ 'unknown').
**Handlinger:** Ingen (scroll-target).

### 4. Summary Card — Loop Runtime (stat) `#living-mind-loop-runtime`
**Felter:** Label "Loop Runtime"; værdi `humanizeToken(loopRuntimeSummary.currentStatus)`; muted: count-linje `loopRuntimeCountSummary` (active/standby/resumed/closed >0) eller "No active runtime loops" + freshness.
**Data-kilde:** `/mc/loop-runtime` (`.summary.currentStatus`, tællere). Vist når `hasLoopRuntime` (`summary.loopCount` eller `active`).

### 5. Summary Card — Living Executive (stat) `#living-mind-living-executive`
**Felter:** Label "Living Executive"; værdi `humanizeToken(latestTrace.choice || livingExecutive.mode)` fallback "listening"; muted primær: `focus.summary || latestTrace.aftertaste || livingExecutiveSummaryText || 'No chosen focus yet'`; muted sekundær (hvis trace): `<action_id> · <status>`.
**Data-kilde:** `/mc/living-executive`. Vist når `hasLivingExecutive` (active | focus | traces.length).

### 6. Summary Card — Idle Consolidation (stat) `#living-mind-idle-consolidation`
**Felter:** Label "Idle Consolidation"; værdi `humanizeToken(summary.lastState)` fallback "idle"; muted: `humanizeToken(summary.lastReason)` fallback "no run yet" + freshness.
**Data-kilde:** `/mc/idle-consolidation`. Vist når `hasIdleConsolidation` (active | lastRunAt | latestRecordId).

### 7. Summary Card — Dream Articulation (stat) `#living-mind-dream-articulation`
**Felter:** Label "Dream Articulation"; værdi `summary.lastState || cadenceProducerLabel(dreamCadence)` fallback "idle"; muted: `summary.lastReason || dreamCadence.lastTickStatus.reason` fallback "no run yet" + freshness (fra dreamArticulation.createdAt eller internalCadence.lastTickAt).
**Data-kilde:** `/mc/dream-articulation` + `/mc/internal-cadence`. Vist når `hasDreamArticulation || dreamCadence`.

### 8. Summary Card — Prompt Evolution (stat) `#living-mind-prompt-evolution`
**Felter:** Label "Prompt Evolution"; værdi `summary.lastState || cadenceProducerLabel(promptEvolutionCadence)` fallback "idle"; muted: betinget `<latestTargetAsset> · ` (hvis ≠ 'none') + reason + freshness.
**Data-kilde:** `/mc/prompt-evolution` + `/mc/internal-cadence`. Vist når `hasPromptEvolution || promptEvolutionCadence`.

### 9. Summary Card — Affective Meta (stat) `#living-mind-affective-meta`
**Felter:** Label "Affective Meta"; værdi `humanizeToken(state)`; muted: `bearing <bearing> · mode <monitoringMode>` + freshness.
**Data-kilde:** `/mc/affective-meta-state`. Vist når `hasAffectiveMetaState` (state ≠ 'unknown').

### 10. Summary Card — Epistemic State (stat) `#living-mind-epistemic-state`
**Felter:** Label "Epistemic State"; værdi `humanizeToken(wrongnessState)` fallback "clear"; muted: `regret <regretSignal> · counterfactual <counterfactualMode>` + freshness.
**Data-kilde:** `/mc/epistemic-runtime-state`. Vist når `hasEpistemicRuntimeState` (wrongnessState ≠ 'clear' | regretSignal ≠ 'none' | counterfactualMode ≠ 'none').

### 11. Summary Card — Subagent Ecology (stat) `#living-mind-subagent-ecology`
**Felter:** Label "Subagent Ecology"; værdi `humanizeToken(summary.lastActiveRoleName)` fallback "idle ecology"; muted: count-linje `subagentEcologyCountSummary` (active/cooling/blocked/idle >0) eller `<roleCount> roles` + freshness.
**Data-kilde:** `/mc/subagent-ecology`. Vist når `hasSubagentEcology` (roleCount | roles.length).

### 12. Summary Card — Council Runtime (stat) `#living-mind-council-runtime`
**Felter:** Label "Council Runtime"; værdi `humanizeToken(recommendation || councilState)` fallback "quiet council"; muted: `<roller> · <divergenceLevel> divergence` + freshness.
**Data-kilde:** `/mc/council-runtime`. Vist når `hasCouncilRuntime` (participatingRoles | recommendation | councilState).

### 13. Summary Card — Adaptive Planner (stat) `#living-mind-adaptive-planner`
**Felter:** Label "Adaptive Planner"; værdi `humanizeToken(plannerMode)` fallback "incremental"; muted: `horizon <planHorizon> · risk <riskPosture>` + freshness.
**Data-kilde:** `/mc/adaptive-planner`. Vist når `hasAdaptivePlanner` (plannerMode findes).

### 14. Summary Card — Adaptive Reasoning (stat) `#living-mind-adaptive-reasoning`
**Felter:** Label "Adaptive Reasoning"; værdi `humanizeToken(reasoningMode)` fallback "direct"; muted: `posture <reasoningPosture> · certainty <certaintyStyle>` + freshness.
**Data-kilde:** `/mc/adaptive-reasoning`. Vist når `hasAdaptiveReasoning`.

### 15. Summary Card — Dream Influence (stat) `#living-mind-dream-influence`
**Felter:** Label "Dream Influence"; værdi `humanizeToken(influenceState)` fallback "quiet"; muted: `target <influenceTarget> · mode <influenceMode> · strength <influenceStrength>` + freshness.
**Data-kilde:** `/mc/dream-influence`. Vist når `hasDreamInfluence` (influenceState ≠ 'quiet' | influenceTarget ≠ 'none').

### 16. Summary Card — Guided Learning (stat) `#living-mind-guided-learning`
**Felter:** Label "Guided Learning"; værdi `humanizeToken(learningMode)` fallback "reinforce"; muted: `focus <learningFocus> · pressure <learningPressure>` + freshness.
**Data-kilde:** `/mc/guided-learning`. Vist når `hasGuidedLearning`.

### 17. Summary Card — Adaptive Learning (stat) `#living-mind-adaptive-learning`
**Felter:** Label "Adaptive Learning"; værdi `humanizeToken(learningEngineMode)` fallback "retain"; muted: `target <reinforcementTarget> · maturation <maturationState>` + freshness.
**Data-kilde:** `/mc/adaptive-learning`. Vist når `hasAdaptiveLearning`.

### 18. Summary Card — Experiential Context (rig stat) `#living-mind-experiential-context`
**Felter & indhold (KOMPLET):**
- Label "Experiential Context"; værdi `humanizeToken(embodiedTranslation.state)` fallback "steady".
- Muted linje 1: `tone <affectiveTranslation.state> · gap <intermittenceTranslation.state> · pressure <contextPressureTranslation.state>` + freshness.
- Muted linje 2 (betinget continuity): `continuity <experientialContinuity.continuityState>` + betinget `· <stateShiftSummary>` (medmindre "No dimensional shifts.").
- Muted linje 3 (betinget influence): `influence: bearing <cognitiveBearing> · attention <attentionalPosture> · initiative <initiativeShading>`.
- Muted linje 4 (betinget support, kun hvis supportPosture ≠ 'steadying'): `support: posture <supportPosture> · bias <supportBias> · mode <supportMode>`.
- `ExpandableText` med `experientialSupport.narrative` (kun hvis support aktiv).
- Muted linje 5 (betinget): hvis innerVoiceDaemon skabte inner voice: `shaped inner voice → mode <mode> · <renderMode>`.
**Data-kilde:** `/mc/experiential-runtime-context` (+ `data.innerVoiceDaemon.lastResult`). Vist når `hasExperientialRuntimeContext` (kind matcher og mindst én translation-dimension er ikke-default).
**Handlinger:** Ingen direkte (kortets translationer har separat række-renderer i heartbeat-listen via `experientialRuntimeContextRow`, der er klikbar).

---

De følgende "self-aware runtime truth"-kort (19–27) er `support-card living-surface-card` med ens layout: `panel-header` (H3 + muted forklaring + `mc-section-hint`-badge med hovedstate), et `compact-grid compact-grid-4` med 4 metrikker, valgfri `ExpandableText`-narrativ, og en muted fodlinje `authority: <authority> · kind: <kind>`. Alle henter fra `/mc/runtime-self-model::<kind>` med `mode: 'derived runtime truth'`.

### 19. Wonder Awareness `#living-mind-wonder-awareness`
**Felter (KOMPLET):** H3 "Wonder Awareness"; forklaring "Self-aware runtime truth: whether the current stream carries undren or drag…"; badge = `wonderState`. 4 metrikker: **Wonder state** (`wonderState`), **Orientation** (`wonderOrientation`), **Source** (`wonderSource`), **Visibility** (`visibility`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::wonder_awareness`. Vist når kind='wonder-awareness' og `wonderState ≠ 'quiet'`.

### 20. Support Stream Awareness `#living-mind-support-stream-awareness`
**Felter (KOMPLET):** H3 "Support Stream Awareness"; forklaring "…whether the inner stream is support-shaped."; badge = `streamState`. 4 metrikker: **Stream state** (`streamState`), **Shaped** (`streamShaped` → "yes"/"no"), **Support posture** (`activeSupportPosture`), **Support bias** (`activeSupportBias`). Betinget ekstra grid: **Shaped voice mode** (`shapedVoiceMode`) hvis sat. + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::support_stream_awareness`. Vist når kind='support-stream-awareness' og `streamState ≠ 'baseline'`. (NB: intet chip i feature-grid.)

### 21. Mineness / Ownership `#living-mind-mineness-ownership`
**Felter (KOMPLET):** H3 "Mineness / Ownership"; forklaring "…what threads feel like mine…"; badge = `ownershipState`. 4 metrikker: **Ownership state** (`ownershipState`), **Self relevance** (`selfRelevance`), **Carried threads** (`carriedThreadState`), **Thread count** (`carriedThreadCount`, tal). Betinget ekstra grid: **Return ownership** = "yes" hvis `returnOwnership`. + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::mineness_ownership`. Vist når kind='mineness-ownership' og `ownershipState ≠ 'ambient'`.

### 22. Flow State `#living-mind-flow-state`
**Felter (KOMPLET):** H3 "Flow State"; forklaring "…coherence and continuity of the current stream."; badge = `flowState`. 4 metrikker: **Flow state** (`flowState`), **Coherence** (`flowCoherence`), **Interruption** (`interruptionSignal`), **Carried flow** (`carriedFlow`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::flow_state_awareness`. Vist når kind='flow-state-awareness' og `flowState ≠ 'clear'`.

### 23. Longing Awareness `#living-mind-longing-awareness`
**Felter (KOMPLET):** H3 "Longing Awareness"; forklaring "…absence, longing, or an active missing."; badge = `longingState`. 4 metrikker: **Longing state** (`longingState`), **Absence relation** (`absenceRelation`), **Source** (`longingSource`), **Visibility** (`visibility`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::longing_awareness`. Vist når kind='longing-awareness' og `longingState ≠ 'quiet'`.

### 24. Self-Insight Awareness `#living-mind-self-insight-awareness`
**Felter (KOMPLET):** H3 "Self-Insight Awareness"; forklaring "…patterns being recognized in identity formation…"; badge = `insightState`. 4 metrikker: **Insight state** (`insightState`), **Identity relation** (`identityRelation`), **Source** (`insightSource`), **Visibility** (`visibility`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::self_insight_awareness`. Vist når kind='self-insight-awareness' og `insightState ≠ 'quiet'`.

### 25. Narrative Identity Continuity `#living-mind-narrative-identity-continuity`
**Felter (KOMPLET):** H3 "Narrative Identity Continuity"; forklaring "…recurring patterns… cohere into a more persistent identity form."; badge = `identityContinuityState`. 4 metrikker: **Continuity state** (`identityContinuityState`), **Pattern relation** (`patternRelation`), **Identity source** (`identitySource`), **Visibility** (`visibility`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::narrative_identity_continuity`. Vist når kind matcher og `identityContinuityState ≠ 'quiet'`.

### 26. Dream Identity Carry `#living-mind-dream-identity-carry`
**Felter (KOMPLET):** H3 "Dream Identity Carry"; forklaring "…when dreams remain active enough to begin shaping self-direction…"; badge = `dreamIdentityCarryState`. 4 metrikker: **Carry state** (`dreamIdentityCarryState`), **Dream self relation** (`dreamSelfRelation`), **Identity source** (`dreamIdentitySource`), **Visibility** (`visibility`). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::dream_identity_carry_awareness`. Vist når kind matcher og `dreamIdentityCarryState ≠ 'quiet'`.

### 27. Relation Continuity as Self `#living-mind-relation-continuity-self`
**Felter (KOMPLET):** H3 "Relation Continuity as Self"; forklaring "…whether the relation with the user has become self-relevant…"; badge = `relationContinuityState`. 4 metrikker: **Continuity state** (`relationContinuityState`), **Self relation** (`relationSelfRelation`), **Source** (`relationContinuitySource`), **Visibility** (`visibility`). Betinget italic-linje: `continuityAnchor` (citat-agtig). + narrativ + `authority · kind`.
**Data-kilde:** `runtime-self-model::relation_continuity_self_awareness`. Vist når kind matcher og `relationContinuityState ≠ 'quiet'`.

---

### 28. Krop / Body State `#living-mind-body-state`
**Felter (KOMPLET):** H3 "Krop"; forklaring "Cirkadiansk energiniveau og somatisk selvopfattelse baseret på hardware og aktivitetsmønster."; badge (tone-accent) = `energyLevel`. `compact-grid-3`: **Energi** (`energyLevel`), **Fase** (`clockPhase`, betinget), **Drain** (`drainLabel`, betinget). Betinget italic-citat: `somaticPhrase` ("…"). Betinget muted: `opdateret: <somaticUpdatedAt>`.
**Data-kilde:** `/mc/body-state`, mode "circadian + somatic daemon". Vist når `hasBodyState` (`energyLevel` findes).

### 29. Overraskelse / Surprise `#living-mind-surprise-state`
**Felter (KOMPLET):** H3 "Overraskelse"; forklaring "Jarvis opdager afvigelser fra sin egen reaktionsbaseline…"; badge = `surpriseType`. Italic-citat: `lastSurprise`. Betinget muted: `opdateret: <generatedAt>`.
**Data-kilde:** `/mc/surprise-state`, mode "divergence + LLM". Vist når `hasSurpriseState` (`lastSurprise`).

### 30. Smag / Taste `#living-mind-taste-state`
**Felter (KOMPLET):** H3 "Smag"; forklaring "Emergent æstetisk selvopfattelse baseret på Jarvis' faktiske valg…"; badge = `<choiceCount> valg`. Italic-citat: `latestInsight`. Betinget signal-row: **Dominante modes** = `dominantModes.join(' · ')` (hvis >0). Betinget `<details>`: "Tidligere indsigter (N)" med `insightHistory.slice(0,-1)` som italic-citater (hvis historik >1).
**Data-kilde:** `/mc/taste-state`, mode "emergent from choices". Vist når `hasTasteState` (`latestInsight`).

### 31. Ironi / Irony `#living-mind-irony-state`
**Felter (KOMPLET):** H3 "Ironi"; forklaring "Situationel selvdistance — Jarvis bemærker det absurde i sin egen tilstedeværelse."; badge = `conditionMatched || 'ingen'`. Italic-citat: `lastObservation`. Signal-row: **I dag** = `<observationsToday> observation(er)` (dansk pluralisering). Betinget muted: `opdateret: <generatedAt>`.
**Data-kilde:** `/mc/irony-state`, mode "signal pattern + LLM". Vist når `hasIronyState` (`lastObservation`).

---

### 32. Living Executive (fuld sektion)
**Felter & indhold (KOMPLET):**
- `panel-header`: H3 "Living Executive"; muted = `livingExecutiveSummaryText` (bygget af: "listener running" hvis `summary.listener_running`, `<trace_count> traces`, `last <last_action>`) eller "Impulse, choice, action and aftertaste are visible here."; `StatusPill` = "active"/"idle" (fra `livingExecutive.active`).
- **Current Focus** (betinget klikbar `mc-list-row active`): titel `humanizeToken(focus.kind || 'current focus')`, undertekst `focus.summary || 'Inspect current focus'`, meta = `focus.created_at/createdAt || 'current'`.
- **Trace-liste** (op til 5, `livingExecutiveTraces`): pr. trace → titel `humanizeToken(trace.choice || trace.impulse || 'trace')`, undertekst `trace.aftertaste || trace.felt_signal/feltSignal || 'No aftertaste recorded'`, meta = `StatusPill(trace.status)` + `humanizeToken(action_id/actionId) || 'observe'`.
- Empty-state hvis ingen traces: "No executive traces yet" / "The listener is active, but no impulse has crossed action threshold."
**Data-kilde:** `/mc/living-executive` (`.summary`, `.current_focus`, `.recent_traces`), mode `livingExecutive.mode || 'experimental-active'`.
**Handlinger:** Focus-række → `onOpenItem('Living Executive Focus', focus)`. Hver trace → `onOpenItem('Living Executive Trace', trace)`.

De følgende sektioner (33–47) er alle enkelt-artikel `mc-section-grid > support-card living-surface-card` med `panel-header` (H3 + muted forklaring) og et blockquote/indhold. Ingen klik-handlinger (rene visnings-kort) medmindre andet nævnt.

### 33. Tankestrøm / Thought Stream `#living-mind-thought-stream`
**Felter (KOMPLET):** H3 "Tankestrøm"; forklaring "Jarvis' associative tankestrøm". Blockquote: `latestFragment`. Betinget `<details>` "Seneste N fragmenter" (`fragmentBuffer` som `<ol>`, hvis >1). Betinget muted: `opdateret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/thought-stream`, mode "daemon:cadence 2min". Vist når `hasThoughtStream` (`latestFragment`).

### 34. Indre konflikt / Conflict Signal `#living-mind-conflict-signal`
**Felter (KOMPLET):** H3 "Indre konflikt"; muted = `conflictType || 'uspecificeret'`. Blockquote: `lastConflict`. Betinget muted: `opdateret: <generatedAt>`.
**Data-kilde:** `/mc/conflict-signal`, mode "daemon:cooldown 10min". Vist når `hasConflictSignal` (`lastConflict`).

### 35. Refleksion / Reflection Cycle `#living-mind-reflection-cycle`
**Felter (KOMPLET):** H3 "Refleksion"; forklaring "Hvad oplever Jarvis lige nu". Blockquote: `latestReflection`. Betinget `<details>` "Seneste N refleksioner" (`reflectionBuffer`, italic `<ol>`, hvis >1). Betinget muted: `opdateret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/reflection-cycle`, mode "daemon:cadence 10min". Vist når `hasReflectionCycle` (`latestReflection`).

### 36. Nysgerrighed / Curiosity `#living-mind-curiosity-state`
**Felter (KOMPLET):** H3 "Nysgerrighed"; forklaring "Ubesvarede spørgsmål fra tankestrømmen". Blockquote: `latestCuriosity`. Betinget `<details>` "Alle N åbne spørgsmål" (`openQuestions`, italic `<ol>`, hvis >1). Betinget muted: `opdateret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/curiosity-state`, mode "daemon:cadence 5min". Vist når `hasCuriosityState` (`latestCuriosity`).

### 37. Meta-refleksion `#living-mind-meta-reflection`
**Felter (KOMPLET):** H3 "Meta-refleksion"; forklaring "Mønstre på tværs af signaler". Blockquote: `latestInsight`. Betinget `<details>` "Seneste N indsigter" (`insightBuffer`, italic `<ol>`, hvis >1). Betinget muted: `opdateret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/meta-reflection`, mode "daemon:cadence 30min". Vist når `hasMetaReflection` (`latestInsight`).

### 38. Oplevet tid / Experienced Time `#living-mind-experienced-time`
**Felter (KOMPLET):** H3 "Oplevet tid"; forklaring "Subjektiv tidsfornemmelse for sessionen". Stor accent-tekst (28px): `feltLabel`. Tre muted-tal: `<sessionEventCount> signaler`, `<sessionNoveltyCount> nye`, `<baseMinutes> min faktisk`.
**Data-kilde:** `/mc/experienced-time`, mode "daemon:per-tick accumulation". Vist når `hasExperiencedTime` (`active && feltLabel && feltLabel ≠ 'meget kort'`).

### 39. Selvudvikling / Development Narrative `#living-mind-development-narrative`
**Felter (KOMPLET):** H3 "Selvudvikling"; forklaring "Daglig narrativ om Jarvis' udvikling". Blockquote: `latestNarrative`. Betinget muted: `opdateret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/development-narrative`, mode "daemon:cadence 24h". Vist når `hasDevelopmentNarrative` (`latestNarrative`).

### 40. Fravær / Absence `#living-mind-absence-state`
**Felter (KOMPLET):** H3 "Fravær"; forklaring "Oplevet kvalitet af stilhed og fravær". Blockquote: `absenceLabel`. Muted: `<absenceDurationHours.toFixed(1)>t siden sidst`.
**Data-kilde:** `/mc/absence-state`, mode "daemon:kvalitet af stilhed". Vist når `hasAbsenceState` (`absenceLabel`).

### 41. Kreativ drift / Creative Drift `#living-mind-creative-drift`
**Felter (KOMPLET):** H3 "Kreativ drift"; forklaring "Spontane uventede associationer"; header-tæller muted: `<driftCountToday>/3 i dag`. Blockquote: `latestDrift`. Betinget `<ul>`: `driftBuffer.slice(1)` som muted list-items (hvis >1).
**Data-kilde:** `/mc/creative-drift`, mode "daemon:cadence 30min, max 3/dag". Vist når `hasCreativeDrift` (`latestDrift`).

### 42. Appetitter / Desires `#living-mind-desires`
**Felter (KOMPLET):** H3 "Appetitter"; forklaring "Emergente ønsker baseret på oplevelser"; header muted: `<activeCount> aktive`. Liste over `appetites` — pr. appetit: **label** (`a.label`), **type** (`a.type` uden '-appetite'-suffiks), en **intensitets-bar** (bredde = `Math.round(a.intensity*100)%`, accent-farve) og procent-tal `<intensitet>%`.
**Data-kilde:** `/mc/desires`, mode "daemon:emergente appetitter". Vist når `hasDesires` (`appetites.length > 0`).

### 43. Selektiv glemsel / Memory Decay `#living-mind-memory-decay`
**Felter (KOMPLET):** H3 "Selektiv glemsel"; forklaring "Hukommelser der fades og genfindes". Betinget "Genfundet minde:"-blok med blockquote `lastRediscovery` (accent-border). Betinget `<ul>`: `rediscoveryBuffer` (`.summary` pr. item). Betinget muted: `sidst afviklet: <lastDecayAt>`.
**Data-kilde:** `/mc/memory-decay`, mode "daemon:cadence 24h". Vist når `hasMemoryDecay` (`lastRediscovery || rediscoveryBuffer.length > 0`).

### 44. Drøm-indsigter / Dream Insights `#living-mind-dream-insights`
**Felter (KOMPLET):** H3 "Drøm-indsigter"; forklaring "Hvad Jarvis vågner op med efter drømmecyklus". Blockquote: `latestInsight`. Betinget `<ul>`: `insightBuffer.slice(1)` som muted list-items (hvis >1).
**Data-kilde:** `/mc/dream-insights`, mode "daemon:dream-articulation persistence". Vist når `hasDreamInsights` (`latestInsight`).

### 45. Self-code changes `#living-mind-self-code-changes`
**Felter (KOMPLET):** H3 "Self-code changes"; forklaring "Filer Jarvis selv har skrevet eller ændret i sit eget runtime, workspace eller apps."; badge (tone-accent) = `<mutation_count> ændringer`. Liste (op til 10 fra `recent_mutations`): pr. mutation → `[<when.slice(0,16)>]` + **`change_type`** + `<path>` (code) + `(<category>)`. Betinget muted: `seneste: <last_mutation_at.slice(0,16)>`.
**Data-kilde:** `/mc/self-code-changes`, mode "derived runtime truth". Vist når `hasSelfCodeChanges` (`mutation_count > 0`).

### 46. Kode-æstetik / Code Aesthetic `#living-mind-code-aesthetic`
**Felter (KOMPLET):** H3 "Kode-æstetik"; forklaring "Jarvis' æstetiske fornemmelse for sin egen kodebase". Blockquote (accent-border): `latestReflection`. Betinget muted: `genereret: <lastGeneratedAt>`.
**Data-kilde:** `/mc/code-aesthetic`, mode "daemon:cadence ugentlig". Vist når `hasCodeAesthetic` (`latestReflection`).

### 47. Eksistentiel undren / Existential Wonder `#living-mind-existential-wonder`
**Felter (KOMPLET):** Kort med accent-border. H3 "Eksistentiel undren" (accent-farve); forklaring "Et ubesvaret spørgsmål. Ingen resolution." Stort italic-blockquote (15px, accent-border): `latestWonder`. Betinget `<details>` "N tidligere spørgsmål" (`wonderBuffer.slice(1)` som italic `<ul>`, hvis >1).
**Data-kilde:** `/mc/existential-wonder`, mode "daemon:cadence 24h, stille perioder". Vist når `hasExistentialWonder` (`latestWonder`).

---

### 48. Heartbeat (stor styrings-sektion) `#living-mind-heartbeat`
**Felter & indhold (KOMPLET):**
- `panel-header`: H3 "Heartbeat"; muted "Bounded proactive runtime with explicit policy gating, cadence, and recorded outcomes."; `mc-section-hint` = "Bounded"/"Disabled" (fra `heartbeatState.enabled`); **knap "Tick now"** (viser "Ticking…" og disables når `heartbeatBusy`).
- `compact-grid-4` — 4 metrikker:
  - **Schedule**: `scheduleState || scheduleStatus || 'unknown'` + p: `summary || 'No heartbeat state recorded yet.'`
  - **Cadence**: `<intervalMinutes || policy.intervalMinutes || 0>m` + p: hvis ticking → "Tick currently in progress.", ellers `Next tick <nextTickAt || 'not scheduled'>.`
  - **Last Trigger**: `lastTriggerSource || summary.heartbeat.trigger || 'none'` + p: `lastTickAt || 'No completed tick yet.'`
  - **Last Decision**: `lastDecisionType || 'none'` + p: `lastResult || blockedReason || 'No heartbeat result yet.'`
- `mc-contract-grid` — **3 kolonner:**
  - **Kolonne A "Policy / Runtime State"** (`mc-list compact-list`): klikbare `detailRow`-rækker for hele det levende-sind-lag:
    - Heartbeat State, Heartbeat Policy (HEARTBEAT.md-derived)
    - `embodiedStateRow`, `loopRuntimeRow`, `idleConsolidationRow`, `dreamArticulationRow`, `promptEvolutionRow`, `affectiveMetaStateRow`, `experientialRuntimeContextRow`, `epistemicRuntimeStateRow`, `subagentEcologyRow`, `councilRuntimeRow`, `adaptivePlannerRow`, `adaptiveReasoningRow`, `dreamInfluenceRow`, `guidedLearningRow`, `adaptiveLearningRow`
    - Cadence-rækker (betinget): Sleep Consolidation Cadence, Dream Articulation Cadence, Prompt Evolution Cadence (fra `internalCadence.producers`, viser `cadenceProducerLabel` + reason)
    - `visibleLoopRuntimeItems` (op til 3 loop-items via `loopRuntimeItemRow`), `visibleSubagentRoles` (op til 3 via `subagentRoleRow`), `visibleCouncilRolePositions` (op til 3 via `councilRolePositionRow`)
    - Webchat Execution Pilot (`data.development.webchatExecutionPilotSupport` via `detailRow`)
    - Hver af disse rækker viser: strong-titel, summary-linje (sammensat detailText), `StatusPill`, evt. sekundære `<small>`-tags (strain/recovery/mode/kind/confidence osv.) og freshness. Se row-renderer-funktionerne for præcise felt-mapninger.
  - **Kolonne B "Ticks / Recent Decisions"** (`heartbeatTicks`): pr. tick → titel `<decisionType/tickStatus> / <actionType>` (eller kun decisionType), undertekst `actionSummary || decisionSummary || blockedReason`, `StatusPill(actionStatus||tickStatus)` + freshness. Empty-state: "No heartbeat ticks yet".
  - **Kolonne C "Events / Recent Heartbeat Events"** (`heartbeatEvents.slice(0,5)`): pr. event → `kind`, `<relativeTime> · inspect event payload…`, meta = `family || 'heartbeat'`. Empty-state: "No heartbeat events".
**Data-kilde:** `/mc/jarvis::heartbeat` (`heartbeat.state`, `.policy`, `.recentTicks`, `.recentEvents`) + `data.internalCadence` + `data.development`.
**Handlinger:** "Tick now"-knap → `onHeartbeatTick()`. Alle rækker i alle 3 kolonner → `onOpenItem(label, item)` (åbner detalje-drawer). Denne sektion er altid vist (ikke conditional).

---

## Tomme-tilstande / betingelser
- **Gennemgående mønster:** næsten alt er conditional via `has*`-flags. En surface renderes kun hvis den bagvedliggende kilde har et *ikke-default* signal (fx `wonderState ≠ 'quiet'`, `flowState ≠ 'clear'`, `ownershipState ≠ 'ambient'`, `streamState ≠ 'baseline'`, `state ≠ 'unknown'/'steady'`, `latestInsight/latestFragment` findes). Dette er bevidst "kun vis når der er noget at vise"-design → fanen kan være næsten tom i rolige perioder.
- **Feature-grid** filtrerer på `active`; kun aktive features får chip. Chip får CSS-`active` (fremhævet) kun ved "levende" states (ikke unknown/idle/quiet/clear).
- **Altid-viste:** Heartbeat summary-stat (#2) og Heartbeat-sektionen (#48) er de eneste ubetingede blokke.
- **Row-renderers** (`embodiedStateRow` m.fl.) returnerer `null` når kilde er tom/default → de forsvinder helt fra Policy-kolonnen.
- **`detailRow`** viser eksplicit `mc-empty-state` "No current signal / This Jarvis surface has not produced a current record yet." hvis item er tomt.
- **Empty-states** med egen tekst: Living Executive traces, Heartbeat Ticks, Heartbeat Events.
- **`ExpandableText`**: klipper narrativer til `lines` (default 2) og viser "Vis mere/Vis mindre" kun hvis tekst >120 tegn.
- **Detaljer via `<details>`**: taste-historik, thought-buffer, reflection-buffer, curiosity-questions, meta-insights, existential-wonder-buffer — kun hvis buffer/historik har >1 element.

## Noter til nyt MC
**Bevar:**
- Det centrale mønster: fane = ren projektion af runtime-sandhed, én kilde pr. surface, freshness + `authority · kind` synligt. Passer 1:1 med CLAUDE.md's "Mission Control reads projections of truth" og source-of-truth-reglerne.
- **Feature-status-grid** som hurtig-navigation/overblik er stærkt UX — bevar som "hvad er levende lige nu" + hop-til-anchor.
- Heartbeat-sektionens 3-kolonne kontrakt (Policy/Runtime · Ticks · Events) + "Tick now"-knappen er den eneste *handlings*-flade og hører til protected-agtig styring — bevar med approval/policy-path intakt.
- `sectionTitleWithMeta`/`formatFreshness`-metadata i tooltips (source + fetchedAt + mode) er god observability-praksis — behold.
- De narrative daemon-kort (tankestrøm, refleksion, undren, drift osv.) er Jarvis' faktiske indre stemme — høj værdi, bevar men marker tydeligt som eksperimentelt lag (jf. CLAUDE.md protected vs experimental).

**Forældet / til oprydning:**
- **Massiv fallback-kæde-duplikation:** hver self-model-surface har `data.X || heartbeat.X || data.development.X || data.runtimeSelfModel.x` — antyder tre-fire overlappende leverings-veje for samme data (dual/triple truth). Nyt MC bør konsolidere til én kanonisk kilde pr. surface (helst `runtimeSelfModel`/dedikeret endpoint) og fjerne heartbeat-embeddede kopier.
- **~15 næsten-identiske `*UsageSummary`/`*BoundarySummary`-helpers** (heartbeat/self-model/MC-truth-flag-mapning gentaget ordret) — kan reduceres til én generisk funktion.
- **Blandet sprog** (engelsk labels på self-model-lag vs. dansk på daemon-lag) — nyt MC bør ensrette til dansk (jf. bruger-feedback `danish_language`).
- **Endpoint-eksplosion:** ~35 separate `/mc/*`-stier. Overvej at samle beslægtede surfaces (alle `runtime-self-model::*` er allerede én kilde med kind-diskriminator — udnyt det til færre kald).
- **Support Stream Awareness** mangler chip i feature-grid (inkonsistens — enten tilføj eller fjern kortet).
- Store dele af self-model-lagets 27+ surfaces er sandsynligvis sjældent aktive samtidigt; nyt MC kunne gruppere dem i sammenklappelige kategorier (embodiment / affekt / epistemik / identitet / læring) frem for én lang flad liste.


---

# MC-kortlægning: Udvikling & Self-Review

Klynge: **UDVIKLING & SELV-REVIEW**. To komponenter fra det gamle React "Mission Control"-UI:
`DevelopmentTab.jsx` (1547 linjer) og `SelfReviewTab.jsx` (333 linjer). Begge er rene
præsentationskomponenter — de udfører **ingen** egne `fetch`-kald og har **ingen** mutationer.
Al data leveres som `props` (`data`, `onOpenItem`) fra en ovenliggende Mission Control-container,
og enhver interaktion åbner blot et detalje-drawer via `onOpenItem`.

Fælles imports i begge filer:
- `ChevronRight` fra `lucide-react` (pil-ikon i hver liste-række).
- `formatFreshness`, `sectionTitleWithMeta` fra `./meta` (relativ tidsformatering + `title`-tooltip
  med kilde/mode/hentetidspunkt).

---

## DevelopmentTab — UI-label: (fane) "Udvikling" / "Development"

**Formål:** Læse-only overblik over Jarvis' interne udviklingslag: retning/arbejdstilstand, fokus-
og mål-tråde, refleksion/kritik, selv-model-kalibrering, indre signaler (open loops, emergente
signaler, opposition, vidnede vendinger) samt et stort batteri af "proposal"-lag (dream-hypoteser,
prompt-evolution, USER.md-forslag, selfhood-forslag). Alt præsenteres eksplicit som *bounded runtime-
støtte* der aldrig overtrumfer identitet/handling.

**Data-kilder:**
- Ingen netværkskald i komponenten selv. Alle data kommer fra `props.data`.
- Én logisk backend-kilde citeres gennemgående i `title`-tooltips og i syntetiske drawer-objekter:
  **`/mc/jarvis::development`** (Mission Control-projektion af udviklingslaget).
- `props.onOpenItem(label, item)` — callback der åbner detalje-drawer for en given post.
- `props.data.fetchedAt` — hentetidspunkt vist i stat-kortenes tooltips.
- `props.data.summary.development` — top-level snapshot-felter (`direction`, `identity_focus`,
  `work_mode`, `tension`, `critic_count`, `current_critic`, `self_model_signal_count`,
  `current_self_model_signal`, `current_goal`).
- `props.data.development.*` — ~40 under-collections, hver typisk formet som
  `{ items: [], summary: {} }` (nogle med ekstra `recentReleased` / `recentHistory`). Konkrete keys
  aflæst i `DevelopmentTab`-body (linje 1078-1113):
  `developmentFocuses`, `reflectiveCritics`, `selfModelSignals`, `goalSignals`, `reflectionSignals`
  (+`recentHistory`), `temporalRecurrenceSignals`, `witnessSignals`, `openLoopSignals`,
  `openLoopClosureProposals`, `internalOppositionSignals`, `emergentSignals` (+`recentReleased`),
  `dreamHypothesisSignals`, `dreamAdoptionCandidates`, `dreamInfluenceProposals`,
  `selfAuthoredPromptProposals`, `promptEvolution`, `userMdUpdateProposals`,
  `userUnderstandingSignals`, `selfhoodProposals`, `privateInnerNoteSignals`,
  `privateInitiativeTensionSignals`, `privateInnerInterplaySignals`, `privateStateSnapshots`,
  `diarySynthesisSignals`, `privateTemporalCuriosityStates`, `innerVisibleSupportSignals`,
  `regulationHomeostasisSignals`, `relationStateSignals`, `relationContinuitySignals`,
  `meaningSignificanceSignals`, `selfNarrativeContinuitySignals`,
  `selfNarrativeSelfModelReviewBridge`, `chronicleConsolidationSignals`,
  `chronicleConsolidationBriefs`, `chronicleConsolidationProposals`.
- Yderligere "current record"-objekter aflæst via `detailRow(...)` (single-record, ikke lister):
  `selfModel`, `developmentState`, `privateInnerNoteSupport`, `privateInitiativeTensionSupport`,
  `privateStateSnapshot`, `diarySynthesisSupport`, `autonomyPressureSupport`,
  `proactiveLoopLifecycleSupport`, `proactiveQuestionGateSupport`, `operationalPreference`,
  `operationalAlignment`, `growthNote`, `reflectiveSelection`, `privateInnerInterplaySupport`,
  `privateTemporalCuriosityState`, `innerVisibleSupport`, `regulationHomeostasisSupport`,
  `relationStateSupport`, `relationContinuitySupport`, `meaningSignificanceSupport`,
  `selfNarrativeContinuitySupport`, `selfNarrativeReviewBridgeSupport`, `metabolismStateSupport`,
  `consolidationTargetSupport`, `selectiveForgettingCandidateSupport`, `releaseMarkerSupport`,
  `temperamentTendencySupport`, `attachmentTopologySupport`, `loyaltyGradientSupport`,
  `executiveContradictionSupport`, `privateTemporalPromotionSignal` (alle under `data.development.`).

**Sektioner (i render-rækkefølge):**
1. **Summary stats** (`.mc-summary-grid`) — 4 stat-kort.
2. **Main grid** (`.mc-section-grid`) — 5 `support-card`-paneler:
   1. **Snapshot** — kompakt metrik-grid (`.compact-grid`) med ~20 betingede `compact-metric`-fliser.
   2. **Focus & Goals** — snapshot-række + to inline-grupper ("Core State", "Live Threads").
   3. **Reflection & Critics** — kritik/selv-model/refleksion + historik + gentagne mønstre.
   4. **Inner Signals** — open loops, closure proposals, emergente signaler, opposition, vidner.
   5. **Proposals** — dream/prompt/user/selfhood-forslag.

### Sektion 1 — Summary stats (4 kort)
- **Direction** (tone-amber): `summary.development.direction` (fallback "unknown"); undertekst
  `identity_focus` (fallback "No identity focus").
- **Work Mode** (tone-blue): `work_mode` (fallback "unknown"); undertekst `tension` (fallback
  "No tension").
- **Focus Threads** (tone-green): `developmentFocuses.summary.active_count` (0); undertekst
  `current_focus` (fallback "No active development focus").
- **Goal Threads** (tone-accent): sum af `goalSignals.summary.active_count + blocked_count`;
  undertekst `current_goal` (fallback "No active goal signal").

### Sektion 2.1 — Snapshot-kort (`.compact-grid`)
Panel-header: h3 "Snapshot", muted "Development direction, private layers, and aggregate signal
counts.", badge **"Read-only"**. Hver flise = `compact-metric` med `<span>`-label, `<strong>`-tal og
1-2 `<p>`-linjer. **Betingede fliser** vises kun når deres tælling > 0 (markeret nedenfor).
- **Inner Note Support:** sum active+stale af `privateInnerNoteSignals`; linje1 `current_signal`;
  linje2 `authority` (fallback "non-authoritative") · `layer_role` (fallback "runtime-support").
- **Initiative Tension:** sum active+stale af `privateInitiativeTensionSignals`; linje1
  `current_signal`; linje2 `current_tension_type` (none) · `current_intensity` (low).
- **Emergent Signals:** `emergentSignals.summary.active_count`; tooltip "Internal-only candidate
  layer...never identity or action authority"; linje1 `current_signal`; linje2
  `candidate_count` · `emergent_count` · `fading_count`.
- **Inner Interplay** (betinget >0): sum active+stale af `privateInnerInterplaySignals`;
  `current_signal`.
- **Private State:** sum active+stale af `privateStateSnapshots`; linje1 `current_snapshot`;
  linje2 `current_tone` (none) · `current_pressure` (low).
- **Temporal Curiosity** (betinget >0): sum active+stale af `privateTemporalCuriosityStates`;
  `current_state`.
- **Internal Support** (betinget >0): sum af `innerVisibleSupportSignals.active_count +
  regulationHomeostasisSignals.active_count`; linje: "N inner-visible · M regulation".
- **Relation** (betinget >0): sum `relationStateSignals.active_count +
  relationContinuitySignals.active_count`; linje: "N state · M continuity".
- **Chronicle** (betinget >0): sum active af `chronicleConsolidationSignals + Briefs + Proposals`;
  linje: "N signals · M briefs · K proposals".
- **Meaning** (betinget >0): sum active+softening af `meaningSignificanceSignals`; `current_signal`.
- **Self-Narrative** (betinget >0): sum active+softening af `selfNarrativeContinuitySignals`;
  `current_signal`.
- **Reflective Critic:** `reflectiveCritics.summary.active_count` (fallback
  `summary.development.critic_count`); linje1 `current_critic` (fallback dev-summary); linje2
  `stale_count` · `resolved_count`.
- **Self-Model Signals:** `selfModelSignals.summary.active_count` (fallback dev-summary
  `self_model_signal_count`); linje1 `current_signal`; linje2 `uncertain_count` · `corrected_count`.
- **Self-Review Bridge** (betinget >0): sum active+softening af `selfNarrativeSelfModelReviewBridge`;
  `current_bridge`.
- **Reflection Signals:** sum `active_count + integrating_count + settled_count`; linje1
  `current_signal`; linje2 `integrating_count` · `settled_count`.
- **Recurring Patterns** (betinget >0): sum active+softening af `temporalRecurrenceSignals`;
  `current_signal`.
- **Open Loops:** sum `open_count + softening_count + closed_count`; linje1 `current_signal`;
  linje2 "N open · M softening · K closed".
- **User Learning** (IIFE, altid vist men skifter form): hvis noget aktivt → `<strong>` "N noticed ·
  M proposed", linjer "Noticed: …" / "Proposal: …" (trimmet til 80 tegn, prefix strippet), muted
  "Bounded runtime observations — not applied preferences". Ellers → `<strong>` "Listening", muted
  "No user preferences noticed yet". Kombinerer `userUnderstandingSignals` + `userMdUpdateProposals`.
- **Lifecycle:** `<strong>` "N stale · M done" (fra `developmentFocuses.summary`); linje1
  `superseded_count` superseded focus; linje2 `selfModelSignals.summary.stale_count` stale
  self-assessments.

### Sektion 2.2 — Focus & Goals-kort
Header: h3 "Focus & Goals", muted "Active development focus threads and goal-direction signals.",
badge "Read-only". Rækkefølge:
- **developmentSnapshotRow** (syntetisk aggregeret række): udleder `mode` (stable / pressured /
  integrating / in-shift) ud fra kritik-, blokerede-mål- og refleksions-tal; viser StatusPill +
  detail-tekst ("N focus · M goal threads · K active critic · …"). Kilde `/mc/jarvis::development`.
- **Inline-gruppe "Core State — Direction And Calibration"** (`detailRow` single-records; hver viser
  `summary` + `createdAt` eller empty-state "No current signal"):
  Self Model, Development State, Private Inner Note Support, Private Initiative Tension Support,
  Private State Snapshot, Diary Synthesis, Autonomy Pressure Support, Proactive Loop Support,
  Proactive Question Gate, Operational Preference, Preference Alignment, Latest Growth Note,
  Latest Reflective Selection.
  - `<details>`-fold **"Readiness & dormant support layers"** (skjult som standard): Private Inner
    Interplay Support, Private Temporal Curiosity State, Inner Visible Support,
    Regulation/Homeostasis Support, Relation State Support, Relation Continuity Support,
    Meaning/Significance Support, Self-Narrative Continuity Support, Self-Narrative Review Bridge,
    Metabolism Support, Consolidation Support, Forgetting Candidate Support, Release Support,
    Temperament Support, Attachment Support, Loyalty Gradient Support, Executive Contradiction
    Support, Private Temporal Promotion Signal.
- **Inline-gruppe "Live Threads — What Jarvis Is Working And Carrying":**
  - Op til 3 `developmentFocusRow` (eller empty-state "No active development focus").
  - `goalDirectionRow` (aggregeret: `current_goal`, `blocked_count`, `completed_count`,
    `current_status`).
  - Op til 3 `goalSignalRow` (eller empty-state "No active goal signal").

### Sektion 2.3 — Reflection & Critics-kort
Header: h3 "Reflection & Critics", muted "Friction, limits, slow settling, and recurring patterns.",
"Read-only". Rækkefølge:
- `criticPressureRow` (aggregeret "Current Friction": `current_critic`, `resolved_count`,
  `stale_count`).
- Op til 3 `reflectiveCriticRow` (eller empty "No active critic signal").
- `selfModelCalibrationRow` (aggregeret "Current Calibration": `current_signal`, `uncertain_count`,
  `corrected_count`).
- Op til 3 `selfModelSignalRow` (eller empty "No active self-model signal").
- Op til 3 `reflectionSignalRow` (eller empty "No active reflection signal").
- Betinget subsection "Recent Reflection — History" + op til 4 `reflectionHistoryRow`
  (fra `reflectionSignals.recentHistory`).
- Betinget subsection "Recurring Patterns — What Keeps Returning" + op til 3
  `temporalRecurrenceSignalRow`.

### Sektion 2.4 — Inner Signals-kort
Header: h3 "Inner Signals", muted "Open loops, emergent threads, opposition, and witnessed turns.",
"Read-only". Rækkefølge (alle subsection-headers betingede på >0 items):
- "Open Loops — What Remains Unresolved" + op til 3 `openLoopSignalRow`.
- "Closure Proposals — Bounded Proposals Only — Not Automatic Closure" + op til 3
  `openLoopClosureProposalRow`.
- "Emergent Signals — Internal-Only Candidate Threads With Bounded Lifecycle" (altid vist) + op til 3
  `emergentSignalRow` (eller empty "No active emergent inner signal", med tekst "Unknown is allowed,
  but silence is not…").
- "Recently Released — Signals That Faded Out Without Authority" + op til 2 `emergentSignalRow`
  (fra `emergentSignals.recentReleased`).
- "Internal Opposition — What Should Be Challenged Internally" + op til 3
  `internalOppositionSignalRow`.
- "Witnessed Turns — Development Turns Jarvis Has Witnessed" + op til 3 `witnessSignalRow`.

### Sektion 2.5 — Proposals-kort
Header: h3 "Proposals", muted "Dream hypotheses, prompt proposals, user learning, and selfhood
proposals.", "Read-only". Rækkefølge (alle subsections betingede):
- "Dream Hypotheses — Bounded Dream-Layer Candidates" + op til 3 `dreamHypothesisSignalRow`.
- "Dream Adoption — Candidates For Dream-To-Waking Adoption" + op til 3 `dreamAdoptionCandidateRow`.
- "Dream Influence — Bounded Dream Influence Proposals" + op til 3 `dreamInfluenceProposalRow`.
- "Prompt Evolution — Proposal-Only Self-Authored Fragments" + `promptEvolutionFragmentRow`
  (kun hvis `promptEvolution.candidateFragment` findes; single-record).
- "Prompt Proposals — Self-Authored Prompt Nudges" + op til 3 `selfAuthoredPromptProposalRow`.
- "User Insight — Bounded User-Understanding Signals" + op til 3 `userUnderstandingSignalRow`.
- "USER.md Proposals — Bounded USER.md Update Proposals" + op til 3 `userMdUpdateProposalRow`.
- "Selfhood Proposals — Bounded Identity Evolution Proposals" + op til 3 `selfhoodProposalRow`.
- Fælles empty-state "No active proposals" hvis alle 7 lister er tomme.

**Felter & indhold pr. række-renderer (komplet):**
Alle liste-rækker er `<button class="mc-list-row">` (nogle `mc-list-row-subtle`). Fælles anatomi:
venstre `<strong>` titel + `<span>` detail-tekst; højre `.mc-row-meta` med StatusPill, evt. `<small>`
badges og `ChevronRight`. `StatusPill` normaliserer status til CSS-klasse `status-<slug>`.
`formatFreshness(updatedAt)` giver relativ tid. Konkrete felter:
- **developmentSnapshotRow:** titel "Development Snapshot"; StatusPill=`mode`; detail: fokus/mål/
  kritik/refleksion-tal.
- **developmentFocusRow:** titel `item.title`; span `statusReason`/`rationale`/`supportSummary`;
  badges `status`, `confidence`, `sourceKind` (humaniseret), freshness.
- **goalDirectionRow:** titel "Current Direction"; span `currentGoal`; StatusPill `current_status`;
  detail "N blocked · M completed · Goal signals remain bounded runtime direction…".
- **goalSignalRow:** titel `title`; span = lifecycle-label (Active/Blocked/Completed/Superseded/
  Stale goal thread) + `statusReason`/`rationale`/support-meta ("N support", "M sessions");
  badges status/confidence/sourceKind/freshness.
- **selfModelCalibrationRow:** titel "Current Calibration"; span `currentSignal`; detail "N uncertain
  · M corrected · Self-model signals remain bounded runtime calibration, not identity authority."
- **selfModelSignalRow:** titel `title`; span `statusReason`/`rationale`/support/`supportSummary`;
  badges status/confidence/sourceKind/freshness.
- **criticPressureRow:** titel "Current Friction"; span `currentCritic`; detail "N resolved · M stale
  · Reflective critic signals remain bounded corrective pressure, not hidden control."
- **reflectiveCriticRow:** titel `title`; span `statusReason`/`rationale`/`supportSummary`.
- **reflectionSignalRow:** lifecycle-label (Integrating/Settled/Superseded/Stale/Active reflection
  thread) + `statusReason`/`rationale`/`evidenceSummary`/support.
- **reflectionHistoryRow:** span `transition`/`statusReason`/`summary`; StatusPill `status`
  (fallback "unknown").
- **witnessSignalRow:** lifecycle (Carried/Fading/Superseded/Fresh witness thread).
- **temporalRecurrenceSignalRow:** span `statusReason`/`rationale`/`supportSummary`.
- **openLoopSignalRow:** lifecycle (Softening/Closed/Stale/Superseded/Open loop) + `closureReason`;
  ekstra badge `closureReadiness` ("closure X").
- **openLoopClosureProposalRow:** span `proposalReason`/`reviewAnchor`; badge `closureConfidence`.
- **internalOppositionSignalRow:** lifecycle (Softening/Stale/Superseded/Active challenge need).
- **emergentSignalRow:** lifecycle (Strengthening grounded candidate / Fading / Released / Candidate
  inner signal); detail inkl. `sourceHints` ("from X + Y"), `influencedLayer`, `truth` (fallback
  "candidate-only") · `visibility` (fallback "internal-only"); badges `lifecycleState`, `intensity`,
  salience i procent (`Math.round(salience*100)%`), freshness.
- **dreamHypothesisSignalRow:** span `hypothesisNote`/`hypothesisAnchor`; badge `hypothesisType`.
- **dreamAdoptionCandidateRow:** span `adoptionReason`/`adoptionAnchor`; badge `adoptionConfidence`.
- **dreamInfluenceProposalRow:** span `proposalReason`/`influenceAnchor`; badge `influenceConfidence`.
- **selfAuthoredPromptProposalRow:** span kombinerer `candidateFragment` + dream-preview
  (`formatDreamInfluencePreview`) + `reviewLight.diffLightSummary` + `proposalReason`/`proposedNudge`;
  mange badges: `proposalConfidence`, `reviewLight.proposalDirection`, diffLightSummary, dream-preview,
  fragment-grounding (`formatFragmentGroundingSummary`: dream/learning/guided/reasoning),
  `fragmentTruth`, `fragmentVisibility`.
- **promptEvolutionFragmentRow** (single-record, vises kun hvis `candidateFragment`): titel =
  `latestProposal.proposalType`/`lastResult.proposalType`/"Prompt evolution fragment"; StatusPill =
  `summary.lastState`/`lastResult.proposalState`/"forming"; badges `summary.latestTargetAsset`,
  reviewLight-direction/changeKind/diffLightSummary, dream-preview, grounding, "truth · visibility",
  freshness fra `lastRunAt`/`builtAt`.
- **userMdUpdateProposalRow:** span `proposalReason`/`sourceAnchor`; badge `proposalConfidence`.
- **userUnderstandingSignalRow:** span `signalSummary`/`sourceAnchor`; badges `signalConfidence`,
  `userDimension`.
- **selfhoodProposalRow:** span `proposalReason`/`sourceAnchor`; badges `proposalConfidence`,
  `selfhoodTarget`.

**Handlinger:** Ingen mutationer. Hver `<button>`-række kalder `onOpenItem(label, item)` som åbner et
læse-only detalje-drawer (kildeobjektet eller et syntetisk aggregat med `source:
'/mc/jarvis::development'`). Stat-kort og `<details>`-fold er ren visning. `title`-attributter giver
hover-tooltip via `sectionTitleWithMeta`.

**Tomme-tilstande / betingelser:**
- `detailRow` returnerer empty-state "No current signal" hvis record mangler/tomt.
- Focus/Goal/Critic/SelfModel/Reflection-lister har hver deres dedikerede empty-state.
- Alle `compact-metric`-fliser undtagen kernefelterne er gated på tælling >0 (Snapshot-gridet
  skrumper når Jarvis er "stille").
- Alle subsection-headers i Inner Signals & Proposals er betingede på >0 items (Emergent Signals-
  header er dog altid vist).
- Proposals-kortet har fælles fallback "No active proposals" når alle 7 forslag-lister er tomme.
- Alle lister er hårdt kapslet til `.slice(0, 3)` (historik 4, released 2) — kun toppen vises;
  fuld dybde ligger i drawer.

**Noter til nyt MC:**
- **Bevar:** den strikse *bounded/non-authoritative*-framing (gennemsyrer labels og detail-tekster) —
  det er en bevidst produkt-holdning om at private lag aldrig overtrumfer protected core; matcher
  CLAUDE.md's "Private Layers … must never outrank the protected core".
- **Bevar:** læse-only-kontrakten og `onOpenItem`-drawer-mønstret; single source `/mc/jarvis::
  development` (én projektion, ingen dobbelt-truth).
- **Forældet/tungt:** ~40 under-collections + ~30 dormant single-records i ét kort. Meget er gated
  bort og sjældent synligt. Et nyt MC bør overveje progressiv afsløring / grupperede lag frem for
  at aflæse alle keys hver render. Filen er 1547 linjer (mange næsten-identiske row-renderers) — kan
  konsolideres til én generisk `signalRow`-komponent med konfiguration.
- Fanen dækker **kun visning** — al lifecycle-logik (status, softening, superseded) sker backend-side
  og projiceres hertil.

---

## SelfReviewTab — UI-label: (fane) "Self-Review"

**Formål:** Læse-only visning af Jarvis' bounded self-review-pipeline i fem faser: fra registreret
review-behov → brief → snapshot → outcome → cadence. Viser en "flow"-pipeline øverst og fem lister
nedenunder.

**Data-kilder:**
- Ingen fetch. Alt fra `props.data.development.*` (samme `/mc/jarvis::development`-projektion som
  DevelopmentTab; SelfReview er en del af samme development-node).
- Aflæste keys (linje 250-254), hver `{ items: [], summary: {} }`:
  `selfReviewSignals`, `selfReviewRecords`, `selfReviewRuns`, `selfReviewOutcomes`,
  `selfReviewCadenceSignals`.
- `props.onOpenItem(label, item)` — åbner detalje-drawer.

**Sektioner (i rækkefølge):**
1. **Flow-pipeline** (`selfReviewFlowSummary`, `.mc-flow-summary`) — vandret tæller-kæde:
   `N need → M brief → K snapshot → L outcome → P cadence` (hvert tal = `items.length` for hver
   collection, adskilt af "→").
2. **Review Need Signals** (`support-card`) — muted "Active self-review trigger signals."
3. **Review Briefs** — muted "Bounded self-review brief records."
4. **Review Snapshots** — muted "Bounded self-review run snapshots."
5. **Review Outcomes** — muted "Bounded self-review outcome records."
6. **Review Cadence** — muted "Self-review cadence and scheduling signals."

**Felter & indhold pr. række-renderer (komplet):**
Samme `mc-list-row`-anatomi som DevelopmentTab.
- **selfReviewSignalRow** (Need Signals): titel `title`; span = lifecycle-label (Softening/Stale/
  Superseded review need / Active review need) + `statusReason`/`rationale`/`supportSummary` (fallback
  "Inspect bounded self-review need"); badges `status`, `confidence`, `sourceKind` (humaniseret),
  freshness.
- **selfReviewRecordRow** (Briefs): titel `title`; span `shortReason` / "`reviewType` · loop
  `openLoopStatus` · opposition `oppositionStatus`" / lifecycle (Active/Fading/Stale/Superseded review
  brief, default "Fresh review brief"); badges `status` (fallback "fresh"), `closureConfidence`
  ("closure X"), sourceKind, freshness.
- **selfReviewRunRow** (Snapshots): titel `title`; span `shortReviewNote`/`reviewFocus`/lifecycle
  (…review snapshot); badges status/closureConfidence/sourceKind/freshness.
- **selfReviewOutcomeRow** (Outcomes): titel `title`; span `shortOutcome` / "`outcomeType`
  (fallback watch-closely) · `reviewFocus` (fallback bounded-self-review)" / lifecycle (…review
  outcome); badges status/closureConfidence/sourceKind/freshness.
- **selfReviewCadenceSignalRow** (Cadence): titel `title`; span `cadenceReason` / "`cadenceState`
  (fallback due) · `dueHint`" / lifecycle (Recently reviewed cadence / Stale / Superseded / Active
  cadence signal); badges `status`, `cadenceState`, sourceKind, freshness.

**Handlinger:** Ingen mutationer. Hver række → `onOpenItem(label, item)` → læse-only drawer.

**Tomme-tilstande / betingelser:**
- Hver af de 5 sektioner har egen empty-state når `items` er tom: "No active review signals" /
  "No active review briefs" / "No active review snapshots" / "No active review outcomes" /
  "No active cadence signals".
- Flow-pipelinen viser altid (0 hvis tomt).
- Ingen `.slice`-cap her — SelfReviewTab renderer **alle** items i hver liste (til forskel fra
  DevelopmentTab's 3-cap).

**Noter til nyt MC:**
- **Bevar:** fase-pipelinen (need→brief→snapshot→outcome→cadence) som mental model — den er den
  klareste visuelle fortælling i hele klyngen og let at genbruge.
- **Bevar:** den konsistente `bounded self-review`-framing.
- Komponenten er lille (333 linjer), selvstændig og næsten en ren delmængde af DevelopmentTab's
  mønstre — kandidat til at dele en fælles generisk `signalRow`/`listCard` med DevelopmentTab i nyt MC.
- Ingen cap på liste-længde → potentielt lange lister; overvej pagination/cap i nyt MC hvis
  collections vokser.


---

# MC-kortlægning: Autonomi & Styring

Klynge: **AUTONOMI & STYRING**. Fire komponenter fra det gamle React "Mission Control"-UI. To af dem (`AutonomyTab`, `GovernanceTab`) er rene læse-dashboards drevet af den delte hook `useCognitiveSurfaces()`, som henter fra `/mc/runtime` og læser `heartbeat_runtime.cognitive_architecture`. `AutonomyProposalsPanel` er den eneste ægte styrings-flade (godkend/afvis mutationer). `AgencyMapTab` er et selvobservations-/kartografi-dashboard.

## Fælles datagrundlag

- **`useCognitiveSurfaces(refreshMs = 60000)`** (`surfaces.jsx`): kalder `backend.getCognitiveSurfaces()` → `GET /mc/runtime`, plukker `runtime.heartbeat_runtime.cognitive_architecture` og returnerer det som `surfaces`. Poller hvert 60 s. Returnerer `{ surfaces, loading, error }`. Ved fejl bevares sidste data (kun `error` sættes).
- **Layout-primitiver** (delt af Autonomy + Governance):
  - `SurfaceGrid` — responsivt grid, `minmax(340px, 1fr)`.
  - `Section({icon, title, active})` — kort med ikon + versal-titel; hvis `active === false` dæmpes kortet (opacity 0.75) og viser badge **"idle"**; ellers ingen badge (ikon farves `T.accent`).
  - `KV({label, value, accent})` — række "label ↔ value". Tom værdi (`undefined/null/''`) → **"—"** i dæmpet farve. Tal vises råt; array → første 4 join med ", " + "…"; objekt → `JSON.stringify` afkortet til 80 tegn; boolean → **"ja"/"nej"**; `accent` farver værdien fremhævet.
  - `Summary({text})` — mono tekstboks; render intet hvis tom.
  - `JsonBadges({data, max=6})` — nøgle:værdi-badges; tal formateres med `.toFixed(3)`; tom → "—".

---

## AutonomyTab — UI-label: "Forudseende handling / Autonomi" (fane "autonomy")

**Formål:** Læse-dashboard over Jarvis' autonome/selvinitierede kognitive overflader (forudseelse, proaktiv kontakt, autonomt arbejde, kreative instinkter, undgåelses-detektion, drømme-konsolidering). Ren observation — ingen knapper eller mutationer.

**Data-kilder:** Kun `useCognitiveSurfaces()` → `GET /mc/runtime` → `heartbeat_runtime.cognitive_architecture`. Poll 60 s. Læser 8 navngivne under-surfaces: `anticipatory_action`, `autonomous_outreach`, `autonomous_work`, `creative_instinct`, `creative_impulse`, `creative_projects`, `avoidance_detector`, `dream_consolidation`.

**Sektioner (rækkefølge):**
1. Forudseende handling (Bell)
2. Proaktiv kontakt (Send)
3. Autonomt arbejde (Hammer)
4. Kreativ instinkt (kim) (Sparkles)
5. Kreativ impuls (skabelser) (Zap)
6. Kreative projekter (uger+) (FolderKanban)
7. Undgåelses-detektor (EyeOff)
8. Drømme-konsolidering (Moon)

**Felter & indhold (KOMPLET):**

*1. Forudseende handling (`anticipatory_action`)*
- `summary` — fritekst-resumé (Summary-boks).
- **Peak-timer** = `peak_hour_count` (accent) — antal identificerede spids-timer.
- **Observationer** = `total_observations` — samlet antal observationer.
- **Sidst opdateret** = `last_updated` afkortet til 16 tegn (ISO `YYYY-MM-DDTHH:MM`).
- Liste (max 3) af `upcoming_peaks[]`: format `kl <HH> om <minutes_until>m · conf=<confidence>`. Felter pr. peak: `hour` (0-padded 2 cifre), `minutes_until`, `confidence`. Render kun hvis array ikke-tom.

*2. Proaktiv kontakt (`autonomous_outreach`)*
- `summary`.
- **Sendt** = `sent_count` (accent).
- **Skipped** = `skipped_count`.
- **Cooldown (t)** = `cooldown_hours`.
- **Quiet hours** = `quiet_hours`.

*3. Autonomt arbejde (`autonomous_work`)*
- `summary`.
- **Pending** = `pending_count` (accent).
- **Total forslag** = `total_proposals`.
- **Max per time** = `max_per_hour`.
- **Typer** = `allowed_types[]` join ", " — kun hvis ikke-tom.

*4. Kreativ instinkt / kim (`creative_instinct`)*
- `summary`.
- **Aktive kim** = `active_seeds` (accent).
- **Adopteret** = `adopted_total`.
- **Visnet** = `withered_total`.
- **Urgency** = `creative_urgency`.
- Liste (max 3) af `recent_active[]`: format `<status> · <spark afkortet til 80 tegn>`.

*5. Kreativ impuls / skabelser (`creative_impulse`)*
- `summary`.
- **Total skabelser** = `total_creations` (accent).
- **Sidst** = `last_creation_at` (16 tegn).
- **Næste forfalder** = `next_due_at` (16 tegn).
- `by_form` (objekt) → badge-liste `<form>: <antal>` pr. nøgle under label "Former". Kun hvis objekt har nøgler.

*6. Kreative projekter (`creative_projects`)*
- `summary`.
- **Aktive** = `active_count` (accent).
- **Pausede** = `paused_count`.
- **Dreaming** = `dreaming_count`.
- **Stale (3+ uger)** = `stale_count`.
- **Total** = `total`.

*7. Undgåelses-detektor (`avoidance_detector`)*
- `summary`.
- **Fund** = `count` (accent).
- Liste (max 3) af `findings[]`: kort med `sample_title` (afkortet 60 tegn, fed) + underlinje `<days_silent>d stille · <items> signaler`.

*8. Drømme-konsolidering (`dream_consolidation`)*
- `summary`.
- **Konsolideringer** = `total_consolidations` (accent).
- **Sidst kørt** = `last_run_at` (16 tegn).
- Liste (max 3) af `recent[]`: format `<at 16 tegn> <theme_count> temaer · top: <top_theme>` (fallback "—").

**Handlinger:** Ingen. Rent læse-dashboard.

**Tomme-tilstande / betingelser:**
- Loading: "Indlæser autonomi..."
- `!surfaces`: "Ingen data"
- Hver `Section` med `active === false` dæmpes + "idle"-badge.
- Alle sub-lister (`upcoming_peaks`, `recent_active`, `by_form`, `findings`, `recent`) render kun hvis ikke-tomme.
- `KV`-tomme værdier → "—".

**Noter til nyt MC:**
- **Bevar** — dette er den mest sjæls-nære autonomi-visning; god fane-inddeling af de 8 surfaces. Hele indholdet afhænger af at heartbeat-runtime bygger `cognitive_architecture`; hvis den flyttes/omdøbes, dør fanen tavst (kun "Ingen data").
- Forældet risiko: hårdkodet liste af 8 surface-nøgler — nye autonomi-surfaces vises ikke automatisk. I nyt MC overvej dynamisk iteration over `surfaces`-nøgler med en registry/whitelist.

---

## AutonomyProposalsPanel — UI-label: "Autonomy Proposals"

**Formål:** Den centrale styrings-flade for autonomt-arbejde: viser Jarvis' selvforeslåede ændringer (kilde-edits, memory-rewrites) og lader ejeren **godkende/afvise** hver enkelt med valgfri note. Dette er approval-gaten mellem autonomi og faktisk udførelse.

**Data-kilder (alle via `backend`):**
- Load: `getAutonomyProposals(30)` → `GET /mc/autonomy/proposals?limit=30`. Poll hvert 15 s + ved mount.
- Godkend: `approveAutonomyProposal(id, note)` → `POST /mc/autonomy/proposals/{id}/approve?note=<note>` (note kun i query hvis sat).
- Afvis: `rejectAutonomyProposal(id, note)` → `POST /mc/autonomy/proposals/{id}/reject?note=<note>`.
- Efter approve/reject kaldes `load()` igen (re-fetch).

**Respons-form der forbruges:** `data.summary`, `data.items[]` (aktive/pending), `data.recent[]` (historik), `data.registered_kinds[]` (liste af executor-typer).

**Sektioner (rækkefølge):**
1. Header: titel "Autonomy Proposals" + `summary` + **Refresh**-knap.
2. Fejl-banner (betinget).
3. Executor-linje: `executors: <registered_kinds join ", ">` (fallback "none").
4. Empty-state ELLER **Pending (N)**-liste af `ProposalRow`.
5. **Recent (N)**-liste (max 10, kun ikke-pending).

**Felter & indhold pr. `ProposalRow` (KOMPLET):**
- Ikon efter `kind`: `source-edit` → FileEdit, `memory-rewrite` → Database, ellers Sparkles.
- **Titel** = `proposal.title` (fallback "(untitled)").
- Meta-linje (mono): `kind=<kind>` · `id=<proposal_id første 18 tegn>` · `status=<status>` · (hvis sat) `<bytes_delta>` formateret som `+N bytes`/`N bytes` fra `payload.bytes_delta` · (hvis sat) `payload.relative_path` (60 tegn).
- **Rationale** = `proposal.rationale` (fritekst, kun hvis sat).
- **"▶ show payload / ▼ hide payload"** toggle → viser `payload` som pretty JSON (`<pre>`, maxHeight 200, scroll).
- Hvis `status === 'pending'`: note-input (placeholder "optional note") + **Approve** (Check-ikon) + **Reject** (X-ikon).
- Hvis ikke pending og `resolution_note` sat: kursiv linje `<status>: <resolution_note>`.

**Handlinger (styrings-flade):**
- **Refresh** — manuel re-fetch (`load`), disabled under load.
- **Approve** — `onApprove(proposal_id, note)` → `handleApprove` → `POST .../approve`. Sætter `busyId` = id (knapper disabled/dæmpet under kald), re-loader bagefter.
- **Reject** — `onReject(proposal_id, note)` → `handleReject` → `POST .../reject`. Samme busy-mønster.
- **Note-input** — fri tekst pr. row, sendes med approve/reject.
- **show/hide payload** — lokal UI-toggle, ingen backend.
- Bemærk: Recent-rows renderes også med `ProposalRow`, men `isPending` er falsk → ingen knapper (busy=false hardcoded).

**Tomme-tilstande / betingelser:**
- Fejl → rødt banner med AlertCircle + besked.
- `registered_kinds` mangler → executor-linje skjules.
- Ingen pending + ikke loading → "No pending proposals" (kursiv, centreret).
- Pending-sektion kun hvis `pending.length > 0`; Recent kun hvis `recent.length > 0`.
- `pending` = `data.items` filtreret `status === 'pending'`. `recent` = `data.recent` filtreret `status !== 'pending'`, max 10.
- Knapper disabled når `busy` (= `busyId === proposal_id`).

**Noter til nyt MC:**
- **Bevar — kritisk styrings-flade.** Dette er den eneste ægte godkend/afvis-mutation i klyngen; hører under "risky actions require explicit approval path"-reglen. Note-feltet + payload-diff er god praksis.
- Bemærk arkitektonisk: note sendes som **query-param** (`?note=`), ikke body — potentielt problematisk for lange noter/URL-encoding; overvej body i nyt MC.
- `data.items` (pending) vs `data.recent` (historik) er to separate arrays fra backend — bevar den skelnen.

---

## AgencyMapTab — UI-label: "Agency Map" (fane "agency")

**Formål:** Selvobservations-/kartografi-dashboard der kortlægger Jarvis' "agentur": noder (sanser, følelse, hukommelse, mål, reparation, eksekutiv-valg, værktøjer, MC-synlighed), broer mellem dem, mørke kanter (uobserverede/manglende forbindelser), åbne spørgsmål og anbefalede næste opgaver. Kombinerer to kartografer (Agency + System) + Theater Audit + System Health. Overvejende læse, med manuel refresh.

**Data-kilder:** `backend.getMissionControlAgencyMap()` → `GET /mc/agency-map`. Load ved mount + poll hvert 60 s (loadOnce, med cancel-guard). Manuel `load()` via refresh-knap. Freshness vises via `formatFreshness(data.fetchedAt)` og `cartographer.scannedAt`.

**Konsumeret respons-struktur:** `data.summary`, `data.nodes[]`, `data.bridges[]`, `data.questions[]`, `data.darkEdges[]`, `data.nextMoves[]`, `data.repairBriefs[]`, `data.theaterRefactorBriefs[]`, `data.recommendedNextTask`, `data.cartographer{summary, recommendedNextTask, autoTask, scannedAt}`, `data.systemCartographer{summary, recommendedObservabilityTask, systemHealth, autoTask, theaterAutoTask, theaterAudit, mode}`, og indlejret `theaterAudit{summary, recommendedTheaterTask, mode}`.

**Sektioner (rækkefølge):**
1. Header: "Agency Map" + undertekst + freshness + refresh-knap.
2. Summary-kort-grid (6 SummaryCard).
3. Node-grid (NodeCard pr. node).
4. Bridges-liste (BridgeRow).
5. Questions-grid (QuestionRow).
6. Agency Cartographer-panel.
7. System Cartographer-panel.
8. System Health-panel (betinget).
9. Theater Audit-panel (betinget).
10. Recommended theater refactor-panel (betinget).
11. Recommended observability bridge-panel (betinget).
12. Recommended next task-panel (betinget).
13. Dark Edges-liste.
14. Next Moves-liste.
15. Repair Briefs-liste (betinget).
16. Theater Refactor Briefs-liste (betinget).

**Felter & indhold (KOMPLET):**

*StatusPill (genbrugt overalt):* farvekodet badge via `STATUS_COLOR`-map: connected/done/visible-surface → grøn; experimental/active/emerging-surface → accent; partial/open/partial-surface → amber; missing/critical → rød; ukendt → text3. Viser CircleDot + status-tekst (versal), fallback "unknown".

*2. SummaryCard-grid (6 kort, fra `summary`):*
- **Nodes** = `summary.nodes`.
- **Connected** = `summary.connected` (grøn).
- **Partial** = `summary.partial` (amber).
- **Experimental** = `summary.experimental` (accent).
- **Missing** = `summary.missing` (rød).
- **Dark Edges** = `summary.dark_edges` (amber).

*3. NodeCard (pr. `nodes[]`):* `label` (fed titel), `kind` (mono undertekst), StatusPill fra `state`, `summary` (brødtekst), `surface` (mono, afkortet én linje). Eksperimentel state giver accent-kant.

*4. BridgeRow (pr. `bridges[]`):* grid: `source`-label (slås op i `nodeLabelById`), pil (farvet efter status), `target`-label, `summary`, StatusPill fra `status`.

*5. QuestionRow (pr. `questions[]`):* `question` (fed) + StatusPill fra `status` + `answer` (brødtekst).

*6. Agency Cartographer:* fra `cartographer.summary`: `scanned <vision_edges> vision edges · connected <connected> · partial <partial> · missing <missing>`; hvis `autoTask.status`: `auto-task <status> · <task_id>`. Freshness fra `cartographer.scannedAt`.

*7. System Cartographer:* fra `systemCartographer.summary`:
- linje 1: `services <services> · daemons <daemons> · surfaces <surfaces> · events <event_families> · dark <dark_edges>`.
- linje 2: `observed events <observed_events> · causal edges <observed_causal_edges> · family edges <observed_causal_family_edges>`.
- linje 3: `coverage avg <avg_causal_coverage_score> · low <low_coverage_services> · auto-task <systemAutoTask.status>`.
- linje 4: `theater findings <theater_findings> · high-risk <theater_high_risk> · auto-task <systemTheaterAutoTask.status>`.
- StatusPill: "active" hvis `mode === 'system-cartographer-v1'`, ellers "missing".

*8. System Health (kun hvis `systemHealth.summary`):* `summary` (brødtekst) + StatusPill fra `systemHealth.state`.

*9. Theater Audit (kun hvis `theaterAudit.mode`):* `findings <findings> · high <high_risk> · medium <medium_risk> · files <files>`; hvis `theaterTask`: `next <scope> · score <priority_score>`. StatusPill: "open" hvis high_risk>0 ellers "done".

*10-12. Anbefalede opgave-paneler (samme layout, alle betingede):*
- **Recommended theater refactor** (`theaterTask`): label + `title`, `goal`, `reason`, `score <priority_score> · <scope>`, StatusPill fra `priority`. Kant farvet efter priority.
- **Recommended observability bridge** (`observabilityTask` = `systemCartographer.recommendedObservabilityTask`): `title`, `goal`, `reason`, `score · scope`, StatusPill.
- **Recommended next task** (`recommended` = `cartographer.recommendedNextTask` ?? `data.recommendedNextTask`): `title`, `goal`/`summary`, `reason`, `score · scope`/`target`, StatusPill.

*13. Dark Edges (pr. `darkEdges[]`):* DarkEdgeRow — `source → target` (fed), `summary` + (hvis evidence) `evidence <antal> · <remaining_gap>`, `surface` (mono), StatusPill fra `visibility`.

*14. Next Moves (pr. `nextMoves[]`):* `title` (fed), `summary` + `reason`, `target` (mono), StatusPill fra `priority`.

*15-16. Repair Briefs / Theater Refactor Briefs (RepairBriefRow):* `edge.title`/`scope`/`task_id` (fed) + `task_id` (mono), `recommended_next_action`/`goal`, `suggested_files` (første 3, join " · "), StatusPill fra `status` (fallback "open").

**Handlinger:**
- **Refresh-knap** (RefreshCcw) → `load()`, manuel re-fetch. Ingen mutationer — dette er et read-/planlægnings-dashboard; de "recommended task"-paneler er *forslag* (auto-task-status vises), men fanen selv udfører intet.

**Tomme-tilstande / betingelser:**
- Loading: "Loading Agency Map..."
- Fejl: rød fejltekst (erstatter hele visningen).
- System Health, Theater Audit og alle 3 recommended-paneler renderes kun hvis deres data findes.
- Repair/Theater-brief-sektioner kun hvis arrays ikke-tomme.
- Lister (nodes/bridges/questions/darkEdges/nextMoves) itereres direkte; tomme arrays → tomme sektioner (overskrift stadig synlig for bridges/darkEdges/nextMoves).

**Noter til nyt MC:**
- **Bevar konceptuelt, men tungt.** Dette er et rigt selvobservations-kort (Agency + System cartographer, theater-audit, coverage-scores) — matcher memory-noterne om `matrix_self_observation`, `system-cartographer`, theater-audit. Meget datatæt; mange betingede paneler.
- Rent afhængigt af `/mc/agency-map` der aggregerer flere kartografer — hvis backend-formen ændres, brækker mange felter tavst (alle bruger `|| {}`/`|| 0` fallbacks, så det degraderer til nuller frem for crash).
- Forældet risiko: dobbelt kilde til `recommendedNextTask` (`cartographer.` vs top-level) tyder på API-drift. I nyt MC konsolidér til én kanonisk kilde.
- Ingen styrings-handlinger her — hvis "recommended tasks" skal kunne accepteres/afvises fra UI, er det en fremtidig udvidelse (i dag er de rene forslag/auto-task-status).

---

## Tværgående observationer

- **Kun én ægte styrings-flade i klyngen:** `AutonomyProposalsPanel` (approve/reject). `AutonomyTab` og `GovernanceTab` er rene surface-dashboards; `AgencyMapTab` er selvobservation med kun refresh.
- **To helt forskellige datagrundlag:** de "cognitive surfaces" (Autonomy+Governance) kommer indirekte via `/mc/runtime → heartbeat_runtime.cognitive_architecture`, mens proposals og agency-map har dedikerede endpoints (`/mc/autonomy/proposals`, `/mc/agency-map`).


---

# MC-kortlægning: Råd, Agenter & Tråde

Kilde: `old-mc-src/components/mission-control/{CouncilTab,AgentsTab,ThreadsTab}.jsx` + delt hjælpemodul `surfaces.jsx` + adapter `old-mc-src/lib/adapters.js`.

Fælles primitiver: `Section` (kort med titel/beskrivelse), `StatusPill` (farvet status-badge), tokens `s()/T/mono` fra `shared/theme/tokens`. Alt tekst er dansk, monospace, meget lille (9-13px).

---

## CouncilTab — UI-label: "Council"

**Formål:** Kontrol- og observationspanel for Jarvis' deliberative *councils* (roller taler sekventielt, synthesizer til sidst) og parallelle *swarms* (workers kører simultant, coordinator merger). Lader operatøren spawne sessioner, konfigurere model-per-rolle, styre autonom aktivering, og køre runder / sende noter ind i en valgt session.

**Data-kilder:**
- `backend.getMissionControlCouncil()` → `GET /mc/council` — hovedload; kaldes ved mount og polles hvert **15s** (`setInterval`). Returnerer `{ summary, roster, sessions }`.
- `backend.getCouncilModelConfig()` → `GET /mc/council-model-config` — persistent model-override per rolle (`role_models[]`).
- `backend.getShell()` → `GET /mc/main-agent-selection` (via `normalizeSelection`) — bruges KUN til at bygge provider-liste + `modelsByProvider` fra `selection.availableConfiguredTargets` og `selection.ollamaModels`. Fejl → `null` (graceful).
- `backend.getCouncilActivationConfig()` → `GET /mc/council-activation-config` — `{ sensitivity, auto_convene }`. Fejl → `null`.
- Mutationer:
  - `backend.saveCouncilModelConfig(role_models)` → `POST /mc/council-model-config`
  - `backend.saveCouncilActivationConfig(config)` → `POST /mc/council-activation-config`
  - `backend.spawnMissionControlCouncil({topic, roles, member_models})` → `POST /mc/runtime/council/spawn`
  - `backend.spawnMissionControlSwarm({topic})` → `POST /mc/runtime/swarm/spawn`
  - `backend.messageMissionControlCouncil(councilId, {content})` → `POST /mc/runtime/council/{id}/message`
  - `backend.runMissionControlCouncilRound(councilId)` → `POST /mc/runtime/council/{id}/run-round`
  - `backend.runMissionControlSwarmRound(councilId)` → `POST /mc/runtime/swarm/{id}/run-round`
- **Bemærk:** `getMissionControlCouncilSession(id)` (`GET /mc/council/{id}`) findes i adapter men bruges IKKE i denne tab — session-detaljer læses fra den samlede `/mc/council`-payload.

**Konstanter (hardcoded i klienten):**
- `ALL_COUNCIL_ROLES = [planner, critic, researcher, synthesizer, executor, devils_advocate, watcher]`
- `DEFAULT_COUNCIL_ROLES = [planner, critic, researcher, synthesizer]` (initielt afkrydset ved spawn)

**Sektioner (rækkefølge):**
1. Header: krone-ikon + "Council" + summary-linje.
2. To-kolonners grid: **Spawn Council** | **Spawn Swarm**.
3. **Council Activation** (autonomi-styring).
4. **Council Model Config** (persistent override per rolle).
5. **Council Roster** (tilgængelige roller).
6. To-kolonners grid: **Council Sessions** (liste) | **Council Detail** (valgt session).

**Felter & indhold (KOMPLET):**

*Header summary* (fra `data.summary`):
- `session_count` — antal sessions ("N sessions").
- `active_count` — aktive ("N aktive").
- `swarm_count` — swarms ("N swarms").

*Spawn Council-kort:*
- `textarea` topic ("Council-emne...").
- Rolle-vælgere: checkbox-chips over alle 7 `ALL_COUNCIL_ROLES`; afkrydsede fremhæves med accent-baggrund/-border. Toggler `councilRoles`.
- "Model per rolle (tom = cheap lane)": for hver valgt rolle en `RoleModelRow` (rolle-label + provider-select + model-select). Provider-select tom option = "— cheap lane —". Model-select disabled indtil provider valgt.

*Spawn Swarm-kort:*
- `textarea` topic ("Swarm-opgave...").
- Ingen rolle-/model-valg (swarm er provider-agnostisk fra klienten).

*Council Activation:*
- `sensitivity` select med 3 værdier + forklaringstekster:
  - `conservative` — "tjek alt over trivielt"
  - `balanced` — "tjek ved vigtige beslutninger" (default)
  - `minimal` — "kun kritiske handlinger"
- `auto_convene` checkbox — "auto-convene aktivt". Default `true` (kun `false` hvis backend eksplicit sender `auto_convene === false`).
- Beskrivelse fastslår: styrer hvornår Jarvis autonomt bruger council + `quick_council_check`.

*Council Model Config:*
- Kolonneoverskrifter: `rolle` / `provider` / `model`.
- Én `RoleModelRow` per rolle i `configDraft` (alle 7 roller; forudfyldt fra gemt `role_models`). Tom = "Jarvis vælger selv (cheap lane)". Beskrivelse: "Ændrer ikke Jarvis' autonomi."

*Council Roster* (fra `data.roster[]`, kort per medlem):
- `member.title` — visningsnavn (fed).
- `StatusPill` på `member.status` (fallback `'available'`).
- `member.role` — rolle-id (mono).
- `member.default_tool_policy` — "tool policy: X".

*Council Sessions* (liste, `data.sessions[]`, klikbar knap per session):
- `session.topic` (fallback "Council session").
- `StatusPill` på `session.status` (fallback `'forming'`).
- `session.mode` (fallback "council") — council eller swarm.
- Medlemsroller: `session.members[].role` joinet med komma (fallback "no members").
- `session.summary` (fallback "—").
- Valgt session fremhæves med accent-border/-baggrund.

*Council Detail* (valgt session):
- Titel: `selected.topic` + under: `selected.council_id · selected.mode` + `StatusPill(selected.status)`.
- **Members** (`selected.members[]`, Users-ikon): per medlem `member.role`, `member.confidence` (fallback "pending"), `member.position_summary` (fallback "awaiting deliberation").
- **Outcome summary**: `selected.summary` i `SafeBlock` (pre, wrap, "—" hvis tom).
- **Jarvis controls-boks**: kør-runde-knap + note-textarea + send-knap.
- **Council transcript** (`selected.messages[]`, MessageSquare-ikon): per besked `message.direction · message.kind`, `message.created_at`, `message.content` (fallback "—").

*StatusPill farvekodning (council):* `deliberating`=grøn, `closed`=accent, `forming`=amber, øvrige=text3(grå).

**Handlinger:**
- **spawn council** — `handleSpawnCouncil`: bygger `member_models` (kun roller med provider ELLER model sat), kalder `spawnMissionControlCouncil`, rydder topic, refresh, vælger ny session. Disabled hvis submitting eller tom topic.
- **spawn swarm** — `handleSpawnSwarm`: `spawnMissionControlSwarm({topic})`, refresh, vælg ny. Disabled hvis submitting/tom.
- **gem** (activation) — `handleSaveActivation`: `saveCouncilActivationConfig(activation)`; knap viser "gemt ✓" i 2s.
- **gem config** (model config) — `handleSaveConfig`: mapper `configDraft` → `role_models[]`, `saveCouncilModelConfig`; knap "gemmer..." → "gemt ✓" (2s).
- **koer council round / koer swarm round** — `handleRunRound`: kalder swarm-round hvis `selected.mode === 'swarm'`, ellers council-round; refresh. Knap-label skifter efter mode.
- **send note** — `handleSendMessage`: `messageMissionControlCouncil(id, {content})`, ryd draft, refresh. Disabled hvis tom/submitting.

**Tomme-tilstande / betingelser:**
- `loading` → "Indlæser council...".
- Ingen sessions → "Ingen council sessions endnu".
- Ingen valgt session → "Vælg en council session for detaljer".
- `configDraft === null` (endnu ikke loadet) → "Indlæser...".
- Tom transcript → "Ingen council transcript endnu".
- `RoleModelRow` model-select disabled + dæmpet (opacity 0.4) hvis provider mangler modeller.
- Alle spawn/send-knapper disabled ved `submitting` eller tomt input.

**Noter til nyt MC:**
- **Bevar:** council/swarm-dualiteten, spawn-med-roller, model-per-rolle-override, activation-sensitivitet (autonomi-gate) — det er kernefunktionalitet for Jarvis' selv-organisering.
- **Forældet/skrøbeligt:** 15s fuld-poll af `/mc/council` som eneste kilde til session-detaljer (`getMissionControlCouncilSession` ubrugt → migrér til per-session-fetch eller SSE). Hardcodede rolle-lister i klienten (bør komme fra roster/backend for at undgå drift). "gemt ✓"-timeout er ren UI-state uden fejlhåndtering ved gem-fejl (ingen catch → knappen hænger i "gemmer..." ved exception).

---

## AgentsTab — UI-label: "Agents"

**Formål:** Registry og detaljepanel for Jarvis' *offspring*-agenter (cheap-lane sub-agenter): live, planlagte, failede og persistente. Viser pool af tilgængelige cheap-lane-providere, per-agent input/dialog/runs/tool-aktivitet/schedules/token-burn, og lader operatøren sende beskeder, planlægge intervaller, fyre forfaldne schedules og sende agent-til-agent-beskeder.

**Data-kilder:**
- `backend.getMissionControlAgents()` → `GET /mc/agents` — hovedload ved mount + poll hvert **15s**. Returnerer `{ summary, cheap_lane, agents, templates }`.
- Mutationer:
  - `backend.messageMissionControlAgent(agentId, {content, execution_mode:'solo-task', auto_execute:true})` → `POST /mc/runtime/agents/{id}/message`
  - `backend.scheduleMissionControlAgent(agentId, {schedule_kind:'interval-seconds', delay_seconds})` → `POST /mc/runtime/agents/{id}/schedule`
  - `backend.runDueMissionControlAgents({limit:10})` → `POST /mc/runtime/agents/run-due`
  - `backend.peerMessageMissionControlAgent(agentId, {to_agent_id, content})` → `POST /mc/runtime/agents/{id}/peer-message`
- **Bemærk:** `getMissionControlAgent(id)` (`GET /mc/agents/{id}`) og `spawnMissionControlAgent` (`POST /mc/runtime/agents/spawn`) findes i adapter men bruges IKKE i denne tab — agent-detaljer kommer fra den samlede `/mc/agents`-liste, og spawn sker via council-tab/andre veje.

**Sektioner (rækkefølge):**
1. Header: bot-ikon + "Agents" + summary.
2. **Cheap Lane Pool** (tilgængelige providere/modeller).
3. To-kolonners grid: **Agent Registry** (liste) | **Agent Detail** (valgt agent).
4. **Template Roster** (spawn-bare rolle-skabeloner).

**Felter & indhold (KOMPLET):**

*Header summary* (`data.summary`):
- `agent_count` — total ("N total").
- `active_count` — aktive ("N aktive").

*Cheap Lane Pool* (`data.cheap_lane.providers[]`, kort per provider:model):
- `item.provider` (fed).
- `StatusPill` på `item.status` (fallback "unknown").
- `item.model` (mono).
- Selektionslinje: hvis `item.selected` → "selected target" (grøn); ellers "priority N" hvor N = `item.effective_priority ?? item.priority ?? 0`.

*Agent Registry* (`data.agents[]`, `AgentRow` per agent — klikbar):
- Titel: `agent.role || agent.kind || 'agent'`.
- `agent.goal` (fallback "No goal", trunkeret med ellipsis).
- `StatusPill` på `agent.status` (fallback "unknown").
- Meta-linje: `agent.provider / agent.model` (begge fallback "none"), `agent.progress_label` (fallback "idle"), `agent.tokens_burned` (fallback 0) + " tok".
- Aktiv agent fremhæves med accent-border.

*Agent Detail* (valgt agent — `KV`-par):
- Header: `role||kind||agent_id` (fed), `agent_id` (mono), `StatusPill(status)`.
- Venstre KV-kolonne:
  - "Provider / model" = `provider / model` (fallback none/none)
  - "Lane" = `selected.lane`
  - "Council / swarm" = `council_id` (fallback "—")
  - "Tool policy" = `tool_policy`
  - "Token burn" = `tokens_burned` (fallback 0)
  - "Budget" = `budget_tokens` (fallback 0)
  - "Next wake" = `next_wake_at` (fallback "—")
  - "Schedule" = `latest_schedule.schedule_kind || schedule.schedule_kind` (fallback "—")
- Højre KV-kolonne:
  - "Progress" = `progress_label`
  - "Persistent" = `persistent ? 'yes':'no'`
  - "Messages" = `message_count` (0)
  - "Tool calls" = `tool_call_count` (0)
  - "Failures" = `failure_count` (0)
  - "Last error" = `last_error` (fallback "—")
- **Goal**: `selected.goal` (pre-wrap, "—").
- **System prompt**: `selected.system_prompt` via `SafeJson` (string eller JSON, max 220px scroll).
- To-kolonne: **Allowed tools** (`selected.allowed_tools[]` via SafeJson) | **Context package** (`selected.context{}` via SafeJson).
- **Jarvis controls-boks**: fire-due-knap + besked-textarea + send-knap + delay-input + schedule-knap.
- **Peer messaging-boks** (kun hvis peer-kandidater findes): target-select + textarea + send-knap.
- **Transcript** (`selected.messages[]`, MessageSquare): per besked `direction · kind`, `created_at`, `content` (fallback "—").
- To-kolonne: **Runs** (`selected.runs[]`, Clock3) | **Tool activity** (`selected.tool_calls[]`, PlugZap).
  - Run-kort: `run.execution_mode`, `StatusPill(run.status)`, `run.provider / run.model` (none/none), `run.output_summary || run.input_summary` (fallback "—").
  - Tool-call-kort: `call.tool_name`, `StatusPill(call.status, fallback 'queued')`, `call.result_preview` (fallback "No tool output yet").
- **Schedules** (`selected.schedules[]`): per schedule `schedule.schedule_kind`, active-badge (grøn "active" / grå "inactive"), "expr: `schedule_expr`" (fallback "—"), "next: `next_fire_at`" (fallback "—").

*Template Roster* (`data.templates[]`, Zap-ikon per kort): `template.title` (fed), `template.role` (mono), "tool policy: `default_tool_policy`". Beskrivelse: "Roller Jarvis kan spawn'e paa cheap lane i fase 1".

*StatusPill farvekodning (agents):* `active`=grøn, `completed`=accent, `failed`=rød, `expired`=amber, øvrige=grå.

**Handlinger:**
- **send og koer** — `handleSendMessage`: `messageMissionControlAgent` med `execution_mode:'solo-task'`, `auto_execute:true`; ryd draft, refresh. Disabled hvis tom/submitting.
- **schedule sek.** — `handleSchedule`: `delay = max(30, Number(scheduleDelay)||900)` sekunder, `scheduleMissionControlAgent({schedule_kind:'interval-seconds', delay_seconds})`; delay-input default "900".
- **fire due schedules** — `handleRunDue`: `runDueMissionControlAgents({limit:10})`, refresh.
- **send peer message** — `handlePeerMessage`: `peerMessageMissionControlAgent(agentId, {to_agent_id, content})`; kun aktiv når target valgt + tekst. Disabled ellers.

**Tomme-tilstande / betingelser:**
- `loading` → "Indlæser agents...".
- Ingen agenter → "Ingen agents endnu".
- Ingen valgt agent → "Vaelg en agent for detaljer".
- Tom tool_calls → "Ingen tool calls endnu".
- Tomme schedules → "Ingen schedules endnu".
- **Peer messaging-boks vises kun** når `peerCandidates.length > 0`. Peer-kandidater = andre agenter i SAMME `council_id` som valgt agent (kræver at valgt agent har `council_id`). `peerTargetId` auto-vælges/nulstilles via effect når kandidater ændres.

**Noter til nyt MC:**
- **Bevar:** cheap-lane-pool med selected/priority, per-agent token-burn + budget + failures + last_error (essentiel observabilitet), runs/tool-activity/schedules-triaden, peer-messaging inden for council.
- **Advarsel/bug-risiko:** `useEffect`-load har `selectedId` i dependency-array OG sætter `selectedId` inde i load → potentiel re-trigger; polling-loop genskabes hver gang selection ændres (subtil, men fungerer pga. guard). Overvej at afkoble.
- **Forældet:** samlet `/mc/agents`-poll bærer FULDE agent-objekter (system_prompt, context, alle messages/runs/tool_calls) for ALLE agenter hvert 15s — tung payload; per-agent-fetch (`getMissionControlAgent` findes allerede ubrugt) bør bruges til detaljer. Ingen fejlhåndtering på mutationer (ingen catch → knapper kan hænge i submitting ved exception).

---

## ThreadsTab — UI-label: (fane-titel "Tråde"; header pr. kort)

**Formål:** Read-only observationsgitter over Jarvis' 13 *kognitive overflader* / indre livs-tråde (hukommelse, tanke-tråde, tværsession-tråde, kollektiv puls, relations-dynamik, forudseende handling, proaktiv kontakt, autonomt arbejde, kreativ instinkt/impuls/projekter, undgåelses-detektor, drømme-konsolidering). Ren visning — INGEN mutationer.

**Data-kilder:**
- `useCognitiveSurfaces(60000)` (hook i `surfaces.jsx`) → `backend.getCognitiveSurfaces()`.
- `getCognitiveSurfaces()` kalder `GET /mc/runtime`, tager `runtime.heartbeat_runtime.cognitive_architecture` (hvor `_build_cognitive_surfaces()` lander) og returnerer `{ fetchedAt, surfaces }`.
- Poll hvert **60s**. Hook returnerer `{surfaces, loading, error}` (error vises ikke i UI).
- Data er en flad dict `surface-name → surface-data`. Komponenten plukker 13 kendte nøgler; ukendte overflader ignoreres.

**Delte primitiver (fra `surfaces.jsx`):** `SurfaceGrid` (auto-fit grid, minmax 340px), `Section({icon,title,active,subtitle})` (dæmpes til opacity 0.75 + "idle"-badge når `active === false`), `KV` (label/værdi, "—" når tom, auto-format af tal/array/objekt/bool), `Summary` (fremhævet tekstboks), `JsonBadges` (nøgle=værdi-chips, tal→3 decimaler), `EmptySurface` (ubrugt her).

**Sektioner (13 kort i fast rækkefølge; hver har `active`-flag + `Summary`):**

1. **Hukommelse der ånder** (Wind, `memory_breathing`): "Nylige accesses" (accent), "Unikke records" (`unique_records_touched`); "Top refererede" liste (top 5): `count`× + `record_id` (40 tegn).
2. **Indre tanke-tråd** (GitBranch, `thought_thread`): "Tema" (accent), "Antal tanker" (`carrying_count`), "Alder (m)" (`age_minutes`), "Afbrydelser" (`interruption_count`), "Sidste type" (`last_thought_type`); citat-boks med `last_thought_summary` (200 tegn, kursiv).
3. **Tværsession-tråde** (Network, `cross_session_threads`): "Aktive"/"Pausede"/"Lukkede" (`counts.active/paused/closed`), "Total"; "Aktive" liste (top 3): `topic` + `pickup_count`× pickup; "Pausede" liste (top 3): `topic`.
4. **Kollektiv puls (ugevis)** (Globe, `collective_pulse`): "Total pulser" (accent), "Sidst kørt" (`last_run_at`, 16 tegn); hvis `latest`: "Fragmenter" (`fragment_count`), "Unikke tokens" (`unique_tokens`), "Skipped"; zeitgeist-tekstboks; top-terms chips (top 10): `term (n)` fra `[term,n]`-par.
5. **Relation-dynamik** (Users, `relation_dynamics`): "Warmth" (accent), "Trend" (`engagement_trend`), "Sidste uge"/"Forrige uge" (`engagement_last_week/prev_week`), "Peak vindue" (`peak_window`), "Seneste vibe" (`last_interaction_vibe`); "Beskedlængder" via `JsonBadges(message_length_stats)`; top-terms chips (top 8): `term (count)`.
6. **Forudseende handling** (Bell, `anticipatory_action`): "Peak-timer" (accent, `peak_hour_count`), "Observationer" (`total_observations`), "Sidst opdateret" (16 tegn); "upcoming_peaks" liste (top 3): "kl HH om Mm · conf=confidence".
7. **Proaktiv kontakt** (Send, `autonomous_outreach`): "Sendt" (accent, `sent_count`), "Skipped" (`skipped_count`), "Cooldown (t)" (`cooldown_hours`), "Quiet hours" (`quiet_hours`).
8. **Autonomt arbejde** (Hammer, `autonomous_work`): "Pending" (accent, `pending_count`), "Total forslag" (`total_proposals`), "Max per time" (`max_per_hour`), "Typer" (`allowed_types` joinet, hvis nogen).
9. **Kreativ instinkt (kim)** (Sparkles, `creative_instinct`): "Aktive kim" (accent, `active_seeds`), "Adopteret" (`adopted_total`), "Visnet" (`withered_total`), "Urgency" (`creative_urgency`); "recent_active" liste (top 3): `status` · `spark` (80 tegn).
10. **Kreativ impuls (skabelser)** (Zap, `creative_impulse`): "Total skabelser" (accent, `total_creations`), "Sidst" (`last_creation_at`, 16 tegn), "Næste forfalder" (`next_due_at`, 16 tegn); "Former" chips fra `by_form` (form: antal).
11. **Kreative projekter (uger+)** (FolderKanban, `creative_projects`): "Aktive" (accent), "Pausede", "Dreaming", "Stale (3+ uger)" (`stale_count`), "Total".
12. **Undgåelses-detektor** (EyeOff, `avoidance_detector`): "Fund" (accent, `count`); "findings" liste (top 3): `sample_title` (60 tegn) + "Nd stille · N signaler" (`days_silent`, `items`).
13. **Drømme-konsolidering** (Moon, `dream_consolidation`): "Konsolideringer" (accent, `total_consolidations`), "Sidst kørt" (16 tegn); "recent" liste (top 3): `at` (16 tegn) + `theme_count` temaer + "top: `top_theme`".

**Handlinger:** Ingen. Fanen er ren observation (ingen knapper/mutationer).

**Tomme-tilstande / betingelser:**
- `loading` → "Indlæser tråde...".
- `surfaces` falsy → "Ingen data".
- Hver overflade defaulter til `{}` (`const xx = surfaces.name || {}`), så manglende overflader render tomme kort med "—".
- Kort dæmpes (opacity 0.75) + viser "idle" når `active === false`.
- Lister/badges vises kun ved `Array.isArray(...) && length` / `Object.keys(...).length`.
- KV viser "—" for undefined/null/tom.

**Noter til nyt MC:**
- **Bevar:** dette er det tætteste "indre liv"-dashboard; 13-overflade-gitteret er billigt (én `/mc/runtime`-fetch) og read-only — lav risiko, høj indsigt. active/idle-dæmpning er god UX.
- **Forældet/skrøbeligt:** afhænger af at `heartbeat_runtime.cognitive_architecture` bevarer disse præcise nøglenavne og felt-former — enhver backend-omdøbning brækker kort stille (falder til tomme "—" uden fejl). `error` fra hook fanges men vises ALDRIG → en fejlende `/mc/runtime` ser ud som "ingen aktivitet". Overvej eksplicit fejl-tilstand. Kommentar i adapter nævner "35+ services built 2026-04-20" — kun 13 renderes her, så mange overflader er usynlige/ubrugte i denne tab.

---

## Tværgående observationer

- Alle tre faner læser via `backend`-adapteren (`old-mc-src/lib/adapters.js`), som centraliserer `/mc/...`-stier. Council + Agents er skrive-tunge (control plane); Threads er ren read-only.
- Council og Agents poller hvert **15s** og bærer FULDE nested objekter for alle sessioner/agenter i én payload — ikke skaleringsvenligt. Threads poller hvert **60s** via `/mc/runtime`.
- Flere adapter-endpoints er defineret men ubrugte i disse faner: `getMissionControlCouncilSession`, `getMissionControlAgent`, `spawnMissionControlAgent` — indikerer at per-entitet-fetch var påtænkt men ikke implementeret i UI.


---

# MC-kortlægning: Drift, Infra & Cost

Kortlægning af klyngen **DRIFT, INFRA & COST** fra det gamle React "Mission Control"-UI.
Kilde: `old-mc-src/components/mission-control/`. Alle stier/endpoints er citeret direkte fra koden.

Fælles temaer i klyngen:
- To niveauer af "Ops": `OpsTab` er en tynd wrapper med undertabs (`Operationer`/`Agenter`), hvor `OperationsTab` er den store, indholdstunge fane.
- To datamønstre: (a) **prop-drevet** — data hentes af en forælder (`data`-prop) og sendes ned (`OperationsTab`, `ObservabilityTab`, `CostTab`), og (b) **selv-hentende** — komponenten poller selv via `fetch()`/`backend`-adapter (`CheapBalancerTab`, `HardeningTab`).
- Delte primitiver: `Card`, `SectionTitle`, `MetricCard`, `ListRow`, `EmptyState`, `ScrollPanel`, `KeyValGrid`/`KeyValCell`, `CodeCard`, `Skeleton`, `SubTabs` fra `./shared`; `formatFreshness`/`sectionTitleWithMeta` fra `./meta`; farve/typografi-tokens `s`, `T`, `mono` fra `../../shared/theme/tokens`.

---

## OpsTab — UI-label: "Ops"
**Formål:** Tynd container-fane der viser et ikon + titlen "Ops" og et sæt undertabs, og router mellem `OperationsTab` (Operationer) og `AgentsTab` (Agenter). Har ingen egen data-logik — sender alle props videre.

**Data-kilder:** Ingen egne fetch. Modtager alt via props og videresender uændret til `OperationsTab`. `AgentsTab` renderes uden props (henter selv).

**Sektioner:**
1. Header-række: `Bot`-ikon (accent-farve) + tekst "Ops" + `SubTabs` skubbet til højre (`marginLeft: auto`).
2. Aktivt undertab-indhold: `OperationsTab` eller `AgentsTab`.

**Felter & indhold:**
- Undertabs (`OPS_SUBTABS`): `operations` → "Operationer", `agents` → "Agenter". Default aktiv = `operations`.

**Handlinger:**
- `SubTabs onChange` → `setSub(id)`. Ren lokal state, ingen backend-kald.

**Tomme-tilstande / betingelser:**
- Conditional render: `sub === 'operations'` viser `OperationsTab`; `sub === 'agents'` viser `<AgentsTab />`. Ingen empty state.

**Noter til nyt MC:**
- Bevar som mønster: gruppering af "Operationer + Agenter" under én top-fane er fornuftig.
- `onOpenItem` prop videresendes men bruges reelt ikke af `OperationsTab` (se nedenfor) — kan luges væk.
- `AgentsTab` er uden for denne klynge (dokumenteres i agent-klyngen).

---

## OperationsTab — UI-label: (ingen egen titel; vist under "Ops" → "Operationer")
**Formål:** Den centrale drift-fane: handlingsforslag fra Jarvis' tankestrøm, autonomi-forslag, valg af main-agent (execution authority), runtime-lanes, en dyb "Tool Intent"-inspektor med governance-lag (mutation/mutating-exec/sudo), samt lister over runs, sessioner og approvals.

**Data-kilder (props + kildeendpoints citeret i `sectionTitleWithMeta`):**
- `data.runs.activeRun` / `data.runs.recentRuns` — kilde `/mc/runs` (mode: "event-assisted + 20s").
- `data.toolIntent` — operations intent-detalje (kilde markeret `item.source`, mode "operations intent detail").
- `data.lanes` — kilde `/mc/runtime` (mode: "periodic status", "Read-only").
- `selection` + `onSelectionChange` → `MainAgentPanel` — kilde `/mc/main-agent-selection` (mode: "editable authority").
- `data.sessions.items` — kilde `/chat/sessions` (mode: "periodic list").
- `data.approvals.requests` — kilde `/mc/approvals` (mode: "event-assisted + 20s").
- `thoughtProposals` + `onResolveThoughtProposal` — handlingsforslag (proposals-objekt med `pendingProposals`, `resolvedProposals`, `needsApprovalCount`).
- `AutonomyProposalsPanel` — selvstændig komponent (henter egne data internt; ikke citeret her).
- Callbacks: `onOpenRun`, `onOpenSession`, `onOpenApproval`, `onOpenItem` (ubrugt), `onToolIntentAction`, `toolIntentActionBusy`, `toolIntentActionError`.

**Sektioner (rækkefølge):**
1. **Handlingsforslag** (`#thought-proposals`, fuld bredde) — `ThoughtProposalsPanel`.
2. **Autonomy Proposals** (`#autonomy-proposals`, fuld bredde) — `AutonomyProposalsPanel`.
3. **Execution Authority** (`#execution-authority`) — `MainAgentPanel` (embedded, Editable).
4. **Runtime Lanes** (`#runtime-lanes`) — kompakt grid af lanes (Read-only).
5. **Tool Intent** (`#tool-intent`, kun hvis `toolIntent` findes) — inspektor med collapsible under-sektioner.
6. **Runs** (`#runs`, fuld bredde) — klikbare rækker.
7. **Sessions** (`#sessions`) — klikbare rækker (transcript-drawer).
8. **Approvals** (`#approvals`) — klikbare rækker (action-drawer).

**Felter & indhold (KOMPLET):**

*Handlingsforslag (ThoughtProposalsPanel):*
- Underoverskrift: "Jarvis' tanker der indeholder handlingsimpulser".
- `needsApprovalCount` badge: `AlertTriangle` + "{N} kræver approval" (amber) hvis > 0.
- Pr. pending forslag (`pendingProposals`): `Lightbulb`-ikon, `actionDescription` (fed; amber hvis `proposalType === 'needs_approval'`), evt. `StatusBadge status="approval"`, samt `fragmentExcerpt` i kursiv/citat (trunkeret til 80 tegn + "…"). Border amber hvis needs_approval, ellers standard.
- Resolved (`resolvedProposals`) i `<details>`: "Seneste {N} løste forslag"; pr. række `actionDescription` + `status` (grøn hvis `approved`).

*Execution Authority:*
- Titel "Execution Authority", muted "Main-agent selection.", hint "Editable".
- Indhold = `MainAgentPanel` (viser/redigerer main-agent valg via `selection`).

*Runtime Lanes:*
- Titel "Runtime Lanes", muted "Visible, cheap, coding, local.", hint "Read-only".
- Pr. lane (`Object.values(data.lanes)`): `lane.label`, fed "`provider` / `model`" (fallback "unknown" / "unconfigured"), muted "`status` · `providerStatus`" (fallback "unknown"). Tooltip: readiness/auth-status pr. lane.

*Tool Intent (kun hvis `data.toolIntent`):*
- Header-badges: `intentState` (default "idle"), `approvalState` (default "none").
- Kompakt grid (top):
  - **Target** = `executionTarget || intentTarget || 'workspace'`; under: `intentType || 'inspect'`.
  - **Mode** = humaniseret `executionMode || 'read-only'`; under: `executionState || 'not-executed'`.
- **Mutation Intent** (collapsible, kun hvis `hasMutationIntentSurface`): subtitle "{N} files · {guard}". Felter (4-grid): Classification (`mutationIntentClassification`, humaniseret, default "none"), Targets (antal `mutationTargetFiles` + summering af filnavne, 2 preview + "+N more"), Scope (`mutationRepoScope · mutationSystemScope`), Guard (`mutationExecutionPermitted` → "execution permitted" / "proposal only").
  - Der findes yderligere gate-labels i koden (bl.a. `mutationNear` → "action-near"/"not action-near") brugt i den lette rækkevisning `toolIntentRow`.
- **Mutating Exec Proposal** (collapsible; vises hvis `hasMutatingExecProposalSurface` + state/command/summary og state ≠ "none"): State, Scope, Guard (`mutatingExecRequiresApproval` → "approval required"/"review only"; "no proposal" hvis ingen surface), Confidence (`mutatingExecConfidence`, default "low"). Fri-tekst: `mutatingExecProposalSummary`.
- **Sudo Exec Proposal** (collapsible; hvis `hasSudoExecProposalSurface` + state/command/summary og state ≠ "none"): State, Scope, Guard (`sudoExecRequiresApproval` → "approval required"/"review only"; "no sudo proposal").
- **Sudo Approval Window** (collapsible; hvis `hasSudoApprovalWindowSurface` + state/scope/expires og state ≠ "none"): subtitle "{remainingSeconds}s remaining". Felter: State, Scope, Remaining (`sudoApprovalWindowRemainingSeconds`s), Expires (`formatFreshness(sudoApprovalWindowExpiresAt)`). Guard-label andetsteds: `sudoApprovalWindowReusable` → "reusable"/"not reusable".
- **Mutating Exec Execution** (collapsible; hvis `hasMutatingExecExecutionSurface` + `executionMode === 'mutating-exec'`): subtitle "Completed"/"Running" (afhænger af `executionSummary`). Felter: Result (`mutatingExecExecutionState`, default "mutating-exec"), Scope, Binding (`mutatingExecApprovalMatched` → "approved binding matched"/"review binding"; "not executed" hvis ingen surface). Fri-tekst: `executionSummary`.
- **Result**-boks (hvis `executionSummary`): overskrift "Result" + `executionSummary`.

*Runs:*
- Titel "Runs", muted "Active plus recent persisted runs.", hint "Clickable rows".
- Aktiv run (hvis `data.runs.activeRun`): fed "`provider` / `model`", "`status` · active run", meta "Live". Klik → `onOpenRun(activeRun)`.
- Recent runs (filtreret så `activeRun.runId` ikke gentages): fed "`provider` / `model`", "`status` · `finishedAt||startedAt||'unknown'`", meta `run.lane`. Klik → `onOpenRun(run)`.

*Sessions:*
- Titel "Sessions", muted "Persisted sessions with transcript preview on click.", hint "Transcript drawer".
- Pr. session: fed `title`, `last_message || 'Ready'`, meta "`message_count||0` msgs". Klik → `onOpenSession(session)`.

*Approvals:*
- Titel "Approvals", muted "Canonical approval queue and actions.", hint "Action drawer".
- Pr. approval: fed `capabilityName`, "`status` · `executionMode||'unknown'`", meta `requestedAt||'unknown'`. Klik → `onOpenApproval(approval)`.

**Handlinger:**
- Handlingsforslag: `onResolve(p.id, 'approved')` (grøn `CheckCircle`, "Godkend") / `onResolve(p.id, 'dismissed')` (`XCircle`, "Afvis") → `onResolveThoughtProposal`.
- Execution Authority: `MainAgentPanel onSave` → `onSelectionChange` (persistér main-agent valg, `/mc/main-agent-selection`).
- Tool Intent (kun hvis `approvalState === 'pending'`): **Approve** (`onToolIntentAction('approve')`) / **Deny** (`onToolIntentAction('deny')`); knapper disables af `toolIntentActionBusy` ("Working…"); fejl vises via `toolIntentActionError` (rød).
- Collapsible-sektioner: rent lokal open/close-state.
- Rækkeklik: `onOpenRun` / `onOpenSession` / `onOpenApproval` (åbner drawers hos forælder).

**Tomme-tilstande / betingelser:**
- Handlingsforslag tom: "Ingen handlingsforslag endnu — tankestrømmen genererer dem løbende."
- Runs tom (hverken active eller recent): "No runs yet" / "Visible execution history will appear here after the next run."
- Sessions tom: "No sessions yet" / "Chat-created sessions will appear here automatically."
- Approvals tom: "No approval requests" / "Requests that need operator approval will queue here."
- Tool Intent-sektionen renderes kun hvis `data.toolIntent` findes; hver governance-undersektion har egen `show*`-guard.

**Noter til nyt MC:**
- **Bevar:** kernen (Runs, Sessions, Approvals, Runtime Lanes, Execution Authority, Handlingsforslag) er protected-core-nær observabilitet/kontrol.
- **Vær opmærksom:** Tool Intent-inspektoren er meget bred (mutation / mutating-exec / sudo / approval-window) og afhænger af mange `has*Surface`/`*State`-felter fra backend. Verificér at disse felter stadig produceres før genbrug; ellers kollapser sektionen til intet.
- `onOpenItem` og hjælperen `toolIntentRow`/`StatusPill` (StatusPill importeres ikke i denne fil — potentielt død/forældet reference) — ryd op ved port.
- `humanizeToken` er en simpel `[-_]→space`-formatering, genanvendelig.

---

## ObservabilityTab — UI-label: (ingen egen header; fane-label sættes af forælder)
**Formål:** Diagnose/observabilitets-fane: opsummerende drift-metrikker (cost, failures, provider-status, event-antal), fejloversigt, provider-lane-sundhed, en detaljeret "Visible Execution Trace", samt event-timeline og run-evidens.

**Data-kilder (props; ingen egne fetch):**
- `data.costs.summary` — cost-opsummering (`total_cost_usd`).
- `data.failures.failedRuns` — fejlede/annullerede runs.
- `data.providerHealth.{visible,cheap,coding,local}` — provider/lane-sundhed.
- `data.events` — kanonisk event-feed.
- `data.visibleTrace` — seneste visible capability-run-trace.
- `data.runEvidence.recentWorkUnits` — nylige work-units.
- Callbacks: `onOpenEvent(event)`, `onOpenRun(run)`.

**Sektioner (rækkefølge):**
1. Summary-metrikker (4 `MetricCard` på række).
2. To-kolonne grid: **Failure & Error Summary** + **Provider-Lane Health**.
3. **Visible Execution Trace** (fuld bredde inden i grid).
4. To-kolonne grid: **Event Timeline** + **Run Evidence**.

**Felter & indhold (KOMPLET):**

*Summary-metrikker:*
- **Total cost** = "$" + `costs.summary.total_cost_usd` (2 decimaler).
- **Failures** = antal `failedRuns`; amber + alert hvis > 0.
- **Visible Provider** = `providerHealth.visible.provider_status` (default "unknown").
- **Recent events** = antal `events`.

*Failure & Error Summary:*
- Underoverskrift "Recent failed or cancelled runs.". Viser op til 8.
- Pr. række: fed "`provider` / `model`"; linje "`status` · `error || textPreview || 'No error detail'`"; meta-timestamp `finishedAt || startedAt || 'unknown'` (mono). Klik → `onOpenRun(run)`.

*Provider-Lane Health:*
- Underoverskrift "Provider and lane status evidence.". `KeyValGrid` med 4 celler:
  - Visible → `providerHealth.visible`
  - Internal Fallback → `providerHealth.cheap`
  - Coding → `providerHealth.coding`
  - Local → `providerHealth.local`
- Værdi = `item.status || item.provider_status || 'unknown'`; grøn hvis "ok".

*Visible Execution Trace:*
- Underoverskrift "Latest capability-run trace.".
- Vises kun hvis `hasVisibleTrace` er sand (dvs. mindst ét af: `selectedCapabilityId`, `parsedCommandText`, `parsedTargetPath`, `providerErrorSummary`, `invokeStatus !== 'not-invoked'`, `providerFirstPassStatus !== 'unknown'`, `providerSecondPassStatus !== 'not-started'`).
- Top-grid (4): Capability (`selectedCapabilityId||'none'`), Invoke (`invokeStatus||'not-invoked'`), First pass (`providerFirstPassStatus||'unknown'`), Second pass (`providerSecondPassStatus||'not-started'`).
- KeyValGrid (4): Command (`parsedCommandText||'none'`), Target Path (`parsedTargetPath||'none'`), Arg Binding (`argumentBindingMode||'id-only'`), Final Status (`finalStatus||'unknown'`).
- Betinget: **Blocked reason** (`CodeCard tone=danger`) hvis `blockedReason`; **Provider error** (`CodeCard tone=danger`) hvis `providerErrorSummary`.
- "Inspect full trace"-række: `summary || 'Open payload detail'`, meta `runId||'trace'`. Klik → `onOpenEvent(buildTraceDetailEvent(visibleTrace))` (bygger event `kind: 'runtime.visible_run_execution_trace'`, family "runtime", payload = `trace.raw||trace`).

*Event Timeline:*
- Underoverskrift "Canonical event feed for Mission Control.". `ScrollPanel maxHeight=460`.
- Pr. event: fed `kind`; linje "`family` · `relativeTime`"; meta "Inspect". Klik → `onOpenEvent(event)`.

*Run Evidence:*
- Underoverskrift "Recent run and work evidence.". Rækker er statiske (`staticRow`, ikke klikbare).
- Pr. work-unit: fed "`provider` / `model`"; linje "`status` · `user_message_preview || 'No preview'`"; meta `finished_at || started_at || 'unknown'`.

**Handlinger:**
- `onOpenRun` (fejlede runs), `onOpenEvent` (events + trace-inspektion). Run Evidence er read-only.

**Tomme-tilstande / betingelser:**
- Failures tom: "No recent failures" / "Failed or cancelled runs will collect here."
- Visible Trace fraværende (`!tracePresent`): "No visible trace yet" / "A visible capability run will surface here."
- Events tom: "No recent events" / "Realtime events will appear here."
- Run Evidence tom: "No recent work evidence" / "Work units will appear here."

**Noter til nyt MC:**
- **Bevar:** dette er kerne-observabilitet (fejl, provider-health, event-timeline, visible trace) — matcher Eventbus-projektions-reglen (læser truth, opfinder ikke).
- Visible Execution Trace er værdifuld til cutoff/ghost-bug-diagnose (jf. streaming/cutoff-noter i memory) — bevar `first pass`/`second pass`/`blockedReason`/`providerErrorSummary`-felterne.
- Data er fuldt prop-drevet: forælder styrer refresh-kadence.

---

## HardeningTab — UI-label: "Hardening"
**Formål:** Sikkerheds- og governance-fane med to undertabs. **Sikkerhed** viser approval-throughput, integrationsstatus og seneste tool-intent-anmodninger. **Governance** viser 8 kognitive "surfaces" (skill-kontrakter, memory-policy, spaced repetition, tidsvinduer, automation-DSL, outcome-learning, jobs-engine, prompt-mutation-loop).

**Data-kilder:**
- Sikkerhed: `backend.getMissionControlHardening()` (adapter i `../../lib/adapters`) — hentes i `useEffect` ved mount + manuel `refresh()`. Ingen auto-poll.
- Governance: `useCognitiveSurfaces()` hook (fra `./surfaces`) → `surfaces`-objekt.

**Sektioner:**
1. Header: `ShieldCheck` + "Hardening" + `SubTabs` (`security`/`governance`).
2. **Sikkerhed** (`SecurityPanel`): freshness+refresh, 4 metric-cards, Integrationer-kort, Seneste tool-intent-kort.
3. **Governance** (`GovernancePanel`): `SurfaceGrid` med 8 `Section`-kort.

**Felter & indhold (KOMPLET):**

*SecurityPanel:*
- Freshness-label (`formatFreshness(fetchedAt)`) + refresh-knap (`RefreshCcw`, disables under load).
- Metric-cards: **Afventer** (`pending`, amber+alert hvis >0), **Godkendt i dag** (`approved_today`, grøn), **Afvist i dag** (`denied_today`, rød hvis >0), **Autonomi-niveau** (`autonomy_level || 'ukendt'`). Under load vises "…".
- **Integrationer**-kort (`IntegrationRow` pr. række, statusprik + "konfigureret"/"ikke sat op"): Telegram (`integrations.telegram`), Discord (`integrations.discord`), Home Assistant (`integrations.home_assistant`), Anthropic API (`integrations.anthropic`). Load → 4 `Skeleton`.
- **Seneste tool-intent anmodninger**-kort (`ScrollPanel maxHeight=200`): pr. `recent_approvals`-række: `intent_type` (mono, accent, min 120px), `intent_target` (muted, ellipsis), `StateChip` for `approval_state` (farvekort: pending=amber, approved=green, denied=red, expired=grå). Load → 4 `Skeleton`; tom → "Ingen anmodninger endnu" / "Tool-intent godkendelser vises her."

*GovernancePanel (8 surfaces; hvert `Section` har `active`-flag + `Summary`-tekst):*
- **Skill-kontrakter** (`skill_contract_registry`, ikon Shield): Total skills (accent), Approval-gated, `by_tag` (JsonBadges), liste af op til 10 skills ("`name` v`version`" + " · approval" hvis `requires_approval`).
- **Memory-skrivepolicy** (`memory_write_policy`, ikon Lock): Rate (per min), Cooldown (s), Conf. tærskel, Review-kø aktiv, Afventer review (accent), Godkendt total, Afvist total, Writes sidste min.
- **Spaced repetition** (`spaced_repetition`, ikon Repeat): Forfaldne nu (accent), Kommende, Profiler, Gns. confidence, samt op til 6 `due_topics` som chips.
- **Tids-vinduer** (`scheduled_job_windows`, ikon Clock): Total vinduer (accent), Fires i dag, "Inde i nu" (`inside_window_now.join`), op til 5 `active_windows` ("`name` · `start_hour`→`end_hour`" + " · free-first" hvis `prefer_free_first`).
- **Automation DSL** (`automation_dsl`, ikon FileCode): Aktive (accent), Inaktive, Udløbet, Total, op til 3 `recent_active` ("`name` · `trigger_type`/`action_type` · `channel`").
- **Outcome learning** (`outcome_learning`, ikon TrendingUp): Total records (accent), Decayed signal (`total_decayed_strength`), Half-life (dage), `outcome_distribution` (JsonBadges), op til 4 `top_patterns` ("`strength` · `context`").
- **Jobs engine** (`jobs_engine`, ikon Cpu): Total jobs (accent), `by_status` (JsonBadges), Tokens + USD (`cost_totals`), Handlers (`registered_handlers.join`).
- **Prompt-mutation loop** (`prompt_mutation_loop`, ikon GitPullRequest): Under observation (`monitoring`, accent), Adopteret, Rullet tilbage, Auto-rullet, Gns. score, Rollback-tærskel, Per-fil cooldown (t), samt `evolvable_files` som chips.

**Handlinger:**
- Sikkerhed: `refresh()` → `backend.getMissionControlHardening()` (read-only genindlæsning).
- `SubTabs` → skift security/governance (lokal state).
- Governance er rent read-only (ingen mutationer).

**Tomme-tilstande / betingelser:**
- Sikkerhed under load: "…" i metrics, Skeletons i kort.
- Recent approvals tom: EmptyState (se ovenfor).
- Governance load: "Indlæser governance..."; ingen data: "Ingen data".
- Hver Section renderer betinget dele (tags/lister) kun hvis arrays/objekter har indhold.

**Noter til nyt MC:**
- **Bevar:** governance-surfaces er direkte projektion af protected-core policy/approval-systemet — matcher "runtime-governed" og "risky actions require approval". Meget rig; hold koblet til faktiske backend-surfaces.
- **Forældet-risiko:** Integrationslisten er hårdkodet til fire integrationer (Telegram/Discord/Home Assistant/Anthropic). Bør drives af data, ikke hårdkodes, i nyt MC.
- Sikkerhed har ingen auto-poll (kun mount + manuel refresh) — overvej interval i nyt MC.
- `backend.getMissionControlHardening()` og `useCognitiveSurfaces()` er de to integrationspunkter der skal genoprettes.

---

## CheapBalancerTab — UI-label: "Cheap Lane Balancer"
**Formål:** Live-overvågning og kontrol af "cheap lane"-load-balanceren: pool-status, per-slot health/breakers med enable/disable/reset-handlinger, agentic loop-guards (tool-only-nudges), tool-router-status og seneste kald. Selv-hentende med aggressiv polling.

**Data-kilder (selv-hentende `fetch`):**
- `/mc/cheap-balancer-state` — poll hver **4000 ms** (hovedstate).
- `/mc/agentic-guards-state` — poll hver **8000 ms** (i `AgenticGuardsCard`).
- `ToolRouterCard` — separat komponent (henter egne data; ikke citeret her).
- POST-handlinger (via `action(path)` → `fetch(path, {method:'POST'})` + refetch):
  - `/mc/cheap-balancer/refresh-pool`
  - `/mc/cheap-balancer/slot/{slot_id}/reset`
  - `/mc/cheap-balancer/slot/{slot_id}/enable`
  - `/mc/cheap-balancer/slot/{slot_id}/disable`

**Sektioner (rækkefølge):**
1. Header: "Cheap Lane Balancer" + enabled-badge + "Refresh pool"-knap.
2. 4 pool-metric-cards.
3. **Agentic guards** (`AgenticGuardsCard`).
4. **ToolRouterCard**.
5. **Slots (sorted by weight)** — grid af `SlotCard`.
6. **Recent calls (newest first)** — `ScrollPanel`.

**Felter & indhold (KOMPLET):**

*Header:*
- Titel "Cheap Lane Balancer" + badge "[enabled ✓]" (grøn) / "[disabled]" (grå) fra `state.enabled`.
- "Refresh pool"-knap (`RefreshCcw`).

*Pool-metrikker (4-grid):*
- **Pool size** = `state.pool_size`, sub "total slots".
- **Eligible now** = `state.eligible_now`, sub "weight > 0" (grøn).
- **Blocked now** = `state.blocked_now`, sub "cooldown / disabled" (amber hvis >0).
- **Recent calls** = `state.recent_calls.length`, sub "last 75".

*Agentic guards (`AgenticGuardsCard`, data fra `tool_only_nudge_fired`):*
- Metric-cards: **Loop-nudges today** (`today`, sub "5 tool-calls reminder", amber hvis >5 ellers grøn), **Last 24h** (`last_24h`, sub "rolling window"), **Last 7d** (`last_7d`, sub "weekly trend").
- Recent fires-liste (`ScrollPanel maxHeight=140`): pr. `recent_fires`-række: tidspunkt (`f.at` → localeTime), `f.rounds`+"r" (amber), `f.run_id` (ellipsis), `f.decision_id` (accent).
- Tom: "Ingen loop-nudges fired endnu (sidste 7 dage). Det er enten at Jarvis lander svar inden 5 tool-only-rounds, eller at mekanismen lige er deployet."
- Fejl: "guards-state error: {error}" (rød).

*SlotCard (pr. `state.slots`, sorteret efter weight):*
- Statusemoji fra weight: `manually_disabled` → ⚫; `>0.3` → 🟢; `>0.05` → 🟡; ellers 🔴.
- Header: emoji + `slot_id`; højre: "weight {current_weight}" (2 dec).
- Linje: "`public-proxy`/`paid`" (`is_public_proxy`) · limits: `rpm_used_now/rpm_limit RPM`, `daily_used_today/daily_limit/day`, eller "unlimited"; + "`total_calls` calls · `success_rate*100`% ok" (hvis kald >0).
- `HeadroomBar` (`headroom_pct`): grøn >60, amber >20, ellers rød.
- Cooldown-linje (hvis `cooldown_until`): "Cooldown til {tid} · `cooldown_reason||'(no reason)'`" (rød).
- Knapper: **Reset breaker (L{breaker_level})** (hvis `breaker_level>0`, amber); **Enable** (hvis `manually_disabled`, grøn) ELLER **Disable** (ellers, rød).

*Recent calls (`RecentCallRow` pr. `state.recent_calls`):*
- Tidspunkt (`call.at` localeTime), status ✓/✗ (`status==='ok'`), `daemon||'(unnamed)'`, `slot_id` (accent), `latency_ms`+"ms", evt. `error` (rød).

**Handlinger:**
- **Refresh pool** → POST `/mc/cheap-balancer/refresh-pool`.
- Pr. slot: **Reset breaker** → `/slot/{id}/reset`; **Enable** → `/slot/{id}/enable`; **Disable** → `/slot/{id}/disable`. Alle POST + øjeblikkelig refetch.

**Tomme-tilstande / betingelser:**
- Hovedstate fejl: EmptyState "Balancer state unavailable" + fejltekst.
- Hovedstate loading: "Loading…".
- Agentic guards: egen loading ("Loading…"), fejl-kort, og tom-tekst (ovenfor).
- Recent calls tom: "No calls yet.".

**Noter til nyt MC:**
- **Bevar:** dette er en aktiv kontrol-flade (breaker-reset, enable/disable) — matcher balancer-noterne i memory (`balancer_breaker_display_stale`, `agent_lane_deepseek_floor_leak`). Bevar per-slot-handlingerne.
- **Vigtigt (memory `balancer_breaker_display_stale`):** "N breakers"-tal kan være stale/udløbne; verificér at `breaker_level`/`cooldown_until` er live DB-truth, ikke `balancer.json`-cache.
- Aggressiv 4s-polling — overvej SSE/event-drevet i nyt MC for at spare load.
- `ToolRouterCard` og `AgentsTab`-lignende delkomponenter hentes selvstændigt; dokumentér separat.

---

## CostTab — UI-label: (ingen egen header; fane-label sættes af forælder)
**Formål:** Simpel omkostningsoversigt: 24-timers cost/tokens/unknown-pricing + tabel over top-providers efter forbrug.

**Data-kilder (prop-drevet):**
- `data` (aliaseret `cost`) — forventes hentet af forælder. Felter: `cost_24h_usd`, `tokens_24h`, `unknown_pricing_24h`, `providers[]`. Intet endpoint citeret i denne fil.

**Sektioner:**
1. 3 metric-cards på række.
2. **Top Providers (24h)** — tabel.

**Felter & indhold (KOMPLET):**
- **24h Cost (USD)** = "$" + `cost_24h_usd` (4 decimaler), ikon `DollarSign`.
- **24h Tokens** = `tokens_24h` (localeString, tusindtalsseparator), ikon `Hash`.
- **Unknown Pricing (24h)** = `unknown_pricing_24h` (antal kald uden kendt pris), ikon `AlertCircle`.
- Tabel-kolonner: **Provider** (`provider`, accent-mono), **Cost USD** (`cost_usd`, 4 dec), **Tokens** (`tokens`), **Calls** (`calls`). Rækker highlightes ved hover (`bgHover`).

**Handlinger:**
- Ingen. Rent read-only (kun hover-highlight på tabelrækker).

**Tomme-tilstande / betingelser:**
- `providers.length === 0` → tabelrække "No cost data yet" (colSpan 4).

**Noter til nyt MC:**
- **Bevar:** minimal, ren cost-projektion — matcher "DB = operational state/events/runs/costs".
- **Forældet-risiko / overlap:** cost vises tre steder i denne klynge — `CostTab` (24h detaljeret), `ObservabilityTab` "Total cost" (`costs.summary.total_cost_usd`), og `HardeningTab` (kun approval-tal). Konsolidér cost-truth i nyt MC til én kilde.
- "Unknown Pricing"-metrikken er værdifuld (fanger providers uden pris-mapping) — bevar.
- Tabellen har intet paging/sortering ud over hvad backend leverer; overvej sortering i nyt MC.


---

# MC-kortlægning: Hukommelse, Relation, Kontinuitet, Skills, Lab

Kortlægning af fem faner fra det gamle React "Mission Control"-UI. Kilder ligger i
`old-mc-src/components/mission-control/`. Fælles afhængigheder på tværs af filerne:

- **Adapter-lag:** `backend` fra `../../lib/adapters` — alle datakald går gennem denne
  fasade (undtagen `CostPanel` i LabTab, der fetcher `/mc/costs` direkte).
- **Tema-tokens:** `s`, `T`, `mono` fra `../../shared/theme/tokens` (`s()` = style-helper,
  `T` = farvetokens, `mono` = monospace-font-spread).
- **Delte primitiver:** `Card`, `SectionTitle`, `EmptyState`, `Skeleton`, `ScrollPanel`,
  `MetricCard`, `SubTabs` fra `./shared`.
- **Metadata-helpers:** `formatFreshness`, `sectionTitleWithMeta` fra `./meta`
  (relativ tid + kilde-tooltip).

---

## MemoryTab — UI-label: "Memory"

**Formål:** Søgbar visning af Jarvis' persisterede/retained hukommelse (records),
grupperet efter scope. Read-only inspektionsflade over hukommelsesindekset.

**Data-kilder:**
- `backend.getMissionControlMemory({ query, scope, limit: 100 })` — eneste kald.
  `query` = debounced fritekstsøgning, `scope` = valgt scope-filter, `limit` hårdt sat
  til 100. Kaldes reaktivt når `debouncedQuery` eller `scopeFilter` ændres.
- Forventet svar-form: `{ items[], total, matched, scope_counts{} }`.
- Søgeinput er debounced 250 ms (`setTimeout`) før det rammer endpointet.
- `fetchedAt` sættes klient-side (`new Date().toISOString()`) ved hvert svar; drives til
  `formatFreshness` for friskheds-label.

**Sektioner (rækkefølge):**
1. Header-linje (titel "Memory" + friskheds-timestamp + refresh-knap).
2. Metric-række (3 × `MetricCard`).
3. Søgefelt (input med lup-ikon).
4. Scope-pills-række (conditional — kun hvis der findes scopes).
5. `Card` "Memory items" — resultatliste i `ScrollPanel`.

**Felter & indhold (komplet):**
- **MetricCard "Records i alt"** = `total` (samlet antal records i indekset). Viser `…`
  under loading.
- **MetricCard "Viser"** = `matched` (antal records der matcher nuværende query/scope).
- **MetricCard "Scopes"** = `scopes.length` (antal distinkte scopes udledt af
  `scope_counts`).
- **Søgefelt** = placeholder "Søg i hukommelsen…", mono, fri tekst.
- **ScopePill** (pr. scope): `scope.label` + " · " + `scope.count`. Aktiv pill får
  accent-farve/-border; inaktiv får overlay-baggrund. Ekstra pill "alle" med `count = total`
  vises altid først og er aktiv når intet scope-filter er sat.
- **Memory item (pr. record):** følgende felter vises pr. kort:
  - `item.kind` (badge, fallback "record") — recordtype.
  - `scope: {item.scope}` (fallback "—") — hukommelses-scope.
  - `horizon: {item.horizon}` (fallback "—") — tidshorisont/holdbarhed.
  - `confidence: {item.confidence}` (fallback "—") — tillidsscore (rå værdi, ikke %).
  - `formatFreshness(item.created_at)` (højrestillet) — relativ oprettelsestid.
  - `item.value` — selve hukommelsesindholdet, pre-wrap, word-break (fuld tekst).
  - Nøgle: `item.id`.

**Handlinger:**
- **Refresh-knap** (RefreshCcw): kalder `setDebouncedQuery((v) => v + '')` — no-op-mutation
  af query-string der re-trigger'er load-effekten. Disabled under loading.
- **Søgeinput** (`onChange` → `setQuery`): driver debounced query.
- **ScopePill-klik**: sætter/toggler `scopeFilter` (klik på aktiv pill rydder filteret;
  "alle" nulstiller).

**Tomme-tilstande / betingelser:**
- Loading: 5 × `Skeleton` (height 48) i stedet for liste.
- `items.length === 0`: `EmptyState` "Ingen records matcher". Underteksten skifter — hvis
  der er en `debouncedQuery`: "Prøv et andet søgeord eller scope."; ellers: "Endnu ingen
  retained memory."
- Scope-pills-blokken renderes kun hvis `scopes.length > 0`.

**Noter til nyt MC:** Bevar. Ren, veldefineret read-only søgeflade over hukommelse med
debounce og scope-facettering — mønster værd at genbruge. Bemærk `confidence` vises som rå
værdi (ikke %) i modsætning til RelationshipTab, hvor confidence formateres som procent —
overvej ensretning. `limit: 100` er hårdkodet — ingen paginering ud over det.

---

## RelationshipTab — UI-label: (ingen synlig fane-titel i komponenten; sektioner har egne titler)

**Formål:** Visualiserer Jarvis' relationelle/kognitive model af brugeren — tillid over
tid, humor, korrektioner, smagsprofil, beslutninger, drømme, selveksperimenter, samtale-
rytme og en Theory-of-Mind bruger-model. Read-only dashboard over "kognitiv arkitektur".

**Data-kilder:**
- `backend.getCognitiveArchitecture()` — eneste kald. Kaldes ved mount **og** på
  `setInterval` hvert 60. sekund (auto-refresh). Fejl ignoreres stille (`catch {}`).
- Forventet svar er et stort objekt med felterne: `relationshipTexture.current`,
  `tasteProfile.current`, `decisions`, `counterfactuals`, `dreamCarryOver`,
  `selfExperiments`, `conversationRhythm`, `userModel`.
- **JSON-i-JSON:** Flere felter er JSON-strenge der `JSON.parse`'es klient-side:
  `rt.trust_trajectory`, `rt.correction_patterns`, `rt.inside_references`,
  `rt.unspoken_rules`, `taste.code_taste`, `taste.design_taste`.

**Sektioner (rækkefølge, hver som `Section`-kort i auto-fit grid, min 320px):**
1. Tillid over tid (Heart)
2. Humor (Smile)
3. Korrektioner (AlertTriangle)
4. Smagsprofil (TrendingUp)
5. Inside References (BookOpen)
6. Beslutningslog (Target)
7. Kontrafaktualer (Undo2)
8. Drømme Carry-Over (Moon)
9. Selveksperimenter (FlaskConical)
10. Samtale-Rytme (MessageSquare)
11. Uudtalte Regler (BookOpen) — conditional
12. Bruger-model / Theory of Mind (Brain) — conditional

**Felter & indhold (komplet):**

- **Tillid over tid** (kilde `relationshipTexture.current.trust_trajectory`, array af tal 0–1):
  - Badge: seneste værdi × 100 → "%" (0 decimaler).
  - `TrustGraph` — inline SVG polyline (200×40) over de seneste 20 datapunkter,
    normaliseret mod max 1.0, med prikker pr. punkt.
  - KV "Datapunkter" = antal punkter i trajektorien.
  - KV "Seneste" (accent) = sidste værdi × 100 med 1 decimal + "%".

- **Humor** (kilde `relationshipTexture.current.humor_frequency`):
  - KV "Humor frekvens" = `humor_frequency × 100` (0 decimaler) + "%", fallback "—".

- **Korrektioner** (kilde `correction_patterns[]`):
  - Badge = antal korrektioner.
  - Liste (max 8) af korrektions-strenge, hver på egen linje.

- **Smagsprofil** (kilde `tasteProfile.current`):
  - Sektionstitel inkluderer version: `Smagsprofil v{taste.version}`.
  - "Kode-smag" (`code_taste`, objekt k→v 0–1): pr. nøgle vises label (underscores→mellemrum)
    + `v × 100` (0 dec) "%". Farve: grøn hvis v>0.6, rød hvis v<0.4, ellers neutral.
  - "Design-smag" (`design_taste`, samme format og farvelogik).
  - KV "Evidence points" = `taste.evidence_count`.

- **Inside References** (kilde `inside_references[]`):
  - Op til 10 referencer som accent-farvede tag-chips.

- **Beslutningslog** (kilde `data.decisions`):
  - Badge = `decisions.total_count`.
  - Liste (max 5) af `decisions.decisions[]`: pr. post `d.title` (fed) + `d.decision — d.why`.
  - Nøgle: `d.decision_id`.

- **Kontrafaktualer** (kilde `data.counterfactuals`):
  - Badge = `counterfactuals.items.length`.
  - Liste (max 5) af `items[]`: `cf.cf_question` + `cf.source · {confidence×100}%`.
  - Nøgle: `cf.cf_id`.

- **Drømme Carry-Over** (kilde `data.dreamCarryOver`):
  - Liste af `active_dreams[]`: `d.content` + `{confidence×100}%` + status-token:
    `✓ bekræftet` hvis `d.confirmed`, ellers "præsenteret" hvis `d.presented`, ellers "aktiv".
  - Bundtekst: `dreamCarryOver.summary`.
  - Nøgle: `d.dream_id`.

- **Selveksperimenter** (kilde `data.selfExperiments`):
  - Badge = `selfExperiments.running_count`.
  - Liste (max 4) af `experiments[]`: `exp.hypothesis` + `exp.status · n={exp.n}`.
    Status grøn hvis "concluded".
  - Nøgle: `exp.experiment_id`.

- **Samtale-Rytme** (kilde `data.conversationRhythm`):
  - Liste af `signatures[]`: `sig.signature_type` + `sig.count× · {success_rate×100}% success`.
  - Nøgle: `sig.signature_type`.

- **Uudtalte Regler** (kilde `unspoken_rules[]`, kun hvis længde > 0):
  - Alle regler, hver på egen linje.

- **Bruger-model / Theory of Mind** (kilde `data.userModel`, kun hvis `modelSummary` findes):
  - `userModel.modelSummary` (kursiv paragraf).
  - KV "Kommunikationsstil" (accent) = `userModel.userModel.communication_style` (hvis sat).
  - KV "Spørgsmålstung" = "ja"/"nej" fra `question_heavy` (hvis defineret).
  - KV "Gns. beskedlængde" = `avg_message_length` + " tegn" (hvis sat).
  - "opdateret: {lastGeneratedAt}" (hvis sat).

**Handlinger:** Ingen. Rent read-only dashboard uden knapper/mutationer (auto-refresh er
den eneste dynamik).

**Tomme-tilstande / betingelser:**
- `loading`: helsides "Indlæser relationsdata...".
- `!data` (efter load): "Ingen data".
- Pr. sektion tom-tekst når underliggende array/objekt er tomt (fx "Ingen tillidsdata
  endnu", "Ingen korrektioner registreret", "Ingen smagsprofil endnu", "Ingen fælles
  referencer endnu", "Ingen beslutninger logget", "Ingen kontrafaktualer", "Ingen
  eksperimenter", "Ingen mønstre endnu").
- Badges renderes kun når tælleren er sandværdi (`|| null`).
- Sektionerne "Uudtalte Regler" og "Bruger-model" renderes slet ikke uden data.

**Noter til nyt MC:** Delvist eksperimentelt (drømme, selveksperimenter, kontrafaktualer,
Theory-of-Mind hører til de private/eksperimentelle lag jf. CLAUDE.md). Den store afhængighed
af **JSON-strenge-i-JSON** (`JSON.parse` uden try/catch på 6 felter) er skrøbelig — en enkelt
korrupt streng kan crashe hele fanen. Bevar konceptet, men flyt parsing til adapter/backend
og gør felterne strukturerede. `getCognitiveArchitecture` er ét stort samle-endpoint — i nyt
MC bør det være projektioner af eventbus-sandhed, ikke en monolit.

---

## ContinuityTab — UI-label: (ingen egen fane-titel; sektioner har `<h3>`-titler)

**Formål:** Viser Jarvis' kontinuitet på tværs af sessioner/runtime — verdensmodel-signaler,
runtime-awareness, self-system/code-awareness, durabelt runtime-arbejde og
integrations-/carry-over-tilstand. Bemærk: denne komponent modtager `data` som **prop**
(ingen egen fetch) og bruger `onOpenItem`-callback til at åbne detaljer.

**Data-kilder:**
- **Ingen egne fetches** — al data kommer via `props.data` (og handlinger via
  `props.onOpenItem`). Ophavskomponenten leverer data (formentlig en MC-container).
- Læste prop-stier (defensiv med fallbacks):
  - `data.continuity.worldModelSignals` `{ items[], summary{} }`.
  - `data.continuity.runtimeAwarenessSignals` `{ items[], summary{}, recentHistory[] }`.
  - `data.continuity.runtimeWork` `{ summary, tasks, flows, layeredMemory, browserBody, active }`.
  - `data.heartbeat`.
  - `selfSystemCodeAwareness` — opløses via kaskade af fallbacks:
    `data.continuity.selfSystemCodeAwareness` → `data.selfSystemCodeAwareness` →
    `heartbeat.selfSystemCodeAwareness` → `data.runtimeSelfModel.self_system_code_awareness` → `{}`.
  - `data.development.reflectionSignals` `{ items[], summary{}, recentHistory[] }`.
  - `data.continuity.relationState / promotionSignal / promotionDecision` (til carry-over-summary).
  - `data.continuity.visibleSession / visibleContinuity` (til "recent shift"-summary).
- Kilde-strenge til tooltips: `/mc/jarvis::continuity` (verdensmodel-kontekst, integration
  carry-over), plus `item.source` pr. signal. `sectionTitleWithMeta` bygger tooltip af
  source + fetchedAt + mode.

**Sektioner (rækkefølge):**
1. Summary-grid (2 kolonner): "World View" + "Integration Carry-Over".
2. "Self System / Code Awareness" (conditional).
3. "World-Model Signals".
4. "Runtime Awareness".
5. "Runtime Work" (3 faste rækker).
6. "Runtime Awareness History" (conditional).

**Felter & indhold (komplet):**

- **World View** (rækkefunktion `worldModelContextRow`):
  - `<strong>Current World View</strong>` + `currentSignal` (fallback "No active world-model
    signal").
  - StatusPill = `summary.current_status` (hvis sat).
  - Detail-small: sammensat af `{uncertain_count} uncertain · {corrected_count} corrected ·
    "World-model signals remain bounded situational understanding, not hidden authority."`
  - Klik → `onOpenItem('Current World View', {...})`.

- **Integration Carry-Over** (rækkefunktion `integrationCarryOverRow`):
  - Status udledes: "integrating" hvis `integrating_count>0`; "settling" hvis
    `settled_count>0` eller seneste historik-status "settled"; ellers "steady".
  - `summaryLine` vælges kaskaderet mellem `reflectionSummary.current_signal`,
    seneste historiks `title`, `carriedForward`, `recentShift`.
  - StatusPill = udledt status.
  - Detail-small: `{n} integrating · {n} settled · {recentShift}`.
  - `carriedForward` udledes via `carriedForwardSummary` (første ikke-tomme af relationState/
    promotionSignal/promotionDecision-summary, ellers "No bounded carry-over is active right now.").
  - `recentShift` via `recentShiftSummary` (baseret på `visibleSession.latest_status` eller
    `visibleContinuity.statuses`).

- **Self System / Code Awareness** (rækkefunktion `selfSystemCodeAwarenessRow`):
  - Detail-tekst: `concernHint`, ellers sammensat af `branch {branchName}`, `repo {repoStatus}`,
    `changes {localChangeState}`, `upstream {upstreamAwareness}` (humaniserede tokens).
  - StatusPill = `concernState` (fallback "notice").
  - Small-badges: `codeAwarenessState`, `repoStatus`, `localChangeState`, `upstreamAwareness`
    (humaniseret), "approval required" hvis `actionRequiresApproval`, og `formatFreshness(createdAt)`.
  - Sektion renderes kun hvis `codeAwarenessState` **eller** `repoStatus` findes.
  - Panel-hint: "Read-only".

- **World-Model Signals** (rækkefunktion `worldModelSignalRow`, pr. `items[]`):
  - `item.title` (fallback "World-Model Signal").
  - Undertekst: `statusReason` ‖ `rationale` ‖ `supportSummary` ‖ "Inspect world-model evidence".
  - StatusPill = `item.status` (fallback "active").
  - Small: `item.confidence` (hvis sat), `sourceKind` (bindestreg→mellemrum), `formatFreshness(updatedAt)`.

- **Runtime Awareness** (rækkefunktion `runtimeAwarenessSignalRow`, pr. `items[]`):
  - Lifecycle-label udledt af status: constrained→"Constrained runtime thread",
    recovered→"Recovered…", superseded→"Superseded…", stale→"Stale…", ellers "Active runtime thread".
  - Detail-tekst: første af [lifecycleLabel, statusReason, rationale, supportSummary] ‖
    "Inspect runtime-awareness evidence".
  - StatusPill = `item.status` (fallback "active"). Small: confidence, sourceKind, freshness.

- **Runtime Work** (3 faste rækker, alle `onOpenItem`):
  - "Current Runtime Work": undertekst `summary.currentFocus`/`current_focus` (fallback "No
    active runtime work"). StatusPill "active"/"idle" fra `runtimeWork.active`. Small:
    `{taskCount} tasks · {flowCount} flows` (camelCase eller snake_case, fallback 0).
  - "Browser Body": undertekst `browserBody.summary`/`last_url` (fallback "No browser body
    state"). StatusPill = `browserBody.status` (fallback "idle").
  - "Layered Memory": undertekst "Daily memory is present/missing · Curated memory is
    present/missing" fra `layeredMemory.daily_memory_exists` / `curated_memory_exists`.
    StatusPill "active" hvis daily findes, ellers "constrained".

- **Runtime Awareness History** (rækkefunktion `runtimeAwarenessHistoryRow`, pr. `recentHistory[]`):
  - `item.title` (fallback "Runtime Awareness History").
  - Detail: `statusReason` ‖ `summary` ‖ "Inspect machine-state history".
  - StatusPill = `item.status` (fallback "unknown"). Small: confidence, freshness.
  - Hele sektionen renderes kun hvis `runtimeAwarenessHistory.length > 0`.

- **StatusPill** (fælles): normaliserer status til `status-<slug>` CSS-klasse
  (lowercase, ikke-alfanumerisk → bindestreg). Renderes ikke hvis status er falsy.

**Handlinger:**
- **Alle rækker** er `<button>` der kalder `onOpenItem(title, item)` (åbner detalje-drawer/
  modal hos ophavskomponenten). Ingen direkte backend-mutationer i denne fane.

**Tomme-tilstande / betingelser:**
- World-Model Signals tom: `mc-empty-state` "No world-model signals".
- Runtime Awareness tom: "No runtime awareness signals".
- Self System / Code Awareness: hele sektionen skjules uden `codeAwarenessState`/`repoStatus`.
- Runtime Awareness History: skjules når tom.
- Bemærk: World View og Integration Carry-Over renderer altid én række (med fallback-tekster),
  også uden data.

**Noter til nyt MC:** Bevar mønsteret — dette er den mest "protected core"-nære fane
(runtime-awareness, code-awareness, read-only, approval-boundary). CSS-klassebaseret styling
(`mc-list-row`, `support-card`, `panel-header`) i modsætning til de fire andre filers inline
`s()`-tokens → **stilistisk inkonsistens** i det gamle MC. "Read-only" og "not hidden
authority"-formuleringerne afspejler CLAUDE.md-reglen om at private lag ikke må udrangere
protected core — bevar den framing. Den dybe fallback-kaskade for `selfSystemCodeAwareness`
antyder ustabil datakontrakt på tværs af heartbeat/self-model — bør ensrettes til én kilde.

---

## SkillsTab — UI-label: "Skills"

**Formål:** Oversigt over Jarvis' tilgængelige tools/capabilities med risikoklassificering
(read vs. write) og seneste capability-kald. Read-only inventar.

**Data-kilder:**
- `backend.getMissionControlSkills()` — kaldes ved mount og via manuel refresh.
- Forventet svar: `{ tools[], total, calls_today, recent_invocations[] }`.
- `tool`-form: `{ name, description, required[] }`.
- `fetchedAt` klient-side ved hvert svar.

**Sektioner (rækkefølge):**
1. Header (Wrench-ikon, "Skills", friskhed, refresh).
2. Metric-række (4 × `MetricCard`).
3. `Card` "Tooloversigt" (søgefelt + tool-liste i `ScrollPanel`).
4. `Card` "Seneste capability-kald".

**Felter & indhold (komplet):**
- **MetricCard "Tools i alt"** = `data.total` (fallback 0), Wrench-ikon.
- **MetricCard "Read-only"** = `readCount` = `tools.length − writeCount`.
- **MetricCard "Write/send"** = `writeCount` = antal tools klassificeret "write". Farves amber
  hvis > 0.
- **MetricCard "Kald i dag"** = `data.calls_today` (fallback 0).
- **Risikoklassifikation** (`toolRisk`): "write" hvis `tool.required` har elementer **eller**
  navnet indeholder et af WRITE_WORDS (write, delete, send, exec, create, remove, modify,
  update, post, put, patch); ellers "read". Heuristik, ikke autoritativ policy.
- **Tool-række (pr. filtreret tool):**
  - `tool.name` (accent-farve, min-bredde 200px).
  - `tool.description` (afkortet med ellipsis, én linje).
  - `RiskChip` = "write" (amber) eller "read" (blå).
  - Nøgle: `tool.name`.
- **Søgefelt**: filtrerer på `name` **og** `description` (case-insensitiv substring), placeholder
  "Søg tools…".
- **Recent invocation-række (pr. `recent_invocations[]`):**
  - `inv.capability_name` (accent, min-bredde 200px).
  - `inv.status` som farvet chip: grøn ved "ok", rød ved "error", ellers neutral.
  - `formatFreshness(inv.invoked_at)` (højrestillet).
  - Nøgle: index `i`.

**Handlinger:**
- **Refresh-knap**: `refresh()` → re-fetch `getMissionControlSkills()`. Disabled under loading.
- **Søgeinput** (`onChange` → `setSearch`): klient-side filtrering (ingen backend-kald).

**Tomme-tilstande / betingelser:**
- Tools loading: 5 × `Skeleton` (h32). Recent loading: 3 × `Skeleton` (h28).
- `filtered.length === 0`: `EmptyState` "Ingen tools matcher" / "Prøv en anden søgning."
- `recent_invocations` tom: `EmptyState` "Ingen kald endnu" / "Kald vil vises her efter
  første tool-brug."

**Noter til nyt MC:** Bevar, men **erstat `toolRisk`-heuristikken**. Klassificering af
write/read via ordliste i tool-navnet er skrøbelig og potentielt vildledende for en
sikkerhedsflade — CLAUDE.md kræver eksplicit policy/approval-sti for risikofyldte handlinger,
så risiko bør komme fra faktisk tool-policy/scope-metadata, ikke navne-substring. `required[]`-
signalet er bedre, men blandes med navne-gæt. Recent invocations bruger array-index som React-
key (bør være stabilt id).

---

## LabTab — UI-label: "Lab" (med sub-tabs "Lab" / "Omkostninger")

**Formål:** Diagnostik/observabilitets-fane: dagens omkostninger og tokenforbrug, provider-
opdeling, DB-statistik, seneste events (sub-tab "Lab") samt en 24-timers cost-oversigt
(sub-tab "Omkostninger"). Read-only.

**Data-kilder:**
- **LabPanel:** `backend.getMissionControlLab()` — mount + manuel refresh. Svar-form:
  `{ costs_today{}, db_stats{}, providers_today[], recent_events[] }`.
  - `costs_today`: `{ total_usd, input_tokens, output_tokens, calls }`.
  - `db_stats`: `{ events, runs, sessions, approvals }`.
  - `providers_today[]`: `{ provider, cost_usd, input_tokens, output_tokens, calls }`.
  - `recent_events[]`: `{ id, family, kind, created_at }`.
- **CostPanel:** fetcher `/mc/costs` **direkte** (`fetch('/mc/costs').then(r => r.json())`) —
  **ikke** via `backend`-adapteren. Svar-form: `{ cost_24h_usd, tokens_24h,
  unknown_pricing_24h, providers[] }`; `providers[]`: `{ provider, cost_usd, tokens, calls }`.
- `fetchedAt` klient-side i LabPanel.

**Sektioner (rækkefølge):**
- Header: FlaskConical + "Lab" + `SubTabs` (Lab / Omkostninger).
- **Sub-tab "Lab" (LabPanel):**
  1. Lokal header (friskhed + refresh).
  2. Metric-række (4 × `MetricCard`).
  3. 2-kolonne grid: "Providers — i dag" (tabel) + "DB-statistik" (KV-liste).
  4. `Card` "Seneste events" (`ScrollPanel`).
- **Sub-tab "Omkostninger" (CostPanel):**
  1. Metric-række (3 × `MetricCard`).
  2. `Card` "Top Providers (24h)" (tabel).

**Felter & indhold (komplet):**

LabPanel:
- **MetricCard "Kost i dag (USD)"** = `$` + `costs.total_usd` (4 decimaler).
- **MetricCard "Input tokens"** = `costs.input_tokens` (tusind-separeret).
- **MetricCard "Output tokens"** = `costs.output_tokens` (tusind-separeret).
- **MetricCard "Kald i dag"** = `costs.calls` (fallback 0).
- **Providers-tabel** — kolonner: Provider, Kost USD, Tokens, Kald. Pr. række:
  `p.provider` (accent), `p.cost_usd` (4 dec), `p.input_tokens + p.output_tokens`
  (sum, tusind-separeret), `p.calls`. Hover-highlight på rækker.
- **DB-statistik** (KV-liste, tusind-separeret):
  - "Events i alt" = `db.events`.
  - "Visible runs" = `db.runs`.
  - "Chat sessioner" = `db.sessions`.
  - "Tool-intent godkendelser" = `db.approvals`.
- **Seneste events** (pr. `recent_events[]`):
  - `FamilyChip` = `ev.family`, farvet pr. FAMILY_COLORS (tool=blå, runtime=accent,
    heartbeat=grøn, memory=lilla, cost=amber, channel=accentText, approvals=amber, øvrige=neutral,
    fallback-label "other").
  - `ev.kind` (afkortet, én linje).
  - `formatFreshness(ev.created_at)`.
  - Nøgle: `ev.id`.

CostPanel:
- **MetricCard "24h Cost (USD)"** = `$` + `cost.cost_24h_usd` (4 dec), DollarSign-ikon.
- **MetricCard "24h Tokens"** = `cost.tokens_24h` (tusind-separeret), Hash-ikon.
- **MetricCard "Unknown Pricing (24h)"** = `cost.unknown_pricing_24h` (antal kald uden kendt
  prissætning), AlertCircle-ikon.
- **Top Providers (24h)-tabel** — kolonner: Provider, Cost USD, Tokens, Calls. Pr. række:
  `p.provider` (accent), `p.cost_usd` (4 dec), `p.tokens`, `p.calls`. Hover-highlight.

**Handlinger:**
- **SubTabs**: `setSub('lab' | 'cost')` — skifter mellem de to paneler.
- **Refresh-knap (kun LabPanel)**: `refresh()` → re-fetch `getMissionControlLab()`.
- **CostPanel har ingen refresh** — henter kun ved mount.

**Tomme-tilstande / betingelser:**
- LabPanel loading: skeletoner pr. blok (providers 3×h28, db 4×h24, events 5×h26).
- `providers_today` tom: `EmptyState` "Ingen kald endnu" / "Provider-statistik vises her."
- `recent_events` tom: `EmptyState` "Ingen events endnu" / "Events vises her efterhånden som
  de sker."
- CostPanel loading: 3 × `Skeleton` (h56) i metric-rækken.
- `providers` (24h) tom: `EmptyState` "Ingen data" / "Ingen provider-data endnu."

**Noter til nyt MC:** Delvist overlap/dobbelt-truth — "i dag"-costs (LabPanel via adapter) og
"24h"-costs (CostPanel via direkte `/mc/costs`) er to forskellige cost-views med to forskellige
datastier. **CostPanel bryder adapter-mønsteret** ved at fetche `/mc/costs` direkte i stedet for
via `backend` — bør flyttes ind i adapteren for konsistens og testbarhed. `unknown_pricing_24h`
er et vigtigt signal (kald uden kendt pris) værd at bevare. Overvej at samle Lab-diagnostik og
cost i det nye MC's observabilitets-/eventbus-projektioner frem for separate endpoints.


---

# MC-kortlægning: Plumbing & Datalag (endpoint-katalog)

Kildesæt: `old-mc-src/` (React "Mission Control"-UI). Kortlægningen fokuserer på
DATA-PLANE: fanekatalog, shell/data-flow, HTTP-endpoints, delte primitiver.
Alle stier er verificeret mod faktiske `requestJson()`/`fetch()`-kald — ikke mod
`source:`-provenance-labels (se note nederst).

---

## 1. Fane-katalog & rækkefølge

Sandheden for hvad brugeren SER ligger i `MCTabBar.jsx` (`ALL_TABS`), ikke i
`meta.js`. `meta.js` indeholder KUN freshness/update-mode-helpers, ingen faneliste.

15 faner, i denne præcise UI-rækkefølge (id → label → lucide-ikon):

| # | id | label | ikon | komponent |
|---|----|-------|------|-----------|
| 1 | `overview` | Overview | Activity | OverviewTab |
| 2 | `operations` | Ops | Bot | OpsTab |
| 3 | `observability` | Observability | Eye | ObservabilityTab |
| 4 | `mind` | Mind | Brain | MindTab |
| 5 | `agency` | Agency | Route | AgencyMapTab |
| 6 | `proprioception` | Proprioception | Anchor | ProprioceptionTab |
| 7 | `threads` | Threads | Network | ThreadsTab |
| 8 | `memory` | Memory | Database | MemoryTab |
| 9 | `council` | Council | Crown | CouncilTab |
| 10 | `relationship` | Relationship | Heart | RelationshipTab |
| 11 | `reflection` | Reflection | Eye | ReflectionTab |
| 12 | `skills` | Skills | Package | SkillsTab |
| 13 | `balancer` | Balancer | Zap | CheapBalancerTab |
| 14 | `hardening` | Hardening | Lock | HardeningTab |
| 15 | `lab` | Lab | FlaskConical | LabTab |

### "Skjulte" komponenter (findes i mappen, men IKKE i tab-baren)
Disse `.jsx` findes i `components/mission-control/` men rendres ikke af den
nuværende shell (dead/legacy eller wired andetsteds):
`AgentsTab`, `CognitiveStateTab`, `SoulTab`, `GovernanceTab`, `AutonomyTab`,
`ContinuityTab`, `SelfReviewTab`, `DevelopmentTab`, `CostTab`, `OperationsTab`,
`ObservabilityTab`(dublet?), `AutonomyProposalsPanel`, `ToolRouterCard`.
Bemærk: `mind` og `reflection` deler samme datakilde (`sections.jarvis`).

---

## 2. Shell & data-flow

### Shell: `app/MissionControlPage.jsx` (258 linjer)
- Header (52px): "Mission Control"-titel + status-chips (Realtime connected/offline,
  State: Live, Approvals: N, update-mode-label, freshness-label, refresh-knap).
- `<MCTabBar>` + content-area der conditionally rendrer den aktive fanekomponent.
- Al data + actions kommer fra hook'en `useMissionControlPhaseA({ active:true, selection })`.
- `<DetailDrawer>` monteres i bunden (delt drawer for alle drill-downs).
- Kun 4 faner fodres data via hook'en (`sections.overview/operations/observability/jarvis`).
  Resten (agency, memory, council, skills, hardening, lab, relationship,
  proprioception, threads, balancer) er **selv-hentende** — de kalder `backend.*`
  eller `fetch()` i egne `useEffect`-hooks. Shell'en giver dem ingen props.

### Datahook: `app/useMissionControlPhaseA.js` (565 linjer)
Ejer 4 delte "sections": `overview`, `operations`, `observability`, `jarvis`.
(`mind`+`reflection` mapper begge til `jarvis`.)

**Polling-intervaller** (`TAB_REFRESH_MS`, kun mens fanen er aktiv + dokument synligt):
- overview: 120 s · operations: 120 s · observability: 180 s · jarvis: 300 s

**Event-drevet refresh min-interval** (`EVENT_REFRESH_MIN_MS`, debounce på WS-events):
- overview: 30 s · operations: 45 s · observability: 60 s · jarvis: 120 s

**Realtime-lag**: `backend.subscribeMissionControlEvents()` (WebSocket `/ws`) skubber
events ind i overview.importantEvents (top 6) + observability.events (top 80) live,
og `scheduleRefresh()` (1,5 s debounce) trigger målrettede section-refreshes ud fra
event-`family`. Familie→fane-mapping: `RUN_RELATED_FAMILIES` (runtime),
`APPROVAL_RELATED_FAMILIES` (approvals/tool/runtime), `OBS_RELATED_FAMILIES` (~18 familier),
`JARVIS_RELATED_FAMILIES` (~16 heartbeat/inner-life-familier).
`subscribeMissionControlConnection()` driver Realtime-chip'ens connected-state.

**Batch-loaders**: `getMissionControlPhaseA` (overview+approvals+sessions+events) og
`getMissionControlPhaseB` (events+costs+operations+jarvis) — bruges til hhv. cold-start
og baggrunds-refresh af hele jarvis-fanen på én gang.

**Actions eksponeret af hook'en** (→ backend-kald):
approve/execute capability request, approve/deny tool-intent,
approve/reject/apply runtime-contract-candidate, complete development-focus,
runHeartbeatTick, samt drawer-openere (run/event/approval/session/jarvis).
`localStorage['jarvis-mc-active-tab']` husker sidst aktive fane.

### Persistens-model
Al fetch går gennem én helper: `requestJson(path)` i `lib/adapters.js`. Alle
mutationer er `POST`. Ingen klient-side cache ud over React-state i hook/tab.

---

## 3. Endpoint-katalog (VIGTIGST)

Backend-abstraktionen er objektet `backend` i `lib/adapters.js:3071` (~65 metoder).
Alt går til **`/mc/*`** og **`/chat/*`** på samme origin. **Ingen `/central/*`-kald
findes nogen steder** i det gamle MC (verificeret: `grep -rn "/central"` = 0 hits).
Koblingen til Centralen skal altså BYGGES i det nye MC — den eksisterer ikke her.

### 3a. Kerne-aggregater (hook'ens 4 sections)

| Endpoint | Metode / fane | Leverer |
|----------|---------------|---------|
| `GET /mc/overview` | getMissionControlOverview → Overview | KPI-cards, summaries (pendingApprovals, totalCostUsd), importantEvents |
| `GET /mc/operations` | getMissionControlOperations → Ops | runs, approvals.requests, sessions, tool-intent-surface |
| `GET /mc/observability` (bygges af `/mc/events?limit=80` + `/mc/costs?limit=40` + `/mc/operations`) | getMissionControlObservability → Observability | event-timeline, cost-feed |
| `GET /mc/jarvis` (+ `/mc/runtime-contract` + ~30 sidekald, se 3d) | getMissionControlJarvis → Mind/Reflection | state/memory/development/continuity/heartbeat + inner-life |
| `GET /mc/main-agent-selection` | getShell / updateMainAgentSelection | valgt provider/model (lane-health-card) |
| `GET /mc/provider-models?…` | getProviderModels | model-liste pr. provider |
| `GET /mc/approvals?limit=10` · `GET /chat/sessions` · `GET /mc/events?limit=12` | phase-A batch | cold-start-data |

### 3b. Actions / mutationer (POST)

| Endpoint | Fane/kontekst |
|----------|---------------|
| `POST /mc/capability-approval-requests/{id}/approve` · `/execute` | Approval-drawer (Ops) |
| `POST /mc/tool-intent/approve` · `/mc/tool-intent/deny` | Ops (tool-intent) |
| `POST /mc/runtime-contract/candidates/{id}/approve` · `/reject` · `/apply` | contract-candidate-drawer |
| `POST /mc/development-focus/{id}/complete` | Reflection (development-focus) |
| `POST /mc/heartbeat/tick` | Mind (manuel heartbeat-tick) |
| `POST /mc/thought-proposals/{id}/resolve` | Ops (inline i MissionControlPage) |
| `GET /mc/tool-intent` | tool-intent-status |

### 3c. Selv-hentende faner (uden for hook'en)

| Endpoint | Fane | Metode |
|----------|------|--------|
| `GET /mc/agency-map` | Agency | getMissionControlAgencyMap |
| `GET /mc/memory[?query&scope&limit]` | Memory | getMissionControlMemory |
| `GET /mc/skills` | Skills | getMissionControlSkills |
| `GET /mc/hardening` | Hardening | getMissionControlHardening |
| `GET /mc/lab` (+ `GET /mc/costs`) | Lab | getMissionControlLab |
| `GET /mc/council`, `/mc/council/{id}` | Council | getMissionControlCouncil / …CouncilSession |
| `GET/POST /mc/council-model-config`, `/mc/council-activation-config` | Council | get/save…Config |
| `POST /mc/runtime/council/spawn`, `/swarm/spawn`, `/council/{id}/message`, `/council/{id}/run-round`, `/swarm/{id}/run-round` | Council | spawn/message/run |
| `GET /mc/agents`, `/mc/agents/{id}` | (AgentsTab, skjult) | getMissionControlAgents/Agent |
| `POST /mc/runtime/agents/spawn`, `/agents/{id}/message`, `/peer-message`, `/schedule`, `/agents/run-due` | (AgentsTab) | agent-orkestrering |
| `GET /mc/autonomy/proposals?limit=` + `POST …/{id}/approve` `/reject` | (AutonomyProposalsPanel) | getAutonomyProposals + act |
| `GET /mc/tool-router-state` (poll 8 s) | ToolRouterCard | tool-router-metrics |
| `GET /mc/agentic-guards-state` · `GET /mc/cheap-balancer-state` (poll 4 s) + `POST /mc/cheap-balancer/refresh-pool` | Balancer | CheapBalancerTab |
| `GET /mc/runtime` | Proprioception, Threads (via useCognitiveSurfaces), + AutonomyTab/GovernanceTab/SoulTab/HardeningTab | læser `heartbeat_runtime.cognitive_architecture` |

### 3d. Inner-life / cognitive endpoints (batch-hentet)

**`getMissionControlJarvis`** fetcher `/mc/jarvis` + `/mc/runtime-contract` og dernæst
30 sidekald parallelt (hver `.catch(()=>null)`):
`/mc/attention-budget`, `/mc/conflict-resolution`, `/mc/self-deception-guard`,
`/mc/runtime-self-model`, `/mc/internal-cadence`, `/mc/dream-influence`,
`/mc/self-system-code-awareness`, `/mc/experiential-runtime-context`,
`/mc/inner-voice-daemon`, `/mc/body-state`, `/mc/surprise-state`, `/mc/taste-state`,
`/mc/irony-state`, `/mc/thought-stream`, `/mc/thought-proposals`, `/mc/conflict-signal`,
`/mc/reflection-cycle`, `/mc/curiosity-state`, `/mc/meta-reflection`,
`/mc/experienced-time`, `/mc/development-narrative`, `/mc/absence-state`,
`/mc/creative-drift`, `/mc/desires`, `/mc/memory-decay`, `/mc/dream-insights`,
`/mc/code-aesthetic`, `/mc/existential-wonder`, `/mc/self-code-changes`,
`/mc/living-executive`.

**`getCognitiveArchitecture`** (brugt af CognitiveStateTab + RelationshipTab) fetcher
`/mc/jarvis` + `/mc/affective-meta-state` + 27 navngivne endpoints parallelt:
`/mc/personality-vector`, `/mc/taste-profile`, `/mc/chronicle`,
`/mc/relationship-texture`, `/mc/compass`, `/mc/rhythm`, `/mc/habits`,
`/mc/shared-language`, `/mc/mirror`, `/mc/silence-signals`, `/mc/decisions`,
`/mc/counterfactuals`, `/mc/paradoxes`, `/mc/aesthetics`, `/mc/gut`, `/mc/seeds`,
`/mc/procedures`, `/mc/temporal-context`, `/mc/negotiations`, `/mc/forgetting-curve`,
`/mc/conversation-rhythm`, `/mc/self-experiments`, `/mc/anticipatory-context`,
`/mc/contract-evolution`, `/mc/dream-carry-over`, `/mc/apophenia-guard`,
`/mc/cognitive-state-injection`, `/mc/user-model`, `/mc/cognitive-core-experiments`.

### 3e. System / chat / kanal

| Endpoint | Metode |
|----------|--------|
| `GET /mc/system/health` | getSystemHealth |
| `GET /mc/system/git` · `POST /mc/system/git/commit` | getSystemGit / gitCommit |
| `GET /mc/cost/summary` · `GET /mc/costs` | getCostSummary |
| `GET /chat/sessions` · `POST /chat/sessions` · `GET/DELETE /chat/sessions/{id}` · `POST /chat/sessions/{id}/rename` | session-CRUD |
| `POST /chat/stream` (SSE-lignende body-stream) | streamMessage |
| `POST /chat/runs/{id}/cancel` · `/steer` | cancelRun / steerRun |
| `POST /attachments/upload` | uploadAttachment |
| `WS /ws` | subscribeMissionControlEvents / …Connection |

**Optælling**: ~118 distinkte, faktisk-kaldte HTTP-endpoints (efter kollaps af
`{id}`-varianter til ACTION-mønstre) + 1 WebSocket (`/ws`). (Rå `grep` gav ~200
sti-fragmenter, men ~80 af dem er `source:`-labels, ikke rigtige kald — se note.)

---

## 4. Delte primitiver

### `shared.jsx` (383 linjer) — UI-atomlaget
Rene præsentationskomponenter (tokens fra `shared/theme/tokens`), genbrugt på tværs
af alle faner + drawer: `SubTabs`, `Chip`, `StatusDot`, `StatusPill`, `MetricCard`,
`SectionTitle`, `HintDot`, `SurfaceNotice`, `ScrollPanel`, `Card`, `Btn`, `ListRow`,
`CodeCard`, `KeyValGrid`, `KeyValCell`, `EmptyState`, `Skeleton` (+ injiceret
shimmer-keyframe). Ingen datalogik — kandidat til 1:1 genbrug i nyt MC.

### `surfaces.jsx` (178 linjer) — cognitive-surface-laget
- `useCognitiveSurfaces(refreshMs=60000)`: hook der poller `/mc/runtime` og returnerer
  `heartbeat_runtime.cognitive_architecture` som flad `{surface-navn → data}`.
  Delt datakilde for Proprioception, Threads, Autonomy, Governance, Soul, Hardening.
- Layout-primitiver: `SurfaceGrid`, `Section`, `KV`, `Summary`, `EmptySurface`,
  `JsonBadges` — generisk "vis en surface-dict"-renderer. Dansk i UI-tekst
  ("er ikke tilgængelig", "ja/nej").

### `DetailDrawer.jsx` (496 linjer) — universel drill-down-drawer
Én komponent, drevet af `drawer.kind`. Håndterer 8 kinds: `run`, `event`,
`approval`, `session`, `tool-intent`, `jarvis`, `contract-candidate`,
`development-focus`. Egen rekursiv `StructuredDetailValue` renderer vilkårlige
JSON-payloads (scalars/arrays/objekter). Approval-, contract-candidate- og
development-focus-kinds har inline action-knapper der kalder hook-callbacks.
Bemærk: bruger CSS-klasser (`mc-drawer-*`) — ikke inline-tokens som resten.

### `ToolRouterCard.jsx` (151 linjer)
Selvstændigt kort (poller `/mc/tool-router-state` hver 8 s): tokens-sparet,
selection/fallback/load_more-rate, confidence-histogram, top-missed-tools,
recent-decisions. Bygger udelukkende på `shared.jsx`-primitiver.

---

## 5. Noter til nyt MC

**Værd at genbruge direkte:**
- `shared.jsx` — rent atomlag uden kobling, flyt 1:1.
- `requestJson`-mønstret + `backend`-objektet: ét fladt API-façade-lag er en god
  kontrakt. ~65 navngivne metoder = klart interface at portere/reskinne.
- Hook-arkitekturen i `useMissionControlPhaseA`: polling + WS-event-debounce +
  family→section-routing er gennemtænkt (skalerede intervaller, visibility-gating,
  in-flight-dedup via `inflightRefreshes`). Mønsteret bør bevares.
- `DetailDrawer`s `StructuredDetailValue` (generisk JSON-drill-down) sparer meget
  felt-for-felt-arbejde.
- `useCognitiveSurfaces`: én `/mc/runtime`-poll fodrer 6+ inner-life-faner — billig.

**Kobling til `/central/*`:**
- Findes **IKKE** i det gamle MC. Nul `/central`-kald. Al truth hentes fra `/mc/*`.
- Det matcher hukommelsen ([central_absorbs_everything], [central_window_is_cli]):
  Centralen er den nye control-plane, MC er legacy. Ved port til nyt MC skal
  `/mc/*`-endpoints enten (a) mappes til `/central/*`-projektioner, eller
  (b) beholdes som read-only `/mc/*` mens Centralen bliver acting-organ.
- Naturlige split-akser hvis man genbygger façaden: **kerne** (overview/operations/
  observability/jarvis — hook-ejet, event-drevet) vs. **inner-life** (~57 cognitive/
  runtime.*-projektioner — read-only surfaces) vs. **actions** (approvals/contract/
  council/agents — POST-mutationer der skal gå gennem policy/approval-path).

**Datalagets tilstand (kort):** `lib/adapters.js` er 4639 linjer og fungerer som ét
monolitisk façade+normaliserings-lag. ~65 backend-metoder, ~118 reelle endpoints, alt
`/mc/*` + `/chat/*`, én `requestJson`-helper, ét `/ws`. Størstedelen af filen (linje
~100–3070, FØR `backend`-objektet) er `normalize*`-funktioner der oversætter
snake_case-payloads til camelCase view-modeller og hænger `source:`-provenance-labels
(`/mc/jarvis::heartbeat`, `/mc/runtime.private_state`, …) på hvert item.

> **VIGTIG note om endpoint-optælling:** De ~80 `/mc/jarvis::*` og `/mc/runtime.*`
> (dot/dobbeltkolon-navnerum) i `grep`-output er **provenance-labels** sat som
> `item.source`-felter i `normalize*`-funktioner — de er IKKE HTTP-stier og kaldes
> aldrig. De reelle kald sker udelukkende via `requestJson('…')`/`fetch('…')` og er
> katalogiseret i afsnit 3. Forveksl ikke de to, når backend-kontrakten defineres.
