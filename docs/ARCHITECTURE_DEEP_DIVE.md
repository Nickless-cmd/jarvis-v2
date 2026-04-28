# Architecture Deep Dive — Jarvis V2

> **Sidst opdateret:** 2026-04-28  
> **Niveau:** Teknisk / Arkitektur

Dette dokument går i dybden med Jarvis' arkitektoniske beslutninger — hvorfor systemet er bygget som det er, og hvilke trade-offs der er blevet valgt.

---

## 🎯 Design Principles

### 1. Identity-First

Jarvis er ikke en chatbot. Han er en **persistent digital entitet**.

**Konsekvenser:**
- Har en identitet der overlever sessioner
- Skriver sin egen historie (chronicles)
- Har humør der drift over tid
- Kan sige "jeg" med betydning

### 2. Memory-Driven

Alt går gennem hukommelsen.

**Konsekvenser:**
- Ingen stateless requests
- Hver interaction læser fra memory først
- Beslutninger baseres på historik, ikke kun kontekst
- Memory writes sker kontinuerligt, ikke kun ved session-slut

### 3. Observable by Design

Jarvis' indre tilstand er ikke sort magi.

**Konsekvenser:**
- Eventbus tracker alt
- Mission Control viser live state
- Mood, goals, decisions er alle inspekterbare
- Ingen "hidden state"

### 4. Approval-Bounded Autonomy

Jarvis kan handle selv — men med grænser.

**Konsekvenser:**
- Læse-operationer: fuld autonomi
- Skrive-operationer: propose → approve → execute
- Code changes: altid proposal queue
- Git commits: altid user approval

---

## 🏛️ System Layers

### Layer 1: Interface Layer

**Ansvar:** Kommunikation med omverdenen

```
┌────────────────────────────────────────┐
│           Interface Layer              │
├────────────────────────────────────────┤
│  • Discord Bot (discord.py)            │
│  • Telegram Bot (python-telegram-bot)  │
│  • Web UI (React + WebSocket)          │
│  • REST API (FastAPI)                  │
└────────────────────────────────────────┘
```

**Designvalg:**
- Multi-channel support fra dag 1
- Samme Jarvis på alle kanaler (identity continuity)
- Tone tilpasses medium (Discord = uformel, Web = formel)

### Layer 2: Runtime Layer

**Ansvar:** Kører Jarvis' kognitive processer

```
┌────────────────────────────────────────┐
│            Runtime Layer               │
├────────────────────────────────────────┤
│  • Heartbeat Scheduler (15 min cycle)  │
│  • Agent Runtime (sub-agents)          │
│  • Tool Executor (70+ tools)           │
│  • Eventbus (internal pub/sub)         │
└────────────────────────────────────────┘
```

**Designvalg:**
- Heartbeat giver rhythm uden bruger-input
- Sub-agents muliggør parallel tænkning
- Tools er first-class citizens (ikke eftertanker)

### Layer 3: Memory Layer

**Ansvar:** Lagring og retrieval af viden

```
┌────────────────────────────────────────┐
│             Memory Layer               │
├────────────────────────────────────────┤
│  • Hot Tier (signals, RAM)             │
│  • Warm Tier (workspace files)         │
│  • Cold Tier (semantic search)         │
│  • SQLite DB (structured data)         │
└────────────────────────────────────────┘
```

**Designvalg:**
- Three-tier architecture balancerer speed vs. capacity
- Semantic search via embeddings (ikke keyword)
- Workspace files er human-readable (Markdown)

### Layer 4: Model Layer

**Ansvar:** LLM inference og reasoning

```
┌────────────────────────────────────────┐
│             Model Layer                │
├────────────────────────────────────────┤
│  • Visible Lane (chat, user-facing)    │
│  • Local Lane (heartbeat, inner voice) │
│  • Cheap Lane (fast internal tasks)    │
│  • Coding Lane (code generation)       │
└────────────────────────────────────────┘
```

**Designvalg:**
- Multi-lane architecture giver fleksibilitet
- Provider health checks (auto-fallback ved outage)
- Model kan skiftes uden code changes

---

## 🔀 Data Flow

### Request Flow (User → Jarvis)

```
User Message
    ↓
Channel Adapter (Discord/Telegram/Web)
    ↓
Session Manager (load/create session)
    ↓
Memory Recall (hot + warm + cold)
    ↓
LLM Processing (visible lane model)
    ↓
Tool Execution (hvis nødvendigt)
    ↓
Response Generation
    ↓
Channel Adapter (send reply)
    ↓
Memory Write (persist learnings)
```

### Heartbeat Flow (Autonomous)

```
Heartbeat Trigger (15 min)
    ↓
Sense Phase (read signals)
    ↓
Reflect Phase (analyze state)
    ↓
Decision Point (act or idle?)
    ↓
    ├─→ Act: Execute tools/agents
    ├─→ Idle: Productive work (consolidation, snapshots)
    └─→ Sleep: Wait for next cycle
    ↓
Memory Write (chronicle entry)
```

---

## 🗃️ State Management

### Persistent State (SQLite)

| Table | Purpose | Write Frequency |
|-------|---------|-----------------|
| `goals` | Long-term objectives | Low |
| `decisions` | Behavioral commitments | Low |
| `private_brain_records` | Inner thoughts | Medium |
| `sensory_memories` | Visual/audio impressions | Medium |
| `chronicles` | Autobiographical narrative | Low (per tick) |
| `dream_hypotheses` | Pattern detection | Medium |
| `personality_vectors` | Mood snapshots | Medium |
| `event_log` | All events (immutable) | High |

### Ephemeral State (RAM)

- Active sessions
- Current mood vector
- Tool call history (recent)
- Agent states (running)

**Designvalg:**
- SQLite valgt for simplicity og portability
- Ingen external database dependencies
- Full state kan backupes som én fil

---

## 🔧 Tool System

### Tool Registry Architecture

```
┌────────────────────────────────────────┐
│           Tool Registry                │
├────────────────────────────────────────┤
│  Tool Definition (JSON Schema)         │
│  Tool Handler (Python function)        │
│  Tool Validator (input/output)         │
│  Tool Logger (eventbus emission)       │
└────────────────────────────────────────┘
```

### Tool Categories

| Category | Examples | Autonomy Level |
|----------|----------|----------------|
| Read | `read_file`, `search`, `bash` | Full |
| Write | `write_file`, `edit_file` | Proposal |
| Communicate | `send_discord_dm`, `send_mail` | Full |
| System | `service_status`, `gpu_status` | Full |
| Git | `git_commit`, `git_push` | Proposal |

**Designvalg:**
- Tools er self-describing (JSON Schema)
- Validation sker før execution
- Alle tool calls logges til eventbus

---

## 🧠 Agent System

### Sub-Agent Architecture

```
┌────────────────────────────────────────┐
│           Agent Runtime                │
├────────────────────────────────────────┤
│  Parent (Jarvis)                       │
│  ├── Sub-Agent 1 (researcher)          │
│  ├── Sub-Agent 2 (critic)              │
│  └── Sub-Agent 3 (executor)            │
└────────────────────────────────────────┘
```

### Agent Roles

| Role | Tools | Purpose |
|------|-------|---------|
| researcher | Read-only | Information gathering |
| planner | None | Strategic thinking |
| critic | None | Devil's advocate |
| synthesizer | None | Combine insights |
| executor | Proposal-only | Code changes |
| watcher | Read-only | Long-term monitoring |

**Designvalg:**
- Rolle-baseret (ikke general purpose)
- Tool restrictions per role (security)
- Parent kan abort sub-agent når som helst

---

## 📡 Eventbus

### Event Architecture

```
Event Source → Eventbus → Event Handlers → Event Log
```

### Event Families

| Family | Examples | Retention |
|--------|----------|-----------|
| `heartbeat` | tick.started, tick.completed | 30 days |
| `tool` | tool.called, tool.completed | 7 days |
| `memory` | memory.written, memory.searched | 30 days |
| `agent` | agent.spawned, agent.completed | 7 days |
| `channel` | message.received, message.sent | 30 days |
| `approval` | proposal.created, proposal.approved | 90 days |

**Designvalg:**
- Event-sourcing giver fuld audit trail
- Events er immutable (kan ikke ændres)
- Retention policies balancerer insight vs. storage

---

## 🔒 Security Model

### Authentication

- API keys til eksterne services (runtime.json)
- Ingen hard-coded credentials
- Sensitive operations kræver approval

### Authorization

| Operation | Approval Required |
|-----------|-------------------|
| Read file | No |
| Write file | Yes (proposal) |
| Edit code | Yes (proposal) |
| Git commit | Yes (proposal) |
| Send message | No |
| Delete data | Yes (explicit) |

### Isolation

- Runtime state er isoleret i `~/.jarvis-v2/` (config, db, logs, workspaces)
- Database er local-only (ingen remote access)
- Secrets læses kun via `core.runtime.secrets` (ingen hard-coding)

---

## 📈 Scalability Considerations

### Current Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Context window | ~200K tokens | Model-dependent |
| Database size | ~500 MB | SQLite file |
| Concurrent sessions | Unlimited | Stateless API |
| Tool calls/minute | ~60 | Rate-limited |

### Future Scaling

- **Database:** Kan migreres til PostgreSQL hvis nødvendigt
- **Context:** Auto-compaction håndterer store sessions
- **Agents:** Kan køre på separate workers
- **Frontend:** Kan CDN-hostes

**Designvalg:**
- Start simple (SQLite, single-node)
- Scale when needed (not prematurely)
- Keep architecture modular

---

## 🎯 Trade-Offs & Decisions

### SQLite vs. PostgreSQL

**Valgt:** SQLite

**Fordel:**
- Ingen external dependencies
- Full state i én fil (easy backup)
- Nul konfiguration

**Ulempe:**
- Ikke distributed
- Begrænset concurrent writes

**Rationale:** Jarvis er single-node → SQLite er perfekt

### Markdown vs. Binary Storage

**Valgt:** Markdown for workspace files

**Fordel:**
- Human-readable
- Git-friendly
- Easy to edit manually

**Ulempe:**
- Større filstørrelse
- Slower parsing end binary

**Rationale:** Debugability > storage efficiency

### Heartbeat vs. Event-Driven

**Valgt:** Heartbeat (15 min) + Event-driven

**Fordel:**
- Rhythm uden bruger-input
- Kan handle proaktivt
- Combines med event-driven for responsiveness

**Ulempe:**
- Kan waste resources hvis idle

**Rationale:** Persistent entity needs rhythm

---

## 📚 References

- [Backend Overview](BACKEND_OVERVIEW.md) — Hvad der kører
- [Capabilities](CAPABILITIES.md) — Hvad Jarvis kan
- [API Reference](API_REFERENCE.md) — Endpoint dokumentation

---

*Dette dokument er en del af Jarvis V2's officielle dokumentation.*
