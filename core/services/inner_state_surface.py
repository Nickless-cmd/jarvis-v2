"""Samlet flade for de indre tilstands-lag — de build_*_surface ingen læser havde.

MAALT 7/11-2026 paa tvaers af HELE repoet (ikke kun apps/): 464 ``build_*_surface``
i core/services. Efter de tre foerste aggregatorer (hukommelse, godkendelse,
drift) stod 31 tilbage med nul reference uden for deres egen fil — maalt baade som
tekst-soegning og ved at kalde hver enkelt.

De 31 her er ikke maskinrummet. Det er de lag der beskriver HVAD JEG ER og HVAD JEG
BESLUTTER: drev-arbitrering, emotions-tagging, identitets-komposition, metakognitiv
integration, selektiv opmaerksomhed, subjektiv tid, resonans-henfald — og de
beslutnings-lag der afgoer hvordan et svar bliver til (klassifikation, eskalering,
konflikt-loesning, konfigurations-drift).

Grupperet efter hvem der EJER tilstanden, ikke efter mappenavn: en fil i
``core/services/`` siger hvor koden bor, ikke hvad den tilhoerer.

Bemaerk om ``active``: en flade der svarer ``active=False`` med en grund er ikke
doed — den melder at der intet er at vise. ``selective_attention`` gjorde praecis
det, og ``approval_runtime`` gjorde det i gaar. Derfor skelner denne aggregator
mellem ``svarer`` (returnerede en ikke-tom dict) og ``active`` (indholdets eget
svar). En tavs flade er kun én der fejlede eller returnerede tomt.
"""
from __future__ import annotations

import importlib
from typing import Any

#: Ejer-relation → (navn, modul, funktion). Alle maalt 7/11-2026: nul paakraevede
#: argumenter, dict-svar, nul fejl, nul tomme. Ingen LLM-kald.
_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    # Hvem jeg er lige nu — drev, foelser, identitet, tid, opmaerksomhed.
    "indre": [
        ("drive_arbitration", "core.services.drive_arbitration_engine", "build_drive_arbitration_surface"),
        ("emotion_tagging", "core.services.emotion_tagging", "build_emotion_tagging_surface"),
        ("identity_composer", "core.services.identity_composer", "build_identity_composer_surface"),
        ("metacognitive_integration", "core.services.metacognitive_integration", "build_metacognitive_integration_surface"),
        ("selective_attention", "core.services.selective_attention", "build_selective_attention_surface"),
        ("self_model_predictive", "core.services.self_model_predictive", "build_self_model_predictive_surface"),
        ("subjective_time", "core.services.subjective_time", "build_subjective_time_surface"),
        ("temporal_self_continuity", "core.services.temporal_self_continuity", "build_temporal_self_continuity_surface"),
        ("embodied_presence", "core.services.embodied_presence", "build_embodied_presence_surface"),
        ("resonance_decay", "core.services.resonance_decay", "build_resonance_decay_surface"),
        ("precision_bias", "core.services.precision_bias", "build_precision_bias_surface"),
        ("curiosity_debt", "core.services.curiosity_hypothesis_debt", "build_curiosity_debt_surface"),
        ("current_pull", "core.services.current_pull", "build_current_pull_surface"),
        ("completion_satisfaction", "core.services.completion_satisfaction", "build_completion_satisfaction_surface"),
        ("conflict_resolution", "core.services.conflict_resolution", "build_conflict_resolution_surface"),
        ("development_ritual", "core.services.development_ritual", "build_development_ritual_surface"),
        ("life_milestones", "core.services.life_milestones", "build_life_milestones_surface"),
        ("dreaming_session", "core.services.dreaming_session", "build_dreaming_session_surface"),
    ],
    # Hvordan et svar bliver til — klassifikation, eskalering, gate, telemetri.
    "beslutning": [
        ("clarification_classifier", "core.services.clarification_classifier", "build_clarification_classifier_surface"),
        ("reasoning_classifier", "core.services.reasoning_classifier", "build_reasoning_classifier_surface"),
        ("reasoning_escalation", "core.services.reasoning_escalation", "build_reasoning_escalation_surface"),
        ("config_drift", "core.services.config_drift", "build_config_drift_surface"),
        ("decision_signal_telemetry", "core.services.decision_signal_telemetry", "build_decision_signal_telemetry_surface"),
        ("read_before_write_guard", "core.services.read_before_write_guard", "build_read_before_write_guard_surface"),
    ],
    # Hvad jeg goer i verden — planer, budget, kandidater, profiler.
    "verden": [
        ("autonomy_budget", "core.services.autonomy_budget", "build_autonomy_budget_surface"),
        ("proactive_candidates", "core.services.proactive_candidates", "build_proactive_candidates_surface"),
        ("candidate_review_digest", "core.services.candidate_review_digest", "build_candidate_review_digest_surface"),
        ("scheduled_tasks", "core.services.scheduled_tasks", "build_scheduled_tasks_surface"),
        ("central_profiles", "core.services.central_profiles", "build_profiles_surface"),
        ("central_agent_smith", "core.services.central_agent_smith", "build_agent_smith_surface"),
        ("central_moltbook", "core.services.central_moltbook", "build_moltbook_surface"),
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


def build_inner_state_surface() -> dict[str, Any]:
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
                # Fejlede eller svarede tomt — men kun hvis den ikke selv
                # melder en grund som en DEL af et ellers gyldigt svar.
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
        "mode": "inner-state-v1",
        "groups": groups,
        "svarer": svarer,
        "active": aktive,
        "taxse": taxse,
        "summary": (
            f"{len(svarer)}/{len(producer_names())} indre lag svarer "
            f"({len(aktive)} melder aktivt indhold)"
            + (f"; taxse: {', '.join(taxse)}" if taxse else "")
        ),
    }
