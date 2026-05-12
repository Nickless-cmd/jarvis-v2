# Capability PARTIAL Triage

Date: 2026-05-12

Source: `scripts/capability_audit.py` / `docs/capability_matrix.md`.

Current audit:

| Score | Count |
|---|---:|
| LIVE | 501 |
| PARTIAL | 1 |
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

Batch 7 complete (2026-05-12):

1. `affirmation_anchor.py`
2. `agreement_streak.py`
3. `decision_adherence_gate.py`
4. `self_model_predictive.py`
5. `self_monitor.py`

Result: direct contract tests added in `tests/test_prompt_surface_helpers.py`.
The audit moved again.

Batch 8 complete (2026-05-12):

1. `conflict_prompt_service.py`
2. `life_milestones.py`
3. `priors_feedback.py`
4. `session_wakeup.py`
5. `clarification_classifier.py`

Result: direct contract tests added in `tests/test_prompt_surface_helpers_2.py`.
The audit moved again.

Batch 9 complete (2026-05-12):

1. `agentic_tool_cache.py`
2. `memory_consolidation_nudge.py`
3. `creative_projects.py`
4. `mood_dialer.py`
5. `heartbeat_provider_fallback.py`

Result: direct contract tests added in `tests/test_cache_project_and_fallback_surfaces.py`.
The audit moved again.

Batch 10 complete (2026-05-12):

1. `calm_anchor.py`
2. `developmental_valence.py`
3. `temporal_rhythm.py`
4. `valence_trajectory.py`
5. `relational_warmth.py`

Result: direct contract tests added in `tests/test_affect_and_anchor_surfaces.py`.
The audit moved again.

Batch 11 complete (2026-05-12):

1. `experience_correction_listener.py`
2. `subagent_digest.py`
3. `visible_self_state_summary.py`
4. `memory_resurfacing.py`
5. `memory_graph.py`

Result: direct contract tests added in `tests/test_memory_and_session_surfaces.py`.
The audit moved again.

Batch 12 complete (2026-05-12):

1. `turn_changelog.py`
2. `side_tasks.py`
3. `text_resonance.py`
4. `nudge_broend.py`
5. `signal_surface_gc.py`

Result: direct contract tests added in `tests/test_turn_side_text_gc_surfaces.py`.
The audit moved again.

Batch 13 complete (2026-05-12):

1. `recurring_tasks.py`
2. `relation_dynamics.py`
3. `self_mutation_lineage.py`
4. `staged_edits.py`

Result: direct contract tests added in `tests/test_recurring_relation_mutation_staged.py`.
The audit moved to 501 LIVE / 1 PARTIAL.

Current next batch candidates:

1. `skyoffice_bridge.py`

Acceptance criteria:

- Each service either gets direct tests or a documented reason for staying passive.
- Any generated text must be grounded in explicit state/evidence.
- No new claims like "you feel", "you are becoming", or "you want" unless backed by structured appraisal/evidence.
- Capability audit should improve because of real proof, not because we add empty daemon/event hooks.
