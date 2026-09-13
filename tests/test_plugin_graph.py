"""Afhængighedsgrafen — Fase 9, «boot rejects missing/cyclic dependencies»."""
from __future__ import annotations

import pytest

from core.runtime.plugin_graph import GrafFejl, valider


# ------------------------------------------------------------- manglende udbyder

def test_afhaengighed_uden_udbyder_er_et_fund():
    """Det er hele forskellen på en graf og en ønskeseddel.

    Maalt paa kadencen 13/9-2026: en tastefejl her giver
    ('blocked', 'dependency-not-met:...') FOR EVIGT, og det er ikke til at
    skelne fra «foraelderen har bare ikke koert endnu».
    """
    r = valider({"a": ["findes_ikke"]})
    assert not r.rask
    assert r.manglende == {"a": ("findes_ikke",)}
    assert "ingen udbyder" in r.forklar()[0]


def test_flere_manglende_paa_samme_knude_naevnes_alle():
    r = valider({"a": ["x", "y"], "b": []})
    assert r.manglende == {"a": ("x", "y")}


def test_knude_der_KUN_er_afhaengighed_taeller_som_manglende():
    """`b` optræder som afhængighed men har ingen egen post — ingen leverer den."""
    r = valider({"a": ["b"]})
    assert r.manglende == {"a": ("b",)}


def test_rask_graf_er_rask():
    r = valider({"a": ["b"], "b": ["c"], "c": []})
    assert r.rask
    assert r.manglende == {} and r.cykler == ()
    assert r.forklar() == []


# -------------------------------------------------------------------- cykler

def test_cyklus_navngives_HELE_vejen_rundt():
    """«Der er en cyklus» sender folk paa jagt i 119 knuder. Stien er til at rette."""
    r = valider({"a": ["b"], "b": ["c"], "c": ["a"]})
    assert not r.rask
    assert len(r.cykler) == 1
    cyklus = r.cykler[0]
    assert cyklus[0] == cyklus[-1], "cyklussen skal lukke om sig selv"
    assert set(cyklus) == {"a", "b", "c"}


def test_selvafhaengighed_er_en_cyklus():
    r = valider({"a": ["a"]})
    assert r.cykler and set(r.cykler[0]) == {"a"}


def test_to_uafhaengige_cykler_findes_begge():
    r = valider({"a": ["b"], "b": ["a"], "x": ["y"], "y": ["x"], "fri": []})
    assert len(r.cykler) == 2
    fundne = {frozenset(c) for c in r.cykler}
    assert fundne == {frozenset({"a", "b"}), frozenset({"x", "y"})}


def test_samme_cyklus_rapporteres_KUN_EN_GANG():
    """En dubleret afhaengighed finder samme ring to gange.

    Foerste udgave af denne test brugte en ring med to INDGANGE (d->a, e->b).
    Den var groen ogsaa uden dedup, fordi knuderne allerede er sorte naar man
    naar d og e — testen maalte altsaa ingenting, og mutationen overlevede.

    Det der FAKTISK udloeser dubletten er en gentagen post i `depends_on`:
    bagkanten traverseres to gange mens `a` stadig er graa. Det er ogsaa den
    realistiske form — en haandholdt liste med et navn skrevet to gange.
    """
    r = valider({"a": ["b"], "b": ["a", "a"]})
    assert len(r.cykler) == 1, f"samme ring rapporteret {len(r.cykler)} gange"


def test_to_FORSKELLIGE_ringe_gennem_samme_knuder_er_to_fund():
    """Dedup maa ikke blive for grovkornet. a->b->c->a og a->b->a er to
    forskellige ringe, og den ene kan brydes uden den anden."""
    r = valider({"a": ["b"], "b": ["c", "a"], "c": ["a"]})
    assert len(r.cykler) == 2
    assert {frozenset(c) for c in r.cykler} == {frozenset({"a", "b", "c"}), frozenset({"a", "b"})}


def test_manglende_udbyder_forveksles_ikke_med_cyklus():
    """To forskellige sygdomme, to forskellige kure. Skrives de sammen,
    leder man efter en ring der ikke findes."""
    r = valider({"a": ["mangler"], "b": ["c"], "c": ["b"]})
    assert r.manglende == {"a": ("mangler",)}
    assert len(r.cykler) == 1 and set(r.cykler[0]) == {"b", "c"}


# ---------------------------------------------------------------- rækkefølgen

def test_afhaengigheder_kommer_foerst():
    r = valider({"barn": ["far"], "far": ["bedstefar"], "bedstefar": []})
    assert r.raekkefoelge.index("bedstefar") < r.raekkefoelge.index("far")
    assert r.raekkefoelge.index("far") < r.raekkefoelge.index("barn")


def test_raekkefoelgen_er_REPRODUCERBAR():
    """Uden navne-sortering afhaenger ordenen af dict-orden, og to koersler af
    samme graf kunne give forskellig opstart. En orden man ikke kan gentage er
    ikke til at fejlsoege."""
    graf = {"c": [], "a": [], "b": [], "d": ["a", "b", "c"]}
    assert valider(graf).raekkefoelge == valider(dict(reversed(list(graf.items())))).raekkefoelge


def test_cyklisk_graf_giver_INGEN_raekkefoelge():
    """En delvis orden ville se brugbar ud og starte halvdelen af systemet i
    en orden der ikke holder."""
    r = valider({"a": ["b"], "b": ["a"], "fri": []})
    assert r.raekkefoelge == (), "en cyklisk graf HAR ingen gyldig raekkefoelge"


def test_raekkefoelgen_daekker_alle_knuder_i_en_rask_graf():
    graf = {"a": ["b"], "b": ["c"], "c": [], "løs": []}
    assert set(valider(graf).raekkefoelge) == set(graf)


# ------------------------------------------------------------- streng tilstand

def test_streng_kaster_paa_manglende():
    with pytest.raises(GrafFejl) as e:
        valider({"a": ["mangler"]}, streng=True)
    assert "ingen udbyder" in str(e.value)


def test_streng_kaster_paa_cyklus():
    with pytest.raises(GrafFejl) as e:
        valider({"a": ["b"], "b": ["a"]}, streng=True)
    assert "cyklus" in str(e.value)


def test_streng_er_TAVS_paa_en_rask_graf():
    assert valider({"a": ["b"], "b": []}, streng=True).rask


def test_streng_er_et_VALG_ikke_en_default():
    """Levende kode er ikke skrevet med et kast i tankerne. Et kast som
    default ville tage runtime ned fordi én producent havde en tastefejl —
    vaerre end sygdommen, og spec'en siger selv at eksisterende tjenester
    migrerer gradvist."""
    r = valider({"a": ["mangler"], "b": ["c"], "c": ["b"]})
    assert not r.rask, "rapporten skal stadig vise fejlen"
    assert len(r.forklar()) == 2


# ------------------------------------------------------------------ randtilfælde

def test_tom_graf():
    r = valider({})
    assert r.rask and r.raekkefoelge == ()


def test_knude_uden_afhaengigheder():
    r = valider({"a": [], "b": None})  # type: ignore[dict-item]
    assert r.rask and set(r.raekkefoelge) == {"a", "b"}


def test_diamant_er_ikke_en_cyklus():
    """a->b, a->c, b->d, c->d. To veje til samme knude er ikke en ring —
    en besoegt-maengde uden farver ville kalde det en cyklus."""
    r = valider({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
    assert r.rask, f"diamant fejlmeldt som cyklus: {r.cykler}"
    assert r.raekkefoelge.index("d") < r.raekkefoelge.index("b")


def test_dyb_kaede_vaelter_ikke():
    """500 led. Rekursionen skal kunne baere den levende grafs dybde med
    rigelig margin (kadencen har 14 kaeder, den dybeste paa 4)."""
    graf = {f"n{i}": [f"n{i+1}"] for i in range(500)}
    graf["n500"] = []
    assert valider(graf).rask


# ------------------------------------------------ den LEVENDE graf skal holde

def test_den_virkelige_kadencegraf_er_rask():
    """Grundsandhed, ikke et opdigtet eksempel.

    Maalt 13/9-2026: 119 producenter, 0 manglende, 0 cykler. Gaar denne roed,
    har nogen indfoert praecis den fejl der ellers ville staa tavs som
    'blocked' for evigt.
    """
    import core.services.internal_cadence as ic
    ic._ensure_producers_registered()
    if not ic._producers:
        pytest.skip("ingen producenter registreret i dette miljoe")
    graf = {n: list(s.depends_on or []) for n, s in ic._producers.items()}
    r = valider(graf)
    assert r.rask, "kadencegrafen er braekket:\n  " + "\n  ".join(r.forklar())


# ------------------------------------------------ validatoren skal KALDES

def test_bootstrap_validerer_grafen():
    """En validator ingen kalder er praecis den fejlform den skal fange.

    Kilde-vagt: `_ensure_producers_registered` skal kalde valideringen. En
    test der selv kalder `_valider_afhaengigheder()` ville vaere groen ogsaa
    hvis bootstrap aldrig roerte den.
    """
    import ast
    import pathlib

    træ = ast.parse(pathlib.Path("core/services/internal_cadence.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "_ensure_producers_registered"), None)
    assert fn is not None, "bootstrap-funktionen er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_valider_afhaengigheder" in kaldt, \
        "bootstrap validerer ikke grafen — en tastefejl ville staa tavs som 'blocked'"


def test_rapporten_er_SYNLIG_paa_fladen():
    """En fejl der kun staar i loggen er halvt tavs — man skal vide at man
    skal lede efter den."""
    import core.services.internal_cadence as ic
    ic._ensure_producers_registered()
    from core.services.cadence_producers import build_cadence_producers_surface
    graf = build_cadence_producers_surface()["afhaengighedsgraf"]
    assert "rask" in graf and "manglende" in graf and "cykler" in graf


def test_valideringen_vaelter_ALDRIG_bootstrap(monkeypatch):
    """En validator der tager opstarten ned er vaerre end ingen validator."""
    import core.runtime.plugin_graph as pg
    import core.services.internal_cadence as ic
    monkeypatch.setattr(pg, "valider",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    ic._valider_afhaengigheder()          # maa ikke kaste
    assert ic.sidste_graf_rapport.get("fejl") is True
