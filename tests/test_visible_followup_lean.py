"""Tests for the pure lean-tail transform in ``visible_followup_lean``.

Focus: the behavioral anti-lie anchor (``⚖️ Before you answer``, English after
audit #3, 2026-07-22) MUST survive the tail-strip, and the strip must fail OPEN
(return the full text unchanged) rather than ever drop the anchor.
"""

from __future__ import annotations

from core.services import visible_followup_lean as vl


_ANCHOR = (
    "⚖️ Before you answer: never claim you did something without a same-turn "
    "tool call that proves it. Do, don't promise."
)


def _tail() -> str:
    return "\n\n".join([
        "[SELF-MONITOR]\nR2 heed-rate 14.9%.",
        "[CALIBRATION]\nTemperatur: fokuseret.",
        _ANCHOR,
    ])


def test_strips_heavy_tail_but_keeps_english_anchor():
    head = "Original task: read db.py."
    text = head + "\n\n" + _tail()
    lean, changed, dropped = vl._lean_strip_user_message(text)
    assert changed is True
    assert dropped > 0
    assert head in lean
    assert _ANCHOR in lean                       # anchor survives
    assert "[SELF-MONITOR]" not in lean          # heavy marker dropped
    assert "[CALIBRATION]" not in lean


def test_anchor_prefix_is_registered():
    # The keep-list must carry the English anchor prefix (regression guard for
    # the audit #3 rename from "⚖️ FØR DU SVARER").
    assert any(p.startswith("⚖️ Before you answer") for p in vl._LEAN_KEEP_ROW_PREFIXES)


def test_no_heavy_marker_is_noop():
    text = "Just a plain message, no heavy tail."
    lean, changed, dropped = vl._lean_strip_user_message(text)
    assert changed is False
    assert dropped == 0
    assert lean == text


def test_fail_open_when_anchor_would_be_lost():
    # Anchor glued to a heavy block WITHOUT a double-newline: the strip can't
    # isolate it, so the guarantee must fail open to the full text.
    text = "task\n\n[SELF-MONITOR]\nnoise " + _ANCHOR  # anchor not its own block
    lean, changed, dropped = vl._lean_strip_user_message(text)
    assert changed is False
    assert lean == text                          # full text preserved


def test_empty_is_noop():
    lean, changed, dropped = vl._lean_strip_user_message("")
    assert changed is False
    assert dropped == 0
    assert lean == ""
