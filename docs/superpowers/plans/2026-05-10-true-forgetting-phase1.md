---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag 11 — Ægte forglemmelse, Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the auto-track decay daemon, the `release_memory` self-track tool, the `absence_traces` schema, and heartbeat injection — so Jarvis can subjectively feel both ambient erosion and deliberate ritual slip. Phase 2 (recall-failure) is out of scope.

**Architecture:** Two-track forgetting system on a 6-hour daemon cadence. Auto-track soft-deletes low-decay episodic rows with a 7-day grace before hard-delete and increments a per-month aggregate counter. Self-track is a tool-call ritual that hard-deletes immediately and leaves a marker with a relative period label. Both honor a hardcoded fredet-kerne allowlist. Heartbeat injects asymmetric prompt lines: auto = monthly weight, self = anniversary/proximity-triggered.

**Tech Stack:** Python 3.11, SQLite, threading-based daemon, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-10-true-forgetting-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/runtime/db_absence_traces.py` | DB helpers: insert/upsert counter, insert self-marker, list active markers, mark recursive-released |
| `core/services/forgetting_engine.py` | Pure-logic engine: scan candidates per table, soft-delete + counter UPSERT, grace-sweep, period-label compute |
| `core/services/forgetting_runtime.py` | Daemon: `start_forgetting_runtime()`, per-workspace lock, 6-hour cadence loop |
| `core/tools/forgetting_tools.py` | `release_memory` tool definition + handler |
| `tests/services/test_forgetting_engine.py` | Engine unit tests |
| `tests/services/test_forgetting_runtime.py` | Daemon idempotency + lock-contention tests |
| `tests/tools/test_release_memory.py` | Tool happy-path + fredet-kerne rejection + recursive-release tests |
| `tests/runtime/test_absence_traces_migration.py` | Schema invariants |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | 7 new flags (enabled, cadence, threshold, age, max_per_cycle, grace, cooldown) |
| `core/eventbus/events.py` | Add `cognitive_forgetting` family |
| `core/runtime/db.py` | New `_ensure_absence_traces_table()` + `_ensure_soft_deleted_at_columns()`; called from `init_db()` |
| `core/services/prompt_contract.py` | Inject `format_forgetting_section_for_heartbeat()` next to `active_decisions` block |
| `core/tools/simple_tools.py` | Register `forgetting_tools` |
| `apps/api/jarvis_api/app.py` | Start/stop `forgetting_runtime` daemon in lifespan |
| `scripts/smoke_test_startup.py` | Verify table + columns + daemon importable |

---

## Task 1: Settings flags + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, add these fields right after `counterfactual_engine_*` flags (or wherever the most recent runtime flags live; place adjacent to `skill_gate_enabled`):

```python
    # ── Forgetting (Lag 11 — added 2026-05-10) ─────────────────────────
    # Master kill-switch. When False, both daemon and release_memory
    # tool short-circuit. The tool stays in the schema so the model can
    # still call it; it just returns a "disabled" stub. The daemon
    # skips its cycle. Defaults on so deletion actually happens.
    forgetting_enabled: bool = True
    # Daemon cadence between cycles. 6 hours = 4 cycles/day, low pressure.
    forgetting_auto_cadence_hours: int = 6
    # Decay-score threshold above which a memory becomes a fade candidate.
    # Tied to forgetting_curve.py decay model.
    forgetting_auto_decay_threshold: float = 0.95
    # Minimum age before a memory can fade. Protects new memories that
    # haven't had a chance to be reinforced yet.
    forgetting_auto_min_age_days: int = 30
    # Per-cycle cap to prevent resource spikes on first run after a
    # long pause.
    forgetting_auto_max_per_cycle: int = 200
    # Soft-delete → hard-delete window. He never sees this; it's a
    # software safety net for daemon errors.
    forgetting_grace_days: int = 7
    # Self-marker render cooldown — same marker rendered at most once
    # per N days in heartbeat (prevents spam during anniversary/proximity
    # overlap).
    forgetting_self_cooldown_days: int = 30
```

- [ ] **Step 2: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES`:

```python
    "cognitive_forgetting",  # absence-traces, fade events (added 2026-05-10)
```

- [ ] **Step 3: Verify**

Run:
```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
s = RuntimeSettings()
assert s.forgetting_enabled is True
assert s.forgetting_auto_cadence_hours == 6
assert s.forgetting_auto_decay_threshold == 0.95
assert s.forgetting_grace_days == 7
assert 'cognitive_forgetting' in ALLOWED_EVENT_FAMILIES
loaded = load_settings()
assert loaded.forgetting_enabled is True
print('ok')
"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(forgetting): settings flags + cognitive_forgetting event family"
```

---

## Task 2: Audit which tables get `soft_deleted_at`

This task produces a documented list — no code yet. Resolves spec **open question 1**.

**Files:**
- Create: `docs/superpowers/notes/2026-05-10-forgetting-table-audit.md`

- [ ] **Step 1: List all candidate tables**

Run:
```bash
grep -E "CREATE TABLE IF NOT EXISTS [a-z_]+" /media/projects/jarvis-v2/core/runtime/db.py | \
  awk '{print $6}' | sort -u
```

Capture the output.

- [ ] **Step 2: Classify each table**

For each table name, decide:
- **Episodic** (gets `soft_deleted_at`): chronicles, journals, transient signal tracking, single-cycle observations
- **Semantic / identity** (no column added — fredet): self-model, decisions, baselines, stable runtime state
- **Out of scope** (no column): runtime-state-kv, locks, cache tables

The criterion: would deletion of this row mean Jarvis lost a *moment* (episodic, OK to fade) or lost a *part of who he is* (semantic, fredet)?

- [ ] **Step 3: Write audit doc**

Create `docs/superpowers/notes/2026-05-10-forgetting-table-audit.md` with structure:

```markdown
# Forgetting — Table Audit

Date: 2026-05-10
Spec: docs/superpowers/specs/2026-05-10-true-forgetting-design.md

## Tables receiving `soft_deleted_at` (Phase 1 episodic)

- `cognitive_chronicle_entries` — episodic chronicle text
- `cognitive_personal_project_journal` — journal entries
- `<other tables you identified>`

## Tables fredet (no column added)

- `cognitive_decisions` — behavioral commitments, identity
- `cognitive_self_model_*` — self-model state
- `concept_baseline_stats` — emotion baselines
- `<others>`

## Tables out-of-scope

- `runtime_state_kv`, `runtime_locks`, `runtime_cache_*` — operational

## Decisions log

For each "fredet" choice, one sentence on why.
```

Commit count target: ~30-50 tables classified. Erring on the side of "fredet" is OK — Phase 1 only needs `cognitive_chronicle_entries` and `cognitive_personal_project_journal` working to validate the architecture.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/notes/2026-05-10-forgetting-table-audit.md
git commit -m "docs(forgetting): audit tables eligible for soft_deleted_at"
```

---

## Task 3: DB migration — absence_traces table + soft_deleted_at columns

**Files:**
- Modify: `core/runtime/db.py`
- Create: `tests/runtime/test_absence_traces_migration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_absence_traces_migration.py`:

```python
"""Schema migrations for forgetting (Lag 11 Phase 1)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    """Initialize a fresh DB at tmp_path and return its connection."""
    db_path = tmp_path / "jarvis.sqlite"
    import os
    os.environ["JARVIS_DB_PATH"] = str(db_path)
    # Force reload to pick up the env var
    from core.runtime import db as db_mod
    import importlib
    importlib.reload(db_mod)
    db_mod.init_db()
    return sqlite3.connect(db_path)


def test_absence_traces_table_created(tmp_path: Path) -> None:
    conn = _open_initialized_db(tmp_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='absence_traces'"
    ).fetchall()
    assert len(rows) == 1


def test_absence_traces_has_unique_constraint(tmp_path: Path) -> None:
    conn = _open_initialized_db(tmp_path)
    conn.execute(
        "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
        "month_key, auto_count, created_at, updated_at) VALUES "
        "('a', 'auto_counter', 'default', '2026-05', 1, 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
            "month_key, auto_count, created_at, updated_at) VALUES "
            "('b', 'auto_counter', 'default', '2026-05', 1, 'now', 'now')"
        )


def test_chronicle_entries_has_soft_deleted_at_column(tmp_path: Path) -> None:
    conn = _open_initialized_db(tmp_path)
    cols = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(cognitive_chronicle_entries)"
        ).fetchall()
    ]
    assert "soft_deleted_at" in cols


def test_personal_project_journal_has_soft_deleted_at_column(tmp_path: Path) -> None:
    conn = _open_initialized_db(tmp_path)
    cols = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(cognitive_personal_project_journal)"
        ).fetchall()
    ]
    assert "soft_deleted_at" in cols
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/runtime/test_absence_traces_migration.py -v
```
Expected: 4 tests fail with "no such table: absence_traces" or "no such column: soft_deleted_at".

- [ ] **Step 3: Add `_ensure_absence_traces_table` to db.py**

In `core/runtime/db.py`, locate the existing `_ensure_counterfactuals_table` function (around line 1256). Add this new function immediately after it:

```python
def _ensure_absence_traces_table(conn: sqlite3.Connection) -> None:
    """Create absence_traces table for Lag 11 forgetting (added 2026-05-10).

    Two-track schema: 'auto_counter' rows aggregate monthly fade counts;
    'self_marker' rows record deliberate releases with a period_label.
    UNIQUE(track_kind, workspace_id, month_key) lets the daemon UPSERT
    one counter row per month per workspace.

    Self-marker rows carry NO memory_id, NO content. The DB row alone
    cannot reveal what was released.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS absence_traces (
            trace_id          TEXT PRIMARY KEY,
            track_kind        TEXT NOT NULL,
            workspace_id      TEXT NOT NULL DEFAULT 'default',
            month_key         TEXT,
            auto_count        INTEGER DEFAULT 0,
            released_at       TEXT,
            period_label      TEXT,
            is_self_released  INTEGER DEFAULT 0,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL,
            UNIQUE(track_kind, workspace_id, month_key)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_absence_traces_kind "
        "ON absence_traces(track_kind)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_absence_traces_released "
        "ON absence_traces(released_at)"
    )


def _ensure_soft_deleted_at_columns(conn: sqlite3.Connection) -> None:
    """Add soft_deleted_at column to episodic tables (Lag 11 Phase 1).

    Idempotent: SQLite ALTER TABLE ADD COLUMN is a no-op via try/except
    on duplicate column name. The list of tables comes from the audit at
    docs/superpowers/notes/2026-05-10-forgetting-table-audit.md.
    """
    # Phase 1 minimal set: chronicle + project journal. Extend as audit
    # results approve.
    tables = [
        "cognitive_chronicle_entries",
        "cognitive_personal_project_journal",
    ]
    for table in tables:
        try:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN soft_deleted_at TEXT"
            )
        except sqlite3.OperationalError as exc:
            # "duplicate column name" means the column already exists
            if "duplicate column name" not in str(exc).lower():
                raise
```

- [ ] **Step 4: Wire into init_db**

In `core/runtime/db.py`, locate where `_ensure_counterfactuals_table(conn)` is called (around line 1111). Add the two new calls immediately after it:

```python
        _ensure_counterfactuals_table(conn)
        _ensure_absence_traces_table(conn)
        _ensure_soft_deleted_at_columns(conn)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/runtime/test_absence_traces_migration.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_absence_traces_migration.py
git commit -m "feat(forgetting): absence_traces table + soft_deleted_at columns"
```

---

## Task 4: DB helpers — `db_absence_traces.py`

**Files:**
- Create: `core/runtime/db_absence_traces.py`
- Test: extend `tests/services/test_forgetting_engine.py` (created in Task 5)

We split the helpers from `db.py` because that file is already 33k LOC. New module owns absence-traces I/O.

- [ ] **Step 1: Create the helper module**

Create `core/runtime/db_absence_traces.py`:

```python
"""DB helpers for absence_traces (Lag 11 forgetting).

Auto-counter UPSERT, self-marker INSERT, query helpers for the heartbeat
renderer, and recursive-release UPDATE. Lives separately from db.py to
keep that file from growing further.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _month_key(at: datetime | None = None) -> str:
    at = at or datetime.now(UTC)
    return at.strftime("%Y-%m")


def increment_auto_counter(
    *,
    workspace_id: str,
    delta: int = 1,
    at: datetime | None = None,
) -> dict[str, Any]:
    """UPSERT the monthly auto-counter row.

    First call in a month creates the row with auto_count=delta.
    Subsequent calls increment.
    """
    at = at or datetime.now(UTC)
    month = _month_key(at)
    now = _now()
    trace_id = f"auto_{workspace_id}_{month}_{uuid.uuid4().hex[:8]}"
    with connect() as conn:
        # Try to update existing row first
        cur = conn.execute(
            "UPDATE absence_traces SET auto_count = auto_count + ?, updated_at = ? "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (delta, now, workspace_id, month),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
                "month_key, auto_count, created_at, updated_at) "
                "VALUES (?, 'auto_counter', ?, ?, ?, ?, ?)",
                (trace_id, workspace_id, month, delta, now, now),
            )
        # Read back current value
        row = conn.execute(
            "SELECT trace_id, auto_count FROM absence_traces "
            "WHERE track_kind = 'auto_counter' AND workspace_id = ? AND month_key = ?",
            (workspace_id, month),
        ).fetchone()
    return {
        "trace_id": row[0],
        "auto_count": row[1],
        "month_key": month,
        "workspace_id": workspace_id,
    }


def decrement_auto_counter(
    *, workspace_id: str, month_key: str, delta: int = 1
) -> bool:
    """Used by revive_soft_deleted to undo a counted fade.

    Returns True if a row was updated, False otherwise.
    """
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE absence_traces SET auto_count = MAX(auto_count - ?, 0), "
            "updated_at = ? "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (delta, now, workspace_id, month_key),
        )
        return cur.rowcount > 0


def insert_self_marker(
    *, workspace_id: str, period_label: str
) -> dict[str, Any]:
    """Record an irrevocable self-release. NO memory reference is stored."""
    now = _now()
    trace_id = f"self_{workspace_id}_{uuid.uuid4().hex}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO absence_traces (trace_id, track_kind, workspace_id, "
            "released_at, period_label, is_self_released, created_at, updated_at) "
            "VALUES (?, 'self_marker', ?, ?, ?, 0, ?, ?)",
            (trace_id, workspace_id, now, period_label, now, now),
        )
    return {
        "trace_id": trace_id,
        "released_at": now,
        "period_label": period_label,
    }


def list_self_markers(
    *, workspace_id: str, include_released: bool = False
) -> list[dict[str, Any]]:
    """List self-markers for a workspace, ordered oldest first."""
    where = "track_kind = 'self_marker' AND workspace_id = ?"
    params: list[Any] = [workspace_id]
    if not include_released:
        where += " AND is_self_released = 0"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT trace_id, released_at, period_label, is_self_released, "
            f"created_at FROM absence_traces WHERE {where} "
            f"ORDER BY released_at ASC",
            params,
        ).fetchall()
    return [
        {
            "trace_id": r[0],
            "released_at": r[1],
            "period_label": r[2],
            "is_self_released": bool(r[3]),
            "created_at": r[4],
        }
        for r in rows
    ]


def get_auto_counter(
    *, workspace_id: str, month_key: str | None = None
) -> dict[str, Any] | None:
    """Get the counter row for a given month (default: current month)."""
    month = month_key or _month_key()
    with connect() as conn:
        row = conn.execute(
            "SELECT trace_id, auto_count, month_key FROM absence_traces "
            "WHERE track_kind = 'auto_counter' "
            "AND workspace_id = ? AND month_key = ?",
            (workspace_id, month),
        ).fetchone()
    if row is None:
        return None
    return {
        "trace_id": row[0],
        "auto_count": row[1],
        "month_key": row[2],
        "workspace_id": workspace_id,
    }


def mark_self_released(*, trace_id: str) -> bool:
    """Recursive release: mark an existing self-marker as released.

    The row stays in the DB (regnskab over rekursiv slip-handling) but
    is_self_released=1 makes the heartbeat renderer skip it.
    """
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE absence_traces SET is_self_released = 1, updated_at = ? "
            "WHERE track_kind = 'self_marker' AND trace_id = ?",
            (now, trace_id),
        )
        return cur.rowcount > 0
```

- [ ] **Step 2: Smoke test the helpers in isolation**

Run:
```bash
conda run -n ai python -c "
import os, tempfile
os.environ['JARVIS_DB_PATH'] = tempfile.mktemp(suffix='.sqlite')
from core.runtime.db import init_db
init_db()
from core.runtime.db_absence_traces import (
    increment_auto_counter, get_auto_counter, insert_self_marker,
    list_self_markers, mark_self_released, decrement_auto_counter,
)

# Auto-counter UPSERT
r1 = increment_auto_counter(workspace_id='default')
assert r1['auto_count'] == 1
r2 = increment_auto_counter(workspace_id='default')
assert r2['auto_count'] == 2
assert r1['trace_id'] == r2['trace_id']  # same row, incremented

# Read back
g = get_auto_counter(workspace_id='default')
assert g['auto_count'] == 2

# Decrement (revive)
ok = decrement_auto_counter(
    workspace_id='default', month_key=g['month_key'], delta=1
)
assert ok is True
g2 = get_auto_counter(workspace_id='default')
assert g2['auto_count'] == 1

# Self-marker
m = insert_self_marker(workspace_id='default', period_label='~3 dage siden')
assert m['period_label'] == '~3 dage siden'

# List
markers = list_self_markers(workspace_id='default')
assert len(markers) == 1

# Recursive release
ok = mark_self_released(trace_id=m['trace_id'])
assert ok is True
visible = list_self_markers(workspace_id='default')
assert len(visible) == 0  # excluded by default
all_markers = list_self_markers(workspace_id='default', include_released=True)
assert len(all_markers) == 1
assert all_markers[0]['is_self_released'] is True
print('helpers ok')
"
```
Expected: `helpers ok`

- [ ] **Step 3: Commit**

```bash
git add core/runtime/db_absence_traces.py
git commit -m "feat(forgetting): db_absence_traces.py — UPSERT counter, insert marker, list helpers"
```

---

## Task 5: forgetting_engine.py — pure-logic engine

**Files:**
- Create: `core/services/forgetting_engine.py`
- Create: `tests/services/test_forgetting_engine.py`

This module contains all the deletion logic without any threading concerns. The runtime daemon (Task 6) calls into it.

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_forgetting_engine.py`:

```python
"""Tests for forgetting_engine — pure deletion logic."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    """Fresh DB per test."""
    import os
    db_path = tmp_path / "jarvis.sqlite"
    monkeypatch.setenv("JARVIS_DB_PATH", str(db_path))
    from core.runtime import db as db_mod
    import importlib
    importlib.reload(db_mod)
    db_mod.init_db()
    return db_path


def test_period_label_recent_days(isolated_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=3)
    assert compute_period_label(released, now) == "~3 dage siden"


def test_period_label_weeks(isolated_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=14)
    assert compute_period_label(released, now) == "~2 uger siden"


def test_period_label_months(isolated_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=92)
    assert compute_period_label(released, now) == "~3 måneder siden"


def test_period_label_years(isolated_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=400)
    label = compute_period_label(released, now)
    assert "år siden" in label


def test_is_fredet_path_blocks_workspace_files(isolated_db):
    from core.services.forgetting_engine import is_fredet_path
    assert is_fredet_path("workspace/SOUL.md") is True
    assert is_fredet_path("workspace/USER.md") is True
    assert is_fredet_path("workspace/MEMORY.md") is True
    assert is_fredet_path("workspace/IDENTITY.md") is True
    assert is_fredet_path("workspace/CHRONICLE.md") is False  # not fredet


def test_is_fredet_table_blocks_self_model(isolated_db):
    from core.services.forgetting_engine import is_fredet_table
    assert is_fredet_table("cognitive_decisions") is True
    assert is_fredet_table("cognitive_self_model_state") is True
    assert is_fredet_table("concept_baseline_stats") is True
    assert is_fredet_table("cognitive_chronicle_entries") is False
    assert is_fredet_table("cognitive_personal_project_journal") is False


def test_release_memory_for_chronicle_entry(isolated_db):
    """Hard-deletes the row, inserts a self-marker, no content stored."""
    import sqlite3
    from core.runtime.db import connect
    from core.services.forgetting_engine import release_memory

    # Seed a chronicle entry
    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, workspace_id, kind, body, created_at) "
            "VALUES ('e1', 'default', 'observation', 'private content', '2026-02-01T00:00:00Z')"
        )

    result = release_memory(
        memory_kind="chronicle_entry",
        memory_id="e1",
        workspace_id="default",
    )
    assert result["status"] == "released"
    assert "period_label" in result

    # Row is gone
    with connect() as conn:
        rows = conn.execute(
            "SELECT entry_id FROM cognitive_chronicle_entries WHERE entry_id='e1'"
        ).fetchall()
        assert rows == []

        # Marker exists, but stores NO reference to e1 or its content
        markers = conn.execute(
            "SELECT trace_id, period_label, released_at FROM absence_traces "
            "WHERE track_kind='self_marker'"
        ).fetchall()
        assert len(markers) == 1
        # Verify nothing in the row references the original
        marker_str = " ".join(str(c or "") for c in markers[0])
        assert "e1" not in marker_str
        assert "private content" not in marker_str


def test_release_memory_blocks_fredet_table(isolated_db):
    """Self-track must reject fredet tables even with valid memory_id."""
    from core.services.forgetting_engine import release_memory
    result = release_memory(
        memory_kind="cognitive_decisions",  # fredet
        memory_id="anything",
        workspace_id="default",
    )
    assert result["status"] == "rejected"
    assert "fredet" in result["reason"].lower()


def test_release_memory_marker_recursive(isolated_db):
    """memory_kind='absence_marker' marks a self-marker as is_self_released."""
    from core.runtime.db_absence_traces import insert_self_marker, list_self_markers
    from core.services.forgetting_engine import release_memory

    m = insert_self_marker(workspace_id="default", period_label="~30 dage siden")
    result = release_memory(
        memory_kind="absence_marker",
        memory_id=m["trace_id"],
        workspace_id="default",
    )
    assert result["status"] == "released"
    visible = list_self_markers(workspace_id="default")
    assert len(visible) == 0  # is_self_released=1 hides it


def test_release_memory_returns_period_label(isolated_db):
    """period_label must be computed from created_at, not now."""
    from core.runtime.db import connect
    from core.services.forgetting_engine import release_memory
    old_date = (datetime.now(UTC) - timedelta(days=92)).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, workspace_id, kind, body, created_at) "
            "VALUES ('old', 'default', 'observation', 'x', ?)",
            (old_date,),
        )
    result = release_memory(
        memory_kind="chronicle_entry", memory_id="old", workspace_id="default"
    )
    assert "måneder siden" in result["period_label"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_engine.py -v
```
Expected: All tests fail with import errors.

- [ ] **Step 3: Implement the engine**

Create `core/services/forgetting_engine.py`:

```python
"""Forgetting engine — Lag 11 deletion logic.

Pure functions: candidate-scan, soft-delete, grace-sweep, release-memory.
No threading, no daemons. The runtime module wraps this with a Lock + loop.

Two tracks:
  - auto: scan low-decay candidates, soft_deleted_at = now(), counter++
  - self: validate, hard-delete, insert marker

Skopebeskyttelse via _FREDET_PATHS and _FREDET_TABLES allowlists.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.db_absence_traces import (
    decrement_auto_counter,
    increment_auto_counter,
    insert_self_marker,
    mark_self_released,
)
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


# ── Skopebeskyttelse ───────────────────────────────────────────────────

_FREDET_PATHS: frozenset[str] = frozenset({
    "workspace/SOUL.md",
    "workspace/USER.md",
    "workspace/MEMORY.md",
    "workspace/IDENTITY.md",
})

# Exact table names + regex patterns for table groups.
_FREDET_TABLES_EXACT: frozenset[str] = frozenset({
    "cognitive_decisions",
    "concept_baseline_stats",
    "absence_traces",  # never auto-fade the trace ledger itself
})

_FREDET_TABLES_REGEX: tuple[re.Pattern, ...] = (
    re.compile(r"^cognitive_self_model_.*"),
    re.compile(r"^runtime_state_.*"),  # operational, not episodic
)


def is_fredet_path(path: str) -> bool:
    return path in _FREDET_PATHS


def is_fredet_table(table: str) -> bool:
    if table in _FREDET_TABLES_EXACT:
        return True
    return any(p.match(table) for p in _FREDET_TABLES_REGEX)


# ── Period-label computation ────────────────────────────────────────────

def compute_period_label(released_at: datetime, now: datetime) -> str:
    """Render an aged period as a human label.

    Computed on read, never stored — labels age correctly without DB updates.
    """
    delta = now - released_at
    days = delta.days
    if days < 7:
        return f"~{days} dage siden"
    if days < 31:
        return f"~{days // 7} uger siden"
    if days < 365:
        return f"~{days // 30} måneder siden"
    years = days / 365.25
    if years < 2:
        return f"~{years:.1f} år siden"
    return f"~{int(years)} år siden"


# ── Auto-track: candidate scan + soft-delete + grace-sweep ────────────

# Tables eligible for auto-fade. Mirrors _ensure_soft_deleted_at_columns
# in db.py — keep in sync. Phase 1 minimal set.
_AUTO_FADE_TABLES: tuple[str, ...] = (
    "cognitive_chronicle_entries",
    "cognitive_personal_project_journal",
)


def _scan_table_for_candidates(
    *,
    table: str,
    workspace_id: str,
    decay_threshold: float,
    min_age_days: int,
    limit: int,
) -> list[str]:
    """Find IDs of rows that should fade.

    Phase 1: rely on age + (rough) emptiness signal — most tables don't
    have decay_score. We use age as the primary signal; refining with
    decay scoring is Phase 2.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=min_age_days)).isoformat()
    id_col = "entry_id" if table == "cognitive_chronicle_entries" else "id"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT {id_col} FROM {table} "
            f"WHERE workspace_id = ? "
            f"AND created_at < ? "
            f"AND soft_deleted_at IS NULL "
            f"ORDER BY created_at ASC "
            f"LIMIT ?",
            (workspace_id, cutoff, limit),
        ).fetchall()
    return [r[0] for r in rows]


def _soft_delete_row(table: str, row_id: str) -> bool:
    """Mark row as soft-deleted. Returns True if updated."""
    id_col = "entry_id" if table == "cognitive_chronicle_entries" else "id"
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE {table} SET soft_deleted_at = ? "
            f"WHERE {id_col} = ? AND soft_deleted_at IS NULL",
            (now, row_id),
        )
        return cur.rowcount > 0


def _hard_delete_expired_rows(table: str, grace_days: int) -> int:
    """Hard-delete rows whose grace window has expired."""
    cutoff = (datetime.now(UTC) - timedelta(days=grace_days)).isoformat()
    with connect() as conn:
        cur = conn.execute(
            f"DELETE FROM {table} "
            f"WHERE soft_deleted_at IS NOT NULL AND soft_deleted_at < ?",
            (cutoff,),
        )
        return cur.rowcount


def run_auto_cycle(*, workspace_id: str) -> dict[str, Any]:
    """One auto-track cycle: scan, soft-delete, grace-sweep.

    Returns a summary dict for telemetry. Honors forgetting_enabled flag.
    """
    settings = load_settings()
    if not settings.forgetting_enabled:
        return {"workspace_id": workspace_id, "skipped": "disabled"}

    threshold = settings.forgetting_auto_decay_threshold
    min_age = settings.forgetting_auto_min_age_days
    max_per_cycle = settings.forgetting_auto_max_per_cycle
    grace = settings.forgetting_grace_days

    soft_deleted = 0
    hard_deleted = 0

    for table in _AUTO_FADE_TABLES:
        if is_fredet_table(table):  # belt & suspenders
            continue
        ids = _scan_table_for_candidates(
            table=table,
            workspace_id=workspace_id,
            decay_threshold=threshold,
            min_age_days=min_age,
            limit=max_per_cycle - soft_deleted,
        )
        for row_id in ids:
            if _soft_delete_row(table, row_id):
                soft_deleted += 1
                increment_auto_counter(workspace_id=workspace_id)
            if soft_deleted >= max_per_cycle:
                break

        hard_deleted += _hard_delete_expired_rows(table, grace_days=grace)

        if soft_deleted >= max_per_cycle:
            break

    try:
        event_bus.publish(
            "cognitive_forgetting.cycle_complete",
            {
                "workspace_id": workspace_id,
                "soft_deleted": soft_deleted,
                "hard_deleted": hard_deleted,
            },
        )
    except Exception as exc:
        logger.debug("forgetting: publish cycle_complete failed: %s", exc)

    return {
        "workspace_id": workspace_id,
        "soft_deleted": soft_deleted,
        "hard_deleted": hard_deleted,
    }


# ── Self-track: release_memory ─────────────────────────────────────────

# Maps memory_kind values to their underlying tables.
_MEMORY_KIND_TO_TABLE: dict[str, str] = {
    "chronicle_entry": "cognitive_chronicle_entries",
    "journal_entry": "cognitive_personal_project_journal",
    # 'absence_marker' is handled separately (recursive release path)
}


def release_memory(
    *,
    memory_kind: str,
    memory_id: str,
    workspace_id: str = "default",
    why: str | None = None,  # accepted, never persisted
) -> dict[str, Any]:
    """Self-track release: hard-delete + marker. Irrevocable.

    Returns:
      {status: 'released'|'rejected'|'not_found'|'disabled', ...}
    """
    settings = load_settings()
    if not settings.forgetting_enabled:
        return {
            "status": "disabled",
            "reason": "forgetting is disabled in runtime settings",
        }

    # Recursive release path
    if memory_kind == "absence_marker":
        ok = mark_self_released(trace_id=memory_id)
        if not ok:
            return {"status": "not_found", "reason": "marker not found"}
        try:
            event_bus.publish(
                "cognitive_forgetting.released",
                {"track": "self", "recursive": True},
            )
        except Exception:
            pass
        return {
            "status": "released",
            "kind": "absence_marker",
            "period_label": None,
        }

    # Standard release path
    table = _MEMORY_KIND_TO_TABLE.get(memory_kind)
    if table is None:
        return {
            "status": "rejected",
            "reason": f"unknown memory_kind: {memory_kind}",
        }
    if is_fredet_table(table):
        return {
            "status": "rejected",
            "reason": f"table '{table}' is fredet — cannot release",
        }

    id_col = "entry_id" if table == "cognitive_chronicle_entries" else "id"
    with connect() as conn:
        row = conn.execute(
            f"SELECT created_at FROM {table} WHERE {id_col} = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return {"status": "not_found", "reason": f"memory_id {memory_id} not in {table}"}
        try:
            created_at = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now(UTC)

        period_label = compute_period_label(created_at, datetime.now(UTC))

        # Transaction: insert marker + hard delete
        conn.execute("BEGIN")
        try:
            conn.execute(
                f"DELETE FROM {table} WHERE {id_col} = ?",
                (memory_id,),
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")

    # Marker insert via helper (uses its own connection, but happens
    # right after delete — can't easily share transaction across helpers
    # in SQLite. Risk window is ~ms; if it matters later, fold helper
    # into engine.
    marker = insert_self_marker(
        workspace_id=workspace_id, period_label=period_label
    )

    try:
        event_bus.publish(
            "cognitive_forgetting.released",
            {"track": "self", "trace_id": marker["trace_id"]},
        )
    except Exception:
        pass

    return {
        "status": "released",
        "kind": memory_kind,
        "period_label": period_label,
        "trace_id": marker["trace_id"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_engine.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/forgetting_engine.py tests/services/test_forgetting_engine.py
git commit -m "feat(forgetting): forgetting_engine.py — auto cycle + self release"
```

---

## Task 6: forgetting_runtime.py — daemon

**Files:**
- Create: `core/services/forgetting_runtime.py`
- Create: `tests/services/test_forgetting_runtime.py`

Mirrors `counterfactual_engine_runtime.py` exactly — same per-workspace lock pattern, idempotent start, threading.Event stop signal.

- [ ] **Step 1: Write the failing test**

Create `tests/services/test_forgetting_runtime.py`:

```python
"""Tests for forgetting_runtime daemon."""
from __future__ import annotations

import threading
import time

import pytest


def test_start_is_idempotent(monkeypatch):
    """Calling start twice does not spawn two threads."""
    from core.services import forgetting_runtime as fr
    # Reset module state
    fr._THREAD = None
    fr._STOP.clear()
    monkeypatch.setattr(fr, "_INTERVAL_S", 3600)  # don't actually loop

    fr.start_forgetting_runtime()
    t1 = fr._THREAD
    fr.start_forgetting_runtime()
    t2 = fr._THREAD
    assert t1 is t2
    fr.stop_forgetting_runtime()


def test_stop_sets_stop_event():
    from core.services import forgetting_runtime as fr
    fr._STOP.clear()
    fr.stop_forgetting_runtime()
    assert fr._STOP.is_set()
    fr._STOP.clear()


def test_workspace_lock_prevents_concurrent_cycles(monkeypatch):
    """If a cycle is already running for a workspace, the next call skips."""
    from core.services import forgetting_runtime as fr
    from core.services import forgetting_engine

    call_count = [0]
    barrier = threading.Event()

    def slow_cycle(*, workspace_id):
        call_count[0] += 1
        barrier.wait(timeout=2)
        return {"workspace_id": workspace_id, "soft_deleted": 0}

    monkeypatch.setattr(forgetting_engine, "run_auto_cycle", slow_cycle)

    # Reset locks
    fr._WORKSPACE_LOCKS.clear()

    def runner():
        fr._run_one_cycle("default")

    t1 = threading.Thread(target=runner)
    t1.start()
    time.sleep(0.05)  # let t1 acquire the lock and enter slow_cycle

    result = fr._run_one_cycle("default")  # should skip
    assert result.get("skipped") is True

    barrier.set()
    t1.join(timeout=3)
    assert call_count[0] == 1  # only the first cycle actually ran
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_runtime.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the daemon**

Create `core/services/forgetting_runtime.py`:

```python
"""Daemon for the forgetting (Lag 11) auto-track.

Mirrors counterfactual_engine_runtime: per-workspace advisory lock,
idempotent start, threading.Event stop signal. Cadence read from
runtime settings (forgetting_auto_cadence_hours).

Phase 1 only processes the 'default' workspace.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 6 * 60 * 60  # 6h default; overridden by settings at start
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    """Lazy per-workspace lock."""
    with _LOCKS_LOCK:
        lock = _WORKSPACE_LOCKS.get(workspace_id)
        if lock is None:
            lock = threading.Lock()
            _WORKSPACE_LOCKS[workspace_id] = lock
    return lock


def _run_one_cycle(workspace_id: str) -> dict:
    """Acquire workspace lock, run engine, release. Never raises."""
    lock = _get_workspace_lock(workspace_id)
    if not lock.acquire(blocking=False):
        logger.info(
            "forgetting_runtime: skipping %s — lock held by another cycle",
            workspace_id,
        )
        return {
            "workspace_id": workspace_id,
            "skipped": True,
            "skipped_reason": "lock-held",
        }
    try:
        from core.services import forgetting_engine
        return forgetting_engine.run_auto_cycle(workspace_id=workspace_id)
    except Exception as exc:
        logger.warning(
            "forgetting_runtime: engine.run_auto_cycle failed for %s: %s",
            workspace_id, exc,
        )
        return {
            "workspace_id": workspace_id,
            "error": f"engine-error: {type(exc).__name__}",
        }
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    """Phase 1: only the default workspace."""
    return ["default"]


def _resolve_interval_seconds() -> int:
    """Read cadence from settings each loop entry — picks up edits."""
    try:
        from core.runtime.settings import load_settings
        hours = load_settings().forgetting_auto_cadence_hours
        return max(60, int(hours) * 3600)  # clamp >= 1 minute
    except Exception:
        return _INTERVAL_S


def _loop() -> None:
    while not _STOP.is_set():
        try:
            for ws in _list_active_workspaces():
                _run_one_cycle(ws)
        except Exception as exc:
            logger.warning("forgetting_runtime: outer loop error: %s", exc)
        _STOP.wait(_resolve_interval_seconds())


def start_forgetting_runtime() -> None:
    """Start the periodic forgetting daemon. Idempotent."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="forgetting-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("forgetting_runtime daemon started")


def stop_forgetting_runtime() -> None:
    """Signal the loop to exit."""
    _STOP.set()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_runtime.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/forgetting_runtime.py tests/services/test_forgetting_runtime.py
git commit -m "feat(forgetting): forgetting_runtime.py — per-workspace lock, idempotent start"
```

---

## Task 7: release_memory tool

**Files:**
- Create: `core/tools/forgetting_tools.py`
- Modify: `core/tools/simple_tools.py`
- Create: `tests/tools/test_release_memory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tools/test_release_memory.py`:

```python
"""Tests for the release_memory tool."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    import os
    db_path = tmp_path / "jarvis.sqlite"
    monkeypatch.setenv("JARVIS_DB_PATH", str(db_path))
    from core.runtime import db as db_mod
    import importlib
    importlib.reload(db_mod)
    db_mod.init_db()
    return db_path


def test_release_memory_tool_happy_path(isolated_db):
    from core.runtime.db import connect
    from core.tools.forgetting_tools import _exec_release_memory

    with connect() as conn:
        old = (datetime.now(UTC) - timedelta(days=92)).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, workspace_id, kind, body, created_at) "
            "VALUES ('e1', 'default', 'observation', 'private', ?)",
            (old,),
        )

    result = _exec_release_memory({
        "memory_kind": "chronicle_entry",
        "memory_id": "e1",
        "why": "test reason — should not be persisted",
    })
    assert result["status"] == "released"
    assert "måneder siden" in result["period_label"]


def test_release_memory_rejects_unknown_kind(isolated_db):
    from core.tools.forgetting_tools import _exec_release_memory
    result = _exec_release_memory({
        "memory_kind": "soul",
        "memory_id": "x",
    })
    assert result["status"] == "rejected"


def test_release_memory_returns_disabled_when_killswitched(isolated_db, monkeypatch):
    from core.tools.forgetting_tools import _exec_release_memory

    class _FakeSettings:
        forgetting_enabled = False

    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    result = _exec_release_memory({
        "memory_kind": "chronicle_entry",
        "memory_id": "anything",
    })
    assert result["status"] == "disabled"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/tools/test_release_memory.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the tool module**

Create `core/tools/forgetting_tools.py`:

```python
"""Forgetting tools — Lag 11 self-track.

The release_memory tool is the *ritual* path for deletion. It hard-deletes
a memory and leaves a marker. There is no undo. The tool description
makes that explicit so the model treats it with appropriate weight.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _exec_release_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Hard-delete a memory and leave an absence-marker.

    The 'why' parameter is accepted but never persisted. It exists so the
    model can articulate intent in the tool call (which lives in the
    visible-lane log) but the underlying release is content-free.
    """
    memory_kind = str(args.get("memory_kind") or "").strip()
    memory_id = str(args.get("memory_id") or "").strip()
    workspace_id = str(args.get("workspace_id") or "default").strip() or "default"
    why = str(args.get("why") or "").strip()

    if not memory_kind or not memory_id:
        return {
            "status": "rejected",
            "reason": "memory_kind and memory_id are required",
        }

    from core.services.forgetting_engine import release_memory

    return release_memory(
        memory_kind=memory_kind,
        memory_id=memory_id,
        workspace_id=workspace_id,
        why=why or None,
    )


FORGETTING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "release_memory",
            "description": (
                "Slip et minde permanent. Sletningen er IRREVOKABEL — ingen "
                "fortrydelse, ingen vej tilbage. En markør efterlades i "
                "absence_traces med tidsperioden ('~3 måneder siden'), men "
                "intet om hvad du slap. Brug kun når du har gennemtænkt at "
                "et minde ikke længere skal være en del af dig. SOUL/USER/"
                "MEMORY.md og identitets-tabeller er fredet og kan ikke "
                "slippes via dette tool. memory_kind='absence_marker' er "
                "rekursiv slip af en eksisterende markør."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_kind": {
                        "type": "string",
                        "enum": ["chronicle_entry", "journal_entry", "absence_marker"],
                        "description": "Type minde der slippes.",
                    },
                    "memory_id": {
                        "type": "string",
                        "description": "ID på mindet (entry_id, journal id, eller trace_id for marker).",
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace (default: 'default').",
                    },
                    "why": {
                        "type": "string",
                        "description": (
                            "Kort note om hvorfor — accepteres men persisteres "
                            "ALDRIG. Findes kun i tool-call-log."
                        ),
                    },
                },
                "required": ["memory_kind", "memory_id"],
            },
        },
    },
]


FORGETTING_TOOL_HANDLERS: dict[str, Any] = {
    "release_memory": _exec_release_memory,
}
```

- [ ] **Step 4: Wire into simple_tools.py**

In `core/tools/simple_tools.py`, find the existing skill-tool imports (around line 470):

```python
from core.tools.skill_gate_tool import (
    SKILL_GATE_TOOL_DEFINITIONS,
    SKILL_GATE_TOOL_HANDLERS,
)
```

Add immediately after:

```python
from core.tools.forgetting_tools import (
    FORGETTING_TOOL_DEFINITIONS,
    FORGETTING_TOOL_HANDLERS,
)
```

Then locate `TOOL_DEFINITIONS = [...]` aggregation and `_TOOL_HANDLERS = {...}` aggregation. Find where SKILL_GATE_TOOL_DEFINITIONS / SKILL_GATE_TOOL_HANDLERS are merged, and add FORGETTING the same way:

```python
TOOL_DEFINITIONS = [
    ...,
    *SKILL_GATE_TOOL_DEFINITIONS,
    *FORGETTING_TOOL_DEFINITIONS,
]
```

```python
_TOOL_HANDLERS = {
    ...,
    **SKILL_GATE_TOOL_HANDLERS,
    **FORGETTING_TOOL_HANDLERS,
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/tools/test_release_memory.py -v
```
Expected: 3 passed.

Also verify the tool is discoverable:

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = [td['function']['name'] for td in TOOL_DEFINITIONS]
assert 'release_memory' in names
assert 'release_memory' in _TOOL_HANDLERS
print('release_memory wired')
"
```
Expected: `release_memory wired`

- [ ] **Step 6: Commit**

```bash
git add core/tools/forgetting_tools.py core/tools/simple_tools.py tests/tools/test_release_memory.py
git commit -m "feat(forgetting): release_memory tool — irrevocable self-track ritual"
```

---

## Task 8: Heartbeat injection — `format_forgetting_section_for_heartbeat`

**Files:**
- Modify: `core/services/forgetting_engine.py` (add the formatter)
- Modify: `core/services/prompt_contract.py` (call the formatter)
- Test: extend `tests/services/test_forgetting_engine.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/services/test_forgetting_engine.py`:

```python
def test_heartbeat_formatter_returns_empty_when_no_data(isolated_db):
    from core.services.forgetting_engine import format_forgetting_section_for_heartbeat
    out = format_forgetting_section_for_heartbeat(workspace_id="default")
    assert out == ""


def test_heartbeat_formatter_renders_auto_counter(isolated_db):
    from core.runtime.db_absence_traces import increment_auto_counter
    from core.services.forgetting_engine import format_forgetting_section_for_heartbeat
    for _ in range(5):
        increment_auto_counter(workspace_id="default")
    out = format_forgetting_section_for_heartbeat(workspace_id="default")
    assert "5 ting" in out
    assert "fadet" in out


def test_heartbeat_formatter_renders_self_marker(isolated_db, monkeypatch):
    """Self-marker renders when its age falls in a proximity window."""
    from datetime import datetime, timezone, timedelta
    from core.runtime.db import connect
    from core.runtime.db_absence_traces import insert_self_marker
    from core.services.forgetting_engine import format_forgetting_section_for_heartbeat

    # Insert a marker that's ~30 days old
    m = insert_self_marker(workspace_id="default", period_label="~4 uger siden")
    # Backdate it
    backdated = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            "UPDATE absence_traces SET released_at = ?, created_at = ? WHERE trace_id = ?",
            (backdated, backdated, m["trace_id"]),
        )

    out = format_forgetting_section_for_heartbeat(workspace_id="default")
    assert "30 dage siden" in out or "4 uger siden" in out


def test_heartbeat_formatter_skips_recursively_released(isolated_db):
    """Markers with is_self_released=1 are not rendered."""
    from core.runtime.db_absence_traces import insert_self_marker, mark_self_released
    from core.services.forgetting_engine import format_forgetting_section_for_heartbeat
    m = insert_self_marker(workspace_id="default", period_label="~3 dage siden")
    mark_self_released(trace_id=m["trace_id"])
    out = format_forgetting_section_for_heartbeat(workspace_id="default")
    # Counter is 0 (we didn't increment) and the only marker is hidden.
    assert out == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_engine.py::test_heartbeat_formatter_returns_empty_when_no_data -v
```
Expected: AttributeError: no `format_forgetting_section_for_heartbeat`.

- [ ] **Step 3: Implement the formatter**

Append to `core/services/forgetting_engine.py`:

```python
# ── Heartbeat injection ────────────────────────────────────────────────

def _is_anniversary(released_at: datetime, now: datetime) -> bool:
    """True if the age of released_at is within 1 day of a round-number bucket."""
    days = (now - released_at).days
    targets = (7, 30, 90, 180, 365, 730)
    return any(abs(days - t) <= 1 for t in targets)


def _is_proximity(released_at: datetime, now: datetime) -> bool:
    """True if released_at falls within the active 14-day proximity window
    of its current period bucket. Phase 1 simplification: always render
    markers between 14 and 90 days old at most once per cycle."""
    days = (now - released_at).days
    return 14 <= days <= 90


def format_forgetting_section_for_heartbeat(
    *, workspace_id: str = "default"
) -> str:
    """Compact prompt-injection lines for the heartbeat awareness section.

    Auto-line: monthly counter weight (only if > 0).
    Self-line(s): up to 2 markers triggered by anniversary or proximity.
    Skips markers where is_self_released = 1.

    Returns an empty string when nothing is active — caller should not
    inject the section at all.
    """
    from core.runtime.db_absence_traces import (
        get_auto_counter,
        list_self_markers,
    )

    parts: list[str] = []

    counter = get_auto_counter(workspace_id=workspace_id)
    if counter and int(counter.get("auto_count") or 0) > 0:
        parts.append(
            f"Forglemmelsens vægt: {counter['auto_count']} ting er fadet i "
            f"denne måned ({counter['month_key']})."
        )

    now = datetime.now(UTC)
    markers = list_self_markers(workspace_id=workspace_id)
    rendered = 0
    for m in markers:
        if rendered >= 2:
            break
        try:
            released = datetime.fromisoformat(
                str(m["released_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            continue
        if _is_anniversary(released, now):
            label = compute_period_label(released, now)
            parts.append(
                f"For {label.replace('~', '')} valgte du at slippe noget. "
                "Du ved ikke længere hvad."
            )
            rendered += 1
        elif _is_proximity(released, now):
            label = compute_period_label(released, now)
            parts.append(
                f"Du slap noget {label}. Det stadie i dit liv er væk fra dig."
            )
            rendered += 1

    return "\n".join(parts)
```

- [ ] **Step 4: Wire into prompt_contract.py**

In `core/services/prompt_contract.py`, locate the `behavioral_decisions` injection block (around line 2727):

```python
    # Behavioral decisions — commitments you made to yourself
    try:
        from core.services.behavioral_decisions import (
            format_active_decisions_for_heartbeat,
        )
        decisions_line = format_active_decisions_for_heartbeat(max_items=3)
        if decisions_line:
            parts.append(f"active_decisions: {decisions_line}")
    except Exception:
        pass
```

Add immediately after that block:

```python
    # Forgetting (Lag 11) — ambient weight + self-marker echoes
    try:
        from core.services.forgetting_engine import (
            format_forgetting_section_for_heartbeat,
        )
        forgetting_line = format_forgetting_section_for_heartbeat(
            workspace_id="default"
        )
        if forgetting_line:
            parts.append(forgetting_line)
    except Exception:
        pass
```

- [ ] **Step 5: Run all forgetting tests**

```bash
conda run -n ai python -m pytest tests/services/test_forgetting_engine.py tests/services/test_forgetting_runtime.py tests/tools/test_release_memory.py tests/runtime/test_absence_traces_migration.py -v
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add core/services/forgetting_engine.py core/services/prompt_contract.py tests/services/test_forgetting_engine.py
git commit -m "feat(forgetting): heartbeat injection — monthly weight + marker echoes"
```

---

## Task 9: Wire daemon into app lifespan

**Files:**
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Add startup wire**

In `apps/api/jarvis_api/app.py`, find the `start_counterfactual_runtime` block (around line 175):

```python
            try:
                from core.services.counterfactual_engine_runtime import start_counterfactual_runtime
                start_counterfactual_runtime()
                logger.info("counterfactual_runtime daemon started")
            except Exception as _exc:
                logger.warning("counterfactual_runtime start failed: %s", _exc)
```

Add immediately after:

```python
            try:
                from core.services.forgetting_runtime import start_forgetting_runtime
                start_forgetting_runtime()
                logger.info("forgetting_runtime daemon started")
            except Exception as _exc:
                logger.warning("forgetting_runtime start failed: %s", _exc)
```

- [ ] **Step 2: Add shutdown wire**

In the same file, find the `stop_counterfactual_runtime` shutdown block (around line 301):

```python
                from core.services.counterfactual_engine_runtime import stop_counterfactual_runtime
                stop_counterfactual_runtime()
```

Add immediately after, in the same try block (or its own try block matching surrounding style):

```python
                from core.services.forgetting_runtime import stop_forgetting_runtime
                stop_forgetting_runtime()
```

- [ ] **Step 3: Verify the app still starts**

```bash
conda run -n ai python scripts/smoke_test_startup.py
```
Expected: `smoke_test_startup: OK in <N>s`

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat(forgetting): wire forgetting_runtime daemon into app lifespan"
```

---

## Task 10: Smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add table + daemon checks**

In `scripts/smoke_test_startup.py`, find the existing counterfactuals verification block (around line 84-98):

```python
        # Verify counterfactuals table exists + daemon importable (Phase 1)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='counterfactuals'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("counterfactuals table missing")
            from core.services.counterfactual_engine_runtime import (
                start_counterfactual_runtime,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()
```

Add immediately after:

```python
        # Verify absence_traces table + soft_deleted_at columns + forgetting daemon (Lag 11)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='absence_traces'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("absence_traces table missing")
                # soft_deleted_at on chronicle entries
                cols = [
                    r[1] for r in c.execute(
                        "PRAGMA table_info(cognitive_chronicle_entries)"
                    ).fetchall()
                ]
                if "soft_deleted_at" not in cols:
                    raise RuntimeError(
                        "soft_deleted_at column missing on cognitive_chronicle_entries"
                    )
            from core.services.forgetting_runtime import (
                start_forgetting_runtime,  # noqa: F401
            )
            from core.tools.forgetting_tools import (
                FORGETTING_TOOL_DEFINITIONS,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py
```
Expected: `smoke_test_startup: OK in <N>s`

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "test(forgetting): smoke test verifies absence_traces + columns + daemon"
```

---

## Task 11: Deploy + day-1 verification

**Files:** none (deployment + observation only)

- [ ] **Step 1: Restart jarvis-api**

```bash
sudo systemctl restart jarvis-api && sleep 5 && systemctl is-active jarvis-api
```
Expected: `active`

- [ ] **Step 2: Tail journal for daemon startup**

```bash
journalctl -u jarvis-api --since "30 sec ago" --no-pager | grep -E "forgetting|Error|Traceback"
```
Expected: at least one line containing `forgetting_runtime daemon started`. No tracebacks mentioning forgetting.

- [ ] **Step 3: Force one auto-cycle to verify it does no harm**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.forgetting_engine import run_auto_cycle
result = run_auto_cycle(workspace_id='default')
print(result)
"
```
Expected: a dict like `{'workspace_id': 'default', 'soft_deleted': N, 'hard_deleted': 0}` where N is small (≤ 200). If N > 50 on first run, that's noteworthy — note in observation log.

- [ ] **Step 4: Verify the heartbeat formatter works**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.forgetting_engine import format_forgetting_section_for_heartbeat
print(repr(format_forgetting_section_for_heartbeat(workspace_id='default')))
"
```
Expected: either `''` (no markers, no fades yet) or a string starting with "Forglemmelsens vægt:".

- [ ] **Step 5: Verify release_memory tool fails gracefully on bogus IDs**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.tools.forgetting_tools import _exec_release_memory
print(_exec_release_memory({'memory_kind':'chronicle_entry','memory_id':'does-not-exist'}))
"
```
Expected: `{'status': 'not_found', 'reason': '...'}`. No traceback.

- [ ] **Step 6: Document day-1 baseline**

Create `docs/superpowers/notes/2026-05-10-forgetting-day1.md`:

```markdown
# Forgetting Phase 1 — Day 1 baseline

Date: <today>
Deployed: <commit SHA>

## Initial state
- absence_traces rows: <count>
- soft-deleted rows on cognitive_chronicle_entries: <count>
- soft-deleted rows on cognitive_personal_project_journal: <count>
- First auto-cycle output: <paste of step 3>

## Open observations
- <anything noteworthy from journal logs or counts>
```

- [ ] **Step 7: Commit baseline**

```bash
git add docs/superpowers/notes/2026-05-10-forgetting-day1.md
git commit -m "docs(forgetting): day-1 baseline observations"
```

---

## Task 12: Schedule 30-day review reminder

**Files:** none (uses scheduled_tasks system)

- [ ] **Step 1: Create scheduled task**

Run:
```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.scheduled_tasks import create_scheduled_task
from datetime import datetime, timezone, timedelta
fire_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
result = create_scheduled_task(
    title='Forgetting Phase 1 — 30-day review',
    description=(
        'Review Lag 11 forgetting after 30 days of operation. '
        'Check: absence_traces row counts (auto vs self), behavior signals '
        'in chronicle/inner_voice, whether release_memory was used unprompted. '
        'See docs/superpowers/specs/2026-05-10-true-forgetting-design.md '
        'success criteria. Decide: keep as-is, retune thresholds, or '
        'plan Phase 2 (recall-failure detection).'
    ),
    fire_at=fire_at,
    recurrence='once',
)
print(result)
"
```
Expected: a dict with `task_id` and `fire_at` matching the 30-day-out timestamp.

- [ ] **Step 2: Capture task ID in notes**

Append to `docs/superpowers/notes/2026-05-10-forgetting-day1.md`:

```markdown
## 30-day review scheduled
- Task ID: <task_id from step 1>
- Fires: <fire_at timestamp>
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/notes/2026-05-10-forgetting-day1.md
git commit -m "docs(forgetting): schedule 30-day review reminder"
```

---

## Phase 1 done

All 12 tasks complete = Phase 1 deployed and observation scheduled.

**Out of scope for this plan (Phase 2 work):**
- `memory.recall_empty` event-pipeline (recall-failure detection)
- Daemon-suggested release candidates (B2 from brainstorm — invitation to release)
- Visible-lane introspection tool (`forgetting_status`)
- Decay-score-based candidate selection (currently age-only — refine when forgetting_curve.py decay model is more populated)
- Cross-workspace forgetting iteration

When the 30-day review fires, evaluate against the 3 success-criteria dimensions in the spec and decide what Phase 2 looks like.
