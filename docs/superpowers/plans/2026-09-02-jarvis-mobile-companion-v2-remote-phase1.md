# Jarvis Mobile Companion V2 — Fase 1 Implementeringsplan (Remote: Arbejde-tab)

---
status: omskrevet efter endeligt review (Claude → Codex → Jarvis) — klar til implementering
date: 2026-09-02
spec: docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md
review: docs/superpowers/reviews/2026-09-02-v2-remote-phase1-jarvis-final-review.md
branch: codex/jarvis-mobile-companion-v1 (apps/mobile) + main (server-arbejde)
---

> **For agentic workers:** brug superpowers:subagent-driven-development eller
> executing-plans. Steps bruger checkbox-syntax (`- [ ]`). Commit efter hver task.

**Goal:** Giv Bjørn "godkend fra lommen": et Arbejde-rum (ChatGPT-Remote-mønster)
i mobil-appen der viser det arbejde Jarvis laver, og en godkendelseskø der
overlever app-lukning og bliver til en push-notifikation.

**Leverance-kriterie (live E2E):** Bjørn kan lukke appen → få en notifikation om
en ventende godkendelse → åbne appen → **godkende og få den gemte handling
udført** fra Arbejde-tabben. Verificeres live, ikke kun med grønne tests.

> **Bemærk run-semantik (beslutning 4):** fase 1 lover "godkend og udfør den gemte
> handling" — IKKE "run'et fortsætter". Et run, der har bedt om godkendelse, er
> allerede fortsat/afsluttet. Ægte fortsættelse kræver suspended-run-arkitektur og
> er en anden fase.

## Det endelige review — 12 beslutninger der omskriver planen

Efter review-kæden Claude → Codex → Jarvis er alle fund verificeret uafhængigt mod
koden. Planen er omskrevet omkring disse 12 beslutninger. Hver beslutning peger på
de tasks, der bærer den:

1. **Task 0: merge main ind i companion-branchen før alt andet.** Branchen er
   1699 commits bag main (merge-base 2026-06-17). Rebase blokeres af
   attributions-hooks → brug merge, ikke rebase. (→ Task 0)
2. **Ét idempotent server-verb, ikke to POST-kald.** Mobilen skal ikke orkestrere
   `/approve` + `/execute`. Ét `approve-and-execute` der atomisk claimer requesten
   (approved → executing), afviser konkurrerende execution og returnerer det
   tidligere resultat ved retry. (→ Task 3)
3. **Bruger-isolation på alle list/get/approve/execute.** CRUD-laget filtrerer i
   dag kun på request_id; `scheduled_for_user_id` bruges ikke. Gamle NULL-rækker
   karantænes owner-only. To-bruger-regressionstest. (→ Task 2)
4. **Ærlig run-semantik** — "godkend og udfør gemt handling", ikke "run'et
   fortsætter". (→ Leverance-kriterie, Task 11)
5. **Modelér begge godkendelsessystemer eksplicit.** `capability_approval_requests`
   (intet udløb) og `tool_intent_approval_requests` (`_APPROVAL_TTL = 15 min`).
   Spøgelses-rækker (juli, stadig pending) håndteres. (→ Task 6)
6. **Løft 5-cappet på BÅDE /mc/runs og /mc/approvals** — samme fil, fælles
   rettelse. (→ Task 4)
7. **A/B/C som server-sandhed, ikke hensigt.** `visible_runs` har ingen
   `source`-kolonne og intet der adskiller agent-arbejde; C-runs bor i
   `agent_runs` (db_agent_runtime.py) og eksponeres pr. agent. Fase 1 viser derfor
   **A+B** (visible + autonomous runs). C er fase 2 (kræver ny work-projektion der
   inkluderer agent_runs). (→ Task 10)
8. **Durable outbox-push** — atomisk med requesten, separat dispatcher med retry,
   deduplikering på request-ID/envelope. (→ Task 5)
9. **Én notification-navigation-ejer** på app-niveau; flyt eksisterende listener
   fra ChatScreen. Test foreground/background/cold-start. (→ Task 12)
10. **Poll /mc/approvals i samme cyklus** som runs/overview — ellers bliver kø og
    badge stale. (→ Task 10/11)
11. **Boy Scout-udskillelse** af approval-persistens til fokuseret modul med
    kompatibel re-export, før nogen logikændring rører det. (→ Task 1)
12. **Stale-policy for gamle capability-requests.** De må ikke kunne eksekveres
    direkte fra mobilen; approval-envelope binder user + capability_id +
    execution_mode + target + content + fingerprint. (→ Task 6)


## Arkitektur (kort)

State bor på serveren (design-princip 1 i spec'en). Appen tilføjer ét nyt rum
ovenpå mission-control API'et. Serveren får en række ændringer — ikke kun to —
fordi reviewet viste, at de eksisterende endpoints ikke er bruger-isolerede, ikke
er idempotente, og at køen ville vise spøgelses-rækker og højst fem runs.

```
┌─────────────────────────────────────────────┐
│ (≡)   [ Snak | Arbejde ]   (⟳)              │  TopBar (ny, fælles)
├─────────────────────────────────────────────┤
│ Arbejde: Tasks | Approve (segmented, sub)   │
│   Tasks:   /mc/runs + /mc/overview → kort   │
│   Approve: /mc/approvals → ApprovalCard V2  │
├─────────────────────────────────────────────┤
│ polling 3–5s (aktivt tab) · push (inaktivt) │
└─────────────────────────────────────────────┘
```

Ét godkendelses-verb på mobilen: `approve-and-execute` (idempotent, server-side
claim). Ingen orkestrering af to risikable POST-kald som én brugerhandling.

## Teknologi

Eksisterende (ubevæget): Expo 56 / RN 0.85+, TypeScript strict, Jest + RNTL,
expo-secure-store, react-native-sse, FCM via push.ts. Ingen ny navigation-lib —
tilstanden `mode: 'snak' | 'arbejde'` bor i App.tsx (AppBody).

## Globale constraints

- API-base: `https://api.srvlab.dk/` (config.authToken, som i dag)
- Arbejde-tab er read-only for runs + ét approve-and-execute-verb. Ingen
  run-cancel i fase 1 (spec-beslutning 3 siger B/C kan afbrydes — men cancel-knap
  er fase 2; kun godkendelse er fase 1's verb).
- Ingen websocket i fase 1. Polling når tab aktivt; push når inaktivt.
- UI: ChatGPT-appens visuelle sprog (spec UI-paritet). Dark mode først.
- Mobile må aldrig auto-godkende. "Godkend" kræver eksplicit tryk.
- Commit-trailers kræves af repo-hooks (Actor/Actor-Type/Run-ID/Session-ID/Origin/
  Approved-By i ét kontinuert blok, ingen tom linje før Co-Authored-By).

## Server-kontrakter (verificeret i kode + review, 2026-09-02)

### Eksisterende endpoints appen skal bruge

`GET /mc/overview` → `{ ok, visible_run: {...}, visible_execution: {...}, runtime: {...} }`
`GET /mc/runs?limit=N` → `{ active_run, last_outcome, recent_runs: [...], summary: { active, recent_count, failed_count } }`
`GET /mc/approvals?limit=N` → `{ requests: [...], recent_invocations, recent_events, summary: { pending_count, approved_count, request_count } }`
`POST /mc/capability-approval-requests/{request_id}/approve` → `{ ok, request }` (404 hvis ukendt)
`POST /mc/capability-approval-requests/{request_id}/execute` → `{ ok, ... }` (eksisterer, men IKKE idempotent)

> Efter beslutning 2+3+4 erstattes approve+execute på mobil-siden af ét nyt verb
> `approve-and-execute` (Task 3). De to gamle endpoints bliver enten bruger-isolerede
> og afløst, eller eksplicit markeret som interne.

### To godkendelsessystemer — begge skal modelleres (beslutning 5)

1. **Capability-approvals** — `capability_approval_requests` (db_capability_approval.py).
   Intet udløb. Livscyklus pending → approved → executed. Ingen `denied`-status
   (kun feedback-log). 22 pending i live-data, ældste fra april.
2. **Tool-intent-approvals** — `tool_intent_approval_requests`, `_APPROVAL_TTL = 15 min`.
   Udløber; server svarer 409 expired. Det kort Bjørn sad med i dag var et
   tool-intent-kort.

Køen i Arbejde-tab skal vise begge, korrekt markeret (capability: ingen TTL men
stale-policy; tool-intent: TTL + expired-tilstand). Spøgelses-rækker (pending fra
juli) må ikke fremstå som aktive.

### Verificerede huller — lukkes i denne plan

1. **Ingen bruger-isolation** (Codex F1). CRUD filtrerer kun på request_id.
2. **approve→execute genoptager ikke run'et** (Codex F2). Intet checkpoint/resume.
3. **execute er ikke idempotent** (Codex F3). `executed` skrives efter kaldet, uden
   compare-and-set. Dobbelttryk/timeout-retry kan køre samme write/sudo flere gange.
4. **5-cap på /mc/runs OG /mc/approvals** (Claude F2). `recent_visible_runs(limit=5)`
   og `recent_capability_approval_requests(limit=5)` — samme form, to steder.
5. **C-runs findes ikke i /mc/runs** (Claude F3) og **source-feltet findes ikke**
   (Claude F5). A/B/C er en hensigt, ikke server-sandhed.
6. **Push-hook er synkront/tabbart/ikke deduplikeret** (Codex F5).
7. **Push-navigation har to potentielle ejere** (Codex F6) — ChatScreen ejer listen
   i dag.
8. **/mc/approvals polles ikke** (Codex F7).
9. **Boy Scout-reglen brydes** (Codex F8) — workspace_capabilities.py er 2291 linjer.
10. **Ingen stale-policy** (Codex F4) — gamle capability-requests kan eksekveres
    direkte fra mobilen.


## Beslutninger (revideret efter review)

- **B1 — "Godkend altid" er UD af fase 1.** Reviewet viste, at server-mekanismen
  (`sudo_approval_window_allows_request`) låner sudo-vinduet fra det forkerte
  system og kun dækker sudo, ikke generelle write-capabilities. At vise "Godkend
  altid" ville lyve om hvad serveren gør. Kortet har i fase 1 ét verb: **Godkend og
  udfør**. Præfiks-regel-UI (R8) er fase 3-arbejde.
- **B2 — "Spring over" = lokal dismissal i fase 1.** Ingen server-status for afvis
  på capability-requests (kun feedback-log). Kortet fjernes fra kø-visningen
  (dismissed-liste i app-state, session-lokal) og forbliver pending server-side.
  Server-side denied-status er fase 3 (kolonne-udvidelse + endpoint + filter).
- **B3 — 5-cap-fix gælder BÅDE /mc/runs og /mc/approvals** (én fælles rettelse,
  samme fil — beslutning 6).
- **B4 — Arbejde-tab er read-only + godkend i fase 1.** Tasks-visning (A+B) og
  approve-kø. Dyk til run-detalje (R6-tråd), cancel, Review (diffs), New task,
  steer og C-runs er fase 2/3. UI'en må IKKE antyde cancel/steer-knapper der ikke
  virker — kun ét aktivt verb: godkend-og-udfør.
- **B5 — Fase 1 viser A+B runs, ikke C.** C-runs (agent-arbejde) bor i
  `agent_runs` og eksponeres pr. agent — en ny work-projektion er fase 2. Tasks-
  listen viser visible (A) + autonomous (B) runs fra /mc/runs + /mc/overview.
- **B6 — Køen viser begge godkendelsessystemer**, korrekt markeret: tool-intent med
  TTL + expired-tilstand; capability med stale-policy (beslutning 12). Ingen
  spøgelses-rækker fremstår som aktive.

## UI-base — nye tokens (1:1 med ChatGPT dark, målt R1–R8)

Erstatter V1's Jarvis-desk-grønne tokens (`bg0 #0d1117`, `accent #6ee7a8`) med
ChatGPT-appens visuelle sprog. **Hele appen skifter visuelt** — dette er en
bevidst, stor ændring (Bjørns 1:1-krav), ikke en kosmetisk touch-up:

- `bg0: #000000` (solid sort baggrund) · `surface1: #2F2F2F` (sekundære
  elementer: cirkel-knapper, segmented-beholder, input-pille) · `surface2:
  #212121` (kort/modal) · `fg1: #FFFFFF` · `fg2: #B0B0B0` (sekundærtekst,
  tidsstempler) · `fg3: #6B7480` (tertiær)
- Accent: lilla→blå gradient (voice-knap, FAB, bruger-boble) —
  `#A78BFA → #60A5FA`; AI-hilsen-boble: mørk lilla `~#7C5CBF`
- Online-prik: `#4CAF50` · advarsel: `#FFB347` (amber) · fejl beholdes `#ff8080`
- Radius: bobler/piller fuldt afrundede (999), kort 12–16, modal 24–28
- V1-tokens beholdes IKKE parallelt — tokens.ts migreres, komponenter der
  refererer `accent`/`bg0`-navne opdateres mod de nye navne. (Renamed keys giver
  type-fejl der tvinger gennemgang — ønsket.)

Reference-screenshots: spec-sektionen "Målt fra Bjørns reference-screenshots"
(R1–R8). Hver skærm verificeres side-for-side mod screenshot før implementering.

## Fil-struktur (nye/ændrede filer)

Server (main-branch, core + api):
- `core/runtime/db_capability_approval.py` — bruger-isolation + stale-policy
- `core/tools/workspace_capabilities.py` — udskil persistens (Task 1) → hook → outbox
- `core/tools/workspace_capabilities_approval.py` (ny) — udskilt persistens (Boy Scout)
- `core/services/push_dispatcher.py` — outbox-dispatcher + dedup
- `core/services/approval_outbox.py` (ny) — durable outbox (atomisk med request)
- `apps/api/jarvis_api/routes/mission_control_runtime_config.py` — approve-and-execute verb
- `apps/api/jarvis_api/routes/mission_control_runs_ops.py` — 5-cap fix (runs + approvals)

App (branch codex/jarvis-mobile-companion-v1, apps/mobile/src):
- `theme/tokens.ts` — ny ChatGPT-paritet-palette
- `components/TopBar.tsx` (ny) — (≡) | [Snak|Arbejde] | (⟳)
- `components/SegmentedControl.tsx` (ny, genbruges to steder)
- `components/WorkTaskCard.tsx` (ny) — status/maskine/alder-kort
- `components/ApprovalCard.tsx` — opgraderet (R8-mønster + kø-kontekst, ét verb)
- `screens/WorkScreen.tsx` (ny) — Tasks|Approve sub-tabs
- `lib/mcTypes.ts` (ny) — mission-control types
- `lib/mcClient.ts` (ny) — apiFetch-baserede kald (approve-and-execute)
- `hooks/useWorkPolling.ts` (ny) — 3–5s polling (runs + approvals), aktivt-tab-only
- `lib/push.ts` — håndter `approval_requested`-kind + nav (én ejer)
- `App.tsx` — mode-state + TopBar + WorkScreen-routing + nav-ejer
- `ChatScreen.tsx` — flyt notification-listener til App-niveau


## Tasks

### Task 0 (branch): merge main ind i companion-branchen

**Baggrund:** companion-branch er 1699 commits bag main (merge-base 2026-06-17).
At bygge på den nuværende base ville ske på en halvanden måned gammel kode.
Rebase blokeres af attributions-hooks → brug **merge**, ikke rebase.

- [ ] 1. `git checkout codex/jarvis-mobile-companion-v1` og `git merge main`
- [ ] 2. Løs konflikter; kør repo-hooks (attributions-trailere) korrekt på merge-commits
- [ ] 3. Verificér appen bygger (`npm ci` + `npm test` + typecheck i apps/mobile)
- [ ] 4. Push branchen — dette er baseline for alle efterfølgende app-tasks

### Task 1 (server): Boy Scout-udskillelse af approval-persistens

**Filer:** `core/tools/workspace_capabilities.py` (2291 linjer) →
`core/tools/workspace_capabilities_approval.py` (ny)
**Krav:** flyt `_persist_capability_approval_request` + dens hjælpere
(fingerprint, kontekst-stampling) til det nye modul med kompatibel re-export,
så eksisterende imports (`workspace_capabilities.X`) fortsat virker. Ingen
logikændring — ren flytning (som repo-reglen kræver før Task 2–6 rører logikken).

- [ ] 1. Udskil persist-funktion + hjælpere; re-export tilbage i workspace_capabilities
- [ ] 2. Kør core-tests — ingen adfærdsændring (grønne = ren flytning)
- [ ] 3. Commit (main): `refactor(core): udskil capability-approval-persistens (Boy Scout)`

### Task 2 (server): bruger-isolation på approval-CRUD

**Filer:** `core/runtime/db_capability_approval.py`, `apps/api/jarvis_api/routes/mission_control_runtime_config.py`
**Krav (beslutning 3):** alle list/get/approve/execute kræver den aktuelle bruger.
`recent_capability_approval_requests` og `get_capability_approval_request` skal
filtrere på `scheduled_for_user_id` (og feltet skal med i SELECT). Gamle
NULL-rækker karantænes owner-only (kun ejer/None kan se dem, eller de udelades
fra multi-bruger-visning).

- [ ] 1. Tilføj `scheduled_for_user_id` til SELECT + `WHERE`-filter i list/get
- [ ] 2. Route-niveau: hent aktuel bruger fra auth-kontekst; afvis cross-user-ID med 404
- [ ] 3. NULL-række-politik: karantæne owner-only (dokumentér valget i commit-besked)
- [ ] 4. Test: to-bruger-regressionstest — bruger B kan hverken se eller påvirke A's request
- [ ] 5. Commit (main): `fix(api): bruger-isolation på capability-approval endpoints`

### Task 3 (server): idempotent approve-and-execute verb

**Filer:** `apps/api/jarvis_api/routes/mission_control_runtime_config.py`
**Krav (beslutning 2+4):** ét verb `POST /mc/capability-approval-requests/{id}/approve-and-execute`
der atomisk claimer requesten approved → executing (compare-and-set), afviser
konkurrerende execution (anden klient ser "already executing"), og returnerer det
tidligere resultat ved retry. Mobilen kalder kun dette — ikke approve + execute.

- [ ] 1. Implementér claim-logik (atomic status-overgang, afvis konkurrence)
- [ ] 2. Udfør capability én gang; gem resultat; retry returnerer gemt resultat
- [ ] 3. Test: dobbelt-kald eksekverer kun én gang; retry returnerer tidligere resultat
- [ ] 4. Commit (main): `feat(api): idempotent approve-and-execute for capability-approvals`

### Task 4 (server): løft 5-cap på /mc/runs OG /mc/approvals

**Filer:** `apps/api/jarvis_api/routes/mission_control_runs_ops.py`
**Krav (beslutning 6):** begge routes henter direkte fra db-modulets
`recent_visible_runs(limit=limit)` / `recent_capability_approval_requests(limit=limit)`
i stedet for surface'ens hardcodede 5. Én fælles rettelse i samme fil.

- [ ] 1. Omskriv `mc_runs` + `mc_approvals` til direkte db-kald med respekt for limit
- [ ] 2. Test: seed 8 runs + 8 requests → limit=20 returnerer alle; limit=3 → 3
- [ ] 3. Commit (main): `fix(api): /mc/runs og /mc/approvals respect limit (var hardcoded 5)`

### Task 5 (server): durable outbox-push + deduplikering

**Filer:** `core/services/approval_outbox.py` (ny), `core/services/push_dispatcher.py`
**Krav (beslutning 8):** skriv et outbox-event atomisk med requesten (samme
transaktion som persist). Separat dispatcher leverer med retry; deduplikerer på
request-ID (eller fuld approval-envelope). Push må aldrig blokere persist eller
tabes ved procesnedbrud.

- [ ] 1. Outbox-tabel/skrivning atomisk med request-persist
- [ ] 2. Dispatcher: retry + dedup; kald `on_approval_requested` (kind `approval_requested`)
- [ ] 3. Test: nedbrud mellem persist og push → outbox leverer senere; tre ens requests → én notifikation
- [ ] 4. Commit (main): `feat(push): durable approval-outbox med retry + dedup`

### Task 6 (server): stale-policy + begge godkendelsessystemer i køen

**Filer:** `core/runtime/db_capability_approval.py`, `apps/api/jarvis_api/routes/mission_control_runs_ops.py`
**Krav (beslutning 5+12):** gamle capability-requests må ikke kunne eksekveres
direkte fra mobilen. Envelope binder user + capability_id + execution_mode +
target + content + fingerprint. Tool-intent-kort vises med TTL + expired-tilstand;
capability-rækker får en stale-markering (alder-tærskel). Spøgelses-rækker
(pending fra juli) fremstår ikke som aktive.

- [ ] 1. Envelope-binding (user/capability/mode/target/content/fingerprint) ved approve
- [ ] 2. Stale-markering på capability-requests (alder-tærskel, konfigurerbar)
- [ ] 3. Køen viser begge systemer, korrekt markeret (TTL vs stale)
- [ ] 4. Test: stale-request afvises ved approve-and-execute; tool-intent expired vises som expired
- [ ] 5. Commit (main): `feat(api): stale-policy + begge godkendelsessystemer i approvals-kø`


### Task 7 (app): tokens-migration til ChatGPT-palette

**Filer:** `apps/mobile/src/theme/tokens.ts` + alle komponenter der refererer gamle nøgler
**Krav:** nye nøgler (bg0 #000, surface1 #2F2F2F, surface2 #212121, fg1/2/3,
accent-gradient-seed, danger #ff8080, ok #4CAF50, warn #FFB347). Renamed keys →
type-fejl tvinger hver komponent igennem.

- [ ] 1. Migrér tokens.ts (behold struktur: color/radius/spacing/motion; tilføj `gradient`-seed + `bubble`-farver)
- [ ] 2. Gennemgå hver komponent der fejler typecheck; opdater farver efter R1–R8-mål
- [ ] 3. `npm test` + `npm run typecheck` grønne
- [ ] 4. Commit (branch): `feat(mobile): ChatGPT-paritet dark palette (R1-R8 mål)`

### Task 8 (app): TopBar + mode-routing (Snak | Arbejde)

**Filer:** `components/TopBar.tsx` (ny), `components/SegmentedControl.tsx` (ny), `App.tsx`, `ChatScreen.tsx`, `screens/WorkScreen.tsx` (skal)
**Krav (R4/R5-mål):** (≡) menu-cirkel venstre · pille-segmented `Snak | Arbejde`
midten · (⟳) sync-cirkel højre. Mode-state i AppBody. ChatScreen's egen header må
ikke skabe dobbelt-header. WorkScreen = skal med sub-segmented `Tasks | Approve`.

- [ ] 1. SegmentedControl (generisk, a11y: accessibilityRole="tab")
- [ ] 2. TopBar (menu → eksisterende side-menu; sync → manuelt poll-signal)
- [ ] 3. Mode-routing i App.tsx; WorkScreen-skal med tom-state
- [ ] 4. ChatScreen header-konflikt løst (ingen dobbelt-header)
- [ ] 5. Tests: TopBar/SegmentedControl render + mode-skift; eksisterende tests grønne
- [ ] 6. Commit (branch): `feat(mobile): top segmented control Snak|Arbejde`

### Task 9 (app): mission-control klient (types + REST)

**Filer:** `lib/mcTypes.ts` (ny), `lib/mcClient.ts` (ny)
**Interfaces:** typer for Run, ApprovalRequest (begge systemer), Overview, Summary.
`mcClient`: `fetchOverview`, `fetchRuns(limit)`, `fetchApprovals(limit)`,
`approveAndExecute(requestId)` — alt via `apiFetch`. `approveAndExecute` mapper
404 → ApiError('unknown') ("findes ikke længere"), 409 → ApiError('stale/expired'),
konflikt → "allerede under udførelse".

- [ ] 1. mcTypes.ts (Run/ApprovalRequest/Overview/Summary — capability + tool-intent)
- [ ] 2. mcClient.ts (4 funktioner, fejl-klassifikation)
- [ ] 3. Tests: mock fetch — shape-unwrapping, auth-header, 404/409/konflikt→fejlbesked
- [ ] 4. Commit (branch): `feat(mobile): mission-control API client`

### Task 10 (app): Tasks-liste i Arbejde (A+B)

**Filer:** `hooks/useWorkPolling.ts` (ny), `components/WorkTaskCard.tsx` (ny), `screens/WorkScreen.tsx`
**Krav (B5, beslutning 7):** viser A+B (visible + autonomous runs) — IKKE C i fase
1. Aktive runs øverst (running/pending/waiting), "afsluttet i dag" under
(kollapsbart). Kort: titel/beskrivelse, status-farveprik, maskine-tag (A=Snak,
B=autonom), relativ alder. Polling poller `/mc/runs` + `/mc/overview` + `/mc/approvals`
i samme cyklus (beslutning 10), kun når Arbejde-tab aktivt + app i foreground.

- [ ] 1. useWorkPolling-hook (aktivt-tab + foreground-gating; poller runs+overview+approvals; cleanup ved unmount)
- [ ] 2. WorkTaskCard (R5-stil: statusprik, tag, alder; read-only, ingen tryk-verber)
- [ ] 3. WorkScreen Tasks-view: gruppering aktive/afsluttet-i-dag + tom-state + fejl-state
- [ ] 4. Tests: polling-hook (timer-mock, gating), kort-rendering, gruppering
- [ ] 5. Commit (branch): `feat(mobile): Arbejde Tasks-liste (runs A+B)`

### Task 11 (app): Approve-kø med opgraderet ApprovalCard

**Filer:** `components/ApprovalCard.tsx`, `screens/WorkScreen.tsx` (Approve-view)
**Krav (R8-mønster + B1/B2/B6):** kort viser anledningstekst (proposal_reason),
tag (capability_name + execution_mode ELLER tool-intent + TTL), detalje-blok
(kommando/indhold + target), alder. Ét aktivt verb: **Godkend og udfør**
(`approveAndExecute` → optimistisk fjern + bekræftelse). **Spring over** = lokal
dismissal (B2). Ingen "Godkend altid" (B1). Køen viser begge systemer, korrekt
markeret (B6): tool-intent med TTL/expired, capability med stale-markering.
Tom-state: "ingen ventende godkendelser".

- [ ] 1. ApprovalCard V2 (ét aktivt verb + Spring-over, R8-visuelt: tag + kodeblok + lodret stak)
- [ ] 2. Approve-view i WorkScreen: pending-kø (begge systemer) + tom-state + fejl-state
- [ ] 3. approve-and-execute → optimistisk UI + refresh; dismissed-liste (session-lokal)
- [ ] 4. Tests: ApprovalCard V2 (verb, betinget markering), kø-logik (dismiss/approve/stale)
- [ ] 5. Commit (branch): `feat(mobile): Approve-kø med R8-kort (godkend-og-udfør)`

### Task 12 (app): push `approval_requested` → notifikation + nav (én ejer)

**Filer:** `lib/push.ts`, `App.tsx` (badge-tilstand + nav-ejer), `screens/WorkScreen.tsx`
**Krav (beslutning 9):** flyt notification-navigation til ÉT app-level-ejer
(auth/session-providers). data-only kind `approval_requested` → notifikation
(notifee) → tap åbner Arbejde→Approve. Badge på Arbejde-segmentet ved
pending_count > 0 (fra polling).

- [ ] 1. Flyt listener fra ChatScreen til app-niveau (fjern dobbelt-ejer)
- [ ] 2. push.ts: håndter kind + tap-nav til Arbejde (deep-link-state i App)
- [ ] 3. Badge på Arbejde-tab ved pending > 0
- [ ] 4. Tests: push-handler (kind-parsing + tap-kald) + foreground/background/cold-start
- [ ] 5. Commit (branch): `feat(mobile): approval_requested push → Arbejde/Approve (én nav-ejer)`

### Task 13: Live E2E — leverance-kriteriet

- [ ] 1. Sørg for server-ændringer (Task 1–6) er deployed og virker live; byg + installer app (branch, Task 0-mergede base)
- [ ] 2. Trigger en ægte capability-approval-request (B-run der kræver approval — sudo-exec eller workspace-write uden for trust)
- [ ] 3. Verificér kæden: app lukket → push lander → åbn → kort i Approve → **Godkend og udfør** → handling udført én gang; request forsvinder fra pending-kø; stale/expired håndteres korrekt
- [ ] 4. Først når E2E er grøn live: marker plan færdig + opdater spec-status

## Accept-kriterier (fase 1)

1. Arbejde-tab viser A+B-runs samlet (aktive + afsluttet-i-dag, grupperet)
2. Approve-kø viser >5 requests (cap-fix virker) med korrekt alder/tag/anledning;
   begge godkendelsessystemer korrekt markeret (TTL vs stale)
3. "Godkend og udfør" flipper request til approved OG udfører handlingen én gang
   (idempotent — dobbelt-tryk udfører ikke to gange)
4. Bruger-isolation: bruger B kan hverken se eller påvirke A's requests
5. Push lander når app er lukket; tap åbner Arbejde→Approve (foreground/background/cold-start)
6. UI matcher R1–R8-reference (side-for-side-check pr. skærm)
7. Alle tests grønne + live E2E gennemført (grønne tests ≠ systemet virker)

## Åbne punkter fra reviewet — besvaret/lukket

1. **B1 (Godkend altid)** — LUKKET: ud af fase 1. Server-mekanismen låner
   sudo-vinduet fra det forkerte system; at vise knappen ville lyve. Fase 3.
2. **B2 (Spring over = lokal dismissal)** — LUKKET: ja, fase 1. denied-status er
   fase 3 (kolonne + endpoint + filter).
3. **Task 4 header-konflikt** — LUKKET: ChatScreen's header fjernes/viger; TopBar
   er den ene fælles header. Verificeres i Task 8.
4. **R8-kortets "Godkend" semantik** — LUKKET: verbet hedder nu "Godkend og udfør"
   og beskrives i UI ("udføres nu"), fordi vi ikke lover "run'et fortsætter" (B4).
5. **Token-migrationens rækkevidde** — LUKKET: hele appen skifter i Task 7 (Bjørns
   1:1-krav); én commit.
6. **Cancel-timing vs spec-beslutning 3** — LUKKET: fase 1 er read-only + godkend.
   Cancel er fase 2. Spec-beslutning 3's "B/C kan afbrydes" gælder fase 2+.

