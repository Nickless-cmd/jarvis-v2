def test_mission_control_operations_route_returns_runtime_runs_approvals_and_sessions(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        mission_control,
        "mc_runtime",
        lambda: {
            "provider_router": {},
            "visible_execution": {},
            "runtime_tool_intent": {
                "active": True,
                "approval_state": "pending",
                "approval_source": "none",
                "execution_state": "not-executed",
                "execution_mode": "read-only",
                "mutation_permitted": False,
                "workspace_scoped": False,
                "external_mutation_permitted": False,
                "delete_permitted": False,
                "mutation_intent_state": "proposal-only",
                "mutation_intent_classification": "modify-file",
                "mutation_repo_scope": "",
                "mutation_system_scope": "",
                "mutation_sudo_required": False,
                "write_proposal_state": "scoped-proposal",
                "write_proposal_type": "propose-file-modification",
                "write_proposal_scope": "repo-file",
                "write_proposal_criticality": "medium",
                "write_proposal_target_identity": False,
                "write_proposal_target_memory": False,
                "write_proposal_target": "MEMORY.md",
                "write_proposal_content_state": "bounded-content-ready",
                "write_proposal_content_fingerprint": "feedface12345678",
                "mutating_exec_proposal_state": "approval-required-proposal",
                "mutating_exec_proposal_scope": "system",
                "mutating_exec_requires_sudo": True,
                "mutating_exec_criticality": "high",
                "sudo_exec_proposal_state": "approval-required-proposal",
                "sudo_exec_proposal_scope": "system",
                "sudo_exec_requires_sudo": True,
                "sudo_exec_criticality": "high",
                "sudo_approval_window_state": "active",
                "sudo_approval_window_scope": "tool:run-non-destructive-command::sudo-exec::system::chmod",
                "sudo_approval_window_expires_at": "2026-04-04T12:05:00+00:00",
                "sudo_approval_window_remaining_seconds": 240,
                "sudo_approval_window_reusable": True,
                "action_continuity_state": "idle",
                "last_action_outcome": "none",
                "last_action_at": "",
                "followup_state": "none",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_runs",
        lambda limit=20: {
            "active_run": None,
            "summary": {"recent_count": 0},
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_approvals",
        lambda limit=20: {
            "summary": {"request_count": 0},
            "requests": [],
            "recent_invocations": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "list_chat_sessions",
        lambda: [{"id": "chat-1", "title": "Demo", "message_count": 2}],
    )

    payload = mission_control.mc_operations(limit=10)

    assert payload["runtime"]["provider_router"] == {}
    assert payload["runs"]["recent_runs"] == []
    assert payload["approvals"]["requests"] == []
    assert payload["tool_intent"]["approval_state"] == "pending"
    assert payload["sessions"]["items"] == [
        {"id": "chat-1", "title": "Demo", "message_count": 2}
    ]
    assert payload["summary"]["session_count"] == 1
    assert payload["summary"]["approval_request_count"] == 0
    assert payload["summary"]["tool_intent_active"] is True
    assert payload["summary"]["tool_intent_approval_state"] == "pending"
    assert payload["summary"]["tool_intent_execution_state"] == "not-executed"
    assert payload["summary"]["tool_intent_execution_mode"] == "read-only"
    assert payload["summary"]["tool_intent_mutation_permitted"] is False
    assert payload["summary"]["tool_intent_workspace_scoped"] is False
    assert payload["summary"]["tool_intent_external_mutation_permitted"] is False
    assert payload["summary"]["tool_intent_delete_permitted"] is False
    assert payload["summary"]["tool_intent_mutation_intent_state"] == "proposal-only"
    assert payload["summary"]["tool_intent_mutation_classification"] == "modify-file"
    assert payload["summary"]["tool_intent_mutation_repo_scope"] == ""
    assert payload["summary"]["tool_intent_mutation_system_scope"] == ""
    assert payload["summary"]["tool_intent_mutation_sudo_required"] is False
    assert payload["summary"]["tool_intent_write_proposal_state"] == "scoped-proposal"
    assert payload["summary"]["tool_intent_write_proposal_type"] == "propose-file-modification"
    assert payload["summary"]["tool_intent_write_proposal_scope"] == "repo-file"
    assert payload["summary"]["tool_intent_write_proposal_criticality"] == "medium"
    assert payload["summary"]["tool_intent_write_proposal_target_identity"] is False
    assert payload["summary"]["tool_intent_write_proposal_target_memory"] is False
    assert payload["summary"]["tool_intent_write_proposal_target"] == "MEMORY.md"
    assert payload["summary"]["tool_intent_write_proposal_content_state"] == "bounded-content-ready"
    assert payload["summary"]["tool_intent_write_proposal_content_fingerprint"] == "feedface12345678"
    assert payload["summary"]["tool_intent_mutating_exec_proposal_state"] == "approval-required-proposal"
    assert payload["summary"]["tool_intent_mutating_exec_proposal_scope"] == "system"
    assert payload["summary"]["tool_intent_mutating_exec_requires_sudo"] is True
    assert payload["summary"]["tool_intent_mutating_exec_criticality"] == "high"
    assert payload["summary"]["tool_intent_sudo_exec_proposal_state"] == "approval-required-proposal"
    assert payload["summary"]["tool_intent_sudo_exec_proposal_scope"] == "system"
    assert payload["summary"]["tool_intent_sudo_exec_requires_sudo"] is True
    assert payload["summary"]["tool_intent_sudo_exec_criticality"] == "high"
    assert payload["summary"]["tool_intent_sudo_approval_window_state"] == "active"
    assert payload["summary"]["tool_intent_sudo_approval_window_scope"] == "tool:run-non-destructive-command::sudo-exec::system::chmod"
    assert payload["summary"]["tool_intent_sudo_approval_window_remaining_seconds"] == 240
    assert payload["summary"]["tool_intent_sudo_approval_window_reusable"] is True
    assert payload["summary"]["tool_intent_action_continuity_state"] == "idle"
    assert payload["summary"]["tool_intent_last_action_outcome"] == "none"
    assert payload["summary"]["tool_intent_followup_state"] == "none"


def test_mission_control_operations_route_reflects_mc_tool_intent_resolution(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        isolated_runtime.tool_intent_runtime,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "dirty",
            "local_change_state": "modified",
            "upstream_awareness": "in-sync",
            "concern_state": "concern",
            "source_contributors": ["repo-root", "git-status"],
            "repo_observation": {
                "branch_name": "feature/tool-intent-operations-mc",
                "upstream_ref": "origin/main",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "build_tool_intent_runtime_surface",
        isolated_runtime.tool_intent_runtime.build_tool_intent_runtime_surface,
    )

    mission_control.mc_tool_intent()
    mission_control.mc_approve_tool_intent()
    payload = mission_control.mc_operations(limit=10)

    assert payload["tool_intent"]["approval_state"] == "approved"
    assert payload["tool_intent"]["approval_source"] == "mc"
    assert payload["tool_intent"]["execution_state"] == "blocked-unavailable"
    assert payload["tool_intent"]["execution_mode"] == "read-only"
    assert payload["tool_intent"]["mutation_permitted"] is False
    assert payload["tool_intent"]["workspace_scoped"] is False
    assert payload["tool_intent"]["external_mutation_permitted"] is False
    assert payload["tool_intent"]["delete_permitted"] is False
    assert payload["tool_intent"]["mutation_intent_state"] == "proposal-only"
    assert payload["tool_intent"]["mutation_intent_classification"] == "modify-file"
    assert payload["tool_intent"]["write_proposal_state"] == "scoped-proposal"
    assert payload["tool_intent"]["write_proposal_type"] == "propose-file-modification"
    assert payload["tool_intent"]["action_continuity_state"] == "idle"
    assert payload["summary"]["tool_intent_approval_state"] == "approved"
    assert payload["summary"]["tool_intent_execution_state"] == "blocked-unavailable"
    assert payload["summary"]["tool_intent_execution_mode"] == "read-only"
    assert payload["summary"]["tool_intent_mutation_permitted"] is False
    assert payload["summary"]["tool_intent_workspace_scoped"] is False
    assert payload["summary"]["tool_intent_external_mutation_permitted"] is False
    assert payload["summary"]["tool_intent_delete_permitted"] is False
    assert payload["summary"]["tool_intent_mutation_intent_state"] == "proposal-only"
    assert payload["summary"]["tool_intent_mutation_classification"] == "modify-file"
    assert payload["summary"]["tool_intent_write_proposal_state"] == "scoped-proposal"
    assert payload["summary"]["tool_intent_write_proposal_type"] == "propose-file-modification"
    assert payload["summary"]["tool_intent_action_continuity_state"] == "idle"


def test_mission_control_operations_route_exposes_bounded_action_continuity(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        mission_control,
        "mc_runtime",
        lambda: {
            "provider_router": {},
            "visible_execution": {},
            "runtime_tool_intent": {
                "active": True,
                "approval_state": "approved",
                "approval_source": "mc",
                "execution_state": "read-only-completed",
                "execution_mode": "read-only",
                "mutation_permitted": False,
                "workspace_scoped": False,
                "external_mutation_permitted": False,
                "delete_permitted": False,
                "action_continuity_state": "carrying-forward",
                "last_action_outcome": "read-only-completed",
                "last_action_at": "2026-04-02T10:30:00+00:00",
                "followup_state": "carry-forward",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_runs",
        lambda limit=20: {
            "active_run": None,
            "summary": {"recent_count": 0},
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_approvals",
        lambda limit=20: {
            "summary": {"request_count": 0},
            "requests": [],
            "recent_invocations": [],
        },
    )
    monkeypatch.setattr(mission_control, "list_chat_sessions", lambda: [])

    payload = mission_control.mc_operations(limit=10)

    assert payload["summary"]["tool_intent_action_continuity_state"] == "carrying-forward"
    assert payload["summary"]["tool_intent_last_action_outcome"] == "read-only-completed"
    assert payload["summary"]["tool_intent_last_action_at"] == "2026-04-02T10:30:00+00:00"
    assert payload["summary"]["tool_intent_followup_state"] == "carry-forward"


def test_mission_control_operations_route_surfaces_mutating_exec_execution_summary(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        mission_control,
        "mc_runtime",
        lambda: {
            "provider_router": {},
            "visible_execution": {},
            "runtime_tool_intent": {
                "active": True,
                "approval_state": "approved",
                "approval_source": "capability-approval",
                "execution_state": "mutating-exec-completed",
                "execution_mode": "mutating-exec",
                "mutation_permitted": True,
                "workspace_scoped": False,
                "external_mutation_permitted": True,
                "delete_permitted": False,
                "mutating_exec_proposal_state": "executed",
                "mutating_exec_proposal_scope": "filesystem",
                "mutating_exec_requires_sudo": False,
                "mutating_exec_criticality": "medium",
                "action_continuity_state": "carrying-forward",
                "last_action_outcome": "mutating-exec-completed",
                "last_action_at": "2026-04-03T12:00:00+00:00",
                "followup_state": "bounded-mutating-exec-recorded",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_runs",
        lambda limit=20: {
            "active_run": None,
            "summary": {"recent_count": 0},
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_approvals",
        lambda limit=20: {
            "summary": {"request_count": 1},
            "requests": [],
            "recent_invocations": [],
        },
    )
    monkeypatch.setattr(mission_control, "list_chat_sessions", lambda: [])

    payload = mission_control.mc_operations(limit=5)

    assert payload["summary"]["tool_intent_execution_state"] == "mutating-exec-completed"
    assert payload["summary"]["tool_intent_execution_mode"] == "mutating-exec"
    assert payload["summary"]["tool_intent_mutation_permitted"] is True
    assert payload["summary"]["tool_intent_external_mutation_permitted"] is True
    assert payload["summary"]["tool_intent_delete_permitted"] is False
    assert payload["summary"]["tool_intent_mutating_exec_proposal_state"] == "executed"
    assert payload["summary"]["tool_intent_mutating_exec_proposal_scope"] == "filesystem"
    assert payload["summary"]["tool_intent_mutating_exec_requires_sudo"] is False
    assert payload["summary"]["tool_intent_action_continuity_state"] == "carrying-forward"
    assert payload["summary"]["tool_intent_last_action_outcome"] == "mutating-exec-completed"
    assert payload["summary"]["tool_intent_followup_state"] == "bounded-mutating-exec-recorded"


def test_mission_control_operations_route_surfaces_sudo_exec_execution_summary(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    monkeypatch.setattr(
        mission_control,
        "mc_runtime",
        lambda: {
            "provider_router": {},
            "visible_execution": {},
            "runtime_tool_intent": {
                "active": True,
                "approval_state": "approved",
                "approval_source": "capability-approval",
                "execution_state": "sudo-exec-completed",
                "execution_mode": "sudo-exec",
                "execution_command": "sudo chmod 600 USER.md",
                "mutation_permitted": True,
                "sudo_permitted": True,
                "workspace_scoped": True,
                "external_mutation_permitted": False,
                "delete_permitted": False,
                "sudo_exec_proposal_state": "executed",
                "sudo_exec_proposal_scope": "system",
                "sudo_exec_requires_sudo": True,
                "sudo_exec_criticality": "high",
                "sudo_approval_window_state": "active",
                "sudo_approval_window_scope": "tool:run-non-destructive-command::sudo-exec::system::chmod",
                "sudo_approval_window_expires_at": "2026-04-03T14:05:00+00:00",
                "sudo_approval_window_remaining_seconds": 120,
                "sudo_approval_window_reusable": True,
                "action_continuity_state": "carrying-forward",
                "last_action_outcome": "sudo-exec-completed",
                "last_action_at": "2026-04-03T14:00:00+00:00",
                "followup_state": "bounded-sudo-exec-recorded",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_runs",
        lambda limit=20: {
            "active_run": None,
            "summary": {"recent_count": 0},
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(
        mission_control,
        "mc_approvals",
        lambda limit=20: {
            "summary": {"request_count": 1},
            "requests": [],
            "recent_invocations": [],
        },
    )
    monkeypatch.setattr(mission_control, "list_chat_sessions", lambda: [])

    payload = mission_control.mc_operations(limit=5)

    assert payload["summary"]["tool_intent_execution_state"] == "sudo-exec-completed"
    assert payload["summary"]["tool_intent_execution_mode"] == "sudo-exec"
    assert payload["summary"]["tool_intent_execution_command"] == "sudo chmod 600 USER.md"
    assert payload["summary"]["tool_intent_mutation_permitted"] is True
    assert payload["summary"]["tool_intent_sudo_permitted"] is True
    assert payload["summary"]["tool_intent_workspace_scoped"] is True
    assert payload["summary"]["tool_intent_external_mutation_permitted"] is False
    assert payload["summary"]["tool_intent_delete_permitted"] is False
    assert payload["summary"]["tool_intent_sudo_exec_proposal_state"] == "executed"
    assert payload["summary"]["tool_intent_sudo_exec_proposal_scope"] == "system"
    assert payload["summary"]["tool_intent_sudo_exec_requires_sudo"] is True
    assert payload["summary"]["tool_intent_sudo_approval_window_state"] == "active"
    assert payload["summary"]["tool_intent_sudo_approval_window_reusable"] is True
    assert payload["summary"]["tool_intent_action_continuity_state"] == "carrying-forward"
    assert payload["summary"]["tool_intent_last_action_outcome"] == "sudo-exec-completed"
    assert payload["summary"]["tool_intent_followup_state"] == "bounded-sudo-exec-recorded"
