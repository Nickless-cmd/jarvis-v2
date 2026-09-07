"""Leksikalsk vaerktoejs-opslag — maalt paa 60 aegte beskeder 7/9-2026.

Testene er skrevet efter de FAKTISKE traef og falske traef fra maalingen, ikke
efter opdigtede eksempler. Hvert forventet svar stod i den koersel.
"""

from __future__ import annotations

import pytest

from core.services.tool_lexical_match import (
    Korpus,
    byg_korpus_fra_definitioner,
    ord_i,
)


def _korpus() -> Korpus:
    """Lille korpus med de vaerktoejer maalingen faktisk bragte frem."""
    return Korpus({
        "provider_health_check": "provider_health_check tjek sundhed for providers i cheap lane",
        "note_delete": "note_delete slet en note fra listen",
        "publish_file": "publish_file udgiv en fil, paste indhold til web",
        "hf_vision_analyze": "hf_vision_analyze analyser et billede med en vision model",
        "commit_staged_edits": "commit_staged_edits commit de stagede aendringer",
        "synthesize_arc": "synthesize_arc saml en bue over hvad der blev sagt",
        "note_add": "note_add tilfoej en note",
        "note_list": "note_list vis noter",
        "memory_usage": "memory_usage vis hukommelsesforbrug",
    })


def test_saerkende_ord_i_navnet_vinder():
    """«providers» + «lane» → provider_health_check. Maalt 13,5 mod 8,3."""
    t = _korpus().slaa_op("Claude er ved at smide den i cheap lane, troede providers var oppe")
    assert t is not None
    assert t.navn == "provider_health_check"
    assert t.score >= t.naest * 1.4


def test_traeffet_baerer_ordene_det_byggede_paa():
    """Nudgen skal kunne vise HVORFOR — et tal alene kan ingen efterproeve."""
    t = _korpus().slaa_op("Jeg har skiftet dig til vision modelen, tag et dump")
    assert t is not None and t.navn == "hf_vision_analyze"
    assert "vision" in t.ord


def test_dansk_falsk_ven_giver_ingenting():
    """«slet ikk faa lov» er «slet ikke» — IKKE en sletning.

    Det var det klareste falske traef i maalingen: note_delete via «slet».
    """
    assert _korpus().slaa_op("Kan slet ikk faa lov at toppe op med kort..") is None


def test_uafgjort_felt_giver_ingenting():
    """Er der ingen afstand ned til feltet, er traeffet tilfaeldigt.

    Maalt: publish_file 5,0 mod naestbedste 5,0 via «paste». Det er praecis
    det moenster porten skal fange — og den grund cosinus ikke kunne, hvor
    afstanden ALTID var ~0,01.
    """
    assert _korpus().slaa_op("Saa blev han vist faerdig..") is None


def test_intet_bud_er_det_normale_svar():
    """43 af 60 aegte beskeder gav intet. Tavshed er korrekt opfoersel."""
    k = _korpus()
    for besked in (
        "du tager den her, det lyder som om du har en plan",
        "hvor gamle er du endelig idag?",
        "det var ren nysgerrighed og lidt sjov",
    ):
        assert k.slaa_op(besked) is None, besked


def test_kandidatlisten_begraenser_puljen():
    """Nudgen scorer kun mod de USYNLIGE vaerktoejer — porten foer opslaget."""
    k = _korpus()
    besked = "Claude er ved at smide den i cheap lane, troede providers var oppe"
    assert k.slaa_op(besked).navn == "provider_health_check"
    # samme besked, men vaerktoejet er ikke i puljen → intet bud
    assert k.slaa_op(besked, kandidater=["note_add", "note_list"]) is None


def test_stopord_fjernes():
    assert ord_i("og eller men som der det") == set()
    assert "providers" in ord_i("troede providers var oppe")


def test_korte_ord_taeller_ikke():
    """Under fire tegn er stort set altid stoej paa begge sprog."""
    assert ord_i("er du op ned") == set()


def test_korpus_fra_definitioner_taager_begge_former():
    """``get_tool_definitions()`` giver baade rå dicts og {'function': {...}}.

    Testen ser paa hvad der blev PARSET, ikke om et opslag krydser gulvet:
    med tre definitioner kan intet ord vaere saerkende (se testen nedenfor),
    saa en traef-paastand her ville maale korpus-stoerrelsen, ikke parsningen.
    """
    k = byg_korpus_fra_definitioner([
        {"function": {"name": "provider_health_check", "description": "providers i cheap lane"}},
        {"name": "note_add", "description": "tilfoej en note"},
        {"function": {"name": "", "description": "uden navn — skal springes over"}},
    ])
    assert set(k._tekster) == {"provider_health_check", "note_add"}
    assert "providers" in k._ord["provider_health_check"]


def test_meget_lille_korpus_giver_ingen_traef():
    """Med faa vaerktoejer kan INTET ord vaere saerkende — og saa tier den.

    Det er ikke en fejl, det er definitionen: IDF maaler sjaeldenhed, og i et
    korpus paa to dokumenter er ingenting sjaeldent. Skrevet ned, saa den
    naeste der ser et tomt svar fra et test-korpus ikke jagter en bug.
    """
    k = byg_korpus_fra_definitioner([
        {"name": "provider_health_check", "description": "providers i cheap lane"},
        {"name": "note_add", "description": "tilfoej en note"},
    ])
    assert k.slaa_op("er vores providers i cheap lane sunde?") is None


def test_tomt_korpus_falder_ikke_over():
    assert Korpus({}).slaa_op("providers i cheap lane") is None


@pytest.mark.parametrize("besked", ["", "   ", "ok", "🙂"])
def test_tom_besked_giver_ingenting(besked):
    assert _korpus().slaa_op(besked) is None
