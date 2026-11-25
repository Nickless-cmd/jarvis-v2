# Experiment 014 protocol — why weighting loses to the best single expert

**Frozen:** 2026-11-25, before the module that computes anything exists. This file
is committed **on its own**, so `git log` can prove the ordering.

## Provenance, declared

Two exploratory probes ran before this protocol was written:
`/tmp/probe_014_weight_penalty.py` and `/tmp/probe_014b.py`. They are not
preregistered. The numbers below are therefore *reported*, not *predicted*, and
the protocol exists to freeze how they will be re-measured and what would
falsify the interpretation — not to claim foresight that was not there.

This is the same deviation as exp_010 and exp_012. It is recorded rather than
dressed up.

## The question

Investigation 12 and 13 reported that the ensemble's forecast error is a median
**1.43–1.59** times the best single expert's. That number has been quoted as
"weighting loses ~59 % to the best expert". Three things are wrong or unstated
about that sentence, and this experiment separates them.

### 1. The ratio depends on the aggregate, and nobody said so

Four defensible aggregations of the same quantity give wildly different answers:

| aggregate | what it weights |
|---|---|
| median over cells of (mean error / mean oracle) | each cell equally |
| median over cells of a 13-point gap grid | each cell equally, wider grid |
| median over months | each month equally |
| mean over months | each month equally, tails dominate |

The claim "loses 59 %" is a **cell-median on one grid**. It is not a property of
the mechanism. Any sentence quoting one of these numbers without naming the
aggregate is measuring the aggregate, not the mechanism.

**Registered prediction:** the month-level median is lower than the cell-level
median, because a cell with many months and a high ratio dominates its own
cell-median but counts once per month at month level.

### 2. The loss is monotone in how concentrated the weight is

If the loss were "mixing", it would appear uniformly. If it is allocation, it
should track `top_weight`: a weight that is nearly all on one expert should cost
almost nothing.

**Registered prediction:** median `err/oracle` falls monotonically across
`top_weight` buckets, and approaches 1.00 when `top_weight > 0.99`.

### 3. The mechanism: the residual mass amplifies the top expert's error

Split the weighted sum into the top expert's term and the rest:

    sum_e w_e a_e  =  w_top a_top  +  sum_{e != top} w_e a_e

When the rest points the **same way** as the top term, the residual mass adds to
the error. When it points **opposite**, it cancels.

**Registered prediction:** the loss is concentrated in the same-sign months, and
the opposite-sign months have ratio ≈ 1.00.

### 4. Warm-up is not the explanation

The weight starts uniform and concentrates over time, so the loss could be a
transient that averaging over the window hides.

**Registered prediction:** the ratio is flat across the window; the loss is a
steady-state property, not a warm-up.

### 5. A sharpened weight beats both ends — on the mean

`w^alpha` normalised interpolates from the learned weight (`alpha = 1`) to a pure
argmax (`alpha -> infinity`). If the loss is allocation, some intermediate value
should beat both.

**Registered prediction:** mean error has an interior minimum, while the median
falls monotonically toward 1.00. If the mean is monotone, the prediction fails.

## Falsification

The experiment fails — and the allocation explanation with it — if:

- `1_aggregate_matters` — the month-level median is **not** lower than the
  cell-level median;
- `2_monotone_in_concentration` — the median ratio is **not** monotone
  non-increasing in `top_weight`;
- `3_residual_amplifies` — same-sign months do **not** carry the loss;
- `4_not_warm_up` — the ratio is not flat across the window;
- `5_interior_optimum` — the mean error has no interior minimum in `alpha`.

All five are success conditions written in positive form. Investigation 12's
verdict function was wrong exactly because one condition was written as a fault
among four successes, so `all()` could never be true. The same mistake is not
repeated here.

## Controls that can be lost silently

1. **The identity.** `err == |sum w a|`, recomposed from the stored weight vector
   and error directions. Residual must be 0.0. A tautological check
   (`err == |err|`) would be zero by construction and is not used.
2. **The error must be read from the real predictions.** If `a` is taken from
   the constructed predictions (`outcome + sign*(l_best+delta)*scale`), the
   outcome cancels out and the error measures the imposed gap instead. This was
   Investigation 12's finding and must not be undone here.
3. **The oracle is per month and uses hindsight.** No sentence may imply that
   the gap to it is closable operationally.
4. **`alpha -> infinity` must reproduce selection.** If the sharpened weight at
   large `alpha` does not converge to `err_selected`, the interpolation is wrong
   and the interior minimum is an artefact.
