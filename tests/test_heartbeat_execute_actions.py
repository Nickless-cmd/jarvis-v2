from __future__ import annotations

import json
import sys
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


def test_inspect_repo_context_invokes_bounded_repo_capabilities(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    calls: list[tuple[str, str]] = []

    def _invoke(capability_id: str, *, command_text=None, **kwargs):
        calls.append((capability_id, str(command_text or "")))
        return {
            "capability": {"capability_id": capability_id},
            "status": "executed",
            "execution_mode": "non-destructive-exec" if command_text else "workspace-file-read",
            "result": {
                "text": "ok",
                "command_text": command_text or "",
                "path": "",
            },
            "detail": "",
        }

    monkeypatch.setattr(heartbeat_runtime, "invoke_workspace_capability", _invoke)

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="inspect_repo_context",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    assert calls[0][0] == "tool:list-project-files"
    assert calls[1][0] == "tool:read-repository-readme"
    assert calls[2][0] == "tool:run-non-destructive-command"
    assert "git -C" in calls[2][1]


def test_follow_open_loop_routes_repo_threads_to_repo_inspection(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    original_execute = heartbeat_runtime._execute_heartbeat_internal_action

    monkeypatch.setattr(
        heartbeat_runtime,
        "visible_session_continuity",
        lambda: {"latest_run_id": "run-1", "latest_status": "success"},
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "recent_visible_runs",
        lambda limit=4: [
            {
                "run_id": "run-1",
                "status": "failed",
                "text_preview": "Repo capability and backend path handling still look wrong.",
                "error": "",
            }
        ],
    )
    seen: list[str] = []

    def _wrapped_execute(*, action_type, tick_id, workspace_dir):
        if action_type != "follow_open_loop":
            seen.append(action_type)
            return {
                "status": "executed",
                "summary": action_type,
                "artifact": json.dumps({"action_type": action_type}),
                "blocked_reason": "",
            }
        return original_execute(
            action_type=action_type,
            tick_id=tick_id,
            workspace_dir=workspace_dir,
        )

    monkeypatch.setattr(
        heartbeat_runtime,
        "_execute_heartbeat_internal_action",
        _wrapped_execute,
    )

    result = original_execute(
        action_type="follow_open_loop",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    assert seen == ["inspect_repo_context"]


def test_manage_runtime_work_orchestrates_hooks_tasks_flows_and_browser_body(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "_heartbeat_runtime_bias_from_recent_work",
        lambda kind: False,
    )

    dispatched = [{"event_id": 1, "task_id": "task-hook", "flow_id": "flow-hook"}]
    queued_tasks = [{"task_id": "task-1"}]
    queued_flows = [{"flow_id": "flow-1", "attempt_count": 0}]
    running_flows = [{"flow_id": "flow-running"}]
    task_updates: list[dict[str, object]] = []
    flow_updates: list[dict[str, object]] = []

    monkeypatch.setitem(
        sys.modules,
        "apps.api.jarvis_api.services.runtime_hooks",
        type(
            "RuntimeHooksStub",
            (),
            {"dispatch_unhandled_hook_events": staticmethod(lambda limit=4: dispatched)},
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "apps.api.jarvis_api.services.runtime_tasks",
        type(
            "RuntimeTasksStub",
            (),
            {
                "list_tasks": staticmethod(
                    lambda status=None, limit=4: queued_tasks if status == "queued" else []
                ),
                "update_task": staticmethod(
                    lambda task_id, **kwargs: task_updates.append({"task_id": task_id, **kwargs})
                    or {"task_id": task_id}
                ),
            },
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "apps.api.jarvis_api.services.runtime_flows",
        type(
            "RuntimeFlowsStub",
            (),
            {
                "list_flows": staticmethod(
                    lambda status=None, limit=4: (
                        queued_flows
                        if status == "queued"
                        else (running_flows if status == "running" else [])
                    )
                ),
                "update_flow": staticmethod(
                    lambda flow_id, **kwargs: flow_updates.append({"flow_id": flow_id, **kwargs})
                    or {"flow_id": flow_id}
                ),
            },
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "apps.api.jarvis_api.services.runtime_browser_body",
        type(
            "RuntimeBrowserBodyStub",
            (),
            {
                "ensure_browser_body": staticmethod(
                    lambda **kwargs: {"body_id": "browser-1", **kwargs}
                )
            },
        ),
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="manage_runtime_work",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    assert "hook dispatches" in result["summary"]
    assert task_updates[0]["task_id"] == "task-1"
    assert flow_updates[0]["flow_id"] == "flow-1"
