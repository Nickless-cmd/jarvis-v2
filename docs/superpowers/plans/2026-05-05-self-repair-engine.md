---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Self-Repair Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runtime-instigated self-repair framework: push-style eventbus subscriber matches events against DB-backed patterns and executes allowlisted repair actions (v1: `daemon_manager.control_daemon` only) directly without going through the LLM/approval layer.

**Architecture:** Single new module `core/services/self_repair_engine.py` (~500-650 lines). Two new SQLite tables (`self_repair_patterns`, `self_repair_attempts`) in `core/runtime/db_self_repair.py` (boy-scout split from `db.py`). Listener thread subscribes to `event_bus.subscribe()`, matches each event against enabled patterns, runs cooldown/window checks, executes via direct service call, records audit + publishes eventbus events, escalates to Discord on failure, auto-disables after 3 failures in 24h.

**Tech Stack:** Python 3.11+, SQLite via existing `core/runtime/db.py`, eventbus push-subscriber pattern, `isolated_runtime` test fixture, threading for listener daemon.

**Spec:** `docs/superpowers/specs/2026-05-05-self-repair-engine-design.md`

---

## File Structure

**Create:**
- `core/runtime/db_self_repair.py` — DB helpers for `self_repair_patterns` + `self_repair_attempts` (boy scout — db.py is 33k lines)
- `core/services/self_repair_engine.py` — main module (pattern dataclass, match, cooldown, executor, listener, public API)
- `tests/test_db_self_repair.py` — DB CRUD + cooldown queries
- `tests/test_self_repair_engine.py` — engine unit tests
- `tests/test_self_repair_settings.py` — RuntimeSettings fields
- `tests/test_self_repair_integration.py` — end-to-end eventbus → match → execute

**Modify:**
- `core/runtime/db.py` — re-export new helpers from `db_self_repair.py`
- `core/runtime/settings.py` — add 6 new `self_repair_*` fields
- Runtime startup hook (identified in Task 9 via grep for `start_watcher_daemon`) — call `start_listener()` at startup alongside the existing `process_watcher` startup

---

## Task 1: RuntimeSettings fields

**Files:**
- Modify: `core/runtime/settings.py`
- Create: `tests/test_self_repair_settings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_self_repair_settings.py`:

```python
from __future__ import annotations


def test_self_repair_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.self_repair_engine_enabled is True
    assert settings.self_repair_default_cooldown_seconds == 300
    assert settings.self_repair_default_max_attempts_per_window == 3
    assert settings.self_repair_default_window_seconds == 3600
    assert settings.self_repair_default_auto_disable_after_escalations == 3
    assert settings.self_repair_default_auto_disable_window_hours == 24
```

- [ ] **Step 2: Run test to verify it fails**

```
conda activate ai
pytest tests/test_self_repair_settings.py -v
```

Expected: FAIL with `AttributeError: ... has no attribute 'self_repair_engine_enabled'`

- [ ] **Step 3: Add fields to RuntimeSettings dataclass**

In `core/runtime/settings.py`, find the section ending with the `sensory_perception_*` fields (added in previous PR) and add the 6 new fields right after them, before `extra: dict[str, Any] = field(default_factory=dict)`:

```python
    # Self-repair engine — runtime-instigated repair actions for known patterns.
    self_repair_engine_enabled: bool = True
    self_repair_default_cooldown_seconds: int = 300
    self_repair_default_max_attempts_per_window: int = 3
    self_repair_default_window_seconds: int = 3600
    self_repair_default_auto_disable_after_escalations: int = 3
    self_repair_default_auto_disable_window_hours: int = 24
```

- [ ] **Step 4: Add to to_dict()**

In `to_dict()`, after `"sensory_perception_recent_baseline_size": self.sensory_perception_recent_baseline_size,`, add:

```python
            "self_repair_engine_enabled": self.self_repair_engine_enabled,
            "self_repair_default_cooldown_seconds": self.self_repair_default_cooldown_seconds,
            "self_repair_default_max_attempts_per_window": self.self_repair_default_max_attempts_per_window,
            "self_repair_default_window_seconds": self.self_repair_default_window_seconds,
            "self_repair_default_auto_disable_after_escalations": self.self_repair_default_auto_disable_after_escalations,
            "self_repair_default_auto_disable_window_hours": self.self_repair_default_auto_disable_window_hours,
```

- [ ] **Step 5: Add to load_settings()**

In `load_settings()`, after the `sensory_perception_*` block (just before `extra={...}`), add:

```python
        self_repair_engine_enabled=bool(data.get("self_repair_engine_enabled", defaults.self_repair_engine_enabled)),
        self_repair_default_cooldown_seconds=int(data.get("self_repair_default_cooldown_seconds", defaults.self_repair_default_cooldown_seconds)),
        self_repair_default_max_attempts_per_window=int(data.get("self_repair_default_max_attempts_per_window", defaults.self_repair_default_max_attempts_per_window)),
        self_repair_default_window_seconds=int(data.get("self_repair_default_window_seconds", defaults.self_repair_default_window_seconds)),
        self_repair_default_auto_disable_after_escalations=int(data.get("self_repair_default_auto_disable_after_escalations", defaults.self_repair_default_auto_disable_after_escalations)),
        self_repair_default_auto_disable_window_hours=int(data.get("self_repair_default_auto_disable_window_hours", defaults.self_repair_default_auto_disable_window_hours)),
```

- [ ] **Step 6: Run test to verify it passes**

```
pytest tests/test_self_repair_settings.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add core/runtime/settings.py tests/test_self_repair_settings.py
git commit -m "feat(self-repair): runtime settings for engine enable + per-pattern defaults"
```

---

## Task 2: DB schema and helpers

**Files:**
- Create: `core/runtime/db_self_repair.py`
- Create: `tests/test_db_self_repair.py`
- Modify: `core/runtime/db.py` (re-export at end of file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_self_repair.py`:

```python
from __future__ import annotations


def test_insert_and_get_pattern(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1",
        name="Restart mail_checker",
        trigger_event_kind="process_watcher.matched",
        trigger_match_json='{"watch_id": "mail_checker_overdue"}',
        action_type="control_daemon",
        action_params_json='{"name": "mail_checker", "action": "restart"}',
        cooldown_seconds=300,
        max_attempts_per_window=3,
        window_seconds=3600,
        auto_disable_after_escalations=3,
        auto_disable_window_hours=24,
        source="manual",
    )
    row = get_self_repair_pattern("p1")
    assert row is not None
    assert row["name"] == "Restart mail_checker"
    assert row["trigger_event_kind"] == "process_watcher.matched"
    assert row["enabled"] == 1
    assert row["total_executed"] == 0


def test_list_patterns_filters_enabled_and_kind(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        list_self_repair_patterns,
        update_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="a", name="A", trigger_event_kind="kind.x",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_pattern(
        pattern_id="b", name="B", trigger_event_kind="kind.x",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_pattern(
        pattern_id="c", name="C", trigger_event_kind="kind.y",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("b", enabled=False)

    only_enabled = list_self_repair_patterns(enabled=True)
    ids = sorted(r["pattern_id"] for r in only_enabled)
    assert ids == ["a", "c"]

    only_x = list_self_repair_patterns(trigger_event_kind="kind.x")
    ids_x = sorted(r["pattern_id"] for r in only_x)
    assert ids_x == ["a", "b"]


def test_update_pattern_partial_fields(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        update_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="orig", trigger_event_kind="x",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("p1", enabled=False, last_outcome="executed")
    row = get_self_repair_pattern("p1")
    assert row["enabled"] == 0
    assert row["last_outcome"] == "executed"
    assert row["name"] == "orig"  # untouched


def test_update_pattern_with_increment_fields(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        update_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("p1", total_executed_increment=1)
    update_self_repair_pattern("p1", total_executed_increment=2)
    row = get_self_repair_pattern("p1")
    assert row["total_executed"] == 3


def test_insert_and_count_attempts(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        insert_self_repair_attempt,
        count_recent_attempts,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:00:00+00:00",
        triggered_by_event_id=42,
        outcome="executed",
        error_summary=None,
        elapsed_ms=15,
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:01:00+00:00",
        triggered_by_event_id=43,
        outcome="failed",
        error_summary="boom",
        elapsed_ms=22,
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:02:00+00:00",
        triggered_by_event_id=44,
        outcome="rate_limited",
        error_summary="cooldown",
        elapsed_ms=0,
    )

    # All outcomes since 09:55
    total = count_recent_attempts(
        pattern_id="p1", since_iso="2026-05-05T09:55:00+00:00",
    )
    assert total == 3

    # Only executed
    executed = count_recent_attempts(
        pattern_id="p1",
        since_iso="2026-05-05T09:55:00+00:00",
        outcome="executed",
    )
    assert executed == 1

    # Time filter excludes earlier attempts
    later = count_recent_attempts(
        pattern_id="p1", since_iso="2026-05-05T10:01:30+00:00",
    )
    assert later == 1


def test_delete_pattern(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        delete_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    assert delete_self_repair_pattern("p1") is True
    assert get_self_repair_pattern("p1") is None
    assert delete_self_repair_pattern("nonexistent") is False
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_db_self_repair.py -v
```

Expected: FAIL with `ImportError: cannot import name 'insert_self_repair_pattern' from 'core.runtime.db'`

- [ ] **Step 3: Create the DB helper module**

Create `core/runtime/db_self_repair.py`:

```python
"""DB helpers for self_repair_patterns + self_repair_attempts tables.

Split out from db.py per CLAUDE.md boy scout rule (db.py is 33k lines).
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.runtime.db import connect, _now_iso


def _ensure_self_repair_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS self_repair_patterns (
            pattern_id          TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            trigger_event_kind  TEXT NOT NULL,
            trigger_match_json  TEXT NOT NULL DEFAULT '{}',
            action_type         TEXT NOT NULL,
            action_params_json  TEXT NOT NULL DEFAULT '{}',
            enabled             INTEGER NOT NULL DEFAULT 1,
            cooldown_seconds    INTEGER NOT NULL DEFAULT 300,
            max_attempts_per_window INTEGER NOT NULL DEFAULT 3,
            window_seconds      INTEGER NOT NULL DEFAULT 3600,
            auto_disable_after_escalations INTEGER NOT NULL DEFAULT 3,
            auto_disable_window_hours      INTEGER NOT NULL DEFAULT 24,
            source              TEXT,
            source_evidence_json TEXT,
            last_attempt_at     TEXT,
            last_outcome        TEXT,
            total_executed      INTEGER NOT NULL DEFAULT 0,
            total_failed        INTEGER NOT NULL DEFAULT 0,
            total_escalated     INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_patterns_trigger
            ON self_repair_patterns (enabled, trigger_event_kind)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS self_repair_attempts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id      TEXT NOT NULL,
            attempted_at    TEXT NOT NULL,
            triggered_by_event_id INTEGER,
            outcome         TEXT NOT NULL,
            error_summary   TEXT,
            elapsed_ms      INTEGER,
            FOREIGN KEY (pattern_id) REFERENCES self_repair_patterns (pattern_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_pattern_time
            ON self_repair_attempts (pattern_id, attempted_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_self_repair_attempts_time
            ON self_repair_attempts (attempted_at DESC)
        """
    )


_INCREMENT_FIELDS = {
    "total_executed": "total_executed_increment",
    "total_failed": "total_failed_increment",
    "total_escalated": "total_escalated_increment",
}

_UPDATABLE_FIELDS = {
    "name",
    "trigger_event_kind",
    "trigger_match_json",
    "action_type",
    "action_params_json",
    "enabled",
    "cooldown_seconds",
    "max_attempts_per_window",
    "window_seconds",
    "auto_disable_after_escalations",
    "auto_disable_window_hours",
    "source",
    "source_evidence_json",
    "last_attempt_at",
    "last_outcome",
    "total_executed",
    "total_failed",
    "total_escalated",
}


def insert_self_repair_pattern(
    *,
    pattern_id: str,
    name: str,
    trigger_event_kind: str,
    trigger_match_json: str = "{}",
    action_type: str,
    action_params_json: str = "{}",
    enabled: bool = True,
    cooldown_seconds: int = 300,
    max_attempts_per_window: int = 3,
    window_seconds: int = 3600,
    auto_disable_after_escalations: int = 3,
    auto_disable_window_hours: int = 24,
    source: str | None = None,
    source_evidence_json: str | None = None,
) -> dict[str, object]:
    """UPSERT a self-repair pattern. Idempotent on pattern_id."""
    now = _now_iso()
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        conn.execute(
            """
            INSERT INTO self_repair_patterns
                (pattern_id, name, created_at, updated_at,
                 trigger_event_kind, trigger_match_json,
                 action_type, action_params_json,
                 enabled, cooldown_seconds, max_attempts_per_window,
                 window_seconds, auto_disable_after_escalations,
                 auto_disable_window_hours, source, source_evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_id) DO UPDATE SET
                name=excluded.name,
                updated_at=excluded.updated_at,
                trigger_event_kind=excluded.trigger_event_kind,
                trigger_match_json=excluded.trigger_match_json,
                action_type=excluded.action_type,
                action_params_json=excluded.action_params_json,
                enabled=excluded.enabled,
                cooldown_seconds=excluded.cooldown_seconds,
                max_attempts_per_window=excluded.max_attempts_per_window,
                window_seconds=excluded.window_seconds,
                auto_disable_after_escalations=excluded.auto_disable_after_escalations,
                auto_disable_window_hours=excluded.auto_disable_window_hours,
                source=excluded.source,
                source_evidence_json=excluded.source_evidence_json
            """,
            (
                str(pattern_id)[:120],
                str(name)[:240],
                now,
                now,
                str(trigger_event_kind)[:120],
                str(trigger_match_json or "{}"),
                str(action_type)[:60],
                str(action_params_json or "{}"),
                1 if enabled else 0,
                int(cooldown_seconds),
                int(max_attempts_per_window),
                int(window_seconds),
                int(auto_disable_after_escalations),
                int(auto_disable_window_hours),
                source,
                source_evidence_json,
            ),
        )
    return {"pattern_id": pattern_id, "created_at": now}


def get_self_repair_pattern(pattern_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        row = conn.execute(
            "SELECT * FROM self_repair_patterns WHERE pattern_id=?",
            (str(pattern_id),),
        ).fetchone()
    return _pattern_row_to_dict(row) if row is not None else None


def list_self_repair_patterns(
    *,
    enabled: bool | None = None,
    trigger_event_kind: str | None = None,
) -> list[dict[str, object]]:
    where: list[str] = []
    params: list[Any] = []
    if enabled is not None:
        where.append("enabled = ?")
        params.append(1 if enabled else 0)
    if trigger_event_kind:
        where.append("trigger_event_kind = ?")
        params.append(str(trigger_event_kind))
    sql = "SELECT * FROM self_repair_patterns"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at ASC"
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_pattern_row_to_dict(r) for r in rows]


def update_self_repair_pattern(pattern_id: str, **fields: Any) -> bool:
    """Update specific fields. Supports `<field>_increment` for atomic counters.

    Returns True if a row was updated, False otherwise.
    """
    if not fields:
        return False

    set_clauses: list[str] = []
    params: list[Any] = []
    for key, value in fields.items():
        if key in _INCREMENT_FIELDS.values():
            target = next(
                target for target, inc_name in _INCREMENT_FIELDS.items()
                if inc_name == key
            )
            set_clauses.append(f"{target} = COALESCE({target}, 0) + ?")
            params.append(int(value))
        elif key in _UPDATABLE_FIELDS:
            if key == "enabled":
                set_clauses.append(f"{key} = ?")
                params.append(1 if value else 0)
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        else:
            raise ValueError(f"unsupported field for update: {key!r}")

    set_clauses.append("updated_at = ?")
    params.append(_now_iso())
    params.append(str(pattern_id))

    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            f"UPDATE self_repair_patterns SET {', '.join(set_clauses)} WHERE pattern_id=?",
            tuple(params),
        )
        return cur.rowcount > 0


def delete_self_repair_pattern(pattern_id: str) -> bool:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            "DELETE FROM self_repair_patterns WHERE pattern_id=?",
            (str(pattern_id),),
        )
        return cur.rowcount > 0


def insert_self_repair_attempt(
    *,
    pattern_id: str,
    attempted_at: str,
    triggered_by_event_id: int | None,
    outcome: str,
    error_summary: str | None,
    elapsed_ms: int,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        cur = conn.execute(
            """
            INSERT INTO self_repair_attempts
                (pattern_id, attempted_at, triggered_by_event_id,
                 outcome, error_summary, elapsed_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(pattern_id),
                str(attempted_at),
                int(triggered_by_event_id) if triggered_by_event_id else None,
                str(outcome)[:40],
                error_summary[:240] if error_summary else None,
                int(elapsed_ms),
            ),
        )
        return {"id": int(cur.lastrowid), "attempted_at": attempted_at}


def count_recent_attempts(
    *,
    pattern_id: str,
    since_iso: str,
    outcome: str | None = None,
) -> int:
    where = ["pattern_id = ?", "attempted_at >= ?"]
    params: list[Any] = [str(pattern_id), str(since_iso)]
    if outcome is not None:
        where.append("outcome = ?")
        params.append(str(outcome))
    sql = "SELECT COUNT(*) AS n FROM self_repair_attempts WHERE " + " AND ".join(where)
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        row = conn.execute(sql, tuple(params)).fetchone()
    return int(row["n"]) if row else 0


def list_recent_self_repair_attempts(
    *, pattern_id: str | None = None, limit: int = 50,
) -> list[dict[str, object]]:
    where = ""
    params: list[Any] = []
    if pattern_id:
        where = "WHERE pattern_id = ?"
        params.append(str(pattern_id))
    sql = (
        "SELECT id, pattern_id, attempted_at, triggered_by_event_id, "
        "outcome, error_summary, elapsed_ms FROM self_repair_attempts "
        f"{where} ORDER BY attempted_at DESC LIMIT ?"
    )
    params.append(max(int(limit), 1))
    with connect() as conn:
        _ensure_self_repair_tables(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "id": int(r["id"]),
            "pattern_id": r["pattern_id"],
            "attempted_at": r["attempted_at"],
            "triggered_by_event_id": r["triggered_by_event_id"],
            "outcome": r["outcome"],
            "error_summary": r["error_summary"],
            "elapsed_ms": r["elapsed_ms"],
        }
        for r in rows
    ]


def _pattern_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "pattern_id": row["pattern_id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "trigger_event_kind": row["trigger_event_kind"],
        "trigger_match_json": row["trigger_match_json"],
        "action_type": row["action_type"],
        "action_params_json": row["action_params_json"],
        "enabled": int(row["enabled"]),
        "cooldown_seconds": int(row["cooldown_seconds"]),
        "max_attempts_per_window": int(row["max_attempts_per_window"]),
        "window_seconds": int(row["window_seconds"]),
        "auto_disable_after_escalations": int(row["auto_disable_after_escalations"]),
        "auto_disable_window_hours": int(row["auto_disable_window_hours"]),
        "source": row["source"],
        "source_evidence_json": row["source_evidence_json"],
        "last_attempt_at": row["last_attempt_at"],
        "last_outcome": row["last_outcome"],
        "total_executed": int(row["total_executed"]),
        "total_failed": int(row["total_failed"]),
        "total_escalated": int(row["total_escalated"]),
    }
```

- [ ] **Step 4: Re-export from db.py**

Append at end of `core/runtime/db.py`:

```python


# --- Self-repair engine (split into db_self_repair.py per boy scout rule) ---
from core.runtime.db_self_repair import (  # noqa: E402,F401
    insert_self_repair_pattern,
    get_self_repair_pattern,
    list_self_repair_patterns,
    update_self_repair_pattern,
    delete_self_repair_pattern,
    insert_self_repair_attempt,
    count_recent_attempts,
    list_recent_self_repair_attempts,
)
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/test_db_self_repair.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db_self_repair.py core/runtime/db.py tests/test_db_self_repair.py
git commit -m "feat(self-repair): db schema and helpers for patterns + attempts"
```

---

## Task 3: Pattern dataclass + match logic

**Files:**
- Create: `core/services/self_repair_engine.py`
- Create: `tests/test_self_repair_engine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_self_repair_engine.py`:

```python
from __future__ import annotations


def test_pattern_matches_event_exact_payload(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(
        p, {"kind": "k", "payload": {"daemon": "mail_checker"}}
    ) is True
    assert _pattern_matches_event(
        p, {"kind": "k", "payload": {"daemon": "other"}}
    ) is False


def test_pattern_does_not_match_wrong_kind(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="kind.x",
        trigger_match={}, action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(p, {"kind": "kind.y", "payload": {}}) is False


def test_pattern_does_not_match_missing_payload_key(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k", trigger_match={"key": "value"},
        action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(p, {"kind": "k", "payload": {}}) is False


def test_payload_predicate_gt(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    assert _payload_predicate_matches({"op": "gt", "value": 5}, 10) is True
    assert _payload_predicate_matches({"op": "gt", "value": 5}, 3) is False
    assert _payload_predicate_matches({"op": "gt", "value": 5}, "not-a-number") is False


def test_payload_predicate_lt(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    assert _payload_predicate_matches({"op": "lt", "value": 5}, 3) is True
    assert _payload_predicate_matches({"op": "lt", "value": 5}, 10) is False


def test_payload_predicate_in(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    p = {"op": "in", "values": ["a", "b", "c"]}
    assert _payload_predicate_matches(p, "a") is True
    assert _payload_predicate_matches(p, "z") is False


def test_payload_predicate_regex(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    p = {"op": "regex", "pattern": r"timeout"}
    assert _payload_predicate_matches(p, "upstream timeout error") is True
    assert _payload_predicate_matches(p, "all good") is False
    # Bad regex should not raise
    p_bad = {"op": "regex", "pattern": "[unclosed"}
    assert _payload_predicate_matches(p_bad, "anything") is False


def test_decode_pattern_from_db_row(isolated_runtime) -> None:
    from core.services.self_repair_engine import _decode_pattern

    row = {
        "pattern_id": "p1", "name": "X",
        "trigger_event_kind": "k",
        "trigger_match_json": '{"daemon": "mail_checker"}',
        "action_type": "control_daemon",
        "action_params_json": '{"name": "mail_checker", "action": "restart"}',
        "enabled": 1, "cooldown_seconds": 300,
        "max_attempts_per_window": 3, "window_seconds": 3600,
        "auto_disable_after_escalations": 3, "auto_disable_window_hours": 24,
        "source": "manual", "source_evidence_json": None,
    }
    p = _decode_pattern(row)
    assert p.pattern_id == "p1"
    assert p.trigger_match == {"daemon": "mail_checker"}
    assert p.action_params == {"name": "mail_checker", "action": "restart"}
    assert p.enabled is True
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.self_repair_engine'`

- [ ] **Step 3: Create the module skeleton with pattern + match**

Create `core/services/self_repair_engine.py`:

```python
"""Self-repair engine — runtime-instigated repair actions for known patterns.

Push-style eventbus subscriber matches events against DB-backed patterns
and executes allowlisted repair actions (v1: daemon_manager.control_daemon
only) directly without going through the LLM/approval layer.

See docs/superpowers/specs/2026-05-05-self-repair-engine-design.md
for the full design.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern dataclass
# ---------------------------------------------------------------------------


@dataclass
class SelfRepairPattern:
    pattern_id: str
    name: str
    trigger_event_kind: str
    trigger_match: dict[str, object]
    action_type: str
    action_params: dict[str, object]
    enabled: bool
    cooldown_seconds: int
    max_attempts_per_window: int
    window_seconds: int
    auto_disable_after_escalations: int
    auto_disable_window_hours: int
    source: str
    source_evidence: dict[str, object] | None


def _decode_pattern(row: dict) -> SelfRepairPattern:
    """Build a SelfRepairPattern from a DB row dict. May raise on malformed JSON."""
    try:
        trigger_match = json.loads(str(row.get("trigger_match_json") or "{}"))
    except Exception:
        trigger_match = {}
    try:
        action_params = json.loads(str(row.get("action_params_json") or "{}"))
    except Exception:
        action_params = {}
    source_evidence_raw = row.get("source_evidence_json")
    if source_evidence_raw:
        try:
            source_evidence = json.loads(str(source_evidence_raw))
        except Exception:
            source_evidence = None
    else:
        source_evidence = None

    return SelfRepairPattern(
        pattern_id=str(row.get("pattern_id") or ""),
        name=str(row.get("name") or ""),
        trigger_event_kind=str(row.get("trigger_event_kind") or ""),
        trigger_match=trigger_match if isinstance(trigger_match, dict) else {},
        action_type=str(row.get("action_type") or ""),
        action_params=action_params if isinstance(action_params, dict) else {},
        enabled=bool(int(row.get("enabled") or 0)),
        cooldown_seconds=int(row.get("cooldown_seconds") or 300),
        max_attempts_per_window=int(row.get("max_attempts_per_window") or 3),
        window_seconds=int(row.get("window_seconds") or 3600),
        auto_disable_after_escalations=int(row.get("auto_disable_after_escalations") or 3),
        auto_disable_window_hours=int(row.get("auto_disable_window_hours") or 24),
        source=str(row.get("source") or ""),
        source_evidence=source_evidence,
    )


# ---------------------------------------------------------------------------
# Match logic
# ---------------------------------------------------------------------------


def _pattern_matches_event(pattern: SelfRepairPattern, event: dict) -> bool:
    """True if event matches pattern's trigger_event_kind + trigger_match predicates."""
    if str(event.get("kind") or "") != pattern.trigger_event_kind:
        return False
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    for key, expected in pattern.trigger_match.items():
        actual = payload.get(key)
        if not _payload_predicate_matches(expected, actual):
            return False
    return True


def _payload_predicate_matches(expected, actual) -> bool:
    """Predicate forms supported in trigger_match values:
    - scalar (str/int/bool): exact match
    - dict {"op": "gt", "value": N}: numeric comparison
    - dict {"op": "lt", "value": N}: numeric comparison
    - dict {"op": "in", "values": [...]}: membership
    - dict {"op": "regex", "pattern": "..."}: regex on str(actual)
    """
    if isinstance(expected, dict) and "op" in expected:
        op = expected["op"]
        try:
            if op == "gt":
                return float(actual) > float(expected["value"])
            if op == "lt":
                return float(actual) < float(expected["value"])
            if op == "in":
                return actual in (expected.get("values") or [])
            if op == "regex":
                return bool(re.search(str(expected["pattern"]), str(actual)))
        except Exception:
            return False
        return False
    return expected == actual


def _now() -> datetime:
    """Indirected for monkeypatching in tests."""
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): pattern dataclass and event-match logic with predicates"
```

---

## Task 4: Action allowlist + control_daemon handler

**Files:**
- Modify: `core/services/self_repair_engine.py`
- Modify: `tests/test_self_repair_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_self_repair_engine.py`:

```python
def test_action_handlers_only_contain_allowlisted(isolated_runtime) -> None:
    from core.services.self_repair_engine import _ACTION_HANDLERS

    # v1: only control_daemon. Adding new actions requires explicit PR.
    assert set(_ACTION_HANDLERS.keys()) == {"control_daemon"}


def test_action_control_daemon_calls_daemon_manager(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import self_repair_engine as eng
    import core.services.daemon_manager as dm

    captured = {}

    def fake_control_daemon(name, action, *, interval_minutes=None):
        captured["name"] = name
        captured["action"] = action
        captured["interval_minutes"] = interval_minutes
        return {"ok": True, "name": name, "action": action}

    monkeypatch.setattr(dm, "control_daemon", fake_control_daemon)

    result = eng._action_control_daemon({
        "name": "mail_checker", "action": "restart",
    })
    assert captured == {
        "name": "mail_checker", "action": "restart", "interval_minutes": None,
    }
    assert result["ok"] is True


def test_action_control_daemon_passes_interval_minutes(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import self_repair_engine as eng
    import core.services.daemon_manager as dm

    captured = {}

    def fake_control_daemon(name, action, *, interval_minutes=None):
        captured["interval_minutes"] = interval_minutes
        return {"ok": True}

    monkeypatch.setattr(dm, "control_daemon", fake_control_daemon)

    eng._action_control_daemon({
        "name": "x", "action": "set_interval", "interval_minutes": 15,
    })
    assert captured["interval_minutes"] == 15


def test_action_control_daemon_rejects_invalid_action(isolated_runtime) -> None:
    from core.services.self_repair_engine import _action_control_daemon

    import pytest
    with pytest.raises(ValueError, match="invalid control_daemon params"):
        _action_control_daemon({"name": "x", "action": "delete-everything"})

    with pytest.raises(ValueError, match="invalid control_daemon params"):
        _action_control_daemon({"name": "", "action": "restart"})
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL — `_ACTION_HANDLERS` and `_action_control_daemon` not yet defined.

- [ ] **Step 3: Add action allowlist + handler**

Append to `core/services/self_repair_engine.py`:

```python


# ---------------------------------------------------------------------------
# Action allowlist + handlers
# ---------------------------------------------------------------------------


def _action_control_daemon(params: dict) -> dict:
    """Allowlisted handler for control_daemon. Validates params then delegates."""
    from core.services.daemon_manager import control_daemon

    name = str(params.get("name") or "")
    action = str(params.get("action") or "")
    if not name or action not in {"enable", "disable", "restart", "set_interval"}:
        raise ValueError(f"invalid control_daemon params: {params!r}")
    interval = params.get("interval_minutes")
    if interval is not None:
        interval = int(interval)
    return control_daemon(name, action, interval_minutes=interval)


_ACTION_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "control_daemon": _action_control_daemon,
    # v1: only this. Adding new actions requires explicit PR + governance review.
}
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (12 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): action allowlist with control_daemon handler"
```

---

## Task 5: Cooldown check

**Files:**
- Modify: `core/services/self_repair_engine.py`
- Modify: `tests/test_self_repair_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_self_repair_engine.py`:

```python
def test_check_cooldown_ok_when_no_recent_attempts(isolated_runtime) -> None:
    from core.runtime.db import insert_self_repair_pattern
    from core.services.self_repair_engine import _check_cooldown, _decode_pattern
    from core.runtime.db import get_self_repair_pattern

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    p = _decode_pattern(get_self_repair_pattern("p1"))
    assert _check_cooldown(p) == "ok"


def test_check_cooldown_blocks_within_cooldown_seconds(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
        insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", cooldown_seconds=300, source="manual",
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    # An executed attempt 2 min ago (within 300s cooldown)
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at=(now - timedelta(seconds=120)).isoformat(),
        triggered_by_event_id=1, outcome="executed",
        error_summary=None, elapsed_ms=10,
    )

    p = eng._decode_pattern(get_self_repair_pattern("p1"))
    reason = eng._check_cooldown(p)
    assert reason.startswith("cooldown")


def test_check_cooldown_blocks_at_window_cap(isolated_runtime, monkeypatch) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
        insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon",
        cooldown_seconds=0,  # disable cooldown for this test
        max_attempts_per_window=3, window_seconds=3600,
        source="manual",
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    # Three attempts within the 1h window (any outcome counts)
    for i, outcome in enumerate(["executed", "failed", "rate_limited"]):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=(now - timedelta(minutes=i * 10)).isoformat(),
            triggered_by_event_id=i, outcome=outcome,
            error_summary=None, elapsed_ms=5,
        )

    p = eng._decode_pattern(get_self_repair_pattern("p1"))
    reason = eng._check_cooldown(p)
    assert reason.startswith("window-cap-reached")


def test_check_cooldown_returns_db_error_on_query_failure(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import insert_self_repair_pattern, get_self_repair_pattern
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    p = eng._decode_pattern(get_self_repair_pattern("p1"))

    def boom(**kwargs):
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr(eng, "count_recent_attempts", boom)
    assert eng._check_cooldown(p) == "db-error"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL — `_check_cooldown` not yet defined.

- [ ] **Step 3: Add cooldown check**

Append to `core/services/self_repair_engine.py`:

```python


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


from core.runtime.db import count_recent_attempts


def _check_cooldown(pattern: SelfRepairPattern) -> str:
    """Return 'ok' if attempt allowed, else reason string explaining why blocked."""
    try:
        now = _now()

        # Check 1: cooldown_seconds since last EXECUTED attempt
        if pattern.cooldown_seconds > 0:
            cooldown_since = (now - timedelta(seconds=pattern.cooldown_seconds)).isoformat()
            recent_executed = count_recent_attempts(
                pattern_id=pattern.pattern_id,
                since_iso=cooldown_since,
                outcome="executed",
            )
            if recent_executed > 0:
                return f"cooldown ({pattern.cooldown_seconds}s since last execution)"

        # Check 2: max_attempts_per_window — counts ALL outcomes
        window_since = (now - timedelta(seconds=pattern.window_seconds)).isoformat()
        recent = count_recent_attempts(
            pattern_id=pattern.pattern_id,
            since_iso=window_since,
            outcome=None,
        )
        if recent >= pattern.max_attempts_per_window:
            return (
                f"window-cap-reached ({recent}/{pattern.max_attempts_per_window} "
                f"in {pattern.window_seconds}s)"
            )
        return "ok"
    except Exception as exc:
        logger.warning(
            "self_repair: cooldown check failed for %s: %s",
            pattern.pattern_id, exc,
        )
        return "db-error"  # conservative — block when in doubt
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (16 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): cooldown check with executed-cooldown and window-cap"
```

---

## Task 6: Public CRUD API + audit listing + surface

**Files:**
- Modify: `core/services/self_repair_engine.py`
- Modify: `tests/test_self_repair_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_self_repair_engine.py`:

```python
def test_register_pattern_validates_allowlist(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern

    import pytest
    with pytest.raises(ValueError, match="not in allowlist"):
        register_pattern(
            pattern_id="p1", name="x",
            trigger_event_kind="k",
            action_type="evil_action",
        )


def test_register_pattern_requires_identity_fields(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern

    import pytest
    with pytest.raises(ValueError, match="required"):
        register_pattern(
            pattern_id="", name="x",
            trigger_event_kind="k",
            action_type="control_daemon",
        )


def test_register_pattern_persists_with_settings_defaults(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern, list_patterns

    register_pattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    patterns = list_patterns()
    assert len(patterns) == 1
    p = patterns[0]
    assert p["pattern_id"] == "p1"
    assert p["enabled"] == 1
    assert p["cooldown_seconds"] == 300  # settings default


def test_enable_disable_delete_pattern(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        register_pattern, list_patterns,
        enable_pattern, disable_pattern, delete_pattern,
    )

    register_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon",
    )
    assert disable_pattern("p1") is True
    assert list_patterns(enabled=False)[0]["pattern_id"] == "p1"
    assert enable_pattern("p1") is True
    assert list_patterns(enabled=True)[0]["pattern_id"] == "p1"
    assert delete_pattern("p1") is True
    assert list_patterns() == []


def test_list_recent_attempts(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern, insert_self_repair_attempt,
    )
    from core.services.self_repair_engine import list_recent_attempts

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    for i in range(3):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=f"2026-05-05T10:0{i}:00+00:00",
            triggered_by_event_id=i, outcome="executed",
            error_summary=None, elapsed_ms=10,
        )
    rows = list_recent_attempts(limit=2)
    assert len(rows) == 2
    # DESC order
    assert rows[0]["attempted_at"] > rows[1]["attempted_at"]


def test_build_self_repair_surface_returns_overview(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        register_pattern, build_self_repair_surface,
    )

    register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
    )
    surface = build_self_repair_surface()
    assert surface["engine_enabled"] is True
    assert surface["pattern_count"] == 1
    assert surface["enabled_pattern_count"] == 1
    assert surface["patterns"][0]["pattern_id"] == "p1"
    assert "recent_attempts" in surface
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL — public API not yet defined.

- [ ] **Step 3: Implement public CRUD + surface**

Append to `core/services/self_repair_engine.py`:

```python


# ---------------------------------------------------------------------------
# Public CRUD API
# ---------------------------------------------------------------------------


from core.runtime.db import (
    insert_self_repair_pattern,
    get_self_repair_pattern,
    list_self_repair_patterns,
    update_self_repair_pattern,
    delete_self_repair_pattern,
    list_recent_self_repair_attempts,
)


def register_pattern(
    *,
    pattern_id: str,
    name: str,
    trigger_event_kind: str,
    trigger_match: dict[str, object] | None = None,
    action_type: str,
    action_params: dict[str, object] | None = None,
    enabled: bool = True,
    cooldown_seconds: int | None = None,
    max_attempts_per_window: int | None = None,
    window_seconds: int | None = None,
    auto_disable_after_escalations: int | None = None,
    auto_disable_window_hours: int | None = None,
    source: str = "manual",
    source_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    """Register a self-repair pattern. Validates action_type against allowlist.

    Defaults for governance fields come from RuntimeSettings.
    """
    if action_type not in _ACTION_HANDLERS:
        raise ValueError(
            f"action_type {action_type!r} not in allowlist: {sorted(_ACTION_HANDLERS)}"
        )
    if not pattern_id or not name or not trigger_event_kind:
        raise ValueError(
            "pattern_id, name, trigger_event_kind required (non-empty strings)"
        )

    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        cd = cooldown_seconds if cooldown_seconds is not None else int(getattr(s, "self_repair_default_cooldown_seconds", 300))
        max_w = max_attempts_per_window if max_attempts_per_window is not None else int(getattr(s, "self_repair_default_max_attempts_per_window", 3))
        win_s = window_seconds if window_seconds is not None else int(getattr(s, "self_repair_default_window_seconds", 3600))
        auto_n = auto_disable_after_escalations if auto_disable_after_escalations is not None else int(getattr(s, "self_repair_default_auto_disable_after_escalations", 3))
        auto_h = auto_disable_window_hours if auto_disable_window_hours is not None else int(getattr(s, "self_repair_default_auto_disable_window_hours", 24))
    except Exception:
        cd, max_w, win_s, auto_n, auto_h = (
            cooldown_seconds or 300,
            max_attempts_per_window or 3,
            window_seconds or 3600,
            auto_disable_after_escalations or 3,
            auto_disable_window_hours or 24,
        )

    insert_self_repair_pattern(
        pattern_id=pattern_id,
        name=name,
        trigger_event_kind=trigger_event_kind,
        trigger_match_json=json.dumps(trigger_match or {}, ensure_ascii=False),
        action_type=action_type,
        action_params_json=json.dumps(action_params or {}, ensure_ascii=False),
        enabled=enabled,
        cooldown_seconds=cd,
        max_attempts_per_window=max_w,
        window_seconds=win_s,
        auto_disable_after_escalations=auto_n,
        auto_disable_window_hours=auto_h,
        source=source,
        source_evidence_json=(
            json.dumps(source_evidence, ensure_ascii=False) if source_evidence else None
        ),
    )
    return get_self_repair_pattern(pattern_id) or {}


def list_patterns(
    *,
    enabled: bool | None = None,
    trigger_event_kind: str | None = None,
) -> list[dict[str, object]]:
    return list_self_repair_patterns(
        enabled=enabled, trigger_event_kind=trigger_event_kind,
    )


def enable_pattern(pattern_id: str) -> bool:
    return update_self_repair_pattern(pattern_id, enabled=True)


def disable_pattern(pattern_id: str) -> bool:
    return update_self_repair_pattern(pattern_id, enabled=False)


def delete_pattern(pattern_id: str) -> bool:
    return delete_self_repair_pattern(pattern_id)


def list_recent_attempts(
    *, pattern_id: str | None = None, limit: int = 50,
) -> list[dict[str, object]]:
    return list_recent_self_repair_attempts(pattern_id=pattern_id, limit=limit)


def build_self_repair_surface() -> dict[str, object]:
    """Compact surface for Mission Control consumption."""
    patterns = list_self_repair_patterns()
    enabled_count = sum(1 for p in patterns if p["enabled"])
    return {
        "engine_enabled": _engine_enabled(),
        "pattern_count": len(patterns),
        "enabled_pattern_count": enabled_count,
        "patterns": patterns,
        "recent_attempts": list_recent_self_repair_attempts(limit=20),
    }


def _engine_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "self_repair_engine_enabled", True))
    except Exception:
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (22 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): public CRUD api, audit listing, mission control surface"
```

---

## Task 7: Audit + attempt orchestrator + escalation

**Files:**
- Modify: `core/services/self_repair_engine.py`
- Modify: `tests/test_self_repair_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_self_repair_engine.py`:

```python
def test_attempt_repair_executes_action_and_records_executed(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import (
        list_recent_self_repair_attempts,
        get_self_repair_pattern,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )

    captured = {}
    def fake_handler(params):
        captured["params"] = params
        return {"ok": True}
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", fake_handler)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(
        pattern,
        {"id": 99, "kind": "k", "payload": {"daemon": "mail_checker"}},
    )

    assert captured["params"] == {"name": "mail_checker", "action": "restart"}
    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"
    assert attempts[0]["triggered_by_event_id"] == 99
    # No Discord notification on success
    assert notify_calls == []


def test_attempt_repair_records_failed_on_handler_exception(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts, get_self_repair_pattern
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )

    def boom(params):
        raise RuntimeError("backend on fire")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "on fire" in attempts[0]["error_summary"]
    # Discord notification on failure
    assert len(notify_calls) == 1
    assert "Self-repair failed" in notify_calls[0]


def test_attempt_repair_skips_when_action_not_in_allowlist(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts, get_self_repair_pattern
    from core.services import self_repair_engine as eng

    # Bypass register's allowlist by inserting directly
    from core.runtime.db import insert_self_repair_pattern
    insert_self_repair_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="ghost_action", source="manual",
    )

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "unknown action_type" in attempts[0]["error_summary"]


def test_attempt_repair_skips_when_cooldown_blocks(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import (
        list_recent_self_repair_attempts, get_self_repair_pattern,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setattr(eng, "_check_cooldown", lambda p: "cooldown (test)")

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    assert handler_called == []
    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert attempts[0]["outcome"] == "rate_limited"


def test_record_failed_triggers_auto_disable_at_threshold(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        get_self_repair_pattern, insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        cooldown_seconds=0,
        max_attempts_per_window=10,  # don't block on window cap
        auto_disable_after_escalations=3,
        auto_disable_window_hours=24,
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    # Two prior failures
    for i in range(2):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=(now - timedelta(hours=i + 1)).isoformat(),
            triggered_by_event_id=i, outcome="failed",
            error_summary="prior", elapsed_ms=5,
        )

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    def boom(params):
        raise RuntimeError("third failure")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 99, "kind": "k", "payload": {}})

    after = get_self_repair_pattern("p1")
    assert after["enabled"] == 0
    assert after["last_outcome"] == "auto_disabled"
    # Two notifications: one for failed, one for auto-disabled
    assert any("auto-disabled" in m for m in notify_calls)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL — `_attempt_repair`, `_notify_owner_async` etc. not yet defined.

- [ ] **Step 3: Implement audit + attempt orchestrator**

Append to `core/services/self_repair_engine.py`:

```python


# ---------------------------------------------------------------------------
# Audit + attempt orchestration
# ---------------------------------------------------------------------------


from core.eventbus.bus import event_bus
from core.runtime.db import insert_self_repair_attempt


def _notify_owner_async(message: str) -> None:
    """Best-effort Discord DM to owner. Failure is silently swallowed."""
    try:
        from core.services.discord_gateway import send_dm_to_owner
        send_dm_to_owner(message)
    except Exception as exc:
        logger.debug("self_repair: notify_owner failed: %s", exc)


def _record_executed(
    pattern: SelfRepairPattern,
    triggered_by: int,
    result: dict,
    elapsed_ms: int,
) -> None:
    try:
        insert_self_repair_attempt(
            pattern_id=pattern.pattern_id,
            attempted_at=_now_iso(),
            triggered_by_event_id=triggered_by,
            outcome="executed",
            error_summary=None,
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:
        logger.warning("self_repair: audit insert failed: %s", exc)
    try:
        update_self_repair_pattern(
            pattern.pattern_id,
            last_attempt_at=_now_iso(),
            last_outcome="executed",
            total_executed_increment=1,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "self_repair.action_executed",
            {
                "pattern_id": pattern.pattern_id,
                "name": pattern.name,
                "action_type": pattern.action_type,
                "action_params": pattern.action_params,
                "elapsed_ms": elapsed_ms,
                "result": result,
            },
        )
    except Exception:
        pass
    logger.info(
        "self_repair: executed %s (%s) elapsed=%dms",
        pattern.pattern_id, pattern.action_type, elapsed_ms,
    )


def _record_attempt_and_escalate(
    pattern: SelfRepairPattern,
    triggered_by: int,
    *,
    outcome: str,
    error: str,
    elapsed_ms: int,
) -> None:
    try:
        insert_self_repair_attempt(
            pattern_id=pattern.pattern_id,
            attempted_at=_now_iso(),
            triggered_by_event_id=triggered_by,
            outcome=outcome,
            error_summary=error[:240],
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:
        logger.warning("self_repair: audit insert failed: %s", exc)
    try:
        update_self_repair_pattern(
            pattern.pattern_id,
            last_attempt_at=_now_iso(),
            last_outcome=outcome,
            total_failed_increment=1,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "self_repair.action_failed",
            {
                "pattern_id": pattern.pattern_id,
                "name": pattern.name,
                "action_type": pattern.action_type,
                "error": error,
                "elapsed_ms": elapsed_ms,
            },
        )
    except Exception:
        pass
    logger.warning(
        "self_repair: %s failed for %s: %s",
        pattern.action_type, pattern.pattern_id, error,
    )

    _notify_owner_async(
        f"⚠️ Self-repair failed: {pattern.name}\n"
        f"Action: {pattern.action_type} → {error[:120]}"
    )

    # Escalation check
    try:
        escalation_window_since = (
            _now() - timedelta(hours=pattern.auto_disable_window_hours)
        ).isoformat()
        failures = count_recent_attempts(
            pattern_id=pattern.pattern_id,
            since_iso=escalation_window_since,
            outcome="failed",
        )
        if failures >= pattern.auto_disable_after_escalations:
            _auto_disable_pattern(pattern, failures)
    except Exception as exc:
        logger.warning("self_repair: escalation check failed: %s", exc)


def _auto_disable_pattern(pattern: SelfRepairPattern, failure_count: int) -> None:
    try:
        update_self_repair_pattern(
            pattern.pattern_id,
            enabled=False,
            last_outcome="auto_disabled",
            total_escalated_increment=1,
        )
    except Exception as exc:
        logger.warning("self_repair: auto_disable update failed: %s", exc)
    try:
        event_bus.publish(
            "self_repair.escalated",
            {
                "pattern_id": pattern.pattern_id,
                "name": pattern.name,
                "failure_count": failure_count,
                "window_hours": pattern.auto_disable_window_hours,
            },
        )
    except Exception:
        pass
    logger.error(
        "self_repair: auto-disabled %s after %d failures in %dh",
        pattern.pattern_id, failure_count, pattern.auto_disable_window_hours,
    )
    _notify_owner_async(
        f"🚨 Self-repair auto-disabled: {pattern.name}\n"
        f"Failed {failure_count} times in {pattern.auto_disable_window_hours}h. "
        f"Re-enable manually."
    )


def _attempt_repair(pattern: SelfRepairPattern, event: dict) -> None:
    """Run cooldown check, execute action, record audit, escalate if needed."""
    triggered_by = int(event.get("id") or 0)
    cooldown_status = _check_cooldown(pattern)
    if cooldown_status != "ok":
        try:
            insert_self_repair_attempt(
                pattern_id=pattern.pattern_id,
                attempted_at=_now_iso(),
                triggered_by_event_id=triggered_by,
                outcome="rate_limited",
                error_summary=cooldown_status,
                elapsed_ms=0,
            )
        except Exception:
            pass
        try:
            event_bus.publish(
                "self_repair.rate_limited",
                {"pattern_id": pattern.pattern_id, "reason": cooldown_status},
            )
        except Exception:
            pass
        return

    started = time.monotonic()
    handler = _ACTION_HANDLERS.get(pattern.action_type)
    if handler is None:
        _record_attempt_and_escalate(
            pattern, triggered_by,
            outcome="failed",
            error=f"unknown action_type: {pattern.action_type}",
            elapsed_ms=0,
        )
        return

    try:
        result = handler(pattern.action_params)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _record_executed(pattern, triggered_by, result, elapsed_ms)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _record_attempt_and_escalate(
            pattern, triggered_by,
            outcome="failed",
            error=str(exc)[:240] or type(exc).__name__,
            elapsed_ms=elapsed_ms,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (27 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): audit functions, attempt orchestrator, escalation, auto-disable"
```

---

## Task 8: Event processor + listener daemon

**Files:**
- Modify: `core/services/self_repair_engine.py`
- Modify: `tests/test_self_repair_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_self_repair_engine.py`:

```python
def test_engine_disabled_skips_all_processing(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.runtime import settings as settings_mod
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.self_repair_engine_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    eng._process_event({"id": 1, "kind": "k", "payload": {}})
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_unknown_event_kind_skipped_silently(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="kind.x",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})

    eng._process_event({"id": 1, "kind": "kind.y", "payload": {}})
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_process_event_runs_matching_pattern(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="kind.x",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})

    eng._process_event({
        "id": 99, "kind": "kind.x", "payload": {"daemon": "mail_checker"},
    })

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"


def test_listener_starts_and_stops_cleanly(isolated_runtime) -> None:
    import time
    from core.services import self_repair_engine as eng

    eng.start_listener()
    assert eng._LISTENER_THREAD is not None
    assert eng._LISTENER_THREAD.is_alive()

    eng.stop_listener()
    # Wait up to 3s for thread to exit
    for _ in range(30):
        if not eng._LISTENER_THREAD.is_alive():
            break
        time.sleep(0.1)
    assert not eng._LISTENER_THREAD.is_alive()
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: FAIL — `_process_event`, `start_listener`, `stop_listener` not yet defined.

- [ ] **Step 3: Implement event processor + listener**

Append to `core/services/self_repair_engine.py`:

```python


# ---------------------------------------------------------------------------
# Event processor + listener daemon
# ---------------------------------------------------------------------------


import queue


_LISTENER_THREAD: threading.Thread | None = None
_LISTENER_STOP = threading.Event()
_LISTENER_QUEUE: "queue.Queue[dict[str, Any] | None] | None" = None


def _process_event(event: dict) -> None:
    """Match event against enabled patterns, execute if any match."""
    if not _engine_enabled():
        return

    event_kind = str(event.get("kind") or "")
    if not event_kind:
        return

    try:
        patterns = list_self_repair_patterns(
            enabled=True, trigger_event_kind=event_kind,
        )
    except Exception as exc:
        logger.warning("self_repair: list_patterns failed: %s", exc)
        return

    for raw_pattern in patterns:
        try:
            pattern = _decode_pattern(raw_pattern)
        except Exception:
            continue
        if not _pattern_matches_event(pattern, event):
            continue
        _attempt_repair(pattern, event)


def start_listener() -> None:
    """Start the eventbus listener daemon. Idempotent."""
    global _LISTENER_THREAD, _LISTENER_QUEUE
    if _LISTENER_THREAD is not None and _LISTENER_THREAD.is_alive():
        return
    _LISTENER_STOP.clear()
    _LISTENER_QUEUE = event_bus.subscribe()
    _LISTENER_THREAD = threading.Thread(
        target=_listener_loop,
        args=(_LISTENER_QUEUE,),
        daemon=True,
        name="self-repair-engine-listener",
    )
    _LISTENER_THREAD.start()
    logger.info("self_repair_engine: listener started")


def stop_listener() -> None:
    """Signal the listener to exit. Best-effort."""
    _LISTENER_STOP.set()
    if _LISTENER_QUEUE is not None:
        try:
            _LISTENER_QUEUE.put(None)  # poison pill
        except Exception:
            pass


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    while not _LISTENER_STOP.is_set():
        try:
            item = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if item is None:
            break
        try:
            _process_event(item)
        except Exception as exc:
            logger.warning("self_repair_engine: process_event failed: %s", exc)
    logger.info("self_repair_engine: listener stopped")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_self_repair_engine.py -v
```

Expected: PASS (31 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/self_repair_engine.py tests/test_self_repair_engine.py
git commit -m "feat(self-repair): event processor and push-style listener daemon"
```

---

## Task 9: Wire start_listener into runtime startup

**Files:**
- Modify: runtime startup hook (find via grep — typically `apps/api/jarvis_api/app.py` or runtime init)

- [ ] **Step 1: Find the startup wiring point**

Grep for the existing process_watcher startup wiring:

```
grep -rn "start_watcher_daemon\|process_watcher.*start" apps/ core/ --include="*.py"
```

Expected: At least one match in runtime startup (typically `apps/api/jarvis_api/app.py` lifespan or `core/services/runtime_*` startup).

Open the file. Look for the function that calls `process_watcher.start_watcher_daemon()` (or similar). That's where we wire `self_repair_engine.start_listener()`.

- [ ] **Step 2: Add the wiring**

Inside the same startup function, alongside the `process_watcher` call, add:

```python
try:
    from core.services.self_repair_engine import start_listener
    start_listener()
except Exception as exc:
    logger.warning("self_repair_engine startup failed: %s", exc)
```

(Use the existing logger in that file; if there's no logger yet, import logging and create one.)

If the startup function is paired with a shutdown function, add corresponding cleanup:

```python
try:
    from core.services.self_repair_engine import stop_listener
    stop_listener()
except Exception:
    pass
```

- [ ] **Step 3: Verify by importing and running compileall**

```
conda run -n ai python -c "from core.services.self_repair_engine import start_listener, stop_listener; print('imports ok')"
conda run -n ai python -m compileall apps/api core 2>&1 | tail -3
```

Expected: prints `imports ok` and compileall returns 0.

- [ ] **Step 4: Commit**

```bash
git add <touched file(s)>
git commit -m "feat(self-repair): wire start_listener into runtime startup alongside process_watcher"
```

---

## Task 10: End-to-end integration test

**Files:**
- Create: `tests/test_self_repair_integration.py`

- [ ] **Step 1: Write the integration tests**

Create `tests/test_self_repair_integration.py`:

```python
from __future__ import annotations


def test_eventbus_publish_triggers_matched_pattern_action(
    isolated_runtime, monkeypatch,
) -> None:
    """End-to-end: register pattern → start listener → publish matching event →
    handler called → audit row created → eventbus action_executed event fired."""
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="test.self_repair.trigger",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
        cooldown_seconds=0,
    )

    handler_calls = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_calls.append(params) or {"ok": True},
    )

    eng.start_listener()
    try:
        event_bus.publish(
            "test.self_repair.trigger",
            {"daemon": "mail_checker"},
        )
        # Poll for audit row up to 2s
        attempts = []
        for _ in range(20):
            attempts = list_recent_self_repair_attempts(pattern_id="p1")
            if attempts:
                break
            time.sleep(0.1)
    finally:
        eng.stop_listener()

    assert len(handler_calls) == 1
    assert handler_calls[0] == {"name": "mail_checker", "action": "restart"}
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"


def test_disabled_pattern_does_not_fire(isolated_runtime, monkeypatch) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="test.disabled",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
        enabled=False,
    )

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    eng.start_listener()
    try:
        event_bus.publish("test.disabled", {})
        time.sleep(0.5)  # give listener a moment
    finally:
        eng.stop_listener()

    assert handler_called == []
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_matched_event_for_disabled_engine_does_nothing(
    isolated_runtime, monkeypatch,
) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.runtime import settings as settings_mod
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="test.engine_off",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.self_repair_engine_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    eng.start_listener()
    try:
        event_bus.publish("test.engine_off", {})
        time.sleep(0.5)
    finally:
        eng.stop_listener()

    assert handler_called == []
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_failed_action_publishes_failure_event_and_pings_owner(
    isolated_runtime, monkeypatch,
) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="test.fail",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
        cooldown_seconds=0,
    )

    def boom(params):
        raise RuntimeError("test failure")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    eng.start_listener()
    try:
        event_bus.publish("test.fail", {})
        attempts = []
        for _ in range(20):
            attempts = list_recent_self_repair_attempts(pattern_id="p1")
            if attempts:
                break
            time.sleep(0.1)
    finally:
        eng.stop_listener()

    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "test failure" in attempts[0]["error_summary"]
    assert any("Self-repair failed" in m for m in notify_calls)
```

- [ ] **Step 2: Run integration tests**

```
pytest tests/test_self_repair_integration.py -v
```

Expected: PASS (4 tests).

If the listener tests are flaky on slow machines, increase polling timeout in the test from 20×100ms to 40×100ms.

- [ ] **Step 3: Commit**

```bash
git add tests/test_self_repair_integration.py
git commit -m "test(self-repair): end-to-end integration covering full pipeline"
```

---

## Task 11: Final smoke + CI verification

**Files:** No new files — final validation pass.

- [ ] **Step 1: Run the full self-repair test suite**

```
conda activate ai
pytest tests/test_self_repair_settings.py \
       tests/test_db_self_repair.py \
       tests/test_self_repair_engine.py \
       tests/test_self_repair_integration.py \
       -v
```

Expected: ALL PASS (~40+ tests).

- [ ] **Step 2: Run adjacent suites to catch regressions**

```
pytest tests/test_perceptual_event_engine.py \
       tests/test_emotional_memory_engine.py \
       tests/test_emotional_memory_integration.py \
       tests/test_cognitive_conductor.py \
       tests/test_sensory_perception_bridge.py \
       tests/test_sensory_perception_integration.py \
       -v
```

Expected: ALL PASS — none of these modules should regress.

- [ ] **Step 3: Syntax smoke (CI mirror)**

```
python -m compileall core apps/api scripts
```

Expected: Exit code 0.

- [ ] **Step 4: Manual end-to-end smoke (optional but recommended)**

In a Python REPL with `conda activate ai`:

```python
from core.services.self_repair_engine import (
    register_pattern, list_patterns, build_self_repair_surface, _ACTION_HANDLERS,
)
print("allowlist:", sorted(_ACTION_HANDLERS))
print("patterns before:", list_patterns())

# Register a no-op pattern (action will succeed if mail_checker daemon exists)
# To test without affecting prod, leave this commented unless you know what you're doing:
# register_pattern(
#     pattern_id="smoke-test",
#     name="smoke",
#     trigger_event_kind="smoke.test.kind",
#     action_type="control_daemon",
#     action_params={"name": "mail_checker", "action": "restart"},
# )

surface = build_self_repair_surface()
print("engine_enabled:", surface["engine_enabled"])
print("pattern_count:", surface["pattern_count"])
```

Expected: prints `allowlist: ['control_daemon']`, `engine_enabled: True`, `pattern_count: 0` (assuming no patterns registered yet).

- [ ] **Step 5: Final commit if anything was tweaked during smoke**

```bash
git status
# If changes:
git add <files>
git commit -m "fix(self-repair): smoke-test corrections"
```

- [ ] **Step 6: Push branch / open PR**

User's call — do not push without explicit confirmation.

---

## Self-review notes

1. **Spec coverage:** Every spec section maps to one or more tasks:
   - *Architecture overview* → T2 (DB), T3 (skeleton), T8 (listener), T9 (wiring)
   - *Data model* → T2
   - *Pattern definition + matching* → T3
   - *Action allowlist* → T4
   - *Cooldown / escalation / auto-disable* → T5 (cooldown), T7 (escalation + auto-disable)
   - *Listener daemon + execution flow* → T7 (attempt orchestrator), T8 (listener)
   - *Settings + governance + public API* → T1 (settings), T6 (CRUD + surface)
   - *Error handling* → woven through T5, T7, T8 with try/except guards
   - *Testing strategy* → all tasks (TDD) + T10 (integration)
   - *Future extensions* → not implemented (explicitly v2)

2. **Type/method consistency:**
   - `SelfRepairPattern` dataclass defined in T3, consumed unchanged in T5, T7, T8.
   - `_ACTION_HANDLERS` dict defined in T4, consumed in T7 attempt and T6 register validation.
   - `_check_cooldown` defined in T5, consumed in T7's `_attempt_repair`.
   - `_notify_owner_async` signature consistent (one positional `message: str`).
   - `_record_executed` and `_record_attempt_and_escalate` parameter names match between definition (T7) and call sites in `_attempt_repair`.

3. **No placeholders.** All steps contain runnable code or exact commands. T9 has one "find via grep" step which is necessary because the runtime startup wiring location varies and is verified at implementation time.
