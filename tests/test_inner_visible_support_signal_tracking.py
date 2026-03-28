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


def _insert_private_temporal_curiosity_state(
    db,
    *,
    run_id: str,
    status: str = "active",
    curiosity_type: str = "active-observation",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_curiosity_state(
        state_id=f"private-temporal-curiosity-state-{uuid4().hex}",
        state_type="private-temporal-curiosity",
        canonical_key=f"private-temporal-curiosity:{curiosity_type}:workspace-search",
        status=status,
        title="Private temporal curiosity support: workspace search",
        summary="Bounded runtime temporal curiosity is keeping a small forward-looking pull.",
        rationale="Validation temporal curiosity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal curiosity evidence",
        support_summary="Derived only from active bounded private-state and initiative-tension runtime support.",
        status_reason="Validation bounded temporal curiosity support",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_inner_visible_support_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_inner_visible_support_signal(
        signal_id=f"inner-visible-support-signal-{uuid4().hex}",
        signal_type="inner-visible-support",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded inner-visible runtime support is holding a small outward-facing support shape.",
        rationale="Validation inner-visible support runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="inner visible support evidence",
        support_summary="Derived only from bounded private-state runtime support and optional temporal-curiosity sharpening.",
        status_reason="Validation bounded inner-visible support and not-yet-bridged prompt state.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_executive_contradiction_signal(
    db,
    *,
    run_id: str,
    status: str = "active",
    pressure: str = "high",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_executive_contradiction_signal(
        signal_id=f"executive-contradiction-signal-{uuid4().hex}",
        signal_type="executive-contradiction",
        canonical_key="executive-contradiction:contradiction-pressure:workspace-search",
        status=status,
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


def test_inner_visible_support_stays_empty_without_private_state_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.inner_visible_support_signal_tracking
    db = isolated_runtime.db

    _insert_private_temporal_curiosity_state(db, run_id="visible-run-1")

    result = tracking.track_runtime_inner_visible_support_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_inner_visible_support_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_inner_visible_support_forms_bounded_runtime_support_from_state_and_curiosity(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.inner_visible_support_signal_tracking
    db = isolated_runtime.db

    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_private_temporal_curiosity_state(db, run_id="visible-run-2")

    result = tracking.track_runtime_inner_visible_support_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_inner_visible_support_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "inner-visible-support"
    assert item["support_type"] == "bounded-inner-visible-support"
    assert item["support_tone"] in {"careful-forward", "careful-steady", "steady-forward", "steady-support"}
    assert item["support_stance"] in {"watchful", "careful", "steady"}
    assert item["support_directness"] in {"high", "medium"}
    assert item["support_watchfulness"] in {"low", "medium"}
    assert item["support_momentum"] in {"steady", "held", "carried"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["prompt_bridge_state"] == "gated-visible-prompt-bridge"
    assert "tiny gated prompt-support line" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_inner_visible_support_gets_small_bounded_executive_watchfulness_sharpening(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.inner_visible_support_signal_tracking
    db = isolated_runtime.db

    _insert_private_state_snapshot(db, run_id="visible-run-contradiction")
    _insert_private_temporal_curiosity_state(db, run_id="visible-run-contradiction")
    _insert_executive_contradiction_signal(db, run_id="visible-run-contradiction")

    result = tracking.track_runtime_inner_visible_support_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-contradiction",
    )
    surface = tracking.build_runtime_inner_visible_support_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert item["support_watchfulness"] == "medium"
    assert item["support_watchfulness_source"] == "executive-contradiction"
    assert item["support_contradiction_sharpening"] == "bounded-watchfulness"
    assert "executive-contradiction" in item["grounding_mode"]
    assert item["authority"] == "non-authoritative"
    assert item["prompt_bridge_state"] == "gated-visible-prompt-bridge"
    assert "cannot directly veto execution" in item["status_reason"].lower()


def test_inner_visible_support_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.inner_visible_support_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_inner_visible_support_signal(
        db,
        status="active",
        canonical_key="inner-visible-support:careful-forward:workspace-search",
        title="Inner visible support: workspace search",
    )
    _insert_inner_visible_support_signal(
        db,
        status="stale",
        canonical_key="inner-visible-support:steady-support:visible-work",
        title="Inner visible support: visible work",
    )
    _insert_inner_visible_support_signal(
        db,
        status="superseded",
        canonical_key="inner-visible-support:careful-steady:archive-focus",
        title="Inner visible support: archive focus",
    )

    surface = tracking.build_runtime_inner_visible_support_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["inner_visible_support_signals"]
    runtime_shape = runtime["runtime_inner_visible_support_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_tone",
        "current_stance",
        "current_directness",
        "current_watchfulness",
        "current_watchfulness_source",
        "current_contradiction_sharpening",
        "current_momentum",
        "current_confidence",
        "authority",
        "layer_role",
        "prompt_bridge_state",
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
        "support_type",
        "support_tone",
        "support_stance",
        "support_directness",
        "support_watchfulness",
        "support_watchfulness_source",
        "support_contradiction_sharpening",
        "support_momentum",
        "support_summary",
        "support_confidence",
        "source_anchor",
        "prompt_bridge_state",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["prompt_bridge_state"] == "gated-visible-prompt-bridge"
