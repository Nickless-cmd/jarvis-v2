"""Et confidence-løft kræver at beviset bærer SAMME domæne som drømmen.

Målt før ændringen: `record_evidence_for_hypothesis` koblede bevis til en drøm
alene på id-substring, og to uafhængige pegepinde fra et HELT ANDET område
løftede drømmens confidence via `confirm_dream`. Domænebegrebet er det
eksisterende `dream_domains.DOMAENER` — der er ikke opfundet et nyt.

Valgt håndtering af domæneløst bevis: AFVISES (ikke «svagere»). Se
`record_dream_evidence` for begrundelsen.
"""
from __future__ import annotations

import pytest

from core.services import dream_carry_over as dco


@pytest.fixture(autouse=True)
def _frisk(monkeypatch):
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_save", lambda: None)
    monkeypatch.setattr(dco, "_observe_dream_signal", lambda *a, **k: None)
    monkeypatch.setattr(dco.event_bus, "publish", lambda *a, **k: None)


def _drom(domain: str | None = "memory", confidence: float = 0.5) -> dict:
    kw = {"domain": domain} if domain is not None else {}
    dco.adopt_dream(dream_id="d1", content="Et mønster i hukommelsen", confidence=confidence, **kw)
    return next(d for d in dco._ACTIVE_DREAMS if d["dream_id"] == "d1")


def _bevis(ref: str, **kw):
    return dco.record_dream_evidence(
        "d1", supports=True, source="central_hypothesis_generator",
        evidence="målt", evidence_ref=ref, **kw)


def test_samme_domaene_loefter():
    d = _drom("memory", 0.5)
    assert _bevis("r1", domain="memory")["status"] == "ok"
    ud = _bevis("r2", domain="memory")
    assert ud["decision"] == "confirmed"
    assert d["confidence"] > 0.5


def test_fremmed_domaene_loefter_ikke():
    d = _drom("memory", 0.5)
    for ref in ("r1", "r2", "r3"):
        ud = _bevis(ref, domain="creativity")
        assert ud["status"] == "rejected"
        assert "domæne" in ud["reason"]
    assert d["confidence"] == 0.5
    assert not d.get("confirmed")
    assert not d.get("evidence")


def test_domaeneloest_bevis_afvises_og_loefter_ikke():
    d = _drom("memory", 0.5)
    for ref in ("r1", "r2", "r3"):
        ud = _bevis(ref)  # intet domain
        assert ud["status"] == "rejected"
    assert d["confidence"] == 0.5
    assert not d.get("evidence")


def test_ugyldigt_domaene_afvises():
    d = _drom("memory", 0.5)
    assert _bevis("r1", domain="ikke-et-domaene")["status"] == "rejected"
    assert d["confidence"] == 0.5


def test_droem_uden_domaene_kan_ikke_loeftes():
    d = _drom(None, 0.5)
    assert _bevis("r1", domain="memory")["status"] == "rejected"
    assert d["confidence"] == 0.5


def test_ugyldigt_domaene_paa_droemmen_gemmes_ikke():
    d = _drom("lorteord", 0.5)
    assert not d.get("domain")


def test_bro_videregiver_domaene():
    _drom("memory", 0.5)
    ramte = dco.record_evidence_for_hypothesis(
        "d1", supports=True, source="x", evidence="e", evidence_ref="r1", domain="creativity")
    assert ramte == []
    ramte = dco.record_evidence_for_hypothesis(
        "d1", supports=True, source="x", evidence="e", evidence_ref="r1", domain="memory")
    assert ramte == ["d1"]
