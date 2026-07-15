"""Fase 6 (Lag 5): surprise daemon gated behind the shared event-gate.

Legacy (flag off) fires the surprise narration as today. Flag on consults
event_gate.should_generative_fire — skips the LLM when the divergence/mode/
energy signals have not moved, fires on real change. event_gate is mocked here.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.surprise_daemon as sd


def _reset() -> None:
    # Two identical priors + a diverging current mode → guaranteed divergence.
    sd._mode_history = ["rest", "rest"]
    sd._energy_history = []
    sd._heartbeats_since_surprise = 10  # > _COOLDOWN_BEATS
    sd._cached_surprise = ""
    sd._cached_surprise_at = None
    sd._pending_afterimages = []


def _install_fake_event_gate(monkeypatch, *, enabled: bool, fire: bool):
    from core.services import event_gate
    monkeypatch.setattr(event_gate, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: fire)
    return event_gate


def test_flag_off_fires_llm_as_today(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(sd, "_generate_surprise", return_value="overraskelse") as mock_gen:
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon(inner_voice_mode="reasoning", somatic_energy="medium")
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_llm(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(sd, "_generate_surprise", return_value="overraskelse") as mock_gen:
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon(inner_voice_mode="reasoning", somatic_energy="medium")
    mock_gen.assert_not_called()
    assert result["skipped"] == "no_signal_change"


def test_flag_on_signal_changed_fires_llm(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(sd, "_generate_surprise", return_value="overraskelse") as mock_gen:
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon(inner_voice_mode="reasoning", somatic_energy="medium")
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    _reset()
    from core.services import event_gate

    def _boom():
        raise RuntimeError("gate down")

    monkeypatch.setattr(event_gate, "event_driven_enabled", _boom)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: False)
    with patch.object(sd, "_generate_surprise", return_value="overraskelse") as mock_gen:
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon(inner_voice_mode="reasoning", somatic_energy="medium")
    mock_gen.assert_called_once()
    assert result["generated"] is True
