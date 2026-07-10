from __future__ import annotations

from core.services import emergence as em


def test_band_classification():
    assert em._band(0.9) == "emergent"
    assert em._band(0.78) == "emergent"
    assert em._band(0.6) == "brewing"
    assert em._band(0.5) == "brewing"
    assert em._band(0.49) == "weak"
    assert em._band(0.0) == "weak"


def test_brewing_filters_and_enriches(monkeypatch):
    rows = [
        {"pattern_key": "a", "title": "Direction Drift", "confidence": 0.6,
         "evidence_count": 8, "evaluation_count": 4, "last_updated_at": "t"},
        {"pattern_key": "b", "title": "Emergent one", "confidence": 0.85,
         "evidence_count": 9, "evaluation_count": 2, "last_updated_at": "t"},
        {"pattern_key": "c", "title": "Weak one", "confidence": 0.3,
         "evidence_count": 2, "evaluation_count": 1, "last_updated_at": "t"},
    ]
    monkeypatch.setattr(em, "list_patterns", lambda **k: rows)
    brewing = em.brewing_patterns()
    # kun 'a' (0.6) er i brewing-båndet; b er emergent, c er weak
    assert [b["title"] for b in brewing] == ["Direction Drift"]
    b = brewing[0]
    assert b["trajectory"] == "strengthening"  # evaluation_count>=2
    assert b["gap_to_emergent"] == round(0.78 - 0.6, 3)


def test_surface_exposes_brewing_and_felt(monkeypatch):
    rows = [{"pattern_key": "a", "title": "Direction Drift", "summary": "s",
             "status": "candidate", "confidence": 0.6, "evidence_count": 8,
             "evaluation_count": 4, "competing_explanations_json": "[]",
             "confounders_json": "[]", "last_updated_at": "t"}]
    monkeypatch.setattr(em, "list_patterns", lambda **k: rows)
    monkeypatch.setattr(em, "summarize_patterns",
                        lambda: {"candidate": 1, "upgraded": 0, "downgraded": 0,
                                 "rejected": 0, "total": 1})
    surf = em.build_emergence_surface()
    assert surf["active"] is True
    assert surf["summary"]["brewing_count"] == 1
    assert "Direction Drift" in surf["summary"]["felt"]
    assert surf["items"][0]["band"] == "brewing"
    assert len(surf["brewing"]) == 1
