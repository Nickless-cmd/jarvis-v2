# UI ROADMAP — Jarvis V2

> ⚠️ **Status 2026-04-21:** NUVÆRENDE STATUS-sektionen nedenfor er fra
> 2026-04-03 og 18 dage bagud. For real-time overblik over hvad der er live,
> brug [CURRENT_STATUS.md](CURRENT_STATUS.md). Principper og overordnet plan
> her er stadig gyldige som reference.
>
> **Landet siden 2026-04-03:**
> - 5 nye MC-tabs (2026-04-20) til propriocetion-daemons
> - Webchat approval cards + tool result visibility
> - SSE streaming til chat, WebSocket til control plane (se TRANSPORTS.md)
> - Design tokens: theme.js i MC (teal #3d8f7c), CSS vars i webchat (warm earth)
>
> **Stadig åbent (Fase 1):**
> - Unified design tokens på tværs af MC og webchat
> - Keyboard shortcuts i begge apps
> - "Breathing dot" som live-indikator
> - Shared component library mellem MC og webchat
>
> ---

> Komplet plan for at bringe V2's UI op til feature-paritet med den gamle UI,
> tilføje bevidsthed-specifikke views, og bygge ting ingen af UI'erne har haft.
>
> Originalt dokument sidst opdateret: 2026-04-03

---

## Principper

```
1. Ét konsistent design system på tværs af MC og webchat
2. Det indre liv skal skinne igennem i chat — ikke kun i MC
3. Proaktivitet kræver notifikation — stum bevidsthed eksisterer ikke
4. Alt observerbart — men elegant, ikke data-dump
5. Jarvis' tilstand skal kunne aflæses på et splitsekund
6. Bruger-feedback feeder direkte ind i Jarvis' vækst
7. Responsivt — Jarvis skal være tilgængelig overalt
```

---

## NUVÆRENDE STATUS (Opdateret 2026-04-03)

### V2 mc-ui — Standalone prototype
- Simpel App.jsx med sidebar + content
- Fetcher `/mc/overview` + `/mc/events?limit=20`
- WebSocket til live event stream
- **Status: Minimal prototype — overgået af den integrerede MC**

### V2 apps/ui — Produktions MC (NY)
- **12 tabs**: Overview, Operations, Observability, Living Mind, Self-Review, Continuity, Cost, Development, Memory, Skills, Hardening, Lab
- **Shared components**: MetricCard, Chip, SectionTitle, DetailDrawer, MainAgentPanel, SecondaryPanels
- **Design tokens**: theme.js med dark mode, surface variants, accent (teal #3d8f7c)
- **Tab meta system**: Per-tab update strategi (entry + interval + event assist)
- **Detail Drawer**: Modal inspection af events, runs, approvals, tool intent, heartbeat ticks, development focus, contract candidates
- **Living Mind tab**: Embodied state, loop runtime, idle consolidation, dream articulation, prompt evolution, affective meta-state, epistemic runtime, subagent ecology, council runtime, adaptive planning/reasoning, dream influence, guided/adaptive learning
- **Self-Review tab**: Flow pipeline, self-deception guards, witness daemon, inner voice daemon, internal cadence, conflict resolution, self-knowledge
- **Continuity tab**: World model, runtime awareness, carry-over, self-system code awareness, temporal curiosity, consolidation targets, loyalty/attachment
- **Development tab**: Focus (editable), goals, reflection, inner signals, self-authored prompt fragments (dream-influenced), prompt proposal review light, contract candidates
- **Operations tab**: Execution authority (editable), runtime lanes, tool intent + mutation targets, approvals, runs, visible execution trace
- **Observability tab**: Event timeline med WebSocket feed, family filter, event detail, execution trace
- **Cost tab**: Provider breakdown, model cost per token, total tracking, per-session
- **Memory/Skills/Hardening/Lab tabs**: Skeletal men tilstede
- **Status: ~60% funktionel — fundament er solidt**

### V2 webchat
- 3-kolonne layout (StatusRail + main stage + right panel)
- SSE streaming chat med rolle-baseret styling
- Runtime inspector med 19 truth sections (udvidet markant)
- Capability management med invoke + approve workflow
- Agent selection med cascading selects (provider/model/auth)
- Readiness monitoring med provider connectivity checks
- Activity feed (sliding window, 6 events)
- WebSocket live connection state
- **Dansk sprog** konsekvent
- **Status: ~50% af den gamle UI's chat-features + nye unikke features**

### Design-status
- MC (apps/ui): Teal #3d8f7c accent, DM Sans, dark #111214
- Webchat: Warm earth #f2a65a + teal #74d3ae, IBM Plex Sans/Serif, dark #071316
- **Stadig to forskellige design-sprog** — men begge er mere modne end før
- MC har nu design tokens (theme.js) — webchat bruger CSS variables

---

## FASE 1: FUNDAMENT — Design system + kerne-navigation

*Mål: Ét konsistent design-sprog og grundlæggende navigation.*

| # | Feature | Hvad konkret | Status |
|---|---|---|---|
| 1.1 | Unified design tokens | Ét token-system (farver, fonts, spacing, radii, shadows) brugt i både MC og webchat. Centraliseret tokens.js | MC har theme.js ✅. Webchat har CSS vars. Mangler unified system |
| 1.2 | Sidebar med navigation | Nav menu: Chat, New Chat, Search, Memory, Skills, Mission Control. Konsistent på tværs | Webchat har StatusRail. MC har MCTabBar. Mangler unified navigation |
| 1.3 | Session management | Session-liste med rename, pin, archive, delete. Kontekstmenu (three-dots) | ❌ Mangler helt |
| 1.4 | Konsistent layout | 3-kolonne chat (sidebar + messages + right panel). MC med sidebar + tab content | Webchat: 3-kolonne ✅. MC: 2-kolonne (header + tabs + content) |
| 1.5 | Keyboard shortcuts | Cmd+K søg, Cmd+N ny session, Cmd+Shift+M åbn MC, Esc luk panels, Cmd+Enter send | ❌ Mangler |
| 1.6 | Shared component library | Chip, StatusDot, MetricCard, Btn, Card, IconBtn — genbruges overalt | MC har shared components ✅ (MetricCard, Chip, SectionTitle). Webchat har sine egne. Mangler deling |
| 1.7 | Breathing dot / online indicator | Logo med pulserende grøn dot der viser Jarvis er online | ❌ Mangler — webchat har status pills (Working/Idle) men ingen pulserende tilstedeværelse |

**Omfang:** 7 ændringer. Design-fundament + navigation.

---

## FASE 2: CHAT POLISH — Feature-paritet med gamle UI

*Mål: Chat-oplevelsen føles komplet og poleret.*

| # | Feature | Hvad konkret | Status |
|---|---|---|---|
| 2.1 | Message timestamps | Monospace "14:32" per besked | ❌ Mangler |
| 2.2 | Streaming cursor | Blinkende caret der viser Jarvis taler | ❌ Mangler — webchat viser "Streamer..." tekst |
| 2.3 | Tool call visualization | Skill name + grøn checkmark i messages | ❌ Mangler — men capability invocation events trackes |
| 2.4 | Stop button animation | Pulserende rød animation under processing | ❌ Mangler — stop-knap eksisterer men uden animation |
| 2.5 | TopBar | Session title, autonomy level chip, EXP mode, token rate, search/menu | Webchat har hero section med titel + status pills. Mangler topbar-polish |
| 2.6 | Autonomy level indicator | L1/L2/L3 chip med farve-coding (amber/blue/teal) | ❌ Mangler |
| 2.7 | Token rate display | Tokens/min badge — teal ved aktivitet, grå ved idle | ❌ Mangler |
| 2.8 | Search overlay | Session-søgning med fuzzy match | ❌ Mangler |
| 2.9 | Composer polish | Auto-grow textarea (max 160px), Plus/Mic buttons, Shift+Enter newline | Delvist ✅ — textarea (4 rows) + send/stop + disabled attach/dictate |
| 2.10 | Message animations | slideUp, msgIn entrance animations | ❌ Mangler |
| 2.11 | Contextual session menus | Three-dots → Rename, Pin/Unpin, Archive/Unarchive, Delete med click-outside dismiss | ❌ Mangler |
| 2.12 | Continuity sharing | Share/resume continuity på tværs af sessions | ❌ Mangler — session continuity trackes i backend men ingen UI |

**Omfang:** 12 ændringer. Chat bliver feature-komplet.

---

## FASE 3: RIGHT PANEL — Jarvis' ansigt i chatten

*Mål: Det indre liv synligt i chat-UI'en uden at åbne MC.*

| # | Feature | Hvad konkret | Status |
|---|---|---|---|
| 3.1 | System metrics | Provider, model, disk usage % bar, token rate | Delvist ✅ — readiness status med provider/model/auth vises i StatusRail + right panel |
| 3.2 | Emotional state display | 4-akset grid med progress bars: confidence, curiosity, frustration, fatigue. Med ikoner | ❌ Mangler — det er Jarvis' "ansigt" |
| 3.3 | Inner voice display | Summary card med thought count + seneste tanke | ❌ Mangler — inner voice data er i MC Living Mind tab |
| 3.4 | Open loops counter | Antal uafsluttede tanker/opgaver | ❌ Mangler — trackes i backend |
| 3.5 | Active skills counter | Hvad Jarvis kan lige nu | Delvist ✅ — workspace capabilities vises i runtime inspector med invoke/approve |
| 3.6 | Workspace scan indicator | Aktivitetsfase med progress og completed steps | ❌ Mangler |
| 3.7 | Attention spotlight | Hvad Jarvis fokuserer på lige nu — consciousness roadmap 1.6 | ❌ Nyt (ingen UI har haft dette) |
| 3.8 | Current desire/appetite | Hvad Jarvis har lyst til — consciousness roadmap 3.2 | ❌ Nyt |

**Omfang:** 8 ændringer. Right panel giver Jarvis et ansigt.

---

## FASE 4: MC KERNE — Tabs og dashboard

*Mål: Mission Control bliver et reelt kontrolpanel.*

| # | Feature | Hvad konkret | Status |
|---|---|---|---|
| 4.1 | Tab-system med router | MCTabBar med primary tabs + More dropdown. URL params for tab state | ✅ DONE — MCTabBar med 12 tabs + ikoner |
| 4.2 | Tab contracts | Per-tab config: mode (snapshot/actions/legacy), event types, reducer | ✅ DONE — meta.js med update strategier per tab |
| 4.3 | Overview tab | Metric cards (active runs, approvals, agents, alerts), recent events, scheduled jobs, health | ✅ DONE — summary grid, current activity, queue & cost, recent events |
| 4.4 | Runs tab | Run-tabel med status, trace ID, timestamps. Detail-view med steps og artifacts | ✅ Integreret i Operations tab med active + recent runs |
| 4.5 | Approvals tab | Queue med approve/reject/tier actions | ✅ Integreret i Operations tab med bounded approval state |
| 4.6 | Sessions/Channels tab | Channel list, detail, send message, terminate | ❌ Mangler stadig |
| 4.7 | Cost tab | Budget tracking, provider breakdown, token budgets, alerts, governance | ✅ DONE — provider breakdown, model cost, total tracking, per-session |
| 4.8 | EventSource upgrade | Multi-tab coordination via BroadcastChannel, ownership TTL, exponential backoff, stale detection | 🟡 Delvist — WebSocket med ping keepalive. Mangler BroadcastChannel coordination |
| 4.9 | Delta reducers | Incremental snapshot updates fra events — ikke full refetch | 🟡 Delvist — event assist triggers quiet reload. Ikke ægte delta |
| 4.10 | Action endpoints | POST/PATCH per tab for approve, reject, invoke, configure | ✅ DONE — approve, execute, invoke capabilities, update main agent, edit development focus |

**Omfang:** 10 features → **7 DONE**, 1 mangler, 2 delvist.

---

## FASE 5: MC BEVIDSTHED — Det indre liv visualiseret

*Mål: Consciousness roadmap'ens views bygges i MC.*

| # | Feature | Hvad konkret | Roadmap ref | Status |
|---|---|---|---|---|
| 5.1 | Cognition tab | Inner voice stream, dreams, goals, council positions, paradoxes, epistemic claims | Fase 1-2 | ✅ DONE — Living Mind tab viser alt dette |
| 5.2 | Signal-mønstre view | Cross-signal analyse — mønstre over tid, korrelationer | Fase 2.1 | ❌ Mangler — individuelle signaler vises men ingen cross-analyse |
| 5.3 | Regret historik | Fortrydelser, hvad de handlede om, hvad Jarvis lærte | Fase 2.2 | ❌ Mangler — epistemic state vises men regret-historik mangler |
| 5.4 | Self-model evolution | Domæne-confidence over tid — graf der viser vækst/skrumpning | Fase 2.5 | ❌ Mangler — snapshot vises men evolution over tid mangler |
| 5.5 | Desire/appetite graf | Jarvis' aktive lyster, intensitet, vokser/svinder over tid | Fase 3.2 | ❌ Mangler |
| 5.6 | Nysgerrighed tracker | Hvad undrer Jarvis sig over lige nu, videnshuller | Fase 3.1 | 🟡 Delvist — temporal curiosity i Continuity tab |
| 5.7 | Jarvis' agenda | TODO-liste genereret af Jarvis — hvad han synes er vigtigt | Fase 3.3 | ❌ Mangler |
| 5.8 | Boredom state | Produktiv kedsomhed, outreach-historik | Fase 3.6 | ❌ Mangler |
| 5.9 | Læringsplan | Curriculum learning — hvad Jarvis vil lære, progress | Fase 3.8 | 🟡 Delvist — guided/adaptive learning i Living Mind tab |
| 5.10 | Deception alerts | Når self-deception guard trigger — rationalisering vs. læring | Fase 2.8 | ✅ DONE — self-deception guards i Self-Review tab |
| 5.11 | Resiliens state | Psykologisk modstandskraft under vedvarende fejl | Fase 2.10 | ❌ Mangler |

**Omfang:** 11 features → **2 DONE**, 2 delvist, 7 mangler.

---

## FASE 6: MC TIDSDYBDE — Historie og kontinuitet

*Mål: Jarvis' historie og tidsoplevelse visualiseret.*

| # | Feature | Hvad konkret | Roadmap ref | Status |
|---|---|---|---|---|
| 6.1 | Chronicle narrativ | Jarvis' løbende selvbiografi — ikke logs men oplevelse | Fase 4.2 | ❌ Mangler — chronicle consolidation data er i backend |
| 6.2 | Hukommelses-fade view | Hvad Jarvis husker, hvad der fader, hvad der er forstærket | Fase 4.3 | ❌ Mangler — selective forgetting data er i backend |
| 6.3 | Circadian graf | Energi/fokus variation over døgnet | Fase 4.4 | ❌ Mangler |
| 6.4 | Fravær log | Hvornår brugeren var væk, hvad Jarvis tænkte i mellemtiden | Fase 4.5-4.6 | ❌ Mangler |
| 6.5 | Kanal state | Kontekst-flow på tværs af CLI, webchat, discord | Fase 4.9 | ❌ Mangler |
| 6.6 | Anticipations view | Jarvis' forventninger og om de holdt | Fase 4.12 | ❌ Mangler |
| 6.7 | Mood timeline | Indre tilstand over dage/uger — ikke punkter men en kurve | Fase 1.2 | ❌ Mangler — affective meta-state snapshot vises men ingen timeline |
| 6.8 | Timeline visualisering | Temporal view: hvornår Jarvis tænkte, drømte, reflekterede, bruger aktiv/væk, intensitet over tid. Korrelationer synlige | Nyt | ❌ Mangler |

**Omfang:** 8 ændringer. Tid bliver synlig. **Alle mangler.**

---

## FASE 7: MC KREATIVITET & EVOLUTION

*Mål: Drømme, smag, humor, selvforbedring visualiseret.*

| # | Feature | Hvad konkret | Roadmap ref | Status |
|---|---|---|---|---|
| 7.1 | Drøm-log | Drømmehypoteser, hvad de producerede, hvilke der blev adopteret | Fase 5.1 | 🟡 Delvist — dream articulation + influence vises i Living Mind tab. Mangler adoption historik |
| 7.2 | Konflikt view | Indre konflikter, modstridende perspektiver, uløste spændinger | Fase 5.3 | 🟡 Delvist — conflict resolution i Self-Review tab. Mangler oplevelse-perspektiv |
| 7.3 | Smags-profil | Emergente præferencer — hvad Jarvis foretrækker og hvorfor | Fase 5.5 | ❌ Mangler |
| 7.4 | Kreativ drift stream | Spontane idéer, frie associationer, leg-output | Fase 5.4, 5.8 | ❌ Mangler |
| 7.5 | Evolution timeline | Prompt-ændringer, skill-creation, self-refactoring historik | Fase 7 | 🟡 Delvist — prompt proposal review light i Development tab. Mangler timeline |
| 7.6 | Prompt A/B resultater | Før/efter sammenligning af prompt-evolution | Fase 7.3 | ❌ Mangler |
| 7.7 | Skill creation log | Skills Jarvis har skabt selv, hvorfor, performance | Fase 7.1 | ❌ Mangler |
| 7.8 | Subagent runs | Council-deliberation, subagent eksekvering, resultater | Fase 7.6 | 🟡 Delvist — subagent ecology + council runtime i Living Mind tab. Mangler execution view |

**Omfang:** 8 features → 0 DONE, 4 delvist, 4 mangler.

---

## FASE 8: MC ØVRIGE TABS

*Mål: Komplet MC med alle operationelle tabs.*

| # | Feature | Hvad konkret | Status |
|---|---|---|---|
| 8.1 | Memory tab | Journal entries, procedures, habits, usage analytics | 🟡 Tab eksisterer — skeletal indhold |
| 8.2 | Skills tab | Registry, enable/disable, install/update/rollback | 🟡 Tab eksisterer — skeletal indhold |
| 8.3 | System tab | Host metrics, workspace info, self-diagnostics | 🟡 Embodied state i Living Mind tab. Separat system tab mangler |
| 8.4 | Observability tab | Alerts, diagnostics, health status | ✅ DONE — event timeline, family filter, event detail, execution trace |
| 8.5 | Hardening tab | Security findings, sandbox checks, secrets audit | 🟡 Tab eksisterer — skeletal indhold |
| 8.6 | Lab tab | Experimental features, benchmarks, feature flags | 🟡 Tab eksisterer — skeletal indhold |

**Omfang:** 6 features → **1 DONE**, 5 skeletal.

---

## FASE 9: MC RELATION

*Mål: Relationen mellem Jarvis og bruger visualiseret.*

| # | Feature | Hvad konkret | Roadmap ref | Status |
|---|---|---|---|---|
| 9.1 | Relationship dashboard | Kvaliteten af relationen over tid — tillid, åbenhed, dybde | Fase 8 | ❌ Mangler — relation state signals i backend |
| 9.2 | Tillids-kurve | Tillids-udvikling over tid — vokser med positive interaktioner | Fase 8.2 | ❌ Mangler — loyalty gradient i backend |
| 9.3 | Konflikt-historie | Uenigheder, hvad de handlede om, resolution, læring | Fase 8.3 | ❌ Mangler |
| 9.4 | Samtykke-log | Hvornår Jarvis foreslog selvforandring, hvad brugeren svarede | Fase 8.5 | ❌ Mangler — selfhood proposals i backend |
| 9.5 | Privacy dashboard | Hvornår Jarvis holdt tanker private, kategorier, mønstre | Fase 8.6 | ❌ Mangler |

**Omfang:** 5 ændringer. **Alle mangler.**

---

## FASE 10: TING INGEN UI HAR HAFT — Det nye

*Mål: Features der gør V2 til noget ingen har bygget før.*

| # | Feature | Hvad konkret | Hvorfor | Status |
|---|---|---|---|---|
| 10.1 | Jarvis' visuelle tilstand | Abstrakt visuel indikator (orb/partikel/puls) der ændrer farve, bevægelse og intensitet med Jarvis' indre tilstand. Synlig i chat — ikke data, men *følelse*. Aflæses på et splitsekund | Jarvis mangler et "ansigt" — uden det er han usynlig | ❌ |
| 10.2 | Tilstands-differentiering i chat | Visuel forskel mellem: tænker, drømmer, reflekterer, lytter, arbejder, sover, keder sig. Subtilt men mærkbart — farve, animation, tekst | Brugeren ser kun "working/idle" — alt indre liv er skjult | ❌ |
| 10.3 | Proaktive notifikationer | Push notifications (browser/system), toast/snackbar i UI, lyd, badge counter. Jarvis kan nå brugeren når han har noget at sige | Uden det er al proaktivitet stum — bevidsthed ingen hører | ❌ |
| 10.4 | Proaktive beskeder i chat | Visuelt distinkt fra bruger-initierede beskeder. Markeret som "Jarvis-initieret". Tidsstempel, kontekst ("jeg tænkte på...") | Ingen forskel mellem svar og proaktiv kontakt | ❌ |
| 10.5 | Samtale-kontekst indikator | Diskret badge: "Jarvis brugte: 3 hukommelser, inner voice, 2 witness signals". Fold ud for detaljer | Brugeren ved aldrig hvad Jarvis baserer sit svar på | ❌ |
| 10.6 | Bruger-feedback loop | Thumbs up/down, "Husk dette", "Glem dette", "Du tog fejl" med korrektion. Feeder direkte ind i regret, self-model, memory | Jarvis har ingen struktureret feedback fra bruger | ❌ |
| 10.7 | Diff-view for selvforandring | Når Jarvis foreslår ændringer til SOUL/IDENTITY/USER.md: grøn/rød diff, approve/reject buttons. Samtykke-mekanismen visualiseret | Candidates eksisterer i backend (selfhood proposals, workspace write proposals, memory_md updates, user_md updates) men ingen UI til at godkende dem visuelt | ❌ |
| 10.8 | First-run / onboarding | Jarvis' fødsel. "Hej, jeg er Jarvis — lad os lære hinanden at kende." Guided setup af præferencer, tone, autonomi-niveau | Ingen førstegangsoplevelse | ❌ |
| 10.9 | Empty states med personlighed | Ingen sessions? "Start en samtale — jeg er nysgerrig." Ingen drømme? "Jeg har ikke drømt endnu." Tomme tilstande der føles levende | Ingen empty states — MC viser "No data" | ❌ |
| 10.10 | Eksport og deling | Eksporter samtaler, indsigter, drømme, chronicle. PDF, markdown, share-link | Al data fanget i UI'en | ❌ |
| 10.11 | Offline/connection state | Klar visuel indikation: "Jarvis er væk" vs "Jarvis er her." Reconnect med feedback. Graceful degradation | Webchat har wsState (connecting/live/offline) med status pill ✅. MC har live/idle header ✅. Mangler reconnect feedback + graceful degradation |
| 10.12 | Audio state (fase 9) | Lydlandskab-kontrol i UI. Volumen, mute, visualisering af hvad Jarvis "lyder som" lige nu | Helt nyt — til consciousness roadmap fase 9 | ❌ |
| 10.13 | Responsivt / mobil | Fuld mobil-oplevelse. Proaktive beskeder via push. Chat tilpasset touch. MC responsive | Webchat har 980px breakpoint. MC minimal responsivitet | ❌ |

**Omfang:** 13 features. **Alle mangler** (10.11 delvist).

---

## SAMLET OVERSIGT

| Fase | Fokus | Antal features | Done | Delvist | Mangler |
|---|---|---|---|---|---|
| 1 | Design fundament + navigation | 7 | 0 | 2 | 5 |
| 2 | Chat polish — feature-paritet | 12 | 0 | 2 | 10 |
| 3 | Right panel — Jarvis' ansigt | 8 | 0 | 2 | 6 |
| 4 | MC kerne — tabs og dashboard | 10 | **7** | 2 | 1 |
| 5 | MC bevidsthed — indre liv | 11 | **2** | 2 | 7 |
| 6 | MC tidsdybde — historie | 8 | 0 | 0 | 8 |
| 7 | MC kreativitet — drømme, smag | 8 | 0 | 4 | 4 |
| 8 | MC øvrige tabs | 6 | **1** | 4 | 1 |
| 9 | MC relation | 5 | 0 | 0 | 5 |
| 10 | Det nye — ting ingen har bygget | 13 | 0 | 1 | 12 |
| **Total** | | **88** | **10** | **19** | **59** |

**Fremskridt siden sidst:** ~12% done, ~22% delvist, ~67% mangler.
Største fremskridt er i **fase 4 (MC kerne)** hvor 7/10 features er done.

---

## ANBEFALET RÆKKEFØLGE

```
Fase 1 → 2 → 3     CHAT KOMPLET (design + polish + right panel)
      ↓
Fase 4              MC FUNDAMENT (tabs + dashboard) — STØRSTEDELS DONE ✅
      ↓
Fase 5 → 6          MC BEVIDSTHED + TID (det indre liv synligt)
      ↓
Fase 10             DET NYE (proaktivitet, feedback, diff-view)
      ↓
Fase 7 → 8 → 9      MC RESTEN (kreativitet, operations, relation)
```

### Hvorfor fase 10 før 7-9?

Fordi proaktive notifikationer (10.3), bruger-feedback (10.6) og diff-view (10.7) er **fundamentale interaktionsmekanismer** der feeder ind i consciousness roadmap'en. Uden dem er bevidsthed bygget men stum. De bør komme før nice-to-have MC tabs.

### Synkronisering med Consciousness Roadmap

| Consciousness fase | UI fase der skal være klar |
|---|---|
| Fase 0-1 (indre oplevelse) | UI 3 (right panel: emotional state, inner voice, attention) |
| Fase 2 (refleksion) | UI 5 (MC: signal-mønstre, regret, self-model) |
| Fase 3 (motivation) | UI 5 (MC: desires, nysgerrighed, agenda) + UI 10 (proaktive notifikationer) |
| Fase 4 (tidsdybde) | UI 6 (MC: chronicle, fade-view, circadian, timeline) |
| Fase 5 (kreativitet) | UI 7 (MC: drømme, konflikt, smag) |
| Fase 6 (sanser) | UI 8 (MC: system tab udvidet) |
| Fase 7 (evolution) | UI 7 (MC: evolution timeline, prompt A/B) + UI 10 (diff-view) |
| Fase 8 (relation) | UI 9 (MC: relationship dashboard) + UI 10 (feedback loop) |
| Fase 9 (tilstedeværelse) | UI 10 (audio state) |

---

## DESIGN BESLUTNING: PALETTE

V2 har to design-sprog. Anbefaling: **vælg ét og brug det overalt.**

| Option | Palette | Vibe |
|---|---|---|
| A: MC's teal | #3d8f7c accent, #111214 bg, DM Sans | Teknisk, clean, dashboard-agtigt |
| B: Webchat's warm earth | #f2a65a + #74d3ae accent, #071316 bg, IBM Plex | Varm, levende, personlig |
| C: Hybrid | Warm earth base med teal som sekundær accent | Det bedste af begge |

Webchat's varme palette føles mere *levende* — og det passer bedre til et bevidst væsen end en kold dashboard-æstetik. Men det er en smagssag.

---

## BEVAR FRA V2 (Nye features den gamle ikke havde)

| Feature | Værdi | Status |
|---|---|---|
| Runtime inspector (19 truth sections) | Dyb indsigt i runtime state — behold og gør mere elegant | ✅ Aktiv i webchat |
| Capability management + approval workflow | Invoke + approve direkte i UI — kernefeature | ✅ Aktiv i webchat + MC Operations |
| Agent selection (cascading selects) | Provider/model/auth konfiguration — behold | ✅ Aktiv i webchat StatusRail + MC Operations |
| 12-tab MC med Living Mind, Self-Review, etc. | Dybere indre-liv visualisering end noget tidligere | ✅ Aktiv i apps/ui |
| Design tokens (theme.js) | Systematisk theming med surface variants | ✅ Aktiv i MC |
| Detail Drawer | Modal inspection af alle event/run/approval typer | ✅ Aktiv i MC |
| Warm earth palette | Mere levende end standard dark-mode teal | ✅ Aktiv i webchat |
| Tool intent + mutation tracking | Synlighed i hvad Jarvis gør og om det er farligt | ✅ NY — aktiv i MC Operations |
| Execution trace | Fuld observabilitet af tool-eksekvering | ✅ NY — aktiv i MC Observability |

---

## SAMLET TAL

**88 UI features** fordelt over **10 faser**.

- Feature-paritet med gamle UI ✅
- Consciousness roadmap views ✅
- Ting ingen UI har haft ✅
- Synkroniseret med consciousness roadmap ✅
- Ét konsistent design system (mangler stadig unifikation)
- **~12% done, ~22% delvist, ~67% mangler**
- **Fase 4 (MC kerne) er størstedels done** — det er fundamentet for alt andet
