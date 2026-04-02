from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def test_self_system_code_awareness_builds_bounded_read_only_shape(
    isolated_runtime,
    monkeypatch,
    tmp_path,
) -> None:
    awareness_mod = isolated_runtime.self_system_code_awareness
    workspace_root = tmp_path / "jarvis-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        awareness_mod,
        "load_workspace_capabilities",
        lambda name="default": {
            "workspace": str(workspace_root),
            "authority": {"approval_required_count": 3},
        },
    )
    monkeypatch.setattr(
        awareness_mod,
        "_detect_repo_root",
        lambda *starts: Path("/tmp/jarvis-repo"),
    )
    monkeypatch.setattr(
        awareness_mod,
        "_observe_repo_status",
        lambda repo_root: {
            "branch_name": "feature/runtime-awareness",
            "upstream_ref": "origin/main",
            "ahead_count": 0,
            "behind_count": 2,
            "dirty_working_tree": True,
            "untracked_present": True,
            "modified_present": True,
            "recent_local_changes_present": True,
            "repo_status": "dirty",
            "local_change_state": "mixed",
            "upstream_awareness": "behind",
        },
    )

    surface = awareness_mod.build_self_system_code_awareness_surface()

    assert surface["system_awareness_state"] == "host-ready"
    assert surface["code_awareness_state"] == "repo-visible"
    assert surface["repo_status"] == "dirty"
    assert surface["local_change_state"] == "mixed"
    assert surface["upstream_awareness"] == "behind"
    assert surface["concern_state"] == "action-requires-approval"
    assert surface["action_requires_approval"] is True
    assert surface["observation_mode"] == "read-only"
    assert surface["confidence"] == "high"
    assert "git-status" in surface["source_contributors"]
    assert surface["repo_observation"]["approval_required_capability_count"] == 3
    assert surface["repo_observation"]["branch_name"] == "feature/runtime-awareness"
    assert "explicit approval" in surface["approval_boundary"]
    assert "sync action would require approval" in surface["concern_hint"]


def test_self_system_code_awareness_stays_notice_when_repo_is_not_detected(
    isolated_runtime,
    monkeypatch,
) -> None:
    awareness_mod = isolated_runtime.self_system_code_awareness

    monkeypatch.setattr(
        awareness_mod,
        "load_workspace_capabilities",
        lambda name="default": {
            "workspace": str(Path("/tmp/jarvis-workspace")),
            "authority": {"approval_required_count": 0},
        },
    )
    monkeypatch.setattr(awareness_mod, "_detect_repo_root", lambda *starts: None)

    surface = awareness_mod.build_self_system_code_awareness_surface()

    assert surface["code_awareness_state"] == "repo-unavailable"
    assert surface["repo_status"] == "not-git"
    assert surface["local_change_state"] == "unknown"
    assert surface["upstream_awareness"] == "unknown"
    assert surface["concern_state"] == "notice"
    assert surface["action_requires_approval"] is True


def test_self_system_code_awareness_is_exposed_in_runtime_and_endpoint(
    isolated_runtime,
    monkeypatch,
) -> None:
    surface = {
        "active": True,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "truth": "read-only-observation",
        "kind": "self-system-code-awareness-light",
        "observation_mode": "read-only",
        "system_awareness_state": "host-ready",
        "code_awareness_state": "repo-visible",
        "repo_status": "dirty",
        "local_change_state": "modified",
        "upstream_awareness": "ahead",
        "concern_state": "concern",
        "concern_hint": "Branch is ahead with visible local modifications; no action has been taken.",
        "action_requires_approval": True,
        "confidence": "high",
        "source_contributors": ["cwd", "repo-root", "git-status"],
        "approval_boundary": "Observation is read-only. Any repo action would require explicit approval.",
        "repo_observation": {
            "branch_name": "feature/runtime-awareness",
            "upstream_ref": "origin/main",
            "ahead_count": 1,
            "behind_count": 0,
            "dirty_working_tree": True,
            "untracked_present": False,
            "modified_present": True,
            "recent_local_changes_present": True,
            "repo_status": "dirty",
            "local_change_state": "modified",
            "upstream_awareness": "ahead",
            "approval_required_capability_count": 2,
            "repo_root_detected": True,
        },
        "seam_usage": [
            "heartbeat-grounding",
            "prompt-contract-runtime-truth",
            "runtime-self-model",
            "mission-control-runtime",
        ],
        "built_at": datetime.now(UTC).isoformat(),
        "source": "/mc/self-system-code-awareness",
    }

    monkeypatch.setattr(
        isolated_runtime.self_system_code_awareness,
        "build_self_system_code_awareness_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_self_system_code_awareness_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_self_system_code_awareness_surface",
        lambda: surface,
    )

    endpoint = isolated_runtime.mission_control.mc_self_system_code_awareness()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["code_awareness_state"] == "repo-visible"
    assert endpoint["concern_state"] == "concern"
    assert runtime["runtime_self_system_code_awareness"]["upstream_awareness"] == "ahead"
    assert runtime["runtime_self_system_code_awareness"]["action_requires_approval"] is True
    assert self_model["self_system_code_awareness"]["repo_status"] == "dirty"
    layer = next(
        item for item in self_model["layers"]
        if item["id"] == "self-system-code-awareness-light"
    )
    assert layer["truth"] == "derived"
    assert "approval_required=True" in layer["detail"]


def test_heartbeat_runtime_truth_includes_self_system_code_awareness(
    isolated_runtime,
) -> None:
    lines = isolated_runtime.prompt_contract._heartbeat_runtime_truth_instruction(
        {
            "schedule_status": "due",
            "budget_status": "open",
            "kill_switch": "enabled",
            "self_system_code_awareness": {
                "code_awareness_state": "repo-visible",
                "repo_status": "dirty",
                "local_change_state": "modified",
                "upstream_awareness": "ahead",
                "concern_state": "concern",
                "action_requires_approval": True,
            },
        }
    )

    assert "self_system_code_awareness=repo-visible" in lines
    assert "repo=dirty" in lines
    assert "changes=modified" in lines
    assert "upstream=ahead" in lines
    assert "concern=concern" in lines
    assert "approval_required=True" in lines
