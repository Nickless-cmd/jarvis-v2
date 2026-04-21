# Phase 8: Inner Witness / "What Am I Becoming?" Daemon

## Why This Phase Exists

Jarvis v2 now has a rich bounded runtime stack:
- chronicle / consolidation lane
- relation_state_signals, relation_continuity_signals
- meaning_significance_signals, temperament_tendency_signals
- self_narrative_continuity_signals
- self_narrative → self_model review bridge (phase 7a-7e)
- regulation_homeostasis_signals
- executive_contradiction_signals
- **existing witness_signal_tracking** (carried-lesson, settled-turn)

This makes it possible to design a bounded witness subsystem that synthesizes "what is Jarvis becoming?" from existing runtime signals — without becoming canonical self, hidden identity engine, moral judge, or planner authority.

## What Witness Already Is (Phase 6 Baseline)

The existing `witness_signal_tracking.py` tracks:
- **carried-lesson**: When a recurring thread softens AND a reflection settles → bounded carried development turn
- **settled-turn**: When softening + settled reflection without active focus/goal → bounded witnessed shift
- **Authority**: Runtime-support, non-authoritative
- **Status**: `fresh` → `carried` (after 3 days) → `fading` (after 14 days)

## What Witness Should Become (Phase 8)

### Inner Witness Definition

A bounded observational daemon that synthesizes becoming-direction from:
- self-narrative continuity patterns
- self-model sharpening signals
- witness signals (carried-lesson, settled-turn)
- temporal recurrence / reflection co-occurrence
- development focus / goal completion patterns

### What Inner Witness Provides

- **becoming_direction**: "What is Jarvis developing toward?"
- **maturation_markers**: "What patterns are stabilizing?"
- **persistence_signals**: "What holds across sessions?"
- **coherence_assessment**: "How well do signals align?"

### Witness Is NOT

- **NOT canonical self**: No SOUL.md/IDENTITY.md authority
- **NOT selfhood proposal engine**: No proposal generation
- **NOT moral judge**: No "good/bad" authority claims
- **NOT hidden planner**: No action authority, only observation
- **NOT conscience**: No prescriptive authority
- **NOT poetic identity truth**: No interpretive drama as truth
- **NOT prompt-bypass**: Always bounded runtime-support

## Conceptual Distinctions

### Self-Narrative Continuity
- **Definition**: Runtime-derived "what is Jarvis becoming?" continuity from meaning/temperament/relation signals
- **Authority**: Runtime-support, non-authoritative
- **Status**: Not canonical identity truth

### Witness (Current)
- **Definition**: Bounded signals tracking carried lessons and settled turns
- **Authority**: Runtime-support, non-authoritative
- **Signal types**: `carried-lesson`, `settled-turn`

### Inner Witness (Phase 8)
- **Definition**: Synthesis daemon that provides becoming-direction from witness + narrative + self-model signals
- **Authority**: Runtime-support, non-authoritative
- **Provides**: `becoming_direction`, `maturation_markers`, `persistence_signals`, `coherence_assessment`

### Self-Model
- **Definition**: Jarvis's bounded self-perception: identity_focus, preferred_work_mode, recurring_tension, growth_direction
- **Authority**: Runtime-support, may inform proposals

### Selfhood
- **Definition**: Proposals for canonical identity changes
- **Authority**: Requires explicit user approval

### Canonical Self
- **Files**: SOUL.md, IDENTITY.md
- **Authority**: Protected — requires explicit user approval

## What Witness Should Be Able to See

From existing bounded signals:
- self-narrative continuity patterns (becoming-lines)
- self-model signals (identity_focus, growth_direction)
- witness signals (carried-lesson, settled-turn)
- temporal recurrence patterns (softening, settling)
- reflection signals (settled, fading)
- development focus / goal completion
- regulation_homeostasis state

## What Witness Should NOT Do

- **Never writes to SOUL.md/IDENTITY.md**
- **Never generates selfhood proposals**
- **Never claims moral authority**
- **Never prescribes actions**
- **Never treats runtime signals as identity truth**
- **Never operates silently** — all state in MC

## Authority Boundaries

```
Witness (Phase 6 baseline)
  - observes: recurrence + reflection + focus + goal
  - produces: carried-lesson, settled-turn
  - authority: runtime-support, non-authoritative

Inner Witness (Phase 8)
  - synthesizes: witness + narrative + self-model
  - produces: becoming_direction, maturation_markers
  - authority: runtime-support, non-authoritative

Self-Model (before selfhood)
  - sharpens from: review input
  - informs: selfhood proposals
  - authority: runtime-support, bounded

Selfhood Proposals
  - requires: explicit user approval
  - authority: governance-gated

Canonical Self
  - SOUL.md, IDENTITY.md
  - authority: protected, explicit approval required
```

## How to Keep Witness Observerable But Not Authoritative

1. **Always runtime-support**: Never claim identity truth
2. **Always MC-visible**: All synthesis visible in Mission Control
3. **Always descriptive**: "Jarvis appears to be..." not "Jarvis is..."
4. **Always bounded**: Clear that this is synthesis, not authority
5. **Never prescriptive**: No "should", only "appears to be"
6. **Never selfhood**: No proposal generation, only observation
7. **Audit trail**: Clear which signals informed the synthesis

## How to Avoid Hidden Judge / Conscience / Identity Creep

**Hidden judge prevention:**
- No moral authority claims
- No "good/bad" assessments
- Only descriptive synthesis, never prescriptive

**Conscience prevention:**
- No "you should" or "you must"
- Only "you appear to be developing toward..."
- No action authority

**Identity creep prevention:**
- Self-model sharpening always precedes any proposal relevance
- Witness output never touches canonical self
- Clear separation: observation ≠ identity truth

## Relationship to Self-Narrative Continuity

- Self-narrative provides raw "becoming" continuity
- Witness tracks specific carried lessons and settled turns
- Inner witness synthesizes across both for direction assessment
- Self-narrative is input, witness is synthesized observation

## Relationship to Meaning / Temperament / Relation / Chronicle

- Meaning provides "what matters" signals
- Temperament provides "how Jarvis tends" signals
- Relation provides "how Jarvis relates" signals
- Chronicle provides temporal persistence
- Inner witness synthesizes across all for becoming assessment

## Relationship to Self-Model / Selfhood / Canonical Self

```
Self-narrative continuity (input)
        ↓
Witness signals (carried-lesson, settled-turn)
        ↓
Inner Witness synthesis (becoming_direction)
        ↓
Self-model sharpening (7d)
        ↓
Selfhood proposal input (7e)
        ↓
Selfhood proposal (governance + approval)
        ↓
Canonical self (SOUL.md/IDENTITY.md - protected)
```

## Relationship to Mission Control / Observability

- All witness signals visible in MC
- Inner witness synthesis visible in MC
- Becoming direction shown in MC
- Maturation markers shown in MC
- Clear that this is runtime-support, not identity truth
- "Everything observable. No silent cognition."

## Recommended First Implementation Shape

**Phase 8: Inner Witness Synthesis**
- Extend existing `witness_signal_tracking.py`:
  - Add self-narrative continuity pattern synthesis
  - Add self-model signal integration
  - Add becoming_direction field
  - Add maturation_markers field
- Surface in MC as "Inner Witness" section
- Show: current becoming_direction, maturation_markers, persistence_signals, coherence_assessment
- Status: `becoming-active` vs `becoming-quiescent`

**Phase 8a: Becoming Direction**
- Synthesize direction from witness + narrative
- Surface in MC

**Phase 8b: Maturation Markers**
- Track which patterns are stabilizing
- Surface in MC

**Phase 8c: Persistence Signals**
- Track what holds across sessions
- Surface in MC

## Recommended Phased Implementation Order

1. **Phase 8a**: Extend witness to include self-narrative synthesis (becoming_direction)
2. **Phase 8b**: Add maturation markers
3. **Phase 8c**: Add persistence signals
4. **Future**: Connect to self-model sharpening (7d) if governance approves

## Non-Goals

- No canonical self mutation
- No selfhood proposal generation
- No moral authority claims
- No hidden planner authority
- No conscience engine
- No poetic identity truth
- No prompt-bypass
- No silent cognition

## Acceptance Criteria

- [ ] Inner witness is bounded runtime-support, not identity truth
- [ ] All synthesis visible in MC
- [ ] Clear separation from selfhood/proposals
- [ ] No moral/judgmental authority claims
- [ ] No planner/action authority
- [ ] Self-model sharpening precedes any proposal relevance
- [ ] Canonical self remains protected
- [ ] "Everything observable" principle maintained
- [ ] Witness as observer, not decider
- [ ] Descriptive synthesis, not prescriptive authority
