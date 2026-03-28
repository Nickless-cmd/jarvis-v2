from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_chronicle_consolidation_brief(
    db,
    *,
    run_id: str,
    status: str = "active",
    confidence: str = "medium",
    canonical_key: str = "chronicle-consolidation-brief:consolidation-brief:workspace-search",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-consolidation-brief-{uuid4().hex}",
        brief_type="consolidation-brief",
        canonical_key=canonical_key,
        status=status,
        title="Chronicle brief: workspace search",
        summary="Bounded chronicle brief is holding a small longer-horizon continuity candidate.",
        rationale="Validation chronicle brief runtime layer",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="chronicle brief evidence",
        support_summary="Derived primarily from an existing bounded chronicle/consolidation signal.",
        status_reason="Validation bounded chronicle brief with no writeback authority.",
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


def _insert_chronicle_consolidation_proposal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_proposal(
        proposal_id=f"chronicle-consolidation-proposal-{uuid4().hex}",
        proposal_type="consolidation-proposal",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded chronicle proposal is preparing a small future carry-forward candidate.",
        rationale="Validation chronicle proposal runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle proposal evidence",
        support_summary="Derived primarily from an existing bounded chronicle/consolidation brief.",
        status_reason="Validation bounded chronicle proposal with no writeback authority.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_chronicle_proposal_stays_empty_without_chronicle_brief_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_proposal_tracking
    db = isolated_runtime.db

    _insert_private_temporal_promotion_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_chronicle_consolidation_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_chronicle_proposal_forms_bounded_runtime_support_from_chronicle_brief(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_proposal_tracking
    db = isolated_runtime.db

    _insert_chronicle_consolidation_brief(db, run_id="visible-run-2")
    _insert_private_temporal_promotion_signal(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_chronicle_consolidation_proposal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["proposal_type"] in {
        "chronicle-proposal",
        "carry-forward-proposal",
        "consolidation-proposal",
        "anchored-proposal",
    }
    assert item["proposal_weight"] in {"medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["writeback_state"] == "not-writing-to-canonical-files"
    assert "not yet writing to chronicle or memory files" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_chronicle_proposal_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.chronicle_consolidation_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
        title="Chronicle proposal: workspace search",
    )
    _insert_chronicle_consolidation_proposal(
        db,
        status="softening",
        canonical_key="chronicle-consolidation-proposal:carry-forward-proposal:visible-work",
        title="Chronicle proposal: visible work",
    )
    _insert_chronicle_consolidation_proposal(
        db,
        status="superseded",
        canonical_key="chronicle-consolidation-proposal:chronicle-proposal:archive-focus",
        title="Chronicle proposal: archive focus",
    )

    surface = tracking.build_runtime_chronicle_consolidation_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["chronicle_consolidation_proposals"]
    runtime_shape = runtime["runtime_chronicle_consolidation_proposals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "writeback_state",
    }.issubset(surface["summary"].keys())
    assert {
        "proposal_id",
        "proposal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "proposal_focus",
        "proposal_weight",
        "proposal_summary",
        "proposal_reason",
        "proposal_confidence",
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
