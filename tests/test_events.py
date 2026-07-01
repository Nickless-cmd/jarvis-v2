"""Tests for core/eventbus/events.py — familie-validering."""
from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event


def test_awareness_families_registered():
    # Latent-bug-fix 1. jul: disse var afvist (ikke-registreret) → awareness-events persisterede aldrig.
    assert "reboot" in ALLOWED_EVENT_FAMILIES
    assert "inner_voice" in ALLOWED_EVENT_FAMILIES


def test_event_create_accepts_registered_family():
    e = Event.create("inner_voice.signal", {"x": 1})
    assert e.family == "inner_voice"
    e2 = Event.create("reboot.imminent", {"graceful": True})
    assert e2.family == "reboot"
