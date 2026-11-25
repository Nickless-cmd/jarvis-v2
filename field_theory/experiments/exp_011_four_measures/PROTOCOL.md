# Experiment 011 protocol — four measures instead of one threshold statistic

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering. Investigation 10 could not make that
claim and had to record why; this one can, and does.

## Where this question comes from

Investigation 10 established that `mean_effective_experts < 0.5·N` measures an
**equilibrium** in `fixed` assignment and an **occupancy** in `roving`, and that
the two cannot be compared. It closed with the statistic itself as the open
problem: one number cannot say whether a system sits below the floor constantly
or oscillates through it.

Four properties are proposed as replacements:

| property | what it measures |
|---|---|
| **occupancy** | the fraction of evaluation months below the floor |
| **persistence** | how long each collapse lasts |
| **recovery** | how long diversity lasts once it returns |
| **identity stability** | whether it is the *same* expert that dominates |

## The definitions, precisely

For the evaluation window `t = 1..T`, with `E_t` the effective expert count at
month `t` and floor `c = 0.5·N`:

- **Occupancy** `O = |{t : E_t < c}| / T`. In `[0, 1]`.
- A **collapse run** is a maximal contiguous block with `E_t < c`; `K` is the
  number of such blocks. **Persistence** `P = (Σ run lengths)/K` — the mean
  collapse length in months. Undefined when `K = 0`.
- A **healthy run** is a maximal contiguous block with `E_t ≥ c`; `K'` is the
  number of such blocks. **Recovery** `R = (Σ healthy run lengths)/K'` — the
  mean time diversity lasts once it returns. Undefined when `K' = 0`.
- **Identity stability** `I = |{t = 2..T : d_t = d_{t−1}}| / (T−1)`, where
  `d_t = argmax_e S_t(e)` is the expert with the largest accumulated loss at
  month `t`. Ties are broken by the tuple order so the measure is deterministic.
  In `[0, 1]`. Also reported: `D` = the number of distinct dominant experts.

`I` is deliberately **not** a concentration measure. `O` already measures how
often the system is collapsed; `I` measures whether the *identity* of the
dominant expert survives. A system can be collapsed every month (`O = 1`) with
one fixed dominant expert (`I = 1`) or with the dominant expert changing
constantly (`I ≈ 1/N`). That is the distinction Investigation 10 could not make.

## The prediction this protocol is built to break

The four measures are proposed as independent. **They are not — the first three
are algebraically dependent, and the protocol states this before measuring.**

By construction `O·T = K·P` and `(1−O)·T = K'·R`, so

```
P/(P+R) = O·K' / (O·K' + (1−O)·K)
```

and therefore, whenever `K = K'`,

```
O = P/(P+R)      exactly
```

Because collapse runs and healthy runs alternate, `|K − K'| ≤ 1` always. So
occupancy, persistence and recovery span **two** degrees of freedom, not three:
any two determine the third. Reporting all three as separate findings would be
presenting one measurement three times.

This is written down as a **prediction, not a discovery**. If the residual
`|O − P/(P+R)|` is not zero on cells with `K = K'`, my algebra is wrong and that
is the more interesting result.

The consequence is the real question: **if three of the four measures collapse
to two degrees of freedom, is the fourth an independent axis at all?** That is
what conditions 4 and 5 test.

## Two parts

**Part A — synthetic rank sequences (independent of both sources).** Rank orders
drawn so the tuple order occurs with probability `q ∈ {0.0, 0.2, 0.4, 0.6, 0.8,
1.0}`, from `_synthetic_orders` in Investigation 10 with the same seed. `q = 1`
is exactly `fixed`, `q = 0` exactly a uniform permutation. Retention
`r ∈ {0.9, 0.99}`, gap `g ∈ {0.05, 0.2, 0.8}`. 400 months, 4 experts.

**Part B — the preserved sources.** Sunspots and CO₂, all five expert sets from
Investigation 9, both assignments, `r ∈ {0.9, 0.99}`, `g ∈ {0.05, 0.2, 0.8}`.
The losses and rank orders come from `_prepare`/`_orders` in Investigation 10
unchanged — this experiment adds a measurement to the existing instrument, it
does not build a second one.

## Controls

1. **`C1_occupancy_matches_investigation_10`** — occupancy measured here must
   equal `duty_cycle` from `_evaluate` in Investigation 10 to within `1e-12` on
   every shared cell. If it does not, the new instrument is not measuring the
   same mechanism, and no comparison across the two is meaningful.
2. **`C2_series_reconstructs_aggregate`** — the per-month series must reproduce
   the aggregate `mean_effective_experts` and `min_effective_experts` from
   `_evaluate` to within `1e-9`. The series is the new object; it must agree with
   the number it replaces.
3. **`C3_runs_are_maximal`** — every run must be bounded by a transition, and
   `K + K'` must differ by at most 1. A run-counting bug shows up here before it
   reaches a verdict.

## Falsification conditions

1. **`1_identity_does_not_hold`** — fires if, on any cell with `K = K' ≥ 1`, the
   residual `|O − P/(P+R)|` exceeds `1e-12`. The algebra above would then be
   wrong, and the three measures would be independent after all.
2. **`2_occupancy_disagrees_with_investigation_10`** — fires if control C1 fails
   on any cell. Two instruments measuring the same thing must agree exactly, not
   approximately.
3. **`3_identity_is_a_function_of_occupancy`** — fires if `I` is determined by
   `O` across the measured cells: specifically, if no pair of cells exists with
   `|O_a − O_b| ≤ 0.05` and `|I_a − I_b| ≥ 0.30`. If no such pair exists, the
   fourth measure adds no axis in practice and the honest report is that four
   measures were proposed and three degrees of freedom were found.
4. **`4_fixed_is_identity_stable`** — fires if `fixed` assignment yields
   `I < 1.0` on any cell. In `fixed` the rank order never changes, so if the
   dominant expert still changes hands, the dominance is driven by the realised
   losses and not by the rank order — a result, not a defect, and one that
   weakens the reading of `I` as "continuity of the mechanism".
5. **`5_no_collapse_is_unmeasurable`** — fires if a cell with `O = 0` is reported
   with a `P` value, or a cell with `O = 1` is reported with an `R` value. An
   undefined measure must be reported as undefined, never as zero. Investigation
   10's `mean_over_min = 1.000` conflating "always above" with "always below" is
   the precedent this condition exists to prevent.

## The evidence boundary

The rank orders are observed on real experts; the losses are constructed by
inversion, so the gap is a quantity the instrument **prescribes**. Nothing here
establishes that any real process ranks its experts this way. What can be
established is narrower: whether four proposed measures carry more information
than the one they replace, and which of them are algebraically forced to agree.

## Out of scope

`r = 1.0` — no steady state, the accumulated loss is an undecayed sum. Reported
where it exists but excluded from every condition, as in Investigation 10.

Two-expert sets — floor `0.5·2 = 1.0` is the minimum attainable effective count,
so collapse is approached but never reached and `O` is identically zero. Such a
cell is reported as unreachable, not as a measurement of zero occupancy.

## Amendment — after the first run, before any report

The first run (`artifacts/exp_011_four_measures/run_20261125_v1/`) completed with
all three controls passing. Two things came out of it, and both are recorded here
rather than quietly fixed.

**(a) Condition 1 was too narrow to test the claim it was written to test.** The
identity `O = P/(P+R)` was asserted only on cells where `K = K'`. That held
exactly — the worst residual over the 7 qualifying cells was 1.1e-16 — but 125 of
132 cells were excluded, because a finite window almost never starts and ends in
the same state. The correct test is the general form derived above,
`P/(P+R) = O·K'/(O·K' + (1−O)·K)`, which applies to every cell. The narrow form
is reported as measured; the general form is added as a diagnostic. The condition
itself is **not** loosened — it fired on nothing because the algebra is right,
and that stands.

**(b) The fourth measure was itself a grab-bag, which is the error this
investigation exists to name.** Condition 3 fired: no pair of cells shared an
occupancy within 0.05 while differing in `identity_stability` by 0.30. But the
reason is a defect in the definition, not an absence of information:

- `identity_stability = 1 − switches/(T−1)` divides by the window length, so the
  same underlying churn produces a smaller number as `T` grows. On a 318-month
  window, ~51 switches give 0.839 — which reads as "stable" although the
  dominant expert changed hands 51 times.
- It also says nothing about *how* the dominance is distributed. One expert
  holding 72.6% of the window and three experts sharing it evenly can produce the
  same switch count.

Two supplementary measures are therefore reported alongside it, not in place of
it: `dominance_share` (the fraction of the window held by the single most
dominant expert) and `switches_per_month` (the transition rate). Condition 6
applies condition 3's pair test to `dominance_share`.

**What is not changed: conditions 1–5.** Condition 3 fired on the frozen
definition and the results file reports it as fired. Condition 6 is an addition
that asks whether the *reason* for that firing was the definition.

The precedent is Investigation 10's, one step further on: there, "duty cycle"
named two different quantities. Here, "identity stability" names at least three —
transition frequency, dominance concentration, and dominance diversity — and only
the first was written into the frozen protocol.
