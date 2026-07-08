# Architecture Overview — the map

This is a **map**, not the territory. It gives the shape of the system and points to the depth. Per-route detail is in [`../reference/API_REFERENCE.md`](../reference/API_REFERENCE.md); per-tool detail in [`../reference/CAPABILITIES.md`](../reference/CAPABILITIES.md); service liveness in [`../capability_matrix.md`](../capability_matrix.md); the nervous system in [`../CENTRAL.md`](../CENTRAL.md). Per-file/function narrative docs are the docs-programme SP4.

## One sentence

The LLM does the work; the **runtime** governs it (boundaries, policy, budget, events, observability); the **Central** is the single truth/control plane that all runtime decisions and observability flow through.

## Directory structure

| Path | Responsibility |
|---|---|
| `core/runtime/` | Runtime foundation: settings, secrets, the DB layer (`db*.py` — the operational state/events/runs/costs store), state store, process/lifecycle. |
| `core/services/` | The bulk of the system — the Central (`central_*`), the visible chat run loop (`visible_runs.py` + `simple_tool_executor.py`), followup/streaming, memory, identity, cost, gates, self-state, and hundreds of cognitive/inner-life services. |
| `core/tools/` | The tool implementations behind the LLM's capabilities (`simple_tools.py` dispatch → `_exec_*` handlers), incl. operator tools that act on the user's machine via the bridge. |
| `core/context/` | Context/window management: compaction (`run_compact`, `session_compact`, `auto_compact`), token estimation, tool-result handling. |
| `core/eventbus/` | The nervous-system substrate: event families (runtime/tool/channel/memory/heartbeat/cost/approvals/…) the Central projects truth from. |
| `apps/api/` | FastAPI backend: chat, Mission Control, live event (SSE/WS) endpoints. Routers under `apps/api/jarvis_api/routes/` — see the generated API reference. |
| `apps/ui/`, `apps/jarvis-desk/` | Mission Control + web/desktop chat UIs. |
| `scripts/` | Entry points (`jarvis.py` CLI) + the audit/generator scripts (`capability_audit.py`, `docs_audit.py`, `api_reference_gen.py`, `capabilities_gen.py`, `god_file_map`). |
| `state/` (runtime `~/.jarvis-v2/`) | Runtime state: config, DB, logs, cache, sessions, auth, workspaces. **The code repo is not Jarvis' runtime home.** |
| `workspace/` | Identity/memory/skills **text** files. |

## Request flow (visible chat)

1. A message hits `apps/api` → the chat route starts a **visible run**.
2. `core/services/visible_runs.py` drives the **agentic loop**: build the prompt (`prompt_contract`), call the model, stream deltas over SSE, and when the model emits tool calls, execute them via `simple_tool_executor._execute_simple_tool_calls` (which calls `core/tools/simple_tools.execute_tool`).
3. Each tool call passes the **commit gates** (veto + decision) and mode/role/tier scoping before running; results feed back into the loop (`_followup_exchanges`) for the next round.
4. Context is kept in budget by compaction (`core/context/`), and the whole run is observed by the **Central** (`central().decide` / `observe`) for one trace per `run_id`.

## The Central (nervous system)

The Central is where all runtime decisions and observability converge — "nothing left anywhere the Central doesn't catch." It reads **projections of truth** from the event/state systems (it does not invent a second truth), governs gates per-kill-switch, carries the agenda and self-state, and surfaces everything to Mission Control / the `jc` CLI. Full detail: [`../CENTRAL.md`](../CENTRAL.md).

## The four sources of truth

Per `CLAUDE.md`:

- **`config`** — runtime/governance/provider settings (`~/.jarvis-v2/config/runtime.json`).
- **`DB`** — operational state/events/runs/costs.
- **`workspace files`** — identity/memory/skills text.
- **`Central`** — the control plane *over* the truth (projections, not a second truth).

Secrets are never hardcoded — they come from `runtime.json` via `core.runtime.secrets.read_runtime_key()`.

## Model philosophy

A paid/stable model powers the **visible** Jarvis; free/cheap models support internal small jobs but never *define* him. See [`../MODEL_STRATEGY.md`](../MODEL_STRATEGY.md).

## Protected core vs experimental

- **Protected:** SOUL/IDENTITY, cross-session memory, tools/skills/approvals, hardware/code/runtime awareness, Mission Control, multi-channel continuity, the visible chat lane.
- **Experimental (must never outrank the protected core):** inner voice, self-review, self-model, chronicle, council, dreams, boredom/companionship.

## Where to go next

- Endpoints → [`../reference/API_REFERENCE.md`](../reference/API_REFERENCE.md)
- Tools → [`../reference/CAPABILITIES.md`](../reference/CAPABILITIES.md)
- Service liveness → [`../capability_matrix.md`](../capability_matrix.md)
- The Central → [`../CENTRAL.md`](../CENTRAL.md)
- Code rules & runtime home → `../../CLAUDE.md`
