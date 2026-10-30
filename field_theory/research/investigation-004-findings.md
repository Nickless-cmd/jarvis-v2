# Investigation 4: relational continuity, change, and expectation

**Status:** completed retrospective exploration with a frozen prospective test
pending new observations, 2026-10-30.

## Evidence status and provenance

Investigation 4 has two evidence layers that must remain separate.

1. The retrospective analysis reuses the already inspected 25,000-row CT105
   snapshot. Every recurrence and historical-expectation result from it is
   exploratory.
2. A forecast and evaluation procedure were frozen before querying whether
   rows above the historical high-water mark exist. The designated independent
   evaluation needs 1,000 new rows. Only three were available, so no outcomes
   were read and the prospective test remains pending.

Provenance:

- Observation host: `Jarvis` (CT105)
- Historical source: `/home/bs/.jarvis-v2/state/jarvis.db`
- Historical observation high-water ID: 46095
- Historical observation SHA-256: `b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`
- Retrospective deployed analysis revision: `32092ec71`
- Prospective protocol/evaluator revision: `05699cef6`
- Frozen forecast artifact revision: `fd2329ce7`
- Database boundary: SQLite `mode=ro` plus `PRAGMA query_only=ON`

No production state was modified and no service was restarted.

## Method: continuity remains plural

The primary view divides the historical observations into 25 non-overlapping
blocks of 1,000 database-ordered rows. These blocks are an observational
resolution, not claimed natural states. Four representations remain separate:

1. **State/transition:** terminal-status proportions and the adjacent-status
   transition matrix; no model, calendar, or explicit timestamp.
2. **Operational relation:** state/transition plus status entropy,
   model/status MI, adjacent-status MI, non-completion prevalence, and the
   composition of non-completed statuses.
3. **Calendar relation:** the operational signature plus weekday/status MI and
   incremental model×weekday information.
4. **Model composition:** labeled model-population distributions compared by
   Jensen–Shannon divergence.

The first three use bounded root-mean-square feature distance. The fourth uses
a distribution divergence. Their magnitudes are not interchangeable and are
not combined into a universal continuity score.

For each state, the closest non-adjacent block is compared with the closest
chronological neighbor. Historical expectation then asks whether the observed
status distribution after a previous analog state predicts a later target.
Both the analog state and its following block must precede the current state,
preventing target leakage.

## Observation 1: structural proximity and chronological proximity differ

At the primary 1,000-row resolution:

| Representation | Non-adjacent closer than closest adjacent | Mean selected gap |
|---|---:|---:|
| State/transition | 13/25 | 4.48 blocks |
| Operational relation | 12/25 | 4.60 blocks |
| Calendar relation | 12/25 | 4.60 blocks |
| Model composition | 10/25 | 4.28 blocks |

Chronological adjacency is therefore not the same thing as nearest observable
structure under these representations. Several relationships recur across
distant positions.

Examples include reciprocal non-adjacent nearest pairs:

- state/transition: blocks 5↔12, 16↔18, 19↔25, and 20↔22;
- operational and calendar relation: blocks 7↔10, 8↔15, 16↔18, and 20↔22;
- model composition: blocks 2↔5, 7↔25, 11↔16, and 18↔20.

These pairings depend on perspective. Block 7 and block 25 are reciprocal
model-composition analogs, but not operational-relation analogs. Blocks 8 and
15 are operational analogs despite occurring before and after the July episode.

The strongest apparent recurrence also exposes a degeneracy. Blocks 1 and 9
are eight blocks apart but have zero operational and calendar distance because
every outcome in both is `completed`; their entropy and measured status
relations collapse to zero. Zero distance here means that the representation
cannot distinguish the states, not that their generating systems were
identical. Model composition retains distinctions that the outcome relation
erases.

## Observation 2: recurrence is partly resolution-dependent

The conclusion that non-adjacent structure can be closer than adjacent
structure survives alternative block sizes, but model identity is sensitive to
resolution:

| Rows per block | State/transition | Operational | Calendar | Model composition |
|---:|---:|---:|---:|---:|
| 500 | 60% | 52% | 52% | 50% |
| 1,000 | 52% | 48% | 48% | 40% |
| 2,000 | 67% | 50% | 50% | 8% |

State/transition recurrence remains common at all three views. Model-composition
recurrence nearly disappears at 2,000 rows, where broader windows mix model
populations that were distinct at finer resolution. “Continuity of the system”
therefore changes with what the observer calls a state.

This is not license to select the resolution with the most recurrence. It is
evidence that block construction is part of the measuring perspective.

## Observation 3: calendar context did not change analog identity

Calendar and operational signatures selected the same historical analog in all
22 historical expectation targets. Weekday features changed distance
magnitudes, but not which past state was nearest at the primary resolution.

This constrains the role of the calendar representation. Investigation 3 found
detectable model×weekday structure, especially in July, but the added calendar
features did not supply a different recurrence organization here. Detectable
dependence and useful state discrimination are not equivalent.

It does not follow that calendar is irrelevant. A different state definition,
finer day representation, or independent future episode could make it
discriminating. It was redundant for nearest-analog identity under this exact
instrument.

## Observation 4: structural similarity did not provide stable expectation

Six fixed historical predictors were evaluated on 22 later blocks. Lower
scores are better.

| Predictor | Mean log loss (bits) | Mean Brier | Log-loss wins vs previous block |
|---|---:|---:|---:|
| Previous block | **0.390812** | **0.114384** | reference |
| Expanding prevalence | 0.435067 | 0.116174 | 8/22 |
| Recurrence: model composition | 0.442935 | 0.117756 | 8/22 |
| Recurrence: operational relation | 0.473709 | 0.117168 | 6/22 |
| Recurrence: calendar relation | 0.473709 | 0.117168 | 6/22 |
| Recurrence: state/transition | 0.482410 | 0.118393 | 5/22 |

The immediately preceding block is best on average under both proper scoring
rules. This is evidence that event-order proximity retained useful information
that the tested recurrence representations did not capture.

It is not universally best. Recurrence and expanding experience win individual
targets. Their weakness is occasional large error rather than uniform
inferiority:

- For target block 15, immediately after the July maximum, expanding prevalence
  scores 0.206496 bits and state/transition recurrence 0.214097 versus 0.347854
  for the preceding block. Chronological persistence carried too much of the
  July episode forward after it ended.
- For target block 13, where the July episode begins, operational recurrence
  maps current block 12 to analog block 8 and uses block 9's all-completed
  successor. It scores 1.680037 bits versus 0.994010 for the preceding block.
  A superficially similar low-event state did not announce the same next
  transition.
- Model-composition recurrence improves target block 13 to 0.889539 bits by
  selecting a different analog, but later produces large errors, including
  1.353585 bits for target block 20 versus 0.836307 for the preceding block.

The result separates two meanings of continuity. Observable states can recur,
while the transition following those states fails to recur. Continuity of
description did not imply continuity of transformation.

## Experience, learning, and expectation

The instruments expose different consequences of prior information:

- **Expanding prevalence** accumulates all experience but adapts slowly. It is
  badly miscalibrated during the July rise, yet helps after the abrupt fall.
- **Previous-block expectation** is a short-memory learning rule. It adapts to
  gradual local conditions and performs best on average, but carries abrupt
  episodes forward one block too long.
- **Recurrence expectations** use a broader history and an explicit relation
  between present and remembered states. They sometimes recognize a transition
  better than proximity, but they assume that similar states have similar
  successors. The historical record contradicts that assumption often enough
  to worsen average prediction.

More recorded experience therefore does not monotonically improve expectation.
The relation chosen to organize experience matters, and an apparently richer
memory can supply a confidently wrong analog.

These are computational distinctions. They do not establish subjective
experience or learning in the human sense.

## Chronology and time-like structure

The state/transition representation contains no explicit timestamp, elapsed
duration, weekday, or model label, yet often identifies distant states as more
similar than adjacent ones. This shows that some descriptive recurrence can be
constructed from outcomes and event order without calendar categories.

It does not show that time is unnecessary:

- event order defines the transition matrix;
- block position defines what information is prior and what is subsequent;
- model availability and operational evolution encode historical position;
- the best average predictor is the immediately preceding block.

Chronology is partly redundant for describing state similarity but remains
useful for expectation in this record. Explicit clock time, event order, and
structural proximity make different contributions and should not be collapsed.

## Prospective procedure: expectation exists, predictive success is unknown

After the historical result, four forecasts were frozen without reading any
rows beyond ID 46095:

| Forecast | Completed | Interrupted | Failed | Cancelled | Reserved other |
|---|---:|---:|---:|---:|---:|
| Expanding 25,000-row prevalence | 0.946885 | 0.034657 | 0.011299 | 0.007139 | 0.000020 |
| Previous 1,000-row block | 0.929177 | 0.060349 | 0.001496 | 0.008479 | 0.000499 |
| Model-composition recurrence | 0.991022 | 0.004489 | 0.003491 | 0.000499 | 0.000499 |
| Operational-relation recurrence | 0.926185 | 0.043392 | 0.012469 | 0.017456 | 0.000499 |

The model-composition analog is block 7 with block 8 as its successor. The
operational analog is block 18 with block 19 as its successor. These choices,
the distributions, smoothing, target size, and metrics are immutable for the
designated evaluation.

Only after the forecast artifact was committed and deployed did the checker
query the live database. It found:

- 3 rows above ID 46095;
- current maximum ID 46103;
- 1,000 rows required;
- `outcomes_read: false`.

The checker queried only `COUNT(*)` and `MAX(id)`. It did not read status,
timestamps, model, provider, text, identity, or other outcome fields. There is
therefore genuine uncertainty about the prospective result. No historical row
or three-row interim substitute is reported as confirmation.

## Interpretations contradicted or constrained

1. **“Structural similarity implies a repeated transition.”** Contradicted by
   recurrence's worse average prediction and its failures at regime changes.
2. **“Chronological proximity is always the most similar state.”** Contradicted
   descriptively in roughly half the blocks under several representations.
3. **“More historical experience necessarily improves expectation.”**
   Contradicted by expanding and recurrence instruments losing to short memory
   on average.
4. **“Calendar information reorganizes recurrence because it exposed July.”**
   Not supported at the primary resolution; calendar and operational analogs
   are identical for all historical targets.
5. **“Removing timestamps removes temporal information.”** Rejected as a
   description of the method. Event order, block succession, and operational
   history remain temporal carriers.

## What remains unresolved

- Which missing contextual variable distinguishes similar states with
  different successors.
- Whether a transition-based representation can recognize an approaching
  regime change rather than only a current state.
- Whether duration, traffic intensity, retry chains, deployment revision, or
  incident context would separate the July onset from earlier low-event states.
- Whether model-composition recurrence's occasional successes reflect a real
  operational mechanism or historical coincidence.
- Whether the frozen preceding-block expectation will outperform expanding
  prevalence on the designated 1,000 untouched rows.
- Whether the conclusions survive a non-Jarvis source whose state and
  transition mechanisms are independently known.

Investigation 4 does not establish a general law of continuity. It shows that
state recurrence, transition recurrence, chronological continuity, and
predictive usefulness are empirically separable in this record.
