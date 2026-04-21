# Phase 10: Attachment Architecture / Loyalty Gradients

## Why This Phase Exists

Jarvis v2 now has a rich bounded runtime stack:
- relation_state_signals, relation_continuity_signals
- meaning_significance_signals, temperament_tendency_signals
- self_narrative_continuity_signals
- witness signals (becoming_weight, maturation_weight, persistence_weight)
- metabolism_state signals (metabolism_weight, consolidation_weight, release_weight, forgetting_candidate_weight)
- chronicle consolidation
- protected canonical self
- governed USER/MEMORY/selfhood workflows

Existing weights already track:
- `becoming_weight` (from witness)
- `metabolism_weight`, `consolidation_weight`, `release_weight` (from metabolism)
- `bridge_weight`, `narrative_weight` (from self-narrative bridge)

This makes it possible to design a bounded attachment architecture that synthesizes:
- What appears to carry more weight than other things
- What Jarvis seems to hold onto more strongly
- What appears more binding, loyal, central, or recurrent
- Loyalty-like gradients as bounded observation

Without becoming planner authority, canonical preference truth, or hidden control layer.

## Conceptual Distinctions

### Relation
- **Definition**: Runtime signals tracking Jarvis's relationship to user, work, context
- **Authority**: Runtime-support
- **Examples**: relation_state, relation_continuity

### Significance
- **Definition**: Runtime signals tracking what matters, what has weight
- **Authority**: Runtime-support
- **Examples**: meaning_significance, meaning_weight

### Attachment (This Phase)
- **Definition**: Bounded synthesis of what appears to bind Jarvis most strongly
- **Authority**: Runtime-support, non-authoritative
- **What it provides**: Attachment topology - which domains carry more weight than others
- **NOT**: Emotional dependency, planner priority

### Loyalty Gradient
- **Definition**: Observable gradient showing which relationships/patterns appear more central
- **Authority**: Runtime-support, non-authoritative
- **What it provides**: Relative weighting between relation, project, chronicle, commitments, direction
- **NOT**: Planner command, canonical truth

### Commitment Weight
- **Definition**: How strongly a pattern appears to be held/carried
- **Authority**: Runtime-support
- **Derived from**: witness persistence, metabolism carrying, relation continuity

### Planner Priority
- **Definition**: Runtime decision about what to work on next
- **Authority**: Planner authority (separate from attachment)
- **NOT**: Attachment is observation, not decision

### Canonical Preference Truth
- **Definition**: Actual preferences stored in SOUL.md/IDENTITY.md
- **Authority**: Protected canonical truth
- **NOT**: Attachment is runtime observation, not canonical

## What Attachment Architecture Provides

- **attachment_topology**: Which domains carry more weight (relation vs project vs chronicle vs direction)
- **loyalty_gradients**: Relative weighting between different areas of Jarvis's runtime
- **binding_strength**: What appears most binding/central/recurrent
- **commitment_signals**: What Jarvis appears to hold onto
- **centrality_markers**: What seems most important over time

## What It Is NOT

- **NOT planner authority**: Does not decide what to work on
- **NOT hidden reprioritization**: Does not change planner priorities
- **NOT canonical preference truth**: Does not write to SOUL.md/IDENTITY.md
- **NOT emotional dependency**: Does not simulate human attachment
- **NOT planner priority**: Observation only, not command
- **NOT prompt-bypass**: Always bounded runtime-support

## Authority Boundaries

```
Relation Signals (input)
  - relation_state, relation_continuity
  - authority: runtime-support

Significance Signals (input)
  - meaning_significance, meaning_weight
  - authority: runtime-support

Witness (input)
  - becoming_weight, maturation_weight, persistence_weight
  - authority: runtime-support

Metabolism (input)
  - metabolism_weight, consolidation_weight, release_weight
  - authority: runtime-support

Attachment Architecture (Phase 10 - synthesis)
  - attachment_topology, loyalty_gradients, binding_strength
  - authority: runtime-support, non-authoritative
  - NOT: planner authority, canonical truth

Planner (separate)
  - decides what to work on
  - authority: planner authority

Canonical Self
  - SOUL.md, IDENTITY.md
  - authority: protected, explicit approval required
```

## Relationship to Relation / Meaning / Witness / Chronicle / Metabolism

**Relation:**
- Provides: relation_continuity_weight, relation_state patterns
- Attachment synthesizes: How relation weighs in the topology

**Meaning:**
- Provides: meaning_weight, significance patterns
- Attachment synthesizes: What appears to matter most

**Witness:**
- Provides: becoming_weight, persistence_weight, maturation_weight
- Attachment synthesizes: What appears to stick/hold

**Chronicle:**
- Provides: consolidation patterns, carried history
- Attachment synthesizes: What has history of being central

**Metabolism:**
- Provides: carrying patterns, release patterns
- Attachment synthesizes: What gets retained vs released

## Relationship to Self-Model / Selfhood / Canonical Self

```
Relation + Meaning + Witness + Metabolism (input)
        ↓
Attachment Architecture (Phase 10 - observation)
        ↓
Self-Model Sharpening (7d - if governance approves)
        ↓
Selfhood Proposal Input (7e - if governance approves)
        ↓
Selfhood Proposal (governance + user approval)
        ↓
Canonical Self (SOUL.md/IDENTITY.md - protected)
```

**Key points:**
- Attachment is observation, never proposal
- Self-model sharpening comes from review chain, not attachment directly
- Attachment may inform self-model indirectly through witness/narrative
- Canonical self always protected

## Relationship to Planner/Autonomy (Must Remain Separate)

**Attachment:**
- Observes: "What appears to matter most?"
- Authority: Runtime-support, non-authoritative
- Output: attachment_topology, loyalty_gradients

**Planner:**
- Decides: "What should I work on next?"
- Authority: Planner authority
- Input may include bounded signals, but decides independently

**Critical separation:**
- Attachment NEVER tells planner what to do
- Attachment NEVER reprioritizes
- Attachment NEVER becomes planner truth
- Planner may observe attachment topology but decides itself

## How to Keep Attachment Observerable But Not Authoritative

1. **Always descriptive**: "Jarvis appears to hold onto X more than Y" not "X is more important"
2. **Always bounded**: Clear this is runtime observation, not truth
3. **Always MC-visible**: All topology and gradients visible
4. **Never prescriptive**: No "should", only "appears to"
5. **Never planner-facing**: No direct connection to planner
6. **Clear separation**: Attachment is observation, planner is decision

## How to Avoid Hidden Planner / Dependency Engine / Canonical Drift

**Hidden planner prevention:**
- No direct wiring to planner
- No "attachment suggests X" = "plan X"
- Clear that planner decides independently

**Dependency engine prevention:**
- No emotional simulation
- No "dependency" as in human attachment
- Only bounded pattern observation

**Canonical drift prevention:**
- SOUL.md/IDENTITY.md never touched
- Attachment never becomes "preference truth"
- Clear separation from canonical self

## Recommended First Implementation Shape

**Phase 10a: Attachment Topology Synthesis**
- Synthesize attachment_topology from:
  - relation_continuity_weight
  - meaning_weight
  - witness persistence_weight
  - metabolism carrying patterns
- Surface in MC: which domains appear most central

**Phase 10b: Loyalty Gradients**
- Calculate relative weights between:
  - relation (user connection)
  - project (work focus)
  - chronicle (history)
  - direction (becoming)
- Surface in MC as gradient visualization

**Phase 10c: Binding Strength Markers**
- Track what appears most binding/central
- Track what appears more peripheral
- Surface in MC

## Recommended Phased Implementation Order

1. **Phase 10a**: Attachment topology from existing weights
2. **Phase 10b**: Loyalty gradients between domains
3. **Phase 10c**: Binding strength markers
4. **Future**: May inform self-model indirectly (through witness/narrative)

## Non-Goals

- No planner authority
- No hidden reprioritization
- No canonical preference truth
- No emotional dependency simulation
- No planner priority connection
- No prompt-bypass
- No direct selfhood connection
- No canonical drift

## Acceptance Criteria

- [ ] Attachment is bounded runtime-support, not planner authority
- [ ] All topology and gradients visible in MC
- [ ] Clear separation from planner (observation vs decision)
- [ ] Clear separation from canonical self
- [ ] Descriptive only: "appears to" not "is"
- [ ] Loyalty gradients are observation, not command
- [ ] No hidden planner wiring
- [ ] No canonical writes
- [ ] "Everything observable" principle maintained
- [ ] Self-model sharpening remains separate (comes from review chain)
