"""core/services/central_notation.py

Model-frit bevis (Intelligent Central-spec §5, Fase 0 nordstjerne-milepæl): Centralen REGNER på sine
egne tanker uden modellen.

Når hypoteser bærer interlanguage-notation (`central_lexicon.render_relation`), kan Centralen udføre
ægte operationer på dem med REN symbol-manipulation — ingen model-token: (1) dedup af identiske
formodninger; (2) venstre-leds-korrelation (hypoteser med samme ANTECEDENT handler om samme årsag →
kan grupperes/sammenlignes). Det er forskellen på at LÆSE en tanke (fritekst, kræver model) og at
REGNE på den (notation, model-fri). Det er første konkrete skridt mod Lag 5 model-uafhængighed.

Alt read-only, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any


def normalize(notation: str) -> str:
    """Kanonisk form: trim + kollaps whitespace. Deterministisk, model-fri."""
    return " ".join(str(notation or "").split())


def parse(notation: str) -> dict[str, str] | None:
    """Split 'term OP term' → {antecedent, operator, consequent}. '!term' → saliens-form.
    Returnerer None hvis ikke velformet. Ren string-operation, ingen model."""
    n = normalize(notation)
    if not n:
        return None
    if n.startswith("!"):
        return {"antecedent": "", "operator": "!", "consequent": n[1:].strip()}
    for op in ("→", "↔", "⊂", "≈"):
        if f" {op} " in n:
            left, _, right = n.partition(f" {op} ")
            return {"antecedent": left.strip(), "operator": op, "consequent": right.strip()}
    return None


def dedup(notations: list[str]) -> list[str]:
    """Unikke normaliserede notationer (identiske formodninger kollapses). Model-fri."""
    seen: dict[str, None] = {}
    for x in (notations or []):
        k = normalize(x)
        if k and k not in seen:
            seen[k] = None
    return list(seen.keys())


def correlate_by_antecedent(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Gruppér hypoteser efter ANTECEDENT (venstre led). Hypoteser med samme antecedent handler om
    SAMME årsag → model-frit korrelerbare. items: [{notation_il, hyp_id?, ...}]. Self-safe."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for it in (items or []):
        p = parse(str(it.get("notation_il") or ""))
        if not p or not p["antecedent"]:
            continue
        groups.setdefault(p["antecedent"], []).append(it)
    return groups


def model_free_analysis(*, only_correlated: bool = False) -> dict[str, Any]:
    """NORDSTJERNE-BEVIS: læs aktive hypotesers notation_il og udfør dedup + antecedent-korrelation
    UDEN model. Returnerer et resultat der er 100% symbol-afledt. Self-safe."""
    out: dict[str, Any] = {"total_with_notation": 0, "unique": 0, "correlations": {}, "model_used": False}
    try:
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, notation_il FROM central_hypotheses "
                "WHERE status='active' AND notation_il IS NOT NULL AND notation_il != ''").fetchall()
        items = [{"hyp_id": str(r["hyp_id"]), "notation_il": str(r["notation_il"])} for r in rows]
    except Exception:
        items = []
    out["total_with_notation"] = len(items)
    out["unique"] = len(dedup([it["notation_il"] for it in items]))
    groups = correlate_by_antecedent(items)
    # Korrelationer = antecedenter delt af ≥2 hypoteser (samme årsag, flere konsekvenser).
    corr = {ant: [it["hyp_id"] for it in g] for ant, g in groups.items()
            if (len(g) >= 2 or not only_correlated)}
    out["correlations"] = {ant: ids for ant, ids in corr.items() if len(ids) >= 2}
    return out


def build_central_notation_surface() -> dict[str, object]:
    """Mission Control surface — read-only model-fri notations-analyse."""
    return {"active": True, **model_free_analysis()}
