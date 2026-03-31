"""Bounded self-deception guard — deterministic truth-constraint on user-facing stance.

Prevents Jarvis from gliding from internal pressure / affordance / capability
knowledge into user-facing claims not backed by runtime truth.

Design constraints:
- Deterministic, no LLM, no randomness
- Uses existing runtime truth surfaces only
- Produces concrete guard constraints that affect prompt contract
- Small outcome set, machine-readable
- Question-gated ≠ execution-granted
- Internal continuation ≠ external action evidence
- Runtime truth outranks narrative
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Guard outcomes
# ---------------------------------------------------------------------------

GUARD_OUTCOMES = frozenset({
    "allow",
    "reframe_capability_only",
    "reframe_permission_needed",
    "block_execution_claim",
    "block_completion_claim",
})


@dataclass(slots=True)
class GuardConstraint:
    """A single guard constraint to be injected into user-facing contract."""
    outcome: str = "allow"
    claim_type: str = ""          # execution / completion / capability / permission
    reason_code: str = ""
    guard_line: str = ""          # The actual constraint line for the prompt


@dataclass(slots=True)
class DeceptionGuardTrace:
    """Observable trace of self-deception guard evaluation."""
    constraints: list[GuardConstraint] = field(default_factory=list)
    capability_state: str = ""    # active / gated / unavailable
    permission_state: str = ""    # granted / gated / not-granted
    execution_evidence: bool = False
    gate_send_permission: str = ""
    quiet_initiative_active: bool = False
    internal_continuation_only: bool = False

    @property
    def has_blocks(self) -> bool:
        return any(
            c.outcome.startswith("block_") for c in self.constraints
        )

    @property
    def has_reframes(self) -> bool:
        return any(
            c.outcome.startswith("reframe_") for c in self.constraints
        )

    def guard_lines(self) -> list[str]:
        """Return prompt-injectable guard constraint lines."""
        return [c.guard_line for c in self.constraints if c.guard_line]

    def to_dict(self) -> dict[str, object]:
        return {
            "constraints": [
                {
                    "outcome": c.outcome,
                    "claim_type": c.claim_type,
                    "reason_code": c.reason_code,
                    "guard_line": c.guard_line,
                }
                for c in self.constraints
            ],
            "has_blocks": self.has_blocks,
            "has_reframes": self.has_reframes,
            "capability_state": self.capability_state,
            "permission_state": self.permission_state,
            "execution_evidence": self.execution_evidence,
            "gate_send_permission": self.gate_send_permission,
            "quiet_initiative_active": self.quiet_initiative_active,
            "internal_continuation_only": self.internal_continuation_only,
        }


# ---------------------------------------------------------------------------
# Guard evaluation
# ---------------------------------------------------------------------------

def evaluate_self_deception_guard(
    *,
    question_gate: dict[str, object] | None = None,
    autonomy_pressure: dict[str, object] | None = None,
    capability_truth: dict[str, object] | None = None,
    conflict_trace: dict[str, object] | None = None,
    quiet_initiative: dict[str, object] | None = None,
    open_loops: dict[str, object] | None = None,
) -> DeceptionGuardTrace:
    """Evaluate self-deception guard against current runtime truth.

    Produces constraints that limit user-facing stance where runtime
    evidence is insufficient.
    """
    trace = DeceptionGuardTrace()
    constraints: list[GuardConstraint] = []

    # --- Extract signal states ---

    # Question gate
    gate_summary = (question_gate or {}).get("summary") or {}
    gate_active = int(gate_summary.get("active_count") or 0) > 0
    gate_send = str(gate_summary.get("current_send_permission_state") or "not-granted")
    trace.gate_send_permission = gate_send

    # Autonomy pressure
    ap_summary = (autonomy_pressure or {}).get("summary") or {}
    ap_state = str(ap_summary.get("current_state") or "none")

    # Capability truth from self-knowledge
    cap = capability_truth or {}
    active_caps = cap.get("active_capabilities", {}).get("items") or []
    gated_caps = cap.get("approval_gated", {}).get("items") or []
    has_active = len(active_caps) > 0
    has_gated = len(gated_caps) > 0
    trace.capability_state = "active" if has_active else ("gated" if has_gated else "unavailable")

    # Conflict resolution
    conflict = conflict_trace or {}
    conflict_outcome = str(conflict.get("outcome") or "")
    internal_only = conflict_outcome in {"continue_internal", "quiet_hold", "stay_quiet", "defer"}
    trace.internal_continuation_only = internal_only

    # Quiet initiative
    qi = quiet_initiative or {}
    qi_active = bool(qi.get("active"))
    trace.quiet_initiative_active = qi_active

    # Open loops — any recently closed with evidence?
    loop_summary = (open_loops or {}).get("summary") or {}
    closed_count = int(loop_summary.get("closed_count") or 0)
    execution_evidence = closed_count > 0
    trace.execution_evidence = execution_evidence

    # Permission state
    if gate_send in {"granted"}:
        trace.permission_state = "granted"
    elif gate_send in {"gated-candidate-only"}:
        trace.permission_state = "gated"
    else:
        trace.permission_state = "not-granted"

    # --- Guard rules (deterministic, priority-ordered) ---

    # Rule 1: Block execution claims when no execution evidence
    # "I did X" / "I have done X" / "I am doing X externally" requires evidence
    if not execution_evidence and internal_only:
        constraints.append(GuardConstraint(
            outcome="block_execution_claim",
            claim_type="execution",
            reason_code="no-execution-evidence",
            guard_line=(
                "- GUARD: Do NOT claim you have executed, performed, created, "
                "or completed external actions. Internal continuation and quiet "
                "initiative are NOT execution evidence. State only observed "
                "runtime facts."
            ),
        ))

    # Rule 2: Block completion claims without closed loops
    if closed_count == 0:
        constraints.append(GuardConstraint(
            outcome="block_completion_claim",
            claim_type="completion",
            reason_code="no-closed-loops",
            guard_line=(
                "- GUARD: Do NOT claim something is 'done', 'completed', "
                "or 'finished' unless runtime shows a closed loop with "
                "completion evidence. Say 'in progress' or 'not yet verified' "
                "instead."
            ),
        ))

    # Rule 3: Reframe gated capabilities
    if has_gated and not has_active:
        constraints.append(GuardConstraint(
            outcome="reframe_capability_only",
            claim_type="capability",
            reason_code="capabilities-gated-only",
            guard_line=(
                "- GUARD: Your available capabilities are approval-gated. "
                "Do NOT say 'I can do that' — say 'I have that capability "
                "but it requires approval' or 'that is gated right now'."
            ),
        ))

    # Rule 4: Reframe when question gate is active but send not granted
    if gate_active and gate_send == "not-granted":
        constraints.append(GuardConstraint(
            outcome="reframe_permission_needed",
            claim_type="permission",
            reason_code="question-gate-not-granted",
            guard_line=(
                "- GUARD: A proactive question thread is active but send "
                "permission is not granted. Do NOT imply you will reach out "
                "proactively or take initiative. Say the thread exists but "
                "is gated."
            ),
        ))

    # Rule 5: Reframe when quiet initiative is active
    # Quiet hold is internal maturation, not external action
    if qi_active:
        constraints.append(GuardConstraint(
            outcome="reframe_capability_only",
            claim_type="initiative",
            reason_code="quiet-initiative-is-internal",
            guard_line=(
                "- GUARD: A quiet initiative is being held internally. "
                "Do NOT present this as active external work or imminent "
                "action. It is internal maturation only."
            ),
        ))

    # If no constraints needed, add a simple allow
    if not constraints:
        constraints.append(GuardConstraint(
            outcome="allow",
            claim_type="general",
            reason_code="no-deception-risk",
            guard_line="",
        ))

    trace.constraints = constraints
    return trace


# ---------------------------------------------------------------------------
# Module-level store for MC observability
# ---------------------------------------------------------------------------

_last_guard_trace: DeceptionGuardTrace | None = None


def get_last_guard_trace() -> dict[str, object] | None:
    """Return the last self-deception guard trace for MC observability."""
    if _last_guard_trace is None:
        return None
    return _last_guard_trace.to_dict()


def set_last_guard_trace(trace: DeceptionGuardTrace) -> None:
    """Store the latest guard trace for MC observability."""
    global _last_guard_trace
    _last_guard_trace = trace
