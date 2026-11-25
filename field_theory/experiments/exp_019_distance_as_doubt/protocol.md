# Experiment 019 protocol — can the detector's distance be used as self-doubt?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering.

## Provenance — this one is exploratory, and that has to be said first

Investigations 10 through 17 each had to record that a probe ran before the
protocol was written. Investigation 18b declared itself exploratory for a
different reason: its lag features were chosen after the registered shape
fingerprint failed its own C4.

This one is exploratory for a third reason, and it is the strongest of the
three: **the premise comes from a sentence already written in
`research/investigation-018-findings.md`.** That sentence says the held-out
distance "is a usable self-doubt signal". It was written from a table whose
per-cell sample is three experts. This experiment exists to test whether that
sentence is true, not to discover something new.

So the registered hypotheses below are written knowing that the table they came
from exists. That is a weaker position than 017's, where nothing had been
measured. It is stated here rather than hidden, and the falsification conditions
are set as hard as the position allows.

## The claim under test

Investigation 18's H5 compared two **constructed conditions**: the reference
with the true name present, and the reference with the true name removed. The
distance to the nearest remaining reference was larger in the second case, at
every window, and the ratio grew with the window.

Two things are wrong with reading that as self-doubt:

1. **It compares conditions the detector cannot choose between.** In operation
   the reference is always complete — it is built from the world the detector
   knows. The held-out condition is a question the operator never asks. What
   matters is whether the distance, *inside* the ordinary condition, separates
   a right match from a wrong one.
2. **The sample is three.** `held_out_total` is 3 in every cell, because a cell
   has three experts. A median of three numbers is not a signal, and the ratio
   between two such medians is not a measurement of separation.

The real question is therefore: **month by month, in ordinary operation, does
the distance to the chosen reference name predict whether that choice is
correct?**

## What is measured, and from where

The detector is `experiment_018b_lag_fingerprint`. Its `_match` already computes
the distance for every name and then discards it (`mapping, _ = assign(...)`).
This experiment keeps it. Nothing about the fingerprint, the reference, the
windows or the swap changes — the only change is that the number already
computed is retained and paired with whether the match was right.

Per cell (source × expert set × window) and per evaluated month after the swap:

- `distance` — the distance from the observed fingerprint to the nearest
  reference name, in the reference's coordinates
- `hit` — whether the chosen mapping equals the true permutation
- `ceiling` — the distance to the second-nearest name, so a margin can be formed
- `month_index` — position after the swap, so development and test can be split

The evaluated months after the swap are split **in half**: the first half is
development, the second half is test. A threshold is chosen on development and
measured on test. That split is the same discipline Investigation 16 applied to
alpha, and it is what makes H4 an ex ante test rather than a description.

## Registered hypotheses

**H1 — calibration.** The error rate rises monotonically across distance
quartiles. *Falsified* if the four quartile error rates are not monotone
increasing.

**H2 — rank power.** The distance separates wrong matches from right ones:
AUC, computed with wrong matches as the positive class, exceeds 0.5, and a
bootstrap 95 % interval (1 000 resamples, seed 20261125) excludes 0.5.
*Falsified* if the interval contains 0.5.

**H3 — the signal is not cell identity.** The effect survives centring the
distance within each cell (subtract that cell's mean distance). *Falsified* if
the within-cell AUC falls inside a bootstrap interval containing 0.5. This is
the hypothesis that matters most: if all the variation lies between cells, then
"self-doubt" is only "this cell is hard", which an operator cannot use on a
running system.

**H4 — abstention pays.** A threshold chosen on development months, applied to
test months, raises precision on the months it answers by more than the
development error rate would predict at the resulting coverage. *Falsified* if
the test precision at any development-chosen threshold is not above the
development error rate's complement, or if every threshold leaves less than 25 %
coverage.

**H5 — the held-out table transfers.** The ordinary in-operation distance is
the same order of magnitude as Investigation 18's held-out distance. *Falsified*
if the ordinary distance's median is below half the held-out median at the same
window, in the majority of valid cells. If it is falsified, then 018's table
describes a condition the operator never enters, and the sentence in the 018
findings was written without grounds.

## Controls that can void the whole run

- **C1 — no look-ahead.** Mutating the outcome of the current month must not
  change the distance. Measured as the worst residual over all cells; must be
  exactly `0.0`.
- **C2 — label permutation.** Randomly renaming the reference names (seed
  20261125) must drive the AUC toward 0.5. If a permuted reference still
  separates at AUC above 0.6, the measurement is reading something other than
  the match.
- **C3 — identity.** In the unshifted control the detector must return the
  identity mapping. A cell where it does not is not a measurement of detection.
- **C4 — reference stability.** Inherited from 18b unchanged. A cell whose
  reference cannot identify a name against itself is excluded, and the exclusion
  is counted and reported. It is a finding, not a nuisance.

If C1 or C2 fails, the verdict is `control_failed` and no hypothesis is
reported as held.

## What would make this worth the run

A **calibrated** distance — one where a large distance means a likely wrong
answer, and where that holds *within* a cell — would be the first quantity in
this series that lets a mechanism know it is uncertain without knowing the
outcome. That is the difference between a system that is wrong and a system that
can say it does not know.

A **flat** distance would be the more useful result to have written down: it
would mean the nearest-neighbour detector fails confidently by construction, and
that the held-out table in Investigation 18 measured a question nobody asks.

## Limits stated in advance

- The detector only recognises worlds it has already seen. A genuinely novel
  regime has no reference, and this experiment cannot create one.
- The evaluated months after the swap number 159 per cell, so the development
  and test halves are about 80 months each. A calibration curve over four
  quartiles therefore rests on roughly 20 months per bin per cell; pooling across
  cells is what gives it power, and pooling is also what H3 guards against.
- A window of 120 consumes most of the evaluated months before scoring begins.
  Cells whose scored months fall below 40 are excluded and counted.
