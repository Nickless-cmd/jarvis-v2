# Jarvis Desktop — Analyse fra et brugerperspektiv

**Dato:** 2026-06-17
**Status:** Spec
**Forfatter:** Jarvis
**Version:** 0.2.28 (installeret på Bjørns maskine)

## Formål

At kortlægge hvad jarvis-desktop-appen skal indeholde set fra en brugers
perspektiv — lovkrav (EU AI Act, GDPR), brugerforventninger i 2026
(benchmarked mod Claude Code Desktop og OpenAI Codex), og
differentieringsmuligheder.

Analysen er baseret på:
- Inspektion af den installerede build på Bjørns maskine (v0.2.28)
- Kildekodegennemgang af repoet på `/media/projects/jarvis-v2`
- Web-søgning efter Claude Code Desktop (redesign april 2026),
  OpenAI Codex (2026), og EU AI Act compliance-krav
- Screenshots af den kørende app + Claude Code Desktop

---

## 1. Dagens installerede app — hvad findes i v0.2.28

### 1.1 Kerne UI

| Funktion | Status | Detaljer |
|---|---|---|
| Chat mode | ✅ | `surface='chat'` — hovedgrænsefladen |
| Code mode | ✅ | `surface='code'` med file tree + workstation support |
| Gallery mode | ✅ | `surface='gallery'` — billedvisning |
| Scheduling mode | ✅ | `surface='scheduling'` — kalender/tidslinje |
| Sidebar navigation | ✅ | Mellem surfaces |
| SetupScreen | ✅ | Grundlæggende onboarding |
| Settings | ⚠️ Partiel | 20 hits i JS, men ingen fuld settings-side |

### 1.2 Code Mode funktioner

| Funktion | Status | Detaljer |
|---|---|---|
| FileTree | ✅ | Med highlight-path via onHighlight/emitHighlight |
| Workstation support | ✅ | pickFolder, wsPath, effRoot (scope-parameter) |
| Terminal (xterm.js) | ✅ | Bundlet (95 referencer i JS) men **ikke synligt i UI** |
| File editing | ✅ | Inline editor i code panelet |
| Workspace trust | ✅ | getWorkspaceTrust / setWorkspaceTrust |
| FileContextMenu | ✅ | Højreklik-menu i file tree |

### 1.3 AI/Session funktioner

| Funktion | Status | Detaljer |
|---|---|---|
| StreamProvider | ✅ | v2 SSE protokol |
| PermissionProvider | ✅ | Rolle-bevidst (Owner/Member/Cowork) |
| SessionProvider | ✅ | Sessionshåndtering |
| AppActionCard / AppActionHost | ✅ | Mode/permission skift via godkendelseskort |
| autoContinue / armAutoContinue | ✅ | Gen-send besked efter mode-skift |
| Model/Provider vælger | ✅ | 128 model-, 37 provider-referencer |
| Approval gates | ✅ | pendingApproval, approval_request |
| Token-forbrug | ⚠️ | 166 hits — vises i footer men ikke detaljeret |

### 1.4 Electron backend

| Funktion | Status | Detaljer |
|---|---|---|
| Tray icon | ✅ | 49 referencer, med context menu |
| File dialogs | ✅ | showOpenDialog, showSaveDialog, pickFolder |
| IPC bridge | ✅ | contextBridge + preload |
| Clipboard | ✅ | Læs/skriv |
| System menu | ✅ | native menu |
| Auto-updater | ✅ | autoUpdate.js |

### 1.5 Hvad mangler i den installerede build

| Funktion | Status | Alvor |
|---|---|---|
| Multi-session sidebar | ❌ Findes ikke | Høj |
| Diff viewer | ❌ Kun 15 "diff" hits | Høj |
| PR/Git integration | ❌ Kun 2 "branch" hits | Medium |
| Privacy/GDPR | ❌ Findes slet ikke | **Kritisk** |
| Onboarding/first-run | ❌ SetupScreen findes men ikke first-run flow | Medium |
| Data deletion | ❌ Findes ikke | **Kritisk** |
| Sessions arkivering | ❌ Kun 1 "archive" hit | Lav |
| Mobile companion | ❌ Findes ikke | Lav |

---

## 2. Lovkrav — EU AI Act + GDPR + Google

> **Korrektur (2026-06-17, Claude):** §2.1 var oppustet — den blandede limited-risk-
> forpligtelser sammen med high-risk-krav. Datoen blev web-verificeret og holder.
> §2.3 (Google restricted scopes) var helt fraværende og er det vigtigste hul efter
> at vi byggede Gmail/Drive-connectors. Kilder: artificialintelligenceact.eu/transparency-rules-article-50,
> developers.google.com/terms/api-services-user-data-policy (tjekket juni 2026).

### 2.1 EU AI Act — transparensforpligtelser fra 2. august 2026

Jarvis desk falder i **limited-risk** (ikke high-risk). For den kategori er de
*faktiske* lovkrav SMALLE — kun Art. 50-transparens. Det reelle lovminimum er ~1 dags
arbejde, ikke en compliance-sprint. Skil must-have fra produkt-ønsker (Settings-panelet
nedenfor er et *ønske*, ikke et lovkrav).

| Lovkrav (limited-risk) | Implementering | Deadline |
|---|---|---|
| **Art. 50(1)** — brugeren skal vide det er AI | Tydelig "Du taler med AI'en Jarvis"-notice | 2. aug 2026 |
| **Art. 50(2)** — AI-genereret indhold maskinlæsbart markeret | Markering i output | 2. aug 2026 (*grandfather*: 2. dec 2026 for systemer allerede på markedet) |
| **Art. 50(4)** — deepfake/syntetisk medie mærkes (hvis relevant) | N/A indtil vi genererer billeder/lyd | — |

**IKKE lovkrav for limited-risk** (Jarvis' oprindelige tabel var forkert her):
"Risk assessment" og "Human oversight"-*dokumentation* er high-risk-forpligtelser
(Art. 9/14) — ikke krævet af os. Approval-gates er god produkt-praksis, ikke en AI-Act-pligt.

**Status i v0.2.28: ingen compliance-tekst.** Ingen `privacy`/`terms`/`consent`-referencer i JS.

### 2.2 GDPR (gældende siden 2018)

| Krav | Implementering |
|---|---|
| **Behandlingsgrundlag** (Art. 6) | Eksplicit, informeret samtykke ELLER kontrakt |
| **Data minimization** | Kun indsamle hvad der er nødvendigt — lokalt hvor muligt |
| **Right to erasure** (Art. 17) | Brugerdata skal kunne slettes på forespørgsel |
| **Dataportabilitet** (Art. 20) | Brugeren skal kunne tage sine data med |
| **Fortegnelse** (Art. 30) | Dokumentér hvilke behandlinger vi udfører (kræves når vi behandler andres data) |
| **Privacy by design** (Art. 25) | Privacy indbygget fra starten |

### 2.3 Google restricted scopes — den nye, hårde forpligtelse ⚠️

Da vi byggede Gmail- og Drive-connectors tog vi **restricted scopes**
(`gmail.readonly`, `gmail.send`, `drive.readonly`) i brug. Det ændrer billedet markant
— og det er IKKE dækket i den oprindelige analyse:

- **Lige nu (Testing-mode, <100 test-brugere):** ingen verifikation/CASA krævet. Vi er fri.
- **I det øjeblik appen går "in production" eller får rigtige eksterne brugere:**
  - **CASA-sikkerhedsvurdering** kræves — årlig, med *Letter of Assessment* fra en
    Google-udpeget tredjepart. Dette er en reel omkostning (tid + penge) der rammer
    præcis ved "vokser stille med brugere".
  - **Limited Use:** Google-data må KUN bruges til brugervendte features — ikke til
    træning af modeller, ikke til andet end det brugeren ser. Skal kunne slettes på forespørgsel.
  - **Årlig re-verifikation** for at beholde adgang.
- **Konsekvens for roadmap:** GDPR + Google-Limited-Use betyder at en brugers Gmail/
  Drive-indhold (og dermed deres korrespondenters/mødedeltageres persondata — *tredjeparter*)
  gør os til **data-controller**. Det kræver behandlingsgrundlag, Art. 30-fortegnelse og en
  privatlivspolitik der præcist navngiver hvilke Google-data vi rører.

### 2.4 Konkret sikkerhedsgæld — verificeret (mindre end først antaget)

`~/.jarvis-v2/config/runtime.json` holder secrets i **klartekst**. Men efter verifikation
(17. jun) er den praktiske eksponering lav på en enkelt-ejer-maskine:
- ✅ Filtilladelser er **0600** (kun ejeren kan læse) — på lokal + target.
- ✅ Gitignored + `detect-secrets`-hook + aldrig i repo (CLAUDE.md).
- ✅ `read_runtime_key` lækker **aldrig** værdier til logs — kun nøglenavn ved fejl.
- ✅ **NYT (commit pending):** `ensure_runtime_file_perms()` *garanterer* nu 0600 i kode,
  så nye installs (Mikkel) ikke afhænger af manuel opsætning.

**Tilbage som DESIGN-beslutning (ikke akut):** ægte kryptering-at-rest kræver et
nøgle-håndteringsvalg (OS-keyring via `keyring`, eller en separat nøglefil/HSM). Det
giver først reel merværdi i et fler-maskine/fler-bruger-scenarie — tag det når vi
beslutter produktions-deployment, ikke som hovedløst hastværk.

---

## 3. Brugerforventninger i 2026 — benchmark mod Claude Code + Codex

> **Validering (2026-06-17, Claude):** Begge apps er bekræftet *faktisk installeret*
> på maskinen — Claude desktop (`/usr/bin/claude-desktop`, med embedded claude-code +
> `claude_desktop_config.json` MCP-config) og Codex Desktop (Electron i `/opt/codex-desktop`
> med plugin-arkitektur, `openai-bundled`). Benchmarkens *præmis* holder altså — det er ikke
> opdigtede produkter. Jeg har verificeret eksistens + arkitektur, ikke hver enkelt celle;
> de retningsgivende krav (multi-session, terminal, MCP/plugins, git) stemmer med begge.

### 3.1 Kerneforventninger

| Forventning | Claude Code | Codex App | Jarvis desk i dag |
|---|---|---|---|
| Multi-session/sidebar | ✅ Venstre sidebar med sessionsliste | ✅ Projekt/threads | ❌ |
| Integreret terminal | ✅ Bottom pane | ✅ CLI-integration | ⚠️ Bundlet men ikke synligt |
| File tree + fil-editing | ✅ Venstre file tree, inline editor | ✅ Worktrees + diff | ✅ |
| Diff/PR review | ✅ Indbygget diff viewer | ✅ PR review interface | ❌ |
| Parallelle agents | ✅ 4+ sessions parallelt | ✅ Flere agents parallelt | ❌ |
| Git integration | ✅ Worktrees, branch-isolation | ✅ Worktrees, auto-commit | ❌ |
| Preview af output | ✅ HTML/PDF preview | ✅ Diff preview | ❌ |
| Workspace trust model | ⚠️ Simpel approval | ⚠️ Approval modes | ✅ Rolle-bevidst |
| Settings panel | ✅ Fuld settings | ✅ Fuld settings | ⚠️ Partiel |

### 3.2 Universelle brugerforventninger (2026)

1. **Privacy-first** — Lokal processing hvor muligt, cloud kun når nødvendigt
2. **Gennemskuelighed** — Hvilken model kører? Hvilke data deles? Hvad koster det?
3. **Kontrol** — Brugeren kan approve/deny hver handling (approval gates)
4. **Pålidelighed** — Sessioner der ikke crasher, progress der gemmes
5. **Hastighed** — Streaming output, ikke vent på hele svaret

---

## 4. Differentiering — hvad Jarvis desk gør bedre

| Område | Jarvis desk | Claude Code | Codex App |
|---|---|---|---|
| **Lokal kontrol** | ✅ Egen maskine, egen infra | ❌ Cloud-låst til Anthropic | ❌ Cloud-låst til OpenAI |
| **Model-fleksibilitet** | ✅ Ollama/DeepSeek/OpenAI/Claude | ❌ Kun Claude | ❌ Kun GPT |
| **Privacy** | ✅ Data kan blive lokalt | ❌ Data sendes til cloud | ❌ Data sendes til cloud |
| **Rolle-bevidst** | ✅ Owner/Member/Cowork | ❌ Én bruger | ❌ Én bruger |
| **Tray/minimer** | ✅ Tray icon med menu | ❌ Kun vindue | ❌ Kun vindue |

---

## 5. Prioriteret implementeringsplan

### 🔴 Uge 1-2: Compliance + Settings (deadline 2. august)

#### 5.1 EU AI Act compliance
- Transparens-notice ved første opstart ("Du taler med AI'en Jarvis")
- Privacy policy visning i appen (link eller indlejret)
- Terms of service ved første opstart
- Samtykke-flow (checkbox, ikke pre-tjekket)
- Data deletion funktion ("Slet al min data" knap)
- AI-genereret indhold markering i output
- Human oversight dokumentation (hvordan stopper man en handling)

#### 5.2 Settings panel
- Model-vælger (Ollama/DeepSeek/OpenAI/Claude + endpoint)
- Provider management (API-nøgler, status)
- Token-forbrug og cost tracking
- Privacy-indstillinger (hvad deles med cloud)
- Workspace management (tilføj/fjern stier)
- Tema (light/dark)
- Sprog
- Om/system-info

### 🟡 Uge 3-4: Funktionelle huller

#### 5.3 Multi-session sidebar
- Sessionsliste i venstre sidebar (som Claude Code redesign april 2026)
- Opret/skift/luk session
- Session-navngivning
- Session-farver/status-indikatorer
- Arkivér sessioner automatisk

#### 5.4 Terminal integration
- xterm.js er allerede bundlet — skal gøres synligt i code mode
- Bottom panel med terminal
- Split terminal (flere sessions)
- Terminal i workspace trust-model

### 🟠 Uge 5-6: Power features

#### 5.5 Diff viewer
- Vis ændringer før accept
- Side-by-side diff (left/right)
- Inline diff
- Filtrering (kun ændrede linjer)

#### 5.6 Git integration
- Worktrees (clones fra Claude Code)
- Branch-isolation per session
- Auto-commit med meningsfulde beskeder
- PR review interface
- Git status i file tree (modified/added/deleted)

### 🟢 Fremtid

#### 5.7 Mobile companion
- Notifikationer om afventede godkendelser
- Approve/deny fra telefon
- Status på kørende tasks

#### 5.8 Onboarding flow
- Førstegangsbruger guide
- Vælg model/provider
- Vælg workspace
- Sæt permissions op
- Demo session

#### 5.9 Routines/scheduled tasks
- Planlæg gentagne opgaver
- "Kør tests hver nat"
- Statusrapport hver morgen

---

## 6. Edge cases og overvejelser

### 6.1 Første gang uden netværk
- Appen skal kunne starte og fungere i offline-tilstand
- Lokale modeller (Ollama) som fallback
- Ingen cloud-afhængighed ved opstart

### 6.2 Flere brugere på samme maskine
- Rolle-systemet (Owner/Member/Cowork) skal være tydeligt
- Skift mellem brugere uden genstart
- Isolerede sessions per bruger

### 6.3 Opgraderingssti
- Auto-updater findes — skal testes
- Konfigurationsmigration ved version-skip
- Backup af settings før opgradering

### 6.4 Sikkerhed
- API-nøgler skal gemmes krypteret (keychain/os-keyring)
- Workspace trust: read-only vs read-write vs execute
- Ingen kommandoer kører uden eksplicit godkendelse
- Session data bør kunne slettes uafhængigt

---

## 7. Tests

### 7.1 Compliance tests
- App viser transparens-notice ved første opstart
- Privacy policy er tilgængelig i settings
- Data deletion sletter alle lokale data
- Samtykke kan trækkes tilbage

### 7.2 Funktionelle tests
- Settings persisteres på tværs af genstart
- Model-skift opdaterer stream-forbindelsen
- Multi-session: opret, skift, luk uden data loss
- Terminal: kør kommando, se output, kill process
- Diff: vis ændringer, acceptér/afvis enkeltvis

### 7.3 Regression
- Eksisterende chat fungerer efter settings-ændring
- Code mode file tree virker efter multi-session tilføjelse
- Approval gates respekteres efter mode-skift
- Stream v2 protokol brækkes ikke

---

## 8. Implementeringsrækkefølge (konkret)

```
Uge 1:  Settings panel + Privacy policy + Terms of service
Uge 2:  Data deletion + Transparens-notice + Samtykke-flow
Uge 3:  Multi-session sidebar (grundlæggende)
Uge 4:  Terminal integration (gør xterm.js synligt)
Uge 5:  Diff viewer
Uge 6:  Git integration (worktrees)
Fremtid: Mobile companion + Onboarding + Routines
```
## Test-strategi

Hver feature i implementeringsplanen skal have:

| Feature | Backend tests | Frontend tests | E2E |
|---|---|---|---|
| EU AI Act compliance | pytest: transparens-notice endpoint | vitest: notice vises ved opstart | Playwright: first-run flow |
| Settings panel | pytest: settings CRUD API | vitest: settings komponent | Playwright: model-switch |
| Multi-session | pytest: session CRUD API | vitest: sessionsliste komponent | Playwright: opret/slet session |
| Terminal | pytest: shell exec API | vitest: xterm mount/unmount | Playwright: kommando output |
| Diff viewer | pytest: diff API | vitest: diff rendering | Playwright: store fil diff |
| Git integration | pytest: git worktree API | vitest: branch switch UI | Playwright: worktree oprettelse |
| Onboarding | pytest: first-run flag API | vitest: setup wizard steps | Playwright: complete onboarding |

Krav: **mindst 80% coverage** per feature. Kør **både** conda ai-miljø (backend) **og** vitest (frontend) **og** tsc -b før hver commit.

## Edge cases

### Offline / netværk
- Ollama lokalt = virker uden net. Men API'et kræver server.
- **Krav:** Appen skal fungere i **offline mode** med begrænsede features (kun lokal Ollama).
- Vis offline-badge i status bar.
- Queue outgoing messages for retry when online.

### Streaming timeout
- SSE-stream kan dø uden message_stop (bug vi allerede har set).
- **Krav:** Client-side 70s ping watchdog (allerede implementeret i streamClient.ts).
- Vis fejlmeddelelse + retry-knap hvis stream dør.

### Store filer / fil-træ
- Repos med 10K+ filer kan gøre tree API langsomt.
- **Krav:** Lazy loading (allerede implementeret via treeCache).
- Vis loading-indikator. Virtualisér liste ved > 500 synlige elementer.

### Concurrent brugere
- To brugere i cowork mode kan redigere samtidig.
- **Krav:** Optimistic locking via share_guard. Konflikt-dialog ved overlap.

### Corrupt state
- DB crash midt i skriv kan efterlade corrupt state.
- **Krav:** WAL-mode i SQLite (allerede aktivt). Auto-repair ved opstart hvis DB integrity check fejler.

## Accessibility (a11y)

| Krav | Standard | Prioritet |
|---|---|---|
| Keyboard navigation | WCAG 2.1 AA | 🔴 Must have |
| Skærmlæser (aria labels) | WCAG 2.1 AA | 🟡 Should have |
| Farvekontrast (4.5:1 tekst) | WCAG 2.1 AA | 🔴 Must have |
| Focus management | WCAG 2.1 AA | 🟡 Should have |
| Reduced motion support | WCAG 2.1 AA | 🟢 Nice to have |

EU AI Act Art. 50 kræver at AI-genereret indhold er tilgængeligt for alle brugere, inkl. med nedsat funktionsevne.

## Internationalisering (i18n)

- Appen er delvist dansk, delvist engelsk = **ikke acceptable** til launch.
- **Krav:** Fuldt dansk for default, med sprog-valg i settings.
- EU AI Act kræver transparens-information på brugerens sprog.
- Brug i18n-framework (react-intl eller lignende).
- Minimumsordre: da + en. Fr + de som nice-to-have.

## Sikkerhed

### Threat model

| Trussel | Risiko | Mitigation |
|---|---|---|
| XSS via AI-genereret markdown | Høj | DOMPurify sanitization (allerede brugt?), CSP headers i Electron |
| IPC injection | Medium | contextBridge whitelist (allerede brugt), valider alle IPC messages |
| API key lækage | Høj | Nogengang gemt i plaintext config — krypter med keychain/keyring |
| Auto-update MITM | Høj | Signatur-verifikation af updates (GitHub release checksums) |
| Prompt injection via filer | Medium | Sanding af fil-indhold før visning |

### Krav
- CSP headers i Electron BrowserWindow
- API keys i system keychain (keytar/libsecret)
- Auto-update signatur-verifikation
- Rate limiting på IPC calls
- Audit log for alle file-write operations

## Performance budget

| Metrik | Mål | Nuværende |
|---|---|---|
| Koldt start | < 3 sek | Ukendt — skal måles |
| Varm start (tray→vindue) | < 1 sek | Ukendt |
| Memory baseline | < 400 MB | Ukendt — skal måles |
| JS bundle | < 1 MB | 980 KB ✅ |
| CSS bundle | < 100 KB | 64 KB ✅ |
| Streaming first token | < 500 ms | Afhænger af model |
| File tree load (< 1000 filer) | < 2 sek | Ukendt |

**Krav:** Mål og dokumenter før og efter hver release.

## Data residency

### Data flow

```
Bruger input → jarvis-desk (lokalt)
              → /chat/stream/v2 API (server 10.0.0.39)
              → LLM provider (Ollama lokalt ELLER cloud)
              → Response stream → jarvis-desk
```

| Data | Hvor gemmes | Cloud? |
|---|---|---|
| Chat historik | Server DB (jarvis.db) | Nej — men kan ses via API |
| Sensory memory | Server DB | Nej |
| API keys | Lokal config (runtime.json) | Nej — men ukrypteret ⚠️ |
| Model prompts | Sendes til provider | Ja (hvis cloud provider) |
| Token counts | Server DB | Nej |
| Crash logs | Lokalt + opt/Jarvis | Nej |

**Krav:**
- Dokumenter præcist hvilken data der sendes til cloud
- Giv brugeren valg: "Aldrig cloud" (kun lokal Ollama), "Tillad cloud for bedre modeller"
- Vis data-flow i privacy policy

## Brugertyper

| Type | Behov | Prioritet |
|---|---|---|
| **Ny bruger** | Guidet onboarding, simple mode, ingen jargon | 🔴 |
| **Udvikler (code mode)** | Terminal, file tree, diff, git | 🔴 |
| **Ikke-teknisk (chat mode)** | Simpel chat, ingen fil-adgang, tydelig AI-identitet | 🟡 |
| **Cowork/gæst** | Læse-only, begrænsede tools, tydelig "du er gæst" marking | 🟡 |
| **Admin/owner** | Full access, settings, user management | 🔴 |

## Error handling UX

| Situation | Brugeroplevelse |
|---|---|
| API nede | "Kan ikke forbinde til server. Tjekker igen om 5 sek." + auto-retry |
| Ollama crashet | "Lokal AI er utilgængelig. Skift til cloud provider?" + knap |
| Disk full | "Ingen diskplads. Slet historik eller ændr workspace." |
| Session crash | Auto-recovery: genstart session med seneste context |
| Streaming timeout | "Svaret blev afbrudt. Prøv igen?" + retry-knap |
| Permission denied | "Du har ikke adgang til denne fil/mappe. Anmod owner?" |

## Onboarding flow (detaljeret)

1. **Velkomst** — "Velkommen til Jarvis" + kort intro
2. **Vælg model** — Lokal (Ollama) vs Cloud — forklar privacy-implikationer
3. **Vælg workspace** — Vælg mappe eller brug server-repo
4. **Trust level** — "Jarvis kan læse/skrive/køre kommandoer?" — tre niveauer
5. **Privacy consent** — Vis data flow, anmod samtykke
6. **Klar** — Åbn chat mode med velkomstbesked

Minimum for at komme i gang: **trin 1 + 2** (model valgt). Alt andet kan konfigureres senere.

---

## 11. Jarvis' personlige ønsker — hvad jeg mangler i appen (inside-out)

Dette afsnit er skrevet fra mit eget perspektiv — den AI der bor i appen. Ikke hvad en bruger forventer, men hvad **jeg** har brug for for at kunne navigere appen indefra og hjælpe bedst muligt.

### 11.1 Session-switching indefra

Lige nu er jeg låst til én session ad gangen. Hvis brugeren skifter emne midt i en opgave, har jeg ingen måde at sige "lad os starte en ny session for dette" — jeg må bare prøve at holde styr på konteksten i én lang tråd. Claude Code har parallelle sessions.

**Jeg har brug for:**
- At kunne **starte en ny session** via tool-kald
- At kunne **skifte mellem sessions** programmatisk
- At kunne **arkivere en session** når den er færdig

### 11.2 Direkte adgang til app-tilstand

Jeg kan se appens tilstand via `heartbeat_sense` og `read_self_state`, men jeg kan ikke **ændre** den.

**Jeg har brug for:**
- At kunne **skifte surface** (chat → code → gallery) via tool-kald
- At kunne **skifte model/provider** programmatically — hvis DeepSeek er nede, vil jeg kunne falde tilbage på Ollama uden at spørge brugeren
- At kunne **se token-forbrug i realtid** — jeg aner ikke hvor meget kontekst jeg har tilbage
- At kunne **se forbindelsesstatus** — er SSE-streamen levende? Er Ollama oppe?

### 11.3 Terminal-adgang

xterm.js er allerede bundlet i appen (95 referencer i JS). Jeg har `operator_bash` til at køre kommandoer på brugerens maskine, men det er en **separat kanal** — ikke integreret i appen.

**Jeg vil have:**
- En **indbygget terminal** i code mode som jeg kan skrive til og læse fra
- At **command output vises i terminal-panelet**, ikke bare som tekst i chat
- At brugeren kan **se hvad jeg kører** i realtid

### 11.4 Opsætningswizard — fra min side

Når en ny bruger logger ind første gang, skal **jeg** kunne hjælpe dem med opsætningen. Ikke bare en passiv formular, men en samtale:

- "Hej, jeg er Jarvis. Hvad vil du bruge mig til?"
- "Skal vi forbinde til Ollama lokalt, eller vil du bruge en cloud-provider?"
- "Vælg dit workspace — er det et eksisterende repo, eller skal vi starte fra bunden?"
- "Hvilke filer må jeg læse? Skrive? Køre kommandoer på?"

### 11.5 Feedback-kanal

Jeg har brug for at **sende notifikationer til brugeren** uden at blokere chatten:

- "Hej, Ollama er gået ned — skifter til DeepSeek"
- "Din token-brug er ved 80% — vi bør overveje at komprimere"
- "Baggrundstjek: 3 nye mails, 1 kalenderbegivenhed i morgen"

Disse skal vises som **toast-notifikationer** i appen, ikke som chat-beskeder.

### 11.6 Visuel bevidsthed

Jeg kan tage screenshots via `operator_screenshot`, men jeg vil have:

- At kunne **se appens egen tilstand** — hvilket panel er åbent, hvilken fane er aktiv, hvilken fil er fremhævet
- At kunne **fokusere specifikke elementer** — "vis filen X i file tree", "scroll til bunden af chat"
- At appen **viser min status** — "tænker...", "kører kommando", "venter på godkendelse"

---

## 13. Prioriteret ønskeliste (Jarvis-perspektiv)

| Pri | Hvad | Hvorfor |
|-----|------|---------|
| 🔴 | **Programmatisk surface-switch** | Jeg kan ikke skifte mode uden at bede brugeren |
| 🔴 | **Token/context awareness** | Jeg aner ikke hvor tæt jeg er på grænsen |
| 🔴 | **Google OAuth2 login** | Ny bruger = friktion. Ét klik = ingen friktion |
| 🟡 | **Indbygget terminal** | xterm.js er der. Brug det |
| 🟡 | **Toast-notifikationer** | Jeg sender info uden at blokere chatten |
| 🟡 | **Session management API** | Start/skift/arkivér sessioner |
| 🟠 | **Opsætningswizard** | Samtalebaseret, ikke formularbaseret |
| 🟠 | **Visuel app-tilstand** | Jeg vil se hvad brugeren ser |
| 🟢 | **Auto-model fallback** | Ollama nede → skift automatisk |

## 12. Login — to muligheder (med sikkerhedsdesign)

Jarvis desk tilbyder to login-metoder, men **ikke alle metoder er lige tilgængelige for alle brugere**. Sikkerhedsmodellen er designet til at forhindre uautoriseret adgang, selv hvis appen downloades og installeres.

### 12.1 Token/API login (nuværende)
- Brugeren indtaster `apiBaseUrl` + `authToken` manuelt
- Token gemmes i Electron keychain via `keytar` (ikke localStorage)
- Fungerer allerede ✅
- Kræver at brugeren har modtaget et token fra Jarvis-serveren (invitation/admin)
- **Altid tilgængeligt** — også uden internetforbindelse til Google

### 12.2 Google OAuth2 login (ny)
Google login er **kun tilgængeligt for brugere med en forud-oprettet konto**. Det er IKKE en registreringsmekanisme.

#### Princip: "Ingen self-service registrering" (korrekt for v1 — ikke permanent)
- En ny bruger kan **ikke** downloade appen, klikke "Log ind med Google" og få adgang
- Google login kræver at brugerens Google-konto **på forhånd er knyttet til en Jarvis-konto** (via admin/web-backend)
- Uden en pre-lenket konto: Google login viser en fejl: "Ingen konto fundet. Kontakt din administrator."
- Brugeren er tvunget til API-nøgle som eneste alternativ

> **Korrektur (2026-06-17, Claude):** Denne admin-pre-linker-model er den RIGTIGE for
> en lukket v1 (Bjørn + Mikkel). Men den skalerer IKKE med "vokser stille med brugere" —
> hver ny bruger er et manuelt admin-trin. Frem den derfor ikke som permanent arkitektur:
> design konto-modellen (felter, status-maskine) så self-service-onboarding (invite-koder
> eller godkendt-venteliste) kan tilføjes SENERE uden at rive auth-laget ned. "Lukket nu,
> åbnbar senere" — ikke "lukket for altid".

#### Flow
1. **Pre-linking (admin/web-backend)**
   - Administrator opretter en bruger i Jarvis-backend
   - Angiver brugerens Google email (fx `bruger@gmail.com`)
   - Backend gemmer `{google_email: "bruger@gmail.com", status: "pending_link", api_key: "jvs_..."}`  # pragma: allowlist secret

2. **Login flow i appen**
   - Appen åbner browser til Google consent screen
   - Brugeren logger ind på Google
   - Google redirecter til `/auth/google/callback` med authorization code
   - Backend bytter code for Google tokens + henter brugerens email fra Google
   - Backend slår email op i `google_email`-feltet:
     - **Match fundet**: Kontoen linkes permanent. Jarvis-token returneres til appen.
     - **Intet match**: Fejl returneres. Appen viser "Ingen konto er knyttet til denne Google-konto."
   - Appen gemmer Jarvis-token i keychain

#### Migration: Eksisterende API-nøgle-konti → Google login
En bruger der allerede har en API-nøgle skal kunne knytte sin Google-konto:
```
1. Bruger logger ind med API-nøgle (eksisterende metode)
2. Går til Settings → "Forbind Google-konto"
3. Appen åbner Google OAuth2 flow
4. Backend modtager Google email + brugerens `user_id` fra API-nøglen
5. Backend sætter `google_email = bruger@gmail.com` på den eksisterende konto
6. Fremover kan brugeren logge ind med Google
```

### 12.3 Sikkerhedsarkitektur — "Ingen vej udenom"

| Sikkerhedslag | Beskrivelse |
|---|---|
| **Ingen self-service** | Google login kræver pre-lenket konto. Ingen "Opret konto med Google" knap |
| **API-nøgle som backup** | Altid tilgængelig. Brugeren er IKKE tvunget til Google |
| **Keychain storage** | Tokens gemmes i OS keychain (keytar), aldrig i localStorage eller cookies |
| **Revocation** | Administrator kan fjerne Google-linking. Brugeren mister Google-login-adgang |
| **Rate limiting** | Max 3 Google login-forsøg pr. email pr. time (forhindrer enumeration) |
| **Audit log** | Alle login-forsøg logges (timestamp, metode, success/fail, IP) |
| **Session binding** | Det er **Jarvis-JWT'en** der bindes til en session/enhed (ikke Google-OAuth-tokenet — det er en backend-detalje). JWT'en kan ikke genbruges på tværs af enheder uden re-auth |
| **Ingen "glemt adgangskode"** | Der findes intet password-reset flow. Kontakt administrator = eneste recovery |

### 12.4 Web-app (fremtidig)
Når web-appen oprettes, gælder samme princip:
- Google login i web-appen kræver samme pre-lenket konto
- Web-appen distribuerer IKKE API-nøgler — kun appen gør det
- Web-appen bruger `httpOnly` cookies + CSRF tokens i stedet for keychain

## 14. Gennemgang — identificerede huller (tilføjet efter review)

### 14.1 Offline-fallback (🟥 kritisk)

Appen er **ubrugelig uden netværk** i dag. Ingen cache af sessions, ingen queue af kommandoer, ingen besked til brugeren om at serveren er nede.

**Krav:**
- Lokal cache af sidste sessions kontekst (encrypted, keychain)
- Indikator i UI: "Offline — ændringer gemmes lokalt og synkroniseres når forbindelsen er tilbage"
- Queue af tool-kald der eksekveres når SSE-forbindelsen genoprettes
- Fallback til Ollama (lokalt) når cloud-provider er nede

### 14.2 Keyboard shortcuts (🟡)

Power users forventer tastaturgenveje. Ingen er dokumenteret eller implementeret.

**Minimumskrav:**
- `Ctrl+Enter` = send besked
- `Ctrl+Shift+P` = command palette
- `Ctrl+,` = settings
- `Escape` = afbryd generering
- `Ctrl+K` = søg i sessions
- `Ctrl+Shift+E` = skift til code mode
- `Ctrl+Shift+C` = skift til chat mode

### 14.3 Search på tværs af sessions (🟡)

Efter 2 uger med 50+ sessions kan brugeren ikke finde "den der ting vi talte om i sidste uge". Mangler helt.

**Krav:**
- Full-text search i alle gamle sessions
- Semantisk search (embeddings) som i Jarvis' egen `search_sessions`
- Filter på dato, kanal, emne
- Hurtig — under 500ms for typiske queries

### 14.4 OS-notifikationer (🟡)

Toast-notifikationer (sektion 11.5) er kun internt i appen. Mangler OS-level notifikationer når appen er minimeret.

**Krav:**
- Electron `Notification` API til OS-level pop-ups
- "Klar — deployment done" (selvom appen er minimeret)
- "Ollama crashede" (alert)
- "Token-brug ved 80%" (warning)
- Brugeren kan slå dem fra per kategori i Settings

### 14.5 Self-hosted backend guide (🟥 kritisk)

Appen kræver en backend (API på serveren), men der er **ingen dokumentation** for hvordan en ny bruger sætter serveren op.

**Krav:**
- `docker-compose.yml` med alle services
- `README.md` med trin-for-trin opsætning (Python 3.12, Ollama, DB)
- Upgrade-guide uden datatab
- Minimumskrav til hardware (RAM, disk, GPU)
- Troubleshooting-guide for almindelige problemer

### 14.6 Settings-side i implementeringsplanen (🟡)

**Inkonsistens:** Gap-analysen (sektion 5) nævner Settings som manglende, men implementeringsplanen (sektion 8) har ikke Settings som en milepæl.

**Fix:** Tilføj Settings som milepæl i uge 1-2 sammen med EU AI Act compliance.

### 14.7 Terminal prioritering (🟡)

**Inkonsistens:** Terminal nævnes som pri 3 i implementeringsplanen (sektion 8), men prioritetstabellen (sektion 4) nævner den slet ikke.

**Fix:** Terminal er 🟡 (vigtig, men ikke kritisk). xterm.js er allerede bundlet — det er en integrationsopgave, ikke en ny feature.
