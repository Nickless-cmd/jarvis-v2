# Central CLI Client — Self-Review (2. gennemkørsel)

**Dato:** 5. juli 2026  
**Reviewer:** Jarvis (selv)  
**Spec under review:** `2026-07-05-central-cli-client-design.md`  
**Metode:** Fuld gennemlæsning + krydstjek mod backend-kode (auth, workers, central_routes) + kritisk analyse  
**Status:** Efter 2. gennemkørsel — klar til revidering

---

## Samlet vurdering

Spec'en er et **solidt udkast** med komplet endpoint-oversigt og godt TUI-layout. Men den har **2 rigtige kritiske huller** (C1 var delvist forkert i 1. runde), **5 high-severity issues**, og en række medium mangler. Efter revidering af C1-C3 + H1-H5 er den byggeklar.

---

## 🔴 Kritiske fund (blokkerer implementering)

### C1: Auth flow — REVURDERET (1. runde var delvist forkert)

**Hvad 1. runde sagde:** "Clienten kalder `/api/auth/issue` som er owner-only — cirkulær afhængighed."

**Hvad koden faktisk gør:** Der er **to forskellige `_require_owner()`-implementationer**:

1. **`central.py` linje 36:** `uid = current_user_id(); if uid is None: return` — **ubundet = owner**. Central-routes virker uden auth på localhost.

2. **`jarvisx.py` linje 1120:** `user_id = snap.get("user_id") or ""; if not user_id: raise 403` — **ubundet = AFVIST**. `/api/auth/issue` kræver en bundet user identity.

**Den reelle auth-kæde:**
- `auth_required()` default = `False` → API'en kræver ikke bearer tokens
- Men `/api/auth/issue` kalder `_require_owner()` som kræver `X-JarvisX-User` header med en owner Discord ID
- Clienten kan altså minte et token ved at sende `X-JarvisX-User: <bjorn_discord_id>` header — **uden allerede at have et bearer token**

**Konklusion:** C1 er **ikke** en cirkulær afhængighed. Der er en fungerende bootstrap-sti:
1. Clienten sender `X-JarvisX-User: <owner_discord_id>` → kalder `/api/auth/issue` → får token
2. Efterfølgende kald bruger `Authorization: Bearer <token>`

**Men spec'en er stadig uklar på:**
- Hvordan clienten kender owner's Discord ID (skal hardcodes? config? prompt?)
- At der er to auth-mekanismer (header vs bearer) og hvornår hver bruges
- At `X-JarvisX-User` header kun virker når `auth_required()=False` (localhost)
- Hvad der sker når `auth_required()=True` — så virker header-auth ikke længere

**Anbefaling:** Beskriv to auth-tilstande eksplicit:
- **Local mode** (`auth_required=False`): `X-JarvisX-User` header til bootstrap, derefter bearer token
- **Remote mode** (`auth_required=True`): Kræver pre-minted token (via `central token mint` kommando på serveren, overføres out-of-band)
- Hardcode owner Discord ID i config-wizard med default

### C2: Single-worker + SSE — BEKRÆFTET

**Bekræftet i kode:** `systemd` service kører `--workers 1 --timeout-keep-alive 120`. SSE-stream deler event loop med alle REST-kald.

**Kode-kommentar i app.py linje 519:** *"sync DB-UPSERT må ALDRIG blokere event-loopet med --workers 1 (blocking-freeze-mønstret)"* — teamet er allerede opmærksom på risikoen.

**SSE-streamen i `central_realtime.py`** bruger `asyncio.to_thread` for DB-læsninger, men selve stream-generator'en er en async coroutine der holder event-loopet.

**Risiko:** Med SSE åben + REST-kald samtidig kan REST-kald forsinkes (ikke blokeres helt, men latency stiger). Med `--timeout-keep-alive 120` kan SSE-connection også dræbes af uvicorn.

**Anbefaling:** 
- **Default til polling** (hvert 2-3s) frem for SSE i v1
- SSE som opt-in via `--sse` flag eller config
- Når SSE bruges: vis latency i status bar så Bjørn kan se hvis det forringes
- Dokumenter at SSE + samtidig REST kan give forsinkelser på single-worker

### C3: Pipe-feature — uændret (1. runde var korrekt)

`incidents | grep network` inde i en Textual TUI kræver intern pipe-parser. Ikke en one-liner.

**Anbefaling:** Fjern pipes fra v1. Tilføj `--filter` flag i stedet: `incidents --filter network`. Meget simplere, dækker 90% af use-casen. Pipes kan tilføjes i v2.

---

## 🟠 High-severity fund

### H1: Local mode vs HTTP mode

**Bekræftet:** Clienten kører på samme maskine som API'en (Bjørn koder på serveren). Kan importere `core.services.central_query` direkte.

**Anbefaling:** Tilføj **local mode** som default:
- Local: `python -m central_cli` → importerer central_query direkte, ingen HTTP
- Remote: `central --remote http://10.0.0.39:8080` → HTTP mode med token
- Auto-detection: tjek om `127.0.0.1:8080` svarer → local mode

Local mode eliminerer C2 (single-worker) helt for det primære use-case.

### H2: Relation til central_terminal.py

**Bekræftet:** `central_terminal.py` eksisterer med 16 kommandoer. Spec'en nævner den ikke.

**Anbefaling:** CLI'en **genbruger central_terminal's command-parser** som backend. central_terminal.py bliver parser-laget, CLI'en bliver TUI-laget oven på. Ingen duplikeret logik.

### H3: Logging

**Anbefaling:** 
- `~/.jarvis-v2/logs/central_cli.log` med rotation (5 MB, 3 backups)
- Audit-log for write-kommandoer (toggle, resolve, depromote)
- `--verbose` for debug-level, ellers INFO
- Token **aldrig** i logs (redacted)

### H4: Graceful shutdown

**Anbefaling:**
- `Ctrl+C` / `SIGINT` → luk SSE → vent in-flight requests (max 3s) → gem command history → exit
- `SIGTERM` → force quit (ingen ventetid)
- `SIGHUP` → reload config (ikke v1, men dokumenter som fremtidig)

### H5: Versionshåndtering

**Anbefaling:**
- Clienten kalder `/central/realtime` ved startup (allerede eksisterende endpoint)
- Viser client-version + API connection-status i status bar
- Ukendte felter i JSON-responses ignoreres graceful (forward-compatible)
- Ingen separat `/api/version` endpoint nødvendigt — realtime-snapshottet bekræfter at API'en lever

---

## 🟡 Medium-severity fund (uændret fra 1. runde)

| ID | Issue | Løsning |
|---|---|---|
| M1 | Keyboard shortcuts mangler | Tilføj: Ctrl+L (clear), Ctrl+R (refresh), ↑/↓ (history), F1 (help), Esc (cancel) |
| M2 | Ingen command history | `~/.jarvis-v2/state/central_cli_history`, max 500 kommandoer, ↑/↓ navigation |
| M3 | `watch` ikke specificeret | `watch status` = overskriv output-panel hvert 5s, stop med Esc, blokerer ikke andre kommandoer |
| M4 | Accessibility | Tilføj ikoner ved siden af farver (●/○/▲/▼), ikke kun farve-kodning |
| M5 | Config format | Skift til JSON (`central_cli.json`) for konsistens med `runtime.json` |
| M6 | Dependency versions | Textual>=4.0, Rich>=13.0, httpx>=0.27, PyJWT>=2.8 |
| M7 | Boot ikke skippable | `--no-boot` flag, `--script` mode (ingen TUI, kun output) |
| M8 | Token rotation | Advarsel 7 dage før udløb, auto-refresh via refresh-token |

---

## 🟢 Low-severity fund (uændret fra 1. runde)

| ID | Issue | Løsning |
|---|---|---|
| L1 | Fremtidige udvidelser for vage | OK for "future" sektion — men flyt command history + keyboard shortcuts til v1 |
| L2 | Multi-line/bred output | Horisontal scroll i Textual, wrapping som fallback |
| L3 | Terminal emulator kompatibilitet | Dokumenter krav: 256-color minimum, truecolor anbefalet. tmux/SSH OK |
| L4 | Test mocking | Tilføj mock HTTP-server (httpx mock) + SSE fixtures |

---

## Kontradiktioner i spec'en

### K1: "Token fra samme sted som jarvis-desk" — DELVIST RESOLVERET
Jarvis-desk bruger `X-JarvisX-User` header, ikke bearer tokens. Men begge er gyldige auth-mekanismer. Spec'en skal beskrive begge og hvornår hver bruges. **Løst via C1-revision.**

### K2: "SSE stream: forbundet" i boot vs single-worker — BEKRÆFTET
Boot-sekvensen viser SSE som problemfrit. Med `--workers 1` er der reel risiko. **Løst via C2-revision (default polling).**

### K3: "Ikke en erstatning for jarvis-desk" men fjerner streaming-load — UAFKLARET
Hvis streaming-loaden flytter til CLI'en, deaktiveres jarvis-desk's Central-panel? Eller kører begge? 

**Anbefaling:** Begge kan køre samtidig. SSE-stream er per-klient. Jarvis-desk's panel kan sættes til "low-frequency polling" (hver 10s) mens CLI'en har realtid. Det er en config-ændring i jarvis-desk, ikke i CLI'en.

---

## Hvad spec'en gør godt

- **Endpoint-oversigten er komplet og korrekt** — krydstjekket mod kode, alle endpoints findes
- **TUI-layoutet er praktisk** — 3-panel split giver mening for et terminal-vindue
- **Fejl-kategorierne er reelle** — de 5 kategorier dækker de faktiske fejl-tilstande
- **Edge cases er en god start** — API nede, token udløbet, stor output
- **Implementationsfaserne er realistiske** — 4 faser over 4-6 dage
- **J.A.R.V.I.S æstetikken er konkret** — farvekoder, boot-sekvens, status bar
- **Kommando-oversigten er omfattende** — dækker både core og udvidede kommandoer

---

## Nye fund fra 2. gennemkørsel (kode-verificerede)

### N1: To `_require_owner()` implementationer med forskellig adfærd
- `central.py`: ubundet = owner (tillader ubundet adgang)
- `jarvisx.py`: ubundet = afvist (kræver bundet identity)
- **Konsekvens:** Central-routes virker uden auth på localhost, men `/api/auth/issue` kræver `X-JarvisX-User` header. Spec'en skal dokumentere denne forskel.

### N2: `--timeout-keep-alive 120` kan dræbe SSE
Uvicorn dræber keep-alive connections efter 120s. SSE-streamen kan blive afbrudt hvert 2. minut. Auto-reconnect (som spec'en beskriver) håndterer det, men det er værd at dokumentere.

### N3: `auth_required()` kan slås til via environment
`JARVISX_AUTH_REQUIRED=1` eller `runtime.json["jarvisx_auth_required"]`. Hvis Bjørn slår det til, ændres auth-kravene. Clienten skal håndtere begge tilstande.

---

## Endelig konklusion & byggeklar-tjek

| Kategori | Status | Handling |
|---|---|---|
| C1 (auth flow) | 🟡 Delvist løst — kode-sti findes, spec uklar | Revider spec med local/remote auth-tilstande |
| C2 (single-worker + SSE) | 🔴 Ikke løst | Default til polling, SSE som opt-in |
| C3 (pipes) | 🔴 Ikke løst | Fjern pipes fra v1, brug `--filter` |
| H1 (local mode) | 🔴 Mangler | Tilføj local mode som default |
| H2 (central_terminal) | 🔴 Mangler | Beskriv genbrug af parser |
| H3-H5 | 🔴 Mangler | Tilføj logging, shutdown, versioning |
| Medium (M1-M8) | 🟡 Kan løses under implementering | Noter som known-gaps |
| Endpoint-oversigt | 🟢 Komplet og korrekt | — |
| TUI-layout | 🟢 Godt | — |
| Fejlhåndtering | 🟢 God start | Udvid med N2/N3 |

**Dom:** Spec'en er **byggeklar efter revidering af C1-C3 + H1-H2**. Resten kan løses under implementeringen. Revidering tager 30 min, så er vi i gang med Fase 1.

---

## Review 3 — Claude (5. jul, på Bjørns anmodning)

**Metode:** Verificerede spec'ens load-bearing påstande mod den faktiske kode (ikke bare læst).

**Verificeret KORREKT (Jarvis' krydstjek holdt):**
- Alle stikprøve-endpoints findes: `/central/realtime|diagnostics|command|stream` (central.py, `prefix="/central"`), `/mc/overview` (mission_control.py:783), `/mc/body-state` (mission_control_living_mind.py:66), `/api/auth/issue` (jarvisx.py:1462).
- `core/services/central_terminal.py` findes. Begge `_require_owner()` findes (central.py:36, jarvisx.py:1120). De tre desk-komponenter der foreslås slettet findes alle.
→ "Endpoint-oversigten er komplet og korrekt" er en ægte, verificeret påstand. Godt arbejde.

**R1 (kritisk korrektion — H1 er teknisk usund):** Self-reviewens H1 anbefaler "local mode = importér `central_query` direkte, ingen HTTP" for at eliminere C2. **Det virker IKKE for live data.** CLI'en er en SEPARAT proces fra api/runtime. Den LIVE nerve-fire-feed (`/central/stream`) og `jc nerve`-recent lever i den kørende proces' IN-MEMORY trace — en frisk proces har sin egen TOMME trace. (Bevist gentagne gange 5. jul: throwaway-python læser durable shared_cache-tidsserie men får tom in-memory recent.) Kun durable snapshots (status/incidents/tidsserie) er cross-proces via shared_cache/DB; live-feeden er ikke. **Konklusion:** v2-designets valg (HTTP selv lokalt) er KORREKT — direct-import ville dræbe headline-feature (live feed). Marker H1 som **afvist-med-grund**, så ingen "fikser" det senere ved at adoptere direct-import. Opdater H1 i design-doc'en.

**R2 (beslutnings-inkonsistens — desk-sletning):** Self-reviewens K3 konkluderede "begge kan køre samtidig... config-ændring i desk, IKKE sletning". Men v2-designet (§1) BESLUTTER at SLETTE `CentralPanel.tsx` + `CentralHud.tsx` + `centralStream.ts`. Designet modsiger sin egen self-reviews anbefaling. At fjerne Centralen fra desk-appen (som Bjørn bruger dagligt) til fordel for en CLI er en reel UX-beslutning — ikke oplagt rigtig. **Anbefaling:** bak desk-sletningen ud af Fase 4 indtil Bjørn eksplicit bekræfter. Standard-sti bør være K3's blødere: behold desk-panelerne på lav-frekvens-polling, CLI'en får realtid. Sletning er en separat, bekræftet beslutning.

**R3 (mindre smell):** Hardcoded owner Discord ID i wizard (§3, linje 154). Bedre: prompt ved første kørsel eller læs fra en config-kilde. Ikke en blocker, men undgå hardcoded identitet.

**Mindre:** verificér `Textual>=4.0`/`Rich>=13.0`-pins eksisterer ved build (kan ikke tjekkes fra spec'en).

**Samlet:** Spec'en er solid og ærligt selv-reviewet. To ting bør ind FØR Fase 4: (R1) korrigér H1 til afvist-med-grund, (R2) gør desk-sletningen betinget af Bjørns bekræftelse. R3 er kosmetisk.

**Opdatering (Bjørn, 5. jul):** R2 **BEKRÆFTET** — desk-Central-panelerne skal væk. Begrundelse: to
SSE-tunge Central-paneler (`CentralPanel` + `CentralHud`) er den reelle streaming-belastning; Bjørn
har 3 skærme + terminal-workflow og vil have Centralen live i en dedikeret CLI så han kan se realtid
mens Claude/Jarvis arbejder. Rækkefølge-værn: CLI bygges + verificeres FØR panelerne fjernes (Fase 4).
Desk beholder et let `CentralBadge`. R1 lukket i design-doc. Spec er nu fuldt byggeklar.