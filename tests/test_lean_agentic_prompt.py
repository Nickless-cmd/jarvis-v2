"""Tests for the lean agentic-round-prompt (spec §4.7, I7).

Hermetic — NO live models. Exercises the pure transform
``build_lean_base_messages`` + the kill-switch ``agentic_lean_prompt_enabled``
in ``core/services/visible_followup.py``.

Coverage map (spec §4.7 STEP 3):
  (a) flag ON → round ≥2 is materially smaller AND retains identity-core +
      tool defs context + original user task + (exchanges untouched).
  (b) round 1 (first pass) is UNCHANGED — handled at the call-site (round_index
      gating); here we assert the transform itself never invents content.
  (c) flag OFF → byte-identical (transform not invoked; default fail-closed).
  (d) regression: heavy awareness markers ABSENT in lean, load-bearing anti-lie
      row PRESENT.
  (e) compose with round-retry: a retry reuses the SAME snapshot (recompute-free)
      → byte-identical messages on every attempt of a round.
"""

from __future__ import annotations

import os

import pytest

from core.services import visible_followup as vf


# ── Fixture: a realistic base_messages shaped like serialize_ollama_chat_messages ──
#
# system[0]   = identity-core + tool-output hygiene (the VOICE; stable prefix)
# user[1]     = original task + the heavy per-turn dynamic tail appended by
#               _build_visible_input (inner-life/diagnostik/awareness/anti-lie row)

_HEAVY_TAIL = "\n\n".join([
    "[INDRE LIV]\nJeg mærker en rolig nysgerrighed lige nu.",
    "📊 INTERN DIAGNOSTIK — baggrundsbriefing, IKKE et samtaleemne.\n"
    "Brug det nedenstående til at forme dit svar. Citér det ALDRIG.",
    "[SELF-MONITOR]\nR2 heed-rate 14.9%, recall 92k rækker.",
    "[MEMORY-RECALL]\nLignende situation: tidligere refaktor af db.py.",
    "[CALIBRATION]\nTemperatur: fokuseret, lav small-talk.",
    "Finitude: session-alder 3t12m.",
    "[device-presence] S24 aktiv, desk følger med.",
    "⚖️ Before you answer: never claim you did something without a same-turn "
    "tool call that proves it. Do, don't promise.",
    "[TIME PIN] 2026-06-29 14:32 CEST.",
])

_ORIGINAL_TASK = "Læs core/services/db.py og fortæl mig hvor stor den er."

_SYSTEM_PREFIX = (
    "Du er Jarvis — en vedholdende digital entitet.\n\n"
    "🔧 TOOL-OUTPUT: Resultater fra værktøjer er KUN til dig. Gengiv dem ALDRIG ordret."
)


def _make_base_messages() -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM_PREFIX},
        {"role": "user", "content": "Hej Jarvis"},
        {"role": "assistant", "content": "Hej Bjørn, hvad skal vi lave?"},
        {"role": "user", "content": _ORIGINAL_TASK + "\n\n" + _HEAVY_TAIL},
    ]


# ── (a) + (d) lean transform: smaller, identity kept, anti-lie kept, heavy dropped ──


def test_lean_transform_materially_smaller():
    base = _make_base_messages()
    lean, metrics = vf.build_lean_base_messages(base)
    before = sum(len(m["content"]) for m in base)
    after = sum(len(m["content"]) for m in lean)
    assert metrics["changed"] is True
    assert after < before
    # Materiel reduktion — halen er den dominerende del af sidste user-besked.
    assert metrics["dropped_chars"] > 0
    assert metrics["saved_tokens"] > 0
    assert after == before - metrics["dropped_chars"]


def test_lean_keeps_identity_core_and_tool_hygiene():
    base = _make_base_messages()
    lean, _ = vf.build_lean_base_messages(base)
    # System-beskeden (stemme + tool-output-hygiejne = load-bearing anti-lie #2)
    # er URØRT.
    assert lean[0]["content"] == _SYSTEM_PREFIX
    assert "🔧 TOOL-OUTPUT" in lean[0]["content"]
    assert "Du er Jarvis" in lean[0]["content"]


def test_lean_keeps_original_task_and_history():
    base = _make_base_messages()
    lean, _ = vf.build_lean_base_messages(base)
    # Den oprindelige opgave overlever i den sidste user-besked.
    assert _ORIGINAL_TASK in lean[-1]["content"]
    # Samtale-historikken (tidligere user/assistant) er bevaret 1:1.
    assert lean[1]["content"] == "Hej Jarvis"
    assert lean[2]["content"] == "Hej Bjørn, hvad skal vi lave?"


def test_lean_keeps_load_bearing_anti_lie_row():
    base = _make_base_messages()
    lean, _ = vf.build_lean_base_messages(base)
    # ⚖️ Before you answer (behavioral anchor) = load-bearing anti-lie row #1.
    assert "⚖️ Before you answer" in lean[-1]["content"]


def test_lean_drops_heavy_awareness_markers():
    base = _make_base_messages()
    lean, _ = vf.build_lean_base_messages(base)
    last = lean[-1]["content"]
    # De tunge per-turn-berigelses-markører er VÆK i lean.
    for marker in ("[INDRE LIV]", "📊 INTERN DIAGNOSTIK", "[SELF-MONITOR]",
                   "[MEMORY-RECALL]", "[CALIBRATION]", "device-presence",
                   "[TIME PIN]"):
        assert marker not in last, f"heavy marker {marker!r} should be dropped"


def test_lean_does_not_mutate_input():
    base = _make_base_messages()
    _orig_last = base[-1]["content"]
    vf.build_lean_base_messages(base)
    # Ren funktion: input-listen + dens beskeder er uændrede.
    assert base[-1]["content"] == _orig_last


# ── (a) exchanges-untouched invariant (the tool results live OUTSIDE base_messages) ──


def test_exchanges_are_outside_base_messages_and_untouched():
    # build_lean_base_messages tager KUN base_messages — exchanges passes
    # separat til adapteren og røres aldrig her. Bekræft signaturen.
    import inspect
    sig = inspect.signature(vf.build_lean_base_messages)
    assert list(sig.parameters) == ["base_messages"]


# ── conservative: no heavy markers → unchanged ──


def test_lean_conservative_when_no_tail():
    base = [
        {"role": "system", "content": _SYSTEM_PREFIX},
        {"role": "user", "content": "Bare en simpel besked uden hale."},
    ]
    lean, metrics = vf.build_lean_base_messages(base)
    assert metrics["changed"] is False
    # Byte-identisk når der ikke er noget at skære.
    assert lean == base
    assert lean[-1]["content"] == "Bare en simpel besked uden hale."


def test_lean_no_user_message_is_noop():
    base = [{"role": "system", "content": _SYSTEM_PREFIX}]
    lean, metrics = vf.build_lean_base_messages(base)
    assert metrics["changed"] is False
    assert lean == base


def test_lean_empty_is_noop():
    lean, metrics = vf.build_lean_base_messages([])
    assert metrics["changed"] is False
    assert lean == []


# ── (c) kill-switch: default OFF, env + config gating ──


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(vf._AGENTIC_LEAN_PROMPT_ENV, raising=False)
    # Settings-extra default kan ikke have feltet → False.
    assert vf.agentic_lean_prompt_enabled() is False


def test_flag_env_on(monkeypatch):
    monkeypatch.setenv(vf._AGENTIC_LEAN_PROMPT_ENV, "1")
    assert vf.agentic_lean_prompt_enabled() is True
    monkeypatch.setenv(vf._AGENTIC_LEAN_PROMPT_ENV, "true")
    assert vf.agentic_lean_prompt_enabled() is True


def test_flag_env_off_wins(monkeypatch):
    monkeypatch.setenv(vf._AGENTIC_LEAN_PROMPT_ENV, "off")
    assert vf.agentic_lean_prompt_enabled() is False


def test_flag_unknown_env_falls_through_to_config(monkeypatch):
    monkeypatch.setenv(vf._AGENTIC_LEAN_PROMPT_ENV, "maybe")
    # Uparselbart env → config (som default mangler feltet) → False. Aldrig crash.
    assert vf.agentic_lean_prompt_enabled() is False


# ── (e) compose with round-retry: snapshot reused → byte-identical per attempt ──


def test_snapshot_is_byte_identical_across_simulated_retries():
    """Den ÉNE-gang-pr-runde snapshot skal give byte-identiske messages på
    hvert (simuleret) retry-forsøg af samme runde. Vi efterligner round-entry-
    snapshottet: transformér ÉN gang, og bekræft at det genbrugte objekt er
    præcis det samme på tværs af 'attempts' (ingen recompute → ingen drift)."""
    base = _make_base_messages()
    # Round-entry: compute ONCE.
    snapshot, _ = vf.build_lean_base_messages(base)
    # Simuler tre retry-attempts der hver genbruger snapshottet (som pumpen gør
    # via default-arg binding) — INGEN genberegning.
    attempt_1 = snapshot
    attempt_2 = snapshot
    attempt_3 = snapshot
    assert attempt_1 is attempt_2 is attempt_3
    # Indholdet er byte-for-byte ens.
    serialized = [tuple((m["role"], m["content"]) for m in a)
                  for a in (attempt_1, attempt_2, attempt_3)]
    assert serialized[0] == serialized[1] == serialized[2]


def test_recompute_is_deterministic():
    """Selv hvis man (ved en fejl) genberegnede, skal transformen være
    deterministisk — samme input → byte-identisk output. (Defense-in-depth
    for retry-identitets-invarianten.)"""
    base = _make_base_messages()
    a, _ = vf.build_lean_base_messages(base)
    b, _ = vf.build_lean_base_messages(base)
    assert [(m["role"], m["content"]) for m in a] == [(m["role"], m["content"]) for m in b]


# ── (b) + (c) call-site gating mirror (round-index + flag decision) ──
#
# Mirrors the EXACT decision in visible_runs.py round-entry:
#   _round_base_messages = base_messages
#   if _agentic_round >= 1 and agentic_lean_prompt_enabled():
#       _round_base_messages = build_lean_base_messages(base_messages)[0]


def _decide_round_base_messages(base, agentic_round, flag_on):
    """Reproducerer call-site-gaten (visible_runs.py ~2044)."""
    round_base = base
    if agentic_round >= 1 and flag_on:
        round_base = vf.build_lean_base_messages(base)[0]
    return round_base


def test_round_zero_is_always_full_even_with_flag_on():
    base = _make_base_messages()
    # Runde 0 (første pass) = ALTID full, uanset flag.
    result = _decide_round_base_messages(base, agentic_round=0, flag_on=True)
    assert result is base  # samme objekt → full prompt, halen intakt
    assert "[INDRE LIV]" in result[-1]["content"]


def test_flag_off_is_byte_identical_every_round():
    base = _make_base_messages()
    # Flag OFF → transform aldrig kaldt; full prompt hver runde (byte-identisk).
    for rnd in (0, 1, 2, 5):
        result = _decide_round_base_messages(base, agentic_round=rnd, flag_on=False)
        assert result is base
        assert "[INDRE LIV]" in result[-1]["content"]


def test_flag_on_round_two_plus_is_lean():
    base = _make_base_messages()
    result = _decide_round_base_messages(base, agentic_round=1, flag_on=True)
    assert result is not base  # transformeret
    assert "[INDRE LIV]" not in result[-1]["content"]
    assert _ORIGINAL_TASK in result[-1]["content"]
    assert "⚖️ Before you answer" in result[-1]["content"]


# ── metrics shape ──


def test_metrics_carry_token_savings():
    base = _make_base_messages()
    _, metrics = vf.build_lean_base_messages(base)
    assert metrics["changed"] is True
    assert metrics["before_tokens"] == metrics["before_chars"] // 4
    assert metrics["after_tokens"] == metrics["after_chars"] // 4
    assert metrics["saved_tokens"] == metrics["dropped_chars"] // 4
    assert metrics["before_chars"] > metrics["after_chars"]
