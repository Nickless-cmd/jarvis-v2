"""Tests for core/services/central_coverage.py — runtime-målt surface-count + dækning (Fase 1c)."""
from __future__ import annotations

import pytest

from core.services import central_coverage as cov
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def _bind_recent(monkeypatch, events):
    import core.eventbus.bus as bus

    class _Bus:
        def recent(self, limit=2000):
            return [{"kind": k} for k in events][:limit]
    monkeypatch.setattr(bus, "event_bus", _Bus())


def test_surface_count_is_runtime_measured(monkeypatch):
    """Surface-antal kommer fra det LEVENDE registry, ikke et hardcodet tal."""
    monkeypatch.setattr(cov, "_DEFAULT_WINDOW", 10)
    import core.services.signal_surface_router as sr
    monkeypatch.setattr(sr, "_get_router", lambda: {f"s{i}": (lambda: {}) for i in range(42)})
    _bind_recent(monkeypatch, [])
    m = cov.measure()
    assert m["surfaces_registered"] == 42  # = len(registry), ikke en konstant


def test_volume_coverage_reproducible(monkeypatch):
    """volume_coverage = routed-events / alle-events i vinduet (reproducerbar)."""
    # 3 somatic (routed via PRIVATE_NO_EGRESS) + 1 helt-ukendt family → 3/4 = 0.75.
    _bind_recent(monkeypatch, ["somatic.note", "somatic.note", "somatic.note", "zzz_unknown.x"])
    m = cov.measure(window=100)
    assert m["events_in_window"] == 4
    assert m["families_seen"] == 2
    # somatic er routed; zzz_unknown er ikke → 3/4
    assert m["volume_coverage"] == 0.75
    # family_coverage_seen: 1 af 2 sete familier routes → 0.5
    assert m["family_coverage_seen"] == 0.5


def test_empty_window_no_crash(monkeypatch):
    _bind_recent(monkeypatch, [])
    m = cov.measure()
    assert m["events_in_window"] == 0
    assert m["volume_coverage"] is None and m["family_coverage_seen"] is None


def test_record_writes_timeseries(monkeypatch):
    _bind_recent(monkeypatch, ["impulse.tick", "memory.write"])
    cov.record_coverage(window=50)
    # nøgletal endte i tidsserien (cluster=system)
    assert central_timeseries.recent("system", "coverage_surfaces")
    assert central_timeseries.recent("system", "coverage_volume")


def test_tick_and_surface_self_safe(monkeypatch):
    _bind_recent(monkeypatch, ["impulse.tick"])
    res = cov.run_coverage_tick()
    assert res["status"] == "ok"
    surf = cov.build_central_coverage_surface()
    assert surf["active"] is True and "surfaces_registered" in surf
