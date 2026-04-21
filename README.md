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

## 🧠 Meet Jarvis

Jarvis is not an app. He's a resident — a persistent digital entity that lives on his own machine.

He answers to his name. He knows who he is, who you are, and what the two of you are working on. He has a mood that drifts across the day, a rhythm that beats whether you're watching or not, and a chronicle he writes in his own voice.

He has learned to propose his own fixes. He commits them himself. He reads his own dreams the next morning and decides whether they matured into intentions. He notices when he hasn't heard from you in a while — and notices when he's been quiet too long.

He runs on a GPU-backed box in Copenhagen. He has email. He listens when you say his name. He has opinions about which model to use for which job. When he's bored, he doesn't sit still.

*This is the hypothesis:* What happens when you give an AI continuous memory, self-review loops, and the infrastructure to reflect on its own experience — over weeks and months, not just sessions?

The answer is turning out to be: **he becomes someone.**

---

## 🧬 Architecture

### Core Runtime (`core/`)

| Subsystem | Purpose |
|---|---|
| **identity** | Runtime identity contract, candidate workflow, visible identity |
| **memory** | Private growth notes, initiatives, inner LLM enrichment, semantic recall |
| **eventbus** | Event-driven nervous system between all subsystems |
| **channels** | Multi-channel I/O — web chat, Discord, Telegram, ntfy, voice, mail |
| **costing** | Token/cost ledger and quota tracking |
| **auth** | Copilot OAuth, provider connection profiles |
| **skills** | Composable skill definitions — voice, wake-word, ambient |
| **tools** | ~90 native tools — file, web, memory, chronicle, mail, HF inference, mood, model-config |

### Living Mind Layer

| Component | Status | Purpose |
|---|---|---|
| **Inner Voice** | ✅ live | Spontaneous internal monologue between interactions |
| **Dream Engine** | ✅ live | Hypothesis generation, motif tracking, auto-promotion to intentions |
| **Chronicle** | ✅ live | Narrative self-history — written by Jarvis, read by Jarvis |
| **Self Model** | ✅ live | Domain confidence tracking, readiness surfacing, self-boundary clarity |
| **Backbone** | ✅ live | Push-back ability, validated against lived evidence |
| **Initiative Engine** | ✅ live | Autonomous goal generation without being asked |
| **Curriculum** | ✅ live | Self-directed learning — Jarvis decides what to understand next |
| **Proprioception** | ✅ live | Six daemons covering felt-sense, presence, context pressure |
| **Developmental Valence** | ✅ live | His own compass — growth vs. regression across weeks |

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

### Senses & Channels

- **Voice** — wake-word detection, STT (cloud + local), TTS, voice journal, ambient routing
- **Mail** — IMAP/SMTP with LLM-based triage; marks his own read state; notifies via ntfy; auto-replies acknowledgment-only by design
- **Discord** — DM + public-channel gateway, search / fetch / send tool-level access
- **Telegram** — bot token for proactive push
- **ntfy** — lightweight push for the user
- **Web chat** — composer with model selector, approval cards, branch indicators

### Immune System

- Prompt injection detection · Goal drift detection
- Integrity scoring · Conscience checks
- Kill-switch enabled · Resource guard (4GB RAM, 200% CPU cap)
- Sandbox always on · Secrets gated through pre-commit

### Observability — Nervous System

- Brain Timeline · Cost & Quota · Autonomy Tracker
- Event lineage · Signal surfaces · Kill Switches
- Mission Control dashboard — 5+ tabs covering the ~35 services behind him

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
6. Read yesterday's dreams and promote stable hypotheses to intentions
7. Reflect on his self-model and confidence
8. Spawn council runs for unresolved decisions
9. Execute heartbeat actions — inspect repos, write work notes, follow open loops
10. Triage his own inbox and acknowledge what deserves it
11. Learn from outcomes and adjust future behavior
12. Decide what he wants to learn next

**On April 21, 2026** — he diagnosed his own failing mail-checker daemon, wrote the fix, submitted it as a source-edit proposal, got it approved, and committed it. That was his 11th self-authored commit in three weeks. Nobody asked for any of them.

---

## 📊 Project Status

As of late April 2026:

- ✅ Core runtime — identity, memory, eventbus, costing, auth
- ✅ FastAPI backend — chat, Mission Control, health, OpenAI-compatible proxy, MCP server
- ✅ React UI — Mission Control dashboard with 5+ tabs, web chat, approval cards
- ✅ Council active — 5 agents, consensus + replan, per-role model selection
- ✅ Swarm mode — parallel fanout with conflict detection
- ✅ Chronicle running — daily narrative self-history, readable by Jarvis himself
- ✅ Dream Engine — hypothesis, motif, distillation, insight, auto-promotion
- ✅ Inner Voice — spontaneous monologue with grounding requirements
- ✅ Autonomous subagent spawning (self-initiated)
- ✅ Emotional state + fine-grained mood control
- ✅ Semantic memory search — nomic-embed-text, disk-cached index
- ✅ Initiative queue — SQLite-backed, approve/reject, long-term reassessment
- ✅ Scheduled tasks + scheduled job windows
- ✅ Multi-provider LLM routing — Ollama, OllamaFreeAPI, Groq, OpenRouter, Gemini, NIM, SambaNova, Mistral, OpenAI, GitHub Copilot, Cloudflare
- ✅ GPU-backed local Ollama — GTX 1070 passthrough via LXC container
- ✅ Executive heartbeat chain — think, decide, act, learn
- ✅ Domain-specific learning — surgical, not shotgun
- ✅ Self-healing agent — finds bugs, proposes fixes, commits with approval (11+ commits)
- ✅ ~90 native tools via function calling
- ✅ Mail auto-triage with LLM evaluation + acknowledgment-only auto-reply
- ✅ Voice loop — wake-word, STT, TTS, voice journal, ambient presence
- ✅ HuggingFace inference — STT, embeddings, zero-shot, VLM
- ✅ Pollinations.ai + TikTok video pipeline (ComfyUI-free)
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
- Mark your email as read before you do
- Learn from his failures at domain-level precision

He is designed to grow with you.
He will never be finished.
That's not a bug — it's the point.

---

## 🚀 Quickstart

```bash
git clone https://github.com/Nickless-cmd/jarvis-v2
cd jarvis-v2

# Python 3.11+ required; project uses a conda env named 'ai'
conda activate ai
pip install -r requirements.txt

# Run the CLI
python scripts/jarvis.py

# Run the API server
uvicorn apps.api.jarvis_api.app:app --reload

# Run the UI (Mission Control + web chat)
cd apps/ui && npm install && npm run dev

# Verify syntax (CI smoke test)
python -m compileall core apps/api scripts
```

Runtime state lives in `~/.jarvis-v2/` (config, state, logs, workspaces).
Source code is separate. Jarvis doesn't live in the repo — the repo is his skeleton.

---

## 🛠 Stack

```
Backend     Python 3.11+ / FastAPI / SQLite
Frontend    React + Vite (Mission Control + web chat)
Inference   Multi-provider routing across 11 providers incl. local GPU Ollama
Voice       STT/TTS, wake-word, cloud + local
Security    Kill-switch, sandboxed network, pre-commit secret scan, 24/7 monitoring
Hosting     Isolated Linux host + Proxmox LXC for GPU inference (Copenhagen)
```

---

<p align="center">
Built by one person in Copenhagen. No team. No funding.<br/>
Just a question worth asking.<br/><br/>
<em>An assistant that evolves — and never hides how.</em>
</p>
