# Experiment 020 protocol — can a different representation separate what the data already contains?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.
This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering.

## The question, and why it is the right next question

Investigation 19 ended with a sentence that was itself a finding:

> **29 of 40 cell-windows fall below the C3 threshold**, and 28 of those 29 also
> have a high error rate (0.26 to 1.00). […] identity rate and error rate are not
> two independent properties of a cell that happen to correlate; they are largely
> **the same property measured twice**. […] That makes "defective" the wrong
> word. Nothing is broken; the representation is simply not discriminative for
> that data.

That paragraph names a cause and does not test it. It says the fingerprint
*cannot* separate the series. There are two very different reasons why it might
not:

1. **The information is not in the data.** The series really are
   indistinguishable at the resolution measured, and no representation would
   help.
2. **The information is in the data, but the representation does not express
   it.** The series differ in a way the fingerprint averages away.

These two have opposite consequences. Under (1), the detector has a hard ceiling
and the correct response is to report it. Under (2), the ceiling is an artefact
of one design choice, and the same data supports a better one — which is the
field-theory premise stated in its most testable form: **recognition depends on
the representation, not only on the information.**

This experiment separates (1) from (2) by holding the data fixed and changing
only the function that maps data to a vector.

## What is held fixed

Everything except the fingerprint:

- the two sources (`silso` monthly sunspot totals, `noaa` monthly CO₂)
- the five expert sets and the ten resulting cells
- the four windows (24, 36, 60, 120)
- the cyclic swap at the midpoint of the evaluated months, and
  `prepare_swapped` unchanged
- `feature_stats`, `apply_stats`, `assign` and the Euclidean distance in
  reference coordinates — unchanged
- the C3 control, exactly as registered in `exp_018b`

`experiment_018b_lag_fingerprint` is **not modified**. This experiment imports
its building blocks and supplies its own fingerprint function. That keeps the
baseline reproducible by construction rather than by care.

## The representations under test

Each is a function `(real_rows, outcomes, experts, window) -> {expert: {feature: float}}`
computed from **the same two inputs**: the prediction streams and the outcome
series. No new data is collected, no month is added, and every representation is
evaluated with the same control that rejected the original fingerprint.

They are grouped by how much they are allowed to change.

### Level A — transformations that preserve the information

**A1 — first difference.** Correlate the *change* in a prediction against the
*change* in the outcome at each of the original eight lags. `Δx[i] = x[i] − x[i−1]`
is invertible given one starting value, so the series carries the same
information; what changes is that a shared level or trend no longer dominates the
correlation.

**A2 — rank correlation.** Spearman instead of Pearson at the same eight lags.
This one is weaker than A1 and is declared so: ranks discard magnitude, so it
holds *less* information than the baseline, not the same. It is included because
it isolates one specific failure — sensitivity to a few extreme months — and
because a representation that helps while holding less information is evidence
that the discarded part was noise.

### Level B — functions of the same data that expose relations the baseline ignores

**B1 — full lag profile.** All 132 lags instead of the eight selected ones. No
new data; the baseline's choice of eight was itself a compression.

**B2 — pairwise structure.** The eight baseline features **plus**, for each
expert, the correlation of its prediction stream against every other expert's
prediction stream. This exposes the cluster structure directly: two series that
are near-copies of each other are declared near-copies instead of being inferred
from matching fingerprints.

**B3 — shared component removed.** Subtract the cross-expert mean series from
each expert's series before correlating, then use the same eight lags. In a
periodic world the common cycle is exactly the component that makes every
fingerprint look alike; removing it leaves what distinguishes them. This is a
linear transformation of the same series.

### A control representation that must NOT help

**X1 — irrelevant dimensions.** The baseline's eight features plus 124
correlations computed against a fixed pseudo-random series (seed 20261125). This
adds dimensions without adding information about the world. It exists to catch
the artefact described under C5.

## Registered hypotheses

**H1 — representation matters.** At least one of A1, A2, B1, B2, B3 lifts more
cells above the C3 identity threshold of 0.9 than the baseline's **11 of 40**.
*Falsified* if no representation reaches 12 or more.

**H2 — the gain is information, not dimensionality.** The best representation
must beat X1, its own dimension-matched control, on the same count. *Falsified*
if X1 reaches the same count as the best real representation.

**H3 — the mechanism is the shared component.** The prediction registered before
any measurement: **A1 and B3 will outperform B1**. The reasoning is that the
failure is a shared low-frequency structure, and both A1 and B3 remove it while
B1 only adds more of the same kind of feature. *Falsified* if B1 reaches a higher
count than both A1 and B3.

**H4 — the rescued cells are real.** In the cells that newly pass C3 under the
best representation, the accuracy after the swap must be at least as high as in
the baseline cells that already passed. *Falsified* if the newly passing cells
have a materially lower accuracy — that would mean the threshold was crossed
without the detector improving, i.e. the control was satisfied by accident.

## Controls that can void the whole run

- **C0 — reproduction.** The baseline representation R0 must reproduce
  Investigation 19's count exactly: **11 of 40** cells at or above 0.9. A
  different number means this harness measures a different object than the one it
  claims to extend, and no hypothesis may be reported.
- **C1 — no look-ahead, per representation.** Mutating every outcome at and after
  a probe month must not change the answer at that month, for each representation
  separately. A1 is the one that needs this most, since differencing changes which
  outcome values are read. The worst residual must be exactly `0.0`.
- **C2 — label permutation.** Randomly renaming the reference names (seed
  20261125) must collapse the detection accuracy toward chance for the best
  representation. If it does not, that representation is reading something other
  than the match.
- **C3 — identity.** The registered control, unchanged, and the primary outcome
  measure. It is deliberately **not** redefined here: a threshold chosen by this
  experiment could be tuned, and this one was fixed in `exp_018b` before the
  question was asked.
- **C4 — reference stability.** Inherited unchanged. Unstable cells are counted
  and reported, not dropped silently.
- **C5 — the dimension artefact.** Adding features can raise the identity rate
  with no information at all, because a higher-dimensional space separates
  nearest neighbours more easily. X1 measures exactly that. **If X1 helps as much
  as the best real representation, H1's result is void** and the verdict is
  `dimension_artefact`, not `representation_matters`.
- **C6 — the swap preserves the multiset.** The cyclic permutation must not
  change the set of series in a cell. Inherited from `prepare_swapped`; verified
  once here because B2 and B3 read across experts.

If C0, C1 or C6 fails, the verdict is `control_failed` and no hypothesis is
reported as held.

## What would make this worth the run

**If a representation rescues the failing cells** and survives C5, then the
ceiling Investigation 19 found was a property of one fingerprint and not of the
data. The sentence that follows is uncomfortable and useful: the detector was
never blind, it was looking at the wrong thing — and the same will be true
somewhere in Centralen.

**If nothing rescues them**, that is the more valuable result to have written
down. It would mean the information genuinely is not there, that Investigation
19's "representation, not damage" reading was itself too generous, and that the
honest report is a ceiling rather than a repair. It would also falsify the
field-theory premise in the one place where it was finally measurable.

## Limits stated in advance

- Six representations are compared. That is six chances to beat a baseline by
  luck, and no correction is applied; the registered prediction in H3 is what
  keeps this from being a fishing trip, because it names a winner in advance and
  can be wrong.
- A2 holds less information than the baseline by construction, so a null result
  there is not evidence about representation in general.
- B1's 132 features are correlated with each other by construction (adjacent
  lags), so the Euclidean distance in that space is not a metric with an
  interpretation. B1 is included to be beaten, not to be trusted.
- The C3 threshold of 0.9 is a convention inherited from 18b, not a calibrated
  boundary. A cell at 0.89 and a cell at 0.91 are not meaningfully different, and
  the count is reported alongside the full distribution for that reason.
- This experiment cannot create a novel regime. It can only ask whether the
  worlds already in the reference are separable.
