"""Tests for hollow_promise_guard — fang 'lovede handling, kaldte intet værktøj'."""
from __future__ import annotations

import core.services.hollow_promise_guard as hpg


# ── is_promise_of_action ─────────────────────────────────────────────────────────────

def test_detects_danish_promises():
    for t in [
        "Jeg kører self-review nu.",
        "Ja, du har ret. Jeg gør det nu.",
        "I gang — jeg fortsætter auditen.",
        "Jeg fortsætter auditen nu. 🎯",
        "I gang — jeg fortsætter auditen og gemmer bagefter. 🎯",
        "Lad mig lige køre tools.",
        "Nu kører jeg self-review og council.",
        "Jeg starter self-review nu, så council, så commit.",
    ]:
        assert hpg.is_promise_of_action(t) is True, t


def test_detects_english_promises():
    for t in ["I'll run it now.", "Let me start the audit.", "I'm going to check that.",
              "Running it now."]:
        assert hpg.is_promise_of_action(t) is True, t


def test_ignores_normal_answers():
    for t in [
        "Root-cause er cooldown 0; jeg har committet fixet og deployet.",
        "Her er de tre spor: STITCH, PULSE, DIASTOLE.",
        "Membranen er intakt, ingen brud.",
        "",
        "   ",
    ]:
        assert hpg.is_promise_of_action(t) is False, t


def test_question_tail_is_not_a_promise():
    # afventer bruger (spørgsmål) → ikke tom løfte (respektér consent-bug-læringen)
    assert hpg.is_promise_of_action("Skal jeg køre self-review nu?") is False


# ── is_hollow_promise ────────────────────────────────────────────────────────────────

def test_hollow_when_promise_and_zero_tools():
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=0) is True


def test_not_hollow_when_a_tool_ran():
    # et værktøj KØRTE → ikke tomt (han handlede faktisk)
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=3) is False


def test_not_hollow_when_already_nudged():
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=0,
                                 nudged_already=True) is False


def test_not_hollow_on_empty_text():
    # tomt håndteres af empty-completion-vagten, ikke her
    assert hpg.is_hollow_promise("", total_tool_calls=0) is False


def test_not_hollow_on_normal_answer():
    assert hpg.is_hollow_promise("Fixet er committet og deployet.", total_tool_calls=0) is False


# ── flag ─────────────────────────────────────────────────────────────────────────────

def test_flag_default_true(monkeypatch):
    monkeypatch.delenv(hpg._ENV, raising=False)
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d: d)  # ingen override → default
    assert hpg.hollow_promise_guard_enabled() is True


def test_env_can_disable(monkeypatch):
    monkeypatch.setenv(hpg._ENV, "off")
    assert hpg.hollow_promise_guard_enabled() is False


def test_env_can_enable(monkeypatch):
    monkeypatch.setenv(hpg._ENV, "1")
    assert hpg.hollow_promise_guard_enabled() is True


def test_runtime_state_can_disable(monkeypatch):
    monkeypatch.delenv(hpg._ENV, raising=False)
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d: False)
    assert hpg.hollow_promise_guard_enabled() is False
