from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


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
        status_reason="Bounded private-state snapshot remains subordinate to visible/runtime truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_initiative_tension_signal(db, *, run_id: str, tension_type: str = "unresolved") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"private-initiative-tension-signal-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key=f"private-initiative-tension:{tension_type}:workspace-search",
        status="active",
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


def _insert_private_temporal_curiosity_state(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_curiosity_state(
        state_id=f"private-temporal-curiosity-state-{uuid4().hex}",
        state_type="private-temporal-curiosity",
        canonical_key="private-temporal-curiosity:active-observation:workspace-search",
        status="active",
        title="Private temporal curiosity support: workspace search",
        summary="Bounded runtime temporal curiosity is keeping a small forward-looking pull.",
        rationale="Validation temporal curiosity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal curiosity evidence",
        support_summary="Derived only from active bounded private-state and initiative-tension runtime support.",
        status_reason="Validation bounded temporal curiosity support.",
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
        support_summary="Derived only from internal opposition, open-loop, self-review, and optional bounded inner-state support.",
        status_reason="Validation executive contradiction support with no execution veto authority.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_inner_visible_support_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_inner_visible_support_signal(
        signal_id=f"inner-visible-support-signal-{uuid4().hex}",
        signal_type="inner-visible-support",
        canonical_key="inner-visible-support:careful-forward:workspace-search",
        status="active",
        title="Inner visible support: workspace search",
        summary="Bounded inner-visible runtime support is holding a small outward-facing support shape.",
        rationale="Validation inner-visible support runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="inner visible support evidence",
        support_summary="Derived only from bounded private-state runtime support and optional temporal-curiosity sharpening.",
        status_reason="Validation bounded inner-visible support and gated prompt bridge state.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_regulation_homeostasis_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-homeostasis-signal-{uuid4().hex}",
        signal_type="regulation-homeostasis",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded regulation/homeostasis runtime support is holding a small regulation state.",
        rationale="Validation regulation/homeostasis runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation homeostasis evidence",
        support_summary="Derived only from bounded private-state support with optional sharpening.",
        status_reason="Validation bounded regulation/homeostasis support and not canonical mood or personality.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_regulation_homeostasis_stays_empty_without_private_state_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.regulation_homeostasis_signal_tracking
    db = isolated_runtime.db

    _insert_executive_contradiction_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_regulation_homeostasis_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_regulation_homeostasis_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_regulation_homeostasis_forms_bounded_runtime_support_from_existing_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.regulation_homeostasis_signal_tracking
    db = isolated_runtime.db

    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_private_initiative_tension_signal(db, run_id="visible-run-2")
    _insert_private_temporal_curiosity_state(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")
    _insert_inner_visible_support_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_regulation_homeostasis_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_regulation_homeostasis_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "regulation-homeostasis"
    assert item["regulation_state"] in {"watchful-pressure", "steady-pressure", "settling-support", "steady-support"}
    assert item["regulation_pressure"] in {"low", "medium"}
    assert item["regulation_watchfulness"] in {"low", "medium"}
    assert item["regulation_pacing"] in {"steady", "careful-forward", "slow-and-check", "settling-needed"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_mood_state"] == "not-canonical-mood-or-personality"
    assert "not canonical mood or personality" in item["status_reason"].lower()
    assert "executive-contradiction" in item["grounding_mode"]
    assert item["source_anchor"]


def test_regulation_homeostasis_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.regulation_homeostasis_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_regulation_homeostasis_signal(
        db,
        status="active",
        canonical_key="regulation-homeostasis:watchful-pressure:workspace-search",
        title="Regulation support: workspace search",
    )
    _insert_regulation_homeostasis_signal(
        db,
        status="stale",
        canonical_key="regulation-homeostasis:settling-support:visible-work",
        title="Regulation support: visible work",
    )
    _insert_regulation_homeostasis_signal(
        db,
        status="superseded",
        canonical_key="regulation-homeostasis:steady-support:archive-focus",
        title="Regulation support: archive focus",
    )

    surface = tracking.build_runtime_regulation_homeostasis_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["regulation_homeostasis_signals"]
    runtime_shape = runtime["runtime_regulation_homeostasis_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_pressure",
        "current_watchfulness",
        "current_pacing",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_mood_state",
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
        "regulation_state",
        "regulation_pressure",
        "regulation_watchfulness",
        "regulation_pacing",
        "regulation_summary",
        "regulation_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_mood_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_mood_state"] == "not-canonical-mood-or-personality"
