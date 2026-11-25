# Experiment 007 protocol — is lock-in a function of expert disagreement?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed before the run.

## Where this question comes from

Investigation 5 (sunspots) found that long and cumulative retention collapsed
all weight onto one expert: continuity became lock-in. Investigation 6 applied
the identical mechanism to NOAA Mauna Loa CO₂ and the relation did **not**
transfer — `long_continuity_continued` kept 1.886 effective experts there
against 1.000 on sunspots.

Investigation 6's own Limitation names the untested explanation:

> The CO₂ series has a strong monotone trend, which makes `previous_month`
> near-optimal by construction — a plausible reason the adaptive mechanisms
> cannot beat it. That is an interpretation, not a measurement, and it was not
> tested.

And its Questions section asks the discriminating version directly:

> Is there a source where the two experts are *equally* good, and does the
> mechanism then stay responsive indefinitely?

## Question

**Does the collapse to one expert depend on how far apart the experts' losses
are, rather than on which source they are measured on?**

If lock-in is a property of the retention rule alone, it should appear at every
degree of expert disagreement. If it is an interaction, there should be a
measurable threshold: below some loss gap the mechanism stays responsive
indefinitely, above it the softmax goes one-hot.

## Why this is not a new source

No new observational series is introduced. The experiment **grades the
disagreement** on the two series already preserved, by mixing each expert's
prediction toward the others with a fixed blend weight. This is a constructed
instrument, exactly as the experts themselves are constructed: it does not
claim that a real process behaves this way. It asks how the *mechanism* behaves
as a function of a quantity that can be measured on the preserved data.

The blend is applied identically to both sources, and the mechanism constants
are imported from `experiment_005_learning` — not retyped — so the runs cannot
silently diverge.

## Instrument

For each preserved source, and for each blend weight `b` in
`{0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}`:

- each expert's prediction is replaced by
  `(1 - b) * own_prediction + b * mean(other_two_predictions)`.

At `b = 0` the experts are unchanged, so the run must reproduce the preserved
Investigation 5 and 6 results exactly. That is the instrument's control: if
`b = 0` does not reproduce the earlier numbers, the instrument is broken and no
other row may be read.

At `b = 1` all three experts are identical, so every loss is equal, the softmax
is uniform, and no lock-in is possible by construction. That is the instrument's
upper bound, not a finding.

## Measured quantities

For each `(source, b, retention, history)` cell, over the evaluation period
only:

- mean effective expert count;
- mean weight change (L1);
- MAE, and MAE gap fraction against the fixed selected expert;
- **expert loss gap**: the mean absolute difference between the best and worst
  expert's normalized loss, measured on the same blended predictions. This is
  the independent variable.

## Falsification, stated before measurement

The claim under test is: *"the collapse to one expert is governed by the expert
loss gap, not by the source."*

It is contradicted if any of the following holds:

1. **No threshold exists.** For `long_continuity_continued`, the effective
   expert count does not increase monotonically (within tolerance 0.05) as the
   blend weight increases on **both** sources. If the curve is flat or
   non-monotone, the loss gap does not govern the collapse.
2. **The sources disagree at matched gap.** At a matched expert loss gap
   (within 10 % relative), the two sources give effective expert counts that
   differ by more than 0.25. That would show the source matters beyond the gap.
3. **The control fails.** At `b = 0` the run does not reproduce the preserved
   Investigation 5 and 6 evaluation figures for `long_continuity_continued`
   (sunspots: 1.000 effective experts, MAE 14.8513; CO₂: 1.886 effective
   experts, MAE 1.3024) to within 1e-6.

Condition 3 is a validity check, not a finding: if it fires, the experiment
reports an instrument fault and no substantive result.

## What this experiment cannot show

- Nothing about field, identity, perspective, experience, or access.
- Nothing about whether the Sun or the atmosphere "learns".
- Nothing about a real process whose experts genuinely disagree by a graded
  amount — the blend is constructed.
- No claim that the threshold, if found, is universal. It is bounded by this
  expert set, this learning rate, this loss, and these two sources.
- A monotone relation between gap and collapse is not proof of causation; the
  blend changes the predictions and the gap together.

## Evaluation rule

Development period is before 2000-01; evaluation is from 2000-01. The fixed
expert is selected by development MAE on the unblended predictions and held
fixed across blend weights, so the comparison baseline does not move with the
instrument.
