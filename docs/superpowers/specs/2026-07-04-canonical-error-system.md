# Canonical Error System — hele stakken, én sandhed

**Dato:** 2026-07-04  
**Forfatter:** Jarvis (spec + audit) / Bjørn (retning)  
**Scope:** jarvis-desk, API/runtime, Centralen, model-provider, host/infra.  
**Princip:** Centralen er dirigent — ikke afsender af alle fejl, men klassificerer, healing-handler, eskalerer og propagérer én canonical repræsentation tilbage til UI.

---

## 1. Baggrund: hvorfor nu?

Systemet har i dag mange "teater-fallbacks": tekster og stilheder der *lyder* som forklaringer, men som skjuler at noget gik galt, og at systemet ikke altid ved præcis hvad.

Eksempler fra audit:

- Desk: `.catch(() => { /* ignore */ })`, `.catch(() => setError(true))`, `Kunne ikke nå serveren.`, `Kunne ikke hente`, `Commit fejlede`.
- Backend: `except Exception: pass` i central diagnostics, realtime, nerve-detail, mind, chat-stream override/guard.
- Runtime: `except Exception: pass` i `heartbeat_runtime.py` (tusindvis af steder), `pfsense_syslog.py`, `network_health.py`.

Konsekvens: når noget går galt, kan vi ikke trace fra UI → Centralen → backend → kilde. Brugeren får en generisk besked eller ingenting. Udvikleren skal gætte.

---

## 2. Mål

1. **Én canonical fejltype** for hele stakken — ikke 40 lokale tekster.
2. **Self-healing** hvor det er muligt — med tællede forsøg og cooldown.
3. **Transparent propagation** — UI spørger Centralen "hvad skete der?" og viser svaret.
4. **Traceability** — `kind` + `origin` (fil:linje/funktion) gør det muligt at gå fra desk til kilde.
5. **Ingen stilhed** — enhver fejl enten heales, eskaleres eller vises. Aldrig `pass` uden log/flag.

---

## 3. Canonical error-repræsentation

### 3.1 Type-hierarki

```ts
// TypeScript (desk) / Python (runtime) — samme navne, samme betydning.
type ErrorKind =
  // Transport / netværk
  | 'network.timeout'
  | 'network.unreachable'
  | 'network.dns_failed'
  | 'network.tls_failed'
  // Auth / tillid
  | 'auth.token_expired'
  | 'auth.forbidden'
  | 'trust.workspace_untrusted'
  // Runtime / Centralen
  | 'central.daemon_dead'
  | 'central.nerve_timeout'
  | 'central.circuit_open'
  | 'self.cutoff'
  | 'self.loop_lag'
  // Model / inference
  | 'model.refusal'
  | 'model.rate_limited'
  | 'model.context_exceeded'
  | 'provider.unavailable'
  | 'provider.latency_spike'
  // Agent / tool
  | 'tool.permission_denied'
  | 'tool.execution_failed'
  | 'tool.timeout'
  | 'workspace.file_missing'
  // Host / infra
  | 'infra.host_down'
  | 'infra.syslogd_dead'
  | 'infra.disk_pressure'
  | 'infra.cpu_pressure'
  // Desk / UI
  | 'ui.stream_disconnect'
  | 'ui.render_error'
  | 'ui.unknown'
```

### 3.2 Felter

```ts
interface CanonicalError {
  id: string              // UUID — følger fejlen på tværs af stakken
  kind: ErrorKind
  severity: 'info' | 'warning' | 'error' | 'critical'
  recoverable: 'auto' | 'retry' | 'user_action' | 'degraded' | 'none'
  scope: 'global' | 'session' | 'run' | 'tool' | 'component'
  origin: string           // fil:linje eller modul-funktion
  message: string          // kort, dansk, sikker at vise
  detail?: string          // teknisk, kun i "Se detaljer"
  context: Record<string, unknown>
  createdAt: string        // ISO
  runId?: string
  sessionId?: string
  toolCallId?: string
}
```

---

## 4. Centralen som dirigent

### 4.1 Fejl-bus

Alle lag sender fejl til Centralen via én endpoint:

```
POST /central/errors
{
  "kind": "network.timeout",
  "severity": "warning",
  "recoverable": "retry",
  "scope": "run",
  "origin": "apps/api/jarvis_api/routes/chat_stream_v2.py:run_stream",
  "message": "Forbindelsen til model-provideren tog for lang tid.",
  "context": { "provider": "ollama", "model": "glm-5.2:cloud", "attempt": 2 },
  "runId": "...",
  "sessionId": "..."
}
```

### 4.2 Klassifikation

Centralen modtager, normaliserer `kind`, og afgør `recoverable` hvis afsender ikke har sat det. Den kender regler som:

- `network.timeout` → `retry`
- `auth.token_expired` → `user_action`
- `central.daemon_dead` → `auto`
- `model.context_exceeded` → `degraded`

### 4.3 Self-healing matrix

| Kind | Handling | Max forsøg | Cooldown | Eskalering |
|------|----------|------------|----------|------------|
| `central.daemon_dead` | restart daemon | 3 | 10s | `user_action` |
| `network.timeout` | backoff retry | 5 | 250ms→8s | `degraded` |
| `auth.token_expired` | refresh token | 1 | - | `user_action` |
| `ui.stream_disconnect` | reconnect + resume | 5 | 1s→30s | `user_action` |
| `infra.syslogd_dead` | restart syslogd | 3 | 60s | `user_action` |
| `provider.unavailable` | switch lane/model | 2 | 5s | `degraded` |
| `self.cutoff` | log + diagnose | 0 | - | `user_action` |

Healing-resultat rapporteres tilbage: `healed`, `retrying`, `failed`, `escalated`.

### 4.4 Eskalering

Hvis auto-healing fejler max gange, eller `recoverable` er `user_action` fra start, oprettes en **incident** i Centralen. Desk viser et kort med én CTA.

---

## 5. Propagation til desk

### 5.1 Ingen lokale fallback-tekster

Desk-appen må ikke selv opfinde:

- `Kunne ikke nå serveren.`
- `Kunne ikke hente.`
- `Commit fejlede.`
- `/* ignore */`

I stedet kalder den Centralen og viser det canonical svar.

### 5.2 To visningsformer

**A) Global system health-chip**  
Placering: sidebar-fod eller header.  
Tilstande: `ok` / `degraded` / `attention`.  
Klik åbner **transparency-log**: tidslinje over fejl, handlinger, udfald.

**B) Inline error cards**  
Når et run/tool/model fejler, vises et kort i transcript med:

- Titel (fra `kind`)
- Hvad der skete (1 sætning)
- Hvad systemet gjorde (`Jeg prøvede igen`, `Jeg kører i nedsat tilstand`, `Kræver din godkendelse`)
- Én CTA: `Prøv igen`, `Godkend`, `Se detaljer`, `Ignorér`

### 5.3 Eksempel: tool timeout

```
[ToolCard]
Titel: Værktøj tog for lang tid
Tekst:  `read_file` på `/etc/nginx/nginx.conf` nåede ikke at svare inden for 30s.
System: Jeg prøvede igen én gang — det lykkedes ikke.
CTA:    [Prøv igen] [Se detaljer]
```

---

## 6. Audit: hvad skal erstattes

### 6.1 Desk-app (udvalg)

| Fil | Mønster | I dag | Skal blive |
|-----|---------|-------|------------|
| `views/ChatView.tsx:88` | `.catch(() => setCompactAt(0))` | skjuler fejl | send `central.errors` + vis degraded |
| `views/ChatView.tsx:105` | `.catch(() => { /* behold sidste */ })` | stilhed | log `network.timeout` + vis chip |
| `views/ChatView.tsx:122` | `.catch(() => { /* fallback til user-beskeder */ })` | stilhed | log + vis fallback-rail med notice |
| `views/ChatView.tsx:317` | fallback-tekst i message | hardcoded | canonical `model.context_exceeded` |
| `views/CodeView.tsx:70` | `catch { return {} }` localStorage | skjuler | `ui.render_error` med degraded |
| `views/CodeView.tsx:443` | `.catch(() => setTrusted(false))` | skjult trust-fald | `trust.workspace_untrusted` kort |
| `components/settings/AccountSection.tsx:51` | `Kunne ikke nå serveren.` | hardcoded | `network.unreachable` canonical |
| `components/settings/NotificationsSection.tsx:35` | `Kunne ikke hente` | hardcoded | `network.timeout` canonical |
| `components/code/EnvironmentPanel.tsx:72` | `Commit fejlede` | hardcoded | `tool.execution_failed` canonical |
| `components/shell/Composer.tsx:186` | `_deepseekFallback` | model-specifik hack | `provider.unavailable` + switch lane |
| `components/cowork/JarvisMind.tsx:189` | `FALLBACK_TABS` | data-fallback | `central.nerve_timeout` + retry |
| `lib/streamClient.ts` | `StreamError.userMessage()` | godt fundament | udvides til canonical `kind` |

### 6.2 Backend / runtime (udvalg)

| Fil | Mønster | I dag | Skal blive |
|-----|---------|-------|------------|
| `apps/api/jarvis_api/routes/central.py` | `except Exception: pass` x 10+ | fejl forsvinder | send til Centralen, returnér partial |
| `apps/api/jarvis_api/routes/chat_stream_v2.py` | `except Exception: pass` override/guard | fejl forsvinder | log + fortsæt med notice |
| `apps/api/jarvis_api/routes/system_health.py` | `except Exception: pass` git | fejl forsvinder | `infra.git_unavailable` |
| `core/services/heartbeat_runtime.py` | `except Exception: pass` (hundredvis) | fejl sluges | central observe + log, aldrig pass |
| `core/services/pfsense_syslog.py` | `except Exception: continue/pass` | støj sluges | `infra.syslogd_dead` hvis bind fejler |
| `core/services/network_health.py` | `except Exception: pass` | fejl forsvinder | observe med `unknown` hvis alt fejler |
| `core/services/daemon_manager.py` | `except Exception: pass` | daemon dør stille | `central.daemon_dead` + auto-restart |

### 6.3 Kritisk princip

> **Ingen `except Exception: pass` uden en Centralen-observe eller en begrundet `info`-log.**  
> Hvis vi virkelig mener en fejl er støj, skal vi eksplicit markere den som `recoverable: none` og `severity: info`, ikke bare sluge den.

---

## 7. Implementeringsfaser

### Fase 1: Foundation (1 dag)

1. Definér `CanonicalError` schema i både Python og TypeScript.
2. Opret `POST /central/errors` endpoint.
3. Opret `core/services/canonical_errors.py` med klassifikation og healing-matrix.
4. Erstat de værste 10 `except Exception: pass` i backend med observe-kald.

### Fase 2: Desk integration (1 dag)

1. Udvid `StreamError` til at bære `kind` og `origin`.
2. Byg global system-health chip + transparency-log.
3. Byg inline `ErrorCard` komponent.
4. Erstat de værste desk fallback-tekster med canonical visning.

### Fase 3: Self-healing (1-2 dage)

1. Implementér healing actions: daemon restart, backoff retry, lane switch, syslogd restart.
2. Tæl forsøg og eskaler ved max.
3. Test med simulerede fejl.

### Fase 4: Læring

1. Log healing-udfald.
2. Lad Centralen justere `recoverable` og `severity` baseret på historik.
3. Eksempel: hvis `infra.syslogd_dead` altid heales efter genstart, sænk severity.

---

## 8. Test-strategi

Canonical error-systemet skal kunne testes uden at køre hele stacken.

### 8.1 Unit tests
- **CanonicalError factory:** Givet `kind`, `origin`, `context` → returnér korrekt objekt med `severity` og `recoverable` fra matrix.
- **Klassifikation:** Givet rå input → map til korrekt `kind`. Test at ukendt kind → `ui.unknown`.
- **Healing matrix:** Hver `kind` har en handling i matrix. Test at matrix er komplet (alle kinds har en definition).
- **Eskalering:** Når max attempts nås → `recoverable` eskaleres korrekt.

### 8.2 Integration tests
- **POST /central/errors:** Send en CanonicalError → få 202 + `id`. GET /central/errors/:id returnér korrekt objekt.
- **SSE stream:** Abonner på /central/errors/stream → se nye errors.
- **Healing action:** Mock en daemon-død, kør healing → verificér at daemon genstartes. Test at 3. forsøg eskalerer.

### 8.3 Edge cases
- **Rate-limiting:** Hvis error-conductoren modtager >100 errors/min fra samme `origin`, skal den midlertidigt nedprioritere (severity: debug, ingen healing).
- **Rekursive errors:** Hvis selve error-systemet fejler (POST /central/errors fejler), skal den ikke gå i loop. Fail-open: log til stdout, fortsæt.
- **Malformed input:** Hvis en error ankommer uden `kind`, sæt `kind: ui.unknown`. Hvis uden `origin`, forsøg at udlede fra caller stack.

### 8.4 Verifikation af audit
Efter migration: kør script der scanner alle `.catch` / `except` blokke og verificerer at de enten rapporterer canonical error eller har en explicit `// canonical: none` kommentar (til ægte støj).

---

## 9. Rate-limiting & circuit breaker

Error-conductoren selv skal have beskyttelse:

1. **Pr. origin:** Maks 100 errors/min pr. `origin` (fil+funktion). Overskridelse → nedprioriteres til `severity: debug`, ingen healing.
2. **Pr. kind:** Maks 10 healer-forsøg/min pr. `kind`. Overskridelse → circuit breaker åbner i 30s.
3. **Global:** Maks 1000 errors/min total. Overskridelse → log + summarér ("120 errors opstod — viser de første 5").
4. **Fail-open:** Hvis error-conductoren selv kaster en exception, logges den til stdout og systemet fortsætter uden canonical error-handling. Aldrig cascade failure.

---

## 10. Relation til desk-app design

Dette system er en forudsætning for at desk-appen kan føles som en **agent-native arbejdsplatform** snarere end en chatbot. Claude/Codex/Devin har alle en aktivitetsoversigt inklusive fejl. Vores tool-kort, approval-kort og liveness-indikatorer er allerede på vej — canonical error-systemet giver dem et fælles sprog.

Når vi i morgen vælger farve- og identitetsretning (agent-native / subtil HUD / hybrid), skal denne fejl-transparens være en af de bærende søjler i designet.

---

## 11. Åbne spørgsmål (med anbefalede svar)

1. **Skal `CanonicalError` persistes i DB eller kun leve i Centralens hukommelse?**  
   *Anbefaling:* I memory + log (struktureret log til stdout, scrapes af Centralen). Persistens i DB tilføjes senere hvis der er behov for historisk analyse. De første 1000 fejl per session er nok til at trace.

2. **Skal brugeren kunne "ignorér" en fejl permanent, eller skal den genopstå ved næste occurrence?**  
   *Anbefaling:* Genopstå ved næste occurrence. Permanent ignore er en settings-funktion vi kan tilføje senere; for nu skal brugeren altid kunne se om et problem vender tilbage.

3. **Skal healing altid køre autonomt, eller skal nogle handlinger kræve godkendelse (fx lane-switch, daemon-restart)?**  
   *Anbefaling:* Autonomt for `recoverable: auto` med cooldown. `SECURITY`-klassede handlinger (fx daemon-restart med root-adgang) kræver godkendelse via gate_kernel. Lane-switch er auto hvis samme lane-familie, kræver godkendelse hvis cross-family.

4. **Hvor meget af `heartbeat_runtime.py`'s `except Exception: pass` skal vi røre ad gangen?**  
   *Anbefaling:* Top 10 værste spots først (dem med synlig brugerpåvirkning: cutoff, daemon-død, stream-fejl). Resten i en separat cleanup-sprint. Risikoen for støj er reel — introducér med `severity: debug` og hæv når mønstret er godkendt.

---

## 12. Konklusion

Systemet har brug for ét canonical error-system der dækker hele stakken, med Centralen som dirigent og self-healing hvor det er muligt. Det fjerner teater-fallbacks, gør fejl traceable, og giver desk-appen den transparens en agent-native platform kræver.
