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


# ── Model-fri INFERENS (Tråd 3-udvidelse): Centralen UDLEDER nye relationer uden modellen ──
def _causal_edges(items: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Byg antecedent→konsekvens-graf fra '→'-notationer (kun kausale led)."""
    edges: dict[str, set[str]] = {}
    for it in (items or []):
        p = parse(str(it.get("notation_il") or ""))
        if p and p["operator"] == "→" and p["antecedent"] and p["consequent"]:
            edges.setdefault(p["antecedent"], set()).add(p["consequent"])
    return edges


def infer_transitive(items: list[dict[str, Any]], *, max_derived: int = 50) -> list[dict[str, Any]]:
    """TRANSITIV INFERENS (model-fri): fra A → B og B → C udled A → C. En NY tanke ingen enkelt
    hypotese udtrykte, afledt af ren symbol-manipulation — Centralen der TÆNKER i sit eget sprog.
    Returnerer kun ægte NYE relationer (ikke allerede kendte, ikke selv-løkker). Self-safe."""
    edges = _causal_edges(items)
    derived = []
    for a, bs in edges.items():
        for b in bs:
            for c in edges.get(b, ()):
                if c != a and c not in edges.get(a, set()):
                    derived.append({"notation": f"{a} → {c}", "via": b,
                                    "chain": f"{a} → {b} → {c}"})
    # dedup afledte
    seen: set[str] = set()
    uniq = [d for d in derived if not (d["notation"] in seen or seen.add(d["notation"]))]
    return uniq[:max_derived]


def detect_notation_contradictions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Model-fri MODSIGELSES-detektion: samme antecedent → BÅDE X og !X (Centralen opdager at den
    tror to uforenelige ting). Ren symbol-operation. Self-safe."""
    pos: dict[str, set[str]] = {}
    neg: dict[str, set[str]] = {}
    for it in (items or []):
        p = parse(str(it.get("notation_il") or ""))
        if not p or p["operator"] != "→" or not p["antecedent"]:
            continue
        cons = p["consequent"]
        (neg if cons.startswith("!") else pos).setdefault(
            p["antecedent"], set()).add(cons[1:].strip() if cons.startswith("!") else cons)
    out = []
    for a in pos:
        for x in pos[a] & neg.get(a, set()):
            out.append({"antecedent": a, "term": x, "contradiction": f"{a} → {x}  ×  {a} → !{x}"})
    return out


def model_free_reasoning() -> dict[str, Any]:
    """NORDSTJERNE (dybere): læs aktive hypotesers notation og UDLED + find modsigelser — alt uden
    model-token. Beviser Centralen kan REGNE på sine tanker, ikke bare læse dem. Self-safe."""
    try:
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, notation_il FROM central_hypotheses "
                "WHERE status IN ('active','resolved') AND notation_il IS NOT NULL "
                "AND notation_il != ''").fetchall()
        items = [{"hyp_id": str(r["hyp_id"]), "notation_il": str(r["notation_il"])} for r in rows]
    except Exception:
        items = []
    derived = infer_transitive(items)
    contradictions = detect_notation_contradictions(items)
    return {"model_used": False, "notations": len(items),
            "derived_inferences": derived, "contradictions": contradictions}


def run_notation_reasoning_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: udfør model-fri ræsonnement + registrér tællere egress-frit. Self-safe."""
    r = model_free_reasoning()
    # Spec B / Fase B0: mål taksonomi-dækning (S1) — hvor stor en del af Centralens vokabular er sigeligt.
    try:
        from core.services import central_lexicon
        tax = central_lexicon.taxonomy_coverage()
    except Exception:
        tax = {}
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "notation_reasoning",
                       value=float(len(r["derived_inferences"])),
                       meta={"notations": r["notations"], "derived": len(r["derived_inferences"]),
                             "contradictions": len(r["contradictions"]),
                             "taxonomy_ratio": tax.get("ratio"), "taxonomy_unbound": tax.get("unbound")})
    except Exception:
        pass
    return {"status": "ok", "derived": len(r["derived_inferences"]),
            "contradictions": len(r["contradictions"]), "notations": r["notations"],
            "taxonomy_ratio": tax.get("ratio"), "taxonomy_unbound": tax.get("unbound")}


def register_notation_reasoning_producer() -> None:
    """Registrér model-fri ræsonnement som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_notation_reasoning",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_notation_reasoning_tick,
        priority=7,
    ))


def build_central_notation_surface() -> dict[str, object]:
    """Mission Control surface — read-only model-fri notations-analyse + ræsonnement."""
    return {"active": True, **model_free_analysis(), **model_free_reasoning()}
