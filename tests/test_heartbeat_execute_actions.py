from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def _insert_visible_run(
    runtime_db,
    *,
    run_id: str,
    status: str = "completed",
    text_preview: str = "Kan du lave et kort resume af næste step?",
    capability_id: str = "chat",
) -> None:
    now = datetime.now(UTC).isoformat()
    with runtime_db.connect() as conn:
        conn.execute(
            """
            INSERT INTO visible_runs (
                run_id, lane, provider, model, status,
                started_at, finished_at, text_preview, error, capability_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "visible",
                "phase1-runtime",
                "visible-placeholder",
                status,
                now,
                now,
                text_preview,
                "",
                capability_id,
            ),
        )


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


def test_initiative_queue_persists_across_module_reload(isolated_runtime) -> None:
    import apps.api.jarvis_api.services.initiative_queue as initiative_queue

    initiative_id = initiative_queue.push_initiative(
        focus="Persist this initiative across runtime reload",
        source="inner-voice",
        source_id="voice-persist",
        priority="high",
    )

    reloaded = importlib.reload(initiative_queue)
    pending = reloaded.get_pending_initiatives()

    assert any(item["initiative_id"] == initiative_id for item in pending)
    persisted = isolated_runtime.db.get_runtime_initiative(initiative_id)
    assert persisted is not None
    assert persisted["focus"] == "Persist this initiative across runtime reload"


def test_act_on_initiative_materializes_runtime_work(isolated_runtime) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    import apps.api.jarvis_api.services.initiative_queue as initiative_queue

    initiative_id = initiative_queue.push_initiative(
        focus="Inspect the current repo thread",
        source="inner-voice",
        source_id="voice-2",
        priority="high",
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="act_on_initiative",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    artifact = json.loads(result["artifact"])
    assert artifact["initiative_id"] == initiative_id

    task = isolated_runtime.db.get_runtime_task(artifact["task_id"])
    flow = isolated_runtime.db.get_runtime_flow(artifact["flow_id"])
    assert task is not None
    assert flow is not None
    assert task["kind"] == "initiative-followup"
    assert task["run_id"] == "heartbeat-tick:test"

    queue_state = initiative_queue.get_initiative_queue_state()
    assert not any(item["initiative_id"] == initiative_id for item in queue_state["pending"])
    assert any(item["initiative_id"] == initiative_id for item in queue_state["recent_acted"])


def test_phase1_heartbeat_prefers_pending_initiative_when_execute_allowed(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setitem(
        sys.modules,
        "apps.api.jarvis_api.services.initiative_queue",
        type(
            "InitiativeQueueStub",
            (),
            {
                "get_pending_initiatives": staticmethod(
                    lambda: [{"initiative_id": "init-1", "focus": "Inspect repo drift", "priority": "high"}]
                )
            },
        ),
    )

    result = heartbeat_runtime._execute_heartbeat_model(
        prompt="heartbeat test",
        target={"provider": "phase1-runtime", "model": "phase1-runtime"},
        policy={"allow_execute": True},
        open_loops=[],
        liveness={"liveness_summary": "", "liveness_pressure": "low", "liveness_threshold_state": "quiet-threshold"},
    )

    payload = json.loads(result["text"])
    assert payload["decision_type"] == "initiative"
    assert payload["execute_action"] == "act_on_initiative"
    assert payload["summary"] == "Inspect repo drift"


def test_process_contract_writes_applies_safe_and_approved_candidates(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    db = isolated_runtime.db
    now = datetime.now(UTC).isoformat()

    db.upsert_runtime_contract_candidate(
        candidate_id=f"candidate-{uuid4().hex}",
        candidate_type="preference_update",
        target_file="USER.md",
        status="proposed",
        source_kind="user-explicit",
        source_mode="visible_chat",
        actor="runtime:test",
        session_id="test-session",
        run_id="test-run",
        canonical_key="user-preference:language:danish",
        summary="User prefers replies in Danish.",
        reason="Explicit durable language preference stated in chat.",
        evidence_summary="Jeg vil gerne have svar på dansk.",
        support_summary="Candidate only. No USER.md write has been applied.",
        confidence="high",
        evidence_class="explicit_user_statement",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation candidate status",
        proposed_value="- Language preference: replies in Danish by default.",
        write_section="## Durable Preferences",
    )
    approved_identity = db.upsert_runtime_contract_candidate(
        candidate_id=f"candidate-{uuid4().hex}",
        candidate_type="identity_update",
        target_file="IDENTITY.md",
        status="approved",
        source_kind="runtime-derived-support",
        source_mode="runtime_selfhood_proposal",
        actor="runtime:test",
        session_id="test-session",
        run_id="test-run",
        canonical_key="selfhood-proposal:challenge-style-proposal:challenge-thread",
        summary="Carry a small internal challenge-before-settling style as a possible future IDENTITY-level trait.",
        reason="Validation approved identity candidate.",
        evidence_summary="identity candidate evidence",
        support_summary="identity candidate support",
        confidence="high",
        evidence_class="single_session_pattern",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Explicitly approved for apply.",
        proposed_value="- Carry a small internal challenge-before-settling style as a possible future IDENTITY-level trait.",
        write_section="## Proposed Canonical Self Shifts",
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="process_contract_writes",
        tick_id="heartbeat-tick:test",
        workspace_dir=workspace_dir,
    )

    assert result["status"] == "executed"
    artifact = json.loads(result["artifact"])
    assert artifact["safe_user_applied"] == 1
    assert artifact["approved_applied"] >= 1

    user_text = (workspace_dir / "USER.md").read_text(encoding="utf-8")
    identity_text = (workspace_dir / "IDENTITY.md").read_text(encoding="utf-8")
    assert "Language preference: replies in Danish by default." in user_text
    assert "challenge-before-settling style" in identity_text

    refreshed_identity = db.get_runtime_contract_candidate(
        str(approved_identity["candidate_id"])
    )
    assert refreshed_identity is not None
    assert refreshed_identity["status"] == "applied"


def test_phase1_heartbeat_prefers_contract_write_processing_when_candidates_wait(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "runtime_contract_candidate_counts",
        lambda: {
            "preference_update:proposed": 1,
            "identity_update:approved": 1,
        },
    )

    result = heartbeat_runtime._execute_heartbeat_model(
        prompt="heartbeat test",
        target={"provider": "phase1-runtime", "model": "phase1-runtime"},
        policy={"allow_execute": True},
        open_loops=[],
        liveness={
            "liveness_summary": "",
            "liveness_pressure": "low",
            "liveness_threshold_state": "quiet-threshold",
        },
    )

    payload = json.loads(result["text"])
    assert payload["decision_type"] == "execute"
    assert payload["execute_action"] == "process_contract_writes"


def test_evaluate_self_experiments_auto_observes_recent_visible_runs(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    _insert_visible_run(
        isolated_runtime.db,
        run_id="run-observe-1",
        text_preview="Kan du først vise et kort resume, og bagefter pege på næste bounded step?",
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="evaluate_self_experiments",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    artifact = json.loads(result["artifact"])
    assert int(artifact["observation"]["observed"]) >= 1

    experiments = isolated_runtime.db.list_cognitive_experiments(status="running", limit=10)
    assert any(int(item["n"]) >= 1 for item in experiments)


def test_manage_runtime_work_materializes_curriculum_tasks(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"repo_reasoning": 0.2, "planning": 0.35}),
        recurring_mistakes=json.dumps(["Svar bliver for lange i simple repo-opgaver"]),
    )

    result = heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="manage_runtime_work",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    assert result["status"] == "executed"
    artifact = json.loads(result["artifact"])
    materialization = artifact["curriculum_materialization"]
    assert int(materialization["created"]) >= 1

    task_id = str(materialization["task_ids"][0])
    task = isolated_runtime.db.get_runtime_task(task_id)
    assert task is not None
    assert task["kind"] == "curriculum-focus"


def test_propose_decision_delivers_message_to_webchat_when_available(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    chat_sessions = __import__(
        "apps.api.jarvis_api.services.chat_sessions",
        fromlist=["create_chat_session", "get_chat_session"],
    )
    session = chat_sessions.create_chat_session(title="Heartbeat bridge")

    result = heartbeat_runtime._validate_heartbeat_decision(
        decision={
            "decision_type": "propose",
            "summary": "Propose inspecting repo drift next.",
            "reason": "Open loop continuity is live.",
            "proposed_action": "Jeg foreslår, at jeg inspicerer repo drift som næste bounded step.",
            "ping_text": "",
            "execute_action": "",
        },
        policy={
            "allow_execute": True,
            "allow_ping": False,
            "allow_propose": True,
            "ping_channel": "webchat",
        },
        workspace_dir=Path("/tmp/test-workspace"),
        tick_id="heartbeat-tick:proposal",
    )

    assert result["blocked_reason"] == ""
    assert result["action_status"] == "sent"
    assert result["action_type"] == "webchat-heartbeat-proposal"

    artifact = json.loads(result["action_artifact"])
    session_view = chat_sessions.get_chat_session(session["id"])

    assert artifact["session_id"] == session["id"]
    assert session_view is not None
    assert session_view["messages"][-1]["content"] == (
        "Jeg foreslår, at jeg inspicerer repo drift som næste bounded step."
    )


def test_blocked_heartbeat_tick_dispatches_runtime_hooks_from_active_loop(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    seen: list[tuple[set[str] | None, int]] = []

    monkeypatch.setattr(
        heartbeat_runtime,
        "_tick_blocked_reason",
        lambda merged_state: "kill-switch-disabled",
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_dispatch_runtime_hook_events_safely",
        lambda *, event_kinds=None, limit=4: seen.append((event_kinds, limit)) or [],
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "heartbeat_runtime_surface",
        lambda name="default": {"state": {"summary": "ok"}},
    )

    heartbeat_runtime._run_heartbeat_tick_locked(trigger="manual-test")

    assert seen == [({"heartbeat.tick_blocked"}, 2)]


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
