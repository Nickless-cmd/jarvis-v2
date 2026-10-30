# Live Investigation 4: relational continuity and expectation

**Status:** retrospective protocol recorded before the deployed exploratory run.

**Recorded:** 2026-10-30.

## Question and evidence status

Investigation 4 asks whether continuity is better described by chronological
adjacency, recurrence of observable state/transition structure, operational
relations, or calendar-conditioned relations. It also asks whether an earlier
structurally similar state supplies a useful expectation for a later block.

The 25,000-row live snapshot has already shaped the question. All analysis of
it remains retrospective and exploratory. A separate prospective protocol is
required before reading any `visible_runs` rows above the existing high-water
ID 46095.

## Immutable source and blocks

The analysis reuses the verified CT105 extract with SHA-256
`b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`.
It creates 25 non-overlapping blocks of 1,000 database-ordered observations.
Blocks are an observational resolution, not natural system states. A 500-row
and 2,000-row sensitivity comparison tests whether descriptive recurrence is
specific to the primary resolution.

Database order supplies event order. Explicit elapsed time is not used in the
state vectors, but order, model availability, cumulative operational change,
and weekday where declared can encode time indirectly.

## Separate representations of continuity

No universal continuity score is defined. Four distances remain separate:

1. **State/transition:** terminal-status proportions plus the normalized
   adjacent-status transition matrix. It uses event order but no model,
   weekday, or timestamps.
2. **Operational relation:** state/transition features plus status entropy,
   model/status mutual information, adjacent-status mutual information,
   non-completion prevalence, and the composition of non-completed statuses.
   Model labels influence MI but are not compared directly across blocks.
3. **Calendar relation:** the operational signature plus weekday/status MI and
   the incremental model×weekday contribution beyond model.
4. **Model composition:** Jensen–Shannon divergence between labeled model
   distributions. This is explicitly population identity, not a label-invariant
   relational signature.

Euclidean root-mean-square distance is used only for the bounded signature
vectors; model composition uses Jensen–Shannon divergence. Magnitudes are not
treated as interchangeable across representations.

For each block, the analysis compares adjacent distance with its closest
non-adjacent block. A distant block being closer under one representation does
not mean chronology is absent; it means that representation does not preserve
chronological adjacency as nearest structure.

## Historical expectation instrument

For target block `t`, only blocks before `t` may form expectations. Four simple
status-distribution predictors are compared:

- expanding prevalence from every earlier row;
- immediately preceding block prevalence;
- recurrence following the most similar earlier state/transition block;
- recurrence following the most similar earlier operational, calendar, or
  model-composition state.

An analog state `j` is eligible only when its following block `j+1` is also
strictly earlier than the current state `t-1`. The status distribution of
`j+1` becomes the expectation for `t`. This avoids target leakage and prevents
the recurrence predictor from collapsing into the immediately preceding block.

All distributions use additive 0.5 smoothing over the terminal statuses.
Cross-entropy in bits and multiclass Brier score remain separate evaluation
views. The backtest does not tune smoothing, block size, or representation to
maximize performance.

## Interpretation boundary

Structural recurrence can describe similarity without identifying a shared
mechanism. A successful analog predictor would not prove that time is derived
or unnecessary. A failed predictor would not prove that experience cannot
support expectation; it would constrain these representations and this source.

Access to prior observations is called experience only in the operational
research sense. A fixed update rule is a computational learning mechanism.
Its probability distribution is an expectation. Only later untouched outcomes
can provide independent predictive evaluation. None establishes subjective
experience.
