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

MODULER (tilføjet 25/9-2026). Registret dækkede kun tabeller. Men Jarvis' audit
fandt 27 borde uden rækker, og en parallel gennemgang fandt 11 MODULER uden
bord — moduler der gemmer i en modul-global liste der dør ved genstart og er
usynlig for den proces der bygger fladen. Det er samme sag set fra hver sin
ende, og de hører til i samme register.

Status for moduler:
- kørende          — kaldes og gemmer varigt
- uden_bord        — kaldes, virker, men persisterer INTET
- bygget           — tidligere uden bord, nu med (se `note`)
- afløst           — gør det samme som `replacement`, som er i drift
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


# modul_navn -> klassifikation. Se docstringen for vokabularet.
_MODUL_REGISTRY: dict[str, dict[str, Any]] = {
    # — Kaldes, men gemmer intet —
    "continuity_kernel": {
        "status": "uden_bord",
        "note": (
            "Eksistens-FOELELSEN mellem tik (`get_existence_feeling`). Jeg var "
            "25/9-2026 ved at klassificere den som AFLOEST af `continuity` — "
            "forkert. `continuity` er tilstands-TRANSPORT mellem sessioner "
            "(`write_capsule`, `get_wake_tier`). Paastanden var bygget paa "
            "docstring-lighed, ikke paa hvad funktionerne goer."
        ),
    },
    "initiative_accumulator": {
        "status": "uden_bord",
        "note": (
            "Samler OENSKER der akkumulerer mellem tik. Ikke afloest af "
            "`initiative_queue`, som koer HANDLINGER (`push_initiative`, "
            "`approve_initiative`). Samme fejl som ovenfor, samme dag."
        ),
    },
    # — Bygget 25/9-2026: persistering + maalt indhold + en kalder —
    "body_memory": {
        "status": "bygget",
        "note": ("Gemte `random.choice([\"varm\",\"kold\",...])` i en modul-liste. "
                 "Fornemmelsen udledes nu af `embodied_state`, og grundlaget "
                 "gemmes med."),
    },
    "forgetting_curve": {
        "status": "bygget",
        "note": ("`register_memory` havde nul callers. Tikket laeser nu "
                 "arbejdssaettet fra `build_private_brain_context`."),
    },
    "decision_ghosts": {
        "status": "bygget",
        "note": ("`regret_potential` var `random.uniform(0.1, 0.6)`, og den "
                 "«mest saliente» fortrydelse var det hoejeste terningkast. "
                 "Kommer nu fra `adherence_score` i beslutnings-gennemgangen."),
    },
    "memory_tattoos": {
        "status": "bygget",
        "note": ("Kilden er `emotional_memory_anchors`, men KUN de "
                 "ikke-perceptuelle: 202.250 af 205.961 er `perceptual_event`, "
                 "og intensiteten maetter. Hoejst ét maerke i doegnet."),
    },
}

_MODUL_LEVENDE = {"koerende", "bygget", "afloest"}

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


def classify_module(name: str) -> dict[str, Any]:
    """Klassifikation for et MODUL. Ukendt → 'unclassified' (IKKE 'doedt').

    Tabeller uden raekker og moduler uden bord er to ender af samme sag: et lag
    hvor formen blev bygget faerdig og indholdet aldrig kom.
    """
    entry = _MODUL_REGISTRY.get(str(name or "").strip())
    if entry is None:
        return {"status": "unclassified", "module": name}
    return {"module": name, **entry}


def module_persists(name: str) -> bool:
    """False for et modul der kaldes men gemmer i hukommelsen."""
    return classify_module(name).get("status") in _MODUL_LEVENDE


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
