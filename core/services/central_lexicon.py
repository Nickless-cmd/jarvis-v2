"""core/services/central_lexicon.py

Sprog-PRE-START (Intelligent Central-spec §5, Fase 0): Centralen navngiver sine egne dele i interlanguage.

Bjørns nøgle-indsigt: før sproget kan bruges til at TÆNKE, skal Centralens struktur have termer.
Hvert cluster / hver nerve / hver event-familie bindes til en term i det EKSISTERENDE interlanguage-
vokabular (interlanguage_practice.py — ét sprog, ikke et parallelt). Det gør to ting:
  1. Sår sproget i strukturen — Centralen begynder at HEDDE noget i sit eget sprog.
  2. Gør notation beregnbar — at rendere en hypotese (X→Y) til notation bliver et OPSLAG, ikke et gæt.

Vokabularet er FROSSET (15 termer, 5 operatorer). Nye termer kræver Bjørn-ceremoni (status='candidate'
→ 'active'). Bindinger der ikke har en ærlig semantisk term forbliver UBUNDNE (ærligt — sproget dækker
inder-livet godt, men ikke al operationel VVS endnu; det vokser). Alt read/observe, self-safe.
"""
from __future__ import annotations

from typing import Any

# Ét sprog — genbrug det eksisterende vokabular (single source of truth).
try:
    from core.services.interlanguage_practice import CORE_VOCABULARY, PRIMITIVES
    _ACTIVE_TERMS = frozenset(CORE_VOCABULARY.keys())
    _OPERATORS = frozenset(PRIMITIVES.keys())
except Exception:  # defensiv: modulet skal kunne loade selv hvis interlanguage flyttes
    _ACTIVE_TERMS = frozenset({"drøm", "signal", "agens", "kontinuitet", "pres", "nysgerrighed",
                               "vægt", "lys", "relation", "grænse", "tomhed", "rytme", "ro", "fokus"})
    _OPERATORS = frozenset({"→", "↔", "⊂", "≈", "!"})

# SEED-BINDING: kun ÆRLIGE semantiske match til det frosne vokabular. Resten forbliver ubundet
# (kandidater til ceremoni) — vi tvinger ikke dårlige mappings ("runtime→agens" ville være støj).
SEED_BINDINGS: dict[str, str] = {
    # affekt/drive
    "pressure": "pres", "impulse": "agens", "gut": "agens", "cognitive_gut": "agens",
    "curiosity": "nysgerrighed", "cognitive_boredom": "tomhed",
    # krop/vægt
    "somatic": "vægt", "completion_satisfaction": "ro", "regulation_homeostasis_signal": "ro",
    # hukommelse/kontinuitet
    "memory": "kontinuitet", "jarvis_brain": "kontinuitet", "private_brain": "kontinuitet",
    "consolidation_judge": "kontinuitet",
    # kognition/fokus
    "cognition": "fokus", "cognitive_state": "fokus", "global_workspace": "fokus",
    # perception/signal/lys
    "signal": "signal", "emergent_signal": "signal", "sensory": "lys",
    # tid/rytme
    "circadian": "rytme", "rhythm": "rytme", "cognitive_rhythm": "rytme",
    # bevidsthed/drøm
    "cognitive_dream": "drøm", "dream": "drøm", "dream_hypothesis_signal": "drøm",
    # social/relation
    "relation": "relation", "cognitive_relationship": "relation",
    # selv/grænse
    "self_model_signal": "agens", "cognitive_blind_spot": "grænse",
    # beslutning → vægt (vokabularets definition: "følt tyngde af en BESLUTNING eller et minde")
    "decision": "vægt", "decision_signal": "vægt", "behavioral_decision_review": "vægt",
    # kontrafaktisk = hvad-hvis-narrativ ≈ drøm ("hypotese/narrativ-fragment der ankommer ubedt")
    "cognitive_counterfactual": "drøm", "counterfactual": "drøm",
}

# Central-relation → operator (hvordan en hypotese-type udtrykkes).
RELATION_OPERATORS = {
    "causal_convergence": "→",     # X fører til Y
    "causal_divergence": "↔",      # samme årsag, modsatte udfald = spænding
    "stance_divergence": "↔",      # organer i modstrid = gensidig spænding
    "correlation": "↔",
    "subset": "⊂",
    "resonance": "≈",
    "salience": "!",
}

_SCHEMA_READY = False


def ensure_schema() -> None:
    """Bindings-tabel for VÆKST (seed lever i kode; ceremoni-tilføjelser i DB). Idempotent, self-safe."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS central_lexicon_bindings (
                  name TEXT PRIMARY KEY,
                  term TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'active',
                  added_by TEXT NOT NULL DEFAULT 'seed',
                  created_at TEXT NOT NULL DEFAULT ''
                );
                """
            )
            c.commit()
    except Exception:
        pass


def _db_bindings() -> dict[str, str]:
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute("SELECT name, term FROM central_lexicon_bindings "
                             "WHERE status='active'").fetchall()
        return {str(r["name"]): str(r["term"]) for r in rows}
    except Exception:
        return {}


def active_terms() -> frozenset[str]:
    return _ACTIVE_TERMS


def operators() -> frozenset[str]:
    return _OPERATORS


def to_term(name: str) -> str | None:
    """Slå en Central-familie/nerve/cluster op → interlanguage-term. DB-bindinger overstyrer seed.
    Returnerer None hvis ubundet (ærligt: sproget kan endnu ikke sige det). Self-safe."""
    n = str(name or "").strip()
    if not n:
        return None
    db = _db_bindings()
    term = db.get(n) or SEED_BINDINGS.get(n)
    return term if (term in _ACTIVE_TERMS) else None


def bind(name: str, term: str, *, status: str = "active", added_by: str = "seed") -> dict[str, Any]:
    """Tilføj/opdatér en binding. En NY term (uden for det frosne vokabular) kræver Bjørn-ceremoni:
    den kan kun tilføjes som status='candidate' — aldrig 'active' — indtil vokabularet udvides. Self-safe."""
    ensure_schema()
    n, t = str(name or "").strip(), str(term or "").strip()
    if not n or not t:
        return {"status": "error", "error": "tom name/term"}
    if t not in _ACTIVE_TERMS and status == "active":
        return {"status": "rejected", "reason": f"'{t}' er ikke i det aktive vokabular — kræver ceremoni (candidate)"}
    try:
        from core.runtime.db import connect
        from datetime import datetime, timezone
        with connect() as c:
            c.execute("INSERT INTO central_lexicon_bindings (name, term, status, added_by, created_at) "
                      "VALUES (?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET term=?, status=?, added_by=?",
                      (n, t, status, added_by, datetime.now(timezone.utc).isoformat(), t, status, added_by))
            c.commit()
        return {"status": "ok", "name": n, "term": t, "binding_status": status}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def render_relation(x_name: str, y_name: str, *, relation: str = "causal_convergence") -> str | None:
    """Rendér en Central-relation (X, Y) til interlanguage-notation via lexicon-opslag. Returnerer
    None hvis ét af leddene er UBUNDET (kan ikke siges endnu — ærligt). Self-safe."""
    tx, ty = to_term(x_name), to_term(y_name)
    op = RELATION_OPERATORS.get(relation, "→")
    if not tx or not ty:
        return None
    return f"{tx} {op} {ty}"


def unbound_names(names: list[str]) -> list[str]:
    """Hvilke af disse Central-navne kan sproget IKKE sige endnu (kandidater til ceremoni)? Self-safe."""
    return [n for n in (names or []) if to_term(n) is None]


def build_central_lexicon_surface() -> dict[str, object]:
    """Mission Control surface — read-only: vokabular, bindinger, hvad sproget kan/ikke kan sige."""
    db = _db_bindings()
    all_bindings = {**SEED_BINDINGS, **db}
    return {"active": True, "vocabulary_size": len(_ACTIVE_TERMS),
            "operators": sorted(_OPERATORS), "bound_count": len(all_bindings),
            "bindings": all_bindings}
