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

## Result: the transfer is falsified

| Mechanism | MAE | Effective experts | Mean weight change |
|---|---:|---:|---:|
| fixed previous_month | 1.1617 | 1.000 | 0.0000 |
| one encounter, continued | 7.6284 | 2.993 | 0.0015 |
| short continuity, continued | 3.9732 | 2.598 | 0.0018 |
| long continuity, continued | 1.3024 | **1.886** | 0.0016 |
| cumulative continuity, continued | 1.1558 | 1.152 | 0.0005 |

Both falsification conditions that could fire, fired:

- `long_continuity_continued` keeps **1.886 effective experts** — above the
  frozen threshold of 1.5. On the solar series the same mechanism collapsed to
  1.000. It does not collapse here.
- `long_continuity_continued` is **12.1 % worse** than the fixed expert in MAE,
  far above the 0.5 % threshold. On the solar series it was identical to the
  fixed expert.

`cumulative_continuity_continued` sits at 1.152 effective experts — just below
the threshold — and 0.50 % from the fixed expert, i.e. exactly at the boundary.
It is the one variant that behaves like the solar case, and it is the extreme
end of the retention family.

## Second result: reset had no observable effect at all

Continued and reset variants produced **identical predictions in all 691
evaluation rows** for every retention value. On the solar series the same
comparison produced 263 of 318 differing predictions for short continuity and
189 of 318 for long continuity.

The reason is visible in the weights. `long_continuity_continued` settles at
0.621 / 0.379 within the first evaluation month and moves by less than 0.002
across 321 months. Its retained state is already saturated before 2000, so
discarding it changes nothing that the update rule can still express.

This is a stronger statement than "reset did not help": under this mechanism
and this source, **the retained history was not doing any work that a reset
could remove.** The mechanism had stopped responding to new consequences long
before the reset point — not because retention was high, but because the
weight vector had reached a fixed point.

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
