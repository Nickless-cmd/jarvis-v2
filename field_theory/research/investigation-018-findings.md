# Investigation 18 — can a regime shift be detected before the outcome?

**Verdict:** yes, in the world where the experts are distinguishable — and the
detector's false-alarm rate is exactly its own error rate, so a detection and a
mistake look identical from the inside.

Two experiments are reported. The **registered** one (18) failed its own control
and says nothing about detection. The **exploratory** repair (18b) answers the
question, and its evidence is weaker because it was written after seeing the
registered run fail.

---

## A correction to Investigation 17, found on the way

Investigation 17 placed its regime shift at `swap_at = len(rows)//2`, which is
**1893-04** — inside the development period. Evaluation starts at **2000-01**,
**1281 months later**.

The memory of the pre-shift world at evaluation start is `0.99^1281 = 2.6e-6`.
At retention 0.9 and 0.99 the heaviest weight already sits on the structurally
best expert in the first evaluated month (`w = 0.448` and `0.978`).

So Investigation 17's headline delay of **6.0 / 8.5 / 126.0 months is not
adaptation delay from the shift**. It is the time, a century after the world
changed, for the weight to land on the new best expert. The number is real; the
name it was given is wrong.

Placing the same shift at the evaluation midpoint instead — 2013-04, 159 months
on each side — gives delays **2 / 24 / 150** and accumulated excess loss
**13.9 / 55.0 / 395.2**. That is a far cleaner and far more expensive picture,
and it is the placement this experiment uses.

This was measured by `/tmp/probe_018_diag.py` before the protocol was written,
and is declared in the protocol for that reason.

---

## The structural boundary, proved exactly

The shift is a **permutation of the prediction columns**. The multiset of series
in a cell is unchanged; only which name holds which series changes.

Therefore every statistic symmetric in the expert names is **exactly invariant**.
Measured over all months and all cells: the maximum absolute difference between
the shifted and the control run for the sorted prediction vector, its mean, its
spread and its mean absolute deviation is **0.0** — not small, zero.

That is H1, and it held. It means the class of detectors that can work is
severely restricted: the mechanism cannot notice a regime shift by looking at how
disagreed its experts are, how concentrated its weights are, or how spread out
their predictions are. All of that is unchanged by a change of ownership.

Only a **name-aware** statistic can see the shift.

---

## The registered detector failed its own control

The registered fingerprint used three shape features: jaggedness, lag-1
autocorrelation, and the share of repeated values.

Its control C4 asks whether the reference can identify a name **against itself**,
by fingerprinting two disjoint halves of the pre-shift history and matching them.
It could not, in **34 of 40** cells. The control-run identity rate is ~**0.10**.

Two reasons, and both are informative rather than accidental:

1. `f_tie` is zero in almost every window — a dead feature contributing noise.
2. The experts within a set are near-duplicates. `trailing_3_mean`,
   `trailing_6_mean`, `trailing_12_mean` and `trailing_24_mean` are all smooth
   averages of the same series. A shape fingerprint cannot tell them apart.

**This is the failure mode the control exists to prevent.** Reporting "detection
is impossible" from this run would have reported a feature-design failure as a
property of the world. It is reported instead as what it is: a failed detector.

One exception in the registered run, worth keeping: the `two_experts` set, whose
two series are maximally different (noisy `previous_month` against smooth
`trailing_12_mean`), reached accuracy **0.960** at W=36 with a control identity
rate of **0.918**. So even the weak fingerprint worked exactly where the series
were distinguishable — a hint the repair would confirm.

---

## The repair: a fingerprint of lag structure

An expert is *defined* by its lag structure. `previous_month` is the observation
one month back; `trailing_12_mean` is a flat average over lags 1–12;
`cycle_lag_132` is the observation 132 months back. Correlating each name's
prediction stream against the observation series at lags
`1, 2, 3, 6, 12, 24, 66, 132` recovers that structure directly.

The measured signatures are clean:

| expert | lag 1 | lag 12 | lag 132 |
|---|---:|---:|---:|
| `previous_month` | 1.000 | 0.691 | 0.510 |
| `trailing_12_mean` | 0.870 | 0.909 | 0.355 |
| `cycle_lag_132` | 0.510 | 0.156 | 1.000 |

**This stays ex ante.** Detecting a shift at month `t` uses predictions at `t`
and outcomes **strictly below** `t`. Control C1′ mutates every outcome at and
after a probe month and requires the answer at that month to be unchanged:
measured residual **0.0**.

---

## The answer

The best cell — CO2, the `short_memory` expert set:

| window | accuracy | control identity | detection delay |
|---|---:|---:|---:|
| 24 months | **1.000** | **1.000** | **10** |
| 36 | 1.000 | 1.000 | 18 |
| 60 | 1.000 | 1.000 | 30 |
| 120 | 1.000 | 1.000 | 69 |

A regime shift is detected **ten months after it happens**, with no outcome from
the shifted world used, and with no false alarm in the unshifted control. For
comparison, the memory cost of not detecting it runs to **150 months** of
adaptation at retention 0.99.

The delay is roughly half the window: the trailing window must be dominated by
the new world before the identification is reliable. That is the price, and it is
linear and predictable.

---

## The warning: a detection and a mistake are the same number

Look at accuracy and control identity across every valid cell:

| cell | window | accuracy | control identity |
|---|---:|---:|---:|
| co2 / original | 24 | 0.768 | 0.764 |
| co2 / original | 36 | 0.730 | 0.758 |
| co2 / original | 60 | 0.912 | 0.944 |
| co2 / long_memory | 24 | 0.768 | 0.789 |
| co2 / two_experts | 24 | 0.746 | 0.745 |
| co2 / two_experts | 36 | 0.627 | 0.646 |
| co2 / four_experts | 24 | 0.877 | 0.876 |
| co2 / four_experts | 36 | 0.810 | 0.839 |

They are the same number in every cell.

The detector does not sense that the world changed. It **identifies which series
each name currently carries**, and reports a change when that identification
differs from the one it remembers. So its success rate at finding a real shift
and its false-alarm rate on an unchanged world are **the same measurement**.

A detector that is 77 % accurate will report a regime shift 23 % of the time when
nothing has changed — and it cannot tell the two cases apart, because the outcome
that would distinguish them is precisely what it does not have.

This is the operational answer to the question, and it is narrower than it looks:
**detection is not knowledge. It is identification with a known error rate.**

---

## Where it fails, and why the failure is interpretable

Sunspots: **12 of 20** window-cells were rejected by C4, and the 8 that survived
reached accuracy **0.000–0.210** — at or below chance for a 3-permutation (0.167).

The reason is in the data, not the method. The sunspot series is periodic with an
~11-year cycle, and lag 132 is almost exactly one full cycle. Every expert
therefore correlates with the outcome at lag 132 in the same way, and the
signatures collapse onto each other:

| expert | lag 66 | lag 132 |
|---|---:|---:|
| `previous_month` | −0.468 | 0.510 |
| `trailing_12_mean` | −0.318 | 0.355 |
| `cycle_lag_132` | −0.849 | 1.000 |

Compare CO2, which is a smooth monotone trend: its experts stay distinguishable
at every window and the detector reaches accuracy 1.000.

So the boundary is: **detection works in a world whose statistical character is
stable, and fails in a periodic world where the experts are near-collinear.**

---

## The detector can know that it does not know

H5 held at every window. With the true match removed from the reference set, the
distance to the nearest available reference is systematically larger than the
distance to the true match:

| window | held-out distance | true-match distance | ratio |
|---|---:|---:|---:|
| 24 | 4.15 | 3.31 | 1.25 |
| 36 | 3.70 | 2.27 | 1.63 |
| 60 | 3.41 | 2.01 | 1.69 |
| 120 | 3.40 | 1.88 | 1.81 |

The separation grows with the window. A nearest-neighbour rule always returns an
answer, so the failure mode is a confident wrong answer — but the distance is
available, and it is a usable self-doubt signal.

This is the closest the data can come to the limit stated in the protocol: the
detector recognises a world it has **already seen**. It does not discover a new
one. Under a genuinely novel regime the correct reference is absent, the nearest
neighbour is wrong, and only the distance says so.

---

## What held and what fell

| # | hypothesis | result |
|---|---|---|
| H1 | name-symmetric statistics have exactly zero power | **held** — residual `0.0` |
| H2 | fingerprint recovers the permutation, accuracy ≥ 0.9 | **held** — 1.000 at W=120; 0.912 at W=60 |
| H3 | shorter window detects sooner and identifies worse | **fell** as measured; the aggregate compares different valid-cell sets per window |
| H4 | control run returns the identity | **held at W ≥ 60** (0.944, 1.000); fell at W = 24, 36 (0.745, 0.839) |
| H5 | held-out match falls to chance, distance separates | **held** — ratio 1.25 → 1.81 |

H3's failure is a flaw in my aggregation, not a fact about the world. The valid
cell set differs per window, so medians across windows are not comparable. The
within-cell frontier — co2 / `short_memory` — is clean and monotone: delay
10 → 18 → 30 → 69 with accuracy constant at 1.000.

H4's failure at short windows is the same finding as the accuracy table: at 24
and 36 months the detector is not reliable enough to distinguish a shift from its
own noise, and that is precisely the warning above.

---

## Limits

1. **Recognition, not discovery.** The detector works because the new world is
   one whose series it has already seen. A regime shift to something genuinely
   new has no reference, and the only teacher left is the outcome.
2. **Validity is conditional.** 13 of 40 cells were rejected by C4 — 12 of them
   sunspots. The answer is a statement about worlds whose statistical character
   is stable, not about all worlds.
3. **Exploratory.** The lag features were chosen after the registered detector
   failed. The choice was principled, but the timing makes this weaker evidence
   than a pre-registered confirmation would be.
4. **One mechanism.** Detection was measured against the memory knob it is meant
   to protect. It has not been wired into anything, and the 10-month delay is a
   property of this data, not a promise about a running system.

---

*Tallet der ligner et svar, er som regel et andet tal med et velkendt navn.*
Here the detection rate and the false-alarm rate turned out to be the same
number. The evening's motto held one more time, at the last layer.
