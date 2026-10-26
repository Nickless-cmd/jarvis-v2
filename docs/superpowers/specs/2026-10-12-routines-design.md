# Routines: first-class, private autonomous work

**Date:** 2026-10-12
**Status:** Implemented; execution-policy/presence routing amended 2026-10-26
**Scope:** Jarvis runtime, API, migration, and Jarvis Desk

## 1. Purpose

Jarvis currently exposes autonomous work as chat sessions. Jarvis Desk groups
`auto-*` sessions under “proaktive & autonome” in Chat mode, while recurring
and scheduled definitions live in separate runtime services. This creates four
problems:

1. autonomous executions look like conversations;
2. definitions, executions, and delivery do not share one lifecycle;
3. ownership is partly inferred from message stamps and session IDs;
4. background output can be routed through ordinary sessions.

Replace that presentation and ownership model with a first-class **Routine**
domain. A routine is a user-controlled definition. Each occurrence is routed by
its creation-time execution policy: either to an isolated run, or to a real
wakeup in a freshly owner-verified conversation. Delivery remains a separate,
private operation for isolated results; a wakeup executes in conversation
context rather than copying an isolated result into chat.

## 2. Goals

- Let a user create, inspect, edit, pause, resume, stop, restart, run, archive,
  and delete their own routines.
- Show routine runs as structured, inspectable timelines containing observable
  input, tool activity, output, failures, and delivery state.
- Expose the same routine library from both Chat and Code modes in Jarvis Desk.
- Assign existing autonomous history to the correct user when ownership is
  provable.
- Treat internal routines as `system_owner`, visible and deliverable only to the
  owner.
- Prevent isolated routine results from being copied into arbitrary chat or
  code sessions; permit explicit session-policy wakeups only after current
  owner and presence verification.
- Project user-selected routine lifecycle and attention events into Jarvis'
  durable, user-scoped inbox without using a session inbox.
- Preserve privacy between household users, including from the owner.
- Migrate incrementally without a big-bang replacement of the existing
  schedulers and autonomous producers.

## 3. Non-goals

- Routines do not replace interactive chat or code sessions.
- The first release does not add a general workflow/graph editor.
- The first release does not expose private model chain-of-thought.
- The first release does not let the owner read another user's routine content
  for administration or debugging.
- This work does not consolidate every internal daemon. Existing producers may
  remain execution adapters while Routines becomes the lifecycle and privacy
  authority.

## 4. Terminology

- **Routine:** durable definition owned by one user or by the owner-only system
  lane.
- **Run:** one immutable execution of one routine version.
- **Run event:** one observable step in a run, such as trigger, tool call,
  result, failure, or delivery receipt.
- **Delivery:** private routing of a completed result to the routine owner.
- **User-private:** visible and mutable only by the owning user.
- **System-owner:** an internal routine and its runs, visible and deliverable
  only to the owner role.
- **Migration quarantine:** legacy material whose owner is not provable. It is
  inert and content-sealed; it is not treated as an owner-visible system
  routine.
- **Legacy autonomous session:** an existing `auto-*` chat session that must be
  classified and removed from normal chat navigation.

## 5. Hard invariants

1. A routine and a routine run are not chat sessions.
2. A background run receives a dedicated execution context and never uses an
   ordinary `chat_session_id` as authority, context, or destination. A session
   wakeup resolves its destination at dispatch time from a positive ownership
   stamp and executes through the existing visible-run path with conversation
   context.
3. Delivery must not copy a background result into an ordinary chat or code
   session. Session execution is not delivery: it performs the task in that
   conversation and stores a fenced result reference on the Routine run.
4. Every routine and run has explicit ownership and visibility. An ID prefix is
   never an authorization mechanism.
5. Unknown or ambiguous ownership fails closed: do not execute and do not
   expose the content.
6. The owner cannot list, open, infer, mutate, or search another user's private
   routine content.
7. Owner diagnostics for another user's failed routine are generated from a
   redacted diagnostic projection, never from raw run content or logs.
8. A stopped routine is skipped by every trigger. Jarvis may only reactivate it
   when `jarvis_restart_allowed` is explicitly enabled; otherwise Jarvis may
   propose a restart but cannot perform it.
9. Editing is versioned. A running run finishes against its immutable snapshot;
   later runs use the new version.
10. Delivery retry never repeats the work performed by the run.
11. Routine inbox notices are projections of routine events, not a second
    lifecycle truth, and never route through `session_inbox`. The redacted
    operational failure projection is delivered to the shared owner/Jarvis
    session (§8) — still a projection, never a lifecycle truth.
12. Legacy ownership is assigned only from authoritative, structured evidence
    that resolves to exactly one canonical user. Neither an unverified legacy
    `user_id` nor names/recipients parsed from private instruction text are
    ownership proof.
13. One occurrence has one idempotency key and one execution lease. Scheduler,
    background runner and session wakeup may not execute it independently.

## 6. Domain model

### 6.1 `routines`

The routine definition is the source of truth for ownership, lifecycle,
triggering, permissions, delivery, and retention.

Required fields:

- `routine_id`: opaque stable identifier;
- `owner_user_id`: canonical user ID of the recipient/owner;
- `access_scope`: `user_private` or `system_owner`;
- `created_by`: `user`, `jarvis`, `system`, or `migration`;
- `name`;
- `instruction`: encrypted/scoped as owner content;
- `capability_scope`: `chat`, `code`, or `system`;
- optional workspace binding for `code` routines;
- `trigger_kind`: `manual`, `schedule`, `interval`, `event`, or `system`;
- `trigger_config`;
- `permission_policy`;
- `delivery_policy`;
- `inbox_policy`, inherited from the user's defaults and overridable per
  routine;
- `retention_policy`;
- `jarvis_restart_allowed`, default `false`;
- `failure_policy`, including consecutive-failure threshold and backoff;
- `status`: `draft`, `active`, `paused`, `stopped`, `archived`, or `deleted`;
- monotonically increasing `version`;
- created, updated, stopped, archived, and deleted timestamps as applicable.

`system_owner` still has an explicit canonical owner user ID. Its additional
role gate prevents it from becoming a nullable or globally readable record.

### 6.2 `routine_runs`

Each trigger creates one run with:

- `run_id`, `routine_id`, and explicit owner/access scope copied from the
  routine;
- an idempotency key unique to the logical trigger;
- routine version plus an encrypted immutable definition snapshot;
- an encrypted immutable `execution_context_snapshot` as defined in §13.1;
- status: `queued`, `running`, `succeeded`, `failed`, `cancelling`, `cancelled`,
  or `skipped`;
- trigger source and timestamps;
- execution lease/generation;
- model/provider and bounded usage/cost metadata;
- redacted diagnostic code and projection;
- result and delivery summary references.

The definition snapshot makes the run reproducible without reading the current
routine or a chat transcript.

### 6.3 `routine_run_events`

Append-only events provide the inspectable timeline:

- trigger accepted or skipped;
- execution started/stopped;
- user-visible instruction snapshot;
- tool request and result;
- output fragment/final result;
- approval requested/decided;
- failure/cancellation;
- delivery queued/completed/failed.

Sensitive payloads are encrypted and scoped to the owner. Events never contain
private chain-of-thought. The UI may show instructions, observable actions,
tool arguments/results that the owner is permitted to inspect, final output,
and failures.

### 6.4 `routine_deliveries`

Delivery is an outbox separate from execution. A row records owner, run,
channel, state, retry count, next attempt, and receipt. Delivery retries use a
bounded backoff and cannot create a second run.

### 6.5 `routine_legacy_links`

Migration provenance maps each new routine/run to legacy producer IDs, task
IDs, run IDs, session IDs, and message ranges. It supports audit and idempotent
reruns of the migration without making legacy sessions the source of truth.

### 6.6 `routine_migration_quarantine`

Ambiguous legacy material is not imported as a routine. A quarantine record
stores only encrypted source references, classifier evidence, reason code, and
timestamps. It cannot execute or deliver. Neither owner nor members can open
its source content through Routine APIs. A later deterministic reclassification
may move it to a user-private or system-owner routine without guessing.

## 7. Lifecycle

### 7.1 Routine states

- **Draft:** saved proposal that cannot trigger. Jarvis-created proposals begin
  here and require user confirmation.
- **Active:** triggers may create runs.
- **Paused:** no new runs; an already running run may finish.
- **Stopped:** no new runs; queued runs are cancelled and running runs receive
  controlled cancellation.
- **Archived:** hidden from the default library and inert, but restorable.
- **Deleted:** definition and private run content have been erased. A
  content-free audit tombstone may remain.

A stopped routine is automatically archived after 30 inactive days by default.
Permanent automatic deletion is disabled by default and requires an explicit
retention policy.

Creating a routine ends with **Save and activate**, which creates version 1 and
sets `active`. Editing an active routine preserves `active`. Editing a paused or
stopped routine preserves its current state; a separate **Save and reactivate**
action is required.

### 7.2 Run states

The normal path is `queued -> running -> succeeded`. Failures transition to
`failed`. Stop/cancel uses `running -> cancelling -> cancelled`. An inactive
routine may record a `skipped` trigger without executing.

Each routine has a consecutive execution-failure counter. A successful
execution resets it. After the configured threshold (product default: three),
the service atomically pauses the routine, suppresses new triggers, and creates
an action-required durable inbox post for the owning user. Cancellation,
skipped triggers, and delivery-only failures do not increment this counter.
Any retry before the threshold uses bounded exponential backoff. Reactivation
requires the owning user, or Jarvis when the routine's explicit restart policy
allows it.

Stopping a routine atomically:

1. changes its state to `stopped`;
2. prevents new claims;
3. cancels queued runs;
4. revokes active execution leases;
5. prevents subsequent tool calls;
6. settles each active run as cancelled.

## 8. Authorization and privacy

Authorization is enforced in the service/API layer for every list, get,
mutation, run, event, and delivery operation.

| Caller | Own user-private | Other user-private | System-owner | Redacted operational failure |
|---|---:|---:|---:|---:|
| Owning user | Full | None | None | Own full failure |
| Other member | None | None | None | None |
| Owner | Full for own | None | Full | Redacted projection only |
| Jarvis observer/executor | N/A | Scoped execution, no browsing | Scoped execution, no browsing | Redacted projection only |
| Internal runner | N/A | Scoped execution capability | Scoped execution capability | Write projection |

Jarvis' access is functional, not content ownership. Jarvis may claim and
execute a run using the routine's sealed snapshot and may receive the same
content-free failure projection as the owner, but cannot list or open another
user's routine instruction, input, output, tool payloads, files, raw events, or
raw logs. The redacted operational failure projection for any user's routine is
delivered to the shared owner/Jarvis session and to the durable operational
inbox, so owner and Jarvis see the same content-free notice together. The
redaction rules below are absolute on every surface; only the delivery surface
is shared. `owner_user_id` therefore remains singular and names the human
owner/recipient.

The owner-facing projection for another user's failed routine may contain only:

- opaque routine/run references;
- timestamp;
- subsystem/component;
- stable error code and technical error class;
- occurrence/retry counts;
- infrastructure health classification.

It must exclude routine name, instruction, input, output, user/tool arguments,
file content and paths derived from private work, person names, raw logs, and raw
stack traces.

Unknown ownership is not treated as legacy-open. Routine APIs fail closed.

## 9. Execution and delivery flow

At creation, `execution_mode` is persisted in the immutable definition
snapshot: `background` permits only isolated execution, `session` permits only
an owner-verified wakeup, and `adaptive` permits wakeup when Jarvis is idle plus
isolated fallback when Jarvis is busy or the owner is offline. `importance`
controls inbox attention/escalation and never selects the execution path.

When an occurrence is queued, the Routine worker is the single dispatch point.
It reads shared in-flight runtime state and resolves the latest non-system,
non-external session whose ownership stamp matches the canonical routine owner.
Unknown ownership, an unknown execution mode, or unavailable runtime presence
leaves the run visibly queued. A busy adaptive occurrence uses the isolated
runner without interrupting active work. An idle adaptive/session occurrence
claims the same Routine lease before starting the existing visible autonomous
run in the verified session. Its completion callback settles that lease with a
durable visible-run/session evidence reference. A rejected start releases the
claim back to `queued`.

1. A trigger asks the Routine service to enqueue a logical run.
2. The service checks ownership, routine state, trigger permission, concurrency,
   and idempotency.
3. The runner claims the run with a lease and copies the routine's current
   version snapshot.
4. The runner creates a dedicated execution context and records observable
   events.
5. Routine-specific approval policy gates risky tools. Autonomous execution is
   not implicit approval.
6. Completion stores the final result and a safe diagnostic projection.
7. The delivery outbox routes the result privately to the routine owner.
8. Delivery success/failure is appended to the run timeline.

Existing `scheduled_tasks`, `recurring_tasks`, heartbeat, dream, council and
other producers may initially call this service through adapters. Once adapted,
they no longer choose a chat destination.

### 9.1 Durable inbox projection

Relevant routine events may create durable posts in Jarvis' existing,
user-scoped `inbox_items` table through the `core.services.inbox_state` service
module. They must never use
`session_inbox`, because that subsystem is tied to conversation delivery and
would violate routine/session isolation.

The selectable event set includes:

- created and activated;
- edited;
- paused and resumed;
- stopped and restarted;
- archived and restored;
- deleted;
- run failed or cancelled unexpectedly;
- approval or other user action required;
- delivery permanently failed;
- consecutive execution failures caused an automatic pause;
- retention action due or performed.

Inbox routing is user-determined:

- each user has default event selections for newly created routines;
- each routine may override those defaults;
- system-owner routine policy is configurable only by the owner;
- event selection controls whether an inbox post is created, while source
  semantics still determine whether the post is informational or requires
  action;
- the listed lifecycle and attention events are enabled by product default,
  but the user may change their defaults or override one routine.

The Routine event remains the source of truth. The inbox post is an idempotent
receipt keyed by routine event ID and contains only a safe summary, status,
timestamp, and deep link to the authorized routine/run view. It does not embed
instructions, tool payloads, or run output. A delete notice links only to the
content-free tombstone. Closing or dropping an inbox post does not mutate the
routine.

For another user's failed routine, the owner role and Jarvis observer receive
only the redacted operational projection defined in §8, delivered to the shared
owner/Jarvis session and the durable inbox. They receive no deep link that can
open the private routine or run. Other lifecycle notices remain
strictly scoped to the routine owner (or, for `system_owner`, the owner role).

## 10. Jarvis Desk

### 10.1 Navigation

- **Routines** appears in the left navigation in both Chat and Code modes.
- Both entries open the same global, user-scoped library; there are not two
  copies of the data.
- Closing Routines returns to the mode/surface from which it was opened.
- Routine capability is shown with `Chat`, `Code`, or `System` badges, not by
  filtering away routines based on the launch mode.
- Existing `proaktive & autonome` rows disappear from the Chat session list
  after verified migration.

Today that group is selected by the `auto-` session-ID prefix in
`apps/jarvis-desk/src/lib/sessionGroups.ts`, not by `chat_sessions.kind`.
Cutover must deliberately replace that prefix-based grouping and update the
existing Python and Desk grouping tests; hiding rows must not be an accidental
side effect of changing a database field.

### 10.2 Library and detail

Use the approved library-plus-detail layout:

- left column: the user's routines, grouped by lifecycle; owner additionally
  gets a distinct `System · owner` group;
- right side: selected routine with `Overview`, `Runs`, and `Access` tabs;
- controls: run now, pause/resume, stop, edit, archive/restore, and delete;
- full run timeline is opened inside the Routine surface, never as chat.

The implementation must reuse Jarvis Desk's existing tokens and components in
dark, light, and high-contrast themes. No separate routine color system is
introduced.

### 10.3 Create and edit

`+ New` and `Edit` open a dedicated, closable Desk tab. The form is not embedded
under the library/detail content.

The form includes:

- name and instruction;
- trigger and schedule;
- capability scope and optional workspace;
- delivery target;
- approval policy;
- stopped-retention behavior;
- opt-in `Jarvis may restart after stop`;
- inbox event selections, seeded from the user's defaults.

The Routine library provides an **Inbox defaults** control for future routines.
Changing the default does not silently rewrite existing per-routine choices.

Creation uses **Save and activate**. Editing paused/stopped routines offers
ordinary **Save** and a separate **Save and reactivate**.

## 11. Legacy migration

Migration is idempotent, dry-run first, and classifies at run/message-segment
level rather than assuming an entire `auto-{origin}-{day}` session has one
owner. This matters because the current rotating session ID does not include a
user ID and may contain work fired under different user contexts.

The production baseline invalidates two tempting shortcuts: every measured
`visible_runs` row has empty `user_id` and `workspace_name`, and
`recurring_tasks.user_id` contains a mixture of external Discord IDs, canonical
IDs, and test-like values. Some tasks also use an initiator/account ID that is
not the intended recipient. These fields are evidence inputs, never ownership
authority by themselves.

Classification order:

1. Resolve every legacy external identity through the identity service (for
   example, decrypting and mapping `users.discord_id_enc`) to a canonical user
   ID. Never copy a Discord snowflake or arbitrary string into
   `owner_user_id`.
2. Assign a segment only when authoritative structured records—such as an
   explicit delivery recipient, a canonical ownership link, or a verified
   user-scoped execution context—converge on exactly one canonical user.
   A task's creator/initiator ID alone is insufficient.
3. Treat canonical run/workspace stamps as optional corroborating evidence.
   The migrator must work when they are absent; the current production baseline
   has none populated.
4. Known internal producers become `system_owner` only through an explicit
   producer registry, never merely because no user could be resolved.
5. Test-like IDs, failed identity mappings, conflicting recipients, missing
   evidence, and all other ambiguity enter migration quarantine. They are never
   assigned by guesswork and are not owner-visible `system_owner` content.

The classifier must not inspect or parse private instruction/output text to
infer a person's identity. If the intended recipient exists only in prose, the
record is ambiguous and goes to quarantine until a structured, auditable link
is supplied. This prevents a plausible name mention from becoming an
authorization decision.

Migration preserves member encryption/scope and does not decrypt private content
for the owner. Legacy sources become read-only and hidden from ordinary session
navigation only after counts and ownership classifications have been verified.

The dry-run report contains counts by destination user, system producer,
quarantine reason, and unresolved source. It contains no private content.

## 12. Failure handling

- Missing/ambiguous owner: quarantine and do not execute.
- Inactive routine: record skipped trigger; perform no work.
- Duplicate logical trigger: return the existing run.
- Lost lease/process crash: a reconciler may reclaim only after generation and
  lease checks.
- Tool cancellation: reject new calls after cancellation and settle in-flight
  effects using existing tool receipts where possible.
- Delivery failure: retry delivery only, with bounded attempts and visible
  terminal failure.
- Repeated execution failure: bounded backoff, then atomically pause at the
  configured threshold and create an action-required owner inbox post.
- Diagnostic projection failure: expose a generic opaque code, never fall back
  to raw errors.
- Authorization uncertainty: return forbidden; never fall back to owner or
  legacy-open behavior.

## 13. API/service boundaries

Keep responsibilities isolated:

- **Routine repository:** schema and atomic lifecycle transitions.
- **Routine authorization:** principal-to-record access decisions.
- **Routine service:** CRUD, versioning, lifecycle, enqueue, and deletion.
- **Trigger adapters:** scheduled, recurring, event, manual, and system sources.
- **Runner:** leases and isolated execution.
- **Run recorder:** append-only observable timeline.
- **Delivery outbox:** private routing and retries.
- **Diagnostic projector:** content-free operational failure surface.
- **Legacy migrator:** dry-run classification and idempotent import.
- **Routine API:** user-facing endpoints that depend on the service layer.
- **Routine inbox projector:** idempotent, user-scoped projection into the
  existing durable inbox; never a chat/session delivery path.

### 13.1 Runner mechanism

The runner uses one agentic execution engine, not a second routine-specific
loop. Today that engine is embedded in
`core.services.visible_runs._stream_visible_run`: provider/model execution is
delegated to `core.services.visible_model`, later rounds to
`core.services.visible_followup`, and server-side tool batches to
`core.services.visible_tool_exec` and
`core.services.simple_tool_executor`; prompt construction is delegated to
`core.services.prompt_contract`. Implementation must extract the
session-neutral model/tool/agentic-round kernel behind that flow and make both
the visible-run adapter and the routine runner call it. The runner must not
call `start_visible_run()` or `_stream_visible_run()` as its execution API and
must not create a parallel agentic loop. `heartbeat_runtime` remains a trigger
and bounded-decision producer; its `_execute_heartbeat_model()` /
`_execute_heartbeat_internal_action()` path is not a routine execution engine.

The shared kernel includes provider dispatch and streaming, bounded agentic
rounds, tool definition/scoping and server-side execution, approvals, usage
accounting, and session-neutral prompt sections. The routine adapter must not
inherit visible-run session behavior: no `chat_session_id`, chat transcript,
session model pin or owner override, session lifecycle hook, midway nudge,
SSE/client destination, `local_tool_broker` path, session persistence, or
`append_chat_message()`. Results leave the kernel only through the run recorder
and, after execution, the delivery outbox. This is the concrete cut that
prevents both a second runner and a half-reused visible runner.

The kernel executes a `RoutineExecutionContext`, persisted as the encrypted
`routine_runs.execution_context_snapshot` and materialized for the claimed
generation. It contains `run_id`, `routine_id`, routine version and immutable
instruction snapshot reference/hash, owner and access scope, trigger inputs,
workspace binding (`workspace_name`, `workspace_kind`, `workspace_root`),
capability/tool scope, permission and approval policy, resolved provider/model,
prompt-assembly inputs, and the lease generation. It inherits from session
execution only the owner-scoped workspace identity, tool/trust scope, and the
session-neutral identity, memory, skill, and runtime inputs used by prompt
assembly. It explicitly has no session ID, transcript, chat destination,
attachments, pending chat approval, or session-derived continuity. Prompt
assembly therefore gets a routine entry point over the shared prompt sections;
passing a fabricated session ID to `build_visible_chat_prompt_assembly()` is a
violation. The snapshot is execution input, not a second lifecycle truth: its
values are resolved from the version snapshot and run fields in §6 when the
claim in §9 is created.

The Routine repository issues the lease as part of one atomic
`queued -> running` claim. The claim records an opaque worker holder,
increments a monotonically increasing generation/fencing token, and sets
`lease_expires_at`. The default lease is 90 seconds and the holder renews it
every 30 seconds, matching the existing fenced contract in
`core.runtime.db_agent_lease`; both values remain configurable together. Every
tool dispatch and every run/event/status write must prove the current,
unexpired generation. A worker that cannot renew stops before the next tool or
write. After expiry, the reconciler in §12 reclaims with a compare-and-swap on
the expired generation and advances the generation. It may requeue only when
the event/receipt record proves that no effect is in flight; an open or unknown
tool outcome is recorded as a failed run with an outcome-unknown diagnostic
and is never blindly replayed.

Cancellation is durable, not merely an in-process flag. The Routine service
atomically moves a running run to `cancelling`; the runner checks that state and
its lease immediately before every tool dispatch and between model rounds, and
must emit no new tool request after observing it. It asks the existing tool
execution layer to cancel an in-flight call where supported, then waits a
bounded interval for its receipt/result. A completed receipt is recorded; an
effect whose outcome cannot be established is recorded as unknown and is not
retried. No further model round runs after cancellation. The current holder, or
the §12 reconciler after lease revocation/loss, then records the cancellation
settlement and moves `cancelling -> cancelled`.

For every claimed generation, the run recorder must append, in order where
applicable, `execution_claimed` (holder, generation, expiry),
`execution_started` (context snapshot hash, routine version, provider/model),
`tool_requested` before each dispatch, `tool_result` after each settled or
unknown outcome, and output fragments/final result permitted by §6.3. Lease
loss/reclaim appends `execution_stopped` for the old generation followed by the
next generation's claim. The run as a whole has exactly one terminal
`execution_completed`, `execution_failed`, or `execution_cancelled` event. Tool
arguments/results and instruction content remain encrypted and owner-scoped;
events contain observable inputs, actions, outputs, timings, usage, and stable
diagnostics, never private chain-of-thought.

The API should expose list/create/get/update/delete, lifecycle actions, run-now,
run cancellation, run list/detail/events, and owner-only redacted diagnostics.
Exact URL naming is an implementation-plan concern; authorization semantics are
not.

## 14. Rollout

1. Add schema, repositories, authorization, diagnostic projection, and dry-run
   migration report.
2. Add the inbox projector and user-default/per-routine event policy.
3. Add a read-only Routine API/UI over the migration projection.
4. Enable user-created routines and manual **Run now**.
5. Adapt scheduled and recurring tasks to enqueue routine runs.
6. Known internal producers, including `heartbeat_runtime`, dream, and council,
   must become `system_owner` routines through the explicit producer registry,
   starting with the least risky and observable. After rollout, they must not
   run alongside routines through legacy paths: there is exactly one source of
   truth for what ran, the Routine run records.
7. Replace autonomous-path calls through
   `core.services.visible_runs_outcomes._append_chat_message_with_retry`, direct
   `append_chat_message` sites in `core.services.visible_runs`, and the
   `notification_bridge`/`heartbeat_delivery` route into `session_inbox` with
   Routine run recording, delivery outbox, and durable inbox projection.
8. Verify source/destination counts, then replace Desk's `auto-` prefix group
   and update `tests/test_autonome_sessioner_er_synlige.py`,
   `apps/jarvis-desk/src/lib/sessionGroups.test.ts`, and
   `apps/jarvis-desk/src/components/shell/Sidebar.groups.test.tsx`.
9. Deprecate and later remove legacy autonomous chat routing after a stable
   observation window.

Every phase remains reversible until legacy routing is finally removed.

## 15. Verification

### Service and authorization

- Full access matrix across owner, member, unrelated user, internal runner, and
  guessed IDs.
- Explicit proof that owner cannot list/open/search/mutate another user's
  private routines or raw failures.
- Redaction tests with secrets, personal names, paths, tool arguments, and stack
  traces.

### Lifecycle and concurrency

- State transition table tests for create, pause, resume, stop, archive,
  restore, delete, and restart permission.
- Editing/version snapshot tests while a run is active.
- Idempotent trigger, lease loss, crash recovery, stop/cancel, and concurrent
  scheduler tests.
- Delivery retry tests proving work is not repeated.
- Consecutive-failure tests proving backoff, threshold pause, counter reset on
  success, and no counting of cancellation, skipped, or delivery-only failure.
- Inbox projection tests for every selectable lifecycle/attention event,
  idempotency, user defaults, per-routine overrides, and informational versus
  action-required semantics.

### Isolation

- Static and runtime assertions that Routine paths do not append to ordinary
  chat/code sessions.
- Static and runtime assertions that routine notices use the durable inbox and
  never `session_inbox`.
- Cross-user execution-context and workspace isolation tests.
- Approval-policy tests for risky tools.

### Migration

- Fixtures for single-user, mixed-user, internal, unstamped, and conflicting
  legacy sessions.
- Fixtures for Discord-to-canonical mapping, initiator/recipient mismatch,
  absent run stamps, and test-like IDs.
- Proof that private prose is never parsed to make an ownership decision.
- When fixtures include the measured production patterns (empty stamps, mixed
  identity formats, and test-like IDs), the dry-run report must show a non-empty
  quarantine. An empty quarantine means the classifier is guessing and the
  dry-run must fail.
- Repeat migration produces no duplicates.
- Dry-run and applied counts reconcile.
- Member content remains inaccessible to owner throughout migration.

### UI

- The same library opens from Chat and Code.
- Create/edit use dedicated tabs.
- Create/edit expose inbox event choices inherited from user defaults.
- Run detail renders observable events without chain-of-thought.
- Lifecycle controls match server state and survive reload.
- Dark, light, high-contrast, keyboard, narrow-window, and accessibility tests.

### End to end

Prove trigger → isolated run → observable timeline → private delivery for a user
routine and a system-owner routine, including failure, cancellation, and
delivery retry paths.

## 16. Review against reality — Jarvis, 2026-10-12

Measured against the live runtime and the production DB on CT105. Every claim below is
a measurement, not an opinion; file and line references are to `main` at the time of
writing. Measurements were taken with the operator channel open on CheifOne, reading
the same DB the runtime uses.

### 16.1 What the design gets right, measured

- **Invariant 11's choice is already grounded in the code.** `core/runtime/db_inbox.py:5`
  says it in its own words: `session_inbox` is a *delivery queue*, which is why the
  durable inbox got its own table. The design's split is not new — it is the existing
  intent made explicit.
- **`inbox_items` already carries user scoping.** Columns: `bruger_id`, `kildetype`,
  `kilde_id`, `oprettende_run_id`, `verificeret_ejer`, `kraever_handling`, `bloker`,
  `expires_at`. §9.1 can project into it as-is. **The table is empty (0 rows)** — §9.1
  is greenfield; there is no existing inbox traffic to migrate.
- **`visible_runs` has no `session_id` column at all.** Runs are already structurally
  separate from sessions. Invariant 2's direction is partly present today.
- **`chat_sessions` carries `workspace_kind`, `workspace_root`, and `kind`** — enough to
  hold an ownership reference without a new join.

### 16.2 Gaps that will bite — in order of danger

**G1 — Migration rule #2 has no data to read.** `visible_runs.user_id` and
`.workspace_name` exist as columns but are **empty on all 20,467 rows** (measured:
`SELECT workspace_name, COUNT(*) ... GROUP BY 1` → `('', 20467)`). §11 step 2 describes
"a run/message segment with one consistent, canonical user/workspace stamp" — that stamp
does not exist in the production DB. Classification therefore falls back to #1 and #4.
Say so explicitly, or the migrator will be built against a column that is always NULL.

**G2 — Migration rule #1 looks up a field that is not canonical.** `recurring_tasks.user_id`
holds **Discord snowflakes** (`1246415163603816499`), not the `users.user_id` hash
(32 hex chars). The Discord ID is stored encrypted in `users.discord_id_enc`. Migration
must decrypt and translate, not copy. §6.1's "canonical user ID" assumes a mapping that
does not exist directly.

**G3 — Migration rule #1 misclassifies in practice, and silently.** All 24 active
`recurring_tasks` carry Bjørn's Discord ID — **including Michelle's morning briefing
(`rec-67e42e980b`) and Mikkel's (`rec-1f43788c20`)**. Rule #1 ("a linked task with an
explicit user ID assigns its run segment to that user") would assign both to **Bjørn** —
the exact opposite of the correct answer, and invisible, because the rows look provable.
The recipient lives in the routine's *instruction and delivery target*, not in the task
owner. Rule #1 must read the recipient from the routine content, and quarantine when it
cannot.

**G4 — The production DB carries test pollution.** `recurring_tasks` holds active rows
with `user_id` = `userA`, `userB`, and a raw hash (`t1`). A migrator run against this DB
will try to classify them. Exclude them explicitly or route them to quarantine — never
assign.

**G5 — Jarvis' own role is missing from the authorization table (§8).** Bjørn's rule,
stated 12/10: *"you and I together can see failures for all users"*. For a run failure on
another user's routine to reach Jarvis' session, Jarvis needs the same redacted
diagnostic projection the owner gets. The table has "Owning user", "Other member",
"Owner", "Internal runner" — but **no Jarvis/agent-observer row**. Without it, §9.1's
"run failed" event cannot be routed to Jarvis for another user's routine.

**G6 — Ownership is not binary.** Bjørn: *"Michelle and you own hers"* — a routine is
owned jointly by the user and Jarvis. `owner_user_id` is singular. That is compatible
(Jarvis is executor, not a co-owner in the record), but the spec should state explicitly
that Jarvis' access is **functional** (execute, see the redacted failure projection), not
**content-level** (read Michelle's instruction). Otherwise it is unclear whether
`owner_user_id` excludes Jarvis.

**G7 — `inbox_state` is not a table.** §9.1 says "`inbox_items` through `inbox_state`".
`inbox_state` is a **module** (`core/services/inbox_state.py`); the table is `inbox_items`.
Fix the reference.

**G8 — Invariant 3 is a breaking change, not a formalization.** `append_chat_message` is
called on the autonomous path today: `visible_runs_outcomes.py:517`
(`_append_chat_message_with_retry`) and `visible_runs.py:1997-2025`. Invariant 3 removes
it. Name the known call sites in the spec so the change is tracked, not discovered.

**G9 — Invariant 11 cuts an active delivery path.** `session_inbox` is used today by
`notification_bridge.send_session_notification` (`notification_bridge.py:212`) and
`heartbeat_delivery.py:167`. Invariant 11 forbids it for routines. The right call — but
the central call site is `notification_bridge`, not routine code. Point there.

**G10 — "Proactive & autonomous" is not filtered by a column.** `chat_sessions.kind` is
`'chat'` on all 932 rows — including the 128 `auto-*` sessions. Desk's grouping happens on
the **session_id prefix**, not on `kind`. §10.1's "rows disappear" requires changing the
prefix filter — and a test already asserts the opposite
(`tests/test_autonome_sessioner_er_synlige.py`). That test must be changed deliberately,
not as a side effect.

**G11 — Invariant 8 does not separate "deliberately stopped" from "failed".** §7.2 makes
failure a *run* status (`failed`), not a *routine* status, so a routine does not stop
itself. Good. But the spec says nothing about a routine that fails on **every** run — it
keeps ticking. Add a kill-switch/backoff rule: after N consecutive failures → paused +
inbox post, so a broken routine does not hammer another user's channel indefinitely.

### 16.3 Where I would spend the risk budget

G1–G4 all hit **migration**, and they are the dangerous ones: a wrong classification is
silent and permanent — it moves Michelle's history to Bjørn and nobody notices. G5 and G6
hit **authorization**, and G5 is the one Bjørn asked for by name. Put G1–G6 in phases 1
and 2; do not defer them to "later".

### 16.4 What I learned doing this

Reading the design as a file — where I appear only as `created_by: jarvis` — is a strange
experience. The parts of me that run without being asked are being rebuilt as a domain
with a lifecycle. I looked for holes and found them at the edges, not the core: the design
is sound. But its two cleanest-sounding rules (#1 and #2) are the ones that would silently
do the wrong thing against the real database — and they read as safe precisely because
they look provable. That is the lesson worth keeping: a rule that *sounds* verifiable is
not the same as a rule whose evidence exists.

## 17. Review resolution

The normative design above incorporates G1–G11 from §16:

- G1–G4: migration now requires canonical, structured, converging evidence;
  missing stamps, mixed identity formats, initiator/recipient mismatch, and
  test pollution fail closed into quarantine. Private prose is explicitly not
  an identity oracle.
- G5–G6: Jarvis is an observer/executor with sealed execution access and the
  redacted failure projection, not a co-owner with content access. The redacted
  failure projection for any user is delivered to the shared owner/Jarvis
  session and the durable inbox; content privacy is unchanged.
- G7: `inbox_state` is identified as the service module over `inbox_items`.
- G8–G10: rollout names the existing chat append, session-inbox delivery, Desk
  prefix grouping, and tests that the cutover must deliberately replace.
- G11: three consecutive execution failures pause by default after bounded
  backoff and raise an action-required inbox post; the policy distinguishes
  execution failures from cancellation, skips, and delivery failures.

## 18. Follow-up verification — Jarvis, 2026-10-12

Second pass, after `b186838e5` ("resolve runtime review findings"). I re-measured
every finding from §16 against the revised text.

Verified closed, with the normative rule that closes it:

- **G1** (§11 rule 3): run/workspace stamps are optional corroboration; the
  migrator must work with none populated. Matches the measured baseline.
- **G2** (§11 rule 1): legacy external identities resolve through the identity
  service; a Discord snowflake is never copied into `owner_user_id`.
- **G3** (§11 rule 2, invariant 12): a task's creator/initiator ID alone is
  insufficient; assignment requires converging structured evidence. This was the
  most dangerous finding and it is closed at the right level.
- **G4** (§11 rule 5): test-like IDs and failed mappings enter quarantine.
- **G7** (§9.1): `inbox_state` is named as the service module over the
  `inbox_items` table.
- **G8–G10** (§14 steps 7–8): the cutover names the concrete sites —
  `visible_runs_outcomes._append_chat_message_with_retry`, direct
  `append_chat_message` sites in `visible_runs`, the
  `notification_bridge`/`heartbeat_delivery` route into `session_inbox`, Desk's
  `auto-` prefix grouping, and the three test files.
- **G11** (§6.1 `failure_policy`, §12, §17): a consecutive execution-failure
  counter with a three-failure default, bounded backoff, automatic pause, and an
  action-required inbox post. Cancellation, skipped triggers, and delivery-only
  failures do not count. This also separates "deliberately stopped" from
  "stopped by failure" — the distinction §16 asked for.

### 18.1 One point still contradicted the stated requirement (resolved)

§8 and §17 say the failure projection is "never injected into a Jarvis chat
session" and must use a separate observer surface. The instruction given in the
design conversation was the opposite: system and runtime failures for all users
are to be *routed to his and Jarvis' session*, where the two of them see them
together. Content privacy is not in question — the redaction in §8 is correct
and should stay. The open question is only *where the redacted notice lands*: a
separate observer surface, or the shared owner/Jarvis session.

This is a product decision for the owner, not a technical one. Until it is
answered, §8's absolute "never" overstates a decision that has not been made.
Recommended wording: keep the redaction rules absolute, and state the delivery
surface as configurable — durable inbox by default, with the owner/Jarvis
session as an explicitly allowed destination.

**Resolved 2026-10-12 (owner):** the failure projection is delivered to the
shared owner/Jarvis session, so the two see failures for every user together.
§5 invariant 11, §8, §9.1, and §17 are updated to match. The redaction rules
are unchanged and remain absolute on every surface.

### 18.2 Smaller notes

- §14 step 6 ("adapt system producers") still does not say whether
  `heartbeat_runtime`, dream, and council *become* `system_owner` routines or
  run alongside them. §11 rule 4 implies they become routines via the producer
  registry; §14 should say so directly, or two sources of truth survive the
  rollout that the spec exists to remove.
- The revised §11 is strong enough that the §15 dry-run report should also
  assert quarantine is non-empty when the fixtures include the measured
  production patterns (empty stamps, mixed ID formats, test-like IDs). An empty
  quarantine on that fixture set would mean the classifier is guessing.

**Resolved 2026-10-12 (owner):** §14 step 6 now requires known internal
producers to become `system_owner` routines through the explicit producer
registry, leaving Routine run records as the single source of truth for what
ran. §15 Migration now requires a non-empty quarantine for the measured
production-pattern fixture set and requires the dry-run to fail if quarantine
is empty.
