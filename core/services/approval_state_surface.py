"""Samlet flade for godkendelses- og samtykke-lagene — de build_*_surface ingen rute kaldte.

Målt 7/11-2026: 202 ``build_*_surface`` i core/services blev aldrig kaldt fra
apps/. Godkendelses-bunken er den gruppe hvor en manglende læser koster mest:
her ligger tilstand som «en godkendelse venter», «en anmodning er udløbet»,
«en grænse er sat» og «veto-laget afviste». Uden en indgang kan den tilstand
vente i månedsvis uden at nogen ser den — det er samme fejlform som de 48
initiativer der aldrig fik et svar fordi spørgsmålet ikke nåede en knap.

Mønstret er ``memory_state_surface`` og ``central_tool_infra_surface``:
deklarativ ``_PRODUCERS``, én læsning kalder alle READ-ONLY surfaces og
returnerer deres egne signaler uændret, og hver producent er self-safe — en
kastende flade isoleres til ``{"active": False, "reason": …}``.

Alle otte er målt før de blev skrevet ind: ingen påkrævede argumenter, dict-svar,
ingen LLM-kald.
"""
from __future__ import annotations

import importlib
from typing import Any

# (navn, modul, funktion). Målt 7/11-2026: alle svarer med en ikke-tom dict.
_PRODUCERS: list[tuple[str, str, str]] = [
    ("approval_runtime", "core.services.approval_runtime", "build_approval_runtime_surface"),
    ("approval_outbox", "core.services.approval_outbox", "build_approval_outbox_surface"),
    ("approval_expiry_daemon", "core.services.approval_expiry_daemon", "build_approval_expiry_daemon_surface"),
    ("approval_feedback_subscriber", "core.services.approval_feedback_subscriber", "build_approval_feedback_subscriber_surface"),
    ("agent_approval_notify", "core.services.agent_approval_notify", "build_agent_approval_notify_surface"),
    ("agent_approval_gate", "core.services.agent_approval_gate", "build_agent_approval_gate_surface"),
    ("consent_registry", "core.services.consent_registry", "build_consent_registry_surface"),
    ("veto_gate", "core.services.veto_gate", "build_veto_gate_surface"),
]


def producer_names() -> list[str]:
    """Navnene i kald-rækkefølge — til test og introspektion."""
    return [name for (name, _mod, _fn) in _PRODUCERS]


def _is_live(surface: Any) -> bool:
    if not isinstance(surface, dict) or not surface:
        return False
    if "active" in surface:
        return bool(surface["active"])
    # Flader uden active-nøgle melder data hvis de har indhold og ikke selv er
    # fejl-indpakket af aggregatoren.
    return "reason" not in surface


def build_approval_state_surface() -> dict[str, Any]:
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
        "mode": "approval-state-v1",
        "surfaces": surfaces,
        "live": live,
        "silent": silent,
        "summary": (
            f"{len(live)}/{len(surfaces)} godkendelses-lag melder data"
            + (f"; tavse: {', '.join(silent)}" if silent else "")
        ),
    }
