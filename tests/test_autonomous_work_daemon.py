"""Tests for autonomous_work_daemon — særligt kø-grænsen (3/11-2026).

Baggrund (målt): daemonen skrev forslag ind i `autonomous_work_log.json` ved
hvert ledigt tick. `_save` trimmer til `_LOG_MAX` (300), så gamle forslag blev
ikke afvist — de blev kastet væk ved rotation. Målt i den levende fil: 300
poster, ALLE `pending`, ældste 28/10. `resolve_proposal` findes og virker, men
kaldes kun manuelt, så der var ingen automatisk forbruger: produktionen fyldte
loggen op og skubbede et gammelt forslag ud, uden at nogen nogensinde så det.

Vagterne her låser at produktionen standser når køen er fuld af ubehandlede
forslag, og at fladen siger det højt i stedet for at se sund ud.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import autonomous_work_daemon as aw


def _entry(i: int, *, status: str = "pending", dage: int = 0) -> dict:
    at = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    return {
        "proposal_id": f"aw-test{i}",
        "at": at,
        "type": "research",
        "title": f"forslag {i}",
        "details": {},
        "rationale": "",
        "status": status,
    }


@pytest.fixture
def fuld_koe(monkeypatch):
    """Log fyldt til loftet med ubehandlede forslag."""
    poster = [_entry(i, dage=6) for i in range(aw._LOG_MAX)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    monkeypatch.setattr(aw, "_save", lambda items: None)
    monkeypatch.setattr(aw, "_is_low_activity", lambda: (True, "stub-idle"))
    monkeypatch.setattr(aw, "_proposals_last_hour", lambda: 0)
    return poster


def test_tick_standser_naar_koeen_er_fuld_og_uforbrugt(fuld_koe):
    """Ved fuld kø må ticken IKKE producere flere forslag.

    Uden denne grænse blev hvert nyt forslag skrevet ind og skubbede et gammelt
    ud — rotation der skjuler at intet bliver behandlet.
    """
    resultat = aw.tick()
    assert resultat["skipped"] is True
    assert resultat["reason"] == "queue-full-unconsumed"
    assert resultat["pending"] == aw._LOG_MAX


def test_tick_producerer_naar_der_er_plads(monkeypatch):
    """Under loftet skal den stadig producere — grænsen må ikke gøre den død."""
    poster = [_entry(i, status="completed") for i in range(5)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    monkeypatch.setattr(aw, "_save", lambda items: None)
    monkeypatch.setattr(aw, "_is_low_activity", lambda: (True, "stub-idle"))
    monkeypatch.setattr(aw, "_proposals_last_hour", lambda: 0)
    monkeypatch.setattr(aw, "_plan_once", lambda: ["aw-ny"])

    resultat = aw.tick()
    assert resultat["skipped"] is False
    assert resultat["proposals_created"] == 1


def test_fuld_koe_rapporteres_som_uforbrugt(fuld_koe):
    """Fladen skal sige at køen er fuld og uforbrugt — ikke se som en travl kø.

    Før stod der «300 afventende forslag af 300 total», hvilket er sandt og
    samtidig misvisende: ingen af dem var nogensinde behandlet.
    """
    overflade = aw.build_autonomous_work_surface()
    assert overflade["pending_count"] == aw._LOG_MAX
    tekst = overflade["summary"]
    assert "FULD" in tekst
    assert "uforbrugt" in tekst
    assert "6 dage" in tekst


def test_aendelig_koe_rapporterer_alder(monkeypatch):
    """Også en ikke-fuld kø skal vise hvor gammelt det ældste forslag er.

    Alder er det der afslører om køen bliver behandlet eller bare fyldt op.
    """
    poster = [_entry(0, dage=3), _entry(1, dage=0)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    tekst = aw.build_autonomous_work_surface()["summary"]
    assert "2 afventende" in tekst
    assert "3 dage" in tekst
