"""core/services/central_proposal.py

Spec B / Fase B4: NotationProposal-KONTRAKTEN — broen til den modige del (Fase 3-4).

En foreslået mutation (routing-skift, prompt-relevans-vægt, adaptation) udtrykkes som en NOTATION-
SÆTNING og SKAL passere en model-fri audit FØR den nogensinde kunne anvendes:
  1. Parsebar (en gyldig relation i sproget)?
  2. Sigelig (begge led bundne — ikke rå navne Centralen ikke har ord for)?
  3. Konsistent (introducerer den IKKE en modsigelse mod hvad Centralen allerede tror)?

Dette modul DØMMER kun — det ANVENDER intet (der er ingen apply-sti her; den bygger den modige del
ovenpå, bag Bjørns per-tråd-flags). At beslutte i notation gør mutationen læsbar og model-frit
auditerbar før den rører virkeligheden. Kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any


def audit_proposal(notation: str, *, existing: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Auditér en foreslået mutation (som notation-sætning) model-frit. Returnerer
    {ok, reasons, notation, parsed, new_contradictions}. INGEN mutation. Self-safe."""
    from core.services.central_notation import parse, detect_notation_contradictions
    from core.services.central_lexicon import _ACTIVE_TERMS

    reasons: list[str] = []
    p = parse(str(notation or ""))
    if not p:
        return {"ok": False, "reasons": ["uparsebar notation"], "notation": notation,
                "parsed": None, "new_contradictions": []}

    # (2) sigelig: begge ikke-tomme led skal være KENDTE termer (ikke rå navne / ubundne begreber)
    consequent = p["consequent"].lstrip("!").strip()
    for role, term in (("antecedent", p["antecedent"]), ("consequent", consequent)):
        if term and term not in _ACTIVE_TERMS:
            reasons.append(f"{role} '{term}' er ikke et kendt ord (uslegeligt → ceremoni først)")

    # (3) konsistent: forslaget må ikke INTRODUCERE en ny modsigelse mod eksisterende notation
    try:
        if existing is None:
            from core.services.central_notation import gather_all_notations
            existing = gather_all_notations()
    except Exception:
        existing = []
    base = detect_notation_contradictions(existing or [])
    with_prop = detect_notation_contradictions(
        list(existing or []) + [{"id": "proposal", "notation_il": str(notation)}])
    new_contra = [c for c in with_prop if c not in base]
    if new_contra:
        reasons.append(f"introducerer modsigelse: {new_contra[0]['contradiction']}")

    return {"ok": not reasons, "reasons": reasons, "notation": str(notation),
            "parsed": p, "new_contradictions": new_contra}


def make_proposal(*, domain: str, notation: str, rationale: str = "",
                  existing: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Pak en mutation-forslag ind SOM en auditeret NotationProposal. `admissible=True` betyder KUN
    at den bestod den model-frie audit — IKKE at den anvendes (den modige del + Bjørns flag afgør
    anvendelse). §8-domænet bæres med så en fremtidig gate_self_mutation kan namespaces korrekt. Self-safe."""
    audit = audit_proposal(notation, existing=existing)
    return {"domain": str(domain or ""), "notation": str(notation), "rationale": str(rationale)[:280],
            "admissible": bool(audit["ok"]), "audit": audit, "applied": False}
