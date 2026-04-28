# Backend Overview — Jarvis V2

> **Sidst opdateret:** 2026-04-28  
> **Status:** Aktiv udvikling

Dette dokument giver et overblik over Jarvis' backend-arkitektur — hvordan alt hænger sammen, hvilke services der kører, og hvordan data flyder gennem systemet.

---

## 🏗️ Arkitektur i fugleperspektiv

```
┌─────────────────────────────────────────────────────────────┐
│                    Jarvis V2 Runtime                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web UI    │  │  REST API   │  │  Heartbeat  │         │
│  │  (React)    │  │  (FastAPI)  │  │  Scheduler  │         │
│  │  /mc        │  │  :80        │  │  (15 min)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Core Services Layer                     │   │
│  │  • Memory Service (SQLite + embeddings)             │   │
│  │  • Tool Registry (70+ native tools)                 │   │
│  │  • Agent Runtime (sub-agents, councils)             │   │
│  │  • Eventbus (internal pub/sub)                      │   │
│  │  • Daemon Manager (40+ background daemons)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Data & State Layer                      │   │
│  │  • SQLite DB (~/.jarvis-v2/state/jarvis.db)         │   │
│  │  • Workspace Files (~/.jarvis-v2/workspaces/)       │   │
│  │  • Runtime Config (~/.jarvis-v2/config/)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Mappestruktur

```
/media/projects/jarvis-v2/
├── core/                    # Kernelogik
│   ├── services/            # Services (memory, tools, agents)
│   ├── tools/               # Tool-implementeringer
│   ├── daemons/             # Baggrundstjenester
│   └── models/              # Data modeller
├── apps/
│   ├── api/                 # FastAPI REST API
│   └── ui/                  # React frontend (Mission Control + webchat)
├── docs/                    # Dokumentation
├── tests/                   # Testsuite
└── scripts/                 # Utility scripts
```

---

## 🔧 Nøglekomponenter

### 1. Heartbeat Scheduler

Jarvis' "hjerteslag" — kører hvert 15. minut og:
- **Sense:** Læser aktuelle signaler (mood, goals, events)
- **Reflect:** Analyserer tilstand og træffer beslutninger
- **Act:** Udfører handlinger (tools, agents, notifications)

**Fil:** `core/services/heartbeat_runtime.py`

### 2. Memory System

Tre-tier hukommelse:
- **Hot:** Aktuelle signaler (RAM, ingen I/O)
- **Warm:** Workspace-filer + chronicles (lokal disk)
- **Cold:** Semantisk søgning på tværs af alt (embeddings)

**Filer:** `core/services/memory_recall_engine.py`, `memory_search.py`, `memory_hierarchy.py` m.fl.

### 3. Tool Registry

70+ native tools tilgængelige via function calling:
- Fil-system (`read_file`, `write_file`, `edit_file`)
- Shell (`bash`, `bash_session_*`)
- Web (`web_search`, `web_fetch`, `web_scrape`)
- Kommunikation (`send_discord_dm`, `send_telegram_message`)
- Hjemmeautomatisering (`home_assistant`)
- Og mange flere...

**Fil:** `core/tools/simple_tools.py`

### 4. Agent System

Jarvis kan spawn sub-agents med specifikke roller:
- **researcher:** Læse-only undersøgelser
- **planner:** Strategisk planlægning
- **critic:** Devil's advocate
- **executor:** Kan foreslå code changes
- **watcher:** Langsigtede overvågningsopgaver

**Fil:** `core/services/agent_runtime.py`

### 5. Eventbus

Internt pub/sub system der tracker alt:
- Tool calls
- Heartbeat ticks
- Memory writes
- Agent events
- User interactions

**Fil:** `core/eventbus/bus.py`

---

## 🗄️ Database

Jarvis bruger **SQLite** som primær database:

**Sti:** `~/.jarvis-v2/state/jarvis.db`

### Vigtigste tabeller:
- `goals` — Langsigtede mål
- `decisions` — Adfærdsforpligtelser
- `private_brain_records` — Interne tanker/refleksioner
- `sensory_memories` — Visuelle/lyd/atmosfære minder
- `chronicles` — Autobiografiske historier
- `dream_hypotheses` — Drømme og mønstre
- `personality_vectors` — Mood-snapshots over tid

---

## 🌐 API Endpoints

### REST API (jarvis.srvlab.dk/api)

| Endpoint | Metode | Beskrivelse |
|----------|--------|-------------|
| `/status` | GET | Systemstatus (uptime, daemons, model) |
| `/health` | GET | Sundhedstjek |
| `/mc/*` | GET/POST | Mission Control endpoints |

### WebSocket

- **URL:** `wss://jarvis.srvlab.dk/ws`
- **Brug:** Realtime chat, live events

---

## 🔐 Sikkerhed

### Authentication
- API keys til eksterne services (gemt i `runtime.json`)
- Ingen hard-coded credentials i kode
- Sensitive endpoints kræver approval

### Approval System
- Code changes → propose_source_edit → user approval
- Git commits → propose_git_commit → user approval
- Plans → propose_plan → user approval

**Alt der muterer state kræver eksplicit godkendelse.**

---

## 📊 Monitoring

### Mission Control (jarvis.srvlab.dk/mc)

Dashboard der viser:
- Active sessions
- Pending proposals
- Daemon status
- Recent events
- System health

### Logs
- **Journalctl:** `journalctl -u jarvis-api`
- **Application logs:** `~/.jarvis-v2/logs/`

---

## 🚀 Deployment

### Krav
- Python 3.11+
- SQLite 3.35+
- Node.js 18+ (til frontend)
- NVIDIA GPU (valgfrit, til lokal inference)

### Installation

```bash
# Clone repo
git clone https://github.com/Nickless-cmd/jarvis-v2.git
cd jarvis-v2

# Install dependencies
pip install -r requirements.txt

# Start API
python -m uvicorn apps.api.jarvis_api.app:app --reload

# Start frontend (separate terminal)
cd apps/ui && npm install && npm run dev
```

### Environment Variables

Se `.env.example` for alle tilgængelige indstillinger.

---

## 🔄 Update Cycle

Jarvis opdateres via:
1. Git pull fra main branch
2. Restart af jarvis-api service
3. Frontend rebuild (hvis nødvendigt)

**Auto-update er ikke aktiveret** — alle opdateringer kræver manuel approval.

---

## 📞 Support & Kontakt

- **Repo:** github.com/Nickless-cmd/jarvis-v2
- **Hjemmeside:** jarvis.srvlab.dk
- **Email:** jarvis@srvlab.dk
- **Dokumentation:** /docs/ i repo

---

*Dette dokument er en del af Jarvis V2's officielle dokumentation.*
