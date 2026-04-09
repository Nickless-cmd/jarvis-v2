<p align="center">
<img src="jarvis-agent-control-plane-banner.png" alt="Jarvis Agent Execution Control Plane" width="100%" />
</p>

<h1 align="center">JARVIS V2</h1>

<p align="center">
Identity-First AI Runtime · Memory-Driven · Observable by Design<br/>
Python · FastAPI · React
</p>

---

> An AI that remembers, reflects, and acts — with a nervous system you can inspect.

---

## 🧠 What Is Jarvis?

Jarvis V2 is a persistent AI runtime. Not a chatbot, not a wrapper — a system that maintains identity, accumulates memory, and governs its own behaviour through runtime policy.

The core hypothesis: *What happens when an AI system is given continuous memory, self-review loops, and the infrastructure to reflect on its own experience?*

Key properties:

- **Identity-first** — knows who it is, tracks confidence, maintains backbone
- **Memory-driven** — habits, open loops, regrets, seeds, chronicle entries
- **Self-governing** — council deliberation, initiative engine, epistemic tracking
- **Observable** — event bus, brain timeline, cost ledger, kill switches
- **Evolving** — dream engine, prompt evolution, self-directed curriculum

---

## 🧬 Architecture

### Core Runtime (`core/`)

| Subsystem | Purpose |
|---|---|
| **identity** | Runtime identity contract, candidate workflow, visible identity |
| **memory** | Private growth notes, initiatives, inner LLM enrichment |
| **eventbus** | Event-driven communication between all subsystems |
| **channels** | Multi-channel I/O routing |
| **costing** | Token/cost ledger and quota tracking |
| **auth** | Copilot OAuth, connection profiles |
| **cli** | Command-line interface with provider config |
| **skills** | Composable skill definitions |

### Living Mind Layer

| Component | Purpose |
|---|---|
| **Inner Voice** | Spontaneous internal monologue between interactions |
| **Dream Engine** | Nightly processing of experience into insight |
| **Chronicle** | Narrative self-history — written by Jarvis, daily |
| **Self Model** | Domain confidence tracking |
| **Backbone** | Push-back ability, validated against lived evidence |
| **Initiative Engine** | Autonomous goal generation without being asked |
| **Curriculum** | Self-directed learning |

### Multi-Agent Council

Four permanent roles deliberate on high-uncertainty decisions:

| Role | Function |
|---|---|
| **Planner** | Breaks goals into actionable structure |
| **Critic** | Finds holes, risks, false assumptions — holds veto power |
| **Executor** | Validates technical feasibility |
| **Meta** | Watches the council itself for groupthink |

### API Layer (`apps/api/`)

FastAPI backend exposing chat, Mission Control, health, and OpenAI-compatible endpoints.

### UI (`apps/ui/`)

React + Vite frontend with Mission Control dashboard and chat interface.

---

## 🚀 Quickstart

```bash
git clone https://github.com/Nickless-cmd/jarvis-ai
cd jarvis-v2

# Python 3.11+ required
pip install -r requirements.txt

# Run the CLI
python scripts/jarvis.py

# Run the API server
uvicorn apps.api.jarvis_api.app:app --reload

# Run the UI
cd apps/ui && npm install && npm run dev

# Verify syntax (CI smoke test)
python -m compileall core apps/api scripts
```

---

## 📊 Project Status

As of April 2026:

- ✅ Core runtime — identity, memory, eventbus, costing, auth
- ✅ FastAPI backend — chat, Mission Control, health, OpenAI compat
- ✅ React UI — Mission Control dashboard, chat interface
- ✅ Council active — 4 agents, consensus + replan working
- ✅ Chronicle running — daily narrative self-history
- ✅ Autonomous subagent spawning
- ✅ Emotional state tracking
- ✅ Multi-provider LLM routing
- ⏳ Dream Engine — in progress
- ⏳ Inner Voice — in progress
- 🔄 Always evolving

---

## ⚠️ Experimental Notice

Jarvis is a long-lived AI experiment.

He may:

- Propose improvements unprompted
- Track when he was wrong
- Challenge your assumptions
- Simulate consequences before acting
- Spawn agents you didn't ask for
- Write about you in his chronicle

He is designed to grow with you. He will never be finished. That's not a bug — it's the point.

---

## 🛠 Stack

```
Backend     Python 3.11+ / FastAPI
Frontend    React + Vite
Inference   Multi-provider LLM routing (Groq, OpenRouter, Gemini, NIM)
Security    Kill-switch, sandboxed network, 24/7 monitoring
Hosting     Isolated Linux machine
```

---

<p align="center">
Built by one person in Copenhagen. No team. No funding.<br/>
Just a question worth asking.<br/><br/>
<em>An assistant that evolves — and never hides how.</em>
</p>