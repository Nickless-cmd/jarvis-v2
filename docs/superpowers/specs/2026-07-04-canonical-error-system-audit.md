# Canonical Error System — Audit af nuværende fallback-tekster og gates

**Dato:** 2026-07-04  
**Forfatter:** Jarvis  
**Scope:** jarvis-desk, apps/api, core/services  
**Metode:** statisk søgning efter `catch`, `except`, `fallback`, `ignore`, `noop`, `pass` + manuel gennemlæsning af de værste hotspots.

---

## 1. Executive summary

Systemet har i dag **mange lag af fejlslugning**. Desk-appen har ~70 steder hvor fejl catches og enten ignoreres, erstattes med en hardcoded dansk tekst, eller reduceres til en boolean (`setError(true)`). Backend og runtime har hundredvis af `except Exception: pass` blokke, ofte uden log eller propagation. Resultat: fejl forsvinder, brugeren får generiske beskeder, og udviklere kan ikke trace.

Den gode nyhed: der findes allerede et **stærkt fundament** i `apps/jarvis-desk/src/lib/streamClient.ts` med `StreamError` og `ErrorCategory`. Det kan udvides til det canonical system.

---

## 2. Prioritering

For at gøre implementeringen overskuelig prioriteres hotspots i tre kategorier:

| Prioritet | Kriterium | Antal | Eksempler |
|-----------|-----------|-------|-----------|
| **P0** | Synlig brugerpåvirkning — brugeren får forkert/ingen feedback | ~15 | `ChatView.tsx:88`, `Composer.tsx:186`, `streamClient.ts` |
| **P1** | Skjult fejlslugning — data går tabt uden spor | ~25 | `CodeView.tsx:70`, `settings/*`, `heartbeat_runtime.py` |
| **P2** | Intern robusthed — bør laves men påvirker ikke brugeren direkte | ~30+ | `catch { /* en lytter må ikke vælte de andre */ }` |

**Rækkefølge:** P0 først (desk), så P1 (backend/runtime), så P2 (intern konsolidering).

---

## 3. Desk-app: hotspots (prioriteret)

### 2.1 `views/ChatView.tsx`

| Linje | Mønster | Problem | Canonical kind |
|-------|---------|---------|----------------|
| 88 | `.catch(() => setCompactAt(0))` | Skjuler at context-info ikke kunne hentes | `network.timeout` / `central.nerve_timeout` |
| 105 | `.catch(() => { /* behold sidste kendte */ })` | Netværksfejl bliver tavs | `network.unreachable` |
| 122 | `.catch(() => { /* behold sidste — fallback til user-beskeder */ })` | Rail-fallback uden notice | `central.nerve_timeout` |
| 195 | `.catch(() => { /* behold sidste — ingen flicker */ })` | Stilhed ved pollingfejl | `network.timeout` |
| 317 | Kommentar: "fallback-tekst (backend afviser ellers med 400)" | Hardcoded tekst i message | `model.context_exceeded` |
| 400 | Kommentar: "fallback til user-beskederne så rail'en aldrig er tom" | Data-fallback uden fejlmarkering | `central.nerve_timeout` |

### 2.2 `views/CodeView.tsx`

| Linje | Mønster | Problem | Canonical kind |
|-------|---------|---------|----------------|
| 70 | `catch { return {} }` localStorage | Skjuler parse-fejl | `ui.render_error` |
| 108 | `.catch(() => { /* ignore */ })` | Workspace-info fejler tavst | `workspace.file_missing` / `network.timeout` |
| 133 | `catch { return { tokens: 0, toolCalls: 0, tools: [] } }` | Skjuler model-prefs fejl | `ui.render_error` |
| 138 | `catch { /* localStorage utilgængelig — ignorér */ }` | Storage-fejl ignoreres | `ui.render_error` |
| 253 | `.catch(() => setCompactAt(0))` | Context-info fejler tavst | `central.nerve_timeout` |
| 349 | `.catch(() => { /* behold sidste — ingen flicker */ })` | Git-status fejler tavst | `infra.git_unavailable` |
| 404 | `try { localStorage.setItem(...) } catch { /* ignore */ }` | Storage-fejl ignoreres | `ui.render_error` |
| 443 | `.catch(() => { if (!cancelled) setTrusted(false) })` | Trust-fald skjules | `trust.workspace_untrusted` |
| 453 | `catch { /* lad banneret blive */ }` | Fejl detaljer ikke logget | `trust.workspace_untrusted` |

### 2.3 `components/settings/*`

| Fil | Mønster | Problem | Canonical kind |
|-----|---------|---------|----------------|
| `AccountSection.tsx:51` | `Kunne ikke nå serveren.` | Hardcoded tekst | `network.unreachable` |
| `AccountSection.tsx:72` | `.catch(() => ({ state: undefined }))` | Pair-status fejler tavst | `network.timeout` |
| `AccountSection.tsx:90` | `Kunne ikke nå serveren.` | Hardcoded tekst | `network.unreachable` |
| `NotificationsSection.tsx:35` | `Kunne ikke hente` | Hardcoded tekst | `network.timeout` |
| `NotificationsSection.tsx:47` | `Kunne ikke gemme` | Hardcoded tekst | `network.timeout` |
| `JarvisSection.tsx:14` | `.catch(() => setError(true))` | Boolean fejl, ingen detail | `central.nerve_timeout` |
| `MemorySection.tsx:18` | `.catch(() => { if (alive) setError(true) })` | Boolean fejl | `central.nerve_timeout` |
| `WorkspaceSection.tsx:22` | `.catch(() => { if (alive) setError(true) })` | Boolean fejl | `central.nerve_timeout` |
| `KvoteSection.tsx:21` | `.catch(() => { if (alive) setError(true) })` | Boolean fejl | `central.nerve_timeout` |
| `PermissionsSection.tsx:18` | `.catch(() => { if (alive) setError(true) })` | Boolean fejl | `central.nerve_timeout` |
| `AppsSection.tsx:16` | `.catch(() => { if (alive) setError(true) })` | Boolean fejl | `central.nerve_timeout` |
| `McpSection.tsx:16` | `.catch(() => setError(true))` | Boolean fejl | `central.nerve_timeout` |
| `TotpSetup.tsx:28` | `catch { setConfigured(null) }` | Fejl sluges | `auth.forbidden` / `network.timeout` |
| `TotpSetup.tsx:38` | `.catch(() => setQrDataUrl(''))` | QR fejler tavst | `network.timeout` |
| `SprogSection.tsx:21` | `.catch(() => { if (alive) setLang('da') })` | Fejl skjules med default | `network.timeout` |

### 2.4 `components/code/*`

| Fil | Mønster | Problem | Canonical kind |
|-----|---------|---------|----------------|
| `EnvironmentPanel.tsx:72` | `Commit fejlede` | Hardcoded tekst | `tool.execution_failed` |
| `EnvironmentPanel.tsx:83` | `PR fejlede` | Hardcoded tekst | `tool.execution_failed` |
| `EnvironmentPanel.tsx:99` | `.catch(() => { if (!cancelled) setGit(null) })` | Git-info fejler tavst | `infra.git_unavailable` |
| `CentralPanel.tsx:30` | `.catch((e) => { if (403) setDenied(true) })` | Kun 403 håndteres | `auth.forbidden` / `central.nerve_timeout` |
| `CentralPanel.tsx:54` | `.catch(() => undefined)` | Nerve-detail fejler tavst | `central.nerve_timeout` |
| `CentralPanel.tsx:59` | `.catch(() => undefined)` | Toggle fejler tavst | `central.nerve_timeout` |
| `OperatorPanel.tsx:16-17` | `catch { /* ignore */ }` x2 | localStorage fejl | `ui.render_error` |

### 2.5 `components/shell/Composer.tsx`

| Linje | Mønster | Problem | Canonical kind |
|-------|---------|---------|----------------|
| 186 | `_deepseekFallback` | Model-specifik hack | `provider.unavailable` + lane switch |

### 2.6 `components/cowork/*`

| Fil | Mønster | Problem | Canonical kind |
|-----|---------|---------|----------------|
| `JarvisMind.tsx:189` | `FALLBACK_TABS` | Data-fallback uden fejlmarkering | `central.nerve_timeout` |
| `MissionControl.tsx:181` | `catch { ... }` | Run-detail parse fejl | `ui.render_error` |
| `RunDetail.tsx:27` | `.catch(() => { if (alive) setDetail(null) })` | Detail fejler tavst | `central.nerve_timeout` |

### 2.7 `lib/*`

| Fil | Mønster | Problem | Canonical kind |
|-----|---------|---------|----------------|
| `api.ts:107` | `.catch(() => '')` | Response body læses ikke ved fejl | `server.error` |
| `api.ts:503` | `catch { onError?.(); return }` | Central feed fejler tavst | `central.nerve_timeout` |
| `api.ts:518` | `catch { /* skip */ }` | Malformed JSON droppes | `protocol.malformed` |
| `api.ts:559` | `catch { onDone(); return }` | SSE fejler tavst | `ui.stream_disconnect` |
| `api.ts:578` | `catch { /* skip malformet */ }` | Malformed SSE droppes | `protocol.malformed` |
| `api.ts:762` | `catch { /* presence er best-effort */ }` | Presence ping fejler tavst | `network.timeout` |
| `api.ts:785` | `catch { /* best-effort */ }` | Notification ack fejler tavst | `network.timeout` |
| `streamClient.ts` | `StreamError.userMessage()` | Godt fundament | udvides til canonical |
| `centralStream.ts:25` | `catch { /* en lytter må ikke vælte de andre */ }` | Subscriber fejl sluges | `ui.render_error` |
| `centralStream.ts:29` | `catch { /* noop */ }` | Error-subscriber fejl sluges | `ui.render_error` |
| `themeStore.ts:10,19` | `catch { ... }` | localStorage fejl | `ui.render_error` |
| `composerPrefs.ts:10-11` | `catch { /* ignore */ }` x2 | localStorage fejl | `ui.render_error` |
| `postConnect.ts:10,19` | `catch { ... }` | Storage / parse fejl | `ui.render_error` |
| `panelStore.ts:9,17` | `catch { ... }` | localStorage fejl | `ui.render_error` |
| `deskLocation.ts` | `catch { ... }` x4 | localStorage / parse fejl | `ui.render_error` |
| `sanitize.ts:16,32` | `catch { ... }` | Sanitize fejl | `ui.render_error` |
| `artifacts.ts:36` | `catch { ... }` | Artifact parse fejl | `ui.render_error` |
| `coworkZone.ts:59` | `catch { /* en lytter må ikke vælte de andre */ }` | Zone listener fejl | `ui.render_error` |
| `fileTreeHighlight.ts:16` | `catch { /* en lytter må ikke vælte de andre */ }` | Listener fejl | `ui.render_error` |

### 2.8 `hooks/*`

| Fil | Mønster | Problem | Canonical kind |
|-----|---------|---------|----------------|
| `useMissionControl.ts:41` | `.catch(() => { /* overblik er blødt */ })` | MC overview fejler tavst | `central.nerve_timeout` |
| `useMissionControl.ts:60-61` | `catch { /* polling-fallback dækker */ }` | WS fejl skjules | `ui.stream_disconnect` |
| `useCoworkData.ts:60-61` | `ws.onerror = () => { /* polling-fallback dækker */ }` | WS fejl skjules | `ui.stream_disconnect` |
| `useConnection.ts:29` | `catch { /* behold rå */ }` | URL parse fejl | `ui.render_error` |
| `useDictation.ts:60,69` | `catch { ... }` | Dictation fejl | `ui.render_error` |
| `usePollWhenVisible.ts:38` | `catch (e) { ... }` | Polling fejl | `network.timeout` |

---

## 4. Backend / runtime: hotspots

### 3.1 `apps/api/jarvis_api/app.py`

Lifespan-funktionen starter ~30 services. Hver enkelt er pakket ind i `try/except Exception: pass` eller `logger.warning`. Hvis en kritisk service fejler ved opstart, får vi ingen synlig fejl — bare en log-linje. Eksempler: linje 157, 168, 176, 191, 220, 226, 232, 240, 246, 252, 258, 264, 270, 281, 289, 295, 301, 307, 314, 326, 331, 337, 345, 352, 372, 379, 394, 398, 404, 409, 414, 419, 424, 429, 434, 439, 444, 449, 462, 468, 540.

### 3.2 `apps/api/jarvis_api/routes/central.py` (estimeret)

Central-diagnostics, realtime, nerve-detail, mind og andre routes har ifølge søgning mange `except Exception: pass`. Fejl fra Centralen forsvinder før de når desk.

### 3.3 `apps/api/jarvis_api/routes/chat_stream_v2.py`

Override/guard logik har `except Exception: pass` mønstre. Stream-fejl kan blive slugt i stedet for at blive sendt som SSE error events.

### 3.4 `apps/api/jarvis_api/routes/system_health.py`

`except Exception: pass` omkring git-kald. Hvis git ikke er tilgængelig, får vi ingen data og ingen fejl.

### 3.5 `core/services/heartbeat_runtime.py`

Ifølge søgning har filen mange `except Exception as _exc:` uden re-raise. Daemon-livelihood kan fejle uden at blive synlig.

### 3.6 `core/services/pfsense_syslog.py`

Syslogd-død håndteres, men fejlen propagérer ikke canonical. Den ender som en incident, men uden `kind` og `recoverable`.

### 3.7 `core/services/network_health.py`

Netværksfejl logges, men ikke som canonical errors. Der er ingen `network.timeout` / `provider.latency_spike` kind.

### 3.8 `core/services/gate_execution.py`

Dette er faktisk et **positivt eksempel**: den samler tidligere `except: pass` fail-retninger og routet dem gennem Centralen. Men den bruger stadig `except Exception: pass` internt (linje 75, 103, 108, 118, 135, 189, 192, 204) — den skal opgraderes til at rapportere canonical errors.

---

## 4. Mønstre vi skal udrydde

1. **`catch { /* ignore */ }` / `except Exception: pass`** — altid logge eller rapportere.
2. **`.catch(() => setError(true))`** — boolean fejl uden detail. Skal blive til canonical error card.
3. **Hardcoded danske fejlbeskeder** — `Kunne ikke nå serveren.`, `Kunne ikke hente`, `Commit fejlede`.
4. **Data-fallbacks uden notice** — `FALLBACK_TABS`, `return {}`, `setCompactAt(0)`.
5. **Model-specifik hacks** — `_deepseekFallback`.
6. **Tavse reconnects** — `polling-fallback dækker` uden at brugeren ved det.

---

## 5. Mønstre vi skal bevare / udvide

1. **`StreamError` i `streamClient.ts`** — allerede typed errors med `category`, `retryable`, `statusCode`. Udvides med `kind` og `origin`.
2. **Gate execution** — allerede central routing. Opgraderes til canonical error format.
3. **Central anomaly detector** — fanger uhåndterede exceptions. Kan beriges med canonical kinds.
4. **Incident-systemet** — allerede i Centralen. Kan bruges som eskaleringsmål.

---

## 6. Anbefalet implementeringsrækkefølge

1. **Backend:** `core/services/central_error_conductor.py` + `POST /central/errors`.
2. **Backend:** Erstat de værste `except Exception: pass` i `app.py` lifespan og `gate_execution.py`.
3. **Desk:** Udvid `StreamError` til canonical format; lav `useCanonicalError()` hook.
4. **Desk:** Erstat hardcoded fejlbeskeder i settings + code + chat med canonical cards.
5. **UI:** Global system health-chip + transparency-log.
6. **Iterativt:** Konverter resten af catch-blokke efterhånden.

---

## 7. Konklusion

Der er **meget at gøre**, men det er ikke uoverkommeligt. De værste 20-30 steder står for størstedelen af den dårlige brugeroplevelse. Hvis vi starter med dem, plus backendens `except: pass` ved opstart, får vi hurtigt en markant mere troværdig og tracebar platform.
