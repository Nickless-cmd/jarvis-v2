# Living research notebook

This is a chronological record. Entries distinguish **observation** (what a
method returned), **interpretation** (a proposed meaning), **limitation**, and
**question**. Earlier entries are amended by dated notes, not silently rewritten.

## 2026-10-30 — Investigation 6: the transfer test fired against us

**Status:** completed transfer test; falsification conditions frozen before the
run and one of them fired.

### Observation

Investigation 5's "continuity became lock-in" was recorded as a property of the
constructed mechanism, not a general law. Investigation 6 applied the identical
mechanism — constants imported, not retyped — to NOAA Mauna Loa CO₂ (823
monthly observations, 1958-03 to 2026-09).

The relation did not transfer. `long_continuity_continued` kept 1.886
effective experts on CO₂ against 1.000 on sunspots, and was 12.1 % worse than
the fixed expert in MAE against being identical to it on sunspots.

### Second observation, not anticipated in the protocol

Continued and reset variants produced identical predictions in all 691
evaluation rows, for every retention value. On sunspots the same comparison
produced 263 of 318 differing predictions for short continuity. The weights
show why: `long_continuity_continued` settles at 0.621/0.379 within the first
evaluation month and moves by less than 0.002 across 321 months. The retained
state was already saturated before the reset point, so discarding it removed
nothing the update rule could still express.

### Interpretation

The solar finding stands as measured, but its scope narrows. Lock-in is not a
property of the retention rule; it is an interaction between the rule, the
expert set, and the source. Where one expert is persistently best, accumulated
loss drives the softmax to one-hot and adaptation stops. Where two experts stay
comparable, the same rule settles at a stable mixture and keeps a small
responsiveness.

### Limitation

Two sources are two sources. The CO₂ series has a strong monotone trend, which
makes `previous_month` near-optimal by construction — a plausible reason the
adaptive mechanisms cannot beat it. That is an interpretation, not a
measurement, and it was not tested.

### Why this entry is worth anything

The thresholds were written down before the run and they fired. Had they been
chosen after seeing 1.886 and 12.1 %, they could have been set to accommodate
either conclusion. This is the same discipline Investigation 4's frozen
forecasts depend on.

### Question

Investigation 5's "continuity became lock-in" and this run's "continuity
reached a fixed point" — same phenomenon at two levels, or two different ones?

## 2026-10-30 — Method deviation: the reset branch in Investigation 6 never ran

**Status:** deviation recorded; original run preserved, corrected run added.

### What happened

Investigation 6 (`2221ad6bb9ae`) applied Investigation 5's mechanism unchanged
to NOAA Mauna Loa CO₂ and reported two results: the transfer was falsified, and
continued and reset variants produced identical predictions in every row.

The second result was not an observation. The reset was gated on `not trace`,
and `trace` is already populated by the development period when the evaluation
boundary is reached. The condition was never true. **Reset never executed**, so
the `_reset` variants ran the same computation as `_continued`.

### Why the guard did not catch it

The preserved test asserted that continued and reset produced identical
predictions for every retention. It encoded the symptom as the expectation. A
test that requires two variants to agree, without checking that the mechanism
which should separate them actually fires, protects the fault rather than
the instrument.

### Correction

The gate is now a pending flag that is consumed at the first evaluation
observation. Two tests replace the old one: the reset variant's first evaluation
weights must be exactly 1/3 each while the continued variant keeps its
development history, and a zero-retention control pins how far a reset can reach
when the retained state is one observation deep.

The corrected run is `artifacts/exp_006_order/noaa_20261030_v2/`. The original
is preserved unchanged at `noaa_20261030/`, and the continued rows are
bit-identical between the two — the fix touched only the branch that had never
executed.

### What the corrected run shows

Reset now diverges from continued for every non-zero retention, and it makes
the mechanism **worse**: long continuity 1.3024 → 1.5308 MAE, cumulative
1.1558 → 1.4354. So on this source the retained history is doing work, which is
the opposite of what the broken run reported.

The falsification of the transfer stands: `long_continuity_continued` still
holds 1.886 effective experts and is 12.1 % worse than the fixed expert. Those
figures come from the branch the bug never touched, and they are reproduced
exactly.

### Observation

The error was found by inspecting an observation that should have been
surprising — that a reset produces no change at all is a claim strong enough to
warrant checking the mechanism before publishing it. It was not found by the
test suite, which had been written to agree with the result.

### Question

Which other results in this project rest on a variant that may never have
executed? The same failure shape — a condition that cannot be satisfied, whose
symptom looks like a finding — is cheap to produce and expensive to notice.

## 2026-10-30 — Investigation 6: two reporting errors corrected, and a mutation review

**Status:** findings corrected; no change to the frozen protocol, the preserved
runs, or any forecast.

### Two errors in my own report

1. I wrote that reset "changed nothing" for long and cumulative retention on the
   solar series. That is the opposite of my own measured data. Investigation 5's
   preserved run shows 189/318 and 95/318 differing prediction rows, with MAE
   14.8513 -> 14.4150 and 14.8513 -> 14.4548 — reset executed and *improved* both.
   The direction of the reset effect is source-dependent, which makes the
   cross-source comparison more interesting, not less.
2. I reported the cumulative variant as 0.508 % from the fixed expert. The
   preserved value is `mae_gap_fraction_vs_fixed = 0.0050000241`, i.e. 0.5000024 %
   against a 0.5 % threshold. That is 0.0000024 percentage points over the line.
   It falsifies on the letter of the pre-registered rule and carries no weight as
   an independent argument. `long_continuity_continued` carries the verdict.

### Mutation review

Seven conditions were deliberately disabled one at a time and the suite re-run
(baseline 27 passed, each mutation reverted with `git checkout`). All seven were
caught: exp_005 reset, exp_006 reset, exp_006 falsification verdict, exp_004
`outcomes_read`, and `mutual_information()` returning zero.

**Observation:** before the reset correction, disabling the exp_006 reset branch
would have produced a green suite. The guard was not missing — it asserted the
bug. A mutation test is therefore the check that would have caught this class,
and it was not run.

**Limitation recorded:** mutation testing only covers conditions someone thought
to name. `experiment_003_change.py` is guarded only indirectly, through a test
that asserts snapshot preservation rather than the perspective construction or
the MI values. And `experiment_004_prospective.py` — the frozen forecast, the
artifact whose entire value is that it cannot move — has no dedicated test
module.

## 2026-10-30 — Method deviation: prospective blind was broken after freeze

**Status:** deviation recorded, forecasts and evaluation left unchanged.

### What happened

Investigation 4 froze four forecast distributions at `source_high_water_id`
46095 and documented an availability check limited to `COUNT(*)` and `MAX(id)`.
That procedure was blind to every other field.

Later the same evening, a progress measurement of the pending prospective test
read far more than count and highest ID. The measurement was made on the live
CT105 database and reported, for the rows above the frozen cutoff:

- per-day distribution via `started_at`
- **`status` distribution (`completed: 16, running: 1`)**
- `user_id` and `profile_name`
- model and lane

### Severity, stated precisely

The forecast artifacts are unchanged and their hashes still match. The
evaluation procedure is unchanged. Nothing about what was predicted has moved.

But the claim that the evaluator remained blind to terminal status is **false**.
Sixteen of seventeen rows above the cutoff were read as `completed`. Terminal
status is precisely what the frozen forecasts are meant to predict. Blindness
over remaining future metadata (timing, model, lane, owner) is also broken.

This is worse than a partial breach: the one field that matters most was read,
and it was read by the party who will later judge whether the forecast held.

### Correction, forward only

- Future availability checks on this test are restricted to `COUNT(*)` and
  `MAX(id)`. No other field may be selected until the evaluation is complete.
- The breach cannot be undone retroactively. It can only be recorded.
- The prospective evaluation must not be adjudicated by the same instance that
  read the seventeen rows. An independent reading, or a mechanical evaluation
  script whose output is inspected only after it has been produced, is required.
  Otherwise the result is not a blind test, and calling it one would repeat the
  error this project exists to catch.

### What the deviation does not do

It does not invalidate the forecast. It changes the epistemic status of any
later claim that the forecast was confirmed under blind conditions.

### Observation that prompted the measurement

The rows above the cutoff were produced by one owner profile interacting with
the system, not by background daemons. The observation process is therefore
coupled to the activity being observed: the composition of the eventual sample
depends on who keeps talking to the system. This is recorded as a question for
the project, not as a finding, and it does not license any change to the frozen
predictions.

### Amendment (same day): preregistration and blindness are not the same thing

The deviation above was first written as if a broken blind also weakened the
forecast. That conflates two properties that must be kept apart:

- **Preregistration** — forecast, cutoff, evaluation procedure and scoring were
  fixed and committed *before* any post-cutoff outcome was observed. This still
  holds. The four distributions are unchanged, their hashes match, and the
  evaluation rules were never edited. The prediction remains genuinely
  prospective and can still be tested.
- **Blindness** — the evaluator's ignorance of the reserved observations. This
  is lost and cannot be restored.

What was lost is the evaluator's ignorance, not the forecast's prospective
status. A later claim that the forecast "held" is still meaningful; a claim that
it held *under blind conditions* is not.

Three further distinctions, recorded so they are not flattened later:

1. An independent evaluator restores independence of *judgement*, not blindness
   of *collection*. It does not need to restore the latter for the
   preregistered test to stand. A locked, deterministic scorer with inspectable
   output is a strong starting point.
2. `running` is not a terminal outcome. The sixteen `completed` rows are known
   outcomes; the last row was an observed intermediate state and must not be
   treated as final except by the frozen evaluator's own rules.
3. Sample composition is a separate problem from blindness. If the next 1,000
   rows are produced mainly by one person's intensive use, the result can still
   be a valid evaluation of *that period* without being representative of
   Jarvis' operation in general.

The forecasts and the evaluation procedure remain untouched by this amendment.

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

## 2026-10-30 — Investigation 5: consequence, learning, and continuity

### Prompt and protocol boundary

Investigation 5 made error/consequence and learning explicit in the conceptual
foundation. The selected unresolved dependency was whether a consequence that
changes state also changes a subsequent access organization, and whether that
change persists. The protocol and implementation were committed as
`e9a732ca9` before the independent source file was downloaded or inspected.

The source was the WDC-SILSO version 2.0 monthly mean total sunspot number.
The preserved download contained 3,330 definitive non-missing observations
from 1749-01 through 2026-06 and three excluded provisional rows. Its SHA-256
digest is
`47:49:cc:16:c6:8e:06:73:f5:6e:c8:50:67:4d:05:c4:c8:7c:9d:3c:b8:48:5f:45:35:19:31:b3:82:2f:3f:3e`.
No live Jarvis data were queried; Investigation 4 remains pending and untouched.

### Constructed mechanisms

All mechanisms received previous-month, trailing-12-mean, and lag-132
expectations. A fixed-uniform control recorded a cumulative error ledger but
never changed weights. Adaptive mechanisms used the same normalized errors to
change later weights with retentions 0.0, 0.9, 0.99, and 1.0. Continued/reset
pairs differed only in whether pre-2000 retained loss entered evaluation.

These update rules are constructed operational examples of consequence,
learning, and continuity. Their existence is not an observation about the
external process.

### Primary observations

The previous-month expert was selected by development MAE and remained the
best fixed expert in 318 evaluation months. Fixed uniform MAE was 17.8609 and
the selected fixed expert's was 14.8513. Continued short continuity produced
the lowest MAE at 14.0282, while reset long continuity produced the lowest
normalized absolute error at 0.4283 versus 0.4297 for the fixed expert. Short
continuity's normalized error was worse at 0.4489. No single mechanism won all
predeclared measurements.

Prior history altered later expectations. Continued/reset predictions differed
for 1, 263, 189, and 95 evaluation months as retention increased from 0.0 to
0.9, 0.99, and 1.0. Duration was not monotonic because both cumulative paths
eventually concentrated on the same expert.

### Unexpected result and post-hoc audit

Continued long and cumulative retention were effectively one-hot on the
previous-month expert for every evaluation row. Continuity had become lock-in;
new errors no longer materially reorganized access. Reset variants temporarily
used the trailing-12 relation and slightly improved all aggregate errors over
their continued counterparts.

One declared post-hoc audit examined the metric conflict. Short continuity
improved absolute error in the two upper outcome quartiles but worsened the
lowest quartile, where normalized error gives misses much greater weight. The
lowest-quartile normalized error was 1.1186 versus 1.0140 for the fixed expert;
highest-quartile MAE was 22.7645 versus 24.8025. This explains the arithmetic
disagreement but is not independent evidence.

### Interpretation and limitations

**Interpretation:** The distinctions are empirically useful within the
instrument. A retained consequence can leave access unchanged; adaptive change
can fail to improve a chosen outcome; and continuity can preserve organization
while reducing adaptability. Different histories can alter later expectation
without implying subjective perspective.

**Limitation:** The experiment cannot distinguish learning from ordinary state
transition at an ontological level. It does not show that the solar process
learns or that algorithmic weights instantiate identity, experience, or
subjective perspective. Dataset selection used knowledge of solar cyclicity,
the evaluation is one historical interval, uncertainty fields were not modeled,
and no stochastic significance claim was made.

### Revised assumptions and open questions

- Retention is not a sufficient operational definition of continuity; it may
  preserve state while destroying effective responsiveness.
- Prediction improvement cannot define learning without collapsing two concepts
  that the project intends to keep separate.
- Identical outputs can conceal different retained histories. It remains open
  whether that constitutes latent perspective or merely inaccessible state.
- A second independent process should test whether the lock-in/metric conflict
  is source-specific before new adaptive rules are tuned on this series.
- A future controlled intervention may be needed to distinguish consequence-
  caused change from an autonomous transition that happens after the same event.
