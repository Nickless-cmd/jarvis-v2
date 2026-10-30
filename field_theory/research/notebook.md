# Living research notebook

This is a chronological record. Entries distinguish **observation** (what a
method returned), **interpretation** (a proposed meaning), **limitation**, and
**question**. Earlier entries are amended by dated notes, not silently rewritten.

## 2026-10-30 — Scope correction: measurements must be live

Bjørn clarified after the first two runs that both investigations' substantive
measurements must occur on the deployed Jarvis system and its live database.
The existing experiment 001 and Investigation 2 values are therefore
reclassified as **synthetic method-validation results**. They remain preserved
for research history and software verification but are not evidence about the
live system. New live protocols require execution on CT105 after deployment,
read-only SQLite access, a recorded database high-water mark, and explicit
exclusion of conversational text and user identifiers.

**First deployed extraction attempt:** revision `b13ca76e2` reached CT105 and
opened the production database read-only, but stopped before producing a
manifest or measurements because 365 of 25,000 live rows lacked `started_at`.
All 365 had `finished_at`. Extraction version 2 therefore uses `finished_at` as
an explicit fallback and records the timestamp basis per row. The partial
`/tmp` output is not a valid run and no number from it is reported as evidence.

## 2026-10-30 — Project initiation

### Prompt and assumptions

- The project begins from Bjørn's propositions, not from a settled theory.
- “Field”, “perspective”, “experience”, “continuity”, “identity”, and “time”
  currently have multiple possible meanings.
- A small repository-local project can be operationally independent from
  Jarvis while avoiding premature infrastructure. This placement can be
  revisited if independent release or governance becomes useful.
- Locally generated pseudorandom data are suitable for validating a workflow,
  but not evidence about physical randomness or natural phenomena.

### Open questions

- What does “the field is constant while expanding” preserve, and what grows?
- What are Bjørn's three experiences of “now”, stated without translating them
  into conventional tense categories?
- Which definition of information is intended in each proposition?
- When is a perspective more than a data-access or feature transformation?
- What observable change would distinguish experience from learning?
- Which kinds of continuity are candidates for identity, and who supplies the
  equivalence criterion?
- Can a useful relational ordering avoid merely hiding clock time in its edges?

### Method decision

Experiment 001 will compare three access perspectives on identical records
from a constructed context-dependent source and an independent control. The
method and limitations are recorded in the protocol before the committed run.
No fixed pass/fail threshold is defined. Permuted outcomes provide descriptive
null distributions rather than a universal significance rule.

### Potential confounders recorded before the run

- finite-sample mutual-information bias, especially with more context states;
- accidental imbalance in cues, contexts, or outcomes;
- dependence on Python's pseudorandom generator and seed;
- the context variable and correct relation are supplied by the generator, not
  discovered from an unrestricted space;
- adjacent records are ordered, so lag dependence may reflect construction;
- repeated inspection could turn later use of this dataset into confirmation
  in name only.

### Observations and unexpected results

The preserved reference run is `artifacts/exp_001/seed_20261030`; its raw file
contains 4,096 rows and has SHA-256 digest
`c2:27:42:7e:a5:95:a2:29:83:df:3c:cd:50:a7:3d:6e:3b:27:c3:44:11:aa:29:eb:24:d7:52:2c:1e:01:07:b8`
(colon-separated hexadecimal bytes).

**Observation:** Both sources had near-balanced outcomes: the outcome-one
fractions were 0.513672 for `iid_control` and 0.520996 for
`context_relation`. Their binary outcome entropies were respectively 0.999461
and 0.998728 bits.

**Observation:** In `iid_control`, observed mutual information was 0.000053
bits for adjacent outcomes, 0.000072 bits with cue access, and 0.000124 bits
with cue-plus-context access. Each value fell within or below the central range
of 500 outcome permutations. The fractions of permuted values at least as
large as observed were 0.700, 0.632, and 0.946.

**Observation:** In `context_relation`, adjacent-outcome and cue-only mutual
information remained near zero (0.000004 and 0.000059 bits). With cue and
context accessible, mutual information was 0.515753 bits. None of the 500
permuted measurements was as large; their observed range ended at 0.006230
bits. “None of 500” is a finite resolution statement, not a probability of
zero.

**Interpretation:** The instrument recovered the relation deliberately encoded
by the generator only when the analysis could use the contextual distinction.
Aggregate outcome balance and cue-only association concealed that relation.
The independent control did not show a comparable departure from its
permutation distributions in this run. This supports the runner's narrow use
as a perspective/access demonstration; it is not evidence that unknown natural
randomness contains analogous structure.

**Potentially informative detail:** The cue-plus-context estimator had a
higher null median than the lower-dimensional estimators (about 0.00085–0.00090
bits versus about 0.00015–0.00019). That is consistent with finite-sample bias
when more joint states are available and demonstrates why raw metric magnitude
should not be compared across perspectives without a suitable baseline.

**Unexpected result:** No result contradicted the known construction. That is
useful for instrument validation but means this run generated no unexpected
substantive pattern. The first genuinely exploratory use should not reuse these
same records as independent confirming evidence.

### Method and implementation changes

- Before data collection, the import package was renamed from `field_theory`
  to `feltteori_research` after a test exposed a namespace collision with the
  project directory. This was an implementation correction; the protocol,
  generator, measurements, and reference-run parameters did not change.
- Before commit, the raw SHA-256 digest was changed from contiguous to
  colon-separated hexadecimal serialization after the secret-scanning hook
  correctly challenged an opaque high-entropy string. The digest and raw
  observations did not change; only their textual representation did.
- The generated linear-scale visualization makes the 0.515753-bit contextual
  value clear but visually compresses millibit-scale null ranges. Exact ranges
  remain available in the table and complete permutation file. A later
  visualization may add a documented logarithmic or inset view without
  replacing this artifact.

### Unresolved ideas

- A later blinded mixture could record the complete path of exploratory views.
- A useful experience/learning experiment may need outcomes other than
  predictive accuracy, such as persistent representational change.
- Null models themselves encode perspective and assumptions; they should be
  treated as methods with provenance, not neutral reality.

## 2026-10-30 — Investigation 2: unknown structure

### Prompt

Move from recovering a known context relation to selecting candidate
relationships without generator-revealing labels, while measuring what the
search itself contributes and testing selected candidates on independent data.

### Method recorded before the run

- Five sources were assigned opaque identifiers.
- The automated analyzer could access only preserved observations and the
  generation manifest, not `source_key.json` or generator code through imports.
- It searched 52 declared perspectives: five single variables, ten joint
  pairs, 25 XOR subsets, and twelve sequence lags.
- The maximum discovery mutual information selected one candidate per source.
- A 250-permutation maximum-over-search null represented selection opportunity.
- The selected candidate was frozen and measured on a separately generated
  confirmation partition with its own 250-permutation null.
- This is procedural, not genuine investigator blinding: the code author knew
  the families used on both sides.

### Preserved observations

The reference bundle is `artifacts/exp_002/seed_202610302`. It contains 15,360
raw rows: 1,024 discovery and 2,048 confirmation rows for each of five sources.
The raw SHA-256 digest is
`c7:ec:38:26:6a:44:5a:f1:6d:3d:11:f2:78:6b:b2:07:72:c2:76:c8:c1:8f:bb:f6:0f:6d:91:ed:83:32:67:6d`.

**Observation:** Two selected relationships persisted. The contextual source's
selected representation measured 0.476542 bits in discovery and 0.467335 bits
in confirmation. The three-variable parity source measured 0.411795 and
0.379161 bits. Neither confirmation score was reached by 250 permutations.

**Observation:** A partition-specific relation measured 0.584464 bits during
discovery but only 0.000991 bits in confirmation; 104/250 confirmation
permutations were at least as large. The relation existed locally but did not
support continuity across the new partition.

**Observation:** The independent source's best searched candidate was not
unusual even during discovery: 221/250 search-wide permutation maxima were at
least as large. It fell from 0.003250 to 0.000100 bits on confirmation.

**Unexpected observation:** The deterministic digest source produced a best
discovery candidate of 0.010503 bits. Only 4/250 search-wide permutations were
at least as large, so search calibration alone made it look unusual. The fixed
candidate fell to 0.000018 bits on confirmation, where 205/250 permutations
were at least as large. A rare search result survived the multiple-perspective
comparison but not new data.

### Interpretation

The catalog discovered two persistent planted relationships, including a
higher-order parity relation. It also named patterns in independent and
deterministic-but-inaccessible data. Independent confirmation, not the most
interesting discovery score, separated these outcomes in this run.

Determinism and observable structure were not equivalent: the digest source
was fully deterministic but its actual generating relation was outside the
available perspective. Conversely, the partition-specific source contained
strong observable structure that was not continuous.

### Search-induced method finding

Raw mutual-information maximization favored richer joint representations. In
the contextual source, `joint(v0,context)` exceeded the simpler
`xor(v0,context)` by only 0.000064 bits. In the partition-specific source, four
joint representations containing `v2` narrowly exceeded `value(v2)`, even
though their extra variables were not part of the planted relation. Search-wide
permutations calibrate magnitude but do not supply explanatory simplicity.

### Limitations and changed status

- Confirmation data have now been inspected and must not be reused as fresh
  confirmation for revised hypotheses.
- Source families and candidate families were co-designed; external validity
  is unknown.
- Unrestricted outcome permutation assumes exchangeability and may be wrong
  for future nonstationary or sequence-dependent sources.
- Mutual information was the selection score because the binary candidate
  catalog made it interpretable, not because it is a universal pattern metric.
- No causal, experiential, physical-field, or subjective claim was tested.

### New questions

- Should a later search compare nested perspectives by their incremental
  information rather than their raw maximum?
- Can a simplicity or compression criterion be recorded before new data,
  without privileging the generator form?
- What happens when source construction and candidate design are performed by
  different, genuinely blinded parties?
- How should continuity be investigated when a relationship changes gradually
  rather than at an explicit partition boundary?
- Which null preserves relevant local sequence structure without preserving
  the candidate relation itself?
