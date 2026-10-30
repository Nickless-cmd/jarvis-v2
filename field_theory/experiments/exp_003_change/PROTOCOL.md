# Live Investigation 3: changing observable relationships

**Status:** protocol recorded before the deployed analysis run.

**Recorded:** 2026-10-30.

## Prompt and evidence status

Investigation 2 repeatedly selected `joint(model,weekday_utc)` in the final
three historical blocks, while its later-half plug-in mutual information
changed from 0.193991 to 0.073069 to 0.034201 bits. Investigation 3 asks what
changed without presuming that the relation itself weakened.

The 25,000-row extract has already been inspected. Every result in this
investigation is therefore retrospective and exploratory. Recalculation with
a new estimator or window is not independent confirmation.

## Immutable observation boundary

The analysis reuses the verified live extract with SHA-256
`b4:49:e4:93:d2:0b:17:31:da:85:48:72:2e:23:fc:b4:f6:30:1d:b3:b9:20:b6:6d:2f:49:ea:d7:1e:ce:ea:6e`.
It does not re-extract, edit, or append observations. The source was created on
CT105 from `/home/bs/.jarvis-v2/state/jarvis.db` using SQLite `mode=ro` and
`PRAGMA query_only=ON`. Its 365 `finished_at` timestamp fallbacks remain
explicit in the raw records.

## Primary changing-information view

The fixed perspective is status dependence on model and UTC weekday. A
2,000-row rolling window advances by 500 database-ordered observations. This
gives overlapping descriptive views, not independent samples. Each window
records:

- terminal-status entropy and non-completed prevalence;
- model and model×weekday state counts and sparse-state exposure;
- plug-in mutual information for model, weekday, and model×weekday;
- the incremental quantity `I(model, weekday; status) - I(model; status)`;
- joint MI divided by outcome entropy when entropy is nonzero;
- estimator references from 200 deterministic permutations.

Window sizes 1,000 and 4,000 are also calculated without permutation claims.
They are sensitivity views of the same inspected observations, not additional
tests. Non-overlapping 1,000-row blocks provide adjacent Jensen–Shannon
divergences for status and model composition; peaks are prompts for inspection,
not formal change points.

## Same information, changing measurement

Two permutation comparisons answer different questions:

1. A global outcome shuffle preserves marginal context and status counts but
   destroys chronology, clustering, and all row-wise relations. It mainly
   exposes finite-sample opportunity for the joint plug-in estimator.
2. A conditional calendar shuffle keeps every outcome and model at its
   original row and shuffles weekday only within model×calendar-month groups.
   It preserves model/status dependence, outcome clustering, monthly drift,
   and local model availability while disrupting exact weekday alignment where
   a group contains multiple weekdays.

The conditional null is used for the incremental weekday contribution. Its
mean is subtracted as a descriptive bias/reference adjustment. It is still not
a counterfactual operating history: weekday is derived from timestamps, group
sizes vary, and some rows cannot move between weekday states. The movable-row
fraction is recorded per window.

## Changing information and perspective together

The five 5,000-row historical blocks from Investigation 2 are retained only as
a comparability view. For each adjacent pair, smoothed categorical probability
models are fitted on the earlier complete block and scored on the next block:

- status prevalence only;
- model → status;
- model×weekday → status, with unseen joint states backing off to model and
  unseen models backing off to prevalence.

Cross-entropy in bits and exact-state coverage measure practical transport.
This is retrospective next-period evaluation, not fresh confirmation, because
the periods and relationship were selected after inspecting the dataset.

## Operational context boundary

An optional deployed context collector runs on hostname `Jarvis`, uses the same
read-only SQLite boundary, and filters records to the observation cutoff. It
exports only monthly counts from `provider_model_epochs` and
`central_incidents`; no messages, run IDs, session IDs, payloads, incident text,
or user fields are read. It also counts Git author dates by month. Author dates
show repository activity, not deployment time.

Only provider/model epochs whose recorded end is at or before the observation
cutoff are included; an epoch crossing the boundary is excluded because its
aggregate observation count cannot be split reliably. Coverage start and end
are part of the result. Missing early context must not
be replaced by narrative. Coincidence between a context count and a measured
change is not causal evidence.

## Interpretation boundary

The investigation can describe how an observed relation, population,
representation, and estimator co-vary. It cannot identify a physical field,
subjective experience, causal mechanism, or hidden information. A stable
number need not imply a stable process, and a changing number need not imply a
changing underlying relation.

## Post-primary audit boundary

If the primary rolling result exposes a localized peak, a separately invoked
audit may preserve model×weekday terminal-status counts for that maximum window
and the immediately preceding and following non-overlapping row intervals.
This audit is selected after seeing the primary result. It can show whether a
peak is broad or cell-concentrated, but it is neither preregistered discovery
nor confirmation.
