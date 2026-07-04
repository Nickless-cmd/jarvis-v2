"""Tests for PULSE — kroppens kort som en sans (LivingNeuron-council)."""
from __future__ import annotations

import core.services.central_body_map_pulse as pulse


def _fake_coverage(**kw):
    base = {"available": True, "total": 819, "connected": 451, "dark": 50,
            "llm_waste": 42, "silent": 277, "structural_ratio": 0.55, "dark_ratio": 0.061}
    base.update(kw)
    return base


def test_sense_unavailable_when_matrix_missing(monkeypatch):
    monkeypatch.setattr("core.services.central_coverage.structural_coverage",
                        lambda: {"available": False})
    assert pulse.sense_body_map() == {"available": False}


def test_sense_maps_scalars_and_zero_delta_first_time(monkeypatch):
    monkeypatch.setattr("core.services.central_coverage.structural_coverage", _fake_coverage)
    monkeypatch.setattr(pulse, "_kv_get", lambda k, d: d)  # ingen tidligere snapshot
    s = pulse.sense_body_map()
    assert s["available"] and s["total"] == 819 and s["dark"] == 50 and s["llm_waste"] == 42
    assert s["coverage"] == 0.55
    # første gang: intet snapshot → delta 0
    assert s["dark_delta"] == 0 and s["connected_delta"] == 0


def test_sense_computes_delta_against_snapshot(monkeypatch):
    monkeypatch.setattr("core.services.central_coverage.structural_coverage",
                        lambda: _fake_coverage(dark=54, connected=449))
    monkeypatch.setattr(pulse, "_kv_get",
                        lambda k, d: {"dark": 50, "connected": 451, "llm_waste": 42, "total": 819})
    s = pulse.sense_body_map()
    assert s["dark_delta"] == 4        # 4 neuroner mørkere
    assert s["connected_delta"] == -2  # 2 færre koblet


def test_describe_body_map_speaks_only_on_change(monkeypatch):
    # intet skift → tavs
    monkeypatch.setattr(pulse, "sense_body_map",
                        lambda: {"available": True, "dark_delta": 0})
    assert pulse.describe_body_map() == []
    # mørkere → mærkes
    monkeypatch.setattr(pulse, "sense_body_map",
                        lambda: {"available": True, "dark_delta": 4})
    line = pulse.describe_body_map()
    assert line and "mørkere" in line[0] and "4" in line[0]
    # lysere → mærkes med anden ordlyd
    monkeypatch.setattr(pulse, "sense_body_map",
                        lambda: {"available": True, "dark_delta": -3})
    assert "lysere" in pulse.describe_body_map()[0]


def test_run_tick_skips_when_unavailable(monkeypatch):
    monkeypatch.setattr(pulse, "sense_body_map", lambda: {"available": False})
    out = pulse.run_body_map_pulse_tick()
    assert out["status"] == "skip"


def test_run_tick_emits_and_snapshots(monkeypatch):
    monkeypatch.setattr(pulse, "sense_body_map",
                        lambda: {"available": True, "coverage": 0.55, "dark": 50,
                                 "dark_delta": 4, "dark_ratio": 0.06, "connected": 451,
                                 "llm_waste": 42, "llm_waste_delta": 0, "total": 819})
    recorded = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: recorded.append((c, n)))
    saved = {}
    monkeypatch.setattr(pulse, "_kv_set", lambda k, v: saved.update({k: v}))
    out = pulse.run_body_map_pulse_tick()
    assert out["status"] == "ok" and out["dark_delta"] == 4
    # tre nerver emitteret i connections-clusteret
    assert ("connections", "coverage") in recorded
    assert ("connections", "dark_delta") in recorded
    assert ("connections", "decoupled_llm") in recorded
    # snapshot gemt til næste delta
    assert saved[pulse._SNAP_KEY]["dark"] == 50


def test_never_raises_on_broken_coverage(monkeypatch):
    def boom():
        raise RuntimeError("matrix korrupt")
    monkeypatch.setattr("core.services.central_coverage.structural_coverage", boom)
    # sense sluger fejlen → unavailable, ingen exception
    assert pulse.sense_body_map() == {"available": False}
    assert pulse.describe_body_map() == []
