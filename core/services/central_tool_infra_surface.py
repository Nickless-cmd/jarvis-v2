"""Samlet flade for værktøjs-infrastrukturen — de 12 lag der ellers er usynlige.

Målt 7/11-2026: System Cartographer rapporterede 382 services med
runtime-indflydelse uden nogen flade. De 12 her fik bygget en ``build_*_surface``
hver — men INGEN rute kaldte dem, så Cartographer'en blev tilfredsstillet
(markøren fandtes) uden at synligheden steg. En flade ingen indgang har, er
stadig mørk for både Jarvis og operatøren.

Denne aggregator er indgangen: én læsning kalder alle 12 READ-ONLY surfaces og
returnerer deres egne signaler uændret. Den reducerer IKKE (modsat
``central_dark_products_digest``, der kun bærer liveness+count) — her er hele
pointen at kunne se tallene: hvad cachen indeholder, hvad gaten har stoppet,
hvor mange work-claims der manglede evidens.

Self-safe pr. producent: en manglende eller kastende flade isoleres til
``{"active": False, "reason": …}`` så én defekt ikke skjuler de øvrige.
"""
from __future__ import annotations

import importlib
from typing import Any

# (navn, modul, funktion). Alle verificeret READ-ONLY: kun state-/fil-/DB-læsning,
# ingen LLM-kald, ingen sleeps.
_PRODUCERS: list[tuple[str, str, str]] = [
    ("agent_approval_gate", "core.services.agent_approval_gate", "build_agent_approval_gate_surface"),
    ("agentic_tool_cache", "core.services.agentic_tool_cache", "build_agentic_tool_cache_surface"),
    ("cache_telemetry", "core.services.cache_telemetry", "build_cache_telemetry_surface"),
    ("causal_inference_daemon", "core.services.causal_inference_daemon", "build_causal_inference_daemon_surface"),
    ("composite_tools", "core.services.composite_tools", "build_composite_tools_surface"),
    ("task_worker", "core.services.task_worker", "build_task_worker_surface"),
    ("tool_calling_evidence", "core.services.tool_calling_evidence", "build_tool_calling_evidence_surface"),
    ("tool_embeddings", "core.services.tool_embeddings", "build_tool_embeddings_surface"),
    ("tool_hunt_nudge", "core.services.tool_hunt_nudge", "build_tool_hunt_nudge_surface"),
    ("tool_router_runtime", "core.services.tool_router_runtime", "build_tool_router_runtime_surface"),
    ("tool_tagger", "core.services.tool_tagger", "build_tool_tagger_surface"),
    ("tool_usage_store", "core.services.tool_usage_store", "build_tool_usage_store_surface"),
]


def producer_names() -> list[str]:
    """Navnene i kald-rækkefølge — til test og introspektion."""
    return [name for (name, _mod, _fn) in _PRODUCERS]


def build_tool_infra_surface() -> dict[str, Any]:
    """Kald alle 12 producenter og returnér deres egne signaler. Kaster ALDRIG."""
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

    live = [n for n, s in surfaces.items() if isinstance(s, dict) and s.get("active")]
    silent = [n for n in surfaces if n not in live]
    return {
        "mode": "tool-infra-v1",
        "surfaces": surfaces,
        "live": live,
        "silent": silent,
        "summary": (
            f"{len(live)}/{len(surfaces)} lag melder data"
            + (f"; tavse: {', '.join(silent)}" if silent else "")
        ),
    }
