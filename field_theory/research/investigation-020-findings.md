# Investigation 20 — does the representation decide what can be recognised?

**Run:** `artifacts/exp_020_representation/run_v3/results.json` (26/11-2026, 16 min).
**Protocol:** frozen and committed alone as `127fff270`, before the module existed.
**Verdict:** `representation_matters`. All four registered hypotheses held.

---

## The question

Investigation 19 found that 29 of 40 cell-windows fail the C3 identity control, and
that the identity rate and the error rate are largely the same property measured
twice: *a cell where the fingerprint cannot tell the series apart is a cell where
the match is wrong.* It named the cause — the representation is not discriminative
— and never tested it.

There are two very different reasons a cell can fail:

- **The information is not in the data.** Then the detector has a hard ceiling and
  the honest report is a ceiling.
- **The information is there, but the representation does not express it.** Then
  the ceiling is a property of one design choice, and the same data carries better.

This experiment holds every input fixed and changes only the function that maps
data to a vector.

## The answer

| representation | C3 ≥ 0.9 | median C3 | median accuracy | dims |
|---|---:|---:|---:|---:|
| R0 baseline | 11/40 | 0.625 | 0.238 | 8 |
| **A1 first difference** | **21/40** | **0.994** | **0.976** | 8 |
| A2 rank | 11/40 | 0.537 | 0.284 | 8 |
| B1 full lag profile | 14/40 | 0.237 | 0.173 | 132 |
| B2 relational profile | 6/40 | 0.369 | 0.142 | 10 |
| **B3 shared component removed** | **21/40** | 0.972 | 0.964 | 8 |
| X1 irrelevant control | 0/40 | 0.047 | 0.000 | 132 |

**The ceiling was a property of the representation, not of the data.** A1 and B3
are linear transformations of exactly the same series; they add no observation.
Both nearly double the number of cells that clear the identity threshold.

Both rescue **10 cells that R0 fails and lose none**. The gain is a strict
superset, not a trade.

## Why it is not dimensionality

X1 is dimension-matched to B1: the same eight features plus 124 correlations
against a fixed pseudo-random series (seed 20261125), no information about the
world. It scores **0 of 40** — worse than the baseline.

So B1's 132 dimensions buy it 3 cells over R0 (14 vs 11) while destroying the
median (C3 0.237 against R0's 0.625). More coordinates made most cells *worse*.
X1 shows that adding dimensions without information produces nothing at all.

H2 therefore holds: the gain from A1 and B3 is information, not arithmetic room.

## What the two winners have in common

They look unrelated in the table and are the same move:

- **A1** replaces absolute levels with *changes* — it removes the level and keeps
  the movement.
- **B3** subtracts the cross-expert mean series — it removes what all experts
  share and keeps what separates them.

Both delete a component that is present in every series and therefore carries no
information about which series you are looking at. In sunspots the shared
component is the eleven-year cycle; it dominates the variance so completely that
eight absolute correlations describe the cycle and not the forecaster.

This is the answer to the question the protocol's own "worth the run" section
posed, and it is the second half of H3: **a strong relation between information
can make other existing relations less recognisable.** The common cycle is not
noise. It is information — about the world, not about the forecaster — and it was
sitting on top of the signal.

## What did not work, and why that matters

**B2 — relations between experts — is the worst representation in the run (6/40).**
Its relational profile does not help identify a series. That is a real answer to
the question GPT raised before the run: identity is *not* made easier to recognise
through the relations between components, at least not when the relation is
described without naming which component it points at.

And that qualification is the whole story of the amendment below. The first
version of B2 named the expert it described. It would have scored high — and the
score would have been the detector reading its own coordinate system.

## Controls

- **C0** — R0 reproduces Investigation 19's 11 of 40. The harness measures the
  same object.
- **C1 no-look-ahead** — 0.0 for all seven representations: no representation
  reads an outcome it would not have had.
- **C2 label permutation** — 0.0 for all representations except B3 (0.18).
  B3's 0.18 is *below* chance for three names (1/3), so it is not an identity
  leak: B3's residuals are similar enough that `assign` returns the same answer
  whatever the names are, and sometimes that answer is right. It is a weakness in
  B3's discrimination, and the reason B3's 21/40 should be read as "as good as
  A1" rather than "as trustworthy as A1". A1's own C2 is 0.0.
- **C6 multiset preserved** — the cyclic swap moves the same series around; it
  does not change the set.

## Amendments made after the protocol was frozen

### A1 — B2 may not name the expert it describes

The protocol's B2 adds, for each expert, its correlation to every other expert
*under that expert's own name* (`pair_<expert>`), with the self-pair set to the
constant 1.0. The first draft did that and claimed in a comment that the constant
"z-scores to zero and therefore adds nothing".

Measured, that claim is false. After the z-scoring that `feature_stats` and
`apply_stats` apply, the self-pair becomes a near one-hot identity code:

| feature | previous_month | trailing_12_mean | cycle_lag_132 |
|---|---:|---:|---:|
| `pair_previous_month` | **+1.39** | −0.92 | −0.47 |
| `pair_trailing_12_mean` | −0.84 | **+1.41** | −0.57 |
| `pair_cycle_lag_132` | −0.61 | −0.80 | **+1.41** |

Each expert carries +1.4 at its own position. Spread 2.21–2.31 against ~2.0 for
the lag features, and `assign` weights every feature equally — so the detector can
read the identity off the coordinate system instead of off the series. That is
precisely the artefact C5 exists to catch, arriving through B2 itself.

**Amended:** B2 now carries a *sorted* relational profile, `rel_1 … rel_{n-1}`,
where `rel_1` is the strongest relation this series has to any other series,
whoever that is. The relation is kept; the self-reference is gone.

Consequence: B2 no longer answers "which expert is this related to" — only "how
strong are my relations, ranked". That is narrower than the protocol asked, and
it is the only version that can be answered without handing the detector the
answer.

### A2 — a representation that is not name-symmetric must fail loudly

`_features_of` read the first expert's keys and returned them. When another
expert carried a different set, the failure surfaced as a `KeyError` three frames
deeper with no indication of which representation was at fault. It cost the first
full run (25/11-2026, 21:13Z).

**Amended:** `_features_of` compares every expert's key set to the first and
raises `ValueError` naming the asymmetry.

## Limits

- Six real representations are compared with no multiple-comparison correction.
  H3 named a winner in advance (B3, the shared-component mechanism), and it did
  win — that is what keeps this from being a fishing trip. But A1 tying it was not
  predicted by name.
- Dimensionality varies from 8 to 132. Euclidean distance grows with dimension, so
  B1 and X1 cannot be read against R0 as "more history" alone. That is exactly why
  X1 exists, and it settles the question empirically rather than by argument.
- The C3 threshold of 0.9 is inherited from 18b, not calibrated. Cells at 0.89 and
  0.91 are not meaningfully different; the median is reported alongside the count
  for that reason.
- This experiment cannot create a novel regime. It can only ask whether worlds
  already in the reference are separable.
- A1 and B3 are both *differences*. The result therefore cannot separate "remove
  the common component" from "look at change rather than level" — they may be the
  same insight wearing two names, and this run does not tell them apart.

## The sentence that follows

The detector was never blind. It was looking at the wrong thing — and the thing
it was looking at was the one component that every series shares, which is the
one component that cannot tell them apart.
