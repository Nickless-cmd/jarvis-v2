# Session-Bound Background Continuation Design

## Intent

Work born in a conversation must keep that conversation as its authoritative home through execution, delivery, wake-up, and continuation. The purpose is to prevent a result from silently moving to whichever conversation happens to be active later, while preserving the distinct homes already used by side tasks, subagents, routines, and system initiatives.

## Goals

- Treat a non-empty origin session as authoritative; an unusable explicit origin waits with a visible reason instead of falling back.
- Preserve side-task lineage (`owner_user_id`, `origin_session_id`, `parent_run_id`, task id, evidence and autonomous policy) in its existing durable record.
- Characterize the existing subagent outbox/wait/recovery path and the existing routine/system-session separation.
- Prove single-flight, restart durability, session isolation, coalescing, idempotency, and user-stop behavior through the real service/database boundaries.

## Non-goals

- Do not put routines or sessionless system initiatives into a user conversation.
- Do not create a second result queue; agent results remain in `agent_result_outbox`, wake requests remain in the inbox/recovery journals, and side tasks remain in their existing durable store.
- Do not redesign autonomous visible runs or add decorative UI.

## Constraints

- Existing approval, workspace, ownership, tool-scope, and destructive-action gates remain authoritative.
- A sessionless producer may still use the existing owner/system resolver because it has no conversation origin to preserve.
- A side task is a deferred conversation continuation, not a subagent result envelope. A subagent result is executed independently and delivered through the durable outbox.
- Routines retain autonomous sessions and their structured delivery model.

## Approaches

1. **Extend the existing boundaries (selected).** Make explicit session routing fail closed, add missing side-task lineage to the existing record, and add contract tests across the current inbox/wait/recovery paths. This preserves the four existing models and changes only the broken boundaries.
2. **Move every producer into `agent_result_outbox`.** Rejected because side tasks, routines, and system initiatives do not share the subagent assignment lifecycle or result schema.
3. **Add a new background-delivery queue.** Rejected because the repository already has durable inbox, agent outbox, wait-contract, and recovery journals; another queue would create dual truth.

## Design

`pick_wakeup_run_target` keeps resolver fallback only when `record_session` is empty. If an explicit app origin is an external/inaccessible channel, it returns no target. Callers therefore leave their durable record pending and record the block/retry reason rather than redirecting it.

`side_tasks.flag` stores normalized lineage alongside the existing task id and autonomy policy. Backward-compatible `session_id` remains, while `origin_session_id` is the explicit semantic field. Existing callers need not change; missing values are derived from the current owner/run context when safely available.

Subagent completion continues to commit the assignment outcome and exactly one result envelope atomically, fire the registered wait contract, materialize a system-framed wake in `in_flight_runs`, and let `visible_run_recovery_dispatcher` start only when the origin session is free. Model-step claim remains filtered by owner and origin session.

The regression suite covers the twelve requested scenarios by category, and a deliberate routing mutation must make the origin-isolation test fail.

