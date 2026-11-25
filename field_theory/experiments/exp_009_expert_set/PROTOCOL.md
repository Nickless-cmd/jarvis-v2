# Experiment 009 protocol — is the threshold a property of the mechanism or of the experts?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed before the run.

## Where this question comes from

Investigation 8 constructed the expert loss gap directly and found that the
collapse threshold lands near `1 − r`, where `r` is the retention. It measured
that on two sources (SILSO sunspots and NOAA Mauna Loa CO₂), two assignment
modes (`fixed`, `roving`) and four retention conditions.

But it measured it on **one** expert set: `previous_month`, `trailing_12_mean`,
`cycle_lag_132`. That set is a modelling choice, not a property of the
mechanism. Investigation 8's own finding was narrow — it explained Investigation
6's missing transfer by the *stability* of the advantage rather than by the
source. If the threshold moves when the experts change, then the narrow finding
is narrower still: it would describe this expert set rather than the mechanism.

The question here is therefore: **does `1 − r` survive a different expert set,
and does it depend on how many experts there are?**

## What is varied

Five expert sets. All are computed from the same preserved series; no new
source is introduced.

| Set | Experts | What it tests |
|---|---|---|
| `original` | `previous_month`, `trailing_12_mean`, `cycle_lag_132` | Control — must reproduce Investigation 8 |
| `short_memory` | `trailing_3_mean`, `trailing_6_mean`, `seasonal_naive_12` | Experts that are all fast |
| `long_memory` | `trailing_24_mean`, `cycle_lag_66`, `cycle_lag_132` | Experts that are all slow |
| `two_experts` | `previous_month`, `trailing_12_mean` | Does the count matter? |
| `four_experts` | `previous_month`, `trailing_3_mean`, `trailing_12_mean`, `cycle_lag_132` | Does the count matter? |

Every set is computable at index ≥ `WARMUP_MONTHS = 132`, which is the first row
the mechanism evaluates. This is checked before any cell is run.

## The normalisation that makes the comparison meaningful

Investigation 8 used `THRESHOLD_LOW = 1.5` to mean "the mechanism is no longer
responsive". With three experts the maximum effective count is 3, so 1.5 is
exactly **50 % of the available experts**.

Comparing a 1.5 threshold across sets of two and four experts would compare
different things. This experiment therefore uses a **fraction**, not an absolute
count:

```
THRESHOLD_FRACTION = 0.5
threshold_effective_experts = THRESHOLD_FRACTION * len(experts)
```

For the original set this is `0.5 * 3 = 1.5`, identical to Investigation 8. The
control is what proves the normalisation did not change the question.

## Held fixed

- The mechanism: `_normalized_loss`, softmax with `LEARNING_RATE = 2.0`,
  retention applied to accumulated loss.
- The construction: `l_best` measured on the real experts at that month, the
  over/under sign kept from the real experts, and the remaining losses set by
  inverting `_normalized_loss`. This is Investigation 8's `fixed` and `roving`
  assignments, unchanged.
- `GAPS`, `RETENTIONS`, `WARMUP_MONTHS`, `EVALUATION_START`, both preserved
  source files and their digests.
- The two sources.

## What is measured

For each (source, expert set, assignment, retention) cell: the smallest
prescribed gap at which the mean effective expert count falls below
`THRESHOLD_FRACTION * N`. That is the **measured threshold**. The predicted
threshold is `1 − r`.

## Controls — read these before any verdict

1. **Reproduction.** The `original` set must reproduce Investigation 8's
   measured thresholds exactly for both sources, both assignments and all four
   retentions. If it does not, the local weight function has diverged from
   `_weights` and no other row may be read.
2. **Weight-function identity.** The local `_weights(losses, experts)` must
   return bit-identical values to `exp_005`'s `_weights` when called with the
   original set. Checked over a fixed grid of loss vectors, not assumed from
   reading the code.
3. **Calibration.** The gap measured back off the constructed predictions must
   equal the prescribed gap within `1e-9` for every set.
4. **Uniform control.** At gap 0 all experts in a set have identical losses, so
   the softmax is uniform and the effective count is exactly N. This is an
   analytic prediction, not a figure lifted from a run.

## Falsification conditions

1. **`1 − r` does not survive the expert set.** Fires if, in `fixed`
   assignment, the ratio `measured / (1 − r)` falls outside
   `[1 / THRESHOLD_FACTOR, THRESHOLD_FACTOR]` with `THRESHOLD_FACTOR = 3.0` for
   at least one non-original set on both sources.

2. **The count matters.** Fires if the measured threshold for `two_experts` or
   `four_experts` differs from the `original` threshold by more than
   `THRESHOLD_FACTOR` in the same cell (same source, assignment, retention).

3. **A control failed.** Any of controls 1–4 failing yields `instrument_fault`
   and no substantive claim may be made.

## What each outcome means

- **Neither condition fires:** the threshold is a property of the mechanism
  (softmax with a fixed learning rate against a normalised responsiveness
  floor), not of the experts. Investigation 8's finding generalises across
  expert sets and counts, and the honest scope widens to "any expert set on
  these two sources".
- **Condition 1 fires:** the threshold is set-specific. Investigation 8's
  `1 − r` would then describe one modelling choice, and its explanation of
  Investigation 6 would be narrower than stated.
- **Condition 2 fires:** the count of experts is part of the answer, and the
  fraction normalisation does not capture it.

## Scope limits, stated before the run

The construction still prescribes the gap. This experiment varies which real
predictions anchor `l_best` and the sign — it does not make a real adaptive
system appear. No claim is made about whether any physical process behaves this
way. Only `l_best(t)` and the error sign come from the data.
