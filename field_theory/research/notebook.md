# Living research notebook

This is a chronological record. Entries distinguish **observation** (what a
method returned), **interpretation** (a proposed meaning), **limitation**, and
**question**. Earlier entries are amended by dated notes, not silently rewritten.

## 2026-11-14 — The chain observed in operation: retention did not correct itself

**Status:** observational note, not an experiment. No protocol, no forecast, no
falsification condition was declared before the events recorded here. It is
recorded because the project's opening assumptions list Jarvis as a possible
future observation source, and this is the first material that source produced
without being asked to.

### Observation

During one working day (2026-11-14), six corrections were made to the same
family of subsystems — consequence recording, decision application, memory
selection. In each case the material needed for the correct conclusion had
already been produced or read in the same session. In each case a distinction
was collapsed: a representation was treated as the thing it represented.

| retained as | treated as | what the material actually showed |
|---|---|---|
| same `subject` string | same finding | the string was a label, not an identity |
| a reservation record | a completed decision | the decision had not been applied |
| 157 record rows | 157 rejections | one observation, written 157 times |
| a commit on `main` | code that had run | the commit was superseded 66 s before process start |
| an updated `created_at` | loss of first observation | the overwriting code never ran in production |
| the selection layer's output | what reaches the prompt | a second filter runs after selection |

The fifth row is the one that matters for this note. The claim of irreversible
loss was not merely unsupported — it was the **opposite** of the measurement
already on screen: 157 rows, 157 distinct `created_at` values, earliest intact.
The correction of a correction was required.

**Who fired the correction.** None of the six were caught by an instrument
inside the system. Each was caught after a question from outside it — five from
one interlocutor, one from another. The system's own retention was intact
throughout: the earlier conclusions were written down, dated, and retrievable.
Retention alone produced no revision.

### Interpretation

This is a naturalistic instance of Investigation 5's finding, not a
reproduction of it. Investigation 5 concluded that retention is not a sufficient
operational definition of continuity, because retained state can preserve
organisation while destroying responsiveness. Here the retained state was
present and *correctly* retained, and responsiveness still failed.

The mechanism that did fire was relational, not continuous. A retained
conclusion became an error signal only when a second perspective introduced a
competing distinction. Continuity held the conclusion; the relation made the
contradiction visible. Neither was sufficient alone.

If this reading is right, the chain in `conceptual-foundation.md` is not
traversed in order. `filter` failed at the point of *distinction*, not at the
point of *access* — the information was available in every case. And
`learning` was driven from `relations` back into `continuity`, rather than
forward from `error`. The day supplies no evidence about `field` or `identity`;
neither was measured.

### Limitation

- **n = 6, one day, one system.** No baseline, no control, no counterfactual.
  Whether the errors would have been caught without the interlocutors is
  unknown and cannot be recovered.
- **Self-classified.** The claim that the six share a form is a post-hoc
  judgement by the same system that made them. That is precisely the kind of
  judgement this note reports as unreliable. A second classifier was not used.
- **One of the six is an error about the errors.** The claimed data loss was
  itself a false conclusion, drawn from a measurement that refuted it. The
  class therefore includes defects in the correction process, not only in the
  original process.
- **Selection effect.** The day was unusually adversarial: two interlocutors
  questioned nearly every conclusion. A day without that pressure would
  plausibly produce fewer recorded corrections — which is not the same as
  fewer errors.
- **No ontological claim.** Nothing here bears on whether the system has
  experience, perspective, or identity. It records that a specific failure
  mode recurred and was corrected from outside.

### Question

What would have to be true for the correction to fire without an external
interlocutor? The candidate signature, not yet built: a conclusion whose
supporting material was produced in the same session, and which was never
re-read against that material after being stated. If that signature can be
detected mechanically, the distinction-collapse class may be detectable before
a second perspective arrives — and this note would become a falsifiable
prediction instead of a retrospective description.

A weaker question, answerable sooner: of the six, how many had a *declared*
verification step that was skipped, versus no verification step at all? That
distinction would say whether the defect is in discipline or in design.

### Amendment (2026-11-14, same day): why this note was not registered as an experiment

**Status:** scope note on the entry above. No protocol, forecast, or run added;
nothing in `experiments/` or `artifacts/` changed.

**Observation.** The entry's own status line says "No protocol, no forecast, no
falsification condition was declared before the events recorded here." The
fields an experiment needs (protocol, forecast, falsification condition, all
declared before the events) are absent, and the events are already past.

**Why it cannot be registered retroactively.** A protocol written now for the
six corrections would be written by a party who has seen the events and their
classification. That is the post-hoc fitting that Investigation 6's
before-the-run thresholds exist to prevent. A forecast about those six events is
not a forecast.

**Why a forward-looking version was not written either.** A prediction such as
"retention will not correct itself within N days" needs three things this
project does not have:

1. a mechanical definition of "a correction" and of "distinction-collapse". The
   six cases were identified by a self-classification, and the entry's Question
   section states that the detector "is not yet built";
2. a baseline rate measured with that definition. None has been measured, so any
   N or threshold written now would be invented;
3. a classifier other than the system that made the errors.

**Decision.** The entry stays an observation. A future experiment may be opened,
but only as a new entry with its own protocol, written after the detector and
baseline exist and before the window it covers. It is not a registration of
this note. The next reader should not try to turn this entry into an experiment
by editing it.

## 2026-10-30 — Investigation 6, fourth correction: a red test is not a verdict

**Observation.** The line-214 mutant (`required = 0`) turns
`test_investigation_004_prospective_waits_without_reading_outcomes` red with
`IndexError`. Wrapping `sqlite3.connect` and recording every statement, on a
synthetic database with 999 rows above the high-water mark and `target.rows =
1000`:

- unmutated: `PRAGMA query_only=ON`, `BEGIN`, `SELECT COUNT(*), COALESCE(MAX(id), ?) …` — nothing else
- mutant: the same three, then `SELECT id, started_at, finished_at, status …`, then `IndexError`

**Interpretation.** The boundary holds at the level of what reaches the
database, which is stronger than the returned dict. The mutant does issue a
statement that *references* the outcome-bearing column before it crashes — but
with `LIMIT 0`, so it returns zero rows and no value is retrieved. An earlier
version of this entry said the mutant "reads the outcome-bearing column"; that
is more than the observation supports. A query being issued and its results
being accessed are two different events, and only the first is demonstrated
here. The red test is red for an unrelated reason either way. The verdict is neither `killed` nor `survived` but a third
category: **caught by an unrelated error**. The existing test asserts the
returned status and the absence of an observations file — both of which a
mutant that read outcomes and then returned `pending` would also satisfy.

**Limitation.** The mutation review's own conclusion ("the threshold is
guarded") was drawn from a signal that cannot distinguish the two cases it
needs to distinguish. `killed`/`survived` is too coarse a vocabulary for this.

**Question.** What would a mutation harness need to record so that "caught for
the right reason" is a measurement rather than a judgement? The candidate
answer, not yet built: identify the target by AST node plus file hash rather
than line number; run in an isolated worktree; assert on the query stream, not
only on the return value; and classify each result as caught-by-assertion,
caught-by-unrelated-error, or survived.

## 2026-10-30 — Investigation 6, third correction: the mutation hit the wrong line

**Status:** one correction to the mutation review. Preserved runs, protocol and
forecasts unchanged. No new experiment.

### Observation

The mutation review reported two surviving mutants. One of them —
`required_rows` → `0` — was applied to **line 178** of
`experiment_004_prospective.py`:

```python
"required_rows": int(target["rows"]),   # reporting field in the pending dict
```

The actual access condition is **line 214**:

```python
required = int(target["rows"])          # what `if available < required:` tests
```

Disabling a reporting field does not remove a guard. Its survival therefore said
nothing about whether the guard was protected, and the claim that the frozen
evaluation's threshold was unguarded was unsupported.

Mutating line 214 instead turns
`test_investigation_004_prospective_waits_without_reading_outcomes` red: with
`required = 0`, `available < required` is never true, outcomes are read
immediately, and `observations[0]` raises `IndexError` on the empty selection.

**The threshold is guarded. Six of seven mutants are caught; one survives.**

### What actually survives

`weekdays` → constant in `_window_metrics`. Mutated at the correct site: it
deletes one of the three perspectives Investigations 1–3 rest on, and no test
reacts. That is a genuine coverage gap, and it is now the only one this scan
reports.

### Limitation

This is the third instance of the same failure form in one evening, now inside
the instrument built to detect that form: a measurement was claimed about a
site that was never touched. Mutation testing constrains what a test suite can
see; it does not constrain whether the mutation was aimed correctly. Verifying
*where* the mutation landed is a separate step, and skipping it reproduces the
exact error the method was adopted to catch.

### Correction of scope: three faults are not one mechanism

The evening's three code faults — `mutating` written but never read,
`commit_attributed` built but never registered, the reset branch never
satisfied — share a *form*: an intended relation between two operations is
never realised. They do not share a mechanism with the sunspot lock-in, where
the retained state does determine every prediction and measurably stopped
responding. Shared form is not shared mechanism.

### Correction of scope: "rigid" is bounded

A near-unchanged weight distribution across 318 observed months does not
establish that the state could never move. The report now states the scope: the
claim is bounded by the expert set, the learning rate, the loss, and the
observed window.

### Question raised

If a mutation can be aimed at the wrong site and still produce a clean-looking
result, what makes the *aim* verifiable? In this case the answer was reading
both occurrences of the same expression and asking which one the guard tests.
That is a manual step, and manual steps are what this project keeps finding are
not enforced.



**Status:** two further corrections to the Investigation 6 report. Preserved runs, protocol and forecasts unchanged.

### Correction 1: a locked state is not an information-free state

The report read: *"a reset helps only when the retained state has already become information-free."* That does not follow from the results.

On sunspots the two high-retention mechanisms had locked almost all weight onto one expert (mean weight change 0.000000), but the retained state still carried the result of earlier adaptation — *this expert is to be preferred* — and still determined every prediction. Reset changed 189/318 and 95/318 predictions, which is direct evidence the state mattered.

Three properties must be kept apart, and they vary independently:

- **Retention** — is earlier adaptation still represented in the state?
- **Responsiveness** — can new observations still move that state?
- **Utility** — does the retained state improve the system's results?

What had gone on sunspots was not the information but its responsiveness. The report now says *rigid*, and states the three properties explicitly.

### Correction 2: the mutation review claimed a count it had not measured

The review stated "all seven, including the two baseline checks, are caught". The table showed five rows. Two mutants had been attempted but never measured, and the sentence was written as if they had been.

Both were run afterwards:

| Mutation | Result |
|---|---|
| exp_004 `required_rows` → `0` | 27 passed — survived |
| exp_003 `weekdays` → constant | 27 passed — survived |

Both survive. The first removes the threshold that keeps the frozen prospective evaluation from scoring on too few observations. The second deletes the weekday perspective from `_window_metrics` — one of the three perspectives Investigations 1–3 rest on.

So mutation testing is a scan, not a certificate, and this scan reports two open holes. The methodological point is unchanged and now measured rather than argued: before the reset correction, disabling the exp_006 reset branch produced a green suite because the guard pointed the wrong way.

### Question raised

Which of the three properties — retention, responsiveness, utility — is the one the chain's learning→continuity relation actually constrains? A mechanism can hold a strong historical preference, be nearly insensitive to new consequences, and perform worse than if its history were cleared. If that is possible, then continuity is not one property but a relation between what is kept and what the system subsequently meets.

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

## 2026-11-25 — Investigation 7: the instrument could not reach its own question

**Status:** completed, inconclusive. Protocol frozen in
`experiments/exp_007_gradient/PROTOCOL.md` before any measurement; run
preserved in `artifacts/exp_007_gradient/run_20261125_v4/`.

Investigation 6's Limitation named an untested explanation — that
`previous_month` is near-optimal by construction on CO₂ — and its Questions
section asked the discriminating version: is there a source where the experts
are equally good, and does the mechanism then stay responsive? Investigation 7
asked whether the collapse to one expert is governed by the **expert loss gap**
rather than by the source, by grading the disagreement on the two preserved
series instead of introducing a third.

### The control passed, after one correction

At blend 0 the run reproduced both preserved results to ten decimals. The first
version of the control compared against the three-decimal figure `1.886` quoted
in the Investigation 6 findings with a `1e-6` tolerance, and reported an
instrument fault for a `0.0003` difference that was rounding in the report. The
control now reads the full-precision values from the preserved result file, and
three tests fail if the rounded figure is put back.

### The instrument's independent variable is not monotone

Blending each expert toward the mean of the other two makes the predictions
converge; once they are close, the difference between their losses is dominated
by noise and the gap turns and grows again. Sunspots run
2.1019 → 0.2290 → 1.0620, CO₂ 0.0554 → 0.0058 → 0.0275. Both turn at blend 0.7.

The outcome variable shows the same shape, and it shows it in mechanisms that
have no lock-in to remove: `one_encounter` — retention 0 — falls from 2.91 to
2.57 on sunspots. A fall that appears where there is nothing to remove is not
evidence that lock-in eased.

### Verdict

`inconclusive_instrument_cannot_reach_question`. Condition 1 fired, but
condition 4 fired with it: the gap the condition depends on is itself not
monotone, so a falsification resting on it does not falsify the hypothesis.

Condition 2 could not fire at all — **zero** matched-gap pairs exist, because
the two sources' gap ranges do not overlap (sunspots 0.11–2.10, CO₂
0.003–0.055). An earlier version of the code counted the absence of pairs as a
failed condition, turning "the instrument cannot reach the question" into a
finding. Corrected: an unreachable condition carries no verdict.

### What would work

The blend changes the predictions and the gap together, so it cannot hold the
gap fixed. Two routes avoid that: construct the gap directly by choosing
predictions whose losses differ by a prescribed amount, or find a source where
two experts are genuinely comparable for a sustained period. The second is what
Investigation 6 asked for in the first place.

### Why this entry is worth anything

The experiment produced no answer, and it says so. The alternative was to report
the fall in effective experts as a falsification — the numbers were there and
they pointed the way the protocol's condition 1 was written to detect. What
stopped that was checking the independent variable itself, and finding that it
turned for a reason that had nothing to do with the mechanism.

## 2026-11-25 — Investigation 8: the gap became an input, and a different variable answered

**Status:** completed. Protocol frozen before measurement, including an addendum
that added the second axis. Run preserved in
`artifacts/exp_008_direct_gap/run_20261125_v2/`.

### Observation

Investigation 7 could not reach its question: its blend changed the predictions
and the gap together, so the gap was not monotone in the instrument. Its own
closing section named the fix — construct the gap directly, so it becomes the
input. The loss function makes that possible exactly:
`_normalized_loss(p, y) = |p − y| / (1 + |y|)` inverts to
`p = y + s · l · (1 + |y|)`, so a prescribed loss is produced, not measured.

### What was done

For each month of both preserved series, `l_best` was measured on the real
experts, so the difficulty of the month stayed anchored in the observation.
Three constructed experts then received `l_best`, `l_best + gap/2`,
`l_best + gap`. The gap is the input by construction — verified after the fact
at **6.7 · 10⁻¹⁶** calibration error.

The control was an analytic prediction rather than a preserved figure: at
`gap = 0` the losses are identical, the softmax is uniform, and the effective
count must be exactly 3. Measured 3.000000000.

### Result

At `fixed` assignment — one expert systematically best every month — the two
physically unrelated series behave **almost identically**. Median difference in
effective experts across all 40 matched (retention, gap) pairs: **0.0000**; 39
of 40 below the 0.25 threshold. The threshold sits near `1 − r` within a factor
of two: r=0.9 → 0.2 (predicted 0.1), r=0.99 → 0.02 (predicted 0.01).

At `roving` assignment — same gap size, but which expert is best follows the
real series — they diverge: 11 of 40 pairs differ by more than 0.25.

### What it means

Investigation 6's missing explanation is measured. CO₂'s monotone trend does not
matter because the gap is small; it matters because the trend makes the same
expert best nearly every month. That is exactly the `fixed` condition, and under
`fixed` both sources collapse the same way.

Investigation 7's own open question — *does the collapse depend on the gap, or on
the stability of the gap over time?* — is answered: **on the stability.** The
assignment axis changed the outcome in 20 of 80 cells.

The verdict is `falsified` for the hypothesis as written, because the source does
matter in the `roving` mode. But the falsification locates the mechanism instead
of defeating it: gap size sets the scale, stability decides whether the scale is
ever reached.

### Why this entry is worth anything

The first run pooled the two assignment modes when deciding whether condition 3
fired, and returned a flat `falsified`. That number was true and told me nothing.
Splitting the condition — which the protocol's addendum had required all along —
turned the same data into the answer to a question two investigations had left
open. The correction was to implement the frozen protocol, not to move the goal.

---

## 2026-11-25 — Investigation 9: the threshold does not depend on the experts

**Status:** completed, not falsified. Protocol frozen and committed before any
measurement. Run preserved in `artifacts/exp_009_expert_set/run_20261125_173937/`.

### Observation

Investigation 8 measured the collapse threshold near `1 − r` on a single expert
set. I ran five: the original, only-fast, only-slow, two experts, four experts —
two sources, two assignment modes, four retentions, with the responsiveness floor
expressed as a fraction of the available experts so the counts are comparable.

The threshold did not move. Not between sources, not between sets, not between
three and four experts. On a grid with a factor of 1.6 between points — fine
enough to resolve what the protocol's factor-of-two grid could not — all four
sets give the same grid point on both sources.

### Interpretation

That is not robustness. With retention `r` the accumulated loss difference
converges to `gap / (1 − r)`, and the softmax has a fixed learning rate, so the
mechanism depends on the single quantity `x = learning_rate · gap / (1 − r)`.
Crossing the 50 % floor happens at a fixed `x`, so the threshold in gap space is
`(x_threshold / learning_rate) · (1 − r)`. The expert set only changes
`l_best(t)` and the sign, and neither enters `x`.

Which means part of Investigation 8 was a tautology. In `fixed` assignment the
expert order is the set's tuple order — constant over time by construction. So
the gap is constructed, the order is constant, and the agreement between sources
follows arithmetically. It was reported as evidence that the source does not
matter. It was evidence that the arithmetic does what arithmetic does.

The part of Investigation 8 that survives as a data result is `roving`, where
the order is sorted by each month's real loss. There the threshold varies by a
factor of eight across sets and sources.

### What the instrument could not do

The two-expert set never crosses its floor. With two experts the minimum
effective count is 1.0, and 50 % of two is also 1.0, so `< 1.0` is unreachable —
the series approaches 1.0 asymptotically (`1.00000023` at gap 0.8) and never
passes it. The `not_falsified` verdict must not be read as evidence that two
experts behave like three. This experiment could not ask that question, and the
test file pins the distinction so a `None == None` comparison cannot silently
turn an unmeasurable cell into a vote for the hypothesis.

### A measurement error I caught

My first analytic check returned exactly `0.2000` for every retention and every
gap. The number was suspiciously constant, which is what made me look: the
effective-count helper iterated over the dict's **keys** (`0, 1, 2`) instead of
its values, computing `1 / (0² + 1² + 2²) = 0.2` regardless of input. Had the
wrong number varied, it would have looked like a result. A quantity that does not
move when its input moves by a factor of 400 is not a measurement.

### Why this entry is worth anything

The question I was asked — does the threshold survive another expert set — has
the answer "yes", and that answer is almost worthless on its own. What makes it
worth writing down is *why*: it survives because it never depended on the
experts. Finding that out required checking the independent variable instead of
reading the flat result as confirmation, and it retroactively narrows a finding I
published one commit earlier.

## 2026-11-25 — Investigation 10: the threshold was measuring two different things

**Status:** completed, falsified. The drift formula is exact for deterministic
drift and does not govern stochastic drift — and the reason is that the
threshold statistic itself means different things in the two modes.

Investigation 9 said the collapse threshold does not depend on the expert set.
That was true and it was a tautology: in `fixed` the deltas are pinned to the
tuple order, so the mean rank positions are always `0, 1/(N−1), …, 1`. The data
dependence lives in `roving`, where the delta follows the real ranking.

Investigation 10 tested whether the roving threshold is governed by the spread of
the mean rank positions, `gap ≈ u_crit(1−r)/(LR·(m_max−m_min))`.

In `fixed` the invariant holds on every cell: `Q` = 3.29–3.54 against
`u_crit` = 3.13/3.18, a ratio of 1.08 — inside the grid factor of 1.15. In
`roving` it fails by up to seven times.

The first run of this investigation returned `instrument_fault` and was stopped
by its own controls. It had a spurious `(N−1)` in the formula; the `fixed` cells
sat at exactly half the prediction, which is what exposed it. Two further
defects — a control applied outside its scope, and a generator that never
actually reached `fixed` — are recorded in the protocol amendment.

Part A controlled the drift directly (`q` = probability that a month's order is
the tuple order). The scaling held: the threshold falls monotonically as the
drift strengthens, and `q = 1` reproduces the fixed threshold. The
unreachability claim failed: at `r = 0.99` a uniform ranking collapses at gap
0.31. A uniform ranking is not driftless in a finite window — sampling alone
produces a mean-position spread of 0.074 over the 100-month effective window.

The decisive measurement came after the run. The hypothesis that the *range* of
the accumulated losses is the right variable was tested and rejected (1.03 to
6.65 times `u_crit`, not constant). The **duty cycle** — the fraction of
evaluation months below the floor — separates the modes cleanly:

- `fixed`: 1.00 on all 16 cells, and mean effective equals the minimum. A steady
  state.
- `roving`: 0.52–1.00, mean just under the floor while individual months fall to
  1.007. An intermittent state.

So `mean_effective_experts < 0.5·N` measures a settled spread in one mode and a
duty cycle in the other. The statistic is inherited from Investigations 8 and 9,
which compared across modes without asking whether it meant the same thing in
each. That is the finding, and it is a criticism of the instrument rather than
only of the formula.

## 2026-11-25 — Investigation 10, correction: one name covered two statistics

**Status:** correction to the section above. Protocol, run and verdict unchanged;
the re-measurement is on the preserved sources and the independent generator.

The section above says "the duty cycle" and then, twelve lines later, reports
`mean/min` under the same name. They are not the same quantity:

- **duty cycle** — fraction of evaluation months below the floor. `[0, 1]`.
  Measures *occupancy*.
- **mean/min** — mean effective count over the minimum. `[1, ∞)`.
  Measures *fluctuation*.

Neither implies the other. On the preserved sunspot series, `fixed`, gap 0.1,
both states give `mean/min` 1.0000 while their duty cycles are 0.0000 (`r = 0.9`,
pinned above the floor, mean = min = max = 1.959) and 1.0000 (`r = 0.99`, pinned
below it, 1.000 throughout). The original report would have given the same
number for opposite states.

Consequences, measured rather than argued:

- The claim that the split is "a matter of degree, not of kind" is **withdrawn**.
  It rested on `mean/min`. On the true duty cycle the split is categorical: on
  the independent generator, `q = 1` gives duty 1.0000 and `q = 0` gives 0.0579.
- The claim that "the softmax is stochastic even when the rank order is
  deterministic" is **wrong**. Softmax is deterministic. The 1.022 measured for
  `q = 1` was the transient from a zero initialisation: with `r = 0.9` the
  effective memory is ~10 months, so ~2.5 % of a 400-month window is transient,
  which accounts for the whole discrepancy. Excluding the first 20 months gives
  `mean/min` 1.0008.
- `_evaluate` now reports `duty_cycle` and `mean_over_min` as separate fields,
  and a test fails if either is missing. The old code could not report the true
  duty at all — it never kept the per-month effective count.

The `fixed` figure of "1.00 on all 16 cells" in the section above is correct, and
for a reason the `mean/min` table cannot show: those 16 cells crossed the floor,
so every one of their months is below it by definition of the crossing.

Open: a threshold defined on a steady state — the median effective count, or the
first month from which the count stays below the floor for `k` consecutive
months — would make the two modes comparable. It needs its own frozen protocol
and must not be fitted to this run.

## 2026-11-25 — Investigation 11: four measures, and two of them were one

Investigation 10 ended with its own instrument as the open problem. One number
cannot say whether a system sits below the floor constantly or oscillates through
it, so four were proposed: occupancy, persistence, recovery, identity stability.

The protocol was committed alone (`2d9cc7d3c`) before the module existed — the
claim Investigation 10 could not make. It also carried a prediction it was built
to break: the first three are not independent. From `O·T = K·P` and
`(1−O)·T = K'·R` follows `P/(P+R) = O·K'/(O·K' + (1−O)·K)`, and since collapse
and healthy runs alternate, `K = K'` reduces it to `O = P/(P+R)` exactly.

**It held.** Measured residual 1.1e-16, on 7 cells in the narrow form and 31 in
the general one. Three measures, two degrees of freedom.

The fourth measure was the real question, and the first answer was no. Condition 3
fired: no pair of cells shared an occupancy within 0.05 while differing in
identity stability by 0.30; the best pair reached 0.199. That is a pre-registered
criterion not observed inside the design — not a dependence demonstrated, and the
two claims should not be merged. Separately, the definition carries an analytic
defect: `1 − switches/(T−1)` divides by the window length, so ~51 switches over
318 months read as 0.839, "stable", while one expert held 72.6 % of the window.

Measured as dominance share instead, the axis is there — and the first version of
this table was wrong, because the sign of `d_t` was inverted. The protocol said
`argmax` of accumulated loss, but the weight is `exp(−LR·(S−min S))`, so the
governing expert is the `argmin`. Over 3198 months `argmax` matched in 1 and
`argmin` in 3198; 42 of 132 cells changed share. The corrected pair comes from one
source, one expert set and one assignment:

| | occupancy | share | identity stability | dominants |
|---|---:|---:|---:|---:|
| synthetic, q=0, gap 0.8, r 0.9 | 0.396 | 0.453 | 0.738 | 3 |
| synthetic, q=0, gap 0.2, r 0.99 | 0.393 | 0.921 | 0.937 | 3 |

Same occupancy to 0.003; three experts share the window in the first, one holds
most of it in the second. The frozen measure orders them the other way round,
which is the point: transition frequency and concentration are different
properties and neither replaces the other.

That pair moves `gap` and `retention` together, so on its own it isolates neither.
Holding `gap` fixed at 0.05 and raising retention 0.9 → 0.99 leaves occupancy at
0.000 in both cells while dominance share goes **0.453 → 0.921** — five such pairs
exist in the grid. Retention shapes the dominance structure without moving
occupancy at all, which is the hypothesis tested with one variable held fixed
rather than inferred from a pair that moved both.

`fixed` is identity stable across all 48 cells: the rank order never changes and
the dominant expert never changes hands, so dominance follows the rank order and
not the realised losses. 101 of 132 cells have occupancy 0 or 1, and on every one
the undefined measure is `None` — the distinction Investigation 10 lost when
`mean_over_min` read 1.000 for both.

The rank is not the power. All four measures read *who* holds the top rank; none
reads *how much* power the top rank holds. Two systems with constant weights
34/33/33 and 60/20/20 return identical values on every one of them —
`occupancy` 0, `dominance_share` 1.000, `identity_stability` 1.000,
`distinct_dominants` 1 — while their power distribution is not comparable.

`_measure_series` computed the weights every month and threw them away. Carried
alongside as `mean_top_weight` and `mean_top_margin`, the grid shows the blind
spot is the majority case: **896 pairs** share occupancy, dominance share and
identity stability to within 0.02 while differing in top weight by more than
0.05. The sharp cell holds the same expert at rank one for the whole window while
that expert carries **38.5 %** of the weight with **3.53** effective experts —
stable rank, distributed power. A report built on the four rank-based measures
alone would call it fully concentrated, and that would be wrong.

That is the same error one level down from where the investigation started: one
grab-bag statistic was replaced by four, and the four shared a single blind spot.

**Does retention shape the rank order or the power distribution?** The grid holds
66 pairs that differ in retention alone, so any difference is attributable to it.
Median change in dominance share **0.000**, in top weight **0.220**; Pearson
correlation between the two changes **0.042**. 35 pairs move the distribution
while the rank order stands still, and **zero pairs do the reverse**. But 28 of
those 35 were already saturated at 0.99 — only 7 prove anything.

The answer is conditional, and it reverses with collapse. On the four pairs where
occupancy is 0.000 in both cells — free of collapse entirely — the rank order
moves by **+0.32 to +0.47** while the top weight moves by only **+0.08 to
+0.22**. Without collapse, retention reshapes *who* wins. With collapse the winner
is already decided, and retention only decides *how much* it wins by: dominance
share is pinned at its ceiling and the distribution is the remaining degree of
freedom. That is why the 28 saturated pairs show a large `Δtopw` with a zero
`Δshare`, and why the power measure is not a better rank measure but the one that
keeps working after the rank measure runs out of room.

**The run count is not an axis; the run shape is.** The identity carries `K` and
`K'` in it, so the count looked like a candidate third measure. It is not one:
`persistence` is *defined* as `below/K`, so `K = O·T/P` is a rearrangement rather
than a regularity — **0 deviations** across all 101 cells where persistence
exists. And because collapse and healthy runs alternate inside one sequence, the
counts cannot separate by more than one: `K − K'` is −1 (42 cells), 0 (7), +1
(83), never more, and that difference is exactly the window-endpoint term
`C₁ + C_T − 1`. Regressing `dominance_share` on `O` and `P` gives R² = 0.4916;
adding `log K` gives 0.5095 — **+0.018** for a whole extra variable.

What the identity did leave free is how the collapse time is *partitioned*. Two
constructed sequences with identical occupancy 0.250, persistence 10.0, recovery
24.0, `K = 4` and `K' = 5` differ only in block lengths — 10+10+10+10 against
37+1+1+1 — and the longest collapse runs **10 against 37**. In the data 27 of 101
cells have `longest/persistence > 1.01`, up to 8.49, and the sharpest real pair
(same source, set and assignment, `K = 15` in both) runs 106 against 48. The
shape is free but weak: adding it on top of `O`, `P` and `log K` moves R² to
0.5114.

The pattern worth keeping: three times now a candidate measure has turned out to
be a rearrangement of one already in the table — `duty_cycle` for occupancy,
`mean_over_min` for constancy, and now the run count for `O·T/P`. A quantity
derivable from the others is not a measurement of them; it is the same
measurement wearing a second name.

## 2026-11-25 — Investigation 12: retention reaches the forecast, and the forecast is not structure

Investigation 11 could not predict the forecast error from any structural measure,
yet retention moved the error in 208 of 260 pairs. Following the path instead of the
correlation settles it: the ensemble error is `|Σ_e w_e·a_e|` with
`a_e = real_e − outcome`, identity residual 0.0, and since the rank order does not
depend on retention and `a` is data, the weight vector is the only channel.

The error is not mostly structure. Over 120 observations the source explains
η² = 0.798 of the total error variation, the expert set 0.114, and retention
**0.002**; the best single expert's error explains **93.4 %** of the level and the
top weight **2.6 %**. Within each expert set separately the oracle explains
86–99.8 %, the structure 0.1–13 %. No structural measure can predict the error
because the error is not in the structure — that is a property of the problem, not
a defect in the measures.

The one path retention takes is concentration. `corr(Δ top weight, Δ error)` is
−0.414 (R² 0.171) and survives dropping the most reactive set (−0.382, R² 0.146).
A concentrated weight is closer to choosing the best expert than to averaging
disagreeing ones: median `error/oracle` falls from 1.432 to 1.367, and concentration
tracks that ratio at R² 0.214. It is the price of weighting rather than selecting,
and retention pays a little of it.

But the effect has no reliable sign — median −0.005, mean −0.690, the error falls in
34 of 60 pairs. The mean is carried by a handful of large cases; the median is half
a percent of the error level. Reporting −0.69 as "retention improves the forecast"
would be the error this whole sequence has been about.

What does *not* happen is the interesting part. The alignment between weight and
error direction, `corr(w_e, |a_e|)` per month, is −0.42 in `fixed` and −0.55 in
`roving`, and higher retention makes it worse in both. Its change explains 0.000 of
the change in error. Retention does not make the ensemble smarter about which
expert is right; it makes it less willing to average.

The corollary: to predict whether a weighted ensemble forecasts well, measure the
disagreement among its members and the error of its best member — not the shape of
its weights.

Two faults in my own controls are recorded rather than smoothed over. A
monotonicity control demanded exactly zero groups where the true error was monotone;
with three gap points a random ordering is monotone one time in six, and the measured
share was 0.10 — below chance, which is the point, but the zero-demanding form failed
for the wrong reason. And condition 1 was written as `1_identity_does_not_hold`, a
fault condition among four success conditions, so `all()` could never be true and the
verdict reported "a control failed" while all five were met. Same class as the sign of
`argmax` in Investigation 11: a name pointing the wrong way, with green tests either
way.

## 2026-11-25 — Investigation 13: the sign is reliable and useless in advance

Investigation 12 ended with an opening: retention moved the true error in 208 of
260 pairs, up to 10.77, and no structural measure predicted it. So where does the
effect have a consistent sign?

I had to retract something first. I wrote that the ensemble never beats the best
single expert "as the arithmetic of a convex combination requires". That is not
arithmetic. The correct statement is `|Σ w a| ≤ Σ w |a|` — an upper bound with no
lower bound — and when the errors point in opposite directions the weighted mean
can land closer to the outcome than any member. Measured: the ensemble beats the
oracle in **2 974 of 19 170 months**, and the worst month is 4 494 times worse than
the best expert. GPT was right and I was wrong, and the wrong version had been
sitting in a findings file as though it were a fact about arithmetic.

The reason it is nevertheless rare is measurable, which is the honest replacement
for the argument that failed. Decomposing `(Σ w a)² = Σ w²a² + 2Σ_{i<j} w_iw_ja_ia_j`,
the cross term is **positive in 59 of 60 cells**, median `cross/diag` +0.285. The
experts reinforce each other's errors. They almost never cancel. That is a property
of these data and not of ensembling in general.

The regime exists. `corr(err/oracle, Δerror) = −0.551`, R² 0.304 — and only −0.263
for the plain error level, so it is not "high error falls back" but specifically
the distance to the best available choice. The price of weighting rather than
selecting, and high retention pays a little of it. Split-half confirms it is not
regression to the mean: 0.358 and 0.208 across halves that share no month, both
above the same-half 0.249.

Then the part that matters. All of it needs `oracle`, which needs the outcome. The
best predictor available *before* the outcome is the top weight, R² 0.150. Expert
disagreement — the obvious proxy for "there is something to gain here" — reaches
**0.034**, and correlates +0.049 with the quantity it would have to replace. It is
not a weak version of the regime; it is unrelated to it.

Seventy percent of the variation in the retention effect is not available until the
outcome is known. And the reason is structural, not a measurement failure: the sign
is decided by whether concentration happens to favour the better expert, which is a
property of the outcome. No reorganisation of the structural measures can recover
it, because the information is not in the structure.

The candidate that failed its hold-out — top-expert stability — flips sign in both
directions and stays in the result. The variant that survives is carried by three
cells, which is not evidence.

So the answer to Bjørn's question is: yes, there is a regime, and no, it cannot be
used. Reporting "retention improves the forecast when the ensemble is far from the
oracle" as a finding would have been true and useless at the same time. Investigations
8–13 built an apparatus that describes weight structure precisely, and this is where
it stops: the forecast error is data, the one structural channel is the distance to
the best choice, and that distance is not knowable in advance.
