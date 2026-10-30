# First deployed Field Theory measurements

**Status:** completed live observational run, 2026-10-30.

This report covers the first valid measurements executed on deployed CT105
against the production database. It supersedes the earlier simulations as
evidence about Jarvis, while preserving them as method-validation history.

## Provenance and privacy boundary

- Host: `Jarvis` (CT105)
- Primary measurement revision: `96c1f6a49`
- Post-hoc candidate-audit revision: `1aec61080`
- Database: `/home/bs/.jarvis-v2/state/jarvis.db`
- Access: SQLite `mode=ro` plus `PRAGMA query_only=ON`
- Source table: `visible_runs`
- Snapshot: 25,000 rows through high-water ID 46095
- Observation range: 2026-03-22 18:22:39 UTC through 2026-10-30 18:17:57 UTC
- Observation SHA-256: `b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`

The extract excludes message previews, errors, run IDs, user IDs, workspace
names, and capability identifiers. It retains operational categories,
timestamp-derived bands, and terminal status. For 365 rows lacking
`started_at`, `finished_at` supplies the recorded observation time and the
fallback is marked per row.

The first deployed extraction attempt stopped before producing a manifest or
measurement when those missing timestamps were encountered. Extraction version
2 documented the fallback before the valid run.

## Live Investigation 1: fixed perspectives

The 25,000 outcomes contain 23,674 completed, 866 interrupted, 282 failed, and
178 cancelled runs. Status entropy is 0.366283 bits; the strong imbalance is
part of the observed system, not normalized away.

| Perspective | Observed MI | Permutation q05–q95 | Exceedances |
|---|---:|---:|---:|
| Adjacent status ordering | 0.045476 | 0.000108–0.000498 | 0/500 |
| Provider | 0.023295 | 0.000622–0.001257 | 0/500 |
| Provider + model | 0.046282 | 0.002535–0.003821 | 0/500 |

No permutation among 500 reached an observed value. This means fewer than one
exceedance was observed at the available Monte Carlo resolution; it is not a
probability of zero.

### Observation

Terminal statuses are not exchangeable across the preserved sequence and are
not independent of provider/model representation. Adding model to provider
nearly doubles the measured dependence, from 0.023295 to 0.046282 bits. The
ordering perspective is similar in magnitude at 0.045476 bits.

### Interpretation limits

The result does not identify cause. Provider, model, deployment era, workload,
and status are historically entangled. Sequential dependence may reflect
outages, migrations, clustered user interruptions, retry behavior, or changing
instrumentation. The outcome permutation deliberately removes all such local
structure and is therefore a comparison, not a realistic counter-history.

## Live Investigation 2: searched perspectives over time

Rows were divided by database order into five contiguous 5,000-row blocks.
Within each block, the earlier 2,500 rows selected one of 40 candidate
perspectives and the later 2,500 rows evaluated it without reselection.

| Block | Approximate UTC range | Selected discovery perspective | Discovery MI | Confirmation MI | Confirmation exceedances |
|---:|---|---|---:|---:|---:|
| 1 | Mar 22 → May 6 | capability presence + hour band | 0.000000 | 0.002269 | 12/250 |
| 2 | May 6 → Jun 14 | hour band + weekday | 0.026811 | 0.013449 | 1/250 |
| 3 | Jun 14 → Jul 25 | model + weekday | 0.090477 | 0.193991 | 0/250 |
| 4 | Jul 25 → Sep 27 | model + weekday | 0.074508 | 0.073069 | 0/250 |
| 5 | Sep 27 → Oct 30 | model + weekday | 0.060022 | 0.034201 | 0/250 |

Database row order is the partition relation. Timestamps overlap by minutes at
one boundary, so the blocks should not be described as perfectly disjoint
clock intervals.

### Block 1: no discovery information

Every discovery outcome in block 1 was `completed`. Status entropy and all 40
candidate scores were therefore zero. The named candidate was selected only by
the stable tie-break rule and has no substantive discovery status. Its later
score must not be described as confirmation of a discovered relationship.

This is a useful negative result: a perspective search cannot distinguish
relationships when the observed outcome contains no distinctions.

### Block 2: weak temporal structure

Hour band plus weekday exceeded all 250 search-wide permutation maxima during
discovery. It declined from 0.026811 to 0.013449 bits in later rows; one of 250
candidate-specific confirmation permutations was at least as large. The
relationship persisted weakly under this comparison but changed in magnitude.

### Blocks 3–5: model and weekday

The same `joint(model,weekday)` perspective was selected independently in the
last three blocks. It strengthened sharply in block 3 confirmation, remained
nearly unchanged in block 4, and weakened in block 5 while staying above all
250 candidate-specific permutation scores.

The post-hoc full-candidate audit shows that the joint representation carried
more raw information than model alone:

| Block | Discovery joint−model | Confirmation joint−model |
|---:|---:|---:|
| 3 | 0.054781 | 0.067674 |
| 4 | 0.030846 | 0.033295 |
| 5 | 0.030727 | 0.024940 |

This difference is an estimated conditional information contribution from
weekday given model. It remains observational. Model availability and traffic
can themselves follow weekly schedules, and joint categorical estimators have
more finite-sample bias than single-variable estimators. The candidate-specific
permutation comparisons account for state count under exchangeability, but do
not remove historical confounding.

## What survived and what changed

- Fixed-perspective dependencies survived their permutation comparisons on the
  full live snapshot.
- A model-plus-weekday relationship recurred across three consecutive
  historical blocks and persisted into each block's later half.
- The selected relationship's strength was not constant; the newest block was
  weaker than the preceding two.
- The earliest block could not support discovery because its discovery outcome
  was constant.
- The hour-plus-weekday relationship in block 2 persisted more weakly and is
  sensitive to the chosen chronological boundary.

## Field Theory distinctions

**Information:** The same immutable extract supports fixed global views,
chronological blocks, single variables, joint variables, and sequence views.

**Perspective:** Provider alone exposes less status dependence than
provider-plus-model. In later eras, model alone exposes less than
model-plus-weekday. Representation changes what is observable, while also
changing estimator bias and confounding opportunities.

**Relations and continuity:** The repeated selection of model-plus-weekday in
blocks 3–5 is evidence of relational continuity under this measurement. Its
changing magnitude is equally important; continuity did not mean constancy.

**Expectation:** A discovery-selected perspective predicted nonzero dependence
in later rows for blocks 2–5. Block 1 demonstrates that a mechanically named
candidate is not an expectation when discovery contains no outcome variation.

**Time:** Chronology mattered both through adjacent statuses and through
discovery-to-later comparison. Weekday was also informative, but it is an
explicit calendar representation, not evidence that time is derived from
relations.

No result establishes subjective experience, causality, or a physical
information field.

## New questions

- Does model-plus-weekday dependence remain after conditioning on deployment
  revision, provider availability, traffic volume, and incident windows?
- Is the newest-block decline a recovery, a routing change, different workload,
  or sampling variation?
- Would rolling or change-point views describe continuity more honestly than
  five fixed blocks?
- Which null model preserves outage clustering and weekly traffic while
  disrupting the candidate relation?
- Can status transitions be related to interventions without importing message
  content or user identity?

These questions arise from the live record. They should guide the next
measurement rather than be answered retroactively with the already inspected
confirmation rows.
