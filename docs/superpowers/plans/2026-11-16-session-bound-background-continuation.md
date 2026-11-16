# Session-Bound Background Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve authoritative conversation origin and prove automatic continuation across the existing side-task, agent, routine, and system-initiative paths.

**Architecture:** Tighten the shared routing boundary, enrich the existing side-task record, and characterize the already-durable agent wait/recovery path. No new queue or delivery subsystem is introduced.

**Tech Stack:** Python 3.11, SQLite, pytest, existing JSON state store and visible-run recovery services.

**Spec:** `docs/superpowers/specs/2026-11-16-session-bound-background-continuation-design.md`

## Global Constraints

- Explicit origin sessions never fall back to the owner's latest active session.
- Sessionless system initiatives retain their current resolver behavior.
- Reuse `agent_result_outbox`, inbox, `agent_wait_contracts`, and `in_flight_runs`; do not create a parallel queue.
- Preserve approval, workspace, ownership, permission, and destructive-action gates.
- Do not merge routines into conversation wake-ups.

## Review Focus

- Explicit external/deleted origins remain pending instead of redirecting to another app session.
- Two results arriving near-simultaneously cannot create concurrent turns in one session.
- A user-stopped parent cannot be restarted by a late child result.
- A restart between terminal commit and wake materialization cannot lose the result.
- Sessionless system work still resolves to its established autonomous/app home.

---

### Task 1: Authoritative origin routing

**Files:**
- Modify: `core/services/wakeup_dispatcher.py`
- Modify: `core/services/autonomous_side_task_dispatcher.py`
- Test: `tests/test_wakeup_dispatcher.py`
- Test: `tests/test_autonomous_side_task_dispatcher.py`

**Interfaces:**
- Consumes: `pick_wakeup_run_target(channel, record_session, app_resolver, owner_resolver, is_external)`.
- Produces: no-target for an unusable explicit app origin; resolver fallback only for empty origin.

- [ ] Write failing tests that an explicit external origin returns `None` and a side task with that origin remains queued with a block reason.
- [ ] Run the focused tests and verify the old fallback behavior fails them.
- [ ] Implement the minimal routing and side-task release behavior.
- [ ] Run the focused tests and existing wake/side-task suites.

### Task 2: Durable side-task lineage

**Files:**
- Modify: `core/services/side_tasks.py`
- Test: `tests/test_side_tasks.py`
- Test: `tests/test_autonomous_side_task_dispatcher.py`

**Interfaces:**
- Consumes: `flag(..., session_id, source_run_id, autonomy_mode, ...)` and current runtime identity when present.
- Produces: backward-compatible task records with `owner_user_id`, `origin_session_id`, and `parent_run_id`.

- [ ] Write a failing test that a flagged task persists explicit owner/session/parent lineage and autonomous policy.
- [ ] Run it and verify the lineage fields are absent.
- [ ] Add optional lineage parameters and safe derivation while retaining existing fields.
- [ ] Run focused side-task tests.

### Task 3: End-to-end continuation contract and mutation proof

**Files:**
- Create: `tests/test_session_bound_background_continuation.py`
- Modify: `DEVLOG.md`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes: real agent contract DB, wait contracts, wake intentions, recovery dispatcher, side-task store, and routine session behavior.
- Produces: executable characterization of the twelve requested scenarios.

- [ ] Add scenario tests for origin isolation, idle wake, busy deferral, closed-client behavior, restart materialization, coalescing, duplicate delivery, invalid origin, user stop, agent/side-task parity, and autonomous system/routine homes.
- [ ] Run the scenario file and address only observed contract gaps using TDD.
- [ ] Deliberately mutate explicit-origin routing, run the protected test to capture failure, restore the implementation, and rerun green.
- [ ] Update `DEVLOG.md` and `STATUS.md` in English with measured/derived/expected distinctions.
- [ ] Run targeted backend tests, syntax compilation, and relevant frontend tests if a frontend path changed.
- [ ] Commit only intended paths with the repository attribution wrapper and compare `origin/main` remote hash with `HEAD` without pushing.

