from __future__ import annotations


def test_council_runtime_builds_from_subagent_ecology(isolated_runtime) -> None:
    council = isolated_runtime.council_runtime

    surface = council.build_council_runtime_from_sources(
        subagent_ecology={
            "roles": [
                {
                    "role_name": "critic",
                    "role_kind": "epistemic-check",
                    "current_status": "active",
                    "activation_reason": "epistemic-off",
                },
                {
                    "role_name": "witness-helper",
                    "role_kind": "reflective-observer",
                    "current_status": "active",
                    "activation_reason": "reflective-bearing-live",
                },
                {
                    "role_name": "planner-helper",
                    "role_kind": "bounded-coordination",
                    "current_status": "cooling",
                    "activation_reason": "standby-loops-held",
                },
            ],
            "summary": {
                "active_count": 2,
                "blocked_count": 0,
                "last_active_role_name": "critic",
            },
        },
        affective_meta_state={
            "state": "reflective",
            "bearing": "inward",
        },
        epistemic_runtime_state={
            # Use "strained" — only actual epistemic strain triggers
            # critic.constrain → bounded-check. "off" is treated as a
            # neutral no-active-assessment state per council_runtime
            # _role_position semantics.
            "wrongness_state": "strained",
            "regret_signal": "active",
        },
        conflict_trace={
            "outcome": "quiet_hold",
            "reason_code": "quiet-hold-continue",
        },
    )

    assert surface["kind"] == "council-runtime-light"
    assert surface["visibility"] == "internal-only"
    assert surface["tool_access"] == "none"
    assert surface["boundary"] == "not-memory-not-identity-not-action-not-tool-execution"
    assert surface["participating_roles"] == ["critic", "witness-helper", "planner-helper"]
    assert surface["recommendation"] == "bounded-check"
    assert surface["divergence_level"] in {"medium", "high"}
    assert len(surface["role_positions"]) == 3
    assert all(item["tool_access"] == "none" for item in surface["role_positions"])


def test_council_runtime_prompt_section_is_grounded(isolated_runtime) -> None:
    council = isolated_runtime.council_runtime

    section = council.build_council_runtime_prompt_section(
        {
            "council_state": "checking",
            "recommendation": "bounded-check",
            "divergence_level": "medium",
            "confidence": "high",
            "role_positions": [
                {"role_name": "critic", "position": "constrain"},
                {"role_name": "witness-helper", "position": "observe"},
                {"role_name": "planner-helper", "position": "hold"},
            ],
            "tool_access": "none",
            "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        }
    )

    assert "Council runtime light" in section
    assert "recommendation=bounded-check" in section
    assert "critic->constrain" in section
    assert "tool_access=none" in section


def test_heartbeat_self_knowledge_section_includes_council_runtime(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    monkeypatch.setattr(
        isolated_runtime.council_runtime,
        "build_council_runtime_prompt_section",
        lambda surface=None: (
            "Council runtime light (derived runtime truth, internal-only):\n"
            "- state=checking | recommendation=bounded-check | divergence=medium | confidence=high\n"
            "- roles=critic->constrain, witness-helper->observe | tool_access=none"
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Council runtime light (derived runtime truth, internal-only):" in section
    assert "recommendation=bounded-check" in section


def test_mission_control_runtime_and_endpoint_expose_council_runtime(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "council_state": "checking",
        "participating_roles": ["critic", "witness-helper", "planner-helper"],
        "role_positions": [
            {
                "role_name": "critic",
                "role_kind": "epistemic-check",
                "status": "active",
                "position": "constrain",
                "activation_reason": "epistemic-off",
                "tool_access": "none",
                "internal_only": True,
            }
        ],
        "divergence_level": "medium",
        "recommendation": "bounded-check",
        "recommendation_reason": "critic-pressure from wrongness=off and conflict=defer",
        "confidence": "high",
        "last_council_at": "2026-04-01T20:00:00+00:00",
        "summary": "checking council with bounded-check recommendation at medium divergence",
        "source_contributors": [],
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
        "influence_scope": "bounded",
        "boundary": "not-memory-not-identity-not-action-not-tool-execution",
        "kind": "council-runtime-light",
    }

    monkeypatch.setattr(
        isolated_runtime.council_runtime,
        "build_council_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(isolated_runtime.mission_control, "build_council_runtime_surface", lambda: runtime_surface)
    monkeypatch.setattr(isolated_runtime.runtime_self_model, "_council_runtime_surface", lambda: runtime_surface)

    endpoint = isolated_runtime.mission_control.mc_council_runtime()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["recommendation"] == "bounded-check"
    assert runtime["runtime_council_runtime"]["tool_access"] == "none"
    assert self_model["council_runtime"]["council_state"] == "checking"
