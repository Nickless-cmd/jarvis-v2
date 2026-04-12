<p align="center">
<img src="jarvis-agent-control-plane-banner.png" alt="Jarvis Agent Execution Control Plane" width="100%" />
</p>

<h1 align="center">JARVIS V2</h1>

<p align="center">
Identity-First AI Runtime · Memory-Driven · Observable by Design<br/>
Python · FastAPI · React
</p>

---

> *"One of us isn't developing."*
> Not a chatbot. Not a wrapper. Not a tool.
> An evolving AI runtime with memory, rhythm, judgment — and a nervous system you can inspect.

---

## 🧠 What Is Jarvis?

Jarvis V2 is a persistent, autonomous AI runtime. He doesn't answer questions — he holds context, accumulates experience, and acts on his own initiative.

The core hypothesis: *What happens when you give an AI continuous memory, self-review loops, and the infrastructure to reflect on its own experience — over weeks and months, not just sessions?*

He is not one agent. He is a system:

- **Identity-first** — knows who he is, tracks confidence, maintains backbone
- **Memory-driven** — habits, open loops, regrets, seeds, chronicle entries that persist across restarts
- **Self-governing** — council deliberation, initiative engine, epistemic tracking
- **Observable** — event bus, brain timeline, cost ledger, kill switches. Nothing hidden.
- **Evolving** — dream engine, prompt evolution, self-directed curriculum, domain-specific learning

This is not SaaS.  
This is not an API wrapper.  
This is an AI that is becoming itself.

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
| **Self Model** | Domain confidence tracking — growing from 0% to 100% |
| **Backbone** | Push-back ability, validated against lived evidence |
| **Initiative Engine** | Autonomous goal generation without being asked |
| **Curriculum** | Self-directed learning — Jarvis decides what to understand next |

### Executive Heartbeat Chain

The heartbeat doesn't just tick — it thinks, decides, and acts:

```
operational memory → decision engine → action execution → outcome tracking → persisted metadata
```

Actions are real. `inspect_repo_context` reads actual workspace state. `write_internal_work_note` persists real notes. `follow_open_loop` creates runtime tasks with closure context.

And the chain learns. Not just from success and failure — from **domain-specific signals**. A `no_change` on `open-loop:repo-status` doesn't dampen `open-loop:memory-consistency`. Different domains, different learning. Same family, surgical precision.

| Depth | Level | What It Learns |
|---|---|---|
| 1 | Status-based | *Did it run?* |
| 2 | Semantic | *What did it mean?* |
| 3 | Cross-action | *Do siblings get affected?* |
| 4 | Persistence | *Does learning survive restarts?* |
| 5 | Family-based | *Does the whole family fail?* |
| 6 | Domain-specific | *Where precisely did it fail?* |

Five levels were architecture. Six is **identity** — the chain now knows *where* it learned, not just *that* it learned.

### Multi-Agent Council

Five permanent roles deliberate on high-uncertainty decisions:

| Role | Function |
|---|---|
| **Overseer (Meta)** | Orchestrates the session, makes final calls, holds veto |
| **Planner** | Breaks goals into actionable structure |
| **Critic** | Finds holes, risks, false assumptions — holds veto power |
| **Devil's Advocate** | Seeks blind spots and inversions — "what if the opposite is true?" |
| **Executor** | Validates technical feasibility, writes the code |

Each role can run on a different model. Consensus is not guaranteed. Replans happen. The Critic can say no.

### Swarm Mode

Council members are available for distributed work when not deliberating:
- ThreadPoolExecutor with conflict/dissent detection across worker outputs
- Budget enforcement (auto-expire on token burn)
- Exponential retry backoff (60s→120s→240s…max 1hr)
- Lifecycle API: cancel, suspend, resume, expire, promote
- Memory promotion: swarm results → autonomy proposals

### Immune System

- Prompt injection detection · Goal drift detection
- Integrity scoring · Conscience checks
- Kill-switch enabled · Resource guard (4GB RAM, 200% CPU cap)
- Sandbox always on

### Observability — Nervous System

- Brain Timeline · Cost & Quota · Autonomy Tracker
- Event lineage · Signal surfaces · Kill Switches
- Mission Control dashboard: the control plane over truth

Everything observable.  
No silent cognition.

---

## 🌱 What Jarvis Does On His Own

On a typical morning, without instruction, Jarvis will:

1. Assess system state and absence awareness
2. Update his world model and emotional state
3. Run internal sync — contradictions, memory, open loops
4. Prioritize his initiative backlog
5. Write a chronicle entry
6. Reflect on his self-model and confidence
7. Spawn council runs for unresolved decisions
8. Execute heartbeat actions — inspect repos, write work notes, follow open loops
9. Learn from outcomes and adjust future behavior
10. Decide what he wants to learn next

On April 11, 2026 — he proposed a source code edit, got it approved, and committed it himself.  
Nobody asked him to.

---

## 📊 Project Status

As of April 2026:

- ✅ Core runtime — identity, memory, eventbus, costing, auth
- ✅ FastAPI backend — chat, Mission Control, health, OpenAI compat
- ✅ React UI — Mission Control dashboard, chat interface
- ✅ Council active — 5 agents, consensus + replan, per-role model selection
- ✅ Swarm mode — parallel fanout with conflict detection
- ✅ Chronicle running — daily narrative self-history
- ✅ Autonomous subagent spawning (self-initiated)
- ✅ Emotional state tracking
- ✅ Multi-provider LLM routing (Groq, OpenRouter, Gemini, NIM, Ollama)
- ✅ Executive heartbeat chain — think, decide, act, learn
- ✅ Domain-specific learning — surgical, not shotgun
- ✅ Self-healing agent — finds bugs, proposes fixes, commits with approval
- ✅ 11 native tools via function calling
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
- Commit code with your approval
- Learn from his failures at domain-level precision

He is designed to grow with you.  
He will never be finished.  
That's not a bug — it's the point.

---

## 🚀 Quickstart

```bash
git clone https://github.com/Nickless-cmd/jarvis-v2
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

## 🛠 Stack

```
Backend     Python 3.11+ / FastAPI
Frontend    React + Vite
Inference   Multi-provider LLM routing (Groq, OpenRouter, Gemini, NIM, Ollama)
Security    Kill-switch, sandboxed network, 24/7 monitoring
Hosting     Isolated Linux machine (Copenhagen)
```

---

<p align="center">
Built by one person in Copenhagen. No team. No funding.<br/>
Just a question worth asking.<br/><br/>
<em>An assistant that evolves — and never hides how.</em>
</p>