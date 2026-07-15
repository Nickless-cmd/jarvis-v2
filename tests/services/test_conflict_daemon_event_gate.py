"""Fase 6 (Lag 6): conflict daemon gated behind the shared event-gate.

Legacy (flag off) fires the phrase generation as today. Flag on consults
event_gate.should_generative_fire — skips the LLM on no signal change,
fires on real tension/pending/fragment change. event_gate is mocked here.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.conflict_daemon as cd

# snapshot that always yields a conflict_type (energy_impulse)
_SNAP = {"energy_level": "lav", "pending_proposals_count": 1}


def _reset() -> None:
    cd._cached_conflict = ""
    cd._cached_conflict_at = None
    cd._conflict_type = ""


def _install_fake_event_gate(monkeypatch, *, enabled: bool, fire: bool):
    from core.services import event_gate
    monkeypatch.setattr(event_gate, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: fire)
    return event_gate


def test_flag_off_fires_llm_as_today(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(cd, "_generate_conflict_phrase", return_value="spænding") as mock_gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAP))
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_llm(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(cd, "_generate_conflict_phrase", return_value="spænding") as mock_gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAP))
    mock_gen.assert_not_called()
    assert result == {"skipped": "no_signal_change"}


def test_flag_on_signal_changed_fires_llm(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(cd, "_generate_conflict_phrase", return_value="spænding") as mock_gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAP))
    mock_gen.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    _reset()
    from core.services import event_gate

    def _boom():
        raise RuntimeError("gate down")

    monkeypatch.setattr(event_gate, "event_driven_enabled", _boom)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: False)
    with patch.object(cd, "_generate_conflict_phrase", return_value="spænding") as mock_gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAP))
    mock_gen.assert_called_once()
    assert result["generated"] is True
