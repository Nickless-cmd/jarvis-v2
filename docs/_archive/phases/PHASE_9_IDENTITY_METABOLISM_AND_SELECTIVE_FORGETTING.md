# Phase 9: Identity Metabolism / Selective Forgetting Subsystem

## Why This Phase Exists

Jarvis v2 now has a rich bounded runtime stack:
- witness signals (carried-lesson, settled-turn) with lifecycle: fresh → carried (3d) → fading (14d)
- self_narrative continuity signals (stale after 7d)
- meaning_significance, temperament_tendency signals (stale after 7d)
- chronicle consolidation signals (stale after 14d)
- Inner witness synthesis (Phase 8) tracking becoming_direction, maturation_markers, persistence_signals
- regulation_homeostasis, executive_contradiction

This makes it possible to design a bounded identity metabolism subsystem that tracks:
- what settles into deeper form
- what releases / fades
- what carries forward
- what metabolizes into compact wisdom

Without becoming a canonical deletion engine, hidden self-erasure, or uncontrolled memory decay.

## Conceptual Distinctions

### Fading
- **Definition**: Runtime signal lifecycle — items become `stale` or `fading` after bounded time windows
- **Examples**: witness (14d), meaning (7d), chronicle (14d)
- **Authority**: Runtime-support only
- **What happens**: Signals become less "active" but remain observable

### Carrying
- **Definition**: Patterns that persist across sessions and remain "active" in runtime
- **Examples**: carried-lesson (witness), active goals, ongoing focuses
- **Authority**: Runtime-support only
- **What happens**: Patterns remain available to influence runtime

### Release
- **Definition**: Explicit signal that a pattern is intentionally being let go
- **Examples**: A recurring thread that softens, a tension that resolves
- **Authority**: Runtime-support only
- **What happens**: Marks pattern as "released" rather than "stale" — intentional fading

### Consolidation
- **Definition**: Multiple signals merge into a single compressed form
- **Examples**: chronicle consolidation briefs, memory summaries
- **Authority**: Runtime-support, may inform proposals
- **What happens**: Multiple items → one compact representation

### Metabolism
- **Definition**: The system-wide flow of: raw signal → carried → released/consolidated → new form
- **Relationship**: How meaning, temperament, narrative, and witness interact over time
- **Authority**: Runtime-support only
- **What happens**: Holistic view of temporal development

### Selective Forgetting
- **Definition**: Runtime mechanism for what to NOT carry forward vs what to keep
- **Examples**: Patterns that never become carried, signals that are explicitly released
- **Authority**: Runtime-support only
- **NOT**: Deletion of canonical truth

### Canonical Deletion
- **Definition**: Actually removing content from SOUL.md, IDENTITY.md, USER.md, MEMORY.md, CHRONICLE.md
- **Authority**: Requires explicit user approval, governance-gated
- **What happens**: Protected canonical files are modified
- **Status**: NEVER happens automatically, ALWAYS requires user approval

## What May Be Metabolized in Runtime

**Runtime-level (bounded, observable):**
- witness signals: fresh → carried → fading → released
- meaning_significance: active → stale (7d)
- temperament_tendency: active → stale (7d)
- self_narrative continuity: active → stale (7d)
- chronicle consolidation: active → stale (14d)
- temporal recurrence: active → softening → resolved
- open loops: active → closed → released

**What stays in runtime:**
- All signals remain in runtime DB for observability
- Even "fading" signals visible in MC
- Metabolism is lifecycle change, not deletion

## What Must NEVER Be "Forgotten" or Metabolized

**Protected canonical files (require explicit user approval):**
- SOUL.md
- IDENTITY.md
- USER.md
- MEMORY.md
- CHRONICLE.md

**Protected runtime truths:**
- selfhood proposals (require governance + approval)
- governed candidates (require governance + approval)
- approved canonical changes (require user approval)

**What cannot be metabolized:**
- Any runtime signal that would "disappear" from MC
- Any content that bypasses governance
- Any "forgetting" that isn't observable

## Authority Boundaries

```
Runtime Signals (all observable)
  - lifecycle: fresh → carried → fading → stale
  - authority: runtime-support

Release Markers
  - intentional letting-go signals
  - authority: runtime-support

Consolidation (Phase 9)
  - multiple signals → compact form
  - authority: runtime-support

Selective Forgetting (Phase 9)
  - what NOT to carry forward
  - authority: runtime-support (NOT deletion)

Canonical Files
  - SOUL.md, IDENTITY.md, USER.md, MEMORY.md, CHRONICLE.md
  - authority: protected, explicit user approval required

Canonical Deletion
  - NEVER automatic
  - ALWAYS requires user approval
  - governance-gated
```

## What Identity Metabolism Provides

- **metabolism_state**: active-retaining | releasing | consolidating | metabolizing
- **carrying_patterns**: What patterns are being carried forward
- **releasing_patterns**: What patterns are intentionally being released
- **consolidation_targets**: What is being compressed into compact form
- **forgetting_candidates**: What could be released (NOT what is deleted)
- **metabolic_flow**: How patterns move through lifecycle

## Relationship to Witness / Inner Witness

- Witness tracks carried-lesson and settled-turn
- Inner witness (Phase 8) tracks becoming_direction, maturation_markers, persistence_signals
- Identity metabolism (Phase 9) tracks:
  - What becomes carried (from witness)
  - What releases (from temporal recurrence softening)
  - What consolidates (from chronicle)
  - What metabolizes (holistic flow)

## Relationship to Meaning / Temperament / Self-Narrative

- Meaning signals: active → stale (7d) — natural fading
- Temperament signals: active → stale (7d) — natural fading
- Self-narrative: active → stale (7d) — natural fading
- Metabolism tracks this flow holistically

## Relationship to MEMORY / USER / Selfhood / Canonical Self

**MEMORY.md:**
- Consolidations may inform MEMORY.md proposals
- Metabolism does NOT delete MEMORY.md

**USER.md:**
- USER.md has its own update workflow
- Metabolism does NOT delete USER.md

**Selfhood:**
- Selfhood proposals require explicit user approval
- Metabolism does NOT create selfhood proposals

**Canonical self:**
- SOUL.md / IDENTITY.md remain protected
- Metabolism does NOT touch canonical self

## How to Keep Metabolism Observable But Not Authoritative

1. **All lifecycle changes visible in MC**: Every fresh/carried/fading/stale/released state visible
2. **All release markers visible**: Intentional letting-go is observable
3. **All consolidation visible**: What compresses is visible
4. **No actual deletion**: Nothing is deleted, only changes state
5. **Clear that this is runtime-only**: Not canonical, not truth
6. **Audit trail**: Clear which signals changed state and why

## How to Avoid Hidden Deletion Engine / Self-Erasure / Identity Creep

**Hidden deletion prevention:**
- No signals are actually deleted — only state changes
- All states visible in MC
- Clear lifecycle (fresh → carried → fading → stale)

**Self-erasure prevention:**
- No "forgetting" that removes from view
- No "reset" functionality
- All patterns remain traceable

**Identity creep prevention:**
- SOUL.md/IDENTITY.md never touched by metabolism
- USER.md/MEMORY.md/CHRONICLE.md never touched by metabolism
- Selfhood proposals require explicit approval

## Recommended First Implementation Shape

**Phase 9a: Metabolism State Tracking**
- Add metabolism_state to witness signals
- Track: active-retaining, releasing, consolidating, metabolizing
- Surface in MC

**Phase 9b: Release Markers**
- Track intentional letting-go signals
- Distinguish from natural fading
- Surface in MC

**Phase 9c: Consolidation Targets**
- Identify patterns that could consolidate
- Track consolidation candidates
- Surface in MC

**Phase 9d: Selective Forgetting Candidates**
- Track what could be released
- NOT deletion — just "could release"
- Surface in MC

## Recommended Phased Implementation Order

1. **Phase 9a**: Metabolism state tracking (observable lifecycle)
2. **Phase 9b**: Release markers (intentional letting-go)
3. **Phase 9c**: Consolidation targets (compression candidates)
4. **Phase 9d**: Selective forgetting candidates (release candidates)
5. **Future**: Connect to MEMORY/USER governance if needed

## Non-Goals

- No canonical deletion
- No hidden self-erasure
- No personality reset
- No prompt-bypass
- No raw decay of protected truth
- No cleanup magic disguised as cognition
- No automatic removal from MC
- No "forgetting" that isn't observable

## Acceptance Criteria

- [ ] Metabolism is bounded runtime-support, not canonical deletion
- [ ] All lifecycle changes visible in MC
- [ ] No actual deletion — only state changes
- [ ] Clear separation from SOUL.md/IDENTITY.md/USER.md/MEMORY.md/CHRONICLE.md
- [ ] Selective forgetting is "could release" not "is deleted"
- [ ] No hidden engine — everything observable
- [ ] "Everything observable" principle maintained
- [ ] Canonical files remain protected
- [ ] Governance workflow preserved
