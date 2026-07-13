"""Fase 2 / Lag 1 — absence raw-signal-mode.

Bag flag `raw_signal_mode` (runtime-state, default OFF) emitter absence-daemonen
de RÅ fraværs-metrics (minutter siden sidst + niveau-bånd) som frase i stedet for
at kalde narrations-LLM'en (_generate_absence_label). Flippes flaget, skifter kun
STRENGEN i output-feltet `label` — samme shape, ingen consumer brækker.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import patch

import core.services.absence_daemon as ad


def _reset(last_interaction_minutes_ago: float = 47.0) -> datetime:
    now = datetime.now(UTC)
    ad._last_interaction_at = now - timedelta(minutes=last_interaction_minutes_ago)
    ad._absence_start_at = None
    ad._absence_label = ""
    ad._last_generated_at = None
    return now


def test_flag_defaults_off(isolated_runtime):
    _reset()
    assert ad.raw_signal_mode_enabled() is False


def test_flag_self_safe_returns_false_on_error():
    with patch(
        "core.runtime.db_core.get_runtime_state_value",
        side_effect=RuntimeError("boom"),
    ):
        assert ad.raw_signal_mode_enabled() is False


def test_flag_off_calls_generate_absence_label(isolated_runtime):
    now = _reset()
    with patch.object(ad, "_generate_absence_label", return_value="Det er stille her.") as gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)
    gen.assert_called_once()
    assert result["generated"] is True
    assert result["label"] == "Det er stille her."


def test_flag_on_skips_llm_and_emits_raw_metrics(isolated_runtime):
    now = _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    with patch.object(ad, "_generate_absence_label") as gen:
        with patch.object(ad, "_store_absence"):
            result = ad.tick_absence_daemon(now=now)

    gen.assert_not_called()
    assert result["generated"] is True
    phrase = result["label"]
    # Rå tal, ingen LLM-label.
    assert "fravær" in phrase
    assert "47min" in phrase
    assert "niveau" in phrase
    assert "short" in phrase  # < 8h → short band
