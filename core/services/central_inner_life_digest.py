"""Inner-life digest — §24.4 reduceret ved kilden: KUN liveness+count pr. sektion.

Kører i jarvis-runtime (hvor daemon-tilstanden bor). Rå tanke/drøm/konflikt-indhold
forlader ALDRIG denne proces — kun bool liveness + int count pr. sektion. Proxy'es
som én samlet flade til /central/inner-life (§24.4 PRIVATE_NO_EGRESS-ånd)."""
from __future__ import annotations
from typing import Callable

# (sektion-navn, modul-sti, funktionsnavn) — to grupper: living-mind + experiment/AGI.
# INNER_LIFE: Jarvis' levende sind (somatik, tanke, drøm, konflikt, undren, ...).
_INNER_LIFE: list[tuple[str, str, str]] = [
    ("body", "core.services.somatic_daemon", "build_body_state_surface"),
    ("thought_stream", "core.services.thought_stream_daemon", "build_thought_stream_surface"),
    ("thought_proposals", "core.services.thought_action_proposal_daemon", "build_proposal_surface"),
    ("surprise", "core.services.surprise_daemon", "build_surprise_surface"),
    ("taste", "core.services.aesthetic_taste_daemon", "build_taste_surface"),
    ("irony", "core.services.irony_daemon", "build_irony_surface"),
    ("desire", "core.services.desire_daemon", "build_desire_surface"),
    ("curiosity", "core.services.curiosity_daemon", "build_curiosity_surface"),
    ("meta_reflection", "core.services.meta_reflection_daemon", "build_meta_reflection_surface"),
    ("conflict", "core.services.conflict_daemon", "build_conflict_surface"),
    ("dream", "core.services.dream_insight_daemon", "build_dream_insight_surface"),
    ("wonder", "core.services.existential_wonder_daemon", "build_existential_wonder_surface"),
    ("reflection", "core.services.reflection_cycle_daemon", "build_reflection_surface"),
    ("experienced_time", "core.services.experienced_time_daemon", "build_experienced_time_surface"),
    ("development_narrative", "core.services.development_narrative_daemon", "build_development_narrative_surface"),
    ("code_aesthetic", "core.services.code_aesthetic_daemon", "build_code_aesthetic_surface"),
    ("user_model", "core.services.user_model_daemon", "build_user_model_surface"),
    ("memory_decay", "core.services.memory_decay_daemon", "build_memory_decay_surface"),
    ("creative_drift", "core.services.creative_drift_daemon", "build_creative_drift_surface"),
    ("layer_tension", "core.services.layer_tension_daemon", "build_layer_tension_surface"),
    ("dream_motif", "core.services.dream_motif_daemon", "build_dream_motif_surface"),
    ("absence", "core.services.absence_daemon", "build_absence_surface"),
]

# EXPERIMENT: AGI/experiment-lag (adaptiv læring, planlægning, selv-mutation, ...).
_EXPERIMENT: list[tuple[str, str, str]] = [
    ("adaptive_learning", "core.services.adaptive_learning_runtime", "build_adaptive_learning_runtime_surface"),
    ("adaptive_planner", "core.services.adaptive_planner_runtime", "build_adaptive_planner_runtime_surface"),
    ("adaptive_reasoning", "core.services.adaptive_reasoning_runtime", "build_adaptive_reasoning_runtime_surface"),
    ("affective_meta", "core.services.affective_meta_state", "build_affective_meta_state_surface"),
    ("epistemic", "core.services.epistemic_runtime_state", "build_epistemic_runtime_state_surface"),
    ("guided_learning", "core.services.guided_learning_runtime", "build_guided_learning_runtime_surface"),
    ("idle_consolidation", "core.services.idle_consolidation", "build_idle_consolidation_surface"),
    ("loop_runtime", "core.services.loop_runtime", "build_loop_runtime_surface"),
    ("prompt_evolution", "core.services.prompt_evolution_runtime", "build_prompt_evolution_runtime_surface"),
    ("subagent_ecology", "core.services.subagent_ecology", "build_subagent_ecology_surface"),
    ("embodied", "core.services.embodied_state", "build_embodied_state_surface"),
    ("dream_articulation", "core.services.dream_articulation", "build_dream_articulation_surface"),
    ("dream_influence", "core.services.dream_influence_runtime", "build_dream_influence_runtime_surface"),
    ("self_mutation", "core.services.self_mutation_lineage", "build_self_mutation_lineage_surface"),
    ("internal_cadence", "core.services.internal_cadence", "get_cadence_state"),
]


def _first_count(surface: dict) -> int:
    """Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den
    første liste-værdi, ellers den første ikke-negative int-værdi, ellers 0."""
    if not isinstance(surface, dict):
        return 0
    for v in surface.values():
        if isinstance(v, (list, tuple)):
            return len(v)
    for v in surface.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and v >= 0:
            return v
    return 0


def _reduce(surface) -> dict:
    """KUN liveness+count. Ingen tekst. Self-safe."""
    if not isinstance(surface, dict) or not surface:
        return {"liveness": False, "count": 0}
    active = surface.get("active")
    liveness = bool(active) if active is not None else True
    return {"liveness": liveness, "count": _first_count(surface)}


def _build_group(group: list[tuple[str, str, str]]) -> dict[str, dict]:
    """Byg én gruppe reduceret. Self-safe pr. sektion (import/kald i try/except
    → ``{liveness:False,count:0}``). Kun liveness+count pr. sektion — ingen tekst."""
    import importlib
    out: dict[str, dict] = {}
    for name, mod, fn in group:
        try:
            m = importlib.import_module(mod)
            builder: Callable = getattr(m, fn)
            out[name] = _reduce(builder())
        except Exception:
            out[name] = {"liveness": False, "count": 0}
    return out


def build_inner_life_digest() -> dict:
    """Samlet reduceret living-mind + experiment/AGI-digest. Kaster ALDRIG.
    Kun liveness+count pr. sektion (§24.4 reducér-ved-kilden)."""
    inner_life = _build_group(_INNER_LIFE)
    experiment = _build_group(_EXPERIMENT)
    live_count = (
        sum(1 for s in inner_life.values() if s.get("liveness"))
        + sum(1 for s in experiment.values() if s.get("liveness"))
    )
    return {
        "inner_life": inner_life,
        "experiment": experiment,
        "live_count": live_count,
        "total": len(inner_life) + len(experiment),
    }
