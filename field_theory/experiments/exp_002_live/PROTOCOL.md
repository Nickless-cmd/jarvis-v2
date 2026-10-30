# Live Investigation 2: discovery and continuity in deployed observations

**Status:** protocol recorded before deployment and live extraction.

**Recorded:** 2026-10-30.

## Correction to the synthetic investigation

Investigation 2's synthetic run tested the discovery workflow against sources
whose generators were known to the code author. Its values are simulation
results, not measurements of Jarvis. This live investigation retains the
discovery/confirmation discipline while replacing generated sources with a
read-only deployed observation snapshot.

## Question

Which status relationships become detectable when the same deployed
visible-run records are represented through different operational metadata,
and which selected relationships persist into later observations?

## Sources and chronology

The high-water-bounded `visible_runs` extract is ordered by database row ID and
divided into five contiguous blocks of nearly equal size. Opaque source IDs are
used in the pre-reveal report. Within each block, the earlier half is discovery
and the later half is confirmation.

The blocks are observational eras, not independent randomized experiments.
Chronological persistence can be affected by deployments, provider changes,
traffic, outages, user behavior, or schema evolution. Confirmation here means
later held-out records under the fixed candidate, not universal replication.

## Candidate perspectives

The catalog contains:

- each of provider, model, lane, profile, capability presence, UTC hour band,
  and weekday alone;
- every pair as a joint categorical representation;
- terminal-status sequence lags 1 through 12.

This gives 40 mechanically enumerated candidates. The score is plug-in mutual
information with terminal status. The highest discovery score is selected;
ties use stable names. The top five are preserved to expose alternatives.

The catalog is deliberately limited. It does not search message content,
semantic meaning, arbitrary expressions, causal graphs, or user identity.
Failure to find structure means only that this catalog did not expose it.

## Search and confirmation controls

For each block, 250 discovery permutations recompute the maximum across all 40
candidates. This search-wide null represents the opportunity created by the
catalog. The selected candidate is then held fixed on the later half and
compared with 250 candidate-specific permutations.

Unrestricted outcome permutation assumes exchangeability. That assumption is
imperfect for chronological production data. A candidate involving status
lags especially may require block-preserving or generative controls in a later
investigation. The current null is retained as an explicit comparison, not
treated as neutral truth.

## Interpretation boundary

Persistent statistical dependence may be operationally useful, but is not
automatically causal or meaningful beyond the measured fields. A changing
relationship may indicate drift, sampling, deployment changes, or genuine
context dependence. Neither persistence nor failure validates or falsifies
Field Theory as a whole.
