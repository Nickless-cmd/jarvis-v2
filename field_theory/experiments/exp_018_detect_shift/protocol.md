# Experiment 018 protocol — can a regime shift be detected before the outcome?

**Frozen:** 2026-11-25, before any measurement of this experiment's hypotheses was
computed.

This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering.

## Provenance — one probe ran, and it was not about this question

Investigations 10 through 17 all had to record probes that ran before their
protocol. This one has **one** pre-protocol probe: `/tmp/probe_018_diag.py`.

It measured **Investigation 17's swap placement**, not this experiment's
hypotheses. It established three facts that the design depends on:

1. In Investigation 17, `swap_at = len(rows)//2 = 1599`, which is **1893-04**,
   with `period == "development"`. Evaluation starts at **2000-01**. The shift
   therefore sits **1281 months before** the first evaluated month.
2. The memory of the pre-shift world at evaluation start is `0.99^1281 = 2.6e-6`
   at retention 0.99 — fully decayed.
3. At the first evaluation month, with retention 0.9 and 0.99, the heaviest
   weight already sits on the structurally best expert (`cycle_lag_132`,
   `w = 0.448` and `0.978`).

**Consequence for Investigation 17, recorded here because it is a correction and
not a detail.** Its reported delay of 6.0 / 8.5 / 126.0 months is measured from
the first evaluation month, not from the shift. It is the time, long after the
world already changed, for the weight to land on the new best expert. The number
is real; the name it was given is wrong. This experiment does not reuse that
placement.

The same probe measured the placement this experiment **will** use — a shift at
the evaluation midpoint — and produced delays 2 / 24 / 150 with accumulated
excess 13.9 / 55.0 / 395.2. Those numbers are visible to me before the protocol
is written. That is a contamination of any hypothesis about the *size* of the
cost, so this experiment registers **no hypothesis about cost**. It asks only
whether the shift is detectable, which the probe did not measure.

## The question

Investigations 8–17 measured the mechanism's error. Every one of them grades the
mechanism against an outcome that has already happened. The operational question
is different and harder:

> Before the outcome of the current month is known, can the mechanism tell that
> the world has changed?

If it can, the cost measured in Investigation 17 is avoidable — the mechanism
could shorten its own memory at the moment of change instead of paying for it
over 150 months. If it cannot, the cost is the price of not knowing, and that is
a different and more honest statement than "retention is expensive".

## The design — an identity swap placed inside the evaluated window

The regime shift is Investigation 17's, unchanged: **an exchange of prediction
series between expert names.** Expert `e_i` delivers series `s_i` before the
shift and series `s_{(i+1) mod n}` after it. Every number is a real prediction
from `experiment_009._predict`; the outcome is never touched.

The one change is placement. The shift is at the **evaluation midpoint**, the
month that splits the evaluated months into two halves of equal size. It is
derived from the data, not chosen by me: for the sunspot series it lands on
**2013-04** with 159 evaluated months on each side.

The control is the identical accumulation with no swap, so the difference
between the two runs is the shift and nothing else.

## What is a detector, exactly

A detector sees, at month `t`, **only**:

- `real[e]` for every expert — this month's predictions, and their history,
- the weight vector `w` and the accumulated `retained` from months before `t`.

A detector may **never** see `outcome`, `a`, `err`, `err_oracle` or `losses` at
or after month `t`. Those are the outcome. A detector that reads them is not a
detector, it is a hindsight measurement wearing a detector's clothes.

This is enforced mechanically, not by discipline: control **C1** below mutates
every outcome in the data and requires the detector's output to be
**bit-identical**.

## Two classes of ex ante statistic, and why the distinction is the whole point

The shift is a **permutation of the prediction columns**. The multiset of series
in a cell is unchanged; only which name holds which series changes.

Therefore any statistic that is **symmetric in the expert names** — the spread of
the predictions, their dispersion, the entropy of the weights, the mean absolute
prediction — is **exactly identical** in the shifted and the control run, at
every month, forever. It cannot detect the shift. Not weakly: identically zero
power.

**H1 — the invariant class has exactly zero power.** For a battery of
name-symmetric ex ante statistics, the maximum absolute difference between the
shifted and the control run is exactly `0.0` at every month. Any non-zero value
means the statistic is not symmetric and the classification is wrong.

Only **name-aware** statistics can differ. The natural one is a **fingerprint of
each name's prediction stream**: the shape of the series that name is delivering.
`previous_month` is noisy; `trailing_12_mean` is smooth; `cycle_lag_132` is a
lagged smooth series. Those shapes are distinguishable from the numbers alone,
without any outcome.

**H2 — a shift can be recognised before the outcome.** A causal fingerprint of
each name's prediction stream, matched against that name's pre-shift fingerprint,
recovers the permutation with **exact-match accuracy ≥ 0.9** at some window
length in the registered grid.

This is the positive answer, and its scope is narrow and must be stated with it:
the detector recognises the new world **as a world it has already seen**. It
detects a change of **ownership**, not a change of the world.

**H3 — speed is bought with window length, and the price is measurable.** A
shorter trailing window detects sooner and identifies worse. For each window
`W` the experiment reports the detection delay and the exact-match accuracy, so
the frontier is a measurement rather than a trade-off asserted in prose.

**H4 — the detector does not fire on a world that has not changed.** Run on the
control series, the same detector must return the **identity** mapping. A
detector that reports a shift in the unshifted control is measuring its own
noise.

**H5 — recognition is not discovery, and the detector can be made to know it.**
With the true match **held out** of the reference set, the accuracy must fall to
chance. A nearest-neighbour rule always returns an answer, so the failure is not
silence — it is a confident wrong answer. The registered second half of H5 is the
one that matters operationally: the distance to the nearest reference must be
**larger** under the held-out case than under the true permutation, so a
threshold can tell "I have seen this before" from "I have not".

## The fingerprint — registered before measurement

Each feature is computed from `real[e]` alone over a trailing window of `W`
months ending at month `t`, and is scale-free:

1. `f_step` — `mean(|real_t − real_{t−1}|) / mean(|real − median(window)|)`.
   How jagged the series is. `previous_month` scores high, a 12-month mean low.
2. `f_ac1` — lag-1 autocorrelation of the series inside the window.
3. `f_tie` — the share of months where `real_t == real_{t−1}` exactly. A
   trailing mean almost never repeats a value; a lag series can.

Matching: features are z-scored across the reference set and assigned by nearest
neighbour in Euclidean distance. No feature is fitted to the shift, and no
parameter is tuned after the fact. The grid is registered now:

- windows `W ∈ {6, 12, 24, 36}` months,
- expert sets: all five in `EXPERT_SETS`,
- sources: `sunspots` and `co2`,
- assignment: `roving` (the fingerprint does not depend on `gap` or `retention`,
  and that independence is itself a result — see below).

## Why the detector's independence from retention matters

The fingerprint reads the prediction streams. Those do not depend on `retention`
or `gap`, which are the mechanism's own memory knobs. So detection cost is
**decoupled** from the memory knob: a mechanism can detect a shift in `W` months
regardless of whether it remembers for 6 or 150. If H2 holds, that decoupling is
the operational finding of the evening, because Investigation 17 showed the
memory knob alone sets the price at 13.9 to 395.2.

## Controls — each of which can kill the run

- **C1 — the detector cannot see the outcome.** Every `outcome` in the data is
  replaced by a different value; the fingerprint output must be bit-identical.
  If it changes, the detector is contaminated and no result is reported.
- **C2 — the shift is a permutation, not a data change.** The sorted predictions
  are unchanged across the swap, to `1e-12`.
- **C3 — the no-swap path is a fixed point.** `shifted=False` reproduces
  `experiment_010._prepare` byte for byte.
- **C4 — the reference is stable before the shift.** Computed on two disjoint
  halves of the pre-shift window, the same-name match must be the identity. If
  the reference does not identify a name against itself, nothing downstream
  means anything.

## Registered hypotheses, all falsifiable

| # | hypothesis | falsified by |
|---|---|---|
| H1 | name-symmetric statistics have exactly zero power | any difference `> 0.0` |
| H2 | fingerprint recovers the permutation, accuracy ≥ 0.9 | accuracy `< 0.9` at every window |
| H3 | shorter window detects sooner and identifies worse | no monotone frontier |
| H4 | control run returns the identity | any non-identity assignment on control |
| H5 | held-out match falls to chance, and distance separates | accuracy stays high, or distance does not separate |

H2 and H5 point in opposite directions on purpose. H2 asks whether recognition
works; H5 asks what it costs to mistake recognition for discovery. A run that
reports only H2 would be the flattering half.

## What this experiment does not measure

It does not measure a regime shift in which the world changes to something
**new** — where no name delivers a series it has delivered before. Under such a
shift the prediction streams change distribution without exchanging identity,
and H1's invariance argument no longer applies, because the multiset itself
changes. That case is not built here, and the absence is deliberate: it requires
a counterfactual outcome generator, and inventing one to make a detector fail
would be the same error as constructing predictions from the outcome in
Investigation 10.

The limit is therefore stated as a scope condition, not as a measurement, and
H5 is the closest the data can come to it.
