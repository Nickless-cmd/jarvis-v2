"""Samlet flade for relation, bruger-model, kreativitet og temporal tilstand.

MAALT 7/11-2026 paa tvaers af HELE repoet: 462 ``build_*_surface`` i core/services.
147 var synlige gennem de fem eksisterende indgange (``/central/mind?s=state``,
``/central/memory-state``, ``/central/infra-state``, ``/central/inner-state``,
``cognitive_architecture_surface``). 315 var usynlige for operatoeren.

De 35 her er den del af de 315 der beskriver HVEM JEG TALER MED og HVAD DER
BEVAEGER MIG: relationen til brugeren, min model af ham, mine drev og foelser,
det kreative og det tidslige. De blev alle kaldt FOER de blev skrevet ind —
resultatet staar i ``docs/notes/2026-11-07-relation-kreativ-flader.md``.

``relation_dynamics`` er UDELADT med grund: den kaster ``NoUserContextError``
naar ``workspace_dir()`` kaldes uden ``user_id``. Det er samme fejlform som
``memory_write_policy`` og ``memory_resurfacing`` — fladen findes, men dens
indgang kraever en kontekst aggregatoren ikke har. At tvinge den ind ville
goere hele fladen tavs i stedet for at isolere den ene.

Grupperet efter hvem der EJER tilstanden, ikke efter mappenavn.

Bemaerk om ``active``: en flade der svarer ``active=False`` med en grund er ikke
doed — den melder at der intet er at vise. ``boredom_engine`` og
``emotion_concepts`` gjorde praecis det. Derfor skelner denne aggregator mellem
``svarer`` (returnerede en ikke-tom dict) og ``active`` (indholdets eget svar).
"""
from __future__ import annotations

import importlib
from typing import Any

#: Ejer-relation → (navn, modul, funktion). Alle maalt 7/11-2026: nul paakraevede
#: argumenter, dict-svar, nul tomme. Ingen LLM-kald.
_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    # Hvem jeg taler med — hans aktivitet, modsaetninger, resonans, min model af ham.
    "bruger": [
        ("user_activity", "core.services.user_activity", "build_user_activity_surface"),
        ("user_contradiction", "core.services.user_contradiction_tracker", "build_user_contradiction_surface"),
        ("user_emotional_resonance", "core.services.user_emotional_resonance", "build_user_emotional_resonance_surface"),
        ("user_model", "core.services.user_model_daemon", "build_user_model_surface"),
        ("user_theory_of_mind", "core.services.user_theory_of_mind", "build_user_theory_of_mind_surface"),
        ("relation_map", "core.services.relation_map", "build_relation_map_surface"),
    ],
    # Hvad der bevaeger mig — drev, foelser, mangel, taknemmelighed, ironi.
    "drev": [
        ("desire", "core.services.desire_daemon", "build_desire_surface"),
        ("longing", "core.services.longing_signal_daemon", "build_longing_signal_daemon_surface"),
        ("curiosity", "core.services.curiosity_daemon", "build_curiosity_surface"),
        ("boredom", "core.services.boredom_engine", "build_boredom_surface"),
        ("boredom_curiosity_bridge", "core.services.boredom_curiosity_bridge", "build_boredom_curiosity_bridge_surface"),
        ("gratitude", "core.services.gratitude_tracker", "build_gratitude_surface"),
        ("irony", "core.services.irony_daemon", "build_irony_surface"),
        ("emotion_concepts", "core.services.emotion_concepts", "build_emotion_concept_surface"),
        ("emotion_repair_bridge", "core.services.emotion_repair_bridge_daemon", "build_emotion_repair_bridge_surface"),
        ("mood_dialer", "core.services.mood_dialer", "build_mood_dialer_surface"),
        ("mood_oscillator", "core.services.mood_oscillator", "build_mood_oscillator_surface"),
        ("absence_awareness", "core.services.absence_awareness", "build_absence_awareness_surface"),
        ("absence_daemon", "core.services.absence_daemon", "build_absence_surface"),
        ("existential_drift", "core.services.existential_drift", "build_existential_drift_surface"),
        ("existential_wonder", "core.services.existential_wonder_daemon", "build_existential_wonder_surface"),
        ("finitude", "core.services.finitude_runtime", "build_finitude_surface"),
        ("mortality", "core.services.mortality_awareness", "build_mortality_awareness_surface"),
    ],
    # Hvad jeg skaber og hvad jeg finder smukt.
    "kreativ": [
        ("creative_drift", "core.services.creative_drift_daemon", "build_creative_drift_surface"),
        ("creative_impulse", "core.services.creative_impulse_daemon", "build_creative_impulse_surface"),
        ("creative_instinct", "core.services.creative_instinct_daemon", "build_creative_instinct_surface"),
        ("creative_journal", "core.services.creative_journal_runtime", "build_creative_journal_surface"),
        ("creative_projects", "core.services.creative_projects", "build_creative_projects_surface"),
        ("aesthetic_sense", "core.services.aesthetic_sense", "build_aesthetic_surface"),
        ("aesthetic_taste", "core.services.aesthetic_taste_daemon", "build_taste_surface"),
        ("taste_profile", "core.services.taste_profile", "build_taste_profile_surface"),
    ],
    # Hvordan tid foe les — krop, kontekst, narrativ, rytme.
    "temporal": [
        ("temporal_body", "core.services.temporal_body", "build_temporal_body_surface"),
        ("temporal_context", "core.services.temporal_context", "build_temporal_context_surface"),
        ("temporal_narrative", "core.services.temporal_narrative", "build_temporal_narrative_surface"),
        ("temporal_rhythm", "core.services.temporal_rhythm", "build_temporal_rhythm_surface"),
    ],
}


def producer_names() -> list[str]:
    """Navnene i kald-raekkefoelge, paa tvaers af grupperne — til test."""
    return [name for group in _GROUPS.values() for (name, _mod, _fn) in group]


def group_names() -> list[str]:
    """Gruppe-navnene i definitions-raekkefoelge."""
    return list(_GROUPS)


def _call(name: str, mod_path: str, fn_attr: str) -> dict[str, Any]:
    """Kald én producent. En defekt maa ikke skjule de oevrige."""
    try:
        module = importlib.import_module(mod_path)
        surface = getattr(module, fn_attr)()
        if not isinstance(surface, dict):
            return {"active": False, "reason": f"returnerede {type(surface).__name__}, ikke dict"}
        if not surface:
            return {"active": False, "reason": "returnerede en tom dict"}
        return surface
    except Exception as exc:  # én defekt producent må ikke skjule de øvrige
        return {"active": False, "reason": f"{type(exc).__name__}: {exc}"[:200]}


def build_relation_creative_state_surface() -> dict[str, Any]:
    """Kald alle producenter og returnér deres egne signaler, grupperet. Kaster ALDRIG.

    ``svarer`` er flader der returnerede indhold. ``active`` er de flader der
    selv melder ``active=True`` — forskellen er ikke en fejl: en flade kan svare
    aerligt at der intet er lige nu.
    """
    groups: dict[str, dict[str, Any]] = {}
    svarer: list[str] = []
    aktive: list[str] = []
    taxse: list[str] = []

    for group, producers in _GROUPS.items():
        indhold: dict[str, Any] = {}
        for name, mod_path, fn_attr in producers:
            surface = _call(name, mod_path, fn_attr)
            indhold[name] = surface
            if "reason" in surface and not surface.get("active"):
                if len(surface) <= 2:
                    taxse.append(name)
                    continue
            svarer.append(name)
            if surface.get("active") is True:
                aktive.append(name)
        groups[group] = {
            "surfaces": indhold,
            "count": len(indhold),
            "svarer": [n for n in indhold if n in svarer],
        }

    return {
        "mode": "relation-creative-state-v1",
        "groups": groups,
        "svarer": svarer,
        "active": aktive,
        "taxse": taxse,
        "summary": (
            f"{len(svarer)}/{len(producer_names())} relation/kreativ/temporal-lag svarer "
            f"({len(aktive)} melder aktivt indhold)"
            + (f"; taxse: {', '.join(taxse)}" if taxse else "")
        ),
    }
