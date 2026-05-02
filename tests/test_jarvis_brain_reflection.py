"""Tests for core/services/jarvis_brain_reflection.py — daily reflection slot."""
from __future__ import annotations
import pytest


def test_reflection_envelope_contains_chronicle_and_question():
    from core.services.jarvis_brain_reflection import build_reflection_envelope
    env = build_reflection_envelope(chronicle_summary="Today: did A, fixed B.")
    assert "did A, fixed B" in env
    assert "remember_this" in env
    assert "1-3 ting" in env


def test_internal_nudge_returns_text_at_or_above_threshold():
    from core.services.jarvis_brain_reflection import build_internal_nudge
    msg = build_internal_nudge(count_so_far=3)
    assert msg
    assert "3" in msg
    assert "færdig" in msg.lower()


def test_internal_nudge_empty_below_threshold():
    from core.services.jarvis_brain_reflection import build_internal_nudge
    msg = build_internal_nudge(count_so_far=2)
    assert msg == ""


def test_run_daily_reflection_skipped_when_inactive(monkeypatch):
    from core.services import jarvis_brain_reflection as r
    called = {"n": 0}

    def stub_run(summary):
        called["n"] += 1
        return 0

    monkeypatch.setattr(r, "_run_reflection_turn", stub_run)
    monkeypatch.setattr(r, "_was_active_today", lambda: False)
    r.run_daily_reflection_if_active()
    assert called["n"] == 0


def test_run_daily_reflection_runs_when_active(monkeypatch):
    from core.services import jarvis_brain_reflection as r
    called = {"summary": None}

    def stub_run(summary):
        called["summary"] = summary
        return 0

    monkeypatch.setattr(r, "_run_reflection_turn", stub_run)
    monkeypatch.setattr(r, "_was_active_today", lambda: True)
    monkeypatch.setattr(r, "_build_today_chronicle_summary", lambda: "Today: X")
    r.run_daily_reflection_if_active()
    assert called["summary"] == "Today: X"
