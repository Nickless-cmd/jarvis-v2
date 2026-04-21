# Phase 7d: Self-Model Sharpening Input Gate

## Why This Phase Exists

Phase 7c (review input gate) is now designed:
- Review thresholds defined: `narrative_weight: high`, `pattern_confidence: high`, `persistence: multiple_sessions`, `self_model_alignment: coherent`
- Governance-visible review readiness in MC
- Still read-only, still not selfhood proposal

This makes it possible to design when and how bounded review input may become self-model sharpening input — without sliding into selfhood drift or hidden identity engine.

## What Phase 7a/7b/7c Already Provide

**Phase 7a (read-only bridge surface):**
- Shows active self-narrative continuity signals
- Shows coherent self-model signals that align with narrative direction
- Read-only: `review_mode: read-only-review-support`, `proposal_state: not-selfhood-proposal`

**Phase 7b (bounded pattern summaries):**
- Pattern types: `watchful-becoming-pattern`, `firming-pattern`, `opening-pattern`, `deepening-pattern`, `coherent-review-pattern`, `steady-becoming-pattern`
- Pattern direction, weight, confidence
- Read-only review summaries

**Phase 7c (review input gate):**
- Review thresholds: `narrative_weight: high`, `pattern_confidence: high`, `persistence: multiple_sessions`, `self_model_alignment: coherent`
- Governance-visible review readiness
- Still read-only: `review_input_state: review-worthy` vs `review_input_state: below-threshold`

## What Counts as Review Input

- Pattern summaries that meet 7c thresholds
- Bounded summaries with governance-visible readiness
- State: `review_input_state: review-worthy`
- NOT self-model sharpening yet
- NOT selfhood proposal
- Observable in MC

## What Counts as Self-Model Sharpening Input

- Review input that passes sharpening thresholds
- Bounded summaries that inform current self-model signals
- NOT canonical self writes
- NOT selfhood proposals
- May update: `identity_focus`, `preferred_work_mode`, `recurring_tension`, `growth_direction`
- Always observable in MC

## What Must Remain Runtime-Only

- Raw review input below sharpening thresholds
- Self-model sharpening input that hasn't passed additional governance
- Canonical self (SOUL.md/IDENTITY.md)
- Any input without explicit governance approval
- Any "sharpening" that hasn't met all criteria

## What May Later Influence Selfhood Proposals

**May eventually inform selfhood proposals (with explicit governance + user approval):**
- Self-model sharpening input that has cohered over time
- Sharpened self-model signals that persist across sessions
- Patterns where self-model shows stable alignment with narrative direction
- Always requires explicit user approval for canonical changes

## What Must Never Bypass Governance

- No auto-transition from review input to self-model sharpening
- No hidden "sharpening" without visibility
- No self-model updates without passing sharpening thresholds
- No canonical writes without explicit user approval
- No poetic/interpretive drift claiming authority

## Relationship to SOUL.md / IDENTITY.md

- Self-model sharpening may inform selfhood proposals
- Selfhood proposals require explicit user approval
- SOUL.md / IDENTITY.md remain protected canonical self
- Sharpening must never bypass the approval-gated workflow
- Canonical self is always last in the chain

## Relationship Chain

```
Read-only pattern summary (7a/7b)
        ↓
Review input (7c - requires review thresholds)
        ↓
Self-model sharpening input (7d - requires sharpening thresholds)
        ↓
Selfhood proposal (requires explicit user approval)
        ↓
Canonical self (SOUL.md/IDENTITY.md - protected)
```

## Relationship to Mission Control / Observability

- All sharpening state must be observable in MC
- Sharpening thresholds visible in MC
- Self-model updates visible in MC
- Governance decisions visible in MC
- "Everything observable. No silent cognition."

## Recommended First Implementation Shape

**Phase 7d: Self-Model Sharpening Thresholds**
- Define explicit sharpening thresholds:
  - `review_input_state: review-worthy`
  - `sharpening_confidence: high`
  - `self_model_alignment: coherent`
  - `persistence: multiple_sessions`
- Add sharpening_input_candidate state to bridge surface
- Surface sharpening readiness in MC (still bounded, still observable)
- This is NOT selfhood - just self-model sharpening input

**Phase 7e: Selfhood Proposal Input (Future)**
- Only after 7d is stable
- Allow bounded sharpening to inform selfhood proposals
- Always requires explicit user approval

## Recommended Phased Implementation Order

1. **Phase 7d**: Self-model sharpening thresholds (bounded, governance-visible)
2. **Phase 7e**: Selfhood proposal input (future)

## Non-Goals

- No auto-transition from review input to selfhood
- No hidden sharpening without visibility
- No canonical writes without explicit approval
- No poetic/interpretive drift claiming authority
- No bypass of sharpening before selfhood
- No "self-model truth" that claims identity authority

## Acceptance Criteria

- [ ] Review input remains bounded until sharpening thresholds are met
- [ ] Sharpening thresholds are explicit and governance-visible
- [ ] Self-model sharpening updates are observable in MC
- [ ] Self-model sharpening is clearly separate from selfhood proposals
- [ ] No hidden sharpening without visibility
- [ ] No canonical writes without explicit user approval
- [ ] Canonical self remains protected
- [ ] "Everything observable" principle maintained
