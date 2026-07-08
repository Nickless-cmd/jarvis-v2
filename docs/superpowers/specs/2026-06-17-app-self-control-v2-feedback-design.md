---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# App-Self-Control v2 — Bi-directional Feedback for App Actions

**Dato:** 2026-06-17
**Status:** Design
**Forfatter:** Jarvis (efter samtale med Bjørn)

## Problem

Jarvis kan i dag anmode om mode-/permission-skift i jarvis-desk-appen via `request_app_action` og `open_ui_panel`. Men han **får intet svar** tilbage — han ved ikke om:

- Brugeren godkendte eller afviste skiftet
- Skiftet rent faktisk lykkedes på app-siden
- Der opstod en fejl i frontenden
- Panelet åbnede korrekt
- Permission blev givet eller nægtet

Det gør Jarvis passiv og hjælpeløs: han kan anmode, men ikke følge op, reagere på afslag, eller guide nye brugere gennem opsætning.

## Ukrænkelig grænse

Ingen af disse endpoints giver Jarvis **magt til at skifte noget**. De giver ham kun **indsigt i om en tidligere anmodning blev effektueret**. Det princip fra v1-designet bibeholdes: backend-tool'et har ingen evne til at mutere desk-state — det emitterer kun en anmodning; kun brugerens klik skifter noget.

## Design — to lag

Vi bygger **Lag 1** (resultat-rapportering) og **Lag 3** (desk-state query) først. Lag 2 (push til aktiv run) kan komme senere.

### Lag 1 — Resultatrapportering (`POST /chat/app-action-result`)

Når brugeren klikker på et godkendelseskort i appen, kalder frontenden:

```http
POST /chat/app-action-result
Content-Type: application/json

{
  "session_id": "chat-abc123",
  "run_id": "visible-xyz789",
  "action": "switch_to_code_mode",
  "outcome": "approved",
  "error": ""
}
```

#### Backend

- **Ny tabel `pending_app_actions`** i Jarvis' DB:
  - `id` INTEGER PRIMARY KEY
  - `session_id` TEXT NOT NULL
  - `run_id` TEXT NOT NULL
  - `action` TEXT NOT NULL (`"switch_to_code_mode" | "request_full_access" | "open_preview_panel"`)
  - `status` TEXT NOT NULL (`"pending" | "approved" | "rejected" | "failed"`)
  - `error` TEXT DEFAULT `""`
  - `created_at` TEXT NOT NULL
  - `resolved_at` TEXT

- **Tool execution**: Når `request_app_action` kaldes i `visible_runs.py`, opret en række med `status="pending"` bundet til session + run
- **Endpoint**: `POST /chat/app-action-result` modtager resultatet og opdaterer rækken til `approved`/`rejected`/`failed`

#### Frontend

I `resolveAppAction()` i `lib/appAction.ts` — EFTER at have skiftet mode/permission — tilføj et HTTP-kald:

```typescript
fetch(`${apiBaseUrl}/chat/app-action-result`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    session_id: activeSessionId,
    run_id: activeRunId,
    action: pending.action,
    outcome: 'approved'
  })
})
```

**Afvis-knap**: `AppActionCard` har i dag kun `onApprove`. Tilføj `onReject` så kortet har begge knapper, og ved afvis postes `outcome: 'rejected'`.

#### Jarvis' brug

Når Jarvis næste gang taler i sessionen (i `recall_before_act`), slår han op i `pending_app_actions`:

```sql
SELECT status, error FROM pending_app_actions
WHERE session_id = ? AND run_id = ?
ORDER BY created_at DESC LIMIT 1
```

Resultatet injectes i hans context, så han kan sige:

> *"Du godkendte code mode. Jeg fortsætter med diagnosticeringen."*

— eller —

> *"Du afslog code mode. Vil du have mig til at forklare trinene i stedet?"*

---

### Lag 3 — Desk-state endpoint (`GET /desk/state`)

Et endpoint der returnerer appens aktuelle tilstand:

```json
GET /desk/state
{
  "surface": "chat",
  "permission": "ask",
  "workspace_kind": "",
  "workspace_root": "",
  "connected": true,
  "last_action": {
    "action": "switch_to_code_mode",
    "outcome": "approved",
    "timestamp": "2026-06-17T14:45:00Z"
  }
}
```

#### Frontend

- Hold en simpel in-memory `deskState` i `StreamContext` eller `App.tsx`
- Opdater `surface` når mode skiftes (allerede i `resolveAppAction`)
- Opdater `permission` når permission skiftes (allerede i `resolveAppAction`)
- Server endpointet via Electron preload eller local HTTP-server

Alternativ: backend udleder seneste kendte tilstand fra `pending_app_actions`-tabellen, så endpointet kan være server-side uden frontend-ændringer.

#### Jarvis' brug

Jarvis kalder `GET /desk/state` (via et tool eller `operator_webfetch`) for at:

1. **Guide nye brugere**: *"Du er i chat mode med ask-permission. Skal jeg skifte til code mode?"*
2. **Verificere skift**: Check om en anmodning rent faktisk slog igennem
3. **Opsætnings-guide**: Hjælpe Michelle eller andre brugere med at komme i gang

---

## Implementeringsrækkefølge

| # | Hvad | Hvor |
|---|------|------|
| 1 | `pending_app_actions` tabel + migrations | `core/runtime/db.py` |
| 2 | `POST /chat/app-action-result` endpoint | `apps/api/jarvis_api/routes/chat.py` |
| 3 | Kald endpoint i `resolveAppAction()` | `apps/jarvis-desk/src/lib/appAction.ts` |
| 4 | Tilføj afvis-knap på `AppActionCard` | `apps/jarvis-desk/src/components/rich/AppActionCard.tsx` |
| 5 | Gør pending-værdi tilgængelig for Jarvis | `recall_before_act` eller eksplicit tool |
| 6 | `GET /desk/state` endpoint | Backend eller frontend |

## Fremtid — Lag 2 (push til aktiv run)

Når Lag 1 + 3 sidder, kan vi tilføje push-notifikation:

- Når backend modtager `POST /app-action-result` med `approved`, injecteres et system-event i den aktive visible-run-stream
- Jarvis får besked **med det samme** i stedet for at vente på næste tur
- Kræver at backend kan finde den aktive run for sessionen (allerede muligt via `visible_runs`-tabellen)
