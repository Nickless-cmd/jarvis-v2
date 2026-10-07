"""Ambient presence må ikke ringe på Bjørns telefon.

Målt 7/10-2026: 14 af 31 ntfy-beskeder på ét døgn var Jarvis' egne
tilstandsskift — «træder ind i legetilstand», «vender tilbage til arbejde» —
plus et ensomt «·» i timen. Bjørn spurgte selv: «Det er nogen sjove ting jeg
får på ntfy… lege tilstand??»

Signalet er stadig ægte; det hører bare i Centralen, ikke på en telefon.
Testene her holder den grænse: ntfy må ikke importeres eller kaldes fra
modulet, og event-bussen skal stadig få signalet.
"""
from __future__ import annotations

import inspect

from core.services import ambient_presence


def test_modulet_importerer_ikke_ntfy():
    """Ingen ntfy-import nogen steder i modulet — heller ikke lazy i en funktion.

    Kilden læses som tekst, ikke som modul: et lazy import inde i en funktion
    ville ikke ses i `dir()`, og det er præcis den form der sad her før.
    """
    kilde = inspect.getsource(ambient_presence)
    assert "ntfy_gateway" not in kilde, (
        "ambient_presence må ikke sende til telefonen — signalet hører i Centralen"
    )
    assert "send_notification" not in kilde


def test_ambient_signal_publicerer_paa_bussen(monkeypatch):
    """Signalet skal stadig ud — bare et andet sted."""
    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        ambient_presence.event_bus, "publish",
        lambda navn, data: set_events.append((navn, data)),
    )
    # Rate-limit'en er modul-global; nulstil så testen ikke afhænger af rækkefølge.
    monkeypatch.setattr(ambient_presence, "_LAST_SIGNAL_AT", None)

    ok = ambient_presence.emit_ambient_signal(kind="play_mode", detail="træder ind i legetilstand")

    assert ok is True
    assert len(set_events) == 1
    navn, data = set_events[0]
    assert navn == "runtime.ambient_presence_signal"
    assert data["kind"] == "play_mode"
    assert data["label"] == "Leger"


def test_presence_rhythm_publicerer_uden_telefon(monkeypatch):
    """«Stadig her»-pulsen er den mest støjende — den skal kun på bussen."""
    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        ambient_presence.event_bus, "publish",
        lambda navn, data: set_events.append((navn, data)),
    )
    monkeypatch.setattr(ambient_presence, "_LAST_RHYTHM_AT", None)

    ok = ambient_presence.emit_presence_rhythm()

    assert ok is True
    assert [n for n, _ in set_events] == ["runtime.ambient_presence_rhythm"]


def test_rate_limit_er_bevaret(monkeypatch):
    """To signaler i træk inden for 30 min: kun det første slipper igennem."""
    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        ambient_presence.event_bus, "publish",
        lambda navn, data: set_events.append((navn, data)),
    )
    monkeypatch.setattr(ambient_presence, "_LAST_SIGNAL_AT", None)

    foerste = ambient_presence.emit_ambient_signal(kind="insight", detail="en")
    anden = ambient_presence.emit_ambient_signal(kind="insight", detail="to")

    assert foerste is True
    assert anden is False
    assert len(set_events) == 1


def test_state_shift_gaar_gennem_ambient_signal(monkeypatch):
    """Faseovergangen skal stadig producere et signal — den er ikke fjernet,
    kun flyttet."""
    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        ambient_presence.event_bus, "publish",
        lambda navn, data: set_events.append((navn, data)),
    )
    monkeypatch.setattr(ambient_presence, "_LAST_SIGNAL_AT", None)

    ok = ambient_presence.emit_state_shift("active", "play_mode")

    assert ok is True
    assert set_events[0][1]["detail"] == "træder ind i legetilstand"
