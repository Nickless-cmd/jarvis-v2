"""Fase 2 Lag 5: user_model daemon gated behind the shared event-gate.

Legacy (flag off) fires the LLM generation as today. Flag on consults
event_gate.should_generative_fire — skips the LLM when the user-interaction
signal (message/question activity) hasn't moved, fires on real change.

Robust patch pattern: patch the ÆGTE event_gate module attributes via
monkeypatch.setattr / patch.object — NEVER sys.modules injection.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import core.services.user_model_daemon as um

_MESSAGES = ["Hej, hvordan går det?", "Kan du hjælpe mig med noget?"]


def _reset() -> None:
    um._last_tick_at = None
    um._last_generated_at = None
    um._user_model = {}
    um._model_summary = ""


def _install_gate(monkeypatch, *, enabled: bool, fire: bool) -> MagicMock:
    from core.services import event_gate

    gate = MagicMock(return_value=fire)
    monkeypatch.setattr(event_gate, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(event_gate, "should_generative_fire", gate)
    return gate


def test_flag_off_fires_llm_as_today(isolated_runtime, monkeypatch):
    """Flag OFF → legacy: LLM generation fires, gate never consulted."""
    _reset()
    gate = _install_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(um, "_generate_model_summary", return_value="Brugeren er fokuseret.") as mock_gen:
        with patch.object(um, "_store_model"):
            result = um.tick_user_model_daemon(list(_MESSAGES))
    mock_gen.assert_called_once()
    gate.assert_not_called()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_llm(isolated_runtime, monkeypatch):
    """Flag ON + should_generative_fire False → skip LLM, cheap no-op."""
    _reset()
    _install_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(um, "_generate_model_summary", return_value="Brugeren er fokuseret.") as mock_gen:
        with patch.object(um, "_store_model"):
            result = um.tick_user_model_daemon(list(_MESSAGES))
    mock_gen.assert_not_called()
    assert result == {"skipped": "no_signal_change"}


def test_flag_on_signal_changed_fires_llm(isolated_runtime, monkeypatch):
    """Flag ON + should_generative_fire True → LLM fires."""
    _reset()
    _install_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(um, "_generate_model_summary", return_value="Brugeren er fokuseret.") as mock_gen:
        with patch.object(um, "_store_model"):
            result = um.tick_user_model_daemon(list(_MESSAGES))
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    """event_gate raising → fail-open: the daemon still fires the LLM."""
    _reset()
    from core.services import event_gate

    def _boom():
        raise RuntimeError("gate down")

    monkeypatch.setattr(event_gate, "event_driven_enabled", _boom)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: False)
    with patch.object(um, "_generate_model_summary", return_value="Brugeren er fokuseret.") as mock_gen:
        with patch.object(um, "_store_model"):
            result = um.tick_user_model_daemon(list(_MESSAGES))
    mock_gen.assert_called_once()
    assert result["generated"] is True
