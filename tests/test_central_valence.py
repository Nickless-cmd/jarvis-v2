"""Tests for Spec D / D2 — central_valence (Centralens ene følte tilstand, integreret + egress-frit)."""
from __future__ import annotations

import pytest

from core.services import central_valence as cv


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    cv._kv_set(cv._VALENCE_KEY, {})
    yield


def _patch(monkeypatch, *, valence, somatic, stance):
    monkeypatch.setattr(cv, "_read_valence_trajectory", lambda: valence)
    monkeypatch.setattr(cv, "_read_somatic", lambda: somatic)
    monkeypatch.setattr(cv, "_read_stance", lambda: stance)


def test_fresh_instant_grounds_tone(monkeypatch, isolated_runtime):
    """Den friske present-moment-valens (instant) styrer tonen, ikke den langsomme hour-average."""
    _patch(monkeypatch, valence={"score": 0.05, "instant": 0.42, "delta": 0.1, "trend": "neutral"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    felt = cv.integrate_valence()
    assert felt["tone"] == "opløftet"            # instant 0.42 ≥ 0.25
    assert felt["sources"]["instant"] == 0.42
    assert felt["intensity"] >= 0.0


def test_flourishing_trend_no_longer_forces_uplift(monkeypatch, isolated_runtime):
    """Staleness-fixet: en langsom 'flourishing'-trend må IKKE tvinge 'opløftet', når nuet kun er
    mildt. Tonen følger den friske instant (0.1 → 'let'), ikke 24t-trajektorien."""
    _patch(monkeypatch, valence={"score": 0.4, "instant": 0.1, "delta": 0.57, "trend": "flourishing"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    felt = cv.integrate_valence()
    assert felt["tone"] == "let"                 # instant 0.1 → 'let', IKKE 'opløftet'


def test_falls_back_to_average_when_no_instant(monkeypatch, isolated_runtime):
    """Uden instant (fx <1 sample) falder grundtonen tilbage til hour-average score."""
    _patch(monkeypatch, valence={"score": 0.3, "delta": 0.2, "trend": "flourishing"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    assert cv.integrate_valence()["tone"] == "opløftet"   # fallback 0.3 ≥ 0.25


def test_caution_and_tensions_lower_tone(monkeypatch, isolated_runtime):
    """Integration: gut-forsigtighed + spændinger trækker tonen NED (ikke valens alene)."""
    _patch(monkeypatch, valence={"score": 0.05, "delta": 0.1, "trend": "steady"},
           somatic={"posture": "braced", "max_level": 0.7},
           stance={"gut": "caution", "somatic": "stress", "tension_count": 3})
    felt = cv.integrate_valence()
    # 0.05 - 0.10 (caution) - 0.15 (somatic stress) - 0.15 (3 tensions) = -0.35 → belastet
    assert felt["score"] < 0 and felt["tone"] == "belastet"
    assert felt["intensity"] > 0.3            # høj kropslig belastning + spændinger = høj intensitet


def test_neutral_when_flat(monkeypatch, isolated_runtime):
    _patch(monkeypatch, valence={"score": 0.0, "delta": 0.0, "trend": "steady"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    assert cv.integrate_valence()["tone"] == "neutral"


def test_tick_persists_durably(monkeypatch, isolated_runtime):
    _patch(monkeypatch, valence={"score": 0.3, "delta": 0.2, "trend": "flourishing"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    res = cv.run_valence_tick()
    assert res["status"] == "ok" and res["tone"] == "opløftet"
    assert cv.get_valence_state()["tone"] == "opløftet"     # durabelt (overlever genstart)


def test_egress_free(monkeypatch, isolated_runtime):
    _patch(monkeypatch, valence={"score": 0.1, "delta": 0.1, "trend": "steady"},
           somatic={"posture": "steady", "max_level": 0.0},
           stance={"gut": "proceed", "somatic": "calm", "tension_count": 0})
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    cv.run_valence_tick()
    assert published == []                     # følt tilstand er privat — aldrig til bussen


def test_self_safe_all_sources_fail(monkeypatch, isolated_runtime):
    monkeypatch.setattr(cv, "_read_valence_trajectory", lambda: {"score": 0.0, "delta": 0.0, "trend": None})
    monkeypatch.setattr(cv, "_read_somatic", lambda: {"posture": None, "max_level": 0.0})
    monkeypatch.setattr(cv, "_read_stance", lambda: {"gut": None, "somatic": None, "tension_count": 0})
    assert cv.integrate_valence()["tone"] == "neutral"
