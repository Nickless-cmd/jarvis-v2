# Jarvis Mobile Companion V2 — Fase 1 Implementeringsplan (Remote: Arbejde-tab)

---
status: udkast (klar til eksternt review — Claude + Codex)
date: 2026-09-02
spec: docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md
branch: codex/jarvis-mobile-companion-v1 (apps/mobile) + main (server-arbejde)
---

> **For agentic workers:** brug superpowers:subagent-driven-development eller
> executing-plans. Steps bruger checkbox-syntax (`- [ ]`). Commit efter hver task.

**Goal:** Giv Bjørn "godkend fra lommen": et Arbejde-rum (ChatGPT-Remote-mønster)
i mobil-appen der viser alt det arbejde Jarvis laver (A/B/C-runs) og en
godkendelseskø der overlever app-lukning og bliver til en push-notifikation.

**Leverance-kriterie (live E2E):** Bjørn kan lukke appen → få en notifikation om
en ventende godkendelse → åbne appen → godkende fra Arbejde-tabben → og run'et
fortsætter. Verificeres live, ikke kun med grønne tests.

## Arkitektur (kort)

State bor på serveren (design-princip 1 i spec'en). Appen tilføjer ét nyt rum
ovenpå mission-control API'et der allerede findes. Serveren får to små tilføjelser:
en ny push-kind (`approval_requested`) + en kø-fix (`/mc/approvals` cap på 5).

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

## Teknologi

Eksisterende (ubevæget): Expo 56 / RN 0.85+, TypeScript strict, Jest + RNTL,
expo-secure-store, react-native-sse, FCM via push.ts. Ingen ny navigation-lib —
tilstanden `mode: 'snak' | 'arbejde'` bor i App.tsx (AppBody).

## Globale constraints

- API-base: `https://api.srvlab.dk/` (config.authToken, som i dag)
- Arbejde-tab er read-only for runs + approve-verber. Ingen run-cancel i fase 1
  (spec-beslutning 3 siger B/C kan afbrydes — men cancel-knap er fase 2; kun
  godkendelse er fase 1's verb — se Beslutninger).
- Ingen websocket i fase 1. Polling når tab aktivt; push når inaktivt.
- UI: ChatGPT-appens visuelle sprog (spec UI-paritet). Dark mode først.
- Mobile må aldrig auto-godkende. "Godkend" kræver eksplicit tryk.
- Commit-trailers kræves af repo-hooks (Actor/Actor-Type/Run-ID/Session-ID/Origin/
  Approved-By i ét kontinuert blok, ingen tom linje før Co-Authored-By).

## Server-kontrakter (verificeret i kode, 2026-09-02)

### Eksisterende endpoints appen skal bruge

`GET /mc/overview` → `{ ok, visible_run: {...}, visible_execution: {...}, runtime: {...} }`
`GET /mc/runs?limit=N` → `{ active_run, last_outcome, recent_runs: [...], summary: { active, recent_count, failed_count } }`
`GET /mc/approvals?limit=N` → `{ requests: [...], recent_invocations, summary: { pending_count, approved_count, request_count } }`
`POST /mc/capability-approval-requests/{request_id}/approve` → `{ ok, request }` (404 hvis ukendt)

### Capability-approval-request-objekt (felter appen renderer)

Fra `_capability_approval_request_from_row` (db_capability_approval.py):
`request_id, capability_name, capability_kind, execution_mode, approval_policy,
run_id, proposal_target_path, proposal_content, proposal_content_summary,
proposal_content_fingerprint, proposal_reason, requested_at, status
(pending|approved), executed, executed_at`

Kortet viser: `capability_name`/`execution_mode` som tag, `proposal_reason` som
anledningstekst, `proposal_content_summary`/`proposal_target_path` som detalje,
`requested_at` som alder.

### To huller i serveren (verificeret) — lukkes i denne plan

1. **`/mc/approvals` kan max returnere 5.** `_capability_invocation_surface()`
   (mission_control_common.py:588) kalder `recent_capability_approval_requests(limit=5)`
   hardcoded; route'en skærer kun ned, aldrig op. Fase 1's kø skal vise mere end 5.
   Fix: route'en henter direkte `recent_capability_approval_requests(limit=limit)`
   (findes i db-modulet) i stedet for surface'ens 5-cap.
2. **Ingen server-verb for "Spring over/afvis" på capability-requests.** Status
   kan kun være pending → approved (→ executed). `denied` findes kun i
   `approval_feedback_log` (feedback-lag). Se Beslutning B2.

### Push-infrastruktur (verificeret)

`push_dispatcher.py` har tre kinds: `answer_ready`, `initiative`, `reminder`.
Data-only push (ingen title) → fcm_gateway bygger ikke notification-blok → notifee
bevarer tap-nav. `_persist_capability_approval_request` (workspace_capabilities.py:2177)
stempler allerede `scheduled_for_user_id` fra workspace_context — det er
modtageren til den nye push. Hook-punkt: efter `conn.commit()` i persist-funktionen
(kald ~468/515 sker gennem samme funktion).

## Beslutninger (taget i planen — bedes reviewet)

- **B1 — "Godkend altid" kun for sudo-exec-proposal i fase 1.** Serveren har en
  reusable-sudo-window-mekanisme i execute-endpointet (`sudo_approval_window_allows_request`)
  men ingen generel præfiks-regel for write-capabilities. Fase 1: "Godkend altid"
  vises kun når `execution_mode == 'sudo-exec-proposal'`; ellers nedtonet med
  "kommer i fase 3". Spec R8's præfiks-regel-UI kan tegnes, men må ikke lyve om
  hvad serveren gør.
- **B2 — "Spring over" = lokal dismissal i fase 1.** Ingen server-status for afvis
  på capability-requests (kun feedback-log). Kortet fjernes fra kø-visningen
  (dismissed-liste i app-state, session-lokal) og forbliver pending server-side —
  den asynkrone model gør at intet run blokerer. Server-side denied-status er fase
  3-arbejde (kræver kolonne-udvidelse + endpoint + surface-filter).
- **B3 — /mc/approvals-limit fix inkluderes i fase 1 (server).** Uden den kan
  køen ikke vise mere end 5 — for lidt efter 24t med B-runs.
- **B4 — Arbejde-tab er read-only + godkend i fase 1.** Tasks-visning og
  approve-kø. Dyk til run-detalje (R6-tråd), cancel, Review (diffs), New task og
  steer er fase 2/3 (spec Faser). UI'en skal IKKE antyde cancel/steer-knapper der
  ikke virker — kun godkend-verber er aktive.

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
- `core/services/push_dispatcher.py` — ny kind + `on_approval_requested()`
- `core/tools/workspace_capabilities.py` — hook efter persist-commit
- `apps/api/jarvis_api/routes/mission_control_runs_ops.py` — /mc/approvals limit-fix

App (branch codex/jarvis-mobile-companion-v1, apps/mobile/src):
- `theme/tokens.ts` — ny ChatGPT-paritet-palette
- `components/TopBar.tsx` (ny) — (≡) | [Snak|Arbejde] | (⟳)
- `components/SegmentedControl.tsx` (ny, genbruges to steder)
- `components/WorkTaskCard.tsx` (ny) — status/maskine/alder-kort
- `components/ApprovalCard.tsx` — opgraderet (R8-mønster + kø-kontekst)
- `screens/WorkScreen.tsx` (ny) — Tasks|Approve sub-tabs
- `lib/mcTypes.ts` (ny) — mission-control types
- `lib/mcClient.ts` (ny) — apiFetch-baserede kald
- `hooks/useWorkPolling.ts` (ny) — 3–5s polling, aktivt-tab-only
- `lib/push.ts` — håndter `approval_requested`-kind (badge/nav)
- `App.tsx` — mode-state + TopBar + WorkScreen-routing
- `ChatScreen.tsx` — egen header viger for TopBar (verificér ingen dobbelt-header)

## Tasks

### Task 1 (server): `approval_requested`-push-kind + hook

**Filer:** `core/services/push_dispatcher.py`, `core/tools/workspace_capabilities.py`
**Interfaces:** `push_dispatcher.on_approval_requested(user_id, *, request_id, run_id, capability_name, preview)` → dispatcher data-only push med `kind: "approval_requested"` (samme mønster som `_dispatch_run_done`: data-only, ingen title — notifee tap-nav bevares). Hook i `_persist_capability_approval_request` efter `conn.commit()`: læs `scheduled_for_user_id` fra den indsatte række (findes i INSERT), kald `on_approval_requested` guarded i try/except (push må aldrig kunne vælte persist).

- [ ] 1. Tilføj `on_approval_requested()` i push_dispatcher.py (kind `approval_requested`, preview = `proposal_reason`/`proposal_content_summary` ≤160 tegn; modtager = scheduled_for_user_id)
- [ ] 2. Hook i `_persist_capability_approval_request` efter commit
- [ ] 3. Test: enhedstest der mock'er `_fcm_send`, verificerer data-only payload + kind; test at hook-fejl ikke bryder persist (try/except)
- [ ] 4. Kør core-tests (pytest apps/tests + core/tests, relevant udsnit)
- [ ] 5. Commit (main): `feat(push): approval_requested kind + hook ved capability-approval filing`

### Task 2 (server): `/mc/approvals` kø-fix (cap 5 → limit)

**Filer:** `apps/api/jarvis_api/routes/mission_control_runs_ops.py`
**Fix:** `mc_approvals` skal hente direkte fra `recent_capability_approval_requests(limit=limit)` (db-modulet) i stedet for surface'ens hardcodede 5. Behold `recent_invocations`/`recent_events` fra surface.

- [ ] 1. Omskriv `mc_approvals`-route til direkte db-kald med respekt for limit
- [ ] 2. Test: route-test med 8 seedede requests → limit=20 returnerer alle 8; limit=3 → 3
- [ ] 3. Commit (main): `fix(api): /mc/approvals respect limit (var hardcoded 5)`

### Task 3 (app): tokens-migration til ChatGPT-palette

**Filer:** `apps/mobile/src/theme/tokens.ts` + alle komponenter der refererer gamle nøgler
**Krav:** nye nøgler (bg0 #000, surface1 #2F2F2F, surface2 #212121, fg1/2/3, accent-grådient-seed, danger #ff8080, ok #4CAF50, warn #FFB347). Renamed keys → type-fejl tvinger hver komponent igennem.

- [ ] 1. Migrér tokens.ts (behold struktur: color/radius/spacing/motion; tilføj `gradient`-seed + `bubble`-farver)
- [ ] 2. Gennemgå hver komponent der fejler typecheck; opdater farver efter R1–R8-mål (bobler, komponist, kort, cirkel-knapper)
- [ ] 3. `npm test` + `npm run typecheck` grønne
- [ ] 4. Commit (branch): `feat(mobile): ChatGPT-paritet dark palette (R1-R8 mål)`

### Task 4 (app): TopBar + mode-routing (Snak | Arbejde)

**Filer:** `components/TopBar.tsx` (ny), `components/SegmentedControl.tsx` (ny), `App.tsx`, `ChatScreen.tsx`, `screens/WorkScreen.tsx` (skal)
**Krav (R4/R5-mål):** (≡) menu-cirkel venstre · pille-segmented `Snak | Arbejde` midten · (⟳) sync-cirkel højre. Mode-state i AppBody (`useState<'snak'|'arbejde'>`). ChatScreen's egen header må ikke skabe dobbelt-header — verificér og fjern/inkorporér. WorkScreen = skal med sub-segmented `Tasks | Approve` (Tasks tom-state i denne task).

- [ ] 1. SegmentedControl (generisk, a11y: accessibilityRole="tab")
- [ ] 2. TopBar (menu → eksisterende side-menu/indstillinger; sync → manuelt poll-signal)
- [ ] 3. Mode-routing i App.tsx; WorkScreen-skal med tom-state
- [ ] 4. ChatScreen header-konflikt løst (ingen dobbelt-header; ChatScreen bevarer funktionalitet)
- [ ] 5. Tests: TopBar/SegmentedControl render + mode-skift; eksisterende ChatScreen-tests grønne
- [ ] 6. Commit (branch): `feat(mobile): top segmented control Snak|Arbejde`

### Task 5 (app): mission-control klient (types + REST)

**Filer:** `lib/mcTypes.ts` (ny), `lib/mcClient.ts` (ny)
**Interfaces:** typer for Run, ApprovalRequest, Overview (felter fra Server-kontrakter).
`mcClient`: `fetchOverview(config)`, `fetchRuns(config, limit)`, `fetchApprovals(config, limit)`,
`approveRequest(config, requestId)` — alt via eksisterende `apiFetch` (auth + ApiError-klassifikation).
`approveRequest` mapper 404 → ApiError('unknown') med tydelig besked ("godkendelse findes ikke længere").

- [ ] 1. mcTypes.ts (Run/ApprovalRequest/Overview/Summary)
- [ ] 2. mcClient.ts (4 funktioner)
- [ ] 3. Tests: mock fetch — shape-unwrapping, auth-header, 404→fejlbesked
- [ ] 4. Commit (branch): `feat(mobile): mission-control API client`

### Task 6 (app): Tasks-liste i Arbejde

**Filer:** `hooks/useWorkPolling.ts` (ny), `components/WorkTaskCard.tsx` (ny), `screens/WorkScreen.tsx`
**Krav (spec-beslutning 1):** aktive runs øverst (status running/pending/waiting), "afsluttet i dag"
under (kollapsbart). Kort: titel/beskrivelse (fra run), status-farveprik, maskine/source-tag
(A=Snak, B=autonom, C=agent), relativ alder (relativ-tid-hjælper findes: `lib/relativeDate.ts`).
Polling: `useWorkPolling(config, active: boolean, onData)` — poller `/mc/runs` + `/mc/overview`
hvert 3–5s KUN når Arbejde-tab aktivt og app i foreground (AppState); stopper ellers.
Data-normalisering: byg én liste fra `active_run` + `recent_runs`, dedup, sorteret.

- [ ] 1. useWorkPolling-hook (aktivt-tab + foreground-gating; cleanup ved unmount)
- [ ] 2. WorkTaskCard (R5-stil: statusprik, tag, alder; read-only i fase 1 — ingen
   tryk-verber, jf. B4: ingen falske verber der antyder cancel/steer)
- [ ] 3. WorkScreen Tasks-view: gruppering aktive/afsluttet-i-dag + tom-state + fejl-state (ErrorBanner)
- [ ] 4. Tests: polling-hook (timer-mock, gating), kort-rendering, gruppering
- [ ] 5. Commit (branch): `feat(mobile): Arbejde Tasks-liste (runs A/B/C)`

### Task 7 (app): Approve-kø med opgraderet ApprovalCard

**Filer:** `components/ApprovalCard.tsx`, `screens/WorkScreen.tsx` (Approve-view)
**Krav (R8-mønster + B1/B2):** kort viser anledningstekst (proposal_reason), tag
(capability_name + execution_mode), kode/detalje-blok (proposal_content_summary
eller — hvis tom — proposal_content (kommandoen/indholdet) + proposal_target_path), alder. Verber: **Godkend** (POST approve → optimistisk fjern fra
kø + bekræftelse), **Godkend altid** (kun hvis execution_mode=sudo-exec-proposal; ellers
nedtonet mærke "fase 3"), **Spring over** (B2: lokal dismissal). V1's binære onDeny
erstattes af dette tre-verb-mønster. Køen: pending fra /mc/approvals; refresh efter
godkendelse; "ingen ventende godkendelser"-tom-state. Alder-format via relativeDate.

- [ ] 1. ApprovalCard V2 (3 verber, R8-visuelt: tag + kodeblok + lodret stak)
- [ ] 2. Approve-view i WorkScreen: pending-kø + tom-state + fejl-state
- [ ] 3. approve-verb → mcClient.approveRequest → optimistisk UI + refresh; dismissed-liste (session-lokal)
- [ ] 4. Tests: ApprovalCard V2 (verber, betinget Godkend-altid), kø-logik (dismiss/approve)
- [ ] 5. Commit (branch): `feat(mobile): Approve-kø med R8-kort (godkend fra lommen)`

### Task 8 (app): push `approval_requested` → notifikation + nav

**Filer:** `lib/push.ts`, `App.tsx` (badge-tilstand), evt. `screens/WorkScreen.tsx`
**Krav:** data-only kind `approval_requested` håndteres: vis notifikation (notifee-mønster
findes i push.ts), tap → åbn app på Arbejde→Approve. Badge/prik på Arbejde-segmentet når
pending_count > 0 (fra polling — ingen ekstra state).

- [ ] 1. push.ts: håndter kind + tap-nav til Arbejde (deep-link-state i App)
- [ ] 2. Badge på Arbejde-tab ved pending > 0
- [ ] 3. Test: push-handler-enhedstest (kind-parsing + tap-kald); manuel smoke på enhed
- [ ] 4. Commit (branch): `feat(mobile): approval_requested push → Arbejde/Approve`

### Task 9: Live E2E — leverance-kriteriet

- [ ] 1. Sørg for server-ændringer (Task 1+2) er deployed og virker live; byg + installer app på Bjørns enhed (branch)
- [ ] 2. Trigger en ægte capability-approval-request (B/C-run der kræver approval — fx
  sudo-exec eller workspace-write uden for trust)
- [ ] 3. Verificér kæden: app lukket → push lander → åbn → kort i Approve → Godkend →
  run-status afspejler approved; request forsvinder fra pending-kø
- [ ] 4. Først når E2E er grøn live: marker plan færdig + opdater spec-status

## Accept-kriterier (fase 1)

1. Arbejde-tab viser A/B/C-runs samlet (aktive + afsluttet-i-dag, grupperet)
2. Approve-kø viser >5 requests (limit-fix virker) med korrekt alder/tag/anledning
3. Godkend fra mobil flipper request til approved server-side (POST endpoint)
4. Push lander når app er lukket; tap åbner Arbejde→Approve
5. UI matcher R1–R8-reference (side-for-side-check pr. skærm)
6. Alle tests grønne + live E2E gennemført (Bjørns krav: grønne tests ≠ systemet virker)

## Åbne punkter til eksternt review (Claude + Codex)

1. **B1 (Godkend altid begrænset)** — er sudo-only i fase 1 for restriktivt, eller skal
   præfiks-regel-UI bygges fuldt med server-støtte nu?
2. **B2 (Spring over = lokal dismissal)** — accepterbart for fase 1, eller skal
   denied-status bygges server-side med det samme?
3. **Task 4 header-konflikt** — ChatScreen's eksisterende header: fjernes den, eller
   laves TopBar om til en wrapper der lader ChatScreen beholde sin egen?
4. **R8-kortets "Godkend" semantik** — capability-approvals er deferred (approve →
   execute sker ved næste kald). Skal appen forklare dette i UI ("godkendt — udføres
   når Jarvis kalder capability'en igen")? Foreslået: ja, én forklarende linje.
5. **Token-migrationens rækkevidde** — hele appen skifter visuelt (også Snak). Er det
   ønsket i samme commit som Arbejde, eller skal Snak bevares indtil Arbejde er klar?
6. **Cancel-timing vs spec-beslutning 3** — spec-beslutning 3 lukkede "B/C-runs kan
   afbrydes fra mobilen", men planen (B4) udskyder cancel-knappen til fase 2 og gør
   fase 1 read-only + godkend. Er det den rette læsning (spec'ens Faser nævner ikke
   cancel i fase 1), eller skal cancel med allerede i fase 1?
