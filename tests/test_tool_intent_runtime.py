from __future__ import annotations

from datetime import UTC, datetime


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
    assert surface["execution_state"] == "not-executed"


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
        "execution_state": "not-executed",
        "intent_state": "formed",
        "intent_type": "inspect-working-tree",
        "intent_target": "feature/tool-intent",
        "intent_reason": "Read-only awareness sees local modifications; Jarvis can ask to inspect them.",
        "approval_required": True,
        "approval_scope": "repo-read",
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
    assert self_model["tool_intent"]["execution_state"] == "not-executed"
    layer = next(
        item for item in self_model["layers"]
        if item["id"] == "approval-gated-tool-intent-light"
    )
    assert layer["truth"] == "derived"
    assert "approval_required=True" in layer["detail"]
    assert "execution=not-executed" in layer["detail"]


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
                "approval_required": True,
            },
        }
    )

    assert "tool_intent=approval-required" in lines
    assert "type=inspect-upstream-divergence" in lines
    assert "target=origin/main" in lines
    assert "urgency=high" in lines
    assert "approval_required=True" in lines
