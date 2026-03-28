from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_understanding_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_understanding_signal(
        signal_id=f"user-understanding-{uuid4().hex}",
        signal_type="workstyle-signal",
        canonical_key="user-understanding:workstyle-signal:workspace-search",
        status=status,
        title="User understanding: workstyle signal",
        summary="Signal summary: workstyle signal",
        rationale="Validation user-understanding signal",
        source_kind="user-explicit",
        confidence="medium",
        evidence_summary="user-understanding signal evidence",
        support_summary="user-understanding signal support | Visible user anchor: validation anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation user-understanding signal status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_private_state_snapshot(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_state_snapshot(
        snapshot_id=f"private-state-snapshot-{uuid4().hex}",
        snapshot_type="private-state-runtime-snapshot",
        canonical_key="private-state-snapshot:steady-pressure:workspace-search",
        status="active",
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


def _insert_regulation_homeostasis_signal(db, *, run_id: str) -> None:
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
        evidence_summary="regulation homeostasis evidence",
        support_summary="Derived only from bounded private-state support with optional sharpening.",
        status_reason="Validation bounded regulation/homeostasis support and not canonical mood or personality.",
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


def _insert_relation_state_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_state_signal(
        signal_id=f"relation-state-signal-{uuid4().hex}",
        signal_type="relation-state",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded relation-state runtime support is holding a small working relationship state.",
        rationale="Validation relation-state runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation state evidence",
        support_summary="Derived only from bounded user-understanding runtime support plus bounded regulation and private-state support.",
        status_reason="Validation bounded relation-state support and not canonical relationship truth.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_relation_state_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.relation_state_signal_tracking
    db = isolated_runtime.db

    _insert_user_understanding_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_relation_state_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_relation_state_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_relation_state_forms_bounded_runtime_support_from_existing_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.relation_state_signal_tracking
    db = isolated_runtime.db

    _insert_user_understanding_signal(db, run_id="visible-run-2")
    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_regulation_homeostasis_signal(db, run_id="visible-run-2")
    _insert_executive_contradiction_signal(db, run_id="visible-run-2")
    _insert_inner_visible_support_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_relation_state_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_relation_state_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "relation-state"
    assert item["relation_state"] in {"trustful-flow", "working-alignment", "careful-collaboration", "cautious-distance"}
    assert item["relation_alignment"] in {"aligned", "working-alignment", "cautious-alignment"}
    assert item["relation_watchfulness"] in {"low", "medium"}
    assert item["relation_pressure"] in {"low", "medium"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_relation_state"] == "not-canonical-relationship-truth"
    assert "not canonical relationship truth" in item["status_reason"].lower()
    assert "user-understanding" in item["grounding_mode"]
    assert item["source_anchor"]


def test_relation_state_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.relation_state_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_relation_state_signal(
        db,
        status="active",
        canonical_key="relation-state:working-alignment:workspace-search",
        title="Relation state support: workspace search",
    )
    _insert_relation_state_signal(
        db,
        status="stale",
        canonical_key="relation-state:careful-collaboration:visible-work",
        title="Relation state support: visible work",
    )
    _insert_relation_state_signal(
        db,
        status="superseded",
        canonical_key="relation-state:trustful-flow:archive-focus",
        title="Relation state support: archive focus",
    )

    surface = tracking.build_runtime_relation_state_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["relation_state_signals"]
    runtime_shape = runtime["runtime_relation_state_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_alignment",
        "current_watchfulness",
        "current_pressure",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_relation_state",
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
        "relation_state",
        "relation_alignment",
        "relation_watchfulness",
        "relation_pressure",
        "relation_summary",
        "relation_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_relation_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_relation_state"] == "not-canonical-relationship-truth"
