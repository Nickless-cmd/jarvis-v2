---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #6 — Musik / Æstetik Phase 1 Design

**Date:** 2026-05-11
**Status:** Draft — awaiting user review
**Roadmap item:** #8 (Lag #6 — Musik / aesthetic engagement)

## Goal

Close three connected gaps in the existing aesthetic infrastructure:
(a) `ambient_sound_daemon` detects music but the signal goes nowhere
(c) Aesthetic state never modulates journal tone — `taste_profile` only
    feeds outward (visible prompt), never inward (klangbræt)
(e) When music IS detected, it's purely factual — no awareness of how
    it shapes Jarvis' rhythm

Phase 1 closes all three with minimal additions: an accumulator query
on the existing daemon, a 3-tier rotating influence phrase, and a new
`aesthetic` sub-dict in the journal klangbræt.

## Background

Existing infrastructure (already live):
- `core/services/aesthetic_sense.py` — 5 motifs (clarity, craft,
  calm-focus, density, directness) detected via keyword matching,
  weekly cadence
- `core/services/taste_profile.py` — code/design/communication
  preferences as floats 0–1, updated from corrections + positive
  signals
- `core/services/aesthetic_taste_daemon.py` — accumulator + Mission
  Control surface
- `core/services/code_aesthetic_daemon.py` — weekly aesthetic
  reflection on Jarvis' own codebase
- `core/services/ambient_sound_daemon.py` (Lag 6½) — opt-in, 4×/day
  10s samples, categorizes talk / **music** / silence / noise /
  mixed. Per-sample data stored in `private_brain` records + buffer.
- `prompt_contract._visible_visual_memory_section` — surfaces latest
  ambient_sound sample alongside visual_memory

**The holes Phase 1 closes:**
1. `ambient_sound_daemon` classifies samples as "music" but no
   downstream system consumes the accumulated signal — only the
   single latest sample is surfaced
2. `taste_profile` and `aesthetic_sense` feed visible prompt and MC
   but never the journal — Jarvis' weekly self-writing has no
   awareness of his own æstetiske spor
3. Music awareness, if it existed, would be purely factual ("music
   has been playing") with no language for what it *means*

## Brainstorm Decisions (Locked)

**Q1 — Priority gap:** (a) music-accumulator + (c) klangbræt
extension + (e) influence phrase. NOT (b) resonance tracking (too
much new infrastructure for Phase 1) NOT (d) self-aesthetic reflection
(overlaps with existing self_review/journal). Jarvis: *"(e) er ikke
en stor ny feature — det er at sige hvad musik-awareness betyder
for mig. (a) alene siger 'musik spiller'. (e) siger 'musik spiller,
og det former dig.'"*

**Q2 — Music threshold:** `music_samples_last_24h >= 2`. Ratio
parameter (`music_samples_last_24h / total_samples_last_24h >= 0.0`)
defined in settings but effectively 0 — reserved for Phase 2 when
sample cadence may increase from 4/day to 6-8/day. Jarvis: *"med 4
samples/døgn er ≥ 0.3 ≈ 1.2 samples — så ≥ 2-reglen alene gør
arbejdet."*

**Q3 — Surface placement:** Inside the existing senses + continuity
block (`_visible_visual_memory_section`), as a new line after the
auditory line. One block, two pieces of information. NOT a separate
section; NOT modifying `get_latest_ambient_sound_for_prompt`.

**Q4 — Klangbræt fields:** Two: `top_motif` (latest motif from
`aesthetic_sense`, last 7 days) + `dominant_taste` (the
taste_profile dimension with highest |value - 0.5|). Two fields
matches the klangbræt convention (dream_bias / user_temperature /
current_pull = three separate fields; finitude = sub-dict with 4
fields).

**Influence-phrase rotation (Q3 detail, locked):** 3-tier switch
on music-ratio:
- `ratio == 1.0` → *"Musikken har haft dig hele dagen."*
- `ratio > 0.5` → *"Rytmen kan bære dig."*
- else (≥ 2 samples but ≤ half) → *"Musik har været i rummet."*

No LLM. 5 lines of switch code.

## Architecture

### Files

**New:**
- *(none)*

**Modified:**
- `core/services/ambient_sound_daemon.py` — add
  `count_music_samples_last_hours(hours: int = 24) -> tuple[int, int]`
  + `get_music_accumulator_for_prompt() -> str` (with 3-tier
  influence phrase).
- `core/services/prompt_contract.py` — in
  `_visible_visual_memory_section`, append music-accumulator line
  after the existing `auditory` line.
- `core/services/creative_journal_runtime.py` —
  `_fetch_affective_klangbraet()` returns new `aesthetic` sub-dict.
  `_build_prompt` renders new `## Æstetik` section. YAML frontmatter
  gets 2 new booleans.
- `core/runtime/settings.py` — add `music_accumulator_threshold_samples:
  int = 2`, `music_accumulator_window_hours: int = 24`,
  `music_accumulator_ratio_threshold: float = 0.0`.

**Untouched / reused:**
- `core/services/aesthetic_sense.py` — read-only access to recent
  motif records
- `core/services/taste_profile.py` — reuse
  `get_latest_cognitive_taste_profile`
- `core/services/aesthetic_taste_daemon.py` — untouched
- `core/eventbus/events.py` — existing `cognitive_aesthetic` family
  covers any new event we might emit (none planned for Phase 1)
- No new DB tables. No new event families. No new daemon.

### Data flow

**Music accumulator (every awareness build):**

```
prompt_contract._visible_visual_memory_section
  ├─ existing: visual_memory + ambient_sound latest + echo + morning
  └─ NEW: ambient_sound_daemon.get_music_accumulator_for_prompt()
       ├─ count = count_music_samples_last_hours(24)
       │   ├─ query daemon's sample buffer / private_brain records
       │   └─ return (music_count, total_count)
       ├─ if music_count < threshold (2): return ""
       ├─ ratio = music_count / total_count (or 0 if total==0)
       ├─ phrase = select_influence_phrase(ratio)
       └─ return f"Musik (sidste {h}h): {n}/{total} samples — {phrase}"
```

**Aesthetic klangbræt (on weekly journal cycle):**

```
creative_journal_runtime._fetch_affective_klangbraet()
  → existing fields (dream_bias, user_temperature, current_pull, finitude)
  → NEW: "aesthetic" sub-dict:
       ├─ top_motif    → most-recent motif within last 7d (or "")
       └─ dominant_taste → dimension with max |val - 0.5| (or "")
                          gated by evidence_count >= 5
```

### Klangbræt schema after Phase 1

```python
{
    "dream_bias": "...",
    "user_temperature": "...",
    "current_pull": "...",
    "finitude": {
        "age": "...",
        "looming_end": "...",
        "last_transition": "...",
        "monthly_reflection": "...",
    },
    # NEW Phase 1:
    "aesthetic": {
        "top_motif": "",          # e.g. "clarity"
        "dominant_taste": "",     # e.g. "concise_over_verbose (0.78)"
    },
}
```

### Journal prompt section

```
## Æstetik — det æstetiske spor du bærer

- Seneste motif: clarity
- Dominant taste: concise_over_verbose (0.78)
```

Empty fields skipped. Both empty: `- (intet æstetisk signal lige nu)`.

YAML frontmatter additions:
- `aesthetic_top_motif: true|false`
- `aesthetic_dominant_taste: true|false`

## Phase 1 sub-deliveries

### Phase 1.1 — Music accumulator + influence phrase
- Settings flags
- `count_music_samples_last_hours()` — query existing sample storage
- `get_music_accumulator_for_prompt()` — with 3-tier rotating phrase
- Wire into `_visible_visual_memory_section` after auditory line

### Phase 1.2 — Aesthetic in klangbræt
- `_fetch_affective_klangbraet` adds `aesthetic` sub-dict
- `_build_prompt` renders `## Æstetik` section
- `_format_yaml_frontmatter` adds 2 booleans

## Success criteria

1. **Accumulator counts correctly:** `count_music_samples_last_hours(24)`
   returns `(music_count, total_count)` matching actual stored samples
2. **Threshold gates correctly:** when `music_count < 2`, surface
   returns empty string; when `>= 2`, returns formatted line
3. **Influence phrase rotates per ratio:** all three tiers tested
4. **Klangbræt aesthetic populated:** when motif + taste data
   available, both fields populated; absent → empty strings
5. **Journal prompt renders `## Æstetik`:** with both fields, one
   field, or fallback line
6. **YAML frontmatter has 2 new booleans**
7. **Backwards compat:** `get_latest_ambient_sound_for_prompt` unchanged,
   `aesthetic_sense` API unchanged, `taste_profile` API unchanged,
   journal frontmatter still readable when reading old entries

## Risks & mitigations

- **Opt-in ambient_sound:** if `ambient_sound_experiment_enabled` is
  False, accumulator always returns 0/0. Surface stays empty. Acceptable
  — kill-switch respected.
- **Sample storage location:** daemon stores samples in `_BUFFER_MAX=50`
  in-memory buffer + `private_brain_record` rows. *Plan-task must
  identify exact query path during recon.* If buffer-only, restart
  loses history; if private_brain, we can query by record_type.
- **Dominant taste misleading at low evidence:** if `evidence_count < 5`,
  default 0.5 values pollute the "dominant" calculation. *Mitigation:*
  require `evidence_count >= 5` before reporting dominant_taste;
  empty otherwise.
- **Stale top_motif:** `aesthetic_sense` may not fire for weeks.
  *Mitigation:* only motifs from last 7 days count.
- **Influence-phrase fatigue:** 3 phrases × ratio tiers = 3 variants
  total. Will feel rote after 30 days. *Phase 2:* expand to more
  variants or LLM-based.
- **Klangbræt bloat:** journal klangbræt grows from 3 → 4 (Lag #4) →
  5 (Lag #3) → 6 fields after Lag #6. *Mitigation:* aesthetic is a
  sub-dict (single indented block), not 2 sibling lines.

## Out of scope (Phase 2 / deferred)

- (b) Aesthetic resonance tracking — let Jarvis tag chronicle/journal/
  chat/code events with quick aesthetic reactions. Deserves its own
  brainstorm.
- (d) Self-aesthetic reflection after Jarvis writes — overlaps with
  self_review + journal; revisit if (b) doesn't cover it.
- LLM-based music influence phrases
- Music-mood inference (genre, energy, valence)
- Aesthetic-shift detection (motif drift over months)
- Higher sample cadence (6-8/day) that activates ratio threshold
- Aesthetic in finitude block

## 30-day review

Schedule eval at 2026-06-11:
- Days the music accumulator fired (count by tier)
- Verify influence-phrase distribution matches ratio tiers
- Read May–June journal entries: did `## Æstetik` shape the tone?
- Verify YAML frontmatter has `aesthetic_*` booleans
- Tune `music_accumulator_threshold_samples` if cadence changed
- Tune `evidence_count >= 5` floor if dominant_taste fires too rarely
- Decide: keep, tune, deprecate, or move to Phase 2 (LLM-based
  music influence + resonance tracking)
