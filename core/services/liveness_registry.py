"""Liveness-registry (Stage 2, liveness-audit 2026-06-15).

Maskinlæsbar SANDHEDS-flade over Jarvis' livs-tabeller: er en tabel aktiv, afløst,
manuel-kun eller en forældreløs/depreceret port? Formålet er at STOPPE konfabulation
— både Jarvis' og menneskers — om at "hans systemer er døde". En tom GAMMEL tabel
betyder oftest AFLØST, ikke død; registeret peger på afløseren.

Grundet i verificeret audit (docs/audits/2026-06-15-cognitive-liveness-audit.md),
ikke gæt. Tabeller der IKKE står her er u-klassificerede (default), ikke "døde".

Status-vokabular:
- active            — producent + skriver løbende (verificeret)
- replaced          — gammel tabel, kognition migreret til `replacement` (parallel skriv kan stadig ske)
- manual_only       — skrives kun via et eksplicit tool, ikke autonomt
- orphaned          — skrive-funktion findes men har INGEN live-caller; depreceret
- wired             — tidligere forældreløs, nu fodret (se `note`)
"""
from __future__ import annotations

from typing import Any

# table_name -> klassifikation
_REGISTRY: dict[str, dict[str, Any]] = {
    # — Forældreløse/depreceret (un-integrerede ports; afløst af aktive systemer) —
    "cognitive_epistemic_claims": {
        "status": "orphaned", "producer": "epistemics.reconcile_claim (nul callers)",
        "replacement": "runtime_self_review_outcomes",
        "note": "Genuint distinkt evne (claim-kalibrering) — kandidat til ægte integration.",
    },
    "cognitive_wrongness": {
        "status": "orphaned", "producer": "epistemics.reconcile_claim (nul callers)",
        "replacement": "runtime_self_review_outcomes",
        "note": "Transitivt afhængig af epistemic_claims.",
    },
    "cognitive_missions": {
        "status": "orphaned", "producer": "missions_pipeline.create_mission (nul callers)",
        "replacement": "agent_dispatch (§19 multi-agent code-mode)",
        "note": "Un-integreret port; multi-agent håndteres af agent_dispatch.",
    },
    "cognitive_mission_messages": {
        "status": "orphaned", "producer": "missions_pipeline.send_mission_message (nul callers)",
        "replacement": "agent_dispatch",
    },
    "cognitive_trade_outcomes": {
        "status": "orphaned", "producer": "negotiation_pipeline.record_trade_outcome (nul callers)",
        "replacement": "cognitive_conflict_memories",
        "note": "Indre-stemme-konflikt håndteres af conflict_memories.",
    },
    # — Tidligere forældreløs, nu wired —
    "cognitive_gut_state": {
        "status": "wired", "producer": "gut_calibration via run_closure_gate (fix 4bfcc05a)",
        "note": "Fyldes ved afsluttede autonome runs. Var forældreløs til 15. jun.",
    },
    # — Manuel-kun (intentionelt; ikke død) —
    "meta_learning_hypotheses": {
        "status": "manual_only", "producer": "meta_learning_tools (Jarvis-tool)",
    },
    "meta_learning_hypothesis_samples": {
        "status": "manual_only", "producer": "meta_learning_tools (Jarvis-tool)",
    },
    # — Afløst-parallel (gammelt navn; kognition migreret til replacement, aktiv i dag) —
    "cognitive_dream_hypotheses": {
        "status": "replaced", "replacement": "runtime_dream_hypothesis_signals",
        "note": "Drømme PRODUCERER i den nye tabel; den gamle får sjælden parallel-skriv.",
    },
    "cognitive_chronicle_entries": {
        "status": "replaced", "replacement": "runtime_chronicle_consolidation_briefs",
    },
    "runtime_goal_signals": {
        "status": "replaced", "replacement": "runtime_development_focuses + runtime_initiatives",
        "note": "Parallel — alle tre skrives/læses; goals erstattes gradvist.",
    },
    # — Aktive kerne-organer (verificeret skriver dagligt; repr. udvalg) —
    "private_brain_records": {"status": "active"},
    "sensory_memories": {"status": "active"},
    "cognitive_experiential_memories": {"status": "active"},
    "cognitive_relationship_textures": {"status": "active"},
    "cognitive_counterfactuals": {"status": "active"},
    "runtime_self_review_outcomes": {"status": "active"},
    "runtime_world_model_signals": {"status": "active"},
    "runtime_dream_hypothesis_signals": {"status": "active"},
    "cognitive_decisions": {"status": "active"},
    "cognitive_personality_vectors": {"status": "active"},
}

_NON_DEAD = {"active", "wired", "replaced", "manual_only"}


def classify_table(name: str) -> dict[str, Any]:
    """Returnér klassifikation for en tabel. Ukendt → 'unclassified' (IKKE 'død')."""
    entry = _REGISTRY.get(str(name or "").strip())
    if entry is None:
        return {"status": "unclassified", "table": name}
    return {"table": name, **entry}


def is_alive(name: str) -> bool:
    """True hvis tabellen IKKE er forældreløs/død. Afløst/manuel/aktiv tæller som levende."""
    return classify_table(name).get("status") in _NON_DEAD


def liveness_summary() -> dict[str, Any]:
    """Aggregeret overblik — til Mission Control / anti-konfabulations-flade."""
    by_status: dict[str, list[str]] = {}
    for tab, entry in _REGISTRY.items():
        by_status.setdefault(str(entry["status"]), []).append(tab)
    return {
        "by_status": by_status,
        "counts": {s: len(v) for s, v in by_status.items()},
        "orphaned": by_status.get("orphaned", []),
        "replaced": {t: _REGISTRY[t].get("replacement") for t in by_status.get("replaced", [])},
    }
