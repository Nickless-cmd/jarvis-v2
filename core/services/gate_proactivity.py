"""Proactivity-cluster gate — verifikations-disciplin, GRADERET (R2 blød / R2.5 hård).

Konsoliderer de to tidligere SEPARATE prompt-injektioner til ÉN graderet gate routet
gennem Den Intelligente Central:
  - R2  (verification_gate_section, awareness-slot 23): blød surface — "du har
    uverificerede mutationer, overvej at verificere". Jarvis kunne ignorere den.
  - R2.5 (r2_5_block_section, awareness-slot 95): hård blok — "STOP og verificér"
    når 24t heed_rate er lav + tærskel krydset.

R2 og R2.5 var to GRADER af samme koncept (verifikations-nag). Som TruthGate: ÉN gate,
flere grader af blok:
  RED    = R2.5 hård blok (heed_rate lav + tærskel krydset)
  YELLOW = R2 blød surface (uverificerede mutationer findes)
  GREEN  = ingen verifikations-bekymring

evidence["text"] bærer den færdige awareness-tekst så kald-stedet kan injicere den
rigtige grad på den rigtige prioritet. Cognitiv → fail-open (gate-fejl → GREEN).
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def proactivity_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {reasoning_tier}. Returnér ét GRADERET Verdict for verifikations-disciplin."""
    tier = str(ctx.get("reasoning_tier") or "fast")

    # RED — R2.5 hård blok (r2_5_block_section returnerer formateret tekst eller None;
    # den kalder should_block_for_verification internt, så cooldown/telemetri bevares).
    try:
        from core.services.r2_5_blocking_gate import r2_5_block_section
        block_text = r2_5_block_section(tier)
    except Exception:
        block_text = None
    if block_text:
        return Verdict("verification", Decision.RED, "R2.5 hård blok — verifikation påkrævet",
                       action="block", klass=GateClass.COGNITIVE,
                       evidence={"text": block_text, "priority": 95})

    # YELLOW — R2 blød surface.
    try:
        from core.services.verification_gate import verification_gate_section
        surface = verification_gate_section()
    except Exception:
        surface = None
    if surface:
        return Verdict("verification", Decision.YELLOW, "R2 blød surface — uverificerede mutationer",
                       action="warn", klass=GateClass.COGNITIVE,
                       evidence={"text": surface, "priority": 23})

    return Verdict("verification", Decision.GREEN, "ok", klass=GateClass.COGNITIVE)
