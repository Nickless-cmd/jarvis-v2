---
status: færdig
audited: 2026-07-08
ground_truth: "Verified claims against live codebase (2026-07-08): visible_model.py + visible_runs.py execute primary lane for chat/persona/planning; agent_runtime_spawn.py falls back to cheap_lane_status_surface() for council agents; execute_cheap_lane_via_pool() actively used in compact_llm.p"
---
# Model Strategy

## Primary Lane
Used for:
- visible chat
- persona
- planning
- tool explanation
- continuity-bearing responses

## Cheap Internal Lane
Used for:
- council roles
- ranking/scoring
- summarization
- memory distillation
- internal small jobs
- cheap swarm workers

## Rule
Cheap models may support Jarvis.
They may not define Jarvis.
