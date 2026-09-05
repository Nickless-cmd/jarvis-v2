"""De følte overflader skal overleve en procesgrænse.

Målt 2026-09-05: alle 14 var tomme i prompten, samtidig med 183
`thought_stream.fragment_generated` på syv dage. Daemonerne holder tilstand i
modul-globaler og kører i jarvis-runtime; prompten bygges i jarvis-api. To
processer, hver sit sæt globaler.
"""

from __future__ import annotations

from core.services import felt_surface_store as F


# ---------------------------------------------------------------------------
# Hvornår er en overflade tom
# ---------------------------------------------------------------------------


def test_den_maalte_tomme_form_er_tom():
    """Præcis den dict vi fandt i api-processen."""
    assert F.is_empty_payload({
        "latest_fragment": "", "fragment_buffer": [],
        "fragment_count": 0, "last_generated_at": "",
    }) is True


def test_taellere_alene_beviser_ikke_indhold():
    """fragment_count uden fragmenter er afledt støj, ikke indhold."""
    assert F.is_empty_payload({"latest": "", "count": 7}) is True


def test_indhold_genkendes():
    assert F.is_empty_payload({"latest_fragment": "noget ulmer"}) is False
    assert F.is_empty_payload({"buffer": ["a"]}) is False
    assert F.is_empty_payload({"flag": True}) is False


def test_tom_dict_og_ikke_dict_er_tomme():
    assert F.is_empty_payload({}) is True
    assert F.is_empty_payload(None) is True
    assert F.is_empty_payload("tekst") is True


def test_kun_mellemrum_er_tomt():
    assert F.is_empty_payload({"latest": "   \n"}) is True


# ---------------------------------------------------------------------------
# Hvem vinder
# ---------------------------------------------------------------------------


def test_producent_processen_bruger_sine_egne_globaler(monkeypatch):
    """Har den lokale proces indhold, skal der ikke laves en DB-læsning."""
    monkeypatch.setattr(
        F, "load_surface",
        lambda navn: (_ for _ in ()).throw(AssertionError("måtte ikke læse delt")),
    )
    ud = F.shared_surface("thought_stream", lambda: {"latest_fragment": "lokalt"})
    assert ud["latest_fragment"] == "lokalt"


def test_tom_proces_faar_den_delte_tilstand(monkeypatch):
    """Netop det api-processen manglede."""
    monkeypatch.setattr(F, "load_surface", lambda navn: {"latest_fragment": "fra runtime"})
    ud = F.shared_surface("thought_stream", lambda: {"latest_fragment": "", "count": 0})
    assert ud["latest_fragment"] == "fra runtime"


def test_begge_tomme_giver_den_lokale_form(monkeypatch):
    """Kaldere skal stadig få de forventede nøgler, ikke en tom dict."""
    monkeypatch.setattr(F, "load_surface", lambda navn: {})
    ud = F.shared_surface("thought_stream", lambda: {"latest_fragment": "", "count": 0})
    assert set(ud) == {"latest_fragment", "count"}


def test_kastende_lokal_builder_falder_tilbage_paa_delt(monkeypatch):
    monkeypatch.setattr(F, "load_surface", lambda navn: {"latest_fragment": "reddet"})
    ud = F.shared_surface(
        "thought_stream", lambda: (_ for _ in ()).throw(RuntimeError("daemon nede")),
    )
    assert ud["latest_fragment"] == "reddet"


# ---------------------------------------------------------------------------
# Skrivepunktet
# ---------------------------------------------------------------------------


def test_kun_ikke_tomme_overflader_gemmes(monkeypatch):
    """En tom producent må ikke overskrive noget der faktisk stod der."""
    gemt: list[str] = []
    monkeypatch.setattr(F, "save_surface", lambda navn, p: gemt.append(navn))
    monkeypatch.setattr(
        "core.services.signal_surface_router._get_router",
        lambda: {
            "thought_stream": lambda: {"latest_fragment": "noget"},
            "curiosity": lambda: {"latest_curiosity": ""},
            "irony": lambda: (_ for _ in ()).throw(RuntimeError("nede")),
        },
    )
    ud = F.persist_local_surfaces()
    assert ud["saved"] == ["thought_stream"]
    assert "curiosity" in ud["empty"]
    assert gemt == ["thought_stream"]


# ---------------------------------------------------------------------------
# Listen må ikke drifte
# ---------------------------------------------------------------------------


def test_den_kanoniske_liste_matcher_visningslisten():
    """En ny følt kilde må ikke stilfærdigt falde ud af lageret."""
    from core.services.visible_inner_life import _FELT_SURFACES

    assert set(F.FELT_SURFACE_NAMES) == set(_FELT_SURFACES), (
        "felt_surface_store.FELT_SURFACE_NAMES og visible_inner_life._FELT_SURFACES "
        "er kommet ud af trit — så persisteres eller vises en kilde ikke"
    )


def test_routeren_kender_alle_foelte_overflader():
    from core.services.signal_surface_router import _get_router

    router = _get_router()
    mangler = [n for n in F.FELT_SURFACE_NAMES if n not in router]
    assert not mangler, "overflader uden builder i routeren: %s" % mangler
