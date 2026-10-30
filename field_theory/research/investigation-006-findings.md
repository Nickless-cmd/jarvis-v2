# Investigation 6: does the retention→adaptation relation transfer?

**Status:** completed transfer test on an independent physical source, 2026-10-30.
Protocol frozen in `experiments/exp_006_order/PROTOCOL.md` and committed before
the source was parsed.

## What was asked

Investigation 5 found on monthly sunspot number that greater retention of
accumulated loss did not increase continuing adaptation: long and cumulative
retention concentrated all weight on one expert and became indistinguishable
from a fixed baseline. That was recorded as a property of the constructed
mechanism, not a general law.

Investigation 6 asks the narrower, discriminating question: **does that
relation transfer to a physically unrelated series under the identical
mechanism?**

This is not a test of Bjørn's progression. Field, identity, perspective,
experience and access are not operationalised here, and no result below
supports or contradicts them.

## Source

- NOAA Global Monitoring Laboratory, Mauna Loa CO₂ monthly mean.
- 823 monthly observations, 1958-03 through 2026-09, no missing values.
- Preserved byte digest in `exp006_results.json`.
- Instrumented, historically revised physical record; not generated for this
  project. The Mauna Loa site was suspended Nov 2022 – Jul 2023 and substituted
  from Maunakea; that discontinuity is inside the evaluation period and is not
  corrected for.

## Mechanism

Copied unchanged from `exp005.learning.1` — the constants are *imported*, not
retyped, so the two runs cannot silently diverge:

- experts: previous month, trailing-12 mean, lag-132;
- loss: `|prediction − outcome| / (1 + |outcome|)`;
- learning rate 2.0, softmax over retained losses;
- retentions 0.0 / 0.9 / 0.99 / 1.0, continued and reset-at-2000 variants;
- development before 2000-01, evaluation from 2000-01.

The fixed expert was selected by development MAE: `previous_month`
(1.0901), against `trailing_12_mean` (1.9662) and `cycle_lag_132` (14.5325).

## Method deviation (2026-10-30): the reset branch never ran

**Status:** deviation recorded; the original run is preserved unchanged in
`artifacts/exp_006_order/noaa_20261030/`. Corrected run in
`artifacts/exp_006_order/noaa_20261030_v2/`.

The first implementation gated the reset on an empty trace:

```python
if reset_at_evaluation and period == "evaluation" and not trace:
    retained = {expert: 0.0 for expert in EXPERTS}
```

`trace` is already filled by the development period when the boundary is
reached, so the condition was never true and **reset never executed**. The
`_reset` variants therefore ran the identical computation as `_continued`,
which was then reported below as an empirical finding about continuity. It was
an instrument fault.

Investigation 5 had the correct form — `observation.date == "2000-01"` — so the
intended behaviour was already documented in this project.

The preserved test asserted that continued and reset produced identical
predictions for every retention. That assertion was the fault wearing a guard's
clothes: it locked in the symptom instead of checking the mechanism. It is
replaced by two tests: one that requires the reset variant's first evaluation
weights to be exactly 1/3 each while the continued variant keeps its
development history, and one that pins how far a reset can reach when retention
is zero.

Two reporting errors are corrected with it: 691 is the number of rows per
mechanism after the 132-month warm-up, not the evaluation length — the
evaluation period is **321 months**. And a mechanism holding 1.886 effective
experts does not by itself show that it keeps learning; a nearly fixed mixture
of two experts can also be almost unresponsive. The measured mean weight change
(0.0016) is the figure that speaks to that, not the effective-expert count.

## Result: the transfer is falsified

Corrected run, `noaa_20261030_v2`, same preserved source digest
(`d8:95:fb:5b:…:07:f6:75`), identical constants imported from
`exp005.learning.1`:

| Mechanism | MAE | Effective experts | Mean weight change |
|---|---:|---:|---:|
| fixed previous_month | 1.1617 | 1.000 | 0.0000 |
| one encounter, continued | 7.6284 | 2.993 | 0.0015 |
| one encounter, reset | 7.6293 | 2.993 | 0.0016 |
| short continuity, continued | 3.9732 | 2.598 | 0.0018 |
| short continuity, reset | 4.0424 | 2.610 | 0.0021 |
| long continuity, continued | 1.3024 | **1.886** | 0.0016 |
| long continuity, reset | 1.5308 | 2.002 | 0.0025 |
| cumulative continuity, continued | 1.1558 | 1.152 | 0.0005 |
| cumulative continuity, reset | 1.4354 | 1.786 | 0.0025 |

The continued rows are bit-identical to the original run — the correction
touched only the branch that had never executed. Both falsification conditions
that could fire, fired:

- `long_continuity_continued` keeps **1.886 effective experts** — above the
  frozen threshold of 1.5. On the solar series the same mechanism collapsed to
  1.000. It does not collapse here.
- `long_continuity_continued` is **12.1 % worse** than the fixed expert in MAE,
  far above the 0.5 % threshold. On the solar series it was identical to the
  fixed expert.

`cumulative_continuity_continued` sits at 1.152 effective experts — below the
threshold — but 0.508 % from the fixed expert, which is above the 0.5 %
threshold by the width of the rounding. It falsifies on the MAE condition
alone, and it is close enough to the boundary that the margin should be read as
"at the threshold", not as a comfortable gap.

## Second result, corrected: reset costs accuracy on this source

With the reset branch actually executing, continued and reset **diverge for
every non-zero retention**. The direction is consistent across all four:

- long continuity: MAE 1.3024 → 1.5308 (+17.5 %), effective experts 1.886 → 2.002
- cumulative continuity: MAE 1.1558 → 1.4354 (+24.2 %), effective experts 1.152 → 1.786
- short continuity: MAE 3.9732 → 4.0424 (+1.7 %)
- one encounter: MAE 7.6284 → 7.6293 (+0.01 %)

So on this source the retained history is *doing work*: discarding it at the
evaluation boundary makes the mechanism worse and pushes it toward the uniform
prior. That is the opposite of what the broken run reported, and it is the
opposite of the solar result, where reset changed nothing for long and
cumulative continuity.

The one-encounter case changes by a single row — the boundary prediction — which
is expected: with retention 0 the retained state is only one observation deep,
so there is almost nothing for a reset to remove.

## What the original run claimed, and why it is withdrawn

The preserved text read: *"Continued and reset variants produced identical
predictions in all 691 evaluation rows for every retention value… the retained
history was not doing any work that a reset could remove."*

Both sentences are withdrawn. The identity was produced by a condition that
could not be satisfied, not by the mechanism reaching a fixed point, and 691 is
not the number of evaluation rows. The observation about saturation — that
`long_continuity_continued` settles at 0.621 / 0.379 and moves by less than
0.002 — is measured and stands, but it no longer carries the claim that reset
was irrelevant.

## What this changes about Investigation 5

The solar finding stands as measured, but its scope narrows. "Continuity became
lock-in" is not a property of the retention rule. It is an interaction between
the retention rule, the expert set, and the source:

- On a series where one expert is persistently and clearly best
  (`previous_month` on sunspots), accumulated loss drives the softmax to a
  one-hot vector and adaptation stops.
- On a series where two experts stay comparably good (`previous_month` and
  `trailing_12_mean` on CO₂), the same rule settles at a stable mixture and
  keeps a small but non-zero responsiveness.

The mechanism is identical. The outcome differs. So the earlier conclusion was
about a *joint* configuration, not about retention as such.

## What this does not show

- Nothing about field, identity, perspective, experience, or access.
- Nothing about whether the atmosphere or the Sun learns.
- Nothing about whether another expert set, learning rate, or loss would
  reverse either result.
- No universality claim. Two sources are two sources, and both are
  instrumented records with their own revision histories.
- The CO₂ series has a strong monotone trend. `previous_month` is near-optimal
  for a trended series by construction, which is a plausible reason the
  adaptive mechanisms cannot beat it. That is an interpretation, not a
  measurement, and it was not tested.

## The methodological point that matters most

The falsification was written down before the run, and it fired. That is the
only reason this result is worth anything: had the thresholds been chosen after
seeing 1.886 and 12.1 %, they could have been set to accommodate either
conclusion.

The same discipline is what Investigation 4's frozen forecasts depend on, and
what the recorded blind-breach deviation protects. It is the one part of this
project that has held under pressure.

## Questions raised

- Is there a source where the two experts are *equally* good, and does the
  mechanism then stay responsive indefinitely?
- Does the fixed point depend on the learning rate, or only on the loss gap
  between experts?
- Can a mechanism be built that retains history without reaching a fixed
  point — and would that be a different relation, or the same one at another
  scale?
- Investigation 5's "continuity became lock-in" and this run's "continuity
  reached a fixed point" — are those the same phenomenon described at two
  levels, or two different ones?
