# Routines: first-class, private autonomous work

**Date:** 2026-10-12
**Status:** Approved design
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
domain. A routine is a user-controlled definition. A routine run is an isolated
execution. Delivery is a separate, private operation. None of these is a chat
session.

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
- Prevent routine content from being written into any ordinary chat or code
  session.
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
2. A run receives a dedicated execution context and never uses an ordinary
   `chat_session_id` as its context or destination.
3. Routine execution and delivery must not call `append_chat_message()` for an
   ordinary chat or code session.
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
    lifecycle truth, and never route through `session_inbox` or a chat session.

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
| Internal runner | Scoped execution capability | None | Scoped execution capability | Write projection |

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
user-scoped inbox (`inbox_items` through `inbox_state`). They must never use
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

Classification order:

1. A linked scheduled/recurring task with an explicit user ID assigns its
   corresponding run segment to that user.
2. A run/message segment with one consistent, canonical user/workspace stamp is
   assigned to that user.
3. Known internal producers such as heartbeat, dream, council, and internal
   self-maintenance become `system_owner`.
4. Conflicting, missing, or otherwise ambiguous evidence enters migration
   quarantine and is never assigned by guesswork. It is not owner-visible
   `system_owner` content.

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
6. Adapt system producers, starting with the least risky and observable.
7. Verify source/destination counts, then hide migrated autonomous sessions from
   Chat navigation.
8. Deprecate and later remove legacy autonomous chat routing after a stable
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
