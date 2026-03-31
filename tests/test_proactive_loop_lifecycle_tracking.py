from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_open_loop(
    db,
    *,
    status: str = "open",
    canonical_key: str = "open-loop:persistent-open-loop:danish-concise-calibration",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type="persistent-open-loop",
        canonical_key=canonical_key,
        status=status,
        title="Open loop: Danish concise calibration",
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
        run_id="test-run",
        session_id="test-session",
    )


def _insert_autonomy_pressure(
    db,
    *,
    pressure_type: str,
    pressure_state: str,
    weight: str = "medium",
    confidence: str = "high",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_autonomy_pressure_signal(
        signal_id=f"autonomy-pressure-{uuid4().hex}",
        signal_type="autonomy-pressure",
        canonical_key=f"autonomy-pressure:{pressure_type}",
        status="active",
        title=f"Autonomy pressure: {pressure_type}",
        summary=f"Bounded autonomy pressure is carrying {pressure_type}.",
        rationale="Validation autonomy pressure",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary=f"{pressure_type} evidence",
        support_summary=(
            f"autonomy-pressure-state={pressure_state} | autonomy-pressure-type={pressure_type} | "
            f"autonomy-pressure-weight={weight} | autonomy-pressure-confidence={confidence} | source-anchor=autonomy-anchor"
        ),
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation autonomy pressure status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_relation_continuity(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key="relation-continuity:carried-thread:danish-concise-calibration",
        status="active",
        title="Relation continuity: Danish concise calibration",
        summary="Relation continuity is still holding weight.",
        rationale="Validation relation continuity",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="relation continuity evidence",
        support_summary=f"continuity-weight={weight} | source-anchor=relation-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation relation continuity status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_meaning(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-{uuid4().hex}",
        signal_type="developmental-significance",
        canonical_key="meaning-significance:developmental-significance:danish-concise-calibration",
        status="active",
        title="Meaning significance: Danish concise calibration",
        summary="Meaning significance is still carried.",
        rationale="Validation meaning significance",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="meaning evidence",
        support_summary=f"meaning-weight={weight} | source-anchor=meaning-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation meaning status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_loyalty_gradient(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_loyalty_gradient_signal(
        signal_id=f"loyalty-{uuid4().hex}",
        signal_type="loyalty-gradient",
        canonical_key="loyalty-gradient:danish-concise-calibration",
        status="active",
        title="Loyalty gradient: Danish concise calibration",
        summary="Loyalty gradient is observing central held weight.",
        rationale="Validation loyalty gradient",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="loyalty evidence",
        support_summary=(
            "gradient-state=loyalty-central | gradient-focus=danish concise calibration | "
            f"gradient-weight={weight} | gradient-confidence=high | source-anchor=loyalty-anchor"
        ),
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation loyalty gradient status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_witness(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type="carried-lesson",
        canonical_key="witness:carried-lesson:danish-concise-calibration",
        status="carried",
        title="Witnessed turn: Danish concise calibration",
        summary="A bounded turn now looks carried.",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="witness evidence",
        support_summary="persistence-state=carried-forward | source-anchor=witness-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_open_loop_closure_proposal(db, *, confidence: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_closure_proposal(
        proposal_id=f"closure-{uuid4().hex}",
        proposal_type="soft-close-review",
        canonical_key="open-loop-closure-proposal:soft-close-review:danish-concise-calibration",
        status="active",
        title="Loop closure proposal: Danish concise calibration",
        summary="Closure proposal is active.",
        rationale="Validation closure proposal",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="closure proposal evidence",
        support_summary="source-anchor=closure-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation closure proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_proactive_loop_lifecycle_stays_empty_without_autonomy_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking

    _insert_open_loop(db)

    result = tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_loop_lifecycle_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0


def test_proactive_loop_lifecycle_forms_as_bounded_non_authoritative_runtime_support(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking

    _insert_open_loop(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_loyalty_gradient(db)
    _insert_witness(db)
    _insert_open_loop_closure_proposal(db)
    _insert_autonomy_pressure(
        db,
        pressure_type="initiative-pressure",
        pressure_state="initiative-held",
        weight="high",
    )
    _insert_autonomy_pressure(
        db,
        pressure_type="question-pressure",
        pressure_state="question-worthy",
        weight="high",
    )
    _insert_autonomy_pressure(
        db,
        pressure_type="closure-pressure",
        pressure_state="closure-worthy",
        weight="high",
    )

    result = tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_loop_lifecycle_surface(limit=8)
    kinds = {item["loop_kind"] for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert kinds == {"initiative-loop", "question-loop", "closure-loop"}
    assert surface["summary"]["planner_authority_state"] == "not-planner-authority"
    assert surface["summary"]["proactive_execution_state"] == "not-proactive-execution"
    assert surface["summary"]["canonical_intention_state"] == "not-canonical-intention-truth"
    for item in surface["items"]:
        assert item["loop_state"]
        assert item["loop_focus"]
        assert item["loop_weight"] in {"medium", "high"}
        assert item["loop_confidence"] in {"medium", "high"}
        assert item["question_readiness"] in {"low", "medium", "high"}
        assert item["closure_readiness"] in {"low", "medium", "high"}
        assert item["authority"] == "non-authoritative"
        assert item["planner_authority_state"] == "not-planner-authority"
        assert item["proactive_execution_state"] == "not-proactive-execution"
    assert db.runtime_contract_file_write_counts() == {}


def test_proactive_loop_lifecycle_surface_is_exposed_in_mission_control_runtime(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking
    mission_control = isolated_runtime.mission_control

    _insert_open_loop(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_autonomy_pressure(
        db,
        pressure_type="question-pressure",
        pressure_state="question-worthy",
        weight="high",
    )

    tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    development = mission_control.mc_jarvis()["development"]["proactive_loop_lifecycle_signals"]
    runtime = mission_control.mc_runtime()["runtime_proactive_loop_lifecycle_signals"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert runtime["summary"]["planner_authority_state"] == "not-planner-authority"
    assert runtime["summary"]["proactive_execution_state"] == "not-proactive-execution"
    assert runtime["summary"]["prompt_inclusion_state"] == "not-prompt-included"
    assert runtime["summary"]["workflow_bridge_state"] == "not-workflow-bridge"


def test_proactive_loop_lifecycle_prefers_meaningful_open_loop_focus_over_none(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking

    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-focus-{uuid4().hex}",
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
        run_id="test-run",
        session_id="test-session",
    )
    _insert_autonomy_pressure(
        db,
        pressure_type="question-pressure",
        pressure_state="question-worthy",
        weight="high",
    )

    tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_loop_lifecycle_surface(limit=8)

    item = next(item for item in surface["items"] if item["loop_kind"] == "question-loop")
    assert item["loop_focus"] == "Visible work"


def _insert_initiative_tension(db, *, intensity: str = "medium") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-tension-{uuid4().hex}",
        signal_type="unresolved",
        canonical_key="private-initiative-tension:unresolved:proactive-test-thread",
        status="active",
        title="Private initiative tension support: Proactive test thread",
        summary="Bounded initiative tension is still carrying unresolved pressure.",
        rationale="Validation initiative tension",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary=f"tension-level={intensity} | source-anchor=initiative-tension-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation initiative tension status",
        run_id="test-run",
        session_id="test-session",
    )


def test_proactive_loop_materializes_from_initiative_tension_without_open_loops(
    isolated_runtime,
) -> None:
    """When initiative tension is active with medium+ intensity and autonomy
    pressure exists, a proactive loop should materialize even without formal
    open loops."""
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking

    # Insert initiative tension (medium intensity) + autonomy pressure, but NO open loop
    _insert_initiative_tension(db, intensity="medium")
    _insert_autonomy_pressure(
        db,
        pressure_type="initiative-pressure",
        pressure_state="initiative-held",
        weight="medium",
    )

    result = tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_loop_lifecycle_surface(limit=8)

    assert result["created"] >= 1
    assert surface["active"] is True
    kinds = {item["loop_kind"] for item in surface["items"]}
    assert "initiative-loop" in kinds
    for item in surface["items"]:
        assert item["authority"] == "non-authoritative"
        assert item["planner_authority_state"] == "not-planner-authority"
        assert item["proactive_execution_state"] == "not-proactive-execution"


def test_proactive_loop_does_not_materialize_from_low_intensity_tension(
    isolated_runtime,
) -> None:
    """Low-intensity initiative tension should NOT trigger tension-driven
    materialization — the threshold requires medium or high."""
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_loop_lifecycle_tracking

    # Insert initiative tension with LOW intensity (via focus-based, not unresolved)
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-tension-low-{uuid4().hex}",
        signal_type="retention-pull",
        canonical_key="private-initiative-tension:retention-pull:low-test",
        status="active",
        title="Private initiative tension support: Low intensity test",
        summary="Bounded initiative tension is carrying low pressure.",
        rationale="Validation",
        source_kind="runtime-derived-support",
        confidence="low",
        evidence_summary="low initiative evidence",
        support_summary="tension-level=low | source-anchor=low-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation",
        run_id="test-run",
        session_id="test-session",
    )
    _insert_autonomy_pressure(
        db,
        pressure_type="initiative-pressure",
        pressure_state="initiative-held",
        weight="medium",
    )

    result = tracking.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_loop_lifecycle_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
