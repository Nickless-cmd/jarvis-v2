"""Tests for session-milepæle (rail-kapitler) — Bjørn 2026-06-23."""
from __future__ import annotations

from core.services import session_milestones as sm


def test_per_turn_for_short_session(monkeypatch):
    turns = [{"id": f"m{i}", "text": f"besked {i}"} for i in range(4)]
    monkeypatch.setattr(sm, "_user_turns", lambda sid: turns)
    out = sm.get_session_milestones("s1")
    assert len(out) == 4
    assert out[0] == {"anchor_id": "m0", "title": "besked 0"}


def test_empty_session_returns_empty(monkeypatch):
    monkeypatch.setattr(sm, "_user_turns", lambda sid: [])
    assert sm.get_session_milestones("s1") == []


def test_short_title_truncates():
    assert sm._short_title("x" * 100, n=10).endswith("…")
    assert sm._short_title("kort") == "kort"


def test_llm_segment_parses_and_maps(monkeypatch):
    turns = [{"id": f"m{i}", "text": f"emne {i}"} for i in range(10)]
    monkeypatch.setattr(
        "core.context.compact_llm.call_compact_llm",
        lambda prompt, max_tokens=400: 'her: [{"start": 0, "title": "Opstart"}, {"start": 5, "title": "Anden del"}]',
    )
    out = sm._llm_segment(turns)
    assert out == [
        {"anchor_id": "m0", "title": "Opstart"},
        {"anchor_id": "m5", "title": "Anden del"},
    ]


def test_llm_segment_falls_back_on_garbage(monkeypatch):
    turns = [{"id": f"m{i}", "text": f"emne {i}"} for i in range(10)]
    monkeypatch.setattr(
        "core.context.compact_llm.call_compact_llm",
        lambda prompt, max_tokens=400: "ingen json her",
    )
    assert sm._llm_segment(turns) is None


def test_generate_uses_per_turn_when_llm_fails(monkeypatch):
    turns = [{"id": f"m{i}", "text": f"emne {i}"} for i in range(10)]
    monkeypatch.setattr(sm, "_llm_segment", lambda t: None)
    out = sm._generate(turns)
    assert len(out) == 10 and out[0]["anchor_id"] == "m0"


def test_invalid_indexes_skipped(monkeypatch):
    turns = [{"id": f"m{i}", "text": f"emne {i}"} for i in range(10)]
    monkeypatch.setattr(
        "core.context.compact_llm.call_compact_llm",
        lambda prompt, max_tokens=400: '[{"start": 99, "title": "uden for"}, {"start": 3, "title": "gyldig"}]',
    )
    out = sm._llm_segment(turns)
    assert out == [{"anchor_id": "m3", "title": "gyldig"}]
