"""Fejeren for udløbne godkendelser.

Fejlen den blev skrevet for var ikke at `expire_stale()` var forkert — den var
testet og virkede. Fejlen var at **ingen kaldte den**. Derfor er den vigtigste
prøve her ikke at fejningen sker, men at fejeren er registreret et sted der
faktisk kører.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_approval_bridge as B
from core.runtime.db import connect
from core.services import approval_expiry_daemon as D


@pytest.fixture(autouse=True)
def _ren(isolated_runtime):
    D._nulstil_for_tests()
    yield
    D._nulstil_for_tests()


def _tilstand(aid: str) -> str:
    with connect() as c:
        r = c.execute("SELECT state FROM approval_claims WHERE approval_id = ?",
                      (aid,)).fetchone()
    return str(r[0]) if r else ""


# ── koblingen: den fejl der faktisk skete ────────────────────────────────

def test_fejeren_ER_registreret_i_en_familie_der_koerer():
    """DEN afgoerende prøve. `expire_stale()` var korrekt og testet i maaneder
    og havde nul kaldere — en mekanisme uden kalder er ingen mekanisme."""
    from core.services.cluster_daemon_families import _INFRA_UNCONDITIONAL
    navne = [n for n, _ in _INFRA_UNCONDITIONAL]
    assert "approval_expiry" in navne


def test_familiens_medlem_kalder_faktisk_igennem(monkeypatch):
    """Registreret under det rigtige navn er ikke nok — den skal naa frem."""
    kaldt: list[bool] = []
    monkeypatch.setattr(D, "tick_approval_expiry_daemon",
                        lambda *a, **k: kaldt.append(True) or {"fejet": True})
    from core.services.cluster_daemon_families import _infra_approval_expiry_live
    _infra_approval_expiry_live({})
    assert kaldt == [True]


# ── hvad den fejer, og hvad den aldrig roerer ────────────────────────────

def test_en_udloebet_pending_bliver_fejet():
    aid = "a-pending"
    B.request(aid, tool_name="gmail_send", arguments={"til": "x"},
              run_id="r1", session_id="s1")
    assert _tilstand(aid) == B.PENDING
    D.tick_approval_expiry_daemon(now=datetime.now(UTC) + timedelta(hours=2))
    assert _tilstand(aid) == B.EXPIRED


def test_dispatching_roeres_ALDRIG(monkeypatch):
    """En afsendelse der er i gang udloeber ikke — dens udfald er ukendt, og
    at kalde den udloebet ville vaere at paastaa noget vi ikke ved."""
    aid = "a-dispatching"
    args = {"til": "x"}
    B.request(aid, tool_name="gmail_send", arguments=args, run_id="r1", session_id="s1")
    B.decide(aid, approved=True)
    B.claim(aid, tool_name="gmail_send", arguments=args)
    assert _tilstand(aid) == B.DISPATCHING
    D.tick_approval_expiry_daemon(now=datetime.now(UTC) + timedelta(hours=2))
    assert _tilstand(aid) == B.DISPATCHING


def test_en_frisk_godkendelse_roeres_ikke():
    """Kontrolarm. Uden den ville en fejer der markerede ALT bestaa proeverne
    ovenfor."""
    aid = "a-frisk"
    B.request(aid, tool_name="gmail_send", arguments={"til": "x"},
              run_id="r1", session_id="s1")
    D.tick_approval_expiry_daemon(now=datetime.now(UTC))
    assert _tilstand(aid) == B.PENDING


# ── kadencen ─────────────────────────────────────────────────────────────

def test_anden_koersel_inden_for_kadencen_springer_over():
    nu = datetime.now(UTC)
    assert D.tick_approval_expiry_daemon(now=nu)["fejet"] is True
    r = D.tick_approval_expiry_daemon(now=nu + timedelta(minutes=1))
    assert r == {"fejet": False, "grund": "kadence"}


def test_efter_kadencen_koerer_den_igen():
    nu = datetime.now(UTC)
    D.tick_approval_expiry_daemon(now=nu)
    r = D.tick_approval_expiry_daemon(now=nu + timedelta(minutes=6))
    assert r["fejet"] is True


# ── fejl ─────────────────────────────────────────────────────────────────

def test_en_fejl_kaster_ikke_men_tier_heller_ikke(monkeypatch, caplog):
    """Familien isolerer fejl. En fejer der stille holder op med at virke er
    praecis den fejl filen blev skrevet for at rette."""
    import logging

    import core.runtime.db_approval_bridge as DB
    monkeypatch.setattr(DB, "expire_stale",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("db nede")))
    with caplog.at_level(logging.WARNING):
        r = D.tick_approval_expiry_daemon(now=datetime.now(UTC))
    assert r["fejet"] is False and r["grund"] == "fejl"
    assert any("approval_expiry" in x.getMessage() for x in caplog.records)
