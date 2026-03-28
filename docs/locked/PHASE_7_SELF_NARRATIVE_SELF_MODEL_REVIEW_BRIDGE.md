# Phase 7: Self-Narrative → Self-Model Review Bridge

## Why This Phase Exists

Jarvis v2 now has a rich bounded stack that includes:
- `meaning_significance_signals`
- `temperament_tendency_signals`
- `relation_continuity_signals`
- `self_narrative_continuity_signals` (derived from the above)
- chronicle/consolidation lane
- existing self-model and governed canonical-self workflow

This makes it possible to design a disciplined bridge where self-narrative continuity may later become reviewable input to self-model sharpening — without becoming canonical-self drift, a hidden identity engine, or prompt-bloat.

## What Self-Narrative Continuity Is

- **Source**: Derived from bounded `meaning_significance`, `temperament_tendency`, `relation_continuity`, and chronicle signals
- **Authority**: Non-authoritative runtime support only
- **Layer role**: `runtime-support` (not identity truth)
- **Status in surface**: `canonical_identity_state: not-canonical-identity-truth`
- **What it tracks**: "What developmental line is Jarvis carrying?" (e.g., "becoming-firm around openness", "deepening stewardship around partnership")
- **Grounding**: Always subordinate to runtime truth — never prompt authority, workflow authority, or canonical writeback

## What Self-Model Is

- **Source**: Bounded self-model signals tracked from visible turns
- **Authority**: Non-authoritative runtime support, but closer to identity truth than self-narrative
- **Layer role**: `runtime-support` → may inform selfhood proposals
- **What it tracks**: Jarvis's current self-perception: identity_focus, preferred_work_mode, recurring_tension, growth_direction
- **Relationship to self-narrative**: Self-model provides the "what am I?" context; self-narrative provides the "what am I becoming?" continuity

## What Selfhood Proposals Are

- **Source**: Proposals for SOUL.md / IDENTITY.md changes
- **Authority**: Requires explicit user approval (approval-gated)
- **Layer role**: `canonical-self-boundary`
- **What it enables**: Bounded changes to Jarvis's canonical identity files

## What Canonical Self Is

- **Files**: `SOUL.md`, `IDENTITY.md`
- **Authority**: Protected canonical truth — requires explicit user approval to modify
- **Layer role**: `canonical-identity-truth`
- **What must never happen**: Auto-mutation, hidden writes, or bypass of governance

## Authority Boundary Order

From least to most authoritative:

```
1. self_narrative_continuity (runtime-support, non-authoritative)
2. self_model_signals (runtime-support, informs proposals)
3. selfhood_proposals (governed, requires approval)
4. canonical_self (SOUL.md/IDENTITY.md - protected, explicit approval required)
```

## What Kinds of "Becoming" May Become Reviewable

**May cross the bridge (with governance):**
- Persistent narrative patterns (e.g., "Jarvis consistently deepens around partnership work")
- Emerging self-model alignment (e.g., self-model signals cohere with narrative direction)
- Bounded summaries that can inform selfhood proposals

**Must remain runtime-only:**
- Raw self-narrative continuity signals (not canonical)
- Meaning/temperament/relation signals (bounded support only)
- Chronicle proposals (bounded, not identity truth)

## What Must Never Bypass Governance

- No auto-write to SOUL.md / IDENTITY.md
- No self-narrative → canonical self without explicit approval
- No hidden identity engine that mutates without user knowledge
- No raw self-narrative dumps disguised as identity truth
- No emotional/poetic drift claiming authority

## Relationship to SOUL.md / IDENTITY.md

- Self-narrative may inform selfhood proposals
- Selfhood proposals require explicit user approval
- SOUL.md / IDENTITY.md remain protected canonical self
- Bridge must never bypass the approval-gated workflow

## Relationship to Chronicle / Meaning / Temperament

- Self-narrative is **derived** from chronicle, meaning, temperament, and relation signals
- It does **not replace** any of these — it provides continuity context
- These signals remain bounded runtime support

## Relationship to Mission Control / Observability

- All bridge state must be observable in MC
- `runtime_self_narrative_continuity_signals` already surfaces in MC
- Future bridge state should also surface in MC before becoming selfhood proposals
- "Everything observable. No silent cognition."

## Recommended First Bridge Shape

**Phase 7a: Surface Bridge State**
- Add a new surface `runtime_self_narrative_self_model_bridge` that shows:
  - Active self-narrative continuity signals
  - Coherent self-model signals that align with narrative direction
  - Whether bridge criteria are met (narrative weight + self-model coherence)
- This is read-only, no writes

**Phase 7b: Bounded Review Input**
- Create bounded summaries of self-narrative patterns
- Surface these summaries in MC as "becoming" review input
- Still no writes, just observability

**Phase 7c: Proposal Input (Future)**
- Only after 7a + 7b are stable:
- Allow bounded summaries to inform selfhood proposals
- Always require explicit approval before canonical changes

## Recommended Phased Implementation Order

1. **Phase 7a**: Add bridge surface (read-only, observable)
2. **Phase 7b**: Bounded narrative pattern summaries in MC
3. **Phase 7c**: Optional - allow summaries to inform proposals (future)

## Non-Goals

- No auto-mutation of canonical self
- No hidden identity engine
- No raw self-narrative dump into selfhood
- No emotional/poetic drift as identity truth
- No prompt-bypass for identity authority
- No canonical writes without explicit approval
- Not "make Jarvis have an identity" — it's already bounded

## Acceptance Criteria

- [ ] Self-narrative continuity remains non-authoritative runtime support
- [ ] Bridge state is observable in MC before becoming proposals
- [ ] No writes to SOUL.md / IDENTITY.md without explicit approval
- [ ] Self-model sharpening happens before selfhood proposals
- [ ] Canonical self remains protected
- [ ] No hidden identity engine or silent cognition
- [ ] "Everything observable" principle maintained
