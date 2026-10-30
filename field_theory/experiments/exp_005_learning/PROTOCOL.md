# Investigation 5: consequence, learning, and continuity

**Status:** protocol recorded before downloading or inspecting the source data.

**Recorded:** 2026-10-30.

## Prompt and unresolved dependency

Can an error have a consequence that changes subsequent information weighting,
and under what retention conditions does that changed organization continue?

The central unresolved dependency is whether a retained state change should be
called learning merely because it follows an error. This investigation keeps
four observations separate: the error, a changed internal loss record, a
changed next prediction, and persistence of that change. Prediction quality is
an additional outcome, not the definition of learning.

## Independent observational source

The source is the WDC-SILSO monthly mean total sunspot number CSV, version 2.0,
published by the Royal Observatory of Belgium:

`https://www.sidc.be/SILSO/INFO/snmtotcsv.php`

The publisher describes each value as the arithmetic mean of available daily
total sunspot numbers in a calendar month. The file begins in January 1749 and
marks definitive rows with `1` and provisional rows with `0`. Only definitive,
non-missing rows are analyzed. The exact downloaded bytes, retrieval time,
source URL, digest, license, parser version, and exclusions are preserved.

This is independent of Jarvis and was not generated to demonstrate the
analysis. It is nevertheless an instrumented historical record, not direct
access to solar reality. Revision of the source series, changing observation
coverage, interpolation, and measurement uncertainty remain part of its
provenance. WDC-SILSO requires attribution and distributes the data under
CC BY-NC 4.0.

No Investigation 4 live rows are queried or consumed.

## Observation boundary

Rows are ordered by `(year, month)`. The first usable prediction follows a
132-month warm-up. Two chronological roles are fixed before data access:

- development: observations through 1999-12;
- evaluation: observations from 2000-01 through the last definitive downloaded
  month.

The development period initializes continuing mechanisms and selects one fixed
expert baseline. The evaluation period is not used to tune expert definitions,
learning rate, retention values, split date, or metrics. Because the analyst
knows that sunspots are cyclic and chose a solar dataset, this is a held-out
chronological evaluation, not investigator blinding or universal confirmation.

## Fixed accessible expectations

Every mechanism receives the same three expert predictions at month `t`:

1. `previous_month`: the value at `t-1`;
2. `trailing_12_mean`: the mean of `t-12` through `t-1`;
3. `cycle_lag_132`: the value at `t-132`.

The 132-month lag explicitly encodes an approximate 11-year solar-cycle
assumption. It is a chosen perspective, not a discovered natural period. No
future value, centered smooth, provisional value, standard deviation, or
observation count is available to a prediction.

## Constructed consequence and retention mechanisms

All adaptive mechanisms use the same post-outcome expert loss:

`abs(prediction - outcome) / (1 + abs(outcome))`

Before each prediction, expert access weights are proportional to
`exp(-2 * retained_loss)`. After the outcome, retained loss changes by:

`retained_loss = retention * retained_loss + current_loss`.

Four fixed retention conditions are compared:

- `one_encounter`, retention `0.0`: only the most recent consequence can alter
  the next weighting;
- `short_continuity`, retention `0.9`;
- `long_continuity`, retention `0.99`;
- `cumulative_continuity`, retention `1.0`.

Two nonadaptive controls see and record the same errors:

- `fixed_uniform` always gives each expert weight one third;
- `fixed_selected_expert` uses only the expert with lowest development-period
  mean absolute error, selected once before evaluation.

The fixed-uniform control accumulates an error ledger while leaving access
weights unchanged. This deliberately constructs a retained consequence with no
adaptive effect. The adaptive rules deliberately construct learning in the
narrow operational sense. Their existence is therefore not a finding; whether
different continuity conditions produce different trajectories or useful
expectations on independent observations is a finding.

## History and reset comparison

Each adaptive mechanism has two evaluation perspectives:

- `continued`: retained losses from development enter evaluation;
- `reset`: retained losses are set to zero immediately before 2000-01.

Both then receive identical evaluation observations. Differences isolate the
effect of accessible prior history under the constructed update rule. They do
not prove identity, subjective perspective, or natural learning.

## Measurements

The complete prequential trace preserves, before and after every outcome:

- source month and observed value;
- each expert prediction and post-outcome loss;
- mechanism prediction;
- weights used for the prediction;
- retained losses after the consequence;
- whether the row belongs to development or evaluation.

Development and evaluation summaries retain mean absolute error, root mean
squared error, mean normalized absolute error, mean month-to-month weight
change, mean effective expert count `1 / sum(weight^2)`, and the fraction of
evaluation months in which continued and reset predictions differ. Metrics
remain separate; there is no theory score or fixed success threshold.

A fixed-expert error table is also preserved so a changing ensemble cannot be
credited merely for containing a strong static expert. The main visualization
shows observed values and selected predictions plus adaptive expert weights;
it is descriptive and does not imply mechanism discovery.

## Alternative interpretations and controls

Paired mechanisms on identical observations make output differences
attributable to the declared update and retention rules. They cannot show that
the solar process learns, that the chosen errors cause solar changes, or that
these algorithms correspond to Bjørn's full concepts.

Potential explanations for performance differences include ordinary online
model averaging, nonstationarity, chosen expert quality, the 2000 boundary,
scale normalization, solar cycles, observation revisions, and chance alignment
with regimes. Long retention may help, harm, or become inert. A changed
prediction can be learning by the local definition while being empirically
worse.

After primary inspection, at most one focused post-hoc audit may be added to
explain a surprising interval. It must be labeled exploratory and cannot alter
this protocol, the primary trace, or the evaluation summary.

## Interpretation boundary

This investigation can validate whether the research instrument distinguishes
recorded error, consequence, adaptive response, and persistence, then observe
how those constructed mechanisms behave on an independently observed process.
It cannot decide whether learning is fundamentally different from state
transition, establish a universal retention condition, explain solar causality,
derive identity or perspective, or validate Feltteori as a whole.
