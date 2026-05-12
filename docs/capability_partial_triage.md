# Capability PARTIAL Triage

Date: 2026-05-12

Source: `scripts/capability_audit.py` / `docs/capability_matrix.md`.

Current audit:

| Score | Count |
|---|---:|
| LIVE | 452 |
| PARTIAL | 50 |
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

Batch 2 complete (2026-05-12):

1. `proactive_outbound_substrate.py` — existing tests prove the contract.
   Test file: `tests/test_proactive_outbound_substrate.py`.
   Coverage: payload summarization (8), DB-backed substrate (7), section builder (4),
   constraint verification (3 — whitelist-only kinds, no DB writes, no side effects).
   Module itself unchanged — zero theater, pure data-reader. Killswitch verified.

Batch 3 complete (2026-05-12):

1. `verification_gate_telemetry.py` — existing tests prove the contract.
   Test file: `tests/test_verification_gate_telemetry.py`.
   Coverage: record_surface (5), record_verify_event (4), sweep_expired_surfaces (3),
   get_telemetry_summary (6), telemetry_section (3).
   All IO faked via in-memory state_store — no disk, no eventbus needed.
   Low heed-rate wording now reports telemetry instead of second-person judgment.

Batch 4 complete (2026-05-12):

1. `semantic_memory.py` — existing tests prove the contract.
   Test file: `tests/test_semantic_memory.py`.
2. `semantic_indexer.py` — direct handler tests added.
   Test file: `tests/test_semantic_indexer_and_inheritance_seed.py`.
3. `inheritance_seed.py` — direct read/write seed tests added.
   Test file: `tests/test_semantic_indexer_and_inheritance_seed.py`.

Batch 5 complete (2026-05-12):

1. `automation_dsl.py`
2. `scheduled_job_windows.py`
3. `skill_contract_registry.py`
4. `outcome_learning.py`
5. `cross_session_threads.py`

Result: direct contract tests added in `tests/test_autonomy_registry_surfaces.py`.
All five services now have explicit proof, and the audit moved them to LIVE.

Batch 6 complete (2026-05-12):

1. `selective_attention.py`
2. `resonance_decay.py`
3. `auto_code_review.py`
4. `delegation_advisor.py`
5. `good_enough_gate.py`

Result: direct contract tests added in `tests/test_internal_and_helper_surfaces.py`.
All five services now have explicit proof, and the audit moved again.

Current next batch candidates:

1. `monitor_streams.py`
2. `read_before_write_guard.py`
3. `deep_analyzer.py`
4. `decision_review_prompter.py`
5. `agent_outcomes_log.py`

Acceptance criteria:

- Each service either gets direct tests or a documented reason for staying passive.
- Any generated text must be grounded in explicit state/evidence.
- No new claims like "you feel", "you are becoming", or "you want" unless backed by structured appraisal/evidence.
- Capability audit should improve because of real proof, not because we add empty daemon/event hooks.
