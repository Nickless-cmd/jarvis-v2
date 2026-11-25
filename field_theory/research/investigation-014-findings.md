# Investigation 14 — why weighting loses, and why the number moves

**Verdict:** `allocation_holds_aggregate_prediction_fell`

Four of five registered conditions hold. The one that fell is my own prediction
about the direction of an aggregate effect — and it fell for a reason worth
keeping.

## The sentence that started this

Investigations 12 and 13 reported that the ensemble's forecast error is a median
**1.43–1.59** times the best single expert's, and that was quoted as *"weighting
loses ~59 % to the best expert"*. That sentence has three problems.

## 1. The number is the aggregate, not the mechanism

Measured on the same 38 196 months, the identical quantity gives:

| aggregate | value |
|---|---:|
| median over 120 cells of (mean error / mean oracle) | **1.173** |
| median over months | **1.217** |
| mean over months | **8.398** |
| p90 over months | 6.156 |
| p99 over months | 52.34 |

The "59 %" is a **cell-median on a 13-point gap grid** (exp_011's 520 cells). On
a 3-point grid it is 1.43 (exp_013). On months it is 1.22. On the mean it is
**740 %**. All four are defensible; none of them is "the" number.

**My registered prediction here was wrong.** I predicted the month-median would
be *lower* than the cell-median, on the theory that a high-ratio cell with many
months dominates its own cell-median. It is **higher** (1.217 vs 1.173): the
high-ratio cells carry more months than the low-ratio ones, so they pull the
month-median *up*. The prediction is falsified and stays in the result.

The real aggregate effect is not cell-against-month. It is **mean against
median**, a factor 6.9, and that is the tail: p99 is 52 and the worst month is
4 494 times the oracle.

## 2. The loss is allocation, and it is monotone in concentration

This is the answer to the question. If the loss were "mixing several experts
together", it would be roughly uniform. It is not — it tracks how much of the
weight sits on the top expert:

| `top_weight` | months | median err/oracle |
|---|---:|---:|
| < 0.50 | 3 767 | **2.285** |
| 0.50–0.80 | 8 755 | 1.696 |
| 0.80–0.95 | 5 061 | 1.370 |
| 0.95–0.99 | 2 733 | 1.089 |
| > 0.99 | 17 880 | **1.002** |

A weight that is nearly all on one expert costs **0.2 %**. A weight spread over
several costs up to 128 %. The loss is the *diffusion* of the weight, not the
act of weighting.

## 3. The mechanism is the residual mass, and it amplifies

Split the weighted sum into the top expert's term and the rest:

```
sum_e w_e a_e  =  w_top a_top  +  sum_{e != top} w_e a_e
```

| residual points | months | share | median err/oracle |
|---|---:|---:|---:|
| **same way** as the top term | 28 290 | 74.1 % | **1.283** |
| **opposite** | 9 906 | 25.9 % | **1.000** |

In three months out of four the small residual mass **adds to** the top expert's
error instead of cancelling it. That is where the whole loss lives. It is also
the measured replacement for Investigation 13's cross-term result: the experts
amplify each other, and the residual mass is the channel through which the
amplification reaches the error.

## 4. It is not warm-up

The weight starts uniform and concentrates over time, so the loss could have been
a transient that averaging over the window hides. It is not:

| window position | median err/oracle | median top_weight |
|---|---:|---:|
| 0–10 % | 1.219 | 0.9755 |
| 10–25 % | 1.262 | 0.9753 |
| 25–50 % | 1.202 | 0.9728 |
| 50–75 % | 1.231 | 0.9796 |
| 75–100 % | 1.195 | 0.9820 |

Spread across the window: **0.068**. The ratio is flat and `top_weight` barely
moves. The loss is a steady-state property.

## 5. A sharpened weight beats both ends — on the mean

`w^alpha` normalised interpolates from the learned weight (`alpha = 1`) to a pure
argmax:

| alpha | mean err/oracle | median err/oracle |
|---|---:|---:|
| 1 (learned) | 8.398 | 1.217 |
| 2 | 8.130 | 1.101 |
| **3** | **8.059** | 1.064 |
| 5 | 8.091 | 1.032 |
| 10 | 8.164 | 1.007 |
| 50 | 8.244 | 1.000 |
| selection | 8.253 | 1.000 |

The **mean has an interior minimum at alpha ≈ 3**, 4.1 % below the learned weight
and 2.4 % below pure selection. The **median falls monotonically** toward 1.000,
so the two aggregates disagree about which end is better: selection wins the
median, a sharpened weight wins the mean.

That disagreement is the same phenomenon as §1, one level down. The median asks
"what happens in a typical month"; the mean asks "what does a bad month cost".
Selection is better in the typical month and worse in the tail, because a
concentrated weight still keeps a sliver of protection.

## What this means for the earlier claims

- "Weighting loses 59 % to the best expert" is **not a property of the
  mechanism**. It is a cell-median on one grid, and on months the same
  measurement is 22 %.
- The reason weighting loses is **not that it mixes**. It is that the weight is
  spread, and the spread sits on experts whose errors point the same way.
- The mechanism is therefore **fixable in principle** — sharpen the weight — but
  the fix trades the median against the mean, and the oracle it is measured
  against uses hindsight every month.

## Controls

- The identity `err == |sum w a|` holds with residual **0.0** on all 38 196
  months, recomposed from the stored weight vector and error directions.
- The hard argmax reproduces `err_selected` **exactly** (worst gap 0.0). A finite
  alpha could not do this and would have failed for arithmetic reasons.
- `a` is read from the **real** predictions, not the constructed ones. A mutation
  restoring the constructed reading is caught by a hand-built row where the
  answer is known (0.0, not gap-driven).
- Both mutations are proven to fall: `a` from constructed predictions, and
  `err_selected` read as `max` instead of the weight's own top.

## Reproducibility

`run_20261125_v2` and `run_20261125_v3` are identical on verdict, conditions,
controls, aggregate, residual, warm-up spread, best alpha, interior gain, the
full concentration table and the full alpha curve. **12 tests green.**

`run_20261125_v1` is kept: it has the failing convergence control, because the
first control was written for a finite alpha and could not converge. The failure
is part of the record, as exp_010's v1 is.
