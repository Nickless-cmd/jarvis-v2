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

## 2. Lovkrav — EU AI Act + GDPR

### 2.1 EU AI Act (træder i kraft 2. august 2026)

Jarvis desk vurderes at falde i kategorien **limited/generic AI** (ikke high-risk),
men skal stadig overholde følgende transparensforpligtelser:

| Krav | Implementering | Deadline |
|---|---|---|
| **Transparens** (Art. 50) | Brugere skal vide de interagerer med AI — tydeligt markeret i UI | 2. aug 2026 |
| **AI-genereret indhold** | Output skal kunne identificeres som AI-genereret | 2. aug 2026 |
| **Gennemsigtighed** | Systemets formål, begrænsninger og kapabiliteter dokumenteret | 2. aug 2026 |
| **Risk assessment** | Dokumentation af risikovurdering for low-risk systemer | 2. aug 2026 |
| **Human oversight** | Brugeren skal kunne overrule/stoppe AI-handlinger | 2. aug 2026 |

**Nuværende status i v0.2.28: INGEN compliance-tekst findes.** Ingen `privacy`,
`terms`, `consent`, `GDPR`, `cookie`, eller `firstTime` referencer i JS.

### 2.2 GDPR (gældende siden 2018)

| Krav | Implementering |
|---|---|
| **Samtykke** (Art. 6-7) | Data collection kræver eksplicit, informeret samtykke |
| **Data minimization** | Kun indsamle hvad der er nødvendigt — lokalt hvor muligt |
| **Right to be forgotten** | Brugerdata skal kunne slettes på forespørgsel |
| **Dataportabilitet** | Brugeren skal kunne tage sine data med |
| **Privacy by design** | Privacy indbygget fra starten |

**Nuværende fordel:** Jarvis desk's lokale-først arkitektur minimerer
GDPR-risiko. Data kan køre lokalt via Ollama, og sendes kun til cloud
når brugeren vælger en cloud-provider.

---

## 3. Brugerforventninger i 2026 — benchmark mod Claude Code + Codex

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
