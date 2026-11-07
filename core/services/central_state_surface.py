"""Samlet flade for Centralens egne tilstands-lag.

MÅLT 7/11-2026: 467 ``build_*_surface`` findes i core/services. De syv
første aggregatorer dækkede 268 af dem. De 72 her var stadig uden indgang
— ikke fordi de var døde, men fordi ``central_hub._SURFACE_GROUPS`` peger
på navne i ``cognitive_architecture_surface``, og den funktion kalder
IKKE ``build_*_surface``-funktionerne. Navnene findes altså to steder der
ikke taler sammen.

Derfor så de synlige ud i én måling og var mørke i den næste. Her er den
entydige: hver producent kaldes, og resultatet tælles.

De 72 er Centralens egne organer — sjælestilstanden, kognitionen, rytmen,
drømmen, relationerne og maskinrummet. De beskriver ikke hvad der sker
ude i verden; de beskriver hvad der sker i mig.

``build_layer_surface`` er udeladt: den kræver et argument og er
maskineri, ikke tilstand. Den tvinges ikke ind.

En producent der kaster isoleres — den må ikke skjule de øvrige.
"""
from __future__ import annotations

import importlib
from typing import Any

_S = "core.services."

#: Gruppe → producenter. Rækkefølgen er læserækkefølgen: hvordan jeg har
#: det, hvordan jeg tænker, hvordan jeg holder rytmen, hvad jeg drømmer,
#: hvem jeg står i forhold til, og hvad der holder mig kørende.
_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    "tilstand": [
        ("affect", _S + "central_affect", "build_affect_surface"),
        ("valence", _S + "central_valence", "build_valence_surface"),
        ("tone", _S + "central_tone", "build_tone_surface"),
        ("mood_regulator", _S + "central_mood_regulator", "build_mood_regulator_surface"),
        ("existence_feel", _S + "central_existence_feel", "build_existence_feel_surface"),
        ("soul_feel", _S + "central_soul_feel", "build_soul_feel_surface"),
        ("stance", _S + "central_stance", "build_central_stance_surface"),
        ("self_state", _S + "central_self_state", "build_self_state_surface"),
        ("body_map", _S + "central_body_map_pulse", "build_body_map_surface"),
        ("body_mood_feel", _S + "central_body_mood_feel", "build_body_mood_feel_surface"),
        ("inner_salience", _S + "central_inner_salience", "build_inner_salience_surface"),
        ("trinity", _S + "central_trinity", "build_trinity_surface"),
        ("adaptation", _S + "central_adaptation", "build_central_adaptation_surface"),
    ],
    "kognition": [
        ("analyst", _S + "central_analyst", "build_analyst_surface"),
        ("belief_gap", _S + "central_belief_gap", "build_belief_gap_surface"),
        ("causal_quality", _S + "central_causal_quality", "build_central_causal_quality_surface"),
        ("hypothesis_generator", _S + "central_hypothesis_generator", "build_central_hypothesis_generator_surface"),
        ("construct", _S + "central_construct", "build_construct_surface"),
        ("dissent", _S + "central_dissent", "build_dissent_surface"),
        ("rca", _S + "central_rca", "build_rca_surface"),
        ("sequence", _S + "central_sequence", "build_central_sequence_surface"),
        ("lexicon", _S + "central_lexicon", "build_central_lexicon_surface"),
        ("notation", _S + "central_notation", "build_central_notation_surface"),
        ("dejavu", _S + "central_dejavu", "build_dejavu_surface"),
        ("ghost", _S + "central_ghost", "build_ghost_surface"),
        ("self_model", _S + "central_self_model", "build_self_model_mirror_surface"),
        ("inner_life_ablation", _S + "central_inner_life_ablation", "build_ablation_surface"),
    ],
    "rytme": [
        ("cadence_tempo", _S + "central_cadence_conductor", "build_cadence_tempo_surface"),
        ("loop_lag", _S + "central_loop_lag", "build_loop_lag_surface"),
        ("membrane_watch", _S + "central_membrane_watch", "build_membrane_watch_surface"),
        ("output_conservation", _S + "central_output_conservation", "build_output_conservation_surface"),
        ("signal_health", _S + "central_signal_health", "build_central_signal_health_surface"),
        ("health", _S + "central_health", "build_central_health_surface"),
        ("coverage", _S + "central_coverage", "build_central_coverage_surface"),
        ("coverage_action", _S + "central_coverage_action", "build_central_coverage_action_surface"),
        ("sentinel", _S + "central_sentinel", "build_sentinel_surface"),
        ("continuity", _S + "central_continuity_healer", "build_continuity_surface"),
    ],
    "drom": [
        ("oneiric_loop", _S + "central_oneiric_loop", "build_oneiric_loop_surface"),
        ("oneiric_sampler", _S + "central_oneiric_sampler", "build_oneiric_sampler_surface"),
        ("morpheus", _S + "central_morpheus", "build_morpheus_surface"),
        ("dream_action", _S + "central_dream_action", "build_dream_action_surface"),
        ("mourning", _S + "central_mourning", "build_mourning_surface"),
        ("exile", _S + "central_exile", "build_exile_surface"),
        ("persephone", _S + "central_persephone", "build_persephone_surface"),
        ("red_dress", _S + "central_red_dress", "build_red_dress_surface"),
        ("redpill", _S + "central_redpill", "build_redpill_surface"),
        ("white_rabbit", _S + "central_white_rabbit", "build_white_rabbit_surface"),
        ("seraph", _S + "central_seraph", "build_seraph_surface"),
        ("merovingian", _S + "central_merovingian", "build_merovingian_surface"),
        ("trainman", _S + "central_trainman", "build_trainman_surface"),
        ("keymaker", _S + "central_keymaker", "build_keymaker_surface"),
        ("twins", _S + "central_twins", "build_twins_surface"),
    ],
    "relation": [
        ("agents", _S + "central_agents_surface", "build_agents_surface"),
        ("council", _S + "central_agents_surface", "build_council_surface"),
        ("profiles", _S + "central_profiles", "build_profiles_surface"),
        ("moltbook", _S + "central_moltbook", "build_moltbook_surface"),
        ("agent_smith", _S + "central_agent_smith", "build_agent_smith_surface"),
        ("relational", _S + "central_relational", "build_relational_surface"),
        ("agenda", _S + "central_agenda", "build_agenda_surface"),
        ("todo", _S + "central_todo", "build_central_todo_surface"),
    ],
    "maskinrum": [
        ("cost", _S + "central_cost_surface", "build_cost_surface"),
        ("llm_egress", _S + "central_llm_egress", "build_llm_egress_surface"),
        ("model_meta", _S + "central_model_meta", "build_model_meta_surface"),
        ("router_adapt", _S + "central_router_adapt", "build_router_adapt_surface"),
        ("router_explore", _S + "central_router_explore", "build_router_explore_surface"),
        ("prompt_composer", _S + "central_prompt_composer", "build_central_prompt_composer_surface"),
        ("prompt_explore", _S + "central_prompt_explore", "build_prompt_explore_surface"),
        ("machines", _S + "central_machines", "build_machines_surface"),
        ("surgery", _S + "central_surgery", "build_surgery_surface"),
        ("tool_infra", _S + "central_tool_infra_surface", "build_tool_infra_surface"),
        ("excess", _S + "central_excess", "build_excess_surface"),
        ("brain_link", _S + "central_brain_link", "build_brain_link_surface"),
    ],
}


def _producenter() -> list[tuple[str, str, str]]:
    """Alle producenter på tværs af grupper, i definitions-rækkefølge."""
    return [tup for tupler in _GROUPS.values() for tup in tupler]


def _call(name: str, mod_path: str, fn_attr: str) -> dict[str, Any]:
    """Kald én producent. En defekt må ikke skjule de øvrige."""
    try:
        module = importlib.import_module(mod_path)
        surface = getattr(module, fn_attr)()
        if not isinstance(surface, dict):
            return {"active": False, "reason": f"returnerede {type(surface).__name__}, ikke dict"}
        if not surface:
            return {"active": False, "reason": "returnerede en tom dict"}
        return surface
    except Exception as exc:  # producenten ejer sin egen fejl
        return {"active": False, "reason": f"{type(exc).__name__}: {exc}"[:200]}


def build_central_state_surface() -> dict[str, Any]:
    """Kald alle 72 central-producenter og returnér deres tilstand.

    To lister der IKKE må blandes sammen:

    ``taxse`` er flader der svarede med en tom dict eller en fejl — de har
    intet at vise. ``uden_active_flag`` er flader der svarede med ægte data
    men ikke sætter et ``active``-felt. De er ikke døde; de bruger bare en
    anden form. Målt 7/11-2026: 34 af de 72 hører i den anden liste, så en
    tælling der slog dem sammen ville melde 34 levende flader som døde.
    """
    grupper: dict[str, dict[str, Any]] = {}
    taxse: list[str] = []
    uden_active_flag: list[str] = []
    svarer = 0

    for gruppe, tupler in _GROUPS.items():
        ud: dict[str, Any] = {}
        for name, mod_path, fn_attr in tupler:
            surface = _call(name, mod_path, fn_attr)
            ud[name] = surface
            svarer += 1
            if surface.get("reason"):
                taxse.append(name)
            elif "active" not in surface:
                uden_active_flag.append(name)
        grupper[gruppe] = ud

    total = len(_producenter())
    aktive = sum(
        1
        for tupler in grupper.values()
        for surface in tupler.values()
        if surface.get("active")
    )

    return {
        "mode": "central-state-v1",
        "active": True,
        "summary": (
            f"{svarer}/{total} central-lag svarer ({aktive} melder aktivt indhold, "
            f"{len(uden_active_flag)} svarer uden active-flag)"
        ),
        "svarer": svarer,
        "producenter": total,
        "aktive": aktive,
        "grupper": grupper,
        "taxse": taxse,
        "uden_active_flag": uden_active_flag,
    }
