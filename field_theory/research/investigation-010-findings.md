# Investigation 10: the roving threshold is not a function of the rank drift alone

**Status:** completed, **falsified** — and the falsification identifies what the
threshold statistic actually measures in each mode. Protocol frozen in
`experiments/exp_010_rank_drift/PROTOCOL.md`, including the amendment written
after the first (faulted) run. Run preserved in
`artifacts/exp_010_rank_drift/run_20261125_v2/`.

## What was asked

Investigation 9 varied the expert set across five sets and found the `fixed`
threshold did not move. That was correct and it was also a tautology: in `fixed`
the deltas are pinned to the tuple order, so the mean rank positions are exactly
`0, 1/(N−1), …, 1` and there is nothing for the data to move.

The data dependence lives in `roving`, where the delta is assigned by the real
ranking each month — there the threshold ranged from 0.01 to 0.8. This
investigation asked whether that range is governed by the **spread of the mean
rank positions** `m_max − m_min`:

```
gap_threshold = u_crit(N) · (1 − r) / (LR · (m_max − m_min))
```

with `u_crit(N)` the softmax argument spread at which the effective expert count
falls below half of `N` — a pure function of `N`, solved by bisection.

## The first run was stopped by its own controls

`run_20261125_v1` returned `instrument_fault`. Three defects, all mine, all
recorded in the protocol amendment:

- the formula carried a spurious `(N−1)`. The delta for rank `i` is
  `gap·i/(N−1)`, so `i/(N−1) ∈ [0,1]` and the delta *range* is `gap` for every
  `N`. The error was visible because the `fixed` cells sat at exactly **half**
  the predicted threshold on every source and every set.
- the reproduction control applied Investigation 8's expected thresholds to all
  five sets. Those numbers are defined for the three-expert set; the two-expert
  set has a different floor.
- Part A's generator shuffled the non-designated experts, so its upper end
  produced a spread of 0.78 rather than 1.0 and was never actually `fixed`.

The controls that caught the third one were the ones that mattered most: the
prepared/ordered evaluation reproduces Investigation 9's **bit-identically**
(difference 0.0), and the prescribed gap is reproduced to 2·10⁻¹⁵.

## Part B — the preserved sources

The formula is **exact where the drift is deterministic** and does not hold where
it churns. Post-hoc split by assignment, reported as a diagnostic and not as a
condition:

| assignment | N | cells | Q range | ratio | u_crit |
|---|---|---:|---|---:|---:|
| fixed | 3 | 12 | 3.29 – 3.54 | **1.08** | 3.13 |
| fixed | 4 | 4 | 3.29 – 3.54 | **1.08** | 3.18 |
| roving | 3 | 12 | 3.29 – 22.6 | **6.88** | 3.13 |
| roving | 4 | 4 | 2.73 – 4.92 | 1.80 | 3.18 |

`Q` is the measured threshold rescaled by the drift; it must equal `u_crit`. In
`fixed` it does, to within the grid factor of 1.15, on **every** cell. In
`roving` it does not: up to seven times too large.

## Part A — controlled drift

`q` is the probability that a month's rank order is the tuple order. `q = 1` is
exactly `fixed`, `q = 0` exactly a uniform permutation.

| q | spread | measured (r=0.9) | predicted | measured (r=0.99) | predicted |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.243 | unreachable | 0.644 | **0.3098** | 0.211 |
| 0.2 | 0.244 | 0.9477 | 0.642 | 0.0881 | 0.072 |
| 0.4 | 0.257 | 0.4097 | 0.611 | 0.0381 | 0.033 |
| 0.6 | 0.668 | 0.2694 | 0.235 | 0.0250 | 0.026 |
| 0.8 | 0.741 | 0.2037 | 0.211 | 0.0218 | 0.019 |
| 1.0 | 1.000 | 0.1771 | 0.1567 | 0.0165 | 0.0157 |

The scaling half of condition 2 **held**: the threshold falls monotonically as
the drift strengthens, on both retentions, and `q = 1` reproduces the `fixed`
threshold.

The unreachability half **failed**, and that failure is the more interesting
result: at `r = 0.99` a *uniform* ranking collapses at gap 0.31. A uniform
ranking is not driftless in a finite window — over the effective window
`1/(1−r) = 100` months, sampling alone produces a mean-position spread of 0.074,
which is a real drift. "No drift in expectation" is not "no drift".

## What the threshold actually measures

The decisive measurement is not the range of the accumulated losses — that
hypothesis was tested and rejected (the range at the crossing runs from 1.03 to
6.65 times `u_crit`, so it is not constant either). It is the **duty cycle**: the
fraction of evaluation months whose effective expert count lies below the floor.

| assignment | cells | duty cycle | mean eff | min eff |
|---|---:|---|---|---|
| fixed | 16 | **1.00 – 1.00** | 1.396 – 1.963 | equal to mean |
| roving | 16 | **0.52 – 1.00** | 1.46 – 2.00 | 1.007 – 1.84 |

In `fixed` every single evaluation month is below the floor, and the mean equals
the minimum: a **steady state**. In `roving` the average sits just below the
floor while individual months fall far lower: an **intermittent** state whose
mean crosses the floor by duty cycle rather than by equilibrium.

So the two "thresholds" are not the same quantity. `mean_effective_experts <
0.5·N` measures a settled argument spread in one mode and the duty cycle of a
fluctuating one in the other. That is why no single formula fits both, and it is
a criticism of the statistic, not only of the formula — the statistic is
inherited from Investigations 8 and 9, which compared across modes without
asking whether it meant the same thing in each.

This is measured post-hoc, in `experiments/exp_010_rank_drift/posthoc_range.py`,
and it carries no verdict. It is a hypothesis for the next investigation, not a
result of this one.

## What this does to Investigations 8 and 9

- **Investigation 8's `fixed` law stands.** `gap ≈ u_crit(1−r)/LR` is confirmed
  to within the grid factor, now on five expert sets and two sources.
- **Investigation 9's headline is narrowed further.** "The threshold does not
  depend on the experts" is true of `fixed` only, and in `fixed` it could not
  have been otherwise. Its `roving` numbers (0.01 to 0.8) are duty cycles, not
  thresholds, and should not be read as a scaling law.
- **Investigation 6's missing transfer is still explained**, but the explanation
  is now narrower than Investigation 8 proposed: CO₂'s trend makes one expert
  best nearly every month, which puts it close to `fixed` — where the threshold
  is the analytic one. It is not that the source does not matter; it is that the
  ranking's persistence, not the source, sets which regime applies.

## Evidence boundary

The rank positions are measured on the real experts. The losses are constructed
by inversion, so the gap is a quantity this instrument prescribes. Nothing here
establishes that any real process ranks its experts this way.

## The error I made and could not fix by trying harder

The range hypothesis was mine, formed after seeing the falsification, and it was
wrong. Testing it cost one script and removed a plausible-looking explanation
before it reached a report. The duty-cycle measurement replaced it because the
data asked for it, not because I preferred it.

## Open

A threshold defined on a steady state — the median effective count, or the first
month from which the count stays below the floor for `k` consecutive months —
would make the two modes comparable. That is a new instrument and needs its own
frozen protocol. It should not be fitted to this run.
