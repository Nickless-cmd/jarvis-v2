from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_internal_opposition_signal(db, *, status: str = "active", canonical_key: str = "internal-opposition:challenge-direction:workspace-search") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_internal_opposition_signal(
        signal_id=f"internal-opposition-signal-{uuid4().hex}",
        signal_type="challenge-direction",
        canonical_key=canonical_key,
        status=status,
        title="Challenge direction: workspace search",
        summary="This bounded direction now looks like it should face internal challenge.",
        rationale="Validation internal opposition support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="internal opposition evidence",
        support_summary="Derived from bounded critic and loop pressure.",
        status_reason="Validation bounded internal opposition support.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_open_loop_signal(db, *, status: str = "open", canonical_key: str = "open-loop:persistent-open-loop:workspace-search") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-signal-{uuid4().hex}",
        signal_type="persistent-open-loop",
        canonical_key=canonical_key,
        status=status,
        title="Open loop: workspace search",
        summary="A bounded loop is still unresolved and carrying live pressure.",
        rationale="Validation open loop support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="Derived from bounded runtime focus and critic pressure.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation bounded open loop support.",
    )


def _insert_self_review_outcome(db, *, status: str = "fresh", canonical_key: str = "self-review-outcome:review-pressure:workspace-search") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_outcome(
        outcome_id=f"self-review-outcome-{uuid4().hex}",
        outcome_type="watch-closely",
        canonical_key=canonical_key,
        status=status,
        title="Self-review outcome: workspace search",
        summary="Bounded self-review suggests this thread should be watched closely.",
        rationale="Validation self review outcome support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self review outcome evidence",
        support_summary="Derived from bounded self-review chain.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation bounded self-review outcome.",
        review_run_id="test-review-run",
        session_id="test-session",
    )


def _insert_private_state_snapshot(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_state_snapshot(
        snapshot_id=f"private-state-snapshot-{uuid4().hex}",
        snapshot_type="private-state-runtime-snapshot",
        canonical_key="private-state-snapshot:steady-pressure:workspace-search",
        status=status,
        title="Private state snapshot: workspace search",
        summary="Bounded runtime private-state snapshot is holding a small inner-state view.",
        rationale="Validation private-state runtime snapshot",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="private state evidence",
        support_summary="Derived only from active bounded inner-layer runtime support signals.",
        status_reason="Validation bounded private-state snapshot.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_initiative_tension_signal(db, *, run_id: str, status: str = "active", tension_type: str = "unresolved") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"private-initiative-tension-signal-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key=f"private-initiative-tension:{tension_type}:workspace-search",
        status=status,
        title="Private initiative tension support: workspace search",
        summary="Bounded runtime initiative tension is carrying current pressure.",
        rationale="Validation initiative tension support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary="Derived from visible work plus bounded runtime support layers.",
        status_reason="Validation bounded initiative tension support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_executive_contradiction_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_executive_contradiction_signal(
        signal_id=f"executive-contradiction-signal-{uuid4().hex}",
        signal_type="executive-contradiction",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded executive contradiction pressure is asking Jarvis not to carry a thread forward blindly.",
        rationale="Validation executive contradiction runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="executive contradiction evidence",
        support_summary="Derived only from internal opposition, open-loop, self-review, and optional bounded inner-state support.",
        status_reason="Validation bounded executive contradiction and not-authorized execution-veto state.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_executive_contradiction_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.executive_contradiction_signal_tracking
    db = isolated_runtime.db

    _insert_internal_opposition_signal(db)

    result = tracking.track_runtime_executive_contradiction_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_executive_contradiction_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_executive_contradiction_forms_bounded_runtime_support_from_existing_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.executive_contradiction_signal_tracking
    db = isolated_runtime.db

    _insert_internal_opposition_signal(db)
    _insert_open_loop_signal(db)
    _insert_self_review_outcome(db)
    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_private_initiative_tension_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_executive_contradiction_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_executive_contradiction_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "executive-contradiction"
    assert item["control_type"] in {"contradiction-pressure", "veto-watch"}
    assert item["control_pressure"] in {"medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["execution_veto_state"] == "not-authorized"
    assert "not yet allowed to directly veto execution" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_executive_contradiction_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.executive_contradiction_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_executive_contradiction_signal(
        db,
        status="active",
        canonical_key="executive-contradiction:contradiction-pressure:workspace-search",
        title="Executive contradiction support: workspace search",
    )
    _insert_executive_contradiction_signal(
        db,
        status="softening",
        canonical_key="executive-contradiction:veto-watch:visible-work",
        title="Executive contradiction support: visible work",
    )
    _insert_executive_contradiction_signal(
        db,
        status="superseded",
        canonical_key="executive-contradiction:contradiction-pressure:archive-focus",
        title="Executive contradiction support: archive focus",
    )

    surface = tracking.build_runtime_executive_contradiction_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["executive_contradiction_signals"]
    runtime_shape = runtime["runtime_executive_contradiction_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_control_type",
        "current_pressure",
        "current_confidence",
        "authority",
        "layer_role",
        "execution_veto_state",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "control_type",
        "control_target",
        "control_pressure",
        "control_summary",
        "control_confidence",
        "source_anchor",
        "execution_veto_state",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["execution_veto_state"] == "not-authorized"
