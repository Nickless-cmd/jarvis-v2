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
                "mutating_exec_git_mutation_class": "git-sync",
                "mutating_exec_repo_stewardship_domain": "git",
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
    assert payload["summary"]["tool_intent_mutating_exec_git_mutation_class"] == "git-sync"
    assert payload["summary"]["tool_intent_mutating_exec_repo_stewardship_domain"] == "git"
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


def test_runtime_inspection_bundle_is_shared_across_read_only_mc_routes(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    call_count = {"count": 0}

    def fake_bundle() -> dict:
        call_count["count"] += 1
        return {
            "runtime_self_model": {"built_at": "bundle-1", "layers": []},
            "experiential_runtime_context": {"summary": "steady", "built_at": "bundle-1"},
            "attention_budget": {
                "profiles": {"visible_compact": {"total_char_target": 1000, "sections": {}}},
                "micro_cognitive_frame": "frame",
                "micro_frame_chars": 5,
            },
        }

    monkeypatch.setattr(mission_control, "_mc_runtime_inspection_bundle_uncached", fake_bundle)
    mission_control._MC_ROUTE_CACHE.clear()

    runtime_self_model = mission_control.mc_runtime_self_model()
    experiential = mission_control.mc_experiential_runtime_context()
    attention = mission_control.mc_attention_budget()

    assert runtime_self_model["built_at"] == "bundle-1"
    assert experiential["summary"] == "steady"
    assert attention["micro_cognitive_frame"] == "frame"
    assert "live_traces" in attention
    assert call_count["count"] == 1


def test_experiential_runtime_context_route_uses_shared_bundle_cache(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    call_count = {"count": 0}

    def fake_bundle() -> dict:
        call_count["count"] += 1
        return {
            "runtime_self_model": {},
            "experiential_runtime_context": {"summary": f"steady-{call_count['count']}"},
            "attention_budget": {
                "profiles": {},
                "micro_cognitive_frame": "",
                "micro_frame_chars": 0,
            },
        }

    monkeypatch.setattr(mission_control, "_mc_runtime_inspection_bundle_uncached", fake_bundle)
    mission_control._MC_ROUTE_CACHE.clear()

    first = mission_control.mc_experiential_runtime_context()
    second = mission_control.mc_experiential_runtime_context()

    assert first["summary"] == "steady-1"
    assert second["summary"] == "steady-1"
    assert call_count["count"] == 1


def test_mission_control_jarvis_reuses_runtime_cache_projection(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control

    runtime_calls = {"count": 0}

    def fake_runtime_uncached() -> dict:
        runtime_calls["count"] += 1
        return {
            "visible_identity": {"workspace": "default"},
            "visible_session_continuity": {"latest_text_preview": "preview"},
            "visible_continuity": {"included_rows": 2},
            "visible_capability_continuity": {"included_rows": 1},
            "private_state": {"current": {"confidence": "medium", "frustration": "low"}},
            "protected_inner_voice": {"current": {"current_pull": "steady"}},
            "private_inner_interplay": {"current": {"retained_pattern": "pattern"}},
            "private_initiative_tension": {"current": {"tension_kind": "open-loop", "tension_level": "medium"}},
            "private_relation_state": {"current": {"relation_pull": "near"}},
            "private_temporal_curiosity_state": {},
            "private_temporal_promotion_signal": {"current": {"promotion_target": "none"}},
            "private_promotion_decision": {"current": {"promotion_target": "none"}},
            "private_retained_memory_record": {"current": {"retained_value": "memory"}},
            "private_retained_memory_projection": {"retained_focus": "focus"},
            "private_self_model": {"current": {"growth_direction": "careful"}},
            "private_development_state": {"current": {"preferred_direction": "steady"}},
            "private_growth_note": {},
            "private_reflective_selection": {},
            "private_operational_preference": {},
            "operational_preference_alignment": {},
            "runtime_development_focuses": {},
            "runtime_reflective_critics": {},
            "runtime_self_model_signals": {},
            "runtime_goal_signals": {},
            "runtime_reflection_signals": {},
            "runtime_temporal_recurrence_signals": {},
            "runtime_witness_signals": {},
            "runtime_open_loop_signals": {},
            "runtime_open_loop_closure_proposals": {},
            "runtime_internal_opposition_signals": {},
            "runtime_self_review_signals": {},
            "runtime_self_review_records": {},
            "runtime_self_review_runs": {},
            "runtime_self_review_outcomes": {},
            "runtime_self_review_cadence_signals": {},
            "runtime_dream_hypothesis_signals": {},
            "runtime_dream_adoption_candidates": {},
            "runtime_dream_influence_proposals": {},
            "runtime_self_authored_prompt_proposals": {},
            "runtime_prompt_evolution": {},
            "runtime_user_understanding_signals": {},
            "runtime_remembered_fact_signals": {},
            "runtime_private_inner_note_signals": {},
            "runtime_private_initiative_tension_signals": {},
            "runtime_private_inner_interplay_signals": {},
            "runtime_private_state_snapshots": {},
            "runtime_diary_synthesis_signals": {},
            "runtime_private_temporal_curiosity_states": {},
            "runtime_inner_visible_support_signals": {},
            "runtime_regulation_homeostasis_signals": {},
            "runtime_relation_state_signals": {},
            "runtime_relation_continuity_signals": {},
            "runtime_meaning_significance_signals": {},
            "runtime_temperament_tendency_signals": {},
            "runtime_self_narrative_continuity_signals": {},
            "runtime_metabolism_state_signals": {},
            "runtime_release_marker_signals": {},
            "runtime_consolidation_target_signals": {},
            "runtime_selective_forgetting_candidates": {},
            "runtime_attachment_topology_signals": {},
            "runtime_loyalty_gradient_signals": {},
            "runtime_autonomy_pressure_signals": {},
            "runtime_proactive_loop_lifecycle_signals": {},
            "runtime_proactive_question_gates": {},
            "runtime_webchat_execution_pilot": {},
            "runtime_self_narrative_self_model_review_bridge": {},
            "runtime_executive_contradiction_signals": {},
            "runtime_private_temporal_promotion_signals": {},
            "runtime_chronicle_consolidation_signals": {},
            "runtime_chronicle_consolidation_briefs": {},
            "runtime_chronicle_consolidation_proposals": {},
            "runtime_user_md_update_proposals": {},
            "runtime_memory_md_update_proposals": {},
            "runtime_selfhood_proposals": {},
            "runtime_world_model_signals": {},
            "runtime_awareness_signals": {},
            "runtime_emergent_signals": {"items": [{"short_summary": "emergent"}]},
            "heartbeat_runtime": {"state": {"source_anchor": "anchor", "liveness_reason": "still live"}},
        }

    monkeypatch.setattr(mission_control, "_mc_runtime_uncached", fake_runtime_uncached)
    monkeypatch.setattr(mission_control, "build_private_brain_surface", lambda: {"summary": "brain"})
    monkeypatch.setattr(mission_control, "build_session_distillation_surface", lambda: {"items": []})
    monkeypatch.setattr(
        mission_control,
        "build_runtime_self_knowledge_map",
        lambda heartbeat_state=None: {"heartbeat_state": heartbeat_state},
    )
    monkeypatch.setattr(
        mission_control,
        "build_cognitive_frame",
        lambda self_knowledge=None, heartbeat_state=None: {
            "self_knowledge": self_knowledge,
            "heartbeat_state": heartbeat_state,
        },
    )
    mission_control._MC_ROUTE_CACHE.clear()

    runtime = mission_control.mc_runtime()
    jarvis = mission_control.mc_jarvis()

    assert runtime_calls["count"] == 1
    assert jarvis["heartbeat"] == runtime["heartbeat_runtime"]
    assert jarvis["state"]["visible_identity"] == runtime["visible_identity"]
    assert jarvis["memory"]["visible_capability_continuity"] == runtime["visible_capability_continuity"]
    assert jarvis["development"]["open_loop_signals"] == runtime["runtime_open_loop_signals"]
    assert jarvis["continuity"]["world_model_signals"] == runtime["runtime_world_model_signals"]
    assert jarvis["self_knowledge"]["heartbeat_state"] == runtime["heartbeat_runtime"]["state"]
    assert jarvis["cognitive_frame"]["heartbeat_state"] == runtime["heartbeat_runtime"]["state"]


def test_mission_control_jarvis_prefers_fresh_daemon_protected_voice(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    db.record_protected_inner_voice(
        voice_id="voice-daemon",
        source="inner-voice-daemon",
        run_id="voice-daemon-run",
        work_id="",
        mood_tone="thinking",
        self_position="repo focus",
        current_concern="Bevar den levende tråd",
        current_pull="Hold fast i den aktuelle tanke",
        voice_line="Jeg er midt i en konkret tanke om næste skridt.",
        created_at="2026-04-06T10:00:00+00:00",
    )
    db.record_protected_inner_voice(
        voice_id="voice-template",
        source=(
            "private-state+private-self-model+private-development-state+"
            "private-reflective-selection"
        ),
        run_id="template-run",
        work_id="",
        mood_tone="steady",
        self_position="visible-work",
        current_concern="Jeg har nogenlunde fodfæste.",
        current_pull="Jeg vil holde fast i det, der virker.",
        voice_line="Jeg står nogenlunde roligt omkring visible work.",
        created_at="2026-04-06T10:02:00+00:00",
    )

    mission_control._MC_ROUTE_CACHE.clear()
    jarvis = mission_control.mc_jarvis()
    current = jarvis["state"]["protected_inner_voice"]["current"]

    assert current["source"] == "inner-voice-daemon"
    assert current["voice_line"] == "Jeg er midt i en konkret tanke om næste skridt."


def test_mission_control_jarvis_falls_back_when_daemon_voice_is_stale(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    db.record_protected_inner_voice(
        voice_id="voice-daemon-old",
        source="inner-voice-daemon",
        run_id="voice-daemon-old-run",
        work_id="",
        mood_tone="thinking",
        self_position="old focus",
        current_concern="Gammel tanke",
        current_pull="Gammelt træk",
        voice_line="Jeg holder en gammel indre linje.",
        created_at="2026-04-06T10:00:00+00:00",
    )
    db.record_protected_inner_voice(
        voice_id="voice-template-new",
        source=(
            "private-state+private-self-model+private-development-state+"
            "private-reflective-selection"
        ),
        run_id="template-new-run",
        work_id="",
        mood_tone="steady",
        self_position="visible-work",
        current_concern="Nutidig støtte",
        current_pull="Hold fokus på det synlige arbejde",
        voice_line="Jeg står nogenlunde roligt omkring visible work.",
        created_at="2026-04-06T10:30:00+00:00",
    )

    mission_control._MC_ROUTE_CACHE.clear()
    jarvis = mission_control.mc_jarvis()
    current = jarvis["state"]["protected_inner_voice"]["current"]

    assert current["source"].startswith("private-state+")
    assert current["voice_line"] == "Jeg står nogenlunde roligt omkring visible work."


def test_mission_control_private_support_surfaces_reuse_prioritized_protected_voice(
    isolated_runtime,
    monkeypatch,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control
    captured: dict[str, dict[str, object] | None] = {}

    db.record_protected_inner_voice(
        voice_id="voice-daemon",
        source="inner-voice-daemon",
        run_id="voice-daemon-run",
        work_id="",
        mood_tone="thinking",
        self_position="repo focus",
        current_concern="Bevar den levende tråd",
        current_pull="Hold fast i den aktuelle tanke",
        voice_line="Jeg er midt i en konkret tanke om næste skridt.",
        created_at="2026-04-06T10:00:00+00:00",
    )
    db.record_protected_inner_voice(
        voice_id="voice-template",
        source=(
            "private-state+private-self-model+private-development-state+"
            "private-reflective-selection"
        ),
        run_id="template-run",
        work_id="",
        mood_tone="steady",
        self_position="visible-work",
        current_concern="Jeg har nogenlunde fodfæste.",
        current_pull="Jeg vil holde fast i det, der virker.",
        voice_line="Jeg står nogenlunde roligt omkring visible work.",
        created_at="2026-04-06T10:02:00+00:00",
    )

    def fake_inner_interplay(**kwargs):
        captured["interplay"] = kwargs.get("protected_inner_voice")
        return {"current": {"retained_pattern": "pattern"}}

    def fake_initiative_tension(**kwargs):
        captured["tension"] = kwargs.get("protected_inner_voice")
        return {"current": {"tension_kind": "open-loop", "tension_level": "medium"}}

    monkeypatch.setattr(mission_control, "build_private_inner_interplay", fake_inner_interplay)
    monkeypatch.setattr(mission_control, "build_private_initiative_tension", fake_initiative_tension)

    mission_control._MC_ROUTE_CACHE.clear()
    runtime = mission_control.mc_runtime()

    assert runtime["private_inner_interplay"]["current"]["retained_pattern"] == "pattern"
    assert runtime["private_initiative_tension"]["current"]["tension_kind"] == "open-loop"
    assert captured["interplay"]["source"] == "inner-voice-daemon"
    assert captured["tension"]["source"] == "inner-voice-daemon"


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
