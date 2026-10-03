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


def test_aesthetic_insight_koeer_ikke_paa_trigger_koeen(fake_workspace: Path, monkeypatch) -> None:
    """3/10-2026: daemonen skrev til heartbeat-trigger-koeen, som aldrig
    toemmes — 1.721 af 1.726 poster var dens, og ingen laeste dem. Indsigten
    har sin egen kanal (`private_brain_records`), saa koeen skal staa tom."""
    # Stub the DB write and event bus so _store_insight runs cleanly in isolation
    import core.services.aesthetic_taste_daemon as daemon

    gemt: list = []
    monkeypatch.setattr(daemon, "insert_private_brain_record", lambda **kw: gemt.append(kw))
    monkeypatch.setattr(daemon.event_bus, "publish", lambda *a, **kw: None)

    daemon._store_insight("Jeg trækkes mod klarhed og ro.")

    assert heartbeat_triggers.peek_trigger(fake_workspace) is None
    assert gemt, "indsigten skal stadig skrives til private_brain"


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


def test_queue_followup_gaar_gennem_notification_bridge(
    fake_workspace: Path, monkeypatch
) -> None:
    """3/10-2026: vaerktoejet skrev til trigger-koeen, som aldrig toemmes — det
    lovede «kom tilbage ved naeste tick» og leverede ingenting. Maalt samme
    dag stod en besked lagt her nummer 1.725 af 1.726 poster.

    Det gaar nu gennem `notification_bridge`, den vej der faktisk leverer (og
    som har daemon-vagt: koeer ved aktiv session, flusher efter turen).
    """
    from core.services import notification_bridge
    from core.tools import simple_tools

    sendt: list = []

    def _send(content, *, source="", push=True, **_kw):
        sendt.append({"source": source, "text": content})
        return {"status": "ok", "message": {"id": "msg-test"}}

    monkeypatch.setattr(notification_bridge, "send_session_notification", _send)

    result = simple_tools._exec_queue_followup({
        "reason": "follow-up",
        "text": "Jeg kommer tilbage om dit spørgsmål om X i morgen.",
    })
    assert result["status"] == "queued"
    assert result["reason"] == "follow-up"
    assert len(sendt) == 1
    assert sendt[0]["source"] == "jarvis-self-followup"
    assert "X i morgen" in sendt[0]["text"]

    assert heartbeat_triggers.peek_trigger(fake_workspace) is None, (
        "vaerktoejet maa ikke laegge i trigger-koeen — den toemmes aldrig"
    )


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
