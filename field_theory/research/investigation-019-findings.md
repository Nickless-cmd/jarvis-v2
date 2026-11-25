# Investigation 19 — can the detector's distance be used as self-doubt?

Investigation 18 closed with a sentence that had not been measured: *the distance
is available, and it is a usable self-doubt signal.* It came from a table whose
per-cell sample is three experts and which compares two constructed conditions —
the reference with the true name present, and with it removed — that an operator
never chooses between. This investigation tests the operational question
instead.

**Protocol:** `experiments/exp_019_distance_as_doubt/protocol.md`, frozen and
committed alone as `3ec32e2f9` before the module existed. Declared **exploratory**
in its own first section, because the premise came from a sentence already
written rather than from a measurement.

---

## The short answer

The distance is **calibrated** and **weak**, and almost all of its apparent power
is a property of the cell rather than of the month.

| # | hypothesis | result |
|---|---|---|
| H1 | error rate rises monotonically with distance | **held** — 0.083 → 0.097 → 0.471 → 0.793 |
| H2 | distance separates wrong from right matches | **held** — AUC 0.857 [0.841, 0.871] |
| H3 | the signal survives centring within a cell | **held, weakly** — 0.591 [0.567, 0.617] |
| H4 | abstention chosen on development pays on test | **falsified** — 11 of 27 pass, and 7 cannot pass by construction |
| H5 | the held-out table transfers to ordinary operation | **falsified** — ratio 0.434 |

Verdict: `partial:4_abstention_pays,5_held_out_table_transfers`.

---

## The calibration is real

Pooled over 27 valid cells and 2 762 scored months, the error rate across distance
quartiles:

| quartile | months | error rate | distance range |
|---|---:|---:|---|
| Q1 | 690 | **0.083** | 0.253 – 1.266 |
| Q2 | 691 | **0.097** | 1.267 – 1.730 |
| Q3 | 690 | **0.471** | 1.733 – 3.032 |
| Q4 | 691 | **0.793** | 3.032 – 537.385 |

A large distance really does mean a likely wrong answer. The shape is not linear:
Q1 and Q2 are nearly identical, and almost all the movement happens above a
distance of about 1.7. That is what a threshold would look like — there is a
floor below which the distance carries no information, and a knee above it.

## But most of it is the cell, not the month

This is the finding that matters, and it is the reason H3 was registered first in
the protocol's own words: *if all the variation lies between cells, then
"self-doubt" is only "this cell is hard", which an operator cannot use on a
running system.*

Subtracting each cell's own mean distance and re-measuring:

| | AUC | interval |
|---|---:|---|
| pooled | **0.857** | [0.841, 0.871] |
| within cell | **0.591** | [0.567, 0.617] |

The interval still excludes 0.5, so the within-cell signal exists — H3 held. But
of the 0.357 of AUC above chance, only 0.091 survives centring. **About a quarter
of the measured power is per-month self-doubt; three quarters is the identity of
the cell.**

The honest reading: the detector can tell you *this world is one I am bad at*.
It can barely tell you *this particular month is one I am getting wrong*.

## Abstention does not pay reliably — and the protocol could not have shown that it did

H4 required that a threshold chosen on the development half raise precision on the
test half above the complement of the development error rate. It failed, and for
two separate reasons that are worth keeping apart.

**Seven of 27 cells could not pass.** Where the development months contain no
error, the registered bar is `1 - 0 = 1.0`, and nothing exceeds certainty. The
condition was unfalsifiable in those cells by construction — a flaw in the
protocol, not a result about the detector.

**Among the 15 cells where abstention could help, it still fails.** Eleven of 27
abstentions clear the protocol bar; 14 of 27 clear the *stricter* comparison
against the test baseline. The two that are genuinely strong are real:

| cell | threshold | development error | test precision | test baseline | coverage |
|---|---:|---:|---:|---:|---:|
| co2 / original / W=24 | 1.033 | 0.217 | **1.000** | 0.754 | 0.22 |
| co2 / original / W=36 | 1.134 | 0.206 | **1.000** | 0.667 | 0.21 |
| sunspots / two_experts / W=24 | 14.817 | 0.926 | **0.731** | 0.294 | 0.38 |

And one that misses by four thousandths: `sunspots/original/W=24` reaches 0.231
against a bar of 0.235.

So abstention works where a usable threshold exists and where development and
test resemble each other. It is not a property of the distance. This is the same
lesson Investigation 16 gave about alpha: **a rule chosen ex ante does not
automatically transfer.**

## The held-out table describes a condition the system never enters

| | median distance |
|---|---:|
| ordinary operation | **1.609** |
| held-out reference (18b's construction) | **3.709** |
| ratio | **0.434** |

The protocol set the falsification at "below half the held-out median in the
majority of valid cells". The pooled ratio is 0.434 — below half. Investigation
18's table is therefore not evidence about anything the detector does in
operation: it measures what happens when the right answer is deleted from the
pool, which is not a state the system can be in, since the reference is built
from the world it already knows.

This is why the sentence in the 018 findings is now retracted there, in place,
with a pointer to this file.

## Controls

- **C1 — no look-ahead.** The fingerprint reads `outcomes[i - lag]` for the
  trailing window, so the newest outcome it can see at month `n` is `n - 2`. The
  current month's outcome is never read. 18b's `no_look_ahead` control measured
  the worst residual at exactly `0.0` and is inherited unchanged.
- **C2 — scrambled reference.** Renaming the reference names at random collapses
  the AUC to **0.0399**. The control passes, but it is a *weak* null test and the
  reason is worth stating: scrambling makes **99.5 %** of matches wrong, so the
  positive class dominates and the AUC is pushed far below 0.5 rather than toward
  it. It proves the signal disappears; it does not prove the measurement is
  unbiased.
- **C3 — identity.** The unshifted control must return the identity mapping.
- **C4 — reference stability**, inherited from 18b: **27 cells valid, 13
  unstable**, and the 13 are counted rather than dropped silently. The unstable
  cells are the sunspot periodic ones, where lag 132 is nearly a full solar cycle
  and the experts are near-collinear.

## A measurement trap worth recording

The first reproducibility comparison between two runs reported five differences.
They were all `nan`: `nan != nan` is `True`, so five absent values compared as
disagreements. A nan-aware comparison found **0 real differences across 51 866
values**.

The lesson is the same one the rest of this series keeps teaching. A number that
looks like a discrepancy is usually a comparison with a well-known name.

## The control that changes the conclusion

C3 was registered in the protocol and then left unimplemented — ruff caught the
dead variable that was meant to feed it. Implemented, it measures whether the
reference, built from the shifted world, gives back the identity mapping on the
unshifted world. A cell where it cannot is not measuring detection, only
confusion.

**Only 11 of the 27 valid cells reach an identity rate of 0.9.** The other 16
are mostly sunspots, where the ~11-year cycle makes the lag fingerprint drift
even when nothing changes. And on those 11 the measurement does not just hold —
it sharpens:

| | registered (C4, 27 cells) | strict (C4 + C3, 11 cells) |
|---|---:|---:|
| pooled AUC | 0.857 | **0.923** |
| within-cell AUC | 0.591 | **0.958** |
| months | 2 762 | 882 |
| quartile error rates | 0.083 / 0.097 / 0.471 / 0.793 | 0.000 / 0.000 / 0.000 / 0.104 |

Within-cell power is now **higher** than pooled power. In the cells where the
detector can actually recognise a world it has seen, the signal is almost
entirely per-month: the detector is right on nearly every month, and the few
errors it makes are exactly the months with a large distance.

So the first reading of H3 — "three quarters of the power is cell identity" — is
true of the pooled set and misleading about the mechanism. The dilution is not
that the distance is inherently a property of the cell. It is that **16 defective
cells are averaged into the measurement**, and in a defective cell the detector
is wrong for reasons that have nothing to do with the current month.

The correct sentence is narrower and more useful: **in a cell where the detector
can recognise the world, the distance is a genuine per-month self-doubt signal,
and a strong one.** The pooled figure is what you get when you do not check
whether the detector works before you ask it how unsure it is.

## What this changes

The 018 finding said the failure mode was *a confident wrong answer*. That is
still true, and now it has a size and a condition. Where the reference is stable
and identity holds, a large distance means a likely wrong answer at AUC 0.958
within the cell. Where it does not hold, the distance is still informative but
the whole measurement is contaminated by a detector that cannot recognise the
world it is standing in.

A mechanism built on this could know **which regimes it is bad in** — that is
what C3 measures, and it is the gate that matters. Given a regime it can
recognise, it can also know **which month it is currently wrong about**, and that
second ability is stronger than the pooled numbers suggested.

The 018 claim was retracted because it rested on three experts and a constructed
condition. It turns out to have been closer to right than this investigation's
first reading of its own data — but only under a condition the 018 table never
checked: that the detector works.
