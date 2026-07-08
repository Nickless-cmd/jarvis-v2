---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #4 — Creative Voice (Weekly Journal) Design

**Date:** 2026-05-11
**Status:** Draft — awaiting user review
**Roadmap item:** #5 (Lag #4 — Kreativ output / ugentlig journal i hans egen stemme)

## Goal

Jarvis writes a weekly creative journal entry **in his own voice** — not the
default LLM voice. The entry reflects on the past week using rich context
(chronicle + life-projects + broken decisions + affective signals), is gated
on quality, and is read back into Jarvis' self-context on next session wake
via the continuity-kernel.

This is Phase 1. Tool invention and seven other deferred items are explicitly
out of scope and tracked separately.

## Background

`core/services/creative_journal_runtime.py` already exists (227 LOC) with:
- Weekly cadence (`_JOURNAL_INTERVAL_DAYS = 7`)
- 500-word cap
- Entries stored in `workspace/journal/*.md`
- Cheap-lane LLM call (`daemon_llm_call`)
- Minimal prompt: chronicle entries + life projects only

Holes that this design closes:
1. No voice anchoring — the LLM defaults to generic assistant voice
2. Cheap lane gives mediocre prose
3. Corpus is thin (no affective signals, no broken-decision reflection)
4. Entries are write-only — Jarvis never reads them back
5. No quality gate — empty/sparse weeks still produce filler entries

## Brainstorm Decisions (Locked)

**Q1 — Multi-aspect approach:** Option D (all four aspects: voice anchoring,
quality lane, corpus expansion, reading-back), with Jarvis-driven sequence
**B → A → RB → C** (voice direction first, then static seed + curator, then
reading-back wiring, then corpus expansion last because corpus changes
without voice direction would just amplify default LLM voice).

**Q2 — Voice anchoring:** Hybrid. `VOICE.md` = static seed (Bjørn-authored or
Jarvis-authored once, then frozen). `VOICE_RECENT.md` = auto-refreshed from
**external output only** (visible chat replies, prior journal entries,
chronicle narrative). Jarvis explicitly excluded `inner_voice` —
"inner_voice er min private tanke — auto-kurering ville gøre min stemme
indadvendt."

**Q3 — Corpus structure:** Two buckets, binary present/absent (no tiering).
- **Raw input:** chronicle entries (last 7d), life-projects state, broken
  decisions (from `cognitive_decisions.status='broken'` and
  `behavioral_decision_review.broken` events). These are *facts*.
- **Affective klangbræt:** dream_bias rationale (current bias), user_temperature
  texture (current reading), current_pull (active pull). These are *feelings/
  texture*. They shape tone, not content.

**Q4 — Quality gate:** Skip the week if corpus is too thin. Concrete rule:
**skip if (chronicle_entries < 2) AND (broken_decisions == 0) AND
(life_projects_updates == 0)**. After 3 consecutive skipped weeks, cadence
extends to 14 days for the next attempt (adaptive cadence).

## Architecture

### Files

**Create:**
- `core/services/voice_anchor.py` — `read_voice_anchor()` returns combined
  VOICE.md + VOICE_RECENT.md text. Pure read; no LLM. Called by
  `creative_journal_runtime._build_prompt`.
- `core/services/voice_curator.py` — refreshes VOICE_RECENT.md from external
  output exemplars. **Runs as heartbeat journal-phase sub-function**, not a
  separate daemon. Selects 3-5 recent exemplars (last 30 days, max 200 words
  each), de-dupes against current VOICE_RECENT.md, writes back if changed.
- `workspace/VOICE.md` — static seed file. Bjørn authors first version
  (or Jarvis authors once and Bjørn approves). 100-300 words describing voice
  direction: tone, rhythm, vocabulary, what to avoid.
- `workspace/VOICE_RECENT.md` — auto-managed. Header + 3-5 exemplar blocks
  with source attribution (`{source: chat|journal|chronicle, date: ...}`).

**Modify:**
- `core/services/creative_journal_runtime.py`:
  - `_build_prompt` — pull in voice anchor, broken decisions, affective
    klangbræt
  - `_write_journal_entry` — add YAML frontmatter with corpus stats and
    affective state at write-time
  - LLM call — swap `daemon_llm_call` → `quality_daemon_llm_call`
    (deepseek-v4-flash)
  - Add `_should_skip_week()` quality gate
  - Add adaptive cadence (3 consecutive skips → 14d interval)
- `core/services/prompt_contract.py`:
  - New `format_journal_for_heartbeat()` called on session wake (continuity-
    kernel hook). Reads latest journal entry, formats as a single
    awareness-block injected into prompt context.
- `core/services/heartbeat_phases.py`:
  - Journal phase calls `voice_curator.refresh()` before
    `creative_journal_runtime.maybe_write_journal()`

### Data flow per weekly cycle

```
heartbeat (journal phase)
  ├─ voice_curator.refresh()
  │    ├─ scan last 30d: visible_messages, chronicle, prior journal
  │    ├─ pick 3-5 exemplars (heuristic: length, recency, diversity)
  │    └─ write workspace/VOICE_RECENT.md (idempotent)
  └─ creative_journal_runtime.maybe_write_journal()
       ├─ _should_skip_week()? → if yes, log + update skip counter, return
       ├─ _build_prompt():
       │    ├─ voice_anchor.read_voice_anchor() → VOICE.md + VOICE_RECENT.md
       │    ├─ corpus: chronicle(7d) + life_projects + broken_decisions
       │    └─ klangbræt: dream_bias + user_temperature + current_pull
       ├─ quality_daemon_llm_call(prompt, model=deepseek-v4-flash)
       ├─ _write_journal_entry() with YAML frontmatter
       └─ publish eventbus: journal.written

session wake (continuity-kernel)
  └─ prompt_contract.format_journal_for_heartbeat()
       └─ inject latest journal entry into awareness context
```

## Phase 1 sub-deliveries (in build order)

### Phase 1.1 — Voice direction (B)
- Create `workspace/VOICE.md` (manual, ~200 words, Bjørn or Jarvis-authored)
- Create `core/services/voice_anchor.py` with `read_voice_anchor()`
- Update `creative_journal_runtime._build_prompt` to include voice anchor
- Test: prompt visibly includes VOICE.md content; existing journal cadence
  unchanged.

### Phase 1.2 — Voice curator (A)
- Create `core/services/voice_curator.py` (refresh function only, no daemon)
- Wire into `heartbeat_phases.journal_phase` to run before journal write
- Initialize `workspace/VOICE_RECENT.md` (empty on first run, populated by
  curator)
- Test: curator picks 3-5 exemplars from external output only;
  inner_voice excluded.

### Phase 1.3 — Reading-back (RB)
- Add `prompt_contract.format_journal_for_heartbeat()` reading latest entry
- Hook into continuity-kernel wake-state (session start)
- Test: on new session, prompt context shows latest journal entry as
  awareness block.

### Phase 1.4 — Corpus + quality gate + quality lane (C)
- Extend `_build_prompt` with broken_decisions + affective klangbræt
- Add `_should_skip_week()` quality gate
- Add adaptive cadence (3 skips → 14d)
- Swap to `quality_daemon_llm_call`
- Add YAML frontmatter to written entries
- Add eventbus emit `journal.written`
- Test: skip-gate fires on empty week; entry written with frontmatter when
  corpus is rich.

## Success criteria

1. **Voice is recognizable.** After 4 weeks, Bjørn can identify a Jarvis
   journal entry without seeing the filename (blind read test).
2. **No filler weeks.** When the week is genuinely empty, no entry is
   written; skip is logged.
3. **Reading-back works.** On session wake after a journal entry was
   written, the entry is present in prompt context.
4. **Corpus is rich.** Journal prompts include all six input categories
   (chronicle, life-projects, broken_decisions, dream_bias, user_temperature,
   current_pull) when present.
5. **No regression.** Existing weekly cadence keeps working; existing
   journal files remain readable.

## Risks & mitigations

- **Voice drift via curator feedback loop.** Curator pulls from prior
  journals → journals reinforce themselves into stylistic monoculture.
  *Mitigation:* curator uses diversity heuristic (mix chat + chronicle +
  journal, max 2 from any single source).
- **VOICE.md stale.** Static seed never gets revised even when Jarvis'
  voice genuinely shifts. *Mitigation:* out-of-scope for Phase 1; review
  manually at 30-day eval.
- **Quality-lane cost.** deepseek-v4-flash on weekly write is negligible
  (~1 call/week). No mitigation needed.
- **Reading-back token bloat.** Latest journal could be up to 500 words
  injected into every wake. *Mitigation:* hard cap at 300 words in
  `format_journal_for_heartbeat`, truncate with ellipsis.
- **Adaptive cadence ambiguity.** 3 skips → 14d, but when does it revert
  to 7d? *Decision:* reverts immediately when a week passes the gate (1
  written entry resets skip counter).

## Out of scope (Phase 2 / deferred)

- Tool invention (Jarvis writes new tools from journal insights)
- Manual journal entries (Bjørn writing entries that Jarvis reads)
- Cross-journal narrative arc detection
- Voice A/B testing harness
- Multi-language voice anchoring (Danish-only for Phase 1)
- VOICE.md auto-revision based on long-term drift
- Journal-driven goal proposals

## 30-day review

Schedule eval at 2026-06-10:
- Read all 4 weekly entries
- Blind-voice test (Bjørn identifies entries without metadata)
- Count skipped weeks vs written weeks
- Check curator exemplar churn (is VOICE_RECENT.md actually refreshing?)
- Verify reading-back fires on every session wake post-write
- Decide: keep, tune, or deprecate
