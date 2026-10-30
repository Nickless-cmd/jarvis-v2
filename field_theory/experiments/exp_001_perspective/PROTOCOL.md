# Experiment 001: perspective and conditional structure

**Mode:** exploratory instrument demonstration.

**Protocol recorded:** 2026-10-30, before the preserved reference run.

## Prompt

Can explicit changes in accessible context make different dependency
structures observable in the same preserved records, and can a permutation
baseline distinguish the constructed relation from finite-sample artefacts?

## Sources

Each row records an index, binary cue, binary context, and binary outcome.

- `iid_control`: cue and outcome are independent pseudorandom bits. Context
  alternates in blocks and should not govern the outcome.
- `context_relation`: outcome normally equals `cue XOR context`, with a recorded
  probability of independent bit-flip noise. Cue and context are balanced in
  expectation, so aggregate cue/outcome association can cancel while their
  conditional relation remains.

The construction is deliberately known. Detecting it validates this narrow
instrument; it is not a discovery about nature.

## Perspectives and measurements

All perspectives operate on the same rows:

1. `outcome_only`: mutual information between adjacent outcomes.
2. `cue_access`: mutual information between cue and outcome.
3. `cue_context_access`: mutual information between the joint `(cue, context)`
   state and outcome.

The analysis also records outcome frequency and binary entropy as description,
not scores. Mutual information is the plug-in estimate in bits. It is biased
upward in finite samples; no correction is silently applied.

For each source, outcomes are repeatedly permuted while cues, contexts, and
outcome counts remain fixed. The complete observed statistics and descriptive
null summaries (minimum, 5th percentile, median, 95th percentile, maximum, and
fraction at least as large as observed) are retained. Quantiles aid inspection;
they are not a preregistered acceptance boundary.

## Reference-run parameters

- 2,048 rows per source
- seed 20,261,030
- context block size 32
- context-relation noise probability 0.10
- 500 outcome permutations per source

These values balance legibility and runtime for the first demonstration. They
are not permanent standards. Any revision must create a new artifact directory
and record its parameters and rationale.

## Preserved outputs

- `observations.csv`: raw generated records;
- `manifest.json`: parameters, environment, method version, and SHA-256 digest;
- `results.json`: derived measurements tied to the raw digest;
- `permutations.csv`: the complete null measurements;
- `perspective_comparison.svg`: observed values against null ranges;
- `summary.md`: generated observation-level report without theoretical claims.

## Limits and alternative explanations

Any recovered relation was encoded by the generator. Failure may arise from an
implementation error, unsuitable statistic, sample variability, or excessive
noise. Control deviations can arise by chance and from estimator bias. The
experiment says nothing direct about subjective experience, physical fields,
physical time, causal relations, or genuine randomness.
