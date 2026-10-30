# Investigation 3: the changing structure of observable relationships

**Status:** completed deployed retrospective exploration, 2026-10-30.

## Evidence status and provenance

Investigation 3 reuses the immutable 25,000-row CT105 live extract from
Investigations 1 and 2. The observations were already inspected before this
question and every new result here is exploratory. A new calculation on old
rows is not independent confirmation.

- Observation host: `Jarvis` (CT105)
- Observation database: `/home/bs/.jarvis-v2/state/jarvis.db`
- Observation access: SQLite `mode=ro` plus `PRAGMA query_only=ON`
- Observation range: 2026-03-22 18:22:39 UTC through 2026-10-30 18:17:57 UTC
- Observation SHA-256: `b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`
- Primary deployed analysis revision: `07906ebdd`
- Post-hoc peak-cell audit revision: `1824d98cb`
- Post-hoc day×model audit revision: `0b9524ce8`

The raw extract was not rewritten. Its 365 explicit `finished_at` timestamp
fallbacks remain part of the provenance. The primary analysis produced 47
overlapping 2,000-row windows with a 500-row step. Window sizes 1,000 and 4,000
were retained as sensitivity views.

## Question and measurement perspectives

Investigation 2 observed later-half plug-in mutual information of 0.193991,
0.073069, and 0.034201 bits for `model + weekday → terminal status` in its
last three equal blocks. Investigation 3 asks whether this apparent decline is
better described as changing outcomes, changing model composition, changing
calendar relations, changing estimator behavior, or some combination.

For the same rows, the primary instrument records:

- terminal-status entropy and non-completed prevalence;
- model, weekday, and joint model×weekday plug-in mutual information;
- incremental weekday information beyond model;
- joint MI normalized by terminal-status entropy;
- model and joint-state cardinality and sparse-cell exposure;
- a global outcome-shuffle reference;
- a conditional calendar reference that keeps each outcome, model, row order,
  and calendar month fixed while shuffling weekday within model×month.

The conditional reference preserves more of the observed operational history
than the global shuffle, but is not a counterfactual history. It disrupts exact
weekday alignment and can therefore expose both repeated weekday structure and
date-local incidents that happen to share a weekday.

## Observation 1: the change is localized, not a smooth decline

The full snapshot contains 42 model labels and 172 model×weekday states:

| Full-snapshot perspective | MI (bits) |
|---|---:|
| Weekday | 0.006720 |
| Model | 0.045108 |
| Model×weekday | 0.061589 |
| Incremental weekday given model | 0.016480 |

Joint MI is 0.168145 of the 0.366283-bit full-snapshot status entropy. This
aggregate conceals large changes:

| Representative 2,000-row view | Status entropy | Non-completed | Models | Joint MI | Incremental weekday | Conditional-reference adjusted increment |
|---|---:|---:|---:|---:|---:|---:|
| Mar 22–Apr 20 | 0.000 | 0.00% | 12 | 0.000000 | 0.000000 | 0.000000 |
| Jun 14–Jul 5 | 0.282 | 3.90% | 17 | 0.082639 | 0.044607 | 0.019952 |
| Jul 5–Jul 16, maximum | 0.759 | 15.05% | 10 | 0.251291 | 0.097335 | 0.076739 |
| Sep 19–Oct 3 | 0.792 | 15.80% | 9 | 0.091898 | 0.042556 | 0.024067 |
| Oct 18–Oct 30 | 0.378 | 6.05% | 5 | 0.033409 | 0.024867 | 0.005024 |

The first six primary windows contain only `completed` outcomes and therefore
cannot expose any status relationship. Structure appears in May, rises in
June, forms a sharp July maximum, drops, and partially reappears in September
before weakening in the latest rows.

The maximum is not created by the chosen 2,000-row scale. The largest joint MI
was 0.291140 bits for a 1,000-row view and 0.160498 bits for a 4,000-row view;
both maxima cover the same July region. Window size changes magnitude and
temporal resolution, but not the existence or approximate location of the
peak.

This revises the five-block description. The previous three-number sequence
mixed a strong localized July episode with surrounding observations. It was
not evidence of a single relation decaying smoothly across three eras.

## Observation 2: outcome entropy and estimator opportunity are insufficient explanations

The July maximum has 44 joint states, only 1.9% of rows in states with fewer
than five observations, and 0.251291 bits of raw joint MI. Its global
outcome-shuffle q95 is 0.039887 bits. The observed incremental weekday
contribution is 0.097335 bits; the model×month conditional-shuffle mean is
0.020596 and q95 is 0.026514 bits. None of 200 conditional permutations reaches
the observation. This is finite Monte Carlo resolution, not probability zero.

The joint estimator has a positive reference value even after model is fixed,
so raw incremental MI overstates the observed departure. Subtracting the
conditional mean reduces the July increment by about one fifth, but leaves a
localized 0.076739-bit difference.

Outcome entropy does not explain the trajectory alone. The Sep 19–Oct 3 window
has slightly more status entropy than the July maximum (0.792 versus 0.759
bits), but much lower joint MI (0.091898 versus 0.251291). Cardinality is also
insufficient: the Jun 12–Jul 2 window has 19 models but only 0.087929 bits,
whereas the maximum has 10 models and 0.251291 bits.

Of 47 overlapping primary windows, 41 have positive conditional-reference
adjusted increments and 32 have zero exceedances among 200 conditional
permutations. These counts must not be read as 47 independent tests: adjacent
windows share 75% of their rows, and the dataset, relation, and summaries have
all been inspected.

## Observation 3: model composition and status behavior change at different boundaries

Adjacent non-overlapping 1,000-row blocks expose discontinuities without
declaring formal change points.

- The largest model-composition Jensen–Shannon divergence is 0.683707 bits at
  the May 6 boundary, while status divergence is only 0.000027 bits and the
  non-completed fraction changes by −0.2 percentage points. Model population
  can change sharply while observable outcome behavior remains nearly fixed.
- At the July 5 boundary, non-completed prevalence rises by 12.5 percentage
  points; status divergence is 0.038652 bits and model divergence is 0.126541.
- At the July 16 boundary, non-completed prevalence falls by 12.2 percentage
  points; status divergence is the series maximum at 0.044895 bits and model
  divergence is 0.334197.

The last two boundaries bracket the primary maximum. They show simultaneous
changes in outcomes and model composition, but do not identify which change,
if either, caused the measured relation.

Database row order remains the continuity relation. At one May 6 boundary,
the first timestamp in the later row block precedes the last timestamp in the
earlier block by about six minutes. The views must not be described as perfectly
ordered clock-time intervals.

## Observation 4: the July maximum is broad enough to inspect, but narrow enough to mislead

After seeing the primary maximum, two explicitly post-hoc audits examined its
cells and dates. The selected 2,000 rows span July 5–16.

| Period | Non-completed / rows | Fraction |
|---|---:|---:|
| Immediately preceding 2,000 rows | 78 / 2,000 | 3.90% |
| Selected maximum | 301 / 2,000 | 15.05% |
| Immediately following 2,000 rows | 77 / 2,000 | 3.85% |

Within the maximum, Thursday has 155 non-completed outcomes among 639 rows
(24.26%). The elevation is not attributable to one rare model alone. Examples
include 86/295 for `kimi-k2.7-code:cloud`, 31/137 for
`deepseek-v4-flash`, 14/38 for `glm-5.2:cloud`, and 20/21 for `groq-model`
on Thursday.

The two Thursdays differ operationally:

| Date | Non-completed / rows | Interrupted | Failed |
|---|---:|---:|---:|
| 2026-07-09 | 34 / 123 (27.64%) | 30 | 4 |
| 2026-07-16 | 121 / 516 (23.45%) | 6 | 115 |

The weekday description therefore recurs across both Thursdays in the window,
but the terminal-status composition changes from interruptions to failures.
Two occurrences are not evidence of a stable weekly mechanism. `weekday` may
be a lossy label joining distinct date-local processes.

This is a concrete example of the same observations supporting different
descriptions. “Thursday relation,” “two operational episodes,” and “changing
model-specific failure mixtures” are all compatible with the measured cells.
The current data do not select one causal description.

## Observation 5: detected dependence does not transport as expectation

The five Investigation 2 blocks were reused as a comparability instrument.
Smoothed status probabilities fitted on one complete block were evaluated on
the next. Unseen model×weekday states back off to model; unseen models back off
to status prevalence.

| Train → evaluate | Base loss | Model loss | Model×weekday loss | Weekday gain over model | Exact joint coverage |
|---|---:|---:|---:|---:|---:|
| 1 → 2 | 0.089514 | 0.087050 | 0.092042 | −0.004993 | 6.4% |
| 2 → 3 | 0.671581 | 0.686971 | 0.694069 | −0.007098 | 48.8% |
| 3 → 4 | 0.500130 | 0.501507 | 0.563630 | −0.062123 | 93.9% |
| 4 → 5 | 0.587244 | 0.575075 | 0.595179 | −0.020104 | 76.3% |

Lower loss is better. Model×weekday is worse than model alone in all four
transfers. The largest degradation occurs from block 3 to block 4 despite
93.9% exact joint-state coverage, so unseen categories are not a sufficient
explanation there. Model alone improves on prevalence only in transfers 1→2
and 4→5.

This does not contradict within-period dependence. It contradicts a stronger
interpretation: the historically detected relation was not a stable
next-period predictive rule under this probability model. Observable structure
and transportable expectation are different properties.

## Operational context: what can and cannot be established

The context collector ran on CT105 with SQLite read-only mode and exported only
monthly aggregates through the observation cutoff.

- `provider_model_epochs` has 100 fully bounded rows from Sep 10 through Oct
  30. It has no coverage for the July maximum and is not a deployment log.
- `central_incidents` begins Aug 7 and contains 11,091 records through the
  cutoff. It likewise cannot explain July. Aggregate incident kinds are not
  verified causes of visible-run outcomes.
- Git author dates cover the observation period, but show repository activity,
  not which revision was deployed at a given time.
- No reliable deployment-revision timeline was found for the observation
  period. Routing-decision and general event tables begin still later than the
  relevant June–July change.

The first deployed context attempt exposed an epoch whose `first_seen_at` was
before the observation cutoff but whose `last_seen_at` was after it. That
attempt was rejected. Context version 1 was corrected before preservation to
include only epochs ending at or before the cutoff; one crossing epoch was
excluded because its aggregate count could not be split honestly.

There is therefore no documented operational variable in the available
context that explains the July maximum. A deployment, routing change, outage,
workload shift, retry behavior, or status-classification change remains
possible, but naming one as the explanation would be narrative substitution
for missing evidence.

## Field Theory distinctions tested by the observations

### Same information, different perspective

On identical rows, model exposes 0.045108 bits globally, weekday 0.006720, and
their joint representation 0.061589. Inside July, joint representation exposes
substantially more structure than either aggregate view. Replacing global
shuffle with a model×month conditional calendar reference reduces the apparent
weekday increment but does not erase its localized maximum.

The visible relation changes with representation and measurement assumptions.
That is an empirical property of these instruments, not evidence of subjective
perspective.

### Same perspective, changing information

The fixed model×weekday perspective moves from unmeasurable under constant
outcomes, to weak structure, to a sharp July maximum, then to weaker later
episodes. Status prevalence, model composition, and cell-specific relations
all change. Continuity of the labels does not imply constancy of the measured
relation.

### Changing information and perspective together

A representation fitted in one block becomes harmful to log-loss in the next,
even when most joint states remain available. The earlier perspective does not
carry forward as a stable expectation. This separates retrospective
description from predictive continuity.

## Surprises and revised interpretation

1. The apparent three-block decline is better described as a localized July
   episode plus later weaker structure, not a smooth weakening.
2. Higher outcome entropy does not guarantee higher dependence; September has
   more status entropy than the July maximum but much less joint MI.
3. A perspective can be repeatedly detectable within periods yet degrade
   prediction in every adjacent-period transfer.
4. Weekday combines two Thursdays with different terminal-status mixtures,
   making one stable calendar label compatible with multiple operational
   processes.
5. Model composition can change almost completely while status behavior barely
   changes, as at the May 6 boundary.

## What remains unknown

- Whether the July episodes correspond to deployments, provider incidents,
  workload, retry behavior, instrumentation, or another unavailable variable.
- Whether a future Thursday effect will recur under a method fixed before
  observing new rows.
- Whether exact dates, weekday, model availability, or an unrecorded common
  cause is the more useful relation.
- Whether the terminal-status categories retained consistent operational
  meaning throughout the period.
- How much dependence remains under a null that preserves weekly recurrence,
  date-local outage clusters, and model availability simultaneously.
- Whether results generalize beyond `visible_runs` or beyond Jarvis.

## Evidence needed next

A stronger continuation would freeze a prospective measurement before reading
new rows. It should retain exact date and deployment/routing revision at
collection time, distinguish interruptions from failures rather than only
non-completion, and compare weekday recurrence with date-local incident models.
Circular week shifts or within-model calendar-block resampling may provide more
realistic references than global shuffling, but each would test a different
question and must be recorded before use.

No result here establishes causality, subjective experience, a physical field,
or that apparent randomness necessarily conceals a predictable rule.
