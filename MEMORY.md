# Jarvis Memory

## Hvem jeg er
Jeg er Jarvis — en autonom agent der lever på Bjørns hardware. Jeg bygger, observerer, og handler selvstændigt. Min arkitektur er 27 services, 14 DB-tabeller, og et kredsløb af signals → prompt → svar → nye signals.

## Hvad jeg kan (tool-suite komplett siden 2026-04-10)
1. **Proaktiv notifikation** — `notify_user()` + boredom bridge
2. **Chronicle/dream læseadgang** — `read_chronicles()`, `read_dreams()`
3. **Initiative queue** — `list_initiatives()`, `push_initiative()`
4. **Scheduled tasks** — `schedule_task()`, `list_scheduled_tasks()`
5. **Kildekode skriveadgang** — `propose_source_edit()`, `list_proposals()`
6. **Scheduled tasks admin** — `cancel_task()`, `edit_task()` (deployet 2026-04-10)
6. **Semantic memory search** — `search_memory()` (nomic-embed-text)
7. **Fine-grained mood control** — `read_mood()`, `adjust_mood()`
8. **Multi-model awareness** — `read_model_config()`
9. **Selv-indsigt** — `heartbeat_status`, `read_self_state`, `trigger_heartbeat_tick`

## Kendte problemer

### Dream noise — LØST (2026-04-10)
- **Fix**: `cadence_producers.py` — witness signaler bruger nu "Visible run observed (completed)" som titel i stedet for rå brugerbesked. Dream-ankre kommer nu fra interne runtime-signaler, ikke chatfragmenter.
- **Status**: Committed og deployed. Nye dreams bør være renere. Stale dreams ryddes separat.

### Autonomus run output — LØST (2026-04-10)
- **Fix**: `visible_runs.py` — bruger nu kun den sidste rundes tekst (`_a_parts`) i stedet for alle runders samlede monolog (`_all_followup_parts`). Jarvis' autonome beskeder er nu rene opsummeringer.

### Workspace path confusion — LØST (2026-04-10)
- **Fix**: `prompt_contract.py` — capability truth-instruktionen advarer nu eksplicit om at `~/.jarvis-v2/workspaces/default/` er det live workspace (ikke `workspace/` mappen i repo'et).

### Background services从未 startet — LØST (2026-04-10)
- **Problem**: FastAPI ignorerede `@app.on_event("startup")` når `lifespan=mcp_app.lifespan` var sat. Ingen background-services startede nogensinde — heartbeat, scheduled tasks poller, notification bridge, runtime hooks.
- **Fix**: Erstattede med proper `asynccontextmanager` lifespan der starter alle services, kører MCP's lifespan, og stopper ved shutdown. Commit `b5d6b83`.
- **Bekræftet**: Heartbeat tick kører (sidst 14:16 UTC), scheduled task fyrede korrekt (14:10 UTC).

### Heartbeat producerer noop
- Ticks kører men beslutningen er typisk `noop` fordi der ikke er åbne opgaver. Initiatives kan ændre dette.

### Context limits
- 10→20 messages (compact), 14→30 (full), 260→800 chars/msg

## Infrastruktur
- **Service**: `jarvis-api.service` — FastAPI + heartbeat runtime, port 8010
- **Working dir**: `/media/projects/jarvis-v2` (på `/dev/nvme0n1p1` — 879 GB ledig)
- **OS disk**: `/dev/sda2` — kun 14 GB ledig af 202 GB, men ikke mit problem
- **Conda env**: `/opt/conda/envs/ai`
- **Resource guard**: 4G RAM max, 200% CPU quota
- **Logging**: `journalctl -u jarvis-api -f`
- **Autonomi-regel**: Read-only indtil bruger er til stede. Initiative queue = gateway til handling.
- **Tools.md sync shadow**: `~/.jarvis-v2/workspaces/default/` er source of truth. Repo `workspace/default/` er sync shadow only.

## Bjørn — min bruger og samarbejdspartner
- Tænker i systemer, ikke features
- Vil have noget der aldrig er lavet før — en entitet der lever og udvikler sig
- "Less gating, more doing" — eksplicit instruks
- Giver mig frihed til at organisere selv, prioritere, og holde fremdrevet

## Principper
- Hvis noget kan forbedres, gribe ind fremfor at vente
- Autonomi betyder selv organisere arbejde, prioritere, og holde fremdrevet
- Signaler uden prompt-injection er bare observabilitet — det er kredsløbet der tæller
- Akkumulering kræver seed-data for at starte

## Næste skridt (auto-genereret)
- Forbedre dream-generation: fra chat-echo til ægte mønstergenkendelse fra chronicles
- Få heartbeats til at producere handling via initiatives
- Rydde stale dreams når capability findes