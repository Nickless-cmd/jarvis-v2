# Experiment 010 protocol — is the roving threshold predicted by the rank drift?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed before the run.

## Where this question comes from

Investigation 8 built an instrument that prescribes the expert loss gap directly
(by inverting the normalized loss), and measured the collapse threshold. In
`fixed` assignment — the same expert best every month — the threshold followed
`gap ≈ x_crit · (1 − r) / LR` on both sources, identically.

Investigation 9 varied the expert set across five sets and found the `fixed`
threshold did not move at all. That result was correct and it was also, in
hindsight, a tautology: in `fixed` the deltas are pinned to the tuple order, so
the mean rank positions are exactly `0, 1/(N−1), …, 1` regardless of which
experts are in the set. There was nothing for the data to move.

But Investigation 9 also measured `roving` — where the delta is assigned by the
**real** ranking that month — and there the threshold moved a great deal:

| source | retention | measured roving threshold (original set) |
|---|---|---|
| sunspots | 0.99 | 0.1 |
| CO₂ | 0.99 | 0.05 |
| sunspots | 0.9 | > 0.8 (not crossed) |
| CO₂ | 0.9 | 0.4 |

and across expert sets it ranged from 0.01 to 0.8. **That** is the data
dependence. Investigation 9's headline — "the threshold does not depend on the
experts" — is true of `fixed` only, and the finding file says so; the open
question is what governs the roving threshold.

## The question

In `roving`, an expert accumulates advantage only while it keeps being ranked
best. So the natural candidate is the **spread of the mean rank positions**: if
one expert is best nearly every month, the accumulated advantage grows as it
does in `fixed`; if the ranking churns uniformly, every expert's mean position is
the same and no systematic advantage accrues.

Derivation, with `N` experts, rank index `i ∈ {0..N−1}`, delta `= gap · i/(N−1)`,
retention `r`, learning rate `LR`:

- mean position of expert `e` over the evaluation window: `m_e`
- steady-state accumulated loss: `S_e = gap · m_e / ((N−1)(1−r))`
- softmax argument spread: `u = LR · gap · (m_max − m_min) / ((N−1)(1−r))`
- the mechanism collapses when `u` reaches `u_crit(N)`, a pure function of `N`
  and the floor fraction, obtained by solving `1/Σw² = 0.5·N`

Therefore

```
gap_threshold = u_crit(N) · (N−1) · (1−r) / (LR · (m_max − m_min))
```

and the invariant

```
Q ≡ gap_threshold · (m_max − m_min) · LR / ((N−1)(1−r))   must equal  u_crit(N)
```

`Q` must be the same in every cell with the same `N`, whichever source, whichever
expert set, whichever retention. In `fixed`, `m_max − m_min = 1` by construction,
which is why Investigation 9 measured one number for all five sets.

## Two parts

**Part A — synthetic rank sequences (the strong test).** The formula is validated
where the rank drift is *controlled*, not observed. A designated expert is ranked
best with probability `p ∈ {1/3, 0.4, 0.5, 0.6, 0.8, 1.0}`; otherwise the order is
a uniform random permutation. `p = 1/3` is the uniform control (no drift). The
sequence is generated with a fixed seed so the run is reproducible. `m_e` is
measured from the generated sequence, not assumed. If the formula holds, `Q` is
constant across `p` and the threshold scales as `1/(m_max − m_min)`.

**Part B — the preserved sources.** `m_e` is measured per (source, expert set)
from the real expert losses over the evaluation window, the threshold is measured
on a fine gap grid, and `Q` is compared across all cells.

## Fine grid

Investigation 9 used gaps with a factor of 2 between points. That resolution
cannot distinguish a predicted 0.0157 from a measured 0.02 — both sit inside the
same bracket. This experiment uses a geometric grid with ratio **1.15** from
0.0005 to 1.0. A threshold is therefore known to within a factor of ~1.07
(geometric midpoint), and the invariant is tested at that resolution.

## Falsification conditions

1. **`1_invariant_not_constant`** — fires if, among cells with the same `N` and
   `r < 1`, the measured `Q` spans more than a factor of **2.0**. (The same
   `THRESHOLD_FACTOR` scale used in Investigations 8 and 9.) If `Q` is not
   constant, the mean-position formula does not govern the threshold and the
   explanation is wrong.
2. **`2_synthetic_scaling_absent`** — fires if, in Part A, the measured threshold
   does not fall monotonically as the drift strengthens. Over the ordered
   probabilities `p = (1/3, 0.4, 0.5, 0.6, 0.8, 1.0)` the threshold must decrease,
   with an unreachable cell counting as the largest value. `p = 1/3` is the
   uniform control and must be unreachable; `p = 1.0` is `fixed` and must
   reproduce the fixed threshold.

   *Clarified before the run and before any measurement was computed.* The first
   wording of this condition named `p = 0.5` as "larger still" than `p = 0.4`,
   which contradicts the derivation above: `p = 0.5` is closer to uniform than
   `p = 0.4`, so its drift is weaker and its threshold must be **larger**. The
   condition is implemented in the direction the derivation implies. This note
   records the change rather than hiding it — the same discipline the earlier
   investigations were held to.
3. **`3_uniform_is_unreachable`** — if `m_max − m_min` falls below
   `UNIFORM_TOLERANCE`, the cell must be reported as **unreachable**, not as
   "never collapses" and not as a threshold. A cell where the drift is zero
   cannot be crossed by drift at any gap, and calling that a measurement would be
   the same error Investigation 7 made with an unreachable threshold.
4. **`4_control_failed`** — `fixed` cells must reproduce Investigation 9's
   measured thresholds (0.2 at r=0.9, 0.02 at r=0.99, for every expert set and
   both sources). The fine grid must land inside the same bracket.
5. **`5_calibration_failed`** — the prescribed gap must be reproduced by the
   constructed predictions to within 1e-9 at every cell.

## The `r = 1.0` regime is declared out of scope

At `r = 1` the accumulated loss is a cumulative sum with no decay, so
`(1 − r) = 0` and the invariant diverges. There is no steady state: any drift,
however small, eventually dominates, which is why Investigation 9 measured 0.002
there — smaller than at `r = 0.99`. Those cells are reported but excluded from
condition 1. Treating them as a scaling law would be fitting a formula outside
its domain.

## Evidence boundary

The rank positions are measured on the real experts. The losses are constructed
by inversion, so the "gap" is a quantity this instrument prescribes, not one it
observes in nature. Nothing here establishes that any real process ranks its
experts this way. What can be established is narrower and still worth having:
whether the roving threshold is a free parameter or a function of the rank drift.

## Amendment — after the first run, before any verdict

The first run (`artifacts/exp_010_rank_drift/run_20261125_v1/`) returned
`instrument_fault`. The controls stopped it before any threshold carried a
verdict, which is what they are for. It revealed three defects — two in this
protocol, one in the implementation. All three are recorded here rather than
quietly corrected.

**(a) The threshold formula carried a spurious `(N−1)` factor.** The delta
assigned to rank `i` is `gap · i/(N−1)`, so `i/(N−1) ∈ [0, 1]` and the delta
*range* is `gap` for every `N`. The accumulated argument spread is therefore
`u = LR · gap/(1−r)` and

```
gap_threshold = u_crit(N) · (1 − r) / (LR · (m_max − m_min))
```

with no `(N−1)`. The error was visible in the first run's `fixed` cells, where
the threshold sat at exactly half the predicted value on every source and every
set. Corrected: the same cells now sit at the predicted value within the grid
factor.

**(b) Part A's generator did not implement `fixed` at its upper end.** It
shuffled the non-designated experts, so `p = 1.0` produced a mean-position
spread of 0.78 rather than 1.0 and was therefore *not* the fixed configuration.
Part A is rebuilt on a cleaner parameter: `q = P(the tuple order)` per month.
`q = 1` is exactly `fixed`, `q = 0` is exactly a uniform permutation. Both ends
are now anchors instead of approximations.

**(c) The reproduction control applied Investigation 8's expected thresholds to
all five expert sets.** Those numbers are defined for the three-expert set.
Restricted to `N = 3`. The two-expert set is separately structural: its floor is
`0.5 · 2 = 1.0`, which is the minimum attainable effective count, so it can only
be approached and never crossed. The formula now returns "unreachable" for that
case instead of a finite number produced by bisection saturating at float
precision.

**What is not changed: the falsification conditions.** In particular, condition
2's claim that a uniform ranking must be unreachable stays as written, even
though the first run measured a crossing at `r = 0.99`. That is a result, not a
defect, and it will be allowed to fire.
