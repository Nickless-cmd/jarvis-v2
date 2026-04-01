from __future__ import annotations


def test_subagent_ecology_builds_bounded_internal_roles(isolated_runtime) -> None:
    ecology = isolated_runtime.subagent_ecology

    surface = ecology.build_subagent_ecology_from_sources(
        affective_meta_state={
            "state": "reflective",
            "bearing": "inward",
            "reflective_load": "high",
        },
        epistemic_runtime_state={
            "wrongness_state": "off",
            "regret_signal": "slight",
            "counterfactual_mode": "nearby-alternative",
        },
        conflict_trace={
            "outcome": "defer",
            "reason_code": "policy-blocked",
        },
        loop_runtime={
            "summary": {
                "loop_count": 2,
                "current_status": "active",
                "active_count": 1,
                "standby_count": 1,
                "resumed_count": 0,
            }
        },
        prompt_evolution={
            "summary": {
                "last_state": "forming",
                "latest_target_asset": "INNER_VOICE.md",
            },
            "latest_proposal": {
                "proposal_type": "tone-adjustment",
            },
        },
        quiet_initiative={"active": True, "state": "holding", "hold_count": 2},
    )

    assert surface["kind"] == "subagent-ecology-light"
    assert surface["visibility"] == "internal-only"
    assert surface["tool_access"] == "none"
    assert surface["boundary"] == "not-memory-not-identity-not-action-not-tool-execution"
    assert len(surface["roles"]) == 3
    assert surface["summary"]["active_count"] >= 2

    valid_statuses = {"active", "idle", "cooling", "blocked"}
    for role in surface["roles"]:
        assert role["role_name"] in {"critic", "witness-helper", "planner-helper"}
        assert role["current_status"] in valid_statuses
        assert role["internal_only"] is True
        assert role["tool_access"] == "none"
        assert role["influence_scope"] == "bounded"


def test_subagent_ecology_prompt_section_is_grounded_and_bounded(isolated_runtime) -> None:
    ecology = isolated_runtime.subagent_ecology

    section = ecology.build_subagent_ecology_prompt_section(
        {
            "roles": [
                {
                    "role_name": "critic",
                    "current_status": "active",
                    "activation_reason": "epistemic-off",
                },
                {
                    "role_name": "planner-helper",
                    "current_status": "cooling",
                    "activation_reason": "standby-loops-held",
                },
            ],
            "summary": {
                "role_count": 3,
                "active_count": 1,
                "cooling_count": 1,
                "blocked_count": 0,
            },
            "freshness": {"state": "fresh"},
            "tool_access": "none",
            "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        }
    )

    assert "Subagent ecology light" in section
    assert "roles=3" in section
    assert "critic=active(epistemic-off)" in section
    assert "tool_access=none" in section
    assert "do not imply agentic delegation" not in section


def test_heartbeat_self_knowledge_section_includes_subagent_ecology(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    monkeypatch.setattr(
        isolated_runtime.subagent_ecology,
        "build_subagent_ecology_prompt_section",
        lambda surface=None: (
            "Subagent ecology light (derived runtime truth, internal-only):\n"
            "- roles=3 | active=1 | cooling=1 | blocked=0 | freshness=fresh\n"
            "- active_roles=critic=active(epistemic-off) | tool_access=none"
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Subagent ecology light (derived runtime truth, internal-only):" in section
    assert "active_roles=critic=active(epistemic-off)" in section


def test_mission_control_runtime_and_endpoint_expose_subagent_ecology(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "roles": [
            {
                "role_name": "critic",
                "role_kind": "epistemic-check",
                "current_status": "active",
                "last_activation_at": "2026-04-01T20:00:00+00:00",
                "activation_reason": "epistemic-off",
                "internal_only": True,
                "tool_access": "none",
                "influence_scope": "bounded",
            }
        ],
        "summary": {
            "role_count": 3,
            "active_count": 1,
            "idle_count": 1,
            "cooling_count": 1,
            "blocked_count": 0,
            "last_active_role_name": "critic",
            "last_active_role_status": "active",
            "last_activation_reason": "epistemic-off",
        },
        "freshness": {"built_at": "2026-04-01T20:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "internal_only": True,
        "tool_access": "none",
        "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        "kind": "subagent-ecology-light",
        "summary_text": "active internal roles: critic",
    }

    monkeypatch.setattr(
        isolated_runtime.subagent_ecology,
        "build_subagent_ecology_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(isolated_runtime.mission_control, "build_subagent_ecology_surface", lambda: runtime_surface)
    monkeypatch.setattr(isolated_runtime.runtime_self_model, "_subagent_ecology_surface", lambda: runtime_surface)

    endpoint = isolated_runtime.mission_control.mc_subagent_ecology()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["summary"]["last_active_role_name"] == "critic"
    assert runtime["runtime_subagent_ecology"]["tool_access"] == "none"
    assert self_model["subagent_ecology"]["summary"]["active_count"] == 1
