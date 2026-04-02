from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.api.jarvis_api.services.chat_sessions import append_chat_message, create_chat_session


def test_tool_intent_builds_approval_gated_shape_from_awareness(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime

    monkeypatch.setattr(
        tool_intent_mod,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "dirty",
            "local_change_state": "mixed",
            "upstream_awareness": "behind",
            "concern_state": "action-requires-approval",
            "source_contributors": ["repo-root", "git-status"],
            "repo_observation": {
                "branch_name": "feature/tool-intent",
                "upstream_ref": "origin/main",
            },
        },
    )

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["truth"] == "proposal-only"
    assert surface["intent_state"] == "approval-required"
    assert surface["intent_type"] == "inspect-upstream-divergence"
    assert surface["intent_target"] == "origin/main"
    assert surface["approval_required"] is True
    assert surface["approval_scope"] == "repo-update-check"
    assert surface["approval_state"] == "pending"
    assert surface["approval_source"] == "none"
    assert surface["execution_state"] == "not-executed"
    assert "proposal-only" in surface["boundary"]
    assert "approval-gated" in surface["boundary"]
    assert "self-system-code-awareness" in surface["source_contributors"]


def test_tool_intent_stays_idle_when_awareness_is_stable(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime

    monkeypatch.setattr(
        tool_intent_mod,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "clean",
            "local_change_state": "clean",
            "upstream_awareness": "in-sync",
            "concern_state": "stable",
            "source_contributors": ["repo-root", "git-status"],
            "repo_observation": {
                "branch_name": "main",
                "upstream_ref": "origin/main",
            },
        },
    )

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["intent_state"] == "idle"
    assert surface["urgency"] == "low"
    assert surface["approval_required"] is True
    assert surface["approval_state"] == "none"
    assert surface["approval_source"] == "none"
    assert surface["execution_state"] == "not-executed"
    assert surface["execution_mode"] == "read-only"
    assert surface["mutation_permitted"] is False


def test_tool_intent_is_exposed_in_runtime_endpoint_and_self_model(
    isolated_runtime,
    monkeypatch,
) -> None:
    surface = {
        "active": True,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "truth": "proposal-only",
        "kind": "approval-gated-tool-intent-light",
        "execution_state": "read-only-completed",
        "execution_mode": "read-only",
        "execution_target": "feature/tool-intent",
        "execution_summary": "Working tree inspection ran in bounded read-only mode.",
        "execution_started_at": datetime.now(UTC).isoformat(),
        "execution_finished_at": datetime.now(UTC).isoformat(),
        "execution_confidence": "high",
        "execution_operation": "inspect-working-tree",
        "execution_excerpt": ["modified:apps/api/jarvis_api/services/tool_intent_runtime.py"],
        "mutation_permitted": False,
        "intent_state": "formed",
        "intent_type": "inspect-working-tree",
        "intent_target": "feature/tool-intent",
        "intent_reason": "Read-only awareness sees local modifications; Jarvis can ask to inspect them.",
        "approval_required": True,
        "approval_scope": "repo-read",
        "approval_state": "approved",
        "approval_source": "verbal",
        "approval_reason": "Intent remains proposal-only until explicitly approved within bounded scope.",
        "approval_requested_at": datetime.now(UTC).isoformat(),
        "approval_expires_at": datetime.now(UTC).isoformat(),
        "approval_resolved_at": datetime.now(UTC).isoformat(),
        "approval_resolution_reason": "Explicit bounded verbal approval matched the current tool-intent context.",
        "approval_resolution_message": "approve repo read tool intent",
        "approval_session_id": "chat-approval",
        "approval_lifecycle": "bounded-approval-surface-light",
        "approval_semantics": {
            "verbal_supported": True,
            "mc_supported": True,
            "mode": "explicit-bounded-approval-only",
        },
        "urgency": "medium",
        "confidence": "high",
        "source_contributors": ["self-system-code-awareness", "git-status"],
        "boundary": "Intent is proposal-only and approval-gated. No action has been performed.",
        "seam_usage": [
            "heartbeat-grounding",
            "prompt-contract-runtime-truth",
            "runtime-self-model",
            "mission-control-runtime",
        ],
        "built_at": datetime.now(UTC).isoformat(),
        "source": "/mc/tool-intent",
    }

    monkeypatch.setattr(
        isolated_runtime.tool_intent_runtime,
        "build_tool_intent_runtime_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_tool_intent_runtime_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_tool_intent_surface",
        lambda: surface,
    )

    endpoint = isolated_runtime.mission_control.mc_tool_intent()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["intent_type"] == "inspect-working-tree"
    assert runtime["runtime_tool_intent"]["approval_scope"] == "repo-read"
    assert runtime["runtime_tool_intent"]["approval_required"] is True
    assert runtime["runtime_tool_intent"]["approval_state"] == "approved"
    assert endpoint["approval_source"] == "verbal"
    assert self_model["tool_intent"]["execution_state"] == "read-only-completed"
    assert self_model["tool_intent"]["execution_mode"] == "read-only"
    assert self_model["tool_intent"]["mutation_permitted"] is False
    layer = next(
        item for item in self_model["layers"]
        if item["id"] == "approval-gated-tool-intent-light"
    )
    assert layer["truth"] == "derived"
    assert "approval_state=approved" in layer["detail"]
    assert "approval_source=verbal" in layer["detail"]
    assert "approval_required=True" in layer["detail"]
    assert "execution=read-only-completed" in layer["detail"]
    assert "execution_mode=read-only" in layer["detail"]
    assert "mutation_permitted=False" in layer["detail"]


def test_heartbeat_runtime_truth_includes_tool_intent(
    isolated_runtime,
) -> None:
    lines = isolated_runtime.prompt_contract._heartbeat_runtime_truth_instruction(
        {
            "schedule_status": "due",
            "budget_status": "open",
            "kill_switch": "enabled",
            "tool_intent": {
                "intent_state": "approval-required",
                "intent_type": "inspect-upstream-divergence",
                "intent_target": "origin/main",
                "urgency": "high",
                "approval_state": "pending",
                "approval_source": "none",
                "approval_required": True,
                "approval_expires_at": "2099-01-01T00:00:00+00:00",
                "execution_state": "not-executed",
                "execution_mode": "read-only",
                "mutation_permitted": False,
                "execution_summary": "No bounded repo inspection has been executed.",
            },
        }
    )

    assert "tool_intent=approval-required" in lines
    assert "type=inspect-upstream-divergence" in lines
    assert "target=origin/main" in lines
    assert "urgency=high" in lines
    assert "approval_state=pending" in lines
    assert "approval_source=none" in lines
    assert "approval_required=True" in lines
    assert "approval_expires_at=2099-01-01T00:00:00+00:00" in lines
    assert "execution_state=not-executed" in lines
    assert "execution_mode=read-only" in lines
    assert "mutation_permitted=False" in lines


def test_tool_intent_verbal_approval_becomes_runtime_truth(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime

    monkeypatch.setattr(
        tool_intent_mod,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "dirty",
            "local_change_state": "modified",
            "upstream_awareness": "in-sync",
            "concern_state": "concern",
            "source_contributors": ["repo-root", "git-status"],
            "repo_observation": {
                "branch_name": "feature/tool-intent",
                "upstream_ref": "origin/main",
            },
        },
    )

    pending = tool_intent_mod.build_tool_intent_runtime_surface()
    session = create_chat_session(title="Approval test")
    append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="approve repo read tool intent",
    )

    approved = tool_intent_mod.build_tool_intent_runtime_surface()

    assert pending["approval_state"] == "pending"
    assert approved["approval_state"] == "approved"
    assert approved["approval_source"] == "verbal"
    assert approved["execution_state"] == "blocked-unavailable"
    assert approved["execution_mode"] == "read-only"
    assert approved["mutation_permitted"] is False
    assert approved["approval_resolution_message"] == "approve repo read tool intent"


def test_tool_intent_verbal_denial_is_bounded_runtime_truth(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime

    monkeypatch.setattr(
        tool_intent_mod,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "dirty",
            "local_change_state": "modified",
            "upstream_awareness": "in-sync",
            "concern_state": "concern",
            "source_contributors": ["repo-root", "git-status"],
            "repo_observation": {
                "branch_name": "feature/tool-intent-deny",
                "upstream_ref": "origin/main",
            },
        },
    )

    _ = tool_intent_mod.build_tool_intent_runtime_surface()
    session = create_chat_session(title="Approval deny test")
    append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="afvis repo read tool intent",
    )

    denied = tool_intent_mod.build_tool_intent_runtime_surface()

    assert denied["approval_state"] == "denied"
    assert denied["approval_source"] == "verbal"
    assert denied["execution_state"] == "not-executed"
    assert denied["mutation_permitted"] is False
    assert "denial" in denied["approval_resolution_reason"].lower()


def test_tool_intent_approval_can_expire_without_execution(
    isolated_runtime,
) -> None:
    approval_runtime = isolated_runtime.tool_intent_approval_runtime

    expired = approval_runtime.build_tool_intent_approval_surface(
        {
            "intent_state": "approval-required",
            "intent_type": "inspect-upstream-divergence",
            "intent_target": "origin/main",
            "approval_scope": "repo-update-check",
            "approval_required": True,
            "execution_state": "not-executed",
        },
        requested_at="2000-01-01T00:00:00+00:00",
    )

    assert expired["approval_state"] == "expired"
    assert expired["approval_source"] == "none"
    assert expired["execution_state"] == "not-executed"
    assert expired["approval_requested_at"] == "2000-01-01T00:00:00+00:00"
    assert expired["approval_resolution_reason"]


def test_approved_read_only_tool_intent_executes_bounded_repo_inspection(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    bounded_tools = isolated_runtime.bounded_repo_tools_runtime

    monkeypatch.setattr(
        tool_intent_mod,
        "build_self_system_code_awareness_surface",
        lambda: {
            "code_awareness_state": "repo-visible",
            "repo_status": "dirty",
            "local_change_state": "modified",
            "upstream_awareness": "in-sync",
            "concern_state": "concern",
            "source_contributors": ["repo-root", "git-status"],
            "host_context": {
                "repo_root": ".",
                "git_present": True,
            },
            "repo_observation": {
                "branch_name": "feature/bounded-read-only",
                "upstream_ref": "origin/main",
            },
        },
    )
    monkeypatch.setattr(
        bounded_tools,
        "_inspect_working_tree",
        lambda repo_root, intent_target: {
            "execution_target": intent_target,
            "execution_summary": "Working tree inspection found 2 modified files in bounded read-only mode.",
            "execution_confidence": "high",
            "execution_excerpt": [
                "modified:apps/api/jarvis_api/services/tool_intent_runtime.py",
                "modified:tests/test_tool_intent_runtime.py",
            ],
            "source_contributors": ["git-status", "git-diff-stat"],
        },
    )

    session = create_chat_session(title="Approved execution test")
    pending = tool_intent_mod.build_tool_intent_runtime_surface()
    append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="approve inspect working tree tool intent",
    )

    approved = tool_intent_mod.build_tool_intent_runtime_surface()

    assert pending["approval_state"] == "pending"
    assert pending["execution_state"] == "not-executed"
    assert approved["approval_state"] == "approved"
    assert approved["execution_state"] == "read-only-completed"
    assert approved["execution_mode"] == "read-only"
    assert approved["execution_operation"] == "inspect-working-tree"
    assert approved["execution_target"] == "feature/bounded-read-only"
    assert approved["execution_summary"]
    assert approved["execution_excerpt"]
    assert approved["mutation_permitted"] is False
    assert approved["truth"] == "derived-runtime-truth"


@pytest.mark.parametrize("approval_state", ["pending", "denied", "expired"])
def test_non_approved_tool_intent_does_not_execute_read_only_repo_tools(
    isolated_runtime,
    monkeypatch,
    approval_state: str,
) -> None:
    bounded_tools = isolated_runtime.bounded_repo_tools_runtime

    called = {"value": False}

    def _fail_if_called(*args, **kwargs):
        called["value"] = True
        raise AssertionError("read-only handler should not run")

    monkeypatch.setattr(bounded_tools, "_inspect_working_tree", _fail_if_called)

    surface = bounded_tools.build_bounded_repo_tool_execution_surface(
        {
            "intent_state": "formed",
            "intent_type": "inspect-working-tree",
            "intent_target": "feature/non-approved",
            "approval_scope": "repo-read",
            "approval_state": approval_state,
            "confidence": "high",
        },
        awareness_surface={
            "host_context": {
                "repo_root": "/tmp/demo-repo",
                "git_present": True,
            }
        },
    )

    assert surface["execution_state"] == "not-executed"
    assert surface["execution_mode"] == "read-only"
    assert surface["mutation_permitted"] is False
    assert called["value"] is False


@pytest.mark.parametrize(
    ("action", "expected_state"),
    (("approve", "approved"), ("deny", "denied")),
)
def test_tool_intent_pending_can_resolve_via_bounded_mc_path(
    isolated_runtime,
    monkeypatch,
    action: str,
    expected_state: str,
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
                "branch_name": f"feature/tool-intent-mc-{action}",
                "upstream_ref": "origin/main",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "build_tool_intent_runtime_surface",
        isolated_runtime.tool_intent_runtime.build_tool_intent_runtime_surface,
    )

    pending = mission_control.mc_tool_intent()
    assert pending["approval_state"] == "pending"

    payload = (
        mission_control.mc_approve_tool_intent()
        if action == "approve"
        else mission_control.mc_deny_tool_intent()
    )

    assert payload["ok"] is True
    assert payload["request"]["approval_state"] == expected_state
    assert payload["request"]["approval_source"] == "mc"
    assert payload["tool_intent"]["approval_state"] == expected_state
    assert payload["tool_intent"]["approval_source"] == "mc"
    expected_execution_state = "blocked-unavailable" if expected_state == "approved" else "not-executed"
    assert payload["tool_intent"]["execution_state"] == expected_execution_state
    assert payload["tool_intent"]["execution_mode"] == "read-only"
    assert payload["tool_intent"]["mutation_permitted"] is False


def test_mc_tool_intent_approval_does_not_mix_with_chat_or_execution(
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
                "branch_name": "feature/tool-intent-mc-isolation",
                "upstream_ref": "origin/main",
            },
        },
    )
    monkeypatch.setattr(
        mission_control,
        "build_tool_intent_runtime_surface",
        isolated_runtime.tool_intent_runtime.build_tool_intent_runtime_surface,
    )

    _ = mission_control.mc_tool_intent()
    with isolated_runtime.db.connect() as conn:
        message_count_before = conn.execute(
            "SELECT COUNT(*) AS n FROM chat_messages"
        ).fetchone()["n"]
        run_count_before = conn.execute(
            "SELECT COUNT(*) AS n FROM visible_runs"
        ).fetchone()["n"]

    payload = mission_control.mc_approve_tool_intent()

    with isolated_runtime.db.connect() as conn:
        message_count_after = conn.execute(
            "SELECT COUNT(*) AS n FROM chat_messages"
        ).fetchone()["n"]
        run_count_after = conn.execute(
            "SELECT COUNT(*) AS n FROM visible_runs"
        ).fetchone()["n"]

    assert message_count_after == message_count_before
    assert run_count_after == run_count_before
    assert payload["tool_intent"]["approval_source"] == "mc"
    assert payload["tool_intent"]["execution_state"] == "blocked-unavailable"
    assert payload["tool_intent"]["mutation_permitted"] is False
