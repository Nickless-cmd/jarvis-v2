# Experiment 016 protocol — can alpha be chosen before the outcome is known?

**Frozen:** 2026-11-25, before the module that computes anything exists.
This file is committed **on its own**, so `git log` can prove the ordering.

## Provenance

No probe was run for *this* question before this protocol was written. That is
the point of writing it now: Investigations 12–15 each ran exploratory probes
first and had to declare the ordering afterwards. This one does not.

What is known before the measurement, and from where:

- Investigation 15's registered result: moderate sharpening (alpha in {2,3,5,10})
  improves the **conditional** median, the argmax limit does not, and the gain
  holds in every calendar year and in ~69 % of cells at alpha=3.
- Investigation 15's win rate: sharpening beats alpha=1 in **fewer than half**
  of months (47.7 % at alpha=3), so the median gain is a gain in magnitude when
  it wins, not in frequency.
- Investigation 14: the alpha curve has an interior optimum on the mean
  (alpha=3, 8.058) and is monotone on the median.

Those are registered results from earlier experiments, not probes of this one.

## Where the question comes from

Investigation 15 chose alpha=3 **after** seeing which alpha performed best.
That is a hyperparameter picked with hindsight, and it is the weakest kind of
claim: it says a number exists, not that anyone could have found it in advance.

The question asked here is the operational one:

> Can alpha be fixed from information available **before** the outcome, and
> still win on data that was not used to choose it?

## What is actually available ex ante

This has to be stated before any measurement, because it bounds the answer.
`_prepare` builds each row from `prediction_<expert>` and `outcome`, and
`sign` is `1.0 if real[e] >= outcome`. So:

**Available before the outcome:**

- `real[e]` — each expert's own prediction, made before the outcome existed;
- `w` — the weight vector, built from `retained` accumulated over *earlier*
  months, before this month's losses are added;
- `retained`, and the parameters that define a run: retention, gap, expert set,
  assignment.

**Not available before the outcome:**

- `outcome` itself, hence `a[e] = real[e] - outcome`, `err_oracle`, `sign`.

Two consequences follow, and both are load-bearing:

1. `err_oracle` — the denominator of every ratio in Investigations 12–15 — is
   **not** ex ante. Any rule that uses it is hindsight, however it is dressed.
2. The only genuinely ex ante quantities are functions of `w` and of `real`:
   `max(w)`, the spread of `real`, the effective expert count `1/sum(w^2)`, and
   the gap in `retained` between the leader and the runner-up.

## Three strengths of "ex ante", measured separately

They are not interchangeable and a report that merges them is worthless.

**A. Fixed alpha, chosen on an earlier period.** Split every series by date:
development 2000–2012, test 2013–2026. Pick `alpha*` as the one with the best
conditional median on development. Measure it on test, against alpha=1.

**B. Adaptive alpha, chosen per month from an ex ante signal.** A rule
`alpha_t = f(signal_t)` where `signal_t` is one of the ex ante quantities
above, calibrated on development and applied to test.

**C. Oracle alpha.** The best alpha per month, chosen with the outcome in hand.
This is a **ceiling, never a choice**, and it is reported only to say how much
room A and B leave on the table.

## Registered hypotheses

**H1 — a fixed alpha survives the split.** The `alpha*` chosen on development
has a lower conditional median on test than alpha=1. *Falsified if* test
conditional median at `alpha*` is at or above alpha=1.

**H2 — the choice is not sensitive to where the split falls.** Repeating A with
development 2000–2006, 2000–2010 and 2000–2018 gives the same `alpha*`.
*Falsified if* the chosen alpha moves across the three splits.

**H3 — no ex ante signal predicts which alpha is best per month.** For each
candidate signal, the rank correlation with the per-month best alpha is below
0.20 in absolute value. *Falsified if* any signal reaches 0.20.

**H4 — the adaptive rule does not beat the best fixed alpha out of sample.**
On test, `f` chosen on development has a conditional median at or above the
best fixed alpha. *Falsified if* the adaptive rule is strictly better.

**H5 — one trivial regime is real.** alpha=1 is the better choice when the
weight is already concentrated (`max(w) > 0.99`), because there is nothing left
to sharpen. *Falsified if* sharpening still improves the conditional median
inside that subset.

## Controls

- **The split must be temporal.** Development ends before test begins; no
  month appears on both sides. A random split would leak the mechanism's own
  history into its evaluation.
- **`alpha=1` must reproduce Investigation 15.** The ratio at alpha=1 on the
  full set is recomputed and compared against exp_015's summary
  (`unconditional_median` 1.2166164905795165). A mismatch means this module is
  measuring a different object.
- **The oracle alpha is a ceiling.** No sentence may present C as an
  achievable choice.
- **Placebo: a random alpha per month.** Uniform over {1,2,3,5,10}, drawn per
  month with a fixed seed. If the placebo beats the best fixed alpha, the
  comparison is measuring noise and the experiment is void.
- **The error is read from the real predictions**, never the constructed ones
  (Investigation 12).
- **The conditional set is reported per alpha**, so a shrinking set cannot be
  mistaken for an improvement.

## What would make this experiment worthless

If `alpha*` is chosen on development but the development period is short enough
that its conditional median is itself a hit-rate artifact, the transfer is
meaningless. The development and test conditional set sizes are therefore
reported for every alpha, and H2 exists to catch a choice that only works at
one split point.

## Not claimed

Nothing here is a deployed forecast. The losses driving the weights are
constructed from the outcome (Investigation 12), the experts are replayed, and
the oracle is hindsight. The claim under test is narrower: whether a
hyperparameter can be fixed before the outcome and still hold afterwards.
