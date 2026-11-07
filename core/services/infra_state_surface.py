"""Samlet flade for drifts- og infrastruktur-lagene — de build_*_surface ingen læser havde.

Målt 7/11-2026 på tværs af HELE repoet (ikke kun apps/): 464 ``build_*_surface`` i
core/services, hvoraf 24 blev refereret fra ingen anden fil end deres egen. 28 andre
saas som «kun-egen-fil» men naas via registry-tupler i central_lexicon,
eventbus_central_bridge og central_query_tool — de er ikke doede.

De 23 her er resten: daemoner og infrastruktur hvis tilstand fandtes, men hvis flade
ingen indgang havde. Det er samme fejlform som de 35 central-flader og de 19
hukommelses-flader — men denne gruppe er maskinrummet: cache, DB-helbred, mail,
vision, selv-reparation, ressource-signaler. Praecis den slags der koerer forkert i
maanedsvis uden at nogen opdager det, fordi ingen ser den.

UDELADT efter maaling (kraever argument, tvinges ikke ind):
- ``tool_intent_approval_runtime.build_sudo_approval_window_surface`` rejser
  TypeError uden et positionelt argument. Den er en vindues-beregning, ikke en
  tilstands-flade, og hoerer derfor ikke i en aggregator uden kontekst.
"""
from __future__ import annotations

import importlib
from typing import Any

# (navn, modul, funktion). Alle maalt 7/11-2026: ingen paakraevede argumenter,
# dict-svar, ingen LLM-kald.
_PRODUCERS: list[tuple[str, str, str]] = [
    ("db_sentinel", "core.services.db_sentinel", "build_db_health_surface"),
    ("shared_cache", "core.services.shared_cache", "build_shared_cache_surface"),
    ("cache_maintenance", "core.services.cache_maintenance_daemon", "build_cache_maintenance_surface"),
    ("runtime_resource_signal", "core.services.runtime_resource_signal", "build_runtime_resource_signal_surface"),
    ("runtime_action_outcome", "core.services.runtime_action_outcome_tracking", "build_runtime_action_outcome_surface"),
    ("cluster_family_scheduler", "core.services.cluster_family_scheduler", "build_cluster_family_scheduler_surface"),
    ("shutdown_window", "core.services.shutdown_window_daemon", "build_shutdown_window_surface"),
    ("paid_lane_guard", "core.services.paid_lane_guard", "build_paid_lane_guard_surface"),
    ("self_repair", "core.services.self_repair_engine", "build_self_repair_surface"),
    ("session_tool_pin", "core.services.session_tool_pin", "build_session_tool_pin_surface"),
    ("skill_relevance", "core.services.skill_relevance_surface", "build_skill_relevance_surface"),
    ("vision_backend", "core.services.vision_backend", "build_vision_backend_surface"),
    ("mail_checker", "core.services.mail_checker_daemon", "build_mail_checker_surface"),
    ("ambient_sound", "core.services.ambient_sound_daemon", "build_ambient_sound_surface"),
    ("query_language_bridge", "core.services.query_language_bridge", "build_query_language_bridge_surface"),
    ("policy_abstraction", "core.services.policy_abstraction", "build_generalized_policies_surface"),
    ("concept_baseline", "core.services.concept_baseline_tracker", "build_concept_baseline_surface"),
    ("repeated_requests", "core.services.repeated_requests", "build_repeated_requests_surface"),
    ("selective_consolidation", "core.services.selective_consolidation_daemon", "build_selective_consolidation_surface"),
    ("offline_recomposition", "core.services.offline_recomposition_engine", "build_offline_recomposition_surface"),
    ("dream_action_executor", "core.services.dream_action_executor", "build_executor_surface"),
    ("inner_dialectic", "core.services.inner_dialectic_engine", "build_inner_dialectic_surface"),
    ("self_model_history", "core.services.self_model_history", "build_self_model_history_surface"),
]


def producer_names() -> list[str]:
    """Navnene i kald-raekkefoelge — til test og introspektion."""
    return [name for (name, _mod, _fn) in _PRODUCERS]


def _is_live(surface: Any) -> bool:
    if not isinstance(surface, dict) or not surface:
        return False
    if "active" in surface:
        return bool(surface["active"])
    return "reason" not in surface


def build_infra_state_surface() -> dict[str, Any]:
    """Kald alle producenter og returnér deres egne signaler. Kaster ALDRIG."""
    surfaces: dict[str, Any] = {}
    for name, mod_path, fn_attr in _PRODUCERS:
        try:
            module = importlib.import_module(mod_path)
            surfaces[name] = getattr(module, fn_attr)()
        except Exception as exc:  # én defekt producent må ikke skjule de øvrige
            surfaces[name] = {
                "active": False,
                "reason": f"{type(exc).__name__}: {exc}"[:200],
            }

    live = [n for n, s in surfaces.items() if _is_live(s)]
    silent = [n for n in surfaces if n not in live]
    return {
        "mode": "infra-state-v1",
        "surfaces": surfaces,
        "live": live,
        "silent": silent,
        "summary": (
            f"{len(live)}/{len(surfaces)} drifts-lag melder data"
            + (f"; tavse: {', '.join(silent)}" if silent else "")
        ),
    }
