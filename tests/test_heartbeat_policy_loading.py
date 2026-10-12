from __future__ import annotations

from datetime import UTC, datetime


def test_heartbeat_hjem_er_shared_og_ikke_en_brugers_workspace(isolated_runtime) -> None:
    """12/10-2026 (Bjørn): «heartbeat er ikk kun en bruger.. det er dig».

    Målt før fixet: heartbeat-loopen er GLOBAL, men stien fulgte
    `ensure_default_workspace()`, som er kontekstafhængig. Resultatet var ni
    spredte HEARTBEAT_STATE.json — `workspaces/t/` blev skrevet 12/10 06:41,
    og `t` er ikke engang en bruger i users.json. Det var ikke
    per-bruger-isolation; det var splittelse.

    Kontrakten: heartbeatets tilstand og policy bor i shared/, uanset hvem
    der er aktiv. Testen fejler hvis nogen binder dem til en bruger igen.
    """
    from core.runtime.workspace_paths import (
        heartbeat_home,
        heartbeat_policy_path,
        heartbeat_state_path,
        shared_dir,
    )

    assert heartbeat_home() == shared_dir()
    assert heartbeat_state_path() == shared_dir() / "runtime" / "HEARTBEAT_STATE.json"
    assert heartbeat_policy_path() == shared_dir() / "HEARTBEAT.md"


def test_heartbeat_stien_flytter_sig_ikke_naar_en_anden_bruger_er_aktiv(
    isolated_runtime,
) -> None:
    """Den skarpe del: stien må ikke afhænge af brugerkonteksten.

    Uden dette kunne et run i Michelles session skrive heartbeatets tilstand
    til hendes workspace — mens loopen er global. Det er præcis den fejl der
    gav ni spredte filer.
    """
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime.workspace_paths import heartbeat_state_path

    foer = heartbeat_state_path()
    token = set_context(user_id="1313522677369143429", workspace_name="michelle")
    try:
        efter = heartbeat_state_path()
    finally:
        reset_context(token)

    assert foer == efter, (
        "heartbeat-stien flyttede sig da brugerkonteksten skiftede — "
        "den er bundet til en bruger igen"
    )


def test_et_tik_skaber_ikke_en_workspace_mappe(isolated_runtime, tmp_path) -> None:
    """12/10-2026: `tick_with_phases(name="t")` skabte `workspaces/t/`.

    Målt: mappen stod med 16 filer og frisk mtime hver gang testsuiten kørte,
    og `t` er ikke en bruger i users.json. Årsagen var `record_phased_tick`s
    `ensure_default_workspace(name=name)` — resultatet endte i en parameter
    som state-skriveren ignorerer, så kaldet skabte en mappe ingen brugte.

    Kontrakten: et tik bootstrapper ALDRIG et workspace. Testen fejler hvis
    nogen fører `ensure_default_workspace` tilbage i tik-vejen.
    """
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    heartbeat_runtime.record_phased_tick(
        name="t",
        trigger="test",
        result={"phases": {"act": {"kind": "productive_idle"}, "reflect": {}}},
    )

    from core.runtime.workspace_paths import heartbeat_state_path

    assert heartbeat_state_path().exists(), (
        "tikket skrev ingen tilstand — så er der intet målt"
    )
    assert not (tmp_path / "workspaces" / "t").exists(), (
        "et tik skabte en workspace-mappe — heartbeatets hjem er shared/, "
        "ikke en mappe pr. navn"
    )


def test_load_heartbeat_policy_reads_ping_fields_from_workspace_file(
    isolated_runtime,
) -> None:
    # 12/10-2026: policyen læses nu fra shared/ (Jarvis' egen rytme), ikke fra
    # en brugers workspace. Testen skriver derfor filen hvor systemet læser.
    from core.runtime.workspace_paths import heartbeat_policy_path
    hb = heartbeat_policy_path()
    hb.parent.mkdir(parents=True, exist_ok=True)
    hb.write_text(
        "status: enabled\n"
        "interval minutes: 15\n"
        "allow propose: true\n"
        "allow execute: true\n"
        "allow ping: true\n"
        "ping channel: webchat\n"
        "kill switch: enabled\n",
        encoding="utf-8",
    )
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    policy = heartbeat_runtime.load_heartbeat_policy()

    assert policy["present"] is True
    assert policy["enabled"] is True
    assert policy["allow_propose"] is True
    assert policy["allow_execute"] is True
    assert policy["allow_ping"] is True
    assert policy["ping_channel"] == "webchat"
    assert policy["kill_switch"] == "enabled"


def test_heartbeat_runtime_surface_exposes_loaded_ping_policy(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    surface = heartbeat_runtime.heartbeat_runtime_surface()

    assert surface["policy"]["allow_ping"] is True
    assert surface["policy"]["ping_channel"] == "webchat"
    assert surface["policy"]["kill_switch"] == "enabled"
    assert surface["policy"]["heartbeat_file"].endswith("/HEARTBEAT.md")


def test_merge_runtime_state_recomputes_next_tick_at_from_current_policy_interval(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    last_tick_at = "2026-04-01T17:52:52.146944+00:00"
    stale_next_tick_at = "2026-04-01T20:52:52.146944+00:00"

    merged = heartbeat_runtime._merge_runtime_state(
        policy={
            "enabled": True,
            "kill_switch": "enabled",
            "interval_minutes": 15,
            "budget_status": "bounded-internal-only",
            "summary": "interval=15m",
            "workspace": "/tmp/test-heartbeat-workspace",
        },
        persisted={
            **heartbeat_runtime._default_persisted_state(),
            "last_tick_at": last_tick_at,
            "next_tick_at": stale_next_tick_at,
        },
        now=datetime(2026, 4, 1, 18, 0, tzinfo=UTC),
    )

    assert merged["last_tick_at"] == last_tick_at
    assert merged["next_tick_at"] == "2026-04-01T18:07:52.146944+00:00"
    assert merged["due"] is False


def test_build_heartbeat_context_includes_cognitive_frame_without_name_errors(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_candidate_workflows", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "runtime_contract_candidate_counts", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "recent_runtime_contract_file_writes",
        lambda limit=3: [],
    )
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: {"active": False})
    monkeypatch.setattr(heartbeat_runtime, "recent_visible_runs", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "load_workspace_capabilities", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "visible_execution_readiness",
        lambda: {"provider_status": "ready"},
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_liveness_signal",
        lambda merged_state, trigger: {"liveness_state": "quiet", "liveness_score": 0},
    )
    monkeypatch.setattr(heartbeat_runtime.event_bus, "recent", lambda limit=12: [])
    monkeypatch.setattr(heartbeat_runtime, "build_embodied_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_affective_meta_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_epistemic_runtime_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_loop_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_prompt_evolution_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_subagent_ecology_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_council_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_planner_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_reasoning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_dream_influence_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_guided_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_self_system_code_awareness_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_tool_intent_runtime_surface", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_cognitive_frame",
        lambda merged_state: {"mode": {"mode": "watch"}},
    )
    monkeypatch.setattr(heartbeat_runtime, "_build_influence_trace", lambda **kwargs: {})

    context = heartbeat_runtime._build_heartbeat_context(
        policy={
            "allow_execute": False,
            "budget_status": "bounded-internal-only",
            "kill_switch": "enabled",
        },
        merged_state={"due": False, "schedule_status": "idle"},
        trigger="manual",
    )

    assert context["schedule_status"] == "idle"
    assert context["cognitive_frame"] == {"mode": {"mode": "watch"}}


def test_build_heartbeat_context_promotes_private_signal_pressure_into_due_items(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_candidate_workflows", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "runtime_contract_candidate_counts", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "recent_runtime_contract_file_writes", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: {"active": False})
    monkeypatch.setattr(heartbeat_runtime, "recent_visible_runs", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "load_workspace_capabilities", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "visible_execution_readiness", lambda: {"provider_status": "ready"})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_liveness_signal",
        lambda merged_state, trigger: {"liveness_state": "quiet", "liveness_score": 0},
    )
    monkeypatch.setattr(heartbeat_runtime.event_bus, "recent", lambda limit=12: [])
    monkeypatch.setattr(heartbeat_runtime, "build_embodied_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_affective_meta_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_epistemic_runtime_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_loop_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_prompt_evolution_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_subagent_ecology_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_council_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_planner_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_reasoning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_dream_influence_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_guided_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_self_system_code_awareness_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_tool_intent_runtime_surface", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_cognitive_frame",
        lambda merged_state: {
            "mode": {"mode": "watch"},
            "private_signal_pressure": "high",
            "private_signal_items": [
                {"source": "initiative-tension", "summary": "Private initiative tension is high around stalled-work."}
            ],
        },
    )
    monkeypatch.setattr(heartbeat_runtime, "_build_influence_trace", lambda **kwargs: {})

    context = heartbeat_runtime._build_heartbeat_context(
        policy={
            "allow_execute": False,
            "budget_status": "bounded-internal-only",
            "kill_switch": "enabled",
        },
        merged_state={"due": False, "schedule_status": "idle"},
        trigger="manual",
    )

    assert context["private_signal_pressure"] == "high"
    assert any("private signal pressure is high" in item for item in context["due_items"])
    assert any("private signal carry:" in item for item in context["open_loops"])
