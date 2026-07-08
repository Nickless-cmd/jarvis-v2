---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Multi-step Planner Phase 2 — revise_plan: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the destination gap on Bjørn's `replan_signal` infrastructure: give Jarvis `revise_plan(plan_id, reason, new_steps)` so the "stale" signal has somewhere to go. New plan goes through the same approval flow as `propose_plan`; on approval, the original plan is superseded.

**Architecture:** One new tool module (`plan_revise_tool.py`), one new function (`revise_plan`) and one supersede hook in the existing `plan_proposals.py`. Three new optional fields on plan records (`revised_from`, `revision_reason`, `superseded_by`) — all default to None for backwards compat. Approval supersedes via the existing `resolve_plan` hook chain.

**Tech Stack:** Python 3.11, existing `state_store`, eventbus family `cognitive_state` (already registered).

**Spec:** `docs/superpowers/specs/2026-05-12-multistep-planner-phase2-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/tools/plan_revise_tool.py` | `_exec_revise_plan` handler; `PLAN_REVISE_TOOL_DEFINITIONS` + `PLAN_REVISE_TOOL_HANDLERS`. Mirror `world_model_tools.py` pattern from today. |
| `tests/test_plan_revision.py` | All Phase 2 tests: validation, revise flow, approval supersede, dismiss preserves old, killswitch, dedupe, backwards compat. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `plan_revision_enabled: bool = True` (kill-switch). |
| `core/services/plan_proposals.py` | Seed three new fields (`revised_from`, `revision_reason`, `superseded_by`) on plan records in `propose_plan`. Add `revise_plan(plan_id, *, session_id, reason, new_steps)`. Extend `resolve_plan` approved-branch with a supersede hook for plans carrying `revised_from`. Emit `cognitive_state.plan_revised` at propose-time and `cognitive_state.plan_revision_approved` at approval. |
| `core/tools/simple_tools.py` | Import + splat `PLAN_REVISE_TOOL_*`. |
| `scripts/smoke_test_startup.py` | Verify imports + tool registration. |

### Untouched / reused

- `replan_signal_for_plan` and `pending_plan_section` — Bjørn's stale-signal surface remains the trigger for Jarvis. We don't modify it.
- `propose_plan` signature unchanged (schema seed is additive).
- `agent_todos.create_from_plan` fires automatically when the revised plan is approved (existing Phase 1 hook); creates fresh todos from `new_steps`.
- `cross-session plans` formatter unchanged — revised plans surface naturally as approved+incomplete in awareness.
- `cognitive_state` event family — no new family.
- No DB schema changes. No new daemons.

---

## Spec deltas confirmed during planning

1. **Existing supersede behavior in `propose_plan`:** lines ~95-99 of `plan_proposals.py` already supersede any earlier still-pending plan for the same session at propose-time. Phase 2's supersede hook runs in `resolve_plan` (at approval-time) — different mechanism, different target (old approved plan, not pending plan in same session). No conflict.

2. **`resolve_plan` already has multiple post-approval hooks** added today: auto-todo-creation (Phase 1) + skill_data install (Tool Invention). Phase 2 adds a third hook (supersede `revised_from`). Order matters slightly: the skill_data hook would never fire on a revision (revisions don't carry `skill_data`), so the order is safe.

3. **Plan dedupe in `propose_plan`** checks for awaiting_approval plans with the same normalized title. Revisions naturally bypass this because the title is Jarvis-authored. We add explicit revise-side dedupe: if a pending revision of the same `plan_id` already exists, return it instead of creating a duplicate. This matches the spec.

4. **`revised_from` does NOT carry `skill_data`:** Phase 2 revise_plan explicitly sets `skill_data=None` on the new plan record. Even if the original plan had skill_data (Tool Invention Phase 1 install plan), the revision is for step-flows.

5. **Tool registration mirrors world_model_tools.py:** `simple_tools.py` already has two splat sites — line ~2330 for `TOOL_DEFINITIONS` (after `*WORLD_MODEL_TOOL_DEFINITIONS`) and line ~6196 for `_TOOL_HANDLERS` (after `**WORLD_MODEL_TOOL_HANDLERS`). We add `*PLAN_REVISE_TOOL_DEFINITIONS` and `**PLAN_REVISE_TOOL_HANDLERS` to both.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flag**

In `core/runtime/settings.py`, find `world_model_loop_enabled: bool = True` and add right after it:

```python
    # ── Plan revision (Phase 2 multi-step planner — added 2026-05-12) ───
    # When True: revise_plan tool is active. When False: tool returns
    # error immediately. Reverts to Phase 1-only behaviour (propose +
    # approve + supersede-on-duplicate). Existing plans unaffected.
    plan_revision_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `world_model_loop_enabled=bool(...)` in `load_settings` and add right after its closing comma:

```python
        plan_revision_enabled=bool(
            data.get(
                "plan_revision_enabled",
                defaults.plan_revision_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.plan_revision_enabled is True
print('OK:', load_settings().plan_revision_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(plan-revision): add plan_revision_enabled kill-switch"
```

---

## Task 2: revise_plan API + schema additions

**Files:**
- Modify: `core/services/plan_proposals.py`
- Create: `tests/test_plan_revision.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan_revision.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store so plans don't pollute across tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import importlib
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.plan_proposals as pp
    importlib.reload(pp)
    import core.services.agent_todos as at
    importlib.reload(at)
    return None


def test_propose_plan_seeds_new_phase2_fields(clean_state):
    """propose_plan now seeds revised_from/revision_reason/superseded_by=None."""
    from core.services.plan_proposals import propose_plan, _load_all

    r = propose_plan(
        session_id="s1", title="Original plan", why="x",
        steps=["step 1", "step 2"],
    )
    plans = _load_all()
    rec = plans[r["plan_id"]]
    assert rec.get("revised_from") is None
    assert rec.get("revision_reason") is None
    assert rec.get("superseded_by") is None


def test_revise_plan_errors_on_unknown_plan(clean_state):
    from core.services.plan_proposals import revise_plan

    result = revise_plan(
        plan_id="plan-does-not-exist",
        session_id="s1",
        reason="x",
        new_steps=["a"],
    )
    assert result["status"] == "error"
    assert "unknown" in result["error"].lower() or "not found" in result["error"].lower()


def test_revise_plan_errors_on_non_approved(clean_state):
    from core.services.plan_proposals import propose_plan, revise_plan

    r1 = propose_plan(
        session_id="s1", title="Still awaiting", why="x", steps=["a"],
    )
    # plan_id is still awaiting_approval — cannot be revised
    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="changed mind",
        new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "approved" in result["error"].lower()


def test_revise_plan_errors_on_empty_new_steps(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="x",
        new_steps=[],
    )
    assert result["status"] == "error"


def test_revise_plan_errors_on_empty_reason(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    result = revise_plan(
        plan_id=r1["plan_id"],
        session_id="s1",
        reason="",
        new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "reason" in result["error"].lower()


def test_revise_plan_creates_new_with_revised_from(clean_state):
    """Happy path: revise creates new plan with revised_from + reason set,
    progress reset, skill_data=None, status=awaiting_approval."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all

    r1 = propose_plan(
        session_id="s1", title="Original", why="initial",
        steps=["step A", "step B", "step C"],
    )
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    # Mark step 0 completed so we can verify progress resets
    plans = _load_all()
    plans[old_id]["completed_step_indices"] = [0]
    from core.services.plan_proposals import _save_all
    _save_all(plans)

    r2 = revise_plan(
        plan_id=old_id,
        session_id="s1",
        reason="context changed — different approach",
        new_steps=["new A", "new B"],
    )
    assert r2["status"] == "ok"
    new_id = r2["plan_id"]
    assert new_id != old_id

    plans_after = _load_all()
    new_rec = plans_after[new_id]
    assert new_rec["revised_from"] == old_id
    assert new_rec["revision_reason"] == "context changed — different approach"
    assert new_rec["completed_step_indices"] == []  # progress reset
    assert new_rec["status"] == "awaiting_approval"
    assert new_rec["steps"] == ["new A", "new B"]
    assert new_rec.get("skill_data") is None


def test_revise_plan_does_not_supersede_old_at_propose(clean_state):
    """Old plan remains approved until new revision is approved."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    revise_plan(
        plan_id=old_id,
        session_id="s1",
        reason="x",
        new_steps=["b"],
    )

    plans = _load_all()
    old_rec = plans[old_id]
    assert old_rec["status"] == "approved"  # unchanged
    assert old_rec.get("superseded_by") is None


def test_revise_plan_dedupe_returns_existing_pending(clean_state):
    """Second revise_plan of same plan_id returns the existing pending revision."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    rev_a = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="reason a", new_steps=["new a"],
    )
    rev_b = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="reason b", new_steps=["new b"],
    )
    assert rev_b["status"] == "skipped_duplicate"
    assert rev_b["existing_plan_id"] == rev_a["plan_id"]


def test_revise_plan_respects_killswitch(clean_state, monkeypatch):
    from core.services import plan_proposals as pp
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan

    r1 = propose_plan(session_id="s1", title="P1", why="x", steps=["a"])
    resolve_plan(r1["plan_id"], decision="approved")

    class FakeSettings:
        plan_revision_enabled = False
        # Also disable the Phase 1 todo auto-create flag to avoid surprises
        plan_todo_auto_create_enabled = True

    monkeypatch.setattr(pp, "load_settings", lambda: FakeSettings())

    result = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="x", new_steps=["b"],
    )
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_revise_plan_does_not_inherit_skill_data(clean_state):
    """If original plan had skill_data, revision MUST NOT inherit it."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan, _load_all

    skill_data = {
        "name": "test-skill",
        "description": "x",
        "instructions": "y",
        "use_when": "z",
        "tags": [],
    }
    r1 = propose_plan(
        session_id="s1", title="Install skill", why="x",
        steps=["install"], skill_data=skill_data,
    )
    resolve_plan(r1["plan_id"], decision="approved")
    # After approval, plan is approved (and via Tool Invention hook the skill
    # may have been installed, but that's not relevant to revise semantics).

    r2 = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="change my mind on the skill",
        new_steps=["different step"],
    )
    new_rec = _load_all()[r2["plan_id"]]
    assert new_rec.get("skill_data") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -15
```

Expected: most fail with `ImportError: cannot import name 'revise_plan'` or schema-seed assertions failing.

- [ ] **Step 3: Seed three new fields in `propose_plan`**

In `core/services/plan_proposals.py`, find the dict literal in `propose_plan` that builds `data[plan_id] = { ... }`. The current shape (after Phase 1 + Tool Invention Phase 1) ends with `"skill_data": skill_data if isinstance(skill_data, dict) else None,`. Add three more fields right after that line:

```python
    data[plan_id] = {
        "plan_id": plan_id,
        "session_id": sid,
        "title": title[:160],
        "why": why[:400],
        "steps": cleaned_steps[:20],
        "status": "awaiting_approval",
        "created_at": now,
        "completed_step_indices": [],
        "skill_data": skill_data if isinstance(skill_data, dict) else None,
        # Phase 2 (2026-05-12) — revision tracking
        "revised_from": None,
        "revision_reason": None,
        "superseded_by": None,
    }
```

- [ ] **Step 4: Add `revise_plan` function**

In `core/services/plan_proposals.py`, find `def mark_step_completed(` (added in Phase 1 today). Add the new `revise_plan` function right above it:

```python
def revise_plan(
    *,
    plan_id: str,
    session_id: str | None,
    reason: str,
    new_steps: list[str],
) -> dict[str, Any]:
    """Propose a revision of an existing approved plan.

    Creates a NEW plan record with status="awaiting_approval", linked to
    the original via revised_from. The original plan is NOT mutated here —
    it stays "approved" until the revision is approved (see resolve_plan
    hook below). Progress is reset on the new plan; skill_data is NOT
    inherited.

    Phase 2 of Multi-step Planner (2026-05-12).
    """
    if not _plan_revision_enabled():
        return {"status": "error", "error": "plan_revision disabled (killswitch)"}

    pid = str(plan_id or "").strip()
    reason_clean = (reason or "").strip()
    cleaned_steps = [str(s).strip() for s in (new_steps or []) if str(s).strip()]

    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    if not reason_clean:
        return {"status": "error", "error": "reason is required"}
    if not cleaned_steps:
        return {"status": "error", "error": "new_steps must contain at least one non-empty entry"}

    data = _load_all()
    old = data.get(pid)
    if old is None:
        return {"status": "error", "error": f"unknown plan_id {pid!r}"}
    if old.get("status") != "approved":
        return {
            "status": "error",
            "error": (
                f"plan {pid} is {old.get('status')!r}, not 'approved' — "
                "only approved plans can be revised"
            ),
        }

    # Dedupe: if a pending revision of this same plan_id already exists,
    # return the existing one rather than creating a duplicate.
    for existing_id, rec in data.items():
        if (
            rec.get("status") == "awaiting_approval"
            and rec.get("revised_from") == pid
        ):
            return {
                "status": "skipped_duplicate",
                "existing_plan_id": existing_id,
                "awaiting": True,
                "session_id": str(rec.get("session_id") or sid or "_default"),
            }

    # Create new plan record
    sid = str(session_id or old.get("session_id") or "_default")
    new_plan_id = f"plan-{uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()

    data[new_plan_id] = {
        "plan_id": new_plan_id,
        "session_id": sid,
        "title": f"Revision of {old.get('title') or pid}"[:160],
        "why": reason_clean[:400],
        "steps": cleaned_steps[:20],
        "status": "awaiting_approval",
        "created_at": now,
        "completed_step_indices": [],
        # Revisions never carry skill_data — they are for step-flows.
        "skill_data": None,
        # Phase 2 revision tracking
        "revised_from": pid,
        "revision_reason": reason_clean,
        "superseded_by": None,
    }
    _save_all(data)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_state.plan_revised",
            {
                "old_plan_id": pid,
                "new_plan_id": new_plan_id,
                "reason": reason_clean[:120],
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "plan_id": new_plan_id,
        "awaiting": True,
        "session_id": sid,
        "revised_from": pid,
    }


def _plan_revision_enabled() -> bool:
    try:
        return bool(load_settings().plan_revision_enabled)
    except Exception:
        return True  # fail-open: settings issue shouldn't disable feature
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -15
```

Expected: 10 passed.

- [ ] **Step 6: Verify no Phase 1 regression**

```bash
conda run -n ai pytest tests/test_multistep_planner.py tests/test_tool_invention.py 2>&1 | tail -5
```

Expected: all green (existing Phase 1 + Tool Invention tests still pass with new schema fields).

- [ ] **Step 7: Commit**

```bash
git add core/services/plan_proposals.py tests/test_plan_revision.py
git commit -m "feat(plan-revision): revise_plan API + schema additions (revised_from / revision_reason / superseded_by)"
```

---

## Task 3: Approval supersede hook in resolve_plan

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `tests/test_plan_revision.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plan_revision.py`:

```python
def test_approving_revision_supersedes_old(clean_state):
    """When the revised plan is approved, old plan transitions to superseded."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all,
    )

    r1 = propose_plan(session_id="s1", title="Original", why="x", steps=["a", "b"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="changed", new_steps=["x", "y"],
    )
    new_id = r2["plan_id"]

    resolve_plan(new_id, decision="approved")

    plans = _load_all()
    assert plans[old_id]["status"] == "superseded"
    assert plans[old_id]["superseded_by"] == new_id
    assert plans[new_id]["status"] == "approved"


def test_dismissing_revision_preserves_old(clean_state):
    """When the revised plan is dismissed, old plan stays approved."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all,
    )

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="x", new_steps=["b"],
    )
    new_id = r2["plan_id"]

    resolve_plan(new_id, decision="dismissed")

    plans = _load_all()
    assert plans[old_id]["status"] == "approved"
    assert plans[old_id].get("superseded_by") is None
    assert plans[new_id]["status"] == "dismissed"


def test_approving_revision_creates_fresh_todos(clean_state):
    """The Phase 1 todo-creation hook still fires for revised plans."""
    from core.services.plan_proposals import propose_plan, resolve_plan, revise_plan
    from core.services.agent_todos import list_todos

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["old-step"])
    resolve_plan(r1["plan_id"], decision="approved")

    r2 = revise_plan(
        plan_id=r1["plan_id"], session_id="s1",
        reason="x", new_steps=["new-step-1", "new-step-2"],
    )
    resolve_plan(r2["plan_id"], decision="approved")

    # Todos for revised plan should exist (Phase 1 auto-create hook fires)
    todos = list_todos("s1")
    new_todo_contents = [t["content"] for t in todos if t.get("plan_id") == r2["plan_id"]]
    assert "new-step-1" in new_todo_contents
    assert "new-step-2" in new_todo_contents


def test_approval_when_old_already_not_approved_is_graceful(clean_state):
    """Race condition: old plan manually dismissed before revision approved.
    Revision still approves; supersede hook no-ops on non-approved old."""
    from core.services.plan_proposals import (
        propose_plan, resolve_plan, revise_plan, _load_all, _save_all,
    )

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["a"])
    old_id = r1["plan_id"]
    resolve_plan(old_id, decision="approved")

    r2 = revise_plan(
        plan_id=old_id, session_id="s1",
        reason="x", new_steps=["b"],
    )
    new_id = r2["plan_id"]

    # Manually mark old plan as something other than approved (race condition)
    data = _load_all()
    data[old_id]["status"] = "completed"  # imagine all steps got resolved
    _save_all(data)

    # Approving revision should still succeed, but should NOT mutate the
    # already-completed old plan.
    result = resolve_plan(new_id, decision="approved")
    assert result["status"] == "ok"

    plans = _load_all()
    # Old stays completed (not flipped to superseded)
    assert plans[old_id]["status"] == "completed"
    assert plans[old_id].get("superseded_by") is None
    # New is approved as usual
    assert plans[new_id]["status"] == "approved"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -10
```

Expected: 4 new tests fail (old plan does not yet transition to superseded on approval).

- [ ] **Step 3: Add supersede hook in `resolve_plan`**

In `core/services/plan_proposals.py`, locate the `resolve_plan` function. After the existing Tool Invention hook (the block that calls `create_skill` when `skill_data` is present), add the Phase 2 supersede hook right before the final `return {"status": "ok", ...}`:

```python
    # Phase 2 (2026-05-12) — supersede the revised plan's original.
    # Fires only on approval of a revision; gracefully no-ops if the
    # original is no longer in 'approved' state (race condition with
    # manual dismiss/completion).
    if decision == "approved":
        revised_from = rec.get("revised_from")
        if revised_from:
            # Reload fresh — the skill_data hook above may have mutated state
            data_after = _load_all()
            old_rec = data_after.get(str(revised_from))
            if old_rec is not None and old_rec.get("status") == "approved":
                old_rec["status"] = "superseded"
                old_rec["superseded_by"] = plan_id
                old_rec["updated_at"] = datetime.now(UTC).isoformat()
                _save_all(data_after)
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish(
                        "cognitive_state.plan_revision_approved",
                        {
                            "old_plan_id": str(revised_from),
                            "new_plan_id": plan_id,
                        },
                    )
                except Exception:
                    pass
```

Note: the function already imports `datetime` and `UTC` at module top; if `_save_all` and `_load_all` aren't visible inside `resolve_plan`'s scope, they should be — they're module-level. Verify:

```bash
grep -n "_save_all\|_load_all" /media/projects/jarvis-v2/core/services/plan_proposals.py | head -5
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -15
```

Expected: 14 passed.

- [ ] **Step 5: Verify no Phase 1 regression (Multi-step Planner + Tool Invention)**

```bash
conda run -n ai pytest tests/test_multistep_planner.py tests/test_tool_invention.py tests/test_plan_revision.py 2>&1 | tail -6
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add core/services/plan_proposals.py tests/test_plan_revision.py
git commit -m "feat(plan-revision): approval supersede hook in resolve_plan + plan_revision_approved event"
```

---

## Task 4: plan_revise_tool.py + register in simple_tools

**Files:**
- Create: `core/tools/plan_revise_tool.py`
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_plan_revision.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plan_revision.py`:

```python
def test_revise_plan_tool_creates_revision(clean_state):
    from core.services.plan_proposals import propose_plan, resolve_plan, _load_all
    from core.tools.plan_revise_tool import _exec_revise_plan

    r1 = propose_plan(session_id="s1", title="P", why="x", steps=["a", "b"])
    resolve_plan(r1["plan_id"], decision="approved")

    result = _exec_revise_plan({
        "plan_id": r1["plan_id"],
        "session_id": "s1",
        "reason": "user wants different approach",
        "new_steps": ["x", "y"],
    })
    assert result["status"] == "ok"
    new_id = result["plan_id"]

    plans = _load_all()
    assert plans[new_id]["revised_from"] == r1["plan_id"]


def test_revise_plan_tool_validates_required_args(clean_state):
    from core.tools.plan_revise_tool import _exec_revise_plan

    # Missing plan_id
    result = _exec_revise_plan({"reason": "x", "new_steps": ["a"]})
    assert result["status"] == "error"

    # Missing reason
    result = _exec_revise_plan({"plan_id": "p", "new_steps": ["a"]})
    assert result["status"] == "error"

    # Missing new_steps
    result = _exec_revise_plan({"plan_id": "p", "reason": "x"})
    assert result["status"] == "error"


def test_revise_plan_tool_killswitch(clean_state, monkeypatch):
    from core.tools import plan_revise_tool as prt

    class FakeSettings:
        plan_revision_enabled = False

    monkeypatch.setattr(prt, "load_settings", lambda: FakeSettings())

    result = prt._exec_revise_plan({
        "plan_id": "any",
        "session_id": "s1",
        "reason": "x",
        "new_steps": ["a"],
    })
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_revise_plan_tool_definitions_registered():
    from core.tools.plan_revise_tool import (
        PLAN_REVISE_TOOL_DEFINITIONS,
        PLAN_REVISE_TOOL_HANDLERS,
    )

    names = [
        (e.get("function") or {}).get("name")
        for e in PLAN_REVISE_TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "revise_plan" in names
    assert "revise_plan" in PLAN_REVISE_TOOL_HANDLERS


def test_revise_plan_tool_registered_via_simple_tools():
    """End-to-end: the splat into simple_tools picks up our new tool."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    names = [
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "revise_plan" in names
    assert "revise_plan" in _TOOL_HANDLERS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -10
```

Expected: 5 new tests fail with `ModuleNotFoundError: core.tools.plan_revise_tool`.

- [ ] **Step 3: Create `core/tools/plan_revise_tool.py`**

```python
"""Plan revision tool — revise_plan.

Phase 2 of Multi-step Planner (2026-05-12). Closes the destination gap on
Bjørn's replan_signal: stale-signal fires but Jarvis has no clean tool to
revise. This tool proposes a revision via plan_proposals.revise_plan, which
goes through the standard approval flow.

Approval semantics:
  - Revision starts as awaiting_approval (NOT auto-approved)
  - Original plan stays approved until revision is approved
  - On approval, the original plan transitions to "superseded"
  - On dismissal, the original plan continues unchanged

Mirror the world_model_tools.py pattern.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.plan_proposals import revise_plan

logger = logging.getLogger(__name__)


def _exec_revise_plan(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for revise_plan."""
    # Killswitch is checked inside plan_proposals.revise_plan too — duplicate
    # here so we error out before even validating the rest of the args.
    try:
        if not bool(load_settings().plan_revision_enabled):
            return {"status": "error", "error": "plan_revision disabled (killswitch)"}
    except Exception:
        pass  # fail-open: settings broken → defer to function-level check

    plan_id = str(args.get("plan_id") or "").strip()
    session_id = args.get("session_id")
    reason = str(args.get("reason") or "").strip()
    new_steps = args.get("new_steps") or []
    if not isinstance(new_steps, list):
        new_steps = [str(new_steps)]

    if not plan_id:
        return {"status": "error", "error": "plan_id is required"}
    if not reason:
        return {"status": "error", "error": "reason is required"}
    if not new_steps:
        return {"status": "error", "error": "new_steps is required"}

    return revise_plan(
        plan_id=plan_id,
        session_id=session_id,
        reason=reason,
        new_steps=[str(s) for s in new_steps],
    )


PLAN_REVISE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "revise_plan",
            "description": (
                "Foreslå en revision af en eksisterende approved plan. Bruges når "
                "planen er blevet stale, konteksten har ændret sig, eller du har "
                "lært noget der ændrer hvad næste skridt bør være. Ny plan venter "
                "på godkendelse — godkendelse markerer den gamle plan som "
                "superseded. Progress nulstilles (revision = ny plan = ny progress)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "ID på den eksisterende approved plan der reviseres",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Hvorfor reviderer du? Hvad har ændret sig?",
                    },
                    "new_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Den reviderede step-liste. Inkluder allerede-"
                            "fuldførte steps hvis de stadig er relevante "
                            "(progress nulstilles)."
                        ),
                    },
                },
                "required": ["plan_id", "reason", "new_steps"],
            },
        },
    },
]


PLAN_REVISE_TOOL_HANDLERS: dict[str, Any] = {
    "revise_plan": _exec_revise_plan,
}
```

- [ ] **Step 4: Register in `simple_tools.py`**

In `core/tools/simple_tools.py`, find the import block where `WORLD_MODEL_TOOL_DEFINITIONS` is imported. Add right after that import:

```python
from core.tools.plan_revise_tool import (
    PLAN_REVISE_TOOL_DEFINITIONS,
    PLAN_REVISE_TOOL_HANDLERS,
)
```

Then find the `TOOL_DEFINITIONS` list and locate `*WORLD_MODEL_TOOL_DEFINITIONS,` (added earlier today). Add right after it:

```python
    *PLAN_REVISE_TOOL_DEFINITIONS,
```

Then find the `_TOOL_HANDLERS` dict and locate `**WORLD_MODEL_TOOL_HANDLERS,`. Add right after it:

```python
    **PLAN_REVISE_TOOL_HANDLERS,
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_plan_revision.py -v 2>&1 | tail -15
```

Expected: 19 passed.

- [ ] **Step 6: Smoke check tool registration**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = [(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)]
assert 'revise_plan' in names, 'revise_plan missing from TOOL_DEFINITIONS'
assert 'revise_plan' in _TOOL_HANDLERS, 'revise_plan missing from _TOOL_HANDLERS'
print('OK: revise_plan registered via simple_tools')
"
```

Expected: `OK: revise_plan registered via simple_tools`

- [ ] **Step 7: Commit**

```bash
git add core/tools/plan_revise_tool.py core/tools/simple_tools.py tests/test_plan_revision.py
git commit -m "feat(plan-revision): revise_plan tool handler + register via simple_tools"
```

---

## Task 5: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the World Model Phase 1 smoke block and add right after it:

```python
        # Multi-step Planner Phase 2 — revise_plan (added 2026-05-12)
        try:
            from core.services.plan_proposals import (  # noqa: F401
                revise_plan,
                _plan_revision_enabled,
            )
            from core.tools.plan_revise_tool import (  # noqa: F401
                _exec_revise_plan,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _names = [
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            ]
            if "revise_plan" not in _names:
                raise RuntimeError("revise_plan not in TOOL_DEFINITIONS")
            if "revise_plan" not in _TOOL_HANDLERS:
                raise RuntimeError("revise_plan not in _TOOL_HANDLERS")
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_plan_revision.py tests/test_multistep_planner.py tests/test_tool_invention.py tests/test_world_model_loop.py 2>&1 | tail -10
```

Expected: all green (19 + 28 + 20 + 29 = 96 tests).

- [ ] **Step 3: Production probe — verify tool listed + replan_signal still works**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS
defs = [e for e in TOOL_DEFINITIONS if isinstance(e, dict) and (e.get('function') or {}).get('name') == 'revise_plan']
assert len(defs) == 1
print('OK: revise_plan tool definition present')

# Confirm Bjørn's stale-signal API still works (Phase 2 didn't break it)
from core.services.plan_proposals import replan_signal_for_plan
print('OK: replan_signal_for_plan still callable:', callable(replan_signal_for_plan))
"
```

Expected: `OK: revise_plan tool definition present` and `OK: replan_signal_for_plan still callable: True`.

- [ ] **Step 4: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Multi-step Planner Phase 2 (AGI track #2) — 30-day review: '
    'count revisions Jarvis proposed via revise_plan tool, '
    'count revisions approved vs dismissed, '
    'read revision_reason fields — were they meaningful? '
    'compute revise-rate vs stale-signal-rate (does Jarvis act on '
    'replan_signal when it fires?). '
    'If 0 revisions despite N stale-signals: tool not visible enough; '
    'consider direct awareness-nudge in Phase 3. '
    'Check chain depth: any plan revised > 2 times indicates thrashing. '
    'Look at skill-install plans: are they showing up in stale-signals '
    'with no available action? (skill_data plans cannot be revised by design). '
    'Decide: keep / tune / Phase 3 deviation detection / Phase 3 failure handler.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='multistep_planner_phase2')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 5: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(plan-revision): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `plan_revision_enabled` | Task 1 |
| Plan schema additions (`revised_from`, `revision_reason`, `superseded_by`) | Task 2 step 3 |
| `revise_plan(plan_id, *, session_id, reason, new_steps)` API | Task 2 step 4 |
| Validation: unknown plan, non-approved, empty steps, empty reason | Task 2 step 4 |
| Dedupe on existing pending revision | Task 2 step 4 |
| Reset `completed_step_indices=[]` on new plan | Task 2 step 4 |
| `skill_data=None` on new plan (revisions don't inherit) | Task 2 step 4 |
| Old plan NOT touched at propose-time | Task 2 step 4 (only writes new record) |
| `cognitive_state.plan_revised` event at propose | Task 2 step 4 |
| `resolve_plan` supersede hook | Task 3 step 3 |
| Old plan transitions to `superseded` + `superseded_by` set | Task 3 step 3 |
| `cognitive_state.plan_revision_approved` event at approval | Task 3 step 3 |
| Race-condition safe (old plan not in approved → no mutation) | Task 3 step 3 + test |
| `plan_revise_tool.py` with handler | Task 4 step 3 |
| `revise_plan` registered via simple_tools | Task 4 step 4 |
| Kill-switch returns error | Tasks 2, 4 (both check) |
| Smoke imports | Task 5 step 1 |
| 30-day review | Task 5 step 4 |
| Backwards compat | All tasks: schema fields default to None; propose_plan signature unchanged; existing Phase 1 hooks unchanged |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `revise_plan(*, plan_id: str, session_id: str | None, reason: str, new_steps: list[str]) -> dict[str, Any]` — Tasks 2, 3, 4
- `_plan_revision_enabled() -> bool` — Tasks 2, 4
- `_exec_revise_plan(args: dict[str, Any]) -> dict[str, Any]` — Tasks 4, 5
- Plan record fields: `revised_from`, `revision_reason`, `superseded_by` — consistently named across Tasks 2, 3
- Eventbus event names: `cognitive_state.plan_revised`, `cognitive_state.plan_revision_approved` — consistent

**Backwards-compat verified:**
- `propose_plan` signature unchanged (only adds 3 new fields with `None` default).
- Existing 109+ plans + Phase 1 plans + Tool Invention plans + World Model plans all load fine — `rec.get("revised_from")` returns `None` for old records.
- `resolve_plan` Phase 1 hooks (auto-todo-creation, skill_data) still fire — Phase 2 hook is additive, runs after them, no-ops when `revised_from` is None.
- `propose_plan` dedupe (same title pending in session) still works for non-revision plans.
- Bjørn's `replan_signal_for_plan` API unchanged.
- `pending_plan_section` formatter unchanged.
- Kill-switch `plan_revision_enabled=False` → tool errors immediately; existing plans untouched; no degradation.
- No DB schema changes. No new event families. No new daemons.
