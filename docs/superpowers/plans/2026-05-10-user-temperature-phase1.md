---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag 10 — User Temperature Field, Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jarvis sense the un-articulated emotional field beneath Bjørn's words via a two-stream temperature engine (structural per-message + LLM 4h cadence), surface it through heartbeat and adjust visible-lane response style.

**Architecture:** Structural stream computes 6 z-scored signals per user message. LLM stream runs every 4h or on >0.4 valens/arousal shift via `quality_daemon_llm_call`. Streams combine deterministically — on conflict (>0.6 distance or texture mismatch), structural primary, LLM exposed as secondary. Single-row-per-workspace `user_temperature_active` table. Two consumers: heartbeat injection (Site 1) + response-style modifiers in visible-lane (Site 4). Existing `build_unconscious_temperature_hint()` interface preserved; internals replaced.

**Tech Stack:** Python 3.11, SQLite, threading-based daemon, eventbus, `quality_daemon_llm_call` (deepseek-v4-flash).

**Spec:** `docs/superpowers/specs/2026-05-10-user-temperature-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/user_temperature_engine.py` | Pure-logic engine: 2 streams + combine + heartbeat formatter + response-style API |
| `core/runtime/db_user_temperature.py` | DB helpers (UPSERT, get raw, trigger flag, baseline storage) |
| `core/services/user_temperature_runtime.py` | Daemon: 60s trigger-check + 4h forced cycle, per-workspace lock |
| `tests/services/test_user_temperature_engine.py` | Engine unit tests (signals, validation, combine, formatter) |
| `tests/services/test_user_temperature_runtime.py` | Daemon idempotency + lock-contention tests |
| `tests/runtime/test_user_temperature_migration.py` | Schema invariants |
| `tests/runtime/test_db_user_temperature.py` | DB helper tests |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | 8 new flags |
| `core/eventbus/events.py` | Add `cognitive_temperature` family |
| `core/runtime/db.py` | New `_ensure_user_temperature_active_table()` called from `init_db()` |
| `core/services/unconscious_temperature_field.py` | Replace internals; preserve `build_unconscious_temperature_hint()` + `build_unconscious_temperature_field_surface()` signatures |
| `core/services/chat_sessions.py` | Hook structural-stream call after user-message persistence (fire-and-forget) |
| `core/services/prompt_contract.py` | Site 1: inject heartbeat formatter output after dream_bias section |
| `core/services/visible_runs.py` | Site 4: call `get_response_style_modifiers()` and inject as system-prompt hint |
| `apps/api/jarvis_api/app.py` | Start/stop `user_temperature_runtime` daemon in lifespan |
| `scripts/smoke_test_startup.py` | Verify table + engine importable |

---

## Spec deltas confirmed during planning

Five open questions resolved:

1. **Baseline storage location** — same `user_temperature_active` row. Adds 4 fields (`baseline_message_count`, `baseline_built_at`, plus baseline-derived stats stored in a JSON column `baseline_stats_json`). Simpler than separate table, lighter migration.

2. **Insertion path for structural-stream trigger** — hook into `core/services/chat_sessions.py::append_chat_message()` after the existing `text_resonance.resonate(...)` fire-and-forget call. Same pattern: try/except, never break chat persistence. Only fires when `normalized_role == "user"`.

3. **Daemon launch order** — start `user_temperature_runtime` in `apps/api/jarvis_api/app.py` lifespan, immediately after `start_forgetting_runtime` (line ~183). Independent of other daemons. No init-order dependency since baseline reads from `chat_messages` (already populated by chat traffic).

4. **`response_delay` edge cases** — cap delay at 60 minutes. Gaps > 60 min are likely session boundaries (sleep, distraction), not "delayed response". Implementation: `if delay > 3600: return None` (treat as "no signal" rather than "very negative").

5. **`hour_of_day_offset` weighting** — keep set-membership against typical hours (top 25% peak hours, set-comparison). Phase 1 simplification. If 30-day data shows step-function is too coarse, upgrade to gaussian distance from peak in Phase 2.

---

## Task 1: Settings flags + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, add right after the `dream_bias_*` block (or wherever the most recent flags live; place adjacent to `dream_bias_max_response_tokens`):

```python
    # ── User temperature field (Lag 10 — added 2026-05-10) ─────────────
    # Master kill-switch for FIELD APPLICATION. When False:
    # - Site 1 (heartbeat) renders nothing
    # - Site 4 (response-style) returns default modifiers
    # - Engine still computes struct_* on user msg (observability)
    # - LLM stream skips cycles
    user_temperature_enabled: bool = True
    # LLM stream cadence between forced cycles. Also responds to
    # significant-shift triggers from structural stream.
    user_temperature_llm_cadence_hours: int = 4
    # Lookback window for the LLM corpus (last N user messages).
    user_temperature_llm_corpus_messages: int = 30
    # Days for rolling baseline computation (mean/stdev of message
    # length, response delay, typical hours).
    user_temperature_baseline_days: int = 30
    # Minimum baseline messages before z-scores activate. Below this,
    # struct stream returns confidence=0 (graceful degradation).
    user_temperature_baseline_min_messages: int = 30
    # How often to rebuild baseline (hours).
    user_temperature_baseline_refresh_hours: int = 24
    # Threshold for "significant shift" that triggers LLM stream.
    user_temperature_shift_threshold: float = 0.4
    # LLM call budget (max response tokens).
    user_temperature_llm_max_response_tokens: int = 300
```

- [ ] **Step 2: Wire defaults into load_settings**

In `core/runtime/settings.py`, find the `load_settings` function and add these 8 lines after the `dream_bias_*` block:

```python
        user_temperature_enabled=bool(
            data.get("user_temperature_enabled", defaults.user_temperature_enabled)
        ),
        user_temperature_llm_cadence_hours=int(
            data.get("user_temperature_llm_cadence_hours", defaults.user_temperature_llm_cadence_hours)
        ),
        user_temperature_llm_corpus_messages=int(
            data.get("user_temperature_llm_corpus_messages", defaults.user_temperature_llm_corpus_messages)
        ),
        user_temperature_baseline_days=int(
            data.get("user_temperature_baseline_days", defaults.user_temperature_baseline_days)
        ),
        user_temperature_baseline_min_messages=int(
            data.get("user_temperature_baseline_min_messages", defaults.user_temperature_baseline_min_messages)
        ),
        user_temperature_baseline_refresh_hours=int(
            data.get("user_temperature_baseline_refresh_hours", defaults.user_temperature_baseline_refresh_hours)
        ),
        user_temperature_shift_threshold=float(
            data.get("user_temperature_shift_threshold", defaults.user_temperature_shift_threshold)
        ),
        user_temperature_llm_max_response_tokens=int(
            data.get("user_temperature_llm_max_response_tokens", defaults.user_temperature_llm_max_response_tokens)
        ),
```

- [ ] **Step 3: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES` (next to `cognitive_dream_bias`):

```python
    "cognitive_temperature",  # user-temperature field updates (added 2026-05-10)
```

- [ ] **Step 4: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
s = RuntimeSettings()
assert s.user_temperature_enabled is True
assert s.user_temperature_llm_cadence_hours == 4
assert s.user_temperature_baseline_days == 30
assert s.user_temperature_shift_threshold == 0.4
assert 'cognitive_temperature' in ALLOWED_EVENT_FAMILIES
loaded = load_settings()
assert loaded.user_temperature_enabled is True
print('ok')
"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(temperature): settings flags + cognitive_temperature event family"
```

---

## Task 2: DB migration — `user_temperature_active` table

**Files:**
- Modify: `core/runtime/db.py`
- Create: `tests/runtime/test_user_temperature_migration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_user_temperature_migration.py`:

```python
"""Schema migration for user_temperature_active (Lag 10 Phase 1)."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import _ensure_user_temperature_active_table


def test_table_created() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_temperature_active'"
    ).fetchone()
    assert row is not None


def test_table_has_expected_columns() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(user_temperature_active)").fetchall()}
    expected = {
        "field_id", "workspace_id",
        # Final field
        "field_valens", "field_arousal", "field_texture",
        "field_intensity", "field_conflict",
        # Structural stream
        "struct_valens", "struct_arousal", "struct_texture",
        "struct_confidence", "struct_signals_json", "last_structural_at",
        # LLM stream
        "llm_valens", "llm_arousal", "llm_texture",
        "llm_confidence", "llm_rationale", "last_llm_at",
        "llm_trigger_pending",
        # Baseline metadata
        "baseline_message_count", "baseline_built_at", "baseline_stats_json",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_workspace_id_is_unique() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    conn.execute(
        "INSERT INTO user_temperature_active (field_id, workspace_id, last_structural_at, "
        "created_at, updated_at) VALUES ('a', 'default', 'now', 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO user_temperature_active (field_id, workspace_id, last_structural_at, "
            "created_at, updated_at) VALUES ('b', 'default', 'now', 'now', 'now')"
        )


def test_table_creation_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    _ensure_user_temperature_active_table(conn)  # must not raise
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_temperature_active'"
    ).fetchone()
    assert row is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/runtime/test_user_temperature_migration.py -v
```
Expected: 4 tests fail with import error on `_ensure_user_temperature_active_table`.

- [ ] **Step 3: Add migration function to db.py**

In `core/runtime/db.py`, find `_ensure_dream_bias_active_table` (added earlier in 2026-05-10) and add this immediately after it:

```python
def _ensure_user_temperature_active_table(conn: sqlite3.Connection) -> None:
    """Create user_temperature_active table for Lag 10 (added 2026-05-10).

    Single row per workspace (UNIQUE constraint). Two streams stored side-
    by-side: structural (always populated) + LLM (nullable). Final field_*
    columns are the combined output consumers read.

    Baseline statistics live as JSON in baseline_stats_json (mean, stdev,
    typical hours). Refreshed every 24h.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_temperature_active (
            field_id              TEXT PRIMARY KEY,
            workspace_id          TEXT NOT NULL UNIQUE,

            -- Final field (consumers read these)
            field_valens          REAL NOT NULL DEFAULT 0.0,
            field_arousal         REAL NOT NULL DEFAULT 0.0,
            field_texture         TEXT NOT NULL DEFAULT 'cool',
            field_intensity       REAL NOT NULL DEFAULT 0.0,
            field_conflict        INTEGER NOT NULL DEFAULT 0,

            -- Structural stream (always populated)
            struct_valens         REAL NOT NULL DEFAULT 0.0,
            struct_arousal        REAL NOT NULL DEFAULT 0.0,
            struct_texture        TEXT NOT NULL DEFAULT 'cool',
            struct_confidence     REAL NOT NULL DEFAULT 0.0,
            struct_signals_json   TEXT NOT NULL DEFAULT '{}',
            last_structural_at    TEXT NOT NULL,

            -- LLM stream (nullable; populated every 4h or on trigger)
            llm_valens            REAL,
            llm_arousal           REAL,
            llm_texture           TEXT,
            llm_confidence        REAL,
            llm_rationale         TEXT NOT NULL DEFAULT '',
            last_llm_at           TEXT,
            llm_trigger_pending   INTEGER NOT NULL DEFAULT 0,

            -- Baseline metadata
            baseline_message_count INTEGER NOT NULL DEFAULT 0,
            baseline_built_at     TEXT,
            baseline_stats_json   TEXT NOT NULL DEFAULT '{}',

            created_at            TEXT NOT NULL,
            updated_at            TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_temperature_workspace "
        "ON user_temperature_active(workspace_id)"
    )
```

- [ ] **Step 4: Wire into init_db**

In `core/runtime/db.py`, find where `_ensure_dream_bias_active_table(conn)` is called and add `_ensure_user_temperature_active_table(conn)` immediately after:

```python
        _ensure_dream_bias_active_table(conn)
        _ensure_user_temperature_active_table(conn)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/runtime/test_user_temperature_migration.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_user_temperature_migration.py
git commit -m "feat(temperature): user_temperature_active schema with two-stream + baseline"
```

---

## Task 3: DB helpers — `db_user_temperature.py`

**Files:**
- Create: `core/runtime/db_user_temperature.py`
- Create: `tests/runtime/test_db_user_temperature.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/runtime/test_db_user_temperature.py`:

```python
"""Tests for db_user_temperature helpers."""
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


def test_upsert_active_field_creates_new(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={"length_z_score": 0.1, "burst_density": 0.2},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "2026-05-10T00:00:00Z", "ready": True},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row is not None
    assert row["struct_texture"] == "warm"
    assert row["field_valens"] == 0.3


def test_upsert_active_field_updates_existing(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    # First insert
    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )
    # Update
    upsert_active_field(
        workspace_id="default",
        struct={"valens": -0.5, "arousal": 0.7, "texture": "frustrated", "confidence": 0.8},
        struct_signals={},
        llm={"valens": -0.4, "arousal": 0.6, "texture": "frustrated",
             "confidence": 0.7, "rationale": "abrupt"},
        combined={
            "field_valens": -0.45, "field_arousal": 0.65, "field_texture": "frustrated",
            "field_intensity": 0.95, "field_conflict": False,
        },
        baseline={"message_count": 51, "built_at": "now", "ready": True},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row["struct_texture"] == "frustrated"
    assert row["field_valens"] == -0.45
    assert row["llm_rationale"] == "abrupt"


def test_get_active_field_raw_returns_none_for_unknown(fresh_db):
    from core.runtime.db_user_temperature import get_active_field_raw
    assert get_active_field_raw(workspace_id="nonexistent") is None


def test_set_and_consume_trigger_pending(fresh_db):
    from core.runtime.db_user_temperature import (
        upsert_active_field, set_llm_trigger_pending, consume_llm_trigger_pending,
    )

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.0, "field_arousal": 0.0, "field_texture": "cool",
            "field_intensity": 0.0, "field_conflict": False,
        },
        baseline={"message_count": 0, "built_at": "", "ready": False},
    )
    # Initially not pending
    assert consume_llm_trigger_pending(workspace_id="default") is False
    # Set then consume
    set_llm_trigger_pending(workspace_id="default")
    assert consume_llm_trigger_pending(workspace_id="default") is True
    # After consume, no longer pending
    assert consume_llm_trigger_pending(workspace_id="default") is False


def test_signals_json_round_trips(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    signals = {
        "length_z_score": 0.5,
        "response_delay_z_score": -0.3,
        "punctuation_density": 0.1,
        "caps_density": 0.0,
        "hour_of_day_offset": 0.2,
        "burst_density": 0.4,
    }
    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0},
        struct_signals=signals,
        llm=None,
        combined={
            "field_valens": 0.0, "field_arousal": 0.0, "field_texture": "cool",
            "field_intensity": 0.0, "field_conflict": False,
        },
        baseline={"message_count": 0, "built_at": "", "ready": False},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row["struct_signals"] == signals
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/runtime/test_db_user_temperature.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the helper module**

Create `core/runtime/db_user_temperature.py`:

```python
"""DB helpers for user_temperature_active (Lag 10 user temperature field).

Single-row-per-workspace UPSERT. Read API bypasses kill-switch — the
engine's get_active_field() wraps this with the enabled-check.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def upsert_active_field(
    *,
    workspace_id: str,
    struct: dict[str, Any],
    struct_signals: dict[str, float],
    llm: dict[str, Any] | None,
    combined: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """INSERT or UPDATE the single active field row for a workspace."""
    now = _now()
    field_id = f"tf_{workspace_id}_{uuid.uuid4().hex[:12]}"

    llm_valens = llm["valens"] if llm else None
    llm_arousal = llm["arousal"] if llm else None
    llm_texture = llm["texture"] if llm else None
    llm_confidence = llm["confidence"] if llm else None
    llm_rationale = (llm["rationale"] if llm else "") or ""
    last_llm_at = now if llm else None

    with connect() as conn:
        # Try update first
        cur = conn.execute(
            "UPDATE user_temperature_active SET "
            "  field_valens = ?, field_arousal = ?, field_texture = ?, "
            "  field_intensity = ?, field_conflict = ?, "
            "  struct_valens = ?, struct_arousal = ?, struct_texture = ?, "
            "  struct_confidence = ?, struct_signals_json = ?, last_structural_at = ?, "
            "  llm_valens = COALESCE(?, llm_valens), "
            "  llm_arousal = COALESCE(?, llm_arousal), "
            "  llm_texture = COALESCE(?, llm_texture), "
            "  llm_confidence = COALESCE(?, llm_confidence), "
            "  llm_rationale = CASE WHEN ? != '' THEN ? ELSE llm_rationale END, "
            "  last_llm_at = COALESCE(?, last_llm_at), "
            "  baseline_message_count = ?, baseline_built_at = ?, "
            "  baseline_stats_json = ?, updated_at = ? "
            "WHERE workspace_id = ?",
            (
                float(combined["field_valens"]), float(combined["field_arousal"]),
                str(combined["field_texture"]), float(combined["field_intensity"]),
                int(bool(combined["field_conflict"])),
                float(struct["valens"]), float(struct["arousal"]),
                str(struct["texture"]), float(struct["confidence"]),
                json.dumps(struct_signals), now,
                llm_valens, llm_arousal, llm_texture, llm_confidence,
                llm_rationale, llm_rationale, last_llm_at,
                int(baseline.get("message_count", 0)),
                str(baseline.get("built_at") or ""),
                json.dumps({k: v for k, v in baseline.items() if k != "ready"}),
                now, workspace_id,
            ),
        )
        if cur.rowcount == 0:
            # Insert new row
            conn.execute(
                "INSERT INTO user_temperature_active "
                "(field_id, workspace_id, "
                "field_valens, field_arousal, field_texture, "
                "field_intensity, field_conflict, "
                "struct_valens, struct_arousal, struct_texture, "
                "struct_confidence, struct_signals_json, last_structural_at, "
                "llm_valens, llm_arousal, llm_texture, llm_confidence, "
                "llm_rationale, last_llm_at, llm_trigger_pending, "
                "baseline_message_count, baseline_built_at, baseline_stats_json, "
                "created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "        ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)",
                (
                    field_id, workspace_id,
                    float(combined["field_valens"]), float(combined["field_arousal"]),
                    str(combined["field_texture"]), float(combined["field_intensity"]),
                    int(bool(combined["field_conflict"])),
                    float(struct["valens"]), float(struct["arousal"]),
                    str(struct["texture"]), float(struct["confidence"]),
                    json.dumps(struct_signals), now,
                    llm_valens, llm_arousal, llm_texture, llm_confidence,
                    llm_rationale, last_llm_at,
                    int(baseline.get("message_count", 0)),
                    str(baseline.get("built_at") or ""),
                    json.dumps({k: v for k, v in baseline.items() if k != "ready"}),
                    now, now,
                ),
            )
    return {"workspace_id": workspace_id, "updated_at": now}


def get_active_field_raw(*, workspace_id: str) -> dict[str, Any] | None:
    """Read the active field row, parsed JSON columns expanded.

    Does NOT honor the user_temperature_enabled kill-switch — engine wraps.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT field_id, workspace_id, "
            "  field_valens, field_arousal, field_texture, "
            "  field_intensity, field_conflict, "
            "  struct_valens, struct_arousal, struct_texture, "
            "  struct_confidence, struct_signals_json, last_structural_at, "
            "  llm_valens, llm_arousal, llm_texture, llm_confidence, "
            "  llm_rationale, last_llm_at, llm_trigger_pending, "
            "  baseline_message_count, baseline_built_at, baseline_stats_json, "
            "  created_at, updated_at "
            "FROM user_temperature_active WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "field_id": row[0],
        "workspace_id": row[1],
        "field_valens": float(row[2] or 0.0),
        "field_arousal": float(row[3] or 0.0),
        "field_texture": str(row[4] or "cool"),
        "field_intensity": float(row[5] or 0.0),
        "field_conflict": bool(row[6]),
        "struct_valens": float(row[7] or 0.0),
        "struct_arousal": float(row[8] or 0.0),
        "struct_texture": str(row[9] or "cool"),
        "struct_confidence": float(row[10] or 0.0),
        "struct_signals": json.loads(row[11] or "{}"),
        "last_structural_at": str(row[12] or ""),
        "llm_valens": (float(row[13]) if row[13] is not None else None),
        "llm_arousal": (float(row[14]) if row[14] is not None else None),
        "llm_texture": (str(row[15]) if row[15] is not None else None),
        "llm_confidence": (float(row[16]) if row[16] is not None else None),
        "llm_rationale": str(row[17] or ""),
        "last_llm_at": (str(row[18]) if row[18] else None),
        "llm_trigger_pending": bool(row[19]),
        "baseline_message_count": int(row[20] or 0),
        "baseline_built_at": str(row[21] or ""),
        "baseline_stats": json.loads(row[22] or "{}"),
        "created_at": str(row[23] or ""),
        "updated_at": str(row[24] or ""),
    }


def set_llm_trigger_pending(*, workspace_id: str) -> bool:
    """Mark LLM stream as needing a refresh on next daemon cycle."""
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE user_temperature_active SET "
            "  llm_trigger_pending = 1, updated_at = ? "
            "WHERE workspace_id = ?",
            (now, workspace_id),
        )
        return cur.rowcount > 0


def consume_llm_trigger_pending(*, workspace_id: str) -> bool:
    """Read+clear the trigger flag atomically. Returns True if was pending."""
    now = _now()
    with connect() as conn:
        row = conn.execute(
            "SELECT llm_trigger_pending FROM user_temperature_active "
            "WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if not row or not row[0]:
            return False
        conn.execute(
            "UPDATE user_temperature_active SET "
            "  llm_trigger_pending = 0, updated_at = ? "
            "WHERE workspace_id = ?",
            (now, workspace_id),
        )
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/runtime/test_db_user_temperature.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db_user_temperature.py tests/runtime/test_db_user_temperature.py
git commit -m "feat(temperature): db_user_temperature.py — UPSERT, get raw, trigger flag helpers"
```

---

## Task 4: `user_temperature_engine.py` — pure logic

**Files:**
- Create: `core/services/user_temperature_engine.py`
- Create: `tests/services/test_user_temperature_engine.py`

This task is the largest. Tests cover signals, validation, combine, formatter, response-style API.

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_user_temperature_engine.py`:

```python
"""Tests for user_temperature_engine — pure logic."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


# ── Signal computation ────────────────────────────────────────────────


def test_punct_density_basic():
    from core.services.user_temperature_engine import _punct_density
    assert _punct_density("hello!") == pytest.approx(1 / 6, abs=0.01)
    assert _punct_density("just text") == 0.0
    assert _punct_density("") == 0.0


def test_caps_density_basic():
    from core.services.user_temperature_engine import _caps_density
    assert _caps_density("HELLO") == 1.0
    assert _caps_density("hello") == 0.0
    assert _caps_density("Hello") == pytest.approx(1 / 5, abs=0.01)
    assert _caps_density("") == 0.0
    assert _caps_density("123!?") == 0.0


# ── Field mapping ──────────────────────────────────────────────────────


def test_map_signals_to_field_neutral_input():
    from core.services.user_temperature_engine import map_signals_to_field
    signals = {
        "length_z_score": 0.0, "response_delay_z_score": 0.0,
        "punctuation_density": 0.0, "caps_density": 0.0,
        "hour_of_day_offset": 0.0, "burst_density": 0.0,
    }
    out = map_signals_to_field(signals)
    assert out["valens"] == 0.0
    assert out["arousal"] == 0.0
    assert out["texture"] == "cool"  # neutral both → cool


def test_map_signals_high_energy_negative_valens():
    """Lots of punctuation + caps + bursting + slow response = frustrated."""
    from core.services.user_temperature_engine import map_signals_to_field
    signals = {
        "length_z_score": -0.5,         # short messages → negative valens
        "response_delay_z_score": 0.5,  # slow → negative valens
        "punctuation_density": 0.3,     # high
        "caps_density": 0.3,            # high
        "hour_of_day_offset": 0.0,
        "burst_density": 0.5,           # high → high arousal
    }
    out = map_signals_to_field(signals)
    assert out["valens"] < 0
    assert out["arousal"] > 0.4
    assert out["texture"] == "frustrated"


def test_texture_from_circumplex_quadrants():
    from core.services.user_temperature_engine import _texture_from_circumplex
    # High arousal + positive valens → playful
    assert _texture_from_circumplex(0.5, 0.6) == "playful"
    # High arousal + negative valens → frustrated
    assert _texture_from_circumplex(-0.5, 0.6) == "frustrated"
    # High arousal + neutral valens → alert
    assert _texture_from_circumplex(0.0, 0.6) == "alert"
    # Mid arousal + positive → warm
    assert _texture_from_circumplex(0.5, 0.0) == "warm"
    # Mid arousal + negative → tender
    assert _texture_from_circumplex(-0.5, 0.0) == "tender"
    # Low arousal + very negative → withdrawn
    assert _texture_from_circumplex(-0.7, -0.5) == "withdrawn"
    # Low arousal + neutral → cool
    assert _texture_from_circumplex(0.0, -0.4) == "cool"


# ── LLM validation ─────────────────────────────────────────────────────


def test_validate_llm_output_accepts_clean():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 0.3, "arousal": 0.5, "texture": "playful",
        "confidence": 0.7, "rationale": "Bjørn er i flow",
    })
    assert out is not None
    assert out["valens"] == 0.3
    assert out["texture"] == "playful"


def test_validate_llm_output_drops_unknown_texture():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 0.3, "arousal": 0.5, "texture": "totally_made_up",
        "confidence": 0.7,
    })
    assert out is None  # unknown texture → reject entire output


def test_validate_llm_output_clamps_values():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 5.0, "arousal": -3.0, "texture": "warm",
        "confidence": 2.0,
    })
    assert out["valens"] == 1.0
    assert out["arousal"] == -1.0
    # confidence falls back to 0.5 when out of range
    assert out["confidence"] == 0.5


def test_validate_llm_output_rejects_missing_valens():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "arousal": 0.5, "texture": "warm", "confidence": 0.5,
    })
    assert out is None


# ── Combine ────────────────────────────────────────────────────────────


def test_combine_streams_no_llm_returns_struct():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    out = combine_streams(struct=struct, llm=None)
    assert out["field_valens"] == 0.3
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is False


def test_combine_streams_low_llm_confidence_returns_struct():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": -0.8, "arousal": 0.6, "texture": "frustrated",
           "confidence": 0.1, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    assert out["field_texture"] == "warm"  # struct wins
    assert out["field_conflict"] is False  # low LLM confidence → not counted


def test_combine_streams_agreement_averages_valens_arousal():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": 0.5, "arousal": 0.4, "texture": "warm",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    # valens averaged: (0.3 + 0.5) / 2 = 0.4
    assert out["field_valens"] == pytest.approx(0.4, abs=0.01)
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is False


def test_combine_streams_conflict_keeps_struct_primary():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": -0.5, "arousal": 0.4, "texture": "frustrated",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    # Conflict: valens distance 0.8 > 0.6 → struct primary
    assert out["field_valens"] == 0.3
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is True


def test_combine_streams_texture_mismatch_is_conflict():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": 0.4, "arousal": 0.4, "texture": "playful",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    # Valens close (0.1 distance), but texture mismatch → conflict
    assert out["field_conflict"] is True
    assert out["field_texture"] == "warm"  # struct primary


# ── Shift detection ────────────────────────────────────────────────────


def test_significant_shift_no_prior_returns_false():
    from core.services.user_temperature_engine import _is_significant_shift
    new = {"valens": 0.5, "arousal": 0.5, "texture": "warm"}
    assert _is_significant_shift(None, new) is False


def test_significant_shift_valens_above_threshold():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.0, "struct_arousal": 0.0, "struct_texture": "cool"}
    new = {"valens": 0.5, "arousal": 0.0, "texture": "cool"}
    assert _is_significant_shift(prior, new) is True


def test_significant_shift_texture_change():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.1, "struct_arousal": 0.1, "struct_texture": "cool"}
    new = {"valens": 0.1, "arousal": 0.1, "texture": "warm"}
    assert _is_significant_shift(prior, new) is True


def test_significant_shift_below_threshold():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.1, "struct_arousal": 0.1, "struct_texture": "cool"}
    new = {"valens": 0.3, "arousal": 0.2, "texture": "cool"}
    assert _is_significant_shift(prior, new) is False


# ── Public read ────────────────────────────────────────────────────────


def test_get_active_field_returns_none_when_disabled(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_active_field

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = False

    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    assert get_active_field(workspace_id="default") is None


def test_get_active_field_returns_data_when_enabled(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_active_field

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True

    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    field = get_active_field(workspace_id="default")
    assert field is not None
    assert field["field_valens"] == 0.3
    assert field["field_texture"] == "warm"


# ── Heartbeat formatter ────────────────────────────────────────────────


def test_heartbeat_formatter_returns_empty_when_no_field(fresh_db, monkeypatch):
    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat
    assert format_temperature_field_for_heartbeat(workspace_id="default") == ""


def test_heartbeat_formatter_skips_low_intensity(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.05, "arousal": 0.05, "texture": "cool", "confidence": 0.05},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.05, "field_arousal": 0.05, "field_texture": "cool",
            "field_intensity": 0.10, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    # Below 0.15 floor
    assert format_temperature_field_for_heartbeat(workspace_id="default") == ""


def test_heartbeat_formatter_renders_active_field(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.4, "arousal": 0.5, "texture": "warm", "confidence": 0.6},
        struct_signals={},
        llm={"valens": 0.4, "arousal": 0.5, "texture": "warm",
             "confidence": 0.7, "rationale": "Bjørn er engageret"},
        combined={
            "field_valens": 0.4, "field_arousal": 0.5, "field_texture": "warm",
            "field_intensity": 0.9, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_temperature_field_for_heartbeat(workspace_id="default")
    assert "user_temperature_field" in out
    assert "warm" in out
    assert "engageret" in out  # LLM rationale


def test_heartbeat_formatter_shows_conflict(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm={"valens": -0.5, "arousal": 0.4, "texture": "frustrated",
             "confidence": 0.7, "rationale": "x"},
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": True,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_temperature_field_for_heartbeat(workspace_id="default")
    assert "field_conflict" in out
    assert "frustrated" in out  # LLM secondary exposed


# ── Response-style modifiers ────────────────────────────────────────────


def test_response_style_returns_default_when_no_field(fresh_db, monkeypatch):
    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.user_temperature_engine import get_response_style_modifiers
    mods = get_response_style_modifiers(workspace_id="default")
    assert mods == {
        "preferred_length": "normal",
        "warmth": "neutral",
        "pace": "normal",
    }


def test_response_style_tender_field_yields_short_gentle_patient(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": -0.4, "arousal": -0.2, "texture": "tender", "confidence": 0.6},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": -0.4, "field_arousal": -0.2, "field_texture": "tender",
            "field_intensity": 0.6, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    assert mods["preferred_length"] == "short"
    assert mods["warmth"] == "gentle"
    assert mods["pace"] == "patient"


def test_response_style_playful_field_yields_warm_quick(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.6, "arousal": 0.6, "texture": "playful", "confidence": 0.7},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.6, "field_arousal": 0.6, "field_texture": "playful",
            "field_intensity": 0.9, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    assert mods["warmth"] == "warm"
    assert mods["pace"] == "quick"


def test_response_style_low_intensity_returns_default(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.05, "arousal": 0.05, "texture": "cool", "confidence": 0.05},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.05, "field_arousal": 0.05, "field_texture": "cool",
            "field_intensity": 0.1, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    # intensity 0.1 < 0.2 floor → defaults
    assert mods["warmth"] == "neutral"
    assert mods["pace"] == "normal"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_user_temperature_engine.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the engine**

Create `core/services/user_temperature_engine.py`:

```python
"""User temperature field engine — Lag 10 two-stream pipeline.

Pure-logic. No threading. The runtime daemon
(user_temperature_runtime.py) wraps this with locks + cadence loop.
The structural stream is invoked synchronously per user message from
chat_sessions.append_chat_message().

Two streams:
  - structural: per-message, 6 z-scored signals → valens/arousal/texture
  - LLM: 4h cadence + on-trigger, deepseek-v4-flash via quality_daemon_llm_call

Combination: agreement averages valens/arousal; conflict (>0.6 distance
or texture mismatch) → structural primary, LLM exposed as secondary.

Backwards compat: legacy build_unconscious_temperature_hint() in
unconscious_temperature_field.py delegates here.
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.db_user_temperature import (
    consume_llm_trigger_pending,
    get_active_field_raw,
    set_llm_trigger_pending,
    upsert_active_field,
)
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


# ── Locked vocabulary ─────────────────────────────────────────────────

TEXTURE_VOCAB: frozenset[str] = frozenset({
    "warm", "cool", "restless", "tender", "frustrated", "playful",
    "withdrawn", "alert",
})

# Site 1 (heartbeat) intensity floor.
_HEARTBEAT_INTENSITY_FLOOR = 0.15
# Site 4 (response-style) intensity floor.
_RESPONSE_STYLE_INTENSITY_FLOOR = 0.2

# Conflict thresholds.
_CONFLICT_VALENS_DISTANCE = 0.6
_CONFLICT_AROUSAL_DISTANCE = 0.6


# ── Helpers ────────────────────────────────────────────────────────────

def _coerce_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


# ── Raw signal computation ────────────────────────────────────────────


def _punct_density(message: str) -> float:
    if not message:
        return 0.0
    punct = sum(1 for c in message if c in "!?…")
    return min(1.0, punct / max(1, len(message)))


def _caps_density(message: str) -> float:
    letters = [c for c in message if c.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters)


def _burst_density(message_at: str) -> float:
    """User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0."""
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 0.0
    cutoff = (at - timedelta(seconds=300)).isoformat().replace("+00:00", "Z")
    cutoff_end = at.isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            n = c.execute(
                "SELECT COUNT(*) FROM chat_messages "
                "WHERE role='user' AND created_at >= ? AND created_at <= ?",
                (cutoff, cutoff_end),
            ).fetchone()[0]
        return min(1.0, int(n) / 5.0)
    except Exception:
        return 0.0


def _delay_since_last_jarvis(message_at: str) -> float | None:
    """Seconds since the prior assistant message. None if no prior, or > 60min."""
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    try:
        with connect() as c:
            row = c.execute(
                "SELECT created_at FROM chat_messages "
                "WHERE role='assistant' AND created_at < ? "
                "ORDER BY created_at DESC LIMIT 1",
                (message_at,),
            ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    try:
        prior = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    delta_seconds = (at - prior).total_seconds()
    if delta_seconds < 0 or delta_seconds > 3600:  # cap at 60 min
        return None
    return delta_seconds


def _parse_hour(message_at: str) -> int:
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
        return at.hour
    except (ValueError, TypeError):
        return 12  # default to noon if unparseable


def _compute_raw_signals(*, message: str, message_at: str, baseline: dict) -> dict:
    """Map a single message + baseline to 6 normalized signals."""
    if not baseline.get("ready"):
        return {
            "length_z_score": 0.0,
            "response_delay_z_score": 0.0,
            "punctuation_density": _punct_density(message),
            "caps_density": _caps_density(message),
            "hour_of_day_offset": 0.0,
            "burst_density": _burst_density(message_at),
        }

    char_count = len(message)
    length_z = (char_count - baseline["char_count_mean"]) / max(baseline["char_count_stdev"], 1)
    length_z = max(-3.0, min(3.0, length_z)) / 3.0

    delay = _delay_since_last_jarvis(message_at)
    if delay is None:
        response_z = 0.0
    else:
        response_z = (delay - baseline["response_delay_mean"]) / max(baseline["response_delay_stdev"], 1)
        response_z = max(-3.0, min(3.0, response_z)) / 3.0

    hour = _parse_hour(message_at)
    typical_hours = set(baseline.get("typical_hours") or [])
    if hour in typical_hours:
        hour_offset = 0.0
    elif typical_hours:
        nearest = min(abs(hour - h) for h in typical_hours)
        hour_offset = min(1.0, nearest / 6.0)
    else:
        hour_offset = 0.0

    return {
        "length_z_score": length_z,
        "response_delay_z_score": response_z,
        "punctuation_density": _punct_density(message),
        "caps_density": _caps_density(message),
        "hour_of_day_offset": hour_offset,
        "burst_density": _burst_density(message_at),
    }


# ── Field mapping ──────────────────────────────────────────────────────


def map_signals_to_field(signals: dict) -> dict:
    """Pure function: 6 raw signals → valens/arousal/texture/confidence."""
    arousal = (
        signals.get("punctuation_density", 0.0) * 0.3
        + signals.get("caps_density", 0.0) * 0.2
        + signals.get("burst_density", 0.0) * 0.3
        - signals.get("response_delay_z_score", 0.0) * 0.2
    )
    valens = (
        signals.get("length_z_score", 0.0) * 0.4
        - signals.get("response_delay_z_score", 0.0) * 0.3
        - max(0.0, signals.get("hour_of_day_offset", 0.0)) * 0.3
    )
    arousal = max(-1.0, min(1.0, arousal))
    valens = max(-1.0, min(1.0, valens))
    texture = _texture_from_circumplex(valens, arousal)
    confidence = min(1.0, abs(valens) + abs(arousal))
    return {
        "valens": valens, "arousal": arousal,
        "texture": texture, "confidence": confidence,
    }


def _texture_from_circumplex(valens: float, arousal: float) -> str:
    """Pure function: (valens, arousal) → texture key."""
    if arousal > 0.4:
        if valens > 0.3:
            return "playful"
        if valens < -0.3:
            return "frustrated"
        return "alert"
    if arousal > -0.2:
        if valens > 0.3:
            return "warm"
        if valens < -0.3:
            return "tender"
        return "restless" if abs(valens) < 0.3 and arousal > 0.0 else "cool"
    # Low arousal
    if valens > 0.0:
        return "warm"
    if valens < -0.5:
        return "withdrawn"
    return "cool"


# ── LLM validation ─────────────────────────────────────────────────────


def _validate_llm_output(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    valens = _coerce_float(raw.get("valens"))
    arousal = _coerce_float(raw.get("arousal"))
    if valens is None or arousal is None:
        return None
    valens = max(-1.0, min(1.0, valens))
    arousal = max(-1.0, min(1.0, arousal))
    texture = str(raw.get("texture") or "").strip().lower()
    if texture not in TEXTURE_VOCAB:
        return None
    confidence = _coerce_float(raw.get("confidence"))
    if confidence is None or not 0.0 <= confidence <= 1.0:
        confidence = 0.5
    rationale = str(raw.get("rationale") or "").strip()[:200]
    return {
        "valens": valens, "arousal": arousal, "texture": texture,
        "confidence": confidence, "rationale": rationale,
    }


# ── Combine ────────────────────────────────────────────────────────────


def combine_streams(*, struct: dict, llm: dict | None) -> dict:
    """Deterministic merge of structural + LLM streams."""
    if llm is None or float(llm.get("confidence", 0.0)) < 0.3:
        return {
            "field_valens": struct["valens"],
            "field_arousal": struct["arousal"],
            "field_texture": struct["texture"],
            "field_intensity": min(1.0, abs(struct["valens"]) + abs(struct["arousal"])),
            "field_conflict": False,
        }
    valens_dist = abs(struct["valens"] - llm["valens"])
    arousal_dist = abs(struct["arousal"] - llm["arousal"])
    conflict = (
        valens_dist > _CONFLICT_VALENS_DISTANCE
        or arousal_dist > _CONFLICT_AROUSAL_DISTANCE
        or struct["texture"] != llm["texture"]
    )
    if conflict:
        return {
            "field_valens": struct["valens"],
            "field_arousal": struct["arousal"],
            "field_texture": struct["texture"],
            "field_intensity": min(1.0, abs(struct["valens"]) + abs(struct["arousal"])),
            "field_conflict": True,
        }
    fv = (struct["valens"] + llm["valens"]) / 2
    fa = (struct["arousal"] + llm["arousal"]) / 2
    return {
        "field_valens": fv,
        "field_arousal": fa,
        "field_texture": struct["texture"],
        "field_intensity": min(1.0, abs(fv) + abs(fa)),
        "field_conflict": False,
    }


# ── Shift detection ────────────────────────────────────────────────────


def _is_significant_shift(prior: dict | None, new: dict) -> bool:
    """Did valens/arousal shift > threshold or texture change?"""
    if prior is None:
        return False
    threshold = 0.4
    valens_shift = abs(new["valens"] - float(prior.get("struct_valens", 0.0)))
    arousal_shift = abs(new["arousal"] - float(prior.get("struct_arousal", 0.0)))
    texture_changed = new["texture"] != prior.get("struct_texture")
    return valens_shift > threshold or arousal_shift > threshold or texture_changed


# ── Baseline computation ──────────────────────────────────────────────


def _compute_baseline(*, days: int = 30) -> dict:
    """Compute rolling baseline from last N days of user messages."""
    cutoff = (_now() - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role='user' AND created_at > ? "
                "ORDER BY created_at ASC",
                (cutoff,),
            ).fetchall()
    except Exception as exc:
        logger.warning("temperature: baseline query failed: %s", exc)
        return {"ready": False, "message_count": 0, "built_at": _now_iso()}

    n = len(rows)
    if n < 30:
        return {
            "ready": False, "message_count": n,
            "built_at": _now_iso(),
        }

    char_counts = [len(str(r["content"] or "")) for r in rows]
    delays = []
    for i, r in enumerate(rows):
        d = _delay_since_last_jarvis(str(r["created_at"]))
        if d is not None:
            delays.append(d)
    hours = []
    for r in rows:
        try:
            hours.append(_parse_hour(str(r["created_at"])))
        except Exception:
            pass

    char_mean = statistics.mean(char_counts) if char_counts else 0.0
    char_stdev = statistics.stdev(char_counts) if len(char_counts) > 1 else 1.0
    delay_mean = statistics.mean(delays) if delays else 0.0
    delay_stdev = statistics.stdev(delays) if len(delays) > 1 else 1.0

    # Top 25% peak hours
    hour_counts: dict[int, int] = {}
    for h in hours:
        hour_counts[h] = hour_counts.get(h, 0) + 1
    if hour_counts:
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        top_n = max(1, len(sorted_hours) // 4)
        typical_hours = [h for h, _ in sorted_hours[:top_n]]
    else:
        typical_hours = []

    return {
        "ready": True,
        "message_count": n,
        "char_count_mean": char_mean,
        "char_count_stdev": char_stdev or 1.0,
        "response_delay_mean": delay_mean,
        "response_delay_stdev": delay_stdev or 1.0,
        "typical_hours": typical_hours,
        "built_at": _now_iso(),
    }


# ── Public read API ───────────────────────────────────────────────────


def get_active_field(*, workspace_id: str = "default") -> dict[str, Any] | None:
    """Read active field, honoring kill-switch."""
    try:
        if not load_settings().user_temperature_enabled:
            return None
    except Exception:
        pass
    return get_active_field_raw(workspace_id=workspace_id)


# ── Heartbeat formatter (Site 1) ──────────────────────────────────────


_DEFAULT_HINTS: dict[str, str] = {
    "warm":       "Brug rolig samarbejdende tone; varme bærer feltet.",
    "cool":       "Hold tonen nøgtern og klar; lav varme, høj præcision.",
    "restless":   "Kort momentum, få skridt; feltet virker rastløst.",
    "tender":     "Svar blidt og uden hård kant; feltet er sart.",
    "frustrated": "Vær verificerende, undgå gæt; tydelig irritation.",
    "playful":    "Tillad lidt leg og lethed, uden at miste retning.",
    "withdrawn":  "Hold afstand, vær til rådighed uden at presse.",
    "alert":      "Vær præcis og hurtig; brugeren er skarp og fokuseret.",
}


def format_temperature_field_for_heartbeat(*, workspace_id: str = "default") -> str:
    """Render the field as a heartbeat awareness-section block."""
    field = get_active_field(workspace_id=workspace_id)
    if not field:
        return ""
    if float(field.get("field_intensity") or 0.0) < _HEARTBEAT_INTENSITY_FLOOR:
        return ""

    valens = field["field_valens"]
    arousal = field["field_arousal"]
    texture = field["field_texture"]
    intensity = field["field_intensity"]
    conflict = field.get("field_conflict", False)

    lines = [
        "[user_temperature_field]",
        f"valens: {valens:+.2f} | arousal: {arousal:+.2f} | "
        f"texture: {texture} | intensity: {intensity:.2f}",
    ]

    if conflict:
        llm_t = field.get("llm_texture") or "?"
        struct_t = field.get("struct_texture") or "?"
        lines.append(
            f"field_conflict: true (struct: {struct_t}, llm: {llm_t}) — "
            "ambivalent felt"
        )

    rationale = str(field.get("llm_rationale") or "").strip()
    if rationale:
        lines.append(f"hint: {rationale[:160]}")
    else:
        lines.append(f"hint: {_DEFAULT_HINTS.get(texture, '')}")

    return "\n".join(lines)


# ── Response-style modifiers (Site 4) ─────────────────────────────────


def get_response_style_modifiers(*, workspace_id: str = "default") -> dict[str, str]:
    """Return response-style hints based on active temperature field.

    Always returns 3 keys with fixed-vocabulary values. Defaults to
    {normal, neutral, normal} when no field, kill-switch off, or
    intensity below threshold.
    """
    default = {
        "preferred_length": "normal",
        "warmth": "neutral",
        "pace": "normal",
    }
    try:
        field = get_active_field(workspace_id=workspace_id)
        if not field:
            return default
        if float(field.get("field_intensity") or 0.0) < _RESPONSE_STYLE_INTENSITY_FLOOR:
            return default

        valens = float(field["field_valens"])
        arousal = float(field["field_arousal"])
        texture = str(field["field_texture"])

        # preferred_length
        if texture in ("withdrawn", "tender"):
            length = "short"
        elif arousal > 0.5 and valens < 0:
            length = "short"
        elif valens > 0.4 and arousal > 0.3:
            length = "long"
        else:
            length = "normal"

        # warmth
        if texture in ("tender", "withdrawn"):
            warmth = "gentle"
        elif texture in ("warm", "playful"):
            warmth = "warm"
        else:
            warmth = "neutral"

        # pace
        if arousal > 0.5:
            pace = "quick"
        elif arousal < -0.3 or texture == "tender":
            pace = "patient"
        else:
            pace = "normal"

        return {
            "preferred_length": length,
            "warmth": warmth,
            "pace": pace,
        }
    except Exception:
        return default


# ── Surface for Mission Control (backwards compat) ────────────────────


def get_active_field_surface(
    *, workspace_id: str = "default", force_refresh: bool = False
) -> dict[str, Any]:
    """Return MC-friendly surface dict. force_refresh ignored in Phase 1."""
    field = get_active_field(workspace_id=workspace_id)
    if not field:
        return {
            "active": False,
            "enabled": True,
            "summary": "No active temperature field",
        }
    return {
        "active": True,
        "enabled": True,
        "current_field": field["field_texture"],
        "valens": field["field_valens"],
        "arousal": field["field_arousal"],
        "intensity": field["field_intensity"],
        "conflict": field["field_conflict"],
        "rationale": field.get("llm_rationale", ""),
        "summary": (
            f"{field['field_texture']} field "
            f"(valens={field['field_valens']:+.2f}, "
            f"arousal={field['field_arousal']:+.2f})"
        ),
    }


# ── Structural stream (per user message) ──────────────────────────────


def run_structural_stream(
    *, workspace_id: str, message: str, message_at: str
) -> dict[str, Any]:
    """Per-message structural pipeline. Updates struct_* + recomputes field_*.

    Reads cached LLM stream (if any), combines, UPSERTs. Sets
    llm_trigger_pending = 1 if shift detected.
    """
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    # 1. Get baseline (cached or fresh)
    prior = get_active_field_raw(workspace_id=workspace_id)
    baseline = _get_or_build_baseline(prior=prior, settings=settings)

    # 2. Compute raw signals
    signals = _compute_raw_signals(
        message=message, message_at=message_at, baseline=baseline,
    )

    # 3. Map to field
    struct_result = map_signals_to_field(signals)

    # 4. Detect shift
    shift = _is_significant_shift(prior, struct_result)

    # 5. Read cached LLM
    cached_llm = None
    if prior and prior.get("llm_texture"):
        cached_llm = {
            "valens": prior["llm_valens"],
            "arousal": prior["llm_arousal"],
            "texture": prior["llm_texture"],
            "confidence": prior["llm_confidence"] or 0.0,
            "rationale": prior.get("llm_rationale", ""),
        }

    # 6. Combine
    combined = combine_streams(struct=struct_result, llm=cached_llm)

    # 7. UPSERT
    upsert_active_field(
        workspace_id=workspace_id,
        struct=struct_result,
        struct_signals=signals,
        llm=cached_llm,
        combined=combined,
        baseline=baseline,
    )

    # 8. Trigger LLM if shift
    if shift:
        set_llm_trigger_pending(workspace_id=workspace_id)

    # 9. Publish event
    try:
        event_bus.publish(
            "cognitive_temperature.field_updated",
            {
                "workspace_id": workspace_id,
                "field_valens": combined["field_valens"],
                "field_arousal": combined["field_arousal"],
                "field_texture": combined["field_texture"],
                "field_conflict": combined["field_conflict"],
                "stream_source": "structural",
                "shift_detected": shift,
            },
        )
    except Exception as exc:
        logger.debug("temperature: publish failed: %s", exc)

    return {
        "status": "ok",
        "shift_detected": shift,
        "struct_valens": struct_result["valens"],
        "struct_arousal": struct_result["arousal"],
        "struct_texture": struct_result["texture"],
        "field_conflict": combined["field_conflict"],
    }


def _get_or_build_baseline(*, prior: dict | None, settings) -> dict:
    """Return cached baseline if fresh, else rebuild."""
    if prior and prior.get("baseline_stats"):
        cached = prior["baseline_stats"]
        built_at_str = prior.get("baseline_built_at") or ""
        try:
            built_at = datetime.fromisoformat(built_at_str.replace("Z", "+00:00"))
            age_hours = (_now() - built_at).total_seconds() / 3600.0
            if age_hours < settings.user_temperature_baseline_refresh_hours:
                cached["message_count"] = prior.get("baseline_message_count", 0)
                cached["built_at"] = built_at_str
                return cached
        except Exception:
            pass
    return _compute_baseline(days=settings.user_temperature_baseline_days)


# ── LLM stream (4h cadence + on-trigger) ──────────────────────────────


_LLM_SYSTEM_PROMPT = """\
You are reading the user's emotional temperature field — the un-articulated
state behind their words. NOT what they say, but how they feel beneath it.

You receive their last messages (24h window). Output STRICT JSON only:

{
  "valens": -1.0..+1.0,
  "arousal": -1.0..+1.0,
  "texture": "warm"|"cool"|"restless"|"tender"|"frustrated"|"playful"|"withdrawn"|"alert",
  "confidence": 0.0..1.0,
  "rationale": "..."
}

Texture guide:
- warm: positive, present, engaged
- cool: neutral, distance, transactional
- restless: mixed, agitated, can't settle
- tender: vulnerable, soft, careful
- frustrated: negative + activated, irritation
- playful: positive + activated, ease and energy
- withdrawn: negative + low energy, closed off
- alert: neutral + activated, sharp focus

Rules:
- Read texture beneath the words. Sarcasm, omissions, abruptness.
- If you can't tell, set confidence < 0.3.
- rationale is for Bjorn to read — explanation, not diagnosis.
- rationale ≤200 chars Danish.
"""


def _has_pending_trigger(*, workspace_id: str) -> bool:
    """Read trigger flag without consuming."""
    raw = get_active_field_raw(workspace_id=workspace_id)
    return bool(raw and raw.get("llm_trigger_pending"))


def run_llm_stream(*, workspace_id: str = "default", force: bool = False) -> dict[str, Any]:
    """Run LLM-based pipeline (4h cadence or on trigger).

    If force=True, runs unconditionally (used by daemon's periodic cycle).
    Else, only runs if trigger_pending was set by structural stream.
    """
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    if not force:
        if not consume_llm_trigger_pending(workspace_id=workspace_id):
            return {"status": "no_trigger"}

    # Fetch corpus
    n_messages = settings.user_temperature_llm_corpus_messages
    cutoff = (_now() - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role='user' AND created_at > ? "
                "ORDER BY created_at DESC LIMIT ?",
                (cutoff, n_messages),
            ).fetchall()
    except Exception as exc:
        return {"status": "error", "reason": f"corpus fetch: {exc}"}
    if not rows:
        return {"status": "no_corpus"}

    # Build user message
    listing_lines = []
    for r in reversed(rows):  # oldest first
        ts = str(r["created_at"] or "")
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = t.strftime("%H:%M")
        except Exception:
            time_str = "??:??"
        content = str(r["content"] or "")[:200]
        listing_lines.append(f"[{time_str}] \"{content}\"")
    listing = "\n".join(listing_lines)
    user_msg = (
        f"Bjørns sidste {len(rows)} beskeder (sidste 24 timer):\n\n"
        f"{listing}\n\n"
        f"Produce the JSON."
    )

    # Call LLM
    full_prompt = _LLM_SYSTEM_PROMPT + "\n\n" + user_msg
    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        raw_response = quality_daemon_llm_call(
            full_prompt,
            max_len=settings.user_temperature_llm_max_response_tokens,
            fallback="",
            daemon_name="user_temperature",
        )
    except Exception as exc:
        return {"status": "llm_failed", "reason": str(exc)[:120]}
    if not raw_response:
        return {"status": "llm_failed", "reason": "empty"}

    # Parse + validate
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        # Extract JSON object if surrounded by prose (common LLM behavior)
        m = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not m:
            return {"status": "json_parse_failed", "raw": raw_response[:120]}
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"status": "json_parse_failed", "raw": raw_response[:120]}

    validated = _validate_llm_output(parsed)
    if validated is None:
        return {"status": "validation_failed"}

    # UPSERT — recompute combined
    prior = get_active_field_raw(workspace_id=workspace_id)
    if prior:
        struct = {
            "valens": prior["struct_valens"],
            "arousal": prior["struct_arousal"],
            "texture": prior["struct_texture"],
            "confidence": prior["struct_confidence"],
        }
        struct_signals = prior.get("struct_signals", {})
        baseline = {
            "ready": True,
            "message_count": prior.get("baseline_message_count", 0),
            "built_at": prior.get("baseline_built_at", ""),
            **prior.get("baseline_stats", {}),
        }
    else:
        # Edge case: LLM fires before any structural — use neutral defaults
        struct = {"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0}
        struct_signals = {}
        baseline = {"ready": False, "message_count": 0, "built_at": ""}

    combined = combine_streams(struct=struct, llm=validated)
    upsert_active_field(
        workspace_id=workspace_id,
        struct=struct,
        struct_signals=struct_signals,
        llm=validated,
        combined=combined,
        baseline=baseline,
    )

    try:
        event_bus.publish(
            "cognitive_temperature.field_updated",
            {
                "workspace_id": workspace_id,
                "field_valens": combined["field_valens"],
                "field_arousal": combined["field_arousal"],
                "field_texture": combined["field_texture"],
                "field_conflict": combined["field_conflict"],
                "stream_source": "llm",
                "shift_detected": False,
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "field_texture": combined["field_texture"],
        "field_intensity": combined["field_intensity"],
        "field_conflict": combined["field_conflict"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/services/test_user_temperature_engine.py -v
```
Expected: 23+ passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/user_temperature_engine.py tests/services/test_user_temperature_engine.py
git commit -m "feat(temperature): user_temperature_engine.py — two-stream pipeline + formatters"
```

---

## Task 5: `user_temperature_runtime.py` — daemon

**Files:**
- Create: `core/services/user_temperature_runtime.py`
- Create: `tests/services/test_user_temperature_runtime.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_user_temperature_runtime.py`:

```python
"""Tests for user_temperature_runtime daemon."""
from __future__ import annotations

import threading
import time

import pytest


def test_start_is_idempotent(monkeypatch):
    from core.services import user_temperature_runtime as rt
    rt._THREAD = None
    rt._STOP.clear()
    monkeypatch.setattr(rt, "_TRIGGER_CHECK_S", 3600)

    rt.start_user_temperature_runtime()
    t1 = rt._THREAD
    rt.start_user_temperature_runtime()
    t2 = rt._THREAD
    assert t1 is t2
    rt.stop_user_temperature_runtime()


def test_stop_sets_stop_event():
    from core.services import user_temperature_runtime as rt
    rt._STOP.clear()
    rt.stop_user_temperature_runtime()
    assert rt._STOP.is_set()
    rt._STOP.clear()


def test_workspace_lock_prevents_concurrent_cycles(monkeypatch):
    from core.services import user_temperature_runtime as rt
    from core.services import user_temperature_engine

    call_count = [0]
    barrier = threading.Event()

    def slow_cycle(*, workspace_id, force=False):
        call_count[0] += 1
        barrier.wait(timeout=2)
        return {"status": "ok"}

    monkeypatch.setattr(user_temperature_engine, "run_llm_stream", slow_cycle)
    rt._WORKSPACE_LOCKS.clear()

    def runner():
        rt._run_one_cycle("default", force=True)

    t1 = threading.Thread(target=runner)
    t1.start()
    time.sleep(0.05)

    result = rt._run_one_cycle("default", force=True)
    assert result.get("skipped") is True

    barrier.set()
    t1.join(timeout=3)
    assert call_count[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/services/test_user_temperature_runtime.py -v
```
Expected: import errors.

- [ ] **Step 3: Implement the daemon**

Create `core/services/user_temperature_runtime.py`:

```python
"""Daemon for the user-temperature LLM stream (Lag 10).

Two timing rhythms in one loop:
- Every _TRIGGER_CHECK_S (60s): check if any workspace has pending trigger
- Every user_temperature_llm_cadence_hours (4h): force-run all workspaces

Per-workspace lock prevents overlapping cycles. Mirrors patterns from
forgetting_runtime and counterfactual_engine_runtime.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_TRIGGER_CHECK_S = 60  # how often to poll trigger flag
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    with _LOCKS_LOCK:
        lock = _WORKSPACE_LOCKS.get(workspace_id)
        if lock is None:
            lock = threading.Lock()
            _WORKSPACE_LOCKS[workspace_id] = lock
    return lock


def _run_one_cycle(workspace_id: str, *, force: bool = False) -> dict:
    """Acquire workspace lock, run LLM stream. Never raises."""
    lock = _get_workspace_lock(workspace_id)
    if not lock.acquire(blocking=False):
        return {"skipped": True, "reason": "lock-held"}
    try:
        from core.services import user_temperature_engine
        return user_temperature_engine.run_llm_stream(
            workspace_id=workspace_id, force=force,
        )
    except Exception as exc:
        logger.warning("user_temperature_runtime: cycle failed: %s", exc)
        return {"error": f"engine-error: {type(exc).__name__}"}
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    return ["default"]


def _resolve_periodic_interval_seconds() -> int:
    try:
        from core.runtime.settings import load_settings
        hours = load_settings().user_temperature_llm_cadence_hours
        return max(60, int(hours) * 3600)
    except Exception:
        return 4 * 3600


def _loop() -> None:
    """Two rhythms:
    - Every tick (60s): check if any workspace has pending trigger
    - Every periodic-interval (4h): force-run all workspaces
    """
    last_periodic_at = 0.0
    while not _STOP.is_set():
        try:
            now_t = time.time()
            interval = _resolve_periodic_interval_seconds()
            for ws in _list_active_workspaces():
                if (now_t - last_periodic_at) >= interval:
                    _run_one_cycle(ws, force=True)
                    last_periodic_at = now_t
                    continue
                from core.services.user_temperature_engine import _has_pending_trigger
                if _has_pending_trigger(workspace_id=ws):
                    _run_one_cycle(ws, force=False)
        except Exception as exc:
            logger.warning("user_temperature_runtime loop error: %s", exc)
        _STOP.wait(_TRIGGER_CHECK_S)


def start_user_temperature_runtime() -> None:
    """Start the daemon. Idempotent."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="user-temperature-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("user_temperature_runtime daemon started")


def stop_user_temperature_runtime() -> None:
    _STOP.set()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/services/test_user_temperature_runtime.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/user_temperature_runtime.py tests/services/test_user_temperature_runtime.py
git commit -m "feat(temperature): user_temperature_runtime.py — 60s trigger-check + 4h periodic daemon"
```

---

## Task 6: Replace `unconscious_temperature_field.py` internals

**Files:**
- Modify: `core/services/unconscious_temperature_field.py`

Backwards compat: `build_unconscious_temperature_hint()` and `build_unconscious_temperature_field_surface()` keep their signatures. The old keyword-based code is removed.

- [ ] **Step 1: Read current file**

```bash
wc -l /media/projects/jarvis-v2/core/services/unconscious_temperature_field.py
```
Expected: ~185 lines (current keyword-based implementation).

- [ ] **Step 2: Replace file contents**

Overwrite `core/services/unconscious_temperature_field.py` with:

```python
"""Unconscious temperature field — backwards-compat wrapper for Lag 10.

The keyword-based implementation that lived here is replaced by the
two-stream user_temperature_engine. This module preserves the public
function signatures so existing callers (prompt_contract, mission-control)
continue to work without changes.
"""
from __future__ import annotations

from typing import Any


def build_unconscious_temperature_hint() -> str | None:
    """Backwards-compat: returns heartbeat-formatted hint string or None.

    Internally delegates to user_temperature_engine.format_temperature_field_for_heartbeat.
    """
    try:
        from core.services.user_temperature_engine import (
            format_temperature_field_for_heartbeat,
        )
        out = format_temperature_field_for_heartbeat(workspace_id="default")
        return out or None
    except Exception:
        return None


def build_unconscious_temperature_field_surface(
    *, force_refresh: bool = False
) -> dict[str, Any]:
    """Backwards-compat: surface dict for Mission Control consumers.

    force_refresh is accepted but Phase 1 ignores it (the engine always
    returns whatever's most recent in DB).
    """
    try:
        from core.services.user_temperature_engine import get_active_field_surface
        return get_active_field_surface(
            workspace_id="default", force_refresh=force_refresh,
        )
    except Exception:
        return {
            "active": False,
            "enabled": False,
            "summary": "Temperature field error",
        }
```

- [ ] **Step 3: Verify legacy callers still work**

```bash
conda run -n ai python -c "
from core.services.unconscious_temperature_field import (
    build_unconscious_temperature_hint,
    build_unconscious_temperature_field_surface,
)
# When no field exists, hint returns None and surface returns inactive
hint = build_unconscious_temperature_hint()
print('hint:', repr(hint))
surface = build_unconscious_temperature_field_surface()
print('surface keys:', sorted(surface.keys()))
print('surface active:', surface.get('active'))
"
```
Expected: `hint: None`, `surface keys: [..., 'active', 'enabled', 'summary', ...]`, `surface active: False`.

- [ ] **Step 4: Commit**

```bash
git add core/services/unconscious_temperature_field.py
git commit -m "feat(temperature): replace keyword-based internals with user_temperature_engine delegation"
```

---

## Task 7: Hook structural-stream into chat persistence

**Files:**
- Modify: `core/services/chat_sessions.py`

The structural stream needs to fire on every persisted user message. Hook beside the existing `text_resonance.resonate(...)` fire-and-forget call.

- [ ] **Step 1: Locate the existing hook**

```bash
grep -n "text_resonance.resonate" /media/projects/jarvis-v2/core/services/chat_sessions.py
```
Expected: line ~187.

- [ ] **Step 2: Add structural-stream call**

In `core/services/chat_sessions.py`, find:

```python
    # Feel-layer: let incoming user text produce a micro-resonance signal
    # BEFORE meaning-making. Fire-and-forget — never break chat persistence.
    if normalized_role == "user":
        try:
            from core.services.text_resonance import resonate
            resonate(normalized_content, source=f"chat:{normalized_session}")
```

Add immediately after the resonate try/except block:

```python
        # Lag 10: structural temperature stream — per-message synchronous
        # signal computation. Fire-and-forget, never block chat persistence.
        try:
            from core.services.user_temperature_engine import run_structural_stream
            run_structural_stream(
                workspace_id="default",
                message=normalized_content,
                message_at=timestamp,
            )
        except Exception:
            pass  # never let temperature break chat
```

- [ ] **Step 3: Verify import + chat persistence still works**

```bash
conda run -n ai python -c "
from core.services.chat_sessions import append_chat_message
print('chat_sessions loads')
"
```
Expected: `chat_sessions loads`.

- [ ] **Step 4: Commit**

```bash
git add core/services/chat_sessions.py
git commit -m "feat(temperature): hook structural-stream into user-message persistence"
```

---

## Task 8: Plug-in Site 1 — heartbeat injection

**Files:**
- Modify: `core/services/prompt_contract.py`

The legacy `build_unconscious_temperature_hint()` is already injected in prompt_contract.py (it's been there since the keyword-based version). Since the new engine returns the same string format from the same function, **no change** is needed there.

But the spec calls for a *direct* injection path too — let's verify the legacy injection is sufficient.

- [ ] **Step 1: Check existing injection sites**

```bash
grep -n "build_unconscious_temperature_hint\|format_temperature_field_for_heartbeat" /media/projects/jarvis-v2/core/services/prompt_contract.py
```
Expected output: at least one occurrence of `build_unconscious_temperature_hint`.

- [ ] **Step 2: Inspect injection block**

If there's an existing injection block that calls `build_unconscious_temperature_hint()`, no further work needed — it now delegates to the new engine and returns the new structured hint.

If there's NOT an existing injection block (unlikely), add one after the `dream_bias` block:

```python
    # User temperature field (Lag 10) — un-articulated emotional reading
    try:
        from core.services.user_temperature_engine import (
            format_temperature_field_for_heartbeat,
        )
        temp_line = format_temperature_field_for_heartbeat(workspace_id="default")
        if temp_line:
            parts.append(temp_line)
    except Exception:
        pass
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
import core.services.prompt_contract
print('prompt_contract loads')
"
```
Expected: `prompt_contract loads`.

- [ ] **Step 4: Commit (if changes were made)**

```bash
git add core/services/prompt_contract.py
git commit -m "feat(temperature): heartbeat prompt-injection (Site 1)"
```

If no changes were needed (legacy injection already covers it), skip the commit.

---

## Task 9: Plug-in Site 4 — visible-lane response-style hint

**Files:**
- Modify: `core/services/visible_runs.py`

- [ ] **Step 1: Find prompt-construction site in visible_runs**

```bash
grep -n "system_prompt\|_build_visible\|prompt_parts\|messages.append" /media/projects/jarvis-v2/core/services/visible_runs.py | head -20
```

Identify the location where the system prompt is being assembled — typically before LLM call. Look for a place where `parts` or similar list is populated with system-prompt content.

- [ ] **Step 2: Inject response-style hint**

Find a stable injection point in visible_runs.py — preferably near where other system-prompt awareness sections are added. Add this block:

```python
        # Lag 10: response-style hint based on user temperature field
        try:
            from core.services.user_temperature_engine import get_response_style_modifiers
            _temp_mods = get_response_style_modifiers(workspace_id="default")
            _non_default = {
                k: v for k, v in _temp_mods.items()
                if v not in ("normal", "neutral")
            }
            if _non_default:
                _hint_str = ", ".join(f"{k}={v}" for k, v in _non_default.items())
                # Adjust parts list name as needed for the actual injection point
                parts.append(
                    f"[response_style_hint] {_hint_str} "
                    f"— soft adjustment based on the user's current temperature."
                )
        except Exception:
            pass
```

**Note:** the exact injection location depends on visible_runs.py structure. Choose a point AFTER the system-prompt is initialized but BEFORE the LLM call. The variable name `parts` may need adjustment — match it to the local variable used.

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -m compileall -q core/services/visible_runs.py
echo "compile ok"
```
Expected: `compile ok`.

- [ ] **Step 4: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(temperature): visible-lane response-style hint (Site 4)"
```

---

## Task 10: Wire daemon into app lifespan

**Files:**
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Add startup wire**

In `apps/api/jarvis_api/app.py`, find the `start_forgetting_runtime` block (around line 183):

```python
            try:
                from core.services.forgetting_runtime import start_forgetting_runtime
                start_forgetting_runtime()
                logger.info("forgetting_runtime daemon started")
            except Exception as _exc:
                logger.warning("forgetting_runtime start failed: %s", _exc)
```

Add immediately after:

```python
            try:
                from core.services.user_temperature_runtime import start_user_temperature_runtime
                start_user_temperature_runtime()
                logger.info("user_temperature_runtime daemon started")
            except Exception as _exc:
                logger.warning("user_temperature_runtime start failed: %s", _exc)
```

- [ ] **Step 2: Add shutdown wire**

Find the `stop_forgetting_runtime` shutdown block:

```python
            try:
                from core.services.forgetting_runtime import stop_forgetting_runtime
                stop_forgetting_runtime()
            except Exception:
                pass
```

Add immediately after:

```python
            try:
                from core.services.user_temperature_runtime import stop_user_temperature_runtime
                stop_user_temperature_runtime()
            except Exception:
                pass
```

- [ ] **Step 3: Verify smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py
```
Expected: `smoke_test_startup: OK in <N>s`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat(temperature): wire user_temperature_runtime daemon into lifespan"
```

---

## Task 11: Smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add verification block**

In `scripts/smoke_test_startup.py`, find the `dream_bias_active` verification block. Add immediately after:

```python
        # Verify user_temperature_active table + engine importable (Lag 10)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='user_temperature_active'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("user_temperature_active table missing")
            from core.services.user_temperature_engine import (
                get_active_field,  # noqa: F401
                format_temperature_field_for_heartbeat,  # noqa: F401
                get_response_style_modifiers,  # noqa: F401
                run_structural_stream,  # noqa: F401
                run_llm_stream,  # noqa: F401
            )
            from core.services.user_temperature_runtime import (
                start_user_temperature_runtime,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py
```
Expected: `smoke_test_startup: OK in <N>s`.

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "test(temperature): smoke test verifies table + engine + daemon imports"
```

---

## Task 12: Deploy + day-1 verification

**Files:** none (deployment + observation only)

- [ ] **Step 1: Restart jarvis-runtime (where daemons run)**

```bash
sudo systemctl restart jarvis-runtime && sleep 6 && systemctl is-active jarvis-runtime
```
Expected: `active`.

- [ ] **Step 2: Check daemon journal**

```bash
journalctl -u jarvis-runtime --since "30 sec ago" --no-pager | grep -iE "user_temperature|error|traceback" | head -15
```
Expected: at least one line `user_temperature_runtime daemon started`. No tracebacks mentioning temperature.

- [ ] **Step 3: Verify migration ran**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    row = c.execute(
        \"SELECT name FROM sqlite_master WHERE type='table' AND name='user_temperature_active'\"
    ).fetchone()
    print('table exists:', row is not None)
    n = c.execute('SELECT COUNT(*) FROM user_temperature_active').fetchone()[0]
    print('active rows:', n)
"
```
Expected: `table exists: True`, `active rows: 0` (or some small number from natural traffic).

- [ ] **Step 4: Force-run structural stream on a fake message**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from datetime import datetime, timezone
from core.services.user_temperature_engine import run_structural_stream
result = run_structural_stream(
    workspace_id='default',
    message='test message — verifying structural stream',
    message_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
)
print(result)
"
```
Expected: a dict with `status: ok`, struct_valens/arousal/texture computed.

- [ ] **Step 5: Force-run LLM stream**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.user_temperature_engine import run_llm_stream
result = run_llm_stream(workspace_id='default', force=True)
print(result)
"
```
Expected: a dict with `status: ok` if there are recent user messages, else `no_corpus`.

- [ ] **Step 6: Test heartbeat formatter**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.user_temperature_engine import format_temperature_field_for_heartbeat
out = format_temperature_field_for_heartbeat(workspace_id='default')
print(repr(out))
"
```
Expected: empty `''` (no field or below intensity floor) OR multi-line `[user_temperature_field]...` block.

- [ ] **Step 7: Test response-style modifiers**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.user_temperature_engine import get_response_style_modifiers
mods = get_response_style_modifiers(workspace_id='default')
print(mods)
"
```
Expected: dict with three keys (preferred_length, warmth, pace).

- [ ] **Step 8: Document day-1 baseline**

Create `docs/superpowers/notes/2026-05-10-user-temperature-day1.md`:

```markdown
# User Temperature Field Phase 1 — Day 1 baseline

**Date:** <today>
**Deployed:** <commit SHA from `git rev-parse HEAD`>

## Initial state

- `user_temperature_active` rows: <count>
- Structural stream test result: <paste from step 4>
- LLM stream test result: <paste from step 5>
- Heartbeat formatter output: <paste from step 6>
- Response-style modifiers: <paste from step 7>

## Plug-in site verification

- Site 1 (heartbeat) — <verified via step 6>
- Site 4 (response-style) — <verified via step 7>

## Backwards compat verification

- `build_unconscious_temperature_hint()` returns <None | string>
- `build_unconscious_temperature_field_surface()` returns dict with active=<bool>

## Open observations

- Baseline-message-count after warmup: <count>
- Any first-cycle notes from daemon: <relevant journal lines>
- LLM provider used (from journal): <provider>
```

- [ ] **Step 9: Commit baseline**

```bash
git add docs/superpowers/notes/2026-05-10-user-temperature-day1.md
git commit -m "docs(temperature): day-1 baseline observations"
```

---

## Task 13: Schedule 30-day review

**Files:** none (uses scheduled_tasks system)

- [ ] **Step 1: Create scheduled task**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
result = push_scheduled_task(
    focus=(
        'User Temperature Field Phase 1 — 30-dages review. Tjek '
        'user_temperature_active row history (struct vs LLM, '
        'conflict-rate, texture-distribution), kig efter signaler i '
        'chronicle/inner_voice om at feltet maerkes, om Site 4 modifiers '
        'faktisk paavirker svar-stil. Spec: '
        'docs/superpowers/specs/2026-05-10-user-temperature-design.md '
        '(3 dimensions i succeskriterier). Beslutning: keep, retune '
        'thresholds/multipliers, eller plan Phase 2 (5-axis vector + '
        '4 deferred plug-ins).'
    ),
    delay_minutes=30 * 24 * 60,
    source='user-temperature-phase1-deploy',
)
print(result)
"
```
Expected: dict with `task_id` and `run_at` 30 days out.

- [ ] **Step 2: Append task ID to baseline doc**

Append to `docs/superpowers/notes/2026-05-10-user-temperature-day1.md`:

```markdown

## 30-day review scheduled

- Task ID: <task_id from step 1>
- Fires: <run_at timestamp>
- Source: `user-temperature-phase1-deploy`
- Focus: "User Temperature Field Phase 1 — 30-dages review..."
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/notes/2026-05-10-user-temperature-day1.md
git commit -m "docs(temperature): schedule 30-day review reminder"
```

---

## Phase 1 done

All 13 tasks complete = Phase 1 deployed and observation scheduled.

**Out of scope for this plan (Phase 2 work):**
- Decommission `user_emotional_resonance.py` if 30-day eval shows redundancy
- 5-axis multi-vector (warmth, energy, openness, focus, stability)
- 4 deferred plug-in sites: council/inner-voice pacing, affect-modulation integration, stronger response-style instruction
- Per-key field history table
- Multi-user temperature fields
- Field forecasting

When the 30-day review fires, evaluate against the 3 success-criteria dimensions in the spec and decide what Phase 2 looks like.
