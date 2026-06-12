# Cowork-flade (jarvis-desk) — Design

**Dato:** 2026-06-12
**Status:** Godkendt af Bjørn — klar til implementerings-plan
**Forfatter:** Claude Code (med Bjørn)

## Formål

Cowork er **arbejd-sammen-fladen** i jarvis-desk: et dashboard hvor Bjørn (og
senere andre brugere) ser og styrer hvad Jarvis vil gøre — uden at grave i chat.
Det er Jarvis' kontrol-/koordinerings-plan *inde i appen*, ved siden af chat
(snak) og code (han udfører).

Cowork er **ikke** et delt dokument og **ikke** endnu en chat. Det er ren
oversigt + handling: se → godkend/afvis → hurtige actions. Vil du tale med
Jarvis, gør du det i chat.

Cowork afspejler IKKE en bestemt Claude Desktop-feature — det er Bjørns egen
idé, mere konkret end noget i Claude Desktop, designet efter hans workflow.

## De fire søjler

1. **Godkendelser** (hero, øverst venstre) — én samlet kø af alt Jarvis venter
   på et ja til: tool-intents, capability-requests, fil-ændringer (diffs) og
   initiativ-forslag. Hvert item har Godkend / Afvis (+ Diff for fil-ændringer).
2. **Planer** — planer Jarvis har foreslået/arbejder på, med trin-progress.
3. **Todo & initiativer** — tjekliste over opgaver/initiativer.
4. **Kanaler** — kanal-status (Discord/Telegram/webchat). **Kun owner.**

## Rolle-model (load-bearing)

| Rude | Owner (Bjørn) | Bruger (Mikkel m.fl.) |
|---|---|---|
| Godkendelser | alle items | kun egne (skriv til *deres* workspace/maskine) |
| Planer | alle | kun egne |
| Todo/initiativer | alle | kun egne |
| **Kanaler** | **ja** | **NEJ — slet ikke synlig** |

Kanaler er owner-only fordi Jarvis kun lever på Bjørns Discord-server; vi åbner
aldrig for "brugere får Jarvis på deres egen Discord" (dyrt + uønsket). Backend
**håndhæver** grænsen (bruger der kalder kanal-endpointet får 403); frontend
skjuler bare ruden. Genbruger `role` fra `/api/whoami` + den eksisterende
multi-user/workspace-gating fra code-mode.

## Arkitektur

### Frontend (apps/jarvis-desk)
- `views/CoworkView.tsx` — 2×2 grid (owner) / 2×2 med kanal-ruden udeladt (bruger).
  Header med presence-ring + ConnectionPill (som code). Erstatter stub'en.
- `components/cowork/ApprovalQueue.tsx` — kø-rude; items med Godkend/Afvis/Diff.
- `components/cowork/PlansPane.tsx` — planer + trin-progress.
- `components/cowork/TodoPane.tsx` — todo/initiativ-tjekliste.
- `components/cowork/ChannelsPane.tsx` — kanal-status (kun owner).
- `hooks/useCoworkData.ts` — henter de fire datasæt + abonnerer på live-updates.
- `lib/api.ts` — nye klient-funktioner (se endpoints nedenfor).

### Backend (apps/api/jarvis_api/routes/cowork.py — NY rute-fil)
Primært genbrug; ét nyt aggregerings-endpoint.

- **`GET /cowork/queue`** (NY) — samler server-side til én rolle-scopet liste:
  tool-intents (`/approvals`/`_capability_invocation_surface`),
  capability-approval-requests, afventende fil-diffs, og initiativ-forslag
  (`initiative_queue` + `autonomy/proposals`). Owner=alt; bruger=kun egne
  (filtreret på `user_id`). Hvert item: `{id, kind, title, detail, diff?, source}`
  hvor `source` fortæller hvilket eksisterende approve/reject-endpoint der skal
  kaldes.
- **`POST /cowork/queue/{id}/approve`** og **`/reject`** (NY, tynde) — router til
  det rette eksisterende endpoint baseret på item'ets `source`. Alternativt
  kalder frontend de eksisterende endpoints direkte; aggregatoren returnerer
  `approve_url`/`reject_url`. (Plan-detalje afgøres i implementerings-planen —
  default: tynd router for ét konsistent kald.)
- **Planer:** genbrug eksisterende `plan_proposals` + jarvisx `/plans` (scopet
  pr. bruger). Ny tynd `GET /cowork/plans` hvis scoping kræver det.
- **Todo:** genbrug `agent_todos` (`list_todos`/`add_todo`/`update_todo_status`).
- **Kanaler:** `GET /cowork/channels` (NY) — returnerer kanal-status fra Mission
  Control-state. **403 for ikke-owner.**

Alt blokerende arbejde (subprocess/bro/aggregering over flere kilder) køres via
`asyncio.to_thread` — jf. [[reference_async_blocking_worker]]: jarvis-api kører
`--workers 1`, så et blokerende kald fryser hele API'et.

### Real-time
`useCoworkData` abonnerer på Mission Control-websocket'en (`/ws`, `live.py`) og
re-henter den relevante rude når et event i den familie ankommer (approvals,
initiatives, channel, plan). Polling-fallback hver ~6s (som active-runs) hvis
WS er nede.

## Data-flow

```
whoami → role          ┐
                       ├→ useCoworkData ─→ GET /cowork/queue   (rolle-scopet)
/ws (live events) ─────┘                ─→ GET /cowork/plans
                                        ─→ agent_todos
                                        ─→ GET /cowork/channels (kun owner)
ApprovalQueue.[Godkend] → POST /cowork/queue/{id}/approve → eksisterende approve-endpoint
```

## Fejlhåndtering
- Manglende/utilgængeligt endpoint → ruden viser en rolig tom-tilstand ("ingen
  afventende godkendelser"), ikke en fejl-banner.
- 403 på kanaler (bruger) → ruden renderes slet ikke (frontend skjuler).
- WS nede → polling-fallback; ingen synlig fejl.
- Approve/reject der fejler → item bliver i køen + en lille inline-fejl på kortet.

## Test
- **Frontend (vitest):** hver rude renderer sine items; ApprovalQueue kalder
  approve/reject; CoworkView skjuler kanal-ruden for `role=member`; useCoworkData
  merger + live-update.
- **Backend (pytest):** `/cowork/queue` owner-vs-bruger scoping (bruger ser kun
  egne); `/cowork/channels` 403 for ikke-owner; aggregatoren samler de fire
  kilder korrekt.

## Afgrænsning (YAGNI for v1)
- Ingen chat-lane i cowork (snak sker i chat).
- Ingen redigering af planer/todos *inde* i cowork ud over hurtige actions
  (godkend plan, tilføj/afkryds todo, abandon initiativ).
- Ingen bruger-variant af kanaler (findes ikke; owner-only punktum).
- Cowork for andre brugere end owner testes men er ikke i daglig brug endnu.

## Genbrug — eksisterende backend
- `core/services/plan_proposals.py`, `agent_todos.py`, `initiative_queue.py`
- `routes/mission_control.py`: `/approvals`, `/initiatives`, `/autonomy/proposals`,
  `/capability-approval-requests`, `/tool-intent/approve`
- `routes/jarvisx.py`: `/plans` (+ approve/dismiss)
- `routes/live.py`: `/ws` (Mission Control event-stream)
- `core/tools/tool_scoping.py` + `core/identity/workspace_context.py`: rolle/scoping
