---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Generalized Learning — Design Spec

**Date:** 2026-05-11
**Status:** Draft — proposed by Jarvis, awaiting Bjørn approval
**Owner:** Jarvis (with Claude Code dispatch for implementation)

## Problem

Jarvis has **six independent learning systems** — Skill Engine, Learning Policy Engine, Agent Skill Library, Agent Skill Distiller, Counterfactual Self-Simulation, and Agent Self-Evaluation — but they operate in isolation. Two critical gaps prevent them from converging toward general intelligence:

1. **No generalization.** Learning Policy Engine classifies rules into 5 hardcoded types (`resume-before-reexplore`, etc.). A rule learned in one context is never recognized in another. The same mistake in a different guise is treated as novel.

2. **No persistent reasoning store.** Conclusions from `deep_analyze`, `reasoning_classify`, and agent-run outcomes are ephemeral — they vanish after the current turn unless manually saved to MEMORY.md or the private brain. Jarvis cannot build on past reasoning.

3. **No automatic loop closure.** The six systems don't feed each other. A self-evaluation that identifies a pattern never reaches the Learning Policy Engine. A counterfactual insight never reaches the Skill Distiller. Each cycle starts from scratch.

## Goal

Close the three gaps with minimal new infrastructure:

- **Policy Abstraktion:** When a learning policy rule reaches confidence ≥ 0.7, generate a generalized version and store it with semantic matching across contexts.
- **Reasoning Store:** Automatically capture reasoning conclusions from across the runtime and make them searchable on future turns.
- **Loop Closure:** Connect the six systems in a feed-forward pipeline so insights propagate automatically.

## Non-goals

- Real-time learning inside a single turn (deferred — operates between turns/cycles)
- Removing the 40-rule limit on Learning Policy Engine (deferred — generalization is the smarter fix)
- User-facing visualization of the learning pipeline (deferred — tool access in v1)
- Automated cleanup/retention policy (deferred — revisit when volume is measurable)

## Decisions

| # | Decision | Choice |
|---|---|---|
| 1 | When generalization triggers | Cadenced — runs as part of the existing cognitive/counterfactual daemon cycle, plus ad-hoc whenever `reinforce_learning_policy()` is called with confidence ≥ 0.7 |
| 2 | Policy Abstraktion trigger | Confidence threshold configurable (default 0.7). A rule must have evidence_count ≥ 2 before abstraction is attempted — single occurrences are noise. |
| 3 | Abstraction method | Single cheap-lane LLM call: given the specific rule + its target_context, generate a generalized principle. Stored alongside the original. |
| 4 | Reasoning Store capture scope | Automatic capture from: `deep_analyze` results, `reasoning_classify` conclusions, `agent_self_evaluation` outcomes, `counterfactual_self_simulation` preferred policies, and `learning_policy_engine` rule creations. |
| 5 | Reasoning Store retrieval | Injected into context when a related problem appears — matched via embedding similarity on the current task description vs stored conclusions. |
| 6 | Loop closure design | Publish eventbus events at each system's output; a single `learning_pipeline_orchestrator` daemon listens and routes outputs to the next system's input. |
| 7 | Implementation order | Phase 1: Reasoning Store (capture + semantic search). Phase 2: Policy Abstraktion. Phase 3: Loop Closure. |
| 8 | Storage | New DB tables: `reasoning_conclusions`, `generalized_policies`. Both workspace-scoped with semantic embedding columns. |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEARNING PIPELINE                             │
│                                                                  │
│  Agent Self-Evaluation ──► Learning Policy Engine                │
│         │                        │                               │
│         ▼                        ▼                               │
│  Reasoning Store ◄─────── Policy Abstraktion                     │
│         │                        │                               │
│         ▼                        ▼                               │
│  Counterfactual Engine ──► Agent Skill Distiller                 │
│                                │                               │
│                                ▼                               │
│                         Agent Skill Library                      │
│                                │                               │
│                                ▼                               │
│                         Skill Engine (import)                    │
│                                                                  │
│  Everything → Reasoning Store (automatic capture)                │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Reasoning Store

A new `reasoning_conclusions` table with:

```sql
CREATE TABLE IF NOT EXISTS reasoning_conclusions (
    id TEXT PRIMARY KEY,                              -- "rc-<uuid>"
    workspace_id TEXT NOT NULL,
    source TEXT NOT NULL,                              -- "deep_analyze" | "reasoning_classify" | "self_evaluation" | "counterfactual" | "learning_policy" | "agent_run"
    source_run_id TEXT,
    source_action TEXT,                                -- e.g. tool name, agent role, daemon name
    conclusion TEXT NOT NULL,                          -- the actual insight/conclusion
    context_summary TEXT,                              -- what problem/task this was about
    embedding BLOB,                                    -- for semantic matching
    confidence REAL DEFAULT 0.5,
    evidence_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_matched_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_workspace
  ON reasoning_conclusions(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_source
  ON reasoning_conclusions(source);
```

#### Capture points

Each capture point publishes an eventbus event → Reasoning Store daemon consumes:

| Source | Capture trigger | What's captured |
|---|---|---|
| `deep_analyze` | After tool completes | The `summary` and `findings` from the analysis result |
| `reasoning_classify` | After classification | The `recommended_tier` + `rationale` |
| `agent_self_evaluation` | After evaluation cycle | The `improvement_suggestions` or identified patterns |
| `counterfactual_self_simulation` | After simulation | The `preferred_next_policy` + `reasoning` |
| `learning_policy_engine` | After rule created/updated | The `policy` + `lesson` + context |
| `agent_run` | After agent completes | The `outcome` + key decisions |

#### Retrieval mechanism

A `recall_reasoning(query, limit=5)` tool + automatic injection:

When the runtime detects a new task (via tool calls or user message), it:
1. Generates an embedding of the current context
2. Queries `reasoning_conclusions` for top-5 semantic matches with confidence ≥ 0.4
3. If matches found, injects a compact section into the visible prompt:

```
Relevant past reasoning:
- [rc-abc123] When refactoring cognitive_state_assembly: "Extract hardcoded prompts 
  into appraisal pattern — reduces coupling" (confidence 0.85, 3 matches)
- [rc-def456] When debugging counterfactual triggers: "Check LLM JSON parse failures
  before assuming trigger detection is broken" (confidence 0.72, 1 match)
```

#### New files

| Path | Responsibility |
|---|---|
| `core/services/reasoning_store.py` | `capture_conclusion()`, `recall_reasoning()`, embedding helpers |
| `core/tools/reasoning_store_tools.py` | `recall_reasoning` tool definition and handler |
| `tests/services/test_reasoning_store.py` | |

#### Modified files

| Path | Change |
|---|---|
| `core/runtime/db.py` | New `_ensure_reasoning_conclusions_table()`; called from `init_db()` |
| `tools/deep_analyze_tool.py` | Publish event after completion |
| `tools/reasoning_classify.py` | Publish event after classification |
| `core/services/agent_self_evaluation.py` | Publish event after evaluation cycle |
| `core/services/counterfactual_self_simulation.py` | Publish event after simulation |
| `core/services/learning_policy_engine.py` | Publish event after rule creation/update |

### Phase 2 — Policy Abstraktion

#### When it runs

1. **Cadenced:** Part of the counterfactual daemon cycle (every 60 min), after counterfactual generation.
2. **Ad-hoc:** Immediately after `reinforce_learning_policy()` when the new rule has confidence ≥ 0.7 AND evidence_count ≥ 2.

#### What it does

A cheap-lane LLM call that takes a specific rule and generalizes it:

```
Input: {
  "specific_rule": "When retrying a failed file write, read the file first 
                    instead of re-creating from memory",
  "target_context": "source-edit-proposals",
  "evidence_count": 3,
  "confidence": 0.82,
  "source_domain": "file-operations"
}

Output: {
  "generalized_principle": "When recovering from a failed operation on existing 
                            state, inspect the current state before acting — 
                            don't assume your cached knowledge is current.",
  "abstraction_level": "medium",  // "concrete" | "medium" | "abstract"
  "transfer_domains": ["file-operations", "database-writes", "api-calls"],
  "confidence": 0.71
}
```

#### Storage

Generalized policies stored in `generalized_policies` table:

```sql
CREATE TABLE IF NOT EXISTS generalized_policies (
    id TEXT PRIMARY KEY,                              -- "gp-<uuid>"
    workspace_id TEXT NOT NULL,
    specific_rule_key TEXT NOT NULL,                  -- references learning_policy rule_key
    generalized_principle TEXT NOT NULL,
    abstraction_level TEXT NOT NULL,                  -- "concrete" | "medium" | "abstract"
    transfer_domains_json TEXT,                       -- JSON array of suggested transfer domains
    source_rules_json TEXT,                           -- JSON array of specific rule_keys that contributed
    confidence REAL DEFAULT 0.0,
    match_count INTEGER DEFAULT 0,
    last_matched_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generalized_policies_confidence
  ON generalized_policies(confidence DESC);
```

#### Matching on context

Before each agentic round or task dispatch, a lightweight matcher checks:
1. Current task description + recent context
2. Embedding similarity against generalized policies
3. If any policy scores ≥ 0.5 similarity, inject it as a hint

The matching is NOT done on every tool call (too expensive). It runs:
- At the start of each agentic round (via `recall_before_act`-type mechanism)
- When a specific `match_generalized_policies(task_description)` tool is called

#### New files

| Path | Responsibility |
|---|---|
| `core/services/policy_abstraction.py` | `abstract_rule()`, `match_generalized_policies()`, LLM abstraction prompt |
| `tests/services/test_policy_abstraction.py` | |

#### Modified files

| Path | Change |
|---|---|
| `core/runtime/db.py` | New `_ensure_generalized_policies_table()` |
| `core/services/learning_policy_engine.py` | After `reinforce_learning_policy()`, check if abstraction should trigger |
| `core/services/counterfactual_engine_runtime.py` | Add abstraction step to cadenced cycle |

### Phase 3 — Loop Closure

#### The orchestrator

A lightweight daemon (`learning_pipeline_orchestrator`) that listens for eventbus events from all six systems and routes outputs to appropriate next-stage inputs:

```
Event: self_evaluation.completed
  → Extract improvement suggestions
  → Call learning_policy_engine.reinforce_learning_policy() with derived rule
  → Call reasoning_store.capture_conclusion()

Event: learning_policy.rule_created (confidence ≥ 0.7)
  → Call policy_abstraction.abstract_rule()
  → Call reasoning_store.capture_conclusion()

Event: counterfactual_simulation.completed
  → Feed preferred_next_policy to agent_skill_distiller
  → Capture in reasoning_store

Event: agent_skill_distiller.completed
  → Updated skills are now in Agent Skill Library
  → No further routing needed (available on next agent spawn)

Event: agent_run.completed
  → Feed outcome to self_evaluation
  → Capture key decisions in reasoning_store
```

This is intentionally SIMPLE — no DAG, no scheduling, no retry logic. Each event handler calls at most 2 downstream functions. The orchestrator is a single file with one callback per event family.

#### Trigger integration

The orchestrator hooks into the existing `phased_heartbeat_tick` REFLECT phase:
- After counterfactual generation
- After self-evaluation
- Before the next agentic round

This avoids adding a new daemon thread — the heartbeat already runs every ~10-30 minutes and has a REFLECT slot that's often underutilized.

#### Modified files

| Path | Change |
|---|---|
| `core/services/learning_pipeline_orchestrator.py` | **New.** Event handlers + REFLECT-phase integration |
| `core/services/phased_heartbeat.py` | Call orchestrator in REFLECT phase |
| `core/eventbus/events.py` | Register new event families for pipeline routing |

### Pipeline health visibility

Each phase of the pipeline publishes a `learning_pipeline.cycle_completed` event with:
- `generalizations_attempted` / `generalizations_created`
- `reasoning_conclusions_captured`
- `policies_routed` (count of inter-system handoffs)
- `elapsed_ms`

These are surfaced in Mission Control alongside counterfactual metrics.

## Rollout — three phases

### Phase 1 (~5-7 days): Reasoning Store

Deploy:
- DB migration (`reasoning_conclusions` table)
- `reasoning_store.py` with capture + semantic search
- Capture hooks in deep_analyze, reasoning_classify, self_evaluation, counterfactual, learning_policy
- `recall_reasoning` tool registered
- Automatic context injection at agentic round start

Verification:
```bash
# Count conclusions captured after 24h
SELECT source, COUNT(*) FROM reasoning_conclusions
 WHERE created_at > datetime('now', '-1 day')
 GROUP BY source;

# Test retrieval
SELECT conclusion FROM reasoning_conclusions
 ORDER BY last_matched_at DESC LIMIT 5;
```

Expected: 10-30 conclusions/day across all sources. Retrieval should return relevant matches for similar tasks.

### Phase 2 (~3-5 days): Policy Abstraktion

Deploy:
- DB migration (`generalized_policies` table)
- `policy_abstraction.py` with LLM abstraction + context matching
- Integration in counterfactual daemon cycle
- Ad-hoc trigger from `reinforce_learning_policy()`

Verification:
- After 3 days: 3-10 generalized policies exist
- Spot-check 5: are they truly general, or just the specific rule rephrased?
- Precision: do matches fire in genuinely related contexts?

### Phase 3 (~3-5 days): Loop Closure

Deploy:
- `learning_pipeline_orchestrator.py`
- REFLECT-phase integration
- Event handlers for all six systems

Verification:
- Eventbus shows `learning_pipeline.cycle_completed` events
- Count of inter-system handoffs per cycle > 0
- Do self-evaluation outcomes actually reach the Learning Policy Engine?

### Killswitch (any phase)

```json
// ~/.jarvis-v2/config/runtime.json
{
  "learning_pipeline_enabled": false,
  "reasoning_store_enabled": false,
  "policy_abstraction_enabled": false
}
```

Each toggle stops its respective daemon/capture. Settings reload within 30s.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM generates vague generalizations | Phase 2 verification: 5 spot-checks. If >60% are generic ("be careful" level), tighten prompt |
| Reasoning Store noise — too many low-value conclusions | Confidence filter at retrieval (default 0.4); source-level enable/disable in settings |
| Context injection adds token pressure | Injected text is max 400 chars (2-3 items). Monitor via `context_pressure` tool. |
| Embedding quality poor for Danish queries | Use existing HuggingFace embedding endpoint; test with Danish-specific queries in Phase 1 |
| Loop closure creates feedback loops | Each system's output is idempotent (UNIQUE constraints). Orchestrator checks for duplicate routing. |
| Performance — embedding on every agentic round | Embedding is ~50ms on local GPU (GTX 1070). Only runs at round start, not per-tool. |

## Success criteria

- **Phase 1:** After 7 days, ≥50 reasoning conclusions captured. Retrieval returns relevant matches for ≥60% of test queries.
- **Phase 2:** After 5 days, ≥5 generalized policies exist with abstraction_level ≠ "concrete". At least 2 matched against genuinely different contexts.
- **Phase 3:** After 3 days, eventbus shows ≥10 `learning_pipeline.cycle_completed` events. At least one full pipeline trace: Self-Evaluation → Learning Policy → Abstraction → Skill Distiller.
- **End state:** Jarvis demonstrates improved behavior on a repeated mistake — the second occurrence is handled differently because the generalized policy fired.

## Out of scope (deferred)

- Real-time within-turn learning (e.g., "I just learned X from this tool call, apply it to the next call")
- Removing the 40-rule cap on Learning Policy Engine (generalization reduces need)
- Cross-workspace learning transfer
- Automated retention/cleanup of old reasoning conclusions
- Visualization of the learning pipeline in Mission Control
