"""Fase 2 / Lag 1 — experienced_time raw-signal-mode.

Bag flag `raw_signal_mode` (runtime-state, default OFF) emitter experienced_time-
daemonen de RÅ metrics (ur-tid + aktivitets-tæthed) som frase i stedet for at kalde
narrations-LLM'en (_generate_felt_label). Flippes flaget, skifter kun STRENGEN i
output-feltet `felt_label` — samme shape, ingen consumer brækker.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import patch

import core.services.experienced_time_daemon as etd


def test_flag_defaults_off(isolated_runtime):
    etd.reset_experienced_time_daemon()
    assert etd.raw_signal_mode_enabled() is False


def test_flag_self_safe_returns_false_on_error():
    with patch(
        "core.runtime.db_core.get_runtime_state_value",
        side_effect=RuntimeError("boom"),
    ):
        assert etd.raw_signal_mode_enabled() is False


def test_flag_off_calls_generate_felt_label(isolated_runtime):
    etd.reset_experienced_time_daemon()
    with patch.object(etd, "_generate_felt_label", return_value="normal") as gen:
        result = etd.tick_experienced_time_daemon(
            event_count=30, new_signal_count=3, energy_level="medium"
        )
    gen.assert_called_once()
    assert result["felt_label"] == "normal"


def test_flag_on_skips_llm_and_emits_raw_metrics(isolated_runtime):
    etd.reset_experienced_time_daemon()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    with patch.object(etd, "_generate_felt_label") as gen:
        result = etd.tick_experienced_time_daemon(
            event_count=30, new_signal_count=3, energy_level="medium"
        )

    gen.assert_not_called()
    phrase = result["felt_label"]
    # Rå tal, ingen LLM-label.
    assert "ur-tid" in phrase
    assert "min" in phrase
    assert "aktivitet" in phrase
    # density_factor = 1.0 + 30/100 = 1.3 → aktivitet 0.3
    assert "0.3" in phrase
