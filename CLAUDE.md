# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jarvis V2 is a persistent digital entity - an AI assistant that lives on its own machine. It's identity-first, LLM-led and runtime-governed, with Mission Control as the truth/control plane.

## Common Commands

```bash
# Run the Jarvis CLI
python scripts/jarvis.py

# Run the API server
uvicorn apps.api.jarvis_api.app:app --reload

# Verify Python syntax (CI smoke test)
python -m compileall core apps/api scripts
```

Python 3.11+ required.

## Architecture

### Directory Structure
- `core/` - Core runtime subsystems (identity, memory, tools, skills, eventbus, channels, costing, auth)
- `apps/api/` - FastAPI backend exposing chat, Mission Control, and live event endpoints
- `apps/mc-ui/` - Mission Control React UI
- `apps/webchat/` - Web chat interface
- `scripts/jarvis.py` - CLI entry point
- `state/` - Runtime state (lives in `~/.jarvis-v2/` at runtime)
- `workspace/` - Identity/memory/skills text files

### Key Concepts

**Runtime State Separation**: Code repo is not Jarvis' runtime home. Runtime state lives in `~/.jarvis-v2/` with config/, state/, logs/, cache/, sessions/, auth/, workspaces/.

**LLM-led, Runtime-governed**: The LLM does the work; the runtime sets boundaries, policy, budget, event flow and observability.

**Mission Control**: The control plane for observability, planning, intervention, approvals, cost/token monitoring, event stream, runtime truth, and channel state.

**Eventbus**: Jarvis' nervous system with event families: runtime, tool, channel, memory, heartbeat, cost, approvals, council/swarm, self-review, self-model, inner-voice, incident.

**Private Layers**: Inner voice, self-review, self-model, chronicle, council, dreams, boredom/companionship - must never outrank the protected core (identity, memory, tools/skills, Mission Control).

### Protected Core vs Experimental
- **Protected**: SOUL/IDENTITY, cross-session memory, tools/skills/approvals, hardware awareness, code/runtime awareness, Mission Control, multi-channel continuity, strong visible chat lane
- **Experimental**: inner voice, self-review, self-model, chronicle, council, dreams, boredom/companionship

## Code Rules

- No file over 1500 lines without explicit exception
- No core runtime file over 2000 lines
- Split at 1200 lines
- One primary responsibility per file
- No hidden side effects
- No dual truth between config and DB
- All risky actions require explicit policy/approval path

## Model Philosophy
- Paid/stable model for visible Jarvis
- Free/cheap models for internal small jobs
- Cheap models may support Jarvis, not define him

## Eventbus Rule
Mission Control reads projections of truth from event/state systems - it does not invent a second truth.

## Source of Truth
- `config` = runtime/governance/provider settings
- `DB` = operational state/events/runs/costs
- `workspace files` = identity/memory/skills text
- `Mission Control` = control plane over truth

## Secrets-håndtering

Hardcoded API-nøgler, tokens og passwords er forbudt i repoet. Alle secrets
læses fra `~/.jarvis-v2/config/runtime.json` via `core.runtime.secrets.read_runtime_key()`.

En pre-commit hook (`detect-secrets`) blokerer commits der introducerer nye
secrets. Kør `pre-commit install` efter clone. Hvis hook'en flagger en
false positive, tilføj det til `.secrets.baseline` med:

```bash
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
```

Se `core/runtime/secrets.py` og `scripts/pipelines/_config.py` for mønstre
til at læse secrets fra runtime.json.
