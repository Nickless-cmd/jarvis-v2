from __future__ import annotations

from pathlib import Path


def test_decision_engine_prefers_live_open_loop(isolated_runtime) -> None:
    from apps.api.jarvis_api.services.runtime_decision_engine import (
        RuntimeDecisionInput,
        decide_next_action,
    )

    decision = decide_next_action(
        RuntimeDecisionInput(
            cognitive_frame={"summary": {"current_mode": "watch"}},
            operational_memory={
                "open_loops": [
                    {
                        "loop_id": "open-loop:memory",
                        "title": "Carry the memory thread forward",
                        "runtime_status": "active",
                    }
                ],
                "summary": {"recent_outcome_count": 1},
            },
            loop_runtime={"items": []},
            initiative_state={"pending": []},
            visible_state={"summary": {"active": False}},
            tool_intent_state={"summary": {"pending_count": 0}},
            timestamp_iso="2026-04-12T10:00:00+00:00",
        )
    )

    assert decision.action_id == "follow_open_loop"
    assert decision.mode == "execute"
    assert decision.score > 0.8


def test_decision_engine_prefers_repo_inspection_for_repo_focused_open_loop(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.runtime_decision_engine import (
        RuntimeDecisionInput,
        decide_next_action,
    )

    decision = decide_next_action(
        RuntimeDecisionInput(
            cognitive_frame={"summary": {"current_mode": "watch"}},
            operational_memory={
                "open_loops": [
                    {
                        "loop_id": "open-loop:repo-status",
                        "title": "Inspect repo drift before next step",
                        "runtime_status": "active",
                        "canonical_key": "open-loop:repo-status",
                    }
                ],
                "summary": {"recent_outcome_count": 1},
            },
            loop_runtime={"items": []},
            initiative_state={"pending": []},
            visible_state={"summary": {"active": False}},
            tool_intent_state={"summary": {"pending_count": 0}},
            timestamp_iso="2026-04-12T10:00:00+00:00",
        )
    )

    assert decision.action_id == "inspect_repo_context"
    assert decision.mode == "execute"
    assert decision.score > 0.9


def test_decision_engine_penalizes_recent_blocked_repo_inspection(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.runtime_decision_engine import (
        RuntimeDecisionInput,
        decide_next_action,
    )

    decision = decide_next_action(
        RuntimeDecisionInput(
            cognitive_frame={"summary": {"current_mode": "watch"}},
            operational_memory={
                "open_loops": [
                    {
                        "loop_id": "open-loop:repo-status",
                        "title": "Inspect repo drift before next step",
                        "runtime_status": "active",
                        "canonical_key": "open-loop:repo-status",
                    }
                ],
                "executive_feedback_summary": {
                    "latest_action": "inspect_repo_context",
                    "latest_status": "blocked",
                    "action_stats": {
                        "inspect_repo_context": {
                            "blocked_count": 1,
                            "failed_count": 0,
                            "success_count": 0,
                        }
                    },
                },
                "summary": {"recent_outcome_count": 1},
            },
            loop_runtime={"items": []},
            initiative_state={"pending": []},
            visible_state={"summary": {"active": False}},
            tool_intent_state={"summary": {"pending_count": 0}},
            timestamp_iso="2026-04-12T10:05:00+00:00",
        )
    )

    assert decision.action_id == "follow_open_loop"
    assert "blocked feedback penalizes inspect_repo_context" in str(
        decision.considered[1]["reason"]
    )


def test_operational_memory_summarizes_recent_executive_feedback(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.runtime_action_outcome_tracking import (
        record_runtime_action_outcome,
    )
    from apps.api.jarvis_api.services.runtime_operational_memory import (
        build_operational_memory_snapshot,
    )

    record_runtime_action_outcome(
        action_id="inspect_repo_context",
        mode="execute",
        reason="Need repo truth.",
        score=0.9,
        payload={"focus": "repo drift"},
        result={"status": "blocked", "summary": "Repo command was blocked."},
    )
    record_runtime_action_outcome(
        action_id="follow_open_loop",
        mode="execute",
        reason="Carry the loop.",
        score=0.8,
        payload={"loop_id": "open-loop:memory"},
        result={"status": "executed", "summary": "Created follow-up task."},
    )

    snapshot = build_operational_memory_snapshot(limit=6)
    summary = snapshot["summary"]
    feedback_summary = snapshot["executive_feedback_summary"]

    assert summary["executive_outcome_count"] >= 2
    assert feedback_summary["latest_action"] == "follow_open_loop"
    assert feedback_summary["action_stats"]["inspect_repo_context"]["blocked_count"] == 1
    assert feedback_summary["action_stats"]["follow_open_loop"]["executed_count"] == 1


def test_executor_and_outcome_tracking_persist_visible_proposal(
    isolated_runtime,
    monkeypatch,
) -> None:
    from apps.api.jarvis_api.services.runtime_action_executor import (
        execute_runtime_action,
    )
    from apps.api.jarvis_api.services.runtime_action_outcome_tracking import (
        record_runtime_action_outcome,
        recent_runtime_action_outcomes,
    )

    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.send_session_notification",
        lambda content, source="runtime-proposal": {
            "status": "ok",
            "session_id": "chat-1",
            "source": source,
            "content": content,
        },
    )

    result = execute_runtime_action(
        action_id="propose_next_user_step",
        payload={"current_mode": "respond"},
    )
    stored = record_runtime_action_outcome(
        action_id="propose_next_user_step",
        mode="propose",
        reason="Visible lane is active.",
        score=0.4,
        payload={"current_mode": "respond"},
        result={
            "status": result.status,
            "summary": result.summary,
            "details": result.details,
            "side_effects": result.side_effects,
            "error": result.error,
        },
    )
    recent = recent_runtime_action_outcomes(limit=1)

    assert result.status == "proposed"
    assert stored["action_id"] == "propose_next_user_step"
    assert recent[0]["outcome_id"] == stored["outcome_id"]
    assert recent[0]["result_status"] == "proposed"


def test_executor_persists_internal_work_note(isolated_runtime) -> None:
    from apps.api.jarvis_api.services.runtime_action_executor import (
        execute_runtime_action,
    )
    from core.runtime.db import recent_visible_work_notes

    result = execute_runtime_action(
        action_id="write_internal_work_note",
        payload={"current_mode": "watch", "reason": "repo follow-up pressure"},
    )
    recent = recent_visible_work_notes(limit=1)

    assert result.status == "executed"
    assert result.summary == "Persisted executive work note."
    assert recent[0]["projection_source"] == "runtime-executive-note"
    assert "repo follow-up pressure" in str(recent[0]["work_preview"])


def test_executor_uses_repo_capability_and_bounded_surface(
    isolated_runtime,
    monkeypatch,
) -> None:
    from apps.api.jarvis_api.services.runtime_action_executor import (
        execute_runtime_action,
    )

    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.invoke_workspace_capability",
        lambda capability_id, **kwargs: {
            "status": "executed",
            "detail": "ok",
            "result": {"text": " M apps/api/jarvis_api/services/runtime_action_executor.py"},
        },
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.build_self_system_code_awareness_surface",
        lambda: {"host_context": {"repo_root": "/media/projects/jarvis-v2", "git_present": True}},
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.build_bounded_repo_tool_execution_surface",
        lambda intent_surface, awareness_surface=None: {
            "execution_summary": "Repo status on main: repo=dirty, changes=modified, upstream=in-sync.",
            "execution_state": "read-only-completed",
            "execution_excerpt": ["branch=main"],
        },
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.load_workspace_capabilities",
        lambda name="default": {"callable_capability_ids": ["tool:run-non-destructive-command"]},
    )

    result = execute_runtime_action(
        action_id="inspect_repo_context",
        payload={"focus": "inspect repo drift"},
    )

    assert result.status == "executed"
    assert result.details["workspace_capability_id"] == "tool:run-non-destructive-command"
    assert result.details["repo_operation"] == "inspect-repo-status"
    assert result.details["bounded_repo_surface"]["execution_state"] == "read-only-completed"


def test_executor_turns_open_loop_into_runtime_task(isolated_runtime, monkeypatch) -> None:
    from apps.api.jarvis_api.services.runtime_action_executor import (
        execute_runtime_action,
    )

    monkeypatch.setattr(
        "apps.api.jarvis_api.services.runtime_action_executor.build_runtime_open_loop_closure_proposal_surface",
        lambda limit=8: {
            "items": [
                {
                    "canonical_key": "open-loop-closure-proposal:close-now:repo-status",
                    "summary": "Close the repo-status loop with a bounded inspection follow-up.",
                    "closure_confidence": "high",
                }
            ]
        },
    )

    result = execute_runtime_action(
        action_id="follow_open_loop",
        payload={
            "loop_id": "open-loop:repo-status",
            "canonical_key": "open-loop:repo-status",
            "title": "Inspect repo drift",
            "status": "active",
        },
    )

    task = result.details["task"]
    assert result.status == "executed"
    assert task["kind"] == "open-loop-follow-up"
    assert task["origin"] == "runtime-executive"
    assert task["priority"] == "high"
    assert task["scope"] == "open-loop:repo-status"
    assert result.details["closure_proposal"]["closure_confidence"] == "high"


def test_heartbeat_tick_persists_executive_action_metadata(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "_tick_blocked_reason", lambda merged: "")
    monkeypatch.setattr(
        heartbeat_runtime,
        "_select_heartbeat_target",
        lambda: {
            "provider": "test-provider",
            "model": "test-model",
            "lane": "heartbeat",
            "model_source": "test",
            "resolution_status": "resolved",
            "fallback_used": False,
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_context",
        lambda policy, merged_state, trigger: {
            "open_loops": [],
            "due_items": [],
            "liveness": {"liveness_state": "quiet", "liveness_score": 0},
            "recent_events": [],
            "continuity_summary": "",
            "cognitive_frame": {"summary": {"current_mode": "watch"}},
            "tool_intent": {"summary": {"pending_count": 0}},
            "loop_runtime": {"items": []},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_decide_executive_action",
        lambda merged_state, context, now_iso: {
            "mode": "execute",
            "action_id": "write_internal_work_note",
            "reason": "Quiet runtime state.",
            "score": 0.35,
            "payload": {"current_mode": "watch"},
            "considered": [],
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_execute_executive_decision",
        lambda executive_decision: {
            "status": "executed",
            "action_id": "write_internal_work_note",
            "summary": "Executive note written.",
            "details": {"current_mode": "watch"},
            "side_effects": ["internal-work-note"],
            "error": "",
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_heartbeat_prompt_assembly",
        lambda heartbeat_context, name="default": type("Assembly", (), {"text": "heartbeat prompt"})(),
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_execute_heartbeat_model",
        lambda prompt, target, policy, open_loops, liveness: {
            "text": "{}",
            "execution_status": "success",
            "input_tokens": 1,
            "output_tokens": 1,
            "cost_usd": 0.0,
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_parse_heartbeat_decision_bounded",
        lambda raw_response: (
            {
                "decision_type": "noop",
                "summary": "No heartbeat action.",
                "reason": "test",
                "proposed_action": "",
                "ping_text": "",
                "execute_action": "",
            },
            "success",
        ),
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_recover_bounded_heartbeat_liveness_decision",
        lambda decision, policy, liveness: decision,
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_run_bounded_conflict_resolution",
        lambda decision, context, policy: None,
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_apply_conflict_resolution_to_decision",
        lambda decision, conflict_trace: decision,
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_validate_heartbeat_decision",
        lambda decision, policy, workspace_dir, tick_id: {
            "tick_id": tick_id,
            "blocked_reason": "",
            "ping_eligible": False,
            "ping_result": "not-checked",
            "action_status": "skipped",
            "action_summary": "Heartbeat model skipped action.",
            "action_type": "",
            "action_artifact": "",
        },
    )

    captured: dict[str, object] = {}

    def _capture_record(**kwargs):
        captured.update(kwargs)
        return {
            "tick_id": kwargs["tick_id"],
            "tick_status": kwargs["tick_status"],
            "decision_summary": kwargs["decision_summary"],
            "action_status": kwargs["action_status"],
        }

    monkeypatch.setattr(heartbeat_runtime, "_record_heartbeat_outcome", _capture_record)
    monkeypatch.setattr(
        heartbeat_runtime,
        "heartbeat_runtime_surface",
        lambda name="default": {"state": {"last_action_type": captured.get("action_type", "")}},
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_dispatch_runtime_hook_events_safely",
        lambda event_kinds, limit=2: None,
    )

    result = heartbeat_runtime.run_heartbeat_tick(name="default", trigger="test")

    assert captured["action_type"] == "write_internal_work_note"
    assert captured["action_status"] == "executed"
    assert captured["action_summary"] == "Executive note written."
    assert str(captured["action_artifact"]).startswith("rao-")
    assert result.tick["action_status"] == "executed"
