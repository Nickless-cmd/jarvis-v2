"""Alderen var et terningkast — nu er den en måling.

Filen havde INGEN test. Den bestod af en docstring, `import pytest` og en
stjerne-import: fire linjer der tilfredsstiller dæknings-gaten uden at måle
noget. Målt 25/9-2026: 3 af 1.746 testfiler var af den slags.

`age_journey()` gjorde `_total_thoughts += thoughts or random.randint(5, 20)`,
og før det sad alderen fast på «spæd» i månedsvis fordi `random` manglede som
import og NameError'en blev slugt. Begge tilstande er samme fejl set fra hver
sin side: tallet betød intet.
"""
from __future__ import annotations

import pytest

import core.services.temporal_body as T


@pytest.fixture(autouse=True)
def _tom_tilstand():
    """Skærm-mappen fra conftest er sessions-bred, så nøglen skal tømmes."""
    T.reset_temporal_body()
    yield
    T.reset_temporal_body()


@pytest.fixture
def _tanker(monkeypatch):
    """Sæt tanke-tallet uden at røre databasen."""
    def saet(antal: int):
        monkeypatch.setattr(T, "_taelling", lambda: antal)
    return saet


def test_alderen_kommer_fra_en_TAELLING_ikke_fra_et_kast(_tanker):
    """KERNEN. Samme input skal give samme alder — hver gang."""
    _tanker(26416)   # målt på CT105 25/9-2026
    assert T.get_temporal_body_age() == "gammel"
    assert T.get_temporal_body_age() == "gammel"
    assert T.build_temporal_body_surface()["total_thoughts"] == 26416


def test_age_journey_laegger_IKKE_tanker_til(_tanker):
    """Et tik er et tik. Tankerne tælles i databasen, ikke her.

    Både fladen OG `age_journey`s eget svar måles. Første udgave af testen så
    kun på fladen, og en mutation der lagde tallet til i returværdien slap
    igennem (mutationstest 25/9-2026).
    """
    _tanker(500)
    foer = T.build_temporal_body_surface()["total_thoughts"]

    svar1 = T.age_journey()
    svar2 = T.age_journey(thoughts=9999)

    assert svar1["total_thoughts"] == foer
    assert svar2["total_thoughts"] == foer, "argumentet blev lagt til"
    assert T.build_temporal_body_surface()["total_thoughts"] == foer
    # Tikket skal derimod TAELLE.
    assert svar2["ticks_alive"] == svar1["ticks_alive"] + 1


def test_tik_taelleren_overlever_at_modulet_indlaeses_forfra():
    import importlib

    T.age_journey()
    T.age_journey()

    frisk = importlib.reload(T)
    try:
        assert frisk.build_temporal_body_surface()["ticks_alive"] == 2
    finally:
        frisk.reset_temporal_body()
        importlib.reload(T)


@pytest.mark.parametrize("tanker,forventet", [
    (0, "spæd"), (999, "spæd"), (1000, "ung"), (4999, "ung"),
    (5000, "moden"), (19999, "moden"), (20000, "gammel"),
])
def test_traersklerne_staar_uroerte(_tanker, tanker, forventet):
    """Skalaen er IKKE justeret.

    Tærsklerne blev skrevet til en terning-akkumulator der voksede langsomt
    fra nul; mod en rigtig tælling (26.416) mætter de straks. Det er en
    beslutning om hvad alder skal betyde — ikke en fejl i målingen — så de
    pinnes som de står, indtil nogen tager den beslutning.
    """
    _tanker(tanker)
    assert T.get_temporal_body_age() == forventet


def test_en_database_der_ikke_kan_laeses_vaelter_ikke_tikket(monkeypatch):
    def _knaek():
        raise RuntimeError("databasen er væk")
    monkeypatch.setattr("core.runtime.db.connect", _knaek)
    T._tanke_cache = None

    assert T._taelling() == 0
    assert T.build_temporal_body_surface()["active"] is True


def test_et_tomt_modul_er_LEVENDE_ikke_doedt(_tanker):
    """`active` stod som `_ticks_alive > 0`. En nyligt genstartet proces er
    ikke et dødt modul — og api-processen tikker aldrig selv."""
    _tanker(0)
    flade = T.build_temporal_body_surface()
    assert flade["active"] is True
    assert flade["ticks_alive"] == 0
