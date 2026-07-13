"""Unified TruthGate (cluster B). Smelter Truth-klyngens tre homogene Verdict-gates
(claim_scanner, fact_gate, diagnosis) til ÉT kombineret Verdict via worst-decision.

Fase 1 (denne fil) er rent additivt: ingen ændring i visible_runs. Den live-effekt
(strip/block) ligger stadig på de gamle inline-kald indtil flippet (Fase 2)."""
from __future__ import annotations

from typing import Any

from core.services.gate_adapters import (claim_scanner_adapter, diagnosis_adapter,
                                         fact_gate_adapter)
from core.services.gate_kernel import Decision, GateClass, Verdict, worst

_PRECEDENCE = {Decision.RED: 3, Decision.YELLOW: 2, Decision.GREEN: 1, Decision.SKIP: 0}


def truth_gate(ctx: dict[str, Any]) -> Verdict:
    """Kør de tre Truth-checks på samme ctx og kombinér til ét Verdict.
    Beslutning = worst (RED>YELLOW>GREEN>SKIP); reason/action arves fra den mest
    alvorlige delgate, så strip/block-signalet bevares uændret."""
    verdicts = [claim_scanner_adapter(ctx), fact_gate_adapter(ctx), diagnosis_adapter(ctx)]
    decision = worst(verdicts)
    lead = max(verdicts, key=lambda v: _PRECEDENCE[v.decision])
    # Rig attribuering: bær lead-delgatens detected_text/trigger_pattern videre på det
    # kombinerede Verdict, så en fact_gate-fyring er præcist attribuerbar på truth-niveau.
    return Verdict("truth", decision, lead.reason, action=lead.action,
                   klass=GateClass.COGNITIVE,
                   detected_text=getattr(lead, "detected_text", "") or "",
                   trigger_pattern=getattr(lead, "trigger_pattern", "") or "",
                   evidence={v.gate: v.decision.value for v in verdicts})


def register_truth_nerve(central) -> None:
    """Registrér den unified TruthGate som post_output-nerve i Centralen."""
    central.register("truth", "post_output", truth_gate,
                     klass=GateClass.COGNITIVE, flag_key="gate.truth")
