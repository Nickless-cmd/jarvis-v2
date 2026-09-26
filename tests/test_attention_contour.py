"""Opmærksomhedens form var et terningkast — nu er den udledt.

Filen havde INGEN test. Den bestod af en docstring, `import pytest` og en
stjerne-import: fire linjer der tilfredsstiller dæknings-gaten uden at måle
noget. Det var den sidste af tre af den slags (de to andre var
`test_existential_drift.py` og `test_temporal_body.py`).

Modulet gjorde `random.choice(_shapes)` — og formen BRUGES: den injiceres i
hjerteslaget og vises i Centralen. Værre endnu kaldte fladen terningen TRE
gange i samme dict, så ét svar kunne sige «kristalliseret som is»,
«kaotisk som storm» og «spredt som stjerner» på samme tid. Målt 26/9-2026:
20 af 20 flader modsagde sig selv.
"""
from __future__ import annotations

import pytest

import core.services.attention_contour as A


@pytest.fixture
def _maalt(monkeypatch):
    """Sæt tråd og rytme uden at røre databasen."""
    def saet(*, baerer=0, afbrydelser=0, puls=1.0, tempo="steady", aktiv=True):
        monkeypatch.setattr(A, "_maal", lambda: (
            {"active": aktiv, "carrying_count": baerer,
             "interruption_count": afbrydelser},
            {"pulse_rate": puls, "subjective_time_pressure": tempo},
        ))
    return saet


def test_samme_input_giver_samme_form(_maalt):
    """KERNEN. `random.choice` kunne aldrig svare det samme to gange i træk."""
    _maalt(baerer=74, afbrydelser=21, puls=0.3, tempo="breathing")
    svar = {A.get_attention_shape() for _ in range(20)}
    assert len(svar) == 1, f"formen skiftede uden at input gjorde: {svar}"


def test_fladen_modsiger_IKKE_sig_selv(_maalt):
    """Tre kald til terningen i ét dict. Målt: 20 af 20 modsagde sig selv."""
    _maalt(baerer=74, afbrydelser=21, puls=0.3, tempo="breathing")
    for _ in range(20):
        f = A.build_attention_contour_surface()
        assert f["current_shape"] == f["summary"]
        assert f["current_shape"] in f["description"]


def test_fladen_udleder_ÉN_gang(monkeypatch):
    """Ikke bare «den modsiger ikke sig selv» — den må ikke kaste tre gange.

    Første udgave af testen ovenfor låste input fast, og så gav tre udledninger
    samme svar: mutationen «udled tre gange igen» slap igennem. Kaldene tælles
    derfor direkte. Det er også billigere — hver udledning rammer både
    `thought_thread` og `temporal_rhythm`.
    """
    kald: list[int] = []

    def _taellende():
        kald.append(1)
        return ({"active": True, "carrying_count": 74, "interruption_count": 21},
                {"pulse_rate": 0.3, "subjective_time_pressure": "breathing"})

    monkeypatch.setattr(A, "_maal", _taellende)
    A.build_attention_contour_surface()

    assert len(kald) == 1, f"fladen maalte {len(kald)} gange"


def test_den_maalte_tilstand_er_tidevand(_maalt):
    """CT105 26/9-2026: 74 tanker over 133 min, 21 afbrydelser, puls 0,3.

    Han BÆRER en tråd, men den brydes hver fjerde tanke. Det er hverken
    laseren eller stormen.
    """
    _maalt(baerer=74, afbrydelser=21, puls=0.3, tempo="breathing")
    ord_ = A.get_attention_shape()
    assert ord_ == A.TIDEVAND
    assert "21/74" in A.build_attention_contour_surface()["grundlag"]


def test_ingen_traad_er_spredt(_maalt):
    _maalt(aktiv=False, baerer=0)
    assert A.get_attention_shape() == A.SPREDT


def test_en_uafbrudt_traad_er_en_laser(_maalt):
    _maalt(baerer=12, afbrydelser=0, puls=1.0)
    assert A.get_attention_shape() == A.LASER


def test_en_kort_traad_uden_afbrydelser_er_IKKE_en_laser(_maalt):
    """Tre tanker er ikke fokus, uanset at ingen har afbrudt dem."""
    _maalt(baerer=3, afbrydelser=0, puls=1.0)
    assert A.get_attention_shape() != A.LASER


def test_racende_puls_med_afbrydelser_er_storm(_maalt):
    _maalt(baerer=20, afbrydelser=6, puls=1.6, tempo="racing")
    assert A.get_attention_shape() == A.STORM


def test_rolig_puls_og_faa_afbrydelser_er_is(_maalt):
    _maalt(baerer=40, afbrydelser=2, puls=0.3, tempo="breathing")
    assert A.get_attention_shape() == A.IS


def test_ordene_er_uroerte():
    """De fem ord er hans. Kastet er væk — ikke vokabularet."""
    assert A._shapes == [
        "spredt som stjerner",
        "fokuseret som en laser",
        "bølgende som tidevand",
        "kristalliseret som is",
        "kaotisk som storm",
    ]


def test_grundlaget_foelger_med_ordet(_maalt):
    """Et ord der ikke kan føres tilbage til et tal er en pænere overflade
    end `random.choice` — ikke en måling."""
    _maalt(baerer=40, afbrydelser=2, puls=0.3, tempo="breathing")
    g = A.build_attention_contour_surface()["grundlag"]
    assert "2/40" in g and "0.30" in g


def test_kilder_der_ikke_kan_laeses_vaelter_ikke_fladen(monkeypatch):
    """Formen ligger i hjerteslaget. En død kilde må ikke standse det."""
    def _knaek():
        raise RuntimeError("tråden er væk")
    monkeypatch.setattr("core.services.thought_thread.get_current_thread", _knaek)
    monkeypatch.setattr("core.services.temporal_rhythm.get_current_rhythm", _knaek)

    f = A.build_attention_contour_surface()
    assert f["active"] is True
    assert f["current_shape"] == A.SPREDT
    assert f["grundlag"]
