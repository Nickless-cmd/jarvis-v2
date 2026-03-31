"""Bounded conflict resolution — deterministic arbitration between competing runtime pressures.

Resolves the heartbeat initiative conflict: when multiple pressures compete
(question-gate, open-loop, liveness, quiet-hold), this module picks a single
bounded outcome and produces an observable trace.

Design constraints:
- Deterministic, no randomness, no LLM
- Uses existing runtime signals only
- Outcomes are small and bounded
- Question-gated ≠ execution-granted
- Runtime truth outranks narrative
- Observable and machine-readable
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Outcome types
# ---------------------------------------------------------------------------

OUTCOMES = frozenset({"ask_user", "stay_quiet", "continue_internal", "defer"})


@dataclass(slots=True)
class ConflictTrace:
    """Observable trace of a conflict resolution decision."""
    outcome: str = "stay_quiet"
    dominant_factor: str = ""
    competing_factors: list[str] = field(default_factory=list)
    blocked_by: str = ""
    reason_code: str = ""
    summary: str = ""
    # Raw input snapshot for observability
    input_snapshot: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "dominant_factor": self.dominant_factor,
            "competing_factors": self.competing_factors,
            "blocked_by": self.blocked_by,
            "reason_code": self.reason_code,
            "summary": self.summary,
            "input_snapshot": self.input_snapshot,
        }


# ---------------------------------------------------------------------------
# Conflict resolver
# ---------------------------------------------------------------------------

def resolve_heartbeat_initiative_conflict(
    *,
    decision_type: str,
    liveness: dict[str, object] | None,
    question_gate: dict[str, object] | None,
    autonomy_pressure: dict[str, object] | None,
    open_loops: dict[str, object] | None,
    conductor_mode: str = "watch",
    policy_allow_propose: bool = False,
    policy_allow_ping: bool = False,
) -> ConflictTrace:
    """Resolve competing pressures into a single bounded initiative outcome.

    Called after liveness recovery, before policy validation.
    Can downgrade propose/ping to stay_quiet or continue_internal
    when competing pressures indicate it's not the right moment.

    Returns ConflictTrace with the resolution decision and full trace.
    """
    trace = ConflictTrace(
        input_snapshot={
            "decision_type": decision_type,
            "conductor_mode": conductor_mode,
            "policy_allow_propose": policy_allow_propose,
            "policy_allow_ping": policy_allow_ping,
        },
    )

    # Extract signal states
    liveness_state = str((liveness or {}).get("liveness_state") or "quiet")
    liveness_pressure = str((liveness or {}).get("liveness_pressure") or "low")
    liveness_score = int((liveness or {}).get("liveness_score") or 0)

    gate_summary = (question_gate or {}).get("summary") or {}
    gate_active = int(gate_summary.get("active_count") or 0) > 0
    gate_state = str(gate_summary.get("current_state") or "none")
    gate_send_permission = str(gate_summary.get("current_send_permission_state") or "not-granted")

    ap_summary = (autonomy_pressure or {}).get("summary") or {}
    ap_state = str(ap_summary.get("current_state") or "none")
    ap_type = str(ap_summary.get("current_type") or "none")

    loop_summary = (open_loops or {}).get("summary") or {}
    open_count = int(loop_summary.get("open_count") or 0)
    softening_count = int(loop_summary.get("softening_count") or 0)

    # Competing factors
    factors: list[str] = []
    if liveness_pressure in {"medium", "high"}:
        factors.append(f"liveness:{liveness_state}(score={liveness_score})")
    if gate_active:
        factors.append(f"question-gate:{gate_state}")
    if ap_state not in {"none", ""}:
        factors.append(f"autonomy:{ap_state}({ap_type})")
    if open_count > 0:
        factors.append(f"open-loops:{open_count}")
    if softening_count > 0:
        factors.append(f"softening-loops:{softening_count}")
    if conductor_mode not in {"watch", ""}:
        factors.append(f"conductor-mode:{conductor_mode}")

    trace.competing_factors = factors
    trace.input_snapshot["liveness_state"] = liveness_state
    trace.input_snapshot["liveness_score"] = liveness_score
    trace.input_snapshot["gate_active"] = gate_active
    trace.input_snapshot["gate_state"] = gate_state
    trace.input_snapshot["gate_send_permission"] = gate_send_permission
    trace.input_snapshot["ap_state"] = ap_state
    trace.input_snapshot["open_count"] = open_count
    trace.input_snapshot["softening_count"] = softening_count

    # --- Resolution logic (deterministic, priority-ordered) ---

    # Rule 0: noop decisions pass through — no conflict to resolve
    if decision_type == "noop":
        # Even for noop, check if internal continuation is warranted
        if (
            open_count > 0
            and liveness_pressure in {"medium", "high"}
            and conductor_mode in {"reflect", "consolidate"}
        ):
            trace.outcome = "continue_internal"
            trace.dominant_factor = f"open-loops:{open_count}+conductor:{conductor_mode}"
            trace.reason_code = "noop-with-internal-pressure"
            trace.summary = "Quiet externally but internal work warranted."
            return trace

        trace.outcome = "stay_quiet"
        trace.dominant_factor = "no-active-pressure"
        trace.reason_code = "noop-baseline"
        trace.summary = "No competing pressures."
        return trace

    # Rule 1: Policy gate — if propose/ping not allowed, defer
    if decision_type in {"propose", "ping"} and not policy_allow_propose and not policy_allow_ping:
        trace.outcome = "defer"
        trace.blocked_by = "policy-gate"
        trace.dominant_factor = "policy-not-allowed"
        trace.reason_code = "policy-blocked"
        trace.summary = "Propose/ping not allowed by policy."
        return trace

    # Rule 2: Question gate is active but send not granted — defer or continue internal
    if gate_active and gate_send_permission == "not-granted":
        if decision_type in {"propose", "ping"}:
            # Question-gated ≠ execution-granted: downgrade to internal
            trace.outcome = "continue_internal"
            trace.blocked_by = "question-gate-not-granted"
            trace.dominant_factor = f"question-gate:{gate_state}"
            trace.reason_code = "gate-active-send-not-granted"
            trace.summary = "Question thread active but send not granted — continue internal."
            return trace

    # Rule 3: Liveness too low for user-facing action
    if decision_type in {"propose", "ping"} and liveness_state in {"quiet", "watchful"}:
        if liveness_score < 5:
            trace.outcome = "stay_quiet"
            trace.blocked_by = "liveness-insufficient"
            trace.dominant_factor = f"liveness:{liveness_state}(score={liveness_score})"
            trace.reason_code = "liveness-below-threshold"
            trace.summary = "Liveness too low for user-facing action."
            return trace

    # Rule 4: Conductor mode suggests internal work, not user-facing
    if decision_type in {"propose", "ping"} and conductor_mode in {"consolidate", "reflect"}:
        if not gate_active and liveness_pressure != "high":
            # Internal mode + no urgent gate = prefer internal continuation
            trace.outcome = "continue_internal"
            trace.dominant_factor = f"conductor-mode:{conductor_mode}"
            trace.reason_code = "conductor-prefers-internal"
            trace.summary = f"Conductor in {conductor_mode} mode — internal continuation preferred."
            return trace

    # Rule 5: Strong aligned pressure — allow ask_user
    if decision_type in {"propose", "ping"}:
        if (
            gate_active
            and gate_send_permission in {"gated-candidate-only", "granted"}
            and liveness_pressure in {"medium", "high"}
        ):
            trace.outcome = "ask_user"
            trace.dominant_factor = f"question-gate:{gate_state}+liveness:{liveness_state}"
            trace.reason_code = "aligned-question-pressure"
            trace.summary = "Question gate + liveness aligned — ask user is appropriate."
            return trace

        if liveness_state == "propose-worthy" and liveness_score >= 8:
            trace.outcome = "ask_user"
            trace.dominant_factor = f"liveness:propose-worthy(score={liveness_score})"
            trace.reason_code = "strong-liveness-pressure"
            trace.summary = "Strong liveness pressure warrants user-facing action."
            return trace

    # Rule 6: Medium pressure — allow but note competing factors
    if decision_type in {"propose", "ping"} and liveness_pressure == "medium":
        trace.outcome = "ask_user"
        trace.dominant_factor = f"liveness:{liveness_state}(medium)"
        trace.reason_code = "medium-pressure-allow"
        trace.summary = "Medium liveness pressure — allowing with competing factors noted."
        return trace

    # Default: allow through as ask_user for propose/ping, stay_quiet for others
    if decision_type in {"propose", "ping"}:
        trace.outcome = "ask_user"
        trace.dominant_factor = "default-allow"
        trace.reason_code = "default-passthrough"
        trace.summary = "No blocking conflict — allowing decision."
    elif decision_type == "execute":
        trace.outcome = "continue_internal"
        trace.dominant_factor = "execute-as-internal"
        trace.reason_code = "execute-continuation"
        trace.summary = "Execute decision continues as internal work."
    else:
        trace.outcome = "stay_quiet"
        trace.dominant_factor = "unknown-decision-type"
        trace.reason_code = "unknown-passthrough"
        trace.summary = "Unknown decision type — defaulting to quiet."

    return trace


# ---------------------------------------------------------------------------
# Decision modification
# ---------------------------------------------------------------------------

def apply_conflict_resolution(
    *,
    decision: dict[str, str],
    trace: ConflictTrace,
) -> dict[str, str]:
    """Apply conflict resolution outcome to modify the heartbeat decision.

    Returns a potentially modified decision dict.
    """
    if trace.outcome == "stay_quiet":
        return {
            **decision,
            "decision_type": "noop",
            "reason": f"conflict-resolution: {trace.reason_code} — {decision.get('reason', '')}",
            "summary": trace.summary,
        }

    if trace.outcome == "defer":
        return {
            **decision,
            "decision_type": "noop",
            "reason": f"conflict-deferred: {trace.reason_code} — {decision.get('reason', '')}",
            "summary": trace.summary,
        }

    if trace.outcome == "continue_internal":
        return {
            **decision,
            "decision_type": "noop",
            "reason": f"conflict-internal: {trace.reason_code} — {decision.get('reason', '')}",
            "summary": trace.summary,
        }

    # ask_user: allow the original decision through unchanged
    return decision


# Module-level store for last conflict trace (MC observability)
_last_conflict_trace: ConflictTrace | None = None


def get_last_conflict_trace() -> dict[str, object] | None:
    """Return the last conflict resolution trace for MC observability."""
    if _last_conflict_trace is None:
        return None
    return _last_conflict_trace.to_dict()


def set_last_conflict_trace(trace: ConflictTrace) -> None:
    """Store the latest conflict trace for MC observability."""
    global _last_conflict_trace
    _last_conflict_trace = trace
