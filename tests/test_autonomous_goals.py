"""Unit tests for autonomous_goals."""
from __future__ import annotations

from unittest.mock import patch

import core.services.autonomous_goals as ag


def setup_function(_fn):
    # Reset state by patching load to empty dict for each test
    pass


def test_create_goal_basic(tmp_path, monkeypatch):
    state: dict = {}
    monkeypatch.setattr(ag, "_load", lambda: state.copy())
    monkeypatch.setattr(ag, "_save", lambda d: state.update({k: v for k, v in d.items() if v}))
    state.clear()
    result = ag.create_goal(title="Lær det nye memory-system", priority="high")
    assert result["status"] == "ok"
    assert result["goal"]["title"] == "Lær det nye memory-system"
    assert result["goal"]["priority"] == "high"
    assert result["goal"]["status"] == "pending"


def test_create_goal_requires_title(monkeypatch):
    monkeypatch.setattr(ag, "_load", dict)
    monkeypatch.setattr(ag, "_save", lambda d: None)
    result = ag.create_goal(title="")
    assert result["status"] == "error"


def test_create_with_parent_links(monkeypatch):
    state: dict = {}
    def fake_load(): return state.copy()
    def fake_save(d): state.clear(); state.update(d)
    monkeypatch.setattr(ag, "_load", fake_load)
    monkeypatch.setattr(ag, "_save", fake_save)
    parent = ag.create_goal(title="Parent goal")
    parent_id = parent["goal"]["goal_id"]
    child = ag.create_goal(title="Child goal", parent_id=parent_id)
    assert child["goal"]["parent_id"] == parent_id
    assert child["goal"]["goal_id"] in state[parent_id]["sub_goal_ids"]


def test_update_status(monkeypatch):
    state: dict = {}
    def fake_load(): return state.copy()
    def fake_save(d): state.clear(); state.update(d)
    monkeypatch.setattr(ag, "_load", fake_load)
    monkeypatch.setattr(ag, "_save", fake_save)
    g = ag.create_goal(title="x")
    gid = g["goal"]["goal_id"]
    result = ag.update_goal_status(gid, "active")
    assert result["status"] == "ok"
    assert state[gid]["status"] == "active"
    result = ag.update_goal_status(gid, "achieved")
    assert state[gid]["status"] == "achieved"
    assert state[gid]["achieved_at"] is not None


def test_invalid_status_rejected(monkeypatch):
    state: dict = {"x": {"goal_id": "x"}}
    monkeypatch.setattr(ag, "_load", lambda: state.copy())
    monkeypatch.setattr(ag, "_save", lambda d: None)
    result = ag.update_goal_status("x", "bogus")
    assert result["status"] == "error"


def test_list_goals_filters(monkeypatch):
    state: dict = {
        "g1": {"goal_id": "g1", "status": "active", "priority": "high", "parent_id": None, "updated_at": "2026-04-26"},
        "g2": {"goal_id": "g2", "status": "pending", "priority": "low", "parent_id": None, "updated_at": "2026-04-25"},
        "g3": {"goal_id": "g3", "status": "active", "priority": "low", "parent_id": "g1", "updated_at": "2026-04-26"},
    }
    monkeypatch.setattr(ag, "_load", lambda: dict(state))
    active = ag.list_goals(status="active")
    assert len(active) == 2
    high = ag.list_goals(priority="high")
    assert len(high) == 1
    top = ag.list_goals(parent_id=None)  # top-level only
    assert len(top) == 2  # g1 and g2


def test_section_returns_none_when_no_active(monkeypatch):
    monkeypatch.setattr(ag, "_load", lambda: {})
    assert ag.goals_prompt_section() is None


def test_section_lists_high_priority_first(monkeypatch):
    state = {
        "g1": {"goal_id": "g1", "status": "active", "priority": "low", "title": "Low one", "parent_id": None, "updated_at": "2026-04-26"},
        "g2": {"goal_id": "g2", "status": "active", "priority": "critical", "title": "Critical thing", "parent_id": None, "updated_at": "2026-04-26"},
    }
    monkeypatch.setattr(ag, "_load", lambda: dict(state))
    section = ag.goals_prompt_section()
    assert section is not None
    assert "Critical thing" in section
    # low one filtered when high present
    assert "Low one" not in section


def test_decompose_parses_numbered_list(monkeypatch):
    state: dict = {}
    def fake_load(): return state.copy()
    def fake_save(d): state.clear(); state.update(d)
    monkeypatch.setattr(ag, "_load", fake_load)
    monkeypatch.setattr(ag, "_save", fake_save)
    parent = ag.create_goal(title="Build memory framework")
    pid = parent["goal"]["goal_id"]
    fake_response = (
        "1. Design SQLite schema for embeddings\n"
        "2. Implement embedding generation pipeline\n"
        "3. Add semantic recall to recall_memories tool\n"
        "4. Migrate existing memory entries\n"
    )
    with patch("core.services.daemon_llm.daemon_llm_call", return_value=fake_response):
        result = ag.decompose_goal(pid)
    assert result["status"] == "ok"
    assert result["sub_goals_created"] == 4
    sub_titles = [s["title"] for s in result["sub_goals"]]
    assert any("SQLite" in t for t in sub_titles)
