# Tool Invention Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the loop from "Jarvis notices he needs a new skill" to "skill installed on disk after approval" — without inventing new infrastructure. Reuse `propose_plan` (Multi-step Planner Phase 1) for the approval flow; reuse `create_skill()` (already live) for installation; validate up front so approval always succeeds.

**Architecture:** Five existing files are extended; no new modules. `propose_plan` learns an optional `skill_data` payload field that survives the approval lifecycle. When `resolve_plan(decision="approved")` runs, a hook checks for `skill_data` and calls `create_skill()`. A new tool `propose_new_skill` validates inputs at propose-time using a new `validate_skill_proposal()` helper, then submits via `propose_plan`. Validation includes shadow-check against existing tool names.

**Tech Stack:** Python 3.11, existing skill_engine (file-based), existing plan_proposals (state_store), existing eventbus (`cognitive_state` family).

**Spec:** `docs/superpowers/specs/2026-05-12-tool-invention-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `tests/test_tool_invention.py` | All Phase 1 tests: validation, propose/approve/dismiss/install flow, kill-switch, shadow-check, I/O failure path, backwards compat. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `tool_invention_enabled: bool = True` (kill-switch). |
| `core/services/skill_engine.py` | Add `validate_skill_proposal(name, description, instructions, use_when, tags) -> dict[str, Any]`. Extracts validation from `create_skill()` into a shared helper called by both; `create_skill()` body becomes thin wrapper that validates then writes. Validation now also rejects names that shadow existing tool names. |
| `core/services/plan_proposals.py` | Extend `propose_plan` to accept `skill_data: dict[str, Any] | None = None` kwarg. Store it on the plan record. Extend `resolve_plan` to detect `skill_data` at `decision="approved"`, call `create_skill()`, emit events. |
| `core/tools/skill_engine_tools.py` | Add `_exec_propose_new_skill(args)` handler + tool definition; append to `SKILL_ENGINE_TOOL_DEFINITIONS` and `SKILL_ENGINE_TOOL_HANDLERS`. |
| `core/tools/simple_tools.py` | No new code — `SKILL_ENGINE_TOOL_DEFINITIONS` and `SKILL_ENGINE_TOOL_HANDLERS` already splat in. New tool flows through automatically. |

### Untouched / reused

- `core/services/agent_todos.py` — `create_from_plan` already handles single-step plans; skill-proposal plans use one symbolic step "Install skill 'X'". No changes.
- `core/services/prompt_contract.py` — `pending_plan_section` already shows all approved+incomplete plans; skill-proposal plans surface naturally.
- `core/eventbus/events.py` — `cognitive_state` family already covers new event kinds.
- `core/runtime/db.py` — no schema changes.
- No new DB tables. No new event families. No new daemons.

---

## Spec deltas confirmed during planning

1. **Tool-name shadow-check requires a list of registered tools.** `core/tools/simple_tools.py` exposes `TOOL_DEFINITIONS` as a module-level list of dicts; each dict has a `function.name` field. Helper iterates and collects names. Lazy import inside `validate_skill_proposal` so we don't pull simple_tools at module load time (it's a heavy import).

2. **`create_skill()` validation order:** the current function strips/lowers the name BEFORE the regex check. The extracted helper must preserve this — the regex is applied to the cleaned name, not the raw input. Tests must check both raw inputs (uppercase, spaces) and the post-cleanup name.

3. **`SKILL_ENGINE_TOOL_DEFINITIONS` and `SKILL_ENGINE_TOOL_HANDLERS` register names.** `simple_tools.py:476-477` imports them; `simple_tools.py:2326` splats definitions into `TOOL_DEFINITIONS`; `simple_tools.py:6191` splats handlers into `_TOOL_HANDLERS`. Adding `propose_new_skill` to both dicts in `skill_engine_tools.py` is sufficient — no changes to `simple_tools.py`.

4. **`propose_plan` returns dict with `plan_id` key.** Tool handler returns this dict directly so Jarvis sees the plan_id back from his tool call.

5. **Backwards compat for `propose_plan` callers:** existing call sites (`_exec_propose_plan`, autonomous proposers) don't pass `skill_data`. Default `None` → field absent → existing code paths unaffected. `resolve_plan` hook uses `rec.get("skill_data")` which returns `None` for old plans.

6. **`create_skill()` post-extraction:** to keep diff minimal and tests light, we leave `create_skill()` calling its own validation path (same logic now lives in `validate_skill_proposal()`). After the helper is added, `create_skill()` can call `validate_skill_proposal()` internally for DRY — but this is optional and Phase 1 keeps both paths in sync by extracting the *single source of truth* into one helper function.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flag**

In `core/runtime/settings.py`, find `unconscious_modulation_top_p_ceiling: float = 1.0` and add right after it:

```python
    # ── Tool invention (AGI track #9 — added 2026-05-12) ─────────────────
    # When True, propose_new_skill tool is exposed and active. When False,
    # the tool returns an error immediately (kill-switch).
    tool_invention_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `unconscious_modulation_top_p_ceiling=float(...)` and add right after its closing comma:

```python
        tool_invention_enabled=bool(
            data.get(
                "tool_invention_enabled",
                defaults.tool_invention_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.tool_invention_enabled is True
print('OK:', load_settings().tool_invention_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(tool-invention): add tool_invention_enabled kill-switch"
```

---

## Task 2: validate_skill_proposal helper

**Files:**
- Modify: `core/services/skill_engine.py`
- Create: `tests/test_tool_invention.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tool_invention.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def isolated_skills_root(tmp_path, monkeypatch):
    """Point SKILLS_ROOT to an empty tmp dir, reload skills."""
    import core.services.skill_engine as se

    monkeypatch.setattr(se, "SKILLS_ROOT", tmp_path)
    se.reload_skills()
    return tmp_path


def test_validate_accepts_clean_proposal(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="my-new-skill",
        description="Does X cleanly.",
        instructions="When triggered, do X by following these steps...",
        use_when="When user asks for X",
        tags=["productivity"],
    )
    assert result["status"] == "ok"


def test_validate_rejects_empty_name(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="",
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"
    assert "name" in result["error"].lower()


def test_validate_rejects_invalid_regex(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="MyNewSkill!",  # uppercase + bang
        description="x",
        instructions="x",
    )
    assert result["status"] == "error"


def test_validate_rejects_empty_description(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="ok-name",
        description="",
        instructions="some instructions",
    )
    assert result["status"] == "error"


def test_validate_rejects_empty_instructions(isolated_skills_root):
    from core.services.skill_engine import validate_skill_proposal

    result = validate_skill_proposal(
        name="ok-name",
        description="ok description",
        instructions="",
    )
    assert result["status"] == "error"


def test_validate_rejects_duplicate_name(isolated_skills_root):
    from core.services.skill_engine import (
        create_skill,
        validate_skill_proposal,
    )

    create_skill(
        name="already-here",
        description="existing skill",
        instructions="existing instructions",
    )
    result = validate_skill_proposal(
        name="already-here",
        description="another",
        instructions="more",
    )
    assert result["status"] == "error"
    assert "already" in result["error"].lower() or "exist" in result["error"].lower()


def test_validate_rejects_name_shadowing_existing_tool(isolated_skills_root, monkeypatch):
    """Skill name must not collide with a registered tool name."""
    from core.services import skill_engine

    # Stub the tool-name lookup to return a known tool.
    monkeypatch.setattr(
        skill_engine,
        "_collect_registered_tool_names",
        lambda: {"approve_plan", "propose_plan", "bash"},
    )

    result = skill_engine.validate_skill_proposal(
        name="approve-plan",  # close to "approve_plan" after normalization
        description="x",
        instructions="x",
    )
    # The check normalizes both sides for comparison; "approve-plan" → "approve_plan" collision.
    assert result["status"] == "error"
    assert "tool" in result["error"].lower() or "shadow" in result["error"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -15
```

Expected: FAIL with `ImportError: cannot import name 'validate_skill_proposal'`.

- [ ] **Step 3: Extract validation logic + add validate_skill_proposal**

In `core/services/skill_engine.py`, find `def create_skill(` (around line 251). Add this helper right ABOVE it:

```python
def _collect_registered_tool_names() -> set[str]:
    """Return the set of registered tool names (normalized form).

    Lazy import to avoid pulling simple_tools at module load time —
    simple_tools transitively imports a lot.
    """
    try:
        from core.tools.simple_tools import TOOL_DEFINITIONS
    except Exception:
        return set()
    names: set[str] = set()
    for entry in TOOL_DEFINITIONS or []:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") if isinstance(entry.get("function"), dict) else entry
        n = str((fn or {}).get("name") or "").strip()
        if n:
            # Normalize for comparison: lowercase, "-" → "_"
            names.add(n.lower().replace("-", "_"))
    return names


def validate_skill_proposal(
    name: str,
    description: str,
    instructions: str,
    use_when: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Validate that a proposed skill would be installable by create_skill().

    Same checks as create_skill() but without writing to disk:
      - name is non-empty after strip+lower+space→hyphen normalization
      - name matches ^[a-z0-9][a-z0-9_-]*$
      - description and instructions are non-empty
      - no existing skill with the (normalized) name
      - normalized name does not shadow a registered tool name

    Returns {"status": "ok"} or {"status": "error", "error": "..."}.
    """
    name = name.strip().lower().replace(" ", "-")
    if not name:
        return {"status": "error", "error": "name is required"}
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        return {"status": "error", "error": "name must be lowercase alphanumeric with - and _"}
    if not description or not instructions:
        return {"status": "error", "error": "description and instructions are required"}

    skill_dir = SKILLS_ROOT / name
    if skill_dir.exists():
        return {"status": "error", "error": f"skill '{name}' already exists"}

    # Shadow-check: skill name (normalized to underscore form) must not
    # collide with a registered tool name.
    normalized_for_tool_check = name.replace("-", "_")
    tool_names = _collect_registered_tool_names()
    if normalized_for_tool_check in tool_names:
        return {
            "status": "error",
            "error": (
                f"name '{name}' shadows existing tool '{normalized_for_tool_check}' — "
                "pick a different name to avoid skill_chain confusion"
            ),
        }

    return {"status": "ok", "name": name}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Verify create_skill() still works (no regression)**

```bash
conda run -n ai pytest tests/ -k "skill_engine or skill_create" -v 2>&1 | tail -10
```

Expected: existing skill-engine tests still pass.

- [ ] **Step 6: Commit**

```bash
git add core/services/skill_engine.py tests/test_tool_invention.py
git commit -m "feat(tool-invention): validate_skill_proposal helper with shadow-check"
```

---

## Task 3: propose_plan accepts skill_data kwarg

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `tests/test_tool_invention.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tool_invention.py`:

```python
@pytest.fixture()
def clean_plan_state(tmp_path, monkeypatch):
    """Isolated state_store so plans don't pollute."""
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


def test_propose_plan_accepts_skill_data(clean_plan_state):
    from core.services.plan_proposals import propose_plan, _load_all

    skill_data = {
        "name": "my-skill",
        "description": "x",
        "instructions": "y",
        "use_when": "z",
        "tags": ["a"],
    }
    result = propose_plan(
        session_id="s1",
        title="Ny skill: my-skill",
        why="x",
        steps=["Install skill 'my-skill' (auto on approval)"],
        skill_data=skill_data,
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    plans = _load_all()
    assert plans[plan_id]["skill_data"] == skill_data


def test_propose_plan_without_skill_data_works_unchanged(clean_plan_state):
    """Backwards compat: existing callers don't pass skill_data."""
    from core.services.plan_proposals import propose_plan, _load_all

    result = propose_plan(
        session_id="s1",
        title="Regular plan",
        why="x",
        steps=["step 1"],
    )
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    # Field should NOT be present on the plan
    plans = _load_all()
    assert "skill_data" not in plans[plan_id] or plans[plan_id].get("skill_data") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_tool_invention.py::test_propose_plan_accepts_skill_data tests/test_tool_invention.py::test_propose_plan_without_skill_data_works_unchanged -v
```

Expected: first fails (`skill_data` not stored), second may pass already (no breakage yet).

- [ ] **Step 3: Extend propose_plan signature + storage**

In `core/services/plan_proposals.py`, find the `propose_plan` function (around line 48). The current signature ends with `steps: list[str],`. Add `skill_data` kwarg:

```python
def propose_plan(
    *,
    session_id: str | None,
    title: str,
    why: str,
    steps: list[str],
    skill_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Then find the dict creation inside `propose_plan` that builds the new plan record (the one starting `data[plan_id] = { ... }`). Add `skill_data` field right after `completed_step_indices`:

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
        # Tool Invention Phase 1 (2026-05-12): optional skill-install metadata.
        # When present, resolve_plan(decision="approved") will call
        # skill_engine.create_skill() on it after status transition.
        "skill_data": skill_data if isinstance(skill_data, dict) else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -10
```

Expected: 9 passed.

- [ ] **Step 5: Verify no Multi-step Planner regression**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -10
```

Expected: 26 passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/plan_proposals.py tests/test_tool_invention.py
git commit -m "feat(tool-invention): propose_plan accepts optional skill_data kwarg"
```

---

## Task 4: resolve_plan hook calls create_skill on approval

**Files:**
- Modify: `core/services/plan_proposals.py`
- Modify: `tests/test_tool_invention.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tool_invention.py`:

```python
def test_resolve_plan_approved_calls_create_skill(clean_plan_state, isolated_skills_root):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.skill_engine import skill_exists

    r = propose_plan(
        session_id="s1",
        title="Ny skill: install-this",
        why="testing",
        steps=["Install skill 'install-this' (auto on approval)"],
        skill_data={
            "name": "install-this",
            "description": "Does the install",
            "instructions": "When triggered, install something.",
            "use_when": "When asked",
            "tags": ["test"],
        },
    )
    plan_id = r["plan_id"]

    res = resolve_plan(plan_id, decision="approved")
    assert res["status"] == "ok"

    assert skill_exists("install-this") is True


def test_resolve_plan_dismissed_does_not_install_skill(clean_plan_state, isolated_skills_root):
    from core.services.plan_proposals import propose_plan, resolve_plan
    from core.services.skill_engine import skill_exists

    r = propose_plan(
        session_id="s1",
        title="Ny skill: dont-install",
        why="x",
        steps=["x"],
        skill_data={
            "name": "dont-install",
            "description": "x",
            "instructions": "x",
            "use_when": "x",
            "tags": [],
        },
    )
    resolve_plan(r["plan_id"], decision="dismissed")
    assert skill_exists("dont-install") is False


def test_resolve_plan_without_skill_data_no_install_attempted(clean_plan_state, isolated_skills_root):
    """Backwards compat: plans without skill_data behave exactly as before."""
    from core.services.plan_proposals import propose_plan, resolve_plan

    r = propose_plan(
        session_id="s1",
        title="Regular plan",
        why="x",
        steps=["x"],
    )
    res = resolve_plan(r["plan_id"], decision="approved")
    assert res["status"] == "ok"
    # No skill should have been installed because no skill_data present


def test_resolve_plan_install_io_failure_logged_not_raised(
    clean_plan_state, isolated_skills_root, monkeypatch, caplog,
):
    """If create_skill raises at install time, resolve_plan logs + emits
    event but does not raise. Plan stays approved."""
    from core.services import plan_proposals
    from core.services.plan_proposals import propose_plan, resolve_plan, _load_all

    def boom(**kwargs):
        raise IOError("disk full")

    monkeypatch.setattr(
        "core.services.skill_engine.create_skill", boom,
    )

    r = propose_plan(
        session_id="s1",
        title="x",
        why="x",
        steps=["x"],
        skill_data={
            "name": "will-fail",
            "description": "x",
            "instructions": "x",
            "use_when": "x",
            "tags": [],
        },
    )
    plan_id = r["plan_id"]

    # Should NOT raise
    with caplog.at_level("ERROR"):
        res = resolve_plan(plan_id, decision="approved")
    assert res["status"] == "ok"

    plan = _load_all()[plan_id]
    assert plan["status"] == "approved"  # not auto-completed, but no crash
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -10
```

Expected: 4 new tests fail with skills not being installed.

- [ ] **Step 3: Extend resolve_plan hook**

In `core/services/plan_proposals.py`, find `resolve_plan`. The existing function (after Multi-step Planner Phase 1) handles the approved branch including auto-todo-creation. Find the existing approved-block in `resolve_plan` — it should look approximately like this (line numbers may differ):

```python
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
```

Right after that block, add a new install hook:

```python
    # Tool Invention Phase 1 (2026-05-12): if the plan carries skill_data,
    # call create_skill() on approval. Validation already ran at propose-time,
    # so this should normally succeed; I/O failures are logged + emitted but
    # do not raise (plan stays "approved" but uncompleted in that case).
    if decision == "approved":
        skill_data = rec.get("skill_data")
        if isinstance(skill_data, dict):
            try:
                from core.services.skill_engine import create_skill
                install_result = create_skill(
                    name=str(skill_data.get("name") or ""),
                    description=str(skill_data.get("description") or ""),
                    instructions=str(skill_data.get("instructions") or ""),
                    use_when=str(skill_data.get("use_when") or ""),
                    tags=list(skill_data.get("tags") or []),
                )
                if install_result.get("status") == "ok":
                    try:
                        from core.eventbus.bus import event_bus
                        event_bus.publish(
                            "cognitive_state.skill_installed",
                            {
                                "plan_id": plan_id,
                                "name": skill_data.get("name"),
                                "path": install_result.get("path"),
                            },
                        )
                    except Exception:
                        pass
                else:
                    logger.error(
                        "tool_invention: create_skill returned error for plan %s: %s",
                        plan_id, install_result.get("error"),
                    )
                    try:
                        from core.eventbus.bus import event_bus
                        event_bus.publish(
                            "cognitive_state.skill_install_failed",
                            {
                                "plan_id": plan_id,
                                "name": skill_data.get("name"),
                                "error": install_result.get("error"),
                            },
                        )
                    except Exception:
                        pass
            except Exception as exc:
                logger.error(
                    "tool_invention: create_skill raised for plan %s: %s",
                    plan_id, exc,
                )
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish(
                        "cognitive_state.skill_install_failed",
                        {
                            "plan_id": plan_id,
                            "name": skill_data.get("name"),
                            "error": str(exc),
                        },
                    )
                except Exception:
                    pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -15
```

Expected: 13 passed (7 from Task 2 + 2 from Task 3 + 4 from Task 4).

- [ ] **Step 5: Verify no Multi-step Planner regression**

```bash
conda run -n ai pytest tests/test_multistep_planner.py -v 2>&1 | tail -10
```

Expected: 26 passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/plan_proposals.py tests/test_tool_invention.py
git commit -m "feat(tool-invention): resolve_plan hook installs skill on approval"
```

---

## Task 5: propose_new_skill tool + handler + registration

**Files:**
- Modify: `core/tools/skill_engine_tools.py`
- Modify: `tests/test_tool_invention.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tool_invention.py`:

```python
def test_propose_new_skill_killswitch_returns_error(
    clean_plan_state, isolated_skills_root, monkeypatch,
):
    from core.tools import skill_engine_tools as set_

    class FakeSettings:
        tool_invention_enabled = False

    monkeypatch.setattr(set_, "load_settings", lambda: FakeSettings())

    result = set_._exec_propose_new_skill({
        "name": "x",
        "description": "x",
        "instructions": "x",
        "session_id": "s1",
    })
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_propose_new_skill_validation_failure_returns_error(
    clean_plan_state, isolated_skills_root,
):
    from core.tools import skill_engine_tools as set_

    result = set_._exec_propose_new_skill({
        "name": "BAD!NAME",  # invalid regex
        "description": "x",
        "instructions": "x",
        "session_id": "s1",
    })
    assert result["status"] == "error"


def test_propose_new_skill_valid_proposal_creates_plan(
    clean_plan_state, isolated_skills_root,
):
    from core.tools import skill_engine_tools as set_
    from core.services.plan_proposals import _load_all

    result = set_._exec_propose_new_skill({
        "name": "auto-renamer",
        "description": "Renames files based on content",
        "instructions": "When given a file, rename it based on its content.",
        "use_when": "When user asks for batch rename",
        "tags": ["filesystem"],
        "session_id": "s1",
    })
    assert result["status"] == "ok"
    plan_id = result["plan_id"]

    plans = _load_all()
    assert plans[plan_id]["status"] == "awaiting_approval"
    assert plans[plan_id]["skill_data"]["name"] == "auto-renamer"


def test_propose_new_skill_registered_in_tool_definitions(monkeypatch):
    """The new tool is exposed via SKILL_ENGINE_TOOL_DEFINITIONS
    and SKILL_ENGINE_TOOL_HANDLERS."""
    from core.tools.skill_engine_tools import (
        SKILL_ENGINE_TOOL_DEFINITIONS,
        SKILL_ENGINE_TOOL_HANDLERS,
    )

    names = [
        (entry.get("function") or {}).get("name")
        for entry in SKILL_ENGINE_TOOL_DEFINITIONS
        if isinstance(entry, dict)
    ]
    assert "propose_new_skill" in names
    assert "propose_new_skill" in SKILL_ENGINE_TOOL_HANDLERS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -10
```

Expected: 4 new tests fail with `AttributeError` (no `_exec_propose_new_skill`) and `propose_new_skill` not in definitions.

- [ ] **Step 3: Add load_settings import to skill_engine_tools**

In `core/tools/skill_engine_tools.py`, near the top imports, ensure `load_settings` is available:

```bash
grep -n "from core.runtime.settings" /media/projects/jarvis-v2/core/tools/skill_engine_tools.py | head -3
```

If `load_settings` is not imported, add:

```python
from core.runtime.settings import load_settings
```

near the other `from core.*` imports.

- [ ] **Step 4: Add _exec_propose_new_skill handler**

In `core/tools/skill_engine_tools.py`, find `def _exec_skill_create(args: dict[str, Any]) -> dict[str, Any]:` (around line 170). Add the new handler right above it:

```python
def _exec_propose_new_skill(args: dict[str, Any]) -> dict[str, Any]:
    """Propose a new skill via the plan-approval flow.

    Validates the proposal up front. If validation fails, returns the
    error to the caller. If validation passes, creates a plan with the
    skill_data payload; when the plan is approved, the install hook
    automatically calls create_skill().
    """
    try:
        if not bool(load_settings().tool_invention_enabled):
            return {"status": "error", "error": "tool_invention disabled"}
    except Exception:
        pass  # fail-open if settings broken

    name = str(args.get("name") or "")
    description = str(args.get("description") or "")
    instructions = str(args.get("instructions") or "")
    use_when = str(args.get("use_when") or "") or description
    tags = list(args.get("tags") or [])

    from core.services.skill_engine import validate_skill_proposal
    validation = validate_skill_proposal(
        name=name,
        description=description,
        instructions=instructions,
        use_when=use_when,
        tags=tags,
    )
    if validation.get("status") != "ok":
        return validation

    # Use the normalized name from validation (it lowercases + space→hyphen)
    normalized_name = str(validation.get("name") or name)

    from core.services.plan_proposals import propose_plan
    result = propose_plan(
        session_id=args.get("session_id"),
        title=f"Ny skill: {normalized_name}",
        why=description,
        steps=[f"Install skill '{normalized_name}' (auto on approval)"],
        skill_data={
            "name": normalized_name,
            "description": description,
            "instructions": instructions,
            "use_when": use_when,
            "tags": tags,
        },
    )
    if result.get("status") == "ok":
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "cognitive_state.skill_proposed",
                {
                    "plan_id": result.get("plan_id"),
                    "name": normalized_name,
                },
            )
        except Exception:
            pass
    return result
```

- [ ] **Step 5: Add tool definition + register handler**

In `core/tools/skill_engine_tools.py`, find `SKILL_ENGINE_TOOL_DEFINITIONS: list[dict[str, Any]] = [` (around line 640). Find the end of the list (right before the closing `]`). Add this new entry as the LAST item in the list:

```python
    {
        "type": "function",
        "function": {
            "name": "propose_new_skill",
            "description": (
                "Foreslå en ny skill du selv mener du har brug for. Værktøjet "
                "validerer at navn+content er installerbart, lægger forslaget "
                "som en plan der venter på godkendelse. Når brugeren godkender, "
                "installeres skillen automatisk via skill_engine.create_skill()."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "lowercase, alphanumeric + - + _ (matches ^[a-z0-9][a-z0-9_-]*$)",
                    },
                    "description": {
                        "type": "string",
                        "description": "én sætning om hvad skillen gør",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "SKILL.md body (markdown). Skal være konkret nok til at en frisk session kan følge den.",
                    },
                    "use_when": {
                        "type": "string",
                        "description": "trigger-beskrivelse: hvornår skal denne skill påberåbes? Default = description.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "valgfrie tags til søgbarhed",
                    },
                },
                "required": ["name", "description", "instructions"],
            },
        },
    },
```

In the same file, find `SKILL_ENGINE_TOOL_HANDLERS: dict[str, Any] = {` (around line 873). Add to the dict (place right before the closing `}` or among the other entries):

```python
    "propose_new_skill": _exec_propose_new_skill,
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_tool_invention.py -v 2>&1 | tail -15
```

Expected: 17 passed.

- [ ] **Step 7: Verify tool reachable via simple_tools**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = [(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)]
assert 'propose_new_skill' in names, f'not in TOOL_DEFINITIONS: {len(names)} names'
assert 'propose_new_skill' in _TOOL_HANDLERS, 'not in _TOOL_HANDLERS'
print('OK: propose_new_skill registered via simple_tools')
"
```

Expected: `OK: propose_new_skill registered via simple_tools`

- [ ] **Step 8: Commit**

```bash
git add core/tools/skill_engine_tools.py tests/test_tool_invention.py
git commit -m "feat(tool-invention): propose_new_skill tool + handler + registration"
```

---

## Task 6: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Unconscious modulation Phase 1 smoke block and add right after it:

```python
        # Tool Invention Phase 1 (AGI track — added 2026-05-12)
        try:
            from core.services.skill_engine import (  # noqa: F401
                validate_skill_proposal,
                _collect_registered_tool_names,
            )
            from core.tools.skill_engine_tools import (  # noqa: F401
                _exec_propose_new_skill,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _names = [
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            ]
            if "propose_new_skill" not in _names:
                raise RuntimeError("propose_new_skill not in TOOL_DEFINITIONS")
            if "propose_new_skill" not in _TOOL_HANDLERS:
                raise RuntimeError("propose_new_skill not in _TOOL_HANDLERS")
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_tool_invention.py tests/test_multistep_planner.py tests/test_unconscious_modulation.py 2>&1 | tail -10
```

Expected: all green.

- [ ] **Step 3: Production probe — verify tool listed**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS
defs = [e for e in TOOL_DEFINITIONS if isinstance(e, dict) and (e.get('function') or {}).get('name') == 'propose_new_skill']
assert len(defs) == 1
print('OK: propose_new_skill tool definition present')
print('params:', list((defs[0]['function']['parameters'].get('properties') or {}).keys()))
"
```

Expected: `OK` + parameter list (`name`, `description`, `instructions`, `use_when`, `tags`).

- [ ] **Step 4: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Tool Invention Phase 1 (AGI track #9) — 30-day review: '
    'count proposed skills (zero is meaningful — Jarvis may have forgotten), '
    'count approved + installed, count dismissed, '
    'read installed SKILL.md content for kvalitet vurdering, '
    'Bjorns subjektive: virker tool? Er forslagene gode? '
    'check eventbus for skill_proposed / skill_installed / skill_install_failed events, '
    'decide: keep / tune / deprecate / proceed to Phase 1.1 (daily nudge-scanner).'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='tool_invention_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 5: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(tool-invention): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `tool_invention_enabled` | Task 1 |
| `validate_skill_proposal` helper | Task 2 step 3 |
| Shadow-check against tool names | Task 2 step 3 (`_collect_registered_tool_names`) |
| `propose_plan` accepts `skill_data` kwarg | Task 3 step 3 |
| `skill_data` stored on plan record | Task 3 step 3 |
| `resolve_plan` install hook | Task 4 step 3 |
| Event `cognitive_state.skill_installed` | Task 4 step 3 |
| Event `cognitive_state.skill_install_failed` | Task 4 step 3 |
| Event `cognitive_state.skill_proposed` | Task 5 step 4 |
| I/O failure logged not raised | Task 4 step 3 (try/except) |
| Tool definition + handler | Task 5 steps 4-5 |
| Kill-switch returns error | Task 5 step 4 |
| Validation runs before plan creation | Task 5 step 4 |
| Smoke imports | Task 6 step 1 |
| 30-day review | Task 6 step 4 |
| Backwards compat (existing 109 plans) | Task 3 step 3 (skill_data defaults None) |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `validate_skill_proposal(name: str, description: str, instructions: str, use_when: str = "", tags: list[str] | None = None) -> dict[str, Any]` — consistent across Tasks 2, 5
- `_collect_registered_tool_names() -> set[str]` — Task 2
- `propose_plan` new kwarg: `skill_data: dict[str, Any] | None = None` — consistent across Tasks 3, 5
- Plan record `skill_data` key — populated in propose, read in resolve_plan
- `_exec_propose_new_skill(args: dict[str, Any]) -> dict[str, Any]` — Tasks 5, 6

**Backwards-compat verified:**
- `propose_plan` callers without `skill_data` work unchanged (Task 3, default None).
- `resolve_plan` only fires install when `skill_data` is a dict (existing 109 plans don't have field → no install attempt).
- `create_skill()` public signature unchanged. Validation logic now in shared helper (`validate_skill_proposal`) which `create_skill()` does NOT need to call — both paths have the same checks (`create_skill` keeps its own inline validation; helper duplicates the logic deliberately to avoid changing `create_skill`'s control flow in Phase 1). If at any point we want pure DRY, `create_skill()` can be refactored to call the helper, but that's a separate concern.
- `SKILL_ENGINE_TOOL_DEFINITIONS`/`SKILL_ENGINE_TOOL_HANDLERS` are extended additively. `simple_tools.py` splats them unchanged.
- Kill-switch `tool_invention_enabled=False` → tool returns error immediately; no plan created; no install.
- All existing tests pass (verified explicitly for Multi-step Planner + Unconscious Modulation).
