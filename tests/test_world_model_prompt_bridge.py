from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _system_text_from_visible_input(visible_model, message: str = "Hello") -> str:
    payload = visible_model._build_visible_input(message, session_id="test-session")
    assert payload[0]["role"] == "system"
    return payload[0]["content"][0]["text"]


def _insert_world_model_signal(db, *, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_world_model_signal(
        signal_id=f"worldmodel-{uuid4().hex}",
        signal_type="workspace-scope-assumption",
        canonical_key="world-model:workspace-scope:jarvis-v2",
        status=status,
        title="Current workspace scope: jarvis-v2",
        summary="Jarvis is carrying a bounded assumption that the active workspace scope is jarvis-v2.",
        rationale="Validation world-model support.",
        source_kind="user-explicit",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation active world-model signal.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _insert_goal_signal(db, *, status: str = "blocked") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key="goal-signal:danish-concise-calibration",
        status=status,
        title="Current direction: Danish concise calibration",
        summary="Current direction: Danish concise calibration",
        rationale="Validation goal support.",
        source_kind="critic-backed",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation blocked goal signal.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _insert_runtime_awareness_signal(db, *, status: str = "constrained") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_awareness_signal(
        signal_id=f"runtime-awareness-{uuid4().hex}",
        signal_type="visible-local-runtime",
        canonical_key="runtime-awareness:visible-local-runtime",
        status=status,
        title="Visible local model lane is constrained",
        summary="Jarvis is currently pointed at a local visible-model runtime, but the lane is constrained.",
        rationale="Validation runtime-awareness support.",
        source_kind="runtime-health",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation constrained runtime-awareness signal.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _insert_reflection_signal(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type="slow-integration",
        canonical_key="reflection-signal:slow-integration:danish-concise-calibration",
        status="integrating",
        title="Slow integration thread: Danish concise calibration",
        summary="Jarvis is carrying a slow integration thread around Danish concise calibration.",
        rationale="Validation reflection support.",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=3,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation integrating reflection.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _insert_self_model(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.record_private_self_model(
        model_id=f"self-model-{uuid4().hex}",
        source="validation",
        identity_focus="bounded runtime truth",
        preferred_work_mode="concise scoped changes",
        recurring_tension="none",
        growth_direction="stay bounded",
        confidence="high",
        created_at=now,
        updated_at=now,
    )


def test_visible_input_omits_world_model_support_block_when_no_relevant_signals_exist(isolated_runtime) -> None:
    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "World-model support signal:" not in system_text


def test_visible_input_includes_small_subordinate_world_model_support_block(isolated_runtime) -> None:
    _insert_world_model_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "World-model support signal:" in system_text
    assert "dominant_world_thread=Current workspace scope: jarvis-v2" in system_text
    assert "world_state=active" in system_text
    assert "world_direction=workspace-scope" in system_text
    assert "world_confidence=high" in system_text
    assert "Use only as subordinate support. Runtime and visible truth outrank it." in system_text


def test_visible_input_world_model_support_block_stays_bounded(isolated_runtime) -> None:
    _insert_world_model_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    world_block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("World-model support signal:")
    )

    assert "evidence_summary" not in world_block
    assert "support_summary" not in world_block
    assert "rationale" not in world_block
    assert "recent_history" not in world_block
    assert "current_signal" not in world_block
    assert "current_status" not in world_block


def test_visible_input_omits_goal_support_block_when_no_relevant_signals_exist(isolated_runtime) -> None:
    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Goal support signal:" not in system_text


def test_visible_input_includes_small_subordinate_goal_support_block(isolated_runtime) -> None:
    _insert_goal_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Goal support signal:" in system_text
    assert "current_goal_direction=Current direction: Danish concise calibration" in system_text
    assert "goal_state=blocked" in system_text
    assert "goal_direction=danish-concise-calibration" in system_text
    assert "goal_confidence=high" in system_text
    assert "Use only as subordinate support. Runtime and visible truth outrank it." in system_text


def test_visible_input_goal_support_block_stays_bounded(isolated_runtime) -> None:
    _insert_goal_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    goal_block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("Goal support signal:")
    )

    assert "evidence_summary" not in goal_block
    assert "support_summary" not in goal_block
    assert "rationale" not in goal_block
    assert "recent_history" not in goal_block
    assert "current_signal" not in goal_block
    assert "current_status" not in goal_block


def test_visible_input_omits_runtime_awareness_support_block_when_no_relevant_signals_exist(isolated_runtime) -> None:
    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Runtime-awareness support signal:" not in system_text


def test_visible_input_includes_small_subordinate_runtime_awareness_support_block(isolated_runtime) -> None:
    _insert_runtime_awareness_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Runtime-awareness support signal:" in system_text
    assert "runtime_state=constrained" in system_text
    assert "runtime_detail=Visible local model lane is constrained" in system_text
    assert "runtime_direction=local-visible-lane" in system_text
    assert "runtime_confidence=high" in system_text
    assert "Use only as subordinate support. Runtime and visible truth outrank it." in system_text


def test_visible_input_runtime_awareness_support_block_stays_bounded(isolated_runtime) -> None:
    _insert_runtime_awareness_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    runtime_block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("Runtime-awareness support signal:")
    )

    assert "evidence_summary" not in runtime_block
    assert "support_summary" not in runtime_block
    assert "rationale" not in runtime_block
    assert "recent_history" not in runtime_block
    assert "current_signal" not in runtime_block
    assert "current_status" not in runtime_block
    assert "machine_state" not in runtime_block
    assert "machine_detail" not in runtime_block


def test_visible_support_blocks_remain_small_subordinate_helper_sections(isolated_runtime) -> None:
    _insert_self_model(isolated_runtime.db)
    _insert_reflection_signal(isolated_runtime.db)
    _insert_world_model_signal(isolated_runtime.db)
    _insert_goal_signal(isolated_runtime.db)
    _insert_runtime_awareness_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    support_blocks = [
        part
        for part in system_text.split("\n\n")
        if part.startswith(
            (
                "Self-model support signal:",
                "Reflection support signal:",
                "World-model support signal:",
                "Goal support signal:",
                "Runtime-awareness support signal:",
            )
        )
    ]

    assert len(support_blocks) == 5
    assert system_text.count("Use only as subordinate support. Runtime and visible truth outrank it.") >= 5
    for block in support_blocks:
        assert "recent_history" not in block
        assert "evidence_summary" not in block
        assert "support_summary" not in block
        assert "rationale" not in block
        assert "summary=" not in block
        assert "current_signal" not in block
        assert "current_status" not in block
        assert "machine_state" not in block
        assert "machine_detail" not in block


def test_visible_input_includes_runtime_self_report_grounding_for_backend_status_query(
    isolated_runtime,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        isolated_runtime.visible_model,
        "visible_execution_readiness",
        lambda: {
            "provider": "ollama",
            "model": "qwen3.5:9b",
            "provider_status": "ready",
            "auth_status": "not-required",
            "live_verified": True,
        },
    )
    _insert_runtime_awareness_signal(isolated_runtime.db, status="constrained")

    system_text = _system_text_from_visible_input(
        isolated_runtime.visible_model,
        "hvad er din backend status?",
    )

    assert "Runtime self-report grounding:" in system_text
    assert "backend_provider=ollama" in system_text
    assert "backend_model=qwen3.5:9b" in system_text
    assert "backend_status=ready" in system_text
    assert "runtime_awareness_state=constrained" in system_text


def test_visible_input_includes_runtime_self_report_grounding_for_open_loop_query(
    isolated_runtime,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        isolated_runtime.visible_model,
        "visible_execution_readiness",
        lambda: {
            "provider": "phase1-runtime",
            "model": "phase1",
            "provider_status": "local-fallback",
            "auth_status": "not-required",
            "live_verified": False,
        },
    )
    now = datetime.now(UTC).isoformat()
    isolated_runtime.db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-self-report-{uuid4().hex}",
        signal_type="open-loop",
        canonical_key="open-loop:open-loop:visible-work",
        status="open",
        title="Open loop: Visible work",
        summary="Bounded open loop is still active.",
        rationale="Validation open loop",
        source_kind="derived-runtime-open-loop",
        confidence="high",
        evidence_summary="open loop evidence",
        support_summary="source-anchor=open-loop-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation open loop status",
        run_id="validation-run",
        session_id="validation-session",
    )

    system_text = _system_text_from_visible_input(
        isolated_runtime.visible_model,
        "har du åbne loops lige nu?",
    )

    assert "Runtime self-report grounding:" in system_text
    assert "open_loop_count=1" in system_text
    assert "open_loop_state=open" in system_text
    assert "open_loop_current=Open loop: Visible work" in system_text


def test_visible_input_self_report_grounding_explicitly_marks_bounded_uncertainty_when_runtime_truth_is_missing(
    isolated_runtime,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        isolated_runtime.visible_model,
        "visible_execution_readiness",
        lambda: {
            "provider": "unknown",
            "model": "unknown",
            "provider_status": "unknown",
            "auth_status": "unknown",
            "live_verified": False,
        },
    )

    system_text = _system_text_from_visible_input(
        isolated_runtime.visible_model,
        "er du sikker, eller gætter du om din aktuelle tilstand?",
    )
    block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("Runtime self-report grounding:")
    )

    assert "open_loop_state=none-recorded" in block
    assert "open_loop_current=none-recorded" in block
    assert "current_runtime_state=none-recorded" in block
    assert "do not invent stronger certainty" in block
    assert "If asked whether you are guessing" in block
