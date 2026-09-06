"""Hvorfor loopet stopper — de to huller fra Bjørns session 5/9 kl. 06:05.

Selve loopet er én lang generator der ikke kan instantieres i en unit-test uden
en hel model-lane. Disse tests læser kilden og hævder de to kontrakter der
faktisk gik i stykker, så de ikke kan fjernes uden at nogen opdager det.
Logikken bag dem er dækket af tests/test_tool_world_change.py.
"""
from __future__ import annotations

import inspect

from core.services import visible_runs


def _source() -> str:
    return inspect.getsource(visible_runs)


def test_a_round_that_changed_something_is_never_no_progress():
    """En skrivning efterfulgt af to afviste verifikationer blev læst som
    "modellen spinner" → tvungen afslutning midt i arbejdet."""
    src = _source()
    marker = "_no_new = bool(_round_sig) and ("
    block = src[src.index(marker): src.index(marker) + 1400]
    assert "round_changed_the_world(_a_results)" in block
    assert "_no_new = False" in block
    # Rækkefølgen betyder alt: nulstillingen skal ske EFTER _no_new er beregnet
    # og FØR den bruges til at taelle op.
    assert block.index("round_changed_the_world") < block.index("if _no_new:")


def test_hollow_promise_is_still_detected_on_the_forced_finalize_round():
    """Vagten var slaaet fra naar _is_last_round — praecis den runde hvor
    loopet har fjernet vaerktoejerne og bedt om et endeligt svar."""
    src = _source()
    idx = src.index("hollow_promise_on_forced_finalize")
    block = src[idx - 2600: idx + 400]
    assert "_is_last_round" in block and "is_hollow_promise(" in block
    # Ingen puf (der er ingen runde tilbage) — men runnet skal markeres,
    # udfaldet persisteres og svaret sige det aerligt.
    assert "_run_degenerated = True" in block
    assert "note_detected" in block
    assert "løkken tvang en" in block


def test_the_honest_note_reaches_both_the_stream_and_the_persisted_answer():
    src = _source()
    idx = src.index("løkken tvang en")
    block = src[idx: idx + 700]
    assert "_a_parts.append(_stop_note)" in block
    assert "_all_followup_parts.append(_stop_note)" in block
    assert '"delta": _stop_note' in block


def test_followup_rounds_resolve_their_own_thinking_mode():
    src = _source()
    assert "thinking_mode=_thinking_for_round(run, _followup_exchanges)" in src
    assert "thinking_mode=run.thinking_mode," in src, "foerste pas er uaendret"
