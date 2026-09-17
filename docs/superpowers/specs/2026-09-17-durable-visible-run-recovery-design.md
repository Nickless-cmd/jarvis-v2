# Durable Visible Run Recovery Design

## Status and Scope

This design extends `2026-09-17-visible-task-terminal-recovery-design.md`.
The existing design makes recoverable segment exits truthful. This addendum
closes the six remaining ways a visible user task can be lost:

1. process or container death;
2. cancellation or accidental supersession;
3. provider or model failure;
4. watchdog and execution-budget exhaustion;
5. research deadlines and worker-budget exhaustion;
6. unexpected runtime exceptions.

The objective is not to make every provider attempt immortal. Attempts and
stream segments remain bounded. The invariant is that a user task either
continues, waits for the user, is explicitly cancelled by the user, or ends
with a visible terminal failure and a preserved checkpoint. It never silently
becomes `completed` because infrastructure stopped.

## Chosen Architecture

Build on the existing `in_flight_runs` store, terminal policy, checkpoints,
and boot reconciler. Introduce one durable recovery coordinator rather than
six independent fixes. Moving all visible runs to a new external queue is out
of scope; patching each exit locally is rejected because it preserves multiple
sources of terminal truth.

The coordinator owns two decisions:

- `settle_segment`: classify and durably record how the current segment ended;
- `claim_recovery`: atomically claim one recoverable task for one process and
  start the next segment exactly once.

No caller may schedule continuation directly after this change. Callers report
evidence and consume the coordinator's decision.

## Durable Recovery Record

`in_flight_runs` remains the source of truth for unresolved visible work. Its
records gain backward-compatible fields:

- `task_id`: stable across continuation segments;
- `run_id`: current segment identifier;
- `status`: `running`, `recovering`, `waiting_for_user`, `cancelled`,
  `completed`, or `failed_terminal`;
- `exit_reason` and `failure_class`;
- `checkpoint_ref` and a bounded `checkpoint_summary`;
- `recovery_attempt` and `recovery_limit`;
- `recovery_owner`, `recovery_lease_until`, and `recovery_generation`;
- `next_attempt_at` for bounded backoff;
- `notice_pending` and `notice_delivered_at`;
- timestamps for creation, last progress, settlement, and recovery claim.

Writes remain atomic. Read-modify-write operations that change ownership use a
single process lock around load, compare, and save. A claim succeeds only when
the record is recoverable, the previous owner is dead or its lease expired,
and `next_attempt_at` has passed. The generation increments on every claim, so
late work from an old process cannot settle the new segment.

The record stores checkpoint references and compact recovery metadata, not the
entire token stream. A hard crash may lose the uncheckpointed token tail, but
must not lose the task, completed tools, or the latest durable conclusion.

## Unified Settlement

Every one of the six failure classes is normalized into `TerminalEvidence`
and passed through the terminal policy. The coordinator then performs the
state transition and side effects in this order:

1. save or locate the latest checkpoint and working conclusion;
2. atomically settle the durable recovery record;
3. stamp the operational visible-run outcome;
4. emit a typed recovery or terminal notice;
5. close the current SSE segment;
6. schedule recovery only after durable settlement succeeds.

`completed` requires positive completion evidence. `mark_completed` may no
longer erase records for generic failed or cancelled outcomes. Explicit user
cancellation records `cancelled`; successful completion records `completed`;
both may then be pruned after their notices and operational outcomes are
durable.

All settlement operations are idempotent by `(task_id, generation, run_id)`.
Duplicate callbacks, late provider pumps, and repeated boot reconciliation
must produce the same state without duplicate continuation.

## Failure-Class Policy

### Process or Container Death

Graceful shutdown settles owned active runs as `recovering` with reason
`shutdown`, checkpoints at the next safe boundary, and starts no new work.

After an ungraceful death, boot reconciliation identifies records whose
process owner is gone. It changes them from `running` to `recovering`, emits a
pending notice, and leaves them claimable. After application startup is fully
ready, the recovery dispatcher claims and resumes visible, non-autonomous
tasks automatically. Autonomous runs retain their existing scheduler cadence
and are only marked interrupted.

Startup never resumes work while dependencies are still initializing. A
bounded readiness delay and lease prevent duplicate recovery when API and
runtime services start together.

### Cancellation and Supersession

Only an explicit user Stop action, a recognized user stop instruction, or a
policy-required safety cancellation is terminal. It records `cancelled`,
invalidates any recovery lease, and prevents future automatic continuation.

A new user message while work is active is not cancellation by default. It is
delivered as a steer to the active run. If the active segment cannot accept a
steer, the new message is queued after the recovering segment; it must not
silently erase the previous durable record. Explicit restart/forget intent may
cancel and clear previous work because that is user authorization.

### Provider or Model Failure

Retryable failures first use the existing bounded same-provider retry and
provider failover. Non-retryable failures, breaker-open without fallback,
unsupported models, empty provider responses, context failures, and repeated
`finish_reason=length` settle the segment as `recovering`.

Recovery uses the configured visible model when viable, otherwise an approved
fallback provider. It resumes from the checkpoint and must not rerun completed
mutating tools. Exhausting the task recovery limit invokes one final no-tools
synthesis attempt. If synthesis also fails, the task becomes
`failed_terminal` with its checkpoint preserved and a visible reason.

### Watchdogs and Budgets

Provider silence, round deadlines, turn wall-clock limits, retry caps, relay
source timeouts, maximum rounds, empty-output limits, tool-only limits, and
no-progress gates are segment limits, not proof of task completion. They all
settle as `recovering` unless the forced synthesis provides positive completion
evidence.

The existing numeric limits remain unchanged initially. This work changes
their terminal semantics, not their resource-governance purpose.

### Research Limits

Research worker timeout, turn/token/tool budget exhaustion, and the research
wall deadline cancel only the affected workers. The orchestrator synthesizes
from collected evidence and reports explicit gaps. If no usable evidence or no
synthesis is available, the parent visible segment settles as `recovering`.

Research recovery retains the research run identifier, completed findings,
source ledger, and unfinished track list. Continuation starts only missing
tracks and never repeats completed paid workers. Research cancellation caused
by explicit user Stop remains terminal.

### Unexpected Runtime Exceptions

All ordinary exceptions flow through the same coordinator. The outer visible
run handler records the exception class and a redacted summary, checkpoints
partial work, emits a typed recovery notice, and schedules continuation.

`GeneratorExit`, task cancellation, and other non-`Exception` exits are
classified in `finally` as abandoned segments unless explicit user
cancellation is already durable. `SIGKILL`, interpreter abort, OOM, and host
power loss are recovered by owner-death reconciliation on the next startup.

Persistence failure is fail-closed for completion: if durable settlement
cannot be written, the runtime must not emit a successful terminal state. It
emits an infrastructure failure where possible and leaves the prior in-flight
record intact for boot reconciliation.

## Recovery Dispatcher

The dispatcher runs after application readiness and whenever a segment settles
as recoverable. It:

1. lists due recoverable visible tasks;
2. atomically claims one using a lease and generation;
3. persists the recovery notice before model dispatch;
4. starts a detached continuation carrying `task_id`, generation, checkpoint,
   original request, and unfinished intent;
5. renews the lease on progress;
6. settles the new segment through the same coordinator.

Dispatch is bounded globally and per session. One session may have only one
claimed visible task. Recovery backoff is deterministic and capped. A failed
spawn releases or expires the lease and remains visible as pending recovery;
it cannot disappear between threads.

## Stream and Client Contract

The in-memory event log remains the low-latency live transport. Durable task
state is authoritative across process death. On reconnect:

- if the live event log exists, the client replays it normally;
- if it vanished but the task is `recovering`, the API returns a recovery
  snapshot and the client attaches to the continuation segment;
- if recovery is exhausted, the API returns the durable terminal notice and
  checkpoint summary.

A synthetic `message_stop` closes only the dead segment. Its stop reason must
be `recovering` or `failed_terminal`, never `end_turn`.

## Observability

Every transition emits one structured event containing `task_id`, `run_id`,
generation, failure class, exit reason, attempt count, prior owner, new owner,
and whether a checkpoint exists. Required counters include:

- orphaned tasks discovered;
- recovery claims won, lost, expired, and duplicated;
- recovery success and terminal exhaustion by failure class;
- forced syntheses attempted and succeeded;
- explicit cancellations;
- settlement persistence failures.

User-facing notices state what happened and whether Jarvis is continuing. They
must not expose raw exception text or appear as model-authored prose.

## Compatibility and Rollout

Old `in_flight_runs` records are read with conservative defaults and upgraded
on first write. The change is guarded by one recovery-coordinator feature flag.
Shadow mode classifies and records proposed transitions without dispatching;
enforced mode enables claims and automatic continuation. Existing autonomous
run behavior and explicit cancellation remain unchanged.

The rollout order is:

1. durable schema and pure transition tests;
2. unified settlement wiring;
3. provider/watchdog/runtime normalization;
4. research recovery;
5. boot and live recovery dispatcher;
6. reconnect snapshot and observability;
7. shadow verification, then enforcement.

## Acceptance Criteria

- Killing the owning process mid-tool-round leaves a claimable record and the
  restarted service continues it exactly once.
- A graceful deploy stops at a safe boundary and resumes after readiness.
- Explicit Stop never restarts; a normal new message never silently cancels.
- Provider failure, watchdog expiry, retry exhaustion, loop limits, and runtime
  exceptions cannot produce `completed` without positive completion evidence.
- Research timeout preserves completed findings and resumes only unfinished
  tracks or synthesizes visible partial results.
- Recovery-chain exhaustion produces a visible `failed_terminal` notice with a
  checkpoint, not a blank response or clean completion.
- Duplicate settlement, duplicate boot reconciliation, and stale provider
  callbacks cannot start or settle a task twice.
- Focused fault-injection tests cover all six failure classes, process restart,
  lease expiry, and persistence failure.

