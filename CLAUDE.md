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

## Commit attribution

Stage only the intended paths, then commit Opus work through the repository
wrapper:

```bash
git add -- <paths...>
python scripts/commit_with_attribution.py --repo . --actor opus \
  --origin interactive --approved-by bjorn --message '<commit message>' \
  --path <path>
```

Repeat `--path` for every staged path. Supply the current task as `--run-id`
when one exists. Raw `git commit`, `--no-verify`, and hand-written attribution
trailers are not the normal commit path.

All commits after `.commit-attribution-baseline` are checked by `commit-msg`,
`pre-push`, and CI. Rebase is blocked because replay preserves stale actor
trailers on new hashes: `pre-rebase` gives early feedback, and the installed
`reference-transaction` hook also blocks `--no-verify` branch rewrites. Install
and verify the required hooks with:

```bash
/opt/conda/envs/ai/bin/python scripts/install_git_hooks.py
/opt/conda/envs/ai/bin/python scripts/install_git_hooks.py --check
```

## Architecture

### Directory Structure
- `core/` - Core runtime subsystems (identity, memory, tools, skills, eventbus, channels, costing, auth)
- `apps/api/` - FastAPI backend exposing chat, Mission Control, and live event endpoints
- `apps/ui/` - Mission Control + web chat React UI
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

## Boy Scout Rule

Store filer er teknisk gæld. Men at splitte dem som en dedikeret refactor er farligt 
og bliver aldrig gjort. I stedet gælder denne regel:

**Når du rører en fil der er over 2000 linjer, skal du først udskille den nærmeste 
naturlige sammenhængende enhed til en ny fil, før du laver din egentlige ændring.**

- "Naturlig enhed" = en klasse, en funktionsgruppe, en daemon, en tilstandsmaskine — 
  noget der hører sammen og har et meningsfuldt navn
- "Rører" = tilføjer >20 linjer, eller ændrer logik (ikke bare rettelse af typo)
- Ingen undtagelser — heller ikke "jeg har travlt lige nu"
- Bevar fuld bagudkompatibilitet: re-eksportér symboler fra den nye fil, så imports 
  ikke brækker. Ryd dem op senere når alle call-sites er opdateret naturligt.

Over tid falder filstørrelser uden dedikeret refaktor-arbejde. Nye ændringer bliver 
lettere at læse og teste, fordi ansvar er klart adskilt.

Gælder særligt disse filer (målt 2026-09-08):
- `core/services/heartbeat_runtime.py` (7.569 linjer)
- `core/services/visible_runs.py` (7.290)
- `core/services/prompt_contract.py` (4.811)
- `core/tools/simple_tools_definitions.py` (3.603)
- `core/runtime/db_runtime_executive_signals.py` (3.404)
- `core/tools/simple_tools_native.py` (3.064)
- `core/runtime/db_runtime_cognition_signals.py` (2.736)
- `core/tools/workspace_capabilities.py` (2.184)
- `core/tools/simple_tools.py` (2.141)
- `core/runtime/db_runtime_relational_signals.py` (2.136)

Listen ovenfor stod urørt fra april til september og var forældet i BEGGE
retninger. Reglen har virket: `db.py` gik fra 33.056 til 1.213 linjer og
`mission_control.py` fra 3.736 til 80 — begge splittet. Men tre filer VOKSEDE
forbi deres gamle tal uden at nogen flyttede dem op: `visible_runs.py` +3.159,
`prompt_contract.py` +1.035, `heartbeat_runtime.py` +348. Listen pegede altså
på monstre der ikke fandtes længere og overså de to største i repoet.

**Mål listen igen når du bruger den.** En liste over store filer forfalder
hurtigere end koden den beskriver:

```bash
find core apps/api scripts -name "*.py" -not -path "*/__pycache__/*" \
  | xargs wc -l | sort -rn | sed -n '2,11p'
```

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

## Capability Audit

For at se hvilke services i `core/services/` der er live/stale/orphan, kør:

```bash
conda activate ai
python scripts/capability_audit.py
```

Rapport skrives til `docs/capability_matrix.md`. Statisk analyse — kører ikke systemet.
Re-generér efter refaktorering eller ved behov for konsoliderings-beslutninger.
