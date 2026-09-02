"""Livstegn — er Jarvis vågen, og hvad lavede han sidst?

Jarvis' eget ønske: «en stille indikator ... baseret på eksisterende
heartbeat/livstegn fra runtime, IKKE en statisk online-prik der lyver».
Testene holder fast i netop dét: fire tilstande, og «unknown» når vi ikke kan se
ham — frem for et gæt der ser grønt ud.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import companion_presence as cp


def test_arbejder_slaar_vaagen(monkeypatch):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(cp, "_last_heartbeat",
                        lambda: {"finished_at": (now - timedelta(minutes=5)).isoformat(),
                                 "tick_status": "completed", "status": "completed",
                                 "decision": "execute", "summary": "ryddede op"})
    monkeypatch.setattr(cp, "_running_now", lambda: True)
    assert cp.build_presence(now=now)["state"] == "working"


def test_friskt_hjerteslag_er_vaagen(monkeypatch):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(cp, "_last_heartbeat",
                        lambda: {"finished_at": (now - timedelta(minutes=10)).isoformat(),
                                 "status": "completed", "decision": "noop", "summary": "kiggede"})
    monkeypatch.setattr(cp, "_running_now", lambda: False)
    out = cp.build_presence(now=now)
    assert out["state"] == "awake"
    assert out["last_beat_ago_s"] == 600
    # Livstegnet skal kunne MÆRKES — ikke bare lyse.
    assert out["last_action"] == "kiggede"


def test_gammelt_hjerteslag_er_stille(monkeypatch):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(cp, "_last_heartbeat",
                        lambda: {"finished_at": (now - timedelta(hours=4)).isoformat()})
    monkeypatch.setattr(cp, "_running_now", lambda: False)
    assert cp.build_presence(now=now)["state"] == "quiet"


def test_ulaeseligt_spor_giver_unknown_ikke_groent(monkeypatch):
    """Kan vi ikke se ham, må indikatoren ikke gætte. Det var præcis dét den
    statiske «online»-prik gjorde forkert."""
    def _boom():
        raise RuntimeError("db nede")
    monkeypatch.setattr(cp, "_last_heartbeat", _boom)
    assert cp.build_presence()["state"] == "unknown"


def test_tidsstempel_uden_mening_giver_unknown(monkeypatch):
    monkeypatch.setattr(cp, "_last_heartbeat", lambda: {"finished_at": "ikke en dato"})
    assert cp.build_presence()["state"] == "unknown"
