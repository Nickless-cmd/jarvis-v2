# Investigation 6: does the retention→adaptation relation transfer?

**Status:** completed transfer test on an independent physical source, 2026-10-30.
Protocol frozen in `experiments/exp_006_order/PROTOCOL.md` and committed before
the source was parsed.

## What was asked

Investigation 5 found on monthly sunspot number that greater retention of
accumulated loss did not increase continuing adaptation: long and cumulative
retention concentrated all weight on one expert and became indistinguishable
from a fixed baseline. That was recorded as a property of the constructed
mechanism, not a general law.

Investigation 6 asks the narrower, discriminating question: **does that
relation transfer to a physically unrelated series under the identical
mechanism?**

This is not a test of Bjørn's progression. Field, identity, perspective,
experience and access are not operationalised here, and no result below
supports or contradicts them.

## Source

- NOAA Global Monitoring Laboratory, Mauna Loa CO₂ monthly mean.
- 823 monthly observations, 1958-03 through 2026-09, no missing values.
- Preserved byte digest in `exp006_results.json`.
- Instrumented, historically revised physical record; not generated for this
  project. The Mauna Loa site was suspended Nov 2022 – Jul 2023 and substituted
  from Maunakea; that discontinuity is inside the evaluation period and is not
  corrected for.

## Mechanism

Copied unchanged from `exp005.learning.1` — the constants are *imported*, not
retyped, so the two runs cannot silently diverge:

- experts: previous month, trailing-12 mean, lag-132;
- loss: `|prediction − outcome| / (1 + |outcome|)`;
- learning rate 2.0, softmax over retained losses;
- retentions 0.0 / 0.9 / 0.99 / 1.0, continued and reset-at-2000 variants;
- development before 2000-01, evaluation from 2000-01.

The fixed expert was selected by development MAE: `previous_month`
(1.0901), against `trailing_12_mean` (1.9662) and `cycle_lag_132` (14.5325).

## Method deviation (2026-10-30): the reset branch never ran

**Status:** deviation recorded; the original run is preserved unchanged in
`artifacts/exp_006_order/noaa_20261030/`. Corrected run in
`artifacts/exp_006_order/noaa_20261030_v2/`.

The first implementation gated the reset on an empty trace:

```python
if reset_at_evaluation and period == "evaluation" and not trace:
    retained = {expert: 0.0 for expert in EXPERTS}
```

`trace` is already filled by the development period when the boundary is
reached, so the condition was never true and **reset never executed**. The
`_reset` variants therefore ran the identical computation as `_continued`,
which was then reported below as an empirical finding about continuity. It was
an instrument fault.

Investigation 5 had the correct form — `observation.date == "2000-01"` — so the
intended behaviour was already documented in this project.

The preserved test asserted that continued and reset produced identical
predictions for every retention. That assertion was the fault wearing a guard's
clothes: it locked in the symptom instead of checking the mechanism. It is
replaced by two tests: one that requires the reset variant's first evaluation
weights to be exactly 1/3 each while the continued variant keeps its
development history, and one that pins how far a reset can reach when retention
is zero.

Two reporting errors are corrected with it: 691 is the number of rows per
mechanism after the 132-month warm-up, not the evaluation length — the
evaluation period is **321 months**. And a mechanism holding 1.886 effective
experts does not by itself show that it keeps learning; a nearly fixed mixture
of two experts can also be almost unresponsive. The measured mean weight change
(0.0016) is the figure that speaks to that, not the effective-expert count.

## Result: the transfer is falsified

Corrected run, `noaa_20261030_v2`, same preserved source digest
(`d8:95:fb:5b:…:07:f6:75`), identical constants imported from
`exp005.learning.1`:

| Mechanism | MAE | Effective experts | Mean weight change |
|---|---:|---:|---:|
| fixed previous_month | 1.1617 | 1.000 | 0.0000 |
| one encounter, continued | 7.6284 | 2.993 | 0.0015 |
| one encounter, reset | 7.6293 | 2.993 | 0.0016 |
| short continuity, continued | 3.9732 | 2.598 | 0.0018 |
| short continuity, reset | 4.0424 | 2.610 | 0.0021 |
| long continuity, continued | 1.3024 | **1.886** | 0.0016 |
| long continuity, reset | 1.5308 | 2.002 | 0.0025 |
| cumulative continuity, continued | 1.1558 | 1.152 | 0.0005 |
| cumulative continuity, reset | 1.4354 | 1.786 | 0.0025 |

The continued rows are bit-identical to the original run — the correction
touched only the branch that had never executed. Both falsification conditions
that could fire, fired:

- `long_continuity_continued` keeps **1.886 effective experts** — above the
  frozen threshold of 1.5. On the solar series the same mechanism collapsed to
  1.000. It does not collapse here.
- `long_continuity_continued` is **12.1 % worse** than the fixed expert in MAE,
  far above the 0.5 % threshold. On the solar series it was identical to the
  fixed expert.

`cumulative_continuity_continued` sits at 1.152 effective experts — below the
threshold — but `mae_gap_fraction_vs_fixed = 0.0050000241`, i.e. **0.5000024 %**
against a 0.5 % threshold. That is 0.0000024 percentage points over the line.

It falsifies on the MAE condition alone, and the margin is not a margin. It
should be read as "at the threshold", and it must not be used as an independent
argument for failed transfer. The `long_continuity_continued` result — 1.886
effective experts and a 12.1 % MAE gap — is the one that carries the verdict.

## Second result, corrected: reset costs accuracy on this source

With the reset branch actually executing, continued and reset **diverge for
every non-zero retention**. The direction is consistent across all four:

- long continuity: MAE 1.3024 → 1.5308 (+17.5 %), effective experts 1.886 → 2.002
- cumulative continuity: MAE 1.1558 → 1.4354 (+24.2 %), effective experts 1.152 → 1.786
- short continuity: MAE 3.9732 → 4.0424 (+1.7 %)
- one encounter: MAE 7.6284 → 7.6293 (+0.01 %)

So on this source the retained history is *doing work*: discarding it at the
evaluation boundary makes the mechanism worse and pushes it toward the uniform
prior. That is the opposite of what the broken run reported.

It is **not** the opposite of the solar result — an earlier version of this
document said reset "changed nothing" there, which is wrong. Measured on the
preserved Investigation 5 run:

| Retention on sunspots | Prediction rows differing after reset | MAE continued → reset |
|---|---:|---|
| long continuity | 189 / 318 | 14.8513 → 14.4150 (−0.4363) |
| cumulative continuity | 95 / 318 | 14.8513 → 14.4548 (−0.3964) |
| short continuity | 263 / 318 | 14.0282 → 14.0445 (+0.0163) |
| one encounter | 1 / 318 | 14.4462 → 14.4903 (+0.0440) |

Reset executed on the solar series, and it *improved* MAE for the two
high-retention mechanisms. So the direction of the reset effect is
source-dependent, and the comparison is more interesting than the one that was
written.

The pattern across both sources is consistent with one reading, offered as an
interpretation rather than a result: **a reset helps only when the retained
state has become rigid — when it still determines the prediction but can no
longer be moved by new evidence.**

An earlier version of this paragraph said "information-free", and that was
wrong. On sunspots the two high-retention mechanisms had locked almost all
weight onto one expert and their weights moved by 0.000000, but the retained
state was not empty: it still carried the result of earlier adaptation — *this
expert is to be preferred* — and it still determined every prediction. What had
gone was not the information but its **responsiveness**. Reset changed 189/318
and 95/318 predictions precisely because the state still mattered.

Three properties have to be kept apart, and they vary independently:

| Property | What it asks |
|---|---|
| Retention | Is earlier adaptation still represented in the state? |
| Responsiveness | Can new observations still move that state? |
| Utility | Does the retained state improve the system's results? |

A mechanism can retain a strong historical preference, be nearly insensitive to
new consequences, and still perform worse than if its history were cleared. That
is not absence of information; it is information whose influence has gone rigid.

**Scope of "rigid".** This is a description of the measured window, not an
absolute property. A near-unchanged weight distribution across the observed
period does not establish that the state could never move — only that it did
not move under the conditions present. The claim is bounded by the expert set,
the learning rate, the loss, and the 318 evaluation months actually observed.

Concretely: long and cumulative continued collapsed to exactly the fixed expert
on sunspots (MAE 14.8513 = fixed 14.8513, 1.000 effective experts, mean weight
change 0.000000), and reset gave the mixture a chance to rebuild from uniform.
Where the state was still both retained *and* responsive — short and
one-encounter on sunspots, all four on CO₂ — reset cost accuracy. No mechanism
on CO₂ saturated that far, so reset cost there across the board.

That reading is not tested. It is fitted to eight cells from two sources, and
the CO₂ `long_continuity` case (continued already 12.1 % worse than the fixed
expert, yet reset still made it worse) shows it is not simply "reset helps when
continued underperforms".

The one-encounter case changes by a single row — the boundary prediction — which
is expected: with retention 0 the retained state is only one observation deep,
so there is almost nothing for a reset to remove.

## What the original run claimed, and why it is withdrawn

The preserved text read: *"Continued and reset variants produced identical
predictions in all 691 evaluation rows for every retention value… the retained
history was not doing any work that a reset could remove."*

Both sentences are withdrawn. The identity was produced by a condition that
could not be satisfied, not by the mechanism reaching a fixed point, and 691 is
not the number of evaluation rows. The observation about saturation — that
`long_continuity_continued` settles at 0.621 / 0.379 and moves by less than
0.002 — is measured and stands, but it no longer carries the claim that reset
was irrelevant.

## What this changes about Investigation 5

The solar finding stands as measured, but its scope narrows. "Continuity became
lock-in" is not a property of the retention rule. It is an interaction between
the retention rule, the expert set, and the source:

- On a series where one expert is persistently and clearly best
  (`previous_month` on sunspots), accumulated loss drives the softmax to a
  one-hot vector and adaptation stops.
- On a series where two experts stay comparably good (`previous_month` and
  `trailing_12_mean` on CO₂), the same rule settles at a stable mixture and
  keeps a small but non-zero responsiveness.

The mechanism is identical. The outcome differs. So the earlier conclusion was
about a *joint* configuration, not about retention as such.

## What this does not show

- Nothing about field, identity, perspective, experience, or access.
- Nothing about whether the atmosphere or the Sun learns.
- Nothing about whether another expert set, learning rate, or loss would
  reverse either result.
- No universality claim. Two sources are two sources, and both are
  instrumented records with their own revision histories.
- The CO₂ series has a strong monotone trend. `previous_month` is near-optimal
  for a trended series by construction, which is a plausible reason the
  adaptive mechanisms cannot beat it. That is an interpretation, not a
  measurement, and it was not tested.

## The methodological point that matters most

The falsification was written down before the run, and it fired. That is the
only reason this result is worth anything: had the thresholds been chosen after
seeing 1.886 and 12.1 %, they could have been set to accommodate either
conclusion.

The same discipline is what Investigation 4's frozen forecasts depend on, and
what the recorded blind-breach deviation protects. It is the one part of this
project that has held under pressure.

## Mutation review (2026-10-30): are the experimental conditions guarded?

The reset fault was not a typo. It was a condition that was named, implemented
and reported without ever being activated — and the test suite was green
throughout. That is a class of failure the ordinary tests cannot see, so the
suite was mutation-tested: each experimental condition was deliberately
disabled and the tests re-run. A condition with no test that reacts to its
removal is a condition nothing is guarding.

Baseline 27 passed. Every mutation was applied to the working tree, measured,
and reverted with `git checkout`:

| Mutation | Result |
|---|---|
| exp_005 reset branch → `if False` | 1 failed — caught |
| exp_006 reset branch → `if False` | 2 failed — caught |
| exp_006 `falsifies_transfer` → `False` | 1 failed — caught |
| exp_004 `outcomes_read` → `True` | 1 failed — caught |
| `metrics.mutual_information()` → `0.0` | 5 failed — caught |
| exp_004 access condition `required = 0` (line 214) | 1 failed — caught |
| exp_003 `weekdays` → constant | 27 passed — **survived** |

Six of seven are caught. An earlier version of this section claimed "all seven
are caught" — the same failure this whole review is about: a statement about a
measurement that had not been made. It was then corrected in the other
direction, to "five of seven", on the strength of a mutation that turned out to
have hit the wrong line. And the sixth is caught by an unrelated error rather
than by the assertion it appears to exercise (see below), so the honest count
of mutations caught *for the right reason* is five.

### Correction: the first "surviving" mutation was aimed at the wrong line

`target["rows"]` occurs twice in `experiment_004_prospective.py`:

- line 214 — `required = int(target["rows"])`, the access condition that
  `if available < required:` actually tests
- line 178 — `"required_rows": int(target["rows"])`, a reporting field inside
  the pending status dict

The mutation was applied to line 178. Disabling a reporting field does not
remove a guard, so its survival said nothing about the guard — and the claim
that the threshold was unguarded was unsupported. Mutating line 214 instead
turns the existing test
`test_investigation_004_prospective_waits_without_reading_outcomes` red: with
`required = 0` the `available < required` branch is never taken, outcomes are
read immediately, and `observations[0]` raises `IndexError` on the empty
selection.

**The threshold is guarded.** The mutation review did not find a hole there; it
found a mutation aimed at the wrong line — a third instance of the same failure
form, now inside the instrument that was built to detect it.

### Correction to the correction: "caught" is not the same as "guarded for the right reason"

The line-214 mutant turns the test red with `IndexError: list index out of
range`. That is a red test, but a red test is not by itself evidence that the
property under test was checked. If the mutant already read the outcome-bearing
column before it crashed, the test would go red *while the boundary had in fact
been breached* — the failure would be incidental, not protective.

Measured, not argued. A synthetic database with 999 rows above the frozen
high-water mark and `target.rows = 1000`, with `sqlite3.connect` wrapped so
every statement is recorded:

| Run | Statements actually executed |
|---|---|
| unmutated | `PRAGMA query_only=ON`, `BEGIN`, `SELECT COUNT(*), COALESCE(MAX(id), ?) …` |
| `required = 0` | the same three, **then** `SELECT id, started_at, finished_at, status …` → `IndexError` |

So the unmutated evaluator issues **no** statement that touches `status` when
the sample is insufficient — the boundary holds at the level of what reaches
the database, not merely at the level of the returned dict. And the mutant does
read `status` before crashing, which means the red test is *coincidentally*
red: the `IndexError` comes from `observations[0]` on an empty selection, after
the outcome column has already been read.

The verdict for that mutant is therefore neither "caught" nor "survived" but a
third category: **caught by an unrelated error**. The existing test does not
assert the property it appears to assert. It asserts that the returned status is
`pending_insufficient_rows` and that no observations file is written — both
true of the unmutated code, and both still true of a hypothetical mutant that
read outcomes and then returned `pending` anyway.

A test that would actually guard it has to observe the query stream, not the
return value: assert that no statement referencing `status` is executed while
`available < required`. That is a different assertion, and it does not exist
yet.

This is the fourth instance of the evening's failure form, and the sharpest:
the mutation review's own conclusion — "the threshold is guarded" — was drawn
from a signal (red test) that does not distinguish the two cases it needs to
distinguish.

What does survive is real:

- **`weekdays` → constant** deletes the weekday perspective from
  `_window_metrics`, i.e. one of the three perspectives Investigation 1–3 is
  built on. No test reacts. This one was mutated at the correct site and is a
  genuine coverage gap.

That one confirms the limit stated below by measurement rather than by
argument: `experiment_003_change.py` is covered only indirectly, and the
perspective construction itself is unguarded.

What the review does establish: before the correction, disabling the exp_006
reset branch would have produced a *green* suite. The preserved test asserted
that continued and reset were identical, so the mutant and the expectation
agreed. The guard was not absent — it pointed the wrong way.

Two limits on this review:

- It tests the conditions I could name. A condition nobody thought of has no
  mutant to apply, and this method cannot find it.
- One of the seven mutants survives, so mutation testing is not a certificate.
  It is a scan, and this scan reports one open hole. Direct state-transition
  assertions and an independent reference implementation would cover ground
  this method does not reach.
- A red test is not a verdict. The scan recorded `killed`/`survived`, and the
  line-214 case shows why that is too coarse: a mutant can be killed by an
  unrelated exception after the property has already been violated. Every
  mutation needs three separate proofs before its result means anything —
  that the intended syntax node was the one changed, that the change altered
  the intended behaviour, and that the test reacted *for the right reason*.
  The third is the one this review did not have, and it is the one that
  matters.

### The three code faults are not one mechanism

It is tempting to read the evening's three faults as the same phenomenon as the
sunspot lock-in. They are not, and flattening them would be exactly the error
this project keeps warning about — seeing a pattern and assuming the pattern
means the same underlying mechanism.

- A field that is written but never read has no demonstrated influence through
  that path at all. (`mutating`.)
- A tool that is never registered in the dispatch array is an unreachable
  action path, not a state that resists change. (`commit_attributed`.)
- A condition that is never satisfied is an inactive state transition. (The
  reset branch.)

They share a *form*: an intended relation between two operations is never
realised. The sunspot case is different in kind: there the retained state does
determine every prediction, and it is measurable that it stopped responding.
Shared form is not shared mechanism, and only the sunspot relation was measured.

The one finding this review produced on its own: `experiment_004_prospective.py`
has no dedicated test module. The frozen forecast — the single artifact in this
project whose whole value is that it cannot move — is guarded only from inside
another experiment's test file.

## Questions raised

- Is there a source where the two experts are *equally* good, and does the
  mechanism then stay responsive indefinitely?
- Does the fixed point depend on the learning rate, or only on the loss gap
  between experts?
- Can a mechanism be built that retains history without reaching a fixed
  point — and would that be a different relation, or the same one at another
  scale?
- Investigation 5's "continuity became lock-in" and this run's "continuity
  reached a fixed point" — are those the same phenomenon described at two
  levels, or two different ones?
