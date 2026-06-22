"""Memory-cluster gate — promotion til identitets-filer, GRADERET.

Konsoliderer de to tidligere separate auto-apply-eligibility-gates (USER.md via
_candidate_eligible_for_auto_apply + MEMORY.md via _memory_candidate_eligible_for_auto_apply)
til ÉN graderet gate routet gennem Den Intelligente Central. Gaten bestemmer hvad der er
sikkert at auto-SKRIVE til Jarvis' identitets-filer (MEMORY.md/USER.md).

Grader af blok (som TruthGate):
  RED    = injection-/poisoning-mønstre i kandidat-indholdet → AFVIS (skriv aldrig til
           identitets-fil). Ny sikkerheds-grad: forhindrer at prompt-injection forgifter
           identiteten via memory-promotion.
  YELLOW = legitim kandidat men IKKE auto-sikker (ikke whitelisted) → kø til menneske-review.
  GREEN  = sikker (whitelisted/eligible) → auto-apply.

Cognitiv → fail-open: gate-fejl → YELLOW (kø, IKKE auto-apply) — det sikre default for
en skrive-gate er at IKKE skrive ved tvivl.
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def _candidate_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(k) or "")
        for k in ("summary", "content_line", "value", "directive", "detail")
    ).strip()


def memory_promotion_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {candidate, kind: 'user_md'|'memory_md'}. Returnér ét GRADERET Verdict."""
    candidate = ctx.get("candidate") or {}
    kind = str(ctx.get("kind") or "")

    # RED — injection/poisoning-beskyttelse af identitets-filen.
    try:
        from core.services.abuse_monitor import scan_for_injection
        hits = scan_for_injection(_candidate_text(candidate)) or []
    except Exception:
        hits = []
    if hits:
        return Verdict("memory_promotion", Decision.RED,
                       f"injection-mønstre i memory-kandidat — afvist: {hits[:3]}",
                       action="block", klass=GateClass.COGNITIVE, evidence={"hits": hits})

    # GREEN — eligible (whitelisted/sikker → auto-apply). Eligibility-funktionerne er
    # detektorerne (lever videre, som Truths detektorer).
    try:
        from core.identity.candidate_workflow import (
            _candidate_eligible_for_auto_apply,
            _memory_candidate_eligible_for_auto_apply,
        )
        eligible = (
            _memory_candidate_eligible_for_auto_apply(candidate) if kind == "memory_md"
            else _candidate_eligible_for_auto_apply(candidate)
        )
    except Exception:
        eligible = False
    if eligible:
        return Verdict("memory_promotion", Decision.GREEN, "sikker — auto-apply",
                       action="none", klass=GateClass.COGNITIVE)

    # YELLOW — legitim men ikke auto-sikker → kø til review (skriv ikke automatisk).
    return Verdict("memory_promotion", Decision.YELLOW, "ikke auto-safe — kø til review",
                   action="warn", klass=GateClass.COGNITIVE)
