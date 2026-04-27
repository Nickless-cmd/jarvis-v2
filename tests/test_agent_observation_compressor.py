"""Unit tests for agent_observation_compressor."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.agent_observation_compressor as aoc


def test_compress_skips_empty_output(monkeypatch):
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(aoc, "save_json", lambda *a, **k: None)
    result = aoc.compress_agent_run(agent_id="x", role="r", goal="g", raw_output="")
    assert result["status"] == "skipped"


def test_compress_calls_llm_and_persists(monkeypatch):
    state: list = []
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(aoc, "save_json", lambda k, v: state.clear() or state.extend(v))
    fake_summary = "- Found bug in line 42\n- Recommend rollback\n- Tested 3 cases"
    with patch("core.services.daemon_llm.daemon_llm_call", return_value=fake_summary):
        result = aoc.compress_agent_run(
            agent_id="agent-1", role="researcher",
            goal="find the bug",
            raw_output="A" * 1500,
        )
    assert result["status"] == "ok"
    obs = result["observation"]
    assert obs["raw_chars"] == 1500
    assert obs["compression_ratio"] >= 1.0
    assert "Found bug" in obs["compressed_text"]
    assert len(state) == 1


def test_compress_skips_when_llm_says_trivial(monkeypatch):
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: [])
    monkeypatch.setattr(aoc, "save_json", lambda *a, **k: None)
    with patch("core.services.daemon_llm.daemon_llm_call",
               return_value="INGEN — output var trivielt."):
        result = aoc.compress_agent_run(
            agent_id="x", role="r", goal="g", raw_output="boring stuff",
        )
    assert result["status"] == "skipped"


def test_list_observations_filters_by_role(monkeypatch):
    now = datetime.now(UTC).isoformat()
    state = [
        {"obs_id": "o1", "role": "researcher", "recorded_at": now,
         "goal": "g1", "compression_ratio": 3.0, "compressed_chars": 100,
         "compressed_text": "a"},
        {"obs_id": "o2", "role": "critic", "recorded_at": now,
         "goal": "g2", "compression_ratio": 2.0, "compressed_chars": 80,
         "compressed_text": "b"},
    ]
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: list(state))
    out = aoc.list_agent_observations(role="researcher")
    assert len(out) == 1
    assert out[0]["role"] == "researcher"


def test_list_observations_respects_days_back(monkeypatch):
    old = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    fresh = datetime.now(UTC).isoformat()
    state = [
        {"obs_id": "old", "role": "r", "recorded_at": old, "goal": "",
         "compression_ratio": 1, "compressed_chars": 1, "compressed_text": ""},
        {"obs_id": "fresh", "role": "r", "recorded_at": fresh, "goal": "",
         "compression_ratio": 1, "compressed_chars": 1, "compressed_text": ""},
    ]
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: list(state))
    out = aoc.list_agent_observations(days_back=14)
    assert len(out) == 1
    assert out[0]["obs_id"] == "fresh"


def test_get_observation_by_id(monkeypatch):
    state = [{"obs_id": "found", "role": "r", "compressed_text": "hi"}]
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: list(state))
    assert aoc.get_agent_observation("found") is not None
    assert aoc.get_agent_observation("notfound") is None


def test_mark_stale_marks_old_records(monkeypatch):
    state: list = [
        {"obs_id": "old", "recorded_at": (datetime.now(UTC) - timedelta(days=20)).isoformat(),
         "stale": False},
        {"obs_id": "fresh", "recorded_at": datetime.now(UTC).isoformat(), "stale": False},
    ]
    monkeypatch.setattr(aoc, "load_json", lambda *a, **k: list(state))
    monkeypatch.setattr(aoc, "save_json", lambda k, v: state.clear() or state.extend(v))
    result = aoc.mark_stale_observations(days=14)
    assert result["marked"] == 1
    old_record = next(r for r in state if r["obs_id"] == "old")
    assert old_record["stale"] is True
