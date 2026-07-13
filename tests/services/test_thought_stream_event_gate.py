"""Fase 2 Lag 5: thought_stream daemon gated behind the shared event-gate.

Legacy (flag off) fires the LLM generation as today. Flag on consults
event_gate.should_generative_fire — skips the LLM on no signal change,
fires on real change. event_gate is built in parallel and mocked here.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch

import core.services.thought_stream_daemon as ts


def _reset() -> None:
    ts._last_fragment = ""
    ts._last_fragment_at = None
    ts._fragment_buffer.clear()
    ts._cached_fragment = ""


def _install_fake_event_gate(monkeypatch, *, enabled: bool, fire: bool):
    """Inject a fake core.services.event_gate so the daemon's in-function
    `from core.services import event_gate` resolves to our stub."""
    fake = types.ModuleType("core.services.event_gate")
    fake.event_driven_enabled = lambda: enabled
    fake.should_generative_fire = lambda name, signals: fire
    monkeypatch.setitem(sys.modules, "core.services.event_gate", fake)
    return fake


def test_flag_off_fires_llm_as_today(isolated_runtime, monkeypatch):
    """Flag OFF → legacy behaviour: the LLM generation fires unchanged."""
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(
                energy_level="medium", inner_voice_mode="work-steady"
            )
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_llm(isolated_runtime, monkeypatch):
    """Flag ON + should_generative_fire False → skip LLM, cheap no-op."""
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(
                energy_level="medium", inner_voice_mode="work-steady"
            )
    mock_gen.assert_not_called()
    assert result == {"skipped": "no_signal_change"}


def test_flag_on_signal_changed_fires_llm(isolated_runtime, monkeypatch):
    """Flag ON + should_generative_fire True → LLM fires."""
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(
                energy_level="medium", inner_voice_mode="work-steady"
            )
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    """event_gate raising → fail-open: the daemon still fires the LLM."""
    _reset()
    fake = types.ModuleType("core.services.event_gate")

    def _boom():
        raise RuntimeError("gate down")

    fake.event_driven_enabled = _boom
    fake.should_generative_fire = lambda name, signals: False
    monkeypatch.setitem(sys.modules, "core.services.event_gate", fake)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(energy_level="medium")
    mock_gen.assert_called_once()
    assert result["generated"] is True
