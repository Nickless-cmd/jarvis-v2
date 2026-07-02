"""Tests for core/services/central_growth_observe.py — C vækst-observation (LivingNeuron-data).

Fase 1b: inner-drive-gauge er nu et ÆGTE rate-signal (cursor-baseret delta), ikke et
mættende last-50-count. Og alle egress-fri writes går via den kanoniske record_private-kontrakt."""
from __future__ import annotations

import pytest

from core.services import central_growth_observe as go
from core.services import central_timeseries


class _FakeSink:
    def __init__(self):
        self.records = []

    def record(self, rec):
        self.records.append(rec)


class _FakeCache:
    """In-memory stand-in for shared_cache (cursor-lager) — deterministisk pr. test."""
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, *, ttl_seconds=0):
        self.store[key] = value


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def _bind_bus(monkeypatch, per_family):
    """Fake bus: hver familie får `n` rows med stigende event-id'er (til delta-beregning)."""
    import core.eventbus.bus as bus

    class _Bus:
        def recent_by_family(self, fam, limit=50):
            n = per_family.get(fam, 0)
            # nyeste først (ORDER BY id DESC), id'er 1..n
            return [{"kind": f"{fam}.x", "id": i} for i in range(n, 0, -1)][:limit]
    monkeypatch.setattr(bus, "event_bus", _Bus())
    return bus


def test_inner_drive_is_egress_free(monkeypatch):
    """KRITISK (§24.4): inner-drives må ALDRIG ramme central().observe (→ _emit) eller
    eventbus.publish — kun lokal sink + tidsserie (cluster=autonomy)."""
    sink = _FakeSink()
    monkeypatch.setattr(go.central_trace, "sink", lambda: sink)
    monkeypatch.setattr(go, "shared_cache", _FakeCache())
    _bind_bus(monkeypatch, {"impulse": 5, "pressure": 2, "emergent_signal": 0})

    published, observed = [], []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: published.append(a), raising=False)
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(e)})())

    go.observe_inner_drive_activity()

    # egress-frit: skrevet til lokal sink under cluster=autonomy for alle tre familier
    assert {r.cluster for r in sink.records} == {"autonomy"}
    assert {r.nerve for r in sink.records} == {"impulse", "pressure", "emergent_signal"}
    # ALDRIG egress
    assert published == [] and observed == []


def test_inner_drive_delta_semantics(monkeypatch):
    """Gauge = ÆGTE delta (nye events siden sidste tick), ikke mættende last-50-count.
    Første tick sætter cursor → delta 0 (ingen falsk opstarts-spike); næste tick tæller kun nye."""
    monkeypatch.setattr(go.central_trace, "sink", lambda: _FakeSink())
    cache = _FakeCache()
    monkeypatch.setattr(go, "shared_cache", cache)

    # Tick 1: 3 impulse-events (id 1..3). Ingen cursor endnu → delta 0, cursor sat til 3.
    _bind_bus(monkeypatch, {"impulse": 3, "pressure": 0, "emergent_signal": 0})
    c1 = go.observe_inner_drive_activity()
    assert c1["impulse"] == 0
    assert cache.store["growth:cursor:impulse"] == 3

    # Tick 2: nu 5 events (id 1..5) → 2 NYE siden cursor=3 → delta 2, cursor→5.
    _bind_bus(monkeypatch, {"impulse": 5, "pressure": 0, "emergent_signal": 0})
    c2 = go.observe_inner_drive_activity()
    assert c2["impulse"] == 2
    assert cache.store["growth:cursor:impulse"] == 5

    # Tick 3: ingen nye events (stadig id 1..5) → delta 0 (IKKE 5 som last-50-gauge ville give).
    c3 = go.observe_inner_drive_activity()
    assert c3["impulse"] == 0
    # tidsserien bærer rate-signalet
    assert central_timeseries.recent("autonomy", "impulse")[-1].value == 0.0


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
    monkeypatch.setattr(go.central_trace, "sink", lambda: _FakeSink())
    monkeypatch.setattr(go, "shared_cache", _FakeCache())
    _bind_bus(monkeypatch, {})
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: None})())
    res = go.run_growth_observe_tick()
    assert res["status"] == "ok"
    assert "inner_drives" in res


def test_sensory_activity_egress_free(monkeypatch):
    """Sansernes Arkiv → cluster=sensory EGRESS-FRIT: scalar-metadata (total/rate/modalitet),
    ALDRIG indhold, ALDRIG central().observe/eventbus."""
    sink = _FakeSink()
    monkeypatch.setattr(go.central_trace, "sink", lambda: sink)
    import core.runtime.db_sensory as dbs
    monkeypatch.setattr(dbs, "count_sensory_memories",
                        lambda modality=None: {"visual": 10, "audio": 3, "atmosphere": 2,
                                               "mixed": 1}.get(modality, 16))
    import core.services.sensory_archive as sa
    monkeypatch.setattr(sa, "list_recent",
                        lambda limit=100: [{"timestamp": "2099-01-01T00:00:00Z", "content": "HEMMELIG SANSNING"}])

    published, observed = [], []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: published.append(a), raising=False)
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: observed.append(e)})())

    out = go.observe_sensory_activity()
    assert out["total"] == 16 and out["mod_visual"] == 10 and out["recent_1h"] == 1
    # egress-frit: lokal sink under cluster=sensory
    assert sink.records and sink.records[0].cluster == "sensory"
    # ALDRIG egress + intet indhold lækket
    assert published == [] and observed == []
    assert "HEMMELIG" not in str(sink.records[0].payload)


def test_never_raises(monkeypatch):
    monkeypatch.setattr(go.central_trace, "sink",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(go, "shared_cache", _FakeCache())
    go.observe_inner_drive_activity()  # må ikke kaste
    go.run_growth_observe_tick()       # må ikke kaste
