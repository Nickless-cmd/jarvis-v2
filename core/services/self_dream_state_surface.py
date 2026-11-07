"""Samlet flade for Jarvis' SELV- og DROEMME-tilstand.

MAALT 7/11-2026: 462 ``build_*_surface`` i core/services; 315 usynlige for
operatoeren. Bunken her er modulerne hvis navn starter med ``self`` eller ``dream``.
Hver kandidat blev kaldt med ``PYTHONPATH=. python`` FOER den kom i listen:
nul paakraevede argumenter, dict-svar, nul fejl. ``active`` var sat i 25 af 34;
``self_mutation_lineage``, ``dream_influence_runtime``, ``dream_insight_daemon``,
``dream_motif_daemon``, ``central_dream_action``, ``self_model_history``,
``self_repair_engine`` svarer med indhold men uden ``active``-noeglen.

UDELADT, med grund:
- ``dreaming_session``  — allerede i ``inner_state_surface`` (gruppen "indre").
- ``dream_action_executor`` — allerede i ``infra_state_surface``.
- ``self_model_predictive`` — allerede i ``inner_state_surface``.
Dobbelt-visning ville give to sandheder om samme flade.

TILFOEJET ud over kandidatlisten (samme praefiks, samme maaling, nul fejl, ikke
synlige andre steder): ``self_model_history``, ``self_repair_engine``,
``self_narrative_self_model_review_bridge``, ``dream_adoption_candidate_tracking``,
``dream_hypothesis_signal_tracking``, ``dream_influence_proposal_tracking``.

Ingen producent kraever argumenter. ``*_tracking``-fladerne tager ``limit`` med
default og kaldes uden. READ-ONLY; ingen LLM-kald.
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_S = "core.services."

#: Gruppe → (navn, modul, funktion).
_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    "selv": [
        ("self_compassion", _S + "self_compassion", "build_self_compassion_surface"),
        ("self_critique", _S + "self_critique_runtime", "build_self_critique_surface"),
        ("self_deception_guard", _S + "self_deception_guard", "build_self_deception_guard_surface"),
        ("self_experiments", _S + "self_experiments", "build_self_experiments_surface"),
        ("self_mutation_lineage", _S + "self_mutation_lineage", "build_self_mutation_lineage_surface"),
        ("self_review_unified", _S + "self_review_unified", "build_self_review_surface"),
        ("self_surprise", _S + "self_surprise_detection", "build_self_surprise_surface"),
        ("self_system_code_awareness", _S + "self_system_code_awareness", "build_self_system_code_awareness_surface"),
        ("self_model_blind_spots", _S + "self_model_blind_spots", "build_blind_spots_surface"),
        ("self_model_history", _S + "self_model_history", "build_self_model_history_surface"),
        ("self_repair", _S + "self_repair_engine", "build_self_repair_surface"),
        ("selfhood_proposals", _S + "selfhood_proposal_tracking", "build_runtime_selfhood_proposal_surface"),
        ("self_model_signals", _S + "self_model_signal_tracking", "build_runtime_self_model_signal_surface"),
        ("self_narrative_continuity", _S + "self_narrative_continuity_signal_tracking", "build_runtime_self_narrative_continuity_signal_surface"),
        ("self_narrative_review_bridge", _S + "self_narrative_self_model_review_bridge", "build_runtime_self_narrative_self_model_review_bridge_surface"),
        ("self_review_cadence", _S + "self_review_cadence_signal_tracking", "build_runtime_self_review_cadence_signal_surface"),
        ("self_review_outcome", _S + "self_review_outcome_tracking", "build_runtime_self_review_outcome_surface"),
        ("self_review_record", _S + "self_review_record_tracking", "build_runtime_self_review_record_surface"),
        ("self_review_run", _S + "self_review_run_tracking", "build_runtime_self_review_run_surface"),
        ("self_review_signal", _S + "self_review_signal_tracking", "build_runtime_self_review_signal_surface"),
        ("self_authored_prompt_proposals", _S + "self_authored_prompt_proposal_tracking", "build_runtime_self_authored_prompt_proposal_surface"),
    ],
    "drom": [
        ("dream_articulation", _S + "dream_articulation", "build_dream_articulation_surface"),
        ("dream_carry_over", _S + "dream_carry_over", "build_dream_carry_over_surface"),
        ("dream_consolidation", _S + "dream_consolidation_daemon", "build_dream_consolidation_surface"),
        ("dream_continuum", _S + "dream_continuum", "build_dream_continuum_surface"),
        ("dream_distillation", _S + "dream_distillation_daemon", "build_dream_distillation_surface"),
        ("dream_hypothesis", _S + "dream_hypothesis_generator", "build_dream_hypothesis_surface"),
        ("dream_influence", _S + "dream_influence_runtime", "build_dream_influence_runtime_surface"),
        ("dream_insight", _S + "dream_insight_daemon", "build_dream_insight_surface"),
        ("dream_motif", _S + "dream_motif_daemon", "build_dream_motif_surface"),
        ("dream_action", _S + "central_dream_action", "build_dream_action_surface"),
        ("dream_adoption_candidates", _S + "dream_adoption_candidate_tracking", "build_runtime_dream_adoption_candidate_surface"),
        ("dream_hypothesis_signals", _S + "dream_hypothesis_signal_tracking", "build_runtime_dream_hypothesis_signal_surface"),
        ("dream_influence_proposals", _S + "dream_influence_proposal_tracking", "build_runtime_dream_influence_proposal_surface"),
    ],
}


def producer_names() -> list[str]:
    """Navnene i kald-raekkefoelge, paa tvaers af grupperne — til test."""
    return [name for group in _GROUPS.values() for (name, _m, _f) in group]


def group_names() -> list[str]:
    return list(_GROUPS)


def _call(mod_path: str, fn_attr: str) -> dict[str, Any]:
    """Kald én producent. En defekt maa ikke skjule de oevrige."""
    try:
        surface = getattr(importlib.import_module(mod_path), fn_attr)()
    except Exception as exc:
        logger.warning("self_dream_state_surface: %s.%s fejlede: %s", mod_path, fn_attr, exc)
        return {"active": False, "reason": f"{type(exc).__name__}: {exc}"[:200], "failed": True}
    if not isinstance(surface, dict):
        return {"active": False, "reason": f"returnerede {type(surface).__name__}, ikke dict", "failed": True}
    if not surface:
        return {"active": False, "reason": "returnerede en tom dict", "failed": True}
    return surface


def build_self_dream_state_surface() -> dict[str, Any]:
    """Kald alle producenter, grupperet. Kaster ALDRIG.

    ``svarer`` = returnerede indhold; ``active`` = selv meldte ``active=True``;
    ``taxse`` = kastede eller returnerede tomt/ikke-dict.
    """
    groups: dict[str, dict[str, Any]] = {}
    svarer: list[str] = []
    aktive: list[str] = []
    taxse: list[str] = []
    for group, producers in _GROUPS.items():
        indhold: dict[str, Any] = {}
        for name, mod_path, fn_attr in producers:
            surface = _call(mod_path, fn_attr)
            indhold[name] = surface
            if surface.get("failed") is True:
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
    total = len(producer_names())
    return {
        "mode": "self-dream-state-v1",
        "groups": groups,
        "svarer": svarer,
        "active": aktive,
        "taxse": taxse,
        "summary": (
            f"{len(svarer)}/{total} selv- og droemme-lag svarer "
            f"({len(aktive)} melder aktivt indhold)"
            + (f"; taxse: {', '.join(taxse)}" if taxse else "")
        ),
    }
