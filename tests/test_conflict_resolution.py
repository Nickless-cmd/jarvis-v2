"""Tests for bounded conflict resolution — heartbeat initiative arbitration."""
from __future__ import annotations

import pytest

import core.services.conflict_resolution as cr_module
from core.services.conflict_resolution import (
    ConflictTrace,
    QuietInitiative,
    resolve_heartbeat_initiative_conflict,
    apply_conflict_resolution,
    get_quiet_initiative,
    OUTCOMES,
    _expire_quiet_initiative,
    _MAX_HOLD_COUNT,
)


@pytest.fixture(autouse=True)
def _reset_quiet_initiative():
    """Reset quiet initiative state between tests."""
    cr_module._quiet_initiative = QuietInitiative()
    yield
    cr_module._quiet_initiative = QuietInitiative()


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _liveness(*, state="quiet", pressure="low", score=0):
    return {
        "liveness_state": state,
        "liveness_pressure": pressure,
        "liveness_score": score,
    }


def _gate(*, active_count=0, current_state="none", send_permission="not-granted"):
    return {
        "summary": {
            "active_count": active_count,
            "current_state": current_state,
            "current_send_permission_state": send_permission,
        },
    }


def _autonomy(*, current_state="none", current_type="none"):
    return {
        "summary": {
            "current_state": current_state,
            "current_type": current_type,
        },
    }


def _loops(*, open_count=0, softening_count=0):
    return {
        "summary": {
            "open_count": open_count,
            "softening_count": softening_count,
        },
    }


# ---------------------------------------------------------------------------
# Outcome validity tests
# ---------------------------------------------------------------------------


def test_all_outcomes_are_in_allowed_set() -> None:
    """Every outcome from the resolver must be in OUTCOMES."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="noop",
        liveness=_liveness(),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
    )
    assert trace.outcome in OUTCOMES


def test_noop_baseline_stays_quiet() -> None:
    """A noop with no pressure should stay quiet."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="noop",
        liveness=_liveness(),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
    )
    assert trace.outcome == "stay_quiet"
    assert trace.reason_code == "noop-baseline"


# ---------------------------------------------------------------------------
# Gate vs send permission tests
# ---------------------------------------------------------------------------


def test_question_gate_active_but_send_not_granted_downgrades_to_internal() -> None:
    """Question-gated ≠ execution-granted. Must downgrade propose to internal."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="high", score=8),
        question_gate=_gate(active_count=1, current_state="question-gated-candidate",
                          send_permission="not-granted"),
        autonomy_pressure=_autonomy(current_state="question-worthy"),
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "gate-active-send-not-granted"
    assert trace.blocked_by == "question-gate-not-granted"


def test_question_gate_with_gated_candidate_permission_allows_ask_user() -> None:
    """When gate is active AND send permission is gated-candidate, allow ask_user."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=6),
        question_gate=_gate(active_count=1, current_state="question-gated-candidate",
                          send_permission="gated-candidate-only"),
        autonomy_pressure=_autonomy(current_state="question-worthy"),
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )
    assert trace.outcome == "ask_user"
    assert trace.reason_code == "aligned-question-pressure"


# ---------------------------------------------------------------------------
# Liveness threshold tests
# ---------------------------------------------------------------------------


def test_low_liveness_blocks_propose() -> None:
    """Propose with quiet/watchful liveness and low score should stay quiet."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
        policy_allow_propose=True,
    )
    assert trace.outcome == "stay_quiet"
    assert trace.reason_code == "liveness-below-threshold"


def test_strong_liveness_allows_ask_user() -> None:
    """Propose-worthy liveness with high score allows ask_user."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="propose-worthy", pressure="high", score=10),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )
    assert trace.outcome == "ask_user"
    assert trace.reason_code == "strong-liveness-pressure"


# ---------------------------------------------------------------------------
# Conductor mode tests
# ---------------------------------------------------------------------------


def test_consolidate_mode_prefers_internal() -> None:
    """Conductor in consolidate mode should prefer internal over user-facing."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=6),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        conductor_mode="consolidate",
        policy_allow_propose=True,
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "conductor-prefers-internal"


def test_noop_with_internal_pressure_becomes_continue_internal() -> None:
    """A noop with open loops + reflect mode should become continue_internal."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="noop",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=5),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=_loops(open_count=2),
        conductor_mode="reflect",
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "noop-with-internal-pressure"


def test_noop_with_crowded_frame_becomes_continue_internal() -> None:
    """A noop should continue internally when the broader frame is overloaded."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="noop",
        liveness=_liveness(state="watchful", pressure="low", score=2),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
        cognitive_frame={
            "continuity_pressure": "high",
            "active_constraints": [
                "Stay within active review gate.",
                "Do not fragment attention further.",
            ],
            "counts": {
                "salient_items": 4,


                "gated_affordances": 2,
                "inner_forces": 1,
                "integrated_signal_inputs": 12,
            },
        },
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "noop-with-frame-pressure"


# ---------------------------------------------------------------------------

def test_crowded_frame_prefers_internal_even_when_mode_is_watch() -> None:
    """Broader frame pressure should steer propose toward internal continuation."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=6),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=1),
        conductor_mode="watch",
        cognitive_frame={
            "continuity_pressure": "medium",
            "active_constraints": ["Need to keep continuity intact."],
            "counts": {
                "salient_items": 4,
                "gated_affordances": 1,
                "inner_forces": 2,
                "integrated_signal_inputs": 10,
            },
        },
        policy_allow_propose=True,
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "frame-pressure-prefers-internal"


# Policy gate tests
# ---------------------------------------------------------------------------


def test_policy_not_allowed_defers() -> None:
    """Propose/ping when policy forbids both should defer."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="propose-worthy", pressure="high", score=10),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
        policy_allow_propose=False,
        policy_allow_ping=False,
    )
    assert trace.outcome == "defer"
    assert trace.reason_code == "policy-blocked"
    assert trace.blocked_by == "policy-gate"


def test_trace_captures_frame_pressure_inputs() -> None:
    """Conflict trace should expose the broader frame inputs used for arbitration."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=6),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=_loops(open_count=1),
        cognitive_frame={
            "continuity_pressure": "medium",
            "active_constraints": ["Avoid widening the surface."],
            "counts": {
                "salient_items": 3,
                "gated_affordances": 1,
                "inner_forces": 2,
                "integrated_signal_inputs": 9,
            },
        },
        policy_allow_propose=True,
    )
    assert trace.input_snapshot["frame_continuity_pressure"] == "medium"
    assert trace.input_snapshot["frame_salient_count"] == 3
    assert trace.input_snapshot["frame_gated_affordances"] == 1
    assert trace.input_snapshot["frame_inner_forces"] == 2
    assert trace.input_snapshot["frame_active_constraints"] == ["Avoid widening the surface."]
    assert trace.input_snapshot["frame_integrated_signal_inputs"] == 9


# ---------------------------------------------------------------------------
# Trace quality tests
# ---------------------------------------------------------------------------


def test_trace_has_competing_factors() -> None:
    """Trace should list competing factors when multiple pressures exist."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="high", score=8),
        question_gate=_gate(active_count=1, current_state="question-gated-candidate",
                          send_permission="gated-candidate-only"),
        autonomy_pressure=_autonomy(current_state="question-worthy",
                                   current_type="question-pressure"),
        open_loops=_loops(open_count=2, softening_count=1),
        policy_allow_propose=True,
    )
    assert len(trace.competing_factors) >= 3
    assert any("liveness" in f for f in trace.competing_factors)
    assert any("question-gate" in f for f in trace.competing_factors)
    assert any("open-loops" in f for f in trace.competing_factors)


def test_trace_to_dict_is_complete() -> None:
    """to_dict must produce a complete machine-readable dict."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=6),
        question_gate=_gate(active_count=1, send_permission="gated-candidate-only"),
        autonomy_pressure=None,
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )
    d = trace.to_dict()
    assert d["outcome"] in OUTCOMES
    assert isinstance(d["competing_factors"], list)
    assert isinstance(d["input_snapshot"], dict)
    assert d["input_snapshot"]["decision_type"] == "propose"
    assert "liveness_score" in d["input_snapshot"]


# ---------------------------------------------------------------------------
# apply_conflict_resolution tests
# ---------------------------------------------------------------------------


def test_apply_stay_quiet_downgrades_to_noop() -> None:
    """stay_quiet outcome should change decision to noop."""
    decision = {"decision_type": "propose", "reason": "test", "summary": "test"}
    trace = ConflictTrace(outcome="stay_quiet", reason_code="test-quiet")
    result = apply_conflict_resolution(decision=decision, trace=trace)
    assert result["decision_type"] == "noop"
    assert "conflict-resolution" in result["reason"]


def test_apply_continue_internal_downgrades_to_noop() -> None:
    """continue_internal outcome should change decision to noop."""
    decision = {"decision_type": "propose", "reason": "test", "summary": "test"}
    trace = ConflictTrace(outcome="continue_internal", reason_code="test-internal")
    result = apply_conflict_resolution(decision=decision, trace=trace)
    assert result["decision_type"] == "noop"
    assert "conflict-internal" in result["reason"]


def test_apply_ask_user_preserves_decision() -> None:
    """ask_user outcome should preserve the original decision."""
    decision = {"decision_type": "propose", "reason": "test", "summary": "test"}
    trace = ConflictTrace(outcome="ask_user", reason_code="test-allow")
    result = apply_conflict_resolution(decision=decision, trace=trace)
    assert result["decision_type"] == "propose"
    assert result["reason"] == "test"


def test_apply_defer_downgrades_to_noop() -> None:
    """defer outcome should change decision to noop."""
    decision = {"decision_type": "ping", "reason": "test", "summary": "test"}
    trace = ConflictTrace(outcome="defer", reason_code="test-defer")
    result = apply_conflict_resolution(decision=decision, trace=trace)
    assert result["decision_type"] == "noop"
    assert "conflict-deferred" in result["reason"]


# ---------------------------------------------------------------------------
# Internal continuation execution tests
# ---------------------------------------------------------------------------


def test_execute_continue_internal_calls_brain_continuity(isolated_runtime) -> None:
    """continue_internal must attempt private brain continuity motor."""
    from core.services.heartbeat_runtime import (
        _execute_continue_internal,
    )

    trace = ConflictTrace(
        outcome="continue_internal",
        reason_code="test-internal",
        dominant_factor="test",
    )

    result = _execute_continue_internal(
        conflict_trace=trace,
        trigger="test",
    )

    # Without brain records, it should skip but still report
    assert result["applied"] is False
    assert result["action"] == "skipped"
    assert result["reason"] in {
        "no-active-brain-records",
        "insufficient-diversity",
        "near-duplicate-consolidation",
    }


def test_execute_continue_internal_with_brain_records(isolated_runtime) -> None:
    """continue_internal with enough brain records should consolidate."""
    from core.services.heartbeat_runtime import (
        _execute_continue_internal,
    )
    from core.services.session_distillation import (
        insert_private_brain_record,
    )
    from datetime import datetime, UTC

    now = datetime.now(UTC).isoformat()
    # Insert diverse brain records so continuity motor can consolidate
    for i, rtype in enumerate(["carry", "reflection", "observation"]):
        insert_private_brain_record(
            record_id=f"test-brain-{i}",
            record_type=rtype,
            layer="private_brain",
            session_id="test-session",
            run_id="test-run",
            focus=f"focus-{rtype}",
            summary=f"Summary for {rtype} brain record number {i}.",
            detail=f"Detail for {rtype}",
            source_signals="test",
            confidence="medium",
            created_at=now,
        )

    trace = ConflictTrace(
        outcome="continue_internal",
        reason_code="test-internal-with-data",
        dominant_factor="test",
    )

    result = _execute_continue_internal(
        conflict_trace=trace,
        trigger="test",
    )

    assert result["applied"] is True
    assert result["action"] == "consolidated"
    assert result["continuity_mode"] != ""
    assert result["record_id"] != ""


def test_stay_quiet_does_not_trigger_internal_continuation() -> None:
    """stay_quiet should NOT be the same as continue_internal."""
    trace_quiet = ConflictTrace(outcome="stay_quiet", reason_code="test-quiet")
    trace_internal = ConflictTrace(outcome="continue_internal", reason_code="test-internal")

    # stay_quiet and continue_internal both become noop in decision
    decision = {"decision_type": "propose", "reason": "test", "summary": "test"}
    result_quiet = apply_conflict_resolution(decision=decision, trace=trace_quiet)
    result_internal = apply_conflict_resolution(decision=decision, trace=trace_internal)

    # Both become noop
    assert result_quiet["decision_type"] == "noop"
    assert result_internal["decision_type"] == "noop"

    # But they have different reason markers
    assert "conflict-resolution" in result_quiet["reason"]
    assert "conflict-internal" in result_internal["reason"]
    assert result_quiet["reason"] != result_internal["reason"]


def test_continue_internal_observability_fields() -> None:
    """The internal continuation result must have all required observability fields."""
    from core.services.heartbeat_runtime import (
        _execute_continue_internal,
    )

    trace = ConflictTrace(
        outcome="continue_internal",
        reason_code="test-obs",
        dominant_factor="test-factor",
    )

    result = _execute_continue_internal(
        conflict_trace=trace,
        trigger="test-obs",
    )

    # Must have all required fields regardless of whether it applied
    assert "applied" in result
    assert "action" in result
    assert isinstance(result["applied"], bool)
    assert isinstance(result["action"], str)


# ---------------------------------------------------------------------------
# Quiet initiative tests
# ---------------------------------------------------------------------------


def test_low_liveness_with_backing_starts_quiet_hold() -> None:
    """A propose with low liveness but backing signals should start quiet hold.
    Gate send_permission must not be 'not-granted' to avoid Rule 2 interception."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,  # No gate — backing comes from autonomy + loops
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert trace.outcome == "quiet_hold"
    assert trace.reason_code == "quiet-hold-started"

    qi = get_quiet_initiative()
    assert qi["active"] is True
    assert qi["state"] == "holding"
    assert qi["hold_count"] == 1


def test_low_liveness_without_backing_stays_quiet() -> None:
    """A propose with low liveness and no backing should stay quiet, not hold."""
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="quiet", pressure="low", score=2),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
        policy_allow_propose=True,
    )
    assert trace.outcome == "stay_quiet"
    assert trace.reason_code == "liveness-below-threshold"

    qi = get_quiet_initiative()
    assert qi["active"] is False


def test_quiet_hold_continues_across_ticks() -> None:
    """Repeated resolves with same backing should continue the hold."""
    # First tick — starts hold
    resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert get_quiet_initiative()["hold_count"] == 1

    # Second tick — continues hold
    trace2 = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert trace2.outcome == "quiet_hold"
    assert trace2.reason_code == "quiet-hold-continue"
    assert get_quiet_initiative()["hold_count"] == 2


def test_quiet_hold_promotes_when_liveness_improves() -> None:
    """Quiet hold should promote to ask_user when liveness improves."""
    # Start hold (no gate to avoid Rule 2)
    resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert get_quiet_initiative()["active"] is True

    # Liveness improves — promote
    trace2 = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=7),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert trace2.outcome == "ask_user"
    assert trace2.reason_code == "quiet-hold-promoted"
    assert get_quiet_initiative()["state"] == "promoted"
    assert get_quiet_initiative()["active"] is False


def test_quiet_hold_expires_after_max_holds() -> None:
    """Quiet hold should expire after _MAX_HOLD_COUNT holds."""
    for _ in range(_MAX_HOLD_COUNT):
        resolve_heartbeat_initiative_conflict(
            decision_type="propose",
            liveness=_liveness(state="watchful", pressure="low", score=3),
            question_gate=None,
            autonomy_pressure=_autonomy(current_state="initiative-held"),
            open_loops=_loops(open_count=2),
            policy_allow_propose=True,
        )

    # Next tick should expire
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert trace.outcome == "stay_quiet"
    assert trace.reason_code == "quiet-hold-expired"
    assert get_quiet_initiative()["state"] == "max-holds-reached"


def test_quiet_hold_does_not_bypass_policy() -> None:
    """Quiet hold cannot bypass policy gate."""
    # Start a hold first (no gate to avoid Rule 2)
    resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert get_quiet_initiative()["active"] is True

    # Policy now forbids — should defer and expire hold
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=7),
        question_gate=None,
        autonomy_pressure=None,
        open_loops=None,
        policy_allow_propose=False,
        policy_allow_ping=False,
    )
    assert trace.outcome == "defer"
    assert trace.reason_code == "policy-blocked"
    assert get_quiet_initiative()["state"] == "policy-blocked"


def test_quiet_hold_does_not_bypass_question_gate() -> None:
    """Quiet hold cannot bypass question gate send permission."""
    # Start a hold
    resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=_gate(active_count=1),
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )

    # Gate active but send not granted — should go to continue_internal, not ask_user
    trace = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="alive-pressure", pressure="medium", score=7),
        question_gate=_gate(active_count=1, send_permission="not-granted"),
        autonomy_pressure=_autonomy(current_state="question-worthy"),
        open_loops=_loops(open_count=1),
        policy_allow_propose=True,
    )
    assert trace.outcome == "continue_internal"
    assert trace.reason_code == "gate-active-send-not-granted"


def test_apply_quiet_hold_becomes_noop() -> None:
    """quiet_hold outcome should become noop with conflict-quiet-hold reason."""
    decision = {"decision_type": "propose", "reason": "test", "summary": "test"}
    trace = ConflictTrace(outcome="quiet_hold", reason_code="test-hold")
    result = apply_conflict_resolution(decision=decision, trace=trace)
    assert result["decision_type"] == "noop"
    assert "conflict-quiet-hold" in result["reason"]


def test_quiet_initiative_trace_shows_in_conflict_trace() -> None:
    """Conflict trace input_snapshot should show quiet_hold state."""
    # Start a hold (no gate to avoid Rule 2)
    resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )

    # Next resolve should show quiet hold in input snapshot
    trace2 = resolve_heartbeat_initiative_conflict(
        decision_type="propose",
        liveness=_liveness(state="watchful", pressure="low", score=3),
        question_gate=None,
        autonomy_pressure=_autonomy(current_state="initiative-held"),
        open_loops=_loops(open_count=2),
        policy_allow_propose=True,
    )
    assert trace2.input_snapshot["quiet_hold_active"] is True
    assert trace2.input_snapshot["quiet_hold_count"] >= 1
