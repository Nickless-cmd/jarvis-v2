# Forgetting — Table Audit (Lag 11 Phase 1)

**Date:** 2026-05-10
**Spec:** `docs/superpowers/specs/2026-05-10-true-forgetting-design.md`
**Plan:** `docs/superpowers/plans/2026-05-10-true-forgetting-phase1.md`

143 tables exist in `core/runtime/db.py`. This audit classifies them into three buckets to decide which receive a `soft_deleted_at` column for the auto-track.

## Classification criterion

For each table, ask: would deletion of a row mean Jarvis lost a *moment* (episodic — fade is OK) or lost a *part of who he is* (semantic — fredet)?

## Phase 1 episodic set (gets `soft_deleted_at` now)

Minimal set to validate the architecture. Other episodic tables can join later via additive migrations once the Phase 1 daemon proves itself.

| Table | Why episodic |
|-------|-------------|
| `cognitive_chronicle_entries` | Chronicle observations — single moments, primary fade target |
| `cognitive_personal_project_journal` | Daily journal entries — episodic by definition |

## Phase 2+ episodic candidates (deferred — review during 30-day eval)

These are also episodic but excluded from Phase 1 to keep the blast radius small. Add via additive `ALTER TABLE` migration when ready.

- `cognitive_conflict_memories` — past conflicts; emotionally weighted, may want self-track only
- `cognitive_self_surprises` — moments of self-surprise
- `experiment_*` (broadcast_events, meta_cognition_records, recurrence_iterations) — research data, may be archive-worthy instead
- `runtime_chronicle_consolidation_*` (signals, briefs, proposals) — interim consolidation byproducts
- `runtime_action_outcomes` — past action results
- `runtime_awareness_signals` — single-cycle observations
- `chat_messages` — transient conversation rows; **note**: deletion of chat history requires UI considerations, defer
- Most `runtime_*_signals` tables — single-cycle signal tracking

## Fredet — semantic / identity (no `soft_deleted_at` column)

Deletion of these would damage who he *is*, not just what he *remembers*.

| Table / pattern | Reason |
|-----------------|--------|
| `cognitive_decisions` | Behavioral commitments — identity infrastructure |
| `cognitive_self_model_*` (regex) | Self-model state — core identity |
| `cognitive_narrative_identities` | Identity narratives |
| `cognitive_personality_vectors` | Personality trait vectors |
| `cognitive_formed_values` | Values he has formed |
| `cognitive_taste_profiles` | Aesthetic preferences |
| `cognitive_relationship_textures` | Texture of his relationships |
| `cognitive_compass_states` | Moral compass state |
| `concept_baseline_stats` | Emotion baselines — affective infrastructure |
| `private_self_models`, `private_brain_records` | Inner self-modeling |
| `cognitive_emotion_concept_signals` | Active emotion concept tracking |
| `causal_edges` | Causal graph — semantic memory of how the world works |

## Out of scope (operational, no column)

These are runtime infrastructure, not memory at all.

| Table / pattern | Reason |
|-----------------|--------|
| `runtime_state_kv` | Key-value runtime state |
| `runtime_locks`, `runtime_*_locks` | Concurrency primitives |
| `cheap_provider_runtime_state` | Provider-state cache |
| `cached_affective_state` | Cache (recompute-able) |
| `agent_*` (registry, runs, schedules, messages, tool_calls) | Agent execution infrastructure |
| `events` | Eventbus persistence; tail-trimmed by separate mechanism |
| `daemon_output_log` | Daemon telemetry |
| `costs` | Billing telemetry |
| `chat_sessions`, `channel_attachments` | Session/attachment plumbing |
| `bounded_action_continuity_state` | Continuity safety net |
| `approval_feedback_log` | Approval audit trail |
| `capability_approval_requests`, `capability_invocations` | Approval/invocation logs |
| `runtime_browser_bodies` | Browser-control state |

## Decisions log

- **`cognitive_conflict_memories` deferred to Phase 2:** these are emotionally heavy; auto-fade feels wrong. Likely a self-track-only target later.
- **`chat_messages` deferred:** deletion has UI implications (history disappears mid-scroll). Needs separate UX thought.
- **`absence_traces` is fredet:** the trace ledger itself must not auto-fade. Already enforced in `forgetting_engine._FREDET_TABLES_EXACT`.
- **`runtime_state_*` excluded as out-of-scope:** these are operational caches and registries, not memory. They reset naturally on restart.
- **`experiment_*` deferred:** unclear whether research data should fade or archive. Defer until use-case emerges.

## Phase 1 minimal validation

The two tables in the "Phase 1 episodic set" are sufficient to:
1. Prove the auto-track daemon works end-to-end (scan → soft-delete → grace-sweep → counter)
2. Prove the self-track tool deletes irrevocably (`release_memory` on chronicle/journal)
3. Prove heartbeat injection renders correctly

Adding more tables to the auto-fade pool is a single line in `_AUTO_FADE_TABLES` and an additive migration in `_ensure_soft_deleted_at_columns` — no architecture change needed.
