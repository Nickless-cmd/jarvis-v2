"""Unit tests for proactive_context_governor."""
from __future__ import annotations

from unittest.mock import patch

import core.services.proactive_context_governor as pcg


def test_should_auto_compact_below_threshold():
    with patch("core.services.context_window_manager.estimate_pressure",
               return_value={"estimated_tokens": 4000, "target": 8000}):
        result = pcg.should_auto_compact()
    assert result["should_compact"] is False


def test_should_auto_compact_above_threshold():
    pcg._LAST_AUTO_COMPACT_TS = 0  # reset
    with patch("core.services.context_window_manager.estimate_pressure",
               return_value={"estimated_tokens": 6000, "target": 8000}):
        result = pcg.should_auto_compact()
    assert result["should_compact"] is True
    assert result["percent"] >= 70


def test_should_auto_compact_respects_cooldown():
    import time
    pcg._LAST_AUTO_COMPACT_TS = time.time()  # just compacted
    with patch("core.services.context_window_manager.estimate_pressure",
               return_value={"estimated_tokens": 7000, "target": 8000}):
        result = pcg.should_auto_compact()
    assert result["should_compact"] is False
    assert "cooldown" in result["reason"]


def test_auto_compact_skips_when_not_needed():
    pcg._LAST_AUTO_COMPACT_TS = 0
    with patch("core.services.context_window_manager.estimate_pressure",
               return_value={"estimated_tokens": 1000, "target": 8000}):
        result = pcg.auto_compact_if_needed()
    assert result["compacted"] is False


def test_build_subagent_context_includes_goal():
    with patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.memory_recall_engine.unified_recall",
               return_value={"results": []}):
        result = pcg.build_subagent_context_slice(role="researcher", goal="find pakkenavn")
    assert "find pakkenavn" in result["compact_text"]
    assert "Din opgave" in result["compact_text"]


def test_build_subagent_context_includes_relevant_memories():
    with patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.memory_recall_engine.unified_recall", return_value={
             "results": [{"source": "workspace", "text": "tidligere note om dette"}],
         }):
        result = pcg.build_subagent_context_slice(role="critic", goal="x")
    assert "tidligere note" in result["compact_text"]
    assert len(result["relevant_memories"]) == 1


def test_build_subagent_context_includes_active_goals():
    with patch("core.services.autonomous_goals.list_goals", return_value=[
        {"title": "Lær memory-arkitektur", "priority": "high"},
    ]), patch("core.services.memory_recall_engine.unified_recall", return_value={"results": []}):
        result = pcg.build_subagent_context_slice(role="planner", goal="x")
    assert "Lær memory-arkitektur" in result["compact_text"]


def test_build_subagent_context_truncates_to_max_chars():
    long_goal = "x" * 10000
    with patch("core.services.autonomous_goals.list_goals", return_value=[]), \
         patch("core.services.memory_recall_engine.unified_recall", return_value={"results": []}):
        result = pcg.build_subagent_context_slice(role="r", goal=long_goal, max_chars=500)
    assert len(result["compact_text"]) <= 600  # truncated + slack for marker


def test_save_and_recall_context_version(monkeypatch):
    state: list = []
    monkeypatch.setattr(pcg, "_load_versions", lambda: list(state))
    monkeypatch.setattr(pcg, "_save_versions", lambda v: state.clear() or state.extend(v))
    with patch("core.services.chat_sessions.list_chat_sessions", return_value=[]):
        vid = pcg.save_context_version(reason="test")
    assert vid.startswith("ctx-")
    recalled = pcg.recall_context_version(vid)
    assert recalled is not None
    assert recalled["reason"] == "test"


def test_list_context_versions_returns_recent_first(monkeypatch):
    state = [
        {"version_id": "ctx-old", "reason": "first", "captured_at": "2026-04-26T00:00:00Z"},
        {"version_id": "ctx-new", "reason": "second", "captured_at": "2026-04-27T00:00:00Z"},
    ]
    monkeypatch.setattr(pcg, "_load_versions", lambda: list(state))
    versions = pcg.list_context_versions()
    assert versions[0]["version_id"] == "ctx-new"
