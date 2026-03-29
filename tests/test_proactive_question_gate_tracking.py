from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_autonomy_question_pressure(db, *, weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_autonomy_pressure_signal(
        signal_id=f"autonomy-pressure-{uuid4().hex}",
        signal_type="autonomy-pressure",
        canonical_key="autonomy-pressure:question-pressure",
        status="active",
        title="Autonomy pressure: question carry",
        summary="Bounded autonomy pressure is carrying question-worthiness.",
        rationale="Validation autonomy pressure",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="question pressure evidence",
        support_summary=(
            "autonomy-pressure-state=question-worthy | autonomy-pressure-type=question-pressure | "
            f"autonomy-pressure-weight={weight} | autonomy-pressure-confidence=high | source-anchor=autonomy-anchor"
        ),
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation autonomy pressure status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_question_loop(db, *, readiness: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_proactive_loop_lifecycle_signal(
        signal_id=f"question-loop-{uuid4().hex}",
        signal_type="proactive-loop-lifecycle",
        canonical_key="proactive-loop-lifecycle:question-loop:danish-concise-calibration",
        status="active",
        title="Proactive loop lifecycle: Danish concise calibration",
        summary="Bounded proactive-loop lifecycle is carrying a question-capable thread.",
        rationale="Validation proactive loop lifecycle",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="question loop evidence",
        support_summary=(
            "loop-state=loop-question-worthy | loop-kind=question-loop | loop-focus=danish concise calibration | "
            f"loop-weight=high | loop-confidence=high | question-readiness={readiness} | closure-readiness=low | source-anchor=loop-anchor"
        ),
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation proactive loop lifecycle status",
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


def _insert_runtime_awareness_constraint(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_awareness_signal(
        signal_id=f"awareness-{uuid4().hex}",
        signal_type="visible-local-runtime",
        canonical_key="runtime-awareness:visible-local-runtime",
        status="constrained",
        title="Visible local model lane is constrained",
        summary="Visible runtime is constrained.",
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


def test_proactive_question_gate_stays_empty_without_question_loop_and_pressure(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.proactive_question_gate_tracking

    result = tracking.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_question_gate_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0


def test_proactive_question_gate_forms_as_bounded_candidate_only_runtime_support(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_question_gate_tracking

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_loyalty_gradient(db)

    result = tracking.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_question_gate_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    item = surface["items"][0]
    assert item["question_gate_state"] in {"question-gated-candidate", "question-gated-hold"}
    assert item["question_gate_weight"] in {"medium", "high"}
    assert item["question_gate_confidence"] in {"medium", "high"}
    assert item["send_permission_state"] in {"gated-candidate-only", "not-granted"}
    assert item["authority"] == "non-authoritative"
    assert item["proactive_execution_state"] == "not-proactive-execution"
    assert item["planner_authority_state"] == "not-planner-authority"
    assert surface["summary"]["current_send_permission_state"] in {"gated-candidate-only", "not-granted"}
    assert db.runtime_contract_file_write_counts() == {}


def test_proactive_question_gate_downweights_under_runtime_constraint(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_question_gate_tracking

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)
    _insert_runtime_awareness_constraint(db)

    tracking.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_question_gate_surface(limit=8)

    item = surface["items"][0]
    assert item["question_gate_reason"] == "runtime-constrained"
    assert item["send_permission_state"] == "not-granted"


def test_proactive_question_gate_surface_is_exposed_in_mission_control_runtime(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_question_gate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)

    tracking.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    development = mission_control.mc_jarvis()["development"]["proactive_question_gates"]
    runtime = mission_control.mc_runtime()["runtime_proactive_question_gates"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert runtime["summary"]["planner_authority_state"] == "not-planner-authority"
    assert runtime["summary"]["proactive_execution_state"] == "not-proactive-execution"
    assert runtime["summary"]["current_send_permission_state"] in {"gated-candidate-only", "not-granted"}


def test_proactive_question_gate_accepts_carried_bonded_continuity_without_relation_meaning(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.proactive_question_gate_tracking

    _insert_autonomy_question_pressure(db)
    _insert_question_loop(db)
    _insert_witness(db)
    _insert_chronicle_brief(db)
    _insert_attachment_topology(db)

    tracking.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_proactive_question_gate_surface(limit=8)

    item = surface["items"][0]
    assert item["question_gate_continuity_mode"] == "carried-bonded-continuity"
    assert item["question_gate_reason"] == "carried-context"
    assert surface["summary"]["current_continuity_mode"] == "carried-bonded-continuity"
