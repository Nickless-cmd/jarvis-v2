# Phase 7c: Self-Narrative Review Input Gate

## Why This Phase Exists

Phase 7a (bridge surface) and 7b (pattern summaries) are now implemented:
- `runtime_self_narrative_self_model_review_bridge` surfaces in MC
- Read-only pattern summaries show becoming-lines
- All state is observable in MC

This makes it possible to design when and how bounded narrative pattern summaries may become review input to self-model sharpening — without sliding into hidden proposal-prep or identity creep.

## What Phase 7a and 7b Already Provide

**Phase 7a (read-only bridge surface):**
- Shows active self-narrative continuity signals
- Shows coherent self-model signals that align with narrative direction
- Read-only: `review_mode: read-only-review-support`, `proposal_state: not-selfhood-proposal`
- All observable in MC

**Phase 7b (bounded pattern summaries):**
- Pattern types: `watchful-becoming-pattern`, `firming-pattern`, `opening-pattern`, `deepening-pattern`, `coherent-review-pattern`, `steady-becoming-pattern`
- Pattern direction, weight, confidence
- Read-only review summaries

## What Counts as Read-Only Pattern Summary

- Narrative becoming-lines (e.g., "becoming-firm around openness")
- Pattern types derived from self-narrative continuity
- Bounded summaries without proposal intent
- Always: `review_mode: read-only-review-support`
- Always: `proposal_state: not-selfhood-proposal`

## What Counts as Review Input

- Pattern summaries that meet explicit review thresholds
- Bounded summaries that can inform self-model sharpening
- NOT selfhood proposals yet
- NOT canonical self writes
- Still observable in MC

## What Must Remain Runtime-Only

- Raw self-narrative continuity signals
- Individual meaning/temperament/relation signals
- Chronicle proposals
- Any pattern that hasn't met review thresholds
- Any summary without explicit governance approval

## What May Later Sharpen Self-Model

**May cross to self-model sharpening (with explicit governance):**
- High-confidence coherent patterns that persist across sessions
- Pattern summaries where self-model alignment is strong
- Patterns where `bridge_weight: high` and `pattern_confidence: high`
- Only after explicit governance criteria are met

## What May Later Inform Selfhood Proposals

**May eventually inform selfhood proposals (with explicit governance + user approval):**
- Pattern summaries that have been through self-model sharpening
- Patterns where self-model signals cohere with narrative direction
- Patterns that pass additional governance review
- Always requires explicit user approval for canonical changes

## What Must Never Bypass Governance

- No auto-transition from pattern summary to proposal
- No hidden "proposal prep" that happens without visibility
- No narrative patterns becoming selfhood without going through self-model sharpening first
- No canonical writes without explicit user approval
- No raw narrative dumps disguised as identity truth

## Relationship to SOUL.md / IDENTITY.md

- Pattern summaries may inform selfhood proposals
- Selfhood proposals require explicit user approval
- SOUL.md / IDENTITY.md remain protected canonical self
- Bridge must never bypass the approval-gated workflow
- Canonical self is always last in the chain

## Relationship to Self-Model / Selfhood / Canonical Self

```
Read-only pattern summary (7a/7b)
        ↓
Review input (7c - requires thresholds)
        ↓
Self-model sharpening (requires explicit governance)
        ↓
Selfhood proposal (requires explicit user approval)
        ↓
Canonical self (SOUL.md/IDENTITY.md - protected)
```

## Relationship to Mission Control / Observability

- All review input state must be observable in MC
- Pattern summaries visible in MC
- Review thresholds visible in MC
- Governance decisions visible in MC
- "Everything observable. No silent cognition."

## Recommended First Implementation Shape

**Phase 7c: Review Input Thresholds**
- Define explicit review thresholds:
  - `narrative_weight: high`
  - `pattern_confidence: high`  
  - `persistence: multiple_sessions`
  - `self_model_alignment: coherent`
- Add review_input_candidate state to bridge surface
- Surface review readiness in MC (still read-only)
- This is NOT proposal - just review input readiness

**Phase 7d: Self-Model Sharpening Input (Future)**
- Only after 7c is stable
- Allow high-confidence patterns to inform self-model signals
- Still observable, still bounded

**Phase 7e: Selfhood Proposal Input (Future)**
- Only after 7d is stable
- Allow bounded summaries to inform selfhood proposals
- Always requires explicit user approval

## Recommended Phased Implementation Order

1. **Phase 7c**: Review input thresholds (read-only, governance-visible)
2. **Phase 7d**: Self-model sharpening input (future)
3. **Phase 7e**: Selfhood proposal input (future)

## Non-Goals

- No auto-transition from summary to proposal
- No hidden proposal-prep
- No raw narrative dumps as identity truth
- No canonical writes without explicit approval
- No poetic/interpretive drift claiming authority
- No bypass of self-model sharpening before selfhood

## Acceptance Criteria

- [ ] Pattern summaries remain read-only until thresholds are met
- [ ] Review input thresholds are explicit and governance-visible
- [ ] Self-model sharpening happens before any selfhood implications
- [ ] All state observable in MC
- [ ] No hidden proposal-prep
- [ ] No canonical writes without explicit user approval
- [ ] Canonical self remains protected
- [ ] "Everything observable" principle maintained
