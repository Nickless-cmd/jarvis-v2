"""Tests for DIASTOLE — det følte åndedræt (LivingNeuron-council). SHADOW-første skridt."""
from __future__ import annotations

import core.services.central_cadence_conductor as cc


# --- tempo_scalar: den hårde klemme [0.5, 2.0] + fejl-sikker baseline ---

def test_tempo_scalar_high_pulse_maps_to_floor():
    # presset (puls 2.0) → hyppigere → laveste multiplier
    assert cc.tempo_scalar(2.0) == 0.5


def test_tempo_scalar_low_pulse_maps_to_ceiling():
    # hvile (puls 0.5) → sjældnere → højeste multiplier
    assert cc.tempo_scalar(0.5) == 2.0


def test_tempo_scalar_normal_pulse_is_baseline():
    assert cc.tempo_scalar(1.0) == 1.0


def test_tempo_scalar_clamps_extreme_low_pulse():
    # puls 0.1 → 1/0.1 = 10 → HÅRDT klemt til 2.0 (aldrig →∞ = sultet daemon)
    assert cc.tempo_scalar(0.1) == 2.0


def test_tempo_scalar_zero_and_none_are_baseline():
    # aldrig →0 (= CPU-brand) og aldrig division-by-zero → fejl-sikker 1.0
    assert cc.tempo_scalar(0.0) == 1.0
    assert cc.tempo_scalar(None) == 1.0
    assert cc.tempo_scalar(-1.0) == 1.0
    assert cc.tempo_scalar("nonsense") == 1.0  # type: ignore[arg-type]


# --- sense_tempo: læser puls + loop-lag-dødemandsknap ---

def test_sense_unavailable_when_no_rhythm(monkeypatch):
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm", lambda: None)
    assert cc.sense_tempo() == {"available": False}


def test_sense_computes_tempo_from_pulse(monkeypatch):
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm",
                        lambda: {"pulse_rate": 2.0})
    monkeypatch.setattr(cc, "_recent_loop_lag_ms", lambda: 0.0)
    s = cc.sense_tempo()
    assert s["available"] and s["pulse_rate"] == 2.0
    assert s["tempo"] == 0.5 and s["throttled_by_loop_lag"] is False


def test_sense_forces_baseline_when_loop_lag_high(monkeypatch):
    # puls VILLE give 0.5, men loopet sulter (≥250ms) → dødemandsknap → tvangs-1.0
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm",
                        lambda: {"pulse_rate": 2.0})
    monkeypatch.setattr(cc, "_recent_loop_lag_ms", lambda: 400.0)
    s = cc.sense_tempo()
    assert s["throttled_by_loop_lag"] is True
    assert s["tempo"] == 1.0  # aldrig speed-up mens loopet er blokeret


def test_sense_not_throttled_just_below_threshold(monkeypatch):
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm",
                        lambda: {"pulse_rate": 0.5})
    monkeypatch.setattr(cc, "_recent_loop_lag_ms", lambda: 249.0)
    s = cc.sense_tempo()
    assert s["throttled_by_loop_lag"] is False and s["tempo"] == 2.0


# --- run tick: emitterer nerven (SHADOW, ingen modulation) ---

def test_run_tick_skips_when_unavailable(monkeypatch):
    monkeypatch.setattr(cc, "sense_tempo", lambda: {"available": False})
    out = cc.run_cadence_tempo_tick()
    assert out["status"] == "skip"


def test_run_tick_emits_cadence_tempo_nerve(monkeypatch):
    monkeypatch.setattr(cc, "sense_tempo",
                        lambda: {"available": True, "pulse_rate": 2.0, "tempo": 0.5,
                                 "throttled_by_loop_lag": False})
    recorded = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: recorded.append((c, n, kw)))
    saved = {}
    monkeypatch.setattr(cc, "_kv_set", lambda k, v: saved.update({k: v}))
    out = cc.run_cadence_tempo_tick()
    assert out["status"] == "ok" and out["tempo"] == 0.5
    assert ("runtime", "cadence_tempo") in [(c, n) for (c, n, _kw) in recorded]
    _c, _n, kw = recorded[0]
    assert kw["value"] == 0.5 and "consuming" in kw["meta"]
    assert saved["cadence_tempo_last"]["tempo"] == 0.5


# --- robusthed: kaster ALDRIG på ødelagt input ---

def test_never_raises_on_broken_rhythm(monkeypatch):
    def boom():
        raise RuntimeError("temporal_rhythm korrupt")
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm", boom)
    assert cc.sense_tempo() == {"available": False}
    assert cc.run_cadence_tempo_tick()["status"] == "skip"


def test_never_raises_on_broken_loop_lag(monkeypatch):
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm",
                        lambda: {"pulse_rate": 1.0})
    def boom():
        raise RuntimeError("loop_lag nede")
    monkeypatch.setattr("core.services.central_loop_lag.recent_peak_ms", boom)
    s = cc.sense_tempo()
    assert s["available"] and s["throttled_by_loop_lag"] is False
