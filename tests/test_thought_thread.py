"""Thought thread — kontrakten paa succes-stien.

11/11-2026: `_find_thread()` returnerede et dict UDEN `active` paa succes-stien;
kun fejl-stien satte `{"active": False}`. `attention_contour._form()` laeste
`bool(traad.get("active"))` og fik derfor altid `None` -> `False`, saa
opmaerksomhedsfladen returnerede SPREDT ("spredt som stjerner") uanset hvor
sammenhaengende traaden var. Fire af fem former var uopnaaelige i drift.

Testene her maaler kontrakten direkte paa `_find_thread` — ikke gennem
`attention_contour` — saa de fanger bruddet uanset hvem der laeser dictet.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import thought_thread as T


def _tanke(tekst: str, *, minutter_siden: int = 0, record_type: str = "meta-reflection"):
    return {
        "record_id": f"rec-{minutter_siden}-{tekst[:12]}",
        "record_type": record_type,
        "focus": tekst,
        "summary": tekst,
        "created_at": datetime.now(UTC) - timedelta(minutes=minutter_siden),
    }


DELT_TEMA = "partial batch koersel"


def test_succes_stien_har_active_sat():
    """Rod-aarsagen: `active` manglede, og alt nedstroems laeste den som False."""
    traad = T._find_thread([_tanke(DELT_TEMA, minutter_siden=10),
                            _tanke(DELT_TEMA, minutter_siden=5)])

    assert traad is not None, "to tanker med delt tema skal give en traad"
    assert traad.get("active") is True, (
        "succes-stien SKAL saette active=True — ellers kan attention_contour "
        "kun sige 'spredt som stjerner'"
    )


def test_succes_dictet_baerer_de_noegler_forbrugerne_laeser():
    """Kontrakten som attention_contour og build_thought_thread_surface laeser."""
    traad = T._find_thread([_tanke(DELT_TEMA, minutter_siden=20),
                            _tanke(DELT_TEMA, minutter_siden=10)])

    assert traad is not None
    for noegle in (
        "active",
        "theme",
        "theme_tokens",
        "carrying_count",
        "interruption_count",
        "age_minutes",
        "last_thought_summary",
        "last_thought_at",
        "last_thought_type",
    ):
        assert noegle in traad, f"manglende noegle i traad-dictet: {noegle}"

    assert traad["theme"], "theme skal vaere en ikke-tom streng"
    assert traad["carrying_count"] >= 2
    assert isinstance(traad["theme_tokens"], list)


def test_for_faa_tanker_giver_ingen_traad():
    """Under to tanker er der intet tema at baere."""
    assert T._find_thread([]) is None
    assert T._find_thread([_tanke(DELT_TEMA)]) is None


def test_uden_delt_tema_giver_ingen_traad():
    """To tanker uden fælles noegleord er ikke en traad."""
    assert T._find_thread([
        _tanke("partial batch koersel", minutter_siden=10),
        _tanke("vejr og temperatur udenfor", minutter_siden=5),
    ]) is None


def test_afbrydelser_taelles():
    """Tanker mellem yderpunkterne uden tema er afbrydelser."""
    traad = T._find_thread([
        _tanke(DELT_TEMA, minutter_siden=30),
        _tanke("vejr og temperatur udenfor", minutter_siden=20),
        _tanke(DELT_TEMA, minutter_siden=10),
    ])

    assert traad is not None
    assert traad["carrying_count"] == 2
    assert traad["interruption_count"] == 1


def test_get_current_thread_fejl_stien_siger_ikke_aktiv(monkeypatch):
    """Naar beregningen fejler, skal tilstanden vaere aerligt inaktiv."""
    def _braender():
        raise RuntimeError("bevidst fejl i testen")

    monkeypatch.setattr(T, "_recent_thoughts", _braender)
    monkeypatch.setattr(T, "_last_thread", {})
    monkeypatch.setattr(T, "_last_computed_ts", 0.0)

    traad = T.get_current_thread()
    assert traad.get("active") is False
    assert "theme" not in traad


def test_tom_taenkeliste_giver_ikke_aktiv(monkeypatch):
    """Ingen nye tanker -> ingen traad -> ikke aktiv."""
    monkeypatch.setattr(T, "_recent_thoughts", lambda: [])
    monkeypatch.setattr(T, "_last_thread", {})
    monkeypatch.setattr(T, "_last_computed_ts", 0.0)

    traad = T.get_current_thread()
    assert traad.get("active") is False


@pytest.mark.parametrize("antal", [2, 3, 7])
def test_carrying_count_foelger_antal_deltagende_tanker(antal):
    """Alle tanker med temaet skal taelles med, ikke kun de to foerste."""
    tanker = [_tanke(DELT_TEMA, minutter_siden=i * 5) for i in range(antal)]
    traad = T._find_thread(tanker)

    assert traad is not None
    assert traad["carrying_count"] == antal
