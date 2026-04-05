"""Tests for bounded self-deception guard — deterministic truth-constraint on user-facing stance."""
from __future__ import annotations

from apps.api.jarvis_api.services.self_deception_guard import (
    evaluate_self_deception_guard,
    DeceptionGuardTrace,
    GuardConstraint,
    GUARD_OUTCOMES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gate(*, active_count=0, send_permission="not-granted"):
    return {"summary": {"active_count": active_count, "current_send_permission_state": send_permission}}


def _autonomy(*, current_state="none"):
    return {"summary": {"current_state": current_state}}


def _loops(*, open_count=0, closed_count=0, softening_count=0):
    return {"summary": {"open_count": open_count, "closed_count": closed_count, "softening_count": softening_count}}


def _caps(*, active=0, gated=0):
    return {
        "active_capabilities": {"items": [{"label": f"cap-{i}"} for i in range(active)]},
        "approval_gated": {"items": [{"label": f"gated-{i}"} for i in range(gated)]},
    }


def _conflict(*, outcome="stay_quiet"):
    return {"outcome": outcome}


def _qi(*, active=False):
    return {"active": active}


# ---------------------------------------------------------------------------
# Outcome validity
# ---------------------------------------------------------------------------

def test_all_outcomes_are_in_allowed_set() -> None:
    trace = evaluate_self_deception_guard()
    for c in trace.constraints:
        assert c.outcome in GUARD_OUTCOMES


# ---------------------------------------------------------------------------
# Execution claim guard
# ---------------------------------------------------------------------------

def test_blocks_execution_claim_without_evidence() -> None:
    """When no execution evidence and conflict was internal-only, block execution claims."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=0),
        conflict_trace=_conflict(outcome="continue_internal"),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "block_execution_claim" in outcomes
    assert trace.execution_evidence is False
    assert trace.internal_continuation_only is True


def test_execution_guard_mentions_write_scoping() -> None:
    """Execution claim guard text must scope to write/mutating actions, not all actions."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=0),
        conflict_trace=_conflict(outcome="continue_internal"),
    )
    exec_constraints = [c for c in trace.constraints if c.claim_type == "execution"]
    assert len(exec_constraints) > 0
    guard_text = exec_constraints[0].guard_line
    assert "write or mutating" in guard_text.lower() or "write" in guard_text.lower()
    assert "Read-only capability results are factual" in guard_text


def test_no_execution_block_when_evidence_present() -> None:
    """When there is execution evidence (closed loops), allow execution claims."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=2),
        conflict_trace=_conflict(outcome="ask_user"),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "block_execution_claim" not in outcomes
    assert trace.execution_evidence is True


# ---------------------------------------------------------------------------
# Completion claim guard
# ---------------------------------------------------------------------------

def test_blocks_completion_claim_without_closed_loops() -> None:
    """Without closed loops, completion claims must be blocked."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=2, closed_count=0),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "block_completion_claim" in outcomes


def test_no_completion_block_with_closed_loops() -> None:
    """With closed loops, completion claims are allowed."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=1),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "block_completion_claim" not in outcomes


# ---------------------------------------------------------------------------
# Capability reframe guard
# ---------------------------------------------------------------------------

def test_reframes_when_only_gated_capabilities() -> None:
    """When capabilities are only gated (not active), reframe."""
    trace = evaluate_self_deception_guard(
        capability_truth=_caps(active=0, gated=3),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "reframe_capability_only" in outcomes
    assert trace.capability_state == "gated"


def test_no_reframe_when_active_capabilities() -> None:
    """When active capabilities exist, no capability reframe."""
    trace = evaluate_self_deception_guard(
        capability_truth=_caps(active=2, gated=1),
    )
    cap_reframes = [c for c in trace.constraints if c.claim_type == "capability"]
    assert len(cap_reframes) == 0
    assert trace.capability_state == "active"


def test_no_capability_reframe_when_callable_capabilities_exist() -> None:
    """When callable (non-gated) runtime capabilities exist alongside gated ones, no reframe."""
    trace = evaluate_self_deception_guard(
        capability_truth={
            "active_capabilities": {"items": []},
            "approval_gated": {"items": [{"label": "gated-0"}]},
            "runtime_capabilities": [
                {"capability_id": "tool:read-workspace-memory", "available_now": True},
            ],
        },
    )
    cap_reframes = [c for c in trace.constraints if c.claim_type == "capability"]
    assert len(cap_reframes) == 0


# ---------------------------------------------------------------------------
# Permission reframe guard
# ---------------------------------------------------------------------------

def test_reframes_when_gate_active_but_send_not_granted() -> None:
    """Question gate active + send not granted = reframe permission needed."""
    trace = evaluate_self_deception_guard(
        question_gate=_gate(active_count=1, send_permission="not-granted"),
    )
    outcomes = [c.outcome for c in trace.constraints]
    assert "reframe_permission_needed" in outcomes
    assert trace.gate_send_permission == "not-granted"


def test_no_permission_reframe_when_gate_inactive() -> None:
    """No gate active = no permission reframe."""
    trace = evaluate_self_deception_guard(
        question_gate=_gate(active_count=0, send_permission="not-granted"),
    )
    perm_reframes = [c for c in trace.constraints if c.claim_type == "permission"]
    assert len(perm_reframes) == 0


# ---------------------------------------------------------------------------
# Quiet initiative guard
# ---------------------------------------------------------------------------

def test_reframes_when_quiet_initiative_active() -> None:
    """Quiet initiative is internal maturation — cannot be presented as external action."""
    trace = evaluate_self_deception_guard(
        quiet_initiative=_qi(active=True),
    )
    initiative_constraints = [c for c in trace.constraints if c.claim_type == "initiative"]
    assert len(initiative_constraints) > 0
    assert initiative_constraints[0].reason_code == "quiet-initiative-is-internal"


def test_no_initiative_guard_when_qi_inactive() -> None:
    """No quiet initiative = no initiative guard."""
    trace = evaluate_self_deception_guard(
        quiet_initiative=_qi(active=False),
    )
    initiative_constraints = [c for c in trace.constraints if c.claim_type == "initiative"]
    assert len(initiative_constraints) == 0


# ---------------------------------------------------------------------------
# Guard lines for prompt injection
# ---------------------------------------------------------------------------

def test_guard_lines_are_prompt_injectable() -> None:
    """Guard lines must be non-empty strings suitable for prompt insertion."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=0),
        conflict_trace=_conflict(outcome="continue_internal"),
        question_gate=_gate(active_count=1, send_permission="not-granted"),
    )
    lines = trace.guard_lines()
    assert len(lines) >= 2
    for line in lines:
        assert isinstance(line, str)
        assert line.startswith("- GUARD:")


def test_allow_produces_no_guard_lines() -> None:
    """When everything is clean, no guard lines needed."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=0, closed_count=1),
        conflict_trace=_conflict(outcome="ask_user"),
        capability_truth=_caps(active=2),
    )
    lines = trace.guard_lines()
    assert len(lines) == 0


# ---------------------------------------------------------------------------
# Trace quality
# ---------------------------------------------------------------------------

def test_trace_to_dict_is_complete() -> None:
    """to_dict must produce a complete machine-readable dict."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=0),
        conflict_trace=_conflict(outcome="quiet_hold"),
        quiet_initiative=_qi(active=True),
    )
    d = trace.to_dict()
    assert "constraints" in d
    assert "has_blocks" in d
    assert "has_reframes" in d
    assert "capability_state" in d
    assert "permission_state" in d
    assert "execution_evidence" in d
    assert "quiet_initiative_active" in d
    assert d["quiet_initiative_active"] is True
