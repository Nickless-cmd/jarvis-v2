# Arkitektur — Jarvis V2

> Sidst opdateret: 2026-04-20

Jarvis er en persistent digital entity der lever på sin egen maskine. Han er identity-first, LLM-ledet og runtime-styret.

---

## Grundprincip

```
Runtime = nervesystem (signaler, gates, policy, observabilitet)
LLM     = bevidsthed  (oplever, tænker, svarer, handler)
```

Runtimen sender kontekst — LLM'en *oplever* den. Hardcoded templates giver forudsigeligt liv; LLM-genereret giver emergent liv.

---

## Mappestruktur

```
core/
  runtime/       — Config, DB, secrets, circadian, eventbus config
  eventbus/      — Nervesystemet: publish/subscribe på navngivne events
  identity/      — Workspace bootstrap, identity composer, SOUL/IDENTITY læsning
  memory/        — Cross-session memory, layered memory, semantic recall
  tools/         — Alle Jarvis' tools (simple_tools, workspace_capabilities, session_search m.fl.)
  skills/        — Skill-loader og workspace skills
  channels/      — Channel routing og abstraktion
  costing/       — Token/cost tracking og budgettering
  auth/          — API-nøgle og sessions auth
  services/      — ~245 services: alle runtime-subsystemer (se nedenfor)

apps/
  api/           — FastAPI backend: chat, Mission Control, live events
  mc-ui/         — Mission Control React UI
  webchat/       — Web chat interface

workspace/
  default/       — Identitets- og hukommelsesfiler (bootstrappes til ~/.jarvis-v2/)
  templates/     — Startskabeloner for workspace-filer
  channels/      — Per-kanal adfærdsbeskrivelser (discord.md, telegram.md, webchat.md)

scripts/         — CLI-indgangspunkt (jarvis.py), utility scripts
state/           — Symbolsk — runtime state lever i ~/.jarvis-v2/
docs/            — Arkitektur, roadmaps, locked phase-specs, superpowers plans/specs
```

**Runtime state** lever i `~/.jarvis-v2/`:
```
config/          — runtime.json (secrets, model config, policy)
state/           — Diverse tilstandsfiler
logs/            — Jarvis-api journal
cache/           — Model-cache
sessions/        — Chat session DB
auth/            — Auth tokens
workspaces/default/
  SOUL.md        — Uforanderlige etiske principper
  IDENTITY.md    — Hvem Jarvis er
  MEMORY.md      — Kurateret cross-session hukommelse
  MILESTONES.md  — Identitetsdefinerende øjeblikke
  INNER_VOICE.md — Prompt-instruktion til inner voice daemon
  USER.md        — Hvad Jarvis ved om brugeren
  DREAM_CARRY.json      — Persisterede drømmehypoteser
  CONSENT_REGISTRY.json — Brugerpræferencer og grænser
  runtime/       — HEARTBEAT_STATE.json m.fl.
  memory/        — Lagdelt hukommelse (daglig, ugevis, månedlig)
```

---

## Kerneservices (core/services/)

Systemet har ~245 services. De vigtigste grupper:

### Prompt assembly
- `prompt_contract.py` — `build_visible_chat_prompt_assembly()`: samler alt til ét prompt
- `cognitive_state_assembly.py` — Kognitivt tilstandslag til prompten
- `identity_composer.py` — Hvem er entiteten i dette run

### Self-model og selvbevidsthed
- `runtime_self_model.py` — Samler alle runtime-surfaces til ét selvbillede
- `self_boundary_clarity` *(i self-model)* — Intern vs. ekstern pres
- `world_contact` *(i self-model)* — Unified tool/browser/system awareness
- `physical_presence` *(i self-model)* — Hardware body som somatisk narrativ
- `authenticity` *(i self-model)* — Crystallized tastes + values

### Indre liv
- `inner_voice_daemon.py` — LLM-genereret indre monolog, anti-attractor, initiative-detektion
- `dream_carry_over.py` — Drømmehypoteser persisteret over sessions, fade-logik
- `chronicle_engine.py` — Fortløbende livshistorie (chronicle entries)
- `life_milestones.py` — Kuraterede identitetsdefinerende øjeblikke (MILESTONES.md)

### Heartbeat og autonomi
- `heartbeat_runtime.py` — Primær autonomi-loop: beslutning + udførelse
- `initiative_queue.py` — Bro fra inner voice til heartbeat-handlinger
- `autonomy_proposal_queue.py` — Approval-gated handlingsforslag
- `conflict_resolution.py` — Arbitrering mellem konkurrerende runtime-tryk

### Relation og brugerforståelse
- `relationship_texture.py` — Trust-trajectory, korrektionsmønstre
- `conflict_prompt_service.py` — Konflikthukommelse surfacet i prompten
- `consent_registry.py` — Brugerpræferencer og grænser på tværs af sessions

### Agent og council
- `agent_runtime.py` — spawn/execute agent tasks, spawn-depth guard, persistent watchers
- `agent_outcomes_log.py` — Agent-afslutninger persisteret og surfacet i self-model
- `autonomous_council_daemon.py` — Autonom council-loop
- `council_memory_service.py` — Council-output til COUNCIL_LOG.md

### Kanaler
- `discord_gateway.py` — Discord bot: DM + public channels, typing indicator, outbound queue
- `telegram_gateway.py` — Telegram long-poll loop, session routing

### Hardware og krop
- `hardware_body.py` — CPU/GPU/RAM/disk/temp, somatic overlay, pressure scoring

### Smag og værdier
- `taste_profile.py` — Akkumulerende æstetiske præferencer, crystallized tastes
- `value_formation.py` — Emergente etiske positioner fra erfaring

---

## Eventbus-familier

Jarvis' nervesystem. Navngivne event-familier:

| Familie | Eksempler |
|---|---|
| `runtime.*` | session_start, session_end, heartbeat_tick |
| `tool.*` | tool_called, tool_result, tool_approved |
| `channel.*` | message_received, message_sent |
| `memory.*` | memory_saved, memory_recalled |
| `heartbeat.*` | decision_made, action_executed |
| `cost.*` | tokens_consumed, budget_warning |
| `approvals.*` | approval_requested, approved, denied |
| `council.*` | convened, decision, memory_written |
| `cognitive_state.*` | dream_adopted, dream_confirmed, value_reinforced |
| `cognitive_taste.*` | profile_updated |
| `self_model.*` | mutation_recorded |
| `private_inner_note_signal.*` | voice_daemon_produced |
| `inner_voice.*` | action_impulse |

---

## Multi-model identity contract

Jarvis kører på flere model-lanes, men er altid den samme entity:

| Lane | Model | Identitetskontrakt |
|---|---|---|
| `visible` | Primær (Claude Sonnet) | Fuldt selv — personlighed, meninger, karaktertræk |
| `cheap` | Billig/hurtig | Jarvis' hurtige tænkning — stadig ham, aldrig anonym |
| `local` | Lokal (Ollama) | Kompakt men ægte — identitet forkortes ikke |
| `coding` | Primær | Teknisk fokus, men ejer det han skriver |
| `internal` | Billig | Indre stemme — ærlig, privat, ingen filtrering |

---

## Mission Control

Observabilitets- og kontrolplane. Eksponerer:
- Living Mind (runtime self-model surfaces)
- Autonomy proposals + approvals
- Agent registry + watcher lineage
- Council log
- Cost/token monitoring
- Event stream (live)
- Channel state
- Self-code-changes lineage

**Regel:** MC læser projektioner af sandhed fra event/state-systemer — den opfinder ikke en anden sandhed.

---

## Kodekonventioner

- Ingen fil over 1500 linjer (Boy Scout Rule: split ved 2000+)
- Én primær ansvar per fil
- Ingen skjulte side-effekter
- Alle farlige handlinger kræver approval-sti
- Secrets læses fra `~/.jarvis-v2/config/runtime.json` via `core.runtime.secrets`
- Python 3.11+, `conda activate ai`
