"""Tests for bounded conflict resolution — heartbeat initiative arbitration."""
from __future__ import annotations

from apps.api.jarvis_api.services.conflict_resolution import (
    ConflictTrace,
    resolve_heartbeat_initiative_conflict,
    apply_conflict_resolution,
    OUTCOMES,
)


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


# ---------------------------------------------------------------------------
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
