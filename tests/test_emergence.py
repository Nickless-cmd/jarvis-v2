"""Emergence-detektoren — hvad der overlever, og hvad der skal nedgraderes.

13/11-2026: `detect_and_score_patterns` persisterede kandidater, men en række
hvis mønster holdt op med at generere en kandidat blev aldrig rørt. Den blev
stående som «upgraded» med frosset confidence, og fladen og initiativ-broen
blev ved med at læse den. Målt i den ægte base stod `capability_growth_procedures`
med conf=1.0 og «27 procedures indicate expanding stable capability», hvor de
27 rækker var en write-only bank uden hit.

Testene her rammer den grænse ændringen FAKTISK håndhæver: en række UDEN
kandidat nedgraderes, en række MED kandidat røres ikke.

Den retter ikke den underliggende påstand — at et absolut antal er en vækst.
Det er en anden fejl, og den skal ikke kunne læses ud af grønne tests her.
"""

from __future__ import annotations

import pytest

from core.services import emergence as em


def _kandidat(key: str, *, ev: int = 5) -> em.EmergenceCandidate:
    return em.EmergenceCandidate(
        pattern_key=key,
        title=key.replace("_", " ").title(),
        summary="s",
        evidence_count=ev,
        base_confidence=0.5,
        competing_explanations=[],
        confounders=[],
    )


@pytest.fixture
def miljoe(monkeypatch):
    """Fanger persistering og læsning, så testen måler grænsen — ikke apophenia."""
    state: dict = {"skrevet": [], "laest": [], "persisteret": []}

    monkeypatch.setattr(
        em, "assess_pattern", lambda **k: {"confidence": 0.6, "status": "candidate"}
    )
    monkeypatch.setattr(em.event_bus, "publish", lambda *a, **k: None)
    monkeypatch.setattr(
        em,
        "_create_or_update_pattern",
        lambda **k: (state["skrevet"].append(k), k)[1],
    )

    def _list_patterns(*, status: str = "", limit: int = 120):
        state["laest"].append(status)
        return list(state["persisteret"]) if status == "upgraded" else []

    monkeypatch.setattr(em, "list_patterns", _list_patterns)
    return state


def test_en_upgraded_raekke_uden_kandidat_nedgraderes(miljoe, monkeypatch):
    """Kernen: en evidenskilde der holder op med at fyre må ikke blive ved at reklamere."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])
    miljoe["persisteret"] = [
        {
            "pattern_key": "doed_kilde",
            "title": "Død kilde",
            "summary": "s",
            "confidence": 1.0,
            "evidence_count": 27,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [k for k in miljoe["skrevet"] if k["pattern_key"] == "doed_kilde"]
    assert len(ned) == 1, miljoe["skrevet"]
    assert ned[0]["status"] == "downgraded"
    assert ned[0]["confidence"] <= 0.4, "en frosset conf=1.0 må ikke overleve"
    assert ned[0]["competing_explanations"] == ["evidence_no_longer_generates_candidate"]


def test_en_upgraded_raekke_MED_kandidat_roeres_ikke(miljoe, monkeypatch):
    """Modstykket: nedgraderingen må ikke ramme et mønster der faktisk fyrer."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])
    miljoe["persisteret"] = [
        {
            "pattern_key": "stadig_aktiv",
            "title": "Stadig aktiv",
            "summary": "s",
            "confidence": 0.98,
            "evidence_count": 140,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [
        k
        for k in miljoe["skrevet"]
        if k["pattern_key"] == "stadig_aktiv" and k["status"] == "downgraded"
    ]
    assert ned == [], "et aktivt mønster blev nedgraderet"


def test_nedgraderingen_bevarer_evidence_count(miljoe, monkeypatch):
    """Historikken skal blive stående — ellers kan nedgraderingen ikke efterprøves."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [])
    miljoe["persisteret"] = [
        {
            "pattern_key": "doed_kilde",
            "title": "Død kilde",
            "summary": "s",
            "confidence": 1.0,
            "evidence_count": 27,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [k for k in miljoe["skrevet"] if k["pattern_key"] == "doed_kilde"]
    assert ned[0]["evidence_count"] == 27


def test_kun_upgraded_raekker_gennemgaas(miljoe, monkeypatch):
    """Gennemgangen må ikke skrive i kandidat- og afviste rækker den ikke ejer."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [])

    em.detect_and_score_patterns(window_days=21)

    assert miljoe["laest"] == ["upgraded"], miljoe["laest"]


def test_kandidaterne_persisteres_stadig(miljoe, monkeypatch):
    """Stale-blokken ligger efter hovedløkken — den må ikke sluge den normale vej."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])

    ud = em.detect_and_score_patterns(window_days=21)

    assert len(ud) == 1
    assert any(
        k["pattern_key"] == "stadig_aktiv" and k["status"] == "candidate"
        for k in miljoe["skrevet"]
    )
