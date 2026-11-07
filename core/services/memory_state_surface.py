"""Samlet flade for hukommelses-lagene — de build_*_surface ingen rute kaldte.

Målt 7/11-2026: 202 ``build_*_surface`` i core/services blev aldrig kaldt fra
apps/. Hukommelses-bunken var den største sammenhængende gruppe: modulerne var
importeret, daemonerne kørte, tilstanden fandtes — men ingen læste fladen.
En flade ingen indgang har, er stadig mørk for både Jarvis og operatøren.

Mønstret er det samme som ``central_tool_infra_surface``: deklarativ
``_PRODUCERS``, én læsning kalder alle READ-ONLY surfaces og returnerer deres
egne signaler uændret, og hver producent er self-safe — en kastende flade
isoleres til ``{"active": False, "reason": …}``.

UDELADT efter måling (kræver kontekst, tvinges ikke ind):
- ``memory_write_policy.build_memory_write_policy_surface`` kaster
  NoUserContextError uden bruger-kontekst (workspace_dir() har intet user_id).
- ``emotional_memory_engine.build_emotional_memory_surface`` kræver de
  keyword-only argumenter ``anchor_type`` og ``context``.
"""
from __future__ import annotations

import importlib
from typing import Any

# (navn, modul, funktion). Alle målt: ingen påkrævede argumenter, dict-svar,
# 0-20 ms, ingen LLM-kald.
_PRODUCERS: list[tuple[str, str, str]] = [
    ("semantic_memory", "core.services.semantic_memory", "build_semantic_memory_surface"),
    ("memory_emotional_context", "core.services.memory_emotional_context", "build_memory_emotional_context_surface"),
    ("cross_agent_memory", "core.services.cross_agent_memory", "build_cross_agent_memory_surface"),
    ("end_of_run_memory_consolidation", "core.services.end_of_run_memory_consolidation", "build_end_of_run_memory_consolidation_surface"),
    ("associative_recall", "core.services.associative_recall", "build_associative_recall_surface"),
    ("memory_recall_engine", "core.services.memory_recall_engine", "build_memory_recall_engine_surface"),
    ("memory_safeguard", "core.services.daemon_memory_safeguard", "build_memory_safeguard_surface"),
    ("memory_graph", "core.services.memory_graph", "build_memory_graph_surface"),
    ("memory_hygiene", "core.services.memory_hygiene", "build_memory_hygiene_surface"),
    ("memory_resurfacing", "core.services.memory_resurfacing", "build_memory_resurfacing_surface"),
    ("memory_breathing", "core.services.memory_breathing", "build_memory_breathing_surface"),
    ("memory_write_queue", "core.services.memory_write_queue", "build_memory_write_queue_surface"),
    ("memory_maintenance", "core.services.memory_maintenance_daemon", "build_memory_maintenance_surface"),
    ("memory_pruning", "core.services.memory_pruning_daemon", "build_memory_pruning_surface"),
    ("memory_recall_telemetry", "core.services.memory_recall_telemetry", "build_memory_recall_telemetry_surface"),
    ("memory_density", "core.services.memory_density", "build_memory_density_surface"),
    ("visual_memory", "core.services.visual_memory", "build_visual_memory_surface"),
    ("conflict_memory", "core.services.conflict_prompt_service", "build_conflict_memory_surface"),
    ("council_memory", "core.services.council_memory_service", "build_council_memory_surface"),
]


def producer_names() -> list[str]:
    """Navnene i kald-rækkefølge — til test og introspektion."""
    return [name for (name, _mod, _fn) in _PRODUCERS]


def _is_live(surface: Any) -> bool:
    if not isinstance(surface, dict) or not surface:
        return False
    if "active" in surface:
        return bool(surface["active"])
    # Daemon-flader uden active-nøgle (maintenance/pruning/visual) melder
    # data hvis de har et indhold og ikke selv er fejl-indpakket.
    return "reason" not in surface


def build_memory_state_surface() -> dict[str, Any]:
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
        "mode": "memory-state-v1",
        "surfaces": surfaces,
        "live": live,
        "silent": silent,
        "summary": (
            f"{len(live)}/{len(surfaces)} hukommelses-lag melder data"
            + (f"; tavse: {', '.join(silent)}" if silent else "")
        ),
    }
