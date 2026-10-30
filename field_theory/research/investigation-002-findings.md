# Investigation 2: findings

**Status:** completed exploratory run with local independent confirmation,
2026-10-30. This report interprets the preserved run at
`artifacts/exp_002/seed_202610302`; generated output remains the measurement
record.

## What was investigated

The analyzer searched 52 declared perspectives for each of five opaque binary
sources: individual variables, joint pairs, XOR transformations of two to four
variables, and outcome lags 1–12. Candidate selection used 1,024 discovery
observations. The selected candidate was then held fixed and measured on 2,048
independently generated confirmation observations.

Outcome permutations supplied two different comparisons. The discovery
comparison retained the largest score across all 52 perspectives on each
permutation, representing the search itself. The confirmation comparison used
only the already selected candidate. Neither comparison is treated as a
universal significance threshold.

The procedure was blind only in a limited, operational sense. The analyzer did
not import the generators or read the source key, and results were written
before reveal. The code author nevertheless designed both source and candidate
families and could inspect their code.

## Measurements before source reveal

| Opaque source | Selected perspective | Discovery MI | Search-null q95 | Confirmation MI | Confirmation-null q95 |
|---|---|---:|---:|---:|---:|
| S-05E2 | `joint(v0,context)` | 0.476542 | 0.009380 | 0.467335 | 0.003268 |
| S-11B3 | `xor(v0,v2,v3)` | 0.003250 | 0.009162 | 0.000100 | 0.001211 |
| S-197C | `joint(v2,context)` | 0.584464 | 0.008910 | 0.000991 | 0.002819 |
| S-B4E5 | `xor(v0,v1,v2)` | 0.411795 | 0.008985 | 0.379161 | 0.001548 |
| S-D592 | `xor(v0,v2,v3)` | 0.010503 | 0.008970 | 0.000018 | 0.001266 |

The table is intentionally readable without knowing source meanings. Two
selected relations remained large on confirmation, one large discovery result
collapsed, and two small selections did not persist.

## Findings after reveal

### Structure that persisted

S-05E2 was the noisy contextual XOR source. The selected four-state joint
representation and the simpler XOR transformation were nearly tied on
discovery (a difference of 0.000064 bits). The selected representation retained
0.467335 bits on confirmation, with no permutation among 250 reaching it.

S-B4E5 was the noisy three-variable XOR source. Its exact higher-order
transformation was selected at 0.411795 bits and retained 0.379161 bits on
confirmation. No confirmation permutation among 250 reached the observed
score. Pairwise and single-variable views were insufficient to represent this
parity relation; the catalog's higher-order perspective mattered.

These results show persistent detectable structure under specified
representations. Because both structures were generated, they validate the
discovery-and-confirmation procedure only within this source family.

### Structure that was real in one partition but did not persist

S-197C contained a noisy relation to `v2` in discovery and an independent
outcome in confirmation. The search found 0.584464 bits, far beyond its
search-wide permutation values, but the fixed perspective produced only
0.000991 bits on confirmation; 104 of 250 confirmation permutations were at
least as large.

The discovery measurement was not fabricated: the relation existed in those
records. What failed was the broader expectation of continuity across the
source's partitions. “Detected structure” and “stable source property” are
therefore separate claims.

### Search-created candidates

S-11B3 was fully independent pseudorandom data. Its best candidate measured
0.003250 bits. In 221 of 250 search-wide permutations, the best searched
candidate was at least that large. Its confirmation score was 0.000100 bits.
Searching produced a named pattern, but the search-aware baseline already made
it unremarkable.

S-D592 was deterministic SHA-256-derived data whose generating input was
unavailable to the analyzer. Its best discovery candidate measured 0.010503
bits; only 4 of 250 search-wide permutations reached that value. This was the
most instructive surprise: even after calibrating the 52-candidate search, an
apparently unusual relation occurred. On confirmation it fell to 0.000018 bits,
and 205 of 250 candidate-specific permutations were at least as large.

Thus a low search-calibrated rank fraction was not enough to establish a
persistent relationship. Independent examination changed the interpretation.
The underlying generator was deterministic throughout, yet none of the
available perspectives revealed its actual generating structure.

## What the search itself contributed

Maximizing uncorrected mutual information favored richer joint states when
scores were close. For S-05E2, `joint(v0,context)` narrowly outranked the
simpler and generator-matching `xor(v0,context)`. For S-197C, four joint
representations containing `v2` narrowly outranked `value(v2)`, although the
extra variable was not part of the planted discovery relation.

The search-wide null accounts for the opportunity to obtain a large score, but
it does not choose the simplest explanation. Future candidate comparison could
record predictive compression, complexity penalties, or nested-model
differences. Adding such a rule after seeing this run would be exploratory; a
later confirmatory use would need to record it in advance.

## Field Theory distinctions

**Information:** The raw records remained unchanged while access and
representation changed. Generator determinism did not imply accessible
structure.

**Perspective:** XOR and joint representations exposed relations invisible to
individual-variable views. Conversely, a flexible perspective search created
plausible but nonpersistent candidates.

**Relations:** The three-variable parity result depended on interaction among
values rather than any one value. The partition-specific source showed that a
relation can be present without being continuous.

**Expectation:** Discovery created a narrow expectation that a selected
relation would recur. Confirmation supported that expectation for two sources
and contradicted it for three. This is predictive evidence, not subjective
experience.

**Time:** Outcome lags were available, but no lag was the persistent selected
relation. This run neither supports nor rules out time-like structure. Order
was only one candidate representation and explicit partition roles remained.

## What remains unknown

- How should representation complexity be compared without building a favored
  answer into the selection rule?
- Which conclusions survive source families not designed alongside the
  analyzer?
- Can candidate relations be proposed by a genuinely blinded researcher or a
  held-out transformation generator?
- How should nonstationary sources be distinguished from accidental sample
  differences without assuming stationarity as ground truth?
- Which null model is appropriate when sequence dependence or changing regimes
  makes unrestricted outcome permutation implausible?
- Can relational continuity be measured without treating chronological split
  membership as the definition of continuity?

No broader Field Theory proposition is validated or falsified by this run.
The principal empirical lesson is narrower: discovery is partly a property of
the records and partly a property of the searched perspectives, and only new
observations distinguished persistent relations from several compelling local
ones.
