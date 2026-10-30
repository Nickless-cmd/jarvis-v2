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

### Valid deployed run

Revision `96c1f6a49` was deployed to CT105 without restarting runtime services,
because only the independent research project changed. The extractor ran on
hostname `Jarvis` against the production database with `mode=ro` and
`query_only=ON`. It preserved 25,000 `visible_runs` rows through high-water ID
46095, digest
`b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`.

**Live Investigation 1 observation:** Adjacent-status MI was 0.045476 bits,
provider/status MI was 0.023295 bits, and joint provider-model/status MI was
0.046282 bits. None of 500 outcome permutations reached any observed value.
The terminal-status distribution was strongly imbalanced: 23,674 completed,
866 interrupted, 282 failed, and 178 cancelled.

**Live Investigation 2 observation:** The first chronological block had a
constant discovery outcome (2,500 completed runs), so all candidate scores were
zero and its tie-broken candidate has no discovery meaning. Block 2 selected
hour band plus weekday and retained a smaller later relationship. Blocks 3, 4,
and 5 independently selected model plus weekday, with discovery/confirmation
scores of 0.090477/0.193991, 0.074508/0.073069, and 0.060022/0.034201 bits.

**Interpretation:** A model-plus-weekday relationship was continuous across
three later operational eras but not constant in strength. It may reflect
routing, availability, workload, deployments, or incidents. It is detectable
structure in the live record, not yet a causal explanation.

**Post-hoc method change:** The primary result retained only the five highest
discovery candidates. After inspecting it, revision `1aec61080` added and ran a
post-hoc audit preserving all 200 candidate/block scores on the same observation
digest. This audit found positive incremental joint-minus-model information in
blocks 3–5, but it is exploratory and the inspected confirmation rows cannot be
reused to confirm that refinement.

**Operational verification:** Both Jarvis services remained active throughout,
the deployed repository remained clean, and no runtime restart or database
write was performed by the measurement workflow.

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

## 2026-10-30 — Investigation 3: changing observable relationships

### Prompt and evidence status

Investigation 2 repeatedly selected `model + weekday → terminal status` in its
last three historical blocks, while later-half plug-in MI changed from
0.193991 to 0.073069 to 0.034201 bits. Investigation 3 asked what changed
without treating the apparent decline as a weakening relation in advance.

The 25,000 observations had already been inspected. The protocol therefore
classified every new measurement as retrospective exploration rather than
independent confirmation. The immutable live observation digest remained
`b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`.

### Recorded method

The primary deployed runner used overlapping 2,000-row windows stepped by 500
rows, plus 1,000- and 4,000-row sensitivity views. It measured outcome entropy,
model and joint cardinality, raw and normalized MI, and incremental weekday
information beyond model. Two null references were kept distinct:

- global outcome permutation, which destroys operational chronology;
- weekday permutation within model×calendar-month, which preserves outcomes,
  models, row order, monthly drift, and status clustering while disrupting
  exact calendar alignment.

Adjacent 1,000-row blocks exposed descriptive distribution discontinuities.
Smoothed block-to-next-block log-loss examined whether a learned perspective
transported as expectation.

### Method correction before the preserved run

The first deployed context collection at revision `f0c8295ac` revealed that a
provider/model epoch beginning before the observation cutoff extended 12
minutes beyond it. The observation analysis was unaffected, but the context
claim was too broad. That output was rejected and not preserved as a valid run.

Revision `07906ebdd` changed the query to include only epochs ending at or
before the cutoff and added a crossing-epoch regression fixture. The complete
primary analysis and corrected context collection were then rerun on CT105.
Both `jarvis-api` and `jarvis-runtime` remained active; neither was restarted.

### Primary observations

Forty-seven overlapping windows showed no smooth three-era decline. The first
six had constant `completed` outcomes and zero measurable status relation.
Structure appeared in May, rose in June, and formed a localized maximum from
July 5–16:

- status entropy: 0.759112 bits;
- non-completed prevalence: 15.05%;
- model MI: 0.153956 bits;
- model×weekday MI: 0.251291 bits;
- incremental weekday given model: 0.097335 bits;
- conditional-null mean: 0.020596 bits;
- conditional-reference adjusted increment: 0.076739 bits;
- conditional exceedances: 0/200.

The maximum remained in the same July region with 1,000-row and 4,000-row
windows, although magnitude changed. September reached slightly higher outcome
entropy (0.791889 bits) with much lower joint MI (0.091898), challenging an
entropy-only explanation. A June window contained 19 models but only 0.087929
bits, challenging a cardinality-only explanation.

The largest model-composition discontinuity occurred May 6 (0.683707-bit
Jensen–Shannon divergence) with almost no status-distribution change. July 5
and July 16 instead bracketed a +12.5 and −12.2 percentage-point change in
non-completion while model composition also changed.

### Unexpected transport result

`model + weekday` worsened next-block log-loss relative to model alone in all
four adjacent transfers: −0.004993, −0.007098, −0.062123, and −0.020104 bits of
gain. The largest degradation occurred with 93.9% exact joint-state coverage,
so unseen categories were not a sufficient explanation. Retrospective
dependence did not become stable expectation under this instrument.

### Post-hoc investigative path

After the July maximum was observed, revision `1824d98cb` added a declared
post-hoc cell audit. Non-completion was 3.90% in the immediately preceding
2,000 rows, 15.05% in the selected maximum, and 3.85% in the following rows.
Thursday contained 155/639 non-completed outcomes and the elevation crossed
several models rather than one rare category.

That result made weekday look potentially date-local. Revision `0b9524ce8`
therefore added a second declared post-hoc day×model audit. Both Thursdays were
elevated, but differently: July 9 had 34/123 non-completed, dominated by 30
interruptions; July 16 had 121/516, dominated by 115 failures. Two occurrences
do not establish a weekly process. The stable label joined operationally
different status mixtures.

### Context limitations

The read-only aggregate context source established no explanation for July.
`provider_model_epochs` begins September 10 and `central_incidents` August 7.
Git author dates are not deployment records, and later routing/event tables do
not reconstruct the earlier deployed state. Deployment, routing, incidents,
workload, retries, and classification change remain alternatives without
adequate historical evidence.

### Revised interpretation and unresolved questions

The five-block decline is now better described as a localized July episode,
later weaker structure, and a measurement that changes with window,
representation, and null model. Weekday may encode recurrence, exact dates, or
unobserved shared causes. The current record cannot decide among them.

The next defensible step is prospective: freeze a method before untouched rows,
record deployment/routing revision at observation time, retain exact-date
context, and distinguish failure from interruption. A null preserving weekly
traffic and date-local clusters should be designed for that specific question,
not retrofitted as confirmation on these rows.

## 2026-10-30 — Investigation 4: relational continuity and expectation

### Prompt and selected distinction

Investigation 4 asked what distinguishes a relationship that appears in
recorded information from one that remains useful across change. The selected
distinction was structural similarity versus transition continuity: does a
past state that resembles the present have a similar successor, and is that
more useful than the chronologically nearest state?

The historical snapshot was already inspected. The retrospective protocol
therefore remained exploratory and reserved a separate prospective boundary
for rows above high-water ID 46095.

### Retrospective method

Revision `32092ec71` was deployed before analysis. Twenty-five non-overlapping
1,000-row blocks were represented independently as:

- status proportions plus adjacent-status transitions;
- operational relational features without explicit calendar fields;
- the same relation with weekday contributions;
- labeled model composition.

No combined continuity score was created. Historical recurrence predictors
could use only an analog state and its successor that both occurred before the
current state. Log loss and Brier score were recorded separately.

### Structural recurrence observation

The closest non-adjacent state was closer than the closest chronological
neighbor for 13/25 state/transition blocks, 12/25 operational blocks, 12/25
calendar blocks, and 10/25 model-composition blocks. Distant relational
recurrence therefore exists under these instruments.

The result was perspective-sensitive. At 500 rows, non-adjacent model
composition was closer in 50% of states; at 2,000 rows only 8%. State/transition
recurrence remained common at 60–67%. A state boundary is part of the
measurement, not an observer-neutral fact.

Blocks 1 and 9 had zero operational and calendar distance because both had only
`completed` outcomes. This was recorded as representational degeneracy rather
than evidence that their generating systems were identical.

Calendar and operational signatures chose exactly the same analog for all 22
historical targets. Calendar information altered distances but did not add a
new recurrence organization at this resolution.

### Expectation observation

The preceding-block predictor had the best mean historical scores: 0.390812
bits log loss and 0.114384 Brier. Expanding prevalence scored 0.435067 bits.
Recurrence predictors ranged from 0.442935 to 0.482410 bits.

Recurrence sometimes helped, but made rare large errors. Before target block
13, operational recurrence treated block 8 as analogous to block 12 and used
block 9's all-completed successor. The July onset then produced 1.680037-bit
loss versus 0.994010 for the preceding block. Similar current states did not
have continuous transformations.

After the July episode, the reverse occurred. For target block 15, expanding
prevalence scored 0.206496 and state/transition recurrence 0.214097 versus
0.347854 for the preceding block. Chronological proximity carried the episode
forward after its termination.

The finding revised continuity into at least four empirical meanings: state
similarity, transition recurrence, chronological persistence, and predictive
usefulness. None implied the others.

### Prospective freeze

Revision `05699cef6` added a separate prospective protocol and evaluator. The
primary comparison was frozen as the previous 1,000-row distribution versus
the expanding 25,000-row prevalence. Model-composition and operational
recurrence were retained as secondary expectations. Additive 0.5 smoothing,
an explicit `other` outcome, the first 1,000 rows above ID 46095, log loss, and
Brier score were fixed.

The forecast was generated on deployed CT105 using only historical rows, then
committed as `fd2329ce7` and deployed before the availability query. The frozen
previous-block expectation assigns 0.929177 to completion and 0.060349 to
interruption. The expanding expectation assigns 0.946885 and 0.034657.

### Genuine uncertainty preserved

Only after forecast deployment did the evaluator query the live database. It
found three rows above ID 46095 and current maximum ID 46103. The 1,000-row
target was unavailable. The status record states `outcomes_read: false`; only
`COUNT(*)` and `MAX(id)` were queried.

No three-row interim result was inspected. The independent predictive question
remains open. Experience has formed explicit expectations, but predictive
success has not yet been observed.

### New questions

- Which context distinguishes states that look similar but have different
  successors?
- Can changes leading into a state be more informative than the state itself?
- When does recent experience adapt, and when does it merely lag an abrupt
  reversal?
- Would duration or traffic intensity add information that event order lacks?
- Does recurrence become useful in an independently understood non-Jarvis
  process?
- What will the frozen forecasts do on the first complete untouched target?
