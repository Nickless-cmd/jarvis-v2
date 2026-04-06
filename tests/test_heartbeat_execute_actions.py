from __future__ import annotations

from pathlib import Path


def test_initiative_decision_executes_bounded_action(isolated_runtime, monkeypatch) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "_execute_heartbeat_internal_action",
        lambda **kwargs: {
            "status": "executed",
            "summary": "Acted on initiative.",
            "artifact": '{"initiative_id":"init-1"}',
            "blocked_reason": "",
        },
    )

    result = heartbeat_runtime._validate_heartbeat_decision(
        decision={
            "decision_type": "initiative",
            "summary": "Act on the pending initiative now.",
            "reason": "Inner pressure is clear.",
            "proposed_action": "",
            "ping_text": "",
            "execute_action": "act_on_initiative",
        },
        policy={"allow_execute": True, "allow_ping": False, "allow_propose": True},
        workspace_dir=Path("/tmp/test-workspace"),
        tick_id="heartbeat-tick:test",
    )

    assert result["blocked_reason"] == ""
    assert result["action_status"] == "executed"
    assert result["action_type"] == "act_on_initiative"
    assert result["action_summary"] == "Acted on initiative."


def test_refresh_memory_context_runs_scan_and_safe_apply(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "track_runtime_contract_candidates_for_session_review",
        lambda session_id, run_id: {
            "created": 2,
            "messages_scanned": 3,
            "session_id": "session-1",
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "auto_apply_safe_user_md_candidates",
        lambda: {"applied": 1, "items": [{"candidate_id": "user-1"}]},
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "auto_apply_safe_memory_md_candidates",
        lambda: {"applied": 2, "items": [{"candidate_id": "memory-1"}]},
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="refresh_memory_context",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    assert "applied 3 safe updates" in result["summary"]
    assert '"created": 2' in result["artifact"]


def test_initiative_queue_retries_blocked_attempts(isolated_runtime) -> None:
    import apps.api.jarvis_api.services.initiative_queue as initiative_queue

    initiative_id = initiative_queue.push_initiative(
        focus="Revisit the current repo thread",
        source="inner-voice",
        source_id="voice-1",
        priority="high",
    )

    pending = initiative_queue.get_pending_initiatives()
    assert pending
    assert pending[0]["initiative_id"] == initiative_id
    assert pending[0]["attempt_count"] == 0

    assert initiative_queue.mark_attempted(
        initiative_id,
        blocked_reason="waiting-for-clearer-grounding",
        action_summary="Need one more pass of context.",
    )

    queue_state = initiative_queue.get_initiative_queue_state()
    refreshed = next(
        item for item in queue_state["pending"] if item["initiative_id"] == initiative_id
    )
    assert refreshed["attempt_count"] == 1
    assert refreshed["blocked_reason"] == "waiting-for-clearer-grounding"
    assert refreshed["next_attempt_at"]

