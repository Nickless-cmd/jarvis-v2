"""Surface-test (dark-edges batch 1) — se tests/test_tool_infra_surfaces.py for moensteret."""
from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    """Frisk sqlite-DB som ALLE de steder surface'erne henter `connect` fra peger paa."""
    path = tmp_path / "jarvis.db"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    import core.runtime.db as dbmod
    import core.runtime.db_composites as dbc
    import core.runtime.db_core as dbcore
    import core.runtime.db_runtime_tasks as dbt
    import core.services.causal_inference_daemon as cid
    monkeypatch.setattr(dbmod, "connect", _connect)
    monkeypatch.setattr(dbcore, "connect", _connect)
    monkeypatch.setattr(dbc, "connect", _connect)
    monkeypatch.setattr(dbt, "connect", _connect)
    monkeypatch.setattr(cid, "connect", _connect)
    return _connect


@pytest.fixture
def bus(monkeypatch):
    """In-memory eventbus: publish() skriver, recent_by_family() laeser det samme."""
    from core.eventbus.bus import event_bus
    log: list[dict] = []

    def publish(kind, payload=None, **_):
        log.insert(0, {"kind": kind, "payload": dict(payload or {})})

    def recent_by_family(family, *, limit=50):
        return [e for e in log if e["kind"].startswith(f"{family}.")][:limit]

    monkeypatch.setattr(event_bus, "publish", publish)
    monkeypatch.setattr(event_bus, "recent_by_family", recent_by_family)
    return log


def _ok(s, mode):
    assert s["mode"] == mode
    assert isinstance(s["signals"], dict)
    assert isinstance(s["summary"], str) and s["summary"]
    return s


def _inactive(s, mode, why):
    _ok(s, mode)
    assert s["active"] is False
    assert why in s["reason"], s["reason"]
    return s



# ── 6. tool_router_runtime ───────────────────────────────────────────────────

def test_tool_router_runtime_surface(db, bus):
    import core.services.tool_router_runtime as r
    _inactive(r.build_tool_router_runtime_surface(), "tool-router-runtime", "findes ikke")
    with db() as c:
        c.execute("CREATE TABLE tool_router_decisions (created_at TEXT)")
        c.execute("CREATE TABLE tool_router_load_more (created_at TEXT)")
        for _ in range(10):
            c.execute("INSERT INTO tool_router_decisions VALUES (datetime('now'))")
        for _ in range(2):
            c.execute("INSERT INTO tool_router_load_more VALUES (datetime('now'))")
        c.execute("INSERT INTO tool_router_decisions VALUES (datetime('now','-30 days'))")  # uden for vinduet
        c.commit()
    s = _ok(r.build_tool_router_runtime_surface(), "tool-router-runtime")
    assert s["active"] is True
    assert (s["signals"]["decisions_7d"], s["signals"]["load_more_7d"],
            s["signals"]["load_more_rate_7d"]) == (10, 2, 0.2)
    assert s["signals"]["recorded_runs"] == 0 and s["signals"]["last_run"] is None
    assert s["signals"]["threshold_applied_by_daemon"] is False
    r.event_bus.publish("tool_router.daemon_run", {"started_at": "t0", "embeddings_warmed": 7,
                                                   "threshold_proposed": 0.5})
    s = r.build_tool_router_runtime_surface()
    assert s["signals"]["recorded_runs"] == 1
    assert s["signals"]["last_run"] == {"started_at": "t0", "embeddings_warmed": 7, "threshold_proposed": 0.5}
