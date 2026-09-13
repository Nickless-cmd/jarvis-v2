"""Profil-komponisten — Fase 9's baerende invariant.

En profil er kun en sikkerhedsgraense hvis et senere lag ALDRIG kan give mere
end et tidligere. Kan det, er profilen en anbefaling: enhver der kan tilfoeje et
lag, kan haeve sine egne rettigheder.
"""
import pytest

from core.runtime.profile_composer import (
    SIKKERHEDS_AKSER, SKEMA_VERSION, UKRAENKELIGE, komponer,
)


def _p(*lag, navn=""):
    return komponer(list(lag), navn=navn)


# ── Den baerende invariant ───────────────────────────────────────────────────

@pytest.mark.parametrize("akse,raekke", list(SIKKERHEDS_AKSER.items()))
def test_et_senere_lag_kan_INDSNAEVRE_enhver_sikkerheds_akse(akse, raekke):
    p = _p(("base", {akse: raekke[0]}), ("senere", {akse: raekke[-1]}))
    assert p.felter[akse] == raekke[-1]


@pytest.mark.parametrize("akse,raekke", list(SIKKERHEDS_AKSER.items()))
def test_et_senere_lag_kan_ALDRIG_udvide_en_sikkerheds_akse(akse, raekke):
    """DEN regel. Uden den er profilen ikke en graense."""
    p = _p(("base", {akse: raekke[-1]}), ("senere", {akse: raekke[0]}))
    assert p.felter[akse] == raekke[-1], f"{akse} blev udvidet af et senere lag"


def test_udvidelse_forsoegt_i_TREDJE_lag_afvises_ogsaa():
    """Angrebet er ikke noedvendigvis i lag to."""
    p = _p(("base", {"tool_scope": "all"}),
           ("rolle", {"tool_scope": "none"}),
           ("koersel", {"tool_scope": "all"}))
    assert p.felter["tool_scope"] == "none"


def test_raekkefoelgen_er_ligegyldig_for_SIKKERHEDEN():
    """Konsekvensen af invarianten: uanset hvordan lagene blandes, kan man kun
    bevaege sig én vej. Det er dét der goer den til en graense."""
    a = _p(("x", {"tool_scope": "all"}), ("y", {"tool_scope": "limited"}),
           ("z", {"tool_scope": "none"}))
    b = _p(("z", {"tool_scope": "none"}), ("x", {"tool_scope": "all"}),
           ("y", {"tool_scope": "limited"}))
    assert a.felter["tool_scope"] == b.felter["tool_scope"] == "none"


def test_en_UKENDT_vaerdi_kan_ikke_bruges_til_at_haeve_rettigheder():
    """Kender vi ikke retningen, tillader vi ikke skiftet. Ellers ville et
    stavefejl-agtigt «tool_scope: alt» kunne aabne alt."""
    p = _p(("base", {"tool_scope": "none"}), ("senere", {"tool_scope": "alt"}))
    assert p.felter["tool_scope"] == "none"


# ── Ikke-sikkerhed foelger almindelig praecedens ─────────────────────────────

def test_model_og_retry_foelger_sidste_lag():
    """Skellet er bevidst: en profil skal kunne vaelge en anden model uden at
    det er en rettigheds-aendring."""
    p = _p(("base", {"model": "a", "retry": 1}), ("senere", {"model": "b", "retry": 5}))
    assert p.felter["model"] == "b"
    assert p.felter["retry"] == 5


# ── Revision kan ikke slaas fra ──────────────────────────────────────────────

@pytest.mark.parametrize("felt", sorted(UKRAENKELIGE))
def test_en_profil_kan_IKKE_slaa_revision_fra(felt):
    """«audit truth cannot be disabled by profiles». Revision er ikke en
    indstilling — det er den eneste grund til at man bagefter kan vide hvad
    der skete."""
    p = _p(("base", {felt: True}), ("ondsindet", {felt: False}))
    assert p.felter[felt] is True


def test_revision_er_slaaet_til_selv_naar_INGEN_lag_naevner_den():
    p = _p(("base", {"model": "a"}))
    for felt in UKRAENKELIGE:
        assert p.felter[felt] is True


# ── Version og hash ─────────────────────────────────────────────────────────

def test_hashen_daekker_INDHOLDET_ikke_navnet():
    """Et navn siger ikke hvad profilen indeholdt dengang; profiler aendrer sig."""
    a = _p(("b", {"tool_scope": "none"}), navn="autonomous")
    b = _p(("b", {"tool_scope": "none"}), navn="et-helt-andet-navn")
    assert a.hash == b.hash


def test_forskelligt_indhold_giver_forskellig_hash():
    a = _p(("b", {"tool_scope": "none"}))
    b = _p(("b", {"tool_scope": "limited"}))
    assert a.hash != b.hash


def test_hashen_er_stabil_paa_tvaers_af_noegle_raekkefoelge():
    """Ellers kunne to identiske profiler se forskellige ud, og hashen ville
    ikke kunne bruges til at sammenligne koersler."""
    a = _p(("b", {"tool_scope": "none", "model": "m"}))
    b = _p(("b", {"model": "m", "tool_scope": "none"}))
    assert a.hash == b.hash


def test_skema_versionen_foelger_med():
    assert _p(("b", {})).skema_version == SKEMA_VERSION


def test_forklaringen_indeholder_det_Mission_Control_skal_vise():
    p = _p(("base", {"model": "m", "tool_scope": "limited", "approval_mode": "ask"}),
           navn="visible-owner")
    f = p.forklar()
    assert f["navn"] == "visible-owner"
    assert f["hash"] == p.hash
    assert f["lag"] == ["base"]
    assert f["sikkerhed"]["tool_scope"] == "limited"
    assert f["felter"]["model"] == "m"


def test_tomme_lag_giver_en_gyldig_profil():
    p = _p()
    assert p.felter and p.hash and p.skema_version == SKEMA_VERSION
