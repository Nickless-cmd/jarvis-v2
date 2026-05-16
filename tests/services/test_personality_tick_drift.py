"""Tests for tick_personality_drift — heartbeat-triggered passive drift.

Designet 2026-05-16 efter Jarvis' "frosset 14 dage"-rapport. Eksisterende
decay-pathway i _deterministic_update var sofistikeret nok, men kørte
kun ved visible runs. tick_personality_drift wirer pathwayen til
heartbeat så drift sker uafhængigt af samtaler.

Outcome_signal hook reserveret til fremtidig lag 1 (credit assignment
fra self_review_outcome) — bestået gennem som outcome_status så
_deterministic_update kan behandle det.
"""
from __future__ import annotations
import time

import pytest


@pytest.fixture(autouse=True)
def reset_decay_state(monkeypatch):
    """Hvert test starter med fresh decay-debounce state."""
    import core.services.personality_vector as pv
    monkeypatch.setattr(pv, "_last_decay_ts", None)


def test_tick_drift_callable():
    """tick_personality_drift exists og er callable."""
    from core.services.personality_vector import tick_personality_drift
    assert callable(tick_personality_drift)


def test_tick_drift_invokes_decay_pathway_when_debounce_open(monkeypatch):
    """Med fresh debounce state skal tick fyre decay-pathway."""
    import core.services.personality_vector as pv

    called = {"decay": False, "outcome_status": None}

    def _fake_update(outcome_status, current):
        called["decay"] = True
        called["outcome_status"] = outcome_status
        return current

    monkeypatch.setattr(pv, "_deterministic_update", _fake_update)
    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", lambda: {"emotional_baseline": "{}"})

    pv.tick_personality_drift()
    assert called["decay"] is True
    # Default outcome_status = "idle" (ingen outcome-bumps trigges)
    assert called["outcome_status"] == "idle"


def test_tick_drift_accepts_outcome_signal_override(monkeypatch):
    """outcome_signal kwarg overstyrer default 'idle' — hook for lag 1."""
    import core.services.personality_vector as pv

    captured = {"outcome_status": None}

    def _fake_update(outcome_status, current):
        captured["outcome_status"] = outcome_status
        return current

    monkeypatch.setattr(pv, "_deterministic_update", _fake_update)
    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", lambda: {"emotional_baseline": "{}"})

    pv.tick_personality_drift(outcome_signal="completed")
    assert captured["outcome_status"] == "completed"


def test_tick_drift_returns_none_when_no_baseline_data(monkeypatch):
    """Hvis ingen personality_vector findes endnu, må vi ikke crashe."""
    import core.services.personality_vector as pv
    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", lambda: None)
    # Skal IKKE raise
    result = pv.tick_personality_drift()
    # Acceptér både None og dict-return; det vigtige er ingen crash
    assert result is None or isinstance(result, dict)


def test_tick_drift_handles_internal_error_gracefully(monkeypatch):
    """Hvis _deterministic_update raiser, må tick'en ikke smitte heartbeat."""
    import core.services.personality_vector as pv

    def _boom(outcome_status, current):
        raise RuntimeError("transient DB lock")

    monkeypatch.setattr(pv, "_deterministic_update", _boom)
    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", lambda: {"emotional_baseline": "{}"})

    # Skal IKKE raise — return None ved fejl
    result = pv.tick_personality_drift()
    assert result is None


def test_tick_drift_does_not_force_run_if_debounce_closed(monkeypatch):
    """Hvis decay-debounce er stadig lukket (<30 min siden sidst), kører
    _deterministic_update stadig (den interne logik skipper bare decay-blokken).
    Vi tester at vi ikke selv tilføjer en ekstra debounce der dobbelt-blokerer."""
    import core.services.personality_vector as pv

    called_count = {"n": 0}

    def _fake_update(outcome_status, current):
        called_count["n"] += 1
        return current

    monkeypatch.setattr(pv, "_deterministic_update", _fake_update)
    monkeypatch.setattr(pv, "get_latest_cognitive_personality_vector", lambda: {"emotional_baseline": "{}"})
    # Sæt last_decay_ts til lige nu — debounce er lukket
    monkeypatch.setattr(pv, "_last_decay_ts", time.monotonic())

    # tick'en skal stadig forsøge — det er _deterministic_update's job at
    # respektere debounce, ikke tick'ens
    pv.tick_personality_drift()
    assert called_count["n"] == 1
