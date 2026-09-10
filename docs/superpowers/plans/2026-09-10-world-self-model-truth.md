# World And Self Model Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis evidence-bounded world facts, provider model epochs, durable self-model snapshots, correction learning, and retrieval that can truthfully compare his earlier and current state.

**Architecture:** Add focused persistence/services for conversation topics, world facts, model observations/epochs, and cadence checkpoints. Keep legacy columns and APIs compatible, filter legacy topic rows at read time, then wire versioned self-history and model identity into a query-gated dynamic prompt section.

**Tech Stack:** Python 3.11, SQLite, pytest, existing Jarvis prompt/runtime services.

**Spec:** `docs/superpowers/specs/2026-09-10-world-self-model-truth-design.md`

## Global Constraints

- Schema changes are additive and lazy/idempotent.
- Historical records are preserved; legacy topic rows are quarantined, never deleted.
- `visible_runs.model` remains the requested model for compatibility.
- Missing provider model identity remains unknown; it is never copied from the request.
- Alias evidence cannot be described as a verified substrate rollout.
- At most one automatic self-model snapshot is accepted per UTC day.
- Full-repository pytest is out of scope; run only affected suites and compile checks.
- Commits use `scripts/commit_with_attribution.py` with actor `codex`, origin `interactive`, and approval `bjorn`.

---

### Task 1: Separate Conversation Topics From World Facts

**Files:**
- Create: `core/runtime/db_world_self_truth.py`
- Create: `core/services/conversation_topics.py`
- Create: `core/services/world_facts.py`
- Modify: `core/services/cadence_producers.py`
- Modify: `core/services/world_model_signal_tracking.py`
- Modify: `core/services/prompt_support_signals.py`
- Test: `tests/runtime/test_db_world_self_truth.py`
- Test: `tests/test_conversation_topics.py`
- Test: `tests/test_world_facts.py`
- Modify: `tests/test_world_model_signal_tracking.py`
- Modify: `tests/test_prompt_contract.py`

**Interfaces:**
- Produces: `record_conversation_topic(...)`, `list_conversation_topics(...)`.
- Produces: `record_world_fact(...)`, `list_world_facts(...)`, `build_world_fact_prompt_section(...)`.
- Produces: `quarantine_legacy_world_topics(batch_size: int = 200) -> dict[str, int]`.
- Preserves: existing prediction APIs in `world_model_signal_tracking.py`.

- [ ] **Step 1: Write failing persistence and surface tests**

Test that topic records merge by canonical topic key, world facts preserve source/status/contradiction metadata, legacy `conversational_context` rows are excluded immediately, and quarantine changes at most `batch_size` rows per call.

- [ ] **Step 2: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/runtime/test_db_world_self_truth.py tests/test_conversation_topics.py tests/test_world_facts.py tests/test_world_model_signal_tracking.py`

Expected: failures because the new stores and legacy filter do not exist.

- [ ] **Step 3: Implement stores and bounded migration**

Create lazy idempotent tables:

```text
conversation_topics(topic_id, canonical_key UNIQUE, title, summary, source_kind,
session_id, run_id, support_count, session_count, created_at, updated_at)

runtime_world_facts(fact_id, canonical_key, statement, status, confidence,
source_kind, source_ref, observed_at, valid_from, valid_until,
contradicts_fact_id, supersedes_fact_id, evidence_count,
distinct_source_count, created_at, updated_at)

world_self_truth_migrations(migration_key PRIMARY KEY, cursor_id, completed_at,
updated_at)
```

Legacy filtering must be type-based, not dependent on migration completion.

- [ ] **Step 4: Route cadence topics and prompt facts**

Replace cadence producer world-signal writes with `record_conversation_topic`.
Replace `_world_model_support_signal_instruction` with the dedicated verified/
observed world-fact section. A reported-only fact may be shown only with an
explicit `reported` label and may not outrank verified facts.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command plus:

`/opt/conda/envs/ai/bin/python -m pytest -q tests/test_prompt_contract.py -k 'world_model or support_signal'`

- [ ] **Step 6: Commit Task 1**

Stage only Task 1 paths and commit through the attribution wrapper with message:
`fix(world-model): separate topics from world facts`.

---

### Task 2: Capture Provider Model Observations And Build Epochs

**Files:**
- Modify: `core/services/cheap_provider_runtime_streaming.py`
- Modify: `core/services/visible_model_types.py` or the existing module owning `VisibleModelResult`
- Modify: `core/services/visible_model_adapters.py`
- Modify: `core/services/visible_followup_adapters.py`
- Modify: `core/services/visible_runs_outcomes.py`
- Modify: `core/runtime/db_schema.py`
- Modify: `core/runtime/db_world_self_truth.py`
- Create: `core/services/provider_model_epochs.py`
- Modify: relevant visible-run API serializers that expose model identity
- Modify: `tests/test_cheap_provider_runtime_streaming.py`
- Test: `tests/test_visible_model.py`
- Test: `tests/test_visible_runs.py`
- Create: `tests/test_provider_model_epochs.py`

**Interfaces:**
- SSE done event adds `observed_model: str`.
- `VisibleModelResult` adds `observed_model: str = ""` without breaking callers.
- `visible_runs` adds nullable/empty `requested_model`, `observed_model`, and `model_epoch_id` columns.
- Produces: `record_model_observation(...) -> dict` and `current_model_epoch(...) -> dict | None`.

- [ ] **Step 1: Write failing SSE and epoch tests**

Cover a stream whose first chunk contains `model='deepseek-flash'`, a stream
without model metadata, repeated identical observations, alias mismatch, and a
changed observed model opening a new epoch.

- [ ] **Step 2: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/test_cheap_provider_runtime_streaming.py tests/test_provider_model_epochs.py tests/test_visible_model.py -k 'model or stream'`

- [ ] **Step 3: Capture and propagate observed model**

Capture the first non-empty top-level SSE `model` value and include it in the
terminal event. Never default it to the requested model. Propagate it through
first-pass and follow-up terminal results.

- [ ] **Step 4: Persist requested/observed identities**

Add lazy columns and populate `requested_model=run.model`,
`observed_model=result.observed_model`. Keep legacy `model=run.model`.

- [ ] **Step 5: Implement evidence-bounded epochs**

Create `provider_model_epochs` with epoch ID, provider, endpoint,
requested/observed model, fingerprint, evidence kind, first/last observed,
evidence count, and confidence. Expose claims as `alias_observed`,
`deployment_reported`, or `substrate_verified`; only immutable provider evidence
may create the last status.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 2 command plus the directly affected visible-run tests discovered
with `rg 'VisibleModelResult|visible_runs' tests`.

- [ ] **Step 7: Commit Task 2**

Commit Task 2 paths with message:
`feat(model-truth): persist observed provider model epochs`.

---

### Task 3: Make Cadence Durable And Self Snapshots Daily

**Files:**
- Modify: `core/runtime/db_world_self_truth.py`
- Create: `core/services/durable_cadence.py`
- Modify: `core/services/internal_cadence.py`
- Modify: `core/services/self_model_distiller.py`
- Test: `tests/test_durable_cadence.py`
- Modify: `tests/test_internal_cadence.py`
- Modify: `tests/test_self_model_distiller.py`

**Interfaces:**
- Produces: `claim_producer(name, cooldown_minutes, lease_seconds, now) -> ClaimResult`.
- Produces: `complete_producer(name, lease_token, succeeded, now) -> bool`.
- Produces: `claim_idempotency_key(scope, key, now) -> bool`.
- `_last_run_at` may remain as a cache/observable mirror but is not authoritative.

- [ ] **Step 1: Write failing restart and concurrency tests**

Use two independent SQLite connections to prove only one process claims a due
producer. Clear module memory and prove cooldown still applies. Prove expired
leases recover and failed runs do not become successful cooldown checkpoints.

- [ ] **Step 2: Write failing daily snapshot test**

Call the automatic self-model distiller twice with simulated process-local state
reset and assert only one accepted snapshot for the UTC day. Prove a manual
trigger uses a separate explicit idempotency scope.

- [ ] **Step 3: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/test_durable_cadence.py tests/test_internal_cadence.py tests/test_self_model_distiller.py`

- [ ] **Step 4: Implement transactional leases/checkpoints**

Use `BEGIN IMMEDIATE`, a random lease token, bounded lease expiry, and compare-
token completion. Persist last attempt, last success, lease owner/token/expiry,
and last result status.

- [ ] **Step 5: Integrate cadence and daily idempotency**

Claim before dispatch. Complete success/error after bounded execution. The
self-model automatic path claims `self-model-snapshot:<UTC date>` before calling
the LLM and records a visible skip reason when already accepted.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 3 command.

- [ ] **Step 7: Commit Task 3**

Commit Task 3 paths with message:
`fix(cadence): persist producer cooldown and snapshot claims`.

---

### Task 4: Version And Compare Self-Model Snapshots

**Files:**
- Modify: `core/runtime/db_private_states.py`
- Modify: `core/services/self_model_distiller.py`
- Create: `core/services/self_model_history.py`
- Modify: `core/services/runtime_self_model_builder.py`
- Modify: relevant Mission Control self-model route serializer
- Create: `tests/runtime/test_db_private_states.py`
- Modify: `tests/test_self_model_distiller.py`
- Create: `tests/test_self_model_history.py`

**Interfaces:**
- `record_private_self_model` accepts optional snapshot metadata with compatible defaults.
- Produces: `list_self_model_snapshots(limit, before, after)`.
- Produces: `compare_self_model_snapshots(older_id, newer_id) -> dict`.
- Produces: `build_self_model_history_surface(...) -> dict`.

- [ ] **Step 1: Write failing schema/linkage tests**

Assert monotonic snapshot versions, previous-snapshot linkage, deterministic
content hash, evidence digest/window, source run/model epoch, producer trigger,
and compatibility for old callers.

- [ ] **Step 2: Write failing diff/trend tests**

Assert field-level added/removed/changed values, unchanged fields, timestamp
ordering, nearest-before/after selection, and the label `interpreted_evidence`.

- [ ] **Step 3: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/runtime/test_db_private_states.py tests/test_self_model_distiller.py tests/test_self_model_history.py`

- [ ] **Step 4: Implement additive metadata and history service**

Migrate private self-model columns lazily. Determine next version inside the
write transaction. Hash normalized semantic fields plus evidence digest. Link
the current model epoch when available.

- [ ] **Step 5: Add bounded runtime/MC surface**

Expose current snapshot, prior comparable snapshot, diff, and trend summary.
Call them snapshots throughout; never versions of Jarvis or substrate evidence.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 3 command plus affected Mission Control route tests.

- [ ] **Step 7: Commit Task 4**

Commit Task 4 paths with message:
`feat(self-model): add versioned snapshot history and diffs`.

---

### Task 5: Learn Explicit Corrections Provisionally

**Files:**
- Modify: `core/services/self_model_signal_tracking.py`
- Modify: `core/runtime/db_runtime_self.py` only if additive evidence metadata is required
- Modify: `tests/test_self_model_signal_tracking.py`

**Interfaces:**
- Produces: deterministic `explicit_self_correction_candidate(message)`.
- Preserves existing critic-backed limitation and improvement paths.

- [ ] **Step 1: Write failing correction tests**

Cover Danish and English explicit corrections such as “du glemte at tjekke din
historik”, “du tog fejl om dine egne evner”, and “there is a problem with your
self model”. Assert one correction creates `uncertain/medium` immediately.
Assert neutral mentions and questions do not create limitations.

- [ ] **Step 2: Write failing promotion/conflict tests**

Assert a separate supporting run promotes the canonical signal to active,
improvement creates an improving edge, and contradictory evidence is retained
rather than overwritten.

- [ ] **Step 3: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/test_self_model_signal_tracking.py`

- [ ] **Step 4: Implement bounded deterministic extraction**

Require direct second-person/self-reference plus an explicit correction or
limitation predicate. Normalize a short canonical key without storing arbitrary
message text as identity. Persist quoted evidence and run/session provenance.

- [ ] **Step 5: Implement promotion and conflict preservation**

Merge support only across distinct run IDs. Promote after a second support or a
matching runtime failure. Preserve contradicted evidence in status reason and
support metadata.

- [ ] **Step 6: Run tests and verify GREEN**

Run the Step 3 command.

- [ ] **Step 7: Commit Task 5**

Commit Task 5 paths with message:
`feat(self-model): learn explicit corrections provisionally`.

---

### Task 6: Route Self-History And World Facts Into Prompt Grounding

**Files:**
- Create: `core/services/self_history_grounding.py`
- Modify: `core/services/prompt_sections/runtime_self_report.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `core/services/runtime_cognitive_conductor.py`
- Modify: `core/services/prompt_support_signals.py`
- Test: `tests/test_self_history_grounding.py`
- Modify: `tests/test_prompt_contract.py`
- Modify: `tests/test_cognitive_conductor.py`

**Interfaces:**
- Produces: `classify_self_history_query(text) -> QueryProfile`.
- Produces: `build_self_history_grounding_section(text, session_id) -> str | None`.
- Consumes: model epoch, self-history, correction, and world-fact surfaces.

- [ ] **Step 1: Write failing intent and prompt tests**

Cover prior version/snapshot, before-after, backend actually served, development,
strength, limitation, and remembered prior behavior. Assert unrelated messages
produce no section.

- [ ] **Step 2: Write failing truth-boundary regression**

Seed a verified fact that the DeepSeek Harness is public plus a newer
conversation topic claiming it is unpublished. Assert the prompt contains the
verified fact, labels any contradiction, and never renders the topic as world
truth.

- [ ] **Step 3: Write failing self-comparison regression**

Seed snapshots before/after a model epoch and assert the prompt calls them
interpreted self snapshots, reports requested/observed model IDs, and explicitly
states that alias evidence does not verify a substrate rollout.

- [ ] **Step 4: Run tests and verify RED**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q tests/test_self_history_grounding.py tests/test_prompt_contract.py tests/test_cognitive_conductor.py -k 'self_history or world_fact or backend or self_report'`

- [ ] **Step 5: Implement compact dynamic grounding**

Build a bounded dynamic-tail section, not a stable-prefix section. Prefer
verified/observed facts, include contradictions with timestamps, and include at
most current/prior snapshot plus one diff summary. Replace configured-only
backend wording with requested/observed wording.

- [ ] **Step 6: Remove remaining topic-as-world consumers**

Search all prompt and cognitive-frame consumers for
`runtime_world_model_signals` and ensure conversational-context rows cannot
reach a world-fact field. Keep prediction surfaces separate.

- [ ] **Step 7: Run all affected tests and compile checks**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest -q \
  tests/runtime/test_db_world_self_truth.py \
  tests/runtime/test_db_private_states.py \
  tests/test_conversation_topics.py \
  tests/test_world_facts.py \
  tests/test_world_model_signal_tracking.py \
  tests/test_cheap_provider_runtime_streaming.py \
  tests/test_provider_model_epochs.py \
  tests/test_durable_cadence.py \
  tests/test_internal_cadence.py \
  tests/test_self_model_distiller.py \
  tests/test_self_model_history.py \
  tests/test_self_model_signal_tracking.py \
  tests/test_self_history_grounding.py
/opt/conda/envs/ai/bin/python -m compileall -q core apps/api scripts
```

Also run the narrowly selected prompt, visible-run, and Mission Control tests
identified by the preceding tasks. Do not run the full repository suite.

- [ ] **Step 8: Regenerate generated API documentation if hooks require it**

Run: `/opt/conda/envs/ai/bin/python scripts/api_docs_gen.py`

Stage only generated pages changed by the new public interfaces.

- [ ] **Step 9: Commit Task 6**

Commit Task 6 and required generated docs with message:
`feat(prompt): ground self history in versioned runtime truth`.

---

### Task 7: Final Review And Migration Verification

**Files:**
- Modify only files required by review findings.
- Update: `docs/superpowers/specs/2026-09-10-world-self-model-truth-design.md` only if implementation exposes a resolved design ambiguity.

**Interfaces:**
- Consumes all prior task interfaces.
- Produces a clean branch with focused verification evidence.

- [ ] **Step 1: Inspect the complete branch diff against its base**

Check schema compatibility, bounded queries, transaction behavior, prompt size,
truth labels, and absence of broad table scans on visible hot paths.

- [ ] **Step 2: Run a temporary-database migration rehearsal**

Create a test DB containing legacy topic rows, legacy private self-model rows,
and legacy visible runs. Initialize the new services twice, run bounded
quarantine twice, and verify data preservation and idempotency.

- [ ] **Step 3: Run final affected verification**

Repeat Task 6 Step 7 plus `git diff --check` and the repository hook checks
triggered by an attribution commit. Do not run full pytest.

- [ ] **Step 4: Commit review fixes if any**

Use message: `fix(world-self-truth): address final review findings`.

- [ ] **Step 5: Report branch and commit sequence**

Do not merge or push without a separate explicit user request. Report focused
test counts, migrations exercised, residual risks, and the final branch tip.
