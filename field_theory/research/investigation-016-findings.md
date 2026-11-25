# Investigation 16 — alpha can be fixed before the outcome, but not chosen per month

Investigation 15 established that moderate sharpening improves the conditional
median and that the argmax limit does not. But `alpha=3` was chosen **after**
seeing which alpha performed best. That is a hyperparameter picked with
hindsight: it says a number exists, not that anyone could have found it in
advance.

This investigation asks the operational version. The protocol was committed
alone as `07a5622af` before the module existed, so `git log` can prove the
ordering.

## What is ex ante, and what is not

Settled before any measurement, because it bounds the answer. `_prepare` builds
`sign` as `1.0 if real[e] >= outcome`, and `losses` from `real` and `outcome`.
So:

- **Available before the outcome:** `real` (each expert's own prediction), `w`
  (built from `retained` over *earlier* months), `retained`, and the parameters
  defining a run.
- **Not available:** `outcome`, hence `a = real − outcome`, `err_oracle`, `sign`.

The consequence is load-bearing: `err_oracle` is the denominator of every ratio
in Investigations 12–15, and it is **not** ex ante. Any rule that uses it is
hindsight, however it is dressed. Every signal tested here is a function of `w`,
`real` and `retained` only.

## The answer, in two halves

**A fixed alpha transfers.** Chosen on development (2000–2012) as the one with
the best conditional median, and measured on test (2013–2026):

| | conditional median |
|---|---:|
| alpha = 1 (no sharpening) | 1.8646 |
| alpha = 10, chosen on development | **1.4209** |

That is 24 % better, on months the choice never saw. And the choice does not
depend on where the split falls — development ending in 2006, 2010 and 2018 all
pick the same alpha:

| development ends | chosen alpha |
|---|---:|
| 2006 | 10.0 |
| 2010 | 10.0 |
| 2018 | 10.0 |

**An adaptive alpha does not.** A rule that picks alpha per month from an ex
ante signal, calibrated on development and applied to test, lands at 1.42091
against the best fixed alpha's 1.42093 — a ratio of 0.999987. It wins by two
parts in a hundred thousand. That is a tie, not a win.

There is a detail behind that number worth stating, because it makes the "tie"
partly definitional. Of the four signals, **one never moved** — `spread` picked
alpha = 10 in all four splits (10/10/10/10) and is therefore the fixed choice
wearing an adaptive name. A second, `retained_gap`, moved in only one split
(10/10/10/5). Only `top_weight` and `effective` vary their choice across the whole
range, and they vary it in mirror image: 10/10/5/1 against 1/5/10/10.

So the honest reading is narrower than "adaptivity does not help": **one of four
signals degenerated to the constant, one nearly did, and the two that genuinely
moved landed within 2·10⁻⁵ of it.**

## The signal is real but weak — and it is one signal, not two

My registered hypothesis H3 said no ex ante signal would reach a rank
correlation of 0.20 with the per-month best alpha. **It was falsified:**

| signal | Spearman | over threshold |
|---|---:|---|
| `top_weight` | −0.2208 | yes |
| `effective` (1/Σw²) | +0.2218 | yes |
| `spread` of `real` | −0.1170 | no |
| `retained_gap` | −0.0228 | no |

The two that pass are **strongly correlated with opposite signs** (ρ = −0.221 and
+0.222), and their alpha choices are exact mirrors of each other: `top_weight`
picks 10, 10, 5, 1 across the four splits where `effective` picks 1, 5, 10, 10.
That is why they are counted as **one** signal here — reporting both would be the
run-count error again.

But "same axis" is an empirical statement about these data, not an algebraic
identity, and an earlier version of this paragraph overstated it. They are not
mathematically equivalent: weights 50/25/25 and 50/49/1 both have a top weight of
0.5 while their effective counts are 2.67 and 2.04. The measured correlation is
what licenses treating them as one signal; the algebra does not.

## The room exists — the rule does not find it

A per-month choice made with the outcome in hand reaches a conditional median of
**1.2959**, against the best fixed alpha's 1.4209. So a perfect chooser would
gain another 8.8 %. The ex ante rule captured **none** of it.

That is the sharpest form of the answer: the room is not empty, and the
information available before the outcome does not reach it. The gap between
1.4209 and 1.2959 is what hindsight is worth here.

## What actually carries the gain

The placebo draws a random alpha per month from {1,2,3,5,10}, 200 times with a
fixed seed:

| choice | conditional median |
|---|---:|
| alpha = 1 always | 1.8646 |
| random alpha per month | 1.6041 (min 1.5880, max 1.6258) |
| alpha = 10 always | 1.4209 |
| per-month oracle | 1.2959 |

Random sharpening recovers **59 %** of the gain from 1.8646 to 1.4209. So most
of the benefit is *sharpening at all*, not *sharpening exactly right*. Picking
the precise alpha is worth the remaining 41 %, and no ex ante rule I tested
reaches it.

## The concentrated regime is not a separate regime

H5 predicted that alpha=1 would be better once the weight is already
concentrated (`max(w) > 0.99`), because there is nothing left to sharpen. Over
17 939 such months, restricted to the 7 070 where every candidate has something
to lose:

| alpha | conditional median |
|---|---:|
| 1 | 2.0913 |
| 3 | 2.0895 |

Ratio 0.99917 — 0.08 % better, inside the tolerance. The regime is not a
regime; sharpening neither helps nor hurts when the weight is already on one
expert.

**This is the one conclusion that depends on the tolerance.** Tested directly
against the raw ratios, without any margin: H4 survives at every tolerance above
2·10⁻⁵ — its largest deviation is 1.91·10⁻⁵, fifty-two times below the 10⁻³ that
was applied, so no reasonable margin changes it. H5 does not survive: 0.99917 is
strictly below 1.0, so with zero tolerance sharpening *is* better in the
concentrated regime and H5 is falsified. The difference is 0.08 %, which is why it
was called meaningless — but "meaningless" is a judgement, and the verdict moves
with it. Stated so the reader can price it.

## Deviations from the protocol

Stated plainly, because a frozen protocol that is quietly edited is worth
nothing.

1. **A tolerance was introduced after the first run.** The protocol's decision
   rules said "strictly better" with no margin. The first run (artifact `v1`)
   failed H4 and H5 on differences of 2·10⁻⁵ and 8·10⁻⁴ — numerically nonzero
   and operationally meaningless. `MEANINGFUL = 1e-3` was added, and the raw
   ratio is now reported beside every decision so the threshold cannot hide
   anything. `v1` is kept with its failing verdict.
2. **The ceiling was wrong in the first two runs.** The protocol registered C as
   a *per-month* choice with the outcome in hand; the code computed the best
   *fixed* alpha on test. Those are different objects, and reporting one as the
   other understates the room a perfect chooser would have. Corrected in `v3`;
   the per-month ceiling is 1.2959.
3. **A month-set name was misleading.** `common_non_hit.pooled` held the
   *discriminating* months, a different set. Renamed to `month_sets` in `v4`.

## Controls

All pass, and each one can fail:

- `identity_holds` — `error == |Σ w·a|`, worst residual **0.0**.
- `identity_against_exp_015` — the alpha=1 unconditional median recomputed here
  is **1.2166164905795165**, exactly Investigation 15's registered value. This
  is the control that proves the module measures the same object.
- `limit_reproduces_selection` — the hard argmax equals `err_selected`, gap
  **0.0**.
- `leader_equals_argmin` — 38 340 of 38 340 months. Sharpening is following the
  leader, and it is named as such.
- `split_is_temporal` — every development year precedes every test year.
- `placebo_does_not_beat_best_fixed` — 1.6041 ≥ 1.4209.

## Not claimed

Nothing here is a deployed forecast. The losses driving the weights are
constructed from the outcome (Investigation 12), the experts are replayed, and
the oracle is hindsight. The claim is narrower: **a hyperparameter can be fixed
before the outcome and still hold afterwards, but it cannot be adapted per month
from what is known before the outcome.** The 8.8 % between the fixed choice and
the per-month ceiling is the measured price of not knowing the outcome.
