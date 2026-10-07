"""Tests for core/services/peak_varsel_daemon.py (30/9-2026).

Dækker: weekend, for-tidligt, dagvinduet vs. natvinduet, dedup pr. vindue,
og at varsel-teksten regner i dansk tid — sommer (CEST) vs. vinter (CET).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services import peak_varsel_daemon as pv


def _u(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.fixture()
def ingen_kv(monkeypatch):
    """Isolér fra DB: hukommelsen om «sidst varslet» bor i runtime_state_kv."""
    monkeypatch.setattr(pv, "_allerede_varslet", lambda a: False)
    monkeypatch.setattr(pv, "_marker_varslet", lambda a: None)


def test_weekend_fyrer_ikke(monkeypatch, ingen_kv):
    """Lørdag morgen: der er ingen myldretid, og mandagens vindue må IKKE varsles."""
    monkeypatch.setattr(pv, "_send_varsel", lambda t, b: pytest.fail("må ikke sende"))
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 3, 5, 45))  # lørdag
    assert r["fired"] is False
    assert r["reason"] == "weekend"


def test_soendag_fyrer_ikke(monkeypatch, ingen_kv):
    monkeypatch.setattr(pv, "_send_varsel", lambda t, b: pytest.fail("må ikke sende"))
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 4, 5, 45))  # søndag
    assert r["fired"] is False
    assert r["reason"] == "weekend"


def test_for_tidligt(monkeypatch, ingen_kv):
    """Mandag 04:00 UTC — to timer til vinduet. Ingen fyring."""
    monkeypatch.setattr(pv, "_send_varsel", lambda t, b: pytest.fail("må ikke sende"))
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 5, 4, 0))
    assert r["fired"] is False
    assert r["reason"] == "for-tidligt"
    assert r["minutter_til"] == 120


def test_15_min_foer_fyrer(monkeypatch, ingen_kv):
    """Mandag 05:45 UTC = 15 min før dagvinduet åbner."""
    kaldt = []
    monkeypatch.setattr(pv, "_send_varsel",
                        lambda t, b: kaldt.append((t, b)) or {"delivered": True})
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 5, 5, 45))
    assert r["fired"] is True
    assert r["minutter_til"] == 15
    assert kaldt and "Myldretid" in kaldt[0][0]


def test_natvinduet_varsler_ikke(monkeypatch, ingen_kv):
    """Mandag 00:50 UTC — næste vindue er nat-vinduet 01-04. Ingen at minde."""
    monkeypatch.setattr(pv, "_send_varsel", lambda t, b: pytest.fail("må ikke sende"))
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 5, 0, 50))
    assert r["fired"] is False
    assert r["reason"] == "ikke-dagvinduet"


def test_dedup_pr_vindue(monkeypatch):
    """Er vinduet allerede varslet, fyrer daemonen ikke igen."""
    monkeypatch.setattr(pv, "_send_varsel", lambda t, b: pytest.fail("må ikke sende"))
    monkeypatch.setattr(pv, "_allerede_varslet", lambda a: True)
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 5, 5, 45))
    assert r["fired"] is False
    assert r["reason"] == "allerede-varslet"


def test_markoer_saettes_ogsaa_naar_leveringen_fejler(monkeypatch):
    """Ellers ville et transportproblem give ét push hvert femte minut."""
    markeret = []
    monkeypatch.setattr(pv, "_allerede_varslet", lambda a: False)
    monkeypatch.setattr(pv, "_marker_varslet", lambda a: markeret.append(a))
    monkeypatch.setattr(pv, "_send_varsel",
                        lambda t, b: {"delivered": False, "channel": "failed"})
    r = pv.tick_peak_varsel_daemon(_u(2026, 10, 5, 5, 45))
    assert r["fired"] is True
    assert markeret, "markøren skal sættes selv når leveringen fejler"


def test_varsel_tekst_sommer_vs_vinter():
    """Samme UTC-time giver forskellig dansk visning — DST-fælden, fanget."""
    sommer_t, sommer_b = pv._varsel_tekst(_u(2026, 7, 6, 6, 0))   # CEST (UTC+2)
    vinter_t, vinter_b = pv._varsel_tekst(_u(2026, 1, 5, 6, 0))   # CET  (UTC+1)
    assert "08:00" in sommer_b and "12:00" in sommer_b
    assert "07:00" in vinter_b and "11:00" in vinter_b
    assert "Myldretid" in sommer_t


def test_vindue_slut_laeses_fra_myldre_vinduer():
    """Dagvinduet er 06-10 UTC = 4 timer. Ikke et gæt i koden."""
    assert pv._vindue_slut(_u(2026, 10, 5, 6, 0)) == _u(2026, 10, 5, 10, 0)
