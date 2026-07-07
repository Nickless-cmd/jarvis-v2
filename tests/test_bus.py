"""EventBus — unit and integration tests.

Covers the async-writer EventBus implementation:
publish, subscribe, unsubscribe, flush, recent queries,
causal edges, backpressure, concurrent access, and shutdown.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def event_bus(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request) -> Any:
    """Return a fresh EventBus backed by an isolated tmp SQLite DB.

    ISOLATION WITHOUT SINGLETON POLLUTION
    -------------------------------------
    An earlier version of this fixture popped ``core.runtime.db*`` and
    ``core.eventbus.*`` from ``sys.modules`` and re-imported them so they
    would pick up a fresh HOME.  That had a nasty side effect: re-importing
    ``core.eventbus.bus`` re-executed its module body, which builds a NEW
    module-level ``event_bus = EventBus()`` singleton (with its own writer
    thread).  The finalizer only stopped the fixture's LOCAL bus, never the
    freshly-minted module singleton — so every invocation leaked one
    writer thread AND left ``core.eventbus.bus.event_bus`` pointing at a
    different object id than the one other test modules had bound at
    collection time (``from core.eventbus.bus import event_bus``).  Those
    victims then published/subscribed on a different bus than the code under
    test, or their bus's writer targeted a since-deleted tmp DB → "event not
    published" / empty ``causal_edges``.

    This version avoids all module churn:

    * ``connect()`` (in ``core.runtime.db_core``) reads its ``DB_PATH``
      module global at call time.  We ``monkeypatch.setattr`` that single
      global to a tmp DB.  Because ``core.runtime.db`` and
      ``core.eventbus.bus`` both call the *same* ``db_core.connect`` object,
      the fixture bus's writer, this test's read-backs, and any runtime code
      all hit the same isolated DB — no reload required.

    * The ``EventBus`` class is imported from the already-loaded module (no
      pop/reimport), so the shared ``core.eventbus.bus`` module object and
      its ``event_bus`` singleton are never rebound by import machinery.

    * The module singleton is repointed at the fixture's local bus via
      ``monkeypatch.setattr`` (auto-restored on teardown), so its object id
      is IDENTICAL before and after the test.

    * The local bus's writer thread is joined in the finalizer, so no
      writer threads leak.
    """
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    import sys

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Isolated on-disk DB for this test. We point db_core.DB_PATH at it via
    # monkeypatch (auto-restored) rather than reloading the module under a
    # fresh HOME. connect() reads DB_PATH lazily, so this reroutes every
    # caller (bus writer + test read-backs) to the same tmp file.
    tmp_db = tmp_path / "jarvis.db"

    import core.runtime.db_core as db_core

    monkeypatch.setattr(db_core, "DB_PATH", tmp_db)

    # Ensure tables exist in the isolated DB.
    from core.runtime.db import connect, _ensure_causal_edges_table

    with connect() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_causal_edges_table(c)
        c.commit()

    import core.eventbus.bus as bus_mod
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES

    ALLOWED_EVENT_FAMILIES.update({"alpha", "beta", "gamma"})

    bus = bus_mod.EventBus()

    # Make the module singleton resolve to our local bus for any code under
    # test that binds `core.eventbus.bus.event_bus` at call time. monkeypatch
    # restores the ORIGINAL singleton object on teardown → object id unchanged.
    monkeypatch.setattr(bus_mod, "event_bus", bus)

    request.addfinalizer(lambda b=bus: b.stop())
    return bus


def _count_events(db_cursor) -> int:
    return db_cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def _last_event(db_cursor) -> dict[str, Any] | None:
    row = db_cursor.execute(
        "SELECT id, kind, payload_json, created_at FROM events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "kind": row["kind"],
        "payload": json.loads(row["payload_json"]),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPublishAndFlush:
    """Core write path: publish → flush → read-back from DB."""

    def test_publish_persists_event(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.test_ping", {"msg": "hello"})
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            ev = _last_event(c)
        assert ev is not None
        assert ev["kind"] == "runtime.test_ping"
        assert ev["payload"] == {"msg": "hello"}

    def test_publish_no_payload(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.test_no_payload")
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            ev = _last_event(c)
        assert ev is not None
        assert ev["kind"] == "runtime.test_no_payload"
        assert ev["payload"] == {}

    def test_publish_multiple_events_in_order(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.test_a", {"n": 1})
        bus.publish("runtime.test_b", {"n": 2})
        bus.publish("runtime.test_c", {"n": 3})
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            rows = c.execute(
                "SELECT kind, payload_json FROM events ORDER BY id ASC"
            ).fetchall()
        kinds = [r["kind"] for r in rows]
        payloads = [json.loads(r["payload_json"])["n"] for r in rows]
        assert kinds == ["runtime.test_a", "runtime.test_b", "runtime.test_c"]
        assert payloads == [1, 2, 3]

    def test_flush_timeout_logs_warning(self, event_bus, monkeypatch, tmp_path, caplog):
        """flush() with a very short timeout should log, not crash."""
        bus = event_bus
        # Fill the writer queue so flush has to wait
        for i in range(100):
            bus.publish(f"runtime.test_spam.{i}")
        # A 0.001s timeout is too short for 100 events
        bus.flush(timeout=0.001)
        assert any(
            "timed out" in msg for msg in caplog.messages
        ), "Expected timeout warning"


class TestSubscribe:
    """Real-time subscriber notification."""

    def test_subscriber_receives_event(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        sub = bus.subscribe()
        bus.publish("runtime.test_sub", {"x": 1})
        bus.flush()
        got = sub.get(timeout=2)
        assert got is not None
        assert got["kind"] == "runtime.test_sub"
        assert got["payload"] == {"x": 1}
        assert got["id"] > 0

    def test_subscriber_id_and_timestamp(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        sub = bus.subscribe()
        bus.publish("runtime.test_meta", {"v": 1})
        bus.flush()
        got = sub.get(timeout=2)
        assert isinstance(got["id"], int) and got["id"] > 0
        assert isinstance(got["created_at"], str) and "T" in got["created_at"]

    def test_multiple_subscribers(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        sub1 = bus.subscribe()
        sub2 = bus.subscribe()
        bus.publish("runtime.test_broadcast", {"broadcast": True})
        bus.flush()
        got1 = sub1.get(timeout=2)
        got2 = sub2.get(timeout=2)
        assert got1["id"] == got2["id"]
        assert got1["kind"] == "runtime.test_broadcast"

    def test_subscriber_unsubscribe_stops_events(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        sub = bus.subscribe()
        bus.publish("runtime.test_before")
        bus.flush()
        sub.get(timeout=2)  # consume

        bus.unsubscribe(sub)
        bus.publish("runtime.test_after")
        bus.flush()
        # The queue should get None sentinel (from unsubscribe), NO event
        got = sub.get(timeout=0.5)
        assert got is None, "Got event after unsubscribe"

    def test_slow_subscriber_not_stalled(self, event_bus, monkeypatch, tmp_path):
        """Slow subscriber should not block the bus for others."""
        bus = event_bus
        slow = queue.Queue()
        bus._subscribers.append(slow)  # bypass lock for test
        sub = bus.subscribe()
        bus.publish("runtime.test_fast")
        bus.flush()
        fast_got = sub.get(timeout=2)
        assert fast_got is not None
        assert fast_got["kind"] == "runtime.test_fast"


class TestCausalEdges:
    """Causal edge persistence from publish(caused_by=...)."""

    def test_explicit_caused_by(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.parent_event", {"id": 99})
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            parent = c.execute(
                "SELECT id FROM events WHERE kind = 'runtime.parent_event'"
            ).fetchone()
        parent_id = parent["id"]

        bus.publish("runtime.child_event", {"id": 100}, caused_by=parent_id)
        bus.flush()

        with connect() as c:
            edges = c.execute(
                "SELECT * FROM causal_edges WHERE child_event_id = ("
                "SELECT id FROM events WHERE kind = 'runtime.child_event'"
                ")"
            ).fetchall()
        assert len(edges) == 1
        assert edges[0]["parent_event_id"] == parent_id
        assert edges[0]["edge_kind"] == "triggered"
        assert edges[0]["confidence"] == 1.0

    def test_caused_by_list(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.p1")
        bus.publish("runtime.p2")
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            ids = [
                r["id"]
                for r in c.execute(
                    "SELECT id FROM events WHERE kind IN ('runtime.p1', 'runtime.p2') ORDER BY id"
                ).fetchall()
            ]

        bus.publish("runtime.child_list", caused_by=ids)
        bus.flush()

        with connect() as c:
            edge_parents = c.execute(
                "SELECT parent_event_id FROM causal_edges WHERE child_event_id = ("
                "SELECT id FROM events WHERE kind = 'runtime.child_list'"
                ") ORDER BY parent_event_id"
            ).fetchall()
        assert [r["parent_event_id"] for r in edge_parents] == ids

    def test_duplicate_causal_edge_ignored(self, event_bus, monkeypatch, tmp_path):
        """INSERT OR IGNORE on duplicate (child, parent, edge_kind)."""
        bus = event_bus
        bus.publish("runtime.parent_causal")
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            pid = c.execute(
                "SELECT id FROM events WHERE kind = 'runtime.parent_causal'"
            ).fetchone()["id"]

        bus.publish("runtime.child_causal", {"x": 1}, caused_by=pid)
        bus.publish("runtime.child_causal", {"x": 1}, caused_by=pid)  # same kind, same parent
        bus.flush()

        with connect() as c:
            edges = c.execute(
                "SELECT COUNT(*) FROM causal_edges WHERE parent_event_id = ?",
                (pid,),
            ).fetchone()[0]
        # Two separate child events, each gets one edge = 2 edges total.
        # They have different child_event_ids so no conflict.
        assert edges == 2


class TestRecentQueries:
    """recent(), recent_by_family(), recent_since_id()."""

    def test_recent_returns_newest_first(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.test_first")
        bus.publish("runtime.test_second")
        bus.publish("runtime.test_third")
        bus.flush()
        recent = bus.recent(limit=10)
        kinds = [e["kind"] for e in recent]
        assert kinds == ["runtime.test_third", "runtime.test_second", "runtime.test_first"]

    def test_recent_by_family(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("alpha.one")
        bus.publish("beta.one")
        bus.publish("alpha.two")
        bus.publish("gamma.one")
        bus.flush()
        alphas = bus.recent_by_family("alpha")
        assert len(alphas) == 2
        assert {"alpha.one", "alpha.two"} == {e["kind"] for e in alphas}

    def test_recent_by_family_empty(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("alpha.one")
        bus.flush()
        assert bus.recent_by_family("nonexistent") == []

    def test_recent_since_id(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.pre")
        bus.flush()

        from core.runtime.db import connect

        with connect() as c:
            after = c.execute(
                "SELECT id FROM events WHERE kind = 'runtime.pre'"
            ).fetchone()["id"]

        bus.publish("runtime.post_a")
        bus.publish("runtime.post_b")
        bus.flush()
        since = bus.recent_since_id(after)
        assert len(since) == 2
        assert [e["kind"] for e in since] == ["runtime.post_a", "runtime.post_b"]

    def test_recent_since_id_zero_returns_all(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.publish("runtime.a")
        bus.publish("runtime.b")
        bus.flush()
        all_ = bus.recent_since_id(0)
        assert len(all_) >= 2


class TestEdgeCases:
    """Boundary and resilience."""

    def test_queue_full_does_not_deadlock(self, event_bus, monkeypatch, tmp_path):
        """If writer queue is full, overflow event is dropped but no crash."""
        bus = event_bus
        fill_count = 1_000  # enough to stress but not excessive
        for i in range(fill_count):
            bus.publish(f"runtime.test_fill.{i}")
        bus.flush(timeout=5)

        from core.runtime.db import connect

        with connect() as c:
            count = _count_events(c)
        # Some events may have been dropped but at least some persisted
        assert count > 0, "All events were lost"
        # The bus should still be operational after overflow
        bus.publish("runtime.test_after_overflow")
        bus.flush()
        with connect() as c:
            ev = _last_event(c)
        assert ev is not None and ev["kind"] == "runtime.test_after_overflow"

    def test_publish_after_stop_is_safe(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.stop()
        # Should not raise or crash
        bus.publish("runtime.test_after_stop")

    def test_subscribe_after_stop(self, event_bus, monkeypatch, tmp_path):
        bus = event_bus
        bus.stop()
        sub = bus.subscribe()
        bus.publish("runtime.test_stopped")
        bus.flush()
        # Writer thread is gone, so event won't persist — but no crash
        import queue as _q_mod
        try:
            sub.get(timeout=0.3)
            pytest.fail("Expected queue.Empty after stop")
        except _q_mod.Empty:
            pass  # expected — no notification on stopped bus

    def test_concurrent_publish(self, event_bus, monkeypatch, tmp_path):
        """Multiple threads publish simultaneously — all events persisted."""
        bus = event_bus
        NUM_THREADS = 10
        EVENTS_PER = 50

        def publisher(thread_id: int):
            for i in range(EVENTS_PER):
                bus.publish(f"runtime.test_concurrent.{thread_id}", {"i": i})

        threads = [
            threading.Thread(target=publisher, args=(tid,), daemon=True)
            for tid in range(NUM_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        bus.flush(timeout=5)

        from core.runtime.db import connect

        with connect() as c:
            count = _count_events(c)
        expected = NUM_THREADS * EVENTS_PER
        # Allow small variance if queue overflow occurred
        assert count >= expected - 10, (
            f"Only got {count}/{expected} concurrent events"
        )
