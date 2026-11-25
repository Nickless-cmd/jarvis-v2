# Investigation 13 — the regime where retention has a reliable sign

**Question.** Investigation 12 showed retention reaches the forecast through one
channel only, the weight vector, and that the error is 93 % data. It left a
specific opening: retention moved the true error in 208 of 260 pairs, up to 10.77.
Where does that effect have a consistent sign — and can the sign be known before
the outcome is observed?

The second half is the only one with operational value. The answer to it is no.

## First: a claim of mine was wrong, and it is retracted

Investigation 12 reported that the ensemble never beats the best single expert
"as the arithmetic of a convex combination requires". That is not arithmetic. The
correct statement is

    |sum_e w_e a_e|  <=  sum_e w_e |a_e|

which is an upper bound and gives no lower bound at all. When the experts' errors
point in opposite directions their weighted mean can be closer to the outcome than
any of them. The textbook case is two experts at 90 and 110 against an outcome of
100: each is off by 10, the 50/50 ensemble is exact.

Measured on the real grid: **the ensemble beats the best single expert in 2 974 of
19 170 months (15.5 %)**, and the worst month is 4 494 times worse than the best
expert. The claim was wrong on month level. It happens to hold on cell level
(0 of 60 cells) — but for a reason I had not measured, not for the reason I gave.

## The measured reason it is rare: the experts amplify each other

Decomposing the squared error over the members:

    (sum_e w_e a_e)^2  =  sum_e w_e^2 a_e^2  +  2 sum_{i<j} w_i w_j a_i a_j

The cross term is where the relations between the experts live. Measured across
all 60 cells: **positive in 59 of 60, median `cross/diag` +0.285.** The experts'
errors reinforce each other; they almost never cancel. That is a property of these
data, and it is the honest replacement for the arithmetic argument that did not
hold.

One caveat on my own measurement, because it cost a number already: an earlier
probe divided the cross term by `(sum w a)^2`, which can be near zero, and
produced a "cross share" of −972 570. That is division by nothing. The registered
denominator is the diagonal term, which is strictly positive whenever any error is
non-zero. A code test pins it.

## The regime exists — but it needs the outcome

The ensemble's error relative to the best single expert, `ratio = err / oracle`,
predicts the sign of the retention effect:

| statistic | value |
|---|---:|
| `corr(ratio, d_err)` | **−0.551** |
| R² | 0.304 |
| `corr(err_level, d_err)` | −0.263 |
| cells where error falls | 34 of 60 |

Note the second-to-last line. The plain error level is a much weaker predictor
than the ratio, so this is not simply "high error falls back". The signal is
specific to *the distance from the best available choice* — the price of weighting
rather than selecting. High retention concentrates the weight, and a concentrated
weight is nearer to choosing the best expert than to averaging disagreeing ones.

**Is it regression to the mean?** A high error falls toward the mean for purely
arithmetic reasons, so a same-measurement correlation proves nothing. The test is
split-half: `ratio` measured on the first half of the evaluation months against
`d_err` on the **second** half, where the two share no month.

| correlation | R² |
|---|---:|
| `ratio_first` → `d_second` | **0.358** |
| `ratio_second` → `d_first` | 0.208 |
| `ratio_first` → `d_first` (same half) | 0.249 |

Both cross-half values exceed the same-half value. If the effect were mean
reversion inside one measurement, the opposite would hold. It is a real structural
link, not an artefact of choosing the extreme cells.

## But it cannot be known in advance, and that is the answer

Everything above uses `oracle = min_e |a_e|`, which requires the outcome. The only
question with operational value is what can be known *before* it. Measured against
`d_err`:

| ex ante predictor | R² |
|---|---:|
| top weight at low retention | **0.150** |
| top-expert agreement between the two retention levels | 0.035 |
| expert disagreement (std of the experts' own predictions) | **0.034** |

The best predictor available before the outcome explains 15 %, against 30 % for
the ex post measure. **Seventy percent of the variation in the retention effect is
not available until the outcome is known.**

And the intuitive candidate is the emptiest of all. The disagreement between the
experts' own predictions — the obvious proxy for "there is something to gain here"
— explains 3.4 %, and correlates **+0.049** with the ex post quantity it would
have to replace. It is not a weak version of the regime; it is unrelated to it.

**Why, in one sentence:** the sign of the retention effect is decided by whether
the expert that concentration favours is better than the average — and that is a
property of the outcome, not of the structure. No reorganisation of the structural
measures can recover it, because the information is not there.

## The hold-out that failed, kept in

The most plausible structural candidate was top-expert stability: if the dominant
expert is the same at both retention levels, concentration should not hurt.

| train → test | train median | test median | sign preserved |
|---|---:|---:|---|
| sunspots → co2, top stable | +0.002 | −0.057 | **no** |
| co2 → sunspots, top stable | −0.057 | +0.002 | **no** |
| sunspots → co2, top shifts | +0.088 | +0.215 | yes (test n = 3) |
| co2 → sunspots, top shifts | +0.215 | +0.088 | yes (test n = 15) |

The candidate flips sign in both directions. The one variant that preserves sign is
carried by **three cells** on one side, which is not evidence of a regime. It stays
in the result because dropping a failed hold-out is how a weak finding becomes a
strong one.

## What this adds up to

Investigations 8–13 have built an apparatus that describes weight structure
precisely: occupancy, persistence, recovery, identity stability, run shape,
concentration, the cross term. Applied to forecast error it says almost nothing,
and now the reason is measured rather than asserted:

- the error is data (93 %), not structure;
- the one structural channel, concentration, works through the distance to the
  best choice;
- that distance requires the outcome;
- so the effect has a reliable sign **and is unusable in advance**.

That is a negative result of the useful kind: it closes a question instead of
leaving it open. The alternative — reporting "retention improves the forecast when
the ensemble is far from the oracle" as though it were a finding — would have been
true and useless at the same time.

## Controls

- The identity `error == |sum w a|` holds with residual **0.0**, recomposed from
  the stored weights and error directions.
- The cross share uses the diagonal denominator; a code test fails when it is
  replaced by `(sum w a)^2`.
- Sourcing the error from the constructed predictions instead of `real` fails a
  code test. That is the mutation that would silently turn this into Investigation
  12's original mistake.
- The ensemble really does beat the oracle in some months, so the retraction is
  measured rather than merely stated.
- The failed hold-out is in the artifact, not only in this text.

Reference: `experiments/exp_013_retention_sign/protocol.md` — whose provenance
section states that four exploratory probes ran before it was written. This is not
a preregistered experiment, and it does not claim to be.
