"""Brugerens beskeder skal annonceres — ellers hører korrektions-lytteren intet.

Målt 7/9-2026: `experience_correction_listener` har kørt hele tiden (den
startes fra app.py:341 i jarvis-runtime, og loggen bekræfter det). Den lytter
efter `channel.chat_message_appended` og kræver `role == "user"`.

Men alle 1.478 hændelser i basen var publiceret fra
visible_runs_outcomes.py:329 med `role="assistant"` — Jarvis' eget svar.
Listeneren afviste hver eneste på første linje:

    if str(msg.get("role") or "").strip().lower() != "user":
        return ("", "")     # → continue

Derfor 0 correction-lektier, nogensinde. Hver gang Bjørn rettede ham, hørte
systemet der skulle fange det ingenting.
"""

from __future__ import annotations

import pytest


def _ny_session() -> str:
    """Rigtig session, som de øvrige chat-tests gør. En fake-forbindelse ville
    kun måle min egen stub."""
    from core.services.chat_sessions import create_chat_session
    sess = create_chat_session(title="event-test")
    return str(sess.get("session_id") or sess.get("id"))


def _fang(monkeypatch) -> list[tuple[str, dict]]:
    from core.eventbus.bus import event_bus

    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "publish",
                        lambda navn, payload: set_events.append((navn, payload)))
    return set_events


def test_en_brugerbesked_annonceres(monkeypatch, tmp_path):
    from core.services import chat_sessions as CS

    sid = _ny_session()
    set_events = _fang(monkeypatch)
    CS.append_chat_message(session_id=sid, role="user", content="nej, det passer ikke")

    kald = [(n, p) for n, p in set_events if n == "channel.chat_message_appended"]
    assert kald, "brugerens besked blev ikke annonceret"
    p = kald[0][1]
    assert p["session_id"] == sid
    # Listeneren afviser alt der ikke er role=user paa foerste linje.
    assert p["message"]["role"] == "user"
    assert "passer ikke" in p["message"]["content"]


def test_assistentens_besked_dublerer_IKKE(monkeypatch):
    """visible_runs_outcomes publicerer allerede for assistenten.

    Gjorde vi det ogsaa her, ville hver af hans ture give to haendelser, og
    Discord-abonnenten ville kunne sende svaret to gange.
    """
    from core.services import chat_sessions as CS

    sid = _ny_session()
    set_events = _fang(monkeypatch)
    CS.append_chat_message(session_id=sid, role="assistant", content="svar")

    assert not [n for n, _ in set_events if n == "channel.chat_message_appended"]


def test_en_doed_eventbus_koster_ikke_beskeden(monkeypatch):
    """Beskeden er det vigtige; sporet er til os."""
    from core.eventbus.bus import event_bus
    from core.services import chat_sessions as CS

    def eksploder(*a, **kw):
        raise RuntimeError("bus nede")

    sid = _ny_session()
    monkeypatch.setattr(event_bus, "publish", eksploder)
    ud = CS.append_chat_message(session_id=sid, role="user", content="hej")
    assert ud["role"] == "user"
