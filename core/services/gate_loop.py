"""Loop-cluster gate — agentisk loop-kontrol, GRADERET.

Konsoliderer de spredte stop-betingelser for Jarvis' agentiske tool-løkke (max runder,
max tomme-tekst-runder, max tool-only-runder, synthese-pause) til ÉN graderet gate routet
gennem Den Intelligente Central.

Grader (som TruthGate):
  RED    = HÅRD STOP — loop-budget opbrugt (sidste runde): tving et afsluttende svar,
           ingen flere tools denne tur.
  YELLOW = BLØD BREMS — synthese-pause: tools tilbageholdt denne runde, men runnet
           fortsætter (Jarvis skal opsummere, ikke afslutte).
  GREEN  = FORTSÆT — tools tilladt.

KRITISK fail-retning: dette er en LOOP-gate. Ved tvivl skal vi STOPPE (ikke loope i det
uendelige). Kald-stedet behandler derfor SKIP (cognitiv gate-fejl) som hård stop, og har
en lokal backstop-beregning hvis hele central-stien fejler.
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def loop_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {round, max_rounds, consecutive_empty, max_empty, consecutive_tool_only,
    max_tool_only, tool_pause}. Returnér ét GRADERET loop-kontrol-Verdict."""
    rnd = int(ctx.get("round") or 0)
    mx = int(ctx.get("max_rounds") or 100)
    ce = int(ctx.get("consecutive_empty") or 0)
    me = int(ctx.get("max_empty") or 3)
    ct = int(ctx.get("consecutive_tool_only") or 0)
    mt = int(ctx.get("max_tool_only") or 4)
    tool_pause = bool(ctx.get("tool_pause"))

    # RED — hård stop: budget/runder opbrugt (sidste runde).
    if rnd >= mx - 1 or ce >= me - 1 or ct >= mt - 1:
        return Verdict("loop_control", Decision.RED, "hård stop — loop-budget opbrugt",
                       action="block", klass=GateClass.COGNITIVE)
    # YELLOW — blød synthese-brems: tools tilbageholdt, men fortsæt.
    if tool_pause:
        return Verdict("loop_control", Decision.YELLOW, "blød brems — synthese-pause",
                       action="warn", klass=GateClass.COGNITIVE)
    return Verdict("loop_control", Decision.GREEN, "fortsæt", action="none",
                   klass=GateClass.COGNITIVE)
