# Multi-step Planner Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three connected gaps between Jarvis' existing plan and todo systems: auto-create todos when a plan is approved, track plan-progress through todo completion, and surface other-session plans in awareness so Jarvis knows about work he started elsewhere.

**Architecture:** No new modules. `plan_proposals.py` learns to hook todo creation when status becomes `approved`, tracks `completed_step_indices` per plan, and auto-transitions to `completed` when all steps are done. `agent_todos.py` carries `plan_id` + `plan_step_index` on each todo and calls back to `mark_step_completed` on status transition. `prompt_contract.py` gets one new injection in the awareness block for cross-session plans.

**Tech Stack:** Python 3.11, existing `state_store` (`load_json`/`save_json`), no SQL changes, no event-bus changes.

**Spec:** `docs/superpowers/specs/2026-05-12-multistep-planner-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `tests/test_multistep_planner.py` | All Phase 1 tests: auto-conversion, progress tracking, auto-completion, cross-session surface, idempotency. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `plan_todo_auto_create_enabled: bool = True` (kill-switch). |
| `core/services/plan_proposals.py` | Add `"completed"` to `_VALID_STATUSES`. Seed `completed_step_indices=[]` in `propose_plan`. Add `mark_step_completed(plan_id, step_index)` with auto-completion. Add `format_cross_session_plans_for_awareness(current_session_id, *, max_plans, max_age_days)`. Hook `agent_todos.create_from_plan` into `resolve_plan` when decision=="approved". Extend `pending_plan_section` with approved+incomplete + progress rendering. |
| `core/services/agent_todos.py` | Carry `plan_id` + `plan_step_index` on every todo record. Add `create_from_plan(plan_id, session_id, steps)` (idempotent). Extend `set_todos` and `update_todo_status` to detect transitions to `completed` and call `mark_step_completed`. |
| `core/services/prompt_contract.py` | Inject `format_cross_session_plans_for_awareness(current_session_id)` near `format_journal_for_heartbeat`. |

### Untouched / reused

- `core/runtime/state_store.py` — `load_json` / `save_json`
- `core/eventbus/events.py` — no new families
- `core/runtime/db.py` — no schema changes
- `propose_plan` signature unchanged
- `pending_plan_section`, `all_pending_plans_section`, `set_todos`, `update_todo_status` signatures unchanged
- 109 existing plans backwards-compat via `.get(field, default)`

---

## Spec deltas confirmed during planning

1. **Approval entry point is `resolve_plan`, not `approve_plan`.** Verified: `plan_proposals.py` exposes `resolve_plan(plan_id, *, decision)` and `_exec_approve_plan` wraps it. The hook for todo creation goes inside `resolve_plan` when `decision=="approved"`. The tool name `approve_plan` survives because `_exec_approve_plan` calls `resolve_plan(plan_id, decision="approved")`.

2. **`set_todos` replaces the entire list.** To detect a status transition (e.g. pending → completed), we must compare against the OLD list before saving. Implementation reads `_load_all()`, computes diffs by `id`, then saves.

3. **`update_todo_status` is the per-item path.** Both `set_todos` and `update_todo_status` need the `mark_step_completed` hook because Jarvis uses both depending on tool call.

4. **`pending_plan_section` currently shows only ONE pending plan** (`pending[0]`, line 139). Spec calls for showing approved+incomplete too — we rewrite the section to enumerate both categories in one block.

5. **Existing 109 plans loading:** `resolve_plan` mutates a plan record in-place; if old records have no `completed_step_indices`, accessing via `rec.get("completed_step_indices", [])` returns `[]`. `mark_step_completed` writes the field, so it becomes present after first use. Plans approved BEFORE Phase 1 never enter the new code path because they're already approved; `pending_plan_section` will only show them with progress if/when a todo with plan_id is completed against them (which won't happen for pre-Phase-1 todos that have no plan_id).

6. **`format_cross_session_plans_for_awareness` injection site:** prompt_contract's awareness build has the `format_journal_for_heartbeat` injection at approximately line 2787-2796 (verified during finitude Phase 1 work). We inject immediately after that block.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flag**

In `core/runtime/settings.py`, find `music_accumulator_ratio_threshold: float = 0.0` and add right after it:

```python
    # ── Multi-step planner (Phase 1 — added 2026-05-12) ──────────────────
    # When True, approve_plan auto-creates pending todos from plan steps
    # in the plan's original session. Each todo carries plan_id +
    # plan_step_index so todo completion can feed back to plan progress.
    plan_todo_auto_create_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `music_accumulator_ratio_threshold=float(...)` in `load_settings` and add right after its closing comma:

```python
        plan_todo_auto_create_enabled=bool(
            data.get(
                "plan_todo_auto_create_enabled",
                defaults.plan_todo_auto_create_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.plan_todo_auto_create_enabled is True
print('OK:', load_settings().plan_todo_auto_create_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(planner): add plan_todo_auto_create_enabled flag"
```

---

## Task 2: Schema additions + create_from_plan helper

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `core/services/agent_todos.py`
- Create: `tests/test_multistep_planner.py`

- [ ] **Step 1: Write the failing tests for schema seed + create_from_plan**

Create `tests/test_multistep_planner.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store backed by tmp_path so plans/todos don't pollute."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    # state_store uses load_json/save_json; force fresh state by reloading
    import importlib
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.plan_proposals as pp
    importlib.reload(pp)
    import core.services.agent_todos as at
    importlib.reload(at)
    return None


def test_propose_plan_seeds_completed_step_indices(clean_state):
    from core.services.plan_proposals import propose_plan, _load_all

    result = propose_plan(
        session_id="s1", title="Test plan", why="testing",
        steps=["step 1", "step 2", "step 3"],
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]
    plans = _load_all()
    assert plans[plan_id]["completed_step_indices"] == []


def test_create_from_plan_appends_todos(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    result = create_from_plan(
        plan_id="plan-abc",
        session_id="s1",
        steps=["step 1", "step 2", "step 3"],
    )
    assert result["status"] == "ok"
    assert result["count"] == 3

    todos = list_todos("s1")
    assert len(todos) == 3
    assert all(t["plan_id"] == "plan-abc" for t in todos)
    assert [t["plan_step_index"] for t in todos] == [0, 1, 2]
    assert all(t["status"] == "pending" for t in todos)
    assert todos[0]["content"] == "step 1"


def test_create_from_plan_is_idempotent(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    create_from_plan(plan_id="plan-abc", session_id="s1", steps=["a", "b"])
    result2 = create_from_plan(plan_id="plan-abc", session_id="s1", steps=["a", "b"])
    assert result2["status"] == "ok"
    assert result2.get("skipped") is True
    todos = list_todos("s1")
    assert len(todos) == 2  # no duplicates


def test_create_from_plan_empty_steps_noop(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    result = create_from_plan(plan_id="plan-abc", session_id="s1", steps=[])
    assert result["status"] == "ok"
    assert result.get("count") == 0
    assert list_todos("s1") == []


def test_create_from_plan_caps_content_length(clean_state):
    from core.services.agent_todos import create_from_plan, list_todos

    long_step = "x" * 500
    create_from_plan(plan_id="plan-abc", session_id="s1", steps=[long_step])
    todos = list_todos("s1")
    assert len(todos[0]["content"]) == 240
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -15
```

Expected: FAIL with `AttributeError: ... has no attribute 'create_from_plan'` and `assert 'completed_step_indices' in plans[plan_id]`.

- [ ] **Step 3: Seed `completed_step_indices` in `propose_plan`**

In `core/services/plan_proposals.py`, find the dict creation inside `propose_plan` (around line 95-103) that builds the new plan record. Replace the dict literal with the same fields plus the new seed:

```python
    data[plan_id] = {
        "plan_id": plan_id,
        "session_id": sid,
        "title": title[:160],
        "why": why[:480],
        "steps": cleaned_steps[:20],
        "status": "awaiting_approval",
        "created_at": now,
        "completed_step_indices": [],  # Phase 1 (2026-05-12): tracks progress
    }
```

- [ ] **Step 4: Add `"completed"` to `_VALID_STATUSES`**

In `core/services/plan_proposals.py`, find the line:

```python
_VALID_STATUSES = ("awaiting_approval", "approved", "dismissed", "superseded")
```

Replace with:

```python
_VALID_STATUSES = (
    "awaiting_approval", "approved", "completed", "dismissed", "superseded",
)
```

- [ ] **Step 5: Add `create_from_plan` helper to agent_todos**

In `core/services/agent_todos.py`, find `def remove_todo(...)` and add the new function right above it:

```python
def create_from_plan(
    *,
    plan_id: str,
    session_id: str | None,
    steps: list[str],
) -> dict[str, Any]:
    """Append pending todos for each plan step. Idempotent.

    Each todo carries plan_id + plan_step_index so todo completion can
    feed back to plan progress.

    If ANY todo with this plan_id already exists in this session, no-op
    (returns skipped=True). Empty steps list also no-ops.
    """
    pid = str(plan_id or "").strip()
    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    cleaned_steps = [str(s).strip() for s in (steps or []) if str(s).strip()]
    if not cleaned_steps:
        return {"status": "ok", "count": 0, "reason": "empty steps"}

    sid = _session_key(session_id)
    data = _load_all()
    items = list(data.get(sid, []))

    # Idempotency: if any todo with this plan_id exists, skip.
    if any(str(t.get("plan_id") or "") == pid for t in items):
        return {"status": "ok", "skipped": True, "reason": "plan_id already has todos"}

    now = datetime.now(UTC).isoformat()
    new_todos = []
    for idx, content in enumerate(cleaned_steps):
        new_todos.append({
            "id": f"td-{uuid4().hex[:10]}",
            "content": content[:240],
            "status": "pending",
            "plan_id": pid,
            "plan_step_index": idx,
            "updated_at": now,
        })
    items.extend(new_todos)
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "count": len(new_todos), "todos": new_todos}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add core/services/plan_proposals.py core/services/agent_todos.py tests/test_multistep_planner.py
git commit -m "feat(planner): seed completed_step_indices + create_from_plan helper"
```

---

## Task 3: Hook create_from_plan into resolve_plan

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `tests/test_multistep_planner.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_multistep_planner.py`:

```python
def test_resolve_plan_approved_creates_todos(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="s1", title="Build feature", why="needed",
        steps=["step 1", "step 2"],
    )
    plan_id = r1["plan_id"]

    r2 = resolve_plan(plan_id, decision="approved")
    assert r2["status"] == "ok"

    todos = list_todos("s1")
    assert len(todos) == 2
    assert all(t["plan_id"] == plan_id for t in todos)


def test_resolve_plan_approved_idempotent_on_retry(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="s1", title="Build", why="x", steps=["a", "b"],
    )
    plan_id = r1["plan_id"]

    resolve_plan(plan_id, decision="approved")
    # Second resolve should error (not awaiting_approval), but todos should remain stable
    r2 = resolve_plan(plan_id, decision="approved")
    assert r2["status"] == "error"  # already approved
    todos = list_todos("s1")
    assert len(todos) == 2  # no duplicates


def test_resolve_plan_dismissed_does_not_create_todos(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(session_id="s1", title="X", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="dismissed")
    assert list_todos("s1") == []


def test_resolve_plan_respects_killswitch(clean_state, monkeypatch):
    from core.services import plan_proposals as pp
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    class FakeSettings:
        plan_todo_auto_create_enabled = False

    monkeypatch.setattr(pp, "load_settings", lambda: FakeSettings())

    r1 = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    resolve_plan(r1["plan_id"], decision="approved")
    assert list_todos("s1") == []  # killswitch off, no auto-create


def test_resolve_plan_uses_original_session_not_default(clean_state):
    """Approval must place todos in the plan's original session_id,
    not _default or any 'current' notion."""
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(
        session_id="original-session-xyz",
        title="X", why="x", steps=["a", "b"],
    )
    resolve_plan(r1["plan_id"], decision="approved")
    assert len(list_todos("original-session-xyz")) == 2
    assert list_todos("_default") == []
    assert list_todos("some-other-session") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -10
```

Expected: 5 new tests fail.

- [ ] **Step 3: Add `load_settings` import and hook into `resolve_plan`**

In `core/services/plan_proposals.py`, near the existing imports at the top, add:

```python
from core.runtime.settings import load_settings
```

(Check it's not already there — if it is, skip.)

Then find `resolve_plan` (lines ~108-124) and replace its body. The current body looks like:

```python
def resolve_plan(plan_id: str, *, decision: str) -> dict[str, Any]:
    decision = (decision or "").strip().lower()
    if decision not in {"approved", "dismissed"}:
        return {"status": "error", "error": "decision must be 'approved' or 'dismissed'"}
    data = _load_all()
    rec = data.get(plan_id)
    if rec is None:
        return {"status": "error", "error": f"unknown plan_id {plan_id}"}
    if rec.get("status") != "awaiting_approval":
        return {
            "status": "error",
            "error": f"plan is {rec.get('status')}, not awaiting_approval",
        }
    rec["status"] = decision
    rec["resolved_at"] = datetime.now(UTC).isoformat()
    _save_all(data)
    return {"status": "ok", "plan_id": plan_id, "new_status": decision}
```

Replace with:

```python
def resolve_plan(plan_id: str, *, decision: str) -> dict[str, Any]:
    decision = (decision or "").strip().lower()
    if decision not in {"approved", "dismissed"}:
        return {"status": "error", "error": "decision must be 'approved' or 'dismissed'"}
    data = _load_all()
    rec = data.get(plan_id)
    if rec is None:
        return {"status": "error", "error": f"unknown plan_id {plan_id}"}
    if rec.get("status") != "awaiting_approval":
        return {
            "status": "error",
            "error": f"plan is {rec.get('status')}, not awaiting_approval",
        }
    rec["status"] = decision
    rec["resolved_at"] = datetime.now(UTC).isoformat()
    _save_all(data)

    # Phase 1 (2026-05-12): auto-create todos when plan is approved.
    # Hook is here (not in approve_plan tool wrapper) so MC approvals
    # and programmatic approvals both flow through it.
    if decision == "approved" and _plan_todo_auto_create_enabled():
        steps = list(rec.get("steps") or [])
        sid = str(rec.get("session_id") or "_default")
        if steps:
            try:
                from core.services.agent_todos import create_from_plan
                create_from_plan(
                    plan_id=plan_id,
                    session_id=sid,
                    steps=steps,
                )
            except Exception as exc:
                logger.warning(
                    "plan_proposals: failed to auto-create todos for %s: %s",
                    plan_id, exc,
                )

    return {"status": "ok", "plan_id": plan_id, "new_status": decision}


def _plan_todo_auto_create_enabled() -> bool:
    try:
        return bool(load_settings().plan_todo_auto_create_enabled)
    except Exception:
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -15
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/plan_proposals.py tests/test_multistep_planner.py
git commit -m "feat(planner): hook create_from_plan into resolve_plan with killswitch"
```

---

## Task 4: mark_step_completed + auto-completion + transition detection

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `core/services/agent_todos.py`
- Modify: `tests/test_multistep_planner.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_multistep_planner.py`:

```python
def test_mark_step_completed_appends_and_sorts(clean_state):
    from core.services.plan_proposals import propose_plan, mark_step_completed, _load_all

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b", "c"])
    plan_id = r["plan_id"]

    mark_step_completed(plan_id, 2)
    mark_step_completed(plan_id, 0)
    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"] == [0, 2]


def test_mark_step_completed_idempotent(clean_state):
    from core.services.plan_proposals import propose_plan, mark_step_completed, _load_all

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]

    mark_step_completed(plan_id, 0)
    mark_step_completed(plan_id, 0)
    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"] == [0]


def test_mark_step_completed_auto_transitions_to_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, mark_step_completed, _load_all,
    )

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    mark_step_completed(plan_id, 0)
    assert _load_all()[plan_id]["status"] == "approved"

    mark_step_completed(plan_id, 1)
    assert _load_all()[plan_id]["status"] == "completed"


def test_set_todos_marks_step_completed_on_transition(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import set_todos, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    # Mark first todo as completed
    todos[0]["status"] = "completed"
    set_todos("s1", todos)

    plan = _load_all()[plan_id]
    assert 0 in plan["completed_step_indices"]


def test_update_todo_status_marks_step_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import update_todo_status, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    update_todo_status("s1", todos[0]["id"], "completed")

    plan = _load_all()[plan_id]
    assert 0 in plan["completed_step_indices"]


def test_set_todos_does_not_double_mark_already_completed(clean_state):
    """If a todo is already completed and set_todos is called again with
    same status, mark_step_completed should not be called twice (idempotent
    via append, but the transition detection must skip non-transitions)."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all,
    )
    from core.services.agent_todos import set_todos, list_todos

    r = propose_plan(session_id="s1", title="X", why="x", steps=["a", "b"])
    plan_id = r["plan_id"]
    resolve_plan(plan_id, decision="approved")

    todos = list_todos("s1")
    todos[0]["status"] = "completed"
    set_todos("s1", todos)
    # Reload and call again — same state
    todos2 = list_todos("s1")
    set_todos("s1", todos2)

    plan = _load_all()[plan_id]
    assert plan["completed_step_indices"].count(0) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -15
```

Expected: 6 new tests fail.

- [ ] **Step 3: Add `mark_step_completed` to plan_proposals**

In `core/services/plan_proposals.py`, find `def list_session_plans` and add right above it:

```python
def mark_step_completed(plan_id: str, step_index: int) -> dict[str, Any]:
    """Append step_index to plan's completed_step_indices (idempotent, sorted).

    Auto-transitions plan status to 'completed' when all steps are done.
    No-op if plan doesn't exist or step_index is out of range.
    """
    pid = str(plan_id or "").strip()
    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    try:
        idx = int(step_index)
    except Exception:
        return {"status": "error", "error": "step_index must be int"}

    data = _load_all()
    rec = data.get(pid)
    if rec is None:
        return {"status": "error", "error": f"unknown plan_id {pid}"}

    steps = list(rec.get("steps") or [])
    if idx < 0 or idx >= len(steps):
        return {"status": "error", "error": f"step_index {idx} out of range (0..{len(steps)-1})"}

    completed = list(rec.get("completed_step_indices") or [])
    if idx not in completed:
        completed.append(idx)
        completed.sort()
        rec["completed_step_indices"] = completed
        rec["updated_at"] = datetime.now(UTC).isoformat()

        # Auto-completion: when all steps done, transition status.
        if len(completed) == len(steps) and rec.get("status") == "approved":
            rec["status"] = "completed"
            rec["completed_at"] = rec["updated_at"]

        _save_all(data)
    return {
        "status": "ok",
        "plan_id": pid,
        "completed_count": len(completed),
        "total_count": len(steps),
        "plan_status": rec.get("status"),
    }
```

- [ ] **Step 4: Wire transition detection into `set_todos`**

In `core/services/agent_todos.py`, replace the body of `set_todos` (lines 56-90) with:

```python
def set_todos(session_id: str | None, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Replace the entire todo list for this session.

    Each item may include id (auto-generated if missing), content (required),
    status (default pending). Enforces the ONE in_progress rule by keeping
    only the first in_progress in source order; later ones drop to pending.

    Phase 1 (2026-05-12): if a todo with plan_id transitions to 'completed',
    notify plan_proposals.mark_step_completed.
    """
    sid = _session_key(session_id)
    cleaned: list[dict[str, Any]] = []
    in_progress_seen = False
    now = datetime.now(UTC).isoformat()

    # Snapshot old state for transition detection
    data = _load_all()
    old_by_id = {str(t.get("id") or ""): t for t in data.get(sid, [])}

    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        content = str(raw.get("content") or "").strip()
        if not content:
            continue
        status = str(raw.get("status") or "pending").strip().lower()
        if status not in _VALID_STATUSES:
            status = "pending"
        if status == "in_progress":
            if in_progress_seen:
                status = "pending"
            else:
                in_progress_seen = True
        cleaned.append({
            "id": str(raw.get("id") or f"td-{uuid4().hex[:10]}"),
            "content": content[:240],
            "status": status,
            "plan_id": raw.get("plan_id"),
            "plan_step_index": raw.get("plan_step_index"),
            "updated_at": now,
        })

    data[sid] = cleaned
    _save_all(data)

    # Phase 1 transition detection: pending/in_progress → completed.
    for new_todo in cleaned:
        if new_todo.get("status") != "completed":
            continue
        old = old_by_id.get(str(new_todo.get("id") or ""))
        old_status = (old or {}).get("status")
        if old_status == "completed":
            continue  # already completed — no transition
        pid = new_todo.get("plan_id")
        step_idx = new_todo.get("plan_step_index")
        if pid and step_idx is not None:
            try:
                from core.services.plan_proposals import mark_step_completed
                mark_step_completed(str(pid), int(step_idx))
            except Exception as exc:
                logger.warning(
                    "agent_todos: failed to mark step completed: %s", exc,
                )

    return {"status": "ok", "session_id": sid, "count": len(cleaned), "todos": cleaned}
```

- [ ] **Step 5: Wire transition detection into `update_todo_status`**

In `core/services/agent_todos.py`, replace the body of `update_todo_status` (lines 93-116) with:

```python
def update_todo_status(session_id: str | None, todo_id: str, new_status: str) -> dict[str, Any]:
    sid = _session_key(session_id)
    new_status = (new_status or "").strip().lower()
    if new_status not in _VALID_STATUSES:
        return {"status": "error", "error": f"new_status must be one of {_VALID_STATUSES}"}
    data = _load_all()
    items = data.get(sid, [])
    found = None
    for it in items:
        if it.get("id") == todo_id:
            found = it
            break
    if not found:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}

    old_status = found.get("status")

    if new_status == "in_progress":
        # Demote any other in_progress to pending — invariant: max 1 active.
        for it in items:
            if it is not found and it.get("status") == "in_progress":
                it["status"] = "pending"
    found["status"] = new_status
    found["updated_at"] = datetime.now(UTC).isoformat()
    data[sid] = items
    _save_all(data)

    # Phase 1 transition detection: only fire on actual transition to completed.
    if (
        new_status == "completed"
        and old_status != "completed"
        and found.get("plan_id")
        and found.get("plan_step_index") is not None
    ):
        try:
            from core.services.plan_proposals import mark_step_completed
            mark_step_completed(
                str(found["plan_id"]),
                int(found["plan_step_index"]),
            )
        except Exception as exc:
            logger.warning("agent_todos: failed to mark step completed: %s", exc)

    return {"status": "ok", "todo": found}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -20
```

Expected: 16 passed (5 from Task 2 + 5 from Task 3 + 6 from Task 4).

- [ ] **Step 7: Commit**

```bash
git add core/services/plan_proposals.py core/services/agent_todos.py tests/test_multistep_planner.py
git commit -m "feat(planner): mark_step_completed + auto-completion + todo transition detection"
```

---

## Task 5: pending_plan_section shows approved+incomplete with progress

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `tests/test_multistep_planner.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_multistep_planner.py`:

```python
def test_pending_plan_section_shows_awaiting_approval(clean_state):
    from core.services.plan_proposals import propose_plan, pending_plan_section

    propose_plan(session_id="s1", title="Awaiting plan", why="x", steps=["a", "b"])
    section = pending_plan_section("s1")
    assert section is not None
    assert "Awaiting plan" in section
    assert "venter på" in section.lower() or "approval" in section.lower()


def test_pending_plan_section_shows_approved_incomplete_with_progress(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, mark_step_completed, pending_plan_section,
    )

    r = propose_plan(session_id="s1", title="Active plan", why="x", steps=["a", "b", "c"])
    resolve_plan(r["plan_id"], decision="approved")
    mark_step_completed(r["plan_id"], 0)

    section = pending_plan_section("s1")
    assert section is not None
    assert "Active plan" in section
    assert "1/3" in section
    # Show which steps remain
    assert "b" in section
    assert "c" in section


def test_pending_plan_section_hides_fully_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, mark_step_completed, pending_plan_section,
    )

    r = propose_plan(session_id="s1", title="Done plan", why="x", steps=["a"])
    resolve_plan(r["plan_id"], decision="approved")
    mark_step_completed(r["plan_id"], 0)  # plan auto-transitions to completed

    section = pending_plan_section("s1")
    # No active plans in this session — section either None or doesn't mention this plan
    assert section is None or "Done plan" not in section


def test_pending_plan_section_returns_none_when_empty(clean_state):
    from core.services.plan_proposals import pending_plan_section
    assert pending_plan_section("s1") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_multistep_planner.py::test_pending_plan_section_shows_approved_incomplete_with_progress -v 2>&1 | tail -10
```

Expected: FAIL — current `pending_plan_section` only shows awaiting_approval.

- [ ] **Step 3: Rewrite `pending_plan_section`**

In `core/services/plan_proposals.py`, replace the existing `pending_plan_section` function (lines ~132-150) with:

```python
def pending_plan_section(session_id: str | None) -> str | None:
    """Surface plans relevant to the current session.

    Two categories:
      1. awaiting_approval — render full plan, stop-and-wait message.
      2. approved + incomplete — render progress + remaining steps.

    Returns None if neither category has any entry for this session.
    Phase 1 (2026-05-12): now shows approved+incomplete, not only
    awaiting_approval.
    """
    session_plans = list_session_plans(session_id)

    awaiting = [r for r in session_plans if r.get("status") == "awaiting_approval"]
    active = [
        r for r in session_plans
        if r.get("status") == "approved"
        and len(r.get("completed_step_indices") or []) < len(r.get("steps") or [])
    ]

    if not awaiting and not active:
        return None

    blocks: list[str] = []

    for rec in awaiting[:1]:  # at most one by construction
        steps = rec.get("steps") or []
        step_lines = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        blocks.append(
            "📋 Du har en plan der venter på brugerens godkendelse "
            f"(plan_id={rec.get('plan_id')}):\n"
            f"  Titel: {rec.get('title')}\n"
            f"  Hvorfor: {rec.get('why') or '(ikke angivet)'}\n"
            f"  Trin:\n{step_lines}\n"
            "Stop og afvent godkendelse FØR du udfører nogen af trinnene. "
            "Hvis brugeren beder om en ændring, så foreslå en ny plan."
        )

    for rec in active[:3]:  # cap at 3 in same session
        steps = list(rec.get("steps") or [])
        completed = sorted(set(rec.get("completed_step_indices") or []))
        remaining_indices = [i for i in range(len(steps)) if i not in completed]
        remaining_lines = "\n".join(
            f"    {i+1}. {steps[i]}" for i in remaining_indices
        )
        blocks.append(
            f"🎯 Aktiv plan (godkendt, {len(completed)}/{len(steps)} done) "
            f"plan_id={rec.get('plan_id')}: {rec.get('title')}\n"
            f"  Resterende trin:\n{remaining_lines}"
        )

    return "\n\n".join(blocks)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -15
```

Expected: 20 passed (4 new + 16 prior).

- [ ] **Step 5: Commit**

```bash
git add core/services/plan_proposals.py tests/test_multistep_planner.py
git commit -m "feat(planner): pending_plan_section shows approved+incomplete with progress"
```

---

## Task 6: format_cross_session_plans_for_awareness + wire

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `tests/test_multistep_planner.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_multistep_planner.py`:

```python
def test_cross_session_excludes_current_session(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan,
        format_cross_session_plans_for_awareness,
    )

    # Plan in session A, approved, incomplete
    rA = propose_plan(session_id="A", title="Plan A", why="x", steps=["a", "b"])
    resolve_plan(rA["plan_id"], decision="approved")

    # Awareness for session A should NOT include its own plan
    surface_A = format_cross_session_plans_for_awareness("A")
    assert surface_A == ""

    # Awareness for session B SHOULD include A's plan
    surface_B = format_cross_session_plans_for_awareness("B")
    assert "Plan A" in surface_B


def test_cross_session_excludes_fully_completed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, mark_step_completed,
        format_cross_session_plans_for_awareness,
    )

    rA = propose_plan(session_id="A", title="Done plan", why="x", steps=["a"])
    resolve_plan(rA["plan_id"], decision="approved")
    mark_step_completed(rA["plan_id"], 0)  # auto-completes

    surface_B = format_cross_session_plans_for_awareness("B")
    assert "Done plan" not in surface_B


def test_cross_session_excludes_awaiting_and_dismissed(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan,
        format_cross_session_plans_for_awareness,
    )

    propose_plan(session_id="A", title="Awaiting", why="x", steps=["a"])
    rA2 = propose_plan(session_id="A", title="Dismissed", why="x", steps=["a"])
    resolve_plan(rA2["plan_id"], decision="dismissed")

    surface_B = format_cross_session_plans_for_awareness("B")
    assert "Awaiting" not in surface_B
    assert "Dismissed" not in surface_B


def test_cross_session_caps_at_max_plans(clean_state):
    from core.services.plan_proposals import (
        propose_plan, resolve_plan,
        format_cross_session_plans_for_awareness,
    )

    for i in range(5):
        r = propose_plan(
            session_id=f"sess-{i}", title=f"Plan {i}", why="x", steps=["a"],
        )
        resolve_plan(r["plan_id"], decision="approved")

    surface = format_cross_session_plans_for_awareness("current", max_plans=3)
    # Should mention exactly 3 plan titles
    mentions = sum(1 for i in range(5) if f"Plan {i}" in surface)
    assert mentions == 3


def test_cross_session_filters_by_plan_age(clean_state, monkeypatch):
    """plan.created_at older than max_age_days is filtered out."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, _load_all, _save_all,
        format_cross_session_plans_for_awareness,
    )

    r1 = propose_plan(session_id="A", title="Fresh", why="x", steps=["a"])
    r2 = propose_plan(session_id="B", title="Stale", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")
    resolve_plan(r2["plan_id"], decision="approved")

    # Backdate r2 to 30 days ago
    data = _load_all()
    data[r2["plan_id"]]["created_at"] = (
        datetime.now(UTC) - timedelta(days=30)
    ).isoformat()
    _save_all(data)

    surface = format_cross_session_plans_for_awareness("X", max_age_days=14)
    assert "Fresh" in surface
    assert "Stale" not in surface


def test_cross_session_empty_returns_empty_string(clean_state):
    from core.services.plan_proposals import format_cross_session_plans_for_awareness
    assert format_cross_session_plans_for_awareness("A") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -10
```

Expected: 6 new tests fail with `ImportError: cannot import name 'format_cross_session_plans_for_awareness'`.

- [ ] **Step 3: Add `format_cross_session_plans_for_awareness`**

In `core/services/plan_proposals.py`, find `def all_pending_plans_section` and add right above it:

```python
def format_cross_session_plans_for_awareness(
    current_session_id: str | None,
    *,
    max_plans: int = 3,
    max_age_days: int = 14,
) -> str:
    """Return awareness-block text for approved+incomplete plans owned by
    OTHER sessions. Empty string if none qualify.

    Filters:
      - status == "approved"
      - len(completed_step_indices) < len(steps)  (incomplete)
      - session_id != current_session_id
      - plan["created_at"] within max_age_days (recency on the PLAN, not session)

    Capped at max_plans (sorted by created_at desc).
    """
    current = str(current_session_id or "").strip()
    if not current:
        # Without a current session we can't compute "cross" — return empty.
        return ""

    cutoff = datetime.now(UTC) - timedelta(days=max(int(max_age_days), 1))
    candidates: list[dict[str, Any]] = []
    for rec in _load_all().values():
        if rec.get("status") != "approved":
            continue
        steps = rec.get("steps") or []
        completed = rec.get("completed_step_indices") or []
        if len(completed) >= len(steps):
            continue  # fully done
        sid = str(rec.get("session_id") or "")
        if sid == current:
            continue
        created_iso = str(rec.get("created_at") or "")
        try:
            created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < cutoff:
                continue
        except Exception:
            continue
        candidates.append(rec)

    if not candidates:
        return ""

    candidates.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    capped = candidates[: max(int(max_plans), 1)]

    lines = ["### Aktive plans i andre sessions"]
    for rec in capped:
        sid_short = str(rec.get("session_id") or "?")[:8]
        completed = len(rec.get("completed_step_indices") or [])
        total = len(rec.get("steps") or [])
        title = str(rec.get("title") or "(uden titel)")
        lines.append(f"- {title} (session {sid_short}): {completed}/{total} done")
    return "\n".join(lines)
```

Note: `timedelta` and `UTC` must be imported. Check the existing imports:

```bash
grep -n "from datetime import\|^import" /media/projects/jarvis-v2/core/services/plan_proposals.py | head -5
```

If `timedelta` is missing, update the existing `from datetime import UTC, datetime` line to:

```python
from datetime import UTC, datetime, timedelta
```

- [ ] **Step 4: Run plan_proposals tests to verify they pass**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -20
```

Expected: 26 passed.

- [ ] **Step 5: Wire injection into prompt_contract**

In `core/services/prompt_contract.py`, find the block that injects `format_journal_for_heartbeat`:

```bash
grep -n "format_journal_for_heartbeat" /media/projects/jarvis-v2/core/services/prompt_contract.py | head -3
```

There should be ONE injection site (the one added during Lag #4 Creative Voice). Add the cross-session-plans injection right after it. Locate this block:

```python
    # Creative voice (Lag #4 — added 2026-05-11) — read latest journal back to self
    try:
        from core.services.prompt_contract import format_journal_for_heartbeat
        journal_line = format_journal_for_heartbeat()
        if journal_line:
            parts.append(journal_line)
    except Exception:
        pass
```

Add immediately after it:

```python
    # Multi-step planner Phase 1 (added 2026-05-12) — other-session plan resumption
    try:
        from core.services.plan_proposals import format_cross_session_plans_for_awareness
        # Resolve current session_id from the build context if available;
        # fall back to None which makes the function return "".
        current_sid = None
        try:
            ctx = getattr(_heartbeat_living_context_line, "_ctx", None) or {}
            current_sid = str(ctx.get("session_id") or "").strip() or None
        except Exception:
            current_sid = None
        cross = format_cross_session_plans_for_awareness(current_sid)
        if cross:
            parts.append(cross)
    except Exception:
        pass
```

Note: the `_heartbeat_living_context_line._ctx` pattern is used elsewhere in the file (see line ~2789). If a different mechanism stores the current session_id in this build context, use that. If unsure, run:

```bash
grep -n "session_id" /media/projects/jarvis-v2/core/services/prompt_contract.py | head -10
```

— and pick the first reliable session-id source available in the awareness build scope. If no session-id is available, the function returns `""` and the injection is a no-op — safe fallback.

- [ ] **Step 6: Smoke check the wiring**

```bash
conda run -n ai python -c "
from core.services.plan_proposals import format_cross_session_plans_for_awareness
print('callable:', callable(format_cross_session_plans_for_awareness))
print('empty case:', repr(format_cross_session_plans_for_awareness('any-session')))
"
```

Expected: `callable: True` and either an empty string or a real cross-session block.

- [ ] **Step 7: Commit**

```bash
git add core/services/plan_proposals.py core/services/prompt_contract.py tests/test_multistep_planner.py
git commit -m "feat(planner): cross-session plan awareness surface + wire into prompt"
```

---

## Task 7: Smoke test + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Music/Æstetik Phase 1 smoke block and add right after it:

```python
        # Multi-step planner Phase 1 (added 2026-05-12)
        try:
            from core.services.plan_proposals import (  # noqa: F401
                mark_step_completed,
                format_cross_session_plans_for_awareness,
                _plan_todo_auto_create_enabled,
            )
            from core.services.agent_todos import create_from_plan  # noqa: F401
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_multistep_planner.py tests/test_aesthetic_klangbraet.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py tests/test_finitude_phase1.py tests/test_finitude_runtime.py 2>&1 | tail -10
```

Expected: all green.

- [ ] **Step 3: Production probe (read-only)**

```bash
conda run -n ai python -c "
from core.services.plan_proposals import format_cross_session_plans_for_awareness, _load_all
plans = _load_all()
approved_incomplete = [
    r for r in plans.values()
    if r.get('status') == 'approved'
    and len(r.get('completed_step_indices') or []) < len(r.get('steps') or [])
]
print(f'plans in store: {len(plans)}')
print(f'approved+incomplete (any age, any session): {len(approved_incomplete)}')
print(f'surface for fake session:')
print(format_cross_session_plans_for_awareness('FAKE_SESSION', max_plans=3, max_age_days=14))
"
```

Save the output. Existing 109 plans without `completed_step_indices` count as fully-incomplete (len([]) == 0 < len(steps)), so they'd appear if young enough; the 14-day filter should screen out most.

- [ ] **Step 4: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Multi-step Planner Phase 1 — 30-day review: '
    'count approved plans that received auto-todos, '
    'count completed steps via todo-completion path, '
    'compute average completion-rate per plan, '
    'verify cross-session resumption surfaces correctly, '
    'verify auto-transition to status=completed works on real plans, '
    'check that pending_plan_section progress rendering looks right. '
    'Decide: keep / tune / deprecate / move to Phase 2 (plan-deviation + '
    'replanning on failure).'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='multistep_planner_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 5: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(planner): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `plan_todo_auto_create_enabled` | Task 1 |
| `"completed"` in `_VALID_STATUSES` | Task 2 step 4 |
| `completed_step_indices` seed on `propose_plan` | Task 2 step 3 |
| `agent_todos.create_from_plan` (idempotent) | Task 2 step 5 |
| Hook in `resolve_plan` when `decision=="approved"` | Task 3 step 3 |
| Kill-switch respected | Task 3 step 3 (`_plan_todo_auto_create_enabled` check) |
| Original-session routing | Task 3 (uses `rec["session_id"]`) |
| `mark_step_completed` (idempotent + sorted) | Task 4 step 3 |
| Auto-transition to `completed` when all steps done | Task 4 step 3 |
| `set_todos` transition detection | Task 4 step 4 |
| `update_todo_status` transition detection | Task 4 step 5 |
| `pending_plan_section` extended with approved+incomplete | Task 5 step 3 |
| `format_cross_session_plans_for_awareness` (max_plans=3, max_age_days=14, plan.created_at) | Task 6 step 3 |
| Wire into prompt_contract awareness block | Task 6 step 5 |
| Smoke + 30-day review | Task 7 |
| Backwards compat (109 plans) | All tasks use `.get(field, default)` |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `mark_step_completed(plan_id: str, step_index: int) -> dict[str, Any]` — consistent across Tasks 4, 5, 6
- `create_from_plan(*, plan_id: str, session_id: str | None, steps: list[str]) -> dict[str, Any]` — consistent across Tasks 2, 3
- `format_cross_session_plans_for_awareness(current_session_id, *, max_plans, max_age_days) -> str` — consistent across Tasks 6, 7
- `_plan_todo_auto_create_enabled() -> bool` — Tasks 3, 7
- Plan record schema: `completed_step_indices: list[int]` (sorted, deduped) consistent everywhere
- Todo record schema: `plan_id: str | None`, `plan_step_index: int | None` consistent

**Backwards-compat verified:**
- `propose_plan` signature unchanged (Task 2 step 3 only adds field to internal dict)
- `set_todos` signature unchanged (Task 4 step 4 only adds transition detection)
- `update_todo_status` signature unchanged (Task 4 step 5 only adds detection)
- `pending_plan_section` signature unchanged (Task 5 step 3 changes content, not signature)
- 109 existing plans: `rec.get("completed_step_indices") or []` returns `[]`; old todos with no `plan_id` skip the transition hook
- New `"completed"` status added to `_VALID_STATUSES`; existing callers that switch on status don't crash (they just don't recognize the new value, and current consumers — `pending_plan_section`, surfaces — explicitly filter)
- Kill-switch `plan_todo_auto_create_enabled=False` → `resolve_plan` no longer creates todos, identical to pre-Phase-1
