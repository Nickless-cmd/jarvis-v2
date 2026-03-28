from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_understanding_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_understanding_signal(
        signal_id=f"user-understanding-{uuid4().hex}",
        signal_type="workstyle-signal",
        canonical_key="user-understanding:workstyle-signal:workspace-search",
        status="active",
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


def _insert_relation_state_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_state_signal(
        signal_id=f"relation-state-signal-{uuid4().hex}",
        signal_type="relation-state",
        canonical_key="relation-state:working-alignment:workspace-search",
        status="active",
        title="Relation state support: workspace search",
        summary="Bounded relation-state runtime support is holding a small working relationship state.",
        rationale="Validation relation-state runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation state evidence",
        support_summary="Derived only from bounded user-understanding runtime support plus bounded regulation and private-state support.",
        status_reason="Validation bounded relation-state support and not canonical relationship truth.",
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
        support_summary="Derived primarily from an existing bounded chronicle/consolidation signal.",
        status_reason="Validation bounded chronicle brief support.",
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


def _insert_relation_continuity_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-signal-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded relation continuity runtime support is holding a small working-relationship continuity thread.",
        rationale="Validation relation continuity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="relation continuity evidence",
        support_summary="Derived only from bounded relation-state support and chronicle continuity support.",
        status_reason="Validation bounded relation continuity support and not canonical relationship truth.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_relation_continuity_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.relation_continuity_signal_tracking
    db = isolated_runtime.db

    _insert_relation_state_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_relation_continuity_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_relation_continuity_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_relation_continuity_forms_bounded_runtime_support_from_relation_and_chronicle_substrate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.relation_continuity_signal_tracking
    db = isolated_runtime.db

    _insert_user_understanding_signal(db, run_id="visible-run-2")
    _insert_relation_state_signal(db, run_id="visible-run-2")
    _insert_chronicle_brief(db, run_id="visible-run-2")
    _insert_regulation_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_relation_continuity_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_relation_continuity_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "relation-continuity"
    assert item["continuity_state"] in {"trustful-continuity", "watchful-continuity", "carried-alignment", "careful-continuity"}
    assert item["continuity_alignment"] in {"aligned", "working-alignment", "cautious-alignment"}
    assert item["continuity_watchfulness"] in {"low", "medium"}
    assert item["continuity_weight"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["canonical_relation_state"] == "not-canonical-relationship-truth"
    assert "not canonical relationship truth" in item["status_reason"].lower()
    assert "relation-state" in item["grounding_mode"]
    assert item["source_anchor"]


def test_relation_continuity_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.relation_continuity_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_relation_continuity_signal(
        db,
        status="active",
        canonical_key="relation-continuity:carried-alignment:workspace-search",
        title="Relation continuity support: workspace search",
    )
    _insert_relation_continuity_signal(
        db,
        status="softening",
        canonical_key="relation-continuity:watchful-continuity:visible-work",
        title="Relation continuity support: visible work",
    )
    _insert_relation_continuity_signal(
        db,
        status="superseded",
        canonical_key="relation-continuity:trustful-continuity:archive-focus",
        title="Relation continuity support: archive focus",
    )

    surface = tracking.build_runtime_relation_continuity_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["relation_continuity_signals"]
    runtime_shape = runtime["runtime_relation_continuity_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_alignment",
        "current_watchfulness",
        "current_weight",
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
        "continuity_state",
        "continuity_alignment",
        "continuity_watchfulness",
        "continuity_weight",
        "continuity_summary",
        "continuity_confidence",
        "source_anchor",
        "authority",
        "layer_role",
        "canonical_relation_state",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["canonical_relation_state"] == "not-canonical-relationship-truth"
