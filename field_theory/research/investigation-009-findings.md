# Investigation 9: the threshold holds — so completely that the experts do not reach it

**Status:** completed, **not falsified** — but the result is narrower and more
uncomfortable than the question assumed. Protocol frozen in
`experiments/exp_009_expert_set/PROTOCOL.md` and committed before any
measurement was computed. Run preserved in
`artifacts/exp_009_expert_set/run_20261125_173937/`.

## What was asked

Investigation 8 found the collapse threshold near `1 − r`, where `r` is the
retention. It measured that on one expert set (`previous_month`,
`trailing_12_mean`, `cycle_lag_132`), which is a modelling choice rather than a
property of the mechanism. If the threshold moves when the experts change, then
Investigation 8's explanation of Investigation 6 describes that set and not the
mechanism.

Five expert sets were run: the original, one of only fast experts, one of only
slow experts, one with two experts, one with four. Two sources, two assignment
modes and four retention conditions as before. The responsiveness floor was
expressed as a fraction (50 % of the available experts) so that sets of
different size are comparable; for the original set this is identical to
Investigation 8's absolute floor of 1.5.

## The answer, stated plainly

Neither falsification condition fired. The threshold does not move when the
expert set changes. It does not move when the number of experts changes from
three to four. It does not move between the two sources.

**It does not move at all.** Measured on a grid with a factor of 1.6 between
points — fine enough to resolve differences that the protocol's factor-of-two
grid could not — all four sets of three or more experts give the *same*
threshold, to the grid point, on both sources:

| Retention | Expected | Measured (every set, every source) |
|---:|---:|---|
| 0.9 | 0.100 | 0.209715 |
| 0.99 | 0.010 | 0.020000 |

That is not robustness. That is the threshold being **analytic**, and the data
never entering it.

## Why: the threshold is a property of the softmax, not of the experts

With retention `r` the accumulated loss difference between the best and worst
expert converges to `gap / (1 − r)`. The softmax has a fixed learning rate
(`LEARNING_RATE = 2.0`), so the whole mechanism depends on the single quantity

```
x = LEARNING_RATE · gap / (1 − r)
```

The effective expert count is a function of `x` alone. Crossing the 50 %
responsiveness floor therefore happens at a fixed `x`, which means the threshold
in gap space is

```
gap_threshold = (x_threshold / LEARNING_RATE) · (1 − r)
```

For three experts `x_threshold ≈ 1.57`, giving `gap ≈ 0.785 · (1 − r)`. The
measured ratios sit near 2 because the grid is coarse relative to the crossing,
not because the relation is different.

**The expert set cannot move this.** The set only changes `l_best(t)` and the
error sign; neither enters `x`. That is why short memory, long memory and four
experts all land on the same grid point.

## What this does to Investigation 8

Investigation 8 reported that at a matched gap the two sources collapse
identically in `fixed` assignment, and read that as evidence the source does not
matter. In `fixed` assignment the expert order is the set's tuple order — it is
**constant over time by construction**. So the gap is constructed, the order is
constant, and the threshold follows analytically. The agreement between sources
in that mode is a mathematical necessity, not an empirical finding.

The part of Investigation 8 that survives as a data result is `roving`, where
the expert order is sorted by each month's real loss. There the threshold is
genuinely data-dependent, and it varies:

| Set | Source | Retention | Threshold |
|---|---|---:|---:|
| `original` | co2 | 0.99 | 0.05 |
| `long_memory` | co2 | 0.99 | 0.02 |
| `short_memory` | co2 | 0.99 | 0.10 |
| `four_experts` | sunspots | 0.9 | 0.80 |
| `long_memory` | co2 | 0.9 | 0.20 |

A factor of eight across the cells. That is where the experts and the source
actually reach the answer — and it is the opposite of the flat result that
`fixed` gives.

## The two-expert set cannot be measured with this floor

`two_experts` never crosses its floor. With two experts the minimum effective
count is 1.0 (one expert alone), and 50 % of two is also 1.0. The condition is
`< 1.0`, which is unreachable — the series approaches 1.0 asymptotically
(`1.00000023` at gap 0.8) and never passes it.

This is the same failure mode as Investigation 7's unreachable threshold: a
threshold placed exactly at the boundary of what the quantity can attain. It is
not a finding about the mechanism, and the `not_falsified` verdict must not be
read as evidence that two experts behave like three. The honest statement is
that this experiment could not ask the question for two experts.

## A measurement error I made and caught

The first analytic check I ran returned exactly `0.2000` for every retention and
every gap. The number was suspiciously constant, which is what made me look: the
effective-count helper iterated over the dict's **keys** (`0, 1, 2`) instead of
its values, so it computed `1 / (0² + 1² + 2²) = 0.2` regardless of input. Had
the wrong number varied, it would have looked like a result. A quantity that
does not move when its input moves by a factor of 400 is not a measurement.

## Scope

The construction still prescribes the gap. This experiment varies which real
predictions anchor `l_best` and the sign; it does not make a real adaptive
system appear. No claim is made about whether any physical process behaves this
way.

What it does establish is narrower and useful: the `1 − r` threshold is a
property of a softmax with a fixed learning rate against a normalised
responsiveness floor. Any conclusion drawn from it in `fixed` assignment is a
statement about the arithmetic, not about the source or the experts. Only
`roving` puts the data back into the answer.
