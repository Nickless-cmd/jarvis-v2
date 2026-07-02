"""Tests for core/services/central_stance.py — tvær-modal stance-divergens (Lag 3 v3)."""
from __future__ import annotations

import pytest

from core.services import central_stance as st
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def test_current_tensions_detects_opposition():
    # gut vil frem, men kroppen er i stress → tension
    tensions = st.current_tensions({"gut": "proceed", "somatic": "stress", "contradiction": "consistent"})
    keys = {t["key"] for t in tensions}
    assert "gut:proceed|somatic:stress" in keys


def test_no_tension_when_aligned():
    tensions = st.current_tensions({"gut": "proceed", "somatic": "calm", "contradiction": "consistent"})
    assert tensions == []


def test_classify_from_surfaces(monkeypatch):
    import core.services.gut_engine as ge
    import core.services.somatic_runtime_body as sb
    import core.services.contradiction_engine as ce
    monkeypatch.setattr(ge, "build_gut_surface",
                        lambda: {"state": {"last_hunch": "proceed → interrupted"}}, raising=False)
    monkeypatch.setattr(sb, "build_somatic_body_surface",
                        lambda: {"levels": {"pressure": 0.99, "startle": 0.9}}, raising=False)
    monkeypatch.setattr(ce, "build_contradiction_engine_surface",
                        lambda: {"active": False, "summary": {"finding_count": 0}}, raising=False)
    s = st.read_current_stances()
    assert s == {"gut": "proceed", "somatic": "stress", "contradiction": "consistent"}


def test_stance_tick_records_tension_to_timeseries(monkeypatch):
    monkeypatch.setattr(st, "read_current_stances",
                        lambda: {"gut": "proceed", "somatic": "stress"})
    out = st.run_stance_tick()
    assert out["status"] == "ok"
    assert "gut:proceed|somatic:stress" in out["tensions"]
    # tension endte i tidsserien
    assert central_timeseries.recent("cognition", "tension:gut:proceed|somatic:stress")


def test_recurring_tensions_threshold(monkeypatch):
    monkeypatch.setattr(st, "read_current_stances",
                        lambda: {"gut": "proceed", "somatic": "stress"})
    for _ in range(4):
        st.run_stance_tick()
    rec = st.recurring_tensions(min_count=3)
    keys = {r["key"] for r in rec}
    assert "gut:proceed|somatic:stress" in keys
    # under tærskel → ikke medtaget
    assert st.recurring_tensions(min_count=10) == []
