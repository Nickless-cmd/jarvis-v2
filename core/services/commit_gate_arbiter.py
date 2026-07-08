"""Pre-eksekverings commit-gate arbitrage — udskilt fra visible_runs (Boy Scout, 2026-07-08).

Naturlig enhed: evaluér de to pre-exec commit-gates (``veto`` + ``decision_gate``) gennem Den
Intelligente Central, observér den deklarerede arbitrage, og producér ét block-udfald. Kaldes
lige før et simpelt værktøj eksekveres i det agentiske loop.

Håndhævelsen er nu GOVERNED pr. gate (jf. ``gate_enforcement``): et RED-verdikt blokerer kun
hvis gaten er enforce-enabled (default ON). Er en gate kill-switchet fra, degraderer den til
observe-only — den ville-have-blokerede handling registreres som central-observabilitet, men
værktøjet kører. Sikkerheds-invariant er irrelevant her: begge commit-gates er COGNITIVE.

Self-safe/fail-open: enhver gate-/central-fejl → allow (paritet med det gamle inline-except).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CommitGateOutcome:
    """Udfald af commit-gate-arbitrage. ``blocked`` → værktøjet må ikke køre; ``soft_warn`` →
    værktøjet kører men en advarsel prependes til resultatet (decision_gate YELLOW)."""
    blocked: bool = False
    reason: str | None = None
    gate_type: str | None = None          # "veto_gate" | "decision_gate"
    soft_warn: str | None = None


def evaluate_commit_gates(*, name: str, arguments: dict[str, Any], user_message: str,
                          session_id: str, run_id: str) -> CommitGateOutcome:
    """Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér
    et governed block-udfald. Kaster aldrig (self-safe)."""
    from core.services.gate_kernel import Decision, GateClass
    from core.services import gate_enforcement

    _veto_blocked = False
    _veto_reason: str | None = None
    _vv = None  # §11 Trin 1: bær verdiktet ud til arbitrage-shadow

    # 1. Veto gate: affektiv pushback med evidens blokerer eksekvering (commit-cluster,
    #    COGNITIVE fail-open). RED håndhæves kun hvis veto er enforce-enabled (governed).
    try:
        from core.services.central_core import central as _central_veto
        from core.services.gate_commit import veto_gate as _veto_gate_fn
        _vv = _central_veto().decide(
            "veto",
            {"tool_name": name, "user_message": user_message,
             "session_id": session_id, "run_id": run_id},
            _veto_gate_fn, cluster="commit", klass=GateClass.COGNITIVE,
        )
        if _vv.decision is Decision.RED:
            _reason = (_vv.evidence or {}).get("reason") or _vv.reason
            if gate_enforcement.is_enforced("veto", GateClass.COGNITIVE):
                _veto_blocked = True
                _veto_reason = _reason
            else:
                gate_enforcement.note_suppressed_block("veto", "commit", _reason)
    except Exception:
        pass  # central self-safe; gate-fejl → allow (fail-open)

    # 2. Decision gate: aktive beslutnings-konflikter blokerer eksekvering (RED) eller
    #    surfaces som blød advarsel (YELLOW). RED håndhæves kun hvis enforce-enabled.
    _decision_blocked = False
    _decision_reason: str | None = None
    _decision_soft_warn: str | None = None
    _cv = None
    try:
        from core.services.central_core import central as _central_commit
        from core.services.gate_commit import commit_gate as _commit_gate_fn
        _cv = _central_commit().decide(
            "decision_gate",
            {"tool_name": name, "tool_args": arguments,
             "user_message": user_message, "run_id": run_id,
             "session_id": session_id or ""},
            _commit_gate_fn, cluster="commit", klass=GateClass.COGNITIVE,
        )
        if _cv.decision is Decision.RED:
            if gate_enforcement.is_enforced("decision_gate", GateClass.COGNITIVE):
                _decision_blocked = True          # hård grad → blokér (tool kører ikke)
                _decision_reason = _cv.reason
            else:
                gate_enforcement.note_suppressed_block("decision_gate", "commit", _cv.reason)
        elif _cv.decision is Decision.YELLOW:
            _decision_soft_warn = _cv.reason      # blød grad → kør, men surfacer advarsel
    except Exception:
        pass  # central self-safe; gate-fejl → allow (fail-open)

    # §11 Trin 1 (SHADOW, 0-risiko): observér den DEKLAREREDE arbitrage af de to commit-verdicts
    # vs. det faktisk håndhævede udfald (efter governed kill-switch). Ændrer INTET.
    try:
        from core.services.central_arbitration import observe_shadow as _arb_shadow
        _arb_shadow([_vv, _cv], enforced_blocked=bool(_veto_blocked or _decision_blocked),
                    run_id=run_id, where="pre_exec")
    except Exception:
        pass

    if _veto_blocked or _decision_blocked:
        return CommitGateOutcome(
            blocked=True,
            reason=_veto_reason or _decision_reason or "Ukendt gate-blokering",
            gate_type="veto_gate" if _veto_blocked else "decision_gate",
            soft_warn=None,
        )
    return CommitGateOutcome(blocked=False, soft_warn=_decision_soft_warn)
