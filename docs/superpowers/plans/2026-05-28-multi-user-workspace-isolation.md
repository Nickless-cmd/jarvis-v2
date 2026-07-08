---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Multi-User Workspace Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap between existing per-user workspace dirs (mikkel, michelle) and the ~75 hardcoded `workspaces/default/` references across services, so each user's relation-state is isolated while Jarvis-state stays shared (one entity).

**Architecture:** Three-layer split: `shared/` (Jarvis-state), `workspaces/<user>/` (per-relation), and per-user tagging on DB tables for queueable things (scheduled_tasks, initiatives, approvals). A new `core/runtime/workspace_paths.py` helper resolves paths from `workspace_context.current_user_id()` — services read via helper, never hardcoded. ContextVars already propagate into threads (`visible_runs.py:607`).

**Tech Stack:** Python 3.11, SQLite via `core/runtime/db.py`, pytest. Conda env at `/opt/conda/envs/ai/bin/python`.

**Spec:** `docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md`

**Scope adjustments from spec discovered during scouting:**
- GTR has no `ground_truth_facts` table — it's a Python dict (`INFRASTRUCTURE_FACTS`) + computed-on-read DB queries. All inherently Jarvis-scoped; no schema migration needed. The "split GTR by scope" intent is already satisfied structurally because user-specific knowledge lives in per-workspace USER.md.
- File-based daemons (`creative_impulse`, `shadow_scan`, `autonomous_work`) use JSON files, not DB tables. Their migration is "move file to `shared/`" (Task 5), no per-row tagging needed.
- DB tables that DO need `relevant_to_users` tagging are: `cognitive_chronicle_entries`, `runtime_initiatives`, `cognitive_dream_hypotheses`, `runtime_dream_hypothesis_signals`, `runtime_dream_adoption_candidates`, `runtime_dream_influence_proposals`.

---

## File Structure

**New files:**
- `core/runtime/workspace_paths.py` — `shared_dir()`, `workspace_dir()`, `_user_id_to_workspace_name()`, `NoUserContextError`
- `tests/runtime/test_workspace_paths.py` — unit tests for the helper
- `tests/multi_user/test_e2e_isolation.py` — end-to-end concurrent-users test
- `tests/multi_user/__init__.py`
- `docs/multi_user_workspace_layout.md` — operator-facing doc

**Modified files (read-side migration in Task 3):**
- `core/services/memory_search.py` (line 32, 34, 153, 178)
- `core/services/hallucination_guard.py` (line 149, 167)
- `core/services/memory_resurfacing.py`
- `core/services/cross_session_threads.py`
- `core/services/ground_truth_registry.py` (verify only — likely no change)
- `core/services/relation_dynamics.py`
- `core/services/day_shape_memory.py`
- `core/services/creative_impulse_daemon.py` (line 30-31)
- `core/services/shadow_scan_daemon.py` (line 30-31)
- `core/services/autonomous_work_daemon.py` (line 34)
- `core/services/dream_consolidation_daemon.py`
- `core/services/dream_carry_over.py`
- `core/services/deep_reflection_slot.py`
- `core/services/file_watch_daemon.py`
- `core/services/jobs_engine.py`
- `core/services/autonomous_outreach_daemon.py`
- `core/services/prompt_mutation_loop.py`
- `core/services/scheduled_job_windows.py`
- `core/services/memory_write_policy.py`
- `core/services/consent_registry.py`
- `core/services/arc_rule_extractor.py`
- `core/services/action_router.py`
- `core/services/reboot_awareness_daemon.py`
- `core/services/relational_warmth.py`
- `core/services/remembered_fact_signal_tracking.py`
- `core/services/dream_consolidation_daemon.py`
- `core/services/automation_dsl.py`
- `core/services/creative_projects.py`
- `core/tools/tiktok_content_tools.py`
- (Audit list will be completed in Task 3 Step 1 via grep — should match ~30 files)

**Schema migration (Task 2):**
- `core/runtime/db.py` — add columns to `scheduled_tasks`, `runtime_initiatives`, `capability_approval_requests`, `tool_intent_approval_requests`, `cognitive_chronicle_entries`, `cognitive_dream_hypotheses`, `runtime_dream_hypothesis_signals`, `runtime_dream_adoption_candidates`, `runtime_dream_influence_proposals`

**Filesystem changes (Task 5):**
- `~/.jarvis-v2/shared/` created
- Jarvis-state copied from `workspaces/default/` to `shared/`
- `workspaces/default/` renamed to `workspaces/bjorn/`
- `~/.jarvis-v2/config/users.json` — Bjørn's workspace updated to `bjorn`

---

## Task 1: Foundation API

**Goal:** Introduce `workspace_paths.py` helper. Zero behavior change yet (returns same paths as before).

**Files:**
- Create: `core/runtime/workspace_paths.py`
- Create: `tests/runtime/test_workspace_paths.py`
- Create: `tests/runtime/__init__.py` (if missing)

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_workspace_paths.py`:

```python
"""Tests for workspace_paths helper — see plan task 1."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.runtime.workspace_paths import (
    NoUserContextError,
    shared_dir,
    workspace_dir,
    _user_id_to_workspace_name,
)


def test_shared_dir_returns_default_during_transition(monkeypatch, tmp_path):
    """During migration, shared_dir() returns workspaces/default for
    backwards compat. Switched to shared/ in Task 5."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    expected = tmp_path / "workspaces" / "default"
    assert shared_dir() == expected


def test_workspace_dir_for_known_owner(monkeypatch, tmp_path):
    """Bjørn's discord_id resolves to workspaces/default during
    transition (renamed to bjorn in Task 5)."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Bjørn's discord_id from users.json
    result = workspace_dir(user_id="1246415163603816499")
    assert result == tmp_path / "workspaces" / "default"


def test_workspace_dir_for_member_user(monkeypatch, tmp_path, users_json):
    """Member user_id resolves to their named workspace dir."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Mikkel's discord_id from users.json
    result = workspace_dir(user_id="238975101381378048")
    assert result == tmp_path / "workspaces" / "mikkel"


def test_workspace_dir_raises_without_context(monkeypatch, tmp_path):
    """No user_id and no context → loud error, never silent default."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    with pytest.raises(NoUserContextError):
        workspace_dir()  # no user_id arg, no context set


def test_workspace_dir_uses_current_user_id_when_unset(monkeypatch, tmp_path):
    """workspace_dir() reads current_user_id() from workspace_context."""
    from core.identity.workspace_context import set_context, reset_context
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    token = set_context(workspace_name="mikkel", user_id="238975101381378048")
    try:
        result = workspace_dir()
        assert result == tmp_path / "workspaces" / "mikkel"
    finally:
        reset_context(token)


def test_unknown_user_id_raises(monkeypatch, tmp_path):
    """Unknown discord_id → NoUserContextError, never falls back to default."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    with pytest.raises(NoUserContextError):
        workspace_dir(user_id="not-a-real-discord-id-9999")


@pytest.fixture
def users_json(tmp_path, monkeypatch):
    """Provide a users.json under test HOME so find_user_by_discord_id resolves."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "users.json").write_text("""
{
  "users": [
    {"discord_id": "1246415163603816499", "name": "Bjørn", "role": "owner", "workspace": "default", "created_at": "2026-04-22T00:00:00Z"},
    {"discord_id": "238975101381378048", "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-04-30T00:00:00Z"}
  ]
}
""")
    # users.py reads HOME-relative; ensure it resolves to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    yield
```

Also create `tests/runtime/__init__.py` (empty file) if it doesn't exist:

```bash
touch tests/runtime/__init__.py
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/runtime/test_workspace_paths.py -v
```

Expected: All tests FAIL with `ModuleNotFoundError: No module named 'core.runtime.workspace_paths'`.

- [ ] **Step 3: Implement the helper**

Create `core/runtime/workspace_paths.py`:

```python
"""Workspace path resolver — single source of truth for filesystem layout.

Replaces ~75 hardcoded `workspaces/default/` references across services.
Routes per-user requests to their workspace dir; routes Jarvis-state
requests to the shared dir.

During the transition (Tasks 1-4), shared_dir() and the owner's
workspace_dir() both return `workspaces/default/` for backwards compat.
Task 5 switches shared_dir() to `shared/` and renames default → bjorn.

See: docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md
"""
from __future__ import annotations

import os
from pathlib import Path


class NoUserContextError(RuntimeError):
    """Raised when workspace_dir() is called without a resolvable user_id.

    This is intentionally loud — we prefer a visible crash over a silent
    fallback to default/ that would leak the owner's data into a member's
    session.
    """


def _jarvis_home() -> Path:
    """JARVIS_HOME resolved at call time (so tests can override via env)."""
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def shared_dir() -> Path:
    """Jarvis' own state. All users see the same instance.

    Contains: SOUL.md, IDENTITY.md, MANIFEST.md, INNER_VOICE.md,
    CHRONICLE.md, dreams/, creative_impulse/, shadow_scan/, etc.

    Transition note: until Task 5, returns workspaces/default/ for
    backwards compat. After Task 5, returns shared/.
    """
    return _jarvis_home() / "workspaces" / "default"


def workspace_dir(user_id: str | None = None) -> Path:
    """Per-relation workspace. Defaults to current_user_id() from context.

    Contains: MEMORY.md, USER.md (per-relation state).

    Args:
        user_id: explicit discord_id. If None, reads from workspace_context.
                 If unresolvable → NoUserContextError (never silent default).

    Raises:
        NoUserContextError: when user_id is empty and no context is set,
                            or when user_id is not in users.json.
    """
    if not user_id:
        from core.identity.workspace_context import current_user_id
        user_id = current_user_id()
    if not user_id:
        raise NoUserContextError(
            "workspace_dir() called without user_id arg and no current_user_id() "
            "in context. Caller must either pass user_id= explicitly or be inside "
            "a user_context() / set_context() block."
        )
    workspace_name = _user_id_to_workspace_name(user_id)
    return _jarvis_home() / "workspaces" / workspace_name


def _user_id_to_workspace_name(user_id: str) -> str:
    """Resolve discord_id → workspace folder name via users.json.

    Raises NoUserContextError if user_id is not registered.
    """
    from core.identity.users import find_user_by_discord_id
    user = find_user_by_discord_id(str(user_id).strip())
    if user is None:
        raise NoUserContextError(
            f"user_id={user_id!r} not found in users.json — refusing to default "
            "to 'default' workspace (would leak owner data). Register the user "
            "with scripts/users_cli.py add, or pass an explicit user_id."
        )
    return user.workspace
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/runtime/test_workspace_paths.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/workspace_paths.py tests/runtime/test_workspace_paths.py tests/runtime/__init__.py
git commit -m "feat(workspace-paths): foundation helper for multi-user isolation

Introduces shared_dir() (Jarvis-state) and workspace_dir(user_id)
(per-relation state). During the transition both still resolve to
workspaces/default/ so existing services are not yet affected.
NoUserContextError raised loudly when user_id can't be resolved —
better a crash than a silent leak.

Group 1 of 7 in the multi-user isolation refactor."
```

---

## Task 2: Schema Migrations

**Goal:** Add per-user tagging columns to DB tables. Additive only — existing rows get conservative defaults, existing queries unchanged.

**Files:**
- Modify: `core/runtime/db.py` — add columns to 9 tables (see list below)
- Create: `tests/runtime/test_db_schema_multiuser.py`

- [ ] **Step 1: Locate each CREATE TABLE statement**

Run:
```bash
grep -nE "CREATE TABLE IF NOT EXISTS (scheduled_tasks|runtime_initiatives|capability_approval_requests|tool_intent_approval_requests|cognitive_chronicle_entries|cognitive_dream_hypotheses|runtime_dream_hypothesis_signals|runtime_dream_adoption_candidates|runtime_dream_influence_proposals)" core/runtime/db.py
```

Expected: 9 line numbers. Confirm each exists before continuing.

- [ ] **Step 2: Write the failing schema test**

Create `tests/runtime/test_db_schema_multiuser.py`:

```python
"""Tests that DB schema includes multi-user attribution columns.

After Task 2, these columns exist on all listed tables. Each defaults to
NULL so existing rows are still valid and unfiltered queries see them all.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# Tables that need scheduled_for_user_id (work queued for a specific user)
SCHEDULING_TABLES = [
    "scheduled_tasks",
    "runtime_initiatives",
    "capability_approval_requests",
    "tool_intent_approval_requests",
]

# Tables that need relevant_to_users (Jarvis-state with optional relation tags)
RELEVANCE_TABLES = [
    "cognitive_chronicle_entries",
    "cognitive_dream_hypotheses",
    "runtime_dream_hypothesis_signals",
    "runtime_dream_adoption_candidates",
    "runtime_dream_influence_proposals",
]


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Spin up a fresh sqlite db at JARVIS_HOME/state/jarvis.db and let
    core.runtime.db initialise its schema."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "jarvis.db"

    # Re-import db module under the new env so it picks up the new path
    import importlib
    import core.runtime.db as dbmod
    importlib.reload(dbmod)

    with dbmod.connect() as conn:
        # connect() runs CREATE TABLE IF NOT EXISTS for all tables
        pass
    return db_path


def _column_names(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]
    finally:
        conn.close()


@pytest.mark.parametrize("table", SCHEDULING_TABLES)
def test_scheduling_table_has_user_id_columns(fresh_db, table):
    cols = _column_names(fresh_db, table)
    assert "scheduled_for_user_id" in cols, f"{table} missing scheduled_for_user_id"
    assert "initiated_by" in cols, f"{table} missing initiated_by"


@pytest.mark.parametrize("table", RELEVANCE_TABLES)
def test_relevance_table_has_relevant_to_users(fresh_db, table):
    cols = _column_names(fresh_db, table)
    assert "relevant_to_users" in cols, f"{table} missing relevant_to_users"


def test_existing_rows_have_null_defaults(fresh_db):
    """Insert a row in the bare-minimum existing schema, verify new
    columns default to NULL (= no filter restriction)."""
    conn = sqlite3.connect(str(fresh_db))
    try:
        conn.execute(
            "INSERT INTO scheduled_tasks (task_id, focus, source, status, run_at, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-1", "test focus", "test", "pending", "2026-01-01", "2026-01-01", "2026-01-01"),
        )
        row = conn.execute(
            "SELECT scheduled_for_user_id, initiated_by FROM scheduled_tasks WHERE task_id=?",
            ("test-1",),
        ).fetchone()
        assert row == (None, None)
    finally:
        conn.close()
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/runtime/test_db_schema_multiuser.py -v
```

Expected: tests FAIL with `assert "scheduled_for_user_id" in cols`.

- [ ] **Step 4: Add columns to each CREATE TABLE in `core/runtime/db.py`**

For each of the 4 SCHEDULING_TABLES, add inside the table definition (just before the closing `)`):

```
            scheduled_for_user_id TEXT,
            initiated_by TEXT,
```

For each of the 5 RELEVANCE_TABLES, add inside the table definition (just before the closing `)`):

```
            relevant_to_users TEXT,
```

(`relevant_to_users` stores a JSON array string like `'["user_id_1", "user_id_2"]'` or NULL.)

**Important**: these are NEW columns on existing tables. Existing production DBs need an `ALTER TABLE` migration too — see Step 5.

- [ ] **Step 5: Add idempotent ALTER TABLE migrations**

In `core/runtime/db.py`, find the section after all CREATE TABLE definitions where additive migrations live (search for existing `ALTER TABLE ... ADD COLUMN` patterns). Add a new migration block:

```python
def _ensure_multiuser_columns(conn: sqlite3.Connection) -> None:
    """Additive: tag scheduling tables with scheduled_for_user_id +
    initiated_by, and inner-life tables with relevant_to_users. Idempotent
    via existing-column check.

    Part of multi-user workspace isolation refactor — see plan doc
    2026-05-28-multi-user-workspace-isolation.md task 2.
    """
    scheduling_tables = (
        "scheduled_tasks",
        "runtime_initiatives",
        "capability_approval_requests",
        "tool_intent_approval_requests",
    )
    relevance_tables = (
        "cognitive_chronicle_entries",
        "cognitive_dream_hypotheses",
        "runtime_dream_hypothesis_signals",
        "runtime_dream_adoption_candidates",
        "runtime_dream_influence_proposals",
    )

    def _existing_cols(table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    for tbl in scheduling_tables:
        cols = _existing_cols(tbl)
        if "scheduled_for_user_id" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN scheduled_for_user_id TEXT")
        if "initiated_by" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN initiated_by TEXT")

    for tbl in relevance_tables:
        cols = _existing_cols(tbl)
        if "relevant_to_users" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN relevant_to_users TEXT")
```

Find the `connect()` function in `core/runtime/db.py` and add a call to `_ensure_multiuser_columns(conn)` after the other `_ensure_*` calls (search for an existing `_ensure_scheduled_tasks_table(conn)` call and add right after).

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/runtime/test_db_schema_multiuser.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Smoke-test against the live DB**

Run:
```bash
/opt/conda/envs/ai/bin/python -c "
from core.runtime.db import connect
import sqlite3
with connect() as conn:
    cols = {row[1] for row in conn.execute('PRAGMA table_info(scheduled_tasks)')}
    print('scheduled_tasks cols:', sorted(cols))
    assert 'scheduled_for_user_id' in cols
    assert 'initiated_by' in cols
    print('OK — live DB migrated')
"
```

Expected output: prints column list including the new columns, then `OK — live DB migrated`.

- [ ] **Step 8: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_db_schema_multiuser.py
git commit -m "feat(db): per-user attribution columns on scheduling + dream tables

Additive ALTER TABLE migrations for multi-user isolation:

scheduling tables (scheduled_for_user_id, initiated_by):
  - scheduled_tasks
  - runtime_initiatives
  - capability_approval_requests
  - tool_intent_approval_requests

relevance tables (relevant_to_users JSON array):
  - cognitive_chronicle_entries
  - cognitive_dream_hypotheses
  - runtime_dream_hypothesis_signals
  - runtime_dream_adoption_candidates
  - runtime_dream_influence_proposals

All defaults NULL — existing rows are unchanged and unfiltered queries
still see them all. Group 2 of 7."
```

---

## Task 3: Service Path Migration

**Goal:** Replace hardcoded `workspaces/default` paths in services with `shared_dir()` / `workspace_dir()` helper calls. Zero behavior change for Bjørn — the helper still resolves to the same path during this transition.

**Note:** This is the largest task by line-count but mechanical. Split into three commits by concern to keep diffs reviewable.

**Files (read-side migration):** all from grep audit in Step 1.

### Task 3a: Audit + memory-layer services

- [ ] **Step 1: Generate the authoritative audit list**

Run:
```bash
grep -rn 'workspaces.*"default"\|workspaces/default' core/services/ core/runtime/ core/tools/ --include="*.py" | grep -v "\.pyc\|test_\|# " > /tmp/workspace-audit.txt
wc -l /tmp/workspace-audit.txt
cat /tmp/workspace-audit.txt
```

Expected: ~50-75 lines across ~25-30 files. Review the list before editing — flag any reference that's intentional (e.g. a backup-path constant, a doc string) and skip those.

- [ ] **Step 2: Migrate memory-layer services**

For each file below, replace the hardcoded path patterns:

**Pattern to find:**
```python
Path(JARVIS_HOME) / "workspaces" / "default"
```

**Replace with (if Jarvis-state):**
```python
shared_dir()
```

**Replace with (if per-relation state):**
```python
workspace_dir()  # resolves from current_user_id() in context
```

Add at top of each file:
```python
from core.runtime.workspace_paths import shared_dir, workspace_dir
```

Files in this commit (memory + identity reads — all use `shared_dir()` since MEMORY/USER are conceptually relation-state but during transition they live in default):

- `core/services/memory_search.py` (lines 32-34, 153, 178) → use `workspace_dir()` (memory IS per-relation)
- `core/services/hallucination_guard.py` (lines 149, 167) → use `workspace_dir()`
- `core/services/memory_resurfacing.py` → use `workspace_dir()`
- `core/services/cross_session_threads.py` → use `workspace_dir()`
- `core/services/memory_write_policy.py` → use `workspace_dir()`
- `core/services/relation_dynamics.py` → use `workspace_dir()`
- `core/services/relational_warmth.py` → use `workspace_dir()`
- `core/services/day_shape_memory.py` → use `workspace_dir()`
- `core/services/remembered_fact_signal_tracking.py` → use `workspace_dir()`

For each file, the diff looks like (example — `memory_search.py`):

```python
# Before:
def _workspace_dir() -> Path:
    return Path(JARVIS_HOME) / "workspaces" / "default"

# After:
from core.runtime.workspace_paths import workspace_dir as _ws_dir

def _workspace_dir() -> Path:
    return _ws_dir()  # resolves to current user's workspace
```

Keep the local `_workspace_dir()` wrapper if it's called many places in the file — just delegate to the helper.

- [ ] **Step 3: Run all tests + smoke-test as Bjørn**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/ -x --timeout=60 2>&1 | tail -30
```

Expected: any pre-existing tests that hit memory_search etc. still pass (they default to no-context, so workspace_dir() would raise NoUserContextError; verify tests set context or use direct user_id arg).

If tests fail because they don't set context, set context in test fixtures OR use the explicit form `workspace_dir(user_id=BJORN_DISCORD_ID)`.

Run the runtime smoke test:
```bash
/opt/conda/envs/ai/bin/python scripts/smoke_test_startup.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/memory_search.py core/services/hallucination_guard.py core/services/memory_resurfacing.py core/services/cross_session_threads.py core/services/memory_write_policy.py core/services/relation_dynamics.py core/services/relational_warmth.py core/services/day_shape_memory.py core/services/remembered_fact_signal_tracking.py
git commit -m "refactor(memory): use workspace_dir() helper instead of hardcoded paths

Migrates 9 memory-layer services to workspace_paths.workspace_dir().
Same path resolution today (still workspaces/default/) but each call
now respects current_user_id() — Mikkel's memory search will hit
Mikkel's workspace once context is set by the middleware.

Group 3a of 7."
```

### Task 3b: Daemons (file-based state)

- [ ] **Step 1: Migrate daemons**

These daemons store state as JSON files. Their content is Jarvis-state (his own creative impulses, shadow scans, work). Use `shared_dir()`.

Files in this commit:

- `core/services/creative_impulse_daemon.py` (lines 30-31):
  ```python
  # Before:
  _STORAGE_REL = "workspaces/default/runtime/creative_impulse.json"
  _CREATIVE_DIR_REL = "workspaces/default/memory/creative"

  # After:
  from core.runtime.workspace_paths import shared_dir
  # remove the constants, replace usages:
  # Path(JARVIS_HOME) / _STORAGE_REL  →  shared_dir() / "runtime" / "creative_impulse.json"
  # Path(JARVIS_HOME) / _CREATIVE_DIR_REL  →  shared_dir() / "memory" / "creative"
  ```

- `core/services/shadow_scan_daemon.py` (lines 30-31):
  ```python
  # Same pattern:
  # workspaces/default/runtime/shadow_scan.json  →  shared_dir() / "runtime" / "shadow_scan.json"
  # workspaces/default/SHADOW_LOG.md  →  shared_dir() / "SHADOW_LOG.md"
  ```

- `core/services/autonomous_work_daemon.py` (line 34):
  ```python
  # workspaces/default/runtime/autonomous_work_log.json  →  shared_dir() / "runtime" / "autonomous_work_log.json"
  ```

- `core/services/file_watch_daemon.py` — audit the references, use `shared_dir()` (file-watch is global)
- `core/services/dream_consolidation_daemon.py` — `shared_dir()` (dreams are Jarvis)
- `core/services/dream_carry_over.py` — `shared_dir()`
- `core/services/deep_reflection_slot.py` — `shared_dir()`
- `core/services/autonomous_outreach_daemon.py` — `shared_dir()`
- `core/services/reboot_awareness_daemon.py` — `shared_dir()` (Jarvis' own boot state)
- `core/services/collective_pulse_daemon.py` — `shared_dir()`

- [ ] **Step 2: Test + smoke**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/ -x --timeout=60 -k "daemon or impulse or shadow or dream or autonomous" 2>&1 | tail -30
/opt/conda/envs/ai/bin/python scripts/smoke_test_startup.py
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add core/services/creative_impulse_daemon.py core/services/shadow_scan_daemon.py core/services/autonomous_work_daemon.py core/services/file_watch_daemon.py core/services/dream_consolidation_daemon.py core/services/dream_carry_over.py core/services/deep_reflection_slot.py core/services/autonomous_outreach_daemon.py core/services/reboot_awareness_daemon.py core/services/collective_pulse_daemon.py
git commit -m "refactor(daemons): use shared_dir() for Jarvis-state file paths

Migrates 10 daemons that store JSON/Markdown state files. Each
represents Jarvis' own inner life (creative impulses, shadow scans,
autonomous work, dreams) — shared across all relations.

Group 3b of 7."
```

### Task 3c: Remaining services + tools

- [ ] **Step 1: Migrate remaining hits from the audit**

For each remaining file from `/tmp/workspace-audit.txt`, apply the helper:
- If it's about Jarvis (jobs, identity, system) → `shared_dir()`
- If it's about a user's data/relation → `workspace_dir()`

Likely remaining files:
- `core/services/jobs_engine.py` → `shared_dir()` (jobs queue is global)
- `core/services/prompt_mutation_loop.py` → `shared_dir()`
- `core/services/scheduled_job_windows.py` → `shared_dir()` (scheduling infra)
- `core/services/consent_registry.py` → `workspace_dir()` (per-user consent)
- `core/services/arc_rule_extractor.py` → `shared_dir()` (Jarvis' rules)
- `core/services/action_router.py` → audit each ref
- `core/services/automation_dsl.py` → audit
- `core/services/creative_projects.py` → `shared_dir()` (Jarvis' projects)
- `core/services/ground_truth_registry.py` → verify (likely no change needed)
- `core/tools/tiktok_content_tools.py` → audit
- Any other file from the grep that hasn't been touched

- [ ] **Step 2: Final audit — should be 0 hardcoded refs left**

Run:
```bash
grep -rn 'workspaces.*"default"\|workspaces/default' core/services/ core/runtime/ core/tools/ --include="*.py" | grep -v "\.pyc\|test_\|# \|workspace_paths.py"
```

Expected: empty output (or only legitimate references — e.g. doc strings, the helper itself, backups).

- [ ] **Step 3: Test + smoke**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/ --timeout=60 2>&1 | tail -30
/opt/conda/envs/ai/bin/python scripts/smoke_test_startup.py
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add -u core/services/ core/runtime/ core/tools/
git commit -m "refactor: complete service path migration to workspace helpers

Final pass — replaces remaining hardcoded workspaces/default refs
across jobs_engine, prompt_mutation_loop, scheduled_job_windows,
consent_registry, arc_rule_extractor, action_router, automation_dsl,
creative_projects, tiktok_content_tools, and others identified in
the audit.

After this commit, grep for 'workspaces/default' in core/services
should return zero non-comment hits. Group 3c of 7."
```

---

## Task 4: Permission Scope Filters

**Goal:** Apply user-context filters at query time so member users only see their own relation-state.

**Files:**
- Modify: `core/services/memory_search.py` — filter by workspace context
- Modify: `core/services/ground_truth_registry.py` — pass through (already Jarvis-scoped, verify)
- Modify: dream/chronicle/initiative readers — filter on `relevant_to_users`
- Modify: scheduled-task reader — filter on `scheduled_for_user_id`
- Modify: `apps/api/jarvis_api/middleware/jarvisx_user_routing.py` — owner-only path enforcement
- Create: `tests/multi_user/test_scope_filters.py`

- [ ] **Step 1: Write failing tests for scope filtering**

Create `tests/multi_user/__init__.py` (empty file).

Create `tests/multi_user/test_scope_filters.py`:

```python
"""Tests that member-user queries only see their own workspace + Jarvis-shared.

After Task 4, members get filtered results from memory, chronicle,
dreams, initiatives, scheduled_tasks.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def mu_db(tmp_path, monkeypatch):
    """Multi-user test DB. Seeds chronicle/initiatives/scheduled rows with
    different user_id tags so we can test filtering."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)

    # Seed users.json
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "users.json").write_text(json.dumps({
        "users": [
            {"discord_id": BJORN_ID, "name": "Bjørn", "role": "owner", "workspace": "default", "created_at": "2026-01-01"},
            {"discord_id": MIKKEL_ID, "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-01-01"},
        ]
    }))
    monkeypatch.setenv("HOME", str(tmp_path))

    import importlib
    import core.runtime.db as dbmod
    importlib.reload(dbmod)
    with dbmod.connect() as conn:
        # Seed chronicle entries: one untagged (Jarvis-general), one Bjørn-only, one Mikkel-only
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries (entry_id, kind, body, created_at, relevant_to_users) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c1", "note", "general jarvis thought", "2026-01-01", None),
        )
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries (entry_id, kind, body, created_at, relevant_to_users) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c2", "note", "bjorn-specific", "2026-01-01", json.dumps([BJORN_ID])),
        )
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries (entry_id, kind, body, created_at, relevant_to_users) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c3", "note", "mikkel-specific", "2026-01-01", json.dumps([MIKKEL_ID])),
        )
        # Seed scheduled tasks
        conn.execute(
            "INSERT INTO scheduled_tasks (task_id, focus, source, status, run_at, "
            "created_at, updated_at, scheduled_for_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("t1", "bjorn task", "jarvis-tool", "pending", "2026-01-01", "2026-01-01", "2026-01-01", BJORN_ID),
        )
        conn.execute(
            "INSERT INTO scheduled_tasks (task_id, focus, source, status, run_at, "
            "created_at, updated_at, scheduled_for_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("t2", "mikkel task", "jarvis-tool", "pending", "2026-01-01", "2026-01-01", "2026-01-01", MIKKEL_ID),
        )
    yield tmp_path / "state" / "jarvis.db"


def test_chronicle_filter_for_member_user(mu_db):
    """Mikkel sees Jarvis-general (NULL) and Mikkel-tagged, not Bjørn-tagged."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.cognitive_chronicle import query_chronicle_for_user

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        rows = query_chronicle_for_user()
        ids = {r["entry_id"] for r in rows}
        assert "c1" in ids, "missing untagged Jarvis-general entry"
        assert "c3" in ids, "missing Mikkel-tagged entry"
        assert "c2" not in ids, "leaked Bjørn-tagged entry to Mikkel"
    finally:
        reset_context(token)


def test_chronicle_filter_for_owner(mu_db):
    """Bjørn sees Jarvis-general + Bjørn-tagged (not Mikkel's by default)."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.cognitive_chronicle import query_chronicle_for_user

    token = set_context(workspace_name="default", user_id=BJORN_ID)
    try:
        rows = query_chronicle_for_user()
        ids = {r["entry_id"] for r in rows}
        assert "c1" in ids
        assert "c2" in ids
        assert "c3" not in ids, "Bjørn should not see Mikkel's chronicle in normal context"
    finally:
        reset_context(token)


def test_scheduled_tasks_filtered_by_user(mu_db):
    """Mikkel's scheduled-task list only contains his own."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.scheduled_tasks import list_pending_for_current_user

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        tasks = list_pending_for_current_user()
        task_ids = {t["task_id"] for t in tasks}
        assert "t2" in task_ids
        assert "t1" not in task_ids
    finally:
        reset_context(token)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/test_scope_filters.py -v
```

Expected: tests FAIL — either function doesn't exist, or returns unfiltered rows.

- [ ] **Step 3: Implement filtering in chronicle reader**

In `core/services/cognitive_chronicle.py` (or wherever chronicle queries live — grep for `cognitive_chronicle_entries`):

```python
def query_chronicle_for_user(limit: int = 50) -> list[dict]:
    """Return chronicle entries visible to the current user.

    Filter logic:
    - NULL relevant_to_users → visible to all (general Jarvis state)
    - JSON array containing current_user_id() → visible
    - Other → hidden
    """
    from core.identity.workspace_context import current_user_id
    from core.runtime.db import connect

    uid = current_user_id()
    with connect() as conn:
        if uid:
            rows = conn.execute(
                """
                SELECT entry_id, kind, body, created_at, relevant_to_users
                FROM cognitive_chronicle_entries
                WHERE relevant_to_users IS NULL
                   OR relevant_to_users LIKE '%' || ? || '%'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (uid, limit),
            ).fetchall()
        else:
            # No user context — owner-debug path, returns everything
            rows = conn.execute(
                "SELECT entry_id, kind, body, created_at, relevant_to_users "
                "FROM cognitive_chronicle_entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
```

(Note: the `LIKE '%' || ? || '%'` is a string-substring match on the JSON array. Cheap and correct since user_ids are long unique strings — no false positives expected.)

- [ ] **Step 4: Implement filtering in scheduled-tasks reader**

In `core/services/scheduled_tasks.py` (or wherever `list_pending_tasks` lives):

```python
def list_pending_for_current_user() -> list[dict]:
    """Return scheduled tasks where scheduled_for_user_id matches current user.

    Owner with no context binding sees all (debug). Untagged tasks
    (legacy rows) are visible to owner only.
    """
    from core.identity.workspace_context import current_user_id
    from core.runtime.db import connect

    uid = current_user_id()
    with connect() as conn:
        if uid:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks "
                "WHERE status='pending' AND scheduled_for_user_id = ? "
                "ORDER BY run_at ASC",
                (uid,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status='pending' ORDER BY run_at ASC"
            ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Apply equivalent filter to initiatives + dream readers**

Same pattern as chronicle:
- `core/services/runtime_initiatives.py` (or wherever) → filter by `relevant_to_users`
- `core/services/dream_*` readers → filter by `relevant_to_users`

For each reader function that returns rows to the prompt or UI, add the `WHERE relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%'` filter when `current_user_id()` is set.

- [ ] **Step 6: Run tests to verify pass**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/test_scope_filters.py -v
```

Expected: all PASS.

- [ ] **Step 7: Add owner-only path enforcement for shared writes**

In `apps/api/jarvis_api/middleware/jarvisx_user_routing.py`, after the auth-check block, add a role-check helper and wire it to the writes-to-Jarvis-state routes (admin endpoints). Example pattern:

```python
def _require_owner(token_claims: dict | None) -> None:
    """Raise 403 if the caller is not the owner. Used by routes that
    modify Jarvis' shared state (SOUL.md, IDENTITY.md, token mint, etc.)."""
    from fastapi import HTTPException
    role = (token_claims or {}).get("role", "")
    if role != "owner":
        raise HTTPException(status_code=403, detail="owner-only")
```

The new helper is callable by routes that need it. Existing routes that already check `role == 'owner'` inline don't need changes.

- [ ] **Step 8: Commit**

```bash
git add core/services/cognitive_chronicle.py core/services/scheduled_tasks.py core/services/runtime_initiatives.py core/services/dream_*.py apps/api/jarvis_api/middleware/jarvisx_user_routing.py tests/multi_user/__init__.py tests/multi_user/test_scope_filters.py
git commit -m "feat(scope-filters): per-user read filtering on chronicle, tasks, initiatives, dreams

Adds workspace-context filtering on read paths:
- cognitive_chronicle_entries: NULL or relevant_to_users contains current uid
- scheduled_tasks: scheduled_for_user_id = current uid
- runtime_initiatives, dream tables: same as chronicle

Tests verify Mikkel can't see Bjørn-tagged chronicle entries and only
sees his own scheduled tasks. Group 4 of 7."
```

---

## Task 5: Filesystem Reshuffle

**Goal:** Move Jarvis-state files from `workspaces/default/` to `shared/`. Rename `default/` to `bjorn/`. Update `users.json` and `shared_dir()` to point at the new location.

**Files:**
- Modify: `core/runtime/workspace_paths.py` — switch `shared_dir()` to return `shared/`
- Modify: `~/.jarvis-v2/config/users.json` — Bjørn's workspace becomes `bjorn`
- Modify: `core/identity/workspace_context.py` — default workspace name updated to `bjorn`

**Filesystem operations (run on both Linux dev and target via ssh):**

- [ ] **Step 1: Pre-flight backup**

Run:
```bash
tar -cz -f ~/.jarvis-v2/backups/pre-multiuser-reshuffle-$(date +%Y%m%d-%H%M%S).tar.gz -C ~/.jarvis-v2 workspaces config
```

Expected: tar archive created in `~/.jarvis-v2/backups/`. Verify with `tar -tz -f <archive> | head`.

- [ ] **Step 2: Define the Jarvis-state file list**

Files/dirs that are Jarvis-state and move from `workspaces/default/` to `shared/`:

```
SOUL.md
IDENTITY.md
MANIFEST.md
INNER_VOICE.md
CHRONICLE.md
STANDING_ORDERS.md
QUICK_FACTS.md
VOICE.md
SKILLS.md
TOOLS.md
VISIBLE_*.md  (chat rules, memory selection, etc.)
INHERITANCE_SEED.md
AFFECTIVE_STATE.md
AGENT_OUTCOMES.md
PLAN_*.md
COUNCIL_LOG.md
INCUBATOR.md
DREAM_*.md / DREAM_*.json
CONSENT_REGISTRY.json  (debatable — but global registry)
SHADOW_LOG.md
dreams/  (directory)
journal/  (directory)
letters/  (directory)
runtime/  (directory — daemon state)
memory/creative/  (sub-dir from creative_impulse)
jarvis_brain/  (if present)
docker-compose.yml  (deployment scaffolding)
double-take-config  (deployment scaffolding)
```

Files that STAY in `workspaces/default/` (will become `bjorn/`):

```
MEMORY.md
USER.md
multi_user_spec.md  (was Bjørn's note, relation-context)
multi_user_task_for_claude.md
chat_messages.db (if present here)
```

- [ ] **Step 3: Copy Jarvis-state to shared/**

Run:
```bash
mkdir -p ~/.jarvis-v2/shared

# Files
for f in SOUL.md IDENTITY.md MANIFEST.md INNER_VOICE.md CHRONICLE.md \
         STANDING_ORDERS.md QUICK_FACTS.md VOICE.md SKILLS.md TOOLS.md \
         INHERITANCE_SEED.md AFFECTIVE_STATE.md AGENT_OUTCOMES.md \
         COUNCIL_LOG.md INCUBATOR.md SHADOW_LOG.md \
         docker-compose.yml; do
    if [ -f ~/.jarvis-v2/workspaces/default/$f ]; then
        cp -a ~/.jarvis-v2/workspaces/default/$f ~/.jarvis-v2/shared/$f
    fi
done

# Glob-matched files
cp -a ~/.jarvis-v2/workspaces/default/VISIBLE_*.md ~/.jarvis-v2/shared/ 2>/dev/null || true
cp -a ~/.jarvis-v2/workspaces/default/PLAN_*.md ~/.jarvis-v2/shared/ 2>/dev/null || true
cp -a ~/.jarvis-v2/workspaces/default/DREAM_*.md ~/.jarvis-v2/shared/ 2>/dev/null || true
cp -a ~/.jarvis-v2/workspaces/default/DREAM_*.json ~/.jarvis-v2/shared/ 2>/dev/null || true

# Directories
for d in dreams journal letters runtime memory jarvis_brain double-take-config; do
    if [ -d ~/.jarvis-v2/workspaces/default/$d ]; then
        cp -a ~/.jarvis-v2/workspaces/default/$d ~/.jarvis-v2/shared/$d
    fi
done

ls -la ~/.jarvis-v2/shared/ | head -30
```

Expected: shared/ populated with the Jarvis-state files. Verify SOUL.md exists in shared/.

- [ ] **Step 4: Rename default → bjorn**

Run:
```bash
mv ~/.jarvis-v2/workspaces/default ~/.jarvis-v2/workspaces/bjorn
ls ~/.jarvis-v2/workspaces/
```

Expected output: `bjorn  michelle  mikkel  ...` — no `default`.

- [ ] **Step 5: Update users.json**

Run:
```bash
/opt/conda/envs/ai/bin/python -c "
import json
from pathlib import Path
p = Path.home() / '.jarvis-v2' / 'config' / 'users.json'
data = json.loads(p.read_text())
for u in data['users']:
    if u.get('name') == 'Bjørn' and u.get('workspace') == 'default':
        u['workspace'] = 'bjorn'
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
print('Updated:', json.dumps(data, indent=2, ensure_ascii=False))
"
```

Expected: Bjørn's `workspace` field changes from `default` to `bjorn`. Other users unchanged.

- [ ] **Step 6: Switch shared_dir() implementation**

Edit `core/runtime/workspace_paths.py`:

```python
def shared_dir() -> Path:
    """Jarvis' own state. All users see the same instance."""
    # Task 5: switched from workspaces/default to shared/
    return _jarvis_home() / "shared"
```

(Drop the transition note from the docstring.)

- [ ] **Step 7: Update workspace_context.py default**

Edit `core/identity/workspace_context.py`:

```python
# Default: workspace="bjorn", user_id="" (owner implicit when nothing is bound)
_DEFAULT_STATE = _ContextState(
    workspace_name="bjorn",  # was "default" — renamed Task 5
    user_id="",
    user_display_name="",
)
```

Also update the `user_context()` contextmanager's fallback in the same file:

```python
workspace_name = "bjorn"  # was "default"
```

(Search for both occurrences of `"default"` in the file and update.)

- [ ] **Step 8: Update test fixtures expecting "default"**

Run:
```bash
grep -rn '"default"\|workspace_name="default"\|workspaces/default' tests/ 2>/dev/null
```

For each test that asserts the old default name, update to expect `"bjorn"` OR set context explicitly. Particularly:
- `tests/runtime/test_workspace_paths.py` — already updated in Task 1 to expect new paths

- [ ] **Step 9: Restart Jarvis runtime locally + smoke**

Run:
```bash
/opt/conda/envs/ai/bin/python scripts/smoke_test_startup.py
```

Expected: PASS.

Run the API + runtime briefly to verify Jarvis boots:
```bash
timeout 20 /opt/conda/envs/ai/bin/python scripts/jarvis.py --help
```

Expected: prints help, exits cleanly. (Full startup test happens against target in Task 7.)

- [ ] **Step 10: Sync filesystem changes to target**

Run:
```bash
rsync -az ~/.jarvis-v2/shared/ bs@10.0.0.39:~/.jarvis-v2/shared/
ssh bs@10.0.0.39 'cd ~/.jarvis-v2/workspaces && [ -d default ] && mv default bjorn || echo "already renamed"'
rsync -az ~/.jarvis-v2/config/users.json bs@10.0.0.39:~/.jarvis-v2/config/users.json
```

(Don't restart target services yet — Task 7 does that after E2E tests pass.)

- [ ] **Step 11: Commit**

```bash
git add core/runtime/workspace_paths.py core/identity/workspace_context.py tests/runtime/test_workspace_paths.py
git commit -m "refactor(layout): introduce shared/ + rename default → bjorn

Filesystem reshuffle:
- Jarvis-state (SOUL, IDENTITY, MANIFEST, dreams/, etc) moves from
  workspaces/default/ to shared/
- workspaces/default/ renamed to workspaces/bjorn/ (relation-state only)
- users.json: Bjørn's workspace = bjorn
- shared_dir() now points at ~/.jarvis-v2/shared
- workspace_context default workspace_name = 'bjorn'

Copies of files were left in workspaces/bjorn/ during this commit to
keep the system bootable through the transition. Group 7 deletes the
duplicates.

Group 5 of 7."
```

---

## Task 6: Scheduling User-ID Binding

**Goal:** When a scheduled task fires, set `workspace_context` to its `scheduled_for_user_id` *before* dispatching. Stamp user_id on initiative queue, approvals, notifications at insert time.

**Files:**
- Modify: `core/services/scheduled_task_runner.py` (or wherever the dispatcher loop lives — grep for `fired_at`)
- Modify: `core/services/runtime_initiatives.py` — stamp user_id on insert
- Modify: notification dispatcher — stamp + bind
- Create: `tests/multi_user/test_scheduling_context.py`

- [ ] **Step 1: Locate the scheduled-task dispatcher**

Run:
```bash
grep -rn "fired_at\|fire_scheduled\|run_scheduled\|scheduled_tasks.*UPDATE\|status='completed'" core/services/ apps/ 2>/dev/null | grep -v "\.pyc\|test_" | head -10
```

Expected: finds the function that picks pending tasks and dispatches them. Likely in `core/services/scheduled_tasks.py` or a `*_runner.py`.

- [ ] **Step 2: Write the failing test**

Create `tests/multi_user/test_scheduling_context.py`:

```python
"""When a scheduled task fires, the dispatcher must set workspace_context
to the task's scheduled_for_user_id BEFORE calling the run function.
Otherwise Jarvis wakes up in default/owner context and operator tools
route to the wrong bridge.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def mu_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = tmp_path / "config"; cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "users.json").write_text(json.dumps({
        "users": [
            {"discord_id": BJORN_ID, "name": "Bjørn", "role": "owner", "workspace": "bjorn", "created_at": "2026-01-01"},
            {"discord_id": MIKKEL_ID, "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-01-01"},
        ]
    }))
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    import importlib
    import core.runtime.db as dbmod
    importlib.reload(dbmod)
    yield tmp_path


def test_dispatch_sets_user_context_from_scheduled_for_user_id(mu_env):
    """When a task tagged for Mikkel fires, the dispatcher sets context
    to Mikkel's user_id before invoking the run callback."""
    from core.identity.workspace_context import current_user_id
    from core.services.scheduled_task_runner import fire_scheduled_task

    seen_user_id = {}

    def fake_runner(focus: str, **kwargs):
        seen_user_id["uid"] = current_user_id()

    task = {
        "task_id": "test-1",
        "focus": "remind mikkel",
        "scheduled_for_user_id": MIKKEL_ID,
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert seen_user_id["uid"] == MIKKEL_ID


def test_dispatch_without_user_id_falls_back_loudly(mu_env, caplog):
    """A task with no scheduled_for_user_id must log a warning and
    skip rather than firing in random context."""
    from core.services.scheduled_task_runner import fire_scheduled_task

    fired = []
    def fake_runner(focus: str, **kwargs):
        fired.append(focus)

    task = {
        "task_id": "test-2",
        "focus": "untagged task",
        "scheduled_for_user_id": None,
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert fired == [], "untagged task should not fire"
    assert any("scheduled_for_user_id" in r.message for r in caplog.records)


def test_dispatch_missing_user_logs_and_drops(mu_env, caplog):
    """If scheduled_for_user_id no longer exists in users.json, log and drop."""
    from core.services.scheduled_task_runner import fire_scheduled_task

    fired = []
    def fake_runner(focus: str, **kwargs):
        fired.append(focus)

    task = {
        "task_id": "test-3",
        "focus": "ghost user task",
        "scheduled_for_user_id": "9999999999999999999",  # not in users.json
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert fired == []
    assert any("not found in users.json" in r.message or "unknown user" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/test_scheduling_context.py -v
```

Expected: tests FAIL (function doesn't exist or doesn't bind context).

- [ ] **Step 4: Implement `fire_scheduled_task`**

Create or edit `core/services/scheduled_task_runner.py`:

```python
"""Scheduled task dispatcher — binds workspace_context before firing.

Critical for multi-user: a task scheduled by Mikkel must wake Jarvis up
INTO Mikkel's relation, so memory injection reads Mikkel's MEMORY.md and
operator tools route to Mikkel's JarvisX bridge.

See plan: docs/superpowers/plans/2026-05-28-multi-user-workspace-isolation.md task 6
"""
from __future__ import annotations

import logging
from typing import Callable

from core.identity.users import find_user_by_discord_id
from core.identity.workspace_context import set_context, reset_context

logger = logging.getLogger(__name__)


def fire_scheduled_task(
    task: dict,
    *,
    runner: Callable[..., None],
) -> None:
    """Bind workspace_context to task's scheduled_for_user_id and run.

    Args:
        task: row dict from scheduled_tasks. Must have 'scheduled_for_user_id'
              and 'focus'. May have other fields, passed as kwargs to runner.
        runner: callable invoked with focus + extras. The context will be
                set BEFORE runner is called and reset AFTER.

    Behavior:
      - Empty/None scheduled_for_user_id → warn and skip
      - Unknown user_id (not in users.json) → warn and skip
      - Otherwise: set_context to the user, run, reset_context.
    """
    uid = (task.get("scheduled_for_user_id") or "").strip()
    if not uid:
        logger.warning(
            "fire_scheduled_task: task %r has no scheduled_for_user_id — skipping",
            task.get("task_id"),
        )
        return

    user = find_user_by_discord_id(uid)
    if user is None:
        logger.warning(
            "fire_scheduled_task: user_id=%s not found in users.json — dropping task %r",
            uid, task.get("task_id"),
        )
        return

    token = set_context(
        workspace_name=user.workspace,
        user_id=user.discord_id,
        user_display_name=user.name,
    )
    try:
        runner(focus=task["focus"], task_id=task.get("task_id"))
    finally:
        reset_context(token)
```

- [ ] **Step 5: Wire the new dispatcher to existing task loop**

Find the existing scheduled-task polling loop (grep from Step 1). Replace the direct runner call with a call through `fire_scheduled_task`:

```python
# Before:
start_visible_run(message=task["focus"], ...)

# After:
from core.services.scheduled_task_runner import fire_scheduled_task

def _run(focus: str, task_id: str | None = None):
    start_visible_run(message=focus, ...)

fire_scheduled_task(task, runner=_run)
```

- [ ] **Step 6: Stamp user_id on insert for queueable tables**

Find the insert paths for `runtime_initiatives`, `capability_approval_requests`, etc. Update each to include `current_user_id()`:

```python
from core.identity.workspace_context import current_user_id

# In each insert:
conn.execute(
    "INSERT INTO runtime_initiatives (..., scheduled_for_user_id, initiated_by) "
    "VALUES (..., ?, ?)",
    (..., current_user_id() or None, f"user:{current_user_id()}" if current_user_id() else "jarvis-self"),
)
```

- [ ] **Step 7: Run tests to verify pass**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/ -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add core/services/scheduled_task_runner.py core/services/scheduled_tasks.py core/services/runtime_initiatives.py tests/multi_user/test_scheduling_context.py
git commit -m "feat(scheduling): bind workspace_context from scheduled_for_user_id on fire

When a scheduled task fires, the dispatcher now reads its
scheduled_for_user_id, looks up the user in users.json, and calls
set_context() before invoking the run callback. This means Jarvis
wakes up INTO the right relation — memory injection reads that
user's MEMORY.md, and operator tools route to their bridge.

Missing/unknown user_ids are logged and dropped, never silently
fired in default context.

Insert paths for runtime_initiatives + approval tables now stamp
current_user_id() on insert.

Group 6 of 7."
```

---

## Task 7: Cleanup + End-to-End Tests

**Goal:** Remove transitional artefacts and verify the whole system works correctly with concurrent users.

**Files:**
- Modify: `core/runtime/workspace_paths.py` — remove backward-compat comments
- Delete: duplicate files in `workspaces/bjorn/` that were copied to `shared/`
- Create: `tests/multi_user/test_e2e_isolation.py`
- Create: `docs/multi_user_workspace_layout.md`

- [ ] **Step 1: Write the E2E test**

Create `tests/multi_user/test_e2e_isolation.py`:

```python
"""End-to-end test: simultaneous Bjørn + Mikkel sessions don't bleed.

Covers all the routing seams introduced in Tasks 1-6:
- memory_search reads correct workspace
- chronicle filters by user
- scheduled tasks fire in correct context
- operator tool dispatch goes to correct bridge (mocked)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = tmp_path / "config"; cfg.mkdir(parents=True)
    (cfg / "users.json").write_text(json.dumps({
        "users": [
            {"discord_id": BJORN_ID, "name": "Bjørn", "role": "owner", "workspace": "bjorn", "created_at": "2026-01-01"},
            {"discord_id": MIKKEL_ID, "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-01-01"},
        ]
    }))

    bjorn_ws = tmp_path / "workspaces" / "bjorn"
    mikkel_ws = tmp_path / "workspaces" / "mikkel"
    shared = tmp_path / "shared"
    for d in (bjorn_ws, mikkel_ws, shared):
        d.mkdir(parents=True)

    (bjorn_ws / "MEMORY.md").write_text("# Bjørn's memory\n\nworking on jarvis-v2.")
    (bjorn_ws / "USER.md").write_text("# Bjørn\nthe owner.")
    (mikkel_ws / "MEMORY.md").write_text("# Mikkel's memory\n\nshares a friendship with bjorn.")
    (mikkel_ws / "USER.md").write_text("# Mikkel\nbjorn's friend.")
    (shared / "SOUL.md").write_text("# Jarvis' soul\n\nI am Jarvis.")

    yield tmp_path


def test_memory_search_returns_only_current_user_workspace(e2e_env):
    """search in Bjørn-context hits bjorn/MEMORY.md; Mikkel-context hits mikkel/."""
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime.workspace_paths import workspace_dir

    token = set_context(workspace_name="bjorn", user_id=BJORN_ID)
    try:
        wd = workspace_dir()
        assert wd == e2e_env / "workspaces" / "bjorn"
        assert (wd / "MEMORY.md").read_text().startswith("# Bjørn's memory")
    finally:
        reset_context(token)

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        wd = workspace_dir()
        assert wd == e2e_env / "workspaces" / "mikkel"
        assert (wd / "MEMORY.md").read_text().startswith("# Mikkel's memory")
    finally:
        reset_context(token)


def test_shared_dir_unchanged_across_users(e2e_env):
    """Both users see the same SOUL.md (same Jarvis)."""
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime.workspace_paths import shared_dir

    soul_paths = []
    for uid, ws in [(BJORN_ID, "bjorn"), (MIKKEL_ID, "mikkel")]:
        token = set_context(workspace_name=ws, user_id=uid)
        try:
            soul_paths.append(shared_dir() / "SOUL.md")
        finally:
            reset_context(token)

    assert soul_paths[0] == soul_paths[1] == e2e_env / "shared" / "SOUL.md"
    assert soul_paths[0].read_text() == "# Jarvis' soul\n\nI am Jarvis."


def test_no_workspace_context_raises(e2e_env):
    """Without a user_context, workspace_dir() raises loudly."""
    from core.runtime.workspace_paths import workspace_dir, NoUserContextError
    with pytest.raises(NoUserContextError):
        workspace_dir()
```

- [ ] **Step 2: Run the E2E tests**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/ -v
```

Expected: all PASS.

- [ ] **Step 3: Run the full test suite**

Run:
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/ --timeout=60 2>&1 | tail -20
```

Expected: no regressions. Any pre-existing failures unrelated to this work should be unchanged.

- [ ] **Step 4: Clean up duplicated files in `workspaces/bjorn/`**

Files copied to `shared/` in Task 5 can now be removed from `workspaces/bjorn/`:

```bash
cd ~/.jarvis-v2/workspaces/bjorn
for f in SOUL.md IDENTITY.md MANIFEST.md INNER_VOICE.md CHRONICLE.md \
         STANDING_ORDERS.md QUICK_FACTS.md VOICE.md SKILLS.md TOOLS.md \
         INHERITANCE_SEED.md AFFECTIVE_STATE.md AGENT_OUTCOMES.md \
         COUNCIL_LOG.md INCUBATOR.md SHADOW_LOG.md docker-compose.yml; do
    if [ -f "$f" ] && [ -f ~/.jarvis-v2/shared/$f ]; then
        # double-check both exist and content matches before deletion
        diff -q "$f" ~/.jarvis-v2/shared/$f && rm "$f"
    fi
done

rm -f VISIBLE_*.md PLAN_*.md DREAM_*.md DREAM_*.json
rm -rf dreams journal letters runtime memory jarvis_brain double-take-config 2>/dev/null

ls ~/.jarvis-v2/workspaces/bjorn/
```

Expected: only relation-state remains (MEMORY.md, USER.md, etc.).

Repeat on target:
```bash
ssh bs@10.0.0.39 'cd ~/.jarvis-v2/workspaces/bjorn && ls'
# … run the same cleanup as above on target
```

- [ ] **Step 5: Write the layout doc**

Create `docs/multi_user_workspace_layout.md`:

```markdown
# Multi-User Workspace Layout

(One-page reference for what lives where. See spec
`docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md`
for design rationale.)

## Layout

\`\`\`
~/.jarvis-v2/
├── shared/                # Jarvis-state (one entity, all users see same)
│   ├── SOUL.md, IDENTITY.md, MANIFEST.md
│   ├── INNER_VOICE.md, CHRONICLE.md, STANDING_ORDERS.md
│   ├── dreams/, runtime/, journal/, letters/
│   └── (etc.)
│
├── workspaces/            # Per-relation state
│   ├── bjorn/             # MEMORY.md, USER.md, day_shape, threads
│   ├── mikkel/
│   └── michelle/
│
└── config/
    └── users.json         # discord_id → workspace name + role
\`\`\`

## API

In services, always resolve paths via the helper:

\`\`\`python
from core.runtime.workspace_paths import shared_dir, workspace_dir

shared_dir()      # → ~/.jarvis-v2/shared
workspace_dir()   # → ~/.jarvis-v2/workspaces/<current user's name>
workspace_dir(user_id="…")  # explicit override
\`\`\`

If `workspace_dir()` is called without a user_id and no context is set,
it raises `NoUserContextError`. This is deliberate — we want a loud
crash over a silent leak.

## When to use which

- **Per-relation state** (MEMORY.md, USER.md, day_shape, threads): `workspace_dir()`
- **Jarvis' own state** (SOUL, IDENTITY, dreams, creative impulses, jobs queue): `shared_dir()`
- **Per-user queued work** (scheduled_tasks, initiatives): DB row with `scheduled_for_user_id`,
  dispatcher binds context via `core.services.scheduled_task_runner.fire_scheduled_task`.

## Permissions

`role='member'` (Mikkel, Michelle):
- Can chat, use operator tools on their own machine, schedule their own tasks
- Cannot mint tokens or write to shared/ SOUL.md, IDENTITY.md, MANIFEST.md
- Read-filtered: see Jarvis-state + their own relation, never other users'.

`role='owner'` (Bjørn):
- Can do everything, can mint tokens, can write shared/
- In a normal session, sees Jarvis-state + Bjørn-relation only (same filter)
- Admin paths (Mission Control, debug tools) can bypass filter for observability.
```

- [ ] **Step 6: Final smoke + deploy**

Sync to target and restart:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && git pull --ff-only'
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api jarvis-runtime'
sleep 6
ssh bs@10.0.0.39 'sudo systemctl is-active jarvis-api jarvis-runtime'
ssh bs@10.0.0.39 'curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/health'
```

Expected: `active\nactive\n200`.

- [ ] **Step 7: Commit**

```bash
git add tests/multi_user/test_e2e_isolation.py docs/multi_user_workspace_layout.md
git add -u  # picks up any file deletions if tracked
git commit -m "test: end-to-end multi-user isolation + cleanup

E2E test verifies concurrent Bjørn/Mikkel sessions read from their
own workspaces and share Jarvis' state. Includes:
- workspace_dir() routes by context
- shared_dir() is invariant across users
- missing context raises loudly

Also cleans up duplicate files in workspaces/bjorn/ that were copied
to shared/ in Task 5.

Adds docs/multi_user_workspace_layout.md as the operator-facing
one-page reference.

Group 7 of 7 — refactor complete."
```

---

## Final Verification Checklist

After all 7 tasks committed:

- [ ] `git log --oneline | head -10` shows 7+ commits attributable to this refactor
- [ ] `grep -rn 'workspaces.*"default"\|workspaces/default' core/services/ core/runtime/ core/tools/ --include="*.py" | grep -v "_workspace_paths\|test_"` returns empty (or only intentional references)
- [ ] `tests/multi_user/` passes in full
- [ ] `scripts/smoke_test_startup.py` passes
- [ ] Live target services (`jarvis-api`, `jarvis-runtime`) are `active`
- [ ] Mikkel can chat via JarvisX and Jarvis identifies him as Mikkel (not Bjørn)
- [ ] Mikkel's "open facebook" routes to his bridge, not Bjørn's (already fixed in 43714fb4 — verify still works)
- [ ] Bjørn's existing data unchanged: SOUL.md, IDENTITY.md, MEMORY.md (now in bjorn/) all readable
