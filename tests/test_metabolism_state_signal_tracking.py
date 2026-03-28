from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_witness_signal(db, *, canonical_key: str, status: str = "carried", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type="carried-lesson",
        canonical_key=canonical_key,
        status=status,
        title="Carried lesson: Danish concise calibration",
        summary="Witness summary",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="witness evidence",
        support_summary="becoming-direction=steadying | metabolism anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_meaning_signal(db, *, focus: str, status: str = "active", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-{uuid4().hex}",
        signal_type="meaning-significance",
        canonical_key=f"meaning-significance:developmental-significance:{focus}",
        status=status,
        title=f"Meaning significance support: {focus.replace('-', ' ')}",
        summary="Meaning summary",
        rationale="Validation meaning",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="meaning evidence",
        support_summary="grounding-mode=test | meaning support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation meaning status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_temperament_signal(db, *, focus: str, status: str = "active", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_temperament_tendency_signal(
        signal_id=f"temperament-{uuid4().hex}",
        signal_type="temperament-tendency",
        canonical_key=f"temperament-tendency:steadiness:{focus}",
        status=status,
        title=f"Temperament support: {focus.replace('-', ' ')}",
        summary="Temperament summary",
        rationale="Validation temperament",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="temperament evidence",
        support_summary="grounding-mode=test | temperament support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation temperament status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_self_narrative_signal(db, *, focus: str, status: str = "active", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_narrative_continuity_signal(
        signal_id=f"self-narrative-{uuid4().hex}",
        signal_type="self-narrative-continuity",
        canonical_key=f"self-narrative-continuity:becoming-steady:{focus}",
        status=status,
        title=f"Self-narrative support: {focus.replace('-', ' ')}",
        summary="Self-narrative summary",
        rationale="Validation self narrative",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="self narrative evidence",
        support_summary="grounding-mode=test | narrative-direction=deepening | narrative-weight=high | self narrative anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation self-narrative status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_chronicle_signal(db, *, focus: str, status: str = "active", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_signal(
        signal_id=f"chronicle-{uuid4().hex}",
        signal_type="chronicle-consolidation",
        canonical_key=f"chronicle-consolidation:carried-thread:{focus}",
        status=status,
        title=f"Chronicle consolidation support: {focus.replace('-', ' ')}",
        summary="Chronicle summary",
        rationale="Validation chronicle",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="chronicle evidence",
        support_summary="grounding-mode=test | chronicle support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation chronicle status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_relation_continuity_signal(db, *, focus: str, status: str = "active", run_id: str = "test-run") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key=f"relation-continuity:carried-alignment:{focus}",
        status=status,
        title=f"Relation continuity support: {focus.replace('-', ' ')}",
        summary="Relation continuity summary",
        rationale="Validation relation continuity",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation continuity evidence",
        support_summary="grounding-mode=test | relation continuity support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation relation continuity status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_metabolism_state_signal(db, *, status: str, canonical_key: str, title: str, support_summary: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_metabolism_state_signal(
        signal_id=f"metabolism-{uuid4().hex}",
        signal_type="metabolism-state",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Metabolism summary",
        rationale="Validation metabolism",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="metabolism evidence",
        support_summary=support_summary,
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation metabolism status",
        run_id="test-run",
        session_id="test-session",
    )


def test_metabolism_state_stays_empty_without_relevant_lifecycle_substrate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.metabolism_state_signal_tracking

    _insert_meaning_signal(db, focus="danish-concise-calibration")

    result = tracking.track_runtime_metabolism_state_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_metabolism_state_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0


def test_metabolism_state_forms_bounded_runtime_support_from_existing_lifecycle_patterns(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.metabolism_state_signal_tracking
    focus = "danish-concise-calibration"

    _insert_witness_signal(
        db,
        canonical_key=f"witness-signal:carried-lesson:{focus}",
        status="carried",
    )
    _insert_meaning_signal(db, focus=focus, status="active")
    _insert_temperament_signal(db, focus=focus, status="active")
    _insert_self_narrative_signal(db, focus=focus, status="active")
    _insert_chronicle_signal(db, focus=focus, status="active")
    _insert_relation_continuity_signal(db, focus=focus, status="softening")

    result = tracking.track_runtime_metabolism_state_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_metabolism_state_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["metabolism_state"] in {
        "active-retaining",
        "consolidating",
        "releasing",
        "metabolizing",
    }
    assert item["metabolism_direction"] in {
        "settling-in",
        "bleeding-out",
        "carrying-forward",
        "holding-shape",
        "transitioning",
        "circulating",
    }
    assert item["metabolism_weight"] in {"low", "medium", "high"}
    assert item["metabolism_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_delete_state"] == "not-canonical-deletion"
    assert item["self_erasure_state"] == "not-self-erasure"
    assert "appears to be" in item["metabolism_summary"] or "shows signs of" in item["metabolism_summary"]


def test_metabolism_state_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.metabolism_state_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_metabolism_state_signal(
        db,
        status="active",
        canonical_key="metabolism-state:active-retaining:danish-concise-calibration",
        title="Metabolism support: Danish concise calibration",
        support_summary="metabolism-state=active-retaining | metabolism-direction=carrying-forward | metabolism-weight=high | metabolism anchor",
    )
    _insert_metabolism_state_signal(
        db,
        status="softening",
        canonical_key="metabolism-state:releasing:workspace-boundary",
        title="Metabolism support: Workspace boundary",
        support_summary="metabolism-state=releasing | metabolism-direction=bleeding-out | metabolism-weight=medium | metabolism anchor",
    )
    _insert_metabolism_state_signal(
        db,
        status="stale",
        canonical_key="metabolism-state:metabolizing:runtime-lane",
        title="Metabolism support: Runtime lane",
        support_summary="metabolism-state=metabolizing | metabolism-direction=transitioning | metabolism-weight=low | metabolism anchor",
    )
    _insert_metabolism_state_signal(
        db,
        status="superseded",
        canonical_key="metabolism-state:consolidating:older-thread",
        title="Metabolism support: Older thread",
        support_summary="metabolism-state=consolidating | metabolism-direction=settling-in | metabolism-weight=medium | metabolism anchor",
    )

    surface = tracking.build_runtime_metabolism_state_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["metabolism_state_signals"]
    runtime_shape = runtime["runtime_metabolism_state_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_direction",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_delete_state",
        "self_erasure_state",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "metabolism_state",
        "metabolism_direction",
        "metabolism_weight",
        "metabolism_summary",
        "metabolism_confidence",
        "authority",
        "layer_role",
        "canonical_delete_state",
        "self_erasure_state",
        "updated_at",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["canonical_delete_state"] == "not-canonical-deletion"
    assert runtime_shape["summary"]["self_erasure_state"] == "not-self-erasure"
