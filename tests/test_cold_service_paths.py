"""First access and warm access must have distinct, verified behavior."""
from core.services import central_timeseries as ts
from core.services.prompt_sections import tool_discovery_nudge as nudge


def test_timeseries_restores_once_before_first_record(monkeypatch):
    stored = {"central_timeseries_durable": {"old\x1fnerve": [["2026-09-29T00:00:00+00:00", 4.0, {"source": "disk"}]]}}
    reads = []
    monkeypatch.setattr(ts, "_kv_get", lambda key, default: (reads.append(key), stored.get(key, default))[1])
    monkeypatch.setattr(ts, "_durability_on", lambda: True)
    monkeypatch.setattr(ts, "_maybe_persist", lambda: None)
    ts._reset_for_tests()
    try:
        ts.record("new", "nerve", 9.0)
        assert ts.snapshot()["old:nerve"] == {
            "count": 1, "latest": 4.0, "meta": {"source": "disk"},
            "ts": "2026-09-29T00:00:00+00:00", "recent": [4.0],
        }
        assert ts.snapshot()["new:nerve"]["latest"] == 9.0
        ts.record("new", "nerve", 10.0)
        assert reads == ["central_timeseries_durable"]
    finally:
        ts._reset_for_tests()


def test_nudge_core_names_cold_db_read_then_warm_cache_hit(monkeypatch):
    import core.runtime.db as db
    import time

    calls = []

    class Cursor:
        def fetchone(self):
            return ('["bash"]',)

    class Connection:
        def execute(self, query):
            calls.append(query)
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    cache = {"navne": frozenset(), "hentet": 0.0}
    monkeypatch.setattr(nudge, "_KERNE_CACHE", cache)
    monkeypatch.setattr(db, "connect", lambda: Connection())
    monkeypatch.setattr(time, "monotonic", lambda: 1000.0)

    assert nudge._kernens_navne() == frozenset({"bash"})
    assert cache == {"navne": frozenset({"bash"}), "hentet": 1000.0}
    assert nudge._kernens_navne() == frozenset({"bash"})
    assert calls == [
        "SELECT always_core_names_json FROM tool_router_decisions ORDER BY id DESC LIMIT 1"
    ]
