# World And Self Model Truth Design

**Date:** 2026-09-10
**Status:** Approved direction, implementation pending
**Scope:** World-model ontology, provider model identity, self-model history,
durable cadence, correction learning, retrieval, and visible prompt grounding.

## Problem

Jarvis currently mixes three different kinds of truth:

- conversation topics are persisted and surfaced as world-model facts;
- execution runs and generated self-descriptions are described as versions of
  Jarvis;
- the configured provider model is persisted as though it were the model that
  the provider actually served.

This produced a concrete failure on 2026-09-10. Jarvis had previously inspected
the public DeepSeek Harness but later claimed that the harness was unpublished.
When challenged about his own history, he first claimed that no earlier version
existed, then called 7,443 execution runs earlier versions. He found 634 private
self-model snapshots but did not compare them across the suspected provider
change. The snapshots did contain a visible language and work-mode shift.

The live data also shows structural drift:

- 16,974 runtime world-model signals, of which 16,972 are active
  `conversational_context` rows;
- a stale sweep that only examines the newest 40 rows;
- 22 private self-model snapshots written on 2026-09-10 despite a declared
  daily cadence;
- no active runtime self-model limitation signals;
- no persisted distinction between requested and provider-observed model IDs.

## Goals

1. Separate conversation topics, world facts, and predictions into distinct
   ontologies and storage/read paths.
2. Prevent conversation topics from being injected as world truth.
3. Retire or quarantine legacy conversational-context world rows without
   deleting historical evidence.
4. Record requested and provider-observed model identity for visible calls.
5. Represent model changes as evidence-bounded epochs, not asserted substrate
   changes.
6. Make self-model cadence durable across restarts and processes.
7. Store comparable, versioned self-model snapshots linked to their evidence
   and model epoch.
8. Provide self-history trend/diff retrieval as a first-class runtime surface.
9. Record explicit user correction as provisional self-knowledge immediately,
   with promotion requiring repeated support.
10. Route questions about Jarvis' history, backend, change, strengths, or
    limitations through the relevant truth surfaces before answering.

## Non-Goals

- Inferring exact provider weights from output style.
- Claiming that an alias change proves a physical model rollout.
- Rewriting old chat messages or deleting legacy runtime records.
- Turning conversation continuity into world truth.
- Letting generated self-description outrank runtime evidence or user-visible
  corrections.

## Truth Ontology

### Conversation topics

Conversation topics describe what a session is discussing. They support
continuity and retrieval only. They are not claims about the external world and
must never be rendered as `dominant_world_thread` or counted as active world
facts.

Existing `runtime_world_model_signals` rows with
`signal_type='conversational_context'` remain in place for audit history but are
excluded from all world-fact surfaces. New topics are written to a dedicated
conversation-topic store. A bounded migration marks legacy rows
`status='legacy_quarantined'` in batches, using a durable migration cursor so a
large table cannot block startup.

### World facts

A world fact is a bounded claim about the external or operational world with:

- a canonical key and normalized statement;
- source kind and source reference;
- observed timestamp and optional validity interval;
- confidence and verification status;
- contradiction/supersession links;
- evidence count and distinct-source count.

Facts are either `observed`, `reported`, `verified`, `contradicted`, `stale`, or
`superseded`. Conversation text can propose a reported fact, but cannot create a
verified fact by itself. Runtime observations and primary-source retrieval may
create observed or verified facts.

### Predictions

Predictions retain their existing separate lifecycle. They do not become facts
until resolved, and resolution records both the observation and outcome.

## Provider Model Observation And Epochs

Every provider call has two identities:

- `requested_model`: the configured/request payload model;
- `observed_model`: the model ID returned by the provider, when supplied.

The OpenAI-compatible SSE parser captures the top-level `model` field from any
chunk and emits it on the terminal event. The visible result and persisted run
store both fields. Existing `visible_runs.model` remains the requested model for
backward compatibility; new columns are additive.

Model epochs group consecutive observations by provider, requested model,
observed model, endpoint, and available provider fingerprint. An epoch contains
first/last observation times, evidence count, and confidence. A changed observed
model opens a new epoch. A documentation or catalog observation can annotate an
epoch, but cannot rewrite call evidence.

An epoch distinguishes:

- `alias_observed`: requested and observed IDs differ;
- `deployment_reported`: a provider source reports a deployment change;
- `substrate_verified`: reserved for an explicit immutable provider fingerprint
  or equivalent evidence.

The runtime must not infer `substrate_verified` from output quality, language,
timestamps, or an alias alone.

## Self-Model Snapshots

Private self-model records become explicitly versioned snapshots, not versions
of the entity. Additive metadata links each snapshot to:

- `snapshot_version`;
- `source_run_id` and `source_model_epoch_id` when available;
- an evidence digest and evidence window;
- producer instance and trigger;
- previous snapshot ID;
- a deterministic content hash.

The current self-model remains the latest accepted snapshot. A new comparison
service exposes field-level changes across two snapshots and trend windows. It
must label generated differences as interpreted evidence, never runtime truth.

The snapshot distiller continues to describe stable identity/work style, but its
input includes objective outcome aggregates and current model-epoch metadata.
Generated prose alone cannot establish that the substrate changed.

## Durable Cadence

Producer cooldown truth moves from process-local `_last_run_at` state to a
durable lease/checkpoint table keyed by producer name. Dispatch atomically claims
a due producer for a bounded lease. Completion stores the last successful run.
All API/runtime processes consult the same checkpoint.

The self-model distiller additionally uses a UTC day idempotency key. Restarts,
multiple processes, and failed lease owners cannot create more than one accepted
daily snapshot. Manual runs use a distinct explicit trigger and remain visible
as manual.

## Correction Learning

Explicit user feedback about Jarvis' capability, limitation, memory, or
self-report creates a provisional self-model signal immediately. It does not
require an existing reflective critic. The signal records the quoted evidence,
session, run, and canonical limitation key.

Promotion rules:

- one explicit correction: `uncertain`, confidence `medium`;
- repeated correction in a separate run or supporting runtime failure:
  `active`;
- later explicit improvement: `improving`, never silent deletion;
- contradiction: preserve both evidence paths and mark the conflict.

This keeps one complaint from becoming permanent identity while ensuring a
clear correction is not discarded.

## Retrieval And Prompt Grounding

Self/history queries are detected from intent, including variants of:

- previous/earlier version, before/after, changed, developed;
- what model/backend are you actually running;
- what are your limitations or strengths;
- what do you remember about your own prior behavior.

For these queries, prompt assembly adds a compact dynamic tail containing:

- current requested and observed model identity;
- current model epoch and evidence status;
- current self snapshot plus the nearest relevant prior snapshot/diff;
- active/provisional self-model corrections;
- relevant verified world facts and contradictions.

Conversation topics stay in the continuity/retrieval lane. They are never
rendered in the world-fact support block. When retrieved memory conflicts with a
fresh primary source, both are surfaced with timestamps and truth status.

## Migration And Compatibility

All schema changes are additive. Existing APIs keep `model` as the requested
model while exposing `requested_model` and `observed_model`. Legacy world rows
remain queryable for audit but disappear from active world-fact counts and
prompts immediately, even before quarantine migration finishes.

The migration runs in bounded batches and records progress. It is idempotent,
restart-safe, and must not run a table-wide write transaction during service
startup.

## Invariants

1. A conversation topic cannot appear in a world-fact prompt section.
2. A run is never described as a self-model version.
3. A self-model snapshot is never described as a provider substrate version.
4. Requested and observed model IDs are never silently collapsed.
5. Missing observed model remains `unknown`, not copied from requested model.
6. An alias mismatch cannot establish an exact substrate rollout.
7. At most one automatic accepted self snapshot exists per UTC day.
8. Producer cooldown survives service restart and is shared across processes.
9. Explicit correction produces a provisional self signal in the same turn.
10. Legacy conversational-context rows cannot dominate active world surfaces.
11. Historical records are quarantined or superseded, never silently deleted.
12. Prompt grounding states evidence status and contradictions explicitly.

## Testing

Focused tests must cover:

- SSE model capture when present and `unknown` when absent;
- requested/observed persistence through first and follow-up rounds;
- epoch opening, continuation, alias mismatch, and bounded claims;
- exclusion and batched quarantine of legacy conversation rows;
- conversation-topic persistence independent of world facts;
- durable cadence across simulated process restarts and concurrent claims;
- daily self-snapshot idempotency plus explicit manual snapshots;
- snapshot linkage, deterministic diff, and model-epoch association;
- immediate provisional correction and repeated-evidence promotion;
- prompt routing for self-history/backend questions;
- contradiction-aware world-fact retrieval;
- regression that the DeepSeek Harness fact cannot be displaced by a recent
  conversation topic carrying the opposite claim.

Verification is limited to affected suites plus Python compile checks. The full
repository suite is explicitly out of scope because it takes hours.

## Delivery Order

1. Introduce ontology stores and legacy exclusion/quarantine.
2. Capture provider-observed model identity and persist model epochs.
3. Add durable producer cadence and daily self-snapshot idempotency.
4. Version self snapshots and implement diff/trend retrieval.
5. Add provisional correction learning.
6. Add intent routing and truth-bounded prompt sections.
7. Run focused regressions, regenerate API documentation if required, and commit
   only the intended paths through the attribution wrapper.
