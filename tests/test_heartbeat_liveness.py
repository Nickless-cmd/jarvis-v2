"""Fejlformen 2026-09-02 / 2026-11-11: flaget påstod liv uden at nogen målte det."""
from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from core.services import heartbeat_scheduler as sched


@pytest.fixture(autouse=True)
def _rene():
    sched._STOP.set()
    sched._THREAD = None
    sched._ITERATION = 0
    sched._WATCHDOG_LAST_ITER = None
    sched._WATCHDOG_THREAD = None
    sched._STOP.clear()
    yield
    sched._STOP.set()
    sched._THREAD = None


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def _write_state(tmp_path, monkeypatch, *, next_tick_minutes_ago, active=1, health="active"):
    now = datetime.now(UTC)
    state = {
        "scheduler_active": active,
        "scheduler_health": health,
        "last_tick_at": _iso(now - timedelta(minutes=next_tick_minutes_ago + 15)),
        "next_tick_at": _iso(now - timedelta(minutes=next_tick_minutes_ago)),
        "interval_minutes": 15,
    }
    path = tmp_path / "HEARTBEAT_STATE.json"
    path.write_text(json.dumps({
        "state": state,
        "recent_ticks": [],
    }), encoding="utf-8")
    import core.runtime.workspace_paths as wp
    from core.runtime import db_heartbeat

    monkeypatch.setattr(wp, "heartbeat_state_path", lambda: path)
    monkeypatch.setattr(db_heartbeat, "get_heartbeat_runtime_state", lambda: state)


def test_status_er_ikke_active_naar_next_tick_er_60_min_overskredet(tmp_path, monkeypatch):
    from core.tools.simple_tools_native import _exec_heartbeat_status

    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=60)
    out = _exec_heartbeat_status({})
    assert out["status"] == "ok"
    assert out["scheduler"]["verdict"] == "STALLED"
    assert "ACTIVE" not in out["text"].split("\n")[0]
    assert "60" in out["text"]  # overskridelsen er synlig


def test_status_eksponerer_iterations(tmp_path, monkeypatch):
    from core.tools.simple_tools_native import _exec_heartbeat_status

    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=1)
    sched._ITERATION = 7
    out = _exec_heartbeat_status({})
    assert out["scheduler"]["iterations"] == 7
    assert "iterations: 7" in out["text"]


def test_status_eksponerer_watchdog_i_ejerprocessen(tmp_path, monkeypatch):
    from core.tools.simple_tools_native import _exec_heartbeat_status

    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=1)

    class _AliveThread:
        @staticmethod
        def is_alive():
            return True

    sched._WATCHDOG_THREAD = _AliveThread()
    out = _exec_heartbeat_status({})
    assert out["scheduler"]["watchdog_running"] is True
    assert "Watchdog running: True" in out["text"]


def test_runtime_start_starter_scheduler_og_watchdog(monkeypatch):
    from core.services import heartbeat_runtime as hb

    calls: list[str] = []
    monkeypatch.setattr(sched, "start", lambda **k: calls.append("scheduler"))
    monkeypatch.setattr(sched, "start_watchdog", lambda: calls.append("watchdog"))
    hb.start_heartbeat_scheduler(name="t")
    assert calls == ["scheduler", "watchdog"]


def test_start_efterlader_ikke_health_active_foer_foerste_iteration(monkeypatch):
    from core.services import heartbeat_runtime as hb

    captured: dict = {}
    monkeypatch.setattr(hb, "load_heartbeat_policy", lambda name: {"enabled": True})
    monkeypatch.setattr(hb, "get_heartbeat_runtime_state", lambda: {"state_id": 1})
    monkeypatch.setattr(hb, "_resolve_tick_activity_state",
                        lambda **k: {"active": False, "stale": False})
    monkeypatch.setattr(hb, "_log_debug", lambda *a, **k: None)

    def _persist(**kw):
        captured.update(kw["overrides"])
        return {"state_id": 1, "updated_at": None}

    monkeypatch.setattr(hb, "_persist_runtime_state_with_diagnostics", _persist)
    hb._prepare_scheduler_startup(name="t")
    assert captured["scheduler_active"] is True
    assert captured["scheduler_health"] != "active"


def test_health_active_saettes_foerst_efter_foerste_gennemloeb(monkeypatch):
    order: list[str] = []
    iteration_at_active: list[int] = []

    class _FakeHb:
        event_bus = type("B", (), {"publish": staticmethod(lambda *a, **k: None)})()

        @staticmethod
        def _poll_heartbeat_schedule_with_trigger(**kw):
            order.append("poll")
            return {}

        @staticmethod
        def _mark_scheduler_health(*, name, health):
            order.append(f"health={health}")
            iteration_at_active.append(sched.iterations())

        @staticmethod
        def poll_heartbeat_schedule(*, name):
            return {}

    import core.services as pkg
    monkeypatch.setattr(pkg, "heartbeat_runtime", _FakeHb)
    monkeypatch.setattr(sched, "INTERVAL_SECONDS", 0.01)
    t = threading.Thread(target=sched._loop,
                         kwargs={"name": "t", "startup_recovery_requested": False}, daemon=True)
    t.start()
    time.sleep(0.1)
    sched._STOP.set()
    t.join(timeout=1.0)
    assert order[:2] == ["poll", "health=active"]
    assert iteration_at_active == [1]


def _fake_hb(monkeypatch, *, next_minutes_ago):
    now = datetime.now(UTC)
    state = {
        "scheduler_active": 1, "scheduler_health": "active", "interval_minutes": 15,
        "next_tick_at": _iso(now - timedelta(minutes=next_minutes_ago)),
        "last_tick_at": _iso(now - timedelta(minutes=next_minutes_ago + 15)),
    }

    class _FakeHb:
        @staticmethod
        def get_heartbeat_runtime_state():
            return state

    import core.services as pkg
    monkeypatch.setattr(pkg, "heartbeat_runtime", _FakeHb)


def test_vagten_genstarter_kun_ved_stalled_og_ufoerandret_iterations(monkeypatch):
    _fake_hb(monkeypatch, next_minutes_ago=60)
    calls: list[str] = []
    incidents: list[dict] = []
    monkeypatch.setattr(sched, "stop", lambda **k: calls.append("stop"))
    monkeypatch.setattr(sched, "start", lambda **k: calls.append("start"))
    import core.runtime.db_central_incidents as ci
    monkeypatch.setattr(ci, "record_central_incident", lambda **k: incidents.append(k))

    first = sched.watchdog_check()  # baseline
    assert first["restarted"] is False and calls == []
    second = sched.watchdog_check()  # uændret iterations -> genstart
    assert second["restarted"] is True
    assert calls == ["stop", "start"]
    assert incidents and incidents[0]["severity"] == "error"


def test_vagten_lader_en_taellende_traad_vaere(monkeypatch):
    _fake_hb(monkeypatch, next_minutes_ago=60)
    calls: list[str] = []
    monkeypatch.setattr(sched, "stop", lambda **k: calls.append("stop"))
    monkeypatch.setattr(sched, "start", lambda **k: calls.append("start"))
    sched.watchdog_check()
    sched._ITERATION += 10
    assert sched.watchdog_check()["restarted"] is False
    assert calls == []


def test_ulaeseligt_next_tick_er_ikke_active():
    """Et tidsstempel vi ikke kan læse er en MANGLENDE måling, ikke «alt fint».

    Uden denne gren gav `_parse_iso(...) -> None` overdue=0, og en aktiv
    scheduler med en levende tråd blev dømt ACTIVE på skrald — samme fejlform
    som flaget selv: en tilstand der påstås uden at være målt.
    """
    dom = sched.assess_liveness(
        scheduler_active=1,
        scheduler_health="active",
        next_tick_at="ikke-et-tidspunkt",
        last_tick_at="",
        interval_minutes=15,
        thread_running=True,
        iterations_count=42,
    )
    assert dom["verdict"] == "DEGRADED"
    assert "next_tick_at_unparseable" in dom["mismatch"]


def test_manglende_next_tick_giver_samme_dom_som_ulaeseligt():
    for vaerdi in (None, "", "   "):
        dom = sched.assess_liveness(
            scheduler_active=1,
            scheduler_health="active",
            next_tick_at=vaerdi,
            thread_running=True,
            iterations_count=42,
        )
        assert dom["verdict"] == "DEGRADED", vaerdi
        assert "next_tick_at_unparseable" in dom["mismatch"], vaerdi
