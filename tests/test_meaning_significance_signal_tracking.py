from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_relation_continuity_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-signal-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key="relation-continuity:carried-alignment:workspace-search",
        status=status,
        title="Relation continuity support: workspace search",
        summary="Bounded relation continuity runtime support is holding a small working-relationship continuity thread.",
        rationale="Validation relation continuity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation continuity evidence",
        support_summary="Derived only from bounded relation-state support and chronicle continuity support. | relation continuity anchor",
        status_reason="Validation bounded relation continuity support and not canonical relationship truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_brief(db, *, run_id: str, status: str = "active", weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-consolidation-brief-{uuid4().hex}",
        brief_type="consolidation-brief",
        canonical_key="chronicle-consolidation-brief:consolidation-brief:workspace-search",
        status=status,
        title="Chronicle brief: workspace search",
        summary="Bounded chronicle brief is holding workspace search as a small longer-horizon continuity candidate.",
        rationale="Validation chronicle brief runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle brief evidence",
        support_summary=f"Derived primarily from an existing bounded chronicle/consolidation signal. | brief-weight={weight} | chronicle brief anchor",
        status_reason="Validation bounded chronicle brief support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_proposal(db, *, run_id: str, status: str = "active", weight: str = "high") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_proposal(
        proposal_id=f"chronicle-consolidation-proposal-{uuid4().hex}",
        proposal_type="consolidation-proposal",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
        status=status,
        title="Chronicle proposal: workspace search",
        summary="Bounded chronicle proposal is holding workspace search as a small carry-forward proposal.",
        rationale="Validation chronicle proposal runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle proposal evidence",
        support_summary=f"Derived from bounded chronicle brief support. | proposal-weight={weight} | chronicle proposal anchor",
        status_reason="Validation bounded chronicle proposal support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_temporal_promotion_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_promotion_signal(
        signal_id=f"private-temporal-promotion-signal-{uuid4().hex}",
        signal_type="private-temporal-promotion",
        canonical_key="private-temporal-promotion:carry-forward:workspace-search",
        status="active",
        title="Private temporal promotion support: workspace search",
        summary="Bounded runtime temporal promotion is carrying a small maturation pull around workspace search.",
        rationale="Validation temporal promotion runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal promotion evidence",
        support_summary="Derived only from active bounded temporal-curiosity and private-state runtime support. | temporal promotion anchor",
        status_reason="Validation bounded temporal promotion support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_executive_contradiction_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_executive_contradiction_signal(
        signal_id=f"executive-contradiction-signal-{uuid4().hex}",
        signal_type="executive-contradiction",
        canonical_key="executive-contradiction:contradiction-pressure:workspace-search",
        status="active",
        title="Executive contradiction support: workspace search",
        summary="Bounded executive contradiction pressure is asking Jarvis not to carry workspace search forward blindly.",
        rationale="Validation executive contradiction runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="executive contradiction evidence",
        support_summary="Derived only from internal opposition, open-loop, self-review, and optional bounded inner-state support. | executive contradiction anchor",
        status_reason="Validation executive contradiction support with no execution veto authority.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_regulation_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-homeostasis-signal-{uuid4().hex}",
        signal_type="regulation-homeostasis",
        canonical_key="regulation-homeostasis:watchful-pressure:workspace-search",
        status="active",
        title="Regulation support: workspace search",
        summary="Bounded regulation/homeostasis runtime support is holding a small regulation state.",
        rationale="Validation regulation/homeostasis runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation evidence",
        support_summary="Derived only from bounded private-state support with optional sharpening. | regulation anchor",
        status_reason="Validation bounded regulation/homeostasis support and not canonical mood or personality.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_meaning_significance_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-significance-signal-{uuid4().hex}",
        signal_type="meaning-significance",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded meaning/significance runtime support is holding a small significance-weight.",
        rationale="Validation meaning/significance runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="meaning significance evidence",
        support_summary="Derived only from bounded chronicle continuity support, relation continuity support, and small promotion/contradiction/regulation sharpening. | grounding-mode=relation-continuity+chronicle-brief+chronicle-proposal+temporal-promotion+executive-contradiction+regulation | meaning significance anchor",
        status_reason="Validation bounded meaning/significance support and not canonical value or moral truth.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_meaning_significance_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.meaning_significance_signal_tracking
    db = isolated_runtime.db

    _insert_chronicle_brief(db, run_id="visible-run-1")

    result = tracking.track_runtime_meaning_significance_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_meaning_significance_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_meaning_significance_forms_bounded_runtime_support_from_chronicle_and_relation_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.meaning_significance_signal_tracking
    db = isolated_runtime.db

    _insert_relation_continuity_signal(db, run_id="visible-run-2")
    _insert_chronicle_brief(db, run_id="visible-run-2", weight="high")
    _insert_chronicle_proposal(db, run_id="visible-run-2", weight="high")
    _insert_temporal_promotion_signal(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")
    _insert_regulation_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_meaning_significance_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_meaning_significance_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "meaning-significance"
    assert item["meaning_type"] in {
        "carried-significance",
        "relational-significance",
        "development-significance",
        "watchful-significance",
    }
    assert item["meaning_weight"] in {"low", "medium", "high"}
    assert item["meaning_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_value_state"] == "not-canonical-value-or-moral-truth"
    assert "not canonical value or moral truth" in item["status_reason"].lower()
    assert "relation-continuity" in item["grounding_mode"]
    assert item["source_anchor"]


def test_meaning_significance_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.meaning_significance_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_meaning_significance_signal(
        db,
        status="active",
        canonical_key="meaning-significance:development-significance:workspace-search",
        title="Meaning significance support: workspace search",
    )
    _insert_meaning_significance_signal(
        db,
        status="softening",
        canonical_key="meaning-significance:watchful-significance:visible-work",
        title="Meaning significance support: visible work",
    )
    _insert_meaning_significance_signal(
        db,
        status="superseded",
        canonical_key="meaning-significance:carried-significance:archive-focus",
        title="Meaning significance support: archive focus",
    )

    surface = tracking.build_runtime_meaning_significance_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["meaning_significance_signals"]
    runtime_shape = runtime["runtime_meaning_significance_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_type",
        "current_focus",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_value_state",
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
        "meaning_type",
        "meaning_focus",
        "meaning_weight",
        "meaning_summary",
        "meaning_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_value_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_value_state"] == "not-canonical-value-or-moral-truth"
