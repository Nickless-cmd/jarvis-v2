"""Tests for heartbeat trigger queue (set / peek / consume)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.runtime import heartbeat_triggers


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspaces" / "default"
    (ws / "runtime").mkdir(parents=True)
    return ws


def test_peek_empty_returns_none(workspace: Path) -> None:
    assert heartbeat_triggers.peek_trigger(workspace) is None


def test_consume_empty_returns_none(workspace: Path) -> None:
    assert heartbeat_triggers.consume_trigger(workspace) is None


def test_set_then_peek(workspace: Path) -> None:
    entry = heartbeat_triggers.set_trigger(
        workspace, reason="user-question", source="webchat", text="Hvad med X?"
    )
    assert entry["reason"] == "user-question"
    assert entry["source"] == "webchat"
    assert entry["text"] == "Hvad med X?"
    assert entry["created_at"]

    peeked = heartbeat_triggers.peek_trigger(workspace)
    assert peeked == entry


def test_consume_removes_head(workspace: Path) -> None:
    heartbeat_triggers.set_trigger(workspace, reason="a", source="s1")
    heartbeat_triggers.set_trigger(workspace, reason="b", source="s2")

    first = heartbeat_triggers.consume_trigger(workspace)
    assert first["reason"] == "a"

    remaining = heartbeat_triggers.peek_trigger(workspace)
    assert remaining["reason"] == "b"

    second = heartbeat_triggers.consume_trigger(workspace)
    assert second["reason"] == "b"

    assert heartbeat_triggers.consume_trigger(workspace) is None


def test_persistence_across_calls(workspace: Path) -> None:
    heartbeat_triggers.set_trigger(workspace, reason="project-need", source="daemon")
    path = workspace / "runtime" / "HEARTBEAT_TRIGGERS.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["reason"] == "project-need"


def test_clear_triggers(workspace: Path) -> None:
    heartbeat_triggers.set_trigger(workspace, reason="a", source="s")
    heartbeat_triggers.set_trigger(workspace, reason="b", source="s")
    removed = heartbeat_triggers.clear_triggers(workspace)
    assert removed == 2
    assert heartbeat_triggers.peek_trigger(workspace) is None


def test_corrupt_file_treated_as_empty(workspace: Path) -> None:
    path = workspace / "runtime" / "HEARTBEAT_TRIGGERS.json"
    path.write_text("not json at all", encoding="utf-8")
    assert heartbeat_triggers.peek_trigger(workspace) is None
    # set_trigger should still work — overwrites with a valid list
    heartbeat_triggers.set_trigger(workspace, reason="recover", source="test")
    assert heartbeat_triggers.peek_trigger(workspace)["reason"] == "recover"
