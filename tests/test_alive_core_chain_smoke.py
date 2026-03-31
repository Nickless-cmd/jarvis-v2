"""Smoke tests for the bounded alive-core runtime chain.

These tests verify that the key multi-step chains work end-to-end
through the real DB and surface builders, without monkeypatching.
They lock down the invariants landed across the recent lifecycle passes:

    initiative tension → autonomy pressure → proactive loop → question gate
    softening loop → closure proposal
    repeated tracking → supersession (no duplicate spam)
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_initiative_tension(db, *, signal_type: str = "unresolved") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=f"private-initiative-tension:{signal_type}:smoke-thread",
        status="active",
        title="Private initiative tension support: Smoke thread",
        summary="Bounded initiative tension is still carrying unresolved pressure.",
        rationale="Smoke test initiative tension",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary="tension-level=medium | source-anchor=smoke-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


def _insert_open_loop(db, *, status: str = "open") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:smoke-thread",
        status=status,
        title="Open loop: Smoke thread",
        summary="Bounded open loop for smoke test.",
        rationale="Smoke test open loop",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="source-anchor=smoke-loop-anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


def _insert_regulation(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-{uuid4().hex}",
        signal_type="effort-regulation",
        canonical_key="regulation-homeostasis:effort-regulation:smoke-thread",
        status="active",
        title="Regulation support: Smoke thread",
        summary="Bounded regulation pressure remains present.",
        rationale="Smoke test regulation",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation evidence",
        support_summary="regulation-pressure=medium | source-anchor=regulation-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


def _insert_runtime_awareness(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_awareness_signal(
        signal_id=f"awareness-{uuid4().hex}",
        signal_type="machine-available",
        canonical_key="runtime-awareness:machine-available:smoke-thread",
        status="active",
        title="Runtime awareness: machine available",
        summary="Machine is available and ready.",
        rationale="Smoke test awareness",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="awareness evidence",
        support_summary="source-anchor=awareness-anchor",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


# ---------------------------------------------------------------------------
# Chain test 1: initiative tension + open loop → autonomy pressure → proactive loop
# ---------------------------------------------------------------------------


def test_initiative_tension_and_open_loop_drive_autonomy_pressure_and_proactive_loop(
    isolated_runtime,
) -> None:
    """The core alive chain: initiative tension + open loop + regulation
    should produce autonomy pressure (initiative + question), which then
    feeds proactive loop lifecycle materialization — all via real DB."""
    db = isolated_runtime.db
    autonomy = isolated_runtime.autonomy_pressure_signal_tracking
    proactive = isolated_runtime.proactive_loop_lifecycle_tracking

    _insert_initiative_tension(db)
    _insert_open_loop(db)
    _insert_regulation(db)
    _insert_runtime_awareness(db)

    # Step 1: autonomy pressure tracking
    ap_result = autonomy.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    ap_surface = autonomy.build_runtime_autonomy_pressure_signal_surface(limit=8)
    ap_types = {item["autonomy_pressure_type"] for item in ap_surface["items"]}

    assert ap_result["created"] >= 2
    assert "initiative-pressure" in ap_types
    assert "question-pressure" in ap_types

    # Step 2: proactive loop lifecycle tracking (reads autonomy + open loops from DB)
    pl_result = proactive.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    pl_surface = proactive.build_runtime_proactive_loop_lifecycle_surface(limit=8)
    pl_kinds = {item["loop_kind"] for item in pl_surface["items"]}

    assert pl_result["created"] >= 1
    assert pl_surface["active"] is True
    assert "initiative-loop" in pl_kinds

    # Invariants: non-authoritative throughout
    for item in pl_surface["items"]:
        assert item["planner_authority_state"] == "not-planner-authority"
        assert item["proactive_execution_state"] == "not-proactive-execution"


# ---------------------------------------------------------------------------
# Chain test 2: softening loop → closure proposal activation
# ---------------------------------------------------------------------------


def test_softening_loop_drives_closure_proposal_through_real_chain(
    isolated_runtime,
) -> None:
    """A softening open loop should produce a hold-open closure proposal
    via the real DB chain, even without medium closure_confidence."""
    db = isolated_runtime.db
    closure = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(db, status="softening")

    result = closure.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    surface = closure.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert result["created"] >= 1
    assert surface["active"] is True
    item = surface["items"][0]
    assert item["proposal_type"] == "hold-open"
    assert "softening" in (item.get("proposal_reason") or item.get("summary") or "").lower()


# ---------------------------------------------------------------------------
# Chain test 3: repeated tracking produces supersession, not duplicates
# ---------------------------------------------------------------------------


def test_repeated_autonomy_tracking_does_not_accumulate_duplicates(
    isolated_runtime,
) -> None:
    """Calling autonomy pressure tracking twice with the same substrate
    should not accumulate duplicate active signals — upsert by canonical key
    keeps the count stable."""
    db = isolated_runtime.db
    autonomy = isolated_runtime.autonomy_pressure_signal_tracking

    _insert_initiative_tension(db)
    _insert_open_loop(db)
    _insert_regulation(db)
    _insert_runtime_awareness(db)

    # First call
    autonomy.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run-1",
    )
    surface_1 = autonomy.build_runtime_autonomy_pressure_signal_surface(limit=20)
    active_count_1 = len([i for i in surface_1["items"] if i.get("status") == "active"])

    # Second call with same substrate
    autonomy.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run-2",
    )
    surface_2 = autonomy.build_runtime_autonomy_pressure_signal_surface(limit=20)
    active_count_2 = len([i for i in surface_2["items"] if i.get("status") == "active"])

    # Active count stays stable — no duplicate accumulation
    assert active_count_2 == active_count_1
    assert active_count_1 >= 2  # initiative + question pressure at minimum


# ---------------------------------------------------------------------------
# Chain test 4: open loop with status=open + low confidence → no proposal
# ---------------------------------------------------------------------------


def test_open_loop_with_low_confidence_does_not_produce_closure_proposal(
    isolated_runtime,
) -> None:
    """An open (not softening) loop with low closure_confidence must NOT
    produce a closure proposal — only softening or medium+ confidence qualifies."""
    db = isolated_runtime.db
    closure = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(db, status="open")

    result = closure.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    surface = closure.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False


# ---------------------------------------------------------------------------
# Chain test 5: full proactive chain → question gate via real DB
# ---------------------------------------------------------------------------


def _insert_relation_continuity(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key="relation-continuity:carried-thread:smoke-thread",
        status="active",
        title="Relation continuity: Smoke thread",
        summary="Relation continuity is still holding weight.",
        rationale="Smoke test relation continuity",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="relation continuity evidence",
        support_summary="continuity-weight=high | source-anchor=relation-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


def _insert_meaning(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-{uuid4().hex}",
        signal_type="developmental-significance",
        canonical_key="meaning-significance:developmental-significance:smoke-thread",
        status="active",
        title="Meaning significance: Smoke thread",
        summary="Meaning significance is still carried.",
        rationale="Smoke test meaning",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="meaning evidence",
        support_summary="meaning-weight=high | source-anchor=meaning-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Smoke test",
        run_id="smoke-run",
        session_id="smoke-session",
    )


def test_full_proactive_chain_produces_question_gate_via_real_db(
    isolated_runtime,
) -> None:
    """The full alive-core proactive chain:
    initiative tension + open loop + regulation + awareness + relation + meaning
    → autonomy pressure (question-pressure)
    → proactive loop (question-loop)
    → question gate (with backing thread info)
    All via real DB, no monkeypatching."""
    db = isolated_runtime.db
    autonomy = isolated_runtime.autonomy_pressure_signal_tracking
    proactive = isolated_runtime.proactive_loop_lifecycle_tracking
    gate = isolated_runtime.proactive_question_gate_tracking

    # Seed the full substrate
    _insert_initiative_tension(db)
    _insert_open_loop(db)
    _insert_regulation(db)
    _insert_runtime_awareness(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)

    # Step 1: autonomy pressure must produce question-pressure
    autonomy.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    ap_surface = autonomy.build_runtime_autonomy_pressure_signal_surface(limit=8)
    ap_types = {item["autonomy_pressure_type"] for item in ap_surface["items"]}
    assert "question-pressure" in ap_types

    # Step 2: proactive loop must produce question-loop
    proactive.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    pl_surface = proactive.build_runtime_proactive_loop_lifecycle_surface(limit=8)
    pl_kinds = {item["loop_kind"] for item in pl_surface["items"]}
    assert "question-loop" in pl_kinds

    # Step 3: question gate must materialize
    gate.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    gate_surface = gate.build_runtime_proactive_question_gate_surface(limit=4)

    assert gate_surface["active"] is True
    gate_item = gate_surface["items"][0]

    # Bounded invariants
    assert gate_item["authority"] == "non-authoritative"
    assert gate_item["planner_authority_state"] == "not-planner-authority"
    assert gate_item["proactive_execution_state"] == "not-proactive-execution"
    assert gate_item["send_permission_state"] in {"gated-candidate-only", "not-granted"}

    # Gate is grounded in backing thread
    assert gate_item["question_gate_state"] in {"question-gated-candidate", "question-gated-hold"}
    assert gate_item["question_gate_weight"] in {"medium", "high"}


def test_question_gate_surface_is_heartbeat_readable(
    isolated_runtime,
) -> None:
    """The question gate surface shape must be readable by heartbeat
    liveness scoring — specifically summary.active_count and
    summary.current_state must be present and well-formed."""
    db = isolated_runtime.db
    autonomy = isolated_runtime.autonomy_pressure_signal_tracking
    proactive = isolated_runtime.proactive_loop_lifecycle_tracking
    gate = isolated_runtime.proactive_question_gate_tracking

    _insert_initiative_tension(db)
    _insert_open_loop(db)
    _insert_regulation(db)
    _insert_runtime_awareness(db)
    _insert_relation_continuity(db)
    _insert_meaning(db)

    # Build the chain
    autonomy.track_runtime_autonomy_pressure_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    proactive.track_runtime_proactive_loop_lifecycle_signals_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )
    gate.track_runtime_proactive_question_gates_for_visible_turn(
        session_id="smoke-session", run_id="smoke-run",
    )

    # Verify heartbeat-readable shape
    gate_surface = gate.build_runtime_proactive_question_gate_surface(limit=4)
    summary = gate_surface.get("summary", {})

    # These are the exact keys heartbeat liveness reads
    assert isinstance(summary.get("active_count"), int)
    assert summary["active_count"] >= 1
    assert summary.get("current_state") in {"question-gated-candidate", "question-gated-hold"}

    # Proactive loop surface shape heartbeat also reads
    pl_surface = proactive.build_runtime_proactive_loop_lifecycle_surface(limit=6)
    pl_summary = pl_surface.get("summary", {})
    assert isinstance(pl_summary.get("active_count"), int)
    assert pl_summary["active_count"] >= 1
    assert pl_summary.get("current_state") is not None
    assert pl_summary.get("current_kind") is not None
