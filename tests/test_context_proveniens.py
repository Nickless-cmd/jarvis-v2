"""Kontekst-proveniens: registeret der gør `memcite` målbar i stedet for gættet.

2/11-2026. `memcite` blev godkendt ubetinget, fordi der ikke fandtes nogen at
spørge om memory faktisk var i prompten. Det her er den nogen.

Det der testes er ikke «at funktionen findes», men de fire tilstande der gør
den fail-closed — og den ene fælde der ellers gør den meningsløs: at en gammel
registrering kan godkende en ny tur.
"""

from __future__ import annotations

import pytest

from core.services import context_proveniens as cp


@pytest.fixture(autouse=True)
def _rent_register():
    cp.ryd_register()
    yield
    cp.ryd_register()


def test_memory_i_prompten_godkender():
    cp.marker_memory_i_kontekst("s1", 7)
    assert cp.memory_i_kontekst("s1") is True


def test_nul_linjer_er_en_sandhed_ikke_en_mangel():
    """`antal_linjer = 0` betyder eksplicit «ingen memory» — ikke «ved det ikke».

    Forskellen betyder noget: den skal kunne slå en tidligere tur ud, hvor der
    VAR memory. Ellers arver en tom prompt en gammel godkendelse.
    """
    cp.marker_memory_i_kontekst("s1", 5)
    assert cp.memory_i_kontekst("s1") is True

    cp.marker_memory_i_kontekst("s1", 0)
    assert cp.memory_i_kontekst("s1") is False


def test_ukendt_session_afvises():
    assert cp.memory_i_kontekst("aldrig-set") is False


def test_tom_session_afvises():
    cp.marker_memory_i_kontekst("", 9)
    assert cp.memory_i_kontekst("") is False


def test_udloebet_registrering_kan_ikke_godkende_en_ny_tur(monkeypatch):
    """Kernen i TTL'en: en tur fra i går må ikke godkende en `memcite` i dag."""
    nu = [1000.0]
    monkeypatch.setattr(cp.time, "monotonic", lambda: nu[0])

    cp.marker_memory_i_kontekst("s1", 3)
    assert cp.memory_i_kontekst("s1") is True

    nu[0] += cp.TTL_SEKUNDER + 1
    assert cp.memory_i_kontekst("s1") is False


def test_registrering_inden_for_ttl_virker_stadig(monkeypatch):
    nu = [1000.0]
    monkeypatch.setattr(cp.time, "monotonic", lambda: nu[0])

    cp.marker_memory_i_kontekst("s1", 2)
    nu[0] += cp.TTL_SEKUNDER - 1
    assert cp.memory_i_kontekst("s1") is True


def test_sessioner_laekker_ikke_ind_i_hinanden():
    cp.marker_memory_i_kontekst("s1", 4)
    assert cp.memory_i_kontekst("s2") is False


def test_negativt_antal_behandles_som_nul():
    cp.marker_memory_i_kontekst("s1", -5)
    assert cp.memory_i_kontekst("s1") is False
