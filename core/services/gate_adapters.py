"""Gate-adaptere (unified-gate A.5) — wrapper EKSISTERENDE gates som Verdict-returnerende.

Fase A ændrer INGEN gate-logik. En adapter kalder den eksisterende gate og oversætter
dens resultat til en `Verdict`, så kernen kan køre den isoleret + emittere ét event.
Den faktiske EFFEKT (strip/blok) ligger stadig på de gamle kald-sites indtil A.6
router gennem kernen og B-H konsoliderer.

Disse tre hører til TruthGate-clusteret (post_output, kognitiv → fail-OPEN).
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def claim_scanner_adapter(ctx: dict[str, Any]) -> Verdict:
    """claim_scanner.scan_response: repareret tekst ≠ input → claims fanget (YELLOW)."""
    text = str(ctx.get("text") or "")
    if not text.strip():
        return Verdict("claim_scanner", Decision.GREEN, "empty")
    from core.services.claim_scanner import scan_response
    repaired = scan_response(text)
    if repaired != text:
        return Verdict("claim_scanner", Decision.YELLOW, "uverificerede claims repareret",
                       action="strip", evidence={"repaired": True})
    return Verdict("claim_scanner", Decision.GREEN, "ren")


def fact_gate_adapter(ctx: dict[str, Any]) -> Verdict:
    """fact_gate_enforce: blocked=True → RED (strip)."""
    text = str(ctx.get("text") or "")
    tools = ctx.get("tool_names") or ctx.get("tools_used") or []
    from core.services.fact_gate import fact_gate_enforce
    res = fact_gate_enforce(text, list(tools)) or {}
    if res.get("blocked"):
        # block_reasons er en liste af DICTS ({pattern, matched, description, …}) — IKKE
        # strings. Et rå "; ".join(...) kastede 'expected str instance, dict found' og væltede
        # HELE truth-decide (fail-incident). Udtræk en læsbar streng pr. reason i stedet.
        _reasons = res.get("block_reasons") or []
        reason = "; ".join(
            str(br.get("description") or br.get("pattern") or br) if isinstance(br, dict)
            else str(br)
            for br in _reasons
        )[:200] or "fact-gate blok"
        return Verdict("fact_gate", Decision.RED, reason, action="strip")
    return Verdict("fact_gate", Decision.GREEN, "ok")


def diagnosis_adapter(ctx: dict[str, Any]) -> Verdict:
    """analyze_completion_claim: blocked→RED, ikke-verificeret completion→YELLOW."""
    text = str(ctx.get("text") or "")
    tools = ctx.get("tools_used") or ctx.get("tool_names") or []
    from core.services.diagnosis_gate import analyze_completion_claim
    r = analyze_completion_claim(text, tools_used=list(tools))
    if getattr(r, "blocked", False):
        return Verdict("diagnosis", Decision.RED, getattr(r, "reason", "") or "diagnose-blok", action="block")
    # Kun YELLOW hvis der FAKTISK var et completion-claim der ikke kunne verificeres.
    if getattr(r, "is_claim", False) and not getattr(r, "verified", True):
        return Verdict("diagnosis", Decision.YELLOW, getattr(r, "reason", "") or "uverificeret completion")
    return Verdict("diagnosis", Decision.GREEN, "ok")


# Adaptere i TruthGate-clusteret: (name, fn).
_TRUTHGATE_ADAPTERS = [
    ("claim_scanner", claim_scanner_adapter),
    ("fact_gate", fact_gate_adapter),
    ("diagnosis", diagnosis_adapter),
]


def register_truthgate_adapters(k) -> None:
    """Registrér TruthGate-cluster-adapterne i kernen (post_output, kognitiv)."""
    for name, fn in _TRUTHGATE_ADAPTERS:
        k.register(name, "post_output", fn, klass=GateClass.COGNITIVE,
                   timeout_ms=1500, flag_key=f"gate.{name}")


def register_truthgate_adapters_once(k) -> None:
    """Idempotent — registrér KUN hvis ikke allerede registreret (kaldes pr. run i
    visible_runs A.6; må aldrig duplikere gates)."""
    have = {g.name for g in k.gates_for("post_output")}
    if {n for n, _ in _TRUTHGATE_ADAPTERS} <= have:
        return
    register_truthgate_adapters(k)
