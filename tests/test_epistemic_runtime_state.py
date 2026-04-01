from __future__ import annotations


def test_epistemic_runtime_state_builds_bounded_state_from_runtime_inputs(isolated_runtime) -> None:
    epistemic = isolated_runtime.epistemic_runtime_state

    surface = epistemic.build_epistemic_runtime_state_from_sources(
        conflict_trace={
            "outcome": "defer",
            "blocked_by": "policy-gate",
            "reason_code": "policy-blocked",
        },
        deception_guard={
            "has_blocks": True,
            "has_reframes": True,
            "capability_state": "gated",
            "permission_state": "not-granted",
        },
        affective_meta_state={
            "state": "burdened",
            "bearing": "compressed",
            "monitoring_mode": "strain-watch",
        },
        embodied_state={
            "state": "strained",
            "strain_level": "high",
            "recovery_state": "steady",
        },
        loop_runtime={
            "summary": {
                "loop_count": 2,
                "current_status": "standby",
                "active_count": 0,
                "standby_count": 2,
            }
        },
        emergent_signal={
            "active": True,
            "summary": {"active_count": 1, "current_signal": "Unresolved pressure still live"},
        },
        quiet_initiative={"active": True, "state": "holding", "hold_count": 2},
    )

    assert surface["wrongness_state"] == "strained"
    assert surface["regret_signal"] == "active"
    assert surface["counterfactual_mode"] == "blocked-path"
    assert surface["confidence"] == "high"
    assert surface["authority"] == "derived-runtime-truth"
    assert surface["visibility"] == "internal-only"
    assert surface["boundary"] == "not-memory-not-identity-not-action"
    assert surface["kind"] == "epistemic-runtime-state"
    assert surface["seam_usage"]["heartbeat_prompt_grounding"] is True


def test_epistemic_prompt_section_includes_guidance(isolated_runtime) -> None:
    epistemic = isolated_runtime.epistemic_runtime_state

    section = epistemic.build_epistemic_runtime_prompt_section(
        {
            "wrongness_state": "off",
            "regret_signal": "slight",
            "counterfactual_mode": "nearby-alternative",
            "counterfactual_hint": "choose-nearer-lower-claim",
            "confidence": "medium",
            "freshness": {"state": "fresh"},
            "source_contributors": [
                {"source": "self-deception-guard", "signal": "reframes / capability=gated / permission=not-granted"},
                {"source": "conflict-resolution", "signal": "quiet_hold / reason=question-gate-live"},
            ],
        }
    )

    assert "Epistemic state" in section
    assert "wrongness=off" in section
    assert "regret=slight" in section
    assert "counterfactual=nearby-alternative" in section
    assert "Treat the off-sense as bounded evidence" in section


def test_heartbeat_self_knowledge_section_includes_epistemic_guidance(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    monkeypatch.setattr(
        isolated_runtime.epistemic_runtime_state,
        "build_epistemic_runtime_prompt_section",
        lambda surface=None: (
            "Epistemic state (derived runtime truth, internal-only):\n"
            "- wrongness=uneasy | regret=slight | counterfactual=missed-timing | confidence=medium | freshness=fresh\n"
            "- guidance=Keep a small counterfactual in view while carrying forward carefully."
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Epistemic state (derived runtime truth, internal-only):" in section
    assert "wrongness=uneasy" in section
    assert "Keep a small counterfactual in view while carrying forward carefully." in section


def test_mission_control_runtime_and_endpoint_expose_epistemic_state(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "wrongness_state": "off",
        "regret_signal": "slight",
        "counterfactual_mode": "nearby-alternative",
        "counterfactual_hint": "choose-nearer-lower-claim",
        "confidence": "medium",
        "summary": "off epistemic state with slight regret and nearby-alternative counterfactual mode",
        "source_contributors": [
            {"source": "conflict-resolution", "signal": "defer / reason=policy-blocked"},
            {"source": "self-deception-guard", "signal": "reframes / capability=gated / permission=not-granted"},
        ],
        "freshness": {"built_at": "2026-04-01T20:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "epistemic-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.epistemic_runtime_state,
        "build_epistemic_runtime_state_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(isolated_runtime.mission_control, "build_epistemic_runtime_state_surface", lambda: runtime_surface)
    monkeypatch.setattr(isolated_runtime.runtime_self_model, "_epistemic_runtime_state_surface", lambda: runtime_surface)

    endpoint = isolated_runtime.mission_control.mc_epistemic_runtime_state()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["wrongness_state"] == "off"
    assert runtime["runtime_epistemic_state"]["counterfactual_mode"] == "nearby-alternative"
    assert runtime["runtime_epistemic_state"]["visibility"] == "internal-only"
    assert self_model["epistemic_runtime_state"]["regret_signal"] == "slight"
