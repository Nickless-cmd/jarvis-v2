# Investigation 11: four measures, and two of them turned out to be one

**Status:** completed. The proposed replacement for the threshold statistic is
**partly falsified**: three of the four measures are algebraically dependent and
span two degrees of freedom, and the fourth — identity stability — is an
independent axis only when it is measured as dominance share rather than as a
switch count. The frozen definition was tested, fired, and is reported as fired.

Protocol in `experiments/exp_011_four_measures/PROTOCOL.md`, committed **alone**
as `2d9cc7d3c` before the module that computes anything existed. Run preserved in
`artifacts/exp_011_four_measures/run_20261125_v2/`.

## What was asked

Investigation 10 closed with its own instrument as the open problem: the statistic
`mean_effective_experts < 0.5·N` measures an *equilibrium* in `fixed` assignment
and an *occupancy* in `roving`, and the two cannot be compared. One number cannot
say whether a system sits below the floor constantly or oscillates through it.

Four replacements were proposed: **occupancy** (fraction of months below the
floor), **persistence** (how long a collapse lasts), **recovery** (how long
diversity lasts once it returns) and **identity stability** (whether it is the
same expert that dominates).

## The prediction the protocol carried

The first three are not independent. By construction `O·T = K·P` and
`(1−O)·T = K'·R`, so

```
P/(P+R) = O·K' / (O·K' + (1−O)·K)
```

and since collapse and healthy runs alternate, `|K − K'| ≤ 1`. On cells with
`K = K'` the identity collapses to `O = P/(P+R)` exactly.

This was written into the protocol before any measurement, as a prediction rather
than a finding. **It held.**

| test | cells | worst residual |
|---|---:|---:|
| `O = P/(P+R)` where `K = K'` | 7 | 1.1e-16 |
| general form, all cells with both defined | 31 | 1.1e-16 |

Two independent expressions of the same relation, both at floating-point zero.
Occupancy, persistence and recovery are **two degrees of freedom, not three**.
Reporting them as three separate findings would have been one measurement
presented three times.

The narrow form could only be tested on 7 of 132 cells, because a finite window
almost never begins and ends in the same state — 125 cells have `K ≠ K'`. That is
recorded as an amendment: the narrow condition was not loosened, the general form
was added as the diagnostic that actually exercises the algebra.

## The fourth measure, and why it was a grab-bag

Condition 3 fired: no pair of cells shared an occupancy within 0.05 while
differing in identity stability by 0.30. The best pair found differed by 0.16.

That is not an absence of information. It is a defect in the definition, and it
is the same error this investigation exists to name — one name covering several
quantities.

`identity_stability = 1 − switches/(T−1)` divides by the window length, so the
same churn shrinks as the window grows. On a 318-month window, ~51 switches give
**0.839**, which reads as "stable" although the dominant expert changed hands 51
times. It also says nothing about *how* the dominance is distributed: one expert
holding 72.6 % of the window and three sharing it evenly can produce the same
switch count.

Two supplementary measures separate what it merged — `dominance_share` (fraction
of the window held by the single most dominant expert) and `switches_per_month`.
Condition 6 applies the same pair test to `dominance_share`. **It did not fire.**

| | occupancy | dominance share | identity stability | distinct dominants |
|---|---:|---:|---:|---:|
| short_memory, roving, CO₂ | 0.838 | **1.000** | 1.000 | 1 |
| original, q=0, synthetic | 0.855 | **0.525** | 0.950 | 3 |

Same occupancy to within **0.017**. One system is held by a single expert for the
whole window; the other splits it three ways. `identity_stability` reads them as
0.950 and 1.000 — nearly the same — which is exactly backwards.

So the answer to the question the investigation was built on: **the fourth
measure does carry an axis the first three do not, but only when it is measured
as dominance share.** Measured as a switch count it is a window-length artefact.

## Controls and the conditions that did not fire

- **Occupancy equals Investigation 10's `duty_cycle`** on all 132 cells, to
  1e-16. The new instrument measures the same mechanism, so the comparison across
  the two investigations is meaningful.
- **The per-month series reproduces the aggregate** it replaces, to 1e-9.
- **Runs are maximal** and `K`/`K'` differ by at most one on every cell.
- **`fixed` is identity stable**: 48 cells, zero unstable. In `fixed` the rank
  order never changes and the dominant expert never changes hands — dominance
  follows the rank order, not the realised losses.
- **No undefined measure was reported as zero.** 101 of 132 cells have `O = 0` or
  `O = 1`, and on every one the undefined measure is `None`. This is the
  condition Investigation 10 needed and did not have: `mean_over_min = 1.000`
  conflated "always above the floor" with "always below" because neither has a
  spread.

## What this does to Investigation 10

- **Its finding stands.** The threshold statistic does measure different things in
  the two modes, and `duty_cycle` was the right replacement.
- **But `duty_cycle` is one measure of four, and two of the remaining three are
  forced by it.** `O` determines `P` and `R` up to the run-count difference, so
  "occupancy + persistence + recovery" is one number plus a scale, not three.
- **The genuinely new axis is dominance share.** It is not derivable from `O`,
  from `P`, or from `R`, and the pair above demonstrates that with occupancy held
  constant to 0.017.

## The evidence boundary

The rank orders are observed on real experts; the losses are constructed by
inversion, so the gap is a quantity the instrument **prescribes**. Nothing here
establishes that any real process ranks its experts this way.

What is established is narrower and still worth having: of four proposed
measures, three are algebraically dependent and one is not — and the one that is
not was mis-defined in the first draft of the protocol, in the same way
Investigation 10 mis-defined "duty cycle".

## The methodological note worth keeping

This is the third time in two days that an instrument in this project has been
found not to measure what its label said:

1. Investigation 10: "duty cycle" named both `mean/min` and the fraction below
   the floor — opposite readings, identical to four decimals.
2. Investigation 10, second pass: the "duty cycle" test protected a transient
   from zero-initialisation, turning an empirical observation into a requirement
   on the mechanism.
3. Investigation 11: "identity stability" named transition frequency and said
   nothing about dominance distribution.

Each was found by a control written before the result was known. The controls are
not overhead on this work; they are the only reason any of the three is in the
record instead of in the conclusion.
