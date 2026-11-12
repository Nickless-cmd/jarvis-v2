"""Test the predictive self-model prompt section (English after audit #3)."""

from __future__ import annotations

from core.services import self_model_predictive as smp


def test_section_renders_english_when_data_present(monkeypatch):
    fake = {
        "tick_quality": {"avg": 52.5, "samples": 200, "trend": "degrading", "last_5_avg": 45.0},
        "mood_baseline": {"content": {"mean": 0.45, "stdev": 0.05}},
        "adherence": {"adherence_rate": "80%", "total": 37, "flag": None},
        "crisis_frequency_30d": {"count": 6, "per_week": 1.4, "by_kind": {"existential_moment": 3}},
        "productive_idle_ratio_7d": 0.3,
    }
    monkeypatch.setattr(smp, "build_predictive_self_model", lambda days=14: fake)
    out = smp.predictive_self_model_section()
    assert "Who you *empirically* are" in out
    assert "Tick quality:" in out
    assert "Mood baseline:" in out
    assert "Decision adherence:" in out
    assert "Crises last 30 days:" in out
    assert "Productive idle ratio" in out
    # No leftover Danish.
    for danish in ("Hvem du", "Tick-kvalitet", "Stemnings", "Beslutnings", "Kriser", "Produktivt"):
        assert danish not in out


def test_section_empty_when_no_signal(monkeypatch):
    monkeypatch.setattr(smp, "build_predictive_self_model", lambda days=14: {})
    assert smp.predictive_self_model_section() == ""


def test_section_viser_afventende_forudsigelse(monkeypatch):
    """En forudsigelse der endnu ikke er moden skal være synlig, ikke skjult."""
    fake = {
        "tick_quality": {"avg": 52.5, "samples": 200, "trend": "stable", "last_5_avg": 50.0},
        "self_prediction": {"n": 0, "accuracy": None, "pending": 1},
    }
    monkeypatch.setattr(smp, "build_predictive_self_model", lambda days=14: fake)
    out = smp.predictive_self_model_section()
    assert "Self-prediction" in out
    assert "afventer" in out


def test_section_viser_brier_naar_der_er_data(monkeypatch):
    fake = {
        "tick_quality": {"avg": 52.5, "samples": 200, "trend": "stable", "last_5_avg": 50.0},
        "self_prediction": {"n": 4, "accuracy": 0.5, "brier": 0.31, "pending": 0},
    }
    monkeypatch.setattr(smp, "build_predictive_self_model", lambda days=14: fake)
    out = smp.predictive_self_model_section()
    assert "0.5 hit-rate (n=4)" in out
    assert "Brier=0.31" in out
