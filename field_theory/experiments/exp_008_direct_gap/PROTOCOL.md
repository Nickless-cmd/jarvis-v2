# Experiment 008 protocol — the gap as input, not as output

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed before the run.

## Where this question comes from

Investigation 7 asked whether the collapse to one expert is governed by the
expert loss gap rather than by the source. It returned
`inconclusive_instrument_cannot_reach_question`, and its own closing section
named the fix:

> **Construct the gap directly.** Choose expert predictions whose pairwise
> losses differ by a prescribed amount, rather than blending real predictions
> and measuring whatever gap results. The gap then becomes the input, not an
> output.

Investigation 7's blend failed for a specific reason: blending each expert
toward the mean of the other two changed the predictions and the gap together,
so the gap was not monotone in the blend and the two sources' gap ranges never
overlapped (sunspots 0.11–2.10, CO₂ 0.003–0.055). Condition 2 — "do the sources
agree at a matched gap?" — could therefore never fire, which is exactly the
question Investigation 6 left open.

This experiment makes the gap an input. It then asks Investigation 6's
question directly.

## Question

**At a prescribed expert loss gap, held identical across both sources, does the
collapse to one expert depend on the source at all — and if not, where is the
threshold?**

Two sub-questions, both answerable only with a constructed gap:

1. Is there a gap threshold below which the mechanism stays responsive?
2. At matched gap and matched retention, do the two preserved sources agree?

## Instrument

The mechanism is imported, not retyped: `_weights`, `_normalized_loss`,
`EXPERTS`, `RETENTIONS`, `LEARNING_RATE`, `WARMUP_MONTHS`, `EVALUATION_START`
come from `experiment_005_learning`.

`_normalized_loss(p, y) = |p - y| / (1 + |y|)` is invertible. A prescribed
normalized loss `l` is produced exactly by

```
p = y + s * l * (1 + |y|),   s ∈ {+1, -1}
```

So for every month of a preserved series:

- `l_best(t)` is measured on the real data: the smallest normalized loss among
  the three real experts at that month. This anchors the series in the
  observation — the difficulty of the month is not invented.
- Three constructed experts are given normalized losses
  `l_best`, `l_best + gap/2`, `l_best + gap`.
- `s` is the sign of the corresponding real expert's error at that month, so
  the constructed predictions keep the real over/under direction. Where a real
  expert hit exactly, `s = +1`.

The gap is then `max(losses) - min(losses) = gap` by construction. It is
verified after the fact on the constructed predictions, not assumed.

This is a constructed instrument, exactly as the experts themselves are
constructed. It does not claim that a real process behaves this way. It asks how
the *mechanism* behaves as a function of a quantity that is now controlled.

## Analytic expectation, stated before measurement

With a constant gap `g` and retention `r`, the difference between two experts'
accumulated losses is

```
L_a(t) - L_b(t) = (delta_a - delta_b) * sum_{k=0..t} r^k
```

- At `r = 1` the sum grows linearly without bound, so **any** `g > 0` locks in
  eventually. There is no threshold above zero.
- At `r < 1` the sum converges to `1/(1-r)`, so the accumulated difference
  saturates at `(delta_a - delta_b)/(1-r)`.

With the softmax `w_i ∝ exp(-2 (L_i - L_min))` and `delta_2 - delta_1 = g/2`,
the nearest competitor's weight vanishes when `g/(1-r) >> 1`. The expected
threshold is therefore

```
gap_threshold ≈ (1 - r)
```

This is a prediction, not a result. It is stated here so it can fail.

## Grid

- gaps: `0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8`
- retentions: all four from `RETENTIONS`
  (`one_encounter` 0.0, `short_continuity` 0.9, `long_continuity` 0.99,
  `cumulative_continuity` 1.0)
- history: `continued` (the reset variant is not needed here — the gap, not the
  initial condition, is the variable)
- sources: both preserved series

## Measured quantities

Over the evaluation period only (from 2000-01):

- mean effective expert count `1 / sum(w²)`;
- mean weight change (L1);
- **measured** gap, recomputed from the constructed predictions — the
  instrument's own calibration;
- MAE against the outcome.

## Falsification, stated before measurement

The claim under test is: *"the collapse to one expert is governed by the
expert loss gap, not by the source."*

It is contradicted if any of the following holds:

1. **No threshold exists.** For at least two of the three retentions with
   `r < 1`, the effective expert count never falls from above 2.0 to below 1.5
   anywhere in the measured gap range. A flat curve means the gap does not
   govern the collapse.
2. **The threshold is not near `1 - r`.** The measured threshold — the smallest
   gap at which effective experts falls below 1.5 — differs from `1 - r` by more
   than a factor of 3 for at least two retentions. That would show the simple
   accumulation argument is wrong.
3. **The source matters at matched gap.** At identical retention and identical
   prescribed gap, the two sources give effective expert counts differing by
   more than 0.25. This is Investigation 6's open question and the reason this
   experiment exists.
4. **The control fails.** At `gap = 0` all three experts have identical losses,
   so the softmax is uniform and effective experts must be exactly 3.0 for every
   retention. This is an analytic prediction, not a figure from an earlier run.

Condition 4 is a validity check: if it fires the experiment reports an
instrument fault and no substantive result is read.

## What this experiment cannot show

- Nothing about field, identity, perspective, experience, or access.
- Nothing about whether the Sun or the atmosphere "learns".
- Nothing about a real process whose experts genuinely disagree by a graded
  amount — the predictions are constructed.
- No claim that a found threshold is universal. It is bounded by this expert
  set, this learning rate, this loss, and these two sources.
- Agreement between the two sources at matched gap does **not** show the source
  is irrelevant to the real experts; it shows that once the gap is controlled,
  the mechanism's behaviour is the same. The real sources differ in gap, and
  that difference is the thing being separated out.

## Evaluation rule

Development period is before 2000-01; evaluation is from 2000-01. `l_best(t)`
is measured on the real experts' losses at month `t`, so the anchor is the
observation itself and not a fitted quantity.

## Addendum — gap stability as a second axis

**Frozen:** 2026-11-25, before any measurement was computed. Added to the
protocol above, not substituted for it.

Investigation 7's Questions section asked:

> Does the collapse depend on the gap at all, or on the *stability* of the gap
> over time rather than its mean?

The protocol above fixes the gap but leaves open *which* expert is best. That
choice is a second independent variable, and it decides whether the
accumulation argument can apply at all:

- **`fixed` assignment.** Expert A is always given `l_best`, B always
  `l_best + gap/2`, C always `l_best + gap`. One expert is systematically best
  at every month. The accumulation difference grows monotonically, and the
  analytic threshold `gap ≈ (1 - r)` applies.
- **`roving` assignment.** The gap is the same size every month, but *which*
  expert is best follows the real series: the real expert with the smallest
  loss at month `t` is given `l_best`, the middle one `l_best + gap/2`, the
  worst `l_best + gap`. The advantage does not belong to anyone, so the
  accumulated difference should not grow.

Both are run on both sources. The prediction is **differential** and therefore
falsifiable in both directions:

- `fixed`: effective experts should fall as `gap` grows past `(1 - r)`, and at
  `r = 1` should fall for any `gap > 0`.
- `roving`: effective experts should stay near 3.0 across the whole gap range,
  because no expert accumulates a systematic advantage.

If `roving` collapses just as hard as `fixed`, the gap size governs the
collapse and stability does not matter. If `fixed` does not collapse, the
accumulation argument is wrong. If the two assignments agree, the stability
axis is inert and Investigation 7's question is answered in the negative.

Condition 3 (source agreement at matched gap) is evaluated within each
assignment mode separately, so a difference between modes cannot be mistaken
for a difference between sources.
