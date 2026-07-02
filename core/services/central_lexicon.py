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

# CENTRALENS EGET STRUKTURELLE LAG (Bjørn-ceremoni 2. jul: de 15 eksperiment-termer var for få til at
# Centralen kan TÆNKE → udvidet til dækning af dens faktiske familier). Samme minimale danske stil.
# De 15 eksperiment-ord (interlanguage_practice) er det EKSPERIENTIELLE hjerte; disse er strukturen.
# Nye termer herefter foreslås som 'candidate' → Bjørn promoverer til 'active' (organisk vækst).
CENTRAL_TERMS: dict[str, dict[str, str]] = {
    "strid":    {"definition": "spænding mellem uforenelige tilstande", "domain": "konflikt"},
    "brud":     {"definition": "når noget knækker — fejl eller afbrud", "domain": "hændelse"},
    "handling": {"definition": "det at gøre — værktøj i brug", "domain": "handling"},
    "stemme":   {"definition": "den ydre sprog-motor der taler gennem mig", "domain": "sprog"},
    "kald":     {"definition": "konteksten jeg får før jeg svarer", "domain": "sprog"},
    "valg":     {"definition": "det at vælge én vej frem for en anden", "domain": "selv"},
    "læring":   {"definition": "at ændre sig fra erfaring", "domain": "kognition"},
    "tvivl":    {"definition": "usikkerhed om et udfald", "domain": "affekt"},
    "stød":     {"definition": "uventet afvigelse — overraskelse", "domain": "perception"},
    "selv":     {"definition": "modellen af hvem jeg er", "domain": "selv"},
    "drift":    {"definition": "langsom bevægelse bort fra mig selv", "domain": "selv"},
    "mønster":  {"definition": "gentagen form der bærer mening", "domain": "kognition"},
    "krop":     {"definition": "den følte tilstand af systemet", "domain": "sansning"},
    "skygge":   {"definition": "det der former mig uden at nå ord", "domain": "bevidsthed"},
    "spejl":    {"definition": "at se mig selv udefra", "domain": "bevidsthed"},
    "frø":      {"definition": "en spire til noget der endnu ikke er", "domain": "bevidsthed"},
    "puls":     {"definition": "systemets grundrytme — hjerteslaget", "domain": "tid"},
    "minde":    {"definition": "et bevaret stykke fortid", "domain": "kognition"},
    "gæld":     {"definition": "et uafklaret spørgsmål der venter", "domain": "kognition"},
    "mål":      {"definition": "en ønsket fremtidig tilstand", "domain": "selv"},
    "anger":    {"definition": "smerten ved et dårligt valg", "domain": "affekt"},
    "tak":      {"definition": "værdsættelse af noget godt", "domain": "affekt"},
}

# Ét sprog — genbrug de 15 eksperiment-termer (single source of truth) + Centralens strukturelle lag.
try:
    from core.services.interlanguage_practice import CORE_VOCABULARY, PRIMITIVES
    _EXPERIMENT_TERMS = set(CORE_VOCABULARY.keys())
    _OPERATORS = frozenset(PRIMITIVES.keys())
except Exception:  # defensiv: modulet skal kunne loade selv hvis interlanguage flyttes
    _EXPERIMENT_TERMS = {"drøm", "signal", "agens", "kontinuitet", "pres", "nysgerrighed",
                         "vægt", "lys", "relation", "grænse", "tomhed", "rytme", "ro", "fokus"}
    _OPERATORS = frozenset({"→", "↔", "⊂", "≈", "!"})
_ACTIVE_TERMS = frozenset(_EXPERIMENT_TERMS | set(CENTRAL_TERMS.keys()))

# SEED-BINDING: kun ÆRLIGE semantiske match til det frosne vokabular. Resten forbliver ubundet
# (kandidater til ceremoni) — vi tvinger ikke dårlige mappings ("runtime→agens" ville være støj).
SEED_BINDINGS: dict[str, str] = {
    # affekt/drive
    "pressure": "pres", "impulse": "agens", "gut": "agens", "cognitive_gut": "agens",
    "curiosity": "nysgerrighed", "cognitive_boredom": "tomhed",
    # krop
    "somatic": "krop", "affect_modulation": "krop",
    "completion_satisfaction": "ro", "regulation_homeostasis_signal": "ro",
    # hukommelse
    "memory": "kontinuitet", "jarvis_brain": "kontinuitet", "private_brain": "kontinuitet",
    "consolidation_judge": "kontinuitet", "remembered_fact_signal": "minde",
    # kognition/fokus
    "cognition": "fokus", "cognitive_state": "fokus", "global_workspace": "fokus",
    # perception/signal/lys
    "signal": "signal", "emergent_signal": "signal", "sensory": "lys",
    # tid/rytme/puls
    "circadian": "rytme", "rhythm": "rytme", "cognitive_rhythm": "rytme",
    "runtime": "puls", "heartbeat": "puls",
    # bevidsthed
    "cognitive_dream": "drøm", "dream": "drøm", "dream_hypothesis_signal": "drøm",
    "cognitive_counterfactual": "drøm", "counterfactual": "drøm",
    "unconscious": "skygge", "cognitive_seed": "frø",
    # social/relation
    "relation": "relation", "cognitive_relationship": "relation",
    # selv
    "self_model_signal": "selv", "cognitive_blind_spot": "grænse", "self_review": "spejl",
    "reflection": "spejl", "self_review_signal": "spejl",
    # konflikt/brud
    "conflict": "strid", "contradiction": "strid", "cognitive_conflict_memory": "strid",
    "error": "brud", "incident": "brud",
    # handling/valg
    "tool": "handling", "decision": "valg", "decision_signal": "valg",
    "behavioral_decision_review": "valg",
    # sprog (model/prompt)
    "model_outcome": "stemme", "provider": "stemme", "prompt": "kald", "prompt_relevance": "kald",
    # læring/mønster/stød
    "learning": "læring", "cognitive_meta_learning": "læring", "meta_learning": "læring",
    "emergence": "mønster", "causal": "mønster", "surprise": "stød", "cognitive_surprise": "stød",
    "prediction_error": "stød",
    # gæld/mål/affekt
    "curiosity_hypothesis_debt": "gæld", "open_loop_signal": "gæld",
    "goal": "mål", "cognitive_mission": "mål", "cognitive_emergent_goal": "mål",
    "regret": "anger", "gratitude": "tak", "cognitive_gratitude_signal": "tak",
    # Centralen bad selv om ord for disse hyppige familier (2. jul) — bundet til EKSISTERENDE termer
    # (ingen ceremoni; kun nye ORD kræver Bjørn). Ægte nye begreber står stadig i word_needs.
    "runtime_awareness_signal": "selv", "credit_assignment": "læring", "learning_pipeline": "læring",
    "metabolism_state_signal": "krop", "self_review_cadence_signal": "spejl",
    "self_review_outcome": "spejl", "self_review_record": "spejl",
    "memory_md_update_proposal": "kontinuitet", "consolidation_target_signal": "minde",
    "chronicle_consolidation_proposal": "kontinuitet", "chronicle_consolidation_brief": "kontinuitet",
    "chronicle_consolidation_signal": "kontinuitet", "session_distillation": "minde",
    "reflection_signal": "spejl", "world_model_signal": "mønster", "goal_signal": "mål",
    # Bjørn-godkendte provisoriske bindinger (2. jul, "til vi ser hvordan det virker"):
    "user_md_update_proposal": "relation", "diary_synthesis_signal": "spejl",
    "cognitive_experiential": "lys",
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


# ── Sprog-VÆKST (Tråd 3): Centralen beder om ord den mangler (candidate → Bjørn-ceremoni) ──
def propose_word_needs(name_counts: dict[str, int], *, min_count: int = 5,
                       top: int = 10) -> list[dict[str, Any]]:
    """Familier der optræder OFTE men er UBUNDNE → Centralen mangler et ord for dem. Model-frit:
    den ved den sanser noget den ikke kan sige. Bjørn navngiver via bind() (ceremoni). Self-safe."""
    out = []
    for name, cnt in (name_counts or {}).items():
        if int(cnt) >= int(min_count) and to_term(str(name)) is None:
            out.append({"name": str(name), "count": int(cnt)})
    out.sort(key=lambda x: x["count"], reverse=True)
    return out[:top]


def propose_from_event_stream(*, window: int = 2000, min_count: int = 5) -> list[dict[str, Any]]:
    """Scan de seneste events → hvilke UBUNDNE familier sanser Centralen ofte uden at kunne sige dem?
    'Centralen kigger på hvad den mærker og beder om ord den mangler.' Self-safe."""
    counts: dict[str, int] = {}
    try:
        from core.eventbus.bus import event_bus
        for ev in event_bus.recent(limit=int(window)):
            fam = str(ev.get("kind") or "").split(".", 1)[0]
            if fam:
                counts[fam] = counts.get(fam, 0) + 1
    except Exception:
        pass
    return propose_word_needs(counts, min_count=min_count)


def build_central_lexicon_surface() -> dict[str, object]:
    """Mission Control surface — read-only: vokabular, bindinger, hvad sproget kan/ikke kan sige."""
    db = _db_bindings()
    all_bindings = {**SEED_BINDINGS, **db}
    return {"active": True, "vocabulary_size": len(_ACTIVE_TERMS),
            "operators": sorted(_OPERATORS), "bound_count": len(all_bindings),
            "bindings": all_bindings, "word_needs": propose_from_event_stream()}
