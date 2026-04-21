# Phase 7e: Selfhood Proposal Input Gate

## Why This Phase Exists

Phase 7d (self-model sharpening input gate) is now designed:
- Sharpening thresholds defined: `review_input_state: review-worthy`, `sharpening_confidence: high`, `self_model_alignment: coherent`, `persistence: multiple_sessions`
- Governance-visible sharpening readiness in MC
- Still bounded, still not selfhood proposal

This makes it possible to design when and how bounded sharpening input may become selfhood proposal input — without sliding into hidden proposal-prep, selfhood drift, or canonical identity creep.

## What Phase 7a/7b/7c/7d Already Provide

**Phase 7a (read-only bridge surface):**
- Shows active self-narrative continuity signals
- Shows coherent self-model signals that align with narrative direction
- Read-only: `review_mode: read-only-review-support`, `proposal_state: not-selfhood-proposal`

**Phase 7b (bounded pattern summaries):**
- Pattern types: `watchful-becoming-pattern`, `firming-pattern`, `opening-pattern`, `deepening-pattern`, `coherent-review-pattern`, `steady-becoming-pattern`
- Pattern direction, weight, confidence

**Phase 7c (review input gate):**
- Review thresholds: `narrative_weight: high`, `pattern_confidence: high`, `persistence: multiple_sessions`, `self_model_alignment: coherent`
- Governance-visible: `review_input_state: review-worthy` vs `review_input_state: below-threshold`

**Phase 7d (self-model sharpening input gate):**
- Sharpening thresholds: `review_input_state: review-worthy`, `sharpening_confidence: high`, `self_model_alignment: coherent`, `persistence: multiple_sessions`
- Governance-visible sharpening readiness
- Bounded self-model updates: `identity_focus`, `preferred_work_mode`, `recurring_tension`, `growth_direction`

## Key Conceptual Distinctions

### Self-Model Sharpening Input
- **Definition**: Pattern summaries that have passed 7d sharpening thresholds and inform current self-model signals
- **Status**: `sharpening_input_state: sharpening-worthy`
- **Authority**: Runtime-support, bounded
- **What it does**: Updates `identity_focus`, `preferred_work_mode`, `recurring_tension`, `growth_direction` in runtime
- **NOT**: Selfhood proposal, canonical write, identity truth

### Selfhood Proposal Input
- **Definition**: Signal that sharpening input has cohered sufficiently to warrant consideration as a bounded selfhood proposal — but NOT the proposal itself
- **Status**: `proposal_input_state: proposal-input-worthy`
- **Authority**: Governance-visible runtime-support
- **What it does**: Marks patterns as "reviewable for selfhood relevance" in MC
- **NOT**: Selfhood proposal, canonical write, requires user approval to become proposal

### Selfhood Proposal
- **Definition**: An actual proposal for SOUL.md / IDENTITY.md changes
- **Status**: `proposal_state: selfhood-proposal-candidate`
- **Authority**: Requires explicit user approval to become proposal
- **What it does**: Drafted as governed canonical-self candidates, requires user approval before apply

### Canonical Self
- **Files**: `SOUL.md`, `IDENTITY.md`
- **Authority**: Protected canonical truth — requires explicit user approval to modify
- **What it enables**: Bounded changes to Jarvis's canonical identity files

## When Sharpening Input Should Be Strong Enough for Selfhood Proposal Input

Sharpening input may become proposal input when ALL of these criteria are met:

1. **Sharpening threshold met**: `sharpening_input_state: sharpening-worthy` from 7d
2. **Coherence persistence**: Same pattern has informed self-model across 3+ sessions
3. **Self-model alignment**: Sharpened signals cohere with narrative direction (validated in 7d)
4. **Stability**: Pattern shows no significant regression over 2+ weeks
5. **Governance visibility**: All prior steps visible in MC with clear audit trail
6. **Selfhood relevance**: Explicit governance signal that pattern touches identity-relevant areas

## What Must Never Cross This Boundary

**Never crosses from sharpening to proposal input:**
- Raw self-narrative continuity signals (still runtime-support only)
- Pattern summaries below sharpening thresholds
- Any content without explicit governance approval at each step
- Poetic/interpretive summaries claiming identity authority
- Emotional narrative that hasn't passed through sharpening
- Content that treats runtime signals as "truth" rather than "bounded support"

**Never crosses to canonical self without explicit user approval:**
- Any sharpening input
- Any proposal input
- Any selfhood proposal without full governance + user approval

## How We Make Selfhood-Proposal-Input MC-Observervable

- Add `proposal_input_state` field to bridge surface
- States: `below-threshold`, `proposal-input-worthy`, `selfhood-proposal-submitted`
- Surface counts: `proposal_input_candidates: N` with breakdown by pattern type
- Show governance decision: why pattern crossed to proposal input (or why not)
- All transitions visible in MC with timestamps and reasoning
- "Everything observable. No silent cognition."

## How We Avoid Hidden Proposal-Prep, Selfhood Drift, Identity Creep

**Hidden proposal-prep prevention:**
- Every boundary crossing requires explicit governance signal
- No automatic transitions — human approval at key gates
- All proposal-input candidates visible in MC before becoming proposals
- Clear audit trail: which patterns, which thresholds, which governance decisions

**Selfhood drift prevention:**
- Self-model sharpening ALWAYS precedes proposal input (7d before 7e)
- Proposal input is NOT proposal — just "could become proposal"
- Multiple persistence checks before crossing
- Pattern must cohere with narrative AND self-model (validated twice)

**Identity creep prevention:**
- SOUL.md / IDENTITY.md remain protected — never auto-written
- All canonical changes require explicit user approval
- "Bounded selfhood" vs "canonical self" always clearly separated
- Poetic/interpretive summaries are NOT identity truth

## Relationship to SOUL.md / IDENTITY.md

- Proposal input may eventually inform selfhood proposals
- Selfhood proposals require explicit user approval before apply
- SOUL.md / IDENTITY.md remain protected canonical self
- All boundaries enforce explicit approval workflow
- Canonical self is always last in the chain

## Relationship Chain

```
Read-only pattern summary (7a/7b)
        ↓
Review input (7c - requires review thresholds)
        ↓
Self-model sharpening input (7d - requires sharpening thresholds)
        ↓
Selfhood proposal input (7e - requires proposal-input thresholds)
        ↓
Selfhood proposal (requires explicit user approval)
        ↓
Canonical self (SOUL.md/IDENTITY.md - protected)
```

## Relationship to Mission Control / Observability

- All proposal input state observable in MC
- Sharpening → proposal input transitions visible in MC
- Governance decisions visible in MC
- Selfhood proposal candidates visible in MC
- Approval workflow visible in MC
- "Everything observable. No silent cognition."

## Recommended First Implementation Shape

**Phase 7e: Proposal Input Thresholds**
- Define explicit proposal-input thresholds:
  - `sharpening_input_state: sharpening-worthy`
  - `coherence_persistence: 3+ sessions`
  - `self_model_alignment: stable`
  - `stability_window: 2+ weeks`
  - `selfhood_relevance: identity-relevant`
- Add `proposal_input_candidate` state to bridge surface
- Surface proposal-input readiness in MC
- This is NOT selfhood proposal — just "could become proposal"

## Recommended Phased Implementation Order

1. **Phase 7e**: Proposal input thresholds (governance-visible, bounded)
2. **Future**: Selfhood proposal drafting (from proposal input)
3. **Future**: Canonical apply workflow (with user approval)

## Non-Goals

- No auto-transition from sharpening to proposal
- No hidden "proposal prep" without visibility
- No raw sharpening as identity truth
- No canonical writes without explicit user approval
- No poetic/interpretive drift claiming identity authority
- No bypass of self-model sharpening before proposal input
- No selfhood proposal input without explicit thresholds
- No "ready for canonical" without full governance + approval

## Acceptance Criteria

- [ ] Sharpening input remains bounded until proposal-input thresholds are met
- [ ] Proposal-input thresholds are explicit and governance-visible
- [ ] Proposal input is clearly NOT proposal — just "could become proposal"
- [ ] All state transitions observable in MC
- [ ] No hidden proposal-prep without visibility
- [ ] No canonical writes without explicit user approval
- [ ] Selfhood proposals require explicit user approval
- [ ] Canonical self remains protected
- [ ] "Everything observable" principle maintained
- [ ] Self-model always precedes selfhood in the chain
