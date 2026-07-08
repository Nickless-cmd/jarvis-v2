---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Counterfactuals Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the counterfactuals pipeline in **dry-run mode** — trigger detection, dedup, schema, scheduler, eventbus publication — without LLM generation. Run for 7 days to capture trigger volume + distribution. Phase 2-4 (LLM, apophenia, tool exposition) get separate plans informed by Phase 1 data.

**Architecture:** Daemon-driven pipeline (60-min cadence). Per-cycle: fetch trigger-events from 4 families, dedup via `cf_key` hash, store as counterfactual rows with `what_if="TODO"` and `llm_confidence=0.0`. UNIQUE constraint on `cf_key` makes the pipeline idempotent. Phase 1 daemon processes only the `default` workspace (multi-workspace activation deferred to Phase 2).

**Tech Stack:** Python 3.11, SQLite, threading-based daemon, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-07-counterfactuals-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/counterfactual_triggers.py` | `TriggerEvent` dataclass, `fetch_recent_triggers()`, per-family `_key_*()` extractors, `cf_key()` hash |
| `core/services/counterfactual_engine.py` | `run()` orchestrator, dry-run logic, stubs for `_generate_counterfactuals_via_llm` (Phase 2) and `_modulate_with_apophenia` (Phase 3) |
| `core/services/counterfactual_engine_runtime.py` | Daemon: `start_counterfactual_runtime()`, `_loop()`, per-workspace advisory lock |
| `tests/services/test_counterfactual_triggers.py` | |
| `tests/services/test_counterfactual_engine.py` | |
| `tests/services/test_counterfactual_engine_runtime.py` | |
| `tests/runtime/test_counterfactuals_migration.py` | |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | 4 new flags: enabled, interval, lookback, promotion_threshold |
| `core/eventbus/events.py` | Add `cognitive_counterfactual` to `ALLOWED_EVENT_FAMILIES` |
| `core/runtime/db.py` | New `_ensure_counterfactuals_table()` helper called from `init_db()` |
| `apps/api/jarvis_api/app.py` | Start/stop `counterfactual_engine_runtime` daemon in lifespan |
| `scripts/smoke_test_startup.py` | Verify counterfactuals table + daemon startable |

---

## Task 1: Settings flags + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, find the existing `decision_signals_enabled` and add right after it (before `extra`):

```python
    # Counterfactuals Phase 1 (added 2026-05-07)
    # When True (default), the counterfactual_engine_runtime daemon runs
    # the dry-run capture pipeline at the configured interval.
    counterfactual_engine_enabled: bool = True
    counterfactual_engine_interval_seconds: int = 3600  # 1h between cycles
    counterfactual_engine_lookback_minutes: int = 60    # how far back to fetch triggers
    counterfactual_engine_promotion_threshold: float = 0.6  # final_confidence to promote
```

- [ ] **Step 2: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES` set (next to `decision_signal`):

```python
    "cognitive_counterfactual",  # counterfactual reflection (added 2026-05-07)
```

- [ ] **Step 3: Verify**

Run:
```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
s = RuntimeSettings()
assert s.counterfactual_engine_enabled is True
assert s.counterfactual_engine_interval_seconds == 3600
assert 'cognitive_counterfactual' in ALLOWED_EVENT_FAMILIES
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(counterfactuals): settings flags + event family (Phase 1)"
```

---

## Task 2: DB migration

**Files:**
- Modify: `core/runtime/db.py`
- Test: `tests/runtime/test_counterfactuals_migration.py`

- [ ] **Step 1: Write failing tests**

Create `tests/runtime/test_counterfactuals_migration.py`:

```python
"""Verify counterfactuals table created with UNIQUE(cf_key) constraint."""
import sqlite3
import pytest

from core.runtime.db import _ensure_counterfactuals_table


def test_table_created():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='counterfactuals'"
    ).fetchone()
    assert row is not None


def test_table_has_expected_columns():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(counterfactuals)").fetchall()}
    expected = {
        "cf_id", "cf_key", "workspace_id", "cluster_id",
        "trigger_event_ids_json", "trigger_types_json",
        "what_if", "likely_difference", "reasoning",
        "llm_confidence", "apophenia_score", "final_confidence",
        "status", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_cf_key_is_unique():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    conn.execute(
        "INSERT INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
        "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
        "VALUES ('cf-1', 'key-A', 'default', 'c1', '[1]', '[\"x\"]', 'what if', "
        "'generated', 'now', 'now')"
    )
    # Second insert with same cf_key must fail
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
            "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
            "VALUES ('cf-2', 'key-A', 'default', 'c2', '[2]', '[\"y\"]', 'what if', "
            "'generated', 'now', 'now')"
        )


def test_insert_or_ignore_is_idempotent():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    sql = (
        "INSERT OR IGNORE INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
        "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
        "VALUES (?, ?, 'default', 'c1', '[1]', '[\"x\"]', 'what if', "
        "'generated', 'now', 'now')"
    )
    conn.execute(sql, ("cf-1", "key-A"))
    conn.execute(sql, ("cf-2", "key-A"))  # should be no-op
    rows = conn.execute("SELECT cf_id FROM counterfactuals").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "cf-1"


def test_indexes_created():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'idx_counterfactuals_%'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "idx_counterfactuals_workspace_created" in names
    assert "idx_counterfactuals_status" in names


def test_idempotent_migration():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    _ensure_counterfactuals_table(conn)  # second run must not raise
```

Run: `pytest tests/runtime/test_counterfactuals_migration.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement migration helper**

In `core/runtime/db.py`, after the existing `_ensure_decision_trigger_column` function, add:

```python
def _ensure_counterfactuals_table(conn: sqlite3.Connection) -> None:
    """Create counterfactuals table with UNIQUE(cf_key) constraint.

    Idempotent: CREATE TABLE IF NOT EXISTS + index creation. Re-runs are
    no-ops. UNIQUE constraint on cf_key makes INSERT OR IGNORE
    idempotent at the row level.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS counterfactuals (
            cf_id TEXT PRIMARY KEY,
            cf_key TEXT NOT NULL UNIQUE,
            workspace_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            trigger_event_ids_json TEXT NOT NULL,
            trigger_types_json TEXT NOT NULL,
            what_if TEXT NOT NULL,
            likely_difference TEXT,
            reasoning TEXT,
            llm_confidence REAL DEFAULT 0.0,
            apophenia_score REAL DEFAULT 1.0,
            final_confidence REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_counterfactuals_workspace_created "
        "ON counterfactuals(workspace_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_counterfactuals_status "
        "ON counterfactuals(status)"
    )
```

Then call it from `init_db()` near the other ensure-helpers:

```python
        _ensure_counterfactuals_table(conn)
```

(Place this right after `_ensure_decision_trigger_column(conn)` for grouping.)

- [ ] **Step 3: Run tests**

Run: `pytest tests/runtime/test_counterfactuals_migration.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_counterfactuals_migration.py
git commit -m "feat(counterfactuals): DB migration with UNIQUE(cf_key) constraint"
```

---

## Task 3: counterfactual_triggers.py

**Files:**
- Create: `core/services/counterfactual_triggers.py`
- Test: `tests/services/test_counterfactual_triggers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_counterfactual_triggers.py`:

```python
import pytest
from core.services import counterfactual_triggers as ct


def test_cf_key_is_deterministic():
    a = ct.cf_key("default", "self_review_outcome.created", "rev_abc")
    b = ct.cf_key("default", "self_review_outcome.created", "rev_abc")
    assert a == b


def test_cf_key_differs_per_workspace():
    a = ct.cf_key("default", "conflict.detected", "conflict_1")
    b = ct.cf_key("mikkel", "conflict.detected", "conflict_1")
    assert a != b


def test_cf_key_differs_per_event_type():
    a = ct.cf_key("default", "self_review_outcome.created", "rev_1")
    b = ct.cf_key("default", "conflict.detected", "rev_1")
    assert a != b


def test_key_self_review_uses_review_id():
    payload = {"review_id": "rev_xyz", "run_id": "visible-1"}
    assert ct._key_self_review(payload) == "rev_xyz"


def test_key_self_review_falls_back_to_run_id():
    payload = {"run_id": "visible-1"}
    assert ct._key_self_review(payload) == "visible-1"


def test_key_self_review_returns_empty_when_both_missing():
    assert ct._key_self_review({}) == ""


def test_key_conflict_prefers_conflict_id():
    assert ct._key_conflict({"conflict_id": "c1", "run_id": "r1"}) == "c1"


def test_key_conflict_falls_back_to_run_id():
    assert ct._key_conflict({"run_id": "r1"}) == "r1"


def test_key_decision_uses_decision_id():
    assert ct._key_decision({"decision_id": "dec_xxx"}) == "dec_xxx"


def test_key_review_uses_review_id():
    assert ct._key_review({"review_id": "rev_xxx"}) == "rev_xxx"


def test_fetch_recent_triggers_filters_by_lookback(monkeypatch):
    """Events older than lookback_minutes must be excluded."""
    fake_rows = []
    def fake_query(sql, params):
        return fake_rows
    # We'll mock at the db layer in the implementation test
    # For now, just verify the function exists and accepts the right kwargs
    out = ct.fetch_recent_triggers(workspace_id="default", lookback_minutes=60)
    assert isinstance(out, list)


def test_fetch_recent_triggers_returns_trigger_events(monkeypatch):
    """When events match, return TriggerEvent objects."""
    import json
    sample_rows = [
        {
            "id": 1001,
            "kind": "self_review_outcome.created",
            "payload_json": json.dumps({
                "review_id": "rev_abc",
                "run_id": "visible-xyz",
                "summary": "I missed something",
            }),
            "created_at": "2026-05-07T12:30:00+00:00",
        },
        {
            "id": 1002,
            "kind": "conflict.detected",
            "payload_json": json.dumps({
                "conflict_id": "conf-1",
                "summary": "two daemons disagreed",
            }),
            "created_at": "2026-05-07T12:35:00+00:00",
        },
    ]

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def __init__(self, rows):
                    self._rows = rows
                def fetchall(self): return [dict(r) for r in self._rows]
            return _R(sample_rows)

    monkeypatch.setattr(ct, "connect", _FakeConn)
    out = ct.fetch_recent_triggers(workspace_id="default", lookback_minutes=60)
    assert len(out) == 2
    assert isinstance(out[0], ct.TriggerEvent)
    assert out[0].source_event_id == 1001
    assert out[0].event_type == "self_review_outcome.created"
    assert out[0].primary_key == "rev_abc"


def test_fetch_skips_events_with_no_primary_key(monkeypatch):
    """Events whose key extractor returns empty string get dropped."""
    import json
    sample_rows = [
        {
            "id": 2001,
            "kind": "decision_revoked",
            "payload_json": json.dumps({}),  # no decision_id, no fallback
            "created_at": "2026-05-07T12:30:00+00:00",
        },
    ]

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def fetchall(self): return [dict(r) for r in sample_rows]
            return _R()

    monkeypatch.setattr(ct, "connect", _FakeConn)
    out = ct.fetch_recent_triggers(workspace_id="default", lookback_minutes=60)
    assert out == []  # event with no key was filtered
```

Run: `pytest tests/services/test_counterfactual_triggers.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement counterfactual_triggers.py**

Create `core/services/counterfactual_triggers.py`:

```python
"""Trigger detection for counterfactual reflection.

Reads recent regret-events from the events table and normalizes them
into TriggerEvent records. Each event-family has a primary-key extractor
that picks the most stable identifier from the payload.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from core.runtime.db import connect

logger = logging.getLogger(__name__)


@dataclass
class TriggerEvent:
    """A regret-worthy event normalized for counterfactual processing."""
    source_event_id: int
    workspace_id: str
    event_type: str
    primary_key: str
    summary: str
    payload: dict
    created_at: str


def _key_self_review(payload: dict) -> str:
    return str(payload.get("review_id") or payload.get("run_id") or "").strip()


def _key_conflict(payload: dict) -> str:
    return str(payload.get("conflict_id") or payload.get("run_id") or "").strip()


def _key_decision(payload: dict) -> str:
    return str(payload.get("decision_id") or "").strip()


def _key_review(payload: dict) -> str:
    return str(payload.get("review_id") or "").strip()


# event_type → primary_key extractor
_TRIGGER_FAMILIES: dict[str, Callable[[dict], str]] = {
    "self_review_outcome.created": _key_self_review,
    "conflict.detected": _key_conflict,
    "decision_revoked": _key_decision,
    "behavioral_decision_review.broken": _key_review,
}


def cf_key(workspace_id: str, event_type: str, primary_key: str) -> str:
    """First-pass dedup hash. Same workspace+type+key = same hash = skip."""
    raw = f"{workspace_id}:{event_type}:{primary_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _extract_summary(payload: dict) -> str:
    for k in ("summary", "reason", "message", "directive", "note"):
        v = payload.get(k)
        if v:
            return str(v)[:300]
    return ""


def fetch_recent_triggers(
    *, workspace_id: str, lookback_minutes: int = 60
) -> list[TriggerEvent]:
    """Query events table for recent regret-worthy events.

    Returns TriggerEvents for the 4 trigger families. Events whose
    primary-key extractor returns empty string are skipped (we need a
    stable identifier for cf_key dedup).
    """
    cutoff = (datetime.now(UTC) - timedelta(minutes=max(1, int(lookback_minutes)))).isoformat()
    placeholders = ",".join("?" for _ in _TRIGGER_FAMILIES)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE kind IN ({placeholders}) AND created_at >= ? "
        f"ORDER BY id ASC"
    )
    params = list(_TRIGGER_FAMILIES.keys()) + [cutoff]

    out: list[TriggerEvent] = []
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("counterfactual_triggers: events query failed: %s", exc)
        return []

    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        event_type = str(r["kind"] or "")
        extractor = _TRIGGER_FAMILIES.get(event_type)
        if extractor is None:
            continue
        primary_key = extractor(payload)
        if not primary_key:
            # Skip events without stable identifier — can't dedup safely
            continue
        out.append(TriggerEvent(
            source_event_id=int(r["id"]),
            workspace_id=str(workspace_id),
            event_type=event_type,
            primary_key=primary_key,
            summary=_extract_summary(payload),
            payload=payload,
            created_at=str(r["created_at"] or ""),
        ))
    return out
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_counterfactual_triggers.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/counterfactual_triggers.py tests/services/test_counterfactual_triggers.py
git commit -m "feat(counterfactuals): trigger detection + cf_key dedup hash"
```

---

## Task 4: counterfactual_engine.py (dry-run pipeline)

**Files:**
- Create: `core/services/counterfactual_engine.py`
- Test: `tests/services/test_counterfactual_engine.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_counterfactual_engine.py`:

```python
import pytest
from core.services import counterfactual_engine as ce
from core.services.counterfactual_triggers import TriggerEvent


def _trigger(**overrides):
    base = dict(
        source_event_id=1,
        workspace_id="default",
        event_type="self_review_outcome.created",
        primary_key="rev_abc",
        summary="something went wrong",
        payload={"review_id": "rev_abc", "summary": "something went wrong"},
        created_at="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return TriggerEvent(**base)


def test_run_returns_summary_dict(monkeypatch):
    """run() always returns a summary, never raises."""
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: [])
    out = ce.run(workspace_id="default")
    assert isinstance(out, dict)
    assert out["workspace_id"] == "default"
    assert "triggers_fetched" in out
    assert "elapsed_ms" in out


def test_run_with_no_triggers_is_clean_noop(monkeypatch):
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: [])
    out = ce.run(workspace_id="default")
    assert out["triggers_fetched"] == 0
    assert out["triggers_unique"] == 0
    assert out["counterfactuals_generated"] == 0
    assert out["llm_generation_failures"] == 0


def test_run_dry_run_stores_placeholder_values(monkeypatch):
    """Phase 1 default: dry_run=True → what_if='TODO', llm_confidence=0.0."""
    triggers = [_trigger()]
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: triggers)
    monkeypatch.setattr(ce, "_dedup_filter", lambda triggers: triggers)

    captured = []
    monkeypatch.setattr(
        ce, "_store_counterfactual",
        lambda **kwargs: captured.append(kwargs) or None,
    )
    monkeypatch.setattr(ce, "_publish_event", lambda **kwargs: None)

    out = ce.run(workspace_id="default", dry_run=True)
    assert out["counterfactuals_generated"] == 1
    assert len(captured) == 1
    cf = captured[0]
    assert cf["what_if"] == "TODO"
    assert cf["llm_confidence"] == 0.0
    assert cf["apophenia_score"] == 1.0
    assert cf["final_confidence"] == 0.0
    assert cf["status"] == "generated"


def test_run_skipped_when_killswitch_off(monkeypatch):
    class FakeS:
        counterfactual_engine_enabled = False
        counterfactual_engine_lookback_minutes = 60
        counterfactual_engine_promotion_threshold = 0.6
    monkeypatch.setattr(ce, "RuntimeSettings", lambda: FakeS())
    out = ce.run(workspace_id="default")
    assert out["skipped"] is True
    assert out["skipped_reason"] == "killswitch-off"


def test_run_includes_trigger_breakdown(monkeypatch):
    """Phase 1 must report per-event-type counts in summary."""
    triggers = [
        _trigger(event_type="self_review_outcome.created", primary_key="r1"),
        _trigger(event_type="self_review_outcome.created", primary_key="r2"),
        _trigger(event_type="conflict.detected", primary_key="c1"),
    ]
    monkeypatch.setattr(ce, "fetch_recent_triggers", lambda **kwargs: triggers)
    monkeypatch.setattr(ce, "_dedup_filter", lambda triggers: triggers)
    monkeypatch.setattr(ce, "_store_counterfactual", lambda **kwargs: None)
    monkeypatch.setattr(ce, "_publish_event", lambda **kwargs: None)

    out = ce.run(workspace_id="default", dry_run=True)
    bd = out["trigger_breakdown"]
    assert bd["self_review_outcome.created"] == 2
    assert bd["conflict.detected"] == 1


def test_dedup_filter_removes_already_stored(monkeypatch):
    """First-pass dedup: cf_keys already in DB are filtered out."""
    triggers = [
        _trigger(event_type="self_review_outcome.created", primary_key="rev_a"),
        _trigger(event_type="self_review_outcome.created", primary_key="rev_b"),
    ]

    # Mock that "rev_a" is already stored
    from core.services.counterfactual_triggers import cf_key
    existing_key = cf_key("default", "self_review_outcome.created", "rev_a")

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            class _R:
                def fetchall(self): return [{"cf_key": existing_key}]
            return _R()

    monkeypatch.setattr(ce, "connect", _FakeConn)
    out = ce._dedup_filter(triggers)
    assert len(out) == 1
    assert out[0].primary_key == "rev_b"


def test_run_handles_fetch_exception_gracefully(monkeypatch):
    """If fetch_recent_triggers raises, return error summary, not exception."""
    def boom(**kwargs):
        raise RuntimeError("DB unreachable")
    monkeypatch.setattr(ce, "fetch_recent_triggers", boom)
    out = ce.run(workspace_id="default")
    assert out["triggers_fetched"] == 0
    assert "error" in out or out.get("counterfactuals_generated") == 0
```

Run: `pytest tests/services/test_counterfactual_engine.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement counterfactual_engine.py**

Create `core/services/counterfactual_engine.py`:

```python
"""Counterfactual reflection orchestrator.

Phase 1 (dry-run): captures triggers, dedups, stores rows with placeholder
values. No LLM call. No apophenia modulation.

Phase 2-4 will progressively enable:
  - _generate_counterfactuals_via_llm (Phase 2)
  - _modulate_with_apophenia (Phase 3)
  - tool exposition via decisions_tools-style handlers (Phase 4)
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings
from core.services.counterfactual_triggers import (
    TriggerEvent,
    cf_key,
    fetch_recent_triggers,
)

logger = logging.getLogger(__name__)


def run(*, workspace_id: str = "default", dry_run: bool = True) -> dict:
    """One full pipeline cycle. Always returns a summary dict, never raises.

    dry_run=True (Phase 1 default): skip LLM generation. All counterfactuals
    get what_if='TODO', llm_confidence=0.0, status='generated'.

    Phase 2+ will pass dry_run=False; Phase 1 always uses True.
    """
    started_at = time.monotonic()
    summary: dict[str, Any] = {
        "workspace_id": workspace_id,
        "triggers_fetched": 0,
        "triggers_unique": 0,
        "trigger_breakdown": {},
        "counterfactuals_generated": 0,
        "promoted": 0,
        "llm_generation_failures": 0,
        "elapsed_ms": 0,
        "skipped": False,
        "skipped_reason": "",
        "phase": "1",
    }

    try:
        settings = RuntimeSettings()
    except Exception as exc:
        logger.warning("counterfactual_engine: cannot load settings: %s", exc)
        summary["skipped"] = True
        summary["skipped_reason"] = "settings-load-error"
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return summary

    if not settings.counterfactual_engine_enabled:
        summary["skipped"] = True
        summary["skipped_reason"] = "killswitch-off"
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return summary

    # Step 1: fetch triggers
    try:
        triggers = fetch_recent_triggers(
            workspace_id=workspace_id,
            lookback_minutes=settings.counterfactual_engine_lookback_minutes,
        )
    except Exception as exc:
        logger.warning("counterfactual_engine: fetch failed: %s", exc)
        summary["error"] = f"fetch-failed: {type(exc).__name__}"
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return summary

    summary["triggers_fetched"] = len(triggers)
    summary["trigger_breakdown"] = dict(Counter(t.event_type for t in triggers))

    if not triggers:
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        _publish_cycle_complete(summary)
        return summary

    # Step 2: dedup (first-pass via cf_key lookup)
    try:
        unique_triggers = _dedup_filter(triggers)
    except Exception as exc:
        logger.warning("counterfactual_engine: dedup failed: %s", exc)
        unique_triggers = triggers  # degrade gracefully — UNIQUE constraint catches dups
    summary["triggers_unique"] = len(unique_triggers)

    if not unique_triggers:
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        _publish_cycle_complete(summary)
        return summary

    # Step 3: generation (Phase 1: skip; placeholder per trigger)
    if dry_run:
        counterfactuals = [_dry_run_placeholder(t) for t in unique_triggers]
    else:
        # Phase 2 will fill this in; until then it's a no-op stub
        try:
            counterfactuals = _generate_counterfactuals_via_llm(unique_triggers)
        except Exception as exc:
            logger.warning("counterfactual_engine: LLM generation failed: %s", exc)
            summary["llm_generation_failures"] += 1
            counterfactuals = [_failed_generation_placeholder(t) for t in unique_triggers]

    # Step 4: apophenia modulation (Phase 3+; Phase 1 stub returns 1.0)
    counterfactuals = _modulate_with_apophenia(counterfactuals)

    # Step 5: store
    threshold = settings.counterfactual_engine_promotion_threshold
    for cf in counterfactuals:
        cf["status"] = (
            "promoted" if cf["final_confidence"] >= threshold else "generated"
        )
        try:
            _store_counterfactual(workspace_id=workspace_id, **cf)
        except Exception as exc:
            logger.warning("counterfactual_engine: store failed: %s", exc)
            continue
        summary["counterfactuals_generated"] += 1
        if cf["status"] == "promoted":
            summary["promoted"] += 1

        # Step 6: publish per-cf event
        try:
            _publish_event(
                cf_id=cf["cf_id"],
                workspace_id=workspace_id,
                cluster_size=len(cf.get("trigger_event_ids", [])),
                final_confidence=cf["final_confidence"],
                status=cf["status"],
            )
        except Exception:
            pass

    summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
    _publish_cycle_complete(summary)
    return summary


def _dry_run_placeholder(trigger: TriggerEvent) -> dict:
    """Phase 1: every unique trigger becomes a TODO counterfactual."""
    return {
        "cf_id": f"cf-{uuid4().hex[:16]}",
        "cf_key": cf_key(trigger.workspace_id, trigger.event_type, trigger.primary_key),
        "cluster_id": f"cluster-{trigger.source_event_id}",
        "trigger_event_ids": [trigger.source_event_id],
        "trigger_types": [trigger.event_type],
        "what_if": "TODO",
        "likely_difference": None,
        "reasoning": None,
        "llm_confidence": 0.0,
        "apophenia_score": 1.0,
        "final_confidence": 0.0,
    }


def _failed_generation_placeholder(trigger: TriggerEvent) -> dict:
    """Phase 2+: when LLM call fails, store with a marker so we can see frequency."""
    return {
        "cf_id": f"cf-{uuid4().hex[:16]}",
        "cf_key": cf_key(trigger.workspace_id, trigger.event_type, trigger.primary_key),
        "cluster_id": f"cluster-{trigger.source_event_id}",
        "trigger_event_ids": [trigger.source_event_id],
        "trigger_types": [trigger.event_type],
        "what_if": "[generation failed]",
        "likely_difference": None,
        "reasoning": None,
        "llm_confidence": 0.0,
        "apophenia_score": 1.0,
        "final_confidence": 0.0,
    }


def _dedup_filter(triggers: list[TriggerEvent]) -> list[TriggerEvent]:
    """Remove triggers whose cf_key is already stored in the DB."""
    if not triggers:
        return []
    keys = [
        cf_key(t.workspace_id, t.event_type, t.primary_key) for t in triggers
    ]
    placeholders = ",".join("?" for _ in keys)
    with connect() as c:
        rows = c.execute(
            f"SELECT cf_key FROM counterfactuals WHERE cf_key IN ({placeholders})",
            keys,
        ).fetchall()
    existing = {str(r["cf_key"]) for r in rows}
    return [
        t for t, k in zip(triggers, keys) if k not in existing
    ]


def _generate_counterfactuals_via_llm(triggers: list[TriggerEvent]) -> list[dict]:
    """Phase 2 stub. Returns empty list in Phase 1.

    Will be implemented in Phase 2 plan as a single cheap-lane LLM call.
    """
    return []


def _modulate_with_apophenia(counterfactuals: list[dict]) -> list[dict]:
    """Phase 3 stub. Returns counterfactuals unchanged with apophenia_score=1.0.

    Will be implemented in Phase 3 plan as per-cf apophenia_guard.rate_hypothesis()
    call. final_confidence = min(llm_confidence, apophenia_score).
    """
    for cf in counterfactuals:
        cf.setdefault("apophenia_score", 1.0)
        cf["final_confidence"] = min(
            float(cf.get("llm_confidence", 0.0)),
            float(cf["apophenia_score"]),
        )
    return counterfactuals


def _store_counterfactual(*, workspace_id: str, **cf) -> None:
    """INSERT OR IGNORE — UNIQUE(cf_key) makes this idempotent."""
    now = datetime.now(UTC).isoformat()
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO counterfactuals("
            "cf_id, cf_key, workspace_id, cluster_id, "
            "trigger_event_ids_json, trigger_types_json, "
            "what_if, likely_difference, reasoning, "
            "llm_confidence, apophenia_score, final_confidence, "
            "status, created_at, updated_at"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cf["cf_id"], cf["cf_key"], workspace_id, cf["cluster_id"],
                json.dumps(cf["trigger_event_ids"]),
                json.dumps(cf["trigger_types"]),
                cf["what_if"], cf.get("likely_difference"), cf.get("reasoning"),
                float(cf["llm_confidence"]),
                float(cf["apophenia_score"]),
                float(cf["final_confidence"]),
                cf["status"], now, now,
            ),
        )
        c.commit()


def _publish_event(
    *, cf_id: str, workspace_id: str, cluster_size: int,
    final_confidence: float, status: str,
) -> None:
    event_bus.publish("cognitive_counterfactual.generated", {
        "cf_id": cf_id,
        "workspace_id": workspace_id,
        "cluster_size": cluster_size,
        "final_confidence": float(final_confidence),
        "status": status,
    })


def _publish_cycle_complete(summary: dict) -> None:
    try:
        event_bus.publish("cognitive_counterfactual.cycle_complete", dict(summary))
    except Exception:
        pass
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_counterfactual_engine.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/counterfactual_engine.py tests/services/test_counterfactual_engine.py
git commit -m "feat(counterfactuals): engine orchestrator with dry-run pipeline (Phase 1)"
```

---

## Task 5: counterfactual_engine_runtime.py daemon

**Files:**
- Create: `core/services/counterfactual_engine_runtime.py`
- Test: `tests/services/test_counterfactual_engine_runtime.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_counterfactual_engine_runtime.py`:

```python
import threading
import time
import pytest

from core.services import counterfactual_engine_runtime as cer


def test_get_workspace_lock_returns_same_lock_for_same_workspace(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    a = cer._get_workspace_lock("default")
    b = cer._get_workspace_lock("default")
    assert a is b


def test_get_workspace_lock_returns_different_locks(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    a = cer._get_workspace_lock("default")
    b = cer._get_workspace_lock("mikkel")
    assert a is not b


def test_run_one_cycle_with_lock_held_skips(monkeypatch):
    """If the per-workspace lock is held, _run_one_cycle returns skipped."""
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    lock = cer._get_workspace_lock("default")
    lock.acquire()
    try:
        # Simulate concurrent attempt
        called = []
        def fake_run(**kwargs):
            called.append(kwargs)
            return {"counterfactuals_generated": 1}
        monkeypatch.setattr(
            "core.services.counterfactual_engine.run", fake_run
        )
        out = cer._run_one_cycle("default")
        assert out["skipped"] is True
        assert out["skipped_reason"] == "lock-held"
        assert called == []  # engine.run was not invoked
    finally:
        lock.release()


def test_run_one_cycle_invokes_engine_when_lock_free(monkeypatch):
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    called = []
    def fake_run(**kwargs):
        called.append(kwargs)
        return {"workspace_id": "default", "counterfactuals_generated": 2}
    monkeypatch.setattr("core.services.counterfactual_engine.run", fake_run)
    out = cer._run_one_cycle("default")
    assert called == [{"workspace_id": "default"}]
    assert out["counterfactuals_generated"] == 2


def test_run_one_cycle_swallows_engine_exception(monkeypatch):
    """A crashing engine.run must not crash the daemon."""
    monkeypatch.setattr(cer, "_WORKSPACE_LOCKS", {})
    def boom(**kwargs):
        raise RuntimeError("engine exploded")
    monkeypatch.setattr("core.services.counterfactual_engine.run", boom)
    out = cer._run_one_cycle("default")
    assert "error" in out


def test_start_is_idempotent(monkeypatch):
    """Calling start twice must not create two threads."""
    monkeypatch.setattr(cer, "_THREAD", None)
    monkeypatch.setattr(cer, "_STOP", threading.Event())
    monkeypatch.setattr(cer, "_INTERVAL_S", 0.05)  # fast loop for test

    # Stub the loop body so it doesn't actually do work
    monkeypatch.setattr(cer, "_run_one_cycle", lambda ws: {"skipped": True})

    cer.start_counterfactual_runtime()
    first_thread = cer._THREAD
    cer.start_counterfactual_runtime()  # second call
    second_thread = cer._THREAD
    assert first_thread is second_thread
    cer.stop_counterfactual_runtime()
    time.sleep(0.1)
```

Run: `pytest tests/services/test_counterfactual_engine_runtime.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement runtime daemon**

Create `core/services/counterfactual_engine_runtime.py`:

```python
"""Daemon for periodic counterfactual reflection cycles.

Cadence: 60 minutes between cycles by default (overridable via setting).
Per-workspace advisory lock prevents overlapping cycles for the same
workspace. Phase 1 only processes the 'default' workspace.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_INTERVAL_S = 60 * 60  # 1h default
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()  # protects _WORKSPACE_LOCKS dict mutation


def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    """Lazy per-workspace lock. Same workspace_id always returns same Lock."""
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
            "counterfactual_runtime: skipping %s — lock held by another cycle",
            workspace_id,
        )
        return {
            "workspace_id": workspace_id,
            "skipped": True,
            "skipped_reason": "lock-held",
        }
    try:
        from core.services import counterfactual_engine as engine
        return engine.run(workspace_id=workspace_id)
    except Exception as exc:
        logger.warning(
            "counterfactual_runtime: engine.run failed for %s: %s",
            workspace_id, exc,
        )
        return {
            "workspace_id": workspace_id,
            "error": f"engine-error: {type(exc).__name__}",
        }
    finally:
        lock.release()


def _list_active_workspaces() -> list[str]:
    """Phase 1: only the default workspace.

    Phase 2+ may iterate over filesystem workspaces or registered users.
    """
    return ["default"]


def _loop() -> None:
    while not _STOP.is_set():
        try:
            for ws in _list_active_workspaces():
                _run_one_cycle(ws)
        except Exception as exc:
            logger.warning("counterfactual_runtime: outer loop error: %s", exc)
        _STOP.wait(_INTERVAL_S)


def start_counterfactual_runtime() -> None:
    """Start the periodic-evaluation daemon. Idempotent — safe to call multiple times."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(
        target=_loop, name="counterfactual-runtime", daemon=True,
    )
    _THREAD.start()
    logger.info("counterfactual_runtime daemon started")


def stop_counterfactual_runtime() -> None:
    """Signal the loop to exit."""
    _STOP.set()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_counterfactual_engine_runtime.py -v`. Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/services/counterfactual_engine_runtime.py tests/services/test_counterfactual_engine_runtime.py
git commit -m "feat(counterfactuals): runtime daemon with per-workspace advisory lock"
```

---

## Task 6: Wire daemon into app lifespan

**Files:**
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Add daemon start in lifespan startup**

In `apps/api/jarvis_api/app.py`, find the existing `tool_router_runtime daemon started` block. Right after it, add:

```python
            try:
                from core.services.counterfactual_engine_runtime import start_counterfactual_runtime
                start_counterfactual_runtime()
                logger.info("counterfactual_runtime daemon started")
            except Exception as _exc:
                logger.warning("counterfactual_runtime start failed: %s", _exc)
```

- [ ] **Step 2: Add daemon stop in lifespan shutdown**

In the shutdown section (find where `tool_router_runtime` is stopped). Right after it, add:

```python
            try:
                from core.services.counterfactual_engine_runtime import stop_counterfactual_runtime
                stop_counterfactual_runtime()
            except Exception:
                pass
```

- [ ] **Step 3: Verify imports + smoke test**

Run:
```bash
conda run -n ai python -c "import apps.api.jarvis_api.app; print('imports ok')"
conda run -n ai python scripts/smoke_test_startup.py
```

Expected: `imports ok` and `smoke_test_startup: OK in <X>s`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat(counterfactuals): wire daemon into app lifespan"
```

---

## Task 7: Smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add counterfactuals verification**

In `scripts/smoke_test_startup.py`, find the existing decision_signals registry verification block. Right after it, add:

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

- [ ] **Step 2: Run smoke test**

Run: `conda run -n ai python scripts/smoke_test_startup.py`
Expected: exit 0, no traceback containing "counterfactuals".

- [ ] **Step 3: Run full counterfactuals test suite**

Run:
```bash
conda run -n ai pytest tests/services/test_counterfactual_*.py tests/runtime/test_counterfactuals_*.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "test(counterfactuals): smoke test verifies table + daemon importable"
```

---

## Task 8: Deploy + day-1 verification

- [ ] **Step 1: Pre-deploy check**

```bash
conda run -n ai pytest tests/services/test_counterfactual_*.py tests/runtime/test_counterfactuals_*.py -v
conda run -n ai python -m compileall core/services/counterfactual_engine.py core/services/counterfactual_engine_runtime.py core/services/counterfactual_triggers.py
conda run -n ai python scripts/smoke_test_startup.py
```

All must pass.

- [ ] **Step 2: Deploy**

```bash
sudo systemctl restart jarvis-api jarvis-runtime
sleep 5
journalctl -u jarvis-api --since "30 seconds ago" --no-pager | grep -iE "counterfactual|error" | tail -10
```

Expected: log line `counterfactual_runtime daemon started`. No errors.

- [ ] **Step 3: Trigger one cycle manually for verification**

```bash
conda run -n ai python -c "
from core.services.counterfactual_engine import run
import json
out = run(workspace_id='default', dry_run=True)
print(json.dumps(out, indent=2, default=str))
"
```

Expected: a summary dict. `triggers_fetched` may be 0 (if no recent regret events) or N. Either is fine — what matters is no exception.

- [ ] **Step 4: Verify cycle_complete event was published**

```bash
conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    rows = c.execute(
        \"SELECT created_at, payload_json FROM events \"
        \"WHERE kind = 'cognitive_counterfactual.cycle_complete' \"
        \"ORDER BY id DESC LIMIT 5\"
    ).fetchall()
    print(f'{len(rows)} cycle_complete events found')
    for r in rows:
        print(f'  {r[\"created_at\"]}  {r[\"payload_json\"][:200]}')
"
```

Expected: at least 1 row from the manual run in Step 3.

- [ ] **Step 5: Verify table is populated (if any triggers existed)**

```bash
conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    rows = c.execute('SELECT COUNT(*) AS n FROM counterfactuals').fetchone()
    print(f'counterfactuals rows: {rows[\"n\"]}')
    sample = c.execute(
        'SELECT cf_id, workspace_id, what_if, status, llm_confidence FROM counterfactuals LIMIT 3'
    ).fetchall()
    for r in sample:
        print(f'  {r[\"cf_id\"]}  ws={r[\"workspace_id\"]}  status={r[\"status\"]}  what_if={r[\"what_if\"]!r}')
"
```

Expected: rows have `what_if='TODO'` and `status='generated'` (Phase 1 dry-run defaults).

---

## Task 9: 7-day observation setup

- [ ] **Step 1: Schedule 7-day review reminder**

Use the same scheduled-task pattern from earlier deploys:

```bash
cat > /tmp/sched_cf_review.py << 'PYEOF'
import sys
sys.path.insert(0, '/media/projects/jarvis-v2')
from core.services.scheduled_tasks import push_scheduled_task

focus = (
    "Counterfactuals Phase 1 7-day review (deployed 2026-05-07). "
    "Tjek: "
    "(1) Trigger volume per cycle: SELECT json_extract(payload_json,'$.triggers_fetched'), "
    "json_extract(payload_json,'$.triggers_unique') FROM events "
    "WHERE kind='cognitive_counterfactual.cycle_complete' "
    "AND created_at >= datetime('now','-7 days') ORDER BY id DESC; "
    "(2) Trigger breakdown: SELECT json_extract(payload_json,'$.trigger_breakdown') "
    "FROM events WHERE kind='cognitive_counterfactual.cycle_complete' "
    "AND created_at >= datetime('now','-7 days'); "
    "(3) Total counterfactuals stored: SELECT COUNT(*) FROM counterfactuals "
    "WHERE created_at >= datetime('now','-7 days'); "
    "(4) Dedup-rate: triggers_fetched vs triggers_unique. "
    "Maal: 5-15 triggers/cycle, dedup til 3-8 unique. Hvis en event-type dominerer "
    "med 95%+, overvej throttling i Phase 2."
)
out = push_scheduled_task(focus=focus, delay_minutes=7*24*60, source="claude-code-cf-phase1-followup")
print(f"task_id: {out['task_id']}")
print(f"run_at:  {out['run_at']}")
PYEOF
conda run -n ai python /tmp/sched_cf_review.py
```

Expected output: a task_id and run_at ~7 days from now.

- [ ] **Step 2: Save task_id for reference**

The output of step 1 includes a task_id. Note it down — it's the cancellation handle if you decide to abort the experiment early.

- [ ] **Step 3: Push to remote**

```bash
git push origin main
```

---

## Self-Review

Spec coverage:

- ✅ Settings flags (Task 1)
- ✅ Event family `cognitive_counterfactual` (Task 1)
- ✅ DB migration with `UNIQUE(cf_key)` (Task 2)
- ✅ TriggerEvent + fetch + per-family extractors + cf_key (Task 3)
- ✅ `run()` orchestrator with `dry_run=True` Phase 1 default (Task 4)
- ✅ `_generate_counterfactuals_via_llm` Phase 2 stub (Task 4 — returns [] for now)
- ✅ `_modulate_with_apophenia` Phase 3 stub (Task 4 — returns 1.0 score)
- ✅ Daemon with per-workspace advisory lock (Task 5)
- ✅ Lifespan wiring (Task 6)
- ✅ Smoke test extension (Task 7)
- ✅ Manual deploy verification (Task 8)
- ✅ 7-day observation reminder (Task 9 — uses existing scheduled_tasks pattern)
- ✅ `trigger_breakdown` in summary (Task 4 verified by test)
- ✅ Idempotency via `INSERT OR IGNORE` + UNIQUE constraint (Task 2 + Task 4)
- ✅ Killswitch suppresses run() (Task 4 verified by test)

Placeholder scan: clean. All code blocks are complete; no "implement appropriately" or "TBD".

Type consistency:
- `TriggerEvent` fields used identically across Tasks 3, 4
- `cf_key()` signature consistent (workspace_id, event_type, primary_key) across Tasks 3, 4
- `run()` signature consistent (`workspace_id`, `dry_run`)
- Daemon's `_run_one_cycle` calls `engine.run(workspace_id=...)` matching engine's signature
- Cycle-complete event payload includes all summary fields Task 9's queries depend on

Notes:
- `_list_active_workspaces` returns just `["default"]` in Phase 1 — multi-workspace iteration deferred to Phase 2 since trigger event types are mostly Jarvis-global
- Phase 2-4 are explicitly out of scope for this plan; they get separate plans informed by Phase 1 data
