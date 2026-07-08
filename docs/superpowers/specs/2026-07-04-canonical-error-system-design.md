---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Canonical Error System — én kilde-sandhed for hele stakken

**Dato:** 2026-07-04
**Status:** Design under udarbejdelse (Bjørn har godkendt retning)
**Forfatter:** Jarvis + Bjørn
**Parent project:** Centralen / jarvis-desk / jarvis-api

---

## 1. Problem & intention

I dag har systemet mange gates og fallback-tekster, men de viser sjældent den *endelige* fejl. Desk-app og backend kaster enten hardcoded fallbacks eller blokerer et svar helt, i stedet for at markere det som usikkert.

Bjørns observation: hvis Centralen havde en **fejlkode på alt der gik ind og ud**, ville tracing være nemmere — og brugeroplevelsen ville være mere troværdig.

**Intention:** Bygge ét canonical error-system der dækker hele stakken. Centralen er dirigent. Fejl er data, ikke tekst. Self-healing først. Transparent propagation. Ingen teater-fallbacks.

---

## 2. Scope

Systemet dækker **alle lag**:

| Lag | Eksempler på fejl |
|-----|-------------------|
| **desk-app** | render-fejl, stream disconnect, bruger-afbrud, timeout |
| **api / runtime** | auth, rate limiting, routing, serialization |
| **Centralen** | daemon-død, nerve-timeout, circuit open, cutoff |
| **model-provider** | refusal, rate limit, context exceeded, provider unavailable |
| **host / infra** | disk full, memory pressure, CPU pressure, syslogd død |

Centralen modtager, klassificerer, healing-handler, eskalerer og propagérer. Alle andre lag rapporterer **råt** — Centralen beriger og beslutter.

---

## 3. Design-principper

1. **Én kilde-sandhed.** Én fejltype har ét canonical navn, ét canonical objekt, ét log-sted.
2. **Fejl er data, ikke tekst.** UI viser tekst baseret på `kind` + `severity` + `recoverable` — ikke en hardcoded streng.
3. **Self-healing først.** Hvis en fejl kan rettes automatisk, gør Centralen det og rapporterer udfaldet.
4. **Eskaler gradvist.** `auto` → `retry` → `user_action` → `degraded` → `fatal`.
5. **Fail-soft, aldrig fail-silent.** Brugeren skal altid vide om systemet kører i nedsat tilstand.
6. **Traceability.** Hver fejl bærer `origin` (lag, komponent, fil, linje) + `correlationId` + `sessionId` + `runId`.

---

## 4. Canonical Error Object

```ts
interface CanonicalError {
  id: string;                    // UUID
  kind: string;                // dot-notation, se §5
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  scope: 'global' | 'session' | 'run' | 'tool' | 'infra';
  recoverable: 'auto' | 'retry' | 'user_action' | 'degraded' | 'fatal';

  origin: {
    layer: 'desk' | 'api' | 'runtime' | 'central' | 'model' | 'host';
    component: string;         // fx "streamReducer", "ollama_adapter", "pfsense_syslog"
    file?: string;
    line?: number;
  };

  context: Record<string, unknown>; // rå data, aldrig PII
  message: string;             // canonical besked (engelsk, stabil)
  userMessage?: string;          // lokaliseret, kort, til UI

  action?: {
    type: string;                // fx "restart_daemon", "backoff_retry"
    attempts: number;
    maxAttempts: number;
    lastAttemptAt?: string;      // ISO-8601
    result?: 'pending' | 'success' | 'failed';
    log?: string[];              // handlingens output
  };

  correlationId?: string;
  sessionId?: string;
  runId?: string;
  toolCallId?: string;

  createdAt: string;             // ISO-8601
  updatedAt: string;             // ISO-8601
}
```

**Regel:** `message` må aldrig være en LLM-genereret forklaring. Den er en fast, maskinlæsbar streng der kan bruges til aggregation og alerts.

---

## 5. Taxonomi (v1)

Fejl opdeles i `kategori.årsag`. Eksempler:

| Kind | Betydning | Typisk recoverable |
|------|-----------|-------------------|
| `network.timeout` | Request nåede ikke frem i tide | `retry` |
| `network.unreachable` | Host ikke tilgængelig | `auto` / `degraded` |
| `dns.failed` | DNS-opløsning fejlede | `retry` |
| `tls.failed` | TLS handshake fejlede | `user_action` |
| `auth.token_expired` | Auth token udløbet | `auto` (refresh) |
| `auth.forbidden` | Manglende rettigheder | `user_action` |
| `trust.workspace_untrusted` | Workspace ikke trusted i code mode | `user_action` |
| `central.daemon_dead` | En daemon er død | `auto` (restart) |
| `central.nerve_timeout` | Nerve svarer ikke | `retry` → `degraded` |
| `central.circuit_open` | Circuit breaker åben | `degraded` |
| `self.cutoff` | Run blev afbrudt af cutoff | `retry` / `user_action` |
| `self.rate_limited` | Egen egress begrænset | `retry` |
| `model.refusal` | Model nægtede at svare | `user_action` |
| `model.rate_limited` | Provider rate limit | `retry` |
| `model.context_exceeded` | Kontekstvindue overskredet | `user_action` |
| `provider.unavailable` | Model-provider nede | `degraded` |
| `tool.permission_denied` | Tool ikke tilladt | `user_action` |
| `tool.execution_failed` | Tool kørte, men fejlede | `retry` / `user_action` |
| `tool.timeout` | Tool nåede ikke at færdiggøre | `retry` |
| `workspace.file_missing` | Refereret fil findes ikke | `user_action` |
| `ui.stream_disconnect` | Desk mistede SSE-forbindelse | `auto` (reconnect) |
| `ui.render_error` | React render fejlede | `degraded` |
| `host.disk_full` | Disk næsten fuld | `user_action` |
| `host.memory_pressure` | Høj memory-brug | `degraded` |
| `host.cpu_pressure` | Høj CPU-brug | `degraded` |
| `pfsense.syslogd_dead` | pfSense syslogd død | `auto` (restart) |

Taxonomien versioneres. Nye `kind` tilføjes kun via Centralen — aldrig som hardcoded strenge spredt i koden.

---

## 6. Centralen som dirigent

Centralen får et nyt modul: `core/services/central_error_conductor.py`.

### 6.1 Ansvar

1. **Modtag** errors fra alle lag via én indgang.
2. **Klassificer** rå fejl til canonical `kind`.
3. **Berig** med `severity`, `recoverable`, `origin`, `correlationId`.
4. **Afgør** om self-healing skal køres.
5. **Udfør** healing via tilladte actions.
6. **Propagér** resultat til abonnenter (desk, logs, alerts).
7. **Lær** success-rate per `kind` + `action`.

### 6.2 Indgange

- **Intern:** `central_error_conductor.report(error: CanonicalError)` kaldt fra Python-kode.
- **HTTP:** `POST /central/errors` — bruges af desk og eksterne monitors.
- **SSE:** `GET /central/errors/stream` — desk abonnerer på realtidsfejl for den aktive session.
- **Log-scraper:** Centralen læser også strukturerede log-linjer og konverterer dem.

### 6.3 Governance

- Healing-actions køres kun hvis de er **allowlistet** og **idempotente**.
- `SECURITY`-klassede handlinger går gennem `gate_kernel.decide()` før de udføres.
- Max attempts + cooldown håndhæves centralt — ikke i hver consumer.

---

## 7. Self-healing matrix (v1)

| Kind | Action | Max attempts | Cooldown | Escalation |
|------|--------|--------------|----------|------------|
| `central.daemon_dead` | `restart_daemon` | 3 | 10s | `degraded` |
| `network.timeout` | `backoff_retry` | 5 | 250ms → 8s | `user_action` |
| `auth.token_expired` | `refresh_token` | 2 | 0 | `user_action` |
| `ui.stream_disconnect` | `reconnect_with_resume` | 5 | 1s → 30s | `user_action` |
| `pfsense.syslogd_dead` | `restart_syslogd` | 3 | 60s | `degraded` |
| `model.rate_limited` | `switch_lane` | 2 | 0 | `degraded` |
| `host.memory_pressure` | `pause_non_essential` | 1 | 60s | `user_action` |

Healing-resultatet skrives tilbage på `error.action.result`. Hvis det lykkes, markeres fejlen `resolved`. Hvis ikke, eskaleres `recoverable`.

---

## 8. Propagation flow

```
desk-app          api/runtime          Centralen          model/host
   |                   |                    |                  |
   |  POST /errors     |  report()          |                  |
   |------------------>|------------------->|                  |
   |                   |                    | classify + enrich|
   |                   |                    | decide heal?     |
   |                   |                    | run action       |
   |  SSE /stream      |                    |                  |
   |<------------------|<-------------------|                  |
   |  show card        |  propagate         |  log + learn     |
```

**Vigtigt:** Desk spørger Centralen "hvad skete der?" — den opfinder ikke selv forklaringer. Det fjerner teater-fallbacks.

---

## 9. Desk UI mapping

### 9.1 Global system health

Lille chip i sidebar-fod eller header:

- **Grøn:** Ingen uløste fejl.
- **Gul:** Én eller flere `degraded` / `user_action` fejl.
- **Rød:** Kritisk fejl eller selvhealing fejlet.

Klik åbner **Transparency Log**.

### 9.2 Transparency Log

Tidslinje over fejl for den aktive session + globale fejl:

- Tidspunkt
- Kind
- Hvad systemet gjorde
- Resultat
- CTA (hvis `user_action`)

### 9.3 Inline error cards

Når en fejl rammer et run/tool/stream, vises et kort i samtalefladen:

```
┌─────────────────────────────────────┐
│ ⚠️  Verktøjet kunne ikke køre        │
│ Filen findes ikke længere.          │
│ [Vælg fil igen]  [Ignorér]          │
└─────────────────────────────────────┘
```

Kortet viser altid:
1. **Hvad gik galt** (fra `userMessage`)
2. **Hvad systemet gjorde** (healing-status)
3. **Næste skridt** (én CTA)

---

## 10. API surface (forslag)

```http
POST /central/errors
Body: CanonicalError
→ 202 Accepted + { id }

GET /central/errors/:id
→ CanonicalError

GET /central/errors?scope=session&sessionId=...
→ { items: CanonicalError[] }

POST /central/errors/:id/heal
→ { action, result }

GET /central/health
→ { status: green|yellow|red, openErrors: number, degraded: boolean }

GET /central/errors/stream
→ SSE stream af CanonicalError for abonnentens scope
```

---

## 11. Implementation steps

### Fase 1 — Skelet
- Definér `CanonicalError` dataclass / TS-interface.
- Opret `central_error_conductor.py` med report + classify + log.
- Tilføj `POST /central/errors` endpoint.

### Fase 2 — Self-healing
- Implementér action-runner med allowlist.
- Tilføj healing-actions for top-5 fejl (daemon-død, stream disconnect, token refresh, syslogd, rate limit).

### Fase 3 — Desk integration
- Tilføj error-stream consumer i desk.
- Byg `ErrorCard` + `TransparencyLog` + `SystemHealthChip`.
- Fjern hardcoded fallback-tekster ét sted ad gangen.

### Fase 4 — Audit & migration
- Kør audit (se §12) og erstatter alle gates/fallbacks med canonical errors.
- Etablér test-suite der verificerer at nye fejl altid får en `kind`.

---

## 12. Audit findings

> *Udfyldes efter kode-gennemgang. Se companion-fil eller opdateres her.*

### 12.1 Desk-app — kendte hotspots

- `AiTransparencyNotice.tsx` — hardcoded first-run tekst (ikke fejl, men mønster).
- `StatusBar.tsx` — fallback til default model uden error-kode.
- `Composer.tsx` — upload-fejl håndteres lokalt uden propagation.
- `useStream.ts` / `streamReducer.ts` — disconnect og cutoff håndteres som status, ikke errors.
- `SetupScreen.tsx` — connection-fejl vises som generisk besked.

### 12.2 Backend / runtime — kendte hotspots

- `heartbeat_runtime.py` — cutoff og daemon-død logges, men ikke som canonical errors.
- `visible.py` / SSE-håndtering — cutoff-spøgelset har været en saga; mangler error-kind.
- `gate_kernel.py` — verdicts bør beriges med error-koder.
- `ollama_adapter.py` / model adapters — timeout, refusal, rate limit bliver ofte til generiske exceptions.
- `pfsense_syslog` nerve — auto-healer, men rapporterer ikke canonical error.

### 12.3 Næste audit-opgave

Systematisk søgning efter:
- `catch` / `except` uden re-raise
- `try { ... } catch { ... }` med hardcoded besked
- `fallback` / `default` / `placeholder` tekster
- `console.error` / `logger.error` uden error-kode
- Stilhed: funktioner der returnerer `null` / `undefined` / `None` ved fejl

---

## 13. Open questions

1. Skal `userMessage` genereres centralt (én tekst) eller lokaliseres i desk?
2. Skal fejl persistere i DB eller kun leve i memory + log?
3. Hvordan håndteres PII i `context`? (Foreslå: aldrig rå prompts, kun metadata.)
4. Skal gamle incidents i Centralen migreres til nyt system, eller startes der fra nu?

---

## 14. Next steps

1. Bjørn godkender spec-retning.
2. Udfør fuld audit (desk + backend) og opdater §12.
3. Implementér Fase 1 skelet.
4. Test med én konkret fejl (fx `pfsense.syslogd_dead`) end-to-end.
