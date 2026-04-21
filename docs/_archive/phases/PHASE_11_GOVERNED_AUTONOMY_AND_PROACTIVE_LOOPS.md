# Phase 11: Governed Autonomy / Proactive Loop Architecture

## Why This Phase Exists

Jarvis v2 now has a rich bounded runtime stack:
- heartbeat liveness foundation (scheduling, weighting, companion pressure)
- open_loop_signals (open → softening → closed lifecycle)
- private_initiative_tension_signals (initiative pressure without execution authority)
- relation_state_signals, relation_continuity_signals
- meaning_significance_signals, temperament_tendency_signals
- witness signals (becoming_weight, maturation_weight, persistence_weight)
- metabolism_state signals (carrying, releasing, consolidating)
- attachment topology, loyalty gradients
- protected canonical self
- governed USER/MEMORY/selfhood workflows
- open_loop_closure_proposals

Existing runtime already tracks:
- `open_loop` status: open → softening → closed (14d stale)
- `initiative_tension`: initiative pressure without authority
- `regulation_homeostasis`: effort regulation signals
- `open_loop_closure_proposals`: bounded closure candidates

This makes it possible to design a governed autonomy subsystem that enables:
- bounded self-started loops
- proactive UI questions (when legitimately warranted)
- bounded carry-forward behavior
- bounded follow-up
- loop closure semantics

Without becoming hidden planner authority, uncontrolled autonomy, or canonical drift.

## Conceptual Distinctions

### Liveness Pressure
- **Definition**: Runtime signals indicating Jarvis is "alive" and active
- **Authority**: Runtime-support
- **Examples**: heartbeat ticks, active runs, session continuity

### Autonomy Pressure
- **Definition**: Runtime signals indicating Jarvis has internal drive to act, without execution authority
- **Authority**: Runtime-support, non-authoritative
- **Examples**: initiative_tension, open_loop pressure, carrying forward
- **NOT**: Planner authority, execution permission

### Proactive Loop
- **Definition**: A bounded self-started thread that Jarvis tracks and may act upon
- **Authority**: Runtime-support
- **Lifecycle**: open → softening → closed (governed by open_loop signals)
- **NOT**: Planner task, execution command

### Proactive Question
- **Definition**: A bounded UI-initiated question when Jarvis has legitimate internal drive
- **Authority**: Runtime-support, requires explicit gating
- **Triggered by**: Strong autonomy pressure + relation continuity + meaning significance
- **NOT**: Blanket permission to interrupt, uncontrolled messaging

### Loop Closure
- **Definition**: The governed ending of a proactive loop
- **Authority**: Runtime-support, may inform proposals
- **Path**: open_loop closure → open_loop_closure_proposal → governance → (optional) apply

### Planner Authority
- **Definition**: The actual decision engine for what Jarvis executes
- **Authority**: Planner authority (separate from autonomy)
- **NOT**: Autonomy signals are observation, planner decides independently

### Canonical Intention Truth
- **Definition**: Actual intentions stored in SOUL.md/IDENTITY.md
- **Authority**: Protected canonical truth
- **NOT**: Autonomy loops are runtime support, not canonical

## What Governed Autonomy Provides

- **autonomy_pressure**: Current internal drive level (from initiative_tension + open_loops)
- **proactive_loop_count**: Number of active open loops
- **loop_lifecycle_state**: open / softening / closed / stale
- **proactive_question_candidates**: When autonomy pressure warrants UI question
- **closure_readiness**: When loops are ready for closure proposal

## What It Is NOT

- **NOT planner authority**: Does not decide what to execute
- **NOT uncontrolled autonomy**: Always bounded and observable
- **NOT blanket proactive messaging**: Requires explicit gating
- **NOT canonical intention truth**: Runtime support only
- **NOT hidden authority**: Everything visible in MC

## Authority Boundaries

```
Heartbeat (input)
  - liveness foundation
  - authority: runtime-support

Open Loops (input)
  - open → softening → closed lifecycle
  - authority: runtime-support

Initiative Tension (input)
  - autonomy pressure without execution
  - authority: runtime-support

Regulation/Homeostasis (input)
  - effort regulation signals
  - authority: runtime-support

Governed Autonomy (Phase 11 - synthesis)
  - autonomy_pressure, proactive_loop_count, closure_readiness
  - authority: runtime-support, non-authoritative
  - NOT: planner authority, canonical truth

Proactive Questions (gated)
  - requires: high autonomy_pressure + relation_continuity + meaning_significance
  - authority: runtime-support, requires explicit gating
  - NOT: blanket permission

Loop Closure (governed)
  - open_loop_closure_proposal → governance → apply
  - authority: governance-gated

Planner (separate)
  - decides what to execute
  - authority: planner authority

Canonical Self
  - SOUL.md, IDENTITY.md
  - authority: protected, explicit approval required
```

## Relationship to Heartbeat / Liveness / Relation / Witness / Chronicle / Metabolism / Attachment

**Heartbeat:**
- Provides liveness foundation for autonomy
- Autonomy requires heartbeat to be alive

**Liveness:**
- Active runs, sessions, continuity
- Autonomy pressure builds when liveness is established

**Relation:**
- Provides relation_continuity for proactive question gating
- Proactive questions require relation continuity

**Witness:**
- Provides becoming_weight, persistence_weight
- Helps determine if loops are becoming stable

**Chronicle:**
- Provides consolidation patterns
- Loop closure may inform chronicle consolidation

**Metabolism:**
- Provides carrying, release patterns
- Helps determine loop aging and release

**Attachment:**
- Provides loyalty gradients
- Helps determine what loops matter most

## Relationship to Self-Model / Selfhood / Canonical Self

```
Heartbeat + Liveness + Open Loops + Initiative Tension + Regulation
        ↓
Governed Autonomy (Phase 11 - observation)
        ↓
Proactive Question Candidates (gated)
        ↓
Loop Closure Proposals (governed)
        ↓
Open Loop Closure Proposals (governance + approval)
        ↓
Chronicle Consolidation (optional)
```

**Key points:**
- Autonomy is observation, never proposal directly
- Loop closure may inform chronicle, not selfhood
- Selfhood remains separate (from phase 7 chain)
- Canonical self always protected

## Relationship to Planner/Autonomy Authority (Must Remain Separate)

**Governed Autonomy:**
- Observes: "What internal drive does Jarvis have?"
- Authority: Runtime-support, non-authoritative
- Output: autonomy_pressure, loop_count, closure_readiness

**Planner:**
- Decides: "What should I work on next?"
- Authority: Planner authority
- May observe autonomy signals but decides independently

**Critical separation:**
- Autonomy NEVER tells planner what to do
- Autonomy NEVER becomes planner priority
- Autonomy signals are input, planner decides
- Proactive questions are UI-facing, not execution

## How to Keep Autonomy Observerable But Not Authoritative

1. **Always bounded**: All loops have lifecycle (open → softening → closed)
2. **Always MC-visible**: All autonomy signals visible in MC
3. **Always non-authoritative**: Observation only, no execution
4. **Proactive questions gated**: Requires high autonomy_pressure + relation_continuity + meaning_significance
5. **Loop closure governed**: Requires proposal → governance → approval
6. **Never planner-facing**: No direct connection to planner execution
7. **Audit trail**: Clear why autonomy pressure increased

## How to Avoid Hidden Planner / Autonomy Sprawl / Canonical Drift

**Hidden planner prevention:**
- No direct wiring from autonomy to planner execution
- Clear that planner decides independently
- Proactive questions are UI, not execution commands

**Autonomy sprawl prevention:**
- Bounded loop lifecycle prevents unlimited loops
- Explicit gating for proactive questions
- Closure proposals require governance

**Canonical drift prevention:**
- SOUL.md/IDENTITY.md never touched by autonomy
- Loop closure informs chronicle, not canonical self
- Clear separation from selfhood chain (phase 7)

## Recommended First Implementation Shape

**Phase 11a: Autonomy Pressure Synthesis**
- Synthesize autonomy_pressure from:
  - initiative_tension signals
  - open_loop count and age
  - regulation_homeostasis state
- Surface in MC: current autonomy_pressure level

**Phase 11b: Proactive Loop Lifecycle**
- Track loop aging: how long has each loop been open
- Track loop softening: when loops start releasing
- Surface in MC: loop lifecycle visualization

**Phase 11c: Proactive Question Gate**
- Define explicit gating criteria:
  - autonomy_pressure: high
  - relation_continuity: strong
  - meaning_significance: significant
  - no recent user messages (to avoid interruption)
- Surface: proactive_question_candidates in MC (not yet active)

**Phase 11d: Loop Closure Flow**
- Strengthen open_loop_closure_proposal pathway
- Ensure closure proposals go through governance
- Surface closure_readiness in MC

## Recommended Phased Implementation Order

1. **Phase 11a**: Autonomy pressure synthesis
2. **Phase 11b**: Proactive loop lifecycle tracking
3. **Phase 11c**: Proactive question gate (candidates only)
4. **Phase 11d**: Loop closure governance flow
5. **Future**: Actual proactive question activation (if governance approves)

## Non-Goals

- No planner authority
- No uncontrolled autonomy
- No blanket proactive messaging
- No canonical intention truth
- No prompt-bypass
- No hidden planner wiring
- No direct execution from autonomy
- No selfhood connection
- No canonical drift

## Acceptance Criteria

- [ ] Autonomy is bounded runtime-support, not planner authority
- [ ] All loops have observable lifecycle (open → softening → closed)
- [ ] Proactive questions require explicit gating
- [ ] Loop closure goes through governance
- [ ] Clear separation from planner (observation vs decision)
- [ ] Clear separation from canonical self
- [ ] All autonomy signals visible in MC
- [ ] No hidden planner wiring
- [ ] No canonical writes
- [ ] "Everything observable" principle maintained
