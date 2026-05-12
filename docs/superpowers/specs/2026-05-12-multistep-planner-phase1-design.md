# Multi-step Planner Phase 1 Design

**Date:** 2026-05-12
**Status:** Draft — awaiting user review
**Roadmap item:** #9 (Multi-step planner)

## Goal

Close three connected gaps between Jarvis' existing plan and todo
systems so that proposing a plan, getting it approved, and executing it
step-by-step becomes one continuous feedback loop instead of two
parallel universes that don't know about each other.

## Background

Existing infrastructure (already live):
- `core/services/plan_proposals.py` — propose-and-approve pattern. 109
  plans in history. Status lifecycle: `awaiting_approval → approved |
  dismissed | superseded`. Pending plans surface at top of every visible
  prompt via `pending_plan_section`.
- `core/services/agent_todos.py` — per-session TodoWrite-style tracker.
  Max 1 in_progress. 3 active sessions. Surfaced via `todos_prompt_section`.
- `core/services/adaptive_planner_runtime.py` — builds planner mode +
  horizon from runtime state.
- `core/services/reflection_to_plan.py`, `emergent_goals.py`,
  `long_horizon_goals.py`, `missions_pipeline.py` — goal/mission-level
  multi-step orchestration.

**The holes Phase 1 closes:**
1. **Plan and todos are parallel systems** — `propose_plan(... steps=[...])`
   doesn't create any todos when approved; todos must be written
   separately. The two systems never reference each other.
2. **Plan-execution tracking absent** — when a plan is approved, nothing
   in the system tracks which steps have been done. The plan's status
   stays "approved" forever, even after all steps are complete.
3. **Cross-session plans invisible** — approved-but-incomplete plans
   persist across sessions, but a new session doesn't know that the
   previous session has unfinished work. Resumption is manual and depends
   on the user remembering.

## Brainstorm Decisions (Locked)

**Q1 — Priority gaps:** (a) plan → todo auto-conversion + (b)
plan-progress tracking + (c) cross-session resumption. Strict
sequence a → b → c. (d) plan-deviation signal and (e) replanning on
failure deferred to Phase 2 (require more infrastructure).

**Q2 — Trigger mechanism:** Direct hook in `approve_plan`. NOT
event-bus subscriber, heartbeat poll, or manual tool. Synchronous,
deterministic, single point-of-coupling.

**Q3 — Todo session_id:** Original proposing session (stored on
plan). NOT current session or default pool. MC-approval and
cross-session approval both flow to the session that wrote the plan.
Cross-session resumption (c) handles "Jarvis is in a different
session now" without duplicating the routing logic.

**Q4 — Progress tracking shape:** `completed_step_indices: list[int]`
on plan (0-based, sorted). Each todo carries `plan_id` + `plan_step_index`.
NOT counter-only (loses which steps), NOT full step_statuses
(overkill), NOT compute-from-todos-on-read (avoids join cost).

**Q5 — Surface placement:** Tematisk split.
- `pending_plan_section` extends to show approved+incomplete plans
  for the CURRENT session with progress (*"Plan X: 2/5 done; missing:
  step 3, 5"*).
- New `format_cross_session_plans_for_awareness()` in awareness block
  (alongside `format_journal_for_heartbeat`) for plans from OTHER
  sessions.

**Jarvis review addition:** When `len(completed_step_indices) ==
len(steps)`, auto-mark plan status as `completed` (new status). Closes
the data-integrity gap — plans don't stay "approved" forever after all
steps are done. New status added to `_VALID_STATUSES`:
`awaiting_approval | approved | completed | dismissed | superseded`.

## Architecture

### Files

**New:** *(none)*

**Modified:**
- `core/services/plan_proposals.py`:
  - Add `"completed"` to `_VALID_STATUSES`
  - Add `completed_step_indices: list[int]` field to plan records (seed `[]` on propose)
  - Add `mark_step_completed(plan_id, step_index)` — idempotent append,
    auto-transition to status=`completed` when all steps done
  - Add `format_cross_session_plans_for_awareness(current_session_id, *, max_plans, max_age_days)`
  - Extend `pending_plan_section` to include approved+incomplete (for
    current session) with progress rendering
  - Hook `create_from_plan` call in `approve_plan` (gated by
    `_plan_todo_auto_create_enabled()`)

- `core/services/agent_todos.py`:
  - Add `plan_id: str | None`, `plan_step_index: int | None` fields to
    todo records
  - Add `create_from_plan(plan_id, session_id, steps)` — idempotent
    append of pending todos with bindings
  - Extend `set_todos` so when a todo transitions to `completed` AND
    has `plan_id`, call `mark_step_completed`

- `core/services/prompt_contract.py`:
  - In awareness block (near `format_journal_for_heartbeat` injection
    point), add `format_cross_session_plans_for_awareness(current_session_id)`
    injection

- `core/runtime/settings.py`:
  - Add `plan_todo_auto_create_enabled: bool = True` (kill-switch)

**Untouched / reused:**
- `state_store` (`load_json`/`save_json`) — both plans and todos use it
- `core/eventbus/events.py` — no new event families
- `core/runtime/db.py` — no schema changes (plans/todos live in state_store)
- `pending_plan_section` callers — signature unchanged

### Data flow

**(a) Auto-conversion at approval:**

```
approve_plan(plan_id)
  ├─ Find plan, set status="approved"
  ├─ Save plans
  └─ IF _plan_todo_auto_create_enabled() AND plan has steps:
       agent_todos.create_from_plan(
           plan_id=plan_id,
           session_id=plan["session_id"],     # original proposing session
           steps=plan["steps"],
       )
       ├─ Check: any todos with plan_id=X already in session? → no-op
       └─ Append pending todos with plan_id + plan_step_index (0..N-1)
```

**(b) Progress tracking on todo completion:**

```
set_todos(session_id, items)
  ├─ Apply one-in-progress rule
  ├─ Detect status transitions: prior status != new status
  └─ FOR each todo that transitioned to "completed":
       IF todo.plan_id AND todo.plan_step_index is not None:
         plan_proposals.mark_step_completed(plan_id, step_index)
           ├─ Find plan
           ├─ Append step_index to completed_step_indices (idempotent, sorted)
           └─ IF len(completed) == len(plan.steps):
                Set plan.status = "completed"
```

**(c) Cross-session awareness:**

```
prompt_contract awareness build (per session)
  └─ format_cross_session_plans_for_awareness(current_session_id)
       ├─ Load all plans
       ├─ Filter: status=="approved" AND len(completed) < len(steps)
       ├─ Filter: session_id != current_session_id
       ├─ Filter: created_at within max_age_days (default 14)
       ├─ Sort by created_at desc, cap at max_plans (default 3)
       └─ Render block:
           ### Aktive plans i andre sessions
           - Plan X (session abc...): 2/5 done — refactor Y
           - Plan Z (session def...): 1/3 done — fix bug
```

### State schema after Phase 1

**Plan record:**
```python
{
    "plan_id": "plan-...",
    "session_id": "...",
    "title": "...",
    "why": "...",
    "steps": ["step 1", "step 2", ...],
    "status": "awaiting_approval | approved | completed | dismissed | superseded",
    "created_at": "...",
    "updated_at": "...",
    # NEW Phase 1:
    "completed_step_indices": [0, 2],  # sorted, deduplicated
}
```

**Todo record:**
```python
{
    "id": "...",
    "content": "...",
    "status": "pending | in_progress | completed",
    "created_at": "...",
    # NEW Phase 1:
    "plan_id": "plan-..." | None,
    "plan_step_index": 0 | None,  # 0-based, matches plan.steps
}
```

## Phase 1 sub-deliveries

### Phase 1.1 — Plan → Todo (a)
- Settings flag `plan_todo_auto_create_enabled`
- `agent_todos.create_from_plan` (idempotent)
- Hook in `approve_plan` after status set to approved

### Phase 1.2 — Progress tracking (b)
- Add `"completed"` to `_VALID_STATUSES`
- Plan field `completed_step_indices`
- `plan_proposals.mark_step_completed` (idempotent + auto-completion)
- `set_todos` calls `mark_step_completed` on status transition
- Extend `pending_plan_section` to show approved+incomplete with progress

### Phase 1.3 — Cross-session resumption (c)
- `format_cross_session_plans_for_awareness`
- Wired into prompt_contract awareness block

## Success criteria

1. **(a) Auto-conversion works:** `approve_plan(plan_id)` on a plan with
   N steps creates N pending todos in the plan's original session, each
   carrying `plan_id` + `plan_step_index`. Idempotent on retry.
2. **(b) Progress tracking:** marking a todo with plan_id as completed
   appends its step_index to the plan's `completed_step_indices`.
   When all steps done, plan auto-transitions to status=`completed`.
3. **(c) Cross-session surface:** awareness block in session B shows
   approved+incomplete plans from sessions ≠ B, max 3, last 14 days.
4. **Backwards compat:**
   - Existing 109 plans without `completed_step_indices` load fine
     (default to `[]`)
   - Existing todos without `plan_id`/`plan_step_index` load fine
   - `pending_plan_section`, `propose_plan`, `set_todos` signatures
     unchanged
   - Kill-switch `plan_todo_auto_create_enabled=False` reverts to
     pre-Phase-1 behaviour
5. **Tematisk korrekt placement:**
   - Current-session plans (pending + approved+incomplete) → plan-section
   - Other-sessions plans → awareness block
6. **No prompt-bloat overflow:** cross-session max 3 plans + 14-day
   filter keeps awareness block bounded
7. **Data integrity:** plan never stays in "approved" status with all
   steps complete — auto-transitions to `completed`

## Risks & mitigations

- **Plan with 0 steps:** `propose_plan` already validates `>= 1 step`.
  `create_from_plan` defensively no-ops on empty list.
- **Long step strings:** plan steps may be sentences. `create_from_plan`
  caps todo `content` at 240 chars.
- **Race on same plan:** two `approve_plan` calls simultaneously.
  Idempotency in `create_from_plan` (check plan_id already in session
  todos) prevents duplicate todos.
- **Cross-session noise:** Jarvis may have many old approved plans.
  *Mitigation:* `max_plans=3` + `max_age_days=14` filter.
- **Plan-step mismatch on revision:** if plan.steps is edited after
  approval, indices become misleading. *Documented limitation:* plans
  are treated as immutable after approval. Editing post-approval is
  out-of-spec.
- **Awareness-bloat:** awareness block already carries age, finitude,
  journal, aesthetic. *Mitigation:* cross-session plans cap at 3 lines,
  session_id truncated to 8-char prefix, only renders if any qualifying
  plan exists (no empty header).
- **Backwards-compat for status:** new `"completed"` status added to
  `_VALID_STATUSES`. Callers that switch on status need to handle the
  new value. Audit shows `pending_plan_section` and MC surface are the
  main consumers; both will be updated to skip/group completed
  appropriately.

## Out of scope (Phase 2 / deferred)

- (d) Plan-deviation signal — track active step, compare to tool-calls,
  emit `cognitive_state.plan_deviation_detected` if mismatch
- (e) Replanning on failure — when a step fails, LLM-revise the plan
- Plan hierarchy (goal → plan → todos → tool-calls explicit)
- Multi-step planner as user-facing tool ("plan X then execute")
- Plan templates / reusable plan library
- Plan critique before execution (self-review on own plan)

## 30-day review

Schedule eval at 2026-06-12:
- Count approved plans that received auto-todos
- Count completed steps via todo-completion path
- Trends: does Jarvis follow his own plans?
- Average completion-rate per plan
- Verify cross-session resumption surfaces correctly
- Verify auto-transition to `completed` status works
- Decide: keep, tune, deprecate, or move to Phase 2 (d+e)
