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
from datetime import datetime, UTC


# ---------------------------------------------------------------------------
# Outcome types
# ---------------------------------------------------------------------------

OUTCOMES = frozenset({"ask_user", "stay_quiet", "continue_internal", "defer", "quiet_hold", "act_on_initiative"})


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
# Quiet Initiative — bounded stille modning af user-facing impulser
# ---------------------------------------------------------------------------

_MAX_HOLD_COUNT = 4      # Max heartbeat ticks before expiry
_PROMOTE_SCORE = 6       # Liveness score needed for quiet→ask_user promotion


@dataclass(slots=True)
class QuietInitiative:
    """A quietly held user-facing initiative under maturation."""
    active: bool = False
    focus: str = ""               # What the initiative is about
    reason_code: str = ""         # Why it was held quiet
    dominant_factor: str = ""     # Original dominant factor
    hold_count: int = 0           # How many ticks it has been held
    created_at: str = ""
    last_seen_at: str = ""
    original_decision_type: str = ""   # propose / ping
    state: str = "holding"        # holding / promoted / expired / released

    def to_dict(self) -> dict[str, object]:
        return {
            "active": self.active,
            "focus": self.focus,
            "reason_code": self.reason_code,
            "dominant_factor": self.dominant_factor,
            "hold_count": self.hold_count,
            "max_hold_count": _MAX_HOLD_COUNT,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "original_decision_type": self.original_decision_type,
            "state": self.state,
        }


# Module-level quiet initiative (in-memory, per-process)
_quiet_initiative: QuietInitiative = QuietInitiative()


def get_quiet_initiative() -> dict[str, object]:
    """Return the current quiet initiative state for MC observability."""
    return _quiet_initiative.to_dict()


def _start_quiet_hold(
    *,
    focus: str,
    reason_code: str,
    dominant_factor: str,
    decision_type: str,
) -> None:
    """Start or refresh a quiet hold on a user-facing initiative."""
    global _quiet_initiative
    now = datetime.now(UTC).isoformat()
    if _quiet_initiative.active and _quiet_initiative.focus == focus:
        # Same focus: increment hold count
        _quiet_initiative.hold_count += 1
        _quiet_initiative.last_seen_at = now
    else:
        # New initiative: replace
        _quiet_initiative = QuietInitiative(
            active=True,
            focus=focus,
            reason_code=reason_code,
            dominant_factor=dominant_factor,
            hold_count=1,
            created_at=now,
            last_seen_at=now,
            original_decision_type=decision_type,
            state="holding",
        )


def _expire_quiet_initiative(reason: str = "expired") -> None:
    """Mark the current quiet initiative as expired/released."""
    global _quiet_initiative
    if _quiet_initiative.active:
        _quiet_initiative.active = False
        _quiet_initiative.state = reason
        _quiet_initiative.last_seen_at = datetime.now(UTC).isoformat()


def _promote_quiet_initiative() -> None:
    """Mark the current quiet initiative as promoted to user-facing."""
    global _quiet_initiative
    if _quiet_initiative.active:
        _quiet_initiative.active = False
        _quiet_initiative.state = "promoted"
        _quiet_initiative.last_seen_at = datetime.now(UTC).isoformat()


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
    cognitive_frame: dict[str, object] | None = None,
    policy_allow_propose: bool = False,
    policy_allow_ping: bool = False,
) -> ConflictTrace:
    """Resolve competing pressures into a single bounded initiative outcome.

    Called after liveness recovery, before policy validation.
    Can downgrade propose/ping to stay_quiet, continue_internal, or quiet_hold
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

    frame = cognitive_frame or {}
    frame_counts = frame.get("counts") or {}
    continuity_pressure = str(frame.get("continuity_pressure") or "low")
    salient_count = int(
        frame_counts.get("salient_items") or len(frame.get("salient_items") or [])
    )
    gated_affordances = int(frame_counts.get("gated_affordances") or 0)
    inner_forces = int(frame_counts.get("inner_forces") or 0)
    integrated_signal_inputs = int(frame_counts.get("integrated_signal_inputs") or 0)
    active_constraints = [
        str(item).strip()
        for item in (frame.get("active_constraints") or [])
        if str(item).strip()
    ]

    frame_crowded = (
        continuity_pressure == "medium"
        or salient_count >= 3
        or inner_forces >= 2
        or len(active_constraints) >= 1
    )
    frame_overloaded = (
        continuity_pressure == "high"
        or salient_count >= 4
        or gated_affordances >= 2
        or len(active_constraints) >= 2
    )

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
    if continuity_pressure in {"medium", "high"}:
        factors.append(f"frame-carry:{continuity_pressure}")
    if salient_count >= 3:
        factors.append(f"frame-salient:{salient_count}")
    if gated_affordances > 0:
        factors.append(f"frame-gated:{gated_affordances}")
    if active_constraints:
        factors.append(f"frame-constraints:{len(active_constraints)}")
    if integrated_signal_inputs >= 8:
        factors.append(f"frame-signals:{integrated_signal_inputs}")
    if _quiet_initiative.active:
        factors.append(f"quiet-hold:{_quiet_initiative.hold_count}/{_MAX_HOLD_COUNT}")

    trace.competing_factors = factors
    trace.input_snapshot["liveness_state"] = liveness_state
    trace.input_snapshot["liveness_score"] = liveness_score
    trace.input_snapshot["gate_active"] = gate_active
    trace.input_snapshot["gate_state"] = gate_state
    trace.input_snapshot["gate_send_permission"] = gate_send_permission
    trace.input_snapshot["ap_state"] = ap_state
    trace.input_snapshot["open_count"] = open_count
    trace.input_snapshot["softening_count"] = softening_count
    trace.input_snapshot["frame_continuity_pressure"] = continuity_pressure
    trace.input_snapshot["frame_salient_count"] = salient_count
    trace.input_snapshot["frame_gated_affordances"] = gated_affordances
    trace.input_snapshot["frame_inner_forces"] = inner_forces
    trace.input_snapshot["frame_active_constraints"] = active_constraints
    trace.input_snapshot["frame_integrated_signal_inputs"] = integrated_signal_inputs
    trace.input_snapshot["quiet_hold_active"] = _quiet_initiative.active
    trace.input_snapshot["quiet_hold_count"] = _quiet_initiative.hold_count

    # --- Resolution logic (deterministic, priority-ordered) ---

    # Rule 0: noop decisions pass through — no conflict to resolve
    if decision_type == "noop":
        # Check quiet initiative expiry on noop
        if _quiet_initiative.active:
            _quiet_initiative.hold_count += 1
            _quiet_initiative.last_seen_at = datetime.now(UTC).isoformat()
            if _quiet_initiative.hold_count > _MAX_HOLD_COUNT:
                _expire_quiet_initiative("expired-noop")

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

        if frame_overloaded and integrated_signal_inputs >= 8:
            trace.outcome = "continue_internal"
            trace.dominant_factor = (
                f"frame-pressure:{continuity_pressure}"
                f"+salient:{salient_count}"
                f"+signals:{integrated_signal_inputs}"
            )
            trace.reason_code = "noop-with-frame-pressure"
            trace.summary = (
                "Quiet externally but the cognitive frame is crowded enough "
                "to warrant internal continuation."
            )
            return trace

        trace.outcome = "stay_quiet"
        trace.dominant_factor = "no-active-pressure"
        trace.reason_code = "noop-baseline"
        trace.summary = "No competing pressures."
        return trace

    # Rule 0.5: Initiative-based action — if pending initiatives exist,
    # allow internal action without requiring question gate or high liveness.
    # This is the thought→action bridge: inner voice detects initiative,
    # heartbeat can act on it without needing user permission (it's internal work).
    if decision_type == "initiative":
        try:
            from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives
            pending = get_pending_initiatives()
            if pending:
                if _quiet_initiative.active:
                    _promote_quiet_initiative()
                trace.outcome = "act_on_initiative"
                trace.dominant_factor = f"pending-initiatives:{len(pending)}"
                trace.reason_code = "initiative-detected"
                trace.summary = f"Acting on {len(pending)} pending initiative(s) from inner voice."
                return trace
        except Exception:
            pass
        trace.outcome = "continue_internal"
        trace.dominant_factor = "no-pending-initiatives"
        trace.reason_code = "initiative-empty"
        trace.summary = "Initiative decision but no pending initiatives — continuing internal."
        return trace

    # Rule 1: Policy gate — if propose/ping not allowed, defer
    if decision_type in {"propose", "ping"} and not policy_allow_propose and not policy_allow_ping:
        _expire_quiet_initiative("policy-blocked")
        trace.outcome = "defer"
        trace.blocked_by = "policy-gate"
        trace.dominant_factor = "policy-not-allowed"
        trace.reason_code = "policy-blocked"
        trace.summary = "Propose/ping not allowed by policy."
        return trace

    # Rule 2: Question gate active but send not granted
    # PROPOSE → continue internal (don't bother user with proposals)
    # PING → allow if policy permits (pings are lightweight, don't need send-grant)
    if gate_active and gate_send_permission == "not-granted":
        if decision_type == "propose":
            trace.outcome = "continue_internal"
            trace.blocked_by = "question-gate-not-granted"
            trace.dominant_factor = f"question-gate:{gate_state}"
            trace.reason_code = "gate-active-send-not-granted"
            trace.summary = "Question thread active but send not granted — propose continues internal."
            return trace
        # ping falls through to policy check (rule 1 already verified policy_allow_ping)

    # Rule 2.5: Quiet initiative promotion check
    # If we already have a quiet hold and conditions have improved, promote
    if _quiet_initiative.active and decision_type in {"propose", "ping"}:
        if liveness_score >= _PROMOTE_SCORE and liveness_pressure in {"medium", "high"}:
            # Conditions improved enough — promote to ask_user
            _promote_quiet_initiative()
            trace.outcome = "ask_user"
            trace.dominant_factor = f"quiet-hold-promoted(held={_quiet_initiative.hold_count})+liveness:{liveness_state}(score={liveness_score})"
            trace.reason_code = "quiet-hold-promoted"
            trace.summary = f"Quiet initiative promoted after {_quiet_initiative.hold_count} holds — conditions now sufficient."
            return trace

        # Still not ready — continue holding
        if _quiet_initiative.hold_count >= _MAX_HOLD_COUNT:
            _expire_quiet_initiative("max-holds-reached")
            trace.outcome = "stay_quiet"
            trace.dominant_factor = f"quiet-hold-expired(held={_MAX_HOLD_COUNT})"
            trace.reason_code = "quiet-hold-expired"
            trace.summary = f"Quiet initiative expired after {_MAX_HOLD_COUNT} holds without sufficient improvement."
            return trace

        # Continue the quiet hold
        _quiet_initiative.hold_count += 1
        _quiet_initiative.last_seen_at = datetime.now(UTC).isoformat()
        trace.outcome = "quiet_hold"
        trace.dominant_factor = f"quiet-hold-continuing(held={_quiet_initiative.hold_count}/{_MAX_HOLD_COUNT})"
        trace.reason_code = "quiet-hold-continue"
        trace.summary = f"Quiet initiative held ({_quiet_initiative.hold_count}/{_MAX_HOLD_COUNT}) — not yet ready for user-facing."
        return trace

    # Rule 3: Liveness too low for user-facing action — quiet hold candidate
    if decision_type in {"propose", "ping"} and liveness_state in {"quiet", "watchful"}:
        if liveness_score < 5:
            # Has enough backing signal to be worth holding quietly?
            has_backing = (open_count > 0 or gate_active or ap_state not in {"none", ""})
            if has_backing and len(factors) >= 2:
                # Start quiet hold instead of just dropping
                focus = (
                    gate_state if gate_active
                    else ap_state if ap_state not in {"none", ""}
                    else f"open-loops:{open_count}"
                )
                _start_quiet_hold(
                    focus=focus,
                    reason_code="liveness-below-but-backed",
                    dominant_factor=f"liveness:{liveness_state}(score={liveness_score})",
                    decision_type=decision_type,
                )
                trace.outcome = "quiet_hold"
                trace.blocked_by = "liveness-insufficient"
                trace.dominant_factor = f"liveness:{liveness_state}(score={liveness_score})"
                trace.reason_code = "quiet-hold-started"
                trace.summary = "Liveness too low but backing signal present — holding quietly."
                return trace

            # No backing signal — just drop
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

    # Rule 4.5: Broader frame pressure should also bias toward internal work
    # before user-facing action when no explicit question gate is active.
    if decision_type in {"propose", "ping"} and not gate_active and liveness_pressure != "high":
        if frame_overloaded or (frame_crowded and integrated_signal_inputs >= 8):
            trace.outcome = "continue_internal"
            trace.dominant_factor = (
                f"frame-pressure:{continuity_pressure}"
                f"+salient:{salient_count}"
                f"+constraints:{len(active_constraints)}"
            )
            trace.reason_code = "frame-pressure-prefers-internal"
            trace.summary = (
                "Cognitive frame pressure is elevated — internal continuation "
                "preferred before user-facing action."
            )
            return trace

    # Rule 5: Strong aligned pressure — allow ask_user
    if decision_type in {"propose", "ping"}:
        # Release any quiet hold — we're going user-facing
        if _quiet_initiative.active:
            _promote_quiet_initiative()

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
        if _quiet_initiative.active:
            _promote_quiet_initiative()
        trace.outcome = "ask_user"
        trace.dominant_factor = f"liveness:{liveness_state}(medium)"
        trace.reason_code = "medium-pressure-allow"
        trace.summary = "Medium liveness pressure — allowing with competing factors noted."
        return trace

    # Default: allow through as ask_user for propose/ping, stay_quiet for others
    if decision_type in {"propose", "ping"}:
        if _quiet_initiative.active:
            _promote_quiet_initiative()
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

    if trace.outcome == "quiet_hold":
        return {
            **decision,
            "decision_type": "noop",
            "reason": f"conflict-quiet-hold: {trace.reason_code} — {decision.get('reason', '')}",
            "summary": trace.summary,
        }

    if trace.outcome == "act_on_initiative":
        return {
            **decision,
            "decision_type": "execute",
            "execute_action": "act_on_initiative",
            "reason": f"conflict-initiative: {trace.reason_code} — {decision.get('reason', '')}",
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
    result = _last_conflict_trace.to_dict()
    result["quiet_initiative"] = get_quiet_initiative()
    return result


def set_last_conflict_trace(trace: ConflictTrace) -> None:
    """Store the latest conflict trace for MC observability."""
    global _last_conflict_trace
    _last_conflict_trace = trace
