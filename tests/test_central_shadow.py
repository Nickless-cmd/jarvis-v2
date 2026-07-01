"""Tests for core/services/central_shadow.py — M1 shadow-mode (ingen aktiv ændring)."""
from __future__ import annotations

import pytest

from core.services import central_shadow as sh
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


@pytest.fixture
def observed(monkeypatch):
    rec = []
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central",
                        lambda: type("C", (), {"observe": lambda s, e: rec.append(dict(e))})())
    return rec


# ── HÅRD invariant ──

def test_active_apply_is_hardcoded_false():
    assert sh.ACTIVE_APPLY is False


def test_shadow_reactions_never_apply(observed, monkeypatch):
    import core.services.central_learning as cl
    monkeypatch.setattr(cl, "propose_adjustments",
                        lambda **k: [{"kind": "investigate_degrading", "target": "loop/lifecycle",
                                      "action": "undersøg X"}])
    out = sh.shadow_reactions()
    assert out and out[0]["target"] == "loop/lifecycle"
    # logget som skygge med applied=False
    shadow = [o for o in observed if o.get("nerve") == "shadow_reaction"]
    assert shadow and shadow[0]["shadow"] is True and shadow[0]["applied"] is False


# ── prædiktion ──

def test_trend_worsening_detects_rising_latency():
    for v in (10, 12, 11, 200, 210, 220):  # tydelig stigning i sidste halvdel
        central_timeseries.record("system", "central_meta", value=float(v))
    worse, newer, older = sh._trend_worsening("system", "central_meta", higher_is_worse=True)
    assert worse is True and newer > older


def test_trend_stable_not_flagged():
    for v in (10, 11, 10, 11, 10, 11):
        central_timeseries.record("system", "central_meta", value=float(v))
    worse, _, _ = sh._trend_worsening("system", "central_meta", higher_is_worse=True)
    assert worse is False


def test_predict_trends_warns_when_approaching(observed):
    # latency stiger mod 250-tærsklen (>=60% = 150)
    for v in (120, 130, 125, 180, 200, 210):
        central_timeseries.record("system", "central_meta", value=float(v))
    preds = sh.predict_trends()
    assert any(p["target"] == "system/central_meta" for p in preds)
    assert any(o.get("nerve") == "shadow_prediction" for o in observed)


def test_predict_trends_silent_when_far_from_threshold(observed):
    # stiger men langt under tærsklen (<60% af 250 = 150) → ingen advarsel
    for v in (5, 6, 5, 20, 25, 30):
        central_timeseries.record("system", "central_meta", value=float(v))
    preds = sh.predict_trends()
    assert not any(p["target"] == "system/central_meta" for p in preds)


# ── tick ──

def test_tick_reports_apply_off(observed, monkeypatch):
    import core.services.central_learning as cl
    monkeypatch.setattr(cl, "propose_adjustments", lambda **k: [])
    res = sh.run_shadow_tick()
    assert res["status"] == "ok" and res["active_apply"] is False
    summary = [o for o in observed if o.get("nerve") == "shadow"]
    assert summary and summary[0]["active_apply"] is False


def test_never_raises(monkeypatch):
    import core.services.central_learning as cl
    monkeypatch.setattr(cl, "propose_adjustments",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("boom")))
    sh.shadow_reactions()   # må ikke kaste
    sh.run_shadow_tick()    # må ikke kaste
