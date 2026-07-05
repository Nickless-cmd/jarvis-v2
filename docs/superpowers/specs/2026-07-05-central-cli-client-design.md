# Central CLI Client — Design Spec v2

**Dato:** 5. juli 2026  
**Forfatter:** Jarvis (med Bjørn)  
**Status:** Byggeklar (efter 2. gennemkørsel self-review) — 2 punkter afklares før Fase 4 (se review 3)  
**Revisioner:** v2 — inkorporerer self-review fund + jarvis-desk nedgradering. Claude-review 3 (5. jul): verificeret mod kode + R1 (H1 afvist-med-grund) + R2 (desk-sletning betinget af bekræftelse)

---

## 1. Vision

En standalone CLI-klient der giver Bjørn fuld realtids-adgang til Den Intelligente Central fra et terminal-vindue. Ikke en tynd wrapper — en **førsteklasses TUI** med J.A.R.V.I.S-æstetik, live data, fuld læse/skrive-adgang, og diagnostisk dybde.

**Mål:** `central` i terminalen → bum, fuld adgang. Et af tre skærme.

### Arkitekturbeslutning: Centralen flytter ud af jarvis-desk

**Før:** jarvis-desk har to tunge Central-paneler (`CentralPanel.tsx` i code mode + `CentralHud.tsx` i cowork) — begge med SSE-streaming, cluster-grids, nerve-feeds, kommando-konsoller. Det gør desktop-appen tung og langsom.

**Efter:**
- **jarvis-desk** → nedgraderes til et let **CentralBadge** i header/miljøfelt. Poller `/central/realtime` hvert 10-15s. Viser status-farve + incident/anomaly count. Ingen SSE, ingen streaming, ingen kommando-input.
- **CLI-klienten** → bliver den **primære Central-interface**. SSE-stream, alle kommandoer, fuld diagnostic, skrive-adgang, alt.

**Hvad fjernes fra jarvis-desk** — ⚠️ **BETINGET af Bjørns eksplicitte bekræftelse (Claude-review 3, R2).**
Self-reviewens K3 konkluderede "begge kan køre samtidig, IKKE sletning" — men denne §1 besluttede
sletning. Det modsiger self-reviewen, og at fjerne Centralen fra desk-appen Bjørn bruger dagligt er
en reel UX-beslutning. **Standard-sti indtil bekræftelse:** behold desk-panelerne på lav-frekvens-
polling (K3's blødere vej); CLI'en får realtid. Sletningen nedenfor udføres KUN hvis Bjørn siger ja:
- `CentralPanel.tsx` — slettes fra CodeView *(betinget)*
- `CentralHud.tsx` — slettes fra CoworkView *(betinget)*
- `centralStream.ts` — slettes *(betinget)*
- `getCentralNerve`, `toggleCentralNerve`, `runCentralCommand` — fjernes fra api.ts *(betinget)*

**Hvad tilføjes i jarvis-desk:**
- `CentralBadge.tsx` — let komponent: poll `/central/realtime` hvert 10-15s, vis farve + count, klik = tooltip med seneste incidents. ~50 linjer React.

---

## 2. Hvad backenden allerede har

Alt server-siden er bygget. Klienten skal bare snakke med det.

### Central-routes (`/central/*`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/central/command` | POST | Kommando-REPL (status/incidents/trace/nerve/toggle/scan/...) |
| `/central/stream` | SSE | Live nerve-fire feed (realtid) |
| `/central/realtime` | GET | Snapshot af Centralens live-tilstand |
| `/central/timeseries` | GET | Per-nerve tidsserie på tværs af processer |
| `/central/diagnostics` | GET | Fuldt diagnostik-sted (incidents/anomalier/instrument/root causes) |
| `/central/providers` | GET | Provider-helbred (ping/drift) |
| `/central/mind` | GET | Jarvis Mind-hub (alle faner) |
| `/central/nerve/{nerve}` | GET | Én nerves spor + lokation + on/off |
| `/central/nerve/{nerve}/toggle` | POST | Tænd/sluk nerve |

### Mission Control (`/mc/*`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/mc/overview` | GET | System-overview |
| `/mc/events` | GET | Hændelsesstrøm |
| `/mc/costs` | GET | Omkostninger |
| `/mc/runs` | GET | Kørsler |
| `/mc/approvals` | GET | Afventende godkendelser |
| `/mc/autonomy/proposals` | GET | Autonomi-forslag |
| `/mc/initiatives` | GET | Initiativer |
| `/mc/operations` | GET | Operationer |
| `/mc/jarvis` | GET | Selv-model |
| `/mc/cognitive-frame` | GET | Kognitiv ramme |
| `/mc/attention-budget` | GET | Opmærksomhedsbudget |
| `/mc/self-code-changes` | GET | Selv-kode-ændringer |
| `/mc/internal-cadence` | GET | Intern kadence |
| `/mc/emergent-signals` | GET | Emergente signaler |
| `/mc/embodied-state` | GET | Legamlig tilstand |
| `/mc/affective-meta-state` | GET | Affektiv meta-tilstand |
| `/mc/loop-runtime` | GET | Loop-runtime |
| `/mc/idle-consolidation` | GET | Idle-konsolidering |
| `/mc/liveness` | GET | Live-status |
| `/mc/memory-pipeline` | GET | Hukommelses-pipeline |
| `/mc/scheduled-tasks` | GET | Planlagte opgaver |
| `/mc/costs/daily` | GET | Daglige omkostninger |
| `/mc/runs/{run_id}` | GET | Specifik kørsel |

### Living Mind (`/mc/*` — mission_control_living_mind.py)
| Endpoint | Beskrivelse |
|---|---|
| `/mc/body-state` | Legems-tilstand |
| `/mc/surprise-state` | Overraskelses-tilstand |
| `/mc/taste-state` | Smags-tilstand |
| `/mc/irony-state` | Ironi-tilstand |
| `/mc/thought-stream` | Tankestrøm |
| `/mc/thought-proposals` | Tankeforslag |
| `/mc/experienced-time` | Erfaret tid |
| `/mc/development-narrative` | Udviklingsnarrativ |
| `/mc/existential-wonder` | Eksistentiel forundring |
| `/mc/dream-insights` | Drømmeindsigter |
| `/mc/code-aesthetic` | Kode-æstetik |
| `/mc/user-model` | Bruger-model |
| `/mc/memory-decay` | Hukommelses-forgængelse |
| `/mc/desires` | Lyster |
| `/mc/absence-state` | Fraværs-tilstand |
| `/mc/creative-drift` | Kreativ drift |
| `/mc/curiosity-state` | Nysgerrigheds-tilstand |
| `/mc/meta-reflection` | Meta-refleksion |
| `/mc/conflict-signal` | Konflikt-signal |
| `/mc/reflection-cycle` | Refleksionscyklus |
| `/mc/layer-tensions` | Lag-spændinger |
| `/mc/dream-motifs` | Drømmemotiver |

### JarvisX (`/api/*`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/api/whoami` | GET | Identitet-verifikation |
| `/api/auth/whoami-token` | GET | Token-inspektion (public) |
| `/api/auth/issue` | POST | Mint nyt token (owner-only, kræver X-JarvisX-User header) |
| `/api/auth/refresh` | POST | Refresh access-token (public, kræver refresh-token) |
| `/api/workspace/list` | GET | Workspaces |
| `/api/workspace/tree` | GET | Workspace fil-træ |
| `/api/workspace/read` | GET | Læs workspace-fil |
| `/api/channels/state` | GET | Gateway-status (Discord/Telegram) |

### Andre nyttige
| Endpoint | Beskrivelse |
|---|---|
| `/status` | System-status |
| `/mc/agentic-guards` | Agentic guards |
| `/mc/tool-router` | Tool-router config |
| `/mc/cheap-balancer` | Cheap balancer |

---

## 3. Auth & Sikkerhed

### To auth-tilstande (dokumenteret fra kode)

Backenden har **to forskellige `_require_owner()`-implementationer** med forskellig adfærd:

1. **`central.py`:** ubundet request = owner (localhost default). Central-routes virker uden auth.
2. **`jarvisx.py`:** ubundet request = afvist (403). `/api/auth/issue` kræver `X-JarvisX-User` header med owner Discord ID.

`auth_required()` default = `False` (localhost dev mode). Kan slås til med `JARVISX_AUTH_REQUIRED=1`.

### CLI Auth-strategi — to modes

**Local mode (default):**
- Clienten kører på samme maskine som API'en (Bjørn koder på serveren)
- Auto-detektion: tjek om `127.0.0.1:8080` svarer → local mode
- Bootstrap: send `X-JarvisX-User: <owner_discord_id>` header → kald `/api/auth/issue` → mint token
- Efterfølgende: brug `Authorization: Bearer <token>` for alle kald
- Token gemmes i `~/.jarvis-v2/config/central_cli.json` med 0600 perms

> **AFVIST alternativ (Claude-review 3, R1): "importér `central_query` direkte, ingen HTTP".**
> Self-reviewens H1 foreslog dette. Det virker IKKE: CLI'en er en SEPARAT proces fra api/runtime.
> Den LIVE nerve-fire-feed (`/central/stream`, `jc nerve`-recent) lever i den kørende proces'
> IN-MEMORY trace — en frisk CLI-proces har sin egen TOMME trace. Kun durable snapshots
> (status/incidents/tidsserie) er cross-proces via shared_cache/DB; live-feeden er det ikke.
> Derfor SKAL CLI'en gå via HTTP til den kørende api-proces for headline-featuren (live feed).
> Local mode = HTTP mod localhost (som ovenfor), IKKE direct-import.

**Remote mode (`--remote http://10.0.0.39:8080`):**
- Kræver pre-minted token (overføres out-of-band)
- Clienten validerer via `/api/auth/whoami-token` ved startup
- Hvis udløbet: vis besked + instruktion om at minte nyt token på serveren

**Første gang (setup-wizard):**
1. Spørger efter API URL (default: `http://127.0.0.1:8080`)
2. Spørger efter owner Discord ID (default: Bjørns Discord ID, hardcoded i wizard)
3. Kalder `/api/auth/issue` med `X-JarvisX-User` header
4. Gemmer token + refresh-token i `~/.jarvis-v2/config/central_cli.json` (0600)
5. Viser udløbsdato + success-besked

**Sikkerhedsregler:**
- Token **aldrig** i klar tekst i logs, terminal-output, eller process-list
- Token gemmes kun lokalt med 0600 perms
- `whoami-token` kaldes ved startup — hvis udløbet, auto-refresh via refresh-token
- Hvis refresh også udløbet → wizard genstartes
- **Owner-only håndhæves server-side** — clienten kan ikke omgå det
- Advarsel 7 dage før token-udløb i status bar

### Threat model
- **Lokal maskine kompromitteret:** Token-fil kan læses → angriber har owner-adgang. Mitigation: 0600 perms, kort TTL (30 dage), manual rotation.
- **Token lækket:** Rotate `jarvisx_auth_secret` i runtime.json → alle tokens dør. Panic button.
- **Man-in-the-middle:** Local mode = localhost, ingen MITM. Remote mode: brug HTTPS med `--ca-cert` flag.

---

## 4. TUI Arkitektur

### Tech stack
- **Textual** (v4+) — async TUI framework, bygget på Rich
- **Rich** (v13+) — farve, tabeller, panels, syntax highlighting, markdown rendering, animation
- **httpx** (v0.27+) — async HTTP klient (REST + SSE)
- **PyJWT** (v2.8+) — token-verifikation (allerede runtime-dep)

### Layout — 3-panel split

```
┌─────────────────────────────────────────────────────────────────┐
│  ◈ CENTRAL — J.A.R.V.I.S CLI v1.0    [● CONNECTED]  14:32:05   │
├──────────────────────┬──────────────────────────────────────────┤
│                      │                                          │
│  LIVE FEED           │  COMMAND OUTPUT                          │
│  (SSE / poll)        │  (Rich-rendered panels/tables)           │
│                      │                                          │
│  ● network/health    │  ┌─ STATUS ─────────────────────────┐   │
│  ● infra/pfsense     │  │ 🟡 GUL  | 122 nerver | 21 clusters│   │
│  ● cognition/learn   │  │ 0 breakers | 12 incidents         │   │
│  ● memory/store      │  │ 28 anomalier (23 med, 5 low)      │   │
│  ● execution/run     │  └──────────────────────────────────┘   │
│  ...                 │                                          │
│                      │  > central> _                            │
├──────────────────────┴──────────────────────────────────────────┤
│  central> status    │  ← COMMAND BAR (REPL prompt)              │
└─────────────────────────────────────────────────────────────────┘
```

### Paneler

**1. Live Feed (venstre, ~30% bredde)**
- **Default: polling** hvert 2-3s fra `/central/realtime` (undgår single-worker SSE-blokering)
- **SSE opt-in** via `--sse` flag eller config (for når API'en kører med multiple workers)
- Hver nerve-fire vises som: `● cluster/nerve · decision`
- Farvekodet: grøn=observe, gul=degraded, rød=error, blå=info
- Auto-scroll, men kan pauses med `p`
- Viser seneste 200 fyringer, ældste scroller ud
- **Animation:** ny fyring glider ind fra toppen med en kort fade-in (Rich animation)
- **Puls:** status-farve i header pulserer langsomt (2s cyklus) når status = 🟡 GUL eller 🔴 RØD

**2. Command Output (højre, ~70% bredde)**
- Rich-rendered panels, tabeller, træer, markdown
- Overskrives ved ny kommando (eller `watch` mode)
- Paginering ved lange output (Space = næste side, q = afslut)
- **Animation:** panel-overgange har en kort horisontal wipe-effekt
- Syntax highlighting af JSON, Python, SQL output

**3. Command Bar (bund, fuld bredde)**
- REPL prompt: `central> `
- Command history: ↑/↓ navigation, gemmes i `~/.jarvis-v2/state/central_cli_history` (max 500)
- Tab-completion på kommandoer + argumenter
- `Ctrl+L` — clear output panel
- `Ctrl+R` — force refresh af live feed
- `F1` — help overlay
- `Esc` — cancel current operation / exit watch mode

### Boot-sekvens (animeret)

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    ◈  J.A.R.V.I.S — CENTRAL CLI                             ║
║                                                              ║
║    Initializing...                                           ║
║    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%              ║
║                                                              ║
║    ✓ Token validated                                         ║
║    ✓ API connected (127.0.0.1:8080, 12ms)                   ║
║    ✓ Central: 122 nerver, 21 clusters                       ║
║    ✓ Status: 🟡 GUL                                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

- Progress bar animeres (Rich Progress)
- Hvert check vises med ✓ (grøn) eller ✗ (rød) efterhånden som det fuldføres
- Boot kan springes over med `--no-boot` flag
- `--script` mode: ingen TUI, kun output (til pipes/automation)

---

## 5. J.A.R.V.I.S Æstetik

### Farvepalet (mørk baggrund, truecolor)

| Farve | Hex | Brug |
|---|---|---|
| **Cyan** | `#00d4ff` | Primær accent, headers, borders, prompt |
| **Amber** | `#ffb000` | Advarsler, warnings, medium severity |
| **Red** | `#ff4444` | Errors, critical, rød status |
| **Green** | `#00ff88` | Success, grøn status, observe |
| **Dim gray** | `#444444` | Sekundær tekst, borders |
| **White** | `#ffffff` | Primær tekst |
| **Blue** | `#4488ff` | Info, info-severity |
| **Magenta** | `#ff00ff` | Diagnostisk, special highlight |

### Animationer & effekter

**Boot:**
- Progress bar med glidende fill (Rich Progress, bar_style cyan)
- Checkmarks animeres ind én ad gangen med 200ms delay
- Boot-box har en subtil glow-effekt (cyan border der pulserer)

**Live Feed:**
- Nye nerve-fyringer glider ind fra toppen (Rich animation, 150ms)
- Kritiske fyringer har en kort rød blink-effekt (2 blinks, 100ms)
- Status-farve i header pulserer langsomt ved 🟡/🔴 (2s cyklus)

**Command Output:**
- Panel-overgange: horisontal wipe (100ms)
- Tabeller: rækker fades ind top-til-bund ved paginering
- JSON output: syntax highlighted med cyan keys, green strings, amber numbers

**Status Bar (bund):**
- Connection indicator: `●` grøn (connected), `●` rød (disconnected), `●` gul (reconnecting)
- Klokke opdateres hvert sekund
- Token-udløb: amber advarsel 7 dage før, rød 1 dag før

**Kommando-feedback:**
- Succesfuld kommando: kort grøn flash på command bar (200ms)
- Fejl: rød flash + fejl-besked i output panel
- Write-kommandoer (toggle, resolve): amber confirmation flash + "✓ done"

### Accessibility
- Ikke kun farve-kodning — også ikoner: `●` (aktiv), `○` (inaktiv), `▲` (high), `▼` (low)
- Farver har tilstrækkelig kontrast mod mørk baggrund (WCAG AA)
- `--no-color` flag for monokrom terminal
- `--high-contrast` flag for øget kontrast

### Tema
- Default: **J.A.R.V.I.S Dark** (mørk baggrund, cyan accent)
- `--theme light` — lys baggrund variant (til sollysfyldte skærme)
- Tema gemmes i config

---

## 6. Kommandoer

### Core kommandoer (genbruger central_terminal.py parser)

| Kommando | Beskrivelse | Output |
|---|---|---|
| `status` | Central status | Panel med farve, nerver, clusters, incidents, anomalier |
| `clusters` | Cluster oversigt | Tabel med cluster + status + nerve count |
| `incidents` | Uresolverede incidents | Tabel med ID, tid, cluster, nerve, severity, besked |
| `incidents --filter network` | Filtrerede incidents | Filtreret tabel (erstatter pipes i v1) |
| `trace [cluster]` | Trace buffer | Tabel med seneste fyringer for cluster |
| `nerve <name>` | Nerve detail | Panel med nerve info + spor + on/off |
| `toggle <nerve>` | Tænd/sluk nerve | Confirmation + ny state |
| `scan` | Anomali oversigt | Tabel med signaturer + count + priority |
| `instrument` | Instrument-panel | Tabel med instrument-metrikker |
| `resolve <id>` | Løs incident | Confirmation |
| `daemons` | Daemon oversigt | Tabel med daemon + cadence + last_run + status |
| `model` | Model config | Panel med model + provider + state |
| `learning` | Lærings-status | Panel med memos + hypoteser + samples |
| `drift` | Drift-status | Panel med drift-metrikker |
| `breakers` | Circuit breakers | Tabel med breaker + state + count |
| `autonomy` | Autonomi-status | Panel med autonomy-pressure + signals |
| `providers` | Provider health | Tabel med provider + ping + drift |

### Udvidede kommandoer (CLI-specifikke)

| Kommando | Endpoint | Beskrivelse |
|---|---|---|
| `diag` | `/central/diagnostics` | Fuldt diagnostik-panel (incidents + anomalier + root causes) |
| `mind [tab]` | `/central/mind` | Jarvis Mind-hub (alle faner eller specifik) |
| `overview` | `/mc/overview` | Mission Control overview |
| `costs` | `/mc/costs` | Omkostninger (daglig/uge/måned) |
| `runs` | `/mc/runs` | Kørsler |
| `approvals` | `/mc/approvals` | Afventende godkendelser |
| `initiatives` | `/mc/initiatives` | Initiativer |
| `self` | `/mc/jarvis` | Selv-model |
| `cognitive` | `/mc/cognitive-frame` | Kognitiv ramme |
| `signals` | `/mc/emergent-signals` | Emergente signaler |
| `embodied` | `/mc/embodied-state` | Legamlig tilstand |
| `affective` | `/mc/affective-meta-state` | Affektiv meta-tilstand |
| `cadence` | `/mc/internal-cadence` | Intern kadence |
| `liveness` | `/mc/liveness` | Live-status |
| `memory` | `/mc/memory-pipeline` | Hukommelses-pipeline |
| `tasks` | `/mc/scheduled-tasks` | Planlagte opgaver |
| `workspace list` | `/api/workspace/list` | Workspaces |
| `workspace read <file>` | `/api/workspace/read` | Læs workspace-fil |
| `channels` | `/api/channels/state` | Gateway-status |
| `whoami` | `/api/auth/whoami-token` | Token-inspektion |
| `watch <command>` | (poller) | Genkør kommando hvert 5s, Esc stopper |

### Kommando-syntaks
- `command [args] [--flags]`
- `--filter <text>` erstatter pipes i v1 (fx `incidents --filter network`)
- `--json` — rå JSON output (til scripting)
- `--verbose` — debug-level output
- `help [command]` — hjælp

---

## 7. Fejlhåndtering

### Fejl-kategorier

| Kategori | Årsag | Handling | Visning |
|---|---|---|---|
| **Connection** | API nede, netværk | Auto-retry 3x (1s, 2s, 4s) | Rød banner + retry status |
| **Auth** | Token udløbet/ugyldig | Auto-refresh → hvis fail, wizard | Amber banner + instruktion |
| **Permission** | 403 Forbidden | Ingen retry | Rød fejl: "owner-only" |
| **Server** | 500, timeout | Auto-retry 1x | Rød fejl + server detaljer |
| **Client** | Ukendt kommando, forkerte args | Ingen retry | Amber fejl + help hint |

### SSE/Polling fejl
- **Polling default:** hvis poll fejler 3 gange → vis "● DISCONNECTED" + auto-retry hvert 5s
- **SSE mode:** hvis stream afbrydes (fx uvicorn keep-alive 120s) → auto-reconnect med backoff (1s, 2s, 5s, 10s, 30s)
- **Graceful degradation:** hvis live feed er nede, virker kommandoer stadig (REST)

### Edge cases

| Case | Håndtering |
|---|---|
| API nede ved startup | Boot viser ✗, clienten venter med reconnect-hint |
| Token udløbet | Auto-refresh → hvis fail, vis wizard-instruktion |
| Stor output (1000+ incidents) | Paginering, max 50 rækker pr side |
| Security nerve toggle | Amber confirmation prompt: "Tænd/sluk <nerve>? (y/n)" |
| Timeout (30s default) | "Timeout — prøv igen eller brug --timeout 60" |
| Terminal for smal | Min 80 kolonner, vis advarsel hvis < 80 |
| Ctrl+C / SIGINT | Luk SSE → vent in-flight (max 3s) → gem history → exit |
| SIGTERM | Force quit (ingen ventetid) |

---

## 8. Logging & Audit

- **Log fil:** `~/.jarvis-v2/logs/central_cli.log` med rotation (5 MB, 3 backups)
- **Audit-log:** alle write-kommandoer (toggle, resolve, depromote) logges med timestamp + kommando + resultat
- **Verbose:** `--verbose` for debug-level, ellers INFO
- **Token redaction:** token **aldrig** i logs (altid `[REDACTED]`)
- **Command history:** `~/.jarvis-v2/state/central_cli_history` (max 500 kommandoer)

---

## 9. Konfiguration

### Config fil: `~/.jarvis-v2/config/central_cli.json`

```json
{
  "api_url": "http://127.0.0.1:8080",
  "mode": "local",
  "token": "[REDACTED]",
  "refresh_token": "[REDACTED]",
  "token_expires": "2026-08-04T12:00:00Z",
  "owner_discord_id": "123456789",
  "theme": "jarvis-dark",
  "sse": false,
  "poll_interval_s": 3,
  "boot_animation": true,
  "history_max": 500
}
```

- 0600 perms på filen
- `--config <path>` flag for alternativ config
- Miljøvariabler: `CENTRAL_CLI_TOKEN`, `CENTRAL_CLI_API_URL`

---

## 10. Installation

### Metode 1: pip install (anbefalet)
```bash
cd /media/projects/jarvis-v2
pip install -e apps/central_cli/
```
Dette installerer et `central` entry point via `pyproject.toml` `[project.scripts]`.

### Metode 2: symlink (hurtigt)
```bash
ln -s /media/projects/jarvis-v2/apps/central_cli/central.py /usr/local/bin/central
chmod +x /media/projects/jarvis-v2/apps/central_cli/central.py
```

### Brug
```bash
central              # Start TUI (local mode auto-detected)
central --remote http://10.0.0.39:8080   # Remote mode
central --sse         # Brug SSE i stedet for polling
central --no-boot     # Skip boot animation
central --script status --json   # Script mode, rå JSON
central --theme light # Lys tema
```

---

## 11. Filstruktur

```
apps/central_cli/
├── pyproject.toml          # Package + entry point
├── README.md               # Installation + brug
├── central_cli/
│   ├── __init__.py
│   ├── main.py             # Entry point, arg parsing, boot
│   ├── config.py           # Config læs/skriv, token-håndtering
│   ├── auth.py             # Token mint/refresh/validate, wizard
│   ├── client.py           # HTTP klient (httpx), SSE/polling
│   ├── commands.py         # Kommando-parser (genbruger central_terminal.py logik)
│   ├── renderer.py         # Rich/Textual output-formattering
│   ├── theme.py            # J.A.R.V.I.S farvepalet + animationer
│   ├── tui.py              # Textual TUI app (3-panel layout)
│   ├── feed.py             # Live feed widget (SSE/polling)
│   └── utils.py            # Helpers (time format, truncation, etc.)
├── tests/
│   ├── test_config.py      # Token gem/læs/valider/refresh/udløb
│   ├── test_commands.py    # Kommando-parser, alle kommandoer, forkerte args
│   ├── test_renderer.py    # Output-formatter, tabeller, panels, fejl
│   ├── test_auth.py        # Auth-flow, token-refresh, wizard
│   ├── test_feed.py        # SSE-parser, keepalive, reconnect, polling
│   ├── test_integration.py # Forbind til rigtig API, kør kommandoer
│   └── test_edge.py        # API nede, token udløbet, stor output, timeout
└── central_cli.json        # Default config template
```

### Relation til eksisterende kode

- **`central_terminal.py`** → CLI'en genbruger dens command-parser som backend-lag. Ingen duplikeret logik. central_terminal.py forbliver som parser, CLI'en bliver TUI-laget oven på.
- **`CentralPanel.tsx`** → slettes fra CodeView. Erstattes af `CentralBadge.tsx`.
- **`CentralHud.tsx`** → slettes fra CoworkView. Erstattes af `CentralBadge.tsx`.
- **`centralStream.ts`** → slettes. Ingen SSE i jarvis-desk mere.

---

## 12. Test-plan

### Unit tests
- Token-håndtering: gem, læs, valider, refresh, udløb
- Kommando-parser: alle kommandoer, forkerte args, ukendte kommandoer
- Output-formatter: tabeller, panels, fejl-beskeder, animationer
- SSE-parser: keepalive, reconnect, malformed data
- Config: læs, skriv, valider, migrate

### Integration tests
- Forbind til rigtig API, kør `status`, verificer output
- SSE-stream i 30s, verificer at fyringer vises
- Toggle nerve, verificer at state ændres
- Auth-flow: udløbet token → refresh → fortsæt
- Polling mode: 3 polls, verificer data opdateres

### Edge tests
- API nede → connection error + retry
- Token udløbet → auto-refresh → wizard
- Stor output (1000+ incidents) → paginering
- Security nerve toggle → confirmation prompt
- Timeout → fejl-besked
- Terminal < 80 kolonner → advarsel
- Ctrl+C → graceful shutdown

### Sikkerhedstests
- Token ikke i logs (grep efter token-string i log fil)
- Token-fil har 0600 perms
- 403 ved non-owner token (hvis test-bar)
- Token redaction i verbose mode

---

## 13. Implementationsfaser

### Fase 1: Fundament (config + auth + HTTP + tema)
- `config.py` — config læs/skriv, 0600 perms
- `auth.py` — token mint/refresh/validate, setup-wizard
- `client.py` — httpx HTTP klient, polling mode
- `theme.py` — J.A.R.V.I.S farvepalet + animationer
- `main.py` — arg parsing, boot-sekvens
- Tests: config, auth, client

### Fase 2: Core TUI (3-panel layout + kommandoer)
- `tui.py` — Textual 3-panel app
- `feed.py` — live feed widget (polling default)
- `commands.py` — kommando-parser (genbruger central_terminal.py)
- `renderer.py` — Rich output-formattering
- Tests: commands, renderer, feed

### Fase 3: Udvidede kommandoer + SSE
- Udvidede kommandoer (diag, mind, MC, workspace, channels)
- SSE mode (`--sse` flag)
- `watch` kommando
- Tab-completion
- Command history
- Tests: integration, SSE

### Fase 4: Polish + jarvis-desk nedgradering + tests
- Edge cases + graceful shutdown
- `CentralBadge.tsx` — let status-badge til jarvis-desk
- Fjern `CentralPanel.tsx` + `CentralHud.tsx` + `centralStream.ts` fra jarvis-desk
- Installation (pip + symlink)
- Sikkerhedstests
- README

---

## 14. Versionshåndtering

- Clienten kalder `/central/realtime` ved startup — bekræfter at API'en lever
- Viser client-version + API connection-status i status bar
- Ukendte felter i JSON-responses ignoreres graceful (forward-compatible parsing)
- Ingen separat `/api/version` endpoint nødvendigt

---

## 15. Fremtidige udvidelser (post-v1)

- **Pipes:** `incidents | grep network | sort --severity` — intern pipe-parser med built-in grep/sort/wc
- **Multi-nerve watch:** `watch nerve network/health cognition/learn` — flere nerver samtidig
- **Alerting:** Konfigurerbare thresholds med desktop-notification ved kritiske hændelser
- **SIGHUP reload:** Genindlæs config uden genstart
- **Plugin system:** Brugerdefinerede kommandoer via plugins
- **Dark/light auto-switch:** Følger terminal-tema
- **tmux integration:** `central tmux` — åbn i tmux-pane med præ-konfigureret layout
- **Export:** `status --export json/csv` — eksportér data til fil