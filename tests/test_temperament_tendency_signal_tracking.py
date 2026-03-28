from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_meaning_significance_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-significance-signal-{uuid4().hex}",
        signal_type="meaning-significance",
        canonical_key="meaning-significance:development-significance:workspace-search",
        status=status,
        title="Meaning significance support: workspace search",
        summary="Bounded meaning/significance runtime support is holding a small significance-weight around workspace search.",
        rationale="Validation meaning/significance runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="meaning significance evidence",
        support_summary="Derived only from bounded chronicle continuity support, relation continuity support, and small promotion/contradiction/regulation sharpening. | grounding-mode=relation-continuity+chronicle-brief+chronicle-proposal+temporal-promotion+executive-contradiction+regulation | meaning significance anchor",
        status_reason="Validation bounded meaning/significance support and not canonical value or moral truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_relation_continuity_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-signal-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key="relation-continuity:trustful-continuity:workspace-search",
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


def _insert_regulation_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-homeostasis-signal-{uuid4().hex}",
        signal_type="regulation-homeostasis",
        canonical_key="regulation-homeostasis:steady-support:workspace-search",
        status=status,
        title="Regulation support: workspace search",
        summary="Bounded regulation/homeostasis runtime support is holding a small regulation state.",
        rationale="Validation regulation runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation evidence",
        support_summary="Derived only from bounded private-state support with optional sharpening. | regulation anchor",
        status_reason="Validation bounded regulation support and not canonical mood or personality.",
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


def _insert_private_state_snapshot(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_state_snapshot(
        snapshot_id=f"private-state-snapshot-{uuid4().hex}",
        snapshot_type="private-state-runtime-snapshot",
        canonical_key="private-state-snapshot:steady-support:workspace-search",
        status="active",
        title="Private state snapshot: workspace search",
        summary="Bounded runtime private-state snapshot is holding a small inner-state view.",
        rationale="Validation private-state runtime snapshot",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="private state evidence",
        support_summary="Derived only from active bounded inner-layer runtime support signals. | private state anchor",
        status_reason="Bounded private-state snapshot remains subordinate to visible/runtime truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_temperament_tendency_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_temperament_tendency_signal(
        signal_id=f"temperament-tendency-signal-{uuid4().hex}",
        signal_type="temperament-tendency",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded temperament runtime support is holding a small character-tilt.",
        rationale="Validation temperament runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temperament evidence",
        support_summary="Derived only from bounded meaning/significance support, relation continuity support, regulation or private-state substrate, and small contradiction or temporal-promotion sharpening. | grounding-mode=meaning-significance+relation-continuity+regulation+private-state+executive-contradiction+temporal-promotion | temperament anchor",
        status_reason="Validation bounded temperament support and not canonical personality truth.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_temperament_tendency_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    tracking = isolated_runtime.temperament_tendency_signal_tracking
    db = isolated_runtime.db

    _insert_meaning_significance_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_temperament_tendency_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_temperament_tendency_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_temperament_tendency_forms_bounded_runtime_support_from_existing_substrate(isolated_runtime) -> None:
    tracking = isolated_runtime.temperament_tendency_signal_tracking
    db = isolated_runtime.db

    _insert_meaning_significance_signal(db, run_id="visible-run-2")
    _insert_relation_continuity_signal(db, run_id="visible-run-2")
    _insert_regulation_signal(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")
    _insert_temporal_promotion_signal(db, run_id="visible-run-2")
    _insert_private_state_snapshot(db, run_id="visible-run-2")

    result = tracking.track_runtime_temperament_tendency_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_temperament_tendency_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "temperament-tendency"
    assert item["temperament_type"] in {"caution", "steadiness", "firmness", "openness", "watchful-restraint"}
    assert item["temperament_balance"] in {"steady", "guarded", "steady-caution", "curious-caution", "steady-firmness", "steady-openness", "guarded-openness"}
    assert item["temperament_weight"] in {"low", "medium", "high"}
    assert item["temperament_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_personality_state"] == "not-canonical-personality-truth"
    assert "not canonical personality truth" in item["status_reason"].lower()
    assert "meaning-significance" in item["grounding_mode"]
    assert item["source_anchor"]


def test_temperament_tendency_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.temperament_tendency_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_temperament_tendency_signal(
        db,
        status="active",
        canonical_key="temperament-tendency:steadiness:workspace-search",
        title="Temperament support: workspace search",
    )
    _insert_temperament_tendency_signal(
        db,
        status="softening",
        canonical_key="temperament-tendency:watchful-restraint:visible-work",
        title="Temperament support: visible work",
    )
    _insert_temperament_tendency_signal(
        db,
        status="superseded",
        canonical_key="temperament-tendency:firmness:archive-focus",
        title="Temperament support: archive focus",
    )

    surface = tracking.build_runtime_temperament_tendency_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["temperament_tendency_signals"]
    runtime_shape = runtime["runtime_temperament_tendency_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_type",
        "current_balance",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_personality_state",
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
        "temperament_type",
        "temperament_balance",
        "temperament_weight",
        "temperament_summary",
        "temperament_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_personality_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_personality_state"] == "not-canonical-personality-truth"
