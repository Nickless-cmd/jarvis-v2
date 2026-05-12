# Lag 2 — Dream Bias Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a structured bias-distillation pipeline alongside the existing dream-residue text pipeline, producing attention/threshold biases that modulate Jarvis' next waking cycle through 5 specific code-level plug-in sites plus heartbeat prompt-injection.

**Architecture:** Reuses the existing `dream_distillation_daemon` trigger (visible-idle ≥ 30 min). Adds a parallel bias-pipeline that pulls events from 6 regret-heavy sources, calls a quality-lane LLM for strict JSON output, validates against a locked vocabulary (5 attention + 4 threshold keys), and UPSERTs into a single-row-per-workspace `dream_bias_active` table. Bias accumulates with cap ±1.0 per key, expires after 8h TTL (reset on each accumulation), respects a master kill-switch, and plugs into 5 specific consumer sites.

**Tech Stack:** Python 3.11, SQLite, threading-based daemon (existing), eventbus.

**Spec:** `docs/superpowers/specs/2026-05-10-dream-bias-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/dream_bias_engine.py` | Distillation orchestrator, validate, accumulate, heartbeat formatter, public read API |
| `core/runtime/db_dream_bias.py` | DB helpers: UPSERT bias row, get raw active bias (bypasses kill-switch), delete expired |
| `tests/services/test_dream_bias_engine.py` | Engine + validation + heartbeat formatter tests |
| `tests/runtime/test_dream_bias_migration.py` | Schema invariants |
| `tests/runtime/test_db_dream_bias.py` | DB helper tests |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | 7 new flags (enabled + 6 operational) |
| `core/eventbus/events.py` | Add `cognitive_dream_bias` family |
| `core/runtime/db.py` | New `_ensure_dream_bias_active_table()` called from `init_db()` |
| `core/services/dream_distillation_daemon.py` | Add bias-distillation call alongside residue pipeline |
| `core/services/prompt_contract.py` | Inject `format_dream_bias_for_heartbeat()` after forgetting_section |
| `core/services/open_loop_signal_tracking.py` | Modulate `limit` passed to listing using `unfinished_business` bias |
| `core/services/self_review_outcome_tracking.py` | Modulate `limit` using `regret_threads` bias |
| `core/services/visible_runs.py` | Modulate `_MAX_EMPTY_TEXT_ROUNDS` using `loop_persistence` bias |
| `core/services/self_critique_runtime.py` | Modulate `_SELF_CRITIQUE_INTERVAL_DAYS` using `self_critique_volume` bias |
| `scripts/smoke_test_startup.py` | Verify table + module importable |

---

## Spec deltas confirmed during planning

Five open questions in the spec resolved:

1. **`daemon_llm_call` JSON-output mode** — does NOT support strict JSON natively. Returns stripped text. Engine must `json.loads()` the response with try/except + fallback. Use `quality_daemon_llm_call` (deepseek-v4-flash inner_enrichment lane) since dream-bias is identity-relevant — same cost, better quality.

2. **Source SQL queries** — 4 of 6 sources are eventbus events queryable via the `events` table, mirrored from `counterfactual_triggers.fetch_recent_triggers`:
   - `self_review_outcome.created` ✓
   - `conflict.detected` ✓
   - `decision_revoked` ✓
   - `behavioral_decision_review.broken` ✓
   - The remaining 2: `rupture.*` events (events table, kind LIKE 'rupture.%') and counterfactual triggers (already covered by 4 above).

3. **Bias-section render scope** — Phase 1 inject only via `prompt_contract.py` heartbeat awareness section. Visible-lane prompt-contract path (`_build_visible_prompt`) does NOT consume it. Confirmed by reading prompt_contract.py.

4. **`open_loop_signal_tracking` listing** — `_build_runtime_open_loop_signal_surface_uncached(limit=N)` is the entry point. **No per-signal `priority` field exists.** Modulation strategy adjusted: bias modulates the `limit` parameter (more biased = surface more rows). Same applies to `self_review_outcome_tracking.build_runtime_self_review_outcome_surface(limit=N)`.

5. **`self_critique_runtime` cadence** — `_SELF_CRITIQUE_INTERVAL_DAYS = 30` constant at module scope. Wrap with a resolver function that reads bias on every check. Effective cadence: 30 days base, up to 45 days with strong negative bias.

---

## Task 1: Settings flags + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, add right after the `forgetting_*` block:

```python
    # ── Dream bias (Lag 2 — added 2026-05-10) ──────────────────────────
    # Master kill-switch for bias APPLICATION. When False, all 5 plug-in
    # sites return None from get_active_dream_bias(). Daemon still produces
    # bias rows for observability — we can see what would have biased.
    dream_bias_enabled: bool = True
    # Min number of NEW regret-events (since last bias row) needed to fire
    # distillation. Below this, daemon skips the cycle.
    dream_bias_min_content_events: int = 3
    # Lookback window for fetching the 6 regret-heavy sources.
    dream_bias_corpus_lookback_hours: int = 24
    # How long an active bias lasts before TTL expires. Resets on each
    # accumulation. 8h matches "morgen-til-frokost" intuition.
    dream_bias_ttl_hours: int = 8
    # Visible-idle minimum before distillation can fire. Reuses existing
    # daemon's idle-detection pattern.
    dream_bias_visible_idle_minutes: int = 30
    # Per-cycle cap on events fed to LLM (cost protection).
    dream_bias_max_corpus_events: int = 30
    # LLM call budget — max tokens for the JSON response.
    dream_bias_max_response_tokens: int = 400
```

- [ ] **Step 2: Wire defaults into load_settings**

In `core/runtime/settings.py`, find the `load_settings` function and add these 7 lines after the `forgetting_*` block (matching the existing pattern):

```python
        dream_bias_enabled=bool(
            data.get("dream_bias_enabled", defaults.dream_bias_enabled)
        ),
        dream_bias_min_content_events=int(
            data.get("dream_bias_min_content_events", defaults.dream_bias_min_content_events)
        ),
        dream_bias_corpus_lookback_hours=int(
            data.get("dream_bias_corpus_lookback_hours", defaults.dream_bias_corpus_lookback_hours)
        ),
        dream_bias_ttl_hours=int(
            data.get("dream_bias_ttl_hours", defaults.dream_bias_ttl_hours)
        ),
        dream_bias_visible_idle_minutes=int(
            data.get("dream_bias_visible_idle_minutes", defaults.dream_bias_visible_idle_minutes)
        ),
        dream_bias_max_corpus_events=int(
            data.get("dream_bias_max_corpus_events", defaults.dream_bias_max_corpus_events)
        ),
        dream_bias_max_response_tokens=int(
            data.get("dream_bias_max_response_tokens", defaults.dream_bias_max_response_tokens)
        ),
```

- [ ] **Step 3: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES` (next to `cognitive_forgetting`):

```python
    "cognitive_dream_bias",  # dream-driven attention/threshold biases (added 2026-05-10)
```

- [ ] **Step 4: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
s = RuntimeSettings()
assert s.dream_bias_enabled is True
assert s.dream_bias_min_content_events == 3
assert s.dream_bias_ttl_hours == 8
assert s.dream_bias_corpus_lookback_hours == 24
assert 'cognitive_dream_bias' in ALLOWED_EVENT_FAMILIES
loaded = load_settings()
assert loaded.dream_bias_enabled is True
print('ok')
"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(dream-bias): settings flags + cognitive_dream_bias event family"
```

---

## Task 2: DB migration — dream_bias_active table

**Files:**
- Modify: `core/runtime/db.py`
- Create: `tests/runtime/test_dream_bias_migration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_dream_bias_migration.py`:

```python
"""Schema migration for dream_bias_active (Lag 2 Phase 1)."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import _ensure_dream_bias_active_table


def test_dream_bias_active_table_created() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dream_bias_active'"
    ).fetchone()
    assert row is not None


def test_dream_bias_active_has_expected_columns() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dream_bias_active)").fetchall()}
    expected = {
        "bias_id", "workspace_id",
        "attention_bias_json", "threshold_bias_json",
        "intensity", "ttl_expires_at",
        "dream_text", "accumulated_count", "last_dream_at",
        "source_event_ids_json", "source_kinds_json",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_workspace_id_is_unique() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    conn.execute(
        "INSERT INTO dream_bias_active (bias_id, workspace_id, ttl_expires_at, "
        "last_dream_at, created_at, updated_at) VALUES "
        "('a', 'default', 'ttl', 'now', 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dream_bias_active (bias_id, workspace_id, ttl_expires_at, "
            "last_dream_at, created_at, updated_at) VALUES "
            "('b', 'default', 'ttl', 'now', 'now', 'now')"
        )


def test_table_creation_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    _ensure_dream_bias_active_table(conn)  # must not raise
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dream_bias_active'"
    ).fetchone()
    assert row is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/runtime/test_dream_bias_migration.py -v
```
Expected: 4 tests fail with import error on `_ensure_dream_bias_active_table`.

- [ ] **Step 3: Add migration function to db.py**

In `core/runtime/db.py`, find `_ensure_absence_traces_table` (added 2026-05-10) and add this immediately after it:

```python
def _ensure_dream_bias_active_table(conn: sqlite3.Connection) -> None:
    """Create dream_bias_active table for Lag 2 dream-bias (added 2026-05-10).

    One row per workspace (UNIQUE constraint). Daemon UPSERTs on accumulation.
    Self-marker rows carry NO memory_id reference — only timestamp and a
    relative period_label derived from the dream's source events.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dream_bias_active (
            bias_id              TEXT PRIMARY KEY,
            workspace_id         TEXT NOT NULL UNIQUE,
            attention_bias_json  TEXT NOT NULL DEFAULT '{}',
            threshold_bias_json  TEXT NOT NULL DEFAULT '{}',
            intensity            REAL NOT NULL DEFAULT 0.0,
            ttl_expires_at       TEXT NOT NULL,
            dream_text           TEXT NOT NULL DEFAULT '',
            accumulated_count    INTEGER NOT NULL DEFAULT 1,
            last_dream_at        TEXT NOT NULL,
            source_event_ids_json TEXT NOT NULL DEFAULT '[]',
            source_kinds_json    TEXT NOT NULL DEFAULT '[]',
            created_at           TEXT NOT NULL,
            updated_at           TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_dream_bias_active_workspace "
        "ON dream_bias_active(workspace_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_dream_bias_active_ttl "
        "ON dream_bias_active(ttl_expires_at)"
    )
```

- [ ] **Step 4: Wire into init_db**

In `core/runtime/db.py`, find where `_ensure_absence_traces_table(conn)` is called and add `_ensure_dream_bias_active_table(conn)` immediately after:

```python
        _ensure_absence_traces_table(conn)
        _ensure_soft_deleted_at_columns(conn)
        _ensure_dream_bias_active_table(conn)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/runtime/test_dream_bias_migration.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_dream_bias_migration.py
git commit -m "feat(dream-bias): dream_bias_active schema with UNIQUE(workspace_id)"
```

---

## Task 3: DB helpers — `db_dream_bias.py`

**Files:**
- Create: `core/runtime/db_dream_bias.py`
- Create: `tests/runtime/test_db_dream_bias.py`

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_db_dream_bias.py`:

```python
"""Tests for db_dream_bias helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Steer connect() at a fresh on-disk DB for each test."""
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


def test_insert_new_bias_creates_row(fresh_db):
    from core.runtime.db_dream_bias import insert_new_bias

    result = insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={"loop_persistence": 0.2},
        intensity=0.6,
        ttl_hours=8,
        dream_text="test dream",
        source_event_ids=["e1", "e2"],
        source_kinds=["self_review_outcome"],
    )
    assert result["accumulated_count"] == 1
    assert result["intensity"] == 0.6


def test_get_active_bias_raw_returns_inserted(fresh_db):
    from core.runtime.db_dream_bias import insert_new_bias, get_active_bias_raw

    insert_new_bias(
        workspace_id="default",
        attention_bias={"regret_threads": 0.5},
        threshold_bias={},
        intensity=0.7,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )
    row = get_active_bias_raw(workspace_id="default")
    assert row is not None
    assert row["intensity"] == 0.7
    assert row["attention_bias"] == {"regret_threads": 0.5}


def test_get_active_bias_raw_returns_none_for_unknown_workspace(fresh_db):
    from core.runtime.db_dream_bias import get_active_bias_raw
    row = get_active_bias_raw(workspace_id="nonexistent")
    assert row is None


def test_update_existing_bias_replaces_values(fresh_db):
    from core.runtime.db_dream_bias import (
        insert_new_bias, update_existing_bias, get_active_bias_raw,
    )

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.3},
        threshold_bias={},
        intensity=0.5,
        ttl_hours=8,
        dream_text="first",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )
    update_existing_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.6, "regret_threads": 0.4},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.8,
        ttl_hours=8,
        dream_text="first\n— second",
        accumulated_count=2,
        source_event_ids=["e1", "e2"],
        source_kinds=["self_review_outcome", "decision_revoked"],
    )
    row = get_active_bias_raw(workspace_id="default")
    assert row["accumulated_count"] == 2
    assert row["intensity"] == 0.8
    assert row["attention_bias"]["regret_threads"] == 0.4
    assert "second" in row["dream_text"]


def test_delete_expired_removes_old_rows(fresh_db):
    from datetime import datetime, timezone, timedelta
    from core.runtime.db import connect
    from core.runtime.db_dream_bias import (
        insert_new_bias, delete_expired_bias_rows,
    )

    # Insert a row, then backdate its TTL
    insert_new_bias(
        workspace_id="default",
        attention_bias={},
        threshold_bias={},
        intensity=0.5,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )
    expired_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    with connect() as c:
        c.execute(
            "UPDATE dream_bias_active SET ttl_expires_at = ? WHERE workspace_id = ?",
            (expired_iso, "default"),
        )

    deleted = delete_expired_bias_rows()
    assert deleted == 1

    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM dream_bias_active").fetchone()[0]
    assert n == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/runtime/test_db_dream_bias.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the helper module**

Create `core/runtime/db_dream_bias.py`:

```python
"""DB helpers for dream_bias_active (Lag 2 dream-bias).

Single-row-per-workspace UPSERT semantics. Lives separately from db.py to
keep that file from growing further. Read API bypasses kill-switch — the
engine's get_active_dream_bias() wraps this with the enabled-check.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _future_iso(*, hours: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def insert_new_bias(
    *,
    workspace_id: str,
    attention_bias: dict[str, float],
    threshold_bias: dict[str, float],
    intensity: float,
    ttl_hours: int,
    dream_text: str,
    source_event_ids: list[str],
    source_kinds: list[str],
) -> dict[str, Any]:
    """INSERT a fresh bias row for a workspace.

    Caller must ensure no existing row exists OR existing row was just
    deleted — UNIQUE(workspace_id) constraint will raise otherwise.
    """
    now = _now()
    ttl_at = _future_iso(hours=ttl_hours)
    bias_id = f"db_{workspace_id}_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        # Best-effort delete in case there's an expired row blocking UNIQUE
        conn.execute(
            "DELETE FROM dream_bias_active WHERE workspace_id = ?",
            (workspace_id,),
        )
        conn.execute(
            "INSERT INTO dream_bias_active "
            "(bias_id, workspace_id, attention_bias_json, threshold_bias_json, "
            "intensity, ttl_expires_at, dream_text, accumulated_count, "
            "last_dream_at, source_event_ids_json, source_kinds_json, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (
                bias_id, workspace_id,
                json.dumps(attention_bias), json.dumps(threshold_bias),
                float(intensity), ttl_at,
                dream_text[:400], now,
                json.dumps(source_event_ids[-50:]),
                json.dumps(source_kinds),
                now, now,
            ),
        )
    return {
        "bias_id": bias_id,
        "workspace_id": workspace_id,
        "accumulated_count": 1,
        "intensity": float(intensity),
        "ttl_expires_at": ttl_at,
    }


def update_existing_bias(
    *,
    workspace_id: str,
    attention_bias: dict[str, float],
    threshold_bias: dict[str, float],
    intensity: float,
    ttl_hours: int,
    dream_text: str,
    accumulated_count: int,
    source_event_ids: list[str],
    source_kinds: list[str],
) -> bool:
    """Update existing row in place. Returns True if a row was updated."""
    now = _now()
    ttl_at = _future_iso(hours=ttl_hours)
    with connect() as conn:
        cur = conn.execute(
            "UPDATE dream_bias_active SET "
            "attention_bias_json = ?, threshold_bias_json = ?, "
            "intensity = ?, ttl_expires_at = ?, "
            "dream_text = ?, accumulated_count = ?, last_dream_at = ?, "
            "source_event_ids_json = ?, source_kinds_json = ?, "
            "updated_at = ? "
            "WHERE workspace_id = ?",
            (
                json.dumps(attention_bias), json.dumps(threshold_bias),
                float(intensity), ttl_at,
                dream_text[:400], int(accumulated_count), now,
                json.dumps(source_event_ids[-50:]),
                json.dumps(source_kinds),
                now, workspace_id,
            ),
        )
        return cur.rowcount > 0


def get_active_bias_raw(*, workspace_id: str) -> dict[str, Any] | None:
    """Read the single active bias row for a workspace.

    Returns None if no row exists OR if TTL has expired. Does NOT honor
    the dream_bias_enabled kill-switch — that's the engine's concern.
    Includes parsed JSON fields for caller convenience.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT bias_id, workspace_id, attention_bias_json, threshold_bias_json, "
            "intensity, ttl_expires_at, dream_text, accumulated_count, last_dream_at, "
            "source_event_ids_json, source_kinds_json, created_at, updated_at "
            "FROM dream_bias_active WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    if row is None:
        return None
    # TTL check: caller may want raw row even if expired (for cleanup)
    # but the public interface treats expired = None
    ttl_iso = str(row[5] or "")
    if ttl_iso and ttl_iso < _now():
        return None
    return {
        "bias_id": row[0],
        "workspace_id": row[1],
        "attention_bias": json.loads(row[2] or "{}"),
        "threshold_bias": json.loads(row[3] or "{}"),
        "intensity": float(row[4] or 0.0),
        "ttl_expires_at": ttl_iso,
        "dream_text": str(row[6] or ""),
        "accumulated_count": int(row[7] or 0),
        "last_dream_at": str(row[8] or ""),
        "source_event_ids": json.loads(row[9] or "[]"),
        "source_kinds": json.loads(row[10] or "[]"),
        "created_at": str(row[11] or ""),
        "updated_at": str(row[12] or ""),
    }


def delete_expired_bias_rows() -> int:
    """Hard-delete rows whose TTL has passed. Returns count."""
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM dream_bias_active WHERE ttl_expires_at < ?",
            (now,),
        )
        return cur.rowcount
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/runtime/test_db_dream_bias.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db_dream_bias.py tests/runtime/test_db_dream_bias.py
git commit -m "feat(dream-bias): db_dream_bias.py — INSERT/UPDATE/get/delete helpers"
```

---

## Task 4: dream_bias_engine.py — distillation + accumulate + heartbeat formatter

**Files:**
- Create: `core/services/dream_bias_engine.py`
- Create: `tests/services/test_dream_bias_engine.py`

This is the largest task — the engine has many concerns. Tests cover validation, accumulate, kill-switch, heartbeat formatter.

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_dream_bias_engine.py`:

```python
"""Tests for dream_bias_engine — validation, accumulate, formatter."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


# ── Vocabulary + validation ────────────────────────────────────────


def test_validate_accepts_clean_output(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "Stilheden var lang.",
        "attention_bias": {"unfinished_business": 0.4},
        "threshold_bias": {"loop_persistence": 0.2},
        "intensity": 0.6,
    })
    assert out is not None
    assert out["dream_text"] == "Stilheden var lang."
    assert out["attention_bias"] == {"unfinished_business": 0.4}
    assert out["threshold_bias"] == {"loop_persistence": 0.2}
    assert out["intensity"] == 0.6


def test_validate_drops_unknown_keys(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 0.3, "fake_key": 0.5},
        "threshold_bias": {"loop_persistence": 0.1, "made_up": 0.9},
        "intensity": 0.5,
    })
    assert "fake_key" not in out["attention_bias"]
    assert "made_up" not in out["threshold_bias"]


def test_validate_clamps_to_unit_range(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 5.0, "regret_threads": -3.0},
        "threshold_bias": {},
        "intensity": 0.5,
    })
    assert out["attention_bias"]["unfinished_business"] == 1.0
    assert out["attention_bias"]["regret_threads"] == -1.0


def test_validate_forces_self_critique_volume_non_positive(fresh_db):
    """Hard guard: dreams may only soften self-criticism, not sharpen it."""
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {},
        "threshold_bias": {"self_critique_volume": 0.7},  # LLM tried to amplify
        "intensity": 0.5,
    })
    assert out["threshold_bias"]["self_critique_volume"] == 0.0


def test_validate_returns_none_for_empty_output(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "",
        "attention_bias": {},
        "threshold_bias": {},
        "intensity": 0.5,
    })
    assert out is None


def test_validate_defaults_invalid_intensity(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 0.3},
        "threshold_bias": {},
        "intensity": "not-a-number",
    })
    assert out["intensity"] == 0.5


# ── Accumulate ────────────────────────────────────────────────────


def test_accumulate_sums_with_intensity_multiplier(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    prior = {"unfinished_business": 0.3}
    new = {"unfinished_business": 0.5}
    out = accumulate_bias(prior, new, intensity=0.4)
    # 0.3 + (0.5 * 0.4) = 0.3 + 0.2 = 0.5
    assert abs(out["unfinished_business"] - 0.5) < 0.0001


def test_accumulate_clamps_to_unit_range(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    prior = {"unfinished_business": 0.9}
    new = {"unfinished_business": 0.8}
    out = accumulate_bias(prior, new, intensity=1.0)
    assert out["unfinished_business"] == 1.0  # clamped


def test_accumulate_drops_unknown_keys(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    out = accumulate_bias({}, {"fake_key": 0.5}, intensity=1.0)
    assert "fake_key" not in out


# ── Kill-switch ───────────────────────────────────────────────────


def test_get_active_dream_bias_returns_none_when_disabled(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import get_active_dream_bias

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={},
        intensity=0.6,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )

    class _FakeSettings:
        dream_bias_enabled = False

    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    bias = get_active_dream_bias(workspace_id="default")
    assert bias is None


def test_get_active_dream_bias_returns_data_when_enabled(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import get_active_dream_bias

    insert_new_bias(
        workspace_id="default",
        attention_bias={"regret_threads": 0.4},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.5,
        ttl_hours=8,
        dream_text="test",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )

    class _FakeSettings:
        dream_bias_enabled = True

    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    bias = get_active_dream_bias(workspace_id="default")
    assert bias is not None
    assert bias["attention_bias"]["regret_threads"] == 0.4
    assert bias["threshold_bias"]["loop_persistence"] == -0.2
    assert bias["intensity"] == 0.5


# ── Heartbeat formatter ───────────────────────────────────────────


def test_heartbeat_formatter_returns_empty_when_no_bias(fresh_db, monkeypatch):
    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert out == ""


def test_heartbeat_formatter_skips_low_intensity(fresh_db, monkeypatch):
    """Intensity < 0.1 should produce empty render — too weak to surface."""
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={},
        intensity=0.05,  # below threshold
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )

    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert out == ""


def test_heartbeat_formatter_renders_active_bias(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4, "regret_threads": 0.3},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.7,
        ttl_hours=8,
        dream_text="Stilheden var lang.",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )

    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert "dream_bias active" in out
    assert "unfinished_business" in out
    assert "regret_threads" in out
    assert "loop_persistence" in out
    assert "Stilheden" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_dream_bias_engine.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the engine**

Create `core/services/dream_bias_engine.py`:

```python
"""Dream bias engine — Lag 2 distillation + bias state.

Pure-logic distillation orchestrator. Daemon (existing
dream_distillation_daemon) calls run_dream_bias_distillation per cycle.

Two-track output: structured attention/threshold bias data + observability
text. Validates strictly against locked vocabulary. Accumulates with cap
±1.0 per key, intensity-multiplied. TTL-based expiry, single row per
workspace.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_dream_bias import (
    delete_expired_bias_rows,
    get_active_bias_raw,
    insert_new_bias,
    update_existing_bias,
)
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


# ── Locked vocabulary ─────────────────────────────────────────────────

ATTENTION_VOCAB: frozenset[str] = frozenset({
    "unfinished_business",
    "friction_with_user",
    "inner_dissent",
    "regret_threads",
    "relational_warmth",
})

THRESHOLD_VOCAB: frozenset[str] = frozenset({
    "friction_tolerance",
    "commitment_courage",
    "self_critique_volume",
    "loop_persistence",
})

# Intensity below this → bias is too weak to surface in heartbeat.
_HEARTBEAT_INTENSITY_FLOOR = 0.1

# accumulated_count beyond this forces a fresh row on next dream.
_MAX_ACCUMULATED_COUNT = 5


# ── Helpers ────────────────────────────────────────────────────────────

def _coerce_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(UTC)


# ── Validation ─────────────────────────────────────────────────────────

def _validate_dream_output(raw: dict) -> dict | None:
    """Sanitize LLM output — drop unknown keys, clamp values, force guards.

    Returns None if all bias fields and dream_text are empty.
    """
    if not isinstance(raw, dict):
        return None

    text = str(raw.get("dream_text", "")).strip()[:400]

    attention_raw = raw.get("attention_bias") or {}
    attention: dict[str, float] = {}
    if isinstance(attention_raw, dict):
        for key in ATTENTION_VOCAB:
            if key in attention_raw:
                v = _coerce_float(attention_raw[key])
                if v is not None:
                    attention[key] = max(-1.0, min(1.0, v))

    threshold_raw = raw.get("threshold_bias") or {}
    threshold: dict[str, float] = {}
    if isinstance(threshold_raw, dict):
        for key in THRESHOLD_VOCAB:
            if key in threshold_raw:
                v = _coerce_float(threshold_raw[key])
                if v is not None:
                    clamped = max(-1.0, min(1.0, v))
                    # Hard guard: dreams may only soften self-criticism.
                    if key == "self_critique_volume":
                        clamped = min(0.0, clamped)
                    threshold[key] = clamped

    intensity = _coerce_float(raw.get("intensity"))
    if intensity is None or not 0.0 <= intensity <= 1.0:
        intensity = 0.5

    if not attention and not threshold and not text:
        return None

    return {
        "dream_text": text,
        "attention_bias": attention,
        "threshold_bias": threshold,
        "intensity": intensity,
    }


# ── Accumulate ─────────────────────────────────────────────────────────

def accumulate_bias(
    prior: dict[str, float],
    new: dict[str, float],
    intensity: float,
) -> dict[str, float]:
    """Add new bias values to prior, multiplied by intensity, clamped ±1.0.

    Drops any keys not in the locked vocabulary.
    """
    valid_keys = ATTENTION_VOCAB | THRESHOLD_VOCAB
    out = {k: v for k, v in prior.items() if k in valid_keys}
    for key, new_value in new.items():
        if key not in valid_keys:
            continue
        contribution = float(new_value) * float(intensity)
        out[key] = max(-1.0, min(1.0, out.get(key, 0.0) + contribution))
    return out


# ── Public read API ───────────────────────────────────────────────────

def get_active_dream_bias(*, workspace_id: str = "default") -> dict[str, Any] | None:
    """Read active bias, honoring kill-switch + TTL.

    Returns None if:
    - dream_bias_enabled is False
    - No active row exists
    - TTL has expired
    """
    try:
        if not load_settings().dream_bias_enabled:
            return None
    except Exception:
        # Settings unavailable — fail open and return raw bias
        pass
    return get_active_bias_raw(workspace_id=workspace_id)


# ── Heartbeat formatter ───────────────────────────────────────────────

def format_dream_bias_for_heartbeat(*, workspace_id: str = "default") -> str:
    """Render bias as a structured awareness-section block.

    Returns empty string if:
    - kill-switch off
    - no active bias
    - intensity < _HEARTBEAT_INTENSITY_FLOOR
    """
    bias = get_active_dream_bias(workspace_id=workspace_id)
    if not bias:
        return ""
    if float(bias.get("intensity") or 0.0) < _HEARTBEAT_INTENSITY_FLOOR:
        return ""

    # Compute time fields
    try:
        ttl_at = datetime.fromisoformat(
            str(bias.get("ttl_expires_at") or "").replace("Z", "+00:00")
        )
        last_at = datetime.fromisoformat(
            str(bias.get("last_dream_at") or "").replace("Z", "+00:00")
        )
        now = _now()
        age_hours = (now - last_at).total_seconds() / 3600.0
        remaining_hours = max(0.0, (ttl_at - now).total_seconds() / 3600.0)
    except Exception:
        age_hours = 0.0
        remaining_hours = 0.0

    # Format attention/threshold lists, signed numerics
    def _fmt_pairs(d: dict[str, float]) -> str:
        if not d:
            return "(none)"
        parts = []
        for k, v in d.items():
            sign = "+" if v >= 0 else ""
            parts.append(f"{k} {sign}{v:.2f}")
        return ", ".join(parts)

    lines = [
        f"[dream_bias active — fra ~{age_hours:.0f}h siden, fader om {remaining_hours:.0f}h]",
        f"attention: {_fmt_pairs(bias.get('attention_bias') or {})}",
        f"thresholds: {_fmt_pairs(bias.get('threshold_bias') or {})}",
    ]

    text = str(bias.get("dream_text") or "").strip()
    if text:
        # Truncate to ~150 chars for heartbeat budget
        if len(text) > 150:
            text = text[:147].rstrip() + "…"
        lines.append(f'drøm: "{text}"')

    return "\n".join(lines)


# ── Distillation orchestrator ─────────────────────────────────────────

def run_dream_bias_distillation(*, workspace_id: str = "default") -> dict[str, Any]:
    """Full pipeline. Called by dream_distillation_daemon each cycle.

    Phases:
    1. Cleanup expired rows
    2. Min-content gate
    3. LLM distillation
    4. Validate
    5. UPSERT
    6. Publish event
    """
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    # Phase 1: cleanup expired
    expired_count = delete_expired_bias_rows()

    # Phase 2: min-content gate
    has_content, new_events = _has_minimum_dream_content(
        workspace_id=workspace_id, settings=settings
    )
    if not has_content:
        return {
            "status": "no_content",
            "expired_cleaned": expired_count,
            "new_event_count": len(new_events),
        }

    # Phase 3: LLM distillation
    raw_response = _call_llm_for_bias(
        events=new_events,
        max_tokens=settings.dream_bias_max_response_tokens,
    )
    if not raw_response:
        return {"status": "llm_failed", "expired_cleaned": expired_count}

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.warning("dream_bias: JSON parse failed: %s", exc)
        return {"status": "json_parse_failed", "raw_preview": raw_response[:120]}

    # Phase 4: validate
    validated = _validate_dream_output(parsed)
    if validated is None:
        return {"status": "empty_distillation"}

    # Phase 5: UPSERT
    result = _upsert_dream_bias(
        workspace_id=workspace_id,
        validated=validated,
        source_events=new_events,
        ttl_hours=settings.dream_bias_ttl_hours,
    )

    # Phase 6: publish event
    try:
        event_bus.publish(
            "cognitive_dream_bias.distilled",
            {
                "workspace_id": workspace_id,
                "intensity": validated["intensity"],
                "attention_keys": list(validated["attention_bias"].keys()),
                "threshold_keys": list(validated["threshold_bias"].keys()),
                "dream_text_preview": validated["dream_text"][:80],
                "source_count": len(new_events),
                "accumulated_count": result.get("accumulated_count", 1),
            },
        )
    except Exception as exc:
        logger.debug("dream_bias publish failed: %s", exc)

    return {
        "status": "distilled",
        "intensity": validated["intensity"],
        "accumulated_count": result.get("accumulated_count", 1),
        "expired_cleaned": expired_count,
    }


# ── Min-content gate ──────────────────────────────────────────────────

def _has_minimum_dream_content(
    *, workspace_id: str, settings
) -> tuple[bool, list[dict]]:
    """≥3 new regret-events since the active bias's source_event_ids."""
    prior = get_active_bias_raw(workspace_id=workspace_id) or {}
    seen_ids = set(prior.get("source_event_ids") or [])

    cutoff = (_now() - timedelta(hours=settings.dream_bias_corpus_lookback_hours)).isoformat().replace("+00:00", "Z")
    candidates = _fetch_regret_corpus(
        since_iso=cutoff,
        limit=settings.dream_bias_max_corpus_events,
    )
    new_events = [e for e in candidates if e["event_id"] not in seen_ids]
    if len(new_events) < settings.dream_bias_min_content_events:
        return False, new_events
    return True, new_events


# ── Corpus fetch from 6 regret-heavy sources ─────────────────────────

# Maps event-kind → human description used in LLM corpus formatting.
_REGRET_EVENT_KINDS: dict[str, str] = {
    "self_review_outcome.created": "self_review_outcome",
    "conflict.detected": "conflict_detected",
    "decision_revoked": "decision_revoked",
    "behavioral_decision_review.broken": "decision_review_broken",
}

# rupture.* events get a separate prefix-LIKE query.


def _fetch_regret_corpus(*, since_iso: str, limit: int = 30) -> list[dict]:
    """Pull events from the 6 regret-heavy sources.

    Sources (mapped to event kinds in the events table):
    1. self_review_outcome.created (4-trigger family overlap with counterfactuals)
    2. conflict.detected
    3. decision_revoked
    4. behavioral_decision_review.broken
    5. rupture.* (prefix match)
    6. counterfactual events (cognitive_counterfactual.generated when Phase 2
       LLM kicks in; for Phase 1 dry-run it'll be empty — acceptable, the
       other 5 sources carry the corpus)
    """
    from core.runtime.db import connect

    events = []
    placeholders = ",".join("?" for _ in _REGRET_EVENT_KINDS)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE (kind IN ({placeholders}) OR kind LIKE 'rupture.%' "
        f"OR kind LIKE 'cognitive_counterfactual.%') "
        f"AND created_at >= ? "
        f"ORDER BY created_at DESC LIMIT ?"
    )
    params = list(_REGRET_EVENT_KINDS.keys()) + [since_iso, limit]
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("dream_bias: corpus fetch failed: %s", exc)
        return []

    for r in rows:
        kind = str(r["kind"] or "")
        if kind in _REGRET_EVENT_KINDS:
            source_kind = _REGRET_EVENT_KINDS[kind]
        elif kind.startswith("rupture."):
            source_kind = "rupture_repair"
        elif kind.startswith("cognitive_counterfactual."):
            source_kind = "counterfactual"
        else:
            continue

        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}

        # Build a short summary from payload
        summary = _summarize_payload(payload, kind)

        events.append({
            "event_id": str(r["id"]),
            "source_kind": source_kind,
            "kind": kind,
            "created_at": str(r["created_at"] or ""),
            "summary": summary[:200],
        })
    return events


def _summarize_payload(payload: dict, kind: str) -> str:
    """Best-effort short-summary line for an event payload."""
    for key in ("description", "summary", "directive", "verdict", "reason", "title"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"({kind} event)"


# ── LLM call ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Jarvis' dream distillation. You receive recent regret-heavy events
from his last 24 hours: broken decisions, conflicts, friction, regret.

Produce a brief dream and structured biases that should shape his next
waking cycle. Output STRICT JSON only — no prose, no markdown:

{
  "dream_text": "...",
  "attention_bias": {
    "unfinished_business": 0.0,
    "friction_with_user": 0.0,
    "inner_dissent": 0.0,
    "regret_threads": 0.0,
    "relational_warmth": 0.0
  },
  "threshold_bias": {
    "friction_tolerance": 0.0,
    "commitment_courage": 0.0,
    "self_critique_volume": 0.0,
    "loop_persistence": 0.0
  },
  "intensity": 0.0
}

Rules:
- Only include keys actually relevant to the events. Omit irrelevant keys.
- Values are floats in [-1.0, 1.0].
- self_critique_volume must be 0.0 or negative (dreams soften, never sharpen).
- intensity is a float in [0.0, 1.0] reflecting emotional density.
- dream_text is 50-200 chars in Danish, first-person, present tense, sparse.
"""


def _call_llm_for_bias(*, events: list[dict], max_tokens: int) -> str:
    """Call quality-lane LLM. Returns raw text response (possibly empty)."""
    if not events:
        return ""
    listing = "\n".join(
        f"- [{e['source_kind']}] {e['summary']}"
        for e in events[:30]
    )
    user_message = (
        f"Recent regret-heavy events ({len(events)} events from last 24h):\n\n"
        f"{listing}\n\n"
        f"Produce the JSON."
    )
    full_prompt = _SYSTEM_PROMPT + "\n\n" + user_message
    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        return quality_daemon_llm_call(
            full_prompt,
            max_len=max_tokens,
            fallback="",
            daemon_name="dream_bias",
        )
    except Exception as exc:
        logger.warning("dream_bias: LLM call failed: %s", exc)
        return ""


# ── UPSERT ─────────────────────────────────────────────────────────────

def _upsert_dream_bias(
    *,
    workspace_id: str,
    validated: dict,
    source_events: list[dict],
    ttl_hours: int,
) -> dict[str, Any]:
    """INSERT new or accumulate into existing row."""
    prior = get_active_bias_raw(workspace_id=workspace_id)
    intensity = validated["intensity"]

    is_at_cap = prior is not None and int(prior.get("accumulated_count") or 0) >= _MAX_ACCUMULATED_COUNT

    if prior is None or is_at_cap:
        # INSERT new (existing TTL-expired/missing/at-cap → fresh row)
        result = insert_new_bias(
            workspace_id=workspace_id,
            attention_bias=validated["attention_bias"],
            threshold_bias=validated["threshold_bias"],
            intensity=intensity,
            ttl_hours=ttl_hours,
            dream_text=validated["dream_text"],
            source_event_ids=[e["event_id"] for e in source_events],
            source_kinds=list({e["source_kind"] for e in source_events}),
        )
        return {"accumulated_count": 1, "intensity": intensity}

    # Accumulate
    new_attn = accumulate_bias(
        prior["attention_bias"], validated["attention_bias"], intensity
    )
    new_thr = accumulate_bias(
        prior["threshold_bias"], validated["threshold_bias"], intensity
    )
    new_text = (prior["dream_text"] + "\n— " + validated["dream_text"])[-400:]
    merged_ids = (
        list(prior["source_event_ids"]) + [e["event_id"] for e in source_events]
    )[-50:]
    merged_kinds = list({
        *prior["source_kinds"],
        *(e["source_kind"] for e in source_events),
    })
    new_count = int(prior["accumulated_count"] or 0) + 1
    peak_intensity = max(float(prior["intensity"] or 0.0), intensity)

    update_existing_bias(
        workspace_id=workspace_id,
        attention_bias=new_attn,
        threshold_bias=new_thr,
        intensity=peak_intensity,
        ttl_hours=ttl_hours,
        dream_text=new_text,
        accumulated_count=new_count,
        source_event_ids=merged_ids,
        source_kinds=merged_kinds,
    )
    return {"accumulated_count": new_count, "intensity": peak_intensity}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/services/test_dream_bias_engine.py -v
```
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/dream_bias_engine.py tests/services/test_dream_bias_engine.py
git commit -m "feat(dream-bias): dream_bias_engine.py — distill, validate, accumulate, format"
```

---

## Task 5: Wire bias-distillation into `dream_distillation_daemon`

**Files:**
- Modify: `core/services/dream_distillation_daemon.py`

The existing daemon produces residue-text once per cycle. We add a parallel call to `run_dream_bias_distillation` so both pipelines fire on the same trigger. The bias-pipeline has its own min-content gate; if there's no regret material, the call is cheap (no LLM call).

- [ ] **Step 1: Find the daemon's main entry point**

```bash
grep -n "def run_dream_distillation_daemon" /media/projects/jarvis-v2/core/services/dream_distillation_daemon.py
```
Expected: line ~24.

- [ ] **Step 2: Add bias-distillation call**

In `core/services/dream_distillation_daemon.py`, find the function `run_dream_distillation_daemon` (around line 24). After the existing residue-pipeline code returns its result, add a parallel call. Locate the final return statement of the function (likely `return {"status": "written", **payload}` or similar) and modify the function to call the bias engine before returning:

Pattern to add at the end of `run_dream_distillation_daemon` (before its return statement):

```python
    # ── Lag 2 dream-bias pipeline (added 2026-05-10) ────────────────
    # Runs alongside the residue-text pipeline. Has its own min-content
    # gate so an empty corpus produces no LLM call.
    bias_result: dict = {"status": "skipped"}
    try:
        from core.services.dream_bias_engine import run_dream_bias_distillation
        bias_result = run_dream_bias_distillation(workspace_id="default")
    except Exception as exc:
        logger.warning("dream_distillation_daemon: bias call failed: %s", exc)
        bias_result = {"status": "error", "reason": str(exc)[:120]}
```

Then modify the existing `return` statement to include bias_result:
- If existing return is `return {"status": "written", **payload}`, change to:
  `return {"status": "written", **payload, "bias_pipeline": bias_result}`
- Identify and modify ALL return paths similarly.

- [ ] **Step 3: Add logger import if missing**

In the same file, verify `import logging` and `logger = logging.getLogger(__name__)` are at the top. Add if missing.

- [ ] **Step 4: Verify it imports cleanly**

```bash
conda run -n ai python -c "
from core.services.dream_distillation_daemon import run_dream_distillation_daemon
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 5: Manual smoke — run the daemon function once**

```bash
conda run -n ai python -c "
from core.services.dream_distillation_daemon import run_dream_distillation_daemon
result = run_dream_distillation_daemon(trigger='manual-test')
print(result)
"
```
Expected: a dict containing `bias_pipeline` field. The bias_pipeline value will likely be `{"status": "no_content", ...}` if there are no recent regret events — that's correct.

- [ ] **Step 6: Commit**

```bash
git add core/services/dream_distillation_daemon.py
git commit -m "feat(dream-bias): wire bias-pipeline into dream_distillation_daemon"
```

---

## Task 6: Plug-in Site 1 — heartbeat prompt-injection

**Files:**
- Modify: `core/services/prompt_contract.py`

- [ ] **Step 1: Find the forgetting_section injection block**

```bash
grep -n "format_forgetting_section_for_heartbeat" /media/projects/jarvis-v2/core/services/prompt_contract.py
```
Expected: a block where forgetting_line is appended to `parts`.

- [ ] **Step 2: Add dream-bias injection immediately after**

In `core/services/prompt_contract.py`, find:

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

Add immediately after:

```python
    # Dream bias (Lag 2) — attention + threshold modulators from last dream
    try:
        from core.services.dream_bias_engine import (
            format_dream_bias_for_heartbeat,
        )
        dream_bias_line = format_dream_bias_for_heartbeat(workspace_id="default")
        if dream_bias_line:
            parts.append(dream_bias_line)
    except Exception:
        pass
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.services.prompt_contract import _build_heartbeat_living_context_line
# (just confirm the import loads — running the function requires DB state)
print('prompt_contract loads')
"
```
Expected: `prompt_contract loads`

- [ ] **Step 4: Commit**

```bash
git add core/services/prompt_contract.py
git commit -m "feat(dream-bias): heartbeat prompt-injection (Site 1)"
```

---

## Task 7: Plug-in Sites 2 + 3 — listing-limit modulation

**Files:**
- Modify: `core/services/open_loop_signal_tracking.py`
- Modify: `core/services/self_review_outcome_tracking.py`

These two share an identical pattern: bias modulates the `limit` parameter passed to the existing build-surface function. There's no per-row priority field, so we boost the count of rows surfaced instead.

- [ ] **Step 1: Modify open_loop_signal_tracking.py**

In `core/services/open_loop_signal_tracking.py`, find the function `_build_runtime_open_loop_signal_surface_uncached(*, limit: int = 8)` (around line 119). At the top of that function, before any other logic, add:

```python
def _build_runtime_open_loop_signal_surface_uncached(
    *, limit: int = 8
) -> dict[str, object]:
    # Dream bias (Lag 2) — unfinished_business amplifies how many open loops
    # surface. ±40% modulation at intensity=1.0 (limit floor 4, cap 16).
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        _bias = get_active_dream_bias(workspace_id="default")
        if _bias:
            _modifier = float(_bias["attention_bias"].get("unfinished_business", 0.0))
            _intensity = float(_bias.get("intensity") or 0.0)
            if _modifier != 0.0:
                _shift = _modifier * _intensity * 0.4
                limit = max(4, min(16, int(round(limit * (1.0 + _shift)))))
    except Exception:
        pass
    refresh_runtime_open_loop_signal_statuses()
    items = list_runtime_open_loop_signals(limit=limit)
    # ... rest of existing function unchanged
```

**Important**: only change the function's first lines. The rest (`refresh_runtime_open_loop_signal_statuses()` and below) stays exactly as-is.

- [ ] **Step 2: Modify self_review_outcome_tracking.py**

In `core/services/self_review_outcome_tracking.py`, find `def build_runtime_self_review_outcome_surface(*, limit: int = 8)` (around line 82). Add the same pattern at the top of the function with `regret_threads` key:

```python
def build_runtime_self_review_outcome_surface(*, limit: int = 8) -> dict[str, object]:
    # Dream bias (Lag 2) — regret_threads amplifies surfacing of negative outcomes.
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        _bias = get_active_dream_bias(workspace_id="default")
        if _bias:
            _modifier = float(_bias["attention_bias"].get("regret_threads", 0.0))
            _intensity = float(_bias.get("intensity") or 0.0)
            if _modifier != 0.0:
                _shift = _modifier * _intensity * 0.4
                limit = max(4, min(16, int(round(limit * (1.0 + _shift)))))
    except Exception:
        pass
    # ... rest of existing function unchanged
```

- [ ] **Step 3: Verify both files load**

```bash
conda run -n ai python -c "
from core.services.open_loop_signal_tracking import _build_runtime_open_loop_signal_surface_uncached
from core.services.self_review_outcome_tracking import build_runtime_self_review_outcome_surface
print('both loaded')
"
```
Expected: `both loaded`

- [ ] **Step 4: Commit**

```bash
git add core/services/open_loop_signal_tracking.py core/services/self_review_outcome_tracking.py
git commit -m "feat(dream-bias): list-limit modulation (Sites 2+3)"
```

---

## Task 8: Plug-in Site 4 — `visible_runs._MAX_EMPTY_TEXT_ROUNDS` modulation

**Files:**
- Modify: `core/services/visible_runs.py`

- [ ] **Step 1: Find the resolution site**

```bash
grep -n "_MAX_EMPTY_TEXT_ROUNDS = " /media/projects/jarvis-v2/core/services/visible_runs.py
```
Expected: around line 1176 — `_MAX_EMPTY_TEXT_ROUNDS = int(_agentic_budget.get("max_empty_text_rounds") or 12)`.

- [ ] **Step 2: Add bias modulation immediately after the existing line**

Find the existing line:

```python
                _MAX_EMPTY_TEXT_ROUNDS = int(_agentic_budget.get("max_empty_text_rounds") or 12)
```

Replace with:

```python
                _MAX_EMPTY_TEXT_ROUNDS = int(_agentic_budget.get("max_empty_text_rounds") or 12)
                # Dream bias (Lag 2) — loop_persistence shifts how long he stays in loop.
                # ±2 rounds at intensity=1.0; hard floor 4, cap 20.
                try:
                    from core.services.dream_bias_engine import get_active_dream_bias
                    _bias = get_active_dream_bias(workspace_id="default")
                    if _bias:
                        _persistence_mod = float(_bias["threshold_bias"].get("loop_persistence", 0.0))
                        _intensity = float(_bias.get("intensity") or 0.0)
                        if _persistence_mod != 0.0:
                            _shift = int(round(_persistence_mod * _intensity * 2))
                            _MAX_EMPTY_TEXT_ROUNDS = max(4, min(20, _MAX_EMPTY_TEXT_ROUNDS + _shift))
                except Exception:
                    pass
```

(Match the existing indentation level — this site is inside a function with significant indentation.)

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -m compileall -q core/services/visible_runs.py
echo "compile ok"
```
Expected: `compile ok`

- [ ] **Step 4: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(dream-bias): visible_runs MAX_EMPTY_TEXT_ROUNDS modulation (Site 4)"
```

---

## Task 9: Plug-in Site 5 — `self_critique_runtime` cadence modulation

**Files:**
- Modify: `core/services/self_critique_runtime.py`

- [ ] **Step 1: Find the cadence constant + check sites**

```bash
grep -n "_SELF_CRITIQUE_INTERVAL_DAYS" /media/projects/jarvis-v2/core/services/self_critique_runtime.py
```
Expected: 3 references — line 29 (definition), 97 (cadence check), 178 (next_due_at).

- [ ] **Step 2: Add a resolver function**

In `core/services/self_critique_runtime.py`, find the constant definition:

```python
_SELF_CRITIQUE_INTERVAL_DAYS = 30
```

Add immediately after it:

```python
_SELF_CRITIQUE_INTERVAL_DAYS_BASE = 30
_SELF_CRITIQUE_INTERVAL_DAYS = _SELF_CRITIQUE_INTERVAL_DAYS_BASE


def _resolve_self_critique_interval_days() -> int:
    """Read base interval, modulate by dream-bias self_critique_volume.

    self_critique_volume is forced ≤ 0 in distillation, so this only ever
    LENGTHENS the cadence (defers self-critique). Multiplier: 1.0 to 1.5.
    """
    base = _SELF_CRITIQUE_INTERVAL_DAYS_BASE
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        bias = get_active_dream_bias(workspace_id="default")
        if bias:
            mod = float(bias["threshold_bias"].get("self_critique_volume", 0.0))
            intensity = float(bias.get("intensity") or 0.0)
            multiplier = 1.0 + abs(mod) * intensity * 0.5
            return max(base, min(base * 2, int(round(base * multiplier))))
    except Exception:
        pass
    return base
```

- [ ] **Step 3: Replace usage sites**

Find the two usage sites (around lines 97 and 178) where `_SELF_CRITIQUE_INTERVAL_DAYS` is used in `timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)`. Replace both occurrences with `_resolve_self_critique_interval_days()`:

Site at line 97:
```python
    if last_written_at and (now - last_written_at) < timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS):
        next_due = last_written_at + timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)
```
→
```python
    _interval_days = _resolve_self_critique_interval_days()
    if last_written_at and (now - last_written_at) < timedelta(days=_interval_days):
        next_due = last_written_at + timedelta(days=_interval_days)
```

Site at line 178:
```python
        "next_due_at": (now + timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)).isoformat(),
```
→
```python
        "next_due_at": (now + timedelta(days=_resolve_self_critique_interval_days())).isoformat(),
```

- [ ] **Step 4: Verify**

```bash
conda run -n ai python -c "
from core.services.self_critique_runtime import _resolve_self_critique_interval_days
print('interval:', _resolve_self_critique_interval_days())
"
```
Expected: `interval: 30` (when no bias is active).

- [ ] **Step 5: Commit**

```bash
git add core/services/self_critique_runtime.py
git commit -m "feat(dream-bias): self_critique cadence modulation (Site 5)"
```

---

## Task 10: Smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add dream-bias verification block**

In `scripts/smoke_test_startup.py`, find the existing block that verifies `absence_traces` (added in forgetting Phase 1). Add immediately after it:

```python
        # Verify dream_bias_active table + engine importable (Lag 2)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='dream_bias_active'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("dream_bias_active table missing")
            from core.services.dream_bias_engine import (
                get_active_dream_bias,  # noqa: F401
                format_dream_bias_for_heartbeat,  # noqa: F401
                run_dream_bias_distillation,  # noqa: F401
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
git commit -m "test(dream-bias): smoke test verifies table + engine imports"
```

---

## Task 11: Deploy + day-1 verification

**Files:** none (deployment + observation only)

- [ ] **Step 1: Restart jarvis-runtime (where daemons run)**

```bash
sudo systemctl restart jarvis-runtime && sleep 6 && systemctl is-active jarvis-runtime
```
Expected: `active`

- [ ] **Step 2: Check daemon journal for errors**

```bash
journalctl -u jarvis-runtime --since "30 sec ago" --no-pager | grep -iE "dream_bias|error|traceback" | head -15
```
Expected: no tracebacks. Possibly some dream-bias log lines if a cycle has fired.

- [ ] **Step 3: Verify migration ran on production DB**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    row = c.execute(
        \"SELECT name FROM sqlite_master WHERE type='table' AND name='dream_bias_active'\"
    ).fetchone()
    print('table exists:', row is not None)
    # Check for any active rows
    n = c.execute('SELECT COUNT(*) FROM dream_bias_active').fetchone()[0]
    print('active rows:', n)
"
```
Expected: `table exists: True`, `active rows: 0` (or some small number).

- [ ] **Step 4: Force-run the bias-distillation pipeline**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.dream_bias_engine import run_dream_bias_distillation
result = run_dream_bias_distillation(workspace_id='default')
print(result)
"
```
Expected: a dict like `{'status': 'no_content', ...}` if there are no recent regret events. Or `{'status': 'distilled', 'intensity': N, ...}` if events exist. Either is correct — both are healthy outcomes.

- [ ] **Step 5: Test heartbeat formatter**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
out = format_dream_bias_for_heartbeat(workspace_id='default')
print(repr(out))
"
```
Expected: empty string `''` (no active row) OR a multi-line string starting with `[dream_bias active`.

- [ ] **Step 6: Test 4 plug-in sites still load**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.open_loop_signal_tracking import _build_runtime_open_loop_signal_surface_uncached
from core.services.self_review_outcome_tracking import build_runtime_self_review_outcome_surface
from core.services.self_critique_runtime import _resolve_self_critique_interval_days
import core.services.visible_runs  # just check import works
print('all 4 plug-in sites load')
"
```
Expected: `all 4 plug-in sites load`

- [ ] **Step 7: Document day-1 baseline**

Create `docs/superpowers/notes/2026-05-10-dream-bias-day1.md`:

```markdown
# Dream Bias Phase 1 — Day 1 baseline

**Date:** <today>
**Deployed:** <commit SHA from `git rev-parse HEAD`>

## Initial state

- `dream_bias_active` rows: <count>
- First force-run output (`run_dream_bias_distillation`): <paste of step 4>
- Heartbeat formatter output: <paste of step 5>

## Plug-in site verification

All 5 sites import cleanly:
- Site 1 (heartbeat prompt) — <verified via step 5>
- Site 2 (open_loop limit) — verified via import
- Site 3 (self_review_outcome limit) — verified via import
- Site 4 (visible_runs MAX_EMPTY_TEXT_ROUNDS) — verified via import
- Site 5 (self_critique cadence) — `_resolve_self_critique_interval_days()` returns 30 (no bias active)

## Open observations

- Initial corpus volume: how many regret events in last 24h? <count>
- LLM availability: which provider was used? <from journal>
- Any first-cycle fade in journal: <paste relevant lines>
```

- [ ] **Step 8: Commit baseline**

```bash
git add docs/superpowers/notes/2026-05-10-dream-bias-day1.md
git commit -m "docs(dream-bias): day-1 baseline observations"
```

---

## Task 12: Schedule 30-day review

**Files:** none (uses scheduled_tasks system)

- [ ] **Step 1: Create scheduled task**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
result = push_scheduled_task(
    focus=(
        'Dream Bias Phase 1 — 30-dages review. Tjek dream_bias_active row '
        'distributions (intensity, accumulated_count), kig efter signaler '
        'i chronicle/inner_voice om biases mærkes, om plug-ins faktisk '
        'modulerede outputs. Spec: '
        'docs/superpowers/specs/2026-05-10-dream-bias-design.md '
        '(3 dimensions i succeskriterier). Beslutning: keep, retune '
        'thresholds/multipliers, eller plan Phase 2 (hybrid output + '
        '4 deferred plug-ins).'
    ),
    delay_minutes=30 * 24 * 60,
    source='dream-bias-phase1-deploy',
)
print(result)
"
```
Expected: a dict with `task_id` and `run_at` 30 days out.

- [ ] **Step 2: Capture task ID in baseline doc**

Append to `docs/superpowers/notes/2026-05-10-dream-bias-day1.md`:

```markdown

## 30-day review scheduled

- Task ID: <task_id from step 1>
- Fires: <run_at timestamp>
- Source: `dream-bias-phase1-deploy`
- Focus: "Dream Bias Phase 1 — 30-dages review..."
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/notes/2026-05-10-dream-bias-day1.md
git commit -m "docs(dream-bias): schedule 30-day review reminder"
```

---

## Phase 1 done

All 12 tasks complete = Phase 1 deployed and observation scheduled.

**Out of scope for this plan (Phase 2 work):**
- Hybrid output format (semantic embedding for attention + structured for thresholds)
- Layered corpus (two-pass distillation with chronicle-context grounding)
- 4 deferred plug-in sites: `friction_with_user` → rupture-repair, `inner_dissent` → council, `relational_warmth` → attachment, `friction_tolerance` → idle-minutes, `commitment_courage` → decision-dedup
- Per-key kill-switch
- `dream_bias_history` table for long-term observation
- Visible-lane plug-ins

When the 30-day review fires, evaluate against the 3 success-criteria dimensions in the spec and decide what Phase 2 looks like.
