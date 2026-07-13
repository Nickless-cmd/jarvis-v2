"""Fase 2, Lag 1 — surprise raw-signal-mode bag `raw_signal_mode`-flag.

Surprise's divergens er ALLEREDE regel-beregnet (`_compute_divergence`, Counter
majority vote, ingen LLM). LLM'en (`_generate_surprise`) NARRATERER kun. Når
runtime-state-flaget `raw_signal_mode` er sandt, skal ticket udsende den RÅ
divergens og SPRINGE narrations-LLM'et over. Flag af = uændret legacy.

Flaget læses direkte via `core.runtime.db_core.get_runtime_state_value` (IKKE
en helper fra somatic_daemon — undgå cross-modul-afhængighed under parallel
build).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


def _prime_module(surprise):
    """Bring daemon-state forbi tickets tidlige guards (history + cooldown)."""
    surprise._mode_history = ["reasoning", "reasoning", "reasoning"]
    surprise._energy_history = ["høj", "høj", "høj"]
    surprise._heartbeats_since_surprise = surprise._COOLDOWN_BEATS + 1
    surprise._cached_surprise = ""


@pytest.mark.usefixtures("isolated_runtime")
def test_flag_off_calls_generate_surprise():
    import core.services.surprise_daemon as surprise
    from core.runtime.db_core import set_runtime_state_value

    _prime_module(surprise)
    set_runtime_state_value("raw_signal_mode", False)

    divergence = ["mode:reasoning→channel", "energy:høj→lav"]
    with (
        patch.object(surprise, "_compute_divergence", return_value=divergence),
        patch.object(
            surprise, "_generate_surprise", return_value="narreret sætning"
        ) as gen,
    ):
        result = surprise.tick_surprise_daemon("channel", "lav")

    gen.assert_called_once()
    assert result["generated"] is True
    assert result["surprise"] == "narreret sætning"


@pytest.mark.usefixtures("isolated_runtime")
def test_flag_on_skips_llm_and_emits_raw_divergence():
    import core.services.surprise_daemon as surprise
    from core.runtime.db_core import set_runtime_state_value

    _prime_module(surprise)
    set_runtime_state_value("raw_signal_mode", True)

    divergence = ["mode:reasoning→channel", "energy:høj→lav"]
    with (
        patch.object(surprise, "_compute_divergence", return_value=divergence),
        patch.object(surprise, "_generate_surprise") as gen,
    ):
        result = surprise.tick_surprise_daemon("channel", "lav")

    # LLM-narrationen SKAL springes over.
    gen.assert_not_called()
    # Rå divergens skal ud i samme felt som awareness konsumerer.
    assert result["generated"] is True
    raw = result["surprise"]
    assert isinstance(raw, str) and raw
    assert "divergens" in raw.lower()
    # Den rå kategoriske divergens skal være til stede (ikke narreret prosa).
    assert "reasoning" in raw and "channel" in raw
    assert "høj" in raw and "lav" in raw
