"""Fase 6 (Lag 7): absence daemon gated behind the shared event-gate.

Legacy (flag off) fires the absence narration as today. Flag on consults
event_gate.should_generative_fire — skips the LLM when the silence has not
deepened (band/hour drift), fires on real change. event_gate is mocked here.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.absence_daemon as ad


def _reset(now: datetime) -> None:
    ad._last_interaction_at = now - timedelta(hours=3)
    ad._absence_start_at = None
    ad._absence_label = ""
    ad._last_generated_at = None


def _install_fake_event_gate(monkeypatch, *, enabled: bool, fire: bool):
    from core.services import event_gate
    monkeypatch.setattr(event_gate, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: fire)
    return event_gate


def test_flag_off_fires_llm_as_today(isolated_runtime, monkeypatch):
    now = datetime.now(UTC)
    _reset(now)
    _install_fake_event_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(ad, "_generate_absence_label", return_value="stille") as mock_gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_llm(isolated_runtime, monkeypatch):
    now = datetime.now(UTC)
    _reset(now)
    _install_fake_event_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(ad, "_generate_absence_label", return_value="stille") as mock_gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)
    mock_gen.assert_not_called()
    assert result == {"skipped": "no_signal_change"}


def test_flag_on_signal_changed_fires_llm(isolated_runtime, monkeypatch):
    now = datetime.now(UTC)
    _reset(now)
    _install_fake_event_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(ad, "_generate_absence_label", return_value="stille") as mock_gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    now = datetime.now(UTC)
    _reset(now)
    from core.services import event_gate

    def _boom():
        raise RuntimeError("gate down")

    monkeypatch.setattr(event_gate, "event_driven_enabled", _boom)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: False)
    with patch.object(ad, "_generate_absence_label", return_value="stille") as mock_gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)
    mock_gen.assert_called_once()
    assert result["generated"] is True
