"""Fase 2 / Lag 1 — conflict raw-signal-mode.

Bag flag `raw_signal_mode` (runtime-state, default OFF) emitter conflict-daemonen
de RÅ metrics (spænding + between-par) som frase i stedet for at kalde
narrations-LLM'en (_generate_conflict_phrase). Flippes flaget, skifter kun
STRENGEN fra LLM-label til rå tal — samme output-felt/shape, ingen consumer brækker.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import patch

import core.services.conflict_daemon as cd


def _reset():
    cd._cached_conflict = ""
    cd._cached_conflict_at = None
    cd._conflict_type = ""
    cd._last_snapshot = {}


# energy_impulse: energi lav + pending > 0
_SNAPSHOT = {
    "energy_level": "lav",
    "inner_voice_mode": "",
    "pending_proposals_count": 2,
    "latest_fragment": "",
    "last_surprise": "",
    "last_surprise_at": "",
    "fragment_count": 0,
}


def test_flag_defaults_off(isolated_runtime):
    _reset()
    assert cd.raw_signal_mode_enabled() is False


def test_flag_self_safe_returns_false_on_error():
    _reset()
    with patch(
        "core.runtime.db_core.get_runtime_state_value",
        side_effect=RuntimeError("boom"),
    ):
        assert cd.raw_signal_mode_enabled() is False


def test_flag_off_calls_generate_phrase(isolated_runtime):
    _reset()
    with patch.object(
        cd, "_generate_conflict_phrase", return_value="En del af mig vil handle."
    ) as gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAPSHOT))
    gen.assert_called_once()
    assert result["generated"] is True
    assert result["conflict_type"] == "energy_impulse"
    assert result["phrase"] == "En del af mig vil handle."


def test_flag_on_skips_generate_phrase_and_emits_raw_metrics(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    with patch.object(cd, "_generate_conflict_phrase") as gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(dict(_SNAPSHOT))

    gen.assert_not_called()
    assert result["generated"] is True
    assert result["conflict_type"] == "energy_impulse"
    phrase = result["phrase"]
    # Rå tal + between-par, ingen LLM-label.
    assert phrase.startswith("spænding ")
    assert "·" in phrase
    assert "mellem" in phrase
    assert "↔" in phrase
    # between-par for energy_impulse er handling↔krop
    assert "handling" in phrase
    assert "krop" in phrase


def test_flag_on_between_pair_for_mode_thought(isolated_runtime):
    _reset()
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value("raw_signal_mode", True)
    snap = {
        "energy_level": "høj",
        "inner_voice_mode": "rest",
        "pending_proposals_count": 0,
        "latest_fragment": "en tanke",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 1,
    }
    with patch.object(cd, "_generate_conflict_phrase") as gen:
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snap)
    gen.assert_not_called()
    assert result["conflict_type"] == "mode_thought"
    assert "ro" in result["phrase"]
    assert "tanker" in result["phrase"]
