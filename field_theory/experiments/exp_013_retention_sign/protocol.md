# Experiment 013 protocol — the regime where retention has a reliable sign

**Frozen:** 2026-11-25, after exploratory probes and before the module that
computes the registered measurement existed.

## Provenance — read this before anything else

Investigation 10 could not claim preregistration and had to record why.
Investigation 11 could, because its protocol was committed alone first. This one
**cannot** either, and the difference matters:

I ran four exploratory probes on the real grid before writing this file. They
established, in order:

1. The ensemble beats the best single expert in 2 974 of 19 170 months (15.5 %),
   and only 56.7 % of months have all error signs pointing the same way. My
   earlier claim — that "the ensemble never beats the oracle, as the arithmetic of
   a convex combination requires" — is **wrong**. The correct inequality is
   `|sum w a| <= sum w |a|`, which gives no lower bound; GPT was right and I was
   wrong, and the claim is retracted in the findings.
2. The decomposition `(sum w_e a_e)^2 = sum w_e^2 a_e^2 + 2 sum_{i<j} w_i w_j a_i a_j`
   has a **positive** cross term in 59 of 60 cells (median `cross/diag` +0.285).
   The experts amplify each other's errors; they almost never cancel. That is the
   measured reason the ensemble does not beat the oracle on cell level — not
   arithmetic, but a property of these data.
3. Two candidate regimes failed: `top-expert stable` flips sign between the two
   sources under hold-out, and expert disagreement is nearly uncorrelated with the
   quantity it would have to replace (+0.049).
4. The one regime that survives is the ensemble's distance from the oracle,
   and it survives split-half.

So this protocol is **not** a prediction written before looking. It is a
registration of what will be measured, with the exploratory history declared.
The distinction is exactly the one a governance veto in this system is meant to
enforce, and I am stating it rather than dressing the order of events up.

## The question

Investigation 12 established that retention reaches the forecast through one
channel only — the weight vector — and that the error is 93 % data. It left a
specific opening: retention moved the true error in 208 of 260 pairs, with a
maximum of 10.77. Where does that effect have a **reliable sign**?

The question has two halves and they are not interchangeable:

- **Ex post:** conditional on the outcome, is there a regime where retention's
  effect is consistent?
- **Ex ante:** can that regime be known *before* the outcome is observed?

The second is the only one with operational value, and it is the one GPT's
distinction between absolute error, error change, and knowable-in-advance error
points at.

## Hypotheses, stated as falsifiable claims

**H1 — the ensemble can beat the oracle.** If the cross term is negative in some
month, `|sum w a| < min_e |a_e|` is possible. Falsified if the ensemble never
beats the oracle on month level.

**H2 — the experts' errors amplify rather than cancel.** Falsified if
`cross/diag > 0` in fewer than 90 % of cells. This is what makes H1 rare rather
than common.

**H3 — a regime with a reliable sign exists ex post.** The ensemble's error
relative to the best single expert (`ratio = err / oracle`) predicts the sign of
the retention effect. Falsified if `corr(ratio, d_err) > -0.40`.

**H4 — the regime is not regression to the mean.** A high error falls toward the
mean for arithmetic reasons. The test is split-half: `ratio` measured on the
first half of the evaluation months must predict `d_err` on the **second** half,
where the two quantities share no month. Falsified if
`R^2(ratio_first, d_second) < 0.15`.

**H5 — no ex ante regime exists.** The strongest predictor available before the
outcome is the top weight at low retention. Falsified if any ex ante predictor
reaches `R^2 >= 0.20` against `d_err` — half of what the ex post measure
achieves. If H5 holds, the regime is descriptive and not prescriptive, and that
is the honest headline.

## Measurements registered

Per cell — two sources (`sunspots`, `co2`) × five expert sets × two assignments
(`fixed`, `roving`) × three gaps (0.05, 0.2, 0.8) = 60 cells:

- `cross_share` = mean `cross / diag` over evaluation months
- `months_ensemble_beats_oracle`, and the total month count
- `d_err` = mean error at retention 0.99 minus at 0.9
- `ratio_short` = mean error at 0.9 divided by mean oracle error
- split-half: `ratio_first`, `ratio_second`, `d_first`, `d_second`
- ex ante candidates: `top_weight_short`, `exante_spread` (standard deviation of
  the experts' own predictions, which is known before the outcome)
- hold-out between the two sources for the surviving candidate regimes

## What would make this investigation worthless

Four failure modes, each checked explicitly:

1. **The identity must hold.** `error == |sum w a|`; residual must be 0.0.
2. **The cross term must be computed against a positive denominator.** An earlier
   probe divided by `(sum w a)^2`, which can be near zero, and produced a
   "cross share" of −972 570. That is an artefact of division by nothing, not a
   measurement. The registered denominator is `sum w_e^2 a_e^2`, which is
   strictly positive whenever any error is non-zero.
3. **The ex post result must not be reported as operational.** If H5 holds, no
   sentence may suggest the regime can be used before the outcome.
4. **The hold-out must be reported even when it fails.** It failed for
   `top-expert stable`; that failure is part of the result and stays in.

## Reference

Findings: `research/investigation-013-findings.md`. Predecessors:
`investigation-011-findings.md` (four measures), `investigation-012-findings.md`
(the path from retention to the forecast).
