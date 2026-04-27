"""Unit tests for cross_agent_memory."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.cross_agent_memory as cam


def _fake_obs(role: str, goal: str, text: str, days_ago: float = 1.0, stale: bool = False):
    ts = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {
        "obs_id": f"obs-{role}-{days_ago}",
        "role": role,
        "goal": goal,
        "compressed_text": text,
        "recorded_at": ts,
        "stale": stale,
    }


def test_recall_skips_short_query():
    result = cam.cross_agent_recall(query="ab")
    assert result["count"] == 0
    assert "too short" in result["reason"]


def test_recall_returns_empty_when_no_observations():
    with patch.object(cam, "_all_observations", return_value=[]):
        result = cam.cross_agent_recall(query="memory architecture")
    assert result["count"] == 0


def test_recall_excludes_requesting_role():
    obs = [
        _fake_obs("researcher", "find memory architecture", "details about memory architecture"),
        _fake_obs("planner", "plan memory architecture", "memory architecture planning notes"),
    ]
    with patch.object(cam, "_all_observations", return_value=obs):
        result = cam.cross_agent_recall(query="memory architecture", requesting_role="researcher")
    assert all(r["role"] != "researcher" for r in result["results"])
    assert any(r["role"] == "planner" for r in result["results"])


def test_recall_excludes_stale_records():
    obs = [
        _fake_obs("planner", "g", "memory architecture details", stale=True),
        _fake_obs("critic", "g", "memory architecture review"),
    ]
    with patch.object(cam, "_all_observations", return_value=obs):
        result = cam.cross_agent_recall(query="memory architecture")
    roles = [r["role"] for r in result["results"]]
    assert "planner" not in roles
    assert "critic" in roles


def test_recall_respects_days_back():
    obs = [
        _fake_obs("planner", "g", "old memory architecture work", days_ago=30),
        _fake_obs("critic", "g", "fresh memory architecture work", days_ago=2),
    ]
    with patch.object(cam, "_all_observations", return_value=obs):
        result = cam.cross_agent_recall(query="memory architecture", days_back=14)
    roles = [r["role"] for r in result["results"]]
    assert "planner" not in roles
    assert "critic" in roles


def test_recall_min_score_filter():
    obs = [
        _fake_obs("planner", "g", "totally unrelated stuff about cats"),
    ]
    with patch.object(cam, "_all_observations", return_value=obs):
        result = cam.cross_agent_recall(query="memory architecture", min_score=0.5)
    assert result["count"] == 0


def test_recall_section_returns_none_when_no_results():
    with patch.object(cam, "cross_agent_recall", return_value={"results": [], "count": 0}):
        assert cam.cross_agent_recall_section("researcher", "x") is None


def test_recall_section_formats_results():
    with patch.object(cam, "cross_agent_recall", return_value={
        "results": [
            {"role": "planner", "preview": "found memory note about X",
             "recorded_at": "2026-04-26T12:00:00Z"},
        ],
        "count": 1,
    }):
        section = cam.cross_agent_recall_section("researcher", "memory")
    assert section is not None
    assert "found memory note" in section
    assert "planner" in section
