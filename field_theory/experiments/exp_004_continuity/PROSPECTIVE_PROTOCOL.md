# Investigation 4 prospective evaluation protocol

**Status:** frozen after retrospective Investigation 4 analysis and before any
query of `visible_runs` rows above source high-water ID 46095.

**Recorded:** 2026-10-30.

## Narrow claim and target

The retrospective backtest selected the immediately preceding 1,000-row status
distribution as the lowest-mean-log-loss instrument. The primary prospective
question is whether that fixed expectation has lower log loss than the fixed
25,000-row expanding-prevalence expectation on the first 1,000 database-ordered
`visible_runs` rows with ID greater than 46095.

This is a narrow comparison of two probability forecasts, not a claim that
chronology is universally superior or that Field Theory is validated.

## Frozen secondary expectations

Two recurrence expectations are also frozen before outcome access:

- the status distribution following the eligible historical state with the
  closest labeled model composition;
- the status distribution following the eligible historical state with the
  closest operational-relation signature.

They are secondary exploratory comparisons. Their inclusion tests whether
structural recurrence can outperform direct chronological proximity on new
rows despite its weaker retrospective average.

All four distributions use additive 0.5 smoothing over `cancelled`,
`completed`, `failed`, `interrupted`, and a reserved `other` category for any
previously unseen terminal label. No weights, categories, analogs,
block size, or smoothing may change after availability or outcomes are read.

## Availability and privacy boundary

The deployed checker opens `/home/bs/.jarvis-v2/state/jarvis.db` with SQLite
`mode=ro` and `PRAGMA query_only=ON` on hostname `Jarvis`.

It first queries only `COUNT(*)` and `MAX(id)` for rows above 46095. If fewer
than 1,000 are available, it writes an availability record and does not read
status, timestamps, text, identity, model, provider, or any other row field.
The designated evaluation remains pending and the method remains frozen.

When at least 1,000 rows exist, one read transaction selects exactly the first
1,000 by database ID. The privacy-limited evaluation extract contains only a
research observation index, source row ID, observation timestamp, explicit
timestamp basis, and terminal status. It excludes message/error text, run and
session identifiers, users, workspaces, models, providers, capabilities, and
all payloads.

## Evaluation

The fixed outputs are:

- mean log loss in bits;
- multiclass Brier score;
- observed terminal-status counts;
- pairwise score differences, with the primary difference defined as
  `previous_block - expanding_prevalence` so a negative value favors the
  preceding-block expectation.

There is no fixed success threshold. The first completed 1,000-row evaluation
is the designated independent test. Interim outcome inspection is prohibited.
If the evaluation is pending, already inspected historical rows must not be
substituted.
