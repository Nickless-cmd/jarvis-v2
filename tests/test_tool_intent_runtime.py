from __future__ import annotations

import importlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path

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
    assert surface["workspace_scoped"] is False
    assert surface["external_mutation_permitted"] is False
    assert surface["delete_permitted"] is False
    assert surface["mutation_intent_state"] == "proposal-only"
    assert surface["mutation_intent_classification"] == "git-mutate"
    assert surface["mutation_near"] is True
    assert surface["mutation_proposal_only"] is True
    assert surface["mutation_execution_state"] == "not-executed"
    assert surface["mutation_execution_permitted"] is False
    assert surface["mutation_repo_scope"] == "upstream-sync:feature/tool-intent->origin/main"
    assert surface["mutation_system_scope"] == ""
    assert surface["mutation_sudo_required"] is False
    assert surface["write_proposal_state"] == "scoped-proposal"
    assert surface["write_proposal_type"] == "propose-git-mutation"
    assert surface["write_proposal_scope"] == "git"
    assert surface["write_proposal_approval_scope"] == "repo-update-check"
    assert surface["write_proposal_execution_state"] == "not-executed"
    assert surface["write_proposal_target_identity"] is False
    assert surface["write_proposal_target_memory"] is False
    assert surface["write_proposal_content_state"] == "none"
    assert surface["write_proposal_content_fingerprint"] == ""
    assert surface["action_continuity_state"] == "idle"
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
    assert surface["workspace_scoped"] is False
    assert surface["external_mutation_permitted"] is False
    assert surface["delete_permitted"] is False
    assert surface["mutation_intent_state"] == "idle"
    assert surface["mutation_intent_classification"] == "none"
    assert surface["mutation_near"] is False
    assert surface["write_proposal_state"] == "none"
    assert surface["write_proposal_type"] == "none"
    assert surface["action_continuity_state"] == "idle"


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
        "workspace_scoped": False,
        "external_mutation_permitted": False,
        "delete_permitted": False,
        "mutation_intent": {
            "active": True,
            "kind": "bounded-mutation-intent-light",
            "mutation_intent_state": "proposal-only",
            "classification": "modify-file",
            "mutation_near": True,
            "proposal_only": True,
            "approval_required": True,
            "explicit_approval_required": True,
            "not_executed": True,
            "execution_state": "not-executed",
            "execution_permitted": False,
            "summary": "Current intent is proposal-only and mutation-near.",
            "scope": {
                "target_files": ["apps/api/jarvis_api/services/tool_intent_runtime.py"],
                "target_paths": ["apps/api/jarvis_api/services"],
                "repo_mutation_scope": "",
                "system_mutation_scope": "",
                "sudo_required": False,
                "mutation_critical": False,
            },
            "capability_boundary": {
                "approval_required_mutation_capability_count": 2,
                "approval_required_mutation_classes": ["modify-file", "git-mutate"],
            },
            "write_proposal": {
                "active": True,
                "write_proposal_state": "scoped-proposal",
                "write_proposal_type": "propose-file-modification",
                "write_proposal_scope": "repo-file",
                "write_proposal_targets": [
                    "apps/api/jarvis_api/services/tool_intent_runtime.py"
                ],
                "write_proposal_target_paths": ["apps/api/jarvis_api/services"],
                "write_proposal_reason": (
                    "Runtime sees mutation-near file changes and can carry a bounded "
                    "file-modification proposal."
                ),
                "explicit_approval_required": True,
                "approval_scope": "repo-read",
                "criticality": "medium",
                "confidence": "high",
                "proposal_only": True,
                "not_executed": True,
                "execution_state": "not-executed",
                "mutation_near": True,
                "repo_scope": "",
                "system_scope": "",
                "sudo_required": False,
                "target_identity": False,
                "target_memory": False,
                "boundary": "Write proposal light is approval-scoped runtime truth only.",
                "source_contributors": ["bounded-mutation-intent-runtime"],
            },
            "boundary": "Bounded mutation intent is classification-only runtime truth.",
            "source_contributors": ["bounded-mutation-intent-runtime"],
            "source": "/runtime/bounded-mutation-intent",
        },
        "mutation_intent_state": "proposal-only",
        "mutation_intent_classification": "modify-file",
        "mutation_near": True,
        "mutation_proposal_only": True,
        "mutation_execution_state": "not-executed",
        "mutation_execution_permitted": False,
        "mutation_summary": "Current intent is proposal-only and mutation-near.",
        "mutation_target_files": ["apps/api/jarvis_api/services/tool_intent_runtime.py"],
        "mutation_target_paths": ["apps/api/jarvis_api/services"],
        "mutation_repo_scope": "",
        "mutation_system_scope": "",
        "mutation_sudo_required": False,
        "mutation_critical": False,
        "mutation_boundary": "Bounded mutation intent is classification-only runtime truth.",
        "write_proposal": {
            "active": True,
            "write_proposal_state": "scoped-proposal",
            "write_proposal_type": "propose-file-modification",
            "write_proposal_scope": "repo-file",
            "write_proposal_targets": [
                "apps/api/jarvis_api/services/tool_intent_runtime.py"
            ],
            "write_proposal_target_paths": ["apps/api/jarvis_api/services"],
            "write_proposal_reason": (
                "Runtime sees mutation-near file changes and can carry a bounded "
                "file-modification proposal."
            ),
            "explicit_approval_required": True,
            "approval_scope": "repo-read",
            "criticality": "medium",
            "confidence": "high",
            "proposal_only": True,
            "not_executed": True,
            "execution_state": "not-executed",
            "mutation_near": True,
            "repo_scope": "",
            "system_scope": "",
            "sudo_required": False,
            "target_identity": False,
            "target_memory": False,
            "content_state": "bounded-content-ready",
            "content": "replace content",
            "content_summary": "replace content",
            "content_fingerprint": "abc123",
            "content_source": "explicit-write-content",
            "target": "apps/api/jarvis_api/services/tool_intent_runtime.py",
            "boundary": "Write proposal light is approval-scoped runtime truth only.",
            "source_contributors": ["bounded-mutation-intent-runtime"],
        },
        "write_proposal_state": "scoped-proposal",
        "write_proposal_type": "propose-file-modification",
        "write_proposal_scope": "repo-file",
        "write_proposal_targets": ["apps/api/jarvis_api/services/tool_intent_runtime.py"],
        "write_proposal_target_paths": ["apps/api/jarvis_api/services"],
        "write_proposal_reason": (
            "Runtime sees mutation-near file changes and can carry a bounded "
            "file-modification proposal."
        ),
        "write_proposal_explicit_approval_required": True,
        "write_proposal_approval_scope": "repo-read",
        "write_proposal_criticality": "medium",
        "write_proposal_confidence": "high",
        "write_proposal_proposal_only": True,
        "write_proposal_not_executed": True,
        "write_proposal_execution_state": "not-executed",
        "write_proposal_repo_scope": "",
        "write_proposal_system_scope": "",
        "write_proposal_sudo_required": False,
        "write_proposal_target_identity": False,
        "write_proposal_target_memory": False,
        "write_proposal_content_state": "bounded-content-ready",
        "write_proposal_content": "replace content",
        "write_proposal_content_summary": "replace content",
        "write_proposal_content_fingerprint": "abc123",
        "write_proposal_content_source": "explicit-write-content",
        "write_proposal_target": "apps/api/jarvis_api/services/tool_intent_runtime.py",
        "write_proposal_boundary": "Write proposal light is approval-scoped runtime truth only.",
        "action_continuity": {
            "active": True,
            "kind": "bounded-action-continuity-light",
            "continuity_id": "action-continuity:demo",
            "action_continuity_state": "carrying-forward",
            "last_action_type": "inspect-working-tree",
            "last_action_target": "feature/tool-intent",
            "last_action_summary": "Working tree inspection ran in bounded read-only mode.",
            "last_action_outcome": "read-only-completed",
            "last_action_at": datetime.now(UTC).isoformat(),
            "action_mode": "read-only",
            "read_only": True,
            "workspace_write": False,
            "mutation_permitted": False,
            "followup_state": "carry-forward",
            "followup_hint": "Read-only inspection confirmed local modifications remain present.",
            "post_action_understanding": "Read-only execution confirmed local repo concern without mutating anything.",
            "post_action_concern": "concern",
            "confidence": "high",
            "source_contributors": ["bounded-action-continuity-runtime"],
            "boundary": "Bounded action continuity carries the latest read-only execution truth only; it is runtime continuity, not MEMORY.md, not identity, and not permission to act.",
            "updated_at": datetime.now(UTC).isoformat(),
            "source": "/runtime/bounded-action-continuity",
        },
        "action_continuity_state": "carrying-forward",
        "last_action_type": "inspect-working-tree",
        "last_action_target": "feature/tool-intent",
        "last_action_summary": "Working tree inspection ran in bounded read-only mode.",
        "last_action_outcome": "read-only-completed",
        "last_action_at": datetime.now(UTC).isoformat(),
        "action_mode": "read-only",
        "read_only": True,
        "followup_state": "carry-forward",
        "followup_hint": "Read-only inspection confirmed local modifications remain present.",
        "post_action_understanding": "Read-only execution confirmed local repo concern without mutating anything.",
        "post_action_concern": "concern",
        "action_continuity_confidence": "high",
        "action_continuity_boundary": "Bounded action continuity carries the latest read-only execution truth only; it is runtime continuity, not MEMORY.md, not identity, and not permission to act.",
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
    assert endpoint["mutation_intent_classification"] == "modify-file"
    assert endpoint["mutation_intent_state"] == "proposal-only"
    assert runtime["runtime_tool_intent"]["mutation_near"] is True
    assert runtime["runtime_tool_intent"]["write_proposal_state"] == "scoped-proposal"
    assert runtime["runtime_tool_intent"]["write_proposal_type"] == "propose-file-modification"
    assert runtime["runtime_tool_intent"]["write_proposal_content_state"] == "bounded-content-ready"
    assert runtime["runtime_tool_intent"]["write_proposal_content_fingerprint"] == "abc123"
    assert self_model["tool_intent"]["execution_state"] == "read-only-completed"
    assert self_model["tool_intent"]["execution_mode"] == "read-only"
    assert self_model["tool_intent"]["mutation_permitted"] is False
    assert self_model["tool_intent"]["workspace_scoped"] is False
    assert self_model["tool_intent"]["external_mutation_permitted"] is False
    assert self_model["tool_intent"]["delete_permitted"] is False
    assert self_model["tool_intent"]["mutation_intent_classification"] == "modify-file"
    assert self_model["tool_intent"]["mutation_intent_state"] == "proposal-only"
    assert self_model["tool_intent"]["write_proposal_type"] == "propose-file-modification"
    assert self_model["tool_intent"]["write_proposal_content_state"] == "bounded-content-ready"
    assert self_model["tool_intent"]["write_proposal_content_fingerprint"] == "abc123"
    assert self_model["tool_intent"]["write_proposal_target_identity"] is False
    assert self_model["tool_intent"]["write_proposal_target_memory"] is False
    assert self_model["tool_intent"]["action_continuity_state"] == "carrying-forward"
    assert self_model["tool_intent"]["last_action_outcome"] == "read-only-completed"
    assert self_model["tool_intent"]["followup_state"] == "carry-forward"
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
    assert "workspace_scoped=False" in layer["detail"]
    assert "external_mutation_permitted=False" in layer["detail"]
    assert "delete_permitted=False" in layer["detail"]
    assert "mutation_state=proposal-only" in layer["detail"]
    assert "mutation_classification=modify-file" in layer["detail"]
    assert "write_proposal_state=scoped-proposal" in layer["detail"]
    assert "write_proposal_type=propose-file-modification" in layer["detail"]
    assert "write_proposal_target=apps/api/jarvis_api/services/tool_intent_runtime.py" in layer["detail"]
    assert "write_proposal_content_state=bounded-content-ready" in layer["detail"]
    assert "write_proposal_content_fingerprint=abc123" in layer["detail"]
    assert "write_proposal_target_identity=False" in layer["detail"]
    assert "write_proposal_target_memory=False" in layer["detail"]
    assert "continuity=carrying-forward" in layer["detail"]
    assert "followup_state=carry-forward" in layer["detail"]


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
                "mutation_intent_state": "proposal-only",
                "mutation_intent_classification": "git-mutate",
                "mutation_repo_scope": "upstream-sync:feature/tool-intent->origin/main",
                "mutation_system_scope": "",
                "mutation_sudo_required": False,
                "write_proposal_state": "scoped-proposal",
                "write_proposal_type": "propose-git-mutation",
                "write_proposal_scope": "git",
                "write_proposal_criticality": "high",
                "write_proposal_target_identity": False,
                "write_proposal_target_memory": False,
                "write_proposal_target": "MEMORY.md",
                "write_proposal_content_state": "bounded-content-ready",
                "write_proposal_content_fingerprint": "deadbeefcafefeed",
                "write_proposal_content_summary": "Replace MEMORY.md with approved bounded content.",
                "execution_summary": "No bounded repo inspection has been executed.",
                "action_continuity_state": "idle",
                "last_action_outcome": "none",
                "followup_state": "none",
                "followup_hint": "",
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
    assert "workspace_scoped=False" in lines
    assert "external_mutation_permitted=False" in lines
    assert "delete_permitted=False" in lines
    assert "mutation_state=proposal-only" in lines
    assert "mutation_classification=git-mutate" in lines
    assert "mutation_repo_scope=upstream-sync:feature/tool-intent->origin/main" in lines
    assert "mutation_system_scope=none" in lines
    assert "mutation_sudo_required=False" in lines
    assert "write_proposal_state=scoped-proposal" in lines
    assert "write_proposal_type=propose-git-mutation" in lines
    assert "write_proposal_scope=git" in lines
    assert "write_proposal_criticality=high" in lines
    assert "write_proposal_target=MEMORY.md" in lines
    assert "write_proposal_content_state=bounded-content-ready" in lines
    assert "write_proposal_content_fingerprint=deadbeefcafefeed" in lines
    assert "write_proposal_content_summary=Replace MEMORY.md with approved bounded content." in lines
    assert "write_proposal_target_identity=False" in lines
    assert "write_proposal_target_memory=False" in lines
    assert "continuity=idle" in lines
    assert "last_action_outcome=none" in lines
    assert "followup_state=none" in lines


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
    assert approved["action_continuity_state"] == "carrying-forward"
    assert approved["last_action_type"] == "inspect-working-tree"
    assert approved["last_action_outcome"] == "read-only-completed"
    assert approved["action_mode"] == "read-only"
    assert approved["read_only"] is True
    assert approved["followup_state"] == "carry-forward"
    assert approved["followup_hint"]
    assert approved["post_action_understanding"]
    assert approved["post_action_concern"] == "concern"
    assert approved["action_continuity_boundary"]
    assert "not MEMORY.md" in approved["action_continuity_boundary"]
    assert approved["truth"] == "derived-runtime-truth"


def test_approved_workspace_write_execution_becomes_runtime_truth_and_continuity(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

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
            "host_context": {
                "repo_root": ".",
                "git_present": True,
            },
            "repo_observation": {
                "branch_name": "main",
                "upstream_ref": "origin/main",
            },
        },
    )

    result = caps_mod.invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        approved=True,
        write_content="Approved runtime truth write.\n",
    )
    assert result["status"] == "executed"

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["execution_state"] == "workspace-write-completed"
    assert surface["execution_mode"] == "workspace-write"
    assert surface["execution_target"] == "MEMORY.md"
    assert surface["mutation_permitted"] is True
    assert surface["workspace_scoped"] is True
    assert surface["external_mutation_permitted"] is False
    assert surface["delete_permitted"] is False
    assert surface["write_proposal_state"] == "executed"
    assert surface["write_proposal_type"] == "propose-file-modification"
    assert surface["write_proposal_scope"] == "workspace-file"
    assert surface["write_proposal_targets"] == ["MEMORY.md"]
    assert surface["write_proposal_execution_state"] == "workspace-write-completed"
    assert surface["write_proposal_content_state"] == "executed-proposal-content"
    assert surface["write_proposal_content"] == "Approved runtime truth write.\n"
    assert surface["write_proposal_content_fingerprint"]
    assert surface["action_continuity_state"] == "carrying-forward"
    assert surface["last_action_outcome"] == "workspace-write-completed"
    assert surface["action_mode"] == "workspace-write"
    assert surface["read_only"] is False
    assert surface["workspace_write"] is True
    assert surface["followup_state"] == "bounded-write-recorded"
    assert surface["truth"] == "derived-runtime-truth"


def test_workspace_write_proposal_content_becomes_runtime_truth_before_execution(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

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
            "host_context": {
                "repo_root": ".",
                "git_present": True,
            },
            "repo_observation": {
                "branch_name": "main",
                "upstream_ref": "origin/main",
            },
        },
    )

    proposed = caps_mod.invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        write_content="Pending bounded proposal content.\n",
    )
    assert proposed["status"] == "approval-required"

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["execution_state"] == "not-executed"
    assert surface["write_proposal_state"] == "scoped-proposal"
    assert surface["write_proposal_target"] == "MEMORY.md"
    assert surface["write_proposal_content_state"] == "bounded-content-ready"
    assert surface["write_proposal_content"] == "Pending bounded proposal content.\n"
    assert surface["write_proposal_content_summary"]
    assert surface["write_proposal_content_fingerprint"]
    latest_request = isolated_runtime.db.latest_capability_approval_request(
        execution_mode="workspace-file-write",
        include_executed=False,
    )
    assert latest_request is not None
    assert latest_request["proposal_content_fingerprint"] == surface["write_proposal_content_fingerprint"]


def test_mutating_exec_proposal_becomes_runtime_truth_without_execution(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

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

    proposal = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="sudo ls /root",
    )
    assert proposal["status"] == "approval-required"

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["execution_state"] == "not-executed"
    assert surface["execution_mode"] == "sudo-exec-proposal"
    assert surface["approval_state"] == "pending"
    assert surface["mutation_permitted"] is False
    assert surface["mutating_exec_proposal_state"] == "approval-required-proposal"
    assert surface["mutating_exec_proposal_command"] == "sudo ls /root"
    assert surface["mutating_exec_proposal_scope"] == "system"
    assert surface["mutating_exec_requires_approval"] is True
    assert surface["mutating_exec_requires_sudo"] is True
    assert surface["mutating_exec_criticality"] == "high"
    assert surface["mutating_exec_command_fingerprint"]
    assert surface["sudo_exec_proposal_state"] == "approval-required-proposal"
    assert surface["sudo_exec_proposal_command"] == "sudo ls /root"
    assert surface["sudo_exec_proposal_scope"] == "system"
    assert surface["sudo_exec_requires_approval"] is True
    assert surface["sudo_exec_requires_sudo"] is True
    assert surface["sudo_exec_criticality"] == "high"
    assert surface["sudo_exec_command_fingerprint"]


def test_approved_non_sudo_mutating_exec_becomes_runtime_truth_and_continuity(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    source = Path("/tmp/jarvis_tool_intent_mutating_exec_source.txt")
    target = Path("/tmp/jarvis_tool_intent_mutating_exec_target.txt")
    source.write_text("runtime truth mutating exec\n", encoding="utf-8")
    if target.exists():
        target.unlink()

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

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"cp {source} {target}",
    )
    assert proposed["status"] == "approval-required"
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="mutating-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_id)

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)
    assert executed["ok"] is True

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["execution_state"] == "mutating-exec-completed"
    assert surface["execution_mode"] == "mutating-exec"
    assert surface["mutation_permitted"] is True
    assert surface["workspace_scoped"] is False
    assert surface["external_mutation_permitted"] is True
    assert surface["delete_permitted"] is False
    assert surface["mutating_exec_proposal_state"] == "executed"
    assert surface["mutating_exec_proposal_command"] == f"cp {source} {target}"
    assert surface["mutating_exec_proposal_scope"] == "filesystem"
    assert surface["mutating_exec_requires_sudo"] is False
    assert surface["mutating_exec_command_fingerprint"]
    assert surface["action_continuity_state"] == "carrying-forward"
    assert surface["last_action_outcome"] == "mutating-exec-completed"
    assert surface["action_mode"] == "mutating-exec"
    assert surface["truth"] == "derived-runtime-truth"


def test_approved_sudo_exec_becomes_runtime_truth_and_continuity(
    isolated_runtime,
    monkeypatch,
) -> None:
    tool_intent_mod = isolated_runtime.tool_intent_runtime
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target = workspace_dir / "tool_intent_sudo_exec_target.txt"
    target.write_text("runtime truth sudo exec\n", encoding="utf-8")

    def _fake_run_bounded_command(*, argv, workspace_dir):
        return subprocess.CompletedProcess(argv, 0, "", ""), None

    monkeypatch.setattr(caps_mod, "_run_bounded_command", _fake_run_bounded_command)
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

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"sudo chmod 600 {target}",
    )
    assert proposed["status"] == "approval-required"
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_id)

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)
    assert executed["ok"] is True

    surface = tool_intent_mod.build_tool_intent_runtime_surface()

    assert surface["execution_state"] == "sudo-exec-completed"
    assert surface["execution_mode"] == "sudo-exec"
    assert surface["execution_command"] == f"sudo chmod 600 {target}"
    assert surface["mutation_permitted"] is True
    assert surface["sudo_permitted"] is True
    assert surface["workspace_scoped"] is True
    assert surface["external_mutation_permitted"] is False
    assert surface["delete_permitted"] is False
    assert surface["mutating_exec_proposal_state"] == "executed"
    assert surface["mutating_exec_proposal_command"] == f"sudo chmod 600 {target}"
    assert surface["mutating_exec_requires_sudo"] is True
    assert surface["sudo_exec_proposal_state"] == "executed"
    assert surface["sudo_exec_proposal_command"] == f"sudo chmod 600 {target}"
    assert surface["sudo_exec_requires_sudo"] is True
    assert surface["action_continuity_state"] == "carrying-forward"
    assert surface["last_action_outcome"] == "sudo-exec-completed"
    assert surface["action_mode"] == "sudo-exec"
    assert surface["truth"] == "derived-runtime-truth"


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
