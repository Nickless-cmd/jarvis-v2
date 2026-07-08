---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Canonical Error System — Implementation Plan

> ⚠️ **REVIDERET af [REVIEW](2026-07-04-canonical-error-system-REVIEW.md) §2+§6:** Fase 0 skal UDVIDE eksisterende `central_error_envelope` (ikke ny `CanonicalError`), adapter over `central_anomaly`+`observe` (ikke ny conductor), eskalér til `db_central_incidents` (ikke ny store), delegér Provider/Lane-healers til eksisterende visible_runs-failover. ~60-70% findes allerede. Ægte nyt = healer-registret + desk-UI + audit-oprydning.

**Dato:** 2026-07-04
**Forfatter:** Jarvis
**Status:** Follow-up til spec + audit (commit 4677df93). Lukker 7 huller fra self-review.

> **Læs i denne rækkefølge:** design → spec → audit → implementation plan (denne).

---

## 1. Hvad denne plan gør

Self-review af commit `4677df93` fandt 7 huller. Denne plan lukker dem før implementering:

| # | Hul | Hvor | Status |
|---|-----|------|--------|
| 1 | Spec+audit overlapper | begge | → Separeres her |
| 2 | Forældede linjenumre | audit | → Re-auditeres med friske søgninger |
| 3 | Ingen API-kontrakt | spec | → Definér `POST /central/errors` kontrakt |
| 4 | Self-healing mekanisme uklar | design | → Konkrete healere beskrevet |
| 5 | Ingen migrationsplan | audit | → Faser + per-fil checkliste |
| 6 | Centralen-down scenario mangler | spec | → Nødfald i desk |
| 7 | Test-strategi for tynd | spec | → Test-per-fase + integationstest |

---

## 2. Hvad self-review konkluderede

Spec + audit er **stærk som retning**. De 7 huller er **overfladiske** — intet fundamentalt forkert. Planen er at lukke dem som en **separat implementeringsplan** (denne fil), så spec'en forbliver ren og konceptuel.

### Specifikt forkastet:
- **Gen-skrivning af spec** — unødvendigt. Hullerne handler om *hvordan*, ikke *hvad*.
- **Vent med implementering** — hullerne er overfladiske nok til at implementation kan starte parallelt.

---

## 3. API-kontrakt: `POST /central/errors`

### Endpoint
```
POST /internal/errors/report
```

### Request body
```json
{
  "kind": "network.timeout",
  "severity": "warning",
  "recoverable": "retry",
  "message": "Stream modtog ikke heartbeat i 75 sekunder.",
  "origin": {"file": "streamClient.ts", "line": 142, "function": "onHeartbeatTimeout"},
  "scope": "session",
  "session_id": "chat-a1b2c3",
  "run_id": "run-abc123",
  "context": {
    "api_base_url": "https://api.srvlab.dk",
    "latency_ms": 970,
    "attempt": 3
  },
  "source": "desk"
}
```

### Felter

| Felt | Type | Obligatorisk | Beskrivelse |
|------|------|-------------|-------------|
| `kind` | string | ja | Error-kind fra taxonomy (37 kategorier) |
| `severity` | enum | ja | `debug` / `info` / `warning` / `error` / `critical` |
| `recoverable` | enum | ja | `auto` / `retry` / `user_action` / `degraded` / `permanent` |
| `message` | string | ja | Menneske-læselig, maks 200 tegn |
| `origin` | dict | ja | `{file, line?, function?}` |
| `scope` | enum | ja | `global` / `session` / `run` / `tool` |
| `session_id` | string | hvis scope=session/run | Session-ID |
| `run_id` | string | hvis scope=run | Run-ID |
| `context` | dict | nej | Valgfri metadata (latency, attempt, workspace) |
| `source` | enum | ja | `desk` / `api` / `runtime` / `central` / `provider` / `host` |

### Responses

| Status | Betydning |
|--------|-----------|
| 202 | Accepteret — Centralen har modtaget og klassificeret |
| 400 | Ugyldig kind eller manglende obligatorisk felt |
| 429 | Rate-limited (se §6) |
| 503 | Centralen selv er nede — caller skal bruge nødfald (§7) |

### Auth
- **Internal:** Kun kald fra `localhost` / `127.0.0.1` / `/run/jarvis.sock`.
- **Ingen token påkrævet** — det er en intern bus, ikke en ekstern API.
- Desk sender via backend proxy (`POST /api/internal/errors/report` → videresendes til Centralens socket).

---

## 4. Self-healing mekanismer (konkrete)

### Healer registry

Alle healere implementerer:
```python
class ErrorHealer:
    kind: str  # matcher ErrorKind
    max_attempts: int
    cooldown_seconds: int
    
    def heal(self, error: CanonicalError) -> HealingResult:
        """Returnér SUCCESS, RETRY, ESCALATE, eller UNKNOWN."""
```

### Healer-katalog (fase 1, P0-P1)

| ErrorKind | Healer | Handling | Failure-escalation |
|-----------|--------|----------|--------------------|
| `network.timeout` | `BackoffRetryHealer` | Backoff 250ms→2s→8s→30s, max 4 forsøg | `degraded` |
| `network.unreachable` | `BackoffRetryHealer` | Samme som timeout | `critical` |
| `auth.token_expired` | `TokenRefreshHealer` | Kald `/auth/refresh`, gen-send request | `user_action` |
| `central.daemon_dead` | `DaemonRestartHealer` | `systemctl restart jarvis-<daemon>` | `critical` |
| `central.circuit_open` | `CircuitResetHealer` | Vent cooldown, test, reset | `user_action` |
| `model.rate_limited` | `LaneSwitchHealer` | Skift lane, gen-send | `permanent` (hvis alle lanes ramt) |
| `provider.unavailable` | `ProviderFailoverHealer` | Skift til backup provider | `degraded` |
| `tool.timeout` | `ToolRetryHealer` | Gen-kald med timeout * 1.5, max 2 | `user_action` |
| `pfsense.syslogd_dead` | `SyslogRestartHealer` | API-kald til pfSense, max 3, cooldown 60s | `known_benign` (auto-healet) |

### Cooldown after recovery
Hvis en healer lykkes, markeres fejlen som `healed` i 60 sekunder — under cooldown sluges nye forekomster af samme `kind`+`origin` stille.

---

## 5. Migrationsplan

### Fase 0: Infrastruktur (1-2 dage)

| Fil | Handling |
|-----|----------|
| `core/services/central_error_conductor.py` | NY: error receiver, classifier, healer registry |
| `core/services/error_healers.py` | NY: alle healere implementeret |
| `apps/api/jarvis_api/routes/internal_errors.py` | NY: `POST /internal/errors/report` |
| `apps/api/jarvis_api/app.py` | TILFØJ: mount internal_errors router |
| `core/services/central_cadence_conductor.py` | TILFØJ: error drain i tick cycle |

### Fase 1: Backend + runtime (2-4 dage)

| Fil | Handling |
|-----|----------|
| `apps/api/jarvis_api/routes/chat.py` | Erstat 12 `except Exception: pass` med canonical error report |
| `core/services/visible_runs.py` | Erstat 35+ `except:` med canonical errors |
| `core/services/gate_execution.py` | Erstat P0 gates (permission/timeout) |
| `core/services/heartbeat_runtime.py` | Wrap daemon-starts i canonical fejl |
| `core/services/pfsense_syslog.py` | Auto-heal → canonical heal report |
| `core/services/network_health.py` | Canonical oversættelse af spændinger |
| `core/services/central_private_observe.py` | Erstat 6 `except Exception: pass` |

### Fase 2: Desk-app UI (2-3 dage)

| Fil | Handling |
|-----|----------|
| `apps/jarvis-desk/src/lib/streamClient.ts` | Refactor `StreamError` → canonical error dispatch |
| `apps/jarvis-desk/src/lib/api.ts` | Tilføj `reportError()` wrapper |
| `apps/jarvis-desk/src/hooks/useCanonicalError.ts` | NY: hook der abonnerer på error bus |
| `apps/jarvis-desk/src/components/ErrorCard.tsx` | NY: canonical error UI-kort |
| `apps/jarvis-desk/src/components/SystemHealth.tsx` | NY: health chip med error-count |
| `apps/jarvis-desk/src/views/ChatView.tsx` | Erstat 6 `.catch` → canonical |
| `apps/jarvis-desk/src/views/CodeView.tsx` | Erstat 8 `.catch` → canonical |
| `apps/jarvis-desk/src/components/composer/Composer.tsx` | Erstat send-fejl → canonical |

### Fase 3: Centralen integration (2 dage)

| Fil | Handling |
|-----|----------|
| `core/services/central_private_observe.py` | Canonical error drain → Central anomaly system |
| `core/services/central_adaptation.py` | Lær af fejl-mønstre (healing rate pr. kind) |
| `core/services/central_membrane_watch.py` | Error rate → anomali-detektion |

### Fallback-implementationsrækkefølge hvis tid er knap:
P0: Fase 0 + P0 gates i `gate_execution.py` + desk `streamClient.ts`
P1: Fase 1 + Phase2 desk-hotspots (ChatView, CodeView)
P2: Fase 2-complete + Fase 3

---

## 6. Rate-limiting & circuit breaker

Centralens error-endpoint har:
- **Per source (desk/api/runtime):** 100 requests / 10 sekunder
- **Per kind (network.timeout):** 10 / minut — efter 10 sluges stille i 60s
- **Global:** 500 / minut

Circuit breaker på Centralen-down:
- Hvis Centralen ikke svarer på 3 error-reports på 30 sekunder → **circuit open** i 120 sekunder.
- Desk faller tilbage til lokal error-buffer (in-memory queue, max 100).
- Når Centralen er tilbage, flush buffer.

---

## 7. Centralen-down scenario (nødfald)

Hvis Centralen selv er nede eller error-endpoint returnerer `503`:

```python
class EmergencyFallback:
    """
    Når Centralen ikke kan tage imod errors:
    1. Buffer i lokal in-memory queue (max 100, FIFO drop).
    2. Prøv igen hvert 15. sekund (backoff 15s→30s→60s).
    3. Hvis >5 min uden Centralen: skriv til ~/.jarvis-v2/crash/errors.log.
    4. Hvis >30 min: drop bufferen (catastrofe — vi har større problemer).
    
    Desk ser:
    - streamClient.ts: normal reconnect (har allerede backoff).
    - Fejl vises lokalt som `DegradedState` chip i statusbar.
    - Notification: "Centralen er utilgængelig — nogle fejl spores ikke."
    """
```

Desk-appen har allerede `useOnline()` og `useConnection()` — de kan udvides til at vise degraded state i statusbar.

---

## 8. Test-strategi (uddybet)

### Per fase

| Fase | Test-type | Dækning |
|------|-----------|---------|
| 0 | Unit: classifier for alle 37 kinds | Hver kind → korrekt klassificering |
| 0 | Unit: healer registry | Alle healere registreres og matcher |
| 0 | Integration: `POST /internal/errors/report` → 202 | Happy path |
| 1 | Unit: hver `except` der er ændret → canonical report | Min. 1 test pr. hotspot |
| 1 | Integration: gate_execution fejl → error report i DB | Tilføj test-gate med kendt fejl |
| 2 | Unit: `useCanonicalError` hook | Mock reports → korrekt UI state |
| 2 | Integration: ChatView .catch → ErrorCard | Indsæt fejl i stream → ErrorCard vises |
| 2 | E2E: System health chip | Åben desk → chip viser 0 → inject error → chip opdateres |
| 3 | Unit: anomaly detection fra error patterns | 10 errors/min → anomali trigger |
| 3 | Integration: Centralen nede → desk degraded state | Stop central → desk viser chip |

## 8a. Performance-krav (error latency)

| Måling | Target | Målemetode |
|--------|--------|------------|
| Desk: error opdaget → ErrorCard synlig | < 500ms | `performance.now()` i hook |
| Desk: error sendt til backend → 202 modtaget | < 200ms | `fetch` timing |
| Backend: POST modtaget → Centralen klassificeret | < 100ms | server-side logging |
| Healer: opdaget → handling startet | < 1s | tick-cycle timing |
| Centralen-down nødfald: desk skifter til degraded state | < 2s | `useOnline()` timeout |
| SystemHealth chip opdatering efter nye errors | < 1s | subscription push |

**Ikke-fastlagte (skal valideres i fase 2):**
- Max error-buffer flush ved genforbindelse: < 5s for 100 errors
- ErrorCard render time ved 10 samtidige errors: < 200ms total

## 8b. User_action afvisning flow

Når en error med `recoverable: user_action` vises i desk, og brugeren afviser eller ignorerer:

```mermaid
flowchart TD
    A[ErrorCard vises: "Tillad adgang til workspace?"] --> B{Bruger svarer}
    B -->|Godkend| C[Healer kører: sæt trust]
    B -->|Afvis| D[Error eskalerer til permanent]
    B -->|Ignorer (30s timeout)| D
    D --> E[SystemHealth chip: 1 uløst]
    E --> F[Session kan fortsætte i degraded mode]
    F --> G{Ny handling kræver samme tilladelse?}
    G -->|Ja| H[ErrorCard vises igen med count: 2]
    G -->|Nej| I[Session fortsætter normalt]
    H --> J{Samme error gentaget 3x?}
    J -->|Ja| K[Bloker handlingen helt — vis "Kan ikke fortsætte uden tilladelse"]
    J -->|Nej| B
```

**Regler:**
1. En `user_action` error blokerer IKKE hele sessionen — kun den enkelte handling.
2. Brugeren kan altid vælge "Ignorér" → handlingen springes over, session fortsætter.
3. Hvis samme `kind`+`origin` afvises 3 gange indenfor 10 minutter, eskalerer den til `permanent` og handlingen blokeres.
4. Brugeren kan manuelt nulstille blokeringen via Settings → System Health → "Nulstil blokerede handlinger".
5. Ved `permanent` vises en forklarende tekst: "Handlingen blev blokeret efter 3 afvisninger. Nulstil i indstillinger for at prøve igen."

### Acceptance criteria (før fase kan betragtes som done)
- ✅ Alle nye routes har response model + status koder
- ✅ Alle nye hooks har tests
- ✅ Mindst én integrationstest per ny error-kind-sti
- ✅ Desk viser stadig brugbare fejlbeskeder (ikke kun koder)

### Konkrete test-filer (per fase)

| Fase | Test-fil | Fixtures |
|------|----------|----------|
| 0 | `core/services/tests/test_error_conductor.py` | `fixtures/errors/valid_report.json`, `fixtures/errors/invalid_kind.json`, `fixtures/errors/missing_field.json` |
| 0 | `core/services/tests/test_error_healers.py` | `fixtures/healers/heal_success.json`, `fixtures/healers/heal_retry.json`, `fixtures/healers/heal_escalate.json` |
| 0 | `apps/api/tests/test_internal_errors.py` | `fixtures/errors/rate_limited_response.json` |
| 1 | `core/services/tests/test_gate_errors.py` | Mock gate der altid fejler med kendt kind |
| 1 | `core/services/tests/test_visible_runs_errors.py` | Mock run der kaster specifikke exceptions |
| 2 | `apps/jarvis-desk/src/hooks/__tests__/useCanonicalError.test.ts` | Mock error-reports (5 forskellige kinds) |
| 2 | `apps/jarvis-desk/src/components/__tests__/ErrorCard.test.tsx` | Props: hver recoverable-type |
| 2 | `apps/jarvis-desk/src/components/__tests__/SystemHealth.test.tsx` | Props: 0, 3, 12 errors |
| 3 | `core/services/tests/test_central_error_drain.py` | 10 errors/min → anomali trigger |

---

## 9. Åbne spørgsmål (besluttet)

| Spørgsmål | Svar | Rationale |
|-----------|------|-----------|
| Skal desk kunne sende errors direkte til Centralen? | **Nej** — altid via backend proxy (`/api/internal/errors/report`) | Autentifikation, rate-limiting, audit |
| Skal error-loggen i desk være persistent på tværs af refresh? | **Ja** — i localStorage (max 50, FIFO) | Så Brugeren kan se hvad der skete selv efter page reload |
| Skal vi erstatte alle `catch { /* ignore */ }` på én gang? | **Nej** — faseopdelt, P0→P1→P2 | Risiko for regression for stor ved bulk-ændring |
| Er `known_benign` en severity eller en recoverable? | **Recoverable** — auto-healet, vises kun i System Health, ikke i chat | Skal ikke forstyrre flow, men skal kunne inspiceres |

---

## 10. Konklusion

Denne plan lukker alle 7 huller fra self-review. Spec'en er god. Audit er data. Implementeringsplanen er den konkrete vej.

**Næste step:** Bjørn prioriterer: Vil du have jeg starter Fase 0 (infrastruktur) nu, eller vente til desk-app design er færdigt i morgen?
