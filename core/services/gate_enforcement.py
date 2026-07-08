"""Governed per-gate enforce-kill-switch for PRE-eksekverings-gates.

De fire pre-exec gates HÅNDHÆVER allerede inline i hot-pathen — deres RED-verdict blokerer
værktøjs-kaldet / hard-stopper det agentiske loop:

  * ``veto``                  visible_runs pre-tool-exec → RED = tool blokeres
  * ``decision_gate``         visible_runs pre-tool-exec → RED = tool blokeres
  * ``loop_control``          visible_runs loop-runde    → RED = tving sidste runde (hard-stop)
  * ``exec_workspace_trust``  simple_tools pre-tool      → untrusted = tool blokeres (SECURITY)

Men de håndhævede UBETINGET — der var ingen governed off-switch. Hvis en gate begynder at
false-positive-blokere Jarvis, var eneste udvej et deploy. Denne modul giver dem samme mønster
som post-output-gates (jf. ``gate_shadow._is_enforced``): en per-gate flag
``central.switch.gate_enforce.<nerve>`` (default ON = ingen adfærdsændring). Slås den fra,
degraderer gaten til OBSERVE-ONLY — den ville-have-blokerede handling registreres som
central-observabilitet (så en undertrykt blokering er SYNLIG, ikke tavs) men blokerer ikke.

SIKKERHEDS-INVARIANT (§11.3): en SECURITY-gate (``exec_workspace_trust``) kan ALDRIG slås fra.
``is_enforced`` returnerer altid True for SECURITY-klassen — samme invariant som
``central_switches.set_enabled`` håndhæver ved at afvise enabled=False for sikkerheds-nerver.
"""
from __future__ import annotations

from core.services.gate_kernel import GateClass

# Fælles flag-scope med post-output-gates (gate_shadow bruger samme "gate_enforce"-navnerum).
# Ingen kollision: nerve-navnene er disjunkte (post-output: self_review/fact_gate/... ;
# pre-exec: veto/decision_gate/loop_control/exec_workspace_trust).
_ENFORCE_SCOPE = "gate_enforce"


def is_enforced(nerve: str, klass: GateClass) -> bool:
    """True hvis gatens håndhævelse er aktiv.

    SECURITY-gates kan ALDRIG disables (§11.3) → altid True. COGNITIVE-gates styres af
    ``central.switch.gate_enforce.<nerve>`` (default ON). Fail-SAFE: en flag-/cache-fejl →
    True (håndhæv), så en cache-katastrofe ikke tavst åbner en gate."""
    if klass is GateClass.SECURITY:
        return True
    try:
        from core.services import central_switches
        return bool(central_switches.is_enabled(_ENFORCE_SCOPE, nerve))
    except Exception:
        return True


def note_suppressed_block(nerve: str, cluster: str, reason: str) -> None:
    """En gate ville have blokeret, men håndhævelsen er governed-OFF → registrér det som
    central-observabilitet, så en undertrykt blokering er SYNLIG i stedet for tavs. Self-safe
    (må aldrig kaste i hot-pathen)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": cluster,
            "nerve": nerve,
            "kind": "enforce_suppressed",
            "reason": str(reason or "")[:200],
        })
    except Exception:
        pass
