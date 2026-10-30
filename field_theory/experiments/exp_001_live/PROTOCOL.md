# Live Investigation 1: fixed perspectives on deployed observations

**Status:** protocol recorded before deployment and live extraction.

**Recorded:** 2026-10-30.

## Correction to the original reference run

Experiment 001's synthetic run demonstrated the mechanics of fixed-perspective
measurement. It did not measure Jarvis. Its reported bit values remain valid
only for that preserved simulation and must not be cited as live-system
findings.

This investigation measures a read-only snapshot of the deployed CT105
`visible_runs` table. It does not modify Jarvis or use message text.

## Observation boundary

The extractor must execute on hostname `Jarvis` after the measurement code is
deployed. It opens `/home/bs/.jarvis-v2/state/jarvis.db` with SQLite `mode=ro`
and `PRAGMA query_only=ON`, begins one read transaction, records the maximum
visible-run row ID, and exports rows through that high-water mark.

Preserved fields are row ID, observation time, timestamp basis, provider, model, lane, profile,
capability presence, derived UTC hour band, derived weekday, and terminal
status. Message previews, errors, run IDs, user IDs, and workspace content are
excluded. Observation time uses `started_at`, falling back to `finished_at`
when the live row lacks a start time. Derived calendar fields, timestamp
fallback, and missing-value normalization are explicit extraction
transformations, not raw database facts.

## Fixed perspectives

The same terminal-status observations are measured as:

1. `outcome_ordering`: mutual information between adjacent statuses;
2. `provider_access`: mutual information between provider and status;
3. `provider_model_access`: mutual information between the joint
   `(provider, model)` state and status.

Five hundred outcome permutations preserve status counts and recorded context
while breaking row-wise and sequential relations. The complete null
measurements are retained. Quantiles and permutation ranks are descriptive,
not permanent decision thresholds.

The richer provider-model representation has more states and therefore more
finite-sample opportunity. A larger raw value is not automatically a better
explanation; its permutation distribution must be inspected.

## Claims this can and cannot support

The run can show whether operational status structure is detectable under
three specified representations in the deployed record. It cannot establish
causality, subjective perspective, experience, or a physical field. Provider
and model assignments changed historically, so detected relationships may
reflect deployment eras, routing, workload, or instrumentation rather than an
intrinsic source property.
