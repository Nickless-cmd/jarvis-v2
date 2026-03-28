from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_chronicle_consolidation_signal(
    db,
    *,
    run_id: str,
    status: str = "active",
    confidence: str = "medium",
    canonical_key: str = "chronicle-consolidation:consolidation-worthy:workspace-search",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_signal(
        signal_id=f"chronicle-consolidation-signal-{uuid4().hex}",
        signal_type="chronicle-consolidation",
        canonical_key=canonical_key,
        status=status,
        title="Chronicle consolidation support: workspace search",
        summary="Bounded chronicle/consolidation support is marking a small carry-forward thread.",
        rationale="Validation chronicle/consolidation runtime layer",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="chronicle consolidation evidence",
        support_summary="Derived only from bounded self-review outcome/cadence and optional state/promotion support.",
        status_reason="Validation bounded chronicle/consolidation support with no canonical-file writeback.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_temporal_promotion_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_promotion_signal(
        signal_id=f"private-temporal-promotion-signal-{uuid4().hex}",
        signal_type="private-temporal-promotion",
        canonical_key="private-temporal-promotion:carry-forward:workspace-search",
        status=status,
        title="Private temporal promotion support: workspace search",
        summary="Bounded runtime temporal promotion is carrying a small maturation pull around workspace search.",
        rationale="Validation temporal promotion runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal promotion evidence",
        support_summary="Derived only from bounded temporal-curiosity and private-state runtime support.",
        status_reason="Validation bounded temporal promotion support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_executive_contradiction_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_executive_contradiction_signal(
        signal_id=f"executive-contradiction-signal-{uuid4().hex}",
        signal_type="executive-contradiction",
        canonical_key="executive-contradiction:contradiction-pressure:workspace-search",
        status=status,
        title="Executive contradiction support: workspace search",
        summary="Bounded executive contradiction pressure is asking Jarvis not to carry a thread forward blindly.",
        rationale="Validation executive contradiction runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="executive contradiction evidence",
        support_summary="Derived only from internal opposition, open-loop, self-review, and optional bounded inner-state support.",
        status_reason="Validation bounded executive contradiction support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_consolidation_brief(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-consolidation-brief-{uuid4().hex}",
        brief_type="consolidation-brief",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded chronicle brief is holding a small longer-horizon continuity candidate.",
        rationale="Validation chronicle brief runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle brief evidence",
        support_summary="Derived primarily from an existing bounded chronicle/consolidation signal.",
        status_reason="Validation bounded chronicle brief with no writeback authority.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_chronicle_brief_stays_empty_without_chronicle_signal_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_brief_tracking
    db = isolated_runtime.db

    _insert_private_temporal_promotion_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_chronicle_consolidation_briefs_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_chronicle_consolidation_brief_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_chronicle_brief_forms_bounded_runtime_support_from_chronicle_signal(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_brief_tracking
    db = isolated_runtime.db

    _insert_chronicle_consolidation_signal(db, run_id="visible-run-2")
    _insert_private_temporal_promotion_signal(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_chronicle_consolidation_briefs_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_chronicle_consolidation_brief_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["brief_type"] in {
        "chronicle-brief",
        "carry-forward-brief",
        "consolidation-brief",
        "anchored-brief",
    }
    assert item["brief_weight"] in {"medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["writeback_state"] == "not-writing-to-canonical-files"
    assert "not yet writing to chronicle or memory files" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_chronicle_brief_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.chronicle_consolidation_brief_tracking
    mission_control = isolated_runtime.mission_control

    _insert_chronicle_consolidation_brief(
        db,
        status="active",
        canonical_key="chronicle-consolidation-brief:consolidation-brief:workspace-search",
        title="Chronicle brief: workspace search",
    )
    _insert_chronicle_consolidation_brief(
        db,
        status="softening",
        canonical_key="chronicle-consolidation-brief:carry-forward-brief:visible-work",
        title="Chronicle brief: visible work",
    )
    _insert_chronicle_consolidation_brief(
        db,
        status="superseded",
        canonical_key="chronicle-consolidation-brief:chronicle-brief:archive-focus",
        title="Chronicle brief: archive focus",
    )

    surface = tracking.build_runtime_chronicle_consolidation_brief_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["chronicle_consolidation_briefs"]
    runtime_shape = runtime["runtime_chronicle_consolidation_briefs"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_brief",
        "current_status",
        "current_brief_type",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "writeback_state",
    }.issubset(surface["summary"].keys())
    assert {
        "brief_id",
        "brief_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "brief_focus",
        "brief_weight",
        "brief_summary",
        "brief_reason",
        "brief_confidence",
        "source_anchor",
        "grounding_mode",
        "writeback_state",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["writeback_state"] == "not-writing-to-canonical-files"
