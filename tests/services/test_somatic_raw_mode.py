"""Fase 2 / Lag 1 — somatic raw-signal-mode.

Bag flag `raw_signal_mode` (runtime-state, default OFF) emitter somatic-daemonen
de RÅ metrics som frase i stedet for at kalde narrations-LLM'en (_generate_phrase).
Flippes flaget, skifter kun STRENGEN fra LLM-label til rå tal — samme output-felt,
ingen consumer brækker.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import patch

import core.services.somatic_daemon as sd


def _reset():
    sd._cached_phrase = ""
    sd._last_cpu_pct = 0.0
    sd._last_latency_ms = 0.0
    sd._last_energy_level = ""
    sd._heartbeat_count_since_gen = 0
    sd._latency_samples.clear()
    sd._active_requests = 0


_SNAPSHOT = {
    "cpu_pct": 8.0,
    "ram_used_gb": 10.7,
    "ram_total_gb": 32.0,
    "latency_ms": 100.0,
    "active_requests": 0,
    "energy_level": "medium",
    "clock_phase": "formiddag",
}


def test_flag_defaults_off(isolated_runtime):
    _reset()
    assert sd.raw_signal_mode_enabled() is False


def test_flag_self_safe_returns_false_on_error():
    _reset()
    with patch(
        "core.runtime.db_core.get_runtime_state_value",
        side_effect=RuntimeError("boom"),
    ):
        assert sd.raw_signal_mode_enabled() is False


def test_flag_off_calls_generate_phrase(isolated_runtime):
    _reset()
    sd._last_energy_level = "høj"  # force generation via energy change
    with patch.object(sd, "_collect_snapshot", return_value=dict(_SNAPSHOT)):
        with patch.object(sd, "_generate_phrase", return_value="stabil baseline") as gen:
            with patch.object(sd, "_store_phrase"):
                result = sd.tick_somatic_daemon(energy_level="medium")
    gen.assert_called_once()
    assert result["generated"] is True
    assert result["phrase"] == "stabil baseline"


def test_flag_on_skips_generate_phrase_and_emits_raw_metrics(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    sd._last_energy_level = "høj"  # force generation via energy change
    with patch.object(sd, "_collect_snapshot", return_value=dict(_SNAPSHOT)):
        with patch("os.getloadavg", return_value=(0.0, 0.1, 0.2)):
            with patch(
                "core.services.hardware_body.get_hardware_state",
                return_value={"cpu_temp_c": 56.0},
            ):
                with patch.object(sd, "_generate_phrase") as gen:
                    with patch.object(sd, "_store_phrase"):
                        result = sd.tick_somatic_daemon(energy_level="medium")

    gen.assert_not_called()
    assert result["generated"] is True
    phrase = result["phrase"]
    # Rå tal, ingen LLM-label.
    assert "cpu 8%" in phrase
    assert "56°C" in phrase
    assert "21.3GB" in phrase  # 32.0 - 10.7 fri
    assert "load 0.0" in phrase


def test_flag_on_omits_temp_gracefully_when_unavailable(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    sd._last_energy_level = "høj"
    with patch.object(sd, "_collect_snapshot", return_value=dict(_SNAPSHOT)):
        with patch("os.getloadavg", return_value=(0.0, 0.1, 0.2)):
            with patch(
                "core.services.hardware_body.get_hardware_state",
                return_value={},  # temp unavailable
            ):
                with patch.object(sd, "_generate_phrase") as gen:
                    with patch.object(sd, "_store_phrase"):
                        result = sd.tick_somatic_daemon(energy_level="medium")

    gen.assert_not_called()
    assert result["generated"] is True
    phrase = result["phrase"]
    assert "°C" not in phrase  # gracefully omitted, no crash
    assert "cpu 8%" in phrase
