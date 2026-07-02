"""Tests for core/services/central_signal_health.py — hub meta-liveness + signal-korrekthed (Fase 1e)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.services import central_signal_health as sh
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def _ts(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _merged(fresh=("cognitive_conductor", "cognitive_state_assembly", "signal_surface_router"),
            stale=(), missing=("visible_turn_tracking",), sensory_total=None):
    m = {}
    for n in fresh:
        m[f"cognition:{n}"] = {"api": {"ts": _ts(5), "meta": {}}}
    for n in stale:
        m[f"cognition:{n}"] = {"api": {"ts": _ts(300), "meta": {}}}  # 5t gammel
    # missing = udelades helt
    if sensory_total is not None:
        m["sensory:archive"] = {"runtime": {"ts": _ts(2), "meta": {"total": sensory_total}}}
    return m


def test_hub_liveness_classifies(monkeypatch):
    m = _merged(fresh=("cognitive_conductor", "cognitive_state_assembly"),
                stale=("signal_surface_router",), missing=("visible_turn_tracking",))
    r = sh.hub_liveness(merged=m)
    assert r["live"] == 2 and r["stale"] == 1 and r["missing"] == 1
    assert r["all_live"] is False
    assert r["hubs"]["visible_turn_tracking"]["state"] == "missing"
    assert r["hubs"]["signal_surface_router"]["state"] == "stale"


def test_hub_all_live(monkeypatch):
    m = _merged(fresh=("cognitive_conductor", "cognitive_state_assembly",
                       "signal_surface_router", "visible_turn_tracking"), missing=())
    r = sh.hub_liveness(merged=m)
    assert r["all_live"] is True and r["live"] == 4


def test_nerves_observed_xproc(monkeypatch):
    m = _merged()
    assert sh.nerves_observed_xproc(merged=m) == len(m)


def test_signal_correctness_reports_reality(monkeypatch):
    import core.runtime.db_sensory as dbs
    monkeypatch.setattr(dbs, "count_sensory_memories", lambda modality=None: 100)
    # observeret total=98 ≤ db=100 → korrekt
    m = _merged(sensory_total=98)
    r = sh.signal_correctness(merged=m)
    assert r["db_total"] == 100 and r["observed_total"] == 98 and r["correct"] is True


def test_signal_correctness_flags_stuck_zero(monkeypatch):
    import core.runtime.db_sensory as dbs
    monkeypatch.setattr(dbs, "count_sensory_memories", lambda modality=None: 100)
    # sensoren rapporterer 0 mens DB har 100 → sensoren lyver → ikke korrekt
    m = _merged(sensory_total=0)
    r = sh.signal_correctness(merged=m)
    assert r["correct"] is False


def test_signal_correctness_no_observation(monkeypatch):
    import core.runtime.db_sensory as dbs
    monkeypatch.setattr(dbs, "count_sensory_memories", lambda modality=None: 100)
    m = _merged(sensory_total=None)  # ingen sensory-observation
    r = sh.signal_correctness(merged=m)
    assert r["observed_total"] is None and r["correct"] is None


def test_tick_and_surface_self_safe(monkeypatch):
    monkeypatch.setattr(sh, "_merged", lambda: _merged())
    import core.runtime.db_sensory as dbs
    monkeypatch.setattr(dbs, "count_sensory_memories", lambda modality=None: 0)
    res = sh.run_signal_health_tick()
    assert res["status"] == "ok"
    surf = sh.build_central_signal_health_surface()
    assert surf["active"] is True and "hubs" in surf
