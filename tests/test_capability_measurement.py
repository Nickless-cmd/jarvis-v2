"""Fælles skrivevej for MÅLTE capability-værdier (20/11-2026).

Filen flyttede `set_domain_confidence` ud af `desk_render_capability.py`, så to
målere kan skrive gennem samme vej i stedet for at hver bære sin egen kopi.

Den vigtigste egenskab er ikke at den kan skrive — det kan en `UPDATE` også.
Det er at den kan sige NEJ: uden et bevis skrives intet, og en værdi der ikke
har flyttet sig skrives ikke igen. En måler der altid svarer «skrevet» måler
ingenting, og det var netop hvad de selvrapporterede confidence-tal var.
"""

from __future__ import annotations

import json

import pytest

from core.runtime import db_cognitive
from core.services import capability_measurement as cm


class _Skrivninger(list[dict[str, object]]):
    """De kald der faktisk blev skrevet, plus en hånd til at styre den aktuelle vektor."""

    def __init__(self) -> None:
        super().__init__()
        self.nuværende: dict[str, object] = {"confidence_by_domain": "{}"}

    def saet_vektor(self, domaener: dict[str, float]) -> None:
        self.nuværende["confidence_by_domain"] = json.dumps(domaener, ensure_ascii=False)


@pytest.fixture()
def skrivninger(monkeypatch: pytest.MonkeyPatch) -> _Skrivninger:
    """Fanger hvad der faktisk bliver skrevet, og lader testen styre hvad der ligger der."""
    kald = _Skrivninger()

    def _hent() -> dict[str, object]:
        return dict(kald.nuværende)

    def _skriv(**kwargs: object) -> None:
        kald.append(kwargs)

    monkeypatch.setattr(db_cognitive, "get_latest_cognitive_personality_vector", _hent)
    monkeypatch.setattr(db_cognitive, "upsert_cognitive_personality_vector", _skriv)
    return kald


def test_et_bevis_er_betingelsen_for_at_skrive(skrivninger: list[dict[str, object]]) -> None:
    """Uden et bevis er en «måling» en selvrapport med et finere navn."""
    for tomt in ("", "   ", None):
        svar = cm.set_domain_confidence("database-skema", 0.55, evidence=tomt)  # type: ignore[arg-type]
        assert svar["recorded"] is False, svar
        assert "bevis" in svar["reason"], svar
    assert skrivninger == []


def test_tomt_domaene_skrives_ikke(skrivninger: list[dict[str, object]]) -> None:
    svar = cm.set_domain_confidence("   ", 0.55, evidence="målt i test")
    assert svar["recorded"] is False, svar
    assert svar["reason"] == "intet domæne", svar
    assert skrivninger == []


def test_en_uaendret_vaerdi_skrives_ikke_igen(skrivninger: list[dict[str, object]]) -> None:
    """Samme tal er ikke en ny måling. At skrive den igen ville puste historikken op."""
    skrivninger.saet_vektor({"database-skema": 0.55})  # type: ignore[attr-defined]
    svar = cm.set_domain_confidence("database-skema", 0.55, evidence="samme resultat")
    assert svar["recorded"] is False, svar
    assert svar["reason"] == "uændret", svar
    assert skrivninger == []


def test_vaerdien_holdes_i_nul_til_et(skrivninger: list[dict[str, object]]) -> None:
    """En confidence uden for [0,1] er en regnefejl, ikke et signal."""
    for raa, ventet in ((1.7, 1.0), (-0.5, 0.0), (0.4321, 0.432)):
        svar = cm.set_domain_confidence("clamp", raa, evidence="grænsetest")
        assert svar["recorded"] is True, svar
        assert svar["after"] == ventet, svar


def test_eksisterende_domaene_genbruges_paa_tvaers_af_skrivemaade(
    skrivninger: list[dict[str, object]],
) -> None:
    """«Souls-Build  Analyse» og «souls-build analyse» er samme domæne.

    Uden sammenlægningen ville hver ny skrivemåde fra modellen blive et nyt
    domæne — det var sådan 689 navne endte med at dække langt færre reelle evner.
    """
    skrivninger.saet_vektor({"Souls-Build  Analyse": 0.45})  # type: ignore[attr-defined]
    svar = cm.set_domain_confidence("souls-build analyse", 0.62, evidence="målt 5/5")
    assert svar["recorded"] is True, svar
    assert svar["domain"] == "Souls-Build  Analyse", svar
    assert svar["before"] == 0.45, svar
    skrevet = json.loads(str(skrivninger[0]["confidence_by_domain"]))
    assert skrevet == {"Souls-Build  Analyse": 0.62}, skrevet


def test_skrivningen_gaar_gennem_den_faelles_vej(
    skrivninger: list[dict[str, object]],
) -> None:
    """Den bevarer vektorens øvrige felter — den må ikke nulstille personligheden."""
    svar = cm.set_domain_confidence("ny-evne", 0.71, evidence="målt i test")
    assert svar["recorded"] is True, svar
    assert len(skrivninger) == 1, skrivninger
    kald = skrivninger[0]
    assert set(kald) >= {
        "confidence_by_domain",
        "communication_style",
        "learned_preferences",
        "recurring_mistakes",
        "strengths_discovered",
        "current_bearing",
        "emotional_baseline",
    }, kald
    assert json.loads(str(kald["confidence_by_domain"])) == {"ny-evne": 0.71}
