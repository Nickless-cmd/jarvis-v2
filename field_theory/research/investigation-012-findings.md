# Investigation 12: retention reaches the forecast — but the forecast is mostly not structure

**Status:** completed, **negative** on the question that motivated it, and the
negative result is the useful one.

**Provenance, stated precisely.** The probes below were run *before* this file was
written. Unlike Investigations 5–9, this investigation cannot claim a frozen
protocol, and it should not pretend to. What it can claim is that every number
here was measured on the same mechanism as Investigations 10–11, using the
sources already in the repository, and that the probes are reproducible from the
code paths named below.

## What was asked

Investigation 11 established that no structural measure predicts the forecast
error — best R² 0.077 across 520 cells. But retention *did* move the true error
in 208 of 260 retention pairs. The question was how: by what path does retention
reach the forecast when the measures cannot see it?

## The mechanism, read from the code

In `experiment_011_four_measures._measure_series` the accumulation uses
predictions **constructed from the outcome**:

```
prediction_e = outcome + sign_e · (l_best + δ_e) · scale
```

so the constructed loss is a function of the imposed gap, and the constructed
MAE rises monotonically with `gap` in every cell (6.478 at gap 0.0005 to 16.323
at gap 0.9477). That quantity is not a forecast.

The real forecast is the ensemble of the experts' own predictions:

```
ensemble = Σ_e w_e · real_e        error = |Σ_e w_e · a_e|,  a_e = real_e − outcome
```

Measured identity: `error == |Σ w a|` with **residual 0.0** on all 60 cells.
That is arithmetic, not a finding — but it settles the path: **retention can only
reach the forecast through the weight vector `w`.** The rank order (`orders`)
does not depend on retention, and `a` is data. There is no second channel.

## Where the error actually comes from

120 observations — two sources, five expert sets, two assignments, three gaps,
two retentions. Total error variation SS = 8297, mean 9.543, range 1.16–36.96.

Share of the **total** error variation explained by each factor alone:

| factor | groups | η² |
|---|---:|---:|
| source (`sunspots` / `co2`) | 2 | **0.798** |
| expert set | 5 | 0.114 |
| assignment (`fixed` / `roving`) | 2 | 0.001 |
| gap | 3 | 0.003 |
| **retention** | 2 | **0.002** |

And as continuous covariates:

| covariate | share of total variation |
|---|---:|
| oracle error (best single expert) | **93.4 %** |
| top weight (structure) | 2.6 % |

Within every expert set separately, the oracle error explains 86–99.8 % of the
error level, the top weight 0.1–13 %:

| set | R²(top weight) | R²(oracle) |
|---|---:|---:|
| four_experts | 0.059 | 0.980 |
| long_memory | 0.130 | 0.864 |
| original | 0.067 | 0.960 |
| short_memory | 0.001 | 0.997 |
| two_experts | 0.012 | 0.998 |

**The forecast error is 93 % data and 3 % structure.** No structural measure can
predict it, and that is not a defect in the measures. It is a property of the
problem: the measures describe how weight is distributed, and the error measures
how far the ensemble lands from an outcome that the distribution does not contain.

## The one path retention actually takes

Retention raises concentration. Measured as the correlation between the change in
top weight and the change in true error across the 60 retention pairs:

`corr(Δ top weight, Δ error) = −0.414`, R² = 0.171 — and it survives removing the
most reactive expert set (`long_memory`): **−0.382, R² = 0.146**.

Why concentration helps: the ensemble is worse than the best single expert.
Median `error / oracle` is **1.432** at retention 0.9 and **1.367** at 0.99 — high
retention buys 6.4 % of the gap to the oracle. And concentration tracks that gap
directly: `corr(top weight, error/oracle) = −0.463`, R² = 0.214.

So the path is: **retention concentrates the weight, and a concentrated weight is
closer to choosing the best expert than to averaging disagreeing ones.** It is
the price of weighting rather than selecting, and retention pays a little of it.

## What does not happen

The alignment between weight and error direction — `corr(w_e, |a_e|)` per month,
negative when the weight sits on the good experts — is **−0.42 in `fixed` and
−0.55 in `roving`**, and higher retention makes it *worse* in both (−0.38 and
−0.45). The change in alignment explains **0.000** of the change in error.

Retention does not make the ensemble smarter about *which* expert is right. It
makes it less willing to average.

## The size of the effect, stated honestly

Within each cell, comparing retention 0.9 with 0.99:

| statistic | value |
|---|---:|
| median change | **−0.005** |
| mean change | −0.690 |
| std | 2.263 |
| range | −10.61 to +4.32 |
| pairs where the error falls | **34 of 60 (57 %)** |
| median \|change\| as a share of the error level | **4.9 %** |

Retention moves the forecast in 57 % of pairs and worsens it in 43 %. The median
effect is half a percent of the error level; the mean is carried by a handful of
large cases. **Retention reaches the forecast, but weakly and without a reliable
sign.** Reporting the mean (−0.69) as "retention improves the forecast" would be
the same error this whole sequence of investigations has been about: naming an
observation after the mechanism one hopes lies behind it.

## What this does to Investigations 10 and 11

Nothing in their structure claims is retracted. What is now bounded is their
*relevance*: the apparatus describes the weight structure precisely, and the
weight structure accounts for about 3 % of the forecast error. Investigations
8–11 built an instrument for a quantity that turns out to be nearly independent
of the thing one would want to predict.

The corollary is the useful part: **to predict whether a weighted ensemble
forecasts well, measure the disagreement among its members and the error of its
best member — not the shape of its weights.**

## Controls

- `error == |Σ w a|` — residual 0.0, all 60 cells (the path is the only one).
- Ensemble never beats the oracle: arithmetically required of a convex
  combination, and observed in 0 of 520 cells in the earlier probe.
- The constructed MAE is monotone in `gap` in every cell. The true error is
  monotone in **2 of 20** groups — a share of 0.10, *below* the 1-in-6 a random
  ordering of three gap points would produce by chance. The two quantities are
  not the same measurement.
  An earlier probe with the 13-point gap grid gave 0 of 40. The 3-point grid used
  here is coarser, so the honest statement is the share against the chance rate,
  not a zero. My first version of this control demanded exactly zero and failed
  for the wrong reason — that is recorded rather than quietly loosened.
- **Two faults were found in this investigation's own verdict logic.** Condition 1
  was written as `1_identity_does_not_hold` — a fault condition among four success
  conditions — so `all(conditions.values())` could never be true and the verdict
  fell through to `error_is_data_but_a_control_failed` while all five conditions
  were met. Measured and reproduced: the renamed version yields
  `error_is_data_retention_path_is_concentration_without_sign`. This is the same
  class of error as the sign of `argmax` in Investigation 11: a name pointing the
  wrong way, and the tests were green either way. A test now pins the reachable
  verdict string.
- The concentration effect was re-measured without `long_memory`: R² 0.171 →
  0.146, direction unchanged.

## The evidence boundary

Two sources, both monthly and both geophysical (`sunspots`, `co2`). Five expert
sets. The result that the error is dominated by data rather than structure is
strong within this design and says nothing about a system whose members are
genuinely independent rather than five transformations of the same series. The
retention effect is measured on 60 pairs, and 34/60 is not a sign.

## The methodological note worth keeping

This investigation was run without a frozen protocol, after the measurement, and
the file says so at the top rather than in a footnote. That is the weaker form,
and it is the honest one. The alternative — writing "frozen before the run" over
a probe already executed — is exactly what Investigation 10 had to correct, and
the correction cost more than the claim was worth.
