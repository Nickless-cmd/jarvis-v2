"""Varsel før døren smækker — han skal vide hvor han er, ikke bare blive klippet."""

from __future__ import annotations

import pytest

from core.services.round_budget_notice import round_budget_notice as n


def test_ingen_stoej_tidligt_i_turen():
    """Et varsel på runde 3 af 30 er ren støj i prompten."""
    for r in (0, 5, 15, 20):
        assert n(round_index=r, max_rounds=30) == ""


def test_varslet_begynder_fem_runder_foer():
    """Fem giver plads til at samle de sidste kald OG skrive et ordentligt svar.
    Et varsel på sidste runde ville være det samme som ingen varsel."""
    assert "5 arbejdsrunder tilbage" in n(round_index=24, max_rounds=30)
    assert n(round_index=23, max_rounds=30) == ""


def test_taeller_ned_korrekt():
    for r, forventet in ((24, 5), (25, 4), (26, 3), (27, 2)):
        assert f"{forventet} arbejdsrunder tilbage" in n(round_index=r, max_rounds=30)


def test_sidste_arbejdsrunde_siger_det_ligeud():
    t = n(round_index=28, max_rounds=30)
    assert "Sidste arbejdsrunde" in t
    assert "ikke kalde flere værktøjer" in t


def test_finalize_runden_faar_INTET_varsel():
    """Runde 29 har allerede sin egen tvungne finalize-instruktion. To beskeder
    om det samme ville støje — og modsige hinanden om hvad han må."""
    assert n(round_index=29, max_rounds=30) == ""


def test_varslet_opfordrer_til_at_batche():
    """Bjørn spurgte om runderne kunne gøres længere. Det kan de ikke som knap —
    intet begrænser tool-kald pr. runde, modellen vælger selv. Løftestangen er
    at batche, og den kan han kun trække i hvis han ved budgettet slipper op."""
    t = n(round_index=25, max_rounds=30)
    assert "flere værktøjer i samme runde" in t


def test_virker_ogsaa_naar_affekt_har_saenket_budgettet():
    """Affekt-modulering sænker til 12-20 under pres. Varslet skal følge med."""
    assert "5 arbejdsrunder tilbage af 12" in n(round_index=6, max_rounds=12)
    assert n(round_index=11, max_rounds=12) == ""      # finalize
    assert "Sidste arbejdsrunde" in n(round_index=10, max_rounds=12)


@pytest.mark.parametrize("r,mx", [(0, 1), (0, 0), (-1, 30), (5, -3)]) 
def test_meningsloese_vaerdier_giver_tavshed(r, mx):
    assert n(round_index=r, max_rounds=mx) == ""


def test_ugyldige_typer_vaelter_ikke_loopet():
    assert n(round_index="tre", max_rounds=30) == ""      # type: ignore[arg-type]
    assert n(round_index=5, max_rounds=None) == ""        # type: ignore[arg-type]


def test_varslet_er_koblet_ind_i_loopet_FOER_finalize():
    """Selve tilslutningen. Et modul der ikke kaldes, varsler ingen.

    Og rækkefølgen er ikke ligegyldig: varslet må kun tilføjes når det IKKE er
    sidste runde, ellers ville han få både «saml dine kald» og «kald ikke flere
    værktøjer» i samme tur.
    """
    import inspect

    from core.services import visible_runs as VR

    kilde = inspect.getsource(VR)
    assert "round_budget_notice" in kilde, "modulet kaldes ikke fra loopet"
    i_varsel = kilde.index("round_budget_notice")
    i_finalize = kilde.index('"Skriv nu dit endelige svar til brugeren i prosa')
    assert i_varsel < i_finalize, "varslet skal stå før finalize-blokken"
    # Vagten mod at begge udløses samtidig
    assert "if not _is_last_round:" in kilde
