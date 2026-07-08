"""Harness Part 1: tiered output-discipline instruction."""
from core.services.prompt_contract import _output_discipline_instruction


def test_both_tiers_get_synthesis():
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "enough" in t.lower() and "synthes" in t.lower()


def test_strong_gets_conciseness_weak_does_not():
    strong = _output_discipline_instruction(strength="strong")
    weak = _output_discipline_instruction(strength="weak")
    assert "25 words" in strong and "100 words" in strong
    assert "25 words" not in weak and "100 words" not in weak


def test_self_safe_on_bad_input():
    assert isinstance(_output_discipline_instruction(strength="bogus"), str)
