---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Causal Graph Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stå et causal graph-lag op oven på den eksisterende events-tabel, så Jarvis kan besvare "hvorfor skete X?" og counterfactuals kan ræsonnere over ægte kausal-data.

**Architecture:** Separat `causal_edges` tabel med edges mellem event-id'er. Hybrid-population: eksplicit via udvidet `event_bus.publish(..., caused_by=N)` (auto-pickup fra `EventContext` ContextVar) og inferens via daemon med tre confidence-tiers (kind-rule 0.9 / shared-id 0.8 / temporal 0.4). Counterfactuals two-way integration: forward-query graf for hypothetiske downstream prunes + emit counterfactual-events med eksplicit caused_by.

**Tech Stack:** Python 3.11, SQLite (eksisterende `events` tabel), threading + contextvars, pytest, eksisterende `core.eventbus.bus.event_bus` infrastruktur.

**Spec:** `docs/superpowers/specs/2026-05-08-causal-graph-design.md` (revised med Jarvis' 6 review-punkter)

---

## File Structure

**Nye filer:**
- `core/eventbus/context.py` — `EventContext` ContextVar + getter/setter
- `core/services/causal_inference_daemon.py` — three-tier matching daemon
- `core/services/causal_graph.py` — query API (`query_causal_chain`, `query_causal_neighbors`, helpers)
- `core/services/prompt_sections/causal_alerts.py` — failure-event awareness injection
- `tests/test_causal_graph.py` — comprehensive test suite

**Filer der modificeres:**
- `core/runtime/db.py` — `_ensure_causal_edges_table()` migration + opkald i migration sequence
- `core/eventbus/bus.py` — `publish()` udvidet med `caused_by` + `edge_kind` + auto-pickup fra ContextVar
- `core/eventbus/events.py` — tilføj `"causal"` til `ALLOWED_EVENT_FAMILIES`
- `core/services/daemon_manager.py` — registrér `causal_inference` daemon (cadence 15 min)
- `core/services/counterfactual_engine.py` — two-way integration (forward-query + caused_by på emit)
- `core/services/visible_runs.py` — sæt EventContext for agentic-rounds
- `core/services/prompt_contract.py` — wire `causal_alerts.causal_alerts_section()` ind som awareness item
- `core/tools/simple_tools.py` — registrér `query_why` tool

---

## Task 1: DB-migration — causal_edges tabel

**Files:**
- Modify: `core/runtime/db.py` (tilføj `_ensure_causal_edges_table` + kald i migration-sekvens omkring line 1109)
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test for tabel-skema**

```python
# tests/test_causal_graph.py
def test_causal_edges_table_exists_with_correct_schema():
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        cols = {r["name"]: r["type"] for r in c.execute(
            "PRAGMA table_info(causal_edges)"
        ).fetchall()}
    assert "child_event_id" in cols
    assert "parent_event_id" in cols
    assert "edge_kind" in cols
    assert "confidence" in cols
    assert "source" in cols
    assert "reasoning" in cols
    assert "created_at" in cols


def test_causal_edges_unique_constraint():
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) "
            "VALUES (1, 2, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:00Z')"
        )
        # Insert duplicate — should fail via UNIQUE constraint
        import sqlite3
        try:
            c.execute(
                "INSERT INTO causal_edges (child_event_id, parent_event_id, "
                "edge_kind, confidence, source, created_at) "
                "VALUES (1, 2, 'triggered', 0.9, 'inferred-kind', '2026-05-08T00:00:01Z')"
            )
            assert False, "expected UNIQUE constraint violation"
        except sqlite3.IntegrityError:
            pass
        # Cleanup so test is rerunnable
        c.execute("DELETE FROM causal_edges WHERE child_event_id = 1")
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py::test_causal_edges_table_exists_with_correct_schema -v`
Expected: ImportError eller `cannot import name '_ensure_causal_edges_table'`

- [ ] **Step 3: Implementér _ensure_causal_edges_table i db.py**

Indsæt FØR `def _ensure_tool_router_tables(conn:` (omkring line 1147):

```python
def _ensure_causal_edges_table(conn: sqlite3.Connection) -> None:
    """Create causal_edges table for the causal graph layer.

    Tracks parent→child relationships between events, both explicitly
    instrumented (source='explicit') and inferred by causal_inference_daemon
    (source='inferred-kind' | 'inferred-id' | 'inferred-temporal').

    UNIQUE(child, parent, edge_kind) prevents dupes; daemon UPDATE'er
    confidence opadrettet hvis stærkere evidens dukker op senere.

    Idempotent — kan kaldes flere gange uden fejl.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_event_id  INTEGER NOT NULL,
            parent_event_id INTEGER NOT NULL,
            edge_kind       TEXT NOT NULL,
            confidence      REAL NOT NULL,
            source          TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            reasoning       TEXT NOT NULL DEFAULT '',
            UNIQUE(child_event_id, parent_event_id, edge_kind)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_causal_edges_child "
        "ON causal_edges(child_event_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_causal_edges_parent "
        "ON causal_edges(parent_event_id)"
    )
```

Tilføj kald i den eksisterende migration-sekvens omkring line 1109:

```python
        _ensure_decision_trigger_column(conn)
        _ensure_chat_messages_reasoning_column(conn)
        _ensure_counterfactuals_table(conn)
        _ensure_causal_edges_table(conn)  # ← ny linje
        from core.runtime.db_claude_dispatch import ensure_claude_dispatch_tables
```

- [ ] **Step 4: Kør tests — skal nu passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "causal_edges"`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): add causal_edges table migration"
```

---

## Task 2: EventContext via ContextVar

**Files:**
- Create: `core/eventbus/context.py`
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test**

```python
# tests/test_causal_graph.py — append
def test_event_context_default_is_none():
    from core.eventbus.context import get_current_event
    assert get_current_event() is None


def test_event_context_set_and_reset():
    from core.eventbus.context import set_current_event, get_current_event
    token = set_current_event(42)
    try:
        assert get_current_event() == 42
    finally:
        from core.eventbus.context import _current_event_context
        _current_event_context.reset(token)
    assert get_current_event() is None


def test_event_context_with_helper():
    from core.eventbus.context import with_event_context, get_current_event
    assert get_current_event() is None
    with with_event_context(99):
        assert get_current_event() == 99
        with with_event_context(100):
            assert get_current_event() == 100
        assert get_current_event() == 99
    assert get_current_event() is None
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "event_context"`
Expected: `ModuleNotFoundError: No module named 'core.eventbus.context'`

- [ ] **Step 3: Skriv `core/eventbus/context.py`**

```python
"""EventContext — ContextVar holding the current parent event_id.

Producers (tool_router, agentic_round, channel-handlers) sætter context
før de dispatcher arbejde til services. Services kalder event_bus.publish()
som normalt; bus læser context auto via get_current_event() og bruger
den som default for caused_by hvis ikke eksplicit angivet.

Contextvars er thread-local + asyncio-safe — hver request/koroutine får
sin egen value uden interference.
"""
from __future__ import annotations

import contextlib
import contextvars

_current_event_context: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_event_context",
    default=None,
)


def set_current_event(event_id: int | None) -> contextvars.Token:
    """Set parent-event-id for the current dispatch scope.

    Returns Token to use with _current_event_context.reset() later.
    Prefer with_event_context() helper for cleanest pattern.
    """
    return _current_event_context.set(event_id)


def get_current_event() -> int | None:
    """Return current parent-event-id, or None if none active."""
    return _current_event_context.get()


@contextlib.contextmanager
def with_event_context(event_id: int | None):
    """Context manager that sets and reliably resets EventContext.

    Usage:
        with with_event_context(parent_event_id):
            do_work()  # any publish() inside picks up parent automatically
    """
    token = _current_event_context.set(event_id)
    try:
        yield
    finally:
        _current_event_context.reset(token)
```

- [ ] **Step 4: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "event_context"`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add core/eventbus/context.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): EventContext ContextVar for caused_by auto-pickup"
```

---

## Task 3: event_bus.publish() udvidet med caused_by + edge_kind

**Files:**
- Modify: `core/eventbus/bus.py` (publish-signatur + edge-write)
- Modify: `core/eventbus/events.py` (tilføj "causal" family)
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test for explicit caused_by + auto-pickup**

```python
# tests/test_causal_graph.py — append
def test_publish_with_explicit_caused_by_writes_edge():
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        # Create a parent event manually so we have a real id
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.test_parent', '{}', '2026-05-08T00:00:00Z')"
        )
        parent_id = int(cur.lastrowid)
        c.commit()
    event_bus.publish(
        "runtime.test_child",
        {"x": 1},
        caused_by=parent_id,
        edge_kind="triggered",
    )
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE parent_event_id = ?",
            (parent_id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["edge_kind"] == "triggered"
    assert rows[0]["source"] == "explicit"
    assert rows[0]["confidence"] == 1.0


def test_publish_auto_pickup_from_event_context():
    from core.eventbus.bus import event_bus
    from core.eventbus.context import with_event_context
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.ctx_parent', '{}', '2026-05-08T00:00:00Z')"
        )
        parent_id = int(cur.lastrowid)
        c.commit()
    with with_event_context(parent_id):
        event_bus.publish("runtime.ctx_child", {"y": 2})
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE parent_event_id = ?",
            (parent_id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "explicit"
    assert rows[0]["edge_kind"] == "triggered"  # default når ikke specifik


def test_publish_explicit_overrides_context():
    from core.eventbus.bus import event_bus
    from core.eventbus.context import with_event_context
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.override_ctx', '{}', '2026-05-08T00:00:00Z')"
        )
        ctx_id = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.override_explicit', '{}', '2026-05-08T00:00:00Z')"
        )
        explicit_id = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    with with_event_context(ctx_id):
        event_bus.publish(
            "runtime.override_child",
            {"z": 3},
            caused_by=explicit_id,
        )
    with connect() as c:
        rows = c.execute(
            "SELECT parent_event_id FROM causal_edges "
            "WHERE parent_event_id IN (?, ?)",
            (ctx_id, explicit_id),
        ).fetchall()
    parents = {int(r["parent_event_id"]) for r in rows}
    assert parents == {explicit_id}, f"explicit should override context: {parents}"


def test_publish_caused_by_list_creates_multiple_edges():
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.multi_p1', '{}', '2026-05-08T00:00:00Z')"
        )
        p1 = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.multi_p2', '{}', '2026-05-08T00:00:00Z')"
        )
        p2 = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    event_bus.publish(
        "runtime.multi_child", {"v": 1}, caused_by=[p1, p2],
    )
    with connect() as c:
        rows = c.execute(
            "SELECT parent_event_id FROM causal_edges "
            "WHERE parent_event_id IN (?, ?)", (p1, p2),
        ).fetchall()
    assert {int(r["parent_event_id"]) for r in rows} == {p1, p2}
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "publish"`
Expected: 4 fails (caused_by ikke kendt parameter, edges ikke skrevet)

- [ ] **Step 3: Tilføj "causal" til ALLOWED_EVENT_FAMILIES**

I `core/eventbus/events.py`, find blokken med `"identity",        # identity_drift_daemon` og tilføj:

```python
    "identity",         # identity_drift_daemon (added 2026-05-08)
    "causal",           # causal_graph subsystem (added 2026-05-08)
```

- [ ] **Step 4: Udvid publish() i bus.py**

Erstat `publish()`-metoden (line 17-37) med:

```python
    def publish(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        caused_by: int | list[int] | None = None,
        edge_kind: str = "triggered",
    ) -> None:
        # Auto-pickup parent from EventContext if caller didn't specify.
        # Explicit caused_by always wins over context.
        if caused_by is None:
            try:
                from core.eventbus.context import get_current_event
                caused_by = get_current_event()
            except Exception:
                caused_by = None

        event = Event.create(kind=kind, payload=payload)
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        created_at = event.ts.isoformat()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (kind, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    event.kind,
                    payload_json,
                    created_at,
                ),
            )
            event_id = int(cursor.lastrowid)
            # Write causal edges if parent(s) given. Best-effort —
            # never let edge-write break event publication.
            if caused_by is not None:
                parents = caused_by if isinstance(caused_by, list) else [caused_by]
                for pid in parents:
                    try:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO causal_edges
                            (child_event_id, parent_event_id, edge_kind,
                             confidence, source, created_at, reasoning)
                            VALUES (?, ?, ?, 1.0, 'explicit', ?, '')
                            """,
                            (event_id, int(pid), edge_kind, created_at),
                        )
                    except Exception:
                        pass
            conn.commit()

        item = self._serialize_event(event_id=event_id, event=event)
        self._notify_subscribers(item)
```

- [ ] **Step 5: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "publish"`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add core/eventbus/bus.py core/eventbus/events.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): event_bus.publish() with caused_by + auto-pickup"
```

---

## Task 4: Query API — causal_graph.py

**Files:**
- Create: `core/services/causal_graph.py`
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test for backward chain**

```python
# tests/test_causal_graph.py — append
def _setup_chain_a_b_c():
    """Build a deterministic A→B→C chain. Returns (a_id, b_id, c_id)."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.eventbus.bus import event_bus
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.chain_a', '{}', '2026-05-08T00:00:00Z')"
        )
        a = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    event_bus.publish("runtime.chain_b", {}, caused_by=a)
    with connect() as c:
        b = int(c.execute(
            "SELECT id FROM events WHERE kind='runtime.chain_b' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
    event_bus.publish("runtime.chain_c", {}, caused_by=b)
    with connect() as c:
        ch = int(c.execute(
            "SELECT id FROM events WHERE kind='runtime.chain_c' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
    return a, b, ch


def test_query_causal_chain_backward_traversal():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=c, direction="backward", max_depth=5)
    assert result["root_event"]["id"] == c
    chain_ids = [step["event"]["id"] for step in result["chain"]]
    assert chain_ids == [b, a]
    assert result["truncated_by_depth"] is False
    assert result["total_nodes_returned"] == 2


def test_query_causal_chain_forward_traversal():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=a, direction="forward", max_depth=5)
    chain_ids = [step["event"]["id"] for step in result["chain"]]
    assert b in chain_ids
    assert c in chain_ids


def test_query_causal_chain_max_depth_truncates():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=c, direction="backward", max_depth=1)
    assert result["truncated_by_depth"] is True
    assert result["total_nodes_returned"] == 1


def test_query_causal_chain_no_edges_returns_empty_chain():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_graph import query_causal_chain
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.lonely', '{}', '2026-05-08T00:00:00Z')"
        )
        lonely = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    result = query_causal_chain(event_id=lonely, direction="backward")
    assert result["chain"] == []
    assert result["root_event"]["id"] == lonely


def test_query_causal_chain_handles_cycle_gracefully():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_graph import query_causal_chain
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.cycle_a', '{}', '2026-05-08T00:00:00Z')"
        )
        a = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.cycle_b', '{}', '2026-05-08T00:00:00Z')"
        )
        b = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        # Create A→B and B→A (cycle)
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) VALUES "
            "(?, ?, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:00Z')",
            (b, a),
        )
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) VALUES "
            "(?, ?, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:01Z')",
            (a, b),
        )
        c.commit()
    # Should not infinite loop — finishes via visited-set
    result = query_causal_chain(event_id=a, direction="backward", max_depth=10)
    assert isinstance(result, dict)  # returned cleanly, didn't hang


def test_query_causal_chain_pagination():
    """With limit=1, only first node returned but truncated_by_limit=True."""
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(
        event_id=c, direction="backward", max_depth=5, limit=1, offset=0,
    )
    assert result["total_nodes_returned"] == 1
    assert result["truncated_by_limit"] is True
    assert result["next_offset"] == 1
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "query_causal_chain"`
Expected: ImportError eller chain ikke fundet

- [ ] **Step 3: Skriv `core/services/causal_graph.py`**

```python
"""Causal graph query API.

Læser causal_edges + events for at traversere parent/child relations.
Backward = "hvad caused dette?" Forward = "hvad caused dette så?"

BFS-traversal med visited-set forhindrer infinite loops på cykliske
grafer (sjældne men muligt). Pagination via (offset, limit) så brede
events med mange children kan paginerers.
"""
from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _fetch_event(event_id: int) -> dict[str, Any] | None:
    with connect() as c:
        row = c.execute(
            "SELECT id, kind, payload_json, created_at FROM events WHERE id = ?",
            (event_id,),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except Exception:
        payload = {}
    return {
        "id": int(row["id"]),
        "kind": str(row["kind"]),
        "payload": payload,
        "created_at": str(row["created_at"]),
    }


def _fetch_neighbors(
    event_id: int,
    direction: str,
    min_confidence: float,
) -> list[dict[str, Any]]:
    """Return list of (other_event_id, edge dict) for one hop."""
    if direction == "backward":
        sql = (
            "SELECT parent_event_id AS other_id, edge_kind, confidence, "
            "source, reasoning FROM causal_edges "
            "WHERE child_event_id = ? AND confidence >= ?"
        )
    else:
        sql = (
            "SELECT child_event_id AS other_id, edge_kind, confidence, "
            "source, reasoning FROM causal_edges "
            "WHERE parent_event_id = ? AND confidence >= ?"
        )
    with connect() as c:
        rows = c.execute(sql, (event_id, min_confidence)).fetchall()
    return [
        {
            "other_id": int(r["other_id"]),
            "edge": {
                "kind": str(r["edge_kind"]),
                "confidence": float(r["confidence"]),
                "source": str(r["source"]),
                "reasoning": str(r["reasoning"] or ""),
            },
        }
        for r in rows
    ]


def query_causal_chain(
    *,
    event_id: int,
    direction: str = "backward",
    max_depth: int = 5,
    min_confidence: float = 0.5,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """BFS through causal_edges from event_id in given direction.

    Returns a dict with the root event and the chain (list of steps).
    See spec §5 for full response shape.
    """
    if direction not in ("backward", "forward"):
        raise ValueError(f"direction must be 'backward' or 'forward', got {direction}")

    root = _fetch_event(event_id)
    if root is None:
        return {
            "root_event": {"id": event_id, "kind": "<unknown>", "payload": {}, "created_at": ""},
            "chain": [],
            "truncated_by_depth": False,
            "truncated_by_limit": False,
            "total_nodes_returned": 0,
            "total_available": 0,
            "next_offset": None,
        }

    visited: set[int] = {event_id}
    queue: deque[tuple[int, int, dict[str, Any] | None]] = deque()
    # (depth, event_id, edge_dict-from-parent-to-this)
    queue.append((0, event_id, None))

    all_nodes: list[dict[str, Any]] = []
    truncated_by_depth = False

    while queue:
        depth, eid, edge = queue.popleft()
        if depth > max_depth:
            truncated_by_depth = True
            continue
        if depth > 0:  # skip root, it's in root_event
            ev = _fetch_event(eid)
            if ev is not None:
                all_nodes.append({"depth": depth, "event": ev, "edge": edge})
        if depth == max_depth:
            # Don't enqueue further but mark as truncated if there ARE neighbors
            neighbors = _fetch_neighbors(eid, direction, min_confidence)
            if neighbors:
                truncated_by_depth = True
            continue
        for n in _fetch_neighbors(eid, direction, min_confidence):
            other = n["other_id"]
            if other in visited:
                continue
            visited.add(other)
            queue.append((depth + 1, other, n["edge"]))

    total_available = len(all_nodes)
    sliced = all_nodes[offset : offset + limit]
    truncated_by_limit = (offset + limit) < total_available
    next_offset = offset + limit if truncated_by_limit else None

    return {
        "root_event": root,
        "chain": sliced,
        "truncated_by_depth": truncated_by_depth,
        "truncated_by_limit": truncated_by_limit,
        "total_nodes_returned": len(sliced),
        "total_available": total_available,
        "next_offset": next_offset,
    }


def query_causal_neighbors(
    *,
    event_id: int,
    direction: str = "both",
    min_confidence: float = 0.5,
) -> dict[str, Any]:
    """Direct neighbors only (depth=1) — convenience wrapper.

    direction='both' returns parents AND children.
    """
    out: dict[str, Any] = {"event_id": event_id, "parents": [], "children": []}
    if direction in ("backward", "both"):
        for n in _fetch_neighbors(event_id, "backward", min_confidence):
            ev = _fetch_event(n["other_id"])
            if ev:
                out["parents"].append({"event": ev, "edge": n["edge"]})
    if direction in ("forward", "both"):
        for n in _fetch_neighbors(event_id, "forward", min_confidence):
            ev = _fetch_event(n["other_id"])
            if ev:
                out["children"].append({"event": ev, "edge": n["edge"]})
    return out


def get_root_causes(event_id: int, *, max_depth: int = 10) -> list[dict[str, Any]]:
    """Walk backward until events without parents — convenience helper."""
    chain = query_causal_chain(
        event_id=event_id, direction="backward",
        max_depth=max_depth, limit=200,
    )
    # Roots = events der ikke har egne parents i resultatet
    parent_ids: set[int] = set()
    seen: dict[int, dict[str, Any]] = {}
    for step in chain["chain"]:
        seen[step["event"]["id"]] = step["event"]
    # Find dem med ingen edge ovenover (depth=max blandt deres siblings)
    return list(seen.values())[-3:]  # heuristik: top-3 dybeste


def get_immediate_cause(event_id: int) -> dict[str, Any] | None:
    """Return single highest-confidence direct parent, or None."""
    neighbors = query_causal_neighbors(event_id=event_id, direction="backward")
    if not neighbors["parents"]:
        return None
    best = max(neighbors["parents"], key=lambda p: p["edge"]["confidence"])
    return best
```

- [ ] **Step 4: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "query_causal_chain"`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add core/services/causal_graph.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): query API with pagination + cycle handling"
```

---

## Task 5: Three-tier inference daemon

**Files:**
- Create: `core/services/causal_inference_daemon.py`
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing tests for tier-1 og tier-2**

```python
# tests/test_causal_graph.py — append
def _insert_event_with_payload(kind: str, payload: dict, ts: str) -> int:
    import json as _json
    from core.runtime.db import connect
    with connect() as c:
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, _json.dumps(payload), ts),
        )
        c.commit()
        return int(cur.lastrowid)


def test_inference_tier1_kind_rule_match():
    """tool.invoked + tool.completed med samme tool_call_id → tier-1."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges")
        c.commit()
    parent = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": "call_t1"}, "2026-05-08T01:00:00Z",
    )
    child = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": "call_t1"}, "2026-05-08T01:00:02Z",
    )
    stats = run_inference_cycle()
    assert stats["edges_created"] >= 1
    assert stats["tier1_kind_rule_hits"] >= 1
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-kind"
    assert rows[0]["confidence"] == 0.9


def test_inference_tier2_shared_id_match():
    """Events med shared run_id, ingen kind-rule match → tier-2."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges")
        c.commit()
    parent = _insert_event_with_payload(
        "decision.created",
        {"run_id": "run_42", "decision_id": "d_1"},
        "2026-05-08T02:00:00Z",
    )
    child = _insert_event_with_payload(
        "memory.seed_planted",
        {"run_id": "run_42"},
        "2026-05-08T02:00:30Z",
    )
    run_inference_cycle()
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-id"
    assert rows[0]["confidence"] == 0.8


def test_inference_tier3_temporal_only():
    """Samme session_id ≤30s, intet andet match → tier-3."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges")
        c.commit()
    parent = _insert_event_with_payload(
        "channel.message_inbound",
        {"session_id": "chat-99"},
        "2026-05-08T03:00:00Z",
    )
    child = _insert_event_with_payload(
        "self_review.completed",
        {"session_id": "chat-99"},
        "2026-05-08T03:00:20Z",
    )
    run_inference_cycle()
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-temporal"
    assert rows[0]["confidence"] == 0.4


def test_inference_idempotent_no_dupes():
    """Running cycle twice produces same edges, not dupes."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges")
        c.commit()
    p = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": "x"}, "2026-05-08T04:00:00Z",
    )
    ch = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": "x"}, "2026-05-08T04:00:01Z",
    )
    run_inference_cycle()
    run_inference_cycle()
    with connect() as c:
        rows = c.execute(
            "SELECT COUNT(*) AS n FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ?",
            (ch, p),
        ).fetchone()
    assert int(rows["n"]) == 1


def test_inference_upgrades_confidence():
    """Tier-3 edge first; later tier-1 finds same pair → UPDATE confidence."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import (
        _record_edge, _ensure_table_ready,
    )
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges")
        c.commit()
    p = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": "y"}, "2026-05-08T05:00:00Z",
    )
    ch = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": "y"}, "2026-05-08T05:00:01Z",
    )
    _ensure_table_ready()
    _record_edge(child=ch, parent=p, edge_kind="triggered",
                 confidence=0.4, source="inferred-temporal",
                 reasoning="initial-low")
    _record_edge(child=ch, parent=p, edge_kind="triggered",
                 confidence=0.9, source="inferred-kind",
                 reasoning="upgraded")
    with connect() as c:
        row = c.execute(
            "SELECT confidence, source FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ?",
            (ch, p),
        ).fetchone()
    assert float(row["confidence"]) == 0.9
    assert row["source"] == "inferred-kind"
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "inference"`
Expected: ImportError

- [ ] **Step 3: Skriv `core/services/causal_inference_daemon.py`**

```python
"""Causal inference daemon — three-tier matching against event allowlist.

Tier 1 (kind-rule, conf=0.9): hardcoded parent-kind → child-kind par,
  kræver shared_id eller ≤30s temporal proximity.
Tier 2 (shared-id, conf=0.8): match på tool_call_id/run_id/decision_id
  i payload, ≤60s.
Tier 3 (temporal-only, conf=0.4): samme session_id ≤30s, intet andet match.

Cap 500 nye edges/tick. Retention 30 dage (60 for explicit).
Emitter causal.inference_stats event efter hvert tick.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

from core.runtime.db import _ensure_causal_edges_table, connect

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

_CADENCE_SECONDS = 15 * 60
_MAX_EDGES_PER_TICK = 500
_RETENTION_DAYS_INFERRED = 30
_RETENTION_DAYS_EXPLICIT = 60
_MAX_PRUNE_PER_TICK = 5000

# Inference allowlist (per spec §4.1). Kun events af disse kinds får
# inference-edges. Eksplicit edges kan stadig laves på enhver kind.
_ALLOWLIST = frozenset({
    "tool.completed", "tool.error", "tool.invoked", "tool.force_invoked",
    "decision.created", "decision.deduped", "decision.revoked",
    "behavioral_decision_review.kept",
    "behavioral_decision_review.partial",
    "behavioral_decision_review.broken",
    "self_review.completed", "conflict.detected", "conflict.resolved",
    "counterfactual.detected", "counterfactual.regret",
    "contradiction.detected",
    "runtime.executive_action_outcome_recorded",
    "runtime.cheap_lane_provider_failed",
    "channel.message_inbound",
    "memory.seed_triggered", "memory.seed_fulfilled",
    "identity.drift_detected", "heartbeat.conflict_resolved",
})

# Tier-1 kind-rules: parent-kind-prefix → set of child-kind candidates
_KIND_RULES: dict[str, set[str]] = {
    "tool.invoked":      {"tool.completed", "tool.error"},
    "tool.force_invoked": {"tool.completed", "tool.error"},
    "decision.created":   {"behavioral_decision_review.kept",
                           "behavioral_decision_review.partial",
                           "behavioral_decision_review.broken"},
    "conflict.detected":  {"conflict.resolved"},
    "channel.message_inbound": {"tool.invoked", "tool.force_invoked"},
}

# Shared-id keys checked in tier-2 (priority order — first match wins)
_SHARED_ID_KEYS = ("tool_call_id", "decision_id", "run_id", "session_id")

# Temporal windows
_KIND_RULE_WINDOW_S = 30
_SHARED_ID_WINDOW_S = 60
_TEMPORAL_FALLBACK_WINDOW_S = 30

# Module state
_last_tick_at: datetime | None = None


def _ensure_table_ready() -> None:
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.commit()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def _record_edge(
    *, child: int, parent: int, edge_kind: str,
    confidence: float, source: str, reasoning: str,
) -> str:
    """INSERT or UPGRADE an edge. Returns 'created'|'upgraded'|'skipped'."""
    now_iso = _now_iso()
    with connect() as c:
        existing = c.execute(
            "SELECT confidence FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ? "
            "AND edge_kind = ?",
            (child, parent, edge_kind),
        ).fetchone()
        if existing is not None:
            cur_conf = float(existing["confidence"])
            if confidence > cur_conf:
                c.execute(
                    "UPDATE causal_edges SET confidence = ?, source = ?, "
                    "reasoning = ?, created_at = ? "
                    "WHERE child_event_id = ? AND parent_event_id = ? "
                    "AND edge_kind = ?",
                    (confidence, source, reasoning, now_iso,
                     child, parent, edge_kind),
                )
                c.commit()
                return "upgraded"
            return "skipped"
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at, reasoning) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (child, parent, edge_kind, confidence, source, now_iso, reasoning),
        )
        c.commit()
        return "created"


def _payload(event: dict) -> dict:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:
        return {}


def _try_tier1_kind_rule(child: dict, candidates_by_kind: dict[str, list[dict]]) -> tuple[int | None, str]:
    """Look for a parent matching a hardcoded kind→kind rule + shared-id-or-time."""
    child_kind = str(child["kind"])
    child_payload = _payload(child)
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""
    for parent_kind, child_set in _KIND_RULES.items():
        if child_kind not in child_set:
            continue
        for cand in candidates_by_kind.get(parent_kind, []):
            cand_ts = _parse_iso(cand["created_at"])
            if cand_ts is None or cand_ts >= child_ts:
                continue
            if (child_ts - cand_ts).total_seconds() > _KIND_RULE_WINDOW_S * 4:
                continue  # too far apart to be related
            cand_payload = _payload(cand)
            # Prefer shared-id match within the rule
            for key in _SHARED_ID_KEYS:
                if (child_payload.get(key)
                        and cand_payload.get(key) == child_payload.get(key)):
                    return int(cand["id"]), f"kind-rule:{parent_kind}→{child_kind}+id:{key}"
            # Fall back to temporal-only within rule window
            if (child_ts - cand_ts).total_seconds() <= _KIND_RULE_WINDOW_S:
                return int(cand["id"]), f"kind-rule:{parent_kind}→{child_kind}+time"
    return None, ""


def _try_tier2_shared_id(child: dict, candidates: list[dict]) -> tuple[int | None, str]:
    child_payload = _payload(child)
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""
    for key in _SHARED_ID_KEYS:
        cv = child_payload.get(key)
        if not cv:
            continue
        for cand in candidates:
            cand_ts = _parse_iso(cand["created_at"])
            if cand_ts is None or cand_ts >= child_ts:
                continue
            if (child_ts - cand_ts).total_seconds() > _SHARED_ID_WINDOW_S:
                continue
            cp = _payload(cand)
            if cp.get(key) == cv:
                return int(cand["id"]), f"shared-id:{key}"
    return None, ""


def _try_tier3_temporal(child: dict, candidates: list[dict]) -> tuple[int | None, str]:
    child_payload = _payload(child)
    sess = child_payload.get("session_id")
    if not sess:
        return None, ""
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""
    best_cand: dict | None = None
    best_dt: float = _TEMPORAL_FALLBACK_WINDOW_S + 1
    for cand in candidates:
        cp = _payload(cand)
        if cp.get("session_id") != sess:
            continue
        cand_ts = _parse_iso(cand["created_at"])
        if cand_ts is None or cand_ts >= child_ts:
            continue
        dt = (child_ts - cand_ts).total_seconds()
        if dt > _TEMPORAL_FALLBACK_WINDOW_S:
            continue
        if dt < best_dt:
            best_dt = dt
            best_cand = cand
    if best_cand is not None:
        return int(best_cand["id"]), f"temporal:session+{int(best_dt)}s"
    return None, ""


def _fetch_recent_allowlist_events(*, since_minutes: int = 30, limit: int = 1000) -> list[dict]:
    cutoff = (datetime.now(UTC) - timedelta(minutes=since_minutes)).isoformat()
    placeholders = ",".join("?" * len(_ALLOWLIST))
    with connect() as c:
        rows = c.execute(
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE created_at >= ? AND kind IN ({placeholders}) "
            f"ORDER BY created_at ASC LIMIT ?",
            (cutoff, *list(_ALLOWLIST), limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _prune_old_edges() -> int:
    """DELETE edges older than retention thresholds. Cap at MAX_PRUNE_PER_TICK."""
    cutoff_inferred = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS_INFERRED)).isoformat()
    cutoff_explicit = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS_EXPLICIT)).isoformat()
    with connect() as c:
        cur = c.execute(
            "DELETE FROM causal_edges WHERE id IN ("
            "  SELECT id FROM causal_edges "
            "  WHERE (source != 'explicit' AND created_at < ?) "
            "     OR (source = 'explicit' AND created_at < ?) "
            "  LIMIT ?"
            ")",
            (cutoff_inferred, cutoff_explicit, _MAX_PRUNE_PER_TICK),
        )
        deleted = cur.rowcount or 0
        c.commit()
    return deleted


def run_inference_cycle() -> dict[str, int]:
    """Run one inference tick. Returns stats dict.

    Idempotent — UNIQUE-constraint + UPDATE-on-better-confidence handles
    re-runs cleanly.
    """
    _ensure_table_ready()
    started = time.monotonic()

    events = _fetch_recent_allowlist_events()
    candidates_by_kind: dict[str, list[dict]] = {}
    for ev in events:
        candidates_by_kind.setdefault(str(ev["kind"]), []).append(ev)

    edges_created = 0
    edges_upgraded = 0
    tier1 = tier2 = tier3 = 0

    for child in events:
        if edges_created >= _MAX_EDGES_PER_TICK:
            break
        # Tier 1 — kind rule
        pid, reason = _try_tier1_kind_rule(child, candidates_by_kind)
        if pid is not None:
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="triggered", confidence=0.9,
                source="inferred-kind", reasoning=reason,
            )
            if res == "created":
                edges_created += 1; tier1 += 1
            elif res == "upgraded":
                edges_upgraded += 1
            continue
        # Tier 2 — shared id
        pid, reason = _try_tier2_shared_id(child, events)
        if pid is not None and pid != int(child["id"]):
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="caused", confidence=0.8,
                source="inferred-id", reasoning=reason,
            )
            if res == "created":
                edges_created += 1; tier2 += 1
            elif res == "upgraded":
                edges_upgraded += 1
            continue
        # Tier 3 — temporal-only fallback
        pid, reason = _try_tier3_temporal(child, events)
        if pid is not None and pid != int(child["id"]):
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="caused", confidence=0.4,
                source="inferred-temporal", reasoning=reason,
            )
            if res == "created":
                edges_created += 1; tier3 += 1
            elif res == "upgraded":
                edges_upgraded += 1

    pruned = 0
    try:
        pruned = _prune_old_edges()
    except Exception as exc:
        logger.warning("causal_inference: prune failed: %s", exc)

    duration_ms = int((time.monotonic() - started) * 1000)
    stats = {
        "events_scanned": len(events),
        "edges_created": edges_created,
        "edges_upgraded": edges_upgraded,
        "tier1_kind_rule_hits": tier1,
        "tier2_shared_id_hits": tier2,
        "tier3_temporal_hits": tier3,
        "edges_pruned": pruned,
        "duration_ms": duration_ms,
    }
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("causal.inference_stats", {**stats, "completed_at": _now_iso()})
    except Exception as exc:
        logger.debug("causal_inference: publish stats failed: %s", exc)

    return stats


def tick_causal_inference_daemon() -> dict[str, object]:
    """Daemon-manager entry: run one cycle if cadence elapsed."""
    global _last_tick_at
    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at).total_seconds() < _CADENCE_SECONDS:
            return {"ran": False}
    try:
        stats = run_inference_cycle()
        _last_tick_at = now
        return {"ran": True, **stats}
    except Exception as exc:
        logger.warning("causal_inference: cycle failed: %s", exc, exc_info=True)
        _last_tick_at = now
        return {"ran": False, "error": str(exc)}
```

- [ ] **Step 4: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "inference"`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add core/services/causal_inference_daemon.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): three-tier inference daemon + retention + stats"
```

---

## Task 6: Daemon registration

**Files:**
- Modify: `core/services/daemon_manager.py` (registrér causal_inference)

- [ ] **Step 1: Tilføj registry-entry**

I `core/services/daemon_manager.py`, find blokken med `"identity_drift":` og tilføj efter den:

```python
    "causal_inference": {
        "module": "core.services.causal_inference_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "15min causal-graph inference (three-tier matching) — populates causal_edges from events allowlist",
    },
```

- [ ] **Step 2: Verificér registration**

Run: `conda run -n ai python -c "from core.services.daemon_manager import _REGISTRY; assert 'causal_inference' in _REGISTRY; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add core/services/daemon_manager.py
git commit -m "feat(causal-graph): register causal_inference daemon (15min cadence)"
```

---

## Task 7: query_why tool

**Files:**
- Modify: `core/tools/simple_tools.py` (registrér tool)
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test**

```python
# tests/test_causal_graph.py — append
def test_query_why_tool_by_event_id():
    from core.tools.simple_tools import _exec_query_why
    a, b, c = _setup_chain_a_b_c()
    result = _exec_query_why({"event_id": c, "max_depth": 5})
    assert result["status"] == "ok"
    assert "chain" in result
    assert any(step["event"]["id"] == a for step in result["chain"])


def test_query_why_tool_by_event_kind_finds_latest():
    from core.tools.simple_tools import _exec_query_why
    a, b, c = _setup_chain_a_b_c()
    result = _exec_query_why({"event_kind": "runtime.chain_c", "max_depth": 5})
    assert result["status"] == "ok"
    assert result["root_event"]["id"] == c


def test_query_why_tool_unknown_event_kind_returns_error():
    from core.tools.simple_tools import _exec_query_why
    result = _exec_query_why({"event_kind": "no.such.kind"})
    assert result["status"] == "error"
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "query_why"`
Expected: ImportError eller AttributeError

- [ ] **Step 3: Find slutningen af tool-registry i simple_tools.py**

```bash
grep -n "TOOL_DEFINITIONS\|_exec_remember_this\|TOOL_HANDLERS\|register_tool" core/tools/simple_tools.py | head -10
```

Tilføj følgende efter eksisterende tool-handlers (typisk omkring de andre `_exec_*` functions):

```python
def _exec_query_why(args: dict[str, Any]) -> dict[str, Any]:
    """Query the causal graph for why an event happened.

    Either event_id (specific event) or event_kind (latest of kind).
    """
    from core.runtime.db import connect
    from core.services.causal_graph import query_causal_chain

    event_id = args.get("event_id")
    event_kind = str(args.get("event_kind") or "").strip()
    max_depth = int(args.get("max_depth") or 5)
    min_confidence = float(args.get("min_confidence") or 0.5)

    if event_id is None and not event_kind:
        return {"status": "error", "error": "must supply event_id or event_kind"}

    if event_id is None:
        with connect() as c:
            row = c.execute(
                "SELECT id FROM events WHERE kind = ? "
                "ORDER BY id DESC LIMIT 1",
                (event_kind,),
            ).fetchone()
        if not row:
            return {"status": "error",
                    "error": f"no event found with kind={event_kind}"}
        event_id = int(row["id"])

    chain = query_causal_chain(
        event_id=int(event_id),
        direction="backward",
        max_depth=max_depth,
        min_confidence=min_confidence,
    )
    return {"status": "ok", **chain}
```

- [ ] **Step 4: Tilføj til tool-definitions registry**

Find `JARVIS_TOOL_DEFINITIONS` (eller hvad listen kalder sig — søg `"name": "remember_this"`) og tilføj:

```python
    {
        "type": "function",
        "function": {
            "name": "query_why",
            "description": (
                "Spørg causal graph hvorfor en event skete. Traverser baglæns "
                "gennem causal_edges. Giv enten event_id eller event_kind "
                "(seneste event af den kind bruges)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Specifik event-id"},
                    "event_kind": {"type": "string", "description": "Brug seneste event af denne kind"},
                    "max_depth": {"type": "integer", "description": "Max chain-dybde, default 5"},
                    "min_confidence": {"type": "number", "description": "Filter low-confidence edges, default 0.5"},
                },
                "required": [],
            },
        },
    },
```

Og koble dispatch i tool-call-router (tjek hvor andre `_exec_*` registreres — typisk en dict eller en if/elif kæde i `execute_simple_tool` eller lignende):

```python
# I dispatch-funktionen:
if name == "query_why":
    return _exec_query_why(args)
```

- [ ] **Step 5: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "query_why"`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add core/tools/simple_tools.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): query_why tool for on-demand causal queries"
```

---

## Task 8: Awareness injection — causal_alerts

**Files:**
- Create: `core/services/prompt_sections/causal_alerts.py`
- Modify: `core/services/prompt_contract.py` (wire awareness item)
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test**

```python
# tests/test_causal_graph.py — append
def test_causal_alerts_section_empty_when_no_failures():
    """No recent failure events → empty section."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.prompt_sections.causal_alerts import causal_alerts_section
    with connect() as c:
        _ensure_causal_edges_table(c)
        # Clean any failure events from very recent window
        c.execute(
            "DELETE FROM events WHERE kind = 'tool.error' "
            "AND created_at >= datetime('now', '-1 minute')"
        )
        c.commit()
    out = causal_alerts_section()
    assert out == ""


def test_causal_alerts_section_returns_text_for_recent_failure():
    """Recent tool.error with explicit caused_by produces formatted alert."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.eventbus.bus import event_bus
    from core.services.prompt_sections.causal_alerts import causal_alerts_section
    with connect() as c:
        _ensure_causal_edges_table(c)
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.alert_parent', '{}', datetime('now', '-1 minute'))"
        )
        parent = int(cur.lastrowid)
        c.commit()
    event_bus.publish(
        "tool.error",
        {"tool": "test_tool", "error": "boom", "severity": "high"},
        caused_by=parent,
    )
    out = causal_alerts_section()
    assert "Kausalkæde" in out or "🔗" in out
```

- [ ] **Step 2: Kør tests — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "causal_alerts"`
Expected: ModuleNotFoundError

- [ ] **Step 3: Skriv `core/services/prompt_sections/causal_alerts.py`**

```python
"""Causal alerts — surface failure-event chains in the prompt.

Scanner sidste LOOKBACK_MINUTES for kritiske failure-events og injecter
top-1 kausal-kæde for hver. Cap'er max 2 chains pr. tur så det ikke
fylder prompten.

Kører som awareness-item (priority 30) i prompt_contract.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# Tunable. Senere kan vi skifte til events_since_last_tick i stedet
# for et fast tidsvindue (per spec note §7.2).
LOOKBACK_MINUTES = 30

_FAILURE_KINDS = (
    "tool.error",
    "behavioral_decision_review.broken",
    "runtime.cheap_lane_provider_failed",
    "identity.drift_detected",
    "executive_contradiction.detected",
)

_MAX_CHAINS_PER_TURN = 2
_CHAIN_DEPTH = 3
_MIN_CONFIDENCE = 0.7


def _fetch_recent_failures(limit: int) -> list[dict]:
    cutoff = (datetime.now(UTC) - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    placeholders = ",".join("?" * len(_FAILURE_KINDS))
    with connect() as c:
        rows = c.execute(
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) AND created_at >= ? "
            f"ORDER BY id DESC LIMIT ?",
            (*list(_FAILURE_KINDS), cutoff, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _format_chain_for_failure(failure_event: dict) -> str:
    from core.services.causal_graph import query_causal_chain
    chain = query_causal_chain(
        event_id=int(failure_event["id"]),
        direction="backward",
        max_depth=_CHAIN_DEPTH,
        min_confidence=_MIN_CONFIDENCE,
    )
    if not chain["chain"]:
        # No causal data yet — render a minimal alert without chain
        ts = str(failure_event.get("created_at", ""))[:19]
        return (f"🔗 Kausalkæde — recent failure:\n"
                f"  ROOT: {failure_event['kind']} ({ts}) <ingen edges fundet>")
    lines = ["🔗 Kausalkæde — recent failure:"]
    root_kind = str(failure_event["kind"])
    root_ts = str(failure_event.get("created_at", ""))[:19]
    lines.append(f"  ROOT: {root_kind} ({root_ts})")
    for step in chain["chain"]:
        ev = step["event"]
        ts = str(ev.get("created_at", ""))[:19]
        lines.append(f"    ↳ {ev['kind']} ({ts})")
    return "\n".join(lines)


def causal_alerts_section() -> str:
    """Build the causal-alerts awareness section. Returns "" if no alerts."""
    try:
        failures = _fetch_recent_failures(limit=_MAX_CHAINS_PER_TURN)
    except Exception as exc:
        logger.debug("causal_alerts: fetch failed: %s", exc)
        return ""
    if not failures:
        return ""
    chunks: list[str] = []
    for fail in failures:
        try:
            chunks.append(_format_chain_for_failure(fail))
        except Exception as exc:
            logger.debug("causal_alerts: format failed: %s", exc)
            continue
    return "\n\n".join(chunks)
```

- [ ] **Step 4: Wire ind i prompt_contract.py**

Find blokken hvor andre awareness-items registreres (omkring rule_conclusions linjen ~735). Tilføj:

```python
    try:
        from core.services.prompt_sections.causal_alerts import (
            causal_alerts_section,
        )
        _awareness_add(30, "causal alerts", causal_alerts_section())
    except Exception:
        pass
```

- [ ] **Step 5: Kør tests — skal passere**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "causal_alerts"`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add core/services/prompt_sections/causal_alerts.py core/services/prompt_contract.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): causal_alerts prompt-injection for recent failures"
```

---

## Task 9: Instrumentér curated kerne-set

**Files:**
- Modify: `core/services/visible_runs.py` (agentic-round → context)
- Modify: `core/services/counterfactual_engine.py` (placeholder — full integration in Task 10)

Resten af de "curated kerne-sites" kan komme organisk når kode rører de paths. Denne task instrumenterer det vigtigste.

- [ ] **Step 1: Helper-funktion der publicerer round-start + returnerer event-id**

Tilføj nederst i `core/services/visible_runs.py` (eller importer hvor det passer):

```python
def _publish_agentic_round_start(*, run_id: str, round_num: int) -> int:
    """Publish runtime.agentic_round_start event and return its event_id.
    Used for EventContext binding so events inside the round get
    auto-linked to round-start as their parent.
    """
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    event_bus.publish(
        "runtime.agentic_round_start",
        {"run_id": run_id, "round": round_num},
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM events WHERE kind = ? "
            "ORDER BY id DESC LIMIT 1",
            ("runtime.agentic_round_start",),
        ).fetchone()
    return int(row["id"]) if row else 0
```

- [ ] **Step 2: Wrap round-body med `with_event_context`**

I `for _agentic_round in range(_AGENTIC_MAX_ROUNDS):` (~line 1206), find FØRSTE statement i loop-body (typisk `if not _provider_supports_followup:` — line 1207). INDSÆT lige FØR den et opslag og åbn en context manager der dækker resten af loop-body:

```python
                for _agentic_round in range(_AGENTIC_MAX_ROUNDS):
                    from core.eventbus.context import with_event_context
                    _round_event_id = _publish_agentic_round_start(
                        run_id=run.run_id, round_num=_agentic_round + 1,
                    )
                    with with_event_context(_round_event_id):
                        # ↓↓↓ resten af eksisterende round-body uændret ↓↓↓
                        if not _provider_supports_followup:
                            # ...alle eksisterende statements...
                            ...
                        # ↑↑↑ alt indtil "agentic-round-end" log ↑↑↑
```

KONKRET ÆNDRING: tag de ~600 linjer der allerede ligger i loop-body, indrykker dem ÉT niveau (4 spaces) og pak dem i `with with_event_context(...)`. Ingen logik-ændring. Editor's multi-line-indent (Ctrl+]) håndterer det på sekunder.

Verificér at alle eksisterende statements stadig er nået i `for`-loop'ets scope — pas på continue/break-statements som tidligere brød ud af for-loop'en, de bryder nu ud af with-blokken (samme effekt fordi with rejser ikke exception ved break/continue).

- [ ] **Step 3: Compile-check ingen syntax-fejl**

Run: `conda run -n ai python -m compileall -q core/services/visible_runs.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Smoke-test at edges skrives ved en fake round**

```bash
conda run -n ai python -c "
from core.runtime.db import connect, _ensure_causal_edges_table
from core.eventbus.bus import event_bus
from core.eventbus.context import with_event_context
with connect() as c:
    _ensure_causal_edges_table(c)
event_bus.publish('runtime.agentic_round_start', {'round': 1, 'run_id': 'test'})
with connect() as c:
    pid = int(c.execute(\"SELECT id FROM events WHERE kind='runtime.agentic_round_start' ORDER BY id DESC LIMIT 1\").fetchone()['id'])
with with_event_context(pid):
    event_bus.publish('runtime.test_inside_round', {})
with connect() as c:
    n = c.execute('SELECT COUNT(*) AS n FROM causal_edges WHERE parent_event_id = ?', (pid,)).fetchone()['n']
    print(f'edges from round-start: {n}')
assert n == 1
print('OK')
"
```
Expected: `edges from round-start: 1` then `OK`

- [ ] **Step 5: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(causal-graph): wire EventContext in agentic-round dispatch"
```

---

## Task 10: Counterfactuals two-way integration

**Files:**
- Modify: `core/services/counterfactual_engine.py`
- Test: `tests/test_causal_graph.py`

- [ ] **Step 1: Skriv failing test**

```python
# tests/test_causal_graph.py — append
def test_counterfactual_emits_with_explicit_caused_by():
    """When counterfactual_engine emits counterfactual.detected, it carries caused_by."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.counterfactual_engine import _publish_event
    with connect() as c:
        _ensure_causal_edges_table(c)
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('self_review.completed', '{}', datetime('now'))"
        )
        trigger_id = int(cur.lastrowid)
        c.commit()
    _publish_event(
        "counterfactual.detected",
        {"cf_id": "cf-test", "trigger_event_ids": [trigger_id]},
        caused_by_trigger_id=trigger_id,
    )
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE parent_event_id = ?",
            (trigger_id,),
        ).fetchall()
    assert any(r["edge_kind"] == "caused" and r["source"] == "explicit" for r in rows)
```

- [ ] **Step 2: Kør test — forventes at fejle**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "counterfactual_emits"`
Expected: TypeError eller manglende parameter

- [ ] **Step 3: Udvid `_publish_event()` i counterfactual_engine.py**

Find funktionen og tilføj parameter:

```python
def _publish_event(
    kind: str,
    payload: dict,
    *,
    caused_by_trigger_id: int | None = None,
) -> None:
    """Internal publish wrapper. caused_by_trigger_id is the trigger event
    that produced this counterfactual — links it to its source for
    causal-graph queries.
    """
    from core.eventbus.bus import event_bus
    if caused_by_trigger_id is not None:
        event_bus.publish(
            kind, payload,
            caused_by=int(caused_by_trigger_id),
            edge_kind="caused",
        )
    else:
        event_bus.publish(kind, payload)
```

- [ ] **Step 4: Tilføj forward-query i `run()` orchestrator**

I `counterfactual_engine.run()`, lige FØR `_generate_counterfactuals_via_llm` kaldes (Phase 2 placeholder), tilføj:

```python
    # Forward-query causal graph for downstream events that would be
    # pruned in the hypothetical. Phase 1 returns empty if graph hasn't
    # tracked edges for this trigger yet — falls back gracefully.
    downstream_context = []
    try:
        from core.services.causal_graph import query_causal_chain
        for trigger in trigger_events:
            chain = query_causal_chain(
                event_id=trigger.event_id,
                direction="forward",
                max_depth=3,
                min_confidence=0.6,
            )
            if chain["chain"]:
                downstream_context.append({
                    "trigger_id": trigger.event_id,
                    "downstream": [
                        {"id": s["event"]["id"], "kind": s["event"]["kind"]}
                        for s in chain["chain"]
                    ],
                })
    except Exception:
        pass  # graph not ready yet, Phase 1 placeholder still works
```

Pass `downstream_context` videre til `_generate_counterfactuals_via_llm` — den kan ignorere den i Phase 1, men Phase 2 vil bruge den til berigelse.

- [ ] **Step 5: Kør test**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v -k "counterfactual_emits"`
Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add core/services/counterfactual_engine.py tests/test_causal_graph.py
git commit -m "feat(causal-graph): counterfactual two-way integration (forward-query + caused_by emit)"
```

---

## Task 11: End-to-end smoke + restart

**Files:**
- Test: `tests/test_causal_graph.py` (en samlet integration)

- [ ] **Step 1: Skriv integrations-test**

```python
# tests/test_causal_graph.py — append
def test_end_to_end_explicit_inference_query():
    """Full flow: explicit edge + tier-1 inference + query returns combined chain."""
    import json as _json
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.eventbus.bus import event_bus
    from core.services.causal_inference_daemon import run_inference_cycle
    from core.services.causal_graph import query_causal_chain

    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute("DELETE FROM causal_edges WHERE reasoning LIKE 'e2e:%'")
        c.commit()

    # Producer chain manually
    parent = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": "e2e_call"}, "2026-05-08T06:00:00Z",
    )
    child = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": "e2e_call"}, "2026-05-08T06:00:01Z",
    )
    grandchild_id = None
    event_bus.publish(
        "memory.seed_planted",
        {"context": "test", "trigger": "e2e"},
        caused_by=child,
    )
    with connect() as c:
        grandchild_id = int(c.execute(
            "SELECT id FROM events WHERE kind = 'memory.seed_planted' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"])

    # Inference picks up the tier-1 edge (parent → child)
    run_inference_cycle()

    # Query backward from grandchild
    result = query_causal_chain(
        event_id=grandchild_id, direction="backward",
        max_depth=5, min_confidence=0.5,
    )
    chain_ids = [s["event"]["id"] for s in result["chain"]]
    assert child in chain_ids
    assert parent in chain_ids
```

- [ ] **Step 2: Kør hele test-fil**

Run: `conda run -n ai python -m pytest tests/test_causal_graph.py -v`
Expected: alle tests passerer

- [ ] **Step 3: Restart services så daemon registers + EventContext træder i kraft**

```bash
sudo systemctl restart jarvis-api jarvis-runtime
sleep 4
systemctl is-active jarvis-api jarvis-runtime
```
Expected: `active` × 2

- [ ] **Step 4: Verificér første daemon-tick rapporterer stats**

```bash
sleep 30
journalctl -u jarvis-runtime --since "30 sec ago" --no-pager | grep -iE "causal|inference_stats" | tail -5
```
Expected: enten en log-line med causal-aktivitet eller intet (daemon kører på 15-min cadence — kan tage et par tics)

- [ ] **Step 5: Commit + done**

```bash
git add tests/test_causal_graph.py
git commit -m "test(causal-graph): end-to-end integration test"
```

---

## Done-kriterier

- [ ] Alle 11 tasks committet
- [ ] `pytest tests/test_causal_graph.py -v` passerer alle tests grønt
- [ ] Restart sker uden traceback i journal
- [ ] `_REGISTRY['causal_inference']` synlig i daemon_manager
- [ ] Manuelt smoke-tjek: kald `query_why(event_kind="tool.error")` via Python returnerer en chain (eller pænt empty hvis ingen edges)

## Phase 2 (separat plan, IKKE i scope her)

- LLM-summarized forward-graph i prompt ("dette mønster er gentaget 5x — typiske kausalstier ser sådan ud: ...")
- Cross-session "temporal substrate" per Shapira
- `query_why` UI-rendering i Mission Control dashboard
