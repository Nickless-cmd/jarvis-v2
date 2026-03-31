from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_open_loop(
    db,
    *,
    status: str = "open",
    signal_type: str = "persistent-open-loop",
    canonical_key: str = "open-loop:persistent-open-loop:danish-concise-calibration",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type=signal_type,
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


def _insert_initiative_tension(db, *, intensity: str = "medium") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-{uuid4().hex}",
        signal_type="unresolved",
        canonical_key="private-initiative-tension:unresolved:danish-concise-calibration",
        status="active",
        title="Private initiative tension support: Danish concise calibration",
        summary="Bounded initiative tension is still carrying unresolved pressure.",
        rationale="Validation initiative tension",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="initiative evidence",
        support_summary=f"tension-level={intensity} | source-anchor=initiative-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation initiative tension status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_regulation(db, *, pressure: str = "medium") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-{uuid4().hex}",
        signal_type="effort-regulation",
        canonical_key="regulation-homeostasis:effort-regulation:danish-concise-calibration",
        status="active",
        title="Regulation support: Danish concise calibration",
        summary="Bounded regulation pressure remains present.",
        rationale="Validation regulation",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation evidence",
        support_summary=f"regulation-pressure={pressure} | source-anchor=regulation-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation regulation status",
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


def _insert_witness(db, *, persistence_state: str = "persistent") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:danish-concise-calibration",
        status="carried",
        title="Witnessed turn: Danish concise calibration",
        summary="A bounded turn now looks carried.",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="witness evidence",
        support_summary=f"persistence-state={persistence_state} | source-anchor=witness-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_chronicle_brief(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-{uuid4().hex}",
        brief_type="continuity-brief",
        canonical_key="chronicle-consolidation-brief:continuity-brief:danish-concise-calibration",
        status="active",
        title="Chronicle brief: Danish concise calibration",
        summary="Bounded chronicle brief is holding danish concise calibration as a small continuity candidate.",
        rationale="Validation chronicle brief",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="chronicle brief evidence",
        support_summary=f"brief-weight={weight} | source-anchor=chronicle-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation chronicle brief status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_attachment_topology(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_attachment_topology_signal(
        signal_id=f"attachment-{uuid4().hex}",
        signal_type="attachment-topology",
        canonical_key="attachment-topology:attachment-central:danish-concise-calibration",
        status="active",
        title="Attachment topology: Danish concise calibration",
        summary="Attachment topology is holding a central carried thread.",
        rationale="Validation attachment topology",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="attachment evidence",
        support_summary=(
            "attachment-state=attachment-central | attachment-focus=danish concise calibration | "
            f"attachment-weight={weight} | attachment-confidence=high | source-anchor=attachment-anchor"
        ),
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation attachment topology status",
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


def _insert_runtime_awareness(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_awareness_signal(
        signal_id=f"awareness-{uuid4().hex}",
        signal_type="visible-local-runtime",
        canonical_key="runtime-awareness:visible-local-runtime",
        status="constrained",
        title="Visible local model lane is constrained",
        summary="Visible local runtime is constrained.",
        rationale="Validation runtime awareness",
        source_kind="runtime-health",
        confidence="high",
        evidence_summary="runtime awareness evidence",
        support_summary="source-anchor=runtime-awareness-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation awareness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_runtime_awareness_ready(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_awareness_signal(
        signal_id=f"awareness-ready-{uuid4().hex}",
        signal_type="visible-local-runtime",
        canonical_key="runtime-awareness:visible-local-runtime",
        status="active",
        title="Visible local model lane is ready",
        summary="Visible local runtime is ready.",
        rationale="Validation runtime awareness ready",
        source_kind="runtime-health",
        confidence="high",
        evidence_summary="runtime awareness ready evidence",
        support_summary="source-anchor=runtime-awareness-ready-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation awareness ready status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_open_loop_closure_proposal(db) -> None:
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
        confidence="high",
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


def _insert_release_marker(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_release_marker_signal(
        signal_id=f"release-{uuid4().hex}",
        signal_type="release-marker",
        canonical_key="release-marker:danish-concise-calibration",
        status="softening",
        title="Release marker: Danish concise calibration",
        summary="Release marker is leaning toward release.",
        rationale="Validation release marker",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="release marker evidence",
        support_summary="release-state=release-leaning | release-weight=medium | source-anchor=release-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation release marker status",
        run_id="test-run",
        session_id="test-session",
    )


def test_autonomy_pressure_stays_empty_without_relevant_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    result = tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0


def test_autonomy_pressure_forms_as_bounded_non_authoritative_runtime_support(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_open_loop(db)
    _insert_initiative_tension(db)
    _insert_regulation(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_attachment_topology(db)
    _insert_loyalty_gradient(db)
    _insert_runtime_awareness(db)
    _insert_open_loop_closure_proposal(db)
    _insert_release_marker(db)

    result = tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)
    types = {item["autonomy_pressure_type"] for item in surface["items"]}

    assert result["created"] == 4
    assert surface["active"] is True
    assert types == {
        "initiative-pressure",
        "question-pressure",
        "anomaly-report-pressure",
        "closure-pressure",
    }
    for item in surface["items"]:
        assert item["autonomy_pressure_state"]
        assert item["autonomy_pressure_weight"] in {"medium", "high"}
        assert item["autonomy_pressure_confidence"] in {"medium", "high"}
        assert item["authority"] == "non-authoritative"
        assert item["planner_authority_state"] == "not-planner-authority"
        assert item["proactive_execution_state"] == "not-proactive-execution"
        assert item["canonical_intention_state"] == "not-canonical-intention-truth"
        assert item["prompt_inclusion_state"] == "not-prompt-included"
        assert item["workflow_bridge_state"] == "not-workflow-bridge"
    assert db.runtime_contract_file_write_counts() == {}


def test_autonomy_pressure_surface_is_exposed_in_mission_control_runtime(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_open_loop(db)
    _insert_initiative_tension(db)
    _insert_regulation(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_attachment_topology(db)
    _insert_runtime_awareness(db)
    _insert_open_loop_closure_proposal(db)

    tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    development = mission_control.mc_jarvis()["development"]["autonomy_pressure_signals"]
    runtime = mission_control.mc_runtime()["runtime_autonomy_pressure_signals"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert runtime["summary"]["planner_authority_state"] == "not-planner-authority"
    assert runtime["summary"]["proactive_execution_state"] == "not-proactive-execution"
    assert runtime["summary"]["canonical_intention_state"] == "not-canonical-intention-truth"
    assert runtime["summary"]["prompt_inclusion_state"] == "not-prompt-included"
    assert runtime["summary"]["workflow_bridge_state"] == "not-workflow-bridge"


def test_autonomy_question_pressure_can_be_carried_by_witness_chronicle_and_attachment(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_witness(db)
    _insert_chronicle_brief(db)
    _insert_attachment_topology(db)

    tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)

    question_pressure = next(
        item
        for item in surface["items"]
        if item["autonomy_pressure_type"] == "question-pressure"
    )
    assert question_pressure["autonomy_pressure_continuity_mode"] == "carried-bonded-continuity"
    assert surface["summary"]["current_continuity_mode"] in {
        "carried-bonded-continuity",
        "hybrid-continuity",
    }


def test_autonomy_question_pressure_forms_from_initiative_loop_continuity_without_relation_meaning(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_open_loop(db)
    _insert_initiative_tension(db, intensity="low")
    _insert_regulation(db, pressure="low")
    _insert_runtime_awareness_ready(db)

    result = tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)

    question_pressure = next(
        item
        for item in surface["items"]
        if item["autonomy_pressure_type"] == "question-pressure"
    )
    assert result["created"] == 2
    assert question_pressure["autonomy_pressure_continuity_mode"] == "initiative-loop-continuity"
    assert question_pressure["autonomy_pressure_weight"] in {"medium", "high"}
    assert question_pressure["autonomy_pressure_state"] in {"question-emerging", "question-worthy"}


def test_autonomy_question_pressure_forms_from_strong_initiative_with_open_loops_without_regulation_or_awareness(
    isolated_runtime,
) -> None:
    """When initiative tension is medium+ and open loops exist, question-pressure
    should form even without regulation or awareness — the 3-of-4 threshold
    allows initiative intensity to substitute for the missing runtime support."""
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_open_loop(db)
    _insert_initiative_tension(db, intensity="medium")

    result = tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)
    types = {item["autonomy_pressure_type"] for item in surface["items"]}

    assert "initiative-pressure" in types
    assert "question-pressure" in types
    question_pressure = next(
        item for item in surface["items"]
        if item["autonomy_pressure_type"] == "question-pressure"
    )
    assert question_pressure["autonomy_pressure_continuity_mode"] == "initiative-loop-continuity"
    assert question_pressure["autonomy_pressure_weight"] in {"medium", "high"}
    assert question_pressure["authority"] == "non-authoritative"
    assert question_pressure["planner_authority_state"] == "not-planner-authority"


def _insert_low_initiative_tension(db) -> None:
    """Insert initiative tension with retention-pull type, which produces
    tension_level=low in _with_surface_view (unlike unresolved which gives medium)."""
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-low-{uuid4().hex}",
        signal_type="retention-pull",
        canonical_key="private-initiative-tension:retention-pull:low-test",
        status="active",
        title="Private initiative tension support: Low intensity test",
        summary="Bounded initiative tension is carrying a light pull.",
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


def test_autonomy_question_pressure_does_not_form_from_low_initiative_without_runtime_support(
    isolated_runtime,
) -> None:
    """Low-intensity initiative tension (retention-pull) with open loops but
    without regulation or awareness should NOT produce question-pressure."""
    db = isolated_runtime.db
    tracking = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_open_loop(db)
    _insert_low_initiative_tension(db)

    result = tracking.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_autonomy_pressure_signal_surface(limit=8)
    types = {item["autonomy_pressure_type"] for item in surface["items"]}

    assert "initiative-pressure" in types
    assert "question-pressure" not in types
