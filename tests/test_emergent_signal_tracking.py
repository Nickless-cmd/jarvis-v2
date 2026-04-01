from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_witness_signal(db, *, canonical_key: str = "witness:carried-lesson:workspace-search") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-signal-{uuid4().hex}",
        signal_type="carried-lesson",
        canonical_key=canonical_key,
        status="fresh",
        title="Carried lesson: workspace search",
        summary="A bounded lesson around workspace search now looks carried forward.",
        rationale="Validation witness grounding",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="witness evidence",
        support_summary="witness support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_initiative_tension_signal(
    db,
    *,
    canonical_key: str = "private-initiative-tension:workspace-search:retention-pull",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-tension-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key=canonical_key,
        status="active",
        title="Private initiative tension support: workspace search",
        summary="Bounded initiative tension is still carrying directional pressure.",
        rationale="Validation tension grounding",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary="initiative tension support",
        status_reason="Validation initiative tension status",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _clear_grounding(db) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM runtime_witness_signals")
        conn.execute("DELETE FROM runtime_private_initiative_tension_signals")
        conn.commit()


def test_emergent_signal_daemon_creates_grounded_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.emergent_signal_tracking

    _insert_witness_signal(db)
    _insert_initiative_tension_signal(db)

    result = tracking.run_emergent_signal_daemon(trigger="test")
    surface = tracking.build_runtime_emergent_signal_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["current_status"] == "candidate"
    item = surface["items"][0]
    assert item["signal_family"] == "witness-tension"
    assert item["signal_status"] == "candidate"
    assert item["lifecycle_state"] == "candidate"
    assert item["interpretation_state"] == "grounded-candidate"
    assert item["truth"] == "candidate-only"
    assert item["visibility"] == "internal-only"
    assert item["identity_boundary"] == "not-canonical-identity-truth"
    assert item["memory_boundary"] == "not-workspace-memory"
    assert item["action_boundary"] == "not-action"
    assert item["source_hints"]


def test_emergent_signal_can_strengthen_then_fade_and_release(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.emergent_signal_tracking

    _insert_witness_signal(db)
    _insert_initiative_tension_signal(db)
    tracking.run_emergent_signal_daemon(trigger="tick-1")
    tracking.run_emergent_signal_daemon(trigger="tick-2")

    strengthened_surface = tracking.build_runtime_emergent_signal_surface(limit=8)
    assert strengthened_surface["summary"]["emergent_count"] == 1
    assert strengthened_surface["items"][0]["signal_status"] == "emergent"
    assert strengthened_surface["items"][0]["lifecycle_state"] == "strengthening"

    _clear_grounding(db)
    signal = next(iter(tracking._signals.values()))
    signal.last_grounded_at = (datetime.now(UTC) - timedelta(minutes=25)).isoformat()
    tracking.run_emergent_signal_daemon(trigger="tick-3")

    fading_surface = tracking.build_runtime_emergent_signal_surface(limit=8)
    assert fading_surface["summary"]["fading_count"] == 1
    assert fading_surface["items"][0]["lifecycle_state"] == "fading"

    signal.last_grounded_at = (datetime.now(UTC) - timedelta(minutes=50)).isoformat()
    tracking.run_emergent_signal_daemon(trigger="tick-4")

    released_surface = tracking.build_runtime_emergent_signal_surface(limit=8)
    assert released_surface["summary"]["active_count"] == 0
    assert released_surface["summary"]["released_count"] >= 1
    assert released_surface["recent_released"][0]["lifecycle_state"] == "released"


def test_emergent_signal_observability_stays_candidate_only_in_mc_and_self_model(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.emergent_signal_tracking
    mission_control = isolated_runtime.mission_control
    runtime_self_model = isolated_runtime.runtime_self_model

    _insert_witness_signal(db)
    _insert_initiative_tension_signal(db)
    tracking.run_emergent_signal_daemon(trigger="test")

    route_surface = mission_control.mc_emergent_signals()
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    self_model = runtime_self_model.build_runtime_self_model()

    assert route_surface["summary"]["authority"] == "candidate-only"
    assert route_surface["summary"]["identity_boundary"] == "not-canonical-identity-truth"
    assert route_surface["summary"]["memory_boundary"] == "not-workspace-memory"
    assert route_surface["summary"]["action_boundary"] == "not-action"

    assert jarvis["summary"]["emergent"]["authority"] == "candidate-only"
    assert jarvis["development"]["emergent_signals"]["summary"]["active_count"] == 1
    assert runtime["runtime_emergent_signals"]["summary"]["active_count"] == 1

    emergent_layer = next(
        layer for layer in self_model["layers"] if layer["id"] == "emergent-inner-signals"
    )
    assert emergent_layer["kind"] == "groundwork"
    assert emergent_layer["truth"] == "candidate-only"
    assert emergent_layer["visibility"] == "internal-only"