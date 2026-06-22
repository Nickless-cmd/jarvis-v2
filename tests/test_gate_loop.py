"""Tests for gate_loop — graderet agentisk loop-kontrol + paritet med gammel logik."""
from __future__ import annotations

from core.services.gate_loop import loop_gate
from core.services.gate_kernel import Decision


def _old_is_last_round(rnd, mx, ce, me, ct, mt):
    return rnd == mx - 1 or ce >= me - 1 or ct >= mt - 1


def test_red_hard_stop_conditions():
    # sidste runde
    assert loop_gate({"round": 99, "max_rounds": 100}).decision is Decision.RED
    # tomme-tekst-budget
    assert loop_gate({"round": 1, "max_rounds": 100, "consecutive_empty": 2, "max_empty": 3}).decision is Decision.RED
    # tool-only-budget
    assert loop_gate({"round": 1, "max_rounds": 100, "consecutive_tool_only": 3, "max_tool_only": 4}).decision is Decision.RED


def test_yellow_soft_brake_on_tool_pause():
    v = loop_gate({"round": 1, "max_rounds": 100, "tool_pause": True})
    assert v.decision is Decision.YELLOW and v.action == "warn"


def test_green_continue():
    assert loop_gate({"round": 1, "max_rounds": 100}).decision is Decision.GREEN


def test_red_matches_old_is_last_round_parity():
    # gaten RED skal være ÆKVIVALENT med den gamle _is_last_round (ingen adfærdsændring)
    cases = [
        (99, 100, 0, 3, 0, 4), (1, 100, 0, 3, 0, 4), (1, 100, 2, 3, 0, 4),
        (1, 100, 0, 3, 3, 4), (50, 100, 1, 3, 1, 4), (98, 100, 0, 3, 0, 4),
    ]
    for (rnd, mx, ce, me, ct, mt) in cases:
        gate_red = loop_gate({"round": rnd, "max_rounds": mx, "consecutive_empty": ce,
                              "max_empty": me, "consecutive_tool_only": ct,
                              "max_tool_only": mt}).decision is Decision.RED
        assert gate_red == _old_is_last_round(rnd, mx, ce, me, ct, mt), (rnd, mx, ce, me, ct, mt)
