"""Tests for core/services/central_growth_observe.py — C vækst-observation (LivingNeuron-data)."""
from __future__ import annotations

import pytest

from core.services import central_growth_observe as go
from core.services import central_timeseries


class _FakeSink:
    def __init__(self):
        self.records = []

    def record(self, rec):
        self.records.append(rec)


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def _bind_bus(monkeypatch, per_family):
    import core.eventbus.bus as bus

    class _Bus:
        def recent_by_family(self, fam, limit=50):
            return [{"kind": f"{fam}.x"}] * per_family.get(fam, 0)
    monkeypatch.setattr(go, "central_trace", go.central_trace)  # no-op anchor
    monkeypatch.setattr(bus, "event_bus", _Bus())
    return bus


def test_inner_drive_is_egress_free(monkeypatch):
    """KRITISK (§24.4): inner-drives må ALDRIG ramme central().observe (→ _emit) eller
    eventbus.publish — kun lokal sink + tidsserie."""
    sink = _FakeSink()
    monkeypatch.setattr(go.central_trace, "sink", lambda: sink)
    _bind_bus(monkeypatch, {"impulse": 5, "pressure": 2, "emergent_signal": 0})

    published, observed = [], []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: published.append(a), raising=False)
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(e)})())

    counts = go.observe_inner_drive_activity()

    assert counts == {"impulse": 5, "pressure": 2, "emergent_signal": 0}
    # egress-frit: skrevet til lokal sink under cluster=autonomy
    assert {r.cluster for r in sink.records} == {"autonomy"}
    assert {r.nerve for r in sink.records} == {"impulse", "pressure", "emergent_signal"}
    # ALDRIG egress
    assert published == [] and observed == []
    # tidsserie fik data
    assert central_timeseries.recent("autonomy", "impulse")[-1].value == 5.0


def test_index_activity_normal_observe(monkeypatch):
    """semantic-indexer er operationel (ikke privat) → NORMAL observe (cluster=system)."""
    _bind_bus(monkeypatch, {"semantic_indexer": 3})
    observed = []
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(dict(e))})())
    monkeypatch.setattr(go, "build_semantic_indexer_surface", lambda: {"active": True}, raising=False)

    n = go.observe_index_activity()
    assert n == 3
    assert observed and observed[0]["cluster"] == "system"
    assert observed[0]["nerve"] == "semantic_indexer"


def test_tick_returns_ok(monkeypatch):
    sink = _FakeSink()
    monkeypatch.setattr(go.central_trace, "sink", lambda: sink)
    _bind_bus(monkeypatch, {})
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: None})())
    res = go.run_growth_observe_tick()
    assert res["status"] == "ok"
    assert "inner_drives" in res


def test_never_raises(monkeypatch):
    monkeypatch.setattr(go.central_trace, "sink",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    go.observe_inner_drive_activity()  # må ikke kaste
    go.run_growth_observe_tick()       # må ikke kaste
