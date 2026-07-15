"""Fase 6 (Lag 6): desire daemon gated behind the shared event-gate.

Legacy (flag off) spawns a new appetite via the LLM label as today. Flag on
consults event_gate.should_generative_fire — when the appetite landscape /
incoming signal has not moved it skips the spawn (and its LLM label), fires on
real change. event_gate is mocked here.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.desire_daemon as dd

_SIGNALS = {"curiosity": "transformer-arkitektur", "craft": "", "connection": ""}


def _reset() -> None:
    dd._appetites.clear()
    dd._last_generated_at = None


def _install_fake_event_gate(monkeypatch, *, enabled: bool, fire: bool):
    from core.services import event_gate
    monkeypatch.setattr(event_gate, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: fire)
    return event_gate


def test_flag_off_spawns_via_llm_as_today(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=False, fire=False)
    with patch.object(dd, "_generate_appetite_label", return_value="Forstå transformer") as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_called_once()
    spawn.assert_called_once()
    assert result["generated"] is True


def test_flag_on_no_signal_change_skips_spawn(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=False)
    with patch.object(dd, "_generate_appetite_label", return_value="Forstå transformer") as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_not_called()
    spawn.assert_not_called()
    assert result["generated"] is False
    assert result["active_count"] == 0


def test_flag_on_signal_changed_spawns(isolated_runtime, monkeypatch):
    _reset()
    _install_fake_event_gate(monkeypatch, enabled=True, fire=True)
    with patch.object(dd, "_generate_appetite_label", return_value="Forstå transformer") as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_called_once()
    spawn.assert_called_once()
    assert result["generated"] is True


def test_event_gate_error_fails_open(isolated_runtime, monkeypatch):
    _reset()
    from core.services import event_gate

    def _boom():
        raise RuntimeError("gate down")

    monkeypatch.setattr(event_gate, "event_driven_enabled", _boom)
    monkeypatch.setattr(event_gate, "should_generative_fire", lambda name, signals: False)
    with patch.object(dd, "_generate_appetite_label", return_value="Forstå transformer") as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_called_once()
    spawn.assert_called_once()
    assert result["generated"] is True
