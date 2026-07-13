"""Fase 2 / Lag 1 — desire raw-signal-mode.

Bag flag `raw_signal_mode` (runtime-state, default OFF) bygger desire-daemonen
en ny appetits label fra de RÅ intensiteter (nysgerrighed/håndværk/forbindelse)
i stedet for at kalde narrations-LLM'en (_generate_appetite_label). Flippes
flaget, skifter kun label-STRENGEN fra LLM-frase til rå tal — samme output-felt/
shape (appetite-dict uændret), ingen consumer brækker.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import patch

import core.services.desire_daemon as dd


def _reset():
    dd._appetites.clear()
    dd._last_generated_at = None


_SIGNALS = {"curiosity": "transformer-arkitektur", "craft": "", "connection": ""}


def test_flag_defaults_off(isolated_runtime):
    _reset()
    assert dd.raw_signal_mode_enabled() is False


def test_flag_self_safe_returns_false_on_error():
    _reset()
    with patch(
        "core.runtime.db_core.get_runtime_state_value",
        side_effect=RuntimeError("boom"),
    ):
        assert dd.raw_signal_mode_enabled() is False


def test_flag_off_calls_generate_label(isolated_runtime):
    _reset()
    with patch.object(
        dd, "_generate_appetite_label", return_value="Forstå transformer"
    ) as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_called_once()
    assert result["generated"] is True
    spawn.assert_called_once()
    assert spawn.call_args.args[0] == "Forstå transformer"


def test_flag_on_skips_generate_label_and_emits_raw_intensities(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    with patch.object(dd, "_generate_appetite_label") as gen:
        with patch.object(dd, "_spawn_appetite") as spawn:
            result = dd.tick_desire_daemon(dict(_SIGNALS))

    gen.assert_not_called()
    assert result["generated"] is True
    label = spawn.call_args.args[0]
    # Rå intensiteter på tværs af de tre dimensioner, ingen LLM-label.
    assert "nysgerrighed" in label
    assert "håndværk" in label
    assert "forbindelse" in label
    assert "·" in label
    # den spawnende curiosity-dim bærer NEW_APPETITE_INTENSITY (0.6)
    assert "nysgerrighed 0.6" in label
    assert "håndværk 0.0" in label
    assert "forbindelse 0.0" in label


def test_flag_on_produces_persisted_appetite_with_raw_label(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    with patch.object(dd, "_generate_appetite_label") as gen:
        # ægte spawn (ingen mock) for at bevise output-shape holder
        with patch("core.services.desire_daemon.insert_private_brain_record"):
            with patch("core.services.desire_daemon.event_bus"):
                result = dd.tick_desire_daemon(dict(_SIGNALS))
    gen.assert_not_called()
    assert result["generated"] is True
    assert result["active_count"] == 1
    active = dd.get_active_appetites()
    assert len(active) == 1
    appetite = active[0]
    # Shape uændret: type/intensity/label alle til stede
    assert appetite["type"] == "curiosity-appetite"
    assert appetite["intensity"] == dd._NEW_APPETITE_INTENSITY
    assert "nysgerrighed 0.6" in appetite["label"]
