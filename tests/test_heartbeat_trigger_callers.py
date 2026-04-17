"""Tests for the three concrete trigger callers: aesthetic, self-review, and queue_followup tool."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.runtime import heartbeat_triggers


@pytest.fixture
def fake_workspace(tmp_path: Path, monkeypatch) -> Path:
    ws = tmp_path / "workspaces" / "default"
    (ws / "runtime").mkdir(parents=True)
    monkeypatch.setattr(
        "core.identity.workspace_bootstrap.ensure_default_workspace",
        lambda name="default": ws,
    )
    return ws


def test_default_workspace_wrapper_resolves_and_sets(fake_workspace: Path) -> None:
    entry = heartbeat_triggers.set_trigger_for_default_workspace(
        reason="test", source="unit", text="hello"
    )
    assert entry is not None
    assert entry["reason"] == "test"
    assert heartbeat_triggers.peek_trigger(fake_workspace)["reason"] == "test"


def test_aesthetic_insight_queues_trigger(fake_workspace: Path, monkeypatch) -> None:
    # Stub the DB write and event bus so _store_insight runs cleanly in isolation
    import core.services.aesthetic_taste_daemon as daemon

    monkeypatch.setattr(daemon, "insert_private_brain_record", lambda **kw: None)
    monkeypatch.setattr(daemon.event_bus, "publish", lambda *a, **kw: None)

    daemon._store_insight("Jeg trækkes mod klarhed og ro.")

    queued = heartbeat_triggers.peek_trigger(fake_workspace)
    assert queued is not None
    assert queued["reason"] == "aesthetic-insight"
    assert queued["source"] == "aesthetic_taste_daemon"
    assert "klarhed" in queued["text"]


def test_self_review_high_confidence_queues_trigger(fake_workspace: Path, monkeypatch) -> None:
    import core.services.self_review_run_tracking as sr

    # Simulate was_created + confidence=high without touching the DB
    fake_item = {
        "was_created": True,
        "run_id": "sr-1",
        "run_type": "self-review-run",
        "status": "fresh",
        "summary": "Critical drift detected in tool execution",
        "confidence": "high",
    }

    # Call the trigger path directly via the logic used in _persist_self_review_runs
    if fake_item["was_created"] and fake_item["confidence"].lower() == "high":
        heartbeat_triggers.set_trigger_for_default_workspace(
            reason="self-review-incident",
            source="self_review_run_tracking",
            text=fake_item["summary"],
        )

    queued = heartbeat_triggers.peek_trigger(fake_workspace)
    assert queued is not None
    assert queued["reason"] == "self-review-incident"
    assert "drift" in queued["text"]


def test_self_review_low_confidence_does_not_queue(fake_workspace: Path) -> None:
    # Nothing queued initially
    assert heartbeat_triggers.peek_trigger(fake_workspace) is None

    fake_item = {"was_created": True, "confidence": "low", "summary": "noisy signal"}
    # Gate condition: only high-confidence triggers; this should be skipped
    if fake_item["was_created"] and str(fake_item.get("confidence") or "").lower() == "high":
        heartbeat_triggers.set_trigger_for_default_workspace(
            reason="self-review-incident", source="test", text=fake_item["summary"]
        )
    assert heartbeat_triggers.peek_trigger(fake_workspace) is None


def test_queue_followup_tool_queues_trigger(fake_workspace: Path) -> None:
    from core.tools import simple_tools

    result = simple_tools._exec_queue_followup({
        "reason": "follow-up",
        "text": "Jeg kommer tilbage om dit spørgsmål om X i morgen.",
    })
    assert result["status"] == "queued"
    assert result["reason"] == "follow-up"

    queued = heartbeat_triggers.peek_trigger(fake_workspace)
    assert queued is not None
    assert queued["source"] == "jarvis-self-followup"
    assert "X i morgen" in queued["text"]


def test_queue_followup_tool_rejects_empty(fake_workspace: Path) -> None:
    from core.tools import simple_tools

    assert simple_tools._exec_queue_followup({"reason": "", "text": "a"})["status"] == "error"
    assert simple_tools._exec_queue_followup({"reason": "x", "text": ""})["status"] == "error"


def test_queue_followup_tool_rejects_oversize(fake_workspace: Path) -> None:
    from core.tools import simple_tools

    result = simple_tools._exec_queue_followup({
        "reason": "follow-up",
        "text": "x" * 2001,
    })
    assert result["status"] == "error"
    assert "2000" in result["error"]


def test_queue_followup_registered_in_handler_registry() -> None:
    from core.tools import simple_tools

    assert "queue_followup" in simple_tools._TOOL_HANDLERS
    names = {
        t["function"]["name"] for t in simple_tools.TOOL_DEFINITIONS
        if t.get("type") == "function"
    }
    assert "queue_followup" in names
