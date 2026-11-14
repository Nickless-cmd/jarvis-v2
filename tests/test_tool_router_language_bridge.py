"""Sprog-broen i routeren: kun embedding-inputtet, aldrig porten.

Målt 6/9-2026 på 60 ægte beskeder — tallene står i _embedding_query's
docstring, og testene her låser den adfærd tallene retfærdiggør.
"""

from __future__ import annotations

import pytest

from core.services import tool_router as R


def test_dansk_broes_foer_embedding():
    assert R._embedding_query("møde i min kalender") == "meeting i min calendar"


def test_engelsk_og_fagord_roeres_ikke():
    """Hans fagord er i forvejen engelske — de virker allerede."""
    for s in ("run the tests", "tool prompt bash session container"):
        assert R._embedding_query(s) == s


def test_kontakten_slukker_broen(monkeypatch):
    monkeypatch.setattr(R, "_sprog_bro_taendt", lambda: False)
    assert R._embedding_query("møde i min kalender") == "møde i min kalender"


def test_broen_maa_aldrig_vaelte_routeren(monkeypatch):
    """En fejl i broen skal give den RÅ besked, ikke en exception."""
    import core.services.query_language_bridge as B

    def eksploder(_t):
        raise RuntimeError("bro nede")

    monkeypatch.setattr(B, "normalise_for_embedding", eksploder)
    assert R._embedding_query("møde i min kalender") == "møde i min kalender"


def test_tom_besked_er_sikker():
    assert R._embedding_query("") == "" and R._embedding_query(None) == ""


def test_scoren_faar_den_RAA_besked_ikke_den_broede():
    """msg_clarity skal måle hans faktiske sprog. Kun embedding-inputtet brydes.

    Ellers ville broen ændre confidence — og målingen viste netop at porten
    er uændret (median +0,0000, ingen tærskel-krydsninger på 60 beskeder).

    Vagten laeste FOER en streng: `"top_k_similar(_embedding_query(user_message)"`.
    Den braekkede 6/10-2026 af en ren ombrydning — kaldet fik et `timeout_s`
    og blev delt over flere linjer. Egenskaben var uaendret; kun tegnene
    flyttede sig. En kilde-vagt der greper efter en streng maaler altsaa
    formatering, ikke adfaerd. Nu parses AST'en, som huset har skrevet ned.
    """
    import ast
    import inspect
    import textwrap

    traeet = ast.parse(textwrap.dedent(inspect.getsource(R._select_inner)))

    def foerste_arg(funktionsnavn: str):
        for knude in ast.walk(traeet):
            if (isinstance(knude, ast.Call)
                    and isinstance(knude.func, ast.Name)
                    and knude.func.id == funktionsnavn
                    and knude.args):
                return knude.args[0]
        return None

    emb = foerste_arg("top_k_similar")
    assert emb is not None, "top_k_similar kaldes ikke laengere i _select_inner"
    assert isinstance(emb, ast.Call) and isinstance(emb.func, ast.Name) \
        and emb.func.id == "_embedding_query", \
        "embedding-inputtet skal gaa gennem broen"
    assert any(isinstance(a, ast.Name) and a.id == "user_message" for a in emb.args), \
        "broen skal have den raa besked som input"

    sc = foerste_arg("_score")
    assert sc is not None, "_score kaldes ikke laengere i _select_inner"
    raa = (isinstance(sc, ast.Name) and sc.id == "user_message") or (
        isinstance(sc, ast.BoolOp)
        and any(isinstance(v, ast.Name) and v.id == "user_message" for v in sc.values))
    assert raa, "scoren maa IKKE faa den broede tekst — den skal maale hans faktiske sprog"


def test_broen_er_default_TIL(monkeypatch):
    class TomConfig:
        extra: dict = {}

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: TomConfig())
    assert R._sprog_bro_taendt() is True


def test_ulaeselig_config_lader_broen_vaere_taendt(monkeypatch):
    """Modsat nudgen: her er den sikre vej at BLIVE ved med at bro, for uden
    broen er rangordningen målt dårligere — ikke bare anderledes."""
    def eksploder():
        raise RuntimeError("config nede")

    monkeypatch.setattr("core.runtime.settings.load_settings", eksploder)
    assert R._sprog_bro_taendt() is True


# ---------------------------------------------------------------------------
# Tærsklen — kalibreret 6/9 på 189 beskeder over seks måneder
# ---------------------------------------------------------------------------


def test_taersklen_lukker_de_maalte_vaerktoejs_foresporgsler_ind():
    """Fire ægte forespørgsler skal passere — regnet på den formel der kører nu.

    Tallene her var hardkodede (0,42484 / 0,41779 / 0,39311 / 0,38042, målt
    6/9-2026). De var målt med et rate-afhængigt loft, og da loftet faldt
    (målt 14/11-2026: 0,534 → 0,396) faldt de fire med det — den nederste
    endte under tærsklen. Testen var grøn hele tiden, fordi den sammenlignede
    mod en kopi af fortiden i stedet for mod formlen.
    """
    from core.runtime.settings import RuntimeSettings
    from core.services.tool_router import _score

    t = float(RuntimeSettings().tool_router_threshold)
    beskeder = [
        "kan du lægge et møde ind i min kalender på fredag",
        "send en mail til bjorn om netværket",
        "hvad er der i min kalender i morgen",
        "vis mig de seneste commits",
    ]
    # top_sim 0,5 er et forsigtigt match: en ægte forespørgsel må ikke være
    # afhængig af et perfekt embedding-hit for at slippe igennem porten.
    afvist = {
        b: round(_score(b, top_sim=0.5), 4)
        for b in beskeder
        if _score(b, top_sim=0.5) < t
    }
    assert not afvist, f"ægte værktøjs-forespørgsler afvises af tærsklen {t}: {afvist}"


def test_chitchat_faar_kun_kernen():
    """Den anden side af samme port — og den er ikke kosmetisk.

    Uden den her kan testen ovenfor opfyldes ved at sænke tærsklen til nul, og
    så er der ingen pruning tilbage: hver tur betaler ~38K tokens for et fuldt
    sæt. Porten skal skelne, ikke bare åbne.
    """
    from core.runtime.settings import RuntimeSettings
    from core.services.tool_router import _score

    t = float(RuntimeSettings().tool_router_threshold)
    for besked in ("ja", "ok", "hvad synes du om det"):
        assert _score(besked, top_sim=0.0) < t, f"chitchat {besked!r} slipper igennem"


def test_loftet_ligger_over_taersklen_med_margin():
    """Loftet er KONSTANT 0,60, og tærsklen skal have luft under det.

    Vagten regnede FØR loftet ud fra en hardkodet rate (0,08) og målte dermed et
    tal der ikke findes. Ved den faktiske rate 0,102 (målt 14/11-2026) faldt
    loftet til 0,396 mens tærsklen stod på 0,380 — 47 % af turene fik kun
    kernen — og testen var grøn, fordi den aldrig så den rate der kørte.
    """
    from core.runtime.settings import RuntimeSettings
    from core.services.tool_router import _CONFIDENCE_CEILING

    t = float(RuntimeSettings().tool_router_threshold)
    assert t < _CONFIDENCE_CEILING * 0.90, (
        f"tærskel {t} er for tæt på loftet {_CONFIDENCE_CEILING:.3f} — "
        "porten ville næsten aldrig åbne"
    )


def test_loftet_kan_ikke_saenkes_af_load_more_raten():
    """Confidence må ikke straffes for routerens EGEN load_more-rate.

    Målt 14/11-2026: raten gik 0,033 → 0,102, loftet faldt 0,534 → 0,396, og
    tærsklen 0,380 endte OVER loftet. Kæden var cirkulær og havde omvendt
    fortegn: smalt sæt → mere load_more → lavere loft → smallere sæt. Med fast
    loft er scoren 0,578 både før og efter — hele faldet var multiplikatoren.
    """
    import inspect

    assert "load_more" not in inspect.signature(R._score).parameters, (
        "scoren tager stadig load_more-raten som input — koblingen er tilbage"
    )
    # Målt med det faste loft: 0,910 clarity og top_sim 0,7.
    assert R._score(
        "kan du lægge et møde ind i min kalender på fredag", top_sim=0.7
    ) == pytest.approx(0.5784, abs=0.005)


# ---------------------------------------------------------------------------
# _clarity_signal — målt mod grundsandhed, ikke mod en formodning
# ---------------------------------------------------------------------------


def test_befalinger_vejer_tungere_end_spoergsmaal():
    """Det gamle signal gav +0,15 for et SPØRGSMÅL og intet for en befaling.

    Målt på 1.200 beskeder mod grundsandhed (havde næste assistent-svar i samme
    session `tool_use`?) var det ikke bare svagt — det var VENDT OM:
    snit 0,688 med værktøj mod 0,691 uden. Ny formel: 0,791 mod 0,753.
    """
    from core.services.tool_router import _clarity_signal as c
    assert c("vis mig de seneste commits") > c("hvad synes du om det")
    assert c("send en mail til bjorn om netværket") > c("hvad er der sket i dag")


def test_talehandlinger_taeller_IKKE_som_vaerktoejs_befalinger():
    """Jarvis' indvending: «sig hej til Michelle» og «fortæl en joke» er også
    befalinger. Listen er derfor HANDLINGSVERBER (vis/hent/kør/læs), ikke alle
    imperativer — «sig» og «fortæl» står der ikke."""
    from core.services.tool_router import _clarity_signal as c
    for tale in ("sig hej til michelle", "fortæl en joke", "forklar det igen"):
        assert c(tale) < c("vis mig de seneste commits"), tale


def test_boejninger_rammes_men_ikke_delord():
    from core.services.tool_router import _IMPERATIVE_VERBS as V
    assert V.search("kan du lægge et møde ind")      # læg + ge
    assert V.search("send en mail")
    assert not V.search("research mode with findings")  # «find» må ikke ramme «findings»


def test_korte_og_bekraeftende_beskeder_er_uaendrede():
    """Imperativ-feature må ikke røre de to tidlige udgange."""
    from core.services.tool_router import _clarity_signal as c
    assert c("ja") == 0.15
    assert c("kør nu") == 0.30      # under 3 ord → fast 0,30, uanset verbum
