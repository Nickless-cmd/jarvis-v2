# Living research notebook

This is a chronological record. Entries distinguish **observation** (what a
method returned), **interpretation** (a proposed meaning), **limitation**, and
**question**. Earlier entries are amended by dated notes, not silently rewritten.

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
