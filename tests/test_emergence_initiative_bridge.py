"""Emergensmotoren skal have en konsekvens, ikke kun en visning.

Rod (Bjørn, 13/11-2026): «emergent motoren skal gøre til en aktiv del af dit
system og den observationer have en handling/konsekvens».

Målt før broen fandtes: 5 mønstre i ``emergent_patterns``, heraf ``Direction
Drift`` med confidence 0.98 og 115 beviser opdaget 7/5-2026 — som aldrig førte
til noget. ``emergence.pattern_candidate_upgraded`` blev publiceret til en
eventbus uden abonnenter, og ``emergence`` blev nævnt nul gange i
``initiative_queue``.

Det der testes her er ikke at broen kalder en funktion. Det er at et mønster
MED evidens bliver en opgave, at et mønster UDEN evidens ikke gør, og at det
samme mønster ikke bliver en ny opgave hver gang confidence bevæger sig.
"""
from __future__ import annotations

import pytest

from core.services import emergence_initiative_bridge as bro


def _moenster(**over):
    grund = {
        "pattern_key": "direction_drift_decisions",
        "title": "Direction Drift",
        "summary": "Beslutninger trækker i forskellige retninger over tid",
        "confidence": 0.98,
        "evidence_count": 115,
        "status": "upgraded",
        "first_detected_at": "2026-05-07T15:03:54Z",
    }
    grund.update(over)
    return grund


@pytest.fixture
def _fanget(monkeypatch):
    """Fanger push_initiative-kald uden at røre databasen."""
    kald: list[dict] = []

    def _push(**kwargs):
        kald.append(kwargs)
        return f"init-{len(kald)}"

    monkeypatch.setattr(
        "core.services.initiative_queue.push_initiative", _push, raising=True
    )
    monkeypatch.setattr(bro, "_allerede_i_koen", lambda _k: False)
    return kald


def test_moenster_med_evidens_bliver_en_opgave(_fanget):
    """DEN BÆRENDE: et opdaget mønster skal ende som et initiativ i køen."""
    res = bro.push_emergents_to_queue([{"pattern": _moenster()}])

    assert len(_fanget) == 1, "mønstret blev ikke gjort til en opgave"
    kald = _fanget[0]
    assert kald["source"] == "emergence"
    assert kald["source_id"] == "direction_drift_decisions"
    assert "Direction Drift" in kald["focus"]
    assert "115" in kald["focus"], "fokus skal bære evidensen, ikke kun titlen"
    assert len(res["pushet"]) == 1


def test_moenster_uden_evidens_afvises_med_grund(_fanget):
    """En formodning er ikke en opgave — og afvisningen skal kunne læses."""
    res = bro.push_emergents_to_queue(
        [{"pattern": _moenster(evidence_count=1, confidence=0.9)}]
    )

    assert _fanget == [], "et mønster med én observation blev gjort til en opgave"
    assert res["afvist"][0]["grund"].startswith("kun 1 observation")


def test_svag_confidence_afvises(_fanget):
    res = bro.push_emergents_to_queue(
        [{"pattern": _moenster(confidence=0.44, status="candidate")}]
    )

    assert _fanget == []
    assert "confidence 0.44" in res["afvist"][0]["grund"]


def test_afvist_moenster_er_en_konklusion_ikke_en_opgave(_fanget):
    """Et mønster apophenia-guarden har afvist, må ikke genopstå som opgave."""
    res = bro.push_emergents_to_queue([{"pattern": _moenster(status="rejected")}])

    assert _fanget == []
    assert "konklusion" in res["afvist"][0]["grund"]


def test_samme_moenster_bliver_ikke_en_ny_opgave(monkeypatch):
    """DEN MÅLTE FEJLFORM: fokus-teksten bærer confidence, så en ny score giver
    ny tekst — og den eksakte tekst-dedup slipper den igennem som en ny post.
    Uden source_id-kontrollen ville hvert 30. tick kunne fordoble køen."""
    kald: list[dict] = []
    monkeypatch.setattr(
        "core.services.initiative_queue.push_initiative",
        lambda **kw: (kald.append(kw), "init-x")[1],
        raising=True,
    )
    # Første gang: ikke i køen. Derefter: den ER i køen.
    svar = {"i_koen": False}
    monkeypatch.setattr(bro, "_allerede_i_koen", lambda _k: svar["i_koen"])

    bro.push_emergents_to_queue([{"pattern": _moenster(confidence=0.98)}])
    svar["i_koen"] = True
    res = bro.push_emergents_to_queue([{"pattern": _moenster(confidence=0.99)}])

    assert len(kald) == 1, "samme mønster blev pushet to gange"
    assert res["afvist"][0]["grund"] == "allerede i køen (source_id)"


def test_fladen_forklarer_hvorfor_motoren_er_tavs(monkeypatch):
    """En motor der ikke gør noget, skal kunne ses at den ikke gør noget."""
    monkeypatch.setattr(
        "core.services.emergence.list_patterns",
        lambda **_kw: [
            _moenster(),
            _moenster(pattern_key="svag", title="Svag", confidence=0.2, evidence_count=2),
        ],
        raising=True,
    )

    flade = bro.build_emergence_initiative_surface()

    assert flade["moenstre"] == 2
    assert flade["handlingsbare"] == 1
    assert flade["afviste"][0]["titel"] == "Svag"
    assert flade["afviste"][0]["grund"], "en afvisning uden grund kan ikke efterprøves"


def test_raa_db_raekker_og_detect_returform_giver_samme_resultat(_fanget):
    """Broen skal virke for mønstre opdaget FØR den fandtes."""
    raa = bro.push_emergents_to_queue([_moenster()])
    indpakket = bro.push_emergents_to_queue([{"pattern": _moenster()}])

    assert len(raa["pushet"]) == 1
    assert len(indpakket["pushet"]) == 1
    assert _fanget[0]["source_id"] == _fanget[1]["source_id"]
