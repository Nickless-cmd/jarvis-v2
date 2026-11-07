# Hukommelses-flader koblet ind (7/11-2026)

Rute: `GET /central/memory-state` (owner-gated, `apps/api/jarvis_api/routes/central.py`).
Aggregator: `core/services/memory_state_surface.py` (mønster: `central_tool_infra_surface`).

## Måling
Kaldt uden argumenter fra `PYTHONPATH=. python`. Kandidatlisten fra opgaven var
upræcis: mange af de nævnte filer (memory_index, memory_router, memory_tiers,
working_memory m.fl.) har ingen `build_*_surface`. Den faktiske liste kommer fra
`grep "def build_.*_surface" core/services | grep memory|recall` filtreret på
0 forekomster i `apps/`.

**Leverede (19, alle ikke-tomme dicts, 0–20 ms):** semantic_memory,
memory_emotional_context, cross_agent_memory, end_of_run_memory_consolidation,
associative_recall, memory_recall_engine, memory_safeguard
(`daemon_memory_safeguard`), memory_graph, memory_hygiene, memory_resurfacing,
memory_breathing (active=False i målingen, men dict), memory_write_queue,
memory_maintenance, memory_pruning, memory_recall_telemetry, memory_density,
visual_memory, conflict_memory, council_memory.
memory_maintenance, memory_pruning og visual_memory har ingen `active`-nøgle;
de regnes som live hvis dict er ikke-tom og ikke fejl-indpakket.

**Udeladt:**
- `memory_write_policy` — kaster NoUserContextError (`workspace_dir()` uden user_id).
- `emotional_memory_engine.build_emotional_memory_surface` — kræver keyword-argumenterne `anchor_type` og `context`.
- Ingen flade fundet for: memory_index, memory_router, memory_scoring,
  memory_tiers, memory_write_gate, memory_links, working_memory,
  episodic_memory, memory_consolidation, memory_decay (kun `memory_decay_daemon`,
  som allerede læses i apps/).

## Mutationstest
Fjernede `memory_graph` fra `_PRODUCERS`: 21 af 44 tests fejlede (registry,
parametriserede kald-/isolations-tests for alle producenter via forventet liste,
`test_real_surfaces…` og route-testen). Uden mutation: 44 passed.
Mutationen blev rullet tilbage.
