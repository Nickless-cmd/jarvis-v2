# Capability PARTIAL Triage

Date: 2026-05-12

Source: `scripts/capability_audit.py` / `docs/capability_matrix.md`.

Current audit:

| Score | Count |
|---|---:|
| LIVE | 426 |
| PARTIAL | 76 |
| SUSPICIOUS | 3 |
| ORPHAN | 1 |

## What PARTIAL Means Here

`PARTIAL` does not mean broken. The current audit marks a service partial when it is reachable from configured entry points, but has no direct test import, no event emit, and no daemon hook.

That means most of the 81 are not dead code. They are either passive prompt/runtime helpers, cognitive assembly sublayers, storage helpers, or real systems that need a clearer surface/test contract.

## Triage Buckets

### A. Fix First: Important System Surfaces With Weak Proof

These services sit near `prompt_contract`, runtime self-knowledge, memory, governance, or visible state. They should either get focused tests, a read-only signal surface, or explicit documentation that they are passive helpers.

| Service | Why it matters | Likely next action |
|---|---|---|
| `prompt_heartbeat_self_knowledge.py` | Large self-knowledge prompt layer; 18 imports; high theater risk if untested | Add tests around grounded rendering and no ungrounded identity claims |
| `prompt_support_signals.py` | Prompt-side support layer; affects what Jarvis sees as state | Add tests for section shape and evidence-only language |
| `continuity.py` | Used by prompt contract and visible runs | Add focused tests for continuity payload and bounded rendering |
| `development_sense.py` | Development/self-change signal, 7 imports | Add tests for evidence fields and avoid evaluative claims |
| `experience_episodes.py` | Experience correction + visible runs + prompt contract | Add tests for episode read/write and correction path |
| `proactive_outbound_substrate.py` | Proactive behavior gate near prompt contract | Add tests for constraints and no unapproved outbound action |
| `verification_gate_telemetry.py` | Governance/gate telemetry | Add tests for telemetry summarization and prompt-safe wording |
| `semantic_memory.py` | Jarvis brain memory substrate | Add tests for recall/storage boundaries; avoid making it a surface unless needed |
| `semantic_indexer.py` | App startup indexing path | Add smoke test for bootstrap/import behavior |
| `inheritance_seed.py` | Finitude/version inheritance layer | Add tests for seed schema and app bootstrap safety |

### B. Internal Cognitive Assembly: Probably Legitimate PARTIAL

These are mostly one-hop dependencies of `cognitive_state_assembly.py`. They can remain `PARTIAL` if they are covered through assembly-level tests, but a few should get direct tests when we touch them.

| Service | Notes |
|---|---|
| `metacognitive_integration.py` | Large internal cognition mixer |
| `selective_attention.py` | Attention weighting layer |
| `resonance_decay.py` | State decay mechanics |
| `emotional_chords.py` | Affective signal composition |
| `epistemic_pragmatic.py` | Epistemic/pragmatic balance |
| `precision_bias.py` | Bias/precision tuning |
| `embodied_presence.py` | Embodiment-adjacent prompt/state component |
| `temporal_depth.py` | Temporal framing component |

### C. Autonomy/Cadence Systems: Second Batch

These are relevant to Jarvis becoming more agentic, but should be handled after the prompt/memory/governance batch so we do not wire action before evidence.

| Service | Likely next action |
|---|---|
| `automation_dsl.py` | Add parser/execution contract tests |
| `scheduled_job_windows.py` | Add scheduling boundary tests |
| `skill_contract_registry.py` | Add registry read/write tests |
| `outcome_learning.py` | Add learning record tests and prompt-safe summary |
| `cross_session_threads.py` | Add thread continuity tests |
| `memory_write_policy.py` | Add policy tests for when memory writes are blocked/allowed |
| `memory_breathing.py` | Add state summary tests |
| `spaced_repetition.py` | Add scheduling tests |
| `thought_thread.py` | Add thread lifecycle tests |
| `sustained_attention.py` | Add attention persistence tests |

### D. Tool/Operational Helpers: Lower Risk

These are reachable and useful, but mostly score `PARTIAL` because they are tool helpers without direct tests.

Examples: `auto_code_review.py`, `deep_analyzer.py`, `delegation_advisor.py`, `good_enough_gate.py`, `read_before_write_guard.py`, `recurring_tasks.py`, `process_supervisor.py`, `staged_edits.py`, `monitor_streams.py`, `memory_graph.py`, `memory_resurfacing.py`.

### E. Leave For Later

Skyoffice remains intentionally out of scope for now:

| Service | Current status |
|---|---|
| `skyoffice_activity.py` | ORPHAN |
| `skyoffice_council_viz.py` | SUSPICIOUS |
| `skyoffice_residency.py` | SUSPICIOUS |
| `skyoffice_walk.py` | SUSPICIOUS |
| `skyoffice_bridge.py` | PARTIAL |

## Recommended Next Batch

Start with the prompt/memory/governance edge because that is where "real vs theater" matters most.

Batch 1 complete:

1. `prompt_heartbeat_self_knowledge.py`
2. `prompt_support_signals.py`
3. `continuity.py`
4. `development_sense.py`
5. `experience_episodes.py`

Result: direct contract tests added in `tests/test_partial_service_contracts.py`.
`continuity.py` and `development_sense.py` also had small wording changes to
replace identity/performance claims with evidence-based state reporting.

Next batch candidates:

1. `proactive_outbound_substrate.py`
2. `verification_gate_telemetry.py`
3. `semantic_memory.py`
4. `semantic_indexer.py`
5. `inheritance_seed.py`

Acceptance criteria:

- Each service either gets direct tests or a documented reason for staying passive.
- Any generated text must be grounded in explicit state/evidence.
- No new claims like "you feel", "you are becoming", or "you want" unless backed by structured appraisal/evidence.
- Capability audit should improve because of real proof, not because we add empty daemon/event hooks.
