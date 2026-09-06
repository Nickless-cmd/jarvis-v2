"""Tænkning i følge-runder når turen viser sig at være arbejde (5/9-2026).

`resolve_thinking_mode` klassificerer på brugerens besked alene. Det var
harmløst indtil 4/9, hvor tilstanden faktisk begyndte at nå DeepSeek. Bjørns
session 5/9 kl. 06:05: et «1» der valgte mellem to muligheder blev læst som
samtale → fast → nul ræsonnering gennem 11 runders filkirurgi.
"""
from __future__ import annotations

import types

from core.services.visible_runs import _thinking_for_round


def _run(mode: str, adaptive: bool):
    return types.SimpleNamespace(thinking_mode=mode, thinking_adaptive=adaptive)


def _exchange(tool_calls):
    return types.SimpleNamespace(tool_calls=tool_calls)


def test_a_guessed_fast_becomes_think_once_tools_are_used():
    run = _run("fast", adaptive=True)
    assert _thinking_for_round(run, []) == "fast"
    assert _thinking_for_round(run, [_exchange([])]) == "fast"
    assert _thinking_for_round(run, [_exchange([{"id": "c1"}])]) == "think"


def test_an_explicit_fast_is_never_overridden():
    """Vaelger Bjoern selv Fast, staar det ved magt hele turen."""
    run = _run("fast", adaptive=False)
    assert _thinking_for_round(run, [_exchange([{"id": "c1"}])]) == "fast"


def test_think_and_deep_are_untouched():
    for mode in ("think", "deep"):
        for adaptive in (True, False):
            run = _run(mode, adaptive=adaptive)
            assert _thinking_for_round(run, [_exchange([{"id": "c1"}])]) == mode


def test_missing_fields_do_not_raise():
    assert _thinking_for_round(types.SimpleNamespace(), None) == "think"
    assert _thinking_for_round(_run("fast", adaptive=True), None) == "fast"


def test_the_run_records_whether_the_mode_was_a_guess():
    from core.services.visible_runs import VisibleRun
    assert VisibleRun(run_id="r", lane="l", provider="p", model="m",
                      user_message="x").thinking_adaptive is False
