"""Sweepet giver agent-egnede modeller en kvalitets-dom — ikke kun en sonde-score.

MÅLT 7/11-2026: 306 modeller i registret, 276 med `probe_score`, kun **2** med
`kvalitets_score`. `model_benchmark.gem_kvalitet` havde nul kaldere, så
rotationen (`agent_model_fitness.egnede_modeller`, der sorterer efter netop
det felt) rangerede 65 modeller med probe 100 i vilkårlig rækkefølge.

Testene her måler KOBLINGEN, ikke implementeringen: at dommen bliver spurgt om
og gemt, at loftet holder (benchmarken spawner en rigtig agent pr. model), og
at en benchmark uden opgaver IKKE gemmer en score — «ikke målt» må ikke læses
som «dårlig».
"""
from __future__ import annotations

import pytest

from core.services import model_catalogue_sweep as sw


def _rapport(provider: str, *egnede: str) -> dict:
    return {"provider": provider, "agent_egnede": list(egnede),
            "slaaet_fra": [], "nye": [], "genoplivet": [], "uaendret": 0,
            "proevet": len(egnede), "fejl": ""}


@pytest.fixture
def uden_dom(monkeypatch):
    """Kun de modeller testen selv nævner mangler en dom."""
    mangler = {("p1", "m1"), ("p1", "m2"), ("p2", "m3")}
    monkeypatch.setattr(sw, "_modeller_uden_kvalitetsdom", lambda: set(mangler))
    return mangler


def test_dom_gemmes_for_agent_egnet_model_uden_dom(uden_dom):
    kaldt, gemt = [], []

    def koer(*, provider, model):
        kaldt.append((provider, model))
        return {"provider": provider, "model": model, "score": 88,
                "opgaver": [{"opgave": "x", "score": 88}]}

    def gem(*, provider, model, resultat):
        gemt.append((provider, model, resultat.get("score")))
        return True

    ud = sw._benchmark_umalte([_rapport("p1", "m1")], maks=2, koer=koer, gem=gem)

    assert kaldt == [("p1", "m1")]
    assert gemt == [("p1", "m1", 88)]
    assert ud == [{"provider": "p1", "model": "m1", "score": 88, "gemt": True}]


def test_model_med_dom_springes_over(uden_dom):
    """Ellers benchmarker vi de samme få modeller hver uge i evighed."""
    kaldt = []

    def koer(*, provider, model):
        kaldt.append((provider, model))
        return {"score": 90, "opgaver": [{"x": 1}]}

    sw._benchmark_umalte([_rapport("p1", "allerede-maalt")],
                         maks=2, koer=koer, gem=lambda **kw: True)

    assert kaldt == [], "en model der allerede har en dom skal ikke måles igen"


def test_loftet_holder(uden_dom):
    """En benchmark spawner en rigtig explore-agent pr. model OG fil."""
    kaldt = []

    def koer(*, provider, model):
        kaldt.append((provider, model))
        return {"score": 70, "opgaver": [{"x": 1}]}

    ud = sw._benchmark_umalte(
        [_rapport("p1", "m1", "m2"), _rapport("p2", "m3")],
        maks=2, koer=koer, gem=lambda **kw: True,
    )

    assert len(kaldt) == 2, f"loftet på 2 blev brudt: {kaldt}"
    assert [x["model"] for x in ud] == ["m1", "m2"]


def test_nul_slaar_koblingen_fra(uden_dom):
    def koer(**kw):  # pragma: no cover — må ikke blive kaldt
        raise AssertionError("benchmarken blev kørt selv om loftet var 0")

    assert sw._benchmark_umalte([_rapport("p1", "m1")], maks=0, koer=koer,
                                gem=lambda **kw: True) == []


def test_benchmark_uden_opgaver_gemmer_ingen_dom(uden_dom):
    """«Ikke målt» må ikke skrives som score 0 — det ville læse som «dårlig»."""
    gemt = []

    def koer(*, provider, model):
        return {"score": 0, "opgaver": [], "fejl": "ingen egnede filer"}

    ud = sw._benchmark_umalte([_rapport("p1", "m1")], maks=2, koer=koer,
                              gem=lambda **kw: gemt.append(kw) or True)

    assert gemt == []
    assert ud == []


def test_benchmark_fejl_vaelter_ikke_sweepet(uden_dom):
    """En mislykket benchmark er ikke en fejl i sweepet."""
    def koer(**kw):
        raise RuntimeError("udbyderen svarede ikke")

    ud = sw._benchmark_umalte([_rapport("p1", "m1")], maks=2, koer=koer,
                              gem=lambda **kw: True)

    assert ud == []


def test_sweep_alle_kalder_koblingen_efter_sonderingen(monkeypatch, uden_dom):
    """Rækkefølgen er pointen: først ved vi hvem der KAN, så hvor gode de er."""
    monkeypatch.setattr(sw, "sweep_provider",
                        lambda p, **kw: _rapport(p, "m1" if p == "p1" else ""))
    monkeypatch.setattr(sw, "underret_ejeren", lambda b, **kw: False)
    set_ = []
    monkeypatch.setattr(
        sw, "_benchmark_umalte",
        lambda rapporter, **kw: set_.append(len(rapporter)) or [{"provider": "p1", "model": "m1"}],
    )

    ud = sw.sweep_alle(providers=["p1"], underret=False)

    assert set_ == [1], "koblingen blev ikke kaldt præcis én gang efter sweepet"
    assert ud["benchmarked"] == [{"provider": "p1", "model": "m1"}]
